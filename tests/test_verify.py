import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from agent_workflow.cli import main
from agent_workflow.commands import verify


class VerifyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "project"
        self.root.mkdir()
        self.config = self.root / "agent-workflow.toml"
        self.marker = self.root / "started"
        self.mark = [sys.executable, "-c", "from pathlib import Path; Path('started').touch()"]

    def configure(self, *records):
        self.config.write_text("\n".join(
            "[[checks]]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in record.items())
            for record in records
        ), encoding="utf-8")

    def run_cli(self):
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            code = main(["verify", str(self.root)])
        return code, output.getvalue()

    def test_verify_runs_argv_without_shell(self):
        work = self.root / "dir with spaces"
        work.mkdir()
        args = ["with spaces", "", "& echo expanded", "$HOME", "%PATH%", "*.txt"]
        script = "import json,sys; from pathlib import Path; Path('received').write_text(json.dumps(sys.argv[1:]))"
        command = [sys.executable, "-c", script, *args]
        self.configure({"id": "literal", "command": command, "cwd": work.name})
        results = verify(self.root)
        self.assertEqual(json.loads((work / "received").read_bytes()), args)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].passed)
        self.assertEqual(results[0].command, command)
        self.assertGreater(results[0].elapsed_seconds, 0)

    def test_verify_rejects_empty_or_non_string_command(self):
        for command in ([], "echo broken", [1], [""], ["tool", True]):
            with self.subTest(command=command):
                self.configure({"id": "first", "command": self.mark}, {"id": "bad", "command": command})
                self.assertEqual(self.run_cli()[0], 2)
                self.assertFalse(self.marker.exists())

    def test_verify_rejects_cwd_outside_project(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        for cwd in ("../outside", str(outside), "C:drive-relative", "/absolute"):
            with self.subTest(cwd=cwd):
                self.configure({"id": "first", "command": self.mark},
                               {"id": "bad", "command": self.mark, "cwd": cwd})
                self.assertEqual(self.run_cli()[0], 2)
                self.assertFalse(self.marker.exists())
                self.assertFalse((outside / "started").exists())
        alias = self.root / "link"
        try:
            alias.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if os.name != "nt" or error.winerror != 1314:
                raise
            import _winapi
            _winapi.CreateJunction(str(outside), str(alias))
        self.configure({"id": "bad", "command": self.mark, "cwd": alias.name})
        self.assertEqual(self.run_cli()[0], 2)
        self.assertFalse((outside / "started").exists())

    def test_verify_times_out_and_returns_failure(self):
        self.configure({"id": "long", "timeout_seconds": 1,
                        "command": [sys.executable, "-c", "import time; time.sleep(10)"]})
        code, output = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("timed out", output.lower())
        self.assertIn("long", output)

    def test_verify_aggregates_required_failures(self):
        fail = [sys.executable, "-c", "import sys; sys.exit(7)"]
        optional = {"id": "optional", "command": fail, "required": False}
        self.configure(optional, {"id": "required", "command": fail}, {"id": "last", "command": self.mark})
        code, output = self.run_cli()
        self.assertEqual(code, 1)
        self.assertTrue(self.marker.is_file())
        for name in ("optional", "required", "last"):
            self.assertIn(name, output)
        self.configure(optional)
        self.assertEqual(self.run_cli()[0], 0)

    def test_verify_returns_configuration_error_when_no_checks(self):
        self.assertEqual(self.run_cli()[0], 2)
        self.config.write_text('checks = []\n', encoding="utf-8")
        code, output = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("no", output.lower())
        self.assertIn("checks", output.lower())

    def test_verify_rejects_invalid_fields_before_execution(self):
        for override in ({"id": ""}, {"id": "first"}, {"timeout_seconds": 0}, {"timeout_seconds": 3601},
                         {"timeout_seconds": True}, {"required": "false"}, {"cwd": 1},
                         {"cwd": "missing-directory"}):
            with self.subTest(override=override):
                self.configure({"id": "first", "command": self.mark},
                               {"id": "second", "command": self.mark, **override})
                self.assertEqual(self.run_cli()[0], 2)
                self.assertFalse(self.marker.exists())

    def test_missing_executable_reports_check_failure_and_continues(self):
        self.configure({"id": "unavailable", "command": ["agent-workflow-nonexistent-command-for-test"]},
                       {"id": "next", "command": self.mark})
        code, output = self.run_cli()
        self.assertEqual(code, 1)
        self.assertTrue(self.marker.is_file())
        self.assertIn("unavailable", output)
