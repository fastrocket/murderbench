"""Bounded API schema/continuation probes, with no scored scenario exposure."""
import argparse
from copy import deepcopy
import hashlib
import json
from contextlib import closing
import sqlite3

from benchmark.necessity_native import ROOT,Ledger,canonical
from benchmark.necessity_structural_native import payload_for,decode
from benchmark.necessity_events import TOOLS as EVENT_TOOLS
from benchmark.necessity_queue import TOOLS as QUEUE_TOOLS
from benchmark.necessity_pending import TOOLS as PENDING_TOOLS
from benchmark.necessity_collection_live import read_inputs,validate_live,atomic_json,collector_lock,transport_for
from benchmark.necessity_native_pilot import load_key
from benchmark.necessity_collection_plan import normalized_hash

SCHEMAS = {"event":EVENT_TOOLS,"queue":QUEUE_TOOLS,"pending":PENDING_TOOLS}
PLAN = ROOT/"plans/necessity-native-probe-manifest.json"
REPORT = ROOT/"reviews/necessity-native-probes.json"


def prepare():
    manifest,extension,live = read_inputs()
    validate_live(manifest,extension,live)
    value = {"stage":"schema-probes-not-benchmark-results","manifest_sha256":manifest["manifest_sha256"],
             "live_amendment_sha256":live["amendment_sha256"],
             "probe_source_sha256":normalized_hash(ROOT/"benchmark/necessity_native_probes.py"),
             "routes":[{"model":r["model"],"provider":r["provider_tag"],"provider_name":r["provider_name"]} for r in manifest["route_prices"]],
             "schemas":{k:list(v) for k,v in SCHEMAS.items()},"turns_per_schema":2,
             "max_requests":48,"study_cap_usd":"3","original_lifetime_cap_usd":"50",
             "limits":["No scored world, loss, deadline or case is shown.",
                       "Checks exact wait then finish(unknown) tool calls with native continuation.",
                       "Does not prove task competence, checkpoint equivalence or generation latency bounds.",
                       "Budget admission may stop before all routes; no automatic retry."]}
    value["probe_manifest_sha256"] = hashlib.sha256(canonical(value).encode()).hexdigest()
    return value


def validate_plan(plan):
    if plan != prepare():
        raise ValueError("probe source or parent changed")


def messages_for():
    return [{"role":"system","content":"This is an isolated API interface check, not a rescue scenario. No real effect can occur. Use exactly one native tool per response. First call wait with empty arguments. After its acknowledgement, call finish with claim unknown. Do not answer in prose or call other tools."},
            {"role":"user","content":"Start the two-turn interface check by calling wait."}]


def probe_schema(plan,route,name,ledger,transport):
    messages,seen,receipts = messages_for(),set(),[]
    study = plan["probe_manifest_sha256"]
    for turn,expected in enumerate(("wait","finish")):
        packet = payload_for(route,messages,SCHEMAS[name])
        identity = hashlib.sha256((study+"/"+route["model"]+"/"+name+"/"+str(turn)).encode()).hexdigest()
        response = ledger.reserve(identity,study,packet)
        if response is None:
            try:
                response = transport(packet)
            except BaseException:
                ledger.hold(identity,"transport_unknown")
                raise
            ledger.receive(identity,response)
        action,claim,tool_id,assistant,origin = decode(response,route,seen,SCHEMAS[name])
        if origin != "native_tool" or action != expected or claim != ("unknown" if expected == "finish" else None):
            raise ValueError("probe_sequence_not_followed")
        seen.add(tool_id)
        receipts.append({"call_id":identity,"model":response["model"],"provider":response["provider"],
                         "action":action,"claim":claim,"usage":response["usage"],
                         "raw_response_sha256":hashlib.sha256(canonical(response).encode()).hexdigest()})
        messages.extend([assistant,{"role":"tool","tool_call_id":tool_id,
                                   "content":canonical({"acknowledged":True,"interface_check_only":True})}])
    return {"schema":name,"status":"verified_native_schema_continuation","receipts":receipts}


