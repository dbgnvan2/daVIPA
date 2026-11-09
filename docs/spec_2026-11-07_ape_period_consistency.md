# Spec + implementation plan — APE quarter/month consistency

**Date:** 2026-11-07
**Status:** implemented 2026-11-07. Section 5 records where the build departed from this plan.
**Area:** VPS Plan → APE Month Assignment, APE Weekly

---

## 1. The two reported faults

### 1.1 An APE Month record does not appear in APE Weekly

Reproduced from the live demo database
(`~/Library/Application Support/GetMoreDone-Demo/getmoredone.db`):

```
2026  My New Vision Segment|new Subsegment|new   q1=1 q3=1   m11=1
```

`WeeklyItemsScreen` derives the period from the selected week start
(`src/getmoredone/screens/weekly_items.py:229`):

```python
quarter = ((month - 1) // 3) + 1      # a November week -> quarter 4
```

and then asks for APEs with **both** flags set
(`src/getmoredone/vps_manager.py:398`):

```sql
WHERE year = ? AND q4 = 1 AND m11 = 1
```

The row has `m11 = 1` but `q4 = 0`, so the left panel comes back empty. The
month flag is the real month assignment; requiring the derived quarter flag as
well is redundant when the data is consistent and actively hides the row when
it is not.

### 1.2 APE Month lets Q1 and M11 coexist

`src/getmoredone/screens/ape_period_view.py:29` hard-codes the quarter picker's
default:

```python
self.quarter_var = ctk.StringVar(value="1")        # always Q1
self.month_var = ctk.StringVar(value=str(datetime.now().month))   # current month
```

The month combo offers all twelve months regardless of the selected quarter, and
`assign_ape_to_month` (`src/getmoredone/vps_manager.py:462`) validates each
argument's *range* but never their *relationship*. So Save with Q1 + M11 writes
`q1 = 1, m11 = 1` — which is how 1.1's row was created.

The two faults are one fault: nothing in the stack owns the rule that month 11
belongs to quarter 4.

### 1.3 Three copies of that rule already exist

| Location | Form |
|---|---|
| `src/getmoredone/weekly_tactic.py:35` | `QUARTER_OF_MONTH` dict |
| `src/getmoredone/vps_manager.py:873` | quarter→months dict inside `_clear_quarter_month_flags` |
| `src/getmoredone/screens/weekly_items.py:229` | `((month - 1) // 3) + 1` |

All three agree on calendar quarters today. Adding a fourth copy to fix the
picker is the wrong move.

---

## 2. Acceptance criteria → tests

Every criterion names the file it lands in and the automated test that verifies
it. Test file: `tests/test_ape_period_consistency.py` unless stated.

### APC-M1 — one quarter↔month mapping

| ID | Criterion | Test |
|---|---|---|
| APC-M1.1 | `date_utils.quarter_of_month(month)` and `date_utils.months_of_quarter(quarter)` exist and cover 1–12 / 1–4 | `test_apcm11_quarter_of_month_covers_every_month` |
| APC-M1.2 | `weekly_tactic.QUARTER_OF_MONTH` is derived from the new helper, not a second literal | `test_apcm12_weekly_tactic_mapping_is_not_a_second_literal` (AST walk — no dict literal of 12 int keys in the module) |
| APC-M1.3 | `_clear_quarter_month_flags` uses `months_of_quarter` | `test_apcm13_clear_quarter_month_flags_uses_shared_mapping` (behavioural: unassigning Q4 clears m10–m12 only) |
| APC-M1.4 | `weekly_items._selected_week_context` carries no derived quarter at all (see §5.1) | `test_apcm14_week_context_carries_no_derived_quarter` |

### APC-M2 — an inconsistent pair is refused, loudly

| ID | Criterion | Test |
|---|---|---|
| APC-M2.1 | `assign_ape_to_month(ape, 1, 11)` returns `False` and writes **nothing** (`q1` and `m11` unchanged) | `test_apcm21_mismatched_quarter_and_month_is_refused_and_writes_nothing` |
| APC-M2.2 | A consistent pair still succeeds — `assign_ape_to_month(ape, 4, 11)` is `True` | `test_apcm22_matching_quarter_and_month_still_assigns` |
| APC-M2.3 | The Month screen's Save reports a refusal instead of silently skipping it (P2 — surface, never drop) | `test_apcm23_save_reports_refused_assignments` |
| APC-M2.4 | A raising assignment is counted as refused, not allowed out of the loop: the APEs that did not raise are still written, the redraw still happens, and the line says how many | `test_apcm24_a_raising_assignment_is_counted_not_escaped` |
| APC-M2.5 | The Save line is computed from the rows the panel is drawn from, not from the call's boolean, and names all four states: assigned, partly assigned (the call failed and the month holds the row anyway), could not be assigned, and reported assigned but not in the month | `test_apcm25_a_half_written_assignment_is_reported_as_partial`, `test_apcm23_save_reports_refused_assignments` |
| APC-M2.6 | The Month screen's **Remove** reports against the row too, in all three outcomes: removed, still in the month, and out of the month with the call reporting a problem | `test_apcm26_a_failed_remove_is_reported` |

