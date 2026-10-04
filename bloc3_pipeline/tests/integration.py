"""Executable black-box fault tests; all fixtures are synthetic and separately stored."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.__main__ import DEFAULTS
from pipeline.common import atomic_json, now, sha256
from pipeline.monitor import security_check
from pipeline.publish import published_path
from pipeline.rights import access, erase


def article(index):
    return {
        "id": f"test-{index}",
        "date": 1700000000 + index,
        "title": f"Fixture {index}",
        "text": f"Unmanned aircraft № {index} at test site. Épreuve synthétique.",
        "url": f"https://example.invalid/{index}",
    }


def execute(config, schedule=False, **options):
    path = Path(config["state"]).parent / (Path(config["state"]).name + "-config.json")
    atomic_json(path, DEFAULTS | config)
    command = [
        sys.executable,
        "-m",
        "pipeline",
        "schedule" if schedule else "worker",
        "--config",
        str(path),
    ]
    if schedule:
        command += ["--first-delay", str(options.get("delay", 0.05))]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)


def run_tests():
    (ROOT / "Preuves").mkdir(exist_ok=True)
    results = []
    from unittest.mock import patch

    from pipeline.common import actor_identity

    with patch("pipeline.common.getpass.getuser", side_effect=KeyError("uid not found")):
        assert actor_identity() == f"uid:{os.getuid()}"
    results.append({"test": "container_numeric_uid_without_passwd", "passed": True})
    with tempfile.TemporaryDirectory(prefix="osint-b3-tests-") as temporary:
        base = Path(temporary)
        source = base / "source.jsonl"
        source.write_text("\n".join(json.dumps(article(i)) for i in range(40)) + "\n")
        config = {
            "source": str(source),
            "state": str(base / "main"),
            "batch_size": 10,
            "synthetic": True,
        }
        first = execute(config)
        assert first.returncode == 0, first.stderr
        state = Path(config["state"])
        original = json.loads((state / "current.json").read_text())
        result = json.loads((state / "last_result.json").read_text())
        assert result["accepted"] == 40
        final = [json.loads(line) for line in Path(original["jsonl"]).read_text().splitlines()]
        assert all(
            row["text"] == article(i)["text"] and row["id"] == article(i)["id"]
            for i, row in enumerate(final)
        )
        assert all(
            row["text_sha256"] == hashlib.sha256(row["text"].encode()).hexdigest() for row in final
        )
        results.append(
            {
                "test": "text_hash_unicode_offsets_provenance",
                "passed": True,
                "records": 40,
            }
        )
        same = execute(config)
        assert same.returncode == 0 and "unchanged_source" in same.stdout
        assert original == json.loads((state / "current.json").read_text())
        results.append({"test": "idempotent_same_source", "passed": True})
        dup = base / "duplicates.json"
        dup.write_text(
            json.dumps([article(0), article(0), dict(article(0), id="alias"), article(1)])
        )
        duplicate_config = config | {"source": str(dup), "state": str(base / "dup")}
        assert execute(duplicate_config).returncode == 0
        stats = json.loads((base / "dup" / "last_result.json").read_text())
        assert stats["accepted"] == 2 and stats["duplicates"] == 2
        results.append(
            {
                "test": "duplicate_id_and_exact_text",
                "passed": True,
                "accepted": 2,
                "duplicates": 2,
            }
        )
        bad = base / "bad.jsonl"
        bad.write_text(
            json.dumps(article(1))
            + "\n{not json\n"
            + json.dumps(dict(article(2), date="yesterday"))
            + "\n"
        )
        bad_result = execute(config | {"source": str(bad)})
        assert bad_result.returncode != 0
        assert "WORKER_ERROR" in bad_result.stdout and "TypeError" not in bad_result.stderr
        assert original == json.loads((state / "current.json").read_text())
        assert sha256(original["jsonl"]) == original["sha256"]["articles.jsonl"]
        results.append(
            {
                "test": "invalid_rows_quality_blocks_publication",
                "passed": True,
                "previous_release_unchanged": True,
            }
        )
        tolerant = execute(
            config
            | {
                "source": str(bad),
                "state": str(base / "tolerant"),
                "max_reject_rate": 0.7,
            }
        )
        assert tolerant.returncode == 0
        stats = json.loads((base / "tolerant" / "last_result.json").read_text())
        assert stats["accepted"] == 1 and stats["rejected"] == 2
        results.append({"test": "isolated_errors_continue_with_explicit_threshold", "passed": True})
        crash_config = config | {
            "state": str(base / "crash"),
            "test_kill_at_record": 14,
            "retry_seconds": 0.05,
        }
        recovery = execute(crash_config, schedule=True, delay=0.2)
        assert recovery.returncode == 0, recovery.stderr
        events = [
            json.loads(line) for line in (base / "crash" / "events.jsonl").read_text().splitlines()
        ]
        starts = [row["checkpoint"] for row in events if row["event"] == "worker_start"]
        assert starts == [0, 10], starts
        stats = json.loads((base / "crash" / "last_result.json").read_text())
        assert stats["checkpoint"] == 40 and stats["accepted"] == 40 and stats["attempts"] == 2
        trigger = next(row for row in events if row["event"] == "scheduled_trigger")
        assert trigger["trigger_epoch"] >= trigger["due_epoch"]
        results.append(
            {
                "test": "scheduled_sigkill_automatic_durable_resume",
                "passed": True,
                "resumed_checkpoints": starts,
                "accepted": 40,
                "attempts": 2,
                "trigger": trigger,
            }
        )
        (ROOT / "Preuves" / "Reprise_automatique.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )
        primary = Path(original["jsonl"])
        primary.rename(primary.with_suffix(".offline"))
        path, backend = published_path(state)
        assert backend == "mirror" and sha256(path) == original["sha256"]["articles.jsonl"]
        results.append(
            {
                "test": "publication_primary_unavailable_read_failover",
                "passed": True,
                "backend": backend,
            }
        )
        primary.with_suffix(".offline").rename(primary)
        # Hold the real SQLite write lock, release it later; the scheduler recovers alone.
        unavailable = base / "unavailable"
        unavailable.mkdir()
        from pipeline.state import connect

        db = connect(unavailable)
        db.execute("BEGIN EXCLUSIVE")
        cfg = config | {"state": str(unavailable), "retry_seconds": 0.1}
        cp = base / "unavailable-config.json"
        atomic_json(cp, DEFAULTS | cfg)
        proc = subprocess.Popen(
            [sys.executable, "-m", "pipeline", "schedule", "--config", str(cp)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(2.5)
        db.rollback()
        db.close()
        out, err = proc.communicate(timeout=30)
        assert proc.returncode == 0, err
        events_u = [
            json.loads(line) for line in (unavailable / "events.jsonl").read_text().splitlines()
        ]
        assert any(e["event"] == "alert" and e["code"] == "WORKER_EXIT" for e in events_u)
        results.append(
            {
                "test": "sqlite_unavailable_automatic_retry",
                "passed": True,
                "lock_held_seconds": 2.5,
            }
        )
        slow = execute(config | {"state": str(base / "slow"), "slow_batch_seconds": 0})
        assert slow.returncode == 0
        assert "SLOW_BATCH" in (base / "slow" / "alerts.jsonl").read_text()
        results.append(
            {
                "test": "proactive_slow_batch_alert",
                "passed": True,
                "test_threshold_seconds": 0,
            }
        )
        os.chmod(state, 0o755)
        assert security_check(state) is False and (state.stat().st_mode & 0o777) == 0o700
        assert "SECURITY_PERMISSIONS" in (state / "alerts.jsonl").read_text()
        results.append(
            {
                "test": "security_permission_incident_signal_and_containment",
                "passed": True,
            }
        )
        assert len(access(state, "test-3")) == 1
        erase(state, "test-3", "SYNTHETIC-RIGHTS-001")
        assert access(state, "test-3") == []
        export, _ = published_path(state)
        assert all(json.loads(line)["id"] != "test-3" for line in export.read_text().splitlines())
        # A changed file triggers another run and must respect the durable tombstone.
        source.write_text(source.read_text() + "\n")
        cfg = config | {"max_reject_rate": 0.1}
        assert execute(cfg).returncode == 0
        stats = json.loads((state / "last_result.json").read_text())
        assert stats["suppressed"] == 1 and stats["accepted"] == 39
        results.append(
            {
                "test": "access_erasure_and_no_resurrection",
                "passed": True,
                "external_propagation_tested": False,
            }
        )
        external = base / "b2-erasures.json"
        atomic_json(external, ["test-4"])
        assert execute(cfg | {"external_tombstones": str(external)}).returncode == 0
        assert access(state, "test-4") == []
        export, _ = published_path(state)
        assert all(json.loads(line)["id"] != "test-4" for line in export.read_text().splitlines())
        results.append(
            {"test": "external_B2_tombstone_import_and_current_export_purge", "passed": True}
        )
        invalid_json = base / "malformed.json"
        invalid_json.write_text('[{"id":')
        r = execute(config | {"source": str(invalid_json), "state": str(base / "malformed")})
        assert r.returncode != 0 and not (base / "malformed" / "current.json").exists()
        results.append({"test": "malformed_json_array_no_publication", "passed": True})
    report = {
        "at": now(),
        "synthetic": True,
        "tests": results,
        "passed": len(results),
        "failed": 0,
        "environment": {"python": sys.version, "sqlite": sqlite3.sqlite_version},
    }
    atomic_json(ROOT / "Preuves" / "Tests_pipeline.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_tests()
