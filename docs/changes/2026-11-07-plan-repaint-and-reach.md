# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: plan-repaint-and-reach

## Summary

Four things reported from the running Plan screen. The first three are one
cause, and it is the cause PD-M10 got half right earlier today.

**The reports.**

1. "Moving a Day Block creates a blank panel that immediately shows if the
   mouse moves outside the panel area."
2. "I can't move an item into the early or late extended sections."
3. "Scheduling on a non work day creates a message, but *schedule anyway*
   doesn't work (or the item doesn't show up)."
4. "The Day Plan window should scroll as I drag an item up or down to an area
   not shown."

**The cause (PD-M11.1).** Both panes were rebuilt by taking the scroll frame
out of the grid, destroying its children, building the new rows and putting the
frame back. A `CTkScrollableFrame` is a frame of rows inside a canvas inside a
frame, and the frame that leaves the grid is the outer one — so the canvas is
unmapped with it, and on the way back both the width of the canvas window the
rows are drawn in and the scrollregion are restored by `<Configure>` handlers,
which run when the event queue is next serviced. An idle flush does not service
it. The pane came back blank and filled itself in on the next event, which in
use was the next mouse movement — report 1, in the words of the report. The
rows are now destroyed and rebuilt where they are.

That is also reports 2 and 3, which are that pane twice over. A drop on
**Earlier** writes the day's new hours and the block, and *Schedule anyway*
writes the block — both covered by tests that pass
(`test_pdm52_a_drop_above_moves_day_start_back`,
`test_pdm7_a_non_work_day_asks_before_scheduling`) — and both then redrew a
pane that did not come back.

**PD-M10 was treating the symptom.** It read this as a missing flush and added
one. The flush was not wrong, but the rebuild around it was what kept the pane
off the screen, which is why the symptom changed from stale to blank rather than
going away.

**`update` was tried and rejected, with a measurement.** The macOS display path
draws on a pass of the platform run loop, which `update` turns and
`update_idletasks` does not. It was put at the end of every pane rebuild and
measured: six tests of this screen took **four minutes at 120% of a CPU**, on
the machine the user was working on at the time. It is also the hang
`on_drag_release`'s `after_idle` exists to avoid. It is out. The flush stays at
idle tasks, now with no unmap to recover from, and whether that is enough is
PD-M11.8 — a look at the screen.

**Report 2 had a second cause of its own.** The **Earlier** and **Later** boxes
were rows of the scrolling grid. A day of eighteen half hours is several
hundred pixels taller than the pane, so **Later** sat below the bottom of it,
and with no way to scroll while holding a drag there was no gesture that
reached it. Both ends now sit in holders of their own outside the scroll frame,
one above it and one below it, always on screen. That moved them out from under
`virtual_under_pointer`'s first guard, which refused unless the pointer was
inside `blocks_scroll` — right while they were rows of that grid, and a refusal
of every drop on them once they were not. Every existing test of that drop
passed either way, because the helper that places the pointer puts it inside
`blocks_scroll` as well.

**Report 4 is the autoscroll (PD-M11.5).** A drag held within 32px of the top or
bottom edge of the day's viewport scrolls the day 24px every 60ms until the
pointer leaves the zone or the drag ends. On its own `after` clock, because a
pointer held still delivers no motion events — a scroll driven by motion alone
would stop exactly where the day most needs to move. Distance per tick is
converted through the canvas's own `yscrollincrement`, which CustomTkinter sets
to 8px on macOS and 1px on Windows, so a tick is the same distance on either.
The hover outline is re-read after each tick, since the boxes move under a
pointer that does not.

## Files changed

- `src/getmoredone/screens/plan.py` — `load_items` and `load_blocks` rebuild in
  place; `earlier_holder` / `later_holder` in `create_day_pane` with the two
  ends built into them; `virtual_under_pointer` without the `blocks_scroll`
  guard; `_day_canvas`, `_autoscroll_direction`, `_autoscroll_steps`,
  `_tick_autoscroll`, `_pump_autoscroll`, `_stop_autoscroll`; the three
  autoscroll constants; `_autoscroll_job` in `__init__`; `_flush_redraw`'s
  docstring corrected
- `tests/test_plan_screen.py` — fourteen `test_pdm11*` tests, the `_FakeCanvas`
  stand-in and the `_fake_canvas` / `_pointer_at` helpers;
  `test_pdm51_a_virtual_box_sits_at_each_end` rewritten (see below);
  `_pointer_on`'s docstring corrected
