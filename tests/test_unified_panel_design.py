"""Tests for one panel design across the VSP tabs.

Spec: docs/spec_2026-11-07_unified_panel_design.md

Every test name carries the criterion ID it verifies (UPD-M1 … UPD-M7).

This file opens with the **characterisation** tests (UPD-M4.1). They were
written against the screens as they stood before a line of the consolidation
was removed, and they exist to hold the layout in place while the splitter,
the row drag and the chip table move out into shared modules. A
characterisation test is allowed to be fussy about pixel widths and column
order in a way an ordinary test should not be: that fussiness is the point,
because the refactor's promise is that none of it changes.

Screens are built on a **withdrawn** root, so none of them adds to the mapped
window count that tests/test_ci_contract.py pins at 22.
"""

import ast
import dataclasses
import importlib
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

# Self-contained path bootstrap, for the same reason test_ape_week_actions.py
# carries one: tests/test_ci_contract.py imports every test file with the repo
# root stripped from sys.path, and this file cannot rely on another having put
# it back.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

import customtkinter as ctk  # noqa: E402

from src.getmoredone.app_settings import AppSettings  # noqa: E402
from src.getmoredone.color_contrast import pick_text_color  # noqa: E402
from src.getmoredone.screens import chip_table, row_drag, split_panel  # noqa: E402
from src.getmoredone.screens.annual_vision_segments import (  # noqa: E402
    AnnualVisionSegmentsScreen,
)
from src.getmoredone.screens.ape_assignment import APEAssignmentScreen  # noqa: E402
from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen  # noqa: E402
from src.getmoredone.screens.weekly_items import WeeklyItemsScreen  # noqa: E402
from tests.weekly_tactic_fixtures import (  # noqa: E402
    make_vps,
    make_week_item,
    seed_ape,
    seed_second_ape,
)
from conftest import withdrawn_root  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src" / "getmoredone"


# --------------------------------------------------------------------- helpers

def _ape_row(idx, segment="Purposeful Work", subsegment="Living Systems",
             category="Blog"):
    return {
        "id": f"ape-{idx}",
        "segment_name": segment,
        "subsegment_name": subsegment,
        "category_name": category,
    }


def _fake_vps(left_rows, right_rows):
    """A VPS manager double returning real dicts, not MagicMock attributes.

    The screen passes these straight into the lineage colour helpers, which
    call `.strip()` and `.get()` on what comes back, so a MagicMock would
    sail past the assertions this file makes about rendered text.
    """
    calls = []
    return SimpleNamespace(
        calls=calls,
        get_annual_plan_elements=lambda year: list(left_rows),
        get_annual_plan_elements_for_quarter=lambda year, quarter: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
        assign_ape_to_quarter=lambda *a: calls.append(a) or True,
    )


def _quarter_screen(left_rows=(), right_rows=(), settings=None):
    """APE Quarter Assignment on a withdrawn root, already rendered.

    With `settings`, the screen takes it from the app the way the running app
    hands over its own instance; without one it loads its own, which
    conftest.py's settings isolation points at a temporary file.
    """
    root = withdrawn_root()
    vps = _fake_vps(left_rows, right_rows)
    app = SimpleNamespace(vps_manager=vps)
    if settings is not None:
        app.settings = settings
    screen = APEAssignmentScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _header_frame(scroll_frame):
    """The first child of a rendered list: its header row."""
    children = [c for c in scroll_frame.winfo_children() if c.grid_info()]
    children.sort(key=lambda c: int(c.grid_info()["row"]))
    return children[0]


def _row_frames(scroll_frame):
    """Every rendered row frame below the header, in grid order."""
    children = [c for c in scroll_frame.winfo_children() if c.grid_info()]
    children.sort(key=lambda c: int(c.grid_info()["row"]))
    return children[1:]


def _is_resize_handle(widget) -> bool:
    """A ColumnResizer drag handle, which is not a cell.

    The shared table grids a handle into the same grid column as the header
    label it belongs to, so a reader of the header's children sees two
    widgets per resizable column. `test_updm32` identifies a handle the same
    way, by its cursor.
    """
    try:
        return widget.cget("cursor") == "sb_h_double_arrow"
    except Exception:
        return False


def _cells(frame):
    """[(grid column, class name, text)] for a header or row frame.

    Resize handles are skipped: they sit in a column without being a cell of
    it, and before the shared table there was nothing in a header but cells.
    """
    out = []
    for child in frame.winfo_children():
        info = child.grid_info()
        if not info or _is_resize_handle(child):
            continue
        try:
            text = child.cget("text")
        except Exception:
            text = None
        out.append((int(info["column"]), type(child).__name__, text))
    out.sort(key=lambda cell: cell[0])
    return out


def _bound_sequences(widget) -> tuple:
    """The event sequences bound on a widget.

    A CustomTkinter widget forwards `bind` to an internal canvas, so
    `widget.bind()` with no handler reports nothing while the canvas holds the
    binding. Reading the private attribute is the only way to assert a binding
    exists, and these assertions matter: a drag source that silently stops
    being bound looks exactly like a row that was never draggable.
    """
    canvas = getattr(widget, "_canvas", None)
    return tuple(canvas.bind() or ()) if canvas is not None else tuple(widget.bind() or ())


def _minsizes(frame, columns):
    """The grid minsize of each named column on a frame."""
    return [frame.grid_columnconfigure(col).get("minsize") for col in columns]


def _topmost_at_grid_row(scroll_frame, grid_row):
    """The last frame gridded at `grid_row`, which is the one drawn on top.

    Two widgets gridded into one cell both stay mapped, and the later one is
    what the user sees. Before UPD-M5 this panel really did hold several
    frames per row (see
    ::test_updm57_selecting_a_row_repaints_the_panel_instead_of_stacking_it),
    so reading the first child would read a frame the user cannot see.
    """
    at_row = [c for c in scroll_frame.winfo_children()
              if c.grid_info() and int(c.grid_info()["row"]) == grid_row]
    assert at_row, f"nothing gridded at row {grid_row}"
    return at_row[-1]


def _label_texts(widget) -> list:
    """The text of every CTkLabel at or under a widget, in child order."""
    out = []
    if isinstance(widget, ctk.CTkLabel):
        out.append(widget.cget("text"))
    for child in widget.winfo_children():
        out.extend(_label_texts(child))
    return out


# ------------------------------- UPD-M4.1: APE Quarter Assignment, as it stands

