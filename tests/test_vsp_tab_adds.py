"""The VSP tabs' bottom Add New: what each one offers, writes and reports.

Spec: docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md

Every test name carries the criterion ID it verifies (VTF-M3, VTF-M4, VTF-M5).

The user asked, 2026-11-11: *"All the Tabs have to have Add NEW for the records
in the Right hand side ... buttons go on the bottom"*. With the tick now a
filter (VTF-M1), the header Save that read the ticks had nothing left to read,
so these four tabs lost their only way to add a record and gained a dialog in
its place.

**What is not here.** The one hop these tests cannot reach is the dialog's own
``on_confirm`` -> ``report`` link inside ``open_pick_record_dialog``, because a
real ``CTkToplevel`` puts a window on screen and the mapped-window count is
pinned by tests/test_ci_contract.py. The hop either side of it is asserted:
each tab hands the dialog its real write and its real status line
(VTF-M3.7), and each write reconciles and returns a sentence. The join is
VTF-N2 on the manual walk, and it is the same function for all four tabs, so
it is one check, not four.

Screens here are built on a **withdrawn** root, which adds nothing to that
count either.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Self-contained path bootstrap, for the reason test_vsp_tab_filters carries
# one: tests/test_ci_contract.py imports every test file with the repo root
# stripped from sys.path.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

import customtkinter as ctk  # noqa: E402

from src.getmoredone.screens import annual_vision_segments as annual_mod  # noqa: E402
from src.getmoredone.screens import ape_assignment as quarter_mod  # noqa: E402
from src.getmoredone.screens import ape_period_view as month_mod  # noqa: E402
from src.getmoredone.screens import weekly_items as week_mod  # noqa: E402
from src.getmoredone.screens.annual_vision_segments import (  # noqa: E402
    AnnualVisionSegmentsScreen,
)
from src.getmoredone.screens.ape_assignment import APEAssignmentScreen  # noqa: E402
from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen  # noqa: E402
from src.getmoredone.screens.pick_record_dialog import (  # noqa: E402
    describe_lineage,
    open_pick_record_dialog,
)
from src.getmoredone.screens.weekly_items import WeeklyItemsScreen  # noqa: E402
from tests.weekly_tactic_fixtures import make_vps, seed_ape  # noqa: E402

YEAR = 2026
WEEK_START = "2026-02-23"


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


def _bind(stub, cls, *names):
    """Put real methods on a stub, bound to it.

    A function set as a namespace attribute is not a bound method, so
    ``self._add_options()`` inside a real method would arrive one argument
    short.
    """
    for name in names:
        setattr(stub, name, getattr(cls, name).__get__(stub, cls))
    return stub


def _tick(value=True):
    return SimpleNamespace(get=lambda: value)


def _all_filters_open():
    """The three dropdown variables the APE tabs read, all on "All"."""
    return {
        "segment_filter_var": SimpleNamespace(get=lambda: "All"),
        "subsegment_filter_var": SimpleNamespace(get=lambda: "All"),
        "category_filter_var": SimpleNamespace(get=lambda: "All"),
    }


def _row(idx, category, **extra):
    """One VSP row, with the lineage triple every tab's dialog labels from."""
    row = {
        "id": idx,
        "segment_name": "Purposeful Work",
        "subsegment_name": "Living Systems",
        "category_name": category,
        "key_field": category,
    }
    row.update(extra)
    return row


def _vision_element(idx, category):
    return _row(f"ve-{idx}", category)


def _annual_row(idx, vision_element_id, category):
    return _row(f"ave-{idx}", category, year=YEAR,
                vision_element_id=vision_element_id)


def _fake_annual_vps(left_rows, right_rows):
    """A VPS manager double returning real dicts, not MagicMock attributes."""
    return SimpleNamespace(
        get_vision_elements=lambda: list(left_rows),
        get_annual_vision_elements=lambda year: list(right_rows),
        get_vision_categories=lambda: [],
        get_vision_subsegments=lambda: [],
        get_segment_color_map=lambda: {},
        resolve_segment_color=lambda name, colors: "",
    )


