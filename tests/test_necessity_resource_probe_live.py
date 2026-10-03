import unittest
from benchmark.necessity_resource_probe_live import admit, prepare


class ProbeLiveTests(unittest.TestCase):
    def test_current_freeze_and_eligibility_block(self):
        self.assertFalse(prepare()["collection_ready"])
        with self.assertRaisesRegex(RuntimeError, "eligibility"):
            admit({"source_chains_valid":True, "unverified_routes":["google"]}, {"remaining_accounted_usd":"1000"})

    def test_budget_checked_after_route_eligibility(self):
        evidence = {"source_chains_valid":True, "unverified_routes":[], "supplement_conditional_usd":"328.22"}
        with self.assertRaisesRegex(RuntimeError, "headroom"):
            admit(evidence, {"remaining_accounted_usd":"9.06"})
        admit(evidence, {"remaining_accounted_usd":"328.22"})
