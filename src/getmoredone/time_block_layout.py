"""Day-layout arithmetic for the time block planner.

Purpose: turn an ordered list of blocks plus a day's bounds into clock times,
         and answer the small questions the planner asks about an item (how
         long a block for it should be, how deep it is, which band its
         priority falls in, whether a date may hold blocks at all).
Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
Tests:   tests/test_time_block_layout.py

**This module imports no GUI toolkit, and must not.** Correct packing is
arithmetic, and arithmetic should not need a display to verify -- every rule in
here is provable headless, which is the whole reason it does not live in
screens/plan.py.

The model: a planned day is an *order*, not a set of appointments. The user
drags blocks into the order they want to work them; the clock times fall out of
that order, the block lengths, and the day's bounds. Nothing in the UI lets a
block be dragged to 10:17 -- so nothing in here tries to honour such a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, List, Optional, Sequence, Tuple

from .models import ActionItem, BlockType, SchedulingOptions, TimeBlock

# A day is described by four times and seven weekday flags. The defaults here
# match AppSettings' defaults and exist so a caller with no settings in hand
# (a test, a migration) still gets a sane day rather than a crash.
DEFAULT_DAY_START = "08:00"
DEFAULT_LUNCH_START = "12:00"
DEFAULT_LUNCH_MINUTES = 60
DEFAULT_DAY_END = "17:00"
DEFAULT_BLOCK_WEEKDAYS: Tuple[bool, ...] = (True, True, True, True, True, False, False)

# The duration offered when nothing else says otherwise (requirement 4:
# "default to 30 minutes"). AppSettings.default_time_block_minutes overrides it.
FALLBACK_BLOCK_MINUTES = 30

# Durations offered on the block context menu.
DURATION_CHOICES = (15, 30, 45, 60, 90)

MINUTES_PER_DAY = 24 * 60

# The longest block the planner will store. A day is the natural ceiling, and
# there has to be one: format_hhmm clamps at 99:59, so a block long enough to
# push its end past that would be stored with an end_time that is not its start
# plus its duration -- a row that lies about itself to every later reader.
MAX_BLOCK_MINUTES = MINUTES_PER_DAY

# Depth is stored as a word on the action item; the planner draws it as a stack
# of three bars. An item with no depth set draws one bar -- "default depth to 1"
# -- which is also what an unrecognised word gets, because a planner that
# raised on a hand-edited database would be worse than one that under-reports.
DEPTH_BARS = {"deep": 3, "medium": 2, "shallow": 1}
DEFAULT_DEPTH_BARS = 1
MAX_DEPTH_BARS = 3

# priority_score is the *product* of importance x urgency x size x value,
# so it runs 4 .. 9999 -- not 1 .. 10. PRI-M2 capped it at
# PriorityFactors.MAX_SCORE; before that the product ran to 102400
# (20 x 20 x 16 x 16), and rows written then still hold the raw number, so
# these thresholds have to keep classifying scores above the cap. Bands are
# thresholds on that product, lowest bound first match wins from the top.
# No screen draws these bands since PBG-M5 (2026-11-12) and their three colour
# tables are deleted. The thresholds stay because they are what the score's cap
# is measured against -- ``test_priority_floor_and_cap`` reads the top one.
PRIORITY_BANDS: Tuple[Tuple[int, str], ...] = (
    (2000, "critical"),
    (500, "high"),
    (100, "medium"),
    (1, "low"),
)
# ``UNSCORED_BAND = "unscored"`` was here; ``priority_band`` was its only
# reader and went with the band scheme (PBG-M5).

# Minutes past midnight are the source of truth; HH:MM is for storage and
# display. A day packed past midnight keeps counting (25:00, not 01:00) so the
# strings stay ordered and unique, and is clamped here only to keep the field
# two digits wide. Any block at the clamp is already flagged as overflowing.
MAX_FORMATTED_MINUTES = 99 * 60 + 59


class TimeFormatError(ValueError):
    """Raised when a string is not a usable HH:MM time."""


def parse_hhmm(value: Optional[str], *, default: Optional[str] = None) -> int:
    """Minutes past midnight for an ``HH:MM`` string.

    ``default`` makes this total: a corrupt settings file or a hand-edited
    database row falls back rather than stopping the planner. With no default,
    a bad value raises ``TimeFormatError`` -- which is what the settings dialog
    wants, so it can say which field is wrong instead of silently substituting.
    """
    text = (value or "").strip()
    try:
        if ":" not in text:
            raise TimeFormatError(f"not a HH:MM time: {value!r}")
        hours_text, _, minutes_text = text.partition(":")
        hours = int(hours_text)
        minutes = int(minutes_text)
        if hours < 0 or minutes < 0 or minutes > 59:
            raise TimeFormatError(f"not a HH:MM time: {value!r}")
        return hours * 60 + minutes
    except (TimeFormatError, ValueError):
        if default is None:
            raise TimeFormatError(f"not a HH:MM time: {value!r}") from None
        return parse_hhmm(default)


def parse_clock_time(value: Optional[str], *, default: Optional[str] = None) -> int:
    """Minutes past midnight for a time that has to be a time *of day*.

    Spec:  docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
    Tests: tests/test_time_block_layout.py::test_a_clock_time_past_midnight_is_refused

    ``parse_hhmm`` deliberately accepts an hour past 23, because
    ``format_hhmm`` can write one and a hand-edited or legacy row may hold one;
    reading such a row has to be possible, if only so ``slot_index_for_time``
    can decide it belongs nowhere on the grid. A day *bound* is a different
    thing -- a point on one clock face. Accepting ``25:00`` as a Day End puts
    the end of the day beyond any box, so the grid would have no last box and
    every placement would be legal.

    ``default`` makes this total, for the same reason ``parse_hhmm`` has one and
    for one more. The settings dialog wants the raise, so it can name the field
    rather than substitute a value. The *read* path cannot raise -- a settings
    file must not stop the app from starting -- but it still has to be bounded,
    because a file written before this check existed can hold ``25:00`` today.
    Guarding only the keyboard would heal new input and leave that file saying
    the day ends at 25:00 forever, with the overrun warning silently off.
    """
    try:
        minutes = parse_hhmm(value)
        if minutes >= MINUTES_PER_DAY:
            raise TimeFormatError(f"not a time of day: {value!r}")
        return minutes
    except TimeFormatError:
        if default is None:
            raise TimeFormatError(f"not a time of day: {value!r}") from None
        return parse_clock_time(default)


def format_hhmm(minutes: int) -> str:
    """``HH:MM`` for minutes past midnight, counting past 24h rather than wrapping."""
    clamped = max(0, min(int(minutes), MAX_FORMATTED_MINUTES))
    return f"{clamped // 60:02d}:{clamped % 60:02d}"


@dataclass(frozen=True)
class DayBounds:
    """The shape of a planning day: when it starts, when lunch is, when it ends.

    Spec:  docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
    Tests: tests/test_time_grid.py::test_tgm11_grid_covers_the_day_in_half_hours

    Frozen, and built through ``from_settings``, so a screen cannot drift the
    day's shape halfway through packing it.
    """

    day_start: str = DEFAULT_DAY_START
    lunch_start: str = DEFAULT_LUNCH_START
    lunch_minutes: int = DEFAULT_LUNCH_MINUTES
    day_end: str = DEFAULT_DAY_END
    block_weekdays: Tuple[bool, ...] = DEFAULT_BLOCK_WEEKDAYS
    default_block_minutes: int = FALLBACK_BLOCK_MINUTES

    @classmethod
    def from_settings(cls, settings) -> "DayBounds":
        """Read a ``DayBounds`` off an AppSettings-like object.

        Every field is read through ``getattr`` with the default, so a settings
        object from an older build -- or a stub in a test -- still yields a
        usable day instead of an AttributeError.
        """
        return cls(
            day_start=getattr(settings, "plan_day_start", DEFAULT_DAY_START),
            lunch_start=getattr(settings, "plan_lunch_start", DEFAULT_LUNCH_START),
            lunch_minutes=getattr(settings, "plan_lunch_minutes", DEFAULT_LUNCH_MINUTES),
            day_end=getattr(settings, "plan_day_end", DEFAULT_DAY_END),
            block_weekdays=normalize_block_weekdays(
                getattr(settings, "plan_block_weekdays", None)
            ),
            default_block_minutes=getattr(
                settings, "default_time_block_minutes", FALLBACK_BLOCK_MINUTES
            ),
        )

    # -- derived minute values, each tolerant of a corrupt stored string -----

    @property
    def day_start_minutes(self) -> int:
        return parse_clock_time(self.day_start, default=DEFAULT_DAY_START)

    @property
    def day_end_minutes(self) -> int:
        return parse_clock_time(self.day_end, default=DEFAULT_DAY_END)

    @property
    def lunch_start_minutes(self) -> int:
        return parse_clock_time(self.lunch_start, default=DEFAULT_LUNCH_START)

    @property
    def lunch_length(self) -> int:
        try:
            return max(0, int(self.lunch_minutes))
        except (TypeError, ValueError):
            return DEFAULT_LUNCH_MINUTES

    @property
    def lunch_end_minutes(self) -> int:
        return self.lunch_start_minutes + self.lunch_length


def normalize_block_weekdays(value) -> Tuple[bool, ...]:
    """Coerce any stored value to exactly seven booleans, Monday first.

    Settings arrive from JSON, where this is a list that a hand-edit can make
    any length or fill with anything. Short lists are padded with False and long
    ones truncated, because a planner that refused to start over a malformed
    preference would be the worse failure.
    """
    if value is None:
        return DEFAULT_BLOCK_WEEKDAYS
    # A string is iterable, so without this a stored "nonsense" would read as
    # seven enabled days -- an accident of iterability, not a preference.
    if isinstance(value, (str, bytes)):
        return DEFAULT_BLOCK_WEEKDAYS
    try:
        flags = [bool(flag) for flag in value][:7]
    except TypeError:
        return DEFAULT_BLOCK_WEEKDAYS
    while len(flags) < 7:
        flags.append(False)
    return tuple(flags)


def is_block_day(day: str | date, bounds: DayBounds) -> bool:
    """Whether this date's weekday is one the user allows blocks on.

    An unparseable date is not a block day: the planner refuses to write blocks
    somewhere it cannot name, rather than guessing at today.
    """
    weekday = _weekday_of(day)
    if weekday is None:
        return False
    flags = normalize_block_weekdays(bounds.block_weekdays)
    return flags[weekday]


def _weekday_of(day: str | date) -> Optional[int]:
    """Monday=0 .. Sunday=6, or None if the value is not a date."""
    if isinstance(day, datetime):
        return day.weekday()
    if isinstance(day, date):
        return day.weekday()
    try:
        return datetime.strptime(str(day).strip(), "%Y-%m-%d").weekday()
    except (ValueError, TypeError):
        return None


def weekday_names() -> Tuple[str, ...]:
    """Monday-first weekday labels for the settings checkboxes."""
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def duration_for_item(item: Optional[ActionItem], default_minutes: int = FALLBACK_BLOCK_MINUTES) -> int:
    """How long a block for this item should be.

    Requirement 8: "Use Work Block value for block length if present." The
    item's ``work_block`` wins; otherwise the caller's default (which the
    planner takes from AppSettings.default_time_block_minutes, 30).

    A non-positive or unparseable work_block is treated as absent -- it is a
    hint, and a hint that cannot be honoured should fall back rather than
    produce a zero-length block that the user cannot see or click.
    """
    fallback = clamp_block_minutes(
        _positive_int(default_minutes, FALLBACK_BLOCK_MINUTES)
    )
    if item is None:
        return fallback
    work_block = _positive_int(getattr(item, "work_block", None), 0)
    return clamp_block_minutes(work_block) if work_block else fallback


def clamp_block_minutes(minutes: int) -> int:
    """A block length brought inside the day-long ceiling.

    Spec:  docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m8
    Tests: tests/test_time_block_layout.py::test_a_work_block_longer_than_a_day_is_capped

    The ceiling is enforced here rather than at the one dialog that asks a
    human for a length, because the other way in does not ask anybody: a block
    takes its length from the item's Work Block, which the item editor accepts
    as any typed integer. Past the ceiling ``format_hhmm`` clamps the end time,
    so the row stops saying start + duration and starts lying about itself to
    every later reader. Clamped rather than refused, because there is nobody to
    refuse to at this depth -- the caller that has a user reports the change.
    """
    return min(_positive_int(minutes, FALLBACK_BLOCK_MINUTES), MAX_BLOCK_MINUTES)


def _positive_int(value, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


def depth_bars(depth: Optional[str]) -> int:
    """How many of the three bars to fill for this depth.

    Deep=3, Medium=2, Shallow=1, and 1 for unset or unrecognised -- requirement
    8's "Default depth to 1".
    """
    return DEPTH_BARS.get((depth or "").strip().lower(), DEFAULT_DEPTH_BARS)


# PBG-M5 -- ``priority_band`` was here: ``priority_score`` bucketed into
# critical/high/medium/low/unscored. Its three colour tables are gone with it
# (see ``theme.py``), and nothing else read the bucket.


def total_planned_minutes(blocks: Iterable[TimeBlock]) -> int:
    """Minutes committed on a day, buffers and breaks included."""
    return sum(
        _positive_int(getattr(block, "planned_minutes", None), 0)
        for block in blocks
    )


# ``PIXELS_PER_MINUTE``, ``MIN_BLOCK_HEIGHT_PX``, ``block_height`` and
# ``lunch_window`` were here. A row's height encoded its block's length when a
# row *was* a block; a box is half an hour whatever is in it, and its height
# comes from how many tasks share it (``plan_blocks.slot_row_height``). Lunch
# is a marked box in the grid, so the separate band those fed is gone too.


def default_minutes_for_block_type(block_type: str, settings=None) -> int:
    """The length a newly added buffer or break block gets.

    Breaks take the user's existing break length (AppSettings.default_break_minutes,
    5) rather than a second preference meaning the same thing. Buffers take the
    default block length.
    """
    normalized = BlockType.normalize(block_type)
    if normalized == BlockType.BREAK:
        return clamp_block_minutes(
            _positive_int(getattr(settings, "default_break_minutes", None), 5)
        )
    return clamp_block_minutes(
        _positive_int(
            getattr(settings, "default_time_block_minutes", None), FALLBACK_BLOCK_MINUTES
        )
    )


# =========================================================================
# The 30-minute grid (TG-M1, TG-M2, TG-M3)
#
# A planned day is a fixed grid of half hours, not an order. Every slot from
# Day Start to Day End exists whether or not anything sits in it, and a block
# is placed on the slot the user drops it on. Gaps are legitimate: an empty
# 09:00 between two filled slots is a day someone planned that way, not a
# state to be packed away.
#
# Spec: docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#m1
# =========================================================================

SLOT_MINUTES = 30

# What a slot row can draw legibly, not a rule about how people work. A box is
# worth 30 minutes however many tasks share it, so there is no arithmetic
# reason for a ceiling -- past about four titles the row stops being readable,
# which is the only reason this number exists. Promoted to a named constant
# rather than buried in the check (P4), so the day it needs changing it is one
# edit and the reason is written down beside it.
MAX_BLOCKS_PER_SLOT = 4


class SlotRefusedError(Exception):
    """A placement the grid does not allow, carrying which rule said no.

    Raised rather than returned by the database writes, because by then the
    caller has asked for something specific and "it did not happen" has to be
    impossible to ignore. ``reason`` is a ``SlotRefusal`` value, so one screen
    string per rule rather than one string for every refusal.
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class SlotRefusal:
    """Why a placement was refused, as named values rather than a bare False.

    Four call sites report these, and a refusal worded four ways reads to a
    user as four different bugs -- the lesson ``DAY_TOO_FULL`` taught the
    previous model. The screen maps each to one sentence.
    """

    OUTSIDE_GRID = "outside_grid"
    CROSSES_LUNCH = "crosses_lunch"
    SLOT_FULL = "slot_full"


