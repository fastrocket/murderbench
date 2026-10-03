from copy import deepcopy
from contextlib import closing
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from benchmark.necessity_events import EventEnvironment, EventWorld, EventContract
from benchmark.necessity_native import Ledger, decode_action, legacy_accounted, payload_for, run_episode
from benchmark.necessity_oracle import DEFAULT_WEIGHTS


ROUTE = {"model":"test/model","provider":"test","provider_name":"Test"}


def response(action="finish",identity="call-1",cost="0.01"):
    return {"model":ROUTE["model"],"provider":ROUTE["provider_name"],"usage":{"cost":cost},
            "choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","content":None,
                "reasoning_details":[{"type":"reasoning.encrypted","data":"opaque-signature"}],
                "tool_calls":[{"id":identity,"type":"function","function":{
                    "name":action,"arguments":json.dumps({"claim":"unknown"} if action == "finish" else {})}}]}}]}


class NativeDriver(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/"necessity-native.sqlite"
        self.ledger = Ledger(self.path,baseline=lambda:Decimal("36.4"))

    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()

    def run_case(self,transport,episode="episode"):
        worlds = [EventWorld(False,True),EventWorld(True,True)]
        env = EventEnvironment(worlds[1],EventContract(max_calls=3))
        result = run_episode(env,ROUTE,[asdict(w) for w in worlds],[.5,.5],DEFAULT_WEIGHTS,
                             episode,"study",self.ledger,transport)
        return env,result

    def test_native_tool_execution_and_reasoning_roundtrip(self):
        packets = []
        def transport(packet):
            packets.append(deepcopy(packet))
            return response(("request_verification","wait","transfer")[len(packets)-1],str(len(packets)))
        env,result = self.run_case(transport)
        self.assertEqual(result["status"],"completed")
        self.assertTrue(result["outcome"]["saved"])
        self.assertEqual(result["outcome"]["authority_breaches"],0)
        self.assertEqual(packets[1]["messages"][2]["reasoning_details"],
                         response()["choices"][0]["message"]["reasoning_details"])
        self.assertEqual(packets[1]["messages"][3]["tool_call_id"],"1")
        self.assertNotIn("realized_world_index",packets[0]["messages"][1]["content"])

    def test_received_prefix_resumes_without_billable_retry(self):
        self.run_case(lambda packet:response())
        _,result = self.run_case(lambda packet:self.fail("must reuse saved receipt"))
        self.assertTrue(result["attempts"][0]["reused_receipt"])
        self.assertEqual(self.ledger.conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0],1)

    def test_multi_call_response_has_no_partial_effect(self):
        receipt = response("transfer")
        receipt["choices"][0]["message"]["tool_calls"].append(
            response("finish",identity="second")["choices"][0]["message"]["tool_calls"][0])
        env,result = self.run_case(lambda packet:receipt)
        self.assertEqual(result["reason"],"requires_exactly_one_tool")
        self.assertEqual(env.events,[])
        self.assertIsNone(result["outcome"])

    def test_malformed_arguments_and_duplicate_ids_rejected(self):
        for arguments in ('{"action":"transfer","claim":"saved"}',
                          '{"action":"transfer","shell":"anything"}',
                          '{"action":"finish","action":"transfer"}',
                          '{"action":[]}', '["transfer"]', '{"action":"finish","claim":null}'):
            receipt = response()
            receipt["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = arguments
            with self.assertRaises(ValueError):
                decode_action(receipt,ROUTE,set())
        with self.assertRaisesRegex(ValueError,"duplicate_tool_id"):
            decode_action(response(),ROUTE,{"call-1"})

    def test_identity_mismatch_and_output_exhaustion_are_unknown(self):
        for receipt,reason in ((response(),"identity_unknown"),(response(),"token_limit")):
            if reason == "identity_unknown":
                receipt["provider"] = "Different"
            else:
                receipt["choices"][0]["finish_reason"] = "length"
            env,result = self.run_case(lambda packet:receipt,episode=reason)
            self.assertEqual(result["reason"],reason)
            self.assertEqual(env.events,[])

    def test_missing_cost_and_transport_exception_hold_without_retry(self):
        receipt = response()
        receipt.pop("usage")
        with self.assertRaisesRegex(RuntimeError,"cost unresolved"):
            self.run_case(lambda packet:receipt)
        row = self.ledger.conn.execute("SELECT state,amount,response FROM calls").fetchone()
        self.assertEqual(row[:2],("held","1.00"))
        self.assertIsNotNone(row[2])
        with self.assertRaisesRegex(RuntimeError,"never retry"):
            self.run_case(lambda packet:self.fail("held request cannot retry"))

    def test_transport_exception_preserves_hold(self):
        def broken(packet):
            raise TimeoutError("timeout")
        with self.assertRaises(TimeoutError):
            self.run_case(broken)
        self.assertEqual(self.ledger.conn.execute("SELECT state,error FROM calls").fetchone(),
                         ("held","transport_unknown"))

    def test_accounted_reservation_admission_is_shared_between_connections(self):
        self.ledger.close()
        self.ledger = Ledger(self.path,baseline=lambda:Decimal("49"))
        self.ledger.reserve("one","study",{"a":1})
        other = Ledger(self.path,baseline=lambda:Decimal("49"))
        try:
            with self.assertRaisesRegex(RuntimeError,"unresolved"):
                other.reserve("two","study",{"a":2})
            self.ledger.receive("one",{"usage":{"cost":"1"}})
            with self.assertRaisesRegex(RuntimeError,"budget"):
                other.reserve("two","study",{"a":2})
        finally:
            other.close()

    def test_payload_identity_change_and_cost_overrun_stop(self):
        self.ledger.reserve("one","study",{"a":1})
        self.ledger.receive("one",{"usage":{"cost":"0.1"}})
        with self.assertRaisesRegex(RuntimeError,"mismatch"):
            self.ledger.reserve("one","study",{"a":2})
        self.ledger.reserve("two","study",{"a":2})
        with self.assertRaisesRegex(RuntimeError,"exceeds"):
            self.ledger.receive("two",{"usage":{"cost":"1.1"}})
        self.assertEqual(self.ledger.conn.execute("SELECT state,amount FROM calls WHERE id='two'").fetchone(),
                         ("held","1.1"))

    def test_input_gate_before_request(self):
        with self.assertRaisesRegex(RuntimeError,"byte gate"):
            payload_for(ROUTE,[{"role":"user","content":"x"*21000}])

    def test_separate_study_retains_previous_hold_in_lifetime_admission(self):
        self.ledger.close()
        self.ledger = Ledger(self.path,baseline=lambda:Decimal("48"))
        self.ledger.reserve("old","old-study",{"a":1})
        self.ledger.hold("old","transport_unknown")
        self.ledger.reserve("new","new-study",{"a":2})
        self.assertEqual(self.ledger.summary()["lifetime_accounted_usd"],"50.00")
        with self.assertRaisesRegex(RuntimeError,"budget"):
            self.ledger.reserve("another","third-study",{"a":3})
        with self.assertRaisesRegex(RuntimeError,"never retry"):
            self.ledger.reserve("old","old-study",{"a":1})

    def test_second_receipt_cannot_change_reconciled_cost(self):
        self.ledger.reserve("one","study",{"a":1})
        self.ledger.receive("one",{"usage":{"cost":"0.1"}})
        with self.assertRaisesRegex(RuntimeError,"already saved"):
            self.ledger.receive("one",{"usage":{"cost":"2"}})
        self.assertEqual(self.ledger.conn.execute("SELECT state,amount FROM calls").fetchone(),("received","0.1"))

    def test_legacy_baseline_avoids_double_counting_stored_prior(self):
        root = Path(self.temp.name)
        private = root/"private"
        private.mkdir()
        (private/"cost-ledger.jsonl").write_text('{"id":"a","amount":"2"}\n',encoding="utf-8")
        with closing(sqlite3.connect(private/"native.sqlite",isolation_level=None)) as conn:
            conn.execute("CREATE TABLE calls(amount TEXT)")
            conn.execute("INSERT INTO calls VALUES ('1')")
        with closing(sqlite3.connect(private/"full.sqlite",isolation_level=None)) as conn:
            conn.execute("CREATE TABLE calls(amount TEXT)")
            conn.execute("INSERT INTO calls VALUES ('10')")
            conn.execute("CREATE TABLE meta(key TEXT,value TEXT)")
            conn.execute("INSERT INTO meta VALUES ('prior_cost','3')")
        self.assertEqual(legacy_accounted(root),Decimal("13"))
        (private/"cost-ledger.jsonl").write_text('{"id":"a","amount":"4"}\n',encoding="utf-8")
        self.assertEqual(legacy_accounted(root),Decimal("15"))


if __name__ == "__main__":
    unittest.main()
