from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from benchmark.necessity_authorized_ledger import AuthorizedLedger
from benchmark.necessity_matched_pilot import prepare, environment, calibration, collect, analyze
from benchmark.necessity_resource_probe_native import public_packet
from tests.test_necessity_native import ROUTE, response


class AuthorizedBudgetTests(unittest.TestCase):
    def test_shared_lifetime_cap_counts_held_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "necessity-native.sqlite"
            first = AuthorizedLedger(path, "abc", baseline=lambda: Decimal("99"))
            other = AuthorizedLedger(path, "def", baseline=lambda: Decimal("99"))
            try:
                first.reserve("one", "abc/model", {"a": 1})
                first.hold("one", "transport_unknown")
                with self.assertRaisesRegex(RuntimeError, "budget"):
                    other.reserve("two", "def/model", {"a": 2})
                self.assertEqual(other.summary()["lifetime_accounted_usd"], "100.00")
                with self.assertRaisesRegex(RuntimeError, "never retry"):
                    first.reserve("one", "abc/model", {"a": 1})
                self.assertEqual(first.conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0], 1)
            finally:
                first.close(); other.close()

    def test_group_cap_and_receipt_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizedLedger(Path(directory) / "necessity-native.sqlite", "abc", baseline=lambda: 0)
            try:
                for index in range(50):
                    ledger.reserve(str(index), "abc/model", {"i": index})
                    ledger.receive(str(index), {"usage": {"cost": 1}})
                with self.assertRaisesRegex(RuntimeError, "budget"):
                    ledger.reserve("51", "abc/other", {})
                with self.assertRaisesRegex(RuntimeError, "identity"):
                    ledger.reserve("0", "abc/model", {"i": 999})
                with self.assertRaisesRegex(ValueError, "outside"):
                    ledger.reserve("bad", "def/model", {})
            finally:
                ledger.close()


class MatchedPilotTests(unittest.TestCase):
    def test_frozen_matrix_information_parity_and_scripted_controls(self):
        plan = prepare()
        self.assertEqual(len(plan["episodes"]), 192)
        self.assertEqual(sum(r["eligible"] for r in plan["episodes"]), 168)
        packets = {}
        for row in plan["episodes"]:
            key = (row["model"], row["arm"], row["capacity"], row["repetition"])
            packet = public_packet(environment(row))
            if key in packets:
                self.assertEqual(packets[key], packet)
            packets[key] = packet
        records = calibration()["records"]
        self.assertEqual(len(records), 72)
        for record in records:
            if record["policy"] == "certificate_conditional":
                self.assertEqual(record["outcome"]["primary_loss"], 0)
                self.assertEqual(record["outcome"]["authority_breaches"], 0)
            if record["policy"] == "probe_conditional" and record["capacity"] == 1 and record["need"]:
                self.assertEqual(record["outcome"]["primary_loss"], 5)

    def small_plan(self):
        plan = prepare()
        plan["episodes"] = plan["episodes"][:6]
        for row in plan["episodes"]:
            row["model"] = ROUTE["model"]
        plan["routes"] = [{"model": ROUTE["model"], "provider_tag": ROUTE["provider"], "provider_name": ROUTE["provider_name"]}]
        return plan

    def test_receipt_replay_rejects_tampered_outcomes_and_missing_cells(self):
        plan = self.small_plan()
        sent = []
        def transport(payload):
            sent.append(payload)
            action = "read_certificate" if len(payload["messages"]) == 2 else "finish"
            return response(action, identity=str(len(sent)))
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizedLedger(Path(directory) / "necessity-native.sqlite", plan["study_id"], baseline=lambda: 0)
            try:
                report = collect(plan, ledger, transport, lambda _: None)
                ledger.conn.execute("PRAGMA query_only=ON")
                result = analyze(plan, report, ledger.conn)
                self.assertEqual(result["counts"]["completed"], 6)
                self.assertEqual(result["verified_native_receipts"], 12)
                tampered = deepcopy(report)
                tampered["records"][0]["result"]["outcome"]["primary_loss"] = 5
                with self.assertRaisesRegex(ValueError, "trace differs"):
                    analyze(plan, tampered, ledger.conn)
                tampered = deepcopy(report)
                tampered["records"].pop()
                with self.assertRaisesRegex(ValueError, "lacks planned"):
                    analyze(plan, tampered, ledger.conn)
            finally:
                ledger.close()

    def test_transport_failure_keeps_hold_and_skips_route(self):
        plan = self.small_plan()
        with tempfile.TemporaryDirectory() as directory:
            ledger = AuthorizedLedger(Path(directory) / "necessity-native.sqlite", plan["study_id"], baseline=lambda: 0)
            try:
                def transport(_):
                    raise TimeoutError("synthetic")
                report = collect(plan, ledger, transport, lambda _: None)
                self.assertEqual([r["result"]["status"] for r in report["records"]], ["collection_stopped"] + ["not_attempted"] * 5)
                self.assertEqual(report["budget"]["pilot_accounted_usd"], "1.00")
                ledger.conn.execute("PRAGMA query_only=ON")
                result = analyze(plan, report, ledger.conn)
                self.assertEqual(result["counts"]["collection_stopped"], 1)
                self.assertEqual(result["counts"]["not_attempted"], 5)
            finally:
                ledger.close()
