"""CIP batch 2 -- the Plan screen changing a Google Calendar meeting.

Purpose: prove CIP-M4.1, M4.4, M4.6 to M4.8 and E1/E7 on a real, unmapped
         Plan screen with a fake client. The worker thread is joined and its
         poll called directly, so nothing here waits on Tk's clock.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#7-m4--editing-the-calendar-from-inside-the-plan
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_editing.md
"""

from __future__ import annotations

import threading

import pytest

from src.getmoredone.calendar_commitment_edits import EditRequest
from src.getmoredone.calendar_commitments import parse_event
from src.getmoredone.google_calendar import AuthenticationRequired
from src.getmoredone.screens import plan_commitment_edits as pce
from src.getmoredone.screens import plan_commitments as pc
from tests.test_calendar_commitment_edits import GUESTS, EditCalendar
from tests.test_plan_screen_calendar_export import (  # noqa: F401 - fixtures
    THURSDAY,
    manager,
    root,
    settings,
)
from tests.test_plan_screen_commitments import (  # noqa: F401 - fixtures
    TEN,
    _box,
    _chips,
    _drawn_texts,
    _event,
    _open,
    ready,
)

ONE_PM = 10  # 13:00 is box 10 of the default 08:00 day


class Factory:
    """Hands the screen one ``EditCalendar``, counting how often it was asked."""

    def __init__(self, client=None, error=None):
        self.client = client
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.client


@pytest.fixture
def asked(monkeypatch):
    """Every dialog the screen opens, answered from ``asked.answers``."""

    class Asked:
        answers = {"askokcancel": True, "askyesnocancel": False}
        seen = []

    Asked.seen = []
    for name in ("askokcancel", "askyesnocancel"):
        def ask(title, message, _name=name, **_kwargs):
            Asked.seen.append((_name, message))
            return Asked.answers[_name]

        monkeypatch.setattr(pce.messagebox, name, ask)
    return Asked


def _held(manager, event):
    parts = parse_event(event, calendar_id="primary", dates=[THURSDAY])
    manager.replace_commitments_for_dates([THURSDAY], parts, "2026-11-05T09:00:00")
    return manager.get_commitments(THURSDAY)[0]


def _screen(root, manager, settings, event, **client_kwargs):
    commitment = _held(manager, event)
    factory = Factory(EditCalendar(event, zone=None, **client_kwargs))
    screen = _open(root, manager, settings, factory)
    return screen, factory, commitment


def _finish(screen, root):
    thread = getattr(screen, "_edit_thread", None)
    if thread is not None:
        thread.join(timeout=30)
        assert not thread.is_alive(), "the calendar write did not finish"
        screen._poll_commitment_write()
    root.update_idletasks()


def _bindings(widget):
    from src.getmoredone.screens.plan import _subtree

    return [w for w in _subtree(widget) if w.bind("<ButtonPress-1>")]


# --------------------------------------------------------------- M4.1


def test_cipm41_an_uneditable_chip_has_no_drag_binding(root, manager, settings, ready):
    """M4.1 -- someone else's meeting has no drag to refuse; the user's own has one."""
    theirs = {**_event("theirs"), "organizer": {"self": False}}
    mine = _event("mine", start=(14, 0), end=(14, 30), summary="Mine")
    manager.replace_commitments_for_dates(
        [THURSDAY],
        parse_event(theirs, calendar_id="primary", dates=[THURSDAY])
        + parse_event(mine, calendar_id="primary", dates=[THURSDAY]),
        "2026-11-05T09:00:00",
    )
    screen = _open(root, manager, settings, Factory())

    [their_chip] = _chips(_box(screen, TEN))
    [my_chip] = _chips(_box(screen, TEN + 8))

    assert _bindings(their_chip) == []
    assert _bindings(my_chip) != []


def test_cipm41_the_menu_of_an_uneditable_meeting_offers_no_edit(root, manager, settings, ready):
    """M4.1 -- the uneditable meeting offers only Ignore; the user's own offers changes."""
    theirs = _held(manager, {**_event(), "organizer": {"self": False}})
    screen = _open(root, manager, settings, Factory())
    mine = _held(manager, _event())

    their_labels = [label for label, _ in screen.commitment_menu_entries(theirs)]
    my_labels = [label for label, _ in screen.commitment_menu_entries(mine)]

    assert their_labels == ["Ignore on this day (stays on your calendar)"]
    assert screen.commitment_edit_entries(theirs) == []
    assert "Rename…" in my_labels and "Delete from Google Calendar…" in my_labels
    assert "30 minutes  (now)" in my_labels


