"""Google Calendar events read as commitments: parse, fetch, and slots held.

Purpose: CIP-M2 and the arithmetic half of CIP-M3. GUI-free, so every rule
         here is tested with a fake client and no window.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#5-m2--the-read
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md

An action item is *what* has to be done; a commitment is *when* something was
decided for the user. ``calendar_importer.py`` makes the first from an event
and this module makes the second, from the same event, on purpose (spec 2.1).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .google_calendar import (
    BLOCK_ID_PROPERTY,
    AuthenticationRequired,
    CalendarEventMissing,
    CalendarForbidden,
)
from .models import CalendarCommitment
from .time_block_layout import (
    LAST_DAY_END_MINUTES,
    MINUTES_PER_DAY,
    SLOT_MINUTES,
    format_hhmm,
)

logger = logging.getLogger(__name__)

#: CIP-M2.5 -- why an event was left out, as the words the status line counts.
EXCLUDED_CANCELLED = "cancelled"
EXCLUDED_DECLINED = "declined"
EXCLUDED_FREE = "free"
EXCLUDED_EXPORTED = "exported"
EXCLUSION_REASONS = (
    EXCLUDED_CANCELLED, EXCLUDED_DECLINED, EXCLUDED_FREE, EXCLUDED_EXPORTED,
)


class CommitmentParseError(ValueError):
    """An event whose times cannot be read. Skipped and named, never guessed."""


class CommitmentFetchError(RuntimeError):
    """No configured calendar could be read, so nothing is known about the range."""


def local_zone():
    """The machine's zone: ``tzlocal`` when it imports, else ``None`` (D5).

    ``None`` means "the OS zone", which ``datetime.astimezone()`` with no
    argument applies. ``tzlocal`` is optional (``google_calendar.py``), so
    a machine without it still converts, just without an IANA name.
    """
    try:
        from tzlocal import get_localzone

        return get_localzone()
    except Exception:  # noqa: BLE001 - optional; the OS zone is the fallback
        return None


def _to_local(moment: datetime, tz) -> datetime:
    return moment.astimezone(tz) if tz is not None else moment.astimezone()


def _local_midnight(day: date, tz) -> datetime:
    if tz is not None:
        return datetime.combine(day, time.min, tzinfo=tz)
    return datetime.combine(day, time.min).astimezone()


def _parse_moment(value) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CommitmentParseError("no time")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as error:
        raise CommitmentParseError(f"unreadable time {value!r}") from error
    if moment.tzinfo is None:
        # Google always sends an offset with ``dateTime``. A time without one
        # would have to be guessed at, which M2.6 forbids.
        raise CommitmentParseError(f"time {value!r} has no offset")
    return moment


def _parse_day(value) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise CommitmentParseError(f"unreadable date {value!r}") from error


def event_name(event: dict) -> str:
    """How an event is named in a status line: its title, else its id."""
    title = (event.get("summary") or "").strip()
    return title or str(event.get("id") or "(an event with no id)")


def _self_attendee(event: dict) -> Optional[dict]:
    for attendee in event.get("attendees") or ():
        if isinstance(attendee, dict) and attendee.get("self"):
            return attendee
    return None


def exclusion_of(event: dict) -> Optional[str]:
    """Why this event holds no time, or ``None`` if it does (CIP-M2.5, CIP-M3.1).

    The export's own marker is checked first and on its own: an event this
    app created *is* the user's plan, and read back as a commitment it would
    hold the very box the block it came from sits in (spec 6.1).
    """
    private = ((event.get("extendedProperties") or {}).get("private") or {})
    if BLOCK_ID_PROPERTY in private:
        return EXCLUDED_EXPORTED
    if event.get("status") == "cancelled":
        return EXCLUDED_CANCELLED
    me = _self_attendee(event)
    if me is not None and me.get("responseStatus") == "declined":
        return EXCLUDED_DECLINED
    if event.get("transparency") == "transparent":
        return EXCLUDED_FREE
    return None


def can_edit_of(event: dict) -> bool:
    """CIP-M4.1 -- the user organised it, or guests may change it."""
    organizer = event.get("organizer") or {}
    return bool(organizer.get("self")) or bool(event.get("guestsCanModify"))


def parse_event(
    event: dict,
    *,
    calendar_id: str,
    dates: Sequence[str],
    tz=None,
) -> List[CalendarCommitment]:
    """The commitments one event makes on the dates being read.

    Purpose: CIP-M2.3, CIP-M2.4, D4.
    Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#5-m2--the-read
    Tests:   tests/test_calendar_commitments.py::test_cipm23_an_offset_time_is_stored_as_local_wall_clock
             tests/test_calendar_commitments.py::test_cipm23_an_event_over_midnight_is_two_commitments
             tests/test_calendar_commitments.py::test_cipd4_a_date_before_the_range_is_not_written

    One commitment per date the event touches, clipped to that date, and only
    for ``dates`` (D4): ``events.list`` also returns events that began before
    the range, and their earlier dates were not read. Times are local wall
    clock, converted once, here. Raises ``CommitmentParseError`` for an event
    whose times cannot be read. Exclusions are the caller's (``exclusion_of``).
    """
    wanted = set(dates)
    start = event.get("start") or {}
    end = event.get("end") or {}
    me = _self_attendee(event)
    common = dict(
        event_id=str(event.get("id") or ""),
        calendar_id=calendar_id,
        title=(event.get("summary") or "").strip() or "(No title)",
        response_status=(me or {}).get("responseStatus"),
        transparency=event.get("transparency"),
        can_edit=can_edit_of(event),
        is_recurring_instance=bool(event.get("recurringEventId")),
    )
    if not common["event_id"]:
        raise CommitmentParseError("no event id")

    if "dateTime" not in start and "date" in start:
        first = _parse_day(start.get("date"))
        # ``end.date`` is exclusive; a missing one means a one-day event.
        last = _parse_day(end["date"]) - timedelta(days=1) if "date" in end else first
        if last < first:
            raise CommitmentParseError("ends before it starts")
        found = []
        day = first
        while day <= last:
            if day.isoformat() in wanted:
                found.append(CalendarCommitment(
                    commitment_date=day.isoformat(), start_time="", end_time="",
                    start_minutes=0, end_minutes=0, is_all_day=True, **common,
                ))
            day += timedelta(days=1)
        return found

    begins = _to_local(_parse_moment(start.get("dateTime")), tz)
    ends = _to_local(_parse_moment(end.get("dateTime")), tz)
    if ends < begins:
        raise CommitmentParseError("ends before it starts")
    found = []
    day = begins.date()
    while day <= ends.date():
        start_minutes = begins.hour * 60 + begins.minute if day == begins.date() else 0
        end_minutes = (
            ends.hour * 60 + ends.minute if day == ends.date() else MINUTES_PER_DAY
        )
        # A part of no length -- the event ends exactly at midnight -- is no
        # part of the next date.
        if day.isoformat() in wanted and (end_minutes > start_minutes or begins == ends):
            found.append(CalendarCommitment(
                commitment_date=day.isoformat(),
                start_time=format_hhmm(start_minutes),
                end_time=format_hhmm(end_minutes),
                start_minutes=start_minutes,
                end_minutes=end_minutes,
                **common,
            ))
        day += timedelta(days=1)
    return found


@dataclass
class FetchResult:
    """What one read of a date range found, and everything it left out."""

    dates: List[str]
    commitments: List[CalendarCommitment] = field(default_factory=list)
    excluded: Dict[str, int] = field(default_factory=dict)
    unparseable: List[str] = field(default_factory=list)
    #: D6 -- a calendar that refused for good (gone, or forbidden), and why.
    skipped_calendars: Dict[str, str] = field(default_factory=dict)


def dates_between(start_date: str, end_date: str) -> List[str]:
    first, last = _parse_day(start_date), _parse_day(end_date)
    if last < first:
        raise ValueError(f"{end_date} is before {start_date}")
    return [(first + timedelta(days=n)).isoformat() for n in range((last - first).days + 1)]


def fetch_commitments(
    start_date: str,
    end_date: str,
    *,
    client,
    calendar_ids: Sequence[str],
    tz=None,
) -> FetchResult:
    """Read every configured calendar over the range, once each.

    Purpose: CIP-M2.1, CIP-M2.5, CIP-M2.6, CIP-M2.8, D6.
    Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#5-m2--the-read
    Tests:   tests/test_calendar_commitments.py::test_cipm21_seven_days_is_one_call_per_calendar
             tests/test_calendar_commitments.py::test_cipd6_a_forbidden_calendar_is_skipped_and_named

    A transient failure (network, 5xx, rate limit, a lapsed sign-in) is
    raised, so the caller replaces nothing. A calendar that is gone or
    forbidden is skipped and named, so one revoked shared calendar does not
    freeze the rest; if every calendar is skipped, nothing was read and
    ``CommitmentFetchError`` is raised rather than an empty answer returned.

    The same event on two calendars (an invitation on a shared calendar) is
    one commitment per date, editable if any copy is (M2.8).
    """
    dates = dates_between(start_date, end_date)
    time_min = _local_midnight(_parse_day(dates[0]), tz)
    time_max = _local_midnight(_parse_day(dates[-1]) + timedelta(days=1), tz)
    result = FetchResult(dates=dates, excluded={reason: 0 for reason in EXCLUSION_REASONS})
    by_key: Dict[Tuple[str, str], CalendarCommitment] = {}
    seen_excluded = set()
    read_any = False

    for calendar_id in calendar_ids:
        try:
            events = client.list_events_between(
                time_min.isoformat(), time_max.isoformat(), calendar_id
            )
        except (CalendarEventMissing, CalendarForbidden) as error:
            result.skipped_calendars[calendar_id] = str(error)
            logger.warning("CIP D6: calendar %r skipped: %s", calendar_id, error)
            continue
        read_any = True
        for event in events or ():
            if not isinstance(event, dict):
                result.unparseable.append(repr(event)[:60])
                continue
            reason = exclusion_of(event)
            if reason is not None:
                # Counted once per event, however many calendars it is on.
                key = (reason, str(event.get("id")))
                if key not in seen_excluded:
                    seen_excluded.add(key)
                    result.excluded[reason] += 1
                continue
            try:
                parts = parse_event(event, calendar_id=calendar_id, dates=dates, tz=tz)
            except CommitmentParseError as error:
                result.unparseable.append(event_name(event))
                logger.warning("CIP-M2.6: skipped %r: %s", event_name(event), error)
                continue
            for part in parts:
                key = (part.event_id, part.commitment_date)
                held = by_key.get(key)
                if held is None:
                    by_key[key] = part
                elif part.can_edit and not held.can_edit:
                    held.can_edit = True

    if not read_any:
        named = "; ".join(f"{cid}: {why}" for cid, why in result.skipped_calendars.items())
        raise CommitmentFetchError(f"no calendar could be read ({named or 'none configured'})")
    result.commitments = sorted(
        by_key.values(), key=lambda c: (c.commitment_date, c.start_minutes, c.end_minutes)
    )
    return result


@dataclass
class RefreshOutcome:
    """What a refresh did, for the status line."""

    dates: List[str]
    written: int = 0
    failure: Optional[str] = None
    signed_out: bool = False
    result: Optional[FetchResult] = None


def refresh_commitments(
    start_date: str,
    end_date: str,
    *,
    client_factory: Callable[[], object],
    db_path,
    calendar_ids: Sequence[str],
    tz=None,
    now: Optional[Callable[[], datetime]] = None,
) -> RefreshOutcome:
    """Fetch the range and store it, or record that it failed. Never raises.

    Purpose: CIP-M1.4 with CIP-M2.7 -- the worker's whole job. Opens its own
             ``DatabaseManager`` on ``db_path``, because the screen's SQLite
             connection belongs to the Tk thread.
    Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#5-m2--the-read
    Tests:   tests/test_calendar_commitments.py::test_cipm27_a_failed_fetch_keeps_what_was_known

    The client is built here, inside the guard, so a sign-in that has lapsed
    while the client authenticates is recorded like any other failure.
    """
    from .db_manager import DatabaseManager

    clock = now or datetime.now
    try:
        dates = dates_between(start_date, end_date)
    except (CommitmentParseError, ValueError) as error:
        return RefreshOutcome(dates=[], failure=str(error))
    outcome = RefreshOutcome(dates=dates)
    try:
        result = fetch_commitments(
            start_date, end_date, client=client_factory(),
            calendar_ids=calendar_ids, tz=tz,
        )
    except AuthenticationRequired as error:
        outcome.failure = str(error) or "Google Calendar needs you to sign in again"
        outcome.signed_out = True
    except Exception as error:  # noqa: BLE001 - P15: recorded, never raised
        outcome.failure = str(error) or type(error).__name__

    db_manager = DatabaseManager(db_path=db_path)
    try:
        stamp = clock().isoformat(timespec="seconds")
        if outcome.failure is not None:
            db_manager.record_commitment_fetch_failure(dates, outcome.failure, stamp)
            return outcome
        outcome.result = result
        outcome.written = db_manager.replace_commitments_for_dates(
            dates, result.commitments, stamp
        )
        return outcome
    except Exception as error:  # noqa: BLE001 - the write failed; say so
        outcome.failure = f"the calendar was read but could not be saved: {error}"
        return outcome
    finally:
        db_manager.close()


# ----------------------------------------------------------------- the grid


def slots_held_by(commitment: CalendarCommitment, bounds) -> List[int]:
    """The boxes one commitment holds: every box its times touch (CIP-M3.2).

    Purpose: start rounded down to a box, end rounded up, so a 09:50--10:00
             meeting holds the 09:30 box. Over-reserving is the safe way.
    Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#62-occupancy
    Tests:   tests/test_time_grid.py::test_cipm32_a_commitment_holds_every_slot_it_touches

    Only boxes a day can have (00:00 to the last box, ending 23:30). A
    dismissed or all-day commitment holds none; nor does one of no length.
    """
    if commitment.dismissed or commitment.is_all_day:
        return []
    return _boxes_touched(commitment.start_minutes, commitment.end_minutes, bounds)


def _boxes_touched(start, end, bounds) -> List[int]:
    start, end = int(start), int(end)
    if end <= start:
        return []
    origin = bounds.day_start_minutes
    first = (start - origin) // SLOT_MINUTES
    last = math.ceil((end - origin) / SLOT_MINUTES) - 1
    return [
        index
        for index in range(first, last + 1)
        if origin + index * SLOT_MINUTES >= 0
        and origin + (index + 1) * SLOT_MINUTES <= LAST_DAY_END_MINUTES
    ]


def committed_slots(commitments: Iterable[CalendarCommitment], bounds) -> frozenset:
    """The union of the boxes these commitments hold (CIP-M3.9, D1)."""
    held = set()
    for commitment in commitments:
        held.update(slots_held_by(commitment, bounds))
    return frozenset(held)


def is_off_grid(commitment: CalendarCommitment, bounds) -> bool:
    """Whether some of a timed commitment is where no box can be (D4).

    Before the first box a date can have, or past the last one (23:30). Such
    a commitment is listed in the strip above the grid with its times, so
    nothing it holds is hidden; it still holds the boxes the grid does have.
    """
    if commitment.is_all_day:
        return False
    start, end = int(commitment.start_minutes), int(commitment.end_minutes)
    if end <= start:
        return False
    held = _boxes_touched(start, end, bounds)
    if not held:
        return True
    origin = bounds.day_start_minutes
    first_box = origin + held[0] * SLOT_MINUTES
    last_box_end = origin + (held[-1] + 1) * SLOT_MINUTES
    return start < first_box or end > last_box_end


def is_stale(fetch: Optional[dict], stale_minutes: int, now: datetime) -> bool:
    """A date never read, or last read longer ago than the window (CIP-M5.5, D13)."""
    if not fetch or not fetch.get("fetched_at"):
        return True
    try:
        read = datetime.fromisoformat(str(fetch["fetched_at"]))
    except ValueError:
        return True
    return now - read > timedelta(minutes=max(1, int(stale_minutes)))


def age_text(fetch: Optional[dict]) -> Tuple[str, str]:
    """CIP-M5.4 -- the age of the answer, as a sentence and a status kind."""
    if not fetch:
        return "Calendar not read for this day", "muted"
    as_of = None
    if fetch.get("fetched_at"):
        try:
            as_of = datetime.fromisoformat(str(fetch["fetched_at"])).strftime("%H:%M")
        except ValueError:
            as_of = None
    if fetch.get("last_error"):
        known = f"showing what was known at {as_of}" if as_of else "nothing known yet"
        return f"Calendar read failed — {fetch['last_error']} ({known})", "warning"
    if as_of:
        return f"Calendar as of {as_of}", "muted"
    return "Calendar not read for this day", "muted"
