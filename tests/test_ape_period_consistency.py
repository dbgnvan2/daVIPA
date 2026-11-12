"""APE quarter/month consistency.

Purpose: keep an APE's quarter flag and month flag from contradicting each
         other, and keep a month-assigned APE visible in APE Weekly.
Spec:    docs/spec_2026-11-07_ape_period_consistency.md

The fault these cover, from the live demo database: one APE with
``q1 = 1, q3 = 1, m11 = 1``. Month 11 is in Q4, so APE Weekly — which asked
for ``q4 = 1 AND m11 = 1`` for a November week — found nothing, while APE Month
showed it under Q3. Nothing in the stack owned the rule that month 11 belongs
to quarter 4.
"""

import ast
import logging
import pathlib
import sqlite3
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

# Self-contained path bootstrap, for the same reason test_after_tracker.py
# carries one: test_rm3d imports every test file with the repo root stripped
# from sys.path, and this file sorts second, so it cannot rely on an earlier
# file having put the root back.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

from src.getmoredone.date_utils import (  # noqa: E402
    MONTHS_OF_QUARTER,
    QUARTER_OF_MONTH,
    current_quarter,
    months_of_quarter,
    quarter_of_month,
)
from src.getmoredone.vps_manager import VPSManager  # noqa: E402
from tests.weekly_tactic_fixtures import (  # noqa: E402
    make_vps,
    seed_ape,
    seed_second_ape,
)


def _bind(stub, cls, *names):
    """Put real methods on a ``SimpleNamespace`` stub, bound to that stub.

    A function set as a namespace attribute is not a bound method, so
    ``self._assign_one(x, y)`` inside a real method would arrive one argument
    short. These tests drive real methods against hand-built stubs, so the
    binding has to be done here.
    """
    for name in names:
        setattr(stub, name, getattr(cls, name).__get__(stub, cls))
    return stub


# --------------------------------------------------------------------------
# APC-M1 — one quarter <-> month mapping
# --------------------------------------------------------------------------

def test_apcm11_quarter_of_month_covers_every_month():
    """APC-M1.1 — twelve months, the right quarter for each, and no fourth."""
    assert [quarter_of_month(m) for m in range(1, 13)] == [
        1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4
    ]
    assert quarter_of_month(11) == 4, "the month the reported fault turned on"
    for bad in (0, 13, -1, "x", None):
        with pytest.raises(ValueError):
            quarter_of_month(bad)


def test_apcm11_months_of_quarter_covers_every_quarter():
    """APC-M1.1 — the inverse, and it is the exact inverse."""
    assert months_of_quarter(4) == (10, 11, 12)
    seen = []
    for quarter in (1, 2, 3, 4):
        months = months_of_quarter(quarter)
        assert len(months) == 3
        for month in months:
            assert quarter_of_month(month) == quarter
        seen.extend(months)
    assert sorted(seen) == list(range(1, 13)), "every month in exactly one quarter"
    for bad in (0, 5, -1, "x", None):
        with pytest.raises(ValueError):
            months_of_quarter(bad)


def test_apcm12_weekly_tactic_mapping_is_not_a_second_literal():
    """APC-M1.2 — ``weekly_tactic`` re-exports the mapping, never redefines it.

    A source-level check because the defect is a *duplicate*, and two copies
    that agree today are behaviourally identical. Parsed, not grepped, and the
    count is exact: a floor would hide the narrowing this is written to catch.
    """
    module_path = Path("src/getmoredone/weekly_tactic.py")
    tree = ast.parse(module_path.read_text())

    month_keyed_literals = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        and len(node.keys) == 12
        and all(isinstance(k, ast.Constant) and isinstance(k.value, int) for k in node.keys)
    ]
    assert month_keyed_literals == [], (
        "weekly_tactic.py holds a second twelve-month mapping; "
        "date_utils.QUARTER_OF_MONTH is the one home for it"
    )

    from src.getmoredone.weekly_tactic import QUARTER_OF_MONTH as reexported
    assert reexported is QUARTER_OF_MONTH, "the same object, not an equal copy"


def test_apcm12_vps_manager_holds_no_quarter_months_literal():
    """APC-M1.3 — ``_clear_quarter_month_flags`` lost its private dict too."""
    tree = ast.parse(Path("src/getmoredone/vps_manager.py").read_text())
    quarter_keyed_literals = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        and len(node.keys) == 4
        and all(isinstance(k, ast.Constant) and k.value in (1, 2, 3, 4) for k in node.keys)
    ]
    assert quarter_keyed_literals == [], (
        "vps_manager.py holds its own quarter->months mapping; use months_of_quarter"
    )


def test_apcm13_clear_quarter_month_flags_uses_shared_mapping(tmp_path):
    """APC-M1.3 — behaviourally: unassigning Q4 clears m10-m12 and nothing else."""
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        for month in (2, 11, 12):
            vps.set_annual_plan_element_month(ape_id, month, True)
        vps.set_annual_plan_element_quarter(ape_id, 1, True)
        vps.set_annual_plan_element_quarter(ape_id, 4, True)

        assert vps.unassign_ape_from_quarter(ape_id, 4) is True

        row = vps.db.conn.execute(
            "SELECT q1, q4, m2, m10, m11, m12 FROM annual_plan_elements WHERE id = ?",
            (ape_id,),
        ).fetchone()
        assert row["q4"] == 0 and row["m11"] == 0 and row["m12"] == 0
        assert row["m2"] == 1, "a month outside Q4 must survive unassigning Q4"
        assert row["q1"] == 1, "another quarter's flag must survive"
    finally:
        vps.close()


def test_apcm14_week_context_carries_no_derived_quarter():
    """APC-M1.4 — the week context is (week_start, year, month); no quarter.

    It used to derive one with ``((month - 1) // 3) + 1`` purely so the
    left-panel lookup could demand the matching quarter flag. No caller on the
    screen read it, so it is gone rather than renamed.
    """
    from src.getmoredone.screens.weekly_items import WeeklyItemsScreen

    stub = SimpleNamespace(week_var=SimpleNamespace(get=lambda: "2026-11-02"))
    assert WeeklyItemsScreen._selected_week_context(stub) == ("2026-11-02", 2026, 11)

    blank = SimpleNamespace(week_var=SimpleNamespace(get=lambda: "  "))
    assert WeeklyItemsScreen._selected_week_context(blank) is None


