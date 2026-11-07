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

Docs:
- `docs/spec_2026-11-07_ape_period_consistency.md` — spec, plan, departures,
  status report
- `docs/DOCUMENTATION_INDEX.md` — the spec doc listed
- `docs/USER_GUIDE.md` — APE assignment and APE Weekly behaviour
- `NOTES.md` — 2026-11-07 entry
- `docs/changes/2026-11-07-ape-period-consistency.md` — this note

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ape_period_consistency.py -q`
- Result: PASS (40 passed)

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_weekly_tactic_schema.py tests/test_vps_hub_crud.py tests/test_weekly_tactic_cascade.py tests/test_rename_safe_links.py tests/test_vps_integration.py -q`
- Result: PASS (160 passed)

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/ -m meta -q`
- Result: see §Risks — three failures, all in `tests/test_traceability_refs.py`,
  two of them pre-existing and from uncommitted `plan.py` work unrelated to this
  change.

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ci_contract.py tests/test_traceability_refs.py tests/test_no_vacuous_tests.py -q`
- Result: `test_ci_contract.py` PASS. The other two fail, naming only
  `plan.py`, `plan_blocks.py` and `test_plan_screen.py` — see §Risks.

- Mutation proofs: 12 mutations, 12 reds, each restored byte-identical.
  Table in `docs/spec_2026-11-07_ape_period_consistency.md` §5.4.

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

- **Pre-existing meta failures.** `tests/test_traceability_refs.py` reports
  `src/getmoredone/screens/plan.py` and `src/getmoredone/screens/plan_blocks.py`
  naming tests that do not exist (`test_pdm8_a_day_with_no_items_says_so`,
  `test_pdm16_the_depth_bars_line_up_with_the_bottom_of_the_title`). Those files
  are not touched by this change — the Plan-screen work is committed (`dbc1901`,
  `f799be3`, `b010cae`), so these failures are pre-existing on `main` and not
  this change's to fix.
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
  The log line carries the reason.

## Next agent actions

- Finalise the batch with `/csdp` — nothing here is committed yet.
- Decide whether the two pre-existing `test_traceability_refs.py` failures belong
  to the open Plan-screen batch or need their own fix.
