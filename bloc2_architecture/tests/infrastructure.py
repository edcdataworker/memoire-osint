"""Operational failures and diagnostics, independent of the user's data stores."""

import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "infrastructure", Path(__file__).resolve().parents[1] / "scripts/infrastructure.py"
)
infra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(infra)


class InfrastructureTests(unittest.TestCase):
    def test_json_formats(self):
        self.assertEqual(infra.records('[{"x":1}]'), [{"x": 1}])
        self.assertEqual(infra.records('{"x":1}\n{"x":2}'), [{"x": 1}, {"x": 2}])
        self.assertEqual(infra.records(""), [])

    def test_malformed_command_output_is_sanitized(self):
        with self.assertRaisesRegex(infra.OperationError, "^invalid_command_json$"):
            infra.records("private-not-json")

    def test_non_finite_interval_is_rejected(self):
        for value in ("nan", "inf", "0", "-1"):
            with self.assertRaises(infra.argparse.ArgumentTypeError):
                infra.positive(value)

    def test_alerts_missing_unhealthy_and_memory(self):
        services = [
            {"service": "postgres", "state": "running", "health": "unhealthy"},
            {"service": "mongo", "state": "exited", "health": ""},
        ]
        metrics = [{"service": "postgres", "memory_percent": "90.0%"}]
        reasons = {
            a["reason"] for a in infra.evaluate(services, metrics, infra.CORE, 85)
        }
        self.assertEqual(
            reasons, {"health_unhealthy", "not_running", "missing", "memory_threshold"}
        )

    def test_boundary_and_healthy(self):
        services = [{"service": "app", "state": "running", "health": "healthy"}]
        self.assertEqual(infra.evaluate(services, [], ["app"], 85), [])
        self.assertTrue(
            infra.evaluate(
                services, [{"service": "app", "memory_percent": "85%"}], ["app"], 85
            )
        )

    def test_sanitized_failure(self):
        with patch.object(
            infra.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 1, "private", "password"),
        ):
            with self.assertRaisesRegex(infra.OperationError, "^command_failed$"):
                infra.command(["docker"])

    def test_timeout_sanitized(self):
        with patch.object(
            infra.subprocess, "run", side_effect=subprocess.TimeoutExpired("private", 1)
        ):
            with self.assertRaisesRegex(infra.OperationError, "^TimeoutExpired$"):
                infra.command(["docker"])

    def test_snapshot_allowlist_and_scope(self):
        rows = [
            {
                "Service": "app",
                "State": "running",
                "Health": "healthy",
                "ID": "abc123",
                "Labels": "PRIVATE",
            },
            {"Service": "other", "State": "running", "ID": "def"},
        ]
        stats = {
            "ID": "abc123",
            "CPUPerc": "1%",
            "MemUsage": "1MiB / 512MiB",
            "MemPerc": "1%",
            "NetIO": "1B / 2B",
            "BlockIO": "0B / 0B",
        }
        with (
            patch.object(infra, "compose", return_value=json.dumps(rows)),
            patch.object(infra, "command", return_value=json.dumps(stats)) as cmd,
        ):
            result = infra.snapshot(["app"], 85)
        self.assertTrue(result["ok"])
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(cmd.call_args.args[0][-1], "abc123")

    def test_missing_metrics_fails(self):
        rows = [
            {"Service": "app", "State": "running", "Health": "healthy", "ID": "abc"}
        ]
        with (
            patch.object(infra, "compose", return_value=json.dumps(rows)),
            patch.object(infra, "command", return_value=""),
        ):
            with self.assertRaisesRegex(infra.OperationError, "incomplete_metrics"):
                infra.snapshot(["app"], 85)

    def test_deploy_keeps_volumes_and_awaits_health(self):
        with (
            patch.object(infra, "command"),
            patch.object(infra, "compose") as compose,
            patch.object(infra, "snapshot", return_value={"ok": True}),
        ):
            self.assertEqual(infra.deploy(False), {"ok": True})
        calls = [c.args for c in compose.call_args_list]
        self.assertIn(
            ("up", "-d", "--wait", "--wait-timeout", "180", *infra.CORE), calls
        )
        self.assertFalse(any("down" in c or "ingest" in c for c in calls))


if __name__ == "__main__":
    unittest.main()
