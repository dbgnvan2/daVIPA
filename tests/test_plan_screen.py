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
so the two tests that read real geometry ask for the ``mapped_windows``
fixture.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.screens.plan import RIGHT_CLICK_SEQUENCES, PlanScreen
from src.getmoredone.screens.plan_blocks import (
    DepthBarStack,
    accent_for_block,
    accent_for_item,
    build_block_row,
)
from src.getmoredone.screens.plan_settings_dialog import PlanSettingsDialog
from src.getmoredone.theme import block_type_colors, priority_band_colors
from src.getmoredone.time_block_layout import DayBounds, block_height

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


def _add_block(manager, minutes, label, block_date=THURSDAY, **kwargs):
    block = TimeBlock(
        block_date=block_date,
        start_time="",
        end_time="",
        planned_minutes=minutes,
        label=label,
        **kwargs,
    )
    manager.create_time_block(block)
    return block


def _stored(manager, block_date=THURSDAY):
    return [
        (b.label, b.position, b.start_time, b.end_time, b.planned_minutes)
        for b in manager.get_time_blocks(block_date)
    ]


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


def test_saving_settings_repacks_the_day(root, manager, settings):
    """A new day start makes every stored time on the day stale."""
    _add_block(manager, 60, "a")
    _add_block(manager, 60, "b")
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.refresh()
    manager.repack_day(THURSDAY, panel.bounds)
    assert _stored(manager)[0][2] == "08:00"

    dialog = PlanSettingsDialog(panel, settings, on_saved=panel.on_settings_saved)
    try:
        dialog.day_start_entry.delete(0, tk.END)
        dialog.day_start_entry.insert(0, "10:00")
        dialog.save()
    finally:
        if dialog.winfo_exists():
            dialog.destroy()

    assert [row[2] for row in _stored(manager)] == ["10:00", "11:00"]


# --- TB-M6 : the date picker -------------------------------------------------

def test_tbm61_date_change_reloads_both_panes(screen, manager):
    """TB-M6.1 — the picker drives the item list and the block list together."""
    _item(manager, "thursday item", THURSDAY)
    _item(manager, "friday item", FRIDAY)
    _add_block(manager, 30, "thursday block", block_date=THURSDAY)
    _add_block(manager, 30, "friday block", block_date=FRIDAY)

    screen.on_date_changed(FRIDAY)

    assert screen.selected_date == FRIDAY
    assert [i.title for i in screen._items] == ["friday item"]
    assert [entry.block.label for entry in screen._packed] == ["friday block"]


def test_the_date_is_a_picker_not_a_free_text_entry(screen):
    """The free-text entry accepted a typo and wrote blocks under a non-date.

    Asserted on the widget's own contract: a DatePickerButton validates and
    normalises, which is the behaviour being bought here.
    """
    from src.getmoredone.widgets.date_picker import DatePickerButton

    assert isinstance(screen.date_picker, DatePickerButton)
    assert screen.date_picker.get_date() == screen.selected_date


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
    _add_block(manager, 30, "a")
    screen.load_blocks()

    frame, _block_id = screen._block_frames[0]
    bound = _bound_sequences(frame)
    for sequence in RIGHT_CLICK_SEQUENCES:
        assert sequence in bound, f"no {sequence} binding on a block"
    assert RIGHT_CLICK_SEQUENCES == ("<Button-3>", "<Button-2>")


def test_the_block_menu_offers_the_documented_durations(screen, manager, monkeypatch):
    """The menu's contents, as an exact list, with 30 marked as the default.

    tk_popup is stubbed out: posting a real menu grabs the pointer and the test
    run would stop on it.
    """
    _add_block(manager, 30, "a")
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
    _add_block(manager, 30, "a")
    _add_block(manager, 30, "b")
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

    assert [row[4] for row in _stored(manager)] == [30, 90]


