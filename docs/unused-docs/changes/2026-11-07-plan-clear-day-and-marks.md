# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: plan-clear-day-and-marks

## Summary

Three things reported from the running Plan screen, in the same sitting as the
four in `2026-11-07-plan-screen-corrections.md`. The third one supersedes item 4
of that note.

**1. A "Clear Day" button, the reverse of AutoLoad (PD-M8).** AutoLoad fills the
day in one click; undoing it meant a right-click and a Delete block per block.
`clear_day` removes every item block on the selected date in one transaction.

Three decisions worth recording:

- **Item blocks only.** Breaks and buffers are not AutoLoad's work — AutoLoad
  has never written one, so each was put there by hand, and a button that is the
  reverse of AutoLoad should not take them. A button called "Clear Day" that
  leaves blocks behind is a surprise, so the confirmation says how many are
  staying and the status line says it again afterwards.
- **It asks first.** The app has no undo, and the count is in the question.
- **It does not call `_require_block_day`.** Taking work off a day is not
  planning work onto it, so clearing a Saturday asks nothing about the weekday
  list. A test pins that, because the guard is one line away in the same file
  and the obvious "consistency" fix would be wrong.

A day with no item blocks sets a warning status and raises no dialog.

**2. An item row says whether it is scheduled (PD-M9).** The marker column used
to hold `>` for an item the day already holds a block for and nothing at all
otherwise, so an unscheduled item and a row with no marker read the same. Now
every row carries one: `✓` in green when the day holds a block for it, `?` in
red when it does not.

The two colours are new semantic tokens, `scheduled_mark` and `unscheduled_mark`.
They exist because no token already in `theme.py` is legible on the fills these
marks sit on. The row's background is `fill_for_item`, which reads
`priority_fill_colors()` — pale tints in the light theme and deep in the dark
one. `success_strong`'s dark green measures **1.63:1** against the dark `low`
fill: a mark nobody could see. The shipped pair is #166534/#4ADE80 (scheduled)
and #B91C1C/#FCA5A5 (unscheduled), and a test holds every combination of theme
and priority fill at the 4.5:1 text bar — worst measured 5.30:1 light, 7.85:1
dark.

`✓` now has two readings in the app: "this item is complete" on a day-pane chip
(`PD_CHECK_TEXT`) and "this item is scheduled" on an items-pane row. The two
panes keep them apart and the constant's comment records it, but it is a
collision on purpose rather than by oversight.

**3. The depth bars are justified like the text beside them (PD-M1.6).** The
previous note shipped them bottom-flush, which was what "should be BOTTOM to
line up with text" asked for. The follow-up was "justify vertically like TEXT on
the line", so the stack now takes the title's own justification — no `sticky` at
all, which in Tk centres it — and keeps the earlier change that removed the
trailing gap, so there is no slack inside the stack to put the bars a pixel out.
The test asserts all three: no `n`/`s` in the sticky, zero slack above and below
the bars inside their frame, and the bars' midpoint within 1px of the title's
(Tk centres by integer division, so 1px is the floor).

## Files changed

- `src/getmoredone/screens/plan.py` — `btn_clear_day` in the header, packed
  right after AutoLoad so the row reads [status] [Clear Day] [AutoLoad];
  `clear_day()`
- `src/getmoredone/screens/plan_blocks.py` — `PD_BLOCKED_TEXT` `>` → `✓`;
  new `PD_UNSCHEDULED_TEXT`; the marker is drawn on every item row, coloured by
  which of the two it is; the bar stack's `sticky` dropped
- `src/getmoredone/theme.py` — `scheduled_mark`, `unscheduled_mark`
- `tests/test_plan_screen.py` — 6 new `test_pdm8_*`, 1 new `test_pdm9_*`;
  `test_pdm16_*` renamed and rewritten for the new justification; `_row_columns`
  accepts either mark
- `tests/test_time_block_colors.py` —
  `test_pdm9_the_two_marks_are_legible_on_every_fill`
- `CHANGELOG.md`, `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md`
  (PD-M8 and PD-M9 sections, the PD-M1.6 row rewritten, title and status line),
  `docs/spec_coverage.md` (11 new rows, PD-M1.6 rewritten)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py -q`
- Result: PASS — 167 passed, 17 skipped (the skips are the on-screen geometry
  tests the local workflow disables)
- Command: the same over `tests/test_plan_screen.py
  tests/test_time_block_colors.py tests/test_plan_settings.py
  tests/test_ci_contract.py`
- Result: PASS — 311 passed, 18 skipped in 129s
- Mutation gate: 9 mutations, 9 red. Each reverts one shipped line to its
  verbatim original and requires the test that names it red.
- **A measurement I got wrong first.** I first held the two marks against
  `priority_band_colors()` and concluded that only near-white or near-black
  marks could pass. `fill_for_item` uses `priority_fill_colors()`, which is a
  different table — pale in light mode, deep in dark. The shipped colours and
  the test are against the table the code actually reads.

## Risks / Known gaps

- **Not run in the app.** All three items are visual or gestural: the two marks,
  the bar alignment, and the Clear Day dialog's wording and button order. No
  test looks at the real screen.
- **Two existing tests changed, both case (b) — the behaviour changed
  intentionally.** `test_pdm14_*`'s last assertion now expects
  `PD_UNSCHEDULED_TEXT` where it expected no mark, and
  `test_pdm11_the_item_row_uses_the_chips_column_order` includes `"marker"` in
  the row's column set while excluding it from the chip comparison.
- **Adjacent issues found, not fixed** (all three carried over from the previous
  note, none touched here):
  - `SLOT_BARS_WIDTH_PX` is 22 where the stack needs 24, so both width floors
    are 2px short. Already in `BACKLOG.md`.
  - The app configures no logging, so `clear_day`'s `logger.exception` reaches
    stderr only — on a packaged launch, nowhere.
  - The item row's `NNm` label is still `sticky="ne"`. No visible difference,
    because the label is as tall as the row's text.

## Next agent actions

- Run the app and look at an items row of each kind: a scheduled item green and
  checked, an unscheduled one red and questioned, both legible on every priority
  fill and in both themes.
- Press Clear Day on a day with items and a break: read the question, answer No
  and confirm nothing moved, answer Yes and confirm the break stayed.
- Press Clear Day on an empty day: a warning line, no dialog.
- Look at a Deep item row: the bars centred on the title's line.
