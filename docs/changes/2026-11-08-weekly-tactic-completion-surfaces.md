# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: weekly-tactic-completion-surfaces (WTP-M6.7)

## Summary

The WTP batch was pushed (`3f705b4..56c1dc0`, 42 commits) and then reviewed by
the external Hermes `learning-qa-sweep` gate, which **rejected** it on one
medium finding.

**F1, medium, P25.** WTP-M6.1 — "completing a Weekly Tactic with open children
asks first" — existed only inside `ItemEditorDialog._confirm_tactic_completion`.
`DatabaseManager.complete_action_item` is called from seven places, and the
other six asked nothing: the Today checkbox, All Items, Upcoming, the
Hierarchical tree, a Project Board, and the timer's Done button (twice). All of
those list week rows. So the guard covered the one surface a user is least
likely to complete a tactic from, and WTP-M6.1 to WTP-M6.3 had been reported
`done` on the strength of it.

The fix puts the question in one place and calls it from all seven:

- `week_collision_notice.confirm_weekly_tactic_completion(db_manager, item_id,
  parent)` is the single implementation. That module was already the home of
  the shared week notices *and* of `_parent_not_on_top`, the always-on-top
  wrapper these modals need over the TimerWindow, so the question went beside
  them instead of into a new module.
- `ItemEditorDialog._confirm_tactic_completion` is now a one-line delegation to
  it. The method name stays so the call in `complete_item` still reads as the
  editor asking, and so the two existing tests keep their subject.
- The timer asks **once**, early in `finished_action` — before the completion
  note dialog and before the Next Action window is destroyed — so declining
  costs the user neither a typed note nor a window. Both of its
  `complete_action_item` calls are downstream of that one point.

Recorded as **WTP-M6.7** in
`docs/spec_2026-11-08_weekly_tactic_as_parent.md`, with WTP-M6.1's status row
corrected to say it was first built on one surface only.

The gate's second finding (F2, low — Calendar Export hunks inside a
`feat(wtp)` commit) is filed, not fixed.

**WTP-M6.8 — the same question, through the real widgets.** Everything above is
verified by driving each screen's `complete_item` unbound against a
`SimpleNamespace`, which proves the guard is *in* the method and nothing about
the control that reaches it. `tests/test_weekly_tactic_completion_widgets.py`
builds the real screens instead: it finds the widget the screen itself created
— by reading the item id out of that widget's own callback rather than by
matching the row's rendered text — and presses it with the widget's own
`toggle()` / `invoke()`. 21 tests, 13 mutations, all killed.

**WTP-A8, found by doing that.** Looking for the widget behind each guarded
method turned up one that has none: `HierarchicalScreen.complete_item` has no
caller anywhere in `src/` — no `command=`, no string reference, no `getattr`.
Its rows are labels only. The guard on it is therefore harmless but
unreachable, and three documents were claiming otherwise (this note's checklist
step 4 among them). The spec, the user guide and this note are corrected, and
the dead method is filed as WTP-A8 rather than fixed: whether that screen should
grow a Complete control or lose the method is a product decision, not a
cleanup.

## Files changed

Source:
- `src/getmoredone/screens/week_collision_notice.py` — the guard; module
  docstring widened from "notices" to the shared moments of a Weekly Tactic
- `src/getmoredone/screens/item_editor.py` — delegation (22 lines → 4)
- `src/getmoredone/screens/today.py`
- `src/getmoredone/screens/all_items.py`
- `src/getmoredone/screens/upcoming.py`
- `src/getmoredone/screens/hierarchical.py`
- `src/getmoredone/screens/project_boards.py`
- `src/getmoredone/screens/timer_window.py`

Tests:
- `tests/test_weekly_tactic_completion_surfaces.py` — new, 31 tests
- `tests/test_weekly_tactic_completion_widgets.py` — new, 21 tests (WTP-M6.8)

Docs:
- `docs/spec_2026-11-08_weekly_tactic_as_parent.md` — WTP-M6.7, summary, status
- `docs/cycles/2026-11-08_wtp-plc-upd-pd-qa-gate.md` — the gate's own report
- `docs/USER_GUIDE.md` — the Complete bullet now says the question is asked
  wherever a tactic is completed
- `BACKLOG.md` — WTP-A2, WTP-A3, WTP-A4; then WTP-A5, A6, A7 from the re-gate;
  then WTP-A8
- this note

## Verification

- Command: `pytest tests/test_weekly_tactic_completion_surfaces.py tests/test_weekly_tactic_parent.py -q`
- Result: PASS — 72 passed (31 new + 41 existing)

- Command: the twelve touched-area files (editor/boards/timer/today/upcoming/weekly-tactic)
- Result: PASS — 275 passed

- Command: `pytest tests/test_ci_contract.py -q`
- Result: PASS — 82 passed, 1 skipped; the mapped-window count is still 22

- Command: mutation gate, 14 mutations (scratchpad `mutate3.py`)
- Result: PASS — all 14 killed, every file restored byte for byte

