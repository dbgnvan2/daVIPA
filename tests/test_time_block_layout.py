"""TB-M3 — the day-layout arithmetic, proved without a display.

Purpose: hold the packing rules, the item-to-duration rules, the depth bars,
         the priority bands and the weekday gate to their stated behaviour.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
Tests:   this file

These are pure functions on purpose. Correct packing is arithmetic, and
arithmetic should not need a window to verify — which is also why none of it
lives in screens/plan.py.
"""

from types import SimpleNamespace

import pytest

from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.time_block_layout import (
    DEFAULT_DAY_START,
    FALLBACK_BLOCK_MINUTES,
    MAX_BLOCK_MINUTES,
    MIN_BLOCK_HEIGHT_PX,
    PIXELS_PER_MINUTE,
    DayBounds,
    TimeFormatError,
    block_height,
    default_minutes_for_block_type,
    depth_bars,
    duration_for_item,
    format_hhmm,
    is_block_day,
    lunch_window,
    move_block,
    move_block_to_gap,
    normalize_block_weekdays,
    pack_day,
    parse_clock_time,
    parse_hhmm,
    priority_band,
    renumber,
    sort_blocks,
    total_planned_minutes,
)

# A day with no lunch, so packing tests that are not about lunch are not
# silently shaped by it.
NO_LUNCH = DayBounds(day_start="08:00", lunch_minutes=0, day_end="17:00")
# The default working day: 08:00, lunch 12:00-13:00, ends 17:00.
STANDARD = DayBounds()


def _blocks(*minutes, block_date="2026-11-05"):
    """Blocks of the given lengths, in position order, with no stored times."""
    return [
        TimeBlock(
            block_date=block_date,
            start_time="",
            end_time="",
            planned_minutes=length,
            position=index,
            label=f"b{index}",
        )
        for index, length in enumerate(minutes, start=1)
    ]


# --- TB-M3.1 : packing ------------------------------------------------------

def test_tbm31_blocks_pack_from_day_start():
    """TB-M3.1 — back to back from the day's start, in the order given."""
    packed = pack_day(_blocks(30, 60, 30), NO_LUNCH)

    assert [(p.start_time, p.end_time) for p in packed] == [
        ("08:00", "08:30"),
        ("08:30", "09:30"),
        ("09:30", "10:00"),
    ]
    assert not any(p.overflows_day_end for p in packed)


def test_tbm31a_packing_leaves_no_gaps_between_blocks():
    """Each block starts exactly where the one before it ended.

    Asserted as a relation across the whole day rather than against a hardcoded
    list, so it still bites if the lengths change.
    """
    packed = pack_day(_blocks(25, 15, 45, 30), NO_LUNCH)

    for earlier, later in zip(packed, packed[1:]):
        assert later.start_minutes == earlier.end_minutes


def test_tbm31b_an_empty_day_packs_to_nothing():
    assert pack_day([], STANDARD) == []


# --- TB-M3.2 : lunch (adversarial, P7) --------------------------------------

def test_tbm32_block_straddling_lunch_moves_after_lunch():
    """TB-M3.2 — adversarial (P7): a block that *looks* like it fits does not.

    Three 60s from 08:00 reach 11:00, so the fourth has a full hour before the
    12:00 lunch and fits exactly. The fifth starts at 12:00 — inside lunch — and
    must move to 13:00.

    The input that "looks right but is wrong" is the sixth case below: a 90 at
    11:00 has an hour of clear day in front of it and still must not start,
    because it would run through lunch. A naive implementation that only checks
    whether the *start* is inside lunch places it at 11:00 and overlaps lunch by
    half an hour.
    """
    packed = pack_day(_blocks(60, 60, 60, 60, 60), STANDARD)

    assert [(p.start_time, p.end_time) for p in packed] == [
        ("08:00", "09:00"),
        ("09:00", "10:00"),
        ("10:00", "11:00"),
        ("11:00", "12:00"),  # fits exactly up to lunch
        ("13:00", "14:00"),  # would start inside lunch, so moves past it
    ]
    assert packed[4].pushed_after_lunch
    assert not packed[3].pushed_after_lunch


def test_tbm32a_a_block_that_would_run_through_lunch_is_moved_whole():
    """The adversarial case: an hour of clear day in front of it, still moved.

    Not split into 11:00-12:00 plus 13:00-13:30. Half an hour of deep work
    before lunch and half an hour after is not the same thing as an hour of it,
    and the planner must not quietly claim otherwise.
    """
    packed = pack_day(_blocks(60, 60, 60, 90), STANDARD)

    straddler = packed[3]
    assert (straddler.start_time, straddler.end_time) == ("13:00", "14:30")
    assert straddler.pushed_after_lunch
    assert straddler.planned_minutes == 90, "the block must not have been split"


