"""The AST helpers must be able to say no — and must not say yes to prose.

Purpose: prove tests/source_asserts.py is not a no-op that passes on anything.
Spec:    docs/implementation_plan_2026-08-19_backlog_clearance.md
Tests:   this file

Every converted assertion in the suite reads ``assert calls_attribute(...)``.
A helper that always returned True would make all of them vacuous, and one that
always returned False would fail loudly (so it is the True direction that
matters). Both directions are asserted below.

The positive cases are deliberately hostile: a docstring naming the call, a
string literal containing it, a variable of the same name, and a read where a
write is required. Each is exactly what the substring checks these helpers
replaced would have accepted.
"""

from __future__ import annotations

import pytest

from tests.source_asserts import (
    assigns_attribute_of,
    assigns_self_attribute,
    call_string_args,
    calls_any_attribute,
    calls_attribute,
    count_calls,
    iterates_mapping,
    local_assignments,
    references_name,
)


# --- subjects -------------------------------------------------------------
# Module-level so inspect.getsource sees a real function, and indented inside
# a class where the helpers must dedent before parsing.

class _Subject:
    def assigns_once_from_an_attribute(self):
        """Mentions bg_color = palette["x"] in prose, and does not do it."""
        fill = helper()
        bg_color = fill.fill
        return bg_color

    def assigns_twice_with_a_branch(self):
        fill = helper()
        if fill:
            bg_color = palette["critical_tint"]
        else:
            bg_color = None
        return bg_color

    def calls_a_bare_function_twice(self):
        """A docstring naming row_fill does not count as a call."""
        name = "row_fill"
        row_fill(1)
        row_fill(2)
        return name

    def calls_it(self):
        messagebox.showerror("Title", "Body")

    def only_mentions_it(self):
        """We used to call messagebox.showerror here."""
        note = "messagebox.showerror"
        return note

    def calls_a_different_method(self):
        messagebox.showinfo("Title", "Body")

    def assigns_the_attribute(self):
        self.selected_segments = []

    def only_reads_the_attribute(self):
        return self.selected_segments

    def mentions_the_attribute_in_prose(self):
        """Sets selected_segments, honestly."""
        return "selected_segments"

    def uses_the_class(self):
        return CTkMessageBox(self)

    def uses_the_class_by_attribute(self):
        return ctk.CTkMessageBox(self)

    def only_names_it_in_a_string(self):
        """CTkMessageBox must never come back."""
        return "CTkMessageBox"

    def iterates_the_mapping(self):
        for key, value in counts.items():
            print(key, value)

    def sums_the_mapping(self):
        return sum(counts.values())

    def treats_it_as_a_scalar(self):
        return counts + 1

    def augments_the_attribute(self):
        self.selected_segments += ["x"]


# --- calls_attribute ------------------------------------------------------

def test_calls_attribute_finds_a_real_call():
    assert calls_attribute(_Subject.calls_it, "messagebox", "showerror")


def test_calls_attribute_ignores_a_docstring_and_a_string_literal():
    """The substring check this replaced accepted both."""
    assert not calls_attribute(_Subject.only_mentions_it, "messagebox", "showerror")


def test_calls_attribute_distinguishes_methods():
    assert not calls_attribute(_Subject.calls_a_different_method, "messagebox", "showerror")


def test_calls_any_attribute_accepts_either_method():
    assert calls_any_attribute(
        _Subject.calls_a_different_method, "messagebox", ("showerror", "showinfo")
    )
    assert not calls_any_attribute(
        _Subject.only_mentions_it, "messagebox", ("showerror", "showinfo")
    )


# --- references_name ------------------------------------------------------

def test_references_name_finds_both_call_routes():
    assert references_name(_Subject.uses_the_class, "CTkMessageBox")
    assert references_name(_Subject.uses_the_class_by_attribute, "CTkMessageBox")


def test_references_name_ignores_strings_and_docstrings():
    """This is the one asserted NEGATIVELY in the suite, so a helper that
    always returned True would make that assertion impossible to satisfy —
    but one that always returned False would make it vacuous."""
    assert not references_name(_Subject.only_names_it_in_a_string, "CTkMessageBox")


# --- assigns_self_attribute -----------------------------------------------

