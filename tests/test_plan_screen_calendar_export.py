"""CE-M4 — the Plan screen's Google Calendar button, wired to the export.

Purpose: prove the control exists on the screen the user actually uses, that
         it refuses clearly, and that it reports the real counts.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#m4
Tests:   this file

Real Tk, and a real database, for the reason the rest of this screen's tests
give: a button that is drawn and not connected is exactly the failure this
screen has had before (P25 — a check reachable from only one surface, and not
the one anyone uses).

**No test here reaches the network, and none takes the `mapped_windows`
fixture.** The client factory is replaced on the screen, the prerequisite
checks are monkeypatched on `GoogleCalendarManager`, and every assertion is
about widget state, a status string or a recorded call — so the whole file
still runs in the local workflow CLAUDE.md documents, which is where this
wiring most needs proving.

The worker thread is joined rather than waited on with a sleep, and the Tk
callbacks it queues are drained with `update()`, so nothing here is timing
dependent.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import customtkinter as ctk
import pytest

from src.getmoredone import google_calendar as gc
from src.getmoredone.app_settings import AppSettings
from src.getmoredone.calendar_exporter import (
    BLOCK_DATE_PROPERTY,
    BLOCK_ID_PROPERTY,
    ExportOutcome,
)
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem, BlockType, TimeBlock
from src.getmoredone.screens import plan as plan_module
from src.getmoredone.screens.plan import PlanScreen
from src.getmoredone.theme import status_text_color
from src.getmoredone.time_block_layout import DayBounds

THURSDAY = "2026-11-05"
FRIDAY = "2026-11-06"
BOUNDS = DayBounds()


class _App:
    """The slice of the app object PlanScreen actually reads."""

    def __init__(self, settings):
        self.settings = settings


class FakeClient:
    """Records the calls the exporter makes, and never leaves the process."""

    def __init__(self):
        self.created = []
        self.listed = []
        self.deleted = []
        self._next = 0

    def create_event(self, *, summary, start_datetime, duration_minutes,
                     description=None, calendar_id="primary",
                     private_properties=None, reminders=None):
        self._next += 1
        self.created.append((summary, start_datetime, calendar_id))
        return {"id": f"evt-{self._next}"}

    def update_event(self, **kwargs):  # pragma: no cover - nothing here updates
        raise AssertionError("no test in this file should update an event")

    def delete_event(self, event_id, calendar_id="primary"):
        self.deleted.append((event_id, calendar_id))

    def list_day_events(self, block_date, calendar_id="primary"):
        self.listed.append((block_date, calendar_id))
        return []


class CalendarWithStrayEvents(FakeClient):
    """A calendar still holding events this app made for blocks since deleted."""

    def __init__(self, events):
        super().__init__()
        self._events = list(events)

    def list_day_events(self, block_date, calendar_id="primary"):
        self.listed.append((block_date, calendar_id))
        return [dict(event) for event in self._events]


def _stray(event_id, block_id, block_date=THURSDAY):
    return {
        "id": event_id,
        "summary": "Reading",
        "extendedProperties": {
            "private": {
                BLOCK_ID_PROPERTY: block_id,
                BLOCK_DATE_PROPERTY: block_date,
            }
        },
    }


class ExplodingClient(FakeClient):
    def create_event(self, **kwargs):
        raise RuntimeError("503 Service Unavailable")


@pytest.fixture
def manager(tmp_path):
    """Every DatabaseManager in this suite gets an explicit tmp_path database.

    The default path resolves to the user's real application database, and
    __init__ runs migrations against it.
    """
    db = DatabaseManager(str(tmp_path / "plan_export.db"))
    yield db
    db.close()


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Settings that save to tmp_path, never to the user's real settings file."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))
    return AppSettings()


@pytest.fixture
def root():
    window = ctk.CTk()
    yield window
    window.destroy()


@pytest.fixture(autouse=True)
def prerequisites_met(monkeypatch):
    """Google's libraries and credentials are present, without either being real.

    Both are static methods that touch the filesystem (and, in the import
    case, the installed packages); a test about the button's wiring should not
    also be a test of this developer's machine.
    """
    monkeypatch.setattr(gc.GoogleCalendarManager, "is_available", staticmethod(lambda: True))
    monkeypatch.setattr(
        gc.GoogleCalendarManager, "has_credentials", staticmethod(lambda *a, **k: True)
    )
    # A token on disk, without one existing: the export refuses when there is
    # none, because the real client authenticates in ``__init__`` and the
    # consent flow blocks on a browser from a worker thread.
    monkeypatch.setattr(
        gc.GoogleCalendarManager,
        "check_token_validity",
        staticmethod(lambda *a, **k: {"exists": True, "valid": True}),
    )


@pytest.fixture
def screen(root, manager, settings):
    """A Plan screen on the default Thursday, with a client that cannot dial out."""
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.calendar_client_factory = FakeClient
    panel.refresh()
    root.update_idletasks()
    return panel


def _block(manager, slot, label="Reading", block_date=THURSDAY,
           block_type=BlockType.BREAK, item_id=None, minutes=30):
    block = TimeBlock(
        block_date=block_date, start_time="", end_time="",
        planned_minutes=minutes, label=label, block_type=block_type,
        item_id=item_id,
    )
    return manager.add_block_at(block, slot, BOUNDS)


def _export(screen, root):
    """Click the button, let the worker finish, and collect its result.

    `_poll_export` is called directly rather than waited for: it is what the
    scheduled callback runs, and a test that waited on Tk's timer would be
    asserting on the clock. That the scheduling happened at all is asserted
    separately, in test_cem413.
    """
    screen.export_day_to_calendar()
    thread = getattr(screen, "_export_thread", None)
    if thread is not None:
        thread.join(timeout=30)
        assert not thread.is_alive(), "the export worker did not finish"
        screen._poll_export()
    root.update_idletasks()
    return screen.status_label.cget("text")


def _drawn_texts(widget):
    """Every label string under a widget, however deeply nested."""
    found = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            found.append(child.cget("text"))
        found.extend(_drawn_texts(child))
    return found


def test_cem221a_an_event_is_titled_what_the_day_draws_on_the_block(screen, manager):
    """CE-M2.2 — the contract between the screen and the export, behaviourally.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m22
    Tests: this test

    The headless test of this in `tests/test_calendar_export.py` compares the
    exporter's titles to literal strings. It used to compare them to
    `plan_blocks._block_title`, which is a one-line delegation to the function
    the exporter itself calls — true for any implementation, including a
    broken one, as a cold review pass pointed out. What can actually drift is
    the screen: if the day pane stopped calling `block_title`, a calendar
    event would be named something the day does not show. So this reads the
    text Tk has drawn.
    """
    item_id = manager.create_action_item(
        ActionItem(who="Me", title="Call the bank")
    )
    _block(manager, 0, item_id=item_id, label=None, block_type=BlockType.ITEM)
    _block(manager, 2, label=None, block_type=BlockType.BUFFER)
    client = FakeClient()
    screen.calendar_client_factory = lambda: client
    screen.refresh()
    screen.winfo_toplevel().update_idletasks()

    drawn = _drawn_texts(screen)

    assert "Call the bank" in drawn, (
        f"the day does not draw the item's title: {drawn}"
    )
    assert "Buffer" in drawn, f"the day does not draw the buffer's name: {drawn}"

    status = _export(screen, screen.winfo_toplevel())
    sent = sorted(summary for summary, _start, _cal in client.created)

    assert sent == ["Buffer", "Call the bank"], status
    for summary in sent:
        assert summary in drawn, (
            f"an event went out titled {summary!r}, which is not on the day: {drawn}"
        )


# --- CE-M4.1 — the button --------------------------------------------------

def test_cem411_the_button_disables_before_the_work_starts(screen, manager, monkeypatch):
    """CE-M4.1 — disabled before anything slow or fallible runs.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m41
    Tests: this test

    Asserted from inside the first thing the handler calls after disabling the
    button, which is the only place the intermediate state exists: by the time
    the handler returns, the worker may already have re-enabled it.
    """
    _block(manager, 0)
    seen = {}

    real_is_available = gc.GoogleCalendarManager.is_available

    def peek():
        seen["state"] = screen.btn_export_calendar.cget("state")
        return real_is_available()

    monkeypatch.setattr(gc.GoogleCalendarManager, "is_available", staticmethod(peek))

    _export(screen, screen.winfo_toplevel())

    assert seen["state"] == "disabled", (
        "the button must be disabled before the export does anything, not "
        "after it comes back"
    )


def test_cem412_the_button_is_re_enabled_when_the_worker_finishes(screen, manager):
    """CE-M4.1 — and comes back, so a second export is possible."""
    _block(manager, 0)

    _export(screen, screen.winfo_toplevel())

    assert screen.btn_export_calendar.cget("state") == "normal"
    assert screen._export_running is False


def test_cem413_the_result_is_collected_by_a_callback_the_tk_thread_scheduled(
    screen, manager, monkeypatch
):
    """CE-M4.1 — the worker never touches a widget, including through `after`.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test

    Tk is not thread-safe and `after` is no exception: scheduling from the
    worker calls into the Tcl interpreter from a second thread, which wedges a
    process with no mainloop and is undefined behaviour in one that has. So
    the poll is scheduled here, on the thread that owns the widgets, before
    the worker can finish.

    No thread is started. The worker body is captured and then run on *this*
    thread, with `after` and `set_status` made to raise, which proves the
    claim directly: whatever the worker does, it is not a widget call. An
    earlier version of this test started the real thread, joined it with a
    30-second timeout and asserted on the state afterwards; that made a
    wall-clock assumption, and it failed intermittently in long runs with a
    message about `_export_running` that said nothing about the clock.
    """
    _block(manager, 0)
    captured = {}

    class RecordingThread:
        """Captures the worker instead of running it."""

        def __init__(self, *, target, daemon=False):
            captured["target"] = target
            captured["daemon"] = daemon

        def start(self):
            captured["started"] = True

        def is_alive(self):  # pragma: no cover - the poll is not reached here
            return True

    monkeypatch.setattr(
        plan_module, "threading", SimpleNamespace(Thread=RecordingThread)
    )

    screen.export_day_to_calendar()

    # Scheduled by this thread, before the worker has run a single line.
    assert screen._export_poll_id is not None, (
        "the Tk thread must schedule the collection itself"
    )
    assert captured["started"] is True
    assert captured["daemon"] is True, "a non-daemon worker would hold the app open"
    assert screen._export_result is None

    def forbidden(*args, **kwargs):
        raise AssertionError("the worker called into Tk")

    monkeypatch.setattr(screen, "after", forbidden)
    monkeypatch.setattr(screen, "set_status", forbidden)

    captured["target"]()

    kind, payload = screen._export_result
    assert kind == "outcome", f"the worker reported {kind}: {payload}"
    assert payload.created == 1


def test_cem413a_pending_tk_finalizers_run_before_the_worker_starts(
    screen, manager, monkeypatch
):
    """CE-M4.1 — the collection happens on the thread that owns Tk.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test

    A CustomTkinter widget makes a ``tkinter.font.Font``, and a destroyed
    screen's fonts become garbage whose ``__del__`` calls into Tcl. The
    collection that runs those finalizers happens on whichever thread next
    allocates; when that is the export worker, the Tcl call blocks and the
    export never reports back. This run caught that stack for real --
    ``tkinter/font.py __del__`` under ``DatabaseManager.__init__`` under the
    worker -- and the join timed out. So the collection is forced here first,
    where the finalizers are safe, and the order is what matters: before the
    thread exists, not after.
    """
    _block(manager, 0)
    order = []

    class RecordingThread:
        def __init__(self, *, target, daemon=False):
            self.target = target

        def start(self):
            order.append("start")

    monkeypatch.setattr(
        plan_module, "gc", SimpleNamespace(collect=lambda *a, **k: order.append("collect"))
    )
    monkeypatch.setattr(
        plan_module, "threading", SimpleNamespace(Thread=RecordingThread)
    )

    screen.export_day_to_calendar()

    assert order == ["collect", "start"], (
        "the Tk thread must run pending finalizers before the worker can "
        f"allocate; got {order}"
    )


def test_cem414_a_worker_that_vanishes_still_gives_the_button_back(screen):
    """CE-M4.1 — the poll's last resort.

    The worker has a top-level guard, so this is close to unreachable. If it
    is ever reached, a disabled button and a status line stuck on "Exporting…"
    is the worst way for the user to find out.
    """
    screen._export_running = True
    screen._export_result = None
    screen._export_thread = None
    screen.btn_export_calendar.configure(state="disabled")

    screen._poll_export()

    assert screen.btn_export_calendar.cget("state") == "normal"
    assert "without reporting" in screen.status_label.cget("text")


def test_cem412a_a_second_click_while_running_does_nothing(screen, manager):
    """CE-M4.1 — the server-side half of the guard, not just the grey button.

    A disabled button cannot be clicked, but the command can still be invoked
    (a keyboard binding, a test, a later caller), and two exports of one day
    racing each other would both create events for the same blocks.
    """
    _block(manager, 0)
    screen._export_running = True
    screen.set_status("", "muted")

    screen.export_day_to_calendar()

    assert screen.status_label.cget("text") == ""
    assert getattr(screen, "_export_thread", None) is None


# --- CE-M4.2 — the status line ---------------------------------------------

def test_cem421_the_status_line_reports_the_real_counts(screen, manager, root):
    """CE-M4.2 — the counts come from the outcome, not from a hopeful string.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test
    """
    _block(manager, 0, label="Reading")
    _block(manager, 2, label="Walk")

    status = _export(screen, root)

    assert "2 of 2" in status
    assert "2 new" in status
    assert screen.status_label.cget("text_color") == status_text_color("success")


def test_cem422_a_failing_export_sets_an_error_status(root, manager, settings):
    """CE-M4.2 — a run that failed every block has finished, and is not a success.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test
    """
    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.calendar_client_factory = ExplodingClient
    panel.refresh()
    _block(manager, 0, label="Reading")

    status = _export(panel, root)

    assert "FAILED" in status
    assert "503" in status
    assert panel.status_label.cget("text_color") == status_text_color("error")
    assert panel.btn_export_calendar.cget("state") == "normal", (
        "a failed export must still give the button back"
    )


def test_cem422a_an_exception_from_the_client_is_reported_not_swallowed(
    root, manager, settings
):
    """CE-M4.2 / P15 — the worker's top-level guard.

    A client that cannot even be constructed raises before the exporter is
    reached. Without the guard the thread dies silently and the button never
    comes back.
    """
    def cannot_connect():
        raise RuntimeError("token.pickle is unreadable")

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.calendar_client_factory = cannot_connect
    panel.refresh()
    _block(manager, 0)

    status = _export(panel, root)

    assert "token.pickle is unreadable" in status
    assert panel.btn_export_calendar.cget("state") == "normal"
    assert panel.status_label.cget("text_color") == status_text_color("error")


# --- CE-M4.3 — refusals ----------------------------------------------------

def test_cem423_a_screen_that_is_gone_is_not_written_to(screen, monkeypatch):
    """CE-M4.2 / P15 — navigating away mid-export must not raise in a callback.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test

    `clear_content` destroys the screen on every navigation, and the outcome
    arrives afterwards. Found by a cold review pass: both reporters
    configured the button and the status label with no liveness check.
    """
    written = []
    monkeypatch.setattr(screen, "set_status", lambda *a, **k: written.append(a))
    monkeypatch.setattr(
        screen.btn_export_calendar, "configure", lambda *a, **k: written.append(k)
    )
    screen.destroy()

    screen._report_export(
        ExportOutcome(block_date=THURSDAY, blocks_seen=1, created=1)
    )
    screen._finish_export_refusal("whatever went wrong")

    assert written == [], (
        "a destroyed screen was written to: both reporters have to return "
        f"before they touch a widget, and these calls got through: {written}"
    )
    assert screen._export_running is False, (
        "the flag is a plain attribute and is set before the guard, so it "
        "stays honest either way"
    )


def test_cem425_a_result_that_lands_between_the_two_reads_is_not_called_a_failure(
    screen,
):
    """CE-M4.2 / P1 — a transient read of `None` is not a terminal failure.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test

    The worker sets `_export_result` and then exits, so there is a window
    between the poller's read of the attribute and its `is_alive()` check in
    which a successful export looks like a worker that died silently. Both
    cold review passes flagged the ordering. Driven here by a thread stub that
    reports dead and writes the result on the way: that is exactly the
    interleaving, made deterministic.
    """
    outcome = ExportOutcome(block_date=THURSDAY, blocks_seen=1, created=1)

    class DeadThreadThatJustFinished:
        """`is_alive()` is False, and the result appears as it is asked."""

        def is_alive(self):
            screen._export_result = ("outcome", outcome)
            return False

    screen._export_result = None
    screen._export_thread = DeadThreadThatJustFinished()

    screen._poll_export()

    status = screen.status_label.cget("text")
    assert "stopped without reporting a result" not in status, (
        "a successful export was reported as a worker that vanished"
    )
    assert "1 of 1 block(s) exported" in status, status
    assert screen.status_label.cget("text_color") == status_text_color("success")


def test_cem424_destroying_the_screen_cancels_the_poll(screen, monkeypatch):
    """CE-M4.2 / P15 — the queued callback does not outlive its widgets.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
    Tests: this test

    Tk does not cancel a widget's `after` jobs when the widget is destroyed.
    """
    screen._export_poll_id = screen.after(60_000, lambda: None)
    pending = screen._export_poll_id
    # CIP D13: with credentials present the screen has also queued its
    # automatic calendar read, and destroy cancels that too.
    commitment_jobs = [
        getattr(screen, name) for name in ("_refresh_poll_id", "_auto_refresh_id", "_claim_watch_id")
        if getattr(screen, name, None) is not None
    ]
    cancelled = []
    monkeypatch.setattr(screen, "after_cancel", cancelled.append)

    screen.destroy()

    assert cancelled == [pending] + commitment_jobs
    assert screen._export_poll_id is None


def test_cem431_missing_credentials_refuses_with_the_setup_message(
    screen, manager, monkeypatch
):
    """CE-M4.3 — the message names the path that was checked.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m43
    Tests: this test
    """
    from src.getmoredone.screens.calendar_dialog import missing_credentials_message

    _block(manager, 0)
    monkeypatch.setattr(
        gc.GoogleCalendarManager, "has_credentials", staticmethod(lambda *a, **k: False)
    )

    status = _export(screen, screen.winfo_toplevel())

    assert status == missing_credentials_message()
    assert screen.btn_export_calendar.cget("state") == "normal"
    assert getattr(screen, "_export_thread", None) is None, "nothing should have run"


def test_cem432_missing_libraries_refuses(screen, manager, monkeypatch):
    """CE-M4.3 — and says how to fix it."""
    _block(manager, 0)
    monkeypatch.setattr(
        gc.GoogleCalendarManager, "is_available", staticmethod(lambda: False)
    )

    status = _export(screen, screen.winfo_toplevel())

    assert "not installed" in status
    assert "requirements.txt" in status
    assert screen.btn_export_calendar.cget("state") == "normal"


def test_cem434_an_unconnected_account_refuses_rather_than_opening_a_browser(
    screen, monkeypatch
):
    """CE-M4.3 — credentials present, no token: refuse before the thread.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m43
    Tests: this test

    Found by a cold review pass. ``has_credentials`` only tests that
    ``credentials.json`` exists; the real client's ``__init__`` runs the OAuth
    consent flow, which blocks on a browser with no timeout — on the export's
    worker thread, with the button already disabled and the status already
    reading "Exporting…". A user who closed the consent tab had no way back.
    """
    monkeypatch.setattr(
        gc.GoogleCalendarManager,
        "check_token_validity",
        staticmethod(lambda *a, **k: {"exists": False, "valid": None}),
    )
    _block(screen.db_manager, 0)

    screen.export_day_to_calendar()

    assert getattr(screen, "_export_thread", None) is None, (
        "the worker must not start: constructing the client is what opens the "
        "browser, and it would do it off the Tk thread"
    )
    status = screen.status_label.cget("text")
    assert "not connected" in status
    assert "token.pickle" in status, (
        "the message names the file that was checked, as the credentials one does"
    )
    assert screen.btn_export_calendar.cget("state") == "normal"


def test_cem435_a_worker_that_cannot_be_started_gives_the_button_back(
    screen, monkeypatch
):
    """CE-M4.3 — the guard covers the whole method, not the checks only.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m43
    Tests: this test

    Found by a cold review pass: six statements, `threading.Thread(...).start()`
    among them, ran outside the `try` with the button already disabled and
    nothing scheduled to re-enable it. `RuntimeError: can't start new thread`
    is the real version of this.
    """
    class RefusingThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            raise RuntimeError("can't start new thread")

    monkeypatch.setattr(plan_module, "threading", SimpleNamespace(Thread=RefusingThread))
    _block(screen.db_manager, 0)

    screen.export_day_to_calendar()

    assert screen.btn_export_calendar.cget("state") == "normal", (
        "a button left disabled with no explanation is the one outcome the "
        "user cannot do anything about"
    )
    assert screen._export_running is False
    status = screen.status_label.cget("text")
    assert "Could not start the export" in status
    assert "can't start new thread" in status, status


def test_cem433_an_empty_day_runs_the_export_and_says_nothing_was_there(screen):
    """CE-M4.3 — the empty day is reported by the exporter, not refused.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m43
    Tests: this test

    This asserted the opposite until a cold review pass: the screen used to
    refuse before starting, which also skipped the orphan sweep (see
    `test_cem433a`). The behaviour changed on purpose; the message the user
    reads for a genuinely empty day did not.
    """
    status = _export(screen, screen.winfo_toplevel())

    assert "Nothing to export" in status
    assert THURSDAY in status
    assert screen.status_label.cget("text_color") == status_text_color("muted"), (
        "an empty day is not an error the user has to act on"
    )
    assert getattr(screen, "_export_thread", None) is not None, (
        "the export has to run to find out whether anything is out there"
    )


def test_cem433a_clearing_a_day_takes_its_events_off_the_calendar(screen):
    """CE-M4.3 / CE-M2.6 — the case the old refusal made unreachable.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests: this test

    Export a day, then clear it, then export again: the events have to go.
    `delete_event` has no caller anywhere but the sweep, so refusing before
    the sweep left them on the user's calendar for good.
    """
    client = CalendarWithStrayEvents([_stray("evt-stray", "a-block-now-deleted")])
    screen.calendar_client_factory = lambda: client

    status = _export(screen, screen.winfo_toplevel())

    assert client.deleted == [("evt-stray", "primary")]
    assert "1 removed" in status
    assert screen.status_label.cget("text_color") == status_text_color("success"), (
        "a run that cleaned up is a run that did something"
    )


# --- CE-M4.4 — wired to the screen the user uses ---------------------------

def test_cem441_the_header_holds_the_export_button_wired_to_the_export(screen):
    """CE-M4.4 — it is in the header, and its command is the export.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    Both halves matter: a button wired to nothing and a working export no
    button reaches are the same bug from the user's side (P21).

    PF-M4 put the header on two rows, so "beside the other day-wide actions"
    is no longer what this asks: the export moved to the tools row, which is
    where the walk asked for it. What is unchanged is that it is *in the
    header*, and that is what this asserts.
    """
    header = screen.header
    assert screen.btn_export_calendar.cget("text") == "⤴ Google Calendar"
    assert screen.btn_export_calendar.cget("command") is not None
    assert screen.btn_export_calendar._command == screen.export_day_to_calendar
    assert screen.btn_export_calendar.master.master is header, (
        "the export button is not inside the header any more"
    )
    assert screen.btn_export_calendar.master is screen.btn_add_buffer.master, (
        "it belongs on the tools row, with the other buttons that add to the day"
    )


def test_cem441b_the_header_fits_the_window_it_opens_in(screen, root):
    """CE-M4.4 — a seventh button in the header must not squeeze a widget out.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    Found by a cold review pass, and confirmed by measurement: with the status
    label still in the header the header asked for 1203px inside a 1200px
    window. Every widget in it is packed with a fixed width and the status
    label was packed last with no ``expand``, so Tk gave it what was left —
    nothing — and a label squeezed to zero is never mapped. The export's only
    channel for reporting anything would have been invisible at the window's
    own default size.

    Requested widths, not realised ones, so this needs no mapped window: a
    withdrawn window reports ``winfo_width`` as 1, but ``winfo_reqwidth`` is
    what each widget asked for either way, and the sum is what pack has to fit.
    """
    import re

    from src.getmoredone.app import DEFAULT_WINDOW_WIDTH_PX

    screen.pack(fill="both", expand=True)
    root.update_idletasks()

    header = screen.header
    margin = sum(int(v) for v in re.findall(r"\d+", str(header.grid_info()["padx"])))
    if margin and len(re.findall(r"\d+", str(header.grid_info()["padx"]))) == 1:
        margin *= 2
    budget = DEFAULT_WINDOW_WIDTH_PX - margin

    assert header.winfo_reqwidth() <= budget, (
        f"the Plan header asks for {header.winfo_reqwidth()}px inside "
        f"{budget}px. Whatever is packed last loses: trim a width, or take a "
        "widget out of the header the way the status label was taken out"
    )
    assert screen.status_label.master is screen, (
        "the status line belongs on its own row, where a new button cannot "
        "squeeze it to nothing"
    )
    label = screen.btn_export_calendar._text_label
    assert label.winfo_reqwidth() <= screen.btn_export_calendar.winfo_reqwidth(), (
        "the button was narrowed to make the header fit; its own text no "
        "longer fits inside it"
    )


def test_cem441a_the_export_button_is_not_a_second_primary(screen):
    """CE-M4.4 — AutoLoad keeps this screen's only primary colour.

    The project's theme rule allows one primary per screen; a second one makes
    neither of them mean anything.
    """
    assert (
        screen.btn_export_calendar.cget("fg_color")
        != screen.btn_autoload.cget("fg_color")
    )


def test_cem442_the_exported_date_is_the_selected_date(screen, manager, root):
    """CE-M4.4 — the day on screen, not today.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    The screen's date is a picker the user moves. An export that read
    `date.today()` would quietly export the wrong day on every day but one.
    """
    _block(manager, 0, label="Friday's block", block_date=FRIDAY)
    _block(manager, 0, label="Thursday's block", block_date=THURSDAY)
    screen.selected_date = FRIDAY
    screen.refresh()

    _export(screen, root)

    (block,) = manager.get_time_blocks(FRIDAY)
    assert block.calendar_event_id is not None
    assert manager.get_time_blocks(THURSDAY)[0].calendar_event_id is None


def test_cem443_the_configured_calendar_is_the_one_written_to(
    root, manager, settings
):
    """CE-M4.4 / D3 — the setting reaches the client, not just the file.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m31
    Tests: this test
    """
    settings.plan_export_calendar_id = "work@example.com"
    client = FakeClient()

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.calendar_client_factory = lambda: client
    panel.refresh()
    _block(manager, 0, label="Reading")

    _export(panel, root)

    assert [calendar for _, _, calendar in client.created] == ["work@example.com"]
    assert client.listed == [(THURSDAY, "work@example.com")]


def test_cem443a_a_blank_calendar_setting_falls_back_to_primary(
    root, manager, settings
):
    """CE-M4.4 — an empty string in the settings file is not a calendar id."""
    settings.plan_export_calendar_id = "   "
    client = FakeClient()

    panel = PlanScreen(root, manager, _App(settings))
    panel.selected_date = THURSDAY
    panel.calendar_client_factory = lambda: client
    panel.refresh()
    _block(manager, 0)

    _export(panel, root)

    assert [calendar for _, _, calendar in client.created] == ["primary"]


# --- CE-M4.5 — the seam ----------------------------------------------------

def test_cem451_the_screen_uses_its_injected_client_factory(screen, manager, root):
    """CE-M4.5 — and so never builds the authenticating one in a test.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m45
    Tests: this test
    """
    built = []

    def factory():
        client = FakeClient()
        built.append(client)
        return client

    screen.calendar_client_factory = factory
    _block(manager, 0, label="Reading")

    _export(screen, root)

    assert len(built) == 1
    assert [summary for summary, _, _ in built[0].created] == ["Reading"]


def test_cem451a_without_a_factory_the_real_client_is_what_would_be_built(
    screen, monkeypatch
):
    """CE-M4.5 — the default is the real manager, so the seam is not a fork.

    A seam whose default differs from what ships is a second code path, and
    the one the user runs would be the untested one.

    Only ``__init__`` is patched, never ``__new__``: ``__new__`` is inherited
    rather than owned, so ``monkeypatch`` undoes a patch of it by *writing*
    ``object.__new__`` into the class dict, after which every real
    ``GoogleCalendarManager(credentials_file=...)`` in a later test raises
    ``TypeError: object.__new__() takes exactly one argument``. That is how
    this test first broke ``tests/test_first_run.py``.
    """
    screen.calendar_client_factory = None
    constructed = []
    monkeypatch.setattr(
        gc.GoogleCalendarManager, "__init__",
        lambda self, *a, **k: constructed.append(self),
    )

    client = screen.calendar_client()

    assert type(client) is gc.GoogleCalendarManager
    assert constructed == [client]
    # The invariant the old form of this test broke, asserted where it broke:
    # ``__new__`` must stay inherited. A patch of it here is still in force at
    # this line, so re-introducing one fails this assertion rather than some
    # unrelated file three hundred tests later.
    assert "__new__" not in gc.GoogleCalendarManager.__dict__, (
        "GoogleCalendarManager.__new__ is owned by the class; a monkeypatch of "
        "an inherited __new__ leaks object.__new__ into the class dict"
    )


def test_cem452_an_item_block_exports_under_the_items_title(screen, manager, root):
    """CE-M4 end to end — the title the screen draws is the title Google gets."""
    item = ActionItem(who="me", title="Draft the proposal", start_date=THURSDAY)
    manager.create_action_item(item)
    client = FakeClient()
    screen.calendar_client_factory = lambda: client
    _block(manager, 0, label=None, block_type=BlockType.ITEM, item_id=item.id)

    _export(screen, root)

    assert [summary for summary, _, _ in client.created] == ["Draft the proposal"]


def test_cem453_the_status_line_is_built_from_the_outcome_object(screen):
    """CE-M4.2 — the screen reports an outcome it did not compose itself."""
    screen._report_export(
        ExportOutcome(block_date=THURSDAY, blocks_seen=3, created=1, updated=1,
                      skipped_unplaced=1)
    )

    status = screen.status_label.cget("text")
    assert "2 of 3" in status
    assert "not on the grid" in status
    assert screen.btn_export_calendar.cget("state") == "normal"


def test_cem441c_the_exported_time_is_the_box_the_screen_draws(screen, manager):
    """CE-M4.4 — the day's shape goes to the worker with the day.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    Found by a cold review pass. A block's box is stored relative to Day
    Start, so moving Day Start re-times every day on read and leaves the
    stored `start_time` column behind -- `on_settings_saved` deliberately
    writes nothing. The export was reading that column, so a day the screen
    drew from 10:00 went onto other people's calendars from 08:00. This pins
    the whole path: the screen's bounds, through the thread, to the event.

    Fixture changed 2026-11-13, reason (b): PD-M14.7 now puts a block whose
    readable ``start_time`` disagrees with its box back on that time when the
    day loads, so a Day Start change no longer leaves a readable stale column.
    The one it still leaves is a column that cannot be read, so that is what
    this sets up; the export must still use the box.
    """
    block = _block(manager, 0, label="Reading")
    manager.db.conn.execute(
        "UPDATE time_blocks SET start_time = '', end_time = '' WHERE id = ?", (block.id,)
    )
    manager.db.conn.commit()
    client = FakeClient()
    screen.calendar_client_factory = lambda: client

    screen.on_settings_saved(DayBounds(day_start="10:00"))
    screen.winfo_toplevel().update_idletasks()

    stored = manager.get_time_blocks(THURSDAY)[0]
    assert stored.start_time == "", (
        "the fixture has to leave a column the export cannot use for this to prove anything"
    )
    assert "10:00" in _drawn_texts(screen), "the day is not drawn from 10:00"

    status = _export(screen, screen.winfo_toplevel())

    assert [start.strftime("%H:%M") for _s, start, _c in client.created] == ["10:00"], (
        f"the event did not go out at the drawn time: {client.created} ({status})"
    )


# --- CE-M4.4 / E3 — the export's client cannot stop to sign in -------------

def test_cem444a_the_screens_own_client_is_built_non_interactively(screen, monkeypatch):
    """CE-M4.4 — the flag reaches the constructor the export actually uses.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    `__init__` is replaced, not `__new__`: patching `__new__` writes
    `object.__new__` into the class dict when monkeypatch undoes it, and
    `object.__new__` rejects the constructor arguments every later test in the
    session passes — four unrelated failures, in files that never touch this
    one.
    """
    seen = {}

    def record(self, *args, **kwargs):
        seen.update(kwargs)
        self.service = None

    monkeypatch.setattr(gc.GoogleCalendarManager, "__init__", record)
    del screen.calendar_client_factory

    client = screen.calendar_client()

    assert isinstance(client, gc.GoogleCalendarManager)
    assert seen.get("allow_interactive") is False, (
        f"the export's client was built able to open a browser: {seen}"
    )
    assert "__new__" not in gc.GoogleCalendarManager.__dict__, (
        "patching __new__ here leaks object.__new__ into every later test"
    )


def test_cem444b_a_client_that_needs_sign_in_reports_it_and_re_enables(screen, manager):
    """CE-M4.4 — the refusal the non-interactive client raises reaches the user.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    The screen's token check passes here — a token file exists, per the
    autouse fixture — and the client still cannot sign in, which is the
    revoked-or-corrupt case. The status has to name connecting, and the button
    has to come back; "Google Calendar export failed: Google Calendar needs
    you to sign in again, and that cannot be done from here." is the same
    information read as a crash.
    """
    from src.getmoredone.screens.calendar_dialog import not_connected_message

    _block(manager, 0)

    def needs_sign_in():
        raise gc.AuthenticationRequired("sign in again")

    screen.calendar_client_factory = needs_sign_in

    status = _export(screen, screen.winfo_toplevel())

    assert status == not_connected_message()
    assert screen.btn_export_calendar.cget("state") == "normal"
    assert screen._export_running is False


# --- CE-M4.4 — one export per day, across screens --------------------------

def test_cem444c_a_second_screen_cannot_export_the_same_day(root, manager, settings):
    """CE-M4.4 — the in-flight marker outlives the screen that set it.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    Found by a cold review pass. `_export_running` is an attribute of one
    screen, and `App.show_plan` builds a new `PlanScreen` on every
    navigation — so leaving Plan and coming back, while the first export is
    still running, gave a screen that would happily start a second export of
    the same day. The two race over the same rows: the loser writes an event
    id the winner has already replaced, so the block ends up pointing at a
    deleted event, and the user is told twice that it worked.

    The first export is held inside `create_event` on a `threading.Event`
    rather than by sleeping, so the two exports really are in flight at once
    and the test does not depend on the clock.
    """
    _block(manager, 0)
    first = PlanScreen(root, manager, _App(settings))
    first.selected_date = THURSDAY
    second = PlanScreen(root, manager, _App(settings))
    second.selected_date = THURSDAY
    held = threading.Event()
    released = threading.Event()

    class HeldClient(FakeClient):
        def create_event(self, **kwargs):
            held.set()
            assert released.wait(timeout=30), "the held export was never let go"
            return super().create_event(**kwargs)

    blocked = HeldClient()
    first.calendar_client_factory = lambda: blocked
    second_client = FakeClient()
    second.calendar_client_factory = lambda: second_client

    try:
        first.export_day_to_calendar()
        assert held.wait(timeout=30), "the first export never reached the calendar"

        second.export_day_to_calendar()

        assert second._export_thread is None, "a second export of the day started"
        assert "already being exported" in second.status_label.cget("text")
        assert second.btn_export_calendar.cget("state") == "normal"
        assert second_client.created == []
    finally:
        released.set()
        thread = first._export_thread
        if thread is not None:
            thread.join(timeout=30)
        plan_module._release_export(manager.db.db_path, THURSDAY)

    first._poll_export()
    root.update_idletasks()

    assert len(blocked.created) == 1, "the first export did not finish its work"
    assert (str(manager.db.db_path), THURSDAY) not in plan_module._EXPORTS_IN_FLIGHT, (
        "the slot was not given back, so no later export of this day can run"
    )

    third = PlanScreen(root, manager, _App(settings))
    third.selected_date = THURSDAY
    third.calendar_client_factory = FakeClient
    third.export_day_to_calendar()
    thread = third._export_thread

    assert thread is not None, "the day stayed locked after its export finished"
    thread.join(timeout=30)
    third._poll_export()


def test_cem444d_a_failed_export_gives_the_day_back(screen, manager):
    """CE-M4.4 — the slot is released on failure, not only on success.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    A slot leaked by a failing export refuses every later export of that day
    for the life of the process, under a message telling the user to wait for
    an export that is already over (P1 — a transient failure made permanent).
    """
    _block(manager, 0)
    screen.calendar_client_factory = ExplodingClient
    status = _export(screen, screen.winfo_toplevel())

    assert "1 FAILED" in status, status
    assert (str(manager.db.db_path), THURSDAY) not in plan_module._EXPORTS_IN_FLIGHT

    screen.calendar_client_factory = FakeClient
    second = _export(screen, screen.winfo_toplevel())

    assert "already being exported" not in second, second
