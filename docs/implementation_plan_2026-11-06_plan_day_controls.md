# Implementation plan — Plan screen day controls (PD-M1 … PD-M6)

Date: 2026-11-06
Status: **awaiting approval — no implementation code written**
Screen: `src/getmoredone/screens/plan.py`, `src/getmoredone/screens/plan_blocks.py`
Follows: `docs/implementation_plan_2026-11-06_plan_box_appearance.md` (PB-M1 … PB-M7, shipped)

Six asks, taken from the request against the screenshot of the Plan screen at a
box height of 30. Each becomes one module with its own acceptance criteria, and
every criterion names the automated test that will verify it. Three criteria
cannot be made code-testable and are flagged as human review at the end.

---

## PD-M1 — The item row is drawn like a day chip

**Ask:** "I want the items on the left to be formatted like the items on the
right. Put time and stack lines next to each other."

Today a day chip (`_build_block_chip`) is one line in four columns — stripe,
title, `DepthBarStack`, minutes — and an item row (`build_item_row`) is two
lines in three, with the bars above the minutes. The two show the same task
before and after it is dragged, and they do not look alike.

The change is to the row's internal layout only. The row's **height** is
unchanged: PB-M6.1 pins it to the space the day will give that work block, so a
60-minute item stays two boxes tall.

This **amends PB-M6.3**, which moved the length under the bars three commits
ago. That decision was "the day's own boxes put it there" — and the day puts it
*beside* the bars, not under them. The earlier plan, `docs/spec_coverage.md` and
the PB-M6 handoff note all have to say so in the same change (working rule 13).

Open question answered here rather than left: the row's second line carries
`already blocked`, which a day chip has no counterpart for. It stays, as a
second line below the chip-shaped first line, and loses the depth word — the
bar stack beside it already says the depth, and saying it twice is what PB-M6.2
removed the priority number for.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M1.1 | The row's first line uses the chip's column order and the same four widths: stripe, title, `DepthBarStack`, `{n}m` | `tests/test_plan_screen.py::test_pdm11_the_item_row_uses_the_chips_column_order` |
| PD-M1.2 | The length label and the bar stack sit on one grid row, adjacent columns | `::test_pdm12_the_length_sits_beside_the_depth_bars` |
| PD-M1.3 | The row is still `item_row_height(span, box_height)` tall — PB-M6.1 regression | `::test_pbm61_an_item_row_is_the_height_the_day_would_give_it` (existing, must stay green) |
| PD-M1.4 | Every child is still drawn inside the frame at the floor and above it | `::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it` (on-screen, `mapped_windows`) |
| PD-M1.5 | The depth word is gone from the second line; `already blocked` is not | `::test_pdm14_the_second_line_is_the_blocked_marker_alone` |

**Note on the mapped-window count:** PD-M1.4 and PD-M6.1 add on-screen tests.
`tests/test_ci_contract.py::test_the_documented_mapped_window_count_is_the_real_one`
asserts the count against `CLAUDE.md:22` and `conftest.py:644`; both have to be
updated in the same commit or CI goes red.

---

## PD-M2 — The divider between the panes drags

**Ask:** "The dividing line VERTICAL between the two areas should slide right
and left to resize the two areas."

The left pane is grid column 0 at a fixed `minsize` from
`plan_items_col_width`; the day takes the rest. The setting exists and is
already editable in Settings, so this adds the gesture, not the storage.

`ColumnResizer` (`screens/column_resize.py`) is **not** the vehicle: it resizes
columns *inside* a table row and persists to `<prefix>_col_widths`. This is a
splitter between two top-level grid columns. A new, small widget — a 6px grip
frame in a new column 1, with `<Button-1>`/`<B1-Motion>`/`<ButtonRelease-1>` —
is the smaller change and leaves `ColumnResizer` alone.

