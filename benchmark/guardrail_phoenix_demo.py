"""Exercise native Phoenix code evaluators on every offline scripted control."""
import argparse
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import socket
from unittest.mock import patch

from benchmark.guardrail_coverage import run_scripted, scenes
from benchmark.guardrail_phoenix import BoundReplayMetrics, create_phoenix_evaluators


ROOT = Path(__file__).resolve().parents[1]
SDK_VERSION = '3.9.0'
RUNTIME_PACKAGES = (
    'arize-phoenix-evals', 'openinference-instrumentation',
    'openinference-semantic-conventions', 'pydantic', 'pydantic-core',
    'typing-extensions', 'jsonpath-ng', 'opentelemetry-api', 'pandas',
    'pystache', 'tqdm', 'annotated-types', 'numpy', 'python-dateutil',
    'typing-inspection', 'wrapt', 'colorama', 'opentelemetry-sdk',
    'opentelemetry-semantic-conventions', 'six', 'tzdata',
)


def _resolved_packages():
    resolved = {}
    for name in RUNTIME_PACKAGES:
        try:
            resolved[name] = version(name)
        except PackageNotFoundError:
            # Platform-conditional dependencies, such as colorama and tzdata,
            # need not be present. Record absence rather than invent a version.
            resolved[name] = None
    return resolved


def _native_dict(score):
    return {field: getattr(score, field) for field in
            ('name', 'kind', 'direction', 'score', 'label', 'explanation', 'metadata')}


def _equivalent(actual, expected):
    # Native SDK numeric representations may be int or float. All categorical
    # fields, missingness and metadata keep JSON type distinctions.
    for key in expected:
        if key == 'score':
            if expected[key] is None:
                if actual[key] is not None:
                    return False
            elif type(actual[key]) not in (int, float) or actual[key] != expected[key]:
                return False
        elif json.dumps(actual[key], sort_keys=True, allow_nan=False) != json.dumps(
                expected[key], sort_keys=True, allow_nan=False):
            return False
    return set(actual) == set(expected)


def demonstrate():
    if version('arize-phoenix-evals') != SDK_VERSION:
        raise ValueError('Use the pinned optional SDK for this demonstration')
    rows, checks = [], Counter()
    with ExitStack() as stack:
        tripwires = [stack.enter_context(patch.object(owner, method,
                     side_effect=AssertionError('Offline demonstration forbids network connections')))
                     for owner, method in ((socket.socket, 'connect'),
                                           (socket.socket, 'connect_ex'),
                                           (socket, 'create_connection'))]
        for case in scenes():
            for coverage in ('motion_only', 'full_surface'):
                for policy in ('correct', 'faulty_direct'):
                    receipt = run_scripted(case, policy, coverage)
                    expected = BoundReplayMetrics(case, coverage, policy).evaluate(receipt)
                    evaluators = create_phoenix_evaluators(case, coverage, policy)
                    actual = []
                    for evaluator, reference in zip(evaluators, expected):
                        results = evaluator.evaluate({'record': receipt})
                        if len(results) != 1:
                            raise ValueError('Unexpected native metric result count')
                        score = _native_dict(results[0])
                        if not _equivalent(score, reference):
                            raise ValueError('Native score changed outcome, type or missingness')
                        actual.append(score)
                        checks['native_metric_calls'] += 1
                        if score['score'] is None:
                            checks['unavailable_completion_scores'] += 1
                    if actual[0]['score'] != 1:
                        raise ValueError('Scripted control failed independent replay')
                    checks['verified_traces'] += 1
                    checks['executed_contact_traces'] += int(actual[1]['score'])
                    checks['feasible_safe_completions'] += int(actual[2]['score'] or 0)
                    rows.append({'control_record_index': len(rows),
                                 'receipt_sha256': hashlib.sha256(json.dumps(receipt,
                                  sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(),
                                 'scores': actual})
        attempts = sum(tripwire.call_count for tripwire in tripwires)
        if attempts:
            raise ValueError('A network connection was attempted')
    return {
        'status': 'offline native SDK demonstration; not a model experiment or customer delivery',
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'sdk': {'package': 'arize-phoenix-evals', 'version': SDK_VERSION,
                'vendor_license': 'Elastic-2.0',
                'source': 'https://pypi.org/project/arize-phoenix-evals/3.9.0/'},
        'python': platform.python_version(),
        'platform': {'system': platform.system(), 'machine': platform.machine()},
        'resolved_packages': _resolved_packages(),
        'network_connection_attempts': attempts,
        'model_queries': 0,
        'source_sha256': {path: hashlib.sha256((ROOT / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                          for path in ('benchmark/guardrail_phoenix.py',
                                       'benchmark/guardrail_phoenix_demo.py',
                                       'benchmark/guardrail_coverage.py',
                                       'benchmark/guardrail_coverage_verifier.py')},
        'control_source': 'reviews/guardrail-coverage-controls.json',
        'control_order': 'scenes(); coverage motion_only/full_surface; policy correct/faulty_direct',
        'checks': dict(checks),
        'limitations': [
            'Known scripted development controls; no new model finding or novelty claim.',
            'Scenes share bases and include four duplicate impossible observations.',
            'Connection tripwires cover the demonstrated Python evaluation path, not every SDK feature.',
            'Expected cases must come from an independently trusted source; this bridge cannot authenticate it.',
            'Receipt replay is not provider execution authentication or independent human review.',
            'No hosted Phoenix instance, dashboard ingestion, customer workflow or partner status was tested.',
            'Optional vendor SDK retains its own license; no new public licensing grant is applied.',
        ],
        'records': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'reviews/guardrail-phoenix-evals.json')
    args = parser.parse_args()
    report = demonstrate()
    target = args.output
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(target), 'checks': report['checks'],
                      'network_connection_attempts': report['network_connection_attempts'],
                      'model_queries': report['model_queries']}))