def test_tbm92_duration_change_repacks_the_day(screen, manager):
    """TB-M9.2 — resizing a block re-times every block after it."""
    _add_block(manager, 30, "a")
    _add_block(manager, 30, "b")
    _add_block(manager, 30, "c")
    screen.load_blocks()
    manager.repack_day(THURSDAY, screen.bounds)

    first = manager.get_time_blocks(THURSDAY)[0]
    screen.set_block_minutes(first, 60)

    assert _stored(manager) == [
        ("a", 1, "08:00", "09:00", 60),
        ("b", 2, "09:00", "09:30", 30),
        ("c", 3, "09:30", "10:00", 30),
    ]


def test_deleting_a_block_closes_the_gap_it_leaves(screen, manager):
    _add_block(manager, 30, "a")
    _add_block(manager, 30, "b")
    _add_block(manager, 30, "c")
    screen.load_blocks()
    middle = manager.get_time_blocks(THURSDAY)[1]

    screen.delete_block(middle.id)

    assert _stored(manager) == [
        ("a", 1, "08:00", "08:30", 30),
        ("c", 2, "08:30", "09:00", 30),
    ]


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
    block = _add_block(manager, 30, "Buffer", block_type=BlockType.BUFFER)

    assert accent_for_block(block, None) == block_type_colors()[BlockType.BUFFER]
    assert accent_for_block(block, None) not in priority_band_colors().values()


# --- TB-M11 : drag blocks to rearrange --------------------------------------

def test_tbm111_reorder_persists_new_order(screen, manager):
    """TB-M11.1 — by position *and* by time, because the two must agree."""
    _add_block(manager, 30, "a")
    _add_block(manager, 30, "b")
    _add_block(manager, 30, "c")
    screen.load_blocks()
    third = screen._block_frames[2][1]

    screen.reorder_to(third, 0)

    assert _stored(manager) == [
        ("c", 1, "08:00", "08:30", 30),
        ("a", 2, "08:30", "09:00", 30),
        ("b", 3, "09:00", "09:30", 30),
    ]


def test_a_reorder_that_changes_nothing_writes_nothing(screen, manager):
    """Dropping a block back where it was must not bump every updated_at."""
    _add_block(manager, 30, "a")
    _add_block(manager, 30, "b")
    screen.load_blocks()
    manager.repack_day(THURSDAY, screen.bounds)
    before = [(b.id, b.updated_at) for b in manager.get_time_blocks(THURSDAY)]

    screen.reorder_to(before[0][0], 0)

    assert [(b.id, b.updated_at) for b in manager.get_time_blocks(THURSDAY)] == before


def test_a_block_dropped_outside_the_day_column_is_not_reordered(screen, manager, monkeypatch):
    """A release over the sidebar is a cancelled drag, not a move to the end."""
    _add_block(manager, 30, "a")
    _add_block(manager, 30, "b")
    screen.load_blocks()
    manager.repack_day(THURSDAY, screen.bounds)
    before = _stored(manager)

    monkeypatch.setattr(
        "src.getmoredone.screens.plan.widget_contains_pointer",
        lambda *args, **kwargs: False,
    )
    assert screen.drop_index_for_pointer() is None

    screen._drag_kind = "block"
    screen._drag_block = manager.get_time_blocks(THURSDAY)[1]
    screen.on_drag_release(None)

    assert _stored(manager) == before


# --- TB-M12 : appearance ----------------------------------------------------

def test_tbm121_block_height_tracks_minutes(root, manager, mapped_windows):
    """TB-M12.1 — a 90 is three times the height of a 30, in real geometry.

    ``mapped_windows`` because winfo_height() on a withdrawn window returns 1,
    so this is one of the few tests that needs a window actually on screen.
    """
    frame = ctk.CTkFrame(root)
    frame.pack(fill="both", expand=True)

    short = build_block_row(
        frame,
        TimeBlock(block_date=THURSDAY, start_time="08:00", end_time="08:30", planned_minutes=30),
        None, 0, overflows_day_end=False,
    )
    tall = build_block_row(
        frame,
        TimeBlock(block_date=THURSDAY, start_time="08:30", end_time="10:00", planned_minutes=90),
        None, 1, overflows_day_end=False,
    )
    root.update_idletasks()

    assert tall.winfo_height() == 3 * short.winfo_height()
    assert short.winfo_height() == block_height(30)


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

