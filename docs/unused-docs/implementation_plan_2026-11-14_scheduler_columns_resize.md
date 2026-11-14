# Plan: the Scheduler's item columns resize with the window (SCR)

- Date: 2026-11-14
- Status: **approved 2026-11-14 ("Yes, build it") and built 2026-11-14.**
  The walk below is not yet done.
- Screen: Scheduler (`src/getmoredone/screens/drag_schedule.py`), left
  "Action Items" list
- Follows: LSR and LSR2, which covered Today, Upcoming, All Items and
  Hierarchical only

## Why

Requirement (user, 2026-11-14): "You are still not resizing the Title,
Segment, Subsegment and Category columns ... Start with a set of default
widths that create a full width for the screen. Then as the screen size
changes, the column sizes change proportionately."

Title, Segment, SubSegment and Category are the Scheduler's columns; none of
the four LSR screens has a Segment column. The Scheduler was never part of
LSR or LSR2. Two things keep its columns fixed today:

1. **No fit is ever run.** The columns use `ColumnResizer` for dragging, but
   nothing calls `fit_to_width`, so they keep their saved pixel widths at
   every window size. A trailing slack column takes up whatever is left.
2. **The list's pane does not grow.** The list sits in the left pane of a
   `tk.PanedWindow`. Tk gives extra width only to the last pane by default,
   so a wider window widens the date boxes on the right, and the list stays
   the same width.

## Decisions (defaults, each open to change)

- **D1. Both panes grow with the window.** Both panes get `stretch="always"`,
  so a window change is shared between them in proportion, and the
  divider between them keeps its place as a fraction of the width. Dragging
  that divider still works as now.
- **D2. The columns fill the list.** Title, Segment, SubSegment, Category and
  Start Date share the list's width by weight (the LSR2 rule). The trailing
  slack column goes, so there is no empty space at the right.
- **D3. Default weights.** Title 220, Segment 170, SubSegment 170, Category
  170, Start Date 120 (the current default widths). On a first open the five
  columns fill the list in those proportions.
- **D4. Floor of 6 characters**, as on the other four lists (48 px at the
  Scheduler's font size 14). The present floors (120 px Title, 90 px others,
  80 px Start) are replaced.
- **D5. Dragging a column divider** still sets that column's share, and is
  remembered (`drag_schedule_col_widths`). Saved widths load as weights.
- **D6. The checkbox column keeps its 40 px.**

## Acceptance criteria → tests (`tests/test_scheduler_column_resize.py`, new)

| ID | Criterion | Test |
|---|---|---|
| SCR-M1 | A fit makes the five columns fill the list width exactly (no slack) | `test_scrm1_columns_fill_the_list` |
| SCR-M2 | A wider list widens all five columns in proportion to their weights | `test_scrm2_columns_follow_the_width` |
| SCR-M3 | No column goes below 6 characters | `test_scrm3_floor_is_six_characters` |
| SCR-M4 | A `<Configure>` on the list refits it once after the wait | `test_scrm4_configure_refits` |
| SCR-M5 | Both splitter panes have `stretch="always"` | `test_scrm5_both_panes_stretch` |
| SCR-M6 | A drag changes only that column's share and is saved | `test_scrm6_drag_sets_one_share` |
| SCR-M7 | The fit survives `refresh()` rebuilding the rows | `test_scrm7_refresh_keeps_the_fit` |

## Build steps

1. Tests first, unmapped where possible.
2. In `drag_schedule.py`: the 6-character floors, no slack column, a
   debounced `<Configure>` on the items list that calls `fit_to_width` with
   the list width less the checkbox column and padding, a refit after each
   rebuild, and `stretch="always"` on both panes.
3. Docs: the Scheduler section of `docs/USER_GUIDE.md`, and this plan's
   status.
4. `/csdp`, with learning-qa and a cold correctness pass. Push after you
   approve.

## Changes from this plan, made while building

- **Headings now use their cells' padding.** The header used padx (10, 4)
  on every heading and on the select-all box, while the cells use (8, 4) on
  Title and 4 on the rest, so each heading sat a few pixels right of its
  column, more so further right. Guarded by
  `test_scr_headings_padded_like_their_cells`.
- **No column ceiling.** A column's maximum is 10000 px instead of 800, so
  a very wide list is still filled (`test_scrm1b_no_ceiling_on_a_wide_list`).

## Walk checklist (by hand, after the build)

- [ ] Open the Scheduler: the five columns fill the list with no gap at the
      right.
- [ ] Widen and narrow the window: the list and its columns change width in
      proportion.
- [ ] Drag the divider between the list and the date boxes: the columns
      refit to the new list width.