def test_cipm41_a_drop_of_an_uneditable_meeting_makes_no_call(root, manager, settings, ready, asked):
    """M4.1 -- refused before any client is made."""
    event = {**_event(), "organizer": {"self": False}}
    screen, factory, commitment = _screen(root, manager, settings, event)

    assert screen.drop_commitment(commitment, ONE_PM) is False
    assert screen.change_commitment(commitment, EditRequest(title="Mine now")) is False
    assert screen.change_commitment(commitment, EditRequest(delete=True)) is False
    assert factory.calls == 0
    assert asked.seen == []


# --------------------------------------------------------------- M4.2 on screen


def test_cipm42_a_drop_moves_the_meeting_on_the_grid(root, manager, settings, ready, asked):
    """M4.2 / E3 -- dropped on 13:00, drawn at 13:00 once Google confirms."""
    screen, factory, commitment = _screen(root, manager, settings, _event())

    assert screen.drop_commitment(commitment, ONE_PM) is True
    assert any("Board meeting" in t for t in _drawn_texts(_box(screen, TEN)))  # not yet (M4.5)
    _finish(screen, root)

    assert any("13:00–13:30  Board meeting" in t for t in _drawn_texts(_box(screen, ONE_PM)))
    assert not any("Board meeting" in t for t in _drawn_texts(_box(screen, TEN)))
    assert asked.seen == []  # a guestless, single meeting is not asked about (E7)


# --------------------------------------------------------------- M4.4 delete


def test_cipm44_delete_asks_first_and_names_the_event(root, manager, settings, ready, asked):
    """M4.4 -- the question names the meeting and says it leaves the calendar."""
    screen, factory, commitment = _screen(root, manager, settings, _event())

    screen.change_commitment(commitment, EditRequest(delete=True))
    _finish(screen, root)

    [(kind, message)] = asked.seen
    assert kind == "askokcancel"
    assert "Board meeting" in message and "removed from your Google Calendar" in message
    assert factory.client.writes() == [("delete", "ev1", "primary", "none")]
    assert manager.get_commitments(THURSDAY) == []


def test_cipm44_cancel_makes_no_call(root, manager, settings, ready, asked):
    """M4.4 -- Cancel means no client, no write, the meeting still drawn."""
    asked.answers = {"askokcancel": False, "askyesnocancel": False}
    screen, factory, commitment = _screen(root, manager, settings, _event())

    assert screen.change_commitment(commitment, EditRequest(delete=True)) is False

    assert factory.calls == 0
    assert len(manager.get_commitments(THURSDAY)) == 1


# --------------------------------------------------------------- M4.6 / E1 / E7


def test_cipm46_a_recurring_occurrence_is_confirmed_as_this_one_only(root, manager, settings, ready, asked):
    """M4.6 -- a change to one occurrence says so before it is made."""
    event = {**_event(), "recurringEventId": "series-1"}
    screen, factory, commitment = _screen(root, manager, settings, event)

    screen.change_commitment(commitment, EditRequest(title="Renamed"))
    _finish(screen, root)

    [(kind, message)] = asked.seen
    assert kind == "askokcancel" and "this occurrence only" in message


@pytest.mark.parametrize("answer, sent", [(True, "all"), (False, "none")])
def test_cipe1_guests_are_asked_and_the_answer_reaches_send_updates(
    root, manager, settings, ready, asked, answer, sent
):
    """E1 -- the guest question is asked by number, and its answer is what Google gets."""
    asked.answers = {"askokcancel": True, "askyesnocancel": answer}
    screen, factory, commitment = _screen(root, manager, settings, {**_event(), "attendees": GUESTS})

    screen.change_commitment(commitment, EditRequest(title="Renamed"))
    _finish(screen, root)

    [(kind, message)] = asked.seen
    assert kind == "askyesnocancel" and "Email the 1 other guest of" in message
    [write] = factory.client.writes()
    assert write[-1] == sent


def test_cipe1_cancel_on_the_guest_question_makes_no_call(root, manager, settings, ready, asked):
    """E1 -- Cancel on the guest question is Cancel."""
    asked.answers = {"askokcancel": True, "askyesnocancel": None}
    screen, factory, commitment = _screen(root, manager, settings, {**_event(), "attendees": GUESTS})

    assert screen.change_commitment(commitment, EditRequest(title="Renamed")) is False
    assert factory.calls == 0


# --------------------------------------------------------------- M4.7 one at a time


