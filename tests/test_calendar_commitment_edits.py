"""CIP batch 2 -- changing a Google Calendar meeting: the logic and the store.

Purpose: prove CIP-M4.2 to M4.6, M1.6, M0.3b and E1/E2/E5/E6/E9 with a fake
         client and a tmp_path database. No network, no window.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#7-m4--editing-the-calendar-from-inside-the-plan
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_editing.md
"""

from __future__ import annotations

import copy
from datetime import datetime

import pytest

from src.getmoredone.calendar_commitment_edits import (
    MOVE_ONTO_BLOCK,
    CommitmentChanged,
    CommitmentNotMovable,
    EditRequest,
    edit_commitment,
    move_refusal,
    write_commitment_edit,
)
from src.getmoredone.calendar_commitments import parse_event
from src.getmoredone.google_calendar import CalendarEventMissing
from src.getmoredone.models import ActionItem, TimeBlock
from src.getmoredone.time_block_layout import SlotRefusal
from tests.test_calendar_commitments import (  # noqa: F401 - fixture
    BOUNDS,
    DAY,
    TZ,
    _event,
    manager,
)
from tests.test_google_calendar_export_calls import FakeService, _manager

GUESTS = [
    {"email": "me@example.com", "self": True, "organizer": True},
    {"email": "ann@example.com"},
    {"email": "room@resource.calendar.google.com", "resource": True},
]


class EditCalendar:
    """One stored event, changed the way Google changes it, every call recorded."""

    def __init__(self, event, *, fail=None, zone=TZ):
        self.zone = zone  # None: the machine's zone, as the screen reads
        self.event = copy.deepcopy(event)
        self.fail = fail or {}
        self.calls = []

    def _maybe_fail(self, kind):
        if kind in self.fail:
            raise self.fail[kind]
        if self.event is None:
            raise CalendarEventMissing(kind)

    def get_event(self, event_id, calendar_id="primary"):
        self.calls.append(("get", event_id, calendar_id))
        self._maybe_fail("get")
        return copy.deepcopy(self.event)

    def update_event(self, event_id, summary=None, start_datetime=None, duration_minutes=None,
                     calendar_id="primary", *, check=None, send_updates="none"):
        self.calls.append(("read", event_id, calendar_id))
        self._maybe_fail("read")
        if check is not None:
            check(copy.deepcopy(self.event))
        self.calls.append(("update", event_id, calendar_id, summary, start_datetime,
                           duration_minutes, send_updates))
        self._maybe_fail("update")
        if summary:
            self.event["summary"] = summary
        if start_datetime and duration_minutes:
            from datetime import timedelta

            begins = (start_datetime.replace(tzinfo=self.zone) if self.zone is not None
                      else start_datetime.astimezone())
            self.event["start"] = {"dateTime": begins.isoformat()}
            self.event["end"] = {"dateTime": (begins + timedelta(minutes=duration_minutes)).isoformat()}
        return copy.deepcopy(self.event)

    def delete_event(self, event_id, calendar_id="primary", *, send_updates="none"):
        self.calls.append(("delete", event_id, calendar_id, send_updates))
        self._maybe_fail("delete")
        self.event = None

    def writes(self):
        return [c for c in self.calls if c[0] in ("update", "delete")]


def _cached(manager, event, *, at="2026-11-13T09:00:00"):
    """Store the event the way a read would, and return its commitment."""
    parts = parse_event(event, calendar_id="primary", dates=[DAY], tz=TZ)
    manager.replace_commitments_for_dates([DAY], parts, at)
    [commitment] = manager.get_commitments(DAY)
    return commitment


def _write(manager, client, commitment, request, **kwargs):
    return write_commitment_edit(
        commitment, request, client_factory=lambda: client,
        db_path=manager.db.db_path, tz=TZ, **kwargs,
    )


# ---------------------------------------------------------------- M4.2 move


