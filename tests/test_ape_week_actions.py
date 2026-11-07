"""Tests for the APE Week Assignment rename and the APE Week Actions tab.

Spec: docs/spec_2026-11-07_ape_week_actions.md

Covers AWA-M1 (the rename) through AWA-M6 (the seam cut into the Today
screen). Every test name carries the criterion ID it verifies.

The screens here are built on a **withdrawn** root, so none of them adds to
the mapped-window count that tests/test_ci_contract.py pins at 22
(AWA-M3.3).
"""

import ast
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# Self-contained path bootstrap, for the same reason test_ape_period_consistency
# carries one: tests/test_ci_contract.py imports every test file with the repo
# root stripped from sys.path, and this file sorts early, so it cannot rely on
# another file having put the root back.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

import customtkinter as ctk  # noqa: E402

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem
from src.getmoredone.screens.today import TodayScreen
from src.getmoredone.screens.week_collision_notice import (  # noqa: E402
    describe_week_collision,
)
from src.getmoredone.weekly_tactic_maintenance import _child_count  # noqa: E402
from tests.weekly_tactic_fixtures import (
    make_daily_item,
    make_vps,
    make_week_item,
    seed_ape,
    seed_second_ape,
)

SRC = Path(__file__).resolve().parents[1] / "src" / "getmoredone"


# --------------------------------------------------------------------- helpers

def _root():
    """A withdrawn Tk root, or a skip when there is no display."""
    try:
        root = ctk.CTk()
    except Exception as exc:  # Headless without a display.
        pytest.skip(f"Tk display unavailable: {exc}")
    root.geometry("1200x800+0+0")
    root.withdraw()
    return root


def _app_stub(db=None, vps_manager=None):
    """An app double with the two colour maps every list screen reads."""
    app = MagicMock()
    app.vps_manager.get_segment_colors_by_id.return_value = {}
    app.vps_manager.get_segment_color_map.return_value = {}
    if vps_manager is not None:
        app.vps_manager = vps_manager
        app.vps_manager.get_segment_colors_by_id = MagicMock(return_value={})
        app.vps_manager.get_segment_color_map = MagicMock(return_value={})
    if db is not None:
        app.db_manager = db
    return app


def _make_today(tmp_path, titles=()):
    root = _root()
    db = DatabaseManager(str(tmp_path / "today.db"))
    for title in titles:
        db.create_action_item(
            ActionItem(who="Self", title=title, start_date=date.today().isoformat())
        )
    screen = TodayScreen(root, db, _app_stub(db))
    screen.update_idletasks()
    return root, db, screen


def _toolbar_layout(screen):
    """[(grid column, class name)] for the toolbar's children, left to right."""
    rows = []
    for child in screen.toolbar_frame.winfo_children():
        info = child.grid_info()
        if not info:
            continue
        rows.append((int(info["column"]), type(child).__name__, child))
    rows.sort(key=lambda row: row[0])
    return rows


def _scroll_texts(screen):
    """Every label text inside the list area, flattened."""
    found = []

    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                found.append(child.cget("text"))
            walk(child)

    walk(screen.scroll_frame)
    return found


# ------------------------------------------------- AWA-M6: the seam into Today

def test_awam61_today_exposes_the_seam():
    """AWA-M6.1 — _build_toolbar, EMPTY_TEXT and COLUMN_PREFIX are overridable.

    All three must be defined *on TodayScreen itself*, not inherited from
    CTkFrame and not local variables inside __init__, or a subclass has
    nothing to override.
    """
    assert "_build_toolbar" in vars(TodayScreen)
    assert "EMPTY_TEXT" in vars(TodayScreen)
    assert "COLUMN_PREFIX" in vars(TodayScreen)
    assert callable(vars(TodayScreen)["_build_toolbar"])


def test_awam62_today_column_prefix_and_empty_text_are_unchanged(tmp_path):
    """AWA-M6.2 — the seam carries Today's own values, and Today uses them.

    The class attributes are only half the claim: the resizer must actually
    be built from COLUMN_PREFIX and the empty list must actually render
    EMPTY_TEXT, or the seam is decoration and the subclass's overrides do
    nothing.
    """
    assert TodayScreen.COLUMN_PREFIX == "today"
    assert TodayScreen.EMPTY_TEXT == "No items for today"

    root, db, screen = _make_today(tmp_path)  # no items -> empty state
    try:
        assert screen.resizer.prefix == TodayScreen.COLUMN_PREFIX
        assert TodayScreen.EMPTY_TEXT in _scroll_texts(screen)
    finally:
        root.destroy()
        db.db.close()


def test_awam62_today_toolbar_unchanged(tmp_path):
    """AWA-M6.2 — the extracted toolbar builds the same controls in order.

    Asserted as an exact ordered list, not a floor: a control dropped,
    added or moved fails here.
    """
    root, db, screen = _make_today(tmp_path)
    try:
        layout = _toolbar_layout(screen)
        assert [(col, cls) for col, cls, _ in layout] == [
            (0, "CTkLabel"),    # "Today's Items"
            (1, "CTkEntry"),    # search
            (2, "CTkButton"),   # Search
            (3, "CTkButton"),   # Expand / Collapse
            (4, "CTkButton"),   # Top 3
            (6, "CTkButton"),   # + New Item
            (7, "CTkButton"),   # Refresh
        ]
        by_col = {col: widget for col, _, widget in layout}
        assert by_col[0].cget("text") == "Today's Items"
        assert by_col[1] is screen.search_entry
        assert by_col[2].cget("text") == "Search"
        assert by_col[3] is screen.expand_collapse_btn
        assert by_col[4] is screen.top3_btn
        assert by_col[6].cget("text") == "+ New Item"
        assert by_col[7].cget("text") == "Refresh"
    finally:
        root.destroy()
        db.db.close()


