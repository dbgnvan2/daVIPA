"""CIP batch 3 -- the Plan screen's week view.

Purpose: prove CIP-M6.1 and CIP-M6.2 on the real screen.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_week.md

Real Tk, unmapped, and a tmp_path database. The client factory is fake and the
prerequisite checks are monkeypatched, as in test_plan_screen_commitments.
``update_idletasks`` only: a full ``update`` on a second, withdrawn root spins
in Tk's macOS run loop (the cipm51 hang, 2026-11-13).
"""

from __future__ import annotations

from datetime import datetime

from src.getmoredone.models import BlockType, TimeBlock
from src.getmoredone.plan_week import FREE, MEETING, PLANNED, UNREAD, week_dates, week_summary
from src.getmoredone.screens import plan_commitments as pc
from tests.test_plan_screen_calendar_export import (
    BOUNDS,
    THURSDAY,
    _block,
    manager,  # noqa: F401 - fixture
    root,  # noqa: F401 - fixture
    settings,  # noqa: F401 - fixture
)
from tests.test_plan_screen_commitments import (  # noqa: F401 - fixtures
    TEN,
    CountingFactory,
    _event,
    _open,
    _read,
    factory,
    ready,
    screen,
)

WEEK = week_dates(THURSDAY)  # Thu 5 to Wed 11 November 2026


def _week(screen, root):
    screen.view_toggle.set("Week")
    screen.set_view_mode("Week")
    root.update_idletasks()


def _kinds(screen, day):
    return {index: kind for (d, index), (_box, kind) in screen._week_boxes.items() if d == day}


def _fresh(manager, dates=WEEK):
    manager.replace_commitments_for_dates(list(dates), [], datetime.now().isoformat(timespec="seconds"))


class RangeFactory(CountingFactory):
    """Also records the window each list call asked for."""

    def __init__(self, events=()):
        super().__init__(events)
        self.windows = []

    def list_events_between(self, time_min, time_max, calendar_id="primary"):
        self.windows.append((time_min, time_max))
        return super().list_events_between(time_min, time_max, calendar_id)


def test_cipm61_the_week_is_seven_days_from_the_selected_date(screen, root):
    _week(screen, root)

    assert list(screen._week_headers) == WEEK
    assert screen.day_heading.cget("text") == "Week Plan"
    assert screen._slot_frames == [] and screen._virtual_frames == []


def test_cipm61_refresh_fetches_the_range_once(root, manager, settings, ready):
    factory = RangeFactory([_event()])
    screen = _open(root, manager, settings, factory)
    _week(screen, root)

    assert _read(screen, root) is True

    assert factory.calls == 1
    assert len(factory.windows) == 1
    start, end = factory.windows[0]
    assert start.startswith(WEEK[0]) and end.startswith("2026-11-12")
    assert all(manager.get_commitment_fetch(day)["fetched_at"] for day in WEEK)
    assert _kinds(screen, THURSDAY)[TEN] == MEETING


def test_cipm61_week_refresh_is_refused_while_an_edit_runs(screen, root, factory):
    """W6 -- the week's read takes the same claim a meeting edit holds."""
    _week(screen, root)
    db_path = screen.db_manager.db.db_path
    assert pc.claim_refresh(db_path)
    try:
        assert _read(screen, root) is False
    finally:
        pc.release_refresh(db_path)

    assert factory.calls == 0
    assert screen.status_label.cget("text").startswith("The calendar is already being read")


def test_cipm61_an_unread_day_says_so(screen, manager, root):
    """W7 -- six dates read, one not: its boxes are unread and it has no free count."""
    _fresh(manager, WEEK[:-1])
    _week(screen, root)

    assert set(_kinds(screen, WEEK[-1]).values()) == {UNREAD, PLANNED}
    assert screen._week_totals[WEEK[-1]].cget("text").endswith("not read")
    assert FREE in _kinds(screen, THURSDAY).values()
    assert screen.calendar_age_label.cget("text").startswith("Calendar not read for 1 of 7 days")


def test_cipm61_a_non_block_day_says_no_blocks(screen, manager, root):
    """W8 -- Saturday 7 November is closed by the default Day Settings."""
    _fresh(manager)
    _week(screen, root)

    assert screen._week_totals[WEEK[2]].cget("text").endswith("no blocks")
    assert screen._week_totals[THURSDAY].cget("text").splitlines()[1].startswith("Free ")


def test_cipm61_a_click_on_a_day_opens_it(screen, root):
    _week(screen, root)

    # An unmapped widget dispatches no generated click, so the binding is
    # checked for, and the handler it names is called.
    heading = screen._week_headers[WEEK[3]]
    assert heading._label.bind("<Button-1>"), "the day heading has no click"
    screen.open_day(WEEK[3])
    root.update_idletasks()

    assert screen._week_mode is False
    assert screen.selected_date == WEEK[3]
    assert screen.view_toggle.get() == "Day"
    assert screen.day_heading.cget("text") == "Day Plan"
    assert screen._slot_frames, "the day grid was not drawn"


def test_cipm61_the_toggle_returns_to_the_same_day(screen, root):
    _week(screen, root)

    screen.view_toggle.set("Day")
    screen.set_view_mode("Day")
    root.update_idletasks()

    assert screen.selected_date == THURSDAY
    assert screen._slot_frames and screen._week_mode is False
    assert screen.day_heading.cget("text") == "Day Plan"
    # The week narrows column 0 to its time labels; the day's one column fills the pane.
    assert screen.blocks_scroll.grid_columnconfigure(0)["weight"] == 1


