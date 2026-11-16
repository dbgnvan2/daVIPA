"""The column layout shared by six item lists, and the toolbar wrap of seven.

Purpose: LSR-M1/M2/M3/M6, LSR2-M1..M8 -- Today, Upcoming, All Items and
         Hierarchical give every text column (Title, SubSegment, Category,
         Who, and each screen's dates, priority, time, status) to one
         ``ColumnResizer`` each, hold their controls (checkbox, Timer, factor
         chips) at one width in the header and every row, and refit the text
         columns whenever the list area changes width.
         SPC-M1..M17 -- Completed (Title, Who, Completed, Pri) and the Project
         Board's linked Action Items (Title, Status, Start, Due) do the same
         through ``ItemListLayout.custom``, which takes a column set of its
         own; and ``ToolbarWrap`` serves the Scheduler, Projects and Completed
         headers as well as those four, including headers with no search entry
         and with controls on rows of their own.
Spec:    docs/unused-docs/implementation_plan_2026-11-13_resizable_list_layouts.md,
         docs/unused-docs/implementation_plan_2026-11-14_all_columns_resize.md,
         docs/unused-docs/implementation_plan_2026-11-15_schedule_projects_completed_resize.md
Tests:   tests/test_list_screen_resize.py, tests/test_screen_resize_spc.py

The rows stay each screen's own (plan D8); this module owns only widths.
"""

import logging
import tkinter
from dataclasses import dataclass
from typing import Optional

import customtkinter as ctk

from .. import theme
from .column_resize import CHAR_PX, ColumnResizer, ColumnSpec
from .priority_cell import CELL_INSET_PX, build_level_cell

logger = logging.getLogger(__name__)

STRETCH_KEYS = ("title", "subsegment", "category", "who")

# LSR2-D4: no list column is made narrower than this many characters at the
# row font, Title included (user, 2026-11-14).
LIST_MIN_CHARS = 6

TITLE_MAX_PX = 2000
STRETCH_MAX_PX = 800

# LRP-M6 (plan D1): one default width per column kind, shared by every
# listing of action items. A default is also the column's weight until the
# user drags it (LSR2-D8), so this table is the shape a list opens at and the
# reason the seven listings now resize alike. Measured before it: Title was
# 220, 260 or 320, a lineage column 120 or 170, Who 80 or 110, a date column
# 60, 90, 110 or 150.
#
# "start_date" is the Scheduler's key for the same column as "start". A key
# is also its persistence sub-key, so renaming it would discard a width the
# user had dragged; both spellings carry the one value instead.
COLUMN_DEFAULT_PX = {
    "title": 260,
    "segment": 150,
    "subsegment": 150,
    "category": 150,
    "who": 110,
    "start": 110,
    "start_date": 110,
    "due": 110,
    "completed": 110,
    "status": 90,
    "time": 60,
    "subitems": 70,
}
# The priority cell is a control with fixed content, 60 px on most lists and
# 80 on All Items on purpose, so it is not shared.
UNSHARED_KEYS = ("pri",)


def column_default_px(key: str) -> int:
    """The shared default for a column kind; raises on an unknown key.

    Raising is the point. A listing that invents a column name gets an error
    where it is built rather than a width nobody chose.
    """
    return COLUMN_DEFAULT_PX[key]

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

