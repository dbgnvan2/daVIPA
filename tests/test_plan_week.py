"""CIP batch 3 -- the week view's counting, with no Tk.

Purpose: prove CIP-M6.1's per-day counts and W2/W7/W8 on a real tmp database.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_week.md
"""
from __future__ import annotations

from src.getmoredone.calendar_commitments import parse_event
from src.getmoredone.plan_week import (
    FREE,
    MEETING,
    PLANNED,
    UNREAD,
    DaySummary,
    hours_text,
    read_week,
    week_age_text,
    week_dates,
)
from tests.test_calendar_commitments import (  # noqa: F401 - fixture
    BOUNDS,
    DAY,
    TZ,
    _block,
    _event,
    manager,
)

SATURDAY = "2026-11-14"
TEN = 4  # 10:00 is box 4 of the default 08:00 day
LUNCH = (8, 9)  # 12:00 to 13:00


def _read(manager, *events, day=DAY):
    parts = [p for e in events for p in parse_event(e, calendar_id="primary", dates=[day], tz=TZ)]
    manager.replace_commitments_for_dates([day], parts, "2026-11-13T09:00:00")


def _day(manager, day=DAY):
    summaries, _fetches = read_week(manager, day, BOUNDS)
    return summaries[0]


def test_cipm61_free_excludes_meetings_lunch_and_blocks(manager):
    """W2 -- a meeting, a block and lunch are not free; every other box is."""
    _read(manager, _event())  # 10:00 to 10:30
    _block(manager, 2)
    summary = _day(manager)
    kinds = dict(summary.boxes)

    assert kinds[TEN] == MEETING
    assert kinds[2] == PLANNED
    assert [kinds[i] for i in LUNCH] == [PLANNED, PLANNED]
    assert summary.meeting_minutes == 30
    assert summary.planned_minutes == 90
    assert summary.free_minutes == (len(summary.boxes) - 4) * 30


def test_cipm61_a_box_with_a_meeting_and_a_block_counts_once(manager):
    """W2 -- the meeting is what makes the hour gone; it is not counted twice."""
    _block(manager, TEN)  # placed first: a block cannot be put on a meeting
    _read(manager, _event())
    summary = _day(manager)

    assert dict(summary.boxes)[TEN] == MEETING
    assert (summary.meeting_minutes, summary.planned_minutes) == (30, 60)


def test_cipm61_an_unread_day_has_no_free_count(manager):
    """W7 -- a date never read is not an empty day: no free count, no free box."""
    summary = _day(manager)

    assert summary.read is False
    assert summary.free_minutes is None
    assert FREE not in dict(summary.boxes).values()
    assert dict(summary.boxes)[TEN] == UNREAD


def test_cipm61_a_non_block_day_has_no_free_count(manager):
    """W8 -- nothing can be planned on a day Day Settings closes, so no free count."""
    _read(manager, day=SATURDAY)
    summary = _day(manager, SATURDAY)

    assert summary.read is True
    assert summary.block_day is False
    assert summary.free_minutes is None


def test_cipm61_the_week_is_the_selected_date_and_six_after():
    """W3 -- across a month end."""
    assert week_dates("2026-11-27") == [
        "2026-11-27", "2026-11-28", "2026-11-29", "2026-11-30",
        "2026-12-01", "2026-12-02", "2026-12-03",
    ]


def test_cipm61_hours_are_written_in_halves():
    assert [hours_text(m) for m in (0, 30, 60, 150, None)] == ["0h", "½h", "1h", "2½h", "—"]


def _age(fetch):
    return (f"read {fetch['fetched_at']}", "kind")


def test_cipm61_the_week_header_counts_unread_days():
    """W7 -- one unread date is named before any read time."""
    fetches = [{"fetched_at": "2026-11-13T09:00:00"}] * 6 + [None]
    text, kind = week_age_text(fetches, _age)
    assert text.startswith("Calendar not read for 1 of 7 days")
    assert kind == "muted"


def test_cipm61_the_week_header_shows_the_oldest_read():
    fetches = [{"fetched_at": "2026-11-13T09:00:00"}, {"fetched_at": "2026-11-12T08:00:00"}]
    assert week_age_text(fetches, _age) == ("read 2026-11-12T08:00:00", "kind")


