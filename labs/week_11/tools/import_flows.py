#!/usr/bin/env python3
"""Import CTU/Argus-style bidirectional flow CSV into a normalized SQLite table.

The CTU Scenario 6 text timestamps are in CEST (UTC+02:00).  The importer keeps
both the original text and a normalized Unix epoch so that packet and flow
records can be correlated without silently mixing time zones.
"""
import argparse
import csv
import datetime as dt
import os
import sqlite3

ALIASES = {
    'start': {'starttime', 'stime', 'start', 'first', 'firstseen'},
    'last': {'lasttime', 'ltime', 'last', 'lastseen'},
    'duration': {'dur', 'duration'},
    'proto': {'proto', 'protocol'},
    'state': {'state', 'status'},
    'src_addr': {'srcaddr', 'saddr', 'srcip', 'sourceip', 'source_ip'},
    'src_port': {'sport', 'srcport', 'sourceport', 'source_port'},
    'dst_addr': {'dstaddr', 'daddr', 'dstip', 'destinationip', 'destination_ip'},
    'dst_port': {'dport', 'dstport', 'destinationport', 'destination_port'},
    'src_packets': {'srcpkts', 'spkts', 'srcpackets'},
    'dst_packets': {'dstpkts', 'dpkts', 'dstpackets'},
    'packets': {'totpkts', 'pkts', 'packets'},
    'src_bytes': {'srcbytes', 'sbytes'},
    'dst_bytes': {'dstbytes', 'dbytes'},
    'bytes': {'totbytes', 'bytes'},
    'src_app_bytes': {'sappbytes', 'srcappbytes'},
    'dst_app_bytes': {'dappbytes', 'dstappbytes'},
    'app_bytes': {'totappbyte', 'totappbytes', 'appbytes'},
    'label': {'label', 'class'},
}


def norm(s):
    return ''.join(ch.lower() for ch in s if ch.isalnum() or ch == '_')


def index_map(header):
    normalized = [norm(h) for h in header]
    out = {}
    for canon, aliases in ALIASES.items():
        for i, h in enumerate(normalized):
            if h in aliases:
                out[canon] = i
                break
    required = {'src_addr', 'dst_addr', 'proto'}
    missing = required - set(out)
    if missing:
        raise ValueError(f'missing required flow columns {sorted(missing)}; header={header}')
    return out


def val(row, idx, key, default=''):
    i = idx.get(key)
    if i is None or i >= len(row):
        return default
    return row[i].strip()


