#!/usr/bin/env python3
import argparse
import datetime as dt
import socket
import ssl
import sys
import time

FACILITIES = {
    "kern": 0, "user": 1, "mail": 2, "daemon": 3, "auth": 4, "syslog": 5,
    "lpr": 6, "news": 7, "uucp": 8, "cron": 9, "authpriv": 10, "ftp": 11,
    "ntp": 12, "security": 13, "console": 14, "solaris-cron": 15,
    "local0": 16, "local1": 17, "local2": 18, "local3": 19,
    "local4": 20, "local5": 21, "local6": 22, "local7": 23,
}
SEVERITIES = {
    "emerg": 0, "alert": 1, "crit": 2, "err": 3, "warning": 4, "notice": 5,
    "info": 6, "debug": 7,
}
SEVERITY_ALIASES = {"emergency": "emerg", "panic": "emerg", "critical": "crit", "error": "err", "warn": "warning", "informational": "info"}


def canonical_severity(value: str) -> str:
    value = value.lower()
    return SEVERITY_ALIASES.get(value, value)


def pri(facility: str, severity: str) -> int:
    facility = facility.lower()
    severity = canonical_severity(severity)
    if facility not in FACILITIES:
        raise SystemExit(f"Unknown facility: {facility}")
    if severity not in SEVERITIES:
        raise SystemExit(f"Unknown severity: {severity}")
    return FACILITIES[facility] * 8 + SEVERITIES[severity]


def bsd_timestamp() -> str:
    # RFC3164-style timestamps have no year and use English month abbreviations.
    return dt.datetime.now().astimezone().strftime("%b %e %H:%M:%S")


def rfc3339() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_bsd(facility: str, severity: str, host: str, program: str, message: str, pid: str | None = None) -> str:
    p = pri(facility, severity)
    header = f"{program}[{pid}]" if pid else program
    return f"<{p}>{bsd_timestamp()} {host} {header}: {message}"


def build_ietf(facility: str, severity: str, host: str, program: str, message: str,
               procid: str = "-", msgid: str = "LAB", structured_data: str = "-") -> str:
    p = pri(facility, severity)
    return f"<{p}>1 {rfc3339()} {host} {program} {procid} {msgid} {structured_data} {message}"


def send_udp(host: str, port: int, payload: bytes) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(payload, (host, port))


def send_tcp(host: str, port: int, payload: bytes) -> None:
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(payload)


def send_tls(host: str, port: int, payload: bytes, cafile: str, insecure: bool = False) -> None:
    if insecure:
        context = ssl._create_unverified_context()
    else:
        context = ssl.create_default_context(cafile=cafile)
    with socket.create_connection((host, port), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=host) as s:
            s.sendall(payload)


def print_sent(kind: str, transport: str, p: int, raw: str) -> None:
    print(f"sent {kind} over {transport}; PRI={p}")
    print(raw)


def cmd_pri(args):
    p = pri(args.facility, args.severity)
    print(f"PRI={p} = {FACILITIES[args.facility.lower()]}*8 + {SEVERITIES[canonical_severity(args.severity)]}")


def cmd_send_bsd(args):
    raw = build_bsd(args.facility, args.severity, args.host, args.program, args.message, args.pid)
    payload = (raw + "\n").encode()
    p = pri(args.facility, args.severity)
    if args.transport == "udp":
        send_udp(args.target, args.port or 514, payload)
    else:
        send_tcp(args.target, args.port or 1514, payload)
    print_sent("RFC3164/BSD", args.transport, p, raw)


def cmd_send_ietf(args):
    raw = build_ietf(args.facility, args.severity, args.host, args.program, args.message,
                     args.procid, args.msgid, args.sd)
    p = pri(args.facility, args.severity)
    if args.transport == "udp":
        send_udp(args.target, args.port or 8514, raw.encode())
    elif args.transport == "tcp":
        framed = f"{len(raw.encode())} {raw}".encode()
        send_tcp(args.target, args.port or 601, framed)
    else:
        framed = f"{len(raw.encode())} {raw}".encode()
        send_tls(args.target, args.port or 6514, framed, args.cafile, args.insecure)
    print_sent("RFC5424/IETF", args.transport, p, raw)


def cmd_apache(args):
    if args.browser == "firefox":
        ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'
        status = 403
        path = "/"
    else:
        ua = 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)'
        status = 200
        path = "/aux.html"
    apache_time = dt.datetime.now().astimezone().strftime("%d/%b/%Y:%H:%M:%S %z")
    msg = f'10.1.13.5 - - [{apache_time}] "GET {path} HTTP/1.1" {status} 4897 "-" "{ua}"'
    raw = build_bsd("local0", "info", args.host, "apache", msg, None)
    payload = (raw + "\n").encode()
    if args.transport == "udp":
        send_udp(args.target, 514, payload)
    else:
        send_tcp(args.target, 1514, payload)
    print_sent("Apache-in-syslog", args.transport, pri("local0", "info"), raw)


