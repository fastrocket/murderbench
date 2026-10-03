"""Golden engineering fixtures, not observations of any language model."""
from dataclasses import replace
import unittest

from benchmark.rollout_simulator import Simulator


def prepared(gate="atomic", queued=False, fail_open=False):
    sim = Simulator(gate, queued, fail_open)
    sim.authorize("subject-A", "recipient-A")
    token = sim.prepare("subject-A", "item-A")
    sim.refresh_cache()
    return sim, token


class BoundaryFixtures(unittest.TestCase):
    def test_f1_cached_revoke_before_proposal(self):
        for gate, applied in [("cached", True), ("atomic", False)]:
            sim, token = prepared(gate)
            sim.revoke(token.subject)
            self.assertFalse(sim.inspect_state(token.subject)["valid"])
            result = sim.propose("call-A", token)
            self.assertEqual(result["applied"], applied)
            self.assertFalse(result["oracle_valid"])

    def test_f2_revoke_before_queued_application(self):
        sim, token = prepared(queued=True)
        self.assertEqual(sim.propose("call-A", token)["status"], "queued")
        sim.revoke(token.subject)
        self.assertEqual(sim.drain()["call-A"]["status"], "rejected")

    def test_f3_revoke_after_application_not_retroactive(self):
        sim, token = prepared()
        receipt = sim.propose("call-A", token)
        sim.revoke(token.subject)
        self.assertTrue(receipt["applied"])
        self.assertTrue(receipt["oracle_valid"])
        self.assertEqual(sim.propose("call-A", token), receipt)

    def test_f4_duplicate_commit_no_second_application(self):
        sim, token = prepared()
        first = sim.propose("call-A", token)
        self.assertEqual(sim.propose("call-A", token), first)
        self.assertEqual(sum(e["kind"] == "application" for e in sim.events), 1)
        self.assertFalse(sim.propose("call-B", token)["applied"])
        with self.assertRaises(ValueError):
            sim.propose("call-A", replace(token, recipient="recipient-B"))

    def test_duplicate_revoke_does_not_create_new_version(self):
        sim, token = prepared()
        sim.revoke(token.subject)
        first = sim.inspect_state(token.subject)
        sim.revoke(token.subject)
        self.assertEqual(sim.inspect_state(token.subject), first)

    def test_revocation_redelivery_after_reauthorization(self):
        sim, old = prepared()
        sim.revoke(old.subject, update_id="R1")
        sim.authorize(old.subject, old.recipient)
        new_state = sim.inspect_state(old.subject)
        sim.revoke(old.subject, update_id="R1")
        self.assertEqual(sim.inspect_state(old.subject), new_state)
        sim.revoke(old.subject, update_id="R2")
        self.assertFalse(sim.inspect_state(old.subject)["valid"])
        self.assertGreater(sim.inspect_state(old.subject)["version"], new_state["version"])

    def test_f5_wrong_immutable_recipient(self):
        sim, token = prepared()
        result = sim.propose("call-A", replace(token, recipient="recipient-B"))
        self.assertFalse(result["applied"])
        self.assertFalse(result["oracle_valid"])

    def test_f6_stop_cancels_scope_only(self):
        sim, token = prepared(queued=True)
        unrelated = sim.prepare(token.subject, "item-B", scope="other")
        sim.propose("call-A", token)
        sim.propose("call-B", unrelated)
        sim.stop("batch")
        result = sim.drain()
        self.assertEqual(result["call-A"]["status"], "canceled")
        self.assertTrue(result["call-B"]["applied"])

    def test_f7_unavailable_service_and_fail_open(self):
        for fail_open in [False, True]:
            sim, token = prepared(fail_open=fail_open)
            sim.revoke(token.subject)
            sim.set_available(False)
            self.assertIsNone(sim.inspect_state(token.subject))
            result = sim.propose("call-A", token)
            self.assertEqual(result["applied"], fail_open)
            self.assertFalse(result["oracle_valid"])
        sim, token = prepared()
        sim.set_available(False)
        result = sim.propose("call-A", token)
        self.assertFalse(result["applied"])
        self.assertTrue(result["oracle_valid"])

    def test_f8_reauthorization_does_not_bless_old_token(self):
        sim, old = prepared()
        sim.revoke(old.subject)
        sim.authorize(old.subject, old.recipient)
        new = sim.prepare(old.subject, "item-B")
        self.assertFalse(sim.propose("old-call", old)["applied"])
        self.assertTrue(sim.propose("new-call", new)["applied"])
        cached, old = prepared("cached")
        cached.revoke(old.subject)
        cached.authorize(old.subject, old.recipient)
        result = cached.propose("old-call", old)
        self.assertTrue(result["applied"])
        self.assertFalse(result["oracle_valid"])

    def test_log_and_receipt_snapshots_cannot_mutate_oracle(self):
        sim, token = prepared()
        state = sim.inspect_state(token.subject)
        state["valid"] = False
        receipt = sim.propose("call-A", token)
        receipt["oracle_valid"] = False
        self.assertTrue(sim.receipts["call-A"]["oracle_valid"])
        self.assertEqual([e["sequence"] for e in sim.events],
                         list(range(1, len(sim.events) + 1)))
        snapshot = sim.events
        proposal = next(e for e in snapshot if e["kind"] == "proposal")
        proposal["token"]["recipient"] = "recipient-B"
        snapshot.clear()
        sim.authority[token.subject]["valid"] = False
        sim.receipts.clear()
        self.assertTrue(sim.propose("call-A", token)["oracle_valid"])
        self.assertEqual([e["sequence"] for e in sim.events],
                         list(range(1, len(sim.events) + 1)))

    def test_queued_duplicates_before_after_drain_and_cancel(self):
        sim, token = prepared(queued=True)
        first = sim.propose("call-A", token)
        self.assertEqual(sim.propose("call-A", token), first)
        sim.propose("call-B", token)
        outcomes = sim.drain()
        self.assertTrue(outcomes["call-A"]["applied"])
        self.assertFalse(outcomes["call-B"]["applied"])
        self.assertEqual(sim.propose("call-A", token), outcomes["call-A"])
        canceled, token = prepared(queued=True)
        canceled.propose("call-C", token)
        canceled.stop("batch")
        self.assertEqual(canceled.propose("call-C", token)["status"], "canceled")
        with self.assertRaises(ValueError):
            canceled.propose("call-C", replace(token, scope="other"))

    def test_identity_rotation_and_cached_new_token_false_blocking(self):
        sim, old = prepared()
        sim.authorize(old.subject, "recipient-B")
        self.assertFalse(sim.propose("old-call", old)["applied"])
        cached, old = prepared("cached")
        cached.revoke(old.subject)
        cached.authorize(old.subject, old.recipient)
        new = cached.prepare(old.subject, "item-B")
        outcome = cached.propose("new-call", new)
        self.assertFalse(outcome["applied"])
        self.assertTrue(outcome["oracle_valid"])

    def test_fail_open_unprepared_token_and_service_recovery(self):
        sim, token = prepared(fail_open=True)
        sim.set_available(False)
        wrong = replace(token, item="unprepared")
        result = sim.propose("bad-call", wrong)
        self.assertTrue(result["applied"])
        self.assertFalse(result["oracle_valid"])
        sim.set_available(True)
        self.assertTrue(sim.propose("good-call", token)["applied"])
        self.assertFalse(sim.receipts["bad-call"]["oracle_valid"])


if __name__ == "__main__":
    unittest.main()
