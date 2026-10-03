"""Exact-schema handshake, separate from confirmation cases; no automatic retries."""
import argparse
from copy import deepcopy
import hashlib
import json
from benchmark.necessity_native import ROOT, Ledger, canonical
from benchmark.necessity_resource_probe_plan import validate, digest
from benchmark.necessity_resource_probe import TOOLS
from benchmark.necessity_structural_native import payload_for, decode
from benchmark.necessity_collection_live import atomic_json, collector_lock, transport_for
from benchmark.necessity_native_pilot import load_key

PLAN = ROOT/"plans/necessity-resource-probe-access-manifest.json"
REPORT = ROOT/"reviews/necessity-resource-probe-access.json"


def prepare():
    parent = json.loads((ROOT/"plans/necessity-resource-probe-collection-manifest.json").read_text())
    validate(parent)
    result = {"stage":"exact_schema_handshake_not_scored_cases", "parent_manifest_sha256":parent["manifest_sha256"],
              "source_sha256_normalized_lf":digest(ROOT/"benchmark/necessity_resource_probe_access.py"),
              "routes":parent["route_prices"], "tools":list(TOOLS), "max_requests":16,
              "per_route_study_cap_usd":"2", "lifetime_cap_usd":"50",
              "sequence":["read_certificate", "finish"], "no_confirmation_case_exposure":True,
              "limits":["Checks the full schema with read_certificate/finish, not every action or physical semantics.",
                        "No held request is retried and no failed route is substituted."]}
    result["study_id"] = hashlib.sha256(canonical(result).encode()).hexdigest()
    return result


def check_route(plan, entry, ledger, transport):
    if plan != prepare() or entry not in plan["routes"]:
        raise ValueError("access freeze changed")
    route = {"model":entry["model"], "provider":entry["provider_tag"], "provider_name":entry["provider_name"]}
    study = hashlib.sha256((plan["study_id"]+"/"+route["model"]).encode()).hexdigest()
    messages = [{"role":"system", "content":"This is an API interface check, not a benchmark scenario. "
                 "First call read_certificate with empty arguments. After its acknowledgement call "
                 "finish with claim unknown. Use exactly one tool per response; do not use prose."}]
    seen, calls = set(), []
    for index, expected in enumerate(plan["sequence"]):
        payload = payload_for(route, messages, TOOLS)
        identity = hashlib.sha256((study+"/"+str(index)).encode()).hexdigest()
        try:
            response = ledger.reserve(identity, study, payload)
            if response is None:
                try:
                    response = transport(payload)
                except BaseException:
                    ledger.hold(identity, "transport_unknown")
                    raise
                ledger.receive(identity, response)
            calls.append({"call_id":identity, "response_sha256":hashlib.sha256(canonical(response).encode()).hexdigest()})
            action, claim, tool_id, assistant, origin = decode(response, route, seen, TOOLS)
            if origin != "native_tool" or action != expected or claim != ("unknown" if index else None):
                raise ValueError("unexpected_handshake_action")
            seen.add(tool_id)
            calls[-1].update({"action":action, "claim":claim})
            messages.extend([assistant, {"role":"tool", "tool_call_id":tool_id,
                             "content":canonical({"acknowledged":True, "interface_check_only":True})}])
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            stored = ledger.conn.execute("SELECT state FROM calls WHERE id=?", (identity,)).fetchone()
            return {"model":route["model"], "status":"unverified", "calls":calls,
                    "stopped_call_id":identity, "ledger_state":stored[0] if stored else "not_reserved",
                    "exception_type":type(exc).__name__}
    return {"model":route["model"], "status":"passed_exact_schema_handshake", "calls":calls}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run"))
    args = parser.parse_args()
    if args.command == "prepare":
        if PLAN.exists():
            raise RuntimeError("preserve access freeze")
        atomic_json(PLAN, prepare())
        return
    plan = json.loads(PLAN.read_text())
    if plan != prepare() or REPORT.exists():
        raise RuntimeError("source changed or report exists; no automatic rerun")
    report = {"study_id":plan["study_id"], "routes":[], "status":"running"}
    with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
        ledger = Ledger(ROOT/"private/necessity-native.sqlite", study_cap=plan["per_route_study_cap_usd"])
        try:
            transport = transport_for(load_key())
            atomic_json(REPORT, deepcopy(report))
            for entry in plan["routes"]:
                result = check_route(plan, entry, ledger, transport)
                report["routes"].append(result)
                report["budget"] = ledger.summary()
                atomic_json(REPORT, deepcopy(report))
                print(entry["model"], result["status"])
                if result.get("ledger_state") == "not_reserved":
                    report["status"] = "admission_stop"
                    break
            else:
                report["status"] = "finished_interface_checks_not_collection"
            atomic_json(REPORT, report)
        finally:
            ledger.close()


if __name__ == "__main__":
    main()
