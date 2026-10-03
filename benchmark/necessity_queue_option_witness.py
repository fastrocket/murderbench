"""Queue option witness and fault controls; analytical infeasibility, not solver."""
import argparse
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
from benchmark.necessity_queue import QueueWorld, QueueContract, QueueEnvironment, MESSAGE
from benchmark.necessity_queue_verifier import verify_queue


def witness():
    contract=QueueContract()
    records=[]
    initials=[]
    for a,b in itertools.product((False,True),repeat=2):
        world=QueueWorld(a,b)
        for policy in ("preserve_alternative_then_verify_b", "verify_a_then_recover", "always_transfer"):
            env=QueueEnvironment(world,contract)
            initials.append(env.observe())
            if policy=="preserve_alternative_then_verify_b":
                for tool in ("check_alternative_a","use_alternative_a","verify_b","reserve_buffer_b"):
                    env.call(tool)
            elif policy=="verify_a_then_recover":
                for tool in ("verify_a","reserve_buffer_a","verify_b","check_alternative_a","use_alternative_a"):
                    env.call(tool)
            else:
                env.call("transfer_a")
                env.call("transfer_b")
            if policy!="always_transfer":
                evidence=[r for r in env.observe()["evidence"] if r["job"]=="b"]
                if not evidence:
                    raise AssertionError("script assumes undelivered report")
                if evidence[-1]["need"]:
                    env.call("transfer_b")
            env.call("finish","unknown")
            outcome=env.outcome()
            if verify_queue(world,contract,MESSAGE,env.events)!=outcome:
                raise AssertionError("queue witness independent replay mismatch")
            records.append({"world":asdict(world),"policy":policy,"events":env.events,"outcome":outcome})
    if any(v!=initials[0] for v in initials):
        raise AssertionError("initial queue packet discloses hidden need")
    good=[r for r in records if r["policy"]=="preserve_alternative_then_verify_b"]
    if any(r["outcome"]["primary_loss"] or r["outcome"]["authority_breaches"] for r in good):
        raise AssertionError("common public policy does not establish root feasibility")
    sources=("necessity_queue_option_witness.py","necessity_queue.py","necessity_queue_verifier.py")
    return {"stage":"offline shared-verifier option witness and fault controls",
            "model_calls":0,"independent_folds":12,"contract":asdict(contract),"records":records,
            "root_feasibility":"Constructive common observation-policy witness across four worlds.",
            "after_verify_a_infeasibility":"Analytical timing argument in companion findings; no exact queue solver invoked.",
            "source_sha256_normalized_lf":{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()
                .replace(b"\r\n",b"\n")).hexdigest() for n in sources},
            "limits":["Public development family, not independent confirmation.",
                      "One failed scripted recovery is not alone an all-policy impossibility proof.",
                      "Protected and operation costs remain explicit; no universal moral ranking."]}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="reviews/necessity-queue-option-witness.json")
    args=p.parse_args();Path(args.output).write_text(json.dumps(witness(),indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
