#!/usr/bin/env python3
"""Summarize a CSV exported by nfdump.

Expected columns, in order:
    src_ip, src_port, dst_ip, dst_port, proto, packets, bytes

Complete the TODO sections. Do not hardcode the three client addresses in the
aggregation logic: the point is to derive behaviour from the flow records.
"""

import csv
import sys
from collections import defaultdict

if len(sys.argv) != 2:
    print(f"usage: {sys.argv[0]} FLOWS.csv", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]

stats = defaultdict(lambda: {
    "flows": 0,
    "bytes": 0,
    "packets": 0,
    "dst_ports": set(),
    "protocols": set(),
})

with open(path, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader, None)
    for row in reader:
        if len(row) < 7:
            continue

        src_ip, src_port, dst_ip, dst_port, proto, packets, byte_count = row[:7]

        # TODO 1: convert packets and byte_count to integers.
        # TODO 2: increment the source IP's flow, packet, and byte totals.
        # TODO 3: add dst_port to its set of destination ports.
        # TODO 4: add proto to its set of protocols.
        pass

print(f"{'source':<16} {'flows':>7} {'bytes':>12} {'pkts':>9} {'ports':>7}  classification")
print("-" * 72)

for src_ip, data in sorted(stats.items(), key=lambda item: item[1]["bytes"], reverse=True):
    distinct_ports = len(data["dst_ports"])

    # TODO 5: classify scan-like sources. A reasonable lab heuristic is:
    #          >= 12 distinct destination ports and >= 12 flows.
    # TODO 6: classify bulk senders. A reasonable lab heuristic is:
    #          >= 2 MiB total source bytes.
    # Otherwise label the source "baseline".
    classification = "TODO"

    print(
        f"{src_ip:<16} {data['flows']:>7} {data['bytes']:>12} "
        f"{data['packets']:>9} {distinct_ports:>7}  {classification}"
    )
