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
from src.getmoredone.screens.item_list_columns import (
    FIT_DELAY_MS,
    SEARCH_MIN_PX,
    LIST_MIN_CHARS,
    STRETCH_KEYS,
    row_char_px,
)

SCREENS = ("today", "upcoming", "all_items", "hierarchical")
EXPANDABLE = ("today", "upcoming", "all_items")

# LSR2: every text column resizes (plan 2026-11-14, D1/D2).
RESIZABLE = {
    "today": STRETCH_KEYS + ("start", "due", "pri", "time"),
    "upcoming": STRETCH_KEYS + ("start", "due", "pri", "time"),
    "all_items": STRETCH_KEYS + ("start", "due", "pri", "time", "status"),
    "hierarchical": STRETCH_KEYS + ("pri", "due", "subitems"),
}


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
    cols = [layout.grid_col(k) for k in layout.keys]
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
    for key in layout.keys:
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
    narrow = {k: layout.width(k) for k in layout.keys}
    layout.fit(1700)
    wide = {k: layout.width(k) for k in layout.keys}

    for key in layout.keys:
        assert wide[key] > narrow[key], f"{name}: {key} did not widen"
    assert sum(wide.values()) == 1700 - layout.reserved_px()
    # Proportional: Title keeps its share to within a pixel per column.
    share = narrow["title"] / sum(narrow.values())
    assert abs(wide["title"] - share * sum(wide.values())) <= len(layout.keys)
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
    floor = LIST_MIN_CHARS * row_char_px()
    with caplog.at_level("INFO", logger="src.getmoredone.screens.item_list_columns"):
        over = layout.fit(300)
        layout.fit(310)
    assert over > 0
    for key in layout.keys:
        assert layout.width(key) == floor, key
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
    held = {k: resizer.width(k) for k in screen.layout.keys}
    count = screen.layout.fit_count
    assert screen.layout.fit(2000) == 0
    assert {k: resizer.width(k) for k in screen.layout.keys} == held
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
    assert len(dividers) == len(screen.layout.keys)


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


def _pending(root, after_id):
    return after_id is not None and after_id in root.tk.splitlist(
        root.tk.call("after", "info"))


def _row_px(layout):
    return sum(layout.width(k) for k in layout.keys) + layout.reserved_px()


@pytest.mark.parametrize("name", EXPANDABLE)
def test_lsrm2_expand_and_collapse_refit(make, name, monkeypatch):
    """LSR-M2c — Expand and Collapse change the fixed columns without a
    <Configure>; the list still refits to its width."""
    root, screen = make(name)
    layout = screen.layout
    monkeypatch.setattr(layout._measured, "winfo_width", lambda: 1600)
    layout._run_fit()
    for _toggle in range(2):
        screen.toggle_columns()
        assert _pending(root, layout._after_id), f"{name}: toggling queued no refit"
        layout._run_fit()
        assert _row_px(layout) <= 1600, f"{name}: rows overflow after toggling"


def test_lsrm5_releasing_a_divider_refits(make, monkeypatch):
    """LSR-M5 — a fit skipped during a drag runs once the divider is let go."""
    root, screen = make("today")
    layout = screen.layout
    resizer = layout.resizer
    monkeypatch.setattr(layout._measured, "winfo_width", lambda: 1500)
    layout._run_fit()
    resizer._on_start(SimpleNamespace(x_root=500), "title")
    resizer._on_drag(SimpleNamespace(x_root=650), "title")
    resizer._on_stop(SimpleNamespace(x_root=650), "title")
    assert _pending(root, layout._after_id), "releasing the divider queued no refit"
    layout._run_fit()
    assert _row_px(layout) <= 1500


def test_lsrm2_fit_uses_unscaled_width(make, monkeypatch):
    """LSR-M2d — winfo_width is in screen pixels; at 150% scaling the fit
    shares out the width in CTk's unscaled units."""
    _root, screen = make("all_items")
    layout = screen.layout
    monkeypatch.setattr(layout._measured, "winfo_width", lambda: 2400)
    monkeypatch.setattr(screen, "_get_widget_scaling", lambda: 1.5)
    layout._run_fit()
    assert _row_px(layout) == 1600


