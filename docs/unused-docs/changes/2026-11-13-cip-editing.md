# Handoff Note

- Date: 2026-11-13
- Topic: CIP batch 2 — changing a Google Calendar meeting from the Plan, and the walk it owes

## Summary
CIP-M4 (with M1.6 and M0.3b) of `docs/spec_2026-11-08_calendar_into_the_plan.md`
is built, from `docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_editing.md`.
Criteria and tests: `docs/spec_coverage.md`, *Google Calendar into the Plan,
editing*. **No write has reached live Google**, and nothing was seen on screen.

Where the build departs from the plan:
- **E10:** the write logic is a new module, `calendar_commitment_edits.py`,
  not more of `calendar_commitments.py` (already 508 lines).
- **E8:** the shared claim kept its batch-1 name, `_REFRESHES_IN_FLIGHT`. A
  rename would change batch-1 tests for no change in behaviour.
- **E1:** the guest question is asked during the gesture, from a new cached
  column `calendar_commitments.guest_count`, rather than after a read of the
  event. A modal opened from a timer callback is what PD-M13 found raising
  on macOS. The stale-write check (E6) compares the guest count too, so a
  guest added since the read refuses the write rather than emailing someone
  the user was not asked about.

## Verification
- Command: the touched test files, with `GETMOREDONE_NO_MAPPED_WINDOWS=1`. The full suite runs on CI.
- Mutation: every new test was turned red by a mutation of the verbatim line it
  names (41 mutations). Eight first-run survivors led to tightened tests and to
  two lines removed as unreachable (an `is_all_day` test the range check already
  covers, and an `AuthenticationRequired` branch whose result nothing read).
- Live Google: NOT RUN. On screen: NOT RUN.

## Walk checklist (on a test meeting; quit the packaged app, run from source)
1. Drag a meeting you organised, with no guests, to another box. Check Google
   Calendar: new time, same length, description and video link unchanged.
2. Do the same with a meeting that has one guest; answer *No* to the email
   question and check the guest got no mail. Repeat with *Yes*.
3. Move one occurrence of a weekly meeting; the other weeks are unchanged.
4. Try to drag a meeting someone else organised: nothing moves, and its
   right-click menu offers only *Ignore on this day*.
5. Change a meeting's title in Google Calendar, then move it from the Plan
   without pressing ↻ Calendar: refused with "changed in Google Calendar".
6. Delete a test meeting from the Plan: asked first, then gone from Google.

## Risks / Known gaps
- `guestsCanModify` lets a guest move a meeting for everyone. Google allows
  it; the guest question names the count of people affected.
- A meeting starting at 00:00 on its date is treated as part of an
  over-midnight meeting and cannot be moved (rename and delete still work).

## Next agent actions
- Run the walk above and record what was seen.
- Batch 3: the week view (CIP-M6).
