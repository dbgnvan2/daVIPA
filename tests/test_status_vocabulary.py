"""Two status vocabularies, kept apart on purpose, with the board gaining
'canceled'.

Spec: docs/spec_2026-11-16_status_vocabulary.md

SVU-M1  a project board is active/pending/canceled/completed; an action item
        stays open/completed/canceled, and the two lists are the only source
SVU-M2  an existing database's board CHECK constraint is widened on open
"""

import logging
import sqlite3

import pytest

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import (
    ActionItem, ProjectBoard, ProjectBoardStatus, Status)
from src.getmoredone.validation import Validator


# --------------------------------------------------------------------- SVU-M1

def test_svum1_board_vocabulary_is_the_four_words():
    assert ProjectBoardStatus.ALL == (
        "active", "pending", "canceled", "completed")


def test_svum1_item_vocabulary_is_unchanged():
    """The four words are the *project's*. An item has no 'pending'."""
    assert Status.ALL == ("open", "completed", "canceled")
    assert not hasattr(Status, "PENDING")
    assert not hasattr(Status, "ACTIVE")


def test_svum1_the_two_vocabularies_are_not_the_same():
    assert set(Status.ALL) != set(ProjectBoardStatus.ALL)


def test_svum1_a_new_item_is_open():
    assert ActionItem(who="me", title="T").status == Status.OPEN


def test_svum1_the_default_filter_is_open_alone():
    assert Status.DEFAULT_VISIBLE == (Status.OPEN,)


def test_svum1_validator_accepts_every_item_status():
    for status in Status.ALL:
        item = ActionItem(who="me", title="T", status=status)
        assert Validator.validate_action_item(item) == [], status


def test_svum1_validator_rejects_a_board_only_status_on_an_item():
    """'pending' and 'active' are project words; an item must not take them."""
    for status in ("active", "pending"):
        errors = Validator.validate_action_item(
            ActionItem(who="me", title="T", status=status))
        assert [e.field for e in errors] == ["status"], (status, errors)


# --------------------------------------------------------------------- SVU-M2

LEGACY_BOARD_CHECK = (
    "status TEXT NOT NULL DEFAULT 'active' "
    "CHECK(status IN ('active', 'pending', 'completed'))"
)

#: Every non-status column ``initialize_schema`` expects on the table. The
#: index creation that runs after the migration reads
#: ``annual_plan_element_id``, so a cut-down table fails there rather than in
#: the code under test.
BOARD_COLUMNS = (
    "id TEXT PRIMARY KEY, title TEXT NOT NULL, "
    "annual_plan_element_id TEXT, importance INTEGER, "
    "next_step TEXT, notes TEXT, display_order INTEGER, "
    "savor_count INTEGER NOT NULL DEFAULT 0"
)


