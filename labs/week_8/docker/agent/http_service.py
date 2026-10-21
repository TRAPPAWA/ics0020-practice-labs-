#!/usr/bin/env python3
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path == "/health":
            body = b"ok\n"
        elif self.path.startswith("/bytes/"):
            try:
                count = int(self.path.split("/", 2)[2])
            except Exception:
                self.send_error(400, "expected /bytes/<number>")
                return
            count = max(0, min(count, 1024 * 1024))
            body = b"x" * count
        else:
            body = b"SNMP lab device\n"
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8080)
    args = p.parse_args()
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
