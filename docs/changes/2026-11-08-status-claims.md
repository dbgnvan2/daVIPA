# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: status-claims (SST) — the nine open `SSC` filings

## Summary

The nine open `SSC` filings in `BACKLOG.md` were one defect wearing nine faces:
**a claim this repo makes about itself that nothing checks.** All nine are
closed, and the class is now held by three guards rather than by whoever next
reads the document.

Corrected:

- **Seventeen stale lines in sixteen documents** said no implementation code
  had been written — sixteen status claims and one prose sentence. Every one of
  the sixteen documents is built. `SSC-4` named four and
  said the rest were "a sample, not a list"; the other twelve were checked, and
  each correction names its evidence — a coverage document and its `done`
  count, or the module. The oldest had been wrong since August, over
  `src/getmoredone/reward_protocol.py` and over the packaging that builds the
  app. Two were worse than stale: the WTP spec denied its own §6, which reports
  the work finished, and `day_hours_are_a_template.md` said "planned, not
  built" about **PD-M14** — the surviving plan-day design, the one the whole
  PDT batch was written against. That correction names PD-M14.4, which
  genuinely was never built, rather than claiming the plan whole.
- **The dopamine plan's §8** narrated "no implementation code has been written"
  in the present tense, outside a status line. Kept as history, marked as
  history, dated.
- **The WTP criterion count**: 38 in `BACKLOG.md`, 40 in the spec, 41 in the
  spec's own rows. Measured — **41**, and §3 and §6 hold the same 41 IDs,
  compared as sorted sets. The spec's arithmetic for 40 counted §3 as 35 after
  §3 had been amended to carry the additions, so it double-counted them.
- **`RP-2.5`** named `db_manager.py::_update_action_item`. Nothing of that name
  has ever existed; `update_action_item` writes `deliverable` on update.
- **Twelve line-number cites in nine documents** into the four documents every
  batch edits, rewritten as quoted text plus the grep that finds it. Ten of the
  twelve, in eight documents, were there before this batch; the other two were
  in this batch's own plan, written the same day as the rule. Three were
  measurably dead. Count them at any revision with
  `git grep -nE "(BACKLOG\.md|docs/spec_coverage\.md|CLAUDE\.md|docs/DOCUMENTATION_INDEX\.md):[0-9]" <rev> -- '*.md'`.
- **`PRI-A1` to `PRI-A4`** filed. The PRI plan promised them and
  `docs/DOCUMENTATION_INDEX.md` repeated the promise, so two documents asserted
  items that were nowhere.
- **`UPD-A13` and `PLC-A5`** name each other, and `PLC-A5` no longer opens by
  quoting an index footer that had been rewritten.

Added, in `tests/test_doc_status_claims.py`:

- a **register** of documents whose status line may say the work is not built —
  one entry, the CIP spec — checked in both directions, so an entry left behind
  after its work ships fails as loudly as a stale claim;
- a check that every **`file::symbol` in a coverage Implementation column**
  resolves to a definition in `src/`, `tools/` or `conftest.py` — 186
  references, in the `file.py::symbol` form and the bare `::symbol`
  continuation form the `RP-2.5` defect was written in;
- a check that the **four chronic documents are not cited by line number**.

Three of the seven have a companion proving they can fire; the other four
assert on a named anchor in a named file, which is weaker, and is filed as
`SST-A4`. Two of the counts are exact rather than floors (35 plan/spec
documents, 186 implementation references). The markdown walk was checked by a
floor of 200 against 245 files — the defect `SST-A1` files, shipped in this
batch's own tooling — and is now checked by membership: the four chronic
documents, `NOTES.md`, and one file from each directory markdown lives in. An
exact count there would go red on every batch, since every batch adds a handoff
note.

## Two guards shipped unable to fail

Both found by asking what the assertion would accept, not by running it. Both
are this batch's own subject appearing in its own tooling, which is why they are
recorded here rather than quietly fixed:

- `test_sstm9_every_promised_pri_adjacent_item_is_filed` tested
  `f"### {name}" not in backlog`, which matches the name as a substring of a
  longer token. Renaming `### PRI-A3` to `### PRI-A3x` left it green. Now
  anchored with `^### PRI-A3\b`.
- `test_sstm7_the_two_filings_of_the_index_gap_cross_reference` took its slice
  from the first **mention** of each name. Both names appear in `BACKLOG.md`'s
  opening summary, above any `###` heading, so the walk back found no owning
  heading, the slice started at byte 0, and the guard asserted that the whole
  file contains both names — which it does. It passed while neither filing
  mentioned the other, the exact state it was written to catch.

The second one also made a commit message false: `cd4fd49` claimed the two
cross-references and the `PLC-A5` correction, written from the guard being
green. Neither was in that commit. Both are in `6e5d0ae`, which says so.
Reporting a change from a green test rather than from the diff is how a status
claim becomes false in the first place.

## The cold pass, 2026-11-09

