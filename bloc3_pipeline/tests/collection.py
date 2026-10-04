"""Collection regressions with a deterministic source, no external requests."""

import io
import json
import multiprocessing
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from pipeline.collection import store
from pipeline.collection.service import Controller
from pipeline.collection.source import Client, Stopped, bounds, extract, parameters
from pipeline.collection.worker import execute


def markup(identifier, text="A ship &amp; a missile. Unité Ω."):
    metadata = {
        "@type": "NewsArticle",
        "headline": "Fixture",
        "datePublished": "2023-11-26T12:00:00Z",
    }
    return (
        '<nav>IGNORE</nav><script type="application/ld+json">'
        + json.dumps(metadata)
        + '</script><div class="text-content"><div class="text-block"><p>'
        + text
        + '</p><aside>IGNORE</aside><div class="advert">IGNORE</div></div></div>'
    )


class Source:
    def __init__(self, failures=(), pause=None, altered=False):
        self.failures, self.pause, self.altered = failures, pause, altered
        self.requests, self.discoveries = [], 0

    def initialize(self, section):
        return 4953

    def discover(self, section, cursor, excluded):
        self.discoveries += 1
        stamp = bounds("2023-11-26", "2023-11-26")[0] + 43200
        return {
            "newsList": [{"id": i, "date": stamp, "link": f"/defense/{i}"} for i in (1, 2, 3)],
            "lastTime": stamp,
        }

    def request(self, url):
        i = int(url.rsplit("/", 1)[1])
        self.requests.append(i)
        if i == self.pause:
            raise Stopped()
        if i in self.failures:
            raise OSError("fixture unavailable")
        return markup(
            i, "Updated article Ω." if self.altered else "A ship &amp; a missile. Unité Ω."
        )


