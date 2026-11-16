"""Deleting an Annual Plan Element: both refusals reach the user.

An Annual Plan Element is deleted only when it has no child records. There are
two ways it can have them — attached Projects and attached Action Items — and
each raises its own exception. The screen caught the first and not the second,
so the newer refusal would have escaped a Tk ``command`` into a stderr a
double-clicked app has nowhere to send: the user would press Delete, see
nothing happen, and have no idea why (P5).

MOD-M2 moved both refusals off ``messagebox.showerror`` and onto the screen's
notice line. The contract these tests exist for is unchanged -- the refusal,
its count and the names of the blockers reach the user -- so they assert the
same things through ``set_status``. The one deliberate change is the cap: a
dialog body listed ten names down the window, and a notice line has room for
``status_notice.INLINE_LIST_CAP``.
"""

from types import SimpleNamespace

import pytest

import src.getmoredone.screens.annual_vision_segments as avs
from src.getmoredone.models import ActionItem
from src.getmoredone.vps_manager import (
    ActionItemsAttachedError,
    ProjectBoardsAttachedError,
)
from src.getmoredone.screens.status_notice import INLINE_LIST_CAP
from tests.weekly_tactic_fixtures import make_vps, seed_ape


def _screen_stub(vps, raising):
    """Enough of the screen to drive the delete handler without a display."""
    notices = []
    stub = SimpleNamespace(
        vps_manager=SimpleNamespace(
            delete_annual_records_for_vision_element=raising),
        refresh_lists=lambda: None,
        _parse_year=lambda: 2026,
        notices=notices,
    )
    stub.set_status = lambda text, kind="muted": notices.append((kind, text))
    return stub


@pytest.fixture
def dialogs(monkeypatch):
    """Only the question is a dialog now; the refusals are notices (MOD-M2)."""
    seen = {"asked": []}
    monkeypatch.setattr(avs.messagebox, "askyesno",
                        lambda *a, **k: seen["asked"].append(a) or True)
    return seen


def _delete(stub, row=None):
    avs.AnnualVisionSegmentsScreen.delete_annual_item(
        stub, row or {"vision_element_id": "ve-1", "key_field": "Blog"})


def test_action_items_attached_is_reported_not_raised(dialogs):
    def raising(year, ve_id):
        raise ActionItemsAttachedError(["Draft the outline", "Publish it"])

    stub = _screen_stub(None, raising)
    _delete(stub)

    assert stub.notices, "the refusal reached nobody"
    kind, message = stub.notices[0]
    assert kind == "error"
    assert "Draft the outline" in message and "Publish it" in message
    assert "2 action item(s)" in message


def test_a_long_list_of_items_is_capped(dialogs):
    def raising(year, ve_id):
        raise ActionItemsAttachedError([f"Item {i}" for i in range(25)])

    stub = _screen_stub(None, raising)
    _delete(stub)

    _kind, message = stub.notices[0]
    assert "25 action item(s)" in message
    assert f"and {25 - INLINE_LIST_CAP} more" in message, message
    # Named inline, so the line stays a line: the cap, not ten bullets.
    assert message.count(",") == INLINE_LIST_CAP - 1, message
    assert "Item 0" in message and f"Item {INLINE_LIST_CAP}" not in message


def test_the_projects_refusal_still_works(dialogs):
    def raising(year, ve_id):
        raise ProjectBoardsAttachedError(["Website Rebuild"])

    stub = _screen_stub(None, raising)
    _delete(stub)

    kind, message = stub.notices[0]
    assert kind == "error"
    assert "Website Rebuild" in message
    assert "project(s) still attached" in message


def test_a_clean_delete_refreshes_and_says_nothing(dialogs):
    stub = _screen_stub(None, lambda year, ve_id: True)
    refreshed = []
    stub.refresh_lists = lambda: refreshed.append(True)

    _delete(stub)

    assert refreshed == [True]
    assert stub.notices == []


def test_the_refusal_is_raised_for_a_real_attached_item(tmp_path):
    """...and the exception the screen handles is the one the manager raises."""
    vps = make_vps(tmp_path)
    try:
        ape_id = seed_ape(vps)
        item = ActionItem(who="Self", title="On the plan",
                          annual_plan_element_id=ape_id)
        vps.db_manager.create_action_item(item, apply_defaults=False)

        row = vps.db.conn.execute(
            "SELECT vision_element_id FROM annual_plan_elements WHERE id = ?",
            (ape_id,)).fetchone()
        with pytest.raises(ActionItemsAttachedError) as excinfo:
            vps.delete_annual_records_for_vision_element(2026, row["vision_element_id"])
        assert "On the plan" in str(excinfo.value)
    finally:
        vps.close()
