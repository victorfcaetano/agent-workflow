"""Project configuration from agent-workflow.toml."""

import tomllib
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .paths import project_path

CONFIG_PATH = "agent-workflow.toml"


def load_config(root: Path) -> dict:
    path = project_path(root, CONFIG_PATH)
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (ValueError, OSError) as error:
        raise ValueError(f"Could not read {path}: {error}") from error


def onboarding_status(config: dict) -> str:
    onboarding = config.get("onboarding", {})
    if not isinstance(onboarding, dict):
        raise ValueError("The onboarding setting must be a TOML table")
    value = onboarding.get("status", "pending")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("onboarding.status must be a non-empty string")
    return value


@dataclass(frozen=True)
class Check:
    id: str
    command: list[str]
    cwd: str
    timeout_seconds: int
    required: bool

    def working_directory(self, root: Path) -> Path:
        if not isinstance(self.cwd, str) or not self.cwd or PureWindowsPath(self.cwd).anchor:
            raise ValueError(f"Check {self.id!r} needs a relative cwd")
        try:
            path = (root / self.cwd).resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as error:
            raise ValueError(f"Invalid cwd for check {self.id!r}: {self.cwd!r}") from error
        if not path.is_relative_to(root) or not path.is_dir():
            raise ValueError(f"Check {self.id!r} needs a cwd inside the project: {self.cwd!r}")
        return path


def configured_checks(root: Path, config: dict) -> list[Check]:
    records = config.get("checks", [])
    if not isinstance(records, list):
        raise ValueError("Use an array of [[checks]] tables")
    checks = []
    ids = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Check {index} must be a TOML table")
        name = record.get("id")
        if not isinstance(name, str) or not name.strip() or name in ids:
            raise ValueError(f"Check {index} needs a unique, non-empty id")
        unknown = set(record) - {"id", "command", "cwd", "timeout_seconds", "required"}
        if unknown:
            raise ValueError(f"Unknown fields for check {name!r}: {', '.join(sorted(unknown))}")
        argv = record.get("command")
        if (not isinstance(argv, list) or not argv
                or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
                or not argv[0].strip()):
            raise ValueError(f"Check {name!r} needs a command array of strings with an executable")
        timeout = record.get("timeout_seconds", 60)
        if type(timeout) is not int or not 1 <= timeout <= 3600:
            raise ValueError(f"Check {name!r} needs integer timeout_seconds in 1..3600")
        required = record.get("required", True)
        if type(required) is not bool:
            raise ValueError(f"Check {name!r} needs a boolean required setting")
        check = Check(name, argv, record.get("cwd", "."), timeout, required)
        check.working_directory(root)
        ids.add(name)
        checks.append(check)
    return checks
