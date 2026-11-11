#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../evidence"

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum -c SHA256SUMS
elif command -v shasum >/dev/null 2>&1; then
  while read -r expected file; do
    actual=$(shasum -a 256 "$file" | awk '{print $1}')
    if [ "$actual" != "$expected" ]; then
      echo "$file: FAILED" >&2
      exit 1
    fi
    echo "$file: OK"
  done < SHA256SUMS
else
  echo 'Need sha256sum (Linux) or shasum (macOS) to verify evidence.' >&2
  exit 1
fi
