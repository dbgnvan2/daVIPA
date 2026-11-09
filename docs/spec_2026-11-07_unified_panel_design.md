# Spec + implementation plan — one panel design across the VSP tabs

Status: **approved 2026-11-07. UPD-M3, UPD-M1, UPD-M2, UPD-M4, UPD-M5 and
UPD-M6 built. UPD-M7.1 done. §11 was walked on 2026-11-08: UPD-M7.2 was
`partial` and UPD-M7.3 `not done`. The four follow-ups the walk produced were
approved the same day and **all four are built and on `main`**: `UPD-F2`,
`UPD-F3` and `UPD-F4` the same day, and `UPD-F1` — nothing surviving a
relaunch — on `refs/heads/claude/elegant-neumann-ab55c9`, merged at
`2fac9b3`. M7.2 and M7.3 stay at
`partial` and `not done` until §11 is walked again, steps 11 to 13
included.** Per-criterion status is in §10; the follow-up plan is
`docs/implementation_plan_2026-11-08_unified_panel_followups.md`.
IDs: `UPD-M1` … `UPD-M7`, then `UPD-F1` … `UPD-F4`. Use them verbatim in
commits, docstrings and test names.

---

## 0. What was asked

> "The weekly assignment panes should be just like the other tabs — like the
> image attached. Same for Week Actions. ideally all these tabs in have the
> same overall design - left and right panels, records listed in each, drag
> from left to right, vertical resizing divider and resizing that shrinks and
> expands columns withing the panel. Make a list and plan"

The attached image is **APE Month Assignment**: a header card, then two panels
separated by a vertical divider, each panel a table with a `#` / Segment /
SubSegment / Category header and coloured chips in the rows, the right panel
carrying an Actions column with a Delete button.

So the ask has four named parts, and they are not all in the same state:

1. left and right panels — **four of six tabs already have this**
2. records listed in each — **four of six**
3. drag from left to right — **four of six**
4. a vertical resizing divider — **four of six**
5. "resizing that shrinks and expands columns within the panel" — **no tab has
   this**, not even the two in the image. This is a new capability, not a
   copy of an existing one.

Point 5 is the part of this request that is actually new work. Points 1-4 are a
consolidation: the behaviour exists four times, written out four times, and is
missing from the two newest tabs.

---

## 1. What is there now

The VSP hub has six tabs (`screens/vision_planning_hub.py:90-97`). Measured
2026-11-07 by counting references in each file:

| Tab | File | Lines | Two panels + divider | Chip table | Drag L→R | Draggable column widths |
|---|---|---|---|---|---|---|
| Vision Elements | `vision_segments.py` | 514 | no | fixed widths, 3 blocks | no | no |
| Annual Plan Elements | `annual_vision_segments.py` | 541 | yes | yes, `col_widths` dict | yes | no |
| APE Quarter Assignment | `ape_assignment.py` | 601 | yes | yes, `col_widths` dict | yes | no |
| APE Month Assignment | `ape_period_view.py` | 710 | yes | yes, `col_widths` dict | yes | no |
| APE Week Assignment | `weekly_items.py` | 610 | yes | partly — see below | yes | no |
| APE Week Actions | `week_actions.py` | 351 | **no** | **no** — buttons | **no** | right panel only, inherited |

### 1.1 The splitter is written out five times, not four

`_on_divider_press` / `_on_divider_drag` / `_on_divider_release` /
`_apply_split_ratio` / `_on_body_resize`, plus `SPLITTER_WIDTH`,
`MIN_PANEL_WIDTH` and `_split_ratio = 0.5`, appear in
`annual_vision_segments.py`, `ape_assignment.py`, `ape_period_view.py` and
`weekly_items.py`. The five method bodies are not merely the same arithmetic:
`diff` of all four is **byte-identical**, measured before the extraction. All
four declare `MIN_PANEL_WIDTH = 420`; the ratio is **not persisted** anywhere,
so every tab opens at 0.5 every launch.

**Two corrections to what this section claimed when it was drafted**, both
established while building UPD-M1 and both corrected here rather than left to
stand:

- It is **five** copies. `project_boards.py:772-1126` holds a fifth, which the
  AST scan behind UPD-M1.5 found. It is not a VSP tab, so it stays out of
  scope, and it differs in four ways: `MIN_PANEL_WIDTH = 300`, a default ratio
  of 0.6, no `_apply_split_ratio` (the arithmetic is inlined in
  `_on_body_resize`), and a clamp that holds **both** panels at the minimum
  where the other four hold only the left. Recorded as UPD-A5.
- `MIN_PANEL_WIDTH` is not "420 in one and not declared in the others". All
  four declare it as a class constant with the same value. The 520 that reading
  came from is the initial `minsize` on the body's two panel columns, which is
  a starting layout, not a minimum: it is overwritten by the first resize.

### 1.2 The drag is written out four times

`_bind_drag_widgets` / `_start_row_drag` / `_finish_row_drag` /
`_is_descendant`, same four files, same shape: bind the press on the row and
its chips, bind the release on the **toplevel**, and on release ask whether
the pointer is inside the right panel — calling that screen's own assign
method if it is. `_bind_drag_widgets`, `_start_row_drag` and `_is_descendant`
are byte-identical across all four, measured; `_finish_row_drag` differs only
in the body of its final `if`.

**One correction to what this section claimed when it was drafted.** It said
"press/motion/release on the row and its chips". Only the press is on the row.
The release is on the toplevel, because the pointer has left the row by the
time it is let go and the drop target is a different widget entirely. And
there is **no motion handler anywhere** — nothing is drawn while the row is
being dragged, on any of the four. UPD-M2.1's wording inherited the error and
is corrected with it in §3.

### 1.3 The chip table is written out five times

`_render_rows` (three files), `_render_left_rows` + `_render_right_rows`
(`weekly_items.py`), and three similar blocks in `vision_segments.py`. Each
builds its own header frame, its own `grid_columnconfigure(minsize=…)` calls
and its own chip labels. Widths are a local `col_widths` dict in three files
and class constants (`INDEX_COL_WIDTH`, `SEGMENT_COL_WIDTH`, …) in
`weekly_items.py`.

### 1.4 Where APE Week Assignment differs from the image

*As the screen stood when this spec was written. All three are closed at
UPD-M5 — see §10.*

It has the divider, the drag and the chips, so at a glance it is close. Three
differences:

- the **right panel is not a table in the same shape**. Its rows are chips in
  a bordered frame with a selection tint, and its actions are three buttons in
  a bar *below* the list — `Edit Weekly Tactic`, `Delete Weekly`,
  `Add Action Item` (`weekly_items.py:161-173`) — where the image has a Delete
  button in an Actions column on each row.
- the **left header says "Pick"** over the checkbox column; the image's left
  header has an empty cell there.
- the **widths are class constants**, so the two panels on this one tab cannot
  be given different widths, and the numbers differ from the other tabs'.

### 1.5 Where APE Week Actions differs

**All five differences below are closed at UPD-M6** — this section is the
before state, kept for the record. §10's UPD-M6 block has what each became.

It was built to a different brief three commits ago and does not follow this
design at all:

- no divider. The body is `minsize=380` on the left and `weight=1` on the
  right (`week_actions.py:LEFT_PANE_MIN_WIDTH`), so the split is not the
  user's to set.
- the left list is a stack of `CTkButton`s, one per tactic, not a table with
  chips.
- no Segment / SubSegment / Category filter combos, which the other five tabs
  all have.
- no drag.
- its right panel is a `TodayScreen` subclass and therefore **already has**
  draggable, persisted column widths, through `ColumnResizer` with the prefix
  `week_actions`. It is the only panel in the hub that has them.

### 1.6 The mechanism point 5 needs already exists

