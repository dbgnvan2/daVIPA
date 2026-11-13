"""One control contract per VSP tab, after the Add New batch.

Spec: docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md

Required by `~/.claude/standards/ui-regression.md`: this batch removed a
user-visible control from five screens — four header Saves and three bottom
buttons on APE Week Assignment — and added a bottom Add New to five. Each tab
gets one test naming the controls that must be there afterwards, so the next
change to any of these headers has to say so.

Screens are built on a **withdrawn** root with a real ``VPSManager`` on a
temporary database. Real, because a control contract is about the chrome a
screen builds and the chrome is built from the same constructor the app runs;
withdrawn, because a mapped window would change the count
tests/test_ci_contract.py pins.
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

from src.getmoredone.screens.annual_vision_segments import (  # noqa: E402
    AnnualVisionSegmentsScreen,
)
from src.getmoredone.screens import ape_assignment as quarter_mod  # noqa: E402
from src.getmoredone.screens import ape_period_view as month_mod  # noqa: E402
from src.getmoredone.screens.ape_assignment import APEAssignmentScreen  # noqa: E402
from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen  # noqa: E402
from src.getmoredone.screens.vision_segments import VisionSegmentsScreen  # noqa: E402
from src.getmoredone.screens.week_actions import WeekActionsScreen  # noqa: E402
from src.getmoredone.screens.weekly_items import WeeklyItemsScreen  # noqa: E402
from tests.weekly_tactic_fixtures import make_vps, seed_ape  # noqa: E402

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


def _screen(cls, vps):
    """One tab on a withdrawn root, built the way the app builds it.

    ``settings`` is left off the app stub on purpose: each screen that wants
    one loads its own, and conftest.py points that at a temporary file.
    """
    root = _root()
    app = SimpleNamespace(vps_manager=vps, db_manager=vps.db_manager)
    screen = cls(root, vps, app)
    screen.update_idletasks()
    return root, screen


def _buttons(frame):
    """The text of every CTkButton directly under a frame, in child order."""
    return [child.cget("text") for child in frame.winfo_children()
            if isinstance(child, ctk.CTkButton)]


def _all_buttons(frame):
    """The text of every CTkButton anywhere under a frame, in child order."""
    out = []
    for child in frame.winfo_children():
        if isinstance(child, ctk.CTkButton):
            out.append(child.cget("text"))
        else:
            out.extend(_all_buttons(child))
    return out


def _assert_bottom_left(screen):
    """The action row is under the left panel, and the right panel has none.

    Three cells of ``screen.body``, read off the live grid rather than off an
    attribute name. The first version of this check compared two column
    numbers and asserted ``not hasattr(screen, "right_actions")``, which the
    cold sweep found guards much less than it claims: a button gridded
    straight into ``body`` row 2 column 2, or into ``right_frame``, or into a
    frame stored under any other name, passed all three assertions — and a
    later refactor onto a shared row *named* ``right_actions`` would have
    reddened it for a reason that has nothing to do with where a button sits.
    """
    body = screen.body
    assert screen.left_actions.master is body, (
        "the action row belongs to the body grid, not inside a panel")
    left_col = int(screen.left_frame.grid_info()["column"])
    actions = screen.left_actions.grid_info()
    assert int(actions["column"]) == left_col, (
        "the add button must sit in the left panel's column")
    assert int(actions["row"]) > int(screen.left_frame.grid_info()["row"]), (
        "the add button must sit below the left panel, not above it")
    right_col = int(screen.right_frame.grid_info()["column"])
    assert body.grid_slaves(row=int(actions["row"]), column=right_col) == [], (
        "the right panel must carry no action row of its own")
    assert _all_buttons(screen.right_frame) == [], (
        "no button may be parented inside the right panel either")


def _header(screen):
    """The header card a screen grids its filter row into."""
    return screen.filter_row.master


def _row_buttons(table):
    """The buttons on the first rendered row of a ChipTable."""
    frame, _cells = table.rows[0]
    return _all_buttons(frame)


# ------------------------------------------------------- VTF-M7.1, tab by tab

def test_vtfm71_vision_elements_controls(tmp_path):
    """VTF-M7.1 / VTF-M6 — Refresh on top, the switcher, New at the bottom.

    This tab is three lists shown one at a time, so decision D1 kept its
    structure and moved the buttons only: the New button's label still
    follows the active view, from the bottom row rather than the top one.
    """
    vps = make_vps(tmp_path)
    try:
        seed_ape(vps, year=YEAR)
        root, screen = _screen(VisionSegmentsScreen, vps)
        try:
            assert _buttons(screen.refresh_btn.master) == ["Refresh"], (
                "the top row is Refresh alone")
            assert _buttons(screen.bottom_actions) == ["+ New Category"], (
                "the New button must be the bottom row, labelled for the view")
            assert sorted(screen.view_buttons) == [
                "categories", "segments", "subsegments"]
            assert _all_buttons(screen.cat_list)[-2:] == ["Edit", "Delete"], (
                "a category row keeps its own Edit and Delete")
        finally:
            root.destroy()
    finally:
        vps.close()


def test_vtfm71_annual_plan_elements_controls(tmp_path):
    """VTF-M7.1 — Load Year and Refresh on top, Add New at the bottom.

    The header Save is gone (VTF-M4.1): it wrote from the ticks, and a tick is
    a filter now.
    """
    vps = make_vps(tmp_path)
    try:
        seed_ape(vps, year=YEAR)
        root, screen = _screen(AnnualVisionSegmentsScreen, vps)
        try:
            screen.year_var.set(str(YEAR))
            screen.refresh_lists()
            screen.update_idletasks()

            assert _buttons(_header(screen)) == ["Load Year", "Refresh"]
            assert _buttons(screen.right_actions) == [
                "Add New Annual Plan Element"]
            assert screen.status_label.master is screen.right_actions, (
                "the outcome of an add must be reported beside the button")
            assert _row_buttons(screen.right_table)[-2:] == ["Edit", "Delete"]
        finally:
            root.destroy()
    finally:
        vps.close()


def test_vtfm71_ape_quarter_assignment_controls(tmp_path):
    """VTF-M7.1 — Load and Refresh on top, Add APE Quarter at the bottom left.

    The button moved from under the right panel to under the left one and was
    renamed: the dialog it opens asks which Annual Plan Element to assign, and
    the Annual Plan Elements are the left panel. The right panel keeps no
    button of its own, which is asserted here so a later change cannot quietly
    grow a second add control at the other end of the screen.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(APEAssignmentScreen, vps)
        try:
            assert _buttons(_header(screen)) == ["Load", "Refresh"]
            assert _buttons(screen.left_actions) == ["Add APE Quarter"]
            _assert_bottom_left(screen)
        finally:
            root.destroy()
    finally:
        vps.close()


