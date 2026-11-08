# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: UPD-M2 — one row-drag, not four

## Summary

`screens/row_drag.py` is new and owns dragging a row from a two-panel tab's
left list onto its right list: binding the row's widgets, holding the dragged
row, and deciding on release whether the pointer is inside the target.
`_bind_drag_widgets`, `_start_row_drag` and `_is_descendant` were
byte-identical in `annual_vision_segments.py`, `ape_assignment.py`,
`ape_period_view.py` and `weekly_items.py` — measured with `diff` before
anything was removed. `_finish_row_drag` differed in one place only: the body
of its final `if`, which is what a dropped row *means*, and that stays with the
screen. On APE Quarter Assignment it is now `_assign_dragged_row`, passed to
`RowDragSource` as `on_drop`. The other three screens adopt at UPD-M4, per the
spec's implementation order.

Unlike UPD-M1, this extraction carries **no behaviour change**. The three
shared methods moved as they were, and `finish` keeps the original order:
unbind, guard on no row, read the pointer, clear the row, test the drop.

The spec's own description of the drag was wrong and is corrected where it
stood (§1.2 and the UPD-M2.1 criterion row): it said press, motion and release
were bound on the row and its chips. Only the press is on the row's widgets;
the release is on the toplevel, so a release anywhere in the window ends the
drag; and there is **no motion handler on any of the four copies** — nothing is
drawn while a row is dragged, so there is nothing for one to do.

## Files changed

- `src/getmoredone/screens/row_drag.py` (new, 92 lines)
- `src/getmoredone/screens/ape_assignment.py` (adopts it; the four drag methods
  go, `_assign_dragged_row` carries the drop)
- `tests/test_unified_panel_design.py` (7 new tests, +248 lines)
- `tests/test_ape_period_consistency.py` (one test moved to the new seam, plus
  one assertion the mutation gate showed was missing)
- `docs/spec_2026-11-07_unified_panel_design.md` (§1.2 and the M2.1 criterion
  corrected, §10 status added)
- `docs/spec_coverage.md`, `docs/DOCUMENTATION_INDEX.md`, `CHANGELOG.md`,
  `NOTES.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_unified_panel_design.py tests/test_ape_period_consistency.py tests/test_weekly_tactic_schema.py tests/test_settings_isolation.py tests/test_ci_contract.py tests/test_no_vacuous_tests.py tests/test_traceability_refs.py tests/test_release_docs.py -q`
- Result: PASS — 230 passed, 1 skipped (the CI-only display check in
  `test_ci_contract.py`).
- Mutation gate: 9 mutations, each the verbatim original, each run alone, every
  file restored and sha256-compared. First run: 7 red, **2 green**. Both green
  results were findings about the tests, and both are fixed; re-run 9 red.
- The drop path cannot be driven with real widgets at all:
  `winfo_pointerxy()` reads the real mouse. The UPD-M2.2 to M2.4 tests use
  doubles, which is also how `tests/test_ape_period_consistency.py` already
  drove this path.

### The two green mutations

- **Removing the lambda's `r=row` default left `test_updm21` green**, and the
  test's docstring claimed the default guards against the late-binding trap.
  The claim was false: `bind_row` loops over the *widgets*, while `row` is the
  call's own parameter, so every call already closes over its own row. The
  docstring now says what was measured and names the two mutations that do turn
  the test red; `row_drag.py` records that the default is kept for intent, not
  effect, and that no test asserts it.
- **Removing `refresh_lists()` from the quarter screen's drop left every
  APC-M6.2 assertion green.** `tests/test_weekly_tactic_schema.py:393` pins
  that same redraw-on-refusal for the weekly screen; its sibling here had
  nothing holding it (P5). The gap predates this step.
  `assert "refresh" in said` closes it.

## Risks / Known gaps

- **UPD-M2.5 is `partial`, not `done`**, for the same reason as UPD-M1.5: the
  AST guard is exact in both directions — red if a new screen grows its own
  drag, red again when a holdout adopts without being struck off `DRAG_HOLDOUTS`
  — but the count is not 0 while three screens still hold their copies. They
  adopt at UPD-M4. Recorded as UPD-A6, which covers both criteria.
- **Nothing has been seen on screen.** Every test here builds its screen on a
  withdrawn root or on doubles. A real drag of a real row has not been
  performed since the extraction. UPD-M7.2 and UPD-M7.3 are the on-screen
  criteria and are open.
- One test changed to keep passing, case (b) — the behaviour moved:
  `test_apcm62_quarter_drag_path_reaches_the_same_reporting` drove
  `_finish_row_drag`, which no longer exists on the screen; it drives
  `_assign_dragged_row` now. The six stub members that existed only to fake the
  drag machinery are gone with it.

## Next agent actions

- UPD-M4: roll `split_panel`, `row_drag` and `chip_table` through
  `ape_period_view.py`, `annual_vision_segments.py` and `weekly_items.py`. It
  is the step that makes UPD-M1.5 and UPD-M2.5 both read 0. Settle AWA-S5 and
  AWA-S6 before the first screen adopts `chip_table`.
- `/csdp` is owed over the accumulated unpushed range — UPD-M3, UPD-M1 and
  UPD-M2 — before anything is pushed.
- The APE Week Actions on-screen checklist (the end of
  `docs/spec_2026-11-07_ape_week_actions.md` §6) is still unwalked.
