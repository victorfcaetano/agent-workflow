from importlib.resources import files

# Only these project-relative paths are exposed to the installer.
_ASSET_PATHS = ("AGENTS.md", "CLAUDE.md")


def list_assets() -> dict[str, bytes]:
    """Read the bundled assets keyed by their project-relative POSIX paths."""
    assets = files("agent_workflow").joinpath("assets")
    return {name: assets.joinpath(*name.split("/")).read_bytes() for name in _ASSET_PATHS}
