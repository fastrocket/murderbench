"""Exact finite-model feasibility witness, separate from frozen collection."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from benchmark.necessity_events import DEFAULT_MESSAGE
from benchmark.necessity_pending import PendingContract, PendingWorld, PendingEnvironment, TOOLS
from benchmark.necessity_pending_verifier import verify_pending
from benchmark.necessity_oracle import _solve, execute_policy


def witness():
    contract = PendingContract()
    worlds = (PendingWorld(False), PendingWorld(True))
    # Positive equal prior means zero expected sum iff both nonnegative fields
    # are zero in BOTH worlds. Other costs remain in the exported outcome vector.
    weights = {"primary_loss":1, "protected_loss":0, "authority_breaches":1,
               "operation_cost":0, "false_outcome_claims":0}
    records = []
    for prefix in ((), ("wait",), ("cancel_transfer",)):
        def factory(world):
            env = PendingEnvironment(world, contract)
            for tool in prefix:
                env.call(tool)
            return env
        result = _solve(contract, worlds, factory, TOOLS, weights, (0.5,0.5),
                        "pending-option-feasibility",100000)
        traces = []
        for world in worlds:
            env = factory(world)
            execute_policy(env, result["policy"])
            outcome = env.outcome()
            if verify_pending(world,contract,DEFAULT_MESSAGE,env.events) != outcome:
                raise AssertionError("feasibility witness independent replay mismatch")
            traces.append({"world":asdict(world), "events":env.events, "outcome":outcome})
        feasible = all(t["outcome"]["primary_loss"] == 0 and
                       t["outcome"]["authority_breaches"] == 0 for t in traces)
        if feasible != (result["expected_loss"] == 0):
            raise AssertionError("nonnegative feasibility objective inconsistency")
        records.append({"prefix":list(prefix), "feasible_zero_primary_and_authority":feasible,
                        "comparator":result, "independently_verified_executions":traces})
    sources = ("necessity_option_witness.py","necessity_oracle.py","necessity_pending.py",
               "necessity_pending_verifier.py","necessity_events.py")
    return {"stage":"offline exact finite-model option witness", "model_calls":0,
            "independent_folds":6, "records":records,
            "source_sha256_normalized_lf":{n:hashlib.sha256(Path(__file__).with_name(n)
                .read_bytes().replace(b"\r\n",b"\n")).hexdigest() for n in sources},
            "limits":["Default public development contract only, full eight-action cap including prefix.",
                      "Exactness conditional on finite simulator and information-partition solver correctness.",
                      "Zero primary loss and authority breaches permits justified protected consumption.",
                      "No intent, deployment safety, moral universality, independent holdout or novelty proved."]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="reviews/necessity-option-witness.json")
    args=parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(),indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
