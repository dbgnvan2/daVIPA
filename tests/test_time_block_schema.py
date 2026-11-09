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
    # TG-M4. Nullable with no default on purpose: NULL means "never placed on
    # the grid", which is a different fact from "the first box of the day".
    "slot_index": ("INTEGER", None),
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

    get_time_blocks orders by (slot_index, position, start_time). A legacy day
    has no box on any row, so the first key cannot separate them and every
    legacy block sits at position 0 -- which leaves `start_time` as the only
    thing keeping an upgraded day in the order the user left it in. Dropping it
    from that ORDER BY has to fail here.
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


# --- TG-M4 / TG-M5: the grid column, and the days already stored -------------


def _bounds():
    from src.getmoredone.time_block_layout import DayBounds

    return DayBounds()


def test_tgm41_migration_adds_slot_index_idempotently(tmp_path):
    """TG-M4.1 — the column arrives on an upgrading database, and once only.

    Built from the pre-feature CREATE TABLE rather than by dropping a column
    off a current one, so the migration meets the shape it will really find.
    """
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(path))
    conn.execute(LEGACY_TIME_BLOCKS)
    conn.commit()
    conn.close()

    for _ in range(2):
        db = Database(str(path))
        db.initialize_schema()
        db.close()

    conn = sqlite3.connect(str(path))
    columns = [row[1] for row in conn.execute("PRAGMA table_info(time_blocks)")]
    conn.close()

    assert columns.count("slot_index") == 1


def test_a_fresh_database_has_slot_index_too(tmp_path):
    """The CREATE TABLE half. A column added only by the migration would be
    missing on every new install, and present on every upgraded one -- the
    kind of split this file exists to prevent."""
    db = Database(str(tmp_path / "fresh.db"))
    db.initialize_schema()
    columns = [
        row[1] for row in db.conn.execute("PRAGMA table_info(time_blocks)")
    ]
    db.close()

    assert "slot_index" in columns


def test_slot_index_is_nullable_so_never_placed_is_representable(tmp_path):
    """NOT NULL DEFAULT 0 would have made every unplaced block sit at 08:00.

    Asserted against the schema rather than the behaviour, because the whole
    point is what the column *permits*.
    """
    db = Database(str(tmp_path / "fresh.db"))
    db.initialize_schema()
    row = [
        r for r in db.conn.execute("PRAGMA table_info(time_blocks)")
        if r[1] == "slot_index"
    ][0]
    db.close()

    notnull, default = row[3], row[4]
    assert notnull == 0, "slot_index must be nullable"
    assert default is None, "a default would turn 'never placed' into 'box 0'"


def test_the_day_is_indexed_by_box(tmp_path):
    """Every read of a day is ``ORDER BY slot_index, position``.

    Asserted off ``PRAGMA index_info`` rather than the source text, so it is
    the database's own answer about the index it actually has. The older
    ``(block_date, position)`` index is kept and is not this one: a day read in
    box order against an index that does not mention the box is a sort on every
    load.
    """
    db = Database(str(tmp_path / "fresh.db"))
    db.initialize_schema()
    names = [
        row[1] for row in db.conn.execute("PRAGMA index_list(time_blocks)")
    ]
    assert "idx_blocks_date_slot" in names, f"indexes were {names}"
    columns = [
        row[2]
        for row in db.conn.execute("PRAGMA index_info(idx_blocks_date_slot)")
    ]
    db.close()

    assert columns == ["block_date", "slot_index", "position"]


def test_tgm51_existing_times_map_to_slots(tmp_path):
    """TG-M5.1 — a day stored by the old model lands on the right boxes.

    09:30 under an 08:00 Day Start is box 3. Asserted through the manager so
    the derived times are checked too: a block adopted onto the right box but
    left holding its old string would read correctly and sort wrongly.
    """
    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        manager.db.conn.execute(
            """
            INSERT INTO time_blocks (id, item_id, block_date, start_time,
                end_time, planned_minutes, label, block_type, position,
                created_at, updated_at)
            VALUES ('b1', NULL, '2026-11-05', '09:30', '10:00', 30, 'legacy',
                'item', 1, '2026-11-05', '2026-11-05')
            """
        )
        manager.db.conn.commit()

        adopted = manager.adopt_legacy_day("2026-11-05", _bounds())

        assert adopted == ["b1"]
        block = manager.get_time_blocks("2026-11-05")[0]
        assert block.slot_index == 3
        assert (block.start_time, block.end_time) == ("09:30", "10:00")
    finally:
        manager.close()


