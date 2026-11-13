"""A planned day -> Google Calendar.

Purpose: push the Plan screen's time blocks for one date out as timed events,
         and do it again later without duplicating or orphaning anything.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md
Tests:   tests/test_calendar_export.py

**This module imports no GUI toolkit, and must not.** What gets exported, what
it is called and what a second export does are decisions, not drawing, and
every one of them is provable headless.

The model: the day is the truth and the calendar is a copy of it. Each block
records the event it owns (``TimeBlock.calendar_event_id``), and every event
this module writes also carries that block's id back in its own private
properties. Those two halves do different jobs:

* the id on the block is how a re-export finds the event to update;
* the marker on the event is how a re-export finds events whose block is
  **gone** -- the only way to clean up after a deleted block without keeping a
  tombstone table, and it works from any machine the user plans on.

An event without our marker is never touched. It is somebody's real meeting.

Threading: ``export_day`` opens its own ``DatabaseManager`` from a path, the
way ``calendar_importer`` does, because it runs on a worker thread and the
screen's SQLite connection belongs to the main one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence

from .models import ActionItem, TimeBlock
from .time_block_layout import (
    DayBounds,
    block_title,
    build_day_grid,
    parse_hhmm,
    times_for_slot,
)

#: The private event properties every event this module creates carries, and
#: the exception the Google layer raises for an event that is no longer there.
#: Defined in ``google_calendar`` -- the layer that writes the markers, queries
#: them and raises the exception -- and re-exported here because this is the
#: module that gives them their meaning. One definition, and no import cycle.
from .google_calendar import (  # noqa: E402  (constants, not behaviour)
    BLOCK_DATE_PROPERTY,
    BLOCK_ID_PROPERTY,
    INHERIT_REMINDERS,
    CalendarEventMissing,
)

#: The line added to every exported event, so an event that reappears or moves
#: is traceable to the app that put it there. The user's own text comes first.
EXPORT_DESCRIPTION_LINE = "Planned in daVIPA."

#: The calendar written to when no setting says otherwise.
DEFAULT_CALENDAR_ID = "primary"

CREATE = "create"
UPDATE = "update"


@dataclass
class ExportEntry:
    """One block, resolved into the event it should become."""

    block_id: str
    summary: str
    start: datetime
    minutes: int
    action: str  # CREATE or UPDATE
    event_id: Optional[str] = None
    description: str = ""

    #: The calendar ``event_id`` is on, as recorded when it was created, or
    #: None for a row written before that was recorded -- which can only have
    #: been the default calendar. An id is meaningless against any other
    #: calendar, so the two always travel together.
    event_calendar_id: Optional[str] = None


@dataclass
class ExportPlan:
    """What an export would do, before anything is sent.

    The skip counters are the point of keeping this separate: a day can hold
    blocks that cannot become events, and the user is told how many and why
    rather than being shown a count that silently shrank (P2, P9).
    """

    block_date: str
    entries: List[ExportEntry] = field(default_factory=list)
    blocks_seen: int = 0
    skipped_unplaced: int = 0
    skipped_no_minutes: int = 0
    skipped_bad_time: int = 0

    @property
    def skipped(self) -> int:
        return self.skipped_unplaced + self.skipped_no_minutes + self.skipped_bad_time


@dataclass
class ExportOutcome:
    """What an export actually did.

    ``ok`` is derived from ``failed``, not from having reached the end of the
    function (P24): a run that tried six blocks and failed on six has finished,
    and is not a success.

    It says nothing about whether anything was *sent* -- a day with no blocks
    on it reports ``ok`` -- which is a weaker claim than this docstring used to
    make for it. Which of the two meanings the export should have is CE-A9 in
    ``BACKLOG.md``; the status line does not rely on either, because it reports
    the counts themselves.
    """

    block_date: str
    blocks_seen: int = 0
    created: int = 0
    updated: int = 0
    recreated: int = 0
    moved: int = 0
    deleted_orphans: int = 0
    vanished: int = 0
    skipped_unplaced: int = 0
    skipped_no_minutes: int = 0
    skipped_bad_time: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def exported(self) -> int:
        return self.created + self.updated + self.recreated + self.moved

    @property
    def skipped(self) -> int:
        return self.skipped_unplaced + self.skipped_no_minutes + self.skipped_bad_time

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "blocks_seen": self.blocks_seen,
            "created": self.created,
            "updated": self.updated,
            "recreated": self.recreated,
            "moved": self.moved,
            "deleted_orphans": self.deleted_orphans,
            "vanished": self.vanished,
            "skipped_unplaced": self.skipped_unplaced,
            "skipped_no_minutes": self.skipped_no_minutes,
            "skipped_bad_time": self.skipped_bad_time,
            "failed": self.failed,
        }

    def summary_line(self) -> str:
        """One line for the Plan screen's status, honest about all of it.

        Purpose: CE-M4.2 -- the counts the user needs, including the ones that
                 did not happen.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
        Tests:   tests/test_calendar_export.py::test_cem422_the_summary_line_names_every_skip

        A day with no blocks left is not the same as a run that did nothing:
        it is how a cancelled plan reaches the calendar, and the events it
        took off have to be reported (P24). Only a run with nothing seen,
        nothing removed and nothing failed says "nothing to export".
        """
        if not (self.blocks_seen or self.deleted_orphans or self.vanished
                or self.failed):
            return f"Nothing to export: no blocks planned for {self.block_date}"

        if self.blocks_seen:
            parts = [
                f"{self.exported} of {self.blocks_seen} block(s) exported to Google"
                f" Calendar for {self.block_date}"
            ]
        else:
            parts = [f"No blocks planned for {self.block_date}"]
        if self.created:
            parts.append(f"{self.created} new")
        if self.updated:
            parts.append(f"{self.updated} updated")
        if self.recreated:
            parts.append(f"{self.recreated} re-created")
        if self.moved:
            parts.append(f"{self.moved} moved to this calendar")
        if self.deleted_orphans:
            parts.append(f"{self.deleted_orphans} removed")
        if self.vanished:
            parts.append(f"{self.vanished} deleted while exporting")
        if self.skipped_unplaced:
            parts.append(f"{self.skipped_unplaced} skipped (not on the grid)")
        if self.skipped_no_minutes:
            parts.append(f"{self.skipped_no_minutes} skipped (no length)")
        if self.skipped_bad_time:
            parts.append(f"{self.skipped_bad_time} skipped (unreadable time)")
        if self.failed:
            parts.append(f"{self.failed} FAILED")
        return " — ".join([parts[0], ", ".join(parts[1:])]) if len(parts) > 1 else parts[0]


def _description_for(item: Optional[ActionItem]) -> str:
    """The event body: the user's own next step, then where it came from."""
    next_action = (getattr(item, "next_action", None) or "").strip() if item else ""
    if next_action:
        return f"{next_action}\n\n{EXPORT_DESCRIPTION_LINE}"
    return EXPORT_DESCRIPTION_LINE


