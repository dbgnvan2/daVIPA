"""WTP-M6.7 — the completion question, driven through the real widgets.

Purpose: tests/test_weekly_tactic_completion_surfaces.py drives each screen's
         ``complete_item`` unbound against a SimpleNamespace, so it proves the
         guard is *in* the method and nothing about the control that reaches
         it. Three things were therefore untested: that the screen builds at
         all with the guard's import in place, that the widget a user clicks
         is wired to the guarded method, and that the modal survives a real Tk
         parent -- the always-on-top wrapper had only ever seen a stub, which
         is the "bad window path name" risk the handoff note's checklist
         step 10 was written for.
Spec:    docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m6
Tests:   this file

Each test builds the real screen on a real ``DatabaseManager`` over a
``tmp_path`` database, finds the completion control the screen itself created
by reading the item id out of that widget's own command, and presses it with
the widget's own ``toggle()`` / ``invoke()``. Every window is withdrawn --
conftest withdraws them on creation and none of these needs mapping, so none
takes the ``mapped_windows`` fixture and none appears on anybody's screen.

``askyesno`` answers False by default (conftest's ``_MESSAGEBOX_DEFAULTS``), so
the decline tests assert against the suite-wide recorder rather than a stub of
their own; the accept tests patch it to True.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

# Self-contained path bootstrap, for the same reason the other two
# weekly-tactic files carry one: tests/test_ci_contract.py imports every test
# file with the repo root stripped from sys.path.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import customtkinter as ctk  # noqa: E402
import pytest  # noqa: E402

from src.getmoredone.models import ActionItem, ProjectBoard, Status  # noqa: E402
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

# The screens whose rows carry a control that completes an item. Asserted as an
# exact set by test_wtpw_the_screens_with_a_completion_control_are_pinned, and
# deliberately NOT the same set as the seven guarded call sites:
# HierarchicalScreen.complete_item exists and is guarded but has no caller, so
# there is nothing on that screen for this file to press (WTP-A8).
SCREENS_WITH_A_CONTROL = {"all_items.py", "item_editor.py",
                          "project_boards.py", "today.py", "upcoming.py"}


# --------------------------------------------------------------- the world ----


@pytest.fixture
def root():
    win = ctk.CTk()
    win.withdraw()
    # 1400x900 so responsive_column_chars does not collapse to its narrowest
    # layout; nothing here reads a rendered width, but a screen that lays out
    # for a 1px window is not the screen under test.
    win.geometry("1400x900+0+0")
    yield win
    win.destroy()


@pytest.fixture
def world(tmp_path):
    """A Weekly Tactic with two open children, dated today.

    Today's real date, because TodayScreen and UpcomingScreen filter on the
    clock: a fixed date would put the row on neither screen and the test would
    be measuring the date, not the guard.
    """
    vps = make_vps(tmp_path)
    ape_id = seed_ape(vps)
    today = date.today().isoformat()
    tactic = make_week_item(vps, ape_id, start=today, due=today, title="Tactic")
    children = [
        make_daily_item(vps, title=f"Child {n}", start=today, due=today,
                        weekly_tactic_id=tactic.id)
        for n in (1, 2)
    ]
    yield vps, tactic, children
    vps.db_manager.close()


def _app(vps):
    app = MagicMock()
    app.vps_manager = vps
    return app


def _status(manager, item_id):
    return manager.get_action_item(item_id).status


# ------------------------------------------------------ finding the control ----


def _descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from _descendants(child)


def _command_of(widget):
    """The callback the screen gave this widget.

    ``cget("command")`` works on CTkButton but raises on CTkCheckBox --
    CustomTkinter does not list ``command`` among a checkbox's gettable
    arguments -- so the private ``_command`` it stores is the fallback. Read
    rather than reconstructed: the point of this file is to press the callable
    the screen actually installed.
    """
    try:
        command = widget.cget("command")
    except Exception:
        command = getattr(widget, "_command", None)
    return command if callable(command) else None


def _targets(command, item_id: str) -> bool:
    """Does ``command`` close over this item?

    The screens bind the row's item three different ways: the editor's button
    is simply bound to ``self.complete_item`` and reads ``self.item_id``, while
    today and upcoming
    close over the ActionItem itself, while all_items and project_boards pin
    the id as a lambda default (``lambda i=item.id: ...``) to dodge the
    late-binding trap. Both the closure cells and the defaults are read, and
    both an ActionItem and a bare id are accepted, because a predicate that
    knew only one shape would quietly find nothing on half the screens --
    which is what "found 0" meant on the first run of this file.

    Reading the callback rather than matching the row's rendered text on
    purpose: titles are split, truncated to a responsive width and decorated
    with a "WT" badge, so text matching would make this file fail on a layout
    change instead of on a wiring change.
    """
    owner = getattr(command, "__self__", None)
    if owner is not None and getattr(owner, "item_id", None) == item_id:
        return True   # the editor's button is bound to self.complete_item

    values = list(command.__defaults__ or ())
    values += list((command.__kwdefaults__ or {}).values())
    for cell in command.__closure__ or ():
        try:
            values.append(cell.cell_contents)
        except ValueError:  # an empty cell
            continue
    for value in values:
        if isinstance(value, str) and value == item_id:
            return True
        if getattr(value, "id", None) == item_id:
            return True
    return False


def _calls_complete_item(command) -> bool:
    """Does this widget callback call ``complete_item``?

    By the callback's own name or bytecode names rather than by widget class or
    position, so a screen that grows a second button in the same row does not
    silently become the one this file presses.

    Two shapes: the editor's button is bound straight to ``complete_item``, so
    the method's own ``__name__`` is the match -- its bytecode does not name
    itself. The row lambdas elsewhere call it, so it appears among their
    ``co_names``.
    """
    if getattr(command, "__name__", None) == "complete_item":
        return True
    code = getattr(command, "__code__", None)
    return code is not None and "complete_item" in code.co_names


def _completion_control(screen, item_id: str):
    """The one widget on ``screen`` that completes ``item_id``.

    Asserts there is exactly one. Two would mean a user could complete the
    same row from two controls on one screen, only one of which this file
    would then be pressing.
    """
    found = [
        widget
        for widget in _descendants(screen)
        if isinstance(widget, (ctk.CTkCheckBox, ctk.CTkButton))
        and (command := _command_of(widget)) is not None
        and _calls_complete_item(command)
        and _targets(command, item_id)
    ]
    assert len(found) == 1, (
        f"expected one completion control for {item_id} on "
        f"{type(screen).__name__}, found {len(found)}"
    )
    return found[0]


def _press(widget):
    """Press it the way a user does, through the widget's own entry point."""
    if isinstance(widget, ctk.CTkCheckBox):
        widget.toggle()          # refuses when disabled, like a real click
    else:
        widget.invoke()


