import unittest
import json
import sqlite3
from unittest.mock import patch
from contextlib import nullcontext
from benchmark.necessity_resource_probe_live import admit, prepare
from benchmark import necessity_resource_probe_live as live


class ProbeLiveTests(unittest.TestCase):
    def readiness_fixture(self):
        # Exercise the live freeze and admission checks without a private ledger.
        parent = json.loads(live.PLAN.read_text(encoding="utf-8"))["parent_manifest_sha256"]
        return {"parent_manifest_sha256": parent, "source_chains_valid": True,
                "unverified_routes": ["google"]}

    def test_actual_entry_point_blocks_before_credentials_or_transport(self):
        with patch("sys.argv", ["probe-live", "run"]), patch.object(live, "Ledger") as ledger, \
                patch.object(live, "collector_lock", return_value=nullcontext()), \
                patch.object(live, "load_key") as key, patch.object(live, "transport_for") as transport, \
                patch.object(live, "check", return_value=self.readiness_fixture()):
            ledger.return_value.summary.return_value = {"remaining_accounted_usd":"9.0647905414"}
            with self.assertRaisesRegex(RuntimeError, "eligibility"):
                live.main()
            key.assert_not_called()
            transport.assert_not_called()
            ledger.return_value.close.assert_called_once()

    def test_current_freeze_and_eligibility_block(self):
        with patch.object(live, "check", return_value=self.readiness_fixture()):
            prepared = prepare()
        self.assertFalse(prepared["collection_ready"])
        self.assertEqual(prepared, json.loads(live.PLAN.read_text(encoding="utf-8")))
        with self.assertRaisesRegex(RuntimeError, "eligibility"):
            admit({"source_chains_valid":True, "unverified_routes":["google"]}, {"remaining_accounted_usd":"1000"})

    def test_unavailable_readiness_ledger_blocks_before_credentials_or_transport(self):
        with patch("sys.argv", ["probe-live", "run"]), \
                patch.object(live, "check", side_effect=sqlite3.OperationalError("unavailable ledger")), \
                patch.object(live, "Ledger") as ledger, \
                patch.object(live, "load_key") as key, patch.object(live, "transport_for") as transport:
            with self.assertRaisesRegex(sqlite3.OperationalError, "unavailable ledger"):
                live.main()
            ledger.assert_not_called()
            key.assert_not_called()
            transport.assert_not_called()

    def test_budget_checked_after_route_eligibility(self):
        evidence = {"source_chains_valid":True, "unverified_routes":[], "supplement_conditional_usd":"328.22"}
        with self.assertRaisesRegex(RuntimeError, "headroom"):
            admit(evidence, {"remaining_accounted_usd":"9.06"})
        admit(evidence, {"remaining_accounted_usd":"328.22"})