class SlowSource(Source):
    def request(self, url):
        if url.endswith("/2"):
            time.sleep(20)
        return super().request(url)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.config = {"state": str(self.state), "tombstone_files": [], "max_pages": 3}
        self.params = parameters(
            {"section": "defense", "start": "2023-11-26", "end": "2023-11-26", "limit": 3}
        )
        store.initialize(self.state)

    def tearDown(self):
        self.temp.cleanup()

    def run_job(self, source):
        key = store.new_job(self.state, self.params)
        self.assertEqual(execute(self.state, key, self.config, source), 0)
        return key

    def test_inclusive_dates_and_extraction(self):
        a, b = bounds("2023-11-26", "2023-11-26")
        self.assertEqual(b - a, 86400)
        for bad in ([], {**self.params, "start": "2024-01-01", "end": "2023-01-01"}):
            with self.assertRaises(ValueError):
                parameters(bad)
        row = extract(markup(1), "https://tass.com/defense/1", "fixture")
        self.assertEqual(row["text"], "A ship & a missile. Unité Ω.")
        self.assertEqual(row["date"], a + 43200)
        self.assertEqual(row["offset_unit"], "unicode_codepoint")
        self.assertEqual(len(row["text_sha256"]), 64)
        self.assertNotIn("IGNORE", row["text"])

    def test_replay_versions_and_export_contract(self):
        self.run_job(Source())
        self.run_job(Source())
        key = self.run_job(Source(altered=True))
        self.assertEqual(store.job(self.state, key)["counts"], {"updated": 3})
        with store.database(self.state) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM heads").fetchone()[0], 3)
            self.assertEqual(db.execute("SELECT count(*) FROM revisions").fetchone()[0], 6)
        manifest = store.export(self.state, self.config, self.params)
        rows = json.loads(Path(manifest["json"]).read_text())
        lines = [json.loads(line) for line in Path(manifest["jsonl"]).read_text().splitlines()]
        self.assertEqual(rows, lines)
        self.assertEqual(len(rows), 3)
        self.assertTrue(
            set(("id", "date", "date_readable", "title", "url", "text")).issubset(rows[0])
        )

    def test_quality_failure_keeps_published_corpus(self):
        self.run_job(Source())
        previous = (self.state / "current.json").read_bytes()
        key = self.run_job(Source(failures=(2, 3), altered=True))
        self.assertEqual(store.job(self.state, key)["status"], "quality_failed")
        self.assertEqual((self.state / "current.json").read_bytes(), previous)
        self.assertEqual(store.job(self.state, key)["revision_count"], 3)

    def test_pause_resume_skips_downloaded_units(self):
        key = self.run_job(Source(pause=2))
        self.assertEqual(store.job(self.state, key)["status"], "paused")
        source = Source()
        self.assertEqual(execute(self.state, key, self.config, source), 0)
        self.assertEqual(source.requests, [2, 3])
        self.assertEqual(source.discoveries, 0)
        self.assertEqual(store.job(self.state, key)["status"], "complete")

    def test_erasure_excludes_all_versions_and_recollection(self):
        self.run_job(Source())
        self.run_job(Source(altered=True))
        ledger = self.state / "erasures.json"
        ledger.write_text('["2"]')
        self.config["tombstone_files"] = [str(ledger)]
        store.sync_denied(self.state, self.config)
        for path in (self.state / "exports").glob("*/articles.json"):
            self.assertNotIn("2", {str(row["id"]) for row in json.loads(path.read_text())})
        self.run_job(Source())
        with store.database(self.state) as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM revisions WHERE article_id='2'").fetchone()[0], 0
            )
        self.assertEqual(store.export(self.state, self.config, self.params)["articles"], 2)

    def test_hard_process_crash_releases_lock_and_keeps_checkpoint(self):
        key = store.new_job(self.state, self.params)
        process = multiprocessing.get_context("fork").Process(
            target=execute, args=(self.state, key, self.config, SlowSource())
        )
        process.start()
        try:
            deadline = time.monotonic() + 5
            while store.job(self.state, key)["processed"] < 1 and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(store.job(self.state, key)["processed"], 1)
        finally:
            process.kill()
            process.join(3)
        source = Source()
        self.assertEqual(execute(self.state, key, self.config, source), 0)
        self.assertEqual(source.requests, [2, 3])
        self.assertEqual(source.discoveries, 0)

    def test_filters_and_empty_period(self):
        self.params["keywords"] = ["unité"]
        self.run_job(Source())
        self.assertEqual(store.corpus(self.state, self.params)["total"], 3)
        self.assertEqual(
            store.corpus(self.state, {**self.params, "keywords": ["absent"]})["total"], 0
        )
        self.assertEqual(
            store.corpus(self.state, {**self.params, "start": "2024-01-01", "end": "2024-01-01"})[
                "total"
            ],
            0,
        )

    def test_pagination_stall_is_bounded(self):
        self.params["limit"] = 20
        source = Source()
        key = self.run_job(source)
        self.assertEqual(source.discoveries, 2)
        self.assertEqual(store.job(self.state, key)["coverage"], "pagination_stalled")

    def test_http_retry_is_bounded_and_forbidden_is_not_retried(self):
        events = []
        client = Client(lambda kind, **fields: events.append((kind, fields)), interval=0)
        client.pause = lambda seconds: None
        transient = HTTPError("https://tass.com/defense/1", 503, "fixture", {}, None)
        response = io.BytesIO(b"fixture success")
        response.url = "https://tass.com/defense/1"
        with patch(
            "pipeline.collection.source.urlopen", side_effect=[transient, transient, response]
        ) as send:
            self.assertEqual(client.request(response.url), "fixture success")
            self.assertEqual(send.call_count, 3)
        self.assertEqual(len(events), 2)
        forbidden = HTTPError("https://tass.com/defense/1", 403, "fixture", {}, None)
        with patch("pipeline.collection.source.urlopen", side_effect=forbidden) as send:
            with self.assertRaises(HTTPError):
                client.request(response.url)
            self.assertEqual(send.call_count, 1)

    def test_supervisor_automatically_recovers_after_worker_kill(self):
        config = {**self.config, "corpus": str(self.state / "absent.json")}
        controller = Controller(config)
        original_popen = subprocess.Popen
        children = []
        fixture = str(Path(__file__).resolve())

        def launch(args, **kwargs):
            kind = "SlowSource" if not children else "Source"
            code = f"import runpy,json; n=runpy.run_path({fixture!r}); c=json.load(open({args[-2]!r})); n['execute'](c['state'],{args[-1]!r},c,n[{kind!r}]())"
            child = original_popen([sys.executable, "-c", code], **kwargs)
            children.append(child)
            return child

        with patch("pipeline.collection.service.subprocess.Popen", new=launch):
            key = controller.start(self.params)
            deadline = time.monotonic() + 5
            while store.job(self.state, key)["processed"] < 1 and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(store.job(self.state, key)["processed"], 1)
            children[0].kill()
            deadline = time.monotonic() + 10
            while controller.active and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertIsNone(controller.active)
        self.assertEqual(len(children), 2)
        self.assertEqual(store.job(self.state, key)["status"], "complete")
        self.assertEqual(store.job(self.state, key)["counts"], {"new": 3})

    def test_required_metadata_and_text_are_rejected(self):
        for bad in ("<div>unrelated page</div>", markup(1, " ")):
            with self.assertRaises(ValueError):
                extract(bad, "https://tass.com/defense/1", "fixture")


if __name__ == "__main__":
    unittest.main()
