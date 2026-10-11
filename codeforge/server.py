"""A tiny local web server for the CodeForge interface.

Uses only Python's standard library (no Flask, nothing to install).
    python -m codeforge.server            -> http://127.0.0.1:8000
    python -m codeforge.server 9000       -> use a different port

Two routes:
    GET  /             the web page (codeforge/web/index.html)
    POST /api/compile  body {"source": "..."}  ->  JSON from run_pipeline()
"""

import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .pipeline import run_pipeline

INDEX_HTML = Path(__file__).parent / "web" / "index.html"
MAX_BODY = 1_000_000   # refuse request bodies larger than ~1 MB


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/compile":
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_BODY:
                raise ValueError("request too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            source = payload.get("source", "")
            if not isinstance(source, str):
                raise ValueError("'source' must be text")
            body = json.dumps(run_pipeline(source)).encode("utf-8")
            self._send(200, body, "application/json")
        except (ValueError, json.JSONDecodeError) as exc:
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self._send(400, body, "application/json")

    def log_message(self, fmt, *args):
        pass   # keep the terminal quiet


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"CodeForge is running at {url}   (press Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()