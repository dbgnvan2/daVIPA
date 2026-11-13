# Handoff Note

- Date: 2026-11-13
- Topic: CIP batch 1 — Google Calendar meetings read into the Plan, and the walk it owes

## Summary
The read half of `docs/spec_2026-11-08_calendar_into_the_plan.md` is built, from
`docs/unused-docs/implementation_plan_2026-11-13_calendar_into_the_plan_read_half.md`.
Criteria and tests: `docs/spec_coverage.md`, *Google Calendar into the Plan,
read half*. Nothing was seen on screen, and nothing has read a real calendar.

## Verification
- Command: the touched test files, with `GETMOREDONE_NO_MAPPED_WINDOWS=1`. The full suite runs on CI.
- Mutation: every new test was turned red by a mutation of the verbatim line it names (29 mutations, plus each of the five write paths separately).
- On screen: NOT RUN.

## Walk checklist (run from source; quit the packaged app first)
1. A day with a meeting, a lunch, a buffer and an item, in both themes: the
   meeting (purple stripe, real times) does not read as a block.
2. Press **↻ Calendar** with the network off: the failure is shown on the
   status line and the line above the grid, and the meetings read earlier stay
   drawn with their age.
3. A real calendar with a declined meeting, a *free* event and an all-day
   event: none of the three holds a box; the all-day one is in the line above
   the grid; the status line counts the left-out ones.
4. Export a day with **⤴ Google Calendar**, then press **↻ Calendar**: nothing
   changes on the grid, and the status line counts them as *exported*.
5. Open a day not read before, with Google set up: about 1.5 s later the line
   above the grid changes to *Calendar as of …*, and the status line does not.

## Review findings fixed before push
- learning-qa (cold) and a cold correctness pass found: a read that skipped a
  calendar or event deleted its known meetings and showed the date as fully
  read; one meeting on two calendars took its declined/editable state from the
  wrong copy; a day-old read time showed without its date; an ignored meeting
  outside the day was shown nowhere; a dismissal could be lost to a concurrent
  read; an ignored meeting that became editable could never hold again. All
  fixed with tests. **CIP-M2.8 changed**: the first-listed calendar's copy
  decides, not the most permissive copy; the spec records why.
- Dropped as low: the slot repair refuses the whole date when one block is
  under a meeting; a Refresh can be refused in the instant after a read ends;
  `local_zone()` (tzlocal, D5) has no caller, so the OS zone is used;
  `focusTime`/`outOfOffice` events are not filtered and hold boxes.

## Risks / Known gaps
- Times are converted to this machine's zone once, when read (D5). A laptop
  moved across zones shows the old wall-clock times until the day is read
  again. This is the same choice archived CE-A17 and CE-A21 describe for the
  export, now recorded as D5.
- Batch 2, editing a meeting from the Plan (CIP-M4), is not built.

## Next agent actions
- Mark CIP-M3.6 and CIP-M5.4 `done` in `docs/spec_coverage.md` once the walk
  passes them, or file what it shows.
