# learning-qa gate — WTP-M6.8 widget tests + doc corrections

RANGE      `5a91814..HEAD` (exactly two commits)
COMMITS    906827d — test(wtp): the completion question through the real widgets (new file, 592 lines)
           d06180b — docs(wtp): WTP-M6.8, and the Hierarchical screen's dead method
APPLICABLE P6 (doc honesty), P8 (dirty/shared state), P19/P31 (producer/consumer + scope)
CHECKED    906827d and d06180b only; no working-tree files touched
NOT COVERED the mutation gate's own script (scratchpad `mutate_widgets.py` is not in the repo);
           the full suite (per instruction, only the touched file was run)
VERDICT    APPROVED — four low-severity doc-accuracy findings, no test- or code-behaviour defect

## Verification run

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 ./venv/bin/python -m pytest tests/test_weekly_tactic_completion_widgets.py -q
21 passed in 12.66s
```

The 21 tests pass against the current tree. The "13 mutations all killed" claim in the
handoff note cannot be independently reproduced — the mutation scratchpad is not committed —
so it is accepted on the strength of inspection (see the test-quality section below), not
re-run.

## Findings (all low severity; none block)

F1 — LOW · P6 · tests/test_weekly_tactic_completion_widgets.py:437
    The pin test's docstring says the completion-control set "is four, not six", but
    `SCREENS_WITH_A_CONTROL` (line 63) has five entries and the AST walk finds five:
    today, all_items, upcoming, project_boards, item_editor. The count is off by one.
    Risk: a maintainer reading the docstring doubts whether the pin itself is right.
    Fix: "five, not six". (The set and the assertion are correct; only the number in the
    prose is wrong.)

F2 — LOW · P6 · tests/test_weekly_tactic_completion_widgets.py:439
    Same docstring: "project_boards' own call site is the only one outside a row checkbox".
    That is false — item_editor's completion control is also a button
    (`item_editor.py:487 command=self.complete_item`), not a row checkbox. Two screens use
    buttons (project_boards and item_editor), not one.
    Risk: misdescribes the binding shapes the locator must handle.
    Fix: drop the clause or say "the editor and project_boards use buttons; today,
    upcoming and all_items use row checkboxes".

F3 — LOW · P6 · docs/changes/2026-11-08-weekly-tactic-completion-surfaces.md (Verification)
    "Step 7's ordering (the question before the note dialog, the Next Action window intact)
    is tested." The "Next Action window intact" half is not tested. Both timer tests drive
    `finished_action()` on a TimerWindow whose `next_action_window` is None — nothing ever
    opens a Next Action window, so the `if self.next_action_window and ...destroy()` branch
    is not exercised. The test asserts `timer.winfo_exists()` (the TimerWindow survives),
    which is not the Next Action window.
    Risk: a reader believes a regression in that branch would be caught by a test; it would
    not.
    Fix: say "the TimerWindow survives a No is tested; the Next Action window's survival is
    not exercised because the tests never open one." (The claim about "question before the
    note dialog" is tested: `messageboxes == ["askyesno"]` plus `get_work_logs == []`.)

F4 — LOW · P31 scope · tests/test_weekly_tactic_completion_widgets.py:436-443
    The pin test's docstring calls its set "the set a user can reach". The predicate is
    narrower: only `command=` values whose AST mentions an attribute literally named
    `complete_item`. The timer's Done button is a user-reachable completion control
    (`command=self.done_action` → `run_reward_sequence` → `finished_action` →
    `complete_action_item`) and is therefore absent from the pinned set. The timer is not a
    coverage hole — it has two dedicated tests and is pinned by the surfaces file's
    `EXPECTED_CALL_SITES` — but the pin's name and prose overstate what it pins. The
    `SCREENS_WITH_A_CONTROL` comment (lines 58-64) explains the hierarchical exclusion but
    never says why the timer is excluded.
    Risk: someone could read the pin as "every completion control is covered here" and stop
    looking at the timer.
    Fix: add one sentence to the comment: "The timer's Done button is excluded because it
    reaches `complete_action_item` through `finished_action`, not `complete_item`; the two
    timer tests cover it." (The surfaces file already pins the timer's two call sites.)

## What was checked and held up

Test quality (attack area 1) — no vacuous test.
- The decline and ask tests fail if the guard is removed: with `confirm_weekly_tactic_completion`
  gone, `_completion_control` still finds the widget, but pressing it produces no `askyesno`,
  so the `== ["askyesno"]` assertions go red.
- Every outcome is read back from the stored row (`_status(...)`), not a flag or call log,
  except the "the question is asked" tests, whose contract genuinely is the messagebox and
  message content.
- The accept tests (tactic completes, children stay open) do not detect a removed guard, and
  are not expected to — their contract is WTP-D8 no-cascade, verified by inspection.
- The hang that was already fixed is the only one: the two timer tests arm the bounded-retry
  dismisser (`_skip_the_note_dialog`, 50 × 20 ms), so deleting the guard makes
  `finished_action` walk into `wait_window(dialog)`, get dismissed, complete the item, and go
  red instead of blocking. The item_editor and project_boards accept paths have no `wait_window`
  and cannot hang (messageboxes are recorded, not shown, by conftest).

Control locator (attack area 2) — cannot silently skip.
- `_completion_control` asserts `len(found) == 1`; 0 or 2 matches raise with a named message.
  The assertion is reachable in every parametrised case (all 5 BUILDERS exercised in both
  decline and accept runs, plus the plain-item and all-done tests).
- All three binding shapes are real and were confirmed against source: closure over the
  ActionItem (`today.py:555`, `upcoming.py:326`), id pinned as a lambda default
  (`all_items.py:276`, `project_boards.py:1532`), and the bound method
  (`item_editor.py:487`). The `_calls_complete_item` guard correctly excludes the
  project_boards selection checkbox (`_on_item_checkbox_toggled`, line 385) and
  `completed.py`'s `uncomplete_item` (line 320, substring-only match, not an `.attr`
  match).

Scope (attack area 3) — see F4; the timer hole is real but covered, not hidden. The surfaces
file's `EXPECTED_CALL_SITES` pins `("timer_window.py", "finished_action"): 2`, so a new
completion path in the timer still fails an existing test.

Dirty state (attack area 4).
- `_LIVE_TIMERS` is a `WeakValueDictionary` keyed by item.id; each `world` uses fresh ids,
  and the autouse `_empty_timer_registry` clears it both sides. No leak.
- `messageboxes` fixture empties the session recorder on entry and exit.
- `root` and `world` are function-scoped; VPSManager is closed in teardown and also swept
  by conftest's connection net.
- Clock: `date.today()` correctly lands rows on Today and Upcoming (today is always in the
  current week). The only year-boundary wrinkle is inherited, not introduced: `seed_ape()`
  defaults to year 2026 while tactic dates are `date.today()`, so a run in a later year seeds
  a tactic dated outside its APE's year. The assertions here read DB status and the
  messagebox, not APE-year consistency, so the tests would still pass; it is a latent coupling
  in the pre-existing `weekly_tactic_fixtures.py`, not this diff.

Doc honesty beyond the findings (attack area 5) — the remaining claims in d06180b check out:
- "HierarchicalScreen.complete_item has no caller anywhere in src" — confirmed; the only
  reference is its own definition (`hierarchical.py:357`) plus the guard call inside it. The
  alignment label claim (`CTkLabel(frame, text="", width=70)`, line 352) is accurate.
- "Six of the seven call sites are reachable" — confirmed: today, all_items, upcoming,
  project_boards, item_editor, timer_window are all reachable from a control; hierarchical
  is not.
- Spec count 39 → 40 — internally consistent (35 + WTP-M1.7 + 2 WTP-M5.2 extras + WTP-M6.7
  + WTP-M6.8).
- USER_GUIDE correction and handoff checklist step 4 strike-through match the code.

## Follow-ups for the next session

- Fix F1/F2/F4 (one docstring + one comment in the widgets file) and F3 (one sentence in the
  handoff note). All are prose edits, no test behaviour changes.
- The mutation scratchpad (`mutate_widgets.py`) is uncommitted and unreproducible from the
  repo; consider committing it so the "13 killed" claim is re-runnable.

---

# Re-gate (second pass, 2026-11-08)

RANGE      f264cc3, ad0b707, 3b191ae (three non-contiguous commits; dc662f0..7a101dc excluded)
COMMITS    f264cc3 — fix(ce): the TimeBlock field and column 8c65080 left behind
           ad0b707 — test(wtp): the pin test's docstring said three untrue things
           3b191ae — docs(wtp): a verification claim that was not true, withdrawn
APPLICABLE P6 (doc honesty), P8 (idempotent migration / dirty state), P19/P31 (producer/consumer scope)
CHECKED    the three commits only; db_manager.py / models.py / database.py at HEAD, not the working tree
NOT COVERED the full suite (per instruction); the four out-of-scope VSP/UPD commits; the two untracked
           CE test files (test_calendar_export.py, test_plan_screen_calendar_export.py)
VERDICT    NOT CLEAN — PART 1 (the code repair) is sound, but PART 2 introduced one new false claim
           (R2-1) plus two low imprecisions. One sentence to rewrite, then re-sweep that commit.

## Verification run

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 ./venv/bin/python -m pytest tests/test_weekly_tactic_completion_widgets.py -q
21 passed in 16.73s
GETMOREDONE_NO_MAPPED_WINDOWS=1 ./venv/bin/python -m pytest tests/test_weekly_tactic_dedupe.py -q
31 passed in 13.97s
```

