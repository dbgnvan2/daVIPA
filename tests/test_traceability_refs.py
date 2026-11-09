"""Every ``Tests:`` reference in the source must point at something real.

CLAUDE.md makes these references load-bearing for review: a docstring says
which test proves the behaviour it describes, and a reviewer follows it. Two of
them pointed at ``tests/test_vps_ape_deletion.py``, a file that has never
existed — written from memory of what the test was going to be called. Nothing
checked, so nothing said.

This is a source check because the thing being verified *is* the source text.
It fails loudly on a name that does not resolve, and the last test here proves
it can fail at all (P24).

``docs/spec_coverage.md`` is scanned too, and from 2026-11-09 so are the plan,
spec and handoff-note families. A retired criterion keeps its history by naming
the deleted test in plain backticks **without** the ``tests/`` path, so the row
still says what proved it without leaving a pointer a reviewer would follow to
nothing.
"""

import re
from pathlib import Path

import pytest

# This whole file asserts on the REPOSITORY — workflows, packaging, licences,
# docs, traceability — not on application behaviour. Marked `meta` so
# `pytest -m "not meta"` gives a fast app-only run. The default `pytest` run
# still includes it: the marker is for speed, never for skipping.
pytestmark = pytest.mark.meta

REPO = Path(__file__).resolve().parents[1]

# Scanned in full rather than just src/: the first version of this guard looked
# only under src/, and there was a broken reference in conftest.py at the time
# — the exact defect it was written to catch, in a file it could not see.
# ``docs/spec_coverage.md`` is in here because citing tests is its entire
# job: every row names the test that proves its criterion. It was outside the
# scan until 2026-11-05, and the grid rebuild's pre-push sweep found eight rows
# naming tests that had been deleted -- two of them still marked "done". The
# guard could not see the one document most made of the references it checks.
# 2026-11-09: the entry was ``docs/spec_coverage.md``, one file. The six
# ``docs/spec_coverage_*.md`` sidecars were outside the scan, and they hold
# most of this repo's criterion rows — 83 `done` for weekly-tactic scheduling
# alone. The third cold pass over the SST batch resolved their references by
# hand and found two dead ones, both on rows marked `done`, one naming a test
# that has never existed. The SST batch had widened its own Implementation
# column check to the whole family and left this one at the single file.
# 2026-11-09, second entry of the day: the scan stopped at the coverage family,
# so a dead citation in a *plan* was outside it. The fifth cold pass over the
# SAG batch found one by hand — `docs/implementation_plan_2026-06-22.md`'s new
# status line named `tests/test_column_resize.py::test_updf13_…`, two test
# names carried over from the citation it was correcting, against a file that
# has neither. A guard that reads the coverage rows and not the plans is a
# guard over the smaller half of this repo's citations: widening the scan to
# the plan, spec and handoff-note families brought 27 dead references into
# view, 18 of them after the resolver below was taught the two citation forms
# these documents actually use.
SCANNED = (
    "src",
    "tools",
    "conftest.py",
    # Subsumed by `docs/spec_*.md` below, and kept because the entry is what
    # the docstring and `COVERAGE_WITHOUT_PATHS` refer to. Listed first, so
    # the deduplicating walk attributes those files to it.
    "docs/spec_coverage*.md",
    "docs/implementation_plan_*.md",
    "docs/spec_*.md",
    "docs/changes/*.md",
)
SKIP_DIRS = {"venv", ".git", "build", "dist", "__pycache__"}

# Coverage documents that name their tests without a ``tests/`` path, so they
# contribute no reference to this guard and cannot be required to. One file:
# it was generated from a real collection run and lists bare test names in a
# table of its own. `SST-A2` files the convention that would bring such names
# into a guard's domain. The exemption is checked in both directions.
COVERAGE_WITHOUT_PATHS = {
    "docs/spec_coverage_2026-08-19_rename_safe_links.md",
}

# A reference is any tests/... path, wherever it appears. Anchoring on the
# "Tests:" label matched only the first path on that line, so the 22 references
# written as indented continuation lines under a Tests: header were never
# checked — 15% of the domain the docstring claims (P24: a guard whose
# unchecked input path is a silent pass).
_REF = re.compile(r"(tests/[\w/]+\.py)(?:::(\w+))?")


