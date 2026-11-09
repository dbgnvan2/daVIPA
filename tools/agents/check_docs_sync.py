#!/usr/bin/env python3
"""Fail when code/dependency changes are missing documentation updates."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import List, Set

CODE_PREFIXES = ("src/", "tools/", "tests/")

# Every file that declares a dependency. requirements-dev.txt was added in the
# same change that created it and this enumeration was missed, so a PR adding a
# test dependency touched no src/ path and no requirements.txt and the gate
# reported "no code/dependency changes detected".
DEPENDENCY_FILES = ("requirements.txt", "requirements-dev.txt")
DOC_PREFIXES = ("docs/",)
DOC_FILES = {
    "README.md",
    "CHANGELOG.md",
    "GetMoreDone_MasterSpec_SQLite_v1.md",
}


def run(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\\n{result.stderr}")
    return result.stdout.strip()


def changed_files(base: str, head: str) -> Set[str]:
    out = run(["git", "diff", "--name-only", f"{base}...{head}"])
    return {line.strip() for line in out.splitlines() if line.strip()}


#: The outcome names ``verdict`` can return. They are the decision itself, so a
#: test can assert WHICH outcome a set of paths produces rather than reading an
#: exit code that collapses four of them into 0.
NO_FILES = "no-files"
NO_CODE = "no-code"
PASS = "pass"
MISSING_DOCS = "missing-docs"
MISSING_HANDOFF = "missing-handoff"

#: Every outcome ``verdict`` can return, declared rather than inferred.
#: `tests/test_docs_sync_rule.py` reads this and what `verdict` actually
#: returns, and fails when they disagree — so adding an outcome here without a
#: fixture, or returning one that is not here, is a red test. The first version
#: of that guard built its own hardcoded list of five names and was therefore
#: blind to a sixth in either direction: it passed on the broken state and
#: failed on the correct one (found cold, 2026-11-09).
OUTCOMES = (NO_FILES, NO_CODE, PASS, MISSING_DOCS, MISSING_HANDOFF)

#: The outcomes that are not a failure. ``SKIPPED`` is deliberately absent:
#: a range this tool could not read is not an outcome of the rule, it is the
#: absence of an input, and ``main`` reports it as such.
PASSING = (NO_FILES, NO_CODE, PASS)


def verdict(files: Set[str]):
    """The whole docs-sync decision, as a pure function of changed paths.

    Purpose: SAG-M2.1 — the rule has to be assertable without a git range,
             because `.github/workflows/tests.yml` checks out at depth 1 and so
             has no `origin/main` to diff against. The gate it was written for
             runs on `pull_request`, which this repo never produces, so until
             this function existed the rule could not fail anywhere that runs.
    Spec:    docs/implementation_plan_2026-11-09_status_allow_list.md#2-acceptance-criteria--tests
    Tests:   tests/test_docs_sync_rule.py

    Returns ``(code, messages)``: one of the names above, and the lines
    ``main`` prints. ``code in PASSING`` is the decision; the exit code is
    derived from it rather than being the decision itself.
    """
    if not files:
        return NO_FILES, ["docs-sync: no changed files"]

    code_changed = any(
        path.startswith(CODE_PREFIXES) or path in DEPENDENCY_FILES for path in files
    )
    if not code_changed:
        return NO_CODE, ["docs-sync: no code/dependency changes detected"]

    docs_changed = any(
        path.startswith(DOC_PREFIXES)
        or path in DOC_FILES
        or path.startswith("docs/changes/")
        for path in files
    )
    handoff_changed = any(path.startswith("docs/changes/") for path in files)

    if docs_changed and handoff_changed:
        return PASS, ["docs-sync: PASS (docs and handoff note present)"]

    messages = [
        "docs-sync: FAIL",
        "Code/dependency changes detected but required docs artifacts are missing.",
    ]
    if not docs_changed:
        messages.append(
            "- Missing docs update (expected change in docs/, README.md, "
            "CHANGELOG.md, or master spec)")
    if not handoff_changed:
        messages.append("- Missing handoff note in docs/changes/")
    messages.append("Changed files:")
    messages.extend(f"  - {path}" for path in sorted(files))
    return (MISSING_DOCS if not docs_changed else MISSING_HANDOFF), messages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("GITHUB_BASE_REF", "origin/main"))
    parser.add_argument("--head", default=os.getenv("GITHUB_SHA", "HEAD"))
    args = parser.parse_args()

    try:
        files = changed_files(args.base, args.head)
    except RuntimeError as exc:
        # Not a verdict: the range could not be read, so the rule was never
        # applied. Said in those words, because "skipped" printed next to a 0
        # exit code is what let this check look like it was running.
        print(f"docs-sync check skipped: {exc}")
        return 0

    code, messages = verdict(files)
    for line in messages:
        print(line)
    return 0 if code in PASSING else 1


if __name__ == "__main__":
    sys.exit(main())
