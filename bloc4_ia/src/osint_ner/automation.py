"""Bounded polling scheduler: changed inputs trigger a candidate automatically."""

import json
import time
from pathlib import Path

from .contracts import atomic_json, digest, file_sha, read_records, utcnow, write_records
from .model import train, evaluate, Predictor
from .monitor import monitor
from .registry import promote


def watch(
    train_path,
    dev_path,
    state,
    cycles=1,
    interval=60,
    demo=False,
    epochs=3,
    reference=None,
    manifest=None,
    current=None,
    delivery=None,
):
    if cycles < 1 or interval < 0 or epochs < 1:
        raise ValueError("Positive cycles and epochs, nonnegative interval required")
    if bool(reference) != bool(manifest):
        raise ValueError("Evaluation requires both reference and frozen manifest")
    if delivery and (not reference or not current or demo):
        raise ValueError("Automatic model delivery requires reviewed evaluation and monitoring")
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
                version = digest(
                    json.dumps(
                        {
                            "train": file_sha(train_path),
                            "dev": file_sha(dev_path),
                            "reference": file_sha(reference) if reference else None,
                            "manifest": file_sha(manifest) if manifest else None,
                            "current": file_sha(current) if current else None,
                            "epochs": epochs,
                            "demo": demo,
                            "delivery_config": file_sha(delivery) if delivery else None,
                        },
                        sort_keys=True,
                    )
                )
                if version == status.get("last_successful_input"):
                    event.update(action="unchanged_skip")
                else:
                    rows = list(read_records(train_path))
                    dev_rows = list(read_records(dev_path))
                    if not demo and (
                        not rows
                        or not dev_rows
                        or any(
                            r.get("annotation_status") != "human_reviewed"
                            or not r.get("reviewer")
                            or not r.get("reviewed_at")
                            for r in rows + dev_rows
                        )
                    ):
                        raise ValueError(
                            "Automatic retraining requires reviewed train and dev labels"
                        )
                    run = state / "runs" / f"{version[:12]}-{time.time_ns()}"
                    report = train(train_path, dev_path, run, epochs=epochs)
                    quality = evaluate(run, reference, manifest) if reference else None
                    if quality:
                        atomic_json(run / "evaluation.json", quality)
                    previous_quality = None
                    pointer = state / "registry/production.json"
                    if quality and pointer.exists():
                        previous = json.loads(pointer.read_text())
                        previous_quality = evaluate(previous["candidate"], reference, manifest)
                    monitoring = (
                        monitor(
                            rows,
                            list(read_records(current)),
                            run / "monitor.json",
                            previous_quality,
                            quality,
                        )
                        if current
                        else None
                    )
                    frozen = bool(monitoring and monitoring["action"] != "observe")
                    previous_pointer = json.loads(pointer.read_text()) if pointer.exists() else None
                    decision = promote(
                        run,
                        state / "registry",
                        environment="production",
                        quality=quality,
                        frozen=frozen,
                    )
                    delivered = None
                    if decision["accepted"] and delivery:
                        from .deployment import deploy
                        from .export import exclusions

                        try:
                            config = json.loads(Path(delivery).read_text())
                            excluded = exclusions(config["exclusions"])
                            serving_data = run / "serving.jsonl"
                            source_rows = (
                                r
                                for r in read_records(config["data_source"])
                                if str(r["id"]) not in excluded
                            )
                            predictor = Predictor(run)

                            def predictions():
                                batch = []
                                for row in source_rows:
                                    batch.append(row)
                                    if len(batch) == 32:
                                        yield from predictor.predict(batch)
                                        batch = []
                                if batch:
                                    yield from predictor.predict(batch)

                            write_records(serving_data, predictions())
                            delivered = deploy(
                                config["wheel"],
                                serving_data,
                                run,
                                config["state"],
                                config.get("port", 8766),
                            )
                        except Exception:
                            if previous_pointer:
                                atomic_json(pointer, previous_pointer)
                            else:
                                pointer.unlink(missing_ok=True)
                            with (state / "registry/events.jsonl").open("a") as log:
                                log.write(
                                    json.dumps(
                                        {
                                            "action": "delivery_failed_registry_restored",
                                            "candidate": str(run),
                                            "at": utcnow(),
                                        }
                                    )
                                    + "\n"
                                )
                            raise
                    event.update(
                        action="candidate_trained",
                        duration_seconds=report["duration_seconds"],
                        model_version=report["model_version"],
                        model_sha256=report["model_sha256"],
                        run=str(run),
                        production_promotion=decision,
                        evaluation=quality,
                        monitoring=monitoring,
                        delivery=delivered,
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