def _categories(table):
    """The Category cell of every rendered row, in grid order.

    The table pads and clamps a cell's text to its column width, so the
    fixtures use short category names and this strips the padding.
    """
    return [cells["category"].cget("text").strip() for _frame, cells in table.rows]


def _annual_stub(events, left=(), right=(), vps=None):
    stub = SimpleNamespace(
        year_var=SimpleNamespace(get=lambda: str(YEAR)),
        left_items=list(left),
        right_items=list(right),
        left_checks={},
        vps_manager=vps or SimpleNamespace(
            create_annual_records_from_vision_element=lambda *a: events.append(a)),
        refresh_lists=lambda: events.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: events.append(kw["text"])),
    )
    _bind(stub, AnnualVisionSegmentsScreen, "_parse_year",
          "_ticked_vision_element_ids", "_add_options", "_add_default",
          "_perform_add", "open_add_dialog")
    # `write` is whichever method this tab hands the dialog as `on_confirm`.
    stub.write = stub._perform_add
    return stub


def _quarter_stub(events, left=(), right=(), assign=None):
    # The sentence is reconciled against the rows the panel was redrawn from
    # (APC-M6.3), so a fixture whose refresh does not pick up the write would
    # read as "reported assigned but are not in Q4" -- and that is the
    # reconciliation working, not the write failing. `held` is this fixture's
    # quarter, and the redraw re-reads it exactly as refresh_lists does.
    held = [row["id"] for row in right]

    def default_assign(ape_id, quarter):
        events.append((ape_id, quarter))
        held.append(ape_id)
        return True

    stub = SimpleNamespace(
        _parse_period=lambda: (YEAR, 4),
        left_items=list(left),
        right_items=list(right),
        left_checks={},
        vps_manager=SimpleNamespace(
            assign_ape_to_quarter=assign or default_assign),
        status_label=SimpleNamespace(configure=lambda **kw: events.append(kw["text"])),
        _describe_quarter_assignment=APEAssignmentScreen._describe_quarter_assignment,
        **_all_filters_open(),
    )
    stub.refresh_lists = lambda: (
        events.append("refresh"),
        setattr(stub, "right_items", [{"id": i} for i in held]),
    )
    _bind(stub, APEAssignmentScreen, "_filtered_rows", "_visible_left_items",
          "_ticked_ape_ids", "_ids_in_quarter", "_assign_one", "_add_options",
          "_add_default", "_perform_add", "open_add_dialog")
    stub.write = stub._perform_add
    return stub


def _month_stub(events, left=(), right=(), assign=None):
    # As in _quarter_stub: the redraw has to pick the write up, or the
    # reconciliation reports a row the panel does not show.
    held = [row["id"] for row in right]

    def default_assign(ape_id, quarter, month):
        events.append((ape_id, quarter, month))
        held.append(ape_id)
        return True

    stub = SimpleNamespace(
        _parse_period=lambda: (YEAR, 4, 11),
        left_items=list(left),
        right_items=list(right),
        left_checks={},
        vps_manager=SimpleNamespace(
            assign_ape_to_month=assign or default_assign),
        status_label=SimpleNamespace(configure=lambda **kw: events.append(kw["text"])),
        _describe_month_assignment=APEPeriodViewScreen._describe_month_assignment,
        **_all_filters_open(),
    )
    stub.refresh_lists = lambda: (
        events.append("refresh"),
        setattr(stub, "right_items", [{"id": i} for i in held]),
    )
    _bind(stub, APEPeriodViewScreen, "_filtered_rows", "_visible_left_items",
          "_ticked_ape_ids", "_ids_in_month", "_assign_one", "_add_options",
          "_add_default", "_perform_add", "open_add_dialog")
    stub.write = stub._perform_add
    return stub


