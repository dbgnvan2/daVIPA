# Handoff Note

- Date: 2026-11-09
- Agent: Code
- Topic: dead-gate-and-dead-spec-name (GSF)

## Summary

Two pointers that named something which does not exist, closing `BACKLOG.md`'s
`SAG-A3` and `SAG-A7` (both low).

1. **The docs gate is deleted.** `agent-docs-gate.yml` triggered on
   `pull_request` only; this repo's standing instruction is to open none, so it
   had never run here. The rule it carried has been in the suite since `SAG-M2`
   closed `SST-A8`, where it fails before a push. Four live documents still
   described it as an enforcement a reader gets and have been corrected;
   records under `docs/unused-docs/changes/`, `docs/spec_*` and `docs/unused-docs/implementation_plan_*`
   are left as written, because they say what was true when written.
2. **Eleven citations named a file that has never existed.** The master spec
   was cited as `daVIPA_MasterSpec_SQLite_v1.md` in seven documents, including
   the key-files table in `CLAUDE.md` — the one pointer a reader is most likely
   to follow — and a `###` entry heading in `docs/DOCUMENTATION_INDEX.md`, so
   the index listed a document the repo has never contained. The file is
   `GetMoreDone_MasterSpec_SQLite_v1.md`. All eleven now name it.

Two guards were added so neither can recur, each proved against a fixture the
test writes rather than against today's prose: `GSF-M1.1`/`M1.2` for workflow
citations and `GSF-M2.1`/`M2.2` for root-document citations. `GSF-M1.3`, added
by the cold pass, makes the set of scanned documents a rule derived from
`git ls-files` instead of a hand-kept tuple.

Three naming conventions are now stated in `CLAUDE.md` under "Naming a thing
that no longer exists". They exist because a guard that reads prose cannot tell
a pointer from a history: a deleted workflow is named without its
`.github/workflows/` path, a dead root filename quoted as a defect is written
without backticks, and a retired test is named without either the `tests/` path
or the leading `::`.

## Files changed

- `.github/workflows/agent-docs-gate.yml` — deleted
- `tests/test_ci_contract.py` — `GSF-M1.1`/`M1.2`/`M1.3`: `LIVE_DOCS` (root
  half derived), `DOCS_DIR_LIVE_DOCS`, `_tracked_root_markdown`,
  `workflow_citations`, `dangling_workflow_citations`, the guard
- `tests/test_repo_hygiene.py` — `GSF-M2.1`/`M2.2`: `root_doc_citations`,
  `ROOT_DOC_CITATION_EXEMPTIONS`, the guard
- `tests/test_docs_sync_rule.py`, `tests/test_doc_status_claims.py` — comments
  naming the deleted workflow moved to the past tense
- `AGENTS.md`, `CLAUDE.md`, `NOTES.md`, `BACKLOG.md`,
  `docs/MULTI_AGENT_WORKFLOW.md`, `docs/DOCUMENTATION_INDEX.md` — the four
  live gate claims, the conventions section, the marker counts, the closures
- `README.md`, `docs/GEMINI.md`, `docs/action-timer-requirements.md`,
  `docs/daVIPA - Get Started.md`, `.agents/prompts/docs-agent.md`,
  `docs/DOCUMENTATION_INDEX.md`, `CLAUDE.md` — the eleven filename citations
- `docs/unused-docs/implementation_plan_2026-11-09_dead_gate_and_dead_spec_name.md`,
  `docs/spec_coverage.md`, this note — the records

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_ci_contract.py tests/test_repo_hygiene.py tests/test_docs_sync_rule.py tests/test_doc_status_claims.py tests/test_traceability_refs.py -q`
- Result: PASS — the five files the batch touches or is read by. One skip,
  `test_rm3b_ui_tests_are_not_skipped_headless`, which is CI-only by design.
- Mutations: nine, in two rounds, all discriminating on the final state; three
  came back green and each is recorded with what was done about it, in
  `docs/spec_coverage.md` under `## GSF`. Two of those three were one finding —
  a redundant path filter beside a path-blind regex, where neither mechanism
  was observable on its own — and the redundant one is deleted.
- Marker counts re-measured with `-m <marker> --collect-only -q`: **249 meta /
  2439 app = 2688 collected**, the meta figure having moved by this batch's two
  tests. `CLAUDE.md` is updated.
- The full suite was not run locally, by the throttling rule; CI runs it.

## Risks / Known gaps

- **The cold pass's fix for the scanned set changed guard logic, not prose**,
  and is the least-reviewed code in the batch. The sweep budget allows a
  further pass only after a high-severity finding and this pass produced none,
  so it ships unreviewed and is recorded rather than swept.
- **The `docs/` half of the scanned set is still hand-kept.** That directory
  holds dated records and one-off prompts beside live reference documents and
  no path rule separates them, so a new live document under `docs/` is outside
  both guards until someone adds it — 30 of the 36 non-record documents
  directly under `docs/` are. Filed as `GSF-A3`.
- **The root-doc guard accepts a bare name that is the basename of a file
  anywhere in the tree.** Eleven cited names in the scanned documents resolve
  only that way, so the fallback is load-bearing and cannot simply be dropped;
  what it lets through is a bare root pointer to a file that lives in a
  subdirectory.
- Answered since: a depth-1 CI checkout does collect both guards with the
  cross-module `from test_ci_contract import …` intact. Run `42656944129` on
  `1d05a4c` is green on 3.11, 3.12 and 3.13 at `2678 passed, 10 skipped`,
  2688 collected.

## Next agent actions

- `GSF-A1` to `GSF-A5` are filed in `BACKLOG.md`, none fixed here: the
  retired three-agent workflow that `docs/MULTI_AGENT_WORKFLOW.md` still
  describes throughout, the pull-request template kept for PRs this repo never
  opens, the hand-kept `docs/` half of the scanned set, the `TOOL.md` citation
  in `docs/AGENT_UI_REGRESSION_POLICY.md`, and the `BACKLOG.md` entry that
  says a file under `src/getmoredone/screens/` defines a function when no file
  of that name is tracked.
- `GSF-N1` needs the user: whether the master spec should be renamed to the
  app's current name, which eleven documents assumed it had been.
