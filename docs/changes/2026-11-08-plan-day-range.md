# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: plan-day-range — the configured day and the day as drawn (PD-M13/14/15)

## Summary

Four items from `BACKLOG.md`, in the user's words:

1. "Clear day doesn't reset the time blocks to range in settings."
2. "User should be able to drag to the Early or Late Block regardless if
   anything is after the Morning block or before the Evening block."
3. "You are simply ignoring the Work day settings and letting me schedule on a
   NON checked Day. Warning happens once on the first block. (if a non break
   /buffer/ lunch block - a non -action item block - is on the Day, allow
   more)."
4. "ADD - when add to start and End of day do NOT change the length of Day in
   Settings."

Item 4 is the mechanism behind item 1, and is the whole of the code change.
`extend_day_for` had moved `plan_day_start`/`plan_day_end`, saved the settings
file, and called `shift_all_slots` to renumber **every date's** blocks so their
clock times survived the bound moving. All three are gone. A block's
`slot_index` may now be **negative**, and `drawn_day_slots(bounds, blocks)`
lays the day out from the configured range widened to cover whatever sits
outside it. So the *configured* day (Settings) and the *drawn* day (what is on
screen) are two different things, and item 1 follows without any reset code:
the extra half hours are derived from the blocks in them, so Clear Day removing
the blocks narrows the day by itself.

Items 2 and 3 needed **no code**, as the plan predicted and said it would
establish before writing any. There is no adjacency guard on the Earlier/Later
path to remove, and the weekday gate already asks once per date on all four
write paths. Both are now covered by regression tests that fail if either
property is lost. PD-M15 reading (ii) — refusing an unchecked day rather than
warning — was declined by the user ("No, once per day") and is not implemented.

Deleted with their tests: `db_manager.shift_all_slots` (the renumber) and
`time_block_layout.extended_day_bound` with `LAST_DAY_END_MINUTES` (the new
bound, and the 23:30 ceiling that only a moving bound needed). The midnight
guarantee moved off the bound and onto the box: `slot_is_on_the_date`.

Three defects found while building it, all in code this change touches, all
fixed here:

- **`times_for_slot` clamped the index at zero.** Found by PD-M13.6's test. A
  block at box -1 was stored as 08:00 while the grid drew it at 07:30 — the row
  and the screen disagreeing with nothing marked wrong, which is the exact
  failure the deleted renumber existed to prevent.
- **`can_place`, loosened for every caller, regressed two paths.** My first cut
  removed the configured-range refusal outright. AutoLoad then filled a 17:00
  box that Day End excluded, and adoption of a pre-grid 19:00 row invented a
  box past Day End instead of leaving it for the outside group. Both were
  caught by the existing suite. The limit for every ordinary write is now the
  day *as drawn*; `allow_outside_range` is passed by the extension gesture
  alone, and the two free-slot scans walk the configured range rather than
  `self._grid.slots`.
- **`on_settings_saved` blamed itself for pre-grid rows.** It said "N blocks no
  longer fit the day" whenever the outside group was non-empty after a save. A
  save can no longer orphan anything, so on any day holding an unadoptable row
  the user was told their save had displaced a block it had nothing to do with.
  It reports only the increase now, keeping the warning for the case it was
  written for.

## Files changed

Source (commit `6c7b0ef`):

- `src/getmoredone/time_block_layout.py` — `drawn_day_slots`,
  `slot_is_on_the_date`, `_overlaps_lunch`; `can_place` gains
  `allow_outside_range`; `build_day_grid` keys off a `position` dict because
  `Slot.index` is no longer the list position; `slot_occupancy`'s clamp
  removed; `times_for_slot`'s clamp removed; `extended_day_bound` and
  `LAST_DAY_END_MINUTES` deleted
- `src/getmoredone/db_manager.py` — `add_block_at` and
  `_refuse_unless_it_fits` thread `allow_outside_range`; `shift_all_slots`
  deleted
- `src/getmoredone/screens/plan.py` — `extend_day_for` rewritten (no
  `setattr`, no `save()`, no renumber, no rollback arm); `on_settings_saved`
  reports the increase; `_first_free_slot_for` and `first_free_slot` walk the
  configured range; `_DayNotWritten` deleted

