"""LRP — one set of resize principles across every listing of action items.

Purpose: LRP-M1..M11 — the wrapped toolbar row is left-justified, the Project
         Board's right panel loses six buttons, all seven listings share one
         floor, one maximum and one default per column kind, and the value
         filters resize with their toolbar.
Spec:    docs/unused-docs/implementation_plan_2026-11-16_list_resize_principles.md
Tests:   this file

Withdrawn windows throughout: every assertion here reads grid options,
requested widths or ``cget``, none of which needs a mapped window, so the
``mapped_windows`` count in test_ci_contract.py is unchanged.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.getmoredone import theme
from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, ProjectBoard
from src.getmoredone.screens.item_list_columns import (
    COLUMN_DEFAULT_PX,
    FILTER_MAX_FACTOR,
    FILTER_MIN_PX,
    STRETCH_MAX_PX,
    TITLE_MAX_PX,
    UNSHARED_KEYS,
    column_default_px,
    list_floor_px,
)

# The buttons the user asked to be taken off the Project Board's right panel.
REMOVED_BUTTONS = (
    "Create Action Item",
    "Link Action Item",
    "Edit Project",
    "Create Note",
    "Link Note",
    "Open Notes",
)

LISTINGS = ("today", "upcoming", "all_items", "hierarchical", "completed",
            "project_items", "drag_schedule")

# LRP-M10: how many value filters each listing's toolbar hands to ToolbarWrap.
# Every listing is named, the two with none included, so a filter added to a
# toolbar and not wired here is a failure rather than a silent omission.
FILTER_COUNT = {
    "today": 0,
    "upcoming": 1,        # Who
    "all_items": 2,       # Status, Who
    "hierarchical": 1,    # Status
    "completed": 1,       # Who
    "project_items": 0,
    "drag_schedule": 4,   # Who, Segment, SubSegment, Project
}
FILTERED = tuple(name for name, count in FILTER_COUNT.items() if count)


def _app():
    app = MagicMock()
    app.vps_manager.get_segment_colors_by_id.return_value = {}
    app.vps_manager.get_segment_color_map.return_value = {}
    return app


def _root():
    root = ctk.CTk()
    root.withdraw()
    root.geometry("1400x800")
    return root


def _seed(db):
    """Two plain items plus a two-level pair, so every listing renders rows."""
    today = date.today().isoformat()
    parent = None
    for n in range(2):
        db.create_action_item(ActionItem(
            who="Self", title=f"Write the quarterly summary {n}",
            start_date=today, due_date=today, importance=3, urgency=3,
            size=3, value=3))
    for depth in range(2):
        parent = db.create_action_item(ActionItem(
            who="Self", title=f"Level {depth}", start_date=today,
            due_date=today, parent_id=parent))


def _listing_class(name):
    """The screen class for a listing name, or an error.

    Raising on an unknown name rather than falling through to a default:
    the first version of this returned HierarchicalScreen for anything it did
    not recognise, so the "completed" parametrisation silently built the wrong
    screen and the guards passed over a Completed column nothing shared.
    """
    if name == "today":
        from src.getmoredone.screens.today import TodayScreen
        return TodayScreen
    if name == "upcoming":
        from src.getmoredone.screens.upcoming import UpcomingScreen
        return UpcomingScreen
    if name == "all_items":
        from src.getmoredone.screens.all_items import AllItemsScreen
        return AllItemsScreen
    if name == "hierarchical":
        from src.getmoredone.screens.hierarchical import HierarchicalScreen
        return HierarchicalScreen
    if name == "completed":
        from src.getmoredone.screens.completed import CompletedScreen
        return CompletedScreen
    raise AssertionError(f"no screen class for listing {name!r}")


@pytest.fixture
def completed_screen(tmp_path):
    """A real CompletedScreen, for its toolbar wrap."""
    from src.getmoredone.screens.completed import CompletedScreen

    built = []

    def _make():
        root = _root()
        db = DatabaseManager(str(tmp_path / "completed.db"))
        item_id = db.create_action_item(ActionItem(
            who="Self", title="Write the quarterly summary",
            importance=3, urgency=3, size=3, value=3))
        db.complete_action_item(item_id)
        screen = CompletedScreen(root, db, _app())
        screen.pack(fill="both", expand=True)
        screen.update_idletasks()
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
    """A real ProjectBoardsScreen with a board selected, items optional."""
    from src.getmoredone.screens.project_boards import ProjectBoardsScreen

    built = []

    def _make(items=2):
        root = _root()
        db = DatabaseManager(str(tmp_path / "projects.db"))
        board_id = db.create_project_board(ProjectBoard(title="Board One"))
        for n in range(items):
            item_id = db.create_action_item(ActionItem(
                who="Self", title=f"Linked task {n}", status="open",
                start_date="2026-11-15", due_date="2026-11-20"))
            db.link_action_item_to_project_board(board_id, item_id)
        screen = ProjectBoardsScreen(root, db, SimpleNamespace(vps_manager=None))
        screen.pack(fill="both", expand=True)
        screen.selected_board_id = board_id
        screen.refresh()
        screen.update_idletasks()
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
def listing(tmp_path):
    """One of the seven listings of action items, with its ColumnResizer.

    Each is built for real on a withdrawn root with its own database, because
    the point of LRP-M8 is what a screen's own construction produces -- not
    what the shared helpers return when called directly.
    """
    built = []

    def _make(name):
        root = _root()
        db = DatabaseManager(str(tmp_path / f"{name}.db"))
        _seed(db)
        vps = None
        if name == "drag_schedule":
            from src.getmoredone.screens.drag_schedule import DragScheduleScreen
            from src.getmoredone.vps_manager import VPSManager
            vps = VPSManager(str(tmp_path / f"{name}.db"))
            screen = DragScheduleScreen(root, db, SimpleNamespace(vps_manager=vps))
            resizer = screen.resizer
        elif name == "project_items":
            from src.getmoredone.screens.project_boards import ProjectBoardsScreen
            board_id = db.create_project_board(ProjectBoard(title="Board One"))
            for n in range(2):
                item_id = db.create_action_item(ActionItem(
                    who="Self", title=f"Linked task {n}", status="open",
                    start_date="2026-11-15", due_date="2026-11-20"))
                db.link_action_item_to_project_board(board_id, item_id)
            screen = ProjectBoardsScreen(root, db,
                                         SimpleNamespace(vps_manager=None))
            screen.selected_board_id = board_id
            resizer = screen.items_layout.resizer
        else:
            screen = _listing_class(name)(root, db, _app())
            resizer = screen.layout.resizer
        screen.pack(fill="both", expand=True)
        if name == "project_items":
            screen.refresh()
        screen.update_idletasks()
        built.append((root, db, vps))
        return screen, resizer

    yield _make
    for root, db, vps in built:
        try:
            root.destroy()
        except Exception:
            pass
        if vps is not None:
            vps.close()
        db.close()


def _row_zero_toolbar(frame):
    """The frame gridded at row 0 of the right panel: its button toolbar."""
    for child in frame.winfo_children():
        info = child.grid_info()
        if info and int(info["row"]) == 0:
            return child
    raise AssertionError("no widget at row 0 of the items frame")


def _button_texts(toolbar):
    return [child.cget("text") for child in toolbar.winfo_children()
            if isinstance(child, ctk.CTkButton)]


def _label_texts(frame):
    return [child.cget("text") for child in frame.winfo_children()
            if isinstance(child, ctk.CTkLabel)]


# --------------------------------------------------------------------- LRP-M1
def test_lrpm1_the_wrapped_row_is_left_justified(completed_screen):
    """LRP-M1 — the wrap frame pins its left edge, not its right.

    ``sticky`` is what decides which way an over-wide second row overflows,
    and it is Tk's own record of the layout, not the source text.
    """
    screen = completed_screen()
    wrap = screen.toolbar_wrap
    wrap.fit(wrap.min_one_row_px() - 1)
    assert wrap.wrapped
    assert wrap.frame.grid_info()["sticky"] == "w"


def test_lrpm1_the_wrapped_controls_read_left_to_right(completed_screen):
    """LRP-M1 — inside the frame the controls keep their one-row order."""
    screen = completed_screen()
    wrap = screen.toolbar_wrap
    one_row_order = [int(info["column"]) for _w, info in wrap._wrap_candidates()]
    wrap.fit(wrap.min_one_row_px() - 1)
    wrapped = [(w, int(w.grid_info()["column"])) for w, _i in wrap._moved]
    assert [col for _w, col in wrapped] == list(range(len(wrapped)))
    assert one_row_order == sorted(one_row_order)


# --------------------------------------------------------------------- LRP-M2
def test_lrpm2_six_buttons_are_gone_from_the_right_panel(projects_screen):
    """LRP-M2 — the right panel's toolbar holds Bulk Edit and nothing removed."""
    screen = projects_screen()
    texts = _button_texts(_row_zero_toolbar(screen.items_frame))
    assert "Bulk Edit" in texts
    assert [t for t in texts if t in REMOVED_BUTTONS] == []


