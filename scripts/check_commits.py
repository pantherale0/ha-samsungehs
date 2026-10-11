"""Check Conventional Commits 1.0.0 messages without external dependencies."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HEADER = re.compile(
    r"[\w-]+(?:\([^()\s](?:[^()\r\n]*[^()\s])?\))?!?: \S[^\r\n]*",
    re.UNICODE,
)
BREAKING = re.compile(r"BREAKING(?: CHANGE|-CHANGE): \S")


def validate(message: str) -> list[str]:
    """Return syntax errors in a proposed commit message."""
    lines = message.splitlines()
    errors = []
    if not lines or not HEADER.fullmatch(lines[0]):
        errors.append("Use <type>[optional scope][!]: <description>.")
    if len(lines) > 1 and lines[1].strip():
        errors.append("Separate the header from the body or footers with a blank line.")
    if any(
        line.upper().startswith(("BREAKING CHANGE:", "BREAKING-CHANGE:"))
        and not BREAKING.match(line)
        for line in lines[2:]
    ):
        errors.append(
            "Use uppercase BREAKING CHANGE: or BREAKING-CHANGE: with a description."
        )
    return errors


def git(*args: str) -> str:
    """Read local Git history without invoking a shell."""
    return subprocess.check_output(["git", *args], text=True)


def main() -> int:
    """Validate a message file or a range of non-merge commits."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--message-file", type=Path, help="Message file, or - for stdin"
    )
    source.add_argument(
        "--range", help="Git revision range, for example origin/main..HEAD"
    )
    args = parser.parse_args()
    if args.message_file is not None:
        message = (
            sys.stdin.read()
            if str(args.message_file) == "-"
            else args.message_file.read_text(encoding="utf-8")
        )
        messages = [("message", message)]
    else:
        try:
            commits = git("rev-list", "--no-merges", args.range).splitlines()
            messages = [(sha, git("show", "-s", "--format=%B", sha)) for sha in commits]
        except subprocess.CalledProcessError:
            return 1
    failed = False
    for label, message in messages:
        for error in validate(message):
            print(f"{label}: {error}", file=sys.stderr)
            failed = True
    if failed:
        return 1
    print(f"Validated {len(messages)} Conventional Commit message(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
