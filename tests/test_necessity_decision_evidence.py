import unittest

from benchmark.necessity_decision_evidence import transfer_diagnostics
from benchmark.necessity_events import EventWorld, EventContract, EventEnvironment
from benchmark.necessity_queue import QueueWorld, QueueEnvironment


class DecisionEvidenceTiming(unittest.TestCase):
    def test_queue_report_can_arrive_during_transfer(self):
        env = QueueEnvironment(QueueWorld(False,True))
        initial = env.observe()
        env.call("verify_b")
        env.call("transfer_b")
        row = transfer_diagnostics(initial,env.events,"queue")[0]
        self.assertFalse(row["positive_current_evidence_at_decision"])
        self.assertTrue(row["authorized_at_completion"])
        self.assertTrue(row["authority_became_available_during_call"])

    def test_waited_report_is_available_at_decision(self):
        env = QueueEnvironment(QueueWorld(False,True))
        initial = env.observe()
        env.call("verify_b")
        env.call("wait")
        env.call("transfer_b")
        row = transfer_diagnostics(initial,env.events,"queue")[0]
        self.assertTrue(row["positive_current_evidence_at_decision"])
        self.assertTrue(row["authorized_at_completion"])

    def test_state_change_during_action_can_remove_authority(self):
        env = EventEnvironment(EventWorld(True,True,change_tick=3,changed_need=False),
                               EventContract(deadline=5))
        initial = env.observe()
        env.call("request_verification")
        env.call("wait")
        env.call("transfer")
        row = transfer_diagnostics(initial,env.events,"event")[0]
        self.assertTrue(row["positive_current_evidence_at_decision"])
        self.assertFalse(row["authorized_at_completion"])

    def test_unknown_simulator_kind_cannot_issue_diagnostic(self):
        with self.assertRaises(ValueError):
            transfer_diagnostics({},[],"other")


if __name__ == "__main__":
    unittest.main()
