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
`weekly_tactic.LINK_PREDICATE_SQL` is the union, read by
`vps_manager.get_action_items_for_weekly_tactic` and by
`weekly_tactic_maintenance._child_count`.

That last sentence originally read "and is the only place that predicate is
written", about the helper. The pre-push sweep found it false: `_child_count`
already held a second copy, without the `item_type != 'week'` exclusion, and
the guard test could not see it because it scanned `screens/` and
`vps_manager.py` only. `_child_count` feeds the dedupe that *deletes* a
duplicate tactic, so the drift decided which row was kept. The batch had
recorded the duplication as AWA-A3, a Low refactor; the sweep rated the same
code high, and was right to.

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
- `src/getmoredone/weekly_tactic.py` — `LINK_PREDICATE_SQL`, beside `tactic_of`
  (sweep fix)
- `src/getmoredone/weekly_tactic_maintenance.py` — `_child_count` reads the
  shared predicate (sweep fix)
- `src/getmoredone/screens/vision_planning_hub.py` — the rename, the sixth
  button, its route, and a subtitle that was a tab short
- `src/getmoredone/app_settings.py` — `week_actions_col_widths`, so the
  panel's Title width persists (`AppSettings` writes declared fields only)
- `src/getmoredone/app.py`, `date_utils.py`, `vps_schema.py` — the rename
  carried through the comments that named the live screen
- `tests/test_ape_week_actions.py` — **new**: 31 tests, AWA-M1 to AWA-M6
  (27 in the batch, 4 from the sweep)
- `tests/test_weekly_tactic_dedupe.py` — one test: the dedupe counts children
  by the shared predicate (sweep fix)
- `tests/test_ci_contract.py` — session worktrees are not uncollected test
  files (see Risks)
- `docs/spec_2026-11-07_ape_week_actions.md` — §6 status report, mutation
  table, the on-screen checklist, two criteria corrected, AWA-A4/A5 recorded
- `docs/DOCUMENTATION_INDEX.md`, `docs/USER_GUIDE.md`, `docs/spec_coverage.md`,
  `CHANGELOG.md`, `NOTES.md`, `BACKLOG.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest tests/test_ape_week_actions.py -q`
- Result: PASS — 31 passed

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

- Command: the pre-push sweep — three passes over the AWA range, per the
  project's budget: `learning-qa` (failure patterns), a cold correctness pass,
  and a cold test-quality + security pass
- Result: one high, six medium, ten low. The high and five mediums are fixed
  with tests (`8a324cb` src, `ac22a78` tests); one medium is dismissed as a
  false positive with its reason written in `ac22a78`; the lows are AWA-S1 to
  AWA-S4 in `BACKLOG.md`. The security pass reported nothing. Full account in
  the spec's §6 under "The sweep, and what it found in this batch".

- Command: the fix commits re-swept cold, as a separate narrower range
  (`3d69956..HEAD`, limited to this batch's files — the Plan / Day Plan
  session's commits are interleaved and out of scope)
- Result: see below; a fix commit is the least-reviewed code in any change.

- Command: the mutation gate over the fixes — 10 mutations, each the verbatim
  original, each run alone, each file restored and sha256-compared
- Result: PASS — 10 red. Two of them are the AWA-M5.4 notice in both
  directions, removed and moved after `edit_item`, because its position is half
  the fix.

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
- **AWA-A3 is mostly closed, not by plan.** It was recorded as a Low
  refactor — "three readers disagree about what a child is" — and the sweep
  showed that two of those readers were a *drifted duplicate* deciding which
  rows a delete kept. Both SQL readers now share one constant. What is left is
  `tactic_of`, which answers the object-level question from `weekly_tactic_id`
  alone because WT-INV6 depends on that, and so still returns None for a
  `parent_id`-only child. Closing the entry means fixing AWA-A1.
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
  user's call. AWA-A1 is now implicated in three sweep findings and is what
  closes AWA-A3: two cold passes independently reported that a
  `parent_id`-only child is shown in the new panel but is not week-filed, so
  two rows that look identical answer the same inline date edit differently —
  one cascades, the other returns early at `db_manager.py:492`.
