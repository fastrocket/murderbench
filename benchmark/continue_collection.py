"""Disclosed hold-only continuation; frozen request and scoring code is unchanged."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
import study

REGISTER = study.ROOT / 'plans/collection-amendment.json'
MAX_EXCLUSIONS = 64
original_reserve = study.Store.reserve
original_unresolved = study.Store.unresolved

def eligible(row):
    call_id, state, amount, raw, observation = row
    response = json.loads(raw) if raw else {}
    observed = json.loads(observation) if observation else {}
    return (state == 'received' and Decimal(amount) == study.RESERVE
            and isinstance(response, dict) and response.get('id')
            and response.get('usage') is None
            and observed.get('status') == 'content_filter')

def register_holds():
    register = json.loads(REGISTER.read_text())
    with closing(sqlite3.connect(study.ROOT/'private/full.sqlite')) as connection:
        rows = connection.execute("SELECT id,state,amount,response,observation FROM calls WHERE state!='reconciled'").fetchall()
    if not rows or any(not eligible(row) for row in rows):
        raise RuntimeError('No exclusively eligible content-filter receipts. Review required.')
    for row in rows:
        if row[0] not in register['excluded_call_ids']:
            register['excluded_call_ids'].append(row[0])
    if len(register['excluded_call_ids']) > MAX_EXCLUSIONS:
        raise RuntimeError('Amendment hold limit reached. Review required.')
    register['updated_utc'] = datetime.now(timezone.utc).isoformat()
    REGISTER.write_text(json.dumps(register, indent=2)+'\n')
    return set(register['excluded_call_ids'])

def approved(store, call_id):
    ids = json.loads(REGISTER.read_text())['excluded_call_ids']
    if call_id not in ids:
        return False
    row = store.connection.execute('SELECT id,state,amount,response,observation FROM calls WHERE id=?', (call_id,)).fetchone()
    if not row or not eligible(row):
        raise RuntimeError('Excluded receipt changed. Review required.')
    return True

def reserve(store, call_id, spec):
    with store.lock:
        if approved(store, call_id):
            return False
    return original_reserve(store, call_id, spec)

def unresolved(store):
    return [(call_id,state) for call_id,state in original_unresolved(store) if not approved(store,call_id)]

def main():
    manifest = study.validated_manifest()
    if json.loads(REGISTER.read_text())['manifest_sha256'] != study.digest(manifest):
        raise RuntimeError('Amendment manifest differs. Review required.')
    study.Store.reserve = reserve
    study.Store.unresolved = unresolved
    for attempt in range(MAX_EXCLUSIONS + 1):
        register_holds()
        try:
            study.collect(workers=4)
            return
        except RuntimeError as error:
            if str(error) != 'Collection stopped with unresolved or budget state.':
                raise
            # Only saved, filtered, missing-cost receipts can be excluded; no retry.
            print('Reviewing new content-filter receipts under disclosed amendment.', flush=True)
    raise RuntimeError('Continuation limit reached.')

if __name__ == '__main__':
    main()
