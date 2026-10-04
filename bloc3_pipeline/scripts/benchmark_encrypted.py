"""Compare empty and populated encrypted catalogs without changing the live corpus."""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark_collection import BenchmarkSource

from pipeline.collection import security, store
from pipeline.collection.source import bounds, parameters
from pipeline.collection.worker import execute
from pipeline.common import atomic_json, now, private_dir, sha256

DATE = "1999-11-26"
OFFSET = 9_000_000_000


def fingerprint(state):
    """Stable catalog identity independent of audit entries and SQLite layout."""
    digest = hashlib.sha256()
    with store.database(state) as db:
        for row in db.execute("SELECT article_id,revision FROM heads ORDER BY article_id"):
            digest.update(json.dumps(list(row), separators=(",", ":")).encode() + b"\n")
        count = db.execute("SELECT count(*) FROM heads").fetchone()[0]
        assert db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    return {"heads": count, "heads_sha256": digest.hexdigest(), "integrity": "ok"}


class EncryptedSource(BenchmarkSource):
    def __init__(self, size):
        super().__init__(size)
        self.base = bounds(DATE, DATE)[0] + 43200

    def discover(self, section, cursor, excluded):
        result = super().discover(section, cursor, excluded)
        for row in result["newsList"]:
            row["id"] += OFFSET
            row["link"] = f"/defense/{row['id']}"
        return result

    def request(self, url):
        # Preserve exactly the historical body's size distribution, replacing only
        # the date and identifier. No request is sent to these fictional URLs.
        identifier = int(url.rsplit("/", 1)[1])
        before = self.source_bytes
        html = super().request(f"https://tass.com/defense/{identifier - OFFSET}")
        html = html.replace("2023-11-26", DATE)
        self.source_bytes = before + len(html.encode())
        return html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    assert security.encrypted_volume(args.state), "Production state must be encrypted"
    assert security.encrypted_volume(args.directory), "Benchmark must stay encrypted"
    os.umask(0o077)
    private_dir(args.directory)
    proof = ROOT / "Preuves/Collecte_TASS"
    baseline = fingerprint(args.state)
    store_sha = sha256(ROOT / "pipeline/collection/store.py")
    worker_sha = sha256(ROOT / "pipeline/collection/worker.py")
    config = json.loads((args.state / "config.json").read_text())
    results = []
    (proof / "Benchmark_chiffre.log").write_text("")
    (proof / "Benchmark_chiffre_progress.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="isolated-", dir=args.directory) as directory:
        directory = Path(directory)
        seed = directory / "seed.sqlite"
        with store.database(args.state) as source, sqlite3.connect(seed) as target:
            source.backup(target)
        seed_sha = sha256(seed)
        tombstones = directory / "erasures.json"
        atomic_json(tombstones, sorted(store.external_denied(args.state, config)))
        with sqlite3.connect(seed) as db:
            assert (
                db.execute(
                    "SELECT count(*) FROM revisions WHERE published>=? AND published<?",
                    bounds(DATE, DATE),
                ).fetchone()[0]
                == 0
            ), "Synthetic date must be absent from baseline"
            assert (
                db.execute(
                    "SELECT count(*) FROM heads WHERE CAST(article_id AS INTEGER)>=?", (OFFSET,)
                ).fetchone()[0]
                == 0
            ), "Synthetic identifiers must be disjoint"
        for size in (100, 1000, 2000):
            for repetition in range(1, 4):
                # Alternate order to reduce a systematic warm-cache ordering bias.
                modes = ("empty", "populated") if repetition % 2 else ("populated", "empty")
                for mode in modes:
                    state = directory / "run"
                    private_dir(state)
                    if mode == "populated":
                        shutil.copy2(seed, state / "collection.sqlite")
                        rights = args.state / "rights.json"
                        if rights.exists():
                            shutil.copy2(rights, state / "rights.json")
                    store.initialize(state)
                    with store.database(state) as db:
                        plan = [
                            r[3]
                            for r in db.execute(
                                "EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE job_id=? AND status='pending' ORDER BY rowid LIMIT 1",
                                ("fixture",),
                            )
                        ]
                    assert not any("TEMP B-TREE" in step for step in plan), plan
                    with store.database(state) as db:
                        rights_plan = [
                            r[3]
                            for r in db.execute(
                                "EXPLAIN QUERY PLAN UPDATE tasks SET status='suppressed',payload=NULL WHERE article_id=?",
                                ("fixture",),
                            )
                        ]
                    assert not any("SCAN tasks" in step for step in rights_plan), rights_plan
                    expected = baseline["heads"] if mode == "populated" else 0
                    assert fingerprint(state)["heads"] == expected
                    params = parameters(dict(section="defense", start=DATE, end=DATE, limit=size))
                    isolated_config = dict(
                        state=str(state), tombstone_files=[str(tombstones)], max_pages=30
                    )
                    source = EncryptedSource(size)
                    started = time.perf_counter()
                    with (
                        (proof / "Benchmark_chiffre.log").open("a") as log,
                        contextlib.redirect_stdout(log),
                    ):
                        key = store.new_job(state, params)
                        assert execute(state, key, isolated_config, source) == 0
                    elapsed = time.perf_counter() - started
                    current = store.job(state, key)
                    assert current["validated"] == size and current["status"] == "complete", current
                    assert fingerprint(state)["heads"] == expected + size
                    with store.database(state) as db:
                        stages = {
                            json.loads(r[0])["stage"]: json.loads(r[0])["seconds"]
                            for r in db.execute(
                                "SELECT fields FROM events WHERE job_id=? AND kind='stage_duration'",
                                (key,),
                            )
                        }
                    export = state / "exports" / key
                    rows = json.loads((export / "articles.json").read_text())
                    lines = [
                        json.loads(v) for v in (export / "articles.jsonl").read_text().splitlines()
                    ]
                    assert rows == lines and len(rows) == size
                    assert all(OFFSET < row["id"] <= OFFSET + size for row in rows)
                    assert all(
                        hashlib.sha256(row["text"].encode()).hexdigest() == row["text_sha256"]
                        for row in rows
                    )
                    result = dict(
                        mode=mode,
                        baseline_heads=expected,
                        articles=size,
                        repetition=repetition,
                        seconds=round(elapsed, 6),
                        articles_per_second=round(size / elapsed, 2),
                        stage_seconds=stages,
                        source_bytes=source.source_bytes,
                        catalog_bytes=(state / "collection.sqlite").stat().st_size,
                        export_bytes=sum(
                            (export / ("articles." + k)).stat().st_size for k in ("json", "jsonl")
                        ),
                        mirror_bytes=(state / "mirror/catalog.sqlite").stat().st_size,
                        json_jsonl_equal=True,
                        text_hashes_correct=True,
                    )
                    results.append(result)
                    print(json.dumps(result), flush=True)
                    atomic_json(
                        proof / "Benchmark_chiffre_progress.json", {"at": now(), "results": results}
                    )
                    shutil.rmtree(state)
        assert sha256(seed) == seed_sha
    after = fingerprint(args.state)
    assert after == baseline, "Live catalog changed during benchmark"
    summary = []
    for mode in ("empty", "populated"):
        for size in (100, 1000, 2000):
            subset = [r for r in results if r["mode"] == mode and r["articles"] == size]
            times = [r["seconds"] for r in subset]
            summary.append(
                dict(
                    mode=mode,
                    articles=size,
                    median_s=statistics.median(times),
                    min_s=min(times),
                    max_s=max(times),
                    stdev_s=statistics.stdev(times),
                    median_articles_per_second=round(size / statistics.median(times), 2),
                    median_stage_s={
                        stage: statistics.median(r["stage_seconds"][stage] for r in subset)
                        for stage in ("discovery", "download", "publication")
                    },
                )
            )
    atomic_json(
        proof / "Benchmark_chiffre.json",
        dict(
            at=now(),
            python=platform.python_version(),
            platform=platform.platform(),
            worker_sha256=worker_sha,
            store_sha256=store_sha,
            pending_task_query_plan=plan,
            rights_task_query_plan=rights_plan,
            script_sha256=sha256(Path(__file__)),
            storage="Mounted AES-256 APFS disk image, same Mac",
            baseline=baseline,
            after=after,
            live_catalog_unchanged=True,
            results=results,
            summary=summary,
            methodology="18 runs, three repetitions per size/mode; alternating mode order; fresh SQLite snapshot for each populated run; initialization and copying excluded; timed new_job through execute including checkpointing, export and full-catalog mirror; no network requests; approximately 1/10/50 KiB synthetic HTML bodies; export date absent from baseline; isolated copies deleted on encrypted volume",
            limitations=[
                "Shared Mac and filesystem cache, not a controlled hardware laboratory",
                "No isolated estimate of encryption overhead; both compared modes encrypted",
                "No network throughput, SLA or extrapolation beyond 2000 candidates",
                "Full populated catalog copied to mirror at each publication; initialization excluded from timings",
            ],
        ),
    )
    (proof / "Benchmark_chiffre_progress.json").unlink()


if __name__ == "__main__":
    main()
