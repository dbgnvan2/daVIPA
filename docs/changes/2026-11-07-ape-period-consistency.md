# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: ape-period-consistency

## Summary

Two reported faults in the VPS Plan tab, which turned out to be one fault seen
from both ends: nothing in the stack owned the rule that month 11 belongs to
quarter 4.

1. **An APE Month record did not appear in APE Weekly.** Reproduced from the
   demo database (`~/Library/Application Support/GetMoreDone-Demo/`), whose one
   APE row read `q1 = 1, q3 = 1, m11 = 1`. APE Weekly derived the quarter from
   the selected week (a November week gives Q4) and asked for
   `q4 = 1 AND m11 = 1`, so the row matched nothing, every November week, with
   nothing on screen to say why.
2. **APE Month allowed Q1 with M11.** Its Quarter picker opened on the literal
   `"1"` while the Month picker opened on today's month, and
   `assign_ape_to_month` validated each argument's range but never their
   relationship. That is how fault 1's row was written.

What changed:

- `date_utils` now holds the one quarter↔month mapping — `QUARTER_OF_MONTH`,
  `MONTHS_OF_QUARTER`, `quarter_of_month()`, `months_of_quarter()`,
  `current_quarter()`. It replaced four copies: a dict in `weekly_tactic`, a
  second dict inside `VPSManager._clear_quarter_month_flags`,
  `((month - 1) // 3) + 1` in the APE Weekly screen, and the same arithmetic
  inside `date_utils.first_of_next_quarter`.
- `assign_ape_to_month` refuses a pair that cannot both be true, before writing
  anything, and logs the refusal.
- APE Month opens on the current quarter and month, and its Month picker offers
  only the selected quarter's three months; changing the quarter pulls the month
  into it. APE Quarter had the identical hard-coded `"1"` (flagged as APC-M6,
  approved, fixed here).
- `get_annual_plan_elements_for_month(year, month)` replaces
  `get_annual_plan_elements_for_period(year, quarter, month)`. Both APE screens
  use it; the old method had no other caller and is gone. The APE Weekly
  screen's derived quarter had no reader left, so `_selected_week_context` now
  returns `(week_start, year, month)`.
- `VPSSchema._repair_orphan_month_flags` sets the quarter flag every stored
  month flag implies. Additive and idempotent — a quarter flag with no month in
  it is a real state, so nothing is cleared.
- APE Month reports what Save did, for the button and the drop target alike. It
  previously had no status surface at all.

## Files changed

Source:
- `src/getmoredone/date_utils.py` — the shared mapping and helpers;
  `first_of_next_quarter` re-pointed at them
- `src/getmoredone/weekly_tactic.py` — `QUARTER_OF_MONTH` re-exported, not redefined
- `src/getmoredone/vps_manager.py` — APC-M2 guard, `get_annual_plan_elements_for_month`
  replacing `..._for_period`, `_clear_quarter_month_flags` re-pointed
- `src/getmoredone/vps_schema.py` — `_repair_orphan_month_flags`
- `src/getmoredone/screens/ape_period_view.py` — `default_period`,
  `_sync_month_choices`, `on_quarter_changed`, status label,
  `_describe_month_assignment`, pair check in `_parse_period`
- `src/getmoredone/screens/ape_assignment.py` — quarter default
- `src/getmoredone/screens/weekly_items.py` — month-only lookup, no derived quarter

Tests:
- `tests/test_ape_period_consistency.py` — new, 41 tests (40 logic/wiring plus
  one that builds the real `APEPeriodViewScreen` and reads the real combo)
- `tests/test_weekly_tactic_schema.py` — three `_selected_week_context` stubs
  moved from a 4-tuple to a 3-tuple (reason (b): the behaviour changed
  intentionally; they assert nothing about the quarter)

From the sweep (`de2067f` source, `a1bc1d3` tests):
- `src/getmoredone/vps_manager.py` — APC-M4.4, the month guard that refuses the
  junk a caller can reach it with, and a column name built from `int(month)`
