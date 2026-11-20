import os
import stat
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

    def project_bytes(self):
        return {p.relative_to(self.root): p.read_bytes() if p.is_file() else None
                for p in self.root.rglob("*")}

    def test_stale_lock_blocks_noop_install_and_update(self):
        install(self.root)
        (self.root / ".agent-workflow.lock").write_bytes(b"prior operation")
        before = self.project_bytes()
        for operation in (install, update):
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(ValueError, "lock"):
                    operation(self.root)
                self.assertEqual(self.project_bytes(), before)

    def test_stale_lock_blocks_remove_without_manifest(self):
        (self.root / ".agent-workflow.lock").write_bytes(b"prior operation")
        self.agents.write_bytes(b"Unowned instructions")
        before = self.project_bytes()
        with self.assertRaisesRegex(ValueError, "lock"):
            remove(self.root)
        self.assertEqual(self.project_bytes(), before)

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

    def test_external_edit_between_replacement_steps_is_preserved(self):
        install(self.root)
        before = self.project_bytes()
        self.assets["AGENTS.md"] = BLOCK.replace(b"Original", b"Updated")
        self.assets[SKILL] = b"Updated skill"
        replace = Path.replace

        def edit_after_first_replacement(sibling, destination):
            result = replace(sibling, destination)
            if destination == self.agents and self.agents.read_bytes() == self.assets["AGENTS.md"]:
                self.skill.write_bytes(b"Concurrent edit")
            return result

        with patch.object(Path, "replace", edit_after_first_replacement):
            with self.assertRaises(ValueError):
                update(self.root)
        before[Path(SKILL)] = b"Concurrent edit"
        self.assertEqual(self.project_bytes(), before)

    def test_external_edit_between_deletions_is_preserved(self):
        install(self.root)
        before = self.project_bytes()
        unlink = Path.unlink

        def edit_after_first_deletion(path, *args, **kwargs):
            result = unlink(path, *args, **kwargs)
            if path == self.skill:
                self.agents.write_bytes(b"Concurrent edit")
            return result

        with patch.object(Path, "unlink", edit_after_first_deletion):
            with self.assertRaises(ValueError):
                remove(self.root)
        before[Path("AGENTS.md")] = b"Concurrent edit"
        self.assertEqual(self.project_bytes(), before)

    def test_update_refreshes_managed_block_without_losing_user_text(self):
        install(self.root)
        self.agents.write_bytes(b"prefix\r\n" + BLOCK + b"suffix")
        incoming = BLOCK.replace(b"Original", b"Fresh")
        self.assets["AGENTS.md"] = incoming
        update(self.root)
        self.assertEqual(self.agents.read_bytes(), b"prefix\r\n" + incoming + b"suffix")

    def test_rollback_conflict_preserves_edit_and_restores_other_files(self):
        install(self.root)
        before = self.project_bytes()
        claude = self.root / "CLAUDE.md"
        self.assets["AGENTS.md"] = self.assets["CLAUDE.md"] = BLOCK.replace(b"Original", b"Updated")
        self.assets[SKILL] = b"Updated skill"
        write_error = PermissionError("Injected skill write failure")

        def fail_write_and_edit_during_rollback(path, content, **kwargs):
            if path == self.skill:
                raise write_error
            if path == claude and content == BLOCK:
                # The rollback has selected this file. An editor saves before publication.
                claude.write_bytes(b"Edited during rollback")
            atomic_write(path, content, **kwargs)

        with patch("agent_workflow.lifecycle.atomic_write", side_effect=fail_write_and_edit_during_rollback):
            with self.assertRaises((OSError, ValueError)) as raised:
                update(self.root)
        before[Path("CLAUDE.md")] = b"Edited during rollback"
        self.assertEqual(self.project_bytes(), before)
        self.assertIs(raised.exception, write_error)

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

        def pause_first_write(path, payload, **kwargs):
            if path == self.agents and payload == incoming:
                writing.set()
                if not proceed.wait(10):
                    raise TimeoutError("Timed out waiting for concurrent remove")
            atomic_write(path, payload, **kwargs)

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

    def test_directory_prune_failure_restores_manifest_and_files(self):
        install(self.root)
        before = self.project_bytes()
        rmdir = Path.rmdir

        def fail_after_child_is_removed(path):
            if path == self.skill.parent.parent:
                self.assertFalse(self.skill.parent.exists())
                raise PermissionError("Injected directory prune failure")
            rmdir(path)

        with patch.object(Path, "rmdir", fail_after_child_is_removed):
            with self.assertRaisesRegex(PermissionError, "prune failure"):
                remove(self.root)
        self.assertEqual(self.project_bytes(), before)
        remove(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rollback_restores_original_file_mode(self):
        install(self.root)
        self.skill.chmod(0o444 if os.name == "nt" else 0o754)
        before = self.project_bytes()
        unlink = Path.unlink

        def fail_after_skill_deletion(path, *args, **kwargs):
            if path == self.agents:
                self.assertFalse(self.skill.exists())
                raise PermissionError("Injected removal failure")
            if path == self.skill and os.name == "nt":
                # Allow the test to inject a successful deletion of a read-only file.
                path.chmod(stat.S_IWRITE)
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", fail_after_skill_deletion):
            with self.assertRaisesRegex(PermissionError, "removal failure"):
                remove(self.root)
        self.assertEqual(self.project_bytes(), before)
        if os.name == "nt":
            self.assertTrue(self.skill.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
        else:
            self.assertEqual(stat.S_IMODE(self.skill.stat().st_mode), 0o754)

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
