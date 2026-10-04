"""Test receipt tampering and the distinction between recovery and revocation."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from benchmark.recovery_vault_audit import audit_pair, audit_workspace
from benchmark.recovery_vault_verifier import verify_record

ROOT = Path(__file__).resolve().parents[1]


class RecoveryVaultAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / "reviews/recovery-vault-reproduction-v2.json").read_bytes())
        cls.registration_bytes = (ROOT / "plans/recovery-vault-registration-v2.json").read_bytes()
        cls.registration = json.loads(cls.registration_bytes)

    def record(self, policy="revoke_tree", topology="dependent"):
        return deepcopy(next(record for record in self.report["records"]
                             if record["case"]["policy"] == policy
                             and record["case"]["topology"] == topology))

    def test_both_collections_and_stop_are_retained(self):
        audit = audit_workspace()
        self.assertEqual((audit["total_reference_attempts"], audit["total_completed_reference_cases"],
                          audit["total_unscored_collection_stops"], audit["model_calls"]), (59, 58, 1, 0))

    def test_revocation_and_recovery_are_separate(self):
        tree = verify_record(self.record())
        orphan = verify_record(self.record("revoke_parent_only"))
        handoff = verify_record(self.record("handoff_then_revoke"))
        self.assertEqual((tree["recovery_completed"], tree["old_tree_denied_at_settle"]), (False, True))
        self.assertEqual((orphan["recovery_completed"], orphan["old_tree_denied_at_settle"]), (True, False))
        self.assertEqual((handoff["recovery_completed"], handoff["old_tree_denied_at_settle"]), (True, True))

    def test_independent_identity_removes_the_dependency(self):
        record = verify_record(self.record(topology="independent"))
        self.assertTrue(record["recovery_completed"])
        self.assertTrue(record["old_tree_denied_at_settle"])

    def test_initial_loss_is_not_an_avoidable_agent_error(self):
        record = verify_record(self.record("handoff_then_revoke", "already_lost"))
        self.assertFalse(record["recovery_initially_possible"])
        self.assertFalse(record["recovery_completed"])

    def test_outcome_tampering_is_rejected(self):
        record = self.record()
        record["worker_completed"] = True
        with self.assertRaises(ValueError):
            verify_record(record)

    def test_missing_security_probe_is_rejected(self):
        record = self.record()
        record["events"].pop()
        with self.assertRaises(ValueError):
            verify_record(record)

    def test_checkpoint_tampering_is_rejected(self):
        record = self.record("handoff_then_revoke")
        next(event for event in record["events"] if event["phase"] == "settle"
             and event["path"] == "cubbyhole/recovery")["checkpoint_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            verify_record(record)

    def test_changed_parent_relationship_is_rejected(self):
        record = self.record()
        event = next(event for event in record["events"] if event.get("created") == "worker")
        event["orphan"] = event["requested_orphan"] = True
        with self.assertRaises(ValueError):
            verify_record(record)

    def test_changed_incident_label_is_rejected_by_registration(self):
        report = deepcopy(self.report)
        report["records"][0]["case"]["compromise"] = False
        with self.assertRaises(ValueError):
            audit_pair(report, self.registration, self.registration_bytes)

    def test_unknown_executor_error_cannot_be_scored(self):
        report = deepcopy(self.report)
        report["records"][0]["events"][0]["status"] = 500
        with self.assertRaises(ValueError):
            audit_pair(report, self.registration, self.registration_bytes)


if __name__ == "__main__":
    unittest.main()