def test_updm41_ape_quarter_layout_is_unchanged():
    """UPD-M4.1 — the body is left | divider | right, and the divider drags.

    Pins the three-column body, the panels either side of it and the three
    bindings that make the middle column a splitter rather than a line. The
    consolidation moves the handlers into screens/split_panel.py; what this
    test describes must survive that move.
    """
    root, screen = _quarter_screen()
    try:
        body = screen.body
        assert int(screen.left_frame.grid_info()["column"]) == 0
        assert int(screen.divider.grid_info()["column"]) == 1
        assert int(screen.right_frame.grid_info()["column"]) == 2

        # The middle column is the splitter's width, not a panel's. UPD-M1
        # moved the number into screens/split_panel.py, which is the whole
        # point of that step; the column it sizes is unchanged.
        assert body.grid_columnconfigure(1).get("minsize") == split_panel.SPLITTER_WIDTH

        bound = set(_bound_sequences(screen.divider))
        assert {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"} <= bound
    finally:
        root.destroy()


def test_updm41_ape_quarter_left_header_columns_are_unchanged():
    """UPD-M4.1 — left header: Pick over the checkbox, then the four names.

    The left panel is the selectable one, so its first cell is the header over
    the checkbox column. Column order is asserted by position, not by set
    membership, because the order is the thing the shared table has to
    reproduce.

    That first heading was `""` until UPD-F3: case (b), the behaviour changed
    intentionally — the on-screen walk asked for a word over the ticks. The
    set and the order are what this test pins and neither moved.
    """
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        header = _header_frame(screen.left_list)
        texts = [text for _col, _cls, text in _cells(header)]
        assert texts == ["Pick", "#", "Segment", "SubSegment", "Category"]
    finally:
        root.destroy()


def test_updm41_ape_quarter_right_header_ends_with_actions():
    """UPD-M4.1 — right header: the four names, then Actions.

    The right panel has no checkbox and does have an Actions column. This is
    the shape the image in the spec shows, and the shape UPD-M5 has to give
    APE Week Assignment's right panel.
    """
    root, screen = _quarter_screen(right_rows=[_ape_row(1)])
    try:
        header = _header_frame(screen.right_list)
        texts = [text for _col, _cls, text in _cells(header)]
        assert texts == ["#", "Segment", "SubSegment", "Category", "Actions"]
    finally:
        root.destroy()


def test_updm41_ape_quarter_column_widths_are_unchanged():
    """UPD-M4.1 — the header's pixel minsizes, pinned before they move.

    These are the numbers the shared table has to start from: once widths come
    from a ColumnResizer the defaults must be these, or every saved layout
    shifts under the user on first launch after the change.
    """
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        header = _header_frame(screen.left_list)
        # checkbox, index, segment, subsegment, category
        assert _minsizes(header, (0, 1, 2, 3, 4)) == [34, 34, 135, 155, 125]
    finally:
        root.destroy()


def test_updm41_ape_quarter_left_row_is_a_drag_source():
    """UPD-M4.1 — every cell of a left row starts a drag, and the row has a box.

    `_bind_drag_widgets` binds the frame and all four cells, so a drag starts
    wherever in the row the pointer goes down. UPD-M2 moves that into
    screens/row_drag.py; the binding has to still be on all five widgets
    afterwards.
    """
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        row = _row_frames(screen.left_list)[0]
        classes = [cls for _col, cls, _text in _cells(row)]
        assert classes[0] == "CTkCheckBox"

        draggable = [row] + [c for c in row.winfo_children()
                             if not isinstance(c, ctk.CTkCheckBox)]
        assert len(draggable) == 5
        for widget in draggable:
            assert "<Button-1>" in set(_bound_sequences(widget))
    finally:
        root.destroy()


def test_updm41_ape_quarter_right_row_ends_with_a_delete_button():
    """UPD-M4.1 — the right row's last cell is its own Delete.

    Per-row Delete in the Actions column is what the right panel has today and
    what UPD-M5.2 adds to APE Week Assignment. A right row is not a drag
    source: dragging is one-way, left to right.
    """
    root, screen = _quarter_screen(right_rows=[_ape_row(1)])
    try:
        row = _row_frames(screen.right_list)[0]
        cells = _cells(row)
        assert cells[-1][1] == "CTkButton"
        assert cells[-1][2] == "Delete"
        assert "<Button-1>" not in set(_bound_sequences(row))
    finally:
        root.destroy()


# ------------------------- UPD-M4.1: APE Month and Annual, as they stand

def _fake_month_vps(left_rows, right_rows):
    """A VPS double for APE Month Assignment, same shape as `_fake_vps`."""
    calls = []
    return SimpleNamespace(
        calls=calls,
        get_annual_plan_elements_for_quarter=lambda year, quarter: list(left_rows),
        get_annual_plan_elements_for_month=lambda year, month: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
        assign_ape_to_month=lambda *a: calls.append(a) or True,
    )


def _fake_annual_vps(left_rows, right_rows):
    """A VPS double for Annual Vision Segments."""
    calls = []
    return SimpleNamespace(
        calls=calls,
        get_vision_elements=lambda: list(left_rows),
        get_annual_vision_elements=lambda year: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
        create_annual_records_from_vision_element=lambda *a: calls.append(a) or True,
    )


def _month_screen(left_rows=(), right_rows=(), settings=None):
    """APE Month Assignment on a withdrawn root, already rendered."""
    root = withdrawn_root()
    vps = _fake_month_vps(left_rows, right_rows)
    app = SimpleNamespace(vps_manager=vps)
    if settings is not None:
        app.settings = settings
    screen = APEPeriodViewScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _annual_screen(left_rows=(), right_rows=(), settings=None):
    """Annual Vision Segments on a withdrawn root, already rendered."""
    root = withdrawn_root()
    vps = _fake_annual_vps(left_rows, right_rows)
    app = SimpleNamespace(vps_manager=vps)
    if settings is not None:
        app.settings = settings
    screen = AnnualVisionSegmentsScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def test_updm41_ape_month_layout_is_unchanged():
    """UPD-M4.1 — APE Month's body is left | divider | right, and it drags.

    The same three-column body and the same three divider bindings as APE
    Quarter, pinned before this screen's own copies of the handlers are
    removed. `<ButtonPress-1>` and `<Button-1>` are one event in Tk and
    `bind()` reports the canonical name, so this assertion holds both before
    the move, where the screen binds the long form, and after, where
    split_panel binds the short one.
    """
    root, screen = _month_screen()
    try:
        body = screen.body
        assert int(screen.left_frame.grid_info()["column"]) == 0
        assert int(screen.divider.grid_info()["column"]) == 1
        assert int(screen.right_frame.grid_info()["column"]) == 2
        assert body.grid_columnconfigure(1).get("minsize") == split_panel.SPLITTER_WIDTH

        bound = set(_bound_sequences(screen.divider))
        assert {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"} <= bound
    finally:
        root.destroy()


def test_updm41_ape_month_headers_and_widths_are_unchanged():
    """UPD-M4.1 — APE Month's two headers, and the left panel's pixel widths.

    Byte for byte the same `_render_rows` as APE Quarter's, so the same
    numbers: the Pick cell over the checkboxes then the four names on the
    left, the four names then Actions on the right.
    """
    root, screen = _month_screen(left_rows=[_ape_row(1)], right_rows=[_ape_row(2)])
    try:
        left = _header_frame(screen.left_list)
        assert [text for _col, _cls, text in _cells(left)] == [
            "Pick", "#", "Segment", "SubSegment", "Category"]
        assert _minsizes(left, (0, 1, 2, 3, 4)) == [34, 34, 135, 155, 125]

        right = _header_frame(screen.right_list)
        assert [text for _col, _cls, text in _cells(right)] == [
            "#", "Segment", "SubSegment", "Category", "Actions"]
        assert _minsizes(right, (0, 1, 2, 3, 4)) == [34, 135, 155, 125, 84]
    finally:
        root.destroy()


def test_updm41_ape_month_rows_drag_left_and_delete_right():
    """UPD-M4.1 — a left row is a drag source, a right row has its Delete.

    Five draggable widgets on the left (the frame and its four cells, not the
    checkbox) and a Delete button in the right row's Actions column. Dragging
    is one-way, so the right row is bound to nothing.
    """
    root, screen = _month_screen(left_rows=[_ape_row(1)], right_rows=[_ape_row(2)])
    try:
        left_row = _row_frames(screen.left_list)[0]
        assert [cls for _col, cls, _text in _cells(left_row)][0] == "CTkCheckBox"
        draggable = [left_row] + [c for c in left_row.winfo_children()
                                  if not isinstance(c, ctk.CTkCheckBox)]
        assert len(draggable) == 5
        for widget in draggable:
            assert "<Button-1>" in set(_bound_sequences(widget))

        right_row = _row_frames(screen.right_list)[0]
        last = _cells(right_row)[-1]
        assert last[1] == "CTkButton"
        assert last[2] == "Delete"
        assert "<Button-1>" not in set(_bound_sequences(right_row))
    finally:
        root.destroy()


def test_updm41_annual_layout_is_unchanged():
    """UPD-M4.1 — Annual Vision Segments' body and divider, pinned.

    This screen declares its own `SPLITTER_WIDTH = 8`, which is the number
    split_panel carries, so the middle column's width is the same before and
    after the move.
    """
    root, screen = _annual_screen()
    try:
        body = screen.body
        assert int(screen.left_frame.grid_info()["column"]) == 0
        assert int(screen.divider.grid_info()["column"]) == 1
        assert int(screen.right_frame.grid_info()["column"]) == 2
        assert body.grid_columnconfigure(1).get("minsize") == split_panel.SPLITTER_WIDTH

        bound = set(_bound_sequences(screen.divider))
        assert {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"} <= bound
    finally:
        root.destroy()


def test_updm41_annual_headers_and_widths_are_unchanged():
    """UPD-M4.1 — Annual's headers, and the Actions column that is 140 not 84.

    This is the one column width that differs across the three screens: the
    Annual right panel's Actions column holds Edit *and* Delete, so it is 140
    where the APE tabs' is 84. The shared table has to let a screen say so,
    and this pins the number it has to reproduce.
    """
    root, screen = _annual_screen(left_rows=[_ape_row(1)], right_rows=[_ape_row(2)])
    try:
        left = _header_frame(screen.left_list)
        assert [text for _col, _cls, text in _cells(left)] == [
            "Pick", "#", "Segment", "SubSegment", "Category"]
        assert _minsizes(left, (0, 1, 2, 3, 4)) == [34, 34, 135, 155, 125]

        right = _header_frame(screen.right_list)
        assert [text for _col, _cls, text in _cells(right)] == [
            "#", "Segment", "SubSegment", "Category", "Actions"]
        assert _minsizes(right, (0, 1, 2, 3, 4)) == [34, 135, 155, 125, 140]
    finally:
        root.destroy()


def test_updm41_annual_right_row_keeps_edit_beside_delete():
    """UPD-M4.1 — Annual's right row ends in a frame holding Edit and Delete.

    Not a bare button like the APE tabs': the two buttons are packed into a
    transparent sub-frame gridded in the Actions column. The screen keeps
    owning that cell after the move, so what is in it must not change.
    """
    root, screen = _annual_screen(left_rows=[_ape_row(1)], right_rows=[_ape_row(2)])
    try:
        right_row = _row_frames(screen.right_list)[0]
        last = _cells(right_row)[-1]
        assert last[1] == "CTkFrame"

        actions = [c for c in right_row.winfo_children()
                   if isinstance(c, ctk.CTkFrame) and c.grid_info()
                   and int(c.grid_info()["column"]) == last[0]][0]
        assert [b.cget("text") for b in actions.winfo_children()] == ["Edit", "Delete"]

        left_row = _row_frames(screen.left_list)[0]
        draggable = [left_row] + [c for c in left_row.winfo_children()
                                  if not isinstance(c, ctk.CTkCheckBox)]
        assert len(draggable) == 5
        for widget in draggable:
            assert "<Button-1>" in set(_bound_sequences(widget))
    finally:
        root.destroy()


# ------------------------------------------- UPD-M3: the shared chip table

def _table(prefix="ape_quarter_left", columns=None, settings=None):
    """A ChipTable in a scrollable frame on a withdrawn root."""
    root = withdrawn_root()
    frame = ctk.CTkScrollableFrame(root)
    frame.grid(row=0, column=0, sticky="nsew")
    cols = columns if columns is not None else list(chip_table.APE_LEFT_COLUMNS)
    table = chip_table.ChipTable(
        frame, settings if settings is not None else FakeSettings(), prefix, cols
    )
    return root, frame, table


class FakeSettings:
    """Attribute bag with a save() counter, as tests/test_column_resize.py uses."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.saved = 0

    def save(self):
        self.saved += 1


def test_updm31_table_renders_header_and_rows():
    """UPD-M3.1 — a header in column order, then one frame per row.

    The table owns the header and the row frames; the screen owns what goes in
    the checkbox and actions columns. This is the split that lets five
    renderers become one.
    """
    root, _frame, table = _table()
    try:
        table.build_header()
        for idx in range(3):
            table.add_row(
                {"index": str(idx + 1), "segment": "Purposeful Work",
                 "subsegment": "Living Systems", "category": "Blog"},
                {"segment": "#3366cc", "subsegment": "#44aa88", "category": "#cc7744"},
            )
        assert [c.heading for c in table.columns] == [
            "Pick", "#", "Segment", "SubSegment", "Category"]
        assert len(table.rows) == 3
        texts = [lbl.cget("text").strip() for lbl in table.rows[0][1].values()]
        assert "Purposeful Work" in texts
    finally:
        root.destroy()

    # The right panel's set is the same four names with Actions after them and
    # no checkbox before them, so a column's grid index differs between the
    # two panels of one tab. That is why there is a set per panel.
    assert [c.heading for c in chip_table.APE_RIGHT_COLUMNS] == [
        "#", "Segment", "SubSegment", "Category", "Actions"]
    assert [c.default_width for c in chip_table.APE_RIGHT_COLUMNS][-1] == 84
    assert [c.default_width for c in chip_table.ANNUAL_RIGHT_COLUMNS][-1] == 140


def test_updm31_every_shipped_column_declares_a_width_it_can_have():
    """UPD-M3.1 — every shipped column's default sits inside its own bounds.

    `ColumnResizer` clamps a stored width into [min, max], so a column
    declared 34 wide with ChipColumn's default minimum of 40 renders at 40 and
    nothing reports it. That is exactly what happened to the checkbox and #
    columns, and UPD-M4.1's pixel assertion is what caught it. This holds
    every set, so the next one cannot repeat it.
    """
    sets = {
        "APE_LEFT_COLUMNS": chip_table.APE_LEFT_COLUMNS,
        "APE_RIGHT_COLUMNS": chip_table.APE_RIGHT_COLUMNS,
        "ANNUAL_RIGHT_COLUMNS": chip_table.ANNUAL_RIGHT_COLUMNS,
        "WEEK_ASSIGNMENT_RIGHT_COLUMNS": chip_table.WEEK_ASSIGNMENT_RIGHT_COLUMNS,
        "WEEK_ACTIONS_LEFT_COLUMNS": chip_table.WEEK_ACTIONS_LEFT_COLUMNS,
    }
    for name, columns in sets.items():
        assert columns, f"{name} is empty"
        for column in columns:
            assert column.min_width <= column.default_width <= column.max_width, (
                f"{name}.{column.key} declares {column.default_width} but is "
                f"bounded [{column.min_width}, {column.max_width}]")


def test_updm32_every_resizable_column_has_a_handle():
    """UPD-M3.2 — a drag handle per resizable column, and none on the others.

    Exact count, not a floor: the checkbox and Actions columns are fixed
    width, and a handle on them would let a user drag a column that has
    nothing to show.
    """
    root, _frame, table = _table()
    try:
        header = table.build_header()
        handles = [c for c in header.winfo_children()
                   if c.cget("cursor") == "sb_h_double_arrow"]
        resizable = [c for c in table.columns if c.resizable]
        # Segment, SubSegment, Category. The checkbox and # columns are fixed,
        # as is Actions on the panels that have one: a 34px number has nothing
        # to widen into.
        assert len(handles) == len(resizable) == 3
    finally:
        root.destroy()


def test_updm33_resizing_one_column_leaves_the_others():
    """UPD-M3.3 — a drag moves its own column's width and no other's."""
    settings = FakeSettings()
    root, _frame, table = _table(settings=settings)
    try:
        table.build_header()
        before = {c.key: table.resizer.width(c.key) for c in table.columns}
        table.resizer._on_start(SimpleNamespace(x_root=500), "segment")
        table.resizer._on_drag(SimpleNamespace(x_root=560), "segment")
        table.resizer._on_stop(SimpleNamespace(x_root=560), "segment")

        assert table.resizer.width("segment") == before["segment"] + 60
        for key, width in before.items():
            if key != "segment":
                assert table.resizer.width(key) == width
    finally:
        root.destroy()


def test_updm34_column_width_is_clamped():
    """UPD-M3.4 — a drag past either bound stops at the bound.

    Without this a column can be dragged to nothing and never dragged back,
    because the handle goes with it.
    """
    root, _frame, table = _table()
    try:
        table.build_header()
        spec = table.resizer.specs["segment"]

        table.resizer._on_start(SimpleNamespace(x_root=500), "segment")
        table.resizer._on_drag(SimpleNamespace(x_root=0), "segment")
        assert table.resizer.width("segment") == spec.min_width

        table.resizer._on_start(SimpleNamespace(x_root=500), "segment")
        table.resizer._on_drag(SimpleNamespace(x_root=9000), "segment")
        assert table.resizer.width("segment") == spec.max_width
    finally:
        root.destroy()


def test_updm35_chip_text_follows_the_column_width():
    """UPD-M3.5 — narrowing a column re-clamps the chip text inside it.

    A chip is a solid pill whose fill is the column width, so text that is not
    re-clamped does not overflow invisibly -- it widens the pill and pushes
    the next column off the panel.
    """
    root, _frame, table = _table()
    try:
        table.build_header()
        _frame_row, cells = table.add_row(
            {"segment": "Purposeful Work and then some more words"},
            {"segment": "#3366cc"},
        )
        wide = cells["segment"].cget("text")

        table.resizer._on_start(SimpleNamespace(x_root=500), "segment")
        table.resizer._on_drag(SimpleNamespace(x_root=440), "segment")
        narrow = cells["segment"].cget("text")

        assert len(narrow) < len(wide)
    finally:
        root.destroy()


def test_updm35_chip_text_fits_the_pill_not_the_column():
    """UPD-M3.5 / AWA-S5 — the character budget comes from the pill's width.

    A chip pill is CHIP_INSET narrower than its column, so a budget measured
    from the column width overruns the pill by one character at most widths
    and by two where the column width is a multiple of CHAR_PX. The last
    character was clipped on the 135px Segment column on every row of every
    panel that adopts this table.

    Asserted at three widths because the off-by-how-much depends on the
    width modulo CHAR_PX: one number would pass with the bug still in.
    """
    from src.getmoredone.screens.column_resize import chars_for_width

    root, _frame, table = _table()
    try:
        table.build_header()
        long_name = "Purposeful Work and then some more words indeed"
        for width in (135, 136, 160):
            table.resizer._widths["segment"] = width
            _row, cells = table.add_row({"segment": long_name},
                                        {"segment": "#3366cc"})
            text = cells["segment"].cget("text")
            budget = chars_for_width(table._chip_width("segment"))
            assert len(text.strip()) <= budget, (
                f"at {width}px the pill holds {budget} characters and the chip "
                f"was given {len(text.strip())}")
    finally:
        root.destroy()


def test_updm35_a_drag_re_clamps_to_the_pill_too():
    """UPD-M3.5 / AWA-S5 — the live re-clamp uses the same budget as the render.

    `_apply_live` recomputed the text from the column width while setting the
    label's width to the column less the inset, so a drag reproduced the
    clipping the render had just been fixed for. Both paths now take the
    cell's own width_delta.
    """
    from src.getmoredone.screens.column_resize import chars_for_width

    root, _frame, table = _table()
    try:
        table.build_header()
        _row, cells = table.add_row(
            {"segment": "Purposeful Work and then some more words"},
            {"segment": "#3366cc"})

        table.resizer._on_start(SimpleNamespace(x_root=500), "segment")
        table.resizer._on_drag(SimpleNamespace(x_root=460), "segment")

        text = cells["segment"].cget("text")
        assert len(text.strip()) <= chars_for_width(table._chip_width("segment"))
    finally:
        root.destroy()


def test_updm31_a_row_before_a_header_is_refused():
    """UPD-M3.1 / AWA-S6 d — add_row without build_header raises.

    It used to grid the first row at row 1 and leave row 0 empty, which reads
    as a panel with a missing header rather than as a mistake.
    """
    root, _frame, table = _table()
    try:
        with pytest.raises(ValueError, match="before build_header"):
            table.add_row({"segment": "Purposeful Work"})
    finally:
        root.destroy()


def test_updm31_a_row_with_no_known_column_is_refused():
    """UPD-M3.1 / AWA-S6 e — values naming no column of this table raises.

    `values={}`, or a typo in a key, appended a zero-cell, zero-height frame
    with no error and no signal: a row the panel counts and the user cannot
    see.
    """
    root, _frame, table = _table()
    try:
        table.build_header()
        with pytest.raises(ValueError, match="no known column key"):
            table.add_row({})
        with pytest.raises(ValueError, match="no known column key"):
            table.add_row({"segmant": "typo"})
        assert table.rows == []
    finally:
        root.destroy()


def test_updm31_clearing_forgets_the_destroyed_header():
    """UPD-M3.1 / AWA-S6 b — clear() drops the resizer's header registration.

    The header frame is destroyed with the rows, but the resizer went on
    holding it and relied on `winfo_exists()` to make a later drag a no-op.
    """
    root, _frame, table = _table()
    try:
        table.build_header()
        assert table.resizer._header is not None
        table.clear()
        assert table.resizer._header is None
    finally:
        root.destroy()


def test_updm31_the_table_makes_its_container_stretch():
    """UPD-M3.1 / AWA-S6 c — build_header weights the container's column 0.

    The header and every row are gridded sticky="ew" in column 0, which does
    nothing at all unless that column can stretch. Every adopting screen sets
    it, so the table setting it changes nothing for them -- it stops the next
    adopter getting a ragged panel and no clue why.
    """
    root = withdrawn_root()
    try:
        frame = ctk.CTkScrollableFrame(root)
        frame.grid(row=0, column=0, sticky="nsew")
        table = chip_table.ChipTable(frame, FakeSettings(), "ape_quarter_left",
                                     list(chip_table.APE_LEFT_COLUMNS))
        assert frame.grid_columnconfigure(0).get("weight") == 0
        table.build_header()
        assert frame.grid_columnconfigure(0).get("weight") == 1
    finally:
        root.destroy()


def test_updm36_panels_keep_their_own_widths():
    """UPD-M3.6 — two tables with different prefixes do not share a width.

    The left and right panel of one tab are different shapes and different
    widths; one store for both would make a drag in one panel move the other.
    """
    settings = FakeSettings()
    root = withdrawn_root()
    try:
        left_frame = ctk.CTkScrollableFrame(root)
        right_frame = ctk.CTkScrollableFrame(root)
        left = chip_table.ChipTable(left_frame, settings, "ape_quarter_left",
                                    list(chip_table.APE_LEFT_COLUMNS))
        right = chip_table.ChipTable(right_frame, settings, "ape_quarter_right",
                                     list(chip_table.APE_RIGHT_COLUMNS))
        start = right.resizer.width("segment")

        left.resizer._on_start(SimpleNamespace(x_root=500), "segment")
        left.resizer._on_drag(SimpleNamespace(x_root=580), "segment")
        left.resizer._on_stop(SimpleNamespace(x_root=580), "segment")

        assert left.resizer.width("segment") == start + 80
        assert right.resizer.width("segment") == start
        assert settings.ape_quarter_left_col_widths["segment"] == start + 80
        assert not getattr(settings, "ape_quarter_right_col_widths", {})
    finally:
        root.destroy()


def test_updm37_missing_lineage_falls_back_instead_of_raising():
    """UPD-M3.7 — an empty name renders empty, an empty colour gets the surface.

    APEs with no subsegment or category exist in the live database. "It did
    not raise" is not a verdict -- pytest gives that for free and it would
    still hold if the chip rendered the string "None" on a transparent
    background. So this asserts the two things the fallbacks actually do:
    a missing value is empty text, not "None", and a missing colour is the
    panel surface, not an empty colour Tk would reject.
    """
    root, _frame, table = _table()
    try:
        palette_surface = chip_table.semantic_colors()[chip_table.DEFAULT_CHIP_KEY]
        table.build_header()
        _row_frame, cells = table.add_row(
            {"segment": "", "subsegment": None, "category": "Blog"},
            {"segment": "", "subsegment": "", "category": "#cc7744"},
        )
        assert cells["subsegment"].cget("text").strip() == ""
        assert cells["segment"].cget("fg_color") == palette_surface
        assert cells["category"].cget("fg_color") == "#cc7744"
    finally:
        root.destroy()


def test_updm37_the_fallback_chip_does_not_measure_a_named_colour():
    """UPD-M3.7 — the lineage chip measures its colour; the fallback must not.

    `pick_text_color` parses a hex string. The fallback fill is a theme token,
    and on 7 of the 10 themes that token is a *named* Tk colour ("gray16" in
    dark mode), which it cannot parse — it returned the dark default, which is
    black text on a near-black pill, on exactly the rows the fallback exists
    for. The fix is not a better parser: the theme's own label colour is
    readable on the theme's own surface by construction, so the fallback
    leaves `text_color` unset and inherits it.

    Asserted as the two branches side by side in one row, so a fix that
    stopped measuring the lineage colour too would be red here.

    The whole verdict for the fallback branch is the equality against the
    theme's own value. A second line asserting the colour is not `"#000000"`
    was removed: `ThemeManager.theme["CTkLabel"]["text_color"]` is a two-element
    light/dark list (`['gray10', '#DCE4EE']` on the active theme), so comparing
    it to a single hex string could never fail and read as a check while
    carrying no weight. The equality does the work - the mutation that makes
    the fallback measure its fill is red at that line.
    """
    root, _frame, table = _table()
    try:
        inherited = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        table.build_header()
        _row_frame, cells = table.add_row(
            {"segment": "No colour", "category": "Measured"},
            {"segment": "", "category": "#cc7744"},
        )
        # The fallback pill inherits the theme's own label colour.
        assert cells["segment"].cget("text_color") == inherited
        # The lineage pill is still measured against its own fill.
        assert cells["category"].cget("text_color") == pick_text_color("#cc7744")
    finally:
        root.destroy()


# ----------------------------------------------- UPD-M1: one splitter, not four

SPLITTER_METHODS = ("_apply_split_ratio", "_on_divider_drag")

# The screens that still carry their own copy of the splitter. Empty as of
# UPD-M5: ape_assignment adopted at UPD-M1, ape_period_view and
# annual_vision_segments at UPD-M4, and weekly_items here. It stays as an
# exact set rather than a ceiling, so a seventh screen that grows its own copy
# appears in `found` and this goes red.
SPLITTER_HOLDOUTS: set = set()

# A fifth copy, older than the four and not one of them: a different minimum
# (300), a different default ratio (0.6), a clamp that holds both panels, and
# no _apply_split_ratio of its own. project_boards.py is not a VSP tab, so it
# is outside this spec's scope and is recorded as an adjacent issue rather
# than swept into this change. It is listed here, not excluded from the scan,
# so that it cannot be forgotten and cannot grow a sixth variant unnoticed.
SPLITTER_OUT_OF_SCOPE = {"project_boards.py"}


def _event(x_root):
    """A press/motion/release event, which is read for x_root and nothing else."""
    return SimpleNamespace(x_root=x_root)


def _splitter(body_width=1208, ratio=None, settings=None, prefix=None):
    """A real three-column body with a real divider, on a withdrawn root.

    Real widgets rather than a double: the arithmetic under test reads
    `winfo_width()` and writes grid minsizes, and a double would assert the
    test's own idea of what Tk reports rather than what it reports.
    """
    root = withdrawn_root()
    body = ctk.CTkFrame(root, width=body_width, height=400)
    body.grid(row=0, column=0)
    body.grid_propagate(False)
    body.grid_rowconfigure(0, weight=1)
    left = ctk.CTkFrame(body)
    left.grid(row=0, column=0, sticky="nsew")
    divider = ctk.CTkFrame(body, width=split_panel.SPLITTER_WIDTH)
    divider.grid(row=0, column=1, sticky="ns")
    right = ctk.CTkFrame(body)
    right.grid(row=0, column=2, sticky="nsew")
    root.update_idletasks()
    panel = split_panel.SplitPanel(
        body, left, divider, settings=settings, prefix=prefix
    )
    if ratio is not None:
        panel.ratio = ratio
    panel.apply()
    root.update_idletasks()
    return root, body, left, divider, panel


def test_updm11_split_panel_module_owns_the_divider():
    """UPD-M1.1 — the module holds the ratio, the clamp and the handlers.

    Asserted by use, not by reading the source: constructing a SplitPanel must
    leave the three divider events and the body's resize bound to it, and the
    ratio and the clamp must be reachable on the instance. If any of this were
    left in a screen, there would be nothing here to bind.
    """
    root, body, left, divider, panel = _splitter()
    try:
        assert panel.ratio == split_panel.DEFAULT_SPLIT_RATIO
        assert panel.clamp_left(0, 1200) == split_panel.MIN_PANEL_WIDTH
        assert panel.clamp_left(1200, 1200) == 1200 - split_panel.MIN_PANEL_WIDTH

        on_divider = set(_bound_sequences(divider))
        assert {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"} <= on_divider
        assert "<Configure>" in set(_bound_sequences(body))

        # The handlers the screens used to own, now reachable only here.
        for name in ("apply", "on_body_resize", "on_press", "on_drag", "on_release"):
            assert callable(getattr(panel, name)), name
    finally:
        root.destroy()


def test_updm12_drag_moves_both_panels_by_the_same_amount():
    """UPD-M1.2 — 60px right widens the left by 60 and narrows the right by 60.

    The press is asserted to have captured the left panel's applied width: with
    an unlaid-out panel the clamp would absorb the drag and the equal-and-
    opposite assertion below would hold while measuring nothing.
    """
    root, body, left, divider, panel = _splitter()
    try:
        before = _minsizes(body, (0, 2))
        assert before == [600, 600]          # 1208 - 8 splitter, halved
        start_left = left.winfo_width()
        assert start_left == before[0]

        panel.on_press(_event(1000))
        panel.on_drag(_event(1060))
        after = _minsizes(body, (0, 2))

        assert after[0] == start_left + 60
        assert after[0] > before[0]           # right, past the midpoint
        assert after[0] - before[0] == -(after[1] - before[1])
        assert after[0] + after[1] == before[0] + before[1]
    finally:
        root.destroy()


def test_updm13_neither_panel_can_be_crushed():
    """UPD-M1.3 — the minimum wins over the ratio, at every body width.

    Two regimes, and the second one is the honest limit rather than a promise
    the code does not keep: while the body can seat both minimums, a drag to
    either edge leaves the far panel at exactly MIN_PANEL_WIDTH; below that the
    left panel keeps its minimum and the right is given what is left, which can
    be less than a minimum. A body that narrow cannot satisfy both.
    """
    minimum = split_panel.MIN_PANEL_WIDTH
    roomy = [2 * minimum + split_panel.SPLITTER_WIDTH, 1208, 1920]
    for width in roomy:
        root, body, left, divider, panel = _splitter(body_width=width)
        try:
            total = width - split_panel.SPLITTER_WIDTH
            for ratio in (-5.0, 0.0, 0.01, 0.5, 0.99, 5.0):
                panel.ratio = ratio
                panel.apply()
                got = _minsizes(body, (0, 2))
                assert got[0] >= minimum, (width, ratio, got)
                assert got[1] >= minimum, (width, ratio, got)
                assert got[0] + got[1] == total, (width, ratio, got)
            # A drag to either edge stops at the far panel's minimum.
            panel.on_press(_event(0))
            panel.on_drag(_event(10_000))
            assert _minsizes(body, (0, 2)) == [total - minimum, minimum]
            panel.on_drag(_event(-10_000))
            assert _minsizes(body, (0, 2)) == [minimum, total - minimum]
        finally:
            root.destroy()

    # Below two minimums the body overflows rather than crushing a panel.
    for cramped in (2 * minimum + split_panel.SPLITTER_WIDTH - 100, minimum, 40):
        root, body, left, divider, panel = _splitter(body_width=cramped)
        try:
            for ratio in (0.01, 0.5, 0.99):
                panel.ratio = ratio
                panel.apply()
                got = _minsizes(body, (0, 2))
                assert got[0] >= minimum, (cramped, ratio, got)
                assert got[1] >= minimum, (cramped, ratio, got)
                assert got[0] + got[1] > cramped - split_panel.SPLITTER_WIDTH
        finally:
            root.destroy()


def test_updm14_zero_width_body_is_a_noop():
    """UPD-M1.4 — a body with nothing to divide is left alone.

    Reached on every screen before the first layout pass, when winfo_width() is
    1. apply() and on_drag() must leave the columns as they were rather than
    divide by a total of zero.
    """
    minimum = split_panel.MIN_PANEL_WIDTH
    for body_width in (split_panel.SPLITTER_WIDTH, 4, 1):
        root, body, left, divider, panel = _splitter(body_width=1208)
        try:
            panel.apply()
            laid_out = _minsizes(body, (0, 2))

            # CIG-M2.1 — the one reading the code takes, forced, rather than
            # a resize of the real widget.
            #
            # `body.configure(width=body_width)` is what this did until
            # 2026-11-09. It shrinks the body here and did nothing under X11,
            # where CI reported `assert 1208 <= 8` on every run: the test
            # failed before reaching the code it names. Two attempts to force
            # the resize instead — a fixed-width holder, then cancelling the
            # root's `wm geometry` — were both withdrawn after measurement,
            # the first because the body then reported 1px whatever the holder
            # did, the second because the root's geometry is not what the body
            # follows (`withdrawn_root()` sets 1400x900, and 1208 is the body's own
            # request). The X11 cause is still undiagnosed, and a comment
            # asserting a cause nobody measured is the defect this batch is
            # about.
            #
            # So the input is forced where the code reads it. The arithmetic,
            # the widgets and the grid minsizes it writes are all still real;
            # what is stubbed is the one number the criterion is about, which
            # is "before the first layout pass, when winfo_width() is 1".
            body.winfo_width = lambda: body_width
            assert body.winfo_width() <= split_panel.SPLITTER_WIDTH, (
                "the stub did not take, so this test is not measuring a body "
                "with nothing to divide")

            panel.ratio = 0.75
            panel.apply()
            assert _minsizes(body, (0, 2)) == laid_out, body_width

            panel.on_press(_event(500))
            panel.on_drag(_event(900))
            assert _minsizes(body, (0, 2)) == laid_out, body_width
            assert panel.ratio == 0.75, body_width
            assert laid_out[0] >= minimum
        finally:
            root.destroy()


def _screens_with_their_own_splitter():
    """{filename: the splitter names it defines} across screens/, by AST.

    split_panel.py is excluded because it is the file that must define them.
    Nothing else is excluded, so a seventh screen that grows its own copy
    appears here.
    """
    found = {}
    for path in sorted((SRC / "screens").glob("*.py")):
        if path.name == "split_panel.py":
            continue
        names = set()
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in SPLITTER_METHODS:
                    names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SPLITTER_WIDTH":
                        names.add("SPLITTER_WIDTH")
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == "SPLITTER_WIDTH":
                    names.add("SPLITTER_WIDTH")
        if names:
            found[path.name] = names
    return found


def test_updm15_no_screen_keeps_its_own_splitter():
    """UPD-M1.5 — counted from the AST, as an exact set. Zero at UPD-M5.

    Every screen in the alignment has adopted screens/split_panel.py, so the
    holdout set is empty and the only file left with a splitter is
    project_boards.py, which is out of scope by UPD-A5. Asserted as an exact
    set in both directions: red if any of the four grows a copy back, and red
    if project_boards.py is consolidated and not struck off here.
    """
    found = _screens_with_their_own_splitter()
    assert SPLITTER_HOLDOUTS == set(), "strike a holdout off the set when it adopts"
    assert set(found) == SPLITTER_OUT_OF_SCOPE
    for adopted in ("ape_assignment.py", "ape_period_view.py",
                    "annual_vision_segments.py", "weekly_items.py"):
        assert adopted not in found, f"{adopted} grew a splitter back"
    # project_boards.py inlines its apply into _on_body_resize, so it has no
    # _apply_split_ratio to find. Asserted exactly, so that the day it is
    # consolidated this test says so.
    assert found["project_boards.py"] == {"_on_divider_drag", "SPLITTER_WIDTH"}


def test_updm16_split_ratio_survives_a_relaunch():
    """UPD-M1.6 — dragged, saved, and back where it was on the next build.

    Through the real screen, because the field name is the screen's to get
    right: a prefix with no AppSettings field persists nothing.
    """
    settings = FakeSettings(ape_quarter_split_ratio=0.5)
    root, screen = _quarter_screen(settings=settings)
    try:
        assert screen.split.setting_attr() == "ape_quarter_split_ratio"
        screen.split.ratio = 0.7
        screen.split.on_press(_event(0))
        screen.split.on_release(_event(0))
        assert settings.ape_quarter_split_ratio == 0.7
        assert settings.saved == 1
    finally:
        root.destroy()

    root, screen = _quarter_screen(settings=settings)
    try:
        assert screen.split.ratio == 0.7
    finally:
        root.destroy()


def test_updm16_the_ratio_has_a_settings_field_to_land_in():
    """UPD-M1.6 — the field is declared, so the real app saves it.

    AppSettings.save() writes declared dataclass fields only, so an attribute
    set on the instance by name alone would be dropped at the next write and
    the divider would silently reopen at 0.5.
    """
    names = {f.name for f in dataclasses.fields(AppSettings)}
    assert APEAssignmentScreen.SETTINGS_PREFIX == "ape_quarter"
    assert f"{APEAssignmentScreen.SETTINGS_PREFIX}_split_ratio" in names
    assert AppSettings().ape_quarter_split_ratio == split_panel.DEFAULT_SPLIT_RATIO


def test_updm16_a_prefix_with_no_settings_field_says_so(caplog):
    """UPD-M1.6 (P2) — an unpersistable prefix is reported, not swallowed.

    The failure is invisible from the screen: everything drags, and only the
    next launch shows the divider back at the middle. The warning is the only
    surface that can say why, so it is asserted rather than assumed.
    """
    settings = FakeSettings()
    with caplog.at_level(logging.WARNING, logger=split_panel.logger.name):
        root, body, left, divider, panel = _splitter(
            settings=settings, prefix="nowhere"
        )
    try:
        assert panel.ratio == split_panel.DEFAULT_SPLIT_RATIO
        assert any(
            "nowhere_split_ratio" in record.getMessage()
            for record in caplog.records
        ), [r.getMessage() for r in caplog.records]

        panel.on_press(_event(0))
        panel.on_release(_event(0))
        assert settings.saved == 0
        assert not hasattr(settings, "nowhere_split_ratio")
    finally:
        root.destroy()


# --------------------------------------------- UPD-M2: one row-drag, not four

DRAG_METHODS = ("_start_row_drag", "_is_descendant")

# The screens that still carry their own copy of the row drag. Empty as of
# UPD-M5, and with no out-of-scope file beside it: project_boards.py has a
# splitter but no row drag, so this set reaching zero means no screen under
# screens/ defines either drag method. Exact, like SPLITTER_HOLDOUTS.
DRAG_HOLDOUTS: set = set()


class _FakeWidget:
    """A widget that records what was bound on it.

    `winfo_pointerxy` reads the real mouse, so the drop test cannot be driven
    with real widgets: where the pointer happens to be when the suite runs is
    not an input a test may depend on. These doubles are the only way to say
    "the release landed here" and mean it, and they are what the drag tests in
    tests/test_ape_period_consistency.py already use.
    """

    def __init__(self, name="widget", master=None):
        self.name = name
        self.master = master
        self.bound = {}
        self.unbound = []

    def bind(self, sequence, handler):
        # Tk replaces rather than appends without add="+", and so does this.
        self.bound[sequence] = handler

    def unbind(self, sequence):
        self.unbound.append(sequence)
        self.bound.pop(sequence, None)


class _FakeScreen:
    """The three things RowDragSource reads from the screen it is given."""

    def __init__(self, containing=None):
        self.toplevel = _FakeWidget("toplevel")
        self.containing = containing
        self.asked = None

    def winfo_toplevel(self):
        return self.toplevel

    def winfo_pointerxy(self):
        return (7, 11)

    def winfo_containing(self, x, y):
        self.asked = (x, y)
        return self.containing


def _drag_source(containing=None, target=None):
    """A RowDragSource over doubles, plus the list its on_drop appends to."""
    dropped = []
    target = target if target is not None else _FakeWidget("right_list")
    screen = _FakeScreen(containing=containing)
    source = row_drag.RowDragSource(screen, target, dropped.append)
    return screen, target, source, dropped


def test_updm21_every_widget_in_the_row_is_a_drag_handle():
    """UPD-M2.1 — the frame and every cell start the drag, with their own row.

    Two rows are bound, and each row's five handles are asserted to start
    *that* row: a drag handle that assigns the wrong record is worse than one
    that does nothing, because it looks like it worked.

    What this test does **not** establish, though its first draft said it did:
    that the `r=row` default argument in `bind_row`'s lambda is load-bearing.
    It is not. `bind_row`'s loop is over the widgets, and `row` is a parameter
    of the call, so each call already closes over its own `row` and the
    late-binding trap that default argument guards against cannot be reached
    here. Replacing `lambda _event, r=row: self.start(r)` with
    `lambda _event: self.start(row)` leaves this test **green** — measured.
    The assertions that carry a verdict are the two mutations that do turn it
    red: binding only `widgets[:1]`, and starting with a row other than the
    one bound.
    """
    screen, target, source, dropped = _drag_source()
    first = [_FakeWidget(f"a{i}") for i in range(5)]
    second = [_FakeWidget(f"b{i}") for i in range(5)]
    row_a = {"id": "ape-a"}
    row_b = {"id": "ape-b"}
    source.bind_row(first, row_a)
    source.bind_row(second, row_b)

    for widget in first + second:
        assert set(widget.bound) == {"<ButtonPress-1>"}, widget.name

    for widget in first:
        source.dragged_row = None
        widget.bound["<ButtonPress-1>"](SimpleNamespace())
        assert source.dragged_row is row_a, widget.name
    for widget in second:
        source.dragged_row = None
        widget.bound["<ButtonPress-1>"](SimpleNamespace())
        assert source.dragged_row is row_b, widget.name

    # The release is the toplevel's, not the row's: the pointer leaves the row.
    assert set(screen.toplevel.bound) == {"<ButtonRelease-1>"}


def test_updm22_drop_inside_the_target_assigns_once():
    """UPD-M2.2 — one release inside the target is one call, with that row.

    A nested widget, not the target itself, because that is what
    `winfo_containing` returns for a drop onto a row of the right-hand list.
    """
    target = _FakeWidget("right_list")
    inner = _FakeWidget("right_row", master=_FakeWidget("mid", master=target))
    screen, target, source, dropped = _drag_source(containing=inner, target=target)
    row = {"id": "ape-1"}

    source.start(row)
    source.finish(SimpleNamespace())

    assert dropped == [row]
    assert screen.asked == (7, 11), "the pointer decides the target, not the event"
    assert source.dragged_row is None
    assert screen.toplevel.unbound == ["<ButtonRelease-1>"]

    # A second release, with no second press, adds nothing.
    source.finish(SimpleNamespace())
    assert dropped == [row]


def test_updm23_drop_outside_the_target_does_nothing():
    """UPD-M2.3 — released over another widget, or over nothing at all.

    `winfo_containing` returns None when the pointer is outside every widget
    in the application, which is a release past the edge of the window.
    """
    for containing in (_FakeWidget("left_list"), None):
        target = _FakeWidget("right_list")
        screen, target, source, dropped = _drag_source(
            containing=containing, target=target
        )
        source.start({"id": "ape-1"})
        source.finish(SimpleNamespace())

        assert dropped == []
        assert source.dragged_row is None
        assert screen.toplevel.unbound == ["<ButtonRelease-1>"]


def test_updm24_release_without_a_press_does_nothing():
    """UPD-M2.4 (P7) — the input that looks like a drop and is not.

    Reached by any click on the window that is not a row: the release fires,
    there is no row, and nothing may be assigned. Asserted over a pointer that
    *is* inside the drop target, so the drop test cannot be what saves it.
    """
    target = _FakeWidget("right_list")
    inner = _FakeWidget("right_row", master=target)
    screen, target, source, dropped = _drag_source(containing=inner, target=target)

    assert source.dragged_row is None
    source.finish(SimpleNamespace())

    assert dropped == []
    assert screen.asked is None, "a release with no drag must not even look"


def test_updm24_is_descendant_walks_up_and_stops():
    """UPD-M2.4 — the descendant walk: itself, its masters, and nothing else.

    `None` is the answer `winfo_containing` gives for a pointer outside the
    application, so it has to be an ordinary input rather than a crash.
    """
    root_w = _FakeWidget("root")
    mid = _FakeWidget("mid", master=root_w)
    leaf = _FakeWidget("leaf", master=mid)
    other = _FakeWidget("other")

    assert row_drag.is_descendant(leaf, leaf)
    assert row_drag.is_descendant(leaf, mid)
    assert row_drag.is_descendant(leaf, root_w)
    assert not row_drag.is_descendant(leaf, other)
    assert not row_drag.is_descendant(root_w, leaf)
    assert not row_drag.is_descendant(None, root_w)


def _screens_with_their_own_drag():
    """{filename: the drag names it defines} across screens/, by AST."""
    found = {}
    for path in sorted((SRC / "screens").glob("*.py")):
        if path.name == "row_drag.py":
            continue
        names = {
            node.name
            for node in ast.walk(ast.parse(path.read_text()))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in DRAG_METHODS
        }
        if names:
            found[path.name] = names
    return found


def test_updm25_no_screen_keeps_its_own_drag():
    """UPD-M2.5 — counted from the AST, as an exact set. Zero at UPD-M5.

    Nothing under screens/ defines `_start_row_drag` or `_is_descendant` any
    more: all four copies are gone and screens/row_drag.py is the only owner.
    Unlike the splitter there is no out-of-scope file, so this is a plain
    emptiness assertion, and it goes red the moment any screen writes its own
    again.
    """
    found = _screens_with_their_own_drag()
    assert DRAG_HOLDOUTS == set(), "strike a holdout off the set when it adopts"
    assert found == {}, f"a screen grew its own row drag back: {sorted(found)}"


def test_updm22_the_quarter_screen_routes_its_drop_through_the_module():
    """UPD-M2.1/M2.2 — the real screen is wired to the shared module.

    The doubles above prove the module; this proves the screen uses it, which
    is the half a double cannot. Asserted on the real screen: the drag source
    exists, it points at the right panel, and its callback is the screen's own
    assignment rather than something the module invented.
    """
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        assert isinstance(screen.row_drag, row_drag.RowDragSource)
        assert screen.row_drag.drop_target is screen.right_list
        assert screen.row_drag.on_drop == screen._assign_dragged_row
        assert screen.row_drag.dragged_row is None
        assert not hasattr(screen, "dragged_row")

        row_frames = _row_frames(screen.left_list)
        assert row_frames, "a left row is needed to have a handle at all"
        bound = set(_bound_sequences(row_frames[0]))
        assert "<Button-1>" in bound
    finally:
        root.destroy()


# ------------------------------- UPD-M4.3 / UPD-M4.4: the three tabs, adopted

def _drop_on(screen, row):
    """Drive one real drop through the shared RowDragSource.

    The pointer is the one thing that cannot be real: `winfo_pointerxy` reads
    the mouse, so under a suite run it reports wherever the mouse happens to
    be. Everything else is the screen's own: its RowDragSource, its drop
    target, and `is_descendant` walking the real widget tree from the panel's
    scroll frame up to whatever that screen gave as its target.
    """
    screen.winfo_pointerxy = lambda: (0, 0)
    screen.winfo_containing = lambda *_: screen.right_list
    screen.row_drag.start(row)
    screen.row_drag.finish()


def test_updm43_a_drop_assigns_on_each_tab():
    """UPD-M4.3 — a dropped row still reaches the manager, on all three tabs.

    One drop per tab, each through that screen's own RowDragSource, each
    asserted against the call the manager actually got. The three screens
    write through three different methods with three different argument
    shapes, so a drop wired to the wrong one cannot pass by accident.

    The Annual tab's drop target is the right *frame*, not the list inside it;
    dropping on the list still counts, because `is_descendant` walks up. That
    asymmetry predates this work and is kept.
    """
    row = _ape_row(1)

    root, screen = _quarter_screen(left_rows=[row])
    try:
        _drop_on(screen, row)
        assert screen.vps_manager.calls == [("ape-1", int(screen.quarter_var.get()))]
    finally:
        root.destroy()

    root, screen = _month_screen(left_rows=[row])
    try:
        _drop_on(screen, row)
        assert screen.vps_manager.calls == [
            ("ape-1", int(screen.quarter_var.get()), int(screen.month_var.get()))]
    finally:
        root.destroy()

    root, screen = _annual_screen(left_rows=[row])
    try:
        _drop_on(screen, row)
        assert screen.vps_manager.calls == [(int(screen.year_var.get()), "ape-1")]
    finally:
        root.destroy()


def test_updm43_a_drop_outside_the_target_assigns_nothing_on_each_tab():
    """UPD-M4.3 — and the refusal path, which is where a wrong target shows.

    P7: a release that looks exactly like a drop except for where the pointer
    is. `winfo_containing` returns the *left* panel, which is a descendant of
    the screen but not of any drop target, so every tab must write nothing.
    """
    row = _ape_row(1)
    for builder in (_quarter_screen, _month_screen, _annual_screen):
        root, screen = builder(left_rows=[row])
        try:
            screen.winfo_pointerxy = lambda: (0, 0)
            screen.winfo_containing = lambda *_: screen.left_list
            screen.row_drag.start(row)
            screen.row_drag.finish()
            assert screen.vps_manager.calls == [], builder.__name__
        finally:
            root.destroy()


def _resize(table, key="segment", delta=70):
    """Drag one column handle by `delta` pixels and let go."""
    table.resizer._on_start(SimpleNamespace(x_root=500), key)
    table.resizer._on_drag(SimpleNamespace(x_root=500 + delta), key)
    table.resizer._on_stop(SimpleNamespace(x_root=500 + delta), key)


def test_updm44_ape_quarter_columns_resize_and_persist():
    """UPD-M4.4 — the quarter tab's columns drag, save, and come back.

    None of the three tabs had resizable columns before this step. The second
    build is the relaunch: the width has to come back from settings, not from
    the column's default.
    """
    settings = FakeSettings(ape_quarter_split_ratio=0.5)
    root, screen = _quarter_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        start = screen.left_table.resizer.width("segment")
        _resize(screen.left_table)
        assert screen.left_table.resizer.width("segment") == start + 70
        assert settings.ape_quarter_left_col_widths["segment"] == start + 70
        # The other panel of the same tab is a separate store (UPD-M3.6).
        assert not getattr(settings, "ape_quarter_right_col_widths", {})
    finally:
        root.destroy()

    root, screen = _quarter_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        assert screen.left_table.resizer.width("segment") == start + 70
        header = _header_frame(screen.left_list)
        assert header.grid_columnconfigure(2).get("minsize") == start + 70
    finally:
        root.destroy()


def test_updm44_ape_month_columns_resize_and_persist():
    """UPD-M4.4 — the same for APE Month, under its own prefix."""
    settings = FakeSettings(ape_month_split_ratio=0.5)
    root, screen = _month_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        start = screen.right_table.resizer.width("category")
        _resize(screen.right_table, "category", 50)
        assert settings.ape_month_right_col_widths["category"] == start + 50
        assert not getattr(settings, "ape_month_left_col_widths", {})
    finally:
        root.destroy()

    root, screen = _month_screen(right_rows=[_ape_row(1)], settings=settings)
    try:
        assert screen.right_table.resizer.width("category") == start + 50
    finally:
        root.destroy()


def test_updm44_annual_columns_resize_and_persist():
    """UPD-M4.4 — the same for Annual Vision Segments."""
    settings = FakeSettings(annual_vision_split_ratio=0.5)
    root, screen = _annual_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        start = screen.left_table.resizer.width("subsegment")
        _resize(screen.left_table, "subsegment", 40)
        assert settings.annual_vision_left_col_widths["subsegment"] == start + 40
    finally:
        root.destroy()

    root, screen = _annual_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        assert screen.left_table.resizer.width("subsegment") == start + 40
    finally:
        root.destroy()


def test_updm44_every_panel_prefix_has_a_settings_field():
    """UPD-M4.4 — every panel's width store is a declared AppSettings field.

    `ColumnResizer._persist` setattrs the store and calls `save()`, which
    writes declared dataclass fields only. An undeclared one is therefore
    *worse* than a missing split ratio: the width works all session and is
    gone at the next launch, and nothing warns. Asserted as an exact set, so a
    sixth panel cannot be added without its field.
    """
    names = {f.name for f in dataclasses.fields(AppSettings)}
    prefixes = []
    for cls in (APEAssignmentScreen, APEPeriodViewScreen, AnnualVisionSegmentsScreen):
        for side in ("left", "right"):
            prefixes.append(f"{cls.SETTINGS_PREFIX}_{side}")

    assert prefixes == [
        "ape_quarter_left", "ape_quarter_right",
        "ape_month_left", "ape_month_right",
        "annual_vision_left", "annual_vision_right",
    ]
    for prefix in prefixes:
        assert f"{prefix}_col_widths" in names, prefix
        assert getattr(AppSettings(), f"{prefix}_col_widths") == {}


def test_updm44_the_panels_a_screen_builds_use_those_prefixes():
    """UPD-M4.4 — and the screens really pass them, not just declare them.

    The field names above are only worth something if the tables use them. A
    screen that built its table with a typo'd prefix would store widths under
    an attribute nothing declares, and the test above would still pass.
    """
    for builder, prefix in ((_quarter_screen, "ape_quarter"),
                            (_month_screen, "ape_month"),
                            (_annual_screen, "annual_vision")):
        root, screen = builder()
        try:
            assert screen.left_table.prefix == f"{prefix}_left"
            assert screen.right_table.prefix == f"{prefix}_right"
            assert screen.left_table.resizer._setting_attr() == f"{prefix}_left_col_widths"
        finally:
            root.destroy()


# ------------------------- UPD-M5: APE Week Assignment, before and after

def _weekly_row(idx, segment="Purposeful Work", subsegment="Living Systems",
                category="Blog", start_date="2026-11-02"):
    """A weekly tactic row, in the shape `_weekly_parts` reads.

    The right panel's lineage comes from `ape_*` keys, not the `*_name` keys
    the left panel's APE rows carry, so a row built by `_ape_row` would render
    four dashes here and the header assertions would pass against nothing.
    """
    return {
        "id": f"wt-{idx}",
        "title": f"Tactic {idx}",
        "start_date": start_date,
        "ape_segment_name": segment,
        "ape_subsegment_name": subsegment,
        "ape_category_name": category,
    }


def _fake_week_vps(left_rows, right_rows):
    """A VPS double for APE Week Assignment.

    `get_weekly_action_items` ignores the week it is asked for and returns the
    same rows, so a test does not have to make the screen's week picker agree
    with a fixture date to see a right-hand row.
    """
    calls = []
    return SimpleNamespace(
        calls=calls,
        get_weekly_action_items=lambda **_kw: list(right_rows),
        get_annual_plan_elements_for_month=lambda year, month: list(left_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
        create_week_action_items_for_ape=lambda *a: calls.append(("create",) + a) or {
            "created_count": 1, "skipped_count": 0, "collided_count": 0},
        delete_weekly_action_item=lambda item_id: calls.append(("delete", item_id)) or True,
        # WTP-M5.2 and WTP-M6.4 — the screen reads these two now: the count in
        # the delete confirmation, and the Done column on each row. Returning
        # fixed values keeps this file's subject the panel's layout; the
        # numbers themselves are asserted against a real database in
        # tests/test_weekly_tactic_parent.py.
        children_to_delete_with_weekly_tactic=lambda item_id: [],
        count_open_children_for_weekly_tactic=lambda item_id: (0, 0),
    )


def _week_screen(left_rows=(), right_rows=(), settings=None):
    """APE Week Assignment on a withdrawn root, already rendered."""
    root = withdrawn_root()
    vps = _fake_week_vps(left_rows, right_rows)
    app = SimpleNamespace(vps_manager=vps)
    if settings is not None:
        app.settings = settings
    screen = WeeklyItemsScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _button_texts(frame):
    """The text of every CTkButton anywhere under a frame, in child order."""
    out = []
    for child in frame.winfo_children():
        if isinstance(child, ctk.CTkButton):
            out.append(child.cget("text"))
        else:
            out.extend(_button_texts(child))
    return out


def test_updm56_week_assignment_body_is_left_divider_right():
    """UPD-M5.6 — the body and the divider, pinned before the move.

    Characterisation, in the sense this file opens with: the screen already
    has the three-column body and the three divider bindings, and the move
    onto split_panel must not change either. `<ButtonPress-1>` and
    `<Button-1>` are one event in Tk and `bind()` reports the canonical name,
    so this holds before the move, where the screen binds the long form, and
    after, where split_panel binds the short one.
    """
    root, screen = _week_screen()
    try:
        body = screen.body
        assert int(screen.left_frame.grid_info()["column"]) == 0
        assert int(screen.right_frame.grid_info()["column"]) == 2
        assert body.grid_columnconfigure(1).get("minsize") == split_panel.SPLITTER_WIDTH

        divider = [c for c in body.winfo_children()
                   if c.grid_info() and int(c.grid_info()["column"]) == 1][0]
        bound = set(_bound_sequences(divider))
        assert {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"} <= bound
    finally:
        root.destroy()


def test_updm56_both_panels_still_say_when_they_are_empty():
    """UPD-M5.6 — neither empty state is lost to the move (P2).

    Both are the only thing on screen that distinguishes "this week has
    nothing in it" from "the filters hid everything", and the shared table
    renders a bare header for both. The table owns its container outright, so
    each label has to move to a sibling frame rather than be dropped.

    The labels are built in `create_ui` and only gridded or un-gridded as the
    panel fills, so their *existence* says nothing: an earlier version of this
    test read the text off a label that had been removed from the grid and
    passed with the two branches swapped. What is asserted is which of the two
    widgets in that cell is gridded.
    """
    root, screen = _week_screen()
    try:
        for message, listing in ((screen.left_empty, screen.left_list),
                                 (screen.right_empty, screen.right_list)):
            assert message.grid_info(), f"{message.cget('text')} is not on screen"
            assert not listing.grid_info(), "the empty list is still taking the space"
        assert "No month-assigned Annual Plan Elements" in screen.left_empty.cget("text")
        assert "No weekly tactics exist" in screen.right_empty.cget("text")
    finally:
        root.destroy()

    root, screen = _week_screen(left_rows=[_ape_row(1)],
                                right_rows=[_weekly_row(1)])
    try:
        for message, listing in ((screen.left_empty, screen.left_list),
                                 (screen.right_empty, screen.right_list)):
            assert listing.grid_info(), "the list is not on screen"
            assert not message.grid_info(), (
                f"{message.cget('text')} is shown over a panel that has rows")
    finally:
        root.destroy()


def test_updm54_the_bottom_row_is_one_add_and_the_selection_still_works():
    """UPD-M5.4, as VTF-M5 left it: one button below the list.

    UPD-M5.4 kept Edit Weekly Tactic, Delete Weekly and Add Action Item below
    the list because they act on the *selected* tactic. The user withdrew all
    three on 2026-11-11: the first two were second routes to the row's own
    double-click and Delete, and the third created an Action Item this panel
    cannot show. **Add Weekly Tactic** is what sits there now (VTF-M5.4).

    What UPD-M5.4 still asserts is the half that survives: selecting a row
    sets both the item and the index, and `open_selected_weekly_item` -- now
    reached by double-click rather than by a button -- still warns when there
    is no selection instead of opening an editor on nothing.
    """
    import src.getmoredone.screens.weekly_items as wi

    root, screen = _week_screen(right_rows=[_weekly_row(1)])
    warned = []
    original = wi.messagebox.showwarning
    wi.messagebox.showwarning = lambda title, msg: warned.append(title)
    try:
        actions_bar = [c for c in screen.right_frame.winfo_children()
                       if c.grid_info() and int(c.grid_info()["row"]) == 1][0]
        assert _button_texts(actions_bar) == ["Add Weekly Tactic"]

        screen.selected_weekly_item = None
        screen.open_selected_weekly_item()
        assert warned == ["No Weekly Item Selected"]

        screen.on_select_weekly_item(0)
        assert screen.selected_weekly_item["id"] == "wt-1"
        assert screen.selected_weekly_idx == 0
    finally:
        wi.messagebox.showwarning = original
        root.destroy()


def test_updm57_clicking_a_right_row_selects_it_and_double_click_opens_it():
    """UPD-M5.7 — the selection tint and double-click-to-open survive.

    Both are on every widget of the row, frame and cells alike, and both have
    to be re-bound by hand after the move: the shared table knows nothing
    about selection. The tint is asserted as the theme's own token, so a
    rewrite that tinted with a literal would fail.
    """
    root, screen = _week_screen(right_rows=[_weekly_row(1), _weekly_row(2)])
    try:
        rows = _row_frames(screen.right_list)
        assert len(rows) == 2
        # Every widget of the row but its Delete button: a click on Delete
        # opens the confirmation, not the selection, so it is deliberately
        # not a selection handle (UPD-M5.2).
        clickable = [rows[0]] + [c for c in rows[0].winfo_children()
                                 if not isinstance(c, ctk.CTkButton)]
        # Five cells since WTP-M6.4 added Done, plus the row frame itself.
        assert len(clickable) == 6
        for widget in clickable:
            bound = set(_bound_sequences(widget))
            assert "<Button-1>" in bound
            assert "<Double-Button-1>" in bound

        screen.on_select_weekly_item(1)
        screen.update_idletasks()
        tint = chip_table.semantic_colors()["selected_tint"]
        assert _topmost_at_grid_row(screen.right_list, 2).cget("fg_color") == tint
        assert _topmost_at_grid_row(screen.right_list, 1).cget("fg_color") != tint
    finally:
        root.destroy()


def test_updm57_selecting_a_row_repaints_the_panel_instead_of_stacking_it():
    """UPD-M5.7 — a selection click must not leave the old rows behind.

    `on_select_weekly_item` re-renders the right panel to move the tint, and
    before UPD-M5 it did so without destroying what was there: both headers
    and both sets of rows ended up gridded in the same cells, one on top of
    the other, and every further click added another set. The shared table
    clears its container in `build_header`, which is what fixes it, so this
    counts the children rather than trusting that.
    """
    root, screen = _week_screen(right_rows=[_weekly_row(1), _weekly_row(2)])
    try:
        before = len(screen.right_list.winfo_children())
        for idx in (0, 1, 0):
            screen.on_select_weekly_item(idx)
            screen.update_idletasks()
        assert len(screen.right_list.winfo_children()) == before, (
            "three selection clicks left extra row frames stacked in the panel"
        )
    finally:
        root.destroy()


def test_updm51_right_panel_has_the_actions_column():
    """UPD-M5.1 — `#` / Segment / SubSegment / Category / Done / Actions.

    The right panel had four columns and three buttons in a bar below the
    list; the image has a fifth column with the row's own Delete in it. The
    widths are the other APE tabs' now, not this screen's old 180s, which is
    the alignment the request asked for and the part of it that is a visible
    change rather than a move.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)],
                               right_rows=[_weekly_row(1)])
    try:
        right = _header_frame(screen.right_list)
        # WTP-M6.4 put a Done column before Actions, and gave this panel a
        # column set of its own: its rows are Weekly Tactics, so they have
        # children to count, which the other two APE right panels' rows do
        # not. The set is still pinned exactly, including the new width.
        assert [text for _col, _cls, text in _cells(right)] == [
            "#", "Segment", "SubSegment", "Category", "Done", "Actions"]
        assert _minsizes(right, (0, 1, 2, 3, 4, 5)) == [34, 135, 155, 125, 70, 84]
    finally:
        root.destroy()


