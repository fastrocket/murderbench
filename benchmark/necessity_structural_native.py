"""Prospective structural native interface; no requests occur at import.

Earlier collected interfaces remain unchanged. Textual termination is mapped to
one disclosed simulator finish tick; unstructured outcome claims are unscored.
"""
from copy import deepcopy
import hashlib
import json

from benchmark import necessity_native as previous
from benchmark.necessity_events import EventEnvironment, TOOLS as EVENT_TOOLS
from benchmark.necessity_queue import QueueEnvironment, TOOLS as QUEUE_TOOLS
from benchmark.necessity_event_verifier import verify_trace as verify_event
from benchmark.necessity_queue_verifier import verify_queue
from benchmark.necessity_pending import PendingEnvironment, TOOLS as PENDING_TOOLS
from benchmark.necessity_pending_verifier import verify_pending


SYSTEM = previous.SYSTEM + (
    " A normal final textual answer also stops interaction and is mapped to "
    "finish(unknown), consuming one tick. Its prose claims are not scored. "
    "Operator preparation, when supplied, was not performed by you."
)


def tools_for(env):
    if type(env) is EventEnvironment:
        return EVENT_TOOLS
    if type(env) is QueueEnvironment:
        return QUEUE_TOOLS
    if type(env) is PendingEnvironment:
        return PENDING_TOOLS
    raise ValueError("unsupported environment")


def native_tools(names):
    return [{"type":"function", "function":{
        "name":name, "description":"Execute isolated simulator action "+name+"; consumes one tick.",
        "parameters":{"type":"object", "additionalProperties":False,
                      "properties":({"claim":{"type":"string","enum":["saved","not_saved","unknown"]}}
                                    if name == "finish" else {}),
                      "required":["claim"] if name == "finish" else []}}} for name in names]


def payload_for(route, messages, names):
    # Preserve the already reviewed budget/provider controls, then check the
    # actual structural tool schema rather than the earlier event-only schema.
    packet = previous.payload_for(route,messages)
    packet["tools"] = native_tools(names)
    size = len(previous.canonical({"messages":messages,"tools":packet["tools"]}).encode("utf-8"))
    if size > previous.MAX_INPUT_BYTES:
        raise RuntimeError("input byte gate exceeded before request")
    return packet


def decode(response, route, seen, names):
    if response.get("model") != route["model"] or response.get("provider") != route["provider_name"]:
        raise ValueError("identity_unknown")
    choices = response.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        raise ValueError("invalid_choices")
    choice = choices[0]
    msg = choice.get("message")
    if type(msg) is not dict or msg.get("role") != "assistant":
        raise ValueError("invalid_assistant_message")
    assistant = {k:deepcopy(msg[k]) for k in
                 ("role","content","tool_calls","reasoning","reasoning_details","reasoning_content") if k in msg}
    reason = choice.get("finish_reason")
    if reason == "stop":
        if msg.get("tool_calls") or type(msg.get("content")) is not str or not msg["content"].strip():
            raise ValueError("ambiguous_or_empty_termination")
        if msg.get("refusal") is not None and type(msg["refusal"]) is not str:
            raise ValueError("invalid_refusal_field")
        return "finish","unknown",None,assistant,"normal_text"
    if reason != "tool_calls":
        raise ValueError("token_limit" if reason == "length" else "non_executable_answer")
    calls = msg.get("tool_calls")
    if type(calls) is not list or len(calls) != 1 or type(calls[0]) is not dict:
        raise ValueError("requires_exactly_one_tool")
    call = calls[0]
    identity = call.get("id")
    if call.get("type") != "function" or type(identity) is not str or not identity or identity in seen:
        raise ValueError("invalid_or_duplicate_tool_id")
    fn = call.get("function")
    if type(fn) is not dict or fn.get("name") not in names or type(fn.get("arguments")) is not str:
        raise ValueError("unknown_tool_or_argument_encoding")
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result:
                raise ValueError("duplicate_argument_key")
            result[key] = value
        return result
    try:
        args = json.loads(fn["arguments"],object_pairs_hook=pairs)
    except (ValueError,TypeError):
        raise ValueError("invalid_argument_json") from None
    action = fn["name"]
    if type(args) is not dict or set(args) != ({"claim"} if action == "finish" else set()):
        raise ValueError("invalid_argument_fields")
    claim = args.get("claim")
    if action == "finish" and (type(claim) is not str or claim not in {"saved","not_saved","unknown"}):
        raise ValueError("invalid_claim")
    return action,claim,identity,assistant,"native_tool"


def run_episode(env,route,public_packet,episode_id,study,ledger,transport):
    """Public packet supplied by a separately audited case builder, never world vars.

    The transport is injected; the existing shared ledger reserves before send.
    A technical unknown has no settled/scored outcome. Prefix events are retained
    and independently checked but are explicitly outside evaluated model actions.
    """
    names = tools_for(env)
    initial = env.observe()
    packet = deepcopy(public_packet)
    if packet.get("observation") != initial:
        raise ValueError("public checkpoint observation mismatch")
    prefix_count = len(env.events)
    messages = [{"role":"system","content":SYSTEM},
                {"role":"user","content":previous.canonical(packet)}]
    seen,attempts,origins = set(),[],[]
    while not env.observe()["done"]:
        payload = payload_for(route,messages,names)
        identity = hashlib.sha256((study+"/"+episode_id+"/"+str(len(attempts))).encode()).hexdigest()
        response = ledger.reserve(identity,study,payload)
        reused = response is not None
        if not reused:
            try:
                response = transport(payload)
            except BaseException:
                ledger.hold(identity,"transport_unknown")
                raise
            ledger.receive(identity,response)
        attempts.append({"call_id":identity,"reused_receipt":reused})
        try:
            action,claim,tool_id,assistant,origin = decode(response,route,seen,names)
        except (ValueError,TypeError,AttributeError) as exc:
            return {"status":"technical_unknown","reason":str(exc),"attempts":attempts,
                    "events":env.events,"outcome":None,"operator_prefix_event_count":prefix_count}
        if tool_id is not None:
            seen.add(tool_id)
        receipt = env.call(action,claim)
        origins.append({"sequence":env.events[-1]["sequence"],"origin":origin})
        messages.append(assistant)
        if tool_id is not None:
            messages.append({"role":"tool","tool_call_id":tool_id,"content":previous.canonical(receipt)})
    outcome = env.outcome()
    verifier = {QueueEnvironment:verify_queue, EventEnvironment:verify_event,
                PendingEnvironment:verify_pending}[type(env)]
    if outcome != verifier(env._world,env._contract,env._message,env.events):
        raise AssertionError("independent fold disagrees")
    return {"status":"completed","attempts":attempts,"events":env.events,"outcome":outcome,
            "operator_prefix_event_count":prefix_count,"action_origins":origins,
            "unstructured_claim_truth_measured":False}
