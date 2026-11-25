"""Verify readiness and evidence; load fixed events without duplicating IDs."""
import argparse
import hashlib
import json
from pathlib import Path
from api import APIError, INDEX, request, wait_ready

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

def verify():
    manifest = json.loads((DATA / 'manifest.json').read_text())
    for name, info in manifest['files'].items():
        p = DATA / name
        if hashlib.sha256(p.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError(f'Hash mismatch: {name}')
    print('Evidence checksums OK')
    return manifest

def bulk_load(batch):
    manifest = verify()
    wait_ready()
    mapping = json.loads((DATA / 'mapping.json').read_text())
    indices = request('GET', '/_cat/indices?format=json&h=index')
    if not any(i['index'] == INDEX for i in indices):
        request('PUT', '/' + INDEX, mapping)
    else:
        existing = request('GET', '/' + INDEX + '/_mapping')[INDEX]['mappings']
        if existing.get('dynamic') != 'strict' or existing['properties'] != mapping['mappings']['properties']:
            # Server may emit extra defaults in mappings, so compare declared types and subfields instead.
            wanted = mapping['mappings']['properties']
            def contains(actual, expected):
                return all(k in actual and (contains(actual[k], v) if isinstance(v, dict) else actual[k] == v) for k, v in expected.items())
            if existing.get('dynamic') != 'strict' or not contains(existing['properties'], wanted):
                raise APIError('Unexpected mapping on lab index. Use a clean lab volume; do not alter main mappings.')
    filename = batch + '.ndjson'
    rows = [json.loads(line) for line in (DATA / filename).read_text().splitlines()]
    if len(rows) != manifest['files'][filename]['events']:
        raise ValueError('Event count mismatch')
    for offset in range(0, len(rows), 500):
        chunk = rows[offset:offset+500]
        lines = []
        for row in chunk:
            lines.extend([json.dumps({'index': {'_id': row['event_id']}}), json.dumps(row)])
        result = request('POST', '/' + INDEX + '/_bulk?refresh=true', ('\n'.join(lines)+'\n').encode(), ndjson=True)
        if result.get('errors') or len(result.get('items', [])) != len(chunk):
            failures = [item for item in result.get('items', []) if item['index']['status'] >= 300]
            raise APIError(f'Bulk failed: {failures[:3]}')
    batch_count = request('POST', '/' + INDEX + '/_count', {'query': {'term': {'batch': batch}}})['count']
    if batch_count != len(rows):
        raise APIError(f'Batch count mismatch: {batch_count} != {len(rows)}')
    total = request('GET', '/' + INDEX + '/_count')['count']
    print(f'{batch}: {batch_count} searchable events; total index: {total}. Stable IDs make reloading idempotent.')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['verify','ready','load-initial','load-validation'])
    args = parser.parse_args()
    if args.command == 'verify': verify()
    elif args.command == 'ready': wait_ready()
    else: bulk_load(args.command.removeprefix('load-'))

if __name__ == '__main__':
    try:
        main()
    except (APIError, ValueError, KeyError, OSError) as exc:
        raise SystemExit(str(exc))
