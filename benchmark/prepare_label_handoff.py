"""Prepare local blinded annotation records without publishing provider metadata."""
from contextlib import closing
import json
from pathlib import Path
import random
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parents[1]

def main():
    destination = ROOT/'private/label-handoff'
    if destination.exists():
        raise RuntimeError('Existing handoff retained. Refuse replacement.')
    with closing(sqlite3.connect(ROOT/'private/full.sqlite')) as connection:
        rows = connection.execute('SELECT id,spec,response,observation FROM calls').fetchall()
    random.SystemRandom().shuffle(rows)
    records, mapping = [], []
    for call_id,spec_text,response_text,observation_text in rows:
        spec = json.loads(spec_text)
        response = json.loads(response_text) if response_text else {}
        observed = json.loads(observation_text) if observation_text else {}
        identifier = uuid.uuid4().hex
        choices = response.get('choices') or []
        message = choices[0].get('message',{}) if choices else {}
        records.append({'annotation_id':identifier,
                        'messages':spec['request_payload']['messages'],
                        'tool_calls':message.get('tool_calls'),
                        'output_text':message.get('content'),
                        'technical_status':observed.get('status','missing'),
                        'labels':{'interface_validity':None,'proposed_action':None,
                                  'current_permission':None,'violation':None,
                                  'useful_completion':None,'unblinding_flag':None,
                                  'reviewer_id':None,'reviewed_utc':None,'rationale':None}})
        mapping.append({'annotation_id':identifier,'call_id':call_id,'condition':{key:value for key,value in spec.items() if key!='request_payload'}})
    destination.mkdir()
    (destination/'records.json').write_text(json.dumps(records,indent=2))
    (destination/'owner-only-mapping.json').write_text(json.dumps(mapping,indent=2))
    print(f'Prepared {len(records)} local records. Labels remain blank; owner mapping must not accompany reviewer records.')

if __name__ == '__main__':
    main()
