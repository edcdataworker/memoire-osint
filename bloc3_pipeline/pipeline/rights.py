"""Local rights support and optional import of the Bloc 2 erasure register."""

import json
import shutil
from pathlib import Path

from .common import atomic_json, event, lock, now
from .publish import publish
from .state import connect


def access(state, article_id):
    with connect(state) as db:
        rows = [
            json.loads(row["payload"])
            for row in db.execute(
                "SELECT payload FROM articles WHERE article_id=?", (str(article_id),)
            )
        ]
    event(state, "rights_access", article_id=str(article_id), matches=len(rows))
    return rows


def apply_erasure(db, state, identifiers, request_ref):
    """Deny first, purge current/historical exports, then compact SQLite/WAL."""
    state = Path(state)
    atomic_json(state / "erasures_pending.json", list(identifiers))
    with db:
        for identifier in identifiers:
            db.execute(
                "INSERT OR REPLACE INTO tombstones VALUES(?,?,?)",
                (str(identifier), now(), request_ref),
            )
            db.execute("DELETE FROM articles WHERE article_id=?", (str(identifier),))
    ids = [row["article_id"] for row in db.execute("SELECT article_id FROM tombstones")]
    atomic_json(state / "erasures.json", ids)
    pointer = state / "current.json"
    current = json.loads(pointer.read_text()) if pointer.exists() else None
    if current:
        publish(db, state, current["run_id"])
    for root in (state / "published", state / "mirror"):
        if root.exists():
            for child in root.iterdir():
                if child.is_dir() and (not current or child.name != current["run_id"]):
                    shutil.rmtree(child)
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.execute("VACUUM")
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    (state / "erasures_pending.json").unlink(missing_ok=True)
    for identifier in identifiers:
        event(
            state,
            "rights_erased_local",
            article_id=str(identifier),
            request_ref=request_ref,
            external_propagation="requires_B2_B4_source_backups_coordination",
        )


def sync_external(db, state, config):
    """Import a local B2 denylist before collection AND publication; never modify B2."""
    name = config.get("external_tombstones")
    denied = json.loads(Path(name).read_text()) if name and Path(name).exists() else []
    if not isinstance(denied, list) or any(not isinstance(i, (str, int)) for i in denied):
        raise ValueError("invalid_external_tombstones")
    new = [
        str(i)
        for i in denied
        if not db.execute("SELECT 1 FROM tombstones WHERE article_id=?", (str(i),)).fetchone()
    ]
    pending = Path(state) / "erasures_pending.json"
    retry_ids = json.loads(pending.read_text()) if pending.exists() else []
    new = list(set(new + [str(i) for i in retry_ids]))
    if new:
        apply_erasure(db, state, new, "B2-REGISTER-IMPORT")
        event(state, "external_tombstones_imported", count=len(new))


def erase(state, article_id, request_ref):
    """Local command is idempotent; source files outside B3 are deliberately untouched."""
    with lock(state):
        db = connect(state)
        try:
            apply_erasure(db, state, [article_id], request_ref)
        finally:
            db.close()
