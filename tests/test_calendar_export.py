"""CE-M2 — a planned day exported to Google Calendar.

Purpose: hold the exporter to what it claims — the same titles the screen
         draws, the same day twice without duplicates, and exactly one kind of
         event it is allowed to delete.
Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md
Tests:   this file

**No test here reaches the network.** The client is injected and duck-typed,
and every test passes a `FakeCalendar` that records what it was asked to do.
That is the point of the seam: the one real client authenticates in its
constructor, so a module that built its own could not be tested at all.

The sweep tests come first in this file because they came first in the work.
Deleting is the only thing in here that can destroy something the user did not
plan, so its two tests — the orphan that must go, and the meeting that must
not — were written before the code that deletes anything (P10: the test effort
goes where the stakes are, not where the typing is easy).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.getmoredone.calendar_exporter import (
    BLOCK_DATE_PROPERTY,
    BLOCK_ID_PROPERTY,
    CREATE,
    UPDATE,
    CalendarEventMissing,
    ExportOutcome,
    build_export_plan,
    export_day,
)
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.time_block_layout import DayBounds

DAY = "2026-11-09"
BOUNDS = DayBounds()  # 08:00, lunch 12:00-13:00, ends 17:00


# --- the fake calendar ------------------------------------------------------

class FakeCalendar:
    """A Google Calendar that lives in a dict and remembers everything.

    `calls` is the assertion surface for idempotency: "exported twice and
    created nothing the second time" is a statement about the calls made, and
    a fake that only held final state could not tell a create from an update
    that happened to land on the same event.
    """

    def __init__(self, existing=None, fail_on=None, missing=()):
        self.events = dict(existing or {})
        self.calls = []
        self.fail_on = fail_on or {}
        self.missing = set(missing)
        self._next = 0

    # -- the client surface the exporter uses --
    def create_event(self, *, summary, start_datetime, duration_minutes,
                     description=None, calendar_id="primary",
                     private_properties=None, reminders=None):
        self.calls.append(("create", summary, calendar_id))
        self._raise_if_asked(summary)
        self._next += 1
        event_id = f"evt-{self._next}"
        self.events[event_id] = {
            "id": event_id,
            "summary": summary,
            "start": start_datetime,
            "minutes": duration_minutes,
            "description": description,
            "reminders": reminders,
            "extendedProperties": {"private": dict(private_properties or {})},
        }
        return dict(self.events[event_id])

    def update_event(self, *, event_id, summary=None, start_datetime=None,
                     duration_minutes=None, description=None,
                     calendar_id="primary"):
        self.calls.append(("update", event_id, calendar_id))
        if event_id in self.missing or event_id not in self.events:
            raise CalendarEventMissing(event_id)
        self._raise_if_asked(summary)
        self.events[event_id].update(
            summary=summary, start=start_datetime, minutes=duration_minutes,
            description=description,
        )
        return dict(self.events[event_id])

    def delete_event(self, event_id, calendar_id="primary"):
        self.calls.append(("delete", event_id, calendar_id))
        self._raise_if_asked(f"delete:{event_id}")
        self.events.pop(event_id, None)

    def list_day_events(self, block_date, calendar_id="primary"):
        self.calls.append(("list", block_date, calendar_id))
        self._raise_if_asked(f"list:{block_date}")
        return [dict(event) for event in self.events.values()]

    # -- helpers --
    def _raise_if_asked(self, key):
        error = self.fail_on.get(key)
        if error is not None:
            raise error

    def kinds(self, kind):
        return [call for call in self.calls if call[0] == kind]

    def marked(self, event_id):
        private = self.events[event_id]["extendedProperties"]["private"]
        return private.get(BLOCK_ID_PROPERTY)


def _marked_event(event_id, block_id, block_date=DAY, summary="from an earlier export"):
    return {
        "id": event_id,
        "summary": summary,
        "extendedProperties": {
            "private": {
                BLOCK_ID_PROPERTY: block_id,
                BLOCK_DATE_PROPERTY: block_date,
            }
        },
    }


def _unmarked_event(event_id, summary):
    """Somebody's real meeting: on the same day, carrying nothing of ours."""
    return {"id": event_id, "summary": summary, "extendedProperties": {"private": {}}}


# --- the database ----------------------------------------------------------

@pytest.fixture
def manager(tmp_path):
    """Every DatabaseManager in this suite gets an explicit tmp_path database.

    The default path resolves to the user's real application database, and
    __init__ runs migrations against it.
    """
    db = DatabaseManager(str(tmp_path / "export.db"))
    yield db
    db.close()


def _block(manager, slot, minutes=30, label=None, block_type=BlockType.ITEM,
           item_id=None, block_date=DAY):
    """A block on the grid, placed the way the screen places one."""
    block = TimeBlock(
        block_date=block_date,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        block_type=block_type,
        item_id=item_id,
    )
    return manager.add_block_at(block, slot, BOUNDS)


def _item(manager, title, **kwargs):
    """An action item for a block to point at. ``who`` is required by the model."""
    item = ActionItem(who="Me", title=title, **kwargs)
    return manager.create_action_item(item)


