#!/usr/bin/env python3
import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DATA_FILE = os.environ.get("SINK_FILE", "/data/received.jsonl")
PORT = int(os.environ.get("SINK_PORT", "9000"))
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def read_lines():
    if not os.path.exists(DATA_FILE):
        return []
    with LOCK, open(DATA_FILE, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


class Handler(BaseHTTPRequestHandler):
    server_version = "FluentdLabSink/1.0"

    def log_message(self, format, *args):
        print("sink:", format % args, flush=True)

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"ok": True})
            return
        if parsed.path == "/count":
            self._json(200, {"count": len(read_lines())})
            return
        if parsed.path == "/events":
            limit = int(parse_qs(parsed.query).get("limit", ["10"])[0])
            lines = read_lines()[-max(1, min(limit, 100)):]
            events = []
            for line in lines:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    events.append({"raw": line})
            self._json(200, {"count": len(events), "events": events})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/reset":
            with LOCK, open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write("")
            self._json(200, {"ok": True, "count": 0})
            return
        if parsed.path != "/events":
            self._json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        content_type = self.headers.get("Content-Type", "")
        records = []
        try:
            if "application/json" in content_type:
                parsed_body = json.loads(raw or "[]")
                records = parsed_body if isinstance(parsed_body, list) else [parsed_body]
            else:
                for line in raw.splitlines():
                    if line.strip():
                        records.append(json.loads(line))
        except Exception as exc:
            self._json(400, {"error": f"cannot parse request: {exc}"})
            return

        with LOCK, open(DATA_FILE, "a", encoding="utf-8") as f:
            for record in records:
                envelope = {"received_at": now_iso(), "record": record}
                f.write(json.dumps(envelope, separators=(",", ":")) + "\n")
        self._json(200, {"ok": True, "accepted": len(records)})


if __name__ == "__main__":
    print(f"lab sink listening on 0.0.0.0:{PORT}; file={DATA_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
