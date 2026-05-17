import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ament_index_python.packages import get_package_share_directory


class ObjectHuntWebServer:
    def __init__(self, api, host, port, logger=None):
        self.api = api
        self.host = host
        self.port = port
        self.logger = logger
        self.server = None

    def start(self):
        handler = self._make_handler()
        try:
            self.server = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError as exc:
            self._log(
                "error",
                f"Could not start Object Hunt Web UI on {self.host}:{self.port}: {exc}",
            )
            return None

        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self._log("info", f"Object Hunt Web UI: http://{self.host}:{self.port}/")
        return self

    def shutdown(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

    def _make_handler(self):
        api = self.api
        logger = self.logger

        class ObjectHuntHandler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                if logger is not None:
                    logger.debug(fmt % args)

            def do_OPTIONS(self):
                self._send_empty(204)

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/":
                    self._send_html(load_web_index())
                elif parsed.path == "/api/classes":
                    self._send_json({"classes": api.get_track_classes()})
                elif parsed.path == "/api/locations":
                    class_name = parse_qs(parsed.query).get("class", [""])[0]
                    self._send_json({"locations": api.get_locations(class_name)})
                elif parsed.path == "/api/status":
                    self._send_json(api.get_nav_status())
                else:
                    self._send_json({"error": "not found"}, 404)

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path == "/api/navigate":
                    payload = self._read_payload()
                    try:
                        track_id = int(payload.get("track_id"))
                    except (TypeError, ValueError):
                        self._send_json({"error": "track_id is required"}, 400)
                        return
                    ok, message = api.navigate_to_track(track_id)
                    self._send_json({"ok": ok, "message": message}, 200 if ok else 409)
                elif parsed.path == "/api/clear":
                    api.clear_tracks()
                    self._send_json({"ok": True})
                else:
                    self._send_json({"error": "not found"}, 404)

            def _read_payload(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw_body = self.rfile.read(length).decode("utf-8") if length else ""
                if not raw_body:
                    return {}
                try:
                    return json.loads(raw_body)
                except json.JSONDecodeError:
                    return {k: v[0] for k, v in parse_qs(raw_body).items()}

            def _send_empty(self, status):
                self.send_response(status)
                self._cors_headers()
                self.end_headers()

            def _send_json(self, payload, status=200):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, body):
                encoded = body.encode("utf-8")
                self.send_response(200)
                self._cors_headers()
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _cors_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

        return ObjectHuntHandler

    def _log(self, level, message):
        if self.logger is not None:
            getattr(self.logger, level)(message)


def load_web_index():
    candidates = []
    try:
        candidates.append(
            Path(get_package_share_directory("object_detector")) / "web" / "index.html"
        )
    except Exception:
        pass
    candidates.append(Path(__file__).resolve().parents[1] / "web" / "index.html")

    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "<!doctype html><title>Object Hunt</title><p>Web UI asset not found.</p>"