def test_tgm52_a_timeless_row_migrates_by_position(tmp_path):
    """TG-M5.2 — **dirty state (P8)**: the old model could store no time.

    A row written between a create and its repack has an empty start_time.
    There is no time to map, so it takes the first box that will hold it
    rather than being dropped or given an invented hour.
    """
    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        manager.db.conn.execute(
            """
            INSERT INTO time_blocks (id, item_id, block_date, start_time,
                end_time, planned_minutes, label, block_type, position,
                created_at, updated_at)
            VALUES ('b1', NULL, '2026-11-05', '', '', 30, 'timeless',
                'item', 1, '2026-11-05', '2026-11-05')
            """
        )
        manager.db.conn.commit()

        adopted = manager.adopt_legacy_day("2026-11-05", _bounds())

        assert adopted == ["b1"]
        block = manager.get_time_blocks("2026-11-05")[0]
        assert block.slot_index == 0
        assert block.start_time == "08:00"
    finally:
        manager.close()


def test_adopting_a_day_twice_changes_nothing_the_second_time(tmp_path):
    """Idempotent, because it runs every time a day is opened.

    A second pass that re-placed already-placed blocks would shuffle a day
    the user had arranged, every time they looked at it.
    """
    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        manager.db.conn.execute(
            """
            INSERT INTO time_blocks (id, item_id, block_date, start_time,
                end_time, planned_minutes, label, block_type, position,
                created_at, updated_at)
            VALUES ('b1', NULL, '2026-11-05', '09:30', '10:00', 30, 'legacy',
                'item', 1, '2026-11-05', '2026-11-05')
            """
        )
        manager.db.conn.commit()
        manager.adopt_legacy_day("2026-11-05", _bounds())
        before = [
            (b.id, b.slot_index, b.start_time)
            for b in manager.get_time_blocks("2026-11-05")
        ]

        again = manager.adopt_legacy_day("2026-11-05", _bounds())

        assert again == []
        assert [
            (b.id, b.slot_index, b.start_time)
            for b in manager.get_time_blocks("2026-11-05")
        ] == before
    finally:
        manager.close()


def test_a_legacy_block_the_grid_cannot_hold_keeps_its_null(tmp_path):
    """**P2** — surfaced as outside the day, not given a box it did not ask for.

    22:00 is past every box of an 08:00--17:00 day. Adopting it onto some
    arbitrary free box would move planned work to a time the user never chose
    and say nothing; leaving it NULL is what makes build_day_grid show it.
    """
    from src.getmoredone.time_block_layout import build_day_grid

    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        manager.db.conn.execute(
            """
            INSERT INTO time_blocks (id, item_id, block_date, start_time,
                end_time, planned_minutes, label, block_type, position,
                created_at, updated_at)
            VALUES ('b1', NULL, '2026-11-05', '22:00', '22:30', 30, 'late',
                'item', 1, '2026-11-05', '2026-11-05')
            """
        )
        manager.db.conn.commit()

        adopted = manager.adopt_legacy_day("2026-11-05", _bounds())

        assert adopted == []
        blocks = manager.get_time_blocks("2026-11-05")
        assert blocks[0].slot_index is None
        grid = build_day_grid(blocks, _bounds())
        assert [b.label for b in grid.outside] == ["late"]
    finally:
        manager.close()


def test_a_legacy_block_before_day_start_keeps_its_null(tmp_path):
    """The other end of the same rule, and the one a "helpful" clamp would break.

    07:00 under an 08:00 Day Start has no box. Clamping it to box 0 would read
    as tidying up and would move a 07:00 block to 08:00 on top of whatever is
    already there, the first time the day was opened.
    """
    from src.getmoredone.time_block_layout import build_day_grid

    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        manager.db.conn.execute(
            """
            INSERT INTO time_blocks (id, item_id, block_date, start_time,
                end_time, planned_minutes, label, block_type, position,
                created_at, updated_at)
            VALUES ('b1', NULL, '2026-11-05', '07:00', '07:30', 30, 'early',
                'item', 1, '2026-11-05', '2026-11-05')
            """
        )
        manager.db.conn.commit()

        assert manager.adopt_legacy_day("2026-11-05", _bounds()) == []

        blocks = manager.get_time_blocks("2026-11-05")
        assert blocks[0].slot_index is None
        assert [b.label for b in build_day_grid(blocks, _bounds()).outside] == ["early"]
    finally:
        manager.close()


def test_a_legacy_block_whose_own_box_is_full_keeps_its_null(tmp_path):
    """Not slid to the next free box, even though one exists.

    Four blocks already sit in the 09:00 box, which is as many as a box can
    draw. The fifth is left outside rather than moved to 09:30 -- the user
    sees it and decides, which is the whole difference between surfacing and
    quietly rearranging someone's day (P2).
    """
    from src.getmoredone.time_block_layout import (
        MAX_BLOCKS_PER_SLOT,
        build_day_grid,
    )

    manager = DatabaseManager(str(tmp_path / "blocks.db"))
    try:
        for n in range(MAX_BLOCKS_PER_SLOT + 1):
            manager.db.conn.execute(
                """
                INSERT INTO time_blocks (id, item_id, block_date, start_time,
                    end_time, planned_minutes, label, block_type, position,
                    created_at, updated_at)
                VALUES (?, NULL, '2026-11-05', '09:00', '09:30', 30, ?,
                    'item', ?, '2026-11-05', '2026-11-05')
                """,
                (f"b{n}", f"crowd {n}", n + 1),
            )
        manager.db.conn.commit()

        adopted = manager.adopt_legacy_day("2026-11-05", _bounds())

        assert len(adopted) == MAX_BLOCKS_PER_SLOT
        blocks = manager.get_time_blocks("2026-11-05")
        placed = [b for b in blocks if b.slot_index is not None]
        assert {b.slot_index for b in placed} == {2}
        outside = build_day_grid(blocks, _bounds()).outside
        assert [b.label for b in outside] == [f"crowd {MAX_BLOCKS_PER_SLOT}"]
    finally:
        manager.close()