def test_lrpm2_the_removed_buttons_have_no_attributes_left(projects_screen):
    """LRP-M2 — nothing still holds a reference to a button that is gone."""
    screen = projects_screen()
    for name in ("btn_create_action", "btn_link_action", "btn_edit_project",
                 "btn_create_note", "btn_link_note", "btn_open_notes"):
        assert not hasattr(screen, name), name


# --------------------------------------------------------------------- LRP-M3
def test_lrpm3_the_empty_state_names_no_removed_button(projects_screen):
    """LRP-M3 — an empty board points at a route that still exists."""
    screen = projects_screen(items=0)
    texts = " ".join(_label_texts(screen.items_frame))
    assert "action item" in texts.lower()
    for removed in REMOVED_BUTTONS:
        assert removed not in texts, removed


def test_lrpm3_the_notes_empty_state_names_no_removed_button(projects_screen):
    """LRP-M3 — the notes section's empty state does the same."""
    screen = projects_screen(items=0)
    texts = " ".join(_label_texts(screen.notes_links_frame))
    for removed in REMOVED_BUTTONS:
        assert removed not in texts, removed


# ------------------------------------------------------------- LRP-M4/M5/M6/M8
@pytest.mark.parametrize("name", LISTINGS)
def test_lrpm8_every_listing_shares_the_floor_and_the_maxima(listing, name):
    """LRP-M4/M5/M8 — one floor and one maximum per column kind, everywhere."""
    _screen, resizer = listing(name)
    floor = list_floor_px()
    for key, spec in resizer.specs.items():
        if not spec.resizable:
            continue
        assert spec.min_width == floor, (name, key)
        want = TITLE_MAX_PX if key == "title" else STRETCH_MAX_PX
        assert spec.max_width == want, (name, key)


