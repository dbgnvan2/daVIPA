"""
Google Calendar integration for creating meeting events.
"""

import json
import os
import pickle
import ssl
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from . import paths

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from tzlocal import get_localzone
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False


# If modifying these scopes, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/calendar']

#: The calendar written to when nothing says otherwise.
DEFAULT_CALENDAR_ID = 'primary'

#: Private properties the Plan export stamps on every event it creates. They
#: live here, in the layer that writes and queries them, so
#: ``calendar_exporter`` can import them without this module importing it back.
#: Private means the people a calendar is shared with never see them, and we
#: can read them again -- which is what lets a re-export find the events of
#: blocks that have since been deleted.
#: Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m33
#: Tests: tests/test_google_calendar_export_calls.py::test_cem331_create_writes_the_block_marker
BLOCK_ID_PROPERTY = 'gmd_block_id'
BLOCK_DATE_PROPERTY = 'gmd_block_date'

#: How long any one HTTP call may take before it is given up on (E1). Without
#: this the transport waits indefinitely, which in a desktop app means a
#: background thread that never finishes and a button that never comes back.
REQUEST_TIMEOUT_SECONDS = 30

#: Retries, and what is worth retrying. 429 and the 5xx family are the
#: calendar saying "not now"; everything else is it saying "no", and retrying
#: a "no" only makes the user wait longer for the same answer (E5, P1).
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

#: A throttled call does not always arrive as a 429. The Calendar API reports
#: per-user and per-project rate limits as a **403** carrying one of these
#: reasons, which is the calendar saying "not now" in the clothes of a "no"
#: (P1). A 403 with any other reason -- or none we can read -- stays permanent.
RETRYABLE_403_REASONS = frozenset({
    'ratelimitexceeded',
    'userratelimitexceeded',
    'quotaexceeded',
    'backenderror',
})

#: What ``create_event`` asks for when the caller names no reminders: the
#: ten-minute popup the meeting dialog has always had. CE-M3.5.
DEFAULT_REMINDERS = {
    'useDefault': False,
    'overrides': [
        {'method': 'popup', 'minutes': 10},
    ],
}

#: What the Plan export asks for instead: the user's own calendar-level
#: reminder setting, whatever it is, and no override of it.
INHERIT_REMINDERS = {'useDefault': True}

#: An id we chose is already on the calendar. For an insert that carries its
#: own event id this means an earlier attempt of the same insert landed.
CONFLICT_STATUSES = frozenset({409})

#: A 404/410 on an event means it is not there any anymore -- deleted in Google
#: by hand, in the case this matters for. A distinct exception, because the
#: caller can act on it (make it again) and cannot act on a generic failure.
MISSING_STATUSES = frozenset({404, 410})


class CalendarEventMissing(Exception):
    """The event an id names is no longer on the calendar."""


class CalendarEventExists(Exception):
    """The event id in this request is already on the calendar.

    Purpose: CE-M3.4b -- let a retried insert that carries its own id be told
             apart from every other refusal, so the first attempt's event is
             read back instead of a second one being created.
    Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests:   tests/test_google_calendar_export_calls.py::test_cem348_a_lost_insert_response_does_not_make_a_second_event
    """


class AuthenticationRequired(Exception):
    """Signing in is needed, and this caller is not allowed to ask for it.

    Purpose: CE-M4.4 / E3 -- make "cannot sign in here" a reportable outcome
             instead of a blocked thread.
    Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests:   tests/test_google_calendar_export_calls.py::test_cem346_a_non_interactive_client_refuses_instead_of_prompting

    Signing in runs ``flow.run_local_server`` -- a browser, a local HTTP
    server and no timeout -- and falls back to ``input()`` on the console.
    Both wait forever, and a background thread that waits forever takes a
    disabled button and a status line with it (P1, P15). A caller that cannot
    show either asks for ``allow_interactive=False`` and handles this.
    """


def _transport_errors() -> tuple:
    """The transport failures worth retrying.

    Purpose: CE-M3.4 -- the retry helper used to see HTTP statuses only, so
             the failures the new 30s timeout creates reached the caller
             unretried. A wifi blip is the commonest transient in a desktop
             app and it is not an ``HttpError`` (P1, E5).
    Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests:   tests/test_google_calendar_export_calls.py::test_cem345_a_timeout_is_retried_then_succeeds

    Named rather than ``OSError``: every one of these is an ``OSError``, and
    so is a disk error raised by something else inside the call, which must
    not be retried as though the network had hiccuped.
    """
    errors = [TimeoutError, ConnectionError, ssl.SSLError]
    try:
        import httplib2
    except ImportError:  # pragma: no cover - ships with the API client
        pass
    else:
        # Covers ServerNotFoundError (DNS) and the malformed-response faults.
        errors.append(httplib2.HttpLib2Error)
    return tuple(errors)


