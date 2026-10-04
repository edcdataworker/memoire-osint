"""Encrypted consistent snapshot and restoration drill in disposable namespaces.
Run when ingestion is idle. Source namespaces are never replaced by this drill.
"""

import argparse
from contextlib import contextmanager
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import os
import subprocess
import time
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]


def command(args, data=None):
    result = subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError("Docker operation failed: " + " ".join(args[:3]))
    return result.stdout


def mongo_command(operation, extra=""):
    return command(
        [
            "exec",
            "-T",
            "mongo",
            "bash",
            "-c",
            f"{operation} --host mongo --ssl --sslCAFile /run/secrets/ca.crt "
            "--username admin --authenticationDatabase admin "
            '--password "$(cat /run/secrets/mongo_admin)" ' + extra,
        ]
    )


@contextmanager
def write_lock():
    code = "from osint.storage import pg; import sys; c=pg(); c.execute('SELECT pg_advisory_lock(420026)'); print('LOCKED',flush=True); sys.stdin.readline(); c.close()"
    process = subprocess.Popen(
        ["docker", "compose", "run", "--rm", "-T", "ops", "python", "-c", code],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        if process.stdout.readline().strip() != b"LOCKED":
            raise RuntimeError("Could not acquire consistent snapshot lock")
        yield
    finally:
        process.communicate(b"release\n", timeout=30)
        if process.returncode:
            raise RuntimeError("Snapshot lock process failed")


def backup():
    with write_lock():
        return capture_backup()


def capture_backup():
    start = time.perf_counter()
    # The advisory lock is held throughout capture. A stale running status still
    # requires investigation; direct administrator writes must stay paused.
    running = (
        command(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "osint",
                "-Atc",
                "SELECT count(*) FROM runs WHERE status='running'",
            ]
        )
        .decode()
        .strip()
    )
    if running != "0":
        raise RuntimeError("Wait for all ingestion runs to finish before backup")
    pg = command(
        ["exec", "-T", "postgres", "pg_dump", "-U", "postgres", "-d", "osint", "-Fc"]
    )
    mg = mongo_command("mongodump", "--db osint --archive --gzip")
    state = ROOT / ".state/erasures.json"
    ledger = state.read_bytes() if state.exists() else b"[]"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("postgres.dump", pg)
        archive.writestr("mongo.archive.gz", mg)
        archive.writestr("erasures.json", ledger)
    nonce = os.urandom(12)
    key = base64.b64decode((ROOT / ".secrets/backup_key").read_bytes())
    payload = (
        b"OSINTBK1"
        + nonce
        + AESGCM(key).encrypt(nonce, buffer.getvalue(), b"osint-backup-v1")
    )
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = ROOT / ".backups" / f"{name}.enc"
    target.write_bytes(payload)
    target.chmod(0o600)
    result = {
        "backup": target.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "encryption": "AES-256-GCM",
        "duration_s": round(time.perf_counter() - start, 3),
        "scope": "PostgreSQL + MongoDB + erasure ledger; data encryption key stored separately",
        "offsite_copy": False,
    }
    (ROOT / "Preuves/backup.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    return target


def restore(path):
    start = time.perf_counter()
    payload = Path(path).read_bytes()
    assert payload[:8] == b"OSINTBK1"
    key = base64.b64decode((ROOT / ".secrets/backup_key").read_bytes())
    plain = AESGCM(key).decrypt(payload[8:20], payload[20:], b"osint-backup-v1")
    with zipfile.ZipFile(io.BytesIO(plain)) as archive:
        command(
            [
                "exec",
                "-T",
                "postgres",
                "dropdb",
                "-U",
                "postgres",
                "--if-exists",
                "osint_restore_test",
            ]
        )
        command(
            [
                "exec",
                "-T",
                "postgres",
                "createdb",
                "-U",
                "postgres",
                "osint_restore_test",
            ]
        )
        command(
            [
                "exec",
                "-T",
                "postgres",
                "pg_restore",
                "-U",
                "postgres",
                "-d",
                "osint_restore_test",
                "--exit-on-error",
            ],
            archive.read("postgres.dump"),
        )
        script = (
            "mongorestore --host mongo --ssl --sslCAFile /run/secrets/ca.crt "
            '--username admin --authenticationDatabase admin --password "$(cat /run/secrets/mongo_admin)" '
            '--archive --gzip --nsInclude="osint.*" --nsFrom="osint.*" --nsTo="osint_restore_test.*" --drop'
        )
        command(
            ["exec", "-T", "mongo", "bash", "-c", script],
            archive.read("mongo.archive.gz"),
        )
        denied = set(json.loads(archive.read("erasures.json")))
    ledger = ROOT / ".state/erasures.json"
    if ledger.exists():
        denied.update(json.loads(ledger.read_text()))
    # Apply newer erasures before opening restored data to any reader.
    for key in sorted(denied):
        if not all(c.isalnum() or c in "-_" for c in key):
            raise ValueError("Invalid ledger identifier")
        command(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "osint_restore_test",
                "-c",
                f"DELETE FROM articles WHERE article_id='{key}'",
            ]
        )
        mongo_command(
            "mongosh",
            "--quiet --eval "
            + json.dumps(
                'db.getSiblingDB("osint_restore_test").documents.deleteOne({_id:'
                + json.dumps(key)
                + "})"
            ),
        )
    pg_count = int(
        command(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "osint_restore_test",
                "-Atc",
                "SELECT count(*) FROM articles",
            ]
        )
        .decode()
        .strip()
    )
    mongo_count = int(
        mongo_command(
            "mongosh",
            "--quiet --eval 'db.getSiblingDB(\"osint_restore_test\").documents.countDocuments({})'",
        )
        .decode()
        .strip()
    )
    assert pg_count == mongo_count
    result = {
        "restore_namespace": "osint_restore_test",
        "postgres_rows": pg_count,
        "mongo_documents": mongo_count,
        "duration_s": round(time.perf_counter() - start, 3),
        "reapplied_erasures": len(denied),
        "source_databases_replaced": False,
        "index_rebuild": "separate operation from restored authorities",
    }
    (ROOT / "Preuves/restore.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=["backup", "restore-test"])
    p.add_argument("path", nargs="?")
    a = p.parse_args()
    backup() if a.operation == "backup" else restore(a.path)
