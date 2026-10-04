"""Transactional batch processing with automatic discovery of the durable checkpoint."""

import hashlib
import json
import os
import signal
import time
import uuid
from pathlib import Path

from .common import alert, atomic_json, event, lock, now, sha256
from .publish import publish
from .rights import sync_external
from .source import records
from .state import connect
from .transform import normalize


def run(config):
    state, source = Path(config["state"]), Path(config["source"])
    with lock(state):
        return _run(config, state, source)


def _run(config, state, source):
    source_hash = sha256(source)
    semantics = {k: config[k] for k in ("mode", "max_reject_rate", "synthetic")}
    semantics["transform_sha256"] = sha256(Path(__file__).with_name("transform.py"))
    config_hash = hashlib.sha256(json.dumps(semantics, sort_keys=True).encode()).hexdigest()
    db = connect(state)
    sync_external(db, state, config)
    saved = db.execute(
        """SELECT * FROM runs WHERE source_sha256=? AND config_sha256=?
                          ORDER BY started_at DESC LIMIT 1""",
        (source_hash, config_hash),
    ).fetchone()
    if saved and saved["status"] == "complete" and (state / "current.json").exists():
        event(state, "unchanged_source", run_id=saved["run_id"])
        db.close()
        return {"run_id": saved["run_id"], "unchanged": True}
    if saved and saved["status"] == "quality_failed":
        raise ValueError("quality_failed_source_requires_correction")
    if saved:
        run_id, checkpoint = saved["run_id"], saved["checkpoint"]
    else:
        run_id, checkpoint = str(uuid.uuid4()), 0
        db.execute(
            """INSERT INTO runs(run_id,source_sha256,config_sha256,source_name,status,started_at,
                     updated_at,synthetic) VALUES(?,?,?,?,?,?,?,?)""",
            (
                run_id,
                source_hash,
                config_hash,
                source.name,
                "running",
                now(),
                now(),
                config["synthetic"],
            ),
        )
    db.execute(
        "UPDATE runs SET status='running',attempts=attempts+1,updated_at=? WHERE run_id=?",
        (now(), run_id),
    )
    db.commit()
    event(
        state,
        "worker_start",
        run_id=run_id,
        checkpoint=checkpoint,
        source_sha256=source_hash,
    )
    batch, started = [], time.perf_counter()
    try:
        for index, item in records(source):
            if index < checkpoint:
                continue
            batch.append((index, item))
            if len(batch) >= config["batch_size"]:
                process_batch(db, config, run_id, source_hash, batch)
                batch.clear()
        if batch:
            process_batch(db, config, run_id, source_hash, batch)
        if sha256(source) != source_hash:
            raise ValueError("source_changed_during_run")
        result = dict(db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
        rate = result["rejected"] / max(result["checkpoint"], 1)
        if result["accepted"] == 0 or rate > config["max_reject_rate"]:
            db.execute(
                "UPDATE runs SET status='quality_failed',updated_at=? WHERE run_id=?",
                (now(), run_id),
            )
            db.commit()
            alert(
                state,
                "QUALITY_BLOCKED",
                run_id=run_id,
                rejected=result["rejected"],
                reject_rate=rate,
            )
            raise ValueError("quality_gate_failed")
        sync_external(db, state, config)
        manifest = publish(db, state, run_id)
        db.execute(
            "UPDATE runs SET status='complete',updated_at=? WHERE run_id=?",
            (now(), run_id),
        )
        db.commit()
        result.update(
            status="complete",
            attempt_duration_s=round(time.perf_counter() - started, 6),
            reject_rate=rate,
            publication=manifest,
        )
        atomic_json(state / "last_result.json", result)
        event(
            state,
            "complete",
            run_id=run_id,
            rows=result["checkpoint"],
            rejected=result["rejected"],
        )
        return result
    except Exception as exc:
        db.rollback()
        db.execute(
            "UPDATE runs SET status=CASE WHEN status='quality_failed' THEN status ELSE 'retryable' END, updated_at=? WHERE run_id=?",
            (now(), run_id),
        )
        db.commit()
        alert(
            state,
            "WORKER_ERROR",
            run_id=run_id,
            exception=type(exc).__name__,
            error_code=str(exc)[:100],
        )
        raise
    finally:
        db.close()


def process_batch(db, config, run_id, source_hash, batch):
    """The article rows AND the next-record cursor commit together, including rejects."""
    state, start = Path(config["state"]), time.perf_counter()
    counts = {"accepted": 0, "rejected": 0, "duplicates": 0, "suppressed": 0}
    with db:
        for index, item in batch:
            try:
                article = normalize(item, source_hash, index, run_id, config["mode"])
                key = str(article["id"])
                if db.execute("SELECT 1 FROM tombstones WHERE article_id=?", (key,)).fetchone():
                    counts["suppressed"] += 1
                    continue
                previous = db.execute(
                    "SELECT text_sha256 FROM articles WHERE run_id=? AND article_id=?",
                    (run_id, key),
                ).fetchone()
                if previous:
                    if previous["text_sha256"] != article["text_sha256"]:
                        raise ValueError("conflicting_id")
                    counts["duplicates"] += 1
                elif db.execute(
                    "SELECT 1 FROM articles WHERE run_id=? AND text_sha256=?",
                    (run_id, article["text_sha256"]),
                ).fetchone():
                    counts["duplicates"] += 1
                else:
                    db.execute(
                        "INSERT INTO articles VALUES(?,?,?,?,?)",
                        (
                            run_id,
                            index,
                            key,
                            article["text_sha256"],
                            json.dumps(article, ensure_ascii=False),
                        ),
                    )
                    counts["accepted"] += 1
            except ValueError as exc:
                db.execute(
                    "INSERT OR REPLACE INTO rejects VALUES(?,?,?)",
                    (run_id, index, str(exc)),
                )
                counts["rejected"] += 1
            # Test-only injection kills the OS process with an open uncommitted transaction.
            # Marker survives; the supervisor's next worker cannot inject the same crash again.
            fault_at = config.get("test_kill_at_record")
            marker = state / "test_crash_injected"
            if fault_at is not None and index == fault_at and not marker.exists():
                atomic_json(marker, {"at": now(), "record": index})
                event(state, "test_sigkill", run_id=run_id, uncommitted_record=index)
                os.kill(os.getpid(), signal.SIGKILL)
        duration = time.perf_counter() - start
        db.execute(
            """UPDATE runs SET checkpoint=?, accepted=accepted+?, rejected=rejected+?,
                      duplicates=duplicates+?, suppressed=suppressed+?, processing_s=processing_s+?,
                      updated_at=? WHERE run_id=?""",
            (
                batch[-1][0] + 1,
                counts["accepted"],
                counts["rejected"],
                counts["duplicates"],
                counts["suppressed"],
                duration,
                now(),
                run_id,
            ),
        )
    event(
        state,
        "checkpoint",
        run_id=run_id,
        checkpoint=batch[-1][0] + 1,
        batch_duration_s=round(duration, 6),
        **counts,
    )
    if counts["rejected"]:
        alert(state, "REJECTED_RECORDS", run_id=run_id, count=counts["rejected"])
    if duration > config["slow_batch_seconds"]:
        alert(
            state,
            "SLOW_BATCH",
            run_id=run_id,
            batch_duration_s=round(duration, 6),
            threshold_s=config["slow_batch_seconds"],
        )
    if config.get("test_batch_delay_seconds", 0):
        time.sleep(config["test_batch_delay_seconds"])
