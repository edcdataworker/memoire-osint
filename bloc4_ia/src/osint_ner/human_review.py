"""Local, explicit human review. Synthetic tests never certify real articles."""

import argparse
import json
import os
import plistlib
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .contracts import (
    article,
    atomic_json,
    file_sha,
    read_records,
    utcnow,
    validate_spans,
    write_records,
)


class ReviewStore:
    def __init__(self, reference, manifest, directory, run):
        self.reference = Path(reference)
        self.manifest = Path(manifest)
        self.directory = Path(directory)
        self.run = Path(run)
        self.source_hash = file_sha(reference)
        self.original = [article(r) for r in read_records(reference)]
        if len({str(r["id"]) for r in self.original}) != len(self.original):
            raise ValueError("Duplicate article identifiers in review reference")
        frozen = {str(r["id"]): r for r in read_records(manifest)}
        for row in self.original:
            m = frozen.get(str(row["id"]))
            if (
                not m
                or m.get("split") != "test"
                or m.get("text_sha256") != row["text_sha256"]
                or m.get("group_id") != row.get("group_id")
            ):
                raise ValueError("Review source is outside the frozen held-out test")
            validate_spans(row["text"], row["entities"])
        self.by_id = {str(r["id"]): r for r in self.original}
        self.path = self.directory / "progression.json"
        self.lock = threading.RLock()
        self.saved = {}
        if self.path.exists():
            state = json.loads(self.path.read_text())
            if state.get("source_sha256") != self.source_hash:
                raise ValueError("Reference changed: start a new review directory")
            self.saved = state["articles"]
            for key, row in self.saved.items():
                if (
                    key not in self.by_id
                    or row.get("text_sha256") != self.by_id[key]["text_sha256"]
                ):
                    raise ValueError("Saved review does not match reference")
                validate_spans(self.by_id[key]["text"], row["entities"])

    def snapshot(self):
        with self.lock:
            rows = [{**r, **self.saved.get(str(r["id"]), {})} for r in self.original]
            return {
                "articles": rows,
                "reviewed": sum(r.get("annotation_status") == "human_reviewed" for r in rows),
                "total": len(rows),
                "source_sha256": self.source_hash,
            }

    def save(self, data):
        with self.lock:
            original = self.by_id.get(str(data.get("id")))
            if not original or data.get("text_sha256") != original["text_sha256"]:
                raise ValueError("Article identity mismatch")
            if not isinstance(data.get("entities"), list):
                raise ValueError("Annotations must be a list")
            spans = validate_spans(original["text"], data["entities"])
            reviewer = data.get("reviewer", "")
            note = data.get("review_note", "")
            if (
                not isinstance(reviewer, str)
                or not isinstance(note, str)
                or len(reviewer) > 120
                or len(note) > 4000
            ):
                raise ValueError("Invalid reviewer or note")
            attested = data.get("attest") is True
            if attested and not reviewer.strip():
                raise ValueError("Human reviewer name is required")
            # Every draft save invalidates any previous attestation, even when spans match.
            row = {
                **original,
                "entities": spans,
                "review_note": note,
                "annotation_status": "human_reviewed" if attested else "human_review_draft",
                "reviewer": reviewer.strip() if attested else None,
                "reviewed_at": utcnow() if attested else None,
                "review_method": "Full source read and spans corrected by named human"
                if attested
                else None,
                "review_source_sha256": self.source_hash,
            }
            self.saved[str(original["id"])] = row
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            atomic_json(
                self.path,
                {"source_sha256": self.source_hash, "at": utcnow(), "articles": self.saved},
            )
            os.chmod(self.path, 0o600)
            self.export()
            return self.snapshot()

    def export(self):
        rows = self.snapshot()["articles"]
        reviewed = [r for r in rows if r.get("annotation_status") == "human_reviewed"]
        path = self.directory / "reference_humaine.jsonl"
        write_records(path, reviewed)
        os.chmod(path, 0o600)
        return path

    def evaluate(self):
        with self.lock:
            state = self.snapshot()
            if state["reviewed"] != state["total"]:
                raise ValueError(
                    f"Revue incomplète : {state['reviewed']} / {state['total']} articles. Aucun score humain calculé."
                )
            from .model import evaluate

            reference = self.export()
            result = evaluate(self.run, reference, self.manifest)
            result["review_source_sha256"] = self.source_hash
            result["at"] = utcnow()
            result["review_provenance"] = (
                "Explicit declarations recorded through local human-review interface"
            )
            result["limitation"] = (
                "42-article assisted, stratified sample; reviewer declarations, no independent second adjudication; not a production-quality estimate"
            )
            path = self.directory / "evaluation_humaine.json"
            atomic_json(path, result)
            os.chmod(path, 0o600)
            return result


