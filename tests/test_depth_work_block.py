"""Depth and Work Block — schema, persistence, and UI presence.

Two new advisory scheduling hints on an action item:
- ``depth`` (TEXT) — "Deep" | "Medium" | "Shallow"
- ``work_block`` (INTEGER) — minutes, 90 | 60 | 30

Prove the columns land on a fresh database *and* on a legacy one, that every
field survives a round trip, that the Priority tab carries the controls plus a
calendar button, and that the Action Plan block mirrors the chosen values.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.getmoredone.database import Database
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, ProjectBoard, SchedulingOptions
from src.getmoredone.screens.item_editor import ItemEditorDialog
from tests.weekly_tactic_fixtures import make_vps

# The action_items schema as it stood immediately before this feature, so the
# migration is exercised against the shape it will really meet in the wild.
LEGACY_ACTION_ITEMS = """
    CREATE TABLE action_items (
        id TEXT PRIMARY KEY, who TEXT, contact_id INTEGER, parent_id TEXT,
        title TEXT NOT NULL, description TEXT, next_action TEXT,
        start_date TEXT, due_date TEXT, original_due_date TEXT,
        is_meeting INTEGER DEFAULT 0, meeting_start_time TEXT,
        importance INTEGER, urgency INTEGER, size INTEGER, value INTEGER,
        priority_score INTEGER NOT NULL DEFAULT 0,
        "group" TEXT, category TEXT, planned_minutes INTEGER,
        deliverable TEXT,
        status TEXT NOT NULL DEFAULT 'open', completed_at TEXT,
        item_type TEXT NOT NULL DEFAULT 'daily', annual_plan_element_id TEXT,
        today_pin_rank INTEGER,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )
"""


def _columns(conn, table) -> dict:
    return {
        row[1]: row[2].upper()
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _legacy_db(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(LEGACY_ACTION_ITEMS)
    conn.execute(
        "INSERT INTO action_items (id, who, title, priority_score, status,"
        " item_type, created_at, updated_at) VALUES ('old-item', 'me', 'Old',"
        " 0, 'open', 'daily', '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def manager(tmp_path):
    db = DatabaseManager(str(tmp_path / "fresh.db"))
    yield db
    db.close()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_defaults.return_value = None
    db.get_all_contacts.return_value = []
    db.get_distinct_groups.return_value = []
    db.get_distinct_categories.return_value = []
    db.get_item_links.return_value = []
    db.get_action_item.return_value = ActionItem(
        id="test-item", who="Self", title="Test Item")
    db.get_project_board_ids_for_item.return_value = []
    db.get_project_boards.return_value = []
    db.get_project_board.return_value = ProjectBoard(
        id="test-board", title="Test Board", status="active")
    return db


@pytest.fixture
def root():
    window = ctk.CTk()
    window.withdraw()
    yield window
    window.destroy()


# --- schema ----------------------------------------------------------------


def test_fresh_db_has_depth_and_work_block_columns(manager):
    """Both columns, with their spec types, exist on a brand-new database."""
    columns = _columns(manager.db.conn, "action_items")
    assert columns.get("depth") == "TEXT", "depth missing or wrong type on a fresh DB"
    assert columns.get("work_block") == "INTEGER", "work_block missing or wrong type on a fresh DB"


def test_migration_adds_both_columns_to_a_legacy_db_and_is_idempotent(tmp_path):
    """The columns arrive on an upgrading DB, and re-running is harmless."""
    path = _legacy_db(tmp_path)
    db = Database(str(path))
    db.initialize_schema()

    assert "depth" in _columns(db.conn, "action_items")
    assert "work_block" in _columns(db.conn, "action_items")
    # An existing row gets NULL, not a fabricated hint.
    row = db.conn.execute(
        "SELECT depth, work_block FROM action_items WHERE id = 'old-item'"
    ).fetchone()
    assert row["depth"] is None
    assert row["work_block"] is None

    db.initialize_schema()  # second run: must not raise "duplicate column name"
    assert db.conn.execute("SELECT COUNT(*) FROM action_items").fetchone()[0] == 1
    db.close()


# --- persistence -----------------------------------------------------------


def test_depth_and_work_block_round_trip_on_create_and_update(manager):
    """Both write paths carry the fields; a create-only fix would look identical."""
    item = ActionItem(who="me", title="Deep work", depth="Deep", work_block=90)
    manager.create_action_item(item)
    reloaded = manager.get_action_item(item.id)
    assert reloaded.depth == "Deep"
    assert reloaded.work_block == 90

    reloaded.depth = "Shallow"
    reloaded.work_block = 30
    manager.update_action_item(reloaded)
    assert manager.get_action_item(item.id).depth == "Shallow"
    assert manager.get_action_item(item.id).work_block == 30

    reloaded.depth = None
    reloaded.work_block = None
    manager.update_action_item(reloaded)
    assert manager.get_action_item(item.id).depth is None, "clearing depth must clear it"
    assert manager.get_action_item(item.id).work_block is None, "clearing work_block must clear it"


def test_depth_and_work_block_from_form_reach_the_saved_item(tmp_path, root):
    """The Priority-tab controls' values arrive in the database row."""
    vps = make_vps(tmp_path)
    try:
        manager = vps.db_manager
        dialog = ItemEditorDialog(root, manager, vps_manager=vps)
        dialog.who_var.set("Self")
        dialog.title_entry.insert(0, "Scheduled task")
        dialog.depth_var.set("Deep")
        dialog.work_block_var.set("90 min")

        assert dialog.save_item() is True, dialog.error_label.cget("text")

        stored = manager.db.conn.execute(
            "SELECT depth, work_block FROM action_items WHERE title = 'Scheduled task'"
        ).fetchone()
        assert stored["depth"] == "Deep"
        assert stored["work_block"] == 90
    finally:
        vps.close()


