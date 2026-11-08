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

    Spec:  docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
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


# ---------------------------------------------------------------------------
# Retired with the order-based model (TG, 2026-11-05)
#
# ``DayTooFullError``, ``PackedBlock``, ``pack_day``, ``sort_blocks``,
# ``renumber``, ``move_block`` and ``move_block_to_gap`` lived here.
#
# A planned day was an *order*: ``position`` was the truth, and the clock times
# were derived by walking that order from Day Start, past lunch, until the day
# ran out -- which is what ``DayTooFullError`` reported. A fixed grid stores the
# box instead, so there is nothing to pack and no ceiling to run past: the last
# box ends at Day End. ``position`` keeps its name and now orders the tasks
# *inside* one box, which ``_next_position_in_slot`` assigns directly, so
# nothing renumbers a day any more. A drop names a box, so there is no "between
# rows 2 and 3" gap to convert into a list position.
#
# Deleted rather than left unused: a guard that can no longer fire is the thing
# this repo's checklist warns about (P27), because the next reader takes its
# presence as evidence that the case it names still exists.
#
# ``sort_blocks_by_slot`` below is the replacement for ``sort_blocks``.
# ---------------------------------------------------------------------------


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
# Spec: docs/implementation_plan_2026-11-05_time_grid.md#m1
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


def day_grid(bounds: DayBounds) -> List[Slot]:
    """Every half hour from Day Start to Day End, in order.

    Purpose: the fixed set of boxes a day offers, which is the thing items are
             dropped onto.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m1
    Tests:   tests/test_time_grid.py::test_tgm11_grid_covers_the_day_in_half_hours

    A slot that would run past Day End is not produced at all, so a Day End of
    16:45 gives a last slot of 16:00--16:30 rather than a 15-minute stub that
    nothing can hold. Lunch slots are **marked, not removed**: the grid stays
    contiguous in time, which is what lets a span's end be its start plus its
    length without walking the list.
    """
    start = bounds.day_start_minutes
    end = bounds.day_end_minutes
    lunch_start = bounds.lunch_start_minutes
    lunch_end = bounds.lunch_end_minutes

    slots: List[Slot] = []
    index = 0
    at = start
    while at + SLOT_MINUTES <= end:
        # Overlap, not containment: a lunch of 12:15--12:45 makes both the
        # 12:00 and the 12:30 slot unavailable, because a block in either
        # would run through part of it.
        slots.append(
            Slot(index=index, start_minutes=at, is_lunch=_overlaps_lunch(bounds, at))
        )
        index += 1
        at += SLOT_MINUTES
    return slots


def _overlaps_lunch(bounds: DayBounds, at: int) -> bool:
    """Whether a box starting at ``at`` runs through any part of lunch.

    Overlap, not containment: a lunch of 12:15--12:45 makes both the 12:00 and
    the 12:30 box unavailable. Factored out because three places now build a
    ``Slot`` -- ``day_grid``, ``drawn_day_slots`` and ``can_place`` -- and a
    lunch rule written three times is a lunch rule that will disagree with
    itself.
    """
    return (
        bounds.lunch_length > 0
        and at < bounds.lunch_end_minutes
        and bounds.lunch_start_minutes < at + SLOT_MINUTES
    )


