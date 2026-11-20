# Extend the workflow for your project

Use `docs/agent-workflow/context-index.md` to link project knowledge. Add a new topic file when enough material warrants one. Keep facts with their supporting source or observed check, mark inferences as hypotheses, and record open questions with the decision or evidence they need.

## Add a domain skill

Create a separately named directory under `.agents/skills/` for Codex and `.claude/skills/` for Claude Code. Put a `SKILL.md` with a `name` and a concise trigger `description` in each. Keep the host copies in sync. Put project facts in the topic documents and link a skill to the relevant files. Add a supporting reference or script only when its contents serve a focused procedure.

| Example skill | When it applies | Project guidance |
| --- | --- | --- |
| `python-testing` | Python package changes | Test discovery, fixture conventions, and the supported Python versions. |
| `sql-pipelines` | Schema, transform, or migration changes | Input contracts, lineage, null and duplicate handling, migration order, and data-quality checks. |
| `web-ui` | User-facing interaction changes | Accessible patterns, browser targets, component conventions, and UI verification. |

Matt Pocock's skills repository documents plugin installation for both Claude Code and Codex. Its narrowly named skills and emphasis on concrete acceptance criteria informed this workflow. Projects can adopt individual practices after reviewing how they fit their own instructions. Agent Workflow has no dependency on the collection. [Matt Pocock's skills repository](https://github.com/mattpocock/skills)

## Register deterministic checks

Add one `[[checks]]` table per command in the project's `agent-workflow.toml`. For example, a Python project can register its unit tests as follows.

```toml
[[checks]]
id = "unit"
command = ["python", "-m", "unittest", "discover", "-v"]
cwd = "."
timeout_seconds = 60
required = true
```

Each `id` must be unique. The `command` array contains an executable followed by its arguments. `cwd` defaults to `.` and must resolve to a directory within the project. `timeout_seconds` is an integer from 1 to 3600 and defaults to 60. `required` defaults to `true`. Use a real executable on Windows because `.bat` and `.cmd` commands are rejected. Keep validation prerequisites and targeted run instructions in `docs/agent-workflow/validation.md`.

Run `agent-workflow verify` from the project root, or pass the project directory as its argument. It runs the configured commands in order with `shell=False` and reports each result. Required check failures make the command exit 1. Optional check failures appear in the report. Missing or invalid configuration is a usage error. Review the check list before running it in a repository you have just acquired because it contains executable project commands.

For a deterministic event check, a project can opt in to its host's hooks after reviewing the command, trigger, and permissions. The installer leaves that configuration to the project. [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Codex hooks](https://learn.chatgpt.com/docs/hooks)
