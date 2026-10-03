"""New prospective identity for previously unattempted native routes."""
import argparse
from copy import deepcopy
import hashlib
import json
import sqlite3
import urllib.error
from benchmark.necessity_native import ROOT,Ledger,canonical
from benchmark.necessity_native_probes import prepare as original_plan,probe_schema,SCHEMAS
from benchmark.necessity_collection_live import atomic_json,collector_lock,transport_for
from benchmark.necessity_collection_plan import normalized_hash
from benchmark.necessity_native_pilot import load_key
from benchmark.necessity_collection_analysis import ReceiptReader

PLAN=ROOT/"plans/necessity-remaining-probe-manifest.json"
REPORT=ROOT/"reviews/necessity-remaining-probes.json"

def prepare():
    old=original_plan()
    value={**old,"routes":old["routes"][3:],"max_requests":30,"study_cap_usd":"2",
           "original_probe_manifest_sha256":old["probe_manifest_sha256"],
           "remaining_source_sha256":normalized_hash(ROOT/"benchmark/necessity_remaining_probes.py"),
           "scope":"Previously unattempted routes only; no Google replay or parameter change"}
    value.pop("probe_manifest_sha256")
    value["probe_manifest_sha256"]=hashlib.sha256(canonical(value).encode()).hexdigest()
    return value

def run(plan,ledger,transport,save):
    if plan!=prepare(): raise ValueError("remaining probe source mismatch")
    report={"manifest_sha256":plan["manifest_sha256"],"probe_manifest_sha256":plan["probe_manifest_sha256"],
            "routes":[],"collection_state":"running"}
    def persist():
        report["budget"]=ledger.summary(); save(deepcopy(report))
    persist()
    for route in plan["routes"]:
        row={"model":route["model"],"provider_tag":route["provider"],"schemas":[],"status":"incomplete"}
        report["routes"].append(row)
        try:
            for name in SCHEMAS:
                row["schemas"].append(probe_schema(plan,route,name,ledger,transport));persist()
        except BaseException as exc:
            row["status"]="probe_stopped";row["exception_type"]=type(exc).__name__
            if isinstance(exc,urllib.error.HTTPError): row["http_status"]=exc.code
            report["collection_state"]="stopped";persist()
            if isinstance(exc,(KeyboardInterrupt,SystemExit)): raise
            return report
        row["status"]="verified_native_interface";persist()
    report["collection_state"]="finished";persist();return report

def verify(plan,report,conn):
    if plan!=prepare() or report["probe_manifest_sha256"]!=plan["probe_manifest_sha256"] or len(report["routes"])>5:
        raise ValueError("remaining probe identity mismatch")
    checked=0
    for route,row in zip(plan["routes"],report["routes"]):
        if (route["model"],route["provider"])!=(row["model"],row["provider_tag"]): raise ValueError("route mismatch")
        if len(row["schemas"])>3: raise ValueError("extra schemas")
        for name,exported in zip(SCHEMAS,row["schemas"]):
            actual=probe_schema(plan,route,name,ReceiptReader(conn),lambda p:(_ for _ in ()).throw(AssertionError("no network")))
            if actual!=exported: raise ValueError("receipt mismatch")
            checked+=2
        if row["status"]=="verified_native_interface" and len(row["schemas"])!=3: raise ValueError("incomplete route")
    return {"verified_routes":sum(r["status"]=="verified_native_interface" for r in report["routes"]),
            "verified_native_receipts":checked,"collection_state":report["collection_state"]}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["prepare","run","verify"]);args=parser.parse_args()
    if args.command=="prepare":
        if PLAN.exists(): raise RuntimeError("preserve existing manifest")
        atomic_json(PLAN,prepare());return
    plan=json.loads(PLAN.read_text())
    if args.command=="run":
        with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
            ledger=Ledger(ROOT/"private/necessity-native.sqlite",study_cap=plan["study_cap_usd"])
            try: print(run(plan,ledger,transport_for(load_key()),lambda r:atomic_json(REPORT,r))["collection_state"])
            finally: ledger.close()
    else:
        conn=sqlite3.connect((ROOT/"private/necessity-native.sqlite").resolve().as_uri()+"?mode=ro",uri=True)
        try: result=verify(plan,json.loads(REPORT.read_text()),conn)
        finally: conn.close()
        atomic_json(ROOT/"reviews/necessity-remaining-probe-verification.json",result);print(result)

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("STOP:",type(exc).__name__,"Review saved state; no retry.");raise SystemExit(1) from None
