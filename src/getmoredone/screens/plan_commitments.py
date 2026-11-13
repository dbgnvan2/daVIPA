"""The Plan screen's Google Calendar commitments: drawing, Refresh, dismissal.

Purpose: CIP-M3.4, CIP-M3.6, CIP-M3.8 and CIP-M5 -- the screen half of the
         read. A mixin on ``PlanScreen`` plus the widgets it draws, so
         ``plan.py`` carries only the wiring.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md

Nothing here calls Google on the Tk thread. Opening the screen reads the
cache only (M5.1); a read runs on a worker that opens its own database
connection, and the Tk thread collects the result with ``after`` (D10).
"""

from __future__ import annotations

import gc
import logging
import threading
import tkinter as tk
from datetime import datetime
from typing import AbstractSet, List, Optional, Sequence, Tuple

import customtkinter as ctk

from ..calendar_commitments import (
    EXCLUSION_REASONS,
    _boxes_touched,
    age_text,
    committed_slots,
    is_off_grid,
    is_stale,
    refresh_commitments,
)
from ..models import CalendarCommitment
from ..theme import semantic_colors, status_text_color

logger = logging.getLogger(__name__)

#: How often the Tk thread looks for the calendar read's result.
REFRESH_POLL_INTERVAL_MS = 100

#: D13 -- how long after a stale date is drawn the automatic read starts.
#: Long enough that a user clicking through dates does not start one per
#: date; the read is skipped if the screen is not on screen by then.
AUTO_REFRESH_DELAY_MS = 1500

#: The two words a committed box draws besides the meeting itself.
CONFLICT_TEXT = "⚠ overlaps a meeting"
IGNORED_PREFIX = "(ignored) "

# D10 -- one calendar read per database at a time, whatever its range, across
# every Plan screen this process builds. Keyed by the path alone: an automatic
# read and a manual one of the same database must not overlap, or the older
# could finish last and overwrite the newer answer.
_REFRESHES_IN_FLIGHT: set = set()
_REFRESH_LOCK = threading.Lock()

# D13 -- dates already read automatically by this process, success or not. A
# failed automatic read is not retried by itself; Refresh is the next try.
_AUTO_REFRESHED: set = set()


def claim_refresh(db_path) -> bool:
    """Take the one calendar-read slot for a database, or say it is taken."""
    with _REFRESH_LOCK:
        key = str(db_path)
        if key in _REFRESHES_IN_FLIGHT:
            return False
        _REFRESHES_IN_FLIGHT.add(key)
        return True


def release_refresh(db_path) -> None:
    with _REFRESH_LOCK:
        _REFRESHES_IN_FLIGHT.discard(str(db_path))


def refresh_in_flight(db_path) -> bool:
    with _REFRESH_LOCK:
        return str(db_path) in _REFRESHES_IN_FLIGHT


def calendar_ready() -> bool:
    """D13 -- the libraries, ``credentials.json`` and a token are all present."""
    from ..google_calendar import GoogleCalendarManager

    try:
        return bool(
            GoogleCalendarManager.is_available()
            and GoogleCalendarManager.has_credentials()
            and GoogleCalendarManager.check_token_validity().get("exists")
        )
    except Exception:  # noqa: BLE001 - a check that cannot run is "not ready"
        return False


def commitment_label(commitment: CalendarCommitment, *, starts_here: bool = True) -> str:
    """The words on a commitment: its true clock times and its title."""
    if commitment.is_all_day:
        text = f"All day · {commitment.title}"
    elif starts_here:
        text = f"{commitment.start_time}–{commitment.end_time}  {commitment.title}"
    else:
        text = f"↳ {commitment.title}"
    return (IGNORED_PREFIX + text) if commitment.dismissed else text


