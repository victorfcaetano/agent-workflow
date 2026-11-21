"""Portable, project-relative destinations and atomic file replacement."""

import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path, PureWindowsPath

try:
    from ntpath import isreserved
except ImportError:  # Python 3.11 and 3.12
    def isreserved(name: str) -> bool:
        return PureWindowsPath(name).is_reserved()


def project_path(root: Path, name: str) -> Path:
    """Reject nonportable names and links anywhere below the project root."""
    if not isinstance(name, str) or not name:
        raise ValueError(f"Invalid project path: {name!r}")
    root = root.resolve()
    target = root
    for part in name.split("/"):
        if (part in ("", ".", "..") or part.endswith((" ", "."))
                or any(char in '<>:"\\|?*' or ord(char) < 32 for char in part)
                or isreserved(part)):
            raise ValueError(f"Invalid project path: {name!r}")
        if target != root and target.exists() and not target.is_dir():
            raise ValueError(f"Expected a directory at {target}")
        target = target / part
        try:
            info = target.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode) or
                getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f"Linked project destination: {target}")
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"Destination escapes project: {name!r}")
    return target


def atomic_write(path: Path, content: bytes, *, mode: int | None = None,
                 before_replace: Callable[[], None] | None = None) -> None:
    """Replace a regular file without leaving a partially written payload."""
    if mode is None and path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    for _ in range(100):
        sibling = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            descriptor = os.open(sibling, flags, 0o666)
            break
        except FileExistsError:
            continue
    else:
        raise FileExistsError(f"Could not allocate a temporary sibling for {path}")
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(content)
        if mode is not None:
            sibling.chmod(mode)
        if before_replace is not None:
            before_replace()
        sibling.replace(path)
    except BaseException as error:
        try:
            sibling.unlink(missing_ok=True)
        except PermissionError as cleanup_error:
            try:
                sibling.chmod(stat.S_IMODE(sibling.stat().st_mode) | stat.S_IWRITE)
                sibling.unlink(missing_ok=True)
            except OSError as retry_error:
                error.add_note(
                    f"Could not clean up staged file {sibling}: {cleanup_error}; retry failed: {retry_error}"
                )
        except OSError as cleanup_error:
            error.add_note(f"Could not clean up staged file {sibling}: {cleanup_error}")
        raise
