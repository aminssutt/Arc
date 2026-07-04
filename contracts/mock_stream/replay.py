#!/usr/bin/env python3
"""Arc mock SSE replay server (P0.8) — stdlib only, no dependencies.

Serves an .ndjson fixture over real SSE at the SAME path as the future backend
(/api/stream), so switching frontend/iOS to the real thing is a base-URL flip.

    python replay.py run_confirm.ndjson                  # 10x speed, port 8010
    python replay.py run_pivot.ndjson --speed 30 --port 8011
    curl -N http://localhost:8010/api/stream

Behavior (mirrors the frozen contract, see ../EVENTS.md):
  - each line of the fixture is one envelope; emitted as `id:` + `event:` + `data:`
  - inter-event delay = (ts delta) / --speed, capped at --max-gap seconds so the
    technician's 10-minute field trip doesn't stall a demo
  - `: hb` heartbeat comment every 15 s of wall time, including while idle
  - multiple concurrent clients: each connection gets its own replay from t0
  - Last-Event-ID (header or ?lastEventId=) resumes after that envelope id
  - CORS open for local dev; GET /health returns 200
"""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from urllib.parse import urlparse, parse_qs

EVENTS = []  # [(ts_epoch, id, type, raw_line)]
ARGS = None


def load(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            env = json.loads(line)  # crash loudly on invalid fixture
            for k in ("seq", "id", "ts", "incident_id", "type", "data"):
                if k not in env:
                    sys.exit(f"{path}:{n}: envelope missing required key '{k}'")
            ts = datetime.fromisoformat(env["ts"].replace("Z", "+00:00")).timestamp()
            out.append((ts, env["id"], env["type"], json.dumps(env, separators=(",", ":"))))
    if not out:
        sys.exit(f"{path}: no events")
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Last-Event-ID, Cache-Control")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            body = b'{"status":"ok","mode":"mock-replay"}'
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path != "/api/stream":
            self.send_response(404)
            self.end_headers()
            return

        last_id = self.headers.get("Last-Event-ID") or \
            (parse_qs(url.query).get("lastEventId", [None])[0])
        start_idx = 0
        if last_id:
            for i, (_, eid, _, _) in enumerate(EVENTS):
                if eid == last_id:
                    start_idx = i + 1
                    break

        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self._stream(start_idx)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # client went away — normal

    def _emit(self, text):
        self.wfile.write(text.encode("utf-8"))
        self.wfile.flush()

    def _sleep_with_heartbeat(self, delay):
        while delay > 0:
            chunk = min(delay, 15.0)
            time.sleep(chunk)
            delay -= chunk
            if delay > 0:
                self._emit(": hb\n\n")

    def _stream(self, start_idx):
        prev_ts = None
        for ts, eid, etype, raw in EVENTS[start_idx:]:
            if prev_ts is not None:
                self._sleep_with_heartbeat(
                    min((ts - prev_ts) / ARGS.speed, ARGS.max_gap))
            prev_ts = ts
            self._emit(f"id: {eid}\nevent: {etype}\ndata: {raw}\n\n")
        # fixture exhausted: hold the connection open with heartbeats (real
        # backend behaves the same between incidents)
        while True:
            time.sleep(15)
            self._emit(": hb\n\n")

    def log_message(self, fmt, *a):  # quieter default log line
        sys.stderr.write("[replay] %s\n" % (fmt % a))


def main():
    global EVENTS, ARGS
    p = argparse.ArgumentParser(description="Arc mock SSE replay server")
    p.add_argument("fixture", help="path to run_confirm.ndjson / run_pivot.ndjson")
    p.add_argument("--speed", type=float, default=10.0, help="time compression factor (default 10)")
    p.add_argument("--max-gap", type=float, default=5.0, help="max seconds between events after compression (default 5)")
    p.add_argument("--port", type=int, default=8010)
    ARGS = p.parse_args()
    EVENTS = load(ARGS.fixture)
    print(f"[replay] {len(EVENTS)} events from {ARGS.fixture} | speed x{ARGS.speed} "
          f"| max-gap {ARGS.max_gap}s | http://localhost:{ARGS.port}/api/stream")
    ThreadingHTTPServer(("0.0.0.0", ARGS.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
