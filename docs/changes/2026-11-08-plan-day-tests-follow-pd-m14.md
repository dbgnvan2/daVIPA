# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: plan-day-tests-follow-pd-m14 (PDT)

## Summary

The brief was to port the `outside` implementation from
`refs/heads/claude/plan-day-range-pdm13` onto `main`'s PD-M14 design.
**There was nothing to port.** Measured on `main` at `4ca7116` before writing
anything: `outside` is implemented and green at the layout layer
(`tests/test_time_grid.py`, 58 passed), and the screen half — `outside_frame`,
`build_outside_group`, the `grid()`/`grid_remove()` pair, the P2 status, the
scrollable holder — was already there, with a screen test using the "never
placed" vehicle passing the whole time.

The nine red plan-day tests were **stale vehicles, not missing code**. Six
produced an outside block by saving a tighter Day End, which PD-M14.2 made
unable to orphan one: the drawn day is derived from the date's own blocks
(`span_for_blocks`), and `PlanScreen.refresh` calls `build_day_grid` with no
span, so the day always stretches to cover what the date holds. Three asserted
the Day Settings write PD-M14.1 withdrew.

Six of the nine keep every assertion they had and changed only their setup.
**Three lost or inverted an assertion**, and in each case the one removed was of a
mechanism PD-M14 withdrew:

| test | removed | put in its place |
|---|---|---|
| `test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day` | `panel.bounds.day_start < started_at` | `== "08:00"`, plus `slot_index == -1` and `start_time == "07:30"` |
| `test_pdm54_extending_the_day_is_not_confirming_it` | `settings.plan_day_start == "07:30"` precondition | the block was written; the settings file is byte-identical |
| `test_pdm54_an_already_confirmed_day_stays_confirmed` | `settings.plan_day_end == "17:30"` | `== "17:00"`, plus the block's box |

This is repo test rule case **(b), the behaviour changed intentionally** —
stated before any test was edited.

### What replaced each vehicle

| tests | old vehicle | new vehicle | why this one |
|---|---|---|---|
| PDT-M1.1, M1.2, M1.3, M1.4, M1.6 | `on_settings_saved(DayBounds(day_end="12:00"))` | `on_settings_saved(DayBounds(lunch_start="16:00"))` | lunch over the block is the one settings change that still takes work off the grid, so `test_tgm31`'s status assertion survives intact |
| PDT-M1.5 | `day_end="10:00"`, 8 blocks | `lunch_start="13:00", lunch_minutes=240` | eight boxes of lunch is eight outside blocks, the number the fixed height is measured against |
| PDT-M2 | `bounds.day_start < started_at` | `slot_index == -1`, `start_time == "07:30"` | the capability the report asked for, against the mechanism that survived |
| PDT-M3 | `plan_day_start == "07:30"` precondition | the block was written; the settings file is unchanged byte for byte | a precondition that cannot be reached asserts nothing |

### Two findings worth keeping

- **`test_pdm131` and `test_pdm141` contradicted each other on `main`.** One
  asserted a drop moves `bounds.day_start`, the other that it does not, about
  the same call. PD-M13.1's own subject (the drop asks nothing, and it writes)
  is kept verbatim; the `day_start` half is gone, with a docstring line saying
  not to restore it.
- **`test_pbm55_the_settings_reach_the_outside_group_on_screen` had never run
  against the thing it names.** Since PD-M14 it had been reading its height off
  an *in-grid* block, because none was outside — which is why it reported 60px
  against an expected 64. Pointed at a real outside holder it passes:
  `build_outside_group` does honour `drag_schedule_box_height_px`. **No code
  fix was needed.** This was flagged in the plan as the one criterion that
  might need `src/` work; it did not.

The table above names the assertion each test was built around. Two of the
three lost a second line as well: `test_pdm54_extending_the_day_is_not_confirming_it`
also lost `json.loads(settings_file.read_text())["plan_day_shape_unconfirmed"]
is True`, replaced by the parsed-object form plus a byte-identity check on the
file; and `test_pdm131` also changed `"The day now runs"` to `"The day now
shows"`, which is PDT-M2.3.

