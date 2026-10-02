import sys
from pathlib import Path
import unittest
import json
import hashlib
import tempfile
from copy import deepcopy
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'benchmark'))
from analyze import summarize
import analyze
import study
from test_orchestration import fixture

class AnalysisTests(unittest.TestCase):
    def test_export_rejects_source_and_catalog_before_writing(self):
        for mutation in ['source','catalog']:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);fixture(root)
                manifest=json.loads((root/'plans/full-manifest.json').read_text())
                (root/'benchmark/analyze.py').write_text('frozen')
                manifest['source_hashes']['analyze.py']=hashlib.sha256(b'frozen').hexdigest()
                (root/'plans/full-manifest.json').write_text(json.dumps(manifest))
                if mutation=='source': (root/'benchmark/analyze.py').write_text('changed')
                else: (root/'plans/full-catalog.json').write_text('{"models":{"changed":true},"endpoints":{}}')
                with patch.object(analyze,'ROOT',root),patch.object(study,'ROOT',root):
                    with self.assertRaises(RuntimeError): analyze.export()
                self.assertFalse((root/'plans/results.json').exists())

    def test_repeat_missingness_strata_budget_and_duplicate_validation(self):
        manifest={'roster':[{'model':'test','provider_tag':'test'}], 'calls_per_model':16,'claim_scope':'test',
                  'cases':[{'id':'one','mechanism':'consent'}],'timings':['early','late'],
                  'branches':['stable','changed'],'repetitions':4}
        records=[]
        for timing,branch,repeat,status,action in [('early','stable',0,'valid','complete'),('early','stable',1,'valid','pause'),('early','stable',2,'tool_invalid',None),('early','changed',0,'valid','pause'),('late','stable',0,'valid','pause'),('late','changed',0,'valid','complete')]:
            records.append({'spec':{'model':'test','case':manifest['cases'][0],'timing':timing,'branch':branch,'repeat':repeat},
                            'state':'received','amount':'0.50','observation':{'status':status,'action':action}})
        result=summarize(manifest,records,'1.25')
        self.assertEqual(result['budget']['lifetime_accounted_usd'],'4.25')
        self.assertEqual(result['budget']['final_reconciled_spend_usd'],'0')
        model=result['models'][0]
        self.assertEqual(model['unresolved_requests'],6)
        self.assertEqual(sum(model['paired_strata']['mechanism_timing/consent/early'].values()),4)
        self.assertEqual(model['paired_strata']['mechanism_timing/consent/late']['pause / complete'],1)
        repeat=next(row for row in model['repeat_diagnostics'] if row['timing']=='early' and row['branch']=='stable')
        self.assertEqual((repeat['valid'],repeat['invalid'],repeat['missing']),(2,1,1))
        self.assertTrue(repeat['valid_action_disagreement'])
        with self.assertRaises(ValueError): summarize(manifest,records+[records[0]])
        foreign=deepcopy(records[0]);foreign['spec']['repeat']=99
        with self.assertRaises(ValueError): summarize(manifest,[foreign])
    def test_failed_control_and_missing_branch_remain_visible(self):
        manifest = {'roster': [{'model': 'test', 'provider_tag': 'test'}], 'calls_per_model': 4, 'claim_scope': 'test',
                    'cases': [{'id':'one','mechanism':'consent'},{'id':'two','mechanism':'stop'}],
                    'timings':['late'], 'branches':['stable','changed'], 'repetitions':1}
        records = [{'spec': {'model': 'test', 'case': {'id': 'one', 'mechanism': 'consent'},
                            'timing': 'late', 'repeat': 0, 'branch': 'stable'},
                    'state': 'reconciled', 'amount': '0.01', 'observation': {'status': 'valid', 'action': 'pause'}}]
        result = summarize(manifest, records)['models'][0]
        self.assertEqual(result['missing_calls'], 3)
        self.assertEqual(result['capability_conditioned_denominator'], 0)
        self.assertEqual(result['paired_table_stable_then_changed'], {'pause / missing': 1, 'missing / missing': 1})
        self.assertEqual(result['groups']['stop/late/changed']['missing'],1)
        self.assertEqual(sum(row['planned'] for row in result['groups'].values()),4)
        self.assertEqual(result['paired_strata']['context/one/late'],{'pause / missing':1})
