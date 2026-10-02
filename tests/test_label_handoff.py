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
                spec={'model':'hidden_model','request_payload':{'messages':[{'role':'user','content':'synthetic condition'}]}}
                response={'id':'hidden_generation','provider':'hidden_provider','choices':[{'message':{'content':'visible output','reasoning':'hidden_reasoning','tool_calls':[]}}]}
                db.execute('INSERT INTO calls VALUES (?,?,?,?)',('hidden_call',json.dumps(spec),json.dumps(response),json.dumps({'status':'valid'})));db.commit()
            with patch.object(handoff,'ROOT',root):
                handoff.main()
                public=(root/'private/label-handoff/records.json').read_text()
                self.assertFalse(any(value in public for value in ['hidden_model','hidden_generation','hidden_provider','hidden_reasoning','hidden_call']))
                self.assertIn('visible output',public)
                self.assertTrue(all(value is None for value in json.loads(public)[0]['labels'].values()))
                self.assertIn('hidden_model',(root/'private/label-handoff/owner-only-mapping.json').read_text())
                with self.assertRaises(RuntimeError): handoff.main()
