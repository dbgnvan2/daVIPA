"""TB-M1 — the two columns a planned day needs, on fresh and upgrading databases.

Purpose: prove block_type and position exist in both halves of the schema (the
         CREATE TABLE and the migration), survive a round trip, and that a row
         written before the migration still reads.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m1
Tests:   this file

A planned day is an *order*, not a set of appointments, so `position` is the
load-bearing column: the clock times are derived from it. A migration that left
it off would not fail loudly — it would make every reorder a no-op.
"""

import sqlite3

import pytest

from src.getmoredone.database import Database
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import BlockType, TimeBlock

# The columns TB-M1 adds, with the definition the plan gives.
NEW_COLUMNS = {
    "block_type": ("TEXT", "'item'"),
    "position": ("INTEGER", "0"),
}

# time_blocks as it stood immediately before this feature, copied from
# database.py at commit 87ae093. A legacy database is built from this rather
# than by dropping columns off a current one, so the migration is exercised
# against the shape it will really meet on the user's machine.
LEGACY_TIME_BLOCKS = """
    CREATE TABLE time_blocks (
        id           TEXT PRIMARY KEY,
        item_id      TEXT,
        block_date   TEXT NOT NULL,
        start_time   TEXT NOT NULL,
        end_time     TEXT NOT NULL,
        planned_minutes INTEGER NOT NULL,
        label        TEXT,
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL
    )
"""