def test_cipm42_a_move_writes_the_new_start_and_the_same_length(manager):
    """M4.2 / E3 -- a 45-minute meeting moved to 13:00 is 13:00 to 13:45."""
    event = _event(end="2026-11-13T10:45:00-08:00")
    commitment = _cached(manager, event)
    client = EditCalendar(event)

    outcome = _write(manager, client, commitment, EditRequest(start_minutes=13 * 60))

    assert outcome.done, outcome.failure
    [(_, _, _, _, start, minutes, _)] = client.writes()
    assert (start, minutes) == (datetime(2026, 11, 13, 13, 0), 45)
    [stored] = manager.get_commitments(DAY)
    assert (stored.start_time, stored.end_time) == ("13:00", "13:45")


def test_cipm42_a_resize_writes_the_new_end(manager):
    """M4.2 / E4 -- a new length keeps the start."""
    event = _event()
    commitment = _cached(manager, event)
    client = EditCalendar(event)

    _write(manager, client, commitment, EditRequest(minutes=90))

    [stored] = manager.get_commitments(DAY)
    assert (stored.start_time, stored.end_time) == ("10:00", "11:30")


def test_cipm42_a_move_onto_a_block_is_refused_before_any_call(manager):
    """E5 -- a box with a Time Block, lunch or another meeting refuses the meeting."""
    commitment = _cached(manager, _event(end="2026-11-13T11:00:00-08:00"))
    block = TimeBlock(DAY, "13:00", "13:30", 30)
    block.slot_index = 10  # 13:00 in the default 08:00 day

    onto_block = move_refusal(commitment, 13 * 60, 30, blocks=[block],
                              commitments=[commitment], bounds=BOUNDS)
    free = move_refusal(commitment, 14 * 60, 30, blocks=[block],
                        commitments=[commitment], bounds=BOUNDS)
    onto_itself = move_refusal(commitment, 10 * 60 + 30, 60, blocks=[],
                               commitments=[commitment], bounds=BOUNDS)

    assert onto_block == MOVE_ONTO_BLOCK
    assert free is None
    assert onto_itself is None  # its own boxes do not hold it back


def test_cipm42_a_move_onto_another_meeting_is_refused(manager):
    """E5 -- another held meeting's boxes are not free."""
    mine = _cached(manager, _event())
    other = parse_event(_event("ev2", start="2026-11-13T14:00:00-08:00",
                               end="2026-11-13T15:00:00-08:00"),
                        calendar_id="primary", dates=[DAY], tz=TZ)[0]

    assert move_refusal(mine, 14 * 60, 30, blocks=[], commitments=[mine, other],
                        bounds=BOUNDS) == SlotRefusal.SLOT_COMMITTED


@pytest.mark.parametrize("event", [
    _event(start="2026-11-13T22:00:00-08:00", end="2026-11-14T01:00:00-08:00"),
    {**_event(), "start": {"date": DAY}, "end": {"date": "2026-11-14"}},
], ids=["over-midnight", "all-day"])
def test_cipm42_a_split_or_all_day_meeting_cannot_be_moved(manager, event):
    """E2 -- no start or end on this date to move; nothing is written."""
    commitment = _cached(manager, event)
    client = EditCalendar(event)

    with pytest.raises(CommitmentNotMovable):
        edit_commitment(client, commitment, EditRequest(start_minutes=9 * 60), tz=TZ)

    assert client.calls == []


# ------------------------------------------------------------- M4.3 retitle


def test_cipm43_retitle_changes_the_summary_only(manager):
    """M4.3 -- a rename sends a summary and no time."""
    event = _event()
    commitment = _cached(manager, event)
    client = EditCalendar(event)

    outcome = _write(manager, client, commitment, EditRequest(title="  Budget review "))

    [(_, _, _, summary, start, minutes, _)] = client.writes()
    assert (summary, start, minutes) == ("Budget review", None, None)
    assert manager.get_commitments(DAY)[0].title == "Budget review"
    assert outcome.message == "Renamed to “Budget review” in Google Calendar."