def drawn_day_slots(
    bounds: DayBounds, blocks: Iterable[TimeBlock] = ()
) -> List[Slot]:
    """The configured day, widened to cover any blocks lying outside it.

    Purpose: PD-M13 -- "when add to start and End of day do NOT change the
             length of Day in Settings". Day Start and Day End are the day the
             user configured; this is the day that gets drawn, which is that
             range plus whatever has been dropped past either end.
    Spec:    docs/implementation_plan_2026-11-07_plan_day_range.md#pd-m13
    Tests:   tests/test_time_grid.py::test_pdm133_a_block_before_day_start_gets_a_box
             tests/test_time_grid.py::test_pdm134_a_block_past_day_end_gets_a_box

    ``Slot.index`` is counted from the configured Day Start and **may be
    negative**, which is the whole mechanism: a box before the configured start
    is index -1, and no other date's stored index has to move for it to exist.
    The alternative -- what this replaces -- was to move ``plan_day_start`` and
    renumber every date's blocks to compensate, so one drop on one date
    redefined the working day everywhere.

    With no blocks outside the range this returns exactly ``day_grid(bounds)``,
    so the ordinary day is unchanged and the configured range is the floor:
    the day never draws *narrower* than what the user set, however empty it is.
    The date is the ceiling, and it is applied to each block rather than to
    the result: a block the date cannot hold widens the day by nothing at all.
    So every drawn box is one ``can_place`` will accept, and no box is drawn
    past the configured range unless a block is actually drawn in it.
    """
    configured = day_grid(bounds)
    first = 0
    # ``len - 1``, so a configured range too short to yield a single box
    # (Day End at or before Day Start) gives last < first and contributes
    # nothing, rather than claiming a box at index -1.
    last = len(configured) - 1
    for block in blocks:
        start = _slot_index_of(block)
        if start is None:
            continue
        span = slot_span_of(block)
        # A block the date cannot hold widens nothing. It is not drawable, so
        # ``build_day_grid`` routes it to ``outside`` either way -- and
        # widening for it would add empty boxes past the configured range that
        # hold nothing, for a block that is not drawn in them. This is also
        # what keeps every drawn box one ``can_place`` accepts: a stored index
        # counts from Day Start, so *reducing* Day Start in Settings
        # reinterprets it, and a box placed before the old start can land
        # before midnight. Drawn anyway, ``format_hhmm`` floors it to "00:00"
        # and the block shows the wrong time in a box that refuses every move,
        # with deleting it the only way out.
        if not slot_is_on_the_date(bounds, start, span):
            continue
        first = min(first, start)
        last = max(last, start + span - 1)

    day_start = bounds.day_start_minutes
    slots: List[Slot] = []
    for index in range(first, last + 1):
        at = day_start + index * SLOT_MINUTES
        slots.append(
            Slot(index=index, start_minutes=at, is_lunch=_overlaps_lunch(bounds, at))
        )
    return slots


def slot_is_on_the_date(bounds: DayBounds, slot_index: int, span: int = 1) -> bool:
    """Whether a block of ``span`` boxes at this index stays inside one date.

    Purpose: PD-M5.8's guarantee, moved off the bound and onto the box. The day
             no longer grows by moving Day Start, so "a day is one date" can no
             longer be enforced by refusing a new bound -- it is enforced here,
             on the box the block would occupy.
    Spec:    docs/implementation_plan_2026-11-07_plan_day_range.md#pd-m13
    Tests:   tests/test_time_grid.py::test_pdm1311_a_box_before_midnight_is_refused

    A block has no way to say it belongs to the next date, so a box that would
    start before 00:00 or end after 24:00 is not a box this planner can hold.
    """
    span = max(1, int(span))
    at = bounds.day_start_minutes + int(slot_index) * SLOT_MINUTES
    return at >= 0 and at + span * SLOT_MINUTES <= MINUTES_PER_DAY


#: The two ends a drop can extend the day from (PD-M5).
DAY_EXTEND_EARLIER = "earlier"
DAY_EXTEND_LATER = "later"


