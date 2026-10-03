import unittest
from unittest.mock import patch
from contextlib import nullcontext
from benchmark.necessity_resource_probe_live import admit, prepare
from benchmark import necessity_resource_probe_live as live


class ProbeLiveTests(unittest.TestCase):
    def test_actual_entry_point_blocks_before_credentials_or_transport(self):
        with patch("sys.argv", ["probe-live", "run"]), patch.object(live, "Ledger") as ledger, \
                patch.object(live, "collector_lock", return_value=nullcontext()), \
                patch.object(live, "load_key") as key, patch.object(live, "transport_for") as transport:
            ledger.return_value.summary.return_value = {"remaining_accounted_usd":"9.0647905414"}
            with self.assertRaisesRegex(RuntimeError, "eligibility"):
                live.main()
            key.assert_not_called()
            transport.assert_not_called()
            ledger.return_value.close.assert_called_once()

    def test_current_freeze_and_eligibility_block(self):
        self.assertFalse(prepare()["collection_ready"])
        with self.assertRaisesRegex(RuntimeError, "eligibility"):
            admit({"source_chains_valid":True, "unverified_routes":["google"]}, {"remaining_accounted_usd":"1000"})

    def test_budget_checked_after_route_eligibility(self):
        evidence = {"source_chains_valid":True, "unverified_routes":[], "supplement_conditional_usd":"328.22"}
        with self.assertRaisesRegex(RuntimeError, "headroom"):
            admit(evidence, {"remaining_accounted_usd":"9.06"})
        admit(evidence, {"remaining_accounted_usd":"328.22"})
