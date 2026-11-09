# Implementation plan — the status guard as an allow-list, and the gate that never runs (SAG)

**Date:** 2026-11-09
**Status: approved under the standing instruction and built the same day.** The
user's instruction for this session was "proceed on your own recommendations as
I'm going to be away … you can then start on open items", which is the approval
gate for this batch. Recorded here rather than assumed, because the global rule
is to stop after the plan.

**Closes:** `BACKLOG.md`'s `SST-A3` (high) and `SST-A8` (medium).

## 0. Why these two together

Both are the same defect in two places: **a check that cannot fail on the thing
it was written for.**

`SST-A3` is a deny-list of twelve phrasings. Three cold passes each found
documents it could not see, and each was answered by lengthening the list — the
same patch three times. `SST-A8` is a check that exists only in a workflow
triggered on `pull_request`, in a repo whose standing instruction is to open
none, so it has never run on the way work ships here.

They are one batch because they are one decision applied twice: a check belongs
where it fails before a push, and it has to reject by default rather than
accept by default.

## 1. What was measured first

### 1.1 The document family, and what its status lines say

`grep`-free measurement, by the same globs the guard uses
(`docs/implementation_plan_*.md` and `docs/spec_*.md`, minus `spec_coverage*`):
**36 documents** when measured, **37** once this plan was committed into the
family it measures — the glob counts the plan too, which is worth stating
because the table below adds to 36 and will not add to the tree again. Classified against a prototype allow-list:

| | count |
|---|---|
| status claim leads with a recognised built form | 30 |
| registered draft (`docs/spec_2026-11-08_calendar_into_the_plan.md`) | 1 |
| **unrecognised — would fail** | **5**, and **6** as built |

So the convention `SST-A3` describes as "imposed on 35 existing documents"
costs **six edits**, not 35. That is the measurement that makes this worth
doing now rather than filing again.

The prototype that produced this table recognised a sixth form, "Batch 1
complete (…)", for one document. The built guard does not: four forms that
each say what state the work is in are better than six, one of which exists
for a single 2026-08-19 plan, so that plan's status line was reordered like
the four below it. The count above is left as the prototype measured it, with
the correction stated here rather than edited in. The six:

1. `docs/implementation_plan_2026-06-22.md` — **no status line at all.** The
   one document in the family with none, so no reader can tell what state it is
   in. Measured: its feature is built. `src/getmoredone/screens/column_resize.py`
   holds `ColumnResizer`, `screens/drag_schedule.py` builds one with
   `prefix="drag_schedule"`, `app_settings.py` carries
   `drag_schedule_col_widths`, and persistence is asserted by
   `tests/test_column_resize.py::test_persist_round_trips_over_dirty_state`,
   with `::test_legacy_title_scalar_is_honoured_when_dict_missing` and
   `::test_width_is_clamped_to_spec_bounds_on_load` for the load side.
   (Corrected twice on 2026-11-09. It first named two
   `tests/test_settings_merge_on_save.py` tests, which cover the five VSP panel
   prefixes and reach `drag_schedule_col_widths` nowhere; the correction then
   changed the **file** and left the **test names**, so for one pass it cited
   `test_updf13_all_five_tabs_persist_their_own_widths` and
   `test_updf14_stored_widths_are_what_the_resizer_reports` against
   `tests/test_column_resize.py`, which has neither. Named here without
   their paths, which is the convention `tests/test_traceability_refs.py`
   enforces for a test that does not exist.
   Both measured by cold passes, the second and the fifth.)
2. `docs/implementation_plan_2026-08-19_backlog_clearance.md` — "Batch 1
   complete (2026-08-19). Batch 2 complete (2026-08-19)." The state is there,
   as batches rather than as a state of the work.
3. `docs/implementation_plan_2026-11-06_plan_day_controls.md` — leads with
   `PD-M1 … PD-M6 shipped`, so the state is there but the sentence begins with
   an ID list.
4. `docs/implementation_plan_2026-11-08_status_claims.md` — leads with
   "approved to proceed", written before the batch was built. It is built; the
   line was never updated. **This is SST's own plan, and the defect SST exists
   to catch.**
5. `docs/implementation_plan_2026-11-08_unified_panel_followups.md` — leads
   with "approved 2026-11-08", with the build claim in the second sentence.
