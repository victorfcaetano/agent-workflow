import argparse
import sys

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-workflow",
        description="Manage the workflow assets in a project.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install", help="Install the workflow in a project.")
    commands.add_parser("init", help="Initialize a project's workflow context.")
    commands.add_parser("update", help="Update the installed workflow assets.")
    commands.add_parser("doctor", help="Diagnose a project's workflow setup.")
    commands.add_parser("status", help="Show the project's workflow status.")
    commands.add_parser("verify", help="Run the project's configured checks.")
    commands.add_parser("remove", help="Remove the installed workflow assets.")
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

    print(f"agent-workflow: {args.command} is not implemented yet", file=sys.stderr)
    return 1
