"""Atomic files, private directories, checksums and local audit events."""

import fcntl
import getpass
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def private_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def atomic_bytes(path, data):
    """Replace only after file fsync; readers see the old or the complete new file."""
    path = Path(path)
    private_dir(path.parent)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def actor_identity():
    """Containers may run under a numeric UID absent from /etc/passwd."""
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        return f"uid:{os.getuid()}"


def event(state, kind, **fields):
    """Audit metadata only. Never record article text, credentials or raw invalid rows."""
    item = {"at": now(), "event": kind, "actor": actor_identity(), **fields}
    destination = private_dir(Path(state)) / "events.jsonl"
    with destination.open("a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(item, ensure_ascii=False), flush=True)
    return item


def alert(state, code, **fields):
    item = event(state, "alert", code=code, **fields)
    with (Path(state) / "alerts.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def lock(state, name="worker.lock"):
    path = private_dir(state) / name
    with path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
