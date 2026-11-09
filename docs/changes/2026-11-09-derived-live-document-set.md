# Handoff Note

- Date: 2026-11-09
- Topic: the live document set is derived, and retired vocabulary is guarded

## Summary

The `docs/` half of the scanned document set was five names kept by hand. It is
derived now, from one stated path rule, and the scan went from 17 documents to
41. Widening it is what found the rest of this batch: three repairs in prose no
guard had been reading, one of them a pointer that has never resolved at any
commit.

Alongside it, the thing no citation guard can see. `MAW-A3` was filed because
`docs/GEMINI.md` described the retired three-agent workflow as current for two
batches *inside* the scanned set — the guards resolve paths, and a description
contains none. `tools/agents/retired_vocabulary.json` now holds the vocabulary
of retired concepts as editorial config, and a guard reads it over the live
documents.

Closes `GSF-A3` (medium), `GSF-A4` (low) and `MAW-A3` (medium), and settles
`GSF-N1` as a writing convention rather than a rename. Plan:
`docs/implementation_plan_2026-11-09_derived_live_document_set.md`.

## Files changed

- `tests/test_ci_contract.py` — LDS-M1.1/M1.2/M1.3: `_DOCS_DIR_RECORD_DATE`,
  `_derived_docs_dir_live_docs`, `_docs_dir_live_docs`,
  `FORMERLY_HAND_KEPT_DOCS`, and `DOCS_DIR_LIVE_DOCS` derived from the last of
  those; one guard
- `tests/test_repo_hygiene.py` — LDS-M3.1 (the `PROBE.md` exemption, with its
  reason), LDS-M3.2 (`convention_section`, `convention_bullet_count`,
  `stated_convention_count`, `PROSE_CITATION_GUARD_IDS`) and LDS-M4.1/M4.2/M4.3
  (`load_retired_vocabulary`, `prose_sentences`, `retired_vocabulary_hits`);
  two guards
- `tools/agents/retired_vocabulary.json` — new. The retired vocabulary, the
  retirement markers, and a comment per section saying what the window is and
  why
- `docs/AGENT_UI_REGRESSION_POLICY.md` — the TOOL.md citation removed
  (`GSF-A4`), with a line saying it was there until today and has never been in
  this repo
- `docs/GEMINI.md` — nothing in this batch; it was repaired in the MAW batch
  and is the subject the vocabulary guard was written for
- `CLAUDE.md` — a fifth citation convention, for a filename proposed and not
  created, and the marker counts (256 meta / 2439 app)
- `docs/spec_coverage.md` — the `GSF-N1` row's proposed rename unbackticked,
  and the `## LDS` section
- `BACKLOG.md` — three items closed, `LDS-A1` and `LDS-A2` filed
- `docs/DOCUMENTATION_INDEX.md` — the plan's entry
- `.gitignore` — an explicit negation for the new config, which the blanket
  `*.json` rule had been ignoring. Untracked, it is absent on CI, where the
  guard that reads it raises instead of reading any document; a cold pass found
  it missing from this list
- `NOTES.md`, this note — the records

## Test / verification status

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_repo_hygiene.py tests/test_ci_contract.py tests/test_doc_status_claims.py tests/test_traceability_refs.py tests/test_docs_sync_rule.py -q`
- Result: PASS, with one CI-only skip
  (`test_rm3b_ui_tests_are_not_skipped_headless`).
- Each guard was confirmed red against the repo before its repair: the derived
  set made the existing `GSF-M2.1` fail on four citations, which is the proof
  the widening reaches prose that was never being read.
- **Twenty mutations, all red at the end.** Three came back green during the
  round and were dealt with rather than explained away: MH (below), and MP and
  ML, whose first forms defeated only one of two mechanisms encoding the same
  rule.
- **Fourteen mutations in the first round, one green.** MH put the sentence this batch's guard
  exists for — "Work is typically split between Code, Docs, and GitHub
  agents" — back into `docs/GEMINI.md`, and the guard stayed green, because the
  retirement window was the paragraph and the bullet beneath it said
  "retired". The window is the sentence now, over text with inline code spans
  stripped and newlines flattened; MH, and four further mutations written for
  the narrower window, all fail. Every mutation was restored with the verbatim
  original and confirmed by sha256.
- **One cold pass: one high, four mediums, eleven lows.** The high is the
  same defect as MH in a third form — the sentence window flattened the
  document, so a markdown table, a bullet list and a heading each became one
  sentence and a marker anywhere in them exempted the lot. The cold pass got
  the defect sentence passing in all three forms against the real config. The
  window is one markdown block now, then one sentence inside it. Every medium
  and low is recorded in `docs/spec_coverage.md`; four lows are filed as
  `LDS-A3` to `LDS-A6`.
- The full suite was not run locally, by the throttling rule; CI runs it.
- Marker counts re-measured: **256 meta / 2439 app**, 2695 collected.

## Follow-ups

- `LDS-A1` (medium): a 2026-11-08 plan has neither a handoff note nor a
  coverage record. Needs those items read against the code.
- `LDS-A2` (low): whether the dated records deserve a weaker guard — one that
  reads only citations of files that never existed at any commit.
- `LDS-N1`: the same question stated as the plan's not-code-testable item.
- `GSF-A5` (medium) is untouched: `BACKLOG.md` names two screen files that are
  not tracked, and the fix needs those entries read rather than their citations
  rewritten.

## Next agent actions

Record the CI run for `main` and reconcile it against the marker counts, as the
GSF and MAW batches did. Then `GSF-A5`, which is the last of the GSF class
measurement's genuine findings.
