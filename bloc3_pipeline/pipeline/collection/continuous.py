"""Durable polling cycles reuse the collector's checkpoints and quality gate."""

import hashlib
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

from . import resilience, store
from .source import parameters

DEFAULTS = {
    "section": "defense",
    "lookback_days": 2,
    "limit": 200,
    "interval_seconds": 60,
    "max_cycles": 0,
    "max_failures": 3,
    "retry_seconds": 10,
    "freshness_seconds": 300,
}


def options(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError("Configuration de collecte continue invalide.")
    result = DEFAULTS | value
    for key, low, high in [
        ("lookback_days", 1, 30),
        ("limit", 1, 2000),
        ("max_cycles", 0, 1000000),
        ("max_failures", 1, 10),
    ]:
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError(f"Paramètre de collecte continue invalide : {key}")
    for key in ("interval_seconds", "retry_seconds", "freshness_seconds"):
        if type(result[key]) not in (int, float) or not 0.1 <= result[key] <= 86400:
            raise ValueError(f"Délai de collecte continue invalide : {key}")
    parameters(
        {
            "section": result["section"],
            "start": "2026-01-01",
            "end": "2026-01-01",
            "limit": result["limit"],
        }
    )
    return result


class ContinuousCollector:
    def __init__(self, controller, config):
        self.controller, self.state = controller, controller.state
        self.config = options(config)
        self.guard = threading.Lock()
        self.started = False
        self.initialize()

    def initialize(self):
        if resilience.backend(self.state)[1] != "primary":
            return
        fingerprint = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest()
        with store.database(self.state) as db, db:
            saved = db.execute("SELECT * FROM poll_schedule WHERE singleton=1").fetchone()
            if saved and saved["config_sha256"] == fingerprint:
                return
            if saved and saved["config_sha256"] != fingerprint:
                if saved["pending_job"]:
                    raise ValueError("Terminer la collecte en attente avant de changer sa cadence.")
                db.execute("DELETE FROM poll_schedule WHERE singleton=1")
            db.execute(
                "INSERT OR IGNORE INTO poll_schedule(singleton,config_sha256,next_due) "
                "VALUES(1,?,?)",
                (fingerprint, time.time()),
            )

    def snapshot(self):
        backend = resilience.backend(self.state)[1]
        try:
            with store.read_database(self.state) as db:
                row = db.execute("SELECT * FROM poll_schedule WHERE singleton=1").fetchone()
        except sqlite3.OperationalError:
            row = None
        if row is None:
            return {"enabled": True, "runner_active": self.started, "status": "storage_blocked"}
        value = dict(row)
        stamp = time.time()
        value.update(
            enabled=True,
            runner_active=self.started,
            interval_seconds=self.config["interval_seconds"],
            lookback_days=self.config["lookback_days"],
            seconds_until_next=round(max(0, value["next_due"] - stamp), 3),
            success_age_seconds=round(stamp - value["last_success"], 3)
            if value["last_success"]
            else None,
            mode="periodic_microbatches_no_hard_realtime_guarantee",
            storage_backend=backend,
        )
        if backend != "primary":
            value["status"] = "storage_blocked"
        return value

    def update(self, **values):
        with store.database(self.state) as db, db:
            db.execute(
                "UPDATE poll_schedule SET "
                + ",".join(k + "=?" for k in values)
                + " WHERE singleton=1",
                tuple(values.values()),
            )

    def tick(self, stamp=None):
        stamp = time.time() if stamp is None else stamp
        with self.guard:
            resilience.require_primary(self.state)
            status = self.controller.security_status
            if not status["permissions_safe"] or (
                status["encryption_required"] and not status["encrypted_volume"]
            ):
                raise OSError("La collecte continue exige un stockage protégé.")
            self.initialize()
            with store.database(self.state) as db:
                schedule = dict(
                    db.execute("SELECT * FROM poll_schedule WHERE singleton=1").fetchone()
                )
            key = schedule["pending_job"]
            if key:
                job = store.job(self.state, key)
                if job["status"] in ("complete", "empty"):
                    completed = schedule["completed"] + 1
                    finished = bool(
                        self.config["max_cycles"] and completed >= self.config["max_cycles"]
                    )
                    duration = max(0, stamp - datetime.fromisoformat(job["created"]).timestamp())
                    partial = job["coverage"] in (
                        "article_limit",
                        "page_limit",
                        "pagination_stalled",
                    )
                    self.update(
                        pending_job=None,
                        completed=completed,
                        failures=0,
                        status="finished"
                        if finished
                        else "coverage_limited"
                        if partial
                        else "waiting",
                        next_due=stamp + self.config["interval_seconds"],
                        last_success=stamp,
                        last_job=key,
                        last_duration=duration,
                        stale_alert=0,
                    )
                    store.emit(
                        self.state,
                        key,
                        "poll_cycle_complete",
                        cycles=completed,
                        seconds=round(duration, 6),
                        **job["counts"],
                    )
                    if partial:
                        store.emit(
                            self.state,
                            key,
                            "alert",
                            code="POLL_COVERAGE_LIMITED",
                            coverage=job["coverage"],
                        )
                    return
                if job["status"] in ("paused", "quality_failed"):
                    self.update(status="paused" if job["status"] == "paused" else "quality_blocked")
                    return
                if self.controller.active:
                    age = stamp - datetime.fromisoformat(job["updated"]).timestamp()
                    if age > self.config["freshness_seconds"] and not schedule["stale_alert"]:
                        store.emit(
                            self.state, key, "alert", code="POLL_STALLED", seconds=round(age, 3)
                        )
                        self.update(stale_alert=1)
                    return
                if job["status"] in ("failed", "retryable"):
                    if schedule["status"] != "retry_wait":
                        if schedule["failures"] >= self.config["max_failures"]:
                            self.update(status="failed")
                            return
                        failures = schedule["failures"] + 1
                        self.update(
                            status="retry_wait",
                            failures=failures,
                            next_due=stamp + self.config["retry_seconds"],
                        )
                        store.emit(self.state, key, "alert", code="POLL_RETRY", attempt=failures)
                        return
                    if stamp < schedule["next_due"]:
                        return
                self.controller.start(None, resume=key)
                self.update(status="running")
                return
            if (
                schedule["status"] == "finished"
                or self.controller.active
                or stamp < schedule["next_due"]
            ):
                return
            end = datetime.fromtimestamp(stamp, timezone.utc).date()
            start = end - timedelta(days=self.config["lookback_days"] - 1)
            params = parameters(
                {
                    "section": self.config["section"],
                    "start": str(start),
                    "end": str(end),
                    "limit": self.config["limit"],
                }
            )
            key = store.new_job(self.state, params, scheduled=True)
            lag = max(0, stamp - schedule["next_due"])
            self.update(last_lag=lag)
            store.emit(self.state, key, "poll_trigger", lag_seconds=round(lag, 6))
            self.controller.start(None, resume=key)

    def run(self):
        self.started = True
        failed_signal = False
        try:
            while not self.controller.stop_server.is_set():
                try:
                    self.tick()
                    failed_signal = False
                    if self.snapshot()["status"] == "finished":
                        break
                except (OSError, ValueError, sqlite3.Error):
                    if not failed_signal:
                        # Local event remains available even if SQLite cannot be written.
                        from ..common import alert

                        alert(self.state, "POLL_STORAGE_BLOCKED")
                        failed_signal = True
                self.controller.stop_server.wait(0.2)
        finally:
            self.started = False