def test_blank_depth_and_work_block_are_stored_as_null(tmp_path, root):
    """Untouched controls mean "no hint", not a hint of "" or 0."""
    vps = make_vps(tmp_path)
    try:
        manager = vps.db_manager
        dialog = ItemEditorDialog(root, manager, vps_manager=vps)
        dialog.who_var.set("Self")
        dialog.title_entry.insert(0, "Unsized task")
        # leave depth/work_block blank (their defaults)

        assert dialog.save_item() is True, dialog.error_label.cget("text")

        stored = manager.db.conn.execute(
            "SELECT depth, work_block FROM action_items WHERE title = 'Unsized task'"
        ).fetchone()
        assert stored["depth"] is None
        assert stored["work_block"] is None
    finally:
        vps.close()


# --- UI presence -----------------------------------------------------------


def test_priority_tab_holds_depth_work_block_and_calendar_button(root, mock_db):
    """The controls live on the Priority tab, below the priority factors."""
    dialog = ItemEditorDialog(root, mock_db, item_id="test-item")

    assert dialog.depth_combo.master is dialog.tab_priority
    assert dialog.work_block_combo.master is dialog.tab_priority
    assert dialog.btn_schedule_calendar.master is dialog.tab_priority

    depth_values = dialog.depth_combo.cget("values")
    assert set(depth_values) == set(SchedulingOptions.DEPTH)
    assert set(dialog.work_block_combo.cget("values")) == {"90 min", "60 min", "30 min"}
    assert dialog.btn_schedule_calendar.cget("text") == "📅 Schedule on Calendar"


def test_action_plan_block_echoes_depth_and_work_block(root, mock_db):
    """The Action Plan block mirrors the Priority tab's two values."""
    dialog = ItemEditorDialog(root, mock_db, item_id="test-item")

    assert dialog.depth_label.master is dialog.action_plan_frame
    assert dialog.work_block_label.master is dialog.action_plan_frame

    # Unset: explicit "(none)" placeholders, not blank.
    assert dialog.depth_label.cget("text") == "(none)"
    assert dialog.work_block_label.cget("text") == "(none)"

    dialog.depth_var.set("Medium")
    dialog.work_block_var.set("60 min")
    dialog._refresh_scheduling_display()
    assert dialog.depth_label.cget("text") == "Medium"
    assert dialog.work_block_label.cget("text") == "60 min"


# --- calendar duration pre-fill --------------------------------------------


def test_calendar_dialog_prefills_duration_from_work_block(root, mock_db):
    """The event Duration starts at the chosen Work Block, not the default."""
    from src.getmoredone.screens.calendar_dialog import CalendarEventDialog

    dialog = CalendarEventDialog(root, mock_db, "test-item", default_duration_minutes=90)
    try:
        assert dialog.duration_entry.get() == "90"
    finally:
        dialog.destroy()


def test_calendar_dialog_defaults_duration_to_60_without_work_block(root, mock_db):
    """No Work Block means the dialog's existing 60-minute default."""
    from src.getmoredone.screens.calendar_dialog import CalendarEventDialog

    dialog = CalendarEventDialog(root, mock_db, "test-item")
    try:
        assert dialog.duration_entry.get() == "60"
    finally:
        dialog.destroy()


def test_create_calendar_event_passes_work_block_as_default_duration(tmp_path, root, monkeypatch):
    """The Priority tab's button hands the current Work Block to the dialog.

    The combo value is read (not the stored row), so an unsaved choice is
    honoured. Monkeypatching the dialog the module actually imports from —
    ``create_calendar_event`` imports it inside the function (see
    test_item_editor_missing_row.py for why the patch target matters).
    """
    vps = make_vps(tmp_path)
    try:
        manager = vps.db_manager
        item = ActionItem(who="Self", title="Blocked task")
        manager.create_action_item(item)

        dialog = ItemEditorDialog(root, manager, vps_manager=vps, item_id=item.id)
        dialog.work_block_var.set("90 min")

        captured = {}
        import src.getmoredone.screens.calendar_dialog as cd
        original = cd.CalendarEventDialog

        class FakeDialog:
            def __init__(self, parent, db, iid, default_duration_minutes=None):
                self.result = None
                captured["default_duration_minutes"] = default_duration_minutes

            def wait_window(self):
                pass

        cd.CalendarEventDialog = FakeDialog
        try:
            dialog.create_calendar_event()
        finally:
            cd.CalendarEventDialog = original

        assert captured.get("default_duration_minutes") == 90
    finally:
        vps.close()


def test_create_calendar_event_passes_none_without_work_block(tmp_path, root, monkeypatch):
    """No Work Block set → the dialog gets None, so it keeps its own default."""
    vps = make_vps(tmp_path)
    try:
        manager = vps.db_manager
        item = ActionItem(who="Self", title="Unblocked task")
        manager.create_action_item(item)

        dialog = ItemEditorDialog(root, manager, vps_manager=vps, item_id=item.id)

        captured = {}
        import src.getmoredone.screens.calendar_dialog as cd
        original = cd.CalendarEventDialog

        class FakeDialog:
            def __init__(self, parent, db, iid, default_duration_minutes=None):
                self.result = None
                captured["default_duration_minutes"] = default_duration_minutes

            def wait_window(self):
                pass

        cd.CalendarEventDialog = FakeDialog
        try:
            dialog.create_calendar_event()
        finally:
            cd.CalendarEventDialog = original

        assert captured.get("default_duration_minutes") is None
    finally:
        vps.close()