**This batch counted the lost assertions as six, then five, and both were
wrong, because "lost" was never defined.** So here is each of the six removed
`assert` lines with what stands in its place, and no count:

| removed | what replaced it | so it was |
|---|---|---|
| `panel.bounds.day_start < started_at` | `panel.bounds.day_start == "08:00"` | **inverted** — PD-M14 requires the drop *not* to move Day Start |
| `settings.plan_day_start == "07:30"` | `[b.slot_index for b in placed] == [-1]` | **withdrawn** — the only one with nothing equivalent in its place; it asserted a settings write PD-M14 removed |
| `settings.plan_day_end == "17:30"` | `settings.plan_day_end == "17:00"` | kept, expectation changed |
| `json.loads(settings_file.read_text())["plan_day_shape_unconfirmed"] is True` | `settings_file.read_text() == "{ not json"`, with `settings.plan_day_shape_unconfirmed is True` untouched | kept, in another form |
| `"The day now runs" in status` | `"The day now shows" in status` | kept, string changed (PDT-M2.3) |
| `len(manager.get_time_blocks(SATURDAY)) == 1` | `len(blocks) == 1`, same message | rewritten, identical |

The grep `git diff 4ca7116 -- tests/test_plan_settings.py
tests/test_plan_screen.py | grep -E '^-.*assert'` prints those six lines. One
assertion was withdrawn and one inverted; the other four survive.

### What the last three passes changed, and what they left

Passes 8 and 9 stopped working from the diff and worked from the *statements*
instead, grepping every duplicate of each claim. That is what caught the
recurring shape: a statement corrected in one place with its copy left
standing elsewhere.

- **UPD-F1's defect was recorded as live in twelve places, not eleven.**
  `ce7573c` fixed ten across five files, `86a9a53` found an eleventh in
  `CHANGELOG.md` and called the enumeration complete; the ninth pass found a
  twelfth in `docs/spec_coverage.md` (the M7.3 row and two paragraphs below
  it), whose twin in `docs/spec_2026-11-07_unified_panel_design.md` `ce7573c`
  had already corrected. `86a9a53`'s message says "the eleventh place" and is
  wrong by one; the count was never a reliable unit, which is why this note
  gives the places rather than a total.
- **`docs/spec_coverage.md`'s PD-M5.3 cell overstated what was deleted.**
  `86a9a53` wrote "the named tests were deleted"; only one of the two was.
  `::test_pdm53_a_drop_below_does_not_renumber_the_day` is live at
  `tests/test_plan_screen.py` and was *strengthened* by PD-M14, which the
  withdrawing plan says in as many words. The same cell cited the
  earlier-direction guard for a bottom-box criterion; it now cites
  `::test_pdm141_a_drop_on_later_writes_no_settings`. A reader acting on the
  old cell would have deleted a green test.
- **`docs/implementation_plan_2026-11-06_plan_day_controls.md` was the one
  document PD-M14's own plan told the batch to update**, and nothing in it
  mentioned PD-M14. Its PD-M5.2 and PD-M5.3 rows still named the deleted tests
  as live. Annotated in place, in the same form the file's own PD-M5.11 row
  already used. No test scans plan files, so nothing would have caught this.
- **The day-hours plan predicted a reversal that was not built.** Its
  withdrawn-criteria table says TG-M6.4 is "Reversed by PD-M14.4: it must
  renumber". It does not: the box is stored relative to Day Start, so the
  clock times follow on read, and both `test_tgm64` tests are live and green.
  TG-M6.4 and TG-M6.4a stay `done`. The prediction is struck through in place
  with the reason, because that table is cited by the PD-M5.2 and PD-M5.3
  withdrawals above and a reader checking one would have reached the other.
