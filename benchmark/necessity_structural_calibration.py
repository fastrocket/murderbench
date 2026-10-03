"""Offline checkpoint and queue controls. No model or adaptive attack findings."""
import argparse
from dataclasses import asdict
import itertools
import json
from pathlib import Path

from benchmark.necessity_checkpoint import CONTRACT, WORLDS, initialize, run_policy, solve_checkpoint
from benchmark.necessity_events import DEFAULT_MESSAGE, ATTACKS
from benchmark.necessity_oracle import execute_policy, loss
from benchmark.necessity_queue import QueueWorld, QueueContract, QueueEnvironment, MESSAGE
from benchmark.necessity_queue_verifier import verify_queue


QUEUE_POLICIES = {
    "blanket_refusal":("finish",),
    "verify_both_then_act":("verify_a","verify_b","transfer_a","transfer_b","finish"),
    "assume_parallel_verification":("verify_a","verify_b","transfer_b","transfer_a","finish"),
    "obey_urgency":("transfer_a","transfer_b","finish"),
    "alternative_and_buffer_schedule":("check_alternative_a","use_alternative_a","verify_b","reserve_buffer_b","transfer_b","finish"),
}


def run_queue_policy(env,policy):
    if policy not in QUEUE_POLICIES:
        raise ValueError("unknown queue policy")
    if policy == "verify_both_then_act":
        env.call("verify_a")
        env.call("verify_b")
        for job in ("a","b"):
            while not env.observe()["done"] and not any(r["job"] == job for r in env.observe()["evidence"]):
                env.call("wait")
            if not env.observe()["done"] and any(r["job"] == job and r["need"] for r in env.observe()["evidence"]):
                env.call("transfer_"+job)
        if not env.observe()["done"]:
            env.call("finish","unknown")
        return env.outcome()
    for action in QUEUE_POLICIES[policy]:
        if policy == "alternative_and_buffer_schedule" and action == "transfer_b":
            if not any(r["job"] == "b" and r["need"] for r in env.observe()["evidence"]):
                continue
        env.call(action,"unknown" if action == "finish" else None)
    return env.outcome()


def collect():
    checkpoint = []
    policies = ("stale_compliance","blanket_refusal","repeated_verification",
                "verify_without_buffer","deadline_aware_refresh")
    for world in WORLDS:
        for label,message in {"neutral":DEFAULT_MESSAGE,**ATTACKS}.items():
            for policy in policies:
                env = initialize(world,message=message)
                outcome = run_policy(env,policy)
                checkpoint.append({"world":asdict(world),"contract":asdict(CONTRACT),
                                   "message":message,"message_variant":label,"policy":policy,
                                   "operator_prefix_calls":2,"outcome":outcome,"events":env.events})
    solution = solve_checkpoint()
    executions = []
    for world in WORLDS:
        env = initialize(world)
        outcome = execute_policy(env,solution["policy"])
        from benchmark.necessity_event_verifier import verify_trace
        if outcome != verify_trace(world,CONTRACT,DEFAULT_MESSAGE,env.events):
            raise AssertionError("exact checkpoint policy fold mismatch")
        executions.append({"world":asdict(world),"outcome":outcome,"events":env.events})
    observed = sum(p*loss(r["outcome"],solution["weights"]) for p,r in zip(solution["prior"],executions))
    if abs(observed-solution["expected_loss"]) > 1e-10:
        raise AssertionError("checkpoint expectation mismatch")
    queues = []
    for need_a,need_b in itertools.product((False,True),repeat=2):
        world,contract = QueueWorld(need_a,need_b),QueueContract()
        for policy in QUEUE_POLICIES:
            env = QueueEnvironment(world,contract)
            outcome = run_queue_policy(env,policy)
            if outcome != verify_queue(world,contract,MESSAGE,env.events):
                raise AssertionError("independent queue fold mismatch")
            queues.append({"world":asdict(world),"contract":asdict(contract),"message":MESSAGE,
                           "policy":policy,"outcome":outcome,"events":env.events})
    return {"stage":"offline-structural-development","model_calls":0,"paid_cost_usd":0,
            "checkpoint_scripted_episodes":len(checkpoint),"queue_scripted_episodes":len(queues),
            "independent_scripted_fold_matches":len(checkpoint)+len(queues),
            "checkpoint":checkpoint,"queue":queues,
            "checkpoint_exact_comparator":{"solution":solution,"executions":executions},
            "queue_exact_comparator":False,"LLM_mitigation_effect_measured":False,
            "limits":["Fixed scripted controls, not model/attack outcomes",
                      "Shared-queue assumptions do not establish deployment validity",
                      "Queue reference policy is feasible under its support, not proved optimal",
                      "Development cases are not held-out templates"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    result = collect()
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Independent scripted folds:",result["independent_scripted_fold_matches"])
    print("Checkpoint comparator:",result["checkpoint_exact_comparator"]["solution"]["expected_loss"])


if __name__ == "__main__":
    main()
