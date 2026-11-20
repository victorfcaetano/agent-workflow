"""Install, update, and remove manifest-owned project files."""

import errno
import hashlib
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from . import __version__
from .assets_manifest import list_assets
from .manifest import LOCK_PATH, MANIFEST_PATH, SHARED_PATHS, Entry, Manifest, check_payload_name
from .paths import atomic_write, project_path

BEGIN = b"<!-- agent-workflow:begin -->"
END = b"<!-- agent-workflow:end -->"
BLOCK = re.compile(rb"^" + BEGIN + rb"\r?\n.*?^" + END + rb"(?:\r?\n|\Z)", re.M | re.S)


@dataclass
class OperationReport:
    changed: list[str] = field(default_factory=list)
    preserved: list[str] = field(default_factory=list)
    conflicts: dict[str, str] = field(default_factory=dict)


def _read(path: Path) -> bytes | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"Expected a regular file at {path}")
    return path.read_bytes()


class _Changes:
    """Preflight every destination, then apply the changes under a project lock."""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError(f"Expected a project directory at {root}")
        self.original: dict[str, bytes | None] = {}
        self.pending: dict[str, bytes | None] = {}
        self.new_dirs: set[str] = set()

    def read(self, name: str) -> bytes | None:
        if name not in self.original:
            self.original[name] = _read(project_path(self.root, name))
        return self.original[name]

    def set(self, name: str, content: bytes | None) -> None:
        if self.read(name) == content:
            return
        self.pending[name] = content
        for parent in (self.root / name).parents:
            if parent == self.root or parent.exists():
                break
            self.new_dirs.add(parent.relative_to(self.root).as_posix())

    def _check(self, name: str, expected: bytes | None) -> None:
        if _read(project_path(self.root, name)) != expected:
            raise ValueError(f"Project changed during operation: {name}. Retry.")

    def _change_file(self, name: str, expected: bytes | None, replacement: bytes | None,
                     *, mode: int | None = None) -> None:
        path = project_path(self.root, name)
        if replacement is None:
            self._check(name, expected)
            path.unlink()
        else:
            atomic_write(path, replacement, mode=mode, before_replace=partial(self._check, name, expected))

    def apply(self, prune: set[str]) -> None:
        for name, previous in self.original.items():
            self._check(name, previous)
        created = []
        applied = []
        deleted_modes = {}
        pruned = []
        try:
            for name in sorted(self.new_dirs, key=lambda d: (d.count("/"), d)):
                path = project_path(self.root, name)
                path.mkdir()
                created.append(path)
            for name, content in self.pending.items():
                if content is None:
                    path = project_path(self.root, name)
                    deleted_modes[name] = stat.S_IMODE(path.stat().st_mode)
                self._change_file(name, self.original[name], content)
                applied.append(name)
            for name in sorted(prune, key=lambda d: (-d.count("/"), d)):
                mode = _prune_empty(project_path(self.root, name))
                if mode is not None:
                    pruned.append((name, mode))
        except (OSError, ValueError) as operation_error:
            for name, mode in reversed(pruned):
                directory = project_path(self.root, name)
                if not directory.exists():
                    directory.mkdir(mode=mode)
                    directory.chmod(mode)
            for name in reversed(applied):
                try:
                    self._change_file(name, self.pending[name], self.original[name], mode=deleted_modes.get(name))
                except (OSError, ValueError) as restore_error:
                    operation_error.add_note(f"Could not restore {name}: {restore_error}")
            for path in reversed(created):
                _prune_empty(path)
            raise


def _prune_empty(path: Path) -> int | None:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        path.rmdir()
        return mode
    except OSError as error:
        if error.errno not in {errno.ENOENT, errno.ENOTEMPTY, errno.EEXIST, errno.ENOTDIR}:
            raise
        return None


def _block_span(content: bytes):
    if content.count(BEGIN) == content.count(END) == 1:
        return BLOCK.search(content)
    return None


def _owned_span(entry: Entry, current: bytes) -> tuple[int, int] | None:
    if entry.kind == "block":
        match = _block_span(current)
        if match is None:
            return None
        start, end = match.span()
    else:
        start, end = 0, len(current)
    if hashlib.sha256(current[start:end]).hexdigest() == entry.sha256:
        return start, end
    return None


