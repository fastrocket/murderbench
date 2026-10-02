"""Prepare local blinded annotation records without publishing provider metadata."""
from contextlib import closing
import json
import os
from pathlib import Path
import random
import sqlite3
import uuid
from study import validated_manifest, digest

ROOT = Path(__file__).resolve().parents[1]

def reviewer_output(response):
    raw_present = response is not None
    response = response if isinstance(response,dict) else {}
    choices = response.get('choices')
    choice = choices[0] if isinstance(choices,list) and choices and isinstance(choices[0],dict) else {}
    message = choice.get('message')
    message = message if isinstance(message,dict) else {}
    proposals = []
    calls = message.get('tool_calls')
    if isinstance(calls,list):
        for call in calls:
            if not isinstance(call,dict):
                proposals.append({'malformed_call':True}); continue
            function = call.get('function')
            if not isinstance(function,dict):
                proposals.append({'malformed_function':True}); continue
            proposals.append({'type':call.get('type') if isinstance(call.get('type'),str) else None,
                              **{key:function[key] for key in ['name','arguments'] if isinstance(function.get(key),str)}})
    return {'tool_proposals':proposals,'output_text':message.get('content') if isinstance(message.get('content'),str) else None,
            'finish_reason':choice.get('finish_reason') if isinstance(choice.get('finish_reason'),str) else None,
            'http_status':response.get('http_status') if isinstance(response.get('http_status'),int) else None,
            'raw_response_present':raw_present}

def prepare():
    destination = ROOT/'private/label-handoff'
    if destination.exists():
        raise RuntimeError('Existing handoff retained. Refuse replacement.')
    manifest = validated_manifest()
    expected = {(entry['model'],case['id'],timing,branch,repeat)
                for entry in manifest['roster'] for case in manifest['cases']
                for timing in manifest['timings'] for branch in manifest['branches']
                for repeat in range(manifest['repetitions'])}
    with closing(sqlite3.connect(ROOT/'private/full.sqlite')) as connection:
        stored = connection.execute("SELECT value FROM meta WHERE key='manifest_hash'").fetchone()
        if not stored or stored[0] != digest(manifest):
            raise RuntimeError('Handoff manifest differs from collected state.')
        rows = connection.execute('SELECT id,spec,response,observation FROM calls').fetchall()
    random.SystemRandom().shuffle(rows)
    records, mapping, seen = [], [], set()
    for call_id,spec_text,response_text,observation_text in rows:
        spec = json.loads(spec_text)
        response = json.loads(response_text) if response_text else None
        key = (spec['model'],spec['case']['id'],spec['timing'],spec['branch'],spec['repeat'])
        if key not in expected or key in seen:
            raise RuntimeError('Duplicate or out-of-grid handoff condition.')
        seen.add(key)
        identifier = uuid.uuid4().hex
        records.append({'annotation_id':identifier,
                        'messages':spec['request_payload']['messages'],
                        **reviewer_output(response),
                        'labels':{'interface_validity':None,'proposed_action':None,
                                  'current_permission':None,'violation':None,
                                  'useful_completion':None,'unblinding_flag':None,
                                  'reviewer_id':None,'reviewed_utc':None,'confidence':None,'rationale':None}})
        mapping.append({'annotation_id':identifier,'call_id':call_id,'condition':{key:value for key,value in spec.items() if key!='request_payload'}})
    missing = []
    for model,case,timing,branch,repeat in sorted(expected-seen):
        identifier = uuid.uuid4().hex
        missing.append({'annotation_id':identifier,'status':'not_attempted'})
        mapping.append({'annotation_id':identifier,'call_id':None,'condition':{'model':model,'case':case,'timing':timing,'branch':branch,'repeat':repeat}})
    random.SystemRandom().shuffle(missing)
    destination.mkdir()
    (destination/'records.json').write_text(json.dumps(records,indent=2))
    (destination/'reviewer-a.json').write_text(json.dumps(records,indent=2))
    random.SystemRandom().shuffle(records)
    (destination/'reviewer-b.json').write_text(json.dumps(records,indent=2))
    (destination/'owner-only-mapping.json').write_text(json.dumps(mapping,indent=2))
    (destination/'missing.json').write_text(json.dumps(missing,indent=2))
    (destination/'coverage.json').write_text(json.dumps({'planned':len(expected),'recorded':len(records),'missing':len(missing),'independent_labels_completed':False},indent=2))
    print(f'Prepared {len(records)} local records. Labels remain blank; owner mapping must not accompany reviewer records.')

def main():
    lockpath = ROOT/'private/runner.lock'
    fd = os.open(lockpath,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        prepare()
    finally:
        os.close(fd)
        lockpath.unlink()

if __name__ == '__main__':
    main()
