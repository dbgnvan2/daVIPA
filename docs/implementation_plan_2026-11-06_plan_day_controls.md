# Implementation plan — Plan screen day controls (PD-M1 … PD-M13)

Date: 2026-11-06
Status: **PD-M1 … PD-M6 shipped 2026-11-06. PD-M7, PD-M8, PD-M9, PD-M10, PD-M11, PD-M13 and the unplanned PD-M1.6, PD-M2.8 and PD-M2.9 shipped 2026-11-07. PD-M11 corrects PD-M10, which treated the symptom and not the cause; PD-M12 corrects PD-M11's reading of reports 2 and 3, which were a different fault entirely; PD-M12 was built, reported broken on the running app — its dialog hung the application — and is superseded by PD-M13, which takes the modal off the drop path instead of replacing it**
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
| PD-M1.6 | The bar stack takes the title's own vertical justification: centred on the line, not pinned to the top or the bottom of the row, and the bars fill the stack with no slack at either end | `::test_pdm16_the_depth_bars_are_justified_like_the_text_on_the_line` — unplanned; reported from the screen three times, as "justified TOP", then "should be BOTTOM", then "justify vertically like TEXT on the line" |

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
| PD-M2.7 | The items column is never narrower than one of its own rows, by setting or by drag, and the fallback is floored too | `::test_an_unusable_items_column_width_falls_back_rather_than_collapsing`, `::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it` |

| PD-M2.8 | The gap between the panes is 15px and all of it is grip: no pad between a pane and the grip | `::test_pdm28_the_grip_is_the_whole_gap_between_the_panes` — unplanned; reported from the screen |
| PD-M2.9 | The clamp measures both floors against the window less the grip and the two edge pads | `::test_pdm29_the_clamp_leaves_room_for_the_grip_and_the_edges` — unplanned; found while widening the grip |

**PD-M2.7 was not planned. It is a defect PD-M1 shipped, found here.**

**PD-M2.8 and PD-M2.9 were not planned either.** The grip shipped at 6px with
a 2px pad on each side: a 10px gap on screen of which only the middle 6px
started a drag. Widening it to 15px and taking the pads out makes the gap and
the grip one thing. PD-M2.9 is the defect that exposed: the clamp compared both
floors against the whole window width, though 26px of it was grip and edge
padding and none of it was pane. The day pane has nothing holding it open, so
all of that came off the day — the clipping the floors exist to prevent — and
the wider grip would have made it 35px.

Building the clamp meant putting a number on what a row needs, and the number
came out at 360px: the stripe's column, the 220px Drag Schedule title width,
the bars, the length, and the pane's chrome. The items column ships at 260. So
(PD-S later added the marker column and the right-hand inset, taking the same
floor to 384px -- the number below is the one PD-M2 shipped, kept as the record
of what was measured then.)
at the app's own default settings an item row asked for 306px of content inside
a 256px pane and the `30m` label was laid out from x=258 to x=306 -- entirely
past the right edge, invisible, in every row.

`::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it` was written to
catch exactly this and did not, because it built its row directly with
`title_width` left at its default -- `SLOT_TITLE_WIDTH_PX`, which is the 80px
*fallback*, not the setting's 220px default. A test that builds the widget
itself chooses its own inputs, and the one it chose was the only width that
fits. It now builds the row through `PlanScreen`, so the widths are the user's.

The fix is the floor, for the same reason PB-M5.6 floors the box height: a
column too narrow to draw what it holds is a clipped widget with nothing on
screen to say so. It makes the default left pane 360px rather than 260, which
is the honest cost of the two panes lining up -- and PD-M2's own grip is what
lets the user move it from there. PD-S took it to 384px.

`_positive_setting` turned out to apply `minimum` to a parsed value and not to
the fallback. For the box height that could never show, since there the two are
the same constant; here they are not, so a zero in the settings file took the
unfloored 260 and clipped the row by the one path that skipped the guard. Fixed
in the helper rather than at this one call site.

---

## PD-M3 — An "AutoLoad" button

**Ask:** "Have a button 'AutoLoad' that automatically puts all the items into
the day blocks — one after another."

Button in the header beside `+ Break` / `+ Buf`. Decisions, stated rather than
discovered during implementation:

- **What it takes:** the items the left pane is showing, in the order shown,
  skipping any already blocked today. (That list is already capped at
  `MAX_ITEM_ROWS` and the cap is announced; AutoLoad plans what is on screen.)
