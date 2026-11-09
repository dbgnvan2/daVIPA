"""TB-M2/TG-M6 — the writes a planned day needs.

Purpose: hold update_time_block, the slot-aware writes, and the
         exact-start-date item query to their stated behaviour.
Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m6
Tests:   this file

**The reorder and repack tests that used to be most of this file are gone**,
with the writes they covered. A planned day was an order, so every edit had to
re-derive and re-store the whole day's clock times; a block now stores which
half-hour box it sits in, relative to Day Start, and the times follow from the
box on read. There is nothing to re-pack and no ceiling to run past — the last
box ends at Day End. TG-M6.4 at the foot of this file is the test that says so:
a Day Start change writes no rows at all.

There is now exactly **one** renumber, and it is not that one: PD-M5's
drop-extend moves Day Start to make room for an item dropped above the day, and
renumbers so the work already on the day keeps the clock time it had. Changing
Day Start in Day Settings still writes nothing and still re-times the day,
which is the behaviour TG-M6.4 pins; lengthening the day at one end is a
different gesture, and sliding every planned task half an hour earlier is not
what it asked for.
"""

import pytest

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.time_block_layout import (
    MAX_BLOCKS_PER_SLOT,
    DayBounds,
    SlotRefusal,
    SlotRefusedError,
    build_day_grid,
    parse_hhmm,
)

DAY = "2026-11-05"           # a Thursday
NEXT_DAY = "2026-11-06"
BOUNDS = DayBounds()         # 08:00, lunch 12:00-13:00, ends 17:00


@pytest.fixture
def manager(tmp_path):
    """Every DatabaseManager in this suite gets an explicit tmp_path database.

    The default path resolves to the user's real application database, and
    __init__ runs migrations against it.
    """
    db = DatabaseManager(str(tmp_path / "blocks.db"))
    yield db
    db.close()


def _add(manager, minutes, label, block_date=DAY, block_type=BlockType.ITEM, item_id=None):
    """Append a block to a day the way the screen does, and return its id."""
    block = TimeBlock(
        block_date=block_date,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        block_type=block_type,
        item_id=item_id,
    )
    return manager.create_time_block(block)


def _day(manager, block_date=DAY):
    """(label, slot_index, position, start, end) for each block, in order.

    The box is in the tuple because it is now the truth: a snapshot that saw
    only the label, the position and the times would be satisfied by a block
    sitting in the wrong box with the right clock string.
    """
    return [
        (b.label, b.slot_index, b.position, b.start_time, b.end_time)
        for b in manager.get_time_blocks(block_date)
    ]


# --- creating ---------------------------------------------------------------

def test_a_new_block_with_no_box_is_ordered_but_not_placed(manager):
    """``create_time_block`` is the raw insert, so it places nothing.

    Position 0 still means "append", which gives blocks with no box a stable
    order among themselves. The box stays NULL: "never placed" and "the first
    box of the day" are different facts, and a create that quietly chose 08:00
    would plan the user's work for them.
    """
    _add(manager, 30, "first")
    _add(manager, 30, "second")
    _add(manager, 30, "third")

    assert [
        (label, slot_index, position)
        for label, slot_index, position, _, _ in _day(manager)
    ] == [("first", None, 1), ("second", None, 2), ("third", None, 3)]


def test_appending_counts_only_the_day_it_is_appending_to(manager):
    """Two days planned side by side must not share a position counter."""
    _add(manager, 30, "a", block_date=DAY)
    _add(manager, 30, "b", block_date=DAY)
    _add(manager, 30, "other-day", block_date=NEXT_DAY)

    assert [position for _, _, position, _, _ in _day(manager, NEXT_DAY)] == [1]


def test_a_caller_with_an_explicit_position_keeps_it(manager):
    """``_settle_block_on_slot`` works out a position before the insert.

    So the insert must not overwrite one it was given, or every block placed
    on a box would be renumbered against the whole day the moment it was
    written -- and two blocks sharing a box would stop being ordered within it.
    """
    block = TimeBlock(
        block_date=DAY, start_time="", end_time="", planned_minutes=30,
        label="placed", position=7,
    )
    manager.create_time_block(block)

    assert [position for _, _, position, _, _ in _day(manager)] == [7]


# --- TB-M2.1 : the write that was missing -----------------------------------