def slots_for_minutes(minutes: Optional[int]) -> int:
    """How many boxes a block of this length occupies, rounding up.

    Purpose: 45 minutes takes two boxes. The item keeps its own 45; the grid it
             occupies is 60, and the screen shows both because they are
             different facts.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m2
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
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m2
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
    allow_outside_range: bool = False,
) -> Optional[str]:
    """``None`` if a block of ``span`` boxes may sit at ``slot_index``.

    Purpose: one answer for every write path, so a drop, a move and a resize
             cannot disagree about what the day allows.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m2
    Tests:   tests/test_time_grid.py::test_tgm23_each_refusal_has_its_own_reason

    Returns a ``SlotRefusal`` value rather than raising: a refusal here is an
    ordinary answer about an ordinary gesture, not an error. ``ignoring`` is
    the block being moved, which must not count itself as occupying the slot
    it is leaving.

    ``allow_outside_range`` is for the one gesture that means to make the day
    wider -- the Earlier/Later extension, which has to write a box that is not
    drawn yet. Every other caller leaves it alone, and the default refuses a
    box outside the day as drawn.

    The day *as drawn* is the limit, not the configured range, so this default
    on its own does not keep a write inside the hours the user configured once
    anything sits outside them. The two callers that need that stronger limit
    apply it themselves rather than asking for it here:

    * AutoLoad and the free-box scans walk ``day_grid(bounds)`` and bound the
      span by it as well (``plan.first_clear_slot``), so a button never fills
      an hour the user did not claim -- not even the tail of a span.
    * Adoption gives a pre-grid row with a readable ``start_time`` exactly one
      candidate, the box that time names, so it may land past Day End when the
      day is drawn out that far. That keeps the user's own clock time rather
      than inventing a different one, which is the point of honouring it. A
      row with no readable time is offered configured boxes only
      (``db_manager.adopt_legacy_day``), and a row that fits nowhere stays
      unplaced for the outside group to report (P2).
    """
    span = max(1, int(span))
    slot_index = int(slot_index)
    # A box outside the date is refused whatever the caller asked for: a block
    # has no way to say it belongs to the next one.
    if not slot_is_on_the_date(bounds, slot_index, span):
        return SlotRefusal.OUTSIDE_GRID
    # PD-M13: the limit for everyone else is the day *as drawn* -- the
    # configured range widened to cover the blocks already outside it -- not
    # the configured range alone. A box past Day End that already holds work
    # is a box the user can point at, so a drop there must be allowed; a box
    # past the drawn edge is one nothing is drawn on, and only the extension
    # gesture may write it.
    if not allow_outside_range:
        drawn = drawn_day_slots(bounds, blocks)
        if not drawn:
            return SlotRefusal.OUTSIDE_GRID
        if slot_index < drawn[0].index or slot_index + span - 1 > drawn[-1].index:
            return SlotRefusal.OUTSIDE_GRID

    covered = [
        Slot(
            index=slot_index + step,
            start_minutes=bounds.day_start_minutes
            + (slot_index + step) * SLOT_MINUTES,
            is_lunch=_overlaps_lunch(
                bounds, bounds.day_start_minutes + (slot_index + step) * SLOT_MINUTES
            ),
        )
        for step in range(span)
    ]
    if any(slot.is_lunch for slot in covered):
        return SlotRefusal.CROSSES_LUNCH

    occupancy = slot_occupancy(blocks, bounds, ignoring=ignoring)
    if any(len(occupancy.get(slot.index, ())) >= MAX_BLOCKS_PER_SLOT for slot in covered):
        return SlotRefusal.SLOT_FULL
    return None


def slot_occupancy(
    blocks: Iterable[TimeBlock],
    bounds: DayBounds,
    *,
    ignoring: Optional[str] = None,
) -> dict:
    """Which blocks cover which slot index, spanning blocks included.

    A block at slot 4 with a span of 2 appears under both 4 and 5, because
    "is there room here" has to mean the whole box, not just where something
    started.
    """
    occupancy: dict = {}
    for block in blocks:
        if ignoring is not None and str(getattr(block, "id", "")) == str(ignoring):
            continue
        start = _slot_index_of(block)
        if start is None:
            continue
        for offset in range(slot_span_of(block)):
            # PD-M13: no clamp to the configured range. A block before Day
            # Start has a negative index, and clamping it out would let a
            # second block stack invisibly in the same box.
            occupancy.setdefault(start + offset, []).append(block)
    return occupancy


def times_for_slot(slot_index: int, minutes: int, bounds: DayBounds) -> Tuple[str, str]:
    """The clock times a block at this slot carries.

    Purpose: the derived ``start_time``/``end_time`` written with every slot
             change, so the row stays readable in sqlite and the
             ``end == start + planned_minutes`` invariant stays checkable.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m6
    Tests:   tests/test_time_block_crud.py::test_tgm63_every_row_says_start_plus_duration

    The end is the start plus the block's **own** length, not the end of the
    last box it occupies. A 45-minute block in two boxes ends at 09:45 and
    leaves 15 minutes of its second box spare; writing 10:00 there would be the
    row claiming minutes the item does not own.

    PD-M13: the index is **not** clamped at zero. It was, from when a box
    before Day Start could not exist, and under PD-M13 that clamp wrote Day
    Start's own time onto every block dropped earlier than it -- a row at box
    -1 saying 08:00 while the screen drew it at 07:30, which is the row and the
    grid disagreeing with nothing marked wrong. ``slot_is_on_the_date`` is what
    refuses an index far enough back to leave the date, so a start before
    midnight does not reach this.
    """
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

    @property
    def slots_used(self) -> int:
        return sum(1 for entry in self.slots if not entry.is_empty)

    @property
    def minutes_occupied(self) -> int:
        """The day's cost in boxes: 30 a box, however many tasks share it."""
        return self.slots_used * SLOT_MINUTES


