"""Read-only local UI. No remote bind, template evaluation or arbitrary file route."""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from . import __version__
from .contracts import article, read_records, validate_spans


def make_handler(data, run):
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

    def year_of(row):
        return (
            str(datetime.fromtimestamp(row["date"], timezone.utc).year)
            if row.get("date") is not None
            else "inconnue"
        )

    class Handler(BaseHTTPRequestHandler):
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
            if self.headers.get("Host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
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
            self.send(405, {"error": "Read-only service"})

        def log_message(self, format, *args):
            # No source text, URL parameters or article identifiers in operational logs.
            pass

    return Handler


def serve(data, run, port):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(data, run))
    server.timeout = 5
    print(json.dumps({"event": "server_started", "host": "127.0.0.1", "port": port}), flush=True)
    server.serve_forever()
