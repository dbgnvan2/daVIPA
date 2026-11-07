"""The two-panel tabs' list: a header row and chip rows, with resizable columns.

Purpose: UPD-M3 — one renderer for the VSP tabs' lists, with the draggable,
         persisted column widths none of them had.
Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m3
Tests:   tests/test_unified_panel_design.py::test_updm31_table_renders_header_and_rows

Five screens each wrote their own version of this: `_render_rows` in
`ape_assignment`, `ape_period_view` and `annual_vision_segments`,
`_render_left_rows` + `_render_right_rows` in `weekly_items`, and three
similar blocks in `vision_segments`. The bodies were the same header frame,
the same `grid_columnconfigure(minsize=…)` calls and the same chip labels,
with the widths already drifting between the copies.

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
    min_width: int = 40
    max_width: int = 600
    chip: bool = True
    resizable: bool = True


# The column set the APE tabs share. The widths are the ones those screens
# used before this module existed (UPD-M4.1 pins them), so no saved layout
# moves on the first launch after the change.
APE_COLUMNS: Tuple[ChipColumn, ...] = (
    ChipColumn("checkbox", "", 34, chip=False, resizable=False),
    ChipColumn("index", "#", 34, chip=False, resizable=False),
    ChipColumn("segment", "Segment", 135, min_width=60),
    ChipColumn("subsegment", "SubSegment", 155, min_width=60),
    ChipColumn("category", "Category", 125, min_width=60),
    ChipColumn("actions", "Actions", 84, chip=False, resizable=False),
)


class ChipTable:
    """Header + chip rows over a `ColumnResizer`.

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

        The resizer's row registry is cleared too: a row frame that has been
        destroyed but is still registered would be walked on every later drag.
        """
        for widget in self.container.winfo_children():
            widget.destroy()
        self.rows = []
        self.header = None
        self.resizer.clear_rows()

    def build_header(self) -> ctk.CTkFrame:
        """Clear the container and render the header, with its drag handles."""
        self.clear()
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
                color = (colors.get(column.key) or "").strip() \
                    or palette[DEFAULT_CHIP_KEY]
                label = ctk.CTkLabel(
                    frame,
                    text=self.resizer.cell_text(column.key, full_text),
                    width=self._chip_width(column.key),
                    fg_color=color,
                    text_color=pick_text_color(color),
                    corner_radius=6,
                    anchor="w",
                )
                registered.append(
                    (column.key, label, full_text, 0, CHIP_INSET))
            else:
                label = ctk.CTkLabel(
                    frame,
                    text=full_text,
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