def test_tbm32b_a_block_longer_than_the_morning_still_starts_after_lunch():
    """Even the first block of the day moves if it cannot clear lunch.

    08:00 + 5h would run to 13:00, through lunch. There is nowhere before lunch
    it fits, so it goes after — the day starts at 13:00 and the morning is left
    visibly empty rather than the block being cut in two.
    """
    packed = pack_day(_blocks(300), STANDARD)

    assert (packed[0].start_time, packed[0].end_time) == ("13:00", "18:00")
    assert packed[0].pushed_after_lunch
    assert packed[0].overflows_day_end


def test_tbm32c_zero_minute_lunch_means_no_push():
    """A user who sets lunch to 0 minutes gets an unbroken day."""
    packed = pack_day(_blocks(60, 60, 60, 60, 60), NO_LUNCH)

    assert [p.start_time for p in packed] == [
        "08:00", "09:00", "10:00", "11:00", "12:00",
    ]
    assert not any(p.pushed_after_lunch for p in packed)


def test_tbm32d_only_the_first_block_after_lunch_is_marked_pushed():
    """The marker says where to draw the lunch band, so exactly one block carries it."""
    packed = pack_day(_blocks(60, 60, 60, 60, 30, 30), STANDARD)

    assert [p.pushed_after_lunch for p in packed] == [
        False, False, False, False, True, False,
    ]


# --- TB-M3.3 : overflow (real scale, P9) ------------------------------------

def test_tbm33_overflow_blocks_are_flagged_not_dropped():
    """TB-M3.3 — real scale (P9): a day over-filled past its end keeps every block.

    Fourteen hour-long blocks is far more than a 08:00-17:00 day holds, which is
    the point: the cap has to actually bite. Every block comes back, the ones
    past 17:00 are flagged, and nothing is trimmed or refused — over-filling a
    day is the user's business, and the planner's job is to show it (P2).
    """
    packed = pack_day(_blocks(*([60] * 14)), STANDARD)

    assert len(packed) == 14, "no block may be dropped for running past day end"

    overflowing = [p for p in packed if p.overflows_day_end]
    fitting = [p for p in packed if not p.overflows_day_end]

    # 08:00-12:00 is four, lunch, then 13:00-17:00 is four more.
    assert len(fitting) == 8
    assert len(overflowing) == 6
    assert fitting[-1].end_time == "17:00"
    assert overflowing[0].start_time == "17:00"
    # Times stay unique and ordered past midnight rather than wrapping to 01:00.
    assert len({p.start_minutes for p in packed}) == 14
    assert overflowing[-1].end_time == "23:00"


def test_tbm33a_a_block_ending_exactly_at_day_end_does_not_overflow():
    """The boundary is inclusive: 16:30-17:00 is a full day, not an overrun."""
    packed = pack_day(_blocks(240, 240), STANDARD)

    assert packed[-1].end_time == "17:00"
    assert not packed[-1].overflows_day_end


# --- TB-M3.4 : block length from the item -----------------------------------

def test_tbm34_work_block_wins_over_default():
    """TB-M3.4 — requirement 8: use the Work Block value for block length."""
    item = ActionItem(who="me", title="Deep work", work_block=90)

    assert duration_for_item(item, 30) == 90


def test_tbm34a_an_item_without_a_work_block_gets_the_default():
    item = ActionItem(who="me", title="Anything")

    assert duration_for_item(item, 30) == 30
    assert duration_for_item(item) == FALLBACK_BLOCK_MINUTES


@pytest.mark.parametrize("bad", [0, -30, None, "ninety", ""])
def test_tbm34b_an_unusable_work_block_falls_back_rather_than_making_a_zero_block(bad):
    """A hint that cannot be honoured falls back.

    A zero or negative length would render a block the user can neither see nor
    right-click, so the hint is discarded rather than obeyed.
    """
    item = ActionItem(who="me", title="Anything", work_block=bad)

    assert duration_for_item(item, 30) == 30


def test_tbm34c_no_item_at_all_gets_the_default():
    """Buffer and break blocks have no item behind them."""
    assert duration_for_item(None, 45) == 45


# --- TB-M3.5 : depth bars ---------------------------------------------------

