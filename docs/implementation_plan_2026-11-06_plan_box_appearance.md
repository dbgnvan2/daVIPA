# Plan box appearance — PB-M1 to PB-M5

Status: **proposed, not approved, nothing implemented**
Date: 2026-11-06
Supersedes nothing; extends `docs/implementation_plan_2026-11-05_time_grid.md`.

Five changes asked for against the running demo, in the user's order. One of
them conflicts with a standing theme rule; that is called out under PB-M4.

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
  Test: `::test_an_item_row_is_as_tall_as_its_text_not_the_stripe_default`
  *(already written, currently failing)*

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
  both themes. Test: `tests/test_time_block_colors.py::test_pbm41_fill_tints_carry_legible_text`
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

## Order

1. PB-M2 (the stripe height) — everything else is invisible until this lands.
2. PB-M5 (sizes from settings) — the box must be tall enough before the bars
   and the fill are worth looking at.
3. PB-M1 + PB-M4 (the two colour tables) — one change to `theme.py`.
4. PB-M3 (the bars) — a test, once the box is tall enough to hold them.

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
