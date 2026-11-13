"""CE-M3 — what GoogleCalendarManager sends, and what it does when sending fails.

Purpose: hold the four event calls to one calendar id, one marker, one retry
         rule and one timeout.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#m3
Tests:   this file

**Nothing here authenticates and nothing here reaches the network.** The
manager's `__init__` ends in a real OAuth flow, so every test builds the object
with `object.__new__` and gives it a fake `service` — the same shape
googleapiclient returns (`service.events().insert(...).execute()`), recording
what it was called with.

The retry tests patch `time.sleep` in the module under test. A test that
actually slept for the backoff would add seconds to the suite to prove nothing
the recorded sleep calls do not already prove.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.getmoredone import google_calendar as gc
from src.getmoredone.google_calendar import (
    BLOCK_DATE_PROPERTY,
    BLOCK_ID_PROPERTY,
    RETRY_ATTEMPTS,
    CalendarEventMissing,
    GoogleCalendarManager,
)

START = datetime(2026, 11, 9, 9, 30)


class FakeResponse:
    """Just enough of httplib2's response for `_status_of` to read."""

    def __init__(self, status):
        self.status = status
        self.reason = f"status {status}"


def _http_error(status, reason=None):
    """An `HttpError` the way googleapiclient raises one.

    `reason` writes the body Google actually sends, because a 403 is only the
    calendar saying "not now" for some reasons and "no" for the rest, and the
    reason lives in the body rather than in the status.
    """
    body = b"{}"
    if reason is not None:
        body = json.dumps({"error": {"errors": [{"reason": reason}]}}).encode()
    return gc.HttpError(FakeResponse(status), body)


class FakeRequest:
    def __init__(self, parent, kind, kwargs, result):
        self._parent = parent
        self._kind = kind
        self._kwargs = kwargs
        self._result = result

    def execute(self):
        self._parent.calls.append((self._kind, self._kwargs))
        error = self._parent.errors.get(self._kind)
        if error:
            # One error per queued entry, so "fails once then succeeds" is
            # expressible and a test cannot pass by never retrying.
            raised = error.pop(0) if error else None
            if not error:
                self._parent.errors.pop(self._kind, None)
            if raised is not None:
                raise raised
        if callable(self._result):
            return self._result(self._kwargs)
        return self._result


class FakeEvents:
    def __init__(self, parent):
        self._parent = parent

    def insert(self, **kwargs):
        return FakeRequest(self._parent, "insert", kwargs, {"id": "evt-new"})

    def get(self, **kwargs):
        return FakeRequest(self._parent, "get", kwargs, self._parent.stored)

    def update(self, **kwargs):
        return FakeRequest(
            self._parent, "update", kwargs, lambda call: call.get("body")
        )

    def delete(self, **kwargs):
        return FakeRequest(self._parent, "delete", kwargs, {})

    def list(self, **kwargs):
        return FakeRequest(self._parent, "list", kwargs, self._parent.pages.pop(0))


class FakeService:
    def __init__(self, stored=None, pages=None, errors=None):
        self.calls = []
        self.stored = stored if stored is not None else {"id": "evt-1"}
        self.pages = list(pages or [{"items": []}])
        self.errors = {kind: list(queue) for kind, queue in (errors or {}).items()}

    def events(self):
        return FakeEvents(self)

    def of_kind(self, kind):
        return [kwargs for called, kwargs in self.calls if called == kind]


def _manager(service):
    """A manager with a fake service and no authentication.

    `__init__` runs a real OAuth flow, so it is deliberately not called. The
    two attributes the event calls touch are the service and the timezone
    helper, and the second is left as the real one.
    """
    manager = object.__new__(GoogleCalendarManager)
    manager.service = service
    return manager


@pytest.fixture(autouse=True)
def no_real_sleeping(monkeypatch):
    """Record the backoff instead of serving it."""
    slept = []
    monkeypatch.setattr(gc.time, "sleep", slept.append)
    return slept


# --- CE-M3.1 — the calendar id --------------------------------------------