def test_tbm21_update_persists_duration(manager):
    """TB-M2.1 — a changed duration survives a re-read.

    This is the whole of requirement 4's data path. Deleting the
    planned_minutes assignment from update_time_block has to fail here.
    """
    block_id = _add(manager, 30, "resize me")

    (block,) = manager.get_time_blocks(DAY)
    block.planned_minutes = 90
    manager.update_time_block(block)

    (reread,) = manager.get_time_blocks(DAY)
    assert reread.planned_minutes == 90
    assert reread.id == block_id


def test_update_persists_label_type_and_position(manager):
    """Each column the update claims to write, written.

    One assertion per column rather than one for the row: a SET list that
    silently dropped a column would otherwise be caught only by whichever
    column some other test happened to exercise.
    """
    _add(manager, 30, "before")

    (block,) = manager.get_time_blocks(DAY)
    block.label = "after"
    block.block_type = BlockType.BUFFER
    block.position = 5
    block.start_time = "14:00"
    block.end_time = "14:30"
    block.item_id = None
    manager.update_time_block(block)

    (reread,) = manager.get_time_blocks(DAY)
    assert reread.label == "after"
    assert reread.block_type == BlockType.BUFFER
    assert reread.position == 5
    assert reread.start_time == "14:00"
    assert reread.end_time == "14:30"


def test_update_stamps_updated_at(manager):
    _add(manager, 30, "block")
    (block,) = manager.get_time_blocks(DAY)
    before = block.updated_at

    block.planned_minutes = 45
    manager.update_time_block(block)

    (reread,) = manager.get_time_blocks(DAY)
    assert reread.updated_at >= before


def test_an_edit_cannot_silently_move_a_block_to_another_day(manager):
    """block_date is deliberately not in the UPDATE.

    Moving a block to another day is a different operation from editing one.
    Letting an edit relocate it is how a day loses work nobody deleted.
    """
    _add(manager, 30, "stays put")

    (block,) = manager.get_time_blocks(DAY)
    block.block_date = NEXT_DAY
    block.planned_minutes = 45
    manager.update_time_block(block)

    assert len(manager.get_time_blocks(DAY)) == 1
    assert manager.get_time_blocks(NEXT_DAY) == []


# --- TB-M2.4 : the item list ------------------------------------------------

def _item(manager, title, start_date, **kwargs):
    item = ActionItem(who="me", title=title, start_date=start_date, **kwargs)
    manager.create_action_item(item)
    return item


def test_tbm24_start_date_filter_is_exact(manager):
    """TB-M2.4 — exactly this date, not "on or before".

    The user's decision. The consequence is that an item whose start date is
    wrong does not appear on the day being planned, which is why the user guide
    tells them to get start dates right *before* time blocking.
    """
    _item(manager, "on the day", DAY)
    _item(manager, "day before", "2026-11-04")
    _item(manager, "day after", NEXT_DAY)
    _item(manager, "no start date", None)

    assert [i.title for i in manager.get_items_for_start_date(DAY)] == ["on the day"]


def test_item_list_excludes_completed_and_cancelled_work(manager):
    _item(manager, "open", DAY)
    _item(manager, "completed", DAY, status="completed")
    _item(manager, "canceled", DAY, status="canceled")

    assert [i.title for i in manager.get_items_for_start_date(DAY)] == ["open"]


def test_item_list_can_be_asked_for_any_status(manager):
    """The status filter is a parameter, not a hardcoded 'open'."""
    _item(manager, "open", DAY)
    _item(manager, "completed", DAY, status="completed")

    titles = [i.title for i in manager.get_items_for_start_date(DAY, status_filter=None)]
    assert sorted(titles) == ["completed", "open"]


def test_item_list_is_ordered_by_priority_then_title(manager):
    """Highest priority first, so the day is planned from the top down."""
    _item(manager, "low", DAY, importance=1, urgency=1, size=2, value=2)
    _item(manager, "critical", DAY, importance=20, urgency=20, size=16, value=16)
    _item(manager, "medium", DAY, importance=5, urgency=5, size=4, value=4)

    assert [i.title for i in manager.get_items_for_start_date(DAY)] == [
        "critical", "medium", "low",
    ]


