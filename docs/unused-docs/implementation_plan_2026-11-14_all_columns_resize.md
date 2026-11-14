# Plan: every list column resizes with the window (LSR-2)

- Date: 2026-11-14
- Status: **approved, built and pushed 2026-11-14.** Walked by the user
  2026-11-14: "all good on the resizing".
- Screens: Today, Upcoming, All Items, Hierarchical
- Follows: `implementation_plan_2026-11-13_resizable_list_layouts.md` (LSR)

## Why

LSR made four columns resize: Title, SubSegment, Category and Who. Every
other column has a fixed width, so on a typical window most of each row stays
the same size when the window changes. The user reported that "the columns are
not resizing" (2026-11-14) and confirmed that only those four move.

Requirement (user, 2026-11-14): all columns resize with the window, down to a
minimum of 6 characters. Each column can still be resized on its own by
dragging, on all four screens.

## Columns affected

| Screen | Becomes resizable | Stays fixed (D2) |
|---|---|---|
| Today | Start, Due, Pri, Time | checkbox column, factor chips, Timer |
| Upcoming | Start, Due, Pri, Time | checkbox column, factor chips, Timer |
| All Items | Start, Due, Priority, Est. Time, Status | ✓ column, factor chips, Actions |
| Hierarchical | Pri, Due, Sub-items | none |

## Decisions (defaults, each open to change)

- **D1. One rule for every text column.** Each resizable column, the original
  four included, takes a share of the list width in proportion to its weight,
  and no column goes below its floor.
- **D2. Controls keep their size.** The checkbox column, the Timer/Actions
  button and the expanded-mode factor chips do not resize. A button or a
  colour chip cut to 6 characters no longer shows what it is.
- **D3. A divider on every resizable column.** Every resizable column gets its
  own drag divider, as Title, SubSegment, Category and Who have now.
- **D4. The floor is 6 characters at the row font, for every column.** Title's
  current 120 px floor and the other columns' 5-character floor are replaced by
  6 characters. At font size 16 that is 54 px.
- **D5. Date cells drop their "S:" and "D:" prefixes.** The heading already
  says Start or Due. "S:11/14" is 7 characters and would clip at the floor;
  "11/14" is 5 and fits. Hierarchical's Due column keeps its own format.
- **D6. The shape you set survives a narrow window.** Today a column's stored
  width serves as both its weight and its current width. On the way down,
  columns that hit their floor overwrite their weight. On the way back up the
  shape is lost: in a 2026-11-14 measurement, All Items' Who came back as wide
  as Category. With D6, weights change only when you drag a divider, and each
  fit computes every width from the weights.
- **D7. Below the floors the right-hand columns clip.** There is still no
  minimum window size, as LSR decided on 2026-11-13.
- **D8. Saved shapes carry over.** The saved widths of the four original
  columns are used as their weights. A new column starts from its present
  fixed width as its weight.

## Acceptance criteria → tests (`tests/test_list_screen_resize.py`)

| ID | Criterion | Test |
|---|---|---|
| LSR2-M1 | On each screen, every column in "Becomes resizable" changes width when the list width changes | `test_lsr2m1_every_text_column_follows_the_width` (parametrised over the 4 screens) |
| LSR2-M2 | No resizable column goes below 6 characters at the row font, at any list width | `test_lsr2m2_floor_is_six_characters` |
| LSR2-M3 | Controls (D2) keep their width at every list width | `test_lsr2m3_controls_keep_their_size` |
| LSR2-M4 | Every resizable column has a divider, and a drag changes only that column's weight | `test_lsr2m4_every_resizable_column_has_a_divider` |
| LSR2-M5 | Narrow to the floors and back: every column returns to its width from before (D6) | `test_lsr2m5_shape_survives_a_narrow_window` |
| LSR2-M6 | Header cells stay over their row cells after a real resize | existing mapped `test_lsrm2_resize_event_refits`, extended to the new columns |
| LSR2-M7 | Saved widths from LSR load as weights; a screen with none uses the defaults (D8) | `test_lsr2m7_saved_lsr_widths_carry_over` |
| LSR2-M8 | Date cells show no "S:"/"D:" prefix (D5) | `test_lsr2m8_date_cells_have_no_prefix` |

## Build steps

1. Tests first, for M1–M8. M1–M5, M7 and M8 run unmapped.
2. In `column_resize.py`, keep the weights apart from the current widths (D6).
   The two other users of `ColumnResizer` are Drag Schedule and the
   APE/Week panels. Their behaviour is checked by their existing tests.
