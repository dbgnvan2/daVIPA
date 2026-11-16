"""LRP — one set of resize principles across every listing of action items.

Purpose: LRP-M1..M11 — the wrapped toolbar row is left-justified, the Project
         Board's right panel loses six buttons, all seven listings share one
         floor, one maximum and one default per column kind, and the value
         filters resize with their toolbar.
Spec:    docs/unused-docs/implementation_plan_2026-11-16_list_resize_principles.md
Tests:   this file

Withdrawn windows throughout: every assertion here reads grid options,
requested widths or ``cget``, none of which needs a mapped window, so the
``mapped_windows`` count in test_ci_contract.py is unchanged.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, ProjectBoard

# The buttons the user asked to be taken off the Project Board's right panel.
REMOVED_BUTTONS = (
    "Create Action Item",
    "Link Action Item",
    "Edit Project",
    "Create Note",
    "Link Note",
    "Open Notes",
)


def _app():
    app = MagicMock()
    app.vps_manager.get_segment_colors_by_id.return_value = {}
    app.vps_manager.get_segment_color_map.return_value = {}
    return app


def _root():
    root = ctk.CTk()
    root.withdraw()
    root.geometry("1400x800")
    return root


@pytest.fixture
def completed_screen(tmp_path):
    """A real CompletedScreen, for its toolbar wrap."""
    from src.getmoredone.screens.completed import CompletedScreen

    built = []

    def _make():
        root = _root()
        db = DatabaseManager(str(tmp_path / "completed.db"))
        item_id = db.create_action_item(ActionItem(
            who="Self", title="Write the quarterly summary",
            importance=3, urgency=3, size=3, value=3))
        db.complete_action_item(item_id)
        screen = CompletedScreen(root, db, _app())
        screen.pack(fill="both", expand=True)
        screen.update_idletasks()
        built.append((root, db))
        return screen

    yield _make
    for root, db in built:
        db.close()
        try:
            root.destroy()
        except Exception:
            pass


@pytest.fixture
def projects_screen(tmp_path):
    """A real ProjectBoardsScreen with a board selected, items optional."""
    from src.getmoredone.screens.project_boards import ProjectBoardsScreen

    built = []

    def _make(items=2):
        root = _root()
        db = DatabaseManager(str(tmp_path / "projects.db"))
        board_id = db.create_project_board(ProjectBoard(title="Board One"))
        for n in range(items):
            item_id = db.create_action_item(ActionItem(
                who="Self", title=f"Linked task {n}", status="open",
                start_date="2026-11-15", due_date="2026-11-20"))
            db.link_action_item_to_project_board(board_id, item_id)
        screen = ProjectBoardsScreen(root, db, SimpleNamespace(vps_manager=None))
        screen.pack(fill="both", expand=True)
        screen.selected_board_id = board_id
        screen.refresh()
        screen.update_idletasks()
        built.append((root, db))
        return screen

    yield _make
    for root, db in built:
        db.close()
        try:
            root.destroy()
        except Exception:
            pass


def _row_zero_toolbar(frame):
    """The frame gridded at row 0 of the right panel: its button toolbar."""
    for child in frame.winfo_children():
        info = child.grid_info()
        if info and int(info["row"]) == 0:
            return child
    raise AssertionError("no widget at row 0 of the items frame")


def _button_texts(toolbar):
    return [child.cget("text") for child in toolbar.winfo_children()
            if isinstance(child, ctk.CTkButton)]


def _label_texts(frame):
    return [child.cget("text") for child in frame.winfo_children()
            if isinstance(child, ctk.CTkLabel)]


# --------------------------------------------------------------------- LRP-M1
def test_lrpm1_the_wrapped_row_is_left_justified(completed_screen):
    """LRP-M1 — the wrap frame pins its left edge, not its right.

    ``sticky`` is what decides which way an over-wide second row overflows,
    and it is Tk's own record of the layout, not the source text.
    """
    screen = completed_screen()
    wrap = screen.toolbar_wrap
    wrap.fit(wrap.one_row_px() - 1)
    assert wrap.wrapped
    assert wrap.frame.grid_info()["sticky"] == "w"


def test_lrpm1_the_wrapped_controls_read_left_to_right(completed_screen):
    """LRP-M1 — inside the frame the controls keep their one-row order."""
    screen = completed_screen()
    wrap = screen.toolbar_wrap
    one_row_order = [int(info["column"]) for _w, info in wrap._wrap_candidates()]
    wrap.fit(wrap.one_row_px() - 1)
    wrapped = [(w, int(w.grid_info()["column"])) for w, _i in wrap._moved]
    assert [col for _w, col in wrapped] == list(range(len(wrapped)))
    assert one_row_order == sorted(one_row_order)


# --------------------------------------------------------------------- LRP-M2
def test_lrpm2_six_buttons_are_gone_from_the_right_panel(projects_screen):
    """LRP-M2 — the right panel's toolbar holds Bulk Edit and nothing removed."""
    screen = projects_screen()
    texts = _button_texts(_row_zero_toolbar(screen.items_frame))
    assert "Bulk Edit" in texts
    assert [t for t in texts if t in REMOVED_BUTTONS] == []


def test_lrpm2_the_removed_buttons_have_no_attributes_left(projects_screen):
    """LRP-M2 — nothing still holds a reference to a button that is gone."""
    screen = projects_screen()
    for name in ("btn_create_action", "btn_link_action", "btn_edit_project",
                 "btn_create_note", "btn_link_note", "btn_open_notes"):
        assert not hasattr(screen, name), name


# --------------------------------------------------------------------- LRP-M3
def test_lrpm3_the_empty_state_names_no_removed_button(projects_screen):
    """LRP-M3 — an empty board points at a route that still exists."""
    screen = projects_screen(items=0)
    texts = " ".join(_label_texts(screen.items_frame))
    assert "action item" in texts.lower()
    for removed in REMOVED_BUTTONS:
        assert removed not in texts, removed


def test_lrpm3_the_notes_empty_state_names_no_removed_button(projects_screen):
    """LRP-M3 — the notes section's empty state does the same."""
    screen = projects_screen(items=0)
    texts = " ".join(_label_texts(screen.notes_links_frame))
    for removed in REMOVED_BUTTONS:
        assert removed not in texts, removed
