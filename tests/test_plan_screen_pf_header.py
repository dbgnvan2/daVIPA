"""PF-M4 and PF-M5 — the Plan screen's header, in two rows that resize.

Purpose: the walk asked for the four buttons that add things to the day on
         their own line, and for every button to take an equal share of the
         width as the window changes.
Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md
Tests:   this file

A layout test reads grid options rather than realised geometry, so it needs no
mapped window. The two that measure real widths take ``mapped_windows``, and
say so.
"""

from __future__ import annotations

import customtkinter as ctk
import pytest

from src.getmoredone.app import DEFAULT_WINDOW_WIDTH_PX
from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.screens.plan import PlanScreen
from src.getmoredone.widgets.date_picker import DatePickerButton


class _App:
    """The slice of the app object PlanScreen actually reads."""

    def __init__(self, settings):
        self.settings = settings


@pytest.fixture
def manager(tmp_path):
    db = DatabaseManager(str(tmp_path / "pf_header.db"))
    yield db
    db.close()


@pytest.fixture
def settings(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        AppSettings, "get_settings_path", classmethod(lambda cls: path)
    )
    return AppSettings()


@pytest.fixture
def root():
    window = ctk.CTk()
    yield window
    window.destroy()


@pytest.fixture
def screen(root, manager, settings):
    panel = PlanScreen(root, manager, _App(settings))
    panel.refresh()
    root.update_idletasks()
    return panel


def _row(button):
    """The row a header button sits in."""
    return button.master


def test_pfm41_the_header_is_two_rows(screen):
    """PF-M4.1 — the four named buttons are on the second line.

    Asked for by name: "put the Buffer, Break, Calendar and Day Settings
    buttons on the line below the Date, Clear Day and AutoLoad buttons."
    """
    day_row = _row(screen.btn_clear_day)
    tools_row = _row(screen.btn_settings)

    assert day_row is _row(screen.btn_autoload), (
        "Clear Day and AutoLoad are not on the same row"
    )
    assert tools_row is _row(screen.btn_add_buffer) is _row(screen.btn_add_break)
    assert tools_row is _row(screen.btn_export_calendar), (
        "Google Calendar left the row the other tools are on"
    )
    assert day_row is not tools_row, "the header is still one row"

    assert day_row.master is screen.header
    assert tools_row.master is screen.header
    assert int(day_row.grid_info()["row"]) == 0, day_row.grid_info()
    assert int(tools_row.grid_info()["row"]) == 1, tools_row.grid_info()

    # The date picker belongs with the date it changes, not with the tools.
    assert _row(screen.date_picker) is day_row


def test_pfm42_every_control_survives_the_move(screen):
    """PF-M4.2 — seven controls went in and seven are still there.

    UI regression policy rule 2: relocation was asked for; removal was not.
    """
    assert isinstance(screen.date_picker, DatePickerButton)
    assert screen.btn_clear_day.cget("text") == "Clear Day"
    assert screen.btn_autoload.cget("text") == "AutoLoad"
    assert screen.btn_add_buffer.cget("text") == "+ Buffer"
    assert screen.btn_add_break.cget("text") == "+ Break"
    assert screen.btn_export_calendar.cget("text") == "⤴ Google Calendar"
    assert screen.btn_settings.cget("text") == "⚙ Day Settings"

    assert screen.btn_autoload.cget("command") == screen.autoload_day
    assert screen.btn_clear_day.cget("command") == screen.clear_day

    # The colours the two day-wide buttons carry are a decision, not a layout.
    assert screen.btn_autoload.cget("fg_color") != screen.btn_clear_day.cget(
        "fg_color"
    ), "Clear Day lost its danger colour"


def test_pfm43_the_status_line_stays_out_of_the_header(screen):
    """PF-M4.3 — the one channel this screen reports through keeps its own row.

    ``test_cem441b`` asserts the same thing from the other direction; this one
    is here because a second row is exactly the change that would tempt a
    caller to put a label back in the header.
    """
    assert screen.status_label.master is screen, (
        "the status line moved into the header, where a button can squeeze it"
    )
    assert int(screen.status_label.grid_info()["row"]) == 2


def test_pfm51_the_buttons_share_one_column_group(screen):
    """PF-M5.1 — equal widths by construction, not by chosen numbers.

    Every button sits in its row's uniform column group with weight, so what
    the window gives one it gives the rest.
    """
    day_row = _row(screen.btn_clear_day)
    tools_row = _row(screen.btn_settings)

    for column in (3, 4):
        options = day_row.grid_columnconfigure(column)
        assert options["weight"] == 1, (column, options)
        assert options["uniform"] == "day_row", (column, options)

    for column in range(4):
        options = tools_row.grid_columnconfigure(column)
        assert options["weight"] == 1, (column, options)
        assert options["uniform"] == "tools_row", (column, options)

    for button in (
        screen.btn_clear_day,
        screen.btn_autoload,
        screen.btn_add_buffer,
        screen.btn_add_break,
        screen.btn_export_calendar,
        screen.btn_settings,
    ):
        assert button.grid_info()["sticky"] in ("ew", "nsew"), (
            f"{button.cget('text')} will not stretch with its column"
        )


def test_pfm52_widening_the_window_keeps_them_equal(screen, root, mapped_windows):
    """PF-M5.2 — the four tools grow together, by the same amount each.

    The complaint was 90px buttons beside panes that moved. Measured rather
    than read, because ``uniform`` is the mechanism and this is its effect.
    """
    tools = [
        screen.btn_add_buffer,
        screen.btn_add_break,
        screen.btn_export_calendar,
        screen.btn_settings,
    ]
    screen.pack(fill="both", expand=True)

    root.geometry(f"{DEFAULT_WINDOW_WIDTH_PX}x700")
    root.update_idletasks()
    narrow = [button.winfo_width() for button in tools]

    root.geometry(f"{DEFAULT_WINDOW_WIDTH_PX + 400}x700")
    root.update_idletasks()
    wide = [button.winfo_width() for button in tools]

    assert max(wide) - min(wide) <= 2, f"the four are not equal once wide: {wide}"
    assert min(wide) > min(narrow), (
        f"the buttons did not grow with the window: {narrow} then {wide}"
    )


def test_pfm53_the_buttons_fit_the_narrowest_window(screen):
    """PF-M5.3 — the row's own request still fits the window it opens in.

    Requested widths, not realised ones: a withdrawn window reports 1, and the
    question here is whether the row asks for more than it is given.
    """
    tools_row = _row(screen.btn_settings)
    wanted = sum(
        button.winfo_reqwidth()
        for button in (
            screen.btn_add_buffer,
            screen.btn_add_break,
            screen.btn_export_calendar,
            screen.btn_settings,
        )
    )
    wanted += 8 * 3  # the three gaps between them
    wanted += 20  # the row's own padx

    assert wanted <= DEFAULT_WINDOW_WIDTH_PX, (
        f"the tools row asks for {wanted}px inside {DEFAULT_WINDOW_WIDTH_PX}px"
    )
