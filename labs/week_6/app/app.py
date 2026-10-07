#!/usr/bin/env python3
import json
import os
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOG_FILE = os.environ.get("APP_LOG_FILE", "/var/log/lab/app.jsonl")
PORT = int(os.environ.get("APP_PORT", "8080"))
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def emit(record):
    line = json.dumps(record, separators=(",", ":"), sort_keys=True)
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "FluentdLabApp/1.0"

    def log_message(self, format, *args):
        # Suppress BaseHTTPRequestHandler's unstructured stderr logging.
        return

    def _reply(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        started = time.perf_counter()
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        request_id = str(uuid.uuid4())[:8]

        status = 200
        level = "info"
        message = "request completed"
        payload = {"ok": True, "path": path, "request_id": request_id}

        if path == "/health":
            message = "health check"
        elif path == "/error":
            status = 500
            level = "error"
            message = "synthetic application error"
            payload = {"ok": False, "error": "synthetic failure", "request_id": request_id}
        elif path == "/debug":
            level = "debug"
            message = "debug endpoint invoked"
        elif path == "/slow":
            time.sleep(0.25)
            level = "warn"
            message = "slow request"
        elif path == "/burst":
            n = min(max(int(query.get("n", ["10"])[0]), 1), 200)
            for i in range(n):
                emit({
                    "ts": now_iso(),
                    "service": "demo-app",
                    "level": "info" if i % 7 else "warn",
                    "event": "synthetic_burst",
                    "sequence": i + 1,
                    "request_id": request_id,
                    "message": f"burst event {i + 1}",
                })
            payload["generated"] = n
            message = "burst generated"
        elif path != "/":
            status = 404
            level = "warn"
            message = "path not found"
            payload = {"ok": False, "error": "not found", "request_id": request_id}

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        emit({
            "ts": now_iso(),
            "service": "demo-app",
            "level": level,
            "event": "http_request",
            "method": "GET",
            "path": path,
            "status": status,
            "latency_ms": latency_ms,
            "request_id": request_id,
            "message": message,
        })
        self._reply(status, payload)


if __name__ == "__main__":
    print(f"lab app listening on 0.0.0.0:{PORT}; file={LOG_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
