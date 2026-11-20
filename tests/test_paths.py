import stat
import tempfile
import unittest
from pathlib import Path

from agent_workflow.paths import atomic_write


class PathTests(unittest.TestCase):
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
