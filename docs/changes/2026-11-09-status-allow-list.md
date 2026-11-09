# Handoff Note

- Date: 2026-11-09
- Agent: Code
- Topic: status-allow-list — the status guard inverted, and the docs-sync rule put in the suite

## Summary

Two filings closed, `SST-A3` (high) and `SST-A8` (medium). Both are about a
check that cannot fail on the thing it names, which is why they are one batch.

**`SAG-M1` — the status guard is now an allow-list.**
`tests/test_doc_status_claims.py` matched a document's status claim against
`_NOT_BUILT`, a list of twelve "not built" phrasings. Three cold passes each found
documents it could not see, and each was answered by lengthening the list — the
same patch three times. A phrase list can only reject a wording someone has
already met, so an approval state ("approved; in progress" over 55 passing
tests), a question, a new phrasing, and **silence** all passed.

`classify_status_claim` reverses the default. A claim must match one of four
recognised forms — `superseded`, `draft`, `not-built`, `built`, tried in that
order — over one shared `_BUILT` vocabulary, with a negation check before the
match and a cancellation check after it for `built`, the one form that claims
the work exists. An unrecognised sentence fails. An unbuilt claim must be registered in
`DRAFTS_NOT_BUILT`, and a registered document whose claim becomes a built form
must leave the register, so the register cannot go stale in either direction.

