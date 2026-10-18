"""Validate the star in a disposable, network-isolated PostgreSQL with fictional rows."""

import argparse
import hashlib
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = (
    "postgres@sha256:081f1bc7bd5e143dbb6e487b710bbc27712cdcfaced4c071b8e47349aa1b4171"
)


def docker(*args, **kwargs):
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, **kwargs
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    name = "memoire-star-fixture-" + uuid.uuid4().hex[:12]
    docker(
        "run",
        "-d",
        "--name",
        name,
        "--network",
        "none",
        "--memory",
        "768m",
        "--cpus",
        "1",
        "--tmpfs",
        "/var/lib/postgresql/data:rw,size=512m",
        "-e",
        "POSTGRES_HOST_AUTH_METHOD=trust",
        "-e",
        "POSTGRES_DB=osint",
        IMAGE,
    )
    started = time.monotonic()
    try:
        for _ in range(100):
            ready = subprocess.run(
                ["docker", "exec", name, "pg_isready", "-U", "postgres", "-d", "osint"],
                capture_output=True,
            )
            main_process = docker("exec", name, "cat", "/proc/1/comm").stdout.strip()
            if ready.returncode == 0 and main_process == "postgres":
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("Isolated PostgreSQL did not become ready")

        def sql(code):
            return docker(
                "exec",
                "-i",
                name,
                "psql",
                "-X",
                "-q",
                "-t",
                "-A",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "postgres",
                "-d",
                "osint",
                input=code,
            ).stdout

        sql("CREATE ROLE osint_writer; CREATE ROLE osint_reader;")
        sources = [
            "sql/01_schema.sql",
            "sql/02_revisions.sql",
            "sql/03_analytics_star.sql",
            "tests/star_schema.sql",
        ]
        for path in sources[:3]:
            sql((ROOT / path).read_text())
        sql((ROOT / sources[2]).read_text())
        output = sql((ROOT / sources[3]).read_text())
        cases = [
            line.removeprefix("PASS:")
            for line in output.splitlines()
            if line.startswith("PASS:")
        ]
        assert cases == [
            "grain",
            "utc",
            "joins",
            "exclusion",
            "revision",
            "reader",
            "writer",
            "deletion",
        ], output
        sql((ROOT / "docs/analytics_example.sql").read_text())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result = {
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
            "network": "none",
            "host_ports": [],
            "image": IMAGE,
            "tests": len(cases),
            "passed": cases,
            "migration_reapplied": True,
            "example_query_executed": True,
            "duration_seconds": round(time.monotonic() - started, 3),
            "scope": "Fresh isolated PostgreSQL; five fictional current articles plus one revision. No active VM or existing database changed.",
            "code_sha256": {
                path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                for path in sources
                + ["docs/analytics_example.sql", "scripts/verify_star_schema.py"]
            },
        }
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        docker("rm", "-f", name)


if __name__ == "__main__":
    main()
