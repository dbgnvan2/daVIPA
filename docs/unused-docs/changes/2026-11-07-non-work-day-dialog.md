# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: PD-M12 — the non-work-day question is asked by the app, not by the platform

## Summary

Two of PD-M11's four reports were still broken on the running screen after that
batch shipped: "Neither ends allow scheduling" and "Non-workday schedule on YES
does NOT work". The user sent the traceback, which named the fault:

```
  File ".../screens/plan.py", line 1235, in block_item
    if not self._require_block_day():
  File ".../screens/plan.py", line 1595, in _require_block_day
    if messagebox.askyesno(
_tkinter.TclError
```

`messagebox.askyesno` raises a `TclError` with no message when it is called
from the `after_idle` callback `on_drag_release` schedules — macOS will not run
its native dialog from there. Asking whether the day is a work day is the first
statement of both `block_item` and `extend_day_for`, so the exception left the
Tk callback before either wrote anything: an item dropped on a half hour of a
non-work day did nothing (report 3), and an item dropped on **Earlier** or
**Later** of a non-work day did nothing (report 2). 2026-11-07 is a Saturday,
which is why every gesture the user tried was on a non-work day, and why one
fault looked like two.

PD-M11's own fixes were not wrong — reports 1 and 4 are confirmed fixed on the
screen — but its reading of reports 2 and 3 was. It reasoned from two passing
tests that the writes were happening and only the repaint was missing. That
paragraph in the plan doc now carries the correction.

What changed:

- `widgets/confirm_dialog.py` (new) — `ask_yes_no`, a plain Tk toplevel with a
  grab and `wait_window`. Tcl's modality, not AppKit's. It takes its button
  words, so the yes button says *Schedule anyway*. It raises `ConfirmNotShown`
  rather than blocking if its window never becomes visible, which is the one
  outcome worse than the failure it replaces.
- `_require_block_day` asks through that module, and a dialog that raises no
  longer eats the gesture: the work is scheduled, the reason is logged, and the
  status line says the question could not be shown — once, for the gesture it
  happened to, not for every later one on that day.
- `conftest.py` gains the guard the messagebox stub already had. Without it
  every question in the suite would wait out the dialog's four-second
  visibility timeout, because conftest withdraws every window. It patches both
  `src.getmoredone...` and `getmoredone...` spellings: this suite has both on
  `sys.path` and they are two distinct module objects.

## Files changed

- `src/getmoredone/widgets/confirm_dialog.py` (new)
- `src/getmoredone/screens/plan.py`
- `conftest.py`
- `tests/test_plan_screen.py`
- `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md`
- `docs/spec_coverage.md`
- `docs/USER_GUIDE.md`
- `CHANGELOG.md`
- `BACKLOG.md`
- `docs/unused-docs/changes/2026-11-07-non-work-day-dialog.md` (this note)

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 ... pytest tests/test_plan_screen.py tests/test_tk_offscreen.py tests/test_plan_settings.py -q -p no:randomly`
- Result: **PASS** — 274 passed, 20 skipped in 83.8s. The skips are the
  on-screen geometry tests the environment variable turns off.

- Command: the batch's mutation gate (`scratchpad/mutate_pdm12.py`) — eleven
  mutations, each reverting one shipped line to its verbatim original and
  requiring the test that names it to fail at exit 1.
- Result: **PASS** — 11/11 red at exit 1, file restored and the restore checked
  after each one.

The gate found one line nothing could fail on: the note appended to
`extend_day_for`'s status line could be deleted with every test still green,
because the two write paths compose their own text. That is what
`test_pdm122_the_end_of_the_day_says_it_too` exists for.

## Risks / Known gaps

- **`widgets/confirm_dialog.py` has no direct test.** It builds a toplevel and
  waits on it; every window in this suite is withdrawn, so nothing here can
  exercise it. What is tested is the Plan screen's use of it, the fallback when
  it raises, and the suite's guard over it. Whether the dialog appears and its
  buttons answer is PD-M12.5, a walk.
- **PD-M12.5 is the whole on-screen check**, and this batch has had none: the
  dialog on a Saturday drop, *Schedule anyway* writing the block, and a drop on
  **Earlier** and on **Later** lengthening the day. If the new dialog fails too,
  the fallback means the drop still works and the status line says why — so the
  gesture cannot be silent again either way.
- **No sweep has run over this batch**, warm or cold, and thirteen commits are
  unpushed on `main` across several sessions.
- Two adjacent issues recorded in `BACKLOG.md`, neither fixed: the Scheduler's
  drag onto a project asks through `messagebox` from inside its own release
  handler, which is the same class and may be live; and the session-wide
  messagebox stub cannot raise, which is why no test could see this fault.

## Next agent actions

- Ask for the walk in PD-M12.5 before anything else is built on this.
- Then the Scheduler drag-onto-project walk, which is the one adjacent issue
  that may be a live silent no-op.
- `/csdp` over the unpushed range, or at least a cold pass over this batch:
  every fix in it was written in the same context that got reports 2 and 3
  wrong the first time.