# --------------------------------------------------------------------------
# APC-M2 — an inconsistent pair is refused, loudly
# --------------------------------------------------------------------------

def test_apcm21_mismatched_quarter_and_month_is_refused_and_writes_nothing(tmp_path):
    """APC-M2.1 — Q1 with M11 is how the reported row was created."""
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)

        assert vps.assign_ape_to_month(ape_id, 1, 11) is False

        row = vps.db.conn.execute(
            "SELECT q1, q4, m11 FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone()
        assert row["m11"] == 0, "a refused assignment must not set the month flag"
        assert row["q1"] == 0, "nor the quarter flag it was wrongly paired with"
        assert row["q4"] == 0, "nor the quarter the month actually belongs to"
    finally:
        vps.close()


@pytest.mark.parametrize("quarter,month", [(1, 4), (2, 11), (3, 1), (4, 9)])
def test_apcm21_every_mismatched_pair_is_refused(tmp_path, quarter, month):
    """APC-M2.1 — not just Q1/M11; any pair that cannot both be true."""
    vps = make_vps(tmp_path, name=f"mismatch_{quarter}_{month}.db")
    try:
        ape_id = seed_ape(vps)
        assert vps.assign_ape_to_month(ape_id, quarter, month) is False
        row = vps.db.conn.execute(
            f"SELECT q{quarter} AS q, m{month} AS m FROM annual_plan_elements WHERE id = ?",
            (ape_id,),
        ).fetchone()
        assert row["q"] == 0 and row["m"] == 0
    finally:
        vps.close()


def test_apcm22_matching_quarter_and_month_still_assigns(tmp_path):
    """APC-M2.2 — the guard refuses the impossible pair, not the real work."""
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)

        assert vps.assign_ape_to_month(ape_id, 4, 11) is True

        row = vps.db.conn.execute(
            "SELECT q4, m11 FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone()
        assert row["q4"] == 1 and row["m11"] == 1
    finally:
        vps.close()


def test_apcm23_save_reports_refused_assignments():
    """APC-M2.3 / APC-M2.5 — the wording, from the rows rather than a count.

    Four states, each named: assigned, partly assigned (the call failed but the
    month holds the row anyway), could not be assigned, and reported assigned
    but not in the month. Dropping any of them is P2.
    """
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    describe = APEPeriodViewScreen._describe_month_assignment

    assert describe(["a", "b", "c"], {"a", "b", "c"}, {"a", "b", "c"}, 11) == (
        "Assigned 3 APE(s) to M11."
    )

    said = describe(["a", "b", "c"], {"a"}, {"a"}, 11)
    assert said.startswith("Assigned 1 APE(s) to M11."), said
    assert "2 could not be assigned" in said, said
    assert "partly assigned" not in said, said

    # The half-written case: the call said no, the month holds it anyway.
    said = describe(["a", "b"], {"a"}, {"a", "b"}, 11)
    assert said.startswith("Assigned 1 APE(s) to M11."), said
    assert "1 partly assigned — in M11 with no month tactic behind it" in said, said
    assert "could not be assigned" not in said, said

    # And the other direction of P6: the call said yes, the row is not there.
    said = describe(["a"], {"a"}, set(), 11)
    assert said.startswith("Assigned 0 APE(s) to M11."), said
    assert "1 reported assigned but are not in M11" in said, said


def test_apcm23_save_button_reaches_the_reporting():
    """APC-M2.3 — the wiring, not just the wording (P25).

    Asserting the message in isolation would pass with a Save that never calls
    it, which is what the screen did before this change: no status surface at
    all, so a refusal looked exactly like a success.
    """
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    said = []
    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4, 11),
        left_checks={"ape-ok": SimpleNamespace(get=lambda: True),
                     "ape-bad": SimpleNamespace(get=lambda: True)},
        vps_manager=SimpleNamespace(
            assign_ape_to_month=lambda ape_id, *_a: ape_id == "ape-ok"
        ),
        refresh_lists=lambda: said.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[{"id": "ape-ok"}],
        _describe_month_assignment=APEPeriodViewScreen._describe_month_assignment,
    )
    _bind(stub, APEPeriodViewScreen, "_assign_one", "_ids_in_month")

    APEPeriodViewScreen.add_selected(stub)

    assert "refresh" in said
    assert any("1 could not be assigned" in s for s in said if isinstance(s, str)), said


def test_apcm23_drag_path_reaches_the_same_reporting():
    """APC-M2.3 — the drop target reports too (P5: fix the siblings).

    The stub records the call as well as refusing it. ``_assign_one`` carries a
    broad ``except Exception``, so a stub that raised — including on a wrong
    argument count — would be swallowed and reported as an ordinary refusal,
    and an assertion on the message alone would pass. Asserting the recorded
    call is what keeps "the manager said no" apart from "the call blew up".
    """
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    said = []
    calls = []
    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4, 11),
        vps_manager=SimpleNamespace(
            assign_ape_to_month=lambda *a: calls.append(a) or False
        ),
        refresh_lists=lambda: said.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
        _describe_month_assignment=APEPeriodViewScreen._describe_month_assignment,
    )
    _bind(stub, APEPeriodViewScreen, "_assign_one", "_ids_in_month")

    # UPD-M4 moved the drag itself into screens/row_drag.py, so the stub no
    # longer fakes a pointer, a toplevel or a descendant walk: none of that is
    # this screen's any more, and it is covered by UPD-M2.2 to M2.4. What is
    # still this screen's is what a dropped row means, which is this method.
    APEPeriodViewScreen._assign_dragged_row(stub, {"id": "ape-bad"})

    assert calls == [("ape-bad", 4, 11)], (
        f"the drop must reach the manager with the parsed period, got {calls}"
    )
    assert any("could not be assigned" in s for s in said if isinstance(s, str)), said
    assert "refresh" in said, "a refused drop must not skip the redraw"