def test_cipm61_the_arrows_move_by_a_week(screen, root):
    _week(screen, root)

    screen.week_forward_button.invoke()
    root.update_idletasks()
    assert list(screen._week_headers) == week_dates("2026-11-12")

    screen.week_back_button.invoke()
    root.update_idletasks()
    assert list(screen._week_headers) == WEEK


def test_cipm61_opening_the_week_makes_no_call(root, manager, settings, factory, ready):
    """M5.1 -- with all seven dates fresh, nothing is read or scheduled."""
    _fresh(manager)
    screen = _open(root, manager, settings, factory)
    _week(screen, root)

    assert screen._auto_refresh_id is None
    assert factory.calls == 0


def test_cipm61_a_stale_week_is_read_once(root, manager, settings, factory, ready, monkeypatch):
    """W6 -- one unread date: one automatic read of the week, then never again."""
    _fresh(manager, WEEK[:-1])
    screen = _open(root, manager, settings, factory)
    assert screen._auto_refresh_id is None, "Thursday is fresh"
    _week(screen, root)
    assert screen._auto_refresh_id is not None
    monkeypatch.setattr(screen, "winfo_ismapped", lambda: True)

    assert screen._auto_refresh_due(THURSDAY) is True
    screen._refresh_thread.join(timeout=30)
    screen._poll_refresh()

    assert factory.calls == 1
    assert manager.get_commitment_fetch(WEEK[-1])["fetched_at"]
    assert screen._auto_refresh_due(THURSDAY) is False


def test_cipm61_leaving_the_week_cancels_its_automatic_read(root, manager, settings, factory, ready):
    """A read scheduled for the week does not survive a switch to a fresh day."""
    _fresh(manager, WEEK[:-1])
    screen = _open(root, manager, settings, factory)
    _week(screen, root)
    pending = screen._auto_refresh_id
    assert pending is not None

    screen.view_toggle.set("Day")
    screen.set_view_mode("Day")

    assert pending not in root.tk.call("after", "info"), "the week's read is still queued"
    assert screen._auto_refresh_id is None


def test_cipm61_a_day_read_does_not_stand_for_the_week(root, manager, settings, factory, ready,
                                                        monkeypatch):
    """W6 -- the week's key is its own: Thursday read alone leaves six dates to read."""
    screen = _open(root, manager, settings, factory)
    monkeypatch.setattr(screen, "winfo_ismapped", lambda: True)
    assert screen._auto_refresh_due(THURSDAY) is True
    screen._refresh_thread.join(timeout=30)
    screen._poll_refresh()

    _week(screen, root)

    assert screen._auto_refresh_due(THURSDAY) is True
    screen._refresh_thread.join(timeout=30)
    screen._poll_refresh()
    assert factory.calls == 2


def test_cipm62_the_week_column_matches_the_day_grid(screen, manager, root):
    """M6.2 -- the same date, counted from the day screen's own grid, agrees box for box."""
    _block(manager, 2)
    _block(manager, 6, minutes=60)
    manager.replace_commitments_for_dates(
        [THURSDAY], [], datetime.now().isoformat(timespec="seconds")
    )
    screen.load_blocks()
    from tests.test_plan_screen_commitments import _commitment

    manager.replace_commitments_for_dates(
        [THURSDAY], [_commitment(600, 660)], datetime.now().isoformat(timespec="seconds")
    )
    screen.load_blocks()
    day = week_summary(THURSDAY, screen._grid, BOUNDS, read=True)

    _week(screen, root)

    assert _kinds(screen, THURSDAY) == dict(day.boxes)
    assert {MEETING, PLANNED, FREE} <= set(dict(day.boxes).values())


def _boxless_block(manager, day):
    """A block from an earlier version: no box, so outside the day until placed."""
    manager.create_time_block(TimeBlock(
        block_date=day, start_time="", end_time="", planned_minutes=30,
        label="Old", block_type=BlockType.BREAK,
    ))


def test_cipm61_the_day_buttons_are_refused_in_the_week(screen, manager, root):
    """Sweep (batch 3) -- they would place by the last day's grid and meetings."""
    _week(screen, root)

    assert screen.btn_autoload.cget("state") == "disabled"
    screen.add_padding_block(BlockType.BUFFER)
    screen.autoload_day()
    assert manager.get_time_blocks(THURSDAY) == []
    assert screen.status_label.cget("text") == "The week is read-only — click a day to plan it"

    screen.view_toggle.set("Day")
    screen.set_view_mode("Day")
    assert screen.btn_autoload.cget("state") == "normal"
    screen.add_padding_block(BlockType.BUFFER)
    assert len(manager.get_time_blocks(THURSDAY)) == 1


def test_cipm61_saving_settings_in_the_week_counts_the_week(screen, manager, root):
    """Sweep (batch 3) -- not the grid of a day that is not on screen."""
    _boxless_block(manager, WEEK[1])
    _week(screen, root)

    screen.on_settings_saved(BOUNDS)

    assert screen.status_label.cget("text").startswith("Day settings saved — 1 block this week")
    assert screen._week_totals[WEEK[1]].cget("text").splitlines()[-1] == "1 outside"


def test_cipm61_a_column_click_opens_the_day_after_the_click(screen, root):
    """Sweep (batch 3) -- the redraw destroys the clicked widget, so it waits for idle."""
    _week(screen, root)

    class Recorder:
        def bind(self, sequence, callback):
            self.callback = callback

    widget = Recorder()
    screen._bind_open(widget, WEEK[3])
    widget.callback(None)
    assert screen._week_mode is True, "the day opened inside the click"

    root.update_idletasks()
    assert screen._week_mode is False and screen.selected_date == WEEK[3]
