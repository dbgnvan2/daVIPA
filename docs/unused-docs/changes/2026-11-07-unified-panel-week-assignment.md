# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: unified-panel-week-assignment (UPD-M5)

## Summary

APE Week Assignment's two panels now draw with the shared modules the other
three two-panel tabs adopted at UPD-M1 and UPD-M4: `SplitPanel` for the
divider, `RowDragSource` for the left-to-right drag, and `ChipTable` for the
header, the rows, the chips and the column widths. It was the fourth and last
copy of the splitter and of the drag in scope, so UPD-M1.5 and UPD-M2.5 are
`done` and both AST holdout sets are empty.

What changed on the screen:

- The right panel has an **Actions** column with a **Delete** on every row
  (M5.1, M5.2). It asks before deleting (M5.3).
- `Delete Weekly` stays below the panel and still acts on the selection, as do
  `Edit Weekly Tactic` and `Add Action Item` (M5.4). The row's Delete and the
  button are **one method with two callers**, `delete_weekly_row`, so the
  confirmation exists once.
- The left header's first cell is blank and 34px wide, not 52px and "Pick"
  (M5.5).
- Both panels' columns drag and persist per panel, and the divider ratio
  persists (M5.6). Three new `AppSettings` fields:
  `week_assignment_split_ratio`, `week_assignment_left_col_widths`,
  `week_assignment_right_col_widths` - an undeclared field is dropped silently
  at the next launch, so this is load-bearing.
- The three name columns are 135 / 155 / 125 rather than 180 each, which is
  what the other tabs use. §1.4 of the spec named the differing widths as a
  difference from the image, so the change is the alignment asked for.

One pre-existing defect fixed by the adoption: `on_select_weekly_item`
re-rendered the right panel without destroying what was there, so every
selection click gridded a fresh header and a fresh set of rows into the same
cells as the old ones - three clicks on a two-row week took the panel from 3
children to 12. Only `_render_lists` ever cleared. `ChipTable.build_header()`
clears its container, so adopting the table is the fix (M5.7).

The spec disagreed with itself about whether `Delete Weekly` survives: §2's D5
lists only the two other buttons as staying, §5's risk list says in as many
words that it stays. Kept, with the reason recorded in the spec's §10: §5 is
explicit where D5 is an implication, and removing a working button is the one
reading a later step cannot undo.

## Files changed

- `src/getmoredone/screens/weekly_items.py` - 610 to 677 lines; nine
  splitter-and-drag methods, `_clear_scroll` and `_clip_label` removed,
  `_assign_dragged_row`, `_row_colors`, `_show_list_or_message` and
  `delete_weekly_row` added
- `src/getmoredone/app_settings.py` - three new fields
- `tests/test_unified_panel_design.py` - 50 to 64 tests; both holdout sets
  emptied and the two guards rewritten to assert emptiness
- `tests/test_weekly_tactic_schema.py` - three tests moved from
  `_finish_row_drag` to `_assign_dragged_row`, case (b) the behaviour changed
  intentionally; two gained `assert "refresh" not in said`
- `docs/spec_2026-11-07_unified_panel_design.md` - status line, M1.5 and M2.5
  rows, §1.4 note, §4 step 5, and the UPD-M5 §10 block
- `docs/spec_coverage.md` - UPD-M5 table, M1.5 and M2.5 to done
- `docs/DOCUMENTATION_INDEX.md`, `CHANGELOG.md`, `NOTES.md`, `BACKLOG.md`

## Verification

Every run used `GETMOREDONE_NO_MAPPED_WINDOWS=1` and the repo venv, targeted at
the files the change touches.

- Command: the touched pair - `tests/test_unified_panel_design.py`,
  `tests/test_weekly_tactic_schema.py`
- Result: PASS - 64 passed, then 19 passed

- Command: the 12 touched and meta files - `test_unified_panel_design`,
  `test_weekly_tactic_schema`, `test_ape_week_actions`, `test_weekly_items_title`,
  `test_weekly_items_week_options`, `test_ape_period_consistency`,
  `test_settings_isolation`, `test_weekly_item_filters`, `test_column_resize`,
  `test_no_vacuous_tests`, `test_traceability_refs`, `test_ci_contract`
- Result: PASS - 287 passed, 1 skipped (`test_ci_contract.py:371`, CI-only
  display check)

- Command: a second meta batch adding `test_release_docs`,
  `test_vision_planning_regressions`, `test_weekly_tactic_surfaces`
- Result: PASS - 165 passed, 1 skipped

- Command: mutation gate, 17 mutations, each the verbatim original line, each
  run alone, every file restored and sha256-compared
- Result: PASS - 17/17 red. 15 red on the first pass; the 2 green were
  weaknesses in the tests, both stated as case (c) over-specified or vacuous
  and strengthened until red:
  - the empty-state test read the labels' *text*, and the labels are built in
    `create_ui` and only gridded and un-gridded, so inverting the branch left
    it green. It now asserts which of the two widgets in that grid cell is
    gridded, in both the empty and the filled case.
  - the per-panel width test resized the left panel and read the right panel's
    width in memory, where a shared store does not show: a right table built
    on the left prefix loads the store before the drag and holds the default
    for the rest of the session. It now rebuilds the screen from the same
    settings and asserts the right panel is still at its own default.

## Risks / Known gaps

- **Not verified on screen.** Nothing in UPD-M1 through UPD-M5 has been seen
  running. UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are open.
- The column widths of this tab's two panels change on the first launch after
  this change, deliberately (see Summary). A user who had been living with the
  clipped 180px columns will see narrower ones, now draggable.
- `/csdp` is owed over the unpushed range before anything is pushed.
- Adjacent issue found and not fixed, per the standing rule: **UPD-A8**, an
  unused `import tkinter as tk` at `weekly_items.py:10`. Filed in `BACKLOG.md`.

## Next agent actions

- UPD-M6: APE Week Actions adopts the divider, the chip table and the filters.
  No row drag on that tab, per the spec's D6.
- UPD-M7: the on-screen pass over all four tabs.
- Run `/csdp` over the unpushed range before pushing.
