# Implementation plan — the day's hours are a template (PD-M14)

Date: 2026-11-08
Status: **planned, not built — awaiting approval**
Screen: `src/getmoredone/screens/plan.py`, `src/getmoredone/time_block_layout.py`,
`src/getmoredone/db_manager.py`
Follows: `docs/implementation_plan_2026-11-06_plan_day_controls.md` (PD-M1 … PD-M13, shipped)

Three reports from the running screen, 2026-11-08:

1. "There is a status message at the bottom" — PD-M13 confirmed.
2. "The extend day function is inconsistent."
3. "Clearing the day does NOT restore the hours of the day."

And one instruction that changes the design rather than fixing a defect in it:

> **do NOT update the hours of the day — those are solely for starting a blank
> plan for the day.**

## What the data says

Reports 2 and 3 are one mechanism, and it is measurable in the demo instance
(`~/Library/Application Support/GetMoreDone-Demo`).

`extend_day_for` writes `plan_day_start` or `plan_day_end` — **one setting,
shared by every date** — and then calls `shift_all_slots`, which renumbers every
block on every date so their clock times survive the move. Nothing ever writes
those hours back. So each drop on **Earlier** ratchets the whole app's day start
backwards and nothing returns it, Clear Day included: it deletes blocks, and the
hours were never a property of the day's blocks.

The demo settings now read `plan_day_start = "09:00"`. The blocks say the day
start had reached **05:30** — seven boxes earlier — before it was set back to
09:00 by hand in ⚙ Day Settings. Changing the hours there does not renumber
(TG-M6.4, deliberate), so:

| Date | slot | planned at | drawn at |
|---|---|---|---|
| 2026-11-05 | 6, 7, 8, 8 | 08:30, 09:00, 09:30, 09:30 | 12:00, 12:30, 13:00, 13:00 |
| 2026-11-06 | 5 … 15 | 08:00 … 13:00 | 11:30 … 16:30 |
| 2026-11-07 | 5 | 08:30 | 11:30 |

Thirteen blocks on three dates, every one drawn exactly 3½ hours after the time
it was planned at. That is report 2: not a function that sometimes fails, a
function whose side effect is global and permanent, and whose repair by hand
leaves every day it touched wrong.

The root cause is one sentence: **a block's position is stored as a count of
boxes from a Day Start it does not own.** The fix is to stop treating the hours
as the day's state and start treating them as what the user says they are — the
template a blank day starts from.

## What changes

A block keeps a `slot_index` measured from the **template's** Day Start, and
that index is allowed to be **negative**. A negative index means "before the
hours you set"; an index past the last template box means "after them". Nothing
about the hours is stored per date, so nothing about them can go stale: the day
drawn for a date is the template, stretched to cover whatever that date actually
holds. Take the blocks away and it is the template again.

`shift_all_slots` does not disappear — it **moves**. Renumbering is exactly
right when the template itself changes, and exactly wrong as the side effect of
one drop.

---

### PD-M14.1 — A drop never writes the day's hours

`extend_day_for` stops setting `plan_day_start` / `plan_day_end`, stops calling
`settings.save()`, and stops calling `shift_all_slots`. It writes one block, at
a slot index outside the template's range, in one transaction. The whole
settings-rollback arm goes with it: there is nothing left to roll back but the
block, which the transaction already covers.

- **Automated:** `::test_pdm141_a_drop_on_earlier_writes_no_settings` — drop on
  **Earlier**, assert `settings.plan_day_start` is unchanged, `settings.save`
  was never called (a counting stub), and one block exists at a negative slot.
  Same for **Later** with `plan_day_end`.
- **Automated:** `::test_pdm141_a_drop_leaves_every_other_date_alone` — blocks
  on two other dates, snapshot their rows, drop on **Earlier**, assert both rows
  are byte-identical. This is the test the current design cannot pass.
- **On screen:** drop an item on **Earlier**. Open ⚙ Day Settings and check Day
  Start still reads what you set. Change to another date and check nothing moved.

### PD-M14.2 — A block may sit outside the hours you set

`slot_index` becomes signed. The day drawn for a date spans from the lowest
index on that date (or 0, whichever is lower) to the highest (or the last
template box, whichever is higher). Four guards in `time_block_layout.py`
assume the grid starts at index 0 — lines 613, 667, 726 and 809 — and each
widens to the drawn span's own first index. `times_for_slot` already computes
`day_start + index * 30`, which is correct for a negative index with no change.

