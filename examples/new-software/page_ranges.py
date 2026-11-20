"""Normalize a page selection without expanding individual page numbers."""

import argparse
import re


def normalize(selection: str) -> str:
    intervals = []
    for token in selection.split(","):
        match = re.fullmatch(r"([1-9][0-9]*)(?:\s*-\s*([1-9][0-9]*))?", token.strip())
        if match is None:
            raise ValueError(f"Invalid page or range: {token!r}")
        start = int(match[1])
        end = int(match[2]) if match[2] else start
        if end < start:
            raise ValueError(f"Range ends before it starts: {token!r}")
        intervals.append((start, end))

    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 1:
            first, previous_end = merged[-1]
            merged[-1] = (first, max(previous_end, end))
        else:
            merged.append((start, end))
    return ",".join(str(start) if start == end else f"{start}-{end}" for start, end in merged)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", help='Comma-separated pages or ranges, such as "2,5-8".')
    args = parser.parse_args()
    try:
        print(normalize(args.selection))
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
