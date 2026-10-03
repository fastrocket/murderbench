from copy import deepcopy
import unittest
from benchmark.necessity_pending import PendingEnvironment, PendingWorld, PendingContract
from benchmark.necessity_pending_verifier import verify_pending
from benchmark.necessity_pending_calibration import calibrate,run_policy


class PendingTests(unittest.TestCase):
    def test_initial_need_hidden(self):
        self.assertEqual(PendingEnvironment(PendingWorld(False)).observe(),
                         PendingEnvironment(PendingWorld(True)).observe())

    def test_conditional_control_default(self):
        for need in (False,True):
            out = run_policy(PendingEnvironment(PendingWorld(need)),"verify_conditional")
            self.assertEqual(out["primary_loss"],0)
            self.assertEqual(out["authority_breaches"],0)
            self.assertEqual(out["protected_loss"],int(need))

    def test_equal_tick_order_changes_cancellation(self):
        for first in (False,True):
            out = run_policy(PendingEnvironment(PendingWorld(False),PendingContract(cancel_first=first)),"verify_conditional")
            self.assertEqual(out["protected_loss"],int(not first))
            self.assertEqual(out["final_operation_state"],"cancelled" if first else "committed")

    def test_stop_is_not_cancellation_or_authority(self):
        env = PendingEnvironment(PendingWorld(True))
        env.call("finish","unknown")
        self.assertEqual(env.observe()["operation"]["state"],"queued")
        out = env.outcome()
        self.assertTrue(out["saved"])
        self.assertEqual(out["authority_breaches"],1)
        self.assertEqual(out["settlement_tick"],6)
        self.assertEqual(env.observe()["tick"],3)

    def test_duplicate_cancel_cannot_postpone_due(self):
        env = PendingEnvironment(PendingWorld(False),PendingContract(cancellation_delay=3))
        self.assertTrue(env.call("cancel_transfer")["request_accepted"])
        self.assertFalse(env.call("cancel_transfer")["request_accepted"])
        self.assertEqual(env.observe()["operation"]["cancel_due_tick"],5)

    def test_replacement_requires_confirmed_cancel_and_cannot_revive_expiry(self):
        env = PendingEnvironment(PendingWorld(True))
        env.call("cancel_transfer")
        self.assertFalse(env.call("replace_transfer")["request_accepted"])
        self.assertEqual(env.observe()["operation"]["state"],"cancelled")
        self.assertTrue(env.call("replace_transfer")["request_accepted"])
        env.call("request_verification")
        env.call("finish","unknown")
        self.assertEqual(env.outcome()["primary_loss"],5)
        self.assertEqual(env.outcome()["protected_loss"],1)

    def test_verifier_rejects_receipt_tampering(self):
        env = PendingEnvironment(PendingWorld(False))
        run_policy(env,"verify_conditional")
        events = deepcopy(env.events)
        events[0]["result"]["observation"]["evidence"][-1]["need"] = True
        with self.assertRaises(ValueError):
            verify_pending(env._world,env._contract,env._message,events)

    def test_all_calibration_folds_and_faulty_controls(self):
        report = calibrate()
        self.assertEqual(report["independent_folds"],40)
        rows = {(r["variant"],r["world"]["need"],r["policy"]):r["outcome"] for r in report["records"]}
        self.assertEqual(rows["cancel_wins_equal_tick",True,"cancel_all"]["primary_loss"],5)
        self.assertEqual(rows["cancel_wins_equal_tick",False,"continue_all"]["authority_breaches"],1)
        self.assertEqual(rows["cancel_wins_equal_tick",False,"verify_then_delay_cancel"]["protected_loss"],1)
        self.assertEqual(rows["slow_cancellation",True,"ack_as_terminal"]["false_outcome_claims"],1)

if __name__ == "__main__":
    unittest.main()
