"""Loopback consultation and bounded, non-persistent prediction API."""

import json
import os
import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import __version__
from .contracts import MAX_TEXT, article, read_records, validate_spans


def make_handler(data, run, predictor=None):
    rows = [article(r) for r in read_records(data)]
    by_id = {str(r["id"]): r for r in rows}
    metadata = json.loads((Path(run) / "training.json").read_text())
    for row in rows:
        validate_spans(row["text"], row["entities"])
        if (
            row.get("model_sha256") != metadata["model_sha256"]
            or row.get("model_version") != metadata["model_version"]
        ):
            raise ValueError("Inference and declared model identity mismatch")
    assets = Path(__file__).parent / "static"
    prediction_lock = threading.Lock()
    metrics_lock = threading.Lock()
    metrics = {
        "requests": 0,
        "successes": 0,
        "errors": 0,
        "busy": 0,
        "total_seconds": 0.0,
        "last_seconds": None,
        "last_characters": None,
    }

    def local_request(handler):
        host = handler.headers.get("Host", "")
        if host.split(":")[0] not in ("127.0.0.1", "localhost"):
            return False
        origin = handler.headers.get("Origin")
        return origin is None or origin in (f"http://{host}", f"https://{host}")

    def year_of(row):
        return (
            str(datetime.fromtimestamp(row["date"], timezone.utc).year)
            if row.get("date") is not None
            else "inconnue"
        )

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def send(self, code, body, kind="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not local_request(self):
                return self.send(403, {"error": "Local host required"})
            if len(self.path) > 4096:
                return self.send(414, {"error": "Request too long"})
            parsed = urlparse(self.path)
            args = parse_qs(parsed.query)
            if parsed.path == "/health":
                return self.send(
                    200,
                    {
                        "status": "ok",
                        "version": __version__,
                        "quality_status": metadata["quality_status"],
                        "release_token": os.environ.get("OSINT_RELEASE_TOKEN"),
                        "documents": len(rows),
                        "model_version": metadata["model_version"],
                        "model_sha256": metadata["model_sha256"],
                        "prediction_ready": predictor is not None,
                    },
                )
            if parsed.path == "/api/metrics":
                with metrics_lock:
                    snapshot = dict(metrics)
                return self.send(
                    200,
                    {
                        "prediction": snapshot,
                        "scope": "current_process_no_source_text",
                        "model_sha256": metadata["model_sha256"],
                    },
                )
            if parsed.path in ("/", "/app.js", "/style.css"):
                name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[
                    parsed.path
                ]
                kind = {
                    "index.html": "text/html; charset=utf-8",
                    "app.js": "text/javascript; charset=utf-8",
                    "style.css": "text/css; charset=utf-8",
                }[name]
                return self.send(200, (assets / name).read_bytes(), kind)
            if parsed.path == "/api/article":
                row = by_id.get(args.get("id", [""])[0])
                return (
                    self.send(200, row) if row else self.send(404, {"error": "Article not found"})
                )
            if parsed.path == "/api/summary":
                year = args.get("year", [""])[0]
                query = args.get("q", [""])[0].casefold()[:200]
                label = args.get("label", [""])[0]
                subset = [r for r in rows if not year or year_of(r) == year]
                if query:
                    subset = [
                        r
                        for r in subset
                        if query in r["text"].casefold() or query in r.get("title", "").casefold()
                    ]
                entities = [
                    e for r in subset for e in r["entities"] if not label or e["label"] == label
                ]
                return self.send(
                    200,
                    {
                        "total_documents": len(rows),
                        "documents": len(subset),
                        "articles_with_entities": sum(bool(r["entities"]) for r in subset),
                        "mentions": len(entities),
                        "counts": dict(Counter(e["label"] for e in entities)),
                        "top": Counter(
                            (e["label"] + ": " + e["text"]) for e in entities
                        ).most_common(10),
                        "years": sorted({year_of(r) for r in rows}),
                        "by_year": dict(Counter(year_of(r) for r in subset)),
                        "articles": [
                            {k: r.get(k) for k in ("id", "title", "url", "date")}
                            for r in subset[:80]
                        ],
                        "model": {
                            k: metadata[k]
                            for k in (
                                "model_version",
                                "model_sha256",
                                "quality_metrics",
                                "quality_status",
                            )
                        },
                    },
                )
            return self.send(404, {"error": "Route not found"})

        def do_POST(self):
            if not local_request(self):
                return self.send(403, {"error": "Local same-origin request required"})
            if self.path != "/api/predict":
                return self.send(405, {"error": "Only /api/predict accepts POST"})
            with metrics_lock:
                metrics["requests"] += 1

            def reject(code, message):
                with metrics_lock:
                    metrics["errors"] += 1
                return self.send(code, {"error": message})

            if self.headers.get_content_type() != "application/json":
                return reject(415, "Content-Type application/json required")
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                return reject(400, "A single Content-Length is required")
            try:
                length = int(lengths[0])
            except ValueError:
                return reject(400, "Invalid Content-Length")
            if not 0 < length <= MAX_TEXT * 4 + 4096:
                return reject(413, "Request body too large or empty")
            try:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return reject(400, "Incomplete request body")
                value = json.loads(raw)
                if not isinstance(value, dict) or set(value) - {"text"}:
                    return reject(400, "Expected an object with only the text field")
                row = article(
                    {
                        "id": uuid.uuid4().hex,
                        "text": value.get("text"),
                        "url": "https://example.invalid/manual-input",
                    }
                )
            except (ValueError, UnicodeError, TimeoutError):
                return reject(400, "Invalid JSON or text; use 1 to 100000 Unicode characters")
            if predictor is None:
                return reject(503, "Prediction model unavailable")
            if not prediction_lock.acquire(blocking=False):
                with metrics_lock:
                    metrics["busy"] += 1
                return reject(429, "Prediction busy; retry later")
            started = time.perf_counter()
            try:
                result = next(iter(predictor.predict([row])))
                duration = round(time.perf_counter() - started, 6)
                with metrics_lock:
                    metrics["successes"] += 1
                    metrics["total_seconds"] += duration
                    metrics["last_seconds"] = duration
                    metrics["last_characters"] = len(row["text"])
                return self.send(
                    200,
                    {
                        **result,
                        "duration_seconds": duration,
                        "quality_status": metadata["quality_status"],
                        "retention": "not_persisted",
                    },
                )
            except Exception:
                return reject(503, "Prediction failed; no input text was logged")
            finally:
                prediction_lock.release()

        def log_message(self, format, *args):
            # No source text, URL parameters or article identifiers in operational logs.
            pass

    return Handler


def serve(data, run, port, host="127.0.0.1"):
    from .model import Predictor

    server = ThreadingHTTPServer((host, port), make_handler(data, run, Predictor(run)))
    server.timeout = 5
    print(json.dumps({"event": "server_started", "host": host, "port": port}), flush=True)
    server.serve_forever()