def _legacy_db(path):
    """A database carrying the pre-SVU board constraint."""
    with sqlite3.connect(path) as conn:
        conn.execute(f"""
            CREATE TABLE project_boards (
                {BOARD_COLUMNS},
                {LEGACY_BOARD_CHECK},
                completed_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE project_board_links (
                id TEXT PRIMARY KEY, project_board_id TEXT NOT NULL,
                label TEXT, url TEXT NOT NULL, link_type TEXT DEFAULT 'url',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO project_boards (id, title, status, created_at, "
            "updated_at) VALUES ('b1', 'B', 'active', '2020-01-01', "
            "'2020-01-01')")
        conn.execute(
            "INSERT INTO project_board_links (id, project_board_id, url, "
            "status, created_at) VALUES ('n1', 'b1', 'note://x', 'open', "
            "'2020-01-01')")
        conn.commit()
    return str(path)


def test_svum2_board_check_accepts_canceled(tmp_path):
    """The old CHECK rejected 'canceled'; after the rebuild it does not."""
    db_path = _legacy_db(tmp_path / "legacy_check.db")

    with sqlite3.connect(db_path) as probe:
        with pytest.raises(sqlite3.IntegrityError):
            probe.execute(
                "INSERT INTO project_boards (id, title, status, created_at, "
                "updated_at) VALUES ('b0', 'X', 'canceled', 'd', 'd')")

    manager = DatabaseManager(db_path)
    try:
        manager.db.conn.execute(
            "INSERT INTO project_boards (id, title, status, created_at, "
            "updated_at) VALUES ('b2', 'Y', 'canceled', 'd', 'd')")
        manager.db.conn.commit()
        row = manager.db.conn.execute(
            "SELECT status FROM project_boards WHERE id = 'b2'").fetchone()
        assert row["status"] == ProjectBoardStatus.CANCELED
    finally:
        manager.close()


def test_svum2_rebuild_keeps_existing_boards(tmp_path):
    """P2 -- the rebuild copies every row, it does not start a fresh table."""
    db_path = _legacy_db(tmp_path / "legacy_rows.db")
    manager = DatabaseManager(db_path)
    try:
        row = manager.db.conn.execute(
            "SELECT title, status FROM project_boards WHERE id = 'b1'"
        ).fetchone()
        assert (row["title"], row["status"]) == ("B", "active")
    finally:
        manager.close()


def test_svum2_rebuild_leaves_item_status_alone(tmp_path):
    """SVU-M1 renamed nothing: an 'open' note is still 'open' afterwards."""
    db_path = _legacy_db(tmp_path / "legacy_notes.db")
    manager = DatabaseManager(db_path)
    try:
        row = manager.db.conn.execute(
            "SELECT status FROM project_board_links WHERE id = 'n1'"
        ).fetchone()
        assert row["status"] == Status.OPEN
    finally:
        manager.close()


def test_svum2_rebuild_keeps_the_notes_linked_to_a_board(tmp_path):
    """Foreign keys are off for the rebuild, so the cascade must not fire."""
    db_path = _legacy_db(tmp_path / "legacy_cascade.db")
    manager = DatabaseManager(db_path)
    try:
        count = manager.db.conn.execute(
            "SELECT COUNT(*) AS n FROM project_board_links "
            "WHERE project_board_id = 'b1'").fetchone()["n"]
        assert count == 1
    finally:
        manager.close()


def test_svum2_rebuild_leaves_the_board_indexes_in_place(tmp_path):
    """DROP TABLE takes the table's indexes with it.

    They come back because ``_run_migrations`` runs *before* the
    ``CREATE INDEX IF NOT EXISTS`` statements in ``initialize_schema``, which
    is an ordering this guard pins: move the rebuild below them and a migrated
    database loses both indexes silently.
    """
    db_path = _legacy_db(tmp_path / "legacy_indexes.db")
    manager = DatabaseManager(db_path)
    try:
        names = {row[0] for row in manager.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' "
            "AND tbl_name = 'project_boards'").fetchall()}
        assert {"idx_project_boards_status",
                "idx_project_boards_ape"} <= names, names
    finally:
        manager.close()


def test_svum2_foreign_keys_are_on_again_after_the_rebuild(tmp_path):
    db_path = _legacy_db(tmp_path / "legacy_fk.db")
    manager = DatabaseManager(db_path)
    try:
        assert manager.db.conn.execute(
            "PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        manager.close()


class _FailOnDrop:
    """A connection proxy that raises on ``DROP TABLE`` and nothing else.

    The rebuild's own `DROP TABLE` is hard to make fail from outside, and the
    failure has to land *after* the `INSERT` has opened a transaction -- which
    is the whole point of the guard below.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, *args):
        if sql.strip().upper().startswith("DROP TABLE"):
            raise sqlite3.OperationalError("injected failure")
        return self._conn.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def test_svum2_a_failed_rebuild_leaves_foreign_keys_on(tmp_path):
    """`PRAGMA foreign_keys` is ignored while a transaction is open.

    So a rebuild that raises after the copy must roll back before restoring
    it, or enforcement stays OFF for the life of the connection and the next
    board delete orphans its items and notes instead of cascading them.
    """
    db_path = _legacy_db(tmp_path / "legacy_failed.db")
    manager = DatabaseManager(db_path)
    try:
        conn = manager.db.conn
        # Put the old constraint back so the rebuild runs a second time.
        conn.execute("DROP TABLE project_boards")
        conn.execute(f"""
            CREATE TABLE project_boards (
                {BOARD_COLUMNS},
                {LEGACY_BOARD_CHECK},
                completed_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO project_boards (id, title, status, created_at, "
            "updated_at) VALUES ('b9', 'B', 'active', 'd', 'd')")
        conn.commit()

        with pytest.raises(sqlite3.OperationalError):
            manager.db._widen_board_status_check(_FailOnDrop(conn))

        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        manager.close()


def test_svum2_a_check_less_table_is_left_alone_without_warning(tmp_path, caplog):
    """An older database added `status` by ALTER TABLE, so it has no CHECK.

    There is nothing to widen and 'canceled' already stores, so this must not
    log a warning on every launch for the rest of the database's life.
    """
    db_path = str(tmp_path / "no_check.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"""
            CREATE TABLE project_boards (
                {BOARD_COLUMNS},
                status TEXT NOT NULL DEFAULT 'active',
                completed_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

    with caplog.at_level(logging.DEBUG, logger="src.getmoredone.database"):
        manager = DatabaseManager(db_path)
    try:
        # Both halves, because the negative one alone passes with the whole
        # method stubbed out -- it pins no branch at all.
        assert any("no status CHECK" in record.message
                   for record in caplog.records
                   if record.levelno == logging.DEBUG), caplog.text
        assert not [record for record in caplog.records
                    if record.levelno >= logging.WARNING
                    and "SVU-M2" in record.message], caplog.text
        manager.db.conn.execute(
            "INSERT INTO project_boards (id, title, status, created_at, "
            "updated_at) VALUES ('b3', 'Z', 'canceled', 'd', 'd')")
        manager.db.conn.commit()
    finally:
        manager.close()


def test_svum2_migration_is_idempotent(tmp_path):
    """A second open rewrites nothing and leaves the same schema behind."""
    db_path = _legacy_db(tmp_path / "legacy_twice.db")
    first = DatabaseManager(db_path)
    schema_after_first = first.db.conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
    ).fetchone()[0]
    first.close()

    second = DatabaseManager(db_path)
    try:
        schema_after_second = second.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
        ).fetchone()[0]
        assert schema_after_second == schema_after_first
        assert "'canceled'" in schema_after_second
        assert second.db.conn.execute(
            "SELECT COUNT(*) AS n FROM project_boards").fetchone()["n"] == 1
    finally:
        second.close()