# --------------------------------------------------------------------------
# APC-M3 — the pickers cannot produce an invalid pair
# --------------------------------------------------------------------------

def test_apcm31_quarter_defaults_to_current_quarter():
    """APC-M3.1 — on 7 November the screen opens on Q4, not Q1."""
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    year, quarter, month = APEPeriodViewScreen.default_period(date(2026, 11, 7))
    assert (year, quarter, month) == (2026, 4, 11), (
        "the reported case: Q1 + M11 was the screen's opening state"
    )


@pytest.mark.parametrize("month", list(range(1, 13)))
def test_apcm34_default_month_is_always_inside_the_default_quarter(month):
    """APC-M3.4 — for every month of the year, not just today's."""
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    _year, quarter, got_month = APEPeriodViewScreen.default_period(date(2026, month, 15))
    assert got_month == month
    assert got_month in months_of_quarter(quarter)


def _picker_stub(quarter: str, month: str):
    """A stub with just the two variables and the combo the sync touches."""
    offered = []
    state = {"month": month}
    return state, offered, SimpleNamespace(
        quarter_var=SimpleNamespace(get=lambda: quarter),
        month_var=SimpleNamespace(
            get=lambda: state["month"],
            set=lambda v: state.__setitem__("month", v),
        ),
        month_combo=SimpleNamespace(configure=lambda **kw: offered.append(kw["values"])),
    )


def test_apcm32_month_combo_offers_only_that_quarters_months():
    """APC-M3.2 — Q3 offers 7, 8, 9; picking M11 under Q3 is not possible."""
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    _state, offered, stub = _picker_stub("3", "8")
    APEPeriodViewScreen._sync_month_choices(stub)

    assert offered == [["7", "8", "9"]], offered
    assert "11" not in offered[-1], "the pair the reported fault was built from"


def test_apcm33_changing_quarter_moves_month_into_range():
    """APC-M3.3 — an out-of-range month moves; an in-range one is left alone."""
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    moved, _offered, stub = _picker_stub("1", "11")
    APEPeriodViewScreen._sync_month_choices(stub)
    assert moved["month"] == "1", (
        "M11 under Q1 must be pulled into Q1, not left as an invalid pair"
    )

    kept, _offered, stub = _picker_stub("4", "11")
    APEPeriodViewScreen._sync_month_choices(stub)
    assert kept["month"] == "11", "a month already inside the quarter must not jump"


def test_apcm33_every_quarter_leaves_the_month_in_range():
    """APC-M3.3 — across all 48 (quarter, month) starting pairs."""
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    for quarter in (1, 2, 3, 4):
        for month in range(1, 13):
            state, _offered, stub = _picker_stub(str(quarter), str(month))
            APEPeriodViewScreen._sync_month_choices(stub)
            assert int(state["month"]) in months_of_quarter(quarter), (
                f"Q{quarter} left month {state['month']} selected"
            )


def test_apcm61_quarter_screen_defaults_to_current_quarter():
    """APC-M6 — the APE Quarter screen had the identical hard-coded "1"."""
    source = Path("src/getmoredone/screens/ape_assignment.py").read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Attribute) and target.attr == "quarter_var"):
            continue
        call = node.value
        assert isinstance(call, ast.Call), ast.dump(call)
        rendered = ast.unparse(call)
        assert "current_quarter" in rendered, (
            f"quarter_var still opens on a literal: {rendered}"
        )
        break
    else:
        pytest.fail("no self.quarter_var assignment found in ape_assignment.py")

    assert current_quarter(date(2026, 11, 7)) == 4


# --------------------------------------------------------------------------
# APC-M4 — a month-assigned APE shows in that month's weeks
# --------------------------------------------------------------------------

def test_apcm41_month_lookup_matches_on_month_flag_alone(tmp_path):
    """APC-M4.1 — the month flag is the month assignment."""
    vps = make_vps(tmp_path)
    try:
        in_november = seed_ape(vps, key_field="Blog")
        in_august = seed_second_ape(vps, key_field="Podcast")
        assert vps.assign_ape_to_month(in_november, 4, 11) is True
        assert vps.assign_ape_to_month(in_august, 3, 8) is True

        found = vps.get_annual_plan_elements_for_month(2026, 11)
        assert [row["id"] for row in found] == [in_november]

        assert vps.get_annual_plan_elements_for_month(2026, 10) == []
        assert vps.get_annual_plan_elements_for_month(2027, 11) == [], "year still filters"
        assert vps.get_annual_plan_elements_for_month(2026, 13) == []
        assert vps.get_annual_plan_elements_for_month(2026, 0) == []
    finally:
        vps.close()


def test_apcm42_orphan_month_flag_still_appears_in_november(tmp_path):
    """APC-M4.2 — the exact row from the demo database, with q4 still 0.

    The guard stops new ones and the migration repairs stored ones, but the
    lookup must not depend on either: this is the query that was returning
    nothing while the row sat in the table.
    """
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        vps.db.conn.execute(
            "UPDATE annual_plan_elements SET q1 = 1, q3 = 1, q4 = 0, m11 = 1 WHERE id = ?",
            (ape_id,),
        )
        vps.db.conn.commit()

        found = vps.get_annual_plan_elements_for_month(2026, 11)
        assert [row["id"] for row in found] == [ape_id], (
            "an APE with m11 = 1 and q4 = 0 was invisible in APE Weekly"
        )
    finally:
        vps.close()


def test_apcm43_screens_use_month_lookup():
    """APC-M4.3 — both screens ask by month, and the old method is gone."""
    assert not hasattr(VPSManager, "get_annual_plan_elements_for_period"), (
        "the quarter-and-month lookup is what hid the row; it has no callers left"
    )
    assert hasattr(VPSManager, "get_annual_plan_elements_for_month")

    for path in (
        "src/getmoredone/screens/weekly_items.py",
        "src/getmoredone/screens/ape_period_view.py",
    ):
        source = Path(path).read_text()
        assert "get_annual_plan_elements_for_month(" in source, path
        assert "get_annual_plan_elements_for_period(" not in source, path


