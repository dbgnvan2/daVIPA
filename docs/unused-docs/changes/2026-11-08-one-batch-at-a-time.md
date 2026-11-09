# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: one-batch-at-a-time (the concurrent-batch wind-down)

## Summary

Concurrent batches stop being the way of working in this repo. The decision is
the user's; this note records it, what it cost, and where the loose ends now
live so that none of them depends on a session staying open.

Three defects of this session's own were fixed first:

1. **`test_wtpw_the_prompt_survives_a_real_always_on_top_parent` was
   over-specified** (`23f0cc7`). It asserted that the guard restored `-topmost`
   on a real `Toplevel`. Honouring that property is a window manager's job and
   a headless CI display has none, so the read-back was off whatever the code
   did. It now reads the property straight after setting it and skips when the
   display did not take it. Confirmed in CI: the test no longer fails and the
   run reports 2 skipped where it reported 1.
2. **The pin test's failure message named a check it did not make**
   (`23f0cc7`). It claimed every screen with a completion control must appear
   in `BUILDERS` while asserting only `found == SCREENS_WITH_A_CONTROL`. The
   assertion now makes the claim rather than the message being softened.
3. **Six commits could not import `db_manager`** (`b6d6ddf`, closing CE-A22).
   `db_manager.py` held three sessions' work and was split by file instead of
   by hunk, so `apply_priority_floor` was imported six commits before
   `models.py` defined it. The hunk was moved to the commit that defines the
   function and the range replayed.

A fourth was found by the CI run of the push and fixed here: **`2934e2d`
committed four untracked root drafts**, which turned
`test_rm7c_repo_root_doc_allowlist` red. They were moved under `docs/`
(`2285759`, `c8b39ba`) rather than added to an allowlist whose every other
entry is structural.

Then the wind-down itself. `CLAUDE.md` previously allowed two concurrent builds
in two worktrees with disjoint file sets; that exception is withdrawn, with the
evidence for why in a new subsection. `NOTES.md` gains a statement of where
`main` stands. `BACKLOG.md` gains **"What `main` needs, in order"** as its
first section: all 20 of `main`'s red tests, their causes, and what each needs.

The finding that drove the decision: **worktrees fixed the swept commits and
replaced them with orphaned work.** `main` is red on 20 tests and eight of them
are already fixed on `refs/heads/claude/plan-day-range-pdm13`, an unmerged
branch of 28 commits — `main` was given the batch's tests from the shared
checkout while its implementation went on in the worktree. A ninth test exists
only on `main` and on no branch at all.

## Files changed

Source: none.

Tests:
- `tests/test_weekly_tactic_completion_widgets.py` — the skip precondition and
  the `BUILDERS` assertion (`23f0cc7`)
- `tests/test_branding.py` — one `Spec:` path, following the file it names
  (`c8b39ba`)

Docs:
- `CLAUDE.md` — the worktree exception withdrawn; "Why the worktree exception
  was withdrawn" added with the measurements
- `NOTES.md` — "Where `main` stands" added; the UPD-F1 bullet corrected from
  "not built" to "not on `main`", since it was built on a branch afterwards
- `BACKLOG.md` — "What `main` needs, in order" added as the first section;
  CE-A22 closed; WTP-A11 filed; the header's summary updated
- `docs/unused-docs/changes/2026-11-08-weekly-tactic-completion-surfaces.md` — the CI
  section rebuilt from the run logs after it was found wrong in three places
- `docs/unused-docs/changes/2026-11-08-unified-panel-followups.md` — a SHA the rewrite
  invalidated
- `docs/DOCUMENTATION_INDEX.md` — the four moved drafts, with why they moved
- `docs/daVIPA - Get Started.md`, `docs/daVIPA_rebrand_prompt.md`,
  `docs/prompt-test-suite-remediation.md`,
  `docs/prompt-update-claude-md-and-learnings.md` — moved from the repo root
- this note

## Verification

- Command: `pytest tests/test_weekly_tactic_completion_widgets.py tests/test_weekly_tactic_completion_surfaces.py -q`
- Result: PASS — 52 passed

- Command: mutation gate, 3 mutations (scratchpad `mutate_fixes.py`)
- Result: PASS — all 3 killed, both files restored byte for byte. Breaking the
  guard's `_resume_topmost` still fails the `-topmost` test locally, so the new
  skip has not neutered it; `_TOPMOST_ON = ("never",)` makes it skip, which
  proves the precondition governs; renaming a `BUILDERS` key fails the pin test.

- Command: each of the 19 commits in `origin/main..HEAD` checked out and
  `import src.getmoredone.db_manager` run
- Result: PASS — 19 of 19 import. Before the rewrite, 6 of 18 could not.

- Command: `pytest tests/test_repo_hygiene.py tests/test_branding.py tests/test_traceability_refs.py -q`
- Result: FAIL — 16 passed, 2 failed. `test_rm7c_repo_root_doc_allowlist` and
  `tests/test_branding.py` pass; the two failures are the stale `Tests:`
  references of the priority and plan-day batches, item 4 of the new
  `BACKLOG.md` section.

- Command: `pytest tests/test_plan_screen.py tests/test_plan_settings.py` at
  `c8125af` (the plan-day branch tip) in a separate worktree
- Result: PASS — 269 passed, 17 skipped, nothing failed. The same two files on
  `main` fail 9. Eight of those nine exist in the branch's run; the ninth,
  `test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day`, does not
  exist on the branch.

- Command: CI run 42550648188 on `b6d6ddf`
- Result: FAIL — 20 failed, 2578 passed, 2 skipped on each of 3.11, 3.12, 3.13.
  Every failure is accounted for in `BACKLOG.md`'s first section.

- **Nobody has opened the app.** No on-screen checklist was walked for any of
  this work.

## Risks / Known gaps

- **`main` is red on 20 tests.** None of them is now unowned or unexplained,
  but none of them is fixed on `main` either.
- **Two branches are unmerged and nothing enforces that they ever will be.**
  `refs/heads/claude/plan-day-range-pdm13` (28 commits) and
  `refs/heads/claude/elegant-neumann-ab55c9` (3 commits). If they are abandoned
  rather than merged, eight red tests on `main` have no fix in the repository
  and the tests should be removed with a record of why — not left red.
- **The merge in item 1 will conflict** in `tests/test_plan_screen.py` and
  `tests/test_plan_settings.py`. Both sides changed both files since
  `6d86791`.
- **`test_pbm61` cannot be reproduced on a working machine** — it needs a real
  on-screen window and takes keyboard focus, so it is one of the 22 skipped by
  `GETMOREDONE_NO_MAPPED_WINDOWS=1`.
- **The history rewrite changed all 19 unpushed SHAs.** Nine citations across
  three documents were updated; the pre-rewrite tip is kept at
  `refs/backup/pre-bisect-rewrite` (`eeecbd2`), a ref outside `refs/tags/` so
  it is never pushed. Any note elsewhere holding an old SHA needs CE-A22's
  mapping.
- **No external gate ran over this batch.** The Hermes `learning-qa-sweep`
  passes in `docs/unused-docs/cycles/2026-11-08_wtp-widget-tests-qa-gate.md` covered the
  WTP widget tests, not the four fixes or the documents here.

## Next agent actions

- Decide the two branches: merge them into `main`, or abandon them and remove
  the eight tests that then have no implementation. Do not leave them.
- Settle `test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day`
  before that merge, so resolving the conflict does not silently drop it.
- WTP-A11: one shared precondition for the seven window-attribute tests.
- Item 4's stale `Tests:` references, after the merge, since the merge may
  change which names are correct.