Tests (commit `2e1a87b`), committed separately so the ratio stays visible in
`git log --stat`:

- `tests/test_plan_screen.py` — 17 new, 9 retargeted, `_unplaced` helper
  added, `_add_block` gains `outside_range` and `bounds`
- `tests/test_time_grid.py` — 5 new, 2 retargeted
- `tests/test_time_block_layout.py` — 4 deleted with `extended_day_bound`
- `tests/test_time_block_crud.py` — 4 deleted with `shift_all_slots`

Docs:

- `docs/USER_GUIDE.md` — the Earlier/Later entry rewritten (it said the day's
  hours change); three "Outside the day" passages corrected, including the one
  saying a narrower day puts blocks in that group
- `CHANGELOG.md`, `NOTES.md`, `docs/spec_coverage.md` (five PD-M5 rows marked
  superseded, with what replaces each; a new PD-M13/14/15 section),
  `docs/changes/2026-11-08-plan-day-range-checklist.md`, `BACKLOG.md`

## Verification

- Command: the eight files this batch touches or whose subject it changes —
  `test_plan_screen.py`, `test_time_grid.py`, `test_time_block_layout.py`,
  `test_time_block_crud.py`, `test_plan_settings.py`,
  `test_time_block_schema.py`, `test_traceability_refs.py`,
  `test_ci_contract.py`. The file set was chosen by grepping `tests/` for the
  changed names rather than by which files the diff edited, which is how the
  two red tests in `test_plan_settings.py` were found.
- Result: **PASS** — see the line below for the count.
- Command: 16 single-mutation runs before the cold passes, 6 after them, and
  6 again after the fourth pass with the two grid mutants repointed — one now
  deletes the per-block filter, the other *downgrades* it back to the two
  blanket clamps, so the suite has to distinguish "on the date" from "no box
  that holds nothing". Each run applies one mutation to one named production
  line, runs the test that names it, then restores the file and verifies it
  byte-identical by sha256.
- Result: **PASS** — 28 of 28 mutants killed, 0 survived.
- **Not run:** the full suite. Throttled on this machine by the user's
  standing instruction; CI runs it.
- **Not run:** the app itself. The user's standing instruction is that I do not
  drive their computer, so the on-screen verification is a checklist for them:
  `docs/changes/2026-11-08-plan-day-range-checklist.md`, four items.

## The three cold passes, and what they changed

Three cold passes ran over `2b2393f...HEAD` with no implementation context —
failure patterns (`learning-qa`), correctness, and security. Severity was set on
every finding before any fix was written. One high and two mediums were fixed in
this batch; six below-medium findings and one adjacent issue went to
`BACKLOG.md`.

**Fixed — high. Six test references no longer resolved, and
`tests/test_traceability_refs.py::test_every_referenced_test_name_exists` was
red.** Five of the named tests were deleted or renamed by the test commit and no
document was updated with them. This was a mechanical CI break that every
earlier pass in this batch missed, warm and cold alike, because none of them ran
that file. Two source docstrings now point at the surviving tests; three
`spec_coverage.md` rows name their deleted tests in plain backticks instead of
as followable paths.

**Fixed — medium, found independently by all three passes. The grid drew boxes
no write would accept.** `slot_is_on_the_date` guards the write with the Day
Start in force at that moment; nothing re-checked on read, and PD-M13
deliberately never rewrites a stored index when Day Start changes. Reduce Day
Start in ⚙ Day Settings under a block placed before the old start and the box
lands before midnight: `format_hhmm` floors it to "00:00", and `can_place`
refuses the very box the block is drawn in, so the block shows the wrong time
and cannot be moved, resized or dragged out. Deleting it was the only way out.
`drawn_day_slots` now clamps its widening to the boxes that lie on the date, so
the block misses the grid and `build_day_grid` routes it to `outside` — on
screen, with its own stored time, and draggable back. The same clamp re-bounds
the grid's extent, which had become a function of stored data.

