#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-observed-host}"

echo "Generating normal mixed traffic to ${TARGET}"
for i in $(seq 1 18); do
  curl -fsS "http://${TARGET}:8080/small" -o /dev/null
  if (( i % 6 == 0 )); then
    printf 'normal-udp-%s\n' "$i" | nc -u -w 1 "$TARGET" 9999 >/dev/null 2>&1 || true
  fi
  sleep 0.15
done

printf 'normal-tcp\n' | nc -w 1 "$TARGET" 9000 >/dev/null 2>&1 || true
ping -c 3 -W 1 "$TARGET" >/dev/null 2>&1 || true

echo "Normal traffic complete"