def test_apcm43_weekly_screen_left_panel_asks_by_month_only():
    """APC-M4.3 — the call the screen actually makes, with real arguments."""
    from src.getmoredone.screens.weekly_items import WeeklyItemsScreen

    asked = []
    stub = SimpleNamespace(
        _selected_week_context=lambda: ("2026-11-02", 2026, 11),
        vps_manager=SimpleNamespace(
            get_annual_plan_elements_for_month=lambda *a: asked.append(a) or [],
            get_weekly_action_items=lambda **_k: [],
        ),
        _refresh_filter_options=lambda *_a: None,
        _ape_matches_filters=lambda _r: True,
        # VTF-M2.1 removed the right panel's dropdown filter, so
        # `_weekly_matches_filters` is gone and the right heading now comes
        # from `_right_title`. The assertion below is unchanged: what this
        # test is about is the arguments of the left panel's own query.
        _right_title=lambda: "",
        _render_lists=lambda: None,
        left_title_label=SimpleNamespace(configure=lambda **_k: None),
        right_title_label=SimpleNamespace(configure=lambda **_k: None),
        status_label=SimpleNamespace(configure=lambda **_k: None),
    )

    WeeklyItemsScreen.load_selected_week(stub)

    assert asked == [(2026, 11)], (
        f"the left panel must ask for the month, not a month and a quarter: {asked}"
    )


# --------------------------------------------------------------------------
# APC-M5 — existing orphan flags repaired
# --------------------------------------------------------------------------