def _week_stub(events, left=(), create=None):
    stub = SimpleNamespace(
        _selected_week_context=lambda: (WEEK_START, YEAR, 2),
        left_items=list(left),
        left_checks={},
        vps_manager=SimpleNamespace(
            create_week_action_items_for_ape=create or (
                lambda *a: events.append(a) or {
                    "created_count": 1, "skipped_count": 0, "collided_count": 0})),
        refresh=lambda: events.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: events.append(kw["text"])),
        _describe_week_creation=WeeklyItemsScreen._describe_week_creation,
    )
    _bind(stub, WeeklyItemsScreen, "_ticked_ape_ids", "_add_options",
          "_add_default", "_create_tactic_for", "open_add_dialog")
    # This tab hands the dialog the shared write itself: the drag path calls
    # the same method, so there is no one-row wrapper around it.
    stub.write = stub._create_tactic_for
    return stub


# ------------------------------------------------------------------- VTF-M3.1

def test_vtfm31_the_annual_tab_adds_from_a_vision_element():
    """VTF-M3.1 — the picked Vision Element's annual records really get created.

    The dialog offers only the Vision Elements the year has no annual record
    for, because ``create_annual_records_from_vision_element`` is idempotent:
    offering one that is already there is an option that changes nothing.
    """
    events = []
    left = [_vision_element(1, "Blog"), _vision_element(2, "Pod")]
    right = [_annual_row(1, "ve-1", "Blog")]
    stub = _annual_stub(events, left=left, right=right)

    assert [key for key, _label in stub._add_options()] == ["ve-2"], (
        "a Vision Element the year already carries must not be offered again"
    )

    said = stub._perform_add("ve-2")

    assert (YEAR, "ve-2") in events, f"the create never happened: {events}"
    assert "refresh" in events, "the panel must be redrawn before the sentence"
    assert said == f"Added {describe_lineage(left[1])} to {YEAR}.", said


# ------------------------------------------------------------------- VTF-M3.2

def test_vtfm32_the_quarter_tab_assigns_from_a_dialog():
    """VTF-M3.2 — the year's APEs, minus the ones Q4 already holds."""
    events = []
    left = [_row("ape-1", "Blog"), _row("ape-2", "Pod")]
    stub = _quarter_stub(events, left=left, right=[_row("ape-1", "Blog")])

    assert [key for key, _label in stub._add_options()] == ["ape-2"], (
        "an APE already in the quarter must not be offered"
    )

    said = stub._perform_add("ape-2")

    assert ("ape-2", 4) in events, f"the assignment never happened: {events}"
    assert said.startswith("Assigned 1 APE(s) to Q4."), said


# ------------------------------------------------------------------- VTF-M3.3

def test_vtfm33_the_month_tab_assigns_from_a_dialog():
    """VTF-M3.3 — the quarter's APEs, minus the ones M11 already holds."""
    events = []
    left = [_row("ape-1", "Blog"), _row("ape-2", "Pod")]
    stub = _month_stub(events, left=left, right=[_row("ape-2", "Pod")])

    assert [key for key, _label in stub._add_options()] == ["ape-1"], (
        "an APE already in the month must not be offered"
    )

    said = stub._perform_add("ape-1")

    assert ("ape-1", 4, 11) in events, f"the assignment never happened: {events}"
    assert said.startswith("Assigned 1 APE(s) to M11."), said


# ------------------------------------------------------------------- VTF-M3.4

def test_vtfm34_the_week_tab_adds_a_weekly_tactic():
    """VTF-M3.4 — the tactic is created for the selected week, under the APE.

    Every month-assigned APE is offered, including one that already carries a
    tactic in another week: one APE can have a tactic in several weeks, and
    ``create_week_action_items_for_ape`` reports a collision in the selected
    week itself rather than being asked not to.
    """
    events = []
    left = [_row("ape-1", "Blog"), _row("ape-2", "Pod")]
    stub = _week_stub(events, left=left)

    assert [key for key, _label in stub._add_options()] == ["ape-1", "ape-2"]

    said = stub._create_tactic_for("ape-2")

    assert ("ape-2", YEAR, 2, [WEEK_START]) in events, (
        f"the tactic was not created for the selected week: {events}"
    )
    assert "refresh" in events, "the panel must be redrawn before the sentence"
    assert "Created 1" in said, said