def cmd_burst(args):
    for i in range(1, args.count + 1):
        severity = args.severity
        text = args.message.replace("{n}", str(i))
        raw = build_bsd(args.facility, severity, args.host, args.program, text, str(4000 + i))
        payload = (raw + "\n").encode()
        if args.transport == "udp":
            send_udp(args.target, 514, payload)
        else:
            send_tcp(args.target, 1514, payload)
        if args.delay:
            time.sleep(args.delay)
    print(f"sent {args.count} RFC3164/BSD messages over {args.transport}")


def cmd_probe(args):
    if args.transport == "udp":
        print("UDP has no connection handshake; sending a datagram probe instead.")
        send_udp(args.target, args.port, b"<134>Oct 14 00:00:00 probe labctl: probe\n")
        print("datagram sent")
        return
    try:
        with socket.create_connection((args.target, args.port), timeout=args.timeout):
            print(f"TCP connection succeeded: {args.target}:{args.port}")
    except OSError as e:
        print(f"TCP connection failed: {e}", file=sys.stderr)
        raise SystemExit(1)


def build_parser():
    p = argparse.ArgumentParser(description="Containerized syslog lab client")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pri", help="calculate a syslog PRI value")
    s.add_argument("--facility", required=True, choices=sorted(FACILITIES))
    s.add_argument("--severity", required=True)
    s.set_defaults(func=cmd_pri)

    s = sub.add_parser("send-bsd", help="send an RFC3164/BSD-style syslog message")
    s.add_argument("--target", default="syslog-ng")
    s.add_argument("--transport", choices=["udp", "tcp"], default="udp")
    s.add_argument("--port", type=int)
    s.add_argument("--facility", default="user", choices=sorted(FACILITIES))
    s.add_argument("--severity", default="info")
    s.add_argument("--host", default="student-host")
    s.add_argument("--program", default="labapp")
    s.add_argument("--pid")
    s.add_argument("--message", default="hello from the toolbox")
    s.set_defaults(func=cmd_send_bsd)

    s = sub.add_parser("send-ietf", help="send an RFC5424/IETF syslog message")
    s.add_argument("--target", default="syslog-ng")
    s.add_argument("--transport", choices=["udp", "tcp", "tls"], default="udp")
    s.add_argument("--port", type=int)
    s.add_argument("--facility", default="local0", choices=sorted(FACILITIES))
    s.add_argument("--severity", default="info")
    s.add_argument("--host", default="ietf-host")
    s.add_argument("--program", default="api")
    s.add_argument("--procid", default="1234")
    s.add_argument("--msgid", default="LAB42")
    s.add_argument("--sd", default='[lab@32473 env="docker" course="logging"]')
    s.add_argument("--message", default="structured syslog event")
    s.add_argument("--cafile", default="/certs/ca.crt")
    s.add_argument("--insecure", action="store_true", help="skip certificate verification (lab debugging only)")
    s.set_defaults(func=cmd_send_ietf)

    s = sub.add_parser("apache", help="send a simulated Apache access log wrapped in BSD syslog")
    s.add_argument("--target", default="syslog-ng")
    s.add_argument("--transport", choices=["udp", "tcp"], default="tcp")
    s.add_argument("--browser", choices=["firefox", "ie"], default="firefox")
    s.add_argument("--host", default="web01")
    s.set_defaults(func=cmd_apache)

    s = sub.add_parser("burst", help="send many BSD messages")
    s.add_argument("--target", default="syslog-ng")
    s.add_argument("--transport", choices=["udp", "tcp"], default="tcp")
    s.add_argument("--count", type=int, default=20)
    s.add_argument("--delay", type=float, default=0.0)
    s.add_argument("--facility", default="daemon", choices=sorted(FACILITIES))
    s.add_argument("--severity", default="err")
    s.add_argument("--host", default="burst01")
    s.add_argument("--program", default="batchd")
    s.add_argument("--message", default="critical queue failure sequence={n}")
    s.set_defaults(func=cmd_burst)

    s = sub.add_parser("probe", help="test TCP connectivity or send a UDP probe")
    s.add_argument("--target", default="syslog-ng")
    s.add_argument("--transport", choices=["tcp", "udp"], default="tcp")
    s.add_argument("--port", type=int, required=True)
    s.add_argument("--timeout", type=float, default=2.0)
    s.set_defaults(func=cmd_probe)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (ConnectionRefusedError, TimeoutError, OSError, ssl.SSLError) as e:
        print(f"send failed: {e}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
