"""Bounded or ongoing scheduled runner, automatic worker retries and durable next due time."""

import json
import subprocess
import sys
import time
from pathlib import Path

from .common import alert, atomic_json, event, lock


def supervise(config_path, cycles=1, interval=86400, first_delay=0):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    state = Path(config["state"])
    with lock(state, "scheduler.lock"):
        schedule_file = state / "schedule.json"
        schedule = (
            json.loads(schedule_file.read_text())
            if schedule_file.exists()
            else {"next_due_epoch": time.time() + first_delay, "cycles": 0}
        )
        atomic_json(schedule_file, schedule)
        finished = 0
        while cycles == 0 or finished < cycles:
            time.sleep(max(0, schedule["next_due_epoch"] - time.time()))
            event(
                state,
                "scheduled_trigger",
                due_epoch=schedule["next_due_epoch"],
                trigger_epoch=time.time(),
            )
            for attempt in range(config["max_retries"] + 1):
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "pipeline",
                        "worker",
                        "--config",
                        str(config_path),
                    ]
                )
                event(state, "worker_spawned", pid=process.pid, attempt=attempt + 1)
                result = process.wait()
                if result == 0:
                    if attempt:
                        event(state, "recovery_complete", failed_attempts=attempt)
                    break
                alert(state, "WORKER_EXIT", exit_code=result, attempt=attempt + 1)
                if attempt < config["max_retries"]:
                    time.sleep(min(config["retry_seconds"] * 2**attempt, 60))
            if result:
                alert(state, "RETRIES_EXHAUSTED", exit_code=result)
                return result
            schedule = {
                "next_due_epoch": time.time() + interval,
                "cycles": schedule["cycles"] + 1,
            }
            atomic_json(schedule_file, schedule)
            finished += 1
    return 0
