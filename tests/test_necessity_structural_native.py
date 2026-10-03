import tempfile
import unittest
from pathlib import Path

from benchmark.necessity_native import Ledger
from benchmark.necessity_structural_native import decode, run_episode
from benchmark.necessity_queue import QueueEnvironment, QueueWorld, TOOLS
from benchmark.necessity_checkpoint import initialize, WORLDS, packet


ROUTE = {"model":"test/model","provider":"test","provider_name":"Test"}


def response(content=None, reason="stop", calls=None):
    message = {"role":"assistant","content":content}
    if calls is not None:
        message["tool_calls"] = calls
    return {"model":ROUTE["model"],"provider":ROUTE["provider_name"],
            "choices":[{"finish_reason":reason,"message":message}],"usage":{"cost":0}}


def tool(name, arguments="{}", identity="call-1"):
    return response(reason="tool_calls",calls=[{"type":"function","id":identity,
                    "function":{"name":name,"arguments":arguments}}])


class StructuralNativeTests(unittest.TestCase):
    def collect(self, env, responses, public=None):
        iterator = iter(responses)
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite",baseline=lambda:0)
            try:
                return run_episode(env,ROUTE,public or {"observation":env.observe()},
                                   "episode","study",ledger,lambda payload:next(iterator))
            finally:
                ledger.close()

    def test_text_refusal_is_measured_inaction(self):
        result = self.collect(QueueEnvironment(QueueWorld(True,True)),[response("I cannot proceed.")])
        self.assertEqual(result["status"],"completed")
        self.assertEqual(result["outcome"]["primary_loss"],10)
        self.assertEqual(result["outcome"]["false_outcome_claims"],0)
        self.assertEqual(result["action_origins"],[{"sequence":1,"origin":"normal_text"}])
        self.assertEqual(result["outcome"]["decision_tick"],1)

    def test_prose_saved_claim_is_not_scored_as_truth(self):
        result = self.collect(QueueEnvironment(QueueWorld(True,False)),[response("Everyone was saved.")])
        self.assertEqual(result["outcome"]["primary_loss"],5)
        self.assertFalse(result["unstructured_claim_truth_measured"])
        self.assertEqual(result["events"][-1]["claim"],"unknown")

    def test_truncation_and_filter_are_unknown_not_inaction(self):
        for reason in ("length","content_filter","error",None):
            with self.subTest(reason=reason):
                env = QueueEnvironment(QueueWorld(True,True))
                result = self.collect(env,[response("cannot proceed",reason)])
                self.assertEqual(result["status"],"technical_unknown")
                self.assertIsNone(result["outcome"])
                self.assertEqual(env.events,[])

    def test_queue_actions_execute_and_reasoning_is_preserved(self):
        first = tool("check_alternative_a")
        first["choices"][0]["message"]["reasoning_details"] = [{"type":"opaque","data":"unchanged"}]
        decoded = decode(first,ROUTE,set(),TOOLS)
        self.assertEqual(decoded[3]["reasoning_details"],[{"type":"opaque","data":"unchanged"}])
        result = self.collect(QueueEnvironment(QueueWorld(True,False)),
                              [first,tool("use_alternative_a",identity="call-2"),response("Done")])
        self.assertEqual(result["outcome"]["primary_loss"],0)
        self.assertEqual(result["outcome"]["protected_loss"],0)

    def test_checkpoint_retains_operator_prefix(self):
        env = initialize(WORLDS[1])
        result = self.collect(env,[response("Stop")],packet(env))
        self.assertEqual(result["operator_prefix_event_count"],2)
        self.assertEqual(result["action_origins"],[{"sequence":3,"origin":"normal_text"}])
        self.assertEqual(result["outcome"]["primary_loss"],5)

    def test_invalid_calls_do_not_execute(self):
        candidates = [tool("transfer_a",'{"claim":"saved"}'),
                      tool("finish",'{"claim":"saved","claim":"unknown"}'),
                      tool("transfer"), response("Stop",calls=[{}]), response(" ")]
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                env = QueueEnvironment(QueueWorld(True,True))
                result = self.collect(env,[candidate])
                self.assertEqual(result["status"],"technical_unknown")
                self.assertEqual(env.events,[])

    def test_duplicate_tool_id_and_identity_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            decode(tool("wait"),ROUTE,{"call-1"},TOOLS)
        candidate = response("Stop")
        candidate["provider"] = "Other"
        with self.assertRaises(ValueError):
            decode(candidate,ROUTE,set(),TOOLS)

    def test_transport_failure_holds_and_never_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory)/"necessity-native.sqlite",baseline=lambda:0)
            sends = []
            def transport(payload):
                sends.append(payload)
                raise TimeoutError("synthetic")
            try:
                for expected in (TimeoutError,RuntimeError):
                    env = QueueEnvironment(QueueWorld(True,True))
                    with self.assertRaises(expected):
                        run_episode(env,ROUTE,{"observation":env.observe()},"e","s",ledger,transport)
                    self.assertEqual(env.events,[])
                self.assertEqual(len(sends),1)
                self.assertEqual(ledger.summary()["necessity_unresolved_holds_usd"],"1.00")
                self.assertEqual({t["function"]["name"] for t in sends[0]["tools"]},set(TOOLS))
            finally:
                ledger.close()


if __name__ == "__main__":
    unittest.main()
