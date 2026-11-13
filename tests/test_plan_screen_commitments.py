"""CIP batch 1 -- the Plan screen draws Google Calendar commitments and reads them.

Purpose: prove CIP-M2.2, M3.3--M3.9, M5.1--M5.5, D4 and D12 on the real screen.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md

Real Tk and a tmp_path database, as in the export's screen tests. No test here
reaches the network: ``calendar_client_factory`` is replaced, and the three
prerequisite checks on ``GoogleCalendarManager`` are monkeypatched. None takes
the ``mapped_windows`` fixture. The worker thread is joined, and the poll it
would schedule is called directly, so nothing here waits on Tk's clock.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.getmoredone import google_calendar as gc
from src.getmoredone.calendar_commitments import CommitmentFetchError
from src.getmoredone.models import ActionItem, CalendarCommitment
from src.getmoredone.screens import plan_commitments as pc
from src.getmoredone.screens.calendar_dialog import not_connected_message
from src.getmoredone.screens.plan import REFUSAL_TEXT, PlanScreen
from src.getmoredone.theme import semantic_colors
from src.getmoredone.time_block_layout import SlotRefusal, format_hhmm
from tests.test_plan_screen_calendar_export import (
    THURSDAY,
    FakeClient,
    _App,
    _block,
    _drawn_texts,
    _export,
    manager,  # noqa: F401 - fixture
    root,  # noqa: F401 - fixture
    settings,  # noqa: F401 - fixture
)

TEN = 4  # 10:00 is box 4 of the default 08:00 day


def _commitment(start, end, *, event_id="ev1", title="Board meeting", can_edit=False,
                is_all_day=False, day=THURSDAY):
    return CalendarCommitment(
        event_id=event_id, calendar_id="primary", commitment_date=day,
        start_time=format_hhmm(start), end_time=format_hhmm(end),
        start_minutes=start, end_minutes=end, title=title,
        can_edit=can_edit, is_all_day=is_all_day,
    )


def _event(event_id="ev1", start=(10, 0), end=(10, 30), summary="Board meeting"):
    """An event at local wall-clock times: the screen reads in the machine's zone."""
    def moment(hour_minute):
        return datetime(2026, 11, 5, *hour_minute).astimezone().isoformat()

    return {
        "id": event_id, "summary": summary, "organizer": {"self": True},
        "start": {"dateTime": moment(start)},
        "end": {"dateTime": moment(end)},
    }


class CountingFactory:
    """A client factory that counts how often the screen asked for a client."""

    def __init__(self, events=(), error=None):
        self.calls = 0
        self.events = list(events)
        self.error = error

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self

    def list_events_between(self, time_min, time_max, calendar_id="primary"):
        return [dict(e) for e in self.events]


@pytest.fixture
def ready(monkeypatch):
    """Set the D13 gate: libraries, credentials and a token present, or not."""

    def set_ready(libraries=True, credentials=True, token=True):
        monkeypatch.setattr(gc.GoogleCalendarManager, "is_available", staticmethod(lambda: libraries))
        monkeypatch.setattr(gc.GoogleCalendarManager, "has_credentials",
                            staticmethod(lambda *a, **k: credentials))
        monkeypatch.setattr(gc.GoogleCalendarManager, "check_token_validity",
                            staticmethod(lambda *a, **k: {"exists": token, "valid": token}))

    set_ready()
    return set_ready


@pytest.fixture
def factory():
    return CountingFactory()


def _open(root, manager, settings, factory):
    panel = PlanScreen(root, manager, _App(settings))
    panel.calendar_client_factory = factory
    panel.selected_date = THURSDAY
    panel.refresh()
    root.update_idletasks()
    return panel


@pytest.fixture
def screen(root, manager, settings, factory, ready):
    return _open(root, manager, settings, factory)


def _hold(manager, *commitments, at="2026-11-05T09:00:00"):
    manager.replace_commitments_for_dates([THURSDAY], list(commitments), at)


def _read(screen, root, *, automatic=False):
    started = screen.refresh_calendar(automatic=automatic)
    thread = getattr(screen, "_refresh_thread", None)
    if started and thread is not None:
        thread.join(timeout=30)
        assert not thread.is_alive(), "the calendar read did not finish"
        screen._poll_refresh()
    root.update_idletasks()
    return started


