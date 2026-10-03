from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from benchmark.necessity_native import ROOT,Ledger
from benchmark.necessity_collection_runner import amendment,execute
from benchmark.necessity_collection_analysis import analyze


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT/"plans/necessity-structural-collection-manifest.json").read_text())
        self.extension = amendment(self.manifest)

    def run_local(self,transport,limit=2):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        ledger = Ledger(Path(directory.name)/"necessity-native.sqlite",baseline=lambda:0,study_cap=50)
        self.addCleanup(ledger.close)
        snapshots = []
        report = execute(self.manifest,self.extension,ledger,transport,snapshots.append,limit)
        return ledger,report,snapshots

    def final_answer(self,payload,reason="stop"):
        route = next(r for r in self.manifest["route_prices"] if r["model"] == payload["model"])
        return {"model":payload["model"],"provider":route["provider_name"],"usage":{"cost":0},
                "choices":[{"finish_reason":reason,"message":{"role":"assistant","content":"Stop."}}]}

    def test_collection_and_reanalysis_without_network(self):
        ledger,report,snapshots = self.run_local(self.final_answer)
        self.assertEqual(report["collection_state"],"episode_limit_stop")
        self.assertEqual(report["not_attempted"],510)
        self.assertGreater(len(snapshots),2)
        before = ledger.conn.total_changes
        checked = analyze(self.manifest,self.extension,report,ledger.conn)
        self.assertEqual(checked["verified_native_receipts"],2)
        self.assertEqual(checked["verified_episode_records"],2)
        self.assertEqual(ledger.conn.total_changes,before)

    def test_technical_unknown_stops_without_score(self):
        ledger,report,_ = self.run_local(lambda p:self.final_answer(p,"length"))
        self.assertEqual(report["collection_state"],"technical_stop")
        self.assertIsNone(report["records"][0]["result"]["outcome"])
        checked = analyze(self.manifest,self.extension,report,ledger.conn)
        self.assertEqual(checked["records"][0]["status"],"technical_unknown")
        self.assertEqual(checked["complete_pairs"],0)

    def test_transport_hold_and_rerun_cannot_resend(self):
        sends = []
        def timeout(payload):
            sends.append(payload)
            raise TimeoutError("private exception text must not be exported")
        ledger,report,_ = self.run_local(timeout)
        self.assertEqual(report["records"][0]["result"]["stop_category"],"transport_unknown")
        checked = analyze(self.manifest,self.extension,report,ledger.conn)
        self.assertEqual(checked["records"][0]["status"],"collection_stopped")
        self.assertNotIn("private exception text",json.dumps(report))
        execute(self.manifest,self.extension,ledger,timeout,lambda r:None,2)
        self.assertEqual(len(sends),1)
        self.assertEqual(ledger.summary()["necessity_unresolved_holds_usd"],"1.00")

    def test_exported_outcome_or_raw_payload_tampering_rejected(self):
        ledger,report,_ = self.run_local(self.final_answer)
        bad = deepcopy(report)
        bad["records"][0]["result"]["outcome"]["primary_loss"] = 999
        with self.assertRaises(ValueError):
            analyze(self.manifest,self.extension,bad,ledger.conn)
        call_id = report["records"][0]["result"]["attempts"][0]["call_id"]
        ledger.conn.execute("UPDATE calls SET payload='{}' WHERE id=?",(call_id,))
        with self.assertRaises(ValueError):
            analyze(self.manifest,self.extension,report,ledger.conn)

    def test_source_amendment_change_rejected_before_transport(self):
        extension = deepcopy(self.extension)
        extension["matrix_unchanged"] = False
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        ledger = Ledger(Path(directory.name)/"necessity-native.sqlite",baseline=lambda:0)
        self.addCleanup(ledger.close)
        with self.assertRaises(ValueError):
            execute(self.manifest,extension,ledger,lambda p:self.fail("transport called"),lambda r:None)

    def test_complete_route_pairs_are_not_counted_as_independent_world_samples(self):
        ledger,report,_ = self.run_local(self.final_answer,64)
        checked = analyze(self.manifest,self.extension,report,ledger.conn)
        self.assertEqual(checked["complete_pairs"],32)
        self.assertEqual(checked["incomplete_pairs"],224)
        self.assertTrue(all(p["weighted_difference"] == 0 for p in checked["paired_differences"]))

if __name__ == "__main__":
    unittest.main()