- **Ten findings were filed, not fixed at the time** — `SSC-1` to `SSC-10` in
  `BACKLOG.md`. They are the same failure shape in documents outside this
  batch's file set: plans that head themselves "awaiting approval, no
  implementation code written" over code that is on `main`, a spec whose
  header contradicts its own status section 330 lines below. Sweeping them
  into a plan-day test batch would produce an unreviewable diff, which is the
  global rule 10 split. Three are high — `SSC-1`, `SSC-2` and `SSC-3`.
  `SSC-3` was left for the user, because its false sentences are in
  `CLAUDE.md`, which is auto-loaded into every session, so correcting the
  project's own instructions on a review finding is not a sweep's decision.
  **It has since been closed** — the user authorized the edit, and the bullet
  below records what the edit found. The other nine stand as filed.
- **PD-M14.4 was never built, and the plan reads as though it shipped.** The
  ninth pass struck through one table cell of that prediction; the tenth found
  the cell then pointed the reader at a list three lines below that still named
  the live `test_tgm64` test as deleted, and three further copies of the
  prediction elsewhere in the same section. The authority is
  `docs/changes/2026-11-08-day-hours-are-a-template-wip.md`, which records
  PD-M14.4 under "Not started"; `grep -rn "def test_pdm144" tests/` returns
  nothing, and `shift_all_slots` has no production caller. That wip note is
  the authority for what was built, but two of its *other* claims have since
  gone stale — it says TG-M6.4 and PD-M5.5 are withdrawn and still owed
  `docs/spec_coverage.md` rows, and both are recorded `done` there, correctly.
  It is a dated handoff note, so it is left as written. The section now
  carries one dated not-built note at its head, so the copies inside it are
  governed by a single statement, and the deletion list is corrected to the
  three tests that were deleted. This is the batch's own correction gone wrong:
  a cell fixed without reading the paragraph under it.
- **The tenth pass caught a cite the ninth pass's own edits had moved.** SSC-8
  listed `BACKLOG.md:386` for a line that the same commit's earlier hunks in
  `BACKLOG.md` had pushed to `:393`. A line cite written against the pre-edit file is the same defect
  the cite corrections were for. It then happened a third time, in the next
  round: that round's `docs/DOCUMENTATION_INDEX.md` hunk added two lines and
  silently moved five cites in `BACKLOG.md`, three of them inside the sentence
  where the second one had just been fixed. Re-reading cites after each edit
  was clearly not going to hold, so the `SSC` section now says to cite by
  quoted text and a grep for the three files this batch edits, and the
  remaining line cites there point only into files it does not touch.
- **`CLAUDE.md` was corrected, on the user's authorization, and `SSC-3` is
  closed.** The sweep filed it rather than fixing it because that file is the
  project's own instructions, auto-loaded into every session; the user was
  asked and said to fix it. Making the edit turned up a **third** false
  sentence, and it is the one that mattered: the first bullet of "Why the
  worktree exception was withdrawn" said eight of `main`'s twenty red tests
  "were already fixed" on `refs/heads/claude/plan-day-range-pdm13`. Acted on,
  that reads as "merge the branch" — which is what this batch was originally
  asked to do, and which would reintroduce the mechanism that caused both
  reported faults. The implementation was already on `main` at `4ca7116`; the
  eight passed on the branch only because they reached their subject through
  the design PD-M14 withdrew. That bullet now says they *passed* there, that
  the branch must not be merged, and why a test passing on a branch does not
  locate a fix. The measurement itself is left as it was taken, with each
  resolved item marked inside it, because the section's argument is about what
  that day cost. `CLAUDE.md` is now a file this batch edits, so `SSC-3`'s own
  cites into it were converted to quoted text at the same time.
- **Four wrong line cites inside those filings were corrected** rather than
  filed again — a filing whose cite points at the wrong line sends the next
  reader to a non-problem, so the cite is the filing's payload, not cosmetics.

## Files changed

