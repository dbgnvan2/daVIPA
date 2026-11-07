# Handoff Note

- Date: 2026-11-07
- Agent: Code
- Topic: ape-week-actions

## Summary

The "APE Weekly" tab is now **APE Week Assignment**, and a sixth tab, **APE
Week Actions**, shows the Action Items under a week's Weekly Tactics. Built
from `docs/spec_2026-11-07_ape_week_actions.md`, approved as written on
2026-11-07, in the order §4 sets out.

**The one decision that mattered.** A child Action Item points at its Weekly
Tactic through one of two columns, and the codebase did not agree which. The
re-filing cascade writes `weekly_tactic_id`; the APE Week Assignment screen's
Add Action Item button writes `parent_id` and leaves `weekly_tactic_id` NULL.
Counted on 2026-11-07 against both real databases: the main one holds 49
children linked the first way and none the second, the demo one 1 the second
way and none the first. A panel reading either column alone is correct on one
machine and shows an empty list on the other.
`vps_manager.get_action_items_for_weekly_tactic` reads the union, and is the
only place that predicate is written.

**The right panel is a `TodayScreen` subclass, not a copy.** Today's
`load_items` and `create_item_row` already worked on any list of `ActionItem`;
three things in that screen were about *today* and were written inline. They
became `_build_toolbar(parent)`, `EMPTY_TEXT` and `COLUMN_PREFIX` — a pure
move, verified by the five existing Today test files before anything depended
on it. The panel overrides those three plus `get_todays_items`, and nothing
else: edit, complete, timer, push and the three inline editors are inherited
unchanged, which is what "work like the Today tab" has to mean to stay true.

**Deliberate divergences from the sibling tab**, both from the spec's §2:

- the left list passes `ape_only=False` (D4), so a tactic whose Annual Plan
  Element has been detached still appears — hiding it would leave its Action
  Items unreachable from this tab with nothing on screen to say so (P2). The
  count is in the panel heading and the status line;
- the panel reads no clock (D6), so a completed child shows whatever day it
  was completed on. "Completed today" has no meaning once the list is filtered
  by tactic.

**Week identity now has one home.** `week_options.py` holds the three helpers
lifted out of `WeeklyItemsScreen`, which is the second-caller move the APE
quarter/month batch made for the same reason: two owners of one rule is how
that defect started. All three are pure — the clock and the settings object
are passed in — so `date.today()` stays resolved in `weekly_items.py` and the
existing week-options tests are untouched and green.

## Files changed

- `src/getmoredone/screens/today.py` — AWA-M6 seam: `_build_toolbar`,
  `EMPTY_TEXT`, `COLUMN_PREFIX`
- `src/getmoredone/screens/week_actions.py` — **new**, 355 lines:
  `WeekTacticActionsPanel` and `WeekActionsScreen`
- `src/getmoredone/week_options.py` — **new**: week identity and the picker's
  options
- `src/getmoredone/screens/weekly_items.py` — header rename; the three helpers
  re-pointed at `week_options`
- `src/getmoredone/vps_manager.py` — `get_action_items_for_weekly_tactic`
- `src/getmoredone/screens/vision_planning_hub.py` — the rename, the sixth
  button, its route, and a subtitle that was a tab short
- `src/getmoredone/app_settings.py` — `week_actions_col_widths`, so the
  panel's Title width persists (`AppSettings` writes declared fields only)
- `src/getmoredone/app.py`, `date_utils.py`, `vps_schema.py` — the rename
  carried through the comments that named the live screen
- `tests/test_ape_week_actions.py` — **new**: 27 tests, AWA-M1 to AWA-M6
- `tests/test_ci_contract.py` — session worktrees are not uncollected test
  files (see Risks)
- `docs/spec_2026-11-07_ape_week_actions.md` — §6 status report, mutation
  table, the on-screen checklist, two criteria corrected, AWA-A4/A5 recorded
- `docs/DOCUMENTATION_INDEX.md`, `docs/USER_GUIDE.md`, `docs/spec_coverage.md`,
  `CHANGELOG.md`, `NOTES.md`, `BACKLOG.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ape_week_actions.py -q`
- Result: PASS — 27 passed

- Command: the five Today files plus `test_weekly_items_week_options.py`,
  `test_weekly_tactic_schema.py`, `test_weekly_tactic_dedupe.py`
- Result: PASS — AWA-M6.3; the one skip is the mapped-window geometry test,
  skipped by the env var

- Command: `tests/test_ci_contract.py`, `tests/test_no_vacuous_tests.py`,
  `tests/test_traceability_refs.py`
- Result: PASS

- Command: the mutation gate — 28 mutations, each the verbatim original line,
  each run alone, each file restored and sha256-compared
- Result: PASS — 28 red, 28 byte-identical restores. Two needed a second pass;
  one of those was a vacuous test, rewritten. Both are in the spec's §6.

- Command: the app itself, on the new tab
- Result: **NOT RUN.** The user asked not to have their screen taken over
  mid-session. The nine-step checklist at the end of the spec's §6 is what
  needs doing at the keyboard, and the "works like the Today tab" criterion
  stays `not done` until then.

## Risks / Known gaps

- **The on-screen check has not happened.** Everything above is tests plus one
  pure refactor verified by an existing suite. The layout question §5 raised —
  Today's columns were laid out for a full-width screen and this panel gets
  half a pane — is exactly what no test here settles.
- **AWA-A4: the inherited pin is shared.** Dragging a row to the top of this
  panel writes `today_pin_rank` and so also floats it to the top of Today,
  because the grip comes with the inherited row builder. Recorded, not fixed:
  either fix is a behaviour change beyond what was asked.
- **AWA-A1 is still open and is now user-visible.** The APE Week Assignment
  screen's Add Action Item button still writes `parent_id`; this tab's writes
  `weekly_tactic_id`. Both are read, so nothing is lost, but the two buttons
  disagree. The spec recommends fixing it; it was not in what was asked.
- **`tests/test_ci_contract.py` was fixed, not just recorded.** Its
  uncollected-files assertion globbed the desktop app's per-session git
  worktrees under `.claude/worktrees/`, each a full checkout with its own
  `tests/`, and went red against 115 files not in this working tree. It made
  the meta suite unusable, so it was fixed here with its predicate under test.
  Not caused by this feature.
- **This batch is interleaved on `main` with the Plan / Day Plan batch**, which
  was committed from a second session into this same checkout rather than into
  its own worktree. The ranges overlap; `git log --oneline` tells them apart by
  scope (`feat(vps)`/`AWA` here, `fix(plan)`/`PD-` there).
- CI on `main` was already red on eight pre-existing Tk window-manager
  assertions before this batch. Nothing here adds to that count.

## Next agent actions

- Run the nine-step checklist in the spec's §6 and record what the window
  showed, criterion by criterion, the way the APE period-consistency batch was
  recorded on 2026-11-07.
- Decide AWA-A1 (make both Add buttons write `weekly_tactic_id`) and AWA-A4
  (the shared pin). Both are one-line-plus-a-test changes and both are the
  user's call.
