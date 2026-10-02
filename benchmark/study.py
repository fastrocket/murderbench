"""Freeze and collect the reviewed study without executing model actions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import random
import sqlite3
import threading
import time
import urllib.request
from pilot import API, MODELS, ROOT, load_key, spent
from study_cases import TOOL, cases, messages, score

ROUTES = ['openai', 'anthropic', 'google-ai-studio', 'xai', 'deepseek', 'alibaba', 'moonshotai/mxfp4', 'z-ai/fp8']
MAX_TOKENS = 2048
RESERVE = Decimal('0.50')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def fetch(path, key=None, payload=None):
    headers = {'Content-Type': 'application/json', 'HTTP-Referer': 'https://murderbench.com', 'X-Title': 'MurderBench reviewed study'}
    if key:
        headers['Authorization'] = 'Bearer '+key
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(urllib.request.Request(API+path, data=data, headers=headers), timeout=120) as response:
        return json.load(response)

def freeze():
    catalog = fetch('/models')
    models = {m['id']: m for m in catalog['data']}
    roster = []
    snapshots = {}
    for model, route in zip(MODELS, ROUTES):
        endpoint = fetch('/models/'+model+'/endpoints')
        snapshots[model] = endpoint
        matches = [e for e in endpoint['data']['endpoints'] if e['tag'] == route]
        if len(matches) != 1:
            raise RuntimeError(f'Pinned route is absent or ambiguous: {model} / {route}')
        entry = matches[0]
        if 'tools' not in entry['supported_parameters'] or 'tool_choice' not in entry['supported_parameters']:
            raise RuntimeError(f'Pinned route lacks native tools: {model}')
        config = {'max_tokens': MAX_TOKENS, 'reasoning': {'effort': 'low'},
                  'tools': [TOOL], 'tool_choice': {'type': 'function', 'function': {'name': 'propose_action'}},
                  'provider': {'only': [route], 'allow_fallbacks': False, 'require_parameters': True,
                               'max_price': {'prompt': 20, 'completion': 100}}, 'usage': {'include': True}}
        if 'reasoning' not in entry['supported_parameters']:
            raise RuntimeError(f'Pinned route lacks the frozen reasoning setting: {model}')
        if 'temperature' in entry['supported_parameters']:
            config['temperature'] = 0
        roster.append({'model': model, 'canonical_slug': models[model]['canonical_slug'],
                       'provider_tag': route, 'provider_name': entry['provider_name'],
                       'quantization': entry.get('quantization'), 'config': config,
                       'native_sampling_default': 'temperature' not in config})
    source_hashes = {name: hashlib.sha256((ROOT/'benchmark'/name).read_bytes()).hexdigest()
                     for name in ['study.py', 'study_cases.py']}
    manifest = {'version': 'decision-boundary-v1', 'timestamp': datetime.now(timezone.utc).isoformat(),
                'roster': roster, 'cases': cases(), 'timings': ['early', 'late'], 'branches': ['stable', 'changed'],
                'repetitions': 3, 'calls_per_model': 288, 'total_calls': 2304,
                'max_total_budget_usd': 50, 'seed': 20261002, 'source_hashes': source_hashes,
                'catalog_sha256': digest(catalog), 'endpoints_sha256': digest(snapshots),
                'claim_scope': 'fixed synthetic histories; descriptive constraint-update behavior; no injury probabilities or general safety rankings'}
    path = ROOT/'plans/full-manifest.json'
    path.write_text(json.dumps(manifest, indent=2))
    (ROOT/'plans/full-catalog.json').write_text(json.dumps({'models': catalog, 'endpoints': snapshots}, indent=2))
    print(f'Frozen manifest {digest(manifest)}. 2,304 candidate calls after round ten.')

class Store:
    def __init__(self, path, prior_cost, manifest_hash):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.connection.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, spec TEXT NOT NULL, state TEXT NOT NULL, amount TEXT NOT NULL, response TEXT, observation TEXT, error TEXT)')
        for key, value in [('prior_cost', str(prior_cost)), ('manifest_hash', manifest_hash)]:
            old = self.connection.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
            if old and old[0] != value:
                self.connection.close()
                raise RuntimeError('Stored run metadata differs. Resume refused.')
            self.connection.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', (key, value))
        self.connection.commit()

    def reserve(self, call_id, spec):
        with self.lock:
            old = self.connection.execute('SELECT state FROM calls WHERE id=?', (call_id,)).fetchone()
            if old:
                if old[0] != 'reconciled':
                    raise RuntimeError('Unresolved call. No automatic replay.')
                return False
            prior = Decimal(self.connection.execute("SELECT value FROM meta WHERE key='prior_cost'").fetchone()[0])
            total = prior + sum((Decimal(row[0]) for row in self.connection.execute('SELECT amount FROM calls')), Decimal('0'))
            if total + RESERVE > Decimal('50'):
                raise RuntimeError('Budget exhausted before request.')
            self.connection.execute('INSERT INTO calls VALUES (?,?,?,?,NULL,NULL,NULL)', (call_id, json.dumps(spec), 'reserved', str(RESERVE)))
            self.connection.commit()
            return True

    def response(self, call_id, response, observation):
        with self.lock:
            # Save response and derived observation together before cost validation.
            self.connection.execute('UPDATE calls SET state=?, response=?, observation=? WHERE id=?',
                                    ('received', json.dumps(response), json.dumps(observation), call_id))
            self.connection.commit()
            cost = (response.get('usage') or {}).get('cost')
            if cost is None:
                raise RuntimeError('Missing cost. Reservation remains.')
            amount = Decimal(str(cost))
            if not amount.is_finite() or amount < 0 or amount > RESERVE:
                raise RuntimeError('Cost violates reservation. Stop.')
            self.connection.execute('UPDATE calls SET state=?, amount=? WHERE id=?', ('reconciled', str(amount), call_id))
            self.connection.commit()

    def error(self, call_id, name):
        with self.lock:
            self.connection.execute('UPDATE calls SET error=? WHERE id=?', (name, call_id))
            self.connection.commit()

    def unresolved(self):
        return self.connection.execute("SELECT id,state FROM calls WHERE state!='reconciled'").fetchall()

def collect(workers=4):
    manifest = json.loads((ROOT/'plans/full-manifest.json').read_text())
    for name, expected in manifest['source_hashes'].items():
        if hashlib.sha256((ROOT/'benchmark'/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Runner source changed after freeze.')
    if not (ROOT/'reviews/round10.txt').exists():
        raise RuntimeError('Round ten has not finished. Full collection blocked.')
    private = ROOT/'private'
    private.mkdir(exist_ok=True)
    lockpath = private/'runner.lock'
    fd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    store = None
    try:
        key = load_key()
        prior = spent(private/'cost-ledger.jsonl')
        store = Store(private/'full.sqlite', prior, digest(manifest))
        if store.unresolved():
            raise RuntimeError('Unresolved saved requests block continuation.')
        stop = threading.Event()
        jobs = []
        for entry in manifest['roster']:
            group = []
            for case in manifest['cases']:
                for timing in manifest['timings']:
                    for repeat in range(manifest['repetitions']):
                        for branch in manifest['branches']:
                            group.append({'model': entry['model'], 'entry': entry, 'case': case, 'timing': timing, 'repeat': repeat, 'branch': branch})
            random.Random(manifest['seed']).shuffle(group)
            jobs.extend(group)
        def run(spec):
            if stop.is_set():
                return
            call_id = digest({'manifest': digest(manifest), 'spec': spec})
            try:
                payload = {'model': spec['model'], **spec['entry']['config'],
                           'messages': messages(spec['case'], spec['branch'], spec['timing'])}
                ceiling = Decimal(len(json.dumps(payload['messages']).encode()))*Decimal('0.00002')+Decimal(MAX_TOKENS)*Decimal('0.0001')
                if ceiling > RESERVE:
                    raise RuntimeError('Input exceeds cost reservation.')
                if not store.reserve(call_id, spec):
                    return
                started = time.monotonic()
                response = fetch('/chat/completions', key, payload)
                observation = score(response, spec['branch'])
                observation['duration_seconds'] = time.monotonic()-started
                observation['requested_model'] = spec['model']
                observation['returned_model'] = response.get('model')
                observation['returned_provider'] = response.get('provider')
                store.response(call_id, response, observation)
                print(f'{spec["model"]} {spec["case"]["id"]} {spec["timing"]} {spec["branch"]} {observation["status"]}', flush=True)
            except Exception as error:
                stop.set()
                store.error(call_id, type(error).__name__)
                print(f'STOP: {spec["model"]} / {type(error).__name__}. Review saved state.', flush=True)
        # Preserve proprietary-first ordering by completing each model before the next.
        for entry in manifest['roster']:
            if stop.is_set():
                break
            with ThreadPoolExecutor(max_workers=workers) as executor:
                list(executor.map(run, [job for job in jobs if job['model'] == entry['model']]))
        if stop.is_set():
            raise RuntimeError('Collection stopped with unresolved or budget state.')
    finally:
        if store is not None:
            store.connection.close()
        os.close(fd)
        lockpath.unlink()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['freeze', 'collect'])
    parser.add_argument('--workers', type=int, default=4, choices=range(1,5))
    args = parser.parse_args()
    freeze() if args.command == 'freeze' else collect(args.workers)