def test_assigns_self_attribute_requires_a_write():
    assert assigns_self_attribute(_Subject.assigns_the_attribute, "selected_segments")
    assert assigns_self_attribute(_Subject.augments_the_attribute, "selected_segments")


def test_assigns_self_attribute_rejects_a_read_or_a_mention():
    """`"selected_segments" in source` accepted all three of these."""
    assert not assigns_self_attribute(_Subject.only_reads_the_attribute, "selected_segments")
    assert not assigns_self_attribute(
        _Subject.mentions_the_attribute_in_prose, "selected_segments"
    )


# --- iterates_mapping -----------------------------------------------------

def test_iterates_mapping_accepts_items_and_values():
    assert iterates_mapping(_Subject.iterates_the_mapping, "counts")
    assert iterates_mapping(_Subject.sums_the_mapping, "counts")


def test_iterates_mapping_rejects_scalar_use():
    """The regression it guards: delete_segment going back to a scalar."""
    assert not iterates_mapping(_Subject.treats_it_as_a_scalar, "counts")


# --- the helpers must work on real, indented methods ----------------------

def test_the_helpers_parse_a_real_method_from_the_app():
    """Adversarial: these run against source dedented out of a class body.

    A helper that raised IndentationError on a real method would take every
    converted assertion down with it — loudly, but only once someone ran it.
    """
    from src.getmoredone.screens.vps_editors import TLVisionEditorDialog

    assert calls_any_attribute(
        TLVisionEditorDialog.save_vision, "messagebox", ("showerror", "showinfo")
    ), "the helper cannot see a call it should see in real app source"


def test_the_helpers_reject_a_name_absent_from_real_source():
    """The other direction, on the same real method."""
    from src.getmoredone.screens.vps_editors import TLVisionEditorDialog

    assert not references_name(TLVisionEditorDialog.save_vision, "ThisNameIsNotThere")


# --- local_assignments / count_calls / assigns_attribute_of ---------------

def test_local_assignments_counts_each_write_and_ignores_prose():
    """One write, from an attribute — and the docstring naming another is not one."""
    values = local_assignments(_Subject.assigns_once_from_an_attribute, "bg_color")
    assert len(values) == 1
    assert assigns_attribute_of(values[0], "fill", "fill")


def test_local_assignments_sees_every_branch():
    """A branchy assignment is two writes, not one — the shape PLC-M4.7 forbids."""
    values = local_assignments(_Subject.assigns_twice_with_a_branch, "bg_color")
    assert len(values) == 2
    assert not any(assigns_attribute_of(v, "fill", "fill") for v in values)


def test_local_assignments_says_no_to_a_name_never_assigned():
    assert local_assignments(_Subject.assigns_once_from_an_attribute, "row_text") == []


def test_count_calls_counts_calls_not_mentions():
    assert count_calls(_Subject.calls_a_bare_function_twice, "row_fill") == 2
    assert count_calls(_Subject.assigns_once_from_an_attribute, "row_fill") == 0


def test_assigns_attribute_of_rejects_a_different_owner_or_attribute():
    value = local_assignments(_Subject.assigns_once_from_an_attribute, "bg_color")[0]
    assert not assigns_attribute_of(value, "other", "fill")
    assert not assigns_attribute_of(value, "fill", "text_color")


class _Tabbed:
    """A stand-in for a screen that builds a tab strip."""

    def create_tabs(self):
        # Tab 1: Alpha. A comment naming Alpha and Omega on purpose, so a
        # substring check over the source cannot pass for the real calls.
        self.tabview.add("Alpha")
        self.tabview.add("Beta")
        self.other.add("Gamma")
        self.tabview.insert("Delta")
        self.tabview.add(SOME_NAME)


SOME_NAME = "Epsilon"


def test_call_string_args_collects_only_that_owners_calls():
    names = call_string_args(_Tabbed.create_tabs, "self.tabview", "add")
    assert names == ["Alpha", "Beta"]


def test_call_string_args_ignores_comments_other_owners_and_non_literals():
    names = call_string_args(_Tabbed.create_tabs, "self.tabview", "add")
    # "Omega" appears only in a comment, "Gamma" is another owner, "Delta" is
    # another method, "Epsilon" is behind a name rather than a literal.
    for absent in ("Omega", "Gamma", "Delta", "Epsilon"):
        assert absent not in names
    assert call_string_args(_Tabbed.create_tabs, "self.missing", "add") == []