def test_cipm43_an_empty_title_is_refused(manager):
    """M4.3 -- an empty title is refused before any call."""
    event = _event()
    client = EditCalendar(event)

    with pytest.raises(ValueError):
        edit_commitment(client, _cached(manager, event), EditRequest(title="   "), tz=TZ)

    assert client.calls == []


# --------------------------------------------------------------- M4.4 delete


def test_cipm44_a_gone_event_counts_as_deleted(manager):
    """M4.4 -- a 404 is the end state asked for: the cache row goes."""
    event = _event()
    commitment = _cached(manager, event)
    client = EditCalendar(event)
    client.event = None

    outcome = _write(manager, client, commitment, EditRequest(delete=True))

    assert outcome.done, outcome.failure
    assert manager.get_commitments(DAY) == []


def test_cipm44_delete_removes_the_event_and_the_row(manager):
    """M4.4 -- the Google event is deleted, then its row."""
    event = _event()
    commitment = _cached(manager, event)
    client = EditCalendar(event)

    _write(manager, client, commitment, EditRequest(delete=True), send_updates="all")

    assert client.writes() == [("delete", "ev1", "primary", "all")]
    assert manager.get_commitments(DAY) == []


def test_cipm03b_deleting_a_commitment_leaves_its_action_item(manager):
    """M0.3b -- the meeting is deleted where it lives; the action item stays."""
    item = ActionItem(who="me", title="Board meeting", start_date=DAY)
    manager.create_action_item(item)
    event = _event()
    commitment = _cached(manager, event)

    _write(manager, EditCalendar(event), commitment, EditRequest(delete=True))

    assert manager.get_action_item(item.id) is not None


# ------------------------------------------------------- M4.5 never ahead


def test_cipm45_a_failed_write_leaves_the_cache_and_grid_as_they_were(manager):
    """M4.5 -- Google refused: the row is exactly what it was."""
    event = _event()
    commitment = _cached(manager, event)
    before = manager.get_commitments(DAY)
    client = EditCalendar(event, fail={"update": RuntimeError("Failed to update: 500")})

    outcome = _write(manager, client, commitment, EditRequest(start_minutes=13 * 60))

    assert not outcome.done
    assert "500" in outcome.failure
    assert manager.get_commitments(DAY) == before


@pytest.mark.parametrize("change", [
    {"start": {"dateTime": "2026-11-13T09:30:00-08:00"}},
    {"summary": "Renamed elsewhere"},
    {"attendees": [{"email": "me@x", "self": True, "responseStatus": "declined"}]},
    {"attendees": [{"email": "me@x", "self": True}, {"email": "new@x"}]},
], ids=["moved", "renamed", "declined", "guest-added"])
def test_cipm45_a_changed_event_is_not_overwritten(manager, change):
    """E6 -- Google's copy differs from the Plan's: nothing is written."""
    event = _event()
    commitment = _cached(manager, event)
    client = EditCalendar({**event, **change})

    with pytest.raises(CommitmentChanged):
        edit_commitment(client, commitment, EditRequest(start_minutes=13 * 60), tz=TZ)

    assert client.writes() == []


def test_cipm45_a_changed_event_is_not_deleted(manager):
    """E6 -- the same check before a delete."""
    event = _event()
    commitment = _cached(manager, event)
    client = EditCalendar({**event, "summary": "Renamed elsewhere"})

    outcome = _write(manager, client, commitment, EditRequest(delete=True))

    assert not outcome.done
    assert client.writes() == []
    assert len(manager.get_commitments(DAY)) == 1


def test_cipm45_the_cache_takes_googles_reply_not_the_request(manager):
    """E9 -- what is stored is what Google returned."""
    event = _event()
    commitment = _cached(manager, event)

    class Rounding(EditCalendar):
        def update_event(self, *args, **kwargs):
            reply = super().update_event(*args, **kwargs)
            reply["end"] = {"dateTime": "2026-11-13T14:00:00-08:00"}  # Google's own answer
            return reply

    _write(manager, Rounding(event), commitment, EditRequest(start_minutes=13 * 60))

    assert manager.get_commitments(DAY)[0].end_time == "14:00"


