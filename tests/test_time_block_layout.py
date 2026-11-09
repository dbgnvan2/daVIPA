"""TB-M3 — the day-layout arithmetic, proved without a display.

Purpose: hold the item-to-duration rules, the time parsing, the depth bars,
         the priority bands, the weekday gate and the length ceiling to their
         stated behaviour.
Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
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
    DAY_EXTEND_EARLIER,
    DAY_EXTEND_LATER,
    DEFAULT_DAY_START,
    FALLBACK_BLOCK_MINUTES,
    MAX_BLOCK_MINUTES,
    DayBounds,
    DayExtension,
    DaySpan,
    TimeFormatError,
    day_grid,
    default_minutes_for_block_type,
    extended_span,
    depth_bars,
    duration_for_item,
    format_hhmm,
    is_block_day,
    normalize_block_weekdays,
    parse_clock_time,
    parse_hhmm,
    priority_band,
    span_for_blocks,
    template_span,
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
        (102400, "critical"),  # PRI-M2.7: a legacy pre-cap score, not the top
        # of the scale -- 20 x 20 x 16 x 16 now stores as 9999. Rows written
        # before the cap still hold the raw product, and the bands must not
        # re-colour them.
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


# ========== PD-M14.1 — how far the drawn day can be extended =============
#
# These four replace the extended_day_bound tests of PD-M5.8. The limits they
# assert are the same ones -- the first box of a date, and the last box that
# ends at a storable time -- but they are now limits on where a block may go,
# not on a Day Start or Day End the drop is no longer allowed to write.


def test_pdm146_neither_end_can_leave_the_date():
    """PD-M14.6 — the date is the floor and the ceiling, and it refuses rather than clamps.

    A clamped day would make fewer boxes than the item needs, so the block
    would land somewhere other than the end that was dropped on -- or nowhere,
    with the day already lengthened for it.
    """
    early = DayBounds(day_start="00:30")
    first = extended_span(template_span(early), early, DAY_EXTEND_EARLIER, 1)
    assert first is not None
    assert times_for_slot(first.slot_index, 30, early)[0] == "00:00"
    assert extended_span(template_span(early), early, DAY_EXTEND_EARLIER, 2) is None

    midnight = DayBounds(day_start="00:00")
    assert extended_span(template_span(midnight), midnight, DAY_EXTEND_EARLIER, 1) is None

    late = DayBounds(day_end="23:00")
    last = extended_span(template_span(late), late, DAY_EXTEND_LATER, 1)
    assert last is not None
    assert times_for_slot(last.slot_index, 30, late) == ("23:00", "23:30")
    assert extended_span(template_span(late), late, DAY_EXTEND_LATER, 2) is None

    full = DayBounds(day_end="23:30")
    assert extended_span(template_span(full), full, DAY_EXTEND_LATER, 1) is None


def test_pdm146_the_ceiling_is_the_last_box_that_ends_at_a_real_time():
    """23:30, not 24:00: a box running 23:30--24:00 has no storable end time.

    Written because "the day ends at midnight" and "the day's last box ends at
    midnight" are different numbers, and picking the first would offer a box
    whose end time the app refuses to read back.
    """
    bounds = DayBounds(day_end="23:00")
    grown = extended_span(template_span(bounds), bounds, DAY_EXTEND_LATER, 1)

    assert grown is not None
    boxes = day_grid(bounds, grown.span)
    assert boxes[-1].start_time == "23:00", (
        f"the span the function offered ends on these boxes: "
        f"{[slot.start_time for slot in boxes[-3:]]}"
    )
    assert boxes[-1].end_time == "23:30"


def test_pdm141_the_span_grows_at_the_end_that_was_dropped_on():
    """A 90m item needs three boxes, so the drawn day grows by three at that end.

    The hours in Day Settings are untouched -- the function is handed the day
    and hands back a wider one, and it has no way to write a setting.
    """
    bounds = DayBounds()
    drawn = template_span(bounds)

    earlier = extended_span(drawn, bounds, DAY_EXTEND_EARLIER, 3)
    assert earlier is not None
    assert earlier.slot_index == drawn.first - 3
    assert earlier.span == DaySpan(drawn.first - 3, drawn.last)
    assert times_for_slot(earlier.slot_index, 90, bounds)[0] == "06:30"

    later = extended_span(drawn, bounds, DAY_EXTEND_LATER, 3)
    assert later is not None
    assert later.slot_index == drawn.last + 1
    assert later.span == DaySpan(drawn.first, drawn.last + 3)
    assert times_for_slot(later.slot_index, 90, bounds)[1] == "18:30"


def test_pdm141_an_end_of_the_day_that_is_not_one_is_an_error():
    """Not silently treated as one end or the other: a typo would pick a day."""
    with pytest.raises(ValueError):
        extended_span(template_span(DayBounds()), DayBounds(), "sideways", 1)


def test_pdm141_the_extension_carries_the_span_the_block_needs():
    """The returned span holds the whole block, not only its first box.

    An extension that widened by one box and placed a three-box block would
    leave two boxes of it off the end of the grid -- drawn nowhere, and refused
    by the very span the extension produced.
    """
    bounds = DayBounds()
    grown = extended_span(template_span(bounds), bounds, DAY_EXTEND_LATER, 3)

    assert grown is not None
    assert grown.span.holds(grown.slot_index, 3)
    assert isinstance(grown, DayExtension)


# =====================================================================
# PD-M14.2 -- the day is the hours you set, stretched to what is planned
#
# The hours in Day Settings are a template for a blank day and nothing else.
# A block's slot index is counted from that template's Day Start and is
# allowed to be negative, meaning a box before the hours begin. The drawn day
# is derived from the blocks on the date, every read, so there is no second
# copy of the day's shape that can disagree with them.


def _spanned(minutes: int, slot_index=None, label="block") -> TimeBlock:
    """A block with no clock times, because the span is read off the index."""
    return TimeBlock(
        block_date="2026-11-08",
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        slot_index=slot_index,
    )


def test_pdm142_the_template_span_is_the_hours_you_set():
    """Index 0 is the first box of Day Start, and the last is the last whole box."""
    span = template_span(DayBounds(day_start="09:00", day_end="17:00"))

    assert (span.first, span.last) == (0, 15)
    assert span.count == 16
    # 16:45 cannot hold a whole box after 16:30, so the day stops at 16:00.
    assert template_span(DayBounds(day_start="09:00", day_end="16:45")).last == 14


def test_pdm142_a_day_with_no_room_has_no_boxes():
    """A Day End at or before Day Start is answered, not raised on."""
    span = template_span(DayBounds(day_start="09:00", day_end="09:00"))

    assert span.count == 0
    assert not span.holds(0), "a day with no boxes accepted a block in box 0"
    assert day_grid(DayBounds(day_start="09:00", day_end="09:00")) == []


def test_pdm142_a_block_before_the_hours_widens_the_span():
    """PD-M14.2 — the day stretches for what the date holds, at either end."""
    bounds = DayBounds(day_start="09:00", day_end="17:00")

    span = span_for_blocks([_spanned(30, slot_index=-2), _spanned(30, slot_index=17)], bounds)

    assert (span.first, span.last) == (-2, 17)
    boxes = day_grid(bounds, span)
    assert boxes[0].start_time == "08:00"
    assert boxes[-1].start_time == "17:30"


def test_pdm142_nothing_outside_the_hours_leaves_the_span_alone():
    """The common case: the span is the template, so the day is the hours."""
    bounds = DayBounds(day_start="09:00", day_end="17:00")

    span = span_for_blocks([_spanned(30, slot_index=0), _spanned(60, slot_index=14)], bounds)

    assert span == template_span(bounds), (
        "a day inside its own hours was drawn as something other than its hours"
    )


def test_pdm142_a_block_that_was_never_placed_does_not_widen_anything():
    """A NULL slot index is "never placed", and it has no opinion about the day."""
    bounds = DayBounds(day_start="09:00", day_end="17:00")

    span = span_for_blocks([_spanned(30, slot_index=None)], bounds)

    assert span == template_span(bounds)


def test_pdm142_an_absurd_slot_index_does_not_stretch_the_day():
    """Adversarial (P7): an index that reads as ordinary and is off the date.

    The stretch stops at the date, because a day is one date. Without the
    limit one corrupt row would draw a thousand empty boxes, which looks like
    a hung screen rather than like the single bad row it is.
    """
    bounds = DayBounds(day_start="09:00", day_end="17:00")

    span = span_for_blocks(
        [_spanned(30, slot_index=400), _spanned(30, slot_index=-400)], bounds
    )

    assert span == template_span(bounds)


def test_pdm142_a_negative_index_is_not_a_list_position():
    """``position_of``, because ``grid[-1]`` is the end of the day, not its start.

    This is the whole of what makes a signed index safe: Python would answer
    ``grid[-2]`` with the second-to-last box of the day and raise nothing.
    """
    span = DaySpan(-2, 15)

    assert span.position_of(-2) == 0
    assert span.position_of(0) == 2
    assert day_grid(DayBounds(day_start="09:00", day_end="17:00"), span)[
        span.position_of(-1)
    ].start_time == "08:30"


def test_pdm142_the_span_says_what_it_holds_including_a_block_s_length():
    """A 90m block in the last box does not fit, and the span says so."""
    span = DaySpan(0, 15)

    assert span.holds(15, 1)
    assert not span.holds(15, 2), "a two-box block fitted into the last box"
    assert not span.holds(-1, 1), "a box before the day was inside it"
    assert span.holds(0, 16)
