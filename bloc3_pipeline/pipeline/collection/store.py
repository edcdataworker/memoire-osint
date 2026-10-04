"""Durable job queue, immutable revisions and atomic compatible exports."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..common import actor_identity, atomic_bytes, atomic_json, event, now, private_dir, sha256
from ..source import records
from ..transform import normalize
from .source import bounds


@contextmanager
def database(state):
    db = sqlite3.connect(Path(state) / "collection.sqlite", timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA secure_delete=ON")
    try:
        yield db
    finally:
        db.close()


def initialize(state):
    private_dir(state)
    with database(state) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS revisions (
          article_id TEXT NOT NULL, revision TEXT NOT NULL, published INTEGER NOT NULL,
          section TEXT NOT NULL, payload TEXT NOT NULL, collected TEXT NOT NULL,
          PRIMARY KEY(article_id, revision)
        );
        CREATE TABLE IF NOT EXISTS heads (
          article_id TEXT PRIMARY KEY, revision TEXT NOT NULL,
          FOREIGN KEY(article_id, revision) REFERENCES revisions(article_id, revision)
        );
        CREATE INDEX IF NOT EXISTS revisions_date ON revisions(published,section);
        CREATE TABLE IF NOT EXISTS jobs (
          job_id TEXT PRIMARY KEY, params TEXT NOT NULL, status TEXT NOT NULL,
          stage TEXT NOT NULL, cursor INTEGER NOT NULL, pages INTEGER NOT NULL DEFAULT 0,
          section_id INTEGER, coverage TEXT NOT NULL DEFAULT 'pending',
          created TEXT NOT NULL, updated TEXT NOT NULL, work_s REAL NOT NULL DEFAULT 0,
          attempts INTEGER NOT NULL DEFAULT 0, error TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
          job_id TEXT NOT NULL REFERENCES jobs(job_id), url TEXT NOT NULL,
          article_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          payload TEXT, error TEXT, PRIMARY KEY(job_id,url), UNIQUE(job_id,article_id)
        );
        -- Within a fixed job/status, SQLite's index also orders by rowid. Avoid
        -- sorting every remaining task for each downloaded article.
        CREATE INDEX IF NOT EXISTS tasks_pending ON tasks(job_id,status);
        -- Rights apply across every job. This lookup also runs before each
        -- download, so a full task-table scan would grow with the batch size.
        CREATE INDEX IF NOT EXISTS tasks_article ON tasks(article_id);
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
          job_id TEXT, kind TEXT NOT NULL, fields TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS denied (article_id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS corrections (article_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        """)
        if "started_at" not in {r[1] for r in db.execute("PRAGMA table_info(jobs)")}:
            db.execute("ALTER TABLE jobs ADD COLUMN started_at TEXT")
        if "downloaded" not in {r[1] for r in db.execute("PRAGMA table_info(tasks)")}:
            db.execute("ALTER TABLE tasks ADD COLUMN downloaded INTEGER NOT NULL DEFAULT 0")
            db.execute(
                "UPDATE tasks SET downloaded=1 WHERE payload IS NOT NULL OR status='filtered'"
            )
        db.commit()


def emit(state, job_id, kind, **fields):
    if "keywords" in fields:
        fields["keyword_count"] = len(fields.pop("keywords"))
    fields.setdefault("actor", actor_identity())
    with database(state) as db, db:
        db.execute(
            "INSERT INTO events(at,job_id,kind,fields) VALUES(?,?,?,?)",
            (now(), job_id, kind, json.dumps(fields, ensure_ascii=False)),
        )
        if job_id:
            db.execute("UPDATE jobs SET updated=? WHERE job_id=?", (now(), job_id))
    event(state, kind, job_id=job_id, **fields)


@contextmanager
def read_database(state):
    from .resilience import backend

    path, _, _ = backend(state)
    db = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


def external_denied(state, config=None):
    """Read durable ledgers also in fallback mode, without mutating the mirror."""
    if config is None:
        saved = Path(state) / "config.json"
        config = json.loads(saved.read_text()) if saved.exists() else {}
    paths = config.get("tombstone_files", [])
    values = set()
    for path in paths:
        if Path(path).exists():
            data = json.loads(Path(path).read_text())
            if not isinstance(data, list):
                raise ValueError("Registre de suppressions invalide.")
            values.update(str(v) for v in data)
    rights = Path(state) / "rights.json"
    if rights.exists():
        values.update(json.loads(rights.read_text()).get("erased", []))
    return values


