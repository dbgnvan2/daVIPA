"""CIP-M6 -- the week view's arithmetic: seven days, each read as its day grid.

Purpose: CIP-M6.1 and CIP-M6.2. A week column is the same ``build_day_grid``
         call the day grid makes, over the same cache and the same occupancy
         rule (``committed_slots``); this module only counts its boxes.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_week.md
Tests:   tests/test_plan_week.py

Read-only: nothing here writes. The day screen's load also places blocks from
an earlier version and repairs slots from their times; those are writes, and
they stay on the day screen. A block with no box is counted as outside the
day here, which is what the day grid draws it as before that repair.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Sequence, Tuple

from .calendar_commitments import committed_slots
from .time_block_layout import (
    SLOT_MINUTES,
    DayBounds,
    DayGrid,
    GridSlot,
    build_day_grid,
    is_block_day,
)

WEEK_DAYS = 7

#: What one box of a week column holds. A box holding a meeting and a block
#: is a meeting: the meeting is what makes the hour gone.
MEETING = "meeting"
PLANNED = "planned"  # a Time Block, or lunch
FREE = "free"
UNREAD = "unread"  # empty, on a date the calendar was never read for


def week_dates(first: str) -> List[str]:
    """The selected date and the six after it (W3)."""
    start = date.fromisoformat(first)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(WEEK_DAYS)]


def box_kind(entry: GridSlot, committed: frozenset, *, read: bool) -> str:
    """One box, as the week view shades it (W2, W7)."""
    if entry.slot.index in committed:
        return MEETING
    if entry.slot.is_lunch or not entry.is_empty:
        return PLANNED
    return FREE if read else UNREAD


@dataclass
class DaySummary:
    """One week column: its boxes by slot index, and what they add up to."""

    day: str
    boxes: List[Tuple[int, str]] = field(default_factory=list)
    read: bool = True
    block_day: bool = True
    outside: int = 0
    #: All-day events: they hold no box, so no box can show them.
    all_day: int = 0

    def _minutes(self, kind: str) -> int:
        return sum(SLOT_MINUTES for _, k in self.boxes if k == kind)

    @property
    def meeting_minutes(self) -> int:
        return self._minutes(MEETING)

    @property
    def planned_minutes(self) -> int:
        return self._minutes(PLANNED)

    @property
    def free_minutes(self) -> Optional[int]:
        """``None`` when free time is not known (W7) or cannot be used (W8)."""
        if not self.read or not self.block_day:
            return None
        return self._minutes(FREE)


def week_summary(day: str, grid: DayGrid, bounds: DayBounds, *, read: bool,
                 all_day: int = 0) -> DaySummary:
    """Count one date's grid into a week column."""
    committed = frozenset(grid.committed)
    return DaySummary(
        day=day,
        boxes=[(entry.slot.index, box_kind(entry, committed, read=read)) for entry in grid.slots],
        read=read,
        block_day=is_block_day(day, bounds),
        outside=len(grid.outside),
        all_day=all_day,
    )


def is_read(fetch: Optional[dict]) -> bool:
    """Whether the calendar has ever answered for this date."""
    return bool(fetch and fetch.get("fetched_at"))


def read_week(db_manager, first: str, bounds: DayBounds) -> Tuple[List[DaySummary], List[Optional[dict]]]:
    """Each of the seven dates as the day grid would build it (M6.2), and its read record.

    The same three reads and the same call as ``PlanScreen.load_blocks``:
    the date's blocks, its cached commitments, and ``build_day_grid`` with
    ``committed_slots`` of them. No network.
    """
    summaries: List[DaySummary] = []
    fetches: List[Optional[dict]] = []
    for day in week_dates(first):
        blocks = db_manager.get_time_blocks(day)
        commitments = db_manager.get_commitments(day)
        fetch = db_manager.get_commitment_fetch(day)
        grid = build_day_grid(blocks, bounds, committed=committed_slots(commitments, bounds))
        all_day = sum(1 for c in commitments if c.is_all_day and not c.dismissed)
        summaries.append(week_summary(day, grid, bounds, read=is_read(fetch), all_day=all_day))
        fetches.append(fetch)
    return summaries, fetches


def week_rows(summaries: Sequence[DaySummary]) -> List[int]:
    """Every slot index any column has, in order, so rows line up across days."""
    return sorted({index for summary in summaries for index, _ in summary.boxes})


def hours_text(minutes: Optional[int]) -> str:
    """``150`` -> ``"2½h"``; ``None`` -> ``"—"``."""
    if minutes is None:
        return "—"
    whole, half = divmod(int(minutes), 60)
    if half >= SLOT_MINUTES:
        return f"{whole}½h" if whole else "½h"
    return f"{whole}h"


def week_age_text(fetches: Sequence[Optional[dict]], age_text) -> Tuple[str, str]:
    """W7 -- the header line: a failed read, then a partial one, then unread days, then the oldest read.

    A failure or a warning on any one of the seven is said, with the count of
    unread days after it, so neither hides the other (CIP sweep, batch 3).
    """
    unread = sum(1 for fetch in fetches if not is_read(fetch))
    suffix = f" · {unread} of {len(fetches)} days not read" if unread else ""
    for field_name in ("last_error", "warning"):
        flagged = [fetch for fetch in fetches if fetch and fetch.get(field_name)]
        if flagged:
            text, kind = age_text(flagged[0])
            return text + suffix, kind
    if unread:
        return f"Calendar not read for {unread} of {len(fetches)} days — ↻ Calendar reads the week", "muted"
    oldest = min(fetches, key=lambda fetch: str(fetch["fetched_at"]))
    return age_text(oldest)
