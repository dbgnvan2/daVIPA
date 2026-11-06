# Plan box appearance — PB-M1 to PB-M7

Status: **approved and implemented** (PB-M1 to PB-M5 approved 2026-11-06 and
shipped in `3f44a26`; PB-M6 and PB-M7 asked for and shipped the same day)
Date: 2026-11-06
Supersedes nothing; extends `docs/implementation_plan_2026-11-05_time_grid.md`.

Five changes asked for against the running demo, in the user's order, and then
two more after seeing those five on screen. One of the five conflicts with a
standing theme rule; that is called out under PB-M4.

---

## What is actually wrong today

A Day Plan box renders as a bare coloured stripe with no text and no bars. The
title, the three-bar depth stack and the duration are all already built by
`_build_block_chip` (`src/getmoredone/screens/plan_blocks.py:404-410`) — they
are drawn and then hidden.

Cause: `ctk.CTkFrame` requests **200x200** when neither `width` nor `height` is
given. The accent stripe sets `width=STRIPE_WIDTH_PX` only, so its requested
height stays 200. `chip` does not switch off propagation, so `chip` asks for
200 too; the slot row has `height=slot_row_height(chips)` (34px) and
`grid_propagate(False)`, so the chip is clipped to 34px with its contents laid
out around y=100 — below the visible area. Only the stripe shows, because it is
gridded `sticky="ns"` and so is drawn from the top.

The same missing `height=` makes every item row in the left pane ~200px tall
(`build_item_row`, `plan_blocks.py:115`). That is the "Items starting" defect
from the previous round.

So PB-M2 and PB-M3 below are mostly one fix, not two features.

---

## PB-M1 — brighter priority stripes

The light theme's band colours are deliberately dark (`#991B1B`, `#9A3412`,
`#92400E`, `#166534`) so they clear **4.5:1** against `surface_subtle`. The
comment in `theme.py:264-269` says why: headroom "if a band colour is ever put
behind text".

PB-M4 puts a band colour behind text, so that headroom is now load-bearing and
the dark set must stay. Therefore **a second table**, not an edit of the first:

- `priority_band_colors()` — unchanged. Text-safe. Used wherever a band colour
  carries a label.
- `priority_stripe_colors()` — new. The brighter bar. Held to **3:1**, which is
  the WCAG non-text standard the existing comment already names, and
  additionally asserted *brighter* (higher relative luminance in light mode)
  than the text-safe set, so "brighter" is a tested property and not a taste.

Consumers: the vertical stripe in `build_item_row` and `_build_block_chip`.

**Acceptance**
- PB-M1.1 `priority_stripe_colors()` returns all five bands in both themes.
  Test: `tests/test_time_block_colors.py::test_pbm11_stripe_colors_cover_every_band`
- PB-M1.2 Every stripe colour clears 3:1 on `surface_subtle`, both themes.
  Test: `::test_pbm12_stripe_colors_meet_the_non_text_contrast_bar`
- PB-M1.3 Every light-theme stripe colour is brighter than the text-safe band
  of the same name. Test: `::test_pbm13_stripe_colors_are_brighter_than_the_text_safe_set`

## PB-M2 — the task's title shows in the box

Fix the stripe's requested height so the chip is not clipped. One constant,
two call sites.

**Acceptance**
- PB-M2.1 A chip's title label lies wholly inside the box it is drawn in
  (`0 <= top` and `top + height <= box height`). Test:
  `tests/test_plan_screen.py::test_a_task_chips_title_is_inside_the_box_it_is_drawn_in`
  *(already written, currently failing — this is the sliver, measured)*
- PB-M2.2 An item row in the left pane is no taller than its two lines of text.
  Test *as planned*: `::test_an_item_row_is_as_tall_as_its_text_not_the_stripe_default`
  — that test no longer exists under that name; see below.
  **Superseded by PB-M6.1.** The criterion was right for the 200px defect it
  was written against and wrong afterwards: a row is now a multiple of the box
  height on purpose, which is taller than its text whenever the item needs more
  than one box. The test was rewritten as
  `::test_an_item_row_lays_out_at_the_height_it_asks_for`, which asserts the
  row lays out at the height it requests rather than at its text's height.

