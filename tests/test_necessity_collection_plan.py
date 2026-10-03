from copy import deepcopy
import unittest
from benchmark.necessity_collection_plan import matrix,packet_for,freeze,validate,TEMPLATES
from benchmark.necessity_structural_cases import ARMS
from benchmark.necessity_route_plan import ROUTES


class CollectionPlanTests(unittest.TestCase):
    def snapshot(self):
        return {"retrieved_utc":"test","remaining_accounted_usd":"12.19","assumptions":{},
                "routes":[{"model":m,"provider_tag":p,"provider_name":"test",
                           "status":"public_parameters_available",
                           "conditional_eight_turn_episode_usd":"0.8"} for m,p in ROUTES]}

    def test_exact_counts_order_and_unique_ids(self):
        rows = matrix()
        self.assertEqual(len(rows),512)
        self.assertEqual(len({r["episode_id"] for r in rows}),512)
        self.assertEqual(sum(r["max_calls"] for r in rows),4096)
        self.assertTrue(all(r["group"] == "proprietary_frontier" for r in rows[:256]))
        self.assertEqual(sum(r["split"] == "model_unqueried_extension" for r in rows),256)

    def test_pending_variant_disclosures_identical_between_worlds(self):
        for template in TEMPLATES:
            for arm in ARMS:
                self.assertEqual(packet_for(template,0,arm,"neutral")[1],
                                 packet_for(template,1,arm,"neutral")[1])

    def test_manifest_integrity_and_conditional_price(self):
        manifest = freeze(self.snapshot())
        self.assertTrue(validate(manifest))
        self.assertEqual(manifest["conditional_collection_usd"],"409.6")
        self.assertFalse(manifest["collection_ready"])
        changed = deepcopy(manifest)
        changed["episodes"][0]["world_index"] = 99
        with self.assertRaises(ValueError):
            validate(changed)

    def test_invalid_route_snapshot_and_selection_fail_closed(self):
        snapshot = self.snapshot()
        snapshot["routes"][0]["provider_tag"] = "different"
        with self.assertRaises(ValueError):
            freeze(snapshot)
        for args in (("pending/unknown",0,"baseline","neutral"),
                     ("pending/strict_slack",True,"baseline","neutral"),
                     ("pending/strict_slack",0,"baseline","unknown")):
            with self.assertRaises(ValueError):
                packet_for(*args)

if __name__ == "__main__":
    unittest.main()