One cold pass was run over the committed batch, per the sweep budget in
`CLAUDE.md`: a reviewer with the diff and the range and none of the narrative.
It returned **four high and seven medium findings**, and four low ones. Every
one of the eleven was re-measured here before any fix was written, and all
eleven held — no finding was dropped as a reviewer's error. Six of them are the
batch's own subject appearing in the batch's own work: a claim about itself
that nothing checked.

Highs:

1. **The time-blocks correction overstated what is built.** The new status line
   and the plan's §1.1 both said all 28 `TB-M` rows were `done`. Nineteen are;
   nine are superseded — eight by the time grid, `TB-M8.2` by `PD-M13.1`. The
   line now gives the split and the two greps that measure it.
2. **A sixteenth stale document, outside the guard.**
   `docs/implementation_plan_2026-06-06_project_notes.md` still said the plan
   awaited a sign-off, over 25 coverage rows all `done`. The grep in the plan's
   §1.1 returned it; the triage dropped it. The guard could not have caught the
   omission either: the claim sits under a `## Status` heading rather than on a
   line beginning "Status". So "all nine `SSC` filings closed" was itself a
   premature status claim. The guard now reads the first two non-blank lines
   under such a heading (mutation I).
3. **SST-M3 could not fail on its own subject.** It asserted "all 41 criteria"
   against the whole spec — and the spec's corrected status line says that too,
   so §6 could go back to 40 and the guard would stay green. Now scoped to §6
   (mutation J).
4. **"Fifteen status lines in fourteen documents" was wrong** in seven places.
   The table has sixteen rows over fifteen documents, now seventeen over
   sixteen. The grep printed above it returns 32 lines in 21 documents, which
   the sentence never reconciled with; it does now, and says what the other
   fifteen lines are.

Mediums:

5. `_NOT_BUILT` accepts ten phrasings and nothing else. Four were added; the
   structural fix is filed as `SST-A3`.
6. "Twelve cites in eleven documents" — it is twelve in nine. Eleven is
   reachable at no revision: ten in eight before the batch, twelve in nine
   after its own plan added two.
7. The SST-M8 companion asserted a floor of 200 against 245 files, in a batch
   that filed `SST-A1` against exactly that defect and whose note claimed its
   counts were "exact, not floors". Replaced by membership checks (mutation L).
8. "35 rows, every criterion collected" for the rename-safe-links coverage is
   neither figure: 17 rows carrying 15 distinct `RN-M` IDs.
9. The WTP count was corrected in six documents and left at 38 in the batch's
   own handoff note, and at 40 in `docs/cycles/2026-11-08_wtp-widget-tests-qa-gate.md`.
   The note is corrected and now guarded (mutation K); the gate record is left
   as the gate wrote it, with a dated note, because it accurately records what
   the spec said that day.
10. `CLAUDE.md` gave the suite's marker counts as 1691 and 212; they are 2432
    and 224. Measured, corrected, with the command that re-measures them.
11. `docs/spec_coverage.md` said "six guards and four companions" and the test
    module said each guard had a companion. Seven and three, and four have
    none — filed as `SST-A4`.

The low findings go to `BACKLOG.md` rather than being fixed in-loop, per the
budget: `SST-A5` (the `RP-2.5` row names the delegating method, not the one
that writes), `SST-A6` (the reference guard resolves a symbol anywhere, not in
the file named) and `SST-A7` (SST-M4 is a literal-phrase check). The fourth was
a wrong section number in a docstring that the widened guard was rewriting
anyway, so it was corrected there. `SST-A3` and `SST-A4` are the structural
halves of findings 5 and 11, filed because the in-loop fix narrows those holes
without closing them.

Under the budget this pass earns one more, because it produced highs: a second
cold pass, in a different failure family.

## Files changed

Tests (committed separately from the documents, per the repo rule):

- `tests/test_doc_status_claims.py` — **new**, 10 tests
- `tests/test_ci_contract.py` — the new file added to `META_TEST_FILES`, which
  failed on its absence

Records:

- `docs/implementation_plan_2026-11-08_status_claims.md` — **new**, the plan
- `docs/changes/2026-11-08-status-claims.md` — **new**, this note
- `docs/spec_coverage.md` — the SST section, and the `RP-2.5` row
- `BACKLOG.md` — nine closures with a table of what holds each, `PRI-A1`–`PRI-A4`
  filed, `SST-A1` and `SST-A2` filed, `UPD-A13` and `PLC-A5` cross-referenced,
  `PLC-A5`'s stale clause corrected, the WTP count
- `NOTES.md`, `docs/DOCUMENTATION_INDEX.md`

Status claims corrected, sixteen documents:

- `docs/spec_2026-11-08_weekly_tactic_as_parent.md` (also the count and the
  outstanding-items denial)
- `docs/implementation_plan_2026-11-05_time_blocks.md`,
  `docs/implementation_plan_2026-11-05_time_grid.md`,
  `docs/implementation_plan_2026-11-08_day_hours_are_a_template.md`
