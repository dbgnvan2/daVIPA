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


#: The attribute call that posts a real Tk event into the queue.
_EVENT_CALL = "event_generate"

#: The pump that waits for that queue to drain. ``update_idletasks`` is a
#: different attribute and is deliberately not here: it runs idle tasks only,
#: does not wait on the event queue, and so does not deadlock on a withdrawn
#: window -- which is why the ``<Configure>`` tests that use it are safe.
_PUMP_CALL = "update"

#: Passing this to a helper is a test saying outright that it wants a window on
#: the screen, whether or not it then drives events through it.
_ON_PURPOSE = "withdraw=False"


def _markers(func) -> set:
    """What one function body does that bears on needing a mapped window.

    Returns a subset of ``{_EVENT_CALL, _PUMP_CALL, _ON_PURPOSE}``.

    ``update`` counts only when called with no arguments at all. ``d.update(
    {...})`` on a plain dict is the same attribute name and has nothing to do
    with Tk; the no-argument form is what a window pump looks like and what a
    dict update essentially never does. A false positive here is a guard
    failure naming a specific test, not a silent pass, so the narrowing errs in
    the direction that stays visible.
    """
    import ast

    found = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == _EVENT_CALL:
                found.add(_EVENT_CALL)
            elif (node.func.attr == _PUMP_CALL
                    and not node.args and not node.keywords):
                found.add(_PUMP_CALL)
        for keyword in node.keywords:
            if (keyword.arg == "withdraw"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False):
                found.add(_ON_PURPOSE)
    return found


def _reachable(func, lookup) -> set:
    """``_markers`` for this function and everything it reaches in ``lookup``.

    A test rarely generates the event itself: it calls a ``_click`` or
    ``_press_target`` helper, or takes a fixture that maps the window. Both are
    followed -- bare calls by name, and requested fixtures by parameter name,
    which is the same thing at the AST level.
    """
    seen, todo, markers = set(), [func.name], set()
    while todo:
        name = todo.pop()
        if name in seen or name not in lookup:
            continue
        seen.add(name)
        node = lookup[name]
        markers |= _markers(node)
        todo.extend(bare_calls(node))
        todo.extend(fixture_names(node))
    return markers


def bare_calls(func) -> set:
    """The helper call sites in this body, by the name they resolve against.

    Plain ``helper(...)`` calls, and ``self.helper(...)`` -- some of this
    repo's tests are methods on a class, and a helper reached through ``self``
    is the same call site written differently.
    """
    import ast

    names = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"):
            names.add(node.func.attr)
    return names


def module_functions(tree) -> dict:
    """name -> node for every function in a module, nested ones included.

    Keyed by bare name, which is what a call site gives us. Module level wins
    a collision with a method of the same name: resolving a helper to the
    wrong body of the same name can only widen what the caller sees, and a
    widened answer here is a guard failure naming a test, never a silent pass.
    """
    import ast

    nested = {node.name: node for node in ast.walk(tree)
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    top = {node.name: node for node in tree.body
           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return {**nested, **top}


def test_functions(tree) -> list:
    """Every ``test_*`` function in a module, methods on a class included."""
    import ast

    return [node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")]


def needs_a_mapped_window(func, lookup) -> bool:
    """Would this test deadlock, or show a window, on a withdrawn root?

    Two ways, and they are different hazards sharing one fixture:

    - ``event_generate`` **and** a bare ``update()`` somewhere it reaches. The
      pump waits for an event queue that a withdrawn window never drains, so
      the test hangs rather than fails, and a hung suite names no test.
    - ``withdraw=False``, which is a test asking for a real window outright.

    ``event_generate`` on its own is not either of them. Tk delivers a
    generated event straight to the binding, so a test that generates one and
    then asserts on what the handler did -- without pumping -- runs fine
    withdrawn. The file-level predecessor of this check did not make that
    distinction and so failed ``test_scheduler_column_resize.py`` for a
    ``<Configure>`` that cannot hang, while clearing
    ``test_screen_resize_spc.py`` and ``test_unified_panel_design.py``, which
    do the same thing, because the token appeared somewhere else in those
    files (MOD-A2, 2026-11-16).

    Not covered: a helper imported from another test module. ``lookup`` is
    built from the test's own module and ``conftest.py``, which is where this
    repo's shared fixtures live; a helper reached through an import would be
    missed, and the hang would be found by waiting for a timeout.
    """
    markers = _reachable(func, lookup)
    return ((_EVENT_CALL in markers and _PUMP_CALL in markers)
            or _ON_PURPOSE in markers)