## PART 1 — f264cc3 (the code repair)

Completeness — COMPLETE. Every `calendar_event_id` / `calendar_event_calendar_id` site in the
committed db_manager.py is backed by a field and a column:

- `create_time_block` INSERT (db_manager.py:1398-1409) names both columns, which the CREATE
  TABLE (database.py:304-305) and the migration (database.py:807, 821) both declare, and
  which `TimeBlock` (models.py:282, 289) both carries.
- `set_block_calendar_event_id` (db_manager.py:1493-1499) UPDATEs both columns; both exist.
- `_row_to_time_block` (db_manager.py:2790-2811) reads both defensively (try/except KeyError)
  and maps them into the two fields. This is the only row -> TimeBlock mapper, and every
  `SELECT * FROM time_blocks` (1525, 1545, 1789) routes through it, so no positional mapping
  is shifted by the new columns.

Over-inclusion — NONE. The database.py diff is 23 insertions: the two CREATE TABLE columns and
the two migration entries with their comments. The models.py hunk is the two TimeBlock fields
with their comments. Nothing from the Priority session (`priority_score_from_factors` etc.)
entered either file; that code is pre-existing at models.py:59-101, 391-438 and is untouched.

Idempotency (P8) — SAFE on all three states. On a fresh DB the CREATE TABLE declares both
columns, the migration's `PRAGMA table_info` then sees them present and skips. On a pre-CE DB
the CREATE TABLE is a no-op and the migration ALTERs each column in (guarded per-column, not
all-or-nothing). On an already-migrated DB both are present and skipped. Column order is
irrelevant to the guarded ALTER since each check is by name.

