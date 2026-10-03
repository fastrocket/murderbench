"""Exact public-information pending-effect comparators at the full call horizon."""
import argparse
import json
from pathlib import Path
from dataclasses import asdict
from benchmark.necessity_pending import PendingEnvironment, PendingWorld, TOOLS
from benchmark.necessity_pending_calibration import VARIANTS
from benchmark.necessity_pending_verifier import verify_pending
from benchmark.necessity_oracle import _solve, execute_policy
from benchmark.necessity_events import DEFAULT_MESSAGE


def compare():
    results = []
    worlds = (PendingWorld(False),PendingWorld(True))
    for name,contract in VARIANTS.items():
        comparator = _solve(contract,worlds,lambda w:PendingEnvironment(w,contract),
                            TOOLS,None,None,"pending-commit",100000)
        records = []
        for world in worlds:
            env = PendingEnvironment(world,contract)
            execute_policy(env,comparator["policy"])
            outcome = env.outcome()
            if outcome != verify_pending(world,contract,DEFAULT_MESSAGE,env.events):
                raise AssertionError("pending comparator independent fold mismatch")
            records.append({"world":asdict(world),"events":env.events,"outcome":outcome})
        results.append({"variant":name,"comparator":comparator,"executions":records})
    return {"stage":"offline exact information-limited comparison","model_calls":0,
            "independent_folds":8,"results":results,
            "limits":["Specified synthetic support, equal prior and declared loss weights only.",
                      "Optimality does not imply a unique morally appropriate policy.",
                      "A model must receive the same support and semantics; realized need remains hidden."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",default="reviews/necessity-pending-comparator.json")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(compare(),indent=2)+"\n",encoding="utf-8")

if __name__ == "__main__":
    main()