- **Where each goes:** ~~`first_free_slot(minutes)` — the earliest box that
  will hold it, which is what "one after another" means on a grid that already
  has work, lunch and padding in it.~~ **Corrected during implementation:**
  `first_clear_slot(minutes)`, the earliest box with nothing in it at all. A box
  holds four tasks, so `first_free_slot` — the earliest box that is not *full* —
  answers 08:00 four times running on an empty default day: AutoLoad would have
  stacked the first four items four deep at 08:00, the next four at 08:30, and
  called that a planned day. The depth is for a second task a person
  deliberately puts beside a first; a button that fills it is not planning a
  day, and it is not what "one after another" asks for. Every box of a
  multi-box task must be clear, not only the one it starts in.
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
| PD-M3.1 | Every item that fits is blocked, in list order, at the earliest box with nothing in it; a multi-box task takes its own boxes and the next item starts after them | `tests/test_plan_screen.py::test_pdm31_autoload_fills_in_list_order`, `::test_pdm31_autoload_gives_a_long_task_its_own_boxes`, `::test_pdm31_a_long_task_does_not_land_on_a_later_occupied_box` |
| PD-M3.2 | An item already blocked today is skipped, not blocked twice | `::test_pdm32_autoload_skips_an_item_already_blocked` |
| PD-M3.3 | Existing blocks are not moved, resized or deleted | `::test_pdm33_autoload_leaves_existing_blocks_untouched` |
| PD-M3.4 | Nothing is placed across lunch or past Day End | `::test_pdm34_autoload_does_not_straddle_lunch`, `::test_pdm34_autoload_does_not_run_past_the_day_end` |
| PD-M3.5 | The status line reports blocked / did not fit / already blocked, all three | `::test_pdm35_autoload_reports_all_three_counts` |
| PD-M3.6 | On a day with no room, nothing is written and the status says so | `::test_pdm36_a_full_day_writes_nothing` |
| PD-M3.7 | A refusal partway rolls the whole run back | `::test_pdm37_autoload_is_one_transaction` — in `test_plan_screen.py`, not `test_time_block_crud.py` as planned: `autoload_day` is a screen method and the rollback is only observable through it |
| PD-M3.8 | Not offered on a non-working day — the `_require_block_day` refusal | `::test_pdm38_autoload_refuses_a_non_working_day` |
| PD-M3.9 | A day with no items says so, in words that are not "no room" | `::test_pdm3_autoload_on_an_empty_list_says_so` — unplanned: the two are different facts about the day and a shared sentence would hide which one it is |

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
2. ~~Existing blocks store clock times, and the grid is rebuilt from those, so
   moving `day_start` earlier should leave them where they are. "Should" is not
   a test; PD-M5.5 makes it one.~~ **This premise was wrong, and PD-M5.5 is
   what found it.** A block stores `slot_index`, its position counted from Day
   Start, and `build_day_grid` lays the day out from *that*; `start_time` is
   derived and rewritten by `_settle_block_on_slot`. So moving `day_start` back
   one box slides every planned task half an hour earlier on the grid while the
   `start_time` in its own row still says otherwise — which is exactly what
   `tests/test_time_block_crud.py::test_tgm64_a_day_start_change_writes_no_rows`
   documents as the design, and it is the right design for a Day Settings
   change. It is not what a drop above the day asks for. So the extend path
   renumbers: `DatabaseManager.shift_all_slots(by)`, inside the
   same transaction, before the new block, leaving `start_time` and `end_time`
   untouched because they are the fact being preserved. That module's own
   docstring, which said there was "nothing to renumber", is corrected in the
   same change.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M5.1 | A virtual box is drawn above the first slot and below the last, every redraw | `tests/test_plan_screen.py::test_pdm51_a_virtual_box_sits_at_each_end` |
