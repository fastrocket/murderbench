"""Evidence-backed readiness audit; no network, authorization or ledger mutation."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from benchmark.necessity_native import canonical
from benchmark.necessity_resource_probe_plan import ROOT, digest, validate
from benchmark.necessity_resource_probe_collector import freeze
from benchmark.necessity_resource_probe_access_audit import audit


def check():
    def load(path):
        return json.loads((ROOT/path).read_text())
    parent = load("plans/necessity-resource-probe-collection-manifest.json")
    analysis = load("plans/necessity-resource-probe-analysis-amendment.json")
    collector = load("plans/necessity-resource-probe-collector-amendment.json")
    replay = load("plans/necessity-resource-probe-reanalysis-amendment.json")
    validate(parent)
    if freeze(parent, analysis) != collector:
        raise ValueError("collector amendment changed")
    contents = deepcopy(replay)
    expected = contents.pop("amendment_sha256")
    if hashlib.sha256(canonical(contents).encode()).hexdigest() != expected or replay["collector_amendment_sha256"] != collector["amendment_sha256"]:
        raise ValueError("reanalysis amendment changed")
    paths = {"benchmark/necessity_resource_probe_reanalysis.py", "benchmark/necessity_collection_analysis.py",
             "plans/necessity-resource-probe-reanalysis-interface.txt"}
    if set(replay["source_sha256_normalized_lf"]) != paths:
        raise ValueError("reanalysis source set changed")
    for path, expected in replay["source_sha256_normalized_lf"].items():
        if digest(ROOT/path) != expected:
            raise ValueError("reanalysis source changed")
    receipt_audit = audit()
    if receipt_audit != load("reviews/necessity-resource-probe-access-audit.json"):
        raise ValueError("stored access audit differs from private receipts")
    access = load("reviews/necessity-resource-probe-access.json")
    planned = [r["model"] for r in parent["route_prices"]]
    if [r["model"] for r in access["routes"]] != planned:
        raise ValueError("access route set/order mismatch")
    unverified = [r["model"] for r in access["routes"] if r["status"] != "passed_exact_schema_handshake"]
    price = load("reviews/necessity-resource-probe-current-price.json")
    remaining = Decimal(access["budget"]["remaining_accounted_usd"])
    supplement = next(s for s in price["studies"] if s["manifest_sha256"] == parent["manifest_sha256"])
    required = Decimal(supplement["conditional_usd"])
    return {"stage":"readiness_audit_not_authorization", "parent_manifest_sha256":parent["manifest_sha256"],
            "source_chains_valid":True, "exact_schema_passes":len(planned)-len(unverified),
            "unverified_routes":unverified, "remaining_authorized_usd_at_latest_receipt":str(remaining),
            "supplement_conditional_usd":str(required), "budget_compatible":required <= remaining,
            "collection_ready":False,
            "outstanding":["Google exact-schema access", "sufficient explicitly approved lifetime budget",
                           "guarded live wrapper with durable checkpoints and collection lock",
                           "review frozen claims against closest original implementations before novelty marketing"],
            "limits":["Snapshot budget must be checked against live shared ledger at admission.",
                      "Exact-schema handshake checks two requested tools, not all action semantics.",
                      "Priority and real-world validity remain unproved."]}


if __name__ == "__main__":
    output = ROOT/"reviews/necessity-resource-probe-readiness.json"
    if output.exists():
        raise RuntimeError("preserve readiness audit")
    result = check()
    output.write_text(json.dumps(result, indent=2)+"\n")
    print("Ready:", result["collection_ready"], "schema passes:", result["exact_schema_passes"],
          "budget compatible:", result["budget_compatible"])
