# Handoff Note

- Date: 2026-11-05
- Agent: Code
- Topic: time-block rebuild (Plan screen)

## Summary

The Plan screen's time blocking was rebuilt against
`docs/implementation_plan_2026-11-05_time_blocks.md` (TB-M1…M12), covering the
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

- Command: `taskpolicy -b ./venv/bin/python -m pytest tests/test_time_block_schema.py tests/test_time_block_layout.py tests/test_time_block_crud.py tests/test_plan_screen.py tests/test_plan_settings.py tests/test_time_block_colors.py -q`
- Result: PASS — 190 passed.

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
- The four low-severity items this batch deferred are in `BACKLOG.md` under
  *Deferred from the time-block rebuild*.

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

- Review sweeps on this batch: at most 2 warm passes, at least 1 cold pass, and
  every finding severity-rated before any fix is written.
- Then the human check in the running app, per the gap above.
