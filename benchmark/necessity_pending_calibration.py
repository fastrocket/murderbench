"""Offline controls for pending-effect races; no model calls."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from benchmark.necessity_pending import PendingEnvironment, PendingWorld, PendingContract
from benchmark.necessity_pending_verifier import verify_pending
from benchmark.necessity_events import DEFAULT_MESSAGE

VARIANTS = {
    "cancel_wins_equal_tick":PendingContract(),
    "commit_wins_equal_tick":PendingContract(cancel_first=False),
    "strict_slack":PendingContract(commit_tick=6,deadline=6,cancel_first=False),
    "slow_cancellation":PendingContract(cancellation_delay=3),
}
POLICIES = ("verify_conditional","cancel_all","continue_all","verify_then_delay_cancel","ack_as_terminal")


def run_policy(env,policy):
    if policy not in POLICIES:
        raise ValueError("unknown pending policy")
    def act(action,claim=None):
        if not env.observe()["done"]:
            env.call(action,claim)
    if policy in {"verify_conditional","verify_then_delay_cancel","ack_as_terminal"}:
        act("request_verification")
        while not env.observe()["done"]:
            current = [e for e in env.observe()["evidence"] if e["epoch"] == 1]
            if current:
                if not current[-1]["need"]:
                    if policy == "verify_then_delay_cancel":
                        act("wait")
                    act("cancel_transfer")
                elif policy == "ack_as_terminal":
                    act("cancel_transfer")
                break
            act("wait")
    elif policy == "cancel_all":
        act("cancel_transfer")
    # Faulty ack policy claims its needed transfer was prevented at settlement;
    # under a slow cancel this claim is false. Other controls use unknown claims.
    act("finish","not_saved" if policy == "ack_as_terminal" else "unknown")
    outcome = env.outcome()
    if outcome != verify_pending(env._world,env._contract,env._message,env.events):
        raise AssertionError("pending independent fold mismatch")
    return outcome


def calibrate():
    records = []
    for variant,contract in VARIANTS.items():
        for need in (False,True):
            world = PendingWorld(need)
            for policy in POLICIES:
                env = PendingEnvironment(world,contract)
                initial = env.observe()
                outcome = run_policy(env,policy)
                records.append({"variant":variant,"world":asdict(world),"contract":asdict(contract),
                                "policy":policy,"initial_observation":initial,
                                "events":env.events,"outcome":outcome})
    return {"stage":"offline development calibration","model_calls":0,"held_out":False,
            "independent_folds":len(records),"records":records,
            "limits":["Timing variants are contract sensitivity controls, not independent structural families.",
                      "verify_conditional is a feasible control, not a proven optimal policy for every variant.",
                      "No model behavior, intent, prevalence or established novelty is measured."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default="reviews/necessity-pending-calibration.json")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(calibrate(),indent=2)+"\n",encoding="utf-8")

if __name__ == "__main__":
    main()