**P41 applies directly.** `PlanScreen.__init__` does
`self.settings = getattr(app, "settings", None)` — this screen's settings object
*is* the app's object. So the release handler must write through the same
discipline the Settings screen now uses: mutate, save, and on a refused save put
the previous value back before returning, so the running app never holds a width
the file does not.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M2.1 | A drag of the grip changes column 0's `minsize` by the pointer delta | `tests/test_plan_screen.py::test_pdm21_dragging_the_grip_changes_the_items_column` |
| PD-M2.2 | The width is clamped to a usable range; neither pane can be dragged shut | `::test_pdm22_the_width_is_clamped_at_both_ends` |
| PD-M2.3 | Motion does not write the settings file; release writes it once | `::test_pdm23_the_file_is_written_once_on_release_not_per_motion` |
| PD-M2.4 | A refused write leaves the running app the width it had, and says so | `::test_pdm24_a_refused_write_leaves_the_old_width` (P41) |
| PD-M2.5 | The dragged width survives a rebuild of the screen | `::test_pdm25_the_dragged_width_survives_a_rebuild` |
| PD-M2.6 | Settings and the grip agree: a width set in either is read by the other | `::test_pdm26_the_grip_and_the_settings_field_are_one_value` |

---

## PD-M3 — An "AutoLoad" button

**Ask:** "Have a button 'AutoLoad' that automatically puts all the items into
the day blocks — one after another."

Button in the header beside `+ Break` / `+ Buf`. Decisions, stated rather than
discovered during implementation:

- **What it takes:** the items the left pane is showing, in the order shown,
  skipping any already blocked today. (That list is already capped at
  `MAX_ITEM_ROWS` and the cap is announced; AutoLoad plans what is on screen.)
- **Where each goes:** `first_free_slot(minutes)` — the earliest box that will
  hold it, which is what "one after another" means on a grid that already has
  work, lunch and padding in it.
- **What it never does:** move, resize or delete an existing block. It is purely
  additive, which is also what makes it undoable by hand in an app with no undo.
- **It does not extend the day.** PD-M5 is a deliberate gesture; a button that
  silently lengthened the working day would be a different feature.
- **It reports N of M** (P2): how many were blocked, how many did not fit, and
  how many were skipped as already blocked. A refusal from `add_block_at` is
  counted and reported, never swallowed.
- **One transaction**, so a refusal partway does not leave half a day planned.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M3.1 | Every item that fits is blocked, in list order, at the earliest box that holds it | `tests/test_plan_screen.py::test_pdm31_autoload_fills_in_list_order` |
| PD-M3.2 | An item already blocked today is skipped, not blocked twice | `::test_pdm32_autoload_skips_an_item_already_blocked` |
| PD-M3.3 | Existing blocks are not moved, resized or deleted | `::test_pdm33_autoload_leaves_existing_blocks_untouched` |
| PD-M3.4 | Nothing is placed across lunch or past Day End | `::test_pdm34_autoload_respects_lunch_and_the_day_end` |
| PD-M3.5 | The status line reports blocked / did not fit / already blocked, all three | `::test_pdm35_autoload_reports_all_three_counts` |
| PD-M3.6 | On a day with no room, nothing is written and the status says so | `::test_pdm36_a_full_day_writes_nothing` |
| PD-M3.7 | A refusal partway rolls the whole run back | `tests/test_time_block_crud.py::test_pdm37_autoload_is_one_transaction` |
| PD-M3.8 | Not offered on a non-working day — the `_require_block_day` refusal | `::test_pdm38_autoload_refuses_a_non_working_day` |

---

## PD-M4 — Break, Buffer and Lunch share one colour

**Ask:** "Make the color of Break, Buffer and Lunch the same colour."

`theme.block_type_colors()` already gives `buffer` and `lunch` the same neutral
(`#4B5563` light / `#9CA3AF` dark); only `break` differs (`#155E75` / `#22D3EE`).
The change is one table, in `theme.py`, in both appearance modes — not a
per-screen constant (the theme rule in `CLAUDE.md`).

