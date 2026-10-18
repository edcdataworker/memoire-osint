"""Provisioning guardrails, without a VM provider or network."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "virtual_server", Path(__file__).resolve().parents[1] / "scripts/virtual_server.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VMTests(unittest.TestCase):
    def test_missing_provider_cannot_launch(self):
        with (
            patch("sys.argv", ["virtual_server", "up"]),
            patch.object(module.shutil, "which", return_value=None),
            patch.object(module.subprocess, "run") as run,
        ):
            with self.assertRaises(SystemExit) as error:
                module.main()
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()

    def test_existing_instance_is_never_replaced(self):
        inventory = type(
            "Result", (), {"stdout": json.dumps({"list": [{"name": module.NAME}]})}
        )()
        with (
            patch("sys.argv", ["virtual_server", "up"]),
            patch.object(module.shutil, "which", return_value="/fixture/multipass"),
            patch.object(module.subprocess, "run", return_value=inventory) as run,
        ):
            with self.assertRaises(SystemExit):
                module.main()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][1], "list")


if __name__ == "__main__":
    unittest.main()
