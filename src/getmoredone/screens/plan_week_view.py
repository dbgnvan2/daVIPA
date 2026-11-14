"""CIP-M6 -- the Plan screen's week: seven columns of half hours.

Purpose: CIP-M6.1 (the week, meetings against free time), CIP-M6.2 (each
         column is the day grid's own build), CIP-M6.3 (the columns follow the
         pane), CIP-M6.4 (a box is its item's Category colour) and CIP-M6.5 (an
         Action Item dropped on a box is blocked on that box's date). The
         counting is ``plan_week.py``; this module draws it.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
Plan:    docs/unused-docs/implementation_plan_2026-11-14_plan_week_improvements.md
Tests:   tests/test_plan_screen_week.py

The week draws into the day pane's own scroll frame, so the day's drop targets
(``_slot_frames``, ``_virtual_frames``) are emptied while it is up. The week's
own boxes are the targets instead (``_week_boxes``), and an item dropped on one
goes through the day's checks for that box's date. Every other write stays on
the day: clicking a column opens it.
"""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import tkinter as tk

import customtkinter as ctk

from ..calendar_commitments import committed_slots
from ..plan_week import (
    FREE,
    MEETING,
    PLANNED,
    UNREAD,
    WEEK_DAYS,
    hours_text,
    read_week,
    week_age_text,
    week_dates,
    week_rows,
)
from ..color_contrast import normalize_hex_color, pick_text_color
from ..theme import block_type_colors, semantic_colors, status_text_color
from ..models import BlockType
from ..time_block_layout import (
    SLOT_MINUTES,
    SlotRefusedError,
    build_day_grid,
    can_place,
    format_hhmm,
    slots_for_minutes,
)
from .drag_schedule_support import widget_contains_pointer

logger = logging.getLogger(__name__)

DAY_VIEW = "Day"
WEEK_VIEW = "Week"
#: CIP-M6.3 -- the floors. Above them the boxes follow the pane. The height
#: floor is not a constant: it is the title's line plus the drag outline
#: above and below it plus a margin (``week_box_floor``).
DRAG_HOVER_BORDER_PX = 2  # the outline a box gets while a drag is over it
WEEK_TITLE_MARGIN_PX = 1
WEEK_COLUMN_WIDTH_PX = 40
WEEK_BOX_PAD_PX = 2  # pady=1 above and below each box
WEEK_COLUMN_PAD_PX = 2  # padx=1 either side of each column
WEEK_LABEL_PAD_PX = 4  # the time labels' and arrows' padx
WEEK_TITLE_FONT_SIZE = 9
WEEK_TITLE_INSET_PX = 3  # each side of a title inside its box
ELLIPSIS = "…"


def fit_text(text: str, measure, width: int) -> str:
    """``text`` cut to ``width`` pixels with "…", by ``measure`` (a font's).

    The longest prefix that fits with the ellipsis; just "…" when nothing
    does, and "" when not even that fits.
    """
    if measure(text) <= width:
        return text
    if measure(ELLIPSIS) > width:
        return ""
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if measure(text[:middle].rstrip() + ELLIPSIS) <= width:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + ELLIPSIS


def short_date(day: str) -> str:
    """"Fri 20" -- how the week names a date in its headings and status."""
    return date.fromisoformat(day).strftime("%a %d")


def block_label(block) -> str:
    """What a status line calls a block: its label, else its kind."""
    return block.label or str(block.block_type).title()


def week_box_floor(linespace: int, scaling: float = 1.0) -> int:
    """The least box height that shows a title of ``linespace`` px whole.

    Its line, clear of the drag outline at top and bottom, with a margin.
    ``linespace`` is real pixels of the scaled title font; the result is in
    CustomTkinter units, which the box multiplies by ``scaling``.
    """
    line = math.ceil(linespace / scaling)
    return line + 2 * DRAG_HOVER_BORDER_PX + WEEK_TITLE_MARGIN_PX


def week_title_text(title: str, others: int) -> str:
    """What a box says: the title, and "+N" for the others starting with it."""
    return f"{title} +{others}" if others else title