def _scanned_files():
    # `docs/spec_*.md` and `docs/spec_coverage*.md` overlap, so the walk
    # deduplicates: a reference counted twice is reported twice in a failure
    # message, and a count taken off this walk is wrong by however much the
    # globs overlap. (It cannot flip a membership assertion below — `sources`
    # is a set, and the overlapping files belong to neither of the two
    # prefixes those assertions name. The sixth cold pass found this comment
    # claiming it could.)
    seen = set()

    def fresh(path):
        if path in seen:
            return False
        seen.add(path)
        return True

    for entry in SCANNED:
        if "*" in entry:
            yield from (p for p in sorted(REPO.glob(entry)) if fresh(p))
            continue
        target = REPO / entry
        if target.is_file():
            if fresh(target):
                yield target
        elif target.is_dir():
            for path in sorted(target.rglob("*.py")):
                if SKIP_DIRS & set(path.parts):
                    continue
                if fresh(path):
                    yield path


def _references():
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        for match in _REF.finditer(text):
            yield path.relative_to(REPO), match.group(1), match.group(2)


def _defined_names(path):
    """Everything a reference could legitimately be pointing at.

    Test functions and the classes that group them — ``::TestM3UI`` points at
    a class of tests, which is a perfectly good pointer for a reviewer to
    follow — and, since 2026-11-09, the helpers and module constants too. The
    plan and handoff families cite those: `docs/implementation_plan_2026-08-24_window_leak.md`
    names ``::_make_screen`` in five documents' worth of fixture plumbing, and
    `docs/spec_2026-08-18_downloadable_release.md` names ``::GENERATED_AUDIO``.
    Each of those pointers resolves to a real line a reviewer can read, so
    failing them would have been the guard crying wolf on correct prose.
    """
    text = path.read_text(encoding="utf-8")
    return (set(re.findall(r"^\s*(?:async )?def (\w+)", text, re.M))
            | set(re.findall(r"^\s*class (\w+)", text, re.M))
            | set(re.findall(r"^(\w+)\s*=", text, re.M)))


def _resolves(path, name):
    """Is ``name`` something that exists in ``path``?

    Exactly, or as the spec-ID prefix of a family. The second form is how this
    repo's prose cites a group of tests: ``::test_wt_m6b1_`` for seven of
    them, ``::test_cem444a`` for the one whose full name is three times as
    long. A prefix has to stop at a word boundary — the next character is an
    underscore, or the prefix ends with one — so ``::test_updf13_`` does not
    quietly resolve against ``test_updf130``, and it resolves against nothing
    at all in a file that has no such family. That was the citation the fifth
    cold pass found, and it still fails here.
    """
    defined = _defined_names(path)
    if name in defined:
        return True
    return any(
        other.startswith(name)
        and (name.endswith("_") or other[len(name):len(name) + 1] == "_")
        for other in defined)


def test_every_referenced_test_file_exists():
    missing = sorted({
        f"{src}: {target}"
        for src, target, _name in _references()
        if not (REPO / target).exists()
    })
    assert not missing, (
        "these docstrings name a test file that does not exist:\n  "
        + "\n  ".join(missing))


def test_every_referenced_test_name_exists():
    missing = []
    for src, target, name in _references():
        if not name:
            continue
        path = REPO / target
        if not path.exists():
            continue                      # reported by the test above
        if not _resolves(path, name):
            missing.append(f"{src}: {target}::{name}")
    assert not missing, (
        "these references name a test that does not exist:\n  "
        + "\n  ".join(sorted(missing)))


