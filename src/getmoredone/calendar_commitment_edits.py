"""Changing a Google Calendar meeting from the Plan: move, length, title, delete.

Purpose: CIP-M4 -- the write half. GUI-free, so every rule here is tested
         with a fake client and no window.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#7-m4--editing-the-calendar-from-inside-the-plan
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_editing.md

Every write reads the event first and refuses if Google's copy is not the one
the Plan shows (E6), and the cache is changed only from Google's reply (E9),
so the Plan is never ahead of the calendar (M4.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Callable, Iterable, List, Optional, Sequence

from .calendar_commitments import (
    _boxes_touched,
    can_edit_of,
    committed_slots,
    exclusion_of,
    parse_event,
)
from .google_calendar import CalendarEventMissing
from .models import CalendarCommitment
from .time_block_layout import (
    MINUTES_PER_DAY,
    SlotRefusal,
    can_place,
    slot_occupancy,
)

#: E5 -- a block sits in a box the meeting would move onto. Its own value
#: rather than ``SLOT_FULL``: a box with one block is not full for a block,
#: but it is taken for a meeting.
MOVE_ONTO_BLOCK = "onto_block"


class CommitmentChanged(RuntimeError):
    """Google's copy is not the one the Plan shows (E6). Nothing was written."""


class CommitmentNotMovable(ValueError):
    """All day, split over midnight, or not the user's to change (E2, M4.1)."""


def movable(commitment: CalendarCommitment) -> bool:
    """Whether this meeting can be dragged or given a new length (E2, M4.1).

    Timed, the user's to change, and wholly on its date. A part that starts
    at 00:00 or ends at 24:00 may be one part of a meeting over midnight
    (D4), which has no start or end on this date to move, so it is refused;
    the check against Google's copy (``verify_unchanged``) is the final word.
    """
    return bool(
        commitment.can_edit
        and not commitment.dismissed
        # An all-day commitment is stored 00:00 to 00:00, so this refuses it too.
        and 0 < commitment.start_minutes < commitment.end_minutes < MINUTES_PER_DAY
    )


def length_of(commitment: CalendarCommitment) -> int:
    return int(commitment.end_minutes) - int(commitment.start_minutes)


def verify_unchanged(
    event: dict, commitment: CalendarCommitment, *, tz=None, whole: bool = False
) -> None:
    """Raise ``CommitmentChanged`` unless Google's copy is the Plan's (E6).

    Purpose: M4.5 -- a write never overwrites a change the Plan has not read.
    Tests:   tests/test_calendar_commitment_edits.py::test_cipm45_a_changed_event_is_not_overwritten

    Compared: still held (not declined, cancelled or free), still the user's
    to change, and this date's start, end, title and number of guests (the
    user was asked about emailing that many). ``whole`` -- for a move
    or a new length -- also requires the event to be on this date only.
    """
    if exclusion_of(event) is not None or not can_edit_of(event):
        raise CommitmentChanged(_changed_text(commitment))
    day = date.fromisoformat(commitment.commitment_date)
    around = [(day + timedelta(days=d)).isoformat() for d in (-1, 0, 1)]
    parts = parse_event(event, calendar_id=commitment.calendar_id, dates=around, tz=tz)
    here = [p for p in parts if p.commitment_date == commitment.commitment_date]
    if len(here) != 1:
        raise CommitmentChanged(_changed_text(commitment))
    now = here[0]
    if (
        now.is_all_day != commitment.is_all_day
        or now.start_minutes != commitment.start_minutes
        or now.end_minutes != commitment.end_minutes
        or now.title != commitment.title
        # E1 -- the user was asked about emailing this many guests.
        or now.guest_count != commitment.guest_count
    ):
        raise CommitmentChanged(_changed_text(commitment))
    if whole and len(parts) != 1:
        raise CommitmentNotMovable(
            f"“{commitment.title}” runs over midnight, so it cannot be moved from one day"
        )


def _changed_text(commitment: CalendarCommitment) -> str:
    when = (commitment.fetched_at or "")[11:16]
    since = f" since {when}" if when else ""
    return (
        f"“{commitment.title}” changed in Google Calendar{since}. "
        "Refresh, then try again."
    )