def build_export_plan(
    blocks: Sequence[TimeBlock],
    items_by_id: Dict[str, ActionItem],
    block_date: str,
    bounds: Optional[DayBounds] = None,
) -> ExportPlan:
    """Decide what the day's blocks should become, sending nothing.

    Purpose: CE-M2.1 -- the whole decision, testable without a client.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m21
    Tests:   tests/test_calendar_export.py::test_cem212_every_placed_block_gets_one_entry

    A block with no box (``slot_index is None``) is **skipped, and counted**.
    It is drawn under "Outside the day" on the screen precisely because the
    app does not know when it happens; exporting it at whatever clock string
    its row happens to carry would put work on the calendar at a time nobody
    chose (P1 -- an unknown written down as a fact).
    """
    plan = ExportPlan(block_date=block_date)
    bounds = bounds if bounds is not None else DayBounds()

    try:
        day = datetime.strptime(block_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        # The day itself, not a block: nothing on it can be timed, and every
        # block is counted as such rather than the list coming back silently
        # empty (P2).
        plan.blocks_seen = len(blocks)
        plan.skipped_bad_time = plan.blocks_seen
        return plan

    # The same function the screen draws from, called with the same bounds, so
    # "on the grid" means on the grid the user is looking at. Checking
    # ``slot_index is not None`` instead exported blocks the day shows under
    # *Outside the day* -- the ones whose boxes Day End moved past, and the
    # ones the lunch hour was moved over.
    off_grid = {block.id for block in build_day_grid(blocks, bounds).outside}

    for block in blocks:
        plan.blocks_seen += 1

        if block.id in off_grid:
            plan.skipped_unplaced += 1
            continue

        minutes = int(block.planned_minutes or 0)
        if minutes <= 0:
            plan.skipped_no_minutes += 1
            continue

        # Derived from the box, never read from ``block.start_time``: the box
        # is what the Plan screen draws. Before PD-M14.4 (2026-11-13) a Day
        # Start change left every stored time behind, and exporting the record
        # put blocks on other people's calendars at an hour the screen did not
        # show (P19). PD-M14.4 now renumbers and PD-M14.7 repairs old rows, but
        # a box with an unreadable or off-box time still exists, so the box
        # stays the source.
        start_minutes = parse_hhmm(times_for_slot(block.slot_index, minutes, bounds)[0])
        start = day.replace(hour=start_minutes // 60, minute=start_minutes % 60)
        item = items_by_id.get(block.item_id) if block.item_id else None
        event_id = getattr(block, "calendar_event_id", None) or None
        event_calendar_id = (
            getattr(block, "calendar_event_calendar_id", None) or None
        )

        plan.entries.append(
            ExportEntry(
                block_id=block.id,
                summary=block_title(block, item),
                start=start,
                minutes=minutes,
                action=UPDATE if event_id else CREATE,
                event_id=event_id,
                event_calendar_id=event_calendar_id,
                description=_description_for(item),
            )
        )

    return plan


def _private_properties(event: Dict[str, Any]) -> Dict[str, Any]:
    """The event's private extended properties, as a dict, whatever it holds."""
    outer = (event or {}).get("extendedProperties")
    if not isinstance(outer, dict):
        return {}
    private = outer.get("private")
    return private if isinstance(private, dict) else {}


def _marker_of(event: Dict[str, Any]) -> Optional[str]:
    """The block id an event claims, or ``None`` if it carries no marker."""
    value = _private_properties(event).get(BLOCK_ID_PROPERTY)
    return str(value) if value else None


def _marker_date_of(event: Dict[str, Any]) -> Optional[str]:
    """The day an event claims to belong to, or ``None`` if it claims none.

    Purpose: CE-M2.6b -- the sweep deletes, and it must not delete on the
             strength of the date filter alone.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests:   tests/test_calendar_export.py::test_cem266_an_event_marked_for_another_day_is_never_deleted

    The block id is already re-checked here rather than trusted to the query
    (P6). The date was not, and it is the other half of the same marker: an
    event carrying our properties but another day's date is an event this run
    has no business removing, however it came to be on the list -- a copy the
    user made onto another date (Google copies private properties), an
    instance of one they made recurring, or a filter that simply did not do
    what the query asked.
    """
    value = _private_properties(event).get(BLOCK_DATE_PROPERTY)
    return str(value) if value else None


def _items_for(db_manager, blocks: Sequence[TimeBlock]) -> Dict[str, ActionItem]:
    """The action items the day's item blocks point at, by id."""
    items: Dict[str, ActionItem] = {}
    for block in blocks:
        if not block.item_id or block.item_id in items:
            continue
        item = db_manager.get_action_item(block.item_id)
        if item is not None:
            items[block.item_id] = item
    return items


def export_day(
    block_date: str,
    *,
    client,
    db_path: Optional[str] = None,
    db_manager=None,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    bounds: Optional[DayBounds] = None,
) -> ExportOutcome:
    """Push one planned day to Google Calendar, idempotently.

    Purpose: CE-M2.4 -- the one entry point the UI calls.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m24
    Tests:   tests/test_calendar_export.py::test_cem251_a_second_export_updates_and_creates_nothing

    ``client`` is injected and duck-typed (``create_event``, ``update_event``,
    ``delete_event``, ``list_day_events``), so no test here reaches the
    network and nothing in this module can construct a real authenticated
    manager by accident.

    ``db_path`` opens a connection this call owns, which is what makes it safe
    on the worker thread the screen starts; ``db_manager`` is for callers
    already on the thread that owns one (the tests, and nothing else).
    """
    owned = False
    if db_manager is None:
        from .db_manager import DatabaseManager  # local: keeps the import cheap

        db_manager = DatabaseManager(db_path=db_path)
        owned = True

    try:
        blocks = db_manager.get_time_blocks(block_date)
        plan = build_export_plan(
            blocks, _items_for(db_manager, blocks), block_date, bounds=bounds
        )

        outcome = ExportOutcome(
            block_date=block_date,
            blocks_seen=plan.blocks_seen,
            skipped_unplaced=plan.skipped_unplaced,
            skipped_no_minutes=plan.skipped_no_minutes,
            skipped_bad_time=plan.skipped_bad_time,
        )

        live_event_ids: Dict[str, str] = {}

        for entry in plan.entries:
            # Per entry, so one block's failure is one block's failure and the
            # rest of the day still reaches the calendar (P2).
            try:
                if entry.action == UPDATE and not _same_calendar(
                    entry.event_calendar_id, calendar_id
                ):
                    # The export calendar changed in settings since this block
                    # was last exported. An event id only means anything
                    # against the calendar it was made on, so there is nothing
                    # to update here: the old event is taken off the old
                    # calendar and a new one made on the configured one.
                    #
                    # Without this the old event was unreachable -- the sweep
                    # only lists the configured calendar, so it never saw it,
                    # and the id in the database named an event nothing would
                    # ever look for again (found by a cold review pass).
                    #
                    # Delete first. If the create then fails, the block keeps
                    # an id for an event that is gone, and the next export's
                    # ``CalendarEventMissing`` path makes it again. The other
                    # order can leave two events for one block.
                    try:
                        client.delete_event(
                            entry.event_id,
                            calendar_id=entry.event_calendar_id or DEFAULT_CALENDAR_ID,
                        )
                    except CalendarEventMissing:
                        # Already gone from the old calendar: the end state is
                        # the one being asked for.
                        pass

                    event_id = _create(client, entry, plan.block_date, calendar_id)
                    if not db_manager.set_block_calendar_event_id(
                        entry.block_id, event_id, calendar_id
                    ):
                        outcome.vanished += 1
                        continue
                    outcome.moved += 1
                    live_event_ids[entry.block_id] = event_id
                    continue

                if entry.action == UPDATE:
                    try:
                        _update(client, entry, calendar_id)
                        outcome.updated += 1
                        live_event_ids[entry.block_id] = entry.event_id
                        continue
                    except CalendarEventMissing:
                        # Deleted in Google by hand. Make it again rather than
                        # reporting a failure the user cannot act on.
                        event_id = _create(client, entry, plan.block_date, calendar_id)
                        if not db_manager.set_block_calendar_event_id(
                            entry.block_id, event_id, calendar_id
                        ):
                            outcome.vanished += 1
                            continue
                        outcome.recreated += 1
                        live_event_ids[entry.block_id] = event_id
                        continue

                event_id = _create(client, entry, plan.block_date, calendar_id)
                # Only ever from the id in the response: a block must not be
                # recorded as exported because a call was made (P42).
                if not db_manager.set_block_calendar_event_id(
                    entry.block_id, event_id, calendar_id
                ):
                    # The block was deleted while this export was talking to
                    # Google: the day stays clickable while the worker runs,
                    # and an UPDATE matching no rows is not an error to
                    # SQLite. Counted, because "created" would be a success
                    # for work the user has thrown away (P6).
                    #
                    # The event is *not* deleted here. It is simply left out
                    # of ``live_event_ids``, so the sweep below -- which
                    # re-reads the day and finds no block for this marker --
                    # removes it, through the one code path that deletes
                    # anything. Deleting it here as well reported one stuck
                    # event as two failures, and reported a failure even when
                    # the sweep's attempt had succeeded (P1).
                    outcome.vanished += 1
                    continue
                outcome.created += 1
                live_event_ids[entry.block_id] = event_id
            except Exception as error:  # noqa: BLE001 - counted, named, reported
                outcome.failed += 1
                if len(outcome.errors) < 3:
                    outcome.errors.append(f"{entry.summary}: {error}")

        # Read again, rather than reuse the pre-flight snapshot. Everything
        # between the two reads happened over the network, with the Plan
        # screen still clickable: a block deleted in that window is still in
        # ``day_block_ids``, so the sweep would protect the event of a block
        # that no longer exists and leave it on the calendar (P6). A block
        # *added* in that window is in the re-read with no confirmed event,
        # which the sweep already leaves alone.
        day_block_ids = {
            block.id for block in db_manager.get_time_blocks(block_date)
        }

        _sweep_orphans(
            client=client,
            db_manager=db_manager,
            block_date=block_date,
            calendar_id=calendar_id,
            day_block_ids=day_block_ids,
            live_event_ids=live_event_ids,
            outcome=outcome,
        )

        return outcome
    finally:
        if owned:
            db_manager.close()


def _same_calendar(recorded: Optional[str], configured: str) -> bool:
    """Whether a recorded calendar and the configured one are the same place.

    Purpose: CE-M2.5 -- ``None`` is the default calendar, not "no calendar":
             every row written before the calendar was recorded was written by
             an export that could only write to ``primary``.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m25
    Tests:   tests/test_calendar_export.py::test_cem255b_a_row_from_before_the_column_is_read_as_the_default
    """
    return (recorded or DEFAULT_CALENDAR_ID) == (configured or DEFAULT_CALENDAR_ID)


def _create(client, entry: ExportEntry, block_date: str, calendar_id: str) -> str:
    """Create one event and return the id the API gave back."""
    event = client.create_event(
        summary=entry.summary,
        start_datetime=entry.start,
        duration_minutes=entry.minutes,
        description=entry.description,
        calendar_id=calendar_id,
        private_properties={
            BLOCK_ID_PROPERTY: entry.block_id,
            BLOCK_DATE_PROPERTY: block_date,
        },
        # CE-M3.5 -- a day of blocks is not a day of meetings. Without this
        # every block exported would carry the meeting dialog's ten-minute
        # popup and override whatever the user set on the calendar itself.
        reminders=INHERIT_REMINDERS,
    )
    event_id = (event or {}).get("id")
    if not event_id:
        raise RuntimeError("Google Calendar returned no event id")
    return str(event_id)


def _update(client, entry: ExportEntry, calendar_id: str) -> None:
    client.update_event(
        event_id=entry.event_id,
        summary=entry.summary,
        start_datetime=entry.start,
        duration_minutes=entry.minutes,
        description=entry.description,
        calendar_id=calendar_id,
    )


def _sweep_orphans(
    *,
    client,
    db_manager,
    block_date: str,
    calendar_id: str,
    day_block_ids: set,
    live_event_ids: Dict[str, str],
    outcome: ExportOutcome,
) -> None:
    """Remove the events of blocks that are no longer on the day.

    Purpose: CE-M2.6 -- the only part of this module that deletes anything.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m26
    Tests:   tests/test_calendar_export.py::test_cem262_an_unmarked_event_is_never_deleted

    Four rules, in order, and every one of them is a decision not to delete
    something:

    * an event with no marker of ours is never touched, whatever it is called
      and whenever it starts. The marker is checked here and not merely asked
      for in the query, because a filter passed to an API is an argument, not
      a guarantee (P6 -- reconcile against the thing itself).
    * an event whose marker names **another day** is never touched either
      (CE-M2.6b). Both halves of the marker are checked for the same reason:
      a copy of an exported event made onto another date carries the private
      properties with it, and so does every instance of one turned into a
      recurring event.
    * an event whose marker names a block **still on this day** for which
      this run confirmed no event is kept. That covers both a block whose
      call failed -- a 500 on an update must not escalate into deleting the
      event (P1: a transient failure is not a verdict) -- and a block this
      run skipped for having no box or no length, which the export never
      touched and so has no business removing.
      (There is deliberately no separate "did it fail?" set: it would be a
      guard no test could tell from this one, and mutation proved exactly
      that.)
    * an event whose marker names a block still on this day, which this run
      confirmed under a *different* event id, is a duplicate only a previous
      bug could have made, and is removed.

    What is left is the real orphan: a marker naming a block that is no longer
    on the day at all.
    """
    try:
        events = client.list_day_events(block_date, calendar_id=calendar_id) or []
    except Exception as error:  # noqa: BLE001
        # A sweep that cannot list is a sweep that did not run. Reported, not
        # retried silently and not written off as "nothing to remove".
        outcome.failed += 1
        if len(outcome.errors) < 3:
            outcome.errors.append(f"listing {block_date}: {error}")
        return

    for event in events:
        block_id = _marker_of(event)
        if not block_id:
            continue

        # CE-M2.6b -- our marker, but another day's. Not this run's to remove.
        marked_date = _marker_date_of(event)
        if marked_date is not None and marked_date != block_date:
            continue

        event_id = (event or {}).get("id")
        if not event_id:
            continue

        if block_id in day_block_ids:
            live = live_event_ids.get(block_id)
            # ``live is None`` is the "we confirmed nothing for this block"
            # case: skipped, or its own call failed. Either way, not ours to
            # delete on this run.
            if live is None or live == event_id:
                continue

        try:
            client.delete_event(event_id, calendar_id=calendar_id)
            outcome.deleted_orphans += 1
        except CalendarEventMissing:
            # Already gone. Nothing to report: the end state is the one asked
            # for, and counting it as removed is the honest answer.
            outcome.deleted_orphans += 1
        except Exception as error:  # noqa: BLE001
            outcome.failed += 1
            if len(outcome.errors) < 3:
                outcome.errors.append(f"removing {event_id}: {error}")
            continue

        # A block can still exist and hold a stale id -- its event was deleted
        # in Google and re-created under a new one. Clear the id only when the
        # block still points at the event just removed, so this never stamps
        # on the id this very run wrote (P6: check the row, do not assume it).
        block = db_manager.get_time_block(block_id)
        if block is not None and block.calendar_event_id == event_id:
            db_manager.set_block_calendar_event_id(block_id, None)
