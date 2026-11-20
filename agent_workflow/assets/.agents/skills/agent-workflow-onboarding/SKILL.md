---
name: agent-workflow-onboarding
description: Use when the user requests project onboarding or missing project knowledge materially affects nontrivial work.
---

# Onboard a repository

Use repository evidence and focused questions to build a small project context index. Run onboarding only when requested or when missing knowledge materially affects nontrivial work. Keep quick tasks focused on the affected files.

## Investigate the project

1. Read the root and scoped instructions and check the working tree for existing user work. Inspect `agent-workflow.toml` and `docs/agent-workflow/context-index.md` when present. If scaffolding is missing and onboarding is authorized, run `agent-workflow init` from the project root. It creates missing templates and marks a newly initialized project `pending`.
2. For a new project, capture the user's goals, intended users, core behavior, constraints, and initial acceptance checks. Inspect any seed files. Record unmade technical or business choices as open questions and treat proposed architecture as a hypothesis until decided or implemented.
3. For an existing project, inspect its README and contributor instructions, dependency manifests and lockfiles, entry points, module boundaries, schemas or migrations, test configuration, CI, and operational runbooks. Trace representative workflows from inputs to outputs. Use local checks when authorized, and record whether a claim comes from source inspection or an observed run.
4. Reconcile contradictions by checking implementation and current configuration. Ask focused questions about missing business decisions or gaps that block useful work. Follow host permissions for dependencies, credentials, network access, and operational commands.

## Record evidence in project files

- **Verified** — State a fact supported by a concrete source or observed result. Cite a repository-relative path and symbol or section, or the command and outcome. For example, `Verified` that the CI unit job invokes `python -m unittest discover -v` if that command appears in the current workflow file.
- **Hypothesis** — State what appears likely, the evidence that led to the inference, and how to confirm it.
- **Open question** — State what is unknown and the decision or evidence needed to resolve it.

Keep `docs/agent-workflow/context-index.md` as a map of topic links. Put detail in the relevant file and preserve existing project-owned notes.

| File | Record |
| --- | --- |
| `architecture.md` | Entry points, components, dependencies, boundaries, and important data flows. |
| `domain.md` | Business terms, invariants, data ownership, and user workflows. |
| `operations.md` | Local setup, runtime, deployment, and known recovery procedures. |
| `validation.md` | How to run checks, where coverage matters, and known validation gaps. |
| `open-questions.md` | Cross-cutting decisions and unresolved questions with impact and an owner or next action where known. |

Add more topic files only when justified and link them in the index. Keep credentials, raw private data, and environment-specific secrets out of these files. Add validation entries to `agent-workflow.toml` when the commands and their intended scope are understood. Use `[[checks]]` tables with an `id`, a `command` array, and an optional project-relative `cwd`, `timeout_seconds`, and `required`.

## Finish or resume

Read back the index and check that its links resolve. Review the evidence labels, note outstanding questions and check prerequisites, and reconcile any contradictions you can resolve. Once there is enough verified context for the current project scope, set `[onboarding].status` to `"complete"` in `agent-workflow.toml` and report remaining uncertainties. Leave onboarding `pending` when essential facts are still missing, record the blocker and the next action, and resume from those notes when the evidence is available.