# -------------------------------------------------------- M4.6 and E1, real client


def test_cipm46_attendees_conference_reminders_recurrence_description_survive():
    """M4.6 -- the real ``update_event`` writes back everything it did not name."""
    stored = {
        **_event(),
        "attendees": GUESTS,
        "conferenceData": {"entryPoints": [{"uri": "https://meet.example/abc"}]},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 5}]},
        "recurringEventId": "series-1",
        "description": "Agenda",
    }
    service = FakeService(stored=copy.deepcopy(stored))
    commitment = parse_event(stored, calendar_id="primary", dates=[DAY], tz=TZ)[0]

    edit_commitment(_manager(service), commitment, EditRequest(start_minutes=13 * 60),
                    tz=TZ, send_updates="all")

    [update] = service.of_kind("update")
    body = update["body"]
    for key in ("attendees", "conferenceData", "reminders", "recurringEventId", "description"):
        assert body[key] == stored[key], key
    assert update["eventId"] == "ev1"  # the occurrence's own id: that occurrence only
    assert update["sendUpdates"] == "all"


def test_cipm46_a_check_that_refuses_stops_the_real_update():
    """E6 through the real client: ``check`` raising means no update call."""
    service = FakeService(stored=copy.deepcopy(_event(summary="Renamed elsewhere")))
    commitment = parse_event(_event(), calendar_id="primary", dates=[DAY], tz=TZ)[0]

    with pytest.raises(CommitmentChanged):
        edit_commitment(_manager(service), commitment, EditRequest(title="X"), tz=TZ)

    assert service.of_kind("update") == []


def test_cipe1_the_export_still_sends_none():
    """E1 -- the default the export relies on is unchanged, for update and delete."""
    service = FakeService(stored=copy.deepcopy(_event()))
    manager = _manager(service)

    manager.update_event(event_id="ev1", summary="A")
    manager.delete_event("ev1")

    assert service.of_kind("update")[0]["sendUpdates"] == "none"
    assert service.of_kind("delete")[0]["sendUpdates"] == "none"


def test_cipe1_guests_are_counted_without_self_or_rooms():
    """E1 -- the number the user is asked about."""
    [commitment] = parse_event({**_event(), "attendees": GUESTS},
                               calendar_id="primary", dates=[DAY], tz=TZ)

    assert commitment.guest_count == 1


# --------------------------------------------------------------- M1.6 store


def test_cipm16_apply_commitment_edit_replaces_only_that_event_on_that_date(manager):
    """M1.6 -- one event on one date; its id kept; everything else untouched."""
    a = parse_event(_event("a"), calendar_id="primary", dates=[DAY], tz=TZ)
    b = parse_event(_event("b", start="2026-11-13T15:00:00-08:00",
                           end="2026-11-13T15:30:00-08:00"),
                    calendar_id="primary", dates=[DAY], tz=TZ)
    manager.replace_commitments_for_dates([DAY], a + b, "2026-11-13T09:00:00")
    before = {c.event_id: c for c in manager.get_commitments(DAY)}
    fetch_before = manager.get_commitment_fetch(DAY)
    moved = parse_event(_event("a", start="2026-11-13T12:00:00-08:00",
                               end="2026-11-13T12:30:00-08:00"),
                        calendar_id="primary", dates=[DAY], tz=TZ)

    manager.apply_commitment_edit("a", DAY, moved, "2026-11-13T10:00:00")

    after = {c.event_id: c for c in manager.get_commitments(DAY)}
    assert after["a"].start_time == "12:00"
    assert after["a"].id == before["a"].id
    assert after["b"] == before["b"]
    assert manager.get_commitment_fetch(DAY) == fetch_before
