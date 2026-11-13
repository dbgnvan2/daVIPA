"""CIP batch 1 -- the commitment store, the read, and the write paths' refusal.

Purpose: prove CIP-M0.1, M0.3a, M1, M2, M3.1, M3.3, M3.4 and D4/D6/D12 with a
         fake Google client and a tmp_path database. Nothing here touches the
         network or opens a window.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md
"""

from __future__ import annotations

import inspect
import sqlite3
from dataclasses import fields
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.getmoredone import calendar_commitments as cc
from src.getmoredone import models
from src.getmoredone.calendar_commitments import (
    CommitmentFetchError,
    exclusion_of,
    fetch_commitments,
    parse_event,
    refresh_commitments,
)
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.db_manager_commitments import (
    CommitmentDateError,
    CommitmentNotDismissableError,
)
from src.getmoredone.google_calendar import (
    BLOCK_ID_PROPERTY,
    AuthenticationRequired,
    CalendarForbidden,
)
from src.getmoredone.models import ActionItem, BlockType, CalendarCommitment, TimeBlock
from src.getmoredone.time_block_layout import (
    DayBounds,
    SlotRefusal,
    SlotRefusedError,
)
from tests.test_google_calendar_export_calls import FakeService, _http_error, _manager

TZ = ZoneInfo("Etc/GMT+8")  # fixed -08:00; regional zones move with tzdata
DAY = "2026-11-13"
NEXT = "2026-11-14"
BOUNDS = DayBounds()


@pytest.fixture
def manager(tmp_path):
    db = DatabaseManager(str(tmp_path / "commitments.db"))
    yield db
    db.close()


def _event(event_id="ev1", start="2026-11-13T10:00:00-08:00", end="2026-11-13T10:30:00-08:00",
           summary="Board meeting", **extra):
    event = {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        "organizer": {"self": True},
    }
    event.update(extra)
    return event


class FakeCalendar:
    """``list_events_between`` per calendar id, recording every call."""

    def __init__(self, by_calendar=None, errors=None):
        self.by_calendar = by_calendar or {}
        self.errors = errors or {}
        self.calls = []

    def list_events_between(self, time_min, time_max, calendar_id="primary"):
        self.calls.append((time_min, time_max, calendar_id))
        if calendar_id in self.errors:
            raise self.errors[calendar_id]
        return [dict(e) for e in self.by_calendar.get(calendar_id, [])]


def _commitment(start_minutes, end_minutes, *, day=DAY, event_id="ev1", can_edit=True, title="Meeting"):
    from src.getmoredone.time_block_layout import format_hhmm

    return CalendarCommitment(
        event_id=event_id, calendar_id="primary", commitment_date=day,
        start_time=format_hhmm(start_minutes), end_time=format_hhmm(end_minutes),
        start_minutes=start_minutes, end_minutes=end_minutes, title=title,
        can_edit=can_edit,
    )


def _block(manager, slot, minutes=30, day=DAY, label="Work"):
    block = TimeBlock(
        block_date=day, start_time="", end_time="", planned_minutes=minutes,
        label=label, block_type=BlockType.BREAK,
    )
    return manager.add_block_at(block, slot, BOUNDS)


# =====================================================================
# M1 -- the store
# =====================================================================


def test_cipm11_the_table_exists_fresh_and_migrated(tmp_path):
    """CIP-M1.1 -- fresh databases get the table; an older, narrower one gains columns."""
    path = str(tmp_path / "old.db")
    fresh = DatabaseManager(path)
    names = {r[1] for r in fresh.db.conn.execute("PRAGMA table_info(calendar_commitments)")}
    fresh.close()
    assert names == {
        "id", "event_id", "calendar_id", "commitment_date", "start_time", "end_time",
        "start_minutes", "end_minutes", "title", "is_all_day", "response_status",
        "transparency", "can_edit", "is_recurring_instance", "dismissed",
        "fetched_at", "created_at", "updated_at",
        # Reason (b), CIP batch 2: E1 asks about guests from the cache.
        "guest_count",
    }

    raw = sqlite3.connect(path)
    raw.execute("DROP TABLE calendar_commitments")
    raw.execute("CREATE TABLE calendar_commitments (id TEXT PRIMARY KEY, event_id TEXT)")
    raw.commit()
    raw.close()

    migrated = DatabaseManager(path)
    after = {r[1] for r in migrated.db.conn.execute("PRAGMA table_info(calendar_commitments)")}
    migrated.close()
    assert after == names