- **Automated:** `::test_pdm142_a_negative_slot_keeps_its_clock_time` — a block
  at slot −2 with a template start of 09:00 reads 08:00, round-tripped through
  the database.
- **Automated:** `::test_pdm142_the_drawn_day_covers_what_is_planned_on_it` —
  blocks at −2 and at the last box + 1; assert the grid's first and last slot,
  and that the lunch boxes are still marked at their clock times.
- **Automated (adversarial, P7):** `::test_pdm142_a_block_outside_the_day_is_not_silently_dropped`
  — the "outside the day" group stays for blocks with **no** slot index, and a
  negative index is *not* outside the day. One looks like the other and must not
  be treated as one.
- **On screen:** drop an item on **Earlier**, then on **Later**. Both land where
  you dropped them, and the times on the new boxes continue the day's own clock.

### PD-M14.3 — Clearing the day restores the hours

No new code, which is the point: the hours are derived from the blocks, so
deleting the blocks restores them. Clear Day removes item blocks only, so a
break or buffer you placed outside the hours keeps the day stretched that far —
and Clear Day's status line says so, because a day that did not fully collapse
needs to account for why.

- **Automated:** `::test_pdm143_clearing_the_day_restores_the_hours` — extend
  earlier twice, clear the day, assert the drawn grid's first slot is 0 again
  and `settings.plan_day_start` never changed throughout.
- **Automated:** `::test_pdm143_a_break_outside_the_hours_keeps_the_day_open` —
  a buffer at slot −1 survives Clear Day, the day still starts at −1, and the
  status line names the kept block.
- **Automated (dirty state, P8):** `::test_pdm143_a_day_reopened_is_the_day_that_was_left`
  — write, close the screen, build a second screen on the same database, assert
  the same drawn span. The hours must not depend on who drew them last.
- **On screen:** extend the day earlier, press **Clear Day**, confirm. The day
  goes back to your hours. Any break or buffer you put outside them stays, and
  the message says it did.

### PD-M14.4 — Changing the hours keeps planned work on its clock

> **Not built.** `docs/changes/2026-11-08-day-hours-are-a-template-wip.md`
> records PD-M14.4 under "Not started", and nothing since has built it:
> `grep -rn "def test_pdm144" tests/` returns nothing, and
> `grep -rn shift_all_slots src/` finds only the definition at
> `db_manager.py:1658` and a docstring mention — no production caller. So the
> reversal this section proposes did not happen: `on_settings_saved` still
> writes no rows, TG-M6.4 and TG-M6.4a stay `done` in `docs/spec_coverage.md`,
> and both their tests are live. Read the rest of this section as the proposal
> it is, not as built behaviour — including the two `test_pdm144` names below,
> which were never written. *(Recorded 2026-11-08, tenth cold pass of the PDT
> batch, which found this section cited as though it had shipped.)*

This is the reversal that makes PD-M14.1 safe, and it follows from the
instruction: if the hours are only a template, moving the template cannot move
work that is already planned. So `on_settings_saved` renumbers — this is
`shift_all_slots`, with its existing tests, called from the gesture it belongs
to — and every block keeps the clock time it was planned at. Today it does the
opposite: it keeps the box and re-times the block, which is what put thirteen
blocks 3½ hours out.

**This withdraws TG-M6.4, an approved criterion**, and it is the one item here
that changes behaviour you did not report. It is in the plan because without it
the thirteen blocks happen again the next time the hours change.

- **Automated:** `::test_pdm144_changing_the_hours_keeps_clock_times` — blocks
  on three dates, move Day Start from 09:00 to 08:00, assert every block's drawn
  time is the time it had before and its slot index moved by +2.
- **Automated:** `::test_pdm144_a_renumber_that_fails_leaves_the_hours_alone` —
  one transaction: the settings write and the renumber land together or not at
  all, and the status line says which.
- **On screen:** plan three items on a day. Change Day Start by an hour and
  save. All three are still at the times you planned them.

### PD-M14.5 — AutoLoad and the break button never widen the day

`first_free_slot` searches the template's boxes only, so filling a day cannot
invent hours. Only a drag onto **Earlier** or **Later** goes outside them, which
is the one gesture that says so explicitly.