| PD-M5.2 | A drop on the top box moves Day Start back by the item's span and blocks it there | *withdrawn by PD-M14 — the day's hours became a template, so the drop no longer touches the bound; `::test_pdm52_a_drop_above_moves_day_start_back` is deleted, and what holds now is* `tests/test_plan_screen.py::test_pdm141_a_drop_on_earlier_writes_no_settings` |
| PD-M5.3 | A drop on the bottom box moves Day End forward by the span and blocks it there | *withdrawn by PD-M14, at the other end; `::test_pdm53_a_drop_below_moves_day_end_forward` is deleted, and what holds now is* `tests/test_plan_screen.py::test_pdm141_a_drop_on_later_writes_no_settings`. *`::test_pdm53_a_drop_below_does_not_renumber_the_day` is a different test, and is live* |
| PD-M5.4 | Extending does **not** clear `plan_day_shape_unconfirmed` | `tests/test_plan_settings.py::test_pdm54_extending_the_day_is_not_confirming_it` |
| PD-M5.5 | Every existing block keeps its clock time when either bound moves | `tests/test_time_block_crud.py::test_pdm55_blocks_keep_their_times_when_the_day_grows` (+ `::test_pdm55_a_shift_of_zero_writes_nothing`, `::test_pdm55_a_block_outside_the_grid_is_not_given_a_box`, `::test_pdm55_every_date_is_renumbered_not_only_the_one_on_screen`), and *(`tests/test_plan_screen.py::test_pdm52_existing_blocks_keep_their_clock_times`, which no longer exists — one of the nine dead bare names in `BACKLOG.md` PDT-A1)* — in `test_time_block_crud.py` rather than `test_time_block_layout.py` as planned, because keeping the time turned out to need a *write*, not arithmetic |
| PD-M5.6 | A refused settings write leaves the day, the grid and the app as they were | *withdrawn by PD-M14 together with `_DayNotWritten`, which is what the refusal was built on (`docs/changes/2026-11-08-day-hours-are-a-template-wip.md`); `::test_pdm56_a_refused_write_leaves_the_day_unchanged` is deleted and is one of the nine dead bare names in* `BACKLOG.md` *PDT-A1. Recorded* **withdrawn** *in* `docs/spec_coverage.md` |
| PD-M5.7 | The virtual boxes are not droppable for a *block* drag — a block cannot invent a half hour | `::test_pdm57_a_block_drag_onto_a_virtual_box_is_refused` |
| PD-M5.9 | A real box always wins over a virtual one, so a box flush against the Earlier box still gets its own drops | `::test_pdm5_a_real_box_wins_over_a_virtual_one` — unplanned; the read order is a one-line change nothing else would notice |
| PD-M5.10 | The drop gesture itself routes to the right end, not only the method | `::test_pdm5_an_item_drag_onto_a_virtual_box_extends_the_day` — unplanned; without it the extension is only reachable by calling `extend_day_for` |
| PD-M5.11 | Extending is refused on a non-working day, like every other write on this screen | *withdrawn by PD-M13.1 — the test is deleted; the replacement is* `::test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day` |
| PD-M5.8 | Midnight is the floor and the ceiling: the day cannot be extended past either | `tests/test_time_block_layout.py::test_pdm58_the_day_cannot_cross_midnight`, `::test_pdm58_the_ceiling_is_the_last_bound_that_yields_a_whole_box` — the ceiling is a Day End of **23:30**, not 24:00: a box running 23:30–24:00 would need a Day End that is not a time of day, so 23:30 is the last bound that yields a whole box. Refused rather than clamped, because a clamped bound makes fewer boxes than the item needs |

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

The green comes from the existing success token in `theme.py`, never a literal.

**Corrected during the build:** `semantic_colors()` has no `"success"` key --
it has `success_strong`, and reading `["success"]` raises `KeyError`. The token
used is `status_text_color("success")`, which is the one `theme.py` exposes for
exactly this.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M6.1 | A box whose task's item is completed draws a check left of the time | `tests/test_plan_screen.py::test_pdm61_a_completed_task_shows_a_check_left_of_the_time` |
| PD-M6.2 | An open task draws no check, and the row's geometry is unchanged | `::test_pdm62_an_open_task_shows_no_check` |
| PD-M6.3 | The check uses the theme's success token, not a literal colour | `::test_pdm61_a_completed_task_shows_a_check_left_of_the_time`, second assertion -- the colour is a property of the rendered check, so it is asserted where the check is found, not in a second test that would have to build the same row |
| PD-M6.4 | A continuation box of a completed task shows it too — the box is spent either way | `::test_pdm64_a_continuation_of_a_completed_task_shows_the_check` |
| PD-M6.5 | A block whose item has been deleted draws no check and does not raise | `::test_pdm65_a_block_whose_item_is_gone_draws_no_check`, `::test_pdm63_a_box_with_one_task_still_open_shows_no_check`, `::test_pdm66_a_break_in_the_box_does_not_hold_it_open` |

---

## PD-M7 — A non-working day is a warning, not a wall

The screen opens on today. Today is as likely to be a Saturday as any other
day, Saturday and Sunday are off in `DEFAULT_BLOCK_WEEKDAYS`, and
`_require_block_day` returned False at all four write paths: AutoLoad before it
read a single item, a dropped item before a block was written, a padding block,
and an extension of the day. Four gestures that did nothing but write a status
line, which reads as the screen being broken rather than as the day being
closed. Reported as "AutoLoad doesn't work" and "Drag and Drop doesn't move
item", and both were this one guard.

The weekday list describes a normal week. It is not a lock on the calendar, and
a Saturday someone has decided to work is not a mistake to be corrected — so
the guard asks instead of refusing.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M7.1 | A write onto a day outside the weekday list asks before it writes, naming the date and the days the week allows | `tests/test_plan_screen.py::test_pdm132_a_button_still_asks_on_a_non_work_day` — narrowed by PD-M13.1 to the gestures that come from a button |
| PD-M7.2 | Yes writes the block | `::test_pdm132_a_button_still_asks_on_a_non_work_day`, second half |
| PD-M7.3 | No writes nothing and leaves the refusal's own sentence, weekday list included | `::test_pdm132_answering_no_writes_nothing` |
| PD-M7.4 | The question is asked once per date, not once per drop, and the answer is held on the screen only | `::test_pdm132_the_question_is_asked_once_per_date` |
| PD-M7.5 | A day inside the weekday list asks nothing, and is told nothing | `::test_pdm7_a_work_day_says_nothing` |

> **Renamed 2026-11-07.** Every test in this table was rewritten by PD-M13,
> which moved the question off the two drop paths. The criteria stand for the
> gestures that still ask; PD-M13.1 is what a drop does instead.

