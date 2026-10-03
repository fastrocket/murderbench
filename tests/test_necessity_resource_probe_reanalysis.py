from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from benchmark.necessity_native import Ledger
from benchmark.necessity_resource_probe_plan import ROOT
from benchmark.necessity_resource_probe_collector import execute
from benchmark.necessity_resource_probe_reanalysis import analyze


class ProbeReanalysisTests(unittest.TestCase):
    def setUp(self):
        def load(name):
            return json.loads((ROOT/"plans"/name).read_text())
        self.manifest = load("necessity-resource-probe-collection-manifest.json")
        self.analysis = load("necessity-resource-probe-analysis-amendment.json")
        self.amendment = load("necessity-resource-probe-collector-amendment.json")

    def test_receipt_rebuild_and_tampering(self):
        route = self.manifest["route_prices"][0]
        response = {"model":route["model"], "provider":route["provider_name"], "usage":{"cost":0},
                    "choices":[{"finish_reason":"stop", "message":{"role":"assistant", "content":"Stop"}}]}
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite", baseline=lambda:0)
            try:
                report = execute(self.manifest, self.analysis, self.amendment, ledger, lambda _:response, lambda _:None, 1)
                with self.assertRaises(ValueError):
                    analyze(self.manifest, self.analysis, self.amendment, report, ledger.conn)
                ledger.conn.execute("PRAGMA query_only=ON")
                verified = analyze(self.manifest, self.analysis, self.amendment, report, ledger.conn)
                self.assertEqual(verified["verified_native_receipts"], 1)
                self.assertEqual(verified["counts"]["not_attempted"], 383)
                for field in ("outcome", "diagnosis", "episode", "finished", "denominator"):
                    changed = deepcopy(report)
                    if field == "outcome":
                        changed["records"][0]["result"]["outcome"]["primary_loss"] = 999
                    elif field == "diagnosis":
                        changed["records"][0]["diagnosis"]["initial_feasible"] = False
                    elif field == "episode":
                        changed["records"][0]["episode_id"] = "invented"
                    elif field == "finished":
                        changed["collection_state"] = "finished"
                    else:
                        changed["not_attempted"] = 0
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        analyze(self.manifest, self.analysis, self.amendment, changed, ledger.conn)
            finally:
                ledger.close()

    def test_held_request_remains_unscored_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite", baseline=lambda:0)
            def fail(_):
                raise TimeoutError("synthetic")
            try:
                report = execute(self.manifest, self.analysis, self.amendment, ledger, fail, lambda _:None, 1)
                before = ledger.conn.execute("SELECT id,state,response FROM calls").fetchall()
                ledger.conn.execute("PRAGMA query_only=ON")
                verified = analyze(self.manifest, self.analysis, self.amendment, report, ledger.conn)
                self.assertEqual(verified["counts"]["collection_stopped"], 1)
                self.assertIsNone(verified["records"][0]["outcome"])
                self.assertEqual(before, ledger.conn.execute("SELECT id,state,response FROM calls").fetchall())
            finally:
                ledger.close()
