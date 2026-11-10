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

## PF-M3 — A dropped item lands after the block it is linked to

**Asked:** "When I drag an item onto a block, put it after a linked item if one
is already in the block."

Two items are **linked** here when either is the other's `parent_id`, or when
both carry the same non-empty `weekly_tactic_id`. That is the reading of
"linked" this building uses; the schema has no item-to-item link other than
those two (`item_links` points at notes, files and URLs). If the walk shows a
different relation meant, this is the module to correct.

When the dropped item's linked partner already has a block in the target box,
the new block takes the position directly after it instead of the end of the
box. A box orders its blocks by `position` (`_settle_block_on_slot`), and an
ordinary drop joins the end — which is right for an unlinked item and wrong for
a follow-on.

| ID | Criterion | Verified by |
|---|---|---|
| PF-M3.1 | A child dropped on the box holding its parent sits directly after it | `tests/test_plan_screen.py::test_pfm31_a_child_lands_after_its_parent` |
| PF-M3.2 | Two items of one Weekly Tactic order the same way | `::test_pfm32_weekly_tactic_siblings_keep_their_order` |
| PF-M3.3 | An unlinked drop still joins the end of the box | `::test_pfm33_an_unlinked_drop_joins_the_end` |
| PF-M3.4 | A linked item dropped on a box with no partner is unaffected | `::test_pfm34_a_link_with_no_block_in_the_box_is_no_rule` |

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