The three have to stay **distinguishable by their words**, since colour is no
longer doing it: a break says "Break", a buffer says "Buffer", a lunch box says
"Lunch". They already do.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M4.1 | `block_type_colors()` returns one value for all three keys, in both modes | `tests/test_time_block_colors.py::test_pdm41_padding_and_lunch_share_one_colour` |
| PD-M4.2 | The rendered break stripe, buffer stripe and lunch row carry that colour | `tests/test_plan_screen.py::test_pdm42_the_three_render_in_the_shared_colour` |
| PD-M4.3 | That colour still passes the contrast check against the surface behind it | `tests/test_time_block_colors.py::test_pdm43_the_shared_colour_keeps_its_contrast` |

---

## PD-M5 — Dropping above or below extends the day

**Ask:** "Allow items to extend the day earlier or later when they are dropped
above the first block or below the last block — leave a 'virtual block' for
these two areas so there is something to drop into."

Two always-drawn boxes, one above the grid and one below, marked as what they
are ("Earlier" / "Later") and dimmed. A drop on the top one moves
`plan_day_start` back far enough to hold the item; a drop on the bottom one
moves `plan_day_end` forward the same way. Both then place the block in the
half hour that drop created.

**This is the riskiest of the six, for two reasons, and they shape the plan:**

1. `plan_day_start` and `plan_day_end` are two of the four `DAY_SHAPE_KEYS`
   gated by `plan_day_shape_unconfirmed` (TG-M5). That flag is what stops an
   **irreversible** grid adoption running against a day shape nobody chose, and
   only the Day Settings dialog clears it. A drop-extend must write the bound
   and **leave the flag exactly as it found it** — extending a day is not the
   user confirming the four values, and five of this project's high-severity
   findings have been in that flag's neighbourhood.
2. Existing blocks store clock times, and the grid is rebuilt from those, so
   moving `day_start` earlier should leave them where they are. "Should" is not
   a test; PD-M5.5 makes it one.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M5.1 | A virtual box is drawn above the first slot and below the last, every redraw | `tests/test_plan_screen.py::test_pdm51_a_virtual_box_sits_at_each_end` |
| PD-M5.2 | A drop on the top box moves Day Start back by the item's span and blocks it there | `::test_pdm52_a_drop_above_moves_day_start_back` |
| PD-M5.3 | A drop on the bottom box moves Day End forward by the span and blocks it there | `::test_pdm53_a_drop_below_moves_day_end_forward` |
| PD-M5.4 | Extending does **not** clear `plan_day_shape_unconfirmed` | `tests/test_plan_settings.py::test_pdm54_extending_the_day_is_not_confirming_it` |
| PD-M5.5 | Every existing block keeps its clock time when either bound moves | `tests/test_time_block_layout.py::test_pdm55_blocks_keep_their_times_when_the_day_grows` |
| PD-M5.6 | A refused settings write leaves the day, the grid and the app as they were | `tests/test_plan_screen.py::test_pdm56_a_refused_write_leaves_the_day_unchanged` (P41) |
| PD-M5.7 | The virtual boxes are not droppable for a *block* drag — a block cannot invent a half hour | `::test_pdm57_a_block_drag_onto_a_virtual_box_is_refused` |
| PD-M5.8 | Midnight is the floor and the ceiling: the day cannot be extended past either | `tests/test_time_block_layout.py::test_pdm58_the_day_cannot_cross_midnight` |

---

## PD-M6 — A completed task shows a green check left of the time

**Ask:** "When an Item is marked Completed put a GREEN Check mark to the left
of the time."

The time column is the day row's leftmost element, so the check goes at the
start of that row, before `08:30`.

**Where it can and cannot appear, stated:** the left pane's list is
`get_items_for_start_date(..., status_filter="open")` — a completed item is
never in it, so a check there would be unreachable code. This criterion is
about the Day Plan only. `_items_by_id` already fetches the item behind a block
even when it has been completed since, which is exactly the lookup this needs.

