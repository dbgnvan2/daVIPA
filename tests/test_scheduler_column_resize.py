"""SCR — the Scheduler's item columns fill the list and follow its width.

Plan: docs/unused-docs/implementation_plan_2026-11-14_scheduler_columns_resize.md
"""

from types import SimpleNamespace

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem
from src.getmoredone.screens.drag_schedule import DragScheduleScreen
from src.getmoredone.vps_manager import VPSManager

KEYS = ("title", "segment", "subsegment", "category", "start_date")
# Checkbox cell 30 + padx 12, title padx 12, four cells at padx 8, the row's
# own padx 2+2, and a 6px margin so the last cell is never clipped.
RESERVED = 42 + 12 + 4 * 8 + 4 + 6
FLOOR = 6 * 8   # 6 characters at 8px, the Scheduler's font size 14


@pytest.fixture
def scr(tmp_path):
    db_path = str(tmp_path / "sched.db")
    db = DatabaseManager(db_path)
    for n in range(3):
        db.create_action_item(ActionItem(who="Self", title=f"Task {n}"))
    vps = VPSManager(db_path)
    root = ctk.CTk()
    root.withdraw()
    screen = DragScheduleScreen(root, db, SimpleNamespace(vps_manager=vps))
    screen.update_idletasks()
    assert screen.resizer._rows, "the Scheduler rendered no rows"
    yield screen
    root.destroy()
    vps.close()
    db.close()


def _widths(screen):
    return {k: screen.resizer.width(k) for k in KEYS}


def test_scrm1_columns_fill_the_list(scr):
    """SCR-M1 — the five columns and the reserved cells add up to the list."""
    assert scr._items_reserved_px() == RESERVED
    scr._fit_items(1000)
    assert sum(_widths(scr).values()) + RESERVED == 1000
    for frame, _cells in scr.resizer._rows:
        assert frame.grid_columnconfigure(6)["weight"] == 0, "a slack column remains"
    assert scr.items_header.grid_columnconfigure(6)["weight"] == 0


def test_scrm2_columns_follow_the_width(scr):
    """SCR-M2 — a wider list widens every column, in the default proportions."""
    scr._fit_items(900)
    narrow = _widths(scr)
    scr._fit_items(1500)
    wide = _widths(scr)
    for key in KEYS:
        assert wide[key] > narrow[key], key
    assert abs(wide["title"] / wide["segment"] - 220 / 170) < 0.05
    assert abs(wide["segment"] / wide["start_date"] - 170 / 120) < 0.05
    for _frame, cells in scr.resizer._rows:
        for key, label, *_ in cells:
            assert int(label.cget("width")) == wide[key]


def test_scrm3_floor_is_six_characters(scr):
    """SCR-M3 — no column goes below 6 characters."""
    for width in (1200, 600, 300, 1):
        scr._fit_items(width)
        assert min(_widths(scr).values()) >= FLOOR, width
    assert set(_widths(scr).values()) == {FLOOR}


def test_scrm4_configure_refits(scr, monkeypatch):
    """SCR-M4 — a <Configure> on the list refits it to the list's width."""
    pending = []
    monkeypatch.setattr(scr, "after", lambda ms, fn: pending.append(fn) or "id")
    monkeypatch.setattr(scr, "after_cancel", lambda _id: None)
    monkeypatch.setattr(scr.items_frame, "winfo_width", lambda: 1300)
    monkeypatch.setattr(scr, "_get_widget_scaling", lambda: 1.0)
    scr.items_frame.event_generate("<Configure>")
    assert len(pending) == 1, "the list's <Configure> scheduled no fit"
    pending[0]()
    assert sum(_widths(scr).values()) + RESERVED == 1300


def test_scrm5_both_panes_stretch(scr):
    """SCR-M5 — a window change widens the list's pane too, not only the last."""
    panes = scr.splitter.panes()
    assert len(panes) == 2
    for pane in panes:
        assert str(scr.splitter.panecget(pane, "stretch")) == "always"


