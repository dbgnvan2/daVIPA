"""Day-layout arithmetic for the time block planner.

Purpose: turn an ordered list of blocks plus a day's bounds into clock times,
         and answer the small questions the planner asks about an item (how
         long a block for it should be, how deep it is, which band its
         priority falls in, whether a date may hold blocks at all).
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
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

# priority_score is the *product* of importance x urgency x size x value
# (20 x 20 x 16 x 16), so it runs 4 .. 102400 -- not 1 .. 10. Bands are
# thresholds on that product, lowest bound first match wins from the top.
# The colours for these band names live in theme.py; only the arithmetic is
# here, so a theme change cannot alter which band an item is in.
PRIORITY_BANDS: Tuple[Tuple[int, str], ...] = (
    (2000, "critical"),
    (500, "high"),
    (100, "medium"),
    (1, "low"),
)
UNSCORED_BAND = "unscored"

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

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
    Tests: tests/test_time_block_layout.py::test_a_clock_time_past_midnight_is_refused

    ``parse_hhmm`` deliberately accepts an hour past 23, because ``format_hhmm``
    writes one: a block that overruns the day gets an end_time like ``25:30``,
    and ``sort_blocks`` has to be able to read that back. A day *bound* is a
    different thing -- a point on one clock face. Accepting ``25:00`` as a Day
    End puts the end of the day beyond any block's reach, so the overrun
    warning that is Day End's only job can never fire again.

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

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
    Tests: tests/test_time_block_layout.py::test_tbm31_blocks_pack_from_day_start

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

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m8
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


def priority_band(score: Optional[int]) -> str:
    """Which band a priority score falls in.

    Returns ``"unscored"`` for 0, None or a negative: an item missing one of its
    four factors scores 0, and that is absence of information, not low priority.
    Painting it the same colour as a genuinely low-priority item would invent
    data the user never entered.
    """
    try:
        number = int(score)
    except (TypeError, ValueError):
        return UNSCORED_BAND
    if number <= 0:
        return UNSCORED_BAND
    for threshold, name in PRIORITY_BANDS:
        if number >= threshold:
            return name
    return UNSCORED_BAND


class DayTooFullError(Exception):
    """A day whose blocks run past the last time ``HH:MM`` can express.

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
    Tests: tests/test_time_block_crud.py::test_a_day_too_full_to_write_is_refused

    Raised by the writer, never by the display path. Past
    ``MAX_FORMATTED_MINUTES`` ``format_hhmm`` clamps, so the row would be stored
    with an end time that is not its start plus its duration -- and the
    per-block ceiling cannot prevent it, because the ceiling bounds one block
    and this is a property of the day. Four blocks of exactly a day each are
    individually legal and together unrepresentable.
    """


@dataclass
class PackedBlock:
    """A block with the clock times its place in the day gives it."""

    block: TimeBlock
    start_minutes: int
    end_minutes: int
    #: True when this block ends after the configured day end. It is reported,
    #: never dropped: a day the user has over-filled is something to show them,
    #: not something to silently discard part of (P2).
    overflows_day_end: bool = False
    #: True when this block was moved past lunch to avoid straddling it, so the
    #: screen knows where to draw the lunch band.
    pushed_after_lunch: bool = False

    @property
    def start_time(self) -> str:
        return format_hhmm(self.start_minutes)

    @property
    def end_time(self) -> str:
        return format_hhmm(self.end_minutes)

    @property
    def planned_minutes(self) -> int:
        return max(0, self.end_minutes - self.start_minutes)

    @property
    def fits_the_clock(self) -> bool:
        """Whether this block's times can be stored without being clamped.

        ``format_hhmm`` clamps at ``MAX_FORMATTED_MINUTES``, so a block past it
        would be written with an end time that is not its start plus its
        duration. The display path tolerates that; the writer must not.
        """
        return self.end_minutes <= MAX_FORMATTED_MINUTES


def pack_day(blocks: Sequence[TimeBlock], bounds: DayBounds) -> List[PackedBlock]:
    """Assign clock times to an ordered sequence of blocks.

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m3
    Tests: tests/test_time_block_layout.py::test_tbm31_blocks_pack_from_day_start

    Blocks are packed back to back from the day's start, in the order given --
    the caller has already sorted them, because the order *is* the plan.

    A block that would straddle lunch is moved **whole** to after lunch rather
    than split across it. Splitting would be the obvious implementation and the
    wrong one: half an hour of deep work before lunch and half an hour after is
    not the same thing as an hour of it, and the planner should not quietly
    claim otherwise.

    Blocks that run past the day's end are returned with ``overflows_day_end``
    set. Nothing is refused and nothing is trimmed here; over-filling a day is
    the user's business, and the screen's job is to show it.
    """
    packed: List[PackedBlock] = []
    cursor = bounds.day_start_minutes
    lunch_start = bounds.lunch_start_minutes
    lunch_end = bounds.lunch_end_minutes
    has_lunch = bounds.lunch_length > 0
    day_end = bounds.day_end_minutes

    for block in blocks:
        duration = _positive_int(getattr(block, "planned_minutes", None), bounds.default_block_minutes)

        pushed = False
        # Straddles lunch when it starts before lunch ends and would still be
        # running once lunch has begun. A block that starts exactly at
        # lunch_start is inside lunch, and moves too.
        if has_lunch and cursor < lunch_end and cursor + duration > lunch_start:
            cursor = lunch_end
            pushed = True

        start = cursor
        end = start + duration
        packed.append(
            PackedBlock(
                block=block,
                start_minutes=start,
                end_minutes=end,
                overflows_day_end=end > day_end,
                pushed_after_lunch=pushed,
            )
        )
        cursor = end

    return packed


def sort_blocks(blocks: Iterable[TimeBlock]) -> List[TimeBlock]:
    """Blocks in the order the day runs: position first, then stored time.

    The secondary key carries legacy rows. Every block written before TB-M1 has
    position 0, so position alone would order a migrated day arbitrarily --
    their real sequence is still in the start_time they were created with.
    """
    return sorted(
        blocks,
        key=lambda block: (
            _positive_int(getattr(block, "position", None), 0),
            parse_hhmm(getattr(block, "start_time", None), default="00:00"),
        ),
    )


def renumber(blocks: Sequence[TimeBlock]) -> None:
    """Stamp 1..n onto the given order, in place.

    Positions start at 1, not 0: 0 is the value every legacy row carries, and
    keeping it reserved means ``sort_blocks`` can tell a renumbered day from a
    migrated one.
    """
    for index, block in enumerate(blocks, start=1):
        block.position = index


def move_block(order: Sequence[str], block_id: str, target_index: int) -> List[str]:
    """The id order after dragging ``block_id`` to ``target_index``.

    Pure list arithmetic, kept out of the screen so the reorder can be tested
    without a mouse. ``target_index`` is the position the block should occupy
    once removed from its old place; out-of-range values clamp to the ends, and
    an id that is not in the order is returned unchanged rather than appended --
    a drag of something that is no longer there must not resurrect it.
    """
    ids = list(order)
    if block_id not in ids:
        return ids
    ids.remove(block_id)
    index = max(0, min(int(target_index), len(ids)))
    ids.insert(index, block_id)
    return ids


def move_block_to_gap(order: Sequence[str], block_id: str, gap_index: int) -> List[str]:
    """The id order after dropping ``block_id`` into the gap at ``gap_index``.

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m11
    Tests: tests/test_time_block_layout.py::test_a_downward_drop_lands_in_the_gap_it_was_dropped_in

    ``gap_index`` is counted against the list **as rendered** -- the dragged
    block still in it -- because that is the only thing the screen can measure:
    it compares the pointer against the midpoints of the rows actually on
    screen. ``move_block`` counts against the list with the block already
    removed. The two differ by one for a downward move, and passing a rendered
    gap index straight to ``move_block`` is why every downward drag used to
    land one place too far.
    """
    ids = list(order)
    if block_id not in ids:
        return ids
    gap = max(0, min(int(gap_index), len(ids)))
    if ids.index(block_id) < gap:
        gap -= 1
    return move_block(ids, block_id, gap)


def total_planned_minutes(blocks: Iterable[TimeBlock]) -> int:
    """Minutes committed on a day, buffers and breaks included."""
    return sum(
        _positive_int(getattr(block, "planned_minutes", None), 0)
        for block in blocks
    )


# TB-M12 — a block's height tracks its length, so a 90 reads as three times a
# 30 at a glance. 1.1 px per minute keeps the common lengths exactly
# proportional (30 -> 33, 60 -> 66, 90 -> 99) rather than nearly so.
PIXELS_PER_MINUTE = 1.1
# A 5-minute break at 1.1 px/min would be 6 pixels tall: too small to see,
# read or right-click. Short blocks stop shrinking here, which is the one place
# proportionality is deliberately given up.
MIN_BLOCK_HEIGHT_PX = 26


def block_height(minutes: Optional[int]) -> int:
    """Pixel height for a block of this many minutes.

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m12
    Tests: tests/test_time_block_layout.py::test_block_height_is_proportional_to_minutes
    """
    length = _positive_int(minutes, FALLBACK_BLOCK_MINUTES)
    return max(MIN_BLOCK_HEIGHT_PX, round(length * PIXELS_PER_MINUTE))


def lunch_window(bounds: DayBounds) -> Optional[Tuple[str, str]]:
    """The lunch band as ``(start, end)``, or None when lunch is zero minutes."""
    if bounds.lunch_length <= 0:
        return None
    return format_hhmm(bounds.lunch_start_minutes), format_hhmm(bounds.lunch_end_minutes)


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
