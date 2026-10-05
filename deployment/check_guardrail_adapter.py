"""Exhaustive finite-subset and control-trace differential check against native code.

Usage: python deployment/check_guardrail_adapter.py <clean inspect-robots checkout>
Requires numpy; no hardware, policy or model is invoked.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.guardrail_coverage import MotionGuard, UPSTREAM_PIN, run_scripted, scenes
from benchmark.guardrail_coverage_verifier import verify


def main():
    checkout = Path(sys.argv[1]).resolve()
    pin = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain'], text=True).strip()
    if pin != UPSTREAM_PIN or dirty:
        raise ValueError('Require clean pinned upstream source')
    sys.path.insert(0, str(checkout / 'src'))
    import numpy as np
    from inspect_robots.approver import ChainApprover, ClampApprover, DeltaLimitApprover
    from inspect_robots.spaces import ActionSemantics, Box
    from inspect_robots.types import Action

    class NativeGuard:
        def __init__(self, start):
            box = Box((3,), low=np.array([0., 0., 0.]), high=np.array([4., 4., 0.]),
                      semantics=ActionSemantics('eef_abs_pose', rotation_repr='none'))
            self.chain = ChainApprover(ClampApprover(box), DeltaLimitApprover(box, max_delta=1.))
            self.store = {}
            # Explicit wrapper initialization, not an upstream default guarantee.
            self.chain.review(Action(np.array([*start, 0.], dtype=float)), self.store)

        def review(self, target):
            reviewed = self.chain.review(Action(np.array([*target, 0.], dtype=float)), self.store)
            if not all(float(v).is_integer() for v in reviewed.data):
                raise ValueError('Native output outside supported integer subset')
            return [int(v) for v in reviewed.data[:2]], {
                'clamped': bool(reviewed.meta.get('clamped', False)),
                'delta_clamped': bool(reviewed.meta.get('delta_clamped', False))}

        def rewind(self, position):
            DeltaLimitApprover.rewind_reference(self.store, np.array([*position, 0.], dtype=float))

    comparisons = []
    for x in range(5):
        for y in range(5):
            for tx in range(-10, 11):
                for ty in range(-10, 11):
                    start, target = [x, y], [tx, ty]
                    expected, flags = MotionGuard(start).review(target)
                    actual, native_flags = NativeGuard(start).review(target)
                    match = actual == expected and native_flags == flags
                    comparisons.append({'start': start, 'target': target, 'approved': actual,
                                        'flags': native_flags, 'matches_adapter': match})
    records = []
    for scene in scenes():
        for coverage in ('motion_only', 'full_surface'):
            for policy in ('correct', 'faulty_direct'):
                native = run_scripted(scene, policy, coverage, guard_factory=NativeGuard)
                adapter = run_scripted(scene, policy, coverage)
                outcome = verify(native, scene, coverage, policy)
                records.append({'record': native, 'outcome': outcome, 'matches_adapter': native == adapter})
    report = {'status': 'native differential development calibration; not a model result',
              'upstream_pin': pin, 'numpy_version': np.__version__, 'model_queries': 0,
              'source_hash_normalization': 'CRLF-to-LF before SHA256',
              'subset': 'absolute integer targets in [-10,10]^2; reset/reference in [0,4]^2; pinned z=0; max_delta=1',
              'native_source_sha256': {name: hashlib.sha256((checkout / 'src/inspect_robots' / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                      for name in ('approver.py', 'spaces.py', 'types.py', 'errors.py')},
              'local_source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                     for name in ('benchmark/guardrail_coverage.py',
                                                  'benchmark/guardrail_coverage_verifier.py',
                                                  'deployment/check_guardrail_adapter.py')},
              'comparison_count': len(comparisons),
              'differential_mismatches': sum(not c['matches_adapter'] for c in comparisons),
              'trace_count': len(records), 'trace_mismatches': sum(not r['matches_adapter'] for r in records),
              'comparisons': comparisons, 'records': records,
              'limitations': ['The reset no-op and downstream reference rewind are explicit wrapper behavior.',
                              'The adapter is not a reproduction of arbitrary poses, rotations or all embodiments.',
                              'Semantic geometry and payload dynamics remain an original inert simulator.',
                              'Native motion agreement does not establish an LLM effect or research novelty.']}
    destination = ROOT / 'reviews/guardrail-native-differential.json'
    destination.write_text(json.dumps(report, separators=(',', ':')) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('comparison_count', 'differential_mismatches', 'trace_count', 'trace_mismatches')}))
    if report['differential_mismatches'] or report['trace_mismatches']:
        raise ValueError('Differential calibration failed; every attempted outcome was preserved')


if __name__ == '__main__':
    main()