- `docs/implementation_plan_2026-08-19_item_editor_project_link.md`,
  `docs/implementation_plan_2026-08-24_dopamine_reward_protocol.md`,
  `docs/implementation_plan_2026-08-24_window_leak.md`,
  `docs/implementation_plan_2026-08-26_backlog_clearance.md`
- `docs/implementation_plan_2026-08-18_weekly_tactic_scheduling.md` +
  `docs/spec_2026-08-18_weekly_tactic_scheduling.md`
- `docs/implementation_plan_2026-08-19_rename_safe_links.md` +
  `docs/spec_2026-08-19_rename_safe_links.md`
- `docs/implementation_plan_2026-08-18_downloadable_release.md` +
  `docs/spec_2026-08-18_downloadable_release.md`
- `docs/spec_2026-11-05_demo_install.md`
- `docs/implementation_plan_2026-06-06_project_notes.md` — added 2026-11-09 by
  the cold pass, which found both the stale claim and the hole in the guard
  that let it through

Cites rewritten, in five further documents:
`docs/implementation_plan_2026-11-06_plan_box_appearance.md`,
`docs/implementation_plan_2026-11-06_plan_day_controls.md`,
`docs/implementation_plan_2026-11-08_unified_panel_followups.md`,
`docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md`,
`docs/changes/2026-11-08-unified-panel-m7.md`.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_doc_status_claims.py tests/test_traceability_refs.py -q`
- Result: **PASS** — 13 passed.
- Command: the same, over `tests/test_ci_contract.py`
- Result: **PASS** — 82 passed, 1 skipped (the skip is the CI-only display
  check).

Twelve mutations, each restored with the verbatim original and confirmed
byte-identical **by sha256** rather than by `git diff` — two of the files were
untracked when the first mutations ran, which is the state that made a
`git checkout --` restore report success while restoring nothing in the PRIT
batch. A to H were run as the guards were written: six killed their mutant on
the first run, and the two that did not are the two guards described above.
I to L were run on 2026-11-09 against the assertions the cold pass changed; all
four kill their mutant now, and all four were green against the assertions as
shipped. The table is in `docs/spec_coverage.md`'s SST section.

Not run locally: the full suite. Repo rule — targeted files locally, CI runs
the whole thing on push. The nine CI-environment failures carried in `NOTES.md`
are untouched by this batch and were never in its scope.

## Risks / Known gaps

- **SST-N1, not code-testable.** The register guard proves no document claims
  unwritten code outside the register; it cannot prove a replacement sentence
  describes the code accurately. The evidence is named per document in the
  plan's §1.1, where it was measured.
- **The register is a new thing to keep.** A plan genuinely awaiting approval
  must be added to `DRAFTS_NOT_BUILT` and removed when built. That is a step in
  the process, and the guard's second direction is what stops an entry sitting
  there after its work ships.
- **SST-M8 is a style rule with teeth.** It will fail a document that cites a
  line number for a good reason, including one quoted inside a record of a
  line cite — two such records were rewritten here rather than exempted.
- **`SST-A1`, medium, not fixed**: `test_this_guard_can_actually_fire` asserts
  a floor of 140 references where 784 exist, so it would tolerate losing 82% of
  its domain. The fix is a judgement about how often a red suite is acceptable,
  which is the user's call.
- **`SST-A3`, medium, not fixed**: `_NOT_BUILT` is a phrase list, so a status
  line worded in a new way escapes the register guard. Four phrasings were
  added; the fix is to invert the check so an unrecognised sentence fails, and
  that is a convention imposed on 35 existing documents.
- **`SST-A4`, low, not fixed**: four of the seven guards have no companion
  proving they can fire. Each asserts on a named anchor, which is weaker than a
  companion; two guards in this batch shipped unable to fail, so that argument
  is not a measurement.
- **`SST-A5`, `SST-A6`, `SST-A7`, low, not fixed**: see the cold-pass section.
- **`SST-A2`, low, not fixed**: fourteen test references written without the
  `tests/` prefix are read by no guard. One of the fourteen is a deliberate
  quotation of a broken reference, so widening the existing pattern would turn
  a correct historical record red.

## Next agent actions

- A **second cold pass** is owed before this batch is pushed, in a different
  failure family from the first: the budget grants one more pass because the
  first produced high-severity findings.
- Decide `SST-A1` and `SST-A3` together: both are about how a guard decides
  what it will accept, and both are judgements about how often a red suite is
  acceptable.
- `PRIT-N1` — build `PRI-M3` (the four-digit score column) or leave it filed.
  It is a five-screen UI change against the aligned-column contract, and
  `PRI-A2`/`PRI-A3` now carry the measurements it needs.
- `PRI-A1` is one fix with `PLC-A3` and `PLC-A6`; closing it should close all
  three.
- `WTP-A11` — one shared precondition for the seven always-on-top tests, which
  is seven of the nine remaining CI failures.
