from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from benchmark.necessity_authorized_ledger import AuthorizedLedger
from benchmark.necessity_matched_pilot import collect
from benchmark.necessity_matched_reanalysis_v2 import analyze
from tests import test_necessity_matched_pilot as fixtures
from tests.test_necessity_native import response


class ByteGateReanalysisTests(unittest.TestCase):
    def test_saved_large_reasoning_causes_local_unscored_stop_before_next_reservation(self):
        plan = fixtures.MatchedPilotTests().small_plan()
        receipt = response("read_certificate")
        receipt["choices"][0]["message"]["reasoning_details"] = [{"type": "opaque", "data": "x" * 25000}]
        sent = []
        def transport(_):
            sent.append(1)
            return receipt
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizedLedger(Path(directory) / "necessity-native.sqlite", plan["study_id"], baseline=lambda: 0)
            try:
                report = collect(plan, ledger, transport, lambda _: None)
                self.assertEqual(len(sent), 1)
                self.assertEqual(report["records"][0]["result"]["status"], "collection_stopped")
                self.assertEqual(len(report["records"][0]["result"]["events"]), 1)
                self.assertIsNone(report["records"][0]["result"]["outcome"])
                self.assertEqual(ledger.conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0], 1)
                ledger.conn.execute("PRAGMA query_only=ON")
                audit = analyze(plan, report, ledger.conn)
                self.assertEqual(audit["counts"]["collection_stopped"], 1)
                self.assertEqual(audit["verified_native_receipts"], 1)
                altered = deepcopy(report)
                altered["records"][0]["result"]["outcome"] = {"primary_loss": 0}
                with self.assertRaisesRegex(ValueError, "stopped trace differs"):
                    analyze(plan, altered, ledger.conn)
            finally:
                ledger.close()