3. In `item_list_columns.py`, turn the text `FixedColumn`s into stretching
   `ColumnSpec`s, with a 6-character floor (D4), and leave the controls in
   `reserved_px`.
4. In each of the four screens, give each new column's row cell
   `register_row`, with its full text, so it truncates with "…". Also drop the
   date prefixes (D5).
5. Docs: `docs/USER_GUIDE.md` ("Resizing the item lists"), this plan's status,
   and the LSR plan's pointer to it.
6. `/csdp`. This touches `src/` UI code, so it gets the full sweep: learning-qa
   (cold) and a cold correctness pass. Push only after you approve.

## Risks

- **Fit time on long lists.** Eight or nine columns per row are reconfigured
  instead of four. LSR measured 1 s of reconfiguring and 2.3 s of relayout for
  500 rows. I will measure again before the build and record the result here.
- **WeekTacticActionsPanel** inherits Today's layout, so it gets the same
  columns.
- **Text truncation.** The per-character estimate (`row_char_px`) decides
  where text is cut. If it under-measures a font, a cut label is wider than
  its column.

## Changes from this plan, made while building

- **Fit time, measured 2026-11-14:** 203 All Items rows with 9 resizable
  columns take 0.65 to 0.78 s to reconfigure and 0.92 to 1.02 s to relayout
  per fit, with a real window on this Mac. Scaled to 500 rows that is about 4 s,
  against about 3.3 s for LSR's four columns. The fit still waits for the
  window edge to stop (120 ms), so this is paid once per resize.
- **D6, how a drag sets the shape:** when a drag ends, the widths on screen
  become the weights. A drag made while the list is at its floors therefore
  sets the shape to what is on screen then.
  `test_updf43b_the_floor_suspends_the_shape_it_does_not_destroy_it` asserted
  the old result there, and now asserts the new one (behaviour changed on
  purpose).
- **Title's floor** is 6 characters for the column. On Today the completion
  badge and its gap (34 px) sit inside that column, so at the floor less than
  6 characters of the title's text show.
- **`test_pccm3_the_cell_options_come_from_the_helper`** read the Priority
  cell's `build_level_cell(...)` call, which is now
  `self.layout.add_level_cell(...)`. Its matcher accepts both; what it asserts
  (each screen passes its `cell` and `row_text`) is unchanged.
- **Hierarchical's empty Due and Sub-items cells** are now registered text
  cells holding `""`, so they follow their columns like the rest.

## Fixes from the csdp sweep (2026-11-14)

Two cold passes ran over the build: learning-qa and a correctness review.
They found three medium issues, all fixed:

- **A drag reset every column's weight.** Releasing a divider, even
  without moving it, copied every drawn width into the weights, so columns
  held at their floor took the floor as their shape, and it was saved. Now a
  click with no motion changes nothing, and a drag changes only its own
  column's weight. The drag is converted into weight units by the columns
  still sharing freely, or by the last fit's scale when every other column is
  at its floor. What is saved is the weights (D8). This restores the first
  form of the `updf43b` assertion, which the build had changed (described
  above).
- **Headings were never cut.** A heading wider than its column ("Est. Time"
  or "Sub-items" near the floor) widened its label, which pushed every
  heading after it out of line with the rows. Headings are now cut with "..."
  like the cells, at 8 px a character for the bold 12 header font.
- **Hierarchical's Due kept its "Due: " prefix** (D5 kept it). At the floor
  that left "Due..." and no date, so the prefix is gone and the cell shows
  `2026-11-14`.

A cold review of those fixes found one more medium issue: saved weights
were clamped to the column's pixel limits on load, so a shape dragged in a
narrow window changed after a restart. Saved values now load as weights
unclamped; only the drawn width is clamped.

Two low findings were dropped as below medium: deep Hierarchical rows
indenting past a floored Title column, and M4's test not reading the
weights. The new test `test_lsr2m4b` covers the second.

## Walk checklist (by hand, after the build)

- [x] On each screen, narrow and widen the window. Every text column changes
      width, and the checkbox, Timer and chips do not.
- [x] Drag Start's divider, then resize the window. Start keeps its share.
- [x] Narrow the window until every column is at 6 characters, then widen it.
      The columns return to the shape they had before.
- [x] Near the floor, headings are cut with "..." and stay over their
      columns (All Items expanded: Status and Actions headings line up).
- [x] Click a divider without dragging, then widen the window: nothing moves.