def test_item_list_excludes_week_rows(manager):
    """Week rows are containers for other items' scheduling, not work to sit down and do."""
    _item(manager, "real work", DAY)
    manager.db.conn.execute(
        "UPDATE action_items SET item_type = 'week' WHERE title = 'real work'"
    )
    manager.db.conn.commit()

    assert manager.get_items_for_start_date(DAY) == []


def test_blocked_item_ids_names_the_items_already_on_the_day(manager):
    """The list marks these rather than hiding them: an item can need two blocks."""
    item = _item(manager, "blocked", DAY)
    _item(manager, "not blocked", DAY)
    _add(manager, 30, "its block", item_id=item.id)
    _add(manager, 30, "a buffer")

    assert manager.get_blocked_item_ids(DAY) == {item.id}


def test_blocked_item_ids_is_scoped_to_one_day(manager):
    item = _item(manager, "blocked tomorrow", DAY)
    _add(manager, 30, "tomorrow's block", block_date=NEXT_DAY, item_id=item.id)

    assert manager.get_blocked_item_ids(DAY) == set()
    assert manager.get_blocked_item_ids(NEXT_DAY) == {item.id}


# --- TG-M6: the grid writes --------------------------------------------------


def _at(manager, minutes, label, slot_index, block_date=DAY, item_id=None):
    """Put a block in a box the way the screen does, and return it."""
    block = TimeBlock(
        block_date=block_date,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        item_id=item_id,
    )
    return manager.add_block_at(block, slot_index, BOUNDS)


def test_tgm61_two_blocks_share_a_slot(manager):
    """TG-M6.1 — the user's decision, round-tripped through the database.

    Both in box 4, ordered by position, and both reading back at 10:00. The
    ordering assertion is the load-bearing half: two rows in a box with no
    settled order would draw in a different sequence between loads.
    """
    _at(manager, 30, "first", 4)
    _at(manager, 30, "second", 4)

    blocks = manager.get_time_blocks(DAY)

    assert [(b.label, b.slot_index, b.position) for b in blocks] == [
        ("first", 4, 1),
        ("second", 4, 2),
    ]
    assert {b.start_time for b in blocks} == {"10:00"}


def test_position_restarts_in_each_box(manager):
    """``position`` counts within a box, not across the day.

    Day-wide numbering draws the same day, so this is the one assertion that
    can tell the two apart: the stored number is what
    ``idx_blocks_date_slot(block_date, slot_index, position)`` is built on, and
    what a later reader of the column will take it to mean.
    """
    _at(manager, 30, "box 2 first", 2)
    _at(manager, 30, "box 2 second", 2)
    _at(manager, 30, "box 6 first", 6)
    _at(manager, 30, "box 6 second", 6)

    assert [
        (label, slot_index, position)
        for label, slot_index, position, _, _ in _day(manager)
    ] == [
        ("box 2 first", 2, 1),
        ("box 2 second", 2, 2),
        ("box 6 first", 6, 1),
        ("box 6 second", 6, 2),
    ]


def test_a_block_goes_where_it_was_dropped_not_at_the_end_of_the_day(manager):
    """The whole point of the grid, asserted directly.

    Under the old model every new block was appended; here box 9 means 13:00
    even though the day is otherwise empty and 08:00 is free.
    """
    _at(manager, 30, "afternoon", 10)

    block = manager.get_time_blocks(DAY)[0]

    assert block.slot_index == 10
    assert block.start_time == "13:00"


def test_tgm63_every_row_says_start_plus_duration(manager):
    """TG-M6.3 — the invariant, including the rounded-up case.

    A 45-minute block occupies two boxes and ends at 09:45, not 10:00.
    Writing the end of its second box would be the row claiming fifteen
    minutes the item does not own.
    """
    _at(manager, 45, "forty five", 2)
    _at(manager, 30, "thirty", 6)

    for block in manager.get_time_blocks(DAY):
        start = parse_hhmm(block.start_time)
        end = parse_hhmm(block.end_time)
        assert end - start == block.planned_minutes, block.label

    assert manager.get_time_blocks(DAY)[0].end_time == "09:45"


