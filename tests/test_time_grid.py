"""TG-M1/M2/M3 — the 30-minute grid, as arithmetic.

Purpose: prove the fixed grid a planned day is drawn on -- which boxes exist,
         how many a block occupies, where a block may be placed, and what
         happens to a block the grid can no longer hold.
Spec:    docs/implementation_plan_2026-11-05_time_grid.md#m1
Tests:   this file

None of this needs a display. The grid is arithmetic, and arithmetic should be
provable headless -- which is the whole reason it does not live in
``screens/plan.py``.
"""

from __future__ import annotations

import pytest

from src.getmoredone.models import TimeBlock
from src.getmoredone.time_block_layout import (
    MAX_BLOCKS_PER_SLOT,
    SLOT_MINUTES,
    DayBounds,
    SlotRefusal,
    build_day_grid,
    can_place,
    day_grid,
    drawn_day_slots,
    slot_index_for_time,
    slot_is_on_the_date,
    slot_occupancy,
    slot_span_of,
    slots_for_minutes,
    spare_minutes_in_last_slot,
    times_for_slot,
)

BOUNDS = DayBounds()
DAY = "2026-11-05"


def _block(minutes: int, slot_index=None, label="block", position=0) -> TimeBlock:
    """A block with no clock times, because the grid derives them."""
    return TimeBlock(
        block_date=DAY,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        slot_index=slot_index,
        position=position,
    )


# =====================================================================
# TG-M1 -- the grid itself
# =====================================================================


def test_tgm11_grid_covers_the_day_in_half_hours():
    """TG-M1.1 — one slot per half hour from Day Start to Day End.

    The default day is 08:00--17:00, which is nine hours and so eighteen
    boxes. Asserted as times rather than a count alone: a grid of the right
    length starting in the wrong place would pass a count.
    """
    grid = day_grid(BOUNDS)

    assert len(grid) == 18
    assert grid[0].start_time == "08:00"
    assert grid[0].end_time == "08:30"
    assert grid[-1].start_time == "16:30"
    assert grid[-1].end_time == "17:00"
    assert [slot.index for slot in grid] == list(range(18))


def test_the_grid_is_contiguous_in_time():
    """Every slot begins where the one before it ended.

    The span arithmetic depends on this: a block's end is its start plus its
    length, computed without walking the list, which is only true while no
    slot is skipped.
    """
    grid = day_grid(BOUNDS)

    for earlier, later in zip(grid, grid[1:]):
        assert later.start_minutes == earlier.end_minutes


def test_tgm12_lunch_slots_are_marked_not_removed():
    """TG-M1.2 — lunch is unavailable boxes, not a hole in the grid.

    Removing them would break contiguity and make a span's end wrong. The
    default lunch is 12:00 for an hour, so exactly two boxes are marked.
    """
    grid = day_grid(BOUNDS)

    lunch = [slot.start_time for slot in grid if slot.is_lunch]
    assert lunch == ["12:00", "12:30"]
    assert len(grid) == 18, "marking a slot must not remove it"


def test_a_lunch_that_straddles_two_boxes_marks_both():
    """**Adversarial (P7)** — 12:15–12:45 is inside no box and across two.

    Tested by overlap, not containment: a block in either box would run
    through part of lunch, so both are unavailable. A containment test would
    mark neither and quietly let a block sit on top of lunch.
    """
    bounds = DayBounds(lunch_start="12:15", lunch_minutes=30)

    lunch = [slot.start_time for slot in day_grid(bounds) if slot.is_lunch]

    assert lunch == ["12:00", "12:30"]


def test_a_zero_minute_lunch_marks_nothing():
    """Set the minutes to 0 for no lunch -- the user guide's own words."""
    bounds = DayBounds(lunch_minutes=0)

    assert [slot for slot in day_grid(bounds) if slot.is_lunch] == []


def test_tgm13_a_ragged_day_end_yields_no_partial_slot():
    """TG-M1.3 — a Day End off the half hour gives no stub box.

    16:45 ends the last whole box at 16:30. A 15-minute stub would be a box
    that cannot hold the smallest block there is, drawn as though it could.
    """
    grid = day_grid(DayBounds(day_end="16:45"))

    assert grid[-1].start_time == "16:00"
    assert grid[-1].end_time == "16:30"
    assert all(slot.end_minutes <= 16 * 60 + 45 for slot in grid)


