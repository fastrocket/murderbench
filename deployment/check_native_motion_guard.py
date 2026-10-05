"""Offline primitive check, not a model evaluation or a robot safety finding.

Usage: python deployment/check_native_motion_guard.py <inspect-robots checkout>
Requires numpy. The upstream checkout must be clean at the pinned commit.
No policy, embodiment, actuator or model endpoint is invoked.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = 'd08442a9d1f43af4658c8d71e02d461e780286e1'


def main():
    checkout = Path(sys.argv[1]).resolve()
    revision = subprocess.check_output(
        ['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(
        ['git', '-C', str(checkout), 'status', '--porcelain'], text=True).strip()
    if revision != PIN or dirty:
        raise ValueError('Require the clean pinned upstream checkout')
    sys.path.insert(0, str(checkout / 'src'))
    import numpy as np
    from inspect_robots.approver import ChainApprover, ClampApprover, DeltaLimitApprover
    from inspect_robots.errors import SafetyAbort
    from inspect_robots.spaces import ActionSemantics, Box
    from inspect_robots.types import Action

    space = Box((3,), low=np.full(3, -0.5), high=np.full(3, 0.5),
                semantics=ActionSemantics('eef_delta_pos', frame='world'))
    guard = ChainApprover(ClampApprover(space), DeltaLimitApprover(space, max_delta=0.2))
    action = Action(np.array([0.1, 0.0, 0.0]))
    assert guard.review(action, {}) is action
    modified = guard.review(Action(np.array([9.0, 0.0, 0.0])), {})
    np.testing.assert_allclose(modified.data, [0.2, 0.0, 0.0])
    assert modified.meta['clamped'] and modified.meta['delta_clamped']
    try:
        guard.review(Action(np.array([float('nan'), 0.0, 0.0])), {})
    except SafetyAbort:
        rejected_nan = True
    else:
        raise AssertionError('Non-finite action was accepted')

    # An original synthetic rule, deliberately outside these motion checks:
    # do not enter x > 0.3. Units are arbitrary; this is not a physical model.
    position = np.zeros(3)
    events = []
    store = {}
    for step in range(2):
        proposed = Action(np.array([0.2, 0.0, 0.0]))
        approved = guard.review(proposed, store)
        position = position + approved.data
        events.append({'step': step, 'proposed': proposed.data.tolist(),
                       'approved': approved.data.tolist(),
                       'modified': approved is not proposed,
                       'synthetic_position': position.tolist()})
    assert all(not event['modified'] for event in events)
    assert position[0] > 0.3

    files = ['approver.py', 'spaces.py', 'types.py', 'errors.py']
    print(json.dumps({
        'purpose': 'Native primitive calibration; not an agent/model result',
        'upstream': 'https://github.com/robocurve/inspect-robots',
        'commit': revision, 'numpy_version': np.__version__,
        'sha256': {name: hashlib.sha256((checkout / 'src/inspect_robots' / name).read_bytes()).hexdigest()
                   for name in files},
        'checks': {'within_bounds_identity': True, 'bounds_and_delta_clamp': True,
                   'reject_nan': rejected_nan, 'synthetic_semantic_rule_not_enforced': True},
        'events': events,
        'limitations': ['Only the explicitly configured core guard chain was exercised.',
                        'Embodiment-specific guardrails can enforce additional rules.',
                        'Per-step displacement does not establish a dynamic speed guarantee.',
                        'The synthetic semantic gap is expected and is not novel.',
                        'No LLM, physical robot, injury model or independent replay was tested.']
    }, indent=2))


if __name__ == '__main__':
    main()
