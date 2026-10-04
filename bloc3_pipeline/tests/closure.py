"""Rights, raw-page purge, degraded reads and incident regressions on fixtures."""

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collection import Source, markup

from pipeline.collection import resilience, rights, security, store, volume
from pipeline.collection.service import Controller
from pipeline.collection.source import parameters
from pipeline.collection.worker import execute
from pipeline.common import atomic_json, lock

MARKER = "FICTIONAL_PRIVATE_MARKER_8c0c76"


class PrivateSource(Source):
    def request(self, url):
        return markup(
            int(url.rsplit("/", 1)[1]), MARKER if url.endswith("/1") else "Public fixture."
        )


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.config = {"state": str(self.state), "tombstone_files": [], "max_pages": 3}
        self.params = parameters(
            {"section": "defense", "start": "2023-11-26", "end": "2023-11-26", "limit": 3}
        )
        store.initialize(self.state)
        atomic_json(self.state / "config.json", self.config)
        self.collect()

    def tearDown(self):
        self.temp.cleanup()

    def collect(self):
        key = store.new_job(self.state, self.params)
        self.assertEqual(execute(self.state, key, self.config, PrivateSource()), 0)
        return key

    def assert_purged(self):
        for path in [
            self.state / "collection.sqlite",
            self.state / "collection.sqlite-wal",
            self.state / "mirror/catalog.sqlite",
        ]:
            if path.exists():
                self.assertNotIn(MARKER.encode(), path.read_bytes(), str(path))
        for path in (self.state / "exports").rglob("articles.*"):
            self.assertNotIn(MARKER, path.read_text())

    def test_restart_preserves_unchanged_exports_and_repairs_stale_jsonl(self):
        paths = [self.state / "current.json", *(self.state / "exports").rglob("*")]
        before = {p: p.read_bytes() for p in paths if p.is_file()}
        controller = Controller(self.config)
        controller.stop_server.set()
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        line_file = next((self.state / "exports").glob("*/articles.jsonl"))
        atomic_json(line_file, {"stale": "fictional"})
        rights.reapply(self.state, self.config)
        self.assertEqual(line_file.read_bytes(), before[line_file])

    def test_rectification_purges_old_versions_and_survives_recollection(self):
        rights.rectify(self.state, self.config, "1", {"text": "Corrected fixture. Ω"}, "D-001")
        self.assert_purged()
        self.collect()
        values = rights.access(self.state, "1", "D-002")["revisions"]
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["text"], "Corrected fixture. Ω")
        self.assert_purged()
        self.assertEqual(
            values[0]["text_sha256"], hashlib.sha256(values[0]["text"].encode()).hexdigest()
        )

    def test_erasure_purges_sql_wal_exports_mirror_and_recollection(self):
        rights.erase(self.state, self.config, "1", "D-003")
        self.assert_purged()
        self.collect()
        self.assertEqual(rights.access(self.state, "1", "D-004")["revisions"], [])
        self.assertEqual(store.corpus(self.state, self.params)["total"], 2)
        self.assert_purged()

    def test_restore_stale_backup_reapplies_erasure_before_exposure(self):
        old = (self.state / "mirror/catalog.sqlite").read_bytes()
        rights.erase(self.state, self.config, "1", "D-005")
        (self.state / "mirror/catalog.sqlite").write_bytes(old)
        atomic_json(
            self.state / "mirror/manifest.json",
            {"at": "2026-01-01", "sha256": hashlib.sha256(old).hexdigest()},
        )
        resilience.restore(self.state, self.config)
        self.assertEqual(store.corpus(self.state, self.params)["total"], 2)
        self.assert_purged()

    def test_restore_stale_backup_reapplies_rectification(self):
        old = (self.state / "mirror/catalog.sqlite").read_bytes()
        rights.rectify(self.state, self.config, "1", {"text": "Corrected fixture."}, "D-006")
        (self.state / "mirror/catalog.sqlite").write_bytes(old)
        atomic_json(
            self.state / "mirror/manifest.json",
            {"at": "2026-01-01", "sha256": hashlib.sha256(old).hexdigest()},
        )
        resilience.restore(self.state, self.config)
        self.assert_purged()

    def test_degraded_read_export_and_mutation_refusal(self):
        controller = Controller(self.config)
        try:
            (self.state / "collection.sqlite").rename(self.state / "offline.sqlite")
            snapshot = controller.snapshot()
            self.assertEqual(snapshot["backend"], "mirror")
            self.assertTrue(snapshot["read_only"])
            self.assertEqual(store.corpus(self.state, self.params)["total"], 3)
            manifest = store.export(self.state, self.config, self.params)
            self.assertEqual(manifest["articles"], 3)
            for operation in [
                lambda: controller.start(self.params),
                lambda: controller.ingest_b2(snapshot["jobs"][0]["job_id"]),
                lambda: rights.erase(self.state, self.config, "1", "D-007"),
                lambda: rights.rectify(self.state, self.config, "1", {"text": "X"}, "D-008"),
            ]:
                with self.assertRaises(ValueError):
                    operation()
            self.assertFalse((self.state / "collection.sqlite").exists())
            self.assertEqual(
                json.loads((self.state / "security.json").read_text())["code"], "CATALOG_INTEGRITY"
            )
        finally:
            controller.stop_server.set()

    def test_corrupt_primary_uses_mirror_corrupt_mirror_fails_closed(self):
        (self.state / "collection.sqlite").write_bytes(b"corrupt")
        self.assertEqual(resilience.backend(self.state)[1], "mirror")
        (self.state / "mirror/catalog.sqlite").write_bytes(b"also corrupt")
        with self.assertRaises(OSError):
            resilience.backend(self.state)

    def test_external_tombstone_filters_stale_mirror(self):
        ledger = self.state / "external.json"
        self.config["tombstone_files"] = [str(ledger)]
        atomic_json(self.state / "config.json", self.config)
        atomic_json(ledger, ["1"])
        (self.state / "collection.sqlite").rename(self.state / "offline.sqlite")
        self.assertEqual(store.corpus(self.state, self.params)["total"], 2)
        self.assertEqual(store.export(self.state, self.config, self.params)["articles"], 2)

    def test_stale_mirror_never_exposes_superseded_correction(self):
        old = (self.state / "mirror/catalog.sqlite").read_bytes()
        rights.rectify(self.state, self.config, "1", {"text": "Corrected fixture."}, "D-009")
        (self.state / "mirror/catalog.sqlite").write_bytes(old)
        atomic_json(
            self.state / "mirror/manifest.json",
            {"at": "2026-01-01", "sha256": hashlib.sha256(old).hexdigest()},
        )
        (self.state / "collection.sqlite").rename(self.state / "offline.sqlite")
        values = rights.access(self.state, "1", "D-010")["revisions"]
        self.assertEqual(values[0]["text"], "Corrected fixture.")
        manifest = store.export(self.state, self.config, self.params)
        self.assertNotIn(MARKER, Path(manifest["json"]).read_text())

    def test_retention_removes_old_metadata_and_keeps_recent_events(self):
        with store.database(self.state) as db, db:
            db.execute("UPDATE events SET at='2020-01-01T00:00:00+00:00'")
        store.emit(self.state, None, "retention_recent")
        self.assertGreater(security.retention(self.state), 0)
        with store.database(self.state) as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM events WHERE at LIKE '2020%'").fetchone()[0], 0
            )
            self.assertEqual(
                db.execute("SELECT count(*) FROM events WHERE kind='retention_recent'").fetchone()[
                    0
                ],
                1,
            )

    def test_security_permission_signal_and_containment(self):
        os.chmod(self.state, 0o755)
        status = security.check(self.state)
        self.assertTrue(status["contained"])
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        incident = json.loads((self.state / "security.json").read_text())
        self.assertEqual(incident["code"], "SECURITY_PERMISSIONS")
        self.assertIn("actor", incident)

    def test_encryption_requirement_cannot_fall_back_to_plaintext(self):
        with patch.object(security, "encrypted_volume", return_value=False):
            with self.assertRaises(OSError):
                security.check(self.state, require_encrypted=True)

    def test_keywords_are_not_written_to_audit_log(self):
        store.new_job(self.state, {**self.params, "keywords": ["PRIVATE_KEYWORD_SENTINEL"]})
        self.assertNotIn("PRIVATE_KEYWORD_SENTINEL", (self.state / "events.jsonl").read_text())

    def test_slow_article_alert_is_emitted(self):
        key = store.new_job(self.state, self.params)
        config = {**self.config, "slow_article_seconds": 0.000001}
        execute(self.state, key, config, PrivateSource())
        with store.database(self.state) as db:
            events = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT fields FROM events WHERE job_id=? AND kind='alert'", (key,)
                )
            ]
        self.assertTrue(any(e["code"] == "SLOW_ARTICLE" for e in events))


