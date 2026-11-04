#!/usr/bin/env bash
set -euo pipefail

docker compose stop flow-collector >/dev/null
rm -f output/flows/nfcapd.* output/flows/current.* output/pcap/*.pcap 2>/dev/null || true
docker compose up -d flow-collector >/dev/null

echo "Flow and PCAP output cleared."
