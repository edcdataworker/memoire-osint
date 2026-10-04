"""A separate process commits discovery and downloaded units before advancing."""

import json
import sys
import time
from pathlib import Path

from ..common import atomic_json, lock, now
from .resilience import refresh, require_primary
from .source import Client, Stopped, bounds, canonical, extract
from .store import database, emit, export, job, put, revision, sync_denied


def execute(state, key, config, client=None):
    with lock(state, "collection-worker.lock"):
        require_primary(state)
        with database(state) as db, db:
            db.execute(
                "UPDATE jobs SET status='running',attempts=attempts+1,error=NULL,updated=?,started_at=? WHERE job_id=?",
                (now(), now(), key),
            )

        def stopped():
            return (Path(state) / (key + ".stop")).exists()

        def report(kind, **fields):
            emit(state, key, kind, **fields)

        client = client or Client(report, stopped, config.get("request_interval", 0.7))
        start = time.monotonic()
        try:
            denied = sync_denied(state, config)
            current = job(state, key)
            params = current["params"]
            left, right = bounds(params["start"], params["end"])
            if current["stage"] == "discovery":
                section_id = client.initialize(params["section"])
                with database(state) as db, db:
                    db.execute("UPDATE jobs SET section_id=? WHERE job_id=?", (section_id, key))
                while True:
                    if stopped():
                        raise Stopped()
                    current = job(state, key)
                    previous_cursor = current["cursor"]
                    if current["pages"] >= config.get("max_pages", 250):
                        coverage = "page_limit"
                        report("alert", code="DISCOVERY_LIMIT")
                        break
                    with database(state) as db:
                        excluded = [
                            int(r[0])
                            for r in db.execute(
                                "SELECT article_id FROM tasks WHERE job_id=? ORDER BY rowid DESC LIMIT 100",
                                (key,),
                            )
                        ]
                    result = client.discover(section_id, current["cursor"], excluded)
                    entries = result["newsList"]
                    before, older = current["discovered"], False
                    last = result.get("lastTime")
                    if not entries:
                        coverage = "source_end"
                        break
                    with database(state) as db, db:
                        for item in entries:
                            date = item.get("date")
                            if type(date) not in (int, float):
                                raise ValueError("Date de pagination invalide.")
                            if date < left:
                                older = True
                                continue
                            if date >= right:
                                continue
                            url = canonical("https://tass.com" + item["link"])
                            if url.split("/")[3] != params["section"]:
                                continue
                            count = db.execute(
                                "SELECT count(*) FROM tasks WHERE job_id=?", (key,)
                            ).fetchone()[0]
                            if count >= params["limit"]:
                                break
                            db.execute(
                                "INSERT OR IGNORE INTO tasks(job_id,url,article_id,status) VALUES(?,?,?,?)",
                                (
                                    key,
                                    url,
                                    str(item["id"]),
                                    "suppressed" if str(item["id"]) in denied else "pending",
                                ),
                            )
                        if type(last) not in (int, float) or last > current["cursor"]:
                            raise ValueError("Curseur de pagination invalide.")
                        db.execute(
                            "UPDATE jobs SET cursor=?,pages=pages+1,updated=? WHERE job_id=?",
                            (int(last), now(), key),
                        )
                    current = job(state, key)
                    report(
                        "discovery_page",
                        pages=current["pages"],
                        discovered=current["discovered"],
                        cursor=last,
                    )
                    if current["discovered"] >= params["limit"]:
                        coverage = "article_limit"
                        break
                    if older:
                        coverage = "requested_boundary_reached"
                        break
                    if last == previous_cursor and current["discovered"] == before:
                        coverage = "pagination_stalled"
                        report("alert", code="PAGINATION_STALLED")
                        break
                with database(state) as db, db:
                    db.execute(
                        "UPDATE jobs SET stage='download',coverage=? WHERE job_id=?",
                        (coverage, key),
                    )
            report("stage_duration", stage="discovery", seconds=round(time.monotonic() - start, 6))
            download_started = time.monotonic()
            while True:
                if stopped():
                    raise Stopped()
                denied = sync_denied(state, config)
                with database(state) as db:
                    task = db.execute(
                        "SELECT * FROM tasks WHERE job_id=? AND status='pending' ORDER BY rowid LIMIT 1",
                        (key,),
                    ).fetchone()
                if not task:
                    break
                started = time.monotonic()
                try:
                    markup = client.request(task["url"])
                    with database(state) as db, db:
                        db.execute(
                            "UPDATE tasks SET downloaded=1 WHERE job_id=? AND url=?",
                            (key, task["url"]),
                        )
                    row = extract(markup, task["url"], key)
                    if str(row["id"]) != task["article_id"]:
                        raise ValueError("Identifiant source incohérent.")
                    with database(state) as db:
                        corrected = db.execute(
                            "SELECT payload FROM corrections WHERE article_id=?", (str(row["id"]),)
                        ).fetchone()
                    if corrected:
                        row = json.loads(corrected[0])
                    if str(row["id"]) in denied:
                        status = "suppressed"
                    elif not left <= row["date"] < right or (
                        params["keywords"]
                        and not any(
                            k in (row["title"] + " " + row["text"]).casefold()
                            for k in params["keywords"]
                        )
                    ):
                        status = "filtered"
                    else:
                        with database(state) as db:
                            previous = db.execute(
                                "SELECT revision FROM heads WHERE article_id=?", (str(row["id"]),)
                            ).fetchone()
                        status = (
                            "unchanged"
                            if previous and previous[0] == revision(row)
                            else "updated"
                            if previous
                            else "new"
                        )
                    with database(state) as db, db:
                        db.execute(
                            "UPDATE tasks SET status=?,payload=? WHERE job_id=? AND url=?",
                            (
                                status,
                                json.dumps(row, ensure_ascii=False)
                                if status in ("new", "updated", "unchanged")
                                else None,
                                key,
                                task["url"],
                            ),
                        )
                    report(
                        "article_checkpoint",
                        article_id=row["id"],
                        result=status,
                        duration_s=round(time.monotonic() - started, 3),
                    )
                except Stopped:
                    raise
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    with database(state) as db, db:
                        db.execute(
                            "UPDATE tasks SET status='rejected',error=? WHERE job_id=? AND url=?",
                            (type(exc).__name__, key, task["url"]),
                        )
                    report(
                        "alert",
                        code="ARTICLE_REJECTED",
                        article_id=task["article_id"],
                        error_type=type(exc).__name__,
                    )
                if time.monotonic() - started > config.get("slow_article_seconds", 10):
                    report("alert", code="SLOW_ARTICLE", article_id=task["article_id"])
            report(
                "stage_duration",
                stage="download",
                seconds=round(time.monotonic() - download_started, 6),
            )
            publication_started = time.monotonic()
            current = job(state, key)
            rejects = current["counts"].get("rejected", 0)
            rate = rejects / max(current["discovered"], 1)
            if rate > config.get("max_reject_rate", 0.2):
                with database(state) as db, db:
                    db.execute(
                        "UPDATE jobs SET status='quality_failed',error='QUALITY_BLOCKED' WHERE job_id=?",
                        (key,),
                    )
                report("alert", code="QUALITY_BLOCKED", reject_rate=rate)
                return 0
            sync_denied(state, config)
            with database(state) as db, db:
                for task in db.execute(
                    "SELECT payload FROM tasks WHERE job_id=? AND status IN ('new','updated','unchanged')",
                    (key,),
                ):
                    row = json.loads(task[0])
                    if not db.execute(
                        "SELECT 1 FROM denied WHERE article_id=?", (str(row["id"]),)
                    ).fetchone():
                        put(db, row)
                db.execute("UPDATE jobs SET stage='publish' WHERE job_id=?", (key,))
            manifest = export(state, config, params, key)
            if manifest["articles"]:
                atomic_json(Path(state) / "current.json", manifest)
            with database(state) as db, db:
                db.execute(
                    "UPDATE jobs SET status=?,stage='done',updated=? WHERE job_id=?",
                    ("complete" if manifest["articles"] else "empty", now(), key),
                )
            report(
                "collection_complete", articles=manifest["articles"], coverage=current["coverage"]
            )
            refresh(state)
            report(
                "stage_duration",
                stage="publication",
                seconds=round(time.monotonic() - publication_started, 6),
            )
            return 0
        except Stopped:
            with database(state) as db, db:
                db.execute("UPDATE jobs SET status='paused',updated=? WHERE job_id=?", (now(), key))
            report("collection_paused")
            return 0
        except Exception as exc:
            with database(state) as db, db:
                db.execute(
                    "UPDATE jobs SET status='retryable',error=? WHERE job_id=?",
                    (type(exc).__name__, key),
                )
            report("alert", code="COLLECTION_ERROR", error_type=type(exc).__name__)
            return 1
        finally:
            with database(state) as db, db:
                db.execute(
                    "UPDATE jobs SET work_s=work_s+?,updated=?,started_at=NULL WHERE job_id=?",
                    (time.monotonic() - start, now(), key),
                )
            if job(state, key)["status"] in ("complete", "empty"):
                refresh(state)


if __name__ == "__main__":
    config = json.loads(Path(sys.argv[1]).read_text())
    raise SystemExit(execute(config["state"], sys.argv[2], config))