def commitments_by_slot(commitments: Sequence[CalendarCommitment], bounds) -> dict:
    """``{slot index: [(commitment, starts_here), ...]}`` for drawing.

    Dismissed commitments are drawn too, marked as ignored (CIP-M3.4): the
    meeting is still on the user's calendar, and hiding it would say it is not.
    """
    drawn: dict = {}
    for commitment in commitments:
        if commitment.is_all_day:
            continue
        boxes = _boxes_touched(commitment.start_minutes, commitment.end_minutes, bounds)
        for position, index in enumerate(boxes):
            drawn.setdefault(index, []).append((commitment, position == 0))
    return drawn


def strip_entries(
    commitments: Sequence[CalendarCommitment], bounds, drawn: Optional[AbstractSet[int]] = None
) -> List[Tuple[str, CalendarCommitment]]:
    """CIP-M3.8 and D4 -- what the strip above the grid lists, in order.

    All-day events, which hold no box; timed ones some of which is where no
    box can be (before midnight's first box, or after 23:30); and, given the
    ``drawn`` boxes, timed ones none of whose boxes is drawn. The last is an
    ignored meeting before Day Start or after Day End: it no longer widens the
    day, and without this it would be shown nowhere and could not be held
    again (CIP-M3.4).
    """
    lines = []
    for commitment in commitments:
        if commitment.is_all_day:
            lines.append((commitment_label(commitment), commitment))
        elif is_off_grid(commitment, bounds):
            lines.append((
                commitment_label(commitment) + " (part of it is outside the grid)", commitment
            ))
        elif drawn is not None and not drawn.intersection(
            _boxes_touched(commitment.start_minutes, commitment.end_minutes, bounds)
        ):
            lines.append((commitment_label(commitment) + " (outside the drawn day)", commitment))
    return lines


def build_commitment_chip(
    parent, commitment: CalendarCommitment, row: int, *, starts_here: bool
) -> ctk.CTkFrame:
    """One commitment in a box: a stripe in the commitment colour, and its words.

    Purpose: CIP-M3.6 -- visibly not a block and not lunch, never
             priority-coloured.
    Tests:   tests/test_plan_screen_commitments.py::test_cipm36_its_colour_is_the_commitment_token_not_a_priority_fill
    """
    palette = semantic_colors()
    chip = ctk.CTkFrame(parent, fg_color="transparent")
    chip.grid(row=row, column=0, sticky="ew", pady=1)
    chip.grid_columnconfigure(1, weight=1)
    stripe = ctk.CTkFrame(
        chip, width=6, height=12, corner_radius=3, fg_color=palette["commitment"],
    )
    stripe.grid(row=0, column=0, sticky="ns", padx=(0, 8), pady=2)
    stripe.grid_propagate(False)
    chip.stripe = stripe
    label = ctk.CTkLabel(
        chip,
        text=commitment_label(commitment, starts_here=starts_here),
        anchor="w",
        text_color=palette["muted_text"] if (commitment.dismissed or not starts_here)
        else palette["body_text"],
    )
    label.grid(row=0, column=1, sticky="w")
    chip.label = label
    return chip