def test_vtfm34_the_week_tab_refuses_before_a_week_is_chosen():
    """VTF-M3.4 — with no Week Start there is no week to create for.

    ``create_week_action_items_for_ape`` takes the week as an argument, so a
    path that reached it without one would write to whatever the empty string
    resolves to.
    """
    events = []
    stub = _week_stub(events, left=[_row("ape-1", "Blog")])
    stub._selected_week_context = lambda: None

    said = stub._create_tactic_for("ape-1")

    assert said == "Choose a Week Start first.", said
    assert events == [], f"nothing may be written or redrawn: {events}"


# ------------------------------------------------------------------- VTF-M3.6

def test_vtfm36_the_dialog_defaults_to_one_tick():
    """VTF-M3.6 — one tick preselects it; none or two preselect nothing.

    Guessing between two ticked rows would create a record the user did not
    pick, and the Add New dialog is the one control on these tabs that writes
    without a further confirmation.
    """
    rows = [_row("a", "Blog"), _row("b", "Pod")]
    cases = [
        (_annual_stub([], left=[_vision_element(1, "Blog"),
                                _vision_element(2, "Pod")]),
         {"ve-1": _tick(), "ve-2": _tick(False)}, "ve-1"),
        (_quarter_stub([], left=rows), {"a": _tick(), "b": _tick(False)}, "a"),
        (_month_stub([], left=rows), {"a": _tick(False), "b": _tick()}, "b"),
        (_week_stub([], left=rows), {"a": _tick(), "b": _tick(False)}, "a"),
    ]

    for stub, checks, expected in cases:
        stub.left_checks = checks
        assert stub._add_default() == expected, (type(stub), checks)

        stub.left_checks = {key: _tick() for key in checks}
        assert stub._add_default() is None, "two ticks must not be guessed between"

        stub.left_checks = {key: _tick(False) for key in checks}
        assert stub._add_default() is None, "no tick is no default"


# ------------------------------------------------------------------- VTF-M3.7

def test_vtfm37_add_new_reports_on_the_status_line():
    """VTF-M3.7 — every tab hands the dialog its own write and its own status line.

    Before VTF-M3 three of these four tabs had no status surface at all, which
    is the fault APC-M2.3 was raised for: a refusal looked exactly like a
    success. The stand-in records what ``open_add_dialog`` passed instead of
    opening a window, so both ends are named — the sentence comes from the
    tab's real ``_perform_add``, and it is written to the tab's real label.
    """
    rows = [_row("a", "Blog")]
    cases = [
        (annual_mod, _annual_stub([], left=[_vision_element(1, "Blog")])),
        (quarter_mod, _quarter_stub([], left=rows)),
        (month_mod, _month_stub([], left=rows)),
        (week_mod, _week_stub([], left=rows)),
    ]

    for module, stub in cases:
        said = []
        stub.status_label = SimpleNamespace(
            configure=lambda **kw: said.append(kw["text"]))
        captured = {}
        original = module.open_pick_record_dialog
        module.open_pick_record_dialog = lambda _parent, **kw: captured.update(kw)
        try:
            stub.open_add_dialog()
        finally:
            module.open_pick_record_dialog = original

        assert captured, f"{module.__name__} opened no dialog"
        assert captured["on_confirm"] == stub.write, module.__name__
        captured["report"]("reported it")
        assert said == ["reported it"], (module.__name__, said)


def test_vtfm37_a_dialog_with_nothing_to_offer_refuses_on_the_status_line():
    """VTF-M3.7 — the one outcome that opens no window still reaches the user.

    ``open_pick_record_dialog`` reports and returns ``None`` on an empty option
    list, so this drives the real dialog function. It is the case a user meets
    by pressing Add New twice.
    """
    events = []
    stub = _annual_stub(events, left=[_vision_element(1, "Blog")],
                        right=[_annual_row(1, "ve-1", "Blog")])

    assert stub._add_options() == [], "the fixture must leave nothing to offer"
    assert stub.open_add_dialog() is None, "no window opens with nothing to offer"
    assert events == [
        f"Every Vision Element already has an annual record for {YEAR}. "
        f"Add a Vision Element on the Vision Elements tab first."
    ], events