def sync_denied(state, config):
    identifiers = external_denied(state, config)
    for path in config.get("tombstone_files", []):
        if Path(path).exists():
            values = json.loads(Path(path).read_text())
            if not isinstance(values, list) or any(type(v) not in (str, int) for v in values):
                raise ValueError("Registre de suppressions invalide.")
            identifiers.update(str(v) for v in values)
    with database(state) as db, db:
        previous = {row[0] for row in db.execute("SELECT article_id FROM denied")}
        identifiers.update(previous)
        for key in identifiers:
            db.execute("INSERT OR IGNORE INTO denied VALUES(?)", (key,))
            db.execute("DELETE FROM heads WHERE article_id=?", (key,))
            db.execute("DELETE FROM revisions WHERE article_id=?", (key,))
            db.execute("DELETE FROM corrections WHERE article_id=?", (key,))
            db.execute(
                "UPDATE tasks SET status='suppressed',payload=NULL WHERE article_id=?", (key,)
            )
        if identifiers - previous:
            # Erasure is an explicit exception to immutable exports. Copies downloaded
            # outside this managed directory remain part of the coordinated procedure.
            for manifest_path in (Path(state) / "exports").glob("*/manifest.json"):
                manifest = json.loads(manifest_path.read_text())
                path = manifest_path.parent / "articles.json"
                rows = [row for _, row in records(path) if str(row["id"]) not in identifiers]
                if len(rows) == manifest["articles"]:
                    continue
                atomic_json(path, rows)
                lines = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
                atomic_bytes(manifest_path.parent / "articles.jsonl", lines.encode())
                manifest.update(
                    articles=len(rows),
                    erasure_applied_at=now(),
                    sha256={
                        kind: sha256(manifest_path.parent / ("articles." + kind))
                        for kind in ("json", "jsonl")
                    },
                )
                atomic_json(manifest_path, manifest)
                pointer = Path(state) / "current.json"
                if (
                    pointer.exists()
                    and json.loads(pointer.read_text())["export_id"] == manifest["export_id"]
                ):
                    atomic_json(pointer, manifest)
    return identifiers