def test_cem311_the_calendar_id_reaches_every_call():
    """CE-M3.1 — create, read, update, delete and list all honour it.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m31
    Tests: this test

    All five in one test on purpose: the bug this prevents is one call left
    on the hard-coded 'primary' while its siblings were fixed (P5), and that
    is a statement about the set, not about any one of them.
    """
    service = FakeService(stored={"id": "evt-1"}, pages=[{"items": []}])
    manager = _manager(service)
    calendar = "work@example.com"

    manager.create_event(summary="A", start_datetime=START, duration_minutes=30,
                         calendar_id=calendar)
    manager.update_event(event_id="evt-1", summary="B", start_datetime=START,
                         duration_minutes=30, calendar_id=calendar)
    manager.delete_event("evt-1", calendar_id=calendar)
    manager.list_day_events("2026-11-09", calendar_id=calendar)

    assert [kind for kind, _ in service.calls] == [
        "insert", "get", "update", "delete", "list",
    ]
    assert {kwargs["calendarId"] for _, kwargs in service.calls} == {calendar}


def test_cem311a_the_default_calendar_is_still_primary():
    """CE-M3.1 — existing callers that pass no calendar are unaffected."""
    service = FakeService()
    _manager(service).create_event(
        summary="A", start_datetime=START, duration_minutes=30
    )

    assert service.of_kind("insert")[0]["calendarId"] == "primary"


# --- CE-M3.2 — listing the day's exported events --------------------------

def test_cem321_two_pages_are_both_returned():
    """CE-M3.2 — a single page is not a complete answer (E6).

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m32
    Tests: this test

    A sweep that read one page would leave the rest of the day's orphans on
    the calendar and report that it had cleaned up.
    """
    service = FakeService(pages=[
        {"items": [{"id": "a"}, {"id": "b"}], "nextPageToken": "page-2"},
        {"items": [{"id": "c"}]},
    ])

    events = _manager(service).list_day_events("2026-11-09")

    assert [event["id"] for event in events] == ["a", "b", "c"]
    assert [kwargs["pageToken"] for kwargs in service.of_kind("list")] == [None, "page-2"]


def test_cem322_only_our_own_marked_events_are_requested():
    """CE-M3.2 — the query asks for this app's events for that date, and single ones.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m32
    Tests: this test

    Selected by the marker rather than a time window: the marker carries the
    planned date, so no timezone arithmetic sits between the day the user
    planned and the events belonging to it.
    """
    service = FakeService(pages=[{"items": []}])

    _manager(service).list_day_events("2026-11-09")

    call = service.of_kind("list")[0]
    assert call["privateExtendedProperty"] == f"{BLOCK_DATE_PROPERTY}=2026-11-09"
    assert call["singleEvents"] is True
    assert call["showDeleted"] is False


# --- CE-M3.3 — the marker -------------------------------------------------

def test_cem331_create_writes_the_block_marker():
    """CE-M3.3 — and writes it private, where a calendar's viewers cannot see it.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m33
    Tests: this test
    """
    service = FakeService()

    _manager(service).create_event(
        summary="Deep work", start_datetime=START, duration_minutes=45,
        private_properties={BLOCK_ID_PROPERTY: "block-7",
                            BLOCK_DATE_PROPERTY: "2026-11-09"},
    )

    body = service.of_kind("insert")[0]["body"]
    assert body["extendedProperties"]["private"] == {
        BLOCK_ID_PROPERTY: "block-7",
        BLOCK_DATE_PROPERTY: "2026-11-09",
    }


def test_cem331a_an_event_with_no_marker_asked_for_carries_none():
    """CE-M3.3 — the one-off event dialog does not get a marker it never asked for."""
    service = FakeService()

    _manager(service).create_event(
        summary="Dentist", start_datetime=START, duration_minutes=30
    )

    assert "extendedProperties" not in service.of_kind("insert")[0]["body"]


