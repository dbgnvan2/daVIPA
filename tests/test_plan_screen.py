"""TB-M5 to TB-M12 — the Plan screen's controls, wired to the database.

Purpose: prove each control does the thing it claims, against real widgets and
         a real database, rather than merely being rendered.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md
Tests:   this file

Real Tk, because a control that is drawn and not connected is exactly the
failure this screen had before: a free-text date entry, an unfiltered list and
a dialog whose Save wrote a block nobody could reach (P25 — a check reachable
from only one surface, and not the one anyone uses).

The windows are withdrawn by conftest, so a run does not throw modals over
whatever the user is doing. ``winfo_width()`` on a withdrawn window returns 1,
so the tests that read real geometry -- and only those -- ask for the
``mapped_windows`` fixture. A test that reads ``cget`` or a grid option does
not need a mapped window, and taking the fixture anyway means it is skipped in
the local workflow CLAUDE.md documents, which is where the wiring it proves
most needs to be proved.
"""

from __future__ import annotations

import logging
import re
import tkinter as tk
import _tkinter

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.color_contrast import contrast_ratio, pick_text_color
from src.getmoredone.screens.plan import (
    ITEMS_TEXT_INSET_PX,
    NOTE_MIN_WRAP_PX,
    OUTSIDE_GROUP_HEIGHT_PX,
    PD_AUTOSCROLL_INTERVAL_MS,
    PD_AUTOSCROLL_MARGIN_PX,
    PD_AUTOSCROLL_STEP_PX,
    PLAN_DIVIDER_WIDTH_PX,
    PLAN_ITEMS_COL_WIDTH_PX,
    PLAN_PANE_CHROME_PX,
    PLAN_PANE_EDGE_PAD_PX,
    REFUSAL_TEXT,
    RIGHT_CLICK_SEQUENCES,
    PlanScreen,
    refusal_text,
)
from src.getmoredone.screens.plan_blocks import (
    CHIP_BARS_COLUMN,
    CHIP_LENGTH_COLUMN,
    CHIP_MARKER_COLUMN,
    CHIP_RIGHT_INSET_PX,
    ITEM_ROW_MIN_HEIGHT_PX,
    PD_BLOCKED_TEXT,
    PD_UNSCHEDULED_TEXT,
    PD_CHECK_TEXT,
    PD_EARLIER_HINT,
    PD_EARLIER_TEXT,
    PD_LATER_HINT,
    PD_LATER_TEXT,
    STRIPE_WIDTH_PX,
    SLOT_CHIP_HEIGHT_PX,
    SLOT_LENGTH_WIDTH_PX,
    SLOT_MIN_HEIGHT_PX,
    SLOT_ROW_GAP_PX,
    SLOT_MARKER_WIDTH_PX,
    SLOT_TITLE_WIDTH_PX,
    DepthBarStack,
    accent_for_block,
    accent_for_item,
    build_item_row,
    build_outside_group,
    build_slot_row,
    chip_column_minsizes,
    fill_for_item,
    item_row_height,
    slot_row_height,
    stripe_for_item,
)
from src.getmoredone.screens.plan_settings_dialog import PlanSettingsDialog
from src.getmoredone.theme import (
    block_type_colors,
    priority_band_colors,
    semantic_colors,
    status_text_color,
)
from src.getmoredone.time_block_layout import (
    MAX_BLOCKS_PER_SLOT,
    MAX_DEPTH_BARS,
    SLOT_MINUTES,
    DayBounds,
    DAY_EXTEND_EARLIER,
    DAY_EXTEND_LATER,
    SlotRefusal,
    SlotRefusedError,
    build_day_grid,
    day_grid,
    priority_band,
    slots_for_minutes,
)

THURSDAY = "2026-11-05"
SATURDAY = "2026-11-07"
FRIDAY = "2026-11-06"


class _App:
    """The slice of the app object PlanScreen actually reads."""

    def __init__(self, settings):
        self.settings = settings


@pytest.fixture
def manager(tmp_path):
    """Every DatabaseManager in this suite gets an explicit tmp_path database.

    The default path resolves to the user's real application database, and
    __init__ runs migrations against it.
    """
    db = DatabaseManager(str(tmp_path / "plan.db"))
    yield db
    db.close()


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Settings that save to tmp_path, never to the user's real settings file."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))
    return AppSettings()


@pytest.fixture
def root():
    window = ctk.CTk()
    yield window
    window.destroy()


@pytest.fixture
def light_appearance():
    """Pin the appearance mode, so a colour assertion is not host-dependent.

    Nothing in this file sets a mode, so CustomTkinter resolved ``"System"``
    and the colour tests asserted against whichever theme the machine running
    them happened to be in. ``test_pbm1_an_item_rows_stripe_uses_the_brighter
    _table`` was the one that could fail for it: the stripe table is a
    *different* table from the band table only in light mode -- in dark mode
    the two are deliberately equal -- so that test passed on a light-mode Mac
    and would have failed against correct code on a dark-mode one.

    The restore goes back to ``"system"`` when that is what was in force
    rather than to ``get_appearance_mode()``, which returns the *resolved*
    mode: saving and re-setting that would quietly convert "follow the OS"
    into a fixed mode for every test collected after this one.
    """
    was_system = ctk.AppearanceModeTracker.appearance_mode_set_by == "system"
    previous = ctk.get_appearance_mode()
    ctk.set_appearance_mode("light")
    try:
        yield
    finally:
        ctk.set_appearance_mode("system" if was_system else previous)


@pytest.fixture
def screen(root, manager, settings):
    """A Plan screen on the default Thursday, with real widgets."""
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()
    return panel


def _item(manager, title, start_date=THURSDAY, **kwargs):
    item = ActionItem(who="me", title=title, start_date=start_date, **kwargs)
    manager.create_action_item(item)
    return item


def _scored_item(manager, title, band="critical", **kwargs):
    """An item that is really in a priority band after the database has it.

    ``_item(..., priority_score=51200)`` does not produce a scored item.
    ``create_action_item`` calls ``update_priority_score``, which multiplies the
    four factors and returns 0 when any of them is None -- so the item came back
    ``unscored`` and every colour assertion written against it compared the
    unscored grey with the unscored grey. 51200 is a real critical score
    (20 x 20 x 16 x 8); it was only ever being thrown away.

    The resulting band is asserted here rather than left to the caller, so this
    helper cannot start handing back unscored items without a test failing on
    the spot.
    """
    factors = {
        "critical": dict(importance=20, urgency=20, size=16, value=8),   # 51200
    }[band]
    item = _item(manager, title, **factors, **kwargs)
    assert item.priority_score > 0, (
        f"{title!r} came back from the database scoring "
        f"{item.priority_score!r} -- the factors did not take"
    )
    assert priority_band(item.priority_score) == band, (
        f"{title!r} scores {item.priority_score}, which is band "
        f"{priority_band(item.priority_score)!r}, not {band!r}"
    )
    return item


def _add_block(
    manager,
    minutes,
    label,
    slot_index,
    block_date=THURSDAY,
    bounds=None,
    outside_range=False,
    **kwargs,
):
    """Put a block on a box, the way every screen path now does.

    ``slot_index`` is required rather than defaulted: a day's shape is the
    thing under test in most of this file, and a test that did not say where
    its blocks were would be asserting against whatever box the helper chose.

    ``outside_range`` is spelled out at the call site on purpose. A box outside
    the day as drawn is refused for every write but the Earlier/Later extension
    (PD-M13), so a helper that passed it quietly would let a test build a day
    the app itself would not have allowed, and that day is where the
    assertions would then come from. ``bounds`` is for the same kind of
    honesty: a day written under a different Day Start, which is what a
    database from before this change holds.
    """
    block = TimeBlock(
        block_date=block_date,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        **kwargs,
    )
    return manager.add_block_at(
        block,
        slot_index,
        bounds if bounds is not None else DayBounds(),
        allow_outside_range=outside_range,
    )


def _unplaced(manager, *labels, first_hour=17, block_date=THURSDAY):
    """Rows the grid has no box for, which is what "outside the day" now means.

    PD-M13 left exactly one way for a block to be outside the drawn day: a
    pre-grid row whose stored clock time falls outside the configured range,
    which ``adopt_unplaced_blocks`` refuses to invent a box for and leaves
    ``NULL`` (P2 -- surfaced, never dropped). Narrowing Day End no longer does
    it, because the drawn day widens past the configured range to cover
    whatever is still planned out there, so every test that used to orphan a
    block by shrinking the day builds one of these instead.
    """
    for offset, label in enumerate(labels):
        hour, half = divmod(first_hour * 2 + offset, 2)
        start = f"{hour:02d}:{30 if half else 0:02d}"
        manager.create_time_block(
            TimeBlock(
                block_date=block_date,
                start_time=start,
                end_time=start,
                planned_minutes=30,
                label=label,
            )
        )


def _stored(manager, block_date=THURSDAY):
    return [
        (b.label, b.slot_index, b.position, b.start_time, b.end_time, b.planned_minutes)
        for b in manager.get_time_blocks(block_date)
    ]


def _slot_frames(panel):
    """The rendered boxes, as the screen recorded them."""
    return list(panel._slot_frames)


def _label_texts(widget):
    """Every label text under a widget, however deeply nested.

    A box holds a chip per task and a chip holds the title, so a walk one level
    deep sees only the clock times down the left edge.
    """
    found = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            found.append(child.cget("text"))
        found.extend(_label_texts(child))
    return found


# --- TB-M5 : the settings modal ---------------------------------------------

def test_tbm51_settings_modal_writes_day_settings(root, settings):
    """TB-M5.1 — all four times, the lunch length and the seven flags, saved."""
    dialog = PlanSettingsDialog(root, settings)
    try:
        dialog.day_start_entry.delete(0, tk.END)
        dialog.day_start_entry.insert(0, "07:30")
        dialog.lunch_start_entry.delete(0, tk.END)
        dialog.lunch_start_entry.insert(0, "11:45")
        dialog.lunch_minutes_entry.delete(0, tk.END)
        dialog.lunch_minutes_entry.insert(0, "45")
        dialog.day_end_entry.delete(0, tk.END)
        dialog.day_end_entry.insert(0, "18:00")
        for index, var in enumerate(dialog.weekday_vars):
            var.set(index in (0, 2, 4))  # Mon, Wed, Fri only

        dialog.save()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()

    assert settings.plan_day_start == "07:30"
    assert settings.plan_lunch_start == "11:45"
    assert settings.plan_lunch_minutes == 45
    assert settings.plan_day_end == "18:00"
    assert settings.plan_block_weekdays == [
        True, False, True, False, True, False, False,
    ]


def test_the_modal_offers_exactly_seven_weekday_checkboxes(root, settings):
    """"Days for Blocks (7 check boxes)" — asserted as an exact count."""
    dialog = PlanSettingsDialog(root, settings)
    try:
        assert len(dialog.weekday_vars) == 7
    finally:
        dialog.destroy()


@pytest.mark.parametrize(
    "field, value, expected_message",
    [
        ("day_start_entry", "9am", "Day Start must be a time like 09:00"),
        ("lunch_start_entry", "", "Lunch Start must be a time like 09:00"),
        ("day_end_entry", "25:99", "Day End must be a time like 09:00"),
        # Found by the pre-push sweep. The minutes in "25:99" are what made
        # that case fail; the hours never were. "25:00" was accepted and
        # stored, which puts Day End past every block the planner can make, so
        # the overrun warning that is Day End's only job could never fire
        # again. "170:0" was worse: format_hhmm clamped it to "99:59", storing
        # a value the user never typed -- the one thing this dialog validates
        # rather than falling back in order to avoid.
        ("day_end_entry", "24:00", "Day End must be a time like 09:00"),
        ("day_end_entry", "25:00", "Day End must be a time like 09:00"),
        ("day_end_entry", "170:0", "Day End must be a time like 09:00"),
        ("day_start_entry", "99:59", "Day Start must be a time like 09:00"),
    ],
)
def test_the_modal_names_the_field_it_cannot_read(root, settings, field, value, expected_message):
    """A user typing "9am" is told, not silently corrected.

    The settings *file* falls back silently, because the alternative is an app
    that will not start. A person typing into a box is a different case:
    substituting a value under their hands is how a planner teaches someone to
    distrust it.
    """
    dialog = PlanSettingsDialog(root, settings)
    try:
        entry = getattr(dialog, field)
        entry.delete(0, tk.END)
        entry.insert(0, value)

        dialog.save()

        assert dialog.winfo_exists(), "an invalid day must not close the dialog"
        assert dialog.error_label.cget("text") == expected_message
        assert settings.plan_day_start == "08:00", "nothing should have been written"
    finally:
        if dialog.winfo_exists():
            dialog.destroy()


def test_the_modal_accepts_the_last_minute_of_the_day(root, settings):
    """The boundary the hours-past-midnight refusal is written against.

    Paired with the cases above so a guard that refused every time would not
    pass for the right reason.
    """
    dialog = PlanSettingsDialog(root, settings)
    try:
        dialog.day_end_entry.delete(0, tk.END)
        dialog.day_end_entry.insert(0, "23:59")

        dialog.save()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()

    assert settings.plan_day_end == "23:59"


def test_the_modal_refuses_a_day_that_ends_before_it_starts(root, settings):
    dialog = PlanSettingsDialog(root, settings)
    try:
        dialog.day_end_entry.delete(0, tk.END)
        dialog.day_end_entry.insert(0, "06:00")

        dialog.save()

        assert dialog.error_label.cget("text") == "Day End must be after Day Start"
        assert dialog.winfo_exists()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()


def test_the_modal_refuses_a_week_with_no_block_days(root, settings):
    """Not cosmetic: with no block days every drop is refused.

    The planner would look broken rather than configured, with nothing on
    screen to explain why.
    """
    dialog = PlanSettingsDialog(root, settings)
    try:
        for var in dialog.weekday_vars:
            var.set(False)

        dialog.save()

        assert dialog.error_label.cget("text") == "At least one day must accept blocks"
        assert dialog.winfo_exists()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()


# --- TB-M6 : the date picker -------------------------------------------------

def test_tbm61_date_change_reloads_both_panes(screen, manager):
    """TB-M6.1 — the picker drives the item list and the block list together."""
    _item(manager, "thursday item", THURSDAY)
    _item(manager, "friday item", FRIDAY)
    _add_block(manager, 30, "thursday block", 0, block_date=THURSDAY)
    _add_block(manager, 30, "friday block", 0, block_date=FRIDAY)

    screen.on_date_changed(FRIDAY)

    assert screen.selected_date == FRIDAY
    assert [i.title for i in screen._items] == ["friday item"]
    assert [
        block.label for entry in screen._grid.slots for block in entry.starting
    ] == ["friday block"]


def test_the_date_is_a_picker_not_a_free_text_entry(screen):
    """The free-text entry accepted a typo and wrote blocks under a non-date.

    Asserted on the widget's own contract: a DatePickerButton validates and
    normalises, and the screen follows it -- which is the behaviour being
    bought here.

    Two earlier versions of this test were wrong in different ways. The first
    compared the picker against a date the fixture had assigned behind it; the
    picker is built from ``date.today()`` in ``__init__``, so the two agreed
    only on the day it was written and it went red at the first midnight. The
    second moved the date with ``set_date`` and then called
    ``screen.on_date_changed`` itself -- but ``set_date`` already fires that
    callback, so the test was satisfying its own assertion, and removing the
    screen's ``on_date_changed=`` wiring left it green.

    ``set_date`` is given a ``date`` object, not a string, so the normalising
    the docstring claims is the thing being asserted rather than asserted of an
    input that needed none.
    """
    from datetime import date as date_type

    from src.getmoredone.widgets.date_picker import DatePickerButton

    # Deliberately nowhere near today, so nothing here can pass by calendar
    # accident.
    a_later_day = date_type(2027, 3, 3)

    assert isinstance(screen.date_picker, DatePickerButton)

    screen.date_picker.set_date(a_later_day)

    assert screen.date_picker.get_date() == "2027-03-03", (
        "the picker did not normalise the date it was given"
    )
    assert screen.selected_date == "2027-03-03", (
        "the screen is not wired to the picker: setting the date on the control"
        " did not reach the screen"
    )


# --- TB-M7 : the items pane --------------------------------------------------

def test_tbm71_item_list_matches_selected_date(screen, manager):
    """TB-M7.1 — exactly the items starting on the selected date."""
    _item(manager, "on the day", THURSDAY)
    _item(manager, "day before", "2026-11-04")
    _item(manager, "day after", FRIDAY)

    screen.load_items()

    assert [i.title for i in screen._items] == ["on the day"]


def test_the_item_pane_says_why_an_empty_list_may_be_empty(screen, manager):
    """The exact-date filter's consequence, where the user meets it.

    An item with the wrong start date does not appear, and the planner cannot
    warn about work it cannot see — so the empty state says what the list is
    filtered on.
    """
    screen.load_items()

    texts = [
        child.cget("text")
        for child in screen.items_scroll.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
    assert any("Start Date" in text for text in texts)


def test_the_item_cap_announces_what_it_drops(screen, manager):
    """P2 — a cap on core input says "N of M" rather than applying silently.

    The old screen capped at 50 with nothing on screen to say so.
    """
    from src.getmoredone.screens.plan import MAX_ITEM_ROWS

    for index in range(MAX_ITEM_ROWS + 3):
        _item(manager, f"item {index:03d}", THURSDAY)

    screen.load_items()

    hint = screen.items_hint.cget("text")
    assert f"Showing {MAX_ITEM_ROWS} of {MAX_ITEM_ROWS + 3}" in hint


def test_an_uncapped_list_does_not_claim_to_be_capped(screen, manager):
    _item(manager, "only item", THURSDAY)

    screen.load_items()

    assert "Showing" not in screen.items_hint.cget("text")


# --- TB-M8 : drag an item to make a block -----------------------------------

def test_tbm81_drop_creates_block_using_work_block(screen, manager):
    """TB-M8.1 — requirement 8: the item's Work Block becomes the block length."""
    item = _item(manager, "deep work", THURSDAY, work_block=90)

    screen.block_item(item)

    blocks = manager.get_time_blocks(THURSDAY)
    assert len(blocks) == 1
    assert blocks[0].planned_minutes == 90
    assert blocks[0].item_id == item.id
    assert blocks[0].block_type == BlockType.ITEM


def test_an_item_without_a_work_block_gets_the_default_30(screen, manager):
    """Requirement 4's "default to 30 minutes", on the create path."""
    item = _item(manager, "ordinary", THURSDAY)

    screen.block_item(item)

    assert manager.get_time_blocks(THURSDAY)[0].planned_minutes == 30


def test_a_created_block_is_given_its_clock_times_immediately(screen, manager):
    """A block with no times stored would render as "–" until something repacked."""
    item = _item(manager, "first", THURSDAY, work_block=60)

    screen.block_item(item)

    (block,) = manager.get_time_blocks(THURSDAY)
    assert (block.start_time, block.end_time) == ("08:00", "09:00")


def test_tbm82_drop_on_non_block_day_is_refused(root, manager, settings):
    """TB-M8.2 — an unchecked weekday creates no block, and says why.

    2026-11-07 is a Saturday, which the default settings exclude. Refused with
    the reason on screen: a drop that does nothing and says nothing is
    indistinguishable from a drag that missed.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "weekend work", SATURDAY)

    panel.block_item(item)

    assert manager.get_time_blocks(SATURDAY) == []
    status = panel.status_label.cget("text")
    assert "not a block day" in status
    assert "Mon, Tue, Wed, Thu, Fri" in status


def test_a_weekend_accepts_blocks_once_it_is_checked(root, manager, settings):
    settings.plan_block_weekdays = [True] * 7
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "weekend work", SATURDAY)

    panel.block_item(item)

    assert len(manager.get_time_blocks(SATURDAY)) == 1


def test_pdm7_a_non_work_day_asks_before_scheduling(
    root, manager, settings, monkeypatch
):
    """PD-M7 — a day outside the working week is a warning, not a wall.

    The screen opens on today, so on a weekend every write path returned
    before doing anything: AutoLoad before it read an item, a dropped item
    before it wrote one. Four gestures doing nothing read as the screen being
    broken. The weekday list describes a normal week; it does not get a veto
    over a Saturday someone has decided to work.
    """
    asked = []

    def say_yes(*args, **kwargs):
        asked.append((args[0], args[1]))
        return True

    monkeypatch.setattr("tkinter.messagebox.askyesno", say_yes)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "weekend work", SATURDAY)

    panel.block_item(item)

    assert len(asked) == 1, f"the drop asked {len(asked)} times, not once: {asked}"
    title, message = asked[0]
    assert "work day" in title.lower(), title
    assert SATURDAY in message, message
    assert "Mon, Tue, Wed, Thu, Fri" in message, message
    assert "Schedule anyway?" in message, message
    assert len(manager.get_time_blocks(SATURDAY)) == 1, (
        "the user said to schedule it and nothing was written"
    )


def test_pdm7_the_question_is_asked_once_per_date(
    root, manager, settings, monkeypatch
):
    """One decision about the day, not one per item dropped on it."""
    asked = []
    monkeypatch.setattr(
        "tkinter.messagebox.askyesno",
        lambda *a, **k: asked.append(1) or True,
    )
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    first = _item(manager, "first", SATURDAY)
    second = _item(manager, "second", SATURDAY)

    panel.block_item(first)
    panel.block_item(second)

    assert len(asked) == 1, f"two drops onto one Saturday asked {len(asked)} times"
    assert len(manager.get_time_blocks(SATURDAY)) == 2, (
        "the second drop was refused on a day already allowed"
    )


def test_pdm7_answering_no_writes_nothing(
    root, manager, settings, messageboxes
):
    """No means no, and the reason stays on screen.

    ``askyesno`` answers False under the suite's own stub, so this is the
    declining path without patching anything: the sentence is the one the flat
    refusal used to leave, because the answer to "why did nothing happen" is
    the days the week is set to.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "weekend work", SATURDAY)

    panel.block_item(item)

    assert [name for name, _, _ in messageboxes] == ["askyesno"], messageboxes
    assert manager.get_time_blocks(SATURDAY) == []
    status = panel.status_label.cget("text")
    assert "not a block day" in status
    assert "Mon, Tue, Wed, Thu, Fri" in status


def test_pdm7_a_work_day_asks_nothing(screen, manager, messageboxes):
    """The question is for the exception, so a Thursday must not see it."""
    item = _item(manager, "ordinary Thursday work")

    screen.block_item(item)

    assert messageboxes == [], f"a work day asked anyway: {messageboxes}"
    assert len(manager.get_time_blocks(THURSDAY)) == 1


def test_pdm8_the_header_has_a_clear_day_button(screen):
    """PD-M8 — reachable from the screen, not only from a test.

    A method no button calls is a feature nobody has (P25): the whole of this
    ask was a button, and ``clear_day`` was written before it had one.
    """
    assert screen.btn_clear_day.cget("text") == "Clear Day", (
        screen.btn_clear_day.cget("text")
    )
    assert screen.btn_clear_day.cget("command") == screen.clear_day, (
        "the Clear Day button does not call clear_day"
    )
    assert screen.btn_clear_day.master is screen.btn_autoload.master, (
        "Clear Day is not in the header beside AutoLoad"
    )
    assert (
        screen.btn_clear_day.cget("fg_color")
        != screen.btn_autoload.cget("fg_color")
    ), (
        "the destructive button is the same colour as the primary one, so a "
        "misclick looks like the button the user meant"
    )


def test_pdm8_clear_day_removes_every_item_block(
    root, manager, settings, monkeypatch
):
    """PD-M8 — the reverse of AutoLoad: the day's tasks come back off it.

    The count is in the question, so the answer is given against the real day
    rather than against the word "all".
    """
    asked = []

    def say_yes(*args, **kwargs):
        asked.append((args[0], args[1]))
        return True

    monkeypatch.setattr("tkinter.messagebox.askyesno", say_yes)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(manager, 30, "First", 0, block_type=BlockType.ITEM)
    _add_block(manager, 30, "Second", 1, block_type=BlockType.ITEM)

    panel.clear_day()

    assert len(asked) == 1, f"Clear Day asked {len(asked)} times, not once"
    title, message = asked[0]
    assert "clear day" in title.lower(), title
    assert "2 scheduled items" in message, message
    assert THURSDAY in message, message
    assert "cannot be undone" in message, message
    assert manager.get_time_blocks(THURSDAY) == [], (
        "the day still holds blocks after Clear Day"
    )
    assert "removed 2 of 2" in panel.status_label.cget("text"), (
        panel.status_label.cget("text")
    )


def test_pdm8_clear_day_leaves_breaks_and_buffers(
    root, manager, settings, monkeypatch
):
    """PD-M8 — it is the reverse of AutoLoad, and AutoLoad writes no breaks.

    A break or a buffer was put there by hand, one gesture each, so taking
    them out would be a deletion nobody asked for. The question says how many
    are staying, because a button called Clear Day that leaves two blocks
    behind has to account for them where the user is looking.
    """
    asked = []

    def say_yes(*args, **kwargs):
        asked.append((args[0], args[1]))
        return True

    monkeypatch.setattr("tkinter.messagebox.askyesno", say_yes)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(manager, 30, "Draft the proposal", 0, block_type=BlockType.ITEM)
    _add_block(manager, 30, "Break", 1, block_type=BlockType.BREAK)
    _add_block(manager, 30, "Buffer", 2, block_type=BlockType.BUFFER)

    panel.clear_day()

    left = [(b.label, b.block_type) for b in manager.get_time_blocks(THURSDAY)]
    assert left == [("Break", BlockType.BREAK), ("Buffer", BlockType.BUFFER)], (
        f"Clear Day took the wrong blocks: {left} left"
    )
    assert "2 break and buffer blocks stay" in asked[0][1], asked[0][1]
    said = panel.status_label.cget("text")
    assert "removed 1 of 3" in said and "2 break and buffer" in said, said


def test_pdm8_answering_no_removes_nothing(
    root, manager, settings, messageboxes
):
    """PD-M8 — No leaves the day alone and says so.

    ``askyesno`` answers False under the suite's own stub, so this is the
    declining path with nothing patched.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(manager, 30, "Draft the proposal", 0, block_type=BlockType.ITEM)

    panel.clear_day()

    assert [name for name, _, _ in messageboxes] == ["askyesno"], (
        f"Clear Day did not ask before deleting: {messageboxes}"
    )
    assert len(manager.get_time_blocks(THURSDAY)) == 1, (
        "the block was deleted though the question was answered No"
    )
    assert "nothing removed" in panel.status_label.cget("text"), (
        panel.status_label.cget("text")
    )


def test_pdm8_a_day_with_no_items_says_so_and_asks_nothing(
    root, manager, settings, messageboxes
):
    """PD-M8 — nothing to remove is not a question, it is an answer.

    A break on the day and no items: the day is not empty, and the sentence
    has to be about items rather than about blocks.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(manager, 30, "Break", 0, block_type=BlockType.BREAK)

    panel.clear_day()

    assert messageboxes == [], f"it asked about a day with no items: {messageboxes}"
    assert len(manager.get_time_blocks(THURSDAY)) == 1, "the break was removed"
    said = panel.status_label.cget("text")
    assert "nothing to remove" in said and "no items" in said, said


def test_pdm8_clear_day_asks_nothing_about_the_weekday_list(
    root, manager, settings, monkeypatch
):
    """PD-M8 — taking work off a day is not planning work onto it.

    A Saturday that was filled -- by a Yes to PD-M7, or before the week was
    narrowed -- has to be clearable without being asked about the week again.
    So the only question Clear Day asks on a Saturday is its own.
    """
    asked = []

    def say_yes(*args, **kwargs):
        asked.append((args[0], args[1]))
        return True

    monkeypatch.setattr("tkinter.messagebox.askyesno", say_yes)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    _add_block(
        manager, 30, "weekend work", 0,
        block_date=SATURDAY, block_type=BlockType.ITEM,
    )

    panel.clear_day()

    assert [title for title, _ in asked] == ["Clear Day"], (
        f"Clear Day on a Saturday asked: {[t for t, _ in asked]}"
    )
    assert manager.get_time_blocks(SATURDAY) == [], (
        "the Saturday was not cleared"
    )


def test_pdm13_a_settings_save_does_not_blame_itself_for_an_old_unplaced_row(
    screen, manager
):
    """The "no longer fit the day" line has to be about what the save did.

    Found while retargeting the outside-group tests. That sentence was written
    when narrowing the day was the one way a block came off the grid, and it
    fired on any non-empty outside group after a save. Under PD-M13 a save
    cannot orphan anything -- the drawn day widens past the configured range --
    so on any day holding a pre-grid row the user saved Day Settings and was
    told their save had just displaced a block it had nothing to do with.

    The warning is kept for the case it was written for, which is why the
    assertion is on the *wording* and not on the absence of a warning: if
    anything ever does orphan a block again, the user is still told.
    """
    _unplaced(manager, "never placed")
    screen.load_blocks()
    assert len(screen._grid.outside) == 1, "precondition: the row has no box"

    screen.on_settings_saved(DayBounds(day_end="16:00"))

    text = screen.status_label.cget("text")
    assert "no longer fit" not in text, text
    assert text == "Day settings saved", text
    assert [b.label for b in screen._grid.outside] == ["never placed"], (
        "the row stopped being reported at all, which is the P2 failure"
    )


# ================= PD-M14 — either end takes a drop, whatever is near =====
#
# The user's second fault: "User should be able to drag to the Early or Late
# Block regardless if anything is after the Morning block or before the Evening
# block." There is no adjacency guard in the source to remove -- the two rows
# are built on every redraw and the only refusals on the path are the weekday
# gate and midnight -- so these tests exist to establish that and to fail if
# anybody adds one. The gesture itself, with a pointer, is checklist item 2
# (PD-M14.4): nothing here drives a real pane.


def test_pdm141_an_earlier_drop_onto_an_empty_day_schedules(screen, manager):
    """PD-M14.1 — nothing is scheduled, so nothing can be "adjacent" to it.

    The first box of the day is also the last one, and a guard keyed on either
    would refuse the one day where the gesture is most obviously wanted.
    """
    item = _item(manager, "Early start")

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert [(row[0], row[1]) for row in _stored(manager)] == [("Early start", -1)], (
        _stored(manager)
    )


def test_pdm142_an_earlier_drop_ignores_what_is_at_the_other_end(screen, manager):
    """PD-M14.2 — a block at the last box is not next to the Earlier row.

    The fault as reported, in the direction it was reported in: work sitting
    late in the day must not have any bearing on a drop at the early end.
    """
    last = len(day_grid(screen.bounds)) - 1
    _add_block(manager, 30, "end of day", last)
    item = _item(manager, "Early start")

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    placed = {row[0]: row[1] for row in _stored(manager)}
    assert placed == {"end of day": last, "Early start": -1}, placed


def test_pdm143_a_later_drop_ignores_what_is_at_the_other_end(screen, manager):
    """PD-M14.3 — and the mirror of it: box 0 is not next to the Later row."""
    _add_block(manager, 30, "start of day", 0)
    item = _item(manager, "Late finish")
    boxes = len(day_grid(screen.bounds))

    screen.extend_day_for(item, DAY_EXTEND_LATER)

    placed = {row[0]: row[1] for row in _stored(manager)}
    assert placed == {"start of day": 0, "Late finish": boxes}, placed


# ================= PD-M15 — the work-day warning, once per date ===========
#
# The user's third fault: "You are simply ignoring the Work day settings and
# letting me schedule on a NON checked Day. Warning happens once on the first
# block." Asked whether an unchecked day should be warned about once a day or
# refused outright, they chose warned once per day -- which is the behaviour
# that is already there, so PD-M15 is these tests over it rather than new code.
# The question reaching a real dialog is checklist item 3 (PD-M15.6).


def test_pdm151_every_write_path_asks_on_an_unchecked_day(
    root, manager, settings, monkeypatch
):
    """PD-M15.1 — all four, named one at a time.

    Named individually and counted, so a fifth writer added later -- or one of
    these four having its gate removed -- fails here rather than being found by
    the user on a Saturday. Each path gets its own screen, because the answer
    is cached per date for the life of the screen and a shared one would let
    three of the four coast on the first one's yes.
    """
    item = _item(manager, "weekend work", SATURDAY)

    def gesture_padding(panel):
        panel.add_padding_block(BlockType.BREAK)

    def gesture_item(panel):
        panel.block_item(item)

    def gesture_autoload(panel):
        panel.autoload_day()

    def gesture_extension(panel):
        panel.extend_day_for(item, DAY_EXTEND_LATER)

    paths = {
        "add_padding_block": gesture_padding,
        "block_item": gesture_item,
        "autoload_day": gesture_autoload,
        "extend_day_for": gesture_extension,
    }
    asked = {}
    for name, gesture in paths.items():
        count = []
        monkeypatch.setattr(
            "tkinter.messagebox.askyesno",
            lambda *a, **k: count.append(1) or False,
        )
        panel = PlanScreen(root, manager, _App(settings))
        panel.selected_date = SATURDAY
        panel.refresh()
        gesture(panel)
        asked[name] = len(count)

    assert asked == {name: 1 for name in paths}, asked
    assert manager.get_time_blocks(SATURDAY) == [], (
        "a path wrote to the Saturday after the question was declined"
    )


