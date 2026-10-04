"""Three repetitions per bounded collector workload; no external network requests."""

import contextlib
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.collection import store
from pipeline.collection.source import bounds, parameters
from pipeline.collection.worker import execute
from pipeline.common import atomic_json, now


class BenchmarkSource:
    def __init__(self, size):
        self.size = size
        self.base = bounds("2023-11-26", "2023-11-26")[0] + 43200
        self.source_bytes = 0

    def initialize(self, section):
        return 4953

    def discover(self, section, cursor, excluded):
        items = [
            {"id": i, "date": self.base + self.size - i, "link": f"/defense/{i}"}
            for i in range(1, self.size + 1)
            if self.base + self.size - i <= cursor
        ][:100]
        return {"newsList": items, "lastTime": items[-1]["date"] - 1 if items else cursor}

    def request(self, url):
        i = int(url.rsplit("/", 1)[1])
        length = (1024, 10240, 51200)[i % 3]
        text = f"Synthetic article {i}. " + "Fictional equipment in a training area. " * (
            length // 39
        )
        meta = {
            "@type": "NewsArticle",
            "headline": f"Fixture {i}",
            "datePublished": "2023-11-26T12:00:00Z",
        }
        html = (
            '<script type="application/ld+json">'
            + json.dumps(meta)
            + '</script><div class="text-content"><div class="text-block"><p>'
            + text
            + "</p></div></div>"
        )
        self.source_bytes += len(html.encode())
        return html


def main():
    results = []
    proof = ROOT / "Preuves/Collecte_TASS"
    proof.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="memoire-benchmark-") as directory:
        for size in (100, 1000, 2000):
            for repetition in range(1, 4):
                state = Path(directory) / f"{size}-{repetition}"
                store.initialize(state)
                config = {"state": str(state), "tombstone_files": [], "max_pages": 30}
                params = parameters(
                    {
                        "section": "defense",
                        "start": "2023-11-26",
                        "end": "2023-11-26",
                        "limit": size,
                    }
                )
                source = BenchmarkSource(size)
                started = time.perf_counter()
                with (
                    (proof / "Benchmark_collecteur.log").open("a") as log,
                    contextlib.redirect_stdout(log),
                ):
                    key = store.new_job(state, params)
                    assert execute(state, key, config, source) == 0
                elapsed = time.perf_counter() - started
                current = store.job(state, key)
                assert current["validated"] == size, current
                with store.database(state) as db:
                    stages = {
                        json.loads(r[0])["stage"]: json.loads(r[0])["seconds"]
                        for r in db.execute(
                            "SELECT fields FROM events WHERE job_id=? AND kind='stage_duration'",
                            (key,),
                        )
                    }
                rows = json.loads((state / "exports" / key / "articles.json").read_text())
                lines = [
                    json.loads(line)
                    for line in (state / "exports" / key / "articles.jsonl")
                    .read_text()
                    .splitlines()
                ]
                assert rows == lines and len(rows) == size
                assert all(
                    hashlib.sha256(row["text"].encode()).hexdigest() == row["text_sha256"]
                    for row in rows
                )
                results.append(
                    {
                        "articles": size,
                        "repetition": repetition,
                        "seconds": round(elapsed, 6),
                        "articles_per_second": round(size / elapsed, 2),
                        "source_bytes": source.source_bytes,
                        "stage_seconds": stages,
                        "json_jsonl_equal": True,
                        "text_hashes_correct": True,
                    }
                )
                print(json.dumps(results[-1]), flush=True)
    summary = [
        {
            "articles": size,
            "median_s": statistics.median(r["seconds"] for r in results if r["articles"] == size),
            "min_s": min(r["seconds"] for r in results if r["articles"] == size),
            "max_s": max(r["seconds"] for r in results if r["articles"] == size),
        }
        for size in (100, 1000, 2000)
    ]
    atomic_json(
        proof / "Benchmark_collecteur.json",
        {
            "at": now(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "data": "synthetic HTML, approximately 1/10/50 KiB bodies",
            "results": results,
            "summary": summary,
            "limitations": [
                "No network throughput claim; no production SLA.",
                "Single shared Mac; nine measured runs.",
                "Temporary fixture storage; encrypted-volume performance has not been measured.",
            ],
        },
    )


if __name__ == "__main__":
    main()
