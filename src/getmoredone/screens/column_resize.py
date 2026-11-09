"""Reusable spreadsheet-style column resizing for list screens.

One `ColumnResizer` instance per screen owns its column widths, persistence,
the draggable divider handles, and live text re-clamping. Screens keep their
own row/header rendering but delegate widths, clamp counts, and drag handling
here so the behaviour is identical across screens (Today, Scheduler, ...).

Used by `screens/today.py` and `screens/drag_schedule.py`.
"""

from dataclasses import dataclass

import customtkinter as ctk

from .title_format import format_column_text

# Approximate pixels per character at the size-14 list font. Used to translate a
# column's pixel width into a character budget for `format_column_text`.
CHAR_PX = 8

# The narrowest a resizable column is ever made by a panel resize, in
# characters. UPD-F4: the on-screen walk asked for "all columns to resize as I
# move the vertical bar left or right, down to 5 character widths", so the
# floor is stated in characters and converted at whatever `char_px` the screen
# measures its text with.
MIN_COLUMN_CHARS = 5


def min_column_width(char_px: int = CHAR_PX) -> int:
    """The five-character floor in pixels at the given character width."""
    return MIN_COLUMN_CHARS * max(1, char_px)


def chars_for_width(width_px: int, char_px: int = CHAR_PX) -> int:
    """How many characters fit in a column of the given pixel width (>= 1)."""
    return max(1, int(width_px) // max(1, char_px))


@dataclass
class ColumnSpec:
    """One managed column.

    key:          stable id, also the persistence sub-key and cell tag.
    grid_col:     grid column index used in BOTH the header and each row frame.
    default_width/min_width/max_width: pixel bounds.
    resizable:    when False, the column has a fixed width and no divider handle.
    """

    key: str
    grid_col: int
    default_width: int
    min_width: int = 80
    max_width: int = 800
    resizable: bool = True


class ColumnResizer:
    """Owns column widths + persistence + divider drag + live re-clamp.

    text_pad wraps clamped cell text (the Scheduler pills use `" text "`).
    """

    def __init__(self, owner, settings, prefix, specs, char_px=CHAR_PX, text_pad="",
                 set_cell_width=True):
        self.owner = owner
        self.settings = settings
        self.prefix = prefix
        self.specs = {s.key: s for s in specs}
        self.order = [s.key for s in specs]
        self.char_px = char_px
        self.text_pad = text_pad
        # When True, a row cell's own width is set to the column width (needed for
        # solid-colour pill labels). When False, the column width is carried by the
        # grid minsize alone and only the cell text is re-clamped (e.g. Today, whose
        # title label sits inside a sub-frame).
        self.set_cell_width = set_cell_width
        self._widths = self._load_widths()
        self._rows = []          # list[(frame, cells)] ; cells: [(key, label, full, reserve, width_delta)]
        self._header = None      # (header_frame, {key: label})
        self._drag = None        # (key, x_root_start, width_start)
        # The widths held before a too-narrow panel pinned everything to the
        # floor, so the shape can be given back when the panel is wide enough
        # again. `_widths` is both the rendered width and the weight
        # `_share` divides by, so flooring it in place would destroy the
        # proportions the user set rather than suspend them. None whenever
        # the floor is not in force.
        self._pre_floor = None   # {key: width} | None

    # ------------------------------------------------------------------ widths
    def _setting_attr(self) -> str:
        return f"{self.prefix}_col_widths"

    def _load_widths(self) -> dict:
        stored = getattr(self.settings, self._setting_attr(), None) or {}
        widths = {}
        for key, spec in self.specs.items():
            raw = stored.get(key)
            if raw is None and key == "title":
                # Legacy single-title scalar from before this module existed.
                raw = getattr(self.settings, f"{self.prefix}_title_col_width", None)
            widths[key] = self._clamp(spec, raw if raw else spec.default_width)
        return widths

    @staticmethod
    def _clamp(spec: ColumnSpec, width) -> int:
        return max(spec.min_width, min(spec.max_width, int(width)))

    def width(self, key: str) -> int:
        return self._widths[key]

    def chars(self, key: str, reserve: int = 0, width_delta: int = 0) -> int:
        """The character budget for a cell in this column.

        `width_delta` is the same number `register_row` takes: how much
        narrower than its column the cell is. A chip pill is inset inside its
        column, so a budget measured from the column width overruns the pill
        and clips the last character (AWA-S5). It defaults to 0, so every
        caller that predates it is unaffected.
        """
        return max(
            1,
            chars_for_width(self._widths[key] - width_delta, self.char_px) - reserve,
        )

    def cell_text(self, key: str, full_text, reserve: int = 0,
                  width_delta: int = 0) -> str:
        """Clamped, padded text for a cell at the width that cell is given."""
        clamped = format_column_text(full_text, self.chars(key, reserve, width_delta))
        return f"{self.text_pad}{clamped}{self.text_pad}"

    def _persist(self) -> None:
        stored = dict(getattr(self.settings, self._setting_attr(), None) or {})
        stored.update(self._widths)
        setattr(self.settings, self._setting_attr(), stored)
        self.settings.save()

    # --------------------------------------------------------------- fitting
    def fit_to_width(self, available: int) -> int:
        """Share `available` pixels across the resizable columns. Returns overflow.

        Purpose: UPD-F4.1/F4.2/F4.3 — a panel that grew or shrank hands the
                 difference to its resizable columns in proportion to the
                 widths they already have, never below the five-character
                 floor, with the fixed columns reserved out first.
        Spec:    docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
        Tests:   tests/test_unified_panel_design.py::test_updf41_a_divider_move_rescales_every_resizable_column

        A column's stored width is treated as a weight rather than a pixel
        promise. That is what lets a drag and a resize coexist: the drag
        writes a pixel width, which becomes the weight the next resize shares
        the panel out by, so the *shape* the user set survives a window of a
        different size (UPD-F4.6).

        The return value is the pixels by which the columns overrun
        `available` -- zero whenever they fit. It is a count, not a flag, so
        the caller can say how badly a panel is too narrow instead of
        discovering it from a clipped column (P2). A panel too narrow even for
        the floors gets the floors and overflows; a floor that gives way under
        pressure is not a floor.
        """
        order = [k for k in self.order if self.specs[k].resizable]
        if not order:
            return 0

        reserved = sum(self._widths[k] for k in self.order
                       if not self.specs[k].resizable)
        # A panel of no width is the worst case, not a no-op: returning 0 here
        # would report "they fit" for a panel with nothing in it, which is the
        # silence this return value exists to prevent.
        budget = max(0, int(available)) - reserved

        floors = {k: max(self.specs[k].min_width, min_column_width(self.char_px))
                  for k in order}
        floor_total = sum(floors.values())
        if budget < floor_total:
            # Remember the shape once, on the way in -- not on every
            # <Configure> of a drag that holds the window below the floor,
            # which would overwrite it with the floors themselves.
            if self._pre_floor is None:
                self._pre_floor = {k: self._widths[k] for k in order}
            for key in order:
                self._widths[key] = floors[key]
            self._apply_all()
            return floor_total - budget

        if self._pre_floor is not None:
            # Wide enough again: share out the shape the panel had before the
            # floor, not the flat floors it was left holding.
            for key in order:
                if key in self._pre_floor:
                    self._widths[key] = self._pre_floor[key]
            self._pre_floor = None

        assigned = self._share(order, budget, floors)
        if assigned != {k: self._widths[k] for k in order}:
            self._widths.update(assigned)
            self._apply_all()
        return 0

    def _share(self, order, budget: int, floors: dict) -> dict:
        """`budget` pixels over `order`, by weight, inside each column's bounds.

        Columns that would land outside their own bounds are pinned there and
        taken out of the share, and what they did not use is re-shared across
        the rest. The loop runs at most once per column, because each pass
        either pins one or settles.
        """
        assigned: dict = {}
        free = list(order)
        remaining = budget

        while free:
            weight = sum(self._widths[k] for k in free)
            if weight <= 0:
                # Nothing to go by; equal shares is the only honest answer.
                weight = len(free)
                shares = {k: remaining / len(free) for k in free}
            else:
                shares = {k: remaining * self._widths[k] / weight for k in free}

            pinned = False
            for key in list(free):
                want = int(shares[key])
                bound = None
                if want < floors[key]:
                    bound = floors[key]
                elif want > self.specs[key].max_width:
                    bound = self.specs[key].max_width
                if bound is not None:
                    assigned[key] = bound
                    free.remove(key)
                    remaining -= bound
                    pinned = True
            if pinned:
                continue

            for key in free:
                assigned[key] = int(shares[key])
            # Integer division leaves up to one pixel per column unspent. It
            # goes to the widest free column, so the panel is filled exactly
            # and the rounding is where it shows least.
            spare = remaining - sum(assigned[k] for k in free)
            if spare > 0:
                widest = max(free, key=lambda k: assigned[k])
                capped = min(self.specs[widest].max_width,
                             assigned[widest] + spare)
                assigned[widest] = capped
            break

        return assigned

    def _apply_all(self) -> None:
        """Push every column's current width to the header and every row."""
        for key in self.order:
            self._apply_live(key)

    # -------------------------------------------------------------------- grid
    def apply_grid(self, frame) -> None:
        """Set each managed column's grid minsize on a header or row frame."""
        for key in self.order:
            frame.grid_columnconfigure(self.specs[key].grid_col, minsize=self._widths[key])

    # ------------------------------------------------------------------ header
    def build_dividers(self, header_frame, header_labels, height=22, fg_color=None) -> None:
        """Add a draggable divider at each resizable column's right edge.

        header_labels maps column key -> the header CTkLabel (so its width can be
        kept in sync during a drag).
        """
        self._header = (header_frame, dict(header_labels))
        for key in self.order:
            spec = self.specs[key]
            if not spec.resizable:
                continue
            handle = ctk.CTkFrame(
                header_frame,
                width=4,
                height=height,
                corner_radius=0,
                fg_color=fg_color if fg_color is not None else ("gray70", "gray30"),
                cursor="sb_h_double_arrow",
            )
            handle.grid(row=0, column=spec.grid_col, sticky="nse", padx=0, pady=2)
            handle.bind("<Button-1>", lambda e, k=key: self._on_start(e, k))
            handle.bind("<B1-Motion>", lambda e, k=key: self._on_drag(e, k))
            handle.bind("<ButtonRelease-1>", lambda e, k=key: self._on_stop(e, k))

    # -------------------------------------------------------------------- rows
    def register_row(self, frame, cells) -> None:
        """Register a row for live resize.

        cells: iterable of (key, label) or (key, label, full_text) or
        (key, label, full_text, reserve) or
        (key, label, full_text, reserve, width_delta).
        full_text/reserve enable re-clamping. width_delta is subtracted from
        the column width when the cell's own width is set, for a cell that
        sits inside its column rather than filling it -- a chip pill, which
        would otherwise touch the next column (UPD-M3.5). It defaults to 0, so
        every caller that predates it is unaffected.
        """
        self.apply_grid(frame)
        norm = []
        for cell in cells:
            key, label = cell[0], cell[1]
            full = cell[2] if len(cell) > 2 else None
            reserve = cell[3] if len(cell) > 3 else 0
            width_delta = cell[4] if len(cell) > 4 else 0
            norm.append((key, label, full, reserve, width_delta))
        self._rows.append((frame, norm))

    def clear_rows(self) -> None:
        self._rows = []

    def clear_header(self) -> None:
        """Forget the registered header.

        `clear_rows` has always had a counterpart in the caller -- the header
        frame is destroyed with the rows -- but nothing dropped the reference,
        so `_apply_live` went on reaching for a destroyed frame and relied on
        its `winfo_exists()` guard to say nothing happened (AWA-S6 b).
        """
        self._header = None

    # -------------------------------------------------------------------- drag
    def _on_start(self, event, key) -> None:
        self._drag = (key, event.x_root, self._widths[key])

    def _on_drag(self, event, key) -> None:
        if not self._drag:
            return
        k, x0, w0 = self._drag
        new_width = self._clamp(self.specs[k], w0 + (event.x_root - x0))
        if new_width != self._widths[k]:
            self._widths[k] = new_width
            # A width the user set by hand while the panel is floored is the
            # newer intent: the restore must not give it back the old one.
            # The other columns' remembered shape still stands.
            if self._pre_floor is not None:
                self._pre_floor.pop(k, None)
            self._apply_live(k)

    def _on_stop(self, event, key) -> None:
        self._drag = None
        self._persist()

    def _apply_live(self, key) -> None:
        """Push the dragged column's new width to the header and every row."""
        spec = self.specs[key]
        width = self._widths[key]

        if self._header is not None:
            header_frame, header_labels = self._header
            if header_frame.winfo_exists():
                header_frame.grid_columnconfigure(spec.grid_col, minsize=width)
            label = header_labels.get(key)
            if label is not None and label.winfo_exists():
                label.configure(width=width)

        for frame, cells in self._rows:
            if not frame.winfo_exists():
                continue
            frame.grid_columnconfigure(spec.grid_col, minsize=width)
            for ckey, label, full, reserve, width_delta in cells:
                if ckey != key or not label.winfo_exists():
                    continue
                if self.set_cell_width:
                    label.configure(width=max(1, width - width_delta))
                if full is not None:
                    label.configure(
                        text=self.cell_text(key, full, reserve, width_delta))