def build_day_grid(blocks: Iterable[TimeBlock], bounds: DayBounds) -> DayGrid:
    """Lay a day's blocks onto its grid.

    Purpose: the single function the screen draws from, so what is on screen
             and what the arithmetic says are the same object.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m3
    Tests:   tests/test_time_grid.py::test_a_never_placed_block_is_surfaced_rather_than_assumed_to_be_at_eight
             tests/test_time_grid.py::test_pdm13_an_index_the_new_day_start_puts_off_the_date_goes_outside

    A block whose slot no longer exists is **returned in ``outside``, never
    dropped** (P2). The day it stops being drawn is the day the user loses
    work with nothing on screen to say so. Moving Day End earlier is no longer
    one of the ways that happens -- ``drawn_day_slots`` widens the day to keep
    drawing a block past the configured end (PD-M13). What is left are a
    length that now spans past the last box, a stored index no date can hold
    (Day Start reduced under a block placed before it), and lunch, below.

    A block whose boxes now include lunch goes to ``outside`` for the same
    reason. ``can_place`` refuses lunch, so this is only reachable after the
    user moves the lunch hour over work they had already planned -- and a
    lunch box draws "Lunch" and nothing else, so leaving the block in it would
    hide it exactly as dropping it would.
    """
    blocks = list(blocks)
    grid = [GridSlot(slot=slot) for slot in drawn_day_slots(bounds, blocks)]
    # ``Slot.index`` is no longer the list position -- it is negative for the
    # boxes before the configured Day Start -- so every lookup goes through
    # this rather than indexing the list with a slot index.
    position = {entry.slot.index: at for at, entry in enumerate(grid)}
    outside: List[TimeBlock] = []

    for block in sort_blocks_by_slot(blocks):
        start = _slot_index_of(block)
        span = slot_span_of(block)
        at = position.get(start) if start is not None else None
        if at is None or at + span > len(grid):
            outside.append(block)
            continue
        if any(entry.slot.is_lunch for entry in grid[at : at + span]):
            outside.append(block)
            continue
        grid[at].starting.append(block)
        for offset in range(1, span):
            grid[at + offset].continued.append(block)

    return DayGrid(slots=grid, outside=outside)


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


def slot_index_for_time(start_time: Optional[str], bounds: DayBounds) -> Optional[int]:
    """The slot a stored clock time falls in, for the migration.

    Purpose: map the days already in the database onto the grid.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
    Tests:   tests/test_time_block_schema.py::test_tgm51_existing_times_map_to_slots

    ``None`` for a time that cannot be read or falls before Day Start, so the
    caller can fall back to the row's position rather than inventing a slot.
    """
    try:
        minutes = parse_hhmm(start_time)
    except TimeFormatError:
        return None
    offset = minutes - bounds.day_start_minutes
    if offset < 0:
        return None
    return offset // SLOT_MINUTES
