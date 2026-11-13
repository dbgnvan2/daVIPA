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
from src.getmoredone.screens.ape_assignment import APEAssignmentScreen  # noqa: E402
from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen  # noqa: E402
from src.getmoredone.screens.weekly_items import WeeklyItemsScreen  # noqa: E402
from conftest import withdrawn_root

YEAR = 2026


# --------------------------------------------------------------------- helpers

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
    root = withdrawn_root()
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


# ------------------------------------------- helpers: the three APE tabs

def _ape_row(idx, segment="Purposeful Work", subsegment="Living Systems",
             category="Blog"):
    """One Annual Plan Element row, as the VSP queries return it."""
    return {
        "id": f"ape-{idx}",
        "segment_name": segment,
        "subsegment_name": subsegment,
        "category_name": category,
    }


def _tactic_row(idx, ape_id, category="Blog"):
    """One Weekly Tactic row. Its lineage arrives under ``ape_*`` keys."""
    return {
        "id": f"wt-{idx}",
        "title": f"Week {idx}",
        "start_date": "2026-02-23",
        "annual_plan_element_id": ape_id,
        "ape_segment_name": "Purposeful Work",
        "ape_subsegment_name": "Living Systems",
        "ape_category_name": category,
    }


def _fake_period_vps(left_rows, right_rows):
    """A VPS double for the Quarter and Month tabs.

    The period queries ignore the period they are asked for, so a test does
    not have to make the screen's own year/quarter/month selectors agree with
    a fixture.
    """
    return SimpleNamespace(
        get_annual_plan_elements=lambda year: list(left_rows),
        get_annual_plan_elements_for_quarter=lambda year, quarter: list(left_rows),
        get_annual_plan_elements_for_month=lambda year, month: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
    )


