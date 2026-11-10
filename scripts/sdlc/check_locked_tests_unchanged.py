"""Locked-tests check for story pull requests (review item 4).

The locked tests (tests/locked/INT-n/) are written at G3 by a separate test-author step and approved by the QE lead.
The coding agent may read and run them but never change them, so a story PR that adds, edits, deletes or renames
anything under tests/locked/ fails. (The final PR from the feature branch into develop legitimately carries the
locked tests the author committed; it is not checked here. The orchestrator's evidence gate checks the digest of
those files there.) Run this from the base branch's copy of the workflow, so a PR cannot weaken it.

Standard library only; no orchestrator imports, so code repos can run it on their own.

Usage:
    python check_locked_tests_unchanged.py --changed changed.txt        # one path per line, e.g. git diff --name-only
    git diff --name-only origin/develop...HEAD | python check_locked_tests_unchanged.py --changed -

Exit codes: 0 pass, 1 a locked test changed, 2 missing or invalid input.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

LOCKED_ROOT = "tests/locked"


def locked_changes(paths: list[str]) -> list[str]:
    """The changed paths that are locked tests (normalised: no leading ./, forward slashes)."""
    clean = [p.strip().replace("\\", "/").removeprefix("./") for p in paths if p.strip()]
    return sorted({p for p in clean if p == LOCKED_ROOT or p.startswith(LOCKED_ROOT + "/")})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", required=True, help="file with the changed paths, one per line, or - for stdin")
    args = ap.parse_args(argv)
    try:
        text = sys.stdin.read() if args.changed == "-" else Path(args.changed).read_text(encoding="utf-8")
    except OSError as e:
        print(f"cannot read the changed-files list: {e}", file=sys.stderr)
        return 2
    bad = locked_changes(text.splitlines())
    if bad:
        print("This pull request changes locked tests. They are written by the test-author step and approved by the "
              "QE lead; the coding agent never changes them. If a locked test is wrong, it goes back to the "
              "test-author step and the QE lead approves a new digest.", file=sys.stderr)
        for p in bad:
            print(f"  {p}", file=sys.stderr)
        return 1
    print("No locked test changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
