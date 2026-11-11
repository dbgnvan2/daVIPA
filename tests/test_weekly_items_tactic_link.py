"""AWA-A1 — APE Week Assignment's Add Action Item writes both link columns.

Spec: docs/spec_2026-11-07_ape_week_actions.md#awa-m5

`screens/weekly_items.py` set `parent_id` and left `weekly_tactic_id` NULL,
while the APE Week Actions tab's own Add button set `weekly_tactic_id`. Two
buttons on two tabs produced rows of two shapes for the same relationship, and
`weekly_tactic.tactic_of` — the predicate WT-M3.D.1 names as the single
authority on "is this item week-filed" — answered no for everything the first
button made.

The fix writes `weekly_tactic_id` *instead of* `parent_id`, not as well as it,
which is why the reopen assertion is here: a row holding both is not a state
this app keeps. `migrate_parent_links_to_weekly_tactic` runs from
`Database.initialize_schema` on every launch and clears `parent_id` on a row
that names a tactic explicitly, so a both-columns row would be rewritten on
the next launch — and the test that asserted both would have been pinning a
state the app discards (P8).

No Tk here: the method under test needs a database, a selected row and a status
label, so it is driven on a stub, the same way tests/test_weekly_items_title.py
drives it.
"""

from types import MethodType, SimpleNamespace

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.screens.drag_schedule import DragScheduleScreen
from src.getmoredone.screens.item_lineage import lineage_for_item
from src.getmoredone.screens.segment_color_utils import (
    resolve_segment_color_for_item,
)
from src.getmoredone.screens.weekly_items import WeeklyItemsScreen
from src.getmoredone.weekly_tactic import parent_of, tactic_of
from tests.weekly_tactic_fixtures import (
    make_daily_item,
    make_vps,
    make_week_item,
    seed_ape,
)


def _screen_stub(vps, weekly_row, typed):
    """Enough of WeeklyItemsScreen to drive the create method without a display."""
    stub = SimpleNamespace(
        vps_manager=vps,
        app=SimpleNamespace(db_manager=vps.db_manager),
        selected_weekly_item=weekly_row,
        status_label=SimpleNamespace(configure=lambda **kw: None),
    )
    stub._typed = typed
    return stub


def _create(stub, monkeypatch):
    """Run the real method with the input dialog answering ``stub._typed``."""
    import src.getmoredone.screens.weekly_items as wi

    monkeypatch.setattr(
        wi.ctk, "CTkInputDialog",
        lambda *a, **kw: SimpleNamespace(get_input=lambda: stub._typed))
    WeeklyItemsScreen.create_action_item_for_selected_weekly(stub)


def test_awaa1_the_add_button_links_by_weekly_tactic_id(tmp_path, monkeypatch):
    """AWA-A1 — the new row names its tactic in `weekly_tactic_id`, and only there.

    Asserted through `tactic_of` and `parent_of` as well as on the columns:
    the columns are the mechanism, and those two predicates are what every
    reader of the relationship actually calls. `parent_of` must still answer
    the tactic — it falls back to `tactic_of` — so moving the link cannot move
    the row in the tree.

    Reopened on the same file (P8): the launch migration is the authority on
    which shape survives, and a row written with both columns does not.

    Also closes AWA-A3's remainder, which was `tactic_of` returning None for a
    `parent_id`-only child.
    """
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        tactic = make_week_item(vps, ape_id, start="2026-02-23", due="2026-03-01")
        weekly_row = {
            "id": tactic.id,
            "title": "PW|LS|Blog - W09",
            "who": "Self",
            "start_date": tactic.start_date,
            "category": None,
            "annual_plan_element_id": ape_id,
        }

        _create(_screen_stub(vps, weekly_row, "Draft the outline"), monkeypatch)

        rows = vps.db.conn.execute(
            "SELECT id, parent_id, weekly_tactic_id, item_type FROM action_items "
            "WHERE title = ?", ("Draft the outline",)).fetchall()
        assert len(rows) == 1
        assert rows[0]["weekly_tactic_id"] == tactic.id
        assert rows[0]["parent_id"] is None
        assert rows[0]["item_type"] == "daily"

        created = vps.db_manager.get_action_item(rows[0]["id"])
        assert tactic_of(created) == tactic.id
        assert parent_of(created) == tactic.id, (
            "parent_of falls back to tactic_of, so the tree is unchanged")
        item_id = rows[0]["id"]
    finally:
        vps.close()

    # The launch migration decides which shape survives. Nothing it writes
    # should touch a row this button made.
    reopened = DatabaseManager(db_path=str(tmp_path / "weekly_tactic.db"))
    try:
        again = reopened.get_action_item(item_id)
        assert tactic_of(again) == tactic.id
        assert again.parent_id is None
    finally:
        reopened.close()


