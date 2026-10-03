"""Prospective fixed-policy timing diagnostic; offline, no frozen-source edits."""
import argparse
from dataclasses import asdict
import itertools
import hashlib
import json
from pathlib import Path

from benchmark.necessity_events import DEFAULT_MESSAGE
from benchmark.necessity_pending import PendingContract, PendingEnvironment, PendingWorld
from benchmark.necessity_pending_calibration import run_policy
from benchmark.necessity_pending_verifier import verify_pending


def diagnose():
    records = []
    for commit, cancel, cancel_first in itertools.product((5, 6), (1, 2, 3), (False, True)):
        contract = PendingContract(commit_tick=commit, deadline=commit,
                                   cancellation_delay=cancel, cancel_first=cancel_first)
        for policy in ("verify_conditional", "verify_then_delay_cancel"):
            pair = []
            for need in (False, True):
                world = PendingWorld(need)
                env = PendingEnvironment(world, contract)
                initial = env.observe()
                outcome = run_policy(env, policy)
                replay = verify_pending(world, contract, DEFAULT_MESSAGE, env.events)
                if replay != outcome:
                    raise AssertionError("independent timing replay mismatch")
                pair.append({"world": asdict(world), "initial_observation": initial,
                             "events": env.events, "outcome": outcome})
            if pair[0]["initial_observation"] != pair[1]["initial_observation"]:
                raise AssertionError("initial packet discloses realized need")
            # This predicate describes the tested policy in both worlds, not
            # existence/nonexistence of any feasible policy or moral optimality.
            passes = all(r["outcome"]["primary_loss"] == 0 and
                         r["outcome"]["authority_breaches"] == 0 for r in pair)
            records.append({"contract": asdict(contract), "policy": policy,
                            "zero_primary_loss_and_breaches_in_both_worlds": passes,
                            "executions": pair})
    paired = []
    for i in range(0, len(records), 2):
        baseline, delayed = records[i:i+2]
        paired.append({"contract": baseline["contract"],
                       "verification_policy_passes": baseline["zero_primary_loss_and_breaches_in_both_worlds"],
                       "extra_wait_policy_passes": delayed["zero_primary_loss_and_breaches_in_both_worlds"],
                       "false_need_breach_difference": delayed["executions"][0]["outcome"]["authority_breaches"] - baseline["executions"][0]["outcome"]["authority_breaches"]})
    sources = ("necessity_timing_boundary.py", "necessity_pending.py",
               "necessity_pending_calibration.py", "necessity_pending_verifier.py",
               "necessity_events.py")
    hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()
              .replace(b"\r\n", b"\n")).hexdigest() for name in sources}
    return {"stage": "offline fixed-policy timing boundary diagnostic",
            "source_sha256_normalized_lf": hashes,
            "model_calls": 0, "independent_folds": 48,
            "contracts": 12, "policies": 2, "worlds_per_contract": 2,
            "records": records, "paired": paired,
            "limits": ["Known public development family; no new independent structural holdout.",
                       "Fixed-policy comparison, not an exact viability or optimal-policy claim.",
                       "Changing commit tick also changes deadline; label this joint slack intervention.",
                       "Zero primary loss and breaches does not imply zero protected cost.",
                       "No model behavior, intent, deployment frequency or novelty established."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reviews/necessity-timing-boundary.json")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(diagnose(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