def test_a_move_rewrites_the_times_with_the_slot(manager):
    """TG-M11 — the times follow the box, in the same write.

    A move that set the box and left the stored time behind would leave a row
    whose start is from where it used to be. Nothing on screen reads that
    string, so it would stay wrong until somebody opened the database.
    """
    block = _at(manager, 30, "mover", 2)

    manager.place_block_at(block.id, 8 + 2, BOUNDS)

    moved = manager.get_time_blocks(DAY)[0]
    assert (moved.slot_index, moved.start_time, moved.end_time) == (10, "13:00", "13:30")


def test_tgm62_a_failed_move_writes_nothing(manager):
    """TG-M6.2 — a refused move leaves the day exactly as it was.

    The fit is checked before the transaction opens, so there is nothing to
    roll back -- which is the assertion: the block keeps its box *and* its
    times, not just one of the two.
    """
    block = _at(manager, 30, "mover", 2)
    before = _day(manager)

    with pytest.raises(SlotRefusedError) as refusal:
        manager.place_block_at(block.id, 8, BOUNDS)   # 12:00 is lunch

    assert refusal.value.reason == SlotRefusal.CROSSES_LUNCH
    assert _day(manager) == before


def test_a_block_can_be_nudged_inside_a_box_that_is_already_full(manager):
    """It must not be refused by its own presence.

    Without ``ignoring`` the block being moved counts against the room in the
    box it is already in, so a full box becomes a box nothing can leave.
    """
    mover = _at(manager, 30, "mover", 4)
    for n in range(MAX_BLOCKS_PER_SLOT - 1):
        _at(manager, 30, f"other {n}", 4)

    manager.place_block_at(mover.id, 4, BOUNDS)

    assert manager.get_time_block(mover.id).slot_index == 4


def test_tgm112_a_resize_that_does_not_fit_is_refused(manager):
    """TG-M11.2 — the block does not move to somewhere the new length fits.

    11:30 holds a 30 happily; the same box cannot hold a 60, because the next
    box is lunch. Sliding the block to 13:00 to make the number work would
    answer a question the user did not ask.
    """
    block = _at(manager, 30, "resize me", 7)
    before = _day(manager)

    with pytest.raises(SlotRefusedError) as refusal:
        manager.set_block_length(block.id, 60, BOUNDS)

    assert refusal.value.reason == SlotRefusal.CROSSES_LUNCH
    assert _day(manager) == before


def test_a_resize_that_fits_rewrites_the_end_time(manager):
    """Paired with the refusal above so neither passes for the wrong reason."""
    block = _at(manager, 30, "resize me", 2)

    manager.set_block_length(block.id, 45, BOUNDS)

    resized = manager.get_time_block(block.id)
    assert (resized.planned_minutes, resized.start_time, resized.end_time) == (
        45, "09:00", "09:45",
    )


def test_tgm64_a_day_start_change_writes_no_rows(manager):
    """TG-M6.4 — the reason the box is relative to Day Start.

    The same stored row reads as 10:00 under an 08:00 day and 11:00 under a
    09:00 one, with **no write in between**. This is what retires the
    repack-every-day machinery: there is nothing to repack.
    """
    block = _at(manager, 30, "steady", 4)
    stored_before = manager.db.conn.execute(
        "SELECT slot_index, start_time, updated_at FROM time_blocks WHERE id = ?",
        (block.id,),
    ).fetchone()

    later = DayBounds(day_start="09:00")
    grid = build_day_grid(manager.get_time_blocks(DAY), later)

    assert grid.slots[4].starting[0].id == block.id
    assert grid.slots[4].slot.start_time == "11:00"
    stored_after = manager.db.conn.execute(
        "SELECT slot_index, start_time, updated_at FROM time_blocks WHERE id = ?",
        (block.id,),
    ).fetchone()
    assert tuple(stored_after) == tuple(stored_before), "no row should have been written"


def test_a_block_added_past_the_end_of_the_grid_is_refused(manager):
    """The grid is bounded by Day End, so there is no "past day end" state."""
    with pytest.raises(SlotRefusedError) as refusal:
        _at(manager, 30, "too late", 18)

    assert refusal.value.reason == SlotRefusal.OUTSIDE_GRID
    assert manager.get_time_blocks(DAY) == []


# --- found by the pre-push sweep of the grid rebuild ------------------------


