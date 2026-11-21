from importlib.resources import files

# Only these project-relative paths are exposed to the installer.
_ASSET_PATHS = (
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/skills/agent-workflow/SKILL.md",
    ".agents/skills/agent-workflow-onboarding/SKILL.md",
    ".claude/skills/agent-workflow/SKILL.md",
    ".claude/skills/agent-workflow-onboarding/SKILL.md",
)

# Keep removed package paths here for as long as an older installed manifest
# may still refer to them. A manifest must never be allowed to own arbitrary
# project files.
RETIRED_ASSET_PATHS: tuple[str, ...] = ()


def asset_paths() -> tuple[str, ...]:
    """Return the raw catalog so callers can detect duplicate declarations."""
    return _ASSET_PATHS


def managed_paths() -> frozenset[str]:
    """Return the exact canonical paths that Agent Workflow may own."""
    return frozenset((*_ASSET_PATHS, *RETIRED_ASSET_PATHS))


def list_assets() -> dict[str, bytes]:
    """Read the bundled assets keyed by their project-relative POSIX paths."""
    if len(_ASSET_PATHS) != len(set(_ASSET_PATHS)):
        raise RuntimeError("Duplicate path in packaged asset catalog")
    assets = files("agent_workflow").joinpath("assets")
    return {name: assets.joinpath(*name.split("/")).read_bytes() for name in _ASSET_PATHS}