@pytest.mark.parametrize("day_end", ["08:00", "07:00"])
def test_a_day_that_ends_before_it_starts_has_no_slots(day_end):
    """An empty grid, not a negative one, and not a crash."""
    assert day_grid(DayBounds(day_end=day_end)) == []


# =====================================================================
# TG-M2 -- placement
# =====================================================================


@pytest.mark.parametrize(
    "minutes, expected",
    [(30, 1), (45, 2), (60, 2), (1, 1), (90, 3), (31, 2), (0, 1), (None, 1)],
)
def test_tgm21_odd_lengths_round_up(minutes, expected):
    """TG-M2.1 — 45 minutes takes two boxes, and nothing takes none.

    The zero and ``None`` cases matter: a block with a nonsense length still
    has to be somewhere, and a zero-slot block would be invisible and
    undraggable rather than obviously wrong.
    """
    assert slots_for_minutes(minutes) == expected


def test_a_blocks_span_is_derived_not_stored():
    """Changing the length changes the span, with nothing else written.

    Two columns that can disagree about one fact is the failure this project
    catalogues as P6, so there is no ``span`` column to drift.
    """
    block = _block(45)
    assert slot_span_of(block) == 2

    block.planned_minutes = 30
    assert slot_span_of(block) == 1


def test_tgm22_a_span_cannot_cross_lunch():
    """TG-M2.2 — **adversarial (P7)**: the box is free, the one after is lunch.

    11:30 is a legal box and a 30-minute block sits there happily. A
    60-minute block at the same box would run into 12:00, which is lunch --
    and a placement check that only looked at the box dropped on would allow
    it and draw a block straight through the lunch band.
    """
    at_1130 = 7  # 08:00 + 7 half hours

    assert can_place([], BOUNDS, at_1130, slots_for_minutes(30)) is None
    assert can_place([], BOUNDS, at_1130, slots_for_minutes(60)) == (
        SlotRefusal.CROSSES_LUNCH
    )


def test_a_block_may_not_start_on_lunch_either():
    """The simpler half of the same rule, so it is not fixed on one side."""
    at_1200 = 8

    assert can_place([], BOUNDS, at_1200, 1) == SlotRefusal.CROSSES_LUNCH


def test_tgm23_each_refusal_has_its_own_reason():
    """TG-M2.3 — three refusals, three distinct named values.

    One shared "no" would reach the user as one sentence for three different
    situations, which is the thing the single ``DAY_TOO_FULL`` string was
    written to avoid in the previous model.
    """
    full_slot = [_block(30, slot_index=0, position=n) for n in range(MAX_BLOCKS_PER_SLOT)]

    reasons = {
        can_place([], BOUNDS, -1, 1),
        can_place([], BOUNDS, 17, 2),
        can_place([], BOUNDS, 8, 1),
        can_place(full_slot, BOUNDS, 0, 1),
    }

    assert reasons == {
        SlotRefusal.OUTSIDE_GRID,
        SlotRefusal.CROSSES_LUNCH,
        SlotRefusal.SLOT_FULL,
    }
    assert len({SlotRefusal.OUTSIDE_GRID, SlotRefusal.CROSSES_LUNCH, SlotRefusal.SLOT_FULL}) == 3


def test_a_block_running_past_the_last_box_is_outside_the_grid():
    """The last box holds a 30; it cannot hold a 60."""
    last = 17

    assert can_place([], BOUNDS, last, 1) is None
    assert can_place([], BOUNDS, last, 2) == SlotRefusal.OUTSIDE_GRID


def test_pdm13_the_extension_gesture_is_the_only_caller_that_may_go_outside():
    """PD-M13 — the drawn day is the limit, and one flag lifts it.

    The box after the last one is refused for every ordinary write, which is
    what keeps AutoLoad and pre-grid adoption inside the day the user
    configured. ``allow_outside_range`` is the Earlier/Later extension saying
    it means to make the day wider, and nothing else passes it.
    """
    last_box = len(day_grid(BOUNDS)) - 1
    past_the_end = last_box + 1

    assert can_place([], BOUNDS, past_the_end, 1) == SlotRefusal.OUTSIDE_GRID
    assert can_place([], BOUNDS, past_the_end, 1, allow_outside_range=True) is None
    # Before the day as well as after it, so the Earlier half is covered too.
    assert can_place([], BOUNDS, -1, 1) == SlotRefusal.OUTSIDE_GRID
    assert can_place([], BOUNDS, -1, 1, allow_outside_range=True) is None


