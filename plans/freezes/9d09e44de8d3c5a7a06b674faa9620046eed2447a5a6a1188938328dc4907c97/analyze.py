"""Export safe descriptive counts, preserving every planned denominator."""
from contextlib import closing
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from study import ROOT, digest

def summarize(manifest, records):
    outputs = []
    for entry in manifest['roster']:
        model = entry['model']
        rows = [row for row in records if row['spec']['model'] == model]
        statuses = Counter((row['observation'] or {}).get('status', row['state']) for row in rows)
        pairs = {}
        groups = {}
        for row in rows:
            spec, observation = row['spec'], row['observation'] or {}
            key = (spec['case']['id'], spec['timing'], spec['repeat'])
            pairs.setdefault(key, {})[spec['branch']] = observation
            group = groups.setdefault(spec['case']['mechanism']+'/'+spec['timing']+'/'+spec['branch'],
                                      {'attempted': 0, 'valid': 0, 'complete': 0, 'pause': 0, 'clarify': 0, 'invalid': 0})
            group['attempted'] += 1
            if observation.get('status') == 'valid':
                group['valid'] += 1
                group[observation['action']] += 1
            else:
                group['invalid'] += 1
        table = Counter()
        capability_pairs = Counter()
        for pair in pairs.values():
            stable, changed = pair.get('stable'), pair.get('changed')
            def label(observation):
                if observation is None:
                    return 'missing'
                return observation['action'] if observation.get('status') == 'valid' else 'invalid'
            table[label(stable)+' / '+label(changed)] += 1
            if label(stable) == 'complete':
                capability_pairs[label(changed)] += 1
        planned_pairs = manifest['calls_per_model']//2
        unseen = planned_pairs-len(pairs)
        if unseen:
            table['missing / missing'] += unseen
        outputs.append({'model': model, 'provider_route': entry['provider_tag'],
                        'planned_calls': manifest['calls_per_model'], 'attempted_calls': len(rows),
                        'missing_calls': manifest['calls_per_model']-len(rows),
                        'status_counts': dict(statuses), 'groups': groups,
                        'paired_table_stable_then_changed': dict(table), 'planned_pairs': planned_pairs,
                        'capability_conditioned_denominator': sum(capability_pairs.values()),
                        'capability_conditioned_changed_actions': dict(capability_pairs),
                        'accounted_cost_usd': str(sum((Decimal(row['amount']) for row in rows), Decimal('0')))})
    return {'status': 'preliminary_unreviewed_safe_proxy_study', 'manifest_sha256': digest(manifest),
            'claim_scope': manifest['claim_scope'], 'models': outputs,
            'limitations': ['Fixed synthetic histories, no model-generated rollout or real action.',
                            'Four mechanisms; contexts and repetitions are dependent.',
                            'Temperature and opaque deployment revisions vary by route.',
                            'Missing and invalid outputs are unknown outcomes, never counted as safe.',
                            'No human expert validation, independent replication, injury rates or general safety ranking.']}

if __name__ == '__main__':
    manifest = json.loads((ROOT/'plans/full-manifest.json').read_text())
    path = ROOT/'private/full.sqlite'
    with closing(sqlite3.connect(path)) as connection:
        stored = connection.execute("SELECT value FROM meta WHERE key='manifest_hash'").fetchone()[0]
        if stored != digest(manifest):
            raise RuntimeError('Report manifest differs from collected run.')
        records = [{'spec': json.loads(spec), 'state': state, 'amount': amount,
                    'observation': json.loads(observation) if observation else None}
                   for spec,state,amount,observation in connection.execute('SELECT spec,state,amount,observation FROM calls')]
    result = summarize(manifest, records)
    (ROOT/'plans/results.json').write_text(json.dumps(result, indent=2))
    print('Wrote preliminary counts with complete candidate denominators.')
