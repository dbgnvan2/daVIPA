# Implementation plan — the status claims no one checks (SST)

**Date:** 2026-11-08
**Status:** approved to proceed. The user's instruction for this session was
"proceed on your own recommendations as I'm going to be away … you can then
start on open items", which is the approval gate for this batch. Recorded here
rather than assumed, because the global rule is to stop after the plan.

**Closes:** `BACKLOG.md` `SSC-1` (its second clause), `SSC-2`, `SSC-4`,
`SSC-5`, `SSC-6`, `SSC-7`, `SSC-8`, `SSC-9`, `SSC-10`. `SSC-3` was closed on
2026-11-08 by `8edc0a4`.

## 0. Why this is one batch

The nine open `SSC` filings are one defect wearing nine faces: **a claim that
nothing checks.** A plan heads itself "no implementation code written" over
code that shipped months ago; a spec says "nothing is outstanding" eight lines
above two outstanding items; a coverage row names a method that does not
exist; a count is given as 38, 40 and 41 in three places. None of it is caught,
because every check in this repo reads `Tests:` references and nothing else.

So this batch does two things. It corrects the claims — which is the cheap
half, and the half that rots again. And it adds three guards, so that the next
one fails a test instead of waiting for a sweep to notice.

This is a documentation-and-meta-test batch. **No application behaviour
changes**, no file under `src/` is touched, and nothing here can alter what the
app does.

## 1. Measurements taken before planning

Every figure below is measured at `79adec1`, not recalled.

### 1.1 Documents whose status line claims no code was written

```
grep -rniE "awaiting approval|no implementation code written|no code changed yet|no code written|not built" \
  docs/implementation_plan_*.md docs/spec_2*.md
```

That grep returns **32 lines in 21 documents** at `79adec1`. Seventeen of
those lines, in **sixteen documents**, were stale claims: sixteen of them
status claims, one a prose sentence in a plan that also had a stale status
line. The remaining fifteen lines are not defects — they quote a claim in order
to record that it was corrected, or they say that a *named* criterion was never
built, which is true (`PD-M14.3`, `PD-M14.4`, `PD-M14.7`, `PRI-M3`), or they
are the one registered draft, the CIP spec.

`SSC-4` named four of the seventeen and said "seven further `awaiting
approval` plans were not checked at all, so treat this as a sample, not a
list". They are now all checked. **Every one of the sixteen documents is
implemented**:

| document | the claim | evidence it is built |
|---|---|---|
| `spec_2026-11-08_weekly_tactic_as_parent.md:6` | "awaiting approval. No implementation code written." | its own §6, 41 criterion rows all `done` (this is `SSC-2`) |
| `implementation_plan_2026-11-05_time_blocks.md:3` | "awaiting approval. No implementation code written." | `docs/spec_coverage.md`, 28 `TB-M` rows: 19 `done`, 9 superseded — 8 by the grid, `TB-M8.2` by `PD-M13.1` — none outstanding |
| `implementation_plan_2026-11-05_time_grid.md:3` | "No implementation code is written until this is …" | `docs/spec_coverage.md`, 36 `TG-M` rows, all `done` |
| `implementation_plan_2026-11-08_day_hours_are_a_template.md:4` | "planned, not built — awaiting approval" | PD-M14 is the **surviving** plan-day design; `docs/spec_coverage_2026-11-08_plan_calendar_export.md:24` is headed "after PD-M14 landed". PD-M14.4 alone was never built (PDT batch) |
| `implementation_plan_2026-08-19_item_editor_project_link.md:245` | "awaiting approval — no implementation code written." | `docs/spec_coverage_2026-08-19_item_editor_project_link.md`, 33 `done` rows |
| `implementation_plan_2026-08-24_dopamine_reward_protocol.md:5` | "Awaiting approval — no implementation code written yet." | `src/getmoredone/reward_protocol.py` exists |
| `implementation_plan_2026-08-24_dopamine_reward_protocol.md:291` | "No implementation code has been written." | same; this one is prose, not a status line |
| `implementation_plan_2026-08-18_weekly_tactic_scheduling.md:3` | "Draft, awaiting approval. **No implementation code written.**" | `docs/spec_coverage_2026-08-18_weekly_tactic_scheduling.md`, 83 `done` rows |
| `spec_2026-08-18_weekly_tactic_scheduling.md:3` | "Draft v2, awaiting approval" | same |
| `implementation_plan_2026-08-19_rename_safe_links.md:3` | "Draft, awaiting approval. **No implementation code written.**" | `docs/spec_coverage_2026-08-19_rename_safe_links.md`, 17 criterion rows carrying 15 distinct `RN-M` IDs (`RN-M2.A` and `RN-M4.A` appear twice), every one "Collected: yes" against a real collection run. **Corrected 2026-11-09 by the cold pass**, which measured it; the figure here was 35, which is neither the rows nor the IDs: `grep -cE '^\| *RN-M' docs/spec_coverage_2026-08-19_rename_safe_links.md` |
| `spec_2026-08-19_rename_safe_links.md:3` | "Draft v1, awaiting approval" | same |
| `implementation_plan_2026-08-24_window_leak.md:4` | "Awaiting approval — no code changed yet." | `conftest.py:800` is F3's fix (raw `tkinter` windows patched, not only the two `ctk` classes) |
| `implementation_plan_2026-08-18_downloadable_release.md:4` | "Awaiting approval. No implementation code written yet." | `build_mac.sh`, `daVIPA.spec`, `tests/test_release_docs.py`, `tests/test_release_licensing.py` |
| `spec_2026-08-18_downloadable_release.md:3` | "Draft, awaiting approval" | same |
| `implementation_plan_2026-08-26_backlog_clearance.md:4` | "awaiting approval — no code written" | `tests/test_timer_session_endings.py:560` asserts B4's `NextStepsDialog` deletion |
| `spec_2026-11-05_demo_install.md:3` | "Draft v1, awaiting approval" | `docs/spec_coverage_2026-11-05_demo_install.md`, 46 `done`, 1 `not done` |
| `implementation_plan_2026-06-06_project_notes.md:152` | ready for approval, nothing written, M1 awaiting a sign-off | `docs/spec_coverage.md`'s first table is this plan's coverage: 25 `M…` rows, all `done`. **Added 2026-11-09 by the cold pass.** The grep above returned this line and the triage dropped it; it was then outside the guard as well, because the claim sits under a `## Status` heading rather than on a line starting "Status" |