def test_cipm11_the_migration_runs_twice_safely(tmp_path):
    path = str(tmp_path / "twice.db")
    for _ in range(2):
        DatabaseManager(path).close()
    third = DatabaseManager(path)
    third.replace_commitments_for_dates([DAY], [_commitment(600, 630)], "2026-11-13T09:00:00")
    assert len(third.get_commitments(DAY)) == 1
    third.close()


def test_cipm12_existing_models_construct_positionally():
    """CIP-M1.2 -- appended last, so no existing model's fields moved."""
    source_lines = {
        name: inspect.getsourcelines(obj)[1]
        for name, obj in vars(models).items()
        if inspect.isclass(obj) and obj.__module__ == models.__name__
    }
    assert max(source_lines, key=source_lines.get) == "CalendarCommitment"
    assert [f.name for f in fields(CalendarCommitment)][:7] == [
        "event_id", "calendar_id", "commitment_date", "start_time", "end_time",
        "start_minutes", "end_minutes",
    ]
    block = TimeBlock(DAY, "09:00", "09:30", 30)
    assert (block.block_date, block.start_time, block.planned_minutes) == (DAY, "09:00", 30)


def test_cipm13_three_states_of_a_date(manager):
    """CIP-M1.3 -- never read, read and empty, read and failed are three answers."""
    assert manager.get_commitment_fetch(DAY) is None

    manager.replace_commitments_for_dates([DAY], [], "2026-11-13T09:00:00")
    empty = manager.get_commitment_fetch(DAY)
    assert empty == {"fetched_at": "2026-11-13T09:00:00", "last_error": None,
                     "attempted_at": "2026-11-13T09:00:00", "warning": None}
    assert manager.get_commitments(DAY) == []

    manager.record_commitment_fetch_failure([DAY], "503", "2026-11-13T09:20:00")
    failed = manager.get_commitment_fetch(DAY)
    assert failed["last_error"] == "503"
    assert failed["fetched_at"] == "2026-11-13T09:00:00"


def test_cipm14_only_the_fetched_dates_change(manager):
    """CIP-M1.4 -- a fetch of one date leaves every other date's rows alone."""
    manager.replace_commitments_for_dates(
        [DAY, NEXT],
        [_commitment(600, 630), _commitment(600, 630, day=NEXT, event_id="ev2")],
        "t1",
    )

    manager.replace_commitments_for_dates([DAY], [], "t2")

    assert manager.get_commitments(DAY) == []
    assert [c.event_id for c in manager.get_commitments(NEXT)] == ["ev2"]
    assert manager.get_commitment_fetch(NEXT)["fetched_at"] == "t1"
    with pytest.raises(CommitmentDateError):
        manager.replace_commitments_for_dates([DAY], [_commitment(1, 2, day=NEXT)], "t3")
    assert [c.event_id for c in manager.get_commitments(NEXT)] == ["ev2"]


def test_cipm14_a_failure_part_way_writes_nothing(manager, monkeypatch):
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630)], "t1")
    real_insert = manager._insert_commitment
    calls = []

    def insert_then_fail(conn, commitment):
        calls.append(commitment)
        if len(calls) == 2:
            raise sqlite3.OperationalError("disk I/O error")
        real_insert(conn, commitment)

    monkeypatch.setattr(manager, "_insert_commitment", insert_then_fail)
    with pytest.raises(sqlite3.OperationalError):
        manager.replace_commitments_for_dates(
            [DAY], [_commitment(700, 730, event_id="a"), _commitment(800, 830, event_id="b")], "t2"
        )

    assert [c.event_id for c in manager.get_commitments(DAY)] == ["ev1"]
    assert manager.get_commitment_fetch(DAY)["fetched_at"] == "t1"