# ------------------------------------------------------- building the screens ----


def _today(root, vps):
    from src.getmoredone.screens.today import TodayScreen
    return _packed(TodayScreen(root, vps.db_manager, _app(vps)))


def _all_items(root, vps):
    from src.getmoredone.screens.all_items import AllItemsScreen
    return _packed(AllItemsScreen(root, vps.db_manager, _app(vps)))


def _upcoming(root, vps):
    from src.getmoredone.screens.upcoming import UpcomingScreen
    return _packed(UpcomingScreen(root, vps.db_manager, _app(vps)))


def _project_boards(root, vps, item_ids):
    from src.getmoredone.screens.project_boards import ProjectBoardsScreen
    board_id = vps.db_manager.create_project_board(ProjectBoard(title="Board"))
    for item_id in item_ids:
        vps.db_manager.link_action_item_to_project_board(board_id, item_id)
    screen = ProjectBoardsScreen(root, vps.db_manager, _app(vps))
    screen.selected_board_id = board_id
    _packed(screen)
    screen.refresh()
    screen.update_idletasks()
    return screen


def _item_editor(root, vps, item_id):
    from src.getmoredone.screens.item_editor import ItemEditorDialog
    dialog = ItemEditorDialog(root, vps.db_manager, item_id,
                              vps_manager=vps, on_close_callback=lambda: None)
    dialog.update_idletasks()
    return dialog


def _packed(screen):
    screen.pack(fill="both", expand=True)
    screen.update_idletasks()
    return screen


