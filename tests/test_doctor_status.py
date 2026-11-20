import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from agent_workflow.cli import main
from agent_workflow.commands import doctor, initialize, status


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def snapshot(self):
        return {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns)
                if p.is_file() else None for p in self.root.rglob("*")}

    def test_doctor_reports_missing_openspec_without_failure(self):
        initialize(self.root)
        with patch("shutil.which", return_value=None):
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["doctor", str(self.root)]), 0)
        self.assertIn("openspec", output.getvalue().lower())
        self.assertIn("not found", output.getvalue().lower())
        self.assertIn("AGENTS.md", output.getvalue())
        self.assertIn("agent-workflow.toml", output.getvalue())

    def test_doctor_reports_existing_lock_without_mutation(self):
        lock = self.root / ".agent-workflow.lock"
        lock.write_bytes(b"Busy")
        before = self.snapshot()
        report = doctor(self.root)
        matches = [d for d in report if lock.name in d.message]
        self.assertTrue(matches)
        self.assertIn("inspect", matches[0].message.lower())
        self.assertEqual(self.snapshot(), before)

    def test_doctor_is_read_only(self):
        initialize(self.root)
        before = self.snapshot()
        doctor(self.root)
        self.assertEqual(before, self.snapshot())

    def test_doctor_reports_invalid_check_configuration(self):
        config = self.root / "agent-workflow.toml"
        config.write_text('[[checks]]\nid = "bad"\ncommand = "echo unsafe"\n', encoding="utf-8")
        before = self.snapshot()
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["doctor", str(self.root)]), 2)
        self.assertIn("command", output.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_status_reports_onboarding_pending(self):
        initialize(self.root)
        self.assertEqual(status(self.root).onboarding, "pending")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["status", str(self.root)]), 0)
        self.assertIn("pending", output.getvalue())

    def test_status_lists_active_changes_from_both_conventions(self):
        initialize(self.root)
        openspec = "openspec/changes/new-api"
        fallback = "docs/agent-workflow/changes/new-dashboard"
        for name in (openspec, fallback, "openspec/changes/archive/old-api"):
            (self.root / name).mkdir(parents=True)
        report = status(self.root)
        self.assertEqual(set(report.active_changes), {openspec, fallback})
