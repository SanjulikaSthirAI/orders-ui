"""What a STORY branch's CI runs (review item 4): its own locked tests and the earlier stories', never the stories
not built yet, and never the functional tests. The CI log always lists what was left out and why.

Used by the `tests` job of a code repo's sdlc-ci workflow. Standard library only (code repos run it on their own).

On a branch named `story/INT-n/US-n` (the head ref of a story PR, or the pushed branch) it reads the approved
plan.json from the intent's branch in the artifact repo to learn the build order. On any other ref it excludes
nothing. If it cannot read the plan on a story branch it exits 2: it fails closed rather than running the wrong tests.

    python story_ci_args.py --mode pytest                          # one `--ignore` path per line
    python story_ci_args.py --mode files --glob "tests/**/*.test.js"   # the test files to run, one per line

Environment: GITHUB_HEAD_REF or GITHUB_REF_NAME, ARTIFACT_REPO (owner/name), GH_TOKEN, GITHUB_API_URL (optional).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

_STORY_BRANCH = re.compile(r"^story/(INT-\d+)/(US-\d+)$")


def parse_ref(ref: str) -> tuple[str, str] | None:
    m = _STORY_BRANCH.match(ref or "")
    return (m.group(1), m.group(2)) if m else None


def select(intent_id: str, order: list[str], story_id: str) -> dict:
    """Same rule as the orchestrator's locked_tests.select_for_story: run this story and the earlier ones; exclude the
    later ones and the functional tests, with a reason each."""
    if story_id not in order:
        raise ValueError(f"{story_id} is not in the plan")
    i = order.index(story_id)
    root = f"tests/locked/{intent_id}"
    excluded = [{"dir": f"{root}/{sid}/", "story": sid, "reason": f"not built yet (planned after {story_id})"}
                for sid in order[i + 1:]]
    excluded.append({"dir": f"{root}/functional/", "story": None,
                     "reason": "functional tests run at intent level, not in story CI"})
    return {"run": [f"{root}/{sid}/" for sid in order[: i + 1]], "excluded": excluded}


def plan_order(intent_id: str, get) -> list[str]:
    """The story IDs in build order, from the intent's plan.json on its artifact-repo branch. `get(path)` returns
    parsed JSON for a GitHub API path, or raw text when the path ends in `?raw`."""
    n = intent_id.split("-")[1]
    branches = [b["name"] for b in get("/branches?per_page=100")]
    branch = next((b for b in branches if re.match(rf"^feature/INT-{n}-", b)), None)
    if branch is None:
        raise LookupError(f"no artifact-repo branch feature/INT-{n}-* found")
    folder = "sdlc/" + branch.removeprefix("feature/")
    plan = json.loads(get(f"/contents/{folder}/plan.json?ref={branch}&raw"))
    return [s["id"] for s in plan["stories"]]


def _github_get(repo: str, token: str | None, api: str):
    def get(path: str):
        raw = path.endswith("&raw")
        url = f"{api}/repos/{repo}{path.removesuffix('&raw')}"
        headers = {"Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:  # noqa: S310
            body = r.read().decode("utf-8")
        return body if raw else json.loads(body)

    return get


def run(mode: str, pattern: str | None, env: dict, get=None) -> tuple[list[str], dict | None]:
    """(lines to print, the selection or None). Raises on a story branch whose plan can't be read."""
    ref = env.get("GITHUB_HEAD_REF") or env.get("GITHUB_REF_NAME") or ""
    parsed = parse_ref(ref)
    sel = None
    if parsed:
        intent_id, story_id = parsed
        get = get or _github_get(env["ARTIFACT_REPO"], env.get("GH_TOKEN"), env.get("GITHUB_API_URL", "https://api.github.com"))
        sel = select(intent_id, plan_order(intent_id, get), story_id)
    excluded = [e["dir"] for e in sel["excluded"]] if sel else []
    if mode == "pytest":
        return excluded, sel
    files = sorted(f.replace("\\", "/") for f in glob.glob(pattern or "tests/**/*.test.js", recursive=True))
    return [f for f in files if not any(f.startswith(d) for d in excluded)], sel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("pytest", "files"), required=True)
    ap.add_argument("--glob", dest="pattern")
    args = ap.parse_args(argv)
    try:
        lines, sel = run(args.mode, args.pattern, dict(os.environ))
    except (KeyError, LookupError, ValueError, OSError, urllib.error.URLError) as e:
        print(f"cannot choose the locked tests for this story branch: {e}", file=sys.stderr)
        return 2
    if sel:
        print("Locked tests for this story branch:\n" + json.dumps(sel, indent=2), file=sys.stderr)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
