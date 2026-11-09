# Implementation plan — the live document set is derived, and retired vocabulary is guarded

**Batch:** LDS · **Date:** 2026-11-09 · **Branch:** `main`

Closes `GSF-A3` (medium), `GSF-A4` (low) and `MAW-A3` (medium), and settles
`GSF-N1` as a writing convention rather than a rename. All three are
the same defect seen from three sides: a guard that reads a hand-kept list of
documents, and a retired *concept* that no guard can read at all.

**Status: built 2026-11-09**, in the same session, under the standing
instruction for it ("proceed on your own recommendations as I'm going to be
away … you can then start on open items"). Nothing here was approved in
conversation; the instruction is recorded rather than assumed, because the
global rule is to stop after the plan.

## 0. Why these three together

The MAW batch's second cold pass found `docs/GEMINI.md` still describing the
three-agent split as current — **inside** the scanned set the whole time. The
guards resolve *pointers*: a path that does not exist. A sentence describing a
retired workflow is not a pointer, so nothing read it, and two batches went by
with it in place. That is `MAW-A3`.

Separately, the `docs/` half of that scanned set is five names kept by hand
(`DOCS_DIR_LIVE_DOCS`), which the GSF batch recorded as the one place a name
must still be added by hand. That is `GSF-A3`, and it is why the set held
`docs/GEMINI.md` but could just as easily not have.

`GSF-A4` is in because widening the set makes it fail: it is the one genuine
dead root-name pointer the wider scan finds.

## 1. What was measured first

Every figure below is from a command run today at `18195a1`.

### 1.1 Widening the `docs/` half costs nothing in path citations

With the live set widened from the 5 hand-kept names to a derived 29 — every
tracked `docs/*.md` one level down whose name carries no date and whose name
does not contain "prompt" — `dangling_docs_path_citations` reports **zero**
new dangling `docs/`-path citations. The widening is free on that arm.

### 1.2 The root-name arm needs no change — measured twice

The first measurement of this said the widened set would report 15
unresolvable bare names, nine of them false positives from documents inside
`docs/` citing a sibling. That measurement was wrong: it ran
`root_doc_citations` raw, without the fallback
`::test_gsfm21_no_document_cites_a_root_doc_that_does_not_exist` already
applies — a bare name whose basename is tracked anywhere is not dangling. With
the guard's own rule, the widened set reports **four**:

| Citation | In | Verdict |
|---|---|---|
| TOOL.md | `docs/AGENT_UI_REGRESSION_POLICY.md` | genuine — `GSF-A4`, never in this repo |
| `PROBE.md` ×2 | `docs/spec_coverage.md` | a fixture filename quoted in prose; exempt it, with the reason |
| `daVIPA_MasterSpec_SQLite_v1.md` | `docs/spec_coverage.md` (`GSF-N1`) | a rename *proposed* and not made — a form the convention does not yet cover |

`learnings.md` and the three `~/.claude/standards/` names were already in
`ROOT_DOC_CITATION_EXEMPTIONS`, which is why they do not appear.

So the planned `LDS-M2` — resolving a bare name against the citing document's
own directory, then by unique basename — **is dropped**. Both rules were
implemented in a scratch script and measured against the current rule over
both the 17-document and the 29-document sets: identical output, four findings,
no false positive either way. A second mechanism for one rule that changes no
outcome is what this very function's docstring records deleting once already,
after a mutation round showed neither mechanism was observably tested. Writing
it again, one batch after reading that, would have been the same mistake with
a different name.

### 1.3 The records stay out, with the measurement for why

Scanning the dated records as well — 82 `docs/*.md` including plans and
snapshots, and 150 notes under `docs/changes/` — reports **13** dangling
citations. Read one by one, 11 are honest at the moment they were written:
seven name the workflow document this repo deleted today, and four are forward
references to a note the plan was about to produce (two of them the template
placeholder `YYYY-MM-DD-topic.md`). Two point at a record that exists under a
different name — the 2026-08-18 release plan cites one note where six
`-phase*` notes were written.

A record is a record of its own date. A guard that fails because a 2026-06-06
note names a file deleted in November is a guard that makes honest history
unwritable, which is the whole reason the citation conventions exist. The
records stay out of the scan, and this measurement is the justification, not a
preference.

### 1.4 One real gap found while measuring, not fixed here

`docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md` cites a
handoff note and a spec-coverage snapshot that do not exist under those or any
other names (`git ls-files docs | grep -i priority_defaults` finds only the
plan). Every other plan of that week has both. Either the batch was never
built or its records were never written, and the repo's own agreement says a
batch is not done without the note. This needs those items read, not their
citations rewritten, so it is filed as `LDS-A1`.

### 1.5 Where editorial content goes

Global rule 9: trigger words and vocabulary lists belong in config, not in
Python. The repo has one precedent —
`src/getmoredone/email_cleaning_rules.json`, whose `_comment` cites the rule
and which `tests/test_repo_hygiene.py` requires to exist. The retired
vocabulary follows that shape, at `tools/agents/retired_vocabulary.json`,
beside `check_docs_sync.py`, because it is repo hygiene rather than app
behaviour.

## 2. Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| LDS-M1.1 | The `docs/` half of the live document set is derived from a stated path rule, with no hand-kept list of names | `tests/test_ci_contract.py::test_ldsm11_the_docs_half_of_the_live_set_is_derived` |
| LDS-M1.2 | The derived rule is asserted over a listing written in the test, so it fails if the rule stops excluding records or prompts | same test |
| LDS-M1.3 | The live set covers at least every name the hand-kept tuple held, so widening cannot silently narrow | same test |
| LDS-M3.1 | No live document in the widened set cites a bare document name that cannot be resolved, which means the three repairs §1.2 names are made | the existing `tests/test_repo_hygiene.py::test_gsfm21_no_document_cites_a_root_doc_that_does_not_exist`, over the derived set |
| LDS-M3.2 | A filename proposed but not yet created is a named form in the conventions, since `GSF-N1` is the second instance of one | `tests/test_repo_hygiene.py::test_ldsm32_the_conventions_name_every_form_a_guard_reads` |
| LDS-M4.1 | A live document using the vocabulary of a retired concept fails, with the vocabulary read from config rather than from a literal in the test | `tests/test_repo_hygiene.py::test_ldsm41_no_live_document_uses_retired_vocabulary` |
| LDS-M4.2 | The config is valid JSON with a reason and at least one phrase per retired concept, and every concept is dated | same test |
| LDS-M4.3 | The scan is driven over text written in the test, case-insensitively, so it cannot pass by reading nothing | same test |
| LDS-N1 | **Not code-testable:** whether the 4 prompt documents and the dated records should be scanned under a different, weaker rule | human — filed as `LDS-A2` |

## 3. Implementation order

1. **`LDS-M1.*` first**, red against the repo as it stands: derive the set. `DOCS_DIR_LIVE_DOCS` becomes a derived
   function; the tuple goes.
2. **`LDS-M3.1`** over the widened set, and the repairs it names — two
   rewrites and two exemptions, not three repairs, which a cold pass
   corrected here and in `docs/spec_coverage.md`
   (`GSF-A4`'s TOOL.md, the two `PROBE.md` mentions, the backticked
   master-spec name), with the `learnings.md` exemption already in place from an earlier batch.
3. **`LDS-M4.*`**: the config, the scan, the guard. Seed it with the one
   retired concept this repo has — the three-agent workflow — with the
   vocabulary the second MAW cold pass used to find `docs/GEMINI.md`.
4. Mutations, then one cold pass, then the records.

## 4. Risks

- **Widening a guard's input is how a guard starts failing on honest prose.**
  The non-greedy fix one batch ago was exactly that shape, found latent. Every
  new resolution rule here is asserted over text written in the test, both
  directions, before it is pointed at the repo.
- **A vocabulary guard can be a censor.** "Code agent" is a phrase someone may
  legitimately need in a sentence about history. The config carries a reason
  per concept and the guard's failure message says how to write the sentence
  instead — the same shape as the citation conventions, which exist so honest
  history stays writable.
- The config is new editorial surface. It is dated per concept so a future
  reader can tell a live prohibition from an archaeological one.

## 5. Adjacent issues found, not fixed

1. **`LDS-A1`**: the 2026-11-08 priority-defaults plan has neither a handoff
   note nor a spec-coverage snapshot (§1.4).
2. **`LDS-A2`**: the 4 prompt documents and the dated records are outside the
   scan by the rule in §1.3. Whether they deserve a weaker guard — one that
   reads only citations of files that never existed, rather than files deleted
   later — is open.
3. `GSF-A5` is untouched: `BACKLOG.md` names two screen files that are not
   tracked. It needs those items read, which is not this batch.
