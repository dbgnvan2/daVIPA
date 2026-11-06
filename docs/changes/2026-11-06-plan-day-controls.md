# Handoff Note

- Date: 2026-11-06
- Agent: Code
- Topic: plan-day-controls (PD-M1 … PD-M6)

## Summary

The six modules of `docs/implementation_plan_2026-11-06_plan_day_controls.md`,
built in the plan's order against the screenshot the batch started from.

- **PD-M1 — an item is drawn as the task it is about to become.** A row in
  *Items starting* now uses a day box's own first line: the same four columns in
  the same order at the same widths — stripe, title, depth bars, block length —
  with the length beside the bars rather than under them, and the depth word
  gone from the second line. Both panes take the title width from *Drag Schedule
  title column width (px)*; it had been a constant on the left, so the columns
  lined up at the default and nowhere else.
- **PD-M2 — the divider drags.** The line between the panes is a grip that
  writes *Plan items column width (px)*, the same value the Settings field
  holds. Neither pane can be dragged shut: the items column stops at what one
  of its own rows needs, the day at what one day row needs. Motion writes
  nothing; release writes once.
- **PD-M3 — AutoLoad.** A header button that blocks every item the day has room
  for, one after another, at the earliest half hour with nothing in it. It only
  adds, never lengthens the day, reports all three counts every time, and the
  whole run is one transaction.
- **PD-M4 — one colour for padding.** Break, buffer and lunch resolve to a
  single token in both appearance modes. Lunch had no stripe at all before, so
  it had no colour to share.
- **PD-M5 — the day's two ends.** An *Earlier* and a *Later* box at the ends of
  the day column; dropping an item on one moves *Day Start* or *Day End* by the
  item's own length and blocks it in the half hours that appear. Midnight is
  refused rather than clamped. A block dragged there is refused.
- **PD-M6 — a green check for finished work.** A box whose task is completed
  draws a check in a column of its own, left of the time, in the theme's success
  token. A box holding one finished and one open task draws none.

Two corrections to the approved plan, both recorded in it:

- **PD-M3 said `first_free_slot`** — the earliest box that is not *full*. A box
  holds four tasks, so on an empty day that answers 08:00 four times and would
  have stacked four items there. Corrected to a new `first_clear_slot`: the
  earliest box with nothing in it, and every box a multi-box task needs clear,
  not only the first.
- **PD-M5 assumed existing blocks keep their clock times for free.** They do
  not: a block is stored by which box of the day it sits in, so moving *Day
  Start* back slides the whole day earlier. `db_manager.shift_day_slots` is the
  renumber that fixes it, and the one renumber in the app — a Day Settings
  change still writes no rows (TG-M6.4).

## Files changed

Source:

- `src/getmoredone/screens/plan.py` — the grip (`create_divider`,
  `on_divider_press/motion/release`, `items_col_width`, `items_width_floor`,
  `day_width_floor`, `_clamp_items_width`), `autoload_day`, `first_clear_slot`,
  the virtual boxes in `load_blocks`, `virtual_under_pointer`, `extend_day_for`,
  `_DayNotWritten`, and the drop routing in `on_drag_release`
- `src/getmoredone/screens/plan_blocks.py` — `chip_column_minsizes` shared by
  both panes, `build_item_row` rebuilt on it, `build_virtual_slot_row`, the
  check column (`SLOT_CHECK_WIDTH_PX`, `item_is_complete`, `slot_is_complete`)
- `src/getmoredone/time_block_layout.py` — `extended_day_bound`,
  `LAST_DAY_END_MINUTES`, `DAY_EXTEND_EARLIER` / `DAY_EXTEND_LATER`
- `src/getmoredone/db_manager.py` — `shift_day_slots`
- `src/getmoredone/theme.py` — one colour for break, buffer and lunch

Tests:

- `tests/test_plan_screen.py`, `tests/test_plan_settings.py`,
  `tests/test_time_block_crud.py`, `tests/test_time_block_layout.py`,
  `tests/test_time_block_colors.py`
- `conftest.py` and `CLAUDE.md` — the mapped-window count, 20 → 21

Docs:

- `CHANGELOG.md`, `docs/USER_GUIDE.md`, `docs/spec_coverage.md`,
  `docs/implementation_plan_2026-11-06_plan_day_controls.md`, `BACKLOG.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest -q`
- Result: see the status report in the session; the 21 mapped-window tests are
  skipped locally by that variable and run on CI.
- Command: the per-module mutation gates (`mutate_pdm1.py` … `mutate_pdm6.py`
  in the session scratchpad) — every mutation reverts a line a test names,
  confirms red, and restores the verbatim original.
- Result: PASS — PD-M2 12/12, PD-M3 11/11, PD-M5 22/22, and the rest.
- Command: `tests/test_ci_contract.py`
- Result: PASS (81 passed, 1 skipped) — it was red on `843a97b`, which shipped
  the stale mapped-window count; `4eeae1b` fixes it.

Five gate findings were defects in the tests or the code rather than in the
mutations, and each is recorded in the commit that fixed it:

- PD-M2's grip released at the same x as its last motion, so dropping the
  release's own event was invisible.
- No test sent a divider motion or release without a press.
- A release that hit neither virtual box could return an end of the day instead
  of `None`, and would have lengthened the day for a drop on the heading.
- `test_pdm5_a_real_box_wins_over_a_virtual_one` could not fail: the two guards
  were mutually exclusive by construction. The code now reads both and the
  branch order is the rule.
- `extend_day_for` snapshotted `plan_day_shape_unconfirmed` and restored it on
  the failure path — a line no path could make matter. Removed.

## Risks / Known gaps

- **Not yet walked on screen.** The P26 order is the on-screen walk *before* the
  final cold pass, and neither has run at the time of writing.
- **Nothing pushed.** `main` is ahead of `origin/main`.
- `PD-M5` is the first code in the app that renumbers `slot_index`. The guard
  against it running anywhere else is `tests/test_time_block_crud.py` plus
  TG-M6.4's assertion that a Day Settings change writes no rows.
- The drag-feel row under *Human review required* in `docs/spec_coverage.md` is
  still open from the previous batch.

## Adjacent issues found, not fixed

In `BACKLOG.md` under *Adjacent issues from the plan day-controls batch
(2026-11-06)*:

- `+ Break` / `+ Buffer` still place at `first_free_slot`, so they can land in a
  box that already holds work. Left because changing a shipped placement is a
  behaviour change, not a fix to this batch.
- A Settings screen left open holds a stale `AppSettings.load()`, and its Save
  writes the stale items-column width back over a width the drag had set.

## Next agent actions

- Walk the Plan screen in the running app: the item rows against the day's
  boxes, the grip at both floors, AutoLoad on a part-full day, the padding
  colour, both virtual boxes, and a completed item's check.
- Then the cold review pass, then `/csdp`.
