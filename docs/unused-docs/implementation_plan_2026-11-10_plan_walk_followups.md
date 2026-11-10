# Implementation plan — Plan screen: the 2026-11-10 walk, and four asks (PF-M1 … PF-M5)

Date: 2026-11-10
Status: **built, green on the full suite, and waiting on one walk.** PF-M1.6 is
the only criterion no test can reach. PF-M4 and PF-M5 landed with the same
change; PF-M2 and PF-M3 are covered by tests that fail without them.
Screen: `src/getmoredone/screens/plan.py`, `src/getmoredone/db_manager.py`
Follows: `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md`,
whose **The walk** at the end was run on this date.

## What the walk settled

| Step | Gesture | Result |
|---|---|---|
| 1 | A moved block repaints the day pane, with no mouse-outside it | **Passes** |
| 2 | A drop on **Earlier** and on **Later** lengthens the day and blocks the item | **Passes** |
| 3 | A drag held at the pane's edge scrolls the day | **Passes** |
| 4 | A non-work day asks before it is written to | **Fails on the drop, passes on the buttons** — PF-M1 |
| 5 | The Scheduler's drag onto a project files without a dialog | **Not run** |

The three passes close the three `BACKLOG.md` entries they name; step 5's entry
stays open until it is walked. Step 4's entry is superseded by PF-M1 rather
than closed: the buttons keep their question and the drop never asked.

One report from the walk needs no work. **Weekly Tactic rows do not appear in
the Items pane**, and that is the built behaviour: `get_items_for_start_date`
excludes `item_type = 'week'` (TB-M7, "they are containers for other items'
scheduling, not work anyone sits down and does"). Only action items belong in
that pane.

---

## PF-M1 — The non-work-day question reaches a single item's drop

**Reported:** "AutoLoad pops the Warning dialog message. Dragging single action
items does NOT — but it should [warn] for single items."

Today a drop on a day outside the working week writes the block and says so in
the status line (`block_item` → `_require_block_day(ask=False)`, PD-M13.1). The
two buttons ask. The asymmetry is deliberate and it is now the complaint.

**Why the question is not simply turned back on where it is.** PD-M13 removed
it from the drop path because two modal attempts had failed there on screen
three hours apart: the platform's `messagebox` raised `_tkinter.TclError` with
no message when opened from the idle callback `on_drag_release` schedules, and
an in-app toplevel with a grab in its place hung the application. Both were
reported from the running screen. That history does not move.

**What changes is where the question is asked.** `on_drag_release` runs
synchronously in the `ButtonRelease` handler; the write is what cannot run
there, because `refresh()` destroys the row whose handler is dispatching (the
comment above `after_idle` states it). So the question goes in the handler and
the write stays in the idle callback:

- The handler asks through the existing `_require_block_day(ask=True)`, which
  carries PD-M13.2's `try/except tk.TclError`. If the platform refuses the
  dialog, the fallback logs, allows the day and says so — which is exactly what
  happens today, so the failure mode is not a step backwards.
- The answer is remembered per date in `_work_anyway`, so a second drop on the
  same Saturday does not ask again, and neither does AutoLoad afterwards.
- Declining schedules nothing and leaves "… is not a regular work day (Day
  Settings allows …)" on the status line, the same sentence a refusal on the
  buttons writes.
- Read the pointer first, ask second, schedule the write third: the pointer has
  to be read while it is still there, and the question must not be asked about
  a drop that landed on the heading or between boxes.

