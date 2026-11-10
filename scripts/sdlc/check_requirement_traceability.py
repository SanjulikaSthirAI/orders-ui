"""Requirement-traceability check for code-repo pull requests (spec 04 section 5.3, PLAN-G4.md Q3).

Passes only if every acceptance criterion of the PR's story has at least one passing test named with its ID.
Python standard library only; no orchestrator imports, so code repos can run it on their own.

Inputs:
- the PR description, naming the intent (INT-n) and the story ("Story: US-n");
- plan.json from the intent's artifact branch (approved at G3), which lists the story's acceptance criteria;
- JUnit XML reports from the test job.

A test counts for AC-1.1 if its JUnit name (classname and name) contains the ID as `AC-1.1` or `AC_1_1`, for
example `test_AC_1_1_refund_window` or `test_refund_window[AC-1.1-29d]`, and it passed (no failure, error or
skipped element).

Usage:
    python check_requirement_traceability.py --pr-body body.md --plan plan.json --junit reports/*.xml

Exit codes: 0 pass, 1 an acceptance criterion has no passing test, 2 missing or invalid input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - parses the repo's own test reports
from pathlib import Path

_INTENT = re.compile(r"\bINT-(\d+)\b")
_STORY = re.compile(r"^\s*Story:\s*(US-\d+)\s*$", re.M | re.I)


class InputError(Exception):
    pass


def ac_pattern(ac_id: str) -> re.Pattern:
    m = re.fullmatch(r"AC-(\d+)\.(\d+)", ac_id)
    if not m:
        raise InputError(f"invalid acceptance criterion ID {ac_id!r} in plan.json")
    a, b = m.groups()
    return re.compile(rf"(?<![A-Za-z0-9])AC[-_]{a}[._]{b}(?!\d)", re.I)


def parse_junit(text: str) -> list[dict]:
    """[{name, passed}] for every testcase in a JUnit XML document."""
    try:
        root = ET.fromstring(text)  # noqa: S314
    except ET.ParseError as e:
        raise InputError(f"invalid JUnit XML: {e}") from e
    out = []
    for case in root.iter("testcase"):
        name = ".".join(x for x in (case.get("classname"), case.get("name")) if x)
        failed = any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        out.append({"name": name, "passed": not failed})
    return out


def check(*, pr_body: str, plan: dict, cases: list[dict]) -> tuple[bool, list[str]]:
    intents = sorted(set(_INTENT.findall(pr_body or "")), key=int)
    if len(intents) != 1:
        raise InputError("The PR description must name exactly one intent (INT-n).")
    if plan.get("intent_id") != f"INT-{intents[0]}":
        raise InputError(f"plan.json is for {plan.get('intent_id')}, but the PR names INT-{intents[0]}.")
    m = _STORY.search(pr_body or "")
    if not m:
        raise InputError("The PR description must name its story ('Story: US-n').")
    story = next((s for s in plan.get("stories", []) if s.get("id", "").upper() == m.group(1).upper()), None)
    if story is None:
        raise InputError(f"{m.group(1)} is not a story in plan.json.")
    if not cases:
        raise InputError("No test cases found in the JUnit reports.")
    lines, ok = [], True
    for ac in story.get("acceptance_criteria", []):
        pat = ac_pattern(ac["ac_id"])
        named = [c for c in cases if pat.search(c["name"])]
        passing = [c for c in named if c["passed"]]
        if passing:
            lines.append(f"{ac['ac_id']}: {len(passing)} passing test(s), e.g. {passing[0]['name']}")
        else:
            ok = False
            why = "tests named with it did not pass" if named else "no test is named with its ID"
            lines.append(f"{ac['ac_id']}: FAIL, {why}")
    return ok, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pr-body", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--junit", required=True, nargs="+")
    args = ap.parse_args(argv)
    try:
        cases = [c for f in args.junit for c in parse_junit(Path(f).read_text(encoding="utf-8"))]
        ok, lines = check(pr_body=Path(args.pr_body).read_text(encoding="utf-8"),
                          plan=json.loads(Path(args.plan).read_text(encoding="utf-8")), cases=cases)
    except (InputError, OSError, json.JSONDecodeError) as e:
        print(f"requirement-traceability: error: {e}")
        return 2
    for line in lines:
        print(f"requirement-traceability: {line}")
    print("requirement-traceability: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