**Not code-testable, human review:** that Yes-for-the-sitting is the right
scope. It could have been per drop (noisy), or written to the weekday list
(which would silently change the user's working week from a drag). Held on the
screen, it lasts as long as the screen does.

---

## PD-M8 — A "Clear Day" button

The reverse of AutoLoad: one click that takes the day's tasks back off it. The
day was undoable only one block at a time, through the right-click menu, which
is a dozen gestures to throw away a plan that took one.

Item blocks only, because that is what AutoLoad writes. A break or a buffer was
put there by hand, one gesture each, and taking them out would be a deletion
nobody asked for -- so the question says how many are staying. Lunch is not a
block at all; it comes from Day Settings.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M8.1 | A header button labelled Clear Day calls it, styled as destructive rather than primary | `tests/test_plan_screen.py::test_pdm8_the_header_has_a_clear_day_button` |
| PD-M8.2 | Every item block on the selected date is removed, and the status says how many of how many | `::test_pdm8_clear_day_removes_every_item_block` |
| PD-M8.3 | Break and buffer blocks are left in place, and both the question and the status account for them | `::test_pdm8_clear_day_leaves_breaks_and_buffers` |
| PD-M8.4 | It asks first, with the count and the date in the question, and No removes nothing | `::test_pdm8_answering_no_removes_nothing` |
| PD-M8.5 | A day with no items scheduled says so and asks nothing | `::test_pdm8_a_day_with_no_items_says_so_and_asks_nothing` |
| PD-M8.6 | It asks nothing about the weekday list: a non-working day can be cleared | `::test_pdm8_clear_day_asks_nothing_about_the_weekday_list` |
| PD-M8.7 | One transaction, so a failure part-way leaves the day as it was | *(not separately tested — `delete_time_block` has no failure mode to inject without patching the connection; the transaction is asserted by inspection, and `tests/test_weekly_tactic_cascade.py::test_wt_m4d1_cascade_runs_in_one_transaction` covers the helper itself)* |

**Not code-testable, human review:** that "clear" means items and not blocks.
A user who put three buffers on the day and presses Clear Day may expect an
empty grid. The question names the number staying, which is the whole of the
mitigation.

---

## PD-M9 — A scheduled item is checked, an unscheduled one questioned

"A schedule item gets a GREEN Check Mark. An unscheduled item gets a RED ?"

The marker column said something about a blocked item and nothing at all about
the rest, so an unscheduled item and an unmarked row looked the same. It now
says one of two things on every row.

The check is the same glyph a day box uses for "this task is finished"
(PD-M6). The two readings are kept apart by the pane, not by the glyph, which
is the cost of the colours and is recorded where the constant is.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M9.1 | A scheduled row draws the check in the scheduled colour, an unscheduled row the question mark in the unscheduled colour, both in the marker column | `tests/test_plan_screen.py::test_pdm9_a_scheduled_item_is_checked_and_an_unscheduled_one_questioned` |
| PD-M9.2 | Exactly one mark per row, either way | same test |
| PD-M9.3 | Both marks clear 4.5:1 against every priority fill, in both themes | `tests/test_time_block_colors.py::test_pdm9_the_two_marks_are_legible_on_every_fill` |
| PD-M9.4 | The colours are theme tokens, not literals in a screen file | `src/getmoredone/theme.py` (`scheduled_mark`, `unscheduled_mark`); the screen reads them by name |

**On the colours.** `success_strong` and `danger` could not be used as they
are. The marks sit on a priority *fill*: pale tints in the light theme, deep
ones in the dark theme, where `success_strong`'s dark green measures 1.63:1
against the green fill. So the light theme takes the dark pair and the dark
theme the light one, and the test above is what holds them to the text bar.

---

## PD-M10 — A rebuilt pane is on screen before the next event

Three things reported from the running app, which turned out to be one cause:

1. "Drag inside a day to earlier or later doesn't seem to work."
2. The pointer carried the message "Fix login bug" with no drag in progress.
3. "The Day block pane isn't refreshing right away, seems to wait for a mouse
   movement of the app window."

Both panes are rebuilt by taking the scroll frame out of the grid, destroying
its children and putting it back. Tk draws from an idle handler, and every one
of those rebuilds runs inside an event callback or an `after_idle` of one, so
the re-gridded frame could stay undrawn until some later event arrived. In the
app that event was the next mouse movement over the window.

That accounts for all three. `move_block_to_slot`, `set_block_minutes` and
`add_padding_block` end in `load_blocks` alone, so a block moved to an earlier
or later half hour was written and not drawn — report 1 with no defect in the
move itself. And `_end_drag` hid the drag label without drawing the hiding,
which is report 2, made reachable in the first place because the label was
built on the *press*: an ordinary click on an item row put its title beside the
pointer and left it there.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M10.1 | `load_blocks` flushes the redraw once after re-gridding the pane | `tests/test_plan_screen.py::test_pdm101_rebuilding_the_day_pane_flushes_the_redraw` |
| PD-M10.2 | `load_items` does the same | `::test_pdm102_rebuilding_the_items_pane_flushes_the_redraw` |
| PD-M10.3 | A press with no motion builds no drag label | `::test_pdm103_a_press_without_motion_shows_no_drag_label` |
| PD-M10.4 | The first motion shows it with the dragged thing's name; a later motion moves that label rather than building another | `::test_pdm104_the_first_motion_shows_the_label_and_the_second_moves_it` |
| PD-M10.5 | Ending a drag unplaces the label and flushes, so a release that lands on nothing still clears it | `::test_pdm105_ending_a_drag_hides_the_label_and_flushes` |
| PD-M10.6 | A flush on a screen Tk has already torn down does not raise out of the `finally` it is called from | `::test_pdm106_a_flush_on_a_screen_that_is_gone_does_not_raise` |

**`update_idletasks`, not `update`.** Idle tasks are geometry and redisplay,
which is all that is owed. `update` also services the event queue, and these
rebuilds run from drag handlers: dispatching a queued click in the middle of
one would re-enter a rebuild that is destroying the widget the click is for —
the hang the `after_idle` in `on_drag_release` exists to avoid.

**Superseded in part by PD-M11.** The flush added here was not wrong, but it
was not the fix: the rebuild it was added to — which takes the scroll frame out
of the grid — is what kept the pane off the screen, and PD-M11.1 is the
correction. The reasoning below about `update_idletasks` still holds, and
PD-M11 has the measurement that settles it.

**Not code-testable, human review:** that the panes now repaint on the machine
that reported it. No test can see the screen; the tests pin that the flush is
asked for, at the end of each rebuild and when the label is hidden.

**Left as it is:** a block dropped on the Earlier or Later box is still
refused (PD-M5.7), and that refusal is a decision, not this defect. Its warning
was one of the messages the missing flush could hide, so it is worth re-reading
on the running screen before deciding whether the rule itself should change.

---

## PD-M11 — The pane repaints, and both ends of the day can be reached

Four more reported from the running app. The first three are one cause, and it
is the cause PD-M10 got half right.

1. "Moving a Day Block creates a blank panel that immediately shows if the
   mouse moves outside the panel area."
2. "I can't move an item into the early or late extended sections."
3. "Scheduling on a non work day creates a message, but *schedule anyway*
   doesn't work (or the item doesn't show up)."