@pytest.mark.parametrize("name", LISTINGS)
def test_lrpm6_every_listing_opens_at_the_shared_defaults(listing, name):
    """LRP-M6/M8 — a column kind has one default width across all seven.

    A key outside ``COLUMN_DEFAULT_PX`` is a column that is deliberately not
    shared, and the only one is the priority cell. Asserting the set exactly,
    rather than skipping unknown keys, is what stops a new listing inventing
    a column nobody chose a width for.
    """
    _screen, resizer = listing(name)
    for key, spec in resizer.specs.items():
        if key in COLUMN_DEFAULT_PX:
            assert spec.default_width == column_default_px(key), (name, key)
        else:
            assert key in UNSHARED_KEYS, (name, key)


def test_lrpm4_the_floor_follows_the_row_font(listing, monkeypatch):
    """LRP-M4 — a bigger row font gives a wider floor, on the Scheduler too.

    The Scheduler's own floor was ``6 * CHAR_PX``, fixed at the default font,
    so its columns alone did not widen with the setting.
    """
    small = list_floor_px()
    monkeypatch.setattr(theme, "LIST_ROW_FONT_SIZE", 2 * theme.LIST_ROW_FONT_SIZE)
    assert list_floor_px() > small
    _screen, resizer = listing("drag_schedule")
    assert resizer.specs["title"].min_width == list_floor_px()


