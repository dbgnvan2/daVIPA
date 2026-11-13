"""The Segment / SubSegment / Category filter triple a list screen offers.

Purpose: UPD-M6.4 — one owner for the three filter combos, their "All"
         sentinel, the option lists they offer, and the predicate that decides
         whether a row survives them.
Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m6
Tests:   tests/test_unified_panel_design.py::test_updm64_filters_narrow_the_tactic_list

Five files already declare their own `segment_filter_var` /
`subsegment_filter_var` / `category_filter_var` triple with the same "All"
sentinel: `ape_assignment`, `ape_period_view`, `weekly_items`, `drag_schedule`
and `item_editor_weekly_tactic_dialog`. APE Week Actions is the sixth place to
need it, and writing a sixth copy is the thing UPD-D1 exists to prevent, so the
rule moved here as it was added. The five existing copies are **not** changed
by UPD-M6 — a feature change does not silently sweep adjacent code — and are
recorded as UPD-A9 in `BACKLOG.md`.

The screen keeps what is its own: which rows it filters, where the combos sit
in its header, and what it says when a filter hides everything. This module
knows nothing beyond three names per row.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence, Tuple

import customtkinter as ctk

from ..theme import combo_box_style

# What "no filter" is called in the combo and stored in the variable. A row is
# never compared against it.
ALL = "All"

# How deep the filter row is. One combo box high, which is what the row holds
# on every tab that has filters. Annual Plan Elements has none and grids an
# empty frame of this height instead, so the body of all six tabs starts at
# the same y (UPD-F2.5) -- an empty CTkFrame asks for 200px, so it has to be
# told.
FILTER_ROW_HEIGHT = 28

# What a row with no name in that part of its lineage renders and filters as.
# A dash is never offered as a filter value: picking it would mean "the rows
# that are missing a subsegment", which no screen offers and no user asked for.
MISSING = "-"


def weekly_tactic_parts(row: Dict[str, Any]) -> Tuple[str, str, str]:
    """The lineage triple of a Weekly Tactic row, as the VSP query returns it.

    A Weekly Tactic carries its Annual Plan Element's lineage under `ape_*`
    keys, not the `*_name` keys an Annual Plan Element row itself uses. `who`
    is the segment of last resort, which is where a tactic created before the
    APE link existed still carries it.
    """
    segment = (row.get("ape_segment_name") or row.get("who") or "").strip()
    subsegment = (row.get("ape_subsegment_name") or "").strip()
    category = (row.get("ape_category_name") or "").strip()
    return segment or MISSING, subsegment or MISSING, category or MISSING


def annual_plan_element_parts(row: Dict[str, Any]) -> Tuple[str, str, str]:
    """The lineage triple of an Annual Plan Element row.

    No second fall-back after the strip, unlike `weekly_tactic_parts`: a name
    of nothing but spaces reads as empty here and always has. It is not
    offered as a filter value and matches no filter either way, so the two
    readers differ only in what such a row renders, and changing that is not
    UPD-M6's to do.
    """
    return (
        (row.get("segment_name") or MISSING).strip(),
        (row.get("subsegment_name") or MISSING).strip(),
        (row.get("category_name") or MISSING).strip(),
    )


class LineageFilters:
    """Three combos over one `parts` reader.

    `parts` maps a row to its (segment, subsegment, category) names, so one
    instance serves whichever row shape its screen lists.
    """

    def __init__(self, parts: Callable[[Dict[str, Any]], Tuple[str, str, str]]):
        self.parts = parts
        self.segment_var = ctk.StringVar(value=ALL)
        self.subsegment_var = ctk.StringVar(value=ALL)
        self.category_var = ctk.StringVar(value=ALL)
        self.segment_combo: Any = None
        self.subsegment_combo: Any = None
        self.category_combo: Any = None

    # ------------------------------------------------------------------- build

    def build_combos(self, parent, start_column: int, on_change: Callable[[], None],
                     width: int = 150, row: int = 1,
                     pady: Tuple[int, int] = (0, 8)) -> int:
        """Grid `Segment: [ ] SubSegment: [ ] Category: [ ]` and return the next free column.

        Six widgets go in, a label and a combo per filter, starting at
        `start_column`. The caller keeps the returned column so whatever it
        grids next does not land on top of the last combo.
        """
        column = start_column
        pairs = (
            ("Segment:", self.segment_var, "segment_combo", (10, 4)),
            ("SubSegment:", self.subsegment_var, "subsegment_combo", (8, 4)),
            ("Category:", self.category_var, "category_combo", (8, 4)),
        )
        for text, variable, attr, label_padx in pairs:
            ctk.CTkLabel(parent, text=text).grid(
                row=row, column=column, padx=label_padx, pady=pady, sticky="e")
            combo = ctk.CTkComboBox(
                parent,
                width=width,
                values=[ALL],
                variable=variable,
                command=lambda _value: on_change(),
                **combo_box_style(),
            )
            combo.grid(row=row, column=column + 1, padx=4, pady=pady, sticky="w")
            setattr(self, attr, combo)
            column += 2
        return column

    # ----------------------------------------------------------------- options

    def refresh_options(self, rows: Sequence[Dict[str, Any]]) -> None:
        """Offer only the values the given rows actually have.

        A selection that is no longer among them falls back to `ALL` rather
        than staying set to a value nothing can match, which would leave the
        panel empty with a filter the combo no longer lists (P2).
        """
        triples = [self.parts(row) for row in rows]
        for position, (variable, attr) in enumerate((
            (self.segment_var, "segment_combo"),
            (self.subsegment_var, "subsegment_combo"),
            (self.category_var, "category_combo"),
        )):
            values = [ALL] + sorted(
                {
                    triple[position] for triple in triples
                    if triple[position] and triple[position] != MISSING
                },
                key=str.lower,
            )
            current = variable.get().strip() or ALL
            if current not in values:
                variable.set(ALL)
            combo = getattr(self, attr)
            if combo is not None:
                combo.configure(values=values)

    # --------------------------------------------------------------- filtering

    def selections(self) -> Tuple[str, str, str]:
        return (
            self.segment_var.get().strip(),
            self.subsegment_var.get().strip(),
            self.category_var.get().strip(),
        )

    def is_filtering(self) -> bool:
        """True when at least one combo is set to something other than `ALL`."""
        return any(
            value and value != ALL for value in self.selections()
        )

    def matches(self, row: Dict[str, Any]) -> bool:
        names = self.parts(row)
        for name, selected in zip(names, self.selections()):
            if selected and selected != ALL and name != selected:
                return False
        return True

    def filtered(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [row for row in rows if self.matches(row)]

    def describe(self) -> str:
        """The active filters, for a message that has to say what was applied.

        Empty when nothing is filtering, so a caller can print it without
        checking first.
        """
        parts = [
            f"{label} {value}"
            for label, value in zip(
                ("Segment", "Sub", "Cat"), self.selections())
            if value and value != ALL
        ]
        return ", ".join(parts)

    def reset(self) -> None:
        for variable in (self.segment_var, self.subsegment_var, self.category_var):
            variable.set(ALL)
