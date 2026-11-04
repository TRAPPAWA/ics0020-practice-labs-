#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-observed-host}"
# Deliberately plaintext for packet-inspection teaching. This is not a real credential.
curl -sS "http://${TARGET}:8080/login?user=alice&token=lab-demo-token-4821" -o /dev/null || true
