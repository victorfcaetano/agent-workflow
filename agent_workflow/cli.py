import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .commands import doctor, initialize, status, verify
from .lifecycle import install, remove, update


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-workflow",
        description="Manage the workflow assets in a project.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    descriptions = {
        "install": "Install the workflow in a project.",
        "init": "Initialize a project's workflow context.",
        "update": "Update the installed workflow assets.",
        "doctor": "Diagnose a project's workflow setup.",
        "status": "Show the project's workflow status.",
        "verify": "Run the project's configured checks.",
        "remove": "Remove the installed workflow assets.",
    }
    for name, description in descriptions.items():
        command = commands.add_parser(name, help=description)
        command.add_argument("project", type=Path, nargs="?", default=Path("."))
    commands.add_parser("version", help="Print the package version.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return error.code

    if args.command == "version":
        print(__version__)
        return 0

    operations = {"install": install, "init": initialize, "update": update, "remove": remove}
    if args.command in operations:
        try:
            report = operations[args.command](args.project)
        except (ValueError, OSError) as error:
            print(f"agent-workflow: {error}", file=sys.stderr)
            return 1
        for path in report.changed:
            print(f"Changed {path}")
        for path in report.preserved:
            print(f"Preserved {path}")
        for path, artifact in report.conflicts.items():
            print(f"Conflict at {path}. Review {artifact}")
        return int(bool(report.conflicts))

    try:
        if args.command == "doctor":
            diagnostics = doctor(args.project)
            for diagnostic in diagnostics:
                print(f"{diagnostic.level}: {diagnostic.message}")
            return 2 if any(d.level == "error" for d in diagnostics) else 0
        if args.command == "status":
            state = status(args.project)
            print(f"Onboarding: {state.onboarding}")
            print("Active changes: " + (", ".join(state.active_changes) or "none"))
            return 0
        results = verify(args.project)
        for result in results:
            outcome = "passed" if result.passed else "failed"
            requirement = "required" if result.required else "optional"
            print(f"{result.id} ({requirement}) {outcome} in {result.elapsed_seconds:.3f}s "
                  f"({result.detail}): {json.dumps(result.command)}")
        return int(any(result.required and not result.passed for result in results))
    except (ValueError, OSError) as error:
        print(f"agent-workflow: {error}", file=sys.stderr)
        return 2