BUILDERS = {
    "today": lambda root, vps, tactic, children: _today(root, vps),
    "all_items": lambda root, vps, tactic, children: _all_items(root, vps),
    "upcoming": lambda root, vps, tactic, children: _upcoming(root, vps),
    "project_boards": lambda root, vps, tactic, children: _project_boards(
        root, vps, [tactic.id] + [child.id for child in children]),
    "item_editor": lambda root, vps, tactic, children: _item_editor(
        root, vps, tactic.id),
}


# ------------------------------------------------------------- the decline ----


@pytest.mark.parametrize("surface", sorted(BUILDERS))
def test_wtpw_the_real_control_asks_before_completing_a_tactic(
        surface, root, world, messageboxes):
    """Pressing the real control raises the question, with the real count.

    This is the test the stub version could not be: it fails if the control is
    wired to something other than the guarded method, and it fails if the
    screen cannot be built at all.
    """
    vps, tactic, children = world
    screen = BUILDERS[surface](root, vps, tactic, children)

    _press(_completion_control(screen, tactic.id))

    assert [name for name, _title, _message in messageboxes] == ["askyesno"], (
        f"{surface}: pressing the completion control on a Weekly Tactic with "
        f"two open children must ask exactly once; got {messageboxes}"
    )
    _name, title, message = messageboxes[0]
    assert title == "Complete Weekly Tactic", f"{surface}: {title!r}"
    assert "2 Action Items" in message, f"{surface}: {message!r}"


@pytest.mark.parametrize("surface", sorted(BUILDERS))
def test_wtpw_a_declined_prompt_leaves_the_row_open(surface, root, world):
    """No means nothing happened -- read back from the row, not from a flag."""
    vps, tactic, children = world
    screen = BUILDERS[surface](root, vps, tactic, children)

    _press(_completion_control(screen, tactic.id))   # askyesno defaults to No

    assert _status(vps.db_manager, tactic.id) != Status.COMPLETED, (
        f"{surface}: declining the prompt completed the tactic anyway"
    )
    for child in children:
        assert _status(vps.db_manager, child.id) != Status.COMPLETED, (
            f"{surface}: declining the prompt completed a child"
        )


# -------------------------------------------------------------- the accept ----


@pytest.mark.parametrize("surface", sorted(BUILDERS))
def test_wtpw_an_accepted_prompt_completes_the_tactic_only(
        surface, root, world, monkeypatch):
    """Yes completes the tactic and leaves its children open (WTP-D8)."""
    import tkinter.messagebox as messagebox
    vps, tactic, children = world
    screen = BUILDERS[surface](root, vps, tactic, children)
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)

    _press(_completion_control(screen, tactic.id))

    assert _status(vps.db_manager, tactic.id) == Status.COMPLETED, (
        f"{surface}: accepting the prompt did not complete the tactic"
    )
    for child in children:
        assert _status(vps.db_manager, child.id) != Status.COMPLETED, (
            f"{surface}: completion cascaded to a child"
        )


# ------------------------------------------------- the unquestioned paths ----


def test_wtpw_a_plain_item_is_completed_with_no_question(
        root, world, messageboxes):
    """An ordinary Action Item is not a tactic: press, done, nothing asked."""
    vps, _tactic, children = world
    screen = _all_items(root, vps)

    _press(_completion_control(screen, children[0].id))

    assert messageboxes == [], f"a plain item asked something: {messageboxes}"
    assert _status(vps.db_manager, children[0].id) == Status.COMPLETED


def test_wtpw_a_tactic_whose_children_are_all_done_is_not_questioned(
        root, world, messageboxes):
    """Nothing is left open, so there is nothing to warn about.

    The children are still linked to the tactic and marked COMPLETED by SQL,
    not by driving ``complete_action_item``: completion re-files a child onto
    the Weekly Tactic for the week it was finished in (WTP-M6.6), so going
    through the real call would move both children off this tactic and
    ``get_children`` would return nothing. The status filter would then never
    be reached, and a mutation that counts completed children as open would
    survive -- which is exactly what it did on the first run of the mutation
    gate for this file (P8: seed the state the line is for).
    """
    vps, tactic, children = world
    manager = vps.db_manager
    manager.db.conn.executemany(
        "UPDATE action_items SET status = ? WHERE id = ?",
        [(Status.COMPLETED, child.id) for child in children],
    )
    manager.db.conn.commit()
    assert {child.id for child in manager.get_children(tactic.id)} == {
        child.id for child in children
    }, "the seed moved the children off the tactic; the filter is not reached"

    screen = _all_items(root, vps)
    _press(_completion_control(screen, tactic.id))

    assert messageboxes == [], (
        f"a tactic with nothing open asked anyway: {messageboxes}"
    )
    assert _status(manager, tactic.id) == Status.COMPLETED