def test_the_lunch_band_is_drawn_where_the_day_skips_it(screen, manager):
    """The hour the day skips is shown, not left as an unexplained jump in times."""
    for label in ("a", "b", "c", "d", "e"):
        _add_block(manager, 60, label)

    screen.load_blocks()

    labels = [
        child.cget("text")
        for frame in screen.blocks_scroll.winfo_children()
        for child in frame.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
    assert "Lunch" in labels
    assert "12:00–13:00" in labels


def test_no_lunch_band_when_lunch_is_zero_minutes(screen, manager, settings):
    settings.plan_lunch_minutes = 0
    screen.bounds = DayBounds.from_settings(settings)
    for label in ("a", "b", "c", "d", "e"):
        _add_block(manager, 60, label)

    screen.load_blocks()

    labels = [
        child.cget("text")
        for frame in screen.blocks_scroll.winfo_children()
        for child in frame.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
    assert "Lunch" not in labels


# --- a block whose item is gone ---------------------------------------------

def test_a_block_keeps_its_item_title_when_the_item_starts_on_another_day(screen, manager):
    """The item behind a block may start elsewhere; the block still knows it.

    Reusing the date-filtered item list to resolve block titles is the obvious
    shortcut and the wrong one: every block for an item that started earlier
    would read "(item no longer exists)".
    """
    item = _item(manager, "started on Monday", "2026-11-02")
    _add_block(manager, 30, item.title, item_id=item.id)

    screen.load_blocks()

    titles = [
        child.cget("text")
        for frame in screen.blocks_scroll.winfo_children()
        for child in frame.winfo_children()
        if isinstance(child, ctk.CTkLabel)
    ]
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

    _aim_pointer_at(panel, monkeypatch, panel.day_drop_frame, offset_y=40)
    assert panel.pointer_over_day(), (
        "the test aimed outside the day column, so it would prove nothing: "
        f"pointer={panel.winfo_pointerx()},{panel.winfo_pointery()} "
        f"day={panel.day_drop_frame.winfo_rootx()},{panel.day_drop_frame.winfo_rooty()} "
        f"{panel.day_drop_frame.winfo_width()}x{panel.day_drop_frame.winfo_height()} "
        f"mapped={panel.day_drop_frame.winfo_ismapped()}"
    )
    target = _press_target(rows[0])
    target.event_generate("<ButtonPress-1>", x=5, y=5)
    target.event_generate("<B1-Motion>", x=7, y=7)
    target.event_generate("<ButtonRelease-1>", x=7, y=7)
    root.update()

    blocks = manager.get_time_blocks(THURSDAY)
    assert len(blocks) == 1, f"the real drag created {len(blocks)} blocks"
    assert blocks[0].planned_minutes == 45
    assert blocks[0].start_time == "08:00"


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


def test_real_press_and_release_on_a_block_reorders_the_day(
    root, manager, settings, monkeypatch, mapped_windows
):
    """Requirement 6, driven through Tk.

    The second block is picked up and released on the top half of the first,
    which is the gesture a user makes to move it up one place. The assertion is
    on the stored order and the stored times together: a reorder that moved the
    rows and left the clock behind would be the bug worth catching.
    """
    _add_block(manager, 30, "First", block_type=BlockType.ITEM)
    _add_block(manager, 30, "Second", block_type=BlockType.ITEM)
    panel = _live_screen(root, manager, settings)

    assert [label for label, *_ in _stored(manager)] == ["First", "Second"]
    first_frame, _first_id = panel._block_frames[0]
    second_frame, _second_id = panel._block_frames[1]

    _aim_pointer_at(panel, monkeypatch, first_frame, offset_y=2)
    target = _press_target(second_frame)
    target.event_generate("<ButtonPress-1>", x=5, y=5)
    target.event_generate("<B1-Motion>", x=5, y=2)
    target.event_generate("<ButtonRelease-1>", x=5, y=2)
    root.update()

    assert _stored(manager) == [
        ("Second", 1, "08:00", "08:30", 30),
        ("First", 2, "08:30", "09:00", 30),
    ]


def test_a_real_right_click_on_a_block_opens_the_menu(
    root, manager, settings, monkeypatch, mapped_windows
):
    """The context menu is reachable by the gesture, not just by the method.

    ``tk_popup`` is replaced because a real popup grabs the pointer and would
    hang the run; what is being proved is that the binding fires and builds a
    menu for the right block.
    """
    _add_block(manager, 30, "First", block_type=BlockType.ITEM)
    panel = _live_screen(root, manager, settings)

    opened = []
    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, *a, **k: opened.append(self))
    monkeypatch.setattr(tk.Menu, "grab_release", lambda self: None)

    frame, _block_id = panel._block_frames[0]
    _press_target(frame).event_generate(RIGHT_CLICK_SEQUENCES[0], x=5, y=5)
    root.update()

    assert len(opened) == 1, "the right-click binding did not open a menu"
    assert opened[0].index("end") is not None


# --- found by the pre-push sweep --------------------------------------------


def test_dragging_a_block_down_lands_it_where_it_was_dropped(screen, manager):
    """The sweep's high-severity finding, at the screen level.

    `reorder_to` is given the gap index the pointer was released in, counted
    against the rendered rows with the dragged block still among them. It used
    to pass that straight to `move_block`, which removes the block first, so
    every downward drag overshot by one: dropping the first block between the
    second and third put it last instead.
    """
    _add_block(manager, 30, "First")
    _add_block(manager, 30, "Second")
    _add_block(manager, 30, "Third")
    screen.load_blocks()
    first_id = screen._block_frames[0][1]

    # The gap before "Third" — released on the bottom half of "Second".
    screen.reorder_to(first_id, 2)

    assert _stored(manager) == [
        ("Second", 1, "08:00", "08:30", 30),
        ("First", 2, "08:30", "09:00", 30),
        ("Third", 3, "09:00", "09:30", 30),
    ]


def test_releasing_a_block_in_its_own_gap_writes_nothing(screen, manager):
    """A mis-click inside a block's own row is not an instruction to move it.

    Both gaps bounding a block are its own. The old arithmetic turned the
    lower one into a move past the next block, so a two-pixel drag reordered
    the day.
    """
    _add_block(manager, 30, "First")
    _add_block(manager, 30, "Second")
    screen.load_blocks()
    first_id = screen._block_frames[0][1]
    before = _stored(manager)

    screen.reorder_to(first_id, 0)
    screen.reorder_to(first_id, 1)

    assert _stored(manager) == before


def test_a_custom_block_length_longer_than_a_day_is_refused(screen, manager, monkeypatch):
    """A length that format_hhmm would clamp must not reach the database.

    Stored, it would give the row an end_time that is not its start plus its
    duration — a row that lies about itself to every later reader — and draw a
    block tall enough to put the rest of the day out of reach.
    """
    _add_block(manager, 30, "First")
    screen.load_blocks()
    block = manager.get_time_blocks(THURSDAY)[0]
    before = _stored(manager)

    monkeypatch.setattr(
        ctk.CTkInputDialog, "get_input", lambda self: str(24 * 60 + 1)
    )
    screen.ask_custom_minutes(block)

    assert _stored(manager) == before
    assert "1440 minutes or less" in screen.status_label.cget("text")


def test_a_custom_block_length_of_exactly_a_day_is_accepted(screen, manager, monkeypatch):
    """The boundary the refusal is written against, so it cannot creep inward."""
    _add_block(manager, 30, "First")
    screen.load_blocks()
    block = manager.get_time_blocks(THURSDAY)[0]

    monkeypatch.setattr(ctk.CTkInputDialog, "get_input", lambda self: str(24 * 60))
    screen.ask_custom_minutes(block)

    assert manager.get_time_blocks(THURSDAY)[0].planned_minutes == 24 * 60


def test_finishing_a_drag_does_not_drop_the_posted_menu(screen, manager, monkeypatch):
    """`clear_hover_target` must not reset the reference that keeps a menu alive.

    An annotated assignment belonging in `__init__` had been left at the end of
    that method, so ending any drag discarded the reference held to stop a
    posted menu being collected — which takes its commands with it.
    """
    _add_block(manager, 30, "First")
    screen.load_blocks()
    monkeypatch.setattr(tk.Menu, "tk_popup", lambda self, *a, **k: None)
    monkeypatch.setattr(tk.Menu, "grab_release", lambda self: None)

    screen.open_block_menu(_FakeEvent(10, 10), manager.get_time_blocks(THURSDAY)[0])
    assert screen._block_menu is not None

    screen.clear_hover_target()

    assert screen._block_menu is not None, "the menu reference was discarded"


class _FakeEvent:
    """The two attributes open_block_menu reads off a Tk event."""

    def __init__(self, x_root, y_root):
        self.x_root = x_root
        self.y_root = y_root


def test_a_day_settings_change_retimes_the_days_that_are_not_on_screen(
    screen, manager
):
    """The sweep's P6 finding at the screen level.

    `on_settings_saved` used to repack `self.selected_date` alone, so Friday
    kept the clock times Thursday's old Day Start had given it.
    """
    _add_block(manager, 30, "thursday")
    _add_block(manager, 30, "friday", block_date=FRIDAY)
    manager.repack_day(THURSDAY, screen.bounds)
    manager.repack_day(FRIDAY, screen.bounds)

    screen.on_settings_saved(DayBounds(day_start="10:00"))

    assert _stored(manager, THURSDAY)[0][2] == "10:00"
    assert _stored(manager, FRIDAY)[0][2] == "10:00"


def test_a_failed_repack_does_not_leave_a_block_with_no_times(screen, manager):
    """Each screen write and its repack are one commit.

    In between them the new row holds no times at all, and `set_block_minutes`
    is worse: the row would read as a 30-minute block claiming 90 minutes while
    the next block still owned the minutes it had taken.
    """
    _add_block(manager, 30, "first")
    screen.load_blocks()
    before = _stored(manager)
    screen.bounds = _ExplodingBounds()

    with pytest.raises(RuntimeError):
        screen.block_item(_item(manager, "dropped", THURSDAY))

    assert _stored(manager) == before


def test_a_failed_repack_does_not_leave_a_resized_block_claiming_two_lengths(
    screen, manager
):
    """The resize half of the same finding."""
    _add_block(manager, 30, "first")
    _add_block(manager, 30, "second")
    manager.repack_day(THURSDAY, screen.bounds)
    screen.load_blocks()
    before = _stored(manager)
    block = manager.get_time_blocks(THURSDAY)[0]
    screen.bounds = _ExplodingBounds()

    with pytest.raises(RuntimeError):
        screen.set_block_minutes(block, 90)

    assert _stored(manager) == before


class _ExplodingBounds:
    """Bounds that raise the moment packing reads them.

    The same shape as the fixture in test_time_block_crud, pointed at the
    screen's methods rather than the manager's: pack_day asks for
    day_start_minutes first, which puts the failure after the screen's own
    write and before anything is committed.
    """

    default_block_minutes = 30
    block_weekdays = (True,) * 7

    @property
    def day_start_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def day_end_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def lunch_start_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def lunch_end_minutes(self):
        raise RuntimeError("bounds unreadable")

    @property
    def lunch_length(self):
        raise RuntimeError("bounds unreadable")
