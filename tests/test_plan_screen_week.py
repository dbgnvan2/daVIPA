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
    # Re-sweep (batch 3): the redraw waits for idle, as it destroys the button.
    assert list(screen._week_headers) == WEEK, "the week moved inside the click"
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
    assert screen.status_label.cget("text") == "In the week, only an Action Item can be dropped — click a day to plan it"

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


def test_cipm61_saving_settings_says_when_the_week_could_not_be_read(screen, root, monkeypatch):
    """Re-sweep (batch 3) -- a failed week is not reported as a successful save."""
    from src.getmoredone.screens import plan_week_view

    _week(screen, root)

    def broken(*_args, **_kwargs):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(plan_week_view, "read_week", broken)
    screen.on_settings_saved(BOUNDS)

    assert screen.status_label.cget("text") == (
        "Day settings saved — the week could not be read: disk gone"
    )


def test_cipm61_saving_settings_in_the_week_says_what_kept_its_time(screen, root):
    _week(screen, root)

    screen.on_settings_saved(BOUNDS, renumbered=2)

    assert screen.status_label.cget("text") == "Day settings saved — 2 blocks kept their times"


def test_cipm61_the_export_is_refused_in_the_week(screen, root):
    """Re-sweep (batch 3) -- it would export the first column's date only."""
    _week(screen, root)

    assert screen.btn_export_calendar.cget("state") == "disabled"
    screen.export_day_to_calendar()
    assert not getattr(screen, "_export_running", False)
    assert screen.status_label.cget("text") == "In the week, only an Action Item can be dropped — click a day to plan it"


def test_cipm61_leaving_the_week_mid_export_keeps_the_export_disabled(screen, root):
    _week(screen, root)
    screen._export_running = True  # an export started before the week was opened

    screen.view_toggle.set("Day")
    screen.set_view_mode("Day")

    assert screen.btn_export_calendar.cget("state") == "disabled"
    assert screen.btn_autoload.cget("state") == "normal"


def test_cipm61_an_export_ending_in_the_week_leaves_its_button_disabled(screen, root):
    _week(screen, root)

    screen._finish_export_refusal("Google Calendar is not connected")

    assert screen.btn_export_calendar.cget("state") == "disabled"


def test_cipm61_an_export_finishing_in_the_week_leaves_its_button_disabled(screen, root):
    """An export started on a day, finishing after the switch to the week."""
    from types import SimpleNamespace

    _week(screen, root)
    outcome = SimpleNamespace(
        summary_line=lambda: "Exported 1 block", failed=0, errors=[], exported=1, deleted_orphans=0,
    )

    screen._report_export(outcome)

    assert screen.btn_export_calendar.cget("state") == "disabled"
    assert screen.status_label.cget("text") == "Exported 1 block"


# =====================================================================
# Plan 2026-11-14 -- resize (M6.3), Category colours (M6.4), drop (M6.5)
# =====================================================================

from src.getmoredone.models import ActionItem  # noqa: E402
from src.getmoredone.screens import plan_week_view as wv  # noqa: E402

FRIDAY = WEEK[1]
SATURDAY = WEEK[2]


def _item(manager, title):
    item = ActionItem(who="me", title=title, start_date=THURSDAY)
    manager.create_action_item(item)
    return item


def _pointer_on_box(screen, monkeypatch, key):
    """The pointer inside the week box ``key`` (and the scroll frame), nothing else."""
    inside = {id(screen.blocks_scroll)}
    if key is not None:
        inside.add(id(screen._week_boxes[key][0]))
    monkeypatch.setattr(screen, "winfo_pointerx", lambda: 0)
    monkeypatch.setattr(screen, "winfo_pointery", lambda: 0)
    monkeypatch.setattr(wv, "widget_contains_pointer", lambda w, x, y: id(w) in inside)
    monkeypatch.setattr(
        "src.getmoredone.screens.plan.widget_contains_pointer",
        lambda w, x, y: id(w) in inside or w is screen.day_drop_frame,
    )


def _drop(screen, root, item):
    screen._drag_kind, screen._drag_item, screen._drag_block = "item", item, None
    screen.on_drag_release(None)
    root.update_idletasks()
    screen.update_idletasks()
    # block_item runs from after_idle; run the queued callbacks.
    root.update_idletasks()


def _run_idle(screen, root, monkeypatch):
    """after_idle callbacks, run at once: update() is not safe here."""
    monkeypatch.setattr(screen, "after_idle", lambda fn: fn())


def test_cipm63_columns_follow_the_pane_width(screen, root):
    _week(screen, root)

    for column in range(1, 8):
        info = screen.blocks_scroll.grid_columnconfigure(column)
        assert (info["weight"], info["uniform"], info["minsize"]) == (1, "week", wv.WEEK_COLUMN_WIDTH_PX), column
    box, _kind = screen._week_boxes[(THURSDAY, TEN)]
    assert box.grid_info()["sticky"] == "ew"


