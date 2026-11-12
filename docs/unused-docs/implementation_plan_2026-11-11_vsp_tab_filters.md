# Implementation plan — the VSP tabs' left-to-right filter and the bottom Add New (VTF-M1 … VTF-M7)

Date: 2026-11-11
Status: **approved 2026-11-11 by the user and built the same day: 31 of 31
code criteria done, VTF-N1 and VTF-N2 outstanding as walk items. A cold sweep
then found 6 findings (1 high) and they are fixed; see *The sweep* below.** The four
design decisions are settled (recorded under *Decisions taken*). The status
report is at the end of this file.
Screens: `src/getmoredone/screens/annual_vision_segments.py`,
`ape_assignment.py`, `ape_period_view.py`, `weekly_items.py`,
`week_actions.py`, `vision_segments.py`
Reported by the user, 2026-11-11, in three parts: the left rows do not filter
the right rows on any tab; every tab needs an Add New for the right-hand
records, on buttons at the bottom; and APE Week Assignment's bottom buttons are
wrong.

## What is there now

Audited 2026-11-11 by reading all six tab modules.

| Tab | Left | Right | Left row filters right? |
|---|---|---|---|
| Vision Elements | *(not dual-panel: one of Segments / SubSegments / Categories at a time)* | — | n/a |
| Annual Plan Elements | Vision Elements, tick boxes | the year's annual elements | **No.** Right query takes the year only |
| APE Quarter Assignment | the year's APEs, tick boxes | APEs in the quarter | **No.** The Segment/Sub/Cat dropdowns filter, and they filter both panels |
| APE Month Assignment | APEs in the quarter, tick boxes | APEs in the month | **No.** Same |
| APE Week Assignment | the month's APEs, tick boxes | the week's weekly tactics | **No.** Same |
| APE Week Actions | the week's weekly tactics | that tactic's Action Items | **Yes.** A row click narrows the right panel |

**This is not a regression.** In the whole history of the four assignment tabs
`left_checks` is read in exactly one place — `add_selected`, the Save button —
and no checkbox in any version ever carried a `command=` or a `trace_add`. The
tick has always been the assignment selector: tick rows on the left, press
Save, and the records are created in or assigned to the right panel. The
behaviour the user is asking for was never built.

One comment has to go with it. `annual_vision_segments.py:81-84` says *"This
tab filters nothing -- there is no lineage above an annual plan element to
filter by"*, and that is wrong: every right-hand row carries
`vision_element_id`, `segment_name`, `subsegment_name` and `category_name`, so
both the tick filter and the three dropdowns the other tabs have are available
from data already in hand.

## The design this plan implements

The tick cannot mean both "show me these on the right" and "add these to the
right". The user chose, 2026-11-11: **the tick becomes a filter, and the only
way to add a record is a button at the bottom of the right panel.** So each
Add New opens a dialog that names its own parent, rather than reading the
ticks.

**Each panel has exactly one filter, and they are different filters.** The
user stated the rule on 2026-11-11: the Segment / SubSegment / Category
dropdowns filter the **left** panel — they narrow the list of candidates — and
the **right** panel is filtered by what is selected on the left. Today the
dropdowns filter both panels, so the work is to take them off the right panel,
not off the left. APE Week Actions already obeys this rule: its dropdowns
filter the left tactics list only, and the right panel follows the selected
row.

Drag-and-drop assignment (left row onto the right panel) exists on tabs 2–5 and
is **kept**: it is an existing affordance, the UI-regression policy keeps it
unless removal is asked for, and it leaves a second path while the Add New
dialogs are new.

## VTF-M1 — The left tick filters the right panel