# --- CE-M1.1 — the column the Google Calendar export writes -----------------

def test_cem11_migration_adds_calendar_event_id_idempotently(tmp_path):
    """CE-M1.1 — the column arrives on an upgrading database, exactly once.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m11
    Tests: this test

    The second `initialize_schema` is the point: a guard that checked the
    columns as a block rather than one at a time would skip this one forever
    on a database that already has `slot_index`, and the export would then
    write an id into a column that is not there.
    """
    path = _legacy_db(tmp_path)

    for _ in range(2):
        db = Database(str(path))
        db.initialize_schema()
        db.close()

    conn = sqlite3.connect(str(path))
    try:
        info = list(conn.execute("PRAGMA table_info(time_blocks)"))
        legacy = conn.execute(
            "SELECT calendar_event_id FROM time_blocks WHERE id = 'old-block'"
        ).fetchone()
    finally:
        conn.close()

    names = [row[1] for row in info]
    assert names.count("calendar_event_id") == 1, (
        "calendar_event_id should be added once, by whichever run finds it absent"
    )

    column = [row for row in info if row[1] == "calendar_event_id"][0]
    assert column[2].upper() == "TEXT"
    assert column[3] == 0, "a block that was never exported must be representable"
    assert column[4] is None, (
        "a default would back-fill every pre-export block with something that "
        "reads as an event id"
    )
    assert legacy[0] is None, (
        "a block from before the export existed has never been exported, and "
        "must say so rather than claiming an event"
    )


def test_cem11a_a_fresh_database_declares_calendar_event_id_on_its_own(
    tmp_path, monkeypatch
):
    """CE-M1.1 — the CREATE TABLE half, with the migrations switched off.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m11
    Tests: this test

    Same reason as TB-M1.1a above: every other test here would pass with the
    CREATE TABLE half missing, because the migration adds the column to a new
    database as readily as to an old one.
    """
    monkeypatch.setattr(Database, "_run_migrations", lambda self, conn: None)

    db = Database(str(tmp_path / "no_migrations.db"))
    db.initialize_schema()
    try:
        names = [
            row[1] for row in db.conn.execute("PRAGMA table_info(time_blocks)")
        ]
    finally:
        db.close()

    assert "calendar_event_id" in names, (
        "calendar_event_id comes only from the migration; a fresh install "
        "would export a day and have nowhere to record it"
    )


def test_cem11b_migration_adds_the_event_calendar_idempotently(tmp_path):
    """CE-M1.1 — the calendar an event id belongs to, added exactly once.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m11
    Tests: this test

    The second `initialize_schema` matters for the same reason as
    `test_cem11`: this column is the second one in the same tuple, so a guard
    written per-tuple rather than per-column would skip it on any database
    that already has `calendar_event_id` — which is every database the first
    version of the export ever wrote to.
    """
    path = _legacy_db(tmp_path)

    for _ in range(2):
        db = Database(str(path))
        db.initialize_schema()
        db.close()

    conn = sqlite3.connect(str(path))
    try:
        info = list(conn.execute("PRAGMA table_info(time_blocks)"))
        legacy = conn.execute(
            "SELECT calendar_event_calendar_id FROM time_blocks WHERE id = 'old-block'"
        ).fetchone()
    finally:
        conn.close()

    names = [row[1] for row in info]
    assert names.count("calendar_event_calendar_id") == 1

    column = [row for row in info if row[1] == "calendar_event_calendar_id"][0]
    assert column[2].upper() == "TEXT"
    assert column[3] == 0, "a block that was never exported must be representable"
    assert column[4] is None, (
        "a default would claim a calendar for events that were never created"
    )
    assert legacy[0] is None


def test_cem11c_a_fresh_database_declares_the_event_calendar_on_its_own(
    tmp_path, monkeypatch
):
    """CE-M1.1 — the CREATE TABLE half of the same column.

    Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m11
    Tests: this test
    """
    monkeypatch.setattr(Database, "_run_migrations", lambda self, conn: None)

    db = Database(str(tmp_path / "no_migrations_calendar.db"))
    db.initialize_schema()
    try:
        names = [
            row[1] for row in db.conn.execute("PRAGMA table_info(time_blocks)")
        ]
    finally:
        db.close()

    assert "calendar_event_calendar_id" in names
