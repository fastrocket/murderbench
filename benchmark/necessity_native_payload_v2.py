"""Future-study payload builder: check only the supplied schema, once.

Not used by the frozen matched pilot. Retains its provider/privacy/price settings
and native reasoning fields; a new study needs its own prospective source freeze.
"""
from copy import deepcopy

from benchmark import necessity_native as limits
from benchmark.necessity_structural_native import native_tools


def payload_for(route, messages, names):
    tools = native_tools(names)
    size = len(limits.canonical({"messages": messages, "tools": tools}).encode("utf-8"))
    if size > limits.MAX_INPUT_BYTES:
        raise RuntimeError("input byte gate exceeded before request")
    return {"model": route["model"], "messages": deepcopy(messages), "tools": tools,
            "tool_choice": "auto", "max_tokens": limits.MAX_OUTPUT,
            "reasoning": {"effort": "low", "exclude": False}, "usage": {"include": True},
            "provider": {"only": [route["provider"]], "allow_fallbacks": False,
                         "require_parameters": True, "data_collection": "deny",
                         "max_price": {"prompt": 20, "completion": 100, "request": 0, "image": 0}}}