def test_cem332_update_preserves_the_marker():
    """CE-M3.3 — an update must not strip the marker off an event it edits.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m33
    Tests: this test

    If it did, the next export would list the day, fail to recognise its own
    event, and delete it as an orphan — or create a second one beside it.
    """
    stored = {
        "id": "evt-1",
        "summary": "Old title",
        "extendedProperties": {"private": {BLOCK_ID_PROPERTY: "block-7"}},
    }
    service = FakeService(stored=stored)

    _manager(service).update_event(
        event_id="evt-1", summary="New title", start_datetime=START,
        duration_minutes=60, description="x",
    )

    body = service.of_kind("update")[0]["body"]
    assert body["summary"] == "New title"
    assert body["extendedProperties"]["private"] == {BLOCK_ID_PROPERTY: "block-7"}


def test_cea1_update_can_change_the_location_and_the_attendees():
    """CE-A1 — an edit must be able to set `location` and `attendees`.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m33
    Tests: this test

    `create_event` writes both, so the meeting dialog can make an event with a
    room and a guest list. `update_event` had no parameter for either, so the
    only reachable outcome was whatever the fetched body already held: a moved
    meeting kept the old room. The attendee list is written in the API's shape,
    the same one `create_event` builds, because a plain string list is not what
    Google accepts.

    An empty value clears rather than being ignored (`is not None`, as
    `description` already does) — a caller that means to drop the room or the
    guests has to be able to say so.
    """
    stored = {
        "id": "evt-1",
        "location": "Old room",
        "attendees": [{"email": "old@example.com"}],
    }
    service = FakeService(stored=stored)

    _manager(service).update_event(
        event_id="evt-1", location="New room", attendees=["new@example.com"],
    )

    body = service.of_kind("update")[0]["body"]
    assert body["location"] == "New room"
    assert body["attendees"] == [{"email": "new@example.com"}]

    service = FakeService(stored=dict(stored))
    _manager(service).update_event(event_id="evt-1", location="", attendees=[])
    body = service.of_kind("update")[0]["body"]
    assert body["location"] == ""
    assert body["attendees"] == []


def test_cea1c_an_attendee_kept_in_the_list_keeps_their_reply():
    """CE-A1 — a whole-body write must not reset what Google knows about a guest.

    Adversarial (P7): a list rebuilt as `[{'email': e} for e in attendees]`
    passes the test above, and drops `responseStatus`, `displayName` and
    `optional` off every guest the caller re-sent — so adding one person would
    silently un-accept everyone else. The fixture carries those keys for that
    reason.

    `sendUpdates` is asserted in the same test because it is the other half of
    the same statement: `create_event` says 'none' and this call inherited
    whatever the API defaults to, which with a writable attendee list is
    either no invitation at all or mail to everyone on every re-export (P5).
    """
    stored = {
        "id": "evt-1",
        "attendees": [
            {"email": "Accepted@example.com", "responseStatus": "accepted",
             "displayName": "A Person", "optional": True},
            {"email": "dropped@example.com", "responseStatus": "declined"},
        ],
    }
    service = FakeService(stored=stored)

    _manager(service).update_event(
        event_id="evt-1",
        attendees=["accepted@example.com", "added@example.com"],
    )

    call = service.of_kind("update")[0]
    assert call["body"]["attendees"] == [
        {"email": "accepted@example.com", "responseStatus": "accepted",
         "displayName": "A Person", "optional": True},
        {"email": "added@example.com"},
    ]
    assert call["sendUpdates"] == "none"


def test_cea1b_an_update_that_names_neither_keeps_what_the_event_had():
    """CE-A1 — the pass-through must not become a silent clear.

    Adversarial (P7): a fix written as two unconditional assignments would
    pass the test above and wipe the room off every event the day export
    touches, because the export names neither field.
    """
    stored = {
        "id": "evt-1",
        "location": "Old room",
        "attendees": [{"email": "old@example.com"}],
    }
    service = FakeService(stored=stored)

    _manager(service).update_event(event_id="evt-1", summary="New title")

    body = service.of_kind("update")[0]["body"]
    assert body["location"] == "Old room"
    assert body["attendees"] == [{"email": "old@example.com"}]


# --- CE-M3.4 — retry, and what must not be retried ------------------------

