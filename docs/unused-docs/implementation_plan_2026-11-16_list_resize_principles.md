# LRP — list resize principles, resizable filters, left-justified wrap, Project Board buttons

Date: 2026-11-16. Status: **approved and built 2026-11-16.**

Five requests, in the user's words:

1. "there should [be] principles of resizing any list of action items that can
   then be applied to any listing so the resizing behavior looks and feels the
   same across lists. All columns have a default display width and resize in
   proportion to the size change of the Title Field, until they hit a minimum
   size."
2. "All Screen - the Filter boxes e.g. Status, Who should resize."
3. "The buttons that wrap to the 2nd line should be left justified on the
   second line vs. right justified."
4. "on the Right Panel on the Project Board where action items are listed, the
   Buttons Edit Project Create Note, Link Not and Open Notes should be removed."
5. "Create Action and Link Action item get removed as well."

## What is already true

`screens/column_resize.py` (`ColumnResizer`) owns widths, weights, floors,
persistence and divider drags. `screens/item_list_columns.py`
(`ItemListLayout`, `ToolbarWrap`) owns the item-list column sets and the
toolbar wrap. Seven listings of action items go through them:

Today, Upcoming, All Items, Hierarchical, Completed, the Project Board's
linked Action Items, the Scheduler. (`screens/chip_table.py` also uses
`ColumnResizer`, for the APE/Week chip panels. Not a list of action items;
out of scope, and said so here rather than left to be noticed.)

Request 1's proportionality rule **already holds** where `fit_to_width` runs:
each column's share is `weight_k / Σweight` of the available width, so every
column's change is a fixed ratio of Title's change, and `_share` pins a column
at its floor and re-shares the rest. What does *not* hold is that the listings
agree on the numbers.

### The measured divergence (read 2026-11-16)

Default widths for the same column kind, per listing:

| column | Today | Upcoming | All Items | Hierarch. | Completed | Proj. Board | Scheduler |
|---|---|---|---|---|---|---|---|
| title | 260 | 260 | 260 | **320** | 260 | 260 | **220** |
| segment | – | – | – | – | – | – | 170 |
| subsegment | 120 | 120 | 120 | – | – | – | **170** |
| category | 120 | 120 | 120 | – | – | – | **170** |
| who | 80 | 80 | 80 | – | **110** | – | – |
| start | 60 | 60 | 60 | – | – | **90** | **120** |
| due | 60 | 60 | 60 | **110** | – | **90** | – |
| completed | – | – | – | – | **150** | – | – |
| status | – | – | 80 | – | – | **90** | – |
| time | 50 | 50 | **60** | – | – | – | – |

Seven of the ten text-column kinds carry two or three different defaults.

Floors and maxima diverge too:

- Item lists and the two custom sets: `list_floor_px()` = 6 characters at
  `row_char_px()`, which **follows the row-font setting**.
- Scheduler: `ITEM_COLUMN_FLOOR_PX = 6 * CHAR_PX` — 6 characters at the
  *default* font, fixed. A larger row font does not widen its floor.
- `ColumnResizer` applies its own `MIN_COLUMN_CHARS = 5` as a second floor
  (`max(spec.min_width, min_column_width(char_px))`), so there are two floor
  constants in play, 5 and 6.
- Maxima: item lists cap a non-Title column at `STRETCH_MAX_PX = 800` and
  Title at `TITLE_MAX_PX = 2000`; the Scheduler caps every column at
  `ITEM_COLUMN_MAX_PX = 10000`. A column pinned at its maximum stops taking
  its share, so the two behave differently on a wide window.

## Acceptance criteria

### Phase 1 — small and independent

**LRP-M1** The wrapped second row is left-justified. `ToolbarWrap._wrap` grids
its frame `sticky="w"` instead of `"e"`.
*Consequence:* a second row wider than the toolbar now overflows to the
**right**, not the left. `wrap_row_px()`'s docstring records the opposite and
must be corrected; the SPC-S3 budget guard still measures the right number and
stays.

**LRP-M2** The Project Board's right-panel toolbar loses six buttons: Create
Action Item, Link Action Item, Edit Project, Create Note, Link Note, Open
Notes (`screens/project_boards.py:1420–1458`). Bulk Edit and Set Active stay.

Access after removal, checked route by route:

| removed | other route | lost? |
|---|---|---|
| Edit Project | ✎ icon on each project tile (`:1312`), `open_project_from_note` | no |
| Create Note | 📄 tile icon → `add_note_to_project` chooser | no |
| Link Note | same chooser | no |
| Open Notes | each note row already has its own **Open** (`_render_project_note_row`) | no |
| Create Action Item | create on Today/Upcoming/All Items, set Project in the item editor | **yes, from this screen** |
| Link Action Item | open the item, set its Project in the item editor | **yes, from this screen** |

**LRP-M3** Two empty-state texts stop naming removed buttons:
`"No action items linked yet. Use Create Action Item to add the first task."`
(`:1489`) and `"No notes linked yet. Use Create Note or Link Note to add one."`
(`:2011`).

### Phase 2 — the principles

**LRP-M4** One floor for every action-item listing, following the row-font
setting: the Scheduler moves off `ITEM_COLUMN_FLOOR_PX` onto `list_floor_px()`.

**LRP-M5** One maximum per column kind: the Scheduler moves off
`ITEM_COLUMN_MAX_PX` onto `TITLE_MAX_PX` / `STRETCH_MAX_PX`.

**LRP-M6** One default per column kind, in a shared table in
`item_list_columns.py`, which every listing names instead of passing a number.

**LRP-M7** `docs/list_resize_principles.md` — the principles, as live
reference under `docs/` (read before working, so not `unused-docs/`), listed in
`docs/DOCUMENTATION_INDEX.md`.