**Fixed — medium, from the correctness pass. AutoLoad could finish a block
past the configured Day End.** Both free-box scans were moved onto
`day_grid(self.bounds)` during implementation, which bounds where a span may
*start*; its length was still checked by `can_place`, whose limit is the day as
*drawn*. With a Later-extended day and Day End then reduced, a 60-minute item
offered the last configured box ran half an hour past it. Both scans now bound
the span by the configured day as well.

**Fixed — low, named by two passes. `extend_day_for`'s broad failure arm
stopped redrawing**, incidentally, when the settings rollback it belonged to was
deleted. Nothing is wrong on screen today because every refusal this path
reaches is checked before the write; a failure landing after the commit would
leave the drawn day disagreeing with the database. Restored, with a test.

**Two retargeted tests in `tests/test_plan_settings.py`, reason (b).**
`test_pdm54_extending_the_day_is_not_confirming_it` and
`test_pdm54_an_already_confirmed_day_stays_confirmed` asserted
`plan_day_start == "07:30"` and `plan_day_end == "17:30"` after an extension —
the settings write PD-M13 removed. A third assertion read the flag back out of
the settings file, which only worked because the extension called
`settings.save()` and so rewrote an unreadable file as a side effect. All three
now assert the stronger fact: the extension happened (read off the block), the
configured values are untouched, and the file was not written at all. **This
file was never run during implementation** — the batch was verified against the
files it touched, and this one only references the behaviour. Both tests were
red on disk while every other check in the batch was green.

**Also corrected, as claims rather than cosmetics:** `can_place`'s docstring
said adoption "leaves the row unplaced instead of inventing a box past Day End",
which is not what the code does — a pre-grid row with a readable `start_time`
gets exactly one candidate, the box that time names, so it may land past Day End
when the day is drawn out that far. That keeps the user's own clock time, so the
behaviour is right and the docstring was wrong. `build_day_grid`'s docstring
named "Day End moved earlier" as a way into `outside`, which this change
inverted. The status line "drag an item here to lengthen the day" and
`USER_GUIDE.md`'s "Lengthening the day does not count as confirming the day's
hours" both describe a gesture that no longer lengthens anything. `CLAUDE.md`'s
test count said 1691, where collection reports **2000** behaviour tests and 213
meta ones — drift that predates this batch. The figure was first corrected to
1997/212, which did not match a re-collection at the final commit: 2000 and 213.
The only count change this batch's last round made is one new parametrize id, so
1997 was a mis-measurement rather than a change. Both numbers are prose; no test
parses them, which is how they drifted by three hundred in the first place.

**Withdrawn.** A `BACKLOG.md` entry about `shift_all_slots` accepting a negative
`by` outlived the function; and the "adjacent issue" this note first recorded
(that Day Settings accepts a Day End which does not divide into half hours) is
not a gap: `day_grid`'s loop is `while at + SLOT_MINUTES <= end` and its
docstring states that a partial last box is deliberately not produced.

## The fourth cold pass (test quality), and what it changed

A fourth cold pass ran over the fix commits with test quality as its only lens
— a different failure family, as the budget requires of a further pass. It
reported one medium and six low findings, plus one item it correctly refused to
rule on as outside its lens.

**Fixed — production, from the item the pass handed on.** It observed that the
new grid test drew a box one past the configured Day End for a block the clamps
had removed, and said that whether that empty box is intended is a
production-correctness question another pass owns. It is not intended, and it
was reproduced directly: Day Start 20:00, Day End 23:30, a block at stored
index 40 — the clamps held the extent on the date but still widened the day to
box 7, which holds nothing, because the widening was computed from the
unclamped block and only the *result* was clamped. The two blanket clamps are
replaced by a per-block filter: a block the date cannot hold is skipped before
it widens anything, so it widens nothing, `build_day_grid` routes it to
`outside` exactly as before, and the drawn day equals the configured day box
for box. The grid test now asserts that equality, which is strictly stronger
than the "every drawn box is on the date" property it asserted before.

**Fixed — medium. `assert len(grid.slots) <= 48` was a ceiling where an exact
value exists.** The repo rule is to assert exact counts and never a `> N`
floor; this was the same defect with the inequality flipped, and it would have
passed for any wrong-but-small extent. With the filter in place the right
answer is the configured day itself, so the test now compares the grid's boxes
to `day_grid(BOUNDS)` index for index.

