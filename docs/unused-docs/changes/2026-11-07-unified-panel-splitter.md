# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: UPD-M1 — one splitter, not four

## Summary

`screens/split_panel.py` is new and owns the vertical divider between a
screen's two panels: the ratio, the clamp, the three divider handlers and the
body's resize handler. The same 30 lines were written out in
`annual_vision_segments.py`, `ape_assignment.py`, `ape_period_view.py` and
`weekly_items.py` — `diff` across all four is byte-identical, measured before
anything was removed. APE Quarter Assignment (`ape_assignment.py`) has adopted
the module and lost its copy; the other three adopt at UPD-M4, per the spec's
implementation order.

Two deliberate differences from the four copies, both named in the spec's §10:

- **The ratio persists** (UPD-D4). It never did: every tab reopened at 0.5
  however the divider had been left. Stored as `<prefix>_split_ratio`, the same
  shape as the column widths; `ape_quarter_split_ratio` is the first field.
  `split_panel.py` logs a warning when a screen is given a prefix with no
  declared `AppSettings` field, because `AppSettings.save()` writes declared
  dataclass fields only and the failure is otherwise invisible until the next
  launch (P2).
- **Both panels are held at the minimum** (UPD-M1.3, "at any body width"). The
  four clamped the left panel only and gave the right whatever was left, so a
  body under `2 * MIN_PANEL_WIDTH` produced a right panel below the minimum and
  a body under `MIN_PANEL_WIDTH` a negative grid minsize. Tk accepts a negative
  minsize silently — measured in a probe, not assumed — which is why four
  copies carried it. `apply()` holds both sides and lets the body overflow.

Two claims in the spec were wrong and are corrected where they stood: the
splitter is written out **five** times, not four (`project_boards.py` holds a
fifth with its own minimum, its own default and, as it turns out, the clamp the
four were missing), and `MIN_PANEL_WIDTH` is declared as 420 in all four rather
than "420 in one and not declared in the others" — the 520 that reading came
from is the initial grid `minsize`, which the first resize overwrites.

## Files changed

- `src/getmoredone/screens/split_panel.py` (new, 185 lines)
- `src/getmoredone/screens/ape_assignment.py` (adopts it; +22 / −46)
- `src/getmoredone/app_settings.py` (`ape_quarter_split_ratio`)
- `tests/test_unified_panel_design.py` (8 new tests; one characterisation test
  now reads the constant from the module that owns it)
- `docs/spec_2026-11-07_unified_panel_design.md` (§1.1 and UPD-A2 corrected,
  UPD-A5 added, §10 status added)
- `docs/spec_coverage.md`, `docs/DOCUMENTATION_INDEX.md`, `CHANGELOG.md`,
  `NOTES.md`, `BACKLOG.md` (UPD-A5, UPD-A6)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_unified_panel_design.py tests/test_ape_period_consistency.py tests/test_settings_isolation.py tests/test_settings_save_refusal.py tests/test_column_resize.py tests/test_ci_contract.py tests/test_no_vacuous_tests.py tests/test_traceability_refs.py tests/test_release_docs.py -q`
- Result: PASS — 217 passed, 1 skipped (the CI-only display check in
  `test_ci_contract.py`).
- Mutation gate: 8 mutations, each the verbatim original, each run alone, every
  file restored and sha256-compared. 8 red.
- Probe, run under pytest: `grid_columnconfigure(minsize=-120)` is accepted by
  Tk and reads back as `-120`. This is why no test could have caught the
  missing right-hand clamp before, and why no guard against a *raise* was
  added — there is none to catch.

## Risks / Known gaps

- **UPD-M1.5 is `partial`, not `done`.** The AST guard is exact, but the count
  is not yet 0: UPD-M1 adopts one screen. The three VSP holdouts are named in
  `SPLITTER_HOLDOUTS` and adopt at UPD-M4; `project_boards.py` is UPD-A5 and
  stays. Recorded as UPD-A6.
- **Nothing has been seen on screen.** Every test builds its screen on a
  withdrawn root. UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are
  open. The persistence path in particular has been proved against the real
  screen but never against a real relaunch.
- The one behaviour change to the cramped-body layout is reachable only on a
  body under 848px, which was not measured against the app's own minimum window
  size.

## Next agent actions

- UPD-M2 — `screens/row_drag.py`, adopted by `ape_assignment.py`.
- Then UPD-M4, which rolls `split_panel`, `row_drag` and `chip_table` through
  `ape_period_view.py`, `annual_vision_segments.py` and `weekly_items.py`, and
  is the step that makes UPD-M1.5 read 0. Settle AWA-S5 and AWA-S6 before the
  first screen adopts `chip_table`.
- The APE Week Actions on-screen checklist (the end of
  `docs/spec_2026-11-07_ape_week_actions.md` §6) is still unwalked.
