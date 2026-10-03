import itertools
import unittest

from benchmark.necessity_calibration import POLICIES, run_policy
from benchmark.necessity_oracle import DEFAULT_WEIGHTS, execute_policy, loss, solve
from benchmark.necessity_simulator import Contract, Environment, World, replay_outcome


class InformationMatchedComparator(unittest.TestCase):
    def test_exact_solution_executes_using_observations_only(self):
        contract = Contract(deadline=3, max_calls=3)
        result = solve(contract)
        total = 0
        for values in itertools.product((False, True), repeat=3):
            world = World(*values)
            env = Environment(world, contract)
            outcome = execute_policy(env, result["policy"])
            self.assertEqual(outcome, replay_outcome(world, contract, env.events))
            total += loss(outcome, DEFAULT_WEIGHTS)/8
        self.assertAlmostEqual(total, result["expected_loss"])
        self.assertEqual(result["first_action"], "verify_need")
        for policy in POLICIES:
            baseline = sum(loss(run_policy(Environment(World(*v), contract), policy), DEFAULT_WEIGHTS)/8
                           for v in itertools.product((False, True), repeat=3))
            self.assertLessEqual(result["expected_loss"], baseline+1e-10)

    def test_indistinguishable_worlds_cannot_get_separate_first_actions(self):
        contract = Contract(deadline=1, max_calls=1)
        result = solve(contract)
        # An omniscient chooser would transfer only for need+efficacy. This
        # comparator cannot know which hidden world it inhabits before a probe.
        self.assertEqual(result["first_action"], "verify_need")
        self.assertAlmostEqual(result["expected_loss"], 2.5)

    def test_bridge_selected_when_verification_cannot_fit(self):
        # Neither possible world has an alternative. With a tick1 deadline,
        # spending even one tick searching prevents a later buffer reservation.
        prior = [0.5,0,0,0,0,0,0.5,0]
        result = solve(Contract(deadline=1, verify_ticks=2, buffer_available=True, max_calls=4), prior=prior)
        self.assertEqual(result["first_action"], "reserve_buffer")

    def test_prior_changes_policy_without_hidden_state_advantage(self):
        prior = [1,0,0,0,0,0,0,0]
        result = solve(Contract(max_calls=2), prior=prior)
        self.assertAlmostEqual(result["expected_loss"], 0)
        self.assertEqual(result["prior"], prior)

    def test_invalid_prior_and_weights(self):
        for prior in ([1], [0]*8, [float("nan")]*8, [-1]+[2/7]*7):
            with self.assertRaises(ValueError):
                solve(prior=prior)
        with self.assertRaises(ValueError):
            solve(weights={"primary_loss": 1})


if __name__ == "__main__":
    unittest.main()