def test_updm55_left_header_matches_the_other_tabs():
    """UPD-M5.5 — the left header is the one the other three tabs have.

    UPD-M5.5 blanked this cell to match them: this tab said "Pick" in a 52px
    column where the others had nothing over the checkboxes. **UPD-F3 reverses
    the text half of that**, on all four panels at once and at 34px, because
    the on-screen walk asked for a word over the ticks — case (b), the
    behaviour changed intentionally. What UPD-M5.5 was really pinning survives
    and is still asserted: the width, and that the four panels agree. The
    header is asserted as text *and* pixels because a cell that was merely
    blanked would leave the row's cells one place to the right of the other
    tabs'.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        left = _header_frame(screen.left_list)
        assert [text for _col, _cls, text in _cells(left)] == [
            "Pick", "#", "Segment", "SubSegment", "Category"]
        assert _minsizes(left, (0, 1, 2, 3, 4)) == [34, 34, 135, 155, 125]

        row = _row_frames(screen.left_list)[0]
        assert [cls for _col, cls, _text in _cells(row)][0] == "CTkCheckBox"
    finally:
        root.destroy()


def test_updm52_a_row_delete_removes_that_row_not_the_selection():
    """UPD-M5.2 — the row's Delete deletes the row it is on.

    The screen already had a Delete that acted on the selection, so a per-row
    button wired to the selection instead of its own row would look right and delete
    the wrong tactic. Row 2's button is pressed with row 1 selected, and the
    id the manager is given is the assertion.
    """
    import src.getmoredone.screens.weekly_items as wi

    root, screen = _week_screen(right_rows=[_weekly_row(1), _weekly_row(2)])
    original = wi.messagebox.askyesno
    wi.messagebox.askyesno = lambda *_a, **_k: True
    try:
        screen.on_select_weekly_item(0)
        assert screen.selected_weekly_item["id"] == "wt-1"

        second_row = _row_frames(screen.right_list)[1]
        delete = [c for c in second_row.winfo_children()
                  if isinstance(c, ctk.CTkButton)][0]
        assert delete.cget("text") == "Delete"
        delete.invoke()

        assert ("delete", "wt-2") in screen.vps_manager.calls, screen.vps_manager.calls
        assert ("delete", "wt-1") not in screen.vps_manager.calls
    finally:
        wi.messagebox.askyesno = original
        root.destroy()


def test_updm53_delete_is_confirmed_before_it_happens():
    """UPD-M5.3 — a refused confirmation deletes nothing.

    This drove two callers, the row's Delete and Delete Weekly. VTF-M5 removed
    the Delete Weekly button and VTF-A2 its method, so the row's path is the
    only one left to drive (case (b): the behaviour changed on purpose).
    """
    import src.getmoredone.screens.weekly_items as wi

    root, screen = _week_screen(right_rows=[_weekly_row(1)])
    asked = []
    original = wi.messagebox.askyesno
    wi.messagebox.askyesno = lambda title, msg, **_k: asked.append(msg) or False
    try:
        screen.delete_weekly_row({"id": "wt-1", "title": "Tactic 1"})

        assert len(asked) == 1, asked
        assert all("Tactic 1" in msg for msg in asked), asked
        assert not any(call[0] == "delete" for call in screen.vps_manager.calls), (
            screen.vps_manager.calls
        )
    finally:
        wi.messagebox.askyesno = original
        root.destroy()


def test_updm56_week_assignment_uses_the_shared_table_and_module_wiring():
    """UPD-M5.6 — both panels are ChipTables, under this screen's own prefixes.

    And the splitter and the drag source are the shared ones, pointed at the
    right widgets: a `SplitPanel` built over the wrong frame, or a
    `RowDragSource` pointed at the panel frame rather than the list, would
    pass every rendering assertion above and misbehave only under the mouse.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)], right_rows=[_weekly_row(1)])
    try:
        assert isinstance(screen.left_table, chip_table.ChipTable)
        assert isinstance(screen.right_table, chip_table.ChipTable)
        assert screen.left_table.prefix == "week_assignment_left"
        assert screen.right_table.prefix == "week_assignment_right"
        assert screen.left_table.container is screen.left_list
        assert screen.right_table.container is screen.right_list

        assert isinstance(screen.split, split_panel.SplitPanel)
        assert screen.split.left_panel is screen.left_frame
        assert screen.split.prefix == "week_assignment"

        assert isinstance(screen.row_drag, row_drag.RowDragSource)
        assert screen.row_drag.drop_target is screen.right_list
        assert screen.row_drag.on_drop == screen._assign_dragged_row
    finally:
        root.destroy()