def test_a_resize_keeps_a_task_where_it_is_in_its_box(manager):
    """``position`` is a place in a box, and a length change is not a move.

    ``_settle_block_on_slot`` reassigned ``position`` to one past the highest
    other in the box on every call, so resizing the first of two tasks sharing
    a box moved it below the second -- a reordering nobody asked for, from a
    function whose docstring says it keeps the block where it is.
    """
    first = manager.add_block_at(
        TimeBlock(
            block_date=DAY, start_time="", end_time="", planned_minutes=30, label="first"
        ),
        3,
        DayBounds(),
    )
    manager.add_block_at(
        TimeBlock(
            block_date=DAY, start_time="", end_time="", planned_minutes=30, label="second"
        ),
        3,
        DayBounds(),
    )
    before = [(label, position) for label, _slot, position, _s, _e in _day(manager)]
    assert [label for label, _p in before] == ["first", "second"]

    manager.set_block_length(first.id, 60, DayBounds())

    after = [(label, position) for label, _slot, position, _s, _e in _day(manager)]
    assert after == before, f"the resize reordered the box: {before} -> {after}"


def test_a_drop_onto_its_own_box_moves_a_task_to_the_end_of_it(manager):
    """The guard that stopped a resize reordering must not stop a drop.

    ``place_block_at`` documents a block being nudged inside a box it is
    already in -- the only gesture a box has for ordering what is in it. The
    fix for the resize went into the shared helper, which turned that drop
    into a no-op while the screen still reported "Moved to ...".
    """
    first = _at(manager, 30, "first", 3)
    _at(manager, 30, "second", 3)
    assert [label for label, _s, _p, _a, _b in _day(manager)] == ["first", "second"]

    manager.place_block_at(first.id, 3, BOUNDS)

    assert [label for label, _s, _p, _a, _b in _day(manager)] == ["second", "first"], (
        "a drop onto its own box did nothing, and the screen said it moved"
    )


# ================= PD-M5.5 — the day grows, the work stays put ==========


def _rows(manager):
    return {
        row["label"]: (row["slot_index"], row["start_time"], row["end_time"])
        for row in manager.db.conn.execute(
            "SELECT label, slot_index, start_time, end_time FROM time_blocks"
        ).fetchall()
    }


def test_pdm55_blocks_keep_their_times_when_the_day_grows(manager):
    """PD-M5.5 — renumbering is what keeps a stored clock time true.

    A slot index counts boxes from Day Start. Move Day Start back one box and
    leave the indexes alone, and every planned task is drawn half an hour
    earlier than the ``start_time`` in its own row says: two answers on screen
    at once, neither marked wrong. The renumber is what makes the box and the
    time agree again.
    """
    _at(manager, 30, "08:00 meeting", 0)
    _at(manager, 60, "09:00 workshop", 2)
    before = _rows(manager)

    moved = manager.shift_all_slots(1)

    assert moved == 2, f"both blocks should have been renumbered, not {moved}"
    grid = build_day_grid(
        manager.get_time_blocks(DAY), DayBounds(day_start="07:30")
    )
    placed = {
        entry.starting[0].label: entry.slot.start_time
        for entry in grid.slots
        if entry.starting
    }
    assert placed == {"08:00 meeting": "08:00", "09:00 workshop": "09:00"}, placed

    after = _rows(manager)
    for label, (slot, start, end) in before.items():
        assert after[label] == (slot + 1, start, end), (
            f"{label} was {(slot, start, end)} and is now {after[label]}: the "
            "index had to move and the times had not"
        )


def test_pdm55_a_shift_of_zero_writes_nothing(manager):
    """Day End moving does not renumber, so the no-op path must really be one."""
    _at(manager, 30, "steady", 4)
    before = manager.db.conn.execute(
        "SELECT slot_index, updated_at FROM time_blocks"
    ).fetchone()

    assert manager.shift_all_slots(0) == 0

    after = manager.db.conn.execute(
        "SELECT slot_index, updated_at FROM time_blocks"
    ).fetchone()
    assert tuple(after) == tuple(before), "a shift of zero touched a row"


def test_pdm55_a_block_outside_the_grid_is_not_given_a_box(manager):
    """A NULL slot index stays NULL: handing it one here is TG-M5's adoption."""
    manager.create_time_block(
        TimeBlock(
            block_date=DAY,
            start_time="10:00",
            end_time="10:30",
            planned_minutes=30,
            label="from an older version",
        )
    )

    assert manager.shift_all_slots(2) == 0

    assert _rows(manager)["from an older version"] == (None, "10:00", "10:30"), (
        f"a block that was outside the grid was moved onto it: {_rows(manager)}"
    )


