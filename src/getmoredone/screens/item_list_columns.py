"""The column layout shared by the four item lists.

Purpose: LSR-M1/M2/M3/M6 -- Today, Upcoming, All Items and Hierarchical give
         their stretching columns (Title, SubSegment, Category, Who) to one
         ``ColumnResizer`` each, hold their fixed columns at one width in the
         header and every row, and refit the stretching columns whenever the
         list area changes width.
Spec:    docs/unused-docs/implementation_plan_2026-11-13_resizable_list_layouts.md
Tests:   tests/test_list_screen_resize.py

The rows stay each screen's own (plan D8); this module owns only widths.
"""

import logging
import tkinter
from dataclasses import dataclass

import customtkinter as ctk

from .. import theme
from .column_resize import CHAR_PX, ColumnResizer, ColumnSpec, min_column_width

logger = logging.getLogger(__name__)

STRETCH_KEYS = ("title", "subsegment", "category", "who")

TITLE_MIN_PX = 120
TITLE_MAX_PX = 2000
# The widths these columns had before LSR: 15, 15 and 10 characters at
# CHAR_PX, so an unresized list opens as it did.
LINEAGE_DEFAULT_PX = 15 * CHAR_PX
WHO_DEFAULT_PX = 10 * CHAR_PX
STRETCH_MAX_PX = 800

# Every cell is gridded padx=5, every row padx=5 inside the scroll frame.
CELL_PAD_PX = 10
ROW_PAD_PX = 10
# A segment accent draws a border on the row; the rest is rounding.
FIT_MARGIN_PX = 6

# The trailing column that takes whatever the stretching columns cannot.
SPACER_COL = 99

HEADER_FONT_SIZE = 12

# A fit waits this long after the last <Configure>. Measured 2026-11-13: one
# fit over 500 All Items rows is ~1s of reconfiguring and ~2.3s of relayout,
# so fitting on every idle of a window drag would freeze the screen.
FIT_DELAY_MS = 120


# The expanded-mode factor chips: G, C, I, U, E, V, each gridded padx=2.
FACTOR_CHIP_WIDTHS = (120, 120, 40, 40, 40, 40)
FACTORS_WIDTH_PX = sum(FACTOR_CHIP_WIDTHS) + 4 * len(FACTOR_CHIP_WIDTHS)
# The Timer button is 70 wide, gridded padx=(0, 2).
TIMER_WIDTH_PX = 70
TIMER_PAD_PX = 2


@dataclass(frozen=True)
class FixedColumn:
    """A column that does not stretch: its grid index, heading and cell width."""

    grid_col: int
    heading: str
    width_px: int
    pad_px: int = CELL_PAD_PX

    @property
    def column_px(self) -> int:
        """The column's whole width, cell padding included."""
        return self.width_px + self.pad_px


def factors_column(grid_col: int) -> FixedColumn:
    return FixedColumn(grid_col, "", FACTORS_WIDTH_PX)


def timer_column(grid_col: int, heading: str = "") -> FixedColumn:
    return FixedColumn(grid_col, heading, TIMER_WIDTH_PX, TIMER_PAD_PX)


# LSR-D7: on a narrow window the toolbar's search entry gives up width first,
# down to this, before any button is clipped.
SEARCH_MIN_PX = 120
# The toolbar's spacer takes almost all of any extra width, so the search
# entry stays near its own width on a wide window.
TOOLBAR_SPACER_WEIGHT = 1000


def _pad_total(pad) -> int:
    """grid_info's padx, which Tk returns as one number or a pair."""
    if isinstance(pad, (tuple, list)):
        return sum(int(p) for p in pad) if len(pad) > 1 else 2 * int(pad[0])
    parts = str(pad).split()
    return sum(int(p) for p in parts) if len(parts) > 1 else 2 * int(parts[0])


