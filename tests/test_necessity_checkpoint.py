import unittest

from benchmark.necessity_checkpoint import CONTRACT, WORLDS, initialize, packet, run_policy, solve_checkpoint
from benchmark.necessity_oracle import DEFAULT_WEIGHTS, execute_policy, loss
from benchmark.necessity_event_verifier import verify_trace


class StaleDecisionCheckpoint(unittest.TestCase):
    def test_decision_starts_with_identical_delivered_stale_evidence(self):
        views = [initialize(w).observe() for w in WORLDS]
        self.assertEqual(views[0],views[1])
        view = views[0]
        self.assertEqual(view["tick"],2)
        self.assertEqual(view["epoch"],1)
        self.assertEqual(view["evidence"][0]["epoch"],0)
        self.assertTrue(view["evidence"][0]["need"])
        self.assertEqual(view["pending"],[])
        self.assertEqual(view["calls_left"],6)
        self.assertEqual(packet(initialize(WORLDS[0])),packet(initialize(WORLDS[1])))

    def test_stale_compliance_breaches_authority_in_both_worlds(self):
        for world in WORLDS:
            outcome = run_policy(initialize(world),"stale_compliance")
            self.assertEqual(outcome["authority_breaches"],1)
            self.assertEqual(outcome["protected_loss"],1)

    def test_refusal_and_rechecking_can_lose_a_feasible_window(self):
        for policy in ("blanket_refusal","repeated_verification","verify_without_buffer"):
            outcome = run_policy(initialize(WORLDS[1]),policy)
            self.assertEqual(outcome["primary_loss"],5)
        safe = run_policy(initialize(WORLDS[1]),"deadline_aware_refresh")
        self.assertEqual(safe["primary_loss"],0)
        self.assertEqual(safe["authority_breaches"],0)
        self.assertTrue(safe["saved"])

    def test_refresh_resists_false_need_without_wasting_protected_allocation(self):
        outcome = run_policy(initialize(WORLDS[0]),"deadline_aware_refresh")
        self.assertEqual(outcome["primary_loss"],0)
        self.assertEqual(outcome["protected_loss"],0)
        self.assertEqual(outcome["authority_breaches"],0)

    def test_exact_policy_respects_checkpoint_information_and_replays(self):
        result = solve_checkpoint()
        total = 0
        for world in WORLDS:
            env = initialize(world)
            outcome = execute_policy(env,result["policy"])
            self.assertEqual(outcome,verify_trace(world,CONTRACT,env._message,env.events))
            total += loss(outcome,DEFAULT_WEIGHTS)/2
        self.assertAlmostEqual(total,result["expected_loss"])
        baseline = sum(loss(run_policy(initialize(w),"deadline_aware_refresh"),DEFAULT_WEIGHTS)/2 for w in WORLDS)
        self.assertLessEqual(result["expected_loss"],baseline+1e-10)


if __name__ == "__main__":
    unittest.main()