Two of the fourteen are worth naming. `test_wtpm67_the_set_of_completion_call_sites_is_pinned`
is killed by *adding* a call site (`completed.py`'s `uncomplete_action_item`
changed to `complete_action_item`), which is the direction that matters: the
bug being fixed was a guard covering one of seven sites, and a `> N` floor
would have passed that state. And the first run of the gate **failed** on the
open-child filter: `test_wtpm67_a_tactic_whose_children_are_done_is_not_questioned`
stayed green without it, because driving `complete_action_item` re-files a
completed child onto another week's tactic (WTP-M6.6), so `get_children`
returned nothing and the filter was never reached. The test now seeds the
completed status straight onto the rows (P8) and asserts the seed left them
under the tactic, which is the state the line is actually for.

### WTP-M6.8, the widget layer

- Command: `pytest tests/test_weekly_tactic_completion_widgets.py -q`
- Result: PASS — 21 passed

- Command: mutation gate, 13 mutations (scratchpad `mutate_widgets.py`)
- Result: PASS — all 13 killed, every file restored verbatim

The mutation gate was worth running twice here. Its first run left a survivor:
the mutation that counts *completed* children as open, because the test it was
aimed at used a tactic with no children at all, so the status filter was never
reached. The test now seeds two completed children by SQL and asserts the seed
left them under the tactic — the same trap, and the same fix, as in the stub
file. And one test *hung* rather than failing under the "timer: no guard"
mutation: with the guard gone, `finished_action` walked into the note dialog
and blocked in `wait_window` with nobody to dismiss it. Both timer tests now
arm the dismisser, including the one that expects no dialog, so a removed guard
goes red instead of hanging. A test that hangs is not a test that can fail.

A third thing the gate taught, about itself: the first run was killed with
SIGTERM between a mutation and its restore and left the timer's guard deleted
in the working tree. `try/finally` does not cover a signal. The script now
installs a SIGTERM/SIGINT/SIGHUP handler and an `atexit` hook that restore
every mutated file, and asserts the restore at the end.

## Risks / Known gaps

- **Nobody has opened the app.** No test maps a window: every screen here is
  built withdrawn, as conftest requires. What the widget tests add is that the
  real widget tree is built and the real control is pressed, so an unwired
  control or a screen that cannot construct now fails a test rather than
  waiting for someone to look. What they still cannot see is anything only
  visible on screen — layout, colour, whether the modal is legible. The
  on-screen checklist below is not done.
- **`HierarchicalScreen.complete_item` is unreachable** (WTP-A8). Filed, not
  fixed. Its guard is correct and dead.
- **`docs/DOCUMENTATION_INDEX.md` has no entry** for this note or the gate
  file. That file carries another session's uncommitted work, and `CLAUDE.md`
  says to add shared-doc entries after the merge. Nothing enforces the index in
  this repo (no test, and the docs gate runs on `pull_request` only, which this
  project never opens), so it is a real gap rather than a blocked one.
- **`item_editor.py` keeps a function-local import** of the shared guard rather
  than adding to its module-level import list: that line sits inside another
  session's uncommitted hunk, and editing it would have put two changes in one
  hunk. Worth tidying when that session has landed.

## On-screen checklist

Not run. Each step needs the packaged app closed first — a source launch exits
silently while `/Applications/daVIPA.app` holds the database.

1. Today: tick the checkbox on a Weekly Tactic row (the "WT" badge) that has
   open items under it. Expect the question, naming the count.
2. Say No. The row must still be open, and nothing else should change.
3. Say Yes. The tactic completes; its items stay open.
4. ~~Hierarchical: complete a tactic from the tree.~~ **Not possible** — that
   screen's rows have no Complete control (WTP-A8). Nothing to check.
5. All Items and Upcoming: same, once each.
6. A Project Board holding a tactic: same.
7. Timer: open a tactic in the timer and press Done. The question must come up
   **before** the "next step note" dialog, and declining must leave the timer
   window open with its Next Action window intact.
8. Complete a plain Action Item from Today. No question at all.
9. Complete a tactic whose items are all done. No question.
10. Check `app.log` for a `bad window path name` or a Tk traceback after each
    modal — the always-on-top wrapper is exercised on the timer path only.

Steps 1-3, 5, 6 and 8-9 now have a widget test behind them, which is not the
same as having been seen: the test presses the control and reads the row back,
and says nothing about what the screen looks like.

Step 7 is **barely** tested, and two gate passes caught two overclaims here.
What the decline test really pins is narrow: declining writes no work log and
completes nothing. That is not the *ordering*. A guard moved to after the note
dialog would still write no log on a decline, so it would still pass -- what
that reordering costs the user is a note typed for nothing, and no test sees
it. The question coming up before the note dialog is checklist-only. The
*Next Action window staying intact* is untested too. Both timer tests drive
`finished_action()` with `next_action_window` already `None`, so the branch that
destroys it is never entered; what they assert is that the TimerWindow itself
survives. Covering the real thing needs a Next Action window open first, which
is on the checklist and not in a test.

Step 10 is tested for the `-topmost` restore specifically, against a real
Toplevel parent — not for whether the modal is legible in front of it.

## Next agent actions

- Walk the nine remaining steps above and record the result in this note.
- Decide WTP-A8: give the Hierarchical row a Complete control, or delete the
  method. If the control is added, it must also go into the widget tests'
  `BUILDERS` and `SCREENS_WITH_A_CONTROL`, which fail until it does.
- Cover the Next Action window on the timer's decline path: open one, decline,
  assert it is still there. The guard is placed before its destroy precisely
  for that, and nothing checks it.
