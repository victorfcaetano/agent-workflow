import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_workflow.paths import atomic_write


class PathTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX mode bits are required")
    def test_atomic_write_new_files_respect_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "shared.txt"
            previous = os.umask(0o027)
            try:
                atomic_write(target, b"Shared project file")
            finally:
                os.umask(previous)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

    def test_atomic_write_unlinks_temp_when_chmod_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "new.txt"
            with patch.object(type(target), "chmod", side_effect=PermissionError("Injected chmod failure")):
                with self.assertRaisesRegex(PermissionError, "chmod failure"):
                    atomic_write(target, b"New file", mode=stat.S_IREAD)
            self.assertFalse(target.exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_atomic_write_removes_readonly_staged_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "read-only.txt"
            target.write_bytes(b"Existing file")
            target.chmod(stat.S_IREAD)
            original_mode = stat.S_IMODE(target.stat().st_mode)
            conflict = ValueError("Destination changed")

            def abort_replacement():
                raise conflict

            with self.assertRaises(ValueError) as raised:
                atomic_write(target, b"Incoming file", before_replace=abort_replacement)
            self.assertIs(raised.exception, conflict)
            self.assertEqual(set(root.iterdir()), {target})
            self.assertEqual(target.read_bytes(), b"Existing file")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), original_mode)
