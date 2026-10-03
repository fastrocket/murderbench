"""Recompute conditional estimates from a saved public catalog, without network."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTION_ORDER = ["openai/gpt-6-astra", "anthropic/claude-opus-5.5",
                    "google/gemini-3.1-pro-preview", "x-ai/grok-4.7",
                    "deepseek/deepseek-v4-pro-0813", "qwen/qwen3.8-2.4t-a95b",
                    "moonshotai/kimi-k3", "z-ai/glm-5.3"]


def estimate():
    source = ROOT / "plans/necessity-pricing-snapshot.json"
    raw = source.read_bytes()
    snapshot = json.loads(raw)
    rows = []
    for model in snapshot["models"]:
        # Long-context surcharges cannot apply under this declared input cap.
        # Time-of-day overrides can, so retain their most expensive rate.
        applicable = [p for p in model["pricing"].get("overrides", [])
                      if p.get("min_prompt_tokens", 0) <= 4096]
        prices = [model["pricing"], *applicable]
        prompt = max(Decimal(p.get("prompt", model["pricing"]["prompt"])) for p in prices)
        completion = max(Decimal(p.get("completion", model["pricing"]["completion"])) for p in prices)
        per_turn = prompt * 4096 + completion * 1024
        rows.append({"route": model["id"], "input_per_million_usd": str(prompt*1000000),
                     "output_per_million_usd": str(completion*1000000),
                     "estimated_six_turn_episode_usd": str(per_turn*6),
                     "full_one_arm_384_episodes_usd": str(per_turn*6*384)})
    total = sum(Decimal(r["full_one_arm_384_episodes_usd"]) for r in rows)
    pilot_routes = {"openai/gpt-6-astra", "anthropic/claude-opus-5.5"}
    pilot = sum(Decimal(r["estimated_six_turn_episode_usd"])*14 for r in rows if r["route"] in pilot_routes)
    return {"status": "conditional-price-plan-not-collection-authorization",
            "collection_order": COLLECTION_ORDER,
            "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
            "snapshot_date": snapshot["retrieved"], "source": snapshot["source"],
            "assumptions": {"input_tokens_per_turn": 4096, "all_billed_output_tokens_per_turn": 1024,
                            "max_model_turns_per_episode": 6,
                            "retry_attempts": 0, "cache_discount": 0,
                            "provider_endpoint_eligibility_verified": False,
                            "hard_token_bounds_implemented": False,
                            "fees_images_search_and_external_tools": "excluded; tools must be simulator-only"},
            "routes": rows, "full_one_procedure_arm_3072_episodes_usd": str(total),
            "full_two_procedure_arms_usd": str(total*2),
            "development_pilot": {"cases": 7, "routes": sorted(pilot_routes),
                                  "procedure_arms": 2, "repetitions": 1,
                                  "episodes": 28, "max_calls": 168,
                                  "estimated_usd": str(pilot),
                                  "proposed_hard_cap_usd": "12.00",
                                  "approved_new_budget_usd": "0.00"},
            "collection_ready": False}


def main():
    result = estimate()
    path = ROOT / "plans/necessity-priced-collection.json"
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "routes"}, indent=2))


if __name__ == "__main__":
    main()
