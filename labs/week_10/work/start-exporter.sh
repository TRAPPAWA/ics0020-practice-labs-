#!/usr/bin/env bash
set -euo pipefail

# Complete the three TODO values. Everything else is supplied so the exercise
# stays focused on the observation point, collector address, and export format.
IFACE="TODO"
COLLECTOR="TODO"
VERSION="TODO"

CTL=/run/softflowd.ctl
PID=/run/softflowd.pid

# Allow the script to be rerun while experimenting.
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