- `tests/test_plan_screen.py` — PDT-M1.1–M1.6, PDT-M2 (`a19a38a`)
- `tests/test_plan_settings.py` — PDT-M3, both PD-M5.4 tests (`a19a38a`)
- `src/getmoredone/screens/plan.py` — `virtual_under_pointer`'s `Tests:` line
  (`2cd83a3`), and the removal of a duplicate `Tests:` line that `2cd83a3`
  itself introduced (found by the second cold pass; `53d480b`)
- `src/getmoredone/time_block_layout.py` — `edge_limit_time` and `build_day_grid` `Tests:` lines, one broken line break (`2cd83a3`)
- `src/getmoredone/screens/plan_blocks.py` — `build_outside_group`'s stale prose about Day End (`2cd83a3`)
- `docs/spec_coverage.md` — the PD-M5.5 implementation and status cells, the
  three routing phrases that gave a count of dead names, and three PDT rows
  whose wording claimed more than their test asserts; 8 references repointed
  and 1 dropped, across 3
  rows (TG-M3.1, PD-M5.5, PD-M5.8); the 21 PDT rows; the PD-M5.2, PD-M5.3 and
  PD-M5.6 rows marked **withdrawn**; and the M7.3 row with the two UPD-F1
  paragraphs under it
- `docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md` — this note
- `BACKLOG.md` — items 1, 2 and 4 rewritten; `PDT-A1`–`PDT-A5` and `SSC-1`–`SSC-9`
  filed; the `SSC` section's cite rule; `PDT-A1` rewritten to give the measuring
  command instead of totals that went stale inside this batch
- `NOTES.md` — where `main` stands; the UPD-F1 and test-count corrections
- `CHANGELOG.md` — UPD-F1's `[Unreleased]` entry corrected
- `CLAUDE.md` — three false sentences in "Why the worktree exception was
  withdrawn", corrected on the user's authorization (`SSC-3`)
- `docs/spec_2026-11-07_unified_panel_design.md` — the M7.3 row's UPD-F1 status
- `docs/implementation_plan_2026-11-08_unified_panel_followups.md` — the §7
  and §9 wrappers recording UPD-F1 as built
- `docs/implementation_plan_2026-11-06_plan_day_controls.md` — PD-M5.2, PD-M5.3
  and PD-M5.6 annotated as withdrawn by PD-M14, which that plan asked for;
  PD-M5.5's deleted test name and the Earlier-drop paragraph marked
- `docs/implementation_plan_2026-11-08_day_hours_are_a_template.md` — the
  TG-M6.4 prediction struck through; dated not-built notes at the head of the
  PD-M14.4 section and the implementation order; the deletion list, the
  PD-M5.5 row and a test name that never existed corrected
- `docs/implementation_plan_2026-11-08_plan_day_tests_follow_pd_m14.md` — the plan (`11ec1dc`)
- `docs/DOCUMENTATION_INDEX.md` — this note and the plan; the UPD-F1 entry,
  which was still present-tense

No `src/` behaviour changed in this batch. The three `src/` files hold
docstring text only.

## Verification