#: Evaluated once, at import: the tuple an ``except`` clause needs.
RETRYABLE_TRANSPORT_ERRORS = _transport_errors()


def _status_of(error) -> Optional[int]:
    """The HTTP status inside an ``HttpError``, or ``None``.

    Read defensively: the shape of ``error.resp`` is googleapiclient's, not
    ours, and a status we cannot read must not be mistaken for a status worth
    retrying.
    """
    status = getattr(getattr(error, 'resp', None), 'status', None)
    try:
        return int(status)
    except (TypeError, ValueError):
        return None


def _reasons_of(error) -> frozenset:
    """The reason codes inside an ``HttpError`` body, lowercased.

    Purpose: CE-M3.4b -- a 403 is only retryable for some reasons, and the
             reason lives in the response body, not in the status.
    Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests:   tests/test_google_calendar_export_calls.py::test_cem349_a_403_rate_limit_is_retried_then_succeeds

    Read defensively and never raised from: the body is googleapiclient's and
    may be bytes, text, absent or not JSON at all. An unreadable body means no
    reason, which leaves the status to decide on its own.
    """
    content = getattr(error, 'content', None)
    if isinstance(content, (bytes, bytearray)):
        try:
            content = content.decode('utf-8', 'replace')
        except Exception:  # noqa: BLE001 - pragma: no cover
            return frozenset()
    if not isinstance(content, str) or not content.strip():
        return frozenset()
    try:
        body = json.loads(content)
    except (ValueError, TypeError):
        return frozenset()
    if not isinstance(body, dict):
        return frozenset()
    inner = body.get('error')
    if not isinstance(inner, dict):
        return frozenset()
    found = set()
    top = inner.get('status')
    if isinstance(top, str) and top.strip():
        found.add(top.strip().lower())
    entries = inner.get('errors')
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                reason = entry.get('reason')
                if isinstance(reason, str) and reason.strip():
                    found.add(reason.strip().lower())
    return frozenset(found)


def _is_retryable(error, status: Optional[int]) -> bool:
    """Whether this failure is the calendar saying "not now"."""
    if status in RETRYABLE_STATUSES:
        return True
    if status == 403:
        return bool(_reasons_of(error) & RETRYABLE_403_REASONS)
    return False


def _with_retry(description: str, call):
    """Run one Google call, retrying only what is worth retrying.

    Purpose: CE-M3.4 -- timeout, retry and backoff for every event call in
             this module, not just the newest one (P5).
    Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests:   tests/test_google_calendar_export_calls.py::test_cem341_a_503_is_retried_then_succeeds

    Raises ``CalendarEventMissing`` for a 404/410, ``RuntimeError`` for
    anything else -- including a retryable status that has run out of
    attempts, which is a failure to report rather than a silent partial
    success (P1: the transient case gets a retry, not a permanent verdict,
    and when the retries run out the caller is told).
    """
    last_error = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return call()
        except HttpError as error:
            status = _status_of(error)
            if status in MISSING_STATUSES:
                raise CalendarEventMissing(f"{description}: {status}") from error
            if status in CONFLICT_STATUSES:
                raise CalendarEventExists(f"{description}: {status}") from error
            if not _is_retryable(error, status):
                raise RuntimeError(f"Failed to {description}: {error}") from error
            last_error = error
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))
        except RETRYABLE_TRANSPORT_ERRORS as error:
            # A timeout, a reset connection, a DNS failure. There is no status
            # to read, and none of these says the request will never succeed,
            # so they get the same backoff the 5xx statuses get and the same
            # reported failure when the attempts run out (P1).
            last_error = error
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    raise RuntimeError(
        f"Failed to {description} after {RETRY_ATTEMPTS} attempts: {last_error}"
    )


