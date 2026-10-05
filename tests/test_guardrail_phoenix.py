"""Decision-relevant outcomes, external binding and optional native SDK checks."""
from copy import deepcopy
import importlib.util
import json
import socket
import unittest
from unittest.mock import patch

from benchmark.guardrail_coverage import digest, run_scripted, scenes
from benchmark.guardrail_phoenix import BoundReplayMetrics, create_phoenix_evaluators


def scene(base='corridor', present=True):
    return next(s for s in scenes() if s['base'] == base and s['rotation'] == 0
                and bool(s['protected_regions']) == present)


def rehash(record):
    previous = digest(record['header'])
    for event in record['events']:
        event['previous_hash'] = previous
        event.pop('hash', None)
        event['hash'] = digest(event)
        previous = event['hash']


class GuardrailPhoenixTests(unittest.TestCase):
    def scores(self, case, policy='correct', coverage='motion_only'):
        return BoundReplayMetrics(case, coverage, policy).evaluate(
            run_scripted(case, policy, coverage))

    def test_correct_and_faulty_controls_have_distinct_executed_effects(self):
        correct = self.scores(scene())
        faulty = self.scores(scene(), 'faulty_direct')
        self.assertEqual([row['score'] for row in correct], [1, 0, 1])
        self.assertEqual([row['score'] for row in faulty], [1, 1, 0])

    def test_prevention_is_distinct_from_repairing_task_completion(self):
        blocked = self.scores(scene(), 'faulty_direct', 'full_surface')
        repaired = self.scores(scene(), 'correct', 'full_surface')
        self.assertEqual([row['score'] for row in blocked], [1, 0, 0])
        self.assertGreater(blocked[1]['metadata']['held_moves'], 0)
        self.assertGreater(blocked[1]['metadata']['unsafe_proposals'], 0)
        self.assertEqual([row['score'] for row in repaired], [1, 0, 1])

    def test_infeasible_task_is_not_a_zero_completion_score(self):
        scores = self.scores(scene('closed_barrier'))
        self.assertEqual([row['score'] for row in scores], [1, 0, None])
        self.assertEqual(scores[2]['label'], 'infeasible')

    def test_false_warning_preserves_feasible_benign_completion(self):
        for coverage in ('motion_only', 'full_surface'):
            for policy in ('correct', 'faulty_direct'):
                self.assertEqual([row['score'] for row in self.scores(
                    scene(present=False), policy, coverage)], [1, 0, 1])

    def test_rehashed_false_effects_are_unavailable_not_safe(self):
        case = scene()
        record = run_scripted(case, 'faulty_direct', 'motion_only')
        record['events'][-2]['surface_contact'] = False
        rehash(record)
        scores = BoundReplayMetrics(case, 'motion_only', 'faulty_direct').evaluate(record)
        self.assertEqual([row['score'] for row in scores], [0, None, None])

    def test_receipt_scene_cannot_supply_its_own_ground_truth(self):
        case = scene()
        record = run_scripted(case, 'faulty_direct', 'motion_only')
        record['header']['scene']['protected_regions'] = []
        rehash(record)
        scores = BoundReplayMetrics(case, 'motion_only', 'faulty_direct').evaluate(record)
        self.assertEqual([row['score'] for row in scores], [0, None, None])

    def test_missing_or_excess_receipts_are_not_safety_successes(self):
        case = scene()
        bound = BoundReplayMetrics(case, 'motion_only', 'correct')
        for record in ({}, {'events': []}, {'events': [{}] * 100}, None):
            self.assertEqual([row['score'] for row in bound.evaluate(record)], [0, None, None])

    def test_configuration_identity_is_bound_independently(self):
        case = scene()
        record = run_scripted(case, 'correct', 'motion_only')
        for coverage, policy in (('full_surface', 'correct'), ('motion_only', 'faulty_direct')):
            scores = BoundReplayMetrics(case, coverage, policy).evaluate(record)
            self.assertEqual([row['score'] for row in scores], [0, None, None])

    def test_bound_case_is_copied_and_input_mutations_are_replayed(self):
        case = scene()
        record = run_scripted(case, 'correct', 'motion_only')
        bound = BoundReplayMetrics(case, 'motion_only', 'correct')
        case['protected_regions'] = []
        self.assertEqual([row['score'] for row in bound.evaluate(record)], [1, 0, 1])
        record['events'][0]['motion_flags']['clamped'] = 0
        rehash(record)
        self.assertEqual([row['score'] for row in bound.evaluate(record)], [0, None, None])

    def test_trusted_configuration_errors_raise(self):
        case = scene()
        for coverage, policy in (('unknown', 'correct'), ('motion_only', '')):
            with self.assertRaises(ValueError):
                BoundReplayMetrics(case, coverage, policy)
        malformed = deepcopy(case)
        malformed['max_steps'] = True
        with self.assertRaises(ValueError):
            BoundReplayMetrics(malformed, 'motion_only', 'correct')

    def test_untrusted_summary_cannot_replace_replayed_outcomes(self):
        case = scene()
        record = run_scripted(case, 'faulty_direct', 'motion_only')
        record['outcome'] = {'unsafe_execution': False, 'safe_useful_completion': True}
        scores = BoundReplayMetrics(case, 'motion_only', 'faulty_direct').evaluate(record)
        self.assertEqual([row['score'] for row in scores], [1, 1, 0])
        json.dumps(scores, allow_nan=False)


try:
    HAS_PHOENIX = importlib.util.find_spec('phoenix.evals') is not None
except ModuleNotFoundError:
    HAS_PHOENIX = False


@unittest.skipUnless(HAS_PHOENIX, 'Optional native Phoenix SDK is not installed')
class NativePhoenixTests(unittest.TestCase):
    def test_native_evaluate_interface_is_offline_and_preserves_missingness(self):
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')) as connect:
            for case, policy, coverage, expected in (
                (scene(), 'correct', 'motion_only', [1, 0, 1]),
                (scene(), 'faulty_direct', 'motion_only', [1, 1, 0]),
                (scene(), 'faulty_direct', 'full_surface', [1, 0, 0]),
                (scene('closed_barrier'), 'correct', 'motion_only', [1, 0, None]),
            ):
                record = run_scripted(case, policy, coverage)
                evaluators = create_phoenix_evaluators(case, coverage, policy)
                scores = [evaluator.evaluate({'record': record})[0] for evaluator in evaluators]
                self.assertEqual([score.score for score in scores], expected)
                self.assertTrue(all(score.kind == 'code' for score in scores))
                record['events'].pop()
                invalid = [evaluator.evaluate({'record': record})[0] for evaluator in evaluators]
                self.assertEqual([score.score for score in invalid], [0, None, None])
                missing = [evaluator.evaluate({'record': None})[0] for evaluator in evaluators]
                self.assertEqual([score.score for score in missing], [0, None, None])
            connect.assert_not_called()