def test_pdm152_the_day_off_question_is_asked_once_per_date(
    root, manager, settings, monkeypatch
):
    """PD-M15.2 — "once per day" across paths, not once per path.

    ``test_pdm7_the_question_is_asked_once_per_date`` already covers two drops
    through the same path. This is the user's wording -- one warning on the
    first block, and nothing after it -- which only holds if the four paths
    share the one answer rather than each asking its own first question.
    """
    asked = []
    monkeypatch.setattr(
        "tkinter.messagebox.askyesno", lambda *a, **k: asked.append(1) or True
    )
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "weekend work", SATURDAY)

    panel.block_item(item)
    panel.add_padding_block(BlockType.BREAK)
    panel.extend_day_for(_item(manager, "late one", SATURDAY), DAY_EXTEND_LATER)
    panel.autoload_day()

    assert len(asked) == 1, f"four gestures on one Saturday asked {len(asked)} times"
    assert len(manager.get_time_blocks(SATURDAY)) >= 3, (
        f"a gesture after the first was refused: {_stored(manager, SATURDAY)}"
    )


def test_pdm153_breaks_on_the_day_do_not_re_arm_the_question(
    root, manager, settings, monkeypatch
):
    """PD-M15.3 — the user's parenthetical, answered "No, once per day".

    They wondered whether a day holding only breaks and buffers should be
    asked about again. It is not: the question is keyed on the date and reads
    nothing about what is on the day, so filling the Saturday with padding
    cannot bring it back. Pinned because a later change that keyed it on the
    day's contents would be a warning per block, which is the fault this item
    was reported as.
    """
    asked = []
    monkeypatch.setattr(
        "tkinter.messagebox.askyesno", lambda *a, **k: asked.append(1) or True
    )
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()

    panel.add_padding_block(BlockType.BREAK)
    panel.add_padding_block(BlockType.BUFFER)
    panel.add_padding_block(BlockType.BREAK)

    assert len(asked) == 1, (
        f"three padding blocks on one Saturday asked {len(asked)} times"
    )
    assert len(manager.get_time_blocks(SATURDAY)) == 3, _stored(manager, SATURDAY)


def test_pdm154_a_break_on_the_day_does_not_refuse_an_item(
    root, manager, settings, monkeypatch
):
    """PD-M15.4 — the other half: padding is not a lock on the rest of the day.

    "(if a non break /buffer/ lunch block - a non -action item block - is on
    the Day, allow more)". A box already holding something is skipped, which is
    how AutoLoad keeps off lunch, but the day itself goes on accepting work --
    and this pins that so it cannot quietly become a refusal.
    """
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    _add_block(
        manager, 30, "coffee", 0, block_date=SATURDAY, block_type=BlockType.BREAK
    )
    item = _item(manager, "weekend work", SATURDAY)

    panel.block_item(item, 4)

    placed = {row[0]: row[1] for row in _stored(manager, SATURDAY)}
    assert placed == {"coffee": 0, "weekend work": 4}, placed


def test_pdm155_an_unparseable_date_is_not_a_work_day(
    root, manager, settings, monkeypatch
):
    """PD-M15.5 — **adversarial (P7)**: a date that looks like one and is not.

    ``is_block_day`` answers False for anything it cannot parse, so the gate
    asks rather than letting the write through -- the input that "looks right
    but is wrong" must not score as a work day. Declined here, so the
    assertion is that nothing was written to a date the planner cannot name.
    """
    asked = []
    monkeypatch.setattr(
        "tkinter.messagebox.askyesno", lambda *a, **k: asked.append(1) or False
    )
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = "2026-13-45"
    panel.refresh()
    item = _item(manager, "nowhere work", THURSDAY)

    panel.block_item(item, 0)

    assert len(asked) == 1, "the planner read an impossible date as a work day"
    assert manager.get_time_blocks("2026-13-45") == [], (
        "a block was written onto a date that is not one"
    )


# ================= PD-M13.7-13.10 — Clear Day and the drawn range =========
#
# The user's first fault: "Clear day doesn't reset the time blocks to range in
# settings." Under PD-M13 it resets by itself and has no reset code of its own:
# the drawn day is derived from the configured range plus whatever blocks are
# outside it, so removing the blocks that were outside narrows it back. These
# tests are what hold that claim up, and they are the ones that would fail if
# anybody put a bound write back into the extension.


def _clear_day_saying_yes(panel, monkeypatch):
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: True)
    panel.clear_day()


def test_pdm137_clear_day_returns_the_day_to_its_settings_range(
    root, manager, settings, monkeypatch
):
    """PD-M13.7 — the drawn grid after Clear Day is exactly the configured range.

    The fault as reported. A day extended by four drops was drawn from 06:00
    to 19:00; Clear Day took the work off it and left the thirteen hours of
    empty boxes behind, because the range had been written into Settings and
    nothing put it back.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    configured = [slot.start_time for slot in day_grid(panel.bounds)]
    _add_block(
        manager, 30, "early bird", -2,
        block_type=BlockType.ITEM, outside_range=True,
    )
    _add_block(
        manager, 30, "night owl", 20,
        block_type=BlockType.ITEM, outside_range=True,
    )
    panel.refresh()
    assert [entry.slot.start_time for entry in panel._grid.slots] != configured, (
        "precondition: the day is drawn wider than the configured range"
    )

    _clear_day_saying_yes(panel, monkeypatch)

    assert [entry.slot.start_time for entry in panel._grid.slots] == configured, (
        "the day kept the boxes the cleared blocks had widened it to"
    )


def test_pdm138_clear_day_writes_no_settings(root, manager, settings, monkeypatch):
    """PD-M13.8 — the configured range is the user's, and Clear Day is not about it.

    The other half of PD-M13.7, and the half a reset-the-range fix would have
    got wrong: narrowing the day by writing Day Start and Day End back to some
    remembered value would overwrite whatever the user had typed since.
    """
    saves = []
    monkeypatch.setattr(type(settings), "save", lambda self: saves.append(True) or True)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(
        manager, 30, "night owl", 20,
        block_type=BlockType.ITEM, outside_range=True,
    )
    panel.refresh()

    _clear_day_saying_yes(panel, monkeypatch)

    assert saves == [], f"Clear Day saved settings {len(saves)} time(s)"
    assert (settings.plan_day_start, settings.plan_day_end) == ("08:00", "17:00"), (
        f"{settings.plan_day_start}-{settings.plan_day_end}"
    )


def test_pdm139_clear_day_keeps_a_break_outside_the_range_on_the_grid(
    root, manager, settings, monkeypatch
):
    """PD-M13.9 — the day shrinks to the configured range *or* to what is still
    outside it, whichever is wider.

    The decision taken when this was planned: a break put before Day Start by
    hand is one deliberate gesture, Clear Day promises in its own question to
    leave breaks where they are, and a block drawn nowhere is the P2 failure
    the outside group exists to prevent. So the day stays wide enough to show
    it, even though every item block has gone.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(
        manager, 30, "school run", -1,
        block_type=BlockType.BREAK, outside_range=True,
    )
    _add_block(
        manager, 30, "night owl", 20,
        block_type=BlockType.ITEM, outside_range=True,
    )
    panel.refresh()

    _clear_day_saying_yes(panel, monkeypatch)

    drawn = {
        block.label: entry.slot.start_time
        for entry in panel._grid.slots
        for block in entry.starting
    }
    assert drawn == {"school run": "07:30"}, drawn
    assert panel._grid.outside == [], (
        "the break it promised to keep was moved into the outside group"
    )
    # The item block's boxes are gone; the break's is not.
    assert [entry.slot.start_time for entry in panel._grid.slots][0] == "07:30"
    assert [entry.slot.start_time for entry in panel._grid.slots][-1] == "16:30", (
        "the day is still drawn out to the box the cleared item had"
    )


def test_pdm1310_a_day_extended_under_the_old_behaviour_still_draws(
    root, manager, settings, monkeypatch
):
    """PD-M13.10 — **dirty state (P8)**: indexes a previous version renumbered.

    The state this change cannot undo, and the reason the status report carries
    a human-review line about it. Until PD-M13 an Earlier drop moved
    ``plan_day_start`` and renumbered **every** date's blocks to match, so a
    database written by the shipped version holds indexes counted from a Day
    Start that the user never typed and that is still in their settings file.
    There is no way to tell such a 07:30 from one the user chose, so nothing
    tries to: the day is drawn from the settings as they stand, and what this
    test holds up is that it is drawn *coherently* -- every block at the time
    its own row says, none of them in the outside group.
    """
    settings.plan_day_start = "07:30"
    # The renumbered day as the old code left it: the 08:00 meeting at box 1
    # because box 0 became 07:30, and the dropped item at box 0.
    _add_block(
        manager, 30, "standing meeting", 1,
        block_type=BlockType.ITEM, bounds=DayBounds(day_start="07:30"),
    )
    _add_block(
        manager, 30, "early start", 0,
        block_type=BlockType.ITEM, bounds=DayBounds(day_start="07:30"),
    )
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()

    drawn = {
        block.label: entry.slot.start_time
        for entry in panel._grid.slots
        for block in entry.starting
    }
    assert drawn == {"early start": "07:30", "standing meeting": "08:00"}, drawn
    assert panel._grid.outside == [], (
        f"a renumbered day lost a block: {[b.label for b in panel._grid.outside]}"
    )
    stored = {row[0]: row[3] for row in _stored(manager)}
    assert stored == drawn, (
        f"the row and the box disagree about the time: {stored} vs {drawn}"
    )


def test_the_day_summary_flags_a_day_that_takes_no_blocks(root, manager, settings):
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()

    assert "not a block day" in panel.day_summary.cget("text")


# --- TB-M9 : right-click to set a duration ----------------------------------

def _bound_sequences(widget) -> tuple:
    """The event sequences bound on a widget.

    CTkFrame.bind forwards to an internal canvas, so ``frame.bind()`` with no
    handler does not report the binding -- the canvas has it. Reading the
    private attribute is the only way to assert a binding exists on a
    CustomTkinter widget, and asserting it matters: Button-2 was added for
    macOS and nothing else in the suite would notice it being dropped.
    """
    canvas = getattr(widget, "_canvas", None)
    return canvas.bind() if canvas is not None else widget.bind()


def test_tbm91_both_right_click_buttons_are_bound(screen, manager):
    """TB-M9.1 — Button-3 on Linux/Windows, Button-2 for macOS right-click.

    Asserted against the screen's own list of sequences, so adding one without
    binding it fails here. That the OS delivers one of them is a human check in
    the running app, recorded as such in the plan.
    """
    _add_block(manager, 30, "a", 0)
    screen.load_blocks()

    widget, _block_id = screen._block_widgets[0]
    bound = _bound_sequences(widget)
    for sequence in RIGHT_CLICK_SEQUENCES:
        assert sequence in bound, f"no {sequence} binding on a block"
    assert RIGHT_CLICK_SEQUENCES == ("<Button-3>", "<Button-2>")


def test_the_block_menu_offers_the_documented_durations(screen, manager, monkeypatch):
    """The menu's contents, as an exact list, with 30 marked as the default.

    tk_popup is stubbed out: posting a real menu grabs the pointer and the test
    run would stop on it.
    """
    _add_block(manager, 30, "a", 0)
    screen.load_blocks()
    block = manager.get_time_blocks(THURSDAY)[0]

    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, x, y, entry="": None)

    class _Event:
        x_root = 10
        y_root = 10

    screen.open_block_menu(_Event(), block)

    menu = screen._block_menu
    labels = [
        menu.entrycget(index, "label")
        for index in range(menu.index("end") + 1)
        if menu.type(index) == "command"
    ]
    assert labels == [
        "15 minutes",
        "30 minutes  (default)",
        "45 minutes",
        "60 minutes",
        "90 minutes",
        "Custom\u2026",
        "Delete block",
    ]


def test_choosing_a_duration_from_the_menu_resizes_the_block(screen, manager, monkeypatch):
    """The menu entry is wired to the write, not merely present.

    Invoking the entry is what makes this different from the test above: a
    command built with the wrong closure variable would render an identical
    menu and resize the wrong block.
    """
    _add_block(manager, 30, "a", 0)
    _add_block(manager, 30, "b", 1)
    screen.load_blocks()
    second = manager.get_time_blocks(THURSDAY)[1]

    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, x, y, entry="": None)

    class _Event:
        x_root = 10
        y_root = 10

    screen.open_block_menu(_Event(), second)
    menu = screen._block_menu
    index = next(
        i for i in range(menu.index("end") + 1)
        if menu.type(i) == "command" and menu.entrycget(i, "label").startswith("90")
    )
    menu.invoke(index)

    assert [row[5] for row in _stored(manager)] == [30, 90]


# --- TB-M10 : buffer and break ----------------------------------------------

def test_tbm101_buffer_and_break_blocks_are_typed(screen, manager, settings):
    """TB-M10.1 — each gets its own type and its own default length.

    A break takes the user's existing break preference (5 minutes) rather than
    a second setting meaning the same thing.
    """
    screen.add_padding_block(BlockType.BUFFER)
    screen.add_padding_block(BlockType.BREAK)

    blocks = manager.get_time_blocks(THURSDAY)
    assert [(b.block_type, b.planned_minutes) for b in blocks] == [
        (BlockType.BUFFER, settings.default_time_block_minutes),
        (BlockType.BREAK, settings.default_break_minutes),
    ]
    assert all(b.item_id is None for b in blocks)


def test_padding_blocks_are_refused_on_a_non_block_day(root, manager, settings):
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()

    panel.add_padding_block(BlockType.BUFFER)

    assert manager.get_time_blocks(SATURDAY) == []
    assert "not a block day" in panel.status_label.cget("text")


def test_a_padding_block_is_not_priority_coloured(screen, manager):
    """Colouring padding by a priority it does not have is information the data does not support."""
    block = _add_block(manager, 30, "Buffer", 0, block_type=BlockType.BUFFER)

    assert accent_for_block(block, None) == block_type_colors()[BlockType.BUFFER]
    assert accent_for_block(block, None) not in priority_band_colors().values()


# --- TB-M11 : drag blocks to rearrange --------------------------------------


# --- TB-M12 : appearance ----------------------------------------------------


def test_depth_draws_three_bars_with_the_right_number_filled():
    """Requirement 8's three-bar stack, and "default depth to 1"."""
    root = ctk.CTk()
    try:
        assert DepthBarStack(root, "Deep").filled == 3
        assert DepthBarStack(root, "Medium").filled == 2
        assert DepthBarStack(root, "Shallow").filled == 1
        assert DepthBarStack(root, None).filled == 1

        stack = DepthBarStack(root, "Medium")
        bars = [c for c in stack.winfo_children() if isinstance(c, ctk.CTkFrame)]
        assert len(bars) == 3, "the stack is always three bars; the fill is what varies"
    finally:
        root.destroy()


def test_priority_bands_colour_an_item_by_its_score():
    """TB-M12 — the band comes from the score, and the colour from the theme."""
    bands = priority_band_colors()

    critical = ActionItem(who="me", title="x", priority_score=102400)
    low = ActionItem(who="me", title="x", priority_score=4)
    unscored = ActionItem(who="me", title="x", priority_score=0)

    assert accent_for_item(critical) == bands["critical"]
    assert accent_for_item(low) == bands["low"]
    assert accent_for_item(unscored) == bands["unscored"]
    assert accent_for_item(critical) != accent_for_item(low)


def test_an_unscored_item_is_not_coloured_as_low_priority():
    """Score 0 means a missing factor — absence of information, not low priority."""
    bands = priority_band_colors()

    assert bands["unscored"] != bands["low"]


# --- the lunch band ----------------------------------------------------------


# --- a block whose item is gone ---------------------------------------------

def test_a_block_keeps_its_item_title_when_the_item_starts_on_another_day(screen, manager):
    """The item behind a block may start elsewhere; the block still knows it.

    Reusing the date-filtered item list to resolve block titles is the obvious
    shortcut and the wrong one: every block for an item that started earlier
    would read "(item no longer exists)".
    """
    item = _item(manager, "started on Monday", "2026-11-02")
    _add_block(manager, 30, item.title, 0, item_id=item.id)

    screen.load_blocks()

    titles = _label_texts(screen.blocks_scroll)
    assert "started on Monday" in titles
    assert not any("no longer exists" in title for title in titles)


# --- the real bindings, driven by real Tk events ----------------------------
#
# Everything above calls the screen's handlers. That is not evidence the
# handlers are reachable: this project has already shipped a drag feature whose
# handler tests all passed while the live feature never fired, because the
# binding it gated on does not deliver on the widget it was bound to. These two
# tests press, move and release real buttons on the real row widgets, and let
# Tk decide what gets called.
#
# They need ``mapped_windows``: event_generate plus update() deadlocks on a
# withdrawn window. The fixture maps at alpha 0, so Tk lays the window out and
# nothing is drawn.


def _live_screen(root, manager, settings):
    """A Plan screen laid out with real geometry, ready for real events."""
    root.geometry("1200x800")
    # Mapped on purpose, and only legal because the caller holds
    # ``mapped_windows``: a withdrawn window reports every child unmapped, and
    # the drop test decides from ``winfo_ismapped``, so it would pass or fail
    # for the wrong reason. conftest keeps the window fully transparent.
    root.deiconify()
    panel = PlanScreen(root, manager, _App(settings))
    panel.pack(fill="both", expand=True)
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update()
    return panel


def _press_target(frame):
    """The widget a real click on this row actually lands on.

    ``CTkFrame`` draws itself on an internal canvas and forwards ``bind`` to
    it, so the canvas is both where the binding went and where the pointer
    hits. Reading it here rather than guessing keeps the test honest about
    which widget is being exercised.
    """
    return frame._canvas


def _aim_pointer_at(panel, monkeypatch, widget, offset_y=8):
    """Point the screen's pointer getters at a real place inside ``widget``.

    The drop target is decided from ``winfo_pointerx/y`` and the widgets' real
    root coordinates, because during a drag the pointer is over the floating
    label rather than the row underneath. event_generate does not move the
    physical mouse, so the getters are redirected -- at coordinates read from
    the laid-out widget, not invented, so the geometry under test is still
    real.
    """
    x = widget.winfo_rootx() + max(1, widget.winfo_width() // 2)
    y = widget.winfo_rooty() + offset_y
    monkeypatch.setattr(panel, "winfo_pointerx", lambda: x)
    monkeypatch.setattr(panel, "winfo_pointery", lambda: y)


def test_a_real_press_and_release_on_an_item_row_creates_a_block(
    root, manager, settings, monkeypatch, mapped_windows
):
    """Requirement 3, driven through Tk rather than through the handlers.

    Press, motion, release on the row's own widget. Press and release are bound
    to the same widget on purpose: Tk's implicit button grab delivers the
    release there whatever the pointer has moved over, which is why this works
    without depending on the motion event arriving at all.
    """
    _item(manager, "Draft the proposal", work_block=45)
    panel = _live_screen(root, manager, settings)

    rows = [w for w in panel.items_scroll.winfo_children() if isinstance(w, ctk.CTkFrame)]
    assert rows, "the item pane rendered no draggable row"

    # Aimed at the 09:30 box rather than at the day column, because the drop
    # target is now a half hour: a release in the column but on no box is
    # reported, not placed.
    box = next(frame for frame, index in panel._slot_frames if index == 3)
    _aim_pointer_at(panel, monkeypatch, box, offset_y=4)
    assert panel.slot_under_pointer() == 3, (
        "the test aimed outside box 3, so it would prove nothing: "
        f"pointer={panel.winfo_pointerx()},{panel.winfo_pointery()} "
        f"box={box.winfo_rootx()},{box.winfo_rooty()} "
        f"{box.winfo_width()}x{box.winfo_height()} "
        f"mapped={box.winfo_ismapped()}"
    )
    target = _press_target(rows[0])
    target.event_generate("<ButtonPress-1>", x=5, y=5)
    target.event_generate("<B1-Motion>", x=7, y=7)
    target.event_generate("<ButtonRelease-1>", x=7, y=7)
    root.update()
    root.update_idletasks()
    root.update()

    blocks = manager.get_time_blocks(THURSDAY)
    assert len(blocks) == 1, f"the real drag created {len(blocks)} blocks"
    assert blocks[0].planned_minutes == 45
    assert blocks[0].slot_index == 3
    assert blocks[0].start_time == "09:30"


def test_a_real_release_outside_the_day_creates_nothing(
    root, manager, settings, monkeypatch, mapped_windows
):
    """The same real events, released over the item pane, must do nothing.

    Without this the test above would pass for a screen that blocked an item on
    any release at all -- which would mean a user could not click an item row
    without silently scheduling it.
    """
    _item(manager, "Draft the proposal", work_block=45)
    panel = _live_screen(root, manager, settings)

    rows = [w for w in panel.items_scroll.winfo_children() if isinstance(w, ctk.CTkFrame)]
    _aim_pointer_at(panel, monkeypatch, panel.items_scroll)
    target = _press_target(rows[0])
    target.event_generate("<ButtonPress-1>", x=5, y=5)
    target.event_generate("<ButtonRelease-1>", x=5, y=5)
    root.update()

    assert manager.get_time_blocks(THURSDAY) == []


def test_a_real_right_click_on_a_block_opens_the_menu(
    root, manager, settings, monkeypatch, mapped_windows
):
    """The context menu is reachable by the gesture, not just by the method.

    ``tk_popup`` is replaced because a real popup grabs the pointer and would
    hang the run; what is being proved is that the binding fires and builds a
    menu for the right block.
    """
    _add_block(manager, 30, "First", 0, block_type=BlockType.ITEM)
    panel = _live_screen(root, manager, settings)

    opened = []
    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, *a, **k: opened.append(self))
    monkeypatch.setattr(tk.Menu, "grab_release", lambda self: None)

    widget, _block_id = panel._block_widgets[0]
    _press_target(widget).event_generate(RIGHT_CLICK_SEQUENCES[0], x=5, y=5)
    root.update()

    assert len(opened) == 1, "the right-click binding did not open a menu"
    assert opened[0].index("end") is not None


# --- found by the pre-push sweep --------------------------------------------


def test_a_custom_block_length_longer_than_a_day_is_refused(screen, manager, monkeypatch):
    """A length that format_hhmm would clamp must not reach the database.

    Stored, it would give the row an end_time that is not its start plus its
    duration — a row that lies about itself to every later reader — and draw a
    block tall enough to put the rest of the day out of reach.
    """
    _add_block(manager, 30, "First", 0)
    screen.load_blocks()
    block = manager.get_time_blocks(THURSDAY)[0]
    before = _stored(manager)

    monkeypatch.setattr(
        ctk.CTkInputDialog, "get_input", lambda self: str(24 * 60 + 1)
    )
    screen.ask_custom_minutes(block)

    assert _stored(manager) == before
    assert "1440 minutes or less" in screen.status_label.cget("text")


def test_finishing_a_drag_does_not_drop_the_posted_menu(screen, manager, monkeypatch):
    """`clear_hover_target` must not reset the reference that keeps a menu alive.

    An annotated assignment belonging in `__init__` had been left at the end of
    that method, so ending any drag discarded the reference held to stop a
    posted menu being collected — which takes its commands with it.
    """
    _add_block(manager, 30, "First", 0)
    screen.load_blocks()
    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, *a, **k: None)
    monkeypatch.setattr(tk.Menu, "grab_release", lambda self: None)

    screen.open_block_menu(_FakeEvent(10, 10), manager.get_time_blocks(THURSDAY)[0])
    assert screen._block_menu is not None

    screen.clear_hover_target()

    assert screen._block_menu is not None, "the menu reference was discarded"


# --- TG-M3/M7/M9/M10/M11/M12 : the day as a fixed grid of half hours --------
#
# These replace the reorder and repack tests this file used to hold. A day is
# no longer an order to be re-derived on every edit: every half hour from Day
# Start to Day End is a box, drawn whether anything is in it or not, and a
# block stores which box it sits in. So a gap is a legitimate day, a drop is
# aimed at one box rather than at a position in a list, and a Day Start change
# re-times the whole day without writing a row.


def test_tgm71_every_slot_is_drawn(screen, manager):
    """TG-M7.1 — the whole grid, filled boxes and empty ones alike.

    The empty boxes are the feature. A pane that drew only the occupied half
    hours would be the old list of blocks with clock times written on it, and
    there would be nothing for a drop to aim at.
    """
    _add_block(manager, 30, "only block", 4)
    screen.load_blocks()

    bounds = DayBounds()
    expected = [slot.index for slot in day_grid(bounds)]
    assert [slot_index for _frame, slot_index in _slot_frames(screen)] == expected
    assert len(expected) == 18, "08:00 to 17:00 is eighteen half hours"

    times = _label_texts(screen.blocks_scroll)
    assert "08:00" in times and "16:30" in times
    assert "09:00" in times, "the box after the only block was not drawn"


def test_tgm101_two_tasks_share_a_box(screen, manager):
    """TG-M10.1 — a box is worth 30 minutes however many tasks are in it.

    Both titles in the one box, and the box drawn taller to say so: a second
    task that silently replaced the first, or a row that stayed one chip high,
    would both read as a day with one task in that half hour.
    """
    _add_block(manager, 30, "first task", 2)
    _add_block(manager, 30, "second task", 2)
    screen.load_blocks()

    frame = next(f for f, index in _slot_frames(screen) if index == 2)
    assert _label_texts(frame).count("first task") == 1
    assert _label_texts(frame).count("second task") == 1
    assert frame.cget("height") == slot_row_height(2, screen.box_height())
    assert frame.cget("height") > slot_row_height(1)

    # The box is still one half hour, not two.
    assert screen._grid.minutes_occupied == SLOT_MINUTES


def test_a_longer_task_marks_the_boxes_it_runs_through(screen, manager):
    """45 minutes takes two boxes, and the second says what it is.

    Drawn as a plain second chip it would read as another task; left blank it
    would read as a free half hour the user could drop work into. Neither is
    true, so the continuation is marked and its spare minutes are written on it.
    """
    _add_block(manager, 45, "write the brief", 0)
    screen.load_blocks()

    first = next(f for f, index in _slot_frames(screen) if index == 0)
    second = next(f for f, index in _slot_frames(screen) if index == 1)

    assert "write the brief" in _label_texts(first)
    assert "\u21b3 write the brief" in _label_texts(second)
    assert "15m spare" in _label_texts(second)
    assert screen._grid.minutes_occupied == 60, "two boxes are 60 minutes of day"


def test_tgm31_an_outside_block_is_drawn(screen, manager, settings):
    """TG-M3.1 — a block no box can hold is shown, not dropped (P2).

    The mechanism changed under PD-M13, reason (b): the behaviour changed
    intentionally. Day End moving earlier used to be the ordinary way a block
    ended up here, and the day it stopped being drawn was the day that work
    was lost with nothing on screen to say so. The drawn day now widens past
    the configured range instead, so what is left outside is a pre-grid row
    whose clock time no box answers to. The guarantee under test is the same
    one: that block is on screen, in the group, and not silently absent.
    """
    _unplaced(manager, "late afternoon")

    screen.load_blocks()

    assert [b.label for b in screen._grid.outside] == ["late afternoon"]
    drawn = _label_texts(screen.outside_frame)
    assert "late afternoon" in drawn
    assert any("Outside the day (1)" in text for text in drawn)
    # In the items column, not under the grid: the group is dragged from,
    # so it belongs beside the other things that are dragged from.
    assert "late afternoon" not in _label_texts(screen.blocks_scroll)


def test_tgm91_a_drop_lands_on_the_slot_under_the_pointer(screen, manager, monkeypatch):
    """TG-M9.1 — the box the pointer is in, and no other.

    The whole point of a fixed grid is that the user picks the half hour. A
    drop handler that appended to the end of the day, or picked the first free
    box, would plan the work somewhere they did not point.
    """
    item = _item(manager, "Draft the proposal")
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    monkeypatch.setattr(screen, "_slot_frames", [(frames[6], 6)])
    monkeypatch.setattr(screen, "winfo_pointerx", lambda: 0)
    monkeypatch.setattr(screen, "winfo_pointery", lambda: 0)
    monkeypatch.setattr(
        "src.getmoredone.screens.plan.widget_contains_pointer",
        lambda widget, x, y: True,
    )

    assert screen.slot_under_pointer() == 6
    screen.block_item(item, screen.slot_under_pointer())

    assert [(row[0], row[1], row[3]) for row in _stored(manager)] == [
        ("Draft the proposal", 6, "11:00")
    ]


def test_a_drop_that_lands_on_no_box_is_a_cancelled_drag(screen, monkeypatch):
    """``None`` means nothing happens, never "the nearest box".

    Without this the test above would pass for a screen that resolved every
    release to a box, so a release over the sidebar would quietly schedule the
    item at 08:00.
    """
    monkeypatch.setattr(screen, "winfo_pointerx", lambda: 0)
    monkeypatch.setattr(screen, "winfo_pointery", lambda: 0)
    monkeypatch.setattr(
        "src.getmoredone.screens.plan.widget_contains_pointer",
        lambda widget, x, y: widget is screen.blocks_scroll,
    )

    assert screen.slot_under_pointer() is None


def test_tgm92_a_drop_on_lunch_is_refused_and_says_why(screen, manager):
    """TG-M9.2 — lunch is drawn as a box and takes nothing, with a reason.

    Silently placing the block in the next free box would be the screen
    choosing where the work goes; silently doing nothing would read as a
    broken drag.
    """
    item = _item(manager, "Draft the proposal")

    screen.block_item(item, 8)

    assert _stored(manager) == []
    assert screen.status_label.cget("text") == REFUSAL_TEXT[SlotRefusal.CROSSES_LUNCH]
    assert refusal_text(SlotRefusal.CROSSES_LUNCH) == REFUSAL_TEXT[
        SlotRefusal.CROSSES_LUNCH
    ]


def test_tgm121_the_summary_separates_occupied_from_planned(screen, manager):
    """TG-M12.1 — boxes used, time occupied and time planned, all three.

    A 45-minute task occupies 60 minutes of the day and plans 45 of them. One
    number would have to be wrong about one of those, and the whole reason the
    grid rounds up is that the difference is real.
    """
    _add_block(manager, 45, "write the brief", 0)
    screen.load_blocks()

    text = screen.day_summary.cget("text")
    assert "2 of 18 boxes" in text
    assert "1h 00m occupied" in text
    assert "45m planned" in text


def test_tgm64_saving_settings_writes_no_blocks(screen, manager):
    """TG-M6.4 — a Day Start change re-times the day without touching a row.

    The box is stored relative to Day Start, so the clock times follow from it
    on read. This is what retired the packing machinery: there is no stored
    time to go stale, nothing to renumber, and no half-written day.
    """
    _add_block(manager, 30, "first", 0)
    _add_block(manager, 30, "second", 3)
    screen.load_blocks()
    before = _stored(manager)
    assert [row[3] for row in before] == ["08:00", "09:30"]

    screen.on_settings_saved(DayBounds(day_start="07:00"))

    assert _stored(manager) == before, "a settings change wrote to the blocks table"
    drawn = _label_texts(screen.blocks_scroll)
    assert "07:00" in drawn, "the grid did not re-time to the new Day Start"
    assert "Day settings saved" in screen.status_label.cget("text")

    grid = build_day_grid(manager.get_time_blocks(THURSDAY), DayBounds(day_start="07:00"))
    starting = {
        block.label: entry.slot.start_time
        for entry in grid.slots
        for block in entry.starting
    }
    assert starting == {"first": "07:00", "second": "08:30"}


def test_tgm111_a_real_drag_moves_a_block_between_slots(
    root, manager, settings, monkeypatch, mapped_windows
):
    """TG-M11.1 — press, motion, release on a real chip moves it to that box.

    Driven through Tk rather than through the handler, because this screen has
    already shipped a drag whose handler worked and whose binding was never
    reached (P25). Press and release go to the same widget: Tk's implicit
    button grab delivers the release there whatever the pointer moved over.
    """
    _add_block(manager, 30, "First", 0, block_type=BlockType.ITEM)
    panel = _live_screen(root, manager, settings)

    target_frame = next(f for f, index in panel._slot_frames if index == 5)
    _aim_pointer_at(panel, monkeypatch, target_frame, offset_y=4)
    assert panel.slot_under_pointer() == 5, (
        "the test aimed outside box 5, so it would prove nothing: "
        f"pointer={panel.winfo_pointerx()},{panel.winfo_pointery()} "
        f"box={target_frame.winfo_rootx()},{target_frame.winfo_rooty()} "
        f"{target_frame.winfo_width()}x{target_frame.winfo_height()}"
    )

    widget, _block_id = panel._block_widgets[0]
    chip = _press_target(widget)
    chip.event_generate("<ButtonPress-1>", x=5, y=5)
    chip.event_generate("<B1-Motion>", x=7, y=7)
    chip.event_generate("<ButtonRelease-1>", x=7, y=7)
    root.update()
    root.update_idletasks()
    root.update()

    assert [(row[0], row[1], row[3]) for row in _stored(manager)] == [
        ("First", 5, "10:30")
    ]


def test_a_continuation_chip_carries_no_drag(screen, manager):
    """The box a block starts in is the one that owns it.

    A press on the second box of a 45-minute task would otherwise drag -- or
    offer to resize -- a block from a box it does not start in, which is how a
    task ends up moved by a gesture aimed at the half hour it merely runs
    through.
    """
    _add_block(manager, 45, "write the brief", 0)
    screen.load_blocks()

    assert len(screen._block_widgets) == 1, "the continuation chip was bound too"
    bound_frames = {widget for widget, _block_id in screen._block_widgets}
    second = next(f for f, index in _slot_frames(screen) if index == 1)
    assert all(widget not in second.winfo_children() for widget in bound_frames)


