from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from benchmark.necessity_native import Ledger
from benchmark.necessity_google_text_probe import prepare, run
from tests import test_necessity_native_probes as helpers


class GoogleTextProbeTests(unittest.TestCase):
    def test_original_schemas_continuations_and_preserved_metadata(self):
        plan = prepare()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite", baseline=lambda:0, study_cap=2)
            try:
                sent = []
                def transport(packet):
                    self.assertNotIn("image", packet["provider"]["max_price"])
                    self.assertEqual(packet["provider"]["data_collection"], "deny")
                    for tool in packet["tools"]:
                        self.assertIn("parameters", tool["function"])
                    if len(packet["messages"]) > 2:
                        self.assertEqual(packet["messages"][-2]["reasoning_details"],
                                         [{"type":"opaque", "data":"preserve"}])
                    sent.append(deepcopy(packet))
                    return helpers.NativeProbeTests.fake(self, {"routes":[plan["route"]]}, packet)
                report = run(plan, ledger, transport, lambda r:None)
                self.assertEqual(report["status"], "passed_text_only_routing")
                self.assertEqual(len(sent), 6)
            finally:
                ledger.close()

    def test_unresolved_request_cannot_be_retried(self):
        plan = prepare()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite", baseline=lambda:0, study_cap=2)
            try:
                sent = []
                def transport(packet):
                    sent.append(packet)
                    raise TimeoutError()
                run(plan, ledger, transport, lambda r:None)
                run(plan, ledger, transport, lambda r:None)
                self.assertEqual(len(sent), 1)
                self.assertEqual(ledger.summary()["necessity_unresolved_holds_usd"], "1.00")
            finally:
                ledger.close()
