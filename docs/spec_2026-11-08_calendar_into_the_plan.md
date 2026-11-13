# Spec — Google Calendar into the Plan (2026-11-08)

Status: **read half built 2026-11-13** (batch 1: CIP-M0.1, M0.3a, M1 to M3,
M5), from `docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md`,
which also records the decisions this spec left open (D1 to D13). Not walked
on screen. **Batch 2, editing (CIP-M4, M1.6, M0.3b), built 2026-11-13**
from `docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_editing.md`,
which records decisions E1 to E10; not walked, and no write has reached live
Google. **The week view (M6) is not started.** Criteria and tests: `docs/spec_coverage.md`, *Google Calendar into
the Plan, read half*.

Source: user requirement, 2026-11-08 — *"I want to read my google calendar and
put items in the day plan so I know what to plan around. Eventually i want to
look at the next 7 days for this. (Today Action Items, 7 days for planning)."*
Four scope decisions were taken the same day and are recorded in §8.

Related, and read before writing this:
[`docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md`](implementation_plan_2026-11-08_plan_calendar_export.md)
(the other direction, built 2026-11-08) and
[`docs/unused-docs/spec_coverage_2026-11-08_plan_calendar_export.md`](spec_coverage_2026-11-08_plan_calendar_export.md).
Several rules below exist only because of what that batch established.

---

## 1. What this is for

The Plan screen is a fixed grid of half hours. Today it shows only what the
user put there. It does not show the 10:00 that is already gone to a standup,
so a day can be planned full and then collide with the calendar the moment it
starts.

This feature puts the calendar's **commitments** on the grid: the hours that
are not available to plan into. The user plans around them — and where the
calendar itself is wrong or movable, they change it from inside the day plan
rather than leaving for Google and coming back.

### 1.1 What, when, and the difference

> **An action item is *what* has to be done. A time block is *when* you decided
> to do it. A commitment is *when* something was decided for you.**

Three different things, and the three are why both calendar features exist
side by side:

- A meeting creates **work**. "Board meeting Thursday 14:00" means a board
  pack has to be written — and that work needs a block, probably on Wednesday,
  certainly *before* the meeting. That is `calendar_importer.py`'s job: the
  event becomes an action item, which is a *what* with no *when* yet.
- The same meeting also **takes an hour**. Thursday 14:00–15:00 is not
  available to plan into. That is this feature's job.

So one calendar event can legitimately produce both an action item and a
commitment, and they are not duplicates of each other. §2.1 makes that a rule,
because it is exactly the sort of apparent redundancy a later reviewer would
"tidy up".

### 1.2 Two phases, one data layer

- **Phase 1 — today.** The Plan screen's selected day shows its commitments,
  the grid refuses to plan into them, and they can be edited in place.
- **Phase 2 — the next seven days.** A planning view over a date range: where
  the committed hours are, and therefore where the room is.

Phase 2 is a **UI** addition, not a second implementation. Every function in
M1–M3 is specified over a *date range* from the start, with "today" being a
range of one. Fetching seven days must be one paginated list call, not seven.

---

## 2. Scope

### In

- Reading events from the calendars the user has connected, for a date range.
- Caching them locally, per date, with the time they were read.
- Drawing them on the Plan grid for the selected day, and **refusing** to plan
  into the slots they hold.
- **Editing a commitment from inside the Plan screen** — move, resize, retitle,
  delete — which writes the change to Google (M4).
- A week view (phase 2) over the same cache.

### Out

- **RSVP.** Accepting, declining or proposing a new time is not in this feature.
- **Creating a calendar event from the Plan screen.** The export (CE, built
  2026-11-08) already turns a block into an event; a second way to put
  something new on the calendar would be a third answer to the same question.
- **Changing the export.** It keeps working exactly as it does. §6.1 is the one
  place the two features touch.
- **Attendees, rooms, conferencing, recurrence rules.** A commitment the Plan
  screen can edit is a time and a title. Anything structural belongs in Google
  Calendar, and the Plan screen must not silently flatten it (CIP-M4.6).

### 2.1 Both calendar features stay, and neither is the other

`src/getmoredone/calendar_importer.py` creates **open action items** from
events 14 days ahead, tagged `who="Calendar"`, `group="CALENDAR"`, linked by
`ItemLink`. It stays, unchanged by this feature.