- **Automated:** `::test_pdm145_autoload_stops_at_the_hours_you_set` — more
  items than the day has boxes; assert the overflow is reported as "did not fit"
  and no block has a slot index outside the template.
- **Automated:** `::test_pdm145_a_break_is_refused_rather_than_placed_outside` —
  a full day, press break, assert the refusal and no new block.
- **On screen:** fill a day with AutoLoad. The day stays the length you set it.

### PD-M14.6 — Both ends refuse the same way

Earlier's floor is 00:00 and Later's ceiling is 23:30 — the last box that is a
whole half hour. The limits are genuinely different; the message should not be.
One sentence, naming the end and the limit, for both.

- **Automated:** `::test_pdm146_both_ends_refuse_at_midnight_and_say_which` —
  parametrised over the two ends; assert nothing is written and the message
  names the end.
- **On screen:** set Day Start to 00:30, drop an item on **Earlier**. It is
  refused and says why, rather than doing nothing.

### PD-M14.7 — Put the thirteen blocks back on their own times (one-time repair)

Your demo instance has thirteen blocks whose recorded time and drawn box
disagree. Their recorded time is the time you planned them at, so that is the
one to keep: each block's `slot_index` is recomputed from its stored
`start_time` against the current template, negative where the time is before
Day Start.

This is the only irreversible step in the plan. It runs once per date, when the
day's shape is confirmed (the same gate adoption uses), reports how many blocks
it moved and from where, and does nothing at all if the two agree.

- **Automated:** `::test_pdm147_a_block_is_put_back_on_the_time_it_was_planned_at`
  — a block at slot 6 recorded 08:30 with a 09:00 template becomes slot −1, and
  its recorded time does not change.
- **Automated:** `::test_pdm147_a_day_that_agrees_is_not_touched` — snapshot
  every row, load twice, assert no write (idempotent, and no second pass).
- **Automated:** `::test_pdm147_an_unconfirmed_day_shape_repairs_nothing` — the
  guard, for the same reason adoption has one: a template we are guessing at
  would move work to an hour nobody chose.
- **On screen:** open 5, 6 and 7 November. Everything is at the time you planned
  it, and the status line says how many blocks were put back.

### PD-M14.8 — The walk

Not code-testable: nothing in this suite can build a visible window, which is
how PD-M12 and PD-M13's first remedy both reached you. The on-screen checks
above, in one pass, on a weekday and on a Saturday.

---

## Withdrawn criteria

| ID | Criterion | Why |
|---|---|---|
| PD-M5.2 | A drop above the first box moves Day Start back | The drop no longer touches Day Start. The item still lands above the first box. |
| PD-M5.3 | A drop below the last box moves Day End forward | The same, at the other end. |
| PD-M5.5 | Blocks keep their clock times when the day grows | **Not withdrawn** — it is in this table only because the plan expected PD-M14.4 to change how it is kept; `docs/spec_coverage.md` records it `done` and that is correct. Still true, by a different mechanism: nothing is renumbered because nothing moves. The plan expected `shift_all_slots` to keep this criterion under PD-M14.4; since PD-M14.4 was not built, `shift_all_slots` has no production caller and the criterion holds without it. |
| TG-M6.4 | Saving Day Settings writes no blocks | ~~Reversed by PD-M14.4: it must renumber, or work already planned moves on the clock.~~ **Not what was built.** The box is stored relative to Day Start, so the clock times follow on read and nothing is renumbered — the same mechanism the PD-M5.5 row above describes. TG-M6.4 and TG-M6.4a stay `done` in `docs/spec_coverage.md`, and both named tests are live and green: `tests/test_plan_screen.py::test_tgm64_saving_settings_writes_no_blocks` and `tests/test_time_block_crud.py::test_tgm64_a_day_start_change_writes_no_rows`. Neither was deleted: PD-M14.4 was not built, and the deletion list below is corrected to the three tests that were. *(Corrected 2026-11-08, ninth cold pass of the PDT batch.)* |

**Three** tests assert the withdrawn behaviour and were deleted with it:
`::test_pdm52_a_drop_above_moves_day_start_back`,
`::test_pdm52_a_long_item_dropped_above_takes_the_day_back_far_enough` and
`::test_pdm53_a_drop_below_moves_day_end_forward`. All three are replaced by
the PD-M14 tests above.