The checkbox gains a `command=` that re-renders the right panel only. No tick
means no filter, so an untouched screen looks exactly as it does today.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M1.1 | Annual Plan Elements: ticking Vision Elements narrows the right panel to rows whose `vision_element_id` is ticked | `tests/test_vsp_tab_filters.py::test_vtfm11_the_annual_tab_right_panel_follows_the_ticks` |
| VTF-M1.2 | APE Quarter Assignment: ticking APEs narrows the right panel to those APE ids | `::test_vtfm12_the_quarter_tab_right_panel_follows_the_ticks` |
| VTF-M1.3 | APE Month Assignment: the same, on the month's rows | `::test_vtfm13_the_month_tab_right_panel_follows_the_ticks` |
| VTF-M1.4 | APE Week Assignment: ticking APEs narrows the right panel to tactics whose `annual_plan_element_id` is ticked | `::test_vtfm14_the_week_tab_right_panel_follows_the_ticks` |
| VTF-M1.5 | No tick ticked = every right-hand row, on all four tabs | `::test_vtfm15_no_tick_is_no_filter` |
| VTF-M1.6 | The tick takes effect without pressing Load, Save or Refresh | `::test_vtfm16_the_tick_refreshes_without_a_button` |
| VTF-M1.7 | A dropdown narrows the left list, and so narrows which rows can be ticked; it does not reach the right panel (VTF-M2) | `::test_vtfm17_the_dropdown_does_not_reach_the_right_panel` |
| VTF-M1.8 | The left panel is not re-rendered by a tick, so a tick cannot hide its own row | `::test_vtfm18_a_tick_leaves_the_left_panel_alone` |
| VTF-M1.9 | A tick on a row a dropdown has since hidden is ignored, and with no visible tick left the right panel shows every row again (VTF-M1.5) | `::test_vtfm19_a_hidden_tick_stops_filtering` |

## VTF-M2 — The dropdowns stop filtering the right panel

Decision D2, 2026-11-11: the dropdowns are the **left** panel's filter and the
left selection is the **right** panel's. Today `on_filters_changed` applies
`_filtered_rows` to both sides, which gives the right panel two filters and the
tick nothing to do. This is the half that is removed.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M2.1 | Quarter, Month and Week Assignment: a dropdown narrows the left list and leaves the right panel to the ticks | `::test_vtfm21_the_dropdown_is_a_left_panel_filter` |
| VTF-M2.2 | The dropdown's option list is still built from the left items | `::test_vtfm22_the_options_still_come_from_the_left_items` |
| VTF-M2.3 | APE Week Actions is unchanged: its dropdowns already filter the left list only | `::test_vtfm23_week_actions_already_obeys_the_rule` |

## VTF-M3 — A bottom Add New on every right panel

Each button sits in a frame gridded under the right panel, which is where
`weekly_items.py` already puts its `right_actions` row — the one tab that has
a bottom button row today.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M3.1 | Annual Plan Elements: **Add New Annual Plan Element** opens a dialog picking a Vision Element, and creates both annual records through `create_annual_records_from_vision_element` | `::test_vtfm31_the_annual_tab_adds_from_a_vision_element` |
| VTF-M3.2 | APE Quarter Assignment: **Assign APE to Quarter** opens a dialog picking from the year's APEs not already in the quarter | `::test_vtfm32_the_quarter_tab_assigns_from_a_dialog` |
| VTF-M3.3 | APE Month Assignment: **Assign APE to Month**, from the quarter's APEs not already in the month | `::test_vtfm33_the_month_tab_assigns_from_a_dialog` |
| VTF-M3.4 | APE Week Assignment: **Add Weekly Tactic** opens a dialog picking the parent APE from the month's APEs, and creates the tactic for the selected week | `::test_vtfm34_the_week_tab_adds_a_weekly_tactic` |
| VTF-M3.5 | APE Week Actions: the existing **Add Action Item** moves from the top of the right panel to the bottom, unchanged in behaviour | `::test_vtfm35_week_actions_add_sits_at_the_bottom` |
| VTF-M3.6 | Each dialog's parent field defaults to the single ticked left row when exactly one is ticked, and to nothing otherwise | `::test_vtfm36_the_dialog_defaults_to_one_tick` |
| VTF-M3.7 | Every Add New writes its outcome to the tab's status line, including a refusal | `::test_vtfm37_add_new_reports_on_the_status_line` |
| VTF-M3.8 | A record added through the dialog is visible in the right panel without a Refresh | `::test_vtfm38_the_new_record_appears_at_once` |

## VTF-M4 — The Save buttons go

A consequence of VTF-M1: with the tick a filter, a Save that reads the ticks
has nothing to read.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M4.1 | The top-header **Save** is gone from tabs 2–5, and `add_selected` with it | `::test_vtfm41_no_tab_still_saves_from_the_ticks` |
| VTF-M4.2 | Load, This Week and Refresh stay where they are | `::test_vtfm42_the_other_header_buttons_survive` |
| VTF-M4.3 | Drag-and-drop assignment still works on all four tabs | `::test_vtfm43_the_drag_still_assigns` |

