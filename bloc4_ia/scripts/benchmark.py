"""Measured throughput and robustness on the exact delivered CPU model."""

import json
import resource
import time
from pathlib import Path
from osint_ner.contracts import read_records, atomic_json, utcnow
from osint_ner.model import Predictor

root = Path(__file__).resolve().parents[1]
rows = list(read_records(root / ".state/inference.jsonl"))
p = Predictor(root / ".state/runs/baseline")
results = []
for n in (10, 50, 200):
    start = time.perf_counter()
    count = sum(1 for _ in p.predict(rows[:n]))
    duration = time.perf_counter() - start
    results.append(
        {
            "documents": count,
            "seconds": round(duration, 4),
            "documents_per_second": round(count / duration, 2),
        }
    )
robust = []
base = rows[0]
for name, text in [
    ("empty", ""),
    ("malformed", 42),
    ("too_long", "x" * 100001),
    ("noise", "\n😀 !!! Kalibr?? NAT0 NATO. " * 20),
    ("long_valid", "Kalibr. " * 5000),
]:
    start = time.perf_counter()
    try:
        data = {**base, "text": text}
        data.pop("text_sha256", None)
        out = list(p.predict([data]))
        robust.append(
            {
                "case": name,
                "status": "processed",
                "entities": len(out[0]["entities"]),
                "seconds": round(time.perf_counter() - start, 3),
            }
        )
    except ValueError as e:
        robust.append({"case": name, "status": "rejected", "error": str(e)})
atomic_json(
    root / "Preuves/benchmark.json",
    {
        "executed_at": utcnow(),
        "model_sha256": p.meta["model_sha256"],
        "threads": 1,
        "processes": 1,
        "measurements": results,
        "robustness": robust,
        "max_rss_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "quality_under_noise": "Not measured without human labels; these are operational robustness checks",
    },
)
print(json.dumps(results))
