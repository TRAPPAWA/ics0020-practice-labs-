#!/usr/bin/env bash
set -euo pipefail

docker compose exec sensor softflowctl -c /run/softflowd.ctl expire-all
# nfcapd rotates every 10 seconds; give it a complete file to analyse.
sleep 11
ls -1 output/flows/nfcapd.* 2>/dev/null || true