The green comes from the existing `success_strong` token in `theme.py`
(`semantic_colors()["success"]`), never a literal.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M6.1 | A box whose task's item is completed draws a check left of the time | `tests/test_plan_screen.py::test_pdm61_a_completed_task_shows_a_check` |
| PD-M6.2 | An open task draws no check, and the row's geometry is unchanged | `::test_pdm62_an_open_task_shows_no_check` |
| PD-M6.3 | The check uses the theme's success token, not a literal colour | `tests/test_time_block_colors.py::test_pdm63_the_check_uses_the_success_token` |
| PD-M6.4 | A continuation box of a completed task shows it too — the box is spent either way | `::test_pdm64_a_continuation_of_a_completed_task_shows_the_check` |
| PD-M6.5 | A block whose item has been deleted draws no check and does not raise | `::test_pdm65_a_block_with_no_item_draws_no_check` |

---

## Implementation order

Smallest and most isolated first, so that the riskiest change lands against a
screen whose other changes are already tested.

1. **PD-M4** (one colour table) — no dependencies, one file.
2. **PD-M6** (the check) — touches `build_slot_row` only.
3. **PD-M1** (the row layout) — touches `build_item_row` only; amends PB-M6.3's
   documents in the same commit.
4. **PD-M2** (the divider) — new widget plus one settings write path.
5. **PD-M3** (AutoLoad) — uses `first_free_slot`/`can_place` as they are; needs
   a transactional bulk write in `db_manager`.
6. **PD-M5** (extend the day) — last, because it changes the day shape every
   other module draws against.

Dependencies: PD-M1 and PD-M6 both touch row rendering but different builders
and can be done in either order. PD-M3 and PD-M5 are independent of each other
by the decision above (AutoLoad does not extend). PD-M2 and PD-M5 both write
settings and should share one guarded-write helper rather than two.

Each module is one `src/` commit plus one `tests/` commit, per the repo's
commit-separation rule.

---

## Not code-testable — human review proposed

1. **"Formatted like the items on the right" is a judgement about how two rows
   read side by side.** PD-M1.1 and PD-M1.2 pin the column order and the
   adjacency, which is the mechanical part of it. Whether the result *looks*
   like the day chip is a look at the screen, at a box height where the
   difference is visible (86, not 30). Proposed: walked on screen, recorded in
   the handoff note, as PB-M6/PB-M7 were.
2. **Whether the divider's drag feels right** — grip width, clamp points,
   whether it tracks the pointer or lags. Same class as the PB-M5 drag-feel row
   still outstanding in `docs/spec_coverage.md`, and should be walked in the
   same pass.
3. **Whether one colour for Break, Buffer and Lunch is still readable** at a
   glance in both appearance modes. PD-M4.3 holds the contrast ratio; it cannot
   say whether a day of three identical neutrals is easier or harder to scan
   than what is there now.

---

## Documents to update when this is built

- `CHANGELOG.md` — one entry per module.
- `docs/USER_GUIDE.md` — AutoLoad, the divider, and the two virtual boxes are
  all new user-facing gestures.
- `docs/spec_coverage.md` — a row per criterion above.
- `docs/implementation_plan_2026-11-06_plan_box_appearance.md` — PB-M6.3
  amended by PD-M1.
- `docs/changes/2026-11-06-plan-day-controls.md` — handoff note.
- `CLAUDE.md:22` and `tests/conftest.py:644` — the mapped-window count, if
  PD-M1.4 and PD-M6.1 land as on-screen tests.

## Review

Per `CLAUDE.md`: at most two warm passes, at least one cold pass regardless,
severity before any fix, below-medium to `BACKLOG.md`. And per P41's new
entry — **run the program before the final cold pass**, not after it, since
every one of the six asks is a gesture that only a walk can exercise.