def test_cipm15_dismissal_survives_a_refetch(manager):
    """CIP-M1.5 -- keyed on event id and date; everything else is replaced."""
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, can_edit=False)], "t1")
    held = manager.get_commitments(DAY)[0]
    manager.set_commitment_dismissed(held.id, True)

    manager.replace_commitments_for_dates(
        [DAY], [_commitment(660, 690, can_edit=False, title="Moved")], "t2"
    )

    again = manager.get_commitments(DAY)[0]
    assert again.dismissed is True
    assert (again.start_minutes, again.title) == (660, "Moved")


# =====================================================================
# M2 -- the read
# =====================================================================


def test_cipm21_seven_days_is_one_call_per_calendar():
    """CIP-M2.1 -- the whole range in one call per calendar, bounded by local midnights."""
    client = FakeCalendar({"primary": [], "work": []})

    result = fetch_commitments(DAY, "2026-11-19", client=client,
                               calendar_ids=["primary", "work"], tz=TZ)

    assert [call[2] for call in client.calls] == ["primary", "work"]
    assert client.calls[0][:2] == ("2026-11-13T00:00:00-08:00", "2026-11-20T00:00:00-08:00")
    assert len(result.dates) == 7


def test_cipm21_every_page_is_read():
    """CIP-M2.1 / D11 -- the real client follows ``nextPageToken`` to the end."""
    service = FakeService(pages=[
        {"items": [{"id": "a"}], "nextPageToken": "p2"},
        {"items": [{"id": "b"}]},
    ])

    events = _manager(service).list_events_between("t0", "t1", "work")

    assert [e["id"] for e in events] == ["a", "b"]
    listed = service.of_kind("list")
    assert [k["pageToken"] for k in listed] == [None, "p2"]
    assert listed[0]["calendarId"] == "work"
    assert listed[0]["singleEvents"] is True
    assert (listed[0]["timeMin"], listed[0]["timeMax"]) == ("t0", "t1")


def test_cipm23_an_offset_time_is_stored_as_local_wall_clock():
    """CIP-M2.3 / D5 -- 17:00Z is 09:00 in Vancouver, converted once and stored."""
    event = _event(start="2026-11-13T17:00:00Z", end="2026-11-13T18:15:00+00:00")

    [part] = parse_event(event, calendar_id="primary", dates=[DAY], tz=TZ)

    assert (part.start_time, part.end_time) == ("09:00", "10:15")
    assert (part.start_minutes, part.end_minutes) == (540, 615)


def test_cipm23_an_event_over_midnight_is_two_commitments():
    """D4 -- one commitment per date, each clipped to its date."""
    event = _event(start="2026-11-13T23:00:00-08:00", end="2026-11-14T01:00:00-08:00")

    parts = parse_event(event, calendar_id="primary", dates=[DAY, NEXT], tz=TZ)

    assert [(p.commitment_date, p.start_minutes, p.end_minutes) for p in parts] == [
        (DAY, 1380, 1440), (NEXT, 0, 60),
    ]
    assert parts[0].end_time == "24:00"


def test_cipd4_a_date_before_the_range_is_not_written(manager):
    """D4 -- an event that began before the range only writes the dates read."""
    client = FakeCalendar({"primary": [
        _event(start="2026-11-12T23:00:00-08:00", end="2026-11-13T01:00:00-08:00")
    ]})

    outcome = refresh_commitments(
        DAY, DAY, client_factory=lambda: client, db_path=manager.db.db_path,
        calendar_ids=["primary"], tz=TZ,
    )

    assert outcome.failure is None
    assert manager.get_commitments("2026-11-12") == []
    assert manager.get_commitment_fetch("2026-11-12") is None
    assert [(c.start_minutes, c.end_minutes) for c in manager.get_commitments(DAY)] == [(0, 60)]


def test_cipm24_an_all_day_event_holds_no_slot():
    """CIP-M2.4 -- ``start.date`` gives ``is_all_day`` and no boxes."""
    event = {"id": "trip", "summary": "Travelling",
             "start": {"date": DAY}, "end": {"date": "2026-11-15"}}

    parts = parse_event(event, calendar_id="primary", dates=[DAY, NEXT], tz=TZ)

    assert [(p.commitment_date, p.is_all_day) for p in parts] == [(DAY, True), (NEXT, True)]
    assert cc.committed_slots(parts, BOUNDS) == frozenset()


