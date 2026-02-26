"""
rater_server.py
---------------
Persistent HTTP server for the shader rating UI.
One tab stays open the whole session; new shaders push in via SSE.

Usage:
    server = RaterServer()
    server.start()          # opens browser once, returns immediately
    server.push(shader_id, shader_src)   # sends shader to open tab
    rating = server.wait_for_rating()    # blocks until user rates
    server.stop()
"""

import json
import queue
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
RATE_TEMPLATE = TEMPLATES_DIR / "shadertoy_rate.html"

_SSE_CLIENTS: list = []
_SSE_LOCK = threading.Lock()
_LAST_SHADER: dict | None = None


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _make_handler(rating_queue: queue.Queue, html: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == "/events":
                self._sse()
            else:
                body = html.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def _sse(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q: queue.Queue = queue.Queue()
            with _SSE_LOCK:
                # Replay last shader immediately if one exists
                if _LAST_SHADER is not None:
                    q.put(_LAST_SHADER)
                _SSE_CLIENTS.append(q)
            try:
                while True:
                    try:
                        data = q.get(timeout=15)
                        msg = f"data: {json.dumps(data)}\n\n"
                        self.wfile.write(msg.encode())
                        self.wfile.flush()
                    except queue.Empty:
                        # keepalive comment
                        self.wfile.write(b": ka\n\n")
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                with _SSE_LOCK:
                    _SSE_CLIENTS.remove(q)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            if self.path == "/rate":
                self.wfile.write(b'{"ok":true}')
                rating_queue.put(data)
            elif self.path == "/push":
                # External push: inject a new shader from another process
                global _LAST_SHADER
                payload = {"shader_id": data["shader_id"], "glsl": data["glsl"]}
                with _SSE_LOCK:
                    _LAST_SHADER = payload
                    for q in _SSE_CLIENTS:
                        q.put(payload)
                self.wfile.write(b'{"ok":true}')
            else:
                self.wfile.write(b'{"error":"unknown path"}')

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    return Handler


def _find_port(start: int = 7749) -> int:
    import socket
    for p in range(start, start + 20):
        try:
            s = socket.socket()
            s.bind(("", p))
            s.close()
            return p
        except OSError:
            continue
    return start


class RaterServer:
    def __init__(self):
        self.port = _find_port()
        self.rating_queue: queue.Queue = queue.Queue()
        self._server = None
        self._thread = None

    def start(self):
        html = RATE_TEMPLATE.read_text().replace("location.port", f'"{self.port}"')
        handler = _make_handler(self.rating_queue, html)
        self._server = _ThreadingHTTPServer(("", self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        url = f"http://localhost:{self.port}"
        print(f"  [rater] {url}  (keep this tab open)")
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", url])
        except Exception:
            print(f"  Open manually: {url}")

    def push(self, shader_id: str, shader_src: str):
        """Send a new shader to all connected browser tabs."""
        global _LAST_SHADER
        payload = {"shader_id": shader_id, "glsl": shader_src}
        with _SSE_LOCK:
            _LAST_SHADER = payload
            for q in _SSE_CLIENTS:
                q.put(payload)

    def wait_for_rating(self) -> dict:
        """Block until the user submits a rating. Returns {score, note, discard}."""
        return self.rating_queue.get()

    def stop(self):
        if self._server:
            self._server.shutdown()
