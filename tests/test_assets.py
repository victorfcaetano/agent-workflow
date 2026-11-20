import unittest
from pathlib import PurePosixPath, PureWindowsPath

from agent_workflow.assets_manifest import list_assets


class AssetTests(unittest.TestCase):
    def test_asset_catalog_contains_required_roots(self):
        self.assertTrue({"AGENTS.md", "CLAUDE.md"}.issubset(list_assets()))

    def test_asset_paths_are_relative_and_unique(self):
        seen = set()
        for name in list_assets():
            with self.subTest(name=name):
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute())
                self.assertFalse(PureWindowsPath(name).anchor)
                self.assertNotIn("..", path.parts)
                self.assertNotIn("\\", name)
                self.assertTrue(path.parts)
                self.assertEqual(path.as_posix(), name)
                self.assertNotIn(name.casefold(), seen)
                seen.add(name.casefold())

    def test_all_assets_decode_as_utf8(self):
        for name, content in list_assets().items():
            with self.subTest(name=name):
                self.assertIsInstance(content, bytes)
                content.decode("utf-8")