def _box(screen, index):
    return dict((i, frame) for frame, i in screen._slot_frames)[index]


def _chips(widget):
    found = []
    for child in widget.winfo_children():
        if hasattr(child, "stripe"):
            found.append(child)
        found.extend(_chips(child))
    return found


# =====================================================================
# M5 -- opening, Refresh, and the automatic read
# =====================================================================


def test_cipm51_opening_plan_makes_no_call(root, manager, settings, factory, ready):
    """CIP-M5.1 -- the screen paints from the cache; the client is not built."""
    _hold(manager, _commitment(600, 630))

    screen = _open(root, manager, settings, factory)
    root.update()

    assert factory.calls == 0
    assert "10:00–10:30  Board meeting" in _drawn_texts(_box(screen, TEN))


def test_cipm52_refresh_disables_first(screen, root, factory, ready, monkeypatch):
    """CIP-M5.2 -- disabled before anything fallible runs; back on success and refusal."""
    seen = []
    monkeypatch.setattr(
        gc.GoogleCalendarManager, "is_available",
        staticmethod(lambda: seen.append(screen.btn_refresh_calendar.cget("state")) or True),
    )

    assert _read(screen, root) is True
    assert seen == ["disabled"]
    assert screen.btn_refresh_calendar.cget("state") == "normal"

    ready(credentials=False)
    assert _read(screen, root) is False
    assert screen.btn_refresh_calendar.cget("state") == "normal"
    assert factory.calls == 1


def test_cipm52_a_rebuilt_screen_sees_the_fetch_in_flight(root, manager, settings, factory, ready):
    """CIP-M5.2 / D10 -- a screen built mid-read comes up disabled, and re-enables after."""
    path = manager.db.db_path
    assert pc.claim_refresh(path)
    try:
        screen = _open(root, manager, settings, factory)
        assert screen.btn_refresh_calendar.cget("state") == "disabled"
        assert screen._claim_watch_id is not None
    finally:
        pc.release_refresh(path)

    screen._watch_claim()

    assert screen.btn_refresh_calendar.cget("state") == "normal"


def test_cipm53_a_second_fetch_of_the_same_range_is_refused(screen, root, factory):
    """CIP-M5.3 -- one read per database at a time; the second is said, not queued."""
    path = screen.db_manager.db.db_path
    assert pc.claim_refresh(path)
    try:
        assert _read(screen, root) is False
    finally:
        pc.release_refresh(path)

    assert factory.calls == 0
    assert screen.status_label.cget("text") == (
        "The calendar is already being read — wait for that to finish"
    )
    assert screen.btn_refresh_calendar.cget("state") == "normal"


@pytest.mark.parametrize("state, expected", [
    ("never", "Calendar not read for this day"),
    ("read", "Calendar as of 09:00"),
    ("failed", "Calendar read failed — 503 (showing what was known at 09:00)"),
    ("partial", "Calendar as of 09:00 — not read: team"),
])
def test_cipm54_the_age_of_the_answer_is_shown(screen, manager, state, expected):
    """CIP-M5.4 -- the line above the grid says how old the answer is.

    Read "today", so the time is shown alone; another day's read shows its
    date (``test_cipm54_an_answer_from_another_day_shows_its_date``).
    """
    today_at_nine = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    if state in ("read", "failed"):
        _hold(manager, at=today_at_nine.isoformat())
    if state == "partial":
        manager.replace_commitments_for_dates(
            [THURSDAY], [], today_at_nine.isoformat(), warning="not read: team"
        )
    if state == "failed":
        manager.record_commitment_fetch_failure([THURSDAY], "503", "2026-11-05T09:30:00")

    screen.load_blocks()

    assert screen.calendar_age_label.cget("text") == expected


def test_cipm22_a_lapsed_sign_in_is_reported(screen, root, factory):
    """CIP-M2.2 -- the sign-in failure is a sentence on the status line, not a traceback."""
    factory.error = gc.AuthenticationRequired("token expired")

    _read(screen, root)

    assert screen.status_label.cget("text") == not_connected_message()
    assert screen.btn_refresh_calendar.cget("state") == "normal"


