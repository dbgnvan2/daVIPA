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

Three of the eight have a companion proving they can fire; the other five
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

Under the budget this pass earned one more, because it produced highs. That
second pass is recorded above.

## The second cold pass, 2026-11-09

Earned under the budget because the first produced highs, and run in a
different failure family: not "is this figure true" but **"are these guards
load-bearing, and does the batch obey the repo's own process rules"**. One high
and five mediums, all re-measured here before any fix, all confirmed, all
fixed. Six mutations, M to R in `docs/spec_coverage.md`'s table.

**High — a criterion recorded `done` against evidence that cannot run.**
`SST-M10`'s test was given as "the docs-sync gate".
`tools/agents/check_docs_sync.py` only asserts that *some* path under `docs/`
changed alongside code — it never reads the five records `SST-M10` names — and
`.github/workflows/agent-docs-gate.yml` triggers on `pull_request`, which this
repo never opens. So the gate has never run on the way work ships here, and the
sentence in `CLAUDE.md` claiming docs updates are "enforced by the docs sync
gate" described an enforcement that cannot fire. `CLAUDE.md` now says so and
gives the by-hand command; `SST-M10` has a real guard, weak and labelled weak;
the dead gate is filed as `SST-A8`. This is the batch's own defect family found
in the batch's own acceptance criteria.

Mediums:

- **The status-heading rule read a two-line window.** A claim on the third line
  of a `## Status` section passed — and a section longer than two lines is the
  normal shape here. The rule now runs to the next heading (mutation M). The
  hole was opened by the *first* cold pass's fix, which is the budget's reason
  for saying every in-loop fix is in scope for the next pass.
- **`SST-M3` policed one historical figure, not the count.** Its only
  `BACKLOG.md` assertion was that the string "all 38 criteria" was absent, so
  40 passed; and `docs/DOCUMENTATION_INDEX.md`, one of the three documents that
  disagreed in the original defect, was in no guard's domain. Both are now
  anchored on their own sentence and checked against the recount (mutations N
  and O).
- **`SST-M8`'s pattern required the `docs/` prefix** for three of the four
  chronic documents, so the same cite written as a bare basename with a line
  number escaped. Latent — no such cite existed — and now matched on the
  basename with any prefix or none (mutation P). The example is described
  rather than written out, because the widened pattern reads this file too.
- **`SST-M9` went red on a correct edit.** It asserted that the set of
  `PRI-A…` names in the plan equalled its two endpoints, so naming all four —
  the natural edit now that they are filed — turned it red with nothing wrong.
  It now checks that every name is inside the promised range (mutation R).
- **Two claims this batch falsified and left standing.** `UPD-A13` cited
  `grep -rn DOCUMENTATION_INDEX tests/` returning nothing; this batch's own
  test file made that false while the conclusion stayed true. `SSC-8`'s closed
  body said neither filing mentioned the other, which the guard that closed it
  now asserts the opposite of, and gave a grep count of fourteen where 26 is
  current. Both re-worded; `SSC-8`'s is marked as the state at filing rather
  than rewritten.

Also corrected: the rationale for excluding `docs/changes/` from `SST-M1` while
`SST-M3` reaches into it. The distinction was never written down — a claim that
was true when written is exempt, a figure that was never true is not — so the
two rules read as contradicting each other.

Four low findings are measurements of items already filed (`SST-A6`, `SST-A7`),
a poor diagnostic when §6 is renumbered (now an assertion with a message), and
the index-completeness test that `UPD-A13` and `PLC-A5` already cover.

Under the budget this pass earns one more, because it produced a high.

## The third cold pass, 2026-11-09

Earned because the second produced a high, and run in a third family: **does
the repository match reality, outside this batch's own records?** That is the
batch's declared gap — `SST-N1` says no guard can prove a corrected status line
is true. The pass audited the documents against `src/` and the coverage files.
Two highs, two mediums, one medium-low, three lows. Every one re-measured here.
It did not find a false correction: of the sixteen documents this batch
corrected, every checkable evidence claim held. It found the ones the batch
never looked at.

**High — two documents whose work shipped months ago, in wordings no guard
reads.** `docs/spec_2026-08-23_dopamine_reward_protocol.md` was headed "Draft
for implementation" over `src/getmoredone/reward_protocol.py` and 41 `done`
`RP-` rows — and this batch corrected that spec's *paired plan* twice without
opening the spec. `docs/implementation_plan_2026-06-06.md` described all three
of its built phases in the future tense under a `## Status` heading; it is the
twin of the project-notes plan the first cold pass found. Both corrected, with
their evidence named. Neither appears in `docs/DOCUMENTATION_INDEX.md`, which
is how both stayed invisible.

