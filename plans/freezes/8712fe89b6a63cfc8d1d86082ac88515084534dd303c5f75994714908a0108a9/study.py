"""Freeze and collect the reviewed study without executing model actions."""
from contextlib import closing
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
import platform
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from pilot import API, MODELS, ROOT, load_key, spent
from study_cases import TOOL, cases, messages, score

ROUTES = ['openai', 'azure/global', 'google-ai-studio', 'xai', 'phala', 'novita', 'morph/fp8', 'phala']
MAX_TOKENS = 2048
RESERVE = Decimal('0.50')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def source_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()

def fetch(path, key=None, payload=None):
    headers = {'Content-Type': 'application/json', 'HTTP-Referer': 'https://murderbench.com', 'X-Title': 'MurderBench reviewed study'}
    if key:
        headers['Authorization'] = 'Bearer '+key
    data = json.dumps(payload).encode() if payload is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(API+path, data=data, headers=headers), timeout=120) as response:
            raw = response.read()
            try:
                return json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                if payload is None:
                    raise
                return {'response_parse_error': True, 'raw_response': raw.decode(errors='replace')}
    except urllib.error.HTTPError as error:
        if payload is None:
            raise
        return {'http_status': error.code, 'error_body': error.read().decode(errors='replace')}

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
                  'tools': [TOOL], 'tool_choice': 'auto',
                  'provider': {'only': [route], 'allow_fallbacks': False, 'require_parameters': True,
                               'data_collection': 'deny', 'max_price': {'prompt': 20, 'completion': 100}}, 'usage': {'include': True}}
        if 'reasoning' not in entry['supported_parameters']:
            raise RuntimeError(f'Pinned route lacks the frozen reasoning setting: {model}')
        if 'temperature' in entry['supported_parameters']:
            config['temperature'] = 0
        roster.append({'model': model, 'canonical_slug': models[model]['canonical_slug'],
                       'provider_tag': route, 'provider_name': entry['provider_name'],
                       'quantization': entry.get('quantization'), 'config': config,
                       'native_sampling_default': 'temperature' not in config})
    source_hashes = {name: source_digest(ROOT/'benchmark'/name)
                     for name in ['study.py', 'study_cases.py', 'pilot.py', 'scenarios.py', 'analyze.py']}
    manifest = {'version': 'decision-boundary-v1', 'timestamp': datetime.now(timezone.utc).isoformat(),
                'roster': roster, 'cases': cases(), 'timings': ['early', 'late'], 'branches': ['stable', 'changed'],
                'repetitions': 3, 'calls_per_model': 288, 'total_calls': 2304,
                'max_total_budget_usd': 50, 'seed': 20261002, 'source_hashes': source_hashes,
                'source_hash_policy': 'SHA256 of bytes with CRLF normalized to LF for portable checkout verification',
                'environment': {'python': sys.version, 'platform': platform.platform(),
                                'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                                'working_tree': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines()},
                'catalog_sha256': digest(catalog), 'endpoints_sha256': digest(snapshots),
                'claim_scope': 'fixed synthetic histories; descriptive constraint-update behavior; no injury probabilities or general safety rankings'}
    path = ROOT/'plans/full-manifest.json'
    path.write_text(json.dumps(manifest, indent=2))
    (ROOT/'plans/full-catalog.json').write_text(json.dumps({'models': catalog, 'endpoints': snapshots}, indent=2))
    archive = ROOT/'plans/freezes'/digest(manifest)
    archive.mkdir(parents=True, exist_ok=False)
    (archive/'manifest.json').write_text(json.dumps(manifest, indent=2))
    for name in source_hashes:
        (archive/name).write_bytes((ROOT/'benchmark'/name).read_bytes())
    (archive/'catalog.json').write_text(json.dumps({'models': catalog, 'endpoints': snapshots}, indent=2))
    print(f'Frozen manifest {digest(manifest)}. 2,304 candidate calls after round ten.')

def validated_manifest():
    manifest = json.loads((ROOT/'plans/full-manifest.json').read_text())
    for name, expected in manifest['source_hashes'].items():
        if source_digest(ROOT/'benchmark'/name) != expected:
            raise RuntimeError('Runner source changed after freeze.')
    snapshots = json.loads((ROOT/'plans/full-catalog.json').read_text())
    if digest(snapshots['models']) != manifest['catalog_sha256'] or digest(snapshots['endpoints']) != manifest['endpoints_sha256']:
        raise RuntimeError('Frozen catalog differs.')
    return manifest

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
            usage = response.get('usage') if isinstance(response, dict) else None
            cost = usage.get('cost') if isinstance(usage, dict) else None
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

    def received(self, call_id, response):
        with self.lock:
            spec = json.loads(self.connection.execute('SELECT spec FROM calls WHERE id=?',(call_id,)).fetchone()[0])
            spec['response_received_utc'] = datetime.now(timezone.utc).isoformat()
            self.connection.execute('UPDATE calls SET state=?, response=?, spec=? WHERE id=?',
                                    ('received', json.dumps(response), json.dumps(spec), call_id))
            self.connection.commit()

    def unresolved(self):
        return self.connection.execute("SELECT id,state FROM calls WHERE state!='reconciled'").fetchall()

def native_spent(private, exclude=None):
    total = Decimal('0')
    for path in private.glob('native*.sqlite'):
        if path == exclude:
            continue
        with closing(sqlite3.connect(path)) as connection:
            total += sum((Decimal(row[0]) for row in connection.execute('SELECT amount FROM calls')), Decimal('0'))
    return total

def reservation_bound(payload):
    return Decimal(len(json.dumps(payload).encode())+4096)*Decimal('0.00002')+Decimal(MAX_TOKENS)*Decimal('0.0001')

def admit(store, stop, admission_lock, call_id, spec):
    with admission_lock:
        if stop.is_set():
            return False
        return store.reserve(call_id, spec)

def prepare_eligibility():
    manifest = validated_manifest()
    entries = []
    for entry in manifest['roster']:
        payload = {'model': entry['model'], **entry['config'], 'messages': messages(manifest['cases'][0], 'changed', 'early')}
        matches = []
        for path in (ROOT/'private').glob('native*.sqlite'):
            with closing(sqlite3.connect(path)) as connection:
                for call_id,spec,state,observation in connection.execute('SELECT id,spec,state,observation FROM calls'):
                    if json.loads(spec).get('request_payload') == payload and state == 'reconciled' and observation:
                        matches.append({'call_id': call_id, 'status': json.loads(observation)['status']})
        entries.append({'model': entry['model'], 'configuration_sha256': digest(payload),
                        'disposition': 'eligible' if any(row['status']=='valid' for row in matches) else 'unverified',
                        'evidence': matches, 'rule': 'One valid native-interface proposal under identical payload; restraint outcome is not an eligibility criterion.'})
    register = {'manifest_sha256': digest(manifest), 'entries': entries,
                'unresolved_policy': 'Older isolated failures remain charged holds and are never replayed. Only exact payloads with reconciled native-interface evidence are eligible. New final unresolved calls block continuation.'}
    (ROOT/'plans/eligibility.json').write_text(json.dumps(register, indent=2))
    archive = ROOT/'plans/freezes'/digest(manifest)
    if archive.exists():
        (archive/'eligibility.json').write_text(json.dumps(register, indent=2))
    print('Prepared prospective interface eligibility, without behavioral outcome selection.')

def validate_eligibility(manifest, register):
    entries = register.get('entries', [])
    if register.get('manifest_sha256') != digest(manifest) or len(entries) != len(manifest['roster']):
        raise RuntimeError('Candidate interface eligibility is not frozen and complete.')
    for entry in manifest['roster']:
        rows = [row for row in entries if row.get('model')==entry['model']]
        payload = {'model': entry['model'], **entry['config'], 'messages': messages(manifest['cases'][0], 'changed', 'early')}
        if len(rows)!=1 or rows[0].get('disposition')!='eligible' or rows[0].get('configuration_sha256')!=digest(payload) or not any(e.get('status')=='valid' and isinstance(e.get('call_id'), str) and len(e['call_id'])==64 for e in rows[0].get('evidence', [])):
            raise RuntimeError('Exact-payload eligibility evidence differs or is missing.')

def smoke():
    """One changed-state interface check per pinned route; no behavioral comparison."""
    manifest = validated_manifest()
    private = ROOT/'private'
    private.mkdir(exist_ok=True)
    lockpath = private/'runner.lock'
    fd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    store = None
    try:
        if (private/'full.sqlite').exists():
            raise RuntimeError('Final state exists. Isolated collection disabled.')
        path = private/('native-'+digest(manifest)[:12]+'.sqlite')
        store = Store(path, spent(private/'cost-ledger.jsonl')+native_spent(private, path), digest(manifest))
        if store.unresolved():
            raise RuntimeError('Unresolved isolated requests block replay.')
        key = load_key()
        for entry in manifest['roster']:
            payload = {'model': entry['model'], **entry['config'], 'messages': messages(manifest['cases'][0], 'changed', 'early')}
            bound = reservation_bound(payload)
            if bound > RESERVE:
                raise RuntimeError('Input exceeds reservation.')
            spec = {'purpose': 'native interface feasibility only', 'request_payload': payload,
                    'started_utc': datetime.now(timezone.utc).isoformat(), 'reservation_bound_usd': str(bound)}
            call_id = digest({'manifest': digest(manifest), 'model': entry['model'], 'purpose': 'native-smoke'})
            if not store.reserve(call_id, spec):
                continue
            try:
                response = fetch('/chat/completions', key, payload)
                store.received(call_id, response)
                observation = score(response, 'changed')
                observation['ended_utc'] = datetime.now(timezone.utc).isoformat()
                store.response(call_id, response, observation)
                print(entry['model'], observation['status'], flush=True)
            except Exception as error:
                store.error(call_id, type(error).__name__)
                print(entry['model'], 'unavailable/unreconciled', type(error).__name__, flush=True)
                # No replay. Other independent routes may be checked with all holds charged.
    finally:
        if store:
            store.connection.close()
        os.close(fd)
        lockpath.unlink()

def collect(workers=4):
    manifest = validated_manifest()
    for round_number in range(1, 11):
        report = ROOT/f'reviews/round{round_number}.txt'
        if not report.exists() or len(report.read_text()) < 100:
            raise RuntimeError('All ten critique rounds must finish. Full collection blocked.')
    register = json.loads((ROOT/'plans/eligibility.json').read_text())
    validate_eligibility(manifest, register)
    private = ROOT/'private'
    private.mkdir(exist_ok=True)
    lockpath = private/'runner.lock'
    fd = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    store = None
    try:
        key = load_key()
        prior = spent(private/'cost-ledger.jsonl') + native_spent(private)
        store = Store(private/'full.sqlite', prior, digest(manifest))
        if store.unresolved():
            raise RuntimeError('Unresolved saved requests block continuation.')
        stop = threading.Event()
        admission_lock = threading.Lock()
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
                # Full serialized payload plus 4,096 tokens of conservative tool/framing overhead.
                ceiling = reservation_bound(payload)
                if ceiling > RESERVE:
                    raise RuntimeError('Input exceeds cost reservation.')
                spec = {**spec, 'request_payload': payload, 'reservation_bound_usd': str(ceiling),
                        'started_utc': datetime.now(timezone.utc).isoformat()}
                if not admit(store, stop, admission_lock, call_id, spec):
                    return
                started = time.monotonic()
                response = fetch('/chat/completions', key, payload)
                store.received(call_id, response)
                observation = score(response, spec['branch'])
                observation['ended_utc'] = datetime.now(timezone.utc).isoformat()
                observation['duration_seconds'] = time.monotonic()-started
                observation['requested_model'] = spec['model']
                observation['returned_model'] = response.get('model') if isinstance(response, dict) else None
                observation['returned_provider'] = response.get('provider') if isinstance(response, dict) else None
                store.response(call_id, response, observation)
                print(f'{spec["model"]} {spec["case"]["id"]} {spec["timing"]} {spec["branch"]} {observation["status"]}', flush=True)
            except Exception as error:
                with admission_lock:
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
    parser.add_argument('command', choices=['freeze', 'collect', 'smoke', 'prepare'])
    parser.add_argument('--workers', type=int, default=4, choices=range(1,5))
    args = parser.parse_args()
    {'freeze': freeze, 'collect': lambda: collect(args.workers), 'smoke': smoke, 'prepare': prepare_eligibility}[args.command]()