def test_pdm13_a_box_the_day_is_already_drawn_on_needs_no_flag():
    """PD-M13 — once work sits past Day End, that box is droppable.

    The distinction the flag rests on: the limit is the day *as drawn*, not the
    configured range. A box past Day End that something is already drawn on is
    a box the user can point at, so an ordinary drop there must be allowed --
    otherwise a block could be put outside the day by the extension and then
    never moved within the hours it had just created.
    """
    out_there = [_block(30, slot_index=20)]

    # Nothing is drawn at 21 or beyond, so it stays a refusal...
    assert can_place(out_there, BOUNDS, 21, 1) == SlotRefusal.OUTSIDE_GRID
    # ...but 20 is drawn now, and sharing it is an ordinary write.
    assert can_place(out_there, BOUNDS, 20, 1) is None
    # The same box on a day with nothing out there is refused, which is what
    # makes the block above the reason and not a coincidence.
    assert can_place([], BOUNDS, 20, 1) == SlotRefusal.OUTSIDE_GRID


def test_pdm13_the_date_is_the_limit_even_for_the_extension():
    """PD-M13 — the flag lifts the day's range, never the date's.

    A block has no way to say it belongs to another date, so a box off the
    date is refused however the write asks. 08:00 plus 32 boxes is midnight.
    """
    assert can_place([], BOUNDS, 32, 1, allow_outside_range=True) == SlotRefusal.OUTSIDE_GRID
    assert can_place([], BOUNDS, 31, 2, allow_outside_range=True) == SlotRefusal.OUTSIDE_GRID
    assert can_place([], BOUNDS, -16, 1, allow_outside_range=True) is None
    assert can_place([], BOUNDS, -17, 1, allow_outside_range=True) == SlotRefusal.OUTSIDE_GRID


def test_a_second_task_may_share_a_box():
    """The user's decision: a box holds more than one task.

    Paired with the full-box refusal below so neither is proved alone.
    """
    occupied = [_block(30, slot_index=4)]

    assert can_place(occupied, BOUNDS, 4, 1) is None


def test_tgm24_a_full_day_refuses_the_next_one():
    """TG-M2.4 — **real scale (P9)**: every box filled to its limit.

    Sixteen available boxes (eighteen less the two lunch ones), each holding
    the maximum, and the next placement is refused rather than drawn on top
    of something. The fixture is big enough that the limit actually bites,
    which is the point of a real-scale test.
    """
    blocks = [
        _block(30, slot_index=slot.index, position=n)
        for slot in day_grid(BOUNDS)
        if not slot.is_lunch
        for n in range(MAX_BLOCKS_PER_SLOT)
    ]
    assert len(blocks) == 16 * MAX_BLOCKS_PER_SLOT

    assert can_place(blocks, BOUNDS, 0, 1) == SlotRefusal.SLOT_FULL
    assert can_place(blocks, BOUNDS, 17, 1) == SlotRefusal.SLOT_FULL


def test_a_block_being_moved_does_not_block_its_own_slot():
    """Moving a block within a full box must not refuse on its own account.

    Without ``ignoring`` a block already in a box counts against the room in
    that box, so nudging it would be refused by its own presence.
    """
    mover = _block(30, slot_index=3, label="mover")
    others = [_block(30, slot_index=3, position=n) for n in range(MAX_BLOCKS_PER_SLOT - 1)]

    assert can_place([mover] + others, BOUNDS, 3, 1) == SlotRefusal.SLOT_FULL
    assert can_place([mover] + others, BOUNDS, 3, 1, ignoring=mover.id) is None


def test_occupancy_counts_every_box_a_span_covers():
    """A 60-minute block at box 4 occupies 4 *and* 5.

    "Is there room here" has to mean the whole box, not just where something
    started -- otherwise a long block's tail is invisible to the check and
    anything may be dropped on top of it.
    """
    occupancy = slot_occupancy([_block(60, slot_index=4)], BOUNDS)

    assert sorted(occupancy) == [4, 5]


# =====================================================================
# Derived times
# =====================================================================


def test_pdm13_a_box_before_day_start_carries_the_earlier_time():
    """PD-M13 — box -1 is 07:30, not Day Start clamped back to itself.

    ``times_for_slot`` clamped the index at zero, from when a box before Day
    Start could not exist. Under PD-M13 it can, and the clamp wrote 08:00 into
    a row the grid drew at 07:30 -- the stored time and the drawn time
    disagreeing, with nothing marked wrong, which is the exact failure the
    renumber this change deletes was built to prevent (P6: the row is checked
    against what it claims, not trusted).
    """
    assert times_for_slot(-1, 30, BOUNDS) == ("07:30", "08:00")
    assert times_for_slot(-3, 90, BOUNDS) == ("06:30", "08:00")
    # The box after the last one keeps working the same way.
    assert times_for_slot(18, 30, BOUNDS) == ("17:00", "17:30")