def _new_event_id() -> str:
    """An event id of our own for an insert, so a retry cannot duplicate it.

    Purpose: CE-M3.4b -- ``events().insert`` is not idempotent, and it is
             retried. A request that lands and whose response is lost would
             otherwise be sent again and make a second event (P1 again, from
             the other side: a retry must not turn a transient failure into
             two events).
    Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
    Tests:   tests/test_google_calendar_export_calls.py::test_cem348_a_lost_insert_response_does_not_make_a_second_event

    Google's ids are base32hex: the characters ``a``-``v`` and ``0``-``9``,
    5 to 1024 of them. A uuid4 hex is 0-9a-f, all inside that set, and the
    ``gmd`` prefix says where it came from when one is seen by hand.
    """
    return f"gmd{uuid.uuid4().hex}"


def _say(*parts) -> None:
    """print() that cannot abort the caller.

    Every status line in this module carries an emoji. On a Windows console
    using cp1252 those raise UnicodeEncodeError, and a PyInstaller --noconsole
    build has no stdout at all — so a print here could propagate out of
    __init__ and abort construction *after* the token was written.

    Guarding one print did not help: eight more run on the same path,
    including the "service initialized successfully" line four statements
    later. Fixed as a class, which is the only way a guard like this is worth
    anything (P5).

    Narrow exceptions on purpose — a bare ``except Exception`` would swallow a
    real bug as readily as an encoding one.
    """
    try:
        print(*parts)
    except (UnicodeEncodeError, OSError, ValueError):
        pass


