"""Prospective text-only price-filter candidate; not wired to frozen collection."""
from benchmark.necessity_structural_native import payload_for


def text_only_payload(route,messages,names):
    # Do not relax an image price filter unless the actual request is text only.
    for message in messages:
        if type(message) is not dict or message.get("role") not in {"system","user","assistant","tool"}:
            raise ValueError("invalid text-only message")
        content=message.get("content")
        if type(content) is not str and not (content is None and message["role"]=="assistant"):
            raise ValueError("non-text content prohibited")
    packet=payload_for(route,messages,names)
    packet["provider"]["max_price"].pop("image")
    return packet