def _orphan_row(db_path: Path, ape_id: str) -> None:
    """Write the demo database's exact shape: q1, q3 and m11, with no q4."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "UPDATE annual_plan_elements SET q1 = 1, q3 = 1, q4 = 0, m11 = 1 WHERE id = ?",
        (ape_id,),
    )
    conn.commit()
    conn.close()


def test_apcm51_migration_backfills_the_implied_quarter_flag(tmp_path):
    """APC-M5.1 — the implied quarter is set, and no quarter is cleared."""
    from src.getmoredone.vps_schema import VPSSchema

    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        conn = vps.db.conn
        conn.execute(
            "UPDATE annual_plan_elements SET q1 = 1, q3 = 1, q4 = 0, m11 = 1 WHERE id = ?",
            (ape_id,),
        )
        conn.commit()

        VPSSchema._repair_orphan_month_flags(conn)
        conn.commit()

        row = conn.execute(
            "SELECT q1, q2, q3, q4, m11 FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone()
        assert row["q4"] == 1, "m11 = 1 implies q4 = 1"
        assert row["q1"] == 1 and row["q3"] == 1, (
            "a quarter with no month yet is a real state; the repair must not clear it"
        )
        assert row["q2"] == 0, "the repair must not invent a quarter nothing implies"
        assert row["m11"] == 1, "the month flag itself is untouched"
    finally:
        vps.close()


def test_apcm52_dirty_state_orphan_quarter_flag_is_repaired_on_reopen(tmp_path):
    """APC-M5.2 — P8: the repair runs on a database that persists between runs.

    The row is written, the manager closed, and a second manager opened on the
    same file — which is how the user's demo database reaches the migration.
    """
    db_path = tmp_path / "dirty.db"
    first = VPSManager(str(db_path))
    try:
        ape_id = seed_ape(first)
    finally:
        first.close()

    _orphan_row(db_path, ape_id)

    before = sqlite3.connect(str(db_path))
    assert before.execute(
        "SELECT q4 FROM annual_plan_elements WHERE id = ?", (ape_id,)
    ).fetchone()[0] == 0, "the fixture must start dirty or this test proves nothing"
    before.close()

    second = VPSManager(str(db_path))
    try:
        row = second.db.conn.execute(
            "SELECT q1, q3, q4, m11 FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone()
        assert row["q4"] == 1, "opening the database must repair the orphan month flag"
        assert row["q1"] == 1 and row["q3"] == 1 and row["m11"] == 1

        found = second.get_annual_plan_elements_for_month(2026, 11)
        assert [r["id"] for r in found] == [ape_id], (
            "and APE Weekly must now find it for a November week"
        )
    finally:
        second.close()


def test_apcm53_migration_is_idempotent(tmp_path):
    """APC-M5.3 — a second run touches nothing, including ``updated_at``."""
    from src.getmoredone.vps_schema import VPSSchema

    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        conn = vps.db.conn
        conn.execute(
            "UPDATE annual_plan_elements SET q3 = 1, q4 = 0, m11 = 1 WHERE id = ?", (ape_id,)
        )
        conn.commit()

        VPSSchema._repair_orphan_month_flags(conn)
        conn.commit()
        after_first = dict(conn.execute(
            "SELECT q3, q4, m11, updated_at FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone())

        VPSSchema._repair_orphan_month_flags(conn)
        conn.commit()
        after_second = dict(conn.execute(
            "SELECT q3, q4, m11, updated_at FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone())

        assert after_first == after_second, "the second run must be a no-op"
    finally:
        vps.close()


def test_apcm5_every_stored_month_flag_implies_its_quarter(tmp_path):
    """APC-M5 — the whole mapping, not just the one month that was reported."""
    from src.getmoredone.vps_schema import VPSSchema

    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        conn = vps.db.conn
        months = ", ".join(f"m{m} = 1" for m in range(1, 13))
        quarters = ", ".join(f"q{q} = 0" for q in (1, 2, 3, 4))
        conn.execute(
            f"UPDATE annual_plan_elements SET {months}, {quarters} WHERE id = ?", (ape_id,)
        )
        conn.commit()

        VPSSchema._repair_orphan_month_flags(conn)
        conn.commit()

        row = conn.execute(
            "SELECT q1, q2, q3, q4 FROM annual_plan_elements WHERE id = ?", (ape_id,)
        ).fetchone()
        for quarter in MONTHS_OF_QUARTER:
            assert row[f"q{quarter}"] == 1, f"Q{quarter} has a month flag set"
    finally:
        vps.close()


# --------------------------------------------------------------------------
# The real widgets, not a stub
# --------------------------------------------------------------------------

def test_apcm32_the_real_month_combobox_holds_only_that_quarters_months(tmp_path):
    """APC-M3.2 / APC-M3.3 on a real CustomTkinter screen.

    Purpose: prove the combo the user clicks holds the values, not just that
             the method computed them.
    Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m3

    The stub tests above check the logic and the wiring; neither would catch a
    ``configure`` call that never reached a widget. Withdrawn, so it needs no
    mapped window and takes no keyboard focus.
    """
    import customtkinter as ctk

    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    vps = VPSManager(str(tmp_path / "real_widgets.db"))
    root = ctk.CTk()
    root.withdraw()
    try:
        screen = APEPeriodViewScreen(root, vps, SimpleNamespace())
        root.update_idletasks()

        opened_on = int(screen.quarter_var.get())
        assert list(screen.month_combo.cget("values")) == [
            str(m) for m in months_of_quarter(opened_on)
        ], "the screen opened with months outside its own quarter on offer"
        assert int(screen.month_var.get()) in months_of_quarter(opened_on)

        screen.quarter_var.set("3")
        screen.on_quarter_changed()
        root.update_idletasks()

        assert list(screen.month_combo.cget("values")) == ["7", "8", "9"]
        assert screen.month_var.get() in ("7", "8", "9"), (
            "switching to Q3 left a month outside Q3 selected"
        )

        screen.quarter_var.set("4")
        screen.on_quarter_changed()
        root.update_idletasks()
        assert list(screen.month_combo.cget("values")) == ["10", "11", "12"]
        assert "11" in screen.month_combo.cget("values"), (
            "M11 must be reachable from Q4, which is the quarter that contains it"
        )
    finally:
        root.destroy()
        vps.close()


# --------------------------------------------------------------------------
# Sweep fixes — findings from the /csdp passes over this batch
# --------------------------------------------------------------------------

def test_apcm24_a_raising_assignment_is_counted_not_escaped():
    """APC-M2.4 — a raise is reported, not allowed out of the loop.

    ``assign_ape_to_month`` does not only return ``False``: it raises
    ``ValueError`` when an APE's ``segment_name`` resolves to no segment. The
    first version of the reporting loop had no ``try``, so the raise skipped
    both ``refresh_lists`` and the status update and left the previous press's
    "Assigned N APE(s)" on screen — a success message for a save that half
    happened. Three checked, the middle one raising: the line must say two.
    """
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    said = []
    written = []

    def assign(ape_id, _quarter, _month):
        if ape_id == "ape-raises":
            raise ValueError("Segment 'Gone' not found.")
        written.append(ape_id)
        return True

    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4, 11),
        left_checks={
            "ape-one": SimpleNamespace(get=lambda: True),
            "ape-raises": SimpleNamespace(get=lambda: True),
            "ape-two": SimpleNamespace(get=lambda: True),
        },
        vps_manager=SimpleNamespace(assign_ape_to_month=assign),
        refresh_lists=lambda: said.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        # The raising APE wrote nothing, so the month holds only the two that
        # succeeded -- "refused", not "partly assigned".
        right_items=[{"id": "ape-one"}, {"id": "ape-two"}],
        _describe_month_assignment=APEPeriodViewScreen._describe_month_assignment,
    )
    _bind(stub, APEPeriodViewScreen, "_assign_one", "_ids_in_month")

    APEPeriodViewScreen.add_selected(stub)

    assert written == ["ape-one", "ape-two"], (
        f"the APEs that did not raise must still be written, got {written}"
    )
    assert "refresh" in said, "a raise must not skip the redraw"
    message = [s for s in said if isinstance(s, str) and s != "refresh"]
    assert message, f"a raise must not skip the status line, got {said}"
    assert "Assigned 2 APE(s) to M11." in message[-1], message
    assert "1 could not be assigned" in message[-1], message


def test_apcm44_month_lookup_guard_refuses_junk_and_normalises_a_float(tmp_path):
    """APC-M4.4 — the junk a caller can reach this with is refused, not raised on.

    ``month < 1 or month > 12`` raised ``TypeError`` on a string and *passed*
    a float, and ``m_col`` is interpolated as a column name, so ``11.0`` built
    ``m11.0`` and raised ``sqlite3.OperationalError`` from inside a Tk
    callback where nothing is on screen to show it.

    Named for what it asserts rather than "is type safe", which was this test's
    first name and overstated it: an unhashable month (``[]``, ``{}``) still
    raises ``TypeError`` from the membership test, and ``True`` passes it and
    becomes column ``m1``. Neither is reachable from a caller — both screens
    parse the month with ``int()`` — so both are in ``BACKLOG.md`` rather than
    guarded here, and the name no longer claims otherwise.
    """
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        vps.db.conn.execute(
            "UPDATE annual_plan_elements SET q4 = 1, m11 = 1 WHERE id = ?", (ape_id,)
        )
        vps.db.conn.commit()

        assert [r["id"] for r in vps.get_annual_plan_elements_for_month(2026, 11)] == [ape_id], (
            "the integer case must still work or this test proves nothing"
        )

        for junk in ("11", None, "m11", (11,)):
            assert vps.get_annual_plan_elements_for_month(2026, junk) == [], (
                f"{junk!r} must be refused, not raised on"
            )

        # A float is the case the membership test alone does not catch:
        # ``11.0 in {11: ...}`` is True, so it passes the guard. The column
        # name is built from ``int(month)``, so it reaches SQLite as ``m11``.
        assert [r["id"] for r in vps.get_annual_plan_elements_for_month(2026, 11.0)] == [ape_id]

        for out_of_range in (0, 13, -1):
            assert vps.get_annual_plan_elements_for_month(2026, out_of_range) == []
    finally:
        vps.close()


def test_apcm54_the_repair_reports_every_row_it_changed(tmp_path):
    """APC-M5.4 — the migration says which rows it changed, and stamps them.

    It runs against the user's real database on every open. The first version
    returned nothing, logged nothing and left ``updated_at`` alone, so the
    only trace of a repair was the changed data (P2).

    This is also what upgrades APC-M5.3 from inferring idempotency to proving
    it: a row snapshot comparison is satisfied for free by "set 1 to 1 twice",
    where an empty return is not.
    """
    from src.getmoredone.vps_schema import VPSSchema

    vps = make_vps(tmp_path)
    try:
        first_id = seed_ape(vps)
        second_id = seed_second_ape(vps)
        conn = vps.db.conn
        conn.execute(
            "UPDATE annual_plan_elements SET q4 = 0, m11 = 1, updated_at = ? "
            "WHERE id IN (?, ?)",
            ("2020-01-01T00:00:00", first_id, second_id),
        )
        conn.commit()

        repaired = VPSSchema._repair_orphan_month_flags(conn)
        conn.commit()

        assert sorted(repaired) == sorted([(first_id, 4), (second_id, 4)]), (
            f"both repaired rows must be named with their quarter, got {repaired}"
        )

        stamps = [
            row[0] for row in conn.execute(
                "SELECT updated_at FROM annual_plan_elements WHERE id IN (?, ?)",
                (first_id, second_id),
            ).fetchall()
        ]
        assert all(stamp != "2020-01-01T00:00:00" for stamp in stamps), (
            f"a repaired row really changed, so updated_at moves; got {stamps}"
        )

        assert VPSSchema._repair_orphan_month_flags(conn) == [], (
            "a second run has nothing to repair and must say so"
        )
    finally:
        vps.close()


def test_apcm62_quarter_save_reports_refused_assignments():
    """APC-M6.2 / APC-M6.3 — the quarter screen's wording, from the rows."""
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen

    describe = APEAssignmentScreen._describe_quarter_assignment

    assert describe(["a", "b", "c"], {"a", "b", "c"}, {"a", "b", "c"}, 4) == (
        "Assigned 3 APE(s) to Q4."
    )

    said = describe(["a", "b", "c"], {"a"}, {"a"}, 4)
    assert said.startswith("Assigned 1 APE(s) to Q4."), said
    assert "2 could not be assigned" in said, said

    said = describe(["a"], set(), set(), 1)
    assert said.startswith("Assigned 0 APE(s) to Q1."), (
        "a save that assigned nothing must not read as a success"
    )