def test_cem341_a_503_is_retried_then_succeeds(no_real_sleeping):
    """CE-M3.4 — a transient failure gets another go, with backoff (E5, P1).

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test
    """
    service = FakeService(errors={"insert": [_http_error(503), None]})

    result = _manager(service).create_event(
        summary="A", start_datetime=START, duration_minutes=30
    )

    assert result == {"id": "evt-new"}
    assert len(service.of_kind("insert")) == 2, "it should have tried again"
    assert no_real_sleeping == [gc.RETRY_BACKOFF_SECONDS], "and waited before it did"


def test_cem342_a_404_is_not_retried_and_says_the_event_is_gone(no_real_sleeping):
    """CE-M3.4 — 404 is an answer, not a hiccup.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    The distinct exception is what lets the exporter re-create an event the
    user deleted in Google by hand instead of reporting a failure.
    """
    service = FakeService(errors={"get": [_http_error(404)]})

    with pytest.raises(CalendarEventMissing):
        _manager(service).update_event(event_id="evt-1", summary="A")

    assert len(service.of_kind("get")) == 1
    assert no_real_sleeping == []


def test_cem342a_a_403_is_not_retried(no_real_sleeping):
    """CE-M3.4 — nor is any other 4xx: retrying a "no" only delays the answer."""
    service = FakeService(errors={"insert": [_http_error(403)]})

    with pytest.raises(RuntimeError) as raised:
        _manager(service).create_event(
            summary="A", start_datetime=START, duration_minutes=30
        )

    assert "403" in str(raised.value)
    assert len(service.of_kind("insert")) == 1
    assert no_real_sleeping == []


def test_cem342b_a_retryable_status_that_runs_out_is_reported(no_real_sleeping):
    """CE-M3.4 — exhausted retries raise. A partial success must not read as a success."""
    service = FakeService(errors={"insert": [_http_error(500)] * RETRY_ATTEMPTS})

    with pytest.raises(RuntimeError) as raised:
        _manager(service).create_event(
            summary="A", start_datetime=START, duration_minutes=30
        )

    assert str(RETRY_ATTEMPTS) in str(raised.value)
    assert len(service.of_kind("insert")) == RETRY_ATTEMPTS
    assert no_real_sleeping == [
        gc.RETRY_BACKOFF_SECONDS * (2 ** n) for n in range(RETRY_ATTEMPTS - 1)
    ], "the backoff should grow, not repeat"


def test_cem345_a_timeout_is_retried_then_succeeds(no_real_sleeping):
    """CE-M3.4 — the failure the timeout itself creates is retried (E5, P1).

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    Found by a cold review pass: the helper caught `HttpError` and nothing
    else, so the 30s transport timeout, a reset connection and a DNS failure
    all went straight out to the caller unretried. A wifi blip is the
    commonest transient a desktop app sees, and it has no HTTP status at all.
    """
    service = FakeService(errors={"insert": [TimeoutError("timed out"), None]})

    result = _manager(service).create_event(
        summary="A", start_datetime=START, duration_minutes=30
    )

    assert result == {"id": "evt-new"}
    assert len(service.of_kind("insert")) == 2, "it should have tried again"
    assert no_real_sleeping == [gc.RETRY_BACKOFF_SECONDS], "and waited before it did"


def test_cem345a_a_timeout_that_runs_out_of_attempts_is_reported(no_real_sleeping):
    """CE-M3.4 — and when the network stays down, the caller is told."""
    service = FakeService(errors={
        "delete": [TimeoutError("timed out")] * gc.RETRY_ATTEMPTS
    })

    with pytest.raises(RuntimeError) as caught:
        _manager(service).delete_event("evt-1")

    assert str(gc.RETRY_ATTEMPTS) in str(caught.value)
    assert len(service.of_kind("delete")) == gc.RETRY_ATTEMPTS