## PB-M3 — the three depth bars show in the box

Falls out of PB-M2: `DepthBarStack` is already gridded at column 2 of the chip
for `BlockType.ITEM`. It needs its own regression test because it is a
grandchild of the box and so has its own way of disappearing.

**Acceptance**
- PB-M3.1 A chip for an item with depth renders three bars, all inside the box.
  Test: `tests/test_plan_screen.py::test_pbm31_the_depth_bars_are_inside_the_box`

## PB-M4 — the task is shaded by its priority

Today a chip is transparent and the priority appears only as the 6px stripe.
Requested: the chip itself carries the priority shading.

**This conflicts with a project rule.** `CLAUDE.md` says a colour from the DB
is allowed "only as small accents (chip/stripe/icon), never as full-row fills",
and `theme.py:38-40` repeats the reasoning: a wall of saturated rows stops
carrying information and fights the text on top of it.

The rule as written is about **segment/category colours from the database**.
Priority bands are semantic theme tokens, not DB colours, so this is not a
breach of its letter. To keep its spirit, the fill is a **pale tint**, not the
saturated accent:

- `priority_fill_colors()` — new, one tint per band per theme, chosen so
  `pick_text_color` on it clears 4.5:1 and so the stripe of the same band
  clears 3:1 **on the tint** rather than on `surface_subtle`.

Flagging it rather than deciding it: if you want the saturated fill instead,
say so and I will drop the tint and take the text to `pick_text_color` on the
full accent.

**Acceptance**
- PB-M4.1 Every fill tint carries legible text (`pick_text_color` >= 4.5:1),
  both themes. Test: `tests/test_time_block_colors.py::test_pbm41_pick_text_color_is_not_what_makes_a_fill_legible`
  *(named `test_pbm41_fill_tints_carry_legible_text` when planned; renamed when
  written, because what it proves is that `pick_text_color` picking a colour is
  not itself evidence the pairing clears the bar)*
- PB-M4.2 Every stripe clears 3:1 against its own band's fill tint, both
  themes. Test: `::test_pbm42_a_stripe_is_visible_on_its_own_fill`
- PB-M4.3 A chip for a critical item is filled with the critical tint and not
  `surface_subtle`. Test: `tests/test_plan_screen.py::test_pbm43_a_chip_is_filled_by_its_priority`

## PB-M5 — Drag Schedule settings size the boxes

Decided in this session: **height and title width**, from the settings that
already exist.

- Box height from `AppSettings.drag_schedule_box_height_px` (default 86),
  replacing the `SLOT_CHIP_HEIGHT_PX = 30` constant as the per-chip height.
  `slot_row_height()` gains a `chip_height` parameter; the constant stays as
  its default so the arithmetic still has one home.
- Chip title column `minsize` from `AppSettings.drag_schedule_title_col_width`
  (default 220), replacing the inline `minsize=80`.
- `build_slot_row` gains a `chip_height`/`title_width` pair, passed by
  `plan.py` from `self.settings`. Both fall back to the module constants when
  the setting is missing or unusable, the same shape as `items_col_width()`.

**Known consequence, accepted when the option was chosen:** 18 boxes at 86px is
1620px, so the day no longer fits one screen without scrolling. The Day Plan
pane is already a `CTkScrollableFrame`, so nothing new is needed for that — but
"the day reads at a glance" (the outstanding human-review row in
`docs/spec_coverage.md`) stops being true, and that row must be rewritten to
say so rather than left claiming a property this change removes.

**Acceptance**
- PB-M5.1 `slot_row_height(1, chip_height=86)` is 90; the no-argument form is
  unchanged. Test: `tests/test_plan_screen.py::test_pbm51_box_height_follows_the_setting`
- PB-M5.2 A box built with `settings.drag_schedule_box_height_px = 120` is
  taller than one built at the default. Test: `::test_pbm52_the_setting_reaches_the_rendered_box`
- PB-M5.3 An unusable setting (0, negative, non-numeric) falls back to the
  constant rather than collapsing the box. Test: `::test_pbm53_an_unusable_box_height_falls_back`