def test_apcm62_quarter_save_with_nothing_checked_says_so():
    """APC-M6.2 — the same sentence APE Month gives, not silence."""
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen

    said = []
    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4),
        left_checks={"ape-1": SimpleNamespace(get=lambda: False)},
        vps_manager=SimpleNamespace(
            assign_ape_to_quarter=lambda *_a: pytest.fail("nothing was checked")
        ),
        refresh_lists=lambda: said.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
        _describe_quarter_assignment=APEAssignmentScreen._describe_quarter_assignment,
    )
    _bind(stub, APEAssignmentScreen, "_assign_one", "_ids_in_quarter")

    APEAssignmentScreen.add_selected(stub)

    assert said == ["Check one or more APEs on the left first."], said


def test_apcm62_a_raising_quarter_assignment_is_counted_not_escaped():
    """APC-M6.2 — the sibling screen, hardened on the same axis (P5).

    APE Quarter discarded ``assign_ape_to_quarter``'s boolean on both of its
    write paths and had no status surface at all, while the month screen was
    hardened on exactly this axis in the same change. The class is four paths
    across two screens, not two paths on one.
    """
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen

    said = []
    written = []

    def assign(ape_id, _quarter):
        if ape_id == "ape-raises":
            raise ValueError("Segment 'Gone' not found.")
        if ape_id == "ape-refused":
            return False
        written.append(ape_id)
        return True

    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4),
        left_checks={
            "ape-one": SimpleNamespace(get=lambda: True),
            "ape-raises": SimpleNamespace(get=lambda: True),
            "ape-refused": SimpleNamespace(get=lambda: True),
        },
        vps_manager=SimpleNamespace(assign_ape_to_quarter=assign),
        refresh_lists=lambda: said.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[{"id": "ape-one"}],
        _describe_quarter_assignment=APEAssignmentScreen._describe_quarter_assignment,
    )
    _bind(stub, APEAssignmentScreen, "_assign_one", "_ids_in_quarter")

    APEAssignmentScreen.add_selected(stub)

    assert written == ["ape-one"], written
    assert "refresh" in said, "a raise must not skip the redraw"
    message = [s for s in said if isinstance(s, str) and s != "refresh"]
    assert message, f"a raise must not skip the status line, got {said}"
    assert "Assigned 1 APE(s) to Q4." in message[-1], message
    assert "2 could not be assigned" in message[-1], message


def test_apcm62_quarter_drag_path_reaches_the_same_reporting():
    """APC-M6.2 — the drop target reports too, as the month screen's does.

    The stub records the call as well as refusing it, for the reason the month
    screen's drag test gives: ``_assign_one``'s broad ``except Exception``
    would swallow a stub that raised, so a message-only assertion would pass
    on a call that never legitimately happened.

    UPD-M2 moved the drop *test* — the pointer, the descendant walk, the
    release binding — into ``screens/row_drag.py``, and what a dropped row
    means stayed on the screen as ``_assign_dragged_row``. This test is
    rewritten against that method, case (b): the behaviour did not change, the
    method the behaviour lives in did. The six stub members that only ever
    existed to carry the drag machinery are gone with it, which is the point —
    ``test_updm22_drop_inside_the_target_assigns_once`` now owns the claim
    that a release inside the panel reaches this method exactly once, and this
    test owns the claim that reaching it reports.
    """
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen

    said = []
    calls = []
    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4),
        vps_manager=SimpleNamespace(
            assign_ape_to_quarter=lambda *a: calls.append(a) or False
        ),
        refresh_lists=lambda: said.append("refresh"),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
        _describe_quarter_assignment=APEAssignmentScreen._describe_quarter_assignment,
    )
    _bind(stub, APEAssignmentScreen, "_assign_one", "_ids_in_quarter")

    APEAssignmentScreen._assign_dragged_row(stub, {"id": "ape-bad"})

    assert calls == [("ape-bad", 4)], (
        f"the drop must reach the manager with the parsed quarter, got {calls}"
    )
    assert any("could not be assigned" in s for s in said if isinstance(s, str)), said
    # A refused assignment still redraws. Added at UPD-M2, because the
    # mutation gate found that neither this test nor any other asserted it on
    # this screen: dropping `refresh_lists()` from the method left every
    # assertion above green. The same fault was found and fixed on the weekly
    # screen, where `tests/test_weekly_tactic_schema.py` pins it in so many
    # words ("used to refresh only when something was created"); this is its
    # untested sibling (P5), and the gap predates UPD-M2.
    assert "refresh" in said, "a refused drop must not skip the redraw"