@pytest.mark.parametrize(
    "depth, expected",
    [("Deep", 3), ("Medium", 2), ("Shallow", 1), ("deep", 3), ("  SHALLOW  ", 1)],
)
def test_tbm35_depth_words_map_to_bars(depth, expected):
    assert depth_bars(depth) == expected


@pytest.mark.parametrize("unset", [None, "", "   ", "profound", "3"])
def test_tbm35_depth_bars_default_to_one(unset):
    """TB-M3.5 — "Default depth to 1": unset and unrecognised both draw one bar.

    A planner that raised on a hand-edited depth would be worse than one that
    under-reports, so an unknown word is treated as the shallowest.
    """
    assert depth_bars(unset) == 1


# --- TB-M3.6 : the weekday gate ---------------------------------------------

def test_tbm36_unchecked_weekday_is_not_a_block_day():
    """TB-M3.6 — the seven checkboxes gate which days accept blocks.

    2026-11-02 is a Monday and 2026-11-07 a Saturday; the default settings allow
    Monday to Friday.
    """
    assert is_block_day("2026-11-02", STANDARD) is True
    assert is_block_day("2026-11-07", STANDARD) is False


def test_tbm36a_a_weekend_becomes_a_block_day_when_checked():
    weekends_on = DayBounds(block_weekdays=(False,) * 5 + (True, True))

    assert is_block_day("2026-11-07", weekends_on) is True
    assert is_block_day("2026-11-02", weekends_on) is False


def test_tbm36b_an_unparseable_date_is_not_a_block_day():
    """The planner refuses to write blocks somewhere it cannot name.

    Falling back to today would be the dangerous reading: a malformed date would
    silently plan work onto a different day from the one on screen.
    """
    assert is_block_day("not-a-date", STANDARD) is False
    assert is_block_day("", STANDARD) is False
    assert is_block_day(None, STANDARD) is False


@pytest.mark.parametrize(
    "stored, expected",
    [
        (None, (True, True, True, True, True, False, False)),
        ([], (False,) * 7),
        ([True], (True,) + (False,) * 6),
        ([1, 0, 1, 0, 1, 0, 1], (True, False, True, False, True, False, True)),
        ([True] * 10, (True,) * 7),
        # A string is iterable; it must not read as seven enabled days.
        ("nonsense", (True, True, True, True, True, False, False)),
        (42, (True, True, True, True, True, False, False)),
    ],
)
def test_tbm42_weekday_list_is_coerced_to_seven(stored, expected):
    """TB-M4.2 — settings arrive from JSON, where a hand-edit can be any shape.

    Short lists pad with False, long ones truncate, a non-iterable falls back to
    the default. A planner that refused to start over a malformed preference
    would be the worse failure.
    """
    assert normalize_block_weekdays(stored) == expected


# --- time parsing and formatting -------------------------------------------

@pytest.mark.parametrize(
    "text, minutes",
    [("00:00", 0), ("08:00", 480), ("12:30", 750), ("23:59", 1439), (" 9:05 ", 545)],
)
def test_parse_hhmm_reads_a_time(text, minutes):
    assert parse_hhmm(text) == minutes


@pytest.mark.parametrize("bad", ["", None, "nonsense", "12", "12:99", "ab:cd", "-1:00"])
def test_parse_hhmm_falls_back_when_given_a_default(bad):
    """A corrupt settings value falls back rather than stopping the planner."""
    assert parse_hhmm(bad, default="08:00") == 480


@pytest.mark.parametrize("bad", ["", None, "nonsense", "12", "12:99"])
def test_parse_hhmm_raises_when_no_default_is_offered(bad):
    """The settings dialog wants the error, so it can name the wrong field."""
    with pytest.raises(TimeFormatError):
        parse_hhmm(bad)


def test_format_hhmm_counts_past_midnight_rather_than_wrapping():
    """A day packed past midnight keeps counting, so times stay ordered.

    Wrapping 25:00 to 01:00 would make an over-filled day sort before its own
    morning.
    """
    assert format_hhmm(0) == "00:00"
    assert format_hhmm(1439) == "23:59"
    assert format_hhmm(25 * 60) == "25:00"


def test_format_hhmm_clamps_rather_than_widening_the_field():
    assert format_hhmm(10 ** 9) == "99:59"
    assert format_hhmm(-5) == "00:00"


# --- ordering helpers -------------------------------------------------------

