from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from benchmark.necessity_native import Ledger
from benchmark.necessity_native_probes import prepare,run,verify


class NativeProbeTests(unittest.TestCase):
    def ledger(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        ledger = Ledger(Path(directory.name)/"necessity-native.sqlite",baseline=lambda:0,study_cap=3)
        self.addCleanup(ledger.close)
        return ledger

    def fake(self,plan,payload):
        route = next(r for r in plan["routes"] if r["model"] == payload["model"])
        first = len(payload["messages"]) == 2
        action = "wait" if first else "finish"
        return {"model":route["model"],"provider":route["provider_name"],"usage":{"cost":0},
                "choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","content":None,
                    "reasoning_details":[{"type":"opaque","data":"preserve"}],
                    "tool_calls":[{"id":action+"-id","type":"function","function":{
                        "name":action,"arguments":"{}" if first else '{"claim":"unknown"}'}}]}}]}

    def test_all_schemas_and_continuations_replay_without_send(self):
        plan,ledger = prepare(),self.ledger()
        sends = []
        def transport(payload):
            sends.append(payload)
            if len(payload["messages"]) > 2:
                self.assertEqual(payload["messages"][-2]["reasoning_details"],[{"type":"opaque","data":"preserve"}])
            return self.fake(plan,payload)
        report = run(plan,ledger,transport,lambda r:None)
        self.assertEqual(len(sends),48)
        self.assertEqual(report["collection_state"],"finished")
        checked = verify(plan,report,ledger.conn)
        self.assertEqual(checked["verified_routes"],8)
        self.assertEqual(checked["verified_native_receipts"],48)

    def test_wrong_sequence_stops_and_cannot_verify_route(self):
        plan,ledger = prepare(),self.ledger()
        def transport(payload):
            response = self.fake(plan,payload)
            response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "transfer"
            return response
        report = run(plan,ledger,transport,lambda r:None)
        self.assertEqual(report["collection_state"],"stopped")
        self.assertEqual(verify(plan,report,ledger.conn)["verified_routes"],0)

    def test_forged_success_export_rejected(self):
        plan,ledger = prepare(),self.ledger()
        report = run(plan,ledger,lambda p:self.fake(plan,p),lambda r:None)
        bad = deepcopy(report)
        bad["routes"][0]["schemas"][0]["receipts"][0]["action"] = "finish"
        with self.assertRaises(ValueError):
            verify(plan,bad,ledger.conn)

    def test_transport_failure_hold_no_resend(self):
        plan,ledger = prepare(),self.ledger()
        sends = []
        def transport(payload):
            sends.append(payload)
            raise TimeoutError()
        run(plan,ledger,transport,lambda r:None)
        run(plan,ledger,transport,lambda r:None)
        self.assertEqual(len(sends),1)
        self.assertEqual(ledger.summary()["necessity_unresolved_holds_usd"],"1.00")

if __name__ == "__main__":
    unittest.main()