# ------------------------------------------------ the modal's real parent ----


def test_wtpw_the_prompt_survives_a_real_always_on_top_parent(
        root, world, messageboxes):
    """Checklist step 10, as a test: a real Toplevel parent, -topmost set.

    The guard wraps its modal in _parent_not_on_top, which reads and rewrites
    -topmost on the parent so the question is not hidden behind the timer. Every
    other test of it passes a SimpleNamespace, which has no Tk window behind it
    and so cannot raise the "bad window path name" this is here to rule out.
    -topmost is read and written through tk.call rather than .attributes, past
    the patch conftest uses to keep always-on-top windows off the desktop --
    otherwise this would be measuring conftest.
    """
    vps, tactic, _children = world
    parent = ctk.CTkToplevel(root)
    parent.withdraw()
    parent.tk.call("wm", "attributes", parent._w, "-topmost", True)
    try:
        answer = confirm_weekly_tactic_completion(
            vps.db_manager, tactic.id, parent)

        assert answer is False, "askyesno defaults to No; the guard must relay it"
        assert [name for name, _t, _m in messageboxes] == ["askyesno"]
        restored = parent.tk.call(
            "wm", "attributes", parent._w, "-topmost")
        assert str(restored) in ("1", "True", "true"), (
            f"-topmost was not put back after the modal: {restored!r}"
        )
        assert parent.winfo_exists(), "the parent did not survive the modal"
    finally:
        parent.destroy()


# ---------------------------------------------------------- the real denominator ----