def test_sort_blocks_orders_by_position_then_stored_time():
    """Position first; stored time only breaks ties, which is what carries legacy rows."""
    legacy_late = TimeBlock(
        block_date="2026-11-05", start_time="15:00", end_time="15:30",
        planned_minutes=30, position=0, label="legacy-late",
    )
    legacy_early = TimeBlock(
        block_date="2026-11-05", start_time="09:00", end_time="09:30",
        planned_minutes=30, position=0, label="legacy-early",
    )
    positioned = TimeBlock(
        block_date="2026-11-05", start_time="07:00", end_time="07:30",
        planned_minutes=30, position=1, label="positioned",
    )

    ordered = sort_blocks([legacy_late, positioned, legacy_early])

    assert [b.label for b in ordered] == ["legacy-early", "legacy-late", "positioned"]


def test_renumber_stamps_one_based_positions():
    """Positions start at 1, because 0 is reserved for un-renumbered legacy rows."""
    blocks = _blocks(30, 30, 30)
    for block in blocks:
        block.position = 0

    renumber(blocks)

    assert [b.position for b in blocks] == [1, 2, 3]


@pytest.mark.parametrize(
    "block_id, target, expected",
    [
        ("c", 0, ["c", "a", "b"]),
        ("a", 2, ["b", "c", "a"]),
        ("a", 99, ["b", "c", "a"]),
        ("b", -4, ["b", "a", "c"]),
        ("b", 1, ["a", "b", "c"]),
    ],
)
def test_move_block_places_an_id_at_the_target_index(block_id, target, expected):
    assert move_block(["a", "b", "c"], block_id, target) == expected


def test_move_block_ignores_an_id_that_is_no_longer_there():
    """A drag of something already deleted must not resurrect it."""
    assert move_block(["a", "b"], "gone", 0) == ["a", "b"]


# --- small helpers the screen leans on --------------------------------------

def test_total_planned_minutes_counts_buffers_and_breaks_too():
    blocks = _blocks(30, 60)
    blocks.append(
        TimeBlock(
            block_date="2026-11-05", start_time="", end_time="",
            planned_minutes=5, block_type=BlockType.BREAK,
        )
    )

    assert total_planned_minutes(blocks) == 95


def test_lunch_window_is_none_when_lunch_is_zero():
    assert lunch_window(STANDARD) == ("12:00", "13:00")
    assert lunch_window(NO_LUNCH) is None


class _Settings:
    default_time_block_minutes = 30
    default_break_minutes = 5


def test_default_minutes_for_block_type_reuses_the_existing_break_length():
    """A break takes the user's existing break preference, not a second one meaning the same."""
    settings = _Settings()

    assert default_minutes_for_block_type(BlockType.BREAK, settings) == 5
    assert default_minutes_for_block_type(BlockType.BUFFER, settings) == 30
    assert default_minutes_for_block_type(BlockType.ITEM, settings) == 30


def test_default_minutes_for_block_type_works_without_settings():
    assert default_minutes_for_block_type(BlockType.BUFFER) == FALLBACK_BLOCK_MINUTES
    assert default_minutes_for_block_type(BlockType.BREAK) == 5


# --- priority bands ---------------------------------------------------------

@pytest.mark.parametrize(
    "score, band",
    [
        (102400, "critical"),  # 20 x 20 x 16 x 16, the top of the scale
        (2000, "critical"),
        (1999, "high"),
        (500, "high"),
        (499, "medium"),
        (100, "medium"),
        (99, "low"),
        (4, "low"),            # 1 x 1 x 2 x 2, the lowest real score
        (1, "low"),
    ],
)
def test_priority_band_thresholds(score, band):
    assert priority_band(score) == band


@pytest.mark.parametrize("missing", [0, None, -5, "", "high"])
def test_priority_band_calls_an_unscored_item_unscored(missing):
    """An item missing one of its four factors scores 0 — absence, not low priority.

    calculate_priority_score returns 0 if any factor is 0 or None, so a 0 means
    the user has not finished scoring the item. Painting it the same colour as a
    genuinely low-priority item would invent data they never entered.
    """
    assert priority_band(missing) == "unscored"


# --- DayBounds --------------------------------------------------------------

def test_day_bounds_reads_an_app_settings_object():
    class Settings:
        plan_day_start = "07:30"
        plan_lunch_start = "11:45"
        plan_lunch_minutes = 45
        plan_day_end = "16:15"
        plan_block_weekdays = [True, True, True, True, True, True, False]
        default_time_block_minutes = 25

    bounds = DayBounds.from_settings(Settings())

    assert bounds.day_start_minutes == 7 * 60 + 30
    assert bounds.lunch_start_minutes == 11 * 60 + 45
    assert bounds.lunch_end_minutes == 12 * 60 + 30
    assert bounds.day_end_minutes == 16 * 60 + 15
    assert bounds.block_weekdays == (True, True, True, True, True, True, False)
    assert bounds.default_block_minutes == 25


