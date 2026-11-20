"""Portable, project-relative destinations and atomic file replacement."""

import stat
import tempfile
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


def atomic_write(path: Path, content: bytes) -> None:
    """Replace a regular file without leaving a partially written payload."""
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    temporary = tempfile.NamedTemporaryFile(dir=path.parent, delete=False)
    sibling = Path(temporary.name)
    try:
        with temporary:
            temporary.write(content)
        if mode is not None:
            sibling.chmod(mode)
        sibling.replace(path)
    finally:
        sibling.unlink(missing_ok=True)
