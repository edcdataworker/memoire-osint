"""Loopback-only UI, CSRF-protected commands and durable worker supervision."""

import hmac
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..common import atomic_json, lock, now, private_dir
from . import resilience, security, store
from .rights import audit
from .source import SECTIONS, parameters

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).with_name("static")


def default_config(state, corpus=None):
    workspace = ROOT.parent
    b2 = workspace / "02_Bloc_2_Architecture"
    if not b2.exists() and (workspace / "bloc2_architecture").exists():
        b2 = workspace / "bloc2_architecture"
    return {
        "state": str(Path(state).resolve()),
        "corpus": str(Path(corpus).resolve())
        if corpus
        else str(workspace / "00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json"),
        "tombstone_files": [
            str(b2 / ".state/erasures.json"),
            str(ROOT / ".state/erasures.json"),
        ],
        "b2_root": str(b2),
        "request_interval": 0.7,
        "max_pages": 250,
        "max_reject_rate": 0.2,
        "slow_article_seconds": 10,
    }


class Controller:
    def __init__(self, config):
        self.config, self.state = config, Path(config["state"])
        self.guard = threading.Lock()
        self.stop_server = threading.Event()
        self.active = None
        self.bridge_active = False
        self.security_status = security.check(self.state, config.get("require_encrypted", False))
        if not (self.state / "collection.sqlite").exists() and not (self.state / "mirror").exists():
            store.initialize(self.state)
        _, backend, _ = resilience.backend(self.state)
        if backend == "primary":
            store.initialize(self.state)
            store.bootstrap(self.state, config)
            from .rights import reapply

            reapply(self.state, config)
            security.minimize_audit(self.state)
            security.retention(self.state)
            resilience.compact(self.state)
            resilience.refresh(self.state)
        atomic_json(self.state / "config.json", config)
        self.last_backend = backend
        self.last_retention = time.monotonic()
        threading.Thread(target=self.watch_security, daemon=True).start()

    def watch_security(self):
        while not self.stop_server.wait(5):
            try:
                self.security_status = security.check(
                    self.state, self.config.get("require_encrypted", False)
                )
                if time.monotonic() - self.last_retention >= 86400:
                    try:
                        with lock(self.state, "collection-worker.lock"):
                            resilience.require_primary(self.state)
                            security.retention(self.state)
                            resilience.compact(self.state)
                            resilience.refresh(self.state)
                            self.last_retention = time.monotonic()
                    except (BlockingIOError, ValueError):
                        pass
            except (OSError, sqlite3.Error):
                self.security_status = {
                    "permissions_safe": False,
                    "encryption_required": True,
                    "encrypted_volume": False,
                }

    def start(self, params, resume=None):
        resilience.require_primary(self.state)
        with self.guard:
            if self.active:
                raise ValueError("Une collecte est déjà en cours.")
            if resume:
                current = store.job(self.state, resume)
                if current["status"] not in (
                    "paused",
                    "failed",
                    "retryable",
                    "quality_failed",
                    "recovering",
                ):
                    raise ValueError("Cette collecte ne peut pas être reprise.")
                key = resume
                with store.database(self.state) as db, db:
                    # Rejected units may be retried after the bounded failure was shown.
                    db.execute(
                        "UPDATE tasks SET status='pending',error=NULL WHERE job_id=? AND status='rejected'",
                        (key,),
                    )
                    db.execute("UPDATE jobs SET status='queued',attempts=0 WHERE job_id=?", (key,))
                (self.state / (key + ".stop")).unlink(missing_ok=True)
            else:
                key = store.new_job(self.state, params)
            self.active = key
            threading.Thread(target=self.supervise, args=(key,), daemon=True).start()
            return key

    def supervise(self, key):
        try:
            for attempt in range(3):
                if self.stop_server.is_set():
                    break
                with (self.state / "worker.log").open("a") as log:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "pipeline.collection.worker",
                            str(self.state / "config.json"),
                            key,
                        ],
                        cwd=ROOT,
                        stdout=log,
                        stderr=log,
                    )
                    store.emit(
                        self.state, key, "worker_spawned", pid=process.pid, attempt=attempt + 1
                    )
                    while process.poll() is None:
                        if self.stop_server.wait(0.2):
                            (self.state / (key + ".stop")).touch()
                    code = process.returncode
                if code == 0:
                    break
                store.emit(
                    self.state,
                    key,
                    "alert",
                    code="WORKER_EXIT",
                    exit_code=code,
                    attempt=attempt + 1,
                )
                if attempt == 2:
                    with store.database(self.state) as db, db:
                        db.execute(
                            "UPDATE jobs SET status='failed',error='RETRIES_EXHAUSTED' WHERE job_id=?",
                            (key,),
                        )
                else:
                    with store.database(self.state) as db, db:
                        db.execute("UPDATE jobs SET status='recovering' WHERE job_id=?", (key,))
                    if self.stop_server.wait(2**attempt):
                        break
        finally:
            with self.guard:
                self.active = None

    def recover(self):
        _, kind, _ = resilience.backend(self.state)
        if kind != "primary":
            return
        with store.database(self.state) as db, db:
            rows = db.execute(
                "SELECT job_id FROM jobs WHERE status IN ('queued','running','stopping','recovering') ORDER BY created"
            ).fetchall()
            for row in rows:
                db.execute("UPDATE jobs SET status='recovering' WHERE job_id=?", (row[0],))
        if rows:
            key = rows[0][0]
            # A persisted stop request takes precedence over automatic recovery.
            if (self.state / (key + ".stop")).exists():
                with store.database(self.state) as db, db:
                    db.execute("UPDATE jobs SET status='paused' WHERE job_id=?", (key,))
            else:
                self.start(None, resume=key)

    def stop(self, key):
        if key != self.active:
            raise ValueError("Cette collecte n’est pas active.")
        (self.state / (key + ".stop")).touch()
        with store.database(self.state) as db, db:
            db.execute(
                "UPDATE jobs SET status='stopping' WHERE job_id=? AND status IN ('running','queued','recovering')",
                (key,),
            )
        store.emit(self.state, key, "stop_requested")

    def snapshot(self):
        _, kind, mirror_at = resilience.backend(self.state)
        if kind != self.last_backend:
            security.incident(self.state, "CATALOG_INTEGRITY", backend=kind, contained=True)
            self.last_backend = kind
        if kind == "primary":
            previous = store.external_denied(self.state, self.config)
            with store.database(self.state) as db:
                applied = {r[0] for r in db.execute("SELECT article_id FROM denied")}
            if previous - applied:
                # Wait until worker releases its lock; until then all read paths filter
                # durable tombstones, so privacy does not depend on physical cleanup.
                try:
                    with lock(self.state, "collection-worker.lock"):
                        store.sync_denied(self.state, self.config)
                        resilience.compact(self.state)
                        resilience.refresh(self.state)
                except BlockingIOError:
                    pass
        with store.read_database(self.state) as db:
            keys = [
                r[0] for r in db.execute("SELECT job_id FROM jobs ORDER BY created DESC LIMIT 12")
            ]
            events = [
                {"at": r["at"], "job_id": r["job_id"], "kind": r["kind"], **json.loads(r["fields"])}
                for r in db.execute("SELECT * FROM events ORDER BY sequence DESC LIMIT 40")
            ]
            denied = store.external_denied(self.state, self.config)
            total = sum(r[0] not in denied for r in db.execute("SELECT article_id FROM heads"))
        incident_path = self.state / "security.json"
        if incident_path.exists():
            try:
                incident = json.loads(incident_path.read_text())
                events.append({"job_id": None, "kind": "security_incident", **incident})
                events.sort(key=lambda entry: entry["at"], reverse=True)
                events = events[:40]
            except (OSError, ValueError, KeyError):
                pass
        bridge = self.state / "bridge.json"
        return {
            "observed_at": now(),
            "articles": total,
            "active": self.active,
            "jobs": [store.job(self.state, k, readonly=True) for k in keys],
            "events": events,
            "bridge": json.loads(bridge.read_text()) if bridge.exists() else None,
            "backend": kind,
            "read_only": kind != "primary",
            "mirror_at": mirror_at,
            "security": self.security_status,
        }

    def ingest_b2(self, key):
        resilience.require_primary(self.state)
        current = store.job(self.state, key)
        if current["status"] != "complete":
            raise ValueError("Seule une collecte validée peut être importée dans B2.")
        with self.guard:
            if self.bridge_active:
                raise ValueError("Un import B2 est déjà en cours.")
            self.bridge_active = True
        threading.Thread(target=self.bridge, args=(key,), daemon=True).start()

    def bridge(self, key):
        result = {"status": "running", "job_id": key, "at": now()}
        atomic_json(self.state / "bridge.json", result)
        try:
            manifest = store.export(self.state, self.config, store.job(self.state, key)["params"])
            root = Path(self.config["b2_root"])
            if not (root / "docker-compose.yml").exists():
                raise ValueError("Architecture B2 absente de ce poste.")
            with (self.state / "b2_import.log").open("a") as log:
                migration = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        "postgres",
                        "psql",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-U",
                        "postgres",
                        "-d",
                        "osint",
                        "-f",
                        "/docker-entrypoint-initdb.d/02_revisions.sql",
                    ],
                    cwd=root,
                    stdout=log,
                    stderr=log,
                    timeout=30,
                )
                if migration.returncode:
                    raise OSError(
                        "Bases B2 indisponibles ou migration impossible ; consulter le journal local."
                    )
                prefix = [
                    "docker",
                    "compose",
                    "run",
                    "--rm",
                    "-T",
                    "--volume",
                    str(Path(manifest["json"]).parent) + ":/collection:ro",
                    "ops",
                ]
                # Docker uses the existing private secrets and networks, never browser credentials.
                run = subprocess.run(
                    prefix
                    + [
                        "python",
                        "-m",
                        "osint.cli",
                        "ingest",
                        "--file",
                        "/collection/articles.json",
                    ],
                    cwd=root,
                    stdout=log,
                    stderr=log,
                    timeout=600,
                )
                if run.returncode:
                    raise OSError("Ingestion B2 échouée ; consulter le journal local.")
                run = subprocess.run(
                    prefix + ["python", "-m", "osint.cli", "index"],
                    cwd=root,
                    stdout=log,
                    stderr=log,
                    timeout=600,
                )
                if run.returncode:
                    raise OSError("Articles importés, indexation B2 à reprendre.")
            result.update(
                status="complete", articles=manifest["articles"], export_id=manifest["export_id"]
            )
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            result.update(status="failed", error=str(exc))
        finally:
            atomic_json(self.state / "bridge.json", result)
            store.emit(
                self.state,
                key,
                "b2_import_result",
                **{k: v for k, v in result.items() if k != "job_id"},
            )
            self.bridge_active = False