def test_day_bounds_tolerates_a_settings_object_from_an_older_build():
    """Missing attributes fall back; a planner must not die of an AttributeError."""
    class Bare:
        pass

    bounds = DayBounds.from_settings(Bare())

    assert bounds.day_start == DEFAULT_DAY_START
    assert bounds.day_end_minutes == 17 * 60


def test_tbm41_bad_time_in_bounds_falls_back_to_the_default():
    """TB-M4.1 — a corrupt stored time does not stop the day being packed."""
    bounds = DayBounds(day_start="not a time", lunch_start="", day_end="99")

    assert bounds.day_start_minutes == 8 * 60
    assert bounds.lunch_start_minutes == 12 * 60
    assert bounds.day_end_minutes == 17 * 60

    packed = pack_day(_blocks(30), bounds)
    assert packed[0].start_time == "08:00"


@pytest.mark.parametrize("bad", ["lots", None, -10])
def test_bad_lunch_length_falls_back_or_clamps(bad):
    bounds = DayBounds(lunch_minutes=bad)

    assert bounds.lunch_length >= 0


def test_block_height_is_proportional_to_minutes():
    """A 90 is three times a 30, exactly, so the day reads as a bar chart.

    Asserted as a ratio and not just as pixel values: the constant may be
    retuned, and what must survive the retune is that a block twice as long is
    twice as tall.
    """
    assert block_height(90) == 3 * block_height(30)
    assert block_height(60) == 2 * block_height(30)
    assert block_height(30) == round(30 * PIXELS_PER_MINUTE)


def test_a_very_short_block_stops_shrinking_at_the_floor():
    """Proportionality is given up below the floor, on purpose.

    A 5-minute block at the raw rate would be 6 pixels tall -- too small to
    read or right-click, so a user could create a block they then could not
    resize or delete.
    """
    assert block_height(5) == MIN_BLOCK_HEIGHT_PX
    assert block_height(1) == MIN_BLOCK_HEIGHT_PX
    # The floor must not be so high that it flattens a real length.
    assert block_height(FALLBACK_BLOCK_MINUTES) > MIN_BLOCK_HEIGHT_PX


@pytest.mark.parametrize("minutes", [None, 0, -30, "nonsense"])
def test_an_unusable_length_falls_back_rather_than_vanishing(minutes):
    """A block with no readable length still gets a visible, clickable row.

    Zero or None would otherwise render a frame of no height: the block is in
    the database, the user cannot see it, and the day's times no longer add up.
    """
    assert block_height(minutes) == block_height(FALLBACK_BLOCK_MINUTES)


# --- TB-M11 : the gap a block was dropped in -------------------------------
#
# These exist because the screen can only measure one thing -- which rendered
# row the pointer is in, with the dragged block still on screen -- and
# move_block counts against a list the block has already been taken out of.
# The two differ by one for a downward move, and getting it wrong is invisible:
# the day reorders, just not to where the user let go.


def test_a_downward_drop_lands_in_the_gap_it_was_dropped_in():
    """Dragging the first block into the gap before the third puts it second.

    The regression this names: the rendered gap index was passed straight to
    move_block, which removes the block before inserting, so the result was
    ['B', 'C', 'A'] -- one place too far, for every downward drag.
    """
    assert move_block_to_gap(["A", "B", "C"], "A", 2) == ["B", "A", "C"]
    assert move_block_to_gap(["A", "B", "C", "D"], "A", 3) == ["B", "C", "A", "D"]


def test_a_drop_in_a_block_s_own_gap_changes_nothing():
    """Releasing a block where it already is must not reorder the day.

    Both gaps that bound a block are its own: the one above it and the one
    below. A small drag inside its own row is a mis-click, not an instruction,
    and the old arithmetic turned the lower one into a move past its neighbour.
    """
    for gap in (0, 1):
        assert move_block_to_gap(["A", "B", "C"], "A", gap) == ["A", "B", "C"]
    for gap in (1, 2):
        assert move_block_to_gap(["A", "B", "C"], "B", gap) == ["A", "B", "C"]


def test_an_upward_drop_lands_in_the_gap_it_was_dropped_in():
    """The direction that already worked, kept working."""
    assert move_block_to_gap(["A", "B", "C"], "C", 0) == ["C", "A", "B"]
    assert move_block_to_gap(["A", "B", "C"], "C", 1) == ["A", "C", "B"]