@pytest.mark.parametrize("name", SCREENS)
def test_lsrm10_toolbar_configure_is_bound_on_the_toolbar(make, name):
    """LSR-M10 — the wrap's <Configure> handler is in the toolbar's own Tk
    binding, where a resize of the toolbar reaches it.

    CTkFrame.bind binds the frame's inner canvas instead, whose events name
    the canvas. A withdrawn window gets no generated <Configure>, so this
    reads Tk's binding table; the mapped test below drives a real resize.
    """
    _root, screen = make(name)
    toolbar = screen.toolbar_wrap.toolbar
    script = toolbar.tk.call("bind", str(toolbar), "<Configure>")
    # tkinter names a bound method's Tcl command <id><method name>.
    handlers = [line for line in str(script).splitlines() if "_on_configure " in line]
    assert len(handlers) == 1, f"{name}: toolbar's own <Configure> binding: {script!r}"

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


# --------------------------------------------------------------------- LSR2
# Plan: docs/unused-docs/implementation_plan_2026-11-14_all_columns_resize.md

def _floor():
    # Stated, not read from LIST_MIN_CHARS: the user asked for 6 characters.
    return 6 * row_char_px()


@pytest.mark.parametrize("name", SCREENS)
def test_lsr2m1_every_text_column_follows_the_width(make, name):
    """LSR2-M1 — every text column, not only the first four, follows the list."""
    _root, screen = make(name)
    layout = screen.layout
    assert layout.keys == RESIZABLE[name]
    layout.fit(1200)
    narrow = {k: layout.width(k) for k in layout.keys}
    layout.fit(1800)
    for key in layout.keys:
        assert layout.width(key) > narrow[key], f"{name}: {key} did not widen"
    for _frame, cells in _rows(layout)[:2]:
        keys = {key for key, *_ in cells}
        assert keys == set(layout.keys), f"{name}: row cells {keys} lack a column"


@pytest.mark.parametrize("name", SCREENS)
def test_lsr2m2_floor_is_six_characters(make, name):
    """LSR2-M2 — no resizable column goes below 6 characters, at any width."""
    _root, screen = make(name)
    layout = screen.layout
    for width in (2000, 1100, 700, 300, 1):
        layout.fit(width)
        for key in layout.keys:
            assert layout.width(key) >= _floor(), f"{name}@{width}: {key}"
    assert {layout.width(k) for k in layout.keys} == {_floor()}


@pytest.mark.parametrize("name,expanded", _params())
def test_lsr2m3_controls_keep_their_size(make, name, expanded):
    """LSR2-M3 — the checkbox, Timer/Actions and factor chips do not resize (D2)."""
    _root, screen = make(name, expanded=expanded)
    layout = screen.layout
    controls = {c.grid_col: c.column_px for c in layout.lead + layout.fixed}
    assert set(controls).isdisjoint(layout.grid_col(k) for k in layout.keys)
    for width in (1800, 900):
        layout.fit(width)
        for frame, _cells in _rows(layout):
            for col, px in controls.items():
                assert frame.grid_columnconfigure(col)["minsize"] == px


@pytest.mark.parametrize("name", SCREENS)
def test_lsr2m4_every_resizable_column_has_a_divider(make, name):
    """LSR2-M4 — a divider per resizable column; a drag moves only its column."""
    _root, screen = make(name)
    layout = screen.layout
    dividers = [w for w in screen.column_header.winfo_children()
                if isinstance(w, ctk.CTkFrame)
                and str(w.cget("cursor")) == "sb_h_double_arrow"]
    assert sorted(int(d.grid_info()["column"]) for d in dividers) == sorted(
        layout.grid_col(k) for k in layout.keys)
    layout.fit(1500)
    key = "due"
    before = {k: layout.width(k) for k in layout.keys}
    resizer = layout.resizer
    resizer._on_start(SimpleNamespace(x_root=500), key)
    resizer._on_drag(SimpleNamespace(x_root=540), key)
    after = {k: layout.width(k) for k in layout.keys}
    resizer._on_stop(SimpleNamespace(x_root=540), key)
    assert after[key] == before[key] + 40
    assert {k: v for k, v in after.items() if k != key} == {
        k: v for k, v in before.items() if k != key}


@pytest.mark.parametrize("name", SCREENS)
def test_lsr2m5_shape_survives_a_narrow_window(make, name):
    """LSR2-M5 — down to the floors in steps and back: the shape returns (D6).

    The steps matter: columns reach their floors one at a time on the way
    down, and a fit that wrote those floors into the weights lost the shape
    before the whole row was floored (measured 2026-11-14 on All Items).
    """
    _root, screen = make(name)
    layout = screen.layout
    layout.fit(1600)
    before = {k: layout.width(k) for k in layout.keys}
    for width in range(1500, 0, -100):
        layout.fit(width)
    layout.fit(1600)
    assert {k: layout.width(k) for k in layout.keys} == before


