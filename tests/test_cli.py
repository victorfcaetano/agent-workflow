import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

from agent_workflow import __version__
from agent_workflow.cli import main


class CliTests(unittest.TestCase):
    def test_version_prints_package_version(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["version"])

        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), f"{__version__}\n")

    def test_unknown_command_returns_usage_error(self):
        stderr = StringIO()
        with redirect_stderr(stderr):
            result = main(["unknown-command"])

        self.assertEqual(result, 2)
        self.assertIn("usage:", stderr.getvalue())