class _FakeEvent:
    """The two attributes open_block_menu reads off a Tk event."""

    def __init__(self, x_root, y_root):
        self.x_root = x_root
        self.y_root = y_root


# --- found by the fix-range re-sweep ---------------------------------------


# --- TG-M8 : the row has a width, and the suite says so ---------------------
#
# These were written to catch a sliver bug -- block rows reported as rendering
# a few pixels wide -- on the theory that grid_propagate(False) left the frame
# with no width.
#
# This comment used to say **the bug does not reproduce**, on the strength of
# those two measurements. It was wrong, and it was wrong in the way a
# measurement is wrong when it measures the available thing rather than the
# reported one. The bug was real and visible on screen on 2026-11-06: every
# placed task drew as a bare 6px stripe, no title, no duration, no bars. The
# two tests below passed the whole time.
#
# They passed because the row's *width* was never the problem. The stripe
# asked to be 200px tall (``ctk.CTkFrame`` requests 200x200 when neither
# dimension is set, and the stripe set only ``width``), the chip passed that
# request up, and the box clipped it to 34 -- so the title was laid out around
# y=100, below everything the box shows. A label clipped by its parent is
# still full-width and Tk still calls it mapped, which is exactly the pair of
# properties these two assert.
#
# PB-M2.1 (``test_a_task_chips_title_is_inside_the_box_it_is_drawn_in``) is
# the test that closes that gap: it measures where the title sits inside the
# box, which is the question "is the user looking at it" actually reduces to.
# Keep these two as well -- width and mapping are still necessary, just not
# sufficient -- but do not read a pass here as the box being legible.


def _one_slot_pane(
    root, block, width=None, *, mapped=True, continued=False, items_by_id=None
):
    """A pane holding one box of ``block``: the one it starts in, or its next.

    ``mapped`` is explicit because the ``deiconify`` here is what makes a
    window measurable, and a test that only reads ``cget`` or a grid option
    does not need it -- mapping anyway means the test is skipped in the
    documented local workflow for nothing. ``continued=True`` returns the
    second box of a longer block, which is the only way to get at a
    continuation chip.

    ``items_by_id`` defaulted to empty and could not be given, so every chip
    this helper built was rendered with ``item=None`` -- band ``unscored``,
    whatever the test had stored. Any colour assertion against the item's own
    band was comparing the unscored tint with itself.
    """
    if mapped:
        root.geometry("1200x800")
        root.deiconify()
    pane = ctk.CTkFrame(root, width=width) if width else ctk.CTkFrame(root)
    pane.pack(fill="both", expand=True)
    pane.grid_columnconfigure(0, weight=1)

    slots = build_day_grid([block], DayBounds()).slots
    if continued:
        entry = slots[1]
        assert entry.continued, "the block does not reach a second box"
        assert not entry.starting, "the second box starts a task of its own"
    else:
        entry = slots[0]
        assert entry.starting, "the block was not placed in the first box"
    return pane, build_slot_row(pane, entry, items_by_id or {}, 0)


def _find_label(widget, text):
    """The label showing ``text``, however deeply nested, or ``None``."""
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel) and child.cget("text") == text:
            return child
        found = _find_label(child, text)
        if found is not None:
            return found
    return None


def _descendant_labels(widget):
    """Every CTkLabel under a widget, however deeply nested."""
    found = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            found.append(child)
        found.extend(_descendant_labels(child))
    return found


def _stripe_colors(widget):
    """Every stripe frame's colour under a widget, in render order.

    A stripe is the only frame built at ``STRIPE_WIDTH_PX``, which is what
    makes it findable without the renderer handing one back.
    """
    found = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkFrame) and child.cget("width") == STRIPE_WIDTH_PX:
            found.append(child.cget("fg_color"))
        found.extend(_stripe_colors(child))
    return found


def _padding_blocks():
    return [
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, block_type=BlockType.BREAK, slot_index=0,
        ),
        TimeBlock(
            block_date=THURSDAY, start_time="08:30", end_time="09:00",
            planned_minutes=30, block_type=BlockType.BUFFER, slot_index=1,
        ),
    ]


def test_pdm42_a_padding_box_is_drawn_like_the_lunch_box(root):
    """PD-M4.2 — the whole box, not only the stripe.

    PD-M4 gave break, buffer and lunch one stripe colour and stopped there,
    which left a break and a buffer drawn on the surface every task box uses
    while lunch kept its own lighter one. The stripes matched and the boxes did
    not, and the boxes are what a user compares. Lunch is the reference, since
    it is the one of the three the day owns.

    An empty box is excluded deliberately: it is room, not padding, and the
    assertion would be vacuous if everything that is not a task matched.
    """
    pane = ctk.CTkFrame(root)
    pane.grid_columnconfigure(0, weight=1)

    fills = {}
    for row, entry in enumerate(build_day_grid(_padding_blocks(), DayBounds()).slots):
        rendered = build_slot_row(pane, entry, {}, row)
        if entry.slot.is_lunch:
            fills.setdefault("lunch", rendered.frame.cget("fg_color"))
        elif entry.slot.index == 0:
            fills["break"] = rendered.frame.cget("fg_color")
        elif entry.slot.index == 1:
            fills["buffer"] = rendered.frame.cget("fg_color")
        elif entry.is_empty:
            fills.setdefault("empty", rendered.frame.cget("fg_color"))

    assert set(fills) == {"lunch", "break", "buffer", "empty"}, (
        f"the day did not draw all four kinds of box: {sorted(fills)}"
    )
    assert fills["break"] == fills["lunch"], (
        f"a break box is drawn on {fills['break']} and a lunch box on "
        f"{fills['lunch']}"
    )
    assert fills["buffer"] == fills["lunch"], (
        f"a buffer box is drawn on {fills['buffer']} and a lunch box on "
        f"{fills['lunch']}"
    )
    assert fills["empty"] != fills["lunch"], (
        "an empty box is drawn like padding, so the comparison above says "
        "nothing: everything that is not a task would pass it"
    )


def test_pdm42_the_lunch_word_is_body_text_like_a_breaks(root):
    """PD-M4.2 — "Lunch" is as readable as "Break", and the same size.

    It was the theme's muted text at 11pt on the surface a lunch box is drawn
    on, which in light mode left the word within a few values of its own
    background: measured off a screenshot at (239, 234, 252) on (240, 231, 255).
    Asserted against a break's word, because the complaint is that the three
    kinds of padding do not read alike.
    """
    pane = ctk.CTkFrame(root)
    pane.grid_columnconfigure(0, weight=1)

    words = {}
    for row, entry in enumerate(build_day_grid(_padding_blocks(), DayBounds()).slots):
        rendered = build_slot_row(pane, entry, {}, row)
        for label in _descendant_labels(rendered.frame):
            shown = str(label.cget("text"))
            if shown in ("Lunch", "Break"):
                words.setdefault(shown, label)

    assert set(words) == {"Lunch", "Break"}, (
        f"both words have to be on screen to compare them: found {sorted(words)}"
    )
    assert words["Lunch"].cget("font").cget("size") == (
        words["Break"].cget("font").cget("size")
    ), (
        f"Lunch is {words['Lunch'].cget('font').cget('size')}pt and Break is "
        f"{words['Break'].cget('font').cget('size')}pt"
    )
    assert words["Lunch"].cget("text_color") == words["Break"].cget("text_color"), (
        f"Lunch is drawn in {words['Lunch'].cget('text_color')} and Break in "
        f"{words['Break'].cget('text_color')}"
    )


def test_pdm42_break_buffer_and_lunch_render_in_the_shared_colour(root):
    """PD-M4.2 — the table reaching the screen, for all three kinds.

    Purpose: PD-M4 -- one colour for the time that is not work.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m4

    A lunch box carried no stripe at all, so "the same colour as a break" had
    nowhere to be: the only thing it coloured was its own row fill, which is
    the surface every other box is drawn on. It gets the stripe the other two
    have, in the same place and the same width, which is also what makes the
    three read as one kind of thing.
    """
    blocks = [
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, block_type=BlockType.BREAK, slot_index=0,
        ),
        TimeBlock(
            block_date=THURSDAY, start_time="08:30", end_time="09:00",
            planned_minutes=30, block_type=BlockType.BUFFER, slot_index=1,
        ),
    ]
    pane = ctk.CTkFrame(root)
    pane.grid_columnconfigure(0, weight=1)

    seen = {}
    for row, entry in enumerate(build_day_grid(blocks, DayBounds()).slots):
        rendered = build_slot_row(pane, entry, {}, row)
        if entry.slot.is_lunch:
            seen.setdefault("lunch", _stripe_colors(rendered.frame))
        elif entry.slot.index == 0:
            seen["break"] = _stripe_colors(rendered.frame)
        elif entry.slot.index == 1:
            seen["buffer"] = _stripe_colors(rendered.frame)

    for kind in ("break", "buffer", "lunch"):
        assert len(seen.get(kind, [])) == 1, (
            f"the {kind} box drew {len(seen.get(kind, []))} stripes, expected 1"
        )
    shared = block_type_colors()["buffer"]
    assert [seen[kind][0] for kind in ("break", "buffer", "lunch")] == [shared] * 3, (
        "the three kinds of padding render in different colours: "
        f"{ {k: seen[k][0] for k in ('break', 'buffer', 'lunch')} }"
    )


def _slot_row_for(root, blocks, items_by_id, slot_index=0, bounds=None):
    """The rendered box at ``slot_index`` of a day holding ``blocks``.

    ``_one_slot_pane`` takes a single block and is the right tool for one
    task; this is for the boxes that hold two, and for picking a box other
    than the first.
    """
    pane = ctk.CTkFrame(root)
    pane.grid_columnconfigure(0, weight=1)
    entry = build_day_grid(blocks, bounds or DayBounds()).slots[slot_index]
    return build_slot_row(pane, entry, items_by_id, 0)


def _check_label(widget):
    """The completion check in a box, or ``None``."""
    return _find_label(widget, PD_CHECK_TEXT)


def _plain_item(title, status="open"):
    """An ActionItem the renderer can read, with no database behind it.

    ``_item`` creates a row, which these need nothing of: ``build_slot_row``
    is handed its items in a dict and reads title, depth, score and status off
    the object.
    """
    return ActionItem(who="me", title=title, start_date=THURSDAY, status=status)


def test_pdm61_a_completed_task_shows_a_check_left_of_the_time(root):
    """PD-M6.1 — the day says which of its boxes are done.

    Purpose: PD-M6 -- a completed task is marked where the day is read, at
             the start of the row.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m6

    Left of the time, as a grid column rather than as a glance: a check that
    rendered after the time would still satisfy "the box has a check".
    """
    item = _plain_item("Draft the proposal", status="completed")
    block = TimeBlock(
        block_date=THURSDAY, start_time="08:00", end_time="08:30",
        planned_minutes=30, item_id=item.id, slot_index=0,
    )
    row = _slot_row_for(root, [block], {item.id: item})

    check = _check_label(row.frame)
    assert check is not None, (
        f"no check in a box holding a completed task; labels were {_label_texts(row.frame)}"
    )
    time_label = _find_label(row.frame, "08:00")
    assert time_label is not None, "the box lost its time label"
    assert check.grid_info()["column"] < time_label.grid_info()["column"], (
        "the check is drawn at or after the time: check at column "
        f"{check.grid_info()['column']}, time at {time_label.grid_info()['column']}"
    )
    assert check.cget("text_color") == status_text_color("success"), (
        f"the check is {check.cget('text_color')}, not the theme's success token"
    )


def test_pdm62_an_open_task_shows_no_check(root):
    """PD-M6.2 — the mark means something only if it is absent otherwise."""
    item = _plain_item("Draft the proposal")
    block = TimeBlock(
        block_date=THURSDAY, start_time="08:00", end_time="08:30",
        planned_minutes=30, item_id=item.id, slot_index=0,
    )
    row = _slot_row_for(root, [block], {item.id: item})

    assert _check_label(row.frame) is None, (
        f"an open task was marked complete; labels were {_label_texts(row.frame)}"
    )
    assert _find_label(row.frame, "08:00") is not None, "the box lost its time label"


def test_pdm63_a_box_with_one_task_still_open_shows_no_check(root):
    """PD-M6 — the check is the box's claim, and a half-done box is not done.

    The adversarial case: a box holding a finished task beside an unfinished
    one looks finished from the time column, which is the one place a reader
    is counting on the mark to be exact.
    """
    done = _plain_item("Draft the proposal", status="completed")
    todo = _plain_item("Send the proposal")
    blocks = [
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, item_id=done.id, slot_index=0,
        ),
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, item_id=todo.id, slot_index=0,
        ),
    ]
    row = _slot_row_for(root, blocks, {done.id: done, todo.id: todo})

    assert len(_label_texts(row.frame)) > 2, "the box did not render both tasks"
    assert _check_label(row.frame) is None, (
        "a box with work still open was marked complete"
    )


def test_pdm64_a_continuation_of_a_completed_task_shows_the_check(root):
    """PD-M6.4 — the later boxes of a finished task are finished too.

    The box is spent either way, and a 90-minute task checked in its first
    box and bare in the next two reads as a task that was abandoned.
    """
    item = _plain_item("Review the proposal", status="completed")
    block = TimeBlock(
        block_date=THURSDAY, start_time="08:00", end_time="09:00",
        planned_minutes=60, item_id=item.id, slot_index=0,
    )
    row = _slot_row_for(root, [block], {item.id: item}, slot_index=1)

    assert _find_label(row.frame, "08:30") is not None, "not the continuation box"
    assert _check_label(row.frame) is not None, (
        f"the continuation of a completed task is bare; labels were {_label_texts(row.frame)}"
    )


def test_pdm65_a_block_whose_item_is_gone_draws_no_check(root):
    """PD-M6.5 — an unknown item is not a completed one, and must not raise."""
    block = TimeBlock(
        block_date=THURSDAY, start_time="08:00", end_time="08:30",
        planned_minutes=30, item_id="item-that-was-deleted", slot_index=0,
    )
    row = _slot_row_for(root, [block], {})

    assert _check_label(row.frame) is None, "a block with no item was marked complete"


def test_pdm66_a_break_in_the_box_does_not_hold_it_open(root):
    """PD-M6 — padding is not work, so it cannot be *unfinished* work.

    A half hour holding a finished task and a five-minute break is a finished
    half hour: the break is time accounted for, not work outstanding. The
    first version of this test put a break in a box on its own, which cannot
    fail -- a break carries no item, so it reads as "not completed" whether
    the padding filter is there or not, and the mutation came back green over
    it. This is the case that tells the two apart.
    """
    done = _plain_item("Draft the proposal", status="completed")
    blocks = [
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, item_id=done.id, slot_index=0,
        ),
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:05",
            planned_minutes=5, block_type=BlockType.BREAK, slot_index=0,
        ),
    ]
    row = _slot_row_for(root, blocks, {done.id: done})
    assert _check_label(row.frame) is not None, (
        "a break beside a finished task took the box's mark away; labels were "
        f"{_label_texts(row.frame)}"
    )

    bare = _slot_row_for(
        root,
        [
            TimeBlock(
                block_date=THURSDAY, start_time="08:00", end_time="08:30",
                planned_minutes=30, block_type=BlockType.BREAK, slot_index=0,
            )
        ],
        {},
    )
    assert _check_label(bare.frame) is None, (
        "a box holding nothing but a break was marked complete"
    )


def test_tgm81_a_block_row_fills_its_pane(root, manager, mapped_windows):
    """TG-M8.1 — a box is as wide as the column it is gridded into.

    The sliver bug, as a number. Within 8px for the 2px padx on each side plus
    a border; anything near zero is the bug.
    """
    pane, row = _one_slot_pane(
        root,
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, label="Draft the proposal", slot_index=0,
        ),
        width=600,
    )
    root.update()

    assert pane.winfo_width() > 100, (
        "the pane itself did not lay out, so this would prove nothing: "
        f"{pane.winfo_width()}px"
    )
    assert abs(row.frame.winfo_width() - pane.winfo_width()) <= 8, (
        f"box is {row.frame.winfo_width()}px inside a {pane.winfo_width()}px pane"
    )


def test_tgm82_a_block_row_shows_its_title(root, manager, mapped_windows):
    """TG-M8.2 — the title label is non-empty and actually on screen.

    Width alone is not enough: a full-width box whose title column collapsed
    would pass TG-M8.1 and still show the user nothing. winfo_ismapped() is
    the half that catches it, because a label squeezed to zero is unmapped.
    """
    _pane, row = _one_slot_pane(
        root,
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, label="Draft the proposal", slot_index=0,
        ),
    )
    root.update()

    title = _find_label(row.frame, "Draft the proposal")
    assert title is not None, (
        "no title label in the box; labels were "
        f"{_label_texts(row.frame)}"
    )
    assert title.winfo_ismapped(), "the title label is not on screen"
    assert title.winfo_width() > 1, f"title label is {title.winfo_width()}px wide"


# --- found by the pre-push sweep of the grid rebuild ------------------------


def _legacy_block(manager, label="from the old model", start="09:00", minutes=30):
    """A row as the retired model wrote it: a clock time and no box.

    ``create_time_block`` is the raw insert, so it places nothing -- which is
    exactly the shape every day in a database written before the grid has.
    """
    manager.create_time_block(
        TimeBlock(
            block_date=THURSDAY,
            start_time=start,
            end_time="09:30",
            planned_minutes=minutes,
            label=label,
        )
    )


def test_an_unreadable_settings_file_is_flagged_not_just_printed(
    tmp_path, monkeypatch, capsys
):
    """``load`` must say when its defaults are a stand-in, not the user's.

    This flag exists for the Plan screen's adoption, which is why it is tested
    beside it: adoption writes a box derived from Day Start and cannot be
    undone, so it has to be able to tell a default the user chose from one
    that is covering for a file nobody could read.
    """
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json")
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))

    loaded = AppSettings.load()

    # The print is asserted because the flag alone no longer identifies this
    # branch: a settings file that is missing, or that predates Day Settings,
    # sets the same field. Without this the corrupt file could be deleted from
    # the test and it would still pass.
    assert "Error loading settings" in capsys.readouterr().out, (
        "the parse failure was not reported at all"
    )
    assert loaded.plan_day_shape_unconfirmed is True, (
        "an unreadable settings file returned all-defaults with nothing that"
        " survives a save to say the day's four times were invented"
    )
    assert AppSettings().plan_day_shape_unconfirmed is False, (
        "an object built in code claims a user guessed something"
    )


def test_adoption_does_not_run_on_a_guessed_day_start(root, manager, settings):
    """A settings file that cannot be read must not become a permanent box.

    ``adopt_legacy_day`` turns a stored clock time into a ``slot_index``
    relative to Day Start and then overwrites the stored time. Run against an
    all-defaults object standing in for settings nobody could read, it moves
    planned work to an hour the user never picked and destroys the only record
    of the hour they did -- a transient read failure written down as a
    permanent fact (P1). The blocks keep their NULL instead, which is the
    retryable state the outside-the-day group already exists to show.
    """
    _legacy_block(manager)
    settings.plan_day_shape_unconfirmed = True

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    stored = manager.get_time_blocks(THURSDAY)[0]
    assert stored.slot_index is None, "adopted against a day shape nobody could read"
    assert stored.start_time == "09:00", "the stored time was overwritten by a guess"
    assert [b.label for b in panel._grid.outside] == ["from the old model"]
    assert "has not been confirmed" in panel.status_label.cget("text")
    assert "Day Settings" in panel.status_label.cget("text"), (
        "told the user their day shape is unconfirmed and not how to confirm it"
    )


def test_adoption_does_not_run_on_a_file_from_before_day_settings(
    root, manager, tmp_path, monkeypatch
):
    """The upgrade path end to end, through a real file.

    Time blocks are as old as the application; the four day values are not.
    A settings file from before Day Settings existed parses perfectly, so the
    first four rounds of this batch all let adoption run on it -- against a
    day start of 08:00 that nobody has ever seen, rewriting the stored time
    that said 09:45 to the 09:30 of the box it landed in.

    The whole chain is here on purpose: a real file with real keys missing,
    ``load`` reading it, the screen deciding, and the row checked afterwards.
    The screen-level tests beside this one set the field by hand, which is
    exactly the step that was never wrong.
    """
    path = tmp_path / "settings.json"
    path.write_text('{"obsidian_vault_path": "/Users/me/vault"}')
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))

    settings = AppSettings.load()
    assert settings.plan_day_start == "08:00", "precondition: the day start is a guess"

    _legacy_block(manager, start="09:45", minutes=45)

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    stored = manager.get_time_blocks(THURSDAY)[0]
    assert stored.slot_index is None, (
        "adopted against four day values the user has never seen"
    )
    assert stored.start_time == "09:45", (
        "rewrote a stored time against a guessed day start, permanently"
    )


def test_the_unconfirmed_warning_does_not_name_a_cause_it_cannot_know(
    root, manager, tmp_path, monkeypatch
):
    """Three states reach this message; the old wording described one of them.

    "has not been confirmed since the settings file could not be read" was
    written for the corrupt-file case and shipped as the wording for all three.
    On the common one -- a settings file from a version with no Day Settings --
    the file read perfectly, and the status line told the user it had not.
    """
    path = tmp_path / "settings.json"
    path.write_text('{"theme_name": "dark-blue"}')
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))

    _legacy_block(manager)

    panel = PlanScreen(root, manager, _App(AppSettings.load()))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    text = panel.status_label.cget("text")
    assert "has not been confirmed" in text, f"the state is not named: {text!r}"
    assert "Day Settings" in text, f"the remedy is not named: {text!r}"
    assert "could not be read" not in text, (
        f"blamed a settings file that read perfectly well: {text!r}"
    )


def test_adoption_says_which_day_start_it_used(screen, manager):
    """The one irreversible write on this screen, and it was silent.

    The ids ``adopt_legacy_day`` returns were discarded, so a day mapped onto
    the grid said nothing about the Day Start it was mapped against -- the
    assumption that cannot be undone was the one thing not reported.
    """
    _legacy_block(manager)

    screen.load_blocks()

    assert manager.get_time_blocks(THURSDAY)[0].slot_index == 2, "09:00 is box 2 of an 08:00 day"
    text = screen.status_label.cget("text")
    assert "Placed 1 block(s) from an earlier version" in text
    assert "08:00" in text, f"the day start it used is not named: {text!r}"


def test_only_the_last_box_of_a_task_claims_the_spare_minutes(screen, manager):
    """Spare minutes are the last box's, not every continuation's.

    A 75-minute task covers three boxes and leaves 15 minutes of the third.
    The second box it consumes whole. Labelling both "15m spare" makes the one
    number that explains the gap between *occupied* and *planned* wrong in the
    place a reader checks it.
    """
    _add_block(manager, 75, "long one", 0)
    screen.load_blocks()

    frames = {index: frame for frame, index in screen._slot_frames}
    middle = _label_texts(frames[1])
    last = _label_texts(frames[2])

    assert "15m spare" not in middle, (
        f"the middle box claims the last box's spare minutes: {middle}"
    )
    assert "same task" in middle, f"the middle box says nothing useful: {middle}"
    assert "15m spare" in last, f"the last box does not report its spare: {last}"


def test_a_block_released_off_a_box_says_so(screen, manager, monkeypatch):
    """A move that does nothing must not also say nothing.

    The item branch of this same handler reports it; the block branch did not,
    so letting go over the day heading, the summary, or the "Outside the day"
    group was indistinguishable from a drag that missed.
    """
    _add_block(manager, 30, "somewhere", 3)
    screen.load_blocks()
    block = manager.get_time_blocks(THURSDAY)[0]

    monkeypatch.setattr(screen, "slot_under_pointer", lambda: None)
    monkeypatch.setattr(screen, "pointer_over_day", lambda: True)
    screen._drag_kind = "block"
    screen._drag_block = block

    screen.on_drag_release(None)

    assert screen.status_label.cget("text") == "Drop a block on a half-hour box"
    assert manager.get_time_blocks(THURSDAY)[0].slot_index == 3, "the block moved anyway"


def test_every_part_of_an_outside_row_starts_a_drag(screen, manager):
    """The title covers most of an outside row, and it was inert.

    ``build_outside_group`` wraps its chip in a holder, so the labels sit two
    levels below the widget the handlers were bound to. Binding only the
    direct children left a press on the text doing nothing at all, in the one
    group the screen tells the user to drag blocks out of.
    """
    _unplaced(manager, "late afternoon")
    screen.load_blocks()

    label = _find_label(screen.outside_frame, "late afternoon")
    assert label is not None, (
        f"no title label in the outside group; labels were {_label_texts(screen.outside_frame)}"
    )

    # The binding itself, not a generated press: these windows are withdrawn,
    # so Tk does not deliver a synthetic press to a widget that is not
    # viewable -- which is why every other real-press test here asks for
    # ``mapped_windows``. ``CTkLabel.bind`` forwards to this inner
    # ``tkinter.Label``, so this is the widget a real press lands on and the
    # one that either carries the handler or does not.
    inner = label._label
    assert inner.bind("<ButtonPress-1>"), "a press on the title is bound to nothing"
    assert inner.bind("<ButtonRelease-1>"), "a release on the title is bound to nothing"
    assert any(
        inner.bind(sequence) for sequence in RIGHT_CLICK_SEQUENCES
    ), "a right-click on the title opens no menu"


def test_a_length_chosen_for_an_unplaced_block_does_not_show_the_row_id(screen, manager):
    """The outside group binds this menu, so the refusal must be in English.

    ``set_block_length`` raises ``ValueError("time block '<uuid>' is not on
    the grid")`` and the screen rendered ``str(error)`` straight into the
    status line. Every other refusal here goes through ``REFUSAL_TEXT`` so
    that one rule reads as one sentence.
    """
    # 19:00 is past Day End, so adoption leaves it NULL rather than sliding it
    # to a box the user never picked -- which is how a block comes to be in
    # the outside group with this menu bound to it.
    _legacy_block(manager, label="never placed", start="19:00")
    screen.load_blocks()
    block = manager.get_time_blocks(THURSDAY)[0]
    assert block.slot_index is None, "the fixture placed the block after all"
    assert [b.label for b in screen._grid.outside] == ["never placed"]

    screen.set_block_minutes(block, 45)

    text = screen.status_label.cget("text")
    assert "not on a box yet" in text, f"status was {text!r}"
    assert block.id not in text, f"the row id reached the status line: {text!r}"
    assert manager.get_time_blocks(THURSDAY)[0].planned_minutes == 30, "it resized anyway"


# --- found by the re-sweep of this batch's own fix commits -------------------


def test_saving_day_settings_unblocks_adoption(root, manager, tmp_path, monkeypatch):
    """The recovery path has to actually recover, from the real starting state.

    Declining to adopt on a day shape nobody could read is only half a fix: the
    user is told Day Settings could not be read, opens Day Settings and saves --
    and the flag was never cleared, so adoption stayed blocked and the screen
    reported "Day settings saved" over it. The only escape was relaunching the
    app, which nothing in the UI or the guide mentions.

    The settings file here is a real corrupt one rather than a hand-set flag,
    so the whole path runs: ``load`` deciding the file is unreadable, the
    screen declining, the dialog writing, the old file kept aside, and the day
    mapped on the next draw. An earlier version of this test set the flag by
    hand on a path that did not exist, which skipped both ``load`` and the
    copy-aside -- the two steps most likely to be wrong.
    """
    path = tmp_path / "settings.json"
    corrupt = '{ "plan_day_start": "08:00", this is not json'
    path.write_text(corrupt)
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))

    settings = AppSettings.load()
    assert settings.plan_day_shape_unconfirmed is True

    _legacy_block(manager)

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()
    assert manager.get_time_blocks(THURSDAY)[0].slot_index is None

    dialog = PlanSettingsDialog(root, settings)
    try:
        dialog.save()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()

    kept = list(path.parent.glob("settings.json.unreadable-*"))
    assert [p.read_text() for p in kept] == [corrupt], (
        f"the unreadable file was not kept aside: {kept}"
    )

    panel.refresh()
    root.update_idletasks()

    stored = manager.get_time_blocks(THURSDAY)[0]
    assert stored.slot_index == 2, (
        "saving the day settings left adoption blocked, with no way out but a restart"
    )

    # And it stays confirmed: the dialog's confirmation went to disk with the
    # values it describes, so the next launch does not ask again.
    assert AppSettings.load().plan_day_shape_unconfirmed is False, (
        "the confirmation did not survive the save that carried it"
    )


def test_a_failed_settings_write_puts_the_day_back(root, settings, tmp_path, monkeypatch):
    """The dialog writes to the app-wide settings object before it saves.

    On a failed write it reported the failure and left the new values on that
    object. Cancel does not restore it and the Plan screen is rebuilt from it
    on every navigation, so the next visit drew and timed the day against
    bounds that exist nowhere on disk.
    """
    unwritable = tmp_path / "unwritable"
    unwritable.mkdir()
    monkeypatch.setattr(
        AppSettings, "get_settings_path", classmethod(lambda cls: unwritable)
    )
    before = settings.plan_day_start
    # Unconfirmed on the way in, so the restore has something to put back:
    # nothing was written, so nothing was confirmed.
    settings.plan_day_shape_unconfirmed = True

    dialog = PlanSettingsDialog(root, settings)
    try:
        dialog.day_start_entry.delete(0, tk.END)
        dialog.day_start_entry.insert(0, "06:30")
        dialog.save()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()

    assert settings.plan_day_start == before, (
        "a write that failed left the day on the settings object the whole app reads"
    )
    assert settings.plan_day_shape_unconfirmed is True, (
        "a write that failed confirmed a day shape that never reached the disk,"
        " so adoption would run on it"
    )


def test_a_failed_settings_write_is_not_reported_as_saved(
    root, settings, tmp_path, monkeypatch
):
    """"Day settings saved" must mean a file was written.

    ``save`` swallowed its own failure, so the dialog closed, the screen
    reported success, and the day it drew existed only in memory until the
    process ended. The settings path is a directory here, so the write raises.
    """
    unwritable = tmp_path / "unwritable"
    unwritable.mkdir()
    monkeypatch.setattr(
        AppSettings, "get_settings_path", classmethod(lambda cls: unwritable)
    )

    told = []
    dialog = PlanSettingsDialog(
        root, settings, on_saved=lambda bounds: told.append(bounds)
    )
    try:
        dialog.save()

        assert told == [], "a failed write told the screen the day settings were saved"
        assert "Could not write" in dialog.error_label.cget("text")
        assert dialog.winfo_exists(), "the dialog closed on a write that did not happen"
    finally:
        if dialog.winfo_exists():
            dialog.destroy()


def test_no_settings_object_is_not_reported_as_an_unconfirmed_day(root, manager):
    """Two different problems, and only one of them is the user's to fix.

    ``_day_shape_is_the_users`` is false for both a missing settings object and
    a file that would not parse, and the warning was written off that. A screen
    built without settings is a wiring mistake; telling the user their Day
    Settings could not be read sends them to a dialog that will not help.
    """
    _legacy_block(manager)

    panel = PlanScreen(root, manager, _App(None))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    assert panel._day_shape_is_the_users() is False
    assert panel._day_shape_is_unconfirmed() is False, (
        "no settings object was reported as a day shape nobody had confirmed"
    )
    assert "has not been confirmed" not in panel.status_label.cget("text"), (
        "sent the user to a Day Settings dialog that cannot fix a wiring mistake"
    )


def test_the_unreadable_warning_needs_a_block_to_be_about(root, manager, settings):
    """A warning about blocks from an earlier version, with none in existence.

    The branch had no condition on there being anything to adopt, so every
    date change on an ordinary day warned about work left off the grid that
    was never there.
    """
    settings.plan_day_shape_unconfirmed = True

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    assert "earlier version" not in panel.status_label.cget("text"), (
        "warned about blocks from an earlier version on a day that has none"
    )

    # The other half, in the same test: the condition has to be about blocks
    # existing, not about the branch being gone.
    _legacy_block(manager)
    panel.refresh()
    root.update_idletasks()

    assert "earlier version" in panel.status_label.cget("text"), (
        "said nothing about a block adoption declined to place"
    )


# --- The items column, and the clock that has to be read off a box ---------
#
# Found by running the app rather than by a review pass: at full size the day
# had a third of the window, the group of blocks it tells you to drag was in
# the other pane from the things you drag, and the hour on a box was pale
# peach on pale lavender.


def test_the_items_column_is_the_width_the_setting_asks_for(root, manager, settings):
    """The column is a width from Settings > Appearance, not a share of the window.

    Purpose: a column of titles does not read better for being a third of the
             screen, and the day beside it is what the width is for.
    Tests:   this test
    """
    settings.plan_items_col_width = 520
    panel = PlanScreen(root, manager, _App(settings))
    assert 520 > panel.items_width_floor(), (
        "520 is below the floor, so this test would be about the floor and "
        "not about the setting"
    )

    assert panel.grid_columnconfigure(0)["minsize"] == 520
    assert panel.grid_columnconfigure(0)["weight"] == 0, (
        "with a weight the column grows with the window and the setting is "
        "only a floor"
    )
    assert panel.grid_columnconfigure(1)["weight"] == 0, (
        "column 1 is the drag grip since PD-M2 and must not grow"
    )
    assert panel.grid_columnconfigure(2)["weight"] == 1, (
        "the day column has to take the width the items column gave up"
    )


