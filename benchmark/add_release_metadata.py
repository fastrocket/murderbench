"""Add reporting metadata without altering the frozen scorer or its counts."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]

def main():
    path = ROOT / 'plans/results.json'
    report = json.loads(path.read_text())
    with sqlite3.connect(ROOT / 'private/full.sqlite') as connection:
        raw = [json.loads(row[0]) for row in connection.execute('SELECT response FROM calls') if row[0]]
    timestamps = [item['created'] for item in raw if isinstance(item, dict)
                  and isinstance(item.get('created'), (int, float))]
    report['collection_metadata'] = {
        'source': 'Provider-returned response.created Unix timestamps; self-reported generation times, not local receipt times.',
        'responses_with_created': len(timestamps),
        'recorded_conditions': sum(model['attempted_calls'] for model in report['models']),
        'first_generation_utc': datetime.fromtimestamp(min(timestamps), timezone.utc).isoformat(),
        'last_generation_utc': datetime.fromtimestamp(max(timestamps), timezone.utc).isoformat(),
        'report_exported_utc': datetime.now(timezone.utc).isoformat(),
        'note': 'Reporting-only metadata added after the frozen analysis export; counts and scorer unchanged.'
    }
    path.write_text(json.dumps(report, indent=2) + '\n')
    amendment_path = ROOT / 'plans/collection-amendment.json'
    amendment = json.loads(amendment_path.read_text())
    amendment['independent_review'] = 'Operational implementation and limit reviews completed by a separate AI critic; independent scientific and label review pending. Original ten scores unchanged.'
    amendment['operational_review_artifacts'] = [
        'reviews/collection-amendment-review.txt',
        'reviews/collection-amendment-limit-review.txt'
    ]
    amendment_path.write_text(json.dumps(amendment, indent=2) + '\n')
    print(report['collection_metadata'])

if __name__ == '__main__':
    main()