def test_this_guard_can_actually_fire(tmp_path):
    """Guards the guard: the sweep has to be reading real references."""
    found = list(_references())
    # Membership per source, not a count. This asserted a floor of 140 where
    # 784 references exist, so it would have tolerated losing most of its
    # domain — filed as `SST-A1` on 2026-11-08 and replaced here on 2026-11-09,
    # the same way `tests/test_doc_status_claims.py` replaced its own floor: an
    # exact count goes red on every batch, because every batch adds criterion
    # rows, and a band is a floor with better manners. What has to hold is that
    # each arm of the scan is still being read.
    assert any(name for _src, _target, name in found), (
        "no reference carries a ::test_name, so the name check is inert")
    sources = {str(src) for src, _t, _n in found}
    for coverage in sorted(REPO.glob("docs/spec_coverage*.md")):
        name = str(coverage.relative_to(REPO))
        if name in COVERAGE_WITHOUT_PATHS:
            assert "tests/" not in coverage.read_text(encoding="utf-8"), (
                f"{name} is exempted from the check below on the ground that "
                "it names no test by path, and it now does — drop it from "
                "COVERAGE_WITHOUT_PATHS so its references get checked")
            continue
        assert name in sources, (
            f"{name} contributes no test reference — either it is outside the "
            "scan, or its rows have stopped naming their tests. Eight stale "
            "references hid in docs/spec_coverage.md while it sat outside this "
            "scan, and two more in the sidecars while they did")
    assert any(src.startswith("src/") for src in sources), (
        "nothing under src/ is being scanned")
    # One per document family added on 2026-11-09. Membership, not a count:
    # a count goes red on every batch that writes a plan.
    for family, label in (
            ("docs/implementation_plan_", "the implementation-plan family"),
            ("docs/changes/", "the handoff-note family"),
    ):
        assert any(src.startswith(family) for src in sources), (
            f"no reference comes from {label} — either it is outside the "
            "scan, or those documents have stopped citing their tests. The "
            "plans were outside this scan until 2026-11-09, and the fifth "
            "cold pass over the SAG batch had to find a dead citation in one "
            "of them by hand")
    assert any(src.startswith("docs/spec_2") for src in sources), (
        "no reference comes from a dated spec document — the docs/spec_*.md "
        "arm of the scan is reading nothing")
    files = list(_scanned_files())
    assert len(files) == len(set(files)), (
        "a file is scanned twice, so every reference in it is reported twice "
        "and any count taken off this walk is wrong by however much the globs "
        "overlap — docs/spec_*.md and docs/spec_coverage*.md do, which is "
        "what the walk deduplicates")
    # The two citation forms the prose families use, asserted against a file
    # written here rather than against this one. It was written against this
    # one first, and the sixth cold pass measured what that cost: renaming
    # ``test_every_referenced_test_name_exists`` — an ordinary rename, in the
    # file the probe lives in — made two of the assertions falsely red, and
    # left the mid-word rejection passing against a prefix that matched
    # nothing, which is the one assertion written to prove that rejection
    # works. A probe whose subject is written two lines above it cannot drift.
    probe = tmp_path / "test_probe.py"
    probe.write_text(
        "GENERATED_AUDIO = 1\n"
        "\n"
        "def _make_screen():\n"
        "    pass\n"
        "\n"
        "class TestGroup:\n"
        "    def test_inside_a_class(self):\n"
        "        pass\n"
        "\n"
        "def test_wt_m6b1_first():\n"
        "    pass\n"
        "\n"
        "def test_wt_m6b1_second():\n"
        "    pass\n"
        "\n"
        "def test_cem444a_the_long_name():\n"
        "    pass\n",
        encoding="utf-8")
    assert _resolves(probe, "test_cem444a_the_long_name"), (
        "an exact name no longer resolves")
    assert _resolves(probe, "TestGroup") and _resolves(probe, "test_inside_a_class"), (
        "a class of tests, or a test inside one, no longer resolves")
    assert _resolves(probe, "test_wt_m6b1_"), (
        "a spec-ID prefix ending in an underscore no longer resolves, so "
        "every ::test_wt_m6b1_ style citation in the plans would now fail")
    assert _resolves(probe, "test_cem444a"), (
        "a spec-ID prefix stopping at a word boundary no longer resolves, so "
        "the ::test_cem444a style citation would now fail")
    assert not _resolves(probe, "test_cem444a_the_long_nam"), (
        "a prefix that stops mid-word resolves, so the prefix form accepts "
        "truncations of names that do not exist — which is the citation the "
        "fifth cold pass found")
    assert not _resolves(probe, "GENERATED_AUDI"), (
        "a mid-word prefix of a module constant resolves")
    assert _resolves(probe, "GENERATED_AUDIO") and _resolves(probe, "_make_screen"), (
        "module constants and helpers no longer resolve, so the plans' "
        "::GENERATED_AUDIO and ::_make_screen citations would now fail")
    assert not _resolves(probe, "test_absent"), (
        "a name the file does not define resolves, so the resolver accepts "
        "everything and both checks above it are inert")
    assert any(str(src) == "conftest.py" for src, _t, _n in found), (
        "conftest.py is not being scanned — that is where the first broken "
        "reference this guard missed was living")
    # A continuation line under a Tests: header must be matched too.
    block = "    Tests:   tests/test_a.py\n             tests/test_b.py::test_c\n"
    assert [m.group(1) for m in _REF.finditer(block)] == [
        "tests/test_a.py", "tests/test_b.py"]
