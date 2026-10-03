import unittest

from benchmark.necessity_oracle import DEFAULT_WEIGHTS, loss
from benchmark.necessity_queue_bounds import bounds


class QueueInformationBounds(unittest.TestCase):
    def test_default_interval_and_attained_floor(self):
        result = bounds()
        self.assertAlmostEqual(result["lower_bound"],1.1)
        self.assertAlmostEqual(result["upper_bound"],1.25)
        self.assertFalse(result["exact_information_limited_optimum"])
        self.assertEqual(result["independent_fold_matches"],32)
        self.assertEqual(result["best_feasible_policy"],"alternative_and_buffer_schedule")
        observed = sum(loss(r["outcome"],DEFAULT_WEIGHTS)/4 for r in result["lower_executions"])
        self.assertAlmostEqual(observed,result["lower_bound"])

    def test_expensive_protected_allocations_change_feasible_procedure(self):
        weights = {**DEFAULT_WEIGHTS,"protected_loss":10}
        result = bounds(weights=weights)
        self.assertEqual(result["best_feasible_policy"],"alternative_only")
        self.assertAlmostEqual(result["lower_bound"],2.55)
        self.assertAlmostEqual(result["upper_bound"],2.6)

    def test_zero_weights_and_degenerate_prior_remain_valid(self):
        result = bounds(weights={k:0 for k in DEFAULT_WEIGHTS})
        self.assertEqual((result["lower_bound"],result["upper_bound"]),(0,0))
        result = bounds(prior=[1,0,0,0])
        self.assertEqual((result["lower_bound"],result["upper_bound"]),(0,0))

    def test_lower_witnesses_are_explicitly_not_one_observation_policy(self):
        result = bounds()
        first_actions = {r["events"][0]["tool"] for r in result["lower_executions"]}
        self.assertGreater(len(first_actions),1)
        self.assertIn("extra information",result["limits"][0])

    def test_rare_a_need_can_make_prioritizing_b_cheaper_than_buffering_both(self):
        result = bounds(prior=[.495,.495,.005,.005])
        self.assertEqual(result["best_feasible_policy"],"verify_b_only")
        self.assertAlmostEqual(result["upper_bound"],1.1)
        self.assertAlmostEqual(result["lower_bound"],1.051)

    def test_invalid_weights_and_priors_cannot_issue_bounds(self):
        for prior in ([1],[-1,1,1,0],[float("nan")]*4):
            with self.assertRaises(ValueError):
                bounds(prior=prior)
        with self.assertRaises(ValueError):
            bounds(weights={**DEFAULT_WEIGHTS,"primary_loss":-1})


if __name__ == "__main__":
    unittest.main()