def fit_title(title: str, others: int, measure, width: int) -> str:
    """``week_title_text`` cut to ``width``, keeping "+N" whole.

    The title is cut, not the count, so a long title still says how many
    others start with it. When no part of the title fits, the count alone.
    """
    if not others:
        return fit_text(title, measure, width)
    whole = week_title_text(title, others)
    if measure(whole) <= width:
        return whole
    suffix = f" +{others}"
    head = fit_text(title, measure, width - measure(suffix))
    if head:
        return head + suffix
    count = f"+{others}"
    return count if measure(count) <= width else ""
#: What the grid spends on height that is not boxes: the heading row and up
#: to four lines of totals under each column. CustomTkinter units: those are
#: CTk labels, which scale with the window.
WEEK_CHROME_HEIGHT_PX = 100
#: The header buttons that write to the selected day. Disabled in the week.
WEEK_LOCKED_BUTTONS = ("btn_clear_day", "btn_autoload", "btn_add_buffer", "btn_add_break")


def week_box_colors() -> Dict[str, str]:
    """One existing token per kind of box; no new colour (AGENTS.md)."""
    palette = semantic_colors()
    return {
        MEETING: palette["commitment"],
        PLANNED: block_type_colors()["lunch"],
        FREE: palette["surface_subtle"],
        UNREAD: palette["border"],
    }


def column_total_text(summary) -> str:
    """The lines under a column (W4, W7, W8), then what no box shows.

    An unread date's meetings are not known, so they are "—", not "0h".
    """
    meetings = f"Meetings {hours_text(summary.meeting_minutes if summary.read else None)}"
    if not summary.read:
        lines = [meetings, "not read"]
    elif not summary.block_day:
        lines = [meetings, "no blocks"]
    else:
        lines = [meetings, f"Free {hours_text(summary.free_minutes)}"]
    # P2 -- a block outside the day and an all-day event hold no box here.
    if summary.outside:
        lines.append(f"{summary.outside} outside")
    if summary.all_day:
        lines.append(f"{summary.all_day} all-day")
    return "\n".join(lines)


def week_total_text(summaries) -> str:
    """The summary line: meetings and free time, each over the days it is known for."""
    read = [summary for summary in summaries if summary.read]
    meetings = sum(summary.meeting_minutes for summary in read)
    known = [summary.free_minutes for summary in summaries if summary.free_minutes is not None]
    parts = [f"Meetings {hours_text(meetings if read else None)}"
             + ("" if len(read) == len(summaries) else f" on {len(read)} of {len(summaries)} days")]
    if known:
        parts.append(f"free {hours_text(sum(known))} on {len(known)} of {len(summaries)} days")
    else:
        parts.append("free time not known")
    return "  ·  ".join(parts)


