"""Offline, verified migration into an already unlocked encrypted disk image."""

import json
import shutil
import sqlite3
from pathlib import Path

from ..common import atomic_json, lock, private_dir, sha256
from . import resilience, security, store


def migrate_legacy(source, destination):
    """Move the historical file-import state under the same encrypted volume."""
    source = Path(source)
    if not source.exists() or source.is_symlink():
        return {"migrated": False, "reason": "absent_or_already_linked"}
    if destination.exists():
        raise ValueError("État historique déjà présent ; source conservée.")
    with lock(source, "worker.lock"), lock(source, "scheduler.lock"):
        database = source / "pipeline.sqlite"
        with sqlite3.connect(database) as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copytree(
            source, destination, ignore=shutil.ignore_patterns("*.lock", "*-wal", "*-shm")
        )
        files = [
            p
            for p in source.rglob("*")
            if p.is_file() and not p.name.endswith((".lock", "-wal", "-shm"))
        ]
        for path in files:
            if sha256(path) != sha256(destination / path.relative_to(source)):
                raise OSError("Empreinte historique incohérente ; source conservée.")
        with sqlite3.connect(destination / "pipeline.sqlite") as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise OSError("État historique invalide ; source conservée.")
        security.check(destination, True)
    shutil.rmtree(source)
    source.symlink_to(destination, target_is_directory=True)
    return {"migrated": True, "files_verified": len(files), "legacy_path_is_link": True}


def migrate(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination or destination.is_relative_to(source):
        raise ValueError("Destination indépendante requise.")
    if not security.encrypted_volume(destination):
        raise OSError("La destination doit appartenir au volume chiffré déverrouillé.")
    if destination.exists():
        raise ValueError("Destination déjà présente ; ne pas écraser une migration.")
    with lock(source, "collection-server.lock"), lock(source, "collection-worker.lock"):
        resilience.compact(source)
        resilience.refresh(source)
        # Copy everything, including correction decisions. Only lock handles are omitted.
        shutil.copytree(
            source, destination, ignore=shutil.ignore_patterns("*.lock", "*-wal", "*-shm")
        )
        copied = [
            p
            for p in source.rglob("*")
            if p.is_file() and not p.name.endswith((".lock", "-wal", "-shm"))
        ]
        for path in copied:
            if sha256(path) != sha256(destination / path.relative_to(source)):
                raise OSError("Empreinte de migration incohérente ; source conservée.")

        def rewrite(value):
            if isinstance(value, str) and value.startswith(str(source) + "/"):
                return str(destination) + value[len(str(source)) :]
            if value == str(source):
                return str(destination)
            if isinstance(value, list):
                return [rewrite(v) for v in value]
            if isinstance(value, dict):
                return {k: rewrite(v) for k, v in value.items()}
            return value

        for path in destination.rglob("*.json"):
            atomic_json(path, rewrite(json.loads(path.read_text())))
        config = json.loads((destination / "config.json").read_text())
        config.update(state=str(destination), require_encrypted=True)
        atomic_json(destination / "config.json", config)
        resilience.verified(destination / "collection.sqlite")
        with store.database(source) as a, store.database(destination) as b:
            counts = {
                table: a.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("heads", "revisions", "jobs", "tasks")
            }
            if any(
                b.execute(f"SELECT count(*) FROM {t}").fetchone()[0] != n for t, n in counts.items()
            ):
                raise OSError("Comptes de migration incohérents ; source conservée.")
        security.check(destination, True)
        resilience.refresh(destination)
        report = {
            "encrypted_volume": True,
            "copied_files_verified": len(copied),
            "counts": counts,
            "source_removed": False,
            "forensic_ssd_erasure_guaranteed": False,
        }
        atomic_json(destination / "migration.json", report)
        # A durable pointer is written before removing the verified plaintext source.
        pointer = source.parent / ".collection-location.json"
        atomic_json(pointer, {"state": str(destination), "require_encrypted": True})
    shutil.rmtree(source)
    report["source_removed"] = True
    report["legacy_state"] = migrate_legacy(
        source.parent / ".state", destination.parent / "B3_historique"
    )
    atomic_json(destination / "migration.json", report)
    private_dir(destination)
    return report
