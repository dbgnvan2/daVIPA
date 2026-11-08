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
import logging
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

from src.getmoredone.app_settings import AppSettings  # noqa: E402
from src.getmoredone.color_contrast import pick_text_color  # noqa: E402
from src.getmoredone.screens import chip_table, row_drag, split_panel  # noqa: E402
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


def _quarter_screen(left_rows=(), right_rows=(), settings=None):
    """APE Quarter Assignment on a withdrawn root, already rendered.

    With `settings`, the screen takes it from the app the way the running app
    hands over its own instance; without one it loads its own, which
    conftest.py's settings isolation points at a temporary file.
    """
    root = _root()
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

        # The middle column is the splitter's width, not a panel's. UPD-M1
        # moved the number into screens/split_panel.py, which is the whole
        # point of that step; the column it sizes is unchanged.
        assert body.grid_columnconfigure(1).get("minsize") == split_panel.SPLITTER_WIDTH

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

# The screens that still carry their own copy of the splitter. UPD-M1 adopts
# ape_assignment only (the spec's implementation order, step 2); these three
# adopt at UPD-M4, and this set must shrink to empty as they do. It is asserted
# as an exact set rather than a ceiling, so it cannot quietly grow a fourth
# entry and it cannot stay stale after an adoption.
SPLITTER_HOLDOUTS = {
    "annual_vision_segments.py",
    "ape_period_view.py",
    "weekly_items.py",
}

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
    root = _root()
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
            body.configure(width=body_width)
            root.update_idletasks()
            assert body.winfo_width() <= split_panel.SPLITTER_WIDTH

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
    """UPD-M1.5 — counted from the AST, as an exact set.

    UPD-M1 adopts ape_assignment only, so the count is not yet zero and saying
    it is would be a false claim. What is asserted instead is exact: the files
    that still define a splitter are the three the spec's order leaves for
    UPD-M4, and each defines the whole copy rather than part of one. The set
    goes red when a fourth screen grows one, and again when a holdout adopts
    and is not struck off here.
    """
    found = _screens_with_their_own_splitter()
    assert set(found) == SPLITTER_HOLDOUTS | SPLITTER_OUT_OF_SCOPE
    assert "ape_assignment.py" not in found
    whole_copy = {"_apply_split_ratio", "_on_divider_drag", "SPLITTER_WIDTH"}
    for name in SPLITTER_HOLDOUTS:
        assert found[name] == whole_copy, (name, sorted(found[name]))
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

# The screens that still carry their own copy of the row drag. UPD-M2 adopts
# ape_assignment only (the spec's §4 step 3); these three adopt at UPD-M4 and
# this set must shrink to empty as they do. Exact, like SPLITTER_HOLDOUTS, and
# for the same reason.
DRAG_HOLDOUTS = {
    "annual_vision_segments.py",
    "ape_period_view.py",
    "weekly_items.py",
}


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
    """UPD-M2.5 — counted from the AST, as an exact set.

    Partial for the same reason UPD-M1.5 is: UPD-M2 adopts ape_assignment
    only, so the count is not 0 yet and claiming it would be false. The set is
    exact in both directions — red if another screen grows its own copy, red
    again when a holdout adopts and is not struck off here.
    """
    found = _screens_with_their_own_drag()
    assert set(found) == DRAG_HOLDOUTS
    assert "ape_assignment.py" not in found
    for name in DRAG_HOLDOUTS:
        assert found[name] == set(DRAG_METHODS), (name, sorted(found[name]))


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
