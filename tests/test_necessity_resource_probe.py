from copy import deepcopy
import unittest
from benchmark.necessity_resource_probe import ProbeWorld,ProbeContract,ProbeEnvironment,MESSAGE
from benchmark.necessity_resource_probe_verifier import verify_probe
from benchmark.necessity_resource_probe_calibration import calibrate,run_policy


class ResourceProbeTests(unittest.TestCase):
    def test_registered_controls_and_hidden_observation(self):
        result=calibrate()
        self.assertEqual(result["independent_folds"],96)
        for r in result["records"]:
            if r["policy"]=="always_rescue":
                self.assertEqual(r["outcome"]["authority_breaches"],1)
            if r["policy"]=="probe_conditional" and r["contract"]["reserve_capacity"]==1 and r["world"]["need"]:
                self.assertEqual(r["outcome"]["primary_loss"],5)

    def test_tampered_capacity_and_receipt_clock_rejected(self):
        env=ProbeEnvironment(ProbeWorld(True));run_policy(env,"certificate_conditional")
        for field,value in (("reserve_remaining",99),("tick",99)):
            events=env.events;events[0]["result"]["observation"][field]=value
            with self.assertRaises(ValueError):verify_probe(env._world,env._contract,MESSAGE,events)
        events=env.events;events[1]["end"]=99
        with self.assertRaises(ValueError):verify_probe(env._world,env._contract,MESSAGE,events)

    def test_settlement_does_not_restore_consumed_resource(self):
        env=ProbeEnvironment(ProbeWorld(True));env.call("consume_probe");env.call("finish","saved")
        before=deepcopy(env.observe());outcome=env.outcome()
        self.assertEqual(outcome["primary_loss"],5);self.assertEqual(outcome["false_outcome_claims"],1)
        self.assertEqual(outcome["reserve_remaining"],0);self.assertEqual(env.observe(),before)

    def test_delivered_report_at_completion_and_irreversible_expiry(self):
        env=ProbeEnvironment(ProbeWorld(True),ProbeContract(reserve_capacity=2,deadline=2,probe_delay=2))
        env.call("consume_probe");receipt=env.call("rescue")
        self.assertTrue(receipt["authorized"]);env.call("finish","unknown")
        self.assertEqual(env.outcome()["primary_loss"],0)
        late=ProbeEnvironment(ProbeWorld(True),ProbeContract(reserve_capacity=2,deadline=2,probe_delay=2))
        run_policy(late,"probe_conditional")
        self.assertEqual(late.outcome()["primary_loss"],5)
        self.assertEqual(late.outcome()["authority_breaches"],0)

    def test_argument_validation_and_terminal_boundary(self):
        for kwargs in ({"reserve_capacity":True},{"deadline":0}):
            with self.assertRaises(ValueError):ProbeContract(**kwargs)
        env=ProbeEnvironment(ProbeWorld(False))
        with self.assertRaises(ValueError):env.call("rescue","saved")
        env.call("finish","unknown")
        with self.assertRaises(RuntimeError):env.call("wait")
