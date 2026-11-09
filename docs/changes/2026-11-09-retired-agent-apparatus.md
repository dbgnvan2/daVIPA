# Handoff Note

- Date: 2026-11-09
- Topic: retired-agent-apparatus (MAW)

## Summary

`CLAUDE.md` and `AGENTS.md` had recorded the three-agent branch workflow as
retired since 2026-11-08. Its apparatus was all still here and still read as
current. Six files are deleted:

- the workflow document, 70 lines, 35 of them describing role definitions, a
  worktree-per-role branch model and a step 4 that said to open a pull request;
- `tools/agents/setup_worktrees.sh`, which created `codex/agent-code`,
  `codex/agent-docs` and `codex/agent-github` plus a worktree on each and
  printed "Open 3 agent sessions" — two of those three branches were never
  created by anything else, and the third is 624 commits behind `main`;
- the three role prompts under `.agents/prompts/`, one of which told an agent
  to commit to `codex/agent-code`;
- .github/pull_request_template.md, whose only trigger is a pull request.

The document was deleted rather than rewritten, and §1.2 of the plan is the
measurement for why: its other 35 lines were a **third copy** of rules
`CLAUDE.md` and `AGENTS.md` each already carry in full. The one list only it
held had drifted — `requirements.txt` without `requirements-dev.txt`, which the
tool has counted since `SAG-M2` — and was repaired in `1d05a4c`, by the GSF
batch hours before this deletion. So the list was current when the file went,
and the argument is not that it was stale on the day but that a third copy
drifted unnoticed until a cold pass went looking. That same cold pass caught the
paragraph above that list reinstating a false enforcement claim two hours after
the same batch removed that claim from three other documents. Three copies of
one rule is the drift surface; two is the fix.

This closes `BACKLOG.md`'s `GSF-A1` (medium), `GSF-A2` (low), and the
2026-08-20 filing "The retired multi-agent workflow is still described in four
places" — the third filing of the same surface in three months. Each earlier
one scoped itself to the documents and left the executable parts, which is why
it kept coming back.

Three guards hold it now, and a fourth claim was corrected on the way:
`AGENTS.md` still permitted two concurrent builds in two worktrees, which
`CLAUDE.md` withdrew on 2026-11-08 with the measurement of what that day cost.
`AGENTS.md` pointed at `CLAUDE.md` for the detail of the rule it contradicted.

## Files changed

- Deleted: docs/MULTI_AGENT_WORKFLOW.md, `tools/agents/setup_worktrees.sh`,
  .agents/prompts/code-agent.md, .agents/prompts/docs-agent.md,
  .agents/prompts/github-agent.md, .github/pull_request_template.md
- `tests/test_ci_contract.py` — MAW-M2.1: `_GITHUB_FILE_CITATION`,
  `github_file_citations`, `dangling_github_citations`, the guard; and the GSF
  scanned set loses the deleted document, along with the required-membership
  assertion that named it
- `tests/test_repo_hygiene.py` — MAW-M1.1/M1.2/M3.1: `_DOCS_PATH`,
  `_DOCS_PATH_CITATIONS`, `DOCS_PATH_CITATION_EXEMPTIONS`,
  `RETIRED_AGENT_APPARATUS`, `docs_path_citations`,
  `dangling_docs_path_citations`, `present_apparatus`, two guards
- `tests/test_doc_status_claims.py` — MAW-M4.1: the AGENTS/CLAUDE agreement on
  concurrent builds
- `AGENTS.md` — the worktree exception removed, with why it was withdrawn
- `docs/GEMINI.md` — its *Multi-Agent Workflow* section replaced by the
  surviving working agreements; found by the second cold pass, which is the one
  high this batch did not catch itself
- `.agents/templates/handoff-note.md` — the `Agent: Code | Docs | GitHub` line
  removed, the last live naming of the three roles
- `CLAUDE.md` — two convention bullets, the marker counts (253 meta / 2439
  app), and the branch distance corrected to 624 and an ancestor
- `BACKLOG.md` — three items closed; the GSF closure note's list of documents
  repaired where it named the deleted one
- `docs/DOCUMENTATION_INDEX.md` — the two entries replaced by one that says
  where the surviving rules live
- `docs/implementation_plan_2026-11-09_retired_agent_apparatus.md`,
  `docs/spec_coverage.md` (the `## MAW` section), `NOTES.md`,
  `docs/DOCUMENTATION_INDEX.md`, this note — the records

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_ci_contract.py tests/test_repo_hygiene.py tests/test_doc_status_claims.py tests/test_traceability_refs.py tests/test_docs_sync_rule.py -q`
- Result: PASS, with one CI-only skip
  (`test_rm3b_ui_tests_are_not_skipped_headless`).
- All four guards were confirmed red against the repo before the deletions —
  that is the proof they read the real state and not a fixture alone.
- The full suite was not run locally, by the throttling rule; CI runs it.
- **Two cold passes.** The first produced three highs, which is what the budget
  requires a further pass on; the second produced two more highs — a live
  document still describing the retired workflow, and a justification sentence
  that was false as written — five mediums and eight lows. Both passes are
  recorded in full in the `## MAW` section of `docs/spec_coverage.md`. Every
  fix from the first pass was in scope for the second, and the second's own
  fixes are documents and one regex, with no third pass: the budget allows one
  pass after a high, and that was it.
- Marker counts re-measured after this batch's four tests: **253 meta / 2439
  app**, 2692 collected.
- CI run **42674300190** at `fd68c28` is green on 3.11, 3.12 and 3.13:
  `2682 passed, 10 skipped` on each. 2682 + 10 = 2692, which reconciles with
  the two marker counts above, so neither figure in `CLAUDE.md` is stale as of
  this batch.

## Risks / Known gaps

- **Six deletions, one executable.** All six are in git history. What is
  genuinely lost is a script that would create three branches nobody should
  commit to.
- **`MAW-M4.1` matches phrasings, not meaning.** It forbids three specific
  sentences that offer a second build, and asserts `CLAUDE.md` still withdraws
  the exception. A fourth phrasing would pass it. The positive half — that
  `AGENTS.md` still states the rule at all — is what keeps it from passing on
  an absence. It caught this batch's own first draft of the history sentence.
- **`GSF-A3` is narrowed, not closed.** The `docs/`-path arm reads citations
  *in* the scanned documents, of which there are now **17** — the deletions
  took four out, three role prompts and the workflow document. 28 of the 33
  documents one level under `docs/` whose names carry no date — excluding the
  per-batch records: implementation plans, dated spec-coverage snapshots and
  status reports — are still outside that set, so a dead pointer written in one
  of them is unread.
- `origin/codex/agent-code` still exists on the remote. It is 624 commits
  behind `main` and an **ancestor** of it — 0 commits ahead — so every commit
  on it is already here and deleting the ref would lose nothing. Deleting a
  remote branch is still the user's call: `MAW-N1`.

## Next agent actions

- Read the CI run for the pushed range.
- `MAW-N1` needs the user: whether `origin/codex/agent-code` should be
  deleted. Nothing is lost by it — the branch is an ancestor of `main`.
- `MAW-A1` is filed, not fixed: `.agents/` now holds only a template
  directory, which is a tidying question rather than a defect.
