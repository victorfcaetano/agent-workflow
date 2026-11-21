# Architecture

Agent Workflow consists of a Python CLI, a small instruction router, and two skills. The CLI manages files and runs explicitly requested validation. Claude Code and Codex supply the agent session, tools, permissions, memory, and subagents.

## Install and project ownership

| Path | Ownership and purpose |
| --- | --- |
| `AGENTS.md` and `CLAUDE.md` | The installer tracks only the marked block in each file. `AGENTS.md` is the shared router and `CLAUDE.md` imports it. Put project-specific root instructions outside the managed block. |
| `.agents/skills/agent-workflow*/` and `.claude/skills/agent-workflow*/` | The installer tracks the bundled skill files individually. Each skill has matching contents across hosts. Projects own separately named skills. |
| `.agent-workflow/manifest.json` | Records the managed paths and hashes used to compare installed files or blocks against their last installed contents. |
| `agent-workflow.toml` and `docs/agent-workflow/` | The project owns the check configuration, onboarding state, topic documents, and local task records. `init` creates missing starter files. |
| `openspec/` | The project's OpenSpec configuration, changes, and specs when that integration is in use. |

`install` adds the routers and skills. `init` also creates an index and starter topic files, with onboarding initially `pending`. The onboarding skill investigates the repository with local tools and records facts with sources. It labels inferences and unanswered questions so later agents can distinguish them from observations.

`update` replaces unchanged managed content. If managed content was modified, it preserves the installed copy and writes the incoming candidate under `.agent-workflow/updates/` for review. `remove` removes unchanged managed content and keeps project edits. Lifecycle mutations use `.agent-workflow.lock` to serialize writes. If a process is interrupted and leaves the file, use `doctor` to locate it and inspect the operation and project state before clearing the lock.

Manifest paths are restricted to the current package asset catalog and an explicit retired-path list, so a manifest cannot claim a README or other project file. If rollback cannot restore the original snapshot, the CLI saves recoverable original bytes and modes in `.agent-workflow/recovery/rollback-*.json`; `doctor` reports these artifacts for manual inspection.

## Work and continuity

The root routers point to the project context index and skill names. Skills load their procedures when relevant. A small repair can go straight from inspection to a focused check. Medium work gets a short plan and checkpoints. Changes to public behavior, business rules, architecture, or multiple components get requirements, acceptance checks, and a durable change record.

When configured, OpenSpec provides the change artifacts and archive workflow. The work skill supplies a local template under `docs/agent-workflow/changes/` for projects without a usable OpenSpec setup. Both paths record verified progress, assumptions, blockers, and the next task. `agent-workflow status` lists local active changes and onboarding state. Native subagents can handle independent tasks, and the coordinator integrates their work and verifies the result.

The workflow continues through authorized, recoverable work. Checkpoints help the next session resume from evidence. Project hooks are opt-in. See [compatibility](compatibility.md) for host discovery and [extending the workflow](extending.md) for topic and validation examples.

## Design references

- The short router and linked repository knowledge follow OpenAI's harness engineering approach. [Harness engineering](https://openai.com/index/harness-engineering/)
- Concise skill descriptions and on-demand detail follow OpenAI's progressive disclosure guidance. [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
- Milestones, acceptance criteria, and observed checks provide a durable record of long work. [Run long-horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
- Resumable work benefits from incremental verification and explicit progress records. Independent evaluation adds value when a change is difficult to verify reliably in the implementation pass. [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents), [Harness design for long-running application development](https://www.anthropic.com/research/harness-design-long-running-apps)