def _break_segment_link(vps, ape_id):
    """Make the APE's segment unresolvable, the way a rename once did.

    ``_segment_id_for_ape`` returns the stored id when there is one and only
    falls back to the name, so both have to go: no id, and a name that matches
    no segment. That is the state ``tests/test_rename_safe_links.py`` exists
    for, and it is the one condition under which ``assign_ape_to_quarter`` and
    ``assign_ape_to_month`` raise *after* committing a flag.
    """
    vps.db.conn.execute(
        "UPDATE annual_plan_elements "
        "SET segment_description_id = NULL, segment_name = 'Gone' WHERE id = ?",
        (ape_id,),
    )
    vps.db.conn.commit()


def test_apcm25_a_half_written_assignment_is_reported_as_partial(tmp_path):
    """APC-M2.5 — the call raised, the row is in the month, and the line says so.

    This is the test the APC-M2.4 pair could not be. Their stubs raise
    *instead of* writing, so a status line counted off ``_assign_one``'s
    booleans passes them both — and that line said "Assigned 0 APE(s) to M11"
    beside a panel that was showing the row.

    So the fixture here is the real manager on a real database, in the one
    state that makes it half-write: the APE is already in Q4, its segment is
    unresolvable, and ``assign_ape_to_month`` commits the month flag before it
    reaches the segment lookup that raises. Both halves are asserted — the row
    really is in M11, and the call really did fail — because a fixture that
    only fails is the one that cannot catch this.
    """
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    vps = make_vps(tmp_path)
    ape_id = seed_ape(vps, year=2026)
    assert vps.assign_ape_to_quarter(ape_id, 4) is True
    _break_segment_link(vps, ape_id)

    with pytest.raises(ValueError):
        vps.assign_ape_to_month(ape_id, 4, 11)
    assert vps.db.conn.execute(
        "SELECT m11 FROM annual_plan_elements WHERE id = ?", (ape_id,)
    ).fetchone()[0] == 1, (
        "the fixture is not hostile in the way that reaches the line unless "
        "the failed call left the month flag written"
    )
    vps.set_annual_plan_element_month(ape_id, 11, False)

    said = []
    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4, 11),
        left_checks={ape_id: SimpleNamespace(get=lambda: True)},
        vps_manager=vps,
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
        _describe_month_assignment=APEPeriodViewScreen._describe_month_assignment,
    )
    # The same read the real refresh_lists does, so the sentence and the panel
    # cannot disagree: one query feeds both.
    stub.refresh_lists = lambda: setattr(
        stub, "right_items", vps.get_annual_plan_elements_for_month(2026, 11)
    )
    _bind(stub, APEPeriodViewScreen, "_assign_one", "_ids_in_month")

    APEPeriodViewScreen.add_selected(stub)

    assert said, "the press must leave a status line"
    assert ape_id in {row["id"] for row in stub.right_items}, (
        "the half-written row must be in the panel for this test to mean anything"
    )
    assert said[-1].startswith("Assigned 0 APE(s) to M11."), said[-1]
    assert "1 partly assigned — in M11 with no month tactic behind it" in said[-1], said[-1]
    assert "could not be assigned" not in said[-1], said[-1]


def test_apcm26_a_failed_remove_is_reported():
    """APC-M2.6 — Remove reports against the row, in all three outcomes.

    The remove path was left silent when the two assign paths were fixed: it
    popped a confirmation, called the manager, discarded the answer, and
    redrew. A remove that failed looked exactly like one that worked, with the
    row still in the panel to contradict it.

    Three outcomes, each from a real shape: the call succeeds and the row
    leaves; the call raises before clearing the flag (a locked database) and
    the row stays; the call raises after clearing it (the month tactic delete
    fails) so the row has left but the call still failed.
    """
    from src.getmoredone.screens import ape_period_view
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen

    said = []
    state = {"in_month": [{"id": "ape-1"}], "mode": "ok"}

    def unassign(ape_id, _quarter, _month):
        if state["mode"] == "ok":
            state["in_month"] = []
            return True
        if state["mode"] == "raises_before_write":
            raise sqlite3.OperationalError("database is locked")
        state["in_month"] = []
        raise ValueError("Segment 'Gone' not found.")

    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4, 11),
        vps_manager=SimpleNamespace(unassign_ape_from_month=unassign),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
    )
    stub.refresh_lists = lambda: setattr(stub, "right_items", list(state["in_month"]))
    _bind(stub, APEPeriodViewScreen, "_remove_one", "_ids_in_month")

    original = ape_period_view.messagebox
    ape_period_view.messagebox = SimpleNamespace(
        askyesno=lambda *_a, **_k: True,
        showerror=lambda *_a, **_k: None,
    )
    try:
        APEPeriodViewScreen.delete_month_item(stub, {"id": "ape-1", "key_field": "Blog"})
        assert said[-1] == "Removed Blog from M11.", said[-1]

        state.update(in_month=[{"id": "ape-1"}], mode="raises_before_write")
        APEPeriodViewScreen.delete_month_item(stub, {"id": "ape-1", "key_field": "Blog"})
        assert said[-1] == "Blog is still in M11 — see the log.", said[-1]

        state.update(in_month=[{"id": "ape-1"}], mode="raises_after_write")
        APEPeriodViewScreen.delete_month_item(stub, {"id": "ape-1", "key_field": "Blog"})
        assert said[-1] == (
            "Blog is out of M11, but the remove reported a problem — see the log."
        ), said[-1]
    finally:
        ape_period_view.messagebox = original


