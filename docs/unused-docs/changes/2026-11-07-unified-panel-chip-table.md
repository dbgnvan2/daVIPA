# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: unified-panel-chip-table (UPD-M4)

## Summary

UPD-M4 of `docs/spec_2026-11-07_unified_panel_design.md`. The three VSP tabs
that have two panels — APE Quarter Assignment, APE Month Assignment and Annual
Vision Segments — now draw their six panels with the three shared modules
extracted at UPD-M1 to UPD-M3: `split_panel.SplitPanel` for the divider,
`row_drag.RowDragSource` for the assign-by-drag, and `chip_table.ChipTable`
over `column_resize.ColumnResizer` for the rows.

What this changes for the user: every column on all six panels can now be
dragged wider or narrower and each panel remembers its own widths (none of the
three tabs had resizable columns before), the divider on APE Month and Annual
now stays where it is left, and a chip no longer loses its last character.

What it changes in the code: nine splitter-and-drag methods and a private
`_clip_label` are gone from each of the two screens that still had them, and
each screen keeps only `_assign_dragged_row` (or, on Annual, `_create_from_row`
directly) — what a dropped row *means* stays with the screen that means it.
`annual_vision_segments.py` is 106 lines shorter, `ape_period_view.py` 82,
`ape_assignment.py` 51.

Two defects in UPD-M3's own config were found by the first screen that adopted
the table, and both were fixed here:

- `ChipColumn.min_width` defaulted to 40 while the checkbox and `#` columns
  declared 34. `ColumnResizer` clamps into range, so both rendered at 40 and
  nothing said so. Caught by UPD-M4.1's pixel assertion on its first run after
  adoption, which is the whole case for writing that test before touching the
  screen. `::test_updm31_every_shipped_column_declares_a_width_it_can_have`
  now holds it for every shipped set.
- `APE_COLUMNS` was one six-column set holding both the checkbox column and
  the Actions column. No panel has both, and a column's grid index is its
  position in the set, so that one set put every column of every panel one
  place to the right. Replaced by `APE_LEFT_COLUMNS`, `APE_RIGHT_COLUMNS` and
  `ANNUAL_RIGHT_COLUMNS`.

AWA-S5 and AWA-S6 — the two review findings filed to be settled before the
first screen adopted — are settled. AWA-S5 is fixed in `column_resize.py`:
`chars` and `cell_text` take the `width_delta` that `register_row` already
took, so a chip's character budget is measured from the pill and not from the
column around it. Four of AWA-S6's five assumptions are now enforced
(`clear_header()`, the container's column weight, and two `add_row` guards);
the fifth — the table owning its container outright — is stated in the class
docstring rather than changed, because destroying only the table's own widgets
would leave a stale label behind for a screen that added one.

**Correction to the UPD-M1 and UPD-M2 handoff notes.** Both said the remaining
holdouts adopt at UPD-M4 and that UPD-M1.5 and UPD-M2.5 close there. They do
not. UPD-M4 covers the three APE/Annual tabs; the fourth copy of the splitter
and of the drag is in `weekly_items.py`, which UPD-M5 rewrites rather than
converts. Both criteria stay `partial`, with one file left in each holdout set,
and close at UPD-M5. The spec, `docs/spec_coverage.md`, both guard-test
docstrings and `BACKLOG.md`'s UPD-A6 are corrected.

## Files changed

- `src/getmoredone/screens/annual_vision_segments.py`
- `src/getmoredone/screens/ape_assignment.py`
- `src/getmoredone/screens/ape_period_view.py`
- `src/getmoredone/screens/chip_table.py`
- `src/getmoredone/screens/column_resize.py`
- `src/getmoredone/app_settings.py`
- `tests/test_unified_panel_design.py`
- `tests/test_ape_period_consistency.py`
- `docs/spec_2026-11-07_unified_panel_design.md`
- `docs/spec_coverage.md`
- `docs/DOCUMENTATION_INDEX.md`
- `CHANGELOG.md`
- `NOTES.md`
- `BACKLOG.md`
- `docs/unused-docs/changes/2026-11-07-unified-panel-chip-table.md` (this note)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_unified_panel_design.py tests/test_ape_period_consistency.py tests/test_vps_ape_deletion_ui.py tests/test_ape_week_actions.py tests/test_column_resize.py tests/test_drag_schedule_support.py tests/test_today_title_col_width.py tests/test_today_screen.py tests/test_weekly_tactic_schema.py tests/test_settings_isolation.py -q`
- Result: PASS — 202 passed

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_ci_contract.py tests/test_no_vacuous_tests.py tests/test_traceability_refs.py tests/test_release_docs.py tests/test_vision_planning_regressions.py -q`
- Result: PASS — 133 passed, 1 skipped (`tests/test_ci_contract.py:371`, a CI-only display check)

- Command: mutation gate, 13 mutations, each the verbatim original, each run
  alone, every file restored and sha256-compared afterwards
- Result: PASS — 13 red on the first pass. They cover both AWA-S5 paths, all
  four AWA-S6 guards, the `min_width` clamp, APE Month's drag binding, its
  splitter and its settings prefix, Annual's Actions-column width and its drop
  callback, and the quarter tab's two panels sharing one width store.

## Risks / Known gaps

- **Not seen running.** Three tabs changed their renderer, their splitter and
  their drag in one step and none has been looked at on screen. Every test
  builds its screens on a withdrawn root. UPD-M7.2 and UPD-M7.3 are the
  on-screen criteria and are open, as is the AWA nine-step on-screen checklist
  at the end of `docs/spec_2026-11-07_ape_week_actions.md` §6.
- **UPD-M4.2 is `partial`, not `done`.** One existing test changed:
  `tests/test_ape_period_consistency.py::test_apcm23_drag_path_reaches_the_same_reporting`
  drove `_finish_row_drag`, which the screen no longer has. Case (b), the
  behaviour moved; it drives `_assign_dragged_row` now, as its APE Quarter
  sibling already did at UPD-M2, and it gained the same `refresh` assertion.
  "Their existing test files pass unchanged" is therefore false.
- **Two cosmetic changes nothing pins.** The header's blank checkbox cell is
  gridded with `padx=5` where the screens used `padx=2`, a 3px shift; and a
  clipped chip ends in `...` where the screens' own `_clip_label` used `…`,
  because the shared table clamps through `title_format.format_column_text`
  as Today and the Scheduler do. Chip text also now follows the column width
  rather than a fixed 15 characters (UPD-M3.5 as specified): at the default
  widths SubSegment shows 17 characters where it showed 15, and Category 14.
- **Adjacent issue found, not fixed:** UPD-A7 in `BACKLOG.md` — `drag_index`
  and `_create_from_index` in `annual_vision_segments.py` have no reader and
  no caller anywhere in `src/` or `tests/`. Left under the standing rule
  against sweeping adjacent code into a feature change.

## Next agent actions

- Walk UPD-M7's on-screen checks on the three tabs: drag a column on each of
  the six panels and relaunch, drag the divider on APE Month and Annual and
  relaunch, drag a row left to right on each tab, and confirm a chip's text is
  not clipped at the default widths.
- UPD-M5 next in the plan's order: rewrite APE Week Assignment's two panels on
  the same three modules. That is the step that empties `SPLITTER_HOLDOUTS`
  and `DRAG_HOLDOUTS` and closes UPD-M1.5 and UPD-M2.5.
- `/csdp` is owed over the unpushed range before anything is pushed; it now
  carries this batch as well as the nine commits before it.
