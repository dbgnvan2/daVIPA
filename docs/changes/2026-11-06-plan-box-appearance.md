# Handoff Note

- Date: 2026-11-06
- Agent: Code
- Topic: plan-box-appearance (PB-M1 to PB-M5)

## Summary

Five changes to how a task is drawn on the Plan screen, plus the defect that
made three of them look like missing features.

The defect: `ctk.CTkFrame` requests 200x200 when neither `width` nor `height`
is given. The priority stripe set only `width`, so its height request was a
constant nobody chose. In a Day Plan box the chip passed that request up and
the box clipped it to 34px, leaving the title laid out around y=100 — drawn,
below everything the box shows. On screen a planned half hour was a bare 6px
bar. The same missing `height=` made every Items-starting row ~200px tall.

- **PB-M1** — `priority_stripe_colors()`, a brighter table for the bar, held
  to the 3:1 WCAG non-text bar. `priority_band_colors()` is untouched and stays
  at 4.5:1, because PB-M4 puts a band colour behind text and that headroom is
  now load-bearing.
- **PB-M2** — the stripe asks for a height. Title, duration and bars appear.
- **PB-M3** — the three-bar depth stack, now visible, with its own test.
- **PB-M4** — `priority_fill_colors()`: a task is shaded by its band on both
  panes, title colour chosen for the shade. Padding and continuation chips are
  left unshaded.
- **PB-M5** — a task in a box is as tall as `drag_schedule_box_height_px` and
  its title column as wide as `drag_schedule_title_col_width`. Empty half hours
  keep `SLOT_MIN_HEIGHT_PX`. Unusable settings fall back.
- Also: the *no items start on this date* note was clipped at both ends
  (`CTkLabel` centres its text); it is anchored left and wraps to the column.

## Files changed

- `src/getmoredone/theme.py` — two new colour tables
- `src/getmoredone/screens/plan_blocks.py` — `STRIPE_MIN_HEIGHT_PX`,
  `SLOT_TITLE_WIDTH_PX`, `stripe_for_item`/`stripe_for_block`/`fill_for_item`,
  `slot_row_height(chips, chip_height)`, chip fill and sizing
- `src/getmoredone/screens/plan.py` — `box_height()`, `box_title_width()`,
  `_positive_setting()`, the wrapped empty-state note
- `tests/test_plan_screen.py`, `tests/test_time_block_colors.py`
- `docs/implementation_plan_2026-11-06_plan_box_appearance.md` (new),
  `docs/USER_GUIDE.md`, `docs/spec_coverage.md`, `CHANGELOG.md`,
  `docs/implementation_plan_2026-11-05_time_grid.md`

## Verification

- Command: the eight touched test files, run under the venv with mapped
  windows enabled (`GETMOREDONE_NO_MAPPED_WINDOWS` unset, so the geometry
  tests actually ran rather than skipping).
- Result: **PASS** — 280 passed.
- Command: the repo/infra assertions (`-m meta`).
- Result: **PASS** — 211 passed, 1 skipped. It caught one stale `Tests:`
  reference in `theme.py` naming a test that had been renamed.
- Mutation gate: 12 mutations, each the verbatim original reverted, each
  confirmed red, every file restored. Plus 2 more for the empty-note fix.
- On screen: `./start-demo.sh`, Plan, 2026-11-05 and 2026-11-06. All five
  asks confirmed visually. No errors in the launch log.

## Risks / Known gaps

- **Two mutations were green on the first pass, and both were defects in the
  tests, not the code.** (1) The chip had two independent guards — the
  stripe's `height=` and a `grid_propagate(False)` — so no test could fail on
  either alone. The redundant guard was removed rather than left unprovable.
  (2) `test_pbm41_fill_tints_carry_legible_text` was **vacuous**: with
  `pick_text_color` choosing black or white, at least one always clears 4.5:1
  at every luminance, so the assertion could not fail. It was replaced by a
  margin test and by a widget test on the rendered title colour.
- Two live `PlanScreen`s on one mapped root wedge Tk inside `root.update()`.
  Not a defect in the code under test, but it hangs a run; the two PB-M5
  wiring tests settle geometry with `update_idletasks()` instead.
- The demo's `drag_schedule_box_height_px` is 30, so the Plan boxes are
  compact there. The 86 default only applies to a fresh settings file.
- Item titles longer than the column are still clipped at the right edge.
  Anchored left, so the start is always readable; no ellipsis.

## Sweep (2026-11-06, after the first three commits)

Two passes over `99d438f...cfd6dc5`, both cold: a failure-pattern pass
(`learning-qa`) and a correctness pass (`/code-review`). Eight findings
between them, no high, three raised by both. `/security-review` was not run:
the range has no credential, auth, SQL, subprocess, HTTP or deserialisation
surface — the only grep hits were the word "request" in prose about
`CTkFrame` geometry.

Five mediums fixed with tests in `0d48c96` (src) and `cb8c476` (tests):

- The outside-the-day group's rows kept the 30/80 fallbacks while the day took
  the setting, in the column the group had just been moved into.
- That group also lost its scrollable container in the move, so a day with a
  dozen blocks outside it clipped the lower rows out of reach while the header
  counted them (P2). Scrollable at a fixed height, ungridded when empty.
