"""Measured JSON/JSONL volumes and raw/clean equivalence, with explicit data provenance."""

import json
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.__main__ import DEFAULTS
from pipeline.common import atomic_json, now

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".bench" / str(time.time_ns())
BASE.mkdir(parents=True, exist_ok=True)


def benchmark(source, state, mode, synthetic):
    config = DEFAULTS | {
        "source": str(source),
        "state": str(state),
        "mode": mode,
        "synthetic": synthetic,
    }
    path = BASE / (state.name + ".json")
    atomic_json(path, config)
    start = time.perf_counter()
    with (ROOT / "Preuves" / (state.name + ".jsonl")).open("w") as output:
        proc = subprocess.run(
            [sys.executable, "-m", "pipeline", "worker", "--config", str(path)],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
    elapsed = time.perf_counter() - start
    if proc.returncode:
        raise RuntimeError(f"Benchmark failed: {state}")
    d = json.loads((state / "last_result.json").read_text())
    return {
        "data_kind": "synthetic" if synthetic else "real_TASS",
        "format": source.suffix,
        "input_mode": mode,
        "input_records": d["checkpoint"],
        "accepted": d["accepted"],
        "rejected": d["rejected"],
        "duplicates": d["duplicates"],
        "duration_end_to_end_s": round(elapsed, 6),
        "rows_per_second_end_to_end": round(d["checkpoint"] / elapsed, 2),
        "source_sha256": d["source_sha256"],
        "run_id": d["run_id"],
        "batch_size": config["batch_size"],
        "source_bytes": source.stat().st_size,
        "state": str(state),
        "publication": d["publication"],
    }


results = []
for size, fmt in [
    (1000, "jsonl"),
    (10000, "jsonl"),
    (100000, "jsonl"),
    (10000, "json"),
]:
    source = BASE / f"synthetic-{size}.{fmt}"
    with source.open("w") as stream:
        if fmt == "json":
            stream.write("[")
        for i in range(size):
            row = {
                "id": f"bench-{i}",
                "date": 1700000000 + i,
                "title": f"Synthetic {i}",
                "text": (
                    f"Synthetic article {i}. "
                    + ("Military equipment in a fictional training area. " * 8)
                ).strip(),
                "url": f"https://example.invalid/{i}",
            }
            if fmt == "json" and i:
                stream.write(",")
            stream.write(json.dumps(row) + ("\n" if fmt == "jsonl" else ""))
        if fmt == "json":
            stream.write("]")
    results.append(benchmark(source, BASE / f"state-{size}-{fmt}", "clean", True))
raw = ROOT.parent / "00_Pilotage/Sources/Artefacts_recuperes/data_set.json"
results.append(benchmark(raw, BASE / "state-real-raw", "raw", False))
clean = json.load(
    open(ROOT.parent / "00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json")
)
manifest = results[-1]["publication"]
actual = json.load(open(manifest["json"]))
checks = {
    "raw_count_21742": results[-1]["input_records"] == 21742,
    "empty_rejects_66": results[-1]["rejected"] == 66,
    "clean_count_21676": len(actual) == 21676,
    "ids_dates_texts_match_reconstituted": [(r["id"], r["date"], r["text"]) for r in actual]
    == [(r["id"], r["date"], r["text"]) for r in clean],
    "empty_titles_preserved": sum(not r["title"] for r in actual) == 6,
}
assert all(checks.values()), checks
rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
report = {
    "at": now(),
    "environment": {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "maximum_child_rss_bytes_macos": rss,
    },
    "results": results,
    "raw_clean_checks": checks,
    "limitations": [
        "Single measured run per size, no statistical repetitions.",
        "Synthetic articles have short repeated vocabulary, unlike TASS distribution.",
        "Duration includes hashing, parsing, transactional storage, two exports and local mirrors; excludes input fixture generation.",
        "Peak RSS is the maximum reported for child processes across tests, not a per-run sample.",
    ],
}
atomic_json(ROOT / "Preuves" / "Benchmark_pipeline.json", report)
print(
    json.dumps(
        {
            "checks": checks,
            "measurements": [
                {k: v for k, v in r.items() if k not in ("publication", "state")} for r in results
            ],
        },
        indent=2,
    )
)
