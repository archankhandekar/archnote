"""Command line interface for formatting and updating clinical notes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from archnote.formatter import append_visit_to_note, format_note


def read_input(source: Optional[str]) -> str:
    if source is None or source == "-":
        return sys.stdin.read()
    path = Path(source)
    return path.read_text()


def write_output(text: str) -> None:
    sys.stdout.write(text + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Format raw clinical notes or append new visits to existing notes.",
    )
    subparsers = parser.add_subparsers(dest="command")

    format_parser = subparsers.add_parser(
        "format",
        help="Format a raw note into the standardized template.",
    )
    format_parser.add_argument(
        "source",
        nargs="?",
        help="Path to the raw note file. Reads from stdin if omitted or '-'",
    )

    update_parser = subparsers.add_parser(
        "append-visit",
        help="Append a new investigations report into an existing formatted note.",
    )
    update_parser.add_argument(
        "existing",
        help="Path to the existing formatted note. Use '-' to read from stdin.",
    )
    update_parser.add_argument(
        "report",
        help="Path to the new visit report to append. Use '-' to read from stdin.",
    )
    update_parser.add_argument(
        "--date",
        dest="visit_date",
        help="Optional date associated with the new visit.",
    )
    update_parser.add_argument(
        "--label",
        dest="visit_label",
        help="Optional label describing the visit (e.g., 'Oncology follow-up').",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command = args.command or "format"

    if command == "format":
        raw_text = read_input(getattr(args, "source", None))
        formatted = format_note(raw_text)
        write_output(formatted)
        return 0

    if command == "append-visit":
        existing_note = read_input(args.existing)
        visit_report = read_input(args.report)
        updated = append_visit_to_note(
            existing_note,
            visit_report,
            visit_date=args.visit_date,
            visit_label=args.visit_label,
        )
        write_output(updated)
        return 0

    parser.error(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
