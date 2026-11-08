"""The two-panel tabs' list: a header row and chip rows, with resizable columns.

Purpose: UPD-M3 — one renderer for the VSP tabs' lists, with the draggable,
         persisted column widths none of them had.
Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m3
Tests:   tests/test_unified_panel_design.py::test_updm31_table_renders_header_and_rows

Adopted at UPD-M4 by `ape_assignment`, `ape_period_view` and
`annual_vision_segments` — six panels, two each. Their `_render_rows` methods
were the same header frame, the same `grid_columnconfigure(minsize=…)` calls
and the same chip labels three times over, and are now one call to
`build_header()` and one `add_row()` per row.

Adopted at UPD-M5 by `weekly_items` (both panels) and at UPD-M6 by
`week_actions`'s left panel, which replaced a stack of one `CTkButton` per
Weekly Tactic. Nine panels in all. `vision_segments`'s three similar blocks
are left alone, per UPD-A1 and D8.

The split of responsibility is deliberate: this module owns the header, the
row frames, the chips and the widths, and knows nothing about Annual Plan
Elements, Weekly Tactics, checkboxes or Delete buttons. The screen owns what
goes in the checkbox and Actions columns, and grids it at the index
`grid_col()` gives it. That is what lets one table serve a left panel that is
selectable and a right panel that is not.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import customtkinter as ctk

from ..color_contrast import pick_text_color
from ..theme import semantic_colors
from .column_resize import ColumnResizer, ColumnSpec

# How far inside its column a chip sits. The pill is the column width less
# this, so two chips in adjacent columns do not touch.
CHIP_INSET = 12

# A chip whose colour is empty falls back to the panel's own surface, so a row
# with no lineage colour still reads as a row rather than as a hole.
DEFAULT_CHIP_KEY = "surface_subtle"


def show_list_or_message(list_frame, message, empty: bool) -> None:
    """Show a panel's list or its empty-state label, never both.

    Purpose: UPD-M6 — one owner for the swap. Both widgets are gridded into
             the same cell, and two widgets in one Tk cell both stay mapped
             with the later one drawn on top, so "hide the list" has to mean
             `grid_remove`, not "grid the label over it". That reads correct on
             screen while the panel holds both.
    Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m6
    Tests:   tests/test_unified_panel_design.py::test_updm65_an_empty_filter_result_says_what_it_hid
    """
    if empty:
        list_frame.grid_remove()
        message.grid()
    else:
        message.grid_remove()
        list_frame.grid()


@dataclass(frozen=True)
class ChipColumn:
    """One column of the table.

    key:          stable id; also the persistence sub-key and the cell tag.
    heading:      header text. Empty for the checkbox column.
    chip:         True draws a solid-colour pill, False a plain label.
    resizable:    False means a fixed width and no drag handle — the checkbox
                  and Actions columns, which have nothing to widen.
    """

    key: str
    heading: str
    default_width: int
    # A width below this is refused. It must not be above `default_width`:
    # the resizer clamps the stored width into range, so a column declared
    # 34 wide with the default minimum of 40 renders at 40 and nothing says
    # so. Pinned for every shipped set by
    # ::test_updm31_every_shipped_column_declares_a_width_it_can_have.
    min_width: int = 40
    max_width: int = 600
    chip: bool = True
    resizable: bool = True


# The column sets the two-panel tabs use. The widths are the ones those
# screens used before this module existed (UPD-M4.1 pins them), so no saved
# layout moves on the first launch after the change.
#
# One set per *panel*, not per tab: a left panel is selectable and has no
# Actions column, a right panel has Actions and no checkbox. A column's grid
# index is its position in the set, so a single set holding both would put
# every column of every panel one place to the right of where it is today.
_INDEX_AND_CHIPS: Tuple[ChipColumn, ...] = (
    ChipColumn("index", "#", 34, min_width=34, chip=False, resizable=False),
    ChipColumn("segment", "Segment", 135, min_width=60),
    ChipColumn("subsegment", "SubSegment", 155, min_width=60),
    ChipColumn("category", "Category", 125, min_width=60),
)

# Left panel: a blank cell over the checkboxes, then the four names.
APE_LEFT_COLUMNS: Tuple[ChipColumn, ...] = (
    ChipColumn("checkbox", "", 34, min_width=34, chip=False, resizable=False),
) + _INDEX_AND_CHIPS

# Right panel on the two APE tabs: one Delete button, 84px.
APE_RIGHT_COLUMNS: Tuple[ChipColumn, ...] = _INDEX_AND_CHIPS + (
    ChipColumn("actions", "Actions", 84, chip=False, resizable=False),
)

# Right panel on Annual Vision Segments: Edit *and* Delete, so 140px. This is
# the only column width that differs across the three screens.
ANNUAL_RIGHT_COLUMNS: Tuple[ChipColumn, ...] = _INDEX_AND_CHIPS + (
    ChipColumn("actions", "Actions", 140, chip=False, resizable=False),
)

# Left panel on APE Week Actions (UPD-M6.2). The only panel in the hub whose
# rows are Weekly Tactics picked by name, so it carries a Title column the
# other panels have no use for: the three chips say which lineage a tactic
# belongs to, and the title says which tactic it is. No checkbox (nothing is
# ticked here) and no Actions (clicking the row is the interaction, D6).
WEEK_ACTIONS_LEFT_COLUMNS: Tuple[ChipColumn, ...] = (
    ChipColumn("index", "#", 34, min_width=34, chip=False, resizable=False),
    ChipColumn("title", "Weekly Tactic", 220, min_width=80, chip=False),
    ChipColumn("segment", "Segment", 135, min_width=60),
    ChipColumn("subsegment", "SubSegment", 155, min_width=60),
    ChipColumn("category", "Category", 125, min_width=60),
)


class ChipTable:
    """Header + chip rows over a `ColumnResizer`.

    **The table owns its container outright.** `clear()` destroys every child
    of it, so a screen must not grid anything of its own into the frame it
    hands over -- an empty-state label belongs in a sibling frame. All five
    adopting panels satisfy this; it is stated because nothing enforces it
    (AWA-S6 a).

    Purpose: UPD-M3.1 — render one panel's list and own its column widths.
    Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m3
    Tests:   tests/test_unified_panel_design.py::test_updm32_every_resizable_column_has_a_handle
    """

    def __init__(self, container, settings, prefix: str,
                 columns: Sequence[ChipColumn]):
        self.container = container
        self.settings = settings
        self.prefix = prefix
        self.columns: List[ChipColumn] = list(columns)
        self._by_key = {c.key: c for c in self.columns}
        self.header: Optional[ctk.CTkFrame] = None
        # (frame, {key: label}) per rendered row, in render order.
        self.rows: List[Tuple[ctk.CTkFrame, Dict[str, ctk.CTkLabel]]] = []

        self.resizer = ColumnResizer(
            owner=container,
            settings=settings,
            prefix=prefix,
            specs=[
                ColumnSpec(
                    key=c.key,
                    grid_col=idx,
                    default_width=c.default_width,
                    min_width=c.min_width,
                    max_width=c.max_width,
                    resizable=c.resizable,
                )
                for idx, c in enumerate(self.columns)
            ],
            text_pad=" ",
            set_cell_width=True,
        )

    # ------------------------------------------------------------------ layout

    def grid_col(self, key: str) -> int:
        """The grid column index a screen grids its own widget into."""
        return self.resizer.specs[key].grid_col

    def width(self, key: str) -> int:
        return self.resizer.width(key)

    def _chip_width(self, key: str) -> int:
        return max(1, self.resizer.width(key) - CHIP_INSET)

    # ------------------------------------------------------------------ header

    def clear(self) -> None:
        """Destroy every rendered widget and forget the rows.

        The resizer's registries are cleared too: a row frame or a header
        that has been destroyed but is still registered would be walked on
        every later drag.
        """
        for widget in self.container.winfo_children():
            widget.destroy()
        self.rows = []
        self.header = None
        self.resizer.clear_rows()
        self.resizer.clear_header()

    def build_header(self) -> ctk.CTkFrame:
        """Clear the container and render the header, with its drag handles."""
        self.clear()
        # The header and every row are gridded sticky="ew" in column 0, which
        # does nothing unless that column can stretch. The adopting screens
        # all set this on their scroll frames already; the table sets it so a
        # screen that does not is not silently left with a ragged panel
        # (AWA-S6 c).
        self.container.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(
            self.container, fg_color=semantic_colors()["surface_subtle"])
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 4))
        self.resizer.apply_grid(header)

        labels: Dict[str, ctk.CTkLabel] = {}
        for column in self.columns:
            anchor = "e" if column.key == "actions" else "w"
            label = ctk.CTkLabel(
                header,
                text=column.heading,
                width=self.resizer.width(column.key),
                font=ctk.CTkFont(weight="bold"),
                anchor=anchor,
            )
            label.grid(row=0, column=self.grid_col(column.key), padx=5, pady=5,
                       sticky=anchor)
            labels[column.key] = label

        self.resizer.build_dividers(header, labels)
        self.header = header
        return header

    # -------------------------------------------------------------------- rows

    def add_row(self, values: Dict[str, Optional[str]],
                colors: Optional[Dict[str, str]] = None,
                **frame_kwargs) -> Tuple[ctk.CTkFrame, Dict[str, ctk.CTkLabel]]:
        """Render one row and return its frame and its cells.

        `values` and `colors` are keyed by column key. A column missing from
        `values` gets no widget, which is how the screen keeps the checkbox and
        Actions columns for itself. A missing or empty colour falls back to the
        panel surface rather than raising — rows with no subsegment or category
        exist in the live database (UPD-M3.7).
        """
        if self.header is None:
            raise ValueError(
                "ChipTable.add_row before build_header: the first row would be "
                "gridded at row 1 and row 0 left empty (AWA-S6 d)")
        if not any(column.key in values for column in self.columns):
            raise ValueError(
                "ChipTable.add_row with no known column key: the row would be "
                f"a zero-cell, zero-height frame. Got {sorted(values)}, "
                f"columns {[c.key for c in self.columns]} (AWA-S6 e)")
        colors = colors or {}
        palette = semantic_colors()
        frame = ctk.CTkFrame(self.container, **frame_kwargs)
        frame.grid(row=len(self.rows) + 1, column=0, sticky="ew", padx=4, pady=2)

        cells: Dict[str, ctk.CTkLabel] = {}
        registered = []
        for column in self.columns:
            if column.key not in values:
                continue
            full_text = values.get(column.key) or ""
            if column.chip:
                lineage = (colors.get(column.key) or "").strip()
                if lineage:
                    chip_colors = {
                        "fg_color": lineage,
                        "text_color": pick_text_color(lineage),
                    }
                else:
                    # No lineage colour: the pill is the panel's own surface,
                    # and the theme's default label colour is readable on it
                    # by construction. Measuring it is what breaks — the
                    # fallback token is a *named* Tk colour on 7 of the 10
                    # themes ("gray16" in dark mode), which pick_text_color
                    # cannot parse, so it returned black: black text on a
                    # near-black pill, on exactly the rows this fallback is
                    # for.
                    chip_colors = {"fg_color": palette[DEFAULT_CHIP_KEY]}
                label = ctk.CTkLabel(
                    frame,
                    text=self.resizer.cell_text(
                        column.key, full_text, width_delta=CHIP_INSET),
                    width=self._chip_width(column.key),
                    corner_radius=6,
                    anchor="w",
                    **chip_colors,
                )
                registered.append(
                    (column.key, label, full_text, 0, CHIP_INSET))
            else:
                # A resizable plain column is clamped to its width here, the
                # same way the resizer clamps it on a drag. Without this the
                # first render is the one width at which the text can overrun
                # its column -- it would be cut to fit the moment the handle
                # was touched and not before, which on a Title column is a
                # panel that opens wrong and corrects itself when dragged
                # (UPD-M6.2). A fixed-width column keeps its raw text: `#` and
                # `Actions` cannot overrun by construction, and the resizer
                # never re-clamps a column with no handle, so clamping them
                # here would be the only place the pad appeared.
                text = (
                    self.resizer.cell_text(column.key, full_text)
                    if column.resizable else full_text
                )
                label = ctk.CTkLabel(
                    frame,
                    text=text,
                    width=self.resizer.width(column.key),
                    anchor="w",
                )
                registered.append((column.key, label, full_text, 0, 0))
            label.grid(row=0, column=self.grid_col(column.key), padx=5, pady=5,
                       sticky="w")
            cells[column.key] = label

        self.resizer.register_row(frame, registered)
        self.rows.append((frame, cells))
        return frame, cells
