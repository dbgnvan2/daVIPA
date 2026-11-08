# Implementation plan — the configured day vs the day as drawn

**Date:** 2026-11-07
**Branch:** a new branch off `claude/plan-day-faults-03c116` (or off `main` once
that branch merges)
**Status:** awaiting approval. No implementation code written.

Four things reported from the running screen. Three came through another
session; the fourth the user added directly, and it changes what the first one
means.

Their words, verbatim:

1. "Clear day doesn't reset the time blocks to range in settings."
2. "User should be able to drag to the Early or Late Block regardless if
   anything is after the Morning block or before the Evening block."
3. "You are simply ignoring the Work day settings and letting me schedule on a
   NON checked Day. Warning happens once on the first block. (if a non break
   /buffer/ lunch block - a non -action item block - is on the Day, allow
   more )."
4. "ADD - when add to start and End of day do NOT change the length of Day in
   Settings."

Asked whether the day-off warning should fire again when only breaks, buffers
or lunch are on the day, they answered: **"No, once per day."**

---

## What the code does today

Established by reading it, not assumed.

**A drop into Earlier or Later writes the user's Settings.**
`PlanScreen.extend_day_with_item` (`src/getmoredone/screens/plan.py:2283`)
computes a new bound and then does
`setattr(self.settings, "plan_day_start" | "plan_day_end", new_bound)` followed
by `self.settings.save()`. One drop on one date permanently redefines the
working day for every date. Item 4 says this must stop, and it is also the
reason item 1 cannot be done as written: once the drop has moved
`plan_day_start`, there is no record of the range the user configured, so
"reset to the range in settings" has nothing to reset to.

**`slot_index` is counted from Day Start, so moving Day Start forces a global
renumber.** `db_manager.shift_all_slots` renumbers **every date's** blocks so
their clock times survive the bound moving, and its own docstring explains why
it cannot be scoped to one date: `plan_day_start` is a single setting that
`DayBounds.from_settings` applies to whatever date is on screen.

**The grid is exactly the configured range, and anything off it is "outside".**
`day_grid(bounds)` produces the half hours from Day Start to Day End.
`build_day_grid` sends any block with `slot_index < 0`, or whose span runs past
the last box, to `DayGrid.outside`, which the screen reports as "N outside the
day". So if the bound stops moving and nothing else changes, an Earlier drop
would land *off* the grid and read as missing — the symptom class this branch
has just spent a batch on.

**Clear Day removes item blocks only** (`plan.py:1378`), keeping breaks and
buffers because AutoLoad never wrote one, and deliberately skips the weekday
gate. It does nothing to the day's range.

**Earlier and Later are built unconditionally**, every redraw, whether or not
the day holds anything (`plan.py:1038-1080`, and the comment there says so).
`extended_day_bound` refuses only a day that would cross midnight. **There is
no adjacency guard anywhere** — nothing keyed on whether a block sits after the
first box or before the last.

**The weekday list is enforced on all four write paths.**
`_require_block_day` gates the padding/break button (`plan.py:1164`), the
item-onto-a-box path (`1209`), AutoLoad (`1275`) and the day extension (`2283`).
Every block write in the app funnels through `db_manager.add_block_at` /
`create_time_block`, and **no screen other than `plan.py` calls either** — so
there is no ungated writer. The gate asks once per date and caches the answer in
`self._work_anyway` for the life of the screen, which is already "once per day".

---

## PD-M13 — the configured day and the day as drawn are two different things

Items 4 and 1. Item 4 is the mechanism; item 1 falls out of it.

The change: **Day Start and Day End in Settings become the day the user
configured, and nothing but Day Settings ever writes them.** The day that gets
drawn is the configured range *widened to cover whatever blocks exist outside
it*. A drop into Earlier adds a block before the configured start and the grid
grows to show it; Clear Day takes that block away and the grid returns to the
configured range by itself, with no reset code of its own.

This also deletes a defect nobody reported: `shift_all_slots` renumbering every
date because of one drop on one date. With the bound fixed, there is nothing to
compensate for.

**The design decision this needs, and my recommendation.** `slot_index` is
counted from Day Start. If Day Start no longer moves, a block dropped earlier
needs a position before box 0. Two ways:

- **(A) Let `slot_index` go negative.** `build_day_grid` lays out from
  `min(0, lowest slot_index)` to `max(last configured box, highest span end)`.
  `shift_all_slots` is deleted. One stored integer per block, no new state, and
  the "outside the day" list keeps its current meaning for blocks that really
  have nowhere to go (a block inside lunch).
- **(B) Keep `slot_index` ≥ 0 and store a per-date start offset.** A new column
  and a migration, and two sources of truth about where a day begins.

**I recommend (A)**, and the plan below assumes it. (B) is written down so the
choice is visible, not because it is close.

