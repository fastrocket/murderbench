import unittest
from benchmark.necessity_structural_cases import build, specification, CASES, ARMS, catalog
from benchmark.necessity_structural_native import native_tools, tools_for, payload_for


class StructuralPacketTests(unittest.TestCase):
    def test_all_initial_worlds_indistinguishable(self):
        for case in CASES:
            for arm in ARMS:
                with self.subTest(case=case,arm=arm):
                    packets = [build(case,i,arm)[1] for i in range(len(specification(case)[1]))]
                    self.assertTrue(all(p == packets[0] for p in packets))
                    self.assertEqual(set(packets[0]),{
                        "generative_support","prior","loss_weights","transition_rules",
                        "operator_prefix","prefix_origin","observation","procedure_instruction",
                        "support_interpretation"})

    def test_arms_change_only_instruction(self):
        for case in CASES:
            first = build(case,0,"baseline")[1]
            second = build(case,0,"deadline_planning")[1]
            self.assertNotEqual(first.pop("procedure_instruction"),second.pop("procedure_instruction"))
            self.assertEqual(first,second)

    def test_event_request_receipt_is_equal_before_evidence_arrives(self):
        envs = [build("verification_window",i)[0] for i in range(2)]
        receipts = [e.call("request_verification") for e in envs]
        self.assertEqual(receipts[0],receipts[1])
        self.assertNotEqual(envs[0].call("wait"),envs[1].call("wait"))

    def test_queue_request_receipt_does_not_reveal_need(self):
        envs = [build("shared_verifier_queue",i)[0] for i in range(4)]
        receipts = [e.call("verify_b") for e in envs]
        self.assertTrue(all(r == receipts[0] for r in receipts))
        self.assertFalse(receipts[0]["observation"]["evidence"])
        self.assertEqual(set(receipts[0]["observation"]["pending"][0]),
                         {"id","job","service_start","due_tick"})

    def test_all_packets_fit_actual_schema_byte_gate(self):
        route = {"model":"test/model","provider":"test"}
        for case in CASES:
            env,packet = build(case,0,"deadline_planning")
            import json
            messages = [{"role":"user","content":json.dumps(packet)}]
            payload = payload_for(route,messages,tools_for(env))
            self.assertEqual(payload["tools"],native_tools(tools_for(env)))

    def test_invalid_selection_rejected_and_catalog_not_held_out(self):
        for case,index,arm in (("unknown",0,"baseline"),(CASES[0],True,"baseline"),
                               (CASES[0],2,"baseline"),(CASES[0],0,"unknown")):
            with self.assertRaises(ValueError):
                build(case,index,arm)
        self.assertFalse(catalog()["held_out"])
        self.assertEqual(catalog()["episodes_per_route"],16)


if __name__ == "__main__":
    unittest.main()