### APC-M3 — the pickers cannot produce an invalid pair

| ID | Criterion | Test |
|---|---|---|
| APC-M3.1 | Quarter defaults to the current calendar quarter | `test_apcm31_quarter_defaults_to_current_quarter` |
| APC-M3.2 | The month combo offers only the selected quarter's three months | `test_apcm32_month_combo_offers_only_that_quarters_months` |
| APC-M3.3 | Changing the quarter moves the month into range (keeps it when already in range, else the quarter's first month) | `test_apcm33_changing_quarter_moves_month_into_range`, `test_apcm33_every_quarter_leaves_the_month_in_range` |
| APC-M3.4 | Month defaults to the current month, which APC-M3.1 keeps in range | `test_apcm34_default_month_is_always_inside_the_default_quarter` |

APC-M3.1–3.4 build no window: the defaults moved into
`APEPeriodViewScreen.default_period(today)` and the month list into
`_sync_month_choices`, both reachable with a `SimpleNamespace` stub. So the
`tests/test_ci_contract.py` mapped-window count is unchanged.

### APC-M4 — a month-assigned APE shows in that month's weeks

| ID | Criterion | Test |
|---|---|---|
| APC-M4.1 | `get_annual_plan_elements_for_month(year, month)` exists and matches on the month flag alone | `test_apcm41_month_lookup_matches_on_month_flag_alone` |
| APC-M4.2 | A row with `m11 = 1, q4 = 0` is returned for November — the already-stored orphan appears | `test_apcm42_orphan_month_flag_still_appears_in_november` |
| APC-M4.3 | `WeeklyItemsScreen` left panel and the Month screen's right panel both use the month lookup; `get_annual_plan_elements_for_period` is removed (it has no other caller) | `test_apcm43_screens_use_month_lookup` |
| APC-M4.4 | A non-integer month returns `[]` rather than raising: `"11"`, `None`, `(11,)` are refused, and `11.0` — which the membership test alone passes, since `11.0 in {11: ...}` is `True` — reaches SQLite as `m11` because the column name is built from `int(month)` | `test_apcm44_month_lookup_guard_is_type_safe` |

### APC-M5 — existing orphan flags repaired

| ID | Criterion | Test |
|---|---|---|
| APC-M5.1 | Opening a database sets `q{N} = 1` for any APE with a month flag inside quarter N; never clears a quarter flag | `test_apcm51_migration_backfills_the_implied_quarter_flag` |
| APC-M5.2 | Dirty-state (P8): a file DB written with `q1=1, q3=1, m11=1`, then reopened, reads `q1=1, q3=1, q4=1, m11=1` | `test_apcm52_dirty_state_orphan_quarter_flag_is_repaired_on_reopen` |
| APC-M5.3 | Idempotent — a second open changes no row (`updated_at` untouched for already-consistent rows) | `test_apcm53_migration_is_idempotent` |
| APC-M5.4 | The repair returns the `(ape_id, quarter)` list it changed, stamps `updated_at` on those rows, and logs the list at `info` when non-empty; a second run returns `[]` (P2 — an automatic data change that says nothing is indistinguishable from one that did nothing) | `test_apcm54_the_repair_reports_every_row_it_changed` |
| APC-M5.5 | That `info` line is asserted from a handler attached to the logger, naming the repaired row, and a no-op run logs nothing. The only caller discards the return value, so in the running app the log line is the whole trace | `test_apcm55_the_repair_log_reaches_a_handler` |

Home: `VPSSchema._extend_annual_plan_elements`, which calls
`_repair_orphan_month_flags` alongside the flags it is repairing, in the same
idempotent-`UPDATE` style as the existing `action_items` group repair in
`database.py`. Named by function rather than by line: the first version of this
paragraph said `vps_schema.py:777`, and the sweep's own fix moved the function
past it. A line number in a document is a claim like any other (P6), and this
one went stale inside the same batch that wrote it.

### APC-M6 — adjacent issue found, **not** silently fixed

`src/getmoredone/screens/ape_assignment.py:29` (APE **Quarter** Assignment) has
the identical defect: `self.quarter_var = ctk.StringVar(value="1")`. Per the
project's rule 10 this is flagged rather than swept in.

**Approved and fixed** in this change — one line plus
`test_apcm61_quarter_screen_defaults_to_current_quarter`. It is the same defect,
and leaving it means the two APE screens disagree about what quarter you are in.

| ID | Criterion | Test |
|---|---|---|
| APC-M6.1 | APE Quarter's Quarter picker opens on the current calendar quarter | `test_apcm61_quarter_screen_defaults_to_current_quarter` |
| APC-M6.2 | APE Quarter reports what Save did on **both** its write paths, says so when nothing is checked, and counts a raise as refused rather than letting it escape | `test_apcm62_quarter_save_reports_refused_assignments`, `test_apcm62_quarter_save_with_nothing_checked_says_so`, `test_apcm62_a_raising_quarter_assignment_is_counted_not_escaped`, `test_apcm62_quarter_drag_path_reaches_the_same_reporting` |
| APC-M6.3 | APE Quarter's Save line is computed from the rows, not the boolean, with the same four states as APC-M2.5 | `test_apcm63_a_half_written_quarter_assignment_is_reported_as_partial` |
| APC-M6.4 | APE Quarter's **Remove** reports against the row, in the same three outcomes as APC-M2.6 | `test_apcm64_a_failed_quarter_remove_is_reported` |

APC-M6.2 came out of the sweep, not the plan. `_describe_month_assignment`'s
docstring claimed the reporting class was covered because both of the *Month*
screen's paths reported through it. The class is four paths across two screens.
APE Quarter — edited in this same change for APC-M6.1 — discarded
`assign_ape_to_quarter`'s boolean on both of its paths and had no status
surface at all, so a rejected APE simply did not appear in the right-hand
panel, which is what a click on the wrong row looks like. This is the "fixed as
a class" shape P5 describes, with the denominator counted on one screen. The
month docstring's claim is corrected along with the code.

---

## 3. Implementation order

1. APC-M1 — the shared mapping, and the three existing copies re-pointed at it.
   Nothing else can be written correctly before this.
2. APC-M5 — the repair migration. Runs before the UI work so the dev database
   is consistent while the screens are tested by hand.
3. APC-M2 — the manager guard (depends on APC-M1).
4. APC-M4 — the month lookup and both screens' use of it.
5. APC-M3 — the Month screen pickers (depends on APC-M1).
6. APC-M6 — the Quarter screen default, if approved.
7. Tests, written highest-risk first per the fix→test map below.
8. Docs: this file added to `docs/DOCUMENTATION_INDEX.md`, `docs/USER_GUIDE.md`
   APE Weekly / APE Month sections, `NOTES.md`, and the handoff note at
   `docs/unused-docs/changes/2026-11-07-ape-period-consistency.md`.

### Fix→test map (highest impact first)

| Fix | Test written first? | Why |
|---|---|---|
| APC-M5 migration | **yes** | Touches every existing row in the user's real database. Dirty-state test is the whole safety net. |
| APC-M2 guard | yes | Changes a manager return value four existing test files already call. |
| APC-M4 lookup | yes | Removes a public method and changes what two screens display. |
| APC-M3 pickers | after | UI-only; a wrong default is visible immediately. |
| APC-M1 mapping | after | Pure refactor, covered by M1.3/M1.4's behavioural checks. |

### Not code-testable

None. Every criterion above is either a behavioural assertion or an AST check.

---

## 4. Risks

- **Removing `get_annual_plan_elements_for_period`.** Grep over `src/` and
  `tests/` shows exactly two callers, both screens listed in APC-M4.3. If a meta
  test asserts a manager method inventory, it is updated in the same commit.
- **The guard changes a return value.** All four existing test files call
  `assign_ape_to_month` with consistent pairs (`(1,2)`, `(3,8)`, `(2,5)`,
  `(4,11)`, `(2,6)`, `(3,9)`), so none should flip to `False`. Verified by
  running those files, not assumed.
- **Constraining the month combo** means an orphan row cannot be viewed from the
  quarter it was wrongly filed under. APC-M5 removes the need to.

---

## 5. Departures from the plan, and the status report

### 5.1 APC-M1.4 — the derivation was removed, not re-pointed

The plan said `weekly_items._selected_week_context` would use the shared
`quarter_of_month`. Once APC-M4.1 landed, nothing on that screen read the
quarter: `load_selected_week` had used it only for the left-panel lookup, and
the two other callers already unpacked it as `_quarter`. A re-pointed
derivation would have been dead code, so `_selected_week_context` now returns
`(week_start, year, month)`.

Consequence: three `_selected_week_context` stubs in
`tests/test_weekly_tactic_schema.py` returned a 4-tuple and were changed to a
3-tuple. Per the project's test rules the reason is **(b) the behaviour changed
intentionally** — the stubs describe a context shape that no longer has a
quarter in it. They assert nothing about the quarter, so no assertion was
weakened.

### 5.2 APC-M3.1 / APC-M3.4 — the defaults moved into a testable helper

Asserting a `ctk.StringVar`'s opening value needs a Tk root. Rather than build
a window, or assert against source text, the opening period moved into
`APEPeriodViewScreen.default_period(today)`. It takes the date instead of
reading the clock, so the pairing is checked for all twelve months rather than
only the one the suite happens to run in.

### 5.3 Status report

| ID | Status | Evidence |
|---|---|---|
| APC-M1.1 | done | `src/getmoredone/date_utils.py` — `quarter_of_month`, `months_of_quarter`, `current_quarter`, `QUARTER_OF_MONTH`, `MONTHS_OF_QUARTER`; `test_apcm11_quarter_of_month_covers_every_month`, `test_apcm11_months_of_quarter_covers_every_quarter` |
| APC-M1.2 | done | `src/getmoredone/weekly_tactic.py:35` re-exports; `test_apcm12_weekly_tactic_mapping_is_not_a_second_literal` |
| APC-M1.3 | done | `VPSManager._clear_quarter_month_flags`; `test_apcm12_vps_manager_holds_no_quarter_months_literal`, `test_apcm13_clear_quarter_month_flags_uses_shared_mapping` |
| APC-M1.4 | done, changed — see §5.1 | `WeeklyItemsScreen._selected_week_context`; `test_apcm14_week_context_carries_no_derived_quarter` |
| APC-M2.1 | done | `VPSManager.assign_ape_to_month`; `test_apcm21_mismatched_quarter_and_month_is_refused_and_writes_nothing`, `test_apcm21_every_mismatched_pair_is_refused` |
| APC-M2.2 | done | `test_apcm22_matching_quarter_and_month_still_assigns` |
| APC-M2.3 | done | `APEPeriodViewScreen._describe_month_assignment`; `test_apcm23_save_reports_refused_assignments`, `test_apcm23_save_button_reaches_the_reporting`, `test_apcm23_drag_path_reaches_the_same_reporting` |
| APC-M2.4 | done, from the sweep — see §5.8 | `APEPeriodViewScreen._assign_one`; `test_apcm24_a_raising_assignment_is_counted_not_escaped` |
| APC-M2.5 | done, from the re-sweep — see §5.11 | `APEPeriodViewScreen._ids_in_month`, `_describe_month_assignment`; `test_apcm25_a_half_written_assignment_is_reported_as_partial` |
| APC-M2.6 | done, from the re-sweep — see §5.11 | `APEPeriodViewScreen._remove_one`, `delete_month_item`; `test_apcm26_a_failed_remove_is_reported` |
| APC-M3.1 | done | `APEPeriodViewScreen.default_period`; `test_apcm31_quarter_defaults_to_current_quarter` |
| APC-M3.2 | done | `APEPeriodViewScreen._sync_month_choices`; `test_apcm32_month_combo_offers_only_that_quarters_months` |
| APC-M3.3 | done | `test_apcm33_changing_quarter_moves_month_into_range`, `test_apcm33_every_quarter_leaves_the_month_in_range` |
| APC-M3.4 | done | `test_apcm34_default_month_is_always_inside_the_default_quarter` (all 12 months) |
| APC-M4.1 | done | `VPSManager.get_annual_plan_elements_for_month`; `test_apcm41_month_lookup_matches_on_month_flag_alone` |
| APC-M4.2 | done | `test_apcm42_orphan_month_flag_still_appears_in_november` |
| APC-M4.3 | done | `test_apcm43_screens_use_month_lookup`, `test_apcm43_weekly_screen_left_panel_asks_by_month_only` |
| APC-M4.4 | done, from the sweep — see §5.8 | `VPSManager.get_annual_plan_elements_for_month`; `test_apcm44_month_lookup_guard_is_type_safe` |
| APC-M5.1 | done | `VPSSchema._repair_orphan_month_flags`; `test_apcm51_migration_backfills_the_implied_quarter_flag`, `test_apcm5_every_stored_month_flag_implies_its_quarter` |
| APC-M5.2 | done | `test_apcm52_dirty_state_orphan_quarter_flag_is_repaired_on_reopen` |
| APC-M5.3 | done | `test_apcm53_migration_is_idempotent` |
| APC-M5.4 | done, from the sweep — see §5.8 | `VPSSchema._repair_orphan_month_flags`; `test_apcm54_the_repair_reports_every_row_it_changed` |
| APC-M5.5 | done, from the re-sweep — see §5.11 | `VPSSchema._repair_orphan_month_flags`; `test_apcm55_the_repair_log_reaches_a_handler` |
| APC-M6.1 | done | `src/getmoredone/screens/ape_assignment.py`; `test_apcm61_quarter_screen_defaults_to_current_quarter` |
| APC-M6.2 | done, from the sweep — see §5.8 | `APEAssignmentScreen._assign_one`, `_describe_quarter_assignment`, `status_label`; `test_apcm62_quarter_save_reports_refused_assignments`, `test_apcm62_quarter_save_with_nothing_checked_says_so`, `test_apcm62_a_raising_quarter_assignment_is_counted_not_escaped`, `test_apcm62_quarter_drag_path_reaches_the_same_reporting` |
| APC-M6.3 | done, from the re-sweep — see §5.11 | `APEAssignmentScreen._ids_in_quarter`, `_describe_quarter_assignment`; `test_apcm63_a_half_written_quarter_assignment_is_reported_as_partial` |
| APC-M6.4 | done, from the re-sweep — see §5.11 | `APEAssignmentScreen._remove_one`, `delete_quarter_item`; `test_apcm64_a_failed_quarter_remove_is_reported` |

### 5.4 Mutation proofs

Every behavioural claim was proved by deleting or inverting the line the test
names, running that test, confirming red, and restoring the file from its
original bytes (verified byte-identical). Twelve mutations, twelve reds:

| Mutation | Tests that caught it |
|---|---|
| APC-M2.1 guard removed | 5 failed |
| APC-M4.1 quarter clause restored to the lookup | 1 failed |
| APC-M5.1 repair call removed | 1 failed |
| APC-M5.1 repair clears other quarters too | 1 failed |
| APC-M3.1 default quarter back to the literal `1` | 10 failed |
| APC-M3.2 month combo offers all twelve again | 1 failed |
| APC-M3.3 out-of-range month left alone | 2 failed |
| APC-M2.3 Save stops reporting | 1 failed |
| APC-M1.4 derived quarter put back in the week context | 1 failed |
| APC-M1.2 a second mapping literal added to `weekly_tactic` | 1 failed |
| APC-M4.3 weekly screen asks by quarter and month again | 1 failed |
| `_sync_month_choices()` call removed from `create_ui` | 1 failed (the real-widget test) |

### 5.5 Verified against the reported data

On a **copy** of `~/Library/Application Support/GetMoreDone-Demo/getmoredone.db`
in a scratch directory:

```
BEFORE: key_field='My New Vision Segment|new Subsegment|new Category'  q1=1 q2=0 q3=1 q4=0 m11=1
AFTER : key_field='My New Vision Segment|new Subsegment|new Category'  q1=1 q2=0 q3=1 q4=1 m11=1
APE Weekly left panel for a November 2026 week: ['My New Vision Segment|new Subsegment|new Category']
```

`q4` is set, `q1` and `q3` survive, and the record the user reported missing is
returned for a November week. On a copy of the installed app's database
(17 APE rows, all already consistent) the migration changed **0 rows**.

### 5.6 Verified on screen in the running app

2026-11-07, 10:51-10:53. The demo instance the user started at 10:14:50
(`GETMOREDONE_DATA_DIR=~/Library/Application Support/GetMoreDone-Demo`) runs
this change's code, so `_repair_orphan_month_flags` ran against the **real**
demo database on open, not a copy: `ape-1e44cdd5` reads
`q1=1 q2=0 q3=1 q4=1 m11=1`.

| Criterion | What the window showed |
|---|---|
| APC-M3.1 | APE Month Assignment opened on Year 2026, **Quarter 4, Month 11**, with headers `APE For Quarter Q4 (check APEs to add to Month M11 and hit save)` and `APE For Month M11`. |
| APC-M3.2 | With Q4 selected the Month dropdown listed exactly **10, 11, 12**. With Q1 selected it listed exactly **1, 2, 3**. |
| APC-M3.3 | Changing Quarter 4 → 1 moved Month 11 → **1**; both panel headers followed to Q1 / M1, and the M1 panel was correctly empty. Changing 1 → 4 moved Month 1 → **10**, the first month of the quarter, which is `_sync_month_choices` pulling an out-of-range month to `allowed[0]`. |
| APC-M4.2 | APE Weekly on Week Start **2026-11-02** showed the left panel headed `Month-assigned APEs for 2026-11` with row 1 `My New Vision Seg… / new Subsegment` — the record the user reported missing. |

The APE Month header row reads correctly with the status label added to it; the
label itself was not exercised, because that needs a Save, which would write to
the user's demo data.

### 5.7 Not covered

- **The user's main database is not touched by this change.** The repair runs
  against it when the app next opens it; on a copy (17 APE rows, all already
  consistent) it changed 0 rows.
- **The Save status message was not seen on screen.** `_describe_month_assignment`
  is covered by `test_apcm23_*`, but its wording in the real header was not
  checked, since showing it means writing an assignment to live data.

### 5.8 The sweep, and the four criteria it added

Three passes over the unpushed range `7aa601d...HEAD`, which carries this batch
and the nine unpushed plan-screen (PD-\*) commits:

| Pass | Lens | Result |
|---|---|---|
| `learning-qa` | the project's failure-pattern catalogue; P2, P4, P5, P6 and P8 applicable | 4 findings (1 medium-high, 2 medium, 1 low-medium), 2 adjacent notes, no high |
| `/code-review` (high) | correctness over the 1,135-line source-only diff, hunk by hunk | 6 findings — the same four, plus two lows |
| `/security-review` | injection, secrets, path traversal, unsafe deserialisation, data exposure | **no findings at the ≥8 confidence bar** |

Four findings were fixed, with tests, as APC-M2.4, APC-M4.4, APC-M5.4 and
APC-M6.2 — graded, as the table above grades them, one medium-high, two
medium and one low-medium. The first version of this paragraph called all
four "medium", which both overstated three of them and quietly broke the
repo's own budget rule that below-medium findings go to `BACKLOG.md` instead
of being fixed in-loop. The low-medium one (APC-M4.4, the month lookup guard)
was fixed anyway; it belongs in this record as an exception taken, not as a
medium. Two lows and two adjacent issues did go to `BACKLOG.md`:

- `date_utils.quarter_of_month` truncates a float and accepts a bool
  (`quarter_of_month(11.7)` → 4, `quarter_of_month(True)` → 1; measured). No
  production caller can reach it with a non-integer.
- `plan._require_block_day` opens a modal from inside a drop's `after_idle`,
  which pumps the event queue. PLAUSIBLE, not confirmed — neither pass could
  drive a date change through Tk's modal grab.
- Adjacent: the Plan screen's failure arm is on 3 of its 8 write paths;
  `weekly_items` files a straddling week under its start date's month.

**The security pass caught an error in one of the fixes**, which is worth
recording because it is the kind a warm pass does not catch. The first version
of APC-M4.4 guarded with `if month not in QUARTER_OF_MONTH` alone, and its
docstring claimed that rejected the float case. It does not: `11.0 in {11: ...}`
is `True`, because a dict is keyed by hash and equality. The fix needs both the
membership test *and* a column name built from `int(month)`, and the test now
asserts the float case explicitly rather than assuming the guard covers it.

What the SQL review found safe, traced rather than assumed: every f-string
column name in the range resolves to a module constant built from `range(1, 13)`
(`MONTHS_OF_QUARTER`, nothing in `src/` mutates it) or to an `int()`-parsed
caller argument, and the one free-text field on either screen — the year entry —
is bound as a `?` parameter. The new `messagebox` text and log lines carry an
opaque APE id and integers, to a local file in the app's own data directory.

### 5.9 Mutation proofs for the sweep fixes

Eight mutations, eight reds, each restored byte-identical:

| Mutation | Test that caught it |
|---|---|
| APC-M4.4 guard back to `month < 1 or month > 12` | `test_apcm44_month_lookup_guard_is_type_safe` |
| APC-M5.4 repair returns `[]` instead of `repaired` | `test_apcm54_the_repair_reports_every_row_it_changed` |
| APC-M5.4 repair stops stamping `updated_at` | `test_apcm54_the_repair_reports_every_row_it_changed` |
| APC-M2.4 month `_assign_one` loses its `except` arm | `test_apcm24_a_raising_assignment_is_counted_not_escaped` |
| APC-M6.2 quarter `_assign_one` loses its `except` arm | `test_apcm62_a_raising_quarter_assignment_is_counted_not_escaped` |
| APC-M6.2 wording drops the refused count | `test_apcm62_quarter_save_reports_refused_assignments` |
| APC-M6.2 nothing-checked goes silent again | `test_apcm62_quarter_save_with_nothing_checked_says_so` |
| APC-M6.2 drop target stops reporting | `test_apcm62_quarter_drag_path_reaches_the_same_reporting` |

### 5.10 Still not covered after the sweep

- ~~**APE Quarter's new status label was not seen on screen.**~~ Both screens'
  status lines were read on screen in the §5.13 run, against a throwaway copy
  of the demo database rather than the live data — which is what made the
  original reason ("showing it means writing an assignment to the user's live
  demo data") avoidable: `GETMOREDONE_DB` points the real app at a copy. What
  is still unseen is the Remove wording and the "partly assigned" wording; see
  §5.13.
- ~~**`_repair_orphan_month_flags`' new log line was not read from the real
  log file.**~~ Covered as APC-M5.5 in the second fix round — see §5.11. The
  reason given here was wrong: the line going to the user's log does not make
  a behavioural check impractical, and
  `test_wt_m7a5_dedupe_log_reaches_a_handler` in this same repo was already
  the counter-example. What remains untested is the real file handler's path
  and rotation, not whether the record is emitted.
- **The PD-\* plan-screen batch had no `learning-qa`-family finding**, and
  `learning-qa` said plainly that its catalogue does not cover that batch's
  likely failure family (Tk geometry, layout and UI contract). The
  `/code-review` pass did read every plan-screen hunk and traced the pane
  arithmetic, the depth-bar loop bounds, the marker-glyph collision, the redraw
  flush ordering and the `CTkComboBox` variable/command ordering, finding one
  PLAUSIBLE low. No separate UI-regression pass was run over the 50+ screens.

### 5.11 The re-sweep over the fix commits, and the second fix round

The repo's sweep budget says every in-loop fix is itself in scope for the next
pass, so `c31fce7...HEAD` — the three fix commits from §5.8, 1,080 lines over
10 files — went back through `learning-qa`. It returned four findings, one of
them a defect in §5.8's own fix. That is the budget's premise holding: the fix
commit is the least-reviewed code in a change, written last and in the most
anchored state.

| # | Severity | Finding | Outcome |
|---|---|---|---|
| F1 | medium-high | The status line was computed from `_assign_one`'s boolean. `assign_ape_to_month` writes before it can fail, so `False` does not mean nothing was written — the line said "Assigned 0 APE(s) to M11" beside a panel showing the row | fixed, APC-M2.5 / APC-M6.3 |
| F2 | medium | The class claim was wrong. "Four write paths across two screens" is really seven: the two assigns on each screen, the two **removes**, and the cascade's own call site | two removes fixed, APC-M2.6 / APC-M6.4; the cascade flagged, below |
| F3 | medium | `_repair_orphan_month_flags`' `logger.info` had no test — deleting it left every other APC test green — and §5.10's stated reason for that was contradicted by an existing test in this repo | fixed, APC-M5.5 |
| F4 | medium-low | `_assign_one`'s broad `except Exception` swallows a stub's `AssertionError`, so four assertions in the published tests could not fail on a malformed manager call | fixed: both drag tests now record the manager call and assert it |

F1 is the one worth keeping. `_assign_one` returning `False` after a raise is
not "nothing happened": `assign_ape_to_quarter` commits the quarter flag and
*then* raises on a segment it cannot resolve, and `assign_ape_to_month` has two
`return False` exits after both flags are committed. Reporting from a return
code instead of from the artifact is P6 inverted — the status is a claim, and
the only thing that can settle it is a re-read of the row. Both screens now
read `self.right_items` after `refresh_lists()`, which is the same unfiltered
query the panel is drawn from, so the sentence and the panel cannot disagree.

The published APC-M2.4 tests could not have caught F1: their stubs raise
*instead of* writing, so a boolean-counted line passes them. `test_apcm25_*`
and `test_apcm63_*` therefore use the real manager on a real database in the
one state that makes it half-write — the APE already in Q4, its segment
unresolvable — and assert both halves, that the call raised and that the row is
in the month. A fixture that only fails is the fixture that cannot catch this.

**Adjacent issue found, not fixed.** `weekly_tactic.py:294` calls
`assign_ape_to_month` inside the re-filing cascade, discards the return value
and has no `try`. It is the seventh member of F2's class, left alone
deliberately: it is a different subsystem with its own `CascadeReport`
surface, so hardening it belongs with that reporting rather than bolted on
here. Recorded in `BACKLOG.md`.

Five mutations for the five new tests, five reds, each restored byte-identical:

| Mutation | Test that went red |
|---|---|
| APC-M2.5 month Save reports from `claimed` instead of `self._ids_in_month()` | `test_apcm25_a_half_written_assignment_is_reported_as_partial` |
| APC-M2.6 `delete_month_item` stops re-reading the row (`still_there = False`) | `test_apcm26_a_failed_remove_is_reported` |
| APC-M6.3 quarter Save reports from `claimed` instead of `self._ids_in_quarter()` | `test_apcm63_a_half_written_quarter_assignment_is_reported_as_partial` |
| APC-M6.4 `delete_quarter_item` stops re-reading the row | `test_apcm64_a_failed_quarter_remove_is_reported` |
| APC-M5.5 the repair's `logger.info` never fires (`if False:`) | `test_apcm55_the_repair_log_reaches_a_handler` |

### 5.12 Re-sweep findings recorded rather than fixed

Below the medium bar, so `BACKLOG.md` per the budget:

- `month not in QUARTER_OF_MONTH` still raises `TypeError` for an unhashable
  month (`[]`, `{}`, `set()`), and `True` passes the membership test and
  becomes column `m1`. The APC-M4.4 docstring and the `NOTES.md` entry both
  called the guard "type-safe"; it is range-safe and int-safe, which is what
  its reachable callers need, and both wordings are corrected.
- P1 nuance: a transient `sqlite3.OperationalError` ("database is locked")
  produces the same status sentence as a permanent refusal. The log line
  carries the exception; the sentence does not distinguish retryable from
  terminal.

### 5.13 The program run, 2026-11-07 13:05–13:08

Reviews read code; none of them execute it. This batch's own §5.6 run covered
the pickers and APE Weekly against the **real** demo database, read-only in
effect. The second fix round changed what the two screens *say*, which cannot
be seen without writing — so this run used `GETMOREDONE_DB` to point the real
app at a throwaway copy of the demo database, with that copy's `q4` flag
cleared first so the migration had work to do.

Observed, in the running app:

| What | Result |
|---|---|
| APC-M5.4 / M5.5 — the migration on open | The copy's row went `q4 = 0` → `q4 = 1` with `q1` and `q3` intact, `updated_at` stamped `2026-11-07T13:05:20.435172`, and the log line landed: `INFO [vps_schema] APC-M5 backfilled 1 implied quarter flag(s): [('ape-1e44cdd5', 4)]` at 13:05:20,435 |
| APC-M3 / M6.1 — the pickers | APE Month opened on Year 2026, Quarter 4, Month 11; APE Quarter opened on Q4 |
| APC-M2.3 — nothing checked | APE Month's status line read **"Check one or more APEs on the left first."** |
| APC-M2.5 — a real save | APE Month's status line read **"Assigned 1 APE(s) to M11."** |
| APC-M6.2 / M6.3 — the sibling screen | APE Quarter's status line read **"Assigned 1 APE(s) to Q4."** |

That closes §5.7's and §5.10's "the status label was not seen on screen" for
both screens, on the Save path.

**Not covered by this run**, stated rather than left to be assumed:

- The **Remove** wording (APC-M2.6 / M6.4). The Delete button sits in the right
  panel's Actions column, past the visible width at this window size, and the
  divider drag did not take. Covered by `test_apcm26_*` and `test_apcm64_*`,
  whose stubs fail in the three real shapes.
- The **partly assigned** wording. Producing it on screen means an APE whose
  segment cannot be resolved, which is a corrupt lineage this copy does not
  have. Covered by `test_apcm25_*` and `test_apcm63_*` against the real
  manager.
- The log line went to the app's own log directory,
  `~/Library/Application Support/GetMoreDone/weekly_tactic_debug.log`, because
  `GETMOREDONE_DB` overrides the database and not the log path. Nothing was
  written to either real database: afterwards their newest `updated_at` values
  were `2026-11-07T09:00:49` (demo, from this morning's run) and
  `2026-10-18T15:39:43` (installed app), both older than this run.