def test_lrpm6_the_legacy_title_fallback_matches_the_table():
    """LRP-M6 — the legacy scalars agree with COLUMN_DEFAULT_PX.

    ``ColumnResizer._load_stored`` prefers ``<prefix>_title_col_width`` over a
    spec's default, so a scalar that disagrees silently overrides the table --
    which is exactly what 220 here did to the Scheduler until 2026-11-16.
    app_settings cannot import from screens, so this is the link.
    """
    want = column_default_px("title")
    assert AppSettings.drag_schedule_title_col_width == want
    assert AppSettings.today_title_col_width == want


# --------------------------------------------------------------------- LRP-M9
@pytest.mark.parametrize("name", ("today", "completed", "drag_schedule"))
def test_lrpm9_every_column_moves_in_proportion_to_title(listing, name):
    """LRP-M9 — each column's change is a fixed ratio of Title's change.

    The rule the user asked for: "All columns ... resize in proportion to the
    size change of the Title Field, until they hit a minimum size." Checked in
    a band where nothing is at its floor or its ceiling, so the shares are the
    weights and nothing is pinned.
    """
    _screen, resizer = listing(name)
    resizer.fit_to_width(900)
    narrow = {k: resizer.width(k) for k in resizer.order}
    resizer.fit_to_width(1600)
    wide = {k: resizer.width(k) for k in resizer.order}

    title_delta = wide["title"] - narrow["title"]
    assert title_delta > 0
    weights = resizer._weights
    for key in resizer.order:
        if not resizer.specs[key].resizable:
            continue
        delta = wide[key] - narrow[key]
        assert delta > 0, key
        want = weights[key] / weights["title"]
        assert abs(delta / title_delta - want) < 0.05, (key, delta, title_delta)


# -------------------------------------------------------------------- LRP-M10
@pytest.mark.parametrize("name", LISTINGS)
def test_lrpm10_every_value_filter_is_wired(listing, name):
    """LRP-M10 — each toolbar hands its value filters to the wrap, and only those.

    Read off the wrap rather than the screen: a combo the screen holds but
    does not pass through resizes like a label, which is the bug this guards.
    """
    screen, _resizer = listing(name)
    wrap = screen.toolbar_wrap
    assert len(wrap.filters) == FILTER_COUNT[name]
    for widget, default in wrap.filters:
        assert isinstance(widget, ctk.CTkComboBox), widget
        assert default >= FILTER_MIN_PX, (widget, default)
        assert int(widget.grid_info()["row"]) == wrap.control_row


@pytest.mark.parametrize("name", FILTERED)
def test_lrpm10_a_filter_never_goes_below_the_minimum(listing, name):
    """LRP-M10 — squeezed, every filter sits at FILTER_MIN_PX, none under it."""
    screen, _resizer = listing(name)
    wrap = screen.toolbar_wrap
    wrap.fit(wrap.min_one_row_px() - 400)
    assert [widget.cget("width") for widget, _d in wrap.filters] == \
        [FILTER_MIN_PX] * FILTER_COUNT[name]