def test_wtpw_the_screens_with_a_completion_control_are_pinned():
    """Which screens wire a widget to ``complete_item``.

    Exactly that, and not "every completion control a user can reach": the
    predicate looks for a ``command=`` whose value names ``complete_item``, so
    the timer's Done button is outside this pin by construction -- it reaches
    ``complete_action_item`` through ``finished_action``. That is not a
    coverage hole, since the two timer tests in this file call
    ``finished_action`` -- the method Done reaches, through
    ``done_action``'s reward sequence -- and ``EXPECTED_CALL_SITES`` in the
    surfaces file pins the call site. They do not press the button itself, so
    ``done_action`` is covered by neither; the pin's reach stops where its
    predicate does.

    Five screens, not the seven guarded call sites that
    tests/test_weekly_tactic_completion_surfaces.py pins: the timer is
    excluded as above, and ``HierarchicalScreen.complete_item`` has no caller
    anywhere in src (WTP-A8). Of the five, three wire a row checkbox (today,
    all_items, upcoming) and two wire a Complete button (project_boards at
    1532, item_editor at 487). A project board row also carries a checkbox,
    but that one toggles the screen's selection set through
    ``_on_item_checkbox_changed`` and completes nothing.

    An exact set, so wiring a control to a new screen fails here and has to be
    added to this file's BUILDERS rather than shipping unpressed.
    """
    import ast

    found = set()
    for path in sorted(_SCREENS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg != "command":
                    continue
                if "complete_item" in {
                    sub.attr for sub in ast.walk(keyword.value)
                    if isinstance(sub, ast.Attribute)
                }:
                    found.add(path.name)

    assert found == SCREENS_WITH_A_CONTROL, (
        f"the screens offering a completion control changed: {found}. Every "
        "one of them must appear in this file's BUILDERS, or its control ships "
        "with nobody pressing it."
    )


# ------------------------------------------------------------- the timer ----
# tests/test_weekly_tactic_completion_surfaces.py leaves the timer out of its
# ACCEPT_SURFACES: saying Yes there runs a work-log save and a window teardown
# a SimpleNamespace cannot stand in for. These two build the real TimerWindow
# and drive the real note dialog, so the accepting path is covered here.


@pytest.fixture
def quiet_timer(monkeypatch):
    """Silence sound, music and the window flash. The dialogs are the subject."""
    from src.getmoredone.screens.timer_window import TimerWindow
    monkeypatch.setattr(TimerWindow, "_start_music", lambda self: False)
    monkeypatch.setattr(TimerWindow, "_stop_music", lambda self: None)
    monkeypatch.setattr(
        TimerWindow, "play_sound", lambda self, is_break_start: None)
    monkeypatch.setattr(TimerWindow, "_flash_window", lambda self: None)
    yield


@pytest.fixture(autouse=True)
def _empty_timer_registry():
    """The live-timer registry is module level, so it leaks between tests (P8)."""
    from src.getmoredone.screens import timer_window as tw
    tw._LIVE_TIMERS.clear()
    yield
    tw._LIVE_TIMERS.clear()


def _stopped_timer(root, manager, item, vps):
    """A timer that has run and been stopped -- the state Done appears in.

    The deliverable is written first because RP-4.2 makes start_timer confirm
    one for a project-linked item, and a Weekly Tactic always carries an APE.
    Without it start_timer blocks in wait_window on the deliverable dialog and
    the test hangs rather than failing -- which is how the first run of this
    file behaved.
    """
    import random
    from src.getmoredone.screens.timer_window import TimerWindow
    item.deliverable = "Draft the section"
    manager.update_action_item(item)
    timer = TimerWindow(root, manager, item, rng=random.Random(1),
                        vps_manager=vps)
    timer.start_timer()
    timer._cancel_pending_timer()
    timer.work_seconds_elapsed = 25 * 60
    timer.stop_timer()
    return timer


def _skip_the_note_dialog(timer, tries=50):
    """Press Skip on the real note dialog, if and when one appears.

    Scheduled before the handler runs, because finished_action blocks in
    wait_window until the dialog is gone.

    Both timer tests arm this, including the one that expects no dialog at all.
    Without it the decline test *hangs* under mutation instead of failing:
    delete the guard and finished_action walks straight into the note dialog
    and blocks in wait_window with nobody to dismiss it. A test that hangs
    rather than going red is not a test that can fail.

    Bounded retries, so an armed dismisser on a run where no dialog ever opens
    stops rescheduling itself instead of firing until teardown.
    """
    from src.getmoredone.screens.timer_window_dialogs import CompletionNoteDialog

    def press(left=tries):
        for child in timer.winfo_children():
            if isinstance(child, CompletionNoteDialog):
                child.skip()
                return
        if left:
            timer.after(20, lambda: press(left - 1))   # not built yet

    timer.after(20, press)


def test_wtpw_the_timer_asks_and_a_no_costs_the_user_nothing(
        root, world, quiet_timer, messageboxes):
    """Declining on the Done button leaves the item, the note and the window.

    The guard sits before the note dialog and before the Next Action window is
    destroyed precisely so this is true, and that ordering is the one thing a
    stub could not check.
    """
    vps, tactic, children = world
    manager = vps.db_manager
    timer = _stopped_timer(root, manager, tactic, vps)

    _skip_the_note_dialog(timer)     # armed, and must never be needed
    timer.finished_action()          # askyesno defaults to No

    assert [name for name, _t, _m in messageboxes] == ["askyesno"], (
        f"the Done button must ask exactly once; got {messageboxes}"
    )
    assert _status(manager, tactic.id) != Status.COMPLETED, (
        "declining on the timer completed the tactic anyway"
    )
    assert manager.get_work_logs(tactic.id) == [], (
        "declining wrote a work log for a session that was not finished"
    )
    assert timer.winfo_exists(), "declining destroyed the timer window"


def test_wtpw_the_timer_completes_the_tactic_on_yes(
        root, world, quiet_timer, monkeypatch):
    """The accepting path: the row completes, the session is logged, kids stay open."""
    import tkinter.messagebox as messagebox
    vps, tactic, children = world
    manager = vps.db_manager
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    timer = _stopped_timer(root, manager, tactic, vps)

    _skip_the_note_dialog(timer)
    timer.finished_action()

    assert _status(manager, tactic.id) == Status.COMPLETED, (
        "accepting on the timer did not complete the tactic"
    )
    assert manager.get_work_logs(tactic.id), "the session was not recorded"
    for child in children:
        assert _status(manager, child.id) != Status.COMPLETED, (
            "the timer's completion cascaded to a child"
        )