def test_vtfm71_ape_month_assignment_controls(tmp_path):
    """VTF-M7.1 — Load and Refresh on top, Add APE Month at the bottom left.

    The month screen's half of the same move; see the quarter test above.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(APEPeriodViewScreen, vps)
        try:
            assert _buttons(_header(screen)) == ["Load", "Refresh"]
            assert _buttons(screen.left_actions) == ["Add APE Month"]
            _assert_bottom_left(screen)
        finally:
            root.destroy()
    finally:
        vps.close()


def test_the_add_dialog_is_titled_for_its_button(tmp_path):
    """The dialog's title carries the label of the button that opened it.

    The two APE tabs' buttons were renamed and their dialog titles were not,
    so "Add APE Quarter" opened a window titled "Assign APE to Quarter Q4" —
    the only VSP tabs where the two disagreed, and no test read either string.
    The button's label is read off the live widget rather than written out
    here, so the two cannot drift apart again.

    ``open_pick_record_dialog`` is replaced in the screen's own module for the
    call, the way tests/test_vsp_tab_adds.py does it: no window opens, and the
    title is read from what the screen passed.
    """
    vps = make_vps(tmp_path)
    try:
        for cls, module in ((APEAssignmentScreen, quarter_mod),
                            (APEPeriodViewScreen, month_mod)):
            root, screen = _screen(cls, vps)
            try:
                label = _buttons(screen.left_actions)[0]
                captured = {}
                original = module.open_pick_record_dialog
                module.open_pick_record_dialog = \
                    lambda _parent, **kw: captured.update(kw)
                try:
                    screen.open_add_dialog()
                finally:
                    module.open_pick_record_dialog = original
                assert captured, f"{cls.__name__} opened no dialog"
                assert captured["title"].startswith(label), (
                    f"{cls.__name__}: the button says {label!r} and the "
                    f"dialog is titled {captured['title']!r}")
            finally:
                root.destroy()
    finally:
        vps.close()


def test_vtfm54_one_button_at_the_bottom(tmp_path):
    """VTF-M5.4 / VTF-M7.1 — APE Week Assignment's bottom row is one button.

    Edit Weekly Tactic opened the same editor as a double-click on the row and
    Delete Weekly called the same ``delete_weekly_row`` as the row's own
    Delete, so both were second routes to a control already on the row
    (VTF-M5.1, VTF-M5.2). Add Action Item created an Action Item this panel
    cannot display (VTF-M5.3); that button belongs to APE Week Actions, which
    has it. The header keeps Load, This Week and Refresh.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(WeeklyItemsScreen, vps)
        try:
            assert _buttons(_header(screen)) == ["Load", "This Week", "Refresh"]
            assert _buttons(screen.right_actions) == ["Add Weekly Tactic"], (
                "the bottom row is Add Weekly Tactic and nothing else")
        finally:
            root.destroy()
    finally:
        vps.close()