**UI contract.** VTF-M4.1 removes a user-visible control from four screens.
The user asked for Add New on the bottom in place of what is there; this plan
records that as the approval, and it is called out here because the
ui-regression policy requires removals to be explicit rather than implied.

## VTF-M5 — APE Week Assignment's bottom buttons

The user's third point, verified against the code: the bottom **Delete
Weekly** calls the same `delete_weekly_row` as the per-row Delete, and the
bottom **Edit Weekly Tactic** opens the same `ItemEditorDialog` as a
double-click on the row. Both are redundant. **Add Action Item** creates an
`ActionItem` the right panel cannot display — Action Items belong to the Week
Actions tab, which already has that button.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M5.1 | **Edit Weekly Tactic** is gone; a double-click on a right-hand row still opens the editor | `::test_vtfm51_the_row_still_opens_the_editor` |
| VTF-M5.2 | **Delete Weekly** is gone; the per-row Delete still deletes, with its confirmation | `::test_vtfm52_the_row_delete_still_asks_and_deletes` |
| VTF-M5.3 | **Add Action Item** is gone from this tab | `::test_vtfm53_week_assignment_adds_no_action_item` |
| VTF-M5.4 | **Add Weekly Tactic** is the only button in the bottom row, and is VTF-M3.4 | `::test_vtfm54_one_button_at_the_bottom` |
| VTF-M5.5 | A tactic created there satisfies the right panel's own `ape_only=True` query, so it appears rather than being created invisibly | `::test_vtfm55_a_new_tactic_is_not_invisible` |

## VTF-M6 — The Vision Elements tab

Decision D1, 2026-11-11: **move the buttons only.** The tab is three lists
shown one at a time, so "left filters right" has nowhere to land, and it keeps
that structure.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M6.1 | `+ New Segment`, `+ New SubSegment` and `+ New Category` move from the top header to a bottom row, behaviour unchanged | `::test_vtfm61_the_new_buttons_sit_at_the_bottom` |
| VTF-M6.2 | Refresh stays in the top header, and the three view-switcher buttons stay where they are | `::test_vtfm62_the_switcher_and_refresh_do_not_move` |

Restructuring the tab into panels with Segment → SubSegment → Category as a
filter chain was the alternative and was **not** chosen. It is a larger job
than the other five tabs together; it is not filed, because nobody has asked
for it.

## VTF-M7 — A contract test per tab

Required by the ui-regression policy: each of the six tabs gets one test
asserting the controls that must be present after this batch — the bottom Add
New, the surviving header buttons, the per-row Edit/Delete where they exist.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M7.1 | Six contract tests, one per tab, each naming that tab's controls | `tests/test_vsp_tab_contracts.py::test_vtfm71_<tab>_controls` (six tests) |

## Not code-testable

| ID | Criterion | Human-review proposal |
|---|---|---|
| VTF-N1 | The filter reads as a filter on screen: ticking a row visibly narrows the right panel, and the user can tell what the current filter is | A walk-through item per tab, filed with the batch, as the LRR and SCV batches did |
| VTF-N2 | Each Add New dialog opens on macOS from a button command without the `TclError` or the hang that two attempts at a dialog on the Plan screen's drag-release path hit (PF-M1) | Walk item. The risk is low and the reason is stated: these dialogs open from a button `command=`, the same moment as the Edit and Delete confirmations that work today, not from a drag release or an idle callback |

## Implementation order

1. **VTF-M1 on Annual Plan Elements**, with VTF-M1.5–M1.8. The simplest tab —
   no dropdowns to compose with — and the one with no filtering at all today.
2. **VTF-M1 on Quarter, Month and Week Assignment**, including VTF-M1.7.
3. **VTF-M2**, if D2 is yes. Independent of the rest; do it before M3 so the
   Add New dialogs are written against the final filter behaviour.
4. **VTF-M3 and VTF-M4 together, tab by tab.** The Save removal and the Add New
   that replaces it must land in the same change per tab, or a tab sits with no
   way to add a record.
