"""Verified read-only fallback and explicit offline restoration, on one host."""

import json
import os
import sqlite3
import time
from pathlib import Path

from ..common import atomic_json, lock, now, private_dir, sha256

_verified = {}


def verified(path):
    if not Path(path).is_file():
        raise OSError("Catalogue absent.")
    info = Path(path).stat()
    stamp = (info.st_ino, info.st_size, info.st_mtime_ns)
    previous = _verified.get(str(path))
    if previous and previous[0] == stamp and time.monotonic() - previous[1] < 5:
        return
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise OSError("Intégrité du catalogue invalide.")
        db.execute("SELECT count(*) FROM heads").fetchone()
    _verified[str(path)] = (stamp, time.monotonic())


def refresh(state):
    """Publish a complete SQLite snapshot atomically, never copy live WAL files."""
    from . import store

    state = Path(state)
    root = private_dir(state / "mirror")
    with lock(state, "collection-mirror.lock"):
        temporary = root / "catalog.tmp"
        temporary.unlink(missing_ok=True)
        with store.database(state) as source, sqlite3.connect(temporary) as target:
            source.backup(target)
            target.execute("PRAGMA journal_mode=DELETE")
        verified(temporary)
        checksum = sha256(temporary)
        os.chmod(temporary, 0o600)
        # The manifest is deliberately invalid during replacement: no stale generation
        # is served when a publication or rights update has only partly completed.
        (root / "manifest.json").unlink(missing_ok=True)
        temporary.replace(root / "catalog.sqlite")
        atomic_json(root / "manifest.json", {"at": now(), "sha256": checksum})


def backend(state):
    state = Path(state)
    try:
        verified(state / "collection.sqlite")
        manifest_path = state / "mirror/manifest.json"
        try:
            mirror_at = json.loads(manifest_path.read_text())["at"]
        except (OSError, ValueError, KeyError):
            mirror_at = None
        return state / "collection.sqlite", "primary", mirror_at
    except (sqlite3.Error, OSError):
        try:
            manifest = json.loads((state / "mirror/manifest.json").read_text())
            mirror = state / "mirror/catalog.sqlite"
            if sha256(mirror) != manifest["sha256"]:
                raise OSError("Empreinte de secours invalide.")
            verified(mirror)
            return mirror, "mirror", manifest["at"]
        except (sqlite3.Error, OSError, ValueError, KeyError) as exc:
            raise OSError("Catalogue principal et secours indisponibles.") from exc


def require_primary(state):
    _, kind, _ = backend(state)
    if kind != "primary":
        raise ValueError("Mode de secours : écritures bloquées. Restaurer le catalogue.")


def restore(state, config):
    """Caller holds the server and worker locks. Tombstones always precede exposure."""
    from . import store

    state = Path(state)
    mirror = state / "mirror/catalog.sqlite"
    manifest = json.loads((state / "mirror/manifest.json").read_text())
    if sha256(mirror) != manifest["sha256"]:
        raise OSError("Empreinte de secours invalide.")
    verified(mirror)
    temp = state / "restore.tmp"
    temp.unlink(missing_ok=True)
    with sqlite3.connect(f"file:{mirror.resolve()}?mode=ro", uri=True) as src:
        with sqlite3.connect(temp) as dest:
            src.backup(dest)
    verified(temp)
    # Stop locks exclude writers; remove WAL before installing a different main DB.
    for suffix in ("-wal", "-shm"):
        (state / ("collection.sqlite" + suffix)).unlink(missing_ok=True)
    temp.replace(state / "collection.sqlite")
    store.initialize(state)
    store.sync_denied(state, config)
    from .rights import reapply

    reapply(state, config)
    compact(state)
    refresh(state)
    store.emit(state, None, "catalog_restored", backend="primary")
    return {"restored": True, "rights_reapplied": True}


def compact(state):
    from . import store

    with store.database(state) as db:
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("VACUUM")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
