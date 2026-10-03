from copy import deepcopy
from decimal import Decimal
import json
import unittest
from benchmark.necessity_resource_probe_plan import ROOT
from benchmark.necessity_resource_probe_pricing import price


class ProbePriceTests(unittest.TestCase):
    def setUp(self):
        self.manifests = [json.loads((ROOT/"plans"/name).read_text()) for name in
                          ("necessity-structural-collection-manifest.json", "necessity-resource-probe-collection-manifest.json")]
        self.snapshot = json.loads((ROOT/"reviews/necessity-resource-probe-route-refresh.json").read_text())

    def test_reprice_preserves_full_scope(self):
        result = price(self.manifests, self.snapshot)
        self.assertEqual([s["max_calls"] for s in result["studies"]], [4096, 1920])
        self.assertEqual(Decimal(result["future_conditional_usd"]), Decimal("1028.409836544"))
        self.assertFalse(result["collection_ready"])
        self.assertEqual(Decimal(result["conditional_lifetime_total_usd"]),
                         Decimal(result["future_conditional_usd"])+Decimal(result["current_accounted_usd"]))

    def test_missing_or_changed_route_rejected(self):
        for mutation in ("missing", "provider", "parameters"):
            snapshot = deepcopy(self.snapshot)
            if mutation == "missing":
                snapshot["routes"].pop()
            elif mutation == "provider":
                snapshot["routes"][0]["provider_tag"] = "other"
            else:
                snapshot["routes"][0]["status"] = "parameter_gap"
            with self.assertRaises((ValueError, KeyError)):
                price(self.manifests, snapshot)
