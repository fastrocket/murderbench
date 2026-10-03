from pathlib import Path
import tempfile
import unittest
import urllib.error
from benchmark.necessity_native import Ledger
from benchmark.necessity_remaining_probes import prepare,run,verify
from tests import test_necessity_native_probes as probe_tests

class RemainingProbeTests(unittest.TestCase):
    def test_remaining_routes_replay_and_do_not_include_google(self):
        plan=prepare()
        self.assertEqual(len(plan["routes"]),5)
        self.assertFalse(any("google" in r["model"] for r in plan["routes"]))
        with tempfile.TemporaryDirectory() as directory:
            ledger=Ledger(Path(directory)/"necessity-native.sqlite",baseline=lambda:0,study_cap=2)
            try:
                report=run(plan,ledger,lambda p:probe_tests.NativeProbeTests().fake(plan,p),lambda r:None)
                self.assertEqual(verify(plan,report,ledger.conn)["verified_native_receipts"],30)
            finally: ledger.close()

    def test_http_status_saved_without_body_or_retry(self):
        plan=prepare()
        with tempfile.TemporaryDirectory() as directory:
            ledger=Ledger(Path(directory)/"necessity-native.sqlite",baseline=lambda:0,study_cap=2)
            try:
                def fail(payload): raise urllib.error.HTTPError("https://example.invalid",503,"secret body",{},None)
                report=run(plan,ledger,fail,lambda r:None)
                self.assertEqual(report["routes"][0]["http_status"],503)
                self.assertEqual(ledger.summary()["necessity_unresolved_holds_usd"],"1.00")
            finally: ledger.close()
