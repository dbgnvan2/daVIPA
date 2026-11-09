# Handoff Note

- Date: 2026-11-05
- Agent: Code
- Topic: time-block rebuild (Plan screen)

## Summary

The Plan screen's time blocking was rebuilt against
`docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md` (TB-M1…M12), covering the
eight requirements as given.

The organising decision: **a planned day is an order, not a set of
appointments.** `position` is stored and is the source of truth; `start_time`
and `end_time` are *derived* from (order + each block's length + the day
bounds). That is what makes reorder, resize and a settings change all reduce to
one operation — repack the day — instead of three ways to get the clock wrong.

What this replaced: a 313-line stub with a free-text date field that silently
wrote unusable dates, an unfiltered item list, and no `update_time_block` on
`DatabaseManager` at all — so requirements 4 (set a block's length) and 6
(reorder blocks) were not slow or awkward, they were physically impossible.

Against the requirements as numbered by the user:

1. Set a date — `DatePickerButton`, replacing the free-text entry.
2. List action items for that date — `get_items_for_start_date`, start date
   **exactly** equal to the selected date (settled with the user).
3. Drag an item right to create a block — real `<ButtonPress-1>` /
   `<ButtonRelease-1>` on the row; the block is appended and the day re-timed.
4. Right-click a block for its length — 15/30/45/60/90, custom, delete.
   Default 30 minutes, or the item's Work Block value when it has one.
   `+ Break` and `+ Buffer` append typed padding blocks.
5. Day Settings modal — `CTkTabview` with a Day tab: day start, lunch start,
   lunch minutes, day end, seven weekday checkboxes.
6. Drag blocks to rearrange — reorder writes new positions and re-times the
   whole day in one transaction.
8. Priority colours, depth as a three-bar stack, Work Block as length, depth
   defaulting to 1.

The seven weekday checkboxes govern **which weekdays accept blocks** (settled
with the user). Plan stays a single-day view; a drop onto an unchecked day is
refused with the reason.

## Files changed

New:

- `src/getmoredone/time_block_layout.py` — all the day arithmetic, Tk-free on
  purpose: packing, lunch, overflow, durations, depth bars, priority bands,
  the weekday gate, block heights. 95 of the new tests need no display.
- `src/getmoredone/screens/plan_blocks.py` — the item row and block row
  widgets, and the depth bar stack.
- `src/getmoredone/screens/plan_settings_dialog.py` — the Day Settings modal.
- `tests/test_time_block_schema.py`, `tests/test_time_block_layout.py`,
  `tests/test_time_block_crud.py`, `tests/test_plan_screen.py`,
  `tests/test_plan_settings.py`, `tests/test_time_block_colors.py`.

Modified:

- `src/getmoredone/database.py` — `block_type` and `position` on
  `time_blocks`, added by a guarded idempotent migration. The
  `idx_blocks_date_position` index is created **only** in the migration, never
  in `initialize_schema`: index creation runs before `_run_migrations`, so
  indexing `position` there failed schema init on every existing database.
- `src/getmoredone/models.py` — the two new `TimeBlock` fields and `BlockType`.
- `src/getmoredone/db_manager.py` — `update_time_block` (which did not exist),
  `repack_day`, `reorder_time_blocks`, `get_items_for_start_date`,
  `get_blocked_item_ids`, `_next_block_position`.
- `src/getmoredone/app_settings.py` — the four day values and the seven
  weekday flags, normalised on both load and save.
- `src/getmoredone/theme.py` — `priority_band_colors`, `block_type_colors`,
  `depth_bar_colors`.
- `src/getmoredone/screens/plan.py` — rewritten.
- `src/getmoredone/screens/drag_schedule.py` /
  `drag_schedule_support.py` — the drag hit-test, duplicated four times by
  hand, factored into one shared `widget_contains_pointer`.
- `docs/USER_GUIDE.md`, `README.md`, `CHANGELOG.md`, `BACKLOG.md`,
  `CLAUDE.md`.

## Verification

- Command: `taskpolicy -b ./venv/bin/python -m pytest tests/test_time_block_schema.py tests/test_time_block_layout.py tests/test_time_block_crud.py tests/test_plan_screen.py tests/test_plan_settings.py tests/test_time_block_colors.py tests/test_drag_schedule_support.py -q`
- Result: PASS — 263 passed (257 of them new in this batch). Re-measured
  after the re-sweep fixes below; it was 247 before them.

- Command: the same seven files plus `tests/test_settings_isolation.py
  tests/test_theme_settings.py tests/test_today_screen.py tests/test_timer.py
  tests/test_future_dates.py tests/test_db_project_drag.py
  tests/test_depth_work_block.py`, with `GETMOREDONE_NO_MAPPED_WINDOWS=1`
- Result: PASS — 333 passed, 5 skipped (the mapped-window tests, which pass
  when the variable is unset). Run after the sweep fixes, because the length
  ceiling and the strict time parser are shared code and the adjacent screens
  read both.

- Command: `taskpolicy -b ./venv/bin/python -m pytest tests/test_tk_offscreen.py tests/test_ci_contract.py -q`
- Result: PASS — 111 passed, 1 skipped (the CI-only display check).

- Command: `./venv/bin/python run.py --selftest`
- Result: PASS — 4/4 checks, including the database check against the real
  application database. Verified afterwards with `sqlite3` that the real
  `time_blocks` table now carries `block_type TEXT NOT NULL DEFAULT 'item'`,
  `position INTEGER NOT NULL DEFAULT 0`, and `idx_blocks_date_position` (P6:
  checked against the artifact, not against a migration that claimed to run).

Each new test was mutation-proved: the line it names was deleted or inverted,
the test confirmed red, and the **verbatim** original restored. Three of these
found something:

- Reverting the light-theme `critical` band to `#B91C1C` turned the contrast
  test red at 4.15 against the block surface, which is how that colour got
  changed to `#991B1B` (5.33). The earlier measurement had used the lighter
  page background rather than the surface the stripe is actually drawn on.
- Removing `<ButtonRelease-1>` from the item rows, `<ButtonPress-1>` from the
  blocks, and the right-click loop each turned red exactly the one test that
  names that binding.

## Review sweeps

Three passes, per the budget in `CLAUDE.md`: two with different lenses over the
whole range, and `/security-review` because the diff adds SQL.

- `/code-review` (correctness, reuse, simplification): 5 findings — 1 high, 2
  medium, 2 low.
- `learning-qa` (the failure-pattern catalogue): 12 findings — 2 high, 1
  medium-high, 3 medium, 6 below medium. Its own scope note is worth keeping:
  it covers failures that hide, in I/O, migration, state and derived-value
  paths, and did **not** assess Tk event-loop or geometry correctness,
  UI-contract regressions on the 48 untouched screens, accessibility beyond the
  one contrast change, security, performance or dependency risk.
- `/security-review`: run on the committed range plus the working tree.

Everything at medium or above was fixed in the same session with a test, each
proved by mutation — ten mutations, ten reds, every original restored verbatim.
The fixes were then re-swept as their own range, because a fix commit is the
least-reviewed code in any change. That fourth pass returned **0 high, 4
medium, 4 low**; the three mediums still open at the time were fixed with
tests and seven more mutations, and because the pass produced no high-severity
finding the budget in `CLAUDE.md` ends the sweep there rather than running a
fifth.

What the two high findings were:

1. **The block length ceiling guarded one of two ways in.** The dialog refused
   anything over a day; an item's Work Block value, which the item editor
   accepts as any typed integer, went straight through — so the row's stored
   end time was not its start plus its length, which is exactly what the
   constant's own comment forbids. The ceiling now lives in the arithmetic
   layer beside the constant, and both callers go through it.
2. **A test in the batch was red, and the test was wrong, not the code.** It
   asserted stored clock times on a row that nothing in the test had ever
   repacked — an expectation that encoded the inverse of the design.

And the three at medium or medium-high:

3. **Each screen write and its repack were two commits.** Between them a new
   block had no times, and a resize read as a 30-minute block claiming 90 while
   the next block still owned the minutes. Invisible because `load_blocks`
   re-derives, which is also why no test saw it.
4. **The Day Settings dialog accepted an hour past 23.** `25:00` as a Day End
   put the end of the day past every block the planner can make, retiring the
   overrun warning permanently; `170:0` was stored as `99:59`. `parse_hhmm`
   accepts those on purpose, because `format_hhmm` writes them for an
   overrunning block's end time — so the dialog needed a strict reader, not a
   change to the lenient one.
5. **A settings change re-timed only the day on screen.** Every other planned
   day was left holding times derived from bounds that no longer existed.

Two findings were about the tests rather than the code and were corrected as
such: the expectation above, and an atomicity test that passed against a
version with no transaction at all, because its fixture raised before anything
had been written. A third was a false `Tests:` line — `widget_contains_pointer`
named a test that existed nowhere, so the one function this batch extracted
specifically to be shared between two drag surfaces had no direct coverage
while its docstring claimed otherwise.

### What the re-sweep of the fix commits found

Three mediums, each fixed here with a test:

6. **A day end stored past midnight was still read as given.** Finding 4 above
   was fixed in the dialog, which heals new input and leaves a settings file
   written by an earlier version wrong forever: loaded unbounded, a Day End of
   `25:00` puts the end of the day past every block the planner can make and
   keeps the overrun warning switched off permanently, with nothing anywhere to
   say so. `parse_clock_time` is the bounded reader and all three day-bound
   fields now load through it. `parse_hhmm` stays lenient on purpose —
   `sort_blocks` parses a stored overflow start time like `25:30` back.
7. **A day too full to express was written clamped rather than refused.** The
   ceiling from finding 1 bounds one block; this is a property of the day. Four
   blocks of exactly a day each are each legal and together pack past
   `MAX_FORMATTED_MINUTES`, where `format_hhmm` clamps — so the fourth row
   would have been stored claiming 1440 minutes between `85:00` and `99:59`,
   which is 899. `repack_day` now raises `DayTooFullError` before it opens its
   transaction, so nothing is written, and all four screen writes plus the
   settings save report it.
8. **The atomicity fixture from finding 2's correction was itself fragile.** It
   raised on the second *read* of `day_start_minutes`, which is the second day
   only while `pack_day` reads that property exactly once per call. It does —
   probed, not assumed — but a refactor that read it twice would move the
   failure onto day one, before any write, and the test would go green while
   testing nothing: the exact vacuity the correction existed to escape. It now
   counts the per-day repacks, and a second test asserts the first day really
   is written before the second fails.

One mutation of the seven came back green on the first attempt, and the reason
is worth keeping: the mutant was invalid code that raised `NameError`, and
`AppSettings.load()` wraps the whole load in `except Exception` and falls back
to a defaults object, so the error was swallowed and the assertion was
satisfied for the wrong reason. Re-run with a mutant that compiles, it went
red. The broad `except` is pre-existing and is recorded in `BACKLOG.md` as an
adjacent issue: it means any programming error in a normaliser silently
discards the user's entire settings file for that launch.

## Risks / Known gaps

- **Not seen on screen.** `/Applications/daVIPA.app` was running throughout, and
  it holds the single-instance `flock`, so a source launch would have exited
  silently with code 0. Everything above is real widgets under pytest, real Tk
  events, and the headless startup check — none of it is how the screen *looks*
  at full size, or whether macOS delivers a right-click as `<Button-3>` or
  `<Button-2>` on this machine. Both are bound; which one arrives is a human
  check. Run `./start-demo.sh` (beside the installed app, its own data dir) or
  quit the packaged app and `./start.sh`.
- **The demo instance is a thin test bed as seeded.** All six sample items in
  `demo_data.py` have an empty start date and the item list filters on start
  date exactly, so the left pane is empty on a fresh demo. In `BACKLOG.md`.
- Seventeen below-medium items are in `BACKLOG.md` under *Deferred from the
  time-block rebuild* — four deferred during the build, eight from the review
  passes, four from the re-sweep of the fix commits, and one adjacent issue
  found while proving those fixes, each with the pass that found it and the
  reason it was not fixed in-loop. One is worth naming here because it is a crash rather than a
  rough edge: deleting an action item that holds a time block raises
  `IntegrityError`, because `time_blocks.item_id` references `action_items(id)`
  with no `ON DELETE` clause. Pre-existing, but this batch makes creating a
  block a single drag, so it becomes reachable in ordinary use. The fix is a
  schema decision, not a line, which is why it is recorded rather than taken
  in a fix pass at the end of a session.

### One bug worth naming

Dropping an item, or reordering a block, could hang the app. `on_drag_release`
called `block_item` / `reorder_to`, both of which end in `refresh()`, which
destroys the row widget whose `<ButtonRelease-1>` handler was still being
dispatched — tearing down the widget that is dispatching the event hangs Tk.
The work is now deferred with `after_idle` so the handler returns first.

Every test that called the handlers directly passed, before and after. It was
found only by generating real button events at the real row widgets, which is
the lesson this repo had already written down once: *calling a screen's handlers
is not the same as exercising its bindings.* Four event-level tests now cover
the item drop, the refused drop, the reorder and the right-click; they ask for
the `mapped_windows` fixture, because `event_generate` plus `update()`
deadlocks on a withdrawn window.

## Next agent actions

- The human check in the running app, per the gap above. It is the only part of
  this batch nothing automated has covered: how the screen looks at full size,
  and which of the two bound right-click sequences macOS actually delivers.
- A cold sweep over this range from a session with no context, per the
  calibration cadence in the `csdp` skill. This batch needed two fix rounds,
  which is below the three-round trigger, but it is also the batch where both
  review passes found real defects in code two in-session passes had already
  read — so a cold pass here would measure something.
- The schema decision behind the `ON DELETE` crash above.