**Migration is a real question, and I cannot answer it from here.** Any day the
user has already extended has both a moved `plan_day_start` and slot indices
shifted to match. Under (A) those days stay internally consistent — they are
just days with an early configured start — so **doing nothing is coherent**, and
that is what I would do. What it costs is that their Day Settings keeps whatever
value the extension wrote rather than what they originally typed, which is not
recoverable: the original was overwritten. **Flagged for your decision, not
guessed at.** Needs a human-review line in the status report either way, because
no automated test can tell a configured 07:00 from an extension-written one.

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| PD-M13.1 | An Earlier drop does not change `plan_day_start`, and an Later drop does not change `plan_day_end` | `tests/test_plan_screen.py::test_pdm131_an_earlier_drop_leaves_day_start_alone` |
| PD-M13.2 | An Earlier/Later drop writes no settings file at all | `tests/test_plan_screen.py::test_pdm132_a_day_extension_saves_no_settings` |
| PD-M13.3 | A block before the configured Day Start is drawn on the grid, not listed as outside the day | `tests/test_time_grid.py::test_pdm133_a_block_before_day_start_gets_a_box` |
| PD-M13.4 | A block whose span runs past the configured Day End is drawn, not listed as outside | `tests/test_time_grid.py::test_pdm134_a_block_past_day_end_gets_a_box` |
| PD-M13.5 | A block that genuinely has nowhere to go (inside lunch) is still surfaced in `outside` (P2 — the existing guarantee must not be weakened by 13.3/13.4) | `tests/test_time_grid.py::test_pdm135_a_block_in_lunch_is_still_surfaced` |
| PD-M13.6 | No other date's `slot_index` changes when a day is extended | `tests/test_time_block_crud.py::test_pdm136_an_extension_renumbers_nothing` |
| PD-M13.7 | After Clear Day, the drawn grid is exactly the configured range | `tests/test_plan_screen.py::test_pdm137_clear_day_returns_the_day_to_its_settings_range` |
| PD-M13.8 | Clear Day leaves the configured range itself untouched | `tests/test_plan_screen.py::test_pdm138_clear_day_writes_no_settings` |
| PD-M13.9 | A break or buffer sitting before the configured Day Start keeps its box after Clear Day (the day shrinks to the configured range *or* to what is still outside it, whichever is wider) | `tests/test_plan_screen.py::test_pdm139_clear_day_keeps_a_break_outside_the_range_on_the_grid` |
| PD-M13.10 | Dirty-state (P8): a database whose blocks already carry shifted indices from the old behaviour still draws every block | `tests/test_plan_screen.py::test_pdm1310_a_day_extended_by_the_old_code_still_draws` |

PD-M13.9 is the one I most expect you to disagree with. It is what "reset to the
range in settings" has to mean once breaks survive Clear Day: the day cannot
shrink past a block that is still on it. Say so if you want the opposite.

---

## PD-M14 — Earlier and Later accept a drop regardless of what is next to them

Item 2. **I expect this to be a no-op in code, and the plan is to establish
that before writing any.**

There is no adjacency guard in the source. The Earlier and Later rows are built
on every redraw with a comment saying they are there even for the first item of
the day, and the only refusals on that path are the weekday gate, a missing
settings object, and crossing midnight. On the Saturday this was reported, the
weekday gate funnelled into the dialog that fault PD-M11 turned out to be — it
raised instead of returning an answer, so the drop did nothing and said nothing.
That is fixed on this branch and unreleased, which is why item 2 still reads as
broken in the running app.

So the step is: **checklist item 2 first**, on the built branch. If the drop
works, PD-M14 closes as fixed-by-PD-M11 with a regression test and no new
behaviour. If it still refuses, the plan is wrong about the cause and I will
come back with a new one rather than guessing now.

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| PD-M14.1 | An Earlier drop onto a day with nothing scheduled creates the block | `tests/test_plan_screen.py::test_pdm141_an_earlier_drop_onto_an_empty_day_schedules` |
| PD-M14.2 | An Earlier drop works with a block sitting at the last box and nothing adjacent | `tests/test_plan_screen.py::test_pdm142_an_earlier_drop_ignores_what_is_at_the_other_end` |
| PD-M14.3 | A Later drop works with a block at box 0 and nothing adjacent | `tests/test_plan_screen.py::test_pdm143_a_later_drop_ignores_what_is_at_the_other_end` |
| PD-M14.4 | **Not code-testable:** that the gesture works with a real pointer on a real pane. Human review — checklist item 2, before any of this is written | checklist `docs/changes/2026-11-07-plan-day-faults-screen-checklist.md#2` |

---

## PD-M15 — the weekday list, warned once per day

Item 3. **This one has a question I will not answer for you**, because the two
readings lead to opposite code and your "No, once per day" rules out the
reading the relaying session proposed.

What is established: the gate is on all four write paths, every block write in
the app goes through one function, and no other screen calls it. The gate asks
once per date and caches the yes for the life of the screen. That is already
"warning happens once on the first block" **and** "once per day" — the
behaviour you described and the behaviour you asked for are the same behaviour.

