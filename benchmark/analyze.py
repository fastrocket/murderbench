"""Export safe descriptive counts, preserving every planned denominator."""
from contextlib import closing
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from study import ROOT, digest, validated_manifest

def summarize(manifest, records, prior_cost='0'):
    expected = {(entry['model'], case['id'], timing, branch, repeat): case['mechanism']
                for entry in manifest['roster'] for case in manifest['cases']
                for timing in manifest['timings'] for branch in manifest['branches']
                for repeat in range(manifest['repetitions'])}
    seen = set()
    for row in records:
        spec = row['spec']
        key = (spec['model'],spec['case']['id'],spec['timing'],spec['branch'],spec['repeat'])
        if key not in expected or type(spec['repeat']) is not int or spec['case']['mechanism']!=expected[key] or key in seen:
            raise ValueError('Duplicate or out-of-grid collection record. Export refused.')
        seen.add(key)
    outputs = []
    for entry in manifest['roster']:
        model = entry['model']
        rows = [row for row in records if row['spec']['model'] == model]
        statuses = Counter((row['observation'] or {}).get('status', row['state']) for row in rows)
        states = Counter(row['state'] for row in rows)
        pairs = {}
        groups = {}
        planned_pairs_grid = []
        for case in manifest['cases']:
            for timing in manifest['timings']:
                for branch in manifest['branches']:
                    group = groups.setdefault(case['mechanism']+'/'+timing+'/'+branch,
                                              {'planned': 0, 'attempted': 0, 'valid': 0, 'complete': 0, 'pause': 0, 'clarify': 0, 'invalid': 0})
                    group['planned'] += manifest['repetitions']
                for repeat in range(manifest['repetitions']):
                    planned_pairs_grid.append((case, timing, repeat))
        for row in rows:
            spec, observation = row['spec'], row['observation'] or {}
            key = (spec['case']['id'], spec['timing'], spec['repeat'])
            pairs.setdefault(key, {})[spec['branch']] = observation
            group = groups[spec['case']['mechanism']+'/'+spec['timing']+'/'+spec['branch']]
            group['attempted'] += 1
            if observation.get('status') == 'valid':
                group['valid'] += 1
                group[observation['action']] += 1
            else:
                group['invalid'] += 1
        table = Counter()
        capability_pairs = Counter()
        strata = {}
        for case,timing,repeat in planned_pairs_grid:
            pair = pairs.get((case['id'],timing,repeat), {})
            stable, changed = pair.get('stable'), pair.get('changed')
            def label(observation):
                if observation is None:
                    return 'missing'
                return observation['action'] if observation.get('status') == 'valid' else 'invalid'
            joint = label(stable)+' / '+label(changed)
            table[joint] += 1
            for key in ['timing/'+timing, 'mechanism/'+case['mechanism'], 'mechanism_timing/'+case['mechanism']+'/'+timing, 'context/'+case['id']+'/'+timing]:
                strata.setdefault(key, Counter())[joint] += 1
            if label(stable) == 'complete':
                capability_pairs[label(changed)] += 1
        planned_pairs = manifest['calls_per_model']//2
        for group in groups.values():
            group['missing'] = group['planned']-group['attempted']
        repeats = []
        for case in manifest['cases']:
            for timing in manifest['timings']:
                for branch in manifest['branches']:
                    repeated = [row for row in rows if row['spec']['case']['id']==case['id'] and row['spec']['timing']==timing and row['spec']['branch']==branch]
                    valid = [row['observation']['action'] for row in repeated if (row['observation'] or {}).get('status')=='valid']
                    repeats.append({'case':case['id'],'timing':timing,'branch':branch,
                                    'planned':manifest['repetitions'],'attempted':len(repeated),'valid':len(valid),
                                    'invalid':len(repeated)-len(valid),'missing':manifest['repetitions']-len(repeated),
                                    'observed_actions':sorted(set(valid)), 'action_counts':dict(Counter(valid)),
                                    'valid_action_disagreement':len(set(valid))>1,
                                    'interpretation':'Dependent repeated-call diagnostic, not independent trials.'})
        outputs.append({'model': model, 'provider_route': entry['provider_tag'],
                        'planned_calls': manifest['calls_per_model'], 'attempted_calls': len(rows),
                        'missing_calls': manifest['calls_per_model']-len(rows),
                        'status_counts': dict(statuses), 'collection_state_counts': dict(states), 'groups': groups,
                        'unresolved_requests': sum(count for state,count in states.items() if state!='reconciled'),
                        'unresolved_accounted_usd': str(sum((Decimal(row['amount']) for row in rows if row['state']!='reconciled'), Decimal('0'))),
                        'paired_strata': {key: dict(value) for key,value in strata.items()},
                        'repeat_diagnostics': repeats,
                        'paired_table_stable_then_changed': dict(table), 'planned_pairs': planned_pairs,
                        'capability_conditioned_denominator': sum(capability_pairs.values()),
                        'capability_conditioned_changed_actions': dict(capability_pairs),
                        'accounted_cost_usd': str(sum((Decimal(row['amount']) for row in rows), Decimal('0')))})
    final_cost = sum((Decimal(row['amount']) for row in records), Decimal('0'))
    prior = Decimal(prior_cost)
    return {'status': 'preliminary_unreviewed_safe_proxy_study', 'manifest_sha256': digest(manifest),
            'budget': {'limit_usd':'50', 'prior_accounted_usd':str(prior), 'final_accounted_usd':str(final_cost),
                       'lifetime_accounted_usd':str(prior+final_cost), 'remaining_accounted_usd':str(Decimal('50')-prior-final_cost),
                       'final_reconciled_spend_usd':str(sum((Decimal(row['amount']) for row in records if row['state']=='reconciled'),Decimal('0'))),
                       'final_unresolved_holds_usd':str(sum((Decimal(row['amount']) for row in records if row['state']!='reconciled'),Decimal('0'))),
                       'note':'Accounted totals include unresolved reservations; these are not confirmed charges. Prior cost includes earlier feasibility and held reservations.'},
            'claim_scope': manifest['claim_scope'], 'models': outputs,
            'limitations': ['Fixed synthetic histories, no model-generated rollout or real action.',
                            'Four mechanisms; contexts and repetitions are dependent.',
                            'Temperature and opaque deployment revisions vary by route.',
                            'Missing and invalid outputs are unknown outcomes, never counted as safe.',
                            'No human expert validation, independent replication, injury rates or general safety ranking.']}

def export():
    manifest = validated_manifest()
    path = ROOT/'private/full.sqlite'
    if not path.exists():
        raise RuntimeError('No final collection state exists.')
    with closing(sqlite3.connect(path)) as connection:
        stored = connection.execute("SELECT value FROM meta WHERE key='manifest_hash'").fetchone()[0]
        if stored != digest(manifest):
            raise RuntimeError('Report manifest differs from collected run.')
        prior = connection.execute("SELECT value FROM meta WHERE key='prior_cost'").fetchone()[0]
        records = [{'spec': json.loads(spec), 'state': state, 'amount': amount,
                    'observation': json.loads(observation) if observation else None}
                   for spec,state,amount,observation in connection.execute('SELECT spec,state,amount,observation FROM calls')]
    result = summarize(manifest, records, prior)
    (ROOT/'plans/results.json').write_text(json.dumps(result, indent=2))
    print('Wrote preliminary counts with complete candidate denominators.')

if __name__ == '__main__':
    export()