def test_awaa1b_the_add_button_reports_what_the_refile_did(tmp_path, monkeypatch):
    """AWA-A1 — the cascade this create now runs reaches the user.

    Writing the tactic link puts the create on `create_action_item`'s re-file
    path, which can refuse a week or build plan records and records what it did
    on the manager. The sibling button in `screens/week_actions.py` calls
    `notify_weekly_tactic_changes` for exactly that reason; this one reported
    success unconditionally and had nothing to report only because it never
    re-filed (P5, P2).

    Asserted on the order: the notice has to be raised before the status line
    claims the add went through.
    """
    vps = make_vps(tmp_path)
    try:
        import src.getmoredone.screens.weekly_items as wi

        ape_id = seed_ape(vps)
        tactic = make_week_item(vps, ape_id, start="2026-02-23", due="2026-03-01")
        weekly_row = {
            "id": tactic.id,
            "title": "PW|LS|Blog - W09",
            "who": "Self",
            "start_date": tactic.start_date,
            "category": None,
            "annual_plan_element_id": ape_id,
        }

        order = []
        stub = _screen_stub(vps, weekly_row, "Draft the outline")
        stub.status_label = SimpleNamespace(
            configure=lambda **kw: order.append("status"))
        monkeypatch.setattr(wi, "notify_weekly_tactic_changes",
                            lambda db, parent=None: order.append("notify"))

        _create(stub, monkeypatch)

        assert order == ["notify", "status"]
    finally:
        vps.close()


def test_awaa1c_every_reader_resolves_a_week_filed_parent(tmp_path):
    """AWA-A1 — the segment stamp and all three lineage readers follow the link.

    Four readers of "what is this item's parent" were reading `parent_id`
    directly, where nothing is written any more:

    * `screens/item_lineage.lineage_for_item` — Today, Upcoming, All Items,
      Hierarchical.
    * `DragScheduleScreen._lineage_for_item` — Plan Day's private copy of the
      same function, which also decides whether its Segment filter shows the
      row. One fixed and not the other is two screens disagreeing about one
      item (P5), so both are asserted against the same expectation.
    * `segment_color_utils.resolve_segment_color_for_item` step 4, which fires
      for a row carrying no segment id of its own.
    * `db_manager._stamp_segment_from_relationships`, which is the only one of
      the four that writes.

    The item shape is a week-filed item with **no Annual Plan Element of its
    own**, because that is where the fallback decides anything: an item the
    Add buttons create carries a copy of the tactic's APE, so the APE answers
    first and no reader reaches the parent at all. The shape without one is
    what `migrate_parent_links_to_weekly_tactic` produces from a legacy
    `parent_id` row. Its only lineage is through its Weekly Tactic.

    Plan Day's method is driven on a stub rather than a built screen: it needs
    three caches and a database, so no window is put on screen for it.
    """
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        tactic = make_week_item(vps, ape_id)
        tactic_row = vps.db_manager.get_action_item(tactic.id)
        assert tactic_row.segment_description_id, (
            "the tactic must carry a segment of its own, or this proves nothing")
        expected = lineage_for_item(tactic_row, vps.db_manager, {}, {}, {})
        assert all(expected), f"the tactic has no lineage to inherit: {expected}"

        legacy = make_daily_item(vps, title="Moved by the link migration",
                                 weekly_tactic_id=tactic.id, refile=False)
        stored = vps.db_manager.get_action_item(legacy.id)
        assert stored.annual_plan_element_id is None, (
            "the shape under test is an item with no APE of its own")
        assert stored.parent_id is None and tactic_of(stored) == tactic.id

        # The one reader of the four that writes.
        assert stored.segment_description_id == tactic_row.segment_description_id

        # Cleared so the readers below have to follow the link rather than the
        # column the stamp just filled.
        vps.db.conn.execute(
            "UPDATE action_items SET segment_description_id = NULL WHERE id = ?",
            (legacy.id,))
        vps.db.conn.commit()
        stored = vps.db_manager.get_action_item(legacy.id)

        assert lineage_for_item(stored, vps.db_manager, {}, {}, {}) == expected

        plan_day = SimpleNamespace(
            db_manager=vps.db_manager,
            _item_lineage_cache={}, _ape_lineage_cache={}, _week_segment_cache={})
        for name in ("_lineage_from_ape_id", "_segment_from_week_action",
                     "_lineage_for_item"):
            setattr(plan_day, name,
                    MethodType(getattr(DragScheduleScreen, name), plan_day))
        plan_day._lineage_from_structured_title = \
            DragScheduleScreen._lineage_from_structured_title
        assert plan_day._lineage_for_item(stored) == expected

        # The colour comes out of the database by way of the tactic, so the
        # claim is that the child gets the same accent as its tactic — not
        # that some map was consulted.
        tactic_color = resolve_segment_color_for_item(
            tactic_row, {}, {}, vps.db_manager, {}, {}, {})
        assert tactic_color, "the tactic has no colour to inherit"
        assert resolve_segment_color_for_item(
            stored, {}, {}, vps.db_manager, {}, {}, {}) == tactic_color

        # The repair tool reads the same relationship, or it cannot mend a row
        # whose only parent is a Weekly Tactic.
        vps.db_manager.backfill_action_item_segments()
        assert vps.db_manager.get_action_item(legacy.id).segment_description_id \
            == tactic_row.segment_description_id
    finally:
        vps.close()
