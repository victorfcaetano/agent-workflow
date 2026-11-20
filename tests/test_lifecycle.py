import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from threading import Event
from unittest.mock import patch

from agent_workflow.cli import main
from agent_workflow.lifecycle import install, remove, update
from agent_workflow.manifest import Manifest
from agent_workflow.paths import atomic_write


BLOCK = b"<!-- agent-workflow:begin -->\nOriginal map\n<!-- agent-workflow:end -->\n"
SKILL = ".agents/skills/work/SKILL.md"


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.agents = self.root / "AGENTS.md"
        self.skill = self.root / SKILL
        self.assets = {"AGENTS.md": BLOCK, "CLAUDE.md": BLOCK, SKILL: b"Original skill\n"}
        assets = patch("agent_workflow.lifecycle.list_assets", return_value=self.assets)
        assets.start()
        self.addCleanup(assets.stop)

    def test_install_is_idempotent(self):
        install(self.root)

        def snapshot():
            return {p.relative_to(self.root): (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in self.root.rglob("*") if p.is_file()}

        before = snapshot()
        install(self.root)
        self.assertEqual(snapshot(), before)
        self.assertEqual(self.agents.read_bytes(), BLOCK)
        self.assertEqual(Manifest.load(self.root).files[SKILL].source_version, "0.1.0")

    def test_install_preserves_existing_instruction_text(self):
        original = b"# Repository policies\r\n\r\nUse UTF-8: \xc3\xa9"
        self.agents.write_bytes(original)
        install(self.root)
        self.assertIn(original, self.agents.read_bytes())
        self.assertIn(BLOCK, self.agents.read_bytes())
        remove(self.root)
        self.assertEqual(self.agents.read_bytes(), original)

    def test_install_does_not_claim_unowned_files(self):
        self.skill.parent.mkdir(parents=True)
        self.skill.write_bytes(self.assets[SKILL])
        self.agents.write_bytes(BLOCK)
        install(self.root)
        entries = Manifest.load(self.root).files
        self.assertNotIn(SKILL, entries)
        self.assertNotIn("AGENTS.md", entries)
        remove(self.root)
        self.assertEqual(self.skill.read_bytes(), self.assets[SKILL])
        self.assertEqual(self.agents.read_bytes(), BLOCK)

    def test_update_replaces_unchanged_managed_asset(self):
        install(self.root)
        self.assets[SKILL] = b"Fresh skill\n"
        update(self.root)
        self.assertEqual(self.skill.read_bytes(), b"Fresh skill\n")
        remove(self.root)
        self.assertFalse(self.skill.exists())

    def test_update_refreshes_managed_block_without_losing_user_text(self):
        install(self.root)
        self.agents.write_bytes(b"prefix\r\n" + BLOCK + b"suffix")
        incoming = BLOCK.replace(b"Original", b"Fresh")
        self.assets["AGENTS.md"] = incoming
        update(self.root)
        self.assertEqual(self.agents.read_bytes(), b"prefix\r\n" + incoming + b"suffix")

    def test_update_preserves_modified_asset_and_writes_conflict(self):
        install(self.root)
        self.skill.write_bytes(b"Project skill")
        self.assets[SKILL] = b"New skill"
        report = update(self.root)
        self.assertIn(SKILL, report.conflicts)
        self.assertEqual(self.skill.read_bytes(), b"Project skill")
        artifact = self.root / report.conflicts[SKILL]
        self.assertTrue(artifact.is_relative_to(self.root / ".agent-workflow/updates"))
        self.assertEqual(artifact.read_bytes(), b"New skill")
        artifact.write_bytes(b"Reviewed copy")
        retry = update(self.root)
        self.assertEqual(artifact.read_bytes(), b"Reviewed copy")
        self.assertEqual((self.root / retry.conflicts[SKILL]).read_bytes(), b"New skill")

    def test_update_preserves_modified_managed_block(self):
        install(self.root)
        custom = BLOCK.replace(b"Original map", b"Local policy")
        self.agents.write_bytes(custom)
        report = update(self.root)
        self.assertEqual(self.agents.read_bytes(), custom)
        self.assertEqual((self.root / report.conflicts["AGENTS.md"]).read_bytes(), BLOCK)
        removed = remove(self.root)
        self.assertIn("AGENTS.md", removed.preserved)
        self.assertEqual(self.agents.read_bytes(), custom)

    def test_update_and_remove_cannot_publish_inconsistent_ownership(self):
        install(self.root)
        incoming = BLOCK.replace(b"Original map", b"Updated map")
        self.assets["AGENTS.md"] = incoming
        writing = Event()
        proceed = Event()

        def pause_first_write(path, payload):
            if path == self.agents and payload == incoming:
                writing.set()
                if not proceed.wait(10):
                    raise TimeoutError("Timed out waiting for concurrent remove")
            atomic_write(path, payload)

        with patch("agent_workflow.lifecycle.atomic_write", side_effect=pause_first_write):
            with ThreadPoolExecutor(max_workers=1) as executor:
                updating = executor.submit(update, self.root)
                try:
                    self.assertTrue(writing.wait(10))
                    try:
                        remove(self.root)
                    except ValueError:
                        pass  # A busy project can ask the caller to retry.
                finally:
                    proceed.set()
                try:
                    updating.result()
                except (OSError, ValueError):
                    pass
        if Manifest.load(self.root) is None:
            self.assertEqual(list(self.root.iterdir()), [])
        else:
            self.assertEqual(self.agents.read_bytes(), incoming)
            self.assertEqual(self.skill.read_bytes(), self.assets[SKILL])
            self.assertEqual((self.root / "CLAUDE.md").read_bytes(), BLOCK)

    def test_remove_deletes_only_unchanged_owned_files(self):
        (self.root / ".agents").mkdir()
        install(self.root)
        remove(self.root)
        self.assertEqual(set(self.root.iterdir()), {self.root / ".agents"})
        self.assertEqual(list((self.root / ".agents").iterdir()), [])

    def test_remove_preserves_user_text_around_unmodified_block(self):
        install(self.root)
        self.agents.write_bytes(b"prefix\r\n" + BLOCK + b"\nsuffix\r\n")
        remove(self.root)
        self.assertEqual(self.agents.read_bytes(), b"prefix\r\n\nsuffix\r\n")

    def test_remove_keeps_modified_and_unowned_files(self):
        self.agents.touch()
        install(self.root)
        unowned = self.skill.with_name("notes")
        unowned.write_bytes(b"Notes")
        self.skill.write_bytes(b"Edited")
        report = remove(self.root)
        self.assertIn(SKILL, report.preserved)
        self.assertEqual(self.skill.read_bytes(), b"Edited")
        self.assertEqual(unowned.read_bytes(), b"Notes")
        self.assertEqual(self.agents.read_bytes(), b"")

    def test_cli_reports_conflict_and_artifact(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["install", str(self.root)]), 0)
            self.skill.write_bytes(b"Local")
            status = main(["update", str(self.root)])
        self.assertNotEqual(status, 0)
        self.assertIn(SKILL, stdout.getvalue())
        self.assertIn(".agent-workflow/updates/", stdout.getvalue())

    def test_unsafe_destination_is_rejected_before_other_writes(self):
        with tempfile.TemporaryDirectory() as other:
            try:
                os.symlink(other, self.root / ".agents", target_is_directory=True)
            except OSError as error:
                if os.name != "nt" or error.winerror != 1314:
                    raise
                # Windows junctions exercise path redirection without elevation.
                import _winapi
                _winapi.CreateJunction(other, str(self.root / ".agents"))
            with self.assertRaises(ValueError):
                install(self.root)
            self.assertFalse(self.agents.exists())
            self.assertEqual(list(Path(other).iterdir()), [])
