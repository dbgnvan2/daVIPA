# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: plan-calendar-export

## Summary

The Plan screen can export the day you are looking at to Google Calendar, and
can do it again without duplicating anything. CE-M1 to CE-M5 of
`docs/implementation_plan_2026-11-08_plan_calendar_export.md`, approved the
same day.

- **`src/getmoredone/calendar_exporter.py`** (new, 601 lines, imports no GUI
  toolkit): `build_export_plan` decides what the day's blocks should become and
  sends nothing; `export_day` sends it. Blocks the day draws outside the grid,
  blocks with no length, and a day whose date cannot be read are **skipped and
  counted** by name, never guessed at. Every event's time is derived from the
  block's box with `times_for_slot`, against the `DayBounds` the screen is
  drawing — never read from the stored clock columns.
- **Idempotency has two halves.** `time_blocks.calendar_event_id` (new column,
  idempotent migration) is how a re-export finds the event to update; the
  block's id written into the event's own `extendedProperties.private` is how
  a re-export finds events whose block is **gone**, with no tombstone table
  and from any machine the user plans on. An event without that marker is
  never updated or deleted, whatever its title or time.
- **`google_calendar.py` hardened as a class** (P5), not just where the new
  code touches it: a 30s transport timeout, `_with_retry` around all four
  event calls, 429/5xx retried with exponential backoff, 404/410 raised as
  `CalendarEventMissing` so an event the user deleted by hand is re-created
  rather than reported as a failure, and `calendar_id` as a parameter where
  three call sites hard-coded `'primary'` (P4).