def test_updm56_week_assignment_columns_resize_and_persist():
    """UPD-M5.6 — a drag on either panel is kept, and the panels are separate.

    The two panels were one set of class constants, so neither could be sized
    without the other. They have their own stores now, and the test drags one
    and asserts the other did not move, then rebuilds the screen from the same
    settings object and reads the width back.
    """
    settings = FakeSettings(
        week_assignment_left_col_widths={},
        week_assignment_right_col_widths={},
        week_assignment_split_ratio=0.5,
    )
    root, screen = _week_screen(left_rows=[_ape_row(1)],
                                right_rows=[_weekly_row(1)], settings=settings)
    try:
        _resize(screen.left_table, "segment", 40)
        assert screen.left_table.width("segment") == 175
        assert screen.right_table.width("segment") == 135
        assert settings.week_assignment_left_col_widths["segment"] == 175
        assert "segment" not in settings.week_assignment_right_col_widths
    finally:
        root.destroy()

    root, screen = _week_screen(left_rows=[_ape_row(1)],
                                right_rows=[_weekly_row(1)], settings=settings)
    try:
        assert screen.left_table.width("segment") == 175
        assert _minsizes(_header_frame(screen.left_list), (2,)) == [175]
        # And the right panel is still at its default on the new build. The
        # in-memory check above cannot see a shared store: a right table built
        # on the left prefix reads it before the drag happens and holds 135
        # for the rest of that session. Only the next build loads the width
        # the drag wrote, which is where two panels on one store show.
        assert screen.right_table.width("segment") == 135
        assert _minsizes(_header_frame(screen.right_list), (1,)) == [135]
    finally:
        root.destroy()


