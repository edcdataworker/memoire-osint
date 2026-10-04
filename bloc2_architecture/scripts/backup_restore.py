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
import shlex
import time
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "Preuves"


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
    corrections_path = ROOT / ".state/rectifications.json"
    corrections = corrections_path.read_bytes() if corrections_path.exists() else b"{}"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        archive.writestr("postgres.dump", pg)
        archive.writestr("mongo.archive.gz", mg)
        archive.writestr("erasures.json", ledger)
        archive.writestr("rectifications.json", corrections)
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
        "scope": "PostgreSQL + MongoDB + erasure and encrypted correction ledgers; data encryption key stored separately",
        "offsite_copy": False,
    }
    (EVIDENCE / "backup.json").write_text(json.dumps(result, indent=2))
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
        corrections = (
            json.loads(archive.read("rectifications.json"))
            if "rectifications.json" in archive.namelist()
            else {}
        )
    ledger = ROOT / ".state/erasures.json"
    if ledger.exists():
        denied.update(json.loads(ledger.read_text()))
    current_corrections = ROOT / ".state/rectifications.json"
    if current_corrections.exists():
        corrections.update(json.loads(current_corrections.read_text()))
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
                "DO $erase$ BEGIN IF to_regclass('article_revisions') IS NOT NULL THEN "
                f"DELETE FROM article_revisions WHERE article_id='{key}'; "
                f"END IF; DELETE FROM articles WHERE article_id='{key}'; END $erase$;",
            ]
        )
        mongo_command(
            "mongosh",
            "--quiet --eval "
            + shlex.quote(
                'db.getSiblingDB("osint_restore_test").document_revisions.deleteMany({article_id:'
                + json.dumps(key)
                + '}); db.getSiblingDB("osint_restore_test").documents.deleteOne({_id:'
                + json.dumps(key)
                + "})"
            ),
        )
    reapplied = 0
    for identifier, correction in corrections.items():
        if identifier in denied:
            continue
        if not all(c.isalnum() or c in "-_" for c in identifier):
            raise ValueError("Invalid correction identifier")
        encrypted = base64.b64decode(correction["ciphertext"])
        data_key = base64.b64decode((ROOT / ".secrets/data_key").read_bytes())
        row = json.loads(
            AESGCM(data_key).decrypt(
                encrypted[:12], encrypted[12:], identifier.encode()
            )
        )
        body = {
            k: v
            for k, v in row.items()
            if k not in ("id", "date", "date_readable", "source_id")
        }
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        checksum = hashlib.sha256(raw).hexdigest()
        nonce = os.urandom(12)
        ciphertext = base64.b64encode(
            nonce + AESGCM(data_key).encrypt(nonce, raw, identifier.encode())
        ).decode()
        lines = (
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
                    f"DELETE FROM article_revisions WHERE article_id='{identifier}'; UPDATE articles SET content_sha256='{checksum}' WHERE article_id='{identifier}' RETURNING run_id;",
                ]
            )
            .decode()
            .splitlines()
        )
        run_id = next(
            (line for line in lines if len(line) == 36 and line.count("-") == 4), None
        )
        if not run_id:
            continue
        update = {
            "ciphertext": ciphertext,
            "content_sha256": checksum,
            "run_id": run_id,
        }
        expression = (
            'var d=db.getSiblingDB("osint_restore_test");d.document_revisions.deleteMany({article_id:'
            + json.dumps(identifier)
            + "});d.documents.updateOne({_id:"
            + json.dumps(identifier)
            + "},{$set:"
            + json.dumps(update)
            + "})"
        )
        mongo_command("mongosh", "--quiet --eval " + shlex.quote(expression))
        reapplied += 1
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
        "reapplied_rectifications": reapplied,
        "source_databases_replaced": False,
        "index_rebuild": "separate operation from restored authorities",
    }
    (EVIDENCE / "restore.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("operation", choices=["backup", "restore-test"])
    p.add_argument("path", nargs="?")
    p.add_argument("--evidence-dir", type=Path, default=EVIDENCE)
    a = p.parse_args()
    EVIDENCE = a.evidence_dir
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    backup() if a.operation == "backup" else restore(a.path)
