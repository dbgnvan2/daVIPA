"""TB-M2 — the writes a planned day needs, including the one that did not exist.

Purpose: hold update_time_block, repack_day, reorder_time_blocks and the
         exact-start-date item query to their stated behaviour.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m2
Tests:   this file

Before TB-M2 this module could create, read and delete a block and nothing
else. No block could be resized, retyped or reordered after creation, which is
what made "right-click to set a time amount" and "drag blocks to rearrange"
unbuildable rather than merely unbuilt.
"""

import pytest

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.time_block_layout import DayBounds

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
    """(label, position, start, end) for each block on a day, in order."""
    return [
        (b.label, b.position, b.start_time, b.end_time)
        for b in manager.get_time_blocks(block_date)
    ]


# --- creating ---------------------------------------------------------------

def test_a_new_block_is_appended_to_its_day(manager):
    """Position 0 means "append", so the three ways of making a block all land at the end."""
    _add(manager, 30, "first")
    _add(manager, 30, "second")
    _add(manager, 30, "third")

    assert [(label, position) for label, position, _, _ in _day(manager)] == [
        ("first", 1), ("second", 2), ("third", 3),
    ]


def test_appending_counts_only_the_day_it_is_appending_to(manager):
    """Two days planned side by side must not share a position counter."""
    _add(manager, 30, "a", block_date=DAY)
    _add(manager, 30, "b", block_date=DAY)
    _add(manager, 30, "other-day", block_date=NEXT_DAY)

    assert [position for _, position, _, _ in _day(manager, NEXT_DAY)] == [1]


def test_a_caller_with_an_explicit_position_keeps_it(manager):
    """A reorder and a test fixture both set position themselves."""
    block = TimeBlock(
        block_date=DAY, start_time="", end_time="", planned_minutes=30,
        label="placed", position=7,
    )
    manager.create_time_block(block)

    assert [position for _, position, _, _ in _day(manager)] == [7]


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


# --- TB-M2.2 : re-timing and reordering -------------------------------------

def test_tbm22_reorder_yields_unique_contiguous_times(manager):
    """TB-M2.2 — after a reorder no two blocks share a start, and there are no gaps.

    Asserted as properties of the day rather than against a hardcoded
    expectation, so the test still bites when the lengths or the day's bounds
    change.
    """
    ids = [_add(manager, minutes, label) for minutes, label in
           ((60, "a"), (30, "b"), (45, "c"), (30, "d"))]

    manager.reorder_time_blocks(DAY, [ids[3], ids[0], ids[2], ids[1]], BOUNDS)

    blocks = manager.get_time_blocks(DAY)
    assert [b.label for b in blocks] == ["d", "a", "c", "b"]
    assert [b.position for b in blocks] == [1, 2, 3, 4]

    starts = [b.start_time for b in blocks]
    assert len(set(starts)) == len(starts), "two blocks claim the same minute"
    for earlier, later in zip(blocks, blocks[1:]):
        assert later.start_time >= earlier.end_time, "blocks overlap"


def test_reorder_moves_the_clock_times_with_the_order(manager):
    """The times are derived from the order, so reordering re-times the day."""
    ids = [_add(manager, 60, "a"), _add(manager, 30, "b")]

    manager.repack_day(DAY, BOUNDS)
    assert _day(manager) == [
        ("a", 1, "08:00", "09:00"),
        ("b", 2, "09:00", "09:30"),
    ]

    manager.reorder_time_blocks(DAY, [ids[1], ids[0]], BOUNDS)
    assert _day(manager) == [
        ("b", 1, "08:00", "08:30"),
        ("a", 2, "08:30", "09:30"),
    ]


