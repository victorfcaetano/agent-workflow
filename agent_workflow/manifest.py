"""Ownership metadata for repository-scoped installations."""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from .assets_manifest import managed_paths
from .paths import project_path

MANIFEST_PATH = ".agent-workflow/manifest.json"
LOCK_PATH = ".agent-workflow.lock"
SHARED_PATHS = {"AGENTS.md", "CLAUDE.md"}


def check_payload_name(name: str) -> None:
    parts = name.casefold().split("/")
    if (parts[0] in {".agent-workflow", LOCK_PATH, ".git", ".svn", ".hg", ".codex"}
            or parts[0] == ".claude" and parts[1:2] != ["skills"]):
        raise ValueError(f"Reserved project path: {name!r}")


@dataclass(frozen=True)
class Entry:
    path: str
    source_version: str
    sha256: str
    kind: str
    created: bool


@dataclass
class Manifest:
    files: dict[str, Entry] = field(default_factory=dict)
    directories: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, project_root: Path) -> "Manifest | None":
        path = project_path(project_root, MANIFEST_PATH)
        if not path.exists():
            return None
        if not path.is_file():
            raise ValueError(f"Expected a manifest file at {path}")
        return cls.parse(project_root, path.read_bytes())

    @classmethod
    def parse(cls, root: Path, content: bytes) -> "Manifest":
        def unique_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate manifest key: {key}")
                result[key] = value
            return result

        data = json.loads(content, object_pairs_hook=unique_keys)
        if (not isinstance(data, dict)
                or type(data.get("schema_version")) is not int or data["schema_version"] != 1
                or not isinstance(data.get("files"), list)
                or not isinstance(data.get("directories"), list)):
            raise ValueError("Unsupported or malformed ownership manifest")

        manifest = cls()
        seen = set()
        for item in data["files"]:
            if not isinstance(item, dict) or set(item) != set(Entry.__dataclass_fields__):
                raise ValueError("Malformed manifest file entry")
            entry = Entry(**item)
            if not isinstance(entry.path, str) or entry.path not in managed_paths():
                raise ValueError(f"Manifest cannot own an unrecognized asset path: {entry.path!r}")
            project_path(root, entry.path)
            check_payload_name(entry.path)
            key = entry.path.casefold()
            kind = "block" if entry.path in SHARED_PATHS else "file"
            if (key in seen or not isinstance(entry.source_version, str)
                    or not entry.source_version.strip() or not isinstance(entry.sha256, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", entry.sha256)
                    or type(entry.created) is not bool or entry.kind != kind
                    or kind == "file" and not entry.created):
                raise ValueError(f"Invalid or duplicate manifest entry: {entry.path!r}")
            manifest.files[entry.path] = entry
            seen.add(key)

        file_names = seen.copy()
        valid_dirs = {".agent-workflow"}
        for name in manifest.files:
            for destination in (name, f".agent-workflow/updates/{name}"):
                for parent in PurePosixPath(destination).parents:
                    if parent.as_posix().casefold() in file_names:
                        raise ValueError(f"Manifest file used as a directory: {parent}")
                    valid_dirs.add(parent.as_posix())
        for directory in data["directories"]:
            project_path(root, directory)
            key = directory.casefold()
            if key in seen or directory not in valid_dirs:
                raise ValueError(f"Invalid or duplicate manifest directory: {directory!r}")
            seen.add(key)
            manifest.directories.add(directory)
        return manifest

    def dump(self) -> bytes:
        data = {
            "schema_version": 1,
            "files": [asdict(entry) for _, entry in sorted(self.files.items())],
            "directories": sorted(self.directories),
        }
        return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()