So "you are simply ignoring the Work day settings" is either:

- **(i) the PD-M11 dialog fault, seen from the other side.** Before the fix, the
  question raised instead of returning an answer. If a later gesture then found
  the day cached, or took a path whose status line was overwritten, the day
  would accept work with no question visible — "ignoring the settings". This is
  fixed and unreleased. **Under this reading PD-M15 is a no-op plus a
  regression test.**
- **(ii) you want the unchecked day *refused*, not warned.** That contradicts
  the current spec, which says in as many words that the weekday list "is not a
  lock on the calendar", and it contradicts "once per day" — a refusal warns
  every time because nothing is ever permitted. **Under this reading PD-M15 is
  a spec change and the plan above is the wrong shape for it.**

I read your answer as (i) and the criteria below assume it. **If you meant that
an unchecked day should refuse the drop outright, say so and I will replan.**

On the parenthetical: breaks, buffers and lunch must not refuse a drop or
re-arm the warning. The warning is keyed on the date alone and reads nothing
about the day's contents, so it cannot re-arm. Placement is a separate matter —
`first_clear_slot` skips any box that is occupied *by anything*, which is how
AutoLoad avoids writing on top of your lunch, and I am treating that as correct
rather than as the thing you were describing. PD-M15.4 pins it so a later change
cannot quietly turn it into a refusal.

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| PD-M15.1 | Every path that writes a block on an unchecked day asks first — all four, named individually, so a fifth writer added later fails the test | `tests/test_plan_screen.py::test_pdm151_every_write_path_asks_on_an_unchecked_day` |
| PD-M15.2 | The question is asked once per date; a second write on the same date asks nothing | `tests/test_plan_screen.py::test_pdm152_the_day_off_question_is_asked_once_per_date` |
| PD-M15.3 | A day holding only breaks, buffers or lunch does not re-arm the question | `tests/test_plan_screen.py::test_pdm153_breaks_on_the_day_do_not_re_arm_the_question` |
| PD-M15.4 | A day holding a break still accepts an item in a different box | `tests/test_plan_screen.py::test_pdm154_a_break_on_the_day_does_not_refuse_an_item` |
| PD-M15.5 | Adversarial (P7): a date that is not a date does not read as a work day and does not silently write | `tests/test_plan_screen.py::test_pdm155_an_unparseable_date_is_not_a_work_day` |
| PD-M15.6 | **Not code-testable:** that a real Yes on a real dialog schedules. Human review — checklist item 3 | checklist `docs/changes/2026-11-07-plan-day-faults-screen-checklist.md#3` |

---

## Order and dependencies

1. **Checklist items 2 and 3 on the built branch, before any code.** They decide
   whether PD-M14 and PD-M15 are regression tests or real work, and they cost
   one pass through the app. Writing code first risks a batch aimed at a cause
   that the already-pushed PD-M11 fix removed.
2. **PD-M13.3–13.5 first, in `time_block_layout.py`.** The grid has to be able
   to draw a block outside the configured range *before* the drop stops moving
   the bound, or the drop lands somewhere nothing draws. This is the step where
   the work is, and it is the step to review hardest.
3. **PD-M13.1, 13.2, 13.6** — strip the `setattr`, the `save()` and the
   `shift_all_slots` call out of `extend_day_with_item`, and delete
   `shift_all_slots` and its test if nothing else calls it.
4. **PD-M13.7–13.10** — Clear Day, which by then needs no new code, only tests
   proving the range comes back. If a test fails here, step 2 is wrong.
5. **PD-M14, PD-M15** — whatever step 1 leaves of them.
6. Docs: `docs/USER_GUIDE.md` (the Earlier/Later entry currently implies the
   day's hours change), `NOTES.md`, `BACKLOG.md`, the `CHANGELOG` entry for
   Clear Day the relaying session flagged, and a handoff note.

## Criteria that cannot be made code-testable

Flagged per the planning rule, with a human-review proposal each:

- **PD-M14.4 / PD-M15.6** — both gestures need a real pointer on a mapped pane.
  Proposal: checklist items 2 and 3, which already exist and are written.
- **The migration question under PD-M13** — no test can distinguish a Day Start
  the user typed from one an extension wrote. Proposal: a line in the status
  report stating that days extended under the old behaviour keep the bound the
  extension wrote, and that this is not recoverable.

## Things I am not doing without being asked

- Changing whether Clear Day removes breaks and buffers. The relaying session
  raised that the CHANGELOG says they stay; nothing in items 1–4 asks to change
  it, so PD-M13.9 keeps them.
- Making the weekday list a refusal (PD-M15 reading (ii)).
- Touching `weekly_items.py:427`'s dialog or `tk_popup`, both in `BACKLOG.md`
  from the last batch.