def serve(config, port=18743, open_browser=False):
    if config.get("require_encrypted") and not security.encrypted_volume(config["state"]):
        raise OSError("Déverrouiller le volume chiffré avant d’ouvrir l’Observatoire.")
    os.umask(0o077)
    private_dir(config["state"])
    with lock(config["state"], "collection-server.lock"):
        controller = Controller(config)
        csrf = secrets.token_urlsafe(32)
        hostnames = {f"127.0.0.1:{port}", f"localhost:{port}"}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def send(self, code, data, mime="application/json; charset=utf-8", download=None):
                if not isinstance(data, bytes):
                    data = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'",
                )
                if download:
                    self.send_header("Content-Disposition", f'attachment; filename="{download}"')
                self.end_headers()
                self.wfile.write(data)

            def allowed(self, mutation=False):
                host = self.headers.get("Host", "")
                if host not in hostnames:
                    audit(
                        controller.state,
                        "http_refused",
                        result="denied",
                        reason="HOST",
                        method=self.command,
                    )
                    self.send(403, {"error": "Accès local requis."})
                    return False
                if mutation and (
                    self.headers.get("Origin", "http://" + host) != "http://" + host
                    or not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), csrf)
                ):
                    audit(
                        controller.state,
                        "http_refused",
                        result="denied",
                        reason="SESSION",
                        method=self.command,
                    )
                    self.send(403, {"error": "Commande refusée : origine ou session invalide."})
                    return False
                return True

            def do_GET(self):
                if not self.allowed():
                    return
                try:
                    parsed = urlparse(self.path)
                    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                    if parsed.path in ("/", "/app.js", "/style.css"):
                        name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[
                            parsed.path
                        ]
                        mime = {
                            "index.html": "text/html",
                            "app.js": "text/javascript",
                            "style.css": "text/css",
                        }[name]
                        return self.send(
                            200, (STATIC / name).read_bytes(), mime + "; charset=utf-8"
                        )
                    if parsed.path == "/api/config":
                        return self.send(
                            200, {"csrf": csrf, "sections": SECTIONS, "timezone": "UTC"}
                        )
                    if parsed.path == "/api/status":
                        return self.send(200, controller.snapshot())
                    if parsed.path in ("/api/corpus", "/api/export"):
                        params = parameters({**query, "limit": 50})
                        if parsed.path == "/api/corpus":
                            offset = int(query.get("offset", 0))
                            if offset < 0:
                                raise ValueError("Position invalide.")
                            result = store.corpus(controller.state, params, offset)
                            audit(
                                controller.state,
                                "corpus_access",
                                result_count=len(result["articles"]),
                            )
                            return self.send(200, result)
                        kind = query.get("kind", "json")
                        if kind not in ("json", "jsonl"):
                            raise ValueError("Format invalide.")
                        manifest = store.export(controller.state, config, params)
                        audit(
                            controller.state,
                            "export_access",
                            export_id=manifest["export_id"],
                            result_count=manifest["articles"],
                            format=kind,
                        )
                        return self.send(
                            200,
                            Path(manifest[kind]).read_bytes(),
                            "application/json" if kind == "json" else "application/x-ndjson",
                            "tass-articles." + kind,
                        )
                    if parsed.path == "/api/article":
                        with store.read_database(controller.state) as db:
                            rows = db.execute(
                                "SELECT payload,collected FROM revisions WHERE article_id=? AND article_id NOT IN (SELECT article_id FROM denied) ORDER BY collected DESC",
                                (query.get("id", ""),),
                            ).fetchall()
                        identifier = query.get("id", "")
                        values = (
                            []
                            if identifier in store.external_denied(controller.state, config)
                            else list(
                                store.visible_rows(
                                    controller.state, (json.loads(r[0]) for r in rows)
                                )
                            )
                        )
                        audit(
                            controller.state,
                            "article_access",
                            article_id=identifier,
                            result_count=len(values),
                        )
                        return self.send(200, {"revisions": values})
                    self.send(404, {"error": "Page introuvable."})
                except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
                    audit(
                        controller.state,
                        "http_failed",
                        result="failed",
                        method="GET",
                        error_type=type(exc).__name__,
                    )
                    self.send(400, {"error": str(exc)})

            def do_POST(self):
                if not self.allowed(True):
                    return
                try:
                    resilience.require_primary(controller.state)
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 4096:
                        raise ValueError("Commande trop volumineuse ou vide.")
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError("Commande JSON invalide.")
                    if self.path == "/api/start":
                        return self.send(202, {"job_id": controller.start(parameters(data))})
                    key = str(uuid.UUID(data.get("job_id", "")))
                    if self.path == "/api/stop":
                        controller.stop(key)
                    elif self.path == "/api/resume":
                        controller.start(None, resume=key)
                    elif self.path == "/api/ingest-b2":
                        controller.ingest_b2(key)
                    else:
                        return self.send(404, {"error": "Commande introuvable."})
                    self.send(202, {"job_id": key})
                except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
                    audit(
                        controller.state,
                        "http_failed",
                        result="failed",
                        method="POST",
                        error_type=type(exc).__name__,
                    )
                    self.send(400, {"error": str(exc)})

        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        controller.recover()
        print(f"Application TASS : http://127.0.0.1:{port}", flush=True)
        if open_browser:
            import webbrowser

            threading.Timer(0.5, webbrowser.open, args=(f"http://127.0.0.1:{port}",)).start()
        try:
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
        finally:
            controller.stop_server.set()
            server.server_close()