def test_times_for_slot_reads_off_the_grid():
    """Box 4 of an 08:00 day is 10:00."""
    assert times_for_slot(4, 30, BOUNDS) == ("10:00", "10:30")


def test_a_rounded_up_block_ends_when_the_item_does_not_when_the_box_does():
    """The 45-into-two-boxes case, asserted as the times that get stored.

    09:45, not 10:00. Writing the end of the second box would be the row
    claiming fifteen minutes the item does not own -- and the next box is
    free from 09:45 only in the sense that nothing else may have it, which is
    what "15m spare" on screen says.
    """
    assert times_for_slot(2, 45, BOUNDS) == ("09:00", "09:45")
    assert slots_for_minutes(45) == 2


def test_a_moved_day_start_moves_every_time_with_no_row_written():
    """The reason the slot is relative to Day Start rather than absolute.

    The same stored block reads as 10:00 under an 08:00 day and 11:00 under a
    09:00 one, with nothing written in between. This is what retires the
    repack-every-day machinery.
    """
    assert times_for_slot(4, 30, BOUNDS)[0] == "10:00"
    assert times_for_slot(4, 30, DayBounds(day_start="09:00"))[0] == "11:00"


# =====================================================================
# TG-M3 -- laying a day out
# =====================================================================


def test_a_day_grid_puts_each_block_in_its_box():
    """The spanning block appears once as starting and once as continued.

    Drawn differently in each: the box it starts in carries the title, the
    one it runs into says it is the same task rather than a second one.
    """
    grid = build_day_grid([_block(60, slot_index=4, label="long")], BOUNDS)

    assert [b.label for b in grid.slots[4].starting] == ["long"]
    assert [b.label for b in grid.slots[5].continued] == ["long"]
    assert grid.slots[5].starting == []
    assert grid.slots[3].is_empty


def test_an_empty_box_is_still_a_row():
    """Gaps are legitimate, so an empty box is drawn, not skipped."""
    grid = build_day_grid([_block(30, slot_index=4)], BOUNDS)

    assert len(grid.slots) == 18
    assert grid.slots[3].is_empty
    assert not grid.slots[4].is_empty


def test_pdm13_a_block_past_the_configured_day_is_drawn_rather_than_listed():
    """PD-M13 — **P2 discharged better**: drawn at its own hour, not exiled.

    This asserted ``grid.outside == ["late"]`` until PD-M13, under reason (b):
    the behaviour changed intentionally. P2 is the same guarantee -- a block is
    never dropped -- and the drawn day now satisfies it by *showing* the block
    at its real time instead of listing it in a footnote under the day. Day End
    moving earlier in Settings no longer takes the box away; it only narrows
    the day the user configured, and the drawn day widens past it to whatever
    is still planned there.

    The two assertions that matter are that the block has a box and that
    nothing is in ``outside``: a block in neither place would be the loss P2
    names, and this test would then fail on the first one.
    """
    blocks = [_block(30, slot_index=2, label="inside"), _block(30, slot_index=30, label="late")]

    grid = build_day_grid(blocks, BOUNDS)

    drawn = {
        block.label: entry.slot.index
        for entry in grid.slots
        for block in entry.starting
    }
    assert drawn == {"inside": 2, "late": 30}
    assert [b.label for b in grid.outside] == []


def test_pdm13_a_block_whose_span_runs_past_the_day_is_drawn_too():
    """The subtler half, inverted with it: the span extends the day as well."""
    grid = build_day_grid([_block(120, slot_index=17, label="too long")], BOUNDS)

    drawn = [
        entry.slot.index for entry in grid.slots if entry.starting
    ]
    assert drawn == [17], drawn
    assert [b.label for b in grid.outside] == []
    # Four boxes of a 120, the last of them 20 -- 17 + 4 - 1.
    assert grid.slots[-1].slot.index == 20, grid.slots[-1].slot.index


