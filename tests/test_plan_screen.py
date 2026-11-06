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

import tkinter as tk

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.color_contrast import contrast_ratio, pick_text_color
from src.getmoredone.screens.plan import (
    NOTE_MIN_WRAP_PX,
    OUTSIDE_GROUP_HEIGHT_PX,
    PLAN_ITEMS_COL_WIDTH_PX,
    REFUSAL_TEXT,
    RIGHT_CLICK_SEQUENCES,
    PlanScreen,
    refusal_text,
)
from src.getmoredone.screens.plan_blocks import (
    ITEM_ROW_MIN_HEIGHT_PX,
    SLOT_CHIP_HEIGHT_PX,
    SLOT_MIN_HEIGHT_PX,
    SLOT_ROW_GAP_PX,
    SLOT_TITLE_WIDTH_PX,
    DepthBarStack,
    accent_for_block,
    accent_for_item,
    build_item_row,
    build_outside_group,
    build_slot_row,
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
)
from src.getmoredone.time_block_layout import (
    MAX_BLOCKS_PER_SLOT,
    MAX_DEPTH_BARS,
    SLOT_MINUTES,
    DayBounds,
    SlotRefusal,
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
        "medium": dict(importance=5, urgency=5, size=4, value=2),        # 200
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


def _add_block(manager, minutes, label, slot_index, block_date=THURSDAY, **kwargs):
    """Put a block on a box, the way every screen path now does.

    ``slot_index`` is required rather than defaulted: a day's shape is the
    thing under test in most of this file, and a test that did not say where
    its blocks were would be asserting against whatever box the helper chose.
    """
    block = TimeBlock(
        block_date=block_date,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        **kwargs,
    )
    return manager.add_block_at(block, slot_index, DayBounds())


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

    Day End moving earlier is the ordinary way this happens. The block still
    exists and is still the user's planned work; the day it stops being drawn
    is the day that work is lost with nothing on screen to say so.
    """
    _add_block(manager, 30, "late afternoon", 16)
    screen.load_blocks()
    assert screen._grid.outside == []

    screen.on_settings_saved(DayBounds(day_end="12:00"))

    assert [b.label for b in screen._grid.outside] == ["late afternoon"]
    drawn = _label_texts(screen.outside_frame)
    assert "late afternoon" in drawn
    assert any("Outside the day (1)" in text for text in drawn)
    assert "no longer fit the day" in screen.status_label.cget("text")
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
    _add_block(manager, 30, "late afternoon", 16)
    screen.load_blocks()
    screen.on_settings_saved(DayBounds(day_end="12:00"))

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
    settings.plan_items_col_width = 180
    panel = PlanScreen(root, manager, _App(settings))

    assert panel.grid_columnconfigure(0)["minsize"] == 180
    assert panel.grid_columnconfigure(0)["weight"] == 0, (
        "with a weight the column grows with the window and the setting is "
        "only a floor"
    )
    assert panel.grid_columnconfigure(1)["weight"] == 1, (
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
    assert panel.grid_columnconfigure(0)["minsize"] == PLAN_ITEMS_COL_WIDTH_PX

    settings.plan_items_col_width = "two hundred"
    other = PlanScreen(root, manager, _App(settings))
    assert other.grid_columnconfigure(0)["minsize"] == PLAN_ITEMS_COL_WIDTH_PX


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
    _add_block(manager, 30, "late afternoon", 16)
    screen.load_blocks()
    screen.on_settings_saved(DayBounds(day_end="12:00"))
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
    """
    item = _item(manager, "Draft the proposal", depth="Deep")
    block = _item_block()
    block.item_id = item.id
    _pane, row = _one_slot_pane(root, block, width=600)
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
    """
    item = _item(manager, "Draft the proposal", priority_score=51200)
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
    """
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
    assert note.winfo_reqwidth() <= 240, (
        f"the note asks for {note.winfo_reqwidth()}px inside a 240px column"
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
    _add_block(manager, 30, "late afternoon", 16)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    panel.on_settings_saved(DayBounds(day_end="12:00"))

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
    for slot in range(10, 18):
        _add_block(manager, 30, f"late {slot}", slot)
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    panel.on_settings_saved(DayBounds(day_end="10:00"))

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

    _add_block(manager, 30, "late afternoon", 16)
    panel.load_blocks()
    panel.on_settings_saved(DayBounds(day_end="12:00"))

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
    """
    settings.plan_items_col_width = 50
    panel = PlanScreen(root, manager, _App(settings))
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


def test_pbm61_a_row_too_short_for_its_text_keeps_its_text(root, manager):
    """PB-M6.1 — the floor, and why the match with the day stops at it.

    A box height of 30 -- the floor, and what the demo's settings file holds --
    gives a half hour 34px in the day. A row matching that showed its title and
    clipped the depth / ``already blocked`` line and the work-block length: the
    two facts the colour cannot carry, gone with nothing to say they were there.

    Asserted as the real relationship rather than against the constant alone:
    below the floor the row is the taller of the two, at and above it the row is
    exactly what the day gives.
    """
    assert item_row_height(1, 30) == ITEM_ROW_MIN_HEIGHT_PX, (
        "a one-box row at the box-height floor is not held at the row floor"
    )
    assert item_row_height(1, 30) > slot_row_height(1, 30), (
        "the row is no taller than a 34px box, so its second line is still cut"
    )

    tall_enough = 86
    assert item_row_height(1, tall_enough) == slot_row_height(1, tall_enough), (
        "at a usable box height the row is no longer the day's own height"
    )
    assert item_row_height(3, tall_enough) > ITEM_ROW_MIN_HEIGHT_PX, (
        "the floor is swallowing a multi-box row"
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

    The height assertions above are all ``cget``, and a frame can ask for 66px
    while Tk lays its children out somewhere else entirely. This is the same
    measurement PB-M2.1 makes on a task chip, applied to the row: every child's
    bottom edge inside the frame's own height.

    It is the test that fails on the defect the first version shipped with.
    ``grid_rowconfigure(0, weight=1)`` put all the slack -- including a negative
    shortfall -- on the title's row, so at a 30px box height Tk collapsed the
    title to a single pixel and the row showed its depth and its length and not
    which item it was. The weight is on an empty row 2 now, so a row short of
    space loses from the bottom.
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
    """
    item = _scored_item(manager, "Draft the proposal", depth="Medium")
    row = build_item_row(
        root, item, 0, already_blocked=False,
        work_block_minutes=90, box_height=86,
    )
    root.geometry("700x700")
    root.deiconify()
    root.update_idletasks()
    root.update()

    title = _find_label(row, "Draft the proposal")
    detail = _find_label(row, "Medium")
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


def test_pbm63_the_work_block_length_is_under_the_depth_bars(root, manager):
    """PB-M6.3 — "30m" sits below the stacked lines, not in the detail line.

    Position asserted, not just presence: the fact is in the same place on an
    item row as on a task in a box, which is the point of moving it. Measured
    off the grid rather than off pixels so it holds on a withdrawn window.
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
    assert duration_at["column"] == bars_at["column"], (
        f"the length is in column {duration_at['column']}, the bars in "
        f"{bars_at['column']} -- it is not under them"
    )
    assert int(duration_at["row"]) > int(bars_at["row"]), (
        f"the length is on row {duration_at['row']}, the bars on "
        f"{bars_at['row']} -- it is not under them"
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
