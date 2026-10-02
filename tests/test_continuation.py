import json
from contextlib import closing
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'benchmark'))
import continue_collection as continuation
import study

class ContinuationTests(unittest.TestCase):
    def test_exclusion_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'private').mkdir()
            register = root/'register.json'
            register.write_text(json.dumps({'excluded_call_ids':[]}))
            with closing(__import__('sqlite3').connect(root/'private/full.sqlite')) as db:
                db.execute('CREATE TABLE calls (id,state,amount,response,observation)')
                for number in range(64):
                    db.execute('INSERT INTO calls VALUES (?,?,?,?,?)',(str(number),'received','0.50',json.dumps({'id':'gen','usage':None}),json.dumps({'status':'content_filter'})))
                db.commit()
            with patch.object(continuation,'REGISTER',register), patch.object(study,'ROOT',root):
                self.assertEqual(len(continuation.register_holds()),64)
                with closing(__import__('sqlite3').connect(root/'private/full.sqlite')) as db:
                    db.execute('INSERT INTO calls VALUES (?,?,?,?,?)',('65','received','0.50',json.dumps({'id':'gen','usage':None}),json.dumps({'status':'content_filter'})))
                    db.commit()
                with self.assertRaises(RuntimeError):
                    continuation.register_holds()
                self.assertEqual(len(json.loads(register.read_text())['excluded_call_ids']),64)

    def test_only_filtered_received_full_holds_are_eligible(self):
        row = ['id','received','0.50',json.dumps({'id':'gen','usage':None}),json.dumps({'status':'content_filter'})]
        self.assertTrue(continuation.eligible(row))
        for index,value in [(1,'reserved'),(2,'0.1'),(3,json.dumps({'id':'gen','usage':{'cost':0}})),(4,json.dumps({'status':'valid'}))]:
            changed = row.copy(); changed[index] = value
            self.assertFalse(continuation.eligible(changed))

    def test_skip_preserves_hold_and_blocks_any_other_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            register = Path(directory)/'register.json'
            register.write_text(json.dumps({'excluded_call_ids':['filtered']}))
            store = study.Store(Path(directory)/'db.sqlite', '49', 'hash')
            try:
                store.reserve('filtered', {'model':'test'})
                try:
                    store.response('filtered', {'id':'gen','usage':None}, {'status':'content_filter'})
                except RuntimeError:
                    pass
                with patch.object(continuation,'REGISTER',register):
                    self.assertFalse(continuation.reserve(store,'filtered',{}))
                    self.assertEqual(continuation.unresolved(store),[])
                    self.assertEqual(store.connection.execute('SELECT state,amount FROM calls').fetchone(),('received','0.50'))
                    self.assertTrue(continuation.reserve(store,'other',{}))
                    self.assertEqual(continuation.unresolved(store),[('other','reserved')])
                    with self.assertRaises(RuntimeError):
                        continuation.reserve(store,'third',{})
            finally:
                store.connection.close()