def test_svum2_a_fresh_database_already_allows_canceled(tmp_path):
    """The CREATE TABLE carries the new CHECK, so no rebuild is needed."""
    manager = DatabaseManager(str(tmp_path / "fresh.db"))
    try:
        sql = manager.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
        ).fetchone()[0]
        assert "'canceled'" in sql, sql
    finally:
        manager.close()


def test_svum2_a_leftover_scratch_table_does_not_block_the_next_launch(tmp_path):
    """The rebuild is re-entrant, so one transient failure is not permanent.

    `CREATE TABLE` is DDL in autocommit and the rollback cannot undo it, so a
    rebuild that raised after it leaves `project_boards_svu` on disk. SQLite
    stores a CREATE with `IF NOT EXISTS` stripped, so without the pre-CREATE
    drop the next launch raises "table project_boards_svu already exists" out
    of `DatabaseManager.__init__` -- a database that can never be opened again.
    """
    db_path = _legacy_db(tmp_path / "legacy_debris.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"CREATE TABLE project_boards_svu ({BOARD_COLUMNS}, "
                     f"status TEXT, completed_at TEXT, created_at TEXT, "
                     f"updated_at TEXT)")
        conn.commit()

    manager = DatabaseManager(db_path)
    try:
        schema = manager.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
        ).fetchone()[0]
        assert "'canceled'" in schema, schema
        assert manager.db.conn.execute(
            "SELECT COUNT(*) AS n FROM project_boards").fetchone()["n"] == 1
    finally:
        manager.close()