def test_an_unusable_items_column_width_falls_back_rather_than_collapsing(
    root, manager, settings
):
    """A zero in a user-editable file must not hide the list.

    The settings file is hand-editable, and the screen a zero would hide is
    the screen you would have to use to get it back.
    """
    settings.plan_items_col_width = 0
    panel = PlanScreen(root, manager, _App(settings))
    floored = max(PLAN_ITEMS_COL_WIDTH_PX, panel.items_width_floor())
    assert panel.grid_columnconfigure(0)["minsize"] == floored

    settings.plan_items_col_width = "two hundred"
    other = PlanScreen(root, manager, _App(settings))
    assert other.grid_columnconfigure(0)["minsize"] == floored

    # The fallback is subject to the floor as well. At the shipped defaults it
    # is below it -- 260 against the 360 a row asks for -- so a zero in the
    # file used to take the unfloored fallback and clip the row's length label
    # off the right edge, which is exactly what the floor exists to stop.
    assert floored > PLAN_ITEMS_COL_WIDTH_PX, (
        "the fallback is already above the floor, so the clause above is "
        "about nothing"
    )


def _as_hex(widget, color) -> str:
    """``color`` as #RRGGBB, whatever Tk spelling it arrived in.

    The palette mixes hex strings with Tk colour names ("gray81"), and the
    contrast helper only reads hex. Asking Tk resolves both, and resolves them
    the way the screen itself will.
    """
    if isinstance(color, (tuple, list)):
        mode = (ctk.get_appearance_mode() or "Dark").lower()
        color = color[0] if mode == "light" else color[-1]
    red, green, blue = widget.winfo_rgb(color)
    return "#{:02X}{:02X}{:02X}".format(red // 257, green // 257, blue // 257)


def test_the_clock_on_a_box_is_legible_against_the_box(screen):
    """The hour label was a fixed peach, which is the dark theme's colour.

    In light mode that is pale text on a pale box: the one thing that says
    which half hour a box is was the hardest thing on the screen to read.
    4.5:1 is WCAG AA for body text.
    """
    palette = semantic_colors()
    label = _find_label(screen.blocks_scroll, "08:00")
    assert label is not None, "no clock label on the first box"

    foreground = _as_hex(screen, label.cget("text_color"))
    for name in ("surface", "surface_subtle"):
        background = _as_hex(screen, palette[name])
        ratio = contrast_ratio(background, foreground)
        assert ratio >= 4.5, (
            f"the clock label is {ratio:.2f}:1 on {name} "
            f"({foreground} on {background})"
        )


def test_the_outside_group_does_not_outlive_the_day_that_had_one(screen, manager):
    """Cleared on every redraw, not only when there is a new group to draw.

    The group lives in the items pane now, which ``load_blocks`` does not
    otherwise touch: emptied inside the "there are blocks outside the day"
    branch, yesterday's group would still be on screen under today's items.
    """
    _unplaced(manager, "late afternoon")
    screen.load_blocks()
    assert "late afternoon" in _label_texts(screen.outside_frame)

    screen.selected_date = FRIDAY
    screen.refresh()
    assert _label_texts(screen.outside_frame) == [], (
        "the group from the day before is still under the item list"
    )


# --- the accent stripe's default height ------------------------------------
#
# ``ctk.CTkFrame`` requests 200x200 when neither width nor height is given.
# The accent stripe sets ``width`` only, so its requested *height* stayed at
# the class default and every container that let a child's request through
# grew to 200px tall. On screen that was an item row five times taller than
# its own two lines of text -- the row is pinned to a multiple of the box
# height since PB-M6, so the symptom there is now a row that does not lay out
# at the height it asks for -- and a task chip whose title is centred at y=100
# inside a box clipped to 20 -- the title is drawn below the visible area, so
# the box shows nothing but the stripe. Both are the same missing `height=`.


def test_an_item_row_lays_out_at_the_height_it_asks_for(root, mapped_windows):
    """An item in the left pane is as tall on screen as the boxes it will fill.

    This test used to read "is two lines tall, not 200px" and asserted
    ``<= 120``. The behaviour changed intentionally at PB-M6: the row is no
    longer sized by its text at all but pinned to
    ``slots_for_minutes(minutes) * box_height``, so the old upper bound was
    measuring a number that had stopped meaning anything -- it passed only
    because one box of the fallback 30px happens to be under 120.

    What is worth keeping is the laid-out measurement. PB-M6.1 asserts the
    height the row asks for; this asserts Tk gives it, which is what the
    stripe's 200px request broke in the first place: a container that lets a
    child's request through is sized by a constant nobody chose.
    """
    root.geometry("1200x800")
    root.deiconify()
    pane = ctk.CTkFrame(root, width=PLAN_ITEMS_COL_WIDTH_PX)
    pane.pack(fill="both", expand=True)
    pane.grid_columnconfigure(0, weight=1)

    row = build_item_row(
        pane,
        ActionItem(
            who="me", id="i1", title="Draft the proposal", priority_score=100,
            depth="Medium", work_block=True,
        ),
        0,
        already_blocked=False,
        work_block_minutes=90,
        box_height=60,
    )
    root.update()

    expected = item_row_height(3, 60)
    assert row.winfo_height() == expected, (
        f"a 90-minute item laid out at {row.winfo_height()}px, not the "
        f"{expected}px the day gives three boxes of 60px"
    )


def test_a_task_chips_title_is_inside_the_box_it_is_drawn_in(
    root, manager, mapped_windows
):
    """TG-M8.3 — the title is within the box, not merely wide and mapped.

    TG-M8.1 and TG-M8.2 measure width and mapping, and a chip whose title is
    centred 100px below a box clipped to 20px passes both: the label is the
    full width of its column and Tk still calls it mapped, because clipping by
    a parent does not unmap a child. What the user sees is the stripe alone.
    """
    _pane, row = _one_slot_pane(
        root,
        TimeBlock(
            block_date=THURSDAY, start_time="08:00", end_time="08:30",
            planned_minutes=30, label="Draft the proposal", slot_index=0,
        ),
        width=600,
    )
    root.update()

    title = _find_label(row.frame, "Draft the proposal")
    assert title is not None, "no title label in the box"

    box_height = row.frame.winfo_height()
    top = title.winfo_rooty() - row.frame.winfo_rooty()
    assert box_height > 1, f"the box did not lay out: {box_height}px"
    assert 0 <= top and top + title.winfo_height() <= box_height, (
        f"title occupies y {top}..{top + title.winfo_height()} of a "
        f"{box_height}px box, so it is drawn outside what the box shows"
    )


# --- PB-M3 / PB-M5 : the box holds its contents, at the size asked for -----


def _item_block(label="Draft the proposal"):
    return TimeBlock(
        block_date=THURSDAY, start_time="08:00", end_time="08:30",
        planned_minutes=30, label=label, slot_index=0,
    )


def _row_columns(widget, title):
    """The grid column of each of a row's parts, keyed by role.

    Returned as a mapping so an item row and a task chip can be compared
    without either test restating the column numbers: a chip renumbered
    without the item row following is the drift this exists to catch, and a
    test holding its own copy of the layout stays green through it.
    """
    columns = {}
    for child in widget.winfo_children():
        placed = child.grid_info()
        if not placed:
            continue
        column = int(placed["column"])
        if isinstance(child, DepthBarStack):
            columns["bars"] = column
        elif isinstance(child, ctk.CTkFrame):
            if child.cget("width") == STRIPE_WIDTH_PX:
                columns["stripe"] = column
        elif isinstance(child, ctk.CTkLabel):
            shown = str(child.cget("text"))
            if shown == title:
                columns["title"] = column
            elif re.fullmatch(r"\d+m", shown):
                columns["length"] = column
            elif shown in (PD_BLOCKED_TEXT, PD_UNSCHEDULED_TEXT):
                columns["marker"] = column
    return columns


def _find_depth_stacks(widget):
    """Every DepthBarStack under ``widget``, however deeply nested."""
    found = []
    for child in widget.winfo_children():
        if isinstance(child, DepthBarStack):
            found.append(child)
        found.extend(_find_depth_stacks(child))
    return found


def test_pbm31_the_depth_bars_are_inside_the_box(root, manager, mapped_windows):
    """PB-M3.1 — the three-bar stack is drawn, and within the box.

    Its own test rather than a line in the title one: the stack is a
    grandchild of the box, so it has a way of disappearing that the title
    does not -- the title shares the chip's row, the bars are a frame of
    frames inside it.

    ``items_by_id`` was not passed, so the chip was built with ``item=None`` and
    the stack drew no filled bars: the ``depth="Deep"`` above read as if it were
    under test and reached nothing. The last call site of that family, found by
    the re-sweep after the other five were fixed.
    """
    item = _item(manager, "Draft the proposal", depth="Deep")
    block = _item_block()
    block.item_id = item.id
    _pane, row = _one_slot_pane(
        root, block, width=600, items_by_id={item.id: item}
    )
    root.update()

    stacks = _find_depth_stacks(row.frame)
    assert len(stacks) == 1, f"expected one depth stack, found {len(stacks)}"
    bars = stacks[0].winfo_children()
    assert len(bars) == MAX_DEPTH_BARS, f"{len(bars)} bars, not {MAX_DEPTH_BARS}"

    box_height = row.frame.winfo_height()
    top = stacks[0].winfo_rooty() - row.frame.winfo_rooty()
    assert 0 <= top and top + stacks[0].winfo_height() <= box_height, (
        f"bars occupy y {top}..{top + stacks[0].winfo_height()} of a "
        f"{box_height}px box"
    )


def test_pbm43_a_chip_is_filled_by_its_priority(root, manager, light_appearance):
    """PB-M4.3 — the task is shaded by its band, not by the generic surface.

    Asserted against ``fill_for_item`` rather than a literal: a test holding
    its own copy of the hex would pass a theme change that the screen failed.

    Adjacent to PB-M7's fix and corrected with it, because it was the same
    defect: the item was built with ``priority_score=51200``, which the database
    recomputes to 0, and the pane rendered with an empty ``items_by_id``, so
    both sides of the comparison were the unscored tint. Only the second
    assertion could fail, and a critical task drawn in the unscored grey would
    have passed the test named for drawing it in its band.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    _pane, row = _one_slot_pane(
        root, block, width=600, mapped=False, items_by_id={item.id: item}
    )

    chip = row.block_widgets[0][1]
    assert _as_hex(chip, chip.cget("fg_color")) == _as_hex(
        chip, fill_for_item(item)
    ), f"chip fill is {chip.cget('fg_color')}, not {fill_for_item(item)}"
    assert _as_hex(chip, chip.cget("fg_color")) != _as_hex(
        chip, semantic_colors()["surface_subtle"]
    ), "the chip is still drawn on the generic surface"
    assert _as_hex(chip, chip.cget("fg_color")) != _as_hex(
        chip, fill_for_item(None)
    ), "a critical task is drawn in the unscored tint"


def test_pbm51_box_height_follows_the_setting():
    """PB-M5.1 — the arithmetic takes the chip height from its caller.

    The no-argument form is pinned alongside, because every existing layout
    assertion in this suite depends on it and a silent change to the default
    would move them all at once.
    """
    assert slot_row_height(1, chip_height=86) == 90
    assert slot_row_height(2, chip_height=86) == 176
    assert slot_row_height(1) == SLOT_CHIP_HEIGHT_PX + 4
    assert slot_row_height(0) == SLOT_MIN_HEIGHT_PX, (
        "an empty box must keep its minimum: it holds no text and only has "
        "to be large enough to drop onto"
    )


def _one_block_day(manager, item):
    """One 30-minute block in the first box, for the sizing tests below."""
    manager.add_block_at(
        TimeBlock(
            block_date=THURSDAY, start_time="", end_time="",
            planned_minutes=30, item_id=item.id, label=item.title,
        ),
        0,
        DayBounds(),
    )


def test_pbm52_the_setting_reaches_the_rendered_box(
    root, manager, settings, mapped_windows
):
    """PB-M5.2 — the setting is not merely stored, it sizes a real box.

    Two screens built at different settings and measured against each other,
    rather than one measured against a number: the number would re-state the
    arithmetic PB-M5.1 already pins, and prove nothing about the wiring.
    """
    _one_block_day(manager, _item(manager, "Draft the proposal"))

    def box_height_at(setting):
        """The rendered height of box 0 on a screen built at ``setting``.

        The screen is destroyed before the next one is built. Two live Plan
        screens on one mapped root wedge Tk's event loop in ``root.update()``,
        which is a property of the fixture rather than of the code under test
        -- but it hangs the run just the same.
        """
        settings.drag_schedule_box_height_px = setting
        panel = PlanScreen(root, manager, _App(settings))
        panel.selected_date = THURSDAY
        panel.refresh()
        root.update_idletasks()
        try:
            box = next(f for f, index in _slot_frames(panel) if index == 0)
            return box.winfo_height()
        finally:
            panel.destroy()
            root.update_idletasks()

    short_height = box_height_at(40)
    tall_height = box_height_at(120)

    assert short_height > 1, f"the short box did not lay out: {short_height}px"
    assert tall_height > short_height, (
        f"box is {tall_height}px at a 120px setting and "
        f"{short_height}px at 40px -- the setting is not reaching the box"
    )


@pytest.mark.parametrize("bad", [0, -40, "wide", None])
def test_pbm53_an_unusable_box_height_falls_back(root, manager, settings, bad):
    """PB-M5.3 — a zero or a typo in the settings file does not flatten the day.

    A settings file is user-editable. A box of height 0 is a day with no drop
    targets and no way back to the screen that would fix it.
    """
    settings.drag_schedule_box_height_px = bad
    panel = PlanScreen(root, manager, _App(settings))

    assert panel.box_height() == SLOT_CHIP_HEIGHT_PX


def test_pbm54_the_title_column_follows_the_drag_schedule_width(
    root, manager, settings
):
    """PB-M5.4 — a box's title column is the width Drag Schedule uses.

    Read off the rendered chip's own grid, not off the setting: the point of
    the criterion is that the value arrives, and re-reading the setting would
    assert only that a number equals itself.
    """
    _one_block_day(manager, _item(manager, "Draft the proposal"))
    settings.drag_schedule_title_col_width = 173
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    chip = panel._block_widgets[0][0]
    assert chip.grid_columnconfigure(1)["minsize"] == 173, (
        f"title column asks for {chip.grid_columnconfigure(1)['minsize']}px, "
        "not the Drag Schedule width"
    )


@pytest.mark.parametrize("bad", [0, -5, "wide", None])
def test_pbm54_an_unusable_title_width_falls_back(root, manager, settings, bad):
    """The other half of PB-M5.4, on the same grounds as PB-M5.3."""
    settings.drag_schedule_title_col_width = bad
    panel = PlanScreen(root, manager, _App(settings))

    assert panel.box_title_width() == SLOT_TITLE_WIDTH_PX


def test_pbm1_an_item_rows_stripe_uses_the_brighter_table(
    root, manager, light_appearance
):
    """PB-M1 reaches the widget, not just the theme module.

    A colour table nothing consumes is a table that passes its own contrast
    tests and changes nothing on screen.

    The fourth test built on an unscored item, and the one the re-sweep of the
    fixes found still standing. On an unscored item the first assertion compared
    the unscored stripe with itself, and the second had teeth only because the
    light unscored stripe and the unscored band happen to differ -- so the whole
    test exercised the one band whose two tables were never in question.
    ``stripe_for_item`` pinned to the unscored stripe, or reading the text-safe
    table for every scored band, passed it.
    """
    item = _scored_item(manager, "Draft the proposal")
    row = build_item_row(
        root, item, 0, already_blocked=False, work_block_minutes=30
    )
    stripe = next(
        child for child in row.winfo_children()
        if isinstance(child, ctk.CTkFrame) and not isinstance(child, DepthBarStack)
    )

    assert _as_hex(row, stripe.cget("fg_color")) == _as_hex(
        row, stripe_for_item(item)
    )
    assert _as_hex(row, stripe.cget("fg_color")) != _as_hex(
        row, accent_for_item(item)
    ), "the stripe is still the text-safe band colour"
    assert _as_hex(row, stripe.cget("fg_color")) != _as_hex(
        row, stripe_for_item(None)
    ), "the stripe is the unscored bar, so it says nothing about the band"


def test_pbm41_a_chips_title_is_coloured_for_the_shade_behind_it(
    root, manager, light_appearance
):
    """PB-M4.1 — the renderer picks the title colour from the fill it drew.

    The theme-level form of this criterion cannot fail (see
    ``test_pbm41_pick_text_color_is_not_what_makes_a_fill_legible``). This one
    can: before PB-M4 the title was the theme's body text, which is the right
    colour for the theme's surface and the wrong one for a band tint -- pale
    text on a pale shade, the same failure the clock labels had.

    Adjacent to PB-M7's fix and corrected with it: the item was not really
    scored and the chip's item was ``None``, so this ran against the unscored
    tint -- the one fill whose pairing with the body text was never the bug.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    _pane, row = _one_slot_pane(
        root, block, width=600, mapped=False, items_by_id={item.id: item}
    )

    assert _as_hex(row.frame, fill_for_item(item)) != _as_hex(
        row.frame, fill_for_item(None)
    ), "the item is unscored, so this test is not about a band tint at all"

    chip = row.block_widgets[0][1]
    title = _find_label(chip, "Draft the proposal")
    assert title is not None, "no title label on the chip"

    fill = _as_hex(chip, chip.cget("fg_color"))
    drawn = _as_hex(title, title.cget("text_color"))
    assert drawn == _as_hex(title, pick_text_color(fill)), (
        f"title is {title.cget('text_color')} on a {fill} chip, not the "
        "colour chosen for that fill"
    )
    assert contrast_ratio(fill, drawn) >= 4.5, (
        f"title {drawn} on {fill} is {contrast_ratio(fill, drawn):.2f}:1"
    )


def test_the_empty_item_note_fits_the_column_it_is_drawn_in(
    root, manager, settings, mapped_windows
):
    """The "no items start on this date" note stays inside the items column.

    It did not. ``CTkLabel`` centres its text, so a label wider than its cell
    overflows on both sides and Tk clips both -- on screen that read as a
    sentence with its first word missing, which looks like a rendering fault
    rather than a message. Measured as the laid-out label against the column,
    because the hard line breaks it carried were sized for a column that no
    longer exists.

    The narrow column comes through the title-column setting since PD-M2.7:
    ``plan_items_col_width`` alone can no longer make one, because it is raised
    to what an item row needs. The column is read back off the screen rather
    than restated here, for that reason.
    """
    settings.drag_schedule_title_col_width = 60
    settings.plan_items_col_width = 240
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    root.update_idletasks()

    note = next(
        child for child in panel.items_scroll.winfo_children()
        if isinstance(child, ctk.CTkLabel)
        and "No open items start" in child.cget("text")
    )
    width = panel.items_col_width()
    assert width <= 240, (
        f"the column came out at {width}px, so it is not the narrow one this "
        "test is about"
    )
    assert note.winfo_reqwidth() <= width, (
        f"the note asks for {note.winfo_reqwidth()}px inside a {width}px column"
    )
    assert note.cget("anchor") == "w", (
        f"the note is anchored {note.cget('anchor')!r}, so text that does not "
        "fit is clipped at both ends rather than at one"
    )


# --- the sweep's findings --------------------------------------------------
#
# All five below were found by the pre-push sweep, two of them by both passes.
# Three are the same shape: a size that this batch wired to a setting, in a
# place the batch did not look. The other two are the fallback bar being
# "positive" where it had to be "usable".


def test_pbm55_an_outside_block_is_sized_like_one_in_a_box(root, manager):
    """PB-M5.5 — the outside group reads the same two sizes as a box.

    It did not. ``build_outside_group`` called ``_build_block_chip`` with
    neither size, so its rows kept the 30/80 fallbacks while every row in the
    day took the setting -- and this batch moved the group into the items
    column, directly beneath the item rows and across from the boxes it no
    longer matched. Aligned columns between paired panes are a project design
    goal, so the mismatch is the defect whichever size is "right".
    """
    item = _item(manager, "Rewrite the importer", priority_score=51200)
    block = TimeBlock(
        block_date=THURSDAY, start_time="", end_time="",
        planned_minutes=180, item_id=item.id, label=item.title,
    )

    pane = ctk.CTkFrame(root)
    pane.grid(row=0, column=0, sticky="nsew")
    pane.grid_columnconfigure(0, weight=1)
    widgets = build_outside_group(
        pane, [block], {item.id: item}, 0, chip_height=86, title_width=220
    )

    assert len(widgets) == 1, f"{len(widgets)} outside rows, expected 1"
    holder = widgets[0][1]
    assert holder.cget("height") == 86, (
        f"the outside holder is {holder.cget('height')}px while a task in a "
        "box is 86px"
    )
    chip = next(
        child for child in holder.winfo_children()
        if isinstance(child, ctk.CTkFrame)
    )
    assert chip.cget("height") == 86 - 4, (
        f"the outside chip asks for {chip.cget('height')}px, not the setting "
        "less its padding"
    )
    assert chip.grid_columnconfigure(1)["minsize"] == 220, (
        "the outside chip's title column is "
        f"{chip.grid_columnconfigure(1)['minsize']}px, not the 220px setting"
    )


def test_pbm55_the_settings_reach_the_outside_group_on_screen(
    root, manager, settings
):
    """The other half of PB-M5.5: the screen passes what the group accepts.

    Separate from the test above for the reason PB-M5.1 and PB-M5.2 are
    separate: one proves the function can be told, the other proves the screen
    tells it. A keyword argument with no caller is the failure being fixed.
    """
    settings.drag_schedule_box_height_px = 64
    _unplaced(manager, "late afternoon")
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()

    # Read off what the screen recorded as draggable rather than off the
    # container's children: a scrollable frame has children of its own.
    assert len(panel._block_widgets) == 1, (
        f"{len(panel._block_widgets)} draggable blocks, expected the one"
    )
    holder = panel._block_widgets[0][0]
    assert holder.cget("height") == 64, (
        f"the outside holder is {holder.cget('height')}px, not the 64px the "
        "screen draws a box's task at"
    )


def test_pbm56_a_box_height_below_one_line_of_text_is_raised(root, manager, settings):
    """A box height that parses but cannot hold a line of text is floored.

    ``_positive_setting`` guaranteed only "> 0". A box is pinned to
    ``chips * chip_height + 4`` and does not grow to its contents, while a
    chip does grow to its text, so at 14 a two-task half hour is 32px -- the
    same height as a one-task box, with the second task laid out past the
    clip edge. That is the PB-M2 defect reached through a setting rather than
    through a missing ``height=``, and the floor is the line of text that
    ``SLOT_CHIP_HEIGHT_PX`` already stands for.
    """
    settings.drag_schedule_box_height_px = 14
    panel = PlanScreen(root, manager, _App(settings))

    assert panel.box_height() == SLOT_CHIP_HEIGHT_PX, (
        f"a box height of 14 was accepted as {panel.box_height()}"
    )
    assert slot_row_height(2, panel.box_height()) > slot_row_height(
        1, panel.box_height()
    ), "a two-task box is no taller than a one-task box"


def test_pbm56_a_usable_box_height_is_not_floored(root, manager, settings):
    """The floor only floors. A real setting still arrives unchanged.

    Paired with the test above because a clamp written as ``max`` is one typo
    away from ignoring the setting altogether, and PB-M5's whole criterion is
    that the setting is honoured.
    """
    settings.drag_schedule_box_height_px = 120
    panel = PlanScreen(root, manager, _App(settings))

    assert panel.box_height() == 120


def test_the_outside_group_scrolls_instead_of_growing_past_the_pane(
    root, manager, settings
):
    """A full outside group stays reachable.

    The group has no cap -- shortening Day End can put every block of a full
    day into it at once -- and this batch moved it out of a scrollable
    container into a plain frame in the items pane. Every row past the bottom
    edge was then clipped, while the header went on counting them: the screen
    telling the user that work it had made undraggable was still there, which
    is worse than the silent drop P2 is about.
    """
    _unplaced(manager, *(f"late {n}" for n in range(8)))
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()

    assert len(panel._grid.outside) == 8, (
        f"{len(panel._grid.outside)} blocks outside the day, expected 8"
    )
    assert isinstance(panel.outside_frame, ctk.CTkScrollableFrame), (
        "the group is in a plain frame, so its lower rows cannot be reached"
    )
    assert panel.outside_frame.cget("height") == OUTSIDE_GROUP_HEIGHT_PX, (
        f"the group asks for {panel.outside_frame.cget('height')}px, so eight "
        "blocks push the item list it sits under off the pane"
    )


def test_the_outside_group_takes_no_room_on_a_day_without_one(
    root, manager, settings
):
    """A fixed height is only spent on the days that need it.

    The group is held back rather than gridded empty, so an ordinary day gives
    the whole pane to the item list.
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()

    assert panel._grid.outside == []
    # grid_info() and not winfo_ismapped(): every window in this suite is
    # withdrawn, so ismapped is 0 for both states and an assertion on it
    # could not fail.
    assert panel.outside_frame.grid_info() == {}, (
        "the empty group is still taking its height out of the item list"
    )

    _unplaced(manager, "late afternoon")
    panel.load_blocks()

    assert panel.outside_frame.grid_info() != {}, (
        "the group is not gridded on a day that has blocks outside the day"
    )

    # And back off again on the next day, which is the state the ``else``
    # branch in load_blocks exists for: held back at construction only, the
    # pane would keep the height it took for yesterday's group.
    panel.selected_date = FRIDAY
    panel.refresh()

    assert panel.outside_frame.grid_info() == {}, (
        "the group kept its height after moving to a day without one"
    )


def test_the_empty_item_note_wraps_even_in_a_narrow_column(
    root, manager, settings
):
    """The note's wraplength is floored, because Tk reads 0 as "do not wrap".

    ``items_col_width() - ITEMS_TEXT_INSET_PX`` is zero at a 56px column and
    negative below it, and Tk documents ``-wraplength`` of zero or less as no
    wrapping at all -- so the narrowest columns were the ones that got the
    single long clipped line this batch had just removed.

    PD-M2.7 raised ``plan_items_col_width`` to what an item row needs, which
    takes a 50px column off the table and with it most of this floor's reach.
    Not all of it: the row's own floor is mostly the title column, which has a
    fallback and no minimum of its own, so a 1px title width in a
    hand-edited file still produces a 141px items column and an 85px
    wraplength. That is the input now, and the floor is still what stands
    between it and a note that does not wrap.
    """
    settings.drag_schedule_title_col_width = 1
    settings.plan_items_col_width = 50
    panel = PlanScreen(root, manager, _App(settings))
    assert panel.items_col_width() - ITEMS_TEXT_INSET_PX < NOTE_MIN_WRAP_PX, (
        f"a {panel.items_col_width()}px column leaves more than "
        f"{NOTE_MIN_WRAP_PX}px to wrap in, so the floor is not what is being "
        "measured"
    )
    panel.selected_date = SATURDAY
    panel.refresh()

    note = next(
        child for child in panel.items_scroll.winfo_children()
        if isinstance(child, ctk.CTkLabel)
        and "No open items start" in child.cget("text")
    )
    assert note.cget("wraplength") == NOTE_MIN_WRAP_PX, (
        f"the note wraps at {note.cget('wraplength')}, which Tk reads as "
        "'do not wrap' at or below zero"
    )


def _find_continuation_chip(widget):
    """The frame holding a continuation's arrow label, however deeply nested."""
    for child in widget.winfo_children():
        labels = [
            grandchild for grandchild in child.winfo_children()
            if isinstance(grandchild, ctk.CTkLabel)
            and grandchild.cget("text").startswith("↳ ")
        ]
        if labels:
            return child
        found = _find_continuation_chip(child)
        if found is not None:
            return found
    return None


# --- PB-M6 / PB-M7 --------------------------------------------------------
#
# An item is drawn at the size of the space it will take, the facts on it are
# the ones the colour cannot carry, and the later boxes of a long task look
# like the task rather than like padding.


@pytest.mark.parametrize(
    "minutes, boxes, height_at_86",
    [(30, 1, 90), (45, 2, 182), (60, 2, 182), (90, 3, 274), (120, 4, 366)],
)
def test_pbm61_an_item_row_is_the_height_the_day_would_give_it(
    root, manager, minutes, boxes, height_at_86
):
    """PB-M6.1 — a 90-minute item is three boxes tall, because it will be.

    The expected height is built here from the day's own renderer --
    ``slot_row_height`` per box plus the gap ``build_slot_row`` grids between
    them -- not from ``item_row_height``, and not as ``boxes * box_height``.
    That product was what the first version of this test asserted, and it was
    also what the code computed, so the one relationship the change exists for
    was the one thing unchecked: a box in the day is ``box_height + 4`` and sits
    2px from the next, so a 3-box row was 274px of day claimed in 258px of row.

    45 minutes is two boxes for the same reason it is two boxes in the day: a
    half-hour grid cannot hold a quarter hour.

    The expected heights are literals, not expressions over the module's own
    constants. Built from ``slot_row_height`` and ``SLOT_ROW_GAP_PX`` they moved
    with any change to either -- setting ``SLOT_ROW_GAP_PX = 0`` left this test
    green, which is the same self-agreement in a new place. The numbers are what
    the day measures at a box height of 86: a box is 86 + 4, and consecutive
    boxes are 2 apart. ``test_pbm61_a_row_is_as_tall_as_the_boxes_beside_it``
    pins the relationship to the rendered day rather than to arithmetic.
    """
    box_height = 86
    assert height_at_86 > boxes * box_height, (
        "the expected height is no more than the plain product, so this test "
        "cannot tell the two apart"
    )

    item = _scored_item(manager, "Draft the proposal")
    row = build_item_row(
        root, item, 0, already_blocked=False,
        work_block_minutes=minutes, box_height=box_height,
    )

    assert row.cget("height") == height_at_86, (
        f"a {minutes}-minute item asks for {row.cget('height')}px; the "
        f"{boxes} boxes the day gives it occupy {height_at_86}px"
    )


def test_pbm61_a_row_is_as_tall_as_the_boxes_beside_it(
    root, manager, mapped_windows
):
    """PB-M6.1 — measured against the day on screen, not against arithmetic.

    Every other height assertion in this file compares one formula with
    another, and the first version of this change shipped because the formula
    the test used was the formula the code used. This one renders the day this
    item would actually produce -- a 90-minute block as the box it starts in
    and the two it runs through -- measures from the top edge of the first to
    the bottom edge of the third, and asserts the item row is exactly that
    tall. It fails for a wrong gap, a wrong per-box height, or a wrong span,
    without knowing how any of the three is computed.

    The boxes have to hold the task. An empty box keeps ``SLOT_MIN_HEIGHT_PX``
    whatever the box-height setting says, deliberately, because it holds no
    text -- three empty boxes span 100px at a setting of 86. What the row
    claims to match is the space the task takes, not the space it leaves.
    """
    box_height = 86
    item = _scored_item(manager, "Draft the proposal")

    block = _item_block()
    block.item_id = item.id
    block.planned_minutes = 90
    slots = build_day_grid([block], DayBounds()).slots[:3]
    assert [bool(slot.starting) for slot in slots] == [True, False, False], (
        "the 90-minute block did not lay out as one box and two continuations"
    )
    assert all(slot.continued for slot in slots[1:]), (
        "the later boxes are not marked as this task's continuations"
    )

    pane = ctk.CTkFrame(root, width=600)
    pane.grid(row=0, column=0, sticky="nsew")
    pane.grid_columnconfigure(0, weight=1)
    boxes = [
        build_slot_row(
            pane, slot, {item.id: item}, index, chip_height=box_height
        ).frame
        for index, slot in enumerate(slots)
    ]

    row = build_item_row(
        root, item, 0, already_blocked=False,
        work_block_minutes=90, box_height=box_height,
    )
    root.geometry("1200x900")
    root.deiconify()
    root.update_idletasks()
    root.update()

    top = boxes[0].winfo_y()
    bottom = boxes[-1].winfo_y() + boxes[-1].winfo_height()
    assert bottom > top, "the three boxes did not lay out"
    assert boxes[0].winfo_height() > 1, "the boxes have no height to measure"

    assert row.winfo_height() == bottom - top, (
        f"the row is {row.winfo_height()}px; the three boxes it says it will "
        f"fill span {bottom - top}px on screen"
    )


def test_pbm61_a_row_is_the_days_own_height_at_every_usable_box_height(root, manager):
    """PB-M6.1 — the row is its boxes, at 30 as well as at 86.

    This asserted the opposite until the marker became a glyph: the row had a
    second line for the ``already blocked`` words, the floor that line imposed
    was 66px, and at any box height a user is likely to set that floor was two
    boxes' worth. So a 30-minute row and a 60-minute row came out within a few
    pixels of each other, and the left pane stopped showing how much of the day
    an item would take -- which is the only reason the row is the height it is.
    Changed deliberately, not because the test was wrong about the old code.

    Asserted as the relationship rather than against the constant: a one-box
    row is one box, and a two-box row is two boxes and the gap between them, at
    the lowest box height the setting allows and at a comfortable one.
    """
    for box_height in (SLOT_MIN_HEIGHT_PX - 2, 86):
        assert item_row_height(1, box_height) == slot_row_height(1, box_height), (
            f"at a box height of {box_height} a 30-minute row is "
            f"{item_row_height(1, box_height)}px and the box it will fill is "
            f"{slot_row_height(1, box_height)}px"
        )
        assert item_row_height(2, box_height) == (
            2 * slot_row_height(1, box_height) + SLOT_ROW_GAP_PX
        ), (
            f"at a box height of {box_height} an hour-long row is "
            f"{item_row_height(2, box_height)}px, not the two boxes and the "
            "gap between them that the day will give it"
        )

    assert item_row_height(2, 86) > item_row_height(1, 86), (
        "an hour-long row is no taller than a half-hour one -- the floor is "
        "swallowing the difference again"
    )
    # The floor is still there, and still only for a box height no setting can
    # produce: a row cannot be drawn shorter than its own line of text.
    assert item_row_height(1, 1) == ITEM_ROW_MIN_HEIGHT_PX, (
        "the row floor no longer protects the text at an absurd box height"
    )


def test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for(root, manager):
    """The floor is the one number here justified by arithmetic, so measure it.

    ``ITEM_ROW_MIN_HEIGHT_PX`` is the sum of what the two text rows request:
    the title's 28px label plus its 5px top pad, and the ``already blocked``
    marker's 28px plus its 5px bottom pad. Written by hand it was 66 against an
    arithmetic of 67, one pixel short, and the row silently lost the last pixel
    of its bottom padding: no other assertion could see it, because both labels
    anchor to the top of their cell.

    It is 66 now for a reason the first version is the argument for keeping
    this test: PD-M1 moved the ``{minutes}m`` label off the second line and up
    beside the title, taking its 6px bottom pad -- the larger of that row's two
    -- with it. Nothing in the layout change says "the floor is a pixel less";
    only the measurement does.

    So this reads the requirement off the widgets the row actually builds
    rather than restating the number. The stripe is skipped: it spans all three
    rows and asks for less than their sum, so it constrains nothing.
    """
    item = _scored_item(manager, "Draft the proposal", depth="Medium")
    row = build_item_row(
        root, item, 0, already_blocked=True, work_block_minutes=30,
        box_height=SLOT_MIN_HEIGHT_PX - 4,
    )
    root.update_idletasks()

    needed = {}
    for child in row.winfo_children():
        placed = child.grid_info()
        if not placed or int(placed.get("rowspan", 1)) > 1:
            continue
        pads = [int(n) for n in re.findall(r"\d+", str(placed.get("pady", 0)))]
        pady = (pads[0] + pads[1]) if len(pads) > 1 else (pads[0] * 2 if pads else 0)
        where = int(placed["row"])
        needed[where] = max(needed.get(where, 0), child.winfo_reqheight() + pady)

    assert needed, "no single-row children on the item row to measure"
    assert sum(needed.values()) == ITEM_ROW_MIN_HEIGHT_PX, (
        f"the row's grid asks for {sum(needed.values())}px ({needed}) and the "
        f"floor is {ITEM_ROW_MIN_HEIGHT_PX}px -- at a box height this small "
        "the floor is the whole height, so the difference is padding the row "
        "does not get"
    )


def test_pbm61_the_item_row_height_comes_from_the_setting(root, manager, settings):
    """The other half of PB-M6.1: the screen passes the setting it draws with.

    Read off the rendered row, because a row built by hand with an explicit
    ``box_height`` proves only that the argument works.
    """
    settings.drag_schedule_box_height_px = 64
    _item(manager, "Draft the proposal", work_block=60)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()

    rows = [
        child for child in panel.items_scroll.winfo_children()
        if isinstance(child, ctk.CTkFrame)
    ]
    assert len(rows) == 1, f"{len(rows)} item rows, expected the one"
    expected = item_row_height(slots_for_minutes(60), 64)
    assert rows[0].cget("height") == expected, (
        f"the row is {rows[0].cget('height')}px, not the {expected}px two "
        "boxes take at the 64px this screen was told to draw a task at"
    )
    assert expected != item_row_height(slots_for_minutes(60)), (
        "64 gives the same height as the default, so this test cannot tell "
        "whether the setting was read at all"
    )


def test_pbm61_every_line_of_a_row_is_drawn_inside_it(root, manager, mapped_windows):
    """PB-M6.1 — on screen, at the floor and well above it, nothing is clipped.

    The height assertions above are all ``cget``, and a frame can ask for 67px
    while Tk lays its children out somewhere else entirely. This is the same
    measurement PB-M2.1 makes on a task chip, applied to the row: every child's
    bottom edge inside the frame's own height.

    It is the test that fails on the defect the first version shipped with --
    ``grid_rowconfigure(0, weight=1)`` putting all the slack, including a
    negative shortfall, on the title's row, so at a 30px box height Tk collapsed
    the title to a single pixel and the row showed its depth and its length and
    not which item it was.

    It fails on that combination, not on the weight alone: with the floor in
    place a one-box row is 67px and nothing is collapsed even with the weight
    back on row 0. ``test_pbm61_a_tall_row_keeps_its_two_lines_together`` is
    what pins the weight by itself.
    """
    item = _scored_item(manager, "Draft the proposal")

    for box_height in (SLOT_CHIP_HEIGHT_PX, 86):
        row = build_item_row(
            root, item, 0, already_blocked=True,
            work_block_minutes=30, box_height=box_height,
        )
        root.geometry("700x700")
        root.deiconify()
        root.update_idletasks()
        root.update()

        height = row.winfo_height()
        assert height == row.cget("height"), (
            f"the row asked for {row.cget('height')}px and laid out at {height}"
        )
        for child in row.winfo_children():
            bottom = child.winfo_y() + child.winfo_height()
            label = (
                child.cget("text") if isinstance(child, ctk.CTkLabel)
                else type(child).__name__
            )
            assert child.winfo_height() > 1, (
                f"at box height {box_height}, {label!r} is "
                f"{child.winfo_height()}px tall -- it has been collapsed"
            )
            assert bottom <= height, (
                f"at box height {box_height}, {label!r} ends at {bottom} "
                f"inside a {height}px row -- it is clipped"
            )
        row.destroy()


def test_pbm61_a_tall_row_keeps_its_two_lines_together(
    root, manager, mapped_windows
):
    """PB-M6.1 — the slack goes under the text, not between the two lines.

    A 90-minute item at the default is a 274px row holding two lines of text.
    With the weight on the title's row the title was centred in it: drawn at
    y=100 with its own detail line 124px below it and the depth bars pinned to
    the top, so the row stopped reading as one item. Asserted as a distance,
    because "the title is above the detail line" held in the broken version too.

    The second line used to be the depth word, and is the blocked marker since
    PD-M1.5 moved the depth onto the bars alone. The item is built blocked for
    that reason: this test needs two lines of text to measure between, and the
    marker is the only thing that puts a second line on the row now.
    """
    item = _scored_item(manager, "Draft the proposal", depth="Medium")
    row = build_item_row(
        root, item, 0, already_blocked=True,
        work_block_minutes=90, box_height=86,
    )
    root.geometry("700x700")
    root.deiconify()
    root.update_idletasks()
    root.update()

    title = _find_label(row, "Draft the proposal")
    detail = _find_label(row, "already blocked")
    assert title is not None and detail is not None, "the row lost a label"

    gap = detail.winfo_y() - (title.winfo_y() + title.winfo_height())
    assert 0 <= gap <= 8, (
        f"{gap}px between the title and its own detail line in a "
        f"{row.winfo_height()}px row -- the slack is between them, not below"
    )
    assert title.winfo_y() < row.winfo_height() // 4, (
        f"the title sits at y={title.winfo_y()} in a {row.winfo_height()}px "
        "row, not at the top of it"
    )