def test_cipm55_a_stale_day_refreshes_once(screen, root, factory, monkeypatch):
    """CIP-M5.5 / D13 -- a date never read is read once, in the background."""
    factory.events = [_event()]
    assert screen._auto_refresh_id is not None, "a never-read date was not scheduled"
    monkeypatch.setattr(screen, "winfo_ismapped", lambda: True)

    assert screen._auto_refresh_due(THURSDAY) is True
    screen._refresh_thread.join(timeout=30)
    screen._poll_refresh()

    assert factory.calls == 1
    assert screen.status_label.cget("text") == ""
    assert screen.calendar_age_label.cget("text").startswith("Calendar as of ")
    assert "10:00–10:30  Board meeting" in _drawn_texts(_box(screen, TEN))
    assert screen._auto_refresh_due(THURSDAY) is False
    assert factory.calls == 1


def test_cipm55_no_credentials_means_no_auto_refresh(root, manager, settings, factory, ready):
    """D13 -- without credentials.json the screen of a machine without Google is unchanged."""
    ready(credentials=False)

    screen = _open(root, manager, settings, factory)

    assert screen._auto_refresh_id is None
    assert factory.calls == 0


def test_cipm55_a_failed_auto_refresh_is_not_retried(screen, root, factory, monkeypatch):
    """D13 -- once per date per process, whether the read worked or not."""
    factory.error = CommitmentFetchError("every calendar refused")
    monkeypatch.setattr(screen, "winfo_ismapped", lambda: True)
    assert screen._auto_refresh_due(THURSDAY) is True
    screen._refresh_thread.join(timeout=30)
    screen._poll_refresh()
    assert screen.calendar_age_label.cget("text").startswith("Calendar read failed")

    screen.load_blocks()

    assert screen._auto_refresh_id is None
    assert factory.calls == 1


# =====================================================================
# M3 -- drawing, refusing, dismissing
# =====================================================================


def test_cipm33_every_refusal_has_a_sentence():
    """CIP-M3.3 -- a refusal the screen cannot word reads as a bug."""
    reasons = {v for k, v in vars(SlotRefusal).items() if k.isupper()}
    assert reasons <= set(REFUSAL_TEXT)
    assert REFUSAL_TEXT[SlotRefusal.SLOT_COMMITTED] == (
        "A calendar event holds that Time Block — try another one"
    )


def test_cipm33_the_free_slot_finders_skip_committed_slots(screen, manager):
    """CIP-M3.3 -- the finders and the drop check ask the same question the writers do."""
    _hold(manager, _commitment(480, 510))  # 08:00, box 0
    screen.load_blocks()
    item = ActionItem(who="Me", title="Write", start_date=THURSDAY)
    manager.create_action_item(item)

    assert screen.first_clear_slot(30) == 1
    assert screen.first_free_slot(30) == 1
    assert screen._drop_refusal(item, 0) == REFUSAL_TEXT[SlotRefusal.SLOT_COMMITTED]


def test_cipd12_an_overlapping_block_is_marked_and_counted(screen, manager):
    """D12 -- planned work a meeting has landed on stays, and says so."""
    block = _block(manager, TEN, label="Deep work")
    _hold(manager, _commitment(600, 630))

    screen.load_blocks()

    texts = _drawn_texts(_box(screen, TEN))
    assert pc.CONFLICT_TEXT in texts
    assert "Deep work" in " ".join(texts)
    assert "1 block overlaps a meeting" in screen.day_summary.cget("text")
    assert manager.get_time_block(block.id).slot_index == TEN


def test_cipd12_the_export_still_sends_it(screen, root, manager):
    """D12 -- the exporter does not consult commitments; the block still goes out."""
    _block(manager, TEN, label="Deep work")
    _hold(manager, _commitment(600, 630))
    client = FakeClient()
    screen.calendar_client_factory = lambda: client
    screen.load_blocks()

    _export(screen, root)

    assert [summary for summary, _start, _cal in client.created] == ["Deep work"]


def test_cipd4_a_commitment_past_the_last_box_is_listed_in_the_strip(screen, manager):
    """D4 -- 23:30 to midnight has no box; the strip lists it with its times."""
    _hold(manager, _commitment(1380, 1440, title="Late call"))

    screen.load_blocks()

    assert [lbl.cget("text") for lbl in screen._strip_labels] == [
        "23:00–24:00  Late call (part of it is outside the grid)"
    ]


