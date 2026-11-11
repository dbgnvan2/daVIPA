# Implementation plan — the VSP tabs' left-to-right filter and the bottom Add New (VTF-M1 … VTF-M7)

Date: 2026-11-11
Status: **draft, approved by nobody.** Planning only; no code is written until
this is approved.
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

Drag-and-drop assignment (left row onto the right panel) exists on tabs 2–5 and
is **kept**: it is an existing affordance, the UI-regression policy keeps it
unless removal is asked for, and it leaves a second path while the Add New
dialogs are new. See decision D4.

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
| VTF-M1.7 | A tick and a dropdown compose: both must match | `::test_vtfm17_the_tick_and_the_dropdown_are_an_and` |
| VTF-M1.8 | The left panel is not re-rendered by a tick, so a tick cannot hide its own row | `::test_vtfm18_a_tick_leaves_the_left_panel_alone` |

## VTF-M2 — The dropdowns stop filtering the left panel

**Awaiting decision D2.** On an assignment screen the filter belongs to the
right panel: today `on_filters_changed` applies `_filtered_rows` to both sides,
so filtering hides the rows you are trying to assign. Not requested by the
user; raised in review.

| ID | Criterion | Verified by |
|---|---|---|
| VTF-M2.1 | Quarter, Month and Week Assignment: a dropdown narrows the right panel and leaves the left list whole | `::test_vtfm21_the_dropdown_is_a_right_panel_filter` |
| VTF-M2.2 | The dropdown's option list is still built from the left items, so the options do not collapse as the right panel narrows | `::test_vtfm22_the_options_still_come_from_the_left_items` |

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

**Awaiting decision D1.** The tab is three lists shown one at a time, so
"left filters right" has nowhere to land. Two readings:

- **D1a (recommended for this batch):** leave the structure alone, and move the
  existing `+ New Segment / SubSegment / Category` from the top header to a
  bottom row, for consistency with VTF-M3. Verified by
  `::test_vtfm61_the_new_buttons_sit_at_the_bottom`.
- **D1b:** restructure into panels with Segment → SubSegment → Category as a
  filter chain. That is a larger job than the other five tabs together and
  belongs in its own batch.

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

## Open decisions — needed before step 1

- **D1 — the Vision Elements tab.** D1a (move the New buttons to the bottom) or
  D1b (restructure into a filter chain, its own batch)?
- **D2 — VTF-M2.** Should the Segment/Sub/Cat dropdowns stop filtering the left
  panel? Not requested; raised in review.
- **D3 — the Quarter and Month tabs.** Left and right hold the same record
  type there (`annual_plan_elements`), so "the tick filters the right panel"
  reduces to "show only the ticked rows, if they are assigned". That is a
  usable answer — tick one APE, see whether it is in the quarter — but it is
  not the same kind of filter as on the other two tabs, and it is worth
  confirming it is what you want.
- **D4 — drag-and-drop.** Kept by this plan. Say so if you want it gone, since
  "Add New only" could be read as covering it.

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