**LRP-M8** A conformance test over all seven listings: same floor, same maxima,
defaults drawn from the shared table, a fit bound to the list area, dividers
built, widths persisted as weights.

**LRP-M9** The proportionality rule is asserted, not just documented: over a
width change, every column moves by its weight share, each column's change
holds a fixed ratio to Title's, and no column goes below the floor.

### Phase 3 — the filter boxes

**LRP-M10** The value filters grow and shrink with their toolbar, down to a
minimum: Who, Status, Segment, SubSegment and Project on Upcoming, All Items,
Hierarchical, Completed and the Scheduler. `ToolbarWrap` takes a set of
flexible controls and gives each one a weighted, min-sized grid column; the
spacer's `TOOLBAR_SPACER_WEIGHT = 1000` drops so growth actually reaches them.

**LRP-M11** A toolbar wraps only when the controls at their *minimum* widths
do not fit one row — today it wraps at their requested widths.

## Decisions for the owner

**D1 — the shared default table.** Recommended: title 260, lineage (segment,
subsegment, category) 150, who 110, dates (start, due, completed) 110, status
90, time 60. The priority cell keeps `SCORE_CELL_WIDTH_PX` /
`ALL_ITEMS_SCORE_CELL_WIDTH_PX` (a fixed-content control, deliberately two
sizes), and Hierarchical's `sub-items` 70 is unique and stays.
*Consequence:* on an install that has **never dragged a divider**, every list
opens at new widths — wider lineage/who/date columns on Today, Upcoming and All
Items, a wider Title and narrower lineage on the Scheduler, Completed's
Completed column 150 → 110, Hierarchical's Title 320 → 260. A stored weight
wins over a default, so anyone who has dragged keeps their shape. There is no
way to make seven listings agree without moving some of them.

**D2 — the Scheduler's maximum.** 10000 → 800 caps its lineage columns on a
very wide window, where today they keep growing. Recommended: accept, because
a listing that keeps growing while the others pin is the inconsistency being
fixed.

**D3 — the second floor.** `MIN_COLUMN_CHARS = 5` in `column_resize.py` applies
to `chip_table` as well as the listings. Recommended: leave it at 5 as that
module's generic floor and let the listings' 6 win where it is larger — one
number changed is cheaper than auditing the chip panels.

**D4 — the code the removals orphan.** `link_existing_action_item` and
`open_note_picker` lose their only caller, and
`LinkProjectActionItemsDialog` with them. That dialog carries the exclusive
multi-link filing logic and ~1500 lines of guards in
`tests/test_project_multi_link.py`. Recommended: **keep all three in place,
unreachable**, and file the fact in `BACKLOG.md` so deleting them or
re-exposing them is a decision taken on purpose — not a sweeping diff bolted
onto "remove these buttons" (global rule 10).

**D5 — which combos flex.** Recommended: the value filters only. The numeric
selectors (`Next 7 days`, `Last 30 days` — 80 px, content of 1–3 characters)
keep their width; growing them buys nothing.

## Risks

- **CTkComboBox under `sticky="ew"` is unproven here.** The search entry
  already stretches this way, but a combo places its canvas and button
  internally. If it does not redraw at a stretched width, LRP-M10 needs an
  explicit `configure(width=...)` on each fit instead. Verify with a real
  widget before building the rest of Phase 3.
  *Resolved as built:* `sticky="ew"` was not used. `fit_filters` sets each
  filter's width explicitly, because a grid weight cannot give the slack to
  the filters while taking the shortfall out of the search entry first
  (LSR-D7), and the explicit share is the same rule the columns follow.
  `TOOLBAR_SPACER_WEIGHT` is therefore unchanged, contrary to LRP-M10's
  wording above.
- **Reached further than the Scheduler, not in this plan:**
  `AppSettings.drag_schedule_title_col_width` had to move 220 -> 260 for
  LRP-M6 to take effect at all (`ColumnResizer._load_stored` prefers it over
  a spec default). The Plan screen reads the same scalar for a day box's
  title column (PB-M5, so the two screens' columns line up), so that screen's
  title column widens too and `items_width_floor()` / `day_width_floor()`
  rise from 444 px to 484 px. Accepted rather than decoupled: leaving the
  Plan screen at 220 while the Scheduler drew 260 would break the one thing
  the shared scalar exists for. `tests/test_plan_screen.py` is green (243
  passed), the `items_col_width` docstring and the USER_GUIDE's 444 are
  corrected, and the consequence is in the CHANGELOG.
- **Found while building, not in this plan:** a threshold measured from the
  filters' drawn widths made `fit` non-monotone — fitting resized the
  filters, which moved the threshold. `one_row_px()` counts them at their
  defaults and `min_one_row_px()` at their minimum, and
  `test_lrpm11_the_threshold_does_not_move_as_the_filters_resize` holds it.
- **LRP-M1 moves the clipping to the right edge.** Better than the left, where
  the SPC bug hid, but still clipping: there is no window `minsize` (SPC D11).
- **Phase 2 touches all nine screen modules.** One build batch at a time in
  this checkout; the three phases are sequential commits, not parallel work.

## Verification

Targeted runs only: `tests/test_column_resize.py`,
`tests/test_list_screen_resize.py`, `tests/test_scheduler_column_resize.py`,
`tests/test_screen_resize_spc.py`, `tests/test_project_note_chooser.py`,
`tests/test_project_multi_link.py`, `tests/test_project_board_bulk_edit.py`,
plus the new conformance file. The full suite is CI's.

The app is not launched by this session (standing rule). A walk checklist is
written at the end of the batch, as with DBC and SPC.
