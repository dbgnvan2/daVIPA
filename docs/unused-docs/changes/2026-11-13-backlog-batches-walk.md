# Handoff Note

- Date: 2026-11-13
- Topic: backlog batches BSF, PRC, LM3, LPR, PBB, UPD-A12, and the on-screen walk they still owe

## Summary
Seven backlog batches were built, reviewed cold and pushed to `main` on
2026-11-13. Each batch's criteria are in `docs/spec_coverage.md` under its own
heading. The items they closed are in
`docs/unused-docs/backlog_archive_2026-11-13.md`. Nothing below was seen on
screen. Tests pass for each batch, but no session drove the app.

## Verification
- Command: the touched test files for each batch, with `GETMOREDONE_NO_MAPPED_WINDOWS=1`. The full suite ran on CI.
- Result: PASS for each batch (CI green on 3.11, 3.12 and 3.13 through `c58a49d`). Later pushes: see the CI run for each.
- On screen: NOT RUN.

## Walk checklist (run the app from source; quit the packaged app first)
1. **Scheduler, drag onto a project (DRP-M1..M3).** Drag an item that is
   already filed under another project onto a project box. A question should
   appear. Answer Yes; the item moves. If no question appears, the status line
   under the screen should say *Not moved — the confirmation could not be
   shown*, and the item should stay put. Either way, the drag label must not
   stay on screen.
2. **Scheduler, drag a Weekly Tactic onto a date in a week that already has
   one.** Expect the "Week Already Taken" notice, or, if the platform refuses
   it, the same text on the status line. The list must redraw.
3. **Plan, the lunch chip on Earlier/Later (LM3-M1).** Drag the Day Settings
   lunch chip past either end of the day. Nothing moves, and the status line
   says *Lunch stays inside the day — drop it on a Time Block*.
4. **APE Week Actions (AWA2-M1).** The right panel's rows have no grip at the
   left. The Today tab's rows still do, and a Today reorder still works.
5. **The six list screens (LPR-M1).** Open Today, Upcoming, All Items,
   Completed, Hierarchical and VPS Planning, and change a filter on each. The
   list redraws with no blank pane and no wait for a mouse move. Watch for
   flicker, since the rebuild now happens with the pane on screen.
6. **+ Break / + Buffer (PBB-M1).** On a day with work at 08:00, press `+ Break`.
   It lands in the first empty half hour, not beside the 08:00 task.
7. **Filter labels (UPD-A12).** APE Week Assignment and APE Week Actions say
   *SubSegment:* and *Category:*. Check that the filter row still fits the
   half-width panel.
8. **Priority cells (PRC).** Today, Upcoming, Hierarchical, Completed and All
   Items show `P:n` in the same width. The Set Parent and Show Related pickers
   colour the score cell.

## Risks / Known gaps
- DRP-M2/M3 and LPR-M1 are `partial` in `docs/spec_coverage.md` until the walk.
- SBN-A3 is open as a decision, with a recommendation: build PD-M14.4 in a
  batch that can be walked. It rewrites `slot_index` on every date when Day
  Start changes, so it was not built unattended.

## Next agent actions
- Mark DRP-M2, DRP-M3 and LPR-M1 `done` in `docs/spec_coverage.md` once the
  walk passes them, or file what it shows.