@dataclass(frozen=True)
class Slot:
    """One half hour of a planned day."""

    index: int
    start_minutes: int
    is_lunch: bool

    @property
    def end_minutes(self) -> int:
        return self.start_minutes + SLOT_MINUTES

    @property
    def start_time(self) -> str:
        return format_hhmm(self.start_minutes)

    @property
    def end_time(self) -> str:
        return format_hhmm(self.end_minutes)


@dataclass(frozen=True)
class DaySpan:
    """The inclusive range of boxes a day draws, counted from Day Start.

    Purpose: PD-M14.2 -- index 0 is the first box of the hours in Day
             Settings, and a **negative** index is a box before them. A day is
             the hours you set, stretched to cover whatever that date actually
             holds, so the stretch is a property of the date's blocks and not
             of the settings file. Nothing about it is stored, which is why it
             cannot go stale (P6) and why taking the blocks away restores the
             hours with no code at all (PD-M14.3).
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-2
    Tests:   tests/test_time_block_layout.py::test_pdm142_the_template_span_is_the_hours_you_set
             tests/test_time_block_layout.py::test_pdm142_a_block_before_the_hours_widens_the_span

    ``last`` below ``first`` means a day with no boxes -- a Day End at or
    before Day Start -- which every method here answers for rather than
    raising, because a day's shape is read off a settings file.
    """

    first: int
    last: int

    @property
    def count(self) -> int:
        return max(0, self.last - self.first + 1)

    def holds(self, slot_index: int, span: int = 1) -> bool:
        """Whether a block of ``span`` boxes starting here is inside the day."""
        span = max(1, int(span))
        return self.first <= slot_index and slot_index + span - 1 <= self.last

    def position_of(self, slot_index: int) -> int:
        """Where this slot index sits in a list built over this span.

        A signed slot index is not a list position: with a first index of -2,
        box -2 is element 0. Every lookup goes through here, because a bare
        ``grid[slot_index]`` on a negative index silently reads from the end
        of the list instead -- an off-by-the-whole-day with no error.
        """
        return slot_index - self.first

    def widened_to(self, slot_index: int, span: int = 1) -> "DaySpan":
        span = max(1, int(span))
        return DaySpan(
            min(self.first, slot_index), max(self.last, slot_index + span - 1)
        )


