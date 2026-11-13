"""AWA-A1 — every reader of an item's parent follows the Weekly Tactic link.

Spec: docs/spec_2026-11-07_ape_week_actions.md#awa-m5

AWA-A1 found two buttons writing two row shapes for one relationship:
`screens/weekly_items.py`'s Add Action Item set `parent_id`, and APE Week
Actions' Add set `weekly_tactic_id`. The fix made both write
`weekly_tactic_id` and moved the readers onto `parent_of`. The Weekly Items
button was removed by VTF-M5 and its method by VTF-A2, and its two tests went
with it. What is left here is the readers' half, which does not depend on
which button made the row.
"""

from types import MethodType, SimpleNamespace

from src.getmoredone.screens.drag_schedule import DragScheduleScreen
from src.getmoredone.screens.item_lineage import lineage_for_item
from src.getmoredone.screens.segment_color_utils import (
    resolve_segment_color_for_item,
)
from src.getmoredone.weekly_tactic import tactic_of
from tests.weekly_tactic_fixtures import (
    make_daily_item,
    make_vps,
    make_week_item,
    seed_ape,
)


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