def test_cipm47_a_write_is_refused_while_a_refresh_runs(root, manager, settings, ready, asked):
    """M4.7 / E8 -- a read holds the database's calendar slot; a change waits, unasked."""
    screen, factory, commitment = _screen(root, manager, settings, {**_event(), "attendees": GUESTS})
    db_path = manager.db.db_path
    assert pc.claim_refresh(db_path)
    try:
        assert screen.change_commitment(commitment, EditRequest(title="X")) is False
    finally:
        pc.release_refresh(db_path)

    assert factory.calls == 0
    assert asked.seen == []  # refused before the user is asked anything
    assert screen.status_label.cget("text") == pce.BUSY_TEXT


class Blocking(EditCalendar):
    """A client whose update waits until the test lets it go."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.go = threading.Event()

    def update_event(self, *args, **kwargs):
        assert self.go.wait(timeout=30)
        return super().update_event(*args, **kwargs)


def test_cipm47_refresh_is_refused_while_a_write_runs(root, manager, settings, ready, asked):
    """M4.7 -- while a change is in flight, Refresh starts nothing."""
    event = _event()
    commitment = _held(manager, event)
    client = Blocking(event, zone=None)
    screen = _open(root, manager, settings, Factory(client))

    assert screen.change_commitment(commitment, EditRequest(title="Renamed"))
    try:
        assert screen.btn_refresh_calendar.cget("state") == "disabled"
        assert screen.refresh_calendar() is False
    finally:
        client.go.set()
        _finish(screen, root)
    assert screen.btn_refresh_calendar.cget("state") == "normal"


def test_cipm47_the_claim_outlives_the_screen(root, manager, settings, ready, asked):
    """M4.7 -- a Plan screen built while a change runs comes up with Refresh disabled."""
    event = {**_event(), "attendees": GUESTS}
    commitment = _held(manager, event)
    client = Blocking(event, zone=None)
    first = _open(root, manager, settings, Factory(client))
    assert first.change_commitment(commitment, EditRequest(title="Renamed"))
    try:
        second = _open(root, manager, settings, Factory(client))
        second.sync_refresh_button()
        assert second.btn_refresh_calendar.cget("state") == "disabled"
        asked.seen.clear()
        assert second.change_commitment(commitment, EditRequest(title="Again")) is False
        assert asked.seen == []
    finally:
        client.go.set()
        _finish(first, root)


# --------------------------------------------------------------- M4.8 prerequisites


@pytest.mark.parametrize("missing", ["libraries", "credentials", "token"])
def test_cipm48_each_missing_prerequisite_refuses_and_reenables(
    root, manager, settings, ready, asked, missing
):
    """M4.8 -- refused with a reason, no client made, Refresh still usable."""
    screen, factory, commitment = _screen(root, manager, settings, _event())
    ready(**{missing: False})

    assert screen.change_commitment(commitment, EditRequest(title="X")) is False

    assert factory.calls == 0
    assert screen.status_label.cget("text") == pce.NOT_READY_TEXT
    assert screen.btn_refresh_calendar.cget("state") == "normal"
    assert screen._edit_running is False


def test_cipm48_a_lapsed_sign_in_is_reported_and_reenables(root, manager, settings, ready, asked):
    """M4.8 -- the sign-in lapses as the client is built: said, nothing changed."""
    event = _event()
    commitment = _held(manager, event)
    screen = _open(root, manager, settings,
                   Factory(error=AuthenticationRequired("Google Calendar needs you to sign in again")))

    assert screen.change_commitment(commitment, EditRequest(title="X"))
    _finish(screen, root)

    assert screen.status_label.cget("text") == "Not changed: Google Calendar needs you to sign in again"
    assert screen.btn_refresh_calendar.cget("state") == "normal"
    assert manager.get_commitments(THURSDAY)[0].title == "Board meeting"


def test_cipm42_releasing_a_dragged_meeting_on_a_box_starts_the_move(
    root, manager, settings, ready, asked, monkeypatch
):
    """E3 -- the release handler hands the meeting and the box to the move."""
    screen, factory, commitment = _screen(root, manager, settings, _event())
    monkeypatch.setattr(screen, "slot_under_pointer", lambda: ONE_PM)
    monkeypatch.setattr(screen, "virtual_under_pointer", lambda: None)
    screen.start_commitment_drag(None, commitment)

    screen.on_drag_release(None)
    _finish(screen, root)

    assert screen._drag_commitment is None
    assert manager.get_commitments(THURSDAY)[0].start_time == "13:00"
