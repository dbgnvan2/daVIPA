# Plan: Schedule, Projects and Completed resize with the window (SPC)

- Date: 2026-11-15
- Status: **approved and built 2026-11-15**; walk owed (below).
- Screens: Scheduler (`screens/drag_schedule.py`), Project Board
  (`screens/project_boards.py`), Completed (`screens/completed.py`)
- Follows: LSR and LSR2 (Today, Upcoming, All Items, Hierarchical) and SCR
  (the Scheduler's item columns). Same machinery, no new scheme.

## Why

Request (user, 2026-11-15): make the Schedule, Projects and Complete listing
screens fully resizable the way Upcoming is, and make the row of filter
buttons across the top of each wrap to a second line instead of being cut off
on a narrow window.

### Which files these are, and what is actually missing

The sidebar labels map to modules through `app.py:203,213,223`:

| Label | Module | Class |
|---|---|---|
| Schedule | `screens/drag_schedule.py` | `DragScheduleScreen` |
| Projects | `screens/project_boards.py` | `ProjectBoardsScreen` |
| Completed | `screens/completed.py` | `CompletedScreen` |

What each one is missing differs, and two of the three are not what the
request assumes:

- **Schedule** — its five item columns already fill the list and follow the
  window; that was SCR, built and walked 2026-11-14. The gap is the header:
  thirteen fixed-width controls (`drag_schedule.py:157-246`), about 1150 px of
  them, with the slack column at the far right, so the Project filter clips
  off the edge on a narrow window. **Toolbar only** (user's answer, 2026-11-15).
- **Projects** — the Action Items list is not columnar at all
  (`project_boards.py:1490-1535`): each row is a bold title, then one
  two-line string `Status: x | Start: y | Due: z` / `Next: ...`, then three
  buttons. There are no columns to resize. The user chose to **convert it to
  real columns** (2026-11-15). Its header also has two rows of controls and no
  wrap. The left/right split already follows the window (`_apply_split`).
- **Completed** — no column header, no dividers, no fit: Who is a fixed
  110 px, the completed date 150 px, Pri `SCORE_CELL_WIDTH_PX`
  (`completed.py:249-278`). Only the title stretches, and it stretches as a
  raw label with no clamp, so a narrow window clips it mid-word. It was never
  in LSR, LSR2 or SCR.

## Decisions (defaults, each open to change)

- **D1. Completed keeps its own four columns** (user's answer, 2026-11-15):
  Title, Who, Completed, Pri become resizable. No SubSegment or Category
  column is added; the screen gains no content it does not show today.
- **D2. The Projects Action Items list becomes columnar**: Title, Status,
  Start, Due, each resizable. The `Status: … | Start: … | Due: …` string goes
  — those are the columns now, bare values, no prefixes (the LSR2-M8 rule).
  `Next: …` stays, as a second line inside the Title column, cut to that
  column's width like any other cell.
- **D3. `ItemListLayout` takes an explicit column set.** It hard-wires
  Title/SubSegment/Category/Who today (`stretch_specs`), which neither of these
  two screens has. A classmethod `ItemListLayout.custom(owner, settings,
  prefix, columns)` builds the specs from an arbitrary list instead, and
  everything else — the 6-character floor, the 120 ms debounce, the drag
  dividers, heading cutting, the refit after a drag, persistence — is reused
  unchanged. The alternative is a third and fourth copy of the 60 lines
  `drag_schedule.py` already duplicates; the four existing screens keep the
  current constructor and are untouched.
- **D4. Floor of 6 characters at the row font** — `list_floor_px()`, the same
  floor Upcoming uses, on both screens.
- **D5. Default weights = today's widths**, so an unresized list opens as it
  does now: Completed — Title 260, Who 110, Completed 150, Pri
  `SCORE_CELL_WIDTH_PX`; Projects — Title 260, Status 90, Start 90, Due 90.
- **D6. Persistence follows LSR2-D8**: a drag saves weights under
  `<prefix>_col_widths`, loaded as weights. Two new `AppSettings` fields,
  `completed_col_widths` and `project_items_col_widths`. No new scheme.
- **D7. Completed's heading row is pinned; Projects' scrolls.** Completed's
  list is its own `CTkScrollableFrame`, so it gets a pinned header outside it,
  as Upcoming has. The Projects detail panel is one scroll area holding the
  notes section *and* the items, so its heading row scrolls with the list;
  pinning it would mean splitting that panel into two scroll regions, which is
  a redesign of the panel rather than a resize.
- **D8. Controls keep their size** (LSR2-D2): Completed's ✓ (30), factor chips
  and Reopen (70); Projects' row checkbox (24) and Edit/Complete/Unlink.
- **D9. `ToolbarWrap` gains two things** so it fits these three headers: an
  optional search entry (Completed and the Scheduler have none — the search
  minimum then counts as 0), and a configurable control row and wrap row
  (Projects' header already uses rows 0, 1 and 2). It also moves only the
  controls on the control row, which is a no-op for the four screens using it
  today, where every control is on row 0.
- **D10. The group right of the spacer column becomes right-aligned** on
  Schedule and Projects, as it already is on the four item lists and on
  Completed: that is what gives the wrap a hinge. Visible change on a wide
  window — the Scheduler's four filters and the Projects size controls move to
  the right-hand edge. The spacer columns are the Scheduler's Refresh button
  (4), Completed's "days" label (3) and Projects' Show Complete checkbox (4),
  each gridded `sticky="w"` so it does not drift.
- **D11. No window minsize** (LSR D2/D7 stands). Below what two rows need a
  toolbar clips; nothing stops the window being narrower than that.

## Acceptance criteria → tests

New file `tests/test_screen_resize_spc.py`, except where stated. `(m)` needs a
mapped window.

| ID | Criterion | Test |
|---|---|---|
| SPC-M1 | Completed's four columns fill the list exactly; no slack column | `test_spcm1_completed_columns_fill_the_list` |
| SPC-M2 | A wider list widens all four in their default proportions, cells included | `test_spcm2_completed_follows_the_width` |
| SPC-M3 | No Completed column goes below 6 characters; the shortfall is logged once per crossing | `test_spcm3_completed_floor_is_six_characters` |
| SPC-M4 | A `<Configure>` on the list refits once after the wait; `refresh()` and Expand/Collapse keep the fit | `test_spcm4_completed_configure_and_refresh_refit` |
| SPC-M5 | Every Completed column has a divider; a drag sets only its own share, saves under `completed_col_widths`, and the dropped column keeps its width after the refit | `test_spcm5_completed_drag_sets_one_share` |
| SPC-M6 | Completed's shape survives a narrow window; headings are cut to their column and come back whole | `test_spcm6_completed_shape_survives_a_narrow_window` |
| SPC-M7 | Completed's controls are all still there and the header agrees with the rows per column: ✓, Title, Who, Completed, Pri, factor chips when expanded, Reopen | `test_spcm7_completed_controls_preserved` |
| SPC-M8 | The Projects Action Items rows are columnar — checkbox, Title, Status, Start, Due, actions — and the four columns fill the list | `test_spcm8_project_items_are_columns` |
| SPC-M9 | A wider panel widens all four in proportion; the floor is 6 characters | `test_spcm9_project_items_follow_the_width` |
| SPC-M10 | Each Projects column has a divider; a drag saves under `project_items_col_widths` and the dropped column keeps its width | `test_spcm10_project_items_drag_sets_one_share` |
| SPC-M11 | `Next: …` is cut to the Title column and follows it | `test_spcm11_next_action_follows_the_title_column` |
| SPC-M12 | A `<Configure>` refits the Projects list once; the fit survives `_render_detail()` | `test_spcm12_project_items_configure_and_rerender_refit` |
| SPC-M13 | The Projects items contract: row checkbox, Select All, the count label, Show Completed, Edit, Complete, Unlink all still present | `test_spcm13_project_items_controls_preserved` |
| SPC-M14 | Each of the three headers wraps its right-hand group to a second row when too narrow and unwraps when wide again | `test_spcm14_header_wraps_and_unwraps` (parametrized over the three) |
| SPC-M15 | On a real narrow window nothing clips off any of the three headers | `test_spcm15_narrow_window_wraps_and_nothing_clips` **(m)** |
| SPC-M16 | Projects' search row and warning label stay on their own rows when the control row wraps | `test_spcm16_only_the_control_row_wraps` |
| SPC-M17 | The four screens using `ToolbarWrap` today are unaffected: same one-row width, same wrapped group | `tests/test_list_screen_resize.py` — existing `test_lsrm10_*` and `test_lsrm11_controls_preserved` must stay green, plus `test_spcm17_existing_toolbars_unchanged` |

SPC-M15 is one new mapped-window test function, so the mapped count goes
**28 → 29** in `CLAUDE.md` and `conftest.py` (`tests/test_ci_contract.py`
asserts it exactly).

## Build steps

1. **Guards first**, red before any `src/` change, and each one
   mutation-checked (delete or invert the line it names, run, confirm red,
   restore the verbatim original).
2. `item_list_columns.py`: `ItemListLayout.custom` + `custom_specs` (D3), and
   `ToolbarWrap`'s optional entry, control row and wrap row (D9).
3. `app_settings.py`: `completed_col_widths`, `project_items_col_widths`.
4. `completed.py`: the layout, the pinned header, cells through the layout,
   the `<Configure>` bind, the toolbar wrap. The Reopen button's column index
   is renumbered with the rest — today it is `6 + col_offset` while the chips
   are at 5, so with columns expanded column 6 is empty (adjacent issue, fixed
   here because this change renumbers that row anyway).
5. `project_boards.py`: the columnar Action Items rows, the heading row with
   dividers, the fit, the header rows renumbered for the wrap.
6. `drag_schedule.py`: the toolbar wrap; the now-dead slack weight on column
   13 goes.
7. `CLAUDE.md` + `conftest.py`: mapped count 29.
8. Docs in the same change: `docs/USER_GUIDE.md` — the *Resizing the item
   lists* heading at line 82 (it names four screens), and the Scheduler,
   Projects and Completed sections; this plan's status.
9. `/csdp`: learning-qa plus one cold correctness pass over the diff, every
   medium-or-higher finding fixed, the rest dropped. Push the branch and offer
   the merge; no PR.

Tier: **Full** — `src/`, three screens' user-visible layout. Budget: prose at
or under 0.3 lines per line of changed code, tests at or under 2x.

## Sweep findings and what was done (2026-11-15)

Two passes: `learning-qa` (failures that hide, P1-P45) and a cold correctness
pass. Fixed in this batch:

- **High — the colour inventory was stale**, so `tests/test_color_inventory_sync.py`
  was red at the first three commits: this change adds two `build_header(...)`
  calls and removes two `text_color=row_text` labels. `tools/color_audit.py`
  re-run and the regenerated `docs/ui_color_inventory.md` committed with it.
- **SPC-S1 — the Action Items title was a hardcoded bold 15** while the
  resizer cuts that cell at `row_char_px()`, which follows the user's list
  font setting. A larger setting grew the budget and not the text. Now
  `theme.list_row_font_bold()`. The cold pass also predicted the label would
  push its column wider; measured and it does not — `winfo_reqwidth()` equals
  the configured width. The residual is that bold overshoots the 8 px/char
  model by about 12%, which is the same approximation all six lists use.
- **SPC-S2 — `test_spcm15` could not fail for two of its three screens.** The
  wrap frame is gridded `sticky="e"`, so a second row wider than the toolbar
  overflows the *left* edge, which a right-edge check reads as a pass. At the
  fixed 760 px it was testing the Scheduler (second row needs 991 px) and
  Projects (844 px) below their own two-row minimum. Now sized from
  `one_row_px() - 40`, inside the band where two rows are the point, and both
  edges are asserted. New `ToolbarWrap.wrap_row_px()` is that measurement, and
  `_wrap` now shares its candidate selection so the two cannot drift.
  `test_spcs2_two_rows_need_less_width_than_one` guards the band without a
  mapped window.
- **P4 — reserved widths restated beside their widgets.** `REOPEN_WIDTH_PX`
  existed but the button still said `width=70`; `ITEM_ACTIONS_WIDTH_PX = 240`
  carried its arithmetic in a comment; `title_delta = 34` duplicated the
  badge's width and gap. All three now derive from the widget's own constants,
  as `FACTOR_CHIP_WIDTHS` does. `ITEM_ACTIONS_WIDTH_PX` still evaluates to
  240, so nothing moved.
- **P29 — a floor assertion.** `test_spcm17` asserted
  `one_row_px() > SEARCH_MIN_PX`, which cannot see the threshold moving that
  it exists to catch. Pinned to the exact sum of the row-0 column needs plus
  `SEARCH_MIN_PX`, computed in the test from `grid_info`.
- **Rule 13 — `item_list_columns.py`'s own docstring** still said "the four
  item lists" and pointed at only the LSR tests. It now names six lists, the
  four toolbars, this plan and this batch's test file.

Not fixed, recorded below and in `BACKLOG.md`.

## Adjacent issues found, not fixed

- `completed.py` has no `columns_expanded` persistence (it always opens
  collapsed) while Upcoming reads `settings.default_columns_expanded`. Out of
  scope; not a resize defect.
- The Projects left card board recomputes its column count from
  `cards_frame.winfo_width()` on every `<Configure>` with an 80 ms debounce
  (`_schedule_card_render`), which rebuilds every card. It works; it is just
  more work per resize than a fit would be.
- Completed's `stats_label` is the only variable-width control on any of these
  toolbars, and `refresh()` rewrites it (`Count: 3` to `Count: 412 | Time: 93h
  20m`) without re-running `toolbar_wrap.fit`. The header's allocated width
  does not change, so no `<Configure>` fires and the label can clip until the
  next window resize. Not a regression — Completed had no wrap before this
  batch.
- `ColumnResizer._load_stored` calls `.get` on whatever is stored under
  `<prefix>_col_widths`, and `AppSettings.load` filters by field name with no
  type check. A hand-edited or corrupted `settings.json` holding a list,
  string or int there raises `AttributeError` during screen construction, so
  the screen does not open. Pre-existing and class-wide across all six
  prefixes; this batch adds two more of the same shape.

## Walk checklist (by hand, after the build)

I did not launch the application. Nine steps, each naming what to look at.

**Completed**

1. Open Completed. The list now has a pinned heading row: `Title`, `Who`,
   `Completed`, `Pri`, with a divider at each heading's right edge. The date
   column shows `2026-11-14`, not `Completed: 2026-11-14`.
2. Widen and narrow the window. All four columns change width together and
   keep filling the list; no slack opens at the right. Narrow it until the
   columns stop shrinking — that floor is 6 characters, and headings cut to
   `Com...` and come back whole when you widen again.
3. Drag the divider right of `Who` about 60 px. Who keeps the width you
   dropped it at; the other three take up the difference. Quit and reopen:
   the shape is still there.
4. Press Expand. The factor chips appear between `Pri` and `Reopen`, and
   `Reopen` sits immediately right of them with no empty gap (it used to be
   gridded one column too far).
5. Narrow the window until the toolbar runs out of room. `Who:`, its combo,
   Expand/Collapse and the stats label move to a second toolbar row, right
   aligned. Widen again: they go back on one row, in the same order.

**Projects**

6. Click a project. Its Action Items list is now columnar under a heading row
   — `Title`, `Status`, `Start`, `Due` — with the checkbox at the left and
   Edit / Complete / Unlink at the right. The old
   `Status: open | Start: … | Due: …` line is gone.
7. An item's next step still shows on a second line under its title, inside
   the Title column, and is cut with `...` when that column is narrow.
8. Drag the `Status` divider, then drag the board/detail splitter. The item
   columns refit to the new panel width and Status keeps its share. Narrow
   the window: the Note Size slider, Compact Height and the hint line move to
   a second toolbar row, while the search row and the multi-link warning stay
   where they are.

**Schedule**

9. Narrow the window. Who, Segment, SubSegment and Project move to a second
   toolbar row instead of the Project filter clipping off the right edge. The
   item columns behave as they did after SCR — unchanged by this batch.

## Verification status

- `tests/test_screen_resize_spc.py` — 24 passed, 3 skipped locally. The three
  skipped are `test_spcm15_narrow_window_wraps_and_nothing_clips`, which needs
  a mapped window; **not run locally** (it takes keyboard focus on this
  machine), CI runs it.
- Every new guard mutation-checked: the line it names deleted or inverted, the
  test confirmed red, the file restored verbatim (sha256 compared).
- Regression: `test_list_screen_resize.py`, `test_scheduler_column_resize.py`,
  `test_list_pane_rebuild.py` (95 passed, 12 skipped);
  `test_project_board_bulk_edit.py`, `test_project_multi_link.py`,
  `test_unified_panel_design.py` (176 passed);
  `test_priority_level_colors.py` (84 passed); `test_ci_contract.py`
  (84 passed, 1 skipped) at the new mapped count of 29.

## Changed outside the plan

- `tests/test_priority_level_colors.py` — `_level_cell_call` matched only a
  cell call whose result is bound (`ast.Assign`). Completed discards the pair
  `add_level_cell` returns, because the layout grids the box itself, so the
  scanner found no cell for `completed.refresh` and
  `test_pccm3_the_cell_options_come_from_the_helper` **failed**
  (`assert [] == [('cell', 'row_text')]`) — it did not pass on an empty list.
  Widened to `ast.Expr` as well. Test rule **(b)**: the call's shape changed
  intentionally, and the `Assign` requirement was incidental to the claim the
  guard makes. It still fails on a dropped call, so the widening does not
  weaken it.