- `src/getmoredone/vps_schema.py` — APC-M5.4, the repair returns and logs the
  rows it changed and stamps `updated_at`
- `src/getmoredone/screens/ape_period_view.py` — APC-M2.4, `_assign_one`; the
  corrected class claim in `_describe_month_assignment`
- `src/getmoredone/screens/ape_assignment.py` — APC-M6.2, `status_label`,
  `_assign_one`, `_describe_quarter_assignment`, both write paths reporting
- `tests/test_ape_period_consistency.py` — seven more tests (48 total) and
  `_bind`, which binds a real method onto a `SimpleNamespace` stub

From the re-sweep of those fix commits (spec §5.11):
- `src/getmoredone/screens/ape_period_view.py` — APC-M2.5 `_ids_in_month` and
  the four-state `_describe_month_assignment`; APC-M2.6 `_remove_one` and a
  three-outcome report in `delete_month_item`
- `src/getmoredone/screens/ape_assignment.py` — the same two as APC-M6.3 and
  APC-M6.4 (`_ids_in_quarter`, `_remove_one`)
- `src/getmoredone/vps_schema.py` — APC-M5.5 recorded in the docstring; the
  code was already right, the test was missing
- `tests/test_ape_period_consistency.py` — five more tests (53 total), the
  `_break_segment_link` helper, both drag tests now asserting the manager call,
  and `test_apcm44_month_lookup_guard_is_type_safe` renamed to
  `..._refuses_junk_and_normalises_a_float`

Docs:
- `docs/spec_2026-11-07_ape_period_consistency.md` — spec, plan, departures,
  status report, and §5.8–§5.10 for the sweep