6. `docs/spec_2026-11-07_unified_panel_design.md` — the same shape.

Items 2 to 6 are reorderings: every one of them already states the build state
somewhere in the status text. Item 1 is a new status line, and its content is
the measurement above rather than a guess.

Item 4 is worth naming for what it is. `docs/implementation_plan_2026-11-08_status_claims.md`
is **SST's own plan**, and it recorded an approval over a batch that had
shipped the day before. The deny-list SST built could not see it, because an
approval state contains no phrase saying the work is unwritten. That is the
clearest case for the inversion, and it is in the document that built the
deny-list.

### 1.2 Where the three passes' findings actually were

Every stale claim the deny-list missed was in the document's **first** status
claim — the `**Status:**` line at the top, or the first line of its `## Status`
section. That is what sets the scope in §2: the allow-list applies to the first
claim, which is the one a reader reads for the current state. Later status
lines keep the deny-list as a tripwire, and §4 records that residue rather
than implying the whole surface is inverted.

### 1.3 The docs-sync checker, read rather than assumed

`tools/agents/check_docs_sync.py` has a `main()` that takes `--base`/`--head`
and three things that matter here:

- Its decision is a pure function of a **set of changed paths** — code
  prefixes, dependency files, doc prefixes, a handoff note under
  `docs/changes/`. Nothing about that needs git.
- The git part is one call, `git diff --name-only base...head`, and on failure
  `main()` prints "docs-sync check skipped" and **returns 0**. A missing base
  ref is a pass.
- `.github/workflows/tests.yml` checks out with `actions/checkout@v7` and no
  `fetch-depth`, so `origin/main` does not exist in a CI checkout. A test that
  asked the real range would therefore skip on CI — the same shape as the batch
  before this one.

So the test has to be over the decision, not over the range. That is the
judgement `SST-A8` says was missing.

## 2. Acceptance criteria → tests

Spec IDs are this plan's own, `SAG-M*`, and every test name carries the ID it
verifies. Tests live in `tests/test_doc_status_claims.py` (M1, M3) and
`tests/test_docs_sync_rule.py` (M2, new).

| ID | criterion | test |
|---|---|---|
| SAG-M1.1 | A document's first status claim must **match** one of a named set of recognised forms; an unrecognised sentence fails. The forms are `superseded`, `draft`, `not-built` and `built`, tried in that order, each a named pattern rather than one long alternation. (This criterion said **five** forms, `built`, `approved-and-built`, `partly-built`, `superseded` and `draft`, which is the shape built first and rewritten twice by cold passes — the three built forms are one, and `not-built` was added. The criterion is restated rather than the history edited out; `docs/spec_coverage.md` has what each pass changed and why) | `::test_sagm11_every_status_claim_matches_a_recognised_form` |
| SAG-M1.2 | The sentence `SST-A3` was filed for — "Draft, implementation not scheduled. No code exists yet." — fails, and so does a status claim that is merely an approval ("approved; in progress") | `::test_sagm12_an_unrecognised_status_claim_is_rejected` |
| SAG-M1.3 | A document whose first claim is a draft form must be in `DRAFTS_NOT_BUILT`, and a registered document whose claim has become a built form must leave the register — both directions, as before | `::test_sagm13_the_draft_register_holds_both_directions` |
| SAG-M1.4 | A document in the family with **no** status claim fails | `::test_sagm14_a_document_with_no_status_claim_fails` |
| SAG-M1.5 | The form patterns are asserted against text, including the two that must **not** match: a built word reached only after a negation ("not built"), and a built word in the middle of a draft sentence | `::test_sagm15_the_forms_reject_a_built_word_after_a_negation` |
| SAG-M2.1 | The docs-sync decision is a pure function of a set of changed paths, and the suite asserts it over fixtures: code without docs fails, code without a handoff note fails, docs-only passes, a dependency-file-only change is code | `tests/test_docs_sync_rule.py::test_sagm21_the_docs_sync_rule_decides_on_paths_alone` |
| SAG-M2.2 | `requirements-dev.txt` alone counts as a dependency change — the case the tool's own comment records as a miss | `::test_sagm22_a_dev_dependency_alone_is_a_code_change` |
| SAG-M2.3 | An unavailable git range is reported as **skipped**, not as a pass, and the suite asserts which of the two happened rather than reading the exit code alone | `::test_sagm23_an_unavailable_range_is_skipped_not_passed` |
| SAG-M2.4 | Every outcome `verdict` can return has a fixture, so the suite asserts the whole decision and not a sample of it — and `verdict` must return the named constants rather than inline strings | `::test_sagm24_every_outcome_the_tool_can_return_has_a_fixture` |
| SAG-M3.1 | The six documents of §1.1 carry a status claim in a recognised form, and each names its evidence | the six documents; `SAG-M1.1` is what holds them |
| SAG-M3.2 | `docs/implementation_plan_2026-06-22.md`'s new status line is true — the resizable-column work is built | review, against the modules and tests named in §1.1 |
| SAG-M4.1 | A `tests/…::name` citation in a plan, spec or handoff note must resolve, not only one in a coverage row. Added after the fifth cold pass: its high was a dead citation in a plan, and `tests/test_traceability_refs.py`'s scan stopped at `docs/spec_coverage*.md`, so the guard could not see it | `tests/test_traceability_refs.py::test_every_referenced_test_name_exists`, `::test_every_referenced_test_file_exists`, `::test_this_guard_can_actually_fire` |
| SAG-M4.2 | The resolver accepts a module constant, a helper and a spec-ID prefix of a family — the forms these documents really use — and still rejects a truncation of a name that does not exist | `::test_this_guard_can_actually_fire`, both directions |
| SAG-M4.3 | Every dead reference the widened scan exposes is repaired: a renamed test re-cited, one that no longer exists named in plain backticks without its path | `::test_every_referenced_test_name_exists` |
| SAG-N1 | **Not code-testable:** that a recognised built claim is **true**. `SST-N1` already says this; inverting the check does not change it. The guard proves the claim is a recognised form, not that the work exists | human-verified, per document, in §1.1 |

