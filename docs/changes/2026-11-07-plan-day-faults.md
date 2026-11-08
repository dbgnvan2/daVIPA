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
  reports "the question could not be completed — nothing was scheduled", writes
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
(60) and `PD_AUTOSCROLL_STEP_PX` (16) as module constants, and
`day_autoscroll_direction` / `day_autoscroll_fraction` / `autoscroll_day` /
`_start_autoscroll` / `_autoscroll_tick` / `_stop_autoscroll`. While a drag is in hand, a pointer
within 24px of the day pane's top or bottom edge — **or past it**, which is the
gesture the report describes — scrolls the pane 16px every 60ms, and the
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
- `NOTES.md`
- `docs/changes/2026-11-07-plan-day-faults.md` (this note)
- `docs/changes/2026-11-07-plan-day-faults-screen-checklist.md` (the on-screen
  pass this batch cannot do itself)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS= taskpolicy -b venv/bin/python -m pytest tests/test_plan_screen.py tests/test_ci_contract.py -q`
- Result: **red, with a known cause outside this change** — 284 passed, 1
  failed, 1 skipped. Reported as red rather than as a pass: the exit status is
  non-zero, and a batch that calls that PASS teaches the next reader to read
  past a failure line.
  The failure is `test_pbm61_a_tall_row_keeps_its_two_lines_together`, a
  mapped-window layout assertion over `plan_blocks.build_item_row`. It fails on
  `HEAD` too, this change touches neither `plan_blocks.py` nor that test, and it
  matches the layout test already known red on `main`.
- 13 new tests, 2 existing tests adjusted, before the fix pass below added 6
  more tests and adjusted 3. **Commit `1ae0397`'s subject line says "fourteen
  tests" and is wrong** — there are 13. It is left as it is because the commit
  is not the branch tip and rewording it means rewriting two commits of
  history for a subject line; the error is recorded here instead.
  Every new test proved by mutation:
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

## Fix pass — the sweep's findings

`learning-qa` over `6d86791...HEAD` returned 10 findings, one high, after
`/code-review` had returned 3. Disposition:

- **Fixed (1 high).** `PD_AUTOSCROLL_UNITS = 1` was not a distance.
  `CTkScrollableFrame.__init__` configures the canvas's `yscrollincrement`
  itself and differently per platform — 8 on macOS, 1 on Windows, unset on
  Linux, where Tk falls back to a tenth of the pane — so one unit per 60ms was
  ~133px/s, ~17px/s and ~500px/s for the same line of code. The constant's own
  comment ("roughly a box every two ticks") was true on no platform, and no
  test noticed because every test asserted the arguments to `yview_scroll`
  rather than any movement. Now `PD_AUTOSCROLL_STEP_PX = 16` and a new
  `day_autoscroll_fraction`, which converts pixels to a fraction of
  `bbox("all")` and scrolls with `yview_moveto`. 16 is a multiple of 8 so the
  macOS increment cannot round the step away. The tests assert the resulting
  fraction with the arithmetic written out, not the call.
- **Fixed (4 medium).** The confirmation arm is now `_ask_yes_no`, and
  `clear_day` — the nearest sibling, in the same file, gating a transactional
  delete — asks through it too (P5). The `None` status no longer claims a
  cause: the `TclError` came out of the single Tcl call that both shows the
  dialog and returns the answer, so "it was never shown" is a guess, and it is
  the wrong guess in the case where the user answered yes; the sentence now
  says "could not be completed" and names a remedy. The deferral test's queue
  assertions are labelled provisional in its docstring, since the queue is the
  candidate cure for an unproven cause. And the gesture is covered end to end
  by `test_pdm1111_the_gesture_itself_survives_a_question_that_raises` —
  before it, every test of the failing dialog called `block_item` directly.
- **Fixed (1 low, in a line already being rewritten).** `bool(askyesno(...))`
  → `answer is True`: for a confirmation the truthy direction is the unsafe
  one. Also the two stale `after_idle` references in `_flush_redraw`'s
  docstring, which this batch had removed from the code.
- **Refuted by measurement (2 medium).** Both rested on "Tk's `after` is
  registered on the interpreter, not the widget". It is registered on the
  widget: `Misc.after` → `_register(..., needcleanup=1)` appends the Tcl
  command to that widget's `_tclCommands`, and `Misc.destroy` deletes them.
  Probed with pytest — schedule, destroy, pump due timers — the command is
  gone, the callback never runs, no stderr. So neither the autoscroll tick nor
  the deferred drop can run after the screen is destroyed, and the two
  `winfo_exists` guards the findings asked for would have been unreachable
  code. Recorded in `BACKLOG.md` with the probe.
- **Deferred (1 medium, 1 low).** The other 20 `askyesno` / `askokcancel`
  sites across 14 files, on scope — each needs its own user-visible sentence,
  which is its own batch. And `PD_AUTOSCROLL_MARGIN_PX`'s value is still not
  pinned by a test, which is below the repo's fix threshold. Both in
  `BACKLOG.md` with the reasons.
- **Fixed (1 low, docs).** This note's own overstatements: `NOTES.md` missing
  from "Files changed", a non-zero exit reported as PASS, and the commit
  subject's "fourteen tests". All three corrected above.

6 new tests from this pass, 3 existing tests adjusted. The adjusted ones are
the two `test_pdm124` autoscroll tests, which asserted the opaque unit —
reason **(b), the behaviour changed intentionally** — and the dialog test's
status assertions, which moved with the reworded sentence, same reason. 11 more
mutants, one per fix, each applied alone against the test that names it, all 11
killed, source restored and its hash verified after each.

### Re-sweep of the fix pass

The fix commits were swept again — they are the least-reviewed code in the
batch, written last. Six findings, one medium plus one low-medium raised
outside the numbered list. Both of those are fixed:

- **The class is every modal, not every confirmation.** `_ask_yes_no`'s own
  docstring had defined it as "every confirmation on this screen", and the
  measured fault is a modal *failing to return an answer*.
  `ask_custom_minutes` is the third modal in this file, 90 lines below the new
  helper, reached from the context menu's "Custom…", and
  `CTkInputDialog.get_input` is `wait_window` plus a read of the entry — the
  same machinery. It now carries its own arm (it has no yes/no answer to pass
  through `_ask_yes_no`). By the criterion this batch used to defer the rest —
  same file, same screen — it should never have been left out.
- **The arm had cost the evidence.** `clear_day` previously let a `TclError`
  reach `report_callback_exception` and therefore stderr, which is the only
  reason this fault is understood as far as it is. The new arm converted it to
  a status line and logged nothing, and a status line is overwritten by the
  next one. Every other failure arm on this screen logs as well as says;
  these now do too. For a fault whose mechanism is still unproven, trading the
  symptom for the evidence was the wrong direction.

Three claims were wrong and are corrected, two of them mine from the fix pass
itself:

- `day_autoscroll_fraction`'s docstring said it returns `None` for "a day that
  fits its pane". It returns 0.0 for that case (`visible` is 1.0, so the clamp
  is 0.0); the `None` is for an absent scrollregion only.
- The reworded status said "Try **the drop** again", but `_require_block_day`
  is reached from the AutoLoad button and the padding button as well as from a
  drop and a day extension — so two of four callers told the user to retry a
  gesture they never made. It is gesture-neutral now, and a test asserts the
  sentence names no gesture.
- `NOTES.md` and the checklist repeated "half a box per tick" unqualified,
  while the box height is a user setting. Both now say "at the default box
  height".

Three findings were recorded rather than fixed, all below medium, all in
`BACKLOG.md` with their reasons: the denominator in `day_autoscroll_fraction`
is `bbox("all")` while the fractions either side of it are scrollregion
fractions (a latent coupling the reviewer could not construct a reachable path
for, correct today by an event ordering nothing asserts); `_ask_yes_no`
collapses every non-answer other than a raise into the user's refusal; and the
16px step is fixed against a configurable box height.

3 new tests from this pass, 6 more mutants, all killed, source restored and
hashed after each. The re-sweep's own verdict is that one further pass is owed
in a different failure family, since no pass over this branch has covered the
repo's UI contract — that pass ran next, and its result is below.

### Cold UI-contract pass

The re-sweep's own verdict was that a further pass was owed in a different
failure family, since no pass over this branch had covered the repo's UI
contract (`~/.claude/standards/ui-regression.md`, the theme rules, the screen's
controls as a contract). Run cold over the whole range: seven findings, four
major. All four are fixed, and two of the three minors with them, because they
are errors in the checklist the user will act on.

- **The hover outline was asserted as a call, not as an outline.** Both
  PD-M12.4 tests stub `update_hover_target` and assert `hovered == [1]`, and
  `update_hover_target` had no behavioural coverage anywhere in the suite — so
  the outlined box could be the wrong box with the suite green. That is the
  same shape as the unit-versus-distance finding this batch fixed one step
  earlier, one call deeper. `test_pdm129_scrolling_rereads_the_hover_onto_the_box_now_under_the_pointer`
  runs the real thing and asserts which frame carries the 2px border before
  and after a scroll step.
- **`clear_hover_target` put back the border width but not its colour.** It
  was already in `BACKLOG.md` at low from an earlier pass, on the stated
  grounds that "a successful drop hides it" — and PD-M12 stopped that bounding
  it. The hover is now re-read every 60ms, so a pointer held still at an edge
  walks it down every box the day scrolls past, and a drag abandoned away from
  the boxes gets no rebuild: the trail went from one box to the whole day, in a
  colour the theme rules reserve for one action's emphasis. Fixed, and the
  BACKLOG entry re-rated rather than left with its stale rationale. This is
  "every in-loop fix is itself in scope for the next pass" doing its job.
- **The checklist quoted a sentence the code no longer says.** Item 3's second
  outcome still read "Try **the drop** again" — the wording the re-sweep had
  just removed, one commit earlier, in this same batch. Fault 3's disposition
  turns on which of three outcomes comes back, so the decision tree had the
  right answer spelled wrong. Corrected, and nothing in `docs/` quotes the old
  sentence now.
- **`docs/USER_GUIDE.md` had not been updated.** A new drag affordance and
  three new status sentences, in a section that already documents the
  neighbouring affordances and quotes their status lines verbatim, with a docs
  sync gate in CI. Two entries added: holding a drag at either edge, and what
  a question that cannot be completed says on each of the three paths.
- **Two more checklist errors, both of which would have produced a false
  failure report.** It told the tester to hold "within about a box height" of
  the edge, which is outside a 24px band — an empty box is 34px on a 36px
  pitch — so a correct build would have read as "it does not scroll"; and it
  offered the sidebar and the pane heading as interchangeable release targets
  for item 5 when only the heading sets a status line. Item 4 now says 20
  pixels, item 5 is split in two, and `PD_AUTOSCROLL_MARGIN_PX`'s comment no
  longer claims the band is three-quarters of a box or that it stays clear of
  the last visible one.

One minor was recorded rather than fixed, in `BACKLOG.md`: the autoscroll band
is the scroll canvas, while the pane the user sees is the canvas plus its
scrollbar, so the rightmost strip is a dead zone. Recorded because the fix is a
choice between two widgets that wants checking against a mapped window, not a
substitution.

The pass also reported clean on what it was pointed at and found nothing wrong
with, which is worth as much: no hard-coded colour is introduced, the
`set_status` severity words match the file's own use at all 30 call sites, every
new sentence names what was not done and keeps the file's em-dash convention, no
control is removed, renamed or relocated, the drag label cannot be left stale by
a scroll, and `yview_moveto` drives `yscrollcommand` so the scrollbar stays in
step. It could not assess anything needing pixels, which is still items 1, 1a
and 3 of the checklist.

2 new tests, 4 more mutants, all killed. **It also could not read the diff** —
no Bash tool reached that worker, so it reconstructed the change set from the
brief and read the present state of each hunk. Its findings were verified
against the code here before being acted on; the box-pitch arithmetic in
particular was checked against `plan_blocks.py` rather than taken on trust.

## Risks / Known gaps

- **Fault 1 is open.** See above.
- **Nothing in this batch has been seen on screen**, which is why
  `docs/changes/2026-11-07-plan-day-faults-screen-checklist.md` exists. Three
  of the four passes said so independently. The checklist is now six items, and
  three of its own instructions had to be corrected by the last pass — so if an
  item still reads as not working, check the BACKLOG entry for the autoscroll
  band's dead zone before concluding the feature is broken.
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
- The autoscroll speed (16px per 60ms, half a box per tick) is a judgement and
  has not been felt by a human. Item 4 of the checklist asks whether it is
  usable. It is now the same speed on all three platforms, which it was not
  before the fix pass, but it has been measured on none of them — the tests
  assert the fraction asked of the canvas, not pixels that moved on a screen.

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
