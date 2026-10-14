#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose --profile traffic down -v --remove-orphans || true
cp starter/syslog-ng.conf syslog-ng/conf/syslog-ng.conf
find output/main -mindepth 1 ! -name .gitkeep -delete
find output/collector -mindepth 1 ! -name .gitkeep -delete

echo "Lab reset to starter configuration."
