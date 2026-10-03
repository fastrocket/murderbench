from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from benchmark.necessity_resource_probe_plan import ROOT
from benchmark.necessity_resource_probe_collector import execute
from benchmark.necessity_native import Ledger


class ProbeCollectorTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT/"plans/necessity-resource-probe-collection-manifest.json").read_text())
        self.analysis = json.loads((ROOT/"plans/necessity-resource-probe-analysis-amendment.json").read_text())
        self.amendment = json.loads((ROOT/"plans/necessity-resource-probe-collector-amendment.json").read_text())

    def collect(self, transport, limit=1):
        saved = []
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite", baseline=lambda:0)
            try:
                report = execute(self.manifest, self.analysis, self.amendment, ledger, transport, saved.append, limit)
            finally:
                ledger.close()
        return report, saved

    def response(self, content):
        route = self.manifest["route_prices"][0]
        return {"model":route["model"], "provider":route["provider_name"],
                "choices":[{"finish_reason":"stop", "message":{"role":"assistant", "content":content}}],
                "usage":{"cost":0}}

    def test_limit_preserves_fixed_prefix_and_diagnosis(self):
        report, saved = self.collect(lambda payload:self.response("Stop"))
        self.assertEqual(report["collection_state"], "episode_limit_stop")
        self.assertEqual(report["not_attempted"], 383)
        self.assertEqual(report["records"][0]["episode_id"], self.manifest["episodes"][0]["episode_id"])
        self.assertIn("diagnosis", report["records"][0])
        self.assertEqual(saved[0]["records"], [])
        self.assertEqual(saved[-1], report)

    def test_unknown_stops_without_scoring(self):
        report, _ = self.collect(lambda payload:self.response(""), limit=3)
        self.assertEqual(report["collection_state"], "technical_stop")
        self.assertEqual(len(report["records"]), 1)
        self.assertIsNone(report["records"][0]["result"]["outcome"])
        self.assertNotIn("diagnosis", report["records"][0])

    def test_transport_failure_persists_hold_without_exception_text(self):
        sent = []
        def fail(payload):
            sent.append(payload)
            raise TimeoutError("private-string")
        report, _ = self.collect(fail)
        self.assertEqual(report["collection_state"], "stopped")
        self.assertEqual(len(sent), 1)
        self.assertNotIn("private-string", json.dumps(report))
        self.assertEqual(report["budget"]["necessity_unresolved_holds_usd"], "1.00")
        self.assertEqual(report["records"][0]["result"]["attempts"][0]["ledger_state"], "held")

    def test_changed_freeze_fails_before_access(self):
        amendment = deepcopy(self.amendment)
        amendment["collection_ready"] = True
        with self.assertRaises(ValueError):
            execute(self.manifest, self.analysis, amendment, None, None, None)