# ----------------------------------- AWA-M2: one predicate for "linked to this"

def _tactic_and_ape(vps, start="2026-11-09", title="W1"):
    """A Weekly Tactic on a real APE lineage — WT-M1.C.4 requires the APE."""
    ape_id = seed_ape(vps)
    return make_week_item(vps, ape_id, start=start, due=start, title=title), ape_id


def test_awam21_both_link_shapes_are_returned(tmp_path):
    """AWA-M2.1 — the helper matches weekly_tactic_id OR parent_id.

    Both shapes are live in the field: the cascade writes
    weekly_tactic_id, the Add Action Item button writes parent_id. A helper
    reading one column shows an empty panel on whichever database uses the
    other — counted on both real databases in spec §1.3.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps)
        by_tactic_col = make_daily_item(
            vps, title="linked by weekly_tactic_id",
            weekly_tactic_id=tactic.id, refile=False)
        by_parent_col = make_daily_item(
            vps, title="linked by parent_id",
            parent_id=tactic.id, refile=False)

        found = {item.id for item in
                 vps.get_action_items_for_weekly_tactic(tactic.id)}
        assert found == {by_tactic_col.id, by_parent_col.id}
    finally:
        vps.close()


def test_awam22_week_rows_are_never_children(tmp_path):
    """AWA-M2.2 — a tactic is never returned as a child of a tactic.

    A second week row pointed at the first would otherwise render a tactic
    inside its own item list, and two tactics in one week must not nest.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps)
        # A second APE, because (annual_plan_element_id, start_date) is unique:
        # one APE gets one tactic per week.
        nested_week = make_week_item(vps, seed_second_ape(vps),
                                     start="2026-11-09", due="2026-11-09",
                                     title="W2")
        vps.db.conn.execute(
            "UPDATE action_items SET parent_id = ? WHERE id = ?",
            (tactic.id, nested_week.id),
        )
        vps.db.conn.commit()
        ordinary = make_daily_item(vps, title="a real child",
                                   weekly_tactic_id=tactic.id, refile=False)

        found = {item.id for item in
                 vps.get_action_items_for_weekly_tactic(tactic.id)}
        assert found == {ordinary.id}
        assert nested_week.id not in found
    finally:
        vps.close()


def test_awam23_one_home_for_the_link_predicate():
    """AWA-M2.3 - the union predicate is written in exactly one place.

    Scanned over **all** of ``src/getmoredone``, not just ``screens/`` and
    ``vps_manager.py``. The narrower scan this replaces asserted a claim that
    was already false: ``weekly_tactic_maintenance._child_count`` held a
    second copy, and the two had drifted - that one lacked the
    ``item_type != 'week'`` exclusion, so the dedupe's "most children wins"
    chose a survivor on a different definition of "child" than the panel
    renders. Nothing went red, because the file was out of scope.

    Matched on the predicate's *shape* rather than on the two column names
    appearing together: ``db_manager``'s INSERT column list and UPDATE SET
    list both name both columns, and neither is an expression of this
    predicate. A comparison of one column reached from an ``OR`` is.

    **What this does and does not catch.** Case-insensitive — both the
    membership gate and the pattern, since a flag on one half of a two-part
    match buys nothing — either branch order, and ``= ?``, ``= :name`` or
    ``IN (?)``: the forms a second copy would plausibly be written in.

    It cannot see a copy split across two ``ast.Constant`` nodes
    (``"… = ?" + " OR parent_id = ?"``, or an f-string with an interpolation
    between the halves); the constant below survives the scan only because
    adjacent string literals are folded at compile time. Nor can it see a copy
    expressed as a JOIN rather than an ``OR`` — ``weekly_tactic_maintenance``'s
    invariant repair has one (``JOIN action_items week ON
    week.id = child.weekly_tactic_id``). That reader disagrees with this
    predicate on *more* than the rows the ``parent_id`` arm adds: it constrains
    only the parent side (``week.item_type = 'week'``) while this predicate
    also excludes ``child.item_type != 'week'``, so it acts on week rows
    AWA-M2.2 deliberately keeps out. AWA-A1 is the entry; AWA-S9 records the
    week-under-week case it makes reachable.

    Exact count per file, not a floor. The exclusion is by value-equality
    against module, function and class docstrings only, so a non-docstring
    prose string under ``src/`` naming ``weekly_tactic_id``, then "or", then
    ``parent_id = ?`` would match and turn this red spuriously. None exists;
    the cost of that is a one-line edit here, and the cost of a looser gate is
    the finding this test was written for.
    """
    shape = re.compile(
        r"\bOR\b[\s\S]*?\b(?:parent_id|weekly_tactic_id)\s*"
        r"(?:=\s*[?:]|IN\s*\()",
        re.IGNORECASE)

    def docstrings(tree):
        out = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
                text = ast.get_docstring(node, clean=False)
                if text is not None:
                    out.add(text)
        return out

    counts = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text())
        docs = docstrings(tree)
        hits = 0
        for sub in ast.walk(tree):
            if not (isinstance(sub, ast.Constant)
                    and isinstance(sub.value, str)):
                continue
            if sub.value in docs:
                continue
            # Lower-cased for the gate as well as the search: the regex
            # carries re.IGNORECASE, but while this membership test was
            # case-sensitive the flag only widened the half already pinned.
            value = sub.value.lower()
            if "weekly_tactic_id" in value and shape.search(value):
                hits += 1
        if hits:
            counts[str(path.relative_to(SRC))] = hits

    assert counts == {"weekly_tactic.py": 1}

    # And it is the constant both callers use, not a third thing.
    from src.getmoredone import vps_manager, weekly_tactic_maintenance
    from src.getmoredone.weekly_tactic import LINK_PREDICATE_SQL
    assert vps_manager.LINK_PREDICATE_SQL is LINK_PREDICATE_SQL
    assert weekly_tactic_maintenance.LINK_PREDICATE_SQL is LINK_PREDICATE_SQL


