# Implementation plan — Export Plan to Google Calendar (2026-11-08)

Status: **approved 2026-11-08 and built.** M1-M5 implemented. **Four cold
review passes have run and the budget is closed**: the fourth produced nothing
of high severity, which is where `CLAUDE.md` says to stop. The manual checklist
below is still outstanding. Eight things this plan does not describe were added
during the build and are listed under "Added after approval" below, because the
plan as approved would have shipped a wrong day on the calendar, a button that
could wedge, a popup reminder on every block, and a throttled export reported
to the user as a hard failure.
Coverage, the verification runs and eighteen deviations from this plan's wording:
[`docs/spec_coverage_2026-11-08_plan_calendar_export.md`](spec_coverage_2026-11-08_plan_calendar_export.md).
Handoff note: [`docs/changes/2026-11-08-plan-calendar-export.md`](changes/2026-11-08-plan-calendar-export.md).
Where this document and the coverage document disagree, the coverage document
is what was built.
Source: user requirement, 2026-11-08 ("Add ability to export Plan to Google
Calendar"), plus two scope answers given the same day (below).

---

## Added after approval

Each of these came out of a cold review pass, not out of the plan. They are
criteria the plan should have had; the detail, the tests and the reasoning are
in the coverage document's "Pass 3" and "Pass 4" tables and deviations 11-18.

| Spec ID | Description | Test |
|---|---|---|
| CE-M1.1b | `time_blocks.calendar_event_calendar_id TEXT`, its own guarded migration entry: an event id is meaningless except against the calendar it was created on, and that calendar is a user setting | `tests/test_time_block_schema.py::test_cem11b_migration_adds_the_event_calendar_idempotently`, `::test_cem11c_a_fresh_database_declares_the_event_calendar_on_its_own` |
| CE-M1.3b | `set_block_calendar_event_id` writes the calendar with the id, never apart from it, and returns whether a row was written | `tests/test_time_block_crud.py::test_cem12b_the_event_calendar_round_trips`, `::test_cem12c_clearing_the_id_clears_the_calendar_with_it`, `tests/test_calendar_export.py::test_cem13a_recording_an_id_for_a_block_that_is_gone_says_so` |
| CE-M2.3b | Every exported start time is derived from the block's **box** under the bounds the screen is drawing (`times_for_slot`), and "on the grid" is `build_day_grid(...).outside` — not the stored clock columns, and not `slot_index is None` | `tests/test_calendar_export.py::test_cem216_a_block_the_day_draws_outside_the_grid_is_not_exported`, `::test_cem216a_a_block_under_the_lunch_hour_is_not_exported`, `tests/test_plan_screen_calendar_export.py::test_cem441c_the_exported_time_is_the_box_the_screen_draws` |
| CE-M2.5b | A change to `plan_export_calendar_id` moves each existing event: deleted from the old calendar, created on the configured one, counted as `moved`; a failed delete leaves the block exactly as it was | `tests/test_calendar_export.py::test_cem255_changing_the_export_calendar_moves_the_event`, `::test_cem255a`, `::test_cem255b`, `::test_cem255c`, `::test_cem255d` |
| CE-M2.6b | The sweep checks **both** halves of the marker: an event whose marker names another day is never deleted, and an event whose `extendedProperties` is not the shape Google documents is read without raising | `tests/test_calendar_export.py::test_cem266_an_event_marked_for_another_day_is_never_deleted`, `::test_cem266a_an_event_with_our_marker_and_no_date_is_still_swept`, `::test_cem266b_an_event_whose_properties_are_not_a_dict_is_ignored` |
| CE-M3.4b | A retried `insert` cannot make a second event (the body carries an event id of our own; a 409 reads that event back), and a 403 carrying a rate-limit reason is retried while a 403 that is a real refusal is not | `tests/test_google_calendar_export_calls.py::test_cem348_a_lost_insert_response_does_not_make_a_second_event`, `::test_cem348a_the_insert_carries_one_id_across_its_retries`, `::test_cem348b_two_creates_do_not_share_an_id`, `::test_cem349_a_403_rate_limit_is_retried_then_succeeds`, `::test_cem349a_a_403_that_is_a_real_refusal_is_not_retried`, `::test_cem349b_an_unreadable_error_body_leaves_the_status_to_decide`, and the payload itself: `::test_cem347_the_insert_body_carries_the_wall_clock_times_and_a_real_zone`, `::test_cem347a_the_update_body_carries_them_too` |
| CE-M3.5 | `create_event` takes its `reminders` from the caller: the meeting dialog keeps its ten-minute popup, the Plan export asks for the user's own calendar setting instead of overriding it once per block | `tests/test_google_calendar_export_calls.py::test_cem35_the_caller_decides_the_reminders`, `tests/test_calendar_export.py::test_cem35_an_exported_block_inherits_the_user_s_own_reminders` |
| CE-M4.4b | The export's client is non-interactive (`allow_interactive=False` → `AuthenticationRequired`), and one export per `(database, day)` runs at a time, keyed outside the screen instance | `tests/test_google_calendar_export_calls.py::test_cem346_a_non_interactive_client_refuses_instead_of_prompting`, `::test_cem346a_an_interactive_client_still_signs_in`, `tests/test_plan_screen_calendar_export.py::test_cem444a`, `::test_cem444b`, `::test_cem444c`, `::test_cem444d` |

---

## What is actually there now — checked before planning

| Piece | State today |
|---|---|
| `google_calendar.py` | `GoogleCalendarManager` already has `create_event`, `update_event`, `delete_event`. All three **hard-code `calendarId='primary'`** (P4). None has a timeout, retry or backoff (P5, E1, E5). `__init__` ends in `_authenticate()`, so merely constructing it does OAuth or raises `FileNotFoundError`. |
| `screens/calendar_dialog.py` | Exports **one** action item, from the Item Editor, as a one-off event. Writes an `ItemLink`, sets `is_meeting`, opens a browser. Not reusable for a day: it is a modal with hand-typed time and duration. |
| `calendar_importer.py` | The other direction only (Calendar → items). Paginates correctly (E6) and dedupes on an `ItemLink` label marker. Good template for the list call this plan needs. |
| `screens/plan.py` (2335 lines) | The day of `TimeBlock`s. Header already carries AutoLoad (the screen's only primary button), Clear Day, + Buffer, + Break, Day Settings. Nothing exports. |
| `screens/plan_blocks.py:454` | `_block_title(block, item)` — the one function that decides what a block is *called* on screen. Private, and in a module that imports CustomTkinter. |
| `time_block_layout.py` | GUI-free day arithmetic. `times_for_slot`, `DayBounds`. The right neighbourhood for anything that must be provable headless. |
| `time_blocks` table | `id, item_id, block_date, start_time, end_time, planned_minutes, label, block_type, slot_index, position, created_at, updated_at`. **No calendar event id.** |

So: the event-writing primitives exist, the day exists, and there is no path
between them, no way to name a day's worth of events, and nowhere to record
what was exported.

## Decisions taken (answered by the user, 2026-11-08)

- **"Plan" means the Plan screen's selected day** — that date's time blocks,
  exported as timed events. Not the week, not the VSP side.
- **A second export of the same day updates in place.** Each block records the
  Google event id it owns; a moved or resized block updates its event, and a
  block that is gone has its event removed. Exporting twice never duplicates.

## Decisions proposed, not assumed silently — say if any is wrong

- **D1. Buffer and Break blocks are exported too**, titled from `label` and
  falling back to "Buffer"/"Break". A calendar holding only the item blocks
  tells everyone who can see it that you are free during padding you
  deliberately planned. Alternative, if you want it: items only.
- **D2. Lunch is not exported.** The lunch chip is drawn from `DayBounds`
  (settings), not from a `time_blocks` row, so it has nothing to hold an event
  id. Excluding it is stated in the status line rather than left for you to
  notice. Making lunch exportable needs a home for its id and is a separate
  batch.
- **D3. The target calendar is a setting**, `plan_export_calendar_id`,
  defaulting to `"primary"`, threaded through as a `calendar_id` argument on
  all four Google calls. The hard-coded `'primary'` in three existing methods
  is P4 and is in scope here because the export needs the seam anyway.
- **D4. Our events are marked in the calendar itself**, via
  `extendedProperties.private` = `{gmd_block_id, gmd_block_date}`. This is what
  makes the orphan sweep possible without a tombstone table: the day's events
  carrying our marker are listed, and any whose block no longer exists is
  deleted. Events **without** our marker are never touched. The id column on
  the block stays as the fast path for the update; the marker is the record of
  record.
- **D5. Exporting is manual, per day.** No background sync, no on-save hook. A
  one-way push the user asks for.

---

## M1 — Data layer (no UI, no network; all provable headless)

### CE-M1.1 — Schema: a block records the event it owns

`time_blocks` gains `calendar_event_id TEXT` (NULLable, no default: NULL means
"never exported", which is a real state distinct from any id), ALTER guarded
per column in `database.py::_run_migrations` in the house style.

- Test: `tests/test_time_block_schema.py::test_cem11_migration_adds_calendar_event_id_idempotently` — runs the migration twice against a `tmp_path` DB, asserts the column exists once and the second run raises nothing.

### CE-M1.2 — Model and row mapping

`models.TimeBlock` gains `calendar_event_id: Optional[str] = None`.
`db_manager._row_to_time_block` reads it **defensively** (the `depth`/`work_block`
pattern): a row read before the migration must not raise.
`create_time_block` / `update_time_block` carry it.

- Test: `tests/test_time_block_crud.py::test_cem12_calendar_event_id_round_trips`
- Test: `tests/test_time_block_crud.py::test_cem12_a_row_without_the_column_still_reads` (dirty-state, P8)

### CE-M1.3 — One narrow writer

`db_manager.set_block_calendar_event_id(block_id, event_id)` writes that column
and `updated_at` only — not `slot_index`, not `position`. An exporter that
wrote whole blocks back would move the day it was exporting (P39).

- Test: `tests/test_time_block_crud.py::test_cem13_recording_an_event_id_leaves_the_block_where_it_was`

---

## M2 — The exporter (new module, GUI-free, network-free under test)

New `src/getmoredone/calendar_exporter.py`, with the same "imports no GUI
toolkit, and must not" rule as `time_block_layout.py`. Split in two so the
decisions are testable apart from the I/O:

### CE-M2.1 — `build_export_plan(blocks, items_by_id, block_date, bounds)` is pure

Returns an `ExportPlan`: one entry per exportable block (summary, start
datetime, minutes, `create` or `update`), plus **counted, named skips** —
`skipped_unplaced` (a block with `slot_index is None` is not on the grid and has
no honest time), `skipped_no_minutes`. Nothing is dropped silently; the counts
are reported as "N of M" (P2, P9).

- Test: `test_calendar_export.py::test_cem211_an_unplaced_block_is_skipped_and_counted`
- Test: `::test_cem212_every_placed_block_gets_one_entry`
- Test: `::test_cem213_a_block_with_an_event_id_plans_an_update_not_a_create`

### CE-M2.2 — The event is called what the screen calls it

`_block_title` moves to `time_block_layout.block_title(block, item)` (GUI-free);
`plan_blocks._block_title` becomes a one-line delegation so the screen and the
exporter cannot drift (P19, and P25's "two surfaces, one of them unchecked").

- Test: `::test_cem221_the_exporter_and_the_screen_name_a_block_identically` — asserts against `plan_blocks._block_title` for item, buffer, break, and the orphaned-item case.

### CE-M2.3 — Clock times, in the user's timezone

Start datetime = `block_date` + `start_time`; duration = `planned_minutes`. Naive
local datetime plus the IANA zone name the manager already resolves
(`_get_local_timezone`) — never a UTC assumption.

- Test: `::test_cem231_a_0930_block_exports_at_0930_local`

### CE-M2.4 — `export_day(...)` takes an injected client

Duck-typed client with `create_event`, `update_event`, `delete_event`,
`list_day_events`. Default is `GoogleCalendarManager`, but every test passes a
fake, so **no test in this batch reaches the network**. Returns
`{blocks_seen, created, updated, deleted_orphans, skipped_unplaced, skipped_no_minutes, failed}`.

- Test: `::test_cem241_export_day_never_constructs_the_real_manager` (asserts the seam)

### CE-M2.5 — Idempotent

Exporting an unchanged day twice issues updates and **zero** creates; the fake
client's call log is the assertion.

- Test: `::test_cem251_a_second_export_updates_and_creates_nothing`
- Test: `::test_cem252_a_moved_block_updates_its_own_event`

### CE-M2.6 — Orphan sweep, and nothing else (write this test first — P10)

An event on that date carrying our marker whose `gmd_block_id` no longer exists
is deleted. An event **without** our marker — the user's real meetings — is
never passed to `delete_event`, whatever its title or time.

- Test: `::test_cem261_an_event_for_a_deleted_block_is_removed`
- Test: `::test_cem262_an_unmarked_event_is_never_deleted` (adversarial, P7: a fake event whose summary matches a block title exactly and which carries no marker)

### CE-M2.7 — One block's failure is one block's failure

A `RuntimeError`/`HttpError` on block 3 does not abort 4-6. `failed` is counted
and reported; the run's status is **not** success (rule 3, P24). A create that
raises records **no** event id, and an id is only ever written from the id in
the response (P42 — never from the fact that the call was made).

- Test: `::test_cem271_a_failed_block_does_not_stop_the_rest`
- Test: `::test_cem272_a_failed_create_leaves_the_block_unexported`

### CE-M2.8 — An empty day is not a success

Zero exportable blocks creates nothing and reports "nothing to export".
**Built differently, on purpose:** a day with no blocks still runs the orphan
sweep, so a cleared day's events are removed and reported ("No blocks planned
… — 2 removed"). See Deviation 8 in
`docs/spec_coverage_2026-11-08_plan_calendar_export.md`.

- Test: `::test_cem281_an_empty_day_reports_nothing_to_export`

---

## M3 — Google layer, hardened as a class (P5, E1, E5, E6)

All four call sites changed in one commit, not just the new one.

### CE-M3.1 — `calendar_id` parameter, default `'primary'`
- Test: `test_google_calendar_export_calls.py::test_cem311_the_calendar_id_reaches_every_call` (fake `service`; create/update/delete)

### CE-M3.2 — `list_day_events(date, calendar_id, marker)`
`privateExtendedProperty` + `singleEvents=True`, **paginated** (E6), same loop
shape as the importer.
- Test: `::test_cem321_two_pages_are_both_returned`
- Test: `::test_cem322_only_our_marker_is_requested`

### CE-M3.3 — The marker is written and preserved
`extendedProperties.private` set on create; `update_event` must not drop it.
- Test: `::test_cem331_create_writes_the_block_marker`
- Test: `::test_cem332_update_preserves_the_marker`

### CE-M3.4 — Retry transient, never permanent; timeouts everywhere
Retry with backoff on 429/5xx; **no** retry on 4xx (E5, and P1 — a 503 is not a
permanent "no"). Timeout set on the HTTP transport the discovery client builds.
- Test: `::test_cem341_a_503_is_retried_then_succeeds`
- Test: `::test_cem342_a_404_is_not_retried`
- Test: `::test_cem343_every_event_call_goes_through_the_retry_helper` (AST walk over `google_calendar.py`, exact count, no `> N` floor)

---

## M4 — UI: one button on the Plan screen

### CE-M4.1 — The button
`⤴ Google Calendar` in the Plan header, **secondary** style: AutoLoad is this
screen's one primary action and the theme rule allows only one. Disabled
*immediately on click*, before the request leaves, re-enabled from the Tk thread
when the worker finishes (global rule on buttons that launch background work).
- Test: `test_plan_screen_calendar_export.py::test_cem411_the_button_disables_before_the_work_starts`
- Test: `::test_cem412_the_button_is_re_enabled_when_the_worker_finishes`

### CE-M4.2 — Background thread, honest status
Daemon thread, the `run_calendar_import_now` shape. Status via
`set_status` with the real counts and the named skips; failure sets `"error"`,
never `"success"` (P15 — the worker has a top-level guard; P24 — the status is
derived from the stats, not from reaching the end of the function).
- Test: `::test_cem421_the_status_line_reports_the_real_counts`
- Test: `::test_cem422_a_failing_export_sets_an_error_status`

### CE-M4.3 — Prerequisites refused clearly, before any work
Libraries missing → one message; credentials missing → the existing
`missing_credentials_message()`. Each is a refusal, not a crash and not a
silent no-op. **A third refusal was added as built:** credentials present but
no `token.pickle` — the real client authenticates in ``__init__`` and the
consent flow blocks on a browser, which a worker thread cannot show
(Deviation 10). **"No blocks" is not in this list as built:** refusing before
the export ran made the CE-M2.6 orphan sweep unreachable for the day that
needs it most, so the export always runs and reports an empty day itself
(Deviation 8).
- Test: `::test_cem431_missing_credentials_refuses_with_the_setup_message`
- Test: `::test_cem432_missing_libraries_refuses`

### CE-M4.4 — Reachable from the screen the user actually uses (P21, P25)
The button exists in the header subtree, its `command` is the screen's export
entry point, and the exporter is called with **`self.selected_date`**, not
today.
- Test: `::test_cem441_the_header_holds_the_export_button_wired_to_the_export`
- Test: `::test_cem442_the_exported_date_is_the_selected_date`

### CE-M4.5 — No UI test touches the network
The client factory is an attribute on the screen (default
`GoogleCalendarManager`); every test replaces it.
- Test: `::test_cem451_the_screen_uses_its_injected_client_factory`

These tests read `cget`/state and call the command directly, so **none** takes
the `mapped_windows` fixture and the documented mapped-window count does not
move.

---

## M5 — Documentation (same change, not a follow-up)

- `docs/google-calendar-setup.md` — an Export section: what is exported, what is not (lunch, unplaced blocks), what a second export does, which calendar.
- `docs/USER_GUIDE.md` — the Plan screen's new button.
- `CHANGELOG.md`, `NOTES.md`.
- `docs/DOCUMENTATION_INDEX.md` — this plan and the spec-coverage file.
- `docs/spec_coverage_2026-11-08_plan_calendar_export.md` — generated at the end, criterion → file/test.
- `docs/changes/2026-11-08-plan-calendar-export.md` — handoff note from `.agents/templates/handoff-note.md`.
- `CLAUDE.md` — the documented test counts (the app-only run currently says 1691) are asserted by `tests/test_ci_contract.py`; they move with this batch and are updated in it.
- `requirements.txt` / `requirements-dev.txt` — **no change**; every Google dependency is already there. Stated so the docs-sync gate's dependency rule is answered rather than guessed at.

---

## Order of work, with dependencies

1. **M1** (schema → model → writer). Nothing else can be written first.
2. **M2**, starting with CE-M2.6's two tests (highest-stakes fix first, P10: the sweep is the only part that can delete something the user did not plan), then CE-M2.1-2.5, 2.7, 2.8.
3. **M3** — needs M2's required client surface to be settled.
4. **M4** — needs M2's `export_day` signature.
5. **M5**, then the cold review pass the project's sweep budget requires.

Test commits stay separate from `src/` commits.

---

## Criteria that cannot be made code-testable — flagged, with a proposal

- **The real OAuth round trip and Google's acceptance of the event bodies.**
  Every test here uses a fake client; a fake cannot prove Google accepts
  `extendedProperties.private` or that the retry helper handles a real 429.
  This is integration-only and will be reported as **untested**, not implied by
  the fakes.
- **Proposed human check** (a checklist for you to run in the app, no
  automation driving your machine):
  1. Plan a day with two item blocks, one Buffer and one Break. Export. Confirm four events at the planned times in Google Calendar.
  2. Move one block two boxes later, shorten another to 15 minutes. Export again. Confirm **four** events still, two of them moved/resized — no duplicates.
  3. Delete a block. Export again. Confirm its event is gone and the others are untouched.
  4. Put a real meeting on that day in Google Calendar by hand. Export again. Confirm the hand-made meeting is still there.
  5. Export a day with no blocks that never had an export. Confirm the status says nothing was exported and no event appears.
  5a. Export a day, delete every block on it, export again. Confirm the status says "No blocks planned … — N removed" and that all of that day's events are gone from the calendar.
  6. Rename the token file so credentials are missing. Export. Confirm the setup message, and that the button comes back enabled.

---

## Adjacent issues found, not fixed (global rule 10)

Filed as **CE-A1 to CE-A4** in `BACKLOG.md`, in the order below.

- `update_event` ignores `location` and `attendees`; a later edit through it would silently drop them. Not touched by this batch.
- `calendar_dialog.create_event` opens a browser tab on success and sets `is_meeting=True` on the item. Unchanged, and deliberately not reused for the day export.
- `google_calendar._say` prints status to stdout from a GUI app. Related to the known failure where a `print` inside a credential `try` discarded a valid token on a failed stdout write. Flagged only.
- `GoogleCalendarManager.__init__` authenticates, so the class cannot be constructed to ask a cheap question. The export works around it with the injected factory rather than reshaping the constructor.
