---
name: agent-workflow
description: Use when implementing, fixing, reviewing, or resuming software work in this repository.
---

# Carry the task through validation

Confirm the requested outcome and constraints. Read applicable repository instructions, the relevant parts of `docs/agent-workflow/context-index.md`, and any active change that covers the work. Use `agent-workflow-onboarding` when requested or when missing context materially affects a nontrivial task.

## Match the workflow to the change

| Scope | Workflow |
| --- | --- |
| Small | For a localized, reversible change, inspect the affected area, make the change, and run a focused check. A change record is optional. |
| Medium | For a bounded change with several dependent steps, write a short plan with acceptance criteria and checks. Implement and verify in increments. Keep a progress record if work may span sessions. |
| Substantial or high-risk | For changes to public behavior, domain rules, architecture, or multiple components, use the project change workflow below. Define scope, acceptance criteria, dependencies, risks, and recovery or rollback where applicable before implementation. |

Reassess scope when new evidence changes impact or reversibility. State reasonable assumptions and proceed with authorized, in-scope work. A checkpoint records evidence and the next step. Continue after it without asking for approval. Ask only when the user must supply a business decision, resolve a blocker you cannot recover from, approve a scope change, or provide authorization. Describe the impact and continue any independent authorized work while waiting. Use the host's permission controls for gated actions.

## Substantial changes and OpenSpec

Reuse the active change that matches the request. Check for the `openspec` executable and a configured OpenSpec root before starting a new change. Use the project's schema and skills when available. In a terminal, useful commands include `openspec list`, `openspec status --change <id>`, `openspec instructions`, and `openspec validate <id>`.

| Host | Propose | Implement | Archive |
| --- | --- | --- | --- |
| Claude Code | `/openspec-propose` | `/openspec-apply-change` | `/openspec-archive-change` |
| Codex | `$openspec-propose` | `$openspec-apply-change` | `$openspec-archive-change` |

These are host skill invocations. In a Codex client with a skill selector, select the corresponding `openspec-*` skill. Match the names to the project's installed OpenSpec profile. A proposal records scope, requirement and scenario changes, design, and dependency-ordered tasks. Apply the tasks through verification, then archive only after acceptance and required project checks pass. Let the native skill handle confirmations it requires.

If the CLI or project setup is unavailable, record the reason and use the local fallback below. Preserve an existing OpenSpec change as the source of truth and link to it if local progress notes are necessary. If the user or project explicitly requires OpenSpec, report missing setup as a blocker for the OpenSpec-dependent steps. Request authorization before installing tools, initializing the OpenSpec integration, or using the network for setup.

### Local change template

Create `docs/agent-workflow/changes/<change-id>/change.md` with these headings. Keep the same record across sessions.

- **Outcome and scope** with boundaries and affected components.
- **Requirements and acceptance criteria** with concrete scenarios and the expected evidence.
- **Design and decisions** with assumptions, risks, and recovery steps where relevant.
- **Tasks** in dependency order with checkboxes and the check for each increment.
- **Progress and handoff** with completed work, evidence, blockers, and one concrete next step.

Move the finished local record to `docs/agent-workflow/archive/<change-id>/` after acceptance and required checks pass, following any existing project archive convention.

## Delegate when it improves delivery

Use native subagents where available and authorized for independent, bounded research, implementation, or review. Give each an outcome, the relevant context and constraints, specific file ownership, and the evidence to return. Use read-only assignments for shared investigation and isolated worktrees or strictly disjoint write paths for parallel edits. Keep sequential work together when setup, duplicated context, time, or token cost outweighs the benefit.

For changes with a significant blast radius, migrations, or subtle invariants, seek independent review when available and authorized. Give the reviewer acceptance criteria and the integrated diff. Ask for reproducible findings and prioritize by impact. The coordinator owns the shared files, resolves conflicts, checks subagent claims against the code and results, and runs final project checks.

## Verify and leave a resumable record

1. Implement a bounded increment. Review the diff and run its targeted check. Diagnose failures, make an in-scope correction, and rerun the affected checks. Stop retrying the same approach when it yields no new evidence.
2. Update the existing change artifacts or the project's task record at each milestone, before handoff, and before losing session context. Record the current branch or relevant revision, files touched, completed criteria, observed check results, remaining risks, and the next step. Keep secrets out of the record.
3. On resume, read the record and inspect the current working tree and active change status. Re-check stale evidence, preserve intervening edits, and start with the next unfinished task.
4. Compare the integrated result to each acceptance criterion. Run `agent-workflow verify` when checks are configured and add task-specific checks where needed. Use relevant project commands when no checks are registered. Record each result and any check that could not run. Inspect the final diff for accidental scope changes.
5. Finish when acceptance and required verification pass, or when the remaining work has a concrete blocker the user must resolve. Report the outcome, evidence, assumptions, and any remaining blocker with the exact next action. Continuity comes from the saved record and native task tools. Keep hooks opt-in and leave existing host configuration alone.
