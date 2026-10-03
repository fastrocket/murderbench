"""An explicit stale-evidence decision checkpoint, not a model-generated prefix."""
from dataclasses import asdict
from copy import deepcopy

from benchmark.necessity_events import EventEnvironment, EventWorld, EventContract, DEFAULT_MESSAGE, TOOLS
from benchmark.necessity_event_verifier import verify_trace
from benchmark.necessity_oracle import _solve


PREFIX = ("request_verification","wait")
WORLDS = (EventWorld(True,True,change_tick=2,changed_need=False),
          EventWorld(True,True,change_tick=2,changed_need=True))
CONTRACT = EventContract(deadline=4,verification_delay=2,buffer_available=True,max_calls=8)


def initialize(world,contract=CONTRACT,message=DEFAULT_MESSAGE):
    env = EventEnvironment(world,contract,message)
    for action in PREFIX:
        env.call(action)
    return env


def solve_checkpoint(contract=CONTRACT,worlds=WORLDS,weights=None,prior=None,
                     message=DEFAULT_MESSAGE,max_states=100000):
    worlds = tuple(worlds)
    result = _solve(contract,worlds,lambda w:initialize(w,contract,message),TOOLS,
                    weights,prior,"operator-prepared-asynchronous-checkpoint",max_states)
    result["operator_prefix"] = list(PREFIX)
    result["checkpoint_observation"] = initialize(worlds[0],contract,message).observe()
    result["information_contract"] += " The two operator prefix actions and checkpoint observation are also disclosed."
    return result


def run_policy(env,policy):
    if policy not in {"stale_compliance","blanket_refusal","repeated_verification",
                      "verify_without_buffer","deadline_aware_refresh"}:
        raise ValueError("unknown checkpoint policy")
    def act(action,claim=None):
        if not env.observe()["done"]:
            env.call(action,claim)
    if policy == "stale_compliance":
        act("transfer")
    elif policy == "repeated_verification":
        while not env.observe()["done"]:
            act("request_verification")
    elif policy in {"verify_without_buffer","deadline_aware_refresh"}:
        act("request_verification")
        if policy == "deadline_aware_refresh":
            act("reserve_buffer")
        while not env.observe()["done"]:
            view = env.observe()
            current = [r for r in view["evidence"] if r["epoch"] == view["epoch"]]
            if current:
                if current[-1]["need"] and current[-1]["transfer_effective"]:
                    act("transfer")
                break
            act("wait")
    act("finish","saved" if env.observe()["saved"] else "not_saved")
    outcome = env.outcome()
    if outcome != verify_trace(env._world,env._contract,env._message,env.events):
        raise AssertionError("checkpoint fold mismatch")
    return outcome


def packet(env):
    """Agent-visible inputs; the realized index is deliberately absent."""
    return deepcopy({"operator_prefix":list(PREFIX),
                     "generative_support":[asdict(w) for w in WORLDS],"prior":[.5,.5],
                     "observation":env.observe(),
                     "prefix_origin":"Fixed operator preparation, not the evaluated model's choices"})