@pytest.mark.parametrize("change, reason", [
    ({"status": "cancelled"}, "cancelled"),
    ({"attendees": [{"self": True, "responseStatus": "declined"}]}, "declined"),
    ({"transparency": "transparent"}, "free"),
    ({"extendedProperties": {"private": {BLOCK_ID_PROPERTY: "b1"}}}, "exported"),
])
def test_cipm25_each_exclusion_is_counted(change, reason):
    """CIP-M2.5 -- each rule left out on its own, and counted under its own word."""
    held = _event("keep", start="2026-11-13T09:00:00-08:00", end="2026-11-13T09:30:00-08:00")
    excluded = _event("drop", **change)
    client = FakeCalendar({"primary": [held, excluded]})

    result = fetch_commitments(DAY, DAY, client=client, calendar_ids=["primary"], tz=TZ)

    assert [c.event_id for c in result.commitments] == ["keep"]
    assert result.excluded == {r: (1 if r == reason else 0) for r in cc.EXCLUSION_REASONS}
    assert exclusion_of(held) is None


def test_cipm26_an_unparseable_event_is_named_not_guessed():
    broken = _event("bad", summary="Odd one", start="2026-11-13T09:00:00")  # no offset

    result = fetch_commitments(DAY, DAY, client=FakeCalendar({"primary": [broken]}),
                               calendar_ids=["primary"], tz=TZ)

    assert result.commitments == []
    assert result.unparseable == ["Odd one"]


def test_cipm27_a_failed_fetch_keeps_what_was_known(manager):
    """CIP-M2.7 / D6 -- a transient failure replaces nothing and is recorded."""
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630)], "2026-11-13T08:00:00")
    client = FakeCalendar(errors={"primary": RuntimeError("Failed after 3 attempts: 503")})

    outcome = refresh_commitments(
        DAY, DAY, client_factory=lambda: client, db_path=manager.db.db_path,
        calendar_ids=["primary"], tz=TZ, now=lambda: datetime(2026, 11, 13, 9, 0),
    )

    assert outcome.failure == "Failed after 3 attempts: 503"
    assert [c.event_id for c in manager.get_commitments(DAY)] == ["ev1"]
    assert manager.get_commitment_fetch(DAY) == {
        "fetched_at": "2026-11-13T08:00:00",
        "last_error": "Failed after 3 attempts: 503",
        "attempted_at": "2026-11-13T09:00:00",
        "warning": None,
    }


def test_cipm22_a_lapsed_sign_in_is_recorded_not_raised(manager):
    """CIP-M2.2 -- ``AuthenticationRequired`` while the client is built is an outcome."""
    def factory():
        raise AuthenticationRequired("Google Calendar needs you to sign in again")

    outcome = refresh_commitments(DAY, DAY, client_factory=factory,
                                  db_path=manager.db.db_path, calendar_ids=["primary"], tz=TZ)

    assert outcome.signed_out is True
    assert manager.get_commitment_fetch(DAY)["last_error"] == outcome.failure


def test_cipd6_a_forbidden_calendar_is_skipped_and_named():
    """D6 -- a permanent refusal on one calendar does not block the others."""
    client = FakeCalendar(
        {"primary": [_event()]},
        errors={"shared": CalendarForbidden("Failed to list: 403 forbidden")},
    )

    result = fetch_commitments(DAY, DAY, client=client, calendar_ids=["shared", "primary"], tz=TZ)

    assert [c.event_id for c in result.commitments] == ["ev1"]
    assert list(result.skipped_calendars) == ["shared"]
    with pytest.raises(CommitmentFetchError):
        fetch_commitments(DAY, DAY, client=client, calendar_ids=["shared"], tz=TZ)


def test_cipd6_a_non_retryable_403_is_forbidden():
    """D6 -- the client tells a forbidden calendar apart from a rate limit."""
    service = FakeService(errors={"list": [_http_error(403, "forbidden")]})

    with pytest.raises(CalendarForbidden):
        _manager(service).list_events_between("t0", "t1", "shared")


