# On-screen checklist — the four Plan / Day Plan faults (2026-11-07)

Five things pytest cannot answer. One pass through the app covers all of them.
Companion to `docs/changes/2026-11-07-plan-day-faults.md`.

## Before you start

- Quit `/Applications/daVIPA.app` if it is running — a source launch exits
  silently while the packaged app holds the lock.
- Launch from this worktree: `./start.sh`
- Pick a **weekday** in the date picker (Mon–Fri). Items 1, 2 and 4 need a
  normal work day so the non-work-day dialog stays out of the way. Item 3 is
  the only one that wants a weekend.
- Have a few unscheduled items in the left pane, and make the window short
  enough that the Day Plan has to scroll (item 4 needs a day taller than its
  pane).

## 1. Does the Day Plan repaint after a block is moved?

This is the one fault that is **not fixed**. The question is which of two
theories is right, so what you see matters more than whether it works.

1. Block an item into a box so the day has at least one block.
2. Drag that block onto a different box and release.
3. **Without moving the mouse at all**, look at the pane.

Record:

- Is the pane blank, or is the block drawn in its new place?
- **Which** pane is blank — the Day Plan on the right, the unscheduled list on
  the left, or both?
- Does the status line under the panes say `Moved to <time>`?

## 1a. What makes it fill in?

Only if item 1 showed a blank pane. This is the observation that splits the two
theories, so please do them in this order and stop at the first one that works.

1. Move the mouse **one or two pixels, still inside the Day Plan pane**. Does it
   fill in?
2. If not: move the mouse around **inside** the pane, without leaving it. Does
   it fill in?
3. If not: move the mouse **out of the pane**. Does it fill in then?

Any motion inside the pane filling it in means the pixels are waiting for a
draw pass, and the fix is a bounded event pump. Only leaving the pane filling it
in means something bound to the pointer leaving is doing the work, and the
theory in the handoff note is wrong.

## 2. Can an item be dropped into the Earlier / Later sections?

On a **weekday**:

1. Drag an unscheduled item onto the **Earlier** box above the first half hour
   and release.
2. Expected: the day's start moves back half an hour (e.g. 08:00 → 07:30) and
   the item appears in the new 07:30 box.
3. Repeat onto the **Later** box below the last half hour. Expected: the day's
   end moves out half an hour and the item lands in the new box.

Record whether each one worked, and if not, exactly what the status line said.

## 3. Does "Schedule anyway" actually schedule?

This needs a **non-work day**, so set the date picker to a Saturday or Sunday.

1. Drag an unscheduled item onto a half-hour box.
2. The dialog appears: *"<date> is not a regular work day… Schedule anyway?"*
3. Click **Yes**.
4. Expected: the item appears as a block in that box, and the status line names
   the time.

Record which of these three you get:

- **The block appears** — fixed.
- **Nothing appears and the status line says "the question could not be
  completed — nothing was scheduled. Try the drop again, or allow the day in
  Day Settings"** — the dialog is still raising, but it now tells you so
  instead of failing silently. Say so; that is a different next step.
- **Nothing appears and the status line says something else, or nothing** —
  still broken in a third way. Please copy the status line text.

Then, without changing the date, drag a **second** item onto another box. It
should go straight in without asking again.

Then press **Clear Day** on that same date and answer No. Expected: the day is
untouched and the status line says "Clear Day: nothing removed". That button's
question now goes through the same failure arm, so it is worth the one press.

## 4. Does the day scroll while an item is dragged past its edge?

Make the window short enough that the Day Plan has a scrollbar.

1. Pick up an unscheduled item and drag it over the Day Plan.
2. Hold the pointer near the **bottom edge** of the Day Plan pane — within about
   a box height of it — and **hold still**.
3. Expected: the day scrolls down steadily under the pointer, and the box
   highlighted under the pointer keeps up as the boxes move.
4. Hold near the **top edge**. Expected: it scrolls up.
5. Drag the pointer **below the bottom of the pane entirely**, still holding the
   button. Expected: it keeps scrolling.
6. Scroll to the very bottom and keep holding there. Expected: it stops and
   stays still — no flicker.
7. Release on a box. Expected: the item lands in that box, and the scrolling
   stops immediately.

Record whether the **speed** is usable — it is set to 16 pixels every 60ms,
about 270 pixels a second, which is half a box at the default box height (if
you have raised the box height in Plan Settings it is less than half). Too fast to aim,
too slow to be worth it, or about right?

## 5. Does the drag label still disappear on release?

A small thing that changed in the same area, worth one look while you are here.

1. Press on an unscheduled item and move the mouse, so the floating label with
   the item's name appears beside the pointer.
2. Release over something that is **not** a box — the pane heading, or the
   sidebar.
3. Expected: the label disappears at once, and the status line says to drop it
   on a half-hour box.

Record whether the label lingers.

## 6. Does the Custom block length dialog still work?

One press, because the re-sweep found it was the third modal on this screen
with no failure arm and it now has one.

1. Right-click a block in the Day Plan and choose **Custom…**
2. Type `45` and press OK.
3. Expected: the block becomes 45 minutes long.
4. Repeat and press **Cancel**. Expected: nothing changes and nothing is said.

Record anything else — in particular a status line reading "The block length
question could not be completed", which would mean that dialog raises the way
the non-work-day one did.

## Afterwards

`~/Library/Application Support/GetMoreDone/app.log` — anything new at the
bottom is worth pasting back, especially a traceback.
