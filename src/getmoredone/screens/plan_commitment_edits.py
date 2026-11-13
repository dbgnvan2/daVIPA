"""The Plan screen changing a Google Calendar meeting: drag, length, rename, delete.

Purpose: CIP-M4 -- the screen half of the write. A mixin on ``PlanScreen``,
         so ``plan.py`` carries only the drag branch.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#7-m4--editing-the-calendar-from-inside-the-plan
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_editing.md

Every question is asked during the gesture, before any network call: a modal
opened from a timer or idle callback is what PD-M13 found raising on macOS.
The write runs on a worker; the grid changes only when it is collected and the
cache, written from Google's reply, is read again (M4.5).
"""

from __future__ import annotations

import gc
import logging
import threading
from tkinter import messagebox
from typing import List, Optional, Tuple

import customtkinter as ctk

from ..calendar_commitment_edits import (
    MOVE_ONTO_BLOCK,
    EditOutcome,
    EditRequest,
    check_request,
    length_of,
    move_refusal,
    movable,
    write_commitment_edit,
)
from ..models import CalendarCommitment
from ..time_block_layout import (
    DURATION_CHOICES,
    MAX_BLOCK_MINUTES,
    SLOT_MINUTES,
    SlotRefusal,
)
from .plan_commitments import (
    REFRESH_POLL_INTERVAL_MS,
    calendar_ready,
    claim_refresh,
    release_refresh,
    refresh_in_flight,
)

logger = logging.getLogger(__name__)

#: E5 -- why a meeting cannot take the boxes it was dropped on or sized to.
MOVE_REFUSAL_TEXT = {
    SlotRefusal.OUTSIDE_GRID: "That time is outside the day shown — the meeting was not moved",
    SlotRefusal.CROSSES_LUNCH: "That would put the meeting over lunch — the meeting was not moved",
    SlotRefusal.SLOT_FULL: "A Time Block is there — the meeting was not moved",
    SlotRefusal.SLOT_COMMITTED: "Another meeting holds that time — the meeting was not moved",
    MOVE_ONTO_BLOCK: "A Time Block is there — move it first; the meeting was not moved",
}
UNKNOWN_MOVE_REFUSAL = "The meeting cannot go there — it was not moved"

BUSY_TEXT = "Google Calendar is busy with another read or change — wait for it to finish"
NOT_READY_TEXT = (
    "Google Calendar is not connected — Settings → Google Calendar, then try again"
)
NOT_MOVABLE_TEXT = "All day or over midnight — cannot be moved here"