def test_pbm62_an_item_row_does_not_print_its_priority_score(root, manager):
    """PB-M6.2 — the number is gone from the row.

    The band is the shade the row is drawn on and the colour of its stripe, so
    the score was a third way of saying one thing, in the one place a reader
    is looking for something the colour cannot tell them.

    The item has to be really scored for the first assertion to mean anything.
    Written against ``_item(..., priority_score=51200)`` the number never
    reached the row even before the change -- the database recomputed the score
    to 0, so what the old code printed was ``P 0`` and ``"51200" in text`` was
    dead either way.
    """
    item = _scored_item(manager, "Draft the proposal")
    row = build_item_row(
        root, item, 0, already_blocked=False, work_block_minutes=30
    )

    texts = [
        child.cget("text") for child in row.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
    assert not any(str(item.priority_score) in text for text in texts), (
        f"the priority score ({item.priority_score}) is still on the row: "
        f"{texts}"
    )
    assert not any(text.startswith("P ") for text in texts), (
        f"the row still carries a P-prefixed score: {texts}"
    )


def test_pdm11_the_item_row_uses_the_chips_column_order(root, manager):
    """PD-M1.1 - the row's first line is laid out like a task inside a box.

    The ask was for the left pane's items to be formatted like the right
    pane's. Asserted against a real chip, not against four numbers written
    here: the whole point is that the two panes cannot drift apart, and a test
    carrying its own copy of the widths would pass while they did.

    Both halves are asserted. The roles say the order is the same -- stripe,
    title, bars, length -- and the minsizes say the columns are the same
    widths, which is what makes the two panes line up rather than merely
    agree on sequence.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    _pane, slot_row = _one_slot_pane(
        root, block, width=600, mapped=False, items_by_id={item.id: item}
    )
    chip = slot_row.block_widgets[0][1]
    # Its own container: ``_one_slot_pane`` packs into ``root``, and an item
    # row grids into whatever it is handed.
    holder = ctk.CTkFrame(root)
    holder.pack(fill="both", expand=True)
    row = build_item_row(
        holder, item, 0, already_blocked=False, work_block_minutes=30
    )

    columns = _row_columns(row, item.title)
    # Changed with PD-M9: every row now carries a mark, so an unblocked row
    # has a marker too. The behaviour changed intentionally -- the column used
    # to be empty unless the item was blocked -- and the set is asserted
    # whole rather than loosened, so a row that lost a part still fails here.
    assert set(columns) == {"stripe", "title", "marker", "bars", "length"}, (
        f"the row is missing a part: found {sorted(columns)} -- an incomplete "
        "row would make the comparison below vacuous"
    )
    # The chip's marker column is empty by design: the mark is about the item
    # list, and a box the task is already in has nothing to say about whether
    # it is scheduled. So the comparison is over the parts both panes draw.
    chip_columns = _row_columns(chip, item.title)
    shared = {role: column for role, column in columns.items() if role != "marker"}
    assert shared == chip_columns, (
        f"the item row puts its parts in {shared} and a box chip in "
        f"{chip_columns}"
    )

    # Every column, counted off the shared table rather than written here:
    # the marker column was added to both panes at once and a hard-coded 4
    # would have stopped looking at the one column it changed.
    for column in range(len(chip_column_minsizes())):
        mine = row.grid_columnconfigure(column)["minsize"]
        theirs = chip.grid_columnconfigure(column)["minsize"]
        assert mine == theirs, (
            f"column {column} is {mine}px on an item row and {theirs}px on a "
            "box chip -- the two panes do not line up"
        )


def test_pdm15_an_item_rows_title_column_follows_the_same_setting(
    root, manager, settings
):
    """PD-M1.1 — the live width reaches the left pane too, not just the right.

    ``test_pdm11_the_item_row_uses_the_chips_column_order`` compares the two
    panes at the default, which is the one width they agree on for free.
    Dropping ``title_width=self.box_title_width()`` from the item-row call site
    passes that test and leaves the panes lined up at 80px and nowhere else --
    which is the whole of what the setting is for.
    """
    item = _item(manager, "Draft the proposal")
    _one_block_day(manager, item)
    settings.drag_schedule_title_col_width = 173
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()

    title = _find_label(panel.items_scroll, item.title)
    assert title is not None, "the item is not in the left pane at all"
    row = title.master
    assert row.grid_columnconfigure(1)["minsize"] == 173, (
        f"the item row's title column asks for "
        f"{row.grid_columnconfigure(1)['minsize']}px, not the Drag Schedule "
        "width the boxes use"
    )
    chip = panel._block_widgets[0][0]
    assert row.grid_columnconfigure(1)["minsize"] == (
        chip.grid_columnconfigure(1)["minsize"]
    ), "the two panes' title columns are different widths"


def test_pdm12_the_length_sits_beside_the_depth_bars(root, manager):
    """PD-M1.2 - the length is next to the bars on one line, not under them.

    This replaces ``test_pbm63_the_work_block_length_is_under_the_depth_bars``,
    which asserted the same column and a lower row. That test is not wrong
    about what it saw; the behaviour changed intentionally -- PB-M6.3 put the
    length under the bars to mirror a box, and PD-M1 makes the row mirror the
    box properly, which puts both on the chip's single line.
    """
    item = _item(manager, "Draft the proposal", depth="Medium")
    row = build_item_row(
        root, item, 0, already_blocked=False, work_block_minutes=45
    )

    bars = next(
        child for child in row.winfo_children()
        if isinstance(child, DepthBarStack)
    )
    duration = next(
        child for child in row.winfo_children()
        if isinstance(child, ctk.CTkLabel) and child.cget("text") == "45m"
    )

    bars_at = bars.grid_info()
    duration_at = duration.grid_info()
    assert int(duration_at["row"]) == int(bars_at["row"]), (
        f"the length is on row {duration_at['row']} and the bars on "
        f"{bars_at['row']} -- they are not on one line"
    )
    assert int(duration_at["column"]) == int(bars_at["column"]) + 1, (
        f"the length is in column {duration_at['column']} and the bars in "
        f"{bars_at['column']} -- it is not the next column along"
    )


def test_pdm16_the_depth_bars_are_justified_like_the_text_on_the_line(
    root, manager
):
    """PD-M1.6 — the stack takes the title's own vertical justification.

    Three versions of this, each reported from the screen. ``sticky="n"``
    floated the stack above the title, because the stack is 13px and a line of
    text is taller. ``sticky="s"`` sat it under the title's baseline. Neither
    is how the text beside it is placed: the label is centred on the line, so
    the stack is centred too -- "justify vertically like TEXT on the line".

    Two claims, each with its own assertion, because they fail separately:
    the stack is centred in its cell rather than pinned to an edge, and the
    bars fill the stack with no slack at either end. The second is why the
    gap comes off the last bar -- a trailing gap inside a centred frame puts
    every bar 1px high, which is exactly the kind of off-by-one that reads as
    "still not lined up".
    """
    item = _item(manager, "Draft the proposal", depth="Deep")
    row = build_item_row(
        root, item, 0, already_blocked=False, work_block_minutes=45
    )
    root.update_idletasks()

    bars = next(
        child for child in row.winfo_children()
        if isinstance(child, DepthBarStack)
    )
    title = next(
        child for child in row.winfo_children()
        if isinstance(child, ctk.CTkLabel) and child.cget("text") == item.title
    )

    sticky = str(bars.grid_info()["sticky"])
    assert "n" not in sticky and "s" not in sticky, (
        f"the stack is gridded sticky={sticky!r}, which pins it to an edge of "
        "its cell rather than centring it the way the title is placed"
    )

    # Measured on the bars, not on the frame around them: a frame centres
    # whatever is inside it, so a frame-level measurement cannot see a gap
    # under the last bar.
    stack_bars = [
        child for child in bars.winfo_children()
        if isinstance(child, ctk.CTkFrame)
    ]
    assert len(stack_bars) == MAX_DEPTH_BARS, (
        f"the stack holds {len(stack_bars)} bars, not {MAX_DEPTH_BARS}"
    )
    above = min(bar.winfo_y() for bar in stack_bars)
    below = bars.winfo_reqheight() - max(
        bar.winfo_y() + bar.winfo_reqheight() for bar in stack_bars
    )
    assert (above, below) == (0, 0), (
        f"the bars sit {above}px from the top of the stack and {below}px from "
        "its bottom, so centring the stack does not centre the bars"
    )

    # What the two claims add up to, with the 1px Tk's own integer centring
    # can introduce on a cell of odd height.
    bars_middle = 2 * bars.winfo_y() + bars.winfo_reqheight()
    title_middle = 2 * title.winfo_y() + title.winfo_reqheight()
    assert abs(bars_middle - title_middle) <= 1, (
        f"the stack's middle is at {bars_middle / 2}px and the title's at "
        f"{title_middle / 2}px -- they are not on the same line"
    )


def _length_label(widget):
    """The ``NNm`` label on a task's line, in either pane."""
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel) and re.fullmatch(
            r"\d+m", str(child.cget("text"))
        ):
            return child
    raise AssertionError(
        f"no length label on {widget}: "
        f"{[str(c.cget('text')) for c in widget.winfo_children() if isinstance(c, ctk.CTkLabel)]}"
    )


def _right_pad(widget):
    """The right-hand padx a widget was gridded with."""
    pads = [int(n) for n in re.findall(r"\d+", str(widget.grid_info().get("padx", 0)))]
    return pads[-1] if pads else 0


def test_pd2_every_block_ends_short_of_its_right_edge(root, manager):
    """The length does not run to the edge of the box or the row it is in.

    Asked for as a 5-10px buffer on the right end of the blocks, all of them,
    and so asserted in both panes from one constant: the length label is the
    last thing on a task's line either side of the divider, and before this it
    was gridded hard against the edge.

    The inset is counted into the length's own column in
    ``chip_column_minsizes``, which is what keeps PD-M2's width floor and the
    two panes' alignment honest about it.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    _pane, slot_row = _one_slot_pane(
        root, block, width=600, mapped=False, items_by_id={item.id: item}
    )
    chip = slot_row.block_widgets[0][1]
    holder = ctk.CTkFrame(root)
    holder.pack(fill="both", expand=True)
    row = build_item_row(
        holder, item, 0, already_blocked=False, work_block_minutes=30
    )

    assert CHIP_RIGHT_INSET_PX >= 5, (
        f"the inset is {CHIP_RIGHT_INSET_PX}px, below the 5px asked for"
    )
    for name, widget in (("a day box", chip), ("an item row", row)):
        assert _right_pad(_length_label(widget)) == CHIP_RIGHT_INSET_PX, (
            f"the length on {name} is gridded {_right_pad(_length_label(widget))}px "
            f"from the right edge, not {CHIP_RIGHT_INSET_PX}px"
        )

    assert chip_column_minsizes()[CHIP_LENGTH_COLUMN] == (
        SLOT_LENGTH_WIDTH_PX + CHIP_RIGHT_INSET_PX
    ), (
        "the inset is not counted into the length's column, so the pane can be "
        "dragged to a width that cuts it off"
    )


def test_pd3_the_length_is_body_size_in_both_panes(root, manager):
    """``30m`` is read as often as the title beside it, so it is as big.

    Asserted against the title's own font rather than a number: the two sit on
    one line and the complaint was that one of them was smaller than the text
    around it, which is a relationship, not a value.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    _pane, slot_row = _one_slot_pane(
        root, block, width=600, mapped=False, items_by_id={item.id: item}
    )
    chip = slot_row.block_widgets[0][1]
    holder = ctk.CTkFrame(root)
    holder.pack(fill="both", expand=True)
    row = build_item_row(
        holder, item, 0, already_blocked=False, work_block_minutes=30
    )

    def title_label(widget):
        for child in widget.winfo_children():
            if isinstance(child, ctk.CTkLabel) and str(child.cget("text")) == item.title:
                return child
        raise AssertionError(f"no title label on {widget}")

    for name, widget in (("a day box", chip), ("an item row", row)):
        shown = _length_label(widget).cget("font")
        beside = title_label(widget).cget("font")
        assert shown.cget("size") == beside.cget("size"), (
            f"on {name} the length is {shown.cget('size')}pt and the title "
            f"beside it is {beside.cget('size')}pt"
        )