def test_vtfm35_week_actions_add_sits_at_the_bottom(tmp_path):
    """VTF-M3.5 / VTF-M7.1 — Add Action Item moved to the bottom, unchanged.

    The same button with the same command: only its parent and its row
    changed. The panel inherits Today's rows — 0 the toolbar, 1 the column
    header, 2 the scrolling list, which is the only weighted one — so row 3 is
    the bottom of the panel and not a row that floats above the list.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(WeekActionsScreen, vps)
        try:
            # The right panel is a TodayScreen subclass of its own, so the
            # toolbar and the bottom row belong to it, not to the tab.
            panel = screen.actions_panel
            assert _buttons(_header(screen)) == ["Load", "This Week"]
            assert _buttons(panel.toolbar_frame) == [], (
                "the toolbar must hold no button at all now")
            assert _buttons(panel.bottom_actions) == ["Add Action Item"]
            assert panel.add_button.master is panel.bottom_actions
            assert int(panel.bottom_actions.grid_info()["row"]) == 3, (
                "the bottom row must be below the scrolling list")
            assert panel.add_button.cget("command"), (
                "the moved button must still be wired to a command")
        finally:
            root.destroy()
    finally:
        vps.close()


# ---------------------------------------------------------------- VTF-M6 only

def test_vtfm61_the_new_buttons_sit_at_the_bottom(tmp_path):
    """VTF-M6.1 — the New button is below the list, and still relabels itself.

    One button, three labels, as it has always been: what moved is where it
    sits. Switching the view must still relabel it, which is the behaviour a
    move can silently break by re-creating the button after
    ``_set_active_view`` has run.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(VisionSegmentsScreen, vps)
        try:
            assert screen.primary_action_btn.master is screen.bottom_actions
            assert int(screen.bottom_actions.grid_info()["row"]) == 3, (
                "the New row must be under the list, which is row 2")
            assert int(screen.container.grid_rowconfigure(2)["weight"]) == 1, (
                "only the list row may grow, or the bottom row is not the bottom")

            for view, label in (("segments", "+ New Segment"),
                                ("subsegments", "+ New SubSegment"),
                                ("categories", "+ New Category")):
                screen._set_active_view(view)
                screen.update_idletasks()
                assert screen.primary_action_btn.cget("text") == label, view
        finally:
            root.destroy()
    finally:
        vps.close()


