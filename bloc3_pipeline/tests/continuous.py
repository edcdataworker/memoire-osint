"""Continuous collection on fictional arrivals, never on the real catalog."""

import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.collection import resilience, store
from pipeline.collection.continuous import ContinuousCollector, options
from pipeline.collection.service import Controller
from pipeline.collection.source import parameters
from pipeline.collection.worker import execute


class ArrivalSource:
    def __init__(self):
        self.count = 1
        self.rejected = False
        self.stamp = int(time.time())

    def initialize(self, section):
        return 4953

    def discover(self, section, cursor, excluded):
        if excluded:
            return {"newsList": [], "lastTime": self.stamp}
        return {
            "newsList": [
                {"id": i, "date": self.stamp, "link": f"/defense/{i}"}
                for i in range(1, self.count + 1)
            ],
            "lastTime": self.stamp,
        }

    def request(self, url):
        if self.rejected:
            raise OSError("Synthetic unavailable article")
        identifier = int(url.rsplit("/", 1)[1])
        meta = {
            "@type": "NewsArticle",
            "headline": f"Fictional arrival {identifier}",
            "datePublished": datetime.fromtimestamp(self.stamp, timezone.utc).isoformat(),
        }
        return (
            '<script type="application/ld+json">'
            + json.dumps(meta)
            + '</script><div class="text-content"><div class="text-block">'
            + f"<p>Fictional document {identifier}. No real event.</p></div></div>"
        )


class FixtureController(Controller):
    def __init__(self, config, source):
        self.source = source
        super().__init__(config)

    def supervise(self, key):
        try:
            execute(self.state, key, self.config, self.source)
        finally:
            with self.guard:
                self.active = None


class ContinuousTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.source = ArrivalSource()
        self.config = {"state": str(self.state), "tombstone_files": [], "max_pages": 2}
        self.controller = FixtureController(self.config, self.source)
        self.poll = ContinuousCollector(self.controller, {"interval_seconds": 0.1, "max_cycles": 3})
        self.controller.continuous = self.poll

    def tearDown(self):
        self.controller.stop_server.set()
        self.wait_worker()
        self.temp.cleanup()

    def wait_worker(self):
        deadline = time.monotonic() + 5
        while self.controller.active and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertIsNone(self.controller.active)

    def cycle(self):
        # Persist an overdue deadline rather than relying on wall-clock sleeps.
        self.poll.update(next_due=time.time() - 1)
        self.poll.tick()
        self.wait_worker()
        self.poll.tick()

    def test_successive_arrivals_and_idempotence(self):
        self.cycle()
        self.source.count = 2
        self.cycle()
        self.cycle()
        status = self.poll.snapshot()
        self.assertEqual(status["completed"], 3)
        self.assertEqual(status["status"], "finished")
        self.assertEqual(self.controller.snapshot()["articles"], 2)
        with store.database(self.state) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM revisions").fetchone()[0], 2)
        pointer = json.loads((self.state / "current.json").read_text())
        self.assertEqual(pointer["articles"], 2)
        self.assertGreaterEqual(status["last_lag"], 0)

    def test_quality_failure_keeps_last_publication_and_requires_action(self):
        self.cycle()
        before = (self.state / "current.json").read_bytes()
        self.source.rejected = True
        self.cycle()
        self.assertEqual(self.poll.snapshot()["status"], "quality_blocked")
        self.assertEqual((self.state / "current.json").read_bytes(), before)
        key = self.poll.snapshot()["pending_job"]
        self.poll.tick()
        self.assertEqual(self.poll.snapshot()["pending_job"], key)

    def test_queue_and_schedule_checkpoint_are_atomic(self):
        today = datetime.now(timezone.utc).date().isoformat()
        params = parameters({"section": "defense", "start": today, "end": today})
        key = store.new_job(self.state, params, scheduled=True)
        self.assertEqual(self.poll.snapshot()["pending_job"], key)
        self.poll = ContinuousCollector(self.controller, {"interval_seconds": 0.1, "max_cycles": 3})
        self.controller.recover()
        self.wait_worker()
        self.poll.tick()
        with store.database(self.state) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
        self.assertEqual(self.poll.snapshot()["last_job"], key)

    def test_explicit_pause_is_not_restarted(self):
        today = datetime.now(timezone.utc).date().isoformat()
        params = parameters({"section": "defense", "start": today, "end": today})
        key = store.new_job(self.state, params, scheduled=True)
        with store.database(self.state) as db, db:
            db.execute("UPDATE jobs SET status='paused' WHERE job_id=?", (key,))
        self.poll.tick()
        self.assertEqual(self.poll.snapshot()["status"], "paused")
        self.assertIsNone(self.controller.active)

    def test_storage_failure_never_starts_a_new_job(self):
        self.cycle()
        self.poll.update(next_due=time.time() - 1)
        (self.state / "collection.sqlite").rename(self.state / "catalog.offline")
        self.assertEqual(resilience.backend(self.state)[1], "mirror")
        self.assertEqual(self.poll.snapshot()["status"], "storage_blocked")
        with self.assertRaises(ValueError):
            self.poll.tick()
        self.assertIsNone(self.controller.active)
        (self.state / "catalog.offline").rename(self.state / "collection.sqlite")

    def test_invalid_settings(self):
        for value in [
            {"interval_seconds": float("nan")},
            {"limit": True},
            {"lookback_days": 0},
            {"source_url": "https://example.invalid"},
        ]:
            with self.assertRaises(ValueError):
                options(value)

    def test_partial_coverage_is_explicitly_alerted(self):
        self.poll = ContinuousCollector(
            self.controller, {"interval_seconds": 0.1, "max_cycles": 3, "limit": 1}
        )
        self.controller.continuous = self.poll
        self.source.count = 2
        self.cycle()
        self.assertEqual(self.poll.snapshot()["status"], "coverage_limited")
        with store.database(self.state) as db:
            events = [
                json.loads(r[0]) for r in db.execute("SELECT fields FROM events WHERE kind='alert'")
            ]
        self.assertTrue(any(e.get("code") == "POLL_COVERAGE_LIMITED" for e in events))

    def test_retry_budget_and_stalled_alert(self):
        from unittest.mock import patch

        today = datetime.now(timezone.utc).date().isoformat()
        params = parameters({"section": "defense", "start": today, "end": today})
        key = store.new_job(self.state, params, scheduled=True)
        with store.database(self.state) as db, db:
            db.execute("UPDATE jobs SET status='retryable' WHERE job_id=?", (key,))
        stamp = time.time()
        with patch.object(self.controller, "start") as start:
            for attempt in range(3):
                self.poll.tick(stamp)
                stamp += 11
                self.poll.tick(stamp)
                stamp += 1
            self.poll.tick(stamp)
            self.assertEqual(start.call_count, 3)
        self.assertEqual(self.poll.snapshot()["status"], "failed")
        with store.database(self.state) as db, db:
            db.execute("UPDATE jobs SET status='running' WHERE job_id=?", (key,))
        self.controller.active = key
        try:
            self.poll.tick(time.time() + 301)
            self.poll.tick(time.time() + 302)
            with store.database(self.state) as db:
                events = [
                    json.loads(r[0])
                    for r in db.execute("SELECT fields FROM events WHERE kind='alert'")
                ]
            self.assertEqual(sum(e.get("code") == "POLL_STALLED" for e in events), 1)
        finally:
            self.controller.active = None


if __name__ == "__main__":
    unittest.main()
