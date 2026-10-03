from copy import deepcopy
import unittest
from benchmark.necessity_resource_probe import ProbeEnvironment, ProbeWorld, ProbeContract, MESSAGE
from benchmark.necessity_resource_probe_calibration import run_policy
from benchmark.necessity_resource_probe_analysis import diagnose


class ProbeAnalysisTests(unittest.TestCase):
    def test_consumption_loses_option_before_need_revealed(self):
        for need in (False, True):
            env = ProbeEnvironment(ProbeWorld(need))
            run_policy(env, "probe_conditional")
            result = diagnose(env._contract, MESSAGE, env.events)
            self.assertEqual(result["first_loss_event_sequence"], 1)
            self.assertEqual(len(result["prefixes"][1]["conditioned_support"]), 2)
            self.assertEqual(result["prefixes"][1]["minimum_expected_constraint_loss"], 2.5)

    def test_certificate_control_retains_feasibility_both_worlds(self):
        for need in (False, True):
            env = ProbeEnvironment(ProbeWorld(need))
            run_policy(env, "certificate_conditional")
            result = diagnose(env._contract, MESSAGE, env.events)
            self.assertIsNone(result["first_loss_event_sequence"])
            self.assertTrue(all(p["feasible"] for p in result["prefixes"]))
            self.assertEqual(len(result["prefixes"][1]["conditioned_support"]), 1)

    def test_time_obstruction_and_repair(self):
        for deadline, expected in ((2, 1), (3, None)):
            env = ProbeEnvironment(ProbeWorld(True), ProbeContract(2, deadline, 2))
            run_policy(env, "probe_conditional")
            self.assertEqual(diagnose(env._contract, MESSAGE, env.events)["first_loss_event_sequence"], expected)

    def test_tampered_or_nonterminal_trace_rejected(self):
        env = ProbeEnvironment(ProbeWorld(True))
        run_policy(env, "certificate_conditional")
        tampered = deepcopy(env.events)
        tampered[0]["result"]["observation"]["reserve_remaining"] = 90
        for trace in (tampered, env.events[:1], []):
            with self.assertRaises(ValueError):
                diagnose(env._contract, MESSAGE, trace)