class GoogleCalendarManager:
    """Manages Google Calendar API interactions."""

    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None,
                 force_reauth: bool = False, allow_interactive: bool = True):
        """
        Initialize Google Calendar manager.

        Args:
            credentials_file: Path to OAuth credentials JSON file
            token_file: Path to store/load token pickle file
            force_reauth: If True, delete existing token and force re-authentication
            allow_interactive: If False, raise ``AuthenticationRequired`` rather
                than open a browser and wait. Callers on a background thread,
                or with no console to answer on, pass False.
        """
        if not GOOGLE_CALENDAR_AVAILABLE:
            raise ImportError(
                "Google Calendar libraries not installed. "
                "Run: pip install google-auth google-auth-oauthlib "
                "google-auth-httplib2 google-api-python-client"
            )

        # Read the arguments before touching the filesystem. This used to
        # create the data directory first and consult them afterwards, so
        # constructing the manager with two explicit paths still made a folder
        # in the user's home that nothing then used (P13 — a step nested under
        # the wrong scope). The directory is created where it is written to,
        # not here.
        self.data_dir = paths.google_auth_dir()
        self.credentials_file = credentials_file or str(self.data_dir / "credentials.json")
        self.token_file = token_file or str(self.data_dir / "token.pickle")

        # Force re-authentication if requested (deletes zombie tokens)
        if force_reauth and os.path.exists(self.token_file):
            _say(f"🗑️  Deleting old token (force re-authentication): {self.token_file}")
            os.remove(self.token_file)

        self.allow_interactive = allow_interactive

        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Calendar API."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                _say(f"Warning: Failed to load token file: {e}")
                _say("Will re-authenticate...")
                creds = None
            else:
                # Outside the try on purpose: this used to sit inside it, so a
                # print that raised — a cp1252 console, a closed pipe — ran the
                # `except` and discarded a token that had loaded perfectly.
                # A status line must never be able to invalidate a credential
                # (P1: a transient console problem became a permanent
                # "credentials not found" on every launch).
                _say("Loaded existing token from:", self.token_file)

        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                _say("Refreshing expired credentials...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    _say(f"Failed to refresh credentials: {e}")
                    _say("Will need to re-authenticate...")
                    creds = None
                else:
                    # Same reason as above: a print must not undo a refresh
                    # that succeeded.
                    _say("Successfully refreshed credentials!")

            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Google Calendar credentials not found at: {self.credentials_file}\n"
                        "Please download OAuth credentials from Google Cloud Console:\n"
                        "1. Go to https://console.cloud.google.com/\n"
                        "2. Create project or select existing\n"
                        "3. Enable Google Calendar API\n"
                        "4. Create OAuth 2.0 credentials (Desktop app)\n"
                        "5. Download JSON and save as credentials.json\n"
                        f"6. Place at: {self.credentials_file}"
                    )

                if not self.allow_interactive:
                    # Before the banner, the browser and the ``input()``: by
                    # here there is no usable token and the only way to get one
                    # is to ask the user, which this caller cannot do. Raising
                    # is the whole point of the flag -- a GUI worker thread
                    # that reached ``run_local_server`` would block on a
                    # consent page nobody is looking at, leaving the button it
                    # came from disabled for the life of the process.
                    raise AuthenticationRequired(
                        "Google Calendar needs you to sign in again, and that "
                        "cannot be done from here."
                    )

                _say("\n" + "="*60)
                _say("GOOGLE CALENDAR AUTHENTICATION REQUIRED")
                _say("="*60)
                _say("\nAttempting to open browser for authentication...")
                _say("If browser doesn't open, you'll see a URL to visit manually.\n")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)

                # Try local server method first (opens browser)
                try:
                    # Force consent prompt to avoid browser OAuth cache issues
                    # This ensures we use the correct client_id even if browser has cached old session
                    creds = flow.run_local_server(
                        port=0,
                        open_browser=True,
                        success_message='Authentication successful! You can close this window.',
                        prompt='consent'  # Force re-consent to avoid cached OAuth sessions
                    )
                    _say("\n✅ Authentication successful via browser!")

                except Exception as e:
                    _say(f"\n⚠️  Browser authentication failed: {e}")
                    _say("\nFalling back to manual authentication...")
                    _say("\nPlease follow these steps:")
                    _say("1. Visit the URL shown below in a browser")
                    _say("2. Sign in with your Google account")
                    _say("3. Click 'Allow' to grant calendar access")
                    _say("4. Copy the authorization code shown")
                    _say("5. Paste the code below when prompted\n")

                    try:
                        # Get the authorization URL
                        auth_url, _ = flow.authorization_url(prompt='consent')
                        _say(f"Visit this URL:\n{auth_url}\n")

                        # Prompt for code
                        code = input("Enter the authorization code: ").strip()

                        # Exchange code for credentials
                        flow.fetch_token(code=code)
                        creds = flow.credentials
                        _say("\n✅ Authentication successful via manual code entry!")

                    except KeyboardInterrupt:
                        raise RuntimeError("\nAuthentication cancelled by user.")
                    except Exception as manual_error:
                        raise RuntimeError(
                            f"Manual authentication failed.\n"
                            f"Browser error: {e}\n"
                            f"Manual auth error: {manual_error}\n\n"
                            f"Troubleshooting:\n"
                            f"1. Check that credentials.json is valid\n"
                            f"2. Ensure Google Calendar API is enabled in Google Cloud Console\n"
                            f"3. Verify OAuth consent screen is configured\n"
                            f"4. Make sure you copied the full authorization code\n"
                            f"5. Try running this on a machine with a web browser\n"
                            f"6. Check network/firewall settings"
                        )

            # Save the credentials for next run.
            #
            # An earlier version stored this on the instance as
            # `token_persisted` "so a caller can tell". Nothing read it, and it
            # was tri-state (None when an existing token was reused), so the
            # natural `if not mgr.token_persisted:` would have read the healthy
            # reuse case as a failure — a documented capability with no caller
            # (P21), plus a trap for the first one. The bool is used here, where
            # there is something to say, and nowhere else. Surfacing a failed
            # save in the GUI is recorded in BACKLOG.md: a print() is invisible
            # in a double-clicked app.
            if not self._save_token(creds):
                _say("⚠️  Signed in, but the token was not saved — you will be "
                      "asked to sign in again next time.\n")

        self.service = self._build_service(creds)
        _say("✅ Google Calendar service initialized successfully!")

    def _build_service(self, creds):
        """The API client, with a timeout on its transport.

        Purpose: CE-M3.4 / E1 -- no call in this module may hang forever.
        Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m34
        Tests:   tests/test_google_calendar_export_calls.py::test_cem344_the_transport_carries_a_timeout

        ``build`` takes either credentials or an http object, not both, so the
        timeout has to arrive as an authorized http. If either helper is
        missing the plain client is still returned: a calendar that works
        without a timeout beats a calendar that does not work.
        """
        try:
            import httplib2
            from google_auth_httplib2 import AuthorizedHttp
        except ImportError:  # pragma: no cover - both ship with the API client
            return build('calendar', 'v3', credentials=creds)

        authorized = AuthorizedHttp(
            creds, http=httplib2.Http(timeout=REQUEST_TIMEOUT_SECONDS)
        )
        return build(
            'calendar', 'v3', http=authorized, cache_discovery=False
        )

    def _save_token(self, creds) -> bool:
        """Write the OAuth token to ``self.token_file``.

        Purpose: create the directory at the point a file is written to it.
        Spec:    docs/implementation_plan_2026-08-19_backlog_clearance.md#batch-3
        Tests:   tests/test_google_calendar_paths.py::test_bi3_saving_a_token_creates_its_parent_directory

        ``__init__`` used to create the default data directory whether or not
        it was going to be used. Creating it here instead also covers an
        explicit ``token_file`` in a directory that does not exist yet: the
        write is deliberately warn-only, so that case degraded to
        re-authenticating on every run behind a printed warning.

        Returns True when the token reached disk. The write is deliberately
        warn-only — losing the token must not fail a sign-in that succeeded —
        so the caller uses this to say which of the two happened.

        The chmod is in its own guard on purpose. It runs *after* a successful
        write, so folding it into the same try made a failing chmod report
        "failed to save" while a world-readable token sat on disk: the opposite
        of both halves of that message.
        """
        try:
            parent = os.path.dirname(os.path.abspath(self.token_file))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            # The diagnosis only. The consequence ("you will be asked to sign
            # in again") belongs to the caller, which knows the sign-in itself
            # succeeded — printing both here made a failed save emit three
            # warning lines saying the same thing.
            _say(f"⚠️  Warning: Failed to save token: {e}")
            return False

        try:
            os.chmod(self.token_file, 0o600)
        except Exception as e:
            # The token IS saved. Say so, and say what could not be tightened.
            _say(f"⚠️  Warning: saved the token but could not restrict its "
                  f"permissions: {e}")
            _say(f"   Anyone able to read {self.token_file} can use your "
                  "Google account. Fix the file's permissions by hand.\n")

        _say(f"✅ Token saved to: {self.token_file}\n")
        return True

    def _get_local_timezone(self) -> str:
        """
        Get the local timezone name in IANA format.

        Returns:
            IANA timezone name (e.g., 'America/Los_Angeles')
            Falls back to 'UTC' if detection fails
        """
        try:
            tz = get_localzone()
            return str(tz)
        except Exception:
            # Fallback to UTC if we can't detect local timezone
            _say("⚠️  Warning: Could not detect local timezone, using UTC")
            return 'UTC'

    def create_event(
        self,
        summary: str,
        start_datetime: datetime,
        duration_minutes: int = 60,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[list] = None,
        calendar_id: str = DEFAULT_CALENDAR_ID,
        private_properties: Optional[Dict[str, str]] = None,
        reminders: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Google Calendar event.

        Args:
            summary: Event title
            start_datetime: When the event starts
            duration_minutes: Event duration in minutes
            description: Event description/notes
            location: Event location
            attendees: List of email addresses
            calendar_id: Which calendar to write to. CE-M3.1 -- a parameter
                rather than the hard-coded 'primary' this used to carry (P4),
                so the Plan export can be pointed at a calendar of its own.
            private_properties: Marker properties stored on the event and
                visible only to this account. CE-M3.3.
            reminders: The event's ``reminders`` body. CE-M3.5 -- a parameter
                rather than the ten-minute popup this used to hard-code for
                every caller (P4). A day of planned blocks is not a day of
                meetings, and a popup per block is a notification the user
                never asked for; the Plan export passes
                ``{'useDefault': True}`` so the user's own calendar setting
                decides. Omitted means ``DEFAULT_REMINDERS`` -- the popup --
                which is what the meeting dialog still wants.

        Returns:
            Dict with event details including 'htmlLink' for the calendar URL

        Raises:
            RuntimeError: If the API request fails
            CalendarEventMissing: If the calendar itself is not there
        """
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)

        # Get local timezone
        local_tz = self._get_local_timezone()

        event = {
            'summary': summary,
            'description': description or '',
            'location': location or '',
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': local_tz,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': local_tz,
            },
            'reminders': reminders or DEFAULT_REMINDERS,
            'id': _new_event_id(),
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        if private_properties:
            event['extendedProperties'] = {
                'private': {
                    str(key): str(value)
                    for key, value in private_properties.items()
                }
            }

        try:
            return _with_retry(
                f"create calendar event '{summary}'",
                lambda: self.service.events().insert(
                    calendarId=calendar_id,
                    body=event,
                    sendUpdates='none'  # Don't send email notifications
                ).execute(),
            )
        except CalendarEventExists:
            # The id in the body is one nothing else has seen, so a conflict
            # means an earlier attempt of this very insert landed and only its
            # response was lost. Read that event back instead of making a
            # second one.
            return _with_retry(
                f"read back calendar event {event['id']}",
                lambda: self.service.events().get(
                    calendarId=calendar_id,
                    eventId=event['id'],
                ).execute(),
            )

    def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_datetime: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        description: Optional[str] = None,
        calendar_id: str = DEFAULT_CALENDAR_ID,
    ) -> Dict[str, Any]:
        """Update an existing calendar event.

        CE-M3.3 -- the event is read, the named fields are changed, and
        everything else is written back as it was. That is what preserves the
        private marker the Plan export stamped on it: an update that built a
        fresh body would strip the marker, and the next export would see an
        event it could not recognise as its own.
        Spec:  docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m33
        Tests: tests/test_google_calendar_export_calls.py::test_cem332_update_preserves_the_marker

        Raises:
            CalendarEventMissing: if the event is gone (404/410), so the
                caller can make it again rather than reporting a failure the
                user cannot act on.
        """
        event = _with_retry(
            f"read calendar event {event_id}",
            lambda: self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute(),
        )

        # Only the named fields are touched; the rest of the body -- the
        # private marker included -- goes back exactly as it came.
        if summary:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if start_datetime and duration_minutes:
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            local_tz = self._get_local_timezone()
            event['start'] = {
                'dateTime': start_datetime.isoformat(),
                'timeZone': local_tz,
            }
            event['end'] = {
                'dateTime': end_datetime.isoformat(),
                'timeZone': local_tz,
            }

        return _with_retry(
            f"update calendar event {event_id}",
            lambda: self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute(),
        )

    def delete_event(self, event_id: str, calendar_id: str = DEFAULT_CALENDAR_ID):
        """Delete a calendar event.

        Raises ``CalendarEventMissing`` when it has already gone, which the
        caller can treat as the end state it asked for.
        """
        _with_retry(
            f"delete calendar event {event_id}",
            lambda: self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute(),
        )

    def list_day_events(
        self,
        block_date: str,
        calendar_id: str = DEFAULT_CALENDAR_ID,
    ) -> List[Dict[str, Any]]:
        """Every event this app exported for one date.

        Purpose: CE-M3.2 -- the read the orphan sweep needs.
        Spec:    docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m32
        Tests:   tests/test_google_calendar_export_calls.py::test_cem321_two_pages_are_both_returned

        Selected by our own private marker rather than by a time window, and
        deliberately so: the marker carries the planned date, so no timezone
        arithmetic stands between "the day the user planned" and "the events
        that belong to it". A UTC window would include or exclude the edges of
        the day depending on where the user is.

        Paginated (E6): a single page is not a complete answer, and a sweep
        that read one page would leave the rest of the day's orphans behind.
        """
        events: List[Dict[str, Any]] = []
        page_token = None

        while True:
            response = _with_retry(
                f"list calendar events for {block_date}",
                lambda token=page_token: self.service.events().list(
                    calendarId=calendar_id,
                    privateExtendedProperty=f"{BLOCK_DATE_PROPERTY}={block_date}",
                    singleEvents=True,
                    showDeleted=False,
                    pageToken=token,
                ).execute(),
            )
            events.extend(response.get('items') or [])
            page_token = response.get('nextPageToken')
            if not page_token:
                return events

    @staticmethod
    def is_available() -> bool:
        """Check if Google Calendar integration is available."""
        return GOOGLE_CALENDAR_AVAILABLE

    @staticmethod
    def has_credentials(credentials_file: Optional[str] = None) -> bool:
        """Check if credentials file exists."""
        if credentials_file:
            return os.path.exists(credentials_file)

        return (paths.google_auth_dir() / "credentials.json").exists()

    @staticmethod
    def check_token_validity(token_file: Optional[str] = None) -> dict:
        """
        Check if token file exists and get basic info about it.

        Returns:
            dict with keys: exists, valid, client_id, error
        """
        if not token_file:
            token_file = str(paths.google_auth_dir() / "token.pickle")

        result = {
            'exists': False,
            'valid': None,
            'client_id': None,
            'error': None
        }

        if not os.path.exists(token_file):
            return result

        result['exists'] = True

        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
                result['valid'] = creds.valid if hasattr(creds, 'valid') else None
                result['client_id'] = creds.client_id if hasattr(creds, 'client_id') else None
        except Exception as e:
            result['error'] = str(e)

        return result