def test_cem345b_a_disk_error_is_not_mistaken_for_a_network_one(no_real_sleeping):
    """CE-M3.4 — the retried set is named, not "any OSError".

    Every retried transport failure is an ``OSError``; so is a disk error
    raised by something else inside the call, and retrying that three times
    would turn one real failure into three.
    """
    service = FakeService(errors={"insert": [IsADirectoryError("not the network")]})

    with pytest.raises(IsADirectoryError):
        _manager(service).create_event(
            summary="A", start_datetime=START, duration_minutes=30
        )

    assert len(service.of_kind("insert")) == 1, "it must not have tried again"
    assert no_real_sleeping == []


def test_cem343_every_event_call_goes_through_the_retry_helper():
    """CE-M3.4 — all of them, by count, not a floor.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    Read off the AST rather than the text, and asserted as an exact set: the
    failure this guards against is a *new* call added later with no timeout
    and no retry, which a `>= 5` floor would never notice (P29 — a floor hides
    the narrowing it was written to catch). `_with_retry` itself is excluded;
    it is where the `execute()` of last resort lives.
    """
    import ast
    import pathlib

    source = pathlib.Path(gc.__file__).read_text()
    tree = ast.parse(source)

    executing_functions = set()
    helper_wrapped = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "execute"
            ):
                executing_functions.add(node.name)
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_with_retry"
            ):
                helper_wrapped.add(node.name)

    executing_functions.discard("_with_retry")

    assert executing_functions == {
        "create_event", "update_event", "delete_event", "list_day_events",
        # CIP-M2.1 / D11 -- the Plan's commitment read (reason b: a new call,
        # through the retry helper like the rest).
        "list_events_between",
    }, (
        "a method that calls the Google API appeared or disappeared; if it is "
        "new it needs the retry helper, and this list needs updating"
    )
    assert executing_functions <= helper_wrapped, (
        f"these talk to Google without the retry helper: "
        f"{sorted(executing_functions - helper_wrapped)}"
    )


def test_cem344_the_transport_carries_a_timeout(monkeypatch):
    """CE-M3.4 / E1 — the service is built on an http with a timeout.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    Without it a background export can hang forever, which in this app means
    a status line that never changes and a button that never comes back.
    """
    import httplib2

    seen = {}

    class RecordingHttp(httplib2.Http):
        def __init__(self, *args, timeout=None, **kwargs):
            seen["timeout"] = timeout
            super().__init__(*args, timeout=timeout, **kwargs)

    monkeypatch.setattr(httplib2, "Http", RecordingHttp)
    monkeypatch.setattr(gc, "build", lambda *args, **kwargs: ("service", kwargs))

    manager = object.__new__(GoogleCalendarManager)
    service = manager._build_service(creds=None)

    assert seen["timeout"] == gc.REQUEST_TIMEOUT_SECONDS
    assert service[1]["http"] is not None, "the authorized http is what carries it"
    assert "credentials" not in service[1], "build takes one or the other, not both"


# --- CE-M4.4 / E3 — the client the export builds cannot block on a browser --

class _NeverReached:
    """Stands in for the OAuth flow, and fails the test if anything uses it."""

    @staticmethod
    def from_client_secrets_file(*args, **kwargs):
        raise AssertionError(
            "the consent flow was started: run_local_server and input() both "
            "wait forever, and this client is built on a worker thread"
        )


@pytest.fixture
def auth_paths(tmp_path, monkeypatch):
    """A credentials file that exists and a token file that cannot be loaded.

    Nothing here is a real credential. `credentials.json` only has to exist --
    `_authenticate` checks for the path, and the flow that would read it is
    replaced. The token is deliberately unreadable, which is the case that
    reaches the sign-in branch: a pickle this build cannot load, a revoked
    grant, a refresh that fails.
    """
    credentials = tmp_path / "credentials.json"
    credentials.write_text("{}")
    token = tmp_path / "token.pickle"
    token.write_bytes(b"not a pickle")
    monkeypatch.setattr(gc, "InstalledAppFlow", _NeverReached)
    monkeypatch.setattr(
        "builtins.input",
        lambda *a, **k: pytest.fail("the manual code prompt was reached"),
    )
    return str(credentials), str(token)


