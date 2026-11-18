#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cp "$ROOT/templates/student_queries.sql" "$ROOT/work/student_queries.sql"
cp "$ROOT/templates/REPORT.md" "$ROOT/work/REPORT.md"
find "$ROOT/work" -maxdepth 1 -type f \( -name '*.csv' -o -name '*.svg' \) -delete
find "$ROOT/reports" -maxdepth 1 -type f -delete
printf 'Student work files reset.\n'