class ToolbarWrap:
    """LSR-M10: a list screen's toolbar on a window too narrow for one row.

    The search entry gives up width first, down to ``SEARCH_MIN_PX`` (D7).
    Narrower than that, the controls right of the spacer column move to a
    second row, right-aligned; wide enough again, they go back. Below what
    two rows need, the toolbar clips: there is no window minsize (decided
    2026-11-13, options A and C).

    The controls keep the toolbar as their parent -- the second row grids
    them ``in_`` a child frame -- so ``toolbar.winfo_children()`` and each
    control's place in the one-row layout are unchanged.
    """

    def __init__(self, toolbar, entry, search_col: int, spacer_col: int):
        self.toolbar = toolbar
        self.entry = entry
        self.search_col = search_col
        self.spacer_col = spacer_col
        self.frame = None
        self.wrapped = False
        self._moved = []
        toolbar.grid_columnconfigure(search_col, weight=1, minsize=SEARCH_MIN_PX)
        toolbar.grid_columnconfigure(spacer_col, weight=TOOLBAR_SPACER_WEIGHT)
        entry.grid_configure(sticky="ew")
        toolbar.bind("<Configure>", self._on_configure, add="+")

    def _one_row_placements(self) -> list:
        """(widget, grid options) for every control, as in the one-row layout."""
        if self.wrapped:
            moved = {widget for widget, _info in self._moved}
            rest = [(w, w.grid_info()) for w in self.toolbar.winfo_children()
                    if w is not self.frame and w not in moved and w.grid_info()]
            return rest + list(self._moved)
        return [(w, w.grid_info()) for w in self.toolbar.winfo_children()
                if w is not self.frame and w.grid_info()]

    def one_row_px(self) -> int:
        """The toolbar width one row needs, the search entry at its minimum."""
        columns = {}
        for widget, info in self._one_row_placements():
            col = int(info["column"])
            if col == self.search_col:
                continue
            need = widget.winfo_reqwidth() + _pad_total(info["padx"])
            columns[col] = max(columns.get(col, 0), need)
        return sum(columns.values()) + SEARCH_MIN_PX

    def fit(self, width: int) -> None:
        """Lay the toolbar out for ``width`` px: one row if it fits, else two."""
        want = int(width) < self.one_row_px()
        if want == self.wrapped:
            return
        if want:
            self._wrap()
        else:
            self._unwrap()

    def _wrap(self) -> None:
        self._moved = sorted(
            ((w, w.grid_info()) for w in self.toolbar.winfo_children()
             if w is not self.frame and w.grid_info()
             and int(w.grid_info()["column"]) > self.spacer_col),
            key=lambda pair: int(pair[1]["column"]))
        if self.frame is None:
            self.frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        # tkinter's own grid: CTk's wrapper would scale grid_info's padding,
        # which is already in pixels, a second time.
        _tk_grid(self.frame, row=1, column=0, columnspan=SPACER_COL, sticky="e")
        for index, (widget, info) in enumerate(self._moved):
            _tk_grid(widget, in_=self.frame, row=0, column=index,
                     padx=info["padx"], pady=info["pady"], sticky=info["sticky"])
            widget.tkraise()
        self.wrapped = True

    def _unwrap(self) -> None:
        for widget, info in self._moved:
            _tk_grid(widget, **{k: v for k, v in info.items() if k != "in"},
                     in_=self.toolbar)
        self.frame.grid_forget()
        self._moved = []
        self.wrapped = False

    def _on_configure(self, event) -> None:
        if event.widget is self.toolbar and event.width > 1:
            self.fit(event.width)


def _tk_grid(widget, **options) -> None:
    tkinter.Grid.grid_configure(widget, **options)


# CHAR_PX is measured at the default row font; the row font size is a setting.
CHAR_PX_FONT_SIZE = 14


def row_char_px() -> int:
    """Pixels per character at the current list row font size."""
    return max(1, round(CHAR_PX * theme.LIST_ROW_FONT_SIZE / CHAR_PX_FONT_SIZE))


def stretch_specs(first_col: int, title_default: int) -> list:
    """The four stretching columns, in grid order from ``first_col``."""
    floor = min_column_width(row_char_px())
    return [
        ColumnSpec("title", first_col, title_default,
                   min_width=TITLE_MIN_PX, max_width=TITLE_MAX_PX),
        ColumnSpec("subsegment", first_col + 1, LINEAGE_DEFAULT_PX,
                   min_width=floor, max_width=STRETCH_MAX_PX),
        ColumnSpec("category", first_col + 2, LINEAGE_DEFAULT_PX,
                   min_width=floor, max_width=STRETCH_MAX_PX),
        ColumnSpec("who", first_col + 3, WHO_DEFAULT_PX,
                   min_width=floor, max_width=STRETCH_MAX_PX),
    ]