- `BACKLOG.md` — the two low findings and the two adjacent issues
- `docs/DOCUMENTATION_INDEX.md` — the spec doc listed
- `docs/USER_GUIDE.md` — APE assignment and APE Weekly behaviour
- `NOTES.md` — 2026-11-07 entry
- `docs/changes/2026-11-07-ape-period-consistency.md` — this note

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ape_period_consistency.py -q`
- Result: PASS (53 passed, after the re-sweep's five new tests)

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ape_period_consistency.py tests/test_traceability_refs.py tests/test_no_vacuous_tests.py tests/test_ci_contract.py tests/test_weekly_tactic_schema.py tests/test_weekly_tactic_dedupe.py tests/test_vps_hub_crud.py tests/test_vps_integration.py tests/test_rename_safe_links.py -q`
- Result: PASS (306 passed, 1 skipped — the skip is `test_ci_contract.py:371`,
  meaningful only on CI)

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_weekly_tactic_schema.py tests/test_vps_hub_crud.py tests/test_weekly_tactic_cascade.py tests/test_rename_safe_links.py tests/test_vps_integration.py -q`
- Result: PASS (160 passed)

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ape_period_consistency.py tests/test_ci_contract.py tests/test_traceability_refs.py tests/test_no_vacuous_tests.py tests/test_weekly_tactic_schema.py tests/test_vps_hub_crud.py tests/test_vps_integration.py -q`
- Result: PASS (203 passed, 1 skipped — the skip is `test_ci_contract.py:371`,
  meaningful only on CI)

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_plan_screen.py tests/test_time_block_colors.py tests/test_tk_offscreen.py tests/test_plan_settings.py tests/test_time_block_crud.py -q`
- Result: PASS (the PD-\* batch's files; all skips are the mapped-window opt-out)

- Mutation proofs: 25 mutations, 25 reds, each restored byte-identical. Twelve
  for the original criteria (spec §5.4), eight for the sweep fixes (§5.9) and
  five for the re-sweep fixes (§5.11).

- On screen in the running app, 2026-11-07 10:51-10:53, against the **real**
  demo database (table in the spec, §5.6): APE Month opened on Q4 / M11; its
  Month dropdown listed exactly 10, 11, 12 under Q4 and exactly 1, 2, 3 under
  Q1; Q4 → Q1 moved the month to 1 and Q1 → Q4 moved it to 10, both panel
  headers following; and APE Weekly for week 2026-11-02 showed the reported
  record under `Month-assigned APEs for 2026-11`.

- Against the reported data, on **copies** in a scratch directory
  (§5.5 of the spec): the demo database's orphan row goes `q4=0` → `q4=1` with
  `q1` and `q3` intact, and `get_annual_plan_elements_for_month(2026, 11)` then
  returns it. On a copy of the installed app's database — 17 APE rows, all
  already consistent — the migration changed 0 rows.

## Risks / Known gaps

- **The three meta failures are fixed.** `tests/test_traceability_refs.py` was
  red on `main` for two `Tests:` refs in `plan.py` and `plan_blocks.py` naming
  tests that had been renamed, and `tests/test_no_vacuous_tests.py` was red on
  `test_pdm106_a_flush_on_a_screen_that_is_gone_does_not_raise`, which asserted
  nothing. Both belonged to the unpushed PD-\* batch rather than to this change;
  fixed in `0f85168` and `c31fce7` because they were in the sweep's range.
  `test_ci_contract.py`, `test_traceability_refs.py` and
  `test_no_vacuous_tests.py` are all green.
- **The Save status message was not seen on screen.**
  `_describe_month_assignment` is covered by `test_apcm23_*`, but its wording in
  the real header was not checked, because showing it means writing an
  assignment to the user's live demo data.
- **`tests/test_ci_contract.py::test_rm3d_every_test_file_is_importable_on_its_own`
  initially failed** on the new file: it sorts second, and that probe imports
  every test file with the repo root stripped from `sys.path`. Fixed by giving
  the file the same self-contained path bootstrap `test_after_tracker.py`
  carries, for the same documented reason.
- **The user's databases are untouched by this change.** Verification ran on
  copies in a scratch directory. The repair runs against each real database when
  the app next opens it. Nothing was hand-edited.
- **`assign_ape_to_month` returns a bare boolean** and refuses for more than one
  reason, so the Save message counts what did not happen rather than saying why.
  The log line carries the reason. The re-sweep found the sharper half of this:
  the boolean is also returned *after* a write, so the status line is now read
  off the row rather than off the return code (APC-M2.5, spec §5.11).
- **The two removes report, the cascade's call site does not.**
  `weekly_tactic.py:294` is the seventh write path in the class and is in
  `BACKLOG.md` as an adjacent issue, not fixed: it has its own `CascadeReport`.

## The sweep (2026-11-07)

Three passes over the unpushed range `7aa601d...HEAD`, which carried this batch
and the nine unpushed plan-screen (PD-\*) commits. Full account in the spec,
§5.8–§5.10.

| Pass | Lens | Result |
|---|---|---|
| `learning-qa` | the failure-pattern catalogue; P2, P4, P5, P6, P8 applicable | 4 findings (1 medium-high, 2 medium, 1 low-medium), 2 adjacent notes, no high |
| `/code-review` (high) | correctness over the 1,135-line source-only diff | 6 findings — the same four, plus two lows |
| `/security-review` | injection, secrets, path traversal, deserialisation, data exposure | no findings at the ≥8 confidence bar |

Fixed here, with tests and mutation proofs, as APC-M2.4, APC-M4.4, APC-M5.4 and
APC-M6.2 (`de2067f` source, `a1bc1d3` tests) — graded one medium-high, two
medium and one low-medium; the low-medium (APC-M4.4) was fixed in-loop against
the budget's own rule, recorded as an exception taken rather than relabelled:

- `add_selected` had no `try` around the per-APE call, and
  `assign_ape_to_month` raises when an APE's segment resolves to nothing: the
  raise left the earlier APEs written and the previous press's success message
  on screen.
- The sibling APE Quarter screen was silent on the same axis, on both write
  paths, with no status surface at all — the "fixed as a class" shape P5
  describes, with the denominator counted on one screen.
- `_repair_orphan_month_flags` changed the user's real rows on every open and
  reported nothing (P2).
- `get_annual_plan_elements_for_month`'s range comparison raised on a string
  and passed a float, and the month is interpolated as a column name.

Recorded in `BACKLOG.md` instead of fixed, per the repo's sweep budget: two low
findings (`quarter_of_month` truncates a float; `_require_block_day`'s modal
pumps the event queue from inside a drop's `after_idle`, PLAUSIBLE only) and
two adjacent issues (the Plan screen's failure arm is on 3 of 8 write paths;
`weekly_items` files a straddling week under its start date's month).

**The security pass caught an error in one of the fixes.** The first version of
APC-M4.4 guarded with `month not in QUARTER_OF_MONTH` alone and claimed that
rejected floats; `11.0 in {11: ...}` is `True`, because a dict is keyed by hash
and equality. The fix needs the membership test *and* `int(month)`, and the
test asserts the float case rather than assuming the guard covers it.

## The re-sweep of the fix commits (2026-11-07)

`c31fce7...HEAD` — the three fix commits, 1,080 lines over 10 files — went back
through `learning-qa`, per the budget's rule that every in-loop fix is in scope
for the next pass. Four findings, one of them a defect in the sweep's own fix:

| # | Severity | Finding | Outcome |
|---|---|---|---|
| F1 | medium-high | The status line was computed from `_assign_one`'s boolean, and the manager writes before it can fail — so "Assigned 0 APE(s) to M11" appeared beside a panel showing the row | fixed, APC-M2.5 / M6.3 |
| F2 | medium | "Four write paths across two screens" was wrong; the class is seven, including both removes and the cascade's call site | removes fixed (APC-M2.6 / M6.4); cascade flagged in `BACKLOG.md` |
| F3 | medium | The repair's `logger.info` had no test, and the spec's stated reason for that was contradicted by an existing test in this repo | fixed, APC-M5.5 |
| F4 | medium-low | `_assign_one`'s broad `except Exception` swallowed stub assertion errors, so four published assertions could not fail | fixed: both drag tests record and assert the manager call |

The published APC-M2.4 tests could not have caught F1 — their stubs raise
instead of writing. The new tests use the real manager on a real database in
the one state that half-writes, and assert both that the call raised and that
the row is in the month.

Two further lows went to `BACKLOG.md`: the guard still raises on an unhashable
month and accepts `True`, and a transient `sqlite3.OperationalError` reads as a
permanent refusal.

## The program run on the second round (2026-11-07 13:05-13:08)

The real app, pointed by `GETMOREDONE_DB` at a throwaway copy of the demo
database with that copy's `q4` flag cleared first. Full table in the spec,
§5.13.

- The migration repaired the copy's row on open and the log line landed:
  `INFO [vps_schema] APC-M5 backfilled 1 implied quarter flag(s):
  [('ape-1e44cdd5', 4)]` at 13:05:20,435.
- APE Month opened on 2026 / Q4 / M11, APE Quarter on Q4.
- The status lines were read on screen: "Check one or more APEs on the left
  first.", "Assigned 1 APE(s) to M11." and, on the sibling screen,
  "Assigned 1 APE(s) to Q4." That closes the "not seen on screen" gap for both
  screens on the Save path.
- Not covered: the Remove wording (the Delete button is past the right panel's
  visible width at this window size) and the "partly assigned" wording (it
  needs a corrupt lineage the copy does not have). Both are covered by tests.
- Neither real database was written: afterwards their newest `updated_at`
  values were `2026-11-07T09:00:49` (demo) and `2026-10-18T15:39:43`
  (installed app), both older than this run.

## Next agent actions

- Start the APE Week Assignment work (`docs/spec_2026-11-07_ape_week_actions.md`,
  approved, not built) from a clean `main`.
- Open decision carried into that batch: AWA-A1 — whether
  `weekly_items.py:442` should write `weekly_tactic_id` as well as `parent_id`.
  Recommended, not approved.