def template_span(bounds: DayBounds) -> DaySpan:
    """The boxes the hours in Day Settings offer, and nothing more.

    Purpose: PD-M14.5 -- what AutoLoad and the break button are allowed to
             fill. Only a drag onto one of the two ends goes outside it.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-5
    Tests:   tests/test_time_block_layout.py::test_pdm142_the_template_span_is_the_hours_you_set
    """
    room = bounds.day_end_minutes - bounds.day_start_minutes
    return DaySpan(0, room // SLOT_MINUTES - 1)


def _stays_inside_the_date(slot_index: int, span: int, bounds: DayBounds) -> bool:
    """Whether a block at this index is still on the date it belongs to.

    A day is one date. A stored slot index far outside the day -- a corrupt
    row, or one written against a day shape that no longer exists -- must not
    stretch the drawn day to reach it: ``build_day_grid`` surfaces it in the
    "outside the day" group instead, which is where a block the grid cannot
    hold has always gone (P2).
    """
    start = bounds.day_start_minutes + slot_index * SLOT_MINUTES
    end = start + max(1, int(span)) * SLOT_MINUTES
    return (
        start >= 0
        and start <= LAST_DAY_END_MINUTES - SLOT_MINUTES
        and end <= LAST_DAY_END_MINUTES
    )


def span_for_blocks(blocks: Iterable[TimeBlock], bounds: DayBounds) -> DaySpan:
    """The hours you set, stretched to cover what this date holds.

    Purpose: PD-M14.2 -- the day on screen. Derived on every read from the
             blocks themselves, so there is no second copy of the day's shape
             to disagree with them.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-2
    Tests:   tests/test_time_block_layout.py::test_pdm142_a_block_before_the_hours_widens_the_span
             tests/test_time_block_layout.py::test_pdm142_an_absurd_slot_index_does_not_stretch_the_day
    """
    span = template_span(bounds)
    for block in blocks:
        start = _slot_index_of(block)
        if start is None:
            continue
        length = slot_span_of(block)
        if not _stays_inside_the_date(start, length, bounds):
            continue
        span = span.widened_to(start, length)
    return span


def lunch_window(
    blocks: Iterable[TimeBlock], bounds: DayBounds, ignoring: Optional[str] = None
) -> Optional[Tuple[int, int]]:
    """The minutes lunch covers on this date, or ``None`` for the settings'.

    Purpose: PF-M8 -- a day's lunch can be moved. When that happens the date
             carries a ``LUNCH`` block, and that block *is* the lunch: Day
             Settings' hour describes a normal day, exactly as its Day Start and
             Day End do, and a day that moved its lunch must not be shaded in
             two places.
    Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m8
    Tests:   tests/test_plan_screen.py::test_pfm81_a_lunch_block_moves_the_lunch_for_that_date

    ``None`` rather than the settings' window, so the caller can tell "this date
    has its own lunch" from "this date has the same lunch the settings name" --
    the two produce the same grid and different behaviour on the next move.

    ``ignoring`` drops one block from the read: the lunch block being moved must
    not count itself as the lunch where it is leaving.
    """
    for block in blocks:
        if ignoring is not None and getattr(block, "id", None) == ignoring:
            continue
        if BlockType.normalize(block.block_type) != BlockType.LUNCH:
            continue
        if block.slot_index is None:
            continue
        start = bounds.day_start_minutes + int(block.slot_index) * SLOT_MINUTES
        length = max(SLOT_MINUTES, int(block.planned_minutes or SLOT_MINUTES))
        return (start, start + length)
    return None


#: No slot is lunch. ``None`` cannot say that: ``day_grid`` reads it as the
#: window Day Settings names, which is the hour a lunch block is always leaving.
NO_LUNCH: Tuple[int, int] = (0, 0)


def day_grid(
    bounds: DayBounds,
    span: Optional[DaySpan] = None,
    lunch: Optional[Tuple[int, int]] = None,
) -> List[Slot]:
    """Every half hour of the drawn day, in order.

    Purpose: the set of boxes a day offers, which is the thing items are
             dropped onto.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m1
    Tests:   tests/test_time_grid.py::test_tgm11_grid_covers_the_day_in_half_hours

    Without a ``span`` this is the hours in Day Settings: a slot that would run
    past Day End is not produced at all, so a Day End of 16:45 gives a last
    slot of 16:00--16:30 rather than a 15-minute stub that nothing can hold.
    With one (PD-M14.2) the day runs from that span's first box to its last,
    which may begin before Day Start -- a negative index -- or end after Day
    End. Lunch slots are **marked, not removed**: the grid stays contiguous in
    time, which is what lets a span's end be its start plus its length without
    walking the list.
    """
    drawn = template_span(bounds) if span is None else span
    if lunch is not None:
        lunch_start, lunch_end = lunch
        has_lunch = lunch_end > lunch_start
    else:
        lunch_start = bounds.lunch_start_minutes
        lunch_end = bounds.lunch_end_minutes
        has_lunch = bounds.lunch_length > 0

    slots: List[Slot] = []
    for index in range(drawn.first, drawn.last + 1):
        at = bounds.day_start_minutes + index * SLOT_MINUTES
        # Overlap, not containment: a lunch of 12:15--12:45 makes both the
        # 12:00 and the 12:30 slot unavailable, because a block in either
        # would run through part of it.
        overlaps_lunch = has_lunch and at < lunch_end and lunch_start < at + SLOT_MINUTES
        slots.append(Slot(index=index, start_minutes=at, is_lunch=overlaps_lunch))
    return slots


#: The two ends a drop can extend the day from (PD-M5).
DAY_EXTEND_EARLIER = "earlier"
DAY_EXTEND_LATER = "later"

#: The latest Day End that still yields whole boxes. A box running 23:30--24:00
#: would need a Day End of "24:00", which is not a time of day, so the last box
#: a day can offer starts at 23:00 and the day ends at 23:30.
LAST_DAY_END_MINUTES = MINUTES_PER_DAY - SLOT_MINUTES


def edge_limit_time(edge: str) -> str:
    """The clock time one end of the day stops at.

    Purpose: PD-M14.6 -- the two limits are genuinely different (a block may
             start no earlier than midnight and end no later than the last
             whole half hour), so the refusal has to name which one it hit.
             One function, so the two ends cannot drift apart or name a time
             the arithmetic does not actually enforce.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-6
    Tests:   tests/test_plan_screen.py::test_pdm146_both_ends_refuse_at_midnight_and_say_which
    """
    if edge == DAY_EXTEND_EARLIER:
        return format_hhmm(0)
    if edge == DAY_EXTEND_LATER:
        return format_hhmm(LAST_DAY_END_MINUTES)
    raise ValueError(f"not an end of the day: {edge!r}")


@dataclass(frozen=True)
class DayExtension:
    """Where a drop on one of the two ends puts a block, and the day it makes."""

    span: DaySpan
    slot_index: int


def extended_span(
    drawn: DaySpan, bounds: DayBounds, direction: str, span: int
) -> Optional[DayExtension]:
    """The day that makes room for ``span`` more boxes at one end, and the box.

    Purpose: PD-M14.1 -- a drop above the day or below it lengthens the **day
             on screen** and writes one block. It does not move Day Start or
             Day End: those are the hours a blank day begins from, and one
             setting shared by every date is not a thing a single drop may
             change (this replaces ``extended_day_bound``, which did exactly
             that and ratcheted the hours outward with nothing to put them
             back).
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-1
    Tests:   tests/test_time_block_layout.py::test_pdm141_the_span_grows_at_the_end_that_was_dropped_on
             tests/test_time_block_layout.py::test_pdm146_neither_end_can_leave_the_date

    ``None`` when the new boxes would leave the date, which the caller reports
    rather than clamping: a clamped day would make fewer boxes than the item
    needs, so the block would land somewhere other than the end that was
    dropped on, or not at all. A day is one date, and a block has no way to say
    it belongs to the next one.
    """
    span = max(1, int(span))
    if direction == DAY_EXTEND_EARLIER:
        slot_index = drawn.first - span
    elif direction == DAY_EXTEND_LATER:
        slot_index = drawn.last + 1
    else:
        raise ValueError(f"not an end of the day: {direction!r}")
    if not _stays_inside_the_date(slot_index, span, bounds):
        return None
    return DayExtension(
        span=drawn.widened_to(slot_index, span), slot_index=slot_index
    )


def slots_for_minutes(minutes: Optional[int]) -> int:
    """How many boxes a block of this length occupies, rounding up.

    Purpose: 45 minutes takes two boxes. The item keeps its own 45; the grid it
             occupies is 60, and the screen shows both because they are
             different facts.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m2
    Tests:   tests/test_time_grid.py::test_tgm21_odd_lengths_round_up

    Never zero: a block with a nonsense length still has to be somewhere, and a
    zero-slot block would be invisible and undraggable rather than obviously
    wrong.
    """
    value = _positive_int(minutes, FALLBACK_BLOCK_MINUTES)
    return max(1, -(-value // SLOT_MINUTES))


def spare_minutes_in_last_slot(block: TimeBlock) -> int:
    """Minutes of the block's last box that the block itself does not use.

    Purpose: TG-M2 -- the 45-in-two-boxes case, said out loud.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m2
    Tests:   tests/test_time_grid.py::test_the_spare_minutes_of_the_last_box_are_what_the_task_leaves

    A 45-minute task occupies two boxes and ends at 09:45, so 15 minutes of
    the 09:30 box are spare. Spare, not free: the next task starts at 10:00,
    because a box is the unit the day is planned in. This number exists so the
    screen can show the gap rather than let the user discover it by arithmetic
    -- and so that the day summary's "occupied" and "planned" totals have a
    stated reason to differ.
    """
    minutes = _positive_int(getattr(block, "planned_minutes", None), 0)
    if minutes <= 0:
        return 0
    return slots_for_minutes(minutes) * SLOT_MINUTES - minutes


def slot_span_of(block: TimeBlock) -> int:
    """The span of a stored block, derived from its length and never stored.

    Two columns that can disagree about one fact is the failure this project
    already catalogues (P6), so ``span`` is computed everywhere it is needed
    rather than written beside ``planned_minutes``.
    """
    return slots_for_minutes(getattr(block, "planned_minutes", None))


def can_place(
    blocks: Sequence[TimeBlock],
    bounds: DayBounds,
    slot_index: int,
    span: int,
    *,
    ignoring: Optional[str] = None,
    day_span: Optional[DaySpan] = None,
    placing_lunch: bool = False,
) -> Optional[str]:
    """``None`` if a block of ``span`` boxes may sit at ``slot_index``.

    Purpose: one answer for every write path, so a drop, a move and a resize
             cannot disagree about what the day allows.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m2
    Tests:   tests/test_time_grid.py::test_tgm23_each_refusal_has_its_own_reason

    Returns a ``SlotRefusal`` value rather than raising: a refusal here is an
    ordinary answer about an ordinary gesture, not an error. ``ignoring`` is
    the block being moved, which must not count itself as occupying the slot
    it is leaving.

    ``day_span`` is the day being drawn (PD-M14.2). Left out, it is the hours
    in Day Settings, which is what every gesture inside the day wants. A drop
    on one of the two ends passes a span that already covers the box it is
    about to create, because that box is outside the hours by definition --
    that is what the gesture means.

    ``placing_lunch``: the block being placed *is* this date's lunch, so
    neither reason a box can be taken applies -- it defines where lunch is, and
    a lunch box holds the lunch alone (``build_day_grid`` surfaces the rest).
    """
    span = max(1, int(span))
    drawn = template_span(bounds) if day_span is None else day_span
    # PF-M8 -- lunch is where this date's own lunch block puts it, unless the
    # block being placed *is* that lunch: then there is no lunch in the way, or
    # the lunch could never be moved off the box it sits on.
    lunch = NO_LUNCH if placing_lunch else lunch_window(blocks, bounds, ignoring=ignoring)
    grid = day_grid(bounds, drawn, lunch)
    if not drawn.holds(slot_index, span):
        return SlotRefusal.OUTSIDE_GRID

    at = drawn.position_of(slot_index)
    covered = grid[at : at + span]
    if any(slot.is_lunch for slot in covered):
        return SlotRefusal.CROSSES_LUNCH

    # PF-M8 -- a lunch box holds the lunch alone, so the room in it is moot.
    if placing_lunch:
        return None

    occupancy = slot_occupancy(blocks, bounds, ignoring=ignoring, day_span=drawn)
    if any(len(occupancy.get(slot.index, ())) >= MAX_BLOCKS_PER_SLOT for slot in covered):
        return SlotRefusal.SLOT_FULL
    return None


def slot_occupancy(
    blocks: Iterable[TimeBlock],
    bounds: DayBounds,
    *,
    ignoring: Optional[str] = None,
    day_span: Optional[DaySpan] = None,
) -> dict:
    """Which blocks cover which slot index, spanning blocks included.

    A block at slot 4 with a span of 2 appears under both 4 and 5, because
    "is there room here" has to mean the whole box, not just where something
    started.

    Only the boxes the drawn day has (PD-M14.2), which by default is the span
    this date's own blocks need. A block the grid cannot hold is drawn in the
    "outside the day" group instead, and one that is not on the day must not
    hold a box against a drop -- a refusal whose cause is invisible reads as a
    gesture that did nothing.
    """
    drawn = span_for_blocks(blocks, bounds) if day_span is None else day_span
    occupancy: dict = {}
    for block in blocks:
        if ignoring is not None and str(getattr(block, "id", "")) == str(ignoring):
            continue
        start = _slot_index_of(block)
        if start is None:
            continue
        for offset in range(slot_span_of(block)):
            index = start + offset
            if drawn.holds(index):
                occupancy.setdefault(index, []).append(block)
    return occupancy


def times_for_slot(slot_index: int, minutes: int, bounds: DayBounds) -> Tuple[str, str]:
    """The clock times a block at this slot carries.

    Purpose: the derived ``start_time``/``end_time`` written with every slot
             change, so the row stays readable in sqlite and the
             ``end == start + planned_minutes`` invariant stays checkable.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m6
    Tests:   tests/test_time_block_crud.py::test_tgm63_every_row_says_start_plus_duration

    The end is the start plus the block's **own** length, not the end of the
    last box it occupies. A 45-minute block in two boxes ends at 09:45 and
    leaves 15 minutes of its second box spare; writing 10:00 there would be the
    row claiming minutes the item does not own.
    """
    # Signed (PD-M14.2). This clamped the index at 0, which gave every box
    # before Day Start the time of the first one -- so a block dropped on
    # Earlier could only ever record the hour it was not planned at.
    start = bounds.day_start_minutes + int(slot_index) * SLOT_MINUTES
    return format_hhmm(start), format_hhmm(start + _positive_int(minutes, 0))


@dataclass
class GridSlot:
    """One rendered row of the day: a slot and what sits in it."""

    slot: Slot
    starting: List[TimeBlock] = field(default_factory=list)
    continued: List[TimeBlock] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.starting and not self.continued


@dataclass
class DayGrid:
    """A day ready to draw: every slot, plus whatever no slot can hold."""

    slots: List[GridSlot] = field(default_factory=list)
    outside: List[TimeBlock] = field(default_factory=list)
    # The boxes this grid actually drew, which is the template's hours
    # stretched to the date's own blocks (PD-M14.2). Carried here so a caller
    # that has the grid does not derive the same span a second time and get a
    # different answer: ``slots[0].slot.index`` is the same number, but a day
    # with no boxes at all has no slots to read it from.
    span: DaySpan = field(default_factory=lambda: DaySpan(0, -1))

    @property
    def slots_used(self) -> int:
        return sum(1 for entry in self.slots if not entry.is_empty)

    @property
    def minutes_occupied(self) -> int:
        """The day's cost in boxes: 30 a box, however many tasks share it."""
        return self.slots_used * SLOT_MINUTES


def build_day_grid(
    blocks: Iterable[TimeBlock],
    bounds: DayBounds,
    span: Optional[DaySpan] = None,
) -> DayGrid:
    """Lay a day's blocks onto its grid.

    Purpose: the single function the screen draws from, so what is on screen
             and what the arithmetic says are the same object.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m3
    Tests:   tests/test_time_grid.py::test_tgm31_a_block_with_no_box_is_surfaced

    Without a ``span`` the day drawn is the hours in Day Settings stretched to
    cover this date's own blocks (PD-M14.2), so a block dropped before Day
    Start is on the grid rather than beside it.

    A block whose slot no longer exists -- because its stored index is far
    outside the date, or because its length now spans past the last box -- is
    **returned in ``outside``, never dropped** (P2). The day it stops being drawn is the day
    the user loses work with nothing on screen to say so.

    A block whose boxes now include lunch goes to ``outside`` for the same
    reason. ``can_place`` refuses lunch, so this is only reachable after the
    user moves the lunch hour over work they had already planned -- and a
    lunch box draws "Lunch" and nothing else, so leaving the block in it would
    hide it exactly as dropping it would.
    """
    blocks = list(blocks)
    drawn = span_for_blocks(blocks, bounds) if span is None else span
    # PF-M8 -- the date's own lunch, when it has one. ``None`` is the settings'.
    lunch = lunch_window(blocks, bounds)
    grid = [GridSlot(slot=slot) for slot in day_grid(bounds, drawn, lunch)]
    outside: List[TimeBlock] = []

    for block in sort_blocks_by_slot(blocks):
        start = _slot_index_of(block)
        length = slot_span_of(block)
        if start is None or not drawn.holds(start, length):
            outside.append(block)
            continue
        at = drawn.position_of(start)
        is_lunch = BlockType.normalize(block.block_type) == BlockType.LUNCH
        # A lunch block lives on the lunch it defines; everything else in a
        # lunch box is surfaced rather than hidden behind "Lunch".
        if not is_lunch and any(entry.slot.is_lunch for entry in grid[at : at + length]):
            outside.append(block)
            continue
        grid[at].starting.append(block)
        for offset in range(1, length):
            grid[at + offset].continued.append(block)

    return DayGrid(slots=grid, outside=outside, span=drawn)


def sort_blocks_by_slot(blocks: Iterable[TimeBlock]) -> List[TimeBlock]:
    """Blocks in the order a day reads: by slot, then within a slot.

    ``position`` keeps its name and its job, but now orders blocks *inside* one
    box, which is what makes two tasks in a box representable without a second
    table.
    """
    return sorted(
        blocks,
        key=lambda block: (
            _slot_index_of(block) if _slot_index_of(block) is not None else 10**6,
            _positive_int(getattr(block, "position", None), 0),
            str(getattr(block, "id", "")),
        ),
    )


def _slot_index_of(block: TimeBlock) -> Optional[int]:
    """A block's slot, or ``None`` when it has never been placed."""
    raw = getattr(block, "slot_index", None)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def block_title(block: TimeBlock, item: Optional[ActionItem]) -> str:
    """What to call a block: its item's title, its label, or its kind.

    Purpose: CE-M2.2 -- one answer, used by the screen that draws the block
             and by the export that names its calendar event.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m22
    Tests:   tests/test_calendar_export.py::test_cem221_every_branch_of_the_title_rule_names_a_block,
             tests/test_plan_screen_calendar_export.py::test_cem221a_an_event_is_titled_what_the_day_draws_on_the_block

    Moved here from ``screens/plan_blocks.py``, which imports CustomTkinter:
    the exporter must be provable headless, and a second copy of this rule
    would let an exported event be called something the day does not show
    (P19 -- a format contract that drifts between producer and consumer).
    """
    kind = BlockType.normalize(block.block_type)
    if kind == BlockType.BUFFER:
        return block.label or "Buffer"
    if kind == BlockType.BREAK:
        return block.label or "Break"
    if item is not None:
        return item.title
    # An item block whose item is gone. Named rather than blank: a block with
    # no text looks like a rendering fault, and the label is the last record of
    # what it was for.
    return block.label or "(item no longer exists)"


def slot_index_for_time(
    start_time: Optional[str],
    bounds: DayBounds,
    *,
    allow_before: bool = False,
) -> Optional[int]:
    """The slot a stored clock time falls in, for the migration.

    Purpose: map the days already in the database onto the grid.
    Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
    Tests:   tests/test_time_block_schema.py::test_tgm51_existing_times_map_to_slots

    ``None`` for a time that cannot be read, and -- for the migration, which
    is this function's default caller -- for one that falls before Day Start,
    so it can fall back to the row's position rather than inventing a slot.

    ``allow_before`` is PD-M14.7, which wants the negative answer: a block
    recorded at 08:30 under a 09:00 day was planned half an hour before the
    hours now begin, and that is a box the day can draw. Floor division, so
    an offset of -30 is box -1 and not box 0.
    """
    try:
        minutes = parse_hhmm(start_time)
    except TimeFormatError:
        return None
    offset = minutes - bounds.day_start_minutes
    if offset < 0 and not allow_before:
        return None
    return offset // SLOT_MINUTES
