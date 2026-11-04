#!/usr/bin/env bash
set -euo pipefail

docker compose down --remove-orphans || true
rm -f output/flows/nfcapd.* output/flows/current.* output/pcap/*.pcap work/flows.csv 2>/dev/null || true

cat > work/start-exporter.sh <<'INNER'
#!/usr/bin/env bash
set -euo pipefail

IFACE="TODO"
COLLECTOR="TODO"
VERSION="TODO"

CTL=/run/softflowd.ctl
PID=/run/softflowd.pid

if [ -S "$CTL" ]; then
  softflowctl -c "$CTL" shutdown >/dev/null 2>&1 || true
  sleep 1
fi
rm -f "$CTL" "$PID"

softflowd \
  -i "$IFACE" \
  -n "$COLLECTOR" \
  -v "$VERSION" \
  -T full \
  -t maxlife=30s \
  -t expint=5s \
  -c "$CTL" \
  -p "$PID" \
  'not (udp and dst port 2055)'

echo "softflowd started"
INNER

cat > work/analyze_flows.py <<'INNER'
#!/usr/bin/env python3
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
        # TODO 2: increment flow, packet, and byte totals for src_ip.
        # TODO 3: add dst_port to the source's destination-port set.
        # TODO 4: add proto to the source's protocol set.
        pass

print(f"{'source':<16} {'flows':>7} {'bytes':>12} {'pkts':>9} {'ports':>7}  classification")
print("-" * 72)
for src_ip, data in sorted(stats.items(), key=lambda item: item[1]["bytes"], reverse=True):
    distinct_ports = len(data["dst_ports"])
    # TODO 5: scan-like if >= 12 destination ports and >= 12 flows.
    # TODO 6: bulk-sender if >= 2 MiB source bytes.
    # Otherwise baseline.
    classification = "TODO"
    print(f"{src_ip:<16} {data['flows']:>7} {data['bytes']:>12} {data['packets']:>9} {distinct_ports:>7}  {classification}")
INNER

chmod +x work/start-exporter.sh work/analyze_flows.py

echo "Lab reset. Run: docker compose up -d --build"
