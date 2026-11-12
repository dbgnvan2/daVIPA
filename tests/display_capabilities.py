"""Whether the display this run is on honours the window attributes tests read.

Purpose: a test that sets ``-topmost`` or ``-alpha`` on a window that is
         never mapped, and then reads it back, is measuring the display as much
         as the code. On CI, which runs the suite under Xvfb, ``-topmost``
         needs a window manager and there is none, and ``-alpha`` comes back as
         set only once the window has been mapped. Seven tests asserted the
         read-back on a withdrawn window and so failed on CI for months while
         passing here.

         The question this module answers is therefore narrower than "does the
         display support the attribute": it is **does a withdrawn window on
         this display report the attribute back**. That is what the probe does,
         and the distinction is load-bearing — ``tests/test_tk_offscreen.py``
         has two ``-alpha`` read-backs that pass on CI, and what makes them
         different is that they map their window first (they take the
         ``mapped_windows`` fixture). `CIG-A2` is the proper fix for the two
         that skip: map them too, and assert there as well.
Spec:    docs/unused-docs/implementation_plan_2026-11-09_ci_green.md#2-acceptance-criteria--tests (CIG-M1)
Tests:   tests/test_display_capabilities.py

The probe builds a real window and asks the display, rather than reading
``sys.platform``: the question is what this X server or WindowServer does, and
a platform name is a guess at it. It goes through ``tk.call`` rather than
``Toplevel.attributes`` so that it passes the wrapper ``conftest`` installs to
keep test windows invisible — the same reason
``tests/test_timer_session_endings.py`` reads its own assertions that way.

``require`` skips rather than passing, so a capability that disappears on a
developer's machine shows up as a skip with a reason and not as a green run.
"""

import functools

import pytest

#: What Tk reports for a boolean attribute that is on. Tcl's own spellings
#: differ by version and platform, so all three are accepted.
_ON = ("1", "True", "true")

#: attribute -> (value to set, predicate on what comes back). Adding a row here
#: is what makes `require` able to speak about a new attribute.
_PROBES = {
    "-topmost": (True, lambda value: str(value) in _ON),
    "-alpha": (0.0, lambda value: float(value) == 0.0),
}


def _ask_the_display(attribute: str) -> bool:
    import tkinter as tk

    value, accepts = _PROBES[attribute]
    window = None
    try:
        # Inside the try: a machine with no display at all raises here, and
        # the docstring below promises that is a False rather than an error in
        # all four callers. It was outside it until the cold pass, 2026-11-09.
        window = tk.Tk()
        window.withdraw()
        window.tk.call("wm", "attributes", window._w, attribute, value)
        return accepts(window.tk.call("wm", "attributes", window._w, attribute))
    except Exception:
        # A display that refuses the call outright is a display that does not
        # honour the attribute. Returning False rather than raising keeps the
        # failure a skip with a reason instead of an error in every caller.
        return False
    finally:
        if window is not None:
            window.destroy()


def fixture_names(func) -> set:
    """Every fixture a test function requests, from its AST node.

    Positional, keyword-only and positional-only alike, plus
    ``@pytest.mark.usefixtures("...")`` -- which is how a fixture wanted purely
    for its side effect is usually written.

    Shared, because two guards ask this question and they disagreed: the
    read-back detector in ``tests/test_display_capabilities.py`` counted the
    mark as mapping the window while the count in ``tests/test_ci_contract.py``
    did not, so a new on-screen-window test written that way would have been
    correctly cleared by one and invisible to the other -- the drift the count
    exists to catch (cold pass, 2026-11-11).
    """
    import ast

    args = func.args
    names = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
    for decorator in func.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if (isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "usefixtures"):
            names |= {a.value for a in decorator.args
                      if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return names


@functools.lru_cache(maxsize=None)
def honours(attribute: str) -> bool:
    """Does a withdrawn window here report ``attribute`` back? Asked once.

    Cached because it builds and destroys a window, and four tests ask. A
    display with no window at all answers False rather than raising, so a
    caller gets a skip with a reason.
    """
    if attribute not in _PROBES:
        raise KeyError(
            f"no probe for {attribute!r}; add it to _PROBES with the value to "
            "set and how to read the answer")
    return _ask_the_display(attribute)


def require(attribute: str) -> None:
    """Skip the calling test, with a reason, unless the display honours it."""
    if not honours(attribute):
        pytest.skip(
            f"a withdrawn window here does not report {attribute} back, so "
            "reading it back measures the display rather than the code "
            "(CI's Xvfb has no window manager for -topmost, and reports "
            "-alpha only once a window is mapped)")
