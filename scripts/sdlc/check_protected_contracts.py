"""Protected-contracts check for code-repo pull requests (spec 02 section 6).

Fails a PR that changes a protected file or endpoint unless its story has `"changes_protected_contract": true` in
the approved plan.json (G3). Python standard library plus PyYAML (to read OpenAPI YAML); no orchestrator imports,
so code repos can run it on their own.

The PR description names the intent and the story (PLAN-G2.md Q13, story IDs from spec 03):

    INT-12
    Story: US-3

Usage:
    python check_protected_contracts.py --repo org/orders-api --pr-body body.md --changed changed.txt \
        --protected protected-contracts.json [--plan plan.json] \
        [--base-contract base.yaml --head-contract head.yaml]

Exit codes: 0 pass, 1 protected contract changed without a contract-change story, 2 missing or invalid input.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_INTENT = re.compile(r"\bINT-(\d+)\b")
_STORY = re.compile(r"^\s*Story:\s*(US-\d+)\s*$", re.M | re.I)
_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


class InputError(Exception):
    pass


@dataclass
class Result:
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    allowed: bool = False

    @property
    def ok(self) -> bool:
        return not self.violations or self.allowed


def parse_pr(body: str) -> tuple[str, str | None]:
    intents = sorted(set(_INTENT.findall(body or "")), key=int)
    if not intents:
        raise InputError("The PR description must name its intent (INT-n).")
    if len(intents) > 1:
        raise InputError(f"The PR description names more than one intent: {', '.join('INT-' + i for i in intents)}.")
    story = _STORY.search(body or "")
    return f"INT-{intents[0]}", story.group(1).upper() if story else None


def load_contract(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        import yaml
    except ImportError as e:  # pragma: no cover - the workflow installs it
        raise InputError("PyYAML is needed to read a YAML contract: pip install pyyaml") from e
    doc = yaml.safe_load(text)
    return doc if isinstance(doc, dict) else {}


def operations(doc: dict) -> dict[str, str]:
    """'METHOD /path' -> canonical JSON of the operation (path-level parameters included)."""
    out = {}
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        shared = item.get("parameters")
        for method, op in item.items():
            if method.lower() in _METHODS:
                out[f"{method.upper()} {path}"] = json.dumps({"op": op, "parameters": shared}, sort_keys=True,
                                                             default=str)
    return out


def story_is_contract_change(plan: dict | None, story: str | None) -> bool:
    if not plan or not story:
        return False
    return any(s.get("id", "").upper() == story and s.get("changes_protected_contract") is True for s in plan.get("stories", []))


def check(*, repo: str, pr_body: str, changed: list[str], protected: dict, plan: dict | None = None,
          base_contract: str | None = None, head_contract: str | None = None) -> Result:
    intent, story = parse_pr(pr_body)
    if protected.get("intent_id") != intent:
        raise InputError(f"protected-contracts.json is for {protected.get('intent_id')}, but the PR names {intent}.")
    res = Result()
    entry = (protected.get("repos") or {}).get(repo)
    if not entry:
        res.notes.append(f"{intent} protects nothing in {repo}.")
        return res
    for path in sorted(changed):
        hits = [p for p in entry.get("files", []) if fnmatch.fnmatch(path, p)]
        if hits:
            res.violations.append(f"changes protected file {path}")
    if entry.get("endpoints"):
        if base_contract is None or head_contract is None:
            raise InputError(f"{repo} has protected endpoints; pass --base-contract and --head-contract.")
        base, head = operations(load_contract(base_contract)), operations(load_contract(head_contract))
        for ep in entry["endpoints"]:
            if ep in base and ep not in head:
                res.violations.append(f"removes protected endpoint {ep}")
            elif ep in base and base[ep] != head[ep]:
                res.violations.append(f"changes protected endpoint {ep}")
    if res.violations and story_is_contract_change(plan, story):
        res.allowed = True
        res.notes.append(f"Allowed: story {story} is marked as a contract change in plan.json.")
    elif res.violations:
        why = "the PR description names no story (add 'Story: US-n')" if story is None else (
            f"story {story} is not marked as a contract change in plan.json")
        res.notes.append(f"Not allowed: {why}.")
    return res


def _read(path: str | None) -> str | None:
    return Path(path).read_text(encoding="utf-8") if path else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr-body", required=True, help="file with the PR description")
    ap.add_argument("--changed", required=True, help="file with one changed path per line")
    ap.add_argument("--protected", required=True, help="protected-contracts.json from the artifact repo")
    ap.add_argument("--plan", help="plan.json from the artifact repo (absent before G3)")
    ap.add_argument("--base-contract")
    ap.add_argument("--head-contract")
    args = ap.parse_args(argv)
    try:
        protected = json.loads(_read(args.protected))
        plan_text = _read(args.plan) if args.plan and Path(args.plan).is_file() else None
        res = check(
            repo=args.repo, pr_body=_read(args.pr_body), protected=protected,
            changed=[ln.strip() for ln in _read(args.changed).splitlines() if ln.strip()],
            plan=json.loads(plan_text) if plan_text else None,
            base_contract=_read(args.base_contract), head_contract=_read(args.head_contract),
        )
    except (InputError, OSError, json.JSONDecodeError) as e:
        print(f"protected-contracts: error: {e}")
        return 2
    for v in res.violations:
        print(f"protected-contracts: {v}")
    for n in res.notes:
        print(f"protected-contracts: {n}")
    print("protected-contracts: " + ("PASS" if res.ok else "FAIL"))
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