def test_updm56_the_week_assignment_prefixes_have_settings_fields():
    """UPD-M5.6 — and the three fields the screen writes to are declared.

    `ColumnResizer._persist` setattrs the attribute and calls `save()`, which
    writes declared dataclass fields only, so an undeclared field is kept for
    the session and silently gone at the next launch. Same guard as UPD-M4.4's,
    extended to this screen.
    """
    names = {f.name for f in dataclasses.fields(AppSettings)}
    prefix = WeeklyItemsScreen.SETTINGS_PREFIX
    assert prefix == "week_assignment"
    assert f"{prefix}_split_ratio" in names
    assert getattr(AppSettings(), f"{prefix}_split_ratio") == 0.5
    for side in ("left", "right"):
        field_name = f"{prefix}_{side}_col_widths"
        assert field_name in names, field_name
        assert getattr(AppSettings(), field_name) == {}


def test_updm56_a_left_row_is_a_drag_source_on_this_tab_too():
    """UPD-M5.6 — the left rows are bound to the shared drag, cells included.

    The frame and its four cells, not the checkbox: a click on the checkbox
    ticks it. Dragging is one-way, so nothing on a left row is bound to the
    selection handlers the right rows carry.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)], right_rows=[_weekly_row(1)])
    try:
        left_row = _row_frames(screen.left_list)[0]
        draggable = [left_row] + [c for c in left_row.winfo_children()
                                  if not isinstance(c, ctk.CTkCheckBox)]
        assert len(draggable) == 5
        for widget in draggable:
            assert "<Button-1>" in set(_bound_sequences(widget))
        assert "<Double-Button-1>" not in set(_bound_sequences(left_row))
    finally:
        root.destroy()


def test_updm56_a_row_with_no_category_colour_takes_the_subsegments():
    """UPD-M5.6 — the two render methods' colour lookup is one method now.

    Both panels resolved lineage colours with the same four lines, including a
    three-part lower-cased category key that is easy to get subtly wrong in
    one copy and not the other. `_row_colors` is that code once; this drives
    it through both panels and asserts the fallback, which is the branch a
    typo'd key would silently take on every row.

    Changed 2026-11-11 for SCV-M6.3, reason (b), the behaviour changed
    intentionally: ``_normalize_color`` returns the canonical ``#RRGGBB``
    form, where it used to return the stored text with whitespace stripped.
    What this test is about is which key the lookup takes, not the case the
    colour comes back in, and no consumer in ``src/`` compares one of these
    values by equality.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)], right_rows=[_weekly_row(1)])
    try:
        screen.segment_colors = {}
        screen.subsegment_colors = {("purposeful work", "living systems"): "#4477aa"}
        screen.category_colors = {}
        seg, sub, cat = screen._row_colors(
            "Purposeful Work", "Living Systems", "Blog")
        assert sub == "#4477AA"
        assert cat == sub, "a category with no colour of its own takes the subsegment's"

        screen.category_colors = {
            ("purposeful work", "living systems", "blog"): "#cc7744"}
        _seg, _sub, cat = screen._row_colors(
            "Purposeful Work", "Living Systems", "Blog")
        assert cat == "#CC7744"
    finally:
        root.destroy()


# ---------------------------- UPD-M6: APE Week Actions gets the design it can take
#
# The two tests that open this section are **characterisation** tests in the
# sense this file's docstring describes: both were written and run green
# against `week_actions.py` as it stood, before a line of it was changed, and
# both must still be green after. They hold the two things UPD-M6 must not
# disturb -- the right panel's own column store (M6.6) and the absence of a
# drag on this tab (M6.7, D6).

def _week_actions_screen(tmp_path, vps, settings=None, first_day=0):
    """APE Week Actions on a withdrawn root, already rendered.

    Takes a real `VPSManager` on a temporary database rather than a double:
    the right panel is a `TodayScreen` subclass and queries items for real.
    """
    from src.getmoredone.screens.week_actions import WeekActionsScreen
    root = withdrawn_root()
    app = SimpleNamespace(
        vps_manager=vps,
        db_manager=vps.db_manager,
        settings=settings if settings is not None else FakeSettings(
            first_day_of_week=first_day,
            week_actions_left_col_widths={},
            week_actions_split_ratio=0.5,
        ),
    )
    if settings is not None and not hasattr(settings, "first_day_of_week"):
        settings.first_day_of_week = first_day
    screen = WeekActionsScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _this_monday() -> str:
    from src.getmoredone import week_options
    return week_options.week_start_for(date.today(), 0).isoformat()


def test_updm66_right_panel_is_untouched(tmp_path):
    """UPD-M6.6 — the Actions panel's widths are read from `week_actions`.

    Characterisation, written before the change: the right panel is a
    `TodayScreen` subclass and already has draggable, persisted widths under
    its own prefix (AWA-M5.5). UPD-M6 adds a left-hand table with a prefix of
    its own, and the failure to guard against is the new prefix replacing this
    one -- a rename would discard every width a user has already set, with
    nothing on screen to say so.

    The width is seeded in the real settings file (conftest redirects it to a
    temporary path) rather than in a double, because that is the object
    `TodayScreen.__init__` loads.
    """
    from src.getmoredone.screens.week_actions import WeekTacticActionsPanel

    assert WeekTacticActionsPanel.COLUMN_PREFIX == "week_actions"

    stored = AppSettings.load()
    stored.week_actions_col_widths = {"title": 362}
    stored.save()

    vps = make_vps(tmp_path)
    try:
        root, screen = _week_actions_screen(tmp_path, vps)
        try:
            panel = screen.actions_panel
            assert panel.resizer.prefix == "week_actions"
            assert panel.resizer._setting_attr() == "week_actions_col_widths"
            assert panel.resizer.width("title") == 362
        finally:
            root.destroy()
    finally:
        vps.close()