`screens/column_resize.py` (196 lines) is exactly the asked-for behaviour:
`ColumnSpec` per column with default/min/max, a draggable handle at each
column's right edge, live re-clamping of cell text, and persistence to
`AppSettings.<prefix>_col_widths`. It is used by `today.py` and
`drag_schedule.py`, and its `set_cell_width=True` mode exists for
"solid-colour pill labels" — which is what the APE chips are. Nothing new has
to be invented for point 5; it has to be *adopted*.

---

## 2. Decisions this spec makes

**D1 — consolidate first, then apply.** Three shared modules, extracted from
the existing four copies with no behaviour change, then adopted by each tab one
at a time. Copying the design a fifth and sixth time would leave six copies of
a splitter to keep in step, and the standing rule is that two owners of one
rule is how a defect starts. This is the bulk of the work and most of the risk.

**D2 — the shared modules are:**

- `screens/split_panel.py` — the divider: ratio state, press/drag/release,
  min-width clamping, re-apply on resize. Takes the body frame and the two
  column indices; owns nothing else.
- `screens/row_drag.py` — bind a row's widgets as a drag source, test the drop
  on release, call back into the screen.
- `screens/chip_table.py` — the header + chip rows, driven by a column spec
  list and a `ColumnResizer`.

**D3 — column widths come from `ColumnResizer`, one per panel.** Each panel
gets its own prefix, so the left and right panel of a tab resize
independently, and a tab's widths do not move another tab's. Nine new prefixes:
`annual_ape_left/right`, `ape_quarter_left/right`, `ape_month_left/right`,
`ape_week_left/right`, `week_actions_left` — Vision Elements is out of scope
per D8, so it gets none. The right
panel of Week Actions keeps its existing `week_actions` prefix untouched —
renaming it would silently discard the widths a user has already set.

**D4 — the split ratio persists too.** It is the same class of state as a
column width and it is odd to keep one and discard the other. One new
`AppSettings` field per screen, same naming (`<prefix>_split_ratio`). This is
beyond the literal ask; it is one line per screen and it is what "resizing"
implies to anyone who drags a divider twice.

**D5 — APE Week Assignment's right panel becomes a table in the image's
shape**: `#` / Segment / SubSegment / Category / Actions, with the row's
Delete in the Actions column. `Edit Weekly Tactic` and `Add Action Item` stay
as buttons below the list, because they act on the *selected* tactic and have
no per-row equivalent in the image. Row selection and double-click-to-open
stay as they are.

**D6 — APE Week Actions gets the divider, the chip table on the left, and the
filter combos; it does not get the drag.** Dragging a tactic from the left
panel onto the right would have to mean something, and on this tab the right
panel is the *contents* of whatever is selected on the left, not a second
collection you can add to. There is nothing for a drop to do. Clicking a
tactic is the interaction, and the empty-state text already says so. This is
the one place where "the same overall design" cannot be taken literally, and
pretending otherwise would mean a drop target that silently does nothing.