Field order — SAFE. All four src `TimeBlock(...)` constructions (plan.py:1264, 1312, 1732,
2610) pass keyword arguments only; the two new fields are appended after `updated_at`, so no
positional id/created_at/updated_at is shifted.

Broken reads — NONE found. No `UPDATE` drops the columns: `update_time_block`
(db_manager.py:1448-1453) deliberately does not touch them (documented at 1437-1444). NULL is
handled: the columns are NULLable with no default, and the mapper leaves NULL as None rather
than back-filling. `calendar_exporter.py` (the only other reader) is untracked, so it is not
part of "main is repaired".

R1-1 — LOW · P19 scope · the verification selection is 5 of 6, not 6 of 6.
    The claim "main is repaired" was verified against test_time_block_crud.py,
    test_time_block_schema.py, test_plan_screen.py, test_time_grid.py, and
    test_time_block_layout.py. One committed test file exercises TimeBlock and was NOT in the
    selection: tests/test_weekly_tactic_dedupe.py. Its
    `test_wt_m7a3_time_block_on_the_loser_does_not_crash_the_merge` calls
    `create_time_block(TimeBlock(...))` — the exact INSERT the repair touches — so it would have
    been among the 127 failures before f264cc3 and is evidence this repair fixes it. I ran it
    (31 passed). The repair itself holds; only the breadth of the stated evidence is one file
    short of exhaustive. (test_calendar_export.py and test_plan_screen_calendar_export.py also
    exercise TimeBlock but are untracked, so they are correctly excluded from "main".)

