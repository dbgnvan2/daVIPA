# Handoff Note

- Date: 2026-11-09
- Topic: the per-batch records are filed, and the prose guards are deleted

## Summary

On the user's instruction: documents exist to help the work, not the other way
round, and once a document is done it gets filed. 194 record files moved to
`docs/unused-docs/` — 151 handoff notes, 31 implementation plans, 6 coverage
snapshots, 2 QA-gate records, 3 dated status reports and the proposal that
preceded this. They are kept for recovery and history. No test reads them.

The guards that read prose are deleted, not merely narrowed: they existed to
check the records, and the records are out of scope now.

This is written as a note because it changes the working agreements and the
next session needs the state — which is the test the new rule applies.

## Files changed

- 194 files moved under `docs/unused-docs/`, with ~250 path references
  rewritten across `*.py`, `*.md`, `*.json` and `*.yml`
- `tests/test_doc_status_claims.py` — **deleted** (1,341 lines)
- `tests/test_repo_hygiene.py` — the five citation and vocabulary guards
  deleted with their exemption tables and prose helpers (1,236 → 234 lines);
  the repo-hygiene checks that are not about prose are kept
- `tests/test_ci_contract.py` — the document-set machinery and its three
  guards deleted (2,453 → 2,011 lines); the CI contract itself kept
- `tools/agents/retired_vocabulary.json` — **deleted** with its guard
- `tools/agents/check_docs_sync.py` — `missing-handoff` removed from the
  outcome set and from `verdict`; `docs/unused-docs/` excluded from what counts
  as a documentation change
- `tests/test_docs_sync_rule.py` — fixtures follow, including a new one
  asserting that filing a record does **not** satisfy the rule
- `tests/test_traceability_refs.py` — the scan is code and the live dated
  specs; the coverage record, the plans and the notes are out
- `CLAUDE.md` — the handoff mandate and the five naming conventions replaced by
  *Records are filed, not tested*; marker counts re-measured
- `AGENTS.md` — the required-artifact section becomes conditional, pointing at
  `CLAUDE.md` rather than restating it
- `docs/DOCUMENTATION_INDEX.md`, `docs/spec_coverage.md`, `NOTES.md` — records

## Test / verification status

- `tests/test_traceability_refs.py tests/test_ci_contract.py
  tests/test_repo_hygiene.py tests/test_docs_sync_rule.py
  tests/test_no_vacuous_tests.py` — **117 passed, 1 skipped** (the skip is
  CI-only).
- Marker counts re-measured: **231 meta / 2439 app**, 2670 collected. The meta
  figure fell from 256; the app figure did not move, which is the check that
  this change touched no application behaviour.
- The full suite was not run locally, by the throttling rule. CI runs it.
- No mutation round: nothing was added that needed one. Four deletions and one
  behaviour change in `verdict`, which its own fixtures cover in both
  directions.

## Follow-ups

- `LDS-A3` to `LDS-A6` are moot: the guards they were filed against are gone.
  They need closing in `BACKLOG.md` with that reason.
- `BACKLOG.md` is 5,615 lines, mostly closed items. The archive proposed in
  §4.4 of the filed proposal was not done and is still open.
- The four `docs/*prompt*.md` one-offs are still live under `docs/`. They are
  records by nature and could be filed too.
