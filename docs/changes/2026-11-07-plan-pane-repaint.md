# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: plan-pane-repaint

## Summary

Three things reported from the running Plan screen, which are one cause.

**The reports.**

1. "Bug - drag inside a day to earlier or later doesn't seem to work."
2. "Mouse pointer message is 'fix login bug'."
3. "The Day block pane isn't refreshing right away, seems to wait for a mouse
   movement of the app window."

**The cause (PD-M10).** Both panes are rebuilt the same way: take the scroll
frame out of the grid, destroy its children, build the new rows, put the frame
back. Tk draws from an idle handler, and every one of these rebuilds runs
inside an event callback or an `after_idle` of one, so the re-gridded frame
could stay undrawn until some later event arrived. On this machine that event
was the next mouse movement over the window. `load_blocks` and `load_items` now
end with a flush.

That accounts for all three reports:

- **Report 3** is the cause stated directly.
- **Report 1** needs no defect in the move. `move_block_to_slot`,
  `set_block_minutes` and `add_padding_block` all end in `load_blocks` alone —
  the three day-pane writes that do not go through `refresh()` — so a block
  moved to an earlier or a later half hour was written correctly and not drawn.
  Clear Day and AutoLoad call `refresh()` and were reported as working, which
  fits: rebuilding both panes churns enough geometry to get a redraw out of Tk,
  rebuilding one did not.
- **Report 2** is the drag label, and it had a second defect of its own. It was
  built and placed on the button **press**, so an ordinary click on an item row
  put that item's title beside the pointer. The release hid it again — but the
  hiding was not drawn either, so the title stayed. "Fix login bug" is a
  `demo_data.py` sample item, so this was the demo database.

**The label now waits for motion.** A press arms the text; the first
`<B1-Motion>` is what shows the label. A press with no motion is not a drag and
gets no label at all, which is the reason the stale one was reachable. Hiding it
flushes too, so a drag released over nothing — which writes nothing and rebuilds
nothing — still clears.

`update_idletasks` and not `update`: idle tasks are geometry and redisplay,
which is all that is owed. `update` also services the event queue, and these
rebuilds run from drag handlers, so dispatching a queued click inside one would
re-enter a rebuild that is destroying the widget the click is for — the hang the
`after_idle` in `on_drag_release` exists to avoid. The flush is wrapped in
`try/except tk.TclError` because it is called from a `finally`: a queued rebuild
can outlive the window, and an exception there would replace whatever brought
the code into the `finally`.

## Files changed

- `src/getmoredone/screens/plan.py` — `_flush_redraw`; called at the end of
  `load_items` and `load_blocks` and when the drag label is hidden;
  `_arm_drag_label` replaces the `_show_drag_label` call in `start_item_drag`
  and `start_block_drag`; `on_drag_motion` shows the label on the first motion;
  `_drag_label_text` in `__init__`
- `tests/test_plan_screen.py` — six `test_pdm10*` tests and the `_count_flushes`
  helper
- `CHANGELOG.md`, `docs/USER_GUIDE.md` (the drag label follows the pointer once
  you move), `docs/implementation_plan_2026-11-06_plan_day_controls.md` (a
  PD-M10 section), `docs/spec_coverage.md` (seven rows)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py
  tests/test_time_block_colors.py tests/test_plan_settings.py
  tests/test_ci_contract.py -q`
- Result: 1 failed, 316 passed, 18 skipped. The failure was
  `tests/test_ci_contract.py::test_rm3d_every_test_file_is_importable_on_its_own`,
  and it is not this change. It globs every `tests/test_*.py` and imports each
  one with the repo root stripped from `sys.path`;
  `tests/test_ape_period_consistency.py` -- untracked, from other work in this
  repo, written while the run was in flight -- had no path bootstrap yet and
  could not import `src`. That bootstrap has since landed in the file: the same
  import probe run by hand reports 0 failures, and the contract file re-run on
  its own is **81 passed, 1 skipped**. Nothing in the four files failed on this
  change's own account.
- Mutation gate: 6 mutations, 6 red.
- **One mutant was red for the wrong reason first.** The `on_drag_motion`
  mutation replaced part of the new `if`/`else` and left a dangling `if`, so the
  module failed to import and pytest exited 2 rather than 1. A syntax error is
  not a test earning its red. Rewritten to swap the whole body for the whole
  verbatim original; red at exit 1.

## Risks / Known gaps

- **The fix cannot be tested on screen.** No test can see whether a pane
  repainted; the six tests pin that the flush is asked for at the end of each
  rebuild and when the label is hidden. Whether the symptom is gone is a
  question for the running app, and it is the whole of PD-M10.7.
- **Report 1 is explained, not proved.** If a block dragged to another half hour
  still does not move once the panes repaint, the remaining candidate is
  PD-M5.7: a block dropped on the **Earlier** or **Later** box is refused by
  design, with a warning the missing flush would have hidden
  (`test_pdm57_a_block_drag_onto_a_virtual_box_is_refused` pins that refusal).
  That rule is a decision, not this defect, and it is left as it is pending a
  look at the running screen.
- **Adjacent issue found, not fixed:** `drag_schedule.py` has the same
  press-time drag label. `start_drag` is bound to `<ButtonPress-1>`
  (`drag_schedule.py:1340`) and builds, lifts and positions the label straight
  away (`:1344`), so an ordinary click on a row there puts the item's title — or
  "3 items" — beside the pointer exactly as the Plan screen did. It was not
  reported, so it is not touched here. That screen does **not** use the
  remove-rebuild-regrid pattern, so whether its drops repaint promptly is a
  separate question I did not look into.
- The three adjacent issues from the two earlier notes today are unchanged:
  `SLOT_BARS_WIDTH_PX` 2px short of the stack (in `BACKLOG.md`), no logging
  configured so `logger.exception` reaches stderr only, and the `NNm` label's
  `sticky="ne"`.

## Next agent actions

- Move a block from one half hour to another and confirm it appears without
  touching the mouse again. Same for right-click → a different length, and for
  Break/Buffer.
- Click an item row once, without dragging, and confirm no label is left beside
  the pointer.
- Drag a block onto **Earlier**: the expected result today is the refusal
  message. If that is not what you want from the gesture, PD-M5.7 is the rule to
  change.