## PART 2 — ad0b707 + 3b191ae (the corrections)

R2-1 — MEDIUM · P6 · tests/test_weekly_tactic_completion_widgets.py:445-446 (NEW false claim).
    The corrected docstring says "Of the five, four wire a row checkbox and item_editor wires a
    Complete button." That is wrong: only three wire a row checkbox — today.py:550,
    upcoming.py:321, all_items.py:271. project_boards' completion control is the "Complete"
    BUTTON at project_boards.py:1532, not its row checkbox (line 385 wires
    `_on_item_checkbox_toggled`, which only toggles a selection set and never completes).
    item_editor wires the bound-method button at item_editor.py:487. The true split is three
    checkboxes (all_items, today, upcoming) plus two buttons (project_boards, item_editor).
    This is not a fresh discovery — the prior gate's own F2 finding and its fix text already
    stated "the editor and project_boards use buttons; today, upcoming and all_items use row
    checkboxes" — so the correction re-introduced the very error it was fixing.
    Fix: "Of the five, three wire a row checkbox (all_items, today, upcoming) and two —
    project_boards and item_editor — wire a Complete button."

R2-2 — LOW · P6 · tests/test_weekly_tactic_completion_widgets.py:438 (imprecision).
    "the two timer tests in this file press it" overstates. The two timer tests call
    `timer.finished_action()` directly (lines 566, 590); they do not press the Done button
    (`command=self.done_action`, timer_window.py:522, whose `done_action` runs the reward
    sequence before `finished_action`). And only the yes-test reaches `complete_action_item`;
    the decline test returns at the guard (timer_window.py:1147-1150). The substantive claim
    the sentence is making — the timer's completion is not a coverage hole — holds; the verb
    "press" and the "two tests reach completion" reading are loose. Prior gate's F4 wording
    ("the two timer tests cover it") was accurate; "press it" is the regression.

R2-3 — LOW · P6 · docs/changes/2026-11-08-weekly-tactic-completion-surfaces.md (overstatement).
    Half B is correct: both timer tests run on a TimerWindow whose `next_action_window` is None
    (init at timer_window.py:349; neither test opens one), so the destroy branch (1153-1156) is
    never entered and "the Next Action window stays intact" is genuinely untested. Half A is
    overstated: "the question coming up before the note dialog IS tested" is supported only by
    `get_work_logs == []` plus `messageboxes == ["askyesno"]`, which pins "declining asks, then
    writes no log and completes nothing" — i.e. the guard fires before the work-log write and
    the completion. It does NOT pin the literal ordering of the question relative to the note
    dialog: a regression that moved the note dialog ahead of the guard would still pass (the
    dialog is a Tk widget, not a messagebox, and `_skip_the_note_dialog` would dismiss it with
    no assertion on whether it was needed). The current code does put the guard first, so the
    sentence is true by inspection but not mutation-guarded. Note the prior gate's F3 "fix"
    text carried the same over-strong wording, so this is inherited rather than new.

What held up (verified true, not findings):
- "five screens" — SCREENS_WITH_A_CONTROL (line 63) has exactly five entries; the AST walk
  finds the same five.
- Timer exclusion "by construction" — the pin predicate only matches `command=` values naming
  `complete_item`; the Done button names `done_action`, which reaches `complete_action_item`
  through `finished_action` (timer_window_reward.py:261-299), so it is outside the pin.
