"""No-network checks of actual runner entry points."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import threading
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'benchmark'))
import study
import pilot
from study_cases import cases
from study_cases import messages
from test_study import response

def fixture(root, reviews=False):
    (root/'plans').mkdir()
    (root/'benchmark').mkdir()
    (root/'reviews').mkdir()
    snapshots = {'models': {}, 'endpoints': {}}
    (root/'plans/full-catalog.json').write_text(json.dumps(snapshots))
    (root/'benchmark/frozen.py').write_text('frozen')
    manifest = {'source_hashes': {'frozen.py': hashlib.sha256(b'frozen').hexdigest()},
                'catalog_sha256': study.digest({}), 'endpoints_sha256': study.digest({}),
                'roster': [{'model': 'test', 'provider_tag': 'test', 'config': {}}],
                'cases': cases()[:1], 'timings': ['early'], 'branches': ['stable','changed'],
                'repetitions': 1, 'seed': 1, 'calls_per_model': 2}
    (root/'plans/full-manifest.json').write_text(json.dumps(manifest))
    payload = {'model':'test','messages':messages(manifest['cases'][0],'changed','early')}
    (root/'plans/eligibility.json').write_text(json.dumps({'manifest_sha256': study.digest(manifest),
                                                        'entries': [{'model':'test','disposition':'eligible',
                                                                     'configuration_sha256':study.digest(payload),
                                                                     'evidence':[{'status':'valid','call_id':'a'*64}]}]}))
    if reviews:
        for i in range(1,11):
            (root/f'reviews/round{i}.txt').write_text('Completed independent critic report. '*10)

class OrchestrationTests(unittest.TestCase):
    def test_started_sibling_response_reconciles_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixture(root,True)
            path=root/'plans/full-manifest.json'
            manifest=json.loads(path.read_text());manifest['repetitions']=3;manifest['calls_per_model']=6
            path.write_text(json.dumps(manifest))
            eligibility_path=root/'plans/eligibility.json'
            eligibility=json.loads(eligibility_path.read_text());eligibility['manifest_sha256']=study.digest(manifest)
            eligibility_path.write_text(json.dumps(eligibility))
            barrier=threading.Barrier(2)
            failure_saved=threading.Event()
            counter=iter([{'http_status':503,'error_body':'test'},response()])
            mutex=threading.Lock()
            def fake_fetch(*args):
                with mutex: result=next(counter)
                barrier.wait(timeout=5)
                if 'choices' in result:
                    if not failure_saved.wait(timeout=5): raise AssertionError('Failure did not stop queued work.')
                return result
            original_error=study.Store.error
            def saved_error(store,call_id,name):
                original_error(store,call_id,name);failure_saved.set()
            with patch.object(study,'ROOT',root),patch.object(study,'load_key',return_value='test-only'),patch.object(study,'fetch',side_effect=fake_fetch) as network,patch.object(study.Store,'error',saved_error):
                with self.assertRaisesRegex(RuntimeError,'stopped'): study.collect(2)
                self.assertEqual(network.call_count,2)
            with closing(sqlite3.connect(root/'private/full.sqlite')) as connection:
                rows=connection.execute('SELECT state,response,observation,amount FROM calls').fetchall()
            self.assertEqual(sorted(row[0] for row in rows),['received','reconciled'])
            self.assertTrue(all(row[1] and row[2] for row in rows))
            self.assertEqual(sorted(row[3] for row in rows),['0.01','0.50'])
            with patch.object(study,'ROOT',root),patch.object(study,'load_key',return_value='test-only'),patch.object(study,'fetch') as network:
                with self.assertRaisesRegex(RuntimeError,'Unresolved'): study.collect(2)
                network.assert_not_called()
            self.assertFalse((root/'private/runner.lock').exists())

    def test_prior_isolated_holds_block_network_at_lifetime_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixture(root,True);(root/'private').mkdir()
            with closing(sqlite3.connect(root/'private/native-test.sqlite')) as connection:
                connection.execute('CREATE TABLE calls (amount TEXT)')
                connection.execute('INSERT INTO calls VALUES (?)',('49.6',));connection.commit()
            with patch.object(study,'ROOT',root),patch.object(study,'load_key',return_value='test-only'),patch.object(study,'fetch') as network:
                with self.assertRaisesRegex(RuntimeError,'stopped'): study.collect(1)
                network.assert_not_called()

    def test_timeout_retains_reservation_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixture(root,True)
            with patch.object(study,'ROOT',root),patch.object(study,'load_key',return_value='test-only'),patch.object(study,'fetch',side_effect=TimeoutError('test')) as network:
                with self.assertRaisesRegex(RuntimeError,'stopped'): study.collect(1)
                self.assertEqual(network.call_count,1)
            with closing(sqlite3.connect(root/'private/full.sqlite')) as connection:
                row=connection.execute('SELECT state,response,amount,error FROM calls').fetchone()
            self.assertEqual(row,('reserved',None,'0.50','TimeoutError'))
    def test_invalid_eligibility_blocks_before_key_or_network(self):
        for mutation in ['hash','duplicate','evidence','catalog']:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture(root,True)
                path=root/'plans/eligibility.json'
                register=json.loads(path.read_text())
                if mutation=='hash': register['entries'][0]['configuration_sha256']='wrong'
                if mutation=='duplicate': register['entries'].append(register['entries'][0])
                if mutation=='evidence': register['entries'][0]['evidence']=[]
                if mutation=='catalog': (root/'plans/full-catalog.json').write_text('{"models":{"changed":true},"endpoints":{}}')
                path.write_text(json.dumps(register))
                with patch.object(study,'ROOT',root),patch.object(study,'load_key') as key,patch.object(study,'fetch') as network:
                    with self.assertRaises(RuntimeError): study.collect(1)
                    key.assert_not_called();network.assert_not_called()
    def test_before_round_ten_no_key_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            with patch.object(study,'ROOT',root), patch.object(study,'load_key') as key, patch.object(study,'fetch') as network:
                with self.assertRaisesRegex(RuntimeError,'ten critique'):
                    study.collect(1)
                key.assert_not_called()
                network.assert_not_called()

    def test_both_entry_points_reject_changed_source(self):
        for entry in [study.collect,study.smoke]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture(root)
                (root/'benchmark/frozen.py').write_text('changed')
                with patch.object(study,'ROOT',root),patch.object(study,'load_key') as key,patch.object(study,'fetch') as network:
                    with self.assertRaisesRegex(RuntimeError,'source changed'):
                        entry()
                    key.assert_not_called()
                    network.assert_not_called()

    def test_smoke_rejects_changed_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fixture(root)
            (root/'plans/full-catalog.json').write_text('{"models":{"changed":true},"endpoints":{}}')
            with patch.object(study,'ROOT',root),patch.object(study,'load_key') as key,patch.object(study,'fetch') as network:
                with self.assertRaisesRegex(RuntimeError,'catalog'): study.smoke()
                key.assert_not_called();network.assert_not_called()

    def test_real_orchestration_preserves_response_on_scorer_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root,True)
            with patch.object(study,'ROOT',root),patch.object(study,'load_key',return_value='test-only'),patch.object(study,'fetch',return_value=response()) as network,patch.object(study,'score',side_effect=ValueError('scoring failed')):
                with self.assertRaisesRegex(RuntimeError,'stopped'):
                    study.collect(1)
                self.assertEqual(network.call_count,1)
            with closing(sqlite3.connect(root/'private/full.sqlite')) as connection:
                state,raw,amount = connection.execute('SELECT state,response,amount FROM calls').fetchone()
            self.assertEqual(state,'received')
            self.assertEqual(json.loads(raw),response())
            self.assertEqual(amount,'0.50')
            self.assertFalse((root/'private/runner.lock').exists())

    def test_legacy_collection_blocked_after_final_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'private').mkdir()
            (root/'private/full.sqlite').touch()
            with patch.object(pilot,'ROOT',root),patch.object(sys,'argv',['pilot','--collect']),patch.object(pilot,'load_key') as key,patch.object(pilot,'request') as network:
                with self.assertRaisesRegex(RuntimeError,'Legacy pilot'):
                    pilot.main()
                key.assert_not_called()
                network.assert_not_called()
