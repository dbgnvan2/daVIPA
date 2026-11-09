# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: non-work-day-drop (PD-M13)

## Summary

The user's reports 2 and 3 from the Plan screen — "neither ends allow
scheduling" and "non-workday schedule on YES does not work" — are one fault,
and this is the third remedy for it. The first two were both written against a
correct diagnosis and both failed on the running app.

- PD-M11 read the two reports as the repaint bug. They were not; the writes
  never ran.
- PD-M12 found why: `messagebox.askyesno` raises a bare `_tkinter.TclError`
  when it is called from the `after_idle` callback `on_drag_release` schedules,
  and that question is the first statement of both `block_item` and
  `extend_day_for`. 2026-11-07 is a Saturday, so every gesture the user tried
  was on a non-work day. PD-M12 replaced the platform's dialog with the app's
  own `CTkToplevel` + `grab_set` + `wait_window`. Reported back as "broken - it
  just hangs...": that window cannot become viewable from the same callback, so
  `wait_window` never returns and the grab is held with nothing able to take
  it. The application stopped responding.
- PD-M13, this change: **no modal of any kind on the drop path.** The two drop
  paths call `_require_block_day(ask=False)` — the write goes ahead and the
  status line carries the warning, which is the one place on that screen that
  cannot fail to appear. AutoLoad and the break/buffer button keep the
  question, now wrapped in `try/except tk.TclError` so a dialog that raises can
  never again take the gesture with it. `widgets/confirm_dialog.py` is deleted
  and the conftest guard that went with it is removed.

Two approved acceptance criteria are **withdrawn**, not re-pointed: TB-M8.2
("a drop on an unchecked weekday creates no block") and PD-M5.11 ("extending is
refused on a non-working day"). PD-M7 had already softened both from a refusal
to a question; this removes the question from the drop path. Their two tests
are deleted — they had been passing only because the suite's messagebox stub
answers no. The refusal they covered still exists on the paths that ask.

## Files changed

- `src/getmoredone/screens/plan.py` — `_require_block_day(ask=…)`, the
  `except tk.TclError` fallback, `_take_non_work_note()`, and the note appended
  to all four status lines that can follow a non-work-day write
- `src/getmoredone/widgets/confirm_dialog.py` — deleted
- `conftest.py` — the `_confirm_dialogs_never_block` guard and `confirms`
  fixture removed with the dialog they guarded
- `tests/test_plan_screen.py` — eight PD-M13 tests replace the PD-M12 set; two
  superseded tests deleted
- `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md` — `## PD-M13`;
  PD-M12 marked superseded; the PD-M7 and PD-M5.11 tables re-pointed
- `docs/spec_coverage.md` — PD-M13.1–13.4 rows; PD-M12.1–12.5, TB-M8.2 and
  PD-M5.11 marked superseded; the PD-M7 rows re-pointed
- `docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md` — TB-M8.2 row
- `docs/USER_GUIDE.md` — Days for Blocks now says what a drag does and what a
  button does, which are no longer the same thing
- `CHANGELOG.md` — fourth-pass entry; the third-pass entry marked as reported
  broken
- `BACKLOG.md` — the Scheduler's drag-onto-project entry rewritten (its
  recommended fix named the deleted dialog); the messagebox-stub entry extended
  with what PD-M13 cost

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_plan_screen.py tests/test_tk_offscreen.py tests/test_plan_settings.py -q -p no:randomly`
- Result: PASS — 269 passed, 20 skipped (the skips are the mapped-window tests)
- Command: the PD-M13 mutation gate (scratchpad `mutate_pdm13.py`) — ten shipped
  lines each reverted to their verbatim original, the named test required red at
  exit 1, the file restored and the restore asserted
- Result: PASS — 10/10 red at exit 1. Three of the four note appends exist
  because this gate found them deletable with every other test green.
- Not run: the rest of the suite (CI runs it on push).

## Risks / Known gaps

- **PD-M13.4 is not verified and cannot be.** Nothing in this suite can build a
  visible window, which is exactly how both earlier remedies reached the user.
  The walk is: on a Saturday, drop an item on a half hour; drop one on
  **Earlier**; drop one on **Later**. All three should write a block and leave a
  status line naming the day, and the window should keep responding.
- A drop on a day outside the working week now writes without asking. This is a
  deliberate change to PD-M7's approved behaviour and the user may want a
  non-modal confirmation in its place — a status-line undo, or a banner — which
  would be a new module, not a revision of this one.
- The messagebox stub still cannot raise, and no test can show that a toplevel
  never returns from that callback. Both are recorded in `BACKLOG.md`; neither
  is fixed here.
- No sweep has been run over this change or the sixteen commits before it.

## Next agent actions

- Hand the walk above to the user; do not launch the app from a session.
- If the walk passes, run `/csdp` over the unpushed range — nothing in it has
  been swept.
- Before touching the Scheduler's drag-onto-project confirmation, walk it: it
  calls `messagebox` from inside its own `ButtonRelease` handler and may be a
  live silent no-op of the same class.
