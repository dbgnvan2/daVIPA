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
  Start* back slides the whole day earlier. `db_manager.shift_all_slots` is the
  renumber that fixes it, and the one renumber in the app — a Day Settings
  change still writes no rows (TG-M6.4). It was first written scoped to one
  date, which the cold sweep found: *Day Start* is a single setting, so there
  is no such thing as renumbering one day.

### PD-S — six corrections from the built screen

Asked for against a screenshot of the finished batch, so each is a defect in
what PD-M1 … PD-M6 shipped rather than a new feature.

1. **An item row is the boxes the day will give it, at every box height.** It
   was meant to be since PB-M6, but the row had a second line for the `already
   blocked` words and the floor that line imposed was 66px — two boxes' worth
   at any box height anyone sets. Every row was drawn at that floor, so a
   half-hour item looked the size of an hour. The tests stayed green through
   it: they asserted the floor, which was correct, and never that a 60-minute
   row is taller than a 30-minute one.
2. **Those words are a `>` glyph**, in a column of its own left of the depth
   bars. Not the green check, which already means *finished* on a day box.
3. **Every block ends 8px short of its right edge**, both panes, from one
   constant counted into the length's own column so PD-M2's width floor
   accounts for it.
4. **The `NNm` length is the size of the title beside it** — it was 11pt
   against 13.
5. **A box holding only break or buffer is drawn on lunch's surface.** PD-M4
   matched the three stripes and left the box fills apart; the boxes are the
   comparison a user makes. An empty box is left as room.
6. **"Lunch" is body text at body size.** At muted text on the lunch surface it
   was within a few values of its own background — (239, 234, 252) on
   (240, 231, 255), measured off the screenshot.

