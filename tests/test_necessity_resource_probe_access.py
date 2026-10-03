import tempfile
from pathlib import Path
import unittest
from benchmark.necessity_native import Ledger
from benchmark.necessity_resource_probe_access import prepare, check_route


class ProbeAccessTests(unittest.TestCase):
    def check(self, transport):
        plan = prepare()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite", baseline=lambda:0, study_cap="2")
            try:
                return check_route(plan, plan["routes"][0], ledger, transport)
            finally:
                ledger.close()

    def test_exact_schema_and_conversation(self):
        sent = []
        route = prepare()["routes"][0]
        def transport(payload):
            sent.append(payload)
            turn = len(sent)
            names = {t["function"]["name"] for t in payload["tools"]}
            self.assertEqual(names, set(prepare()["tools"]))
            return {"model":route["model"], "provider":route["provider_name"], "usage":{"cost":0},
                    "choices":[{"finish_reason":"tool_calls", "message":{"role":"assistant", "content":None,
                    "tool_calls":[{"type":"function", "id":"call-"+str(turn), "function":{
                    "name":"read_certificate" if turn == 1 else "finish",
                    "arguments":"{}" if turn == 1 else '{"claim":"unknown"}'}}]}}]}
        result = self.check(transport)
        self.assertEqual(result["status"], "passed_exact_schema_handshake")
        self.assertEqual(sent[1]["messages"][-1]["role"], "tool")
        self.assertNotIn("need", sent[0]["messages"][0]["content"])

    def test_empty_output_is_unverified(self):
        route = prepare()["routes"][0]
        result = self.check(lambda _: {"model":route["model"], "provider":route["provider_name"], "usage":{"cost":0},
                           "choices":[{"finish_reason":"stop", "message":{"role":"assistant", "content":""}}]})
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["ledger_state"], "received")

    def test_transport_hold_stops_without_second_send(self):
        sent = []
        def fail(payload):
            sent.append(payload)
            raise TimeoutError("private")
        result = self.check(fail)
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["ledger_state"], "held")
        self.assertEqual(len(sent), 1)
