"""Course load tests with real Docker metrics, no extrapolated success claims."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "Preuves"


def run(args, **kw):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, **kw)


def collect(stop, path):
    with path.open("w") as f:
        while not stop.is_set():
            ids = (
                run(["ps", "-q", "postgres", "mongo", "ops"], stdout=subprocess.PIPE)
                .stdout.decode()
                .split()
            )
            if ids:
                result = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format", "{{json .}}", *ids],
                    capture_output=True,
                    text=True,
                )
                for line in result.stdout.splitlines():
                    value = json.loads(line)
                    value["observed_at"] = datetime.now(timezone.utc).isoformat()
                    f.write(json.dumps(value) + "\n")
                    f.flush()
            stop.wait(3)


def main():
    results = []
    for size in (60000, 600000, 6000000):
        if shutil.disk_usage(ROOT).free < 10 * 1024**3:
            raise RuntimeError("Less than 10 GiB free; do not continue the load test")
        # Only synthetic documents are reset. The real corpus remains untouched.
        cleanup = "from osint.storage import pg,mongo; c=pg(); c.execute('DELETE FROM articles WHERE synthetic=true');c.commit();mongo().documents.delete_many({'synthetic':True});print('synthetic reset')"
        run(
            ["run", "--rm", "-T", "ops", "python", "-c", cleanup],
            stdout=subprocess.DEVNULL,
        )
        stop = threading.Event()
        thread = threading.Thread(
            target=collect, args=(stop, EVIDENCE / f"stats_{size}.jsonl")
        )
        thread.start()
        begin = time.perf_counter()
        try:
            with (
                (EVIDENCE / f"benchmark_{size}.jsonl").open("w") as out,
                (EVIDENCE / f"benchmark_{size}.stderr").open("w") as err,
            ):
                run(
                    [
                        "run",
                        "--rm",
                        "-T",
                        "ops",
                        "python",
                        "-m",
                        "osint.cli",
                        "ingest",
                        "--synthetic",
                        str(size),
                    ],
                    stdout=out,
                    stderr=err,
                )
        finally:
            stop.set()
            thread.join()
        wall = time.perf_counter() - begin
        count_code = "from osint.storage import pg,mongo;import json,time;c=pg(); t=time.perf_counter();p=c.execute('SELECT count(*) FROM articles WHERE synthetic=true').fetchone()[0];q=time.perf_counter()-t;m=mongo().documents.count_documents({'synthetic':True});print(json.dumps({'postgres':p,'mongo':m,'count_query_s':q}))"
        check = run(
            ["run", "--rm", "-T", "ops", "python", "-c", count_code],
            stdout=subprocess.PIPE,
        ).stdout.decode()
        counts = json.loads(check.strip().splitlines()[-1])
        assert counts["postgres"] == counts["mongo"] == size
        event = json.loads(
            (EVIDENCE / f"benchmark_{size}.jsonl").read_text().splitlines()[-1]
        )
        event.update(
            {
                "wall_s": round(wall, 3),
                "rows_per_s": round(size / event["duration_s"], 2),
                "counts": counts,
                "stores_tested": ["PostgreSQL", "MongoDB"],
                "elasticsearch_tested_at_this_volume": False,
            }
        )
        results.append(event)
        (EVIDENCE / "benchmarks.json").write_text(json.dumps(results, indent=2))
        print(json.dumps(event), flush=True)


if __name__ == "__main__":
    main()