def number(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def integerish(s):
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return 0


def parse_offset(text):
    if text.upper() in {'Z', 'UTC', '+00:00', '-00:00'}:
        return dt.timezone.utc
    if len(text) != 6 or text[0] not in '+-' or text[3] != ':':
        raise argparse.ArgumentTypeError('offset must look like +02:00, -05:00, or UTC')
    try:
        hours = int(text[1:3])
        minutes = int(text[4:6])
    except ValueError as exc:
        raise argparse.ArgumentTypeError('invalid UTC offset') from exc
    if hours > 23 or minutes > 59:
        raise argparse.ArgumentTypeError('invalid UTC offset')
    sign = 1 if text[0] == '+' else -1
    return dt.timezone(sign * dt.timedelta(hours=hours, minutes=minutes))


def parse_epoch(text, timezone):
    text = text.strip()
    if not text:
        return None
    try:
        value = float(text)
        if value > 100000000:
            return value
    except ValueError:
        pass
    patterns = (
        '%Y/%m/%d %H:%M:%S.%f', '%Y/%m/%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
    )
    for pattern in patterns:
        try:
            stamp = dt.datetime.strptime(text, pattern).replace(tzinfo=timezone)
            return stamp.timestamp()
        except ValueError:
            pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('database')
    parser.add_argument(
        '--utc-offset', default='+00:00',
        help='UTC offset of text timestamps, e.g. +02:00 for CTU Scenario 6 (default: +00:00)',
    )
    args = parser.parse_args()
    timezone = parse_offset(args.utc_offset)

    if os.path.exists(args.database):
        os.remove(args.database)

    con = sqlite3.connect(args.database)
    con.executescript('''
      CREATE TABLE flows(
        id INTEGER PRIMARY KEY,
        start_text TEXT,
        start_epoch REAL,
        last_text TEXT,
        last_epoch REAL,
        duration REAL,
        proto TEXT,
        state TEXT,
        src_addr TEXT,
        src_port TEXT,
        dst_addr TEXT,
        dst_port TEXT,
        src_packets INTEGER,
        dst_packets INTEGER,
        packets INTEGER,
        src_bytes INTEGER,
        dst_bytes INTEGER,
        bytes INTEGER,
        src_app_bytes INTEGER,
        dst_app_bytes INTEGER,
        app_bytes INTEGER,
        label TEXT
      );
      CREATE INDEX idx_src ON flows(src_addr);
      CREATE INDEX idx_dst ON flows(dst_addr);
      CREATE INDEX idx_dport ON flows(dst_port);
      CREATE INDEX idx_start ON flows(start_epoch);
      CREATE INDEX idx_pair ON flows(dst_addr, dst_port);
    ''')

    insert = '''
      INSERT INTO flows(
        start_text,start_epoch,last_text,last_epoch,duration,proto,state,
        src_addr,src_port,dst_addr,dst_port,
        src_packets,dst_packets,packets,
        src_bytes,dst_bytes,bytes,
        src_app_bytes,dst_app_bytes,app_bytes,label
      ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    '''

    count = 0
    batch = []
    with open(args.input, 'r', encoding='utf-8', errors='replace', newline='') as handle:
        reader = csv.reader(handle)
        header = next(reader)
        idx = index_map(header)
        for row in reader:
            start_text = val(row, idx, 'start')
            last_text = val(row, idx, 'last')
            src_packets = integerish(val(row, idx, 'src_packets'))
            dst_packets = integerish(val(row, idx, 'dst_packets'))
            packets = integerish(val(row, idx, 'packets'))
            if packets == 0 and (src_packets or dst_packets):
                packets = src_packets + dst_packets
            src_bytes = integerish(val(row, idx, 'src_bytes'))
            dst_bytes = integerish(val(row, idx, 'dst_bytes'))
            total_bytes = integerish(val(row, idx, 'bytes'))
            if total_bytes == 0 and (src_bytes or dst_bytes):
                total_bytes = src_bytes + dst_bytes
            src_app = integerish(val(row, idx, 'src_app_bytes'))
            dst_app = integerish(val(row, idx, 'dst_app_bytes'))
            app_bytes = integerish(val(row, idx, 'app_bytes'))
            if app_bytes == 0 and (src_app or dst_app):
                app_bytes = src_app + dst_app

            batch.append((
                start_text, parse_epoch(start_text, timezone),
                last_text, parse_epoch(last_text, timezone),
                number(val(row, idx, 'duration')),
                val(row, idx, 'proto').lower(), val(row, idx, 'state'),
                val(row, idx, 'src_addr'), val(row, idx, 'src_port'),
                val(row, idx, 'dst_addr'), val(row, idx, 'dst_port'),
                src_packets, dst_packets, packets,
                src_bytes, dst_bytes, total_bytes,
                src_app, dst_app, app_bytes,
                val(row, idx, 'label'),
            ))
            if len(batch) >= 5000:
                con.executemany(insert, batch)
                count += len(batch)
                batch.clear()
        if batch:
            con.executemany(insert, batch)
            count += len(batch)

    con.commit()
    print(f'imported {count} rows into {args.database}')
    print(f'text timestamp offset interpreted as {args.utc_offset}')
    print('use datetime(start_epoch, "unixepoch") for normalized UTC display')


if __name__ == '__main__':
    main()
