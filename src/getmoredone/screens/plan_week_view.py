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
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

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
from ..theme import block_type_colors, semantic_colors, status_text_color
from ..time_block_layout import SLOT_MINUTES, build_day_grid, format_hhmm
from .drag_schedule_support import widget_contains_pointer

logger = logging.getLogger(__name__)

DAY_VIEW = "Day"
WEEK_VIEW = "Week"
#: CIP-M6.3 -- the floors. Above them the boxes follow the pane.
WEEK_BOX_HEIGHT_PX = 12
WEEK_COLUMN_WIDTH_PX = 40
WEEK_BOX_PAD_PX = 2  # pady=1 above and below each box
#: What the grid spends on height that is not boxes: the heading row and up
#: to four lines of totals under each column.
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
        self.set_status("The week is read-only — click a day to plan it", "muted")
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
            self.set_status(f"The week could not be read: {error}", "error")
        finally:
            self._flush_redraw()
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
                if kind:
                    self._bind_open(box, day)
                    self._week_boxes[(day, index)] = (box, kind)
                else:
                    self._week_empty_boxes.append(box)
            total = ctk.CTkLabel(
                grid, text=column_total_text(summary), font=small,
                text_color=palette["muted_text"], justify="center",
                width=WEEK_COLUMN_WIDTH_PX,
            )
            total.grid(row=len(rows) + 1, column=column, padx=1, pady=(4, 0))
            self._bind_open(total, day)
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

        return fill

    # ----------------------------------------------------------- M6.3 resize
    def week_box_height(self) -> int:
        """Box height for the pane's visible height, never below the floor."""
        canvas = self._day_canvas()
        rows = getattr(self, "_week_row_count", 0)
        if canvas is None or rows <= 0:
            return WEEK_BOX_HEIGHT_PX
        room = canvas.winfo_height() - WEEK_CHROME_HEIGHT_PX
        return max(WEEK_BOX_HEIGHT_PX, room // rows - WEEK_BOX_PAD_PX)

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
                self.set_status("Drop on a box to plan it — click a day to open it", "muted")
            return
        day, index = hit
        refusal = self._drop_refusal(item, index, day)
        if refusal is not None:
            self.set_status(refusal, "warning")
            return
        if not self._allow_this_day(day):
            return
        self.after_idle(lambda: self.block_item(item, index, day))

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
