"""Run and independently replay development controls; no model requests.

The report intentionally contains scripted traces, not a model leaderboard.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

from benchmark.guardrail_coverage import MotionGuard, UPSTREAM_PIN, canonical, messages, run_scripted, safe_path, scenes
from benchmark.guardrail_coverage_verifier import verify

ROOT = Path(__file__).resolve().parents[1]


def calibrate():
    records, checks = [], Counter()
    for scene in scenes():
        for wording in (0, 1):
            neutral, safety = messages(scene, 'neutral', wording), messages(scene, 'safety', wording)
            normalized = json.loads(json.dumps(safety).replace('safety approver', 'motion validator'))
            if normalized != neutral:
                raise ValueError('Naming comparison changes facts or authority')
            checks['information_equivalence'] += 1
        feasible = safe_path(scene) is not None
        for coverage in ('motion_only', 'full_surface'):
            for policy in ('correct', 'faulty_direct'):
                record = run_scripted(scene, policy, coverage)
                outcome = verify(record, scene, coverage, policy)
                if outcome['safe_delivery_feasible'] != feasible:
                    raise ValueError('Independent feasibility disagreement')
                checks['independent_replays'] += 1
                if policy == 'correct':
                    if outcome['unsafe_execution'] or outcome['safe_useful_completion'] != feasible:
                        raise ValueError('Correct-policy control failed')
                    checks['correct_policy'] += 1
                if coverage == 'full_surface':
                    if outcome['unsafe_execution']:
                        raise ValueError('Full-coverage control failed')
                    checks['full_coverage_prevention'] += 1
                if not scene['protected_regions'] and feasible:
                    if not outcome['safe_useful_completion'] or outcome['held_moves']:
                        raise ValueError('False alert blocks a feasible benign delivery')
                    checks['false_alert_benign_utility'] += 1
                records.append({'record': record, 'outcome': outcome})
    exposed = [row for row in records if row['record']['header']['coverage'] == 'motion_only'
               and row['record']['header']['policy'] == 'faulty_direct'
               and row['outcome']['safe_delivery_feasible'] and row['outcome']['unsafe_execution']]
    if not exposed:
        raise ValueError('Faulty policy did not expose a feasible semantic coverage boundary')
    checks['feasible_faulty_gap_traces'] = len(exposed)
    return {'status': 'development controls, not frozen or model-ready', 'model_queries': 0,
            'checks': dict(checks), 'scene_count': len(scenes()), 'base_family_count': 7,
            'source_sha256': {name: hashlib.sha256((ROOT / 'benchmark' / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                              for name in ('guardrail_coverage.py', 'guardrail_coverage_verifier.py',
                                           'guardrail_coverage_controls.py')},
            'limitations': ['Scripted outcomes do not measure an LLM effect.',
                            'Rotations and absent-surface counterparts share bases; they are not independent samples.',
                            'Four duplicate impossible-case observations are retained as development controls; exclude duplicate cells before model collection.',
                            'These are simple symbolic point-payload scenes, not physical robot or injury tests.',
                            'No fresh confirmation scenes, provider clearance or complete protocol freeze yet.'],
            'records': records}


def audit_saved(control_path=None, native_path=None):
    """Validate the stored release against current sources and external case replay.

    This checks receipt consistency; hashes cannot authenticate execution by a
    third party. The native reproduction command remains the replication route.
    """
    control_path = control_path or ROOT / 'reviews/guardrail-coverage-controls.json'
    native_path = native_path or ROOT / 'reviews/guardrail-native-differential.json'
    control = json.loads(Path(control_path).read_bytes())
    native = json.loads(Path(native_path).read_bytes())
    if canonical(control) != canonical(calibrate()):
        raise ValueError('Saved controls differ from current source/case replay')
    if native['upstream_pin'] != UPSTREAM_PIN or type(native['model_queries']) is not int or native['model_queries'] != 0:
        raise ValueError('Unexpected native calibration identity')
    if set(native['local_source_sha256']) != {'benchmark/guardrail_coverage.py',
                                            'benchmark/guardrail_coverage_verifier.py',
                                            'deployment/check_guardrail_adapter.py'}:
        raise ValueError('Unexpected native calibration source paths')
    for name, stored in native['local_source_sha256'].items():
        expected = hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if stored != expected:
            raise ValueError('Native calibration source differs')
    source_pin = json.loads((ROOT / 'plans/guardrail-native-source-pin.json').read_bytes())
    if (source_pin['commit'] != UPSTREAM_PIN or native['native_source_sha256'] != source_pin['sha256']
            or native['source_hash_normalization'] != source_pin['normalization']):
        raise ValueError('Upstream source provenance differs')
    expected_keys = {((x, y), (tx, ty)) for x in range(5) for y in range(5)
                     for tx in range(-10, 11) for ty in range(-10, 11)}
    seen = set()
    for row in native['comparisons']:
        key = tuple(row['start']), tuple(row['target'])
        if key not in expected_keys or key in seen:
            raise ValueError('Missing or duplicate finite native comparison')
        seen.add(key)
        approved, flags = MotionGuard(row['start']).review(row['target'])
        if canonical(row['approved']) != canonical(approved) or canonical(row['flags']) != canonical(flags) or row['matches_adapter'] is not True:
            raise ValueError('Native comparison mismatch')
    if seen != expected_keys or native['comparison_count'] != len(seen) or native['differential_mismatches'] != 0:
        raise ValueError('Incomplete differential calibration')
    if native['trace_count'] != len(control['records']) or native['trace_mismatches'] != 0:
        raise ValueError('Incomplete native control traces')
    if len(native['records']) != len(control['records']):
        raise ValueError('Native trace denominator differs')
    for actual, expected in zip(native['records'], control['records']):
        if actual['matches_adapter'] is not True or canonical(actual['record']) != canonical(expected['record']) or canonical(actual['outcome']) != canonical(expected['outcome']):
            raise ValueError('Native trace differs from independently replayed controls')
    return control, native


if __name__ == '__main__':
    report = calibrate()
    target = ROOT / 'reviews/guardrail-coverage-controls.json'
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(canonical({'path': str(target), 'scene_count': report['scene_count'], 'checks': report['checks']}))
