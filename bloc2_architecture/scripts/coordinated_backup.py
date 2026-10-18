"""Encrypted Bloc 2 + Bloc 3 snapshot and isolated local restoration drill.

Stop the Bloc 3 server before capture. No live database is replaced. The encryption
key remains separate; this command never claims an off-host copy.
"""

import argparse
import base64
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import backup_restore as b2

ROOT = Path(__file__).resolve().parents[1]


def open_archive(payload, key):
    if payload[:8] != b"OSINTCO1":
        raise ValueError("Format de sauvegarde coordonnée invalide")
    plain = AESGCM(key).decrypt(payload[8:20], payload[20:], b"osint-coordinated-v1")
    return zipfile.ZipFile(io.BytesIO(plain))


def verify_restoration(payload, key, private_parent):
    # Unique namespaces belong only to this invocation and are always removed.
    name = "osint_drill_" + uuid.uuid4().hex[:12]
    pg_created = False
    try:
        with open_archive(payload, key) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            for path, digest in manifest["sha256"].items():
                assert hashlib.sha256(archive.read(path)).hexdigest() == digest
            with tempfile.TemporaryDirectory(
                prefix="coord-restore-", dir=private_parent
            ) as directory:
                db_path = Path(directory) / "catalog.sqlite"
                db_path.write_bytes(archive.read("bloc3/catalog.sqlite"))
                with sqlite3.connect(db_path) as db:
                    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                    assert not db.execute("PRAGMA foreign_key_check").fetchall()
                    heads = db.execute("SELECT count(*) FROM heads").fetchone()[0]
                    assert heads == manifest["catalog_heads"]
            inner = archive.read("bloc2.enc")
            raw = AESGCM(key).decrypt(inner[8:20], inner[20:], b"osint-backup-v1")
            with zipfile.ZipFile(io.BytesIO(raw)) as inner_zip:
                b2.command(
                    ["exec", "-T", "postgres", "createdb", "-U", "postgres", name]
                )
                pg_created = True
                b2.command(
                    [
                        "exec",
                        "-T",
                        "postgres",
                        "pg_restore",
                        "-U",
                        "postgres",
                        "-d",
                        name,
                        "--exit-on-error",
                    ],
                    inner_zip.read("postgres.dump"),
                )
                script = (
                    'mongorestore --host mongo --ssl --sslCAFile /run/secrets/ca.crt --username admin --authenticationDatabase admin --password "$(cat /run/secrets/mongo_admin)" --archive --gzip --nsInclude="osint.*" --nsFrom="osint.*" --nsTo="'
                    + name
                    + '.*"'
                )
                b2.command(
                    ["exec", "-T", "mongo", "bash", "-c", script],
                    inner_zip.read("mongo.archive.gz"),
                )
                pg_rows = int(
                    b2.command(
                        [
                            "exec",
                            "-T",
                            "postgres",
                            "psql",
                            "-U",
                            "postgres",
                            "-d",
                            name,
                            "-Atc",
                            "SELECT count(*) FROM articles",
                        ]
                    )
                    .decode()
                    .strip()
                )
                mg_rows = int(
                    b2.mongo_command(
                        "mongosh",
                        "--quiet --eval 'db.getSiblingDB(\""
                        + name
                        + "\").documents.countDocuments({})'",
                    )
                    .decode()
                    .strip()
                )
                assert pg_rows == mg_rows == manifest["bloc2_articles"]
                views = int(
                    b2.command(
                        [
                            "exec",
                            "-T",
                            "postgres",
                            "psql",
                            "-U",
                            "postgres",
                            "-d",
                            name,
                            "-Atc",
                            "SELECT count(*) FROM pg_views WHERE schemaname='analytics'",
                        ]
                    )
                    .decode()
                    .strip()
                )
            return {
                "catalog_heads": heads,
                "postgres_rows": pg_rows,
                "mongo_documents": mg_rows,
                "analytics_views": views,
                "hashes_verified": True,
                "sqlite_integrity": "ok",
                "exports": manifest["exports"],
            }
    finally:
        if pg_created:
            b2.command(["exec", "-T", "postgres", "dropdb", "-U", "postgres", name])
        b2.mongo_command(
            "mongosh",
            "--quiet --eval 'db.getSiblingDB(\"" + name + "\").dropDatabase()'",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-state", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    # Reuse the same verified encrypted-volume check as the Bloc 3 launcher.
    collection_root = ROOT.parent / "03_Bloc_3_Pipelines"
    if not collection_root.exists():
        collection_root = ROOT.parent / "bloc3_pipeline"
    if not collection_root.is_dir():
        parser.error("Extraire aussi le code du Bloc 3 à côté du Bloc 2, ou utiliser le dépôt commun.")
    sys.path.insert(0, str(collection_root))
    from pipeline.collection.security import encrypted_volume

    state = args.catalog_state.resolve(strict=True)
    output = args.private_output.resolve(strict=True)
    if not encrypted_volume(state) or not encrypted_volume(output):
        parser.error(
            "Catalogue et destination privée doivent être sur un volume chiffré monté."
        )
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    b2.EVIDENCE = args.evidence_dir
    key = base64.b64decode((ROOT / ".secrets/backup_key").read_bytes())
    with ExitStack() as stack:
        for filename in ["collection-server.lock", "collection-worker.lock"]:
            handle = stack.enter_context((state / filename).open("a+"))
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                parser.error(
                    "Arrêter le serveur et le worker du Bloc 3 avant la capture."
                )
        stack.enter_context(b2.write_lock())
        guard = sqlite3.connect(state / "collection.sqlite", timeout=5)
        stack.callback(guard.close)
        guard.execute("BEGIN IMMEDIATE")
        with tempfile.TemporaryDirectory(
            prefix="coord-capture-", dir=output
        ) as directory:
            temporary = Path(directory) / "catalog.sqlite"
            with (
                sqlite3.connect(state / "collection.sqlite") as source,
                sqlite3.connect(temporary) as dest,
            ):
                source.backup(dest)
                heads = dest.execute("SELECT count(*) FROM heads").fetchone()[0]
            inner = b2.capture_backup()
            entries = {
                "bloc2.enc": inner.read_bytes(),
                "bloc3/catalog.sqlite": temporary.read_bytes(),
            }
            exports = 0
            for path in sorted((state / "exports").rglob("*")):
                if path.is_symlink():
                    raise ValueError("Lien dans les exports, capture refusée")
                if path.is_file():
                    entries[
                        "bloc3/exports/" + str(path.relative_to(state / "exports"))
                    ] = path.read_bytes()
                    exports += 1
            rights = state / "rights.json"
            if rights.exists():
                entries["bloc3/rights.json"] = rights.read_bytes()
            pg_rows = int(
                b2.command(
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
                        "SELECT count(*) FROM articles",
                    ]
                )
                .decode()
                .strip()
            )
            manifest = {
                "catalog_heads": heads,
                "bloc2_articles": pg_rows,
                "exports": exports,
                "sha256": {
                    n: hashlib.sha256(data).hexdigest() for n, data in entries.items()
                },
            }
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
                archive.writestr("manifest.json", json.dumps(manifest))
            nonce = os.urandom(12)
            payload = (
                b"OSINTCO1"
                + nonce
                + AESGCM(key).encrypt(nonce, buf.getvalue(), b"osint-coordinated-v1")
            )
            target = output / (
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + "-coordinated.enc"
            )
            with target.open("xb") as stream:
                stream.write(payload)
            restored = verify_restoration(payload, key, output)
            from cryptography.exceptions import InvalidTag

            corrupt = bytearray(payload)
            corrupt[-1] ^= 1
            try:
                open_archive(bytes(corrupt), key)
            except InvalidTag:
                tampering_rejected = True
            else:
                raise AssertionError("Corrupted archive accepted")
    proof = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "encryption": "AES-256-GCM",
        "backup_sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "restoration": restored,
        "tampering_rejected": tampering_rejected,
        "source_databases_replaced": False,
        "off_host_copy": False,
        "key_included": False,
        "limitations": [
            "Même Mac, aucun support externe disponible",
            "Arrêt du serveur Bloc 3 et absence de mutation administrative pendant la capture requis",
            "Les clés et la configuration de reconstruction doivent être conservées séparément",
            "Périmètres Bloc 2 et catalogue distincts ; aucune égalité de corpus supposée",
            "Décisions ultérieures de droits à réappliquer avant une restauration opérationnelle",
        ],
    }
    (args.evidence_dir / "Sauvegarde_coordonnee.json").write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(proof, ensure_ascii=False))


if __name__ == "__main__":
    main()