def test_awam23_an_item_is_listed_under_one_tactic_only(tmp_path):
    """AWA-M2.3 - both columns set means one tactic, not both.

    Reachable through supported UI: add an Action Item from APE Week
    Assignment, whose button writes ``parent_id`` (AWA-A1), then pick a
    different Weekly Tactic in the editor, which sets ``weekly_tactic_id``
    and by design leaves ``parent_id`` alone (``item_editor.py``). A plain
    ``weekly_tactic_id = ? OR parent_id = ?`` listed that one item under
    *both* tactics - two panels each claiming it, and a dedupe counting it
    twice. ``weekly_tactic_id`` wins when set: the tactic last chosen.
    """
    vps = make_vps(tmp_path)
    try:
        first, ape_id = _tactic_and_ape(vps, start="2026-11-09", title="W1")
        second = make_week_item(vps, ape_id, start="2026-11-16",
                                due="2026-11-16", title="W2")
        child = make_daily_item(
            vps, title="Moved by hand", start="2026-11-16", due="2026-11-16",
            weekly_tactic_id=second.id, parent_id=first.id, refile=False)

        row = vps.db.conn.execute(
            "SELECT weekly_tactic_id, parent_id FROM action_items WHERE id = ?",
            (child.id,)).fetchone()
        assert row["weekly_tactic_id"] == second.id
        assert row["parent_id"] == first.id

        under_first = vps.get_action_items_for_weekly_tactic(first.id)
        under_second = vps.get_action_items_for_weekly_tactic(second.id)
        assert [item.id for item in under_second] == [child.id]
        assert [item.id for item in under_first] == []
    finally:
        vps.close()


def test_awam24_ordinary_subtasks_are_not_tactic_children(tmp_path):
    """AWA-M2.4 — parent_id on a non-week parent is ordinary nesting.

    parent_id means two things depending on who wrote it. Asked for the
    children of an id that is not a Weekly Tactic, the helper returns
    nothing rather than a list of somebody's subtasks.
    """
    vps = make_vps(tmp_path)
    try:
        ordinary_parent = make_daily_item(vps, title="an ordinary item",
                                          refile=False)
        make_daily_item(vps, title="its subtask",
                        parent_id=ordinary_parent.id, refile=False)

        assert vps.get_action_items_for_weekly_tactic(ordinary_parent.id) == []
    finally:
        vps.close()


