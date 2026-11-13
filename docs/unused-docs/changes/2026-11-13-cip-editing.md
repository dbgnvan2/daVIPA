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

Sweep (2026-11-13): cold `learning-qa`, cold correctness and `/security-review`
passes over `3af9d33...a124f57`. Security: nothing at confidence 8+. Fixed,
each with a mutation-checked guard:
- **F1 (high):** a plain click on a meeting off the half hour (10:15) moved it
  to the box start in Google with no question. `drop_commitment` now compares
  boxes, not minutes.
- **F2 (high):** delete or rename of one date of a multi-date event changed
  the whole event after a question naming one date, and left the other dates'
  cache rows stale. `verify_unchanged` now refuses any write to an event over
  more than one date. This narrows E2: an over-midnight meeting is no longer
  renamed or deleted from the Plan.
- **F3:** a database that would not open after Google took the change said
  "Not changed". The `DatabaseManager` is now built inside the guarded block.
- **F4:** a failed write is logged as well as shown, so leaving the screen
  mid-write does not lose it.
- **F5:** with tzlocal failing, `update_event` names UTC; the edit path now
  sends an aware start in the zone the reader used.

Cold re-sweep of the fixes (`a124f57...240de8e`, `learning-qa`): two medium,
both fixed with mutation-checked guards. The worker read `_edit_result` back
after handing it over, racing the poll that clears it; it now logs from a
local and hands over last. The menu still offered Rename and Delete on an
event cached on a neighbouring date; it now shows only "Over more than one
day — change it in Google Calendar". No high finding, so no further pass.

Adjacent issues found, not fixed (outside this batch):
- `calendar_exporter.py` and `screens/calendar_dialog.py` pass naive times to
  `create_event`/`update_event`, so they share the UTC fallback F5 closed here.
- If `update_event`'s PUT reaches Google and every retry then fails on
  transport, the edit reports "Not changed" though Google may hold it.

Test hang (pre-existing, batch 1): `test_cipm51` called a full `update()` on a
withdrawn root; on macOS that spins forever in Tk's run loop
(`TkMacOSXDrawAllViews`) when it is not the first Tk test in the process. Now
`update_idletasks()`. Found with pytest-timeout and `sample`.

Dropped as low, with reasons:
- No `If-Match` etag on update/delete: the gap is the seconds between GET and
  PUT, and the app is the only writer the user drives at that moment.
- Rows cached before the `guest_count` column hold 0, so the first edit of a
  meeting with guests is refused as "changed"; nothing is written, one
  Refresh clears it.
- Choosing the current length or title still writes (and may ask about
  email); harmless, the user chose it.
- A meeting moved to end at 24:00 or start at 00:00 cannot be moved again
  (`movable` is stricter than `move_refusal`); rename and delete still work.

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