def _columns(conn, table) -> dict:
    """{name: (declared_type, default)} for one table."""
    return {
        row[1]: (row[2].upper(), row[4])
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _legacy_db(tmp_path):
    """A database file carrying the pre-TB-M1 time_blocks, with one block in it."""
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(LEGACY_TIME_BLOCKS)
    conn.execute(
        "INSERT INTO time_blocks (id, item_id, block_date, start_time, end_time,"
        " planned_minutes, label, created_at, updated_at) VALUES ('old-block', NULL,"
        " '2026-11-05', '09:00', '09:30', 30, 'Old block', '2026-01-01T00:00:00',"
        " '2026-01-01T00:00:00')"
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def manager(tmp_path):
    """Every DatabaseManager in this suite gets an explicit tmp_path database.

    The default path resolves to the user's real application database, and
    __init__ runs migrations against it.
    """
    db = DatabaseManager(str(tmp_path / "fresh.db"))
    yield db
    db.close()


def test_tbm11_migration_adds_columns_and_is_idempotent(tmp_path):
    """TB-M1.1 — the columns arrive on an upgrading DB, and re-running is harmless."""
    path = _legacy_db(tmp_path)

    db = Database(str(path))
    db.initialize_schema()
    try:
        columns = _columns(db.conn, "time_blocks")
        missing = set(NEW_COLUMNS) - set(columns)
        assert not missing, f"time_blocks is missing {sorted(missing)} after migration"

        # NOT NULL DEFAULT means SQLite back-fills the existing row itself.
        row = db.conn.execute(
            "SELECT block_type, position FROM time_blocks WHERE id = 'old-block'"
        ).fetchone()
        assert row[0] == "item", "a pre-TB-M1 block should migrate to an item block"
        assert row[1] == 0, (
            "position 0 is reserved for legacy rows; back-filling a real order "
            "would invent a sequence the user never chose"
        )

        db.initialize_schema()  # second run: must not raise "duplicate column name"
        assert set(NEW_COLUMNS) <= set(_columns(db.conn, "time_blocks"))
        assert db.conn.execute("SELECT COUNT(*) FROM time_blocks").fetchone()[0] == 1
    finally:
        db.close()


def test_tbm11a_create_table_alone_declares_both_columns(tmp_path, monkeypatch):
    """The plan requires each column in *both* the CREATE TABLE and the migration.

    Every other test here would pass with the CREATE TABLE half missing, because
    initialize_schema runs the migrations straight afterwards and they add the
    column to a brand-new database as readily as to an old one.

    So the migrations are switched off and the CREATE TABLE is made to stand on
    its own. Behavioural rather than a grep of the source: ALTER TABLE ADD
    COLUMN rewrites the CREATE TABLE text stored in sqlite_master, so that
    cannot be used for this either.
    """
    monkeypatch.setattr(Database, "_run_migrations", lambda self, conn: None)

    db = Database(str(tmp_path / "no_migrations.db"))
    db.initialize_schema()
    try:
        columns = _columns(db.conn, "time_blocks")
        for name, (declared_type, default) in NEW_COLUMNS.items():
            assert name in columns, (
                f"time_blocks.{name} comes only from the migration; a fresh "
                "database should get it from the CREATE TABLE"
            )
            assert columns[name][0] == declared_type, (
                f"time_blocks.{name} is {columns[name][0]}, plan says {declared_type}"
            )
            assert columns[name][1] == default, (
                f"time_blocks.{name} defaults to {columns[name][1]!r}, "
                f"plan says {default!r}"
            )
    finally:
        db.close()


def test_tbm12_block_type_and_position_round_trip(manager):
    """TB-M1.2 — a typed, positioned block comes back as it went in."""
    block = TimeBlock(
        block_date="2026-11-05",
        start_time="10:00",
        end_time="10:30",
        planned_minutes=30,
        label="Coffee",
        block_type=BlockType.BREAK,
        position=4,
    )
    manager.create_time_block(block)

    (stored,) = manager.get_time_blocks("2026-11-05")
    assert stored.block_type == BlockType.BREAK
    assert stored.position == 4
    assert stored.label == "Coffee"


def test_tbm12a_an_unrecognised_block_type_reads_as_an_item_block(manager):
    """A hand-edited type must not make the planner raise.

    Written against the database rather than BlockType.normalize directly: the
    normalize call could be dropped from the row converter and a unit test of
    the function alone would stay green.
    """
    block = TimeBlock(
        block_date="2026-11-05",
        start_time="10:00",
        end_time="10:30",
        planned_minutes=30,
    )
    manager.create_time_block(block)
    manager.db.conn.execute(
        "UPDATE time_blocks SET block_type = 'sabbatical' WHERE id = ?", (block.id,)
    )
    manager.db.conn.commit()

    (stored,) = manager.get_time_blocks("2026-11-05")
    assert stored.block_type == BlockType.ITEM


def test_tbm13_pre_migration_row_reads_with_defaults(tmp_path):
    """TB-M1.3 — dirty state (P8): a row from before the migration still reads.

    The row converter indexes columns by name off a ``SELECT *``. A query that
    does not project the new columns, or a row selected from a database the
    migration has not reached, is the shape that raises. Here the read is forced
    down the defensive path by selecting without those columns.
    """
    path = _legacy_db(tmp_path)
    manager = DatabaseManager(str(path))
    try:
        row = manager.db.conn.execute(
            "SELECT id, item_id, block_date, start_time, end_time, planned_minutes,"
            " label, created_at, updated_at FROM time_blocks WHERE id = 'old-block'"
        ).fetchone()

        block = manager._row_to_time_block(row)
        assert block.block_type == BlockType.ITEM
        assert block.position == 0
        assert block.planned_minutes == 30
    finally:
        manager.close()


def test_tbm13a_a_legacy_day_still_reads_in_clock_order(tmp_path):
    """Position 0 on every legacy row must not scramble a migrated day.

    get_time_blocks orders by (position, start_time); with every legacy block at
    position 0 the second key is the only thing keeping an upgraded day in the
    order the user left it in. Dropping `start_time` from that ORDER BY has to
    fail here.
    """
    path = tmp_path / "legacy_day.db"
    conn = sqlite3.connect(path)
    conn.execute(LEGACY_TIME_BLOCKS)
    # Inserted deliberately out of clock order, so row order cannot stand in
    # for the sort being correct.
    for block_id, start, end in (
        ("c", "15:00", "15:30"),
        ("a", "09:00", "09:30"),
        ("b", "11:00", "11:30"),
    ):
        conn.execute(
            "INSERT INTO time_blocks (id, item_id, block_date, start_time, end_time,"
            " planned_minutes, label, created_at, updated_at)"
            f" VALUES ('{block_id}', NULL, '2026-11-05', '{start}', '{end}', 30, NULL,"
            " '2026-01-01T00:00:00', '2026-01-01T00:00:00')"
        )
    conn.commit()
    conn.close()

    manager = DatabaseManager(str(path))
    try:
        assert [b.id for b in manager.get_time_blocks("2026-11-05")] == ["a", "b", "c"]
    finally:
        manager.close()