**D7 — the right panel of APE Week Actions stays a `TodayScreen` subclass.**
It already has the asked-for column resizing, and AWA-M5.3 requires its rows
to be Today's rows. Turning it into a chip table would undo the feature that
was just built and asked for ("the Action Items panel on the RIGHT should work
like the Today tab"). So on this one tab the two panels are deliberately not
the same kind of table: the left lists tactics, the right is Today, filtered.

**D8 — `vision_segments.py` (Vision Elements) is out of scope.** It is not a
two-panel screen and making it one is a redesign of that tab, not an
alignment. It is listed in §1 for completeness and named in §6.

---

## 3. Acceptance criteria → tests

Every criterion below is checkable by an automated test except the two marked
**on screen**, which go on a checklist for the user, the way AWA's did.

### UPD-M1 — one splitter, not four

| ID | Criterion | Test |
|---|---|---|
| M1.1 | `screens/split_panel.py` exists and owns the ratio, the clamp and the three event handlers | `test_updm11_split_panel_module_owns_the_divider` |
| M1.2 | Dragging right past the midpoint widens the left panel and narrows the right by the same pixels | `test_updm12_drag_moves_both_panels_by_the_same_amount` |
| M1.3 | The ratio is clamped so neither panel goes below its minimum, at any body width | `test_updm13_neither_panel_can_be_crushed` |
| M1.4 | A body width of 0 or less is a no-op, not a crash or a divide-by-zero | `test_updm14_zero_width_body_is_a_noop` |
| M1.5 | No screen file defines `_apply_split_ratio`, `_on_divider_drag` or `SPLITTER_WIDTH` of its own — counted from the AST, exact count 0 | `test_updm15_no_screen_keeps_its_own_splitter` |
| M1.6 | The ratio persists: set it, rebuild the screen from saved settings, get it back | `test_updm16_split_ratio_survives_a_relaunch` |

### UPD-M2 — one row-drag, not four

| ID | Criterion | Test |
|---|---|---|
| M2.1 | `screens/row_drag.py` binds the press on every widget it is given, and the release on the toplevel. **Corrected from "press/motion/release on every widget"**, which none of the four copies did and nothing needs: there is no motion handler and no drag ghost — see §1.2 | `test_updm21_every_widget_in_the_row_is_a_drag_handle` |
| M2.2 | A release inside the target calls the screen's handler once, with the row | `test_updm22_drop_inside_the_target_assigns_once` |
| M2.3 | A release outside the target calls nothing | `test_updm23_drop_outside_the_target_does_nothing` |
| M2.4 | A release with no drag in progress does nothing (P7: the "looks right but is wrong" input) | `test_updm24_release_without_a_press_does_nothing` |
| M2.5 | No screen file defines `_start_row_drag` or `_is_descendant` of its own — exact count 0 | `test_updm25_no_screen_keeps_its_own_drag` |

### UPD-M3 — one chip table, with resizable columns

| ID | Criterion | Test |
|---|---|---|
| M3.1 | `screens/chip_table.py` renders a header and N rows from a column spec list | `test_updm31_table_renders_header_and_rows` |
| M3.2 | Every resizable column has a divider handle in the header | `test_updm32_every_resizable_column_has_a_handle` |
| M3.3 | Dragging a column handle changes that column's width and no other's | `test_updm33_resizing_one_column_leaves_the_others` |
| M3.4 | A width is clamped to the column's min and max | `test_updm34_column_width_is_clamped` |
| M3.5 | Chip text is re-clamped to the new width, so a narrowed column does not overflow its pill | `test_updm35_chip_text_follows_the_column_width` |
| M3.6 | Widths persist per panel prefix, and two panels with different prefixes do not share | `test_updm36_panels_keep_their_own_widths` |
| M3.7 | A row with an empty segment / subsegment / category renders without raising | `test_updm37_missing_lineage_does_not_raise` |

### UPD-M4 — the four existing tabs keep their behaviour

The consolidation must not change what these screens do. The existing tests for
each stay green unchanged, and one characterisation test per screen pins the
layout it had before the change.

| ID | Criterion | Test |
|---|---|---|
| M4.1 | `annual_vision_segments`, `ape_assignment`, `ape_period_view` each still build two panels, a divider and the same column order | `test_updm41_<screen>_layout_is_unchanged` (3 tests) |
| M4.2 | Their existing test files pass unchanged | the files themselves, run and recorded |
| M4.3 | Assign-by-drag still assigns on all three | `test_updm43_drag_still_assigns_on_each_tab` |
| M4.4 | Each panel's columns are now resizable and persist | `test_updm44_<screen>_columns_resize` (3 tests) |

### UPD-M5 — APE Week Assignment matches the image

| ID | Criterion | Test |
|---|---|---|
| M5.1 | The right panel renders a header of `#`, Segment, SubSegment, Category, Actions | `test_updm51_right_panel_has_the_actions_column` |
| M5.2 | Each right row carries a Delete button that deletes that row's tactic | `test_updm52_row_delete_removes_that_tactic` |
| M5.3 | Delete asks first, and a refused confirmation deletes nothing | `test_updm53_delete_is_confirmed_before_it_happens` |
| M5.4 | `Edit Weekly Tactic` and `Add Action Item` still act on the selected tactic | `test_updm54_selection_buttons_still_work` |
| M5.5 | The left header's first cell is empty, not "Pick" | `test_updm55_left_header_matches_the_other_tabs` |
| M5.6 | Both panels use the shared table, with their own prefixes | `test_updm56_week_assignment_uses_the_shared_table` |
| M5.7 | Selection tint and double-click-to-open survive the rewrite | `test_updm57_selection_and_double_click_survive` |

### UPD-M6 — APE Week Actions gets the design it can take

| ID | Criterion | Test |
|---|---|---|
| M6.1 | The body has a draggable divider between the tactic list and the Actions panel | `test_updm61_week_actions_has_a_divider` |
| M6.2 | The left panel is the shared chip table, not a stack of buttons | `test_updm62_left_panel_is_the_shared_table` |
| M6.3 | Clicking a left row still selects that tactic and reloads the right panel | `test_updm63_clicking_a_row_still_selects` |
| M6.4 | The tab has Segment / SubSegment / Category filters, and they filter the left list | `test_updm64_filters_narrow_the_tactic_list` |
| M6.5 | A filter that matches nothing says so and says how many were hidden (P2) | `test_updm65_an_empty_filter_result_says_what_it_hid` |
| M6.6 | The right panel is still a `TodayScreen` subclass and still keeps the `week_actions` prefix, so widths set before this change are not lost | `test_updm66_right_panel_is_untouched` |
| M6.7 | No drop target is created on this tab (D6), and nothing binds a drag source in it — exact count 0 | `test_updm67_no_dead_drop_target` |

### UPD-M7 — it holds together on screen

| ID | Criterion | Test |
|---|---|---|
| M7.1 | Every screen touched still constructs withdrawn, and the mapped-window count in `test_ci_contract.py` is unchanged | `test_updm71_screens_construct_withdrawn` |
| M7.2 | **on screen** — the six tabs read as one design: same header card, same divider, same row height, same chip style | user checklist |
| M7.3 | **on screen** — a dragged column divider moves only its own column, in both panels, on every tab, and the width is still there after a relaunch | user checklist |

---

## 4. Implementation order

Each step is a commit, tests first, and each leaves the app working.

1. **UPD-M3 first, on one panel.** Build `chip_table.py` and prove it against
   `ape_assignment.py`'s left panel only. This is where the risk is: chips are
   fixed-width coloured labels and the resizer's `set_cell_width` path has
   only ever driven the Scheduler's pills. If this does not land cleanly,
   everything after it changes shape, so it goes first.
2. **UPD-M1** — `split_panel.py`, adopted by `ape_assignment.py`. One screen,
   so the diff is readable.
3. **UPD-M2** — `row_drag.py`, adopted by `ape_assignment.py`.
4. **UPD-M4** — roll all three modules through `ape_period_view.py` and
   `annual_vision_segments.py`, and `chip_table.py` through
   `ape_assignment.py`, which UPD-M3 built the table for but did not move
   onto it. Delete the duplicates as each adopts.

   **This step does not empty UPD-M1.5's or UPD-M2.5's holdout set**, which
   §10's UPD-M1 block and the two guard tests said it would. The fourth copy
   of each is in `weekly_items.py`, and that screen is rewritten at UPD-M5,
   not here. Both criteria stay `partial` until then.
5. **UPD-M5** — APE Week Assignment, including the right-panel rewrite.
   This is the step that empties both holdout sets and closes UPD-M1.5 and
   UPD-M2.5.
6. **UPD-M6** — APE Week Actions: divider, chip table, filters.

   This step was not repetition either. The tab needed two rules it did not
   have — the filter triple and the category chip colour — and both were
   already written out five times under `screens/`. They moved into
   `screens/lineage_filters.py` and two new functions in
   `screens/segment_color_utils.py` as they were adopted, rather than becoming
   a sixth copy each (UPD-D1). `weekly_items.py` was moved onto all three
   seams in the same change, because it is the other screen this batch owns.
   The five remaining copies are UPD-A9, not swept here.
7. **UPD-M7** — the meta test, the docs, the on-screen checklist.

Steps 1-3 are the ones worth pausing after; from step 4 on it is repetition.

Step 4 turned out not to be pure repetition: adopting the table surfaced two
defects in UPD-M3's own config and closed the two findings
(`BACKLOG.md`'s AWA-S5 and AWA-S6) that were filed to be settled before the
first screen moved onto it. See §10.

---

## 5. Risks

- **The biggest file in the batch is the one being deleted from.** Four
  screens lose 80-120 lines each and gain an import. A characterisation test
  per screen (UPD-M4.1) is written **before** its first line is removed, or
  there is nothing holding the layout in place while it changes.
- **Chips are width-sensitive in a way Today's labels are not.** A chip is a
  solid-colour pill whose fill is the column width; clamping its text is not
  the same as clamping a transparent label's. `set_cell_width=True` exists for
  this, but it has one caller today.
- **`weekly_items.py`'s right panel is a behaviour change, not a move.** Rows
  gain a Delete they did not have, and a `Delete Weekly` button that acts on
  the selection stays beside it. Two ways to delete the same thing is a
  reasonable thing to get wrong; M5.2 and M5.4 both have to pass.
- **This batch touches `week_actions.py` and `weekly_items.py`**, the two files
  the unpushed AWA batch just created and changed. See §7.
- **`test_ci_contract.py` pins the mapped-window count at 22.** Any new test
  that builds a real window moves it, and the pin is asserted against the
  suite, so it cannot drift silently — it will simply go red.

---

## 6. Adjacent issues found, not fixed

- **UPD-A1 — `vision_segments.py` is the odd one out.** Three fixed-width
  column blocks, no panels, no divider. Bringing it in is a redesign of that
  tab rather than an alignment, and nothing in the request named it.
- **UPD-A2 — withdrawn, it was a misreading.** All four screens declare
  `MIN_PANEL_WIDTH = 420`; the 520 is the initial `minsize` on each panel
  column, which the first resize overwrites. There was no number to reconcile,
  and `split_panel.py` carries the 420 the four agreed on. See §1.1.
- **UPD-A3 — the split ratio has never persisted on any tab.** Fixed by D4
  rather than recorded, because it is one field per screen and the request
  says "resizing", which nobody means once-per-launch.
- **UPD-A5 — `project_boards.py` holds a fifth copy of the splitter, with a
  better clamp than the four this spec consolidates.** `:772-1126`:
  `MIN_PANEL_WIDTH = 300`, a 0.6 default, the apply inlined into
  `_on_body_resize`, and `right = max(MIN_PANEL_WIDTH, total - left)` — which
  is the line the four were missing (see UPD-M1.3 in §10). Not fixed, because
  Project Boards is not a VSP tab and bringing it in is a change to a screen
  nothing in the request named; sweeping it in on the back of this work is the
  silent-wide-diff the standing rule forbids. Recorded in `BACKLOG.md`, and
  pinned by `test_updm15_no_screen_keeps_its_own_splitter`, which asserts
  exactly what that file still defines, so it cannot be forgotten and cannot
  quietly grow a sixth variant.
- **UPD-A4 — `drag_schedule.py` and `today.py` have the only two
  `ColumnResizer` callers today**, and both predate this. If the chip-table
  work changes `column_resize.py` at all, those two screens are in the blast
  radius and their test files run in the same batch.

---

## 7. Sequencing against the unpushed AWA batch

There are 14 unpushed commits on `main`: the AWA batch (10, mine) and the
Plan / Day Plan batch (3, from the other session), plus one docs commit. The
AWA batch has **not been swept and has not been seen on screen** — the sweep
was started and stopped so the on-screen check could happen first.

This plan edits `week_actions.py` and `weekly_items.py`, which AWA created and
changed. Two options, and they are the user's call:

- **Sweep and push AWA first, then start this.** The sweep diff is already
  built and the three passes are ready to relaunch. This plan then starts from
  a pushed, reviewed base, and its own diff is only its own.
- **Fold this into the AWA batch.** Fewer pushes, but the sweep then covers
  two features at once, and the AWA on-screen checklist is partly invalidated
  before anyone walks it — steps 3, 4, 5 and 9 all describe a left panel this
  plan replaces.

**Recommendation: push AWA first.** The on-screen checklist is the only thing
standing between that batch and a claim it works, and this plan would rewrite
the screen it checks.

---

## 8. Files this will touch

| File | Change |
|---|---|
| `src/getmoredone/screens/split_panel.py` | **new** — the divider |
| `src/getmoredone/screens/row_drag.py` | **new** — the drag source and drop test |
| `src/getmoredone/screens/chip_table.py` | **new** — header + chip rows over `ColumnResizer` |
| `src/getmoredone/screens/ape_assignment.py` | adopt all three; delete the three copies |
| `src/getmoredone/screens/ape_period_view.py` | same |
| `src/getmoredone/screens/annual_vision_segments.py` | same |
| `src/getmoredone/screens/weekly_items.py` | same, plus the right-panel rewrite (UPD-M5) |
| `src/getmoredone/screens/week_actions.py` | divider, chip table, filters (UPD-M6) |
| `src/getmoredone/screens/lineage_filters.py` | **new at UPD-M6** — the Segment / SubSegment / Category filter triple |
| `src/getmoredone/screens/segment_color_utils.py` | at UPD-M6, `load_category_color_map` and `resolve_chip_colors` |
| `src/getmoredone/app_settings.py` | 9 new `<prefix>_col_widths` fields, 5 `<prefix>_split_ratio` fields |
| `tests/test_unified_panel_design.py` | **new** — UPD-M1 … UPD-M7 |
| `tests/test_ci_contract.py` | only if the mapped-window count moves |
| `docs/`, `NOTES.md`, `CHANGELOG.md`, `BACKLOG.md` | last step |

Expect the three new modules at roughly 120 / 80 / 200 lines, and each adopting
screen to **lose** 80-120. `codex.md`'s maintainability policy is read before
`chip_table.py` is written, since it is the one that could grow.

---

## 9. What this plan does not do

- It does not touch Vision Elements (D8, UPD-A1).
- It does not add a drag to APE Week Actions (D6) — there is nothing for a drop
  to mean there.
- It does not turn the APE Week Actions right panel into a chip table (D7); it
  stays the Today list, which is what the previous request asked for.
- It does not change what any tab *does* — what is assigned, saved, deleted or
  filtered is the same before and after, except for UPD-M5's new per-row
  Delete.

---

## 10. Status, criterion by criterion

### UPD-M1 — one splitter, not four — **done**, with one criterion partial

| ID | Status | Evidence |
|---|---|---|
| M1.1 | done | `src/getmoredone/screens/split_panel.py`; `tests/test_unified_panel_design.py::test_updm11_split_panel_module_owns_the_divider` |
| M1.2 | done | `::test_updm12_drag_moves_both_panels_by_the_same_amount` — 60px right is +60 left and -60 right, and the press is asserted to have captured the panel's applied width |
| M1.3 | done | `::test_updm13_neither_panel_can_be_crushed` — three roomy widths × six ratios, both drag edges, and three bodies too narrow to seat two minimums |
| M1.4 | done | `::test_updm14_zero_width_body_is_a_noop` |
| M1.5 | **done at UPD-M5** | `::test_updm15_no_screen_keeps_its_own_splitter`. `ape_assignment.py` adopted at UPD-M1, `ape_period_view.py` and `annual_vision_segments.py` at UPD-M4, `weekly_items.py` at UPD-M5, so `SPLITTER_HOLDOUTS` is empty and the guard asserts it. The only file left with a splitter is `project_boards.py`, which is out of scope by UPD-A5 and is named in `SPLITTER_OUT_OF_SCOPE`. The §4 claim that UPD-M4 would close this was wrong, and is corrected there. |
| M1.6 | done | `::test_updm16_split_ratio_survives_a_relaunch`, `::test_updm16_the_ratio_has_a_settings_field_to_land_in`, `::test_updm16_a_prefix_with_no_settings_field_says_so` |

**One deliberate behaviour change, against D1's "no behaviour change".** M1.3
says "at any body width", and the four copies did not hold that: they clamped
the left panel only and gave the right whatever was left, so on a body under
`2 * MIN_PANEL_WIDTH` the right panel went below the minimum, and under
`MIN_PANEL_WIDTH` it took a **negative** grid minsize. Tk accepts a negative
minsize silently — measured, not assumed — which is why it survived four
copies and a fifth already holding it (UPD-A5). `apply()` now holds both sides
and lets the body overflow instead, which is what a minimum means. A mutation
removing the `max` turns `test_updm13` red.

**One claim not made.** The extraction was checked for identity before it was
written: `diff` across the four `_on_body_resize … _apply_split_ratio` blocks
is byte-identical, so "no behaviour change" is measured for the arithmetic
rather than asserted. The two differences above are the two exceptions, both
named.

**Mutation gate:** 8, each the verbatim original, each run alone, every file
restored and sha256-compared. 8 red.

**Verified on screen 2026-11-08**, by the §11 walk. UPD-M1's divider drags and
does not crush either panel (step 7). Its persistence does **not** hold: step
10 found no divider position surviving a relaunch, which is UPD-F1. Until that
is fixed, the persistence this module's tests assert is proved only against a
withdrawn root, which is exactly where the fault hid.

### UPD-M2 — one row-drag, not four — **done**, with one criterion partial

| ID | Status | Evidence |
|---|---|---|
| M2.1 | done | `src/getmoredone/screens/row_drag.py::RowDragSource.bind_row`; `::test_updm21_every_widget_in_the_row_is_a_drag_handle`. The criterion's wording is corrected in §3 and §1.2: the press is per widget, the release is the toplevel's, and there is no motion handler. |
| M2.2 | done | `RowDragSource.finish`; `::test_updm22_drop_inside_the_target_assigns_once` (one call, one row, and a second release with no press adding nothing), plus `::test_updm22_the_quarter_screen_routes_its_drop_through_the_module` for the real screen's wiring |
| M2.3 | done | `::test_updm23_drop_outside_the_target_does_nothing` — over another widget, and over nothing at all, which is the `None` `winfo_containing` returns past the window edge |
| M2.4 | done | `::test_updm24_release_without_a_press_does_nothing`, asserted with the pointer *inside* the target so the drop test cannot be what saves it, plus `::test_updm24_is_descendant_walks_up_and_stops` |
| M2.5 | **done at UPD-M5** | `::test_updm25_no_screen_keeps_its_own_drag`. Nothing under `screens/` defines `_start_row_drag` or `_is_descendant` any more, so this is a plain emptiness assertion with no out-of-scope file beside it — `project_boards.py` has a splitter but never had a row drag. |

**No behaviour change.** Unlike UPD-M1 this extraction carries none: the three
identical methods moved as they were, and `finish` keeps the original order —
guard, read the pointer, clear the row, test the drop.

**One test moved rather than deleted**, case (b): the behaviour did not
change, the method it lives in did.
`tests/test_ape_period_consistency.py::test_apcm62_quarter_drag_path_reaches_the_same_reporting`
drove `_finish_row_drag` through a stub carrying six members that existed only
to fake the drag machinery. It drives `_assign_dragged_row` now, and UPD-M2.2
owns the claim that a release inside the panel reaches that method once.

**Two mutations came back green, and both were findings about the tests.**

- `test_updm21`'s docstring claimed the lambda's `r=row` default guards
  against the late-binding trap. It does not: `bind_row` loops over the
  *widgets*, and `row` is the call's own parameter, so each call already
  closes over its own row. Removing the default left the test green. The
  docstring now says so and names the two mutations that do turn it red, and
  the module says the default is kept for intent rather than effect.
- Dropping `refresh_lists()` from `_assign_dragged_row` left every assertion
  in APC-M6.2 green. A refused assignment must still redraw — the weekly
  screen's test says exactly that in words ("used to refresh only when
  something was created") and this screen's sibling had no assertion for it
  (P5). The gap predates UPD-M2; it is closed now.

**Mutation gate:** 9, each the verbatim original, each run alone, every file
restored and sha256-compared. 9 red, after the two greens above were resolved
— one by correcting a false docstring claim, one by adding the missing
assertion.

**Not verified on screen.** The drop test cannot be driven with real widgets
at all: `winfo_pointerxy` reads the real mouse, so where the pointer happens
to be when the suite runs is not an input a test may depend on. M2.1 - M2.4
are proved against doubles, M2.2 has one real-screen wiring test, and whether
a drag actually assigns on screen is still UPD-M7.2/M7.3.

### UPD-M3 — one chip table — **built, adopted by nothing**

`chip_table.py` exists with all seven criteria tested
(`::test_updm31` … `::test_updm37`), and its own docstring opens by saying
nothing uses it yet — which stopped being true at UPD-M4, where six panels
across three screens adopted it and that docstring was rewritten. Two findings
from its review are
filed under the batch it shipped in, as `BACKLOG.md`'s **AWA-S5** (a chip's
text is clamped to the column width, not to the pill) and **AWA-S6** (five
lifecycle assumptions its API does not enforce). Both are named there as things
to settle before UPD-M4 moves the first screen onto the table. Both were
settled at UPD-M4: AWA-S5 fixed in `column_resize.py`, four of AWA-S6's five
enforced and the fifth stated in the class docstring. See the UPD-M4 block.

### UPD-M4 — the three tabs, on the shared modules — **done**, with two criteria qualified

| ID | Status | Where |
|---|---|---|
| M4.1 | `done` | 12 characterisation tests, `::test_updm41_*`. The six for APE Month and Annual were written and green **against the untouched screens** before a line of either was removed, which is what §5's first risk asked for. |
| M4.2 | **`partial`** | Every existing test file of the three screens passes, but one test in `tests/test_ape_period_consistency.py` was changed: `::test_apcm23_drag_path_reaches_the_same_reporting` drove `_finish_row_drag`, which no longer exists on the screen. Case (b), the behaviour moved; it drives `_assign_dragged_row` now, exactly as its APE Quarter sibling did at UPD-M2, and it gained the same `refresh` assertion. "Unchanged" is therefore false and recorded as such. |
| M4.3 | `done` | `::test_updm43_a_drop_assigns_on_each_tab` and `::test_updm43_a_drop_outside_the_target_assigns_nothing_on_each_tab`. One drop per tab through that screen's own `RowDragSource`, asserted against the call the manager got — three different methods with three different argument shapes, so a drop wired to the wrong one cannot pass by accident. |
| M4.4 | `done` | `::test_updm44_<screen>_columns_resize_and_persist` (3), plus `::test_updm44_every_panel_prefix_has_a_settings_field` and `::test_updm44_the_panels_a_screen_builds_use_those_prefixes`. None of the three tabs had resizable columns before this step. |
| M1.5 | **still `partial`** | Only `weekly_items.py` is left in `SPLITTER_HOLDOUTS`, and `project_boards.py` in `SPLITTER_OUT_OF_SCOPE` (UPD-A5). |
| M2.5 | **still `partial`** | Only `weekly_items.py` is left in `DRAG_HOLDOUTS`. |

**Two defects in UPD-M3's own config, both found by adoption.**

- `ChipColumn.min_width` defaults to 40, and the checkbox and `#` columns were
  declared 34 wide. `ColumnResizer` clamps a stored width into range, so both
  rendered at 40 and nothing said so. UPD-M4.1's pixel assertion caught it on
  the first run after APE Quarter adopted the table — which is the whole case
  for writing that test before touching the screen.
  `::test_updm31_every_shipped_column_declares_a_width_it_can_have` now holds
  the invariant for every shipped set.
- `APE_COLUMNS` was one six-column set holding both the checkbox column and
  the Actions column. **No panel has both.** A column's grid index is its
  position in the set, so that single set put every column of every panel one
  place to the right of where it is. It is replaced by `APE_LEFT_COLUMNS`,
  `APE_RIGHT_COLUMNS` and `ANNUAL_RIGHT_COLUMNS` — Annual's Actions column is
  140px to the APE tabs' 84, because it holds Edit as well as Delete.

**AWA-S5 and AWA-S6, the two findings filed to be settled before the first
screen adopted the table.**

- **AWA-S5 — fixed, and in `column_resize.py` rather than around it.** A chip
  pill is `CHIP_INSET` narrower than its column, but the character budget was
  measured from the column width, so the last character was clipped on every
  chip of every row. `ColumnResizer.chars` and `.cell_text` now take the same
  `width_delta` that `register_row` already took, and `_apply_live` passes it,
  so the render and the live re-clamp agree. `drag_schedule.py` and `today.py`
  pass 0 and are unaffected (UPD-A4) — their pills fill their columns, so
  there was no sibling to fix (P5 checked, not assumed).
- **AWA-S6 — four of five enforced, one settled by stating it.** (b) the
  resizer has `clear_header()` and `ChipTable.clear()` calls it; (c)
  `build_header()` weights the container's column 0, so the `sticky="ew"` on
  the header and every row has something to stretch into; (d) `add_row` before
  `build_header` raises instead of gridding the first row at row 1; (e)
  `values` naming no column of the table raises instead of appending an
  invisible zero-height row. (a) is **not changed**: `clear()` destroys every
  child of its container, which is what all six adopting panels need, and the
  constraint — the table owns its container, nothing else may be gridded into
  it — is stated in the class docstring instead. Changing it to destroy only
  the table's own widgets would leave a stale label behind for a screen that
  added one, which is the worse failure.

**Gate.** 13 mutations, each the verbatim original, each run alone, every file
restored and sha256-compared: 13 red, first pass.

**Not verified on screen.** Every test here builds its screens on a withdrawn
root. Three tabs changed their renderer, their splitter and their drag in one
step and none has been looked at. UPD-M7.2 and UPD-M7.3 are the on-screen
criteria and are open.

**Two cosmetic changes, stated because nothing pins them.** The header's blank
checkbox cell is gridded with `padx=5` where the screens used `padx=2`, a 3px
shift; and a clipped chip ends in `...` where the screens' own `_clip_label`
used `…`, because the shared table clamps through
`title_format.format_column_text`, as Today and the Scheduler do. Chip text
also now follows the column width rather than a fixed 15 characters, which is
UPD-M3.5 working as specified: at the default widths SubSegment shows 17
characters where it showed 15, and Category 14.

### UPD-M5 — APE Week Assignment matches the image — **done**

| ID | Status | Where |
|---|---|---|
| M5.1 | `done` | `::test_updm51_right_panel_has_the_actions_column`. The right panel had four columns and three buttons in a bar below the list; it has five columns now, with the row's Delete in the Actions one. |
| M5.2 | `done` | `::test_updm52_a_row_delete_removes_that_row_not_the_selection`. Driven with a *different* row selected, because a per-row button wired to `delete_selected_weekly_item` would look right and delete the wrong tactic. |
| M5.3 | `done` | `::test_updm53_delete_is_confirmed_before_it_happens`, which refuses the confirmation from both entry points and asserts nothing was deleted. |
| M5.4 | `done` | `::test_updm54_the_selection_buttons_act_on_the_selection` and `::test_updm54_delete_weekly_still_deletes_the_selection`. |
| M5.5 | `done` | `::test_updm55_left_header_matches_the_other_tabs`, asserted as text *and* pixels: a cell that was merely blanked would leave every row's cells one place to the right of the other tabs'. |
| M5.6 | `done` | `::test_updm56_week_assignment_uses_the_shared_table_and_module_wiring`, `::..._columns_resize_and_persist`, `::..._the_week_assignment_prefixes_have_settings_fields`, `::..._a_left_row_is_a_drag_source_on_this_tab_too`, `::..._both_panels_still_say_when_they_are_empty`, `::..._a_row_with_no_category_colour_takes_the_subsegments`. |
| M5.7 | `done` | `::test_updm57_clicking_a_right_row_selects_it_and_double_click_opens_it` and `::test_updm57_selecting_a_row_repaints_the_panel_instead_of_stacking_it`. |
| M1.5 | **closed here** | `SPLITTER_HOLDOUTS` is empty. |
| M2.5 | **closed here** | `DRAG_HOLDOUTS` is empty, and so is the AST result. |

**A defect in the screen as it stood, found while writing UPD-M5.7's test.**
`on_select_weekly_item` re-rendered the right panel to move the selection
tint, and did so **without destroying what was already there**:
`_render_right_rows` gridded a fresh header and a fresh set of row frames into
the same cells as the old ones, and only `_render_lists` ever cleared the
panel. Two widgets gridded into one cell both stay mapped, so the newest set
was drawn on top and the screen looked right while every click added another
full set — three clicks on a two-row week took the panel from 3 children to
12. The shared table clears its container in `build_header`, so adopting it is
the fix; the test counts the children rather than trusting that, and it was
written and proved red against the old screen first.

**The two spec statements about `Delete Weekly` disagreed.** §2's D5 lists
`Edit Weekly Tactic` and `Add Action Item` as the buttons that stay, "because
they act on the selected tactic and have no per-row equivalent in the image",
which reads as removing `Delete Weekly` now that the row has its own Delete.
§5's risk list says the opposite in as many words: the button "stays beside
it", and "M5.2 and M5.4 both have to pass". M5.4, the criterion, names only
Edit and Add, so it settles nothing. **Resolved by keeping the button**, for
two reasons: §5 is the explicit statement where D5 is an implication, and
removing a working button from a screen the user uses is the one reading that
cannot be undone by a later step. The risk §5 named — two ways to delete the
same thing — is handled by making them one method, `delete_weekly_row`, with
two callers: the row's button passes its own row, `delete_selected_weekly_item`
passes the selection, and the confirmation exists once.
`::test_updm53_delete_is_confirmed_before_it_happens` drives both callers for
that reason.

**The three differences §1.4 listed are all closed.** The right panel is a
table in the image's shape; the left header's first cell is empty; and the
widths are no longer class constants — each panel has its own store
(`week_assignment_left_col_widths`, `week_assignment_right_col_widths`) and
every column is draggable. The numbers are the other APE tabs' now: 34 / 34 /
135 / 155 / 125 on the left and 34 / 135 / 155 / 125 / 84 on the right, where
this screen used 52 for the "Pick" column and 180 for all three names. That
is a visible change to column widths on this tab, and it is the alignment the
request asked for rather than a side effect.

**Gate.** 17 mutations, each the verbatim original, each run alone, every file
restored and sha256-compared: 15 red on the first pass, 2 green. Both green
ones were findings about the tests, not the code, and both tests were
strengthened until the mutation was red:

- The empty-state test read the label's *text*, and the labels are built in
  `create_ui` and only gridded or un-gridded as the panel fills — so swapping
  the two branches of `_show_list_or_message` left it green. It asserts which
  of the two widgets in that grid cell is gridded now, in both the empty and
  the filled case.
- The two-panels-one-store test resized the left panel and read the right
  panel's width in memory. A right table built on the left prefix loads that
  store *before* the drag happens, so it holds the default for the rest of
  the session and the assertion passed. The test rebuilds the screen from the
  same settings now, which is where a shared store shows.

**Two cosmetic changes, stated because nothing pins them.** The left row's
checkbox is `width=20, padx=2` where this screen used `width=30, padx=5`,
matching the other three tabs; and a clipped chip ends in `...` rather than
`…`, and is clipped to the column width rather than to a fixed 18 characters,
for the same reason UPD-M4 recorded.

**Adjacent issues found, not fixed.** `import tkinter as tk` at
`weekly_items.py:10` has no user anywhere in the file and did not before this
step either — recorded as UPD-A8 rather than swept in with a feature change.

**Not verified on screen.** Every test here builds the screen on a withdrawn
root. UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are open.

### UPD-M6 — APE Week Actions gets the design it can take — **done**

| ID | Status | Where |
|---|---|---|
| M6.1 | `done` | `::test_updm61_week_actions_has_a_divider` and `::test_updm61_the_divider_position_survives_a_relaunch`. The body was `minsize=380` on the left and `weight=1` on the right, so the proportion was the layout's; it is `split_panel.SplitPanel` under the `week_actions` prefix now, with the ratio in a declared field. |
| M6.2 | `done` | `::test_updm62_left_panel_is_the_shared_table`, `::test_updm62_a_long_title_is_clipped_to_its_column`, `::test_updm62_a_row_with_no_category_colour_takes_the_subsegments`. The header is `#` / Weekly Tactic / Segment / SubSegment / Category at 34 / 220 / 135 / 155 / 125, and no `CTkButton` is left in the panel. |
| M6.3 | `done` | `::test_updm63_clicking_a_row_still_selects` and `::test_updm63_selecting_a_row_repaints_the_panel_instead_of_stacking_it`. Every cell carries the binding, not just the row frame, and the click is generated on the widget's internal canvas so it is a real event rather than a call to the handler. |
| M6.4 | `done` | `::test_updm64_filters_narrow_the_tactic_list`, `::test_updm64_the_combos_offer_only_the_values_the_week_has`, `::test_updm64_a_filter_that_hides_the_selected_row_clears_the_panel`. |
| M6.5 | `done` | `::test_updm65_an_empty_filter_result_says_what_it_hid` and `::test_updm65_an_empty_week_says_that_instead`. The two cases say different things, and the test asserts which of the two widgets in that grid cell is gridded rather than reading the label's text — that is UPD-M5's finding applied here. |
| M6.6 | `done` | `::test_updm66_right_panel_is_untouched` and `::test_updm66_the_left_panel_columns_resize_and_persist`. The right panel is still a `TodayScreen` subclass on the `week_actions` prefix; the left table has its own `week_actions_left`, so a drag in one panel cannot move the other's columns or read a user's existing widths with the wrong keys (D3). |
| M6.7 | `done` | `::test_updm67_no_dead_drop_target`. Exact count 0, from the AST: no `RowDropTarget`, no `RowDragSource`, no `bind_row` anywhere in the file (D6). |

**The two pins were written first.** §5's first risk says the characterisation
test comes before the first line is removed.
`::test_updm66_right_panel_is_untouched` and `::test_updm67_no_dead_drop_target`
were written against the untouched screen and run green there (2 passed), and
`tests/test_ape_week_actions.py` was baselined at 33 passed, before any edit.
Both still pass.

**Three rules moved out rather than being copied a sixth time.** The tab needed
the Segment / SubSegment / Category filter triple and the category chip colour,
and each was already written out five times under `screens/`:

- `screens/lineage_filters.py` (**new**) owns the three combos, the `All`
  sentinel, the option lists, the predicate and the wording of what is
  filtering. It also owns the two row readers — a Weekly Tactic carries its
  lineage under `ape_*` keys, an Annual Plan Element under `*_name`.
- `screens/segment_color_utils.py` gains `load_category_color_map` (the
  lower-cased three-part key) and `resolve_chip_colors` (the three chip
  colours, with the category falling back to the subsegment's).
- `screens/chip_table.py` gains `show_list_or_message`, the two-widgets-in-one
  -cell rule UPD-M5 wrote inline.

`weekly_items.py` was moved onto all three in the same change: it is the other
screen this batch owns, and leaving it with its own copies would have been the
inconsistent half of the choice. The five remaining copies — `ape_assignment`,
`ape_period_view`, `annual_vision_segments`, `drag_schedule` and
`item_editor_weekly_tactic_dialog` — are **not** changed here and are recorded
as UPD-A9 in `BACKLOG.md`. Two of them fall back differently for a missing
category colour, so reconciling them is a behaviour change on four screens and
not UPD-M6's to make.

**One defect in the shared table, found while writing UPD-M6.2's test.**
`add_row` gave a non-chip cell its raw text while a chip cell was clamped to
its column. On the four tabs that had no plain text column wider than its
content that was invisible; on a Title column it is a panel that opens with
one row pushing every column out of line and corrects itself the moment the
handle is touched. A resizable plain column is clamped in `add_row` now, the
same way the resizer clamps it on a drag. A fixed-width column keeps its raw
text deliberately: `#` and `Actions` cannot overrun, and `_apply_live` never
re-clamps a column with no handle, so clamping them here would be the only
place the pad appeared.

**Four deliberate behaviour changes, stated because they are visible.**

- The left panel's minimum goes 380 to `split_panel.MIN_PANEL_WIDTH` (420),
  which is what the other five tabs use.
- The left list is a table with a Weekly Tactic column where it was one
  two-line button per tactic. Its rows are picked by name on this tab, which
  is why it has a Title column and the other panels do not.
- The three filters are new. This tab was the only one in the hub without
  them.
- The left heading and the status line say "shown of total" **only while a
  filter is narrowing the list**. The unfiltered strings are byte-identical to
  the ones `tests/test_ape_week_actions.py::test_awam43` already asserted, so
  that test still holds the old wording unchanged.

**One test changed, case (b) — the behaviour changed intentionally.**
`test_awam42` asserted `set(screen.tactic_buttons) == {mine.id}`. There are no
buttons any more; it reads `tactic_row_frames`, which is the same claim about
the same rows.

**Gate.** 20 mutations, each the verbatim original, each run alone, every file
restored and sha256-compared: **20 red**, no finding. They cover the clamp and
each column width, the empty-state branch, the filter predicate's `!=` and its
`All` guard, the stale-selection fall-back, `describe`, all three filtered
message branches, the selection-survives-a-filter guard, the per-cell click
binding, the selection tint, the repaint on select, the category colour
fall-back, the splitter's panel, the left table's prefix, the settings field
and the Actions panel's grid column.

**Tests run.** `tests/test_unified_panel_design.py` (79) and
`tests/test_ape_week_actions.py` (33): 112 passed. With
`test_weekly_tactic_schema`, `test_column_resize`, `test_ape_period_consistency`,
`test_settings_isolation`, `test_weekly_item_filters`, `test_weekly_items_title`,
`test_weekly_items_week_options`, `test_no_vacuous_tests`, `test_traceability_refs`
and `test_ci_contract`: 301 passed, 1 skipped, and one failure that was not
this batch's — `test_traceability_refs.py::test_every_referenced_test_name_exists`
was red over nine `Tests:` references in `item_editor.py`,
`item_editor_dialogs.py` and `vps_manager.py` naming WTP tests
(`test_wtpm41_*` … `test_wtpm64_*`) that did not exist yet. Those three files
are untouched by UPD-M6; the WTP batch wrote the tests in `a0fb2d3` and it is
green again, verified here after that commit landed.
`test_release_docs`, `test_vision_planning_regressions` and
`test_weekly_tactic_surfaces`: 75 passed.

**Not verified on screen.** Every test here builds the screen on a withdrawn
root. UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are open.

### UPD-M7 — it holds together on screen — **M7.1 done, M7.2 partial, M7.3 not done**

| ID | Status | Where |
|---|---|---|
| M7.1 | `done` | `::test_updm71_screens_construct_withdrawn` builds all five rewritten screens and asserts that **no `Toplevel` was opened anywhere beneath the root** — a dialog at construction would be a modal thrown over whoever is using the machine, once per test that builds the screen. That count is the failable claim, and it is an exact zero walked to the bottom of each widget tree. The two assertions beside it — the root is withdrawn, the screen is unmapped — are stated in the test as what they are: `conftest.py` withdraws every window at construction and re-withdraws after any `deiconify`, so no change to a screen can turn them red, and `tests/test_tk_offscreen.py` is the guard on that patching rather than this test (P24). `::test_updm71_no_test_here_needs_a_mapped_window` counts the tests in this file that take the `mapped_windows` fixture from the AST: exact 0, so the number `test_ci_contract.py::test_the_documented_mapped_window_count_is_the_real_one` checks is the 22 it was before this plan. |
| M7.2 | `partial` | walked 2026-11-08. Steps 1, 2, 5 and 6 pass. The six tabs do read as one design in header card, divider, row height and chip style — the two exceptions were the filter area, which was one line on Annual Plan Elements and two elsewhere (UPD-F2), and the blank heading over Week Assignment's checkbox column, which should read "Pick" (UPD-F3). **Both are built**; M7.2 stays `partial` until §11 steps 11 and 12 confirm it on screen, since what was walked is not what is now there. |
| M7.3 | `not done` | walked 2026-11-08. Steps 8 and 9 pass: a column drag moves only its own column, in both panels, and the panels keep their own widths. **Step 10 failed at the walk** — nothing survived a relaunch (UPD-F1, **built
afterwards and merged at `2fac9b3`**; the step is owed a re-walk, not a fix). Step 7's divider passes, with a request that the columns rescale with it (UPD-F4, **built**, to be confirmed by §11 step 13). |

**M7.2 and M7.3 are not written as tests, deliberately.** Both are about how
six tabs *read* beside each other, and the thing that would make them
code-testable — comparing rendered geometry across screens — is what the
characterisation tests already do per screen. What is left is the part a
measurement cannot settle: whether the six look like one design at a real
window size, with real data, and whether a width a user set is still there the
next morning. §11 is the checklist for it.

**UPD-M1 through UPD-M6 have now been seen running** — §11 was walked on
2026-11-08, and the verdict per step is in the M7.2 and M7.3 rows above.
Every test in `tests/test_unified_panel_design.py` still builds its screen on
a withdrawn root, which is what keeps a full run off the user's screen and is
why none of them could answer M7.2 or M7.3 in the first place. What the walk
found is four items, `UPD-F1` to `UPD-F4`, in
`docs/implementation_plan_2026-11-08_unified_panel_followups.md`; the one
defect among them is that no column width or divider position survives a
relaunch.

---

### UPD-F1 to UPD-F4 — what the walk asked for — **all four done**

Approved 2026-11-08. The plan, with every criterion and the two corrections
made to it against the code, is
`docs/implementation_plan_2026-11-08_unified_panel_followups.md`.

| ID | Status | Where |
|---|---|---|
| UPD-F1 | `done` | Built on `refs/heads/claude/elegant-neumann-ab55c9` (`31816a0`), merged at `2fac9b3`; `save()` now writes only the fields the object changed, with its `UPD-F1` docstrings at `src/getmoredone/app_settings.py:237`, `:253` and `:417`. The defect was: `AppSettings.save()` writes `asdict(self)`, the whole object, so a screen holding its own snapshot reverts every field another object changed since that snapshot loaded. Not built in this batch — `src/getmoredone/app_settings.py` carries the calendar-export batch's uncommitted hunk, and `CLAUDE.md`'s "One build batch at a time" rules out a second writer in this index. Proposed as its own worktree session. The evidence is in the plan's §2: the demo settings file holds populated widths for two prefixes and empty dicts for five. |
| UPD-F2 | `done` | `self.filter_row`, a frame of its own at header row 2 on all five tabs, holding the three combos at its own row 0; the status line moved to row 3 on the four tabs that have one; Annual Plan Elements' title alone on row 0, its controls on row 1 and an empty frame one combo high on row 2. `::test_updf21_the_filters_are_on_their_own_row`, `::test_updf22_the_header_card_is_three_rows_deep`, `::test_updf23_every_tab_puts_its_filter_row_in_the_same_place`, `::test_updf24_the_tab_with_no_filters_is_the_same_depth`, `::test_updf25_the_status_line_moved_below_the_filters`. 7 of 7 mutations red. |
| UPD-F2.6 | `not done` | On screen. §11 step 11. |
| UPD-F3 | `done` | `ChipColumn("checkbox", "Pick", 34, …)`. The word measures 28px in the bold header font against a 34px column, so no width moved — `::test_updf32_the_pick_column_fits_its_heading_and_has_no_handle` asserts the measurement. Four panels share `APE_LEFT_COLUMNS`, not the three the plan said, and `::test_updf34_every_ape_left_panel_says_pick` pins the adopter list. 6 of 6 mutations red. |
| UPD-F3.5 | `not done` | On screen. §11 step 11. |
| UPD-F4 | `done` | `ColumnResizer.fit_to_width` shares a panel out across its resizable columns by weight, floor `min_column_width()` = 5 × `CHAR_PX` = 40, fixed columns reserved out, and returns the shortfall when a panel cannot seat the floors. `SplitPanel.apply` gained `on_apply(left_px, right_px)`; the five screens pass `chip_table.panel_fitter(...)`. `::test_updf41_a_divider_move_rescales_every_resizable_column` and the five criteria tests beside it. 9 of 9 mutations red. **APE Week Actions' right panel is not fitted** — it is a `TodayScreen` subclass, not a `ChipTable`. |
| UPD-F4.7 | `not done` | On screen. §11 step 13. |

**UPD-F3 reverses the text half of UPD-M5.5.** That step blanked this heading
when the five panels were unified, on the reasoning that a tick column needs
no name. The walk disagreed, and the walk is the authority on how it reads.
The UPD-M5 block above is left as the record of what was done then; this is
what it is now.

---

## 11. The on-screen check — for the user, not for a test

M7.2 and M7.3. Ten steps, in order. Before starting: **quit the packaged app**
if `/Applications/daVIPA.app` is running — a source launch exits silently
while it holds the database lock — then `./start.sh`, and check `app.log` for
a traceback at the end.

**One design (M7.2)**

1. **VSP Plan** in the sidebar. The nav row should show six buttons: Vision
   Elements, Annual Plan Elements, APE Quarter Assignment, APE Month
   Assignment, APE Week Assignment, APE Week Actions.
2. Open each of the last five in turn. Each should show the same shape: a
   header card with its own controls, then two panels side by side with a thin
   rounded divider between them. **Vision Elements is the exception** and
   should still look different — it is out of scope by UPD-D8 (recorded as
   UPD-A1) and was not touched.
3. On those five, compare the row heights and the chips. Segment, SubSegment
   and Category should be coloured pills of the same height and corner radius
   on every tab, and a row should be the same height on all five. A name too
   long for its column should end in `...` rather than spilling into the next
   column or wrapping to a second line.
4. **APE Week Assignment**: the right panel should have five columns ending in
   **Actions**, with a Delete button on each row, and the left panel's first
   column should be a checkbox headed **Pick**. (This step said "a blank
   header — not the word Pick" when it was walked on 2026-11-08. The walk
   asked for the word; UPD-F3 put it there.)
5. **APE Week Actions**: the left panel should be a table — `#`, Weekly
   Tactic, Segment, SubSegment, Category — not a stack of buttons. Clicking
   anywhere in a row, including on a coloured chip, should select that tactic
   and fill the right panel.
6. **APE Week Actions**, the filters: set **Sub** to a value one tactic has.
   The list should narrow, the heading should read "Weekly Tactics (1 of N)",
   and the status line should say how many were hidden and by which filter.
   Set it to a value **no** tactic in that week has: the list should be
   replaced by a line naming the filter and the hidden count, not an empty
   panel. Reset to All and the heading should go back to "Weekly Tactics (N)".

**Widths and dividers (M7.3)**

7. On each of the five tabs, drag the divider between the panels left and
   right. Both panels should move together, neither should be crushed below
   about a third of the window, and the divider should not jump when the
   window is resized. Since UPD-F4 **the columns should move with it** —
   every column except Pick, `#` and Actions should widen and narrow in
   proportion, and none should go below about five characters.
8. On each of the five tabs, drag the **SubSegment** column's right-hand edge
   in the **left** panel. Only that column should change width; the columns
   either side should stay put, and the text in the dragged column should be
   re-clipped as it narrows rather than overflowing its pill.
9. Do the same in the **right** panel of the same tab. The left panel's
   columns should not move — each panel keeps its own widths.
10. Quit the app and start it again. Every divider position and every column
    width from steps 7 to 9 should be where you left it. Then open the
    **Today** screen and check its Title column has not moved: APE Week
    Actions' right panel shares Today's `week_actions` prefix for its own
    columns and must not have taken Today's.

What to watch for, since these are the things no test here settles: columns
crowding or wrapping at the window size you actually use, a header card
overflowing its pane, row heights differing between tabs, a chip colour that
makes its text unreadable, and a divider that snaps back on the first resize
after a relaunch.

**What UPD-F2, UPD-F3 and UPD-F4 ask you to look at (UPD-F2.6, F3.5, F4.7)**

11. **The filter area, UPD-F2.6 and UPD-F3.5.** Open the five tabs in turn.
    Each header card should be three lines: the title, then that tab's own
    controls, then Segment / Sub / Cat on a line of their own, with the status
    line under them. **Annual Plan Elements has no filters** and should carry
    a blank line of the same depth, so the two panels start at the same height
    on every tab — flip between it and APE Quarter and nothing should jump.
    On APE Week Assignment, check that **Pick** reads as a column heading over
    the ticks and not as a button you could press.
12. **At your real window size.** Narrow the window until the header card is
    tight. The three lines should stay three lines — no control should wrap to
    a fourth, and nothing should be clipped by the card's edge.
13. **The columns and the divider, UPD-F4.7.** On each of the five tabs, drag
    the divider slowly from left to right and back. Every chip column should
    grow and shrink with it rather than leaving empty space beside the last
    column, the proportions you set by dragging a column should be kept, and
    no column should shrink past about five characters. Watch for flicker or
    lag while dragging, and for a column heading that clips: "SubSegment" is
    ten characters in a column that can now be five wide, which is a known
    cost of the five-character floor and is recorded in the plan's §8. On
    **APE Week Actions**, the *right* panel's columns are expected **not** to
    move — it is a different table and is out of UPD-F4's scope.