def test_vtfm37_open_pick_record_dialog_reports_its_empty_refusal():
    """VTF-M3.7 — the shared refusal, asserted on the shared function.

    The four tabs pass four different sentences through this one branch; the
    tab tests assert their own wording, this asserts that the branch reports at
    all rather than returning in silence.
    """
    said = []
    result = open_pick_record_dialog(
        None,
        title="t", prompt="p", options=[],
        report=said.append,
        on_confirm=lambda _key: pytest.fail("there was nothing to confirm"),
        empty_message="nothing to add",
    )
    assert result is None
    assert said == ["nothing to add"], said


# ------------------------------------------------------------------- VTF-M3.8

def test_vtfm38_the_new_record_appears_at_once():
    """VTF-M3.8 — the right panel shows the new row with no Refresh pressed.

    The real screen, because this criterion is about the panel and not about
    the write: a ``_perform_add`` that wrote and reported without redrawing
    would leave the user looking at a panel that disagrees with the sentence
    under it.
    """
    left = [_vision_element(1, "Blog"), _vision_element(2, "Pod")]
    right = [_annual_row(1, "ve-1", "Blog")]
    created = []

    def create(year, vision_element_id):
        created.append((year, vision_element_id))
        right.append(_annual_row(2, vision_element_id, "Pod"))
        return {"annual_plan_element_id": "ape-2"}

    root = _root()
    try:
        vps = _fake_annual_vps(left, right)
        vps.create_annual_records_from_vision_element = create
        screen = AnnualVisionSegmentsScreen(root, vps, SimpleNamespace(vps_manager=vps))
        screen.year_var.set(str(YEAR))
        screen.refresh_lists()
        screen.update_idletasks()
        assert _categories(screen.right_table) == ["Blog"]

        said = screen._perform_add("ve-2")
        screen.update_idletasks()

        assert created == [(YEAR, "ve-2")], created
        assert _categories(screen.right_table) == ["Blog", "Pod"], (
            "the new annual record must be on screen without a Refresh"
        )
        assert "Pod" in said, said
    finally:
        root.destroy()


# ------------------------------------------------------------------- VTF-M4.1

def test_vtfm41_no_tab_still_saves_from_the_ticks():
    """VTF-M4.1 — ``add_selected`` is gone from all four tabs.

    It is what read the ticks as a selection to write from, which is the
    reading VTF-M1 replaced. Leaving it in place would leave a second meaning
    for a tick reachable from any new caller.
    """
    for cls in (AnnualVisionSegmentsScreen, APEAssignmentScreen,
                APEPeriodViewScreen, WeeklyItemsScreen):
        assert not hasattr(cls, "add_selected"), (
            f"{cls.__name__} still writes from the ticks"
        )


# ------------------------------------------------------------------- VTF-M5.5

def test_vtfm55_a_new_tactic_is_not_invisible(tmp_path):
    """VTF-M5.5 — the created tactic satisfies the right panel's own query.

    The panel asks ``get_weekly_action_items(week_start_date=..., ape_only=True)``,
    so a tactic created without the APE link, or dated into another week, would
    be written and then not shown — a record the user cannot reach and cannot
    see was not created. The real manager on a real database, because that is
    the only fixture in which the create and the query can disagree.
    """
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps, year=YEAR)
        assert vps.assign_ape_to_quarter(ape_id, 1) is True
        assert vps.assign_ape_to_month(ape_id, 1, 2) is True
        assert vps.get_weekly_action_items(
            week_start_date=WEEK_START, ape_only=True) == []

        events = []
        stub = SimpleNamespace(
            _selected_week_context=lambda: (WEEK_START, YEAR, 2),
            vps_manager=vps,
            refresh=lambda: events.append("refresh"),
            _describe_week_creation=WeeklyItemsScreen._describe_week_creation,
        )
        _bind(stub, WeeklyItemsScreen, "_create_tactic_for")

        said = stub._create_tactic_for(ape_id)

        assert "refresh" in events, said
        shown = vps.get_weekly_action_items(
            week_start_date=WEEK_START, ape_only=True)
        assert [row["annual_plan_element_id"] for row in shown] == [ape_id], (
            f"the panel's own query does not return the new tactic: {shown}"
        )
    finally:
        vps.close()
