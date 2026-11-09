"""The docs-sync rule, asserted where it can fail before a push.

Purpose: SAG-M2 — `tools/agents/check_docs_sync.py` is the check that says a
         code change must carry a documentation change and a handoff note. It
         existed only inside `.github/workflows/agent-docs-gate.yml`, which
         triggers on `pull_request`, and this repo's standing instruction is to
         open none. So the rule had never run on the way work ships here, and
         `CLAUDE.md` described an enforcement that could not fire.

         `.github/workflows/tests.yml` says it in its own header: "No check
         lives only here. Every assertion belongs in the pytest suite so it can
         fail before a push." The gate was the same defect in the other
         direction — a check reachable from exactly one surface, and not the one
         anyone uses. `P25` in `~/.claude/standards/learnings.md` is the
         pattern.

         These tests are over `verdict`, which is the decision as a pure
         function of changed paths. That is deliberate and is the judgement
         `SST-A8` said was missing: a test that asked git for the real range
         would skip on CI, because `tests.yml` checks out at depth 1 and has no
         `origin/main` to diff against.
Spec:    docs/implementation_plan_2026-11-09_status_allow_list.md#2-acceptance-criteria--tests
Tests:   this file
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "tools/agents/check_docs_sync.py"


def _gate():
    """The checker, imported rather than grepped.

    `tools/` is not a package, and a text search over this file has already
    been shown to match the comment explaining a fix rather than the code doing
    it (`tests/test_release_licensing.py` records that measurement).
    """
    spec = importlib.util.spec_from_file_location("_gmd_docs_sync_rule", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: (paths, expected outcome). Every fixture is a change this repo has actually
#: made or could make in one commit; the expected outcome is the name `verdict`
#: returns, not an exit code, because four distinct outcomes share exit code 0.
CASES = [
    # The shape this batch itself has: code, docs and a handoff note.
    (("tools/agents/check_docs_sync.py",
      "docs/implementation_plan_2026-11-09_status_allow_list.md",
      "docs/changes/2026-11-09-status-allow-list.md"), "pass"),
    # Code and documents, and no note. The note is the thing this repo's
    # working agreement asks for after every batch, so it is asserted apart
    # from the documents and not folded into them.
    (("src/getmoredone/db_manager.py", "docs/USER_GUIDE.md"), "missing-handoff"),
    # Code and a note, no other document.
    (("src/getmoredone/db_manager.py", "docs/changes/2026-11-09-x.md"), "pass"),
    # Code alone.
    (("src/getmoredone/db_manager.py",), "missing-docs"),
    # Tests count as code: a test-only change still gets a note here.
    (("tests/test_db_manager.py",), "missing-docs"),
    # Documents alone are not a code change.
    (("docs/USER_GUIDE.md", "README.md"), "no-code"),
    # Nothing at all.
    ((), "no-files"),
    # A dependency file is a code change even with no src/ path — SAG-M2.2.
    (("requirements.txt", "docs/USER_GUIDE.md"), "missing-handoff"),
    (("requirements-dev.txt",), "missing-docs"),
    # A path under neither tree: the repo root's own documents are in DOC_FILES,
    # but a root script is not code by this rule, which is worth pinning rather
    # than discovering.
    (("start.sh",), "no-code"),
]


@pytest.mark.parametrize("paths,expected", CASES)
def test_sagm21_the_docs_sync_rule_decides_on_paths_alone(paths, expected):
    """SAG-M2.1 — the decision, over a set of paths, with no git."""
    gate = _gate()
    code, messages = gate.verdict(set(paths))

    assert code == expected, (
        f"{sorted(paths)} was decided {code!r}, expected {expected!r}; "
        f"the gate printed:\n  " + "\n  ".join(messages))
    assert messages, "a verdict with no message would print nothing at all"
    assert (code in gate.PASSING) == expected.startswith(("pass", "no-")), (
        f"{code!r} is on the wrong side of PASSING, so the exit code and the "
        "decision disagree")


def test_sagm22_a_dev_dependency_alone_is_a_code_change():
    """SAG-M2.2 — the miss the tool's own comment records.

    The gate keyed on the literal "requirements.txt", so a change adding a test
    dependency matched no code prefix and passed as "no code/dependency
    changes detected". `tests/test_release_licensing.py` asserts the
    enumeration exists; this asserts the **decision** uses it, which is the
    half a text search cannot see.
    """
    gate = _gate()
    for name in gate.DEPENDENCY_FILES:
        code, _ = gate.verdict({name})
        assert code not in gate.PASSING, (
            f"a change to {name} alone passed the docs-sync rule, so that "
            "dependency file is in the enumeration and not in the decision")


def test_sagm23_an_unavailable_range_is_skipped_not_passed(capsys, monkeypatch):
    """SAG-M2.3 — an unread range is not a verdict.

    `main` returns 0 either way, which is why this asserts on what it *says*:
    a range it could not read must be reported as skipped and must not print
    one of the rule's own outcomes. A check that prints PASS when it never ran
    is how the gate came to look like it was enforcing something.
    """
    gate = _gate()
    monkeypatch.setattr(
        sys, "argv",
        ["check_docs_sync.py", "--base", "refs/heads/no-such-base-ref-sagm23",
         "--head", "HEAD"])

    gate.main()

    printed = capsys.readouterr().out
    assert "skipped" in printed, (
        "a range the tool could not read was not reported as skipped:\n" + printed)
    assert "PASS" not in printed and "FAIL" not in printed, (
        "the tool announced one of the rule's outcomes for a range it never "
        "read:\n" + printed)


def _returned_outcome_names():
    """The names `verdict` returns as its first tuple element, by AST.

    Read off the function rather than from a list kept here. The first version
    of this guard carried its own hardcoded set of five names and filtered the
    walk by it, so a sixth outcome was invisible to both sides of the
    comparison: the guard passed with the sixth unfixtured and failed once the
    fixture was added. Found cold, 2026-11-09, by adding a sixth and watching
    it pass — a guard that cannot fail on its subject and fires on correct
    work, in one assertion.
    """
    tree = ast.parse(GATE.read_text(encoding="utf-8"))
    verdict = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "verdict")

    names, inline = set(), []
    for node in ast.walk(verdict):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Tuple):
            continue
        first = node.value.elts[0]
        # `return PASS, [...]` and `return (A if c else B), [...]`.
        for part in ([first.body, first.orelse] if isinstance(first, ast.IfExp)
                     else [first]):
            if isinstance(part, ast.Name):
                names.add(part.id)
            else:
                inline.append(ast.dump(part))
    return names, inline


def test_sagm24_every_outcome_the_tool_can_return_has_a_fixture():
    """SAG-M2.4 — the suite covers the decision, not a sample of it.

    A new outcome added to `verdict` with no case in `CASES` fails here, and so
    does one returned as a bare string instead of a declared constant.
    """
    gate = _gate()
    returned, inline = _returned_outcome_names()

    assert not inline, (
        "verdict() returns something other than one of the declared outcome "
        f"constants: {inline}. An outcome spelled inline is one this file "
        "cannot see.")
    assert returned == {
        name for name in vars(gate)
        if name.isupper() and getattr(gate, name) in gate.OUTCOMES
        and isinstance(getattr(gate, name), str)}, (
        "verdict() and OUTCOMES disagree about which outcomes exist: returned "
        f"{sorted(returned)}")

    defined = set(gate.OUTCOMES)
    assert len(defined) == len(gate.OUTCOMES), (
        "two outcome constants share a value, so one of them can never be "
        "distinguished in a fixture")
    assert set(gate.PASSING) <= defined, (
        "PASSING names an outcome that is not in OUTCOMES")

    covered = {expected for _, expected in CASES}
    assert covered == defined, (
        "the outcomes of the docs-sync rule and the fixtures in CASES "
        f"disagree. No fixture: {sorted(defined - covered)}. Fixtures for an "
        f"outcome the tool cannot return: {sorted(covered - defined)}")
