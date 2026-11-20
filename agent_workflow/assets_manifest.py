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


def list_assets() -> dict[str, bytes]:
    """Read the bundled assets keyed by their project-relative POSIX paths."""
    assets = files("agent_workflow").joinpath("assets")
    return {name: assets.joinpath(*name.split("/")).read_bytes() for name in _ASSET_PATHS}
