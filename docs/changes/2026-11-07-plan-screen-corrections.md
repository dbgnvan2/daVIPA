# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: plan-screen-corrections

## Summary

Four things reported from the running Plan screen, plus one defect in the test
suite found while proving the first.

**1. "AutoLoad doesn't work" and "Drag and Drop doesn't move item" were one
guard, not two defects, and not a regression.** The screen opens on today, today
was a Saturday, Saturday and Sunday are off in `DEFAULT_BLOCK_WEEKDAYS`, and
`_require_block_day` returned False at all four write paths — `autoload_day`,
`block_item`, `add_padding_block` and `extend_day_for`. Every one of them
returned before doing anything, leaving a status line as the only sign. The
settings file holds no `plan_*` keys at all, so every Plan setting was at its
default.

Fixed as PD-M7: the guard asks instead of refusing. *"<date> is not a regular
work day. Day Settings allows Mon, Tue, Wed, Thu, Fri. Schedule anyway?"* Yes
plans that date, No writes nothing and leaves the refusal's own sentence. The
Yes is held in `self._work_anyway` on the screen — one decision per date, not
per drop, and not a change to the working week, which is what Day Settings is
for.

**2. The divider is 15px of grip (PD-M2.8).** It was a 6px grip with a 2px pad
on each side: a 10px gap of which the pointer had to hit the middle 6.
`PLAN_DIVIDER_WIDTH_PX` is 15, the pane pads next to it are 0, and
`PLAN_PANE_EDGE_PAD_PX` names the 10px that stays at the window's edges.

**3. The clamp was short by the chrome (PD-M2.9).** Found while doing 2.
`_clamp_items_width` measured both pane floors against the whole window width,
though the grip and the two edge pads are 26px of it and none of it is pane. The
day pane has nothing holding it open, so all of that came off the day — the
clipping the floors exist to prevent — and the wider grip would have made it
35px. `PLAN_PANE_CHROME_PX` now comes off the window before the floors are
measured.

**4. The depth bars sit on the text's line (PD-M1.6).** The stack is shorter
than a line of text and was gridded `sticky="n"`, so it floated above the title
on every row in the items pane. It is `sticky="s"` now, and `DepthBarStack`'s
gap goes between its bars rather than under the last one, so the lowest bar ends
level with the title rather than 2px clear of it. The day-pane chips were not
touched: everything in a chip is centred, so the bars already line up there.

**5. The `messageboxes` fixture was reporting other tests' dialogs.** It yielded
the session-wide record and trimmed only `[before:]` on teardown, so a test that
did not request the fixture left its dialogs in the list for every later test.
Measured: `test_pdm7_a_work_day_asks_nothing` failed on a dialog raised two tests
earlier and passed when run on its own — deterministic, not order-random. The
record is emptied on the way in as well as on the way out.

## Files changed

- `src/getmoredone/screens/plan.py` — `_require_block_day` asks;
  `_work_anyway`; `PLAN_DIVIDER_WIDTH_PX` 6 → 15; `PLAN_PANE_EDGE_PAD_PX` and
  `PLAN_PANE_CHROME_PX`; the pane pads; `_clamp_items_width`
- `src/getmoredone/screens/plan_blocks.py` — `build_item_row` bar stack
  `sticky="s"`; `DepthBarStack` gap between bars only
- `tests/test_plan_screen.py` — 7 new tests; 4 existing tests moved their
  patched window width up by `PLAN_PANE_CHROME_PX`
- `tests/test_tk_offscreen.py` — `test_b51d_the_record_starts_empty_for_each_test`
- `conftest.py` — the `messageboxes` fixture clears on entry
- `CHANGELOG.md`, `docs/USER_GUIDE.md` (Days for Blocks),
  `docs/implementation_plan_2026-11-06_plan_day_controls.md` (PD-M1.6, PD-M2.8,
  PD-M2.9, PD-M7, and its stale "awaiting approval" status),
  `docs/spec_coverage.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py
  tests/test_plan_settings.py tests/test_time_block_colors.py
  tests/test_ci_contract.py tests/test_tk_offscreen.py -q`
- Result: PASS — 332 passed, 21 skipped (the skips are the on-screen geometry
  tests the local workflow disables)
- Command: `pytest tests/test_plan_screen.py -k
  "pdm22_the_day_pane_cannot_be_dragged_shut or pdm22_a_resize_alone"` with
  the env var unset, because both are on-screen tests whose arithmetic this
  batch changed
- Result: PASS — 2 passed
- Mutation gate: 8 mutations, 8 red. One was green on the first run — the
  depth-bar test measured the bottom of the stack *frame*, which bottom-aligns
  whatever is inside it, so it could not see the trailing gap it claimed to
  prove. Rewritten to measure the lowest bar, then red.

## Risks / Known gaps

- **Not run in the app.** The four corrections are all visual or gestural, and
  no test puts a pointer on the real grip or looks at the real alignment. The
  window on screen is what settles items 2 and 4.
- **The four tests whose patched width moved** are case (b): the behaviour
  changed intentionally. Their assertions are unchanged; only the window width
  they patch grew by the chrome, so "both floors plus 40px of slack" still means
  that.
- **Adjacent issues found, not fixed:**
  - `SLOT_BARS_WIDTH_PX` is 22 while the stack is a 14px block of bars gridded
    `padx=(4, 6)`, which needs 24. Both width floors are 2px short. Already in
    `BACKLOG.md`.
  - `logger.exception("AutoLoad failed")` reaches stderr only — the app
    configures no logging and writes no log file, so a failure on a packaged
    launch is recorded nowhere. Not in scope here; worth a decision.
  - The `NNm` length label on an item row is gridded `sticky="ne"` like the
    bars were. It makes no visible difference, because the label is as tall as
    the row's text and fills its cell either way.

## Next agent actions

- Run the app on a Saturday and on a weekday: drag an item onto today, answer
  Yes, confirm the block lands and the second drag asks nothing; answer No on a
  fresh screen and confirm nothing is written.
- Look at the grip: 15px, draggable anywhere in the gap, and the panes still
  meet their floors in a narrow window.
- Look at an item row with Deep depth: the lowest bar level with the bottom of
  the title.