def test_lsr2m7_saved_lsr_widths_carry_over(make, monkeypatch):
    """LSR2-M7 — widths saved before LSR2 load as weights; new columns use defaults."""
    stored = {"title": 400, "subsegment": 100, "category": 100, "who": 100}
    real_load = AppSettings.load

    def _load(*args, **kwargs):
        settings = real_load(*args, **kwargs)
        settings.all_items_col_widths = dict(stored)
        return settings

    monkeypatch.setattr(AppSettings, "load", _load)
    _root, screen = make("all_items")
    layout = screen.layout
    assert {k: layout.width(k) for k in STRETCH_KEYS} == stored
    assert layout.width("start") == 60
    layout.fit(1800)
    assert abs(layout.width("title") / layout.width("subsegment") - 4) < 0.1


@pytest.mark.parametrize("name", ("today", "upcoming"))
def test_lsr2m8_date_cells_have_no_prefix(make, name):
    """LSR2-M8 — Start and Due read "11/14", not "S:11/14" (D5)."""
    _root, screen = make(name)
    want = date.today().strftime("%m/%d")
    cells = [c for _f, cells in _rows(screen.layout) for c in cells
             if c[0] in ("start", "due")]
    assert cells, f"{name}: no date cells registered"
    for key, label, full, _reserve, _delta in cells:
        assert full == want, f"{name}: {key} full text {full!r}"
        assert label.cget("text") == want


# ------------------------------------------------------------ LSR2 sweep fixes

def _partly_floored(layout):
    """A list width at which some resizable columns are at the floor and some not."""
    for width in range(1500, 0, -10):
        layout.fit(width)
        at_floor = [k for k in layout.keys if layout.width(k) == _floor()]
        if at_floor and len(at_floor) < len(layout.keys):
            return width
    raise AssertionError("no width leaves the list partly floored")


@pytest.mark.parametrize("name", ("today", "all_items"))
def test_lsr2m4b_a_drag_changes_only_its_own_weight(make, name):
    """LSR2-M4 — a click changes nothing; a drag changes only its column's weight.

    Found by the csdp sweep (2026-11-14): a release wrote every drawn width
    into the weights, so columns held at the floor took the floor as their
    shape, and that was saved.
    """
    _root, screen = make(name)
    layout = screen.layout
    resizer = layout.resizer
    layout.fit(1600)
    wide = {k: layout.width(k) for k in layout.keys}
    _partly_floored(layout)
    weights = dict(resizer._weights)

    resizer._on_start(SimpleNamespace(x_root=500), "title")
    resizer._on_stop(SimpleNamespace(x_root=500), "title")
    assert resizer._weights == weights, "a click with no motion moved the weights"
    layout.fit(1600)
    assert {k: layout.width(k) for k in layout.keys} == wide

    _partly_floored(layout)
    resizer._on_start(SimpleNamespace(x_root=500), "title")
    resizer._on_drag(SimpleNamespace(x_root=540), "title")
    resizer._on_stop(SimpleNamespace(x_root=540), "title")
    assert resizer._weights["title"] > weights["title"]
    assert {k: v for k, v in resizer._weights.items() if k != "title"} == {
        k: v for k, v in weights.items() if k != "title"}


@pytest.mark.parametrize("name", SCREENS)
def test_lsr2_headings_are_cut_to_their_column(make, name):
    """A heading wider than its column is cut with "...", and comes back whole.

    Found by the csdp sweep (2026-11-14): a label grows to fit its text, so
    an uncut heading pushed every heading after it off its rows.
    """
    _root, screen = make(name)
    layout = screen.layout
    labels = screen.layout.header_labels
    layout.fit(1)
    # 54px at 8px a character (bold 12) leaves 6 characters.
    for key in layout.keys:
        assert len(labels[key].cget("text")) <= 6, f"{name}: {key}"
    if name == "all_items":
        assert labels["pri"].cget("text") == "Pri..."
        layout.fit(2400)
        assert labels["pri"].cget("text") == "Priority"
    if name == "hierarchical":
        assert labels["subitems"].cget("text") == "Sub..."
        layout.fit(2400)
        assert labels["subitems"].cget("text") == "Sub-items"


def test_lsr2_hierarchical_due_has_no_prefix(make):
    """Hierarchical's Due cell holds the date alone (LSR2 sweep)."""
    _root, screen = make("hierarchical")
    cells = [c for _f, cells in _rows(screen.layout) for c in cells if c[0] == "due"]
    assert cells
    assert {full for _k, _l, full, *_ in cells} == {date.today().isoformat()}
