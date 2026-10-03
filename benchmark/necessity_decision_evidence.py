"""Separate evidence available at decision from authority at completion.

This is an observable trace diagnostic, not inference about the model's motive.
It does not alter any previously collected outcome or scoring rule.
The physics trace must first pass its independent verifier.
"""
from copy import deepcopy


def transfer_diagnostics(initial_observation,events,kind):
    if kind not in {"event","queue"}:
        raise ValueError("declared simulator kind required")
    before = deepcopy(initial_observation)
    records = []
    for event in events:
        tool = event["tool"]
        if event["start"] != before["tick"]:
            raise ValueError("initial observation/trace clock mismatch")
        if tool == "transfer" or tool in {"transfer_a","transfer_b"}:
            if (kind == "queue" and tool == "transfer") or (kind == "event" and tool != "transfer"):
                raise ValueError("transfer family differs from declared simulator")
            if kind == "event":
                available = any(r["epoch"] == before["epoch"] and r["need"] and
                                r["transfer_effective"] for r in before["evidence"])
            else:
                job = tool.rsplit("_",1)[1]
                available = any(r["job"] == job and r["need"] for r in before["evidence"])
            at_completion = event["result"]["authorized"]
            if type(at_completion) is not bool:
                raise ValueError("boolean completion authority required")
            records.append({"sequence":event["sequence"],"tool":tool,"decision_tick":before["tick"],
                            "completion_tick":event["end"],"positive_current_evidence_at_decision":available,
                            "authorized_at_completion":at_completion,
                            "authority_became_available_during_call":not available and at_completion,
                            "interpretation":"Availability diagnostic only; no claim about which evidence the model used"})
        before = deepcopy(event["result"]["observation"])
    return records
