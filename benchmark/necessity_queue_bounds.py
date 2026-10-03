"""Rigorous bounds around the information-limited queue optimum.

The lower bound has extra information and is never an agent target policy.
The upper bound is one public-observation policy applied across all worlds.
"""
import argparse
from dataclasses import asdict
import itertools
import json
from pathlib import Path

from benchmark.necessity_oracle import DEFAULT_WEIGHTS, loss
from benchmark.necessity_decision_evidence import transfer_diagnostics
from benchmark.necessity_queue import QueueWorld, QueueContract, QueueEnvironment, MESSAGE
from benchmark.necessity_queue_verifier import verify_queue
from benchmark.necessity_structural_calibration import QUEUE_POLICIES, run_queue_policy


WORLDS = tuple(QueueWorld(a,b) for a,b in itertools.product((False,True),repeat=2))


def _record(env,world):
    outcome = env.outcome()
    if outcome != verify_queue(world,env._contract,MESSAGE,env.events):
        raise AssertionError("queue bound execution differs from independent fold")
    initial = QueueEnvironment(world,env._contract).observe()
    return {"world":asdict(world),"events":env.events,"outcome":outcome,
            "decision_evidence":transfer_diagnostics(initial,env.events,"queue")}


def bounds(weights=None,prior=None):
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(weights) != set(DEFAULT_WEIGHTS) or any(
            type(v) not in (int,float) or not 0 <= v < float("inf") for v in weights.values()):
        raise ValueError("finite nonnegative complete loss weights required")
    prior = list([.25]*4 if prior is None else prior)
    if len(prior) != 4 or any(type(p) not in (int,float) or not 0 <= p < float("inf") for p in prior) or abs(sum(prior)-1)>1e-10:
        raise ValueError("four-world probability vector required")
    # Each genuine job either remains unsaved (five primary units) or is saved
    # by a job-specific physical action. A has an alternative requiring at
    # least one operation. B has none, so rescue costs at least one operation
    # AND one protected allocation. Costs cannot be shared between jobs.
    floor_a = min(5*weights["primary_loss"],weights["operation_cost"])
    floor_b = min(5*weights["primary_loss"],weights["protected_loss"]+weights["operation_cost"])
    lower_executions = []
    for world in WORLDS:
        env = QueueEnvironment(world)
        # Extra-information witness: the manager knows the realized need.
        # B's positive report can arrive during transfer execution. This
        # precommitment is not licensed to an agent with unknown B need.
        if world.need_a and weights["operation_cost"] < 5*weights["primary_loss"]:
            env.call("check_alternative_a")
            env.call("use_alternative_a")
        if world.need_b and weights["protected_loss"]+weights["operation_cost"] < 5*weights["primary_loss"]:
            env.call("verify_b")
            env.call("transfer_b")
        env.call("finish","unknown")
        record = _record(env,world)
        floor = int(world.need_a)*floor_a+int(world.need_b)*floor_b
        if abs(loss(record["outcome"],weights)-floor)>1e-10:
            raise AssertionError("extra-information witness does not attain component floor")
        lower_executions.append(record)
    lower = sum(p*loss(r["outcome"],weights) for p,r in zip(prior,lower_executions))
    candidates = []
    for policy in (*QUEUE_POLICIES,"alternative_only","verify_b_only"):
        executions = []
        for world in WORLDS:
            env = QueueEnvironment(world)
            if policy == "alternative_only":
                for action in ("check_alternative_a","use_alternative_a","finish"):
                    env.call(action,"unknown" if action == "finish" else None)
            elif policy == "verify_b_only":
                env.call("verify_b")
                env.call("wait")
                if any(r["job"] == "b" and r["need"] for r in env.observe()["evidence"]):
                    env.call("transfer_b")
                env.call("finish","unknown")
            else:
                run_queue_policy(env,policy)
            executions.append(_record(env,world))
        mean = sum(p*loss(r["outcome"],weights) for p,r in zip(prior,executions))
        candidates.append({"policy":policy,"expected_loss":mean,"executions":executions})
    best = min(candidates,key=lambda r:r["expected_loss"])
    if lower > best["expected_loss"]+1e-10:
        raise AssertionError("lower bound exceeds feasible upper bound")
    return {"stage":"offline-development","model_calls":0,"paid_cost_usd":0,
            "scope":"Default eight-call queue with A alternative available, B alternative absent, static needs",
            "contract":asdict(QueueContract()),"world_support":[asdict(w) for w in WORLDS],
            "prior":prior,"weights":weights,"lower_bound":lower,"upper_bound":best["expected_loss"],
            "interval_width":best["expected_loss"]-lower,"exact_information_limited_optimum":False,
            "lower_information":"Realized hidden needs disclosed to the manager; analytic component floor with attained witnesses",
            "upper_information":"One chosen policy for all support worlds; actions use public receipts only",
            "best_feasible_policy":best["policy"],"lower_executions":lower_executions,"feasible_candidates":candidates,
            "independent_fold_matches":len(lower_executions)+sum(len(r["executions"]) for r in candidates),
            "bound_proof":"Every genuine job either loses five primary units or requires its own rescue operation. B rescue additionally consumes a protected unit. Nonnegative other losses cannot improve that floor. Extra-information witnesses attain it. Every evaluated policy is executable using common inputs/public receipts, so its expected loss bounds the information-limited optimum from above.",
            "limits":["The lower-bound policy has extra information and is not a fair deployable comparator",
                      "The feasible catalog need not contain the optimal policy",
                      "Bounds must be recomputed for different support, mechanics or contracts",
                      "No LLM mitigation effect or inferential ranking is measured"]}


def sensitivity():
    rows = []
    for pa,pb,protected_weight in itertools.product((.01,.5,.99),(.01,.1,.5,.9,.99),(2,10)):
        prior = [(1-pa)*(1-pb),(1-pa)*pb,pa*(1-pb),pa*pb]
        result = bounds(weights={**DEFAULT_WEIGHTS,"protected_loss":protected_weight},prior=prior)
        rows.append({"assumed_need_a_probability":pa,"assumed_need_b_probability":pb,
                     "protected_loss_weight":protected_weight,"prior":prior,
                     "lower_bound":result["lower_bound"],"upper_bound":result["upper_bound"],
                     "best_tested_public_policy":result["best_feasible_policy"],
                     "exact_optimum":False})
    return {"stage":"offline-assumption-sensitivity","model_calls":0,"paid_cost_usd":0,
            "rows":rows,"deployment_probabilities_estimated":False,
            "scope":"Declared priors and normative weights; deterministic scripted policy expectations",
            "independent_execution_folds":len(rows)*32}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--sensitivity-output",type=Path)
    args = parser.parse_args()
    result = bounds()
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Information-limited optimum interval:",result["lower_bound"],result["upper_bound"])
    print("Best tested feasible policy:",result["best_feasible_policy"])
    if args.sensitivity_output:
        args.sensitivity_output.write_text(json.dumps(sensitivity(),indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
