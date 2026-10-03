"""Rebuild public results from read-only native receipts; no transport or writes."""
from collections import Counter
import hashlib
import json
from benchmark.necessity_native import canonical
from benchmark.necessity_resource_probe_plan import ROOT
from benchmark.necessity_resource_probe_collector import freeze
from benchmark.necessity_resource_probe import ProbeEnvironment, ProbeWorld, ProbeContract
from benchmark.necessity_resource_probe_native import public_packet, run_episode
from benchmark.necessity_resource_probe_analysis import diagnose
from benchmark.necessity_collection_analysis import ReceiptReader


def analyze(manifest, analysis, amendment, report, conn):
    if freeze(manifest, analysis) != amendment:
        raise ValueError("collector freeze changed")
    if conn.execute("PRAGMA query_only").fetchone()[0] != 1:
        raise ValueError("query-only receipt connection required")
    study = hashlib.sha256((manifest["manifest_sha256"]+"/"+amendment["amendment_sha256"]).encode()).hexdigest()
    if (report.get("study_id") != study or report.get("manifest_sha256") != manifest["manifest_sha256"] or
            report.get("amendment_sha256") != amendment["amendment_sha256"]):
        raise ValueError("report identity mismatch")
    rows, records = manifest["episodes"], report["records"]
    if (len(records) > len(rows) or [r["episode_id"] for r in records] != [r["episode_id"] for r in rows[:len(records)]] or
            report.get("planned_episodes") != len(rows) or report.get("not_attempted") != len(rows)-len(records)):
        raise ValueError("report is not the frozen prefix with accurate denominators")
    if report.get("collection_state") == "finished" and len(records) != len(rows):
        raise ValueError("incomplete report claims finished")
    cells = {c["cell_id"]:c for c in json.loads((ROOT/"plans/necessity-resource-probe-registration.json").read_text())["base_cells"]}
    routes = {p["model"]:p for p in manifest["route_prices"]}
    verified, receipts = [], []
    counts = Counter({"planned":len(rows), "not_attempted":len(rows)-len(records)})
    for row, record in zip(rows, records):
        cell = cells[row["cell_id"]]
        contract = ProbeContract(**{k:cell[k] for k in ("reserve_capacity", "deadline", "probe_delay", "max_calls")})
        env = ProbeEnvironment(ProbeWorld(cell["need"]), contract)
        route = {"model":row["model"], "provider":row["provider_tag"], "provider_name":routes[row["model"]]["provider_name"]}
        exported = record["result"]
        reader = ReceiptReader(conn)
        try:
            rebuilt = run_episode(env, route, public_packet(env), row["episode_id"], study, reader,
                                  lambda _: (_ for _ in ()).throw(AssertionError("network forbidden")))
        except RuntimeError as exc:
            if str(exc) not in {"receipt_missing", "receipt_unresolved"}:
                raise
            if exported["status"] != "collection_stopped" or exported["outcome"] is not None or exported["events"] != env.events:
                raise ValueError("stopped trace differs from stored receipts") from None
            rebuilt = {"status":"collection_stopped", "events":env.events, "outcome":None}
        else:
            for key in ("status", "events", "outcome"):
                if rebuilt[key] != exported[key]:
                    raise ValueError("public result differs from native receipts")
            if rebuilt["status"] == "technical_unknown" and rebuilt["reason"] != exported["reason"]:
                raise ValueError("technical reason mismatch")
            if rebuilt["status"] == "completed":
                for key in ("action_origins", "operator_prefix_event_count", "unstructured_claim_truth_measured"):
                    if rebuilt[key] != exported[key]:
                        raise ValueError("action attribution mismatch")
        if [a["call_id"] for a in exported["attempts"]] != [a["call_id"] for a in reader.used]:
            raise ValueError("request identifiers differ from receipt replay")
        status = rebuilt["status"]
        if status != "completed" and record is not records[-1]:
            raise ValueError("collector continued after stop")
        output = {"episode_id":row["episode_id"], "model":row["model"], "status":status,
                  "outcome":rebuilt["outcome"]}
        if status == "completed":
            diagnosis = diagnose(contract, env._message, rebuilt["events"])
            if "diagnosis" in record:
                if diagnosis != record["diagnosis"]:
                    raise ValueError("first-loss diagnosis differs from receipt replay")
                output["diagnosis"] = diagnosis
            elif report.get("collection_state") != "analysis_stop" or record is not records[-1]:
                raise ValueError("completed trace lacks required diagnosis")
            else:
                output["diagnosis_recovered_read_only"] = diagnosis
        elif "diagnosis" in record:
            raise ValueError("unknown trace has fabricated diagnosis")
        counts[status] += 1
        verified.append(output)
        receipts.extend(reader.used)
    if report.get("collection_state") == "finished" and counts["completed"] != len(rows):
        raise ValueError("finished report contains unknown results")
    return {"study_id":study, "counts":dict(counts), "records":verified,
            "verified_native_receipts":len(receipts), "receipt_hashes":receipts,
            "limits":["Ledger bytes support identity checks, not cryptographic provider provenance.",
                      "Historical stop causes and budget snapshots are not independently certified.",
                      "Finite-suite descriptive findings; no deployment prevalence or intent inference."]}
