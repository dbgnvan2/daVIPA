"""CIP-M6 -- the Plan screen's week: seven read-only columns of half hours.

Purpose: CIP-M6.1 (the week, meetings against free time) and CIP-M6.2 (each
         column is the day grid's own build). The counting is
         ``plan_week.py``; this module draws it and handles the toggle.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_week.md
Tests:   tests/test_plan_screen_week.py

The week draws into the day pane's own scroll frame, so the day's drop targets
(``_slot_frames``, ``_virtual_frames``) are emptied while it is up: a drag
released over the week finds no box and changes nothing. Clicking a column
opens that date as a day, which is where planning happens.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Tuple

import customtkinter as ctk

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
from ..time_block_layout import SLOT_MINUTES, format_hhmm

logger = logging.getLogger(__name__)

DAY_VIEW = "Day"
WEEK_VIEW = "Week"
WEEK_BOX_HEIGHT_PX = 12
WEEK_COLUMN_WIDTH_PX = 64
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
    parts = [f"Meetings {hours_text(meetings)}"
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
        # The week set this to 0 for its narrow columns; the day's one
        # column fills the pane.
        self.blocks_scroll.grid_columnconfigure(0, weight=1)

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
            self.day_heading.configure(text="Week Plan")
            self.day_summary.configure(text=week_total_text(summaries))
            self._draw_week_strip(fetches)
            self._draw_week_grid(summaries)
        except Exception as error:  # noqa: BLE001 - said, not a blank pane (P2)
            logger.warning("CIP-M6: week from %s unreadable: %s", self.selected_date, error)
            self._week_fetches = []
            self._week_summaries = []
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
        rows = week_rows(summaries)

        back = ctk.CTkButton(grid, text="‹", width=28, command=lambda: self.step_week(-1))
        back.grid(row=0, column=0, padx=2, pady=(0, 4))
        forward = ctk.CTkButton(grid, text="›", width=28, command=lambda: self.step_week(1))
        forward.grid(row=0, column=WEEK_DAYS + 1, padx=2, pady=(0, 4))
        self.week_back_button, self.week_forward_button = back, forward

        for offset, index in enumerate(rows, start=1):
            minutes = self.bounds.day_start_minutes + index * SLOT_MINUTES  # as day_grid
            if minutes % 60 == 0:
                ctk.CTkLabel(
                    grid, text=format_hhmm(minutes), font=small,
                    text_color=palette["muted_text"], height=WEEK_BOX_HEIGHT_PX,
                ).grid(row=offset, column=0, sticky="e", padx=(0, 4))

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
                box = ctk.CTkFrame(
                    grid, width=WEEK_COLUMN_WIDTH_PX, height=WEEK_BOX_HEIGHT_PX,
                    corner_radius=2,
                    fg_color=colors[kind] if kind else "transparent",
                )
                box.grid(row=offset, column=column, padx=1, pady=1)
                if kind:
                    self._bind_open(box, day)
                    self._week_boxes[(day, index)] = (box, kind)
            total = ctk.CTkLabel(
                grid, text=column_total_text(summary), font=small,
                text_color=palette["muted_text"], justify="center",
                width=WEEK_COLUMN_WIDTH_PX,
            )
            total.grid(row=len(rows) + 1, column=column, padx=1, pady=(4, 0))
            self._bind_open(total, day)
            self._week_totals[day] = total

    def _bind_open(self, widget, day: str) -> None:
        # After the click, not in it: open_day destroys the widget whose
        # handler is running (the rule ``on_drag_release`` follows).
        widget.bind("<Button-1>", lambda _event, d=day: self.after_idle(lambda: self.open_day(d)))
