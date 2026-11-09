# Handoff Note

- Date: 2026-11-09
- Agent: Code
- Topic: the bare `::name` citation form brought into the traceability guard (SBN)

## Summary

`tests/test_traceability_refs.py` checked a test citation written as a path,
`tests/<file>.py::name`. A citation written as a bare continuation — a leading
`::` and a name, under a row that named its file earlier — was matched by
nothing, so about a third of this repo's test citations were never checked.
`PDT-A1` filed that against one document; `SAG-M4` then widened the scan to
four document families and widened the gap with it, which the sixth cold pass
of the SAG batch found and filed as `SAG-A17`. This batch closes it.

- **The arm.** A bare name has no file, so it resolves against every name
  defined anywhere under `tests/` — weaker than the path form, and the whole of
  what can be checked without inventing a convention these documents do not
  follow. `SAG-A17`'s own recommendation, reading the file from the nearest
  preceding path citation, was measured and **rejected**: carried across lines
  and reset at headings it puts the anchor on the wrong file 356 times against
  52 citations that are actually dead, so enforcing it would have demanded
  rewriting hundreds of honest citations. The residue is `SBN-A1`.
- **The repairs.** 68 dead occurrences, 59 distinct names, in 14 documents.
  A test that still exists under a new name is re-cited by that name with its
  path; a test that no longer exists is named in plain backticks with neither
  the path nor the `::`, so it reads as history rather than as a pointer a
  reviewer would follow to nothing.
- **What the repairs exposed.** Ten criteria in
  `docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md` name tests
  that were never written, and PD-M14.4 and PD-M14.7 have no automated test
  under any name — there is no production caller of `shift_all_slots` and no
  repair pass in `src/` at all. That is recorded in the plan and filed as
  `SBN-A3` rather than answered here.
- **A mask deleted.** `_FULL`, a regex that masked whole path-form citations so
  their trailing names would not read as bare, changed no outcome anywhere in
  the repo: every citation that carries a file puts a word character
  immediately before its `::`, which `_BARE`'s lookbehind already excludes.
  Found by mutation (the mutation came back green), confirmed by measuring the
  character before every one of the 1930 `::name` tokens in the scanned
  documents — 1136 are not preceded by a word character and all of them are a
  backtick, an ellipsis or a line start, while all 794 that are include the 763
  preceded by the `y` of `.py` — and deleted rather than left as untested
  protection.

## Files changed

- `tests/test_traceability_refs.py` — the bare arm: `_BARE`, `_TESTISH`,
  `bare_names`, `_suite_names`, `_resolves_in_suite`, four new assertions in
  `test_this_guard_can_actually_fire`, and the four `SBN-M1` tests. `_FULL`
  deleted.
- `docs/unused-docs/implementation_plan_2026-11-09_bare_name_citations.md` — new, the plan.
- `docs/spec_coverage.md` — the SBN section, the mutation table, the cold pass,
  and six repaired rows, two of which also needed their criterion sentence
  corrected.
- Thirteen documents repaired: the window-leak, project-time-totals,
  timer-session-endings, backlog-clearance, time-blocks, time-grid,
  plan-box-appearance, plan-day-controls, day-hours-are-a-template,
  plan-calendar-export and priority-defaults plans; and the
  `2026-11-06-plan-box-appearance` and `2026-11-09-ci-green` handoff notes.
- `BACKLOG.md`, `NOTES.md`, `docs/DOCUMENTATION_INDEX.md`.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_traceability_refs.py tests/test_docs_sync_rule.py tests/test_ci_contract.py tests/test_doc_status_claims.py tests/test_release_docs.py -q`
- Result: PASS — `147 passed, 1 skipped` (the skip is the CI-only display
  check), re-run after every fix below.
- Nine mutations, each restored from the verbatim original and confirmed by
  sha256. Two came back **green**: one was the `_FULL` finding above, and one
  was a wrong-shaped mutation of mine — deleting an assertion cannot fail a
  test — replaced by one that breaks what the assertion guards. The five
  discriminating mutations were re-run after `_FULL` was deleted and all five
  still fire. Table in `docs/spec_coverage.md`.
- One cold pass, in the family the plan named as the batch's own risk: whether
  a repaired row says something true. **No high, eight mediums**, so the sweep
  closes by the budget's own rule. Two of the eight were in the guard's own
  prose, six were repairs whose sentences were false. All fixed; the fixes are
  prose and comments only, so no mutation needed re-running.
- **CI run `42646001919` on `617b1a1` is green on 3.11, 3.12 and 3.13** —
  `2676 passed, 10 skipped` on each, which is 2686 collected and reconciles
  with the marker counts this batch re-measured: 2439 app plus 247 meta.
- Not run locally: the full suite. CI runs it.

## Risks / Known gaps

- **A bare name that resolves may still be the wrong test** — the arm does not
  prove the name is in the file a reader would open next. `SBN-A1`.
- **A third citation form is still unread.** The basename without the path,
  `test_x.py::name`: 54 in the scanned families, 31 unresolvable, three of them
  test citations. `SST-A2` carries it and stays open.
- **`test_this_guard_can_actually_fire` asserts that bare citations continue to
  exist** in each of four families. A future batch that converts a whole
  family's citations to the path form would turn the guard red for having
  improved the documents. `SBN-A4`.
- **The plan's §1.2 measurement table is not reproducible from the repo** — the
  script is scratch. `SBN-A6`.
- **PD-M14.4 and PD-M14.7 have no test at all**, and PD-M14.3's span clause and
  PD-M14.5's second bullet are uncovered. `SBN-A3`.

## Next agent actions

- `SAG-A3` — delete `.github/workflows/agent-docs-gate.yml`, which triggers on
  `pull_request` only and so has never run in this repo.
- `SAG-A7` — `CLAUDE.md` names `daVIPA_MasterSpec_SQLite_v1.md`; the file is
  `GetMoreDone_MasterSpec_SQLite_v1.md`.
- `SBN-A3` — decide whether PD-M14.3 to PD-M14.7's uncovered clauses should be
  covered. It is a product judgement, not a cleanup.
