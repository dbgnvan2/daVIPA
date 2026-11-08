"""WTP-M6.7 — the completion question is asked on every surface, not one.

Purpose: WTP-M6.1 was written inside ``ItemEditorDialog`` and nowhere else, so
         six other screens completed a Weekly Tactic with open children and
         asked nothing — including the Today checkbox and the Hierarchical
         tree, which are the surfaces a user actually ticks items off from.
         This file holds the question to one implementation and pins the set
         of places that call it.
Spec:    docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m6
Tests:   this file

Every ``DatabaseManager`` here comes from ``make_vps(tmp_path)``, so no test
touches the user's real application database. No test builds a window: each
screen's method is called unbound against a stub, which is how the rest of the
WTP suite drives screen code.
"""

import ast
import sys
from pathlib import Path
from types import SimpleNamespace

# Self-contained path bootstrap, for the same reason test_weekly_tactic_parent.py
# carries one: tests/test_ci_contract.py imports every test file with the repo
# root stripped from sys.path.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

from src.getmoredone.models import Status  # noqa: E402
from src.getmoredone.screens.week_collision_notice import (  # noqa: E402
    confirm_weekly_tactic_completion,
)
from tests.weekly_tactic_fixtures import (  # noqa: E402
    make_daily_item,
    make_vps,
    make_week_item,
    seed_ape,
)

_SCREENS = _ROOT / "src" / "getmoredone" / "screens"


# ------------------------------------------------------------ the surfaces ----
# Each entry drives one screen's completion method against a stub carrying
# only what that method touches.


def _drive_today(manager, item_id):
    from src.getmoredone.screens.today import TodayScreen
    stub = SimpleNamespace(
        db_manager=manager,
        refresh=lambda: None,
        _session_completed_count=0,
        _maybe_show_completion_confetti=lambda: None,
    )
    TodayScreen.complete_item(stub, item_id)


def _drive_all_items(manager, item_id):
    from src.getmoredone.screens.all_items import AllItemsScreen
    stub = SimpleNamespace(db_manager=manager, refresh=lambda: None)
    AllItemsScreen.complete_item(stub, item_id)


def _drive_upcoming(manager, item_id):
    from src.getmoredone.screens.upcoming import UpcomingScreen
    stub = SimpleNamespace(db_manager=manager, refresh=lambda: None)
    UpcomingScreen.complete_item(stub, item_id)


def _drive_hierarchical(manager, item_id):
    from src.getmoredone.screens.hierarchical import HierarchicalScreen
    stub = SimpleNamespace(db_manager=manager, refresh=lambda: None)
    HierarchicalScreen.complete_item(stub, item_id)


def _drive_project_boards(manager, item_id):
    from src.getmoredone.screens.project_boards import ProjectBoardsScreen
    stub = SimpleNamespace(db_manager=manager, refresh=lambda: None)
    ProjectBoardsScreen.complete_item(stub, item_id)


def _drive_editor(manager, item_id):
    from src.getmoredone.screens.item_editor import ItemEditorDialog
    stub = SimpleNamespace(
        db_manager=manager,
        item=manager.get_action_item(item_id),
        item_id=item_id,
        on_dialog_close=lambda: None,
    )
    # complete_item reaches the guard through self, so the stub carries the
    # real method rather than a stand-in: the delegation is part of what is
    # under test here.
    stub._confirm_tactic_completion = (
        lambda: ItemEditorDialog._confirm_tactic_completion(stub))
    ItemEditorDialog.complete_item(stub)


def _drive_timer(manager, item_id):
    """The timer asks before its note dialog, so a decline never reaches one."""
    from src.getmoredone.screens.timer_window import TimerWindow
    stub = SimpleNamespace(
        db_manager=manager,
        item=manager.get_action_item(item_id),
        winfo_exists=lambda: True,
        next_action_window=None,
        _save_notes_to_item=lambda: None,
    )
    TimerWindow.finished_action(stub)


