from collections import Counter
from copy import deepcopy
import json
import unittest
from benchmark.necessity_resource_probe_plan import ROOT, build, validate


class ProbePlanTests(unittest.TestCase):
    def test_frozen_matrix_complete_and_information_paired(self):
        manifest = json.loads((ROOT/"plans/necessity-resource-probe-collection-manifest.json").read_text())
        self.assertTrue(validate(manifest))
        self.assertEqual(manifest["episode_count"], 384)
        self.assertEqual(manifest["max_model_calls"], 1920)
        rows = manifest["episodes"]
        self.assertEqual(len({r["episode_id"] for r in rows}), 384)
        self.assertEqual(set(Counter(r["model"] for r in rows).values()), {48})
        for model in {r["model"] for r in rows}:
            for rep in range(3):
                counts = Counter(r["public_packet_sha256"] for r in rows if r["model"] == model and r["repetition"] == rep)
                self.assertEqual(len(counts), 8)
                self.assertEqual(set(counts.values()), {2})
        self.assertFalse(manifest["collection_ready"])

    def test_manifest_tampering_rejected(self):
        for field, value in (("collection_ready", True), ("episode_count", 1), ("dated_conditional_usd", "0")):
            candidate = deepcopy(build())
            candidate[field] = value
            with self.assertRaises(ValueError):
                validate(candidate)