5. **VTF-M5** (Week Assignment's bottom row), which contains VTF-M3.4.
6. **VTF-M6**, per D1.
7. **VTF-M7**, last, so the contract tests assert the finished state.
8. **Documents, in the same batch**: `docs/USER_GUIDE.md` for every changed
   control on all six tabs, `CHANGELOG.md`, `docs/spec_coverage.md` for the
   criteria table, and `docs/DOCUMENTATION_INDEX.md`.

Dependencies: M3 depends on M1 (the tick stops being the assignment selector);
M4 depends on M3 per tab; M5 contains M3.4; M7 depends on all of them.

## Decisions taken — all four, 2026-11-11

- **D1 — the Vision Elements tab: move the buttons only.** No restructure.
  VTF-M6.
- **D2 — the dropdowns filter the left panel; the left selection filters the
  right.** Stated by the user in these words: *"Only the left panel is
  filtered. The right panel is filtered by selecting a record on the left
  panel."* This is the opposite of what the draft of this plan proposed — that
  draft would have moved the dropdowns onto the right panel — and VTF-M2 is
  rewritten accordingly.
- **D3 — Quarter and Month: narrow to the ticked.** Both panels list
  `annual_plan_elements` there, so ticking an APE shows whether it is in that
  quarter or month. VTF-M1.2 and VTF-M1.3 stand as written.
- **D4 — drag-and-drop is kept** on all four assignment tabs.

One rule follows from D2 and D3 together and was not asked about: VTF-M1.9,
what happens to a tick on a row a dropdown then hides. The plan ignores such a
tick, because the alternative is a filter the user cannot see, and because
`week_actions.py` already clears its right panel when the filter hides the
selected tactic. Say so if you want the other reading.

## Risks

- **VTF-M4 is the change with the blast radius.** Four screens lose the only
  button they have for creating records, and four new dialogs take over. Drag
  remains as a second path, which is why D4 recommends keeping it.
- **`tests/test_ci_contract.py` asserts how many tests take the
  `mapped_windows` fixture** (23 today, also stated in `CLAUDE.md`'s Commands
  block). The new tests must not take that fixture — the existing screen tests
  for these tabs do not — or that count and that paragraph change in the same
  batch.
- **One build batch at a time.** Another session is building in this checkout.
  This batch starts when that one has pushed.
- Every `DatabaseManager` in the new tests takes an explicit `tmp_path`
  database, or the suite runs migrations against the user's real one.

## Status report — built 2026-11-11

Commits: `a637917`, `dec6e9d`, `1d69964`, `20bf04c` (VTF-M1, VTF-M2),
`3e7b0af`, `e8d8b3e` (VTF-M3, VTF-M4, VTF-M5), `3ff52ae`, `5d42e8f`
(VTF-M6, VTF-M7). `src/` and test changes are separate commits throughout, so
the ratio stays visible in `git log --stat`.

Tests live in `tests/test_vsp_tab_filters.py` (24), `tests/test_vsp_tab_adds.py`
(12) and `tests/test_vsp_tab_contracts.py` (8). None takes the
`mapped_windows` fixture, so `tests/test_ci_contract.py`'s count of 23 and
`CLAUDE.md`'s Commands block are unchanged — the risk this plan names is
closed. Every test was mutation-proved with the verbatim original restored:
10 mutants for VTF-M1/M2, 8 for the rewritten APC tests, 16 for VTF-M3/M4/M5,
15 for VTF-M6/M7.

| ID | Status | Proof |
|---|---|---|
| VTF-M1.1 | done | `::test_vtfm11_the_annual_tab_right_panel_follows_the_ticks`, `::test_vtfm11_the_heading_says_when_the_right_panel_is_filtered` |
| VTF-M1.2 | done | `::test_vtfm12_the_quarter_tab_right_panel_follows_the_ticks` |
| VTF-M1.3 | done | `::test_vtfm13_the_month_tab_right_panel_follows_the_ticks` |
| VTF-M1.4 | done | `::test_vtfm14_the_week_tab_right_panel_follows_the_ticks` |
| VTF-M1.5 | done | `::test_vtfm15_no_tick_is_no_filter`, `::test_vtfm15_no_tick_is_no_filter_on_the_ape_tabs` |
| VTF-M1.6 | done | `::test_vtfm16_the_tick_refreshes_without_a_button`, `::test_vtfm16_the_tick_refreshes_the_ape_tabs_without_a_button` |
| VTF-M1.7 | done | `::test_vtfm17_the_dropdown_does_not_reach_the_right_panel` |
| VTF-M1.8 | done | `::test_vtfm18_a_tick_leaves_the_left_panel_alone` |
| VTF-M1.9 | done | `::test_vtfm19_a_hidden_tick_stops_filtering`, `::test_vtfm19_a_dropdown_that_hides_a_ticked_row_stops_its_filter` |
| VTF-M2.1 | done | `::test_vtfm21_the_dropdown_is_a_left_panel_filter` |
| VTF-M2.2 | done | `::test_vtfm22_the_options_still_come_from_the_left_items` |
| VTF-M2.3 | done | `::test_vtfm23_week_actions_already_obeys_the_rule` |
| VTF-M3.1 | done | `::test_vtfm31_the_annual_tab_adds_from_a_vision_element` |
| VTF-M3.2 | done | `::test_vtfm32_the_quarter_tab_assigns_from_a_dialog` |
| VTF-M3.3 | done | `::test_vtfm33_the_month_tab_assigns_from_a_dialog` |
| VTF-M3.4 | done | `::test_vtfm34_the_week_tab_adds_a_weekly_tactic`, `::test_vtfm34_the_week_tab_refuses_before_a_week_is_chosen` |
| VTF-M3.5 | done | `tests/test_vsp_tab_contracts.py::test_vtfm35_week_actions_add_sits_at_the_bottom` |
| VTF-M3.6 | done | `::test_vtfm36_the_dialog_defaults_to_one_tick`, all four tabs in one test |
| VTF-M3.7 | done | `::test_vtfm37_add_new_reports_on_the_status_line`, `::test_vtfm37_a_dialog_with_nothing_to_offer_refuses_on_the_status_line`, `::test_vtfm37_open_pick_record_dialog_reports_its_empty_refusal` |
| VTF-M3.8 | done | `::test_vtfm38_the_new_record_appears_at_once`, on the real screen |
| VTF-M4.1 | done | `::test_vtfm41_no_tab_still_saves_from_the_ticks`; `add_selected` is gone from all four classes |
| VTF-M4.2 | done | the four header assertions in `tests/test_vsp_tab_contracts.py`, and `tests/test_unified_panel_design.py::test_updf25_the_status_line_moved_below_the_filters` |
| VTF-M4.3 | done | `tests/test_ape_period_consistency.py::test_apcm23_drag_path_reaches_the_same_reporting`, `::test_apcm62_quarter_drag_path_reaches_the_same_reporting`, `tests/test_weekly_tactic_schema.py::test_wt_m1c3_both_creation_paths_report_collisions` and its two siblings. The annual tab's drop target is unchanged code and has no drag test of its own — see the handoff note |
| VTF-M5.1 | done | `tests/test_vsp_tab_contracts.py::test_vtfm54_one_button_at_the_bottom`, with `tests/test_unified_panel_design.py::test_updm57_clicking_a_right_row_selects_it_and_double_click_opens_it` |
| VTF-M5.2 | done | the same contract test, with `::test_updm52_a_row_delete_removes_that_row_not_the_selection` and `::test_updm53_delete_is_confirmed_before_it_happens` |
| VTF-M5.3 | done | the same contract test asserts the bottom row verbatim |
| VTF-M5.4 | done | `::test_vtfm54_one_button_at_the_bottom` |
| VTF-M5.5 | done | `tests/test_vsp_tab_adds.py::test_vtfm55_a_new_tactic_is_not_invisible`, real manager on a real database |
| VTF-M6.1 | done | `::test_vtfm61_the_new_buttons_sit_at_the_bottom`, `::test_vtfm71_vision_elements_controls` |
| VTF-M6.2 | done | `::test_vtfm62_the_switcher_and_refresh_do_not_move` |
| VTF-M7.1 | done | six tests in `tests/test_vsp_tab_contracts.py` — four `::test_vtfm71_*`, plus `::test_vtfm54_one_button_at_the_bottom` and `::test_vtfm35_week_actions_add_sits_at_the_bottom` for the two tabs whose contract is named by its own criterion |
| VTF-N1 | **not done — walk item** | On-screen only. Filed in `docs/unused-docs/changes/2026-11-11-vsp-tab-filters-walk.md` |
| VTF-N2 | **not done — walk item** | On-screen only, and it is the one hop no test covers: a real `CTkToplevel` is a mapped window. Same note |

### What the code could not cover

`open_pick_record_dialog`'s join between `on_confirm` and `report` — the line
that writes the write's sentence to the tab's status line after the dialog
closes — is asserted on neither side's behalf, because driving it needs a real
`CTkToplevel` and that is a mapped window. Both ends are covered: each tab
hands the dialog its own `_perform_add` and its own status label
(VTF-M3.7), and each write reconciles and returns a sentence. It is one
function for all four tabs, so VTF-N2 is one walk check rather than four.

### The sweep, and what it changed (VTF-S1 - VTF-S6)

A cold `learning-qa` pass over the nine build commits found **1 high, 4 medium
and 1 low-medium** finding, all of them in the write and refusal paths VTF-M3
added. Fixed in `eb09644` (src) and `f770abc` (tests), as a class across the
four tabs. These IDs are the sweep's; `BACKLOG.md`'s VTF-A1 - VTF-A3 are the
adjacent issues found and not fixed, which is a different list.

| ID | Severity | What was wrong | Test |
|---|---|---|---|
| VTF-S1 | high | The Annual Plan Elements drop called the manager raw — no guard, no report either way. `row_drag.finish` calls `on_drop` with no `try`, so a locked database or a stale row escaped into a Tk callback. Its three sibling tabs all guarded and reported (P5) | `::test_vtfs1_the_dropped_row_reports_what_it_wrote`, `::test_vtfs1_a_drop_with_no_id_refuses_rather_than_raising`, `::test_vtfs1_a_raising_drop_is_reported_not_escaped` |
| VTF-S2 | medium | That tab's `_perform_add` claimed "Added" from the absence of an exception. The manager logs a failed project board as a warning and carries on, so a half-written record read as clean success (P6) | `::test_vtfs2_an_unwritten_add_is_not_reported_as_added` |
| VTF-S3 | medium | The quarter and month refusals gave one wording for all three reasons an option list comes back empty, so a year holding no APEs was told every one of them was already in the quarter (P2/P9) | `::test_vtfs3_the_empty_refusal_names_the_real_reason`, and `tests/test_ape_period_consistency.py::test_apcm62_quarter_add_with_nothing_to_add_says_so` |
| VTF-S4 | medium | `weekly_items._create_tactic_for` caught only `ValueError`, and `_assign_dragged_row` calls it straight from a drag release with no `try` above it (P1) | `::test_vtfs4_a_non_valueerror_from_the_week_write_is_reported` |
| VTF-S5 | medium | `_add_options` on the quarter and month tabs read the unfiltered `left_items`, so a dialog opened under a Category filter listed every category's APEs. The week tab's docstring states the opposite rule as the design intent | `::test_vtfs5_the_dialog_offers_only_what_the_left_panel_shows` |
| VTF-S6 | low-medium | The annual `_add_default` handed over a key `_add_options` had excluded, so a tick on an already-added Vision Element opened the combo blank. Both siblings carry the guard (P5) | `::test_vtfs6_a_ticked_row_already_added_is_not_the_default` |

12 further mutants, 12 killed. `tests/test_ape_period_consistency.py::test_apcm62_quarter_add_with_nothing_to_add_says_so` changed its expected sentence under rule (b), the behaviour changed intentionally: that fixture's year holds no APEs, which is the exact input the old refusal was wrong about, and the promise it asserts is unchanged.

A high-severity finding requires a further cold pass, in a different failure
family. The second pass covered test quality and the UI control contract.

### Documents changed in this batch

`docs/USER_GUIDE.md` (the hub section: the tick filter, the bottom Add New,
the removed Save, APE Week Assignment's bottom row, Week Actions' moved
button, Vision Elements' moved button), `CHANGELOG.md`,
`docs/spec_2026-11-07_ape_period_consistency.md` (APC-M2 and APC-M6 point at
the write path, with a dated supersession note),
`docs/spec_2026-11-07_unified_panel_design.md` (UPD-M5.4),
`docs/DOCUMENTATION_INDEX.md` (this plan's entry), `BACKLOG.md` (the three
adjacent issues), `docs/ui_color_inventory.md` (regenerated), this file, and
the handoff note. The sweep's fixes changed what the user sees on two counts --
the annual drop now reports, and a refusal names its reason -- so
`docs/USER_GUIDE.md` and `CHANGELOG.md` were changed again with them. `docs/spec_coverage.md` is **not** changed: it is the Project
Notes feature's criteria record, not a repo-wide one, and this plan's step 8
named it by mistake.
