"""Separate prospective supplement; no model requests or authorization."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from benchmark.necessity_resource_probe import ProbeContract, ProbeWorld, ProbeEnvironment
from benchmark.necessity_resource_probe_native import public_packet
from benchmark.necessity_native import canonical

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "benchmark/necessity_resource_probe_plan.py", "benchmark/necessity_resource_probe.py",
    "benchmark/necessity_resource_probe_native.py", "benchmark/necessity_resource_probe_verifier.py",
    "benchmark/necessity_structural_native.py", "benchmark/necessity_native.py",
    "benchmark/necessity_events.py", "benchmark/necessity_resource_probe_comparator.py",
    "benchmark/necessity_oracle.py", "plans/necessity-resource-probe-analysis-protocol.txt",
    "plans/necessity-resource-probe-protocol.txt", "plans/necessity-resource-probe-registration.json",
    "plans/necessity-structural-route-plan.json",
)


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build():
    registration = json.loads((ROOT/"plans/necessity-resource-probe-registration.json").read_text())
    snapshot = json.loads((ROOT/"plans/necessity-structural-route-plan.json").read_text())
    if digest(ROOT/"plans/necessity-resource-probe-protocol.txt") != registration["protocol_source_sha256_normalized_lf"]:
        raise ValueError("registered protocol changed")
    rows, prices = [], []
    for route in snapshot["routes"]:
        if route["status"] != "public_parameters_available":
            raise ValueError("incomplete route snapshot")
        for cell in registration["base_cells"]:
            fields = {k:v for k,v in cell.items() if k != "cell_id"}
            if hashlib.sha256(canonical(fields).encode()).hexdigest() != cell["cell_id"]:
                raise ValueError("registered cell changed")
            contract = ProbeContract(**{k:cell[k] for k in ("reserve_capacity", "deadline", "probe_delay", "max_calls")})
            packet = public_packet(ProbeEnvironment(ProbeWorld(cell["need"]), contract))
            for rep in range(3):
                identity = {"model":route["model"], "provider_tag":route["provider_tag"],
                            "cell_id":cell["cell_id"], "repetition":rep}
                rows.append({**identity, "episode_id":hashlib.sha256(canonical(identity).encode()).hexdigest(),
                             "public_packet_sha256":hashlib.sha256(canonical(packet).encode()).hexdigest(), "max_calls":5})
        subtotal = Decimal(route["conditional_eight_turn_episode_usd"])*Decimal(5)/8*48
        prices.append({"model":route["model"], "provider_tag":route["provider_tag"],
                       "provider_name":route["provider_name"], "episodes":48, "max_calls":240,
                       "dated_conditional_usd":str(subtotal)})
    result = {"stage":"prospective_supplement_not_collection_authorization", "episodes":rows,
              "episode_count":len(rows), "max_model_calls":len(rows)*5, "repetitions":3,
              "route_prices":prices, "dated_conditional_usd":str(sum(Decimal(p["dated_conditional_usd"]) for p in prices)),
              "price_snapshot_utc":snapshot["retrieved_utc"], "price_assumptions":snapshot["assumptions"],
              "collection_ready":False, "novelty_established":False,
              "missing_gates":["exact adapter eligibility", "prefix analysis and collector implementation freeze",
                               "current price recheck and sufficient authorized budget"],
              "source_sha256_normalized_lf":{p:digest(ROOT/p) for p in SOURCES}}
    result["manifest_sha256"] = hashlib.sha256(canonical(result).encode()).hexdigest()
    return result


def validate(manifest):
    if build() != manifest:
        raise ValueError("resource-probe supplement freeze changed")
    return True


if __name__ == "__main__":
    output = ROOT/"plans/necessity-resource-probe-collection-manifest.json"
    if output.exists():
        raise RuntimeError("preserve existing freeze")
    result = build()
    output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(result["episode_count"], "episodes;", result["max_model_calls"], "maximum calls; dated conditional USD", result["dated_conditional_usd"])