- `CHANGELOG.md`, `docs/USER_GUIDE.md` (the two ends are fixed strips; the day
  scrolls itself while you drag),
  `docs/implementation_plan_2026-11-06_plan_day_controls.md` (a PD-M11 section,
  and PD-M10 marked as superseded in part), `docs/spec_coverage.md` (eight rows,
  and PD-M10.7 marked superseded), `BACKLOG.md` (the four reports marked
  addressed, and the adjacent issue below)

**One test was changed rather than added.**
`test_pdm51_a_virtual_box_sits_at_each_end` asserted that the Earlier box was a
row of the scrolling grid above every slot row and the Later box a row below
them all. That was a true statement about the arrangement in which Later could
not be reached. The criterion — one above the first box, one below the last — is
unchanged; it is now counted in the day pane's rows rather than the grid's.
Case (b) of the repo's rule: the behaviour changed on purpose.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py -q`
  (niced; the only file either change touches)
- Result: **189 passed, 17 skipped in 76s**. The 17 skips are the on-screen
  geometry tests the environment variable turns off.
- Mutation gate: **15 mutations, 15 red, every one at exit 1**, one per new
  test (two tests of `_autoscroll_direction` mutate different branches of it).
  Each mutation reverted a shipped line to its verbatim original or deleted
  the line that was added; `plan.py` was restored from a byte copy after each
  and compared equal at the end. Exit 1 throughout, so every red was a failed
  assertion rather than a module that would not import.
- `test_pdm51_a_virtual_box_sits_at_each_end` passes as rewritten; no other
  pre-existing test in the file needed changing.

**The first attempt at this is worth recording.** The repaint fix originally
added `update()` to `_flush_redraw`. With it in place, six tests of this screen
took four minutes at 120% of a CPU, and the user -- who was working on that
machine -- had to stop the run. `update` turns the platform run loop on every
pane rebuild. It was removed before anything was committed, and the measurement
is the reason PD-M11 settles the question rather than leaving it open.

## Risks / Known gaps

- **The repaint fix is reasoned, not observed.** The unmap-and-remap mechanism
  is read off CustomTkinter's source — `ctk_scrollable_frame.py` binds the
  scrollregion to the inner frame's `<Configure>` and the window width to the
  canvas's — and it fits all three reports. Whether the pane is now on screen
  immediately is still a question only the running app can answer. If it is
  not, the remaining candidate is the macOS draw-at-run-loop behaviour, and the
  answer there is a cheap one-shot repaint nudge rather than `update()`.
- **The autoscroll arithmetic is tested against a stand-in canvas.** The real
  one's size is whatever the window gives it.
  `test_pdm115_the_day_canvas_is_the_scroll_frames_master` is what ties the
  stand-in to the widget, and it is the test that fails if a later
  CustomTkinter puts something other than the canvas at `blocks_scroll.master`.
- **`_day_canvas` reads Tk's `master`**, because `CTkScrollableFrame` exposes no
  accessor for its canvas. If that ever stops being a canvas the day stops
  scrolling itself and nothing raises.
- **PD-M5.7 is untouched**: a *block* dropped on **Earlier** or **Later** is
  still refused with a message. Now that both ends are always visible and the
  pane repaints, that refusal is finally readable. If the gesture should
  lengthen the day and carry the block, that is a rule change.
- **Adjacent issue found, not fixed:** the same remove-and-rebuild pattern is on
  six other screens — `today.py`, `upcoming.py`, `all_items.py`,
  `completed.py`, `hierarchical.py`, `vps_planning.py`, all from `9525d94`.
  Every one unmaps a `CTkScrollableFrame` to rebuild it. None was reported, and
  six screens' worth of UI regression is not a change to make alongside this
  one. In `BACKLOG.md` with the mechanical fix written out.
- **Adjacent issue, still not fixed:** `drag_schedule.py:1340` builds its drag
  label on the press, the defect PD-M10.3 fixed on this screen.
- Other work in this repo has uncommitted changes to `NOTES.md`,
  `date_utils.py`, the APE screens and `vps_manager.py`. None of it is in this
  batch and none of it was staged.

## Next agent actions

- PD-M11.8 on screen: a block moved between half hours appearing without a
  further mouse movement; an item dropped on **Earlier** and on **Later**;
  *Schedule anyway* on a Saturday showing the block it wrote; and the drag-edge
  scroll in both directions.
- Twelve commits are now unpushed, and no sweep has run over any of them.
