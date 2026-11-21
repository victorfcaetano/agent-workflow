# Compatibility

The CLI targets Python 3.11 and later on Windows, macOS, and Linux. The installer writes ordinary repository files. Host discovery depends on the client and release in use, the working directory, and project configuration.

| Host | Project instruction | Project skills | Manual invocation when available |
| --- | --- | --- | --- |
| Claude Code | Root `CLAUDE.md`, which imports `@AGENTS.md` | `.claude/skills/<name>/SKILL.md` | `/agent-workflow` or `/agent-workflow-onboarding` |
| Codex | Root `AGENTS.md`, with scoped files and overrides resolved by Codex | `.agents/skills/<name>/SKILL.md` | `$agent-workflow` or `$agent-workflow-onboarding` where mentions are supported, or the client's skill selector |

Claude Code loads imported content with `CLAUDE.md` and resolves relative imports from that file. Repository skills have their own discovery rules. [Claude Code instructions and memory](https://code.claude.com/docs/en/memory), [Claude Code skills](https://code.claude.com/docs/en/skills)

Claude Code added native `AGENTS.md` discovery in **2.1.277**. It is a fallback when a folder has no `CLAUDE.md`, so Agent Workflow keeps a small `CLAUDE.md` adapter that imports `@AGENTS.md`. This also supports older clients, and remains the compatibility path for provider sessions where native support may arrive later. [Claude Code 2.1.277 release](https://github.com/anthropics/claude-code/releases/tag/v2.1.277)

In Claude Code project cloud threads, repository `.claude/skills/` files are not available. Enable the skills for the Claude account or use a supported local session. [Claude Code skills in cloud sessions](https://code.claude.com/docs/en/skills#skills-in-cowork-and-cloud-sessions)

Codex builds its instruction chain from the repository root toward the current directory and scans applicable `.agents/skills/` directories. An `AGENTS.override.md` can take precedence at its directory level. [Codex custom instructions](https://developers.openai.com/codex/guides/agents-md), [Codex skills](https://developers.openai.com/codex/skills)

## OpenSpec and native controls

OpenSpec is optional and installed separately. For projects already configured to use it, current versions document Claude Code skills such as `/openspec-propose` and `/openspec-apply-change`, with Codex forms `$openspec-propose` and `$openspec-apply-change`. Use the names available in the installed profile. The work skill has a local change template for projects without a usable OpenSpec setup. [OpenSpec supported tools](https://openspec.dev/docs/supported-tools), [OpenSpec skills](https://openspec.dev/docs/skills), [OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)

Each host provides its own subagent tools and capability limits. Agent Workflow records coordination and review guidance in the skill. [Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [Codex subagents](https://developers.openai.com/codex/subagents)

Agent Workflow relies on native permissions, sandboxing, and organizational policy. The installer leaves user settings, MCP configuration, approvals, and existing hooks untouched. Hooks are opt-in. Review project hooks in the host before enabling them and use the host's trust and permission controls. [Claude Code permissions](https://code.claude.com/docs/en/permissions), [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Codex hooks](https://learn.chatgpt.com/docs/hooks)

## What verification covers

`agent-workflow doctor` performs read-only static diagnostics. It reports `claude`, `codex`, and `openspec` on `PATH`, checks each expected instruction and skill file against the ownership manifest, and inspects project check configuration. It distinguishes unchanged managed assets, modified assets, unmanaged root instructions, and missing files. If a failed rollback could not restore an original file, it saves the original bytes and mode in `.agent-workflow/recovery/rollback-*.json`; inspect that artifact and the working tree before restoring it manually. A missing executable can be expected when a host runs in a separate client environment. CI can exercise the CLI, packaged files, and expected discovery layout on each operating system.

Interpretation, actual skill invocation, host policy, and adherence to workflow instructions require a live, authenticated session in the target host. To check a specific environment, open the repository in that client, confirm the expected instruction source and skill discovery, and run a small reversible task that exercises the workflow and its validation. Record the client or release and what you observed. Static checks establish the file contract only.
