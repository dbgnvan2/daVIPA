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

### APC-M5 — existing orphan flags repaired

| ID | Criterion | Test |
|---|---|---|
| APC-M5.1 | Opening a database sets `q{N} = 1` for any APE with a month flag inside quarter N; never clears a quarter flag | `test_apcm51_migration_backfills_the_implied_quarter_flag` |
| APC-M5.2 | Dirty-state (P8): a file DB written with `q1=1, q3=1, m11=1`, then reopened, reads `q1=1, q3=1, q4=1, m11=1` | `test_apcm52_dirty_state_orphan_quarter_flag_is_repaired_on_reopen` |
| APC-M5.3 | Idempotent — a second open changes no row (`updated_at` untouched for already-consistent rows) | `test_apcm53_migration_is_idempotent` |

Home: `VPSSchema._extend_annual_plan_elements` in
`src/getmoredone/vps_schema.py:777`, alongside the flags it is repairing, in the
same idempotent-`UPDATE` style as the existing `action_items` group repair in
`database.py:521`.

### APC-M6 — adjacent issue found, **not** silently fixed

`src/getmoredone/screens/ape_assignment.py:29` (APE **Quarter** Assignment) has
the identical defect: `self.quarter_var = ctk.StringVar(value="1")`. Per the
project's rule 10 this is flagged rather than swept in.

**Approved and fixed** in this change — one line plus
`test_apcm61_quarter_screen_defaults_to_current_quarter`. It is the same defect,
and leaving it means the two APE screens disagree about what quarter you are in.

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
   `docs/changes/2026-11-07-ape-period-consistency.md`.

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
| APC-M3.1 | done | `APEPeriodViewScreen.default_period`; `test_apcm31_quarter_defaults_to_current_quarter` |
| APC-M3.2 | done | `APEPeriodViewScreen._sync_month_choices`; `test_apcm32_month_combo_offers_only_that_quarters_months` |
| APC-M3.3 | done | `test_apcm33_changing_quarter_moves_month_into_range`, `test_apcm33_every_quarter_leaves_the_month_in_range` |
| APC-M3.4 | done | `test_apcm34_default_month_is_always_inside_the_default_quarter` (all 12 months) |
| APC-M4.1 | done | `VPSManager.get_annual_plan_elements_for_month`; `test_apcm41_month_lookup_matches_on_month_flag_alone` |
| APC-M4.2 | done | `test_apcm42_orphan_month_flag_still_appears_in_november` |
| APC-M4.3 | done | `test_apcm43_screens_use_month_lookup`, `test_apcm43_weekly_screen_left_panel_asks_by_month_only` |
| APC-M5.1 | done | `VPSSchema._repair_orphan_month_flags`; `test_apcm51_migration_backfills_the_implied_quarter_flag`, `test_apcm5_every_stored_month_flag_implies_its_quarter` |
| APC-M5.2 | done | `test_apcm52_dirty_state_orphan_quarter_flag_is_repaired_on_reopen` |
| APC-M5.3 | done | `test_apcm53_migration_is_idempotent` |
| APC-M6 | done | `src/getmoredone/screens/ape_assignment.py`; `test_apcm61_quarter_screen_defaults_to_current_quarter` |

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