- `EXPECTED_CALL_SITES` pinning `("timer_window.py", "finished_action"): 2` is real
  (surfaces file line 294).
- "BUILDERS" (replacing "parametrize list") is accurate — the tests parametrise over BUILDERS
  (line 268/282) and the failure message names it.
- Spec WTP-M6.8 row correction (five screens, timer outside the pin, two tests of its own) is
  accurate.
- The handoff note's new next-action bullet ("open one, decline, assert it is still there …
  nothing checks it") is accurate.

## Follow-up

- Rewrite the one sentence in R2-1 (three checkboxes + two buttons), and tighten R2-2's
  "press it" to "drive it" / "cover it" and R2-3's "IS tested" to "is consistent with the
  guard sitting first, by inspection". No test behaviour changes; the 21 widgets tests and the
  31 dedupe tests pass as-is.
- Re-sweep only the fix commit for these three prose edits (new range = pre-fix tip..HEAD).

---

# Resolution of the re-gate (2026-11-08, same session)

Every finding of the second pass, with what was done and why. The sweep budget
in `CLAUDE.md` sends below-medium findings to `BACKLOG.md` rather than fixing
them in-loop; three of these four are false statements in prose, where that
rule buys nothing — a wrong claim carries none of the regression risk a
cosmetic code fix does, and global rule 13 and P6 require correcting it. The
two coverage gaps the pass exposed underneath those claims are genuinely
below-medium and were filed, not fixed.

## R2-1 (medium, new false claim) — fixed

The pin test's docstring said "four wire a row checkbox and item_editor wires a
Complete button." Verified against the source before rewriting: `today.py:550`,
`all_items.py:271` and `upcoming.py:321` build a `CTkCheckBox` with
`command=... complete_item`; `project_boards.py:1532` and `item_editor.py:487`
build a `CTkButton`. So three and two, not four and one. A project board row
does carry a checkbox at 1497, but its variable goes into
`self.item_checkbox_vars` and is read by `_on_item_checkbox_changed` — it is
the screen's selection set and completes nothing.

This was the same error the first pass's F2 had already corrected once. The
first fix replaced a wrong sentence with another wrong sentence because it was
written from the shape of the five `BUILDERS` entries rather than re-read off
the five widgets. The docstring now names each screen with its control.

## R2-2 (low, false claim) — fixed

The same docstring said the timer's Done button is covered because "the two
timer tests in this file press it". They do not: both call
`timer.finished_action()` directly. Traced the real route — Done calls
`timer_window_reward.done_action`, which runs the reward sequence and then
calls `finished_action`. The docstring now says which method the tests call,
and that `done_action` is covered by neither. The gap itself is filed as
**WTP-A9**.

## R2-3 (low, overclaim) — fixed

The handoff note said step 7 was half tested because "declining asserts no work
log was written, which it would have been had the flow reached the dialog."
That reasoning does not hold: with the guard moved to after the note dialog, a
decline still writes no work log, so the test still passes. The note dialog is
a custom `Toplevel`, not a `messagebox`, so the "asks exactly once" assertion
cannot see it either. The note now says the test pins the outcome and not the
ordering, and step 7 is described as checklist-only. Filed as **WTP-A10**.

## R1-1 (low, evidence breadth) — measured

The gate noted the CE repair in `f264cc3` was verified against five of the six
time-block test files; `tests/test_weekly_tactic_dedupe.py` was omitted from
the stated evidence. Run here directly rather than taken from the gate's
report, in the same clean detached worktree at `f264cc3` so no concurrent
session's dirty files could flatter it:

```
cd <worktree-at-f264cc3>
GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b \
  /Users/davemini2/ProjectsLocal/daVIPA/venv/bin/python \
  -m pytest tests/test_weekly_tactic_dedupe.py -q
31 passed in 4.10s
```

So the repair holds across all six; only the breadth of the evidence stated in
the commit message was short, and the commit message is not rewritten for it.

