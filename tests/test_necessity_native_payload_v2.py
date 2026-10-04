import unittest
from benchmark.necessity_native import MAX_INPUT_BYTES, NATIVE_TOOLS, canonical
from benchmark.necessity_structural_native import native_tools, payload_for as inherited
from benchmark.necessity_native_payload_v2 import payload_for
from benchmark.necessity_resource_probe import TOOLS
from tests.test_necessity_native import ROUTE


class SuppliedSchemaGateTests(unittest.TestCase):
    def test_does_not_reject_due_to_unrelated_larger_schema(self):
        messages = [{"role": "user", "content": ""}]
        overhead = len(canonical({"messages": messages, "tools": native_tools(TOOLS)}).encode())
        messages[0]["content"] = "x" * (MAX_INPUT_BYTES - overhead)
        self.assertEqual(len(canonical({"messages": messages, "tools": native_tools(TOOLS)}).encode()), MAX_INPUT_BYTES)
        self.assertGreater(len(canonical({"messages": messages, "tools": NATIVE_TOOLS}).encode()), MAX_INPUT_BYTES)
        with self.assertRaisesRegex(RuntimeError, "byte gate"):
            inherited(ROUTE, messages, TOOLS)
        packet = payload_for(ROUTE, messages, TOOLS)
        self.assertEqual(packet["tools"], native_tools(TOOLS))
        self.assertFalse(packet["provider"]["allow_fallbacks"])
        self.assertEqual(packet["provider"]["data_collection"], "deny")
        messages[0]["content"] += "x"
        with self.assertRaisesRegex(RuntimeError, "byte gate"):
            payload_for(ROUTE, messages, TOOLS)

    def test_identical_payload_for_in_bound_native_reasoning_history(self):
        messages = [{"role": "assistant", "reasoning_details": [{"type": "opaque", "data": "signature"}],
                     "reasoning": "retained", "content": None}]
        self.assertEqual(payload_for(ROUTE, messages, TOOLS), inherited(ROUTE, messages, TOOLS))
