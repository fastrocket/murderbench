"""Guarded confirmation entry point. Preparation never sends requests."""
import argparse
from decimal import Decimal
import hashlib
import json
from benchmark.necessity_native import ROOT, Ledger, canonical
from benchmark.necessity_resource_probe_plan import digest
from benchmark.necessity_resource_probe_readiness import check
from benchmark.necessity_resource_probe_collector import execute
from benchmark.necessity_collection_live import atomic_json, collector_lock, transport_for
from benchmark.necessity_native_pilot import load_key

PLAN = ROOT/"plans/necessity-resource-probe-live-amendment.json"
REPORT = ROOT/"reviews/necessity-resource-probe-collection.json"
SOURCES = ("benchmark/necessity_resource_probe_live.py", "benchmark/necessity_resource_probe_readiness.py",
           "benchmark/necessity_collection_live.py", "benchmark/necessity_native_pilot.py")


def prepare():
    evidence = check()
    result = {"stage":"guarded_live_source_freeze_not_authorization",
              "parent_manifest_sha256":evidence["parent_manifest_sha256"],
              "source_sha256_normalized_lf":{p:digest(ROOT/p) for p in SOURCES},
              "collection_ready":False, "new_model_calls":0}
    result["amendment_sha256"] = hashlib.sha256(canonical(result).encode()).hexdigest()
    return result


def admit(evidence, budget):
    if not evidence["source_chains_valid"] or evidence["unverified_routes"]:
        raise RuntimeError("exact-interface eligibility incomplete")
    if Decimal(budget["remaining_accounted_usd"]) < Decimal(evidence["supplement_conditional_usd"]):
        raise RuntimeError("insufficient authorized ledger headroom")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run"))
    args = parser.parse_args()
    if args.command == "prepare":
        if PLAN.exists():
            raise RuntimeError("preserve live freeze")
        atomic_json(PLAN, prepare())
        print("Live sources frozen; collection not authorized")
        return
    if json.loads(PLAN.read_text()) != prepare():
        raise ValueError("live source freeze changed")
    if REPORT.exists():
        raise RuntimeError("preserve prior collection; no automatic restart")
    with collector_lock(ROOT/"private/necessity-structural-collector.lock"):
        ledger = Ledger(ROOT/"private/necessity-native.sqlite")
        try:
            evidence = check()
            admit(evidence, ledger.summary())
            def load(name):
                return json.loads((ROOT/"plans"/name).read_text())
            execute(load("necessity-resource-probe-collection-manifest.json"),
                    load("necessity-resource-probe-analysis-amendment.json"),
                    load("necessity-resource-probe-collector-amendment.json"), ledger,
                    transport_for(load_key()), lambda report:atomic_json(REPORT, report))
        finally:
            ledger.close()


if __name__ == "__main__":
    main()