def test_a_never_placed_block_is_surfaced_rather_than_assumed_to_be_at_eight():
    """``slot_index`` of ``None`` is "never placed", not "box zero".

    Defaulting it to 0 would silently pile every unplaced block onto the
    first box of the day.
    """
    grid = build_day_grid([_block(30, slot_index=None, label="unplaced")], BOUNDS)

    assert [b.label for b in grid.outside] == ["unplaced"]
    assert grid.slots[0].is_empty


def test_a_block_sitting_in_a_lunch_box_is_surfaced_not_hidden():
    """A box marked lunch draws no tasks, so a block left in one would vanish.

    ``can_place`` refuses lunch, so nothing *new* lands there -- but lunch is a
    setting, and moving it onto an already-planned half hour puts a block in a
    box that will not draw it. Routed to ``outside`` instead, which is the one
    place the user can still see it (P2).
    """
    blocks = [_block(30, slot_index=0, label="early"), _block(30, slot_index=1, label="moved onto lunch")]

    grid = build_day_grid(blocks, DayBounds(lunch_start="08:30", lunch_minutes=30))

    assert [b.label for b in grid.outside] == ["moved onto lunch"]
    assert [b.label for b in grid.slots[0].starting] == ["early"]
    assert grid.slots[1].is_empty


def test_a_span_that_runs_through_lunch_is_surfaced_too():
    """The same for a block whose later boxes are the ones lunch moved onto."""
    grid = build_day_grid(
        [_block(90, slot_index=0, label="runs into lunch")],
        DayBounds(lunch_start="08:30", lunch_minutes=30),
    )

    assert [b.label for b in grid.outside] == ["runs into lunch"]
    assert all(entry.is_empty for entry in grid.slots)


@pytest.mark.parametrize(
    "minutes,spare",
    [(30, 0), (45, 15), (60, 0), (75, 15), (90, 0), (15, 15), (1, 29)],
)
def test_the_spare_minutes_of_the_last_box_are_what_the_task_leaves(minutes, spare):
    """The minutes the last box gives the task that the task does not use.

    Written on screen rather than rounded away: 45 minutes in two boxes ends at
    09:45 and leaves 15 of the second box spare, and the next task starts at
    the following box, not at the minute this one ends.
    """
    assert spare_minutes_in_last_slot(_block(minutes)) == spare


def test_a_block_with_no_length_leaves_nothing_spare():
    """Zero minutes occupies no box, so there is no box for it to part-fill.

    Reporting 30m spare for it would describe a box the block does not hold.
    """
    assert spare_minutes_in_last_slot(_block(0)) == 0


def test_two_tasks_in_one_box_are_ordered_by_position():
    """``position`` orders *within* a box now, and that order is settled."""
    blocks = [
        _block(30, slot_index=4, label="second", position=2),
        _block(30, slot_index=4, label="first", position=1),
    ]

    grid = build_day_grid(blocks, BOUNDS)

    assert [b.label for b in grid.slots[4].starting] == ["first", "second"]


def test_the_day_counts_boxes_used_not_tasks():
    """The user's decision: a box is worth 30 minutes however many share it.

    Two tasks in one box and one in another is two boxes, an hour of the day
    -- not three tasks and ninety minutes.
    """
    blocks = [
        _block(30, slot_index=4, position=1),
        _block(30, slot_index=4, position=2),
        _block(30, slot_index=6),
    ]

    grid = build_day_grid(blocks, BOUNDS)

    assert grid.slots_used == 2
    assert grid.minutes_occupied == 2 * SLOT_MINUTES


def test_a_spanning_block_uses_every_box_it_covers():
    """Paired with the test above so "boxes used" is not just "boxes started"."""
    grid = build_day_grid([_block(90, slot_index=4)], BOUNDS)

    assert grid.slots_used == 3
    assert grid.minutes_occupied == 90


# =====================================================================
# TG-M5 -- reading an existing day onto the grid
# =====================================================================


@pytest.mark.parametrize(
    "start_time, expected",
    [("08:00", 0), ("09:30", 3), ("12:00", 8), ("16:30", 17), ("08:29", 0)],
)
def test_tgm51_a_stored_time_maps_to_its_box(start_time, expected):
    """The migration's arithmetic, proved before it is wired to a database."""
    assert slot_index_for_time(start_time, BOUNDS) == expected


@pytest.mark.parametrize("start_time", ["", None, "nonsense", "07:30"])
def test_a_time_that_cannot_be_placed_returns_none(start_time):
    """Unreadable, or before the day starts -- the caller falls back.

    ``None`` rather than 0, so the migration can tell "no time here" from
    "the first box" and use the row's position instead of inventing a slot.
    """
    assert slot_index_for_time(start_time, BOUNDS) is None