def move_refusal(
    commitment: CalendarCommitment,
    start_minutes: int,
    minutes: int,
    *,
    blocks: Sequence,
    commitments: Iterable[CalendarCommitment],
    bounds,
    day_span=None,
) -> Optional[str]:
    """Why the meeting may not take these times on the grid, or ``None`` (E5).

    Purpose: refuse before any network call, with the reason. The boxes it
             would hold must be inside the drawn day, not lunch, not held by
             another meeting, and empty of blocks.
    Tests:   tests/test_calendar_commitment_edits.py::test_cipm42_a_move_onto_a_block_is_refused_before_any_call
    """
    start, end = int(start_minutes), int(start_minutes) + int(minutes)
    if minutes <= 0 or start < 0 or end > MINUTES_PER_DAY:
        return SlotRefusal.OUTSIDE_GRID
    boxes = _boxes_touched(start, end, bounds)
    if not boxes:
        return SlotRefusal.OUTSIDE_GRID
    others = committed_slots(
        [c for c in commitments if c.id != commitment.id], bounds
    )
    refusal = can_place(
        blocks, bounds, boxes[0], len(boxes), day_span=day_span, committed=others
    )
    if refusal is not None:
        return refusal
    occupancy = slot_occupancy(blocks, bounds, day_span=day_span)
    if any(occupancy.get(index) for index in boxes):
        return MOVE_ONTO_BLOCK
    return None


@dataclass
class EditRequest:
    """One change to one meeting. ``delete`` excludes the other three."""

    start_minutes: Optional[int] = None
    minutes: Optional[int] = None
    title: Optional[str] = None
    delete: bool = False

    @property
    def moves(self) -> bool:
        return self.start_minutes is not None or self.minutes is not None


def check_request(commitment: CalendarCommitment, request: EditRequest) -> EditRequest:
    """Refuse a request that cannot be made, before any call. Returns it tidied."""
    if not commitment.can_edit:
        raise CommitmentNotMovable(
            f"“{commitment.title}” is not yours to change; ignore it on this day instead"
        )
    if request.delete:
        if request.moves or request.title is not None:
            raise ValueError("a delete changes nothing else")
        return request
    if not request.moves and request.title is None:
        raise ValueError("nothing to change")
    if request.moves and not movable(commitment):
        raise CommitmentNotMovable(
            f"“{commitment.title}” is all day or runs over midnight, so it cannot be moved here"
        )
    if request.title is not None:
        title = request.title.strip()
        if not title:
            raise ValueError("A meeting needs a title.")
        request = EditRequest(request.start_minutes, request.minutes, title)
    return request


def edit_commitment(
    client, commitment: CalendarCommitment, request: EditRequest, *,
    send_updates: str = "none", tz=None,
) -> dict:
    """Write one change to Google and return Google's reply (the event as stored).

    Purpose: M4.2, M4.3, M4.6 -- through ``update_event``, which reads the
             event, changes only the named fields and writes the rest back.
    Tests:   tests/test_calendar_commitment_edits.py::test_cipm42_a_move_writes_the_new_start_and_the_same_length
             tests/test_calendar_commitment_edits.py::test_cipm46_attendees_conference_reminders_recurrence_description_survive

    The new start is wall clock on the meeting's date, written in the zone
    ``update_event`` names, as the export does. Raises ``CommitmentChanged``,
    ``CalendarEventMissing`` or the client's failure; nothing is stored here.
    ``commitments_from_reply`` turns the reply into what the cache holds.
    """
    request = check_request(commitment, request)
    if request.delete:
        raise ValueError("use delete_commitment")
    start = None
    minutes = None
    if request.moves:
        start_minutes = (
            commitment.start_minutes if request.start_minutes is None else int(request.start_minutes)
        )
        minutes = length_of(commitment) if request.minutes is None else int(request.minutes)
        start = datetime.combine(date.fromisoformat(commitment.commitment_date), time()) + timedelta(
            minutes=start_minutes
        )
    return client.update_event(
        event_id=commitment.event_id,
        summary=request.title,
        start_datetime=start,
        duration_minutes=minutes,
        calendar_id=commitment.calendar_id,
        check=lambda event: verify_unchanged(event, commitment, tz=tz, whole=request.moves),
        send_updates=send_updates,
    )