def test_cem346_a_non_interactive_client_refuses_instead_of_prompting(auth_paths):
    """CE-M4.4 / E3 — a token that is present but unusable must not open a browser.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    Found by a cold review pass, as a blocker. The Plan screen refuses the
    export when there is no token file, which covers the never-connected
    user — but a token that exists and cannot be loaded or refreshed falls
    through to `flow.run_local_server`, and from there to `input()`. Both of
    those wait forever on the export's worker thread, so the button stays
    disabled under "Exporting…" until the app is killed (P1 — a recoverable
    condition turned into a permanent one, P15 — a worker with nowhere to
    report).
    """
    credentials, token = auth_paths

    with pytest.raises(gc.AuthenticationRequired):
        GoogleCalendarManager(
            credentials_file=credentials, token_file=token, allow_interactive=False
        )


def test_cem346a_an_interactive_client_still_signs_in(auth_paths):
    """CE-M4.4 / E3 — the flag is what decides, not a missing code path.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests: this test

    The paired test. `test_cem346` would also pass if the sign-in branch were
    unreachable for every caller, which would break the one place that is
    allowed to ask — connecting the calendar from the dialog, on the main
    thread, with a console behind it. Here the same unusable token *does*
    reach the flow, and the `_NeverReached` stand-in proves it by raising
    rather than by opening anything.
    """
    credentials, token = auth_paths

    with pytest.raises(AssertionError, match="the consent flow was started"):
        GoogleCalendarManager(credentials_file=credentials, token_file=token)


# --- CE-M3.4b / CE-M3.5 — the payload, the reason, and the second event ----

def test_cem347_the_insert_body_carries_the_wall_clock_times_and_a_real_zone():
    """CE-M3.4b — the one place a block becomes an instant on a calendar.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    Everything above this asserts `ExportEntry.start`, which is a datetime the
    app computed and the app read back. This asserts the three strings that
    actually leave the machine. The zone is checked by handing it to
    `ZoneInfo` rather than by comparing it with what the manager returns: a
    test that asked the production helper for the expected value would pass
    just as well if the field were dropped, or filled with a UTC offset, which
    Google reads differently.
    """
    service = FakeService()
    manager = _manager(service)

    manager.create_event(
        summary="Draft the brief",
        start_datetime=START,
        duration_minutes=45,
    )

    body = service.of_kind("insert")[0]["body"]
    assert body["start"]["dateTime"] == "2026-11-09T09:30:00"
    assert body["end"]["dateTime"] == "2026-11-09T10:15:00"

    zone = body["start"]["timeZone"]
    assert ZoneInfo(zone), "the zone must be an IANA name the calendar can read"
    assert body["end"]["timeZone"] == zone


def test_cem347a_the_update_body_carries_them_too():
    """CE-M3.4b — a moved block is re-timed by the same three strings.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test
    """
    service = FakeService(stored={"id": "evt-1", "summary": "was"})
    manager = _manager(service)

    manager.update_event(
        event_id="evt-1",
        summary="Draft the brief",
        start_datetime=START,
        duration_minutes=45,
    )

    body = service.of_kind("update")[0]["body"]
    assert body["start"]["dateTime"] == "2026-11-09T09:30:00"
    assert body["end"]["dateTime"] == "2026-11-09T10:15:00"

    zone = body["start"]["timeZone"]
    assert ZoneInfo(zone)
    assert body["end"]["timeZone"] == zone


def test_cem35_the_caller_decides_the_reminders():
    """CE-M3.5 — the ten-minute popup is a default, not a law.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m35
    Tests: this test

    The meeting dialog has always wanted a popup and still gets one. The Plan
    export wants the user's own calendar setting, and `useDefault: False` with
    an override is exactly what overrules it — sixteen blocks would have been
    sixteen popups the user never asked for.
    """
    service = FakeService()
    manager = _manager(service)

    manager.create_event(summary="A meeting", start_datetime=START)
    manager.create_event(
        summary="A planned block",
        start_datetime=START,
        reminders={"useDefault": True},
    )

    dialog_body, export_body = [call["body"] for call in service.of_kind("insert")]
    assert dialog_body["reminders"] == {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 10}],
    }
    assert export_body["reminders"] == {"useDefault": True}


