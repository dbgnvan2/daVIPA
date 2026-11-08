# On-screen checklist — the Plan day range (2026-11-08)

Four things pytest cannot answer about this batch. One pass through the app
covers all of them. Companion to `docs/changes/2026-11-08-plan-day-range.md`.

Items 1 and 2 are the two acceptance criteria the plan marked **not
code-testable** (PD-M14.4 and PD-M15.6). Items 3 and 4 are the two the
implementation turned up: the drawn day is a new thing on screen, and no test
can tell you whether it *reads* as a day.

## Before you start

- Quit `/Applications/daVIPA.app` if it is running — a source launch exits
  silently while the packaged app holds the lock.
- Launch from this worktree: `./start.sh`
- **This writes to your real database.** Every item below is undone by Clear
  Day or by right-clicking a block and deleting it, except item 4, which asks
  you to put a break outside your day — delete that one by hand when you are
  done.
- **Check ⚙ Day Settings first and write down Day Start and Day End.** If you
  used Earlier or Later in the shipped app, those hours may already be wider
  than you set them: the old behaviour wrote them and there is no way to tell
  which 07:30 was yours. Item 3 is also the check that nothing moves them now.
- Pick a **weekday** (Mon–Fri) for items 1, 3 and 4. Item 2 wants a weekend.

## 1. Does a drop on Earlier or Later work with a real pointer? (PD-M14.4)

The fault as reported: "User should be able to drag to the Early or Late Block
regardless if anything is after the Morning block or before the Evening block."
There is no adjacency guard in the code and the tests say the gesture works, so
this is about the pointer and the pane, not the logic.

1. On an **empty** day, drag an unscheduled item onto the **Earlier** box at the
   top of the day column. Release.
2. On the same day, drag another item onto the **Later** box at the bottom.
3. Now block an item into the **last** box of the day, and drag another onto
   **Earlier**.
4. And the mirror: with a block in the **first** box, drag one onto **Later**.

Record for each:

- Did the block appear, and in a half hour outside your configured day?
- What does the status line say? It should end with *the day is drawn wider to
  show it and ⚙ Day Settings is unchanged*.
- Did any of the four do nothing at all, or say nothing?

## 2. Does a real Yes on the work-day question schedule? (PD-M15.6)

The fault as reported: "You are simply ignoring the Work day settings and
letting me schedule on a NON checked Day. Warning happens once on the first
block." The dialog fault behind this was fixed in the previous batch and is
unreleased, so this is the first chance to see it on screen.

1. Pick a **Saturday** (or any day your weekday list excludes).
2. Drag an item onto a box. The work-day question should appear.
3. Answer **Yes**.
4. Drag a **second** item onto another box.
5. Add a **break** from the toolbar, and press **AutoLoad**.

Record:

- Did the block appear after the Yes?
- Was the question asked **once**, on the first block only — not again for the
  second item, the break or AutoLoad?
- Did anything happen with no question and no block?

## 3. Does the day column widen and then come back? (PD-M13)

This is the first reported fault — "Clear day doesn't reset the time blocks to
range in settings" — and the new behaviour behind it.

1. On a weekday, drop two items onto **Earlier** and two onto **Later**, so the
   day column is drawn well outside your hours.
2. Open **⚙ Day Settings**. **Day Start and Day End must be exactly what you
   wrote down.** This is the user's own instruction — "do NOT change the length
   of Day in Settings" — and it is the one thing on this list that would be a
   straight regression.
3. Close the dialog. Press **Clear Day** and answer Yes.
4. Look at the day column.

Record:

- Does the column now run exactly from your Day Start to your Day End, with no
  empty half hours left above or below?
- Did Day Settings still show your own hours in step 2?
- Switch to another date and back. Is the column the same both times?

## 4. Does a break outside your hours keep its box? (PD-M13.9)

The decision you took when this was planned: Clear Day removes scheduled items
only, so a break you deliberately put outside your hours should still be there
afterwards, with the column still wide enough to show it.

1. Drop an item onto **Earlier** to make a half hour before your Day Start.
2. Right-click that new block and change it to a **break** — or, if that is not
   offered, add a break and drag it into the early half hour.
3. Block a couple of ordinary items into the day.
4. Press **Clear Day** and answer Yes.

Record:

- Is the break still drawn, at the time it was at?
- Does the column still start early enough to show it, with the rest of the day
  back to your configured range?
- Is anything listed under **Outside the day** in the left column? Nothing you
  put there in this pass should be — but see the note below before you call it
  a fault.

**If something you did not just create is listed under "Outside the day",**
that is this batch surfacing an old row rather than breaking a new one. A
block's stored position counts half hours from Day Start, not a clock time, so
if you ever moved **Day Start** in ⚙ Day Settings, a block saved under the old
start can now land before midnight or past it. Before this change such a block
was drawn in the day at a wrong time — usually 00:00 — and refused every move
and resize, with deleting it the only way out. It is now listed under "Outside
the day" with its own stored time, and you can drag it back onto the day. If
you see one, that is the fix working; note the label and the time it shows.

## Still open from the previous batch

`docs/changes/2026-11-07-plan-day-faults-screen-checklist.md` items **1** and
**1a** — whether the Day Plan repaints after a block is moved — are unanswered
and are not touched by this batch. They are a separate question and can be done
in the same pass if you have the app open.