- PB-M5.4 The chip's title column requests the Drag Schedule title width.
  Test: `::test_pbm54_the_title_column_follows_the_drag_schedule_width`

---

## PB-M6 — an item row is the size of the space it will take

Asked for after PB-M1 to PB-M5 were on screen. Three parts, all on the "Items
Starting" row.

- **PB-M6.1 Height.** `item_row_height(span, box_height)`: the space the day
  gives those half hours, asked of `slot_row_height` rather than recomputed,
  plus the 2px `build_slot_row` grids between consecutive boxes. A 90-minute
  item is three boxes tall on the left because it will be three boxes tall on
  the right. 45 minutes is two boxes for the reason it is two boxes in the day:
  a half-hour grid cannot hold a quarter hour. `grid_propagate(False)` holds
  the height against the row's own text, and the slack sits on an empty row
  below the two text rows so a tall row keeps its lines together and a short
  one loses from the bottom.
- **PB-M6.1 Floor.** Never below `ITEM_ROW_MIN_HEIGHT_PX` -- the title's 28px
  plus its 5px top pad, and the second line's 28 plus its bottom pad, measured
  off the real widgets rather than counted. The 30px floor on the box height
  was justified for a chip holding one line; an item row holds two, and matched
  to a 34px box it dropped the second line with no sign of it.

  **67 as shipped here, 66 since PD-M1.2.** The second line's bottom pad was
  the `{minutes}m` label's 6px while the length sat on that row; PD-M1 moved
  the length up beside the title, leaving the `already blocked` marker's 5px.
  The number is measured by
  `::test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for`, which is why the
  change showed up as a failing measurement rather than as a silently wrong
  constant. The crossover with the day moved with it: exact from a box height
  of 62 up, not 63.
- **PB-M6.2 The priority score comes off.** The band is already the shade the
  row is drawn on and the colour of its stripe, so the number was a third way
  of saying one thing, in the one place a reader looks for what the colour
  cannot tell them.
- **PB-M6.3 The work-block length moves under the depth bars.** `30m` sits
  below the stacked lines rather than in the detail line, which puts the fact
  in the same place on an item row as on a task in a box.

  **Superseded by PD-M1.2.** The intent was right and the position was not: a
  box does not put the length under the bars, it puts it beside them at the
  right-hand end of the task's one line. PB-M6.3 mirrored a box's *facts*
  without mirroring its layout, and on screen the left pane still read as a
  different kind of thing from the right -- which is what PD-M1 was asked for.
  The length is now in column 3 on row 0, where a chip writes it. See
  `docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m1`.

**What the first version of this got wrong, found by the cold sweep over
`2e4add9...HEAD` and measured before fixing:**

- The height was `span * box_height`, which is 4px short of one box and 6px
  short per box after the first, because a day box is `box_height + 4` and
  consecutive boxes are 2px apart. The acceptance test asserted that same
  product, so the one relationship this change exists for was the one thing
  unchecked. Both now go through `item_row_height`, and the test asserts
  literals plus a second test measuring the rendered day.
- `grid_rowconfigure(0, weight=1)` put all the slack — including a negative
  shortfall — on the title's row. At a box height of 30 Tk collapsed the title
  to a single pixel: the row showed its depth and its length and not which item
  it was. At 86 with a 3-box span the title was centred in 224px of slack, 100px
  from its own detail line. The weight is on an empty row 2 now.
- Three colour and score assertions could not fail for what they named, because
  `_item(..., priority_score=51200)` does not produce a scored item —
  `create_action_item` recomputes the score from four factors that were all
  `None`, giving 0 — and `_one_slot_pane` rendered with an empty `items_by_id`,
  so the chip's item was `None`. Both sides were the unscored tint. Fixed with
  a `_scored_item` helper that asserts its own band, and two of the three were
  PB-M4 tests from the earlier batch (adjacent, fixed with it, said so).

**Acceptance**
- PB-M6.1 A row's requested height is what the day gives those boxes, for
  30/45/60/90/120 minutes, asserted as literals rather than as an expression
  over the module's own constants.
  Test: `tests/test_plan_screen.py::test_pbm61_an_item_row_is_the_height_the_day_would_give_it`