**Fixed — three findings that were about a test not testing its own claim**,
which the repo's test rules treat as more than cosmetic:
`test_pdm13_a_failed_extension_redraws_before_it_reports` recorded only *that*
the redraw happened, never that it came first, so the order in its name was
unasserted — it now traces both calls into one list and asserts the index.
`test_pdm13_the_free_box_scan_bounds_the_span_too` passed `outside_range=True`
on a write the helper checked against its own 08:00–17:00 default, where the
box was well inside the day and the flag did nothing — it now passes the short
day the screen is actually on. And the reworded PD-M5.7 refusal had no
coverage for its second clause, which this batch changed; that assertion is
part of this batch's own change, so it was completed rather than deferred.

**Two low findings came along inside a rewrite that was required anyway.** The
grid test had to be rewritten for the production change above, so while it was
being rewritten the assertion that was strictly implied by the one three lines
above it was dropped (replaced by a check on the clock labels, which pins the
symptom the user saw and exercises `format_hhmm` rather than the widening), and
the two cases were parametrized so that each end of the range is reported
independently instead of the first failure hiding the second.

**Recorded, not fixed.** One finding was a judgement call about comparing
`drawn_day_slots` output against `day_grid` output rather than against a
literal: see `BACKLOG.md`. It is accepted as-is, because `day_grid` is pinned
independently by `test_tgm11_grid_covers_the_day_in_half_hours`, and a literal
box list would have to be rewritten by hand every time the fixture day changes.

## Risks / Known gaps

- **Days already extended keep the hours that extension wrote, and this is not
  recoverable.** Nothing distinguishes a `plan_day_start` of 07:30 the user
  typed from one an extension wrote, so no migration is attempted and none is
  possible. Such a day draws coherently —
  `test_pdm1310_a_day_extended_under_the_old_behaviour_still_draws` is the
  dirty-state test (P8) that pins it — but its configured hours are wider than
  the user set them. The CHANGELOG and the user guide both tell them to check
  ⚙ Day Settings once; checklist item 3 is where they would notice.
- **PD-M14.4 and PD-M15.6 are outstanding**, by design: the plan marked both
  not code-testable. Checklist items 1 and 2.
- **The drawn day is new on screen and no test can say whether it reads as a
  day.** A column running 06:30–19:30 on a day the user configured as
  08:00–17:00 is correct by every assertion here. Checklist items 3 and 4.
- The "no longer fit the day" warning on a settings save is now, as far as I
  can see, unreachable: nothing left can orphan a block. It is kept rather than
  deleted because it is the P2 guarantee, and
  `test_pdm13_a_settings_save_does_not_blame_itself_for_an_old_unplaced_row`
  asserts the wording rather than the absence of a warning, so the arm stays
  honest if something ever can orphan one again.
- **Checked and not a gap:** deleting `LAST_DAY_END_MINUTES` removed the only
  place in the source that stated "the latest Day End that still yields whole
  boxes". Day Settings does not check that the range divides into half hours —
  it validates parsing, Day End after Day Start, the lunch minutes and at least
  one weekday (`plan_settings_dialog.py:137-171`) — so a Day End of 23:45 is
  accepted. That is handled deliberately one layer down: `day_grid`'s loop is
  `while at + SLOT_MINUTES <= end` and its docstring says a partial last box is
  "not produced at all... rather than a 15-minute stub that nothing can hold".
  So there is nothing to fix and no BACKLOG item; the constant had no caller
  once the bound stopped moving, and the limit that replaced it
  (`slot_is_on_the_date`) is checked in minutes against the date.
- Three criteria in `docs/spec_coverage.md` (PD-M13.12, 13.13, 13.14) were
  **added during implementation** and were not in the approved plan. Each is
  for a defect the work turned up, and each is marked as such in that table.

## Next agent actions

- Nothing is blocked on code. The next move is the user's: the four checklist
  items, which are the only outstanding acceptance criteria.
- If checklist item 1 shows the Earlier/Later drop still refusing, the plan
  says to come back with a new plan rather than guessing: PD-M14's premise
  (that the cause was the PD-M11 dialog fault, now fixed) would be wrong.