~~`::test_tgm64_saving_settings_writes_no_blocks`~~ was listed here as a
fourth, to be replaced by `::test_pdm144_changing_the_hours_keeps_clock_times`.
Neither happened: PD-M14.4 was not built (see the note at its head), the
`test_pdm144` tests were never written, and
`tests/test_plan_screen.py::test_tgm64_saving_settings_writes_no_blocks` is
live in `tests/test_plan_screen.py` asserting the criterion verbatim — find
it with `grep -n "def test_tgm64_saving_settings_writes_no_blocks"`. Do not
delete it.

`::test_pdm53_a_drop_below_does_not_renumber_the_day` keeps its name and is
strengthened: under PD-M14.1 it holds for both ends, not one. It is live in
`tests/test_plan_screen.py` (`grep -n "def test_pdm53_a_drop_below_does_not_renumber" tests/test_plan_screen.py`).

~~`::test_pdm55_a_block_on_another_date_keeps_its_clock_time`~~ was named here
as a second. **It is not on `main`.** It was there — `git log -S` on the name
finds it added and later removed (`5543476`, `436264f`) — and it is still live
on `refs/heads/claude/elegant-neumann-ab55c9` and two other refs, so a reader
who greps the whole working tree will find the `def` in a worktree copy and
conclude the reference is good. On `main` it is not: `grep -rn "def
test_pdm55_a_block_on_another_date" tests/` returns nothing, and PD-M5.5's four
live tests are in `tests/test_time_block_crud.py` under other names. Repoint it
to one of those or drop it; do not restore the name.
*(Recorded 2026-11-08; the eleventh pass wrote "never existed" here, which the
twelfth corrected — the first version's own grep, run over the whole tree,
returns the branch copies.)*

## Implementation order

> **Only items 1, 2 and PD-M14.6 were built.**
> `docs/changes/2026-11-08-day-hours-are-a-template-wip.md` records PD-M14.3,
> PD-M14.4, PD-M14.5, PD-M14.7 and PD-M14.8 under "Not started", and nothing
> since has built them: `grep -rn "def test_pdm143\|def test_pdm145\|def
> test_pdm147" tests/` returns nothing, `clear_day` in
> `src/getmoredone/screens/plan.py` is still PD-M8's, and `first_free_slot`
> still walks the drawn grid rather than `template_span`, which has no caller
> in `plan.py`. *(Recorded 2026-11-08, eleventh cold pass of the PDT batch.)*

1. PD-M14.2 — signed slot index and the drawn span. Nothing else can land first. **Built.**
2. PD-M14.1 — the drop path, which is what was reported. **Built.**
3. PD-M14.3 — Clear Day, which is free once 14.2 is in, plus its tests. **Not built.**
4. PD-M14.4 — the settings path and TG-M6.4's reversal. **Not built.**
5. PD-M14.5, PD-M14.6 — the two containment rules. **PD-M14.6 built; PD-M14.5 not.**
6. PD-M14.7 — the repair, last, so it runs against finished code. **Not built.**

## Documents to update in the same change

`docs/spec_coverage.md` (PD-M14 rows; PD-M5.2 and PD-M5.3 withdrawn — **not**
TG-M6.4, whose reversal was never built: see the table above),
`docs/implementation_plan_2026-11-06_plan_day_controls.md` (PD-M5 marked
superseded in place), `docs/implementation_plan_2026-11-05_time_grid.md`
(TG-M6.4), `docs/USER_GUIDE.md` (what Day Settings is for, and what the two ends
do), `CHANGELOG.md`, `BACKLOG.md`, a handoff note.

## Risks

- **The signed index is the whole change.** Four guards and every caller of
  `build_day_grid`, `pack_day`, `repack_all_days` and `first_free_slot` have to
  be read, not assumed. If any one of them clamps a negative index to 0, a
  block dropped above the day lands on the first box instead and looks like it
  worked.
- **PD-M14.4 is a reversal of approved behaviour** and it is not something you
  reported. It can be dropped from this batch; the cost of dropping it is that
  changing the hours keeps moving planned work.
- **PD-M14.7 writes to your data.** It can be dropped too, and the thirteen
  blocks fixed by dragging them.
- Nothing here is verified on screen until PD-M14.8, and two remedies for the
  last report were wrong on screen.