def test_cipm28_one_event_on_two_calendars_is_one_commitment():
    """CIP-M2.8 -- one commitment, decided by the copy on the calendar listed first.

    ``organizer.self`` describes the calendar a copy is on: a colleague's
    shared calendar says "organizer" for a meeting the user only attends.
    """
    mine = _event(organizer={"self": False})
    colleagues = _event(organizer={"self": True})

    result = fetch_commitments(DAY, DAY, client=FakeCalendar({"a": [mine], "b": [colleagues]}),
                               calendar_ids=["a", "b"], tz=TZ)

    assert len(result.commitments) == 1
    assert result.commitments[0].can_edit is False
    assert result.commitments[0].calendar_id == "a"


def test_cipm28_declined_on_my_calendar_is_left_out_whatever_a_shared_copy_says():
    """CIP-M2.8 -- the user's own copy decides; the colleague's "accepted" does not."""
    declined = _event(attendees=[{"self": True, "responseStatus": "declined"}])
    accepted = _event(attendees=[{"self": True, "responseStatus": "accepted"}])
    client = FakeCalendar({"primary": [declined], "team": [accepted]})

    result = fetch_commitments(DAY, DAY, client=client, calendar_ids=["primary", "team"], tz=TZ)

    assert result.commitments == []
    assert result.excluded["declined"] == 1


@pytest.mark.parametrize("event_fields, editable", [
    ({"organizer": {"self": True}}, True),
    ({"organizer": {"self": False}, "guestsCanModify": True}, True),
    ({"organizer": {"self": False}}, False),
])
def test_cipm34_can_edit_comes_from_the_event(event_fields, editable):
    event = _event()
    event.update(event_fields)

    [part] = parse_event(event, calendar_id="primary", dates=[DAY], tz=TZ)

    assert part.can_edit is editable


# =====================================================================
# M0 -- an event is both an action item and a commitment
# =====================================================================


def test_cipm01_one_event_is_both_an_item_and_a_commitment(manager, monkeypatch):
    """CIP-M0.1 -- the importer and the read both act on one event, by design."""
    from src.getmoredone import calendar_importer

    event = _event()

    class ImporterClient:
        def __init__(self, *a, **k):
            self.service = FakeService(pages=[{"items": [dict(event)]}])

    monkeypatch.setattr(calendar_importer, "GoogleCalendarManager", ImporterClient)
    stats = calendar_importer.import_upcoming_calendar_events(db_path=manager.db.db_path)
    outcome = refresh_commitments(DAY, DAY, client_factory=lambda: FakeCalendar({"primary": [event]}),
                                  db_path=manager.db.db_path, calendar_ids=["primary"], tz=TZ)

    assert stats["created"] == 1
    assert outcome.written == 1
    items = manager.db.conn.execute(
        "SELECT title FROM action_items WHERE title = 'Board meeting'"
    ).fetchall()
    assert len(items) == 1
    assert [c.title for c in manager.get_commitments(DAY)] == ["Board meeting"]


def test_cipm03_deleting_the_item_leaves_the_commitment(manager):
    """CIP-M0.3a -- the item is *what*; the commitment is *when*. Neither owns the other."""
    item = ActionItem(who="Calendar", title="Board meeting", start_date=DAY)
    manager.create_action_item(item)
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, title="Board meeting")], "t1")

    manager.delete_action_item(item.id)

    assert manager.get_action_item(item.id) is None
    assert [c.title for c in manager.get_commitments(DAY)] == ["Board meeting"]


# =====================================================================
# M3 -- the grid refuses committed boxes, on every write path
# =====================================================================


def _hold_ten(manager):
    # 10:00--10:30 is box 4 of the default 08:00 day.
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630)], "t1")


def _add(manager):
    _hold_ten(manager)
    _block(manager, 4)


def _move(manager):
    block = _block(manager, 1)
    _hold_ten(manager)
    manager.place_block_at(block.id, 4, BOUNDS)


def _resize(manager):
    block = _block(manager, 3)
    _hold_ten(manager)
    manager.set_block_length(block.id, 60, BOUNDS)