def test_cipm61_the_week_header_shows_a_failed_read_first():
    failed = {"fetched_at": "2026-11-13T09:00:00", "last_error": "offline"}
    fetches = [{"fetched_at": "2026-11-12T08:00:00"}, failed]
    assert week_age_text(fetches, lambda f: (f.get("last_error", "ok"), "k")) == ("offline", "k")


def test_cipm61_a_partial_read_is_said_with_the_unread_count():
    """Sweep (batch 3) -- a warning on any one date is shown, and unread days are not hidden by it."""
    warned = {"fetched_at": "2026-11-13T09:00:00", "warning": "not read: Work"}
    fetches = [{"fetched_at": "2026-11-12T08:00:00"}, warned, None]
    text, kind = week_age_text(fetches, lambda f: (f.get("warning", "plain"), "warning"))
    assert (text, kind) == ("not read: Work · 1 of 3 days not read", "warning")


def test_cipm61_an_all_day_event_is_counted(manager):
    """Sweep (batch 3) -- an all-day event holds no box, so the column counts it."""
    event = {
        "id": "ad1", "summary": "Out of office", "organizer": {"self": True},
        "start": {"date": DAY}, "end": {"date": "2026-11-14"},
    }
    _read(manager, event)
    assert _day(manager).all_day == 1


def test_cipm61_a_summary_counts_blocks_outside_the_day(manager):
    from src.getmoredone.models import BlockType, TimeBlock

    manager.create_time_block(TimeBlock(
        block_date=DAY, start_time="", end_time="", planned_minutes=30,
        label="Old", block_type=BlockType.BREAK,
    ))
    assert _day(manager).outside == 1


def test_cipm61_an_unread_days_meetings_are_not_zero():
    from src.getmoredone.screens.plan_week_view import column_total_text, week_total_text

    unread = DaySummary(day=DAY, boxes=[(0, UNREAD)], read=False)
    read = DaySummary(day=SATURDAY, boxes=[(0, MEETING)], read=True)
    assert column_total_text(unread).splitlines()[0] == "Meetings —"
    assert week_total_text([unread, read]).startswith("Meetings ½h on 1 of 2 days")


def test_cipm61_a_column_lists_what_no_box_shows():
    from src.getmoredone.screens.plan_week_view import column_total_text

    summary = DaySummary(day=DAY, boxes=[(0, FREE)], read=True, outside=2, all_day=1)
    assert column_total_text(summary).splitlines()[2:] == ["2 outside", "1 all-day"]


def test_cipm61_a_week_with_nothing_read_has_no_meeting_total():
    from src.getmoredone.screens.plan_week_view import week_total_text

    unread = DaySummary(day=DAY, boxes=[(0, UNREAD)], read=False)
    assert week_total_text([unread]).startswith("Meetings — on 0 of 1 days")


# =====================================================================
# CIP-M6.4 -- which item colours a box (plan 2026-11-14, C1/C2)
# =====================================================================

def _item_block(manager, slot, item_id, minutes=30, day=DAY):
    from src.getmoredone.models import ActionItem, BlockType, TimeBlock

    manager.create_action_item(ActionItem(id=item_id, who="me", title=item_id, start_date=day))
    block = TimeBlock(
        block_date=day, start_time="", end_time="", planned_minutes=minutes,
        label=item_id, block_type=BlockType.ITEM, item_id=item_id,
    )
    return manager.add_block_at(block, slot, BOUNDS)


def test_cipm64_a_box_names_its_earliest_item(manager):
    """C1 -- a block carried into a box colours it before one starting there."""
    _item_block(manager, 2, "long", minutes=60)  # boxes 2 and 3
    _item_block(manager, 3, "short")
    summary = _day(manager)

    assert summary.items[2] == "long"
    assert summary.items[3] == "long", "the block starting in the box won over the one carried in"
    assert summary.grid is not None and summary.grid.span.first == 0


def test_cipm64_padding_first_colours_nothing(manager):
    """C2 -- a buffer or break before the item leaves the box uncoloured."""
    _block(manager, 2)  # a break
    _item_block(manager, 2, "after")
    summary = _day(manager)

    assert 2 not in summary.items