def test_cipm63_boxes_follow_the_pane_height_to_a_floor(screen, root, monkeypatch):
    _week(screen, root)
    canvas = screen._day_canvas()
    rows = screen._week_row_count

    monkeypatch.setattr(canvas, "winfo_height", lambda: 100 + rows * 32)
    assert screen.fit_week_boxes() is True
    box, _kind = screen._week_boxes[(THURSDAY, TEN)]
    assert box.cget("height") == 30
    assert screen._week_hour_labels[0].cget("height") == 30

    monkeypatch.setattr(canvas, "winfo_height", lambda: 50)
    screen.fit_week_boxes()
    assert box.cget("height") == wv.WEEK_BOX_HEIGHT_PX


def test_cipm63_an_unchanged_size_sets_nothing(screen, root, monkeypatch):
    _week(screen, root)
    canvas = screen._day_canvas()
    monkeypatch.setattr(canvas, "winfo_height", lambda: 100 + screen._week_row_count * 22)
    assert screen.fit_week_boxes() is True
    assert screen.fit_week_boxes() is False


def test_cipm63_the_week_fits_the_day_pane_floor(screen, root):
    _week(screen, root)
    labels = max([screen.week_back_button.winfo_reqwidth()]
                 + [label.winfo_reqwidth() for label in screen._week_hour_labels]) + 4
    arrows = screen.week_forward_button.winfo_reqwidth() + 4
    columns = 7 * (wv.WEEK_COLUMN_WIDTH_PX + 2)

    assert labels + columns + arrows <= screen.day_width_floor()


def test_cipm63_leaving_the_week_restores_the_columns(screen, root):
    _week(screen, root)
    screen.set_view_mode("Day")

    for column in range(1, 9):
        info = screen.blocks_scroll.grid_columnconfigure(column)
        assert (info["weight"], info["uniform"], info["minsize"]) == (0, None, 0), column
    assert screen.blocks_scroll.grid_columnconfigure(0)["weight"] == 1


def test_cipm64_an_item_box_has_its_category_colour(screen, manager, root, monkeypatch):
    item = _item(manager, "Coloured")
    _block(manager, TEN, block_type=BlockType.ITEM, item_id=item.id, label=item.title)
    monkeypatch.setattr(screen, "_segment_color_resolver",
                        lambda: lambda it: "#336699" if it.id == item.id else None)
    _week(screen, root)

    box, kind = screen._week_boxes[(THURSDAY, TEN)]
    assert kind == PLANNED
    assert box.cget("fg_color") == "#336699"


def test_cipm64_uncoloured_and_padding_keep_the_planned_token(screen, manager, root, monkeypatch):
    plain = _item(manager, "Plain")
    _block(manager, 2, block_type=BlockType.ITEM, item_id=plain.id, label=plain.title)
    _block(manager, 3)  # a break
    monkeypatch.setattr(screen, "_segment_color_resolver", lambda: lambda it: "#336699" if it is None else None)
    _week(screen, root)

    planned = wv.week_box_colors()[PLANNED]
    assert screen._week_boxes[(THURSDAY, 2)][0].cget("fg_color") == planned
    assert screen._week_boxes[(THURSDAY, 3)][0].cget("fg_color") == planned


def test_cipm65_a_drop_writes_on_the_boxs_date(screen, manager, root, monkeypatch):
    _fresh(manager)
    item = _item(manager, "Week drop")
    _week(screen, root)
    _run_idle(screen, root, monkeypatch)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))

    _drop(screen, root, item)

    written = [b for b in manager.get_time_blocks(FRIDAY) if b.item_id == item.id]
    assert [b.slot_index for b in written] == [TEN]
    assert not [b for b in manager.get_time_blocks(THURSDAY) if b.item_id == item.id]


def test_cipm65_the_refusal_reads_the_boxs_date(screen, manager, root, monkeypatch):
    _fresh(manager)
    item = _item(manager, "Twice")
    _block(manager, 2, block_date=FRIDAY, block_type=BlockType.ITEM, item_id=item.id, label=item.title)
    _week(screen, root)
    queued = []
    monkeypatch.setattr(screen, "after_idle", queued.append)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))

    _drop(screen, root, item)

    # Refused before the write is queued, from Friday's own blocks.
    assert queued == []
    assert len([b for b in manager.get_time_blocks(FRIDAY) if b.item_id == item.id]) == 1
    assert screen.status_label.cget("text").startswith("Twice is already in a Time Block")


