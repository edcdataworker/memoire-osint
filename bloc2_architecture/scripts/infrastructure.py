"""Deploy the local Compose stack or sample its health without reading secrets."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CORE = ("postgres", "mongo", "app")


class OperationError(RuntimeError):
    """Sanitized failure: command output may contain credentials, so do not relay it."""


def command(args, timeout=180):
    try:
        result = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OperationError(type(exc).__name__) from None
    if result.returncode:
        raise OperationError("command_failed")
    return result.stdout


def compose(*args, timeout=180):
    return command(
        [
            "docker",
            "compose",
            "--project-directory",
            str(ROOT),
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-p",
            "memoire_osint",
            *args,
        ],
        timeout,
    )


def records(raw):
    """Compose versions emit either an array or one JSON object per line."""
    raw = raw.strip()
    if not raw:
        return []
    try:
        rows = (
            json.loads(raw)
            if raw.startswith("[")
            else [json.loads(line) for line in raw.splitlines() if line.strip()]
        )
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("Invalid records")
        return rows
    except (ValueError, TypeError):
        raise OperationError("invalid_command_json") from None


def evaluate(services, metrics, required, memory_percent):
    alerts = []
    by_service = {item["service"]: item for item in services}
    for name in required:
        item = by_service.get(name)
        if item is None:
            alerts.append({"service": name, "reason": "missing"})
        elif item["state"] != "running":
            alerts.append({"service": name, "reason": "not_running"})
        elif item["health"] not in ("", "healthy"):
            alerts.append({"service": name, "reason": "health_" + item["health"]})
    for metric in metrics:
        if float(metric["memory_percent"].rstrip("%")) >= memory_percent:
            alerts.append({"service": metric["service"], "reason": "memory_threshold"})
    return alerts


def snapshot(required, memory_percent):
    services, metrics = [], []
    rows = records(compose("ps", "--all", "--format", "json"))
    # An allowlist discards labels, mount paths and full command lines.
    for row in rows:
        if row["Service"] in required:
            services.append(
                {
                    "service": row["Service"],
                    "state": row["State"],
                    "health": row.get("Health", ""),
                    "id": row["ID"],
                }
            )
    active = [s for s in services if s["state"] == "running"]
    if active:
        raw = command(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{json .}}",
                *[s["id"] for s in active],
            ],
            timeout=30,
        )
        mapping = {s["id"]: s["service"] for s in active}
        for row in records(raw):
            key = row.get("ID", row.get("Container", ""))
            name = next(
                (
                    v
                    for k, v in mapping.items()
                    if k.startswith(key) or key.startswith(k)
                ),
                None,
            )
            if name is None:
                raise OperationError("unmatched_container")
            metrics.append(
                {
                    "service": name,
                    "cpu_percent": row["CPUPerc"],
                    "memory": row["MemUsage"],
                    "memory_percent": row["MemPerc"],
                    "network_cumulative": row["NetIO"],
                    "block_io_cumulative": row["BlockIO"],
                }
            )
        if {m["service"] for m in metrics} != {s["service"] for s in active}:
            raise OperationError("incomplete_metrics")
    alerts = evaluate(services, metrics, required, memory_percent)
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local_compose",
        "required": list(required),
        "memory_threshold_percent": memory_percent,
        "services": services,
        "metrics": metrics,
        "alerts": alerts,
        "ok": not alerts,
    }


def deploy(build=True):
    # No corpus import, volume removal or index replacement is implicit.
    command([sys.executable, "scripts/setup.py"])
    compose("config", "--quiet")
    if build:
        compose("build", "app", timeout=600)
    compose("up", "-d", "--wait", "--wait-timeout", "180", *CORE, timeout=210)
    compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "postgres",
        "-d",
        "osint",
        "-v",
        "ON_ERROR_STOP=1",
        "-f",
        "/docker-entrypoint-initdb.d/02_revisions.sql",
    )
    return snapshot(CORE, 85)


def positive(value):
    value = float(value)
    if not math.isfinite(value) or not 0 < value <= 86400:
        raise argparse.ArgumentTypeError("Value must be > 0 and <= 86400")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    start = sub.add_parser("deploy")
    start.add_argument("--no-build", action="store_true")
    watch = sub.add_parser("monitor")
    watch.add_argument("--samples", type=int, default=1, help="0 means until Ctrl+C")
    watch.add_argument("--interval", type=positive, default=30)
    watch.add_argument("--memory-percent", type=positive, default=85)
    watch.add_argument("--search", action="store_true")
    watch.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "deploy":
        result = deploy(not args.no_build)
        print(json.dumps(result))
        return 0 if result["ok"] else 2
    if args.samples < 0 or args.memory_percent > 100:
        parser.error("samples >= 0; memory-percent <= 100")
    failed, count = False, 0
    while args.samples == 0 or count < args.samples:
        try:
            result = snapshot(
                CORE + (("elasticsearch",) if args.search else ()), args.memory_percent
            )
        except OperationError as exc:
            result = {
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "ok": False,
                "alerts": [{"reason": str(exc)}],
            }
        failed = failed or not result["ok"]
        line = json.dumps(result, ensure_ascii=False)
        print(line, flush=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(args.output, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a") as stream:
                stream.write(line + "\n")
        count += 1
        if args.samples == 0 or count < args.samples:
            time.sleep(args.interval)
    return 2 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OperationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