def test_updm67_no_dead_drop_target():
    """UPD-M6.7 — nothing on this tab binds a drag or builds a drop target.

    D6: the right panel is the *contents* of the row selected on the left, not
    a second collection, so a drop has nothing it could mean. The guard is an
    exact count of 0 over the parsed module rather than a floor, and it names
    every spelling the other five tabs use, so a drag added here by copying a
    sibling screen fails this rather than silently doing nothing.
    """
    tree = ast.parse((SRC / "screens" / "week_actions.py").read_text())
    names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } | {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    forbidden = {
        "RowDragSource", "row_drag", "bind_row", "dragged_row",
        "_start_row_drag", "_finish_row_drag", "_bind_drag_widgets",
        "winfo_pointerxy", "winfo_containing", "_is_descendant",
        "drop_target",
    }
    assert names & forbidden == set()


def _week_actions_with(tmp_path, titles_and_lineage, settings=None):
    """APE Week Actions holding one Weekly Tactic per entry, in this week.

    Each entry is (title, subsegment, key_field); a distinct pair of those two
    is a distinct lineage, which is what the filters sort rows by.
    """
    vps = make_vps(tmp_path)
    week = _this_monday()
    for title, subsegment, key_field in titles_and_lineage:
        ape = seed_ape(vps, subsegment=subsegment, key_field=key_field)
        make_week_item(vps, ape, start=week, due=week, title=title)
    root, screen = _week_actions_screen(tmp_path, vps, settings=settings)
    return vps, root, screen


def _tactic_row(screen, index=0):
    """The index-th rendered row frame of the left panel, in grid order."""
    return _row_frames(screen.left_list)[index]


def _click(widget):
    """Generate a real `<Button-1>` where the binding actually lives.

    A CustomTkinter widget forwards `bind` to an internal canvas, so an event
    generated on the widget itself reaches no handler. Driving the canvas is
    what makes this a click rather than a direct call to the handler the test
    is supposed to be checking the row is wired to.
    """
    target = getattr(widget, "_canvas", widget)
    target.event_generate("<Button-1>", x=2, y=2)


def _row_id_for(screen, title):
    """The id of the visible row with this title, whatever order they are in.

    `get_weekly_action_items` does not promise an order, and a test that
    indexes into the list is asserting one it was never given.
    """
    return next(row["id"] for row in screen.visible_rows
                if (row.get("title") or "") == title)


def test_updm61_week_actions_has_a_divider(tmp_path):
    """UPD-M6.1 — a draggable divider, where the split was a fixed minimum.

    The body was `minsize=380` on the left and `weight=1` on the right, so
    the proportion was the layout's and not the user's. The three divider
    bindings and the body's `<Configure>` are split_panel's, and the ratio
    lands in a declared field, which is the difference between a divider that
    is remembered and one that silently is not.
    """
    import dataclasses as _dc

    declared = {f.name for f in _dc.fields(AppSettings)}
    assert "week_actions_split_ratio" in declared
    assert "week_actions_left_col_widths" in declared

    vps, root, screen = _week_actions_with(tmp_path, [("one", "Living Systems", "Blog")])
    try:
        assert isinstance(screen.split, split_panel.SplitPanel)
        assert screen.split.prefix == "week_actions"
        assert screen.split.setting_attr() == "week_actions_split_ratio"
        assert screen.split.left_panel is screen.left_frame
        assert int(screen.left_frame.grid_info()["column"]) == 0
        assert int(screen.divider.grid_info()["column"]) == 1
        assert int(screen.actions_panel.grid_info()["column"]) == 2
        assert screen.body.grid_columnconfigure(1).get("minsize") == (
            split_panel.SPLITTER_WIDTH)

        bound = _bound_sequences(screen.divider)
        for sequence in ("<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"):
            assert sequence in bound, bound
        assert "<Configure>" in _bound_sequences(screen.body)
    finally:
        root.destroy()
        vps.close()


def test_updm61_the_divider_position_survives_a_relaunch(tmp_path):
    """UPD-M6.1 / UPD-D4 — a dragged divider is still there on the next build."""
    settings = FakeSettings(
        first_day_of_week=0,
        week_actions_split_ratio=0.5,
        week_actions_left_col_widths={},
    )
    vps, root, screen = _week_actions_with(
        tmp_path, [("one", "Living Systems", "Blog")], settings=settings)
    try:
        screen.body.update_idletasks()
        screen.split.ratio = 0.62
        screen.split._drag_start_x = 10
        screen.split.on_release()
        assert settings.week_actions_split_ratio == 0.62
        assert settings.saved >= 1
    finally:
        root.destroy()

    try:
        root, screen = _week_actions_screen(tmp_path, vps, settings=settings)
        try:
            assert screen.split.ratio == 0.62
        finally:
            root.destroy()
    finally:
        vps.close()


def test_updm62_left_panel_is_the_shared_table(tmp_path):
    """UPD-M6.2 — a header and chip rows, where it was a stack of buttons.

    The left panel used to be one `CTkButton` per tactic with the title and
    the segment name on two lines inside it. It is the shared table now, with
    a Title column this tab needs -- its rows are picked by name -- and the
    three chip columns at the same widths as the other panels', every one of
    them draggable.
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        ("first", "Living Systems", "Blog"),
        ("second", "Other Systems", "Podcast"),
    ])
    try:
        assert isinstance(screen.left_table, chip_table.ChipTable)
        assert screen.left_table.prefix == "week_actions_left"
        assert screen.left_table.columns == list(
            chip_table.WEEK_ACTIONS_LEFT_COLUMNS)

        header = _header_frame(screen.left_list)
        # WTP-M6.5 added the Done column; the set is still pinned exactly.
        assert [cell[2] for cell in _cells(header)] == [
            "#", "Weekly Tactic", "Segment", "SubSegment", "Category", "Done"]
        assert _minsizes(header, (0, 1, 2, 3, 4, 5)) == [34, 220, 135, 155, 125, 70]

        rows = _row_frames(screen.left_list)
        assert len(rows) == 2
        assert [_cells(row)[0][2] for row in rows] == ["1", "2"]
        assert [_cells(row)[1][2].strip() for row in rows] == ["first", "second"]
        # No CTkButton anywhere in the panel: the stack of them is gone.
        assert _button_texts(screen.left_list) == []
    finally:
        root.destroy()
        vps.close()


def test_updm62_a_long_title_is_clipped_to_its_column(tmp_path):
    """UPD-M6.2 — a plain resizable cell is clamped at the first render.

    `add_row` gave a non-chip cell its raw text, which only the resizer's
    first drag then clamped. On a Title column that is a panel that opens
    with one row pushing every column out of line and corrects itself when
    the handle is touched. The `#` column is fixed-width and keeps its raw
    text, because the resizer never re-clamps a column with no handle.
    """
    vps, root, screen = _week_actions_with(
        tmp_path, [("x" * 400, "Living Systems", "Blog")])
    try:
        cells = _cells(_tactic_row(screen))
        index_text, title_text = cells[0][2], cells[1][2]
        budget = screen.left_table.resizer.chars("title")
        assert len(title_text) < 400
        assert len(title_text.strip()) <= budget
        assert index_text == "1"
    finally:
        root.destroy()
        vps.close()


def test_updm63_clicking_a_row_still_selects(tmp_path):
    """UPD-M6.3 — a click anywhere in the row selects that tactic.

    The button carried the click before; the row's cells carry it now. Every
    cell is asserted, not just the frame: a click lands on the widget under
    the pointer, and a row that only selects at its edges is a row that looks
    broken at random.
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        ("first", "Living Systems", "Blog"),
        ("second", "Other Systems", "Podcast"),
    ])
    try:
        rows = _row_frames(screen.left_list)
        clickable = [rows[1]] + [
            child for child in rows[1].winfo_children()
            if not _is_resize_handle(child)
        ]
        # Six cells since WTP-M6.5 added Done, plus the row frame itself.
        assert len(clickable) == 7
        for widget in clickable:
            assert "<Button-1>" in _bound_sequences(widget), widget

        second_id = _row_id_for(screen, "second")
        second_index = [row["id"] for row in screen.visible_rows].index(second_id)
        _click(_row_frames(screen.left_list)[second_index])
        assert screen.selected_tactic_id == second_id
        assert screen.actions_panel.selected_tactic["id"] == second_id

        tint = chip_table.semantic_colors()["selected_tint"]
        repainted = _row_frames(screen.left_list)
        assert repainted[second_index].cget("fg_color") == tint
        assert repainted[1 - second_index].cget("fg_color") != tint
    finally:
        root.destroy()
        vps.close()


def test_updm63_selecting_a_row_repaints_the_panel_instead_of_stacking_it(tmp_path):
    """UPD-M6.3 — three clicks leave three rows, not nine.

    The lesson from UPD-M5, applied to the screen that re-renders on every
    click: `build_header` clears its container, so a repaint replaces the
    panel rather than gridding a second copy into the same cells. Two widgets
    in one Tk cell both stay mapped and the later one is drawn on top, so the
    stacked case looks right on screen and is only visible as a child count.
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        ("first", "Living Systems", "Blog"),
        ("second", "Other Systems", "Podcast"),
    ])
    try:
        before = len(screen.left_list.winfo_children())
        assert before == 3  # one header, two rows
        for _ in range(3):
            _click(_tactic_row(screen, 0))
        assert len(screen.left_list.winfo_children()) == before
        assert len(screen.tactic_row_frames) == 2
    finally:
        root.destroy()
        vps.close()


def test_updm64_filters_narrow_the_tactic_list(tmp_path):
    """UPD-M6.4 — the three filters this tab did not have, and the counts.

    The other five tabs all filter by Segment / SubSegment / Category. The
    left list, its heading and the status line all report what the filter
    left: a narrowed list with an unchanged count is a screen that looks like
    it lost rows.
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        # Two rows in one subsegment, so the subsegment filter has something
        # to keep and something to hide. They need different key fields: one
        # Annual Plan Element cannot carry two Weekly Tactics in the same week
        # (a unique constraint).
        ("blog one", "Living Systems", "Blog"),
        ("blog two", "Living Systems", "Essay"),
        ("a podcast", "Other Systems", "Podcast"),
    ])
    try:
        assert len(screen.visible_rows) == 3
        assert screen.left_title_label.cget("text") == "Weekly Tactics (3)"

        screen.filters.subsegment_var.set("Other Systems")
        screen.on_filters_changed()

        assert [row["title"] for row in screen.visible_rows] == ["a podcast"]
        assert len(_row_frames(screen.left_list)) == 1
        assert screen.left_title_label.cget("text") == "Weekly Tactics (1 of 3)"
        status = screen.status_label.cget("text")
        assert status.startswith("1 of 3 Weekly Tactic(s) for week of ")
        assert "2 hidden by Sub Other Systems." in status

        screen.filters.reset()
        screen.on_filters_changed()
        assert len(screen.visible_rows) == 3
        assert screen.left_title_label.cget("text") == "Weekly Tactics (3)"
    finally:
        root.destroy()
        vps.close()


def test_updm64_the_combos_offer_only_the_values_the_week_has(tmp_path):
    """UPD-M6.4 — and a selection the new week cannot match falls back to All.

    A filter left pointing at a value the combo no longer lists is a panel
    that is empty for a reason the screen does not show (P2).
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        ("blog one", "Living Systems", "Blog"),
        ("a podcast", "Other Systems", "Podcast"),
    ])
    try:
        assert screen.filters.subsegment_combo.cget("values") == [
            "All", "Living Systems", "Other Systems"]
        assert screen.filters.category_combo.cget("values") == [
            "All", "Blog", "Podcast"]

        screen.filters.subsegment_var.set("Other Systems")
        screen.on_filters_changed()
        assert len(screen.visible_rows) == 1

        # A week with none of that subsegment in it.
        other_week = (date.fromisoformat(_this_monday())
                      + timedelta(days=70)).isoformat()
        screen.week_var.set(other_week)
        screen.load_selected_week()
        assert screen.filters.subsegment_var.get() == "All"
    finally:
        root.destroy()
        vps.close()


def test_updm64_a_filter_that_hides_the_selected_row_clears_the_panel(tmp_path):
    """UPD-M6.4 — the selection survives a filter unless the filter hides it.

    Filtering is not a week change, so a selected tactic that is still listed
    stays selected and the right panel keeps its items. One that the filter
    has hidden is cleared, because its Action Items beside a list that does
    not contain it is the confusion AWA-M4.5 exists to prevent.
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        ("blog one", "Living Systems", "Blog"),
        ("a podcast", "Other Systems", "Podcast"),
    ])
    try:
        kept = _row_id_for(screen, "a podcast")
        screen.select_tactic(kept)

        screen.filters.subsegment_var.set("Other Systems")
        screen.on_filters_changed()
        assert screen.selected_tactic_id == kept
        assert screen.actions_panel.selected_tactic["id"] == kept

        screen.filters.subsegment_var.set("Living Systems")
        screen.on_filters_changed()
        assert screen.selected_tactic_id is None
        assert screen.actions_panel.selected_tactic is None
    finally:
        root.destroy()
        vps.close()


def test_updm65_an_empty_filter_result_says_what_it_hid(tmp_path):
    """UPD-M6.5 — an empty week and a filter that hid everything differ (P2).

    Asserts which of the two widgets in that grid cell is gridded, not only
    what the label says: both are built once and only gridded and un-gridded,
    so a test that read the text alone would stay green with the branch
    inverted. That is the UPD-M5 finding, applied here.
    """
    vps, root, screen = _week_actions_with(tmp_path, [
        ("blog one", "Living Systems", "Blog"),
    ])
    try:
        assert screen.left_list.winfo_viewable() or screen.left_list.grid_info()
        assert screen.left_empty.grid_info() == {}

        screen.filters.subsegment_var.set("Other Systems")
        screen.filters.subsegment_combo.configure(
            values=["All", "Living Systems", "Other Systems"])
        screen.on_filters_changed()

        assert screen.visible_rows == []
        assert screen.left_list.grid_info() == {}
        assert screen.left_empty.grid_info() != {}
        text = screen.left_empty.cget("text")
        assert "No Weekly Tactics match the filter" in text
        assert "Sub Other Systems" in text
        assert "1 hidden." in text
        assert screen.left_title_label.cget("text") == "Weekly Tactics (0 of 1)"
    finally:
        root.destroy()
        vps.close()


def test_updm65_an_empty_week_says_that_instead(tmp_path):
    """UPD-M6.5 — with no tactics at all the message is about the week."""
    vps = make_vps(tmp_path)
    try:
        root, screen = _week_actions_screen(tmp_path, vps)
        try:
            assert screen.tactic_rows == []
            assert screen.left_empty.grid_info() != {}
            assert screen.left_empty.cget("text") == (
                "No Weekly Tactics for this week.")
            assert screen.left_title_label.cget("text") == "Weekly Tactics (0)"
        finally:
            root.destroy()
    finally:
        vps.close()


def test_updm66_the_left_panel_columns_resize_and_persist(tmp_path):
    """UPD-M6.6 — the left panel's own store, and the right panel's untouched.

    The right panel has had draggable widths since AWA-M5.5 under the
    `week_actions` prefix. The left panel's drag has to land somewhere else,
    or sizing one would move the other and a user's existing widths would be
    read with the wrong keys.
    """
    settings = FakeSettings(
        first_day_of_week=0,
        week_actions_split_ratio=0.5,
        week_actions_left_col_widths={},
        week_actions_col_widths={"title": 300},
    )
    vps, root, screen = _week_actions_with(
        tmp_path, [("one", "Living Systems", "Blog")], settings=settings)
    try:
        assert screen.left_table.resizer._setting_attr() == (
            "week_actions_left_col_widths")
        _resize(screen.left_table, "segment", 40)
        assert screen.left_table.width("segment") == 175
        assert settings.week_actions_left_col_widths["segment"] == 175
        # The Actions panel's store is loaded from the real settings file, not
        # from this double, so the assertion that matters here is that the
        # left panel wrote nowhere near it.
        assert settings.week_actions_col_widths == {"title": 300}
    finally:
        root.destroy()

    try:
        root, screen = _week_actions_screen(tmp_path, vps, settings=settings)
        try:
            assert screen.left_table.width("segment") == 175
            assert _minsizes(_header_frame(screen.left_list), (2,)) == [175]
        finally:
            root.destroy()
    finally:
        vps.close()


def test_updm62_a_row_with_no_category_colour_takes_the_subsegments(tmp_path):
    """UPD-M6.2 — the shared chip-colour resolver, on this tab's rows.

    The category chip falls back to the subsegment's colour rather than
    rendering as a hole, which is `resolve_chip_colors`' contract and the
    reason `week_actions` calls it instead of writing a sixth copy of the
    three-part lookup.

    Changed 2026-11-11 for SCV-M6.3, reason (b), the behaviour changed
    intentionally: the category colour now goes through `_normalize_color`
    like the other two, so it comes back as the canonical `#RRGGBB`. Which
    key the lookup takes, and what it falls back to, are unchanged.
    """
    from src.getmoredone.screens.segment_color_utils import resolve_chip_colors

    vps_double = SimpleNamespace(
        resolve_segment_color=lambda name, colors: "#112233",
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_vision_categories=lambda: [],
    )
    seg, sub, cat = resolve_chip_colors(
        "Purposeful Work", "Living Systems", "Blog", vps_double,
        {}, {("purposeful work", "living systems"): "#445566"}, {},
    )
    assert (seg, sub, cat) == ("#112233", "#445566", "#445566")

    seg, sub, cat = resolve_chip_colors(
        "Purposeful Work", "Living Systems", "Blog", vps_double,
        {}, {("purposeful work", "living systems"): "#445566"},
        {("purposeful work", "living systems", "blog"): "#cc7744"},
    )
    assert cat == "#CC7744"


# ------------------------------------- UPD-M7: it holds together on screen
#
# M7.2 and M7.3 cannot be met by a test and are not written as one: they are
# the on-screen checklist in the spec's §11, walked by a person in the running
# app. The two below are M7.1, the part of "it holds together" that code can
# hold: that none of the rewritten panels needs a window on screen to be
# built, and that this batch did not add a test that takes one.

THIS_FILE = Path(__file__).resolve()


def _toplevels_under(widget) -> list:
    """Every Toplevel anywhere beneath a widget, depth first.

    `winfo_class()` rather than `isinstance`: `ctk.CTkToplevel` and
    `tk.Toplevel` both report "Toplevel", and a dialog a screen opens may be
    either. Recursive rather than a pass over the root's own children,
    because a screen builds three or four frames deep before it opens
    anything — the mutation for this walks a dialog in at `left_frame`, which
    is `root` → screen → `body` → `left_frame`.
    """
    found = []
    for child in widget.winfo_children():
        if child.winfo_class() == "Toplevel":
            found.append(str(child))
        found.extend(_toplevels_under(child))
    return found


