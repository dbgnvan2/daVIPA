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
        # One argument is a read whether or not the attribute is written out:
        # requiring a literal missed `window.attributes(attribute)`, and the
        # one test in this suite that reads back is parametrised on exactly
        # that name. Two arguments is a write, which needs no display.
        return len(node.args) == 1 and not node.keywords
    if node.func.attr == "call":
        literals = [a.value for a in node.args if isinstance(a, ast.Constant)]
        return len(node.args) == 4 and literals[:2] == ["wm", "attributes"]
    return False


def _stand_in_classes(tree):
    """Classes in this file that are stand-ins, not real windows.

    A stand-in has no bases: every one in this suite (``_FakeWindow``,
    ``_RecordingTk``, ``_TopmostSpy``) answers for itself. A class WITH bases
    is the opposite case -- ``tests/test_after_tracker.py`` builds
    ``class _Window(TrackedAfterMixin, ctk.CTkToplevel)`` and
    ``tests/test_reward_celebration.py`` a ``_Host`` the same way, and both are
    real always-on-top-capable Tk windows. Exempting those by their name alone
    made a read-back on one invisible, which is what this detector exists to
    prevent (cold pass, 2026-11-11).

    Declared anywhere, not only at the top level: a spy class written inside
    the one test that needs it is the most common shape of all.
    """
    return {node.name for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and not node.bases}


def _bound_names(target):
    """Every plain name a binding target introduces, through tuples."""
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        found = set()
        for element in target.elts:
            found |= _bound_names(element)
        return found
    return set()


def _from_a_stand_in(target, value, classes):
    """The names ``target = value`` binds to a stand-in, pairing tuples.

    ``window, other = _Spy(), _Spy()`` binds both, and a tuple on the right is
    not a call -- which a check for a call alone reported as a real read.
    """
    if (isinstance(target, (ast.Tuple, ast.List))
            and isinstance(value, (ast.Tuple, ast.List))
            and len(target.elts) == len(value.elts)):
        found = set()
        for element, bound in zip(target.elts, value.elts):
            found |= _from_a_stand_in(element, bound, classes)
        return found
    if isinstance(value, ast.Call) and _root_name(value.func) in classes:
        return _bound_names(target)
    return set()


def _stand_in_names(func, classes):
    """Names in this test bound from a stand-in class defined in the same file.

    Assignment, annotated assignment and ``with ... as`` all bind, and a tuple
    target binds several; handling only the first of those reported a spied
    read as a real one.
    """
    found = set()
    for node in ast.walk(func):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            for target in targets:
                found |= _from_a_stand_in(target, node.value, classes)
        elif isinstance(node, ast.withitem):
            if (isinstance(node.context_expr, ast.Call)
                    and _root_name(node.context_expr.func) in classes
                    and node.optional_vars is not None):
                found |= _bound_names(node.optional_vars)
    return found


def _scan(source: str, label: str):
    """``(reads, asks, maps)`` for one module's tests, by AST.

    A read-back reached through a module-level helper in the same file counts:
    ``tests/test_timer_session_endings.py`` reads through ``_topmost_now``, and
    a walk that looked only for the call shape would not see it. Measured
    2026-11-11: one level is enough for this suite.

    A helper is any same-file function that reads an attribute back, whatever
    window it reads from. Until the cold pass of 2026-11-11 it had to read
    from one of its own parameters, which made ``_independently`` below -- a
    helper that builds its own window, the natural shape for this -- invisible,
    and with it every test calling one.
    """
    tree = ast.parse(source)
    classes = _stand_in_classes(tree)

    # A helper is any same-file function that reads an attribute back; one
    # that asks the precondition itself guards every caller, so the ask
    # propagates with the read. Carrying the read without the ask reported a
    # self-guarding helper's callers as unguarded (cold pass, 2026-11-11).
    helpers, guarding_helpers = set(), set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("test_"):
            if any(_is_a_read_back(inner, _stand_in_names(node, classes))
                   for inner in ast.walk(node)):
                helpers.add(node.name)
                if any(isinstance(inner, ast.Call)
                       and isinstance(inner.func, ast.Name)
                       and inner.func.id == "require"
                       for inner in ast.walk(node)):
                    guarding_helpers.add(node.name)

    reads, asks, maps = set(), set(), set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef)
                and node.name.startswith("test_")):
            continue
        exempt = _stand_in_names(node, classes)
        for inner in ast.walk(node):
            if _is_a_read_back(inner, exempt):
                reads.add((label, node.name))
            # Only the bare `require(...)` the suite imports counts as
            # asking. Accepting `caps.require(...)` as well was tried on
            # 2026-11-11 and reverted: the two tests OF `require` call it that
            # way while monkeypatching the probe, so they are not
            # display-dependent, and counting them took the exact count in
            # test_cghm43 from 4 to 6. A guarded test written the attribute
            # way would be reported as unguarded -- loudly, with the file and
            # name, not silently.
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                if inner.func.id == "require":
                    asks.add((label, node.name))
                elif inner.func.id in helpers and not (
                        inner.args and isinstance(inner.args[0], ast.Name)
                        and inner.args[0].id in exempt):
                    reads.add((label, node.name))
                    if inner.func.id in guarding_helpers:
                        asks.add((label, node.name))
        if "mapped_windows" in caps.fixture_names(node):
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


