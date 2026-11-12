"""The VSP tabs' left-to-right filter: the tick on the left narrows the right.

Spec: docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md

Every test name carries the criterion ID it verifies (VTF-M1 ... VTF-M2).

The user reported, 2026-11-11: *"Rows on the LEFT are filters for rows on the
RIGHT. this doesn't work anywhere."* It did not: in the whole history of these
tabs the tick was read in one place only -- the Save button's ``add_selected``
-- so a tick did nothing until a button was pressed, and what it then did was
create records rather than filter any. These tests are that behaviour's
replacement.

Screens are built on a **withdrawn** root, so none of them adds to the mapped
window count that tests/test_ci_contract.py pins.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Self-contained path bootstrap, for the same reason test_unified_panel_design
# carries one: tests/test_ci_contract.py imports every test file with the repo
# root stripped from sys.path.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

import customtkinter as ctk  # noqa: E402

from src.getmoredone.screens.annual_vision_segments import (  # noqa: E402
    AnnualVisionSegmentsScreen,
)

YEAR = 2026


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


def _vision_element(idx, category):
    """One left-hand row: a vision element the annual tab can create from."""
    return {
        "id": f"ve-{idx}",
        "segment_name": "Purposeful Work",
        "subsegment_name": "Living Systems",
        "category_name": category,
        "key_field": category,
    }


def _annual_row(idx, vision_element_id, category):
    """One right-hand row: an ``annual_vision_elements`` row for the year."""
    return {
        "id": f"ave-{idx}",
        "year": YEAR,
        "vision_element_id": vision_element_id,
        "segment_name": "Purposeful Work",
        "subsegment_name": "Living Systems",
        "category_name": category,
        "key_field": category,
    }


def _fake_annual_vps(left_rows, right_rows):
    """A VPS manager double returning real dicts, not MagicMock attributes.

    The screen hands these straight to the lineage colour helpers, which call
    ``.strip()`` and ``.get()`` on what comes back.
    """
    return SimpleNamespace(
        get_vision_elements=lambda: list(left_rows),
        get_annual_vision_elements=lambda year: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        resolve_segment_color=lambda name, colors: "",
    )


def _annual_screen(left_rows=(), right_rows=()):
    """The Annual Plan Elements tab on a withdrawn root, already rendered."""
    root = _root()
    vps = _fake_annual_vps(left_rows, right_rows)
    app = SimpleNamespace(vps_manager=vps)
    screen = AnnualVisionSegmentsScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _categories(table):
    """The Category cell of every rendered row, in grid order.

    The table pads and clamps a cell's text to its column width, so the
    fixtures above use short category names and this strips the padding.
    """
    return [cells["category"].cget("text").strip() for _frame, cells in table.rows]


def _checkboxes(screen):
    """The left panel's checkboxes, one per rendered row, in grid order."""
    out = []
    for frame, _cells in screen.left_table.rows:
        for child in frame.winfo_children():
            if isinstance(child, ctk.CTkCheckBox):
                out.append(child)
    return out


def _three_element_tab():
    """Three vision elements, each with an annual record for the year."""
    left = [_vision_element(i, c) for i, c in ((1, "Blog"), (2, "Pod"), (3, "Talk"))]
    right = [_annual_row(i, f"ve-{i}", c)
             for i, c in ((1, "Blog"), (2, "Pod"), (3, "Talk"))]
    return _annual_screen(left, right)


# ------------------------------------------------------- VTF-M1, annual tab

def test_vtfm11_the_annual_tab_right_panel_follows_the_ticks():
    """VTF-M1.1 — ticking Vision Elements narrows the year's annual records.

    The right panel's query takes the year and nothing else, so before this
    criterion a tick could not have narrowed it: the filter is applied to the
    rows in hand, by ``vision_element_id``.
    """
    root, screen = _three_element_tab()
    try:
        screen.left_checks["ve-2"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Pod"]

        screen.left_checks["ve-3"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Pod", "Talk"]
    finally:
        root.destroy()


def test_vtfm15_no_tick_is_no_filter():
    """VTF-M1.5 — with nothing ticked the whole year is listed.

    An untouched screen must look exactly as it did before VTF-M1, and a tick
    that is then cleared must put every row back.
    """
    root, screen = _three_element_tab()
    try:
        assert _categories(screen.right_table) == ["Blog", "Pod", "Talk"]

        screen.left_checks["ve-1"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Blog"]

        screen.left_checks["ve-1"].set(False)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Blog", "Pod", "Talk"]
    finally:
        root.destroy()


def test_vtfm16_the_tick_refreshes_without_a_button():
    """VTF-M1.6 — the checkbox itself re-renders the right panel.

    Driven through ``CTkCheckBox.toggle``, which is what a click calls: it
    sets the variable and then calls the widget's own ``command``. A tick with
    no command would leave the right panel as it was, which is precisely the
    reported defect.
    """
    root, screen = _three_element_tab()
    try:
        boxes = _checkboxes(screen)
        assert len(boxes) == 3

        boxes[1].toggle()
        assert screen.left_checks["ve-2"].get() is True
        assert _categories(screen.right_table) == ["Pod"]
    finally:
        root.destroy()


def test_vtfm18_a_tick_leaves_the_left_panel_alone():
    """VTF-M1.8 — a tick re-renders the right panel only.

    The left row frames must be the same objects afterwards. Rebuilding the
    left panel from a checkbox's own command destroys the widget that is
    mid-click, and would let a filter hide the row holding its own tick.
    """
    root, screen = _three_element_tab()
    try:
        before = [frame for frame, _cells in screen.left_table.rows]
        boxes = _checkboxes(screen)
        boxes[0].toggle()
        after = [frame for frame, _cells in screen.left_table.rows]

        assert [id(f) for f in after] == [id(f) for f in before]
        assert all(f.winfo_exists() for f in after)
    finally:
        root.destroy()


def test_vtfm19_a_hidden_tick_stops_filtering():
    """VTF-M1.9 — a tick on a row the left panel no longer shows is ignored.

    ``left_checks`` outlives a Load Year: the variables are kept so a tick
    survives a refresh. A row that has gone from the left list must stop
    filtering with it, or the user is left with a filter they cannot see and
    so cannot clear.
    """
    root, screen = _three_element_tab()
    try:
        screen.left_checks["ve-2"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Pod"]

        # The year is reloaded and ve-2 is gone from the left list, while its
        # annual record for the year remains.
        screen.vps_manager.get_vision_elements = lambda: [
            _vision_element(1, "Blog"), _vision_element(3, "Talk"),
        ]
        screen.refresh_lists()

        assert screen.left_checks["ve-2"].get() is True
        assert screen._ticked_vision_element_ids() == set()
        assert _categories(screen.right_table) == ["Blog", "Pod", "Talk"]
    finally:
        root.destroy()


def test_vtfm11_the_heading_says_when_the_right_panel_is_filtered():
    """VTF-M1.1 — the heading names the filter, so it can be seen and undone.

    VTF-N1 asks that the user can tell what the current filter is. The count
    is the only on-screen evidence that rows are being withheld; without it a
    filtered panel and an empty year look the same.
    """
    root, screen = _three_element_tab()
    try:
        assert screen.right_title_label.cget("text") == (
            f"Annual Plan Elements for the year {YEAR}"
        )

        screen.left_checks["ve-2"].set(True)
        screen.refresh_right_panel()
        assert screen.right_title_label.cget("text") == (
            f"Annual Plan Elements for the year {YEAR} "
            "(1 of 3, filtered by tick)"
        )
    finally:
        root.destroy()
