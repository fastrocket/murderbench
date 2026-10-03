"""Public endpoint eligibility and conditional prices; no billable requests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import urllib.request

from benchmark.necessity_native import ROOT, legacy_accounted, amount


ROUTES = (
    ("openai/gpt-6-astra","openai"),
    ("anthropic/claude-opus-5.5","azure/global"),
    ("google/gemini-3.1-pro-preview","google-ai-studio"),
    ("x-ai/grok-4.7","xai"),
    ("deepseek/deepseek-v4-pro-0813","phala"),
    ("qwen/qwen3.8-2.4t-a95b","novita"),
    ("moonshotai/kimi-k3","morph/fp8"),
    ("z-ai/glm-5.3","phala"),
)


def fetch(route):
    model,tag = route
    url = "https://openrouter.ai/api/v1/models/"+model+"/endpoints"
    with urllib.request.urlopen(url,timeout=30) as response:
        data = json.load(response)["data"]
    endpoint = next((e for e in data["endpoints"] if e["tag"] == tag),None)
    if endpoint is None:
        return {"model":model,"provider_tag":tag,"source":url,"status":"endpoint_unavailable"}
    supported = set(endpoint.get("supported_parameters",[]))
    required = {"tools","tool_choice","max_tokens","reasoning"}
    parameters_available = required <= supported and endpoint.get("supports_tool_choice",{}).get("auto") is True
    pricing = endpoint["pricing"]
    prices = [pricing,*pricing.get("overrides",[])]
    # Retain all surcharge overrides; the input byte gate is not a token proof.
    prompt = max(Decimal(p.get("prompt",pricing["prompt"])) for p in prices)
    completion = max(Decimal(p.get("completion",pricing["completion"])) for p in prices)
    per_turn = prompt*20000+completion*4096
    return {"model":model,"provider_tag":tag,"provider_name":endpoint["provider_name"],
            "source":url,"status":"public_parameters_available" if parameters_available else "parameter_gap",
            "endpoint":endpoint,"conditional_input_rate_per_million_usd":str(prompt*1000000),
            "conditional_output_rate_per_million_usd":str(completion*1000000),
            "conditional_20000_input_4096_output_per_turn_usd":str(per_turn),
            "conditional_eight_turn_episode_usd":str(per_turn*8),
            "private_key_access_verified_here":False,"actual_native_queue_adapter_verified_here":False,
            "returned_checkpoint_identity_verified_here":False}


def plan():
    with ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(fetch,ROUTES))
    native = ROOT/"private/necessity-native.sqlite"
    extra = Decimal(0)
    if native.exists():
        with closing(sqlite3.connect(native.resolve().as_uri()+"?mode=ro",uri=True)) as conn:
            extra = sum((amount(r[0]) for r in conn.execute("SELECT amount FROM calls")),Decimal(0))
    total = legacy_accounted()+extra
    matrix = {"status":"reference_matrix_not_frozen_cases_or_powered_study","templates":12,
              "worlds_per_template":4,"procedure_arms":2,"routes":8,"repetitions":1,
              "episodes":768,"max_model_turns":6144}
    costs_available = len(rows)==8 and all("conditional_eight_turn_episode_usd" in r for r in rows)
    conditional = sum(Decimal(r["conditional_eight_turn_episode_usd"])*96 for r in rows) if costs_available else None
    return {"stage":"prospective-routing-and-price-review","retrieved_utc":datetime.now(timezone.utc).isoformat(),
            "new_model_calls":0,"new_paid_cost_usd":0,"collection_order":[r[0] for r in ROUTES],
            "routes":rows,"reference_matrix":matrix,
            "conditional_reference_matrix_usd":str(conditional) if conditional is not None else None,
            "original_lifetime_cap_usd":"50","current_accounted_usd":str(total),
            "remaining_accounted_usd":str(max(Decimal(0),Decimal(50)-total)),
            "new_budget_approved_usd":"0","collection_ready":False,
            "assumptions":{"input_tokens_per_turn":20000,"billed_output_tokens_per_turn":4096,
                           "turns_per_episode":8,"cache_discount":0,"retries":0,
                           "all_price_overrides_retained":True,"images_search_request_fees":"excluded",
                           "input_byte_gate_is_token_bound":False},
            "limits":["Public endpoint support is not an authenticated native-interface probe",
                      "Prices are conditional token arithmetic, not a cost guarantee or collection authorization",
                      "Reference matrix must be replaced with frozen per-template worlds and arm counts",
                      "Current $50 authorization includes all unresolved reservations",
                      "No model rankings or open-checkpoint equivalence follow from hosted routes"]}


if __name__ == "__main__":
    result = plan()
    path = ROOT/"plans/necessity-structural-route-plan.json"
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    for row in result["routes"]:
        print(row["model"],row["status"])
    print("Conditional reference matrix USD:",result["conditional_reference_matrix_usd"])
    print("Remaining original authorization USD:",result["remaining_accounted_usd"])
