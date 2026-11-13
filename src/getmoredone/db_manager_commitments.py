"""The Google Calendar commitment cache: read, replace, dismiss.

Purpose: CIP-M1 -- a local copy of what the calendar said, per date, so the
         Plan screen never waits on the network and always knows how old its
         answer is.
Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#4-m1--the-commitment-store
Plan:    docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md

A mixin on ``DatabaseManager``, as ``db_manager_project_boards.py`` is, so the
commitment store is one file and ``db_manager.py`` does not grow by it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from .models import CalendarCommitment


class CommitmentDateError(ValueError):
    """A commitment was handed to a write for a date that write does not cover."""


class CommitmentNotDismissableError(ValueError):
    """Only a commitment the user cannot edit may be dismissed (CIP-M3.4, D9)."""


_COLUMNS = (
    "id", "event_id", "calendar_id", "commitment_date", "start_time",
    "end_time", "start_minutes", "end_minutes", "title", "is_all_day",
    "response_status", "transparency", "can_edit", "is_recurring_instance",
    "dismissed", "fetched_at", "created_at", "updated_at",
)


class DBManagerCommitmentsMixin:
    """The two narrow writers and the reads the Plan screen draws from."""

    def get_commitments(self, commitment_date: str) -> List[CalendarCommitment]:
        """Every cached commitment on one date, dismissed ones included, by start."""
        rows = self.db.conn.execute(
            """
            SELECT * FROM calendar_commitments
            WHERE commitment_date = ?
            ORDER BY is_all_day DESC, start_minutes, end_minutes, title
            """,
            (str(commitment_date),),
        ).fetchall()
        return [self._row_to_commitment(row) for row in rows]

    def get_commitment_fetch(self, commitment_date: str) -> Optional[dict]:
        """When this date was last read, and whether the last try failed.

        Purpose: CIP-M1.3 -- ``None`` is "never read", which is a different
                 answer from a dict with ``fetched_at`` set and no rows.
        Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#4-m1--the-commitment-store
        Tests:   tests/test_calendar_commitments.py::test_cipm13_three_states_of_a_date
        """
        row = self.db.conn.execute(
            """
            SELECT fetched_at, last_error, attempted_at, warning
            FROM calendar_commitment_fetches WHERE commitment_date = ?
            """,
            (str(commitment_date),),
        ).fetchone()
        if row is None:
            return None
        return {
            "fetched_at": row["fetched_at"],
            "last_error": row["last_error"],
            "attempted_at": row["attempted_at"],
            "warning": row["warning"],
        }

    def replace_commitments_for_dates(
        self,
        dates: Iterable[str],
        commitments: Iterable[CalendarCommitment],
        fetched_at: str,
        *,
        keep_calendars: Iterable[str] = (),
        keep_event_ids: Iterable[str] = (),
        warning: Optional[str] = None,
    ) -> int:
        """Replace exactly these dates' commitments with these, in one transaction.

        Purpose: CIP-M1.4, CIP-M1.5 -- the one writer a fetch uses.
        Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#4-m1--the-commitment-store
        Tests:   tests/test_calendar_commitments.py::test_cipm14_only_the_fetched_dates_change
                 tests/test_calendar_commitments.py::test_cipm14_a_failure_part_way_writes_nothing
                 tests/test_calendar_commitments.py::test_cipm15_dismissal_survives_a_refetch

        A commitment dated outside ``dates`` is refused before anything is
        written (``CommitmentDateError``): writing it would change a date this
        fetch never read. ``dismissed`` is carried over from the row it
        replaces, keyed on ``event_id`` and date; everything else comes from
        the fetch. Returns how many rows were written.

        D6 -- a read that skipped a calendar, or an event it could not parse,
        did not learn those meetings are gone. Their cached rows
        (``keep_calendars``, ``keep_event_ids``) stay, unless the read found
        the same event elsewhere, and ``warning`` is recorded so the screen
        does not call the date fully read.
        """
        keep_calendars = {str(c) for c in keep_calendars}
        keep_event_ids = {str(e) for e in keep_event_ids}
        dates = sorted({str(d) for d in dates})
        commitments = list(commitments)
        covered = set(dates)
        stray = sorted({c.commitment_date for c in commitments} - covered)
        if stray:
            raise CommitmentDateError(
                f"commitments for {', '.join(stray)} are outside the dates being replaced"
            )
        now = datetime.now().isoformat()
        written = 0
        with self.transaction() as conn:
            # Take the write lock before reading what to carry over. A plain
            # SELECT starts no transaction, so a dismissal committed by the
            # screen between that read and the DELETE below would be lost.
            conn.execute("UPDATE calendar_commitment_fetches SET warning = warning WHERE 0")
            for day in dates:
                existing = {
                    row["event_id"]: (row["id"], bool(row["dismissed"]))
                    for row in conn.execute(
                        "SELECT id, event_id, dismissed FROM calendar_commitments"
                        " WHERE commitment_date = ?",
                        (day,),
                    )
                }
                fresh_ids = {c.event_id for c in commitments if c.commitment_date == day}
                kept = [
                    self._row_to_commitment(row)
                    for row in conn.execute(
                        "SELECT * FROM calendar_commitments WHERE commitment_date = ?",
                        (day,),
                    )
                    if (row["calendar_id"] in keep_calendars or row["event_id"] in keep_event_ids)
                    and row["event_id"] not in fresh_ids
                ]
                conn.execute(
                    "DELETE FROM calendar_commitments WHERE commitment_date = ?",
                    (day,),
                )
                for commitment in kept:
                    self._insert_commitment(conn, commitment)
                for commitment in commitments:
                    if commitment.commitment_date != day:
                        continue
                    previous = existing.get(commitment.event_id)
                    if previous is not None:
                        # The same row id across reads, so a menu opened
                        # before a read still names its meeting after it.
                        commitment.id = previous[0]
                    # D9 -- an ignore holds only while the meeting is someone
                    # else's; one the user can now edit is changed in Google.
                    commitment.dismissed = bool(
                        previous is not None and previous[1] and not commitment.can_edit
                    )
                    commitment.fetched_at = fetched_at
                    commitment.updated_at = now
                    self._insert_commitment(conn, commitment)
                    written += 1
                conn.execute(
                    """
                    INSERT INTO calendar_commitment_fetches
                        (commitment_date, fetched_at, last_error, attempted_at, warning)
                    VALUES (?, ?, NULL, ?, ?)
                    ON CONFLICT(commitment_date) DO UPDATE SET
                        fetched_at = excluded.fetched_at,
                        last_error = NULL,
                        attempted_at = excluded.attempted_at,
                        warning = excluded.warning
                    """,
                    (day, fetched_at, fetched_at, warning),
                )
        return written

    def record_commitment_fetch_failure(
        self, dates: Iterable[str], error: str, attempted_at: str
    ) -> None:
        """Say these dates' last read failed, keeping what was known (CIP-M2.7, D6).

        The cached rows and the last good ``fetched_at`` are left alone, so a
        failed refresh shows the day it last knew, labelled with when.
        """
        with self.transaction() as conn:
            for day in sorted({str(d) for d in dates}):
                conn.execute(
                    """
                    INSERT INTO calendar_commitment_fetches
                        (commitment_date, fetched_at, last_error, attempted_at)
                    VALUES (?, NULL, ?, ?)
                    ON CONFLICT(commitment_date) DO UPDATE SET
                        last_error = excluded.last_error,
                        attempted_at = excluded.attempted_at
                    """,
                    (day, str(error), attempted_at),
                )

    def set_commitment_dismissed(self, commitment_id: str, dismissed: bool) -> CalendarCommitment:
        """Ignore one commitment on its date, or hold it again. Local only.

        Purpose: CIP-M3.4 / D9 -- someone else's meeting must not hold slots
                 with no way out. Nothing is sent to Google.
        Spec:    docs/spec_2026-11-08_calendar_into_the_plan.md#62-occupancy
        Tests:   tests/test_calendar_commitments.py::test_cipm34_dismissing_frees_the_slots_locally

        Refused for a commitment the user can edit: the honest gesture there
        is to change the real event, and batch 2 brings that to the Plan.
        """
        row = self.db.conn.execute(
            "SELECT * FROM calendar_commitments WHERE id = ?", (str(commitment_id),)
        ).fetchone()
        if row is None:
            raise ValueError(f"no commitment {commitment_id!r}")
        commitment = self._row_to_commitment(row)
        if commitment.can_edit:
            raise CommitmentNotDismissableError(
                "this meeting is yours to change in Google Calendar, so it cannot be ignored here"
            )
        with self.transaction() as conn:
            conn.execute(
                "UPDATE calendar_commitments SET dismissed = ?, updated_at = ? WHERE id = ?",
                (1 if dismissed else 0, datetime.now().isoformat(), commitment.id),
            )
        commitment.dismissed = bool(dismissed)
        return commitment

    def _committed_for(self, block_date: str, bounds) -> frozenset:
        """The boxes this date's commitments hold, read here so no writer can forget (D2)."""
        from .calendar_commitments import committed_slots

        return committed_slots(self.get_commitments(block_date), bounds)

    def _insert_commitment(self, conn, commitment: CalendarCommitment) -> None:
        values = (
            commitment.id, commitment.event_id, commitment.calendar_id,
            commitment.commitment_date, commitment.start_time, commitment.end_time,
            int(commitment.start_minutes), int(commitment.end_minutes),
            commitment.title or "", 1 if commitment.is_all_day else 0,
            commitment.response_status, commitment.transparency,
            1 if commitment.can_edit else 0,
            1 if commitment.is_recurring_instance else 0,
            1 if commitment.dismissed else 0, commitment.fetched_at,
            commitment.created_at, commitment.updated_at,
        )
        placeholders = ", ".join("?" for _ in _COLUMNS)
        conn.execute(
            f"INSERT INTO calendar_commitments ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
            values,
        )

    @staticmethod
    def _row_to_commitment(row) -> CalendarCommitment:
        return CalendarCommitment(
            id=row["id"],
            event_id=row["event_id"],
            calendar_id=row["calendar_id"],
            commitment_date=row["commitment_date"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            start_minutes=int(row["start_minutes"]),
            end_minutes=int(row["end_minutes"]),
            title=row["title"] or "",
            is_all_day=bool(row["is_all_day"]),
            response_status=row["response_status"],
            transparency=row["transparency"],
            can_edit=bool(row["can_edit"]),
            is_recurring_instance=bool(row["is_recurring_instance"]),
            dismissed=bool(row["dismissed"]),
            fetched_at=row["fetched_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
