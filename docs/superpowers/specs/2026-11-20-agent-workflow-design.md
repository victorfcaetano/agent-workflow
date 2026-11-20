# Agent Workflow Design

## Intent

Build a public, reusable harness that makes Claude Code and Codex follow a consistent, project-aware software workflow with little always-loaded context. Developers should install it once in a repository, initialize project knowledge once, and then work with the agent in natural language. The agent remains responsible for its authorized task through implementation, review, and objective validation; it asks for help only when a decision or permission genuinely belongs to the user.

## Goals

- Provide a stack-independent core methodology with thin native adapters for Claude Code and Codex.
- Discover relevant project context on demand and keep durable, verified project knowledge in the repository.
- Scale ceremony to task complexity and risk; use OpenSpec artifacts for substantial behavior or architecture changes.
- Support new-project and existing-project onboarding, including verified facts, hypotheses, and open questions.
- Provide safe, repeatable install, initialize, update, diagnose, verify, and remove commands.
- Preserve user-owned files and customizations across installation, updates, and removal.
- Keep long work resumable through durable task artifacts and explicit next steps, with a bounded, non-looping workflow.
- Make validation deterministic and extensible by each project, with subagents and independent review used when their cost is justified.
- Ship two runnable examples, tests, CI, public documentation, and an open-source license.

## Non-goals

- Reimplement either agent's model loop, permission system, sandbox, memory, or subagent runtime.
- Require a particular language, framework, MCP server, issue tracker, or skill collection in projects using the harness.
- Automatically run arbitrary project commands, install dependencies, grant permissions, or enable hooks during installation.
- Force specifications, multi-agent delegation, or a separate reviewer for every small task.
- Claim that static checks can prove an agent followed every natural-language instruction.

## Constraints and operating rules

- Primary repository language: English. Project-specific context may use the project's chosen language.
- Runtime and CLI: Python 3.11+, standard library only. Package installation may use the normal Python build tooling; no runtime dependencies.
- Support Windows, macOS, and Linux. Validation commands are argument arrays and run without a shell.
- Installation is repository-scoped by default. Do not edit `~/.claude`, `~/.codex`, user permissions, MCP configuration, or existing hook definitions.
- Only write to missing files or to paths recorded as owned by the installer. Updates preserve modified managed files and report a conflict artifact for review. Removal deletes only unchanged files still owned by the installer.
- Hooks are optional, agent-specific, and require explicit project/user configuration. Default operation relies on native skills/instructions and explicit deterministic validation.
- The workflow uses the native task, skill, memory, permission, and subagent facilities of each agent; no cross-agent background daemon or forced auto-continue loop.

## Approaches considered

1. **One universal prompt file.** Lowest implementation and install cost, but context grows with every project and it cannot express task-specific procedures or deterministic checks cleanly. Rejected.
2. **A central execution orchestrator.** A daemon/loop could enforce continuation and coordinate tools uniformly, but would duplicate native agent capabilities, require more runtime and permission surface, and make installation less portable. Rejected.
3. **A thin installer plus shared, progressively disclosed workflow assets and native adapters.** A concise root instruction map routes work to shared Agent Skills; vendor files expose the same workflow to Claude Code and Codex. A stdlib CLI safely manages files and runs project-declared validations. OpenSpec is detected and used for substantial changes, while domain skills and context remain project-owned. Selected because it preserves native agent behavior, allows deterministic checks, and keeps the mandatory context and runtime small.

## Architecture

### Universal core

The repository ships a Python package/CLI (`agent-workflow`) with `install`, `init`, `update`, `doctor`, `status`, `verify`, and `remove` commands. `init` is a noninteractive bootstrap: it installs the harness if needed, creates an empty context index and onboarding status, and leaves technology/domain facts for the AI onboarding skill to investigate. That skill runs when the user asks for onboarding or when an incomplete onboarding state materially affects a nontrivial task; a quick task does not trigger a repository-wide audit. This boundary avoids a generic scanner silently presenting guesses as verified facts. The CLI installs a small `AGENTS.md` routing map for Codex, a `CLAUDE.md` adapter that imports the shared map when needed, and shared skills in the locations each host discovers. The universal work skill classifies a task by impact, gives short tasks a direct path, and sends substantial changes through requirements, acceptance criteria, a dependency-aware plan, incremental implementation, evidence, and a final review.

The installer maintains a project manifest of managed paths and hashes. It does not treat an entire vendor directory as its property. On update, unmodified owned files advance; modified files are kept and the incoming version is written to a clearly named update-conflict location. On removal, only unchanged owned files are deleted. Existing root instruction files are extended only through an exact, clearly marked managed block; if a block was changed by the project, updates/removal preserve it and report the conflict.

### Project extension points

