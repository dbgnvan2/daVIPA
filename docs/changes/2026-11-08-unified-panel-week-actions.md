# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: UPD-M6 — APE Week Actions joins the one panel design

## Summary

Step 6 of the seven in `docs/spec_2026-11-07_unified_panel_design.md` §4. APE
Week Actions was the one tab in the VSP hub built to a different brief: no
divider, a stack of `CTkButton`s for the tactic list, and none of the three
lineage filters the other five tabs have. All seven UPD-M6 criteria are `done`;
per-criterion evidence is in the spec's §10 and `docs/spec_coverage.md`.

What the tab has now:

- **A draggable divider** (`screens/split_panel.py`, prefix `week_actions`),
  where the body was `minsize=380` on the left and `weight=1` on the right.
  The ratio persists in `AppSettings.week_actions_split_ratio`.
- **The shared chip table** for the tactic list — `#` / Weekly Tactic /
  Segment / SubSegment / Category at 34 / 220 / 135 / 155 / 125, every column
  draggable, under its own `week_actions_left` width store. Every cell in a row
  carries the click, not just the row frame.
- **Segment / SubSegment / Category filters.** The combos offer only the values
  the week contains; a selection the next week cannot match falls back to All;
  an empty result names the filter and the hidden count, and an empty week says
  that instead (P2); the selection survives a filter unless the filter hides it.
- **The Actions panel untouched**, still a `TodayScreen` subclass on the
  `week_actions` prefix (D3), and still no drag or drop target on this tab (D6).

Three rules moved into one owner each rather than being written a sixth time:
`screens/lineage_filters.py` (new) for the filter triple and the two lineage row
readers, `segment_color_utils.load_category_color_map` / `resolve_chip_colors`
for the category chip colour, and `chip_table.show_list_or_message` for the
list-or-message rule UPD-M5 wrote inline. `weekly_items.py` was moved onto all
three in the same change, because it is the other screen this batch owns.

One defect in the shared table, found while writing UPD-M6.2's test: `add_row`
clamped a chip to its column but gave a plain text cell its raw text, so a
Title column opened with one row pushing every column out of line and corrected
itself the moment the handle was touched. A resizable plain column is clamped at
the first render now; a fixed-width one keeps its raw text, because the resizer
never re-clamps a column with no handle.

## Files changed

- `src/getmoredone/screens/week_actions.py` — the rewrite: divider, chip table,
  filters, counts, per-cell click, `tactic_row_frames` in place of
  `tactic_buttons`
- `src/getmoredone/screens/lineage_filters.py` — **new**, the filter triple and
  `weekly_tactic_parts` / `annual_plan_element_parts`
- `src/getmoredone/screens/segment_color_utils.py` — `load_category_color_map`,
  `resolve_chip_colors`
- `src/getmoredone/screens/chip_table.py` — `WEEK_ACTIONS_LEFT_COLUMNS`,
  `show_list_or_message`, and the plain-cell clamp in `add_row`
- `src/getmoredone/screens/weekly_items.py` — moved onto the three shared seams
- `src/getmoredone/app_settings.py` — `week_actions_split_ratio`,
  `week_actions_left_col_widths`
- `tests/test_unified_panel_design.py` — 15 new tests for UPD-M6 (79 in the
  file)
- `docs/spec_2026-11-07_unified_panel_design.md` — status, §1.5, §4 step 6, §8,
  and §10's UPD-M6 block
- `docs/spec_coverage.md` — the UPD-M6 table
- `docs/DOCUMENTATION_INDEX.md`, `CHANGELOG.md`, `NOTES.md`, `BACKLOG.md`
  (UPD-A9)

`tests/test_ape_week_actions.py` carries this batch's two edits — a
`_settings_stub` helper with the two new settings fields, and `test_awam42`
reading `tactic_row_frames` rather than `tactic_buttons` (case (b), the
behaviour changed intentionally). Those edits were swept into commit `869cbd6`
by the concurrent WTP batch rather than committed here.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_unified_panel_design.py tests/test_ape_week_actions.py -q`
- Result: PASS — 112 passed

- Command: the same, over `test_unified_panel_design`, `test_ape_week_actions`,
  `test_weekly_tactic_schema`, `test_column_resize`,
  `test_ape_period_consistency`, `test_settings_isolation`,
  `test_weekly_item_filters`, `test_weekly_items_title`,
  `test_weekly_items_week_options`, `test_no_vacuous_tests`,
  `test_traceability_refs`, `test_ci_contract`
- Result: PASS — 301 passed, 1 skipped (`test_ci_contract.py:371`, CI-only), after
  one failure that was not this batch's: `test_traceability_refs` was red over
  nine `Tests:` references naming WTP tests that did not exist yet, and the WTP
  batch wrote them in `a0fb2d3`. Re-run green here after that commit.

- Command: the same, over `test_release_docs`,
  `test_vision_planning_regressions`, `test_weekly_tactic_surfaces`
- Result: PASS — 75 passed

- Mutation gate: 20 mutations, each the verbatim original, one at a time, every
  file restored and sha256-compared. **20 red, no finding.** Runner at
  `mutate_m6.py` in the session scratchpad.

## Risks / Known gaps

- **Not seen running.** Every test builds the screen on a withdrawn root.
  UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are open for UPD-M1
  through UPD-M6.
- Four deliberate, visible behaviour changes, all recorded in the spec's §10:
  the left panel's minimum goes 380 → 420 (`MIN_PANEL_WIDTH`); the list is a
  table with a Title column where it was two-line buttons; the three filters
  are new; the heading and status line say "shown of total" only while
  filtering, so the unfiltered strings `test_awam43` asserts are unchanged.
- **UPD-A9** is filed, not fixed: five files still hold their own copy of the
  filter triple and/or the category colour key, two of them with a different
  fall-back. Reconciling the fall-backs is a behaviour change on four screens
  and belongs in its own batch.
- The repository was being committed to concurrently while this batch was built
  (PLC and WTP). One of those commits picked up this batch's
  `tests/test_ape_week_actions.py` edits (see above), and an earlier run of
  `test_ci_contract.py::test_rm3d_every_test_file_is_importable_on_its_own`
  failed once on `tests/test_weekly_tactic_parent.py` while that file was
  landing. It passed on two later runs, alone and in the twelve-file set, and
  no change here touches it.

## Next agent actions

- UPD-M7: the meta test (M7.1), the docs, and the on-screen checklist that
  M7.2 and M7.3 need. UPD-M7 is the last step of this plan.
- `/csdp` is owed over the unpushed range before anything is pushed; the sweep
  has not run for UPD-M5 or UPD-M6.
