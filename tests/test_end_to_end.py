import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp = Path(temporary.name)

    def run_python(self, *args, cwd=ROOT, expected=0):
        run = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, text=True,
                             errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             timeout=180, check=False)
        self.assertEqual(run.returncode, expected, run.stdout)
        return run.stdout

    def test_init_to_verify_and_remove_flow(self):
        project = self.temp / "project"
        project.mkdir()
        instructions = project / "AGENTS.md"
        user_text = b"# Team instructions\r\nKeep this file."
        instructions.write_bytes(user_text)
        self.run_python("-m", "agent_workflow", "init", project)
        self.run_python("-m", "agent_workflow", "verify", project, expected=2)
        config = project / "agent-workflow.toml"
        argv = [sys.executable, "-c", "from pathlib import Path; Path('checked').touch()"]
        with config.open("a", encoding="utf-8") as file:
            file.write('\n[[checks]]\nid = "smoke"\ncommand = ' + json.dumps(argv) + "\n")
        saved_config = config.read_bytes()
        self.run_python("-m", "agent_workflow", "verify", project)
        self.assertTrue((project / "checked").is_file())
        self.run_python("-m", "agent_workflow", "remove", project)
        self.assertEqual(instructions.read_bytes(), user_text)
        self.assertEqual(config.read_bytes(), saved_config)
        self.assertTrue((project / "docs/agent-workflow/context-index.md").is_file())
        self.assertFalse((project / ".agent-workflow/manifest.json").exists())

    def test_update_flow_preserves_custom_skill(self):
        self.run_python("-m", "agent_workflow", "install", self.temp)
        skill = Path(".agents/skills/agent-workflow/SKILL.md")
        incoming = (self.temp / skill).read_bytes()
        (self.temp / skill).write_bytes(b"Team customization")
        unowned = self.temp / ".agents/skills/private/SKILL.md"
        unowned.parent.mkdir()
        unowned.write_bytes(b"Project-owned procedure")
        output = self.run_python("-m", "agent_workflow", "update", self.temp, expected=1)
        proposal = Path(".agent-workflow/updates") / skill
        self.assertIn(proposal.as_posix(), output)
        self.assertEqual((self.temp / proposal).read_bytes(), incoming)
        self.assertEqual((self.temp / skill).read_bytes(), b"Team customization")
        self.assertEqual(unowned.read_bytes(), b"Project-owned procedure")

    def test_new_software_example_checks_pass(self):
        project = EXAMPLES / "new-software"
        output = self.run_python("-m", "agent_workflow", "verify", project)
        self.assertIn("page-range-tests (required) passed", output)
        self.assertNotIn("Ran 0 tests", output)
        self.assertEqual(self.run_python("page_ranges.py", "5,1-3,2,4-5,8", cwd=project).strip(), "1-5,8")

    def test_synthetic_data_pipeline_and_quality_checks_pass(self):
        project = EXAMPLES / "data-engineering"
        output = self.run_python("-m", "agent_workflow", "verify", project)
        self.assertIn("pipeline-tests (required) passed", output)
        self.assertNotIn("Ran 0 tests", output)
        database = self.temp / "orders.sqlite"
        self.run_python("pipeline.py", database, cwd=project)
        with closing(sqlite3.connect(database)) as db:
            rows = db.execute("SELECT customer_id, paid_orders, revenue_cents "
                              "FROM customer_sales ORDER BY customer_id").fetchall()
        self.assertEqual(rows, [("C001", 2, 2000), ("C002", 1, 1800),
                                ("C003", 0, 0), ("C004", 0, 0)])

    def test_built_wheel_includes_hidden_agent_skills(self):
        source = self.temp / "source"
        source.mkdir()
        shutil.copytree(ROOT / "agent_workflow", source / "agent_workflow",
                        ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, source / name)
        wheels = self.temp / "wheels"
        self.run_python("-m", "pip", "--disable-pip-version-check", "wheel", "--no-deps",
                        "--wheel-dir", wheels, ".", cwd=source)
        wheel, = wheels.glob("*.whl")
        with zipfile.ZipFile(wheel) as archive:
            for host in (".agents", ".claude"):
                for skill in ("agent-workflow", "agent-workflow-onboarding"):
                    path = f"agent_workflow/assets/{host}/skills/{skill}/SKILL.md"
                    with self.subTest(path=path):
                        self.assertEqual(archive.read(path), (source / path).read_bytes())
