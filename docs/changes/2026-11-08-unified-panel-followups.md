# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: unified-panel-followups — UPD-F2, UPD-F3, UPD-F4 (UPD-F1 not built)

## Summary

Three of the four items the on-screen walk of
`docs/spec_2026-11-07_unified_panel_design.md` §11 produced, approved as
`docs/implementation_plan_2026-11-08_unified_panel_followups.md`.

**UPD-F3 — the checkbox column says "Pick".** `APE_LEFT_COLUMNS`' first
column gets the heading back. UPD-M5.5 had blanked it; the walk asked for a
word there. The plan expected the 34px column to widen — measured in the
bold header font, "Pick" is **28px**, so no width moved and the measurement
is recorded in the source comment and asserted by the test. The plan also
said three panels share the column set; **four do**, Annual Plan Elements
included, and the test pins the adopter list.

**UPD-F2 — the filter area is three lines deep on every tab.** Each of the
five hub tabs now grids `self.filter_row`, a frame of its own, at header row
2, and puts the three lineage combos inside it at its own row 0. The status
line moved to row 3 on the four tabs that have one — on APE Week Assignment
it was a twelfth column of the controls row, and on APE Week Actions it sat
beside the last combo. Annual Plan Elements has **no** lineage filters (there
is nothing above an annual plan element to filter by), so its title moved to
row 0 alone, its Year/Load/Save/Refresh controls to row 1, and row 2 is an
empty frame one combo high — the blank line the walk asked for by name. A
frame rather than six more header cells because grid columns are shared
between rows: filters gridded straight into the header would have coupled a
150px combo's column to the Year entry's.

Two of the plan's criteria were corrected against the code, IDs kept:
UPD-F2.2 described a blank spacer row between title and filters, which never
existed; UPD-F2.4 said Annual Plan Elements had its filters inline, and it
has none.

**UPD-F4 — the columns rescale with the divider, floor five characters.**
`ColumnResizer.fit_to_width(available)` shares a panel across its resizable
columns by weight — a stored width is a weight, not a pixel promise, which is
what lets a drag and a resize coexist — with the fixed columns reserved out
first and a floor of `min_column_width()` = 5 × `CHAR_PX` = 40. It returns the
pixels by which the columns overrun the panel, zero when they fit, so a panel
too narrow for its floors is a number rather than a clipped column (P2).
`SplitPanel.apply` gained an `on_apply(left_px, right_px)` callback, because
it is the only place that knows a panel's new width, and the five screens pass
`chip_table.panel_fitter(...)`. Every resizable chip column's `min_width`
dropped to the floor: 60 for the three chips, 52 for Done, 80 for Week
Actions' Title.

**UPD-F1 was not built.** It is the only defect of the four — no column width
or divider position survives a relaunch, because `AppSettings.save()` writes
`asdict(self)` and a screen holding an older snapshot reverts fields another
object changed. `src/getmoredone/app_settings.py` carries the calendar-export
batch's uncommitted hunk, and `CLAUDE.md`'s "One build batch at a time" rules
out a second writer in this index. Proposed as its own worktree session.

## Files changed

Source:
- `src/getmoredone/screens/chip_table.py` — "Pick"; every resizable column's
  `min_width` to the five-character floor; `HEADER_PADX` / `CELL_PADX` named
  and used at their grid calls; `fit_to_panel`, `available_width`,
  `panel_fitter`.
- `src/getmoredone/screens/column_resize.py` — `MIN_COLUMN_CHARS`,
  `min_column_width`, `fit_to_width`, `_share`, `_apply_all`.
- `src/getmoredone/screens/split_panel.py` — the `on_apply` callback.
- `src/getmoredone/screens/lineage_filters.py` — `FILTER_ROW_HEIGHT`.
- `src/getmoredone/screens/ape_assignment.py`,
  `src/getmoredone/screens/ape_period_view.py`,
  `src/getmoredone/screens/weekly_items.py`,
  `src/getmoredone/screens/week_actions.py`,
  `src/getmoredone/screens/annual_vision_segments.py` — the filter row, the
  status line's row, and `on_apply=panel_fitter(...)`.

Tests:
- `tests/test_unified_panel_design.py` — four UPD-F3 tests, five UPD-F2
  tests, seven UPD-F4 tests, and five expectations changed from `""` to
  `"Pick"` (case (b), the behaviour changed intentionally; the docstrings say
  so, including `test_updm55_left_header_matches_the_other_tabs`, whose claim
  UPD-F3 reverses).