Two more documents match the grep and are **not** defects, so they are not in
the table: `implementation_plan_2026-11-08_priority_defaults_and_cap.md:4` and
`implementation_plan_2026-11-08_pri_tests.md:101` both quote the wrong claim in
order to record that it was corrected, and `docs/DOCUMENTATION_INDEX.md` does
the same (`grep -in "awaiting approval; no" docs/DOCUMENTATION_INDEX.md`).

### 1.2 The WTP criterion count (`SSC-6`)

```
grep -E '^\| *\*{0,2}WTP-M[0-9]' docs/spec_2026-11-08_weekly_tactic_as_parent.md \
  | sed -E 's/^\| *\*{0,2}(WTP-M[0-9.]+[a-z]?)\*{0,2}.*/\1/' | sort -u | wc -l
```

**41**, and §3's table and §6's table hold the *same* 41 — measured by
comparing the two sorted sets, which are identical. Forty-seven `WTP-M…`
strings appear in the file; the extra six are the section headings `WTP-M1` to
`WTP-M6`, which are groups, not criteria.

So **41 is right**, 40 and 38 are both wrong, and the spec's arithmetic for 40
("the 35 in §3, plus WTP-M1.7, …") is stale in its first term: §3 was amended
to carry the additions, so it holds 41, not 35, and adding them again
double-counts. `SSC-6` declined to certify any of the three figures; this
measurement certifies 41.

### 1.3 The method that does not exist (`SSC-7`)

`grep -rn "def _update_action_item" src/ tools/` prints **nothing**. The
`RP-2.5` row in `docs/spec_coverage.md` (`grep -n '| RP-2.5 |'
docs/spec_coverage.md`) names
`db_manager.py::_update_action_item` in its Implementation column. Nothing
checks that column: `tests/test_traceability_refs.py` reads `tests/…` paths
only.

### 1.4 Line-number cites (`SSC-10`)

```
grep -rnE '(BACKLOG\.md|docs/spec_coverage\.md|CLAUDE\.md|docs/DOCUMENTATION_INDEX\.md):[0-9]' \
  --include='*.md' --exclude-dir=.claude .
```

**10** lines at `79adec1`.

## 2. Acceptance criteria → tests

