"""TB-M3 — the day-layout arithmetic, proved without a display.

Purpose: hold the item-to-duration rules, the time parsing, the depth bars,
         the priority bands, the weekday gate and the length ceiling to their
         stated behaviour.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
Tests:   this file

These are pure functions on purpose. Day arithmetic should not need a window to
verify — which is also why none of it lives in screens/plan.py.

**The packing tests that used to be the bulk of this file are gone**, with the
functions they covered: a planned day is a fixed grid of half hours now, not an
order to walk from Day Start, so there is nothing to pack. Their successors —
the grid, its refusals, and what happens to a block no box can hold — are in
tests/test_time_grid.py.
"""

from types import SimpleNamespace

import pytest

from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.time_block_layout import (
    DEFAULT_DAY_START,
    FALLBACK_BLOCK_MINUTES,
    MAX_BLOCK_MINUTES,
    DayBounds,
    TimeFormatError,
    default_minutes_for_block_type,
    depth_bars,
    duration_for_item,
    format_hhmm,
    is_block_day,
    normalize_block_weekdays,
    parse_clock_time,
    parse_hhmm,
    priority_band,
    times_for_slot,
    total_planned_minutes,
)

# A day with no lunch, so a test that is not about lunch is not silently
# shaped by it.
NO_LUNCH = DayBounds(day_start="08:00", lunch_minutes=0, day_end="17:00")
# The default working day: 08:00, lunch 12:00-13:00, ends 17:00.
STANDARD = DayBounds()


def _blocks(*minutes, block_date="2026-11-05"):
    """Blocks of the given lengths, with no stored times or boxes."""
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
    """TB-M4.1 — a corrupt stored time still gives the day a usable grid.

    The fallbacks are asserted, and then the grid they produce: bounds that
    read back as defaults but build an empty or mistimed grid would pass the
    first three assertions and leave the user with a day they cannot plan in.
    """
    bounds = DayBounds(day_start="not a time", lunch_start="", day_end="99")

    assert bounds.day_start_minutes == 8 * 60
    assert bounds.lunch_start_minutes == 12 * 60
    assert bounds.day_end_minutes == 17 * 60

    assert times_for_slot(0, 30, bounds) == ("08:00", "08:30")


@pytest.mark.parametrize("bad", ["lots", None, -10])
def test_bad_lunch_length_falls_back_or_clamps(bad):
    bounds = DayBounds(lunch_minutes=bad)

    assert bounds.lunch_length >= 0


# --- TB-M11 : the gap a block was dropped in -------------------------------
#
# These exist because the screen can only measure one thing -- which rendered
# row the pointer is in, with the dragged block still on screen -- and
# move_block counts against a list the block has already been taken out of.
# The two differ by one for a downward move, and getting it wrong is invisible:
# the day reorders, just not to where the user let go.


def test_the_block_length_ceiling_is_a_day():
    """A block cannot be longer than the day it is stored on.

    Not a style preference: format_hhmm clamps at 99:59, so a block long
    enough to push its end past that would be stored with an end_time that is
    not its start plus its duration.
    """
    assert MAX_BLOCK_MINUTES == 24 * 60
    assert format_hhmm(DayBounds().day_start_minutes + MAX_BLOCK_MINUTES) == "32:00"


def test_a_capped_work_block_still_says_start_plus_duration():
    """The reason the cap exists, asserted as the property it protects.

    An item asking for 5000 minutes is capped to a day, and the times the grid
    derives for the capped length still satisfy end == start + duration. Before
    the cap, ``format_hhmm`` clamped the end and the row stopped saying what it
    claimed.

    Through ``times_for_slot`` rather than the retired ``pack_day``: the
    function changed, the property did not.
    """
    minutes = duration_for_item(SimpleNamespace(work_block=5000))
    assert minutes == MAX_BLOCK_MINUTES

    start, end = times_for_slot(0, minutes, NO_LUNCH)

    assert parse_hhmm(end) - parse_hhmm(start) == minutes


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
