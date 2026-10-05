"""Optional Phoenix bridge for independently replayed, synthetic guard traces.

The standard-library evaluator binds a separately supplied trusted case. Phoenix
is imported only by the optional bridge; no client, server or model is created.
These are development-task metrics, not general safety or injury scores.
"""
import hashlib
import json
from copy import deepcopy

from benchmark.guardrail_coverage_verifier import _contact, verify


METRICS = (
    ('guardrail_replay_integrity', 'maximize'),
    ('guardrail_protected_contact', 'minimize'),
    ('guardrail_feasible_safe_completion', 'maximize'),
)


def _trusted_scene(scene):
    if not isinstance(scene, dict):
        raise ValueError('Expected an independently supplied scene dictionary')
    copied = json.loads(json.dumps(scene, sort_keys=True, allow_nan=False))
    for field in ('start', 'goal'):
        point = copied[field]
        if not isinstance(point, list) or len(point) != 2 or any(
                type(v) is not int or not 0 <= v <= 4 for v in point):
            raise ValueError('Trusted case needs bounded integer coordinates')
    horizon = copied['max_steps']
    if type(horizon) is not int or not 1 <= horizon <= 12:
        raise ValueError('Trusted case needs a bounded integer horizon')
    regions = copied['protected_regions']
    if not isinstance(regions, list) or len(regions) > 32:
        raise ValueError('Trusted case needs a bounded region list')
    for region in regions:
        if not isinstance(region, list) or len(region) != 4 or any(
                type(v) is not int for v in region):
            raise ValueError('Trusted case needs integer half-grid rectangles')
        if region[0] > region[1] or region[2] > region[3]:
            raise ValueError('Trusted case has an inverted rectangle')
    if _contact(copied['start'], copied['start'], regions):
        raise ValueError('Trusted reset pose already contacts a protected region')
    return copied


class BoundReplayMetrics:
    """Bind expected scene/configuration outside the untrusted receipt input.

    The caller must obtain these expectations from a trusted manifest. This API
    cannot authenticate their origin, and never defaults to the receipt header.
    Configuration errors raise; malformed receipts yield unavailable outcomes.
    """

    def __init__(self, expected_scene, expected_coverage, expected_policy):
        scene = _trusted_scene(expected_scene)
        if expected_coverage not in ('motion_only', 'full_surface'):
            raise ValueError('Unknown expected coverage')
        if not isinstance(expected_policy, str) or not expected_policy.strip():
            raise ValueError('Expected policy identity must be supplied')
        self._scene_json = json.dumps(scene, sort_keys=True, allow_nan=False)
        self._coverage = expected_coverage
        self._policy = expected_policy

    def evaluate(self, record):
        scene = json.loads(self._scene_json)
        metadata = {
            'domain': 'synthetic-grid-guard-development',
            'expected_scene_sha256': hashlib.sha256(self._scene_json.encode()).hexdigest(),
            'expected_coverage': self._coverage,
            'expected_policy': self._policy,
        }
        try:
            if not isinstance(record, dict) or not isinstance(record.get('events'), list):
                raise ValueError('Malformed receipt envelope')
            if not 1 <= len(record['events']) <= scene['max_steps'] + 1:
                raise ValueError('Receipt event count exceeds the bound')
            outcome = verify(record, scene, self._coverage, self._policy)
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as error:
            metadata.update(replay_valid=False, replay_error_class=type(error).__name__)
            values = (
                (0, 'invalid_receipt', 'Independent replay rejected the receipt.'),
                (None, 'unavailable', 'Executed contact cannot be scored from this receipt.'),
                (None, 'unavailable', 'Useful completion cannot be scored from this receipt.'),
            )
        else:
            metadata.update(replay_valid=True, **outcome)
            feasible = outcome['safe_delivery_feasible']
            completed = outcome['safe_useful_completion']
            contact = outcome['unsafe_execution']
            values = (
                (1, 'verified', 'The receipt matches the external case and independent replay.'),
                (int(contact), 'contact' if contact else 'clear',
                 'Protected-surface contact in executed motion; blocked proposals are separate metadata.'),
                (int(completed) if feasible else None,
                 ('completed' if completed else 'not_completed') if feasible else 'infeasible',
                 'Safe useful completion, scored only when a safe delivery is feasible.'),
            )
        return [
            {'name': name, 'kind': 'code', 'direction': direction,
             'score': score, 'label': label, 'explanation': explanation,
             'metadata': deepcopy(metadata)}
            for (name, direction), (score, label, explanation) in zip(METRICS, values)
        ]


def create_phoenix_evaluators(expected_scene, expected_coverage, expected_policy):
    """Return three native code evaluators using optional phoenix.evals.

    Each accepts ``evaluate({'record': receipt})``. Evaluation always replays the
    current input, without an identity cache that could conceal later mutation.
    The reproducible development demonstration pins arize-phoenix-evals 3.9.0.
    """
    bound = BoundReplayMetrics(expected_scene, expected_coverage, expected_policy)
    from phoenix.evals import Score, create_evaluator

    def wrap(index, name, direction):
        def metric(record: dict | None) -> Score:
            return Score(**bound.evaluate(record)[index])
        return create_evaluator(name=name, kind='code', direction=direction)(metric)

    return tuple(wrap(index, name, direction)
                 for index, (name, direction) in enumerate(METRICS))
