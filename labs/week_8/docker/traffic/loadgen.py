#!/usr/bin/env python3
import argparse
import concurrent.futures
import time
import urllib.request


def fetch(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read()
        return len(data)


def main():
    p = argparse.ArgumentParser(description="Small HTTP traffic generator for the SNMP lab")
    p.add_argument("--target", required=True, help="URL, for example http://student-agent:8080/bytes/65536")
    p.add_argument("--duration", type=float, default=20.0)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--timeout", type=float, default=3.0)
    args = p.parse_args()

    deadline = time.monotonic() + args.duration
    requests = 0
    failures = 0
    total_bytes = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        active = set()
        while time.monotonic() < deadline or active:
            while time.monotonic() < deadline and len(active) < args.workers:
                active.add(pool.submit(fetch, args.target, args.timeout))
            if not active:
                break
            done, active = concurrent.futures.wait(
                active,
                timeout=0.2,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for fut in done:
                requests += 1
                try:
                    total_bytes += fut.result()
                except Exception:
                    failures += 1

    mib = total_bytes / (1024 * 1024)
    print(f"requests={requests} failures={failures} response_data={mib:.2f} MiB duration={args.duration:.1f}s")


if __name__ == "__main__":
    main()