**This is the third attempt at a question on this path.** The first two were
each written against a correct diagnosis and each failed on screen. A dialog
opened from a release handler is not the same moment as one opened from an idle
callback — it is the moment the Scheduler already asks from — but "not the same
moment" is an argument, and the walk is the evidence.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M1.1 | A single item dropped on a non-work day asks before it writes | `tests/test_plan_screen.py::test_pfm11_the_drop_asks_on_a_non_work_day` |
| PF-M1.2 | Answering no writes nothing, schedules nothing, and names the day | `::test_pfm12_declining_the_drop_writes_nothing` |
| PF-M1.3 | A second drop on the same date does not ask again | `::test_pfm13_the_drop_asks_once_per_date` |
| PF-M1.4 | A work day's drop asks nothing, as before | `::test_pfm14_a_work_day_drop_never_asks` |
| PF-M1.5 | A question that raises schedules the write, as today | `::test_pfm15_a_question_that_raises_still_schedules` |
| PF-M1.6 | On the running app: a single item dropped on a Saturday shows the question | *(not code-testable — **The walk**, step 4)* |
| PF-M1.7 | A drop that would refuse asks nothing, so the day's one answer is not spent on it | `::test_pfm17_a_drop_that_cannot_write_asks_nothing` |

## PF-M2 — One block per item per day, said out loud

**Reported:** "I can drag the same item onto the screen more than once. It goes
on once."

Nothing refuses a second block for the same item today. `add_block_at` asks
`can_place`, and `can_place` refuses a *box* that holds four blocks
(`MAX_BLOCKS_PER_SLOT`), not an item that is already on the day — so dropping
an already-blocked item on a free box writes a second block for it, and
dropping it on its own box is refused as a full box, which names the wrong
cause. Which of the two the report saw was not established before this plan;
the fix makes the outcome one thing either way.

`block_item` gains a check ahead of the write: the day's blocks already holding
this `item_id` are looked up, and if there is one the write is refused with
where it is — "**X** is already blocked at 09:00 — drag that block to move it".
The row's `already blocked` mark stays what it is, a passive cue for a list
that is read rather than dragged.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M2.1 | A second drop of the same item writes no second block | `tests/test_plan_screen.py::test_pfm21_a_second_drop_of_the_same_item_writes_nothing` |
| PF-M2.2 | The refusal names the box the existing block is in | `::test_pfm22_the_refusal_says_where_the_block_is` |
| PF-M2.3 | A different item still lands on the same box | `::test_pfm23_a_different_item_still_lands` |
| PF-M2.4 | A break and a buffer are still repeatable: the guard reads item blocks | `::test_pfm24_a_break_is_not_an_item_to_refuse` |
| PF-M2.5 | A drop on **Earlier** or **Later** refuses a second block too | `::test_pfm25_a_drop_on_an_end_also_refuses_a_second_block` |

## PF-M3 — A dropped item lands with the block it is linked to

**Asked:** "When I drag an item onto a block, put it after a linked item if one
is already in the block."

**Second report, from the walk:** "a linked item (continuation from previous
block) should stay at the top of the block — it seems to go to the bottom."

**Third report:** "just ignore weekly tactics."

Two items are **linked** here when either is the other's `parent_id`. That was
not the first reading: the module shipped treating a shared `weekly_tactic_id`
as a link too, on the guess that the tactic was the relation meant. It is not —
a tactic is a container for steps that need not follow one another, and the
ordering it produced reordered the middle of a box on gestures that had nothing
to do with order. The rule is the parent/child pair and nothing else;
`item_links` points at notes, files and URLs, so it cannot be the relation.

Where the new block goes:

- **Partner in the target box** — directly behind it, not at the end.
- **Partner elsewhere on the day, and this item is its child** — at the **top**
  of the box it was dropped on. A continuation carries on from the box above,
  so the end of the box is the wrong place for it.
- **No partner, no parent** — the end of the box, as before.

A box orders its blocks by `position` (`_settle_block_on_slot`), so "top" is
position 1 with the rest moved down one, and both cases go through one
`_insert_at` in `db_manager` rather than two shifting writes.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M3.1 | A child dropped on the box holding its parent sits directly after it | `tests/test_plan_screen.py::test_pfm31_a_child_lands_after_its_parent` |
| PF-M3.2 | A Weekly Tactic sibling is not a link: it joins the end | `::test_pfm32_a_weekly_tactic_sibling_is_not_a_link` |
| PF-M3.3 | An unlinked drop still joins the end of the box | `::test_pfm33_an_unlinked_drop_joins_the_end` |
| PF-M3.4 | A child dropped on a box its parent is not in is unaffected by that | `::test_pfm34_a_link_with_no_block_in_the_box_is_no_rule` |
| PF-M3.5 | A continuation whose parent is in another box lands at the top of this one | `::test_pfm35_a_continuation_lands_on_top` |