4. "The Day Plan window should scroll as I drag an item up or down to an area
   not shown."

**What PD-M10 missed.** It read the symptom as a missing flush and added one.
The flush was not the problem: the rebuild around it was. Both panes were
rebuilt by taking the scroll frame out of the grid, destroying its children,
building the new rows and putting the frame back. A `CTkScrollableFrame` is a
frame of rows inside a canvas inside a frame, and it is the outer frame that
leaves the grid — so the canvas is unmapped with it, and on the way back both
the width of the canvas window the rows are drawn in and the scrollregion are
restored by `<Configure>` handlers, which run when the event queue is next
serviced. An idle flush does not service it. The pane came back blank and
filled itself in on the next event, which in use was the next mouse movement.
That is report 1 in its own words, and it is why PD-M10's flush changed the
symptom from stale to blank rather than curing it. Rebuilt in place there is
nothing to restore: destroying and rebuilding rows where they are costs one
more layout pass and nothing else, because Tk does its geometry at idle and
draws no intermediate state unless something asks it to mid-rebuild.

Reports 2 and 3 are that pane, twice. A drop on **Earlier** writes the day's
new hours and the block (~~`test_pdm52_a_drop_above_moves_day_start_back` covers
the write~~ — **withdrawn by PD-M14**: the drop writes the block and no hours,
and that test is deleted; see the PD-M5.2 row above), and *Schedule anyway* writes the block
(`test_pdm132_a_button_still_asks_on_a_non_work_day`, named
`test_pdm7_a_non_work_day_asks_before_scheduling` when this was written,
covers that one); both then
redraw a pane that did not come back. Report 2 had a second cause of its own,
below.

> **Corrected 2026-11-07 by PD-M12.** The paragraph above is wrong, and it was
> wrong in the way that matters: it reasoned from two passing tests to the
> conclusion that the writes were happening and only the repaint was missing.
> They were not happening. Both write paths begin by asking whether the day is
> a work day, that question was `messagebox.askyesno`, and on macOS it raises
> from the idle callback a drag release schedules. The user's own traceback is
> in PD-M12. The tests passed because conftest replaces every `messagebox`
> function with a recorder that cannot raise, so the one call that fails in the
> running app is the one call no test makes. PD-M11's repaint and reach fixes
> are still right and still needed — reports 2 and 3 simply were not about
> them, which is why the user saw no change.

**`update` was tried and rejected, with a measurement.** The macOS display
path draws on a pass of the platform run loop, which `update` turns and
`update_idletasks` does not, so `update` is the call that paints. It costs too
much to have in this path: with it at the end of every pane rebuild, six tests
of this screen took four minutes and 120% of a CPU, on the machine the user was
working on. It is also the hang `on_drag_release`'s `after_idle` exists to
avoid. So the flush stays at idle tasks, and whether that is now enough — with
no unmap for it to recover from — is PD-M11.8, a look at the screen.

