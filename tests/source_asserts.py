"""AST helpers for the few checks that must inspect source.

Purpose: make an unavoidable source-text check unable to match prose.
Spec:    docs/implementation_plan_2026-08-19_backlog_clearance.md
Tests:   tests/test_source_asserts.py

A behavioural assertion is always preferred — call the thing, check the result
or the rows it wrote. Some checks cannot be: proving a UI method still reports
errors needs a fully built CustomTkinter screen with entry widgets populated,
which is a heavier and more brittle test than the one it replaces.

Where a source check is genuinely the only option, it must not be a substring
match. That is the shape that produced a guard dead for months:
``test_enhanced_deletion_protection`` greped ``delete_segment``'s source for
``vision_count``, a name removed when the return shape changed, and reported
green throughout. The same shape passes on a *comment* that happens to contain
the word, and fails on a rename that changed nothing that matters.

These helpers parse instead. ``calls_attribute(fn, "messagebox", "showerror")``
is true only for a real call; a docstring saying "we call messagebox.showerror"
does not satisfy it, and neither does a variable of that name.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from typing import Callable


def _tree(func: Callable) -> ast.AST:
    """Parse a function's own source, dedented so a method parses standalone."""
    return ast.parse(textwrap.dedent(inspect.getsource(func)))


def calls_attribute(func: Callable, obj: str, attr: str) -> bool:
    """Does ``func`` contain a real call to ``obj.attr(...)``?

    Matches the call, not the text: a docstring mentioning it, or a string
    literal containing it, does not count.
    """
    for node in ast.walk(_tree(func)):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if (
            isinstance(target, ast.Attribute)
            and target.attr == attr
            and isinstance(target.value, ast.Name)
            and target.value.id == obj
        ):
            return True
    return False


def calls_any_attribute(func: Callable, obj: str, attrs: tuple[str, ...]) -> bool:
    """``calls_attribute`` for a set of acceptable method names."""
    return any(calls_attribute(func, obj, attr) for attr in attrs)


def references_name(func: Callable, name: str) -> bool:
    """Is ``name`` used as a real identifier in ``func`` — not in a string?

    Covers a bare name (``CTkMessageBox(...)``) and an attribute access
    (``ctk.CTkMessageBox``), which is how the same class arrives by two routes.
    """
    for node in ast.walk(_tree(func)):
        if isinstance(node, ast.Name) and node.id == name:
            return True
        if isinstance(node, ast.Attribute) and node.attr == name:
            return True
    return False


def assigns_self_attribute(func: Callable, attr: str) -> bool:
    """Does ``func`` assign ``self.<attr>``?

    ``"selected_segments" in source`` was true of a comment, a docstring, or a
    method that merely *read* the attribute. This is true only of a write, which
    is what "the filter has something to write to" actually requires.
    """
    def _is_self_attr(target: ast.AST) -> bool:
        return (
            isinstance(target, ast.Attribute)
            and target.attr == attr
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        )

    for node in ast.walk(_tree(func)):
        if isinstance(node, ast.Assign):
            if any(_is_self_attr(t) for t in node.targets):
                return True
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            if _is_self_attr(node.target):
                return True
        elif isinstance(node, (ast.For, ast.comprehension)):
            if _is_self_attr(getattr(node, "target", None)):
                return True
    return False


def calls_method_on_name(func: Callable, name: str, method: str) -> bool:
    """Does ``func`` call ``<name>.<method>(...)`` on a local or parameter?

    Distinct from ``calls_attribute`` only in intent — kept separate so a
    caller's assertion reads as what it means.
    """
    return calls_attribute(func, name, method)


def local_assignments(func: Callable, name: str) -> "list[ast.AST]":
    """Every value assigned to the local ``name`` in ``func``, in source order.

    Used where the *shape* of an assignment is the contract and a behavioural
    check cannot reach it: PLC-M4.7 needs "``bg_color`` is assigned once, from
    ``fill.fill``", which proves the five list screens no longer each decide a
    row fill for themselves. Returns the value nodes so the caller can assert
    an exact count -- never a floor, which would hide the narrowing the guard
    exists to catch.
    """
    found = []
    for node in ast.walk(_tree(func)):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    found.append(node.value)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            target = node.target
            if isinstance(target, ast.Name) and target.id == name:
                found.append(node.value)
    return found


def count_calls(func: Callable, name: str) -> int:
    """How many times ``func`` calls the bare function ``name(...)``.

    A call, not a mention: a docstring naming the function, a string literal
    and an import of it do not count.
    """
    return sum(
        1
        for node in ast.walk(_tree(func))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == name
    )


def assigns_attribute_of(value: ast.AST, owner: str, attr: str) -> bool:
    """Is ``value`` exactly the expression ``<owner>.<attr>``?"""
    return (
        isinstance(value, ast.Attribute)
        and value.attr == attr
        and isinstance(value.value, ast.Name)
        and value.value.id == owner
    )


def call_string_args(func: Callable, owner: str, attr: str) -> "list[str]":
    """Every string literal passed as the first argument to ``owner.attr(...)``.

    ``owner`` may be dotted, so ``call_string_args(f, "self.tabview", "add")``
    collects the tab names in ``self.tabview.add("Appearance")`` and friends.
    ``calls_attribute`` cannot be used for this: its ``obj`` must be a bare
    name, and it answers whether the call happens, not what it was given.

    Matches calls, so a comment or a docstring containing the same words
    contributes nothing -- which is the point. A substring check over
    ``inspect.getsource`` is satisfied by the comment above the call.
    """
    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = dotted(node.value)
            return f"{base}.{node.attr}" if base else ""
        return ""

    found: "list[str]" = []
    for node in ast.walk(_tree(func)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        target = node.func
        if not isinstance(target, ast.Attribute) or target.attr != attr:
            continue
        if dotted(target.value) != owner:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.append(first.value)
    return found


def call_string_args(func: Callable, owner: str, attr: str) -> "list[str]":
    """Every string literal passed as the first argument to ``owner.attr(...)``.

    ``owner`` may be dotted, so ``call_string_args(f, "self.tabview", "add")``
    collects the tab names in ``self.tabview.add("Appearance")`` and friends.
    ``calls_attribute`` cannot be used for this: its ``obj`` must be a bare
    name, and it answers whether the call happens, not what it was given.

    Matches calls, so a comment or a docstring containing the same words
    contributes nothing -- which is the point. A substring check over
    ``inspect.getsource`` is satisfied by the comment above the call.
    """
    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = dotted(node.value)
            return f"{base}.{node.attr}" if base else ""
        return ""

    found: "list[str]" = []
    for node in ast.walk(_tree(func)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        target = node.func
        if not isinstance(target, ast.Attribute) or target.attr != attr:
            continue
        if dotted(target.value) != owner:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.append(first.value)
    return found


def iterates_mapping(func: Callable, name: str) -> bool:
    """Does ``func`` call ``<name>.items()`` or ``<name>.values()``?

    The Settings screen's contract with ``delete_segment`` is that the second
    return value is a mapping. Asserting the *call* rather than the substring
    means a comment explaining the mapping does not satisfy it.
    """
    return calls_any_attribute(func, name, ("items", "values"))