def test_pdm14_the_blocked_marker_is_a_glyph_left_of_the_depth_bars(root, manager):
    """PD-M1.5 — one line: the marker is a glyph in its own column, not words.

    It was "already blocked" on a second line until the row had to be the size
    of the space the item will take. A second line needs 66px whatever the box
    height is, which at any realistic setting is two boxes' worth, so every row
    was drawn at that floor and a half-hour item looked the size of an hour.
    Changed deliberately: the fact is still on the row, in a column left of the
    depth bars, and the row is one line tall.

    The depth word is still absent, and for its own reason -- the shade, the
    stripe and the bar stack all say it already.
    """
    item = _item(manager, "Draft the proposal", depth="Medium")
    row = build_item_row(
        root, item, 0, already_blocked=True, work_block_minutes=30
    )

    def lines(widget):
        return {
            int(child.grid_info()["row"])
            for child in widget.winfo_children()
            if isinstance(child, ctk.CTkLabel) and child.grid_info()
        }

    assert lines(row) == {0}, (
        f"the row writes text on more than its own line: rows {sorted(lines(row))}"
    )

    columns = _row_columns(row, item.title)
    assert columns.get("marker") == CHIP_MARKER_COLUMN, (
        f"the blocked marker is in column {columns.get('marker')}, not the "
        f"marker column {CHIP_MARKER_COLUMN}"
    )
    assert columns["marker"] < columns["bars"], (
        f"the marker is in column {columns['marker']} and the depth bars in "
        f"{columns['bars']} -- the marker goes to the left of the bars"
    )

    texts = [
        str(child.cget("text")) for child in row.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
    assert not any(item.depth in shown for shown in texts), (
        f"the depth word {item.depth!r} is still written on the row: {texts}"
    )
    assert not any("blocked" in shown.lower() for shown in texts), (
        f"the words came back: {texts}"
    )

    plain = build_item_row(
        root, item, 1, already_blocked=False, work_block_minutes=30
    )
    # Changed with PD-M9: the column now says something either way, so the
    # claim is that it says the right one. The original assertion was that an
    # unblocked row had no marker at all, and it would have gone on passing
    # for the wrong reason -- ``_row_columns`` knew only the blocked glyph, so
    # a row marked with the new one read as unmarked.
    plain_marks = [
        str(child.cget("text")) for child in plain.winfo_children()
        if isinstance(child, ctk.CTkLabel)
        and str(child.cget("text")) in (PD_BLOCKED_TEXT, PD_UNSCHEDULED_TEXT)
    ]
    assert plain_marks == [PD_UNSCHEDULED_TEXT], (
        f"an item with no block today is marked {plain_marks}, not as "
        f"unscheduled"
    )


def test_pdm9_a_scheduled_item_is_checked_and_an_unscheduled_one_questioned(
    root, manager
):
    """PD-M9 — "a schedule item gets a GREEN Check Mark, an unscheduled item
    gets a RED ?".

    One column, two answers, drawn either way: before this the column said
    something about a blocked item and nothing at all about the rest, so an
    unscheduled item and an unmarked row looked the same.
    """
    item = _item(manager, "Draft the proposal", depth="Medium")

    scheduled = build_item_row(
        root, item, 0, already_blocked=True, work_block_minutes=30
    )
    unscheduled = build_item_row(
        root, item, 1, already_blocked=False, work_block_minutes=30
    )

    def marker(row):
        found = [
            child for child in row.winfo_children()
            if isinstance(child, ctk.CTkLabel)
            and str(child.cget("text")) in (PD_BLOCKED_TEXT, PD_UNSCHEDULED_TEXT)
        ]
        assert len(found) == 1, (
            f"the row draws {len(found)} marks, not one: "
            f"{[str(c.cget('text')) for c in found]}"
        )
        return found[0]

    palette = semantic_colors()
    check = marker(scheduled)
    assert str(check.cget("text")) == PD_BLOCKED_TEXT
    assert check.cget("text_color") == palette["scheduled_mark"], (
        f"the check is {check.cget('text_color')}, not the scheduled mark "
        f"{palette['scheduled_mark']}"
    )
    question = marker(unscheduled)
    assert str(question.cget("text")) == PD_UNSCHEDULED_TEXT
    assert question.cget("text_color") == palette["unscheduled_mark"], (
        f"the question mark is {question.cget('text_color')}, not the "
        f"unscheduled mark {palette['unscheduled_mark']}"
    )
    assert (
        palette["scheduled_mark"] != palette["unscheduled_mark"]
    ), "the two marks are the same colour, so only the glyph tells them apart"
    assert int(check.grid_info()["column"]) == CHIP_MARKER_COLUMN
    assert int(question.grid_info()["column"]) == CHIP_MARKER_COLUMN


def test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it(
    root, manager, settings, mapped_windows
):
    """PD-M1.4 - four columns in the real pane, at the real settings.

    ``test_pbm61_every_line_of_a_row_is_drawn_inside_it`` measures the row
    vertically, which was the risk when the row was two stacked lines. Putting
    the stripe, the title, the bars and the length on one line makes width the
    risk instead, and that is what this measures.

    Through ``PlanScreen``, and that is the whole lesson of this test. The
    first version built the row by hand in a frame of
    ``PLAN_ITEMS_COL_WIDTH_PX`` and let ``title_width`` default to
    ``SLOT_TITLE_WIDTH_PX`` -- the 80px *fallback*. The setting's real default
    is 220, so in the app the row asked for 306px inside a 256px pane and the
    ``30m`` label was laid out entirely past the right edge: invisible, in
    every item row, while this test was green. Built from the screen, the
    widths are the ones the user has.
    """
    item = _item(manager, "Draft the proposal")
    panel = PlanScreen(root, manager, _App(settings))
    panel.pack(fill="both", expand=True)
    panel.selected_date = THURSDAY
    panel.refresh()
    root.geometry("1200x700")
    root.deiconify()
    root.update_idletasks()
    root.update()

    title = _find_label(panel.items_scroll, item.title)
    assert title is not None, "the item is not in the left pane at all"
    row = title.master
    width = row.winfo_width()
    assert width > 1, "the row itself was not laid out"

    for child in row.winfo_children():
        shown = (
            child.cget("text") if isinstance(child, ctk.CTkLabel)
            else type(child).__name__
        )
        assert child.winfo_width() > 1, (
            f"{shown!r} is {child.winfo_width()}px wide in a {width}px row -- "
            "it has been squeezed out"
        )
        assert child.winfo_x() >= 0, (
            f"{shown!r} starts at x={child.winfo_x()}, left of the row"
        )
        right = child.winfo_x() + child.winfo_width()
        assert right <= width, (
            f"{shown!r} ends at {right} in a {width}px row -- it is clipped"
        )
def test_pbm71_a_continuation_box_is_the_colour_of_its_task(root, manager):
    """PB-M7.1 — the later boxes of a long task are shaded like the first.

    They were transparent, on the argument that shading a continuation would
    read as a second task of equal weight. On screen the opposite happened: a
    90-minute task was one coloured box followed by two empty ones, which
    reads as a task that stops after half an hour. The arrow is what says
    "same task, continued", and the colour is what says which task.

    Both halves of this had to be fixed before it could fail for the thing it
    is named after. The item was built with ``priority_score=51200``, which the
    database recomputed to 0, and the pane was rendered with an empty
    ``items_by_id``, so the chip's item was ``None``: band ``unscored`` on both
    sides, and an implementation that filled every continuation with the
    unscored tint regardless of its task would have passed. Hence the real
    factors, the lookup, and the last assertion.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    block.planned_minutes = 90
    _pane, row = _one_slot_pane(
        root, block, width=600, continued=True, mapped=False,
        items_by_id={item.id: item},
    )

    assert row.block_widgets == [], "this box starts no task"
    chip = _find_continuation_chip(row.frame)
    assert chip is not None, "no continuation chip in the second box"

    assert _as_hex(chip, chip.cget("fg_color")) == _as_hex(
        chip, fill_for_item(item)
    ), f"the continuation is {chip.cget('fg_color')}, not the task's shade"
    assert _as_hex(chip, chip.cget("fg_color")) != _as_hex(
        chip, fill_for_item(None)
    ), "the continuation is the unscored tint, so it says nothing about which task"

    stripe = next(
        child for child in chip.winfo_children()
        if isinstance(child, ctk.CTkFrame)
    )
    assert _as_hex(stripe, stripe.cget("fg_color")) == _as_hex(
        stripe, stripe_for_item(item)
    ), "the continuation's bar is not the task's bar"
    assert _as_hex(stripe, stripe.cget("fg_color")) != _as_hex(
        stripe, stripe_for_item(None)
    ), "the continuation's bar is the unscored bar"


def test_pbm71_a_continuation_box_keeps_its_arrow(root, manager):
    """PB-M7.2 — shaded, and still marked as the same task.

    The arrow is the whole of what distinguishes a continuation now that the
    colour no longer does, so it is asserted separately from the colour: a
    change that dropped it would otherwise pass as a colour fix.
    """
    item = _scored_item(manager, "Draft the proposal")
    block = _item_block()
    block.item_id = item.id
    block.planned_minutes = 90
    _pane, row = _one_slot_pane(
        root, block, width=600, continued=True, mapped=False,
        items_by_id={item.id: item},
    )

    texts = _label_texts(row.frame)
    assert any(text.startswith("↳ ") for text in texts), (
        f"no continuation arrow on the box: {texts}"
    )
    assert any("Draft the proposal" in text for text in texts), (
        f"the continuation does not name its task: {texts}"
    )


# --- PD-M2 : the divider between the panes drags ---------------------------


def _drag_the_grip(panel, pixels, *, release=True, start=500):
    """Press the grip, move it ``pixels`` to the right, release.

    Positive is rightward: the items column grows and the day gives up the
    width. The press position is arbitrary -- the handler works in deltas from
    wherever it was pressed -- so it is named once here rather than chosen
    again in every test.

    The release lands past the last motion, which is what a real drag does:
    Tk's last ``<B1-Motion>`` is wherever the pointer was when it last moved,
    not where the button came up. Releasing at the same place as the final
    motion made every one of these tests pass against a release handler that
    ignored its own event and wrote whatever the last motion had left.
    """
    panel.on_divider_press(_FakeEvent(start, 0))
    panel.on_divider_motion(_FakeEvent(start + pixels // 2, 0))
    if release:
        panel.on_divider_release(_FakeEvent(start + pixels, 0))
    else:
        panel.on_divider_motion(_FakeEvent(start + pixels, 0))


def test_pdm28_the_grip_is_the_whole_gap_between_the_panes(
    root, manager, settings
):
    """PD-M2.8 — 15px of grip, and nothing beside it that is not grip.

    The first version drew a 6px grip with a 2px pad on each side: a 10px gap
    in which only the middle 6px started a drag. The gap and the grip are now
    one thing, so a press anywhere in the gap is a press on the grip.
    """
    panel = PlanScreen(root, manager, _App(settings))

    assert int(panel.divider.cget("width")) == 15, (
        f"the grip is {panel.divider.cget('width')}px wide, not 15"
    )
    assert panel.grid_columnconfigure(1)["minsize"] == PLAN_DIVIDER_WIDTH_PX, (
        "the grip's column is not the width of the grip, so the gap on screen "
        "is not what can be pressed"
    )

    def inner_pads(column):
        """The two panes' padx, as (left, right) integers."""
        frame = panel.grid_slaves(row=1, column=column)[0]
        pads = re.findall(r"-?\d+", str(frame.grid_info()["padx"]))
        return (int(pads[0]), int(pads[-1]))

    assert inner_pads(0) == (PLAN_PANE_EDGE_PAD_PX, 0), (
        f"the items pane's padx is {inner_pads(0)} -- a pad between it and "
        "the grip is gap the pointer cannot press"
    )
    assert inner_pads(2) == (0, PLAN_PANE_EDGE_PAD_PX), (
        f"the day pane's padx is {inner_pads(2)} -- a pad between it and the "
        "grip is gap the pointer cannot press"
    )


def test_pdm21_dragging_the_grip_changes_the_items_column(
    root, manager, settings
):
    """PD-M2.1 — the column follows the pointer, both ways, by the delta.

    Both directions, and the second motion from the same press, because the
    handler works from where the press was and not from where the last motion
    left off: a handler that applied each motion's delta to the current width
    would pass a single rightward drag and double every one after it.

    The width is set before the screen is built, which is the only way it
    changes under the app: the Settings entry hands the app a fresh settings
    object and the Plan screen reads the field when it is next built, so a
    live screen never has a setting it has not drawn. This test used to set it
    on a screen already up and lean on the press re-reading it -- the premise
    the press no longer has, because reading the setting there wrote a clamped
    width over it on a click that moved nothing
    (``::test_pdm23_a_click_on_the_grip_does_not_save_the_clamped_width``).
    """
    # Well clear of the floor at both ends, so this test is about the delta
    # and not about the clamp.
    sizer = PlanScreen(root, manager, _App(settings))
    settings.plan_items_col_width = sizer.items_width_floor() + 100
    panel = PlanScreen(root, manager, _App(settings))
    before = panel.items_col_width()

    panel.on_divider_press(_FakeEvent(500, 0))
    panel.on_divider_motion(_FakeEvent(540, 0))
    assert panel.grid_columnconfigure(0)["minsize"] == before + 40, (
        f"40px right of a {before}px column gave "
        f"{panel.grid_columnconfigure(0)['minsize']}px"
    )

    panel.on_divider_motion(_FakeEvent(460, 0))
    assert panel.grid_columnconfigure(0)["minsize"] == before - 40, (
        f"40px left of the press gave "
        f"{panel.grid_columnconfigure(0)['minsize']}px, not {before - 40}"
    )


def test_pdm22_the_items_pane_cannot_be_dragged_shut(root, manager, settings):
    """PD-M2.2 — the left end, where the clamp is a width a row can be drawn in.

    The floor is what a task's own line asks for plus the pane's chrome, not a
    round number: the columns are the chip's, one of them is a setting, and a
    hand-picked floor would be wrong the moment the title width changed.
    """
    panel = PlanScreen(root, manager, _App(settings))
    floor = panel.items_width_floor()
    assert floor > 0, "the floor is not a width at all"
    settings.plan_items_col_width = floor + 100

    _drag_the_grip(panel, -1000, release=False)
    assert panel.grid_columnconfigure(0)["minsize"] == floor, (
        f"dragged to {panel.grid_columnconfigure(0)['minsize']}px, past the "
        f"{floor}px a row needs"
    )

    settings.drag_schedule_title_col_width = 300
    wider = PlanScreen(root, manager, _App(settings))
    assert wider.items_width_floor() > floor, (
        "the floor ignores the title column width, so a wide title can still "
        "be dragged out of its own pane"
    )


def test_pdm22_the_day_pane_cannot_be_dragged_shut(
    root, manager, settings, mapped_windows
):
    """PD-M2.2 — the right end, which only exists on a window with a width.

    Clamped against the real window, because that is the only place the day's
    share is known: on an unmapped screen ``winfo_width`` is 1 and there is no
    right-hand end to clamp to. So this is the one PD-M2 test that needs a
    window on screen, and it is the half that cannot be checked without one.
    """
    panel = PlanScreen(root, manager, _App(settings))
    settings.plan_items_col_width = panel.items_width_floor() + 100
    panel.pack(fill="both", expand=True)
    root.geometry("1000x700")
    root.deiconify()
    root.update_idletasks()
    root.update()

    room = panel.winfo_width()
    assert room > 1, "the panel was not laid out, so there is nothing to clamp"

    _drag_the_grip(panel, 5000, release=False)
    widest = room - PLAN_PANE_CHROME_PX - panel.day_width_floor()
    assert panel.grid_columnconfigure(0)["minsize"] == widest, (
        f"dragged to {panel.grid_columnconfigure(0)['minsize']}px in a "
        f"{room}px screen, leaving the day less than the "
        f"{panel.day_width_floor()}px one of its rows needs"
    )


def test_pdm22_a_narrow_window_takes_the_width_from_the_items_pane(
    root, manager, settings, monkeypatch
):
    """PD-M2.2 — the window is as able to squeeze a pane shut as the grip is.

    Column 0 has a minsize and column 2 has a weight, so in a window too narrow
    for both floors the entire shortfall came out of the day pane -- the side
    with nothing holding it open -- and the block length was laid out past the
    right edge of every box. The clamp only ran while the grip was held, so
    narrowing the window, or simply setting a wide title column, reached a state
    no drag could have reached.

    ``winfo_width`` is patched rather than the window resized: this is the
    division of a known width, and a real window would make the test depend on
    the host's screen. ``monkeypatch`` puts the real method back.
    """
    panel = PlanScreen(root, manager, _App(settings))
    floor = panel.items_width_floor()
    settings.plan_items_col_width = floor + 200
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor + 200, (
        "precondition: with no width to measure the setting is drawn as asked"
    )

    # Both floors, the grip and the two edge pads, and 40px of slack. The
    # chrome is in the sum because the clamp takes it off the window before it
    # divides what is left: the behaviour changed when the grip was widened,
    # and a window of both floors plus 40 no longer has 40px of slack in it.
    monkeypatch.setattr(
        panel,
        "winfo_width",
        lambda: floor + panel.day_width_floor() + PLAN_PANE_CHROME_PX + 40,
    )
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor + 40, (
        f"the items column kept {panel.grid_columnconfigure(0)['minsize']}px of a "
        f"{floor + panel.day_width_floor() + PLAN_PANE_CHROME_PX + 40}px window, "
        f"leaving the day less than the {panel.day_width_floor()}px one of its "
        "rows needs"
    )

    monkeypatch.setattr(panel, "winfo_width", lambda: 400)
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor, (
        "a window narrower than both floors has to stop at the items floor, "
        "not below it"
    )

    monkeypatch.setattr(panel, "winfo_width", lambda: 4000)
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor + 200, (
        "widening the window did not give back the width a narrow one took"
    )


def test_pdm29_the_clamp_leaves_room_for_the_grip_and_the_edges(
    root, manager, settings, monkeypatch
):
    """PD-M2.9 — a window is the two panes plus the grip plus the edges.

    The first version measured both floors against the whole window width,
    though ``PLAN_PANE_CHROME_PX`` of it is not pane at all. The day pane has
    nothing holding it open, so it absorbed all of that -- it could be left
    26px under its own floor, which is the clipping the floors were added to
    prevent, and widening the grip to 15px would have made it 35.

    ``winfo_width`` is patched rather than the window resized, as in
    ``::test_pdm22_a_narrow_window_takes_the_width_from_the_items_pane``: this
    is the division of a known width.
    """
    panel = PlanScreen(root, manager, _App(settings))
    floor = panel.items_width_floor()
    settings.plan_items_col_width = floor + 500
    exactly_both_floors = floor + panel.day_width_floor() + PLAN_PANE_CHROME_PX

    monkeypatch.setattr(panel, "winfo_width", lambda: exactly_both_floors + 40)
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor + 40, (
        f"the items column took {panel.grid_columnconfigure(0)['minsize']}px "
        f"of a {exactly_both_floors + 40}px window, which leaves the day pane "
        f"less than the {panel.day_width_floor()}px one of its rows needs "
        f"once the {PLAN_PANE_CHROME_PX}px of grip and edges are counted"
    )

    monkeypatch.setattr(panel, "winfo_width", lambda: exactly_both_floors)
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor, (
        "a window holding exactly both floors and the chrome has to draw the "
        "items column at its floor, leaving the day pane its own"
    )


def test_pdm22_a_resize_alone_rebalances_the_panes(
    root, manager, settings, mapped_windows
):
    """PD-M2.2 — the binding is the whole fix, so it is pinned on its own.

    ``on_resize`` divides the room correctly, and the test above proves it --
    by calling the method. Nothing called the *binding*: delete
    ``self.bind("<Configure>", self.on_resize)`` and the suite stayed green
    while the shipped screen never re-divided the panes at all. That is the
    same shape as the dead ``grid_rowconfigure`` this batch removed, except
    load-bearing -- a line no test could fail on, holding up the fix.

    A real window, because a synthetic event cannot stand in for one. The
    screen is unmapped in these fixtures: ``winfo_ismapped`` is 0 and
    ``winfo_manager`` is empty, and Tk delivers no ``<Configure>`` to a window
    that was never laid out, so ``event_generate`` on the frame's canvas --
    immediate or queued -- reached the binding not once. The first version of
    this test generated one and asserted against a recorder patched over
    ``apply_items_width``; the recorder was reachable (``on_resize`` resolves
    that name on ``self`` when it runs), so the event never arriving is the
    whole reason it saw nothing. Its own first assertion passed on
    CustomTkinter's internal ``<Configure>`` binding rather than on ours, so
    it read as a test of the bind while asserting nothing about it.
    """
    panel = PlanScreen(root, manager, _App(settings))
    floor = panel.items_width_floor()
    asked = floor + 300
    settings.plan_items_col_width = asked
    panel.pack(fill="both", expand=True)
    root.geometry(f"{asked + panel.day_width_floor() + 200}x700")
    root.deiconify()
    root.update_idletasks()
    root.update()

    assert panel.grid_columnconfigure(0)["minsize"] == asked, (
        f"a window with room for both panes drew the items column at "
        f"{panel.grid_columnconfigure(0)['minsize']}px, not the {asked}px "
        "setting, so no resize reached the clamp at all"
    )

    root.geometry(
        f"{floor + panel.day_width_floor() + PLAN_PANE_CHROME_PX + 40}x700"
    )
    root.update_idletasks()
    root.update()

    room = panel.winfo_width()
    assert room > 1, "the panel was not laid out, so there is nothing to clamp"
    for_panes = room - PLAN_PANE_CHROME_PX
    assert for_panes - panel.day_width_floor() < asked, (
        f"a {room}px window still has room for the {asked}px setting, so this "
        "resize asks nothing of the clamp"
    )
    assert (
        panel.grid_columnconfigure(0)["minsize"]
        == for_panes - panel.day_width_floor()
    ), (
        f"the items column kept {panel.grid_columnconfigure(0)['minsize']}px of "
        f"a {room}px window, leaving the day less than the "
        f"{panel.day_width_floor()}px one of its rows needs"
    )


def test_pdm23_a_click_on_the_grip_does_not_save_the_clamped_width(
    root, manager, settings, monkeypatch
):
    """PD-M2.3 — a gesture that moved nothing writes nothing.

    The press snapshots the width *drawn*, not the width in the settings file.
    The two differ whenever the window is too narrow for the setting, which the
    resize clamp turned from an edge case into an ordinary state, and
    snapshotting the setting meant the release saw a width that differed from
    it and wrote the clamped number over it -- on a click that moved nothing.

    The second half is the same bug seen from the other side: a drag that
    starts from the setting rather than from the column spends its first
    pixels inside the clamp, where the column does not move.
    """
    panel = PlanScreen(root, manager, _App(settings))
    floor = panel.items_width_floor()
    asked = floor + 300
    settings.plan_items_col_width = asked
    monkeypatch.setattr(
        panel,
        "winfo_width",
        lambda: floor + panel.day_width_floor() + PLAN_PANE_CHROME_PX + 40,
    )
    panel.on_resize()
    assert panel.grid_columnconfigure(0)["minsize"] == floor + 40, (
        "precondition: the window is too narrow for the setting, so the width "
        "drawn and the width in the file differ"
    )

    saved = []
    monkeypatch.setattr(
        settings,
        "save",
        lambda: saved.append(settings.plan_items_col_width) or True,
    )

    panel.on_divider_press(_FakeEvent(500, 0))
    panel.on_divider_release(_FakeEvent(500, 0))

    assert saved == [], f"a click that moved nothing wrote {saved}"
    assert settings.plan_items_col_width == asked, (
        f"the clamped width went over the {asked}px setting: "
        f"{settings.plan_items_col_width}"
    )

    panel.on_divider_press(_FakeEvent(500, 0))
    panel.on_divider_motion(_FakeEvent(460, 0))
    assert panel.grid_columnconfigure(0)["minsize"] == floor, (
        f"40px left of a {floor + 40}px column gave "
        f"{panel.grid_columnconfigure(0)['minsize']}px: the drag is measured "
        f"from the {asked}px setting, so its first {asked - floor - 40}px "
        "move nothing"
    )


def test_pdm23_the_file_is_written_once_on_release_not_per_motion(
    root, manager, settings, monkeypatch
):
    """PD-M2.3 — a drag is one write, at the end of it.

    A write per motion is a settings file written tens of times for one
    gesture, and every one of them a chance to fail halfway through a drag.
    Counted, not merely observed to happen: "it saves" holds for both.
    """
    panel = PlanScreen(root, manager, _App(settings))
    before = panel.items_col_width()
    saved = []
    monkeypatch.setattr(
        type(settings), "save",
        lambda self: saved.append(self.plan_items_col_width) or True,
    )

    panel.on_divider_press(_FakeEvent(500, 0))
    for x in (505, 515, 525):
        panel.on_divider_motion(_FakeEvent(x, 0))
    assert saved == [], f"the file was written mid-drag: {saved}"

    # Past the last motion, because that is where a real release lands.
    panel.on_divider_release(_FakeEvent(530, 0))
    assert saved == [before + 30], (
        f"release wrote {saved}, not one write of the width it ended at "
        f"({before + 30})"
    )


def test_pdm23_a_motion_or_release_without_a_press_does_nothing(
    root, manager, settings, monkeypatch
):
    """PD-M2.3 — the handlers are public and bound; they do not assume an order.

    Added because the mutation gate found the ``_divider_from_x is None`` guard
    was a line no test could fail on: every test pressed first, so the guard
    was never reached. Tk's implicit grab makes a stray motion hard to produce
    through the UI, which is an argument for the guard being cheap, not for it
    being unchecked -- these are plain methods on the screen and nothing in the
    class says they may only be called in order.
    """
    panel = PlanScreen(root, manager, _App(settings))
    before = panel.items_col_width()
    # Not the same number: the stored setting is the shipped 260 and
    # items_col_width() floors it to what a row needs. Each is checked
    # against itself.
    stored_before = settings.plan_items_col_width
    saved = []
    monkeypatch.setattr(
        type(settings), "save", lambda self: saved.append(1) or True
    )

    panel.on_divider_motion(_FakeEvent(900, 0))
    panel.on_divider_release(_FakeEvent(900, 0))

    assert panel.grid_columnconfigure(0)["minsize"] == before, (
        f"the column moved to {panel.grid_columnconfigure(0)['minsize']}px on "
        "a motion that followed no press"
    )
    assert saved == [], "a release with no press wrote the settings file"
    assert settings.plan_items_col_width == stored_before, (
        "a release with no press changed the stored width from "
        f"{stored_before} to {settings.plan_items_col_width}"
    )


def test_pdm24_a_refused_write_leaves_the_old_width(
    root, manager, settings, monkeypatch
):
    """PD-M2.4 — P41: this screen's settings object is the app's own.

    So a width left on it after a refused write is not merely a wrong number
    in memory: every screen built from that object afterwards draws it, and the
    user sees a resized pane that no file knows about and that the next launch
    silently undoes. Put back, and said on screen.
    """
    app = _App(settings)
    panel = PlanScreen(root, manager, app)
    settings.plan_items_col_width = panel.items_width_floor() + 100
    before = panel.items_col_width()
    monkeypatch.setattr(type(settings), "save", lambda self: False)
    settings.last_save_error = "settings file is read-only"

    _drag_the_grip(panel, 60)

    assert settings.plan_items_col_width == before, (
        f"the app's settings object holds {settings.plan_items_col_width}, a "
        f"width nothing wrote -- it had {before}"
    )
    assert panel.grid_columnconfigure(0)["minsize"] == before, (
        "the column kept the dragged width after the write was refused"
    )
    assert app.settings is settings, (
        "the app and the screen no longer share one settings object, so this "
        "test is not about the alias P41 is about"
    )
    assert "read-only" in panel.items_hint.cget("text"), (
        f"the refusal is not on screen: {panel.items_hint.cget('text')!r}"
    )


def test_pdm25_the_dragged_width_survives_a_rebuild(root, manager, settings):
    """PD-M2.5 — read back off the file, not off the object that was mutated.

    Asserting against ``settings`` would pass with no write at all, since the
    drag mutates that very object. ``AppSettings.load()`` is what a later
    launch, and the Settings screen, actually see.
    """
    panel = PlanScreen(root, manager, _App(settings))
    expected = panel.items_col_width() + 44
    _drag_the_grip(panel, 44)

    reloaded = AppSettings.load()
    assert reloaded.plan_items_col_width == expected, (
        f"the file holds {reloaded.plan_items_col_width}, not {expected}"
    )
    rebuilt = PlanScreen(root, manager, _App(reloaded))
    assert rebuilt.grid_columnconfigure(0)["minsize"] == expected


def test_pdm26_the_grip_and_the_settings_field_are_one_value(
    root, manager, settings
):
    """PD-M2.6 — the grip writes the field the Settings entry is built from.

    Two surfaces for one width. Settings to grip is
    ``test_the_items_column_is_the_width_the_setting_asks_for``; this is the
    other direction, asserted through the entry rather than through the
    attribute name, so a grip that wrote a field of its own would fail it.

    Built after the width is set, for the reason given in
    ``::test_pdm21_dragging_the_grip_changes_the_items_column``: the press
    takes the width the column is drawn at, not the one in the file, so a
    screen that was up before the field changed would drag from the old one.
    """
    sizer = PlanScreen(root, manager, _App(settings))
    settings.plan_items_col_width = sizer.items_width_floor() + 100
    panel = PlanScreen(root, manager, _App(settings))
    expected = panel.items_col_width() + 25
    _drag_the_grip(panel, 25)

    # What SettingsScreen puts in the entry when it is next opened: its own
    # AppSettings.load(), read exactly as that screen reads it.
    opened = AppSettings.load()
    assert str(getattr(opened, "plan_items_col_width", 260)) == str(expected), (
        "the Settings entry would open at "
        f"{getattr(opened, 'plan_items_col_width', 260)}, not at the "
        f"{expected}px the grip was left at"
    )


# ================= PD-M3 — the AutoLoad button ==========================


def _short_day(root, manager, settings, end="09:30"):
    """A Plan screen on a day with only a few boxes in it.

    ``self.bounds`` is read once in ``__init__``, so the day has to be short
    before the screen is built. Three boxes is enough to run a day out of room
    inside a test without filling fourteen of them first.
    """
    settings.plan_day_start = "08:00"
    settings.plan_day_end = end
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()
    return panel


def _priced_item(manager, title, importance, urgency, size, value):
    """An item whose priority score is chosen, so the list order is chosen."""
    return _item(
        manager,
        title,
        importance=importance,
        urgency=urgency,
        size=size,
        value=value,
    )


def _placements(manager, block_date=THURSDAY):
    return {
        b.label: b.slot_index for b in manager.get_time_blocks(block_date)
    }


def test_pdm31_autoload_fills_in_list_order(screen, manager):
    """PD-M3.1 — one after another, from the top of the list down the day."""
    _priced_item(manager, "First", 20, 20, 16, 8)
    _priced_item(manager, "Second", 10, 10, 8, 4)
    _priced_item(manager, "Third", 5, 5, 4, 2)
    screen.refresh()

    order = [i.title for i in manager.get_items_for_start_date(THURSDAY)]
    assert order == ["First", "Second", "Third"], (
        f"precondition: the list is not in the order this test assumes: {order}"
    )

    screen.autoload_day()

    assert _placements(manager) == {"First": 0, "Second": 1, "Third": 2}, (
        _placements(manager)
    )


def test_pdm31_autoload_gives_a_long_task_its_own_boxes(screen, manager):
    """PD-M3.1 — a 90m task takes three boxes and the next item starts after.

    Written because the depth a box allows makes "the earliest box that will
    hold it" and "the earliest empty box" two different answers, and only the
    second is one after another. A 90m task placed at 08:00 and a 30m task
    placed at 08:00 beside it is what the first answer produces.
    """
    _priced_item(manager, "Long", 20, 20, 16, 8)
    _priced_item(manager, "Short", 10, 10, 8, 4)
    long_item = [i for i in manager.get_items_for_start_date(THURSDAY)
                 if i.title == "Long"][0]
    long_item.work_block = 90
    manager.update_action_item(long_item)
    screen.refresh()

    screen.autoload_day()

    placed = _placements(manager)
    assert placed == {"Long": 0, "Short": 3}, (
        f"the 90m task covers boxes 0, 1 and 2, so the next item starts at 3: {placed}"
    )


def test_pdm31_a_long_task_does_not_land_on_a_later_occupied_box(screen, manager):
    """PD-M3.1 — every box of a multi-box task has to be clear, not just the first.

    A box holding one task is not full, so the box the task *starts* in can be
    clear while the box it runs into is taken. Checking only the first box puts
    a 60m task at 08:00 on top of whatever is already sitting at 08:30.
    """
    _add_block(manager, 30, "Standing meeting", slot_index=1)
    _priced_item(manager, "Long", 20, 20, 16, 8)
    long_item = manager.get_items_for_start_date(THURSDAY)[0]
    long_item.work_block = 60
    manager.update_action_item(long_item)
    screen.refresh()

    screen.autoload_day()

    assert _placements(manager)["Long"] == 2, (
        "box 0 is clear but the 60m task runs into box 1, which is not: "
        f"{_placements(manager)}"
    )


def test_pdm32_autoload_skips_an_item_already_blocked(screen, manager):
    """PD-M3.2 — an item with a block today is not blocked a second time."""
    first = _priced_item(manager, "First", 20, 20, 16, 8)
    _priced_item(manager, "Second", 10, 10, 8, 4)
    manager.add_block_at(
        TimeBlock(
            block_date=THURSDAY,
            start_time="",
            end_time="",
            planned_minutes=30,
            item_id=first.id,
            label="First",
            block_type=BlockType.ITEM,
        ),
        4,
        screen.bounds,
    )
    screen.refresh()

    screen.autoload_day()

    for_first = [
        b.slot_index for b in manager.get_time_blocks(THURSDAY)
        if b.item_id == first.id
    ]
    assert for_first == [4], f"First was blocked again: {for_first}"
    assert _placements(manager) == {"First": 4, "Second": 0}, _placements(manager)


def test_pdm33_autoload_leaves_existing_blocks_untouched(screen, manager):
    """PD-M3.3 — purely additive: nothing already on the day moves or changes."""
    _add_block(manager, 30, "Standing meeting", slot_index=0)
    _add_block(manager, 60, "Workshop", slot_index=2)
    _priced_item(manager, "New", 20, 20, 16, 8)
    screen.refresh()
    before = {
        b.id: (b.slot_index, b.position, b.planned_minutes, b.start_time, b.end_time)
        for b in manager.get_time_blocks(THURSDAY)
    }
    assert len(before) == 2, "precondition: two blocks were put on the day"

    screen.autoload_day()

    after = {
        b.id: (b.slot_index, b.position, b.planned_minutes, b.start_time, b.end_time)
        for b in manager.get_time_blocks(THURSDAY)
    }
    for block_id, row in before.items():
        assert after.get(block_id) == row, (
            f"block {block_id} was {row} and is now {after.get(block_id)}"
        )
    assert _placements(manager)["New"] == 1, (
        f"the new block took the one clear box before the workshop: "
        f"{_placements(manager)}"
    )


def test_pdm34_autoload_does_not_straddle_lunch(screen, manager):
    """PD-M3.4 — a task long enough to reach lunch starts after it instead."""
    for index in range(7):
        _add_block(manager, 30, f"Taken {index}", slot_index=index)
    _priced_item(manager, "Long", 20, 20, 16, 8)
    long_item = manager.get_items_for_start_date(THURSDAY)[0]
    long_item.work_block = 90
    manager.update_action_item(long_item)
    screen.refresh()

    screen.autoload_day()

    placed = _placements(manager)["Long"]
    assert placed == 10, (
        "boxes 7, 8 and 9 would cover the 12:00 lunch, so the task starts at "
        f"10 (12:30); it went to {placed}"
    )


def test_pdm34_autoload_does_not_run_past_the_day_end(screen, manager):
    """PD-M3.4 — a task that would need a box past Day End does not fit."""
    for index in list(range(8)) + list(range(10, 17)):
        _add_block(manager, 30, f"Taken {index}", slot_index=index)
    _priced_item(manager, "Long", 20, 20, 16, 8)
    long_item = manager.get_items_for_start_date(THURSDAY)[0]
    long_item.work_block = 60
    manager.update_action_item(long_item)
    screen.refresh()
    before = len(manager.get_time_blocks(THURSDAY))

    screen.autoload_day()

    assert len(manager.get_time_blocks(THURSDAY)) == before, (
        "a 60m task needs two boxes and only 16:30 is left"
    )
    assert "1 did not fit" in screen.status_label.cget("text")


def test_pdm35_autoload_reports_all_three_counts(root, manager, settings):
    """PD-M3.5 — blocked, did not fit and already blocked, all three, always."""
    panel = _short_day(root, manager, settings, end="09:30")
    blocked = _priced_item(manager, "Blocked already", 20, 20, 16, 8)
    _priced_item(manager, "Fits", 10, 10, 8, 4)
    _priced_item(manager, "Also fits", 8, 8, 6, 4)
    _priced_item(manager, "No room", 5, 5, 4, 2)
    manager.add_block_at(
        TimeBlock(
            block_date=THURSDAY,
            start_time="",
            end_time="",
            planned_minutes=30,
            item_id=blocked.id,
            label="Blocked already",
            block_type=BlockType.ITEM,
        ),
        0,
        panel.bounds,
    )
    panel.refresh()

    panel.autoload_day()

    text = panel.status_label.cget("text")
    assert "blocked 2 of 4" in text, text
    assert "1 did not fit" in text, text
    assert "1 already blocked" in text, text


def test_pdm35_the_counts_cover_the_whole_list_not_just_the_rows_shown(
    root, manager, settings
):
    """PD-M3.5/P2/P9 — the four numbers add up to every item, including the capped.

    AutoLoad reads the item list and takes the first ``MAX_ITEM_ROWS`` of it,
    the same cap the pane draws. It then reported "blocked N of 60", so on a day
    with more items than that, the ones past the cap were in neither the
    numerator nor the denominator nor any of the other counts -- planned work
    silently absent from a report whose whole purpose is to say what was left
    out. The pane announces its cap; the button did not.

    Real-scale by construction: the fixture is three items past the cap, so the
    cap actually bites rather than being asserted against a list that fits.
    """
    from src.getmoredone.screens.plan import MAX_ITEM_ROWS

    panel = _short_day(root, manager, settings, end="09:30")
    total = MAX_ITEM_ROWS + 3
    for index in range(total):
        _item(manager, f"item {index:03d}")
    panel.refresh()

    panel.autoload_day()

    text = panel.status_label.cget("text")
    boxes = len(day_grid(panel.bounds))
    assert f"blocked {boxes} of {total}" in text, text
    assert f"{MAX_ITEM_ROWS - boxes} did not fit" in text, text
    assert "0 already blocked" in text, text
    assert f"3 past the {MAX_ITEM_ROWS}-row list" in text, text


def test_pdm35_an_uncapped_run_does_not_mention_the_cap(screen, manager):
    """The capped count is said only when there is one, so it means something."""
    _item(manager, "Only one")

    screen.autoload_day()

    text = screen.status_label.cget("text")
    assert "blocked 1 of 1" in text, text
    assert "row list" not in text, text


def test_pdm35_a_refusal_counts_what_it_tried_not_the_whole_list(
    screen, manager, monkeypatch
):
    """PD-M3.5 — the refusal arm's denominator is the run, not the item list.

    The success line counts every item, the capped ones included, because it
    reports on the whole list. The refusal line counts how far the run got
    through what it was *going* to try, which is the capped list: the items
    past the cap were never candidates, so putting them in the denominator
    would say the run refused with work outstanding that it had never looked
    at. They are still named, so the sentence accounts for the whole list.

    Both numbers are the same whenever the list fits, which is why the
    existing refusal test could not tell them apart: this one is three items
    past the cap, so they differ.
    """
    from src.getmoredone.screens.plan import MAX_ITEM_ROWS

    total = MAX_ITEM_ROWS + 3
    for index in range(total):
        _priced_item(manager, f"item {index:03d}", 20, 20, 16, 8)
    screen.refresh()

    real = type(manager).add_block_at
    calls = []

    def refuse_on_the_second(self, block, slot_index, bounds):
        calls.append(block.label)
        if len(calls) == 2:
            raise SlotRefusedError(SlotRefusal.SLOT_FULL)
        return real(self, block, slot_index, bounds)

    monkeypatch.setattr(type(manager), "add_block_at", refuse_on_the_second)

    screen.autoload_day()

    text = screen.status_label.cget("text")
    assert f"refused after 1 of {MAX_ITEM_ROWS} tried" in text, text
    assert f"3 past the {MAX_ITEM_ROWS}-row list" in text, text
    assert str(total) not in text, (
        f"the refusal counted all {total} items, including the "
        f"{total - MAX_ITEM_ROWS} the run was never going to try: {text}"
    )


def test_pdm37_a_failure_that_is_not_a_refusal_is_still_reported(
    screen, manager, monkeypatch, caplog
):
    """PD-M3.7 — AutoLoad caught only ``SlotRefusedError``.

    Any other exception escaped the Tk callback, which has no handler: nothing
    redrawn, nothing said, and a press that failed indistinguishable on screen
    from a press that found nothing to do.

    The failure is on the *second* item, so the rollback assertion can fail: a
    version that stubbed out the only write there is could not have written
    anything whether the transaction rolled back or not, and
    ``_stored(manager) == before`` would have held against no transaction at
    all. Here the first item really is written before the second raises.

    The exception carries no message, which is the other half of this. ``str``
    of a message-less built-in is the empty string, and the arm reported
    ``problem or type(problem).__name__`` -- an exception instance is always
    truthy, so that second branch could never be taken and the sentence ended
    at the dash.
    """
    _priced_item(manager, "First", 20, 20, 16, 8)
    _priced_item(manager, "Second", 10, 10, 8, 4)
    before = _stored(manager)
    real = manager.add_block_at
    calls = []

    def boom(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise KeyError()
        return real(*args, **kwargs)

    monkeypatch.setattr(manager, "add_block_at", boom)

    with caplog.at_level(logging.ERROR, logger="getmoredone.screens.plan"):
        screen.autoload_day()

    assert len(calls) == 2, f"the run did not reach a second item: {calls}"
    assert _stored(manager) == before, (
        f"the first item's block survived a failed run: {_stored(manager)}"
    )
    text = screen.status_label.cget("text")
    assert "AutoLoad wrote nothing" in text, text
    assert "KeyError" in text, text
    assert not text.rstrip().endswith("—"), text
    assert screen.status_label.cget("text_color") == status_text_color("error")
    # The status line is transient; the log is what is left to diagnose by.
    assert "AutoLoad failed" in caplog.text, caplog.text
    assert "KeyError" in caplog.text, caplog.text


def test_pdm36_a_full_day_writes_nothing(root, manager, settings):
    """PD-M3.6 — no room anywhere: nothing written, and the status says so."""
    panel = _short_day(root, manager, settings, end="09:30")
    for index in range(3):
        manager.add_block_at(
            TimeBlock(
                block_date=THURSDAY,
                start_time="",
                end_time="",
                planned_minutes=30,
                label=f"Taken {index}",
            ),
            index,
            panel.bounds,
        )
    _priced_item(manager, "Hopeful", 20, 20, 16, 8)
    panel.refresh()
    before = _stored(manager)

    panel.autoload_day()

    assert _stored(manager) == before, "AutoLoad wrote onto a full day"
    text = panel.status_label.cget("text")
    assert "blocked 0 of 1" in text, text
    assert "1 did not fit" in text, text
    assert panel.status_label.cget("text_color") == status_text_color("warning")


def test_pdm37_autoload_is_one_transaction(screen, manager, monkeypatch):
    """PD-M3.7 — a refusal part-way leaves none of the run, not half a day."""
    _priced_item(manager, "First", 20, 20, 16, 8)
    _priced_item(manager, "Second", 10, 10, 8, 4)
    _priced_item(manager, "Third", 5, 5, 4, 2)
    screen.refresh()
    assert _stored(manager) == [], "precondition: the day starts empty"

    real = type(manager).add_block_at
    calls = []

    def explode_on_the_second(self, block, slot_index, bounds):
        calls.append(block.label)
        if len(calls) == 2:
            raise SlotRefusedError(SlotRefusal.SLOT_FULL)
        return real(self, block, slot_index, bounds)

    monkeypatch.setattr(type(manager), "add_block_at", explode_on_the_second)

    screen.autoload_day()

    assert len(calls) == 2, (
        f"the run has to get past one successful write to have anything to "
        f"roll back: {calls}"
    )
    assert _stored(manager) == [], (
        f"the first block survived the refusal: {_stored(manager)}"
    )
    text = screen.status_label.cget("text")
    assert "wrote nothing" in text, text
    assert "refused after 1 of 3" in text, text
    # Pins the ``if unseen`` guard: a run that passed over nothing says
    # nothing about the cap, so the clause means something when it appears.
    assert "row list" not in text, text
    assert screen.status_label.cget("text_color") == status_text_color("error")


def test_pdm38_autoload_refuses_a_non_working_day(root, manager, settings):
    """PD-M3.8 — the Saturday refusal, with its reason, not a silent no-op."""
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    _priced_item(manager, "Weekend", 20, 20, 16, 8, )
    panel.refresh()

    panel.autoload_day()

    assert manager.get_time_blocks(SATURDAY) == [], "a block landed on a Saturday"
    assert "not a block day" in panel.status_label.cget("text")


def test_pdm3_autoload_on_an_empty_list_says_so(screen, manager):
    """No items is not the same answer as no room, and must not read like it."""
    assert manager.get_items_for_start_date(THURSDAY) == []

    screen.autoload_day()

    text = screen.status_label.cget("text")
    assert "nothing to block" in text, text
    assert _stored(manager) == []


# ================= PD-M5 — dropping above or below extends the day =======


def _pointer_on(screen, monkeypatch, *widgets):
    """Put the pointer inside these widgets, and nothing else.

    ``blocks_scroll`` is always included: both ``slot_under_pointer`` and
    ``virtual_under_pointer`` refuse outright unless the pointer is in the day
    pane, so a test that left it out would be asserting against that guard
    rather than against the box it meant to drop on.
    """
    inside = {id(screen.blocks_scroll)} | {id(w) for w in widgets}
    monkeypatch.setattr(screen, "winfo_pointerx", lambda: 0)
    monkeypatch.setattr(screen, "winfo_pointery", lambda: 0)
    monkeypatch.setattr(
        "src.getmoredone.screens.plan.widget_contains_pointer",
        lambda widget, x, y: id(widget) in inside,
    )


def _virtual(screen, edge):
    return [frame for frame, which in screen._virtual_frames if which == edge][0]


def _run_due_timers(widget, limit=50):
    """Run the zero-delay timer a drop defers itself to, and nothing else.

    ``TIMER_EVENTS`` and not every class of event, for two reasons. ``update()``
    -- which is all classes until the queue is empty -- does not always
    terminate in this suite: measured on 2026-11-07, the thirteenth
    ``PlanScreen`` built in one process did not come back from an ``update()``
    inside ``load_items``. And a bounded pass over *all* events does not get to
    the timer at all: the panes' own ``<Configure>`` traffic alone is more than
    200 events after a rebuild, so the drop was still waiting when the budget
    ran out. Timers only, bounded, so the worst case here is a failed
    assertion rather than a hung run or a dispatched stray click.
    """
    widget.update_idletasks()
    for _ in range(limit):
        if not widget.tk.dooneevent(_tkinter.TIMER_EVENTS | _tkinter.DONT_WAIT):
            return


def test_pdm51_a_virtual_box_sits_at_each_end(screen, manager):
    """PD-M5.1 — one above the first box and one below the last, every redraw."""
    assert [edge for _, edge in screen._virtual_frames] == [
        DAY_EXTEND_EARLIER,
        DAY_EXTEND_LATER,
    ], screen._virtual_frames

    slot_rows = [frame.grid_info()["row"] for frame, _ in _slot_frames(screen)]
    above = _virtual(screen, DAY_EXTEND_EARLIER).grid_info()["row"]
    below = _virtual(screen, DAY_EXTEND_LATER).grid_info()["row"]
    assert above < min(slot_rows), f"the Earlier box is at row {above}, not above {min(slot_rows)}"
    assert below > max(slot_rows), f"the Later box is at row {below}, not below {max(slot_rows)}"


def test_pdm51_the_virtual_boxes_survive_a_redraw_with_blocks_on_the_day(
    screen, manager
):
    """PD-M5.1 — drawn on a day that has work in it, not only on an empty one.

    The empty-day assertion above would hold for a screen that drew them in
    the ``if not blocks`` branch, where they would vanish the moment the first
    item was blocked -- taking away the drop target the user had just used.
    """
    _add_block(manager, 30, "Something", slot_index=3)
    screen.refresh()

    assert [edge for _, edge in screen._virtual_frames] == [
        DAY_EXTEND_EARLIER,
        DAY_EXTEND_LATER,
    ], screen._virtual_frames


def test_pdm51_a_virtual_box_says_which_end_it_is(screen):
    """PD-M5.1 — "marked as what they are and dimmed".

    An unlabelled empty rectangle at each end of the day is indistinguishable
    from a drawing mistake, and nothing would tell the user it can be dropped
    on.
    """
    palette = semantic_colors()
    for edge, word, hint in (
        (DAY_EXTEND_EARLIER, PD_EARLIER_TEXT, PD_EARLIER_HINT),
        (DAY_EXTEND_LATER, PD_LATER_TEXT, PD_LATER_HINT),
    ):
        frame = _virtual(screen, edge)
        texts = _label_texts(frame)
        assert word in texts, f"the {edge} box says {texts}, not {word!r}"
        assert hint in texts, f"the {edge} box has no drop hint: {texts}"
        dimmed = [
            child for child in frame.winfo_children()
            if isinstance(child, ctk.CTkLabel)
            and child.cget("text_color") == palette["muted_text"]
        ]
        assert len(dimmed) == 2, (
            f"the {edge} box draws {len(dimmed)} dimmed labels, not both of them"
        )


def test_pdm51_a_virtual_box_is_not_a_slot(screen):
    """They must never be offered to anything that places by slot index.

    ``_slot_frames`` is what ``slot_under_pointer`` and the hover outline read,
    and a virtual box in it would be a box the day does not have.
    """
    virtual = {id(frame) for frame, _ in screen._virtual_frames}
    assert virtual, "precondition: there are virtual boxes to confuse"
    for frame, index in _slot_frames(screen):
        assert id(frame) not in virtual, f"a virtual box is being offered as slot {index}"


def test_pdm131_an_earlier_drop_leaves_day_start_alone(screen, manager, settings):
    """PD-M13.1 — the item is blocked at 07:30 and Day Start is still 08:00.

    This asserted ``plan_day_start == "07:30"`` until PD-M13, under reason (b):
    the behaviour changed intentionally. The user's words were "when add to
    start and End of day do NOT change the length of Day in Settings". The box
    is now a negative index -- one span before the first drawn box -- and the
    day is drawn wide enough to show it, so the gesture is a decision about
    this item on this date instead of a redefinition of the working day for
    every date in the file.

    Both the settings object and the file are asserted, because the old
    version wrote to the object and then saved it: a fix that stopped only the
    save would leave the screen's own day changed for the rest of the session.
    """
    item = _item(manager, "Early start")
    assert settings.plan_day_start == "08:00", "precondition: the shipped day start"

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert [(row[0], row[1], row[3]) for row in _stored(manager)] == [
        ("Early start", -1, "07:30")
    ], _stored(manager)
    assert settings.plan_day_start == "08:00", settings.plan_day_start
    assert AppSettings.load().plan_day_start == "08:00", "the file was written anyway"
    assert screen.bounds.day_start == "08:00", "the screen redefined its own day"


def test_pdm131_a_long_item_dropped_above_goes_as_far_back_as_its_span(
    screen, manager, settings
):
    """PD-M13.1 — the span, not one box: a 90m item needs three half hours.

    Retargeted with the test above, same reason (b). What moves is the box the
    item lands on (-3, 06:30), not Day Start.
    """
    item = _item(manager, "Deep work", work_block=90)

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert [(row[0], row[1], row[3]) for row in _stored(manager)] == [
        ("Deep work", -3, "06:30")
    ], _stored(manager)
    assert settings.plan_day_start == "08:00", settings.plan_day_start


def test_pdm132_a_day_extension_saves_no_settings(screen, manager, settings, monkeypatch):
    """PD-M13.2 — ``save`` is not called at all, on either end of the day.

    Asserted on the call and not only on the values: a version that set the
    attribute, saved, and then set it back would leave the stored values right
    and the user's settings file rewritten under them -- including
    ``plan_day_shape_unconfirmed``, which PD-M5.4 says this gesture must leave
    exactly as it found it.
    """
    saves = []
    monkeypatch.setattr(
        type(settings), "save", lambda self: saves.append(True) or True
    )

    screen.extend_day_for(_item(manager, "Early start"), DAY_EXTEND_EARLIER)
    screen.extend_day_for(_item(manager, "Late finish"), DAY_EXTEND_LATER)

    assert saves == [], f"the extension saved settings {len(saves)} time(s)"
    assert len(_stored(manager)) == 2, f"both ends wrote a block: {_stored(manager)}"


def test_pdm136_an_extension_renumbers_nothing(screen, manager, settings):
    """PD-M13.6 — the 08:00 task keeps box 0 as well as 08:00.

    This asserted ``(1, "08:00")`` until PD-M13, under reason (b): the
    behaviour changed intentionally. A slot index counts boxes from Day Start,
    so while the bound moved every existing block had to be renumbered to keep
    the clock time it was drawn at -- the whole purpose of ``shift_all_slots``.
    With the bound fixed there is nothing to compensate for, and the right
    answer is that the row is not touched: same index, same time.
    """
    _add_block(manager, 30, "Standing meeting", slot_index=0)
    item = _item(manager, "Early start")

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    placed = {row[0]: (row[1], row[3]) for row in _stored(manager)}
    assert placed["Standing meeting"] == (0, "08:00"), (
        f"the meeting was renumbered: {placed['Standing meeting']}"
    )
    assert placed["Early start"] == (-1, "07:30"), placed["Early start"]


def test_pdm136_another_date_is_not_touched_at_all(screen, manager, settings):
    """PD-M13.6 — Friday keeps its index as well as its time.

    This asserted the index had *moved* (the renumber) until PD-M13, under
    reason (b): the behaviour changed intentionally. ``plan_day_start`` is a
    single setting that every date is drawn from, so while a drop moved it
    every other date had to be renumbered to stay where it was -- one drop on
    one date rewriting every day in the file, on screens the user was not even
    on. Nothing changes the bound now, so the correct outcome is that Friday's
    row is byte-for-byte what it was: the index too, which is the assertion
    that would have failed under the old behaviour.
    """
    friday = _add_block(manager, 30, "Friday standup", slot_index=4, block_date=FRIDAY)
    assert friday.start_time == "10:00", (
        f"precondition: the Friday block is stored at 10:00, not {friday.start_time}"
    )
    item = _item(manager, "Early start")

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    later = DayBounds.from_settings(settings)
    assert later.day_start == "08:00", f"the day moved ({later.day_start})"
    grid = build_day_grid(manager.get_time_blocks(FRIDAY), later)
    drawn = {
        entry.starting[0].label: entry.slot.start_time
        for entry in grid.slots
        if entry.starting
    }
    assert drawn == {"Friday standup": "10:00"}, drawn
    stored = {row[0]: (row[1], row[3]) for row in _stored(manager, FRIDAY)}
    assert stored == {"Friday standup": (4, "10:00")}, (
        f"Friday's row was rewritten: {stored}"
    )


def test_pdm131_a_later_drop_leaves_day_end_alone(screen, manager, settings):
    """PD-M13.1 — the item is blocked at 17:00 and Day End is still 17:00.

    The Later half of the test above, retargeted for the same reason (b): the
    box the item lands on is the one after the last drawn box, and the
    configured Day End it is past does not move.
    """
    item = _item(manager, "Late finish")
    assert settings.plan_day_end == "17:00", "precondition: the shipped day end"
    boxes_before = len(day_grid(screen.bounds))

    screen.extend_day_for(item, DAY_EXTEND_LATER)

    assert [(row[0], row[1], row[3]) for row in _stored(manager)] == [
        ("Late finish", boxes_before, "17:00")
    ], _stored(manager)
    assert settings.plan_day_end == "17:00", settings.plan_day_end
    assert AppSettings.load().plan_day_end == "17:00", "the file was written anyway"


def test_pdm53_a_drop_below_does_not_renumber_the_day(screen, manager, settings):
    """Day End moving does not change any slot index: they count from the start."""
    _add_block(manager, 30, "Standing meeting", slot_index=0)
    item = _item(manager, "Late finish")

    screen.extend_day_for(item, DAY_EXTEND_LATER)

    placed = {row[0]: (row[1], row[3]) for row in _stored(manager)}
    assert placed["Standing meeting"] == (0, "08:00"), placed["Standing meeting"]


def test_pdm1311_an_extension_that_would_cross_midnight_writes_nothing(
    screen, manager, settings
):
    """PD-M13.11/P41 — the one refusal this gesture has left, and it is clean.

    This was ``test_pdm56_a_refused_write_leaves_the_day_unchanged``, which
    monkeypatched ``AppSettings.save`` to fail and asserted the rollback put
    the day back. Retargeted under reason (b): the behaviour changed
    intentionally -- there is no settings write here to refuse any more, so
    that path cannot be reached by any input and a test holding it up with a
    monkeypatch would be asserting against code that no longer exists.

    The guarantee that survives is the one worth keeping: the refusal the
    gesture does still have leaves the database exactly as it was. A day
    starting at 00:00 has nothing before box 0 that is still the same date,
    which ``slot_is_on_the_date`` is what refuses -- no patching, a real day a
    user can configure in ⚙ Day Settings.
    """
    settings.plan_day_start = "00:00"
    screen.on_settings_saved(DayBounds(day_start="00:00"))
    _add_block(manager, 30, "Standing meeting", slot_index=0)
    before = _stored(manager)
    item = _item(manager, "Early start")

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert _stored(manager) == before, (
        f"a block was written before the date began: {_stored(manager)}"
    )
    assert settings.plan_day_start == "00:00", settings.plan_day_start
    text = screen.status_label.cget("text")
    assert "a day is one date" in text, text


def test_pdm56_a_failure_with_no_message_still_names_itself(
    screen, manager, settings, monkeypatch
):
    """The status said "The day was not extended — " and then stopped.

    Several built-in exceptions carry no message at all, and ``str`` of one is
    the empty string. The sentence then ended at the dash: the user was told
    the day had not been extended and given nothing about why, on the one path
    that exists to report why. Same hole as the AutoLoad arm, which reports the
    class name for the same reason.
    """
    item = _item(manager, "Early start")

    def boom(*args, **kwargs):
        raise KeyError()

    monkeypatch.setattr(manager, "add_block_at", boom)

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    text = screen.status_label.cget("text")
    assert "KeyError" in text, text
    assert not text.rstrip().endswith("—"), text


def test_pdm56_a_failed_extension_is_not_drawn_as_a_success(
    screen, manager, settings, monkeypatch
):
    """The status must not read like a success. Nothing happened.

    Retargeted with the test above, same reason (b): the refused settings save
    it used to stage is gone, so the failure is staged on the write instead.
    The colour is the assertion -- the sentence is covered by the test above
    this one -- because a success-coloured line is what the user reads before
    they read any of the words.
    """
    item = _item(manager, "Early start")

    def boom(*args, **kwargs):
        raise RuntimeError("the disk went away")

    monkeypatch.setattr(manager, "add_block_at", boom)

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert screen.status_label.cget("text_color") == status_text_color("error")
    assert _stored(manager) == [], f"something was written anyway: {_stored(manager)}"


def test_pdm57_a_block_drag_onto_a_virtual_box_is_refused(
    screen, manager, monkeypatch
):
    """PD-M5.7 — a block already has a half hour; it cannot invent another."""
    item = _item(manager, "Draft the proposal")
    block = _add_block(manager, 30, "Draft the proposal", slot_index=4, item_id=item.id)
    screen.refresh()
    before = _stored(manager)
    _pointer_on(screen, monkeypatch, _virtual(screen, DAY_EXTEND_EARLIER))

    screen.start_block_drag(None, block)
    screen.on_drag_release(None)
    screen.update_idletasks()

    assert _stored(manager) == before, f"the block moved: {_stored(manager)}"
    assert screen.settings.plan_day_start == "08:00", "a block lengthened the day"
    text = screen.status_label.cget("text")
    assert "cannot make a new half hour" in text, text
    # The second clause too. Changed 2026-11-08 under reason (b): the wording
    # was "lengthen the day", which PD-M13 made untrue -- the day is drawn
    # wider and ⚙ Day Settings is untouched.
    assert "drag an item here to add one" in text, text


def test_pdm5_an_item_drag_onto_a_virtual_box_extends_the_day(
    screen, manager, monkeypatch
):
    """The release handler routes a drop that missed every box to the right end.

    Without this the extension is reachable only by calling the method, and the
    gesture the user actually makes -- a drag that lands on the Later box -- is
    untested.
    """
    item = _item(manager, "Late finish")
    screen.refresh()
    asked = []
    monkeypatch.setattr(
        screen, "extend_day_for", lambda i, edge: asked.append((i.title, edge))
    )
    _pointer_on(screen, monkeypatch, _virtual(screen, DAY_EXTEND_LATER))

    screen.start_item_drag(None, item)
    screen.on_drag_release(None)
    # Since PD-M11 the drop is deferred to a zero-delay timer rather than to
    # the idle queue, so draining idle tasks alone no longer runs it.
    _run_due_timers(screen)

    assert asked == [("Late finish", DAY_EXTEND_LATER)], asked


def test_pdm5_a_drop_in_the_day_but_on_no_box_still_does_nothing(
    screen, manager, monkeypatch
):
    """The day pane is more than its boxes, and the gap between them is not an end.

    Found by the mutation gate: ``virtual_under_pointer`` returning an end of
    the day instead of ``None`` for a release that hit neither box passed every
    other test here, because none of them released over the heading, the
    summary or the empty-day note. That release would have lengthened the day.
    """
    item = _item(manager, "Draft the proposal")
    screen.refresh()
    # The day column, but no box in it: day_drop_frame is what
    # pointer_over_day reads, and a pointer really in the column is inside it.
    _pointer_on(screen, monkeypatch, screen.day_drop_frame)

    assert screen.slot_under_pointer() is None
    assert screen.virtual_under_pointer() is None

    screen.start_item_drag(None, item)
    screen.on_drag_release(None)
    screen.update_idletasks()

    assert _stored(manager) == [], f"a block was created: {_stored(manager)}"
    assert screen.settings.plan_day_start == "08:00", "the day was lengthened"
    assert "Drop an item on a half-hour box" in screen.status_label.cget("text")


def test_pdm5_a_real_box_wins_over_a_virtual_one(screen, manager, monkeypatch):
    """A box flush against the Earlier box must still get its own drops.

    The two are read in order -- slots first -- so a pointer that is somehow in
    both lands on the half hour that exists. Asserted because the reverse order
    is a one-line change that no other test would notice.
    """
    item = _item(manager, "Draft the proposal")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    _pointer_on(
        screen, monkeypatch, frames[0], _virtual(screen, DAY_EXTEND_EARLIER)
    )

    assert screen.slot_under_pointer() == 0
    blocked = []
    monkeypatch.setattr(screen, "block_item", lambda i, t: blocked.append((i.title, t)))
    monkeypatch.setattr(
        screen, "extend_day_for", lambda i, edge: blocked.append(("EXTENDED", edge))
    )

    screen.start_item_drag(None, item)
    screen.on_drag_release(None)
    # See the note in the Later-box test: PD-M11 moved the drop off the idle
    # queue and onto a timer.
    _run_due_timers(screen)

    assert blocked == [("Draft the proposal", 0)], blocked


def test_pdm5_the_day_cannot_be_extended_onto_a_non_block_day(
    root, manager, settings
):
    """The Saturday refusal covers this path too, not only the drops onto boxes."""
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "Weekend", start_date=SATURDAY)

    panel.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert settings.plan_day_start == "08:00", "a non-block day lengthened the week"
    assert manager.get_time_blocks(SATURDAY) == []
    assert "not a block day" in panel.status_label.cget("text")


def test_pdm5_an_item_that_would_cross_midnight_is_refused(
    root, manager, settings
):
    """PD-M5.8 on screen: nothing is written and the reason is the date, not room."""
    settings.plan_day_start = "00:00"
    settings.plan_day_end = "17:00"
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    item = _item(manager, "Impossible")

    panel.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert settings.plan_day_start == "00:00", settings.plan_day_start
    assert manager.get_time_blocks(THURSDAY) == []
    text = panel.status_label.cget("text")
    assert "before midnight" in text, text


# ================= PD-M10 — a rebuilt pane is drawn before the next event ===
#
# Reported from the running app as three things: a block dragged to another
# half hour "doesn't seem to work", the dragged item's name stuck beside the
# pointer, and the day pane "seems to wait for a mouse movement of the app
# window". All three are one cause. Tk draws from an idle handler, every
# rebuild on this screen runs inside an event callback or an after_idle of
# one, and nothing here ever flushed.


def _count_flushes(screen, monkeypatch):
    """Count the screen's own ``update_idletasks`` calls, still doing the work.

    monkeypatch rather than a bare setattr: the name is found on the class, so
    an unrestored instance attribute would shadow the bound method for every
    test collected after this one.
    """
    calls = []
    real = screen.update_idletasks

    def counted():
        calls.append(1)
        real()

    monkeypatch.setattr(screen, "update_idletasks", counted)
    return calls


def test_pdm101_rebuilding_the_day_pane_flushes_the_redraw(screen, monkeypatch):
    """PD-M10.1 — ``load_blocks`` leaves the pane drawn, not queued.

    This is the path the report was about: ``move_block_to_slot``,
    ``set_block_minutes`` and ``add_padding_block`` all end in ``load_blocks``
    alone, and all three wrote the day correctly and showed nothing until the
    pointer moved over the window.
    """
    calls = _count_flushes(screen, monkeypatch)

    screen.load_blocks()

    assert len(calls) == 1, f"the day pane flushed {len(calls)} times, not once"


def test_pdm102_rebuilding_the_items_pane_flushes_the_redraw(screen, monkeypatch):
    """PD-M10.2 — the items pane is rebuilt the same way, so it owes the same.

    Only the day pane was reported, but both panes are rebuilt by taking the
    scroll frame out of the grid and putting it back, and a mark that appears
    on an item row only once the pointer moves is the same defect.
    """
    calls = _count_flushes(screen, monkeypatch)

    screen.load_items()

    assert len(calls) == 1, f"the items pane flushed {len(calls)} times, not once"


def test_pdm103_a_press_without_motion_shows_no_drag_label(screen, manager):
    """PD-M10.3 — a click is not a drag, so it puts nothing beside the pointer.

    The reported symptom was an item's title sitting next to the pointer with
    no drag in progress. Every press on a row starts a drag as far as these
    handlers know, so the label was built and placed on the press; the
    release hid it again, but the hiding was not drawn either.
    """
    item = _item(manager, "Fix login bug")
    screen.refresh()

    screen.start_item_drag(None, item)

    assert screen._drag_label is None, "the press alone built the drag label"
    assert screen._drag_label_text == "Fix login bug", screen._drag_label_text


def test_pdm104_the_first_motion_shows_the_label_and_the_second_moves_it(
    screen, manager
):
    """PD-M10.4 — the pointer moving is what turns a press into a drag."""
    item = _item(manager, "Fix login bug")
    screen.refresh()
    screen.start_item_drag(None, item)

    screen.on_drag_motion(None)

    label = screen._drag_label
    assert label is not None, "the first motion did not show the label"
    assert label.cget("text") == "Fix login bug", label.cget("text")
    assert label.winfo_manager() == "place", label.winfo_manager()
    assert screen._drag_label_text is None, "the armed text outlived the label"

    screen.on_drag_motion(None)

    assert screen._drag_label is label, "the second motion built a second label"


def test_pdm105_ending_a_drag_hides_the_label_and_flushes(
    screen, manager, monkeypatch
):
    """PD-M10.5 — a release that lands on nothing redraws nothing by itself.

    A drop onto a box gets its flush from the rebuild that follows it. A
    release over the sidebar writes nothing and rebuilds nothing, so without
    the flush here the label stayed on screen until something else repainted.
    """
    item = _item(manager, "Fix login bug")
    screen.refresh()
    screen.start_item_drag(None, item)
    screen.on_drag_motion(None)
    label = screen._drag_label
    assert label.winfo_manager() == "place", "the label was never placed"
    calls = _count_flushes(screen, monkeypatch)

    screen._end_drag()

    assert label.winfo_manager() == "", "the label is still placed"
    assert len(calls) == 1, f"the hide flushed {len(calls)} times, not once"
    assert screen._drag_label_text is None, screen._drag_label_text


def test_pdm106_a_flush_on_a_screen_that_is_gone_does_not_raise(
    screen, monkeypatch
):
    """PD-M10.6 — the flush is called from a ``finally``, so it must not throw.

    A queued rebuild can outlive the window: a date change or a close whose
    redraw runs after Tk has gone. An exception raised there would replace
    whatever brought the code into the ``finally``, which on the failure paths
    is the error the user needs to be told about.
    """
    calls = []

    def gone():
        calls.append(1)
        raise tk.TclError("application has been destroyed")

    monkeypatch.setattr(screen, "update_idletasks", gone)

    screen._flush_redraw()

    # The verdict is not "nothing was raised" -- pytest gives that for free,
    # and it would still hold if ``_flush_redraw`` stopped drawing entirely.
    # What has to be true is that the raising path was actually entered and
    # swallowed: ``update_idletasks`` was called, and it threw.
    assert calls == [1], f"update_idletasks was called {len(calls)} times, not once"


# ---------------------------------------------------------------------------
# PD-M11 — a dialog that cannot be shown is not an answer
# ---------------------------------------------------------------------------


def test_pdm11_a_dialog_that_raises_writes_nothing_says_so_and_asks_again(
    root, manager, settings, monkeypatch
):
    """PD-M11 — "Schedule anyway on a non-work day does nothing".

    Measured against the running app on 2026-11-07: a Saturday drop raised the
    dialog, and ``askyesno`` raised ``_tkinter.TclError`` with an empty message
    instead of returning the answer. The traceback went to stderr, which the
    user never sees; the drop wrote nothing and said nothing, so the gesture
    read as broken. **That measurement was taken before this fix**, and is
    what settles the half of the report that was open: answered Yes, the day's
    ``time_blocks`` table was still empty, so the fault is that it does not
    schedule rather than that it schedules something which fails to appear.
    The assertions below are on the behaviour *after* the fix, where a Yes that
    the dialog actually returns does schedule.

    Three claims in one test because each kills a different mutation of the
    same two lines. Nothing is written, so the arm is not a silent yes. The
    status says the question could not be completed, so it is not reported as
    the user's refusal -- and it claims no cause, because the raise came out of
    the one Tcl call that both shows the dialog and returns the answer. And the
    failure is not cached either way, so the next drop
    asks again and can still be agreed to -- a transient failure is not a
    permanent negative (P1).
    """
    answers = []

    def raise_then_agree(*args, **kwargs):
        answers.append(1)
        if len(answers) == 1:
            raise tk.TclError("")
        return True

    monkeypatch.setattr("tkinter.messagebox.askyesno", raise_then_agree)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    first = _item(manager, "first", SATURDAY)
    second = _item(manager, "second", SATURDAY)

    panel.block_item(first)

    assert answers == [1], f"the dialog was attempted {len(answers)} times, not once"
    assert manager.get_time_blocks(SATURDAY) == [], (
        "a question that could not be asked scheduled the item anyway"
    )
    status = panel.status_label.cget("text")
    assert "could not be completed" in status, status
    assert "nothing was scheduled" in status, status
    # And it claims no cause: the ``TclError`` came out of the one Tcl call
    # that both shows the dialog and returns the answer, so "never shown" is
    # a guess, and the guess is wrong in the case where the user said yes.
    assert "could not be shown" not in status, status
    assert SATURDAY not in panel._work_anyway, (
        "a question that failed was cached as permission"
    )

    panel.block_item(second)

    assert len(answers) == 2, "the second drop did not ask again after a failure"
    assert SATURDAY in panel._work_anyway, "the Yes was not remembered"
    assert [b.label for b in manager.get_time_blocks(SATURDAY)] == ["second"], (
        manager.get_time_blocks(SATURDAY)
    )


def test_pdm1110_a_clear_day_question_that_raises_removes_nothing(
    root, manager, settings, monkeypatch
):
    """PD-M11 — the arm belongs to the confirmation, not to the one question.

    The measured fault is a modal confirmation on this screen raising instead
    of returning an answer. ``clear_day``'s question is the nearest sibling of
    the one that was measured, in the same file and on the same screen, and it
    gates a transactional delete -- so a raise there removed nothing and said
    nothing, reproducing the reported symptom on the one button that destroys
    work. Both now ask through ``_ask_yes_no`` (P5: hardening the class, not
    the instance).

    Asserted as a delete that did not happen plus a sentence that was said,
    because "nothing was removed" on its own is also what answering No does.
    """
    def raising(*args, **kwargs):
        raise tk.TclError("")

    monkeypatch.setattr("tkinter.messagebox.askyesno", raising)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    _add_block(manager, 30, "Draft the proposal", 0, block_type=BlockType.ITEM)

    panel.clear_day()

    assert len(manager.get_time_blocks(THURSDAY)) == 1, (
        "a question that could not be answered deleted the block anyway"
    )
    said = panel.status_label.cget("text")
    assert "could not be completed" in said, said
    assert "nothing was removed" in said, said


def test_pdm1110_a_truthy_non_answer_is_not_permission(
    root, manager, settings, monkeypatch
):
    """PD-M11 — only the answer yes is a yes.

    ``bool(askyesno(...))`` turns anything unexpectedly truthy into permission
    to write, which is the unsafe direction for a confirmation. Real tkinter
    returns a bool, so this is defence rather than a live bug -- but it is one
    comparison, and the comparison that fails safe.
    """
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: "no")
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()

    assert panel._ask_yes_no("t", "q") is False, (
        "a non-bool truthy answer read as yes"
    )