# LRP-M10: a value filter (Who, Status, Segment, SubSegment, Project) is never
# drawn narrower than this -- "All" plus the dropdown arrow -- and never wider
# than FILTER_MAX_FACTOR times its own default, so a very wide window leaves
# the rest of the slack in the spacer column instead of stretching five combo
# boxes across it. The small numeric selectors ("Next 7 days", "Last 30 days")
# are not filters for this purpose: their content is one to three characters
# and growing them buys nothing (plan D5).
FILTER_MIN_PX = 90
FILTER_MAX_FACTOR = 2
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
    second row, left-aligned (LRP-M1); wide enough again, they go back. Below
    what two rows need, the toolbar clips: there is no window minsize
    (decided 2026-11-13, options A and C).

    The controls keep the toolbar as their parent -- the second row grids
    them ``in_`` a child frame -- so ``toolbar.winfo_children()`` and each
    control's place in the one-row layout are unchanged.

    SPC-D9: ``entry`` is None on a toolbar with no search entry (Completed,
    the Scheduler), and the search minimum then counts as nothing.
    ``control_row``/``wrap_row`` are the row the controls sit on and the row
    they wrap into, for a toolbar whose other rows are already taken (the
    Project Board's search row and its warning line).

    LRP-M10: ``filters`` are the value filters, which resize with the toolbar
    the way a list's columns resize with the list -- a share of the slack in
    proportion to their own default widths, never below ``FILTER_MIN_PX``.
    Their widths are set here rather than left to ``sticky="ew"`` and a grid
    weight, because a grid weight cannot give the slack to the filters while
    taking the shortfall out of the search entry first (LSR-D7), and because
    it is the same rule the columns follow (docs/list_resize_principles.md).

    LRP-M11: that makes the wrap honest. The row wraps when the controls at
    their *minimum* widths do not fit, not when their requested widths do
    not.
    """

    def __init__(self, toolbar, entry, search_col, spacer_col: int,
                 control_row: int = 0, wrap_row: int = 1, filters=()):
        self.toolbar = toolbar
        self.entry = entry
        self.search_col = search_col
        self.spacer_col = spacer_col
        self.control_row = control_row
        self.wrap_row = wrap_row
        self.frame = None
        self.wrapped = False
        self._short = 0
        self._moved = []
        # (widget, its default width), captured before anything resizes it.
        # The default is the weight ``fit_filters`` shares by and the width
        # ``one_row_px`` measures with, so it has to be read before a fit.
        self.filters = [(widget, int(widget.cget("width")))
                        for widget in filters]
        if entry is not None:
            toolbar.grid_columnconfigure(search_col, weight=1,
                                         minsize=SEARCH_MIN_PX)
            entry.grid_configure(sticky="ew")
        toolbar.grid_columnconfigure(spacer_col, weight=TOOLBAR_SPACER_WEIGHT)
        # CTkFrame.bind would bind its inner canvas, whose events never
        # name the toolbar; bind the toolbar's own Tk frame.
        tkinter.Misc.bind(toolbar, "<Configure>", self._on_configure, "+")

    def _on_control_row(self, info) -> bool:
        return bool(info) and int(info["row"]) == self.control_row

    def _one_row_placements(self) -> list:
        """(widget, grid options) for every control, as in the one-row layout."""
        if self.wrapped:
            moved = {widget for widget, _info in self._moved}
            rest = [(w, w.grid_info()) for w in self.toolbar.winfo_children()
                    if w is not self.frame and w not in moved
                    and self._on_control_row(w.grid_info())]
            return rest + list(self._moved)
        return [(w, w.grid_info()) for w in self.toolbar.winfo_children()
                if w is not self.frame and self._on_control_row(w.grid_info())]

    def _row_px(self, filter_px) -> int:
        """One row's width, each value filter counted as ``filter_px(default)``.

        Every other control counts at its requested width. The sum is taken
        per column with ``max``, so a label sharing a filter's column still
        counts at its own width.
        """
        defaults = dict(self.filters)
        columns = {}
        for widget, info in self._one_row_placements():
            col = int(info["column"])
            if self.entry is not None and col == self.search_col:
                continue
            width = (filter_px(defaults[widget]) if widget in defaults
                     else widget.winfo_reqwidth())
            columns[col] = max(columns.get(col, 0),
                               width + _pad_total(info["padx"]))
        minimum = SEARCH_MIN_PX if self.entry is not None else 0
        return sum(columns.values()) + minimum

    def one_row_px(self) -> int:
        """The toolbar width one row needs, the search entry at its minimum.

        The value filters count at their *default* widths, not the widths
        they are drawn at now. A number that moved as ``fit_filters`` resized
        them would make ``fit`` non-monotone: measured 2026-11-16, the same
        All Items toolbar read 997 px, then 916, then 922, and once it had
        wrapped it never came back.
        """
        return self._row_px(lambda default: default)

    def wrap_row_px(self) -> int:
        """The toolbar width the wrapped second row needs.

        LRP-M1: the wrap frame is gridded ``sticky="w"``, so Tk keeps it at
        its requested width and pins its *left* edge to the cell -- a second
        row wider than the toolbar overflows to the right. Either edge hides
        an overflow from a check on the other, so this is the number that
        says whether two rows actually fit, and it is always below
        ``one_row_px()``: the wrapped group is a subset of the controls one
        row has to hold.

        A value filter in that group counts at ``FILTER_MIN_PX``, which is
        the width it is actually at whenever the row is wrapped: a wrapped
        toolbar is narrower than ``min_one_row_px()``, so ``fit_filters`` has
        less room than the minimums and pins every filter at one. Counting it
        live left this number moving as the filters resized -- the same
        feedback loop ``one_row_px`` was changed to break (found by the
        sweep, 2026-11-16, over a measurement that reads the Scheduler's
        whole wrapped group).
        """
        defaults = dict(self.filters)
        return sum((FILTER_MIN_PX if widget in defaults
                    else widget.winfo_reqwidth()) + _pad_total(info["padx"])
                   for widget, info in self._wrap_candidates())

    def _wrap_candidates(self) -> list:
        """(widget, grid options) for the controls right of the spacer column."""
        return sorted(
            ((w, info) for w, info in self._one_row_placements()
             if int(info["column"]) > self.spacer_col),
            key=lambda pair: int(pair[1]["column"]))

    def _filter_room(self, width: int) -> int:
        """The width the filters have between them at a toolbar of ``width``.

        Everything else on the row -- labels, buttons, every pad, and the
        search entry at its minimum -- is taken out first.
        """
        return max(0, int(width) - self._row_px(lambda _default: 0))

    def min_one_row_px(self) -> int:
        """The toolbar width one row needs with every filter at its minimum.

        This is the wrap threshold (LRP-M11): below it the row cannot hold
        its controls even with every filter shrunk, so it wraps.
        ``one_row_px()`` is the same number with the filters at their
        defaults, which is the width at or above which they are drawn full
        size.
        """
        return self._row_px(lambda _default: FILTER_MIN_PX)

    def fit_filters(self, width: int) -> None:
        """Give each value filter its share of a toolbar ``width`` (LRP-M10).

        The share is proportional to the filter's own default width, so the
        filters keep their relative sizes -- Project stays wider than Who.
        A share below ``FILTER_MIN_PX`` or above ``FILTER_MAX_FACTOR`` times
        the default pins there, and what is left is shared again among the
        rest, as ``ColumnResizer._share`` does it. Clamping each share where
        it stood instead drew a total wider than the room: 190 px into 180 on
        All Items, over a 23 px band, where the row has not wrapped, the
        search entry is already at its minimum and Tk takes the difference
        out of a column of its own choosing (found by the sweep, 2026-11-16).

        Only a width that actually changed is written: ``fit`` runs on every
        ``<Configure>`` of a window drag, and a CTkComboBox redraws itself
        when it is configured.
        """
        if not self.filters:
            return
        room = self._filter_room(width)
        pending = list(self.filters)
        drawn = {}
        while pending:
            total = sum(default for _widget, default in pending) or 1
            pinned = []
            for widget, default in pending:
                share = int(room * default / total)
                if share < FILTER_MIN_PX:
                    pinned.append((widget, default, FILTER_MIN_PX))
                elif share > FILTER_MAX_FACTOR * default:
                    pinned.append((widget, default, FILTER_MAX_FACTOR * default))
            if not pinned:
                for widget, default in pending:
                    drawn[widget] = int(room * default / total)
                break
            for widget, default, px in pinned:
                drawn[widget] = px
                room -= px
                pending.remove((widget, default))
            room = max(0, room)
        for widget, px in drawn.items():
            if int(widget.cget("width")) != px:
                widget.configure(width=px)

    def fit(self, width: int) -> int:
        """Lay the toolbar out for ``width`` px: one row if it fits, else two.

        LRP-M11: the threshold is ``min_one_row_px()`` -- the row wraps when
        the controls at their *minimum* widths do not fit, not when their
        default widths do not. A filter therefore gives up width before the
        buttons leave the row, after the search entry (LSR-D7) and before it.

        While wrapped, the filters stay at their minimum: the room is
        measured against one row, which is the width they would have to fit
        in to come back.

        Returns the pixels by which the wrapped row overruns ``width``, and
        logs a shortfall each time it grows past the worst one logged since
        the toolbar last fitted, as ``ItemListLayout.fit`` does for the
        columns (P2). There is no window minsize, and ``sticky="w"`` puts the
        overflow past the right edge where nothing on screen reports it.

        The watermark is the number, not a flag. ``fit`` runs on every
        ``<Configure>``, so a latched boolean logged the first few pixels of
        overrun and then suppressed the 400px case the user reaches by
        keeping hold of the window edge -- one INFO line naming the least
        severe instance was the entire record (found by the sweep's re-sweep,
        2026-11-16).
        """
        self.fit_filters(width)
        want = int(width) < self.min_one_row_px()
        if want != self.wrapped:
            if want:
                self._wrap()
            else:
                self._unwrap()
        short = max(0, self.wrap_row_px() - int(width)) if self.wrapped else 0
        if short > self._short:
            logger.info("toolbar wrapped row needs %d px inside %d px: %d px "
                        "is drawn past the right edge",
                        self.wrap_row_px(), int(width), short)
        self._short = short
        return short

    def _wrap(self) -> None:
        self._moved = self._wrap_candidates()
        if self.frame is None:
            self.frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        # tkinter's own grid: CTk's wrapper would scale grid_info's padding,
        # which is already in pixels, a second time.
        # LRP-M1: left-justified. The frame keeps its requested width, so
        # "w" pins its left edge to the toolbar's left and the controls read
        # left to right from there, as they do on the unwrapped row.
        _tk_grid(self.frame, row=self.wrap_row, column=0,
                 columnspan=SPACER_COL, sticky="w")
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


def header_char_px() -> int:
    """Pixels per character for a heading: the header font, plus one for bold."""
    return max(1, round(CHAR_PX * HEADER_FONT_SIZE / CHAR_PX_FONT_SIZE)) + 1


@dataclass(frozen=True)
class TextColumn:
    """A screen's own text column after Who: it resizes like the first four.

    ``default_px`` is the column's opening width, and its weight until the
    user drags it (LSR2-D8). Left as ``None`` -- which is what every listing
    does for a shared column kind -- it comes from ``COLUMN_DEFAULT_PX``
    (LRP-M6). A number here overrides the table, and the only columns that
    pass one are the priority cells (``UNSHARED_KEYS``).
    """

    key: str
    grid_col: int
    heading: str
    default_px: Optional[int] = None

    @property
    def width_px(self) -> int:
        """Its own default if it has one, else the shared one for its kind."""
        if self.default_px is not None:
            return self.default_px
        return column_default_px(self.key)


def list_floor_px() -> int:
    """The narrowest any list column is made: 6 characters at the row font."""
    return LIST_MIN_CHARS * row_char_px()


def stretch_specs(first_col: int, columns=()) -> list:
    """Every resizable column: the four from ``first_col``, then ``columns``.

    Every width comes from ``COLUMN_DEFAULT_PX`` unless a ``TextColumn``
    carries one of its own (LRP-M6).
    """
    floor = list_floor_px()
    specs = [
        ColumnSpec("title", first_col, column_default_px("title"),
                   min_width=floor, max_width=TITLE_MAX_PX),
        ColumnSpec("subsegment", first_col + 1, column_default_px("subsegment"),
                   min_width=floor, max_width=STRETCH_MAX_PX),
        ColumnSpec("category", first_col + 2, column_default_px("category"),
                   min_width=floor, max_width=STRETCH_MAX_PX),
        ColumnSpec("who", first_col + 3, column_default_px("who"),
                   min_width=floor, max_width=STRETCH_MAX_PX),
    ]
    for column in columns:
        specs.append(ColumnSpec(column.key, column.grid_col, column.width_px,
                                min_width=floor, max_width=STRETCH_MAX_PX))
    return specs


def custom_specs(columns, title_key: str = "title") -> list:
    """Specs for a list whose columns are not the shared four (SPC-D3).

    Completed (Title, Who, Completed, Pri) and the Project Board's Action
    Items (Title, Status, Start, Due) have neither SubSegment nor Category,
    so ``stretch_specs`` cannot describe them. Same floor and same maxima.
    """
    floor = list_floor_px()
    return [ColumnSpec(
        column.key, column.grid_col, column.width_px, min_width=floor,
        max_width=TITLE_MAX_PX if column.key == title_key else STRETCH_MAX_PX)
        for column in columns]


class ItemListLayout:
    """One list screen's column widths, header and resize binding."""

    def __init__(self, owner, settings, prefix: str, first_col: int = 1,
                 columns=(), specs=None):
        self.owner = owner
        self.headings = {column.key: column.heading for column in columns}
        self.resizer = ColumnResizer(
            owner=owner,
            settings=settings,
            prefix=prefix,
            specs=(specs if specs is not None
                   else stretch_specs(first_col, columns)),
            char_px=row_char_px(),
            set_cell_width=True,
        )
        self.fixed: list = []
        self.lead: list = []
        self._measured = None
        self._after_id = None
        self._short = 0
        self.fit_count = 0
        # A fit skipped during a drag runs once the divider is let go.
        self.resizer.on_drag_end = self._on_configure
        self.resizer.fill_after_drag = True

    @classmethod
    def custom(cls, owner, settings, prefix: str, columns,
               title_key: str = "title"):
        """A list whose columns are its own, not the shared four (SPC-D3).

        Every column is a ``TextColumn``, Title included, and the floor, the
        debounce, the dividers, heading cutting, the refit after a drag and
        the persistence are the ones the four item lists use.
        """
        return cls(owner, settings, prefix, columns=columns,
                   specs=custom_specs(columns, title_key))

    # ----------------------------------------------------------------- columns
    @property
    def keys(self) -> tuple:
        """Every resizable column, in grid order."""
        return tuple(self.resizer.order)

    def move(self, key: str, grid_col: int) -> None:
        """Put a resizable column at another grid index (All Items' Status,
        which sits after the factor chips when they are shown)."""
        self.resizer.specs[key].grid_col = grid_col

    def set_columns(self, lead, fixed) -> None:
        """The controls before the resizable columns, and after them."""
        self.lead = list(lead)
        self.fixed = list(fixed)
        if self._measured is not None:
            self._on_configure()

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
        for key in self.keys:
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

    def add_text_cell(self, frame, key: str, full_text, text_color, font,
                      **label_kwargs):
        """Grid a text cell in column ``key`` of a registered row, at that
        column's width, and keep it following the column (LSR2-M1)."""
        full = "" if full_text is None else str(full_text)
        label = ctk.CTkLabel(
            frame,
            text=self.cell_text(key, full),
            width=self.cell_width(key),
            anchor="w",
            text_color=text_color,
            font=font,
            **label_kwargs,
        )
        label.grid(row=0, column=self.grid_col(key), padx=5, pady=5, sticky="w")
        self.resizer.add_cells(frame, [(key, label, full, 0, 0)])
        return label

    def add_cell(self, frame, key: str, widget, full_text=None,
                 width_delta: int = 0) -> None:
        """Keep a widget the screen built itself at column ``key``'s width.

        ``full_text`` re-cuts its text too; ``width_delta`` is how much
        narrower than the column it sits, as in ``register_row``.
        """
        self.resizer.add_cells(frame, [(key, widget, full_text, 0, width_delta)])

    def add_level_cell(self, frame, key: str, cell, text: str, row_text, font,
                       on_click=None):
        """Grid a priority-coloured cell in column ``key`` and keep it, and
        the label inside it, at that column's width."""
        box, label = build_level_cell(frame, cell, text, self.cell_width(key),
                                      row_text, font, on_click=on_click)
        box.grid(row=0, column=self.grid_col(key), padx=5, pady=5, sticky="w")
        if box is label:
            self.add_cell(frame, key, label, text)
        else:
            self.add_cell(frame, key, box)
            self.add_cell(frame, key, label, text, 2 * CELL_INSET_PX)
        return box, label

    def clear_rows(self) -> None:
        self.resizer.clear_rows()

    # ------------------------------------------------------------------ header
    def build_header(self, parent, headings: dict, fg_color, border_color):
        """A header row over the same columns as the rows, with drag dividers.

        ``headings`` maps the first four keys to their text; a screen's own
        text columns and its controls carry their own ``heading``.
        """
        headings = {**self.headings, **headings}
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
        for key in self.keys:
            label = ctk.CTkLabel(header, text=headings[key], width=self.width(key),
                                 anchor="w", font=font)
            label.grid(row=0, column=self.grid_col(key), padx=5, pady=4, sticky="w")
            labels[key] = label
        self.resizer.clear_header()
        self.resizer.build_dividers(
            header, labels, fg_color=border_color,
            header_texts={key: headings[key] for key in self.keys},
            header_char_px=header_char_px())
        self.header_labels = labels
        return header

    @staticmethod
    def header_padx(scroll_frame, outer_padx: int) -> tuple:
        """The header's padx so its columns sit over the scrolled rows.

        A row starts at the scroll frame's own padx, plus the inset at which
        CTkScrollableFrame grids its canvas (corner radius + border), plus
        the row's padx of 5.
        """
        box = scroll_frame._parent_frame
        inset = int(box.cget("corner_radius")) + int(box.cget("border_width"))
        return (outer_padx + inset + ROW_PAD_PX // 2, outer_padx + ROW_PAD_PX // 2)

    # ----------------------------------------------------------------- fitting
    def reserved_px(self) -> int:
        """What a row spends on everything but the resizable columns."""
        fixed = sum(column.column_px for column in self.lead + self.fixed)
        return ROW_PAD_PX + FIT_MARGIN_PX + CELL_PAD_PX * len(self.keys) + fixed

    def fit(self, list_px: int) -> int:
        """Share a list ``list_px`` wide across the resizable columns.

        Returns the overflow in pixels. A shortfall is logged each time it
        grows past the worst one logged since the list last fitted, not on
        every ``<Configure>`` and not only the first few pixels of it -- see
        ``ToolbarWrap.fit`` for why the watermark is the number rather than a
        flag. Ignored while a divider is being dragged.
        """
        if self.resizer.dragging:
            return 0
        self.fit_count += 1
        overflow = self.resizer.fit_to_width(int(list_px) - self.reserved_px())
        if overflow > self._short:
            logger.info("%s list is %d px narrower than its column floors",
                        self.resizer.prefix, overflow)
        self._short = overflow
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
            self.fit(width / self.owner._get_widget_scaling())