def test_pdm55_every_date_is_renumbered_not_only_the_one_on_screen(manager):
    """PD-M5.5 — Day Start is one setting, so a renumber of one date is a bug.

    This test used to assert the opposite, on the premise that "each date's
    boxes count from its own Day Start, and days are independent". There is no
    per-date Day Start: ``plan_day_start`` is a single ``AppSettings`` field and
    ``DayBounds.from_settings`` reads it for whatever date is on screen. So a
    renumber scoped to one date left every other date's blocks drawn earlier on
    the clock than their own rows said -- the disagreement the renumber exists
    to prevent, moved one date over. The code was wrong; the test had pinned it.
    """
    _at(manager, 30, "today", 4)
    _at(manager, 30, "tomorrow", 4, block_date=NEXT_DAY)

    assert manager.shift_all_slots(1) == 2, "a date was left behind"

    placed = {label: row[0] for label, row in _rows(manager).items()}
    assert placed == {"today": 5, "tomorrow": 5}, placed

    # The point of the renumber, stated as the time rather than the index:
    # under the day that now starts half an hour earlier, both are where the
    # person put them.
    for date in (DAY, NEXT_DAY):
        grid = build_day_grid(
            manager.get_time_blocks(date), DayBounds(day_start="07:30")
        )
        drawn = {
            entry.starting[0].label: entry.slot.start_time
            for entry in grid.slots
            if entry.starting
        }
        assert drawn == {
            DAY: {"today": "10:00"}, NEXT_DAY: {"tomorrow": "10:00"}
        }[date], (date, drawn)


# --- CE-M1.2 / CE-M1.3 — the event id a block owns --------------------------

def test_cem12_calendar_event_id_round_trips(manager):
    """CE-M1.2 — the column is written by both writers and read back.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m12
    Tests: this test
    """
    block_id = _add(manager, 30, "exported")

    assert manager.get_time_block(block_id).calendar_event_id is None, (
        "a block that has not been exported must read as not exported"
    )

    manager.set_block_calendar_event_id(block_id, "gcal-abc123")
    assert manager.get_time_block(block_id).calendar_event_id == "gcal-abc123"

    # It can be taken away again, for a block whose event is gone.
    manager.set_block_calendar_event_id(block_id, None)
    assert manager.get_time_block(block_id).calendar_event_id is None


def test_cem12_a_row_without_the_column_still_reads(manager):
    """CE-M1.2 — a projection that leaves the column out must not raise.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m12
    Tests: this test

    Behavioural stand-in for a row selected before the migration ran: a
    `sqlite3.Row` that simply does not carry the key, which is exactly what
    `_row_to_time_block` meets in that case.
    """
    _add(manager, 30, "narrow select")

    row = manager.db.conn.execute(
        """
        SELECT id, item_id, block_date, start_time, end_time, planned_minutes,
               label, block_type, slot_index, position, created_at, updated_at
        FROM time_blocks
        """
    ).fetchone()

    block = manager._row_to_time_block(row)

    assert block.label == "narrow select"
    assert block.calendar_event_id is None


def test_cem13_recording_an_event_id_leaves_the_block_where_it_was(manager):
    """CE-M1.3 — the narrow writer writes one column and moves nothing.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m13
    Tests: this test

    The exporter reads a day, talks to Google, and comes back to write ids. A
    writer that wrote whole blocks back would restore the boxes it read
    minutes earlier -- so the day is moved *after* the read and before the
    write, and the write must not undo it.
    """
    block = TimeBlock(
        block_date=DAY,
        start_time="",
        end_time="",
        planned_minutes=30,
        label="moved after the read",
    )
    placed = manager.add_block_at(block, 0, BOUNDS)
    stale = manager.get_time_block(placed.id)

    moved = manager.place_block_at(placed.id, 4, BOUNDS)
    assert moved.slot_index == 4

    # The exporter is holding `stale`, which still says box 0.
    assert stale.slot_index == 0
    manager.set_block_calendar_event_id(stale.id, "gcal-xyz789")

    after = manager.get_time_block(placed.id)
    assert after.slot_index == 4, (
        "recording an event id must not put the block back in the box the "
        "exporter read"
    )
    assert after.start_time == moved.start_time
    assert after.end_time == moved.end_time
    assert after.position == moved.position
    assert after.calendar_event_id == "gcal-xyz789"