def test_pdm1111_the_gesture_itself_survives_a_question_that_raises(
    root, manager, settings, monkeypatch
):
    """PD-M11 — the whole drop, not just the method the drop calls.

    Every other test of the failing dialog calls ``block_item`` directly, so
    the gesture the user actually makes -- press, move, release onto a box on a
    non-work day -- was not covered end to end, and the deferral the release
    now goes through was not in the path being asserted. Driven as the real
    handlers here: the release defers to a timer, the timer runs the drop, the
    drop asks, the question raises, and the screen has to come out of that
    saying so with nothing written.
    """
    def raising(*args, **kwargs):
        raise tk.TclError("")

    monkeypatch.setattr("tkinter.messagebox.askyesno", raising)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()
    item = _item(manager, "weekend work", SATURDAY)
    panel.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(panel))
    assert frames, "the day pane built no half-hour boxes on a non-work day"
    _pointer_on(panel, monkeypatch, frames[0])

    panel.start_item_drag(None, item)
    panel.on_drag_release(None)
    _run_due_timers(panel)

    assert manager.get_time_blocks(SATURDAY) == [], (
        "the drop scheduled the item though the question never returned"
    )
    said = panel.status_label.cget("text")
    assert "could not be completed" in said, said
    assert "nothing was scheduled" in said, said
    assert SATURDAY not in panel._work_anyway, (
        "a question that failed was cached as permission"
    )


def test_pdm1112_a_length_dialog_that_raises_says_so(
    root, manager, settings, monkeypatch, caplog
):
    """PD-M11 — the third modal on this screen, found by the re-sweep.

    The measured fault is a modal failing to return an answer, not a
    *confirmation* failing to -- so the class is every modal on the screen,
    and ``ask_custom_minutes`` was the one left out. ``CTkInputDialog.get_input``
    is ``wait_window`` plus a read of the entry, the same machinery
    ``askyesno`` goes through, and the context menu's "Custom..." reaches it.
    Before this it wrote nothing and said nothing, which is the reported
    symptom on a third path.
    """
    def raising(*args, **kwargs):
        raise tk.TclError("")

    monkeypatch.setattr("customtkinter.CTkInputDialog", raising)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    block = _add_block(manager, 30, "Draft the proposal", 0,
                       block_type=BlockType.ITEM)

    with caplog.at_level(logging.ERROR, logger="getmoredone.screens.plan"):
        panel.ask_custom_minutes(block)

    said = panel.status_label.cget("text")
    assert "could not be completed" in said, said
    assert manager.get_time_blocks(THURSDAY)[0].planned_minutes == 30, (
        "the block length changed though the question never returned"
    )
    assert "block length dialog" in caplog.text, caplog.text


def test_pdm1115_the_failed_length_dialog_is_torn_down_before_anything_is_said(
    root, manager, settings, monkeypatch
):
    """PD-M11.15 — the arm that reports the failure must not leave the modal up.

    Found by the fourth pass, in the fix for PD-M11.12 itself. The P5 reasoning
    carried the failure arm across the whole class of modals but not the
    cleanup obligation, which is not the same on both: ``askyesno`` goes
    through ``tkinter.commondialog`` and a native dialog Tk disposes of itself,
    while ``CTkInputDialog`` is a Toplevel that takes ``grab_set`` and
    ``-topmost`` in its own ``__init__`` and is destroyed only by its Ok,
    Cancel and close handlers. So returning from a raise left an
    application-modal, always-on-top window on screen still holding the grab,
    and wrote the error status to a screen the user could no longer click --
    worse than the silent failure the arm was added to cure. Order matters as
    much as the calls: the status line has to be readable when it is written.
    """
    order = []

    class _Stuck:
        def get_input(self):
            raise tk.TclError("")

        def grab_release(self):
            order.append("grab_release")

        def destroy(self):
            order.append("destroy")

    monkeypatch.setattr("customtkinter.CTkInputDialog", lambda **kw: _Stuck())
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    block = _add_block(manager, 30, "Draft the proposal", 0,
                       block_type=BlockType.ITEM)
    monkeypatch.setattr(
        panel, "set_status", lambda *a, **k: order.append("set_status")
    )

    panel.ask_custom_minutes(block)

    assert order == ["grab_release", "destroy", "set_status"], order


def test_pdm1116_a_grab_release_that_raises_does_not_strand_the_window(
    root, manager, settings, monkeypatch
):
    """PD-M11.16 — the teardown's own two steps fail independently.

    ``grab_release`` goes to the same interpreter that just raised, so it is as
    able to raise as the call it is cleaning up after. One ``try`` around both
    steps would mean the first failure skipped the ``destroy``, which is the
    step that actually gets the window off the screen, and the stranded modal
    would be exactly the symptom this teardown exists to prevent.
    """
    order = []

    class _Stuck:
        def get_input(self):
            raise tk.TclError("")

        def grab_release(self):
            order.append("grab_release")
            raise tk.TclError("and again")

        def destroy(self):
            order.append("destroy")

    monkeypatch.setattr("customtkinter.CTkInputDialog", lambda **kw: _Stuck())
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    block = _add_block(manager, 30, "Draft the proposal", 0,
                       block_type=BlockType.ITEM)

    panel.ask_custom_minutes(block)

    assert order == ["grab_release", "destroy"], order
    said = panel.status_label.cget("text")
    assert "could not be completed" in said, said


