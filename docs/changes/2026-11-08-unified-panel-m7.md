# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: UPD-M7 — the one panel design is built, and has not been looked at

## Summary

Step 7, the last, of `docs/spec_2026-11-07_unified_panel_design.md` §4. No
screen behaviour changed in this batch: UPD-M7 is the meta test, the docs, and
the on-screen checklist the last two criteria need.

- **UPD-M7.1 is `done`.** `test_updm71_screens_construct_withdrawn` builds all
  five rewritten tabs and asserts that **no `Toplevel` was opened anywhere
  beneath the root** — an exact zero, walked to the bottom of each widget tree.
  A dialog at construction would be a modal thrown over whoever is using the
  machine, once per test that builds the screen.
  `test_updm71_no_test_here_needs_a_mapped_window` parses this file's own
  syntax tree and asserts exactly zero of its 81 tests take the
  `mapped_windows` fixture, so the 22 that `CLAUDE.md` documents and
  `test_ci_contract.py::test_the_documented_mapped_window_count_is_the_real_one`
  checks is the 22 it was before this plan.
- **UPD-M7.2 and UPD-M7.3 are `not done` and are deliberately not tests.** Both
  are about how six tabs read beside each other at a real window size with real
  data, and whether a width a user dragged is still there the next morning.
  They are now a ten-step checklist in the spec's new §11, for a person at the
  running app.

Two honest notes on the test:

- **Only the `Toplevel` count is failable.** The two assertions beside it — the
  root is withdrawn, the screen is unmapped — cannot be turned red by any
  change to a screen, because `conftest.py` withdraws every window at
  construction and re-withdraws after any `deiconify`. The docstring says so,
  and names `tests/test_tk_offscreen.py` as the guard on that patching rather
  than pretending this test is one (P24). An earlier draft asserted them as
  though they were the claim.
- **One mutation came back green and was not a finding.** It inserted a
  `CTkToplevel` into `self.left_list`, which is the `ChipTable`'s container —
  `build_header()` calls `clear()`, which destroys every child of it, so the
  window was gone before the assertion ran. Re-anchored to `left_frame`, three
  levels below the root and not cleared, and it kills the test. The first
  diagnosis of that green was wrong: it blamed `CTkScrollableFrame` for
  overriding `winfo_children`, which measurement showed it does not do.

## Files changed

- `tests/test_unified_panel_design.py` — the two UPD-M7.1 tests and the
  `_toplevels_under` walk (81 tests in the file); one UPD-M6 docstring
  corrected from "seventh copy" to "sixth copy"
- `docs/spec_2026-11-07_unified_panel_design.md` — the status line, §10's
  UPD-M7 block, and the new **§11** on-screen checklist
- `docs/spec_coverage.md` — the UPD-M7 table, replacing "`not done` — not
  started"
- `docs/DOCUMENTATION_INDEX.md` — the UPD spec's status line and a §11 bullet
- `CHANGELOG.md`, `NOTES.md`
- `docs/changes/2026-11-08-unified-panel-m7.md` — this note

`BACKLOG.md` is untouched: UPD-M7 filed nothing. UPD-A9, from UPD-M6, is still
the only open entry from this plan.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_unified_panel_design.py tests/test_ape_week_actions.py tests/test_no_vacuous_tests.py tests/test_traceability_refs.py tests/test_ci_contract.py tests/test_tk_offscreen.py tests/test_release_docs.py -q`
- Result: **FAIL — 1 failed, 261 passed, 4 skipped**, and the failure is not
  this batch's. `test_traceability_refs.py::test_every_referenced_test_name_exists`
  is red over nine `Tests:` references naming PD-M5 / PD-M14 / TG-M3 tests that
  do not exist: three are in `docs/spec_coverage.md` as committed by the
  concurrent plan-day batch in `440b1fc`, and six are in that batch's
  uncommitted `screens/plan.py` and `time_block_layout.py`. No UPD reference
  fails. The three skips in `test_tk_offscreen.py` and one in
  `test_ci_contract.py` are the documented env-var and CI-only skips.

- Mutation gate: 4 mutations, each the verbatim original, one at a time, every
  file restored and sha256-compared. **4 red, no finding** — one of them only
  after being re-anchored, see the Summary. Runner at `mutate_m7.py` in the
  session scratchpad.

## Risks / Known gaps

- **Not seen running — this is the batch's whole point and it is not closed.**
  UPD-M7.2 and UPD-M7.3 are open for UPD-M1 through UPD-M6. UPD-M4 changed the
  renderer, the splitter and the row drag of three tabs in one step and none
  has been looked at. The checklist is the spec's §11.
- The AWA batch's own nine-step on-screen checklist, at the end of
  `docs/spec_2026-11-07_ape_week_actions.md` §6, has also not been walked.
- **Three shared documents hold two batches' uncommitted hunks.**
  `docs/DOCUMENTATION_INDEX.md`, `CHANGELOG.md` and `NOTES.md` each carry the
  concurrent calendar-export batch's edits as well as this batch's. Per
  `CLAUDE.md`'s "Never stage a file to protect your own committed work", the
  commit here stages HEAD's blob plus only this batch's hunks, built and
  verified against HEAD rather than from the working file, and leaves the
  working tree as it was found.
- `CLAUDE.md:53` says the entry point is `getmoredone.app.daVIPAApp`; the class
  is `GetMoreDoneApp` (`src/getmoredone/app.py:22`). Flagged, not fixed — it is
  not this plan's file.

## Next agent actions

- **Walk §11's ten steps in the running app** and record the result against
  UPD-M7.2 and UPD-M7.3. Quit `/Applications/daVIPA.app` first: a source launch
  exits silently while the packaged app holds the database lock.
- `/csdp` is owed over the unpushed range before anything is pushed. No sweep
  has run for UPD-M5, UPD-M6 or UPD-M7, and the range now carries four batches.