def _quarter_screen(left_rows=(), right_rows=()):
    """APE Quarter Assignment on a withdrawn root, already rendered."""
    root = withdrawn_root()
    vps = _fake_period_vps(left_rows, right_rows)
    # The quarter tab's right panel is the quarter query, not the month one.
    vps.get_annual_plan_elements_for_quarter = lambda year, quarter: list(right_rows)
    vps.get_annual_plan_elements = lambda year: list(left_rows)
    app = SimpleNamespace(vps_manager=vps)
    screen = APEAssignmentScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _month_screen(left_rows=(), right_rows=()):
    """APE Month Assignment on a withdrawn root, already rendered."""
    root = withdrawn_root()
    vps = _fake_period_vps(left_rows, right_rows)
    app = SimpleNamespace(vps_manager=vps)
    screen = APEPeriodViewScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _week_screen(left_rows=(), right_rows=()):
    """APE Week Assignment on a withdrawn root, already rendered."""
    root = withdrawn_root()
    vps = SimpleNamespace(
        get_weekly_action_items=lambda **_kw: list(right_rows),
        get_annual_plan_elements_for_month=lambda year, month: list(left_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        get_segment_colors_by_id=lambda: {},
        resolve_segment_color=lambda name, colors: "",
        count_open_children_for_weekly_tactic=lambda item_id: (0, 0),
        children_to_delete_with_weekly_tactic=lambda item_id: [],
    )
    app = SimpleNamespace(vps_manager=vps)
    screen = WeeklyItemsScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _three_ape_tab(builder):
    """Three APEs on the left; the first two of them on the right."""
    left = [_ape_row(1, category="Blog"), _ape_row(2, category="Pod"),
            _ape_row(3, category="Talk")]
    right = [_ape_row(1, category="Blog"), _ape_row(2, category="Pod")]
    return builder(left, right)


# ------------------------------------------ VTF-M1, the three APE tabs

def test_vtfm12_the_quarter_tab_right_panel_follows_the_ticks():
    """VTF-M1.2 — ticking an APE narrows the quarter to those APE ids.

    Both panels list `annual_plan_elements`, so the tick says "show me
    whether these are in the quarter" (decision D3).
    """
    root, screen = _three_ape_tab(_quarter_screen)
    try:
        assert _categories(screen.right_table) == ["Blog", "Pod"]

        screen.left_checks["ape-2"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Pod"]

        # ape-3 is on the left and not in the quarter: ticking it adds no row.
        screen.left_checks["ape-3"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Pod"]
    finally:
        root.destroy()


def test_vtfm13_the_month_tab_right_panel_follows_the_ticks():
    """VTF-M1.3 — the same, on the month's rows."""
    root, screen = _three_ape_tab(_month_screen)
    try:
        assert _categories(screen.right_table) == ["Blog", "Pod"]

        screen.left_checks["ape-1"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Blog"]
    finally:
        root.destroy()


def test_vtfm14_the_week_tab_right_panel_follows_the_ticks():
    """VTF-M1.4 — ticking APEs narrows the week to their tactics.

    The two panels hold different kinds of record here, so the join is the
    tactic's `annual_plan_element_id` rather than a shared id.
    """
    left = [_ape_row(1, category="Blog"), _ape_row(2, category="Pod")]
    right = [_tactic_row(1, "ape-1", category="Blog"),
             _tactic_row(2, "ape-2", category="Pod"),
             _tactic_row(3, "ape-2", category="Pod")]
    root, screen = _week_screen(left, right)
    try:
        assert _categories(screen.right_table) == ["Blog", "Pod", "Pod"]

        screen.left_checks["ape-2"].set(True)
        screen.refresh_right_panel()
        assert [row["id"] for row in screen.right_items] == ["wt-2", "wt-3"]
        assert _categories(screen.right_table) == ["Pod", "Pod"]
    finally:
        root.destroy()


def test_vtfm15_no_tick_is_no_filter_on_the_ape_tabs():
    """VTF-M1.5 — no tick ticked is every right-hand row, on all four tabs.

    The annual tab is `test_vtfm15_no_tick_is_no_filter`; these are the other
    three. An untouched screen must look exactly as it did before VTF-M1.
    """
    for builder, expected in ((_quarter_screen, ["Blog", "Pod"]),
                              (_month_screen, ["Blog", "Pod"])):
        root, screen = _three_ape_tab(builder)
        try:
            assert _categories(screen.right_table) == expected
            screen.left_checks["ape-1"].set(True)
            screen.refresh_right_panel()
            assert _categories(screen.right_table) == ["Blog"]
            screen.left_checks["ape-1"].set(False)
            screen.refresh_right_panel()
            assert _categories(screen.right_table) == expected
        finally:
            root.destroy()

    root, screen = _week_screen(
        [_ape_row(1)], [_tactic_row(1, "ape-1"), _tactic_row(2, "ape-9")])
    try:
        assert [row["id"] for row in screen.right_items] == ["wt-1", "wt-2"]
        screen.left_checks["ape-1"].set(True)
        screen.refresh_right_panel()
        assert [row["id"] for row in screen.right_items] == ["wt-1"]
        screen.left_checks["ape-1"].set(False)
        screen.refresh_right_panel()
        assert [row["id"] for row in screen.right_items] == ["wt-1", "wt-2"]
    finally:
        root.destroy()


def test_vtfm16_the_tick_refreshes_the_ape_tabs_without_a_button():
    """VTF-M1.6 — each APE tab's checkbox carries the command itself."""
    for builder in (_quarter_screen, _month_screen):
        root, screen = _three_ape_tab(builder)
        try:
            boxes = _checkboxes(screen)
            assert len(boxes) == 3
            boxes[1].toggle()
            assert screen.left_checks["ape-2"].get() is True
            assert _categories(screen.right_table) == ["Pod"]
        finally:
            root.destroy()

    root, screen = _week_screen(
        [_ape_row(1), _ape_row(2)],
        [_tactic_row(1, "ape-1"), _tactic_row(2, "ape-2")])
    try:
        boxes = _checkboxes(screen)
        assert len(boxes) == 2
        boxes[0].toggle()
        assert [row["id"] for row in screen.right_items] == ["wt-1"]
    finally:
        root.destroy()


def test_vtfm17_the_dropdown_does_not_reach_the_right_panel():
    """VTF-M1.7 — a dropdown narrows the left list, and so which rows can be
    ticked; it leaves the right panel alone.

    Decision D2, in the user's words: *"Only the left panel is filtered. The
    right panel is filtered by selecting a record on the left panel."*
    """
    left = [_ape_row(1, subsegment="Living Systems", category="Blog"),
            _ape_row(2, subsegment="Other Systems", category="Pod")]
    right = [_ape_row(1, subsegment="Living Systems", category="Blog"),
             _ape_row(2, subsegment="Other Systems", category="Pod")]
    root, screen = _quarter_screen(left, right)
    try:
        assert _categories(screen.left_table) == ["Blog", "Pod"]
        assert _categories(screen.right_table) == ["Blog", "Pod"]

        screen.subsegment_filter_var.set("Living Systems")
        screen.on_filters_changed()

        # The left list is narrowed; the right panel is not.
        assert _categories(screen.left_table) == ["Blog"]
        assert _categories(screen.right_table) == ["Blog", "Pod"]
    finally:
        root.destroy()


def test_vtfm19_a_dropdown_that_hides_a_ticked_row_stops_its_filter():
    """VTF-M1.9 — a tick the dropdown has hidden stops narrowing the right.

    The two filters compose in one direction only. A tick on a row the user
    can no longer see is a filter they cannot clear, so it is ignored, and
    with no visible tick left the right panel shows every row again.
    """
    left = [_ape_row(1, subsegment="Living Systems", category="Blog"),
            _ape_row(2, subsegment="Other Systems", category="Pod")]
    right = [_ape_row(1, subsegment="Living Systems", category="Blog"),
             _ape_row(2, subsegment="Other Systems", category="Pod")]
    root, screen = _quarter_screen(left, right)
    try:
        screen.left_checks["ape-2"].set(True)
        screen.refresh_right_panel()
        assert _categories(screen.right_table) == ["Pod"]

        screen.subsegment_filter_var.set("Living Systems")
        screen.on_filters_changed()

        assert screen.left_checks["ape-2"].get() is True
        assert screen._ticked_ape_ids() == set()
        assert _categories(screen.right_table) == ["Blog", "Pod"]
    finally:
        root.destroy()


# ------------------------------------------------------------------ VTF-M2

def test_vtfm21_the_dropdown_is_a_left_panel_filter():
    """VTF-M2.1 — on all three APE tabs the dropdown leaves the right panel.

    Until this criterion `on_filters_changed` applied `_filtered_rows` to both
    panels, which gave the right panel two filters and the tick nothing to do.
    """
    for builder in (_quarter_screen, _month_screen):
        left = [_ape_row(1, subsegment="Living Systems", category="Blog"),
                _ape_row(2, subsegment="Other Systems", category="Pod")]
        root, screen = builder(left, list(left))
        try:
            screen.segment_filter_var.set("All")
            screen.subsegment_filter_var.set("Other Systems")
            screen.on_filters_changed()
            assert _categories(screen.left_table) == ["Pod"]
            assert _categories(screen.right_table) == ["Blog", "Pod"]
        finally:
            root.destroy()

    # APE Week Assignment bakes its dropdown filter into the row lists rather
    # than applying it at render time, so the assertion is on the lists.
    left = [_ape_row(1, subsegment="Living Systems", category="Blog"),
            _ape_row(2, subsegment="Other Systems", category="Pod")]
    right = [_tactic_row(1, "ape-1", category="Blog"),
             _tactic_row(2, "ape-2", category="Pod")]
    root, screen = _week_screen(left, right)
    try:
        screen.subsegment_filter_var.set("Other Systems")
        screen.on_filters_changed()
        assert [row["id"] for row in screen.left_items] == ["ape-2"]
        assert [row["id"] for row in screen.right_items] == ["wt-1", "wt-2"]
    finally:
        root.destroy()


def test_vtfm22_the_options_still_come_from_the_left_items():
    """VTF-M2.2 — the dropdown's options are built from the left items.

    The dropdowns are the left panel's filter, so a value that exists only on
    the right is not an option: offering one would be an option that narrows
    the left list to nothing.
    """
    left = [_ape_row(1, subsegment="Living Systems")]
    right = [_ape_row(9, subsegment="Right Only")]
    root, screen = _quarter_screen(left, right)
    try:
        values = screen.subsegment_filter_combo.cget("values")
        assert "Living Systems" in values
        assert "Right Only" not in values
    finally:
        root.destroy()


def test_vtfm23_week_actions_already_obeys_the_rule():
    """VTF-M2.3 — APE Week Actions is unchanged: its dropdowns filter the
    left list, and reach the right panel only to clear a hidden selection.

    Driven through the real method on a stub, so no display is needed. The
    right panel is reloaded by `select_tactic`; a filter that leaves the
    selection visible must not call it.
    """
    from src.getmoredone.screens.week_actions import WeekActionsScreen

    rows = [{"id": "t-1"}, {"id": "t-2"}]

    def _stub(selected, visible_ids):
        calls = []
        return calls, SimpleNamespace(
            tactic_rows=list(rows),
            visible_rows=[],
            selected_tactic_id=selected,
            filters=SimpleNamespace(
                filtered=lambda rs: [r for r in rs if r["id"] in visible_ids]),
            _render_tactics=lambda: calls.append("render_left"),
            select_tactic=lambda tid: calls.append(("select", tid)),
            _report_counts=lambda: None,
        )

    # The selection survives the filter: the left list is re-rendered and the
    # right panel is not touched.
    calls, stub = _stub("t-1", {"t-1"})
    WeekActionsScreen.on_filters_changed(stub)
    assert stub.visible_rows == [{"id": "t-1"}]
    assert calls == ["render_left"]

    # The filter hides the selection: the right panel is cleared, which is the
    # one direction in which a left filter may reach it.
    calls, stub = _stub("t-2", {"t-1"})
    WeekActionsScreen.on_filters_changed(stub)
    assert calls == [("select", None)]


# ------------------------------------------------- VTF-S10: the second pass

def test_vtfs10_the_count_on_the_status_line_follows_the_tick():
    """VTF-S10 — a number that describes the panel is read off the panel.

    APE Week Assignment is the only one of the five tabs whose status line
    carries a count, and until 2026-11-11 only Load Week wrote it. So a tick
    narrowed the panel and its heading while the line two rows above went on
    naming the pre-filter total: three rows on screen reduced to two, and the
    status line still said three.
    """
    left = [_ape_row(1, category="Blog"), _ape_row(2, category="Pod")]
    right = [_tactic_row(1, "ape-1", category="Blog"),
             _tactic_row(2, "ape-2", category="Pod"),
             _tactic_row(3, "ape-2", category="Pod")]
    root, screen = _week_screen(left, right)
    try:
        assert screen.status_label.cget("text") == (
            "2 month item(s) on left, 3 weekly tactic(s) on right")

        screen.left_checks["ape-1"].set(True)
        screen.refresh_right_panel()

        assert _categories(screen.right_table) == ["Blog"], (
            "the fixture must really be narrowed, or the count proves nothing")
        assert screen.status_label.cget("text") == (
            "2 month item(s) on left, 1 weekly tactic(s) on right"
        ), screen.status_label.cget("text")
    finally:
        root.destroy()


# ------------------------------------------ UPD-A12, one wording for the filter labels

def _label_texts(widget):
    import customtkinter as ctk

    return [child.cget("text") for child in widget.winfo_children()
            if isinstance(child, ctk.CTkLabel)]


def test_upda12_weekly_items_writes_the_filter_labels_out():
    """UPD-A12 — APE Week Assignment says SubSegment and Category, as the
    APE tabs and the column headings do, not Sub and Cat.

    Spec: docs/spec_coverage.md#filter-label-wording-upd-a12-2026-11-13
    """
    root, screen = _week_screen()
    try:
        texts = _label_texts(screen.filter_row)
        assert ["Segment:", "SubSegment:", "Category:"] == [
            t for t in texts if t in ("Segment:", "SubSegment:", "Category:", "Sub:", "Cat:")]
    finally:
        root.destroy()


def test_upda12_the_shared_filter_combos_write_the_labels_out():
    """UPD-A12 — ``LineageFilters.build_combos`` (APE Week Actions) uses the same words."""
    import customtkinter as ctk
    from src.getmoredone.screens.lineage_filters import LineageFilters

    root = withdrawn_root()
    try:
        frame = ctk.CTkFrame(root)
        LineageFilters(lambda row: ("", "", "")).build_combos(frame, 0, lambda: None)
        assert _label_texts(frame) == ["Segment:", "SubSegment:", "Category:"]
    finally:
        root.destroy()