def test_cipm34_an_editable_commitment_offers_no_dismiss(screen):
    """CIP-M3.4 / D9 -- the user's own meeting is changed in Google, not ignored here."""
    entries = screen.commitment_menu_entries(_commitment(600, 630, can_edit=True))

    assert entries == [("Change this meeting in Google Calendar, then Refresh", None)]


def test_cipm34_a_dismissed_commitment_is_drawn_as_ignored(screen, manager, factory):
    """CIP-M3.4 -- ignored for its date, still drawn, the box free; Google untouched."""
    _hold(manager, _commitment(600, 630))
    screen.load_blocks()
    [(label, command)] = screen.commitment_menu_entries(manager.get_commitments(THURSDAY)[0])
    assert label == "Ignore on this day (stays on your calendar)"

    command()

    assert "(ignored) 10:00–10:30  Board meeting" in _drawn_texts(_box(screen, TEN))
    assert screen._committed == frozenset()
    assert screen.status_label.cget("text").startswith("Ignoring “Board meeting”")
    assert factory.calls == 0


def test_cipm35_the_day_summary_does_not_count_a_commitment(screen, manager):
    """CIP-M3.5 -- a meeting is not a block: no box used, no time occupied."""
    screen.load_blocks()
    before = screen.day_summary.cget("text")
    _hold(manager, _commitment(600, 660))

    screen.load_blocks()

    assert screen.day_summary.cget("text") == before


def test_cipm36_a_commitment_is_drawn_with_its_times(screen, manager):
    """CIP-M3.6 -- true clock times, and a continuation mark in its second box."""
    _hold(manager, _commitment(615, 660))  # 10:15--11:00, boxes 4 and 5

    screen.load_blocks()

    assert "10:15–11:00  Board meeting" in _drawn_texts(_box(screen, TEN))
    assert "↳ Board meeting" in _drawn_texts(_box(screen, TEN + 1))


def test_cipm36_its_colour_is_the_commitment_token_not_a_priority_fill(screen, manager):
    """CIP-M3.6 -- its own token, on the plain surface; never a priority colour."""
    _hold(manager, _commitment(600, 630))

    screen.load_blocks()

    palette = semantic_colors()
    [chip] = _chips(_box(screen, TEN))
    assert chip.stripe.cget("fg_color") == palette["commitment"]
    assert _box(screen, TEN).cget("fg_color") == palette["surface"]


def test_cipm38_all_day_events_are_in_the_strip(screen, manager):
    """CIP-M3.8 -- an all-day event holds no box and is listed above the grid."""
    _hold(manager, _commitment(0, 0, title="Conference", is_all_day=True))

    screen.load_blocks()

    assert [lbl.cget("text") for lbl in screen._strip_labels] == ["All day · Conference"]
    assert screen._committed == frozenset()


def test_cipm39_both_overlapping_commitments_are_drawn(screen, manager):
    """CIP-M3.9 -- two meetings in one box are both shown."""
    _hold(manager, _commitment(600, 630, event_id="a", title="One"),
          _commitment(600, 660, event_id="b", title="Two"))

    screen.load_blocks()

    texts = _drawn_texts(_box(screen, TEN))
    assert "10:00–10:30  One" in texts
    assert "10:00–11:00  Two" in texts
    assert screen._committed == frozenset({TEN, TEN + 1})


def test_cipm34_an_ignored_meeting_before_the_day_is_listed_and_can_be_held_again(
    screen, manager, monkeypatch
):
    """CIP-M3.4 -- ignored, it no longer widens the day; the strip shows it, with its menu."""
    _hold(manager, _commitment(420, 450, title="Standup"))  # 07:00, Day Start 08:00
    screen.load_blocks()
    assert "07:00–07:30  Standup" in _drawn_texts(screen.blocks_scroll)
    [(_label, ignore)] = screen.commitment_menu_entries(manager.get_commitments(THURSDAY)[0])

    bound = []
    monkeypatch.setattr(screen, "bind_commitment_handlers",
                        lambda widget, commitment: bound.append((widget, commitment.title)))

    ignore()

    [line] = screen._strip_labels
    assert line.cget("text") == "(ignored) 07:00–07:30  Standup (outside the drawn day)"
    assert (line, "Standup") in bound
