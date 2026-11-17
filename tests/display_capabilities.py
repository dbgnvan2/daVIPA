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


def usefixtures_names(node) -> set:
    """The fixture names a ``usefixtures`` mark on this node asks for.

    Separate from ``fixture_names`` because the two nodes that carry the same
    mark have no parameters to read: a ``ClassDef``, whose mark pytest
    applies to every method on it, and a ``Module``, where the mark is written
    as ``pytestmark = ...`` and applies to every test in the file. Ten
    test files here already use the module spelling, so it is the house way to
    mark a whole file, and reading only ``decorator_list`` made a module given
    a real window read as needing none (cold pass, 2026-11-16).

    Known gap, surfaced rather than handled: ``usefixtures(*NAMES)`` is a
    ``Starred`` argument whose value cannot be resolved from the syntax, so it
    contributes no names. Nothing in this repo writes it.
    """
    import ast

    if isinstance(node, ast.Module):
        marks = []
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name)
                       and target.id == "pytestmark"
                       for target in statement.targets):
                continue
            value = statement.value
            marks.extend(value.elts
                         if isinstance(value, (ast.List, ast.Tuple))
                         else [value])
    else:
        marks = list(node.decorator_list)

    names = set()
    for mark in marks:
        if not isinstance(mark, ast.Call):
            continue
        if (isinstance(mark.func, ast.Attribute)
                and mark.func.attr == "usefixtures"):
            names |= {a.value for a in mark.args
                      if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return names


def fixture_names(func, enclosing=()) -> set:
    """Every fixture a test function requests, from its AST node.

    Positional, keyword-only and positional-only alike, plus
    ``@pytest.mark.usefixtures("...")`` -- which is how a fixture wanted
    purely for its side effect is usually written -- on the function and on any
    ``ClassDef`` in ``enclosing``. pytest applies a class's mark to every
    method on it, and a method has no way to see that mark from its own node; a
    request the reader cannot see is a window on the screen that no count
    mentions (cold pass, 2026-11-16).

    Shared, because THREE guards ask this question and they have twice
    disagreed. First on 2026-11-11: the read-back detector in
    ``tests/test_display_capabilities.py`` counted the mark as mapping the
    window while the count in ``tests/test_ci_contract.py`` did not, so a new
    on-screen-window test written that way would have been correctly cleared by
    one and invisible to the other -- the drift the count exists to catch.
    Again on 2026-11-16, and this docstring's own "two guards" is why: widening
    this function for the class mark, the detector in that same file was left
    on the narrow call and would have reported a guarded test as unguarded. The
    third reader is the guard in ``tests/test_tk_offscreen.py``. All three now
    pass the enclosing chain.
    """
    import ast

    args = func.args
    names = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
    for node in (func, *enclosing):
        names |= usefixtures_names(node)
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


def _reachable(func, lookup, enclosing=()) -> set:
    """``_markers`` for this function and everything it reaches in ``lookup``.

    A test rarely generates the event itself: it calls a ``_click`` or
    ``_press_target`` helper, or takes a fixture that maps the window. Both are
    followed -- bare calls by name, and requested fixtures by parameter name,
    which is the same thing at the AST level.
    """
    # From ``func`` itself, not from ``lookup[func.name]``: two classes in one
    # module can give a method the same name, and seeding the walk by name
    # looked the subject of the question up and got the OTHER body -- so a test
    # that generates an event and pumps read as needing nothing at all. A
    # silent pass, which is the one direction this guard must not fail in.
    # Demonstrated 2026-11-16; the comment on ``module_functions`` used to
    # claim it could not happen.
    markers = _markers(func)
    seen = set()
    todo = list(bare_calls(func) | fixture_names(func, enclosing))
    while todo:
        name = todo.pop()
        if name in seen or name not in lookup:
            continue
        seen.add(name)
        # EVERY function of that name, not one of them. The lookup is keyed by
        # the bare name a call site gives, and one name can have several
        # bodies; keeping only one discarded the hazardous body whenever the
        # harmless one won, which is a narrowing and so a silent pass. The
        # union is the safe direction: a marker picked up from a body the call
        # could not actually reach is a guard failure naming a test.
        for node in lookup[name]:
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
    """name -> EVERY function of that name in a module, nested ones included.

    Keyed by the bare name a call site gives us, and valued by a tuple, not by
    one node. One name can have several bodies -- 29 of this repo's test files
    already define some name twice -- and keeping one of them dropped the
    others. A caller is expected to union over the tuple, so a collision widens
    the answer instead of narrowing it, because a widened answer is a guard
    failure naming a test while a narrowed one is a hung suite naming nothing.

    This docstring claimed until 2026-11-16 that a collision on a callee "can
    only widen what the caller sees". It was the opposite: the body that lost
    the collision was discarded, markers and all. The claim is recorded here
    because it is the second time this module's comments denied a hazard that
    was reproducible in ten lines, and the comment is what stops the next
    reader looking.
    """
    import ast

    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.setdefault(node.name, []).append(node)
    return {name: tuple(nodes) for name, nodes in found.items()}


def merge_functions(*lookups) -> dict:
    """One ``module_functions`` lookup out of several, keeping every candidate.

    ``{**a, **b}`` would drop ``a``'s bodies for any name ``b`` also defines,
    which is the narrowing ``module_functions`` exists to avoid -- a shared
    fixture in ``conftest.py`` and a same-named helper in the test file would
    leave only one of them reachable.
    """
    merged = {}
    for lookup in lookups:
        for name, nodes in lookup.items():
            merged[name] = merged.get(name, ()) + nodes
    return merged


def test_functions(tree) -> list:
    """``(node, enclosing)`` for every ``test_*`` function in a module.

    ``enclosing`` is the module node followed by any classes the test is
    nested in, outermost first. Both carry fixture requests the function's own
    node cannot show -- a ``usefixtures`` mark on the class, and pytestmark
    at module level -- so a caller passes the whole chain to ``fixture_names``.
    A caller that wants only the class names filters on ``ast.ClassDef``.
    """
    import ast

    found = []

    def walk(node, classes):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, (*classes, child))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("test_"):
                    found.append((child, classes))
                walk(child, classes)
            else:
                walk(child, classes)

    walk(tree, (tree,))
    return found


def needs_a_mapped_window(func, lookup, enclosing=()) -> bool:
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
    markers = _reachable(func, lookup, enclosing)
    return ((_EVENT_CALL in markers and _PUMP_CALL in markers)
            or _ON_PURPOSE in markers)