| ID | Criterion |
|---|---|
| CIP-M0.1 | One calendar event may produce both an action item (via the importer) and a commitment (via this feature). Neither suppresses the other, and a test asserts both exist for the same event — the apparent duplication is the design |
| CIP-M0.2 | Where an action item is linked to an event by `ItemLink`, and a commitment for that same event is on the day being planned, the Plan screen can place that item's block in the free slots **before** the commitment, and offers the latest such position as the default. This is the prep-before-the-meeting case and it is the point of having both |
| CIP-M0.3 | A commitment is never confused for the work it caused: deleting the action item does not touch the commitment, and deleting the commitment (M4) does not touch the action item. Each is deleted where it lives |

---

## 3. The decision that matters: commitments are not `time_blocks` rows

A commitment is stored in **its own table** and drawn as an occupied region of
the grid. It is never a row in `time_blocks`. Five separate mechanisms make the
alternative wrong:

1. **`BlockType.normalize` coerces anything it does not recognise to `ITEM`**
   (`src/getmoredone/models.py:492`). A row stored with a new
   `block_type="commitment"` is read as an *item block* by every code path that
   normalizes, including older builds and `_row_to_time_block`.
2. **The export sends every item block on the grid to Google.** So a meeting
   stored as a block would be exported back to the calendar it came from, as a
   new event, on every export — forever. The export's duplicate guards do not
   help: the event it creates is a genuinely new event carrying the app's own
   marker, which the sweep then protects.
3. **An edit to a block stays local; an edit to a commitment goes to Google.**
   They are two different write paths with two different failure modes, and
   one table cannot carry both without every writer having to ask which kind of
   row it is holding.
4. **`total_planned_minutes(blocks)`** means "how much of the day did I plan".
   A meeting is not planned minutes; it is minutes that were never available.
5. **Blocks have an item, a priority band and a colour derived from it.** A
   commitment has none of those and must not be priority-coloured — a colour
   the eye reads as information, carrying none, is a lie.

**Lunch is the precedent.** Lunch is not a block: it is a property of
`DayBounds`, it occupies slots (`Slot.is_lunch`), and `can_place` refuses a
block across it (`SlotRefusal.CROSSES_LUNCH`). A commitment is the same shape of
thing — a region of the grid that is not available — and the implementation
follows that path, not the block path.

---

## 4. M1 — the commitment store

A local cache of what the calendar said, per date, so the Plan screen never
waits on the network and always knows how old its answer is.

| ID | Criterion |
|---|---|
| CIP-M1.1 | A `calendar_commitments` table, created on fresh databases and added by a guarded idempotent migration in `database.py`, in the established per-column style. Columns: `id`, `event_id`, `calendar_id`, `commitment_date` (`YYYY-MM-DD`), `start_time` / `end_time` (local `HH:MM`), `start_minutes` / `end_minutes` (minutes from local midnight), `title`, `is_all_day`, `response_status`, `transparency`, `can_edit` (CIP-M4.1), `is_recurring_instance`, `dismissed` (CIP-M3.4), `fetched_at`, `created_at`, `updated_at` |
| CIP-M1.2 | A `CalendarCommitment` dataclass in `models.py`, appended last so positional construction of existing models is unchanged |
| CIP-M1.3 | A per-date fetch record: when that date was last read and whether the read succeeded. A date never read is distinguishable from a date read and found empty — a day with no meetings and a day we have never asked about must not look the same |
| CIP-M1.4 | One narrow writer for fetches: `replace_commitments_for_dates(dates, commitments, fetched_at)` replaces whole dates atomically, in one transaction. A fetch covering 2026-11-09 to 2026-11-15 replaces those seven dates and touches no other date. A partial write must not be observable |
| CIP-M1.5 | `dismissed` survives a refetch of the same event on the same date, keyed on `event_id` + `commitment_date`. Everything else about the row is replaced from Google |
| CIP-M1.6 | A second narrow writer for confirmed edits: `apply_commitment_edit(...)`, used only by M4 after Google has confirmed, so the cache is never ahead of the calendar (P6 — a status that says "moved" is checked against the thing it claims) |

Why minutes as well as `HH:MM`: the grid works in minutes, and the export
batch's third cold pass established that deriving the same time twice in two
places is how the two answers drift apart. One parse, at write time, stored.

---

## 5. M2 — the read

