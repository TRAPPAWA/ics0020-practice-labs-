#!/usr/bin/env python3
"""Rank repeated destination pairs by their inter-flow timing."""
import argparse
import collections
import csv
import datetime as dt
import statistics


def parse_offset(text):
    if text.upper() in {'Z', 'UTC', '+00:00', '-00:00'}:
        return dt.timezone.utc
    sign = 1 if text[0] == '+' else -1
    hours, minutes = map(int, (text[1:3], text[4:6]))
    return dt.timezone(sign * dt.timedelta(hours=hours, minutes=minutes))


def parse_time(text, timezone):
    text = text.strip()
    try:
        value = float(text)
        if value > 100000000:
            return value
    except ValueError:
        pass
    for pattern in (
        '%Y/%m/%d %H:%M:%S.%f', '%Y/%m/%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
    ):
        try:
            return dt.datetime.strptime(text, pattern).replace(tzinfo=timezone).timestamp()
        except ValueError:
            pass
    return None


def norm(text):
    return ''.join(ch.lower() for ch in text if ch.isalnum() or ch == '_')


def find(header, names):
    normalized = [norm(x) for x in header]
    for i, value in enumerate(normalized):
        if value in names:
            return i
    return None


def main():
    parser = argparse.ArgumentParser(description='Find repeated destination pairs and inter-flow timing in CTU-style flow CSV.')
    parser.add_argument('file')
    parser.add_argument('--src', required=True)
    parser.add_argument('--min-count', type=int, default=5)
    parser.add_argument('--utc-offset', default='+00:00')
    args = parser.parse_args()
    timezone = parse_offset(args.utc_offset)

    groups = collections.defaultdict(list)
    with open(args.file, encoding='utf-8', errors='replace', newline='') as handle:
        reader = csv.reader(handle)
        header = next(reader)
        si = find(header, {'srcaddr', 'saddr', 'srcip', 'sourceip'})
        di = find(header, {'dstaddr', 'daddr', 'dstip', 'destinationip'})
        pi = find(header, {'dport', 'dstport', 'destinationport'})
        ti = find(header, {'starttime', 'stime', 'start'})
        if None in (si, di, pi, ti):
            raise SystemExit(f'needed columns not found: {header}')
        for row in reader:
            if len(row) <= max(si, di, pi, ti) or row[si].strip() != args.src:
                continue
            timestamp = parse_time(row[ti], timezone)
            if timestamp is not None:
                groups[(row[di].strip(), row[pi].strip())].append(timestamp)

    output = []
    for key, times in groups.items():
        times.sort()
        if len(times) < args.min_count:
            continue
        gaps = [b - a for a, b in zip(times, times[1:])]
        output.append((
            len(times),
            statistics.median(gaps) if gaps else 0.0,
            statistics.mean(gaps) if gaps else 0.0,
            min(gaps) if gaps else 0.0,
            max(gaps) if gaps else 0.0,
            key[0], key[1],
        ))

    output.sort(reverse=True)
    print('count\tmedian_gap_s\tmean_gap_s\tmin_gap_s\tmax_gap_s\tdestination\tport')
    for n, median, mean, minimum, maximum, dest, port in output[:50]:
        print(f'{n}\t{median:.2f}\t{mean:.2f}\t{minimum:.2f}\t{maximum:.2f}\t{dest}\t{port}')


if __name__ == '__main__':
    main()
