# Handoff Note

- Date: 2026-11-11
- Topic: vsp-tab-filters-and-adds (VTF-M1 - VTF-M7, VTF-N1, VTF-N2)

## Summary

The four dual-panel VSP Plan tabs now read their left-hand ticks as a filter on
the right panel, each of the five record panels has an Add New button under its
list, and the header `Save` that used to write from those ticks is gone. APE
Week Assignment's three bottom buttons became one. Full criteria table and
proof: `docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md`,
status report at the end.

This note exists for three things a commit message does not carry: the two
on-screen criteria no test can reach, the one code hop no test can reach, and
the three adjacent issues found and not fixed.

## Files changed

- `src/getmoredone/screens/pick_record_dialog.py` (new)
- `src/getmoredone/screens/annual_vision_segments.py`
- `src/getmoredone/screens/ape_assignment.py`
- `src/getmoredone/screens/ape_period_view.py`
- `src/getmoredone/screens/weekly_items.py`
- `src/getmoredone/screens/week_actions.py`
- `src/getmoredone/screens/vision_segments.py`
- `tests/test_vsp_tab_filters.py`, `tests/test_vsp_tab_adds.py`,
  `tests/test_vsp_tab_contracts.py` (new)
- `tests/test_ape_period_consistency.py`, `tests/test_weekly_tactic_schema.py`
- `docs/USER_GUIDE.md`, `CHANGELOG.md`, `BACKLOG.md`,
  `docs/DOCUMENTATION_INDEX.md`, `docs/ui_color_inventory.md`,
  `docs/spec_2026-11-07_ape_period_consistency.md`,
  `docs/spec_2026-11-07_unified_panel_design.md`

Commits: `a637917`, `dec6e9d`, `1d69964`, `20bf04c`, `3e7b0af`, `e8d8b3e`,
`3ff52ae`, `5d42e8f`.

## Verification

Every run was prefixed `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy
-b`, against `./venv/bin/python -m pytest … -q`.

- Files: `tests/test_vsp_tab_adds.py tests/test_vsp_tab_contracts.py`
- Result: PASS (20 tests)
- Files: `tests/test_ape_period_consistency.py tests/test_weekly_tactic_schema.py`
- Result: PASS (72 tests)
- Files: `tests/test_vsp_tab_filters.py tests/test_unified_panel_design.py tests/test_ape_week_actions.py`
- Result: PASS (147 tests)
- Files: `tests/test_traceability_refs.py tests/test_color_inventory_sync.py`
- Result: PASS (39 tests)
- Command: `./venv/bin/python tools/agents/check_docs_sync.py`
- Result: PASS
- Mutation: 39 mutants, 39 killed, across three drivers (10 for VTF-M1/M2, 8
  for the rewritten APC tests, 16 for VTF-M3/M4/M5, 15 for VTF-M6/M7 — the
  first driver's 10 overlap the APC set). Each restored the verbatim original
  in a `finally:`.
- **Not run:** the full suite. Per `~/.claude/standards/effort-budget.md` and
  this repo's throttle rule, CI runs it on push.

## Risks / Known gaps

- **VTF-N1 — not done, on-screen walk item.** Does the filter *read* as a
  filter? Per tab (Annual Plan Elements, APE Quarter Assignment, APE Month
  Assignment, APE Week Assignment): tick one left row, confirm the right panel
  narrows to its records and the right heading names the filter; untick,
  confirm it widens again; tick two, confirm both sets appear; set the left
  dropdown so a ticked row is hidden, confirm the filter drops.
- **VTF-N2 — not done, on-screen walk item, and the one hop no test covers.**
  `open_pick_record_dialog`'s join between `on_confirm` and `report` — the line
  that writes the write's sentence to the tab's status line after the dialog
  closes — cannot be driven by a test, because a real `CTkToplevel` is a mapped
  window and `tests/test_ci_contract.py` pins that count at 23. Both ends are
  covered (each tab hands the dialog its own `_perform_add` and its own status
  label; each write reconciles and returns a sentence); the join is not. It is
  one function for all four tabs, so one check covers it: on any one tab, press
  Add New, confirm, and read the status line. While there, confirm the dialog
  opens at all on macOS without a `TclError` — the PF-M1 failure mode — on each
  of the four tabs.
- **The annual tab's drag drop target has no drag test of its own.**
  `annual_vision_segments.py:202` builds a `RowDragSource` onto the right
  frame; it is unchanged code, and VTF-M4.3 is proved for the other three tabs
  by `tests/test_ape_period_consistency.py` and
  `tests/test_weekly_tactic_schema.py`. Worth one drag on that tab during the
  walk.
- **Adjacent issues found, not fixed** (global rule 10) — filed as VTF-A1,
  VTF-A2 and VTF-A3 in `BACKLOG.md`: the unreachable second annual panel in
  `screens/vision_planning.py`, the two now-unreachable `weekly_items`
  selection methods still covered by three test files, and the withdrawn-root
  screen builder duplicated across four test files.

## Next agent actions

- Walk VTF-N1 and VTF-N2 on screen, with the annual tab's drag, and record the
  result here or in a dated note beside this one.
- VTF-A1 is the one worth doing next: a second copy of a panel that did not get
  this batch's change is how one copy rots unseen.
