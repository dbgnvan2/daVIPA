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

import sys
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

from src.getmoredone.color_contrast import pick_text_color  # noqa: E402
from src.getmoredone.screens import chip_table  # noqa: E402
from src.getmoredone.screens.ape_assignment import APEAssignmentScreen  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src" / "getmoredone"


# --------------------------------------------------------------------- helpers

def _root():
    """A withdrawn Tk root, or a skip when there is no display."""
    try:
        root = ctk.CTk()
    except Exception as exc:  # Headless without a display.
        pytest.skip(f"Tk display unavailable: {exc}")
    root.geometry("1400x900+0+0")
    root.withdraw()
    return root


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
    return SimpleNamespace(
        get_annual_plan_elements=lambda year: list(left_rows),
        get_annual_plan_elements_for_quarter=lambda year, quarter: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
    )


def _quarter_screen(left_rows=(), right_rows=()):
    """APE Quarter Assignment on a withdrawn root, already rendered."""
    root = _root()
    vps = _fake_vps(left_rows, right_rows)
    screen = APEAssignmentScreen(root, vps, SimpleNamespace(vps_manager=vps))
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


def _cells(frame):
    """[(grid column, class name, text)] for a header or row frame."""
    out = []
    for child in frame.winfo_children():
        info = child.grid_info()
        if not info:
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

        # The middle column is the splitter's width, not a panel's.
        assert body.grid_columnconfigure(1).get("minsize") == screen.SPLITTER_WIDTH

        bound = set(_bound_sequences(screen.divider))
        assert {"<Button-1>", "<B1-Motion>", "<ButtonRelease-1>"} <= bound
    finally:
        root.destroy()


def test_updm41_ape_quarter_left_header_columns_are_unchanged():
    """UPD-M4.1 — left header: an empty checkbox cell, then the four names.

    The left panel is the selectable one, so its first cell is the blank
    header over the checkbox column. Column order is asserted by position,
    not by set membership, because the order is the thing the shared table has
    to reproduce.
    """
    root, screen = _quarter_screen(left_rows=[_ape_row(1)])
    try:
        header = _header_frame(screen.left_list)
        texts = [text for _col, _cls, text in _cells(header)]
        assert texts == ["", "#", "Segment", "SubSegment", "Category"]
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


# ------------------------------------------- UPD-M3: the shared chip table

def _table(prefix="ape_quarter_left", columns=None, settings=None):
    """A ChipTable in a scrollable frame on a withdrawn root."""
    root = _root()
    frame = ctk.CTkScrollableFrame(root)
    frame.grid(row=0, column=0, sticky="nsew")
    cols = columns if columns is not None else list(chip_table.APE_COLUMNS)
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
            "", "#", "Segment", "SubSegment", "Category", "Actions"]
        assert len(table.rows) == 3
        texts = [lbl.cget("text").strip() for lbl in table.rows[0][1].values()]
        assert "Purposeful Work" in texts
    finally:
        root.destroy()


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
        # Segment, SubSegment, Category. The checkbox, # and Actions columns
        # are fixed: a 34px number has nothing to widen into.
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


def test_updm36_panels_keep_their_own_widths():
    """UPD-M3.6 — two tables with different prefixes do not share a width.

    The left and right panel of one tab are different shapes and different
    widths; one store for both would make a drag in one panel move the other.
    """
    settings = FakeSettings()
    root = _root()
    try:
        left_frame = ctk.CTkScrollableFrame(root)
        right_frame = ctk.CTkScrollableFrame(root)
        left = chip_table.ChipTable(left_frame, settings, "ape_quarter_left",
                                    list(chip_table.APE_COLUMNS))
        right = chip_table.ChipTable(right_frame, settings, "ape_quarter_right",
                                     list(chip_table.APE_COLUMNS))
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
    """
    root, _frame, table = _table()
    try:
        inherited = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        table.build_header()
        _row_frame, cells = table.add_row(
            {"segment": "No colour", "category": "Measured"},
            {"segment": "", "category": "#cc7744"},
        )
        # The fallback pill inherits, and what it inherits is not the dark
        # default pick_text_color used to hand back for an unparseable fill.
        assert cells["segment"].cget("text_color") == inherited
        assert cells["segment"].cget("text_color") != "#000000"
        # The lineage pill is still measured against its own fill.
        assert cells["category"].cget("text_color") == pick_text_color("#cc7744")
    finally:
        root.destroy()