Run on the tree as this batch leaves it, **after** the sweep passes and their
fixes (ten cold passes in all). **Re-run after the tenth pass**, which found
this section claiming a result for a tree two rounds of document fixes had
since changed — `docs/spec_coverage.md` is in `tests/test_traceability_refs.py`'s
`SCANNED`, so a document edit can move these numbers. The figures below are
from the re-run, on the tree this batch ends with, and are identical to the
earlier run's. The earlier run recorded here
covered **four** files, without
`tests/test_traceability_refs.py`, and gave 396 passed / 17 skipped — 413
cases, all accounted for. Folding the fifth file in adds its 3 cases, two of
which pass and one of which is the pre-existing failure below: 416 cases,
1 + 398 + 17. No test was added or removed between the two runs; the fixes
added one assertion to `test_pbm55` and five reference edits to
`docs/spec_coverage.md`.

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_plan_screen.py tests/test_plan_settings.py tests/test_time_grid.py tests/test_time_block_layout.py tests/test_traceability_refs.py -q`
- Result: **1 failed, 398 passed, 17 skipped.** The one failure is
  `test_every_referenced_test_file_exists`, red on the two `models.py` file
  references — the PRI gap, which predates this batch (`models.py` is in none
  of its commits and the same `Tests:` lines are present at `4ca7116`).
  `test_every_referenced_test_name_exists` passes. See Risks.
- **No full-suite run and no CI run covers this range.** `main` is ahead of
  `origin/main`, so the twenty-failure CI picture quoted elsewhere is from run
  42550648188, before this batch.

Mutation-proved, each restored byte-identical and confirmed so with
`git diff --stat`:

| criterion | mutation | result |
|---|---|---|
| PDT-M1.1 | the lunch branch deleted from `build_day_grid` | red |
| PDT-M1.3 | the holder pinned to `SLOT_CHIP_HEIGHT_PX`, ignoring `chip_height` | red |
| PDT-M2 | `extended_span` makes no room before the first box | red |
| PDT-M3 | `extend_day_for` writes and saves the hours again | red, both tests |

The full suite was left to CI, per the repo's throttle rule.

## Risks / Known gaps

- **PRI-M1/M2 shipped without its tests.** `src/getmoredone/models.py` names
  `tests/test_priority_floor_and_cap.py` and `tests/test_priority_floor_form.py`
  and three tests inside them; none of the five has ever existed. So the
  priority cap, the floor and the "(capped)" label are unverified.
  `test_every_referenced_test_file_exists` stays red on exactly this.
  **Deliberately not closed:** deleting the `Tests:` lines would green the meta
  test while hiding the gap, which is the opposite of what it is for. Filed as
  `BACKLOG.md` item 2. Not this batch's work.
- **Nine CI-environment failures are untouched** and were never in scope:
  `test_t51`, `test_t52`, `test_t56`, `test_t57`, `test_wt_m6b6`,
  `test_alpha_still_passes_through_the_attributes_wrapper`,
  `test_raw_tkinter_windows_are_hidden_and_registered_too`,
  `test_pbm61_a_tall_row_keeps_its_two_lines_together`,
  `test_updm14_zero_width_body_is_a_noop`. **Eight pass locally** under
  `GETMOREDONE_NO_MAPPED_WINDOWS=1`; seven of those are the always-on-top
  family and need a window manager the CI runner does not have.
  **The ninth, `test_pbm61_a_tall_row_keeps_its_two_lines_together`, does not
  pass locally — it is *skipped*,** because it takes the `mapped_windows`
  fixture that this very variable skips, so it cannot be reproduced on a
  working machine at all (`BACKLOG.md` item 5 says so too). A skipped test is
  not a passing test, and an earlier draft of this note called all nine
  passing. `test_updm14_zero_width_body_is_a_noop` builds no window and its
  cause is unidentified, so it is not the same family either. `BACKLOG.md`
  items 3 and 5.
- **`refs/heads/claude/plan-day-range-pdm13` is superseded, not merged.** It
  stays at `c8125af`. Its design is what caused both reported faults, so it
  must not be merged; deleting it is a decision nobody has taken. No test can
  assert this (PDT-N1), so it lives here and in `BACKLOG.md`.
- **That the rewrites still assert the right things is a judgement**, not
  something mutation testing settles (PDT-N2). The table above is there so a
  reviewer can check each one against what it replaced.

## Next agent actions

- Write the three PRI tests, or decide the priority cap ships unverified and say
  so in `BACKLOG.md`. Until then `main`'s CI cannot go green.
- Design the one shared precondition for the nine CI-environment tests
  (WTP-A11). `23f0cc7` is the worked example for a single test; seven of them
  need one guard, not seven.
- Decide whether `refs/heads/claude/plan-day-range-pdm13` is deleted.
