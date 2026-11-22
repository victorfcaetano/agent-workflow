import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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

    @unittest.skipUnless(os.name == "nt", "Windows may run batch files through a shell")
    def test_verify_rejects_windows_batch_commands_before_any_execution(self):
        (self.root / "batch-on-path.cmd").touch()
        with patch.dict(os.environ, {"PATH": str(self.root), "PATHEXT": ".EXE;.BAT;.CMD"}):
            for program in ("missing.CmD", "./tools/missing.BAT", "batch-on-path"):
                with self.subTest(program=program):
                    self.configure({"id": "first", "command": self.mark},
                                   {"id": "batch", "command": [program]})
                    code, message = self.run_cli()
                    self.assertEqual(code, 2)
                    self.assertIn("batch", message.lower())
                    self.assertFalse(self.marker.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX executable names may end in .cmd")
    def test_posix_executable_named_batch_extension_is_allowed(self):
        (self.root / "tool.cmd").symlink_to(sys.executable)
        command = ["./tool.cmd", *self.mark[1:]]
        self.configure({"id": "native", "command": command})
        result, = verify(self.root)
        self.assertTrue(result.passed, result.detail)
        self.assertEqual(result.command, command)
        self.assertTrue(self.marker.is_file())

    def test_verify_resolves_relative_executable_from_check_cwd(self):
        work = self.root / "work"
        tools = work / "tools"
        tools.mkdir(parents=True)
        if os.name == "nt":
            shutil.copy2(Path(os.environ["SystemRoot"]) / "System32/fc.exe", tools / "compare.exe")
            (work / "left").write_bytes(b"matching")
            (work / "right").write_bytes(b"matching")
            command = ["./tools/compare.exe", "/B", "left", "right"]
        else:
            executable = tools / "true"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            command = ["./tools/true"]
        self.configure({"id": "relative", "command": command, "cwd": work.name})
        result, = verify(self.root)
        self.assertTrue(result.passed, result.detail)
        self.assertEqual(result.command, command)

    def test_verify_records_working_directory_removed_by_prior_check(self):
        (self.root / "obsolete").mkdir()
        remove_cwd = [sys.executable, "-c", "from pathlib import Path; Path('obsolete').rmdir()"]
        self.configure({"id": "prepare", "command": remove_cwd},
                       {"id": "gone", "command": self.mark, "cwd": "obsolete"},
                       {"id": "remaining", "command": self.mark})
        results = verify(self.root)
        self.assertEqual([(r.id, r.passed) for r in results],
                         [("prepare", True), ("gone", False), ("remaining", True)])
        self.assertIn("cwd", results[1].detail)
        self.assertTrue(self.marker.exists())

    def test_verify_rejects_invalid_onboarding_before_execution(self):
        self.configure({"id": "first", "command": self.mark})
        with self.config.open("a", encoding="utf-8") as stream:
            stream.write("\n[onboarding]\nstatus = 10\n")
        code, output = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("onboarding", output)
        self.assertFalse(self.marker.exists())

    @unittest.skipUnless(os.name == "posix", "FIFOs require POSIX")
    def test_nonregular_config_is_rejected_without_blocking(self):
        os.mkfifo(self.config)
        run = subprocess.run([sys.executable, "-m", "agent_workflow", "verify", str(self.root)],
                             text=True, capture_output=True, timeout=5, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn("regular file", run.stderr)
