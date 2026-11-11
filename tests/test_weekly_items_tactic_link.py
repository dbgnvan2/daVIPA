"""AWA-A1 — APE Week Assignment's Add Action Item writes both link columns.

Spec: docs/spec_2026-11-07_ape_week_actions.md#awa-m5

`screens/weekly_items.py` set `parent_id` and left `weekly_tactic_id` NULL,
while the APE Week Actions tab's own Add button set `weekly_tactic_id`. Two
buttons on two tabs produced rows of two shapes for the same relationship, and
`weekly_tactic.tactic_of` — the predicate WT-M3.D.1 names as the single
authority on "is this item week-filed" — answered no for everything the first
button made.

No Tk here: the method under test needs a database, a selected row and a status
label, so it is driven on a stub, the same way tests/test_weekly_items_title.py
drives it.
"""

from types import SimpleNamespace

from src.getmoredone.screens.weekly_items import WeeklyItemsScreen
from src.getmoredone.weekly_tactic import parent_of, tactic_of
from tests.weekly_tactic_fixtures import make_vps, make_week_item, seed_ape


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


def test_awaa1_the_add_button_sets_both_link_columns(tmp_path, monkeypatch):
    """AWA-A1 — the new row names its tactic in `weekly_tactic_id` too.

    Asserted through `tactic_of` and `parent_of` as well as on the columns:
    the columns are the mechanism, and those two predicates are what every
    reader of the relationship actually calls. `parent_of` must still answer
    the tactic — WTP-D3 has `parent_id` win when both are set, so writing the
    second column cannot move the row in the tree.

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
        assert rows[0]["parent_id"] == tactic.id
        assert rows[0]["item_type"] == "daily"

        created = vps.db_manager.get_action_item(rows[0]["id"])
        assert tactic_of(created) == tactic.id
        assert parent_of(created) == tactic.id
    finally:
        vps.close()