def test_awam25_orphaned_child_is_not_returned(tmp_path):
    """AWA-M2.5 — P8 dirty state: a link that outlived the row it points at.

    Both link columns are declared ``REFERENCES action_items(id) ON DELETE
    SET NULL``, so with ``PRAGMA foreign_keys = ON`` an ordinary delete
    clears them and no dangling link survives. The first version of this
    test deleted the tactic that way, and was vacuous: it asserted an
    outcome the schema already guaranteed, and stayed green with the
    helper's guard removed. The mutation gate caught it.

    The state that does survive is one written with foreign keys off — an
    older build, a direct sqlite3 edit, a restored backup. This repo already
    carries rows "no supported path can create" from exactly that. Here the
    guard is the only thing between the panel and a row whose tactic is
    gone, and removing it makes this red.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps)
        make_daily_item(vps, title="orphan", weekly_tactic_id=tactic.id,
                        refile=False)
        vps.db.conn.execute("PRAGMA foreign_keys = OFF")
        try:
            vps.db.conn.execute("DELETE FROM action_items WHERE id = ?",
                                (tactic.id,))
            vps.db.conn.commit()
        finally:
            vps.db.conn.execute("PRAGMA foreign_keys = ON")

        # The dirty state really is dirty: the link outlived its row.
        dangling = vps.db.conn.execute(
            "SELECT COUNT(*) AS n FROM action_items WHERE weekly_tactic_id = ?",
            (tactic.id,)).fetchone()["n"]
        assert dangling == 1

        assert vps.get_action_items_for_weekly_tactic(tactic.id) == []
    finally:
        vps.close()


# --------------------------------- AWA-M5: the right panel behaves like Today

def _panel(tmp_path, vps, tactic_id=None):
    """A WeekTacticActionsPanel on a withdrawn root (AWA-M3.3)."""
    from src.getmoredone.screens.week_actions import WeekTacticActionsPanel
    root = _root()
    panel = WeekTacticActionsPanel(root, vps.db_manager, _app_stub(vps.db_manager, vps))
    if tactic_id is not None:
        panel.set_tactic(_tactic_row(vps, tactic_id))
    panel.update_idletasks()
    return root, panel


def _tactic_row(vps, tactic_id):
    row = vps.db.conn.execute(
        "SELECT * FROM action_items WHERE id = ?", (tactic_id,)).fetchone()
    return dict(row)


def _complete_on(vps, item, when):
    """Complete an item with an explicit completion timestamp."""
    item.status = "completed"
    item.completed_at = f"{when}T09:00:00"
    assert vps.db_manager.update_action_item(item, refile=False)
    return item


def test_awam54_add_action_item_links_by_weekly_tactic_id(tmp_path):
    """AWA-M5.4 — the new row carries weekly_tactic_id and the week's dates.

    Writing parent_id instead is what split the link in two (spec §1.3);
    this panel writes the column weekly_tactic_migrations.py exists to
    establish. The editor then opens on the row that was just created, so
    the user lands where D5 says they do.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps, start="2026-11-09")
        root, panel = _panel(tmp_path, vps, tactic.id)
        try:
            panel._prompt_for_title = lambda: "Draft the outline"
            opened = []
            panel.edit_item = lambda item_id, **kw: opened.append(item_id)

            panel.add_action_item()

            rows = vps.db.conn.execute(
                "SELECT id, weekly_tactic_id, parent_id, start_date, due_date, "
                "item_type FROM action_items WHERE title = ?",
                ("Draft the outline",)).fetchall()
            assert len(rows) == 1
            row = rows[0]
            assert row["weekly_tactic_id"] == tactic.id
            assert row["start_date"] == "2026-11-09"
            assert row["due_date"] == "2026-11-09"
            assert row["item_type"] == "daily"
            assert opened == [row["id"]]
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam54b_empty_title_creates_nothing(tmp_path):
    """AWA-M5.4 — cancelling the prompt writes no row and opens no editor."""
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps)
        root, panel = _panel(tmp_path, vps, tactic.id)
        try:
            before = vps.db.conn.execute(
                "SELECT COUNT(*) AS n FROM action_items").fetchone()["n"]
            panel._prompt_for_title = lambda: "   "
            opened = []
            panel.edit_item = lambda item_id, **kw: opened.append(item_id)

            panel.add_action_item()

            after = vps.db.conn.execute(
                "SELECT COUNT(*) AS n FROM action_items").fetchone()["n"]
            assert after == before
            assert opened == []
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam58_completed_children_are_not_date_filtered(tmp_path):
    """AWA-M5.8 — D6: completed children show whatever the completion date.

    Adversarial (P7): the 90-day-old child is the one a date filter would
    silently drop, and the other tactic's child completed *today* is the one
    a leftover date filter would wrongly let through. A panel filtered by
    tactic has no business reading the clock at all.
    """
    vps = make_vps(tmp_path)
    try:
        ours, _ = _tactic_and_ape(vps, start="2026-11-09", title="ours")
        theirs = make_week_item(vps, seed_second_ape(vps), start="2026-11-09",
                                due="2026-11-09", title="theirs")

        old = make_daily_item(vps, title="done 90 days ago",
                              weekly_tactic_id=ours.id, refile=False)
        _complete_on(vps, old, (date.today() - timedelta(days=90)).isoformat())
        still_open = make_daily_item(vps, title="open on ours",
                                     weekly_tactic_id=ours.id, refile=False)
        other = make_daily_item(vps, title="done today on theirs",
                                weekly_tactic_id=theirs.id, refile=False)
        _complete_on(vps, other, date.today().isoformat())

        root, panel = _panel(tmp_path, vps, ours.id)
        try:
            found = {item.id for item in panel.get_todays_items()}
            assert found == {old.id, still_open.id}
            assert other.id not in found
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam51_right_panel_subclasses_today(tmp_path):
    """AWA-M5.1 — the panel is a TodayScreen, not a second copy of one."""
    from src.getmoredone.screens.week_actions import WeekTacticActionsPanel
    assert issubclass(WeekTacticActionsPanel, TodayScreen)


