"""Evaluate a student-authored OpenSearch aggregation query; no alert delivery."""
import argparse
import json
from pathlib import Path
from api import APIError, INDEX, request


def evaluate(result, minimum, percent):
    if result.get('timed_out') or result.get('_shards', {}).get('failed', 0):
        raise ValueError('Search incomplete; do not interpret partial results as normal.')
    services = result['aggregations']['by_service']
    if services.get('sum_other_doc_count', 0):
        raise ValueError('Service aggregation truncated; increase size.')
    findings = []
    for service in services['buckets']:
        routes = service['by_route']
        if routes.get('sum_other_doc_count', 0):
            raise ValueError('Route aggregation truncated; increase size.')
        for route in routes['buckets']:
            for bucket in route['windows']['buckets']:
                n = bucket['doc_count']
                errors = bucket['errors']['doc_count']
                if not 0 <= errors <= n:
                    raise ValueError('Error count is outside denominator')
                rate = 100 * errors / n if n else None
                state = 'INSUFFICIENT' if n < minimum else ('ALERT' if rate >= percent else 'OK')
                findings.append(dict(service=service['key'], route=route['key'], window=bucket['key_as_string'], requests=n, errors=errors, rate=rate, state=state))
    return sorted(findings, key=lambda x: (x['window'], x['service'], x['route']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('query', type=Path)
    p.add_argument('--min-requests', type=int, default=20)
    p.add_argument('--min-percent', type=float, default=10.0)
    p.add_argument('--all', action='store_true', help='include OK and insufficient windows')
    args = p.parse_args()
    if args.min_requests < 1 or not 0 <= args.min_percent <= 100:
        p.error('minimum requests must be positive and percentage in [0,100]')
    query = json.loads(args.query.read_text())
    if query.get('size') != 0:
        raise ValueError('Set size to 0 for an aggregation-only search')
    result = request('POST', '/' + INDEX + '/_search', query)
    rows = evaluate(result, args.min_requests, args.min_percent)
    print('window_utc\tservice\troute\trequests\t5xx\trate_percent\tstate')
    for r in rows:
        if args.all or r['state']=='ALERT':
            rate = '-' if r['rate'] is None else f"{r['rate']:.2f}"
            print(f"{r['window']}\t{r['service']}\t{r['route']}\t{r['requests']}\t{r['errors']}\t{rate}\t{r['state']}")
    print(f"Evaluated {len(rows)} populated/returned windows; alerts={sum(r['state']=='ALERT' for r in rows)}; insufficient={sum(r['state']=='INSUFFICIENT' for r in rows)}")
    if not rows:
        print('No returned windows. Check evidence, time range and filters; this does not establish health.')

if __name__ == '__main__':
    try:
        main()
    except (APIError, ValueError, KeyError, TypeError, OSError) as exc:
        raise SystemExit(str(exc))