def _record_conflict(changes: _Changes, report: OperationReport, name: str, incoming: bytes):
    base = f".agent-workflow/updates/{name}"
    candidate = base
    index = 1
    while (current := changes.read(candidate)) is not None and current != incoming:
        index += 1
        candidate = f"{base}.{index}"
    changes.set(candidate, incoming)
    report.conflicts[name] = candidate


def _install_asset(changes: _Changes, manifest: Manifest, report: OperationReport,
                   name: str, incoming: bytes, updating: bool) -> None:
    project_path(changes.root, name)
    check_payload_name(name)
    shared = name in SHARED_PATHS
    if shared and (not _block_span(incoming) or not BLOCK.fullmatch(incoming)):
        raise ValueError(f"Packaged instruction file must contain one marked block: {name}")

    current = changes.read(name)
    entry = manifest.files.get(name)
    created = entry.created if entry else current is None
    if current is None:
        content = incoming
    elif entry is None:
        if not shared or BEGIN in current or END in current:
            report.preserved.append(name)
            return
        # Appending after a complete line or prepending before an incomplete line
        # makes the operation reversible without owning a user-provided newline.
        if not current or current.endswith(b"\n"):
            content = current + incoming
        else:
            content = incoming + current
    else:
        span = _owned_span(entry, current)
        if span is None:
            report.preserved.append(name)
            if updating:
                _record_conflict(changes, report, name, incoming)
            return
        if not updating:
            return
        start, end = span
        content = current[:start] + incoming + current[end:]

    changes.set(name, content)
    if current != content:
        report.changed.append(name)
    manifest.files[name] = Entry(name, __version__, hashlib.sha256(incoming).hexdigest(),
                                 "block" if shared else "file", created)


@contextmanager
def _locked_project(project_root: Path):
    changes = _Changes(project_root)
    lock = project_path(changes.root, LOCK_PATH)
    try:
        handle = lock.open("xb")
    except FileExistsError as error:
        raise ValueError(f"Project lock exists at {lock}. Inspect it before retrying.") from error
    try:
        with handle:
            yield changes
    finally:
        lock.unlink()


def _deploy(changes: _Changes, updating: bool) -> OperationReport:
    previous = changes.read(MANIFEST_PATH)
    if previous is None and updating:
        raise ValueError("No installed workflow. Run agent-workflow install first.")
    manifest = Manifest.parse(changes.root, previous) if previous is not None else Manifest()
    report = OperationReport()
    for name, incoming in list_assets().items():
        _install_asset(changes, manifest, report, name, incoming, updating)

    # Include the metadata directory itself only when we create it.
    if not (changes.root / MANIFEST_PATH).parent.exists():
        manifest.directories.add(".agent-workflow")
    manifest.directories.update(changes.new_dirs)
    content = manifest.dump()
    Manifest.parse(changes.root, content)
    changes.set(MANIFEST_PATH, content)
    changes.apply(set())
    return report


def install(project_root: Path) -> OperationReport:
    with _locked_project(project_root) as changes:
        return _deploy(changes, updating=False)


def update(project_root: Path) -> OperationReport:
    with _locked_project(project_root) as changes:
        return _deploy(changes, updating=True)


def remove(project_root: Path) -> OperationReport:
    with _locked_project(project_root) as changes:
        return _remove(changes)


def _remove(changes: _Changes) -> OperationReport:
    previous = changes.read(MANIFEST_PATH)
    report = OperationReport()
    if previous is None:
        return report
    manifest = Manifest.parse(changes.root, previous)
    for name, entry in manifest.files.items():
        current = changes.read(name)
        if current is None:
            continue
        span = _owned_span(entry, current)
        if span is None:
            report.preserved.append(name)
            continue
        start, end = span
        remainder = current[:start] + current[end:]
        changes.set(name, remainder if remainder or not entry.created else None)
        report.changed.append(name)
    changes.set(MANIFEST_PATH, None)
    changes.apply(manifest.directories)
    return report
