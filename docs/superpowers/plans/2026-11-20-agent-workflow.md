# Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public-ready, cross-platform Agent Workflow harness for Claude Code and Codex, with safe lifecycle commands, project onboarding, durable work artifacts, deterministic validation, and runnable examples.

**Architecture:** A Python 3.11+ standard-library CLI installs versioned repository assets and tracks ownership by path/hash. Concise host instruction files route to shared, on-demand skills; the AI performs stack-aware onboarding and uses OpenSpec for substantial work. Project-owned TOML checks execute without a shell, while native agent permissions, skills, and subagent mechanisms remain in control.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `tomllib`, `unittest`, TOML, Markdown, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-20-agent-workflow-design.md`

## Global Constraints

- Runtime and CLI: Python 3.11+, standard library only.
- Support Windows, macOS, and Linux. Validation commands are argument arrays and run without a shell.
- Installation is repository-scoped by default. Do not edit `~/.claude`, `~/.codex`, user permissions, MCP configuration, or existing hook definitions.
- Only write to missing files or paths recorded as owned by the installer. Updates preserve modified managed files and report a conflict artifact for review. Removal deletes only unchanged files still owned by the installer.
- Hooks are optional, agent-specific, and require explicit project/user configuration. Default operation relies on native skills/instructions and explicit deterministic validation.
- The workflow uses the native task, skill, memory, permission, and subagent facilities of each agent; no cross-agent background daemon or forced auto-continue loop.
- Project facts are established by AI onboarding, not an arbitrary generic stack scanner; verified facts, hypotheses, and open questions remain distinguishable.
- No generated project validation command may run through a shell or execute automatically during install/init/update/remove.

## Review Focus

- A malformed, stale, or partially written ownership manifest must fail safely without overwriting project files. Test manifest validation and atomic recovery in Task 2.
- An existing `AGENTS.md` or `CLAUDE.md` may contain user rules and custom formatting. Test exact managed-block insertion and preservation in Task 2.
- A user-modified managed skill must survive update and removal; preserve the new upstream file in an update-conflict location. Test both lifecycle paths in Task 2.
- An invalid command array, out-of-root working directory, or slow validation command must be rejected or timed out without shell execution. Test in Task 3.
- Missing OpenSpec/agent CLIs and absent project context must produce actionable diagnostics without blocking ordinary installation. Document Claude's current `AGENTS.md` support floor and the `CLAUDE.md` import adapter; do not execute host tools or claim a live host version check. Test in Tasks 3 and 4.

---

### Task 1: Python package, CLI surface, and safe asset catalog

**Files:**
- Existing: `.gitignore` (created during repository setup)
- Create: `.gitattributes`
- Create: `pyproject.toml`
- Create: `agent_workflow/__init__.py`
- Create: `agent_workflow/__main__.py`
- Create: `agent_workflow/cli.py`
- Create: `agent_workflow/assets/` with versioned text assets
- Create: `agent_workflow/assets_manifest.py`
- Create: `tests/__init__.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_assets.py`

**Interfaces:**
- `agent_workflow.cli.main(argv: list[str] | None = None) -> int`
- `agent_workflow.assets_manifest.list_assets() -> dict[str, bytes]`; keys are safe project-relative POSIX paths.
- Initial package version is `0.1.0`. Root templates are delimited by `<!-- agent-workflow:begin -->` and `<!-- agent-workflow:end -->`.
- The initial catalog contains `AGENTS.md` and `CLAUDE.md`; Task 4 adds the shared skill assets using the exact paths listed there.
- CLI subcommands are `install`, `init`, `update`, `doctor`, `status`, `verify`, `remove`, and `version`.

- [x] **Step 1: Write failing CLI and asset-inventory tests**

Test `test_version_prints_package_version`, `test_unknown_command_returns_usage_error`, `test_asset_catalog_contains_required_roots` (assert both root instruction paths exist), `test_asset_paths_are_relative_and_unique`, and `test_all_assets_decode_as_utf8` using `unittest`.

- [x] **Step 2: Run tests and confirm expected failures**

Run: `python -m unittest tests.test_cli tests.test_assets -v`
Expected: FAIL because the package entry point and asset catalog do not exist.

- [x] **Step 3: Implement the stdlib package and asset catalog**

Declare Python `>=3.11`, console script `agent-workflow = agent_workflow.cli:main`, and no runtime dependencies. Make `python -m agent_workflow` use the same CLI entry point. The parser registers the eight named commands; behavior is filled in by later tasks.

- [x] **Step 4: Run package tests**

Run: `python -m unittest tests.test_cli tests.test_assets -v`
Expected: all tests pass.

### Task 2: Safe install, update, and remove lifecycle

**Files:**
- Create: `agent_workflow/manifest.py`
- Create: `agent_workflow/paths.py`
- Create: `agent_workflow/lifecycle.py`
- Runtime artifact: `.agent-workflow.lock` is created and removed by lifecycle mutations
- Modify: `agent_workflow/cli.py`
- Test: `tests/test_manifest.py`
- Test: `tests/test_lifecycle.py`
- Test: `tests/test_paths.py`

**Interfaces:**
- `Manifest.load(project_root: Path) -> Manifest | None`
- `install(project_root: Path) -> OperationReport`
- `update(project_root: Path) -> OperationReport`
- `remove(project_root: Path) -> OperationReport`
- The manifest lives at `.agent-workflow/manifest.json`; each owned file entry stores its project-relative path, source version, and SHA-256 of the managed payload (the whole file or the marked block for shared instruction files).
- Shared instruction blocks use exact markers `<!-- agent-workflow:begin -->` and `<!-- agent-workflow:end -->`.
- Install/update/remove serialize with an exclusive `.agent-workflow.lock`; an existing lock fails closed without mutating files. Normal operation removes the lock on exit. If forcibly terminated, a stale lock may remain; `doctor` reports it and advises inspection before manual cleanup.
- Existing root instruction files receive a clearly delimited `agent-workflow` block. A new file contains only the managed block.

- [x] **Step 1: Write failing lifecycle tests**

Add `test_install_is_idempotent`, `test_install_preserves_existing_instruction_text`, `test_install_does_not_claim_unowned_files`, `test_manifest_invalid_json_fails_before_writing`, `test_update_replaces_unchanged_managed_asset`, `test_update_refreshes_managed_block_without_losing_user_text`, `test_update_preserves_modified_asset_and_writes_conflict`, `test_update_preserves_modified_managed_block`, `test_remove_deletes_only_unchanged_owned_files`, `test_remove_preserves_user_text_around_unmodified_block`, `test_remove_keeps_modified_and_unowned_files`, `test_manifest_path_traversal_is_rejected`, a controlled overlapping `update`/`remove` regression that proves serialization, `test_stale_lock_blocks_noop_install_and_update`, `test_stale_lock_blocks_remove_without_manifest`, `test_directory_prune_failure_restores_manifest_and_files`, `test_external_edit_between_replacement_steps_is_preserved`, `test_rollback_restores_original_file_mode` (skip mode assertion on Windows), `test_rollback_conflict_preserves_edit_and_restores_other_files`, and `test_atomic_write_removes_readonly_staged_temp`.

- [x] **Step 2: Run lifecycle tests and confirm expected failures**

Run: `python -m unittest tests.test_manifest tests.test_lifecycle -v`
Expected: FAIL because the ownership manifest and lifecycle functions do not exist.

- [x] **Step 3: Implement manifest validation and path containment**

Validate schema version, file paths, hash format, and duplicate entries before any write. Resolve the project root and every destination parent; refuse absolute paths, `..`, and paths that escape the target. Write files through a temporary sibling followed by `replace`.

- [x] **Step 4: Implement lifecycle behavior and CLI output**

Use manifest hashes to distinguish unchanged managed files from project customizations. Update modified files by leaving the active path untouched and writing the incoming bytes beneath `.agent-workflow/updates/`; report every preserved conflict. Acquire `.agent-workflow.lock` before deciding whether an operation is a no-op, including remove when no manifest exists; fail immediately without writes if it already exists. Recheck each planned destination immediately before its replacement/deletion. Preserve original file modes in rollback. Include directory pruning in the transaction: if pruning fails after file deletion, restore the removed directories and original files/manifest. Removal deletes only unchanged owned files and removes an unchanged managed instruction block while preserving text around it. A forcibly terminated process may leave a lock and partial operation for operator inspection; Task 3 `doctor` reports this state without deleting the lock.

- [x] **Step 5: Run lifecycle tests**

Run: `python -m unittest tests.test_manifest tests.test_lifecycle -v`
Expected: all lifecycle cases pass, including a second install with no filesystem changes.

### Task 3: Project bootstrap, diagnostics, status, and deterministic checks

**Files:**
- Create: `agent_workflow/config.py`
- Create: `agent_workflow/commands.py`
- Create: `agent_workflow/project_templates.py`
- Create: `tests/test_init.py`
- Create: `tests/test_doctor_status.py`
- Create: `tests/test_verify.py`
- Modify: `agent_workflow/cli.py`

**Interfaces:**
- `initialize(project_root: Path) -> OperationReport` installs missing harness assets and creates only missing project context/config files.
- `agent_workflow.project_templates.INIT_FILES: dict[str, str]` defines the empty `agent-workflow.toml` and topic context documents created by `initialize`.
- `doctor(project_root: Path) -> list[Diagnostic]` reports detected host artifacts, project config, `openspec` availability, and incomplete onboarding without modifying files.
- `status(project_root: Path) -> StatusReport` reports onboarding and active OpenSpec/change-artifact task state.
- `verify(project_root: Path) -> list[CheckResult]` reads `agent-workflow.toml`; each `[[checks]]` record has `id`, non-empty `command: list[str]`, optional relative `cwd`, `timeout_seconds` in 1..3600, and `required` defaulting to true.
- CLI exit codes: `0` for success, `1` for a failing required check, and `2` for invalid configuration or no registered checks.

- [ ] **Step 1: Write failing bootstrap and diagnostic tests**

Test `test_init_installs_and_creates_pending_context`, `test_init_preserves_existing_project_context`, `test_doctor_reports_missing_openspec_without_failure`, `test_doctor_reports_existing_lock_without_mutation`, `test_doctor_is_read_only`, and `test_status_reports_onboarding_pending`.

- [ ] **Step 2: Run bootstrap tests and confirm expected failures**

Run: `python -m unittest tests.test_init tests.test_doctor_status -v`
Expected: FAIL because initialization and diagnostic functions do not exist.

- [ ] **Step 3: Implement idempotent bootstrap and read-only diagnostics**

Create `agent-workflow.toml` plus context-index, architecture, domain, operations, validation, and open-questions documents only when absent. Mark onboarding as `pending`; do not infer languages, facts, or architecture in the CLI. Detect `claude`, `codex`, and `openspec` with `shutil.which` only.

- [ ] **Step 4: Write failing verification tests**

Test `test_verify_runs_argv_without_shell`, `test_verify_rejects_empty_or_non_string_command`, `test_verify_rejects_cwd_outside_project`, `test_verify_times_out_and_returns_failure`, `test_verify_aggregates_required_failures`, `test_verify_returns_configuration_error_when_no_checks`, `test_verify_rejects_batch_commands_before_any_execution`, `test_verify_resolves_relative_executable_from_check_cwd`, `test_verify_records_working_directory_removed_by_prior_check`, `test_verify_rejects_invalid_onboarding_before_execution`, and `test_nonregular_config_is_rejected_without_blocking` (POSIX only).

- [ ] **Step 5: Run verification tests and confirm expected failures**

Run: `python -m unittest tests.test_verify -v`
Expected: FAIL because TOML parsing and validation execution do not exist.

- [ ] **Step 6: Implement TOML validation and bounded command execution**

Use `tomllib` and `subprocess.run(argv, shell=False, cwd=resolved_project_path, timeout=..., check=False)` with output inherited by the terminal. Validate onboarding and every check before starting any command. Reject batch-file executables on Windows, resolve explicit relative executables against each validated check cwd, and record launch-time cwd loss as that check's failure while continuing. Reject malformed records and out-of-root working directories before starting any command. Report each check's command, elapsed time, and result without buffering unbounded output.

- [ ] **Step 7: Run all CLI tests**

Run: `python -m unittest tests.test_init tests.test_doctor_status tests.test_verify -v`
Expected: all tests pass; no config or diagnostics command edits user-level agent settings.

### Task 4: Agent methodology, onboarding, continuity, OpenSpec, and compatibility docs

**Files:**
- Create/update: `agent_workflow/assets/AGENTS.md`
- Create/update: `agent_workflow/assets/CLAUDE.md`
- Create/update: `agent_workflow/assets/.agents/skills/agent-workflow/SKILL.md`
- Create/update: `agent_workflow/assets/.agents/skills/agent-workflow-onboarding/SKILL.md`
- Create/update: `agent_workflow/assets/.claude/skills/agent-workflow/SKILL.md`
- Create/update: `agent_workflow/assets/.claude/skills/agent-workflow-onboarding/SKILL.md`
- Create: `docs/architecture.md`
- Create: `docs/extending.md`
- Create: `docs/compatibility.md`
- Test: `tests/test_workflow_assets.py`

**Interfaces:**
- Root instructions contain a concise router, managed-block markers, autonomy/permission boundaries, and pointers to context; detailed methodology is in skills.
- The work skill classifies work as small, medium, or substantial/high-risk; checkpoints do not ask for approval. User input is requested only for missing business decisions, real blockers, scope changes, or authorization.
- The onboarding skill investigates new/existing repositories using tools, labels evidence `Verified`, `Hypothesis`, or `Open question`, and writes topic-based context plus an index.
- OpenSpec is used for behavior/domain/architecture changes and multi-component work when available; small tasks stay lightweight. The skill documents Claude `/openspec-*` and Codex `$openspec-*` invocation forms and the no-CLI fallback.
- Subagent guidance requires independence, bounded tasks, isolation for parallel writes, context/cost consideration, coordinator integration, and risk-based independent review.
- `doctor` and compatibility docs distinguish static artifact support from live semantic verification; project hooks remain opt-in and untouched.

- [ ] **Step 1: Write failing workflow-asset checks**

Test `test_root_adapters_share_canonical_workflow`, `test_skills_have_concise_frontmatter_descriptions`, `test_work_skill_covers_complexity_and_autonomy`, `test_onboarding_marks_evidence_confidence`, `test_openspec_invocation_covers_both_hosts`, `test_context_docs_are_separate_and_indexed`, and `test_compatibility_limits_are_explicit`.

- [ ] **Step 2: Run asset tests and confirm expected failures**

Run: `python -m unittest tests.test_workflow_assets -v`
Expected: FAIL because workflow instructions and project context assets are not authored.

- [ ] **Step 3: Author shared and host-specific instruction assets**

Keep root instructions under 100 lines. Use concise skill descriptions with focused files and scripts for deeper procedures. Onboard only when requested or materially needed; let ordinary quick changes stay quick.

- [ ] **Step 4: Document supported integrations and extension points**

Document native Claude Code/Codex discovery, hooks/permission limits, OpenSpec and Matt Pocock evaluation, Python/SQL/web domain skills, project TOML checks, and the CI compatibility boundary. Include source URLs reviewed in the design.

- [ ] **Step 5: Run workflow-asset tests**

Run: `python -m unittest tests.test_workflow_assets -v`
Expected: all content contract checks pass.

### Task 5: Runnable examples, public README, CI, and end-to-end acceptance

**Files:**
- Create: `examples/new-software/` with application, tests, project context, and TOML checks.
- Create: `examples/data-engineering/` with synthetic CSVs, a runnable SQLite pipeline, tests, and domain/lineage context.
- Create: `README.md`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `SECURITY.md`
- Create: `.github/workflows/ci.yml`
- Create: `tests/test_end_to_end.py`
- Modify: all affected package and documentation files after whole-project integration.

**Interfaces:**
- Example project validation commands run without third-party dependencies.
- A new developer can run `python -m agent_workflow init <target>` or install the package, then ask the agent naturally to onboard/build; `doctor`, `status`, `verify`, `update`, and `remove` behavior is documented with expected outcomes.
- CI runs package tests, both example suites, and build metadata checks on Windows, macOS, and Linux for Python 3.11 and 3.13.

- [ ] **Step 1: Write failing end-to-end command tests**

Test `test_init_to_verify_and_remove_flow`, `test_update_flow_preserves_custom_skill`, `test_new_software_example_checks_pass`, `test_synthetic_data_pipeline_and_quality_checks_pass`, and `test_built_wheel_includes_hidden_agent_skills` using temporary target directories for lifecycle tests, direct example tests, and wheel-content inspection for the sample projects/package.

- [ ] **Step 2: Run end-to-end tests and confirm expected failures**

Run: `python -m unittest tests.test_end_to_end -v`
Expected: FAIL because example projects and end-to-end flows do not exist.

- [ ] **Step 3: Implement runnable examples and project-owned checks**

The software example is a small, tested Python application. The data-engineering example loads synthetic customer/order CSVs into local SQLite, builds a documented aggregate, and tests schema, business rules, and data-quality constraints.

- [ ] **Step 4: Write installation, usage, architecture, extension, compatibility, and contribution docs**

Give copyable commands for Windows PowerShell and POSIX shells. State the Python version, package install paths, safe update/remove behavior, static-vs-live compatibility limits, and known constraints. Document that forced process termination may leave `.agent-workflow.lock` and partial files; `doctor` reports it without removal, and manual lock cleanup is safe only after confirming no workflow mutation is still running. Add a permissive OSI-approved license with the chosen SPDX identifier in repository metadata.

- [ ] **Step 5: Add cross-platform CI**

Use GitHub Actions matrix `ubuntu-latest`, `macos-latest`, `windows-latest` and Python `3.11`, `3.13`. Run `python -m unittest discover -s tests -v`, both example checks, and package build validation.

- [ ] **Step 6: Run complete local verification**

Run: `python -m unittest discover -s tests -v`
Run both examples' documented validation command from their project roots.
Run: `python -m build` when the build frontend is available; otherwise validate package metadata using the standard available tooling and report the limitation.
Expected: all local automated checks pass; install/init/update/doctor/status/verify/remove flows preserve unowned and customized files.

- [ ] **Step 7: Review public distribution readiness and compatibility claims**

Check the final file inventory, license/copyright, package data inclusion, CLI help examples, and CI matrix. Confirm the compatibility matrix does not claim authenticated live-agent testing that did not occur.