Docs:
- `docs/implementation_plan_2026-11-08_unified_panel_followups.md` — the four
  corrections, what was actually built, three new adjacent issues.
- `docs/spec_2026-11-07_unified_panel_design.md` — the status line, the
  UPD-F1…F4 block in §10, §11 steps 4 and 7 rewritten to match what is there
  now, and three new §11 steps (11, 12, 13) for UPD-F2.6, F3.5 and F4.7.
- `docs/spec_coverage.md` — a row per criterion with its proof.
- `docs/DOCUMENTATION_INDEX.md`, `CHANGELOG.md`, `NOTES.md`, `BACKLOG.md`.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_unified_panel_design.py tests/test_column_resize.py tests/test_ape_week_actions.py tests/test_ape_period_consistency.py tests/test_weekly_item_filters.py tests/test_vision_planning_regressions.py tests/test_today_screen.py tests/test_today_title_col_width.py tests/test_weekly_tactic_parent.py tests/test_no_vacuous_tests.py -q`
- Result: **PASS** — 260 passed.
- Mutation gates: UPD-F3 **6/6 red**, UPD-F2 **7/7 red**, UPD-F4 **9/9 red**.
  Each mutation was the verbatim original, applied one at a time to a pristine
  copy and compared back byte-for-byte; the baseline was re-run green after
  each gate. One UPD-F4 mutation (dropping the spare pixels integer shares
  leave) survived the first gate because the fill assertion allowed a pixel
  of slack per column; the assertion was tightened to an exact fill and the
  mutation re-ran red.
- `tests/test_traceability_refs.py` is **red on nine refs, none of them
  UPD-F's.** All nine are the concurrent plan/time-block/priority batch's:
  `models.py` naming two `test_priority_floor_*` files that do not exist, and
  seven `pdm*`/`tgm*` test names in `docs/spec_coverage.md`, `plan.py` and
  `time_block_layout.py`. One UPD-F ref was wrong when first written
  (`annual_vision_segments.py` named `test_updf25_…` for a test called
  `test_updf24_…`) and was corrected; the suite confirms no UPD ref fails.
- **The app was not launched.** No step of this batch was seen running.
  UPD-F2.6, UPD-F3.5 and UPD-F4.7 are `not done` and are spec §11 steps 11,
  12 and 13.

## Risks / Known gaps

- **UPD-F1 is still owed**, so nothing UPD-F4 renders survives a relaunch.
  UPD-F4.6 is proved against the settings double, not against a real restart.
- **A column at the floor clips its own heading.** "SubSegment" measures 84px
  in the bold header font; the floor is 40px. True at the old 60px minimum
  too, and the walk asked for the narrower floor explicitly. Not fixed.
- **APE Week Actions' right panel is not fitted.** A `TodayScreen` subclass
  with its own `ColumnResizer` and its own padding, so `panel_fitter` gets
  the left table alone. Asserted, so it cannot become half-done silently.
- **`weekly_items.py` still abbreviates two filter labels** ("Sub:", "Cat:")
  where the APE tabs write them out. UPD-A9's to unify; rewording here would
  be a silent sweep.
- Every width the fitter computes is written to settings on the next column
  drag, because `_persist` writes the whole width map. That is the weight
  model working as designed, and it means a user who resizes the window and
  then drags one column has stored the fitted widths of all of them.
- **Four commits of this batch were built through a temporary
  `GIT_INDEX_FILE`**, as the previous two were: `CHANGELOG.md`, `NOTES.md`,
  `BACKLOG.md` and `docs/DOCUMENTATION_INDEX.md` carry the calendar-export
  batch's uncommitted hunks and must not be staged.

## Next agent actions

- Walk spec §11 steps 11, 12 and 13 in the running app and record the verdict
  against UPD-F2.6, UPD-F3.5 and UPD-F4.7. Steps 4 and 7 changed, so a re-walk
  of those two is owed before UPD-M7.2 and UPD-M7.3 can move off `partial`
  and `not done`.
- Build UPD-F1 in its own worktree, or after the calendar-export batch has
  committed `src/getmoredone/app_settings.py`. Its test is written and watched
  fail before the fix (P10).
- `/csdp` is owed over the whole unpushed range — 45-plus commits before this
  batch.