## PF-M6 — A box the day grew into accepts a drop

**Reported:** "dragging and dropping on the morning area is now broken", and
"dragging to the bottom to lengthen the day doesn't work either".

The morning one is real and was reproduced: `block_item` passed no `day_span`
to `add_block_at`, so the fit check read **Day Settings' hours** while the user
was looking at a box outside them. Extend the day earlier — which the walk's
step 2 did — and the box above Day Start is on screen, is drawn, takes a drag,
and is refused as *"That is outside the day — Day Settings sets its hours"*.
The same is true at the evening end.

The write now passes the drawn day (`self._grid.span`), which is what
`extend_day_for` already did, and `_drop_refusal` reads the same span so the
pre-check cannot refuse what the write would accept.

This bug predates PF and is not a regression: the same call refused the same
box before the change. It became visible because the walk lengthened the day.

The evening half of the report was not reproduced: a drop on **Later** writes on
a work day and on a non-work day alike, before and after this change. What the
evening end does *not* accept is a drop that misses the **Later** strip while
still inside the day pane — that reports `Drop an item on a half-hour box`, and
whether that is what was seen is a question for the next walk.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M6.1 | A box above Day Start, left by an Earlier drop, accepts a later drop | `tests/test_plan_screen.py::test_pfm61_a_box_the_day_grew_into_accepts_a_drop` |
| PF-M6.2 | A box past Day End, left by a Later drop, accepts a later drop | `::test_pfm62_a_box_the_day_grew_into_at_the_end_accepts_a_drop` |
| PF-M6.3 | The pre-check and the write read the same span | covered by PF-M6.1: the refusal came from the write path |

## PF-M7 — A continuation is drawn at the top of the box it runs into

**Reported:** "a continuation item (same task) is NOT staying at the top of the
block. Each new item pushes the continuation item down. However, each regular
item stays on top and items go below."

`build_slot` drew the box in two passes — everything that *starts* in it, then
everything that *runs through* it — so the greyed `↳` chip was always drawn
last, and every drop into that half hour pushed it further down. The order is
reversed: continuations first, then the tasks that start here, each group in
its own order.

Nothing about the database changes: `position` still orders the blocks that
start in a box, and a continuation chip is the same block drawn again.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M7.1 | A continuation chip is drawn above the tasks that start in that box | `tests/test_plan_screen.py::test_pfm71_a_continuation_sits_above_what_starts_in_that_box` |

## PF-M8 — A day can have a lunch of its own

**Asked:** "Allow the user to move the Lunch item, like they can break and
buffer." Chosen at the fork: **per day**, not for every date.

Lunch has been a property of the day's *shape*: `bounds.lunch_start_minutes` and
`lunch_minutes`, one setting, shaded onto every date's grid and taking no tasks.
Break and buffer blocks are rows, so they move; lunch could not.

A date now gets a lunch of its own by having a `LUNCH` block:

- `BlockType.LUNCH` in `models`, so the three layers agree on the string.
- `lunch_window(blocks, bounds)` in `time_block_layout`: a date's `LUNCH` block
  wins; without one the settings' window is used. `day_grid` takes the window as
  a parameter, so `is_lunch` on a slot has one derivation instead of two.
- `build_day_grid` and `can_place` both read it, so the drawn grid and the
  refusal agree — and a block placed *as* lunch passes `ignore_lunch`, or it
  would be refused by the lunch it defines.
- The screen draws the chip exactly as before. Without a block it is the
  settings', handed back as `SlotRow.lunch_chip` and bound to a drag that
  writes the block on release; with one it is that block's, so drag, resize and
  the right-click menu (including **Delete**) already work.
