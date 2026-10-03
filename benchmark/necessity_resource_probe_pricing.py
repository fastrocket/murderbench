"""Conditional repricing of preserved matrices from an unbilled public snapshot."""
from collections import Counter
from decimal import Decimal
import hashlib
from benchmark.necessity_native import canonical


def price(manifests, snapshot):
    routes = {r["model"]:r for r in snapshot["routes"]}
    if len(routes) != len(snapshot["routes"]):
        raise ValueError("duplicate routes")
    studies, total = [], Decimal(0)
    for manifest in manifests:
        contents = {k:v for k,v in manifest.items() if k != "manifest_sha256"}
        if hashlib.sha256(canonical(contents).encode()).hexdigest() != manifest["manifest_sha256"]:
            raise ValueError("manifest integrity mismatch")
        calls = Counter()
        for row in manifest["episodes"]:
            route = routes[row["model"]]
            if route["provider_tag"] != row["provider_tag"] or route["status"] != "public_parameters_available":
                raise ValueError("route unavailable or changed")
            calls[row["model"]] += row["max_calls"]
        if set(calls) != set(routes):
            raise ValueError("route set mismatch")
        costs = [{"model":model, "max_calls":count,
                  "conditional_usd":str(Decimal(routes[model]["conditional_20000_input_4096_output_per_turn_usd"])*count)}
                 for model, count in calls.items()]
        subtotal = sum(Decimal(r["conditional_usd"]) for r in costs)
        total += subtotal
        studies.append({"manifest_sha256":manifest["manifest_sha256"], "episodes":len(manifest["episodes"]),
                        "max_calls":sum(calls.values()), "routes":costs, "conditional_usd":str(subtotal)})
    accounted = Decimal(snapshot["current_accounted_usd"])
    remaining = Decimal(snapshot["remaining_accounted_usd"])
    return {"stage":"conditional_reprice_no_collection_authorization", "studies":studies,
            "snapshot_sha256":hashlib.sha256(canonical(snapshot).encode()).hexdigest(),
            "retrieved_utc":snapshot["retrieved_utc"], "future_conditional_usd":str(total),
            "current_accounted_usd":str(accounted), "remaining_authorized_usd":str(remaining),
            "conditional_lifetime_total_usd":str(accounted+total),
            "conditional_shortfall_usd":str(max(Decimal(0), total-remaining)),
            "new_model_calls":0, "collection_ready":False,
            "limits":["Conditional token arithmetic, not a price cap or billing guarantee.",
                      "Assumes 20000 input and4096 billed output tokens per turn; byte gate is not a token proof.",
                      "No retries, cache discounts or additional request/image/search fees included.",
                      "Public parameter availability does not prove private native action access.",
                      "Existing reservations remain accounted; no extra spending approved."]}