def test_updm71_screens_construct_withdrawn(tmp_path):
    """UPD-M7.1 — the five rewritten tabs build without a window of their own.

    A full run builds real Tk windows on purpose, and on macOS a mapped one
    raises itself and takes the keyboard — `tests/test_tk_offscreen.py`'s
    docstring has the shape of it. UPD-M1 through UPD-M6 rewrote the
    construction path of all five of these screens, and a dialog opened while
    one is being built is a modal thrown over whoever is using the machine,
    once per test that builds that screen. The Toplevel count is this test's
    failable claim: exact 0, walked to the bottom of each widget tree, so a
    dialog opened three frames down still counts.

    The two assertions above it are weaker on purpose and are stated as what
    they are: `conftest.py` withdraws every window at construction and
    re-withdraws after any `deiconify`, so these hold whatever a screen does.
    `tests/test_tk_offscreen.py` is the guard on that guard (P24); what is
    asserted here is that the five rewritten construction paths are inside it.

    `vision_segments.py` is not here: it is out of scope by UPD-D8 and was not
    touched.
    """
    vps = make_vps(tmp_path)
    builders = (
        ("ape_assignment", lambda: _quarter_screen()),
        ("ape_period_view", lambda: _month_screen()),
        ("annual_vision_segments", lambda: _annual_screen()),
        ("weekly_items", lambda: _week_screen()),
        ("week_actions", lambda: _week_actions_screen(tmp_path, vps)),
    )
    try:
        for name, build in builders:
            root, screen = build()
            try:
                assert root.wm_state() == "withdrawn", name
                assert screen.winfo_ismapped() == 0, name
                opened = _toplevels_under(root)
                assert opened == [], f"{name} opened {opened}"
            finally:
                root.destroy()
    finally:
        vps.close()


def test_updm71_no_test_here_needs_a_mapped_window():
    """UPD-M7.1 — the mapped-window count did not move, counted from the AST.

    The suite-wide total is held by
    `tests/test_ci_contract.py::test_the_documented_mapped_window_count_is_the_real_one`,
    which checks the number CLAUDE.md states against the number of tests that
    actually take the `mapped_windows` fixture. This is the part that belongs
    to this batch: six panels across five screens were rewritten and not one
    of the tests written for them needs a real window, so the number that
    test checks is the one it was before. An exact count of zero, not a
    ceiling — a test added here that quietly took the fixture would put a
    window on the user's screen on every local run.
    """
    tree = ast.parse(THIS_FILE.read_text(encoding="utf-8"))
    needs_window = sorted(
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        and "mapped_windows" in [arg.arg for arg in node.args.args]
    )
    assert needs_window == []


# ------------------------------------- UPD-F3: the checkbox column has a name
#
# The on-screen walk of the spec's §11 asked, at step 4, for a word over the
# ticks. UPD-M5.5 had blanked it; this names it on every panel that has one.

# Every panel built from APE_LEFT_COLUMNS, by the screen that renders it.
# Four, not the three the plan said: Annual Plan Elements shares the set.
_PICK_PANELS = (
    ("ape_quarter", lambda: _quarter_screen(left_rows=[_ape_row(1)])),
    ("ape_month", lambda: _month_screen(left_rows=[_ape_row(1)])),
    ("annual_vision", lambda: _annual_screen(left_rows=[_ape_row(1)])),
    ("week_assignment", lambda: _week_screen(left_rows=[_ape_row(1)])),
)


def test_updf31_the_checkbox_column_is_headed_pick():
    """UPD-F3.1 — the first header cell on Week Assignment's left panel reads Pick.

    Purpose: the heading the user asked for is the one the header renders.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#4-upd-f3
    Tests:   this test

    Asserted on the rendered header rather than on `APE_LEFT_COLUMNS`, because
    the constant is one builder away from what is on screen: a heading set in
    the constant and dropped by `build_header` would leave an assertion
    against the constant green. The grid column is asserted with it, so a
    heading that reads Pick in the wrong column still fails.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        column, _cls, text = _cells(_header_frame(screen.left_list))[0]
        assert (column, text) == (0, "Pick")
    finally:
        root.destroy()


def test_updf32_the_pick_column_fits_its_heading_and_has_no_handle():
    """UPD-F3.2 — Pick fits the column it is declared in, and cannot be dragged.

    Purpose: the heading is not clipped, and the column stays fixed-width.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#4-upd-f3
    Tests:   this test

    Measured in the header's own font rather than compared against a number
    written here: `build_header` sets each label's width to its column width
    and anchors it west, so a heading wider than its column is clipped, not
    wrapped, and 34px of column is only enough while "Pick" measures 28. The
    minimum is checked as well as the default, because `ColumnResizer` clamps
    a stored width up to `min_width` and a settings file written before this
    change can still hold the old one.

    The no-handle half matters because a fixed column is how the checkbox
    keeps its grid index: give it a handle and the header gains a widget in
    column 0, which is what `_cells` would then read first.
    """
    root = withdrawn_root()
    try:
        font = ctk.CTkFont(weight="bold")
        checkbox = chip_table.APE_LEFT_COLUMNS[0]
        assert checkbox.key == "checkbox"
        needed = font.measure(checkbox.heading)
        assert needed <= checkbox.min_width, (
            f"{checkbox.heading!r} measures {needed}px against a "
            f"{checkbox.min_width}px minimum")
        assert needed <= checkbox.default_width
        assert checkbox.resizable is False
    finally:
        root.destroy()

    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        header = _header_frame(screen.left_list)
        handles = [c for c in header.winfo_children() if _is_resize_handle(c)]
        assert 0 not in {int(h.grid_info()["column"]) for h in handles}
    finally:
        root.destroy()


def test_updf33_the_checkbox_still_toggles_in_the_same_column():
    """UPD-F3.3 — naming the column left the checkbox and its wiring alone.

    Purpose: the only thing UPD-F3 changed is a word.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#4-upd-f3
    Tests:   this test

    The widget is driven, not its `BooleanVar`: setting the variable directly
    would pass even if the checkbox were no longer bound to it, which is the
    failure a column change could actually cause. `toggle()` is what a click
    reaches.
    """
    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        row = _row_frames(screen.left_list)[0]
        boxes = [c for c in row.winfo_children()
                 if type(c).__name__ == "CTkCheckBox"]
        assert len(boxes) == 1
        assert int(boxes[0].grid_info()["column"]) == 0

        before = [var.get() for var in screen.left_checks.values()]
        assert before == [False]
        boxes[0].toggle()
        assert [var.get() for var in screen.left_checks.values()] == [True]
    finally:
        root.destroy()


def test_updf34_every_ape_left_panel_says_pick():
    """UPD-F3.4 — all four panels built from APE_LEFT_COLUMNS, not three.

    Purpose: the heading is the same on every panel that shares the set.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#4-upd-f3
    Tests:   this test

    The plan said three panels share `APE_LEFT_COLUMNS`. Four do — Annual Plan
    Elements shares it as well — so the count is asserted here rather than
    left as prose that was already wrong once. Exact count, not a floor: a
    fifth adopter that forgot the checkbox column would otherwise pass.
    """
    importers = sorted(
        path.name for path in
        Path("src/getmoredone/screens").glob("*.py")
        if "APE_LEFT_COLUMNS" in path.read_text(encoding="utf-8")
        and path.name != "chip_table.py")
    assert importers == ["annual_vision_segments.py", "ape_assignment.py",
                         "ape_period_view.py", "weekly_items.py"]

    for name, build in _PICK_PANELS:
        root, screen = build()
        try:
            column, _cls, text = _cells(_header_frame(screen.left_list))[0]
            assert (column, text) == (0, "Pick"), name
        finally:
            root.destroy()


# -------------------------- UPD-F2: the filter area is a line of its own
#
# The on-screen walk of the spec's §11 asked, at step 3, for the three filters
# to move off the controls row onto the line below it, and for the one tab with
# no filters to carry a blank line of the same depth so the hub stops jumping.
#
# What the plan said and what the code was differ on two points, and these
# tests follow the code:
#
# * The plan's UPD-F2.2 described "a blank spacer row between them". There was
#   never a blank row between the title and the filters -- the three lines the
#   user counted are title, controls, filters.
# * The plan's UPD-F2.4 said Annual Plan Elements "had its filters inline". It
#   has no lineage filters at all: there is nothing above an annual plan
#   element to filter by. What it had was its title and its controls on one
#   row, which made it two lines shallower than its neighbours.

# The five hub tabs with a header card, and whether that card has filters.
_FILTER_TABS = (
    ("ape_quarter", lambda tmp_path: _quarter_screen(left_rows=[_ape_row(1)]), True),
    ("ape_month", lambda tmp_path: _month_screen(left_rows=[_ape_row(1)]), True),
    ("week_assignment", lambda tmp_path: _week_screen(left_rows=[_ape_row(1)]), True),
    ("week_actions",
     lambda tmp_path: _week_actions_with(tmp_path, [("A tactic", "Living Systems", "Writing")])[1:],
     True),
    ("annual_vision", lambda tmp_path: _annual_screen(left_rows=[_ape_row(1)]), False),
)


def _header_of(screen):
    """The header card a screen grids its filter row into."""
    return screen.filter_row.master


def _rows_of(widget):
    """The set of header grid rows the given widgets occupy."""
    return {int(w.grid_info()["row"]) for w in widget}


def _combos_of(screen):
    """This screen's three lineage filter combos, whichever way it holds them."""
    if hasattr(screen, "filters"):
        return (screen.filters.segment_combo,
                screen.filters.subsegment_combo,
                screen.filters.category_combo)
    return (screen.segment_filter_combo,
            screen.subsegment_filter_combo,
            screen.category_filter_combo)


def test_updf21_the_filters_are_on_their_own_row(tmp_path):
    """UPD-F2.1 — the three combos sit below the row holding the tab's controls.

    Purpose: UPD-F2.1 — the filters are on a line of their own, not sharing
             the controls row, on every tab that has them.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
    Tests:   tests/test_unified_panel_design.py::test_updf21_the_filters_are_on_their_own_row

    Asserted against the rendered widgets' real grid placement, so the claim
    is about where Tk put them and not about where the source says to put
    them. Each combo must be a child of the filter row, and the filter row
    must sit below every interactive control in the header card -- a combo
    left behind on row 1 fails on the first assertion, and a filter row
    gridded above the controls fails on the second.
    """
    for name, build, has_filters in _FILTER_TABS:
        if not has_filters:
            continue
        root, screen = build(tmp_path)
        try:
            header = _header_of(screen)
            filter_row = int(screen.filter_row.grid_info()["row"])

            for combo in _combos_of(screen):
                assert combo.master is screen.filter_row, (
                    f"{name}: a filter combo is not in the filter row")

            controls = [c for c in header.winfo_children()
                        if isinstance(c, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkComboBox))]
            assert controls, f"{name}: no controls found in the header"
            assert max(_rows_of(controls)) < filter_row, (
                f"{name}: a control sits on or below the filter row "
                f"{filter_row}; rows {sorted(_rows_of(controls))}")
        finally:
            root.destroy()


def test_updf22_the_header_card_is_three_rows_deep(tmp_path):
    """UPD-F2.2 — title, then controls, then filters: three rows, in that order.

    Purpose: UPD-F2.2 — the depth the user counted is three lines.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
    Tests:   tests/test_unified_panel_design.py::test_updf22_the_header_card_is_three_rows_deep

    The title is found by its font size rather than its text, so the
    assertion does not have to carry five tab names that are free to change.
    """
    for name, build, _has_filters in _FILTER_TABS:
        root, screen = build(tmp_path)
        try:
            header = _header_of(screen)
            titles = [c for c in header.winfo_children()
                      if isinstance(c, ctk.CTkLabel) and c.cget("font").cget("size") >= 20]
            assert len(titles) == 1, f"{name}: expected one title, got {len(titles)}"
            assert int(titles[0].grid_info()["row"]) == 0, f"{name}: title is not on row 0"
            assert int(screen.filter_row.grid_info()["row"]) == 2, (
                f"{name}: the filter row is not row 2")
        finally:
            root.destroy()


def test_updf23_every_tab_puts_its_filter_row_in_the_same_place(tmp_path):
    """UPD-F2.3 — one assertion over the set, so no tab can drift on its own.

    Purpose: UPD-F2.3 — the depth is the same on all five tabs.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
    Tests:   tests/test_unified_panel_design.py::test_updf23_every_tab_puts_its_filter_row_in_the_same_place

    The five tabs are collected into one set of (title row, filter row)
    pairs; the set must hold exactly one pair. One tab moving its filter row
    makes the set two pairs wide and names itself in the failure.
    """
    placements = {}
    for name, build, _has_filters in _FILTER_TABS:
        root, screen = build(tmp_path)
        try:
            header = _header_of(screen)
            titles = [c for c in header.winfo_children()
                      if isinstance(c, ctk.CTkLabel) and c.cget("font").cget("size") >= 20]
            placements[name] = (int(titles[0].grid_info()["row"]),
                                int(screen.filter_row.grid_info()["row"]))
        finally:
            root.destroy()

    assert len(_FILTER_TABS) == 5, "the tab list changed; update this assertion"
    assert set(placements.values()) == {(0, 2)}, (
        f"the tabs do not agree on the header's shape: {placements}")


def test_updf24_the_tab_with_no_filters_is_the_same_depth(tmp_path):
    """UPD-F2.4 — Annual Plan Elements has no filters and still has the row.

    Purpose: UPD-F2.4 — the blank line the user asked for, one combo deep, so
             the body of this tab starts where the body of the others does.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
    Tests:   tests/test_unified_panel_design.py::test_updf24_the_tab_with_no_filters_is_the_same_depth

    The height is asserted against the same constant the filtered tabs' own
    combos are built from, and against the height a real combo on another tab
    reports, so the blank row cannot drift away from the thing it is standing
    in for. `grid_propagate` must stay off: an empty CTkFrame asks for 200px,
    and with propagation on an empty one collapses instead.
    """
    from src.getmoredone.screens.lineage_filters import FILTER_ROW_HEIGHT

    root, screen = _annual_screen(left_rows=[_ape_row(1)])
    try:
        assert screen.filter_row.winfo_children() == [], (
            "Annual Plan Elements has no lineage filters; its filter row holds nothing")
        assert int(screen.filter_row.cget("height")) == FILTER_ROW_HEIGHT
        # Tkinter's own `grid_propagate()` returns None when read, so the
        # state is read back out of Tcl.
        propagate = screen.filter_row.tk.call(
            "grid", "propagate", screen.filter_row._w)
        assert int(propagate) == 0, (
            "propagation is on, so the empty row collapses instead of standing "
            "one combo deep")
    finally:
        root.destroy()

    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        assert int(screen.segment_filter_combo.cget("height")) == FILTER_ROW_HEIGHT, (
            "the blank row is standing in for a combo of a different height")
    finally:
        root.destroy()


def test_updf25_the_status_line_moved_below_the_filters(tmp_path):
    """UPD-F2.5 — the controls are the same set, and status is under the filters.

    Purpose: UPD-F2.5 — nothing in the header card changed but where the rows
             sit: the same controls in the same order, and the status line
             below the filters rather than beside them.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
    Tests:   tests/test_unified_panel_design.py::test_updf25_the_status_line_moved_below_the_filters

    Week Assignment had its status label on the controls row at column 12 and
    Week Actions had it beside the last combo, so both were a column of the
    row above rather than a line of their own. The button sets are asserted
    verbatim: UPD-F2 moves rows, and a control that disappeared in the move
    would otherwise go unnoticed.
    """
    # VTF-M4.1 took the Save off four of these headers: it read the ticks,
    # and the ticks are a filter now. Each tab creates records from an Add
    # New button under its right panel instead, which
    # tests/test_vsp_tab_contracts.py asserts. Load, This Week and Refresh
    # stay where they were (VTF-M4.2), which is what this set still pins.
    expected_buttons = {
        "ape_quarter": ["Load", "Refresh"],
        "ape_month": ["Load", "Refresh"],
        "week_assignment": ["Load", "This Week", "Refresh"],
        "week_actions": ["Load", "This Week"],
        "annual_vision": ["Load Year", "Refresh"],
    }
    for name, build, has_filters in _FILTER_TABS:
        root, screen = build(tmp_path)
        try:
            header = _header_of(screen)
            buttons = [c.cget("text") for c in header.winfo_children()
                       if isinstance(c, ctk.CTkButton)]
            assert buttons == expected_buttons[name], (
                f"{name}: header buttons are {buttons}")

            if has_filters:
                assert screen.status_label.master is header, (
                    f"{name}: the status label left the header card")
                assert int(screen.status_label.grid_info()["row"]) == 3, (
                    f"{name}: the status label is on row "
                    f"{screen.status_label.grid_info()['row']}, not below the filters")
                assert int(screen.status_label.grid_info()["column"]) == 0, (
                    f"{name}: the status label is not at the left of its row")
        finally:
            root.destroy()


