import argparse
import sys
from pathlib import Path

from . import __version__
from .lifecycle import install, remove, update


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-workflow",
        description="Manage the workflow assets in a project.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    install_parser = commands.add_parser("install", help="Install the workflow in a project.")
    commands.add_parser("init", help="Initialize a project's workflow context.")
    update_parser = commands.add_parser("update", help="Update the installed workflow assets.")
    commands.add_parser("doctor", help="Diagnose a project's workflow setup.")
    commands.add_parser("status", help="Show the project's workflow status.")
    commands.add_parser("verify", help="Run the project's configured checks.")
    remove_parser = commands.add_parser("remove", help="Remove the installed workflow assets.")
    for command in (install_parser, update_parser, remove_parser):
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

    operations = {"install": install, "update": update, "remove": remove}
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

    print(f"agent-workflow: {args.command} is not implemented yet", file=sys.stderr)
    return 1