# The timer is left out where a test drives the accepting path: saying Yes
# there runs a work-log save and a window teardown that a stub this size
# cannot stand in for. Its decline path is what this fix changed.
DECLINE_SURFACES = {
    "today": _drive_today,
    "all_items": _drive_all_items,
    "upcoming": _drive_upcoming,
    "hierarchical": _drive_hierarchical,
    "project_boards": _drive_project_boards,
    "item_editor": _drive_editor,
    "timer_window": _drive_timer,
}

ACCEPT_SURFACES = {
    name: drive for name, drive in DECLINE_SURFACES.items()
    if name != "timer_window"
}


@pytest.fixture
def seeded(tmp_path):
    """A tactic with two open children, plus a plain item for the quiet path."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        make_daily_item(vps, title="One", weekly_tactic_id=tactic.id)
        make_daily_item(vps, title="Two", weekly_tactic_id=tactic.id)
        plain = make_daily_item(vps, title="An ordinary item")
        yield SimpleNamespace(vps=vps, manager=vps.db_manager,
                              tactic=tactic, plain=plain)
    finally:
        vps.close()


def _record_answer(monkeypatch, answer):
    """Intercept the one messagebox the guard uses. Returns the asked list."""
    import tkinter.messagebox as messagebox
    asked = []

    def fake(title, message, **kw):
        asked.append(message)
        return answer

    monkeypatch.setattr(messagebox, "askyesno", fake)
    return asked


@pytest.mark.parametrize("surface", sorted(DECLINE_SURFACES))
def test_wtpm67_every_completion_surface_asks_first(surface, seeded, monkeypatch):
    """WTP-M6.7 — the prompt fires, and names the count, on every surface."""
    asked = _record_answer(monkeypatch, False)

    DECLINE_SURFACES[surface](seeded.manager, seeded.tactic.id)

    assert len(asked) == 1, f"{surface} asked {len(asked)} times"
    assert "2 Action Items" in asked[0]


@pytest.mark.parametrize("surface", sorted(DECLINE_SURFACES))
def test_wtpm67_a_declined_prompt_completes_nothing_on_any_surface(
        surface, seeded, monkeypatch):
    """WTP-M6.1 — No means the row is untouched, asserted against the row."""
    _record_answer(monkeypatch, False)

    DECLINE_SURFACES[surface](seeded.manager, seeded.tactic.id)

    after = seeded.manager.get_action_item(seeded.tactic.id)
    assert after.status != Status.COMPLETED, f"{surface} completed it anyway"


@pytest.mark.parametrize("surface", sorted(ACCEPT_SURFACES))
def test_wtpm67_yes_completes_it_on_any_surface(surface, seeded, monkeypatch):
    """The guard is a question, not a refusal (WTP-D8): Yes still completes."""
    _record_answer(monkeypatch, True)

    ACCEPT_SURFACES[surface](seeded.manager, seeded.tactic.id)

    after = seeded.manager.get_action_item(seeded.tactic.id)
    assert after.status == Status.COMPLETED, f"{surface} refused a Yes"


@pytest.mark.parametrize("surface", sorted(ACCEPT_SURFACES))
def test_wtpm67_an_ordinary_item_is_never_questioned(surface, seeded, monkeypatch):
    """WTP-M6.3 — the ordinary path is unchanged for a non-tactic item."""
    asked = _record_answer(monkeypatch, False)

    ACCEPT_SURFACES[surface](seeded.manager, seeded.plain.id)

    assert asked == [], f"{surface} questioned a plain item"
    after = seeded.manager.get_action_item(seeded.plain.id)
    assert after.status == Status.COMPLETED


# -------------------------------------------------- the guard's own answer ----


def test_wtpm67_a_tactic_whose_children_are_done_is_not_questioned(
        seeded, monkeypatch):
    """No open child, no question — the count, not the item type, decides.

    P8 — the done state is written straight to the rows on purpose.
    ``complete_action_item`` re-files a completed item onto the tactic for the
    week it was finished in (the year-rollover cascade), so driving it here
    would move both children off this tactic and leave the status filter
    below untested: ``get_children`` would return nothing whatever the filter
    said. A completed child that is still linked is the state this line is
    for, and it is the same state ``test_wtpm63`` seeds for the editor.
    """
    asked = _record_answer(monkeypatch, False)
    for child in seeded.manager.get_children(seeded.tactic.id):
        seeded.vps.db.conn.execute(
            "UPDATE action_items SET status = ? WHERE id = ?",
            (Status.COMPLETED, child.id))
    seeded.vps.db.conn.commit()

    still_linked = seeded.manager.get_children(seeded.tactic.id)
    assert len(still_linked) == 2, "the seed must leave them under the tactic"
    assert all(c.status == Status.COMPLETED for c in still_linked)

    assert confirm_weekly_tactic_completion(
        seeded.manager, seeded.tactic.id, None) is True
    assert asked == []


def test_wtpm67_a_missing_row_is_not_questioned(seeded, monkeypatch):
    """A deleted item cannot be a tactic with children. No prompt, no crash."""
    asked = _record_answer(monkeypatch, False)

    assert confirm_weekly_tactic_completion(
        seeded.manager, "no-such-id", None) is True
    assert asked == []


def test_wtpm67_one_open_child_is_singular(seeded, monkeypatch):
    """P7 — a message that always said "Action Items" would read wrong at one."""
    asked = _record_answer(monkeypatch, False)
    first = seeded.manager.get_children(seeded.tactic.id)[0]
    seeded.manager.complete_action_item(first.id)

    confirm_weekly_tactic_completion(seeded.manager, seeded.tactic.id, None)

    assert len(asked) == 1
    assert "1 Action Item under this Weekly Tactic is still open" in asked[0]


# ------------------------------------------------------ the P25 regression ----


def _completion_call_sites():
    """Every screen function that calls ``complete_action_item``, by AST.

    Walked rather than grepped, and asserted as an exact set rather than a
    floor, because the finding this file answers was a guard that covered one
    of seven call sites: a floor would have passed that state.
    """
    sites = {}
    for path in sorted(_SCREENS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            calls = [
                inner for inner in ast.walk(node)
                if isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "complete_action_item"
            ]
            if calls:
                sites[(path.name, node.name)] = len(calls)
    return sites


EXPECTED_CALL_SITES = {
    ("all_items.py", "complete_item"): 1,
    ("hierarchical.py", "complete_item"): 1,
    ("item_editor.py", "complete_item"): 1,
    ("project_boards.py", "complete_item"): 1,
    ("timer_window.py", "finished_action"): 2,
    ("today.py", "complete_item"): 1,
    ("upcoming.py", "complete_item"): 1,
}


def test_wtpm67_the_set_of_completion_call_sites_is_pinned():
    """A new screen that completes an item fails here until it is listed."""
    assert _completion_call_sites() == EXPECTED_CALL_SITES


def test_wtpm67_every_completion_call_site_is_guarded():
    """Each of them asks first — by name, in the same function.

    ``item_editor.complete_item`` calls the guard through its own
    ``_confirm_tactic_completion``, which is a one-line delegation to the
    shared function; both names count here, and nothing else does.
    """
    guards = {"confirm_weekly_tactic_completion", "_confirm_tactic_completion"}
    unguarded = []
    for (filename, funcname) in EXPECTED_CALL_SITES:
        tree = ast.parse((_SCREENS / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == funcname):
                names = {
                    inner.id for inner in ast.walk(node)
                    if isinstance(inner, ast.Name)
                } | {
                    inner.attr for inner in ast.walk(node)
                    if isinstance(inner, ast.Attribute)
                }
                if not names & guards:
                    unguarded.append(f"{filename}::{funcname}")
    assert unguarded == []