Projects own `agent-workflow.toml`, `docs/agent-workflow/`, and additional skills under `.agents/skills/` and `.claude/skills/`. Onboarding records a context index and small topic-specific documents for architecture, domains, operations, dependencies, and validation. Each document distinguishes verified facts, hypotheses, and open questions. Onboarding is performed by the agent using repository tools and focused interviews, not by generic code that claims to understand arbitrary stacks. Projects register their own validation checks as argument arrays with working directories and timeouts; the CLI runs those commands with `shell=False` and reports each result. User-level preferences live separately in the platform's standard config directory and are never written by the project installer. Claude/Codex permissions and organizational policies remain under their native controls.

### Work lifecycle and OpenSpec

Small, reversible changes stay lightweight. For work that changes public behavior, domain rules, architecture, or several components, the agent uses OpenSpec's change folder and requirement/design/task artifacts as the durable contract and cross-session handoff. It consults existing context first, records decisions and progress in the change artifacts, implements in verified increments, and archives only after acceptance and project checks pass. When OpenSpec is unavailable, the workflow reports that fact and uses its local change template; it never installs a tool or reaches the network without an explicit command.

The core encourages native subagents only for independent research, implementation, or evaluation work. The coordinator owns shared-file integration and final acceptance. Parallel write work requires isolated worktrees or disjoint paths; shared-state conflicts, context cost, and agent limits can make a single agent faster. The default does not wire a Stop hook: checkpointing, status, task artifacts, and explicit resume instructions provide continuity without an unbounded shell loop. Hooks may be added by a project when a deterministic event check is useful and the project has reviewed its permissions.

### Distribution and examples

The package installs from a source checkout or a future public package index; the repository documents both. GitHub Actions runs the standard-library test suite and package checks on Windows, macOS, and Linux. A new-software example demonstrates project initialization and a small tested application. A data-engineering example uses synthetic CSV inputs and a runnable local SQLite pipeline with documented schema, lineage, business rules, and data-quality checks.

## Research and design decisions

- OpenAI's harness engineering write-up treats repository knowledge as the system of record and uses a short instruction file as a map to deeper sources. Its long-horizon article reinforces that sustained work needs incremental steps and durable artifacts. This supports the short-map/context-index design rather than one large root prompt.
- OpenAI's GPT-6 Astra skills guidance recommends concise trigger descriptions and progressive disclosure, loading detailed skill instructions only when relevant. The core will therefore use small skill descriptions and focused references/scripts rather than a broad omnibus instruction.
- Anthropic's long-running-agent experiments use initializer/coding roles, incremental task lists, progress notes, and clean handoffs between context windows. Its later planner/generator/evaluator work shows that independent evaluation is valuable near capability boundaries but adds overhead; the workflow therefore scales review and delegation with task risk.
- Official Claude Code documentation exposes project memory/instructions, skills, subagents, hooks, and native permission settings. Official Codex documentation exposes layered `AGENTS.md`, skills, subagents, hooks, and project trust. The adapters preserve those native discovery and trust boundaries instead of changing user settings.
- OpenSpec currently supports both Claude Code and Codex through shared skills. Its change folders, validation, status, and archive lifecycle fit substantive work and resumable plans. It is an optional integration rather than a vendored dependency because its CLI has an independent release cycle and simple tasks do not need the additional artifacts.
- Matt Pocock's skills repository packages specific engineering workflows and currently supports Claude Code/Codex plugin installation. The project will borrow the narrow-skill and explicit acceptance-criteria pattern, but will not copy or require the collection: its larger, opinionated workflow overlaps with the proposed core and would introduce a second authority.

Primary references reviewed on 2026-11-20:

- [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/)
- [OpenAI: Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
- [OpenAI: Run long-horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
- [Anthropic: Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps)
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)
- [Claude Code: memory](https://code.claude.com/docs/en/memory), [skills](https://code.claude.com/docs/en/skills), [subagents](https://code.claude.com/docs/en/sub-agents), [hooks](https://code.claude.com/docs/en/hooks), and [permissions](https://code.claude.com/docs/en/permissions)
- [Codex: AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [skills](https://developers.openai.com/codex/skills), [subagents](https://developers.openai.com/codex/subagents), and [hooks](https://learn.chatgpt.com/docs/hooks)
- [OpenSpec supported tools](https://openspec.dev/docs/supported-tools) and [CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)
- [Matt Pocock skills](https://github.com/mattpocock/skills)

## Calls left to the builder

- Choose exact CLI option names, manifest schema, skill names, and minimal file templates while preserving the constraints above.
- `init` scaffolds project context and marks onboarding incomplete; the agent does fact-finding on demand and writes verified findings. This resolves the builder-check question about whether the CLI should inspect arbitrary repositories itself.
- Select stable GitHub Actions runner/tool versions available when CI is authored.
- Keep the supported compatibility matrix honest: test installer behavior and static host artifact layout in CI; document that semantic agent behavior still depends on the installed Claude Code/Codex release and cannot be proven without authenticated host sessions.
- Keep the v1 scope small enough to ship all required end-to-end flows, examples, and documentation rather than attempting generic agent orchestration.
