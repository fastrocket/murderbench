"""Prospective text-only routing diagnostic; original requests remain intact."""
import argparse
import hashlib
import json
import urllib.error
from benchmark.necessity_native import ROOT,Ledger,canonical
from benchmark.necessity_native_probes import prepare as parent_plan,SCHEMAS,messages_for
from benchmark.necessity_structural_native import payload_for,decode
from benchmark.necessity_collection_live import atomic_json,collector_lock,transport_for
from benchmark.necessity_collection_plan import normalized_hash
from benchmark.necessity_native_pilot import load_key

PLAN=ROOT/"plans/necessity-google-text-diagnostic-manifest.json"
REPORT=ROOT/"reviews/necessity-google-text-diagnostic.json"

from benchmark.necessity_text_routing import text_only_payload as payload

def prepare():
    parent=parent_plan()
    value={"parent_probe_manifest_sha256":parent["probe_manifest_sha256"],
           "manifest_sha256":parent["manifest_sha256"],"route":parent["routes"][2],
           "text_routing_sha256":normalized_hash(ROOT/"benchmark/necessity_text_routing.py"),
           "source_sha256":normalized_hash(ROOT/"benchmark/necessity_google_text_probe.py"),
           "max_requests":6,"study_cap_usd":"2","original_lifetime_cap_usd":"50",
           "change":"Remove only image max-price filter from validated text-only requests; original tool parameters retained.",
           "unchanged":"Pinned route, auto tool choice, reasoning, data_collection deny, all other prices, tool schemas and simulator semantics",
           "stage":"diagnostic_not_benchmark; no held request replay"}
    value["study_id"]=hashlib.sha256(canonical(value).encode()).hexdigest()
    return value

def run(plan,ledger,transport,save):
    if plan!=prepare(): raise ValueError("diagnostic source changed")
    report={"study_id":plan["study_id"],"status":"running","schemas":[]}
    def persist(): report["budget"]=ledger.summary();save(report)
    persist()
    for name,names in SCHEMAS.items():
        messages,seen,receipts=messages_for(),set(),[]
        try:
            for turn,expected in enumerate(("wait","finish")):
                packet=payload(plan["route"],messages,names)
                identity=hashlib.sha256((plan["study_id"]+"/"+name+"/"+str(turn)).encode()).hexdigest()
                response=ledger.reserve(identity,plan["study_id"],packet)
                if response is None:
                    try: response=transport(packet)
                    except BaseException: ledger.hold(identity,"transport_unknown");raise
                    ledger.receive(identity,response)
                action,claim,tool_id,assistant,origin=decode(response,plan["route"],seen,names)
                if origin!="native_tool" or action!=expected or claim!=("unknown" if turn else None):
                    raise ValueError("unexpected diagnostic sequence")
                seen.add(tool_id)
                receipts.append({"call_id":identity,"action":action,"claim":claim,
                                 "response_sha256":hashlib.sha256(canonical(response).encode()).hexdigest()})
                messages.extend([assistant,{"role":"tool","tool_call_id":tool_id,
                                           "content":canonical({"acknowledged":True,"interface_check_only":True})}])
        except BaseException as exc:
            report["status"]="stopped";report["failed_schema"]=name
            report["exception_type"]=type(exc).__name__
            if isinstance(exc,urllib.error.HTTPError):
                report["http_status"]=exc.code
                # Classify a few known errors, never export raw error text.
                text=exc.read(16384).decode("utf-8",errors="replace").lower()
                report["error_indicators"]={"empty_object_schema":"non-empty" in text and "properties" in text,
                    "routing_no_endpoint":"no endpoints" in text,"reasoning_parameter":"reasoning" in text,
                    "data_policy":"data policy" in text or "data collection" in text}
            persist()
            if isinstance(exc,(KeyboardInterrupt,SystemExit)): raise
            return report
        report["schemas"].append({"schema":name,"receipts":receipts});persist()
    report["status"]="passed_text_only_routing";persist();return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["prepare","run"]);args=parser.parse_args()
    if args.command=="prepare":
        if PLAN.exists(): raise RuntimeError("preserve diagnostic manifest")
        atomic_json(PLAN,prepare());return
    plan=json.loads(PLAN.read_text())
    with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
        ledger=Ledger(ROOT/"private/necessity-native.sqlite",study_cap=plan["study_cap_usd"])
        try: print(run(plan,ledger,transport_for(load_key()),lambda r:atomic_json(REPORT,r))["status"])
        finally: ledger.close()

if __name__=="__main__":
    try: main()
    except Exception as exc: print("STOP:",type(exc).__name__);raise SystemExit(1) from None
