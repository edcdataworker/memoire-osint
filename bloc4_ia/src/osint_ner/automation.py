"""Bounded polling scheduler: changed inputs trigger a candidate automatically."""

import json
import time
from pathlib import Path

from .contracts import atomic_json, digest, file_sha, read_records, utcnow
from .model import train
from .registry import promote


def watch(train_path, dev_path, state, cycles=1, interval=60, demo=False, epochs=3):
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    lock = state / "scheduler.lock"
    # Exclusive creation prevents concurrent jobs overwriting a candidate.
    with lock.open("x") as f:
        f.write(utcnow())
    failed_cycles = 0
    try:
        status_path = state / "scheduler.json"
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
        for cycle in range(cycles):
            event = {"at": utcnow(), "cycle": cycle, "trigger": "input_sha256_poll"}
            try:
                version = digest(file_sha(train_path) + file_sha(dev_path))
                if version == status.get("last_successful_input"):
                    event.update(action="unchanged_skip")
                else:
                    rows = list(read_records(train_path))
                    if not demo and any(
                        r.get("annotation_status") != "human_reviewed"
                        or not r.get("reviewer")
                        or not r.get("reviewed_at")
                        for r in rows
                    ):
                        raise ValueError("Automatic retraining requires reviewed training labels")
                    run = state / "runs" / f"{version[:12]}-{time.time_ns()}"
                    report = train(train_path, dev_path, run, epochs=epochs)
                    decision = promote(run, state / "registry", environment="production")
                    event.update(
                        action="candidate_trained",
                        duration_seconds=report["duration_seconds"],
                        model_version=report["model_version"],
                        model_sha256=report["model_sha256"],
                        run=str(run),
                        production_promotion=decision,
                        demo_mode=demo,
                    )
                    status = {
                        "last_successful_input": version,
                        "last_run": str(run),
                        "at": utcnow(),
                    }
                    atomic_json(status_path, status)
            except Exception as exc:  # Operational failures are recorded; interrupts propagate.
                failed_cycles += 1
                event.update(action="failed", error_type=type(exc).__name__, error=str(exc))
                atomic_json(state / "alert.json", event)
            with (state / "events.jsonl").open("a") as f:
                f.write(json.dumps(event) + "\n")
                f.flush()
            if cycle + 1 < cycles:
                time.sleep(interval)
    finally:
        lock.unlink(missing_ok=True)
    if failed_cycles:
        raise ValueError(
            f"Scheduler recorded {failed_cycles} failed cycle(s); inspect events.jsonl and alert.json"
        )
    return status
