"""Bootstrap and inspect a project's workflow."""

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import CONFIG_PATH, configured_checks, load_config, onboarding_status
from .assets_manifest import list_assets
from .lifecycle import OperationReport, _owned_span, install
from .manifest import LOCK_PATH, MANIFEST_PATH, Manifest
from .paths import project_path
from .project_templates import CONTEXT_DIR, INIT_FILES


def initialize(project_root: Path) -> OperationReport:
    root = project_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in INIT_FILES:
        path = project_path(root, name)
        if path.exists() and not path.is_file():
            raise ValueError(f"Expected a project file at {path}")
    return install(root, extra_files=INIT_FILES)


@dataclass(frozen=True)
class Diagnostic:
    level: str
    message: str


@dataclass(frozen=True)
class StatusReport:
    onboarding: str
    active_changes: list[str]


def _existing_project(project_root: Path) -> Path:
    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Expected a project directory at {project_root}")
    return root


def status(project_root: Path) -> StatusReport:
    root = _existing_project(project_root)
    state = (onboarding_status(load_config(root))
             if project_path(root, CONFIG_PATH).exists() else "uninitialized")
    active = []
    for base in ("openspec/changes", f"{CONTEXT_DIR}/changes"):
        directory = project_path(root, base)
        if directory.is_dir():
            for child in sorted(directory.iterdir()):
                if child.name == "archive" and base == "openspec/changes":
                    continue
                name = child.relative_to(root).as_posix()
                if project_path(root, name).is_dir():
                    active.append(name)
    return StatusReport(state, active)


def doctor(project_root: Path) -> list[Diagnostic]:
    root = _existing_project(project_root)
    diagnostics = []
    if os.path.lexists(root / LOCK_PATH):
        diagnostics.append(Diagnostic("warning", f"Inspect {LOCK_PATH} and any running operation before manual cleanup."))
    for name in ("claude", "codex", "openspec"):
        executable = shutil.which(name)
        diagnostics.append(Diagnostic("info", f"{name}: {executable or 'not found on PATH'}"))
    manifest = None
    try:
        manifest = Manifest.load(root)
        diagnostics.append(Diagnostic("info", f"{MANIFEST_PATH}: {'installed' if manifest else 'missing'}"))
    except (ValueError, OSError) as error:
        diagnostics.append(Diagnostic("error", f"{MANIFEST_PATH}: {error}"))
    partial = False
    found_workflow_location = False
    for name in list_assets():
        try:
            path = project_path(root, name)
            present = path.is_file()
            entry = manifest.files.get(name) if manifest is not None else None
            if present and name not in {"AGENTS.md", "CLAUDE.md"}:
                found_workflow_location = True
            if entry is None:
                if present:
                    diagnostics.append(Diagnostic("info", f"{name}: unmanaged project file"))
                else:
                    diagnostics.append(Diagnostic("info", f"{name}: missing"))
                    if manifest is not None:
                        partial = True
                if name.startswith((".agents/skills/agent-workflow/", ".agents/skills/agent-workflow-onboarding/",
                                   ".claude/skills/agent-workflow/", ".claude/skills/agent-workflow-onboarding/")):
                    if path.parent.is_dir():
                        found_workflow_location = True
                continue
            if not present:
                diagnostics.append(Diagnostic("warning", f"{name}: managed asset is missing"))
                partial = True
            elif _owned_span(entry, path.read_bytes()) is None:
                diagnostics.append(Diagnostic("warning", f"{name}: managed content was modified; preserved"))
            else:
                diagnostics.append(Diagnostic("info", f"{name}: installed and unchanged"))
        except (OSError, ValueError) as error:
            diagnostics.append(Diagnostic("error", f"{name}: {error}"))
            partial = manifest is not None or partial
    if manifest is None and found_workflow_location:
        diagnostics.append(Diagnostic(
            "warning", "Workflow files or skill locations exist without an ownership manifest; setup may be partial or unmanaged."
        ))
    elif partial:
        diagnostics.append(Diagnostic("warning", "Workflow installation is partial; inspect missing managed assets."))
    try:
        recovery_dir = project_path(root, ".agent-workflow/recovery")
        if recovery_dir.is_dir():
            artifacts = sorted(recovery_dir.glob("rollback-*.json"))
            for artifact in artifacts:
                diagnostics.append(Diagnostic(
                    "warning", f"Rollback recovery artifact needs manual inspection: {artifact.relative_to(root).as_posix()}"
                ))
    except (OSError, ValueError) as error:
        diagnostics.append(Diagnostic("error", f".agent-workflow/recovery: {error}"))
    try:
        if project_path(root, CONFIG_PATH).exists():
            config = load_config(root)
            state = onboarding_status(config)
            checks = configured_checks(root, config)
            level = "info" if state == "complete" else "warning"
            diagnostics.append(Diagnostic(level, f"{CONFIG_PATH}: onboarding {state}, {len(checks)} registered checks"))
        else:
            diagnostics.append(Diagnostic("warning", f"{CONFIG_PATH}: missing. Onboarding is uninitialized."))
    except (ValueError, OSError) as error:
        diagnostics.append(Diagnostic("error", str(error)))
    diagnostics.append(Diagnostic("info", "Static diagnostics only. Live host behavior requires a host session."))
    return diagnostics


@dataclass(frozen=True)
class CheckResult:
    id: str
    command: list[str]
    required: bool
    elapsed_seconds: float
    returncode: int | None
    detail: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def verify(project_root: Path) -> list[CheckResult]:
    root = _existing_project(project_root)
    config = load_config(root)
    onboarding_status(config)
    checks = configured_checks(root, config)
    if not checks:
        raise ValueError(f"No registered checks in {CONFIG_PATH}")
    results = []
    for check in checks:
        started = time.monotonic()
        code = None
        try:
            # An earlier check may have changed a directory or executable after preflight.
            cwd = check.working_directory(root)
            executable = check.executable(cwd)
            if executable is None:
                raise FileNotFoundError(f"Executable not found on PATH: {check.command[0]}")
            process = subprocess.run([executable, *check.command[1:]], shell=False, cwd=cwd,
                                     timeout=check.timeout_seconds, check=False)
            code = process.returncode
            detail = f"exit {code}"
        except subprocess.TimeoutExpired:
            detail = f"timed out after {check.timeout_seconds}s"
        except (OSError, ValueError) as error:
            detail = f"could not start: {error}"
        elapsed = time.monotonic() - started
        results.append(CheckResult(check.id, check.command, check.required, elapsed, code, detail))
    return results