- PB-M6.1 The row equals the span of the real boxes holding the task, measured
  on screen. Test: `::test_pbm61_a_row_is_as_tall_as_the_boxes_beside_it`
- PB-M6.1 A row is never shorter than its two lines, and above the floor it is
  exactly the day's height. Test: `::test_pbm61_a_row_too_short_for_its_text_keeps_its_text`
- PB-M6.1 Every child of the row is drawn inside it, at the floor and above it.
  Test: `::test_pbm61_every_line_of_a_row_is_drawn_inside_it`
- PB-M6.1 A tall row keeps its two lines together at the top.
  Test: `::test_pbm61_a_tall_row_keeps_its_two_lines_together`
- PB-M6.1 The screen passes the setting it draws the day with, read off the
  rendered row. Test: `::test_pbm61_the_item_row_height_comes_from_the_setting`
- PB-M6.1 The row lays out at the height it asks for on a real window.
  Test: `::test_an_item_row_lays_out_at_the_height_it_asks_for`
- PB-M6.2 No label on the row carries the score or a `P `-prefixed form of it.
  Test: `::test_pbm62_an_item_row_does_not_print_its_priority_score`
- PB-M6.3 The length label is in the bars' column and on a later row.
  Test: `::test_pbm63_the_work_block_length_is_under_the_depth_bars`
  **Superseded by PD-M1.2**; the test is replaced by
  `::test_pdm12_the_length_sits_beside_the_depth_bars`, which asserts the same
  row and the next column along.

---

## PB-M7 — a continuation box looks like the task it continues

The later boxes of a long task were drawn transparent, on the argument that
shading them would read as a second task of equal weight. On screen the
opposite happened: a 90-minute task was one coloured box followed by two empty
ones, which reads as a task that stops after half an hour.

- **PB-M7.1** A continuation chip takes `fill_for_item` and
  `stripe_for_block` like the box that starts the task; only buffers and breaks
  stay transparent. Its "same task" / "N m spare" line switches from the muted
  text colour to the one `pick_text_color` picks for the fill, because the fill
  is no longer the pane's background.
- **PB-M7.2** The `↳` prefix stays. It is now the whole of what distinguishes a
  continuation, so it is asserted separately from the colour — a change that
  dropped it would otherwise pass as a colour fix.

**Acceptance**
- PB-M7.1 A continuation chip's `fg_color` is the task's fill and its stripe is
  the task's stripe. Test: `tests/test_plan_screen.py::test_pbm71_a_continuation_box_is_the_colour_of_its_task`
- PB-M7.2 A continuation chip still carries the arrow and names its task.
  Test: `::test_pbm71_a_continuation_box_keeps_its_arrow`

---

## Order

1. PB-M2 (the stripe height) — everything else is invisible until this lands.
2. PB-M5 (sizes from settings) — the box must be tall enough before the bars
   and the fill are worth looking at.
3. PB-M1 + PB-M4 (the two colour tables) — one change to `theme.py`.
4. PB-M3 (the bars) — a test, once the box is tall enough to hold them.
5. PB-M6 + PB-M7 — added after the first four were on screen. PB-M6 reuses
   PB-M5's `box_height()`, and PB-M7 reuses PB-M4's `fill_for_item`, so both
   wait on those.

## Not code-testable

Nothing. Every criterion above is a widget measurement or a colour ratio.
"Brighter" (PB-M1.3) is made testable as relative luminance rather than left
to the eye; whether it reads as brighter on your screen is still yours to
confirm, and I will ask after it is on screen.

## Adjacent issues found, not fixed

- `_build_block_chip`'s `chip` frame does not call `grid_propagate(False)`,
  unlike every other fixed-height frame in the module. After PB-M2 it no longer
  matters, but it is the asymmetry that let the 200px leak through.
- `tests/test_plan_screen.py:1126-1140` carries a comment block stating "**The
  bug does not reproduce.**" about this exact sliver. It is false — the bug is
  on screen now. The comment is corrected as part of PB-M2, not left.
- `docs/spec_coverage.md:287-296` still says both human-review rows are
  outstanding and that the packaged app holds the lock. Both are stale.
