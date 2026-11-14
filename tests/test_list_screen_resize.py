"""LSR — the four item lists resize with the window.

Purpose: prove Today, Upcoming, All Items and Hierarchical share their width
         out to the stretching columns, keep header and rows aligned, and
         refit on a real resize.
Spec:    docs/unused-docs/implementation_plan_2026-11-13_resizable_list_layouts.md
Tests:   this file

Withdrawn windows, except the two tests that take ``mapped_windows``: a
withdrawn window is 1px wide and gets no ``<Configure>``, so those read real
geometry. Everything else reads grid options and ``cget``, which need no map.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem
from src.getmoredone.screens.column_resize import min_column_width
from src.getmoredone.screens.item_list_columns import (
    FIT_DELAY_MS,
    SEARCH_MIN_PX,
    STRETCH_KEYS,
    TITLE_MIN_PX,
    row_char_px,
)

SCREENS = ("today", "upcoming", "all_items", "hierarchical")
EXPANDABLE = ("today", "upcoming", "all_items")


def _screen_class(name):
    if name == "today":
        from src.getmoredone.screens.today import TodayScreen
        return TodayScreen
    if name == "upcoming":
        from src.getmoredone.screens.upcoming import UpcomingScreen
        return UpcomingScreen
    if name == "all_items":
        from src.getmoredone.screens.all_items import AllItemsScreen
        return AllItemsScreen
    from src.getmoredone.screens.hierarchical import HierarchicalScreen
    return HierarchicalScreen


def _app():
    app = MagicMock()
    app.vps_manager.get_segment_colors_by_id.return_value = {}
    app.vps_manager.get_segment_color_map.return_value = {}
    return app


def _seed(db, count=2, title="Write the quarterly summary for the board"):
    today = date.today().isoformat()
    parent = None
    for n in range(count):
        item = ActionItem(who="Self", title=f"{title} {n}", start_date=today,
                          due_date=today)
        db.create_action_item(item)
    # A three-level tree for Hierarchical (LSR-M8).
    for depth in range(3):
        item = ActionItem(who="Self", title=f"Level {depth} item", start_date=today,
                          due_date=today, parent_id=parent)
        parent = db.create_action_item(item)


@pytest.fixture
def make(tmp_path):
    """Build one screen on a withdrawn root, every database on tmp_path."""
    built = []

    def _make(name, expanded=False, count=2, mapped=False):
        root = ctk.CTk()
        if not mapped:
            root.withdraw()
        root.geometry("1400x800")
        db = DatabaseManager(str(tmp_path / f"{name}.db"))
        _seed(db, count)
        built.append((root, db))
        screen = _screen_class(name)(root, db, _app())
        screen.pack(fill="both", expand=True)
        if expanded and not screen.columns_expanded:
            screen.toggle_columns()
        elif not expanded and getattr(screen, "columns_expanded", False):
            screen.toggle_columns()
        screen.update_idletasks()
        assert screen.layout.resizer._rows, f"{name} rendered no rows"
        return root, screen

    yield _make
    for root, db in built:
        db.close()
        try:
            root.destroy()
        except Exception:
            pass


def _managed_cols(layout):
    cols = [layout.grid_col(k) for k in STRETCH_KEYS]
    return cols + [c.grid_col for c in layout.lead + layout.fixed]


def _rows(layout):
    return [(frame, cells) for frame, cells in layout.resizer._rows
            if frame.winfo_exists()]


def _params():
    out = [(name, False) for name in SCREENS]
    out += [(name, True) for name in EXPANDABLE]
    return out


@pytest.mark.parametrize("name,expanded", _params())
def test_lsrm1_header_and_rows_agree_per_column(make, name, expanded):
    """LSR-M1 — every managed column is one width in the header and every row.

    A row that set its own minsize, or the header left out a fixed column,
    is a column that does not line up.
    """
    _root, screen = make(name, expanded=expanded)
    layout = screen.layout
    header = screen.column_header
    for col in _managed_cols(layout):
        want = header.grid_columnconfigure(col)["minsize"]
        assert want > 0, f"{name}: header column {col} has no width"
        for frame, _cells in _rows(layout):
            assert frame.grid_columnconfigure(col)["minsize"] == want, (
                f"{name}: row column {col} is "
                f"{frame.grid_columnconfigure(col)['minsize']}, header {want}")
    for key in STRETCH_KEYS:
        assert layout.header_labels[key].cget("width") == layout.width(key)
    for _frame, cells in _rows(layout):
        for key, label, _full, _reserve, delta in cells:
            assert label.cget("width") == layout.width(key) - delta


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm2_wider_list_widens_only_stretch_columns(make, name):
    """LSR-M2a — the extra width goes to the four stretching columns, in proportion."""
    _root, screen = make(name)
    layout = screen.layout
    fixed_before = {c.grid_col: c.column_px for c in layout.lead + layout.fixed}

    layout.fit(1100)
    narrow = {k: layout.width(k) for k in STRETCH_KEYS}
    layout.fit(1700)
    wide = {k: layout.width(k) for k in STRETCH_KEYS}

    for key in STRETCH_KEYS:
        assert wide[key] > narrow[key], f"{name}: {key} did not widen"
    assert sum(wide.values()) == 1700 - layout.reserved_px()
    # Proportional: Title keeps its share of the four to within a pixel per column.
    share = narrow["title"] / sum(narrow.values())
    assert abs(wide["title"] - share * sum(wide.values())) <= len(STRETCH_KEYS)
    for frame, _cells in _rows(layout):
        assert frame.grid_columnconfigure(layout.grid_col("title"))["minsize"] == wide["title"]
        for col, px in fixed_before.items():
            assert frame.grid_columnconfigure(col)["minsize"] == px


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm2_resize_event_refits(make, name, mapped_windows):
    """LSR-M2b — the real <Configure> binding drives the fit, and keeps alignment.

    Calling ``fit`` proves the arithmetic; only a real window proves the
    binding. ``update()`` because Tk delivers <Configure> through the event
    loop, which ``update_idletasks`` does not run.
    """
    root, screen = make(name, mapped=True)
    root.deiconify()
    root.update_idletasks()
    root.update()
    before = screen.layout.width("title")
    root.geometry("1900x800")
    root.update_idletasks()
    root.update()
    # The fit waits for the edge to stop; a bare after(ms) blocks that long.
    root.after(FIT_DELAY_MS + 100)
    root.update()
    root.update_idletasks()
    assert screen.layout.width("title") > before, (
        f"{name}: a 500px wider window left Title at {before}px")
    header = screen.layout.header_labels
    for frame, cells in _rows(screen.layout)[:3]:
        for key, label, _full, _reserve, delta in cells:
            if key == "title":
                continue
            assert abs(label.winfo_rootx() - header[key].winfo_rootx()) <= 2, (
                f"{name}: {key} cell is not under its heading")


def test_lsrm3_floor_holds_and_shortfall_is_counted(make, caplog):
    """LSR-M3 — below the floors the columns stop, and the shortfall is logged once."""
    _root, screen = make("today")
    layout = screen.layout
    floor = min_column_width(row_char_px())
    with caplog.at_level("INFO", logger="src.getmoredone.screens.item_list_columns"):
        over = layout.fit(300)
        layout.fit(310)
    assert over > 0
    assert layout.width("title") == TITLE_MIN_PX
    for key in STRETCH_KEYS[1:]:
        assert layout.width(key) == floor
    assert len([r for r in caplog.records if "narrower" in r.getMessage()]) == 1
    caplog.clear()
    with caplog.at_level("INFO", logger="src.getmoredone.screens.item_list_columns"):
        assert layout.fit(1800) == 0
        layout.fit(300)
    assert len([r for r in caplog.records if "narrower" in r.getMessage()]) == 1


def test_lsrm4_text_follows_width_and_comes_back(make):
    """LSR-M4 — cell text is cut to a narrower column and whole again when wide."""
    _root, screen = make("all_items")
    layout = screen.layout
    title_cells = [c for _f, cells in _rows(layout) for c in cells if c[0] == "title"]
    _key, label, full, _reserve, _delta = title_cells[0]
    layout.fit(600)
    assert label.cget("text").endswith("...")
    assert len(label.cget("text")) < len(full)
    layout.fit(2400)
    assert label.cget("text") == full


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm5_drag_shape_survives_resize(make, name):
    """LSR-M5 — a dragged width is saved for this screen and kept in proportion."""
    _root, screen = make(name)
    resizer = screen.layout.resizer
    screen.layout.fit(1500)
    before = resizer.width("title")
    resizer._on_start(SimpleNamespace(x_root=500), "title")
    resizer._on_drag(SimpleNamespace(x_root=600), "title")
    resizer._on_stop(SimpleNamespace(x_root=600), "title")
    assert resizer.width("title") == before + 100
    stored = getattr(AppSettings.load(), f"{screen.COLUMN_PREFIX}_col_widths")
    assert stored["title"] == before + 100, f"{name} did not save its own shape"

    screen.layout.fit(1500)
    assert resizer.width("title") > before, "the drag's shape was lost on refit"


def test_lsrm5_resize_ignored_mid_drag(make):
    """LSR-M5 — a refit while a divider is held would fight the pointer."""
    _root, screen = make("today")
    resizer = screen.layout.resizer
    resizer._on_start(SimpleNamespace(x_root=500), "title")
    held = {k: resizer.width(k) for k in STRETCH_KEYS}
    count = screen.layout.fit_count
    assert screen.layout.fit(2000) == 0
    assert {k: resizer.width(k) for k in STRETCH_KEYS} == held
    assert screen.layout.fit_count == count
    resizer._on_stop(SimpleNamespace(x_root=500), "title")


def test_lsrm6_events_coalesce_and_no_op_fit_is_silent(make, monkeypatch):
    """LSR-M6 — 20 <Configure> leave one fit pending; an unchanged fit draws nothing.

    One fit over 500 rows measured ~3s (FIT_DELAY_MS), which is why the
    events are coalesced at all; 100 rows prove the same rule without that cost.
    """
    _root, screen = make("all_items", count=100)
    layout = screen.layout
    monkeypatch.setattr(screen.scroll_frame, "winfo_width", lambda: 1500)
    count = layout.fit_count
    for _ in range(20):
        layout._on_configure()
    pending = screen.tk.splitlist(screen.tk.call("after", "info"))
    assert layout._after_id in pending
    ours = [i for i in pending if i == layout._after_id]
    assert len(ours) == 1
    callback = layout._after_id
    screen.after_cancel(callback)
    layout._run_fit()           # what the one remaining timer runs
    assert layout.fit_count == count + 1
    assert layout._after_id is None

    applied = []
    monkeypatch.setattr(layout.resizer, "_apply_all", lambda: applied.append(1))
    layout.fit(1500)
    assert applied == [], "a fit that changed no width redrew every row"


def test_lsrm6_each_event_restarts_the_wait(make, monkeypatch):
    """LSR-M6 — every event cancels the timer before it, so only the last fires."""
    _root, screen = make("today")
    layout = screen.layout
    cancelled = []
    real_cancel = screen.after_cancel
    monkeypatch.setattr(screen, "after_cancel",
                        lambda i: (cancelled.append(i), real_cancel(i)))
    # The build may already have left one fit pending; it is cancelled too.
    already = 1 if layout._after_id is not None else 0
    for _ in range(5):
        layout._on_configure()
    assert len(cancelled) == 4 + already
    assert layout._after_id not in cancelled


@pytest.mark.parametrize("name", ("upcoming", "hierarchical"))
def test_lsrm7_upcoming_and_hierarchical_have_headers(make, name):
    """LSR-M7 — a pinned heading row with a divider on each stretching column."""
    _root, screen = make(name)
    header = screen.column_header
    assert header.master is screen, "the header scrolls with the list"
    texts = {w.cget("text") for w in header.winfo_children()
             if isinstance(w, ctk.CTkLabel)}
    assert {"Title", "SubSegment", "Category", "Who", "Pri", "Due"} <= texts
    dividers = [w for w in header.winfo_children()
                if isinstance(w, ctk.CTkFrame)
                and str(w.cget("cursor")) == "sb_h_double_arrow"]
    assert len(dividers) == len(STRETCH_KEYS)


def test_lsrm8_indent_once_and_columns_align_across_levels(make):
    """LSR-M8 — each level indents 30px inside the title cell, rows start level."""
    _root, screen = make("hierarchical")
    layout = screen.layout
    depths = {}
    for frame, cells in _rows(layout):
        assert int(frame.grid_info()["padx"]) == 5, "a row was indented as a whole"
        _key, label, full, _reserve, delta = cells[0]
        if full.startswith("└─ Level") or full.startswith("Level"):
            depths[full] = (delta, label.grid_info()["padx"])
    by_depth = sorted(depths.values())
    assert [d for d, _pad in by_depth] == [0, 30, 60]
    for delta, padx in by_depth:
        left = int(padx[0] if isinstance(padx, tuple) else str(padx).split()[0])
        assert left == 5 + delta


def test_lsrm9_all_items_header_matches_rows_expanded(make):
    """LSR-M9 — expanded, "Status" sits over the status cell, not the factor chips."""
    _root, screen = make("all_items", expanded=True)
    assert screen.column_header.master is screen, "the header scrolls with the list"
    by_col = {}
    for w in screen.column_header.winfo_children():
        if isinstance(w, ctk.CTkLabel):
            by_col[int(w.grid_info()["column"])] = w.cget("text")
    assert by_col[9] == ""
    assert by_col[10] == "Status"
    assert by_col[11] == "Actions"
    frame, _cells = _rows(screen.layout)[0]
    status = [w for w in frame.winfo_children()
              if isinstance(w, ctk.CTkLabel) and w.cget("text") == "open"]
    assert [int(w.grid_info()["column"]) for w in status] == [10]


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm10_search_gives_up_width_before_buttons(make, name, mapped_windows):
    """LSR-M10 (D7) — a toolbar 60px short of its width narrows the search
    entry, and every button still ends inside the toolbar."""
    root, screen = make(name, mapped=True)
    root.deiconify()
    root.update()
    toolbar = screen.search_entry.master
    entry_before = screen.search_entry.winfo_width()
    short_by = toolbar.winfo_width() - toolbar.winfo_reqwidth() + 60
    root.geometry(f"{root.winfo_width() - short_by}x800")
    root.update()
    root.update_idletasks()
    entry_after = screen.search_entry.winfo_width()
    assert SEARCH_MIN_PX <= entry_after < entry_before, (
        f"{name}: search stayed {entry_after}px (was {entry_before}px)")
    right_edge = toolbar.winfo_rootx() + toolbar.winfo_width()
    for widget in toolbar.winfo_children():
        if widget.winfo_manager() != "grid":
            continue
        end = widget.winfo_rootx() + widget.winfo_width()
        assert end <= right_edge, (
            f"{name}: {widget.winfo_class()} ends {end - right_edge}px past the toolbar")


# The controls right of each toolbar's spacer: what moves to a second row.
WRAPPED = {"today": 2, "upcoming": 4, "all_items": 2, "hierarchical": 3}


def _placements(toolbar, wrap):
    return {w: (str(w.grid_info()["in"]), int(w.grid_info()["row"]),
                int(w.grid_info()["column"]))
            for w in toolbar.winfo_children()
            if w is not wrap.frame and w.grid_info()}


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm10_toolbar_wraps_its_right_hand_group(make, name):
    """LSR-M10 (A) — narrower than one row needs, the controls right of the
    spacer move to a second row; wide again, they go back where they were."""
    _root, screen = make(name)
    toolbar = screen.search_entry.master
    wrap = screen.toolbar_wrap
    before = _placements(toolbar, wrap)
    wrap.fit(wrap.one_row_px() - 1)
    moved = [w for w, (master, _r, _c) in _placements(toolbar, wrap).items()
             if master != str(toolbar)]
    assert len(moved) == WRAPPED[name]
    assert all(before[w][2] > wrap.spacer_col for w in moved)
    assert int(wrap.frame.grid_info()["row"]) == 1
    wrap.fit(wrap.one_row_px())
    assert _placements(toolbar, wrap) == before
    assert not wrap.frame.grid_info(), "the empty second row is still gridded"


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm10_narrow_window_wraps_and_nothing_clips(make, name, mapped_windows):
    """LSR-M10 (A) — on a real window 40px short of one row, a second row
    appears and every control ends inside the toolbar; wide again, one row."""
    root, screen = make(name, mapped=True)
    root.deiconify()
    root.update()
    toolbar = screen.search_entry.master
    wrap = screen.toolbar_wrap
    wide = root.winfo_width()
    short_by = toolbar.winfo_width() - wrap.one_row_px() + 40
    root.geometry(f"{wide - short_by}x800")
    root.update()
    root.update_idletasks()
    first_row_y = screen.search_entry.winfo_rooty()
    right_edge = toolbar.winfo_rootx() + toolbar.winfo_width()
    controls = list(_placements(toolbar, wrap))
    assert any(w.winfo_rooty() > first_row_y + screen.search_entry.winfo_height()
               for w in controls), f"{name}: nothing moved to a second row"
    for widget in controls:
        end = widget.winfo_rootx() + widget.winfo_width()
        assert end <= right_edge, (
            f"{name}: {widget.winfo_class()} ends {end - right_edge}px past the toolbar")
    root.geometry(f"{wide}x800")
    root.update()
    root.update_idletasks()
    assert not wrap.frame.grid_info(), f"{name}: still two rows when wide"


TOOLBAR_TEXTS = {
    "today": {"Today's Items", "Search", "Top 3", "+ New Item", "Refresh"},
    "upcoming": {"Upcoming Items", "Search", "Next", "days", "Who:", "+ New Item"},
    "all_items": {"All Items", "Search", "Status:", "Who:", "+ New Item"},
    "hierarchical": {"Hierarchical View", "Search", "Status:", "+ New Item"},
}


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm11_controls_preserved(make, name):
    """LSR-M11 — every toolbar control, and each row's own controls, are still there."""
    _root, screen = make(name)
    toolbar = screen.winfo_children()[0]
    texts = {w.cget("text") for w in toolbar.winfo_children()
             if isinstance(w, (ctk.CTkLabel, ctk.CTkButton))}
    assert TOOLBAR_TEXTS[name] <= texts
    assert screen.search_entry.winfo_exists()
    if name != "hierarchical":
        assert screen.expand_collapse_btn.winfo_exists()
    frame, _cells = _rows(screen.layout)[0]
    children = []
    stack = [frame]
    while stack:
        w = stack.pop()
        children.append(w)
        stack.extend(w.winfo_children())
    buttons = {w.cget("text") for w in children if isinstance(w, ctk.CTkButton)}
    if name != "hierarchical":
        assert "⏱ Timer" in buttons
        assert any(isinstance(w, ctk.CTkCheckBox) for w in children)
