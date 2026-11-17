# Handoff Note

- Date: 2026-11-16
- Topic: modeless-notices-phase1 (MOD-M1 to M4, and the MOD-M7 walk)

## Summary

Every "telling" platform dialog in the app is gone. All 89 `messagebox.show*`
calls across 25 screen modules now report on a per-screen notice line. The two
that remain are the pair the plan allowlisted, in `app.py`: `main`, where no
window exists yet, and `show_settings`, whose handler reports the failure of
the very screen that would have carried the notice.

`src/getmoredone/screens/status_notice.py` is the new module. It holds the
contract `plan.py` and `drag_schedule.py` already satisfied — `set_status(text,
kind)` writing through `theme.status_text_color(kind)` — plus
`create_status_line`, `notify_owner` (for the ~30 dialogs that report and then
close, which cannot report on a label they are about to destroy),
`report_on(widget, text, kind)` (the same walk as a free function, for the
week-collision notices, which are module functions given a `parent` rather
than screens), and `inline_list(names, cap=3)` (for the two APE refusals that
used to list their blockers down a dialog body).

`AppSettings.notice_dismiss_ms` (6000) is how long an `info` or `success`
notice stays. An `error` or `warning` one is not timed; nor is an unknown kind,
because a notice nobody sees is the failure this change exists to fix.

Phase 2 — MOD-M5 (the asking sites) and MOD-M6 (the 49 `grab_set` calls) — is
**not started**, and is sequential after this is pushed.

## Why a label and not a toast

The archived sweep's floating toast (`archive/no-focus-stealing-dialogs`,
`f1675f5`) was **not** adopted. `main` had already answered the question: the
reason is recorded at `plan.py:2446`. On macOS the platform dialog raises a
bare `TclError` from the idle callback a drag release schedules, and a
hand-rolled grabbed toplevel in its place hung the application outright,
because its window could not become visible while its own grab was up. Both
faults were reported from the running screen on 2026-11-07, three hours apart.
A label already on the screen cannot fail either way.

## Files changed

New:
- `src/getmoredone/screens/status_notice.py`
- `tests/test_modeless_notices.py` (30 guards)

`src/` swept (telling sites moved): `annual_vision_segments.py`,
`ape_assignment.py`, `ape_period_view.py`, `drag_schedule.py`,
`edit_contact.py`, `item_editor.py`, `item_editor_project_dialog.py`,
`project_boards.py`, `settings_integrations.py`, `settings_vsp_segments.py`,
`timer_window.py`, `timer_window_dialogs.py`, `timer_window_reward.py`,
`vision_elements.py`, `vision_segments.py`, `vps_editors.py`,
`vps_planning.py`, `vps_segment_editor.py`, `week_actions.py`,
`week_collision_notice.py`, `weekly_items.py`.

