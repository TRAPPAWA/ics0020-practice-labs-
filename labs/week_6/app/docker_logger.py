#!/usr/bin/env python3
import argparse
import json
import sys
import time
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


p = argparse.ArgumentParser()
p.add_argument("--interval", type=float, default=1.0)
args = p.parse_args()

i = 0
while True:
    i += 1
    level = "error" if i % 10 == 0 else ("warn" if i % 5 == 0 else "info")
    record = {
        "ts": now_iso(),
        "service": "docker-logger",
        "level": level,
        "sequence": i,
        "message": f"stdout event {i}",
    }
    stream = sys.stderr if level == "error" else sys.stdout
    print(json.dumps(record, separators=(",", ":")), file=stream, flush=True)
    time.sleep(args.interval)