**The two ends of the day were unreachable, and not only unpainted.** They were
rows of the scrolling grid, above the first half hour and below the last. A
day of eighteen half hours is several hundred pixels taller than the pane, so
the **Later** box was below the bottom of it, and there was no way to scroll
while holding a drag — no gesture reached it at all. Both ends now sit in
holders of their own, outside the scroll frame: one above it, one below it,
always on screen. That moved them out from under `virtual_under_pointer`'s
first guard, which refused unless the pointer was inside `blocks_scroll` —
correct while they were rows of that grid, and a refusal of every drop on them
once they were not. Every existing test of that drop passed either way, because
the helper that places the pointer puts it inside `blocks_scroll` as well;
PD-M11.4 is the test that does not.

| ID | Criterion | Verified by |
|---|---|---|
| PD-M11.1 | Both panes are rebuilt in place — neither leaves the grid to be rebuilt | `tests/test_plan_screen.py::test_pdm111_a_rebuild_leaves_the_day_pane_in_the_grid`, `::test_pdm111_a_rebuild_leaves_the_items_pane_in_the_grid` |
| PD-M11.2 | The two ends of the day are drawn outside the scrolling grid, in holders of their own in the day pane | `::test_pdm112_the_two_ends_of_the_day_are_outside_the_scrolling_grid` |
| PD-M11.3 | A redraw refills those holders instead of stacking a second box in them | `::test_pdm113_a_redraw_does_not_leave_a_second_box_at_either_end` |
| PD-M11.4 | A drop on an end is recognised with the pointer nowhere near the scrolling grid | `::test_pdm114_a_drop_on_an_end_needs_no_pointer_in_the_scrolling_grid` |
| PD-M11.5 | A drag held at the top or bottom edge of the day's viewport scrolls the day, on its own clock, the same distance per tick whatever the platform's scroll increment is | `::test_pdm115_the_day_canvas_is_the_scroll_frames_master`, `::test_pdm115_the_pointer_at_the_bottom_edge_scrolls_down`, `::test_pdm115_the_pointer_at_the_top_edge_scrolls_up`, `::test_pdm115_the_pointer_in_the_middle_scrolls_nothing`, `::test_pdm115_a_pointer_beside_the_day_scrolls_nothing`, `::test_pdm115_a_tick_is_the_same_distance_on_any_platform`, `::test_pdm115_a_drag_held_at_the_bottom_edge_scrolls_the_day` |
| PD-M11.6 | A tick with the pointer out of the edge zone, or with no drag in progress, scrolls nothing and schedules nothing | `::test_pdm116_a_tick_outside_the_edge_zone_stops_the_scroll`, `::test_pdm116_a_tick_with_no_drag_scrolls_nothing` |
| PD-M11.7 | Ending a drag cancels the pending tick rather than forgetting it | `::test_pdm117_ending_a_drag_cancels_the_scroll` |
| PD-M11.8 | On the running app: the day pane is on screen as soon as a block moves; an item dropped on **Earlier** and on **Later** lengthens the day; *Schedule anyway* shows the block it wrote | *(not code-testable — no test can see the screen)* |

**PD-M5.1's test changed, and why.** It asserted that the Earlier box was a row
of the scrolling grid above every slot row and the Later box a row below them
all. That was a true statement about the arrangement where the Later box could
not be reached. The criterion — one above the first box, one below the last —
is unchanged; it is now counted in the day pane's rows rather than the grid's.
Case (b) of the repo's test rule: the behaviour changed on purpose.

**Adjacent issues found, not fixed.**

