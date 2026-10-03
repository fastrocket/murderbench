from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from benchmark.necessity_native import ROOT
from benchmark.necessity_collection_plan import normalized_hash
from benchmark.necessity_collection_live import atomic_json,collector_lock,live_amendment,validate_live,check_readiness


class LiveWiringTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT/"plans/necessity-structural-collection-manifest.json").read_text())
        self.extension = json.loads((ROOT/"plans/necessity-collector-source-amendment.json").read_text())
        self.live = live_amendment(self.manifest,self.extension)

    def test_amendment_tampering_rejected(self):
        validate_live(self.manifest,self.extension,self.live)
        wrong = deepcopy(self.live)
        wrong["lifetime_cap_usd"] = "800"
        with self.assertRaises(ValueError):
            validate_live(self.manifest,self.extension,wrong)

    def test_atomic_write_failure_preserves_previous_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"report.json"
            atomic_json(path,{"state":"old"})
            with self.assertRaises(ValueError):
                atomic_json(path,{"invalid":float("nan")})
            self.assertEqual(json.loads(path.read_text()),{"state":"old"})
            self.assertEqual(list(Path(directory).glob("*.tmp")),[])

    def test_exclusive_lock_and_release(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"lock"
            with collector_lock(path):
                with self.assertRaises(FileExistsError):
                    with collector_lock(path):
                        self.fail("second collector entered")
                self.assertTrue(path.exists())
            self.assertFalse(path.exists())

    def test_incomplete_readiness_rejected(self):
        with self.assertRaises(RuntimeError):
            check_readiness(self.manifest,self.extension,self.live,{}, {"remaining_accounted_usd":"12.19"})

    def test_native_report_flag_cannot_override_remaining_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/"reviews/probes.json"
            atomic_json(path,{"manifest_sha256":self.manifest["manifest_sha256"],
                            "routes":[{**r,"status":"verified_native_interface"} for r in self.manifest["route_prices"]]})
            readiness = {"manifest_sha256":self.manifest["manifest_sha256"],
                         "collector_amendment_sha256":self.extension["amendment_sha256"],
                         "live_amendment_sha256":self.live["amendment_sha256"],
                         "native_route_probes_complete":True,"prior_case_equivalence_review_complete":True,
                         "hosted_provenance_limits_disclosed":True,"lifetime_cap_usd":"50",
                         "native_probe_report":{"path":"reviews/probes.json","sha256":normalized_hash(path)}}
            with patch("benchmark.necessity_collection_live.ROOT",root),patch("benchmark.necessity_collection_live.validate_live"):
                with self.assertRaisesRegex(RuntimeError,"budget"):
                    check_readiness(self.manifest,self.extension,self.live,readiness,{"remaining_accounted_usd":"12.19"})

if __name__ == "__main__":
    unittest.main()
