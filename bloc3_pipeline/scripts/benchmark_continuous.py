"""Bounded sustained synthetic arrivals through real polling, quality and publication."""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("fixture", ROOT / "tests/continuous.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from pipeline.collection import store
from pipeline.collection.continuous import ContinuousCollector


class Source(fixture.ArrivalSource):
    def __init__(self, batch):
        super().__init__()
        self.batch, self.cycle = batch, 0

    def discover(self, section, cursor, excluded):
        if excluded:
            return {"newsList": [], "lastTime": self.stamp}
        start = max(1, self.cycle * self.batch + 1 - self.batch // 4)
        end = (self.cycle + 1) * self.batch + 1
        rows = [
            {"id": i, "date": self.stamp, "link": f"/defense/{i}"}
            for i in range(start, end)
            if i not in set(excluded)
        ]
        return {"newsList": rows, "lastTime": self.stamp}

    def request(self, url):
        original = super().request(url)
        identifier = url.rsplit("/", 1)[1]
        text = " ".join(hashlib.sha256(f"{identifier}:{i}".encode()).hexdigest() for i in range(32))
        return original.replace("</p>", " " + text + "</p>")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycles", type=int, default=40)
    p.add_argument("--batch", type=int, default=250)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if not 2 <= args.cycles <= 100 or not 1 <= args.batch <= 1000:
        p.error("cycles 2..100, batch 1..1000")
    os.umask(0o077)
    measurements = []
    with tempfile.TemporaryDirectory(prefix="osint-synthetic-flux-") as directory:
        state = Path(directory)
        source = Source(args.batch)
        controller = fixture.FixtureController(
            {"state": directory, "tombstone_files": [], "max_pages": 2}, source
        )
        poll = ContinuousCollector(
            controller,
            {
                "interval_seconds": 0.1,
                "max_cycles": args.cycles,
                "limit": min(2000, args.batch * 2),
            },
        )
        controller.continuous = poll
        started = time.monotonic()
        try:
            for cycle in range(args.cycles):
                source.cycle = cycle
                available = time.monotonic()
                deadline = available + 120
                while poll.snapshot()["completed"] <= cycle:
                    if controller.security_status["permissions_safe"]:
                        poll.tick()
                    if time.monotonic() > deadline:
                        raise RuntimeError("Cycle timeout: " + json.dumps(poll.snapshot()))
                    time.sleep(0.01)
                pointer = json.loads((state / "current.json").read_text())
                expected = (cycle + 1) * args.batch
                if pointer["articles"] != expected:
                    raise AssertionError((expected, pointer))
                measurements.append(
                    {
                        "cycle": cycle + 1,
                        "articles": expected,
                        "availability_to_publication_seconds": round(
                            time.monotonic() - available, 6
                        ),
                    }
                )
                print(json.dumps(measurements[-1]), flush=True)
            elapsed = time.monotonic() - started
            with store.database(state) as db:
                revisions = db.execute("SELECT count(*) FROM revisions").fetchone()[0]
            assert revisions == args.cycles * args.batch, "Overlap created redundant revisions"
            result = {
                "synthetic": True,
                "network_requests": 0,
                "python": platform.python_version(),
                "cycles": args.cycles,
                "articles": revisions,
                "seconds": round(elapsed, 6),
                "articles_per_second": round(revisions / elapsed, 3),
                "overlap_per_cycle": args.batch // 4,
                "measurements": measurements,
                "final_schedule": poll.snapshot(),
                "limits": "Injected fictional source, approximately 2 KiB bodies, one local host; no TASS throughput or hard realtime guarantee.",
                "code_sha256": {
                    str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
                    for f in sorted((ROOT / "pipeline/collection").glob("*.py"))
                },
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
        finally:
            controller.stop_server.set()
            deadline = time.monotonic() + 130
            while controller.active and time.monotonic() < deadline:
                time.sleep(0.02)
            if controller.active:
                raise RuntimeError("Worker did not stop before cleanup")


if __name__ == "__main__":
    main()