| ID | Criterion | How it is verified |
|---|---|---|
| SST-M1 | Every one of the fifteen stale status lines in §1.1 states what is built and what is not, and names the evidence | `test_sstm1_no_document_claims_unwritten_code_outside_the_register` |
| SST-M2 | A document may claim "no implementation code written" only if it is in an explicit register, and every register entry still carries the claim | `test_sstm1_…` (set equality, both directions) and `test_sstm2_the_register_guard_can_fire` |
| SST-M3 | The WTP count is stated as 41 everywhere it is stated: the spec's §6 summary and `BACKLOG.md`'s header paragraph | `test_sstm3_the_wtp_criterion_count_is_what_the_spec_lists` — recounts the spec's rows and asserts the figure in the prose matches |
| SST-M4 | The WTP spec does not say nothing is outstanding while listing two outstanding items | part of `test_sstm3_…`; the prose assertion reads the sentence |
| SST-M5 | Every `file::symbol` named in an Implementation column of a coverage document resolves to a definition in `src/` or `tools/` | `test_sstm5_every_implementation_reference_resolves` plus `test_sstm5_that_guard_can_fire` |
| SST-M6 | `PLC-A5`'s first clause no longer asserts a footer that was rewritten | read-only check in the cold pass; no test (prose) |
| SST-M7 | `UPD-A13` and `PLC-A5` name each other, so a reader landing on either reaches the designed fix | `test_sstm7_the_two_filings_of_the_index_gap_cross_reference` |
| SST-M8 | No markdown document cites `BACKLOG.md`, `docs/spec_coverage.md`, `CLAUDE.md` or `docs/DOCUMENTATION_INDEX.md` by line number | `test_sstm8_the_chronic_documents_are_not_cited_by_line_number` |
| SST-M9 | `PRI-A1` to `PRI-A4`, which the PRI plan promises and the index repeats, exist in `BACKLOG.md` | `test_sstm9_every_promised_pri_adjacent_item_is_filed` |
| SST-M10 | The batch's own records exist: `docs/spec_coverage.md` SST section, handoff note, `BACKLOG.md` closures, `NOTES.md`, `docs/DOCUMENTATION_INDEX.md` | `test_sstm10_every_record_of_this_batch_exists_and_names_it` — added 2026-11-09 by the second cold pass. This read "the index's own entry, and the docs-sync gate", which cannot produce a `done`: `tools/agents/check_docs_sync.py` only asserts that *some* path under `docs/` changed, and its workflow runs on `pull_request`, which this repo never opens (`SST-A8`) |

### Not code-testable

- **That a corrected status line is *true*.** The register guard proves no
  document claims unwritten code outside the register; it cannot prove the
  replacement sentence describes the code accurately. The evidence column in
  §1.1 is the human-reviewable part, and the cold pass re-measures it.

## 3. Implementation order

1. The three guards first, red against the current tree — a guard written
   after the fix is a guard nobody has seen fail.
2. The seventeen stale lines (SST-M1), which turns the register guard green.
3. The counts, the method name, the cross-references, the cites.
4. `PRI-A1`–`PRI-A4` filed.
5. Records: `docs/spec_coverage.md`, `BACKLOG.md`, `NOTES.md`,
   `docs/DOCUMENTATION_INDEX.md`, handoff note.
6. One cold pass, per the sweep budget. No warm pass beyond writing the work.

Tests commit separately from the documents, per the repo rule.

## 4. Risks

- **The register becomes the new rot.** A plan genuinely awaiting approval must
  be added to it, and removed when built. That is a step in the process, and
  the guard's second direction (every entry still carries the claim) is what
  stops a stale entry sitting there forever.
- **SST-M5 narrows silently.** The Implementation columns are prose, not a
  schema; only `::`-form references are machine-readable. The guard asserts the
  exact number of references it found, so a pattern change that stops matching
  shows up as a failure rather than as a pass.
- **SST-M8 is a style rule with teeth.** It will fail a document that cites a
  line number for a good reason. That is the intent — the rule was adopted on
  2026-11-08 after a cite moved in the same commit that wrote it.

## 5. Adjacent issues found, not fixed

- `tests/test_traceability_refs.py:112` asserts `len(found) >= 140`, a floor,
  in a comment that calls it "An exact floor, not 'more than 20'". The repo's
  test rule says exact counts, never floors. It is a floor. Filed rather than
  fixed: an exact count there turns every added docstring reference into a red
  suite, which is a call for the user, not for this batch. **Measured at
  `79adec1`: 784 references.** The floor is 140, so the guard written to catch
  a 15% narrowing would now tolerate the deletion of 644 of the 784 — 82% of
  its own domain — and still pass. Filed in `BACKLOG.md` as `SST-A1`, at
  medium, because the number makes it more than cosmetic.