class PlanCommitmentsMixin:
    """Refresh, the calendar line, the strip, and dismissal, for ``PlanScreen``."""

    # ---------------------------------------------------------------- reading

    def load_commitments(self) -> List[CalendarCommitment]:
        """This date's cached commitments and its read record. No network (M5.1)."""
        try:
            self._commitments = self.db_manager.get_commitments(self.selected_date)
            self._commitment_fetch = self.db_manager.get_commitment_fetch(self.selected_date)
        except Exception as error:  # noqa: BLE001 - a cache that cannot be read
            # is said, not shown as a day with no meetings (P2).
            logger.warning("CIP: commitments for %s unreadable: %s", self.selected_date, error)
            self._commitments = []
            self._commitment_fetch = {"fetched_at": None, "last_error": f"the cache could not be read: {error}"}
        self._committed = committed_slots(self._commitments, self.bounds)
        return self._commitments

    def draw_commitment_strip(self) -> None:
        """CIP-M5.4, CIP-M3.8 -- the age of the answer, then what no box shows."""
        strip = getattr(self, "commitment_strip", None)
        if strip is None:
            return
        for widget in strip.winfo_children():
            widget.destroy()
        text, kind = age_text(getattr(self, "_commitment_fetch", None))
        self.calendar_age_label = ctk.CTkLabel(
            strip, text=text, anchor="w", text_color=status_text_color(kind),
            font=ctk.CTkFont(size=11),
        )
        self.calendar_age_label.grid(row=0, column=0, sticky="w")
        self._strip_labels = []
        palette = semantic_colors()
        grid = getattr(self, "_grid", None)
        drawn = {entry.slot.index for entry in grid.slots} if grid is not None else None
        entries = strip_entries(self._commitments, self.bounds, drawn)
        for row, (line, commitment) in enumerate(entries, start=1):
            label = ctk.CTkLabel(strip, text=line, anchor="w", text_color=palette["body_text"])
            label.grid(row=row, column=0, sticky="w")
            self.bind_commitment_handlers(label, commitment)
            self._strip_labels.append(label)

    # ------------------------------------------------------------ dismissing

    def bind_commitment_handlers(self, frame, commitment: CalendarCommitment) -> None:
        from .plan import RIGHT_CLICK_SEQUENCES, _subtree

        for widget in _subtree(frame):
            for sequence in RIGHT_CLICK_SEQUENCES:
                widget.bind(
                    sequence,
                    lambda event, c=commitment: self.open_commitment_menu(event, c),
                )

    def commitment_menu_entries(self, commitment: CalendarCommitment) -> List[Tuple[str, Optional[object]]]:
        """The menu a commitment offers, as ``(label, command)``; ``None`` is disabled.

        Purpose: CIP-M3.4 / D9 -- dismissal only for a meeting the user cannot
                 edit. An editable one offers none: its honest gesture is to
                 change the real event.
        Tests:   tests/test_plan_screen_commitments.py::test_cipm34_an_editable_commitment_offers_no_dismiss
        """
        if commitment.can_edit:
            return [("Change this meeting in Google Calendar, then Refresh", None)]
        if commitment.dismissed:
            return [(
                "Hold this time again",
                lambda c=commitment: self.dismiss_commitment(c.id, False),
            )]
        return [(
            "Ignore on this day (stays on your calendar)",
            lambda c=commitment: self.dismiss_commitment(c.id, True),
        )]

    def open_commitment_menu(self, event, commitment: CalendarCommitment) -> None:
        menu = tk.Menu(self, tearoff=0)
        self._commitment_menu = menu
        for label, command in self.commitment_menu_entries(commitment):
            if command is None:
                menu.add_command(label=label, state="disabled")
            else:
                menu.add_command(label=label, command=command)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def dismiss_commitment(self, commitment_id: str, dismissed: bool) -> None:
        try:
            commitment = self.db_manager.set_commitment_dismissed(commitment_id, dismissed)
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self.load_blocks()
        if dismissed:
            self.set_status(
                f"Ignoring “{commitment.title}” on {commitment.commitment_date} — it is"
                " still on your calendar", "muted",
            )
        else:
            self.set_status(f"“{commitment.title}” holds its time again", "muted")

    # -------------------------------------------------------------- refresh

    def calendar_ids(self) -> List[str]:
        configured = getattr(self.settings, "plan_commitment_calendar_ids", None)
        if isinstance(configured, list):
            ids = [str(c).strip() for c in configured if isinstance(c, str) and str(c).strip()]
            if ids:
                return ids
        return ["primary"]

    def sync_refresh_button(self) -> None:
        """D10 -- a rebuilt screen comes up disabled while a read is in flight."""
        button = getattr(self, "btn_refresh_calendar", None)
        if button is None:
            return
        db_path = self.db_manager.db.db_path
        busy = refresh_in_flight(db_path)
        button.configure(state="disabled" if busy else "normal")
        if busy and not getattr(self, "_refresh_running", False):
            self._schedule_claim_watch()

    def _schedule_claim_watch(self) -> None:
        try:
            self._claim_watch_id = self.after(REFRESH_POLL_INTERVAL_MS, self._watch_claim)
        except Exception:  # noqa: BLE001 - the widget is gone
            self._claim_watch_id = None

    def _watch_claim(self) -> None:
        """Another screen's read: wait for it, then show what it wrote."""
        self._claim_watch_id = None
        if not self._still_on_screen():
            return
        if refresh_in_flight(self.db_manager.db.db_path):
            self._schedule_claim_watch()
            return
        self.btn_refresh_calendar.configure(state="normal")
        self.load_blocks()

    def refresh_calendar(self, *, automatic: bool = False) -> bool:
        """Read this date from Google Calendar on a worker thread.

        Purpose: CIP-M5.2, CIP-M5.3 -- the Refresh button, and the automatic
                 read of a stale date (M5.5). Returns whether a read started.
        Tests:   tests/test_plan_screen_commitments.py::test_cipm52_refresh_disables_first

        The button is disabled before anything slow or fallible runs, and every
        refusal gives it back. An automatic read says nothing on the status
        line, which belongs to the user's gestures; its answer is the calendar
        line above the grid.
        """
        if getattr(self, "_refresh_running", False):
            return False
        self._refresh_running = True
        self._refresh_automatic = automatic
        self._refresh_result = None
        self._refresh_thread = None
        self.btn_refresh_calendar.configure(state="disabled")
        claimed = None
        try:
            from ..google_calendar import GoogleCalendarManager

            if not automatic:
                if not GoogleCalendarManager.is_available():
                    return self._finish_refresh_refusal(
                        "Google Calendar libraries are not installed — run: "
                        "pip install -r requirements.txt"
                    )
                if not GoogleCalendarManager.has_credentials():
                    from .calendar_dialog import missing_credentials_message

                    return self._finish_refresh_refusal(missing_credentials_message())
                if not GoogleCalendarManager.check_token_validity().get("exists"):
                    from .calendar_dialog import not_connected_message

                    return self._finish_refresh_refusal(not_connected_message())

            db_path = self.db_manager.db.db_path
            if not claim_refresh(db_path):
                return self._finish_refresh_refusal(
                    "The calendar is already being read — wait for that to finish",
                    kind="muted",
                )
            claimed = db_path
            block_date = self.selected_date
            calendar_ids = self.calendar_ids()
            client_factory = self.calendar_client
            if not automatic:
                self.set_status(f"Reading Google Calendar for {block_date}…", "muted")

            def work():
                # Nothing here touches a widget (see the export's worker).
                try:
                    self._refresh_result = refresh_commitments(
                        block_date, block_date,
                        client_factory=client_factory,
                        db_path=db_path,
                        calendar_ids=calendar_ids,
                    )
                except Exception as error:  # noqa: BLE001 - P15
                    from ..calendar_commitments import RefreshOutcome

                    self._refresh_result = RefreshOutcome(
                        dates=[block_date], failure=str(error) or type(error).__name__
                    )
                finally:
                    release_refresh(db_path)

            gc.collect()
            self._refresh_thread = threading.Thread(target=work, daemon=True)
            self._refresh_thread.start()
            self._schedule_refresh_poll()
            return True
        except Exception as error:  # noqa: BLE001 - a refusal, not a crash
            if claimed is not None:
                release_refresh(claimed)
            return self._finish_refresh_refusal(f"Could not start the calendar read: {error}")

    def _finish_refresh_refusal(self, message: str, kind: str = "error") -> bool:
        self._refresh_running = False
        if self._still_on_screen():
            self.btn_refresh_calendar.configure(state="normal")
            if not getattr(self, "_refresh_automatic", False):
                self.set_status(message, kind)
        return False

    def _schedule_refresh_poll(self) -> None:
        try:
            self._refresh_poll_id = self.after(REFRESH_POLL_INTERVAL_MS, self._poll_refresh)
        except Exception:  # noqa: BLE001 - the widget is gone
            self._refresh_poll_id = None

    def _poll_refresh(self) -> None:
        """Collect the worker's result on the Tk thread, or come back later."""
        self._refresh_poll_id = None
        result = self._refresh_result
        if result is None:
            thread = getattr(self, "_refresh_thread", None)
            if thread is not None and thread.is_alive():
                self._schedule_refresh_poll()
                return
            result = self._refresh_result
            if result is None:
                self._finish_refresh_refusal(
                    "The calendar read stopped without reporting a result"
                )
                return
        self._refresh_result = None
        self._refresh_running = False
        if not self._still_on_screen():
            return
        self.btn_refresh_calendar.configure(state="normal")
        self.load_blocks()
        if not getattr(self, "_refresh_automatic", False):
            self.set_status(*refresh_status(result))

    def maybe_auto_refresh(self) -> None:
        """CIP-M5.5 / D13 -- read a stale date once, in the background.

        Only with the libraries, credentials and a token present; once per date
        per process, whether it worked or not. Scheduled, not run: the screen
        paints first (M5.1), and a date the user has already left is not read.
        """
        if not getattr(self, "_ready", False):
            return
        stale_minutes = getattr(self.settings, "plan_commitment_stale_minutes", 15)
        if not is_stale(getattr(self, "_commitment_fetch", None), stale_minutes, datetime.now()):
            return
        key = (str(self.db_manager.db.db_path), self.selected_date)
        if key in _AUTO_REFRESHED or not calendar_ready():
            return
        pending = getattr(self, "_auto_refresh_id", None)
        if pending is not None:
            try:
                self.after_cancel(pending)
            except Exception:  # noqa: BLE001 - already fired
                pass
        try:
            self._auto_refresh_id = self.after(
                AUTO_REFRESH_DELAY_MS, lambda d=self.selected_date: self._auto_refresh_due(d)
            )
        except Exception:  # noqa: BLE001 - the widget is gone
            self._auto_refresh_id = None

    def _auto_refresh_due(self, block_date: str) -> bool:
        self._auto_refresh_id = None
        if not self._still_on_screen() or self.selected_date != block_date:
            return False
        try:
            if not self.winfo_ismapped():
                return False
        except Exception:  # noqa: BLE001
            return False
        key = (str(self.db_manager.db.db_path), block_date)
        if key in _AUTO_REFRESHED:
            return False
        started = self.refresh_calendar(automatic=True)
        if started:
            _AUTO_REFRESHED.add(key)
        return started

    def cancel_commitment_callbacks(self) -> None:
        for name in ("_refresh_poll_id", "_auto_refresh_id", "_claim_watch_id"):
            pending = getattr(self, name, None)
            if pending is not None:
                try:
                    self.after_cancel(pending)
                except Exception:  # noqa: BLE001 - already fired, or already gone
                    pass
                setattr(self, name, None)


def refresh_status(outcome) -> Tuple[str, str]:
    """The status line after a Refresh the user pressed (CIP-M2.5, M2.6, D6)."""
    if outcome.failure is not None:
        if outcome.signed_out:
            from .calendar_dialog import not_connected_message

            return not_connected_message(), "error"
        return f"Google Calendar read failed: {outcome.failure}", "error"
    result = outcome.result
    noun = "event" if outcome.written == 1 else "events"
    parts = [f"Calendar read: {outcome.written} {noun}"]
    kind = "success"
    if result is not None:
        left = [
            f"{result.excluded[reason]} {reason}"
            for reason in EXCLUSION_REASONS
            if result.excluded.get(reason)
        ]
        if left:
            parts.append("left out " + ", ".join(left))
        if result.unparseable:
            parts.append("could not read " + ", ".join(result.unparseable))
            kind = "warning"
        if result.skipped_calendars:
            parts.append("skipped " + ", ".join(sorted(result.skipped_calendars)))
            kind = "warning"
    return " — ".join(parts), kind