def _repair(manager):
    block = _block(manager, 1)
    # A row from before PD-M14.4: box 1 (08:30), recorded as planned at 10:00.
    manager.db.conn.execute(
        "UPDATE time_blocks SET start_time = '10:00', end_time = '10:30' WHERE id = ?",
        (block.id,),
    )
    manager.db.conn.commit()
    _hold_ten(manager)
    repair = manager.repair_slots_from_times(DAY, BOUNDS)
    assert repair.moved == []
    assert manager.get_time_block(block.id).slot_index == 1
    raise SlotRefusedError(repair.refused)


@pytest.mark.parametrize("write", [_add, _move, _resize, _repair],
                         ids=["add", "move", "resize", "repair"])
def test_cipm33_every_write_path_refuses_a_committed_slot(manager, write):
    """CIP-M3.3 / D2 -- each db writer reads the date's commitments itself."""
    with pytest.raises(SlotRefusedError) as refused:
        write(manager)

    assert refused.value.reason == SlotRefusal.SLOT_COMMITTED
    assert all(b.slot_index != 4 for b in manager.get_time_blocks(DAY))


@pytest.mark.parametrize("held", [True, False], ids=["under-a-meeting", "control"])
def test_cipm33_adoption_does_not_put_a_block_under_a_meeting(manager, held):
    """CIP-M3.3 -- adoption asks ``can_place`` with the date's commitments.

    ``adopt_legacy_day`` returns only what it adopted, so the control case
    shows the same row is adopted when no meeting is there.
    """
    if held:
        _hold_ten(manager)
    old_id = manager.create_time_block(TimeBlock(
        block_date=DAY, start_time="10:00", end_time="10:30", planned_minutes=30,
        label="Old", block_type=BlockType.BREAK,
    ))

    adopted = manager.adopt_legacy_day(DAY, BOUNDS)

    assert adopted == ([] if held else [old_id])
    assert manager.get_time_block(old_id).slot_index == (None if held else 4)


def test_cipd12_a_block_under_a_new_commitment_can_still_be_shortened(manager):
    """D12 -- planned work a meeting lands on can be shortened, nudged or moved off."""
    block = _block(manager, 4, minutes=60)  # boxes 4 and 5
    _hold_ten(manager)

    manager.set_block_length(block.id, 30, BOUNDS)        # shorten, inside box 4
    manager.place_block_at(block.id, 6, BOUNDS)           # move off
    with pytest.raises(SlotRefusedError) as back:
        manager.place_block_at(block.id, 4, BOUNDS)       # newly entering box 4

    assert back.value.reason == SlotRefusal.SLOT_COMMITTED
    assert manager.get_time_block(block.id).slot_index == 6


def test_cipm34_dismissing_frees_the_slots_locally(manager):
    """CIP-M3.4 -- someone else's meeting can be ignored for its date; Google is not called."""
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, can_edit=False)], "t1")
    held = manager.get_commitments(DAY)[0]
    with pytest.raises(SlotRefusedError):
        _block(manager, 4)

    manager.set_commitment_dismissed(held.id, True)
    placed = _block(manager, 4)

    assert placed.slot_index == 4
    assert manager.get_commitments(DAY)[0].dismissed is True
    editable = _commitment(700, 730, event_id="mine", can_edit=True)
    manager.replace_commitments_for_dates([DAY], [manager.get_commitments(DAY)[0], editable], "t2")
    mine = [c for c in manager.get_commitments(DAY) if c.event_id == "mine"][0]
    with pytest.raises(CommitmentNotDismissableError):
        manager.set_commitment_dismissed(mine.id, True)


# =====================================================================
# M3.1 -- the export's own events are never commitments (P7)
# =====================================================================


