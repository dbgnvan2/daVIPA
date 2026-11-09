"""The display probe that keeps seven tests honest on a headless runner.

Purpose: CIG-M1 — one shared precondition for every test that sets a window
         attribute and reads it back, so a display with no window manager
         produces a skip with a reason rather than a failure that looks like a
         bug in the application.
Spec:    docs/implementation_plan_2026-11-09_ci_green.md#2-acceptance-criteria--tests
Tests:   this file
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from _pytest.outcomes import Skipped

from tests import display_capabilities as caps

REPO = Path(__file__).resolve().parents[1]

#: Every test that reads a display attribute back **from a window it never
#: maps**, and so needs the precondition. The qualifier is the whole point:
#: `tests/test_tk_offscreen.py` has two more `-alpha` read-backs that are
#: deliberately absent from this registry because they map their window first
#: and so pass on CI. Written without the qualifier, this comment claimed a
#: completeness it did not have — found by the cold pass, 2026-11-09.
#:
#: A registry, not a detector: it cannot notice a *new* test that reads an
#: attribute back without asking, and `CIG-A1` records that gap. What it does
#: catch is the precondition being dropped from one of these eight, which is
#: how the seven failures of run 42586742228 were written in the first place —
#: six of them never had one, and the seventh had a private copy nobody else
#: could use.
EXPECTED_CALLERS = {
    ("tests/test_timer_session_endings.py",
     "test_t51_a_modal_drops_the_timers_always_on_top"),
    ("tests/test_timer_session_endings.py",
     "test_t52_the_timer_is_topmost_again_afterwards"),
    ("tests/test_timer_session_endings.py",
     "test_t56_a_second_modal_does_not_hand_the_flag_back_early"),
    ("tests/test_timer_session_endings.py",
     "test_t57_an_unbalanced_resume_does_not_break_the_next_modal"),
    ("tests/test_weekly_tactic_surfaces.py",
     "test_wt_m6b6_a_notice_lowers_an_always_on_top_parent"),
    ("tests/test_tk_offscreen.py",
     "test_alpha_still_passes_through_the_attributes_wrapper"),
    ("tests/test_tk_offscreen.py",
     "test_raw_tkinter_windows_are_hidden_and_registered_too"),
    ("tests/test_weekly_tactic_completion_widgets.py",
     "test_wtpw_the_prompt_survives_a_real_always_on_top_parent"),
}


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


def test_cigm14_every_display_dependent_test_uses_the_shared_precondition():
    """CIG-M1.4 — the eight, exactly, and by AST rather than by grep.

    Exact set equality in both directions: a test that loses its precondition
    is as much a defect as one that gains a skip nobody decided on.
    """
    found = _requirers()

    missing = sorted(EXPECTED_CALLERS - found)
    assert not missing, (
        "these tests read a display attribute back and no longer ask the "
        "shared precondition first, so they fail rather than skip where the "
        f"display has no window manager: {missing}")

    unexpected = sorted(found - EXPECTED_CALLERS)
    assert not unexpected, (
        "these tests ask the precondition and are not in EXPECTED_CALLERS — "
        "if the skip is deliberate, register it here with the reason: "
        f"{unexpected}")


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
