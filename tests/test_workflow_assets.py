import re
import tempfile
import unittest
from pathlib import Path

from agent_workflow.assets_manifest import list_assets
from agent_workflow.commands import doctor, initialize

DOCS = Path(__file__).resolve().parents[1] / "docs"
HOSTS = (".agents", ".claude")
WORK = "agent-workflow"
ONBOARDING = "agent-workflow-onboarding"


class WorkflowAssetTests(unittest.TestCase):
    def setUp(self):
        self.assets = {name: data.decode("utf-8") for name, data in list_assets().items()}

    def skill(self, name, host=".agents"):
        path = f"{host}/skills/{name}/SKILL.md"
        self.assertIn(path, self.assets)
        return self.assets[path]

    def test_root_adapters_share_canonical_workflow(self):
        for name in ("AGENTS.md", "CLAUDE.md"):
            with self.subTest(name=name):
                lines = self.assets[name].splitlines()
                self.assertLess(len(lines), 100)
                self.assertEqual(lines[0], "<!-- agent-workflow:begin -->")
                self.assertEqual(lines[-1], "<!-- agent-workflow:end -->")
        self.assertIn("@AGENTS.md", self.assets["CLAUDE.md"].splitlines())
        for reference in (WORK, ONBOARDING, "docs/agent-workflow/context-index.md"):
            self.assertIn(reference, self.assets["AGENTS.md"])
        for name in (WORK, ONBOARDING):
            self.assertEqual(self.skill(name), self.skill(name, ".claude"))

    def test_skills_have_concise_frontmatter_descriptions(self):
        for host in HOSTS:
            for name in (WORK, ONBOARDING):
                with self.subTest(host=host, name=name):
                    lines = self.skill(name, host).splitlines()
                    self.assertEqual(lines[0], "---")
                    frontmatter = lines[1:lines.index("---", 1)]
                    self.assertIn(f"name: {name}", frontmatter)
                    descriptions = [line.removeprefix("description: ")
                                    for line in frontmatter if line.startswith("description: ")]
                    self.assertEqual(len(descriptions), 1)
                    self.assertTrue(descriptions[0].startswith("Use when "))
                    self.assertLessEqual(len(descriptions[0]), 180)

    def test_work_skill_covers_complexity_and_autonomy(self):
        work = self.skill(WORK).lower()
        for term in ("small", "medium", "substantial", "high-risk", "acceptance criteria",
                     "checkpoint", "authorization", "blocker", "next step", "subagent",
                     "worktree", "coordinator", "independent review"):
            with self.subTest(term=term):
                self.assertIn(term, work)

    def test_review_only_tasks_do_not_mutate(self):
        work = self.skill(WORK).lower()
        for term in ("review-only", "read-only", "do not modify", "full `agent-workflow verify` suite",
                     "when the task scope, acceptance criteria, or project policy calls for it",
                     "for a small change, run focused relevant checks"):
            with self.subTest(term=term):
                self.assertIn(term, work)

    def test_local_change_archive_moves_entire_directory(self):
        work = self.skill(WORK).lower()
        self.assertIn("docs/agent-workflow/archive/", work)
        self.assertIn("move the entire", work)
        self.assertIn("directory, including supporting files", work)

    def test_onboarding_marks_evidence_confidence(self):
        onboarding = self.skill(ONBOARDING)
        for term in ("Verified", "Hypothesis", "Open question", "new project", "existing project"):
            with self.subTest(term=term):
                self.assertIn(term, onboarding)

    def test_openspec_invocation_covers_both_hosts(self):
        work = self.skill(WORK)
        for term in ("/openspec-propose", "$openspec-propose", "openspec validate",
                     "openspec instructions --change <id>",
                     "docs/agent-workflow/changes/", "fallback"):
            with self.subTest(term=term):
                self.assertIn(term, work)

    def test_context_docs_are_separate_and_indexed(self):
        topics = {"architecture.md", "domain.md", "operations.md", "validation.md", "open-questions.md"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root)
            context = root / "docs" / "agent-workflow"
            index = (context / "context-index.md").read_text(encoding="utf-8")
            links = set(re.findall(r"\]\(([^)]+)\)", index))
            self.assertEqual(links, topics)
            self.assertTrue(all((context / topic).is_file() for topic in topics))
        onboarding = self.skill(ONBOARDING)
        for name in sorted(topics | {"context-index.md"}):
            with self.subTest(name=name):
                self.assertIn(name, onboarding)

    def test_compatibility_limits_are_explicit(self):
        with self.subTest(surface="documentation"):
            path = DOCS / "compatibility.md"
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8").lower()
            for term in ("static", "live", "authenticated", "hooks", "opt-in", "permissions",
                         "cloud threads", ".claude/skills/", "not available"):
                self.assertIn(term, text)
        with self.subTest(surface="doctor"):
            with tempfile.TemporaryDirectory() as directory:
                messages = "\n".join(item.message for item in doctor(Path(directory))).lower()
            self.assertIn("static", messages)
            self.assertIn("live", messages)