# ---------------------------------------------------------------------------
# PD-M13 — the configured day and the day as drawn are two different things
# ---------------------------------------------------------------------------


def test_pdm133_a_block_before_day_start_gets_a_box():
    """PD-M13.3 — a block at a negative index is drawn, not listed as outside.

    The mechanism the whole change rests on. Before this, the only way to get
    a box before the configured Day Start was to move ``plan_day_start`` and
    renumber every date's blocks to match, so one drop on one date redefined
    the working day everywhere. A negative ``slot_index`` means the same thing
    -- one box earlier than the day the user configured -- and costs no other
    date anything.
    """
    grid = build_day_grid([_block(30, slot_index=-2, label="early")], BOUNDS)

    first = grid.slots[0]
    assert first.slot.index == -2, first.slot.index
    assert [b.label for b in first.starting] == ["early"]
    assert grid.outside == []
    # 08:00 less two boxes. The box knows its clock time, so the row and the
    # screen cannot disagree about when the block is.
    assert first.slot.start_minutes == 7 * 60


def test_pdm134_a_block_past_day_end_gets_a_box():
    """PD-M13.4 — and the same at the other end."""
    grid = build_day_grid([_block(30, slot_index=19, label="late")], BOUNDS)

    last = grid.slots[-1]
    assert last.slot.index == 19, last.slot.index
    assert [b.label for b in last.starting] == ["late"]
    assert grid.outside == []
    assert last.slot.start_minutes == 17 * 60 + 30


def test_pdm135_a_block_in_lunch_is_still_surfaced():
    """PD-M13.5 — **P2**: widening the day must not empty ``outside``.

    The drawn day grows to cover a block past either end, so the two cases
    that used to fill ``outside`` no longer do. If that had been allowed to
    make ``outside`` dead, the one case it still has to carry -- a block the
    user's lunch hour has moved on top of, which a lunch box draws nothing of
    -- would have gone quietly missing. ``can_place`` refuses lunch, so this
    is only reachable after the lunch hour moves over planned work.
    """
    grid = build_day_grid([_block(30, slot_index=8, label="eaten")], BOUNDS)

    assert [b.label for b in grid.outside] == ["eaten"]
    assert all(not entry.starting for entry in grid.slots), (
        "the block was drawn in a lunch box, which draws Lunch and nothing else"
    )


def test_pdm133_an_ordinary_day_draws_exactly_the_configured_range():
    """PD-M13.3 — the configured range is the floor, not just a starting point.

    With nothing outside it the drawn day is the configured day, box for box.
    A version of ``drawn_day_slots`` that took its extent from the blocks alone
    would shrink an empty day to nothing, so the day the user set is the
    narrowest it can ever draw.
    """
    assert [slot.index for slot in drawn_day_slots(BOUNDS)] == [
        slot.index for slot in day_grid(BOUNDS)
    ]
    assert [slot.index for slot in drawn_day_slots(BOUNDS, [])] == [
        slot.index for slot in day_grid(BOUNDS)
    ]
    # A block well inside the day does not narrow it either.
    inside = drawn_day_slots(BOUNDS, [_block(30, slot_index=4)])
    assert [slot.index for slot in inside] == [slot.index for slot in day_grid(BOUNDS)]


def test_pdm1311_a_box_before_midnight_is_refused():
    """PD-M13.11 — PD-M5.8's guarantee, moved off the bound and onto the box.

    "A day is one date" used to be enforced by refusing a new Day Start that
    would cross midnight. Nothing moves Day Start any more, so that guard would
    never fire again -- it is enforced on the box a block would occupy instead.
    Asserted at the boundary from both sides, because an off-by-one here is a
    block silently belonging to yesterday.
    """
    # 08:00 less sixteen boxes is exactly 00:00: the earliest box there is.
    assert slot_is_on_the_date(BOUNDS, -16) is True
    assert slot_is_on_the_date(BOUNDS, -17) is False
    # 08:00 plus 31 boxes ends at 24:00: the latest box there is.
    assert slot_is_on_the_date(BOUNDS, 31) is True
    assert slot_is_on_the_date(BOUNDS, 32) is False
    # A span is counted from its own end, not its start.
    assert slot_is_on_the_date(BOUNDS, 30, 2) is True
    assert slot_is_on_the_date(BOUNDS, 31, 2) is False
