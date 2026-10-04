"""Check frozen coverage, retained attempts, and independent receipt folds."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

from benchmark.recovery_vault_verifier import verify_report

ROOT = Path(__file__).resolve().parents[1]


def audit_pair(report, registration, registration_bytes):
    if report["study"] != registration["study"]:
        raise ValueError("The study identity changed")
    if report["registration_sha256"] != hashlib.sha256(registration_bytes).hexdigest():
        raise ValueError("The frozen registration changed")
    expected_cases = registration["cases"]
    if report["planned"] != len(expected_cases):
        raise ValueError("The planned-case count changed")
    attempted_cases = [record["case"] for record in report["records"]]
    if attempted_cases != expected_cases[:len(attempted_cases)]:
        raise ValueError("The attempted cases differ from the frozen ordered matrix")
    for record in report["records"]:
        events = record.get("events", [])
        for event in events:
            if event["status"] not in {200, 204, 403, 404}:
                allowed = (registration["study"].endswith("v2")
                           and record["case"]["topology"] == "already_lost"
                           and event["path"] == "auth/token/revoke-orphan"
                           and event["status"] == 400
                           and event.get("documented_error") == "token to revoke not found")
                if not allowed and "collection_error" not in record:
                    raise ValueError("An unexpected executor error was scored")
    verified = verify_report(report)
    verified["planned"] = len(expected_cases)
    verified["unattempted_case_ids"] = [case["case_id"] for case in expected_cases[len(attempted_cases):]]
    verified["attempted"] = len(attempted_cases)
    return verified


def audit_workspace(root=ROOT):
    studies = []
    for suffix in ("", "-v2"):
        reg_path = root / f"plans/recovery-vault-registration{suffix}.json"
        report_path = root / f"reviews/recovery-vault-reproduction{suffix}.json"
        registration_bytes = reg_path.read_bytes()
        registration = json.loads(registration_bytes)
        for path, expected in registration["source_sha256"].items():
            if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
                raise ValueError(f"The registered source changed: {path}")
        report = json.loads(report_path.read_bytes())
        verified = audit_pair(report, registration, registration_bytes)
        saved = json.loads((root / f"reviews/recovery-vault-verification{suffix}.json").read_bytes())
        if saved != verify_report(report):
            raise ValueError("The saved receipt verification changed")
        studies.append({"registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
                        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                        **verified})
    amendment = json.loads((root / "plans/recovery-vault-registration-v2.json").read_bytes())["amendment"]
    if amendment["original_report_sha256"] != studies[0]["report_sha256"]:
        raise ValueError("The first collection report changed after the amendment")
    summary = defaultdict(lambda: {"completed": 0, "old_tree_denied": 0, "cases": 0})
    for record in studies[1]["records"]:
        case = record["case_id"].split("-")
        key = case[2] + "/" + case[3]
        summary[key]["cases"] += 1
        summary[key]["completed"] += int(record["recovery_completed"])
        summary[key]["old_tree_denied"] += int(record["old_tree_denied_at_settle"])
    return {"completion_path": "mechanism_reproduced_then_contribution_gate_rejected",
            "studies": studies, "v2_summary": dict(summary),
            "total_reference_attempts": sum(study["attempted"] for study in studies),
            "total_completed_reference_cases": sum(study["verified"] for study in studies),
            "total_unscored_collection_stops": sum(study["unscored"] for study in studies),
            "model_calls": 0, "new_model_spending_usd": 0,
            "receipt_capture_independent": False, "external_peer_review": False,
            "limitations": ["Receipt replay uses published aliases and status codes from one local collector.",
                            "Source hashes establish consistency, not independent capture authenticity.",
                            "Compromise labels specify the fixture requirement, not an observed production intrusion.",
                            "No LLM behavior, safety-framing effect, or novel research finding is established."]}


if __name__ == "__main__":
    result = audit_workspace()
    destination = ROOT / "reviews/recovery-vault-audit.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in
                      ("total_reference_attempts", "total_completed_reference_cases",
                       "total_unscored_collection_stops", "model_calls", "v2_summary")}))
