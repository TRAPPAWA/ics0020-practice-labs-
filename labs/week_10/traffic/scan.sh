#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-observed-host}"

echo "Generating a small TCP connect scan against ${TARGET}"
nmap -Pn -sT -p 8075-8090,8995-9010 "$TARGET"

echo "Generating a short periodic beacon-like pattern"
for i in $(seq 1 8); do
  curl -fsS "http://${TARGET}:8080/beacon?client=client-scan&seq=${i}" -o /dev/null
  sleep 1
done