Both renderers now configure their columns through `configure_chip_columns`, so
a column added to the shared table reaches both panes or neither.

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
- `src/getmoredone/db_manager.py` — `shift_all_slots`
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
- Result: PASS — 2050 passed, 23 skipped. The 21 mapped-window tests are among
  the skips: that variable holds them back locally, and CI runs them.
  (Running the whole suite locally was itself a mistake — it is CI's job, and
  the machine is someone's. The per-file runs below are the ones to repeat.)
- Command: the per-module mutation gates (`mutate_pdm1.py` … `mutate_pdm6.py`,
  `mutate_pd2.py` in the session scratchpad) — every mutation reverts a line a
  test names, confirms red, and restores the verbatim original.
- Result: PASS — PD-M2 12/12, PD-M3 11/11, PD-M5 22/22, PD-S 15/15, and the
  rest. PD-S's fifteenth found a dead line rather than a test gap: with one
  text row and a floor equal to that row's height,
  `grid_rowconfigure(1, weight=1)` could no longer change anything, so it was
  removed instead of being left as a line no test can fail on.
- Command: `tests/test_ci_contract.py`
- Result: PASS (81 passed, 1 skipped) — it was red on `843a97b`, which shipped
  the stale mapped-window count; `4eeae1b` fixes it.
- Command (the sweep's fixes):
  `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py
  tests/test_time_block_crud.py tests/test_ci_contract.py -q`
- Result: PASS — 264 passed, 17 skipped: sixteen are `test_plan_screen.py`'s
  mapped-window tests and the seventeenth is `test_ci_contract.py`'s own
  CI-only skip, which is not part of that set.
- Command: `mutate_fixes.py` in the session scratchpad — nine mutations across
  the four fixes, each reverting a line a test names, plus a tenth run on its
  own for `test_pdm56_a_failure_with_no_message_still_names_itself`.
- Result: PASS — 10/10 red. One anchor was wrong on the first run and is
  recorded as an anchor failure rather than a green, which is the distinction
  that makes the gate worth running.
- Command (the second round's fixes, `2b65574` / `f122967`):
  `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py
  tests/test_ci_contract.py -q`
- Result: PASS — 235 passed, 18 skipped (one more mapped-window test than
  before). An earlier run of the same two files was 2 failed / 233 passed:
  `test_pdm21_dragging_the_grip_changes_the_items_column` and
  `test_pdm26_the_grip_and_the_settings_field_are_one_value` both set
  `plan_items_col_width` on a screen already built and leaned on the press
  re-reading it, which the press no longer does. Both now set the width before
  building the screen, which is the app's own order.
- Command: `mutate_round2.py` in the session scratchpad — five mutations, plus
  one run on its own for the `<Configure>` bind.
- Result: PASS — 6/6 red. One selector was wrong on the first run and came back
  as a green: `test_pdm56...` names `extend_day_for`'s failure arm, not
  AutoLoad's, so it could not have failed for a mutation in AutoLoad. Recorded
  rather than accepted, and re-run against the test that does name that arm.
- Not run: the rest of the suite, on this machine, by instruction. CI runs it
  on push.

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

## Sweep

Three passes over `6976b49...HEAD` (18 commits, 4892 diff lines, 20 files),
all cold — given the range and the diff and none of the narrative:

- **`learning-qa`** — `APPLICABLE: P1, P2, P4, P5, P6, P8, P9, P13, P32, P39,
  P40, P41`. Four findings, one high. P6 and P41 were checked explicitly on
  both new write paths and were clean.
- **Correctness (`/code-review`)** — eleven findings, one high, and it
  independently reached the same high finding as `learning-qa`. It also
  answered five questions put to it about the batch: the renumber's arithmetic
  across the lunch gap, `extend_day_for`'s failure paths, whether AutoLoad can
  place a multi-box task on a partly-clear run, the marker column's consumers,
  and `slot_is_padding`. All five came back clean; the defect in the renumber
  is its scope, not its arithmetic.
- **Security (`/security-review`)** — no findings. One new SQL statement
  (`shift_all_slots`): literal text, bound parameters, the repo's own idiom. No
  paths, subprocesses, deserialisation or `eval` in the range.

Fixed in `aead482` / `436264f`: the high finding (the renumber's scope) and
three mediums (AutoLoad's counts, AutoLoad's silent failure, the window
squeezing the day pane past its floor), plus three low corrections that cost a
line each — an empty failure message, a comment naming the wrong method, and a
comment calling `>` a chevron.

Recorded rather than fixed, with the reason on each, in `BACKLOG.md` under
*Deferred from the plan day-controls cold sweep (2026-11-06)*: the two live
`AppSettings` objects (medium-high — the fix is one owner for the settings
file, which is an app-wide change to every save and not a thing for a fix pass
at the end of a batch), and five lows.

**The fix commits were themselves swept**, cold, over `5fce498...HEAD`: one
high, three mediums and five lows. The high was a bug in one of the first
round's own fixes — AutoLoad's new broad-exception arm wrote
`{problem or type(problem).__name__}`, and an exception instance is always
truthy, so a message-less `KeyError()` still ended the sentence at the dash,
which is the defect the same pass had fixed correctly two methods away. All
four high and medium findings are fixed in `2b65574`, with tests in `f122967`.
The lows were recorded; the one worth keeping is folded into the `BACKLOG.md`
entry on the empty-day note's wrap.

That pass also found a test of the first round's that could not fail, and
`test_pdm22_a_real_configure_event_rebalances_the_panes` is gone because of
it — a synthetic `<Configure>` cannot reach an unmapped screen, so it asserted
nothing, and its `root.update()` spun for 8.5 hours of wall clock and 11 hours
of CPU in a background run before it was killed.
`test_pdm22_a_resize_alone_rebalances_the_panes` replaces it with a real
window, which takes the mapped-window count to 22.

## Risks / Known gaps

- **Not yet walked on screen.** PD-S came out of a screenshot the user took, so
  six of its facts are verified against a real render; the rest of the batch is
  not, and the colour and spacing changes PD-S makes have themselves only been
  verified by assertion.
- **Nothing pushed.** `main` is ahead of `origin/main`.
- **The window minimum is not enforced, only divided.** The resize clamp keeps
  the day pane at its floor by taking width off the items pane, but below
  `items_floor + divider + day_floor` (848px at the shipped settings, inside a
  1200px window with a 200px sidebar) there is no width left to divide and the
  day boxes clip again. The app sets no window `minsize`, and setting one is a
  change to every screen rather than to this one.
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
  colour, both virtual boxes, and a completed item's check. Two of the sweep's
  findings are best confirmed by hand rather than by reading — block something
  on one date, drop an item on *Earlier* on another, and look at the first
  date; and set the title column to 300 and look at the right edge of the day
  boxes.
- The sweep is done and its fixes are swept. What remains before this batch can
  be called verified is the on-screen walk: the app has not been run in this
  session.
