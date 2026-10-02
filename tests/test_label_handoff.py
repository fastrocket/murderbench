from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'benchmark'))
import prepare_label_handoff as handoff

class LabelHandoffTests(unittest.TestCase):
    def test_provider_and_reasoning_metadata_do_not_enter_reviewer_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'private').mkdir()
            with closing(sqlite3.connect(root/'private/full.sqlite')) as db:
                db.execute('CREATE TABLE calls (id,spec,response,observation)')
                spec={'model':'hidden_model','case':{'id':'case'},'timing':'early','branch':'stable','repeat':0,'request_payload':{'messages':[{'role':'user','content':'synthetic condition'}]}}
                response={'id':'hidden_generation','provider':'hidden_provider','choices':[{'message':{'content':'visible output','reasoning':'hidden_reasoning','tool_calls':[{'id':'hidden_provider_call_id','extra':'hidden_extra','function':{'name':'propose_action','arguments':'{"action":"pause"}','reasoning':'hidden_nested_reasoning'}}]}}]}
                db.execute('INSERT INTO calls VALUES (?,?,?,?)',('hidden_call',json.dumps(spec),json.dumps(response),json.dumps({'status':'valid'})));db.commit()
            manifest={'roster':[{'model':'hidden_model'}],'cases':[{'id':'case'}],'timings':['early','late'],'branches':['stable','changed'],'repetitions':1}
            with closing(sqlite3.connect(root/'private/full.sqlite')) as db:
                db.execute('CREATE TABLE meta (key,value)')
                db.execute('INSERT INTO meta VALUES (?,?)',('manifest_hash',handoff.digest(manifest)))
                absent={**spec,'branch':'changed'}
                db.execute('INSERT INTO calls VALUES (?,?,?,?)',('hidden_absent',json.dumps(absent),None,None));db.commit()
            with patch.object(handoff,'ROOT',root), patch.object(handoff,'validated_manifest',return_value=manifest):
                handoff.main()
                public=(root/'private/label-handoff/records.json').read_text()
                self.assertFalse(any(value in public for value in ['hidden_model','hidden_generation','hidden_provider','hidden_reasoning','hidden_call','hidden_extra','hidden_nested_reasoning']))
                self.assertIn('visible output',public)
                records=json.loads(public)
                self.assertTrue(all(value is None for record in records for value in record['labels'].values()))
                self.assertEqual(sum(record['raw_response_present'] for record in records),1)
                self.assertIn('hidden_model',(root/'private/label-handoff/owner-only-mapping.json').read_text())
                self.assertEqual(json.loads((root/'private/label-handoff/coverage.json').read_text())['missing'],2)
                self.assertNotIn('hidden_model',(root/'private/label-handoff/missing.json').read_text())
                with self.assertRaises(RuntimeError): handoff.main()

    def test_malformed_outputs_and_active_collection(self):
        for response in [None, [], {'choices':[None]}, {'choices':'bad'}, {'choices':[{'message':None}]}]:
            self.assertEqual(handoff.reviewer_output(response)['tool_proposals'],[])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'private').mkdir();(root/'private/runner.lock').write_text('active')
            with patch.object(handoff,'ROOT',root), patch.object(handoff,'validated_manifest') as validate:
                with self.assertRaises(FileExistsError): handoff.main()
                validate.assert_not_called()
            self.assertEqual((root/'private/runner.lock').read_text(),'active')