class ItemListLayout:
    """One list screen's column widths, header and resize binding."""

    def __init__(self, owner, settings, prefix: str, first_col: int,
                 title_default: int = 260):
        self.owner = owner
        self.resizer = ColumnResizer(
            owner=owner,
            settings=settings,
            prefix=prefix,
            specs=stretch_specs(first_col, title_default),
            char_px=row_char_px(),
            set_cell_width=True,
        )
        self.fixed: list = []
        self.lead: list = []
        self._measured = None
        self._after_id = None
        self._short = False
        self.fit_count = 0

    # ----------------------------------------------------------------- columns
    def set_columns(self, lead, fixed) -> None:
        """The fixed columns before the stretching ones, and after them."""
        self.lead = list(lead)
        self.fixed = list(fixed)

    def grid_col(self, key: str) -> int:
        return self.resizer.specs[key].grid_col

    def width(self, key: str) -> int:
        return self.resizer.width(key)

    def cell_text(self, key: str, full_text, width_delta: int = 0) -> str:
        return self.resizer.cell_text(key, full_text, 0, width_delta)

    def cell_width(self, key: str, width_delta: int = 0) -> int:
        return max(1, self.resizer.width(key) - width_delta)

    def apply_grid(self, frame) -> None:
        """Give a header or row frame every managed column's width."""
        self.resizer.apply_grid(frame)
        for key in STRETCH_KEYS:
            frame.grid_columnconfigure(self.grid_col(key), weight=0)
        for column in self.lead + self.fixed:
            frame.grid_columnconfigure(column.grid_col, minsize=column.column_px,
                                       weight=0)
        frame.grid_columnconfigure(SPACER_COL, weight=1)

    def register_row(self, frame, cells) -> None:
        """cells: (key, label, full_text, width_delta) per stretching cell."""
        self.resizer.register_row(
            frame, [(key, label, full, 0, delta) for key, label, full, delta in cells])

    def add_stretch_cells(self, frame, title, values: dict, text_color, font) -> None:
        """Grid SubSegment, Category and Who on a row and register all four.

        ``title`` is (label, full_text, width_delta) for the row's own title
        cell; ``values`` maps the other three keys to their full text.
        """
        cells = [("title", *title)]
        for key in STRETCH_KEYS[1:]:
            full = values.get(key) or ""
            label = ctk.CTkLabel(
                frame,
                text=self.cell_text(key, full),
                width=self.cell_width(key),
                anchor="w",
                text_color=text_color,
                font=font,
            )
            label.grid(row=0, column=self.grid_col(key), padx=5, pady=5, sticky="w")
            cells.append((key, label, full, 0))
        self.register_row(frame, cells)

    def clear_rows(self) -> None:
        self.resizer.clear_rows()

    # ------------------------------------------------------------------ header
    def build_header(self, parent, headings: dict, fg_color, border_color):
        """A header row over the same columns as the rows, with drag dividers.

        ``headings`` maps each stretching key to its text; fixed columns take
        their own ``heading``.
        """
        header = ctk.CTkFrame(parent, fg_color=fg_color)
        self.apply_grid(header)
        font = ctk.CTkFont(size=HEADER_FONT_SIZE, weight="bold")
        for column in self.lead + self.fixed:
            # The heading is gridded padx=5 whatever the cell's own padding,
            # so it takes the column less that, and fills it exactly.
            ctk.CTkLabel(header, text=column.heading,
                         width=max(1, column.column_px - CELL_PAD_PX),
                         anchor="w", font=font).grid(
                row=0, column=column.grid_col, padx=5, pady=4, sticky="w")
        labels = {}
        for key in STRETCH_KEYS:
            label = ctk.CTkLabel(header, text=headings[key], width=self.width(key),
                                 anchor="w", font=font)
            label.grid(row=0, column=self.grid_col(key), padx=5, pady=4, sticky="w")
            labels[key] = label
        self.resizer.clear_header()
        self.resizer.build_dividers(header, labels, fg_color=border_color)
        self.header_labels = labels
        return header

    # ----------------------------------------------------------------- fitting
    def reserved_px(self) -> int:
        """What a row spends on everything but the stretching columns."""
        fixed = sum(column.column_px for column in self.lead + self.fixed)
        return ROW_PAD_PX + FIT_MARGIN_PX + CELL_PAD_PX * len(STRETCH_KEYS) + fixed

    def fit(self, list_px: int) -> int:
        """Share a list ``list_px`` wide across the stretching columns.

        Returns the overflow in pixels. A shortfall is logged once each time
        the list crosses below the floors, not on every ``<Configure>``.
        Ignored while a divider is being dragged.
        """
        if self.resizer.dragging:
            return 0
        self.fit_count += 1
        overflow = self.resizer.fit_to_width(int(list_px) - self.reserved_px())
        if overflow and not self._short:
            logger.info("%s list is %d px narrower than its column floors",
                        self.resizer.prefix, overflow)
        self._short = bool(overflow)
        return overflow

    def bind(self, widget) -> None:
        """Refit whenever ``widget`` (the list area) changes size."""
        self._measured = widget
        widget.bind("<Configure>", self._on_configure, add="+")

    def _on_configure(self, _event=None) -> None:
        # Many <Configure> events arrive per drag of the window edge: each one
        # restarts the wait, so the rows are refitted once the edge stops.
        if self._after_id is not None:
            self.owner.after_cancel(self._after_id)
        self._after_id = self.owner.after(FIT_DELAY_MS, self._run_fit)

    def _run_fit(self) -> None:
        self._after_id = None
        widget = self._measured
        if widget is None or not widget.winfo_exists():
            return
        width = widget.winfo_width()
        if width > 1:
            self.fit(width)