def test_scrm6_drag_sets_one_share(scr, monkeypatch):
    """SCR-M6 — a drag changes that column's share only, is saved, and refits."""
    pending = []
    monkeypatch.setattr(scr, "after", lambda ms, fn: pending.append(fn) or "id")
    monkeypatch.setattr(scr, "after_cancel", lambda _id: None)
    monkeypatch.setattr(scr.items_frame, "winfo_width", lambda: 1200)
    monkeypatch.setattr(scr, "_get_widget_scaling", lambda: 1.0)
    resizer = scr.resizer
    scr._fit_items(1200)
    weights = dict(resizer._weights)
    before_drag = resizer.width("segment")
    resizer._on_start(SimpleNamespace(x_root=500), "segment")
    resizer._on_drag(SimpleNamespace(x_root=560), "segment")
    resizer._on_stop(SimpleNamespace(x_root=560), "segment")
    assert resizer._weights["segment"] > weights["segment"]
    saved = AppSettings.load().drag_schedule_col_widths
    assert saved["segment"] == round(resizer._weights["segment"])
    # Found by the csdp sweep: nothing refitted after a drag, so the
    # columns overran the list until the window next changed size.
    assert len(pending) == 1, "the drag's end scheduled no refit"
    pending[0]()
    assert sum(_widths(scr).values()) + RESERVED == 1200
    # The column stays where it was dropped; the others made room for it.
    assert abs(resizer.width("segment") - (before_drag + 60)) <= 1


def test_scr_overflow_is_logged_once(scr, caplog):
    """A list narrower than the floors is logged once per crossing (P2)."""
    caplog.set_level("INFO", logger="src.getmoredone.screens.drag_schedule")
    for width in (300, 290, 280):
        assert scr._fit_items(width) > 0
    scr._fit_items(1200)
    scr._fit_items(300)
    hits = [r for r in caplog.records if "narrower than its column floors" in r.getMessage()]
    assert len(hits) == 2


def test_scrm7_refresh_keeps_the_fit(scr, monkeypatch):
    """SCR-M7 — rows rebuilt by refresh() are fitted to the list's width."""
    monkeypatch.setattr(scr.items_frame, "winfo_width", lambda: 1100)
    monkeypatch.setattr(scr, "_get_widget_scaling", lambda: 1.0)
    scr.refresh()
    scr.update_idletasks()
    assert sum(_widths(scr).values()) + RESERVED == 1100
    for _frame, cells in scr.resizer._rows:
        for key, label, *_ in cells:
            assert int(label.cget("width")) == scr.resizer.width(key)


def test_scrm1b_no_ceiling_on_a_wide_list(scr):
    """SCR-M1 — a very wide list is still filled; no column stops at a cap."""
    scr._fit_items(6000)
    assert sum(_widths(scr).values()) + RESERVED == 6000


def test_scr_headings_padded_like_their_cells(scr):
    """Each heading has its cell's padding, so it sits over its column."""
    labels = scr.resizer._header[1]
    frame, cells = scr.resizer._rows[0]
    for key, label, *_ in cells:
        assert labels[key].grid_info()["padx"] == label.grid_info()["padx"], key
    header_box = scr.select_all_checkbox.grid_info()["padx"]
    row_box = [w for w in frame.grid_slaves(row=0, column=0)][0].grid_info()["padx"]
    assert header_box == row_box


def test_scr_headings_are_cut_to_their_column(scr):
    """A heading wider than its column is cut with "...", and comes back whole.

    Found by the csdp sweep: at the 48px floor an uncut bold heading widened
    its header column and pushed the headings after it off their rows.
    """
    labels = scr.resizer._header[1]
    scr._fit_items(1)
    # 48px at 8px a character leaves 6 characters.
    assert labels["subsegment"].cget("text") == "Sub..."
    assert labels["start_date"].cget("text") == "Sta..."
    assert labels["title"].cget("text") == "Title"
    scr._fit_items(2400)
    assert labels["subsegment"].cget("text") == "SubSegment"
    assert labels["start_date"].cget("text") == "Start Date"