def test_vtfm62_the_switcher_and_refresh_do_not_move(tmp_path):
    """VTF-M6.2 — Refresh stays in the top row, the switcher stays on row 1.

    Refresh acts on the whole panel rather than on a record, so it is not an
    Add New and does not move with one.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(VisionSegmentsScreen, vps)
        try:
            top = screen.refresh_btn.master
            assert int(top.grid_info()["row"]) == 0, "Refresh left the top row"
            assert _buttons(top) == ["Refresh"]

            switcher = screen.view_buttons["segments"].master
            assert int(switcher.grid_info()["row"]) == 1, "the switcher moved"
            assert _buttons(switcher) == ["Segments", "SubSegments", "Categories"]
        finally:
            root.destroy()
    finally:
        vps.close()


# ---------------------------------- VTF-S8, VTF-S11: the second cold pass

def _command_of(frame, text):
    """The ``command`` of the one button under ``frame`` with this label."""
    for child in frame.winfo_children():
        if isinstance(child, ctk.CTkButton) and child.cget("text") == text:
            return child.cget("command")
    raise AssertionError(f"no button labelled {text!r} under {frame}")


def test_vtfs11_every_new_button_is_wired_to_its_handler(tmp_path):
    """VTF-S11 — the buttons this batch added and moved reach their methods.

    The batch's whole subject is buttons and not one assertion read a
    ``command``: every add test calls ``open_add_dialog`` or the write method
    directly on a stub, and the one command assertion in the suite tested
    truthiness, which a button wired to ``refresh`` would pass. Deleting
    ``command=self.open_add_dialog`` from all four tabs left the suite green.
    """
    vps = make_vps(tmp_path)
    try:
        seed_ape(vps, year=YEAR)
        for cls, label, attr, frame in (
                (AnnualVisionSegmentsScreen, "Add New Annual Plan Element",
                 "open_add_dialog", "right_actions"),
                # The two APE tabs keep the same command on the row they
                # moved to, under the left panel.
                (APEAssignmentScreen, "Add APE Quarter",
                 "open_add_dialog", "left_actions"),
                (APEPeriodViewScreen, "Add APE Month",
                 "open_add_dialog", "left_actions"),
                (WeeklyItemsScreen, "Add Weekly Tactic", "open_add_dialog",
                 "right_actions"),
        ):
            root, screen = _screen(cls, vps)
            try:
                assert _command_of(getattr(screen, frame), label) == getattr(
                    screen, attr), f"{cls.__name__}'s {label} is not wired"
            finally:
                root.destroy()

        # The two buttons that only moved must still carry the command they
        # had on the row they left.
        root, screen = _screen(VisionSegmentsScreen, vps)
        try:
            assert screen.primary_action_btn.cget("command") == \
                screen._run_primary_action
        finally:
            root.destroy()

        root, screen = _screen(WeekActionsScreen, vps)
        try:
            panel = screen.actions_panel
            assert _command_of(panel.bottom_actions, "Add Action Item") == \
                panel.add_action_item
        finally:
            root.destroy()
    finally:
        vps.close()


def test_vtfs8_the_annual_status_line_cannot_widen_its_column(tmp_path):
    """VTF-S8 — the one status line inside a panel column wraps.

    It is packed ``fill="x", expand=True`` into a frame gridded into the
    body's right column, and ``SplitPanel`` sets that column's width with
    ``grid_columnconfigure(minsize=...)``, which is a floor and not a ceiling.
    Without a wrap the first long sentence -- the refusals are over a hundred
    characters -- makes the column request its own width and pushes the panels
    off the body. The four sibling tabs put their status lines across the
    header, so this tab is the only one that needs it.
    """
    vps = make_vps(tmp_path)
    try:
        root, screen = _screen(AnnualVisionSegmentsScreen, vps)
        try:
            wrap = int(screen.status_label.cget("wraplength"))
            assert wrap > 0, "the status line must wrap, or it widens the column"

            long_refusal = screen._empty_add_message(YEAR)
            assert len(long_refusal) > 40, (
                "the sentence this label has to hold is a long one")
            screen.status_label.configure(text=long_refusal)
            screen.update_idletasks()
            assert screen.status_label.winfo_reqwidth() <= wrap + 40, (
                "the label asked for more width than its wrap allows")
        finally:
            root.destroy()
    finally:
        vps.close()