def make_handler(store, template, token):
    class Handler(BaseHTTPRequestHandler):
        def allowed_host(self):
            return self.headers.get("Host") in (
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            )

        def reply(self, code, body, kind="application/json; charset=utf-8"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            for key, value in {
                "Content-Type": kind,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            }.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.allowed_host():
                return self.reply(403, {"error": "Host local requis"})
            if self.path == "/":
                return self.reply(200, template.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/app.js":
                return self.reply(
                    200, template.with_suffix(".js").read_bytes(), "text/javascript; charset=utf-8"
                )
            if self.path == "/api/state":
                return self.reply(200, {**store.snapshot(), "csrf": token})
            return self.reply(404, {"error": "Route inconnue"})

        def do_POST(self):
            origin = self.headers.get("Origin")
            expected = f"http://{self.headers.get('Host')}"
            if (
                not self.allowed_host()
                or origin != expected
                or self.headers.get("X-Review-Token") != token
            ):
                return self.reply(403, {"error": "Origine locale et jeton requis"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 200_000:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("An object is required")
                if self.path == "/api/save":
                    return self.reply(200, store.save(data))
                if self.path == "/api/evaluate":
                    return self.reply(200, store.evaluate())
                return self.reply(404, {"error": "Route inconnue"})
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                self.reply(400, {"error": str(exc)})
            except Exception:
                # Do not expose filesystem paths, corpus content or stack traces in HTTP.
                self.reply(
                    500,
                    {
                        "error": "Évaluation impossible ; vérifier le modèle et les fichiers du dossier privé."
                    },
                )

        def log_message(self, *_):
            pass

    return Handler


def main():
    p = argparse.ArgumentParser(description="Revue humaine locale des 42 articles réservés au test")
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--port", type=int, default=8767)
    p.add_argument("--encrypted-root", type=Path, required=True)
    a = p.parse_args()
    encrypted = a.encrypted_root.resolve(strict=True)
    # The launcher passes the previously verified encrypted mount, without fallback.
    images = plistlib.loads(
        subprocess.run(["hdiutil", "info", "-plist"], check=True, capture_output=True).stdout
    )["images"]
    mounted_encrypted = any(
        image.get("image-encrypted")
        and any(
            entity.get("mount-point") and Path(entity["mount-point"]).resolve() == encrypted
            for entity in image.get("system-entities", [])
        )
        for image in images
    )
    if not mounted_encrypted:
        raise SystemExit("Volume chiffré absent ; aucune progression en clair créée.")
    for path in (a.reference, a.manifest, a.run, a.directory):
        if not path.resolve().is_relative_to(encrypted):
            raise SystemExit(
                "Les textes, modèle et progression doivent rester sur le volume chiffré."
            )
    os.umask(0o077)
    store = ReviewStore(a.reference, a.manifest, a.directory, a.run)
    if len(store.original) != 42:
        raise SystemExit("Le parcours attend exactement les 42 articles figés.")
    template = Path(__file__).parent / "static/human_review.html"
    server = ThreadingHTTPServer(
        ("127.0.0.1", a.port), make_handler(store, template, secrets.token_urlsafe(32))
    )
    print(
        f"http://127.0.0.1:{a.port} · {store.snapshot()['reviewed']}/42 articles relus", flush=True
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