A **built** claim is one of four named shapes (`_BUILT_SHAPES`): it leads with
the state ("built and on `main`"), or only digits and punctuation come first
("2026-11-10 — built and on `main`."), or the built word is a predicate ("M1, M2
and M3 are built."), or an approval and a build are in one sentence ("approved
2026-11-08 and built."). Nothing else is a built claim, and `built` is tried
last because it is the only form that need not match at position 0.

That shape list is the third version of this form, and the two it replaced are
worth stating, because each was a cold pass's own fix: three forms with three
prefixes enumerating permitted punctuation, then a built word anywhere in the
first sentence, then this.

`SST-A3` put the cost at "a convention imposed on 35 existing documents".
Measured, it is **six** document edits: 30 of the 36 documents in the family
already carried a claim one of the four forms recognises. The sixth was found
only because the inversion makes a *missing* claim fail —
`docs/implementation_plan_2026-06-22.md` had no status line at all, for five
months, which is the failure mode no phrase list can have.

**`SAG-M2` — the docs-sync rule now fails before a push.**
`tools/agents/check_docs_sync.py` held its whole decision inside `main()`, and
the only thing that ran it was `.github/workflows/agent-docs-gate.yml`, which
triggers on `pull_request`. This repo opens none, so the rule had never run
here. The decision is extracted into `verdict(files)`, a pure function of
changed paths returning one of five declared outcome names, and
`tests/test_docs_sync_rule.py` asserts all of them over fixtures.

The test deliberately does **not** ask git for the push range. `tests.yml`
checks out at depth 1 and has no `origin/main`, so a test that asked would skip
on CI — the shape this repo has been bitten by twice. To apply the rule to real
changes, run `./venv/bin/python tools/agents/check_docs_sync.py` by hand; a
range it cannot read is reported as *skipped*, never as a pass.

**`SAG-M3` — the six documents.** Each now carries a recognised claim that
names its evidence. Two were claiming less than was true:
`docs/implementation_plan_2026-11-08_status_claims.md` — the SST batch's own
plan — said only "approved to proceed" over shipped work, and
`docs/implementation_plan_2026-06-22.md`'s new line names
`screens/column_resize.py` and the `tests/test_column_resize.py` tests that
prove it. That citation was wrong when first written — it named two
`tests/test_settings_merge_on_save.py` tests, which cover the five VSP panel
prefixes and reach `drag_schedule_col_widths` nowhere — and was corrected in
all four records by the second cold pass.

`CLAUDE.md`'s docs-gate paragraph is rewritten to say where the rule now lives,
that the suite does not diff your branch, and that `agent-docs-gate.yml` still
runs on nothing (`SAG-A3`). Its marker test counts are re-measured: **2439** app
and **243** meta, against the 2432 and 225 the SST batch measured. Only the meta
figure moved with this batch — every test here is in a meta-marked file; the app
delta is `c190b9f`'s, already on `main`.

## Files changed

- `tools/agents/check_docs_sync.py` — `verdict()` extracted; `OUTCOMES`,
  `PASSING` and the five outcome names declared; `main()` reduced to reading the
  range, calling `verdict`, printing and deriving an exit code
- `tests/test_docs_sync_rule.py` (new) — 4 tests, 10 path fixtures
- `tests/test_doc_status_claims.py` — the `SAG-M1` block: `_BUILT`,
  `_STATUS_FORMS`, `_NEGATION`, `_CANCELLED`, `_strip_status_label`,
  `classify_status_claim`, and 5 tests
- `tests/test_ci_contract.py` — the new meta file added to `META_TEST_FILES`
- `tests/test_traceability_refs.py` — `SAG-M4`: the scan widened to
  `docs/implementation_plan_*.md`, `docs/spec_*.md` and `docs/changes/*.md`,
  the file walk deduplicated, `_test_names` replaced by `_defined_names` plus
  `_resolves`, and the guard-the-guard test given membership assertions for
  each new arm and both directions of the prefix form
- `tests/test_release_licensing.py` — `test_bi2_…` rewritten under test rule (c)
  (over-specified about *where* the dependency enumeration is read)
- `docs/implementation_plan_2026-11-09_status_allow_list.md` (new) — the plan
- `docs/implementation_plan_2026-06-22.md`,
  `docs/implementation_plan_2026-08-19_backlog_clearance.md`,
  `docs/implementation_plan_2026-11-06_plan_day_controls.md`,
  `docs/implementation_plan_2026-11-08_status_claims.md`,
  `docs/implementation_plan_2026-11-08_unified_panel_followups.md`,
  `docs/spec_2026-11-07_unified_panel_design.md` — the six status lines
- `SAG-M4.3`'s eleven repaired documents:
  `docs/implementation_plan_2026-06-06_project_notes.md`,
  `docs/implementation_plan_2026-08-19_item_editor_project_link.md`,
  `docs/implementation_plan_2026-08-26_backlog_clearance.md`,
  `docs/implementation_plan_2026-11-05_time_blocks.md`,
  `docs/implementation_plan_2026-11-06_plan_day_controls.md`,
  `docs/implementation_plan_2026-11-08_pri_tests.md`,
  `docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md`,
  `docs/implementation_plan_2026-11-09_status_allow_list.md`,
  `docs/changes/2026-04-03-project-drag-schedule.md`,
  `docs/changes/2026-08-18-downloadable-release-phase3.md`
  (and `docs/implementation_plan_2026-06-06_project_notes.md`'s file-list row)
- `docs/spec_coverage.md` — the `SAG` section
- `BACKLOG.md` — `SST-A3` and `SST-A8` closed; `SAG-A1`–`SAG-A18` filed
  (`SAG-A17` and `SAG-A18` by the sixth cold pass), and `PDT-A1` marked as
  superseded in scope by `SAG-A17`
- `docs/DOCUMENTATION_INDEX.md`, `NOTES.md`, `CLAUDE.md`

No file under `src/` is touched.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b
  ./venv/bin/python -m pytest tests/test_doc_status_claims.py
  tests/test_docs_sync_rule.py tests/test_release_licensing.py
  tests/test_ci_contract.py -q`
- Result: PASS — 144 passed, 1 skipped over those four files; 147 passed,
  1 skipped with `tests/test_traceability_refs.py`, which reads the records
  this batch writes and which `SAG-M4` changed. The count did not move when
  `SAG-M4` landed: it widens an existing guard's domain and adds assertions
  inside `::test_this_guard_can_actually_fire`, not new test functions, so the
  marker figures in `CLAUDE.md` still hold.
- Mutations: **31**, each restored with the verbatim original and the restore
  confirmed by sha256. Seven cover the criteria (AG–AM); the other sixteen
  cover the cold passes' own fixes — six for the first (AN, AO, AO2, AP, AQ,
  AR), five for the third (AS, AT, AU, AV2, AW3), five for the fourth (AX2, AY,
  AZ, BA, BB), five for the fifth (BC–BG) and three for the sixth (BH–BJ) —
  per the rule that every in-loop fix is in scope for the next
  pass. **Three were not red first time, and that is the useful part:** AW2
  expected a dead alternative that was in fact reachable, AX did not move what
  it claimed to move, and BB came back **green** because the table fix had been
  written with no test. Listed with results in `docs/spec_coverage.md`.
- The whole suite was not run locally, by standing instruction. CI ran it on
  push: **run 42608198985 at `f1ff868` is green on 3.11, 3.12 and 3.13** —
  `2672 passed, 10 skipped` on each. That total is the one check on this
  batch's marker arithmetic that does not come from this batch: 2672 + 10
  collected is **2682**, and the figures `CLAUDE.md` now carries, 2439 app and
  243 meta, add to exactly that.

## Risks / Known gaps

- **`SAG-N1` carries `SST-N1` forward unchanged.** The guard proves a claim is
  a recognised form, not that the work exists. A document saying "built and on
  `main`" over nothing still passes. What changed is the default, not the
  judgement.
- **Two highs came from the first cold pass over this batch**, both in the
  batch's own test code. The new meta file was missing from
  `tests/test_ci_contract.py`'s enumeration, so the batch left an unrelated
  guard red; and `test_sagm24` carried its own hardcoded list of five outcome
  names and filtered the AST walk by it, making a sixth outcome invisible to
  both sides of its comparison — it passed with the sixth unfixtured and failed
  once the fixture was added. Three mediums followed: `partly-built` rejected
  the comma, slash and bracket spellings this repo writes ID lists with;
  `_strip_status_label` left a leading dash, so four spellings of the repo's
  commonest status style matched no form; and the negation window looked only at
  the match, so "Done nothing yet." was accepted.
- **`SAG-A8` is a hole the suite currently passes over.** "Complete rewrite
  proposed. No code yet." still classifies as `built`, because a built word can
  be read adjectivally.
  `test_sagm15_the_forms_reject_a_built_word_after_a_negation` **asserts** that,
  with a message saying so, so closing `SAG-A8` turns the assertion red on
  purpose.
- **`SAG-A1`** is the one medium filed and not fixed: only a document's *first*
  claim is read, and this repo writes per-milestone claims further down.
- **The third cold pass, in the "green anywhere but this machine" family, found
  four mediums and no high — all four latent, none red today, and all four the
  same class: the guard rejecting correct future work.** It also found nothing
  that will make CI red, checked against a depth-1 checkout on 3.11/3.12/3.13
  with no `origin/main` and no mapped-window variable, and nothing that depends
  on state on this machine.
  - The enumerated prefix had already been widened once and still rejected
    `"SAG-M1 & SAG-M2 are built."`, ``"`SAG-M1`: both halves are built."``,
    `"All criteria done."` and `"2026-11-10 — built and on `main`."`.
    Enumerating punctuation cannot be finished, which is the same argument that
    replaced the deny-list, so the three built forms are now one shape. Four
    forms instead of five, and one rule a reader can state.
  - `not approved` was an alternative of the `draft` form that nothing could
    reach: the negation check discarded the match before it was returned. The
    negation and cancellation checks now apply only to the forms that claim the
    work exists, because a negation is what the unbuilt forms are made of.
  - The two guards disagreed about what an unbuilt status looks like. Ten of the
    twelve phrasings `_NOT_BUILT` accepts as a registerable claim classified as
    `None`, so a document registered exactly as the register's own comment
    instructs was red under `SAG-M1.1` with no way to register out. That
    vocabulary is now the `not-built` form.
  - The double bind: `Status: Draft.` classifies as `draft`, so `SAG-M1.3`
    required registration, and registering it made `test_sstm2` red because the
    deny-list does not accept "Draft." alone. The register's contract is now one
    function, `registered_claim_is_unbuilt`, that both guards call, pinned by an
    assertion over a document the test writes — the one really registered
    document satisfies both vocabularies and so cannot show the difference,
    which is why the bind survived three passes.
  - Five mutations on these fixes, all red. A sixth, AW2, was **wrong**: it
    expected a dead alternative and left the guard green, correctly, because
    the alternative is reachable now. AW3 replaces it. Both are in
    `docs/spec_coverage.md` rather than only the one that worked.
  - The pass's own `len(alternatives) > 1` suggestion is not in the fix: this
    repo forbids `> N` floors. The loop asserts the pattern parsed and then
    checks every alternative it found.
  - Six lows from that pass are **not fixed**: three further vocabularies that
    a future document might use (`superseded` recognises three words, an
    approval-only state has no form on purpose, `_STATUS_LINE` matches any line
    beginning "status" — already `SAG-A2`), the glob reaching a future
    `docs/spec_template.md`, `test_sagm23`'s "skipped" substring not
    distinguishing an unreadable range from a missing git, and `run()`'s
    missing subprocess timeout (P5). Filed as `SAG-A9`–`SAG-A12`.
- **The fourth cold pass, over the classifier rewrite alone, found two highs
  and three mediums — all five in the third pass's own fix.** This is the
  budget's own warning measured: the fix commit is the least-reviewed code in
  any change.
  - **H1, a false accept.** `"Spec complete, implementation not started."`,
    `"Design done, no code yet."`, `"Planning complete, nothing written yet."`
    and `"Review complete, implementation deferred."` all classified as
    `built`. The built word belongs to the spec or the review and the sentence
    says the code does not exist. `_NOT_BUILT` lists "not started" and "no code
    written", so **the deny-list this guard replaces would have caught the
    first two**: the inversion was weaker than the list on precisely the
    sentences `SST-A3` is about.
  - **H2, shadowing.** `built` was the only form that need not match at
    position 0, and it was tried first, so a claim that leads with its state —
    which is what the guard's own failure message tells authors to do — was
    reclassified: `"Draft — design complete, awaiting approval"` and
    `"Awaiting approval; the spec is complete"` were both `built`.
  - The fix for both: the unbuilt forms are tried first, and `built` is
    anchored again as four named shapes. Four claims the third pass accepted
    are now rejected on purpose — `"All criteria done."` and `"PD-M1 built,
    PD-M2 outstanding."` among them — because failing loudly is the right
    direction when a sentence is ambiguous: `"All criteria are done."` is shape
    (c) and passes.
  - Three mediums, all fixed: a `Status` line inside a fenced example was read
    as the document's own claim, in both directions (no document has one today,
    and these documents quote the handoff-note template); a list marker before
    the label left the label in place, so `"- **Status:** Draft."` matched no
    anchored form; and a `## Status` section opening with a criterion/state
    table had its header row read as the claim.
  - Five mutations, all red — after two were caught not being mutations at all:
    AX did not move what it claimed to move, and BB was **green** because the
    table fix had been written with no test. Both are recorded in
    `docs/spec_coverage.md`.
  - Five lows not fixed, filed as `SAG-A13`–`SAG-A16`: `without` cancelling a
    built claim, three near-synonyms of `superseded`, no reachability loop over
    `_BUILT` or `_NEGATION_WORDS`, and a misleading message when the
    alternative-parsing loop meets a nested group.
- **The second cold pass, in the records-vs-code family, found one high and four
  mediums — every one of them in this batch's own records, not in its code.**
  All five fixed in-loop, with what was wrong recorded where the wrong claim
  was, not edited out:
  - The high: `SAG-M3.2`'s new status line cited two
    `tests/test_settings_merge_on_save.py` tests as the evidence that Scheduler
    column widths persist. Those tests iterate the five VSP panel prefixes and
    reach `drag_schedule_col_widths` nowhere (`grep -n drag_schedule
    tests/test_settings_merge_on_save.py` returns nothing); the evidence is in
    `tests/test_column_resize.py`. The feature is built either way — that was
    verified in `src/` — but a criterion recorded `done` rested on a citation
    that did not reach its subject, which is `SST-M5`'s defect class committed
    by the batch that closes it. Corrected in four places.
  - `CLAUDE.md`'s new app-test figure, 2439, was attributed to this batch in
    four records. Every test here is in a meta-marked file, so the batch adds no
    app test; the +7 is `c190b9f`'s, already on `main`.
  - `SAG-M3.1` claimed the six documents each name their evidence. Nothing
    asserts that and two of the six do not, so the criterion is narrowed to what
    `test_sagm11` actually checks.
  - `SAG-A2` and `SAG-A6` each gave a false reason: a document in the family
    *does* start a prose line with "status", and the docs-sync fixtures prove a
    handoff note alone *does* satisfy the docs requirement, not that it does
    not.
  - Five lows were also fixed rather than filed, because all five are errors in
    text this batch itself wrote: `_NOT_BUILT` holds twelve phrasings and four
    records said ten; the test file's docstring still said "seven guards" after
    the batch added five; a parenthetical claimed three dates in a line showing
    two; `SAG-A4` described an assertion on `main`'s exit code that does not
    exist (nothing covers that line at all, which is now in the filing); and the
    new index entry ran into the next heading with no blank line.

## Next agent actions

- **The sweep is closed at six cold passes.** The sixth produced three
  mediums and four lows and **no high**, which is where the budget stops. Its
  three mediums were fixed in-loop: `SAG-A17` filed with the two instances it
  found repaired by hand (`docs/implementation_plan_2026-11-05_time_blocks.md`
  TB-M2.2 and TB-M2.3, dead bare names on the rows directly above the one
  `SAG-M4.3` repaired); the two live test-file paths this batch had stripped
  from `docs/implementation_plan_2026-11-08_pri_tests.md` put back, with the
  reason corrected to the one file it actually fitted; and the dead-reference
  counts re-measured over `HEAD` — **26** path-form references dead under the
  old resolver and **14** under the new one, 27 and 15 counting this batch's
  own plan, in 10 repaired documents, where the records had said 27 and 18 in
  eleven. Three of its four lows were fixed too, on the same ground as the
  fifth pass's: all three are text or code this batch itself wrote — the
  probe's self-coupling (now a file the test writes, mutations BH–BJ), a
  dedupe comment that claimed an effect the dedupe cannot have, and two rows
  whose prose still described the test that was replaced. `SAG-A18` is filed.
- **An earlier version of this note said the sweep closed at five, and that
  was wrong.** It
  said the sweep was closed at five on the ground that the fifth pass's
  findings were all records. The budget does not read findings that way: a pass
  that produces a high requires another, and the fifth produced one. It also
  produced `SAG-M4`, an in-loop fix to a guard — the least-reviewed code in the
  batch, and in scope by the same rule. The sixth pass is cold, in a different
  family (the widened guard's behaviour on real input rather than the records),
  and its findings are appended to the Risks section above when it returns.
  The record of what each pass found is in `docs/spec_coverage.md`'s
  **Cold passes** table and in the Risks section.
- `SAG-A3` — delete `.github/workflows/agent-docs-gate.yml`, now that its rule
  is in the suite. Small, and deliberately not in this batch.
- `SAG-A7` — `CLAUDE.md`'s key-files table names
  `daVIPA_MasterSpec_SQLite_v1.md`; the file is
  `GetMoreDone_MasterSpec_SQLite_v1.md`.
- `SST-A2`, `SST-A4`–`SST-A7`, `SST-A9`–`SST-A18` remain open from the SST
  batch.