def test_cem13_an_edit_does_not_erase_the_event_id(manager):
    """CE-M1.3 — ``update_time_block`` leaves the event id alone.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m13
    Tests: this test

    The screen holds block objects it loaded when the day was drawn. Export
    the day, then resize a block from that older object -- which still says
    ``calendar_event_id is None``, because it predates the export -- and the
    id must survive. An ``update_time_block`` that wrote this column would
    erase it here, and the next export would create a second event for a
    block that already had one.
    """
    block = TimeBlock(
        block_date=DAY,
        start_time="",
        end_time="",
        planned_minutes=30,
        label="drawn before the export",
    )
    placed = manager.add_block_at(block, 0, BOUNDS)
    as_the_screen_holds_it = manager.get_time_block(placed.id)

    manager.set_block_calendar_event_id(placed.id, "gcal-already-exported")

    as_the_screen_holds_it.planned_minutes = 45
    manager.update_time_block(as_the_screen_holds_it)

    after = manager.get_time_block(placed.id)
    assert after.planned_minutes == 45, "the edit itself must still land"
    assert after.calendar_event_id == "gcal-already-exported", (
        "a resize from a block loaded before the export must not orphan the "
        "event that export created"
    )


def test_cem13_recording_an_event_id_touches_one_block(manager):
    """CE-M1.3 — and it writes to exactly the block it was given."""
    first = _add(manager, 30, "first")
    second = _add(manager, 30, "second")

    manager.set_block_calendar_event_id(first, "gcal-only-the-first")

    assert manager.get_time_block(first).calendar_event_id == "gcal-only-the-first"
    assert manager.get_time_block(second).calendar_event_id is None


def test_cem12b_the_event_calendar_round_trips(tmp_path):
    """CE-M1.2 — the calendar is stored and read back with the id.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m12
    Tests: this test

    An id with no calendar is not usable: the export has to know where to look
    for the event, and the export calendar is a setting the user can change.
    """
    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        block = TimeBlock(
            block_date="2026-11-09", start_time="08:00", end_time="08:30",
            planned_minutes=30, label="Gym", block_type=BlockType.BREAK,
            slot_index=0,
            calendar_event_id="evt-a",
            calendar_event_calendar_id="work@example.com",
        )
        manager.create_time_block(block)

        stored = manager.get_time_blocks("2026-11-09")[0]

        assert stored.calendar_event_id == "evt-a"
        assert stored.calendar_event_calendar_id == "work@example.com"

        assert manager.set_block_calendar_event_id(
            block.id, "evt-b", "home@example.com"
        )
        moved = manager.get_time_blocks("2026-11-09")[0]

        assert (moved.calendar_event_id, moved.calendar_event_calendar_id) == (
            "evt-b", "home@example.com"
        )
    finally:
        manager.close()


def test_cem12c_clearing_the_id_clears_the_calendar_with_it(tmp_path):
    """CE-M1.2 — a recorded calendar with no event is not a state we produce.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m12
    Tests: this test

    The sweep clears the id when it removes an event. A calendar left behind
    would read as "this block has an event over there" for the rest of the
    row's life (P6).

    The clearing call passes a calendar as well as `None`, because that is the
    only way this guard can be exercised: mutation proved the first version of
    this test — which cleared with the argument defaulted — could not fail.
    """
    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        block = TimeBlock(
            block_date="2026-11-09", start_time="08:00", end_time="08:30",
            planned_minutes=30, label="Gym", block_type=BlockType.BREAK,
            slot_index=0,
        )
        manager.create_time_block(block)
        manager.set_block_calendar_event_id(block.id, "evt-a", "work@example.com")

        manager.set_block_calendar_event_id(block.id, None, "work@example.com")
        cleared = manager.get_time_blocks("2026-11-09")[0]

        assert cleared.calendar_event_id is None
        assert cleared.calendar_event_calendar_id is None
    finally:
        manager.close()