| ID | Criterion |
|---|---|
| CIP-M2.1 | `fetch_commitments(start_date, end_date, *, client, calendar_ids)` in a new GUI-free module (`calendar_commitments.py`), returning parsed `CalendarCommitment` objects and a per-date result. One `events().list` call per calendar for the whole range, paginated, `singleEvents=True`, `orderBy=startTime`, bounded by `timeMin`/`timeMax` |
| CIP-M2.2 | It uses the existing `GoogleCalendarManager` with `allow_interactive=False`, so a lapsed sign-in raises `AuthenticationRequired` and is reported rather than opening a browser on a worker thread. Timeout, retry and the 403-reason classification come from the existing client unchanged |
| CIP-M2.3 | Timed events are converted to **local wall-clock** minutes from midnight, using the event's own offset. The grid is wall clock; one conversion, at the boundary, stored |
| CIP-M2.4 | All-day events (`start.date`, no `dateTime`) are stored with `is_all_day=1` and hold no slots (CIP-M3.8) |
| CIP-M2.5 | Exclusion rules, each independently tested and each **counted** so the user can be told what was left out: `status == "cancelled"`; the user's own `responseStatus == "declined"`; `transparency == "transparent"` (the calendar's own word for "this does not make me busy"); and any event carrying the app's own `gmd_block_id` marker (§6.1) |
| CIP-M2.6 | An event that cannot be parsed is skipped and counted by name, never guessed at — the rule the export follows for a block it cannot time |
| CIP-M2.7 | A failed fetch leaves the previous cache in place and records the failure. A day whose refresh failed shows what it last knew, labelled with when (CIP-M5.4), and never silently shows an empty day |
| CIP-M2.8 | Where several calendars are read, the same event appearing on two of them (a shared calendar plus an invitation) is one commitment, deduplicated on `event_id`, and **the copy on the calendar listed first decides** whether it is left out and whether it is editable. *(Changed 2026-11-13 from "`can_edit` is the most permissive of the copies": `organizer.self` and `attendees[].self` describe the calendar a copy is on, so a colleague's shared copy of a meeting the user declined says accepted and organiser. Found by the batch-1 review.)* |

---

## 6. M3 — the grid

### 6.1 The rule that keeps the two directions from eating each other

The export stamps every event it creates with `gmd_block_id` in
`extendedProperties.private`. Those events **are** the user's plan, sitting on
Google. Read back as commitments they would appear as constraints on the very
blocks that created them: export a full day, refresh, and every slot would be
held by its own shadow — and `can_place` would then refuse to move any block
anywhere.

| ID | Criterion |
|---|---|
| CIP-M3.1 | An event carrying `gmd_block_id` is never a commitment. Adversarial test (P7): a day is exported, the calendar is read back, and the grid is unchanged — same slots free, same blocks movable |

This is the highest-risk rule in the feature, and the one a reviewer without
the export's context would not think to look for, so it gets its own criterion
rather than a line inside CIP-M2.5.

### 6.2 Occupancy

| ID | Criterion |
|---|---|
| CIP-M3.2 | A commitment holds every slot its clock times **touch**: start rounded down to the slot boundary, end rounded up. A 09:50–10:00 meeting holds the 09:30 slot. Over-reserving is the safe direction — a block planned into a half-eaten slot is a collision the user cannot see |
| CIP-M3.3 | `can_place` gains a fourth named refusal, `SlotRefusal.SLOT_COMMITTED`, alongside `CROSSES_LUNCH`, and takes the day's commitments the way it takes its blocks. Every call site that maps a refusal to a sentence maps this one too — `test_tgm23_each_refusal_has_its_own_reason` is the existing guard and must cover four values by **exact count**, never a floor |
| CIP-M3.4 | A commitment the user **cannot** edit (CIP-M4.1) can be dismissed for that date, which releases its slots and marks it on screen as ignored-but-still-on-your-calendar. A commitment the user *can* edit has no dismiss: the honest gesture there is to move or delete the real event (M4). Dismissal is local, survives a refetch, and never touches Google |
| CIP-M3.5 | Commitments do not count toward `total_planned_minutes`, and do not count toward `MAX_BLOCKS_PER_SLOT` (4). A committed slot is refused outright, not counted as one of four occupants |

### 6.3 Where they are drawn

| ID | Criterion |
|---|---|
| CIP-M3.6 | A timed commitment inside the drawn day is a region of the grid, visually distinct from a block and from lunch, labelled with its true clock times and its title. Per the theme rules: no hard-coded colours, a semantic token added to `theme.py`, never the screen's one "primary", and not priority-coloured |
| CIP-M3.7 | A timed commitment outside the day's hours **extends the drawn day**, the way a block outside the hours does (`extended_span`, PD-M14). A 07:00 standup pulls the grid up to 07:00 rather than hiding. See §9 |
| CIP-M3.8 | All-day commitments are drawn in a strip above the grid, not in it, and hold no slots: "I am travelling today" is not a reason the 10:00 is unavailable |
| CIP-M3.9 | Two overlapping commitments are both shown, and the union of their slots is held |

---

## 7. M4 — editing the calendar from inside the Plan

The user must plan around the calendar, but the calendar is not sacred: a
meeting the user owns can be moved to make room, from the grid, without
leaving the app.

| ID | Criterion |
|---|---|
| CIP-M4.1 | Whether a commitment can be edited is decided from the event, not guessed: the user is the organizer (`organizer.self`), or `guestsCanModify` is true. Stored as `can_edit` at fetch time. A commitment that cannot be edited is **not draggable and not resizable** — the gesture is refused before it is made, rather than attempted and failed on a 403 |
| CIP-M4.2 | Dragging a commitment to another slot, or resizing it, writes the new start and end to Google via the existing `update_event` — non-interactive client, existing timeout, retry and 403-reason classification |
| CIP-M4.3 | Retitling a commitment in place writes `summary` and nothing else, via the same preserve-the-rest update path the export relies on. Nothing the Plan screen does not understand is overwritten (CIP-M4.6) |
| CIP-M4.4 | Deleting a commitment from the Plan deletes the Google event, and asks first, naming the event and saying it will be removed from the calendar. Per the global rule, this is an irreversible outward-facing action |
| CIP-M4.5 | **The cache is never ahead of Google.** The commitment stays where it was until the write is confirmed; a failed write leaves the grid exactly as it was and says what failed. No optimistic move that silently diverges from the calendar (P6, and "fix the code, don't fake the state") |
| CIP-M4.6 | An edit to one occurrence of a recurring event changes **that occurrence only**, and says so before it is made. Attendees, conferencing, reminders, recurrence and description are carried through the update untouched — the Plan screen edits a time and a title, and flattens nothing |
| CIP-M4.7 | One calendar write at a time per database, keyed outside the screen instance, and never concurrent with a fetch of the same dates. The export's `_EXPORTS_IN_FLIGHT` is the pattern; the reason is the same — leaving Plan and returning builds a new screen |
| CIP-M4.8 | Every write path refuses cleanly with no credentials, no libraries, or a lapsed sign-in, the way the export's four prerequisite refusals do, and re-enables the UI rather than leaving it dead |

*Built 2026-11-13 (batch 2).* How the plan settled what this table leaves open:
a move is a drag to a box and keeps the meeting's length; a length is chosen
from the right-click menu; a move may land only on empty boxes; an all-day or
over-midnight meeting is renamed or deleted, not moved; guests are emailed only
when the user says yes; and every write first checks Google's copy against the
Plan's. Decisions E1 to E10 in the plan.

---

## 8. M5 — the Plan screen (phase 1), M6 — the week (phase 2), M7 — docs

| ID | Criterion |
|---|---|
| CIP-M5.1 | The Plan screen opens and paints **without any network call**, exactly as it does today. Commitments come from the cache. A machine with no credentials, no network or no connected account sees today's Plan screen unchanged |
| CIP-M5.2 | A refresh control in the Plan header, secondary style, disabled the instant it is pressed and re-enabled when the fetch finishes or fails — with a server-side guard, per the global rule on buttons that start background work |
| CIP-M5.3 | The fetch runs on a worker thread and the screen is updated on the Tk thread. One fetch per `(database, date range)` at a time, keyed outside the screen instance |
| CIP-M5.4 | The age of the answer is always on screen: *"Calendar as of 09:14"*, or *"Calendar not read for this day"*, or the failure. Never a bare empty grid that might mean "nothing on" and might mean "we never asked" |
| CIP-M5.5 | Opening a date whose cache is older than the staleness window (§9, 15 minutes, in config) refreshes it automatically, once, in the background |
| CIP-M6.1 | A seven-day planning view: for each of the next seven days, its committed hours and its free hours, from one fetch over the range |
| CIP-M6.2 | The week view reads the same cache and the same functions as the day. No second parse, no second occupancy rule |
| CIP-M7.1 | Docs in the same change: `docs/USER_GUIDE.md`, `docs/google-calendar-setup.md`, `CHANGELOG.md`, `NOTES.md`, `docs/DOCUMENTATION_INDEX.md`, and a handoff note from `.agents/templates/handoff-note.md` |

---

## 9. Decisions taken, 2026-11-08

Answers to the four questions this spec was drafted with. Recorded rather than
deleted, so the next reader sees what was chosen over what.

| # | Question | Decision |
|---|---|---|
| Q1 | What happens to `calendar_importer.py`? | **Both stay.** An action item is *what* has to be done; a commitment is *when* something is already decided. One event may produce both, and the work a meeting causes often needs a block *before* that meeting. §1.1 and CIP-M0.1–M0.3 |
| Q2 | Binding or advisory? | **Binding — the user works around the calendar.** And where the calendar is theirs to change, they change it from inside the day plan (M4). This replaced a read-only design: the original draft had writes out of scope entirely. Local dismissal survives only for commitments the user has no right to edit (CIP-M3.4) |
| Q3 | Which calendars? | **A list setting, defaulting to `["primary"]`**, read as a list from the first commit so a second calendar is a setting change rather than a migration and a second code path |
| Q4 | Staleness window | **15 minutes**, in config, not a constant |

### Still open

- **Dismissal at all.** CIP-M3.4 keeps it only for events the user cannot edit.
  If that case turns out to be rare in practice, dropping it removes a column,
  a flag and a merge rule. Worth revisiting after phase 1 is in use.
- **Whether the week view is editable.** M6 is specified read-only. Dragging a
  meeting across days is a bigger gesture than moving it within one, and it is
  not needed for "where is my room".

---

## 10. Known hazards, named now

- **PD-M14 is in flight.** Another session is changing exactly the
  `time_block_layout.py` surface CIP-M3.3 and CIP-M3.7 extend —
  `extended_span`, the drawn span, the outside-the-day group. This must not
  start building until that batch is committed and pushed, per *One build batch
  at a time* in `CLAUDE.md`. Writing this spec into a new file of its own is
  the read-only work that section explicitly allows.
- **Writes make this a bigger batch than it looks.** The read half (M1–M3) is
  self-contained and testable with a fake client. M4 is outward-facing,
  irreversible in one case, and touches other people's calendars. **M1–M3 and
  M5 should ship as one batch, M4 as a second**, so the editing path gets its
  own review sweeps rather than riding along with the plumbing.
- **Wall clock, again.** CIP-M2.3 converts to local wall clock because the grid
  is wall clock. Same decision as `BACKLOG.md` CE-A17 and CE-A21, and it should
  be written down once for both directions rather than decided twice.
- **`SlotRefusal` has three values and four call sites.** Adding a fourth
  touches every one, and the existing guard asserts by exact count. A refusal
  that reaches the user as a generic message is the `DAY_TOO_FULL` lesson that
  enum was created to end.
- **Nothing here is testable against live Google.** Every criterion is
  verifiable with a fake client, as the export batch's are; the live path (real
  OAuth, real pagination, real rate limits, real permissions) is
  integration-only and will be flagged as untested rather than implied by a
  mock.

---

## 11. Not code-testable

| Item | Proposed human review |
|---|---|
| That a commitment reads as "not yours" at a glance, rather than as an odd block | Look at a day holding a meeting, a lunch, a buffer and an item block, in both themes |
| That an uneditable commitment is visibly uneditable before the gesture | Try to drag someone else's meeting |
| That the week view answers "where is my room" in one look | Open it on a real week and try to find the free afternoon |
| That prep-before-the-meeting (CIP-M0.2) is the placement actually wanted | Plan a real week containing a meeting that needs preparing for |

---

## 12. What the plan step must add

Per `~/.claude/CLAUDE.md`: every criterion above restated with its **named
automated test**, the implementation order with dependencies, and any criterion
that cannot be made code-testable flagged with a human-review proposal (§11 is
the start of that list). The batch split in §10 is a recommendation to that
plan, not a decision already taken. Nothing gets built until that plan is
approved too.
