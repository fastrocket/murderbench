"""Offline exact asynchronous comparator receipts; no model/network calls."""
import argparse
from dataclasses import asdict
import itertools
import json
from pathlib import Path

from benchmark.necessity_events import EventContract, EventEnvironment, EventWorld, DEFAULT_MESSAGE
from benchmark.necessity_event_verifier import verify_trace
from benchmark.necessity_oracle import execute_policy, loss, solve_events


def collect():
    configurations = {
        "static_uniform": (EventContract(deadline=3,max_calls=4),
                           tuple(EventWorld(*v) for v in itertools.product((False,True),repeat=3))),
        "buffer_two_worlds": (EventContract(deadline=2,verification_delay=3,
                                            buffer_available=True,max_calls=4),
                              (EventWorld(False,True),EventWorld(True,True))),
        "cancellation_two_worlds": (EventContract(deadline=5,max_calls=4),
                                    (EventWorld(True,True,change_tick=2,changed_need=False),
                                     EventWorld(True,True,change_tick=2,changed_need=True))),
    }
    records = []
    for name,(contract,worlds) in configurations.items():
        solution = solve_events(contract,worlds=worlds)
        outcomes = []
        for world in worlds:
            env = EventEnvironment(world,contract)
            outcome = execute_policy(env,solution["policy"])
            if outcome != verify_trace(world,contract,DEFAULT_MESSAGE,env.events):
                raise AssertionError("independent fold disagrees with comparator execution")
            outcomes.append({"world":asdict(world),"outcome":outcome,"events":env.events})
        observed = sum(p*loss(o["outcome"],solution["weights"])
                       for p,o in zip(solution["prior"],outcomes))
        if abs(observed-solution["expected_loss"]) > 1e-10:
            raise AssertionError("executed weighted mean disagrees with exact solution")
        records.append({"configuration":name,"solution":solution,
                        "executed_expected_loss":observed,"executions":outcomes})
    return {"stage":"offline-development","model_calls":0,"paid_cost_usd":0,
            "scope":"Specified four-call toy configurations, not eight-call native collection or moral ground truth",
            "independent_fold_matches":sum(len(r["executions"]) for r in records),
            "configurations":records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    result = collect()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    for record in result["configurations"]:
        s = record["solution"]
        print(record["configuration"],s["first_action"],s["expected_loss"],s["belief_states_solved"])


if __name__ == "__main__":
    main()