## Tests after these corrections

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m pytest \
  tests/test_weekly_tactic_completion_widgets.py \
  tests/test_weekly_tactic_completion_surfaces.py \
  tests/test_ci_contract.py -q
134 passed, 1 skipped in 94.76s
```

The skip is `test_ci_contract.py:371`, which only runs where a display is
provided. The widget tests take no `mapped_windows` fixture, so the documented
mapped-window count of 22 is unchanged and the contract test still passes.

## What was not re-swept

These corrections are prose and two backlog entries; no `src/` line changed.
The budget calls for a further pass only on a high-severity finding, and R2-1
was medium. The corrections themselves were verified by re-reading the five
widget definitions and the `done_action` route in the source, which is what the
two false claims had skipped.

---

# Third pass — the corrections, re-read against source (2026-11-08)

RANGE      `3b191ae..HEAD` (exactly two commits)
COMMITS    fcd92ba — test(wtp): the pin test's docstring, wrong twice about its own five screens
           ef69c5b — docs(wtp): the re-gate's four findings, two backlog entries, the index
APPLICABLE P6 (doc honesty), P19/P31 (producer/consumer + scope)
CHECKED    the two commits only; every factual claim below re-read off `src/`, not off the surrounding prose
NOT COVERED the full suite (per instruction); no test run was needed — every claim here is a source fact, not a run result
VERDICT    CLEAN — no new false claim. The one correction that had already been wrong twice is now right, and two of its
           line numbers silently fix an error the second pass itself made.

## What was verified, claim by claim

Docstring (`test_wtpw_the_screens_with_a_completion_control_are_pinned`):

- Three row checkboxes — `today.py:550`, `all_items.py:271`, `upcoming.py:321` each build a
  `ctk.CTkCheckBox` with `command=…complete_item`. True.
- Two buttons — `project_boards.py:1532` (`CTkButton`, text "Complete", `command=…complete_item`)
  and `item_editor.py:487` (`CTkButton`, text "Complete", `command=self.complete_item`). True.
- The project board row's own checkbox is a selection toggle — `project_boards.py:1497-1508` stores
  its `BooleanVar` in `self.item_checkbox_vars[item.id]` and wires `_on_item_checkbox_changed`,
  which adds/removes `item.id` in `self.selected_item_ids` (line 1697) and completes nothing. True.
- The two timer tests call `finished_action` directly (`:572`, `:596`), not Done. Done's button
  (`timer_window.py:522`, `command=self.done_action`) calls `timer_window_reward.done_action`
  (`:261`), which runs `run_reward_sequence` inside the guarded `try` and then calls
  `finished_action` (`:299`). True.

Note on R2-1's own line numbers: the second pass's finding cited the project board row checkbox as
"line 385 … `_on_item_checkbox_toggled`". That is the *link-item picker's* checkbox, not the board
row. The resolution corrects this to `1497` / `_on_item_checkbox_changed`, and the correction is
right — so this pass fixed a line-number error the prior pass introduced while fixing the count.

Resolution section line numbers: `today.py:550`, `all_items.py:271`, `upcoming.py:321`,
`project_boards.py:1497`, `project_boards.py:1532`, `item_editor.py:487` — all confirmed above.

"Guard moved after the note dialog still passes the decline test" (R2-3, WTP-A10): holds. The
decline test asserts `messageboxes == ["askyesno"]`, `get_work_logs == []`, status not COMPLETED, and
`timer.winfo_exists()`. Moving the guard after the dialog still calls `askyesno`, still returns before
the work-log write and the completion, and still leaves the timer alive; `CompletionNoteDialog` is a
`ctk.CTkToplevel` (`timer_window_dialogs.py:217`), not a messagebox, so the `messageboxes` fixture
never sees it, and `_skip_the_note_dialog` dismisses it with no assertion on whether it was needed.
The ordering genuinely is unasserted; the sentence is accurate.

Step-7 rewrite (`docs/changes/…completion-surfaces.md`): `next_action_window` is initialised to
`None` (`timer_window.py:349`) and neither timer test opens one (`_stopped_timer` never calls
`open_next_action_window`), so the destroy branch (`:1153-1156`) is never entered and the tests assert
the TimerWindow survives (`timer.winfo_exists()`), not the Next Action window. Accurate.

BACKLOG WTP-A9 / WTP-A10: both accurate. A9's route and the `try/except` swallowing the reward-stage
exception (with the TclError comment recording the lost work log/completion/count) are exactly as
described (`timer_window_reward.py:285-299`). A10's outcome-vs-ordering distinction is exactly what
the test asserts. Severity: A10 is clearly Low. A9 is the closer call — the consequence if it regresses
is the data loss the comment records, but the probability is narrow and the pieces (`finished_action`,
the guard, the work-log save) are each already tested, so Low is defensible, not undersold.

DOCUMENTATION_INDEX "40 of 40": matches the spec's §6 summary line ("all 40 criteria `done`"), and the
WTP-M6.7 / WTP-M6.8 / "21 tests" descriptions match §6's rows. The index is now aligned with §6, which
the previous "32 of 35" was not.

> **Note added 2026-11-09, by the cold pass over the SST batch.** The paragraph
> above is left as the gate wrote it: it records what the spec and the index
> said on 2026-11-08, which is what a gate record is for. Both figures were
> wrong, and neither is current. The spec's §3 rows numbered 41 then and number
> 41 now; §6, `BACKLOG.md` and `docs/DOCUMENTATION_INDEX.md` were corrected to
> 41 by the SST batch, and `tests/test_doc_status_claims.py` now recounts the
> rows rather than trusting any of those figures.

## Non-blocking observation

§6's summary says "40" but its tables list 41 `done` rows (M1×7, M2×8, M3×6, M4×6, M5×6, M6×8). The
decomposition "35 + M1.7 + the two M5.2 extras + M6.7 + M6.8" counts M5.2's two extra *test cases* as
criteria while omitting M6.4-M6.6. This is pre-existing in §6 (not in this range) and the index mirrors
§6's summary faithfully, so it is not a finding against these commits — but §6's arithmetic is worth a
one-line correction at some point.

## On the two in-loop judgements

Fixing the three prose false claims (R2-1 medium, R2-2/R2-3 low) in-loop rather than filing them was
the right call. R2-1 was medium and had to be fixed. R2-2 and R2-3 were low but were *false*, not
cosmetic: the below-medium rule's rationale is that a cosmetic fix "buys none of the safety it costs",
i.e. code regression risk, and a prose correction carries none of that — while P6 and rule 13 require a
known-false claim to be corrected, not filed. The one caveat is that a prose fix carries *new-false-claim*
risk rather than behavioural risk — this very pass exists because the first correction got it wrong — and
the resolution acknowledges that by re-reading the five widget definitions and the `done_action` route
instead of trusting the prior fix.

Filing WTP-A9 and WTP-A10 rather than fixing them was also right. Both are below-medium; A9's effort is
Medium (build a TimerWindow with a project-linked item and press the real Done control, pulling the
deliverable dialog and reward sequence into the test) for a Low-severity coverage gap whose pieces are
already tested, and A10's placement is correct today and reviewed twice. The budget says file
below-medium findings; filing both is consistent with it.

## Follow-up

- Optionally fix the §6 summary arithmetic (40 vs 41) noted above — it is a spec edit, not a correction
  of these commits.


---

# The WTP-A10 claim, measured (2026-11-08, after the third pass)

Both the third pass and I had reached "a guard moved after the note dialog
would still pass the decline test" by reading the code. Since the two findings
before it were claims that looked right and were not, it was measured: in a
detached worktree at `ef69c5b`, the guard was removed from its place in
`finished_action` and re-inserted after `self.wait_window(dialog)`.

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b \
  /Users/davemini2/ProjectsLocal/daVIPA/venv/bin/python \
  -m pytest tests/test_weekly_tactic_completion_widgets.py -k timer -q
2 passed, 19 deselected in 3.44s
```

The reordering is invisible to both timer tests, as WTP-A10 says. The worktree
was removed and no file in the shared checkout was mutated, because the gate
was reading that tree at the time.