def test_pdm1113_a_confirmation_that_raises_is_logged_as_well_as_said(
    root, manager, settings, monkeypatch, caplog
):
    """PD-M11 — catching the raise must not cost the evidence of it.

    Before the arm existed, a raising dialog reached stderr, and that traceback
    is the entire reason this fault is understood as far as it is -- the
    mechanism is still unproven. An arm that converted it into a status line
    and nothing else would have traded the symptom for the evidence, and a
    status line is overwritten by the next one. The sibling failure arms on
    this screen (``clear_day``, AutoLoad) log as well as say, for the same
    reason.
    """
    def raising(*args, **kwargs):
        raise tk.TclError("boom")

    monkeypatch.setattr("tkinter.messagebox.askyesno", raising)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()

    with caplog.at_level(logging.ERROR, logger="getmoredone.screens.plan"):
        assert panel._ask_yes_no("Not a work day", "q") is None

    assert "could not be put" in caplog.text, caplog.text
    assert "TclError" in caplog.text, (
        f"the traceback was not logged, only the message: {caplog.text}"
    )


def test_pdm1114_the_non_work_day_sentence_names_no_gesture(
    root, manager, settings, monkeypatch
):
    """PD-M11 — four callers, one sentence, so it cannot name one gesture.

    ``_require_block_day`` is reached from the AutoLoad button, the padding
    button, a drop and a day extension. "Try the drop again" told a user who
    pressed AutoLoad to retry a drop they never made.
    """
    def raising(*args, **kwargs):
        raise tk.TclError("")

    monkeypatch.setattr("tkinter.messagebox.askyesno", raising)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = SATURDAY
    panel.refresh()

    panel.autoload_day()

    said = panel.status_label.cget("text")
    assert "could not be completed" in said, said
    assert "Try again" in said, said
    assert "drop" not in said, (
        f"the sentence names a gesture AutoLoad does not have: {said}"
    )


def test_pdm11_a_drop_is_deferred_to_a_timer_not_the_idle_queue(
    screen, manager, monkeypatch
):
    """PD-M11 — the drop's work runs from the event loop, not from idle.

    The drop is a database write, a full pane rebuild and, outside the working
    week, a modal question. ``after_idle`` means "before the next redraw",
    which is the wrong queue for work that causes a redraw and can block on the
    user answering -- and it is the context the raising ``askyesno`` was
    measured in. A zero-delay timer meets the only requirement the idle call
    was there for: let the ButtonRelease handler return before anything
    destroys the row it is dispatching to.

    **The queue is provisional, and the first two assertions with it.** The
    move off idle is the candidate cure for the raising dialog, not a proven
    one -- the cause of the ``TclError`` was never established. If it turns
    out to lie elsewhere, the queue is free to change and these two
    assertions should change with it rather than being defended. What is not
    provisional is the rest: the work does not run inside the ButtonRelease
    handler, and it does run once that handler has returned.
    """
    item = _item(manager, "weekend work")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    _pointer_on(screen, monkeypatch, frames[0])

    idle, timers = [], []
    monkeypatch.setattr(screen, "after_idle", lambda fn, *a: idle.append(fn))
    monkeypatch.setattr(
        screen, "after", lambda ms, fn=None, *a: timers.append((ms, fn))
    )
    blocked = []
    monkeypatch.setattr(
        screen, "block_item", lambda i, t: blocked.append((i.title, t))
    )

    screen.start_item_drag(None, item)
    screen.on_drag_release(None)

    assert idle == [], "the drop was queued as an idle task"
    assert [ms for ms, _ in timers] == [0], timers
    assert blocked == [], "the drop ran inside the release handler"

    timers[0][1]()

    assert blocked == [("weekend work", 0)], blocked


# ---------------------------------------------------------------------------
# PD-M12 — the day scrolls while a drag sits at its edge
# ---------------------------------------------------------------------------


def _fake_day_viewport(
    screen, monkeypatch, *, top=100, height=300, left=400, width=200,
    yview=(0.3, 0.6), region=(0, 0, 200, 1000),
):
    """Give the day pane a viewport, without needing a mapped window.

    ``winfo_*`` on a withdrawn window answers 1, so the real numbers are only
    available to the 22 tests that take ``mapped_windows`` -- and those are the
    ones skipped in the local workflow CLAUDE.md documents. The geometry is
    faked instead, the same way ``_pointer_on`` fakes the pointer, so the
    margin arithmetic is asserted against numbers the test chose.
    """
    canvas = screen.blocks_scroll._parent_canvas
    monkeypatch.setattr(canvas, "winfo_ismapped", lambda: 1)
    monkeypatch.setattr(canvas, "winfo_rootx", lambda: left)
    monkeypatch.setattr(canvas, "winfo_rooty", lambda: top)
    monkeypatch.setattr(canvas, "winfo_width", lambda: width)
    monkeypatch.setattr(canvas, "winfo_height", lambda: height)
    monkeypatch.setattr(canvas, "yview", lambda *a: yview)
    monkeypatch.setattr(canvas, "bbox", lambda *a: region)
    return canvas


def _fake_pointer(screen, monkeypatch, x, y):
    monkeypatch.setattr(screen, "winfo_pointerx", lambda: x)
    monkeypatch.setattr(screen, "winfo_pointery", lambda: y)


def test_pdm121_a_drag_at_an_edge_asks_to_scroll_that_way(screen, monkeypatch):
    """PD-M12.1 — within the margin of the top or bottom edge, the day moves.

    The reported fault: "the Day Plan does not scroll while an item is dragged
    past its edge", so a day taller than its pane could only be dropped into
    the part of it that happened to be showing.
    """
    _fake_day_viewport(screen, monkeypatch)

    _fake_pointer(screen, monkeypatch, 500, 100 + PD_AUTOSCROLL_MARGIN_PX - 1)
    assert screen.day_autoscroll_direction() == -1

    _fake_pointer(screen, monkeypatch, 500, 400 - PD_AUTOSCROLL_MARGIN_PX)
    assert screen.day_autoscroll_direction() == 1


def test_pdm121_a_drag_past_the_edge_still_asks_to_scroll(screen, monkeypatch):
    """PD-M12.1 — past the edge counts as at it, which is the reported gesture.

    A band that stopped at the border would ask the user to hold the pointer
    inside a 24px strip, and the thing they actually do is drag beyond the
    pane.
    """
    _fake_day_viewport(screen, monkeypatch)

    _fake_pointer(screen, monkeypatch, 500, 100 - 200)
    assert screen.day_autoscroll_direction() == -1

    _fake_pointer(screen, monkeypatch, 500, 400 + 200)
    assert screen.day_autoscroll_direction() == 1


def test_pdm122_a_drag_clear_of_the_edges_asks_for_no_scroll(screen, monkeypatch):
    """PD-M12.2 — the middle of the pane is where a drop is aimed, not a scroll.

    Both boundaries, because the off-by-one that makes the band one pixel too
    wide is the one that steals the last visible box's drop.
    """
    _fake_day_viewport(screen, monkeypatch)

    _fake_pointer(screen, monkeypatch, 500, 250)
    assert screen.day_autoscroll_direction() == 0

    _fake_pointer(screen, monkeypatch, 500, 100 + PD_AUTOSCROLL_MARGIN_PX)
    assert screen.day_autoscroll_direction() == 0

    _fake_pointer(screen, monkeypatch, 500, 400 - PD_AUTOSCROLL_MARGIN_PX - 1)
    assert screen.day_autoscroll_direction() == 0


def test_pdm122_a_drag_beside_the_day_pane_asks_for_no_scroll(screen, monkeypatch):
    """PD-M12.2 — the unscheduled list is at the same heights as the day pane.

    Without the x range, dragging an item up its own list would scroll the day
    under it.
    """
    _fake_day_viewport(screen, monkeypatch)

    _fake_pointer(screen, monkeypatch, 399, 399)
    assert screen.day_autoscroll_direction() == 0

    _fake_pointer(screen, monkeypatch, 600, 399)
    assert screen.day_autoscroll_direction() == 0


def test_pdm123_an_end_already_reached_asks_for_no_scroll(screen, monkeypatch):
    """PD-M12.3 — holding at the bottom of a fully scrolled day asks for nothing.

    Otherwise the pane is re-scrolled and the hover re-read sixteen times a
    second for no movement, for as long as the button is held.
    """
    canvas = _fake_day_viewport(screen, monkeypatch, yview=(0.0, 0.4))
    _fake_pointer(screen, monkeypatch, 500, 100)
    assert screen.day_autoscroll_direction() == 0

    monkeypatch.setattr(canvas, "yview", lambda *a: (0.6, 1.0))
    _fake_pointer(screen, monkeypatch, 500, 399)
    assert screen.day_autoscroll_direction() == 0


def test_pdm124_scrolling_the_day_moves_the_canvas_and_rereads_the_hover(
    screen, monkeypatch
):
    """PD-M12.4 — one step of the canvas, and the hover follows the boxes.

    The boxes move under a pointer that has not, so whichever box was lit is
    no longer the one being dropped on.
    """
    canvas = _fake_day_viewport(screen, monkeypatch)
    scrolled, hovered = [], []
    monkeypatch.setattr(canvas, "yview_moveto", lambda f: scrolled.append(f))
    monkeypatch.setattr(screen, "update_hover_target", lambda: hovered.append(1))
    _fake_pointer(screen, monkeypatch, 500, 399)

    assert screen.autoscroll_day() is True

    # 0.3 of a 1000px day, plus 16px of it. Asserted as a fraction and not as
    # an argument to ``yview_scroll``: see the PD-M12.9 tests below for why a
    # "unit" was not a distance.
    assert scrolled == [0.3 + 16 / 1000], scrolled
    assert hovered == [1], hovered


def test_pdm124_a_drag_clear_of_the_edges_scrolls_nothing(screen, monkeypatch):
    """PD-M12.4 — and the middle of the pane touches neither the canvas nor the hover."""
    canvas = _fake_day_viewport(screen, monkeypatch)
    scrolled, hovered = [], []
    monkeypatch.setattr(canvas, "yview_moveto", lambda f: scrolled.append(f))
    monkeypatch.setattr(screen, "update_hover_target", lambda: hovered.append(1))
    _fake_pointer(screen, monkeypatch, 500, 250)

    assert screen.autoscroll_day() is False

    assert scrolled == [], scrolled
    assert hovered == [], hovered


def test_pdm129_a_tick_moves_the_day_by_the_step_in_pixels(screen, monkeypatch):
    """PD-M12.9 — one tick is a distance, and the distance is 16px.

    The first version of this scrolled ``yview_scroll(1, "units")``, which is
    not a distance at all: ``CTkScrollableFrame.__init__`` configures the
    canvas's ``yscrollincrement`` itself, and differently per platform -- 8 on
    macOS, 1 on Windows, and unset on Linux, where Tk falls back to a tenth of
    the pane. The same line therefore scrolled at three speeds an order of
    magnitude apart, and no test noticed because every test asserted the
    *arguments* to ``yview_scroll`` rather than any movement.

    Asserted as a fraction of the scrollregion, which is the one quantity that
    means the same thing on all three, with the numbers written out: a 1000px
    day scrolled 16px is 0.016 of itself.
    """
    _fake_day_viewport(screen, monkeypatch, yview=(0.3, 0.6),
                       region=(0, 0, 200, 1000))

    assert screen.day_autoscroll_fraction(1) == 0.3 + 0.016, (
        screen.day_autoscroll_fraction(1)
    )
    assert screen.day_autoscroll_fraction(-1) == 0.3 - 0.016, (
        screen.day_autoscroll_fraction(-1)
    )
    assert PD_AUTOSCROLL_STEP_PX == 16, (
        f"the step is {PD_AUTOSCROLL_STEP_PX}px, so the fractions above are "
        "no longer the arithmetic being asserted"
    )


def test_pdm129_a_step_cannot_scroll_past_the_end(screen, monkeypatch):
    """PD-M12.9 — the last step stops at the end rather than overshooting it.

    ``yview_moveto`` is a destination, not an increment, so unlike the units
    version an arithmetic overshoot is not clamped for us by the scroll
    command. A day showing its last 30% cannot start later than 0.70.
    """
    _fake_day_viewport(screen, monkeypatch, yview=(0.69, 0.99),
                       region=(0, 0, 200, 1000))

    assert screen.day_autoscroll_fraction(1) == 0.70, (
        screen.day_autoscroll_fraction(1)
    )

    _fake_day_viewport(screen, monkeypatch, yview=(0.0, 0.3),
                       region=(0, 0, 200, 1000))

    assert screen.day_autoscroll_fraction(-1) == 0.0, (
        screen.day_autoscroll_fraction(-1)
    )


def test_pdm129_a_day_with_no_scrollregion_asks_for_nothing(screen, monkeypatch):
    """PD-M12.9 — no scrollregion is "do not call it", not "scroll to zero".

    A pane rebuilt and not yet configured has no ``bbox("all")``. Zero is a
    real destination and would jump a part-scrolled day to its top, so the
    answer has to be ``None`` and the canvas has to be left alone.
    """
    canvas = _fake_day_viewport(screen, monkeypatch)
    monkeypatch.setattr(canvas, "bbox", lambda *a: None)
    moved = []
    monkeypatch.setattr(canvas, "yview_moveto", lambda f: moved.append(f))
    _fake_pointer(screen, monkeypatch, 500, 399)

    assert screen.day_autoscroll_fraction(1) is None
    assert screen.autoscroll_day() is False
    assert moved == [], moved


def test_pdm129_scrolling_rereads_the_hover_onto_the_box_now_under_the_pointer(
    screen, manager, monkeypatch
):
    """PD-M12.9 — the outline follows the boxes, asserted as an outline.

    The two PD-M12.4 tests stub ``update_hover_target`` and assert that it was
    *called*, which is the same shape as asserting the arguments to
    ``yview_scroll`` rather than any movement -- the thing this batch already
    had to fix once. The hover outline is the only feedback telling the user
    which half hour a drop will land in, and the autoscroll makes a 60ms timer
    responsible for keeping it right, so one test runs the real thing: scroll,
    then assert which box is outlined.
    """
    _item(manager, "Draft the proposal")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    assert len(frames) >= 2, "the day pane built too few boxes to move between"
    screen._drag_kind = "item"

    _fake_day_viewport(screen, monkeypatch)
    _fake_pointer(screen, monkeypatch, 500, 399)
    # The pointer does not move; which box is under it does, because the day
    # scrolls beneath it. Faked as the box the second read lands on.
    under = [frames[0], frames[1]]
    plain = frames[0].cget("border_color")
    monkeypatch.setattr(screen, "slot_under_pointer", lambda: 0)
    screen.update_hover_target()

    assert screen._drag_hover_frame is under[0], "the first box was not outlined"
    assert under[0].cget("border_width") == 2, under[0].cget("border_width")

    monkeypatch.setattr(screen, "slot_under_pointer", lambda: 1)
    assert screen.autoscroll_day() is True

    assert screen._drag_hover_frame is under[1], (
        "the outline stayed on the box the pointer is no longer over"
    )
    assert under[1].cget("border_width") == 2, under[1].cget("border_width")
    assert under[0].cget("border_width") == 1, (
        "the box the day scrolled past kept its outline"
    )
    # Width *and* colour, on this path above all others: PD-M12.10's trail is
    # the whole day precisely because a 60ms timer walks the hover down every
    # box the day scrolls past, so a colour restore asserted only by a direct
    # unit call is asserted nowhere near where it matters.
    assert under[0].cget("border_color") == plain, (
        f"the scrolled-past box kept the accent: {under[0].cget('border_color')}"
    )


def test_pdm1213_a_drag_across_the_middle_of_the_pane_moves_the_outline(
    screen, manager, monkeypatch
):
    """PD-M12.13 — the caller that compensates for the autoscroll's own skip.

    ``on_drag_motion`` ends ``if not self.autoscroll_day(): update_hover_target()``.
    ``autoscroll_day`` deliberately leaves the hover alone when it did not move
    the day -- PD-M12.4 asserts exactly that -- so for every drag clear of the
    two edge bands, which is most of the pane, the outline is moved by that one
    line in the caller and by nothing else. **Measured: deleting it leaves the
    whole suite green** (201 passed) while the drop-target outline stops
    following the pointer across the middle of the pane, which is the only
    feedback telling the user which half hour they are about to get.

    The two tests on this path both stub ``update_hover_target`` and assert a
    call count, so the real outline is what this one asserts -- the same
    correction PD-M12.9 made for the scrolling path.
    """
    _item(manager, "Draft the proposal")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    assert len(frames) >= 2, "the day pane built too few boxes to move between"
    screen._drag_kind = "item"
    screen._drag_label_text = None
    monkeypatch.setattr(screen, "_position_drag_label", lambda: None)

    _fake_day_viewport(screen, monkeypatch)
    # Mid-pane: the viewport is 100..400, so this is clear of both bands and
    # ``autoscroll_day`` must answer False.
    _fake_pointer(screen, monkeypatch, 500, 250)
    monkeypatch.setattr(screen, "slot_under_pointer", lambda: 1)

    screen.on_drag_motion(None)

    try:
        assert screen.autoscroll_day() is False, (
            "the pointer was meant to be clear of both bands"
        )
        assert screen._drag_hover_frame is frames[1], (
            "the box under the pointer was not outlined by the motion"
        )
        assert frames[1].cget("border_width") == 2, frames[1].cget("border_width")
    finally:
        screen._stop_autoscroll()


def test_pdm1214_an_abandoned_drag_leaves_no_outline_behind(
    screen, manager, monkeypatch
):
    """PD-M12.14 — the release clears the hover, asserted through the release.

    PD-M12.10 calls ``clear_hover_target`` directly, but the fault its
    docstring describes -- "a drag abandoned away from the boxes gets no
    rebuild to hide it" -- runs through ``on_drag_release``, which is the only
    production caller for that case. **Measured: deleting that call leaves the
    whole suite green** (202 passed) while the accent trail PD-M12.10 exists to
    remove is back for exactly the gesture it was reported on.

    Released off the boxes on purpose: a release *on* a box ends in a
    ``refresh()`` that rebuilds every box, which would hide the fault rather
    than test it.
    """
    _item(manager, "Draft the proposal")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    box = frames[0]
    plain_colour = box.cget("border_color")
    plain_width = box.cget("border_width")
    screen._drag_kind = "item"
    monkeypatch.setattr(screen, "slot_under_pointer", lambda: 0)

    screen.update_hover_target()
    assert box.cget("border_width") == 2, "the hover never went on"

    # Nothing under the pointer, so nothing is scheduled and nothing rebuilds.
    monkeypatch.setattr(screen, "slot_under_pointer", lambda: None)
    monkeypatch.setattr(screen, "virtual_under_pointer", lambda: None)
    screen.on_drag_release(None)

    assert box.cget("border_width") == plain_width, box.cget("border_width")
    assert box.cget("border_color") == plain_colour, (
        f"the abandoned drag left its accent behind: {box.cget('border_color')}"
    )
    assert screen._drag_hover_frame is None, (
        "the cleared hover is still being tracked"
    )


def test_pdm1212_a_pointer_held_at_the_end_of_the_day_stops_scrolling(
    screen, monkeypatch
):
    """PD-M12.12 — the clamp and the end-stop, against each other.

    PD-M12.3 proves ``day_autoscroll_direction`` answers 0 once ``yview``
    reports ``last >= 1.0``, and PD-M12.9 proves ``day_autoscroll_fraction``
    clamps the destination to ``1.0 - visible``. Nothing joined them, and
    ``_fake_day_viewport`` patches ``yview`` to a constant, so no test ran two
    consecutive ticks against a viewport that moves. The guarantee the two
    together are supposed to give is that a pointer held in the bottom band
    comes to a stop: if the clamped destination made ``yview`` report
    ``0.9999...`` instead of ``1.0``, the direction would stay 1, every tick
    would return True, and the hover would be re-read 16 times a second for no
    movement for as long as the button was held -- which is what PD-M12.3's
    docstring claims is prevented, on the path that actually does the
    scrolling.

    So the fake writes ``yview_moveto`` back into what ``yview`` returns, and
    the assertion is termination: a bounded number of ticks, then False.
    """
    canvas = _fake_day_viewport(screen, monkeypatch)
    # 0.25, not 0.3, and the first version of this test had 0.3 and was
    # vacuous because of it. The step is 16/1000 = 0.016 of the region, and
    # from 0.3 the distance to a 0.7 end-stop is exactly 25 steps -- so the
    # *unclamped* walk landed on the same 0.7 the clamp produces, and the test
    # passed with the clamp deleted. With 0.25 the end-stop is 0.75, which is
    # 28.125 steps away: the clamp stops exactly on it, and without the clamp
    # the walk overshoots to ~0.764 before ``yview`` reports the end.
    visible = 0.25
    state = {"first": 0.3}
    monkeypatch.setattr(canvas, "yview", lambda *a: (state["first"],
                                                     state["first"] + visible))
    monkeypatch.setattr(
        canvas, "yview_moveto", lambda f: state.__setitem__("first", f)
    )
    _fake_pointer(screen, monkeypatch, 500, 400 - 1)

    ticks = 0
    while screen.autoscroll_day():
        ticks += 1
        assert ticks < 200, (
            f"held at the end of the day and still scrolling after {ticks} "
            f"ticks, at first={state['first']}"
        )

    assert ticks > 0, "the pointer was in the band and nothing scrolled at all"
    assert state["first"] == pytest.approx(1.0 - visible), state["first"]
    assert screen.day_autoscroll_direction() == 0, (
        "the day is at its end but the direction still asks to scroll on"
    )


def test_pdm1210_clearing_the_hover_puts_the_colour_back(
    screen, manager, monkeypatch
):
    """PD-M12.10 — width and colour, not width alone.

    ``clear_hover_target`` put back only the border width, so the accent
    stayed on at 1px. A drag abandoned away from the boxes gets no rebuild to
    hide it, and since the autoscroll re-reads the hover every 60ms a pointer
    held at an edge walks it down every box the day scrolls past — the trail
    is the whole day rather than one box. A persistent primary accent on boxes
    with no action pending is also what the theme rules call a misuse of the
    one emphasis colour.
    """
    _item(manager, "Draft the proposal")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    box = frames[0]
    before = box.cget("border_color")
    screen._drag_kind = "item"
    monkeypatch.setattr(screen, "slot_under_pointer", lambda: 0)

    screen.update_hover_target()

    assert box.cget("border_color") != before, (
        "the hover did not change the colour, so this test asserts nothing"
    )

    screen.clear_hover_target()

    assert box.cget("border_color") == before, (
        f"the box kept the hover colour: {box.cget('border_color')} != {before}"
    )
    assert box.cget("border_width") == 1, box.cget("border_width")


def test_pdm1211_the_width_goes_back_even_with_no_colour_to_restore(
    screen, manager
):
    """PD-M12.11 — the colour restore must not be able to cost the width one.

    Found by the fourth pass, in the PD-M12.10 fix. ``CTkFrame.configure``
    pops ``border_color`` and runs it through ``_check_color_type``, which
    raises ``ValueError`` -- not ``TclError``, so the existing guard did not
    cover it -- when the colour is None, and it pops it *before* applying
    ``border_width``. So adding the colour to the restore put the width
    restore, which was already working, behind a call that could raise.

    **The None is not reachable in production today, and this test does not
    claim it is.** ``_drag_hover_color`` is assigned in one place only, in the
    same block that sets ``_drag_hover_frame``, so a frame to restore always
    implies a colour to restore; before the first hover the frame is None too
    and ``clear_hover_target`` returns at its first ``if``. Nor can the cached
    value be None at source: ``build_slot_row`` passes an explicit
    ``border_color``. The state is set by hand here because the guard is a
    code-shape one -- it exists so that no future way of reaching
    ``clear_hover_target`` with an unset colour can cost the width restore --
    and a guard with no test is a guard the next reader deletes or, worse,
    trusts for more than it does.
    """
    _item(manager, "Draft the proposal")
    screen.refresh()
    frames = dict((index, frame) for frame, index in _slot_frames(screen))
    box = frames[0]
    box.configure(border_width=2)
    screen._drag_hover_frame = box
    screen._drag_hover_border = 1
    screen._drag_hover_color = None

    screen.clear_hover_target()

    assert box.cget("border_width") == 1, box.cget("border_width")


def test_pdm125_a_held_drag_keeps_scrolling(screen, monkeypatch):
    """PD-M12.5 — each tick re-arms the next, so holding still keeps scrolling.

    Scrolling only on motion would stop the moment the user held the pointer
    at the border, which is exactly where a drag that wants more of the day to
    appear comes to rest.
    """
    screen._drag_kind = "item"
    moves = []
    monkeypatch.setattr(screen, "autoscroll_day", lambda: moves.append(1))

    screen._autoscroll_tick()

    try:
        assert moves == [1], moves
        assert screen._autoscroll_after is not None, "the tick did not re-arm"
    finally:
        # In a ``finally`` because the timer is real. A failing assertion here
        # would otherwise leave a 60ms callback queued against a screen about
        # to be destroyed, and ``_run_due_timers`` in a later test dispatches
        # timer events indiscriminately -- so one failure in this test would
        # surface as a second, unrelated one somewhere else.
        screen._stop_autoscroll()


def test_pdm126_motion_does_not_stack_autoscroll_timers(screen, monkeypatch):
    """PD-M12.6 — one timer, however many motion events arrive.

    ``_start_autoscroll`` is called on every ``<B1-Motion>``, and a drag across
    the pane produces dozens; a timer per event would scroll the day at the
    speed of the mouse.
    """
    armed = []
    monkeypatch.setattr(
        screen,
        "after",
        lambda ms, fn=None, *a: armed.append(ms) or f"timer-{len(armed)}",
    )

    screen._start_autoscroll()
    screen._start_autoscroll()
    screen._start_autoscroll()

    assert armed == [PD_AUTOSCROLL_INTERVAL_MS], armed


def test_pdm127_a_tick_after_the_drag_ended_does_nothing(screen, monkeypatch):
    """PD-M12.7 — a tick already in flight when the button came up is harmless.

    ``_drag_kind`` is read now rather than trusted from when the timer was
    armed, so the release does not have to win a race with it.
    """
    screen._drag_kind = None
    screen._autoscroll_after = "a-pending-tick"
    moves = []
    monkeypatch.setattr(screen, "autoscroll_day", lambda: moves.append(1))

    screen._autoscroll_tick()

    assert moves == [], "a tick scrolled the day after the drag ended"
    assert screen._autoscroll_after is None, "the dead tick armed another"


def test_pdm128_motion_arms_the_autoscroll_and_the_release_cancels_it(
    screen, manager, monkeypatch
):
    """PD-M12.8 — the day stops scrolling when the button comes up.

    Both halves in one test because neither is worth much alone: an arm with
    no cancel scrolls forever, and a cancel with no arm never scrolls.
    """
    item = _item(manager, "Fix login bug")
    screen.refresh()
    screen.start_item_drag(None, item)

    screen.on_drag_motion(None)

    armed = screen._autoscroll_after
    assert armed is not None, "the first motion armed no autoscroll"

    cancelled = []
    real_cancel = screen.after_cancel
    monkeypatch.setattr(
        screen,
        "after_cancel",
        lambda which: cancelled.append(which) or real_cancel(which),
    )

    screen._end_drag()

    assert cancelled == [armed], cancelled
    assert screen._autoscroll_after is None, screen._autoscroll_after


def test_pdm13_autoload_does_not_spill_into_the_drawn_extension(
    root, manager, settings
):
    """PD-M13.18 — a span that starts inside the configured day ends inside it.

    Purpose: ``can_place``'s limit is the day as *drawn*, which is wider than
             the configured day wherever a block already sits outside it. Both
             free-box scans walk the configured range, so the *start* of a span
             is bounded -- but its length is checked by ``can_place``, so a
             block could start on the last configured box and run past Day End
             into the extension.
    Spec:    docs/implementation_plan_2026-11-07_plan_day_range.md#pd-m13
    Tests:   this test

    Found by a cold pass. AutoLoad fills the day the user configured; only a
    deliberate drag on Earlier or Later may put work outside it.
    """
    panel = _short_day(root, manager, settings, end="16:30")  # boxes 0-16
    # A Later drop has already put a block at 17:00, so the day is *drawn* out
    # to box 18 while the user's configured day still ends at 16:30.
    _add_block(manager, 30, "Later", slot_index=18, outside_range=True)
    # Everything taken but the last configured box, 16:00-16:30. Boxes 8 and 9
    # are lunch and hold nothing.
    for index in list(range(8)) + list(range(10, 16)):
        _add_block(manager, 30, f"Taken {index}", slot_index=index)
    _priced_item(manager, "Long", 20, 20, 16, 8)
    long_item = manager.get_items_for_start_date(THURSDAY)[0]
    long_item.work_block = 60
    manager.update_action_item(long_item)
    panel.refresh()
    existing = {block.id for block in manager.get_time_blocks(THURSDAY)}
    before = len(existing)

    panel.autoload_day()

    # The whole span, not just where it starts: a 60m block written at 16:00
    # starts on the last configured box and ends on one past it. Only the
    # blocks AutoLoad wrote are in scope -- the Later block at box 18 is
    # outside the configured day because the user put it there.
    spilled = [
        (block.label, block.slot_index, slots_for_minutes(block.planned_minutes))
        for block in manager.get_time_blocks(THURSDAY)
        if block.id not in existing
        and block.slot_index is not None
        and block.slot_index + slots_for_minutes(block.planned_minutes) - 1 > 16
    ]
    assert spilled == [], (
        f"AutoLoad wrote these past the configured Day End of 16:30: {spilled}"
    )
    assert len(manager.get_time_blocks(THURSDAY)) == before, (
        "a 60m task needs two boxes and only the last configured box is free"
    )
    assert "1 did not fit" in panel.status_label.cget("text")


def test_pdm13_the_free_box_scan_bounds_the_span_too(root, manager, settings):
    """PD-M13.19 — the same bound on the other scan, for the add paths.

    Purpose: ``first_clear_slot`` serves AutoLoad and ``first_free_slot``
             serves "block this item" and "add a break" when there is no
             pointer to read. Both walk the configured day, so both need the
             span bounded by it; a bound on only one leaves the other able to
             finish a block inside the drawn extension.
    Spec:    docs/implementation_plan_2026-11-07_plan_day_range.md#pd-m13
    Tests:   this test

    ``first_free_slot`` offers the earliest box that is not *full*, so the
    boxes before the last one are filled to ``MAX_BLOCKS_PER_SLOT`` to get the
    scan as far as the end of the configured day.
    """
    panel = _short_day(root, manager, settings, end="09:00")  # boxes 0 and 1
    # A Later drop has drawn the day out to box 2 (09:00-09:30). ``bounds`` is
    # the short day the screen is on, so the write is checked against the same
    # day -- without it the helper checks against its own 08:00-17:00 default,
    # where box 2 is well inside the day and the flag does nothing.
    short_day = DayBounds(day_start="08:00", day_end="09:00")
    _add_block(
        manager, 30, "Later", slot_index=2, bounds=short_day, outside_range=True
    )
    for seat in range(MAX_BLOCKS_PER_SLOT):
        _add_block(manager, 30, f"Full {seat}", slot_index=0)
    panel.refresh()

    assert panel.first_free_slot(30) == 1, (
        "precondition: box 0 is full and box 1 is the last configured box"
    )
    assert panel.first_free_slot(60) is None, (
        "a 60m block offered box 1 would finish in box 2, which is past the "
        "configured Day End and only drawn because the user put work there"
    )


def test_pdm13_a_failed_extension_redraws_before_it_reports(
    screen, manager, settings, monkeypatch
):
    """PD-M13.20 — the broad failure arm redraws the day before reporting.

    Purpose: the arm used to call ``refresh`` as part of putting a settings
             file back. PD-M13 deleted the rollback and the redraw went with
             it. Every refusal this path can currently reach is checked before
             the write, so the screen is already right -- but a failure landing
             *after* the commit would leave the drawn day disagreeing with the
             database, with the error sentence as the only sign of it.
    Spec:    docs/implementation_plan_2026-11-07_plan_day_range.md#pd-m13
    Tests:   this test

    Found by two cold passes independently. Asserted on the call rather than
    on the pixels: what the redraw puts on screen is covered by the grid tests,
    and a failure that is *not* pre-checked cannot be staged from outside.
    """
    item = _item(manager, "Early start")
    # One list for both calls, so the *order* is asserted and not just that
    # each happened -- the name of this test is a claim about the order.
    calls = []
    real_refresh = screen.refresh
    real_set_status = screen.set_status

    def traced_refresh(*args, **kwargs):
        calls.append("refresh")
        return real_refresh(*args, **kwargs)

    def traced_set_status(*args, **kwargs):
        calls.append("set_status")
        return real_set_status(*args, **kwargs)

    def boom(*args, **kwargs):
        raise RuntimeError("the disk went away")

    monkeypatch.setattr(screen, "refresh", traced_refresh)
    monkeypatch.setattr(screen, "set_status", traced_set_status)
    monkeypatch.setattr(manager, "add_block_at", boom)

    screen.extend_day_for(item, DAY_EXTEND_EARLIER)

    assert "refresh" in calls, (
        "the day was not redrawn after the extension failed, so a failure "
        "after the write would leave the screen showing a day that is gone"
    )
    assert calls.index("refresh") < calls.index("set_status"), (
        "the day was redrawn after the error was reported; if the redraw "
        f"itself throws, the user loses the sentence. Order was {calls}"
    )
    assert "the disk went away" in screen.status_label.cget("text")