def revision(row):
    core = {k: row[k] for k in ("id", "date", "title", "url", "text")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def put(db, row):
    key, checksum = str(row["id"]), revision(row)
    correction = db.execute("SELECT payload FROM corrections WHERE article_id=?", (key,)).fetchone()
    if correction:
        row = json.loads(correction[0])
        checksum = revision(row)
    existing = db.execute("SELECT revision FROM heads WHERE article_id=?", (key,)).fetchone()
    if existing and existing[0] == checksum:
        return "unchanged"
    payload = {**row, "revision_sha256": checksum}
    section = row["url"].split("/")[3]
    db.execute(
        "INSERT OR IGNORE INTO revisions VALUES(?,?,?,?,?,?)",
        (key, checksum, row["date"], section, json.dumps(payload, ensure_ascii=False), now()),
    )
    db.execute(
        "INSERT INTO heads VALUES(?,?) ON CONFLICT(article_id) DO UPDATE SET revision=excluded.revision",
        (key, checksum),
    )
    return "updated" if existing else "new"


def bootstrap(state, config):
    source = config.get("corpus")
    if not source or not Path(source).exists():
        return 0
    fingerprint = sha256(source)
    denied = sync_denied(state, config)
    with database(state) as db:
        previous = db.execute("SELECT value FROM meta WHERE key='bootstrap_sha' ").fetchone()
        if previous:
            if previous[0] != fingerprint:
                raise ValueError(
                    "Le corpus initial a changé ; utiliser un nouvel état de collecte."
                )
            return 0
        count = 0
        with db:
            for index, item in records(Path(source)):
                row = normalize(item, fingerprint, index, "historical-bootstrap", "clean")
                if str(row["id"]) not in denied:
                    put(db, row)
                    count += 1
            db.execute("INSERT INTO meta VALUES('bootstrap_sha',?)", (fingerprint,))
    emit(state, None, "historical_import", articles=count, source_sha256=fingerprint)
    return count


def new_job(state, params):
    key = str(uuid.uuid4())
    _, right = bounds(params["start"], params["end"])
    with database(state) as db, db:
        if db.execute(
            "SELECT 1 FROM jobs WHERE status IN ('queued','running','stopping','recovering')"
        ).fetchone():
            raise ValueError("Une collecte est déjà en cours.")
        db.execute(
            "INSERT INTO jobs(job_id,params,status,stage,cursor,created,updated) VALUES(?,?,?,?,?,?,?)",
            (key, json.dumps(params), "queued", "discovery", right, now(), now()),
        )
    emit(state, key, "collection_queued", **params)
    return key


def job(state, key, readonly=False):
    with read_database(state) if readonly else database(state) as db:
        row = db.execute("SELECT * FROM jobs WHERE job_id=?", (key,)).fetchone()
        if not row:
            raise ValueError("Collecte introuvable.")
        data = dict(row)
        if data["started_at"] and data["status"] in ("running", "stopping"):
            data["work_s"] += max(
                0,
                (
                    datetime.now(timezone.utc) - datetime.fromisoformat(data["started_at"])
                ).total_seconds(),
            )
        data["params"] = json.loads(data["params"])
        data["counts"] = dict(
            db.execute("SELECT status,count(*) FROM tasks WHERE job_id=? GROUP BY status", (key,))
        )
        data["discovered"] = sum(data["counts"].values())
        data["processed"] = data["discovered"] - data["counts"].get("pending", 0)
        data["downloaded"] = db.execute(
            "SELECT count(*) FROM tasks WHERE job_id=? AND downloaded=1", (key,)
        ).fetchone()[0]
        data["validated"] = sum(
            data["counts"].get(kind, 0) for kind in ("new", "updated", "unchanged")
        )
        data["revision_count"] = db.execute("SELECT count(*) FROM revisions").fetchone()[0]
        return data


def visible_rows(state, rows):
    from .rights import ledger

    decisions = ledger(state)
    denied = external_denied(state)
    replaced = set()
    for row in rows:
        key = str(row["id"])
        if key in denied:
            continue
        if key in decisions["corrections"]:
            if key in replaced:
                continue
            row = decisions["corrections"][key]["row"]
            row = {**row, "revision_sha256": revision(row)}
            replaced.add(key)
        yield row


def selected(db, params, denied=(), state=None):
    left, right = bounds(params["start"], params["end"])
    query = """SELECT r.payload FROM heads h JOIN revisions r
       ON h.article_id=r.article_id AND h.revision=r.revision
       WHERE r.published>=? AND r.published<? AND r.section=?
       AND h.article_id NOT IN (SELECT article_id FROM denied)
       ORDER BY r.published DESC, h.article_id"""
    rows = (json.loads(item[0]) for item in db.execute(query, (left, right, params["section"])))
    for row in visible_rows(state, rows) if state else rows:
        if str(row["id"]) in denied:
            continue
        if not params["keywords"] or any(
            k in (row["title"] + " " + row["text"]).casefold() for k in params["keywords"]
        ):
            yield row


def corpus(state, params, offset=0, page_size=30):
    with read_database(state) as db:
        count, page = 0, []
        for row in selected(db, params, external_denied(state), state):
            if offset <= count < offset + page_size:
                page.append(
                    {k: row[k] for k in ("id", "date_readable", "title", "url", "revision_sha256")}
                )
            count += 1
    return {"total": count, "offset": offset, "articles": page}


def export(state, config, params, name=None):
    from .resilience import backend

    _, kind, _ = backend(state)
    if kind == "primary":
        sync_denied(state, config)
    key = name or str(uuid.uuid4())
    root = private_dir(Path(state) / "exports" / key)
    hashes = {}
    with read_database(state) as db:
        db.execute("BEGIN")  # Both formats come from exactly the same database snapshot.
        for suffix in ("json", "jsonl"):
            path = root / ("articles." + suffix)
            temp = root / ("articles." + suffix + ".tmp")
            with temp.open("w", encoding="utf-8") as stream:
                import os

                if suffix == "json":
                    stream.write("[\n")
                count = 0
                for row in selected(db, params, external_denied(state, config), state):
                    if suffix == "json" and count:
                        stream.write(",\n")
                    stream.write(
                        json.dumps(row, ensure_ascii=False) + ("\n" if suffix == "jsonl" else "")
                    )
                    count += 1
                if suffix == "json":
                    stream.write("\n]\n")
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(path)
            hashes[suffix] = sha256(path)
    manifest = {
        "export_id": key,
        "created_at": now(),
        "articles": count,
        "params": params,
        "sha256": hashes,
        "json": str((root / "articles.json").resolve()),
        "jsonl": str((root / "articles.jsonl").resolve()),
    }
    atomic_json(root / "manifest.json", manifest)
    return manifest
