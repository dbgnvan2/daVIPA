"""Reusable spreadsheet-style column resizing for list screens.

One `ColumnResizer` instance per screen owns its column widths, persistence,
the draggable divider handles, and live text re-clamping. Screens keep their
own row/header rendering but delegate widths, clamp counts, and drag handling
here so the behaviour is identical across screens (Today, Scheduler, ...).

Used by the four item lists (through `item_list_columns.py`), `screens/drag_schedule.py` and `screens/chip_table.py`.
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
        self._header_texts = {}  # key -> full heading, cut to the column
        self._header_char_px = char_px
        self._drag = None        # (key, x_root_start, width_start)
        # Called after a divider drag ends and the widths are saved.
        self.on_drag_end = None
        # True where the owner refits the columns to its width after a drag
        # (the item lists and the Scheduler): the dragged column then keeps
        # the width it was dropped at and the others absorb the change. False
        # where nothing refits (the APE/Week panels): the widths on screen at
        # release are the shape (`_set_weight_from_drag`).
        self.fill_after_drag = False
        # LSR2-D6: the shape a fit shares the width out by. Only a drag (or
        # the stored widths, on load) sets it; a fit writes `_widths` alone.
        # When a fit wrote its result back as the next fit's weights, the
        # columns that reached their floor first lost their share, and a
        # narrow-then-wide window came back with a different shape.
        self._weights = self._load_stored()
        self._px_per_weight = 1.0

    # ------------------------------------------------------------------ widths
    def _setting_attr(self) -> str:
        return f"{self.prefix}_col_widths"

    def _load_stored(self) -> dict:
        """The saved value per column, or its default; unclamped.

        A saved value is a weight (LSR2-D8), and a weight is not bound by the
        column's pixel limits: clamping it changed the shape on every
        restart (found by the csdp sweep, 2026-11-14).
        """
        stored = getattr(self.settings, self._setting_attr(), None) or {}
        values = {}
        for key, spec in self.specs.items():
            raw = stored.get(key)
            if raw is None and key == "title":
                # Legacy single-title scalar from before this module existed.
                raw = getattr(self.settings, f"{self.prefix}_title_col_width", None)
            try:
                value = float(raw) if raw else 0.0
            except (TypeError, ValueError):
                value = 0.0
            values[key] = value if value > 0 else float(spec.default_width)
        return values

    def _load_widths(self) -> dict:
        return {key: self._clamp(self.specs[key], value)
                for key, value in self._load_stored().items()}

    @staticmethod
    def _clamp(spec: ColumnSpec, width) -> int:
        return max(spec.min_width, min(spec.max_width, int(width)))

    def width(self, key: str) -> int:
        return self._widths[key]

    @property
    def dragging(self) -> bool:
        """True while a divider is held (LSR-M5: a resize then waits)."""
        return self._drag is not None

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
        # The weights, not the drawn widths: a list held partly at its floors
        # draws widths that are not its shape, and saved values load as
        # weights (LSR2-D8).
        stored.update({k: round(v) for k, v in self._weights.items()})
        setattr(self.settings, self._setting_attr(), stored)
        self.settings.save()

    # --------------------------------------------------------------- fitting
    def fit_to_width(self, available: int) -> int:
        """Share `available` pixels across the resizable columns. Returns overflow.

        Purpose: UPD-F4.1/F4.2/F4.3 — a panel that grew or shrank hands the
                 difference to its resizable columns in proportion to the
                 widths they already have, never below the five-character
                 floor, with the fixed columns reserved out first.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
        Tests:   tests/test_unified_panel_design.py::test_updf41_a_divider_move_rescales_every_resizable_column

        A column's stored width is treated as a weight rather than a pixel
        promise. That is what lets a drag and a resize coexist: the drag
        writes a pixel width, which becomes the weight the next resize shares
        the panel out by, so the *shape* the user set survives a window of a
        different size (UPD-F4.6). The weights are `_weights`, kept apart
        from the drawn `_widths`: a fit never writes them, so columns that
        reach their floor on the way down keep their share (LSR2-D6).

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
            # The weights are not touched, so the shape comes back when the
            # panel is wide enough again (UPD-F4.3, LSR2-D6).
            floored = {k: floors[k] for k in order}
            if floored != {k: self._widths[k] for k in order}:
                self._widths.update(floored)
                self._apply_all()
            return floor_total - budget

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
            weight = sum(self._weights[k] for k in free)
            if weight <= 0:
                # Nothing to go by; equal shares is the only honest answer.
                weight = len(free)
                shares = {k: remaining / len(free) for k in free}
            else:
                shares = {k: remaining * self._weights[k] / weight for k in free}

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
            # Pixels per unit of weight, for a drag made later while the
            # other columns are all held (`_set_weight_from_drag`).
            if weight > 0 and remaining > 0:
                self._px_per_weight = remaining / weight
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
    def build_dividers(self, header_frame, header_labels, height=22, fg_color=None,
                       header_texts=None, header_char_px=None) -> None:
        """Add a draggable divider at each resizable column's right edge.

        header_labels maps column key -> the header CTkLabel (so its width can be
        kept in sync during a drag). header_texts, when given, maps a key to
        its full heading, which is then cut to the column's width at
        header_char_px: a label grows to fit its text, so a heading wider
        than its column pushes every heading after it out of line with the
        rows (LSR2 sweep). Callers that pass neither are unaffected.
        """
        self._header = (header_frame, dict(header_labels))
        self._header_texts = dict(header_texts or {})
        self._header_char_px = header_char_px or self.char_px
        for key in self._header_texts:
            self._cut_heading(key)
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

    def add_cells(self, frame, cells) -> None:
        """Add cells to a row already registered, in `register_row`'s shape."""
        for row_frame, norm in reversed(self._rows):
            if row_frame is frame:
                for cell in cells:
                    key, label = cell[0], cell[1]
                    full = cell[2] if len(cell) > 2 else None
                    reserve = cell[3] if len(cell) > 3 else 0
                    width_delta = cell[4] if len(cell) > 4 else 0
                    norm.append((key, label, full, reserve, width_delta))
                return
        raise ValueError("add_cells: the row was never registered")

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
            self._apply_live(k)

    def _on_stop(self, event, key) -> None:
        drag, self._drag = self._drag, None
        if drag is not None and self._widths[drag[0]] != drag[2]:
            self._set_weight_from_drag(drag[0], drag[2])
            self._persist()
        if self.on_drag_end is not None:
            self.on_drag_end()

    def _set_weight_from_drag(self, key, start_width) -> None:
        """Turn the dragged width into a weight, leaving the other weights alone.

        Purpose: LSR2-D6 — only the column dragged changes its share. A
                 click with no motion changes nothing (the caller checks).
        Spec:    docs/unused-docs/implementation_plan_2026-11-14_all_columns_resize.md
        Tests:   tests/test_list_screen_resize.py::test_lsr2m4b_a_drag_changes_only_its_own_weight

        When no other column is held at its floor or its maximum, the drawn
        widths become the weights. With `fill_after_drag` the other columns
        are then scaled to fill the total they shared before the drag, so the
        refit that follows keeps the dragged column at the width it was
        dropped at; without the scaling the refit shrank it with the rest and
        it slid back from the cursor (SCR sweep, 2026-11-14). When some are
        held, their drawn widths
        are not their shares: the dragged width is converted into weight
        units by the columns that are still sharing freely, or, when every
        other column is held, by the scale of the last fit that shared
        (UPD-F4.3).
        """
        floors = {k: max(self.specs[k].min_width, min_column_width(self.char_px))
                  for k in self.order if self.specs[k].resizable}
        others = [k for k in floors if k != key]
        free = [k for k in others
                if floors[k] < self._widths[k] < self.specs[k].max_width]
        if len(free) == len(others):
            dropped = self._widths[key]
            # The total the columns shared before the drag.
            budget = sum(self._widths[k] for k in floors) - (dropped - start_width)
            others_weight = sum(self._widths[k] for k in others)
            self._weights = {k: self._widths[k] for k in self._weights}
            rest = budget - dropped
            if self.fill_after_drag and others and others_weight > 0 and rest > 0:
                # In pixels at that total: the dragged column at the width it
                # was dropped at, the others scaled to fill the rest. So what
                # is saved for it is the width the user set.
                for k in others:
                    self._weights[k] = self._widths[k] * rest / others_weight
            self._px_per_weight = 1.0
            return
        weight = sum(self._weights[k] for k in free)
        if free and weight > 0:
            scale = sum(self._widths[k] for k in free) / weight
        else:
            scale = self._px_per_weight
        self._weights[key] = self._widths[key] / scale

    def _cut_heading(self, key) -> None:
        """Cut a heading registered with `build_dividers` to its column."""
        full = self._header_texts.get(key)
        label = self._header[1].get(key) if self._header is not None else None
        if full is None or label is None or not label.winfo_exists():
            return
        label.configure(text=format_column_text(
            full, chars_for_width(self._widths[key], self._header_char_px)))

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
                self._cut_heading(key)

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