class PlanCommitmentEditsMixin:
    """Gestures that change a meeting in Google Calendar, for ``PlanScreen``."""

    # ------------------------------------------------------------- the menu

    def commitment_edit_entries(
        self, commitment: CalendarCommitment
    ) -> List[Tuple[str, Optional[object]]]:
        """What an editable meeting's menu offers. ``None`` is a disabled line.

        Purpose: M4.1 -- only a meeting the user may change offers changes;
                 E2 -- an all-day or over-midnight one offers no length.
        Tests:   tests/test_plan_screen_commitment_edits.py::test_cipm41_the_menu_of_an_uneditable_meeting_offers_no_edit
        """
        if not commitment.can_edit:
            return []
        entries: List[Tuple[str, Optional[object]]] = []
        if movable(commitment):
            current = length_of(commitment)
            for minutes in DURATION_CHOICES:
                entries.append((
                    f"{minutes} minutes" + ("  (now)" if minutes == current else ""),
                    lambda c=commitment, m=minutes: self.change_commitment(c, EditRequest(minutes=m)),
                ))
            entries.append(("Custom length…", lambda c=commitment: self.ask_commitment_minutes(c)))
        else:
            entries.append((NOT_MOVABLE_TEXT, None))
        entries.append(("Rename…", lambda c=commitment: self.ask_commitment_title(c)))
        entries.append((
            "Delete from Google Calendar…",
            lambda c=commitment: self.change_commitment(c, EditRequest(delete=True)),
        ))
        return entries

    def ask_commitment_minutes(self, commitment: CalendarCommitment) -> None:
        raw = ctk.CTkInputDialog(text="Meeting length in minutes:", title="Meeting Length").get_input()
        if raw is None:
            return
        try:
            minutes = int(str(raw).strip())
        except ValueError:
            self.set_status("Meeting length must be a whole number of minutes", "error")
            return
        if not 0 < minutes <= MAX_BLOCK_MINUTES:
            self.set_status(
                f"Meeting length must be between 1 and {MAX_BLOCK_MINUTES} minutes", "error"
            )
            return
        self.change_commitment(commitment, EditRequest(minutes=minutes))

    def ask_commitment_title(self, commitment: CalendarCommitment) -> None:
        raw = ctk.CTkInputDialog(
            text=f"New title for “{commitment.title}”:", title="Rename Meeting"
        ).get_input()
        if raw is None:
            return
        self.change_commitment(commitment, EditRequest(title=str(raw)))

    # ------------------------------------------------------------- dragging

    def bind_commitment_drag(self, frame, commitment: CalendarCommitment) -> None:
        """M4.1 -- only a meeting that can move gets a drag; others get none at all."""
        if not movable(commitment):
            return
        from .plan import _subtree

        for widget in _subtree(frame):
            widget.bind("<ButtonPress-1>", lambda event, c=commitment: self.start_commitment_drag(event, c))
            widget.bind("<B1-Motion>", self.on_drag_motion)
            widget.bind("<ButtonRelease-1>", self.on_drag_release)

    def start_commitment_drag(self, _event, commitment: CalendarCommitment) -> None:
        self._drag_kind = "commitment"
        self._drag_commitment = commitment
        self._drag_item = None
        self._drag_block = None
        self._arm_drag_label(commitment.title)

    def drop_commitment(self, commitment: CalendarCommitment, slot_index: int) -> bool:
        """A meeting dropped on a box: it starts there and keeps its length (E3)."""
        day_start = self.bounds.day_start_minutes
        start = day_start + int(slot_index) * SLOT_MINUTES
        # Its own box is no move: a click, or a drop back where it was. Boxes,
        # not minutes -- a 9:15 meeting is in the 9:00 box, and comparing
        # minutes would move it to 9:00 on a plain click.
        if int(slot_index) == (commitment.start_minutes - day_start) // SLOT_MINUTES:
            return False
        return self.change_commitment(commitment, EditRequest(start_minutes=start))

    # ------------------------------------------------------------- changing

    def change_commitment(self, commitment: CalendarCommitment, request: EditRequest) -> bool:
        """Check, ask, then write on a worker. Returns whether a write started.

        Purpose: M4.2 to M4.8 on the screen. Refused before any call when the
                 change cannot be made (M4.1, E2, E5), when the calendar is
                 busy (M4.7, E8) or not connected (M4.8), or when the user
                 says no (M4.4, E1, E7).
        Tests:   tests/test_plan_screen_commitment_edits.py::test_cipm47_a_write_is_refused_while_a_refresh_runs
                 tests/test_plan_screen_commitment_edits.py::test_cipm44_cancel_makes_no_call
        """
        try:
            request = check_request(commitment, request)
        except ValueError as error:
            self.set_status(str(error), "warning")
            return False
        if request.moves:
            start = commitment.start_minutes if request.start_minutes is None else request.start_minutes
            minutes = length_of(commitment) if request.minutes is None else request.minutes
            reason = move_refusal(
                commitment, start, minutes,
                blocks=self.db_manager.get_time_blocks(self.selected_date),
                commitments=getattr(self, "_commitments", ()),
                bounds=self.bounds,
                day_span=self._grid.span if getattr(self, "_grid", None) is not None else None,
            )
            if reason is not None:
                self.set_status(MOVE_REFUSAL_TEXT.get(reason, UNKNOWN_MOVE_REFUSAL), "warning")
                return False
        db_path = self.db_manager.db.db_path
        if getattr(self, "_edit_running", False) or refresh_in_flight(db_path):
            self.set_status(BUSY_TEXT, "muted")
            return False
        if not calendar_ready():
            self.set_status(NOT_READY_TEXT, "error")
            return False
        send_updates = self.confirm_commitment_change(commitment, request)
        if send_updates is None:
            self.set_status("Nothing was changed", "muted")
            return False
        if not claim_refresh(db_path):
            self.set_status(BUSY_TEXT, "muted")
            return False
        return self._start_commitment_write(commitment, request, send_updates, db_path)

    def confirm_commitment_change(
        self, commitment: CalendarCommitment, request: EditRequest
    ) -> Optional[str]:
        """Ask what has to be asked; return ``sendUpdates``, or ``None`` to stop.

        Purpose: M4.4, M4.6, E1, E7. A delete always asks, naming the event.
                 A recurring occurrence says "this occurrence only". Guests are
                 asked about by number. A plain move of a guestless meeting is
                 not asked about: moving it back undoes it.
        Tests:   tests/test_plan_screen_commitment_edits.py::test_cipm44_delete_asks_first_and_names_the_event
                 tests/test_plan_screen_commitment_edits.py::test_cipe1_guests_are_asked_and_the_answer_reaches_send_updates

        A dialog that cannot be shown stops the change: unlike a drop, nothing
        is lost by not writing to someone else's calendar.
        """
        try:
            occurrence = " (this occurrence only; the rest of the series stays)" \
                if commitment.is_recurring_instance else ""
            if request.delete:
                if not messagebox.askokcancel(
                    "Delete meeting",
                    f"Delete “{commitment.title}” on {commitment.commitment_date}"
                    f"{occurrence}?\n\nIt will be removed from your Google Calendar.",
                    icon="warning",
                    parent=self,
                ):
                    return None
            elif commitment.is_recurring_instance:
                if not messagebox.askokcancel(
                    "Change one occurrence",
                    f"Change “{commitment.title}” on {commitment.commitment_date}"
                    f"{occurrence}?",
                    parent=self,
                ):
                    return None
            guests = int(commitment.guest_count or 0)
            if guests <= 0:
                return "none"
            answer = messagebox.askyesnocancel(
                "Email guests",
                f"Email the {guests} other guest{'s' if guests != 1 else ''} of "
                f"“{commitment.title}” about this change?",
                parent=self,
            )
        except Exception:  # noqa: BLE001 - no dialog, no write
            logger.exception("CIP: the confirm dialog for a meeting change raised")
            return None
        if answer is None:
            return None
        return "all" if answer else "none"

    def _start_commitment_write(
        self, commitment: CalendarCommitment, request: EditRequest, send_updates: str, db_path
    ) -> bool:
        self._edit_running = True
        self._edit_result = None
        button = getattr(self, "btn_refresh_calendar", None)
        if button is not None:
            button.configure(state="disabled")
        client_factory = self.calendar_client
        self.set_status(f"Changing “{commitment.title}” in Google Calendar…", "muted")

        def work():
            # Nothing here touches a widget.
            try:
                self._edit_result = write_commitment_edit(
                    commitment, request,
                    client_factory=client_factory, db_path=db_path,
                    send_updates=send_updates,
                )
            except Exception as error:  # noqa: BLE001 - P15
                self._edit_result = EditOutcome(failure=str(error) or type(error).__name__)
            finally:
                release_refresh(db_path)
            if self._edit_result.failure:
                # Logged here as well as shown: the screen may be gone by the
                # time the poll would show it (P2).
                logger.warning("Calendar change to %s not completed: %s",
                               commitment.event_id, self._edit_result.failure)

        try:
            gc.collect()
            self._edit_thread = threading.Thread(target=work, daemon=True)
            self._edit_thread.start()
        except Exception as error:  # noqa: BLE001 - a refusal, not a crash
            release_refresh(db_path)
            self._finish_commitment_write(EditOutcome(failure=f"Could not start the change: {error}"))
            return False
        self._schedule_edit_poll()
        return True

    def _schedule_edit_poll(self) -> None:
        try:
            self._edit_poll_id = self.after(REFRESH_POLL_INTERVAL_MS, self._poll_commitment_write)
        except Exception:  # noqa: BLE001 - the widget is gone
            self._edit_poll_id = None

    def _poll_commitment_write(self) -> None:
        self._edit_poll_id = None
        result = self._edit_result
        if result is None:
            thread = getattr(self, "_edit_thread", None)
            if thread is not None and thread.is_alive():
                self._schedule_edit_poll()
                return
            result = self._edit_result or EditOutcome(
                failure="The calendar change stopped without reporting a result. Refresh."
            )
        self._finish_commitment_write(result)

    def _finish_commitment_write(self, result: EditOutcome) -> None:
        self._edit_result = None
        self._edit_running = False
        if not self._still_on_screen():
            return
        button = getattr(self, "btn_refresh_calendar", None)
        if button is not None:
            button.configure(state="normal")
        self.load_blocks()
        if result.done:
            self.set_status(result.message, "success")
        else:
            self.set_status(_failure_text(result.failure), "error")


def _failure_text(failure: Optional[str]) -> str:
    """A failure after Google changed says so; any other says nothing changed."""
    failure = failure or "no reason was given"
    if failure.startswith("Google Calendar was changed"):
        return failure
    return f"Not changed: {failure}"