`src/` given a notice line with no telling site of its own (see "Scope the plan
did not have" below): `all_items.py`, `completed.py`, `hierarchical.py`,
`today.py`, `upcoming.py`.

Also: `app_settings.py` (`notice_dismiss_ms`), `docs/ui_color_inventory.md`
(regenerated).

Tests repointed from the dialog channel to the notice channel (11 guards in 9
files): `test_item_editor_project_link.py`, `test_project_multi_link.py`,
`test_reward_protocol_timer.py`, `test_source_asserts.py`,
`test_timer_session_endings.py`, `test_tk_offscreen.py`,
`test_unified_panel_design.py`, `test_vps_ape_deletion_ui.py`,
`test_vps_fixes.py`, `test_vps_segments.py`,
`test_weekly_tactic_surfaces.py`.

## Scope the plan did not have, and why it was taken

Three things were outside the plan as approved. Each is recorded here rather
than left for someone to find in the diff.

1. **Five list screens gained a notice line with no telling site of their
   own** — Today, Upcoming, Completed, Hierarchical, All Items. Two of the 89
   telling sites are in `week_collision_notice.py`, and those two are reached
   from 40 call sites across 13 screens. Five of those screens had no notice
   line, so a refused week or a cascade's new records would have been logged
   and shown to nobody — quieter than the dialog it replaced, which is the one
   way this change could make the app worse. MOD-M1's own wording is "the
   other screens gain it", so this is that criterion rather than new work.

2. **`project_boards.set_status(board_id, status)` was renamed to
   `set_board_status`.** The plan flagged the collision as adjacent and said
   the rename was not in scope, on the assumption the class could be left
   without the mixin. It could not: `ProjectBoardsScreen` has twelve telling
   sites of its own. Three callers, all in that file, none in tests.

3. **`TimerWindow._show_error_dialog` was renamed to `_report_error.`** It
   opens no dialog any longer, and a method named for the thing it stopped
   doing is drift this change would have created. Five references: one in
   `timer_window_reward.py`, four in `timer_window.py`, and three test stubs.

## The review round, and what it changed

Two passes ran over `f513b98...HEAD` before the push: `learning-qa` (the
failure-pattern family) and `/code-review` at high effort (correctness). They
converged independently on four findings, which is the only strong signal
either of them gives (P26). `/security-review` was **skipped**: the gate was
decided by grep over the sweep diff, not by judgement, and the one hit was the
plan's own sentence saying the pass does not apply.

Nine findings, all confirmed by reading the code, all fixed here. Each fix has
one guard, and every guard was mutation-checked: the `src/` line it names
replaced with its pre-fix state, that guard run, red confirmed, the file
restored byte-identical.

**Two were the one failure this change could introduce — a notice with nowhere
to go.** Both were screens the sweep reached around rather than through:

1. `week_actions.py:184` — `WeekTacticActionsPanel` reported a refusal with
   `notify_owner`, which walks up from `self.master`. `WeekActionsScreen` has a
   `status_label` but no `set_status`, so `report_on` correctly skipped it and
   nothing above had a line: the refusal went to the log only. The panel had a
   line of its own all along, inherited from `TodayScreen` at row 4 — the same
   one `notify_weekly_tactic_changes` three lines below already used. Two
   comments added in the same commit contradicted each other.
2. `manage_contacts.py` — `EditContactDialog` has two openers. One had a line
   and one did not, so Add, Update, Delete, Deactivate and "That contact no
   longer exists." were shown to nobody whenever contacts were managed from the
   Contacts tab, which is the sidebar screen. The generic P5 shape: the dialog
   was swept, one of its two openers was not. It has a line at row 2 now.

The rest:

3. `week_collision_notice.py` sent the year-rollover notice as `info`, which is
   transient. `cascade_needs_attention` admits exactly two conditions and both
   need the user, so there was never a transient case to have; the text ends
   "need your words" and the function's own docstring says nothing else will
   ever ask. Both arms are `warning` now and the conditional is gone.
4. **MOD-M3's auto-clear was wrong for three notices that already existed.**
   `set_status` takes `persist=True`, and three Plan-screen sites use it:
   `plan_week_view.py` when a caveat tail was appended ("export that day again
   to remove it from Google Calendar" is an instruction, and without it a stale
   Google Calendar event survives), `plan.py`'s Clear Day summary ("removed 4
   of 6 blocks", under a comment citing P2 for carrying both numbers), and the
   export summary, which was the only branch of its own `if/elif/else` that
   vanished while the nothing-happened branch persisted. This corrects the
   claim under "Risks" below: that MOD-M3 reaching those 21 sites was
   "deliberate and worth seeing on screen". It was not examined against what
   those messages say, and three of them carry required action or evidence.
5. `report_on` returned True as soon as it called a setter, but `set_status`
   swallows a failed `configure` on purpose (MOD-M4). A half-torn-down ancestor
   therefore took the notice as far as every caller could tell. `set_status`
   returns a bool now, `report_on` returns that bool and keeps walking, and the
   one drop path that logged at DEBUG logs at WARNING like the other five.
6. `_schedule_dismiss` used raw `self.after` with nothing cancelling it on
   destroy — the exact leak `utils/after_tracker.py` was written for (P30).
   `TrackedAfterMixin` does not cover it, because it does not override `after`.
   A success notice followed by a sidebar click inside six seconds fired
   `clear_status` on a destroyed widget and wrote an ERROR traceback to
   `app.log` for ordinary navigation — noise in the one file step 1 of the walk
   below asks you to read. The mixin has a `destroy` override now, and
   `clear_status` checks `winfo_exists` before it writes.
7. Four screens — `weekly_items`, `ape_assignment`, `ape_period_view`,
   `annual_vision_segments` — were given the mixin over a `status_label` that
   already carried their own standing content, leaving two writers with
   different colour contracts: `set_status` sets `text_color` and a raw
   `configure(text=...)` does not reset it, so a neutral count summary written
   after an error notice rendered in the error colour and stayed there. All 17
   direct writes go through `set_status` now, and the four problem branches on
   the two APE screens got the kind they always needed.
8. `self.destroy()` sat inside the `try` whose `except` now reports on the
   dialog's own label, in six places. A TclError out of teardown after a
   successful save reported "Could not save ..." onto a widget on its way out:
   a false failure, and an invisible one. `messagebox.showerror` did not need
   the dialog to still exist; a label on the dialog does.
9. **The guard the first 30 did not make.** Nothing asserted that a class
   calling `self.set_status` has a label to draw on, which is why findings 1
   and 2 passed a green suite — the MOD-M2 exact-set guard cannot see them,
   because the dialog really is gone and only the message goes nowhere. It is
   statically decidable, and it is asserted now, in two arms: every class that
   calls `self.set_status` resolves to a notice line, and every class that
   opens a dialog reporting through `notify_owner` has one for it to walk up
   to. A mixin counts as satisfied when every class that mixes it in has a
   line, which is how `PlanWeekViewMixin` and `ItemEditorContactsMixin` are
   handled.

One `learning-qa` finding is **not fixed and not dismissed**: it reported, as
unverified, that the notice line on the seven fixed-geometry VPS dialogs is
appended as a new last grid row and may be clipped below the window edge, in
which case `set_status` succeeds, `winfo_exists()` is True, every guard passes
and the user still sees nothing. It needs a mapped window to settle, so it is
step 11 of the walk below and `BACKLOG.md` MOD-A3.

## Verification

- `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python
  -m pytest tests/test_modeless_notices.py -q` → **43 passed** (30 for the
  sweep, 13 for the review round above). Includes
  `test_modm2_no_screen_tells_the_user_through_the_platform`, the exact-set AST
  assertion over `src/**/*.py` keyed by enclosing function name, which is the
  phase's own completion check and could not pass until the sweep finished.
- ~50 further targeted test files run in batches across the touched screens:
  all green **except** the pre-existing failure below.
- Every one of the 11 repointed guards was mutation-checked: the `src/` line
  the guard names deleted, that test run, confirmed red, and the file restored
  with the verbatim original. Two were **vacuous on the first rewrite** and the
  mutation pass is what caught them — `test_updm54` (the weekly-items notice
  line already carried a muted load summary containing "weekly tactic", so a
  substring check passed with the refusal deleted; it asserts the warning
  colour now) and `test_the_helpers_parse_a_real_method_from_the_app` (the
  sample method has four `set_status` calls, so deleting one proved nothing).
- All 62 screen modules import cleanly; no MRO conflict; no subclass overrides
  `set_status`.
- Not run: the full suite (CI's job; a local full run is not acceptable on this
  machine). The program was **not launched** — see MOD-M7 below.

### Pre-existing failure, not caused by this batch and not fixed here

`tests/test_tk_offscreen.py::test_every_test_that_needs_a_mapped_window_asks_for_one`
fails because `tests/test_scheduler_column_resize.py` calls
`event_generate("<Configure>")` and no test in that file requests the
`mapped_windows` fixture. It arrived with commit `e35fc1d` (the LRP batch) and
is already on `main`. Filed in `BACKLOG.md`: the fix is a real decision —
request the fixture and change the mapped-window count asserted in
`test_ci_contract.py`, or call the bound handler directly and lose the proof
that the binding exists — not a two-line edit, so it is not folded in here.

## Risks / Known gaps

- **Two `notify_weekly_tactic_changes` call sites deliberately pass no
  parent** (`timer_window.py:1181` and the one inside the
  window-already-destroyed branch). They used to show a dialog parented to the
  root, which needed no window; they now have nowhere to draw, so the notice is
  logged at WARNING and shown to nobody. `timer_window.py:1569` was the third
  and now passes `self`, because there the window is alive.
- **`notify_week_collision` and `notify_cascade` changed meaning.** They
  returned `True` whenever they showed a modal; they now return whether a
  notice line took the message. No caller in `src/` reads the value, and the
  one test that did now asserts through the notice channel.
- **`success` and `info` notices on `plan.py` and `drag_schedule.py` now clear
  themselves** after `notice_dismiss_ms`. Those two screens had 21 existing
  `set_status` calls and MOD-M1 was meant to be inert for them; this is MOD-M3
  applying to them too. This note first called that "deliberate and worth
  seeing on screen", which was a judgement made without reading what those
  messages say: three of them carry an instruction or the "N of M" evidence the
  house rules require to be surfaced, and they take `persist=True` now
  (finding 4 above). The other 18 still clear, which is the intent.
- **The plan said the colour inventory would not need regenerating.** It did:
  `docs/ui_color_inventory.md` records line numbers, not only literals, and the
  sweep moved lines in the files it touched. No new colour literal was added —
  every notice colour comes from `status_text_color`.
- Still pre-existing, still not fixed: `status_text_color` returns an unknown
  `kind` unchanged, so a typo becomes a Tk colour error at draw time rather
  than a caught mistake.
- **The notice line's placement on the seven fixed-geometry VPS dialogs is not
  verified.** It is appended as a new last grid row in Toplevels of a declared
  size whose content already nearly fills them. If a row is clipped,
  `set_status` succeeds and every guard passes while the user sees nothing —
  the one state no assertion on `cget("text")` can detect. Step 11 of the walk,
  and `BACKLOG.md` MOD-A3.

## MOD-M7 — the on-screen walk, for the user to run

Not code-testable; the program is never launched from a session here. Fourteen
steps, one per thing that could have broken.

1. **Launch.** Quit `/Applications/daVIPA.app` first — a source launch exits
   silently while the packaged app holds the database lock. Then
   `./start.sh`. Check `app.log` for `notice dropped` and for `no notice line
   above` — either one names a screen that reports with nowhere to report,
   and there should be none.
2. **An error that must persist.** Settings → VSP Segments → add a segment
   with a blank name and Save. Expect a red message on the section's own
   status line, and expect it to **stay** there (it is an `error`). No OS
   dialog.
3. **A success that clears itself.** Plan screen → drag an item to another
   day. Expect a green or blue line confirming the move, and expect it to
   **disappear** after about six seconds. This is the one deliberate change to
   a screen that already had a notice line.
4. **The drag-release path that started all this.** On the Plan screen, drop an
   item somewhere that is refused (a week already taken by a tactic for the
   same Annual Plan Element). Expect an amber line that stays, and expect the
   drag gesture to complete normally — no frozen window, no traceback in
   `app.log`.
5. **A refused week from a screen that had no line before.** Today → change an
   item's date to a week already holding a tactic for the same Annual Plan
   Element. Expect the refusal on a line at the foot of the Today list. Repeat
   on Upcoming and All Items; the line is at the foot of each.
6. **A dialog that reports and then closes.** Projects → open a project → link
   action items, and make the link fail (pick a tactic rather than an action
   item). Expect the message on the **Projects screen** behind the dialog, not
   on the dialog that just closed.
7. **A long refusal.** VSP → Annual Plan Elements → delete an element that has
   more than three blockers. Expect one line naming three of them and "and N
   more" — not a scrolling dialog body.
8. **The timer.** Start a timer, then force one of its endings to fail (the
   simplest is to pop out the notes window, then close the timer and save
   notes). Expect the message at the foot of the timer window, and expect the
   window's own "Ready to start" / countdown status to be **untouched** — they
   are two different labels now.
9. **The pop-out notes window.** With the timer open, Pop Out, edit notes, and
   save with the timer closed underneath. Expect the message inside the
   pop-out, not a dialog behind it.
10. **A question is still a question.** Complete a Weekly Tactic that has open
    children. Expect a real modal asking whether to complete it anyway, in
    front of whatever it belongs to. Phase 1 changed nothing about asking;
    this step is here to confirm it.
11. **The one thing no test here can see.** Open VSP → edit a Vision, an
    Annual Plan, an Annual Initiative and a Week Action, and in each save with
    a blank required field. The notice is the last grid row of a dialog with a
    declared size, so the question is whether it is **on screen at all** — not
    whether it says the right thing. If any of the four shows no message where
    the others do, that dialog's row is clipped and its geometry needs the
    extra height. Same for Settings → VSP Segments → the segment editor.
12. **The Contacts tab, which the review found reporting to nobody.** Sidebar
    → Contacts → New Contact, save it. Expect the confirmation on a line under
    the Contacts header, not in a dialog and not nowhere. Then Edit one,
    Delete one, and accept the offer to deactivate when a delete is refused.
13. **The APE Week Actions panel, the review's other one.** VSP → APE Week
    Actions, select no tactic on the left, click Add Action Item. Expect an
    amber refusal at the foot of the right-hand panel.
14. **A notice does not outlive its screen.** On the Plan screen make a
    `success` notice appear (step 3), then click another sidebar entry within
    six seconds. Expect no traceback in `app.log` — that was finding 6.

## Next agent actions

- Run the walk above and report any step that does not match.
- **Phase 2 (MOD-M5, MOD-M6) only after this is pushed and walked.** Its plan
  is `docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md`.
  `BACKLOG.md`'s MOD-A1 leaves when phase 2 lands, not before.