def test_apcm63_a_half_written_quarter_assignment_is_reported_as_partial(tmp_path):
    """APC-M6.3 — the same half-write on the quarter screen, same evidence.

    ``assign_ape_to_quarter`` commits the quarter flag and only then raises on
    a segment it cannot resolve, so this screen had the fault in its plainest
    form: one write, one raise, and the row in the panel either way.
    """
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen

    vps = make_vps(tmp_path)
    ape_id = seed_ape(vps, year=2026)
    _break_segment_link(vps, ape_id)

    with pytest.raises(ValueError):
        vps.assign_ape_to_quarter(ape_id, 4)
    assert vps.db.conn.execute(
        "SELECT q4 FROM annual_plan_elements WHERE id = ?", (ape_id,)
    ).fetchone()[0] == 1, (
        "the fixture must leave the quarter flag written, or it cannot reach "
        "the line under test"
    )
    vps.set_annual_plan_element_quarter(ape_id, 4, False)

    said = []
    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4),
        left_checks={ape_id: SimpleNamespace(get=lambda: True)},
        vps_manager=vps,
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
        _describe_quarter_assignment=APEAssignmentScreen._describe_quarter_assignment,
    )
    stub.refresh_lists = lambda: setattr(
        stub, "right_items", vps.get_annual_plan_elements_for_quarter(2026, 4)
    )
    _bind(stub, APEAssignmentScreen, "_assign_one", "_ids_in_quarter")

    APEAssignmentScreen.add_selected(stub)

    assert said, "the press must leave a status line"
    assert ape_id in {row["id"] for row in stub.right_items}, (
        "the half-written row must be in the panel for this test to mean anything"
    )
    assert said[-1].startswith("Assigned 0 APE(s) to Q4."), said[-1]
    assert "1 partly assigned — in Q4 with no quarter initiative behind it" in said[-1], said[-1]
    assert "could not be assigned" not in said[-1], said[-1]


def test_apcm64_a_failed_quarter_remove_is_reported():
    """APC-M6.4 — the quarter screen's Remove reports too, in all three outcomes.

    The sibling of APC-M2.6. Fixing one screen's remove and leaving the
    other's is the same P5 shape that left this whole screen silent in the
    first round.
    """
    from src.getmoredone.screens import ape_assignment
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen

    said = []
    state = {"in_quarter": [{"id": "ape-1"}], "mode": "ok"}

    def unassign(ape_id, _quarter):
        if state["mode"] == "ok":
            state["in_quarter"] = []
            return True
        if state["mode"] == "raises_before_write":
            raise sqlite3.OperationalError("database is locked")
        state["in_quarter"] = []
        raise ValueError("Segment 'Gone' not found.")

    stub = SimpleNamespace(
        _parse_period=lambda: (2026, 4),
        vps_manager=SimpleNamespace(unassign_ape_from_quarter=unassign),
        status_label=SimpleNamespace(configure=lambda **kw: said.append(kw["text"])),
        right_items=[],
    )
    stub.refresh_lists = lambda: setattr(stub, "right_items", list(state["in_quarter"]))
    _bind(stub, APEAssignmentScreen, "_remove_one", "_ids_in_quarter")

    original = ape_assignment.messagebox
    ape_assignment.messagebox = SimpleNamespace(
        askyesno=lambda *_a, **_k: True,
        showerror=lambda *_a, **_k: None,
    )
    try:
        APEAssignmentScreen.delete_quarter_item(stub, {"id": "ape-1", "key_field": "Blog"})
        assert said[-1] == "Removed Blog from Q4.", said[-1]

        state.update(in_quarter=[{"id": "ape-1"}], mode="raises_before_write")
        APEAssignmentScreen.delete_quarter_item(stub, {"id": "ape-1", "key_field": "Blog"})
        assert said[-1] == "Blog is still in Q4 — see the log.", said[-1]

        state.update(in_quarter=[{"id": "ape-1"}], mode="raises_after_write")
        APEAssignmentScreen.delete_quarter_item(stub, {"id": "ape-1", "key_field": "Blog"})
        assert said[-1] == (
            "Blog is out of Q4, but the remove reported a problem — see the log."
        ), said[-1]
    finally:
        ape_assignment.messagebox = original


def test_apcm55_the_repair_log_reaches_a_handler(tmp_path):
    """APC-M5.5 — the repair's log line lands, and names the rows it changed.

    The return value is the only other record, and
    ``_extend_annual_plan_elements`` discards it — so in the running app the
    log line is the *entire* trace of a migration that rewrote the user's
    rows. It was added with no test: deleting it left every other APC test
    green, which is exactly the shape P2 is about.

    §5.10 claimed a behavioural check was not practical here because the line
    goes to the user's log. That was wrong, and
    ``test_wt_m7a5_dedupe_log_reaches_a_handler`` was already the counter-
    example: ``caplog`` cannot be used because this logger sets
    ``propagate = False``, but a handler attached to the logger itself can,
    which is what the app's own file handler is.
    """
    from src.getmoredone.vps_schema import VPSSchema
    from src.getmoredone.weekly_tactic_logging import get_weekly_tactic_logger

    live = get_weekly_tactic_logger()
    assert live.isEnabledFor(logging.INFO), (
        "the repair line is INFO; a logger below that level discards it"
    )

    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        conn = vps.db.conn
        conn.execute(
            "UPDATE annual_plan_elements SET q4 = 0, m11 = 1 WHERE id = ?",
            (ape_id,),
        )
        conn.commit()

        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        probe = _Capture(level=logging.INFO)
        live.addHandler(probe)
        try:
            VPSSchema._repair_orphan_month_flags(conn)
            conn.commit()
        finally:
            live.removeHandler(probe)

        text = "\n".join(records)
        assert "APC-M5" in text, f"the repair summary never reached the log: {text!r}"
        assert ape_id in text, (
            f"the repaired row's id must appear in the log, got {text!r}"
        )

        # And a run with nothing to repair says nothing, so the line stays a
        # signal rather than one more every-launch message.
        quiet = []

        class _Quiet(logging.Handler):
            def emit(self, record):
                quiet.append(record.getMessage())

        probe2 = _Quiet(level=logging.INFO)
        live.addHandler(probe2)
        try:
            VPSSchema._repair_orphan_month_flags(conn)
        finally:
            live.removeHandler(probe2)
        assert quiet == [], f"a no-op repair must log nothing, got {quiet}"
    finally:
        vps.close()
