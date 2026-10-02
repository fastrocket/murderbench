"""Offline integration checks for durable collection and scoring."""
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'benchmark'))
from study import Store, digest
from study_cases import cases, messages, score

def response(action='pause', cost=0.01, finish='tool_calls'):
    return {'usage': {'cost': cost}, 'choices': [{'finish_reason': finish, 'message': {
        'tool_calls': [{'function': {'name': 'propose_action', 'arguments': json.dumps({'action': action, 'reason': 'test'})}}]}}]}

class StudyTests(unittest.TestCase):
    def test_branch_prompts_change_only_state(self):
        for case in cases():
            for timing in ['early', 'late']:
                left, right = messages(case, 'stable', timing), messages(case, 'changed', timing)
                self.assertEqual(left[:-1], right[:-1])
                self.assertEqual(left[-1]['content'].split('. Select')[1], right[-1]['content'].split('. Select')[1])

    def test_simulation_oracle_and_invalids(self):
        self.assertTrue(score(response('complete'), 'changed')['constraint_violation'])
        self.assertTrue(score(response('complete'), 'stable')['useful_completion'])
        self.assertFalse(score(response('pause'), 'changed')['constraint_violation'])
        for finish in ['length', 'content_filter', 'error']:
            result = score(response(finish=finish), 'changed')
            self.assertEqual(result['status'], finish)
            self.assertIsNone(result['action'])

    def test_full_durable_path_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'run.sqlite'
            store = Store(path, Decimal('1'), 'manifest')
            self.assertTrue(store.reserve('trial', {'branch': 'changed'}))
            store.response('trial', response(), score(response(), 'changed'))
            self.assertFalse(store.reserve('trial', {'branch': 'changed'}))
            store.connection.close()
            resumed = Store(path, Decimal('1'), 'manifest')
            self.assertEqual(resumed.unresolved(), [])
            row = resumed.connection.execute('SELECT state,amount,observation FROM calls').fetchone()
            self.assertEqual(row[:2], ('reconciled', '0.01'))
            self.assertEqual(json.loads(row[2])['action'], 'pause')
            resumed.connection.close()

    def test_missing_cost_blocks_resume_but_preserves_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory)/'run.sqlite', Decimal('0'), 'manifest')
            store.reserve('trial', {})
            with self.assertRaisesRegex(RuntimeError, 'Missing cost'):
                store.response('trial', response(cost=None), score(response(), 'changed'))
            self.assertEqual(store.unresolved(), [('trial', 'received')])
            with self.assertRaisesRegex(RuntimeError, 'Unresolved'):
                store.reserve('trial', {})
            row = store.connection.execute('SELECT amount,observation FROM calls').fetchone()
            self.assertEqual(row[0], '0.50')
            self.assertIsNotNone(row[1])
            store.connection.close()

    def test_budget_reservations_cover_inflight_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory)/'run.sqlite', Decimal('49.1'), 'manifest')
            store.reserve('one', {})
            with self.assertRaisesRegex(RuntimeError, 'Budget'):
                store.reserve('two', {})
            store.connection.close()

    def test_manifest_change_refuses_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'run.sqlite'
            first = Store(path, Decimal('0'), 'a')
            first.connection.close()
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                Store(path, Decimal('0'), 'b')

    def test_invalid_cost_retains_reservation(self):
        for cost in [-1, 2, 'NaN', 'Infinity']:
            with tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory)/'run.sqlite', Decimal('0'), 'manifest')
                store.reserve('trial', {})
                with self.assertRaises(RuntimeError):
                    store.response('trial', response(cost=cost), {})
                self.assertEqual(store.unresolved(), [('trial', 'received')])
                store.connection.close()

if __name__ == '__main__':
    unittest.main()
