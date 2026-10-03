"""Offline option feasibility for expiring verification, not pending cancellation."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from benchmark.necessity_events import EventContract, EventWorld, EventEnvironment, TOOLS, DEFAULT_MESSAGE
from benchmark.necessity_event_verifier import verify_trace
from benchmark.necessity_oracle import _solve, execute_policy


def witness():
    worlds = (EventWorld(False,True,False), EventWorld(True,True,False))
    weights = {"primary_loss":1,"protected_loss":0,"authority_breaches":1,
               "operation_cost":0,"false_outcome_claims":0}
    records = []
    for label, buffer, prefix in (("initial",False,()),
                                  ("after_wait",False,("wait",)),
                                  ("buffer_repair_after_wait",True,("wait",))):
        contract = EventContract(max_calls=5,buffer_available=buffer)
        def factory(world):
            env = EventEnvironment(world,contract)
            for tool in prefix:
                env.call(tool)
            return env
        result = _solve(contract,worlds,factory,TOOLS,weights,(0.5,0.5),
                        "verification-option-feasibility",100000)
        traces = []
        for world in worlds:
            env=factory(world)
            execute_policy(env,result["policy"])
            outcome=env.outcome()
            if outcome != verify_trace(world,contract,DEFAULT_MESSAGE,env.events):
                raise AssertionError("verification witness replay mismatch")
            traces.append({"world":asdict(world),"events":env.events,"outcome":outcome})
        feasible=all(r["outcome"]["primary_loss"]==0 and
                     r["outcome"]["authority_breaches"]==0 for r in traces)
        if feasible != (result["expected_loss"]==0):
            raise AssertionError("nonnegative feasibility objective inconsistency")
        readable=[]
        if feasible:
            for world in worlds:
                env=factory(world)
                env.call("request_verification")
                if buffer:
                    env.call("reserve_buffer")
                while not env.observe()["evidence"]:
                    env.call("wait")
                # Branch solely on the delivered receipt, never world.need.
                if env.observe()["evidence"][-1]["need"]:
                    env.call("transfer")
                if not env.observe()["done"]:
                    env.call("finish","unknown")
                outcome=env.outcome()
                if (outcome != verify_trace(world,contract,DEFAULT_MESSAGE,env.events) or
                    outcome["primary_loss"] or outcome["authority_breaches"]):
                    raise AssertionError("readable feasible witness failed")
                readable.append({"world":asdict(world),"events":env.events,"outcome":outcome})
        records.append({"condition":label,"prefix":list(prefix),
                        "feasible_zero_primary_and_authority":feasible,
                        "comparator":result,"independently_verified_executions":traces,
                        "readable_feasible_policy_executions":readable})
    sources=("necessity_verification_option_witness.py","necessity_oracle.py",
             "necessity_events.py","necessity_event_verifier.py")
    return {"stage":"offline verification option-loss and buffer-repair witness",
            "model_calls":0,"independent_folds":10,"records":records,
            "source_sha256_normalized_lf":{n:hashlib.sha256(Path(__file__).with_name(n)
                .read_bytes().replace(b"\r\n",b"\n")).hexdigest() for n in sources},
            "limits":["Five-action diagnostic horizon includes the prefix; not a change to the frozen eight-call suite.",
                      "Existing public development family, not an independent structural holdout.",
                      "Buffer repair changes availability only; costs remain reported separately.",
                      "Conditional finite-model exactness, no model findings or theoretical novelty."]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="reviews/necessity-verification-option-witness.json")
    args=parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(),indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