def test_reorder_keeps_blocks_the_caller_did_not_name(manager):
    """A stale id list must not drop a block out of the day by omission.

    A screen that has not refreshed since another surface added a block would
    otherwise delete it from the order, and the day would show two blocks
    sharing a minute.
    """
    ids = [_add(manager, 30, "a"), _add(manager, 30, "b"), _add(manager, 30, "c")]

    manager.reorder_time_blocks(DAY, [ids[2], ids[0]], BOUNDS)

    blocks = manager.get_time_blocks(DAY)
    assert [b.label for b in blocks] == ["c", "a", "b"], (
        "the unnamed block should keep its place after the named ones"
    )
    assert [b.position for b in blocks] == [1, 2, 3]


def test_reorder_ignores_an_id_from_another_day(manager):
    _add(manager, 30, "mine")
    other = _add(manager, 30, "theirs", block_date=NEXT_DAY)

    manager.reorder_time_blocks(DAY, [other], BOUNDS)

    assert [label for label, _, _, _ in _day(manager)] == ["mine"]
    assert [label for label, _, _, _ in _day(manager, NEXT_DAY)] == ["theirs"]


def test_repack_respects_lunch(manager):
    """The stored times come from the same packing rules as the display."""
    for minutes, label in ((60, "a"), (60, "b"), (60, "c"), (90, "d")):
        _add(manager, minutes, label)

    manager.repack_day(DAY, BOUNDS)

    assert _day(manager) == [
        ("a", 1, "08:00", "09:00"),
        ("b", 2, "09:00", "10:00"),
        ("c", 3, "10:00", "11:00"),
        ("d", 4, "13:00", "14:30"),  # would run through lunch, so moved whole
    ]


def test_repack_renumbers_a_migrated_day(manager):
    """A day of legacy position-0 rows comes out numbered 1..n in clock order."""
    for label, start in (("late", "15:00"), ("early", "09:00")):
        manager.db.conn.execute(
            "INSERT INTO time_blocks (id, item_id, block_date, start_time, end_time,"
            " planned_minutes, label, block_type, position, created_at, updated_at)"
            " VALUES (?, NULL, ?, ?, ?, 30, ?, 'item', 0, '2026-01-01', '2026-01-01')",
            (label, DAY, start, start, label),
        )
    manager.db.conn.commit()

    manager.repack_day(DAY, BOUNDS)

    assert _day(manager) == [
        ("early", 1, "08:00", "08:30"),
        ("late", 2, "08:30", "09:00"),
    ]


# --- TB-M2.3 : atomicity ----------------------------------------------------

class _ExplodingBounds:
    """Bounds that raise the moment packing reads them.

    pack_day asks for day_start_minutes first, which puts the failure *after*
    reorder_time_blocks has already written its positions and before anything
    is committed — exactly the half-applied state the transaction exists to
    prevent.
    """

    default_block_minutes = 30
    block_weekdays = (True,) * 7

    @property
    def day_start_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def day_end_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def lunch_start_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def lunch_end_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def lunch_length(self):
        raise RuntimeError("bounds unreadable")


def test_tbm23_failed_reorder_is_atomic(manager):
    """TB-M2.3 — a reorder that fails partway writes nothing.

    Half of a reorder is worse than none: the day would hold two blocks
    claiming the same minutes, and the next repack would start from the broken
    state and reproduce it.
    """
    ids = [_add(manager, 30, "a"), _add(manager, 30, "b"), _add(manager, 30, "c")]
    manager.repack_day(DAY, BOUNDS)
    before = _day(manager)

    with pytest.raises(RuntimeError):
        manager.reorder_time_blocks(DAY, [ids[2], ids[1], ids[0]], _ExplodingBounds())

    assert _day(manager) == before, "a failed reorder left the day changed"


def test_a_failed_repack_leaves_the_stored_times_alone(manager):
    _add(manager, 30, "a")
    _add(manager, 30, "b")
    manager.repack_day(DAY, BOUNDS)
    before = _day(manager)

    with pytest.raises(RuntimeError):
        manager.repack_day(DAY, _ExplodingBounds())

    assert _day(manager) == before


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