def commitments_from_reply(
    reply: dict, commitment: CalendarCommitment, *, tz=None
) -> List[CalendarCommitment]:
    """This date's commitment as Google's reply has it (E9); none if it no longer holds."""
    if exclusion_of(reply) is not None:
        return []
    return parse_event(
        reply, calendar_id=commitment.calendar_id, dates=[commitment.commitment_date], tz=tz
    )


def delete_commitment(
    client, commitment: CalendarCommitment, *, send_updates: str = "none", tz=None,
) -> None:
    """Delete the Google event, after checking it is still the Plan's copy (M4.4).

    A 404/410 at either step is the end state asked for, so it is not an error.
    For a recurring occurrence the event id is that occurrence's, so only it
    goes (M4.6).
    """
    check_request(commitment, EditRequest(delete=True))
    try:
        event = client.get_event(commitment.event_id, calendar_id=commitment.calendar_id)
    except CalendarEventMissing:
        return
    verify_unchanged(event, commitment, tz=tz)
    try:
        client.delete_event(
            commitment.event_id, calendar_id=commitment.calendar_id, send_updates=send_updates
        )
    except CalendarEventMissing:
        return


@dataclass
class EditOutcome:
    """What a write did, for the status line."""

    done: bool = False
    message: str = ""
    failure: Optional[str] = None
    commitments: List[CalendarCommitment] = field(default_factory=list)


def write_commitment_edit(
    commitment: CalendarCommitment,
    request: EditRequest,
    *,
    client_factory: Callable[[], object],
    db_path,
    send_updates: str = "none",
    tz=None,
    now: Optional[Callable[[], datetime]] = None,
) -> EditOutcome:
    """Write to Google, then store Google's reply. Never raises (the worker's job).

    Purpose: M4.5 / E9 -- the cache changes only after Google confirms, and
             only to what Google returned.
    Tests:   tests/test_calendar_commitment_edits.py::test_cipm45_a_failed_write_leaves_the_cache_and_grid_as_they_were
             tests/test_calendar_commitment_edits.py::test_cipm45_the_cache_takes_googles_reply_not_the_request
    """
    from .db_manager import DatabaseManager

    clock = now or datetime.now
    outcome = EditOutcome()
    try:
        client = client_factory()
        if request.delete:
            delete_commitment(client, commitment, send_updates=send_updates, tz=tz)
            reply = None
        else:
            reply = edit_commitment(
                client, commitment, request, send_updates=send_updates, tz=tz
            )
    except CalendarEventMissing:
        outcome.failure = f"“{commitment.title}” is no longer in Google Calendar. Refresh."
        return outcome
    except Exception as error:  # noqa: BLE001 - P15: reported, never raised
        outcome.failure = str(error) or type(error).__name__
        return outcome

    # Google has the change from here on, so no failure below may say "not
    # changed": it says the calendar changed and the Plan could not follow.
    try:
        fresh = [] if reply is None else commitments_from_reply(reply, commitment, tz=tz)
    except Exception as error:  # noqa: BLE001 - reported, never raised
        outcome.failure = (
            f"Google Calendar was changed, but its reply could not be read: {error}. Refresh."
        )
        return outcome
    stamp = clock().isoformat(timespec="seconds")
    db_manager = DatabaseManager(db_path=db_path)
    try:
        outcome.commitments = db_manager.apply_commitment_edit(
            commitment.event_id, commitment.commitment_date, fresh, stamp
        )
    except Exception as error:  # noqa: BLE001 - Google changed; the cache did not
        outcome.failure = (
            f"Google Calendar was changed, but the Plan could not save it: {error}. Refresh."
        )
        return outcome
    finally:
        db_manager.close()
    outcome.done = True
    outcome.message = _done_text(commitment, request)
    return outcome


def _done_text(commitment: CalendarCommitment, request: EditRequest) -> str:
    if request.delete:
        return f"Deleted “{commitment.title}” from Google Calendar."
    if request.title is not None and not request.moves:
        return f"Renamed to “{request.title.strip()}” in Google Calendar."
    return f"Moved “{commitment.title}” in Google Calendar."