- **The same remove-and-rebuild pattern is on six other screens** —
  `today.py`, `upcoming.py`, `all_items.py`, `completed.py`, `hierarchical.py`
  and `vps_planning.py`, all from `9525d94` ("Fix GUI flickering by preventing
  intermediate renders during screen refresh"). Every one of them unmaps a
  `CTkScrollableFrame` to rebuild it, which is the defect above. None was
  reported, and six screens' worth of UI regression is not a change to make
  alongside this one. Recorded in `BACKLOG.md`.
- **`drag_schedule.py` still builds its drag label on the press**
  (`drag_schedule.py:1340`, `:1344`), the defect PD-M10.3 fixed here.

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

## PD-M12 — The question is asked by the app, not by the platform *(superseded by PD-M13)*

> **Superseded 2026-11-07.** Built, shipped to the user for a walk, and
> reported back as *"broken - it just hangs..."*. The diagnosis in this
> section is correct and PD-M13 keeps it; the remedy is not. An in-app
> `CTkToplevel` with `grab_set` and `wait_window` cannot be raised from the
> `after_idle` callback either: the window never becomes viewable from
> there, so `wait_window` never returns and the grab is up with nothing
> able to take it. The application stopped responding. `confirm_dialog.py`
> is deleted and PD-M12.1 … PD-M12.4 are withdrawn. Read this section for
> the fault; read PD-M13 for what shipped.

Reported on the running app after PD-M11 shipped: "Neither ends allow
scheduling" and "Non-workday schedule on YES does NOT work" — two of PD-M11's
four, unchanged. Reports 1 and 4 were fixed and confirmed on screen.

The user sent the traceback, which named the fault outright:

```
  File ".../screens/plan.py", line 1235, in block_item
    if not self._require_block_day():
  File ".../screens/plan.py", line 1595, in _require_block_day
    if messagebox.askyesno(
  File ".../tkinter/messagebox.py", line 76, in _show
    res = Message(**options).show()
_tkinter.TclError
```

A `TclError` with no message, from the platform's own dialog, raised inside the
`after_idle` callback `on_drag_release` schedules. macOS will not run
`tk_messageBox` from there. The exception propagated out of the Tk callback, so
neither write path got past its first statement:

- `block_item` asks the question, so an item dropped on a half hour of a
  non-work day wrote nothing — report 3.
- `extend_day_for` asks the same question, so an item dropped on **Earlier** or
  **Later** of a non-work day wrote nothing — report 2.

And 2026-11-07 is a Saturday, which is why every gesture the user tried was on
a non-work day and why both reports looked like two faults rather than one.

**Why no test caught it, and why none could.** `conftest.py` replaces every
function in `tkinter.messagebox` with a recorder that returns a canned answer
and cannot raise — installed session-wide, for a good reason of its own: a real
modal in a test run blocks until someone clicks it. The consequence is that the
only call that fails in the running app is a call no test makes. P25, exactly:
a check that exists on one surface and not the one anyone uses. A test asserting
"the block is written when the user says yes" passed against code that could
not ask the question at all.

**What this module does.**

- **PD-M12.1** The question is asked with the app's own dialog
  (`widgets/confirm_dialog.py`): an ordinary Tk toplevel with a grab and
  `wait_window`, which is Tcl's modality and does not go near AppKit's. It also
  takes the words for its buttons, so the yes button says *Schedule anyway*
  rather than *Yes*.
- **PD-M12.2** A question that still cannot be put on the screen does not eat
  the gesture. There are two ways to be wrong here — write without asking, or
  lose the drag — and losing it is what happened: four gestures, nothing
  written, nothing said. So a dialog that fails is logged, the work is
  scheduled, and the status line says the question could not be shown. That is
  also what PD-M7's "a warning, not a wall" means when the warning cannot be
  given. The note is one-shot and belongs to the gesture, not to the day.
- **PD-M12.3** The same guard is the first statement of `extend_day_for`, so
  report 2 is the same fix. Its own test, because its own status line composes
  the note separately — the mutation gate found that line deletable with every
  other test green.
- **PD-M12.4** The suite grows the guard the messagebox one already had:
  `ask_yes_no` is stubbed session-wide, recorded, and answers no. Without it
  every question in the suite would wait out the dialog's own visibility
  timeout, because conftest withdraws every window.

**Not changed, deliberately.** `messagebox` is still used by Clear Day on this
screen and by twenty other call sites across the app. All of them are reached
from a button or a menu, not from a drag release, and none has been reported.
Swapping them is a UI change on surfaces nobody has walked, which is not a
change to make inside a fix to a drop path. One of them is not merely adjacent
but likely live, and it is in `BACKLOG.md`: the Scheduler's drag onto a project
asks through `messagebox` from inside its own `ButtonRelease` handler.

### Acceptance criteria

> Every test named in this table was deleted with the module. The dialog they
> covered hung the application; PD-M13's table is the one that holds.

| ID | Criterion | Test |
|---|---|---|
| PD-M12.1 | The non-work-day question is asked by the app's dialog; the platform's is not on the drop path | `::test_pdm121_the_question_is_asked_by_the_app` |
| PD-M12.1 | The yes button names the gesture | `::test_pdm121_the_question_names_the_answer_it_wants` |
| PD-M12.2 | A dialog that cannot be shown schedules the work and says so | `::test_pdm122_a_question_that_cannot_be_asked_still_schedules` |
| PD-M12.2 | The note is said once, for the gesture, not for every later one on that day | `::test_pdm122_the_note_belongs_to_the_gesture_not_to_the_day` |
| PD-M12.2 | The day-lengthening status line says it too | `::test_pdm122_the_end_of_the_day_says_it_too` |
| PD-M12.3 | A drop on an end of a non-work day lengthens the day and blocks the item | `::test_pdm123_a_drop_on_an_end_of_a_non_work_day_extends_the_day` |
| PD-M12.4 | No test can open a real confirm dialog | `::test_pdm124_a_test_cannot_open_a_real_dialog` |
| PD-M12.5 | On the running app: the dialog appears on a Saturday drop, *Schedule anyway* writes the block, and a drop on either end lengthens the day | *(not code-testable — no test in this suite can build a visible window, and this failure was invisible to every test that did not)* |

`widgets/confirm_dialog.py` itself has no direct test: it builds a toplevel and
waits on it, and every window in this suite is withdrawn. What is tested is the
Plan screen's use of it, the fallback when it raises, and the suite's guard over
it. PD-M12.5 is the rest, and it is a walk.

## PD-M13 — No modal on the drop path at all

Reported on the running app after PD-M12 shipped: **"broken - it just hangs..."**.

PD-M12 read the fault correctly and then made it worse. The platform's dialog
raises a bare `TclError` from the `after_idle` callback `on_drag_release`
schedules; the app's own toplevel does not raise there, it never returns. A
`CTkToplevel` with `grab_set` and `wait_window` cannot become viewable from that
callback, so `wait_window` waits forever with the grab held and nothing able to
take it. One gesture took the whole application down from responding.

So the conclusion is not "ask with a different dialog" but **no modal of any
kind survives that moment on this platform**. The drop paths stop asking.

**What this module does.**

- **PD-M13.1** `block_item` and `extend_day_for` call
  `_require_block_day(ask=False)`: the write goes ahead on a day outside the
  working week and the status line carries the warning. The status line is the
  one place on this screen that cannot fail to appear, and PD-M7's rule for
  this screen was "a warning, not a wall" — this is that rule with the warning
  in the only place that works. The weekday list in Day Settings describes a
  normal week; it was never a lock on the calendar.
- **PD-M13.2** The two button gestures — AutoLoad, and the break/buffer
  button — keep the question. A modal raised from a button press is the
  ordinary case and the platform is content with it, and AutoLoad fills a whole
  day from the item list, which is worth stopping for. The question is now
  wrapped in `try/except tk.TclError` wherever it is asked: a dialog that
  raises logs, allows the day, proceeds, and says which day it was on. Losing
  the gesture is the failure that was reported, and it cannot happen again on
  any path.
- **PD-M13.3** The note is one-shot and belongs to the gesture, not the day:
  it is read by the status line the gesture writes and cleared there. All four
  status lines that can follow a non-work-day write append it — `block_item`,
  `extend_day_for`, AutoLoad and the break/buffer button. Three of those four
  were added because the mutation gate found the line deletable with every
  other test green.

**Withdrawn acceptance criteria.** Two approved criteria asserted the refusal
this module removes, and both are withdrawn rather than re-pointed:

- **TB-M8.2** "A drop on an unchecked weekday creates **no** block and reports
  why" — the second half stands, the first does not. PD-M7 had already softened
  it from a refusal to a question; PD-M13 removes the question from the drop
  path. `::test_tbm82_drop_on_non_block_day_is_refused` is deleted; it had been
  passing only because the suite's messagebox stub answers no.
- **PD-M5.11** "Extending is refused on a non-working day" — the same, for the
  **Earlier** / **Later** path.
  `::test_pdm5_the_day_cannot_be_extended_onto_a_non_block_day` is deleted.

The refusal they covered still exists on the paths that ask, and
`::test_pdm132_answering_no_writes_nothing` covers it there.

**Not changed, deliberately.** `messagebox` is still used by Clear Day on this
screen and by twenty other call sites across the app, all reached from a button
or a menu. The one that is not merely adjacent but likely live is in
`BACKLOG.md`: the Scheduler's drag onto a project asks through `messagebox`
from inside its own `ButtonRelease` handler, which is the same moment this
module is about.

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| PD-M13.1 | A drop on a half hour of a non-work day asks nothing and writes the block | `::test_pdm131_a_drop_on_a_non_work_day_asks_nothing_and_writes` |
| PD-M13.1 | A drop on an end of a non-work day lengthens the day and blocks the item | `::test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day` |
| PD-M13.2 | A button gesture still asks on a non-work day | `::test_pdm132_a_button_still_asks_on_a_non_work_day` |
| PD-M13.2 | The question is asked once per date, not once per press | `::test_pdm132_the_question_is_asked_once_per_date` |
| PD-M13.2 | Answering no writes nothing and leaves the reason on screen | `::test_pdm132_answering_no_writes_nothing` |
| PD-M13.2 | A question that raises does not take the gesture with it | `::test_pdm132_a_question_that_raises_does_not_take_the_gesture` |
| PD-M13.2 | A break added after a failed question says which day it was on | `::test_pdm132_a_break_added_after_a_failed_question_says_the_day` |
| PD-M13.3 | The note is said for the gesture it was raised for, and then cleared | `::test_pdm133_the_note_belongs_to_the_gesture` |
| PD-M13.3 | A work day sees neither the question nor the note | `::test_pdm7_a_work_day_says_nothing` |
| PD-M13.4 | On the running app: a Saturday drop on a half hour writes a block, a drop on **Earlier** and on **Later** lengthens the day, and the app keeps responding | *(not code-testable — no test in this suite can build a visible window, and both of the last two failures were invisible to every test that could not)* |

PD-M13.4 is the walk, and it is the third one for these two reports. The first
two remedies were both written against a correct diagnosis and both failed on
screen, which is the reason this criterion is listed rather than assumed.

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