#: The read-backs that must NOT ask the precondition, with the reason. Only
#: one exists: a test that compares the probe against a freshly built window
#: cannot be gated by the probe -- that would skip it exactly where it has
#: something to measure. Asserted to be exactly this, so an exemption cannot
#: be added quietly and a stale one cannot linger.
EXEMPT_FROM_THE_PRECONDITION = {
    ("tests/test_display_capabilities.py",
     "test_cigm11_cigm12_the_probe_agrees_with_the_display"),
}


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

    assert EXEMPT_FROM_THE_PRECONDITION <= reads, (
        "an exemption names a test the detector no longer sees as a "
        "read-back, so it is hiding nothing and may be hiding something: "
        f"{sorted(EXEMPT_FROM_THE_PRECONDITION - reads)}")
    assert len(EXEMPT_FROM_THE_PRECONDITION) == 1, (
        f"{len(EXEMPT_FROM_THE_PRECONDITION)} tests are exempt from the "
        "precondition; each one is a test that passes on a bare display")

    unguarded = sorted(reads - asks - maps - EXEMPT_FROM_THE_PRECONDITION)
    assert not unguarded, (
        "these tests read a window attribute back on a real window without "
        "asking the shared precondition or mapping the window, so on a display "
        "with no window manager they measure nothing and pass: "
        f"{unguarded}"
    )


#: Each case is a module source and the tests the detector must report as
#: unguarded read-backs. Every shape here was measured against this tree: the
#: first four when the detector replaced the registry, the rest by the two
#: cold passes of 2026-11-11, which found the detector blind or wrong on each.
_DETECTOR_CASES = [
    ("a new test reading -topmost back with no precondition", """
        def test_offender():
            window = ctk.CTk()
            assert window.attributes("-topmost") == 0
    """, {"test_offender"}),

    ("a test that asks the precondition", """
        def test_asks():
            require("-topmost")
            window = ctk.CTk()
            assert window.attributes("-topmost") == 0
    """, set()),

    ("a read on a stand-in defined in the file", """
        class _Spy:
            def attributes(self, *args):
                return 0

        def test_reads_its_own_spy():
            window = _Spy()
            assert window.attributes("-topmost") == 0
    """, set()),

    ("a read through a helper that builds its own window", """
        def _set_and_read(attribute):
            window = tk.Tk()
            window.tk.call("wm", "attributes", window._w, attribute, 1)
            return window.tk.call("wm", "attributes", window._w, attribute)

        def test_reads_through_a_helper_of_its_own():
            assert _set_and_read("-topmost") == 1
    """, {"test_reads_through_a_helper_of_its_own"}),

    # A class WITH bases is a real window, not a stand-in. tests/
    # test_after_tracker.py and tests/test_reward_celebration.py both build one
    # over ctk.CTkToplevel, and the celebration host is the timer's own window.
    ("a read on a real window subclassed in the file", """
        class _Window(SomeMixin, ctk.CTkToplevel):
            pass

        def test_reads_a_real_subclass(root):
            window = _Window(root)
            assert window.attributes("-topmost") == 0
    """, {"test_reads_a_real_subclass"}),

    ("a stand-in class declared inside the test", """
        def test_nested_spy():
            class _Spy:
                def attributes(self, *args):
                    return 0

            window = _Spy()
            assert window.attributes("-topmost") == 0
    """, set()),

    ("a stand-in bound by a tuple, an annotation and a with", """
        class _Spy:
            def attributes(self, *args):
                return 0

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def test_tuple_target():
            window, other = _Spy(), _Spy()
            assert window.attributes("-topmost") == other.attributes("-alpha")

        def test_annotated():
            window: _Spy = _Spy()
            assert window.attributes("-topmost") == 0

        def test_with_as():
            with _Spy() as window:
                assert window.attributes("-topmost") == 0
    """, set()),

    ("a read whose attribute name is a variable", """
        def test_variable_attribute(attribute):
            window = tk.Tk()
            assert window.attributes(attribute) == 0
    """, {"test_variable_attribute"}),

    ("a test that maps the window by mark rather than by signature", """
        @pytest.mark.usefixtures("mapped_windows")
        def test_maps_by_mark():
            window = tk.Tk()
            assert float(window.attributes("-alpha")) == 0.0
    """, set()),

    ("a helper that asks the precondition for its callers", """
        def _topmost_now():
            require("-topmost")
            window = tk.Tk()
            return window.attributes("-topmost")

        def test_guarded_inside_the_helper():
            assert _topmost_now() == 0
    """, set()),
]


@pytest.mark.parametrize("label,source,expected", _DETECTOR_CASES,
                         ids=[case[0] for case in _DETECTOR_CASES])
def test_cghm42_a_new_offender_is_detected(label, source, expected):
    """CGH-M4.2 — adversarial (P7): the cases the registry could not see.

    A registry asserts set equality over the tests that already comply, so it
    catches one losing its precondition and cannot catch a new one written
    without any. Each row is a shape the detector was measured against; the
    five after the fourth are shapes the cold passes found it wrong about, in
    both directions -- a missed offender and a false accusation are each a
    reason nobody trusts the guard.
    """
    reads, asks, maps = _scan(textwrap.dedent(source), "synthetic.py")

    flagged = {name for _, name in reads - asks - maps}
    assert flagged == expected, (
        f"{label}: the detector reported {sorted(flagged)}, expected "
        f"{sorted(expected)}")


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
