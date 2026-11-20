"""Project-owned starters. Onboarding fills in the evidence."""

CONTEXT_DIR = "docs/agent-workflow"

_TOPICS = {
    "architecture": "Architecture",
    "domain": "Domain",
    "operations": "Operations",
    "validation": "Validation",
    "open-questions": "Open questions",
}

INIT_FILES: dict[str, str] = {
    "agent-workflow.toml": '[onboarding]\nstatus = "pending"\n',
    f"{CONTEXT_DIR}/context-index.md": "# Project context\n\n" + "".join(
        f"- [{title}]({name}.md)\n" for name, title in _TOPICS.items()
    ),
}
for _name, _title in _TOPICS.items():
    INIT_FILES[f"{CONTEXT_DIR}/{_name}.md"] = (
        f"# {_title}\n\n## Verified facts\n\n## Hypotheses\n\n## Open questions\n"
        if _name != "open-questions" else "# Open questions\n"
    )
