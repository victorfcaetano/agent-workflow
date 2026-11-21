import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_workflow import lifecycle
from agent_workflow.commands import initialize
from agent_workflow.lifecycle import remove
from agent_workflow.manifest import Manifest


class InitTests(unittest.TestCase):
    def test_init_installs_and_creates_pending_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "new-project"
            report = initialize(root)
            self.assertIn("AGENTS.md", report.changed)
            self.assertTrue((root / "CLAUDE.md").is_file())
            config = root / "agent-workflow.toml"
            data = tomllib.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(data["onboarding"]["status"], "pending")
            self.assertEqual(data.get("checks", []), [])
            context = root / "docs/agent-workflow"
            names = {"context-index.md", "architecture.md", "domain.md", "operations.md",
                     "validation.md", "open-questions.md"}
            self.assertEqual({p.name for p in context.iterdir()}, names)
            self.assertNotIn("agent-workflow.toml", Manifest.load(root).files)
            self.assertEqual(initialize(root).changed, [])
            remove(root)
            self.assertTrue(config.is_file())
            self.assertEqual({p.name for p in context.iterdir()}, names)

    def test_init_preserves_existing_project_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fact = root / "docs/agent-workflow/architecture.md"
            fact.parent.mkdir(parents=True)
            fact.write_bytes(b"Project-owned diagram\r\n")
            config = root / "agent-workflow.toml"
            config.write_bytes(b'[onboarding]\nstatus = "complete"\n')
            initialize(root)
            self.assertEqual(fact.read_bytes(), b"Project-owned diagram\r\n")
            self.assertEqual(config.read_bytes(), b'[onboarding]\nstatus = "complete"\n')
            self.assertTrue((fact.parent / "context-index.md").is_file())

    def test_init_rolls_back_install_when_context_write_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = lifecycle.atomic_write

            def fail_in_context(path, content, **kwargs):
                if path.name == "domain.md":
                    raise PermissionError("Injected context write failure")
                return original(path, content, **kwargs)

            with patch("agent_workflow.lifecycle.atomic_write", side_effect=fail_in_context):
                with self.assertRaisesRegex(PermissionError, "context write failure"):
                    initialize(root)
            self.assertEqual(list(root.iterdir()), [])
