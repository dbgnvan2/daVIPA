# PBG — the priority badge on the Plan screen (2026-11-12)

**Status: plan, not approved. No code written.**

Requirement, as given: *"On the plan screen show the priority badge in the
action item listing. Remove the current priority level coloring."*

Two answers settled with the user before this plan was written:

- the colouring goes from **both panes** — the item rows and the day's time-block
  chips — because `configure_chip_columns` and `chip_column_minsizes` exist to
  keep the two panes the same four columns at the same widths, and stripping one
  leaves the screen half-coloured;
- the badge carries the **level colour scheme** (`priority_levels.level_cell_fill`),
  the same one the Priority cell now uses on Today, Upcoming, All Items,
  Hierarchical and Completed, so the Plan screen's badge matches every other
  listing.

---

## 1. What is there now

The Plan screen is the **only** user of the *band* colour scheme — score →
band → colour — which is a different thing from the *level* scheme
(importance/urgency → level → colour) that the list screens use. Verified by
grep: nothing outside `screens/plan_blocks.py` calls
`priority_band_colors`, `priority_fill_colors` or `priority_stripe_colors`, and
nothing outside it calls `priority_band` except its own definition.

Four consumption sites, and no others:

| Site | What it colours |
|---|---|
| `plan_blocks.py:369` | the item row's whole surface, `fill_for_item` |
| `plan_blocks.py:389` | the item row's left stripe, `stripe_for_item` |
| `plan_blocks.py:836` | a task chip's surface in the day, `fill_for_item` |
| `plan_blocks.py:858` | a task chip's left stripe, `stripe_for_block` |

There is **no priority badge anywhere on the Plan screen**. The item row's five
columns are stripe, title, scheduled-marker, depth bars, length.

## 2. Acceptance criteria

| ID | Criterion | Implementation | Test |
|---|---|---|---|
| PBG-M1 | A badge column is added to `chip_column_minsizes`, so it reaches both panes or neither — that function's own stated contract. The item row draws the badge in it; a day chip leaves the cell empty, because the badge was asked for in the listing. | `plan_blocks.py::chip_column_minsizes`, `CHIP_BADGE_COLUMN` | extend `test_pdm11_the_item_row_uses_the_chips_column_order` |
| PBG-M2 | The badge reads `P:<score>` on `level_cell_fill(settings, item)`, its text colour derived from that fill by `pick_text_color`, falling back to the row text when the level has no colour. `build_item_row` takes `settings`, threaded from `PlanScreen.self.settings` (which may be `None`). | `plan_blocks.py::build_item_row`, `plan.py:1031` | new |
| PBG-M3 | An item row is drawn on the theme's own surface, not a priority fill, and its stripe carries no priority colour. | `plan_blocks.py:369`, `:389` | new, plus rewrite of the PB-M1/PB-M4 row tests |
| PBG-M4 | A task's day chip likewise. Padding chips keep their `block_type_colors` stripe and transparent surface — now the only thing distinguishing a task chip from a padding chip. | `plan_blocks.py:836`, `:858` | new, plus rewrite of the PB-M4/PB-M7 chip tests |
| PBG-M5 | The band scheme is deleted, not left dead: `stripe_for_item`, `fill_for_item`, `_band_of`, `accent_for_item`, `accent_for_block`, `stripe_for_block` from `plan_blocks.py`; `priority_band_colors`, `priority_fill_colors`, `priority_stripe_colors` from `theme.py`; `priority_band` from `time_block_layout.py`. | those files | the band tests are deleted with them; `test_time_block_colors.py` loses its band-palette assertions |
| PBG-M6 | `docs/ui_color_inventory.md` is regenerated, because PBG-M5 removes colour literals from `src/` and `tests/test_color_inventory_sync.py` fails while that file is stale. | `tools/color_audit.py` | `tests/test_color_inventory_sync.py` |

## 3. Tests that change, and why

`CLAUDE.md` requires stating which of (a) the code is wrong, (b) the behaviour
changed intentionally, (c) the test was over-specified applies before a test is
modified to pass. Every one of these is **(b)**: the user asked for the
colouring to go, so the tests asserting it are asserting the old behaviour.

- `tests/test_plan_screen.py` — the PB-M1 stripe tests (~3036–3055), the PB-M4
  fill tests (~2880–2905, ~3081, ~4277–4291), the PB-M7 continuation shading,
  and the `accent_for_item` / `accent_for_block` tests (~1145–1182, ~3052).
- `tests/test_time_block_colors.py` — the band-palette assertions (~267).

Exact line numbers are confirmed when the work starts, not taken from here.

## 4. Consequence to confirm when it is seen

Adding a column raises both pane-width floors, which are
`sum(chip_column_minsizes(...))` at `plan.py:666` and `:685`. The items pane
cannot be dragged as narrow as it can today — by the badge's width. This is
real and user-visible; it is the cost of keeping the two panes aligned, which
was the choice made in the answers above.

## 5. Sequencing

**This cannot start yet.**

- The session *Priority colour only on the Priority column* is still building and
  holds `src/getmoredone/theme.py` — which PBG-M5 edits — plus `today.py`,
  `BACKLOG.md`, `docs/spec_coverage.md` and two test files in the working tree.
  One build batch at a time per checkout.
- PBG-M2 depends on `level_cell_fill`, which that batch is defining.
- The lunch batch (`3adfc91`, `b8779c5`, `b87f941`) is banked unpushed at the
  user's instruction; this batch would sit on top of it.

## 6. Adjacent issues found, not fixed

Carried from the lunch batch and still open:

1. `move_block_to_slot` (`plan.py:2988`) passes no `day_span`, so `can_place`
   checks fit against Day Settings' hours rather than the day actually drawn —
   any block dragged onto an extended slot is refused `outside_grid`.
2. Nothing refuses a second `LUNCH` block on one date; `lunch_window` silently
   returns the first it finds.
3. `on_drag_release` (`plan.py:2752`) handles only `target` for
   `kind == "lunch"`, not `edge`, so the Day Settings lunch chip cannot be
   dropped on Earlier or Later.

Found while reading for this plan:

4. `docs/spec_coverage.md` has no LM section for the lunch batch. Held back
   because the priority-colour session is editing that file.