class MigrationTests(unittest.TestCase):
    def test_verified_migration_and_legacy_link_on_mock_encrypted_mount(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source, destination = root / "source", root / "volume/B3"
            store.initialize(source)
            atomic_json(source / "config.json", {"state": str(source), "tombstone_files": []})
            legacy = root / ".state"
            legacy.mkdir()
            with sqlite3.connect(legacy / "pipeline.sqlite") as db:
                db.execute("CREATE TABLE fixture(value TEXT)")
                db.execute("INSERT INTO fixture VALUES('fictional')")
            with patch.object(security, "encrypted_volume", return_value=True):
                report = volume.migrate(source, destination)
            self.assertTrue(report["source_removed"])
            self.assertFalse(source.exists())
            self.assertTrue(legacy.is_symlink())
            self.assertEqual(legacy.resolve(), root / "volume/B3_historique")
            self.assertTrue(
                json.loads((destination / "config.json").read_text())["require_encrypted"]
            )
            self.assertTrue(
                json.loads((root / ".collection-location.json").read_text())["require_encrypted"]
            )

    def test_migration_refuses_busy_worker_without_removing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"
            store.initialize(source)
            with (
                lock(source, "collection-worker.lock"),
                patch.object(security, "encrypted_volume", return_value=True),
            ):
                with self.assertRaises(BlockingIOError):
                    volume.migrate(source, Path(folder) / "volume/B3")
            self.assertTrue((source / "collection.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