def test_awam52_right_panel_queries_by_tactic_not_date(tmp_path):
    """AWA-M5.2 — the item query is the AWA-M2 helper, with no date filter.

    Driven by behaviour, not by reading the source: the helper is recorded,
    and the panel's answer is whatever the helper returned. A panel that
    still consulted the clock could not pass both halves.
    """
    from src.getmoredone.screens.week_actions import WeekTacticActionsPanel

    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps)
        child = make_daily_item(vps, title="child",
                                weekly_tactic_id=tactic.id, refile=False)
        root, panel = _panel(tmp_path, vps, tactic.id)
        try:
            calls = []
            real = vps.get_action_items_for_weekly_tactic

            def recording(tactic_id):
                calls.append(tactic_id)
                return real(tactic_id)

            panel.app.vps_manager.get_action_items_for_weekly_tactic = recording
            items = panel.get_todays_items()

            assert calls == [tactic.id]
            assert [item.id for item in items] == [child.id]
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam53_row_behaviours_are_inherited_not_copied():
    """AWA-M5.3 — every row behaviour comes from Today, unredefined.

    Exact list, not a floor. Redefining any of these on the subclass is how
    "works like the Today tab" quietly stops being true.
    """
    from src.getmoredone.screens.week_actions import WeekTacticActionsPanel

    inherited = [
        "edit_item",
        "complete_item",
        "start_timer",
        "push_item",
        "edit_start_date_inline",
        "edit_due_date_inline",
        "edit_priority_inline",
        "create_item_row",
        "load_items",
    ]
    redefined = [name for name in inherited
                 if name in vars(WeekTacticActionsPanel)]
    assert redefined == []
    for name in inherited:
        assert getattr(WeekTacticActionsPanel, name) is \
            getattr(TodayScreen, name)

    # The four seams, and only those four, override anything of Today's.
    # A set *intersection* only proved those four were present; it could not
    # see a fifth override appear, which is the drift this criterion is about.
    # The panel's own new names (set_tactic, add_action_item, ...) shadow
    # nothing on Today, so they are not overrides and are not listed.
    overridden = sorted(name for name in vars(WeekTacticActionsPanel)
                        if not name.startswith("__")
                        and hasattr(TodayScreen, name))
    assert overridden == [
        "COLUMN_PREFIX", "EMPTY_TEXT", "_build_toolbar", "get_todays_items"
    ]


def test_awam55_column_prefix_is_its_own(tmp_path):
    """AWA-M5.5 — its Title width is stored apart from Today's.

    Same prefix would mean dragging either panel's divider moved the other,
    and the setting that holds it must exist or the width would not persist
    at all (AppSettings writes declared fields only).
    """
    from dataclasses import fields

    from src.getmoredone.app_settings import AppSettings
    from src.getmoredone.screens.week_actions import WeekTacticActionsPanel

    assert WeekTacticActionsPanel.COLUMN_PREFIX != TodayScreen.COLUMN_PREFIX
    assert WeekTacticActionsPanel.COLUMN_PREFIX == "week_actions"
    declared = {f.name for f in fields(AppSettings)}
    assert "week_actions_col_widths" in declared

    vps = make_vps(tmp_path)
    try:
        root, panel = _panel(tmp_path, vps)
        try:
            assert panel.resizer.prefix == "week_actions"
            assert panel.resizer._setting_attr() == "week_actions_col_widths"
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam56_empty_state_names_the_tactic(tmp_path):
    """AWA-M5.6 — a selected tactic with no children names the tactic.

    "No items for today" would be wrong twice over on this panel: nothing
    here is about today, and it would not say which tactic is empty.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps, title="Publish the essay")
        root, panel = _panel(tmp_path, vps, tactic.id)
        try:
            texts = _scroll_texts(panel)
            assert "No items for today" not in texts
            assert any("Publish the essay" in text for text in texts), texts
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam57_no_selection_is_not_an_error(tmp_path):
    """AWA-M5.7 — with nothing selected the panel prompts and raises nothing.

    The panel is built before anything can be selected, so this is also the
    state every construction passes through.
    """
    vps = make_vps(tmp_path)
    try:
        root, panel = _panel(tmp_path, vps)
        try:
            from src.getmoredone.screens.week_actions import (
                WeekTacticActionsPanel,
            )
            assert panel.selected_tactic is None
            assert panel.get_todays_items() == []
            assert WeekTacticActionsPanel.EMPTY_TEXT in _scroll_texts(panel)
        finally:
            root.destroy()
    finally:
        vps.close()


# --------------------------- AWA-M4: left panel, the week's Weekly Tactics

def _week_screen(tmp_path, vps, first_day=0):
    """A WeekActionsScreen on a withdrawn root, Monday-start by default."""
    from src.getmoredone.screens.week_actions import WeekActionsScreen
    root = _root()
    app = _app_stub(vps.db_manager, vps)
    app.settings = SimpleNamespace(first_day_of_week=first_day)
    screen = WeekActionsScreen(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _this_week(first_day=0):
    from src.getmoredone import week_options
    return week_options.week_start_for(date.today(), first_day).isoformat()


def test_awam41_week_defaults_to_current_week(tmp_path):
    """AWA-M4.1 — the picker opens on this week, from the shared helper.

    Compared against week_options, not against arithmetic rewritten here: a
    test that recomputes the rule cannot catch the screen recomputing it
    differently, which is the defect the shared helper exists to prevent.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _week_screen(tmp_path, vps)
        try:
            assert screen.week_var.get() == _this_week()
            assert screen.week_combo.cget("values")[0] == _this_week()
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam42_left_panel_lists_the_weeks_tactics(tmp_path):
    """AWA-M4.2 — this week's tactics are listed; another week's are not."""
    vps = make_vps(tmp_path)
    try:
        this_week = _this_week()
        other_week = (date.fromisoformat(this_week) + timedelta(days=7)).isoformat()
        mine = make_week_item(vps, seed_ape(vps), start=this_week,
                              due=this_week, title="in this week")
        theirs = make_week_item(vps, seed_second_ape(vps), start=other_week,
                                due=other_week, title="next week")

        root, screen = _week_screen(tmp_path, vps)
        try:
            listed = {row["id"] for row in screen.tactic_rows}
            assert listed == {mine.id}
            assert theirs.id not in listed
            assert set(screen.tactic_buttons) == {mine.id}
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam43_no_tactic_is_silently_dropped(tmp_path):
    """AWA-M4.3 — ape_only=False, and the count is on screen (D4, P2).

    A Weekly Tactic whose Annual Plan Element has been detached still has
    Action Items under it. ape_only=True would hide the row and leave those
    items unreachable from this tab with nothing on screen to say so.
    """
    vps = make_vps(tmp_path)
    try:
        this_week = _this_week()
        kept = make_week_item(vps, seed_ape(vps), start=this_week,
                              due=this_week, title="has an APE")
        orphan = make_week_item(vps, seed_second_ape(vps), start=this_week,
                                due=this_week, title="APE detached")
        # No supported path can write this: item_type='week' requires an APE
        # (WT-M1.C.4). An older APE delete produced it, which is why the
        # panel has to cope with it.
        vps.db.conn.execute(
            "UPDATE action_items SET annual_plan_element_id = NULL WHERE id = ?",
            (orphan.id,),
        )
        vps.db.conn.commit()

        recorded = {}
        real = vps.get_weekly_action_items

        def recording(week_start_date=None, ape_only=True):
            recorded["ape_only"] = ape_only
            return real(week_start_date=week_start_date, ape_only=ape_only)

        root, screen = _week_screen(tmp_path, vps)
        try:
            screen.vps_manager.get_weekly_action_items = recording
            screen.load_selected_week()

            assert recorded["ape_only"] is False
            listed = {row["id"] for row in screen.tactic_rows}
            assert listed == {kept.id, orphan.id}
            # Not `"2" in ...`: the text ends in an ISO date in 2026, so
            # every value it can take contains a "2" and the assertion held
            # for a count of 0, of 1, or for no count at all.
            assert screen.status_label.cget("text").startswith(
                "2 Weekly Tactic(s) for week of ")
            assert screen.left_title_label.cget("text") == "Weekly Tactics (2)"
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam44_selecting_a_tactic_reloads_the_right_panel(tmp_path):
    """AWA-M4.4 — one selection, one reload, and the right tactic."""
    vps = make_vps(tmp_path)
    try:
        this_week = _this_week()
        tactic = make_week_item(vps, seed_ape(vps), start=this_week,
                                due=this_week, title="pick me")
        child = make_daily_item(vps, title="under it",
                                weekly_tactic_id=tactic.id, refile=False)

        root, screen = _week_screen(tmp_path, vps)
        try:
            calls = []
            real_set = screen.actions_panel.set_tactic

            def recording(row):
                calls.append(row["id"] if row else None)
                return real_set(row)

            screen.actions_panel.set_tactic = recording
            screen.select_tactic(tactic.id)

            assert calls == [tactic.id]
            assert screen.selected_tactic_id == tactic.id
            assert [item.id for item in
                    screen.actions_panel.get_todays_items()] == [child.id]
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam45_changing_week_clears_the_selection(tmp_path):
    """AWA-M4.5 — the right panel cannot keep a tactic from another week.

    Without this the panel shows last week's tactic's items beside this
    week's list, and nothing on screen says which week they belong to.
    """
    vps = make_vps(tmp_path)
    try:
        this_week = _this_week()
        next_week = (date.fromisoformat(this_week) + timedelta(days=7)).isoformat()
        tactic = make_week_item(vps, seed_ape(vps), start=this_week,
                                due=this_week, title="this week only")

        root, screen = _week_screen(tmp_path, vps)
        try:
            screen.select_tactic(tactic.id)
            assert screen.actions_panel.selected_tactic is not None

            screen.week_var.set(next_week)
            screen.load_selected_week()

            assert screen.selected_tactic_id is None
            assert screen.actions_panel.selected_tactic is None
            assert screen.actions_panel.get_todays_items() == []
        finally:
            root.destroy()
    finally:
        vps.close()


