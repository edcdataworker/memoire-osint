"""Resumable ingestion: Mongo first, SQL commit/checkpoint second, derived index later."""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from pymongo import ReplaceOne
from .storage import encrypt, mongo, pg, tombstones


def records(path=None, count=0):
    if path:
        data = json.loads(Path(path).read_text())
        for item in data:
            yield {
                "id": str(item["id"]),
                "source_id": item.get("source_id", "tass"),
                "published_at": datetime.fromtimestamp(item["date"], timezone.utc),
                "payload": {
                    k: v
                    for k, v in item.items()
                    if k not in ("id", "date", "date_readable", "source_id")
                },
                "synthetic": False,
            }
    else:
        epoch = datetime(2025, 1, 1, tzinfo=timezone.utc)
        for i in range(count):
            yield {
                "id": f"synthetic-{i:09d}",
                "source_id": "tass",
                "published_at": epoch + timedelta(seconds=i),
                "payload": {
                    "title": f"Synthetic record {i}",
                    "text": "Synthetic payload for storage benchmark. " * 6,
                    "url": "https://example.invalid/synthetic",
                },
                "synthetic": True,
            }


def ingest(path=None, count=0, fail_after=0, resume=None):
    expected = len(json.loads(Path(path).read_text())) if path else count
    fingerprint = (
        hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if path
        else hashlib.sha256(f"synthetic-v1:{count}".encode()).hexdigest()
    )
    run_id = uuid.UUID(resume) if resume else uuid.uuid4()
    batch_size = int(os.getenv("BATCH_SIZE", "2000"))
    denied = tombstones()
    db = mongo()
    start = time.perf_counter()
    with pg() as sql:
        # Reject accidental concurrent writers: one checkpoint stream at a time.
        if not sql.execute("SELECT pg_try_advisory_lock(420026)").fetchone()[0]:
            raise RuntimeError("Another ingestion is running")
        if resume:
            saved = sql.execute(
                "SELECT checkpoint,source_sha256,expected FROM runs WHERE run_id=%s",
                (run_id,),
            ).fetchone()
            if not saved or saved[1] != fingerprint or saved[2] != expected:
                raise ValueError("Resume source mismatch")
            offset = saved[0]
            sql.execute("UPDATE runs SET status='running' WHERE run_id=%s", (run_id,))
        else:
            offset = 0
            sql.execute(
                "INSERT INTO runs(run_id,kind,source_sha256,status,expected) VALUES(%s,%s,%s,%s,%s)",
                (
                    run_id,
                    "corpus" if path else "synthetic",
                    fingerprint,
                    "running",
                    expected,
                ),
            )
        sql.commit()
        print(
            json.dumps(
                {
                    "event": "start",
                    "run_id": str(run_id),
                    "offset": offset,
                    "expected": expected,
                }
            ),
            flush=True,
        )
        processed = offset
        batch = []
        try:
            for i, record in enumerate(records(path, count)):
                if i < offset:
                    continue
                batch.append(record)
                if len(batch) < batch_size and i + 1 != expected:
                    continue
                publish_batch(sql, db, batch, run_id, denied)
                processed = i + 1
                sql.execute(
                    "UPDATE runs SET checkpoint=%s WHERE run_id=%s", (processed, run_id)
                )
                sql.commit()
                batch = []
                if fail_after and processed >= fail_after:
                    raise RuntimeError("Intentional interruption after committed batch")
                if processed % 100000 == 0 or processed == expected:
                    print(
                        json.dumps(
                            {
                                "event": "checkpoint",
                                "rows": processed,
                                "elapsed_s": round(time.perf_counter() - start, 3),
                            }
                        ),
                        flush=True,
                    )
            sql.execute(
                "UPDATE runs SET status='complete',completed_at=now() WHERE run_id=%s",
                (run_id,),
            )
            sql.commit()
        except BaseException:
            sql.rollback()
            sql.execute("UPDATE runs SET status='failed' WHERE run_id=%s", (run_id,))
            sql.commit()
            raise
    result = {
        "run_id": str(run_id),
        "expected": expected,
        "processed": processed,
        "duration_s": round(time.perf_counter() - start, 3),
        "synthetic": not bool(path),
        "source_sha256": fingerprint,
        "batch_size": batch_size,
    }
    print(json.dumps(result), flush=True)
    return result


def publish_batch(sql, db, batch, run_id, denied):
    documents, rows = [], []
    for item in batch:
        if not item["id"] or not item["payload"]["text"].strip():
            raise ValueError("Missing identifier or empty text")
        if item["id"] in denied:
            continue
        ciphertext, checksum = encrypt(item["payload"], item["id"])
        doc = {
            "_id": item["id"],
            "published_at": item["published_at"],
            "ciphertext": ciphertext,
            "content_sha256": checksum,
            "schema_version": 1,
            "run_id": str(run_id),
            "synthetic": item["synthetic"],
        }
        documents.append(ReplaceOne({"_id": item["id"]}, doc, upsert=True))
        rows.append(
            (
                item["id"],
                item["source_id"],
                item["published_at"],
                checksum,
                1,
                run_id,
                item["synthetic"],
            )
        )
    if documents:
        db.documents.bulk_write(documents, ordered=False)
        # A staging COPY makes high-volume loading efficient, without disabling constraints.
        sql.execute(
            "CREATE TEMP TABLE IF NOT EXISTS ingest_batch (LIKE articles INCLUDING DEFAULTS) ON COMMIT DELETE ROWS"
        )
        with sql.cursor().copy("COPY ingest_batch FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
        sql.execute("""INSERT INTO articles SELECT * FROM ingest_batch
                    ON CONFLICT(article_id) DO UPDATE SET content_sha256=excluded.content_sha256,
                    published_at=excluded.published_at,run_id=excluded.run_id,
                    schema_version=excluded.schema_version,synthetic=excluded.synthetic""")
