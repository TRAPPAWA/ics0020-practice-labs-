#!/usr/bin/env python3
import argparse
import json
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

FLUENT_HTTP = "http://fluentd:9880"
APP_HTTP = "http://app:8080"
SINK_HTTP = "http://sink:9000"
MONITOR_HTTP = "http://fluentd:24220"


def request(method, url, data=None, headers=None):
    body = None if data is None else data.encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            print(text)
            return 0
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 2


def cmd_post(args):
    for i in range(args.count):
        record = {
            "message": args.message,
            "level": args.level,
            "source": "toolbox",
            "sequence": i + 1,
        }
        code = request(
            "POST",
            f"{FLUENT_HTTP}/{args.tag}",
            json.dumps(record),
            {"Content-Type": "application/json"},
        )
        if code:
            return code
    return 0


def cmd_app_hit(args):
    code = 0
    for _ in range(args.count):
        code = request("GET", f"{APP_HTTP}{args.path}")
        if code:
            break
    return code


def cmd_syslog(args):
    severity_map = {
        "emerg": 0, "alert": 1, "crit": 2, "error": 3,
        "warn": 4, "notice": 5, "info": 6, "debug": 7,
    }
    pri = 16 * 8 + severity_map[args.severity]  # local0 facility
    timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    msg = f"<{pri}>1 {timestamp} toolbox labctl - LAB01 - {args.message}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(msg.encode("utf-8"), ("fluentd", 5140))
    sock.close()
    print(msg)
    return 0


def cmd_sink_count(_args):
    return request("GET", f"{SINK_HTTP}/count")


def cmd_sink_tail(args):
    return request("GET", f"{SINK_HTTP}/events?limit={args.limit}")


def cmd_sink_reset(_args):
    return request("POST", f"{SINK_HTTP}/reset", "", {"Content-Type": "application/json"})


def cmd_monitor(_args):
    return request("GET", f"{MONITOR_HTTP}/api/plugins.json")


def main():
    p = argparse.ArgumentParser(description="Helper client for the Fluentd teaching lab")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("post", help="POST JSON event(s) to Fluentd HTTP input")
    sp.add_argument("tag")
    sp.add_argument("--message", default="hello from toolbox")
    sp.add_argument("--level", default="info")
    sp.add_argument("--count", type=int, default=1)
    sp.set_defaults(func=cmd_post)

    sp = sub.add_parser("app-hit", help="Call the demo application")
    sp.add_argument("path", nargs="?", default="/")
    sp.add_argument("--count", type=int, default=1)
    sp.set_defaults(func=cmd_app_hit)

    sp = sub.add_parser("syslog", help="Send one RFC 5424 syslog datagram to Fluentd")
    sp.add_argument("--message", default="hello over syslog")
    sp.add_argument("--severity", choices=["emerg", "alert", "crit", "error", "warn", "notice", "info", "debug"], default="info")
    sp.set_defaults(func=cmd_syslog)

    sp = sub.add_parser("sink-count", help="Show how many events the HTTP sink stored")
    sp.set_defaults(func=cmd_sink_count)

    sp = sub.add_parser("sink-tail", help="Show recent sink events")
    sp.add_argument("--limit", type=int, default=5)
    sp.set_defaults(func=cmd_sink_tail)

    sp = sub.add_parser("sink-reset", help="Clear the sink data file")
    sp.set_defaults(func=cmd_sink_reset)

    sp = sub.add_parser("monitor", help="Query Fluentd monitor_agent")
    sp.set_defaults(func=cmd_monitor)

    args = p.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
