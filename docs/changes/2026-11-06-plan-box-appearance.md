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

## Adjacent issues found, not fixed

- A press that lands exactly on a 14x3px depth bar does not start a drag
  (already in `BACKLOG.md`; still true, and the bars are now visible on the
  Day Plan too, so the target exists in one more place).
- `docs/spec_coverage.md`'s third human-review row ("does a drag feel right")
  is still outstanding and is now overtaken by PB-M5 — a chip is no longer
  30px by definition.

## Next agent actions

- Re-walk the drag feel on screen once a box height other than 30 is in use.