# ------------------------- AWA-M1 / AWA-M3: the rename and the new tab

def _hub(tmp_path, vps):
    """The Vision Planning hub on a withdrawn root."""
    from src.getmoredone.screens.vision_planning_hub import (
        VisionPlanningHubScreen,
    )
    root = _root()
    app = _app_stub(vps.db_manager, vps)
    app.settings = SimpleNamespace(first_day_of_week=0)
    hub = VisionPlanningHubScreen(root, vps, app)
    hub.update_idletasks()
    return root, hub


def test_awam11_and_m31_hub_nav_labels(tmp_path):
    """AWA-M1.1, AWA-M3.1 — the six nav buttons, in order, exact text.

    One list, asserted whole: the rename and the new tab are both visible
    here, and so is any reordering or any seventh button nobody meant to add.
    """
    vps = make_vps(tmp_path)
    try:
        root, hub = _hub(tmp_path, vps)
        try:
            labels = [button.cget("text")
                      for button in hub.nav_buttons.values()]
            assert labels == [
                "Vision Elements",
                "Annual Plan Elements",
                "APE Quarter Assignment",
                "APE Month Assignment",
                "APE Week Assignment",
                "APE Week Actions",
            ]
            assert list(hub.nav_buttons)[5] == "ape_week_actions"
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam12_screen_header_matches_the_tab(tmp_path):
    """AWA-M1.2 — the screen's own header says what the tab says.

    It read "APE Weekly Assignment" while the tab read "APE Weekly": two
    different names on one screen, which is the drift the rename fixes.
    """
    from src.getmoredone.screens.weekly_items import WeeklyItemsScreen

    vps = make_vps(tmp_path)
    try:
        root = _root()
        app = _app_stub(vps.db_manager, vps)
        app.settings = SimpleNamespace(first_day_of_week=0)
        try:
            screen = WeeklyItemsScreen(root, vps, app)
            screen.update_idletasks()
            headers = [
                child.cget("text")
                for child in screen.winfo_children()[0].winfo_children()
                if isinstance(child, ctk.CTkLabel)
            ]
            assert "APE Week Assignment" in headers
            assert "APE Weekly Assignment" not in headers
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam13_no_ape_weekly_label_remains():
    """AWA-M1.3 — the old name is gone from both files, counted exactly.

    Parsed from the AST's string constants rather than grepped, and asserted
    as a count of zero rather than a floor. vision_planning.py keeps its own
    "APE Weekly" placeholder caption on a screen no sidebar entry reaches;
    that is AWA-A2, recorded and deliberately out of scope.
    """
    offenders = []
    for path in (SRC / "screens" / "vision_planning_hub.py",
                 SRC / "screens" / "weekly_items.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "APE Weekly" in node.value:
                    offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def test_awam14_and_m32_every_nav_key_opens_its_own_screen(tmp_path):
    """AWA-M1.4, AWA-M3.2 — each key routes to its own screen class.

    ``open_screen`` falls back to VisionSegmentsScreen for a key that is not
    in ``mapping``, so a mistyped key looks like a working tab. Opening every
    one and naming the class it lands on is what catches that; a key/mapping
    comparison would not, since both would read the same typo.
    """
    from src.getmoredone.screens.annual_vision_segments import (
        AnnualVisionSegmentsScreen,
    )
    from src.getmoredone.screens.ape_assignment import APEAssignmentScreen
    from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen
    from src.getmoredone.screens.vision_segments import VisionSegmentsScreen
    from src.getmoredone.screens.week_actions import WeekActionsScreen
    from src.getmoredone.screens.weekly_items import WeeklyItemsScreen

    expected = {
        "vision_segments": VisionSegmentsScreen,
        "annual_vision_segments": AnnualVisionSegmentsScreen,
        "ape_assignment": APEAssignmentScreen,
        "ape_period_view": APEPeriodViewScreen,
        "ape_weekly": WeeklyItemsScreen,
        "ape_week_actions": WeekActionsScreen,
    }

    vps = make_vps(tmp_path)
    try:
        root, hub = _hub(tmp_path, vps)
        try:
            assert set(hub.nav_buttons) == set(expected)
            for key, screen_cls in expected.items():
                hub.open_screen(key)
                assert type(hub.current_screen) is screen_cls, key
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam33_screen_constructs_withdrawn(tmp_path):
    """AWA-M3.3 — the new screen builds and tears down with no mapped window.

    tests/test_ci_contract.py pins the suite's mapped-window count at 22;
    a screen that needed a real on-screen window would move it.
    """
    from src.getmoredone.screens.week_actions import WeekActionsScreen

    vps = make_vps(tmp_path)
    try:
        root, screen = _week_screen(tmp_path, vps)
        try:
            assert isinstance(screen, WeekActionsScreen)
            assert root.winfo_viewable() == 0  # withdrawn, never mapped
            panel = screen.actions_panel
            assert panel.winfo_exists()

            # Destroyed while the interpreter is still up, so the teardown is
            # observable: after root.destroy() every winfo call raises
            # TclError and nothing about the screen can be asserted at all.
            screen.destroy()
            assert not screen.winfo_exists()
            assert not panel.winfo_exists()
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam54c_add_action_item_reports_what_the_refile_did(tmp_path):
    """AWA-M5.4 - the create's cascade report reaches the user.

    ``create_action_item`` re-files into the Weekly Tactic by default, which
    can refuse a week or build cascade rows, and records what it did on the
    manager. Thirteen other screen modules report that with
    ``notify_weekly_tactic_changes``; this one dropped it, so an item saved
    un-re-filed looked identical to one that was filed. The notice has to be
    raised *before* ``edit_item``, which opens a modal: one issued after it
    stacks behind the editor.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps, start="2026-11-09")
        root, panel = _panel(tmp_path, vps, tactic.id)
        try:
            from src.getmoredone.screens import week_actions as module
            order = []
            panel._prompt_for_title = lambda: "Draft the outline"
            panel.edit_item = lambda item_id, **kw: order.append("edit")
            original = module.notify_weekly_tactic_changes
            module.notify_weekly_tactic_changes = \
                lambda db, parent=None: order.append("notify")
            try:
                panel.add_action_item()
            finally:
                module.notify_weekly_tactic_changes = original

            assert order == ["notify", "edit"]
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam41c_week_start_follows_the_first_day_setting(tmp_path):
    """AWA-M4.1 - the week comes from the setting, not from a hardcoded Monday.

    Every other test here builds the screen with ``first_day=0``, and the
    oracle for the default week calls the same production helper the screen
    does, so ``_first_day_of_week`` could have ignored
    ``app.settings.first_day_of_week`` entirely and stayed green. The oracle
    here is independent of that helper: a Monday-start week begins on a
    Monday, a Sunday-start week on a Sunday, and for any date the two differ.
    """
    vps = make_vps(tmp_path)
    try:
        starts = {}
        for first_day in (0, 6):
            root, screen = _week_screen(tmp_path, vps, first_day=first_day)
            try:
                starts[first_day] = screen.week_combo.cget("values")[0]
            finally:
                root.destroy()

        assert date.fromisoformat(starts[0]).weekday() == 0
        assert date.fromisoformat(starts[6]).weekday() == 6
        assert starts[0] != starts[6]
    finally:
        vps.close()


def test_awam41d_an_older_week_stays_in_the_picker(tmp_path):
    """AWA-M4.1 - a tactic filed against a past week is still reachable (P2).

    The picker offers four generated weeks around today; ``week_options``
    adds the weeks that tactics actually sit in, and its docstring makes that
    P2 claim. No test exercised it on this screen - both tactics in
    ``test_awam42`` fall inside the generated four - so
    ``_existing_week_starts`` could return nothing and every historical week
    would vanish from the picker with nothing red.
    """
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        old = date.today() - timedelta(days=120)
        old -= timedelta(days=old.weekday())
        make_week_item(vps, ape_id, start=old.isoformat(),
                       due=(old + timedelta(days=6)).isoformat(), title="Old")

        root, screen = _week_screen(tmp_path, vps)
        try:
            options = list(screen.week_combo.cget("values"))
            assert old.isoformat() in options
            assert screen.week_var.get() == _this_week()
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam54d_a_clean_create_does_not_report_an_old_collision(tmp_path, messageboxes):
    """AWA-M5.4 - the notice reports this save, not an earlier one.

    `last_week_collision` is cleared at the start of every *update* save, with
    a comment in `db_manager` saying why: the manager lives for the session, so
    a flag that is only ever set reads as permanently true after the first
    clash. The create path only ever set it. That was harmless while no caller
    read it after a create - AWA-M5.4 is the first, and it then showed "Week
    Already Taken" after every Add for the rest of the session, for items that
    saved perfectly well.

    Asserted on the dialog, not on the flag: the flag is the mechanism and the
    dialog is the claim the test's name makes. `conftest.py` records every
    messagebox for the whole session instead of showing it, and the
    `messageboxes` fixture empties that record on the way in, so an equality
    assertion against it is about this test. The seeded collision uses the keys
    the two producers in `db_manager` actually write - `item_id`,
    `kept_start`, `rejected_start`, `error` - because a fake that does not
    match its producer can go on passing after the producer changes.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps, start="2026-11-09")
        # Exactly what the create path's own handler leaves behind after a real
        # clash: no kept start, because nothing was created to keep.
        vps.db_manager.last_week_collision = {
            "item_id": "some-earlier-item",
            "kept_start": None,
            "rejected_start": "2026-11-09",
            "error": "UNIQUE constraint failed",
        }
        assert describe_week_collision(vps.db_manager.last_week_collision)

        root, panel = _panel(tmp_path, vps, tactic.id)
        try:
            panel._prompt_for_title = lambda: "Draft the outline"
            panel.edit_item = lambda item_id, **kw: None
            panel.add_action_item()

            assert [title for _func, title, _msg in messageboxes] == []
            assert vps.db_manager.last_week_collision is None
        finally:
            root.destroy()
    finally:
        vps.close()


