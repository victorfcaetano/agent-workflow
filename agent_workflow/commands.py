"""Bootstrap and inspect a project's workflow."""

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import CONFIG_PATH, configured_checks, load_config, onboarding_status
from .lifecycle import OperationReport, _locked_project, install
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
    report = install(root)
    with _locked_project(root) as changes:
        for name, content in INIT_FILES.items():
            if changes.read(name) is None:
                changes.set(name, content.encode("utf-8"))
                report.changed.append(name)
        changes.apply(set())
    return report


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
    for name in ("AGENTS.md", "CLAUDE.md", ".agents/skills", ".claude/skills"):
        try:
            path = project_path(root, name)
            present = path.is_file() if name.endswith(".md") else path.is_dir()
            diagnostics.append(Diagnostic("info", f"{name}: {'present' if present else 'missing'}"))
        except (OSError, ValueError) as error:
            diagnostics.append(Diagnostic("error", str(error)))
    try:
        manifest = Manifest.load(root)
        diagnostics.append(Diagnostic("info", f"{MANIFEST_PATH}: {'installed' if manifest else 'missing'}"))
    except (ValueError, OSError) as error:
        diagnostics.append(Diagnostic("error", f"{MANIFEST_PATH}: {error}"))
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
    checks = configured_checks(root, load_config(root))
    if not checks:
        raise ValueError(f"No registered checks in {CONFIG_PATH}")
    results = []
    for check in checks:
        # An earlier check may have moved a directory after the config preflight.
        cwd = check.working_directory(root)
        started = time.monotonic()
        code = None
        try:
            process = subprocess.run(check.command, shell=False, cwd=cwd,
                                     timeout=check.timeout_seconds, check=False)
            code = process.returncode
            detail = f"exit {code}"
        except subprocess.TimeoutExpired:
            detail = f"timed out after {check.timeout_seconds}s"
        except OSError as error:
            detail = f"could not start: {error}"
        elapsed = time.monotonic() - started
        results.append(CheckResult(check.id, check.command, check.required, elapsed, code, detail))
    return results