def test_cem348_a_lost_insert_response_does_not_make_a_second_event():
    """CE-M3.4b — a retried insert must not leave two events behind.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    The sequence this guards: the insert reaches Google, Google writes the
    event, the response is lost (a 30s timeout, a 503 from a frontend). The
    retry sends the same body — and because the body carries an event id of
    our own, Google answers 409 instead of writing a second event. The id is
    then read back, so the caller still gets the event it asked for.
    """
    service = FakeService(
        stored={"id": "the-one-that-landed", "summary": "Draft the brief"},
        errors={"insert": [_http_error(409)]},
    )
    manager = _manager(service)

    event = manager.create_event(summary="Draft the brief", start_datetime=START)

    inserts = service.of_kind("insert")
    assert len(inserts) == 1, "a 409 is not retried: the event is already there"
    sent_id = inserts[0]["body"]["id"]
    assert sent_id.startswith("gmd")

    reads = service.of_kind("get")
    assert len(reads) == 1
    assert reads[0]["eventId"] == sent_id, "the id read back is the id we sent"
    assert event["id"] == "the-one-that-landed"


def test_cem348a_the_insert_carries_one_id_across_its_retries():
    """CE-M3.4b — the same id on every attempt, or the guard is worthless.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    A body rebuilt per attempt would carry a fresh id each time, and Google
    would accept every one of them.
    """
    service = FakeService(errors={"insert": [_http_error(503)]})
    manager = _manager(service)

    manager.create_event(summary="Draft the brief", start_datetime=START)

    ids = [call["body"]["id"] for call in service.of_kind("insert")]
    assert len(ids) == 2, "the 503 is retried"
    assert ids[0] == ids[1]


def test_cem348b_two_creates_do_not_share_an_id():
    """CE-M3.4b — one id per insert, not one per process.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    A constant id would make the *second* block of a day a 409, and the
    export would quietly report the first block's event for it.
    """
    service = FakeService()
    manager = _manager(service)

    manager.create_event(summary="First", start_datetime=START)
    manager.create_event(summary="Second", start_datetime=START)

    first, second = [call["body"]["id"] for call in service.of_kind("insert")]
    assert first != second


def test_cem349_a_403_rate_limit_is_retried_then_succeeds(no_real_sleeping):
    """CE-M3.4b — a throttled call does not always arrive as a 429.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    The Calendar API reports per-user rate limits as a 403 with a reason. A
    day of twenty blocks plus the sweep's list is a burst of twenty-odd calls,
    so this is the failure a day-sized export meets first — and it was being
    reported to the user as a hard "FAILED" for every block in the burst.
    """
    service = FakeService(
        errors={"insert": [_http_error(403, reason="rateLimitExceeded")]},
    )
    manager = _manager(service)

    event = manager.create_event(summary="Draft the brief", start_datetime=START)

    assert len(service.of_kind("insert")) == 2
    assert event == {"id": "evt-new"}
    assert no_real_sleeping == [1.0]


def test_cem349a_a_403_that_is_a_real_refusal_is_not_retried():
    """CE-M3.4b — "no" is still "no", and retrying it only costs the user time.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test
    """
    service = FakeService(errors={"insert": [_http_error(403, reason="forbidden")]})
    manager = _manager(service)

    with pytest.raises(RuntimeError):
        manager.create_event(summary="Draft the brief", start_datetime=START)

    assert len(service.of_kind("insert")) == 1


def test_cem349b_an_unreadable_error_body_leaves_the_status_to_decide():
    """CE-M3.4b — reading the reason must not become a way to fail.

    Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests: this test

    The body is googleapiclient's, and an error page from a proxy is not JSON
    at all. A 403 with nothing readable in it stays permanent, which is the
    safe side of the line, and the parse itself never raises.
    """
    service = FakeService(
        errors={"insert": [gc.HttpError(FakeResponse(403), b"<html>nope</html>")]},
    )
    manager = _manager(service)

    with pytest.raises(RuntimeError):
        manager.create_event(summary="Draft the brief", start_datetime=START)

    assert len(service.of_kind("insert")) == 1
