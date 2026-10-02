"""Verify proposal isolation and durable budget accounting."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'benchmark'))
import pilot

class PilotTests(unittest.TestCase):
    def test_action_is_strict_json(self):
        self.assertEqual(pilot.parse_action('{"action":"pause","reason":"stop"}'), 'pause')
        for text in ['complete', '{"action":"run_shell"}', '[]', 'null', '```json\n{}\n```']:
            self.assertIsNone(pilot.parse_action(text))

    def test_reservation_is_replaced_by_actual_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / 'ledger'
            pilot.append(ledger, {'id': 'a', 'amount': '0.5'})
            pilot.append(ledger, {'id': 'b', 'amount': '0.5'})
            pilot.append(ledger, {'id': 'a', 'amount': '0.02'})
            self.assertEqual(pilot.spent(ledger), pilot.Decimal('0.52'))

    def test_missing_cost_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger, output = Path(directory) / 'ledger', Path(directory) / 'output'
            with patch.object(pilot, 'request', return_value={'usage': {}}):
                with self.assertRaisesRegex(RuntimeError, 'Missing cost'):
                    pilot.call('model', [], 'secret', output, ledger, {})
            self.assertEqual(pilot.spent(ledger), pilot.RESERVATION)
            self.assertNotIn('secret', output.read_text())

    def test_budget_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger, output = Path(directory) / 'ledger', Path(directory) / 'output'
            pilot.append(ledger, {'id': 'a', 'amount': '49.51'})
            with patch.object(pilot, 'request') as request:
                with self.assertRaisesRegex(RuntimeError, 'exhausted'):
                    pilot.call('model', [], 'secret', output, ledger, {})
                request.assert_not_called()

    def test_response_is_never_executed(self):
        response = {'usage': {'cost': 0.01}, 'choices': [{'message': {'content': 'run_shell'}}]}
        with tempfile.TemporaryDirectory() as directory:
            ledger, output = Path(directory) / 'ledger', Path(directory) / 'output'
            with patch.object(pilot, 'request', return_value=response) as request:
                self.assertEqual(pilot.call('model', [], 'secret', output, ledger, {}), 'run_shell')
                self.assertEqual(request.call_count, 1)

if __name__ == '__main__':
    unittest.main()
