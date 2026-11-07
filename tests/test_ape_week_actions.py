"""Tests for the APE Week Assignment rename and the APE Week Actions tab.

Spec: docs/spec_2026-11-07_ape_week_actions.md

Covers AWA-M1 (the rename) through AWA-M6 (the seam cut into the Today
screen). Every test name carries the criterion ID it verifies.

The screens here are built on a **withdrawn** root, so none of them adds to
the mapped-window count that tests/test_ci_contract.py pins at 22
(AWA-M3.3).
"""

import ast
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import customtkinter as ctk

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem
from src.getmoredone.screens.today import TodayScreen
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
    """AWA-M2.3 — the union predicate is written in exactly one place.

    Counted over function bodies whose string constants name *both*
    columns. Exact lists, not floors: a second copy in vps_manager fails,
    and so does any screen writing the predicate itself instead of calling
    the helper.

    Scope note: the spec's §3 table says "AST walk over screens/: exactly
    one", written before §4 settled the helper into vps_manager. With the
    helper there, screens/ must hold **none** and vps_manager exactly one —
    which is what the criterion means, and what is asserted here.
    """
    def bodies_naming_both(path):
        tree = ast.parse(path.read_text())
        hits = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            strings = [
                sub.value for sub in ast.walk(node)
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
            ]
            if any("weekly_tactic_id" in s for s in strings) and \
               any("parent_id" in s for s in strings):
                hits.append(node.name)
        return hits

    screen_hits = []
    for path in sorted((SRC / "screens").glob("*.py")):
        screen_hits.extend(f"{path.name}::{name}"
                           for name in bodies_naming_both(path))
    assert screen_hits == []

    assert bodies_naming_both(SRC / "vps_manager.py") == [
        "get_action_items_for_weekly_tactic"
    ]


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
    """AWA-M2.5 — P8 dirty state: the tactic row is gone, the child is not.

    Deleting a tactic row directly, as an older build's cascade could,
    leaves children pointing at an id with no row. The helper returns
    nothing and does not raise.
    """
    vps = make_vps(tmp_path)
    try:
        tactic, _ = _tactic_and_ape(vps)
        make_daily_item(vps, title="orphan", weekly_tactic_id=tactic.id,
                        refile=False)
        vps.db.conn.execute("DELETE FROM action_items WHERE id = ?",
                            (tactic.id,))
        vps.db.conn.commit()

        assert vps.get_action_items_for_weekly_tactic(tactic.id) == []
    finally:
        vps.close()
