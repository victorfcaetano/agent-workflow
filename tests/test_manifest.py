import json
import tempfile
import unittest
from pathlib import Path

from agent_workflow.lifecycle import install, remove, update
from agent_workflow.manifest import Manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = self.root / ".agent-workflow/manifest.json"
        self.manifest.parent.mkdir()

    def test_manifest_invalid_json_fails_before_writing(self):
        self.manifest.write_bytes(b"this is project data")
        for operation in (install, update, remove):
            with self.subTest(operation=operation.__name__), self.assertRaises(ValueError):
                operation(self.root)
        self.assertEqual(set(self.root.rglob("*")), {self.manifest.parent, self.manifest})
        self.assertEqual(self.manifest.read_bytes(), b"this is project data")

    def test_manifest_path_traversal_is_rejected(self):
        install(self.root)
        data = json.loads(self.manifest.read_bytes())
        for invalid in ("../other", "/absolute", "C:/other", "a/../b", "a\\b",
                        "C:relative", ".agent-workflow/manifest.json"):
            with self.subTest(path=invalid):
                data["files"][0]["path"] = invalid
                self.manifest.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    remove(self.root)
                self.assertTrue((self.root / "CLAUDE.md").exists())

    def test_malformed_or_duplicate_entries_are_rejected(self):
        install(self.root)
        raw = self.manifest.read_bytes()
        for field, value in (("sha256", "garbage"), ("source_version", ""),
                             ("kind", "directory"), ("created", 1)):
            with self.subTest(field=field):
                data = json.loads(raw)
                data["files"][0][field] = value
                self.manifest.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    Manifest.load(self.root)
        data = json.loads(raw)
        data["files"].append(data["files"][0])
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            Manifest.load(self.root)

        data = json.loads(raw)
        data["schema_version"] = 99
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            Manifest.load(self.root)

    def test_unrelated_directory_cannot_be_claimed_for_removal(self):
        install(self.root)
        notes = self.root / "notes"
        notes.mkdir()
        data = json.loads(self.manifest.read_bytes())
        data["directories"].append("notes")
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            remove(self.root)
        self.assertTrue(notes.is_dir())
        self.assertTrue((self.root / "AGENTS.md").is_file())
