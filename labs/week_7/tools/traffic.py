#!/usr/bin/env python3
import argparse
import datetime as dt
import itertools
import socket
import time

FACILITY = {"mail": 2, "daemon": 3, "cron": 9, "authpriv": 10, "local0": 16}
SEVERITY = {"alert": 1, "crit": 2, "err": 3, "warning": 4, "notice": 5, "info": 6, "debug": 7}


def stamp():
    return dt.datetime.now().astimezone().strftime("%b %e %H:%M:%S")


def pri(facility, severity):
    return FACILITY[facility] * 8 + SEVERITY[severity]


def send_udp(raw):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto((raw + "\n").encode(), ("syslog-ng", 514))


def send_tcp(raw):
    try:
        with socket.create_connection(("syslog-ng", 1514), timeout=3) as s:
            s.sendall((raw + "\n").encode())
    except OSError as e:
        print(f"traffic send failed: {e}", flush=True)


def build(facility, severity, host, program, message, pid=None):
    hdr = f"{program}[{pid}]" if pid else program
    return f"<{pri(facility, severity)}>{stamp()} {host} {hdr}: {message}"


def web_messages():
    n = 0
    while True:
        n += 1
        if n % 9 == 0:
            yield "tcp", build("daemon", "err", "web01", "webapp", f"critical upstream timeout request={n}", 2100 + n)
        elif n % 4 == 0:
            now = dt.datetime.now().astimezone().strftime("%d/%b/%Y:%H:%M:%S %z")
            msg = f'10.10.0.{n % 200 + 10} - - [{now}] "GET /login HTTP/1.1" 403 1234 "-" "Mozilla/5.0 Firefox/128.0"'
            yield "tcp", build("local0", "info", "web01", "apache", msg)
        else:
            yield "tcp", build("local0", "info", "web01", "nginx", f"request completed status=200 request={n}", 3000 + n)


def auth_messages():
    n = 0
    while True:
        n += 1
        if n % 5 == 0:
            msg = f"Failed password for student from 10.20.0.{n % 200 + 20} port {40000 + n} ssh2"
            sev = "warning"
        else:
            msg = f"Accepted publickey for student from 10.20.0.{n % 200 + 20} port {40000 + n} ssh2"
            sev = "notice"
        yield "udp", build("authpriv", sev, "auth01", "sshd", msg, 5000 + n)


def batch_messages():
    n = 0
    while True:
        n += 1
        if n % 7 == 0:
            yield "tcp", build("daemon", "crit", "batch01", "batchd", f"fatal database export failure job={n}", 6000 + n)
        elif n % 2 == 0:
            yield "udp", build("mail", "info", "mail01", "postfix", f"queued message id=LAB{n:05d}", 7000 + n)
        else:
            yield "udp", build("cron", "info", "batch01", "cron", f"job completed id={n}", 8000 + n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", choices=["web", "auth", "batch"], required=True)
    ap.add_argument("--interval", type=float, default=1.5)
    args = ap.parse_args()

    generators = {"web": web_messages, "auth": auth_messages, "batch": batch_messages}
    gen = generators[args.role]()
    for transport, raw in gen:
        if transport == "udp":
            send_udp(raw)
        else:
            send_tcp(raw)
        print(raw, flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