class StoringCalendar:
    """A calendar that keeps what the exporter sends and lists it back.

    Bodies are stored the way Google returns them: ``dateTime`` with the
    machine's offset, the private marker as sent, and the user as organizer.
    """

    def __init__(self):
        self.events = {}
        self._next = 0

    def create_event(self, *, summary, start_datetime, duration_minutes,
                     description=None, calendar_id="primary",
                     private_properties=None, reminders=None):
        self._next += 1
        event_id = f"evt-{self._next}"
        start = start_datetime.astimezone()
        self.events[event_id] = {
            "id": event_id, "summary": summary, "status": "confirmed",
            "organizer": {"self": True},
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": (start + timedelta(minutes=duration_minutes)).isoformat()},
            "extendedProperties": {"private": dict(private_properties or {})},
        }
        return {"id": event_id}

    def update_event(self, **kwargs):  # pragma: no cover - a first export creates
        raise AssertionError("a first export creates, it does not update")

    def delete_event(self, event_id, calendar_id="primary"):
        self.events.pop(event_id, None)

    def list_day_events(self, block_date, calendar_id="primary"):
        return [dict(e) for e in self.events.values()]

    def list_events_between(self, time_min, time_max, calendar_id="primary"):
        return [dict(e) for e in self.events.values()]


def test_cipm31_an_exported_day_read_back_holds_no_slot(manager):
    """CIP-M3.1 -- export a day, read it back: the grid is unchanged."""
    from src.getmoredone.calendar_exporter import export_day

    first = _block(manager, 2, label="Deep work")
    second = _block(manager, 5, minutes=60, label="Review")
    calendar = StoringCalendar()

    exported = export_day(DAY, client=calendar, db_path=manager.db.db_path, bounds=BOUNDS)
    outcome = refresh_commitments(DAY, DAY, client_factory=lambda: calendar,
                                  db_path=manager.db.db_path, calendar_ids=["primary"])

    assert len(calendar.events) == 2, exported
    assert outcome.failure is None
    assert outcome.result.excluded["exported"] == 2
    assert manager.get_commitments(DAY) == []
    assert manager._committed_for(DAY, BOUNDS) == frozenset()
    manager.place_block_at(first.id, 3, BOUNDS)
    manager.place_block_at(second.id, 2, BOUNDS)


# =====================================================================
# D6 -- a read that worked but did not read everything (learning-qa, CIP)
# =====================================================================


def test_cipd6_a_skipped_calendar_keeps_its_known_meetings(manager):
    """D6 -- a revoked calendar did not say its meetings are gone; they stay, and the date says so."""
    manager.replace_commitments_for_dates([DAY], [
        _commitment(600, 630, event_id="team-1"),
        _commitment(700, 730, event_id="old-primary"),
    ], "2026-11-13T08:00:00")
    with manager.transaction() as conn:
        conn.execute("UPDATE calendar_commitments SET calendar_id = 'team' WHERE event_id = 'team-1'")
    client = FakeCalendar({"primary": []}, errors={"team": CalendarForbidden("403 forbidden")})

    outcome = refresh_commitments(DAY, DAY, client_factory=lambda: client,
                                  db_path=manager.db.db_path, calendar_ids=["primary", "team"],
                                  tz=TZ, now=lambda: datetime(2026, 11, 13, 9, 0))

    assert outcome.failure is None
    assert [c.event_id for c in manager.get_commitments(DAY)] == ["team-1"]
    fetch = manager.get_commitment_fetch(DAY)
    assert fetch["warning"] == "not read: team"
    assert fetch["last_error"] is None
    assert cc.age_text(fetch, now=datetime(2026, 11, 13, 9, 5)) == (
        "Calendar as of 09:00 — not read: team", "warning"
    )


def test_cipd6_an_unparseable_event_keeps_its_known_row(manager):
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, event_id="odd")], "t1")
    broken = _event("odd", summary="Odd one", start="2026-11-13T09:00:00")  # no offset

    refresh_commitments(DAY, DAY, client_factory=lambda: FakeCalendar({"primary": [broken]}),
                        db_path=manager.db.db_path, calendar_ids=["primary"], tz=TZ)

    assert [c.event_id for c in manager.get_commitments(DAY)] == ["odd"]
    assert manager.get_commitment_fetch(DAY)["warning"] == "could not read Odd one"


