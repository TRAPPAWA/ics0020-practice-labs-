#!/usr/bin/env python3
import argparse
import os
import socket
import socketserver
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8080"))
TCP_PORT = int(os.environ.get("TCP_PORT", "9000"))
UDP_PORT = int(os.environ.get("UDP_PORT", "9999"))
MAX_BYTES = 2 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "LabHTTP/1.0"

    def _send(self, status, body, content_type="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/upload":
            return self._send(404, "not found\n")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        remaining = min(max(length, 0), MAX_BYTES)
        received = 0
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            received += len(chunk)
            remaining -= len(chunk)
        return self._send(200, f"received={received}\n")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            return self._send(200, "ok\n")

        if path == "/small":
            body = ("small-response\n" + ("x" * 1000) + "\n").encode()
            return self._send(200, body, "application/octet-stream")

        if path.startswith("/bytes/"):
            try:
                requested = int(path.split("/", 2)[2])
            except (ValueError, IndexError):
                return self._send(400, "use /bytes/<number>\n")
            size = max(0, min(requested, MAX_BYTES))
            return self._send(200, b"B" * size, "application/octet-stream")

        if path == "/login":
            user = query.get("user", ["unknown"])[0]
            token = query.get("token", ["missing"])[0]
            return self._send(401, f"login denied for {user}; token={token}\n")

        if path == "/beacon":
            client = query.get("client", ["unknown"])[0]
            return self._send(200, f"beacon accepted from {client}\n")

        return self._send(404, "not found\n")

    def log_message(self, fmt, *args):
        print(f"HTTP {self.client_address[0]} {fmt % args}", flush=True)


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(65535)
        if data:
            self.request.sendall(b"tcp-echo:" + data[:4096])


def run_tcp():
    with ThreadingTCPServer((HOST, TCP_PORT), TCPHandler) as server:
        server.serve_forever()


def run_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, UDP_PORT))
    while True:
        data, addr = sock.recvfrom(65535)
        sock.sendto(b"udp-echo:" + data[:4096], addr)


def main():
    threading.Thread(target=run_tcp, daemon=True).start()
    threading.Thread(target=run_udp, daemon=True).start()
    print(f"HTTP listening on {HTTP_PORT}; TCP echo on {TCP_PORT}; UDP echo on {UDP_PORT}", flush=True)
    ThreadingHTTPServer((HOST, HTTP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
