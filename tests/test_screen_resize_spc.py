"""SPC — Schedule, Projects and Completed resize with the window.

Purpose: SPC-M1..M17 — Completed and the Projects Action Items list share
         their width out to their own columns, and all three screens' headers
         wrap to a second row instead of clipping.
Spec:    docs/unused-docs/implementation_plan_2026-11-15_schedule_projects_completed_resize.md
Tests:   this file

Withdrawn windows, except ``test_spcm15_*``, which takes ``mapped_windows``:
a withdrawn window is 1px wide and gets no ``<Configure>``, so only that one
reads real geometry. Everything else drives ``fit``/``ToolbarWrap.fit``
directly and reads grid options and ``cget``, which need no map.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.getmoredone.app import (
    CONTENT_PAD_PX,
    DEFAULT_WINDOW_WIDTH_PX,
    SIDEBAR_WIDTH_PX,
)
from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, ProjectBoard
from src.getmoredone import theme
from src.getmoredone.screens.item_list_columns import (
    FIT_DELAY_MS,
    LIST_MIN_CHARS,
    ToolbarWrap,
    _pad_total,
    column_default_px,
    row_char_px,
)
from src.getmoredone.screens.priority_cell import SCORE_CELL_WIDTH_PX

COMPLETED_KEYS = ("title", "who", "completed", "pri")
PROJECT_KEYS = ("title", "status", "start", "due")
# The defaults each list opens at, which are also its weights (SPC-D5).
# LRP-M6: read from COLUMN_DEFAULT_PX rather than copied, so a changed
# default cannot leave these asserting proportions no screen has. The
# priority cell is not shared (UNSHARED_KEYS) and keeps its own width.
COMPLETED_DEFAULTS = {k: column_default_px(k) for k in COMPLETED_KEYS
                      if k != "pri"} | {"pri": SCORE_CELL_WIDTH_PX}
PROJECT_DEFAULTS = {k: column_default_px(k) for k in PROJECT_KEYS}


def _floor():
    return LIST_MIN_CHARS * row_char_px()


def _app():
    app = MagicMock()
    app.vps_manager.get_segment_colors_by_id.return_value = {}
    app.vps_manager.get_segment_color_map.return_value = {}
    return app


def _root(mapped=False):
    root = ctk.CTk()
    if not mapped:
        root.withdraw()
    root.geometry("1400x800")
    return root


@pytest.fixture
def completed_screen(tmp_path):
    """A real CompletedScreen with three completed rows."""
    from src.getmoredone.screens.completed import CompletedScreen

    built = []

    def _make(mapped=False, expanded=False):
        root = _root(mapped)
        db = DatabaseManager(str(tmp_path / "completed.db"))
        for n in range(3):
            item_id = db.create_action_item(ActionItem(
                who="Self", title=f"Write the quarterly summary {n}",
                importance=3, urgency=3, size=3, value=3))
            db.complete_action_item(item_id)
        screen = CompletedScreen(root, db, _app())
        screen.pack(fill="both", expand=True)
        if expanded:
            screen.toggle_columns()
        screen.update_idletasks()
        assert screen.layout.resizer._rows, "Completed rendered no rows"
        built.append((root, db))
        return screen

    yield _make
    for root, db in built:
        db.close()
        try:
            root.destroy()
        except Exception:
            pass


@pytest.fixture
def projects_screen(tmp_path):
    """A real ProjectBoardsScreen with a selected board and four linked items."""
    from src.getmoredone.screens.project_boards import ProjectBoardsScreen

    built = []

    def _make(mapped=False):
        root = _root(mapped)
        db = DatabaseManager(str(tmp_path / "projects.db"))
        board_id = db.create_project_board(ProjectBoard(title="Board One"))
        for n in range(4):
            item_id = db.create_action_item(ActionItem(
                who="Self", title=f"Linked task {n}", status="open",
                start_date="2026-11-15", due_date="2026-11-20",
                next_action="Call the supplier about the delivery window"))
            db.link_action_item_to_project_board(board_id, item_id)
        screen = ProjectBoardsScreen(root, db, SimpleNamespace(vps_manager=None))
        screen.pack(fill="both", expand=True)
        screen.selected_board_id = board_id
        screen.refresh()
        screen.update_idletasks()
        assert screen.items_layout.resizer._rows, "Projects rendered no item rows"
        built.append((root, db))
        return screen

    yield _make
    for root, db in built:
        db.close()
        try:
            root.destroy()
        except Exception:
            pass


@pytest.fixture
def scheduler_screen(tmp_path):
    """A real DragScheduleScreen, for the header wrap only."""
    from src.getmoredone.screens.drag_schedule import DragScheduleScreen
    from src.getmoredone.vps_manager import VPSManager

    built = []

    def _make(mapped=False):
        db_path = str(tmp_path / "sched.db")
        db = DatabaseManager(db_path)
        for n in range(3):
            db.create_action_item(ActionItem(who="Self", title=f"Task {n}"))
        vps = VPSManager(db_path)
        root = _root(mapped)
        screen = DragScheduleScreen(root, db, SimpleNamespace(vps_manager=vps))
        screen.pack(fill="both", expand=True)
        screen.update_idletasks()
        built.append((root, db, vps))
        return screen

    yield _make
    for root, db, vps in built:
        try:
            root.destroy()
        except Exception:
            pass
        vps.close()
        db.close()


def _widths(layout, keys):
    return {k: layout.width(k) for k in keys}


def _cells(layout):
    """Every registered cell of every live row: (key, label, width_delta)."""
    out = []
    for frame, cells in layout.resizer._rows:
        if not frame.winfo_exists():
            continue
        for key, label, _full, _reserve, delta in cells:
            out.append((key, label, delta))
    return out


def _pending_after(screen, monkeypatch, measured, width):
    """Capture `after` callbacks and fix the measured width (as SCR does)."""
    pending = []
    monkeypatch.setattr(screen, "after", lambda ms, fn: pending.append(fn) or "id")
    monkeypatch.setattr(screen, "after_cancel", lambda _id: None)
    monkeypatch.setattr(measured, "winfo_width", lambda: width)
    monkeypatch.setattr(screen, "_get_widget_scaling", lambda: 1.0)
    return pending


# ------------------------------------------------------------------- Completed


def test_spcm1_completed_columns_fill_the_list(completed_screen):
    """SPC-M1 — the four columns and the reserved cells add up to the list."""
    layout = completed_screen().layout
    layout.fit(1000)
    assert (sum(_widths(layout, COMPLETED_KEYS).values())
            + layout.reserved_px() == 1000)


def test_spcm2_completed_follows_the_width(completed_screen):
    """SPC-M2 — a wider list widens all four, in their default proportions."""
    layout = completed_screen().layout
    layout.fit(900)
    narrow = _widths(layout, COMPLETED_KEYS)
    layout.fit(1500)
    wide = _widths(layout, COMPLETED_KEYS)
    for key in COMPLETED_KEYS:
        assert wide[key] > narrow[key], key
    for key in ("who", "completed", "pri"):
        want = COMPLETED_DEFAULTS["title"] / COMPLETED_DEFAULTS[key]
        assert abs(wide["title"] / wide[key] - want) < 0.05, key
    for key, label, delta in _cells(layout):
        assert int(label.cget("width")) == max(1, wide[key] - delta), key


def test_spcm3_completed_floor_is_six_characters(completed_screen, caplog):
    """SPC-M3 — no column below 6 characters; the shortfall is logged once."""
    layout = completed_screen().layout
    caplog.set_level("INFO", logger="src.getmoredone.screens.item_list_columns")
    for width in (1200, 600, 300, 1):
        layout.fit(width)
        assert min(_widths(layout, COMPLETED_KEYS).values()) >= _floor(), width
    assert set(_widths(layout, COMPLETED_KEYS).values()) == {_floor()}
    layout.fit(1200)
    layout.fit(1)
    hits = [r for r in caplog.records
            if "narrower than its column floors" in r.getMessage()]
    assert len(hits) == 2, [r.getMessage() for r in hits]


def test_spcm4_completed_configure_and_refresh_refit(completed_screen, monkeypatch):
    """SPC-M4 — a <Configure> refits once after the wait, and a refresh keeps it."""
    screen = completed_screen()
    layout = screen.layout
    pending = _pending_after(screen, monkeypatch, screen.scroll_frame, 1300)

    screen.scroll_frame.event_generate("<Configure>")
    assert len(pending) == 1, "the list's <Configure> scheduled no fit"
    pending[0]()
    assert (sum(_widths(layout, COMPLETED_KEYS).values())
            + layout.reserved_px() == 1300)

    pending.clear()
    screen.refresh()
    assert pending, "a rebuild scheduled no refit"
    for fn in pending:
        fn()
    assert (sum(_widths(layout, COMPLETED_KEYS).values())
            + layout.reserved_px() == 1300)
    for key, label, delta in _cells(layout):
        assert int(label.cget("width")) == max(1, layout.width(key) - delta), key


def test_spcm5_completed_drag_sets_one_share(completed_screen, monkeypatch, tmp_path):
    """SPC-M5 — a drag changes one share, is saved, and keeps its dropped width."""
    monkeypatch.setattr(AppSettings, "get_settings_path",
                        staticmethod(lambda: tmp_path / "drag-settings.json"))
    screen = completed_screen()
    layout = screen.layout
    resizer = layout.resizer
    assert set(resizer._header[1]) == set(COMPLETED_KEYS), "a column has no divider"
    pending = _pending_after(screen, monkeypatch, screen.scroll_frame, 1200)
    layout.fit(1200)
    before = dict(resizer._weights)
    dropped_from = resizer.width("who")

    resizer._on_start(SimpleNamespace(x_root=500), "who")
    resizer._on_drag(SimpleNamespace(x_root=560), "who")
    resizer._on_stop(SimpleNamespace(x_root=560), "who")

    assert resizer._weights["who"] > before["who"]
    assert AppSettings.load().completed_col_widths["who"] == round(
        resizer._weights["who"])
    assert len(pending) == 1, "the drag's end scheduled no refit"
    pending[0]()
    assert (sum(_widths(layout, COMPLETED_KEYS).values())
            + layout.reserved_px() == 1200)
    assert abs(resizer.width("who") - (dropped_from + 60)) <= 1


def test_spcm6_completed_shape_survives_a_narrow_window(completed_screen):
    """SPC-M6 — the shape comes back, and headings are cut and come back whole."""
    layout = completed_screen().layout
    labels = layout.resizer._header[1]
    layout.fit(1200)
    shape = _widths(layout, COMPLETED_KEYS)

    layout.fit(1)
    assert labels["completed"].cget("text") == "Com..."
    assert labels["who"].cget("text") == "Who"

    layout.fit(1200)
    assert _widths(layout, COMPLETED_KEYS) == shape
    assert labels["completed"].cget("text") == "Completed"


@pytest.mark.parametrize("expanded", [False, True], ids=["collapsed", "expanded"])
def test_spcm7_completed_controls_preserved(completed_screen, expanded):
    """SPC-M7 — every control is still there and the header agrees per column."""
    screen = completed_screen(expanded=expanded)
    layout = screen.layout
    header_cols = {key: layout.grid_col(key) for key in COMPLETED_KEYS}

    assert screen.expand_collapse_btn.winfo_exists()
    assert screen.stats_label.cget("text").startswith("Count: ")
    assert screen.days_combo.winfo_exists() and screen.who_combo.winfo_exists()

    rows = [f for f, _c in layout.resizer._rows if f.winfo_exists()]
    assert len(rows) == 3
    for frame in rows:
        occupied = {int(w.grid_info()["column"]) for w in frame.grid_slaves()}
        # The checkmark, the four columns, and Reopen; the chips when expanded.
        expected = {0} | set(header_cols.values())
        expected |= {6, 5} if expanded else {5}
        assert occupied == expected, (expanded, sorted(occupied))
        texts = [w.cget("text") for w in frame.grid_slaves()
                 if isinstance(w, ctk.CTkButton)]
        assert texts == ["Reopen"], texts
    for key, label in layout.resizer._header[1].items():
        assert int(label.grid_info()["column"]) == header_cols[key], key


# -------------------------------------------------------------------- Projects


def test_spcm8_project_items_are_columns(projects_screen):
    """SPC-M8 — the rows are columnar and the four columns fill the list."""
    screen = projects_screen()
    layout = screen.items_layout
    layout.fit(900)
    assert (sum(_widths(layout, PROJECT_KEYS).values())
            + layout.reserved_px() == 900)
    keys = {key for key, _label, _delta in _cells(layout)}
    assert keys == set(PROJECT_KEYS), sorted(keys)
    # The old one-line meta string is gone: Start and Due are columns now.
    for _key, label, _delta in _cells(layout):
        assert "Status:" not in label.cget("text")
        assert "| Start:" not in label.cget("text")


def test_spcm9_project_items_follow_the_width(projects_screen):
    """SPC-M9 — a wider panel widens all four; the floor is 6 characters."""
    layout = projects_screen().items_layout
    layout.fit(700)
    narrow = _widths(layout, PROJECT_KEYS)
    layout.fit(1200)
    wide = _widths(layout, PROJECT_KEYS)
    for key in PROJECT_KEYS:
        assert wide[key] > narrow[key], key
    want = PROJECT_DEFAULTS["title"] / PROJECT_DEFAULTS["status"]
    assert abs(wide["title"] / wide["status"] - want) < 0.05
    layout.fit(1)
    assert set(_widths(layout, PROJECT_KEYS).values()) == {_floor()}


def test_spcm10_project_items_drag_sets_one_share(projects_screen, monkeypatch,
                                                  tmp_path):
    """SPC-M10 — a drag saves under project_items_col_widths and holds its width."""
    monkeypatch.setattr(AppSettings, "get_settings_path",
                        staticmethod(lambda: tmp_path / "drag-settings.json"))
    screen = projects_screen()
    layout = screen.items_layout
    resizer = layout.resizer
    assert set(resizer._header[1]) == set(PROJECT_KEYS), "a column has no divider"
    pending = _pending_after(screen, monkeypatch, screen.items_frame, 1000)
    layout.fit(1000)
    before = dict(resizer._weights)
    dropped_from = resizer.width("status")

    resizer._on_start(SimpleNamespace(x_root=400), "status")
    resizer._on_drag(SimpleNamespace(x_root=450), "status")
    resizer._on_stop(SimpleNamespace(x_root=450), "status")

    assert resizer._weights["status"] > before["status"]
    assert AppSettings.load().project_items_col_widths["status"] == round(
        resizer._weights["status"])
    assert len(pending) == 1, "the drag's end scheduled no refit"
    pending[0]()
    assert abs(resizer.width("status") - (dropped_from + 50)) <= 1


def test_spcm11_next_action_follows_the_title_column(projects_screen):
    """SPC-M11 — "Next: …" is cut to the Title column and follows it."""
    layout = projects_screen().items_layout
    next_cells = [(label, delta) for key, label, delta in _cells(layout)
                  if key == "title" and label.cget("text").startswith("Next:")]
    assert next_cells, "no Next cell is registered in the Title column"
    layout.fit(1)
    narrow = [label.cget("text") for label, _d in next_cells]
    assert all(text.endswith("...") for text in narrow), narrow
    layout.fit(2000)
    for label, delta in next_cells:
        assert int(label.cget("width")) == max(1, layout.width("title") - delta)
        assert not label.cget("text").endswith("...")


def test_spcm12_project_items_configure_and_rerender_refit(projects_screen,
                                                           monkeypatch):
    """SPC-M12 — a <Configure> refits once; the fit survives _render_detail()."""
    screen = projects_screen()
    layout = screen.items_layout
    pending = _pending_after(screen, monkeypatch, screen.items_frame, 1100)

    screen.items_frame.event_generate("<Configure>")
    assert len(pending) == 1, "the items area's <Configure> scheduled no fit"
    pending[0]()
    assert (sum(_widths(layout, PROJECT_KEYS).values())
            + layout.reserved_px() == 1100)

    pending.clear()
    screen._render_detail()
    assert pending, "a re-render scheduled no refit"
    for fn in pending:
        fn()
    for key, label, delta in _cells(layout):
        assert int(label.cget("width")) == max(1, layout.width(key) - delta), key


def test_spcm13_project_items_controls_preserved(projects_screen):
    """SPC-M13 — the items contract: checkbox, Select All, count, the buttons."""
    screen = projects_screen()
    assert screen.check_all_var is not None
    assert len(screen.item_checkbox_vars) == 4, screen.item_checkbox_vars

    def _texts(widget, kind):
        found = []
        for child in widget.winfo_children():
            if isinstance(child, kind):
                found.append(child.cget("text"))
            found.extend(_texts(child, kind))
        return found

    buttons = _texts(screen.items_frame, ctk.CTkButton)
    for text in ("Edit", "Complete", "Unlink"):
        assert buttons.count(text) == 4, (text, buttons)
    boxes = _texts(screen.items_frame, ctk.CTkCheckBox)
    assert "Select All" in boxes, boxes
    assert "Show Completed" in boxes, boxes
    assert boxes.count("") == 4, boxes


# --------------------------------------------------------------------- toolbars


def _wrapped_group(screen):
    wrap = screen.toolbar_wrap
    return [w.cget("text") if hasattr(w, "cget") else w
            for w, _info in wrap._moved]


@pytest.mark.parametrize("name", ["completed", "projects", "scheduler"])
def test_spcm14_header_wraps_and_unwraps(name, completed_screen, projects_screen,
                                         scheduler_screen):
    """SPC-M14 — each header wraps its right-hand group and unwraps again."""
    screen = {"completed": completed_screen, "projects": projects_screen,
              "scheduler": scheduler_screen}[name]()
    wrap = screen.toolbar_wrap
    one_row = wrap.one_row_px()
    assert one_row > 0

    wrap.fit(one_row + 50)
    assert wrap.wrapped is False
    # A control the screen took out of the grid itself (the Project Board's
    # warning line) is not the wrap's to put back.
    gridded = {w for w in wrap.toolbar.winfo_children() if w.grid_info()}

    wrap.fit(one_row - 50)
    assert wrap.wrapped is True, f"{name} did not wrap"
    assert wrap._moved, f"{name} wrapped nothing"
    assert int(wrap.frame.grid_info()["row"]) == wrap.wrap_row
    for widget, _info in wrap._moved:
        assert str(widget.grid_info()["in"]) == str(wrap.frame), widget

    wrap.fit(one_row + 50)
    assert wrap.wrapped is False, f"{name} did not unwrap"
    back = {w for w in wrap.toolbar.winfo_children()
            if w is not wrap.frame and w.grid_info()}
    assert back == gridded, "the unwrap dropped or added a control"


@pytest.mark.parametrize("name", ["completed", "projects", "scheduler"])
def test_spcm15_narrow_window_wraps_and_nothing_clips(
        name, completed_screen, projects_screen, scheduler_screen,
        mapped_windows):
    """SPC-M15 — on a real narrow window each header wraps and nothing clips.

    One screen per test: CustomTkinter builds an image against the first CTk
    root in the process, so a second root in the same test cannot draw the
    Project Board's edit icon (``image "pyimage1" doesn't exist``).
    """
    screen = {"completed": completed_screen, "projects": projects_screen,
              "scheduler": scheduler_screen}[name](mapped=True)
    wrap = screen.toolbar_wrap
    # Inside the band where two rows are the point: narrow enough to wrap,
    # wide enough to hold the wrapped row. Below wrap_row_px() it clips, and
    # nothing stops the window going there (D11) -- a fixed 760 put the
    # Scheduler (991) and Projects (844) below their own second row, where
    # the group overflowed the left edge and this test could not fail.
    width = wrap.one_row_px() - 40
    root = screen.winfo_toplevel()
    root.geometry(f"{width}x600")
    root.update()
    screen.update_idletasks()
    assert wrap.wrapped is True, f"{name} did not wrap at {width}px"
    # The band, checked on the toolbar and not on the window: the geometry
    # above is a window number, and the toolbar is narrower by the sidebar
    # and by every frame's padding, so comparing the two measures different
    # things (SPC-S3).
    assert wrap.toolbar.winfo_width() > wrap.wrap_row_px(), (
        name, wrap.toolbar.winfo_width(), wrap.wrap_row_px())
    toolbar_left = wrap.toolbar.winfo_rootx()
    toolbar_right = toolbar_left + wrap.toolbar.winfo_width()
    for widget, _info in wrap._moved:
        left = widget.winfo_rootx()
        right = left + widget.winfo_width()
        # Both edges. The frame is gridded sticky="w" since LRP-M1, so an
        # over-wide second row now overflows RIGHT; it was "e" when SPC-S2
        # was written and the overflow went left, out of sight of a
        # right-edge check. Checking both survives either direction.
        assert right <= toolbar_right + 1, (name, widget, right, toolbar_right)
        assert left >= toolbar_left - 1, (name, widget, left, toolbar_left)


def test_spcm16_only_the_control_row_wraps(projects_screen):
    """SPC-M16 — the Projects search row and warning stay on their own rows."""
    screen = projects_screen()
    wrap = screen.toolbar_wrap
    rows = {w: int(w.grid_info()["row"]) for w in (
        screen.search_entry, screen.btn_search, screen.btn_clear_search)}
    assert set(rows.values()) == {2}, rows

    wrap.fit(wrap.one_row_px() - 100)

    assert wrap.wrapped is True
    moved = {w for w, _info in wrap._moved}
    # The warning line sits below the search row and is taken out of the grid
    # when there is nothing to report; either way the wrap leaves it alone.
    assert screen.multi_link_label not in moved
    for widget, row in rows.items():
        assert widget not in moved, widget
        assert int(widget.grid_info()["row"]) == row, widget
        assert str(widget.grid_info()["in"]) == str(wrap.toolbar)


@pytest.mark.parametrize("name", ["completed", "projects", "scheduler"])
def test_spcs2_two_rows_need_less_width_than_one(name, completed_screen,
                                                 projects_screen,
                                                 scheduler_screen):
    """SPC-S2 — the wrapped row fits in a width where one row does not.

    The band `wrap_row_px() <= W < one_row_px()` is the whole point of the
    wrap, and it has to be non-empty: the frame keeps its requested width, so
    a second row wider than the toolbar overflows one edge out of sight
    instead of reporting anything -- the left edge when this was written
    (`sticky="e"`), the right since LRP-M1. Needs no mapped window -- both
    numbers are requested widths, which a withdrawn window has.
    """
    screen = {"completed": completed_screen, "projects": projects_screen,
              "scheduler": scheduler_screen}[name]()
    wrap = screen.toolbar_wrap
    assert wrap.wrap_row_px() > 0
    assert wrap.wrap_row_px() < wrap.one_row_px(), (
        name, wrap.wrap_row_px(), wrap.one_row_px())
    # The band is where the wrap is used, so it must actually wrap there.
    wrap.fit(wrap.one_row_px() - 1)
    assert wrap.wrapped is True, name
    # And the group it moved is the one the measurement was taken over.
    assert wrap.wrap_row_px() == sum(
        w.winfo_reqwidth() + _pad_total(i["padx"]) for w, i in wrap._moved)


def test_spcs2_one_row_counts_a_column_once(completed_screen):
    """SPC-S2 -- one row is the sum of column maxima, not of every widget.

    Two controls stacked in one column need that column once. Summing the
    widgets instead inflates one row and wraps a toolbar that would have
    fitted. Every real toolbar puts one control per column, so none of them
    can tell the two apart; this one can.
    """
    screen = completed_screen()
    toolbar = ctk.CTkFrame(screen)
    wide = ctk.CTkButton(toolbar, text="A", width=100)
    wide.grid(row=0, column=0, padx=5)
    narrow = ctk.CTkButton(toolbar, text="B", width=60)
    narrow.grid(row=0, column=0, padx=5)
    alone = ctk.CTkFrame(toolbar, width=40)
    alone.grid(row=0, column=1, padx=0)
    toolbar.update_idletasks()

    wrap = ToolbarWrap(toolbar, None, None, 0)
    stacked = [w.winfo_reqwidth() + 10 for w in (wide, narrow)]
    assert min(stacked) < max(stacked), stacked
    assert wrap.one_row_px() == max(stacked) + alone.winfo_reqwidth()
    assert wrap.one_row_px() < sum(stacked) + alone.winfo_reqwidth()


OLD_TOOLBARS = {
    "today": ("today", "TodayScreen"),
    "upcoming": ("upcoming", "UpcomingScreen"),
    "all_items": ("all_items", "AllItemsScreen"),
    "hierarchical": ("hierarchical", "HierarchicalScreen"),
}


def _build_old_toolbar_screen(name, tmp_path):
    """One of the four screens that already wrapped, on its own root.

    Returns (root, db, screen); the caller closes the db and destroys the
    root. Shared so the four-screen table exists once (P4).
    """
    import importlib

    module, attr = OLD_TOOLBARS[name]
    cls = getattr(importlib.import_module(
        f"src.getmoredone.screens.{module}"), attr)
    root = _root()
    db = DatabaseManager(str(tmp_path / f"{name}.db"))
    db.create_action_item(ActionItem(who="Self", title="A task"))
    screen = cls(root, db, _app())
    screen.pack(fill="both", expand=True)
    screen.update_idletasks()
    return root, db, screen


def _toolbar_budget(wrap, screen):
    """The width this toolbar gets when the app opens at DEFAULT_GEOMETRY.

    The content frame is the window less the sidebar and its own padding; the
    toolbar is that less the padding of every frame between it and the screen.
    """
    budget = DEFAULT_WINDOW_WIDTH_PX - SIDEBAR_WIDTH_PX - 2 * CONTENT_PAD_PX
    widget = wrap.toolbar
    while widget is not None and widget is not screen:
        info = widget.grid_info() or {}
        assert info, (
            f"{widget} between the toolbar and the screen is not grid-managed;"
            " its padding would be read as zero and the budget would come out"
            " too large")
        budget -= _pad_total(info.get("padx", 0))
        widget = widget.master
    # Both sides in the same units: winfo_reqwidth and grid_info's padx are
    # scaled pixels, and the three constants are logical ones. They differ on
    # a HiDPI Windows display, where the window geometry is scaled too.
    return wrap.toolbar._apply_widget_scaling(budget)


def _assert_wrapped_row_fits(name, screen):
    wrap = screen.toolbar_wrap
    budget = _toolbar_budget(wrap, screen)
    assert budget > 0, (name, budget)
    assert wrap.wrap_row_px() <= budget, (
        f"{name}: the wrapped second row needs {wrap.wrap_row_px()} px and "
        f"the header gets {budget} px at the default window")


@pytest.mark.parametrize("name", ["completed", "projects", "scheduler"])
def test_spcs3_the_new_wrapped_rows_fit_the_default_window(
        name, completed_screen, projects_screen, scheduler_screen):
    """SPC-S3 -- the wrapped second row fits the window the app opens at.

    ``wrap_row_px`` says how wide two rows need to be, and nothing compared it
    with the width a header actually gets at ``DEFAULT_GEOMETRY``. The
    Scheduler's four filters needed 991 px against 960, so on every launch the
    wrapped row ran off the toolbar's left edge -- the frame was then
    ``sticky="e"``, so the overflow went left -- and clipped the ``Who:``
    filter. A right-edge assertion reads that as a pass. Since LRP-M1 the
    frame is ``sticky="w"`` and an overflow would go right instead; this
    budget is what keeps it from happening at all.

    Both sides are requested widths, so this needs no window on screen.
    """
    screen = {"completed": completed_screen, "projects": projects_screen,
              "scheduler": scheduler_screen}[name]()
    _assert_wrapped_row_fits(name, screen)


@pytest.mark.parametrize("name", list(OLD_TOOLBARS))
def test_spcs3_the_old_wrapped_rows_fit_the_default_window(name, tmp_path):
    """SPC-S3 -- and so do the four toolbars that already wrapped."""
    root, db, screen = _build_old_toolbar_screen(name, tmp_path)
    try:
        _assert_wrapped_row_fits(name, screen)
    finally:
        db.close()
        root.destroy()


def test_spcs2_the_wrapped_group_survives_a_cycle(completed_screen):
    """SPC-S2 — the same controls, in the same order, wrapped or not.

    ``_wrap`` selects its group through ``_one_row_placements()`` now, which
    returns the captured infos once wrapped and live ``grid_info`` before: the
    two branches must agree, or ``wrap_row_px()`` measures one group while
    ``_wrap`` moves another.
    """
    wrap = completed_screen().toolbar_wrap

    def shape():
        return [(id(w), int(i["column"])) for w, i in wrap._wrap_candidates()]

    before, px_before = shape(), wrap.wrap_row_px()
    assert before, "no control sits right of the spacer column"
    wrap.fit(wrap.one_row_px() - 50)
    assert wrap.wrapped is True
    assert shape() == before and wrap.wrap_row_px() == px_before
    wrap.fit(wrap.one_row_px() + 50)
    assert wrap.wrapped is False
    assert shape() == before and wrap.wrap_row_px() == px_before


def test_spcs1_the_project_title_tracks_the_row_font(projects_screen,
                                                     monkeypatch):
    """SPC-S1 — the bold Action Items title is the row font's size, not 15.

    The resizer cuts that cell at ``row_char_px()``, which follows the user's
    list font setting; a hardcoded 15 meant a larger setting grew the
    character budget while the drawn text stayed put.
    """
    from src.getmoredone.screens import item_list_columns

    monkeypatch.setattr(theme, "LIST_ROW_FONT_SIZE", 20)
    assert item_list_columns.row_char_px() == 11, "the budget did not follow"
    screen = projects_screen()
    titles = [label for key, label, _d in _cells(screen.items_layout)
              if key == "title" and "Next:" not in label.cget("text")]
    assert titles, "no title cell registered"
    for label in titles:
        font = label.cget("font")
        assert int(font.cget("size")) == 20, font.cget("size")
        assert font.cget("weight") == "bold", font.cget("weight")


@pytest.mark.parametrize("name", ["today", "upcoming", "all_items", "hierarchical"])
def test_spcm17_existing_toolbars_unchanged(name, tmp_path):
    """SPC-M17 — the four screens already wrapping keep the same group and width.

    The search entry's minimum still counts towards one row, and the control
    row and wrap row are still 0 and 1, so the generalisation for the screens
    that have no search entry cannot change these four.
    """
    from src.getmoredone.screens.item_list_columns import SEARCH_MIN_PX

    root, db, screen = _build_old_toolbar_screen(name, tmp_path)
    try:
        wrap = screen.toolbar_wrap
        assert wrap.entry is screen.search_entry
        assert wrap.control_row == 0 and wrap.wrap_row == 1
        # The entry's column is excluded and its minimum added instead --
        # pinned exactly, not as a floor: a floor cannot see the threshold
        # move that this test exists to catch (repo test rules).
        columns = {}
        for widget in wrap.toolbar.winfo_children():
            info = widget.grid_info()
            if not info or widget is wrap.frame or int(info["row"]) != 0:
                continue
            col = int(info["column"])
            if col == wrap.search_col:
                continue
            need = widget.winfo_reqwidth() + _pad_total(info["padx"])
            columns[col] = max(columns.get(col, 0), need)
        assert wrap.one_row_px() == sum(columns.values()) + SEARCH_MIN_PX
        wrap.fit(wrap.one_row_px() - 50)
        assert wrap.wrapped is True
        moved = {w for w, _info in wrap._moved}
        assert screen.search_entry not in moved
        assert moved, f"{name} wrapped nothing"
    finally:
        db.close()
        root.destroy()


@pytest.mark.parametrize("name,attr", [("completed", "layout"),
                                       ("projects", "items_layout")])
def test_spc_the_new_lists_use_the_shared_debounce(name, attr, completed_screen,
                                                   projects_screen):
    """Both new lists wait FIT_DELAY_MS, not a second constant of their own."""
    screen = {"completed": completed_screen, "projects": projects_screen}[name]()
    layout = getattr(screen, attr)
    delays = []
    screen.after = lambda ms, fn: delays.append(ms) or "id"
    screen.after_cancel = lambda _id: None
    layout._on_configure()
    assert delays == [FIT_DELAY_MS], (attr, delays)
