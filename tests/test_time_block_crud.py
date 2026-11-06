"""TB-M2/TG-M6 — the writes a planned day needs.

Purpose: hold update_time_block, the slot-aware writes, and the
         exact-start-date item query to their stated behaviour.
Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m6
Tests:   this file

**The reorder and repack tests that used to be most of this file are gone**,
with the writes they covered. A planned day was an order, so every edit had to
re-derive and re-store the whole day's clock times; a block now stores which
half-hour box it sits in, relative to Day Start, and the times follow from the
box on read. There is nothing to re-pack, nothing to renumber, and no ceiling
to run past — the last box ends at Day End. TG-M6.4 at the foot of this file is
the test that says so: a Day Start change writes no rows at all.
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
