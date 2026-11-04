#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-observed-host}"
SIZE="${SIZE:-524288}"
COUNT="${COUNT:-16}"

echo "Uploading ${COUNT} request bodies of ${SIZE} bytes to ${TARGET}"
for i in $(seq 1 "$COUNT"); do
  head -c "$SIZE" /dev/zero | curl -fsS -X POST --data-binary @- "http://${TARGET}:8080/upload" -o /dev/null
done

echo "Bulk traffic complete"
