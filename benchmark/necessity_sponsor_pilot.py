"""Bounded outreach pilot. Registered source/cases before queries; no retries."""
import argparse
import hashlib
import json
from benchmark.necessity_native import ROOT, canonical
from benchmark.necessity_authorized_ledger import AuthorizedLedger
from benchmark.necessity_resource_probe import ProbeContract, ProbeWorld, ProbeEnvironment
from benchmark.necessity_resource_probe_native import public_packet, run_episode
from benchmark.necessity_resource_probe_analysis import diagnose
from benchmark.necessity_resource_probe_plan import digest
from benchmark.necessity_collection_live import atomic_json, collector_lock, transport_for
from benchmark.necessity_native_pilot import load_key

PLAN=ROOT/"plans/necessity-sponsor-pilot-manifest.json"
REPORT=ROOT/"reviews/necessity-sponsor-pilot.json"
CONTRACTS=((1,3,2),(2,2,2),(2,3,2))
SOURCES=("benchmark/necessity_sponsor_pilot.py","benchmark/necessity_authorized_ledger.py",
         "benchmark/necessity_resource_probe_native.py","benchmark/necessity_resource_probe_analysis.py",
         "benchmark/necessity_resource_probe.py","benchmark/necessity_resource_probe_verifier.py",
         "benchmark/necessity_structural_native.py","benchmark/necessity_native.py",
         "benchmark/necessity_oracle.py","benchmark/necessity_collection_live.py",
         "benchmark/necessity_native_pilot.py","plans/budget-authorization-2026-10-03.json")


def prepare():
    routes=json.loads((ROOT/"plans/necessity-resource-probe-collection-manifest.json").read_text())["route_prices"]
    access=json.loads((ROOT/"reviews/necessity-resource-probe-access.json").read_text())
    eligible={r["model"] for r in access["routes"] if r["status"]=="passed_exact_schema_handshake"}
    episodes=[]
    for route in routes:
        for capacity,deadline,delay in CONTRACTS:
            for need in (False,True):
                contract=ProbeContract(capacity,deadline,delay)
                env=ProbeEnvironment(ProbeWorld(need),contract)
                fields={"model":route["model"],"capacity":capacity,"deadline":deadline,"delay":delay,"need":need}
                episodes.append({**fields,"episode_id":hashlib.sha256(canonical(fields).encode()).hexdigest(),
                                 "public_packet_sha256":hashlib.sha256(canonical(public_packet(env)).encode()).hexdigest(),
                                 "eligible":route["model"] in eligible})
    result={"stage":"descriptive_sponsor_pilot_not_full_confirmation","episodes":episodes,"routes":routes,
            "pilot_cap_usd":"50","lifetime_cap_usd":"100","max_calls":240,"repetitions":1,
            "analysis":"Report all planned cells. Unknown/unattempted have no score. Full vectors and first-loss diagnoses; no population inference or intent claim.",
            "confirmation_disclosure":"Selected six base cells become model-exposed development cases; original larger manifest is preserved but no longer wholly model-unqueried.",
            "source_sha256":{p:digest(ROOT/p) for p in SOURCES}}
    result["study_id"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=("prepare","run"));args=parser.parse_args()
    if args.command=="prepare":
        if PLAN.exists(): raise RuntimeError("preserve pilot freeze")
        atomic_json(PLAN,prepare());return
    plan=json.loads(PLAN.read_text())
    if plan!=prepare() or REPORT.exists(): raise RuntimeError("source changed or prior report; no rerun")
    routes={r["model"]:r for r in plan["routes"]}
    report={"study_id":plan["study_id"],"stage":plan["stage"],"records":[],"state":"running"}
    with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
        ledger=AuthorizedLedger(ROOT/"private/necessity-native.sqlite",plan["study_id"])
        try:
            transport=transport_for(load_key())
            atomic_json(REPORT,report)
            blocked=set()
            for row in plan["episodes"]:
                if not row["eligible"] or row["model"] in blocked:
                    report["records"].append({"episode_id":row["episode_id"],"status":"not_attempted_interface_unverified"})
                else:
                    env=ProbeEnvironment(ProbeWorld(row["need"]),ProbeContract(row["capacity"],row["deadline"],row["delay"]))
                    packet=public_packet(env)
                    if hashlib.sha256(canonical(packet).encode()).hexdigest()!=row["public_packet_sha256"]:
                        raise ValueError("packet mismatch")
                    entry=routes[row["model"]]
                    route={"model":entry["model"],"provider":entry["provider_tag"],"provider_name":entry["provider_name"]}
                    try:
                        result=run_episode(env,route,packet,row["episode_id"],plan["study_id"]+"/"+row["model"],ledger,transport)
                    except BaseException as exc:
                        result={"status":"collection_stopped","exception_type":type(exc).__name__,"events":env.events,"outcome":None}
                        blocked.add(row["model"])
                        if isinstance(exc,(KeyboardInterrupt,SystemExit)): raise
                    record={"episode_id":row["episode_id"],**result}
                    if result["status"]=="completed":
                        record["diagnosis"]=diagnose(env._contract,env._message,result["events"])
                    else: blocked.add(row["model"])
                    report["records"].append(record)
                report["budget"]=ledger.summary();atomic_json(REPORT,report)
                print(len(report["records"]),row["model"],report["records"][-1]["status"],flush=True)
            report["state"]="finished_bounded_pilot";atomic_json(REPORT,report)
        finally: ledger.close()


if __name__=="__main__":main()