**Medium — two dead test references on `done` rows, and the guard that could
not see them.** `docs/spec_coverage_2026-08-18_weekly_tactic_scheduling.md`
cited a test name that has never existed in this repo, on a row marked `done`,
and in two further documents; another row named the right test in the wrong
file. That file is the evidence §1.1 cites for the WT work being built. They
survived because `tests/test_traceability_refs.py`'s `SCANNED` held one
coverage document, not the family — while this batch widened its *own*
Implementation-column check to the whole family and left the Tests column
where it was. `SCANNED` is now a glob; the two references are repointed; two
rows that named a parametrised family through a `<surface>` placeholder now
name a real test and point at the list below them.

**Medium-low — three plans that recorded only how they were approved.**
"approved; in progress" over 55 passing tests, and two "approved to implement"
lines over built work. No deny-list of unbuilt phrasings reaches these, which
is the argument for `SST-A3`.

Lows: the register's comment gave the CIP criterion count as 57 where 42 rows
exist; the demo-install evidence said 46 `done` where the status cells say 45
`done`, 1 `not done` and one criterion verified by hand; and the index gap now
carries its measurement — **26 of the 42 plan, spec and coverage documents are
absent from `docs/DOCUMENTATION_INDEX.md`**, filed on `UPD-A13`.

`SST-A1` is closed by this pass rather than deferred: the floor of 140 against
784 references is replaced by membership per source, the same route used for
the markdown walk, which needs no judgement about how often a red suite is
acceptable. `SST-A3` is raised to high, with three passes' worth of evidence
that lengthening the phrase list is not the fix.

A note on method: mutation T failed to fail on the first attempt because the
string it replaced occurred twice — in `SCANNED` and in the companion's own
glob — so the mutation narrowed the guard and its check together. A mutation
that changes two things proves nothing about either; it was re-run against the
`SCANNED` line alone.

Under the budget this pass earns one more, because it produced highs.

## Files changed

Tests (committed separately from the documents, per the repo rule):

- `tests/test_doc_status_claims.py` — **new**, 11 tests (8 guards, 3
  companions). Collect the count rather than trusting this line:
  `--collect-only -q` over the file prints it
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

## The fourth cold pass, 2026-11-09

Earned because the third produced highs, and run in a fourth family: **what do
the new guards reject?** The first three passes all asked whether a guard can
fail on the defect it names. This one asked the opposite — which legitimate
future edit turns the suite red — because a guard whose only failure mode is
"someone added a document" is a tax on every later batch, not a check. Two
highs, three mediums, three medium-low, three lows. Every one re-measured here.

**High — two exact counts that this repo's own process breaks.** SST-M2's
companion asserted `len(documents) == 35` and SST-M5's asserted
`len(found) == 186`. Measured over git history rather than argued: the scanned
document count took **three** distinct values over the last 40 first-parent
commits (it moved twice inside two days, and this batch moved it itself by
adding its own plan), and the reference count took **four** over the last 30
(175, 184, 185, 186), with 66 commits touching a `docs/spec_coverage*.md` in 30
days. The global rule is "Plan before code… Commit it and wait for approval",
so the commit that lands a plan would have turned the meta suite red, in CI's
default run, with nothing wrong.

This batch had already written the argument against itself twice. Its
`CLAUDE.md` edit says of the suite's test counts: "No test asserts either
number, which is why they drifted; one that did would go red on every batch."
And it shipped the right pattern — membership per source — in two other
companions in the same change, one of them with the comment "an exact count
here would turn the suite red on every batch". `SST-A1`'s own closing note
claimed "35 documents and 185 references move far less often than 784 docstring
references do"; the history above says they do not. Both are now membership per
source: the glob must still reach both document families, and five named
coverage files must each contribute a reference. Narrowing either still fails
(mutations V and W).

**Medium — three assertions that only accept the all-done phrasing, or pin
prose.** SST-M3 required the literal `all 41 criteria` in four documents.
Adding a `WTP-M7` row makes the correct summary "41 of 42 criteria", which the
guard rejected; all three positive checks now accept either form. One of the
four documents was `docs/changes/2026-11-08-weekly-tactic-as-parent.md`, a
dated handoff note — the same kind of record SST-M1 deliberately keeps out of
the status scan, "because a handoff note records what was true on its date".
Pinning a recounted figure there would require editing a dated record every
time a criterion is added; the two assertions over it are dropped, with the
reason in the test. And the `BACKLOG.md` check was anchored on a seven-word
fragment of that file's header paragraph — one of the four chronic conflict
surfaces `CLAUDE.md` names *because* every batch rewrites that region — so any
rewording failed a test. It is anchored on the figure now.

Writing the absence half of that check re-created this batch's own trap for the
third time: `assert "all 40 criteria" not in backlog` went red immediately,
because an `SSC` filing quotes that wrong claim verbatim as the thing it
records. Absence over a whole file is red on a true record. The positive check
alone closes the hole the second pass found, which existed because absence was
the *only* assertion there.

