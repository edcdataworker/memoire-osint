"""Local permissions, encrypted-volume checks and metadata-only incidents."""

import calendar
import json
import os
import plistlib
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..common import actor_identity, atomic_json, now


def encrypted_volume(state):
    """Verify the mounted backing image, not merely a directory named /Volumes."""
    try:
        result = subprocess.run(
            ["hdiutil", "info", "-plist"], capture_output=True, check=True, timeout=10
        )
        for image in plistlib.loads(result.stdout).get("images", []):
            for entity in image.get("system-entities", []):
                mount = entity.get("mount-point")
                if mount and Path(state).resolve().is_relative_to(Path(mount)):
                    return bool(image.get("image-encrypted"))
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return False


def incident(state, code, **fields):
    """Works even when the catalog is corrupt. Never put raw errors in a dossier."""
    from ..common import event

    event(state, "security_incident", code=code, **fields)
    path = Path(state) / "security.json"
    atomic_json(path, {"at": now(), "actor": actor_identity(), "code": code, **fields})


def check(state, require_encrypted=False):
    state = Path(state)
    unsafe = []
    for path in [state, *state.rglob("*")]:
        if path.is_symlink():
            continue
        try:
            mode = path.stat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_IMODE(mode) & 0o077:
            unsafe.append(path)
    if unsafe:
        # Contain before appending private incident metadata.
        for path in unsafe:
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        incident(state, "SECURITY_PERMISSIONS", affected=len(unsafe), contained=True)
    encrypted = encrypted_volume(state)
    if require_encrypted and not encrypted:
        incident(state, "ENCRYPTED_VOLUME_REQUIRED", contained=True)
        raise OSError("Déverrouiller le volume chiffré avant d’ouvrir l’Observatoire.")
    return {
        "permissions_safe": not unsafe,
        "contained": bool(unsafe),
        "encrypted_volume": encrypted,
        "encryption_required": require_encrypted,
    }


def minimize_audit(state):
    """Remove the legacy queued-job keywords from managed audit logs."""
    for path in (Path(state) / "events.jsonl", Path(state) / "worker.log"):
        if not path.exists():
            continue
        rows = []
        changed = False
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                rows.append(line)
                continue
            if "keywords" in row:
                row["keyword_count"] = len(row.pop("keywords"))
                changed = True
            rows.append(json.dumps(row, ensure_ascii=False))
        if changed:
            from ..common import atomic_bytes

            atomic_bytes(path, "\n".join(rows).encode() + b"\n")
    from . import store

    with store.database(state) as db, db:
        for entry in db.execute("SELECT sequence,fields FROM events").fetchall():
            row = json.loads(entry[1])
            if "keywords" in row:
                row["keyword_count"] = len(row.pop("keywords"))
                db.execute(
                    "UPDATE events SET fields=? WHERE sequence=?", (json.dumps(row), entry[0])
                )


def retention(state):
    """Six calendar months for managed audit logs; active rights ledgers are separate."""
    current = datetime.now(timezone.utc)
    month = current.year * 12 + current.month - 1 - 6
    year, zero_month = divmod(month, 12)
    cutoff = current.replace(
        year=year,
        month=zero_month + 1,
        day=min(current.day, calendar.monthrange(year, zero_month + 1)[1]),
    ).isoformat()
    from ..common import atomic_bytes
    from . import store

    with store.database(state) as db, db:
        deleted = db.execute("DELETE FROM events WHERE at<?", (cutoff,)).rowcount
    for path in (Path(state) / "events.jsonl", Path(state) / "worker.log"):
        if not path.exists():
            continue
        original = path.read_text().splitlines()
        rows = []
        for line in original:
            try:
                entry = json.loads(line)
                if entry.get("at", cutoff) < cutoff:
                    continue
            except ValueError:
                pass
            rows.append(line)
        if len(rows) != len(original):
            atomic_bytes(path, "\n".join(rows).encode() + b"\n")
    return deleted