def test_awam23_an_empty_string_link_counts_as_no_link(tmp_path):
    """AWA-M2.1 - the SQL answers `''` the way `tactic_of` answers it.

    The predicate used to read `weekly_tactic_id IS NULL`, so a row holding the
    empty string matched neither arm and vanished from the panel *and* from
    `_child_count`, which decides which duplicate tactic a dedupe deletes.
    `tactic_of` has always treated `''` as no link - it tests the value's
    truthiness - and the two must agree or they are not one definition.

    P8 dirty state, the same shape as AWA-M2.5 above and reachable the same
    way. `_validate_weekly_tactic_link` returns early on a falsy value, so the
    validator lets `''` through - but the column is declared `REFERENCES
    action_items(id)` and the connection runs with `PRAGMA foreign_keys = ON`,
    so with foreign keys on the write is refused (measured: writing it raises
    `IntegrityError: FOREIGN KEY constraint failed`). The state that survives
    is one written with foreign keys off: an older build, a direct sqlite3
    edit, a restored backup. So this is seeded the way AWA-M2.5 is, and the
    claim is about the read.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps, start="2026-11-09")
        child = make_daily_item(vps, "Empty string link", start="2026-11-09",
                                due="2026-11-09", parent_id=tactic.id,
                                refile=False)
        vps.db.conn.execute("PRAGMA foreign_keys = OFF")
        try:
            vps.db.conn.execute(
                "UPDATE action_items SET weekly_tactic_id = '' WHERE id = ?",
                (child.id,))
            vps.db.conn.commit()
        finally:
            vps.db.conn.execute("PRAGMA foreign_keys = ON")

        # The dirty state really is dirty, so the assertions below are about
        # the predicate and not about a row that quietly stayed NULL.
        stored = vps.db.conn.execute(
            "SELECT weekly_tactic_id FROM action_items WHERE id = ?",
            (child.id,)).fetchone()["weekly_tactic_id"]
        assert stored == ""

        listed = vps.get_action_items_for_weekly_tactic(tactic.id)
        assert [item.id for item in listed] == [child.id]

        # And the same row, counted by the other consumer of the predicate.
        assert _child_count(vps.db.conn, tactic.id) == 1
    finally:
        vps.close()