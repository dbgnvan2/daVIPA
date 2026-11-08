# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: plan-day-faults — the four faults reported from the running Plan screen

## Summary

The four faults recorded at the top of `BACKLOG.md` under "Reported from the
running screen — Plan / Day Plan (2026-11-07)" were investigated one at a time.
Two are fixed, one is implemented, and one is **not fixed** — diagnosed as far
as it can be without seeing pixels, and left open with the evidence.

### Fault 3 — "Schedule anyway" does nothing. **Established, and fixed.**

The open half of the report ("it does not schedule, *or* the item does not
appear") is settled: **it does not schedule.** Measured against the running
app, answering Yes on a Saturday drop left the day's `time_blocks` table empty,
and the app's stderr carried:

```
Exception in Tkinter callback
  plan.py:1748  self.after_idle(lambda: self.block_item(item, target))
  plan.py:1156  if not self._require_block_day():
  plan.py:1505  if messagebox.askyesno(
  tkinter/messagebox.py:76  res = Message(**options).show()
_tkinter.TclError          # empty message
```

`askyesno` raised instead of returning the answer. The traceback went to
stderr, which the user never sees, so the write never happened and nothing was
said. Two changes:

- `_ask_work_anyway` is split out of `_require_block_day` and carries a
  `tk.TclError` arm returning `None`. `None` is neither yes nor no: the caller
  reports "the question could not be shown — nothing was scheduled", writes
  nothing, and caches nothing, so the next drop asks again and can still be
  agreed to. Recording the failure as a refusal would turn a transient failure
  into a permanent negative (P1).
- `on_drag_release` defers the drop's work through a new `_after_release`,
  which uses `self.after(0, …)` instead of `after_idle`. The drop is a database
  write, a full pane rebuild and, outside the working week, a modal question;
  `after_idle` means "before the next redraw", which is the wrong queue for all
  three, and it is the context the raising `askyesno` was measured in.

**The mechanism of the `TclError` is not proven.** The byte-identical
`askyesno(title, message, icon="warning", parent=self)` call works from
`clear_day`'s button command on the same screen, and 29 other `parent=self`
call sites exist across the app, so the distinguishing factor looks like the
calling context rather than the arguments — but that was not established. There
is also a confound: the Yes click that produced the traceback was synthetic
(CGEvent) input, so the raise could be an artefact of how it was driven. The
*symptom* is independently confirmed by the user's report plus the empty table.
The failure arm is therefore defence that is correct either way, and the
`after(0)` move is the candidate cure, not a proven one. **Needs the user to
click Yes themselves** — item 3 of the checklist below.

### Fault 2 — item cannot be dropped into the early/late sections. **Not reproducible at handler level; almost certainly fault 3.**

Driven as real Tk events on a work day — press, motion, release onto the
"Earlier" row — the day extends to 07:30 and the item is blocked; onto "Later",
to 17:30. Verified with `plan_day_shape_unconfirmed = True` as well, which is
the state in the user's own settings file. `virtual_under_pointer()` returns
`"earlier"`/`"later"` correctly and `slot_under_pointer()` correctly returns
`None` there.

`extend_day_for` also calls `_require_block_day`, so on a Saturday — which is
the day the report was made on, and a non-work day under the defaults — this
gesture funnelled through the same failing dialog. That is the explanation on
offer. It is not proven, and the fault is not closed: **needs the user to try
it on a weekday** — item 2 of the checklist.

### Fault 4 — the Day Plan does not scroll past its edge. **Implemented.**

New in `plan.py`: `PD_AUTOSCROLL_MARGIN_PX` (24), `PD_AUTOSCROLL_INTERVAL_MS`
(60) and `PD_AUTOSCROLL_UNITS` (1) as module constants, and
`day_autoscroll_direction` / `autoscroll_day` / `_start_autoscroll` /
`_autoscroll_tick` / `_stop_autoscroll`. While a drag is in hand, a pointer
within 24px of the day pane's top or bottom edge — **or past it**, which is the
gesture the report describes — scrolls the pane one unit every 60ms, and the
hover highlight is re-read after each step because the boxes have moved under a
pointer that has not. The x range is the pane's own, so dragging up the
unscheduled list does not scroll the day beside it. An end already reached asks
for nothing, so holding at the bottom of a fully scrolled day does not repaint
it sixteen times a second. `on_drag_motion` arms the timer and each tick
re-arms the next; `_end_drag` cancels it.

### Fault 1 — moving a block leaves a blank panel. **NOT FIXED.**

Narrowed, not solved. Measured immediately after a real `move_block_to_slot`,
with no event-loop turn in between: the pane is mapped at full size, none of
its 20 children is unmapped, the three boxes sampled are at correct sizes and
root positions, and the scroll canvas's window width, `bbox("all")`,
scrollregion and yview are already byte-identical to what a following
`update()` leaves them. So nothing in the widget tree or
the canvas is stale.

Two candidate fixes were built and both withdrawn rather than shipped:

- An explicit "settle the scroll panes" step, doing by hand what
  `CTkScrollableFrame` defers to its two `<Configure>` bindings. Measured to
  change **nothing at all** — the comparison above is exactly that measurement.
  Shipping it would have been a fix that does nothing.
- `self.update()` in `_flush_redraw`, to drive the Aqua window-server draw
  pass that `update_idletasks` does not reach. It drains the event queue until
  it is empty, and it does not always come back: the thirteenth `PlanScreen`
  built in one process hung in it inside `load_items`, with the suite's own
  tests as the reproduction. It also dispatches input, so a queued press could
  land in a row being torn down.

What remains unexplained is why the pixels wait for a pointer event when the
app's event loop turns continuously anyway. Recorded in `BACKLOG.md` with the
measurements and with the questions whose answers would narrow it, which are
items 1 and 1a of the checklist. `_flush_redraw` is unchanged in behaviour; its
docstring now records that it is not sufficient for this report, so the next
reader does not re-derive it.

## Files changed

- `src/getmoredone/screens/plan.py`
- `tests/test_plan_screen.py`
- `BACKLOG.md`
- `docs/changes/2026-11-07-plan-day-faults.md` (this note)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS= taskpolicy -b venv/bin/python -m pytest tests/test_plan_screen.py tests/test_ci_contract.py -q`
- Result: PASS — 284 passed, 1 pre-existing failure, 1 skipped.
  The failure is `test_pbm61_a_tall_row_keeps_its_two_lines_together`, a
  mapped-window layout assertion over `plan_blocks.build_item_row`. It fails on
  `HEAD` too, this change touches neither `plan_blocks.py` nor that test, and it
  matches the layout test already known red on `main`.
- 13 new tests, 2 existing tests adjusted. Every new test proved by mutation:
  17 mutants applied one at a time to the line each test names, each run
  against that test alone, all 17 killed, source restored verbatim after each.
  Two mutants had to be rewritten after surviving, and both survivals were
  informative rather than cosmetic: a `PD_AUTOSCROLL_MARGIN_PX = 25` mutant
  survived because the boundary test derives its coordinates *from* the
  constant, so the mutation moved the test with it — the band's comparison is
  what the test pins, and mutating `<` to `<=` kills it.
- The two adjusted tests are `test_pdm5_an_item_drag_onto_a_virtual_box_extends_the_day`
  and `test_pdm5_a_real_box_wins_over_a_virtual_one`. Reason **(b), the
  behaviour changed intentionally**: both drained the idle queue to run the
  drop, and the drop is now a zero-delay timer. They call a new
  `_run_due_timers` helper, which services `TIMER_EVENTS` only and is bounded —
  `update()` is the hang above, and a bounded pass over *all* event classes
  never reaches the timer, because a pane rebuild queues more than 200
  `<Configure>` events of its own.
- **Not verified on screen.** No on-screen run was done: the user's standing
  instruction is not to take over their machine for this. Everything above is
  from pytest driving real widgets on a withdrawn root, plus the app's own
  stderr from the earlier investigation. Items 1–5 of the checklist are what
  pytest cannot answer.

## Risks / Known gaps

- **Fault 1 is open.** See above.
- **The `TclError`'s cause is unproven**, and the `after(0)` move is a candidate
  cure with a real argument behind it, not a demonstrated one. If item 3 of the
  checklist still fails, the next step is to find what Tk/Aqua objects to
  between `clear_day`'s context (works) and the drop's (raised): the open
  question is the calling context, since the arguments are byte-identical.
- **Fault 2 is closed only by inference.** If item 2 fails on a weekday, the
  `virtual_under_pointer` path is innocent — it was driven end to end — and the
  next place to look is which widget actually receives the press, which leads
  to the adjacent issue below.
- **Adjacent issue found, not fixed.** `bind_item_drag` binds only
  `[frame] + list(frame.winfo_children())`, while `bind_block_handlers`
  deliberately walks `_subtree(frame)` because "a press on the text reached
  nothing at all". Probed: the `DepthBarStack` bars inside an item row carry no
  bindings, so a press that starts on a depth bar starts no drag. Not swept
  into this change; recorded in `BACKLOG.md`.
- **The sweep's PLAUSIBLE low finding is not this bug.** `_require_block_day`
  records permission against one read of `self.selected_date` while the caller
  reads it again after the modal returns. That is a real date race and it stays
  in `BACKLOG.md`, but the reported fault is the raise, not the race: the
  traceback shows the dialog never returned at all. The BACKLOG note that said
  "this report may be that demonstration" has been corrected.
- The autoscroll speed (one unit per 60ms) is a judgement, set from the box
  height, and has not been felt by a human. Item 4 of the checklist asks
  whether it is usable.

## Next agent actions

- Get the user's answers to the five checklist items, especially 1, 1a and 3.
- If item 1a says the pane fills in on *any* pointer motion rather than only on
  leaving the pane, fault 1 is the draw-pass theory and the next thing to try is
  a *bounded* event pump in `_flush_redraw` (`tk.dooneevent(DONT_WAIT)` under a
  budget) rather than `update()`. If it fills in only on leaving, the trigger is
  something bound to `<Leave>` and the theory is wrong.
- Fix the `bind_item_drag` subtree gap, with the same `_subtree` walk
  `bind_block_handlers` already uses, and a test that a press on a depth bar
  starts a drag.
