"""The display probe, and the detector that finds what needs it.

Purpose: CIG-M1 — one shared precondition for every test that sets a window
         attribute and reads it back, so a display with no window manager
         produces a skip with a reason rather than a failure that looks like a
         bug in the application.
Spec:    docs/unused-docs/implementation_plan_2026-11-09_ci_green.md#2-acceptance-criteria--tests
Tests:   this file
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest
from _pytest.outcomes import Skipped

from tests import display_capabilities as caps

REPO = Path(__file__).resolve().parents[1]

def _root_name(node):
    """The leftmost name in ``a.b.c`` — the object the call is made on."""
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _is_a_read_back(node, exempt) -> bool:
    """A one-argument ``attributes('-x')``, or a 4-token ``wm attributes`` call.

    Two arguments is a write, which needs no display. ``exempt`` holds the
    names bound to stand-ins defined in the same file: a spy reports back
    whatever was written to it, which is the point of using one.
    """
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    if _root_name(node.func.value) in exempt:
        return False
    if node.func.attr in ("attributes", "wm_attributes"):
        return (len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.startswith("-"))
    if node.func.attr == "call":
        literals = [a.value for a in node.args if isinstance(a, ast.Constant)]
        return len(node.args) == 4 and literals[:2] == ["wm", "attributes"]
    return False


def _stand_in_names(func, classes):
    """Names in this test bound from a class defined in the same file."""
    found = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if _root_name(node.value.func) in classes:
                found |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return found


def _scan(source: str, label: str):
    """``(reads, asks, maps)`` for one module's tests, by AST.

    A read-back reached through a module-level helper in the same file counts:
    ``tests/test_timer_session_endings.py`` reads through ``_topmost_now``, and
    a walk that looked only for the call shape would not see it. Measured
    2026-11-11: one level is enough for this suite.
    """
    tree = ast.parse(source)
    classes = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}

    helpers = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            params = {a.arg for a in node.args.args}
            if any(_is_a_read_back(inner, set())
                   and _root_name(inner.func.value) in params
                   for inner in ast.walk(node)):
                helpers.add(node.name)

    reads, asks, maps = set(), set(), set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef)
                and node.name.startswith("test_")):
            continue
        exempt = _stand_in_names(node, classes)
        for inner in ast.walk(node):
            if _is_a_read_back(inner, exempt):
                reads.add((label, node.name))
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                if inner.func.id == "require":
                    asks.add((label, node.name))
                elif inner.func.id in helpers and not (
                        inner.args and isinstance(inner.args[0], ast.Name)
                        and inner.args[0].id in exempt):
                    reads.add((label, node.name))
        if "mapped_windows" in [a.arg for a in node.args.args]:
            maps.add((label, node.name))
    return reads, asks, maps


def _read_backs():
    """Every test in ``tests/`` that reads a window attribute back."""
    reads, asks, maps = set(), set(), set()
    for path in sorted(REPO.glob("tests/test_*.py")):
        found = _scan(path.read_text(encoding="utf-8"),
                      str(path.relative_to(REPO)))
        reads |= found[0]
        asks |= found[1]
        maps |= found[2]
    return reads, asks, maps


def _independently(attribute: str) -> bool:
    """Ask the display again, without the probe and without its cache."""
    import tkinter as tk

    value, accepts = caps._PROBES[attribute]
    window = tk.Tk()
    try:
        window.withdraw()
        window.tk.call("wm", "attributes", window._w, attribute, value)
        return accepts(window.tk.call("wm", "attributes", window._w, attribute))
    finally:
        window.destroy()


@pytest.mark.parametrize("attribute", ["-topmost", "-alpha"])
def test_cigm11_cigm12_the_probe_agrees_with_the_display(attribute):
    """CIG-M1.1, CIG-M1.2 — the probe reports what a real window does.

    Measured against a second window built here rather than against a platform
    name, and the probe's answer is cached for the run, so this is also what
    would catch a cache poisoned by the first caller.
    """
    assert caps.honours(attribute) is _independently(attribute), (
        f"the probe and a freshly built window disagree about {attribute}; "
        "every precondition in the suite is reading the probe")


def test_cigm13_the_precondition_skips_rather_than_passing(monkeypatch):
    """CIG-M1.3 — no capability means a skip naming the attribute."""
    monkeypatch.setattr(caps, "honours", lambda attribute: False)

    with pytest.raises(Skipped) as skipped:
        caps.require("-topmost")

    assert "-topmost" in str(skipped.value), (
        "the skip does not name the attribute, so a reader of the CI log "
        "cannot tell which capability was missing")
    assert "window manager" in str(skipped.value)


def test_cigm13_an_unknown_attribute_is_an_error_not_a_skip():
    """CIG-M1.3, the other direction — a typo must not read as 'unsupported'.

    `honours("-topmsot")` returning False would skip every test that asked,
    silently and for ever.
    """
    with pytest.raises(KeyError):
        caps.honours("-topmsot")


def _requirers():
    """Every test function containing a call to `require`, by AST."""
    found = set()
    for path in sorted(REPO.glob("tests/test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Name)
                        and inner.func.id == "require"):
                    found.add((str(path.relative_to(REPO)), node.name))
    return found


def test_cghm41_every_real_read_back_asks_or_maps():
    """CGH-M4.1 — a detector, not a list.

    Purpose: the registry this replaced asserted set equality over the eight
             tests that already asked, so it could catch one losing its
             precondition and could not catch a NEW test reading an attribute
             back without one -- which is how six of the seven failures of run
             42586742228 were written (CIG-A1). Run against the tree on
             2026-11-11 it found two more: T5.3 and the -topmost silencing
             test, both asserting a negative that a display reporting nothing
             satisfies for free.
    Spec:    docs/unused-docs/implementation_plan_2026-11-11_ci_guard_honesty.md
    Tests:   this file
    """
    reads, asks, maps = _read_backs()

    unguarded = sorted(reads - asks - maps)
    assert not unguarded, (
        "these tests read a window attribute back on a real window without "
        "asking the shared precondition or mapping the window, so on a display "
        "with no window manager they measure nothing and pass: "
        f"{unguarded}"
    )


def test_cghm42_a_new_offender_is_detected():
    """CGH-M4.2 — adversarial (P7): the case the registry could not see."""
    offender = textwrap.dedent("""
        def test_new_and_unguarded():
            window = ctk.CTk()
            assert window.attributes("-topmost") == 0
    """)
    reads, asks, maps = _scan(offender, "synthetic.py")
    assert reads - asks - maps == {("synthetic.py", "test_new_and_unguarded")}, (
        "a new test reading -topmost back with no precondition was not detected"
    )

    guarded = textwrap.dedent("""
        def test_new_but_asks():
            require("-topmost")
            window = ctk.CTk()
            assert window.attributes("-topmost") == 0
    """)
    reads, asks, maps = _scan(guarded, "synthetic.py")
    assert reads - asks - maps == set(), "a test that asks was still reported"

    spied = textwrap.dedent("""
        class _Spy:
            def attributes(self, *args):
                return 0

        def test_reads_its_own_spy():
            window = _Spy()
            assert window.attributes("-topmost") == 0
    """)
    reads, _, _ = _scan(spied, "synthetic.py")
    assert reads == set(), "a read on a stand-in defined in the file was flagged"


def test_cghm43_the_display_dependent_count_is_exact():
    """CGH-M4.3 — how much a headless runner cannot assert, as a number.

    Four, after CIG-A2 and CIG-A3 moved four of the eight onto mapped windows
    and a spy. An exact count, not a floor: a floor hides the narrowing it
    exists to catch, and a skip nobody decided on is as much a defect as a
    precondition dropped.
    """
    reads, asks, maps = _read_backs()

    assert len(asks) == 4, (
        f"{len(asks)} tests now skip where the display has no window manager, "
        f"not four: {sorted(asks)}"
    )
    assert asks <= reads, (
        "these tests ask the display precondition and never read an attribute "
        f"back, so the skip buys nothing: {sorted(asks - reads)}"
    )


def test_cigm14_the_private_copy_of_the_precondition_is_gone():
    """CIG-M1.4 — the one test that had its own copy uses the shared one.

    Its `_TOPMOST_ON` survives, because the *restore* assertion still reads
    Tk's spellings; what must not survive is a second skip condition with its
    own wording, which is what left the other seven uncovered.
    """
    source = (REPO / "tests/test_weekly_tactic_completion_widgets.py").read_text(
        encoding="utf-8")
    assert "this display does not honour" not in source, (
        "the private skip wording is back; the reason belongs in "
        "tests/display_capabilities.py so every caller shares it")
    assert "_TOPMOST_ON" in source, (
        "the restore assertion lost the spellings it reads Tk's answer with")


def test_cigm15_the_precondition_does_not_skip_where_the_attribute_works():
    """CIG-M1.5 — on a desktop the seven keep their teeth.

    The precondition exists to make CI readable, not to make the suite quieter
    here. If this machine honours the attribute, `require` must be a no-op.
    """
    for attribute in ("-topmost", "-alpha"):
        if not caps.honours(attribute):
            pytest.skip(f"this display does not honour {attribute}; the "
                        "no-op direction cannot be observed on it")
        assert caps.require(attribute) is None, (
            f"require({attribute!r}) skipped on a display that honours it")
