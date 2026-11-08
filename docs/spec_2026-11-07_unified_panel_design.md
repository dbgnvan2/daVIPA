# Spec + implementation plan — one panel design across the VSP tabs

Status: **approved 2026-11-07. UPD-M3, UPD-M1, UPD-M2 and UPD-M4 built;
UPD-M5 … UPD-M7 outstanding.** Per-criterion status is in §10.
IDs: `UPD-M1` … `UPD-M7`. Use them verbatim in commits, docstrings and test
names.

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
6. **UPD-M6** — APE Week Actions: divider, chip table, filters.
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
| M1.5 | **partial** | `::test_updm15_no_screen_keeps_its_own_splitter`. The guard exists and is exact, but the count is not yet 0: UPD-M1 adopts `ape_assignment.py` alone, per §4 step 2. Two of the three VSP holdouts adopted at UPD-M4, which left `weekly_items.py`; `project_boards.py` is UPD-A5 and stays. **The claim that UPD-M4 would close this was wrong** — `weekly_items.py` is rewritten at UPD-M5, so the criterion closes there. |
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

**Not verified on screen.** Nothing in UPD-M1 has been seen running; M7.2 and
M7.3 are the on-screen criteria and are still open. The divider's persistence
in particular has only been proved against the real screen on a withdrawn
root.

### UPD-M2 — one row-drag, not four — **done**, with one criterion partial

| ID | Status | Evidence |
|---|---|---|
| M2.1 | done | `src/getmoredone/screens/row_drag.py::RowDragSource.bind_row`; `::test_updm21_every_widget_in_the_row_is_a_drag_handle`. The criterion's wording is corrected in §3 and §1.2: the press is per widget, the release is the toplevel's, and there is no motion handler. |
| M2.2 | done | `RowDragSource.finish`; `::test_updm22_drop_inside_the_target_assigns_once` (one call, one row, and a second release with no press adding nothing), plus `::test_updm22_the_quarter_screen_routes_its_drop_through_the_module` for the real screen's wiring |
| M2.3 | done | `::test_updm23_drop_outside_the_target_does_nothing` — over another widget, and over nothing at all, which is the `None` `winfo_containing` returns past the window edge |
| M2.4 | done | `::test_updm24_release_without_a_press_does_nothing`, asserted with the pointer *inside* the target so the drop test cannot be what saves it, plus `::test_updm24_is_descendant_walks_up_and_stops` |
| M2.5 | **partial** | `::test_updm25_no_screen_keeps_its_own_drag`. Same shape as M1.5: the guard is exact and the count is not 0. Two of the three holdouts adopted at UPD-M4; the last, `weekly_items.py`, adopts at UPD-M5, which is where this closes. |

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

### UPD-M5 … UPD-M7 — **not started**