# ===========================================================================
# CE-M2.6 — the sweep. Written first.
# ===========================================================================

def test_cem261_an_event_for_a_deleted_block_is_removed(manager):
    """CE-M2.6 — the block is gone, so its event goes with it.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test
    """
    kept = _block(manager, 0, label="still planned", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(kept.id, "evt-kept")

    client = FakeCalendar(existing={
        "evt-kept": _marked_event("evt-kept", kept.id),
        "evt-orphan": _marked_event("evt-orphan", "a-block-id-that-is-gone"),
    })

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.deleted_orphans == 1
    assert client.kinds("delete") == [("delete", "evt-orphan", "primary")]
    assert "evt-orphan" not in client.events
    assert "evt-kept" in client.events, "the block that is still planned keeps its event"


def test_cem262_an_unmarked_event_is_never_deleted(manager):
    """CE-M2.6 — a real meeting is not ours to remove, however much it looks like ours.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    Adversarial (P7): the meeting is on the exported day, at the exported
    time, with the *exact* title of a block on that day. Everything an export
    might match on says "this is the event for that block" — except the one
    thing that actually decides it, which is the marker the export writes
    itself.
    """
    item_id = _item(manager, "Design review")
    block = _block(manager, 2, item_id=item_id)

    client = FakeCalendar(existing={
        "someone-elses": _unmarked_event("someone-elses", "Design review"),
    })

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert client.kinds("delete") == [], "an unmarked event must never be deleted"
    assert "someone-elses" in client.events
    assert outcome.deleted_orphans == 0
    assert outcome.created == 1, "and the block still gets its own event"
    assert manager.get_time_block(block.id).calendar_event_id == "evt-1"


def test_cem266_an_event_marked_for_another_day_is_never_deleted(manager):
    """CE-M2.6b — our marker, another day's date: not this run's to remove.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    Adversarial (P7): by every other rule in the sweep this event *is* an
    orphan — it carries our marker and names a block that is not on the day
    being exported. The only thing standing between it and a delete is the
    half of the marker that says which day it belongs to. A copy of an
    exported event made onto another date carries the private properties with
    it, and so does every instance of one turned into a recurring event.
    """
    _block(manager, 2, item_id=_item(manager, "Design review"))

    client = FakeCalendar(existing={
        "from-another-day": _marked_event(
            "from-another-day", "a-block-on-another-day", block_date="2026-11-10"
        ),
    })

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert client.kinds("delete") == [], "another day's event must never be deleted"
    assert "from-another-day" in client.events
    assert outcome.deleted_orphans == 0
    assert outcome.created == 1, "and the day's own block still gets its event"


def test_cem266a_an_event_with_our_marker_and_no_date_is_still_swept(manager):
    """CE-M2.6b — the date check is a guard, not a blanket pardon.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    An event carrying a block id of ours but no date at all is still the real
    orphan case: it names a block that is not on this day. Were the guard
    written as "the date must match" rather than "a date we can read must not
    disagree", this event would be kept forever and nothing would ever remove
    it.
    """
    event = _marked_event("orphan", "a-block-that-is-gone")
    del event["extendedProperties"]["private"][BLOCK_DATE_PROPERTY]

    client = FakeCalendar(existing={"orphan": event})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert client.kinds("delete") == [("delete", "orphan", "primary")]
    assert outcome.deleted_orphans == 1
    assert "orphan" not in client.events


def test_cem266b_an_event_whose_properties_are_not_a_dict_is_ignored(manager):
    """CE-M2.6b — a response shape Google never promised must not raise.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    `extendedProperties` is read off a response, and a response is data, not a
    contract. A list where a dict was expected used to reach `.get` and take
    the whole outcome — every create and update this run had already made —
    out with it.
    """
    client = FakeCalendar(existing={
        "odd": {
            "id": "odd",
            "summary": "shaped like nothing we send",
            "extendedProperties": ["not", "a", "dict"],
        },
    })

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert client.kinds("delete") == []
    assert outcome.failed == 0
    assert outcome.deleted_orphans == 0


def test_cem35_an_exported_block_inherits_the_user_s_own_reminders(manager):
    """CE-M3.5 — a day of blocks is not a day of meetings.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m35
    Tests: this test

    The literal is asserted rather than the constant: a test that compared the
    body against `INHERIT_REMINDERS` would still pass if that constant were
    changed to the ten-minute popup, which is the thing this exists to stop.
    """
    _block(manager, 2, item_id=_item(manager, "Design review"))

    client = FakeCalendar()
    export_day(DAY, client=client, db_manager=manager)

    assert client.events["evt-1"]["reminders"] == {"useDefault": True}


def test_cem263_a_failed_block_keeps_its_event(manager):
    """CE-M2.6 — a 500 on a block's update must not escalate into a delete.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    The block is still on the day; the export simply could not reach it this
    time. Deleting the event it already owns would turn a transient failure
    into lost information (P1).
    """
    item_id = _item(manager, "Quarterly numbers")
    block = _block(manager, 1, item_id=item_id)
    manager.set_block_calendar_event_id(block.id, "evt-existing")

    client = FakeCalendar(
        existing={"evt-existing": _marked_event("evt-existing", block.id)},
        fail_on={"Quarterly numbers": RuntimeError("500 Backend Error")},
    )

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.failed == 1
    assert client.kinds("delete") == []
    assert "evt-existing" in client.events
    assert manager.get_time_block(block.id).calendar_event_id == "evt-existing", (
        "a failed update must not clear the id of an event that still exists"
    )


def test_cem264_a_duplicate_event_for_a_live_block_is_removed(manager):
    """CE-M2.6 — two events carrying one block's marker: the stale one goes."""
    item_id = _item(manager, "Write the spec")
    block = _block(manager, 0, item_id=item_id)
    manager.set_block_calendar_event_id(block.id, "evt-current")

    client = FakeCalendar(existing={
        "evt-current": _marked_event("evt-current", block.id),
        "evt-stale": _marked_event("evt-stale", block.id),
    })

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert client.kinds("delete") == [("delete", "evt-stale", "primary")]
    assert outcome.deleted_orphans == 1
    assert manager.get_time_block(block.id).calendar_event_id == "evt-current", (
        "removing the duplicate must not clear the id of the event we kept"
    )


def test_cem266_a_block_the_export_skipped_keeps_its_event(manager):
    """CE-M2.6 — the sweep removes nothing for a block it did not touch.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    The block is still on the day, and was exported before; this run skips it
    because its length has gone to zero. Deleting the event it already owns
    would be the export acting on a block it declined to export.
    """
    block = _block(manager, 0, label="Swim", block_type=BlockType.BREAK)
    client = FakeCalendar()
    export_day(DAY, client=client, db_manager=manager)
    event_id = manager.get_time_block(block.id).calendar_event_id
    assert event_id

    manager.db.conn.execute(
        "UPDATE time_blocks SET planned_minutes = 0 WHERE id = ?", (block.id,)
    )
    manager.db.conn.commit()

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.skipped_no_minutes == 1
    assert outcome.deleted_orphans == 0
    assert client.kinds("delete") == []
    assert event_id in client.events
    assert manager.get_time_block(block.id).calendar_event_id == event_id


def test_cem265_a_sweep_that_cannot_list_is_reported_not_assumed_empty(manager):
    """CE-M2.6 — a failed list is a failure, not "nothing to remove".

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test
    """
    _block(manager, 0, label="tea", block_type=BlockType.BREAK)
    client = FakeCalendar(fail_on={f"list:{DAY}": RuntimeError("503 Service Unavailable")})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.created == 1, "the blocks still went out"
    assert outcome.failed == 1, "and the sweep that did not run says so"
    assert outcome.ok is False
    assert any("503" in message for message in outcome.errors)


# ===========================================================================
# CE-M2.1 — what the plan decides, with nothing sent
# ===========================================================================

def test_cem211_an_unplaced_block_is_skipped_and_counted(manager):
    """CE-M2.1 — a block with no box has no honest time, and says so.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m21
    Tests: this test
    """
    placed = _block(manager, 0, label="on the grid", block_type=BlockType.BUFFER)
    unplaced = TimeBlock(
        block_date=DAY, start_time="09:00", end_time="09:30",
        planned_minutes=30, label="outside the day",
    )
    manager.create_time_block(unplaced)

    plan = build_export_plan(manager.get_time_blocks(DAY), {}, DAY)

    assert plan.blocks_seen == 2
    assert plan.skipped_unplaced == 1
    assert [entry.block_id for entry in plan.entries] == [placed.id]


def test_cem212_every_placed_block_gets_one_entry(manager):
    """CE-M2.1 — items, buffers and breaks alike."""
    item_id = _item(manager, "Deep work")
    _block(manager, 0, item_id=item_id)
    _block(manager, 2, label=None, block_type=BlockType.BUFFER)
    _block(manager, 3, label="Walk", block_type=BlockType.BREAK)

    plan = build_export_plan(
        manager.get_time_blocks(DAY),
        {item_id: manager.get_action_item(item_id)},
        DAY,
    )

    assert plan.blocks_seen == 3
    assert plan.skipped == 0
    assert [entry.summary for entry in plan.entries] == ["Deep work", "Buffer", "Walk"]
    assert [entry.action for entry in plan.entries] == [CREATE, CREATE, CREATE]


def test_cem213_a_block_with_an_event_id_plans_an_update_not_a_create(manager):
    """CE-M2.1 — the recorded id is what makes a second export an update."""
    block = _block(manager, 0, label="Lunch walk", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-7")

    plan = build_export_plan(manager.get_time_blocks(DAY), {}, DAY)

    assert [(entry.action, entry.event_id) for entry in plan.entries] == [(UPDATE, "evt-7")]


def test_cem214_a_block_with_no_length_is_skipped_and_counted(manager):
    """CE-M2.1 — a zero-minute event is not a thing to put on a calendar."""
    manager.db.conn.execute(
        "UPDATE time_blocks SET planned_minutes = 0 WHERE id = ?",
        (_block(manager, 0, label="nothing").id,),
    )
    manager.db.conn.commit()

    plan = build_export_plan(manager.get_time_blocks(DAY), {}, DAY)

    assert plan.skipped_no_minutes == 1
    assert plan.entries == []


def test_cem215_an_unreadable_stored_clock_time_no_longer_stops_a_block(manager):
    """CE-M2.1 / CE-M2.3 — the box decides, so the stored column cannot break it.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m23
    Tests: this test

    This asserted the opposite until a cold review pass: the export read
    `block.start_time` and skipped the block as `skipped_bad_time`. Reason (b),
    the behaviour changed intentionally — the stored clock columns are a
    record, not the truth (`PlanScreen.on_settings_saved` says so), so a block
    with an unreadable one is still a block in a box, at the box's time. The
    counter it used to increment now guards the day string instead
    (`test_cem215a`).
    """
    block = _block(manager, 0, label="broken")
    manager.db.conn.execute(
        "UPDATE time_blocks SET start_time = 'tea time' WHERE id = ?", (block.id,)
    )
    manager.db.conn.commit()

    plan = build_export_plan(manager.get_time_blocks(DAY), {}, DAY)

    assert plan.skipped_bad_time == 0
    assert plan.skipped_unplaced == 0
    assert [entry.block_id for entry in plan.entries] == [block.id]
    assert plan.entries[0].start.strftime("%H:%M") == BOUNDS.day_start, (
        "slot 0 is the first box of the day, whatever the row's own column says"
    )


def test_cem215a_a_day_that_cannot_be_parsed_counts_every_block(manager):
    """CE-M2.1 — an unusable date is not an empty day.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m21
    Tests: this test

    The entries list coming back empty would read as "nothing to export" and
    say so to the user (P2 — surfaced, never silently dropped).
    """
    _block(manager, 0)
    _block(manager, 2)
    blocks = manager.get_time_blocks(DAY)

    plan = build_export_plan(blocks, {}, "not-a-day")

    assert plan.blocks_seen == 2
    assert plan.skipped_bad_time == 2
    assert plan.entries == []


def test_cem216_a_block_the_day_draws_outside_the_grid_is_not_exported(manager):
    """CE-M2.1 — "on the grid" is the grid the user sees, bounds and all.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m21
    Tests: this test

    Found by a cold review pass. The check was `slot_index is not None`, which
    is not what the screen means by on the grid: `build_day_grid` also puts a
    block outside the day when Day End has moved past its boxes, and when the
    lunch hour has been moved over it. Both were being exported — at their
    stale stored times — while the day drew them under *Outside the day*, which
    the user guide promises are skipped.
    """
    early = DayBounds(day_start="09:00", day_end="10:00", lunch_start="12:00")
    in_the_day = _block(manager, 0, label="first half hour")
    past_the_end = _block(manager, 6, label="was 12:00")
    blocks = manager.get_time_blocks(DAY)

    assert past_the_end.slot_index == 6, "the fixture has to place it to prove anything"

    plan = build_export_plan(blocks, {}, DAY, bounds=early)

    assert plan.blocks_seen == 2
    assert plan.skipped_unplaced == 1
    assert [entry.block_id for entry in plan.entries] == [in_the_day.id]


def test_cem216a_a_block_under_the_lunch_hour_is_not_exported(manager):
    """CE-M2.1 — the other way `build_day_grid` puts a block outside the day.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m21
    Tests: this test

    Reachable by moving lunch over work already planned, which is why
    `build_day_grid` has the branch: a lunch box draws "Lunch" and nothing
    else, so the block is not on screen at all.
    """
    block = _block(manager, 0, label="lunch moved onto it")
    moved_lunch = DayBounds(day_start=BOUNDS.day_start, lunch_start=BOUNDS.day_start)
    blocks = manager.get_time_blocks(DAY)

    plan = build_export_plan(blocks, {}, DAY, bounds=moved_lunch)

    assert plan.skipped_unplaced == 1, (
        f"block {block.id} is under the lunch hour and was still exported"
    )
    assert plan.entries == []


# ===========================================================================
# CE-M2.2 / CE-M2.3 — the title and the clock
# ===========================================================================

def test_cem221_every_branch_of_the_title_rule_names_a_block(manager):
    """CE-M2.2 — one rule, five branches, asserted against literals.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m22
    Tests: this test

    Five cases, because each is a different branch of ``block_title``: an item
    block, a buffer and a break with no label of their own, an item block
    whose item is gone but which kept its label, and an item block whose item
    is gone and which has no label — the one that would otherwise export an
    event with no title at all. That last branch was reachable in the app and
    asserted nowhere: ``delete_action_item`` leaves an item's time blocks
    behind, which is why the branch exists.

    A cold review pass found this test also comparing the entry titles to
    ``plan_blocks._block_title(...)``, a one-line delegation to the function
    the exporter itself calls — true for any implementation, broken ones
    included, and it dragged CustomTkinter into a file whose point is being
    headless. What that assertion was reaching for — that the screen draws
    what the export sends — is
    ``tests/test_plan_screen_calendar_export.py::test_cem221a_an_event_is_titled_what_the_day_draws_on_the_block``,
    which reads the text Tk drew.
    """
    item_id = _item(manager, "Call the bank")
    item = manager.get_action_item(item_id)

    blocks = [
        _block(manager, 0, item_id=item_id),
        _block(manager, 1, block_type=BlockType.BUFFER),
        _block(manager, 2, block_type=BlockType.BREAK),
        _block(manager, 3, label="was a task"),
        # Not saved, and deliberately not reachable through the database: the
        # ``item_id`` foreign key has no ON DELETE clause and the connection
        # runs with ``foreign_keys = ON``, so deleting an item that still has a
        # block raises rather than orphaning the block. The branch is for the
        # row that got orphaned some other way — an older database, or a
        # restore — and ``build_export_plan`` is pure, so the state can be
        # handed to it directly instead of being faked into SQLite.
        TimeBlock(
            block_date=DAY, start_time="11:00", end_time="11:30",
            planned_minutes=30, label=None, block_type=BlockType.ITEM,
            item_id="an-item-that-is-not-there", slot_index=4,
        ),
    ]

    plan = build_export_plan(blocks, {item_id: item}, DAY)

    assert [entry.summary for entry in plan.entries] == [
        "Call the bank", "Buffer", "Break", "was a task",
        "(item no longer exists)",
    ]


def test_cem231_a_0930_block_exports_at_0930_local(manager):
    """CE-M2.3 — the event starts when the day says it starts.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m23
    Tests: this test

    Box 3 under an 08:00 day start is 09:30. Asserted as a datetime on the
    exported date, not as a string, and with no timezone conversion applied:
    the zone is named to the API alongside the wall-clock time, so a day
    planned for 09:30 is 09:30 wherever the user is.
    """
    block = _block(manager, 3, minutes=45, label="Deep work", block_type=BlockType.BUFFER)

    plan = build_export_plan([block], {}, DAY)
    entry = plan.entries[0]

    assert entry.start == datetime(2026, 11, 9, 9, 30)
    assert entry.start.tzinfo is None, "a wall-clock time, named to the API with its zone"
    assert entry.minutes == 45


def test_cem232_the_items_next_step_travels_with_the_event(manager):
    """CE-M2.3 — the description carries the user's own next step, then ours."""
    item_id = _item(manager, "File the return", next_action="Download last year's PDF")
    block = _block(manager, 0, item_id=item_id)

    plan = build_export_plan([block], {item_id: manager.get_action_item(item_id)}, DAY)

    assert plan.entries[0].description.startswith("Download last year's PDF")
    assert "daVIPA" in plan.entries[0].description


# ===========================================================================
# CE-M2.4 / CE-M2.5 — sending it, twice
# ===========================================================================

def test_cem241_export_day_uses_the_client_it_was_given(manager):
    """CE-M2.4 — the seam exists, and the real manager is never constructed.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m24
    Tests: this test
    """
    import src.getmoredone.google_calendar as google_calendar

    def explode(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("the exporter must not build a real calendar client")

    original = google_calendar.GoogleCalendarManager.__init__
    google_calendar.GoogleCalendarManager.__init__ = explode
    try:
        _block(manager, 0, label="Coffee", block_type=BlockType.BREAK)
        client = FakeCalendar()
        outcome = export_day(DAY, client=client, db_manager=manager)
    finally:
        google_calendar.GoogleCalendarManager.__init__ = original

    assert outcome.created == 1
    assert client.kinds("create")


def test_cem242_the_calendar_id_is_passed_to_every_call(manager):
    """CE-M2.4 — a non-default calendar reaches the client, not just the setting.

    The existing event is recorded as already being *on* that calendar. It
    used to be recorded with no calendar at all, which now means "the default
    one" — a different setup, and one that exercises the move path in
    `test_cem255`, not this one.
    """
    block = _block(manager, 0, label="Gym", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-a", "work@example.com")
    client = FakeCalendar(existing={
        "evt-a": _marked_event("evt-a", block.id),
        "evt-orphan": _marked_event("evt-orphan", "gone"),
    })

    export_day(DAY, client=client, db_manager=manager, calendar_id="work@example.com")

    assert {call[-1] for call in client.calls} == {"work@example.com"}


def test_cem251_a_second_export_updates_and_creates_nothing(manager):
    """CE-M2.5 — the whole point of recording the event id.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests: this test
    """
    item_id = _item(manager, "Inbox zero")
    _block(manager, 0, item_id=item_id)
    _block(manager, 2, label="Tea", block_type=BlockType.BREAK)
    client = FakeCalendar()

    first = export_day(DAY, client=client, db_manager=manager)
    assert (first.created, first.updated) == (2, 0)

    second = export_day(DAY, client=client, db_manager=manager)

    assert (second.created, second.updated) == (0, 2)
    assert len(client.kinds("create")) == 2, "no second set of events"
    assert len(client.events) == 2
    assert client.kinds("delete") == []


def test_cem252_a_moved_block_updates_its_own_event(manager):
    """CE-M2.5 — the event follows the block, rather than a new one appearing."""
    block = _block(manager, 0, minutes=30, label="Reading", block_type=BlockType.BREAK)
    client = FakeCalendar()
    export_day(DAY, client=client, db_manager=manager)
    event_id = manager.get_time_block(block.id).calendar_event_id

    manager.place_block_at(block.id, 6, BOUNDS)
    manager.set_block_length(block.id, 60, BOUNDS)

    export_day(DAY, client=client, db_manager=manager)

    assert manager.get_time_block(block.id).calendar_event_id == event_id
    assert client.events[event_id]["start"] == datetime(2026, 11, 9, 11, 0)
    assert client.events[event_id]["minutes"] == 60
    assert len(client.events) == 1


def test_cem253_an_event_deleted_in_google_is_made_again(manager):
    """CE-M2.5 — a stale id recovers instead of reporting a failure.

    The user deleted the event in Google Calendar by hand. The block still
    holds its id, so the export tries an update and is told the event is gone;
    making it again is what the user asked for by exporting.
    """
    block = _block(manager, 0, label="Standup", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-deleted-by-hand")
    client = FakeCalendar(missing={"evt-deleted-by-hand"})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.recreated == 1
    assert outcome.failed == 0
    new_id = manager.get_time_block(block.id).calendar_event_id
    assert new_id and new_id != "evt-deleted-by-hand"
    assert client.events[new_id]["summary"] == "Standup"


# ===========================================================================
# CE-M2.7 / CE-M2.8 — failure, and nothing to do
# ===========================================================================

def test_cem271_a_failed_block_does_not_stop_the_rest(manager):
    """CE-M2.7 — one block's failure is one block's failure.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m27
    Tests: this test
    """
    first = _item(manager, "First")
    second = _item(manager, "Second")
    third = _item(manager, "Third")
    _block(manager, 0, item_id=first)
    _block(manager, 1, item_id=second)
    _block(manager, 2, item_id=third)
    client = FakeCalendar(fail_on={"Second": RuntimeError("409 Conflict")})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.created == 2
    assert outcome.failed == 1
    assert outcome.ok is False
    assert [event["summary"] for event in client.events.values()] == ["First", "Third"]
    assert any("Second" in message for message in outcome.errors)


def test_cem272_a_failed_create_leaves_the_block_unexported(manager):
    """CE-M2.7 — an id is written from the response, never from the attempt.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m27
    Tests: this test
    """
    item_id = _item(manager, "Will fail")
    block = _block(manager, 0, item_id=item_id)
    client = FakeCalendar(fail_on={"Will fail": RuntimeError("500 Backend Error")})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.failed == 1
    assert manager.get_time_block(block.id).calendar_event_id is None, (
        "a block recorded as exported after a failed call would never be "
        "retried, and would show as exported forever"
    )


def test_cem273_a_create_that_returns_no_id_is_a_failure(manager):
    """CE-M2.7 — a 200 with no id in it is not a success."""
    class Silent(FakeCalendar):
        def create_event(self, **kwargs):
            super().create_event(**kwargs)
            return {}

    item_id = _item(manager, "Quiet")
    block = _block(manager, 0, item_id=item_id)
    client = Silent()

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.created == 0
    assert outcome.failed == 1
    assert manager.get_time_block(block.id).calendar_event_id is None


def test_cem281_an_empty_day_reports_nothing_to_export(manager):
    """CE-M2.8 — and sends nothing at all.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m28
    Tests: this test
    """
    client = FakeCalendar()

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.blocks_seen == 0
    assert outcome.exported == 0
    assert client.kinds("create") == []
    assert "Nothing to export" in outcome.summary_line()


def test_cem283_a_cleared_day_still_removes_the_events_it_had(manager):
    """CE-M2.8 — a cancelled plan is the case the sweep exists for.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m28
    Tests: this test

    Found by a cold review pass: the screen refused to run the export at all
    on a day with no blocks, and this is the only code that deletes an event,
    so clearing a day left its five events on the user's calendar with no way
    to take them off. The exporter always handled it; nothing asked it to.
    """
    client = FakeCalendar(existing={
        "evt-1": _marked_event("evt-1", "a-block-that-was-deleted"),
        "evt-2": _marked_event("evt-2", "another-deleted-block"),
    })

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.blocks_seen == 0
    assert outcome.deleted_orphans == 2
    assert client.events == {}
    line = outcome.summary_line()
    assert "Nothing to export" not in line, (
        "a run that took two events off the calendar did something"
    )
    assert "No blocks planned" in line and "2 removed" in line


def test_cem283a_a_day_with_nothing_at_either_end_says_nothing_to_export(manager):
    """CE-M2.8 — and the honest empty case is still the honest empty case."""
    client = FakeCalendar()

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.deleted_orphans == 0
    assert "Nothing to export" in outcome.summary_line()


def test_cem282_a_day_exports_only_its_own_blocks(manager):
    """CE-M2.8 — the date is a filter, not a label on the status line."""
    _block(manager, 0, label="today's", block_type=BlockType.BREAK, block_date=DAY)
    _block(manager, 0, label="tomorrow's", block_type=BlockType.BREAK,
           block_date="2026-11-10")
    client = FakeCalendar()

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.blocks_seen == 1
    assert [event["summary"] for event in client.events.values()] == ["today's"]


def test_cem422_the_summary_line_names_every_skip():
    """CE-M4.2 — the status line the screen shows is honest about all of it.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test

    Built from an outcome directly: this is a statement about the sentence,
    and routing it through an export would only prove the sentence twice.
    """
    line = ExportOutcome(
        block_date=DAY, blocks_seen=7, created=2, updated=1, recreated=1,
        deleted_orphans=1, skipped_unplaced=1, skipped_no_minutes=1,
        skipped_bad_time=1, failed=0,
    ).summary_line()

    assert "4 of 7" in line
    assert "2 new" in line and "1 updated" in line and "1 re-created" in line
    assert "1 removed" in line
    assert "not on the grid" in line and "no length" in line and "unreadable time" in line


def test_cem422a_a_failure_is_named_in_the_summary_line():
    """CE-M4.2 — and a failed block is never silent."""
    line = ExportOutcome(block_date=DAY, blocks_seen=3, created=2, failed=1).summary_line()

    assert "1 FAILED" in line


# ===========================================================================
# CE-M2.6 — a block deleted while the export was running
# ===========================================================================

def test_cem264_a_block_deleted_mid_export_takes_its_new_event_with_it(manager):
    """CE-M2.6 — nothing points at the event, so the event goes.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    Found by a cold review pass. The export is a background thread and the
    Plan screen stays clickable, so a block can be deleted between the read
    and the write-back. The UPDATE then matches no rows -- which SQLite does
    not call an error -- and the old code counted a create, leaving an event
    on the calendar that nothing in the database names.

    The deletion is made to happen *inside* `create_event`, which is where it
    happens in life: while the call is in flight. The event is taken back by
    the sweep rather than on the spot, so there is one deleting code path and
    one count of it.
    """
    block = _block(manager, 0, label="Reading")

    class DeletesTheBlock(FakeCalendar):
        def create_event(self, **kwargs):
            manager.delete_time_block(block.id)
            return super().create_event(**kwargs)

    client = DeletesTheBlock()

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.created == 0, "a block the user deleted was counted as exported"
    assert outcome.vanished == 1
    assert outcome.deleted_orphans == 1, "the sweep is what takes the event back"
    assert client.kinds("create") and client.kinds("delete"), client.calls
    assert client.events == {}, (
        f"an event nothing points at was left on the calendar: {client.events}"
    )
    assert "deleted while exporting" in outcome.summary_line()


def test_cem264a_a_block_deleted_after_its_update_has_its_event_swept(manager):
    """CE-M2.6 — the sweep reads the day as it is now, not as it was.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    The update path writes nothing to the database, so there is no rowcount to
    notice the deletion by; the sweep is what has to catch it. It used to be
    given the ids read before the first API call, which still contained the
    deleted block -- so its event was protected as "a block still on this day
    whose event we confirmed", and stayed on the calendar.
    """
    block = _block(manager, 0, label="Reading")
    manager.set_block_calendar_event_id(block.id, "evt-1")

    class DeletesTheBlock(FakeCalendar):
        def update_event(self, **kwargs):
            result = super().update_event(**kwargs)
            manager.delete_time_block(block.id)
            return result

    client = DeletesTheBlock(existing={"evt-1": _marked_event("evt-1", block.id)})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.updated == 1, "the update itself succeeded before the deletion"
    assert outcome.deleted_orphans == 1
    assert "evt-1" not in client.events, (
        "the event of a block deleted mid-export was left on the calendar"
    )


def test_cem264b_a_failure_to_take_the_event_back_is_reported(manager):
    """CE-M2.6 — and not swallowed, because the event is now unreachable.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    P1/P2: the delete can fail transiently, and the user has to be told --
    the event is on their calendar with a marker naming a block that is gone,
    which only the next export's sweep will clear. Reported *once*: an earlier
    version of this fix deleted the event on the spot as well, so one stuck
    event was counted as two failures.
    """
    block = _block(manager, 0, label="Reading")

    class DeletesTheBlock(FakeCalendar):
        def create_event(self, **kwargs):
            manager.delete_time_block(block.id)
            return super().create_event(**kwargs)

    client = DeletesTheBlock(fail_on={"delete:evt-1": RuntimeError("503")})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.vanished == 1
    assert outcome.failed == 1
    assert outcome.ok is False
    assert any("removing evt-1" in message for message in outcome.errors), outcome.errors


def test_cem13a_recording_an_id_for_a_block_that_is_gone_says_so(manager):
    """CE-M1.3 — the setter reports whether it wrote anything.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m13
    Tests: this test

    An UPDATE matching no rows is not an error to SQLite, so the exporter had
    no way to tell a recorded id from a block that had been deleted under it.
    """
    block = _block(manager, 0)

    assert manager.set_block_calendar_event_id(block.id, "evt-1") is True
    assert manager.set_block_calendar_event_id("no-such-block", "evt-2") is False


# ===========================================================================
# CE-M2.5 — the calendar the setting points at changed
# ===========================================================================

def test_cem255_changing_the_export_calendar_moves_the_event(manager):
    """CE-M2.5 — off the old calendar, onto the configured one.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests: this test

    Found by a cold review pass. An event id means nothing except against the
    calendar it was created on, and the export calendar is a setting the user
    can change. The id alone was recorded, so after a change the export asked
    the *new* calendar to update an id that had never existed there — and the
    old event was unreachable for good: the sweep only lists the configured
    calendar, so nothing would ever look at the old one again.
    """
    block = _block(manager, 0, label="Gym", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-old", "home@example.com")
    client = FakeCalendar(existing={"evt-old": _marked_event("evt-old", block.id)})

    outcome = export_day(
        DAY, client=client, db_manager=manager, calendar_id="work@example.com"
    )

    assert outcome.moved == 1
    assert outcome.updated == 0 and outcome.created == 0
    assert ("delete", "evt-old", "home@example.com") in client.calls, client.calls
    assert ("create", "Gym", "work@example.com") in client.calls, client.calls

    moved = manager.get_time_blocks(DAY)[0]

    assert moved.calendar_event_id != "evt-old"
    assert moved.calendar_event_calendar_id == "work@example.com", (
        "the block still names the calendar it is no longer on"
    )
    assert "moved to this calendar" in outcome.summary_line()


def test_cem255a_the_move_is_not_made_when_the_calendar_is_the_same(manager):
    """CE-M2.5 — the ordinary re-export still updates in place.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests: this test

    The paired test: a move that fired on every export would delete and
    re-create the whole day each time, which is the duplicate-churn the event
    id exists to prevent.
    """
    block = _block(manager, 0, label="Gym", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-a", "work@example.com")
    client = FakeCalendar(existing={"evt-a": _marked_event("evt-a", block.id)})

    outcome = export_day(
        DAY, client=client, db_manager=manager, calendar_id="work@example.com"
    )

    assert outcome.updated == 1
    assert outcome.moved == 0
    assert client.kinds("create") == []
    assert client.kinds("delete") == []


def test_cem255b_a_row_from_before_the_column_is_read_as_the_default(manager):
    """CE-M2.5 — NULL is the default calendar, not an unknown one.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests: this test

    Dirty state (P8): rows written by the first version of the export hold an
    id and no calendar. That export could only write to `primary`, so reading
    NULL as `primary` is a fact, not a guess — and reading it as "some other
    calendar" would delete and re-create every such event on the next export.
    """
    block = _block(manager, 0, label="Gym", block_type=BlockType.BREAK)
    manager.db.conn.execute(
        """
        UPDATE time_blocks
        SET calendar_event_id = 'evt-a', calendar_event_calendar_id = NULL
        WHERE id = ?
        """,
        (block.id,),
    )
    manager.db.conn.commit()
    client = FakeCalendar(existing={"evt-a": _marked_event("evt-a", block.id)})

    outcome = export_day(DAY, client=client, db_manager=manager)

    assert outcome.updated == 1, "a row with no recorded calendar was moved"
    assert outcome.moved == 0
    assert client.kinds("create") == []


def test_cem255c_an_event_already_gone_from_the_old_calendar_still_moves(manager):
    """CE-M2.5 — a 404 on the old calendar is the end state we wanted.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests: this test

    P1: the event having been deleted in Google by hand is not a failure of
    the move, and must not stop the block reaching the configured calendar.
    """
    block = _block(manager, 0, label="Gym", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-old", "home@example.com")
    client = FakeCalendar(
        existing={"evt-old": _marked_event("evt-old", block.id)},
        fail_on={"delete:evt-old": CalendarEventMissing("evt-old")},
    )

    outcome = export_day(
        DAY, client=client, db_manager=manager, calendar_id="work@example.com"
    )

    assert outcome.moved == 1
    assert outcome.failed == 0
    assert ("create", "Gym", "work@example.com") in client.calls


def test_cem255d_a_move_that_cannot_delete_keeps_the_old_id(manager):
    """CE-M2.5 — a transient failure leaves the block exactly as it was.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests: this test

    P1: a 503 on the old calendar must not lose the id, or the old event
    becomes the unreachable orphan this whole fix exists to prevent. The block
    keeps its id and its calendar, so the next export tries the move again.
    """
    block = _block(manager, 0, label="Gym", block_type=BlockType.BREAK)
    manager.set_block_calendar_event_id(block.id, "evt-old", "home@example.com")
    client = FakeCalendar(
        existing={"evt-old": _marked_event("evt-old", block.id)},
        fail_on={"delete:evt-old": RuntimeError("503 Service Unavailable")},
    )

    outcome = export_day(
        DAY, client=client, db_manager=manager, calendar_id="work@example.com"
    )

    assert outcome.moved == 0
    assert outcome.failed == 1
    assert outcome.ok is False
    assert client.kinds("create") == [], "a second event was made for the same block"

    unchanged = manager.get_time_blocks(DAY)[0]

    assert unchanged.calendar_event_id == "evt-old"
    assert unchanged.calendar_event_calendar_id == "home@example.com"
