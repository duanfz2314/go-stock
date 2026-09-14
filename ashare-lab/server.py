from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ashare.client import DataError  # noqa: E402
from ashare.service import ResearchService  # noqa: E402

WEB_DIR = ROOT / "web"
SERVICE = ResearchService()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[ashare-lab] " + (fmt % args) + "\n")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handle_api(parsed.path, parse_qs(parsed.query))
            return
        if parsed.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def _handle_api(self, path: str, qs: dict) -> None:
        try:
            if path == "/api/health":
                self._json(200, {"ok": True, "app": "ashare-lab", "market": "A-share"})
                return
            if path == "/api/market":
                self._json(200, SERVICE.market_overview())
                return
            if path == "/api/search":
                q = (qs.get("q") or [""])[0]
                self._json(200, SERVICE.search(q))
                return
            if path.startswith("/api/stock/"):
                code = path.split("/api/stock/", 1)[-1]
                self._json(200, SERVICE.stock_research(code))
                return
            if path == "/api/screener":
                params = {k: (v[0] if v else "") for k, v in qs.items()}
                self._json(200, SERVICE.screener(params))
                return
            self._json(404, {"error": "unknown api"})
        except DataError as e:
            self._json(400, {"error": str(e)})
        except Exception as e:
            traceback.print_exc()
            self._json(500, {"error": f"server: {e}"})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8787"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"A股研究台 ashare-lab  http://127.0.0.1:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