def test_every_gap_in_a_four_block_day_is_reachable():
    """Each of the four gaps puts the dragged block somewhere different.

    An exhaustive check rather than a sampled one: an off-by-one makes two
    adjacent gaps produce the same order, and the set below is what proves
    they do not.
    """
    order = ["A", "B", "C", "D"]
    results = [tuple(move_block_to_gap(order, "B", gap)) for gap in range(5)]
    assert results == [
        ("B", "A", "C", "D"),
        ("A", "B", "C", "D"),
        ("A", "B", "C", "D"),
        ("A", "C", "B", "D"),
        ("A", "C", "D", "B"),
    ]


def test_a_gap_index_past_the_end_puts_the_block_last():
    """A release below the last block is a move to the end, not an error."""
    assert move_block_to_gap(["A", "B", "C"], "A", 99) == ["B", "C", "A"]


def test_a_block_that_is_no_longer_there_is_not_resurrected():
    """A stale drag must not add an id the day no longer holds."""
    assert move_block_to_gap(["A", "B"], "GONE", 0) == ["A", "B"]


def test_the_block_length_ceiling_is_a_day():
    """A block cannot be longer than the day it is stored on.

    Not a style preference: format_hhmm clamps at 99:59, so a block long
    enough to push its end past that would be stored with an end_time that is
    not its start plus its duration.
    """
    assert MAX_BLOCK_MINUTES == 24 * 60
    assert format_hhmm(DayBounds().day_start_minutes + MAX_BLOCK_MINUTES) == "32:00"



# --- found by the pre-push sweep: the ceiling has two ways in ---------------


@pytest.mark.parametrize("work_block", [MAX_BLOCK_MINUTES + 1, 5000, 10**6])
def test_a_work_block_longer_than_a_day_is_capped(work_block):
    """The Work Block hint goes through the same ceiling as a typed length.

    The dialog that asks a human for a length refuses anything over a day. The
    other way in asks nobody: a block takes its length from the item's Work
    Block, which the item editor stores as any integer typed into it. Past the
    ceiling format_hhmm clamps the end time, so the row stops saying start +
    duration.
    """
    item = SimpleNamespace(work_block=work_block)

    assert duration_for_item(item) == MAX_BLOCK_MINUTES


def test_a_capped_work_block_still_gives_a_row_that_says_start_plus_duration():
    """The reason the cap exists, asserted as the property it protects."""
    item = SimpleNamespace(work_block=5000)
    minutes = duration_for_item(item)
    bounds = DayBounds()
    block = SimpleNamespace(
        id="b1",
        planned_minutes=minutes,
        position=1,
        block_type="item",
        start_time="",
    )

    packed = pack_day([block], bounds)[0]

    assert parse_hhmm(packed.end_time) - parse_hhmm(packed.start_time) == minutes


@pytest.mark.parametrize("stored", [5000, MAX_BLOCK_MINUTES + 1])
def test_a_default_block_length_longer_than_a_day_is_capped(stored):
    """A hand-edited settings file is the other way past the dialog."""
    settings = SimpleNamespace(
        default_time_block_minutes=stored, default_break_minutes=stored
    )

    assert default_minutes_for_block_type("buffer", settings) == MAX_BLOCK_MINUTES
    assert default_minutes_for_block_type("break", settings) == MAX_BLOCK_MINUTES


@pytest.mark.parametrize("text", ["24:00", "25:00", "99:59", "170:0"])
def test_a_clock_time_past_midnight_is_refused(text):
    """A day bound is a point on one clock face.

    parse_hhmm accepts an hour past 23 on purpose, because format_hhmm writes
    one -- an overrunning block's end_time is "25:30" and sort_blocks has to
    read it back. A Day End of 25:00, though, is past every block, so the
    overrun warning that is Day End's only job could never fire again. And
    "170:0" came back from format_hhmm as "99:59": a value the user never
    typed, stored under their hands.
    """
    with pytest.raises(TimeFormatError):
        parse_clock_time(text)


@pytest.mark.parametrize(
    "text,minutes", [("00:00", 0), ("09:05", 545), ("23:59", 1439)]
)
def test_a_clock_time_within_the_day_is_read(text, minutes):
    """The strict parser is still a parser.

    Paired with the test above so a guard that refused everything would not
    pass for the right reason.
    """
    assert parse_clock_time(text) == minutes