# ------------------- UPD-F4: the columns rescale with the divider
#
# Step 7 of the on-screen walk: "I want all columns to resize as I move the
# vertical bar left or right, down to 5 character widths." Until UPD-F4 a
# column kept the pixel width it was given however wide its panel became, so
# widening a panel added empty space to the right of the last column instead
# of giving the space to the columns.
#
# A withdrawn root has no layout, so `body.winfo_width()` is 1 and
# `SplitPanel.apply` returns early. These tests therefore drive the fit with
# an explicit pixel width -- which is the number `apply` would pass -- and
# assert the wiring from `apply` to the tables separately.


def test_updf41_a_divider_move_rescales_every_resizable_column():
    """UPD-F4.1 — a wider panel is shared out across every resizable column.

    Purpose: UPD-F4.1 — moving the divider rescales every resizable column in
             proportion to its stored width.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf41_a_divider_move_rescales_every_resizable_column

    Proportion, not equal shares: a user who has made Segment twice the width
    of Category has said something about the shape of their panel, and a
    rescale that evened them out would throw it away. The ratio is asserted
    against the ratio before the fit, to one part in twenty, which is as
    close as integer pixels allow at these widths.
    """
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        table = screen.left_table
        resizable = [c.key for c in table.columns if c.resizable]
        assert len(resizable) >= 2, "this tab has no proportions to keep"
        before = {k: table.width(k) for k in resizable}

        table.fit_to_panel(1200)
        after = {k: table.width(k) for k in resizable}

        assert sum(after.values()) > sum(before.values()), (
            f"the extra width went nowhere: {before} -> {after}")
        for key in resizable:
            assert after[key] > before[key], f"{key} did not grow: {after}"

        available = table.available_width(1200)
        used = sum(table.width(c.key) for c in table.columns)
        at_a_bound = [k for k in resizable
                      if after[k] in (table.resizer.specs[k].min_width,
                                      table.resizer.specs[k].max_width)]
        assert not at_a_bound, (
            f"{at_a_bound} are pinned at a bound, so this panel cannot show "
            f"an exact fill; pick another width")
        assert used == available, (
            f"the panel is not filled exactly: {used} of {available}; integer "
            f"shares leave a remainder, and it has to go to a column")

        widest = max(resizable, key=lambda k: before[k])
        narrowest = min(resizable, key=lambda k: before[k])
        want = before[widest] / before[narrowest]
        got = after[widest] / after[narrowest]
        assert abs(got - want) < 0.05, (
            f"the shape changed: {want:.3f} -> {got:.3f}; {before} -> {after}")
    finally:
        root.destroy()


def test_updf41_the_divider_is_wired_to_both_panels():
    """UPD-F4.1 — `SplitPanel.apply` hands each panel's width to its columns.

    Purpose: UPD-F4.1 — the wiring, which the fit itself cannot show: a
             correct `fit_to_panel` that nothing calls is the behaviour the
             user reported.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf41_the_divider_is_wired_to_both_panels

    Driven through a stand-in body rather than a real one: a withdrawn root
    has no layout, so a real `body.winfo_width()` is 1 and `apply` returns
    before it reaches the callback. The stand-in answers the three calls
    `SplitPanel` makes on its body and nothing else.
    """
    calls = []

    class FakeBody:
        def winfo_width(self):
            return 1208  # 1200 usable at SPLITTER_WIDTH = 8

        def grid_columnconfigure(self, *args, **kwargs):
            calls.append(("grid", args, kwargs))

        def bind(self, *args, **kwargs):
            pass

    class FakeDivider:
        def bind(self, *args, **kwargs):
            pass

    fitted = []
    split = split_panel.SplitPanel(
        FakeBody(), SimpleNamespace(winfo_width=lambda: 600), FakeDivider(),
        on_apply=lambda left, right: fitted.append((left, right)))
    split.ratio = 0.5
    split.apply()

    assert fitted == [(600, 600)], fitted
    minsizes = [kwargs.get("minsize") for _tag, _args, kwargs in calls]
    assert minsizes == [600, 600], minsizes

    # Every tab that has two chip panels hands both to the fitter, and the one
    # with a single chip panel hands one. Asserted as the set of screens, so a
    # new tab cannot be added without a decision about this.
    import inspect

    wired = {}
    for name in ("ape_assignment", "ape_period_view", "annual_vision_segments",
                 "weekly_items", "week_actions"):
        module = importlib.import_module(f"src.getmoredone.screens.{name}")
        source = inspect.getsource(module)
        matches = [line.strip() for line in source.splitlines()
                   if "on_apply=panel_fitter(" in line]
        assert len(matches) == 1, f"{name}: {matches}"
        wired[name] = matches[0]

    # The width handed to the columns is the panel's less what the table
    # spends on its own padding. Read off the rendered widgets rather than
    # restated here: `available_width` and the `grid` calls are two places
    # that have to agree, and this is what catches them drifting.
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        table = screen.left_table
        header = _header_frame(screen.left_list)
        header_padx = int(header.grid_info()["padx"])
        cell_padx = {int(label.grid_info()["padx"])
                     for label in header.winfo_children()
                     if isinstance(label, ctk.CTkLabel)}
        assert len(cell_padx) == 1, f"cells disagree on their padding: {cell_padx}"
        spent = 2 * header_padx + 2 * cell_padx.pop() * len(table.columns)
        assert table.available_width(1000) == 1000 - spent, (
            f"available_width does not match the layout: "
            f"{table.available_width(1000)} != {1000 - spent}")
    finally:
        root.destroy()

    assert wired == {
        "ape_assignment": "on_apply=panel_fitter(self.left_table, self.right_table),",
        "ape_period_view": "on_apply=panel_fitter(self.left_table, self.right_table),",
        "annual_vision_segments": "on_apply=panel_fitter(self.left_table, self.right_table),",
        "weekly_items": "on_apply=panel_fitter(self.left_table, self.right_table),",
        # The right panel here is a TodayScreen subclass, not a ChipTable.
        "week_actions": "on_apply=panel_fitter(self.left_table),",
    }, wired
    assert callable(chip_table.panel_fitter)


def test_updf42_a_fixed_column_keeps_its_width_when_the_panel_moves():
    """UPD-F4.2 — Pick, `#` and Actions are reserved out, not rescaled.

    Purpose: UPD-F4.2 — a fixed column holds a checkbox or a pair of buttons,
             whose size does not depend on how wide the panel is.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf42_a_fixed_column_keeps_its_width_when_the_panel_moves

    Both directions: a panel twice as wide and one half as wide. A fit that
    shared the budget across every column would move these on either call.
    """
    root, screen = _annual_screen(left_rows=[_ape_row(1)])
    try:
        for table in (screen.left_table, screen.right_table):
            fixed = [c.key for c in table.columns if not c.resizable]
            assert fixed, "this panel has no fixed columns to hold"
            before = {k: table.width(k) for k in fixed}
            for panel_px in (1600, 500):
                table.fit_to_panel(panel_px)
                assert {k: table.width(k) for k in fixed} == before, (
                    f"a fixed column moved at {panel_px}px: "
                    f"{ {k: table.width(k) for k in fixed} } != {before}")
    finally:
        root.destroy()


def test_updf43_no_column_goes_below_five_characters():
    """UPD-F4.3 — five characters is the floor, and the rest absorb the squeeze.

    Purpose: UPD-F4.3 — the width the user named: "down to 5 character
             widths", and no narrower.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf43_no_column_goes_below_five_characters

    The floor is asserted against `min_column_width()` rather than against 40,
    so it follows `CHAR_PX` if the list font ever changes, and against five
    times `CHAR_PX` as well, so the constant cannot quietly stop meaning five
    characters.

    The panel width is chosen so the floor actually binds for some columns and
    not for others, which is the only case that tests both halves of the
    claim. At 251px: `available_width` spends 58, the two fixed columns
    reserve 68, and 125px of budget against weights 135/155/125 puts the
    narrowest column's share under 40. A width that left every share above
    the floor -- 300px does -- would pass this test with `MIN_COLUMN_CHARS`
    set to 1, which is how it read before the csdp sweep.
    """
    from src.getmoredone.screens.column_resize import (
        CHAR_PX, MIN_COLUMN_CHARS, min_column_width)

    assert MIN_COLUMN_CHARS == 5
    assert min_column_width() == 5 * CHAR_PX == 40

    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        table = screen.left_table
        resizable = [c.key for c in table.columns if c.resizable]
        table.fit_to_panel(251)
        widths = {key: table.width(key) for key in resizable}

        for key, width in widths.items():
            assert width >= min_column_width(), (
                f"{key} is {width}px, below the {min_column_width()}px floor")
        assert min(widths.values()) == min_column_width(), (
            f"no column reached the floor, so this panel width does not "
            f"test it: {widths}")
        assert max(widths.values()) > min_column_width(), (
            f"every column is at the floor, so nothing absorbed the "
            f"squeeze: {widths}")
    finally:
        root.destroy()


def test_updf44_a_panel_too_narrow_for_the_floor_surfaces_it(caplog):
    """UPD-F4.4 — P7: a panel that cannot seat the floors says by how much.

    Purpose: UPD-F4.4 — the adversarial case. A fit that returned a negative
             or zero width here would look like it had worked, and the panel
             would render columns of nothing with no record of why.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf44_a_panel_too_narrow_for_the_floor_surfaces_it

    The number is checked, not just its truthiness: the shortfall is what
    tells a reader whether a panel is 4px or 400px too narrow.

    The expected shortfall is the literal 188, not `len(resizable) *
    min_column_width() + fixed_px`. Derived from the constants it is meant to
    pin, this assertion moved with them: `MIN_COLUMN_CHARS = 1` left it green,
    found by the csdp sweep's mutation. The two parts are asserted separately
    so a reader can see where 188 comes from and a change to either is named.
    """
    from src.getmoredone.screens.chip_table import panel_fitter
    from src.getmoredone.screens.column_resize import min_column_width

    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        table = screen.left_table
        resizable = [c.key for c in table.columns if c.resizable]
        fixed_px = sum(table.width(c.key) for c in table.columns
                       if not c.resizable)

        # Three resizable columns at the 40px floor, and 34px each of
        # checkbox and index reserved out: 188px of column that one pixel of
        # panel cannot seat.
        assert (len(resizable), min_column_width(), fixed_px) == (3, 40, 68), (
            f"the parts of 188 changed: {len(resizable)} resizable, "
            f"{min_column_width()}px floor, {fixed_px}px fixed")

        # One pixel of panel: the floors cannot be seated at all.
        overflow = table.fit_to_panel(1)
        assert overflow == 188, (
            f"overflow {overflow} does not account for three 40px floors "
            f"and {fixed_px}px of fixed columns")
        for key in resizable:
            assert table.width(key) == min_column_width(), (
                f"{key} is {table.width(key)}px, not pinned to the floor")

        with caplog.at_level("WARNING"):
            panel_fitter(table)(1, 0)
        assert any("too narrow" in r.message for r in caplog.records), (
            f"nothing was logged: {[r.message for r in caplog.records]}")
    finally:
        root.destroy()


def test_updf43b_the_floor_suspends_the_shape_it_does_not_destroy_it():
    """UPD-F4.3 — a panel narrower than the floors gives the shape back after.

    Purpose: UPD-F4.3/F4.6 — a stored width is the weight the next fit shares
             by, so pinning every column to the floor in `_widths` would make
             the squeeze permanent: the panel comes back wide and the columns
             come back equal, with the 135/155/125 shape gone for good and
             nothing logged about losing it.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf43b_the_floor_suspends_the_shape_it_does_not_destroy_it

    Found by the csdp sweep's cold pass. Not reachable through the shipped
    wiring -- `SplitPanel` holds both panels at `MIN_PANEL_WIDTH`, which is
    wide enough for every column set's floors -- so this drives
    `fit_to_panel` directly, as the overflow test does.

    The second half covers the other way out of the floor: a width the user
    sets by hand while the panel is floored is newer than the remembered
    shape and must survive the restore.
    """
    from src.getmoredone.screens.column_resize import min_column_width

    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        table = screen.left_table
        resizable = [c.key for c in table.columns if c.resizable]

        table.fit_to_panel(900)
        before = {key: table.width(key) for key in resizable}
        assert len(set(before.values())) > 1, (
            f"the columns start out equal, so this test cannot tell a kept "
            f"shape from a lost one: {before}")

        assert table.fit_to_panel(1) == 188
        floored = {key: table.width(key) for key in resizable}
        assert set(floored.values()) == {min_column_width()}, (
            f"the floor did not take hold: {floored}")

        # Dragging a window narrow fires <Configure> many times, so the floor
        # is entered again and again. The shape is remembered on the way in,
        # once -- re-reading it here would remember the floors themselves and
        # the restore below would have nothing to give back.
        assert table.fit_to_panel(1) == 188
        assert table.fit_to_panel(200) > 0

        table.fit_to_panel(900)
        after = {key: table.width(key) for key in resizable}
        assert after == before, (
            f"the shape did not come back after the squeeze: {before} -> "
            f"{floored} -> {after}")
    finally:
        root.destroy()

    root, screen = _week_screen(left_rows=[_ape_row(1)])
    try:
        table = screen.left_table
        table.fit_to_panel(900)
        remembered = table.width("segment")
        table.fit_to_panel(1)
        _resize(table, key="segment", delta=120)
        dragged = table.width("segment")
        assert dragged == min_column_width() + 120, (
            f"the drag did not land: {dragged}px")
        assert dragged < remembered, (
            f"this drag has to leave segment narrower than the {remembered}px "
            f"it is remembered at, or the next assertion proves nothing")

        # The dragged width is segment's weight now, so a weight of 160
        # against the 290 and 233 beside it gives it less than the 251 the
        # remembered shape would have. Without the drop from `_pre_floor` it
        # comes back at exactly `remembered`, which the first half shows.
        table.fit_to_panel(900)
        assert table.width("segment") < remembered, (
            "the restore undid a drag made while the panel was floored: "
            f"segment came back at {table.width('segment')}px, the "
            f"remembered {remembered}px")
    finally:
        root.destroy()


def test_updf45_a_drag_still_moves_only_its_own_column():
    """UPD-F4.5 — a column drag is unchanged, and is what gets stored.

    Purpose: UPD-F4.5 — UPD-F4 adds a second writer to the same widths, and
             the failure to guard against is a fit running on the back of a
             drag and undoing it.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf45_a_drag_still_moves_only_its_own_column

    The drag is taken after a fit, so the widths it starts from are fitted
    ones rather than the defaults -- which is the state a real drag happens
    in, the panel having been laid out before the user reaches for a handle.
    """
    settings = FakeSettings(week_assignment_split_ratio=0.5)
    root, screen = _week_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        table = screen.left_table
        table.fit_to_panel(1100)
        before = {c.key: table.width(c.key) for c in table.columns}

        _resize(table, key="segment", delta=70)

        after = {c.key: table.width(c.key) for c in table.columns}
        assert after["segment"] == before["segment"] + 70
        for key, width in before.items():
            if key != "segment":
                assert after[key] == width, f"{key} moved with the drag"
        assert settings.week_assignment_left_col_widths["segment"] == (
            before["segment"] + 70)
    finally:
        root.destroy()


def test_updf46_stored_widths_survive_a_different_window_size():
    """UPD-F4.6 — the stored widths are a shape, so a wider window keeps it.

    Purpose: UPD-F4.6 — step 10 of the walk asked for the sizing to come
             back; step 7 asked for it to follow the divider. Both hold only
             if the stored number is read as a weight.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#5-upd-f4
    Tests:   tests/test_unified_panel_design.py::test_updf46_stored_widths_survive_a_different_window_size

    The second build is the relaunch, at a panel 300px wider than the one the
    widths were set in. The pixel widths must differ -- there is more room --
    and the ratio between two of them must not.
    """
    settings = FakeSettings(ape_quarter_split_ratio=0.5)
    root, screen = _quarter_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        table = screen.left_table
        table.fit_to_panel(900)
        _resize(table, key="segment", delta=120)
        narrow = {c.key: table.width(c.key) for c in table.columns if c.resizable}
        shape = narrow["segment"] / narrow["category"]
    finally:
        root.destroy()

    root, screen = _quarter_screen(left_rows=[_ape_row(1)], settings=settings)
    try:
        table = screen.left_table
        assert table.width("segment") == narrow["segment"], (
            "the stored width did not come back")
        table.fit_to_panel(1200)
        wide = {c.key: table.width(c.key) for c in table.columns if c.resizable}
        assert sum(wide.values()) > sum(narrow.values()), (
            f"the wider panel gave the columns nothing: {narrow} -> {wide}")
        assert abs(wide["segment"] / wide["category"] - shape) < 0.05, (
            f"the shape was lost: {shape:.3f} -> "
            f"{wide['segment'] / wide['category']:.3f}")
    finally:
        root.destroy()
