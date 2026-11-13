"""BP6 — a week-filed Action Item's lineage never depended on its title.

Spec: docs/unused-docs/implementation_plan_2026-08-19_backlog_clearance.md#bp6

The Weekly Items screen's Add Action Item used to compose
``<tactic context> - <title>``. That button and its method are gone (VTF-M5,
VTF-A2). What these tests pinned beyond the button is kept: ``lineage_for_item``
resolves an item's segment/subsegment/category from its Annual Plan Element
first and its parent second, so an unprefixed title loses nothing. The item is
built the way APE Week Actions' Add builds it — the tactic's APE copied on,
linked by ``weekly_tactic_id`` — with a legacy-shaped tactic title, the one
the prefix used to be read from.
"""

from src.getmoredone.models import ActionItem
from src.getmoredone.screens.item_lineage import lineage_for_item
from tests.weekly_tactic_fixtures import make_vps, make_week_item, seed_ape


def _week_filed_item(vps):
    """A daily item under a legacy-titled tactic, as APE Week Actions makes one."""
    ape_id = seed_ape(vps)
    tactic = make_week_item(vps, ape_id, title="PW|LS|Blog - W34 - Publish the March post")
    item = ActionItem(
        who="Self",
        title="Draft the outline",
        weekly_tactic_id=tactic.id,
        start_date=tactic.start_date,
        due_date=tactic.start_date,
        annual_plan_element_id=ape_id,
        item_type="daily",
    )
    vps.db_manager.create_action_item(item, apply_defaults=False)
    return vps.db_manager.get_action_item(item.id)


def test_bp6_lineage_still_resolves_without_the_prefix(tmp_path):
    """The prefix was a lineage fallback; the APE is what actually answers."""
    vps = make_vps(tmp_path)
    try:
        item = _week_filed_item(vps)

        segment, subsegment, category = lineage_for_item(item, vps.db_manager, {}, {}, {})
        assert segment and subsegment and category, (
            f"the unprefixed item has no lineage at all: {(segment, subsegment, category)}")
        assert subsegment == "Living Systems"
        assert category == "Blog"
    finally:
        vps.close()


def test_bp6_lineage_survives_even_with_the_annual_plan_element_missing(tmp_path):
    """The second fallback — the parent tactic — still answers on its own.

    Without this, "the APE covers it" would be a single point of failure the
    prefix used to back up.
    """
    vps = make_vps(tmp_path)
    try:
        item = _week_filed_item(vps)
        item.annual_plan_element_id = None

        segment, subsegment, category = lineage_for_item(item, vps.db_manager, {}, {}, {})
        assert (segment, subsegment, category) != ("", "", ""), (
            "with no APE the item falls through to the parent tactic, and did not")
        assert category == "Blog"
    finally:
        vps.close()