- `_positive_setting` guaranteed "> 0", not usable: a box height of 14 made a
  two-task half hour the same height as a one-task one and clipped the second
  task. Floored at one line of text.
- The note's wraplength was unfloored and Tk reads `<= 0` as "do not wrap".
- Three docstrings and a settings comment named the wrong Settings section.

Plus three test-quality fixes: a colour test that passed only because this Mac
is in light mode, three tests holding `mapped_windows` without reading
geometry, and a duplicated WCAG luminance formula whose justification was
false. The documented mapped-window count (conftest: three, CLAUDE.md: ten;
actual: sixteen) is now asserted against the suite by AST.

Mutation gate on the fixes: 8 mutations, 8 red, every file restored. The
appearance pin was probed by forcing dark mode, where the test it protects
goes red as predicted.

Four below-medium findings went to `BACKLOG.md`, including two adjacent issues
flagged rather than fixed under rule 10.

## Adjacent issues found, not fixed

- `screens/drag_schedule.py:115` reads the same box-height setting with a bare
  `int(getattr(...))`, a different fallback (86) and a different floor (20).
  Hand-edit a `null` into settings.json and that screen does not open while
  the Plan screen falls back. One shared helper is the fix; widening this diff
  into another screen is not.
- The four Plan/Drag Schedule size controls render under "Date Increment
  Settings". The docs now say so; moving them needs approval.
- A press that lands exactly on a 14x3px depth bar does not start a drag
  (already in `BACKLOG.md`; still true, and the bars are now visible on the
  Day Plan too, so the target exists in one more place).
- `docs/spec_coverage.md`'s third human-review row ("does a drag feel right")
  is still outstanding and is now overtaken by PB-M5 — a chip is no longer
  30px by definition.

## Next agent actions

- Re-walk the drag feel on screen once a box height other than 30 is in use.

---

## PB-M6 / PB-M7 — a second round, after the first five were on screen

### Summary

Four more changes, asked for against the same demo once PB-M1 to PB-M5 were
visible.

- An item row in **Items starting** is now `slots_for_minutes(minutes)` boxes
  of `box_height()` tall — the same arithmetic and unit the day's grid uses, so
  a 90-minute item is three boxes and a 45-minute item is two. Held by
  `grid_propagate(False)`, which is what makes it the grid's height rather than
  its text's.
- The priority score came off the row. It was the third statement of one fact,
  after the fill and the stripe.
- The work-block length (`30m`) moved from the detail line to under the depth
  bars, which puts it where it already is on a task in a box.
- A continuation chip now carries the task's fill and stripe instead of being
  transparent, and keeps its `↳`. Transparent was the earlier decision, on the
  argument that shading a continuation would read as a second task; on screen a
  90-minute task read as one that stops after half an hour. Buffers and breaks
  stay transparent. The `same task` / `15m spare` line takes the text colour
  the new fill calls for.

### Files changed

- `src/getmoredone/screens/plan_blocks.py` — `build_item_row` height, span and
  detail line; the duration label; `_build_block_chip`'s merged fill branch and
  unconditional stripe; `SLOT_CHIP_HEIGHT_PX` moved above `build_item_row`
  because it is now a default argument and defaults bind at definition time.
- `src/getmoredone/screens/plan.py` — `build_item_row` called with
  `box_height=self.box_height()`.
- `tests/test_plan_screen.py` — six new tests, one rewritten.
- `docs/implementation_plan_2026-11-06_plan_box_appearance.md`,
  `docs/spec_coverage.md`, `docs/USER_GUIDE.md`, `CHANGELOG.md`.

### Verification

- Command: `pytest tests/test_plan_screen.py tests/test_time_block_colors.py tests/test_plan_settings.py -q`
- Result: PASS — 160 passed, mapped windows enabled.
- Mutation gate: 9 mutations over the four changes, 9 red, every file restored
  from a verbatim copy. The first run skipped one because
  `    frame.grid_propagate(False)` matches twice in the module; anchored to its
  preceding line and re-run.

### Risks / Known gaps

- **At a box height near the 30px floor a one-box row clips its second line.**
  The demo's settings file holds 30, so it is visible there; the 86px default
  has room. The height is pinned on purpose — a row that grew to its text would
  stop matching the grid, which is what was asked for. Stated in the plan under
  PB-M6 and in the user guide rather than treated as a defect.
- One rewritten test, under test rule (b): the behaviour changed intentionally.
  `test_an_item_row_is_as_tall_as_its_text_not_the_stripe_default` asserted the
  opposite of PB-M6.1 and is now
  `test_an_item_row_lays_out_at_the_height_it_asks_for`. PB-M2.2 is marked
  superseded in both the plan and `docs/spec_coverage.md` rather than left
  claiming a property this change removes.
- Two test names the plan doc had named were wrong (`PB-M4.1`'s, and PB-M2.2's
  after the rewrite). Found by checking every `::test_` reference in both docs
  against the suite, not by review. Both corrected.
- No review pass has run over PB-M6/PB-M7 itself. The sweep covered
  `99d438f...2e4add9`; this work sits after it.

### Next agent actions

- Walk the item-row heights and the continuation colours on screen in the demo.
- Re-walk the drag feel, still outstanding from PB-M5.