class PlanWeekViewMixin:
    """The Day/Week toggle and the week's drawing. Needs a ``PlanScreen``."""

    def create_view_toggle(self, frame) -> None:
        """W1 -- in the day pane's heading row, not the Plan header."""
        self.view_toggle = ctk.CTkSegmentedButton(
            frame, values=[DAY_VIEW, WEEK_VIEW], command=self.set_view_mode
        )
        self.view_toggle.set(DAY_VIEW)
        self.view_toggle.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="e")

    def refused_in_week(self) -> bool:
        """The day's write buttons say no while the week is up (CIP sweep, batch 3).

        They place by the day grid and the meetings of the last day drawn,
        which the week does not rebuild; and which day they would act on is
        not what the screen shows.
        """
        if not getattr(self, "_week_mode", False):
            return False
        self.set_status(
            "In the week, drag an Action Item or a Time Block — click a date to open the day",
            "muted",
        )
        return True

    def _set_day_buttons(self, state: str) -> None:
        for name in WEEK_LOCKED_BUTTONS:
            button = getattr(self, name, None)
            if button is not None:
                button.configure(state=state)
        # The export disables its own button while it runs; leaving the week
        # mid-export must not give it back early (re-sweep, batch 3).
        export = getattr(self, "btn_export_calendar", None)
        if export is not None and not (state == "normal" and getattr(self, "_export_running", False)):
            export.configure(state=state)

    def set_view_mode(self, value: str) -> None:
        week = value == WEEK_VIEW
        if week == self._week_mode:
            return
        if week:
            self._week_mode = True
            self._set_day_buttons("disabled")
        else:
            self._leave_week()
        self.load_blocks()

    def open_day(self, day: str) -> None:
        """A click on a column: that date, as a day."""
        self._leave_week()
        if day == self.selected_date:
            self.load_blocks()
        else:
            # Calls on_date_changed, which redraws.
            self.date_picker.set_date(day)

    def _leave_week(self) -> None:
        self._week_mode = False
        self._week_fetches = []
        self._week_summaries = []
        self._set_day_buttons("normal")
        self.view_toggle.set(DAY_VIEW)
        self.day_heading.configure(text="Day Plan")
        # The week set column 0 to 0 for its time labels and spread 1-7 over
        # the pane (M6.3); the day's one column fills it.
        self.blocks_scroll.grid_columnconfigure(0, weight=1)
        for column in range(1, WEEK_DAYS + 2):
            self.blocks_scroll.grid_columnconfigure(column, weight=0, uniform="", minsize=0)
        # The week's floor is gone; give the items pane its width back.
        self._week_width_need = 0
        self.apply_items_width(self.items_col_width())

    def step_week(self, weeks: int) -> None:
        """W3 -- ‹ and › move by seven days."""
        start = date.fromisoformat(self.selected_date) + timedelta(days=WEEK_DAYS * weeks)
        self.date_picker.set_date(start.isoformat())

    def load_week(self) -> None:
        """Draw the seven columns from the cache. No network, no writes."""
        try:
            self._clear_day_pane()
            summaries, fetches = read_week(self.db_manager, self.selected_date, self.bounds)
            self._week_fetches = fetches
            self._week_summaries = summaries
            self._week_error = None
            self.day_heading.configure(text="Week Plan")
            self.day_summary.configure(text=week_total_text(summaries))
            self._draw_week_strip(fetches)
            self._draw_week_grid(summaries)
            self._bind_week_resize()
        except Exception as error:  # noqa: BLE001 - said, not a blank pane (P2)
            logger.warning("CIP-M6: week from %s unreadable: %s", self.selected_date, error)
            self._week_fetches = []
            self._week_summaries = []
            self._week_error = str(error) or type(error).__name__
            self._week_width_need = 0
            self.set_status(f"The week could not be read: {error}", "error")
        finally:
            self._flush_redraw()
        if self._week_error is None:
            self.fit_week_columns()
        self.maybe_auto_refresh()

    def _clear_day_pane(self) -> None:
        for widget in self.blocks_scroll.winfo_children():
            widget.destroy()
        for widget in self.outside_frame.winfo_children():
            widget.destroy()
        self.outside_frame.grid_remove()
        for holder in (self.earlier_holder, self.later_holder):
            for widget in holder.winfo_children():
                widget.destroy()
        self._slot_frames = []
        self._virtual_frames = []
        self._block_widgets = []
        self._week_boxes: Dict[Tuple[str, int], Tuple[object, str]] = {}
        self._week_hour_labels: List[object] = []
        self._week_empty_boxes: List[object] = []
        self._week_titles: Dict[Tuple[str, int], object] = {}
        self._week_totals: Dict[str, object] = {}
        self._week_headers: Dict[str, object] = {}

    def _draw_week_strip(self, fetches) -> None:
        from .plan_commitments import age_text

        for widget in self.commitment_strip.winfo_children():
            widget.destroy()
        self._strip_labels = []
        text, kind = week_age_text(fetches, age_text)
        self.calendar_age_label = ctk.CTkLabel(
            self.commitment_strip, text=text, anchor="w",
            text_color=status_text_color(kind), font=ctk.CTkFont(size=11),
        )
        self.calendar_age_label.grid(row=0, column=0, sticky="w")

    def _draw_week_grid(self, summaries: List) -> None:
        palette = semantic_colors()
        colors = week_box_colors()
        small = ctk.CTkFont(size=10)
        grid = self.blocks_scroll
        grid.grid_columnconfigure(0, weight=0)
        # M6.3 -- the seven share the width equally and never go below the floor.
        for column in range(1, WEEK_DAYS + 1):
            grid.grid_columnconfigure(
                column, weight=1, uniform="week", minsize=WEEK_COLUMN_WIDTH_PX
            )
        rows = week_rows(summaries)
        self._week_row_count = len(rows)
        height = self._week_box_px = self.week_box_height()
        fill_for = self._week_fill_resolver(summaries)
        title_for = fill_for.title

        # After the click: the redraw destroys the button whose click runs.
        back = ctk.CTkButton(
            grid, text="‹", width=28, command=lambda: self.after_idle(lambda: self.step_week(-1))
        )
        back.grid(row=0, column=0, padx=2, pady=(0, 4))
        forward = ctk.CTkButton(
            grid, text="›", width=28, command=lambda: self.after_idle(lambda: self.step_week(1))
        )
        forward.grid(row=0, column=WEEK_DAYS + 1, padx=2, pady=(0, 4))
        self.week_back_button, self.week_forward_button = back, forward

        for offset, index in enumerate(rows, start=1):
            minutes = self.bounds.day_start_minutes + index * SLOT_MINUTES  # as day_grid
            if minutes % 60 == 0:
                label = ctk.CTkLabel(
                    grid, text=format_hhmm(minutes), font=small,
                    text_color=palette["muted_text"], height=height,
                )
                label.grid(row=offset, column=0, sticky="e", padx=(0, 4))
                self._week_hour_labels.append(label)

        for column, summary in enumerate(summaries, start=1):
            day = summary.day
            heading = ctk.CTkLabel(
                grid, text=date.fromisoformat(day).strftime("%a %d"),
                width=WEEK_COLUMN_WIDTH_PX, font=ctk.CTkFont(size=11, weight="bold"),
                cursor="hand2",
            )
            heading.grid(row=0, column=column, padx=1, pady=(0, 4))
            self._bind_open(heading, day)
            self._week_headers[day] = heading
            kinds = dict(summary.boxes)
            for offset, index in enumerate(rows, start=1):
                kind = kinds.get(index)
                fill = colors[kind] if kind else "transparent"
                if kind == PLANNED:
                    fill = fill_for(summary.items.get(index)) or fill
                box = ctk.CTkFrame(
                    grid, width=WEEK_COLUMN_WIDTH_PX, height=height,
                    corner_radius=2, fg_color=fill,
                )
                box.grid(row=offset, column=column, padx=1, pady=1, sticky="ew")
                start = summary.starts.get(index) if kind == PLANNED else None
                if start is not None:
                    self._draw_week_title(box, day, index, fill, start, title_for)
                if kind:
                    # CIP-M6.8 -- only the date heading opens the day. A box
                    # holding a block picks it up instead (M6.7).
                    picked = summary.blocks.get(index) if kind == PLANNED else None
                    self._bind_week_block_drag(box, picked)
                    title_label = self._week_titles.get((day, index))
                    if title_label is not None:
                        self._bind_week_block_drag(title_label, picked)
                    self._week_boxes[(day, index)] = (box, kind)
                else:
                    self._week_empty_boxes.append(box)
            total = ctk.CTkLabel(
                grid, text=column_total_text(summary), font=small,
                text_color=palette["muted_text"], justify="center",
                width=WEEK_COLUMN_WIDTH_PX,
            )
            total.grid(row=len(rows) + 1, column=column, padx=1, pady=(4, 0))
            self._week_totals[day] = total

    # ---------------------------------------------------------- M6.4 colours
    def _week_fill_resolver(self, summaries: List):
        """A function from an item id to its Category colour, or ``None``.

        The lookup the day's chips use (``_segment_color_resolver``). The
        items are read once per draw, not once per box.
        """
        color_for = self._segment_color_resolver()
        known = {item.id: item for item in getattr(self, "_items", [])}
        wanted = {item_id for summary in summaries for item_id in summary.items.values()}
        for item_id in wanted - set(known):
            item = self.db_manager.get_action_item(item_id)
            if item is not None:
                known[item_id] = item

        def fill(item_id):
            item = known.get(item_id) if item_id else None
            return color_for(item) if item is not None else None

        def title(item_id, label):
            """The item's title now; the block's own label if it is gone."""
            item = known.get(item_id)
            return item.title if item is not None and item.title else label

        fill.title = title
        return fill

    # ----------------------------------------------------------- M6.6 titles
    def _draw_week_title(self, box, day: str, index: int, fill: str, start, title_for) -> None:
        """The item's title on the box its block starts in, cut to the box.

        A plain Tk label placed in the box: placing never asks the box to
        grow, so a long title cannot widen its column, and its text is re-cut
        whenever the box changes width. Its colour is derived from the fill
        for contrast (AGENTS.md: a data colour is a fill only where that is so).
        """
        background = normalize_hex_color(fill)
        if background is None:
            return
        item_id, label, others = start
        title = title_for(item_id, label)
        full = week_title_text(title, others)
        font = self.week_title_font()
        text = tk.Label(
            box, text="", font=font, anchor="w", padx=0, pady=0, bd=0,
            bg=background, fg=pick_text_color(background),
        )
        # place() is real pixels, so the inset is scaled as the box is.
        inset = round(WEEK_TITLE_INSET_PX * self.week_scaling())
        text.place(x=inset, rely=0.5, anchor="w", relwidth=1, width=-2 * inset)
        text.full_title = full
        text.title_parts = (title, others)
        text.title_font = font
        text.bind("<Configure>", lambda event, w=text: self._fit_week_title(w, event.width))
        self._fit_week_title(text, round(WEEK_COLUMN_WIDTH_PX * self.week_scaling()) - 2 * inset)
        self._week_titles[(day, index)] = text

    @staticmethod
    def _fit_week_title(label, width: int) -> str:
        title, others = label.title_parts
        fitted = fit_title(title, others, label.title_font.measure, width)
        if label.cget("text") != fitted:
            label.configure(text=fitted)
        return fitted

    # ----------------------------------------------------------- M6.3 resize
    def fit_week_columns(self) -> int:
        """Hold each column at its widest heading or totals text (M6.3).

        Measured after the flush, when the labels have their requested
        widths. The day pane's floor then follows (``day_width_floor``), so
        the divider cannot squeeze the week until its text is cut off.
        Returns the column width set.
        """
        texts = list(self._week_headers.values()) + list(self._week_totals.values())
        column = max([WEEK_COLUMN_WIDTH_PX] + [label.winfo_reqwidth() for label in texts])
        for index in range(1, WEEK_DAYS + 1):
            self.blocks_scroll.grid_columnconfigure(index, minsize=column)
        side = [self.week_back_button] + self._week_hour_labels
        self._week_width_need = (
            max(widget.winfo_reqwidth() for widget in side) + WEEK_LABEL_PAD_PX
            + WEEK_DAYS * (column + WEEK_COLUMN_PAD_PX)
            + self.week_forward_button.winfo_reqwidth() + WEEK_LABEL_PAD_PX
        )
        # The setting, not the width drawn: a narrower week must not ratchet
        # the items pane down (as on_resize).
        self.apply_items_width(self.items_col_width())
        return column

    def week_width_need(self) -> int:
        """What the week's grid needs across, or 0 outside the week."""
        return getattr(self, "_week_width_need", 0) if self._week_mode else 0

    def week_scaling(self) -> float:
        """CustomTkinter's widget scaling for this screen (1 on a Mac)."""
        return self._get_widget_scaling()

    def week_title_font(self):
        """The one font every week title uses, at the widget scaling.

        A plain Tk label gets no scaling from CustomTkinter, so the font is
        scaled here the way a CTk label scales its own. Made again only when
        the scaling has changed.
        """
        scaling = self.week_scaling()
        cached = getattr(self, "_week_title_font", None)
        if cached is None or cached[0] != scaling:
            # A CTkFont's size is pixels (negative to Tk), and round() is how
            # CTkFont.create_scaled_tuple scales one for a CTk label.
            size = round(WEEK_TITLE_FONT_SIZE * scaling)
            cached = self._week_title_font = (scaling, ctk.CTkFont(size=size))
        return cached[1]

    def week_box_min_height(self) -> int:
        """The floor for this screen's title font (``week_box_floor``)."""
        return week_box_floor(
            self.week_title_font().metrics("linespace"), self.week_scaling()
        )

    def week_box_height(self) -> int:
        """Box height for the pane's visible height, never below the floor."""
        floor = self.week_box_min_height()
        canvas = self._day_canvas()
        rows = getattr(self, "_week_row_count", 0)
        if canvas is None or rows <= 0:
            return floor
        # The canvas is measured in real pixels; a box's height and its pady
        # are CustomTkinter units, which the box multiplies by the scaling.
        room = canvas.winfo_height() / self.week_scaling() - WEEK_CHROME_HEIGHT_PX
        return max(floor, int(room // rows) - WEEK_BOX_PAD_PX)

    def _bind_week_resize(self) -> None:
        canvas = self._day_canvas()
        if canvas is None or getattr(self, "_week_resize_bound", False):
            return
        canvas.bind("<Configure>", lambda _event: self.fit_week_boxes(), add="+")
        self._week_resize_bound = True

    def fit_week_boxes(self) -> bool:
        """Re-height the drawn boxes for the pane. True when anything changed.

        Only on a change: this runs from ``<Configure>``, and setting a size
        that fires another ``<Configure>`` must settle (as apply_items_width).
        Width needs nothing here; the column weights carry it.
        """
        if not self._week_mode:
            return False
        height = self.week_box_height()
        if height == getattr(self, "_week_box_px", None):
            return False
        self._week_box_px = height
        for box, _kind in self._week_boxes.values():
            box.configure(height=height)
        for widget in self._week_empty_boxes + self._week_hour_labels:
            widget.configure(height=height)
        return True

    # ------------------------------------------------------------- M6.5 drop
    def week_box_under_pointer(self) -> Optional[Tuple[str, int]]:
        """``(date, slot index)`` of the week box under the pointer, or ``None``."""
        x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
        if not widget_contains_pointer(self.blocks_scroll, x_root, y_root):
            return None
        for key, (box, _kind) in self._week_boxes.items():
            if widget_contains_pointer(box, x_root, y_root):
                return key
        return None

    def week_box_frame(self, key) -> Optional[object]:
        entry = self._week_boxes.get(key) if key is not None else None
        return entry[0] if entry else None

    def drop_on_week(self, item) -> None:
        """An Action Item released over the week: the day's checks, for that date.

        Read now, refuse now, ask now, write after the handler returns -- the
        order ``on_drag_release`` keeps for the day, for the same reasons.
        """
        hit = self.week_box_under_pointer()
        if hit is None:
            if self.pointer_over_day():
                self.set_status("Drop on a box to plan it — click a date to open it", "muted")
            return
        day, index = hit
        refusal = self._unplaced_refusal(day) or self._drop_refusal(item, index, day)
        if refusal is not None:
            self.set_status(refusal, "warning")
            return
        if not self._allow_this_day(day):
            return
        self.after_idle(lambda: self.block_item(item, index, day))

    def _unplaced_refusal(self, day: str) -> Optional[str]:
        """Why a drop on ``day`` must wait for the day to be opened, if it must.

        Sweep, 2026-11-14 -- the day places blocks from an earlier version
        (TG-M5) when it is opened, and the week runs no repair. A drop before
        that could take the box such a block is about to be given.
        """
        unplaced = sum(1 for block in self.db_manager.get_time_blocks(day) if block.slot_index is None)
        if not unplaced:
            return None
        return (
            f"Open {short_date(day)} first — {unplaced}"
            " block(s) from an earlier version need a box"
        )

    # ------------------------------------------------------- M6.7 block drag
    def _bind_week_block_drag(self, widget, block) -> None:
        """A press on a week box picks up its block; nothing else happens.

        No block (a meeting, lunch, free) binds nothing, so a click there does
        nothing: only the date heading opens the day (M6.8). A press with no
        motion shows no label (PD-M10.3), so a plain click on a box is not a
        drag either.
        """
        if block is None:
            return
        widget.bind("<ButtonPress-1>", lambda event, b=block: self.start_block_drag(event, b))
        widget.bind("<B1-Motion>", self.on_drag_motion)
        widget.bind("<ButtonRelease-1>", self.on_drag_release)

    def _item_on_date_refusal(self, block, day: str) -> Optional[str]:
        """PF-M2 for a moved block: its item already has a block on ``day``."""
        if day == block.block_date or block.block_type != BlockType.ITEM or not block.item_id:
            return None
        sitting = self._blocked_today(block.item_id, day)
        if sitting is None:
            return None
        return (
            f"{block_label(block)} is already in a Time Block on {short_date(day)}"
            f" at {sitting.start_time} — drag that Time Block to move it"
        )

    def _block_move_refusal(self, block, index: int, day: str) -> Optional[str]:
        """Why moving ``block`` to this box would write nothing, or ``None``.

        Read, not enforced: ``move_block_to_day`` and
        ``db_manager.move_block_to_date`` check again, as the write paths.
        """
        from .plan import refusal_text  # plan.py imports this module

        refusal = self._item_on_date_refusal(block, day)
        if refusal is not None:
            return refusal
        span, committed = self._placement_for(day)
        reason = can_place(
            self.db_manager.get_time_blocks(day),
            self.bounds,
            index,
            slots_for_minutes(block.planned_minutes),
            ignoring=block.id,
            day_span=span,
            committed=committed,
        )
        return refusal_text(reason) if reason else None

    def drop_block_on_week(self, block) -> None:
        """A Time Block released over the week: moved to that box's date.

        Read now, refuse now, ask now, write after the handler returns -- the
        order ``drop_on_week`` keeps. The non-work-day question is asked only
        when the date changes: moving a block within its day never asked.
        """
        hit = self.week_box_under_pointer()
        if hit is None:
            if self.pointer_over_day():
                self.set_status("Drop on a box to move it — click a date to open it", "muted")
            return
        day, index = hit
        refusal = self._unplaced_refusal(day) or self._block_move_refusal(block, index, day)
        if refusal is not None:
            self.set_status(refusal, "warning")
            return
        if day != block.block_date and not self._allow_this_day(day):
            return
        self.after_idle(lambda: self.move_block_to_day(block, index, day))

    def move_block_to_day(self, block, index: int, day: str) -> None:
        """CIP-M6.7 -- the write behind a week block drop, and its status."""
        from .plan import refusal_text  # plan.py imports this module

        moving_date = day != block.block_date
        if moving_date and not self._require_block_day(ask=False, day=day):
            return
        refusal = self._item_on_date_refusal(block, day)
        if refusal is not None:
            self._non_work_day = False
            self.set_status(refusal, "warning")
            return
        was_exported = bool(getattr(block, "calendar_event_id", None))
        old_day = block.block_date
        try:
            moved = self.db_manager.move_block_to_date(
                block.id, day, index, self.bounds, day_span=self._placement_for(day)[0]
            )
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self.refresh()
        text = f"Moved {block_label(block)} to {short_date(day)} at {moved.start_time}"
        if not self._week_day_read(day):
            text += " — calendar not read for that day"
        if moving_date:
            text += self._take_non_work_note(day)
            if was_exported:
                text += f" — export {short_date(old_day)} again to remove it from Google Calendar"
        self.set_status(text, "success")

    def _placement_for(self, day: str):
        """``(span, committed)`` the placement rules read for ``day``.

        The day on screen keeps what it drew. A week date uses the grid its
        column was counted from (M6.2), and any other date is built the same
        way ``read_week`` builds it.
        """
        if not self._week_mode and day == self.selected_date:
            return self._grid.span, self._committed
        for summary in self._week_summaries:
            if summary.day == day and summary.grid is not None:
                return summary.grid.span, summary.grid.committed
        grid = build_day_grid(
            self.db_manager.get_time_blocks(day), self.bounds,
            committed=committed_slots(self.db_manager.get_commitments(day), self.bounds),
        )
        return grid.span, grid.committed

    def _week_day_read(self, day: str) -> bool:
        for summary in self._week_summaries:
            if summary.day == day:
                return summary.read
        return True

    def _bind_open(self, widget, day: str) -> None:
        # After the click, not in it: open_day destroys the widget whose
        # handler is running (the rule ``on_drag_release`` follows).
        widget.bind("<Button-1>", lambda _event, d=day: self.after_idle(lambda: self.open_day(d)))
