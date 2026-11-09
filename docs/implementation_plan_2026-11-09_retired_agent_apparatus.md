# Implementation plan — the retired three-agent apparatus (MAW)

**Date:** 2026-11-09
**Status: approved and being built the same day.** The user chose both items by
name ("GSF-A1 + A2") from the options offered when the GSF batch closed, under
the standing instruction for this session ("proceed on your own
recommendations as I'm going to be away … you can then start on open items").
Recorded here rather than assumed, because the global rule is to stop after the
plan.

**Closes:** `BACKLOG.md`'s `GSF-A1` (medium) and `GSF-A2` (low).

## 0. What these are

`CLAUDE.md` and `AGENTS.md` both record the three-agent branch workflow as
retired: `codex/agent-docs` and `codex/agent-github` were never created as
branches, and `codex/agent-code` was last touched 2026-04-03. What neither of
them says is that the workflow's *apparatus* is all still here, and still
reads as current.

Both of them put that branch "131 commits behind `main`" (`BACKLOG.md` does
not: it never carried the figure).
Measured today, `git rev-list --left-right --count main...origin/codex/agent-code`
gives **624 and 0**: 624 behind, nothing ahead. The 131 was measured on
2026-08-19 and copied forward without being re-measured, and this plan's first
draft copied it again. It is corrected in both live documents. The two dated
records that also give 131 — the 2026-08-19 backlog-clearance plan and
`docs/prompt-update-claude-md-and-learnings.md`, which quotes what an audit
found on 2026-08-20 — are accurate as records of their own date and are left
alone.

## 1. What was measured first

### 1.1 The apparatus

| file | what it is | state |
|---|---|---|
| docs/MULTI_AGENT_WORKFLOW.md | "a starter setup for running three parallel agents"; roles, the worktree bootstrap, the branch model, "Open/update PR with …" | 35 of its 70 lines describe the retired workflow in the present tense |
| `tools/agents/setup_worktrees.sh` | creates `codex/agent-code`, `codex/agent-docs`, `codex/agent-github` **and three worktrees on them**, then prints "Open 3 agent sessions" | executable, runnable today, and the only thing that would create two of those three branches |
| .agents/prompts/code-agent.md | "Code and tests committed on `codex/agent-code`" | instructions to commit to a branch 624 commits behind |
| .agents/prompts/docs-agent.md | the Docs-Agent role | the role does not exist |
| .agents/prompts/github-agent.md | "Open/update PRs … Merge only when required checks pass" | this repo opens no PRs |
| .github/pull_request_template.md | the PR template the workflow's step 4 names | inert: no trigger but a pull request |

Nothing executes any of it: `grep` over `tests/` and `tools/` finds no
reference to `setup_worktrees.sh`, the role prompts or the template. The one
test reference to any of these files is docs/MULTI_AGENT_WORKFLOW.md's
membership in the GSF guards' scanned set.

The remote `origin/codex/agent-code` still exists, and
`git merge-base --is-ancestor origin/codex/agent-code main` succeeds — it is
an **ancestor** of `main`, 0 commits ahead. Every commit on it is already
here, so deleting the ref would lose no work. That is `MAW-N1`: raised, not
taken, because a remote ref is the user's to delete.

### 1.2 What of that document is live, and where it already lives

Of its 70 lines, lines 36–70 are correct: the docs-gate paragraph (rewritten
by the GSF batch two hours earlier) and the handoff-template pointer. Both are
**third copies**:

- the gate rule is in `CLAUDE.md` under *Working agreements*, in full — the
  decision function, the fixtures, the depth-1 reason, the by-hand command and
  the skipped-is-not-a-pass caveat — and in `AGENTS.md` under *Docs sync*,
  also in full;
- the handoff artifact and its template are in `AGENTS.md` under *Required
  handoff artifact* and in `CLAUDE.md` under *Working agreements*.

So deleting the document loses no rule. The one thing it alone carried is a
bullet list restating when `verdict` returns "fail" — and that list is what
drifted: it named only `requirements.txt` while the tool had counted
`requirements-dev.txt` since `SAG-M2`. It was repaired in `1d05a4c`, by the GSF
batch hours before this deletion, so the list is **not** stale at the moment
the file is deleted; what the drift shows is that a third copy went unnoticed
until a cold pass went looking. That same cold pass found the
paragraph above it reinstating the false enforcement claim the same batch had
just removed from three other documents. Three copies of one rule is the drift
surface; the fix is two, not a repaired third.

### 1.3 A contradiction found while measuring

`AGENTS.md`, *One build batch at a time*: "two builds at once means two
worktrees with checked-disjoint file sets." `CLAUDE.md` **withdrew** that
exception on 2026-11-08 — "No second build — not in a worktree either" — and
gives the measurement that cost two orphaned branches and nine red tests. The
two documents disagree about a rule a reader is meant to follow, and
`AGENTS.md` points at `CLAUDE.md` for the detail of the rule it contradicts.
Same family as the four live claims GSF corrected, found in the file this
batch has to edit anyway, so it is in scope rather than filed.

### 1.4 How big the guarded class would be

Two arms, measured over the 21 documents the GSF guards scan:

| arm | unresolvable citations |
|---|---|
| `` `.github/<path>` `` | 1, and it is a directory (`.github/workflows/`), excluded by requiring a filename |
| `` `docs/<path>.md` `` | 3 distinct: a filename template (`docs/changes/YYYY-MM-DD-topic.md`, which goes with the deleted document), and `docs/spec_glossary.md` and `docs/spec_template.md`, two files `BACKLOG.md` *proposes* writing |

So both arms are affordable now, with a two-name exemption list carrying one
shared reason. This is the `GSF-A3` region narrowed to the two shapes this
batch's deletions create, rather than the thirty-document widening that item
asks for.

## 2. Acceptance criteria → tests

| ID | criterion | test |
|---|---|---|
| MAW-M1.1 | docs/MULTI_AGENT_WORKFLOW.md is gone and no live document describes the three-agent workflow, the per-role branches or the worktree bootstrap as current | `tests/test_repo_hygiene.py::test_mawm11_no_document_cites_a_docs_path_that_does_not_exist` for the pointer; prose review for the description |
| MAW-M1.2 | the apparatus that served only that document is gone — the bootstrap script and the three role prompts — and nothing cites them | `tests/test_repo_hygiene.py::test_mawm12_the_retired_agent_apparatus_is_absent` |
| MAW-M2.1 | .github/pull_request_template.md is gone, and a live document citing any `.github/` file that is not tracked fails, proved against a fixture | `tests/test_ci_contract.py::test_mawm21_no_document_cites_a_github_file_that_does_not_exist` |
| MAW-M3.1 | a live document citing a `docs/` path that is not tracked fails, with the exemptions carrying a stated reason and checked in both directions | `tests/test_repo_hygiene.py::test_mawm11_no_document_cites_a_docs_path_that_does_not_exist` |
| MAW-M4.1 | `AGENTS.md` no longer permits a second concurrent build in a worktree, which `CLAUDE.md` withdrew on 2026-11-08 | `tests/test_doc_status_claims.py::test_mawm41_agents_and_claude_agree_on_concurrent_builds` |
| MAW-N1 | **not code-testable:** whether `origin/codex/agent-code` should be deleted. It is 624 commits behind `main` and an ancestor of it, so it holds no commit `main` lacks and nothing would be lost | human — raised in §5, not taken |

## 3. Implementation order

1. The four guards, red against the repo as it stands.
2. The deletions, and the citations they break repaired: the index entries, the
   GSF scanned set (`DOCS_DIR_LIVE_DOCS` and the required-membership assertion
   that names this document), `BACKLOG.md`.
3. `AGENTS.md`'s worktree sentence.
4. Mutations, then one cold pass, then the records.

## 4. Risks

- **Six deletions, one of them executable.** All six are in git history, and
  §1.2 is the measurement that no rule is lost. What is genuinely lost is a
  script that would create three branches nobody should commit to.
- **The guards read prose**, so a future document naming a `docs/` file before
  it is written goes red. That is the cost `ROOT_DOC_CITATION_EXEMPTIONS`
  already carries: an exemption with a reason, checked both ways.
- **`GSF-M1.3` asserts docs/MULTI_AGENT_WORKFLOW.md is scanned.** Deleting
  the document turns the GSF guard red until that assertion goes with it. That
  is the guard working, and it is why step 2 is one change.

## 5. Adjacent issues found, not fixed

1. **`MAW-A1`** — `.agents/prompts/` keeps no live role prompt once the three
   go, but `.agents/templates/handoff-note.md` is used by every batch and
   stays. Whether `.agents/` should now hold only templates is a tidying
   question, not a defect.
2. **`MAW-N1`** above: the remote branch.
3. `GSF-A3` is **narrowed, not closed**, by `MAW-M3.1`: the `docs/`-path arm
   now reads citations in the 17 scanned documents (21 before the deletions),
   but 28 of the 33 documents one level under `docs/` whose names carry no date — i.e. excluding the
   per-batch records: implementation plans, dated spec-coverage snapshots and
   status reports — are outside the scanned set, so a dead pointer written *in*
   one of them is still unread. (The 21-scanned and 30-of-36 this line first gave
were
   mis-measured: the listing was split on whitespace, which breaks the one
   document with spaces in its name.)