It then happened a fourth time, in this pass's own filing: `SST-A10` records
that `_LINE_CITE` would match pasted `grep -n` output, and its first draft
demonstrated the point by pasting some, which failed SST-M8. The filing now
describes the shape instead and says why. That moves `SST-A10` from latent to
demonstrated, and it is the fourth time in this batch that writing *about* a
defect put the defect back inside a guard's domain.

**Medium — SST-M10 pinned an `SST-…` id into `NOTES.md`**, whose opening
"Where `main` stands" section each batch rewrites with deletions. The id is
expected to age out, and the guard's message would then have said the batch "is
no longer traceable", which is the wrong diagnosis. `NOTES.md` is out of
`SST_RECORDS`, with the reason recorded there.

**Below medium, filed not fixed:** `SST-A9` to `SST-A14` — SST-M9 derives its
promise count from the thing it pins; `_LINE_CITE` forbids pasted `grep -n`
output, which its own message recommends as evidence; a new plan needs two
edits to the guard file with a red window between them; `_defined_names()`
cannot resolve an indented constant, though four current references resolve
only as constants; SST-M7 fails on the duplicate-collapse its own subject
prescribes; and the markdown walk reaches `.pytest_cache/` and `licenses/`,
with this repo's worktrees excluded only as a side effect of the `.claude`
entry.

Five mutations, U to Y, each restored with the verbatim original and verified by
sha256. None was green: the loosened assertions still fail on the defect. That
is the limit of mutation for this family — a false positive is not a mutation,
it is a measurement over history, which is how both highs were established. X
had to be re-run against §6 by offset, because the string it replaces occurs
twice in the file.

## The fifth cold pass, 2026-11-09 — the budget's stop

Earned because the fourth produced highs, and run in a fifth family: **will
this batch be green anywhere other than the machine that wrote it?** The work
had only ever run here, under `GETMOREDONE_NO_MAPPED_WINDOWS=1`, and
`.github/workflows/tests.yml` runs the whole suite — meta tests included, with
no marker and without that variable — on a blank ubuntu runner for Python 3.11,
3.12 and 3.13.

**No finding at medium or higher. Under the sweep budget in `CLAUDE.md` that
ends the sweep**, and this batch had five cold passes: figures, guards,
repo-against-code, what the guards reject, and portability.

What the pass established, by re-implementing each new assertion and running it
against both the working tree and `HEAD` alone:

- Every literal path in the new tests is tracked, with matching case, so none of
  them is green on case-insensitive APFS and red on ext4. That covers
  `DRAFTS_NOT_BUILT`, `COVERAGE_WITHOUT_PATHS`, `SST_RECORDS`, `CHRONIC`, and
  the five coverage files SST-M5's companion names.
- The new tests read nothing outside the repository root — in particular not
  `~/.claude/standards`, which is a separate per-machine clone and absent in CI
  — and take no dependency on a display, the network, Tk, a subprocess, the real
  application database, locale, or glob ordering. Every read passes
  `encoding="utf-8"`; every glob is `sorted()`.
- The CI contract still holds: the new file carries the module-level `meta`
  marker, so the exact-set assertion, the default-run collection check and the
  marker-exclusion check all pass, and the mapped-window count of 22 is
  unaffected.
- The widened traceability scan resolves 986 references, all to tracked files
  with matching case; SST-M5 resolves 186, none unresolved.
- Pushing the commits with or without the uncommitted document edits is green
  either way, which it checked rather than assumed.

**One finding was refuted by measurement.** The pass read `CLAUDE.md`'s meta
figure of 225 as stale by one, from the order of two commits. Re-measured here:
`-m meta --collect-only -q` prints `225/2657 tests collected (2432
deselected)`, and `-m "not meta"` prints `2432/2657`. Both documented figures
are right as written; the AST delta the pass used cannot see parametrisation,
and the 225 was taken after the eleventh test was added, not before.

Four below-medium findings filed: `SST-A15` to `SST-A18`. The last is this
batch's own subject in a file it never opened — a test docstring still calling
the docs-sync gate a merge gate, which `CLAUDE.md` now contradicts.

## Next agent actions

- A **fifth cold pass** is owed before this batch is pushed, in a different
  failure family again: the budget grants one more because the fourth pass
  produced highs. Four families are used — are the figures true; are the guards
  load-bearing; does the repo match the code; what do the guards reject. The
  one that is unexamined and matters before a push is whether this batch is
  green *on CI and on the other Mac*, rather than on the machine that wrote it.
- `SST-A8` — the docs-sync gate runs only on pull requests, so it has never
  run here. It is the one filed item with a user-visible consequence: the rule
  it was supposed to enforce is currently enforced by hand.
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