- **One button**, secondary style (AutoLoad is this screen's only primary),
  disabled before anything fallible runs and re-enabled by every exit path.
  The worker thread touches no widget: it leaves its result in an attribute
  and the Tk thread collects it.

**A cold review pass has been run** (`learning-qa`, read-only, no
implementation context) and returned eleven findings: 1 high, 3 medium, 7 low.
The high and all three mediums are fixed here:

- **The empty-day refusal is gone (high).** It made the orphan sweep
  unreachable in the one case it exists for — a day whose blocks have all been
  deleted — so those events could not be taken off the calendar by any code
  path, under a status line saying there was nothing to export. The export now
  always runs and the exporter reports the empty day itself.
- **`summary_line` no longer discards a run's deletions and failures** when the
  day has no blocks left.
- **`_with_retry` retries transport failures**, not `HttpError` only: the
  transient class the batch's own 30s timeout creates was reaching the caller
  unretried (P1, P5). Named exception types, not `OSError`, so a disk error is
  not retried as a network blip.
- **The reporters check the screen still exists and `destroy` cancels the
  poll** (P15): navigating away mid-export raised inside a Tk callback.

The seven low findings are filed as CE-A5 to CE-A11 in `BACKLOG.md`.

**A second cold pass** then ran in a different failure family — UI contract and
test quality — because the budget requires one after a high-severity finding.
Seven more: 1 high, 4 medium, 2 low, with the high and all four mediums fixed:

- **The header did not fit the window (high).** Measured: 1203px of requested
  width inside a 1200px window, every widget in it packed at a fixed width and
  the status label packed last with no `expand`. Tk gave the label nothing, and
  a label squeezed to zero is never mapped — the export's only way of
  reporting anything, invisible at the window's own default size. The status
  line now has its own grid row and the button is 150px instead of 160px.
- **`has_credentials()` is not "connected".** It only checks
  `credentials.json`; the real client authenticates in `__init__`, on the
  worker thread, blocking on a browser consent with no timeout. A
  never-connected user who closed the consent tab was left disabled under
  "Exporting…" with nothing to clear it. Third refusal added, on
  `check_token_validity()["exists"]`.
- **The `try` did not cover the thread start.** Six statements, `.start()`
  among them, ran outside it with the button already disabled.
- **A tautological assertion and an uncovered branch** in the title tests, both
  replaced by assertions that can fail — one of them against the text Tk
  actually draws on a block.
- **`test_cem423`'s own assertion could not fail**, which is exactly what the
  first pass's fix was supposed to be proved by.

It also re-rated CE-A5 from low: the poller's read-then-`is_alive` ordering
reports a successful export as a worker that vanished, so that is fixed too.
CE-A12 to CE-A15 hold what is left. Ten deviations from the plan's wording,
both passes' finding tables, and one claim of the second pass that is wrong
(and why) are in `docs/spec_coverage_2026-11-08_plan_calendar_export.md`.

## Files changed

New:

- `src/getmoredone/calendar_exporter.py`
- `tests/test_calendar_export.py` (44 tests)
- `tests/test_google_calendar_export_calls.py` (27 tests)
- `tests/test_plan_screen_calendar_export.py` (34 tests)
- `docs/spec_coverage_2026-11-08_plan_calendar_export.md`
- `docs/changes/2026-11-08-plan-calendar-export.md` (this note)

Modified:

- `src/getmoredone/database.py` — `calendar_event_id TEXT` and `calendar_event_calendar_id TEXT` on fresh databases and by guarded migration, one entry each
- `src/getmoredone/models.py` — `TimeBlock.calendar_event_id` and `.calendar_event_calendar_id`, appended last so positional construction is unchanged
- `src/getmoredone/db_manager.py` — `create_time_block` carries both columns, `_row_to_time_block` reads both defensively, new `set_block_calendar_event_id` (which takes the calendar, writes it only with an id, and returns whether a row was written); `update_time_block` deliberately writes neither
- `src/getmoredone/google_calendar.py` — retry/timeout/marker/pagination/`calendar_id` (above), plus `allow_interactive` and the new `AuthenticationRequired`
- `src/getmoredone/time_block_layout.py` — `block_title(block, item)`, moved here from the GUI module
- `src/getmoredone/screens/plan_blocks.py` — `_block_title` delegates to it
- `src/getmoredone/screens/plan.py` — the button, the worker, the poller, the status line (moved to its own row), `_still_on_screen`, a `destroy` override
- `src/getmoredone/app.py` — `DEFAULT_GEOMETRY` / `DEFAULT_WINDOW_WIDTH_PX`, so a header-fits test reads the window size instead of copying it (P4)
- `src/getmoredone/screens/calendar_dialog.py` — `not_connected_message()`
- `src/getmoredone/app_settings.py` — `plan_export_calendar_id`
- `tests/test_time_block_crud.py` (+7 tests), `tests/test_time_block_schema.py` (+4 tests)
- `docs/google-calendar-setup.md` — an Export section: what goes out, what is skipped and why, what a second export does, which calendar
- `docs/USER_GUIDE.md` — the Plan header's new button, and what it does when the day's hours move, when the target calendar changes, when the connection has lapsed, and when an export of that day is already running
- `CHANGELOG.md`, `NOTES.md`, `docs/DOCUMENTATION_INDEX.md`
- `BACKLOG.md` — CE-A1 to CE-A4 (found while building), CE-A5 to CE-A21 (the four cold passes' below-medium findings), and corrections to CE-A9 and CE-A11, both of which stated their finding wrongly
- `docs/implementation_plan_2026-11-08_plan_calendar_export.md` — status line

`requirements.txt` and `requirements-dev.txt` need **no** change: the Google
client libraries this uses were already dependencies.

**`src/getmoredone/db_manager.py` is already committed.** Its changes are in
`43d8a43` ("feat(wtp): the editor's parent line, the cascade, the rollup"),
which a concurrent session in this repository made with a tree-wide commit
while this work was in progress. Nothing else from this batch is committed.

## Verification

All under `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19`. The four per-file runs
below were taken before the cold pass added six tests; the combined run at the
end of the list is the current one.

- Command: `pytest tests/test_calendar_export.py tests/test_google_calendar_export_calls.py tests/test_plan_screen_calendar_export.py tests/test_first_run.py tests/test_google_calendar_paths.py -q`
- Result: PASS — 93 passed, and after the cold-pass fixes 28 / 16 / 24 passed
  in the three new files on their own

- Command: `… pytest tests/test_time_block_crud.py tests/test_time_block_schema.py tests/test_time_block_layout.py tests/test_time_block_colors.py tests/test_database.py -q`
- Result: PASS — 182 passed

- Command: `… pytest tests/test_ui_presence.py tests/test_plan_settings.py -q`
- Result: PASS — 52 passed

- Command: `… pytest tests/test_plan_screen.py -q`
- Result: PASS — 192 passed, 17 skipped

- Command: the thirteen files above plus `tests/test_traceability_refs.py`,
  `tests/test_ci_contract.py` and `tests/test_item_editor.py`, in one process,
  `-p no:randomly`
- Result: PASS — **650 passed, 18 skipped** in 183s. This run is the one that
  matters: the only defect in the batch that no single-file run could find was
  an order-dependent one (see below); `test_traceability_refs.py` holds the
  `Tests:` docstring references to real test names; `test_ci_contract.py`
  holds the mapped-window count, which this batch does not change (the new
  geometry check reads requested widths, so it needs no on-screen window); and
  `test_item_editor.py` covers the other caller of the module
  `not_connected_message` was added to.

- Command: full suite
- Result: NOT RUN (local machine rule; CI runs it)

- Command: the three CE files, and the two time-block files, after the third
  cold pass's fixes
- Result: PASS — 40 / 18 / 34, and 58 passed for
  `test_time_block_schema.py` + `test_time_block_crud.py`

- Command: the whole set again — the three CE files, the two time-block
  files, `test_plan_screen.py`, `test_plan_settings.py`,
  `test_time_block_layout.py`, `test_time_grid.py` — after the other
  session's PD-M14 edit to `screens/plan.py` landed and the tree imported
  again
- Result: **9 failed, 537 passed, 17 skipped.** All 150 of this batch's own
  tests pass (the three CE files plus the two time-block files, run alone:
  150 passed). The nine failures are all PD-M14, in the other session's
  in-progress area and in files this batch does not touch:
  `test_plan_screen.py::test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day`,
  `::test_tgm31_an_outside_block_is_drawn`,
  `::test_every_part_of_an_outside_row_starts_a_drag`,
  `::test_the_outside_group_does_not_outlive_the_day_that_had_one`,
  `::test_pbm55_the_settings_reach_the_outside_group_on_screen`,
  `::test_the_outside_group_scrolls_instead_of_growing_past_the_pane`,
  `::test_the_outside_group_takes_no_room_on_a_day_without_one`,
  `test_plan_settings.py::test_pdm54_extending_the_day_is_not_confirming_it`,
  `::test_pdm54_an_already_confirmed_day_stays_confirmed`. Not fixed from
  here; `time_block_layout.py` and the outside-group work are theirs this
  round.

- Command: the three CE files and `test_google_calendar_paths.py`, after the
  fourth cold pass's fixes
- Result: PASS — 182 passed (44 / 27 / 34 in the three CE files)

- Command: the meta suite
- Result: 2 failed, 211 passed, 1 skipped. Both failures are
  `test_traceability_refs.py`, on four references none of which this batch
  wrote: two PD-M14's, two the uncommitted priority-defaults work's. Every
  `Tests:` reference written here resolves.

Mutation proof: 104 mutations, the verbatim original line removed or inverted,
one named test run against each, restored in a `finally`. All red after the
findings below. Three came back green — the test could not fail. Two were real
defects: `update_time_block` writing `calendar_event_id` (it would orphan a
live event on a resize), and a `failed_block_ids` guard in the orphan sweep
that was dead code. The third was a vacuous test: `test_cem12c` cleared an
event id with the calendar argument defaulted, so the guard it named could not
be exercised. Forty-six of the 88 prove the three cold passes' fixes.

## Risks / Known gaps

- **The six-step manual checklist has not been run.** It is the part no test
  can cover — a real OAuth round trip, Google accepting
  `extendedProperties.private`, and the real API's rate limiter. The steps are
  in the plan document under "Criteria that cannot be made code-testable".
- **The review budget is closed.** The fourth cold pass — time correctness and
  the Google API contract — returned ten findings, four medium and six low, and
  nothing high, which is the stopping condition. The four mediums are fixed and
  mutation-proven; the lows are CE-A17 to CE-A21.
- **The fourth pass found that nothing asserted the payload leaving the
  machine.** Every time test asserted `ExportEntry.start`, a datetime the app
  computed and the app read back. `start['dateTime']`, `end['dateTime']` and
  `timeZone` were asserted nowhere: dropping the zone, sending `date` instead
  of `dateTime`, or reading minutes as hours all left the batch green. Three
  mutations now prove otherwise.
- **The retry added in CE-M3.4 could duplicate an event.** `events().insert`
  is not idempotent; a request that lands and whose response is lost was sent
  again. The export's sweep removed the loser, but the meeting dialog — which
  this batch did not otherwise touch — has no sweep, so it made two identical
  events with attendees and recorded one. Fixed by sending our own event id and
  reading back on a 409.
- **Every exported block was carrying a ten-minute popup** and overriding the
  user's own calendar reminder setting, because `create_event` hard-coded the
  meeting dialog's reminders for every caller.
- **The third cold pass found the batch's worst defect, and it had shipped
  through two earlier passes.** The export was timing every block from
  `block.start_time`, which the Plan screen's own docstring calls "a record,
  not the truth": a block's box is stored relative to Day Start, so moving Day
  Start re-times the day on screen and leaves those columns behind. A day drawn
  from 10:00 was going out from 08:00. Both earlier passes read the exporter
  and neither questioned where the time came from.
- **The export's client can no longer sign in, and four documents had said
  this case was already closed.** A token file *existing* is not a token that
  works; revoked access, a changed password or a damaged pickle all reached
  `flow.run_local_server` and then `input()` on the worker thread, both
  waiting forever. `allow_interactive=False` raises `AuthenticationRequired`
  instead. The claim in those four documents is corrected, not deleted — the
  wrong version is recorded beside the right one.
- **The status line moved on the Plan screen.** It was top-right in the header
  and is now its own row under the body. That is a visible change to a screen
  the user knows, made because the header could not hold a seventh control, and
  it affects every message this screen shows, not only the export's.
- **Nothing is committed** (except `db_manager.py`, swept in by another
  session as noted above), and the working tree holds substantial unrelated
  work from other batches. `git commit -a` would sweep it in.
- `update_event` still ignores `location` and `attendees`; a later edit through
  it would silently drop them. Flagged, not fixed (global rule 10).
- `google_calendar._say` still prints to stdout from a GUI app.

## Next agent actions

- The other session's PD-M14 edit to `screens/plan.py` has landed and the set
  has been re-run (above). Nine PD-M14 tests are red in their area; leave them
  to that session.
- No further review pass is owed: the fourth produced nothing high.
  CE-A17 to CE-A21 hold what was filed.
- Run the six-step manual checklist in the app and record the result here.
- Commit in the project's order — `src/` and `tests/` separately — taking care
  not to sweep in the unrelated working-tree changes, which now include
  another session's in-progress PD-M14 work.