@pytest.mark.parametrize("name", FILTERED)
def test_lrpm10_a_filter_stops_at_its_maximum(listing, name):
    """LRP-M10 — given far more room than it can use, a filter pins at its cap.

    Without a cap one wide window turns a Who combo into a banner; with one,
    the slack past it goes to the spacer, as it did before the filters flexed.
    """
    screen, _resizer = listing(name)
    wrap = screen.toolbar_wrap
    wrap.fit(wrap.one_row_px() + 4000)
    for widget, default in wrap.filters:
        assert widget.cget("width") == FILTER_MAX_FACTOR * default, widget


@pytest.mark.parametrize("name", ("all_items", "drag_schedule"))
def test_lrpm10_a_filter_takes_its_share_in_proportion_to_its_default(listing,
                                                                     name):
    """LRP-M10 — the columns' rule, applied to the filters.

    Over a width change each filter's change holds a fixed ratio to the first
    filter's, and that ratio is the ratio of their default widths -- so a
    Project filter stays wider than a Who filter at every width. Measured in
    a band above the minimum and below the maximum, where nothing is pinned.
    """
    screen, _resizer = listing(name)
    wrap = screen.toolbar_wrap
    fixed = wrap.min_one_row_px() - FILTER_MIN_PX * len(wrap.filters)
    total = sum(default for _widget, default in wrap.filters)

    wrap.fit(fixed + total)
    narrow = [widget.cget("width") for widget, _d in wrap.filters]
    wrap.fit(fixed + 3 * total // 2)
    wide = [widget.cget("width") for widget, _d in wrap.filters]

    anchor_default = wrap.filters[0][1]
    anchor = wide[0] - narrow[0]
    assert anchor > 0, (narrow, wide)
    for (widget, default), before, after in zip(wrap.filters, narrow, wide):
        assert after > before, widget
        want = default / anchor_default
        assert abs((after - before) / anchor - want) < 0.05, (
            widget, default, before, after)


# -------------------------------------------------------------------- LRP-M11
@pytest.mark.parametrize("name", FILTERED)
def test_lrpm11_the_row_wraps_only_below_the_minimum_fit(listing, name):
    """LRP-M11 — a filter gives up width before the buttons leave the row.

    The threshold is one row with every filter at its minimum. Between that
    and one row at their defaults the toolbar stays on one row and the
    filters absorb the shortfall; one pixel under it, the row wraps.
    """
    screen, _resizer = listing(name)
    wrap = screen.toolbar_wrap
    assert wrap.min_one_row_px() < wrap.one_row_px()

    wrap.fit(wrap.one_row_px())
    assert not wrap.wrapped
    full = [widget.cget("width") for widget, _d in wrap.filters]
    assert full == [default for _w, default in wrap.filters]

    wrap.fit(wrap.min_one_row_px())
    assert not wrap.wrapped, "wrapped where the minimums still fit"
    assert all(now <= was for now, was in zip(
        [widget.cget("width") for widget, _d in wrap.filters], full))
    assert [widget.cget("width") for widget, _d in wrap.filters] != full, \
        "nothing gave up width on the way down to the threshold"

    wrap.fit(wrap.min_one_row_px() - 1)
    assert wrap.wrapped


@pytest.mark.parametrize("name", FILTERED)
def test_lrpm11_the_threshold_does_not_move_as_the_filters_resize(listing, name):
    """LRP-M11 — the wrap threshold is the same number at every width.

    It was not, when ``one_row_px()`` counted the filters at the width they
    happened to be drawn at: fitting a toolbar resized the filters, which
    moved the threshold, which changed the next fit's answer. All Items read
    997 px, then 916, then 922 on 2026-11-16, and a toolbar that had wrapped
    never unwrapped.
    """
    screen, _resizer = listing(name)
    wrap = screen.toolbar_wrap
    threshold, full = wrap.min_one_row_px(), wrap.one_row_px()
    for width in (full + 2000, threshold - 300, threshold, full):
        wrap.fit(width)
        assert wrap.min_one_row_px() == threshold, width
        assert wrap.one_row_px() == full, width