## 3. Implementation order

1. `SAG-M2` first — it is independent of the document edits and the new test
   file cannot break anything else.
2. `SAG-M1`, with `SAG-M3`'s six document edits in the same step: the guard
   and the documents it rejects have to move together or the suite is red in
   between.
3. Mutations, then one cold pass, then the records.

## 4. Risks, and what this does not close

- **The allow-list is still a judgement about wording, not about truth.**
  `SAG-N1`. A document that says "built and on `main`" over nothing at all
  passes. What changes is the default: silence, an approval state, or a new way
  of writing "not built" now fails instead of passing.
- **Only the first status claim is inverted.** Later status lines, and prose
  inside a `## Status` section below its first line, keep the deny-list as a
  tripwire. §1.2 is the reason — every finding of three cold passes was in the
  first claim — but it is a scope decision and not a closure, and it is filed
  as `SAG-A1` rather than left implicit.
- **A reordering can lose content.** The five status lines of §1.1 items 2 to 6
  are dense; the edit must move the build state to the front without dropping
  the exceptions each of them records (PD-M12 superseded, UPD-M7.2 `partial`,
  UPD-M7.3 `not done`). That is what makes `SAG-M3` a criterion rather than a
  cleanup.
- **`check_docs_sync.py` returning 0 on a missing ref is a defect in the
  tool.** `SAG-M2.3` asserts the current behaviour is *reported* honestly
  (skipped, not passed); changing the return code is a change to a tool the
  workflow calls, which is a second decision and is filed rather than taken
  here.

## 5. Adjacent issues found, not fixed

Flagged per rule 10:

1. **`_STATUS_LINE` matches any line beginning with "status".** Measured:
   `docs/implementation_plan_2026-08-25_project_time_totals.md` has a prose
   line beginning "status was added 2026-11-09 by the third cold pass", which
   the old guard read as a status line and only let through because it contains
   no deny-list phrase. An allow-list over *every* status line would fail on
   it. This is why §2 scopes `SAG-M1` to the first claim, and the pattern's
   looseness is `SAG-A2`.
2. **The gate workflow still exists and still runs on nothing.** Once
   `SAG-M2` puts the assertion in the suite,
   `.github/workflows/agent-docs-gate.yml` is a second surface for the same
   check, triggered on an event this repo does not produce. Deleting it is
   right and is not this batch's call to make: `SAG-A3`.
