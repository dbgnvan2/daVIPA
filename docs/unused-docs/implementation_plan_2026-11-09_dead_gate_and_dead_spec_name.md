# Implementation plan — the gate that never ran, and the spec filename that does not exist (GSF)

**Date:** 2026-11-09
**Status: approved and being built the same day.** The user chose both items by
name ("SAG-A3 and A7") from the options offered when the SBN batch closed,
under the standing instruction for this session ("proceed on your own
recommendations as I'm going to be away … you can then start on open items").
Recorded here rather than assumed, because the global rule is to stop after the
plan.

**Closes:** `BACKLOG.md`'s `SAG-A3` (low) and `SAG-A7` (low).

## 0. What these are

Two pointers that name something which does not exist.

1. **`.github/workflows/agent-docs-gate.yml`** triggers on `pull_request` only.
   This repo's standing instruction is to open none, so the gate has never run
   here. Since `SAG-M2` closed `SST-A8`, the rule it was meant to enforce lives
   in `tests/test_docs_sync_rule.py`, where it fails before a push. Three live
   documents still describe it as an enforcement a reader gets.
2. **`daVIPA_MasterSpec_SQLite_v1.md`** is named by `CLAUDE.md`'s key-files
   table — the one pointer a reader is most likely to follow — and by ten other
   places. The file in the repo root is
   `GetMoreDone_MasterSpec_SQLite_v1.md`.

## 1. What was measured first

### 1.1 The gate's surface

`grep -rn agent-docs-gate` over the tracked tree, excluding the two stale
worktrees under `.claude/worktrees/`:

| where | what it says | treatment |
|---|---|---|
| `AGENTS.md:37` | "Enforced by `.github/workflows/agent-docs-gate.yml`" | **live claim** — corrected |
| `AGENTS.md:43` | a merge gate: "docs sync gate passes" | **live claim** — corrected |
| `CLAUDE.md`, the working-agreements section (`grep -n agent-docs-gate CLAUDE.md`) | "still exists and still triggers on `pull_request` only … Deleting it is `SAG-A3`" | **live claim** — corrected |
| `docs/MULTI_AGENT_WORKFLOW.md:38` | "PR workflow … runs `tools/agents/check_docs_sync.py`" | **live claim** — corrected |
| `tests/test_doc_status_claims.py:1163`, `tests/test_docs_sync_rule.py:5` | comments explaining why the rule had to move into the suite | **history in a comment** — reworded to the past tense, because the file they name will not exist |
| `BACKLOG.md` ×3, one line in `docs/DOCUMENTATION_INDEX.md`, three handoff notes, two plans, `docs/spec_2026-08-18_downloadable_release.md:43`, `docs/unused-docs/changes/2026-08-18-…:111` | records of what was true when they were written | **left as written** |

Nothing executes it but GitHub: no script, test or Makefile invokes the
workflow. `tools/agents/check_docs_sync.py`'s `--base` / `--head` flags are
*not* orphaned by the deletion —
`tests/test_docs_sync_rule.py:131` sets them through `sys.argv` and drives
`main()` with them — so the tool keeps them and the module is not touched.

No test asserts which workflows exist: `tests/test_ci_contract.py` names
`tests.yml` and `build-release.yml` individually and otherwise iterates over
whatever `.github/workflows/*.yml` holds. So the deletion breaks no assertion,
which is also why nothing would have noticed the file rotting there.

### 1.2 The filename's surface

Eleven live citations of a file that does not exist, in seven documents: the
key-files table in `CLAUDE.md`, `README.md:720`,
`docs/daVIPA - Get Started.md:712`, `docs/GEMINI.md:47`,
`docs/action-timer-requirements.md:3`, `.agents/prompts/docs-agent.md:10`,
and five in `docs/DOCUMENTATION_INDEX.md` (one of them a `###` entry heading,
so the index has an entry for a file the repo has never contained).
`grep -rn daVIPA_MasterSpec_SQLite_v1 -- . ":!.claude"` is the measurement.

Two more are records of the discrepancy itself —
`docs/spec_2026-11-05_demo_install.md:289` and
`docs/unused-docs/changes/2026-11-05-demo-install.md:275`, both reading "One of the two is
stale", filed as adjacent and not fixed at the time. Those are accurate history
and are left as written. The `SAG-A7` entry in `BACKLOG.md` is the filing and is closed in place.

Two citations name the file that exists and stay as they are:
`tools/agents/check_docs_sync.py:23` (`DOC_FILES`) and
`tests/test_repo_hygiene.py:96` (`ROOT_DOC_ALLOWLIST`, whose companion
`test_rm7c_allowlisted_root_docs_all_exist` is why that one could not rot).

### 1.3 How big the class is

Both items are instances of "a document cites a repo file that is not there",
and `tests/test_traceability_refs.py` already holds that class for *test*
citations only. Measured over the fourteen live documents (`CLAUDE.md`,
`README.md`, `AGENTS.md`, `BACKLOG.md`, `NOTES.md`, `codex.md`, four named
documents under `docs/`, and `.agents/**` — a hand-kept set the cold pass then
showed to be both narrowable and incomplete, so the root half is derived from
`git ls-files` and the set is twenty-one documents as built):

A first version of this section recorded "33, 22 distinct" with no command
beside it, and the cold pass could not reproduce the figure — which is the
honest outcome of a count whose resolution rule was never written down. The
rule, and the measurement, now:

- the domain is every backticked token in a scanned document ending in an
  extension this repo owns (`md`, `py`, `yml`, `yaml`, `json`, `sh`, `bat`,
  `txt`, `db`, `cfg`, `toml`);
- a token resolves if it is a tracked path, or if its last segment is the
  basename of a tracked path;
- the script was a scratch file outside the repo and is not kept: twenty
  lines over `_live_documents()` and `git ls-files`, reproducible from the two
  rules above alone, which is the point of writing them down.

Over the twenty-one documents the guards now scan: **55 unresolvable
occurrences, 25 distinct.** Of the 25, **one is a genuine defect of the kind
this batch closes** — a `BACKLOG.md` entry
(`grep -n 'screens/reschedule_dialog.py' BACKLOG.md`) says that file *defines*
a function, in the present tense, and no file of that name is tracked (filed
below as `GSF-A5`, not fixed here).

The rest are legitimate, and this is why a general "every cited path exists"
guard is not what was built: runtime files the repo does not track
(`settings.json`, `getmoredone.db`, `credentials.json`, `gmail_token.json`),
the four standards files that live in `~/.claude/standards/` outside any repo,
files `BACKLOG.md` *proposes* writing, a filename template
(`docs/unused-docs/changes/YYYY-MM-DD-topic.md`), this batch's own two new documents
(tracked once committed), the nine past-tense mentions of the deleted
workflow, and the fictional single-letter and placeholder fixture files this
repo's prose names when it explains what a guard reads.

So a general "every cited path exists" guard would need a twenty-entry
allow-list of prose, maintained by hand — the shape this repo has twice
measured rotting. The guard here is narrowed to the two shapes these two items
*are*, where the exemption list is four files with one shared reason.

## 2. Acceptance criteria → tests

Spec IDs are this plan's own, `GSF-M*`.

| ID | criterion | test |
|---|---|---|
| GSF-M1.1 | `.github/workflows/agent-docs-gate.yml` is gone, and no live document describes it as an enforcement a reader gets | `tests/test_ci_contract.py::test_gsfm11_no_document_cites_a_workflow_that_does_not_exist` |
| GSF-M1.2 | the deletion cannot be undone silently: a document citing any `.github/workflows/<name>.yml` that is not there fails, and the check is proved against a fixture rather than against today's prose | same test |
| GSF-M2.1 | every live citation of the master spec names `GetMoreDone_MasterSpec_SQLite_v1.md`; `docs/DOCUMENTATION_INDEX.md` has no entry for a root document the repo does not contain | `tests/test_repo_hygiene.py::test_gsfm21_no_document_cites_a_root_doc_that_does_not_exist` |
| GSF-M2.2 | the four exempted names are exempt for a stated reason and the exemption is checked in both directions — a name that starts resolving must leave the list | same test |
| GSF-N1 | **not code-testable:** whether the file should instead be *renamed* to `daVIPA_MasterSpec_SQLite_v1.md`, the app's current name. Eleven documents assume it was. That is a branding decision, not a defect | human — raised in §5, not taken here |

## 3. Implementation order

1. The two guards, red against the repo as it stands — that is the proof they
   read the real prose.
2. The workflow deleted and the four live claims corrected; the eleven
   filename citations repaired.
3. Mutations, then one cold pass, then the records.

## 4. Risks

- **Deleting a workflow is the one irreversible-looking step**, and it is not:
  the file is in git history, and `tests/test_docs_sync_rule.py` asserts the
  rule it carried. What is genuinely lost is the `pull_request` trigger, which
  has never fired in this repo.
- **The new guards read prose**, so they will fail on a future document that
  cites a workflow or a root doc that has not been written yet. That is the
  same cost `COVERAGE_WITHOUT_PATHS` carries in the traceability guard: an
  exemption with a reason, checked in both directions.

## 5. Adjacent issues found, not fixed

Flagged per rule 10:

1. **`GSF-A1`** — `docs/MULTI_AGENT_WORKFLOW.md` describes the retired
   three-agent workflow throughout: worktrees per role, `AGENTS.md` ownership
   boundaries, and "Open/update PR with `.github/pull_request_template.md`".
   `CLAUDE.md` records that workflow as retired and PRs as not used here. Only
   the gate paragraph is corrected by this batch; the document as a whole
   describes a process this repo does not follow.
2. **`GSF-A2`** — `.github/pull_request_template.md` exists for pull requests
   this repo never opens. Same class as `SAG-A3`, one surface along.
3. **`GSF-N1`** above: eleven documents assume the master spec was renamed to
   match the app's name. This batch makes them name the file that exists, which
   settles the dead pointer and not the question.