def test_svum2_a_deferred_commit_connection_is_refused(tmp_path, caplog):
    """The rebuild rests on a commit it does not own.

    `PRAGMA foreign_keys = OFF` is ignored while a transaction is open, and
    inside `DatabaseManager.transaction()` the commit that closes one is a
    no-op. Rebuilding anyway would leave enforcement ON and let `DROP TABLE
    project_boards` cascade every item and note away.
    """
    db_path = _legacy_db(tmp_path / "legacy_deferred.db")
    manager = DatabaseManager(db_path)
    try:
        conn = manager.db.conn
        # Put the old constraint back so there is work to refuse.
        conn.execute("DROP TABLE project_boards")
        conn.execute(f"""
            CREATE TABLE project_boards (
                {BOARD_COLUMNS},
                {LEGACY_BOARD_CHECK},
                completed_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

        conn.defer_commits()
        try:
            with caplog.at_level(logging.WARNING):
                manager.db._widen_board_status_check(conn)
        finally:
            conn.resume_commits()

        schema = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
        ).fetchone()[0]
        assert "'canceled'" not in schema, schema
        assert "commits are deferred" in caplog.text, caplog.text
    finally:
        manager.close()


def test_svum2_a_comment_mentioning_canceled_does_not_skip_the_rebuild(tmp_path):
    """The decision comes from the matched CHECK, not the whole schema text."""
    db_path = str(tmp_path / "commented.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"""
            CREATE TABLE project_boards (
                {BOARD_COLUMNS},
                -- a project is never 'canceled' here yet
                {LEGACY_BOARD_CHECK},
                completed_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

    manager = DatabaseManager(db_path)
    try:
        schema = manager.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
        ).fetchone()[0]
        assert "'canceled'" in schema.split("CHECK", 1)[1], schema
        manager.db.conn.execute(
            "INSERT INTO project_boards (id, title, status, created_at, "
            "updated_at) VALUES ('b4', 'C', 'canceled', 'd', 'd')")
        manager.db.conn.commit()
        assert manager.db.conn.execute(
            "SELECT status FROM project_boards WHERE id = 'b4'"
        ).fetchone()["status"] == ProjectBoardStatus.CANCELED
    finally:
        manager.close()


def test_svum2_a_lowercase_check_is_widened_too(tmp_path):
    """SQL keywords are case-insensitive, so the pattern must be."""
    db_path = str(tmp_path / "lowercase.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"""
            CREATE TABLE project_boards (
                {BOARD_COLUMNS},
                status TEXT NOT NULL DEFAULT 'active'
                    check(status in ('active', 'pending', 'completed')),
                completed_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        conn.commit()

    manager = DatabaseManager(db_path)
    try:
        schema = manager.db.conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'project_boards'"
        ).fetchone()[0]
        assert "'canceled'" in schema, schema
        manager.db.conn.execute(
            "INSERT INTO project_boards (id, title, status, created_at, "
            "updated_at) VALUES ('b5', 'D', 'canceled', 'd', 'd')")
        manager.db.conn.commit()
        assert manager.db.conn.execute(
            "SELECT status FROM project_boards WHERE id = 'b5'"
        ).fetchone()["status"] == ProjectBoardStatus.CANCELED
    finally:
        manager.close()


# --------------------------------------------------------------------- SVU-M3

def _board(manager, title="P"):
    board = ProjectBoard(title=title)
    manager.create_project_board(board)
    return board.id


def test_svum3_every_board_status_can_be_set(tmp_path):
    """The gate read a hand-written set, so it rejected `canceled` silently."""
    manager = DatabaseManager(str(tmp_path / "setstatus.db"))
    try:
        board_id = _board(manager)
        for status in ProjectBoardStatus.ALL:
            assert manager.set_project_board_status(board_id, status) is True, status
            assert manager.get_project_board(board_id).status == status
    finally:
        manager.close()


def test_svum3_an_unknown_board_status_is_refused(tmp_path):
    manager = DatabaseManager(str(tmp_path / "badstatus.db"))
    try:
        board_id = _board(manager)
        assert manager.set_project_board_status(board_id, "open") is False
        assert manager.get_project_board(board_id).status == (
            ProjectBoardStatus.ACTIVE)
    finally:
        manager.close()


def test_svum3_a_canceled_board_is_hidden_but_reachable(tmp_path):
    """Canceling a project must not put it beyond the UI's reach.

    `get_project_boards` could only ever return active, pending and completed,
    so a project canceled in the editor left the Projects screen and no
    setting brought it back.
    """
    manager = DatabaseManager(str(tmp_path / "canceled_board.db"))
    try:
        board_id = _board(manager, "Dropped")
        manager.set_project_board_status(board_id, ProjectBoardStatus.CANCELED)

        default = [row["id"] for row in manager.get_project_boards()]
        assert board_id not in default

        shown = [row["id"] for row in
                 manager.get_project_boards(show_canceled=True)]
        assert board_id in shown
    finally:
        manager.close()