def test_cipm65_a_meeting_box_refuses(screen, manager, root, monkeypatch):
    _fresh(manager)
    from tests.test_plan_screen_commitments import _commitment

    manager.replace_commitments_for_dates(
        [FRIDAY], [_commitment(600, 630, day=FRIDAY)], datetime.now().isoformat(timespec="seconds")
    )
    item = _item(manager, "Into a meeting")
    _week(screen, root)
    assert _kinds(screen, FRIDAY)[TEN] == MEETING
    queued = []
    monkeypatch.setattr(screen, "after_idle", queued.append)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))

    _drop(screen, root, item)

    # Refused before the write is queued, from Friday's own meetings.
    assert queued == []
    assert not [b for b in manager.get_time_blocks(FRIDAY) if b.item_id == item.id]
    assert screen.status_label.cget("text") == "A calendar event holds that Time Block — try another one"


def test_cipm65_the_week_stays_and_names_the_date(screen, manager, root, monkeypatch):
    _fresh(manager)
    item = _item(manager, "Named")
    _week(screen, root)
    _run_idle(screen, root, monkeypatch)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))

    _drop(screen, root, item)

    assert screen._week_mode is True
    assert _kinds(screen, FRIDAY)[TEN] == PLANNED
    assert screen.status_label.cget("text") == "Blocked 30m for Named on Fri 06 at 10:00"


def test_cipm65_an_unread_date_is_said(screen, manager, root, monkeypatch):
    item = _item(manager, "Unread")
    _week(screen, root)
    _run_idle(screen, root, monkeypatch)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))

    _drop(screen, root, item)

    assert screen.status_label.cget("text").endswith("— calendar not read for that day")


def test_cipm65_a_drop_on_no_box_writes_nothing(screen, manager, root, monkeypatch):
    item = _item(manager, "Missed")
    _week(screen, root)
    _run_idle(screen, root, monkeypatch)
    _pointer_on_box(screen, monkeypatch, None)

    _drop(screen, root, item)

    assert all(not [b for b in manager.get_time_blocks(d) if b.item_id == item.id] for d in WEEK)
    assert screen.status_label.cget("text") == "Drop on a box to plan it — click a day to open it"


def test_cipm65_the_question_is_about_the_boxs_date(screen, manager, root, monkeypatch):
    from src.getmoredone.screens import plan as plan_module

    asked = []
    monkeypatch.setattr(plan_module.messagebox, "askyesno",
                        lambda title, text, **kw: asked.append(text) or True)
    _fresh(manager)
    item = _item(manager, "Weekend")
    _week(screen, root)
    _run_idle(screen, root, monkeypatch)
    _pointer_on_box(screen, monkeypatch, (SATURDAY, TEN))

    _drop(screen, root, item)

    assert len(asked) == 1 and asked[0].startswith(f"{SATURDAY} is not a regular work day")
    assert SATURDAY in screen._work_anyway and THURSDAY not in screen._work_anyway
    assert [b.slot_index for b in manager.get_time_blocks(SATURDAY) if b.item_id == item.id] == [TEN]


def test_cipm65_the_box_under_the_pointer_is_outlined(screen, root, monkeypatch):
    _week(screen, root)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))
    screen._drag_kind = "item"

    screen.update_hover_target()

    assert screen._drag_hover_frame is screen._week_boxes[(FRIDAY, TEN)][0]


def test_cipm65_a_non_work_note_names_the_boxs_date(screen, manager, root, monkeypatch):
    """Sweep -- the note for a question that could not be asked names the dropped date."""
    from src.getmoredone.screens import plan as plan_module

    def refuse(*_args, **_kwargs):
        raise plan_module.tk.TclError("no dialog here")

    monkeypatch.setattr(plan_module.messagebox, "askyesno", refuse)
    _fresh(manager)
    item = _item(manager, "Saturday note")
    _week(screen, root)
    _run_idle(screen, root, monkeypatch)
    _pointer_on_box(screen, monkeypatch, (SATURDAY, TEN))

    _drop(screen, root, item)

    assert screen.status_label.cget("text").endswith(
        f"— {SATURDAY} is not a regular work day (Day Settings allows "
        "Mon, Tue, Wed, Thu, Fri)"
    )


def test_cipm65_a_date_with_unplaced_blocks_is_refused(screen, manager, root, monkeypatch):
    """Sweep -- a date never opened may hold blocks the day has not yet given a box."""
    _fresh(manager)
    _boxless_block(manager, FRIDAY)
    item = _item(manager, "Too early")
    _week(screen, root)
    queued = []
    monkeypatch.setattr(screen, "after_idle", queued.append)
    _pointer_on_box(screen, monkeypatch, (FRIDAY, TEN))

    _drop(screen, root, item)

    assert queued == []
    assert screen.status_label.cget("text") == (
        "Open Fri 06 first — 1 block(s) from an earlier version need a box"
    )
