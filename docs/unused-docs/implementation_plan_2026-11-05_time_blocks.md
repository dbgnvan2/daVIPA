# Implementation plan — Time Blocks (2026-11-05)

Status: **built and on `main`.** `docs/spec_coverage.md` carries 28 `TB-M`
rows: 19 `done` and 9 superseded — eight of the nine by the time-grid design
in `implementation_plan_2026-11-05_time_grid.md` (the reorder, the day-packing,
the proportional block height), and `TB-M8.2` by `PD-M13.1`, which took the
refusal out of the drop path. Nothing here is outstanding: the nine were
replaced rather than left undone, and each row names its successor. Re-measure
with `grep -cE '^\| \*{0,2}TB-M' docs/spec_coverage.md` for the 28 and
`grep -E '^\| \*{0,2}TB-M' docs/spec_coverage.md | grep -c superseded` for the 9.
Corrected 2026-11-08 by the SST batch: this line read "awaiting approval. No
implementation code written" (`SSC-4`), and its first correction said all 28
were `done`.
Source: user requirements, 2026-11-05 ("The time block functionality doesn't
seem to work", seven numbered requirements).

---

## What is actually there now — checked before planning

The Plan screen is a stub, not a broken feature. Nothing in the requirement
list is half-built; most of it was never built.

| Requirement | State today |
|---|---|
| 1. Set a date | `plan.py:84` — a free-text `CTkEntry`. A typo is accepted silently and blocks are written under a `block_date` that is not a date. The reusable `DatePickerButton` already exists (`widgets/date_picker.py`) and is not used here. |
| 2. List action items for that date | **Not implemented.** `load_backlog` lists *all* open items by priority, capped at 50 with no "N of M" notice (P2), with no date filter at all. |
| 3. Drag an item to create a block | **Not implemented.** No drag handlers on the Plan screen. A working, proven drag exists in `drag_schedule.py:1338-1554`. |
| 4. Right-click a block to set a duration | **Not implemented.** There is no right-click handler anywhere in this codebase — `grep "Button-3\|Button-2"` across `screens/` returns nothing. |
| Add Block for Buffer / Break | **Not implemented.** No block type exists; `time_blocks` has no type column. |
| 5. Settings modal (day start, lunch, day end, 7 weekday checkboxes) | **Not implemented.** `AppSettings` has none of these fields. |
| 6. Drag blocks to rearrange | **Impossible as built.** `db_manager` has `create_time_block`, `get_time_blocks`, `delete_time_block` and **no `update_time_block`**. No block can be changed after creation, so neither resize nor reorder can persist. |
| 8. Priority colour, depth 3-bar stack, work-block length | **Not implemented.** Blocks render as a plain row of labels. `ActionItem.depth` ("Deep"/"Medium"/"Shallow") and `ActionItem.work_block` (90/60/30) exist on the model and are read by nothing on this screen. |

So the work is a rebuild of `screens/plan.py` on top of three things that are
missing underneath it: a writable `time_blocks` row, a typed block, and the
day-layout arithmetic.

## Decisions taken (answered by the user, 2026-11-05)

- **The 7 weekday checkboxes govern which weekdays accept blocks.** The Plan
  screen stays a single-day view. Dropping an item onto a day whose weekday is
  unchecked is refused, with the reason shown.
- **The item list shows items whose `start_date` equals the selected date
  exactly.** Not `<=`. An item whose start date is wrong will not appear —
  which makes the documentation note below load-bearing, not advisory.

## Decisions still needed from you — flagged, not assumed silently

- **D1. Priority colour bands.** `priority_score` is the product of four
  factors (20·20·16·16), so it runs 4 … 102 400, not 1 … 10. Proposed bands:
  `>= 2000` critical, `>= 500` high, `>= 100` medium, `> 0` low, `0` unscored
  (neutral). Thresholds go in `theme.py` as one table, not scattered (project
  theme rule + global rule 8).
- **D2. Depth → bars.** Proposed: Deep = 3 bars, Medium = 2, Shallow = 1, and
  **unset = 1** ("default depth to 1"). Say if you meant it the other way up.
- **D3. Lunch needs two values,** a start and a length. Proposed `plan_lunch_start`
  (12:00) + `plan_lunch_minutes` (60), rather than a start/end pair.
- **D4. "Settings tab … in a pop up modal"** is read as a modal containing a
  `CTkTabview` with one **Day** tab, so a second tab can be added later without
  moving the controls. Say if you wanted these on the main Settings screen too.

---

## M1 — Data layer (no UI; all of it testable without a display)

### TB-M1 — Schema: typed blocks and explicit order

`time_blocks` gains two columns, each ALTER guarded individually in
`database.py::_run_migrations` (the house style — a database half-migrated by an
interrupted run must not skip the rest forever):

- `block_type TEXT NOT NULL DEFAULT 'item'` — `item` | `buffer` | `break`
- `position INTEGER NOT NULL DEFAULT 0` — order within the day

`models.TimeBlock` gains `block_type: str = "item"` and `position: int = 0`.
`_row_to_time_block` reads both **defensively**, in the pattern already used for
`depth`/`work_block` at `db_manager.py:1980-1987`: a row selected before the
migration ran must not raise.

### TB-M2 — Complete the CRUD

- `update_time_block(block)` — the missing write. Persists start/end/minutes/
  label/type/position/`updated_at`.
- `reorder_time_blocks(block_date, ordered_ids)` — renumbers positions and
  rewrites times **in one transaction**. A half-applied reorder leaves a day
  with duplicate or overlapping times.
- `get_time_blocks` orders by `position, start_time`, so legacy rows with
  `position = 0` still come out in a stable, sensible order.
- `get_items_for_start_date(date)` — open items with `start_date = ?`
  (parameterised), ordered by `priority_score` descending.

### TB-M3 — Day layout as pure functions

New module `src/getmoredone/time_block_layout.py`. **No Tk import.** All the
arithmetic lives here so it can be proved without building a window:

- `pack_day(blocks, day_start, lunch_start, lunch_minutes, day_end)` — walks
  blocks in position order from `day_start`, assigning start/end times. A block
  that would straddle lunch is **pushed to after lunch, not split**. Returns each
  block with computed times plus an `overflows_day_end` flag.
- `duration_for_item(item, default_minutes)` → `item.work_block or default_minutes`
  (requirement 8: work block value when present; default 30 comes from the
  existing `AppSettings.default_time_block_minutes`).
- `depth_bars(depth)` → 3 / 2 / 1, and **1 for `None` or an unrecognised value**.
- `is_block_day(date_str, enabled_weekdays)`.
- `priority_band(score)` → band name (D1).

A block past `day_end` is **flagged, never dropped or refused** (P2 — surface,
don't silently discard).

## M2 — Settings

### TB-M4 — `AppSettings` fields

`plan_day_start = "08:00"`, `plan_lunch_start = "12:00"`,
`plan_lunch_minutes = 60`, `plan_day_end = "17:00"`,
`plan_block_weekdays = [True]*5 + [False, False]` (Mon…Sun).

Each gets a `_normalize_*` classmethod in the existing style: a hand-edited or
corrupt settings file falls back to the default instead of stopping the app from
starting, and the weekday list is coerced to exactly seven booleans.

### TB-M5 — `PlanSettingsDialog`

Modal (`CTkToplevel`, `transient` + `grab_set`, matching `AddTimeBlockDialog`),
containing a `CTkTabview` with a **Day** tab: day start, lunch start, lunch
minutes, day end, seven weekday checkboxes, Save / Cancel. Invalid times are
rejected in the dialog with a reason, not swallowed. Saving re-packs the day.

## M3 — The screen

### TB-M6 — Date selection
Replace the free-text entry with `DatePickerButton`, `on_date_changed` reloading
both panes. This removes the silent bad-date write.

### TB-M7 — Items for the date
Left pane lists `get_items_for_start_date(selected_date)`. Each row carries the
priority band as a **stripe/chip accent only** — never a full-row fill (project
theme rule) — the depth 3-bar stack, the work-block minutes when set, and a
marker when that item already has a block on that day. If the list is capped,
the cap announces what it dropped ("showing 50 of 63") — the current silent 50
disappears with the function.

### TB-M8 — Drag an item right to create a block
Reuse the drag mechanics proven in `drag_schedule.py` (pointer-root hit testing,
floating drag label, hover border). The hit-test helper is **factored into a
shared module rather than copied a third time** (global rule 5: fix the class).

Drop on the day column → create a block at the end of the day with
`planned_minutes = item.work_block or 30`, times from `pack_day`. A drop on an
unchecked weekday is refused with the reason shown.

### TB-M9 — Right-click a block to set a duration
First right-click surface in this codebase. Bind **both** `<Button-3>` and
`<Button-2>` (macOS delivers right-click as Button-2 on some configurations) to
a `tkinter.Menu`: 15 / 30 / 45 / 60 / 90, Custom…, Delete. **30 is the default
offered.** A duration change re-packs the day and persists every block it moved.

### TB-M10 — Add Buffer / Add Break
Two header buttons creating typed blocks at the end of the day: buffer 30 min,
break from the existing `AppSettings.default_break_minutes` (5). Neutral colour,
no priority band, no depth bars.

### TB-M11 — Drag blocks to rearrange
Drag within the day column; the insertion index comes from pointer-y against the
rendered block frames; `reorder_time_blocks` renumbers and re-packs in one
transaction.

### TB-M12 — Block appearance
Band colour as accent + tint (not a fill), depth 3-bar stack, and **height
proportional to `planned_minutes`** so a 90 reads as three times a 30. Blocks
past day end carry a warning marker.

---

## Acceptance criteria → tests

Every `DatabaseManager` in these tests takes an explicit `tmp_path` database
(project rule — the default path is the user's real application database).

| ID | Criterion | Test |
|---|---|---|
| TB-M1.1 | Migration adds `block_type`/`position` to a legacy `time_blocks` table and is idempotent on a second run | `tests/test_time_block_schema.py::test_tbm11_migration_adds_columns_and_is_idempotent` |
| TB-M1.2 | A `TimeBlock` round-trips type and position through create → read | `::test_tbm12_block_type_and_position_round_trip` |
| TB-M1.3 | **Dirty state (P8)** — a row written before the migration reads back with `block_type='item'`, `position=0`, and does not raise | `::test_tbm13_pre_migration_row_reads_with_defaults` |
| TB-M2.1 | `update_time_block` persists a changed duration — the row, re-read, holds the new value | `tests/test_time_block_crud.py::test_tbm21_update_persists_duration` |
| TB-M2.2 | `reorder_time_blocks` leaves no two blocks on a day sharing a start time, and no gaps | `test_tbm22_reorder_yields_unique_contiguous_times` — gone with `reorder_time_blocks` itself; `tests/test_time_block_crud.py`'s own docstring records that "the reorder and repack tests that used to be most of this file are gone". Named without a path, like TB-M3.1 below. Added 2026-11-09 by the sixth cold pass, which found this row and the next still citing dead names in the bare `::name` form the traceability guard cannot see — the row below was repaired an hour earlier only because its name carried a path |
| TB-M2.3 | A reorder that fails partway writes **nothing** | `test_tbm23_failed_reorder_is_atomic` — gone with the same mechanism. The surviving assertion of the same property over the move path is `tests/test_time_block_crud.py::test_tgm62_a_failed_move_writes_nothing` |
| TB-M2.4 | `get_items_for_start_date` returns the item starting that day and **not** one starting the day before or after | `::test_tbm24_start_date_filter_is_exact` |
| TB-M3.1 | `pack_day` packs from day start with no gaps | `test_tbm31_blocks_pack_from_day_start` — gone with `pack_day` itself, which `tests/test_time_block_layout.py` records as retired in favour of `times_for_slot`. Named without its path because there is nothing left to follow. |
| TB-M3.2 | **Adversarial (P7)** — a block that fits *up to* lunch start but not through it is pushed whole to after lunch, not split and not overlapped onto lunch | `test_tbm32_block_straddling_lunch_moves_after_lunch` — gone with `pack_day`. The surviving assertion of the same property, under the grid design that replaced packing, is `tests/test_time_grid.py::test_tgm22_a_span_cannot_cross_lunch` |
| TB-M3.3 | **Real scale (P9)** — a day of 14 × 60 min blocks: those past day end are returned and flagged, never dropped | `test_tbm33_overflow_blocks_are_flagged_not_dropped` — gone with `pack_day`; what holds now is `tests/test_time_grid.py::test_tgm31_a_block_with_no_box_is_surfaced` (P2, one block rather than a day of fourteen, so the real-scale half of this criterion is not covered) |
| TB-M3.4 | `duration_for_item` returns `work_block` when set, 30 when not | `::test_tbm34_work_block_wins_over_default` |
| TB-M3.5 | `depth_bars` → 3/2/1, and 1 for `None` and for an unrecognised string | `::test_tbm35_depth_bars_default_to_one` |
| TB-M3.6 | `is_block_day` is False for an unchecked weekday, True for a checked one | `::test_tbm36_unchecked_weekday_is_not_a_block_day` |
| TB-M4.1 | A settings file with a garbage `plan_day_start` loads with the default rather than raising | `tests/test_plan_settings.py::test_tbm41_bad_time_falls_back_to_default` |
| TB-M4.2 | A `plan_block_weekdays` of the wrong length is coerced to seven booleans | `::test_tbm42_weekday_list_is_coerced_to_seven` |
| TB-M4.3 | Saved day settings survive a save/load cycle | `::test_tbm43_day_settings_round_trip` |
| TB-M5.1 | The modal exposes all four time fields and seven checkboxes, and Save writes them to `AppSettings` | `tests/test_plan_screen.py::test_tbm51_settings_modal_writes_day_settings` |
| TB-M6.1 | Changing the date picker reloads the item list and the block list for the new date | `::test_tbm61_date_change_reloads_both_panes` |
| TB-M7.1 | The left pane shows exactly the items whose start date is the selected date | `::test_tbm71_item_list_matches_selected_date` |
| TB-M8.1 | A drop on the day column creates one block in the database, with the item's work block as its length | `::test_tbm81_drop_creates_block_using_work_block` |
| TB-M8.2 | A drop on an unchecked weekday creates **no** block and reports why | *superseded 2026-11-07 — PD-M7 softened the refusal to a question and PD-M13.1 removed the question from the drop path; the test is deleted and the replacement is* `::test_pdm131_a_drop_on_a_non_work_day_asks_nothing_and_writes` |
| TB-M9.1 | Both `<Button-3>` and `<Button-2>` are bound on a block widget | `::test_tbm91_both_right_click_buttons_are_bound` |
| TB-M9.2 | Choosing 60 from the menu updates that block's row to 60 and re-times the blocks after it | `test_tbm92_duration_change_repacks_the_day` — gone with the repack. A duration change now resizes in place: `tests/test_time_block_crud.py::test_tgm112_a_resize_that_does_not_fit_is_refused` and `::test_a_resize_that_fits_rewrites_the_end_time` |
| TB-M10.1 | Add Buffer and Add Break each create a typed block of the right length | `::test_tbm101_buffer_and_break_blocks_are_typed` |
| TB-M11.1 | Dragging block 3 above block 1 leaves the database in that order, by position and by time | `test_tbm111_reorder_persists_new_order` — gone with `reorder_time_blocks`, as TB-M2.2 and TB-M2.3 above. A drag now moves a block between boxes: `tests/test_time_block_crud.py::test_a_move_rewrites_the_times_with_the_slot`, `::test_tgm62_a_failed_move_writes_nothing` and `::test_a_drop_onto_its_own_box_moves_a_task_to_the_end_of_it`. `::test_a_block_goes_where_it_was_dropped_not_at_the_end_of_the_day` was cited here first and is a creation, not a move — its helper calls `add_block_at` |
| TB-M12.1 | Block height is proportional to minutes — a 90 is three times a 30 | `test_tbm121_block_height_tracks_minutes` — no test of that name exists. Proportional height was replaced by the box model, where a row is as tall as the boxes it spans: `tests/test_plan_screen.py::test_pbm61_an_item_row_is_the_height_the_day_would_give_it` |
| TB-M12.2 | Every band colour clears the contrast minimum against the block background in **both** light and dark themes (via the existing `color_contrast.py`) | `tests/test_time_block_colors.py::test_tbm122_band_colors_meet_contrast_in_both_themes` |
| TB-M12.3 | No hard-coded hex outside the `theme.py` band table — parsed from the AST, asserted as an **exact count of zero** | `::test_tbm123_no_inline_hex_in_plan_screen` |

Each test is proved by mutation: delete or invert the line it names, run it,
confirm red, restore the **verbatim** original.

### Not code-testable — flagged, with a human-review proposal

- **That the drag feels right** — hit-test tolerance, hover feedback, whether a
  45-pixel block is grabbable. Human check in the running app under the venv,
  plus `app.log`. No test substitutes.
- **That macOS actually delivers the right-click** to one of the two bound
  buttons. The bindings are asserted; the OS delivering the event is a
  human check.
- Both will be done in the real app, not a standalone Tk script.

---

## Order, and why

1. **TB-M1 → M2 → M3.** Schema, the missing `update_time_block`, then the
   arithmetic. All headless. Nothing above can be built on a row that cannot be
   written.
2. **TB-M4, M5.** Settings, because the layout function needs real day bounds.
3. **TB-M6, M7.** Date picker and the date-filtered item list.
4. **TB-M8, M9, M10.** Create by drag, set duration, buffer/break.
5. **TB-M11, M12.** Rearrange, then appearance last — it is the only part with
   no behavioural consequence.
6. **Docs**, in the same change (docs sync gate).

## Adjacent issues found, not fixed (global rule 10)

Found while reading. Listed, not swept up silently:

- `AddTimeBlockDialog.save` catches bare `Exception` and prints it into a UI
  label, and **never sets `item_id`** — so every manually created block is
  permanently unassigned. This dialog is replaced by TB-M9/M10, so it is fixed
  as part of the work rather than left.
- `load_backlog` caps at 50 with no notice (P2). Replaced by TB-M7.
- `delete_time_block` has no confirmation, while other destructive paths in
  this app do ask. **Not in scope** → `BACKLOG.md`.
- `BACKLOG.md`'s "Calendar view for time blocks" (`grep -n "Calendar view for
  time blocks" BACKLOG.md`) overlaps requirement 6 but
  is a wider feature. **Not in scope.**

## Documentation to update, in the same change

- `docs/USER_GUIDE.md` — the Plan section (lines 258-275) describes the stub and
  will be wrong in every particular. Rewritten, and it opens with the
  prerequisite: **get the start dates right before you time block.** With the
  exact-date filter, an item whose start date is wrong simply will not appear in
  the list for the day you are planning — the planner cannot tell you about work
  it cannot see.
- `README.md` — the Plan/time-blocks feature lines and the `time_blocks` schema
  note (lines 18, 146, 473, 520).
- `CHANGELOG.md`, `BACKLOG.md` (tick what this closes, add what it defers).
- `docs/DOCUMENTATION_INDEX.md` — the index does not currently list
  implementation plans and no test enforces that it should, so this plan is
  not added to it. Any **new user-facing** doc this work produces is.
- `docs/unused-docs/changes/2026-11-05-time-blocks.md` — handoff note from
  `.agents/templates/handoff-note.md`.
- `docs/spec_coverage.md` — regenerated for the TB-* IDs.

## Review

Per `CLAUDE.md`: at most 2 warm passes, **at least 1 cold pass always**, every
finding severity-rated before any fix, below-medium findings to `BACKLOG.md`.
The data layer (TB-M1/M2) touches a migration that runs at every app start on
the real database, so it gets its dirty-state test and a
no-op-on-clean-database assertion before anything is built on top of it.