def test_cipd6_a_403_with_no_readable_reason_is_not_forbidden():
    """D6 -- only a 403 whose reason is known is "forbidden for good"."""
    service = FakeService(errors={"list": [_http_error(403)]})  # body "{}": no reason

    with pytest.raises(RuntimeError) as raised:
        _manager(service).list_events_between("t0", "t1", "shared")

    assert not isinstance(raised.value, CalendarForbidden)


def test_cipm54_an_answer_from_another_day_shows_its_date():
    """CIP-M5.4 -- yesterday's 16:40 does not read as this afternoon's."""
    fetch = {"fetched_at": "2026-11-12T16:40:00", "last_error": "offline", "warning": None}

    text, kind = cc.age_text(fetch, now=datetime(2026, 11, 13, 9, 0))

    assert text == "Calendar read failed — offline (showing what was known at 2026-11-12 16:40)"
    assert kind == "warning"


# =====================================================================
# Dismissal across reads (cold review, CIP)
# =====================================================================


def test_cipm15_a_row_keeps_its_id_across_reads(manager):
    """A menu opened before a read still names its meeting after it."""
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, can_edit=False)], "t1")
    before = manager.get_commitments(DAY)[0].id

    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, can_edit=False)], "t2")

    assert manager.get_commitments(DAY)[0].id == before
    assert manager.set_commitment_dismissed(before, True).dismissed is True


def test_cipm15_an_ignored_meeting_that_becomes_editable_holds_again(manager):
    """D9 -- an ignore is for someone else's meeting; once editable it holds its time."""
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, can_edit=False)], "t1")
    manager.set_commitment_dismissed(manager.get_commitments(DAY)[0].id, True)

    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, can_edit=True)], "t2")

    assert manager.get_commitments(DAY)[0].dismissed is False
    assert manager._committed_for(DAY, BOUNDS) == frozenset({4})


def test_cipm15_a_read_holds_the_write_lock_before_it_reads_dismissals(manager, monkeypatch):
    """A dismissal saved by the screen mid-read must wait, not be overwritten."""
    manager.replace_commitments_for_dates([DAY], [
        _commitment(600, 630, can_edit=False),
        _commitment(700, 730, event_id="kept", can_edit=False),
    ], "t1")
    row_id = [c.id for c in manager.get_commitments(DAY) if c.event_id == "ev1"][0]
    blocked = []
    real = manager._row_to_commitment

    def dismiss_from_another_connection(row):
        other = sqlite3.connect(manager.db.db_path, timeout=0)
        try:
            other.execute("UPDATE calendar_commitments SET dismissed = 1 WHERE id = ?", (row_id,))
            other.commit()
        except sqlite3.OperationalError as error:
            blocked.append(str(error))
        finally:
            other.close()
        return real(row)

    monkeypatch.setattr(manager, "_row_to_commitment", dismiss_from_another_connection)
    manager.replace_commitments_for_dates(
        [DAY], [_commitment(600, 630, can_edit=False)], "t2", keep_event_ids=["kept"]
    )

    assert blocked == ["database is locked"]


@pytest.mark.parametrize("seen_as", ["moved", "declined"])
def test_cipd6_a_kept_row_the_read_settled_elsewhere_is_dropped(manager, seen_as):
    """D6 -- keep a skipped calendar's meeting only if this read learned nothing about it."""
    manager.replace_commitments_for_dates([DAY], [_commitment(600, 630, event_id="x")], "t1")
    with manager.transaction() as conn:
        conn.execute("UPDATE calendar_commitments SET calendar_id = 'team' WHERE event_id = 'x'")
    if seen_as == "moved":
        on_primary = _event("x", start="2026-11-14T10:00:00-08:00", end="2026-11-14T10:30:00-08:00")
    else:
        on_primary = _event("x", attendees=[{"self": True, "responseStatus": "declined"}])
    client = FakeCalendar({"primary": [on_primary]}, errors={"team": CalendarForbidden("403")})

    refresh_commitments(DAY, NEXT, client_factory=lambda: client, db_path=manager.db.db_path,
                        calendar_ids=["primary", "team"], tz=TZ)

    assert manager.get_commitments(DAY) == []
    assert [c.event_id for c in manager.get_commitments(NEXT)] == (["x"] if seen_as == "moved" else [])