def run(plan,ledger,transport,save):
    validate_plan(plan)
    report = {"manifest_sha256":plan["manifest_sha256"],"probe_manifest_sha256":plan["probe_manifest_sha256"],
              "stage":plan["stage"],"routes":[],"collection_state":"running"}
    def persist():
        report["budget"] = ledger.summary()
        save(deepcopy(report))
    persist()
    for route in plan["routes"]:
        result = {"model":route["model"],"provider_tag":route["provider"],"schemas":[],"status":"incomplete"}
        report["routes"].append(result)
        try:
            for name in SCHEMAS:
                result["schemas"].append(probe_schema(plan,route,name,ledger,transport))
                persist()
        except BaseException as exc:
            result["status"] = "probe_stopped"
            result["exception_type"] = type(exc).__name__
            report["collection_state"] = "stopped"
            persist()
            if isinstance(exc,(KeyboardInterrupt,SystemExit)):
                raise
            return report
        result["status"] = "verified_native_interface"
        persist()
    report["collection_state"] = "finished"
    persist()
    return report


def verify(plan,report,conn):
    validate_plan(plan)
    if len(report["routes"]) > len(plan["routes"]):
        raise ValueError("extra probe routes")
    expected_routes = plan["routes"][:len(report["routes"])]
    if report["probe_manifest_sha256"] != plan["probe_manifest_sha256"] or report["manifest_sha256"] != plan["manifest_sha256"]:
        raise ValueError("probe report identity mismatch")
    from benchmark.necessity_collection_analysis import ReceiptReader
    checked = 0
    for route,exported in zip(expected_routes,report["routes"]):
        if (route["model"],route["provider"]) != (exported["model"],exported["provider_tag"]):
            raise ValueError("probe route order mismatch")
        if len(exported["schemas"]) > len(SCHEMAS):
            raise ValueError("probe schema count mismatch")
        for name,schema in zip(SCHEMAS,exported["schemas"]):
            reader = ReceiptReader(conn)
            actual = probe_schema(plan,route,name,reader,lambda p:(_ for _ in ()).throw(AssertionError("network forbidden")))
            if actual != schema:
                raise ValueError("probe export differs from private native receipts")
            checked += 2
        if exported["status"] == "verified_native_interface" and len(exported["schemas"]) != 3:
            raise ValueError("incomplete schema set cannot verify route")
    return {"verified_routes":sum(r["status"] == "verified_native_interface" for r in report["routes"]),
            "verified_native_receipts":checked,"collection_state":report["collection_state"],
            "limits":"Only completed schema checks replayed; interrupted/failed schema receipts remain private and unverified."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command",choices=["prepare","run","verify"])
    args = parser.parse_args()
    if args.command == "prepare":
        if PLAN.exists():
            raise RuntimeError("probe manifest exists; preserve it")
        atomic_json(PLAN,prepare())
        print("Prepared at most48 API requests; USD3 probe cap within original USD50.")
        return
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if args.command == "run":
        with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
            ledger = Ledger(ROOT/"private/necessity-native.sqlite",study_cap=plan["study_cap_usd"])
            try:
                result = run(plan,ledger,transport_for(load_key()),lambda r:atomic_json(REPORT,r))
                print("Probe state:",result["collection_state"],flush=True)
            finally:
                ledger.close()
    else:
        with closing(sqlite3.connect((ROOT/"private/necessity-native.sqlite").resolve().as_uri()+"?mode=ro",uri=True)) as conn:
            result = verify(plan,json.loads(REPORT.read_text(encoding="utf-8")),conn)
        atomic_json(ROOT/"reviews/necessity-native-probe-verification.json",result)
        print("Verified routes:",result["verified_routes"],"Native receipts:",result["verified_native_receipts"])

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("STOP:",type(exc).__name__,"Review saved state; no automatic retry.")
        raise SystemExit(1) from None