- **Delete is the way back.** Remove the block and the date is on Day Settings'
  lunch again; nothing remembers an override.
- Length stays a setting: moving lunch moves *when* it is.

Clear Day keeps it, like a break or a buffer: it was put there by hand.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M8.1 | A lunch block replaces the settings' lunch for that date only | `tests/test_plan_screen.py::test_pfm81_a_lunch_block_moves_the_lunch_for_that_date` |
| PF-M8.2 | A lunch box still takes no tasks, wherever it has moved to | `::test_pfm82_a_task_cannot_land_on_the_moved_lunch` |
| PF-M8.4 | Dragging the settings' lunch writes this date's block | `::test_pfm84_dragging_the_lunch_chip_gives_this_date_a_lunch_block` |
| PF-M8.5 | A second drag moves that block rather than writing another | `::test_pfm85_a_second_drag_moves_that_block` |
| PF-M8.6 | Clear Day keeps the lunch block | `::test_pfm86_clear_day_keeps_the_lunch_block` |
| PF-M8.7 | Deleting the block returns the date to Day Settings' lunch | `::test_pfm87_deleting_the_lunch_block_returns_the_date_to_the_settings` |

## PF-M4 — The header is two rows

**Asked:** "Put the Buffer, Break, Calendar and Day Settings buttons on the
line below the Date, Clear Day and AutoLoad buttons."

| Row | Controls |
|---|---|
| 1 | `Plan - Time Blocks`, **Date:** picker, **Clear Day**, **AutoLoad** |
| 2 | **+ Buffer**, **+ Break**, **⤴ Google Calendar**, **⚙ Day Settings** |

Every control survives; what changes is which row it is in (UI regression
policy rule 2 — relocation asked for by name). The status line stays outside
the header on its own row, which `test_cem441b` asserts and this keeps.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M4.1 | The four buttons named are in the second row and the other three in the first | `tests/test_plan_screen_pf_header.py::test_pfm41_the_header_is_two_rows` |
| PF-M4.2 | All seven controls are still on the screen, by name | `::test_pfm42_every_control_survives_the_move` |
| PF-M4.3 | The status line is still outside the header, on its own row | `::test_pfm43_the_status_line_stays_out_of_the_header` |
| PF-M4.4 | The header still fits the default window | `tests/test_plan_screen_calendar_export.py::test_cem441b_the_header_fits_the_window_it_opens_in` (existing, must stay green) |

## PF-M5 — The header's buttons take an equal share of the width

**Asked:** "Resize all the buttons equally as the screen and panels are
resized."

Today every button is packed with a fixed `width=`, so widening the window
gives the extra width to whatever is packed with `expand`, and the buttons stay
90–150px while the panes beside them move. The header becomes a `grid` with one
uniform column group for the buttons and `sticky="ew"`, so each button takes the
same share of what is left, at the same rate, as the window narrows or widens.
The date picker and the title keep their natural widths; the status line is
untouched.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M5.1 | Every button row shares one column group, so widths stay equal | `tests/test_plan_screen_pf_header.py::test_pfm51_the_buttons_share_one_column_group` |
| PF-M5.2 | Widening the window widens all four equally | `::test_pfm52_widening_the_window_keeps_them_equal` |
| PF-M5.3 | Nothing is clipped at the narrowest window the app opens | `::test_pfm53_the_buttons_fit_the_narrowest_window` |

---

## Documents to update when this is built

- `CHANGELOG.md` — one entry per module.
- `docs/USER_GUIDE.md` — the drop now asks on a non-work day, the header is two
  rows, and an item already on the day refuses a second block.
- `docs/spec_coverage.md` — a row per criterion above.
- `BACKLOG.md` — the two entries this closes, and the Scheduler's drag-release
  entry left open because step 5 was not walked.

## Review

Per `CLAUDE.md`: at most two warm passes, at least one cold pass regardless,
severity before any fix. PF-M1 is the risky one — a modal on a path that has
eaten two of them — and it is the one the next walk has to settle.
