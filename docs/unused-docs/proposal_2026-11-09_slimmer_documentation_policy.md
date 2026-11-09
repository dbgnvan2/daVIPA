# Proposal — a slimmer per-batch documentation policy

**Status: draft 2026-11-09** — nothing in this proposal is applied. It changes
the project's own working agreements, so it waits for approval.

Batch id: **SDP**. Supersedes nothing; closes nothing.

## 1. What was measured

All figures taken 2026-11-09 at `8ac468d`, with the command that produced them
named, because every count in this repo that was copied forward rather than
re-measured has turned out to be wrong.

| | count | command |
|---|---|---|
| Tracked Markdown files | **251** | `git ls-files '*.md' \| wc -l` |
| Tracked Python files | 255 | `git ls-files '*.py' \| wc -l` |
| Markdown lines | 50,390 | `git ls-files '*.md' \| xargs wc -l` |
| Python lines | 123,507 | `git ls-files '*.py' \| xargs wc -l` |
| Handoff notes under `docs/unused-docs/changes/` | **151** | `git ls-files docs/changes \| wc -l` (150 dated notes plus its README) |
| Implementation plans | 31 | `git ls-files 'docs/unused-docs/implementation_plan*'` |
| Coverage snapshots | 7 | `git ls-files 'docs/spec_coverage*'` |
| Lines in notes + plans | **22,277** | 14,299 + 7,978, same two listings |
| New Markdown files since 2026-10-01 | 72 | `git log --since=2026-10-01 --diff-filter=A --name-only` |
| Commits since 2026-11-01: docs-only / touching `src/` | **131 / 73** | per-commit path classification |
| `BACKLOG.md` | 5,615 lines | `wc -l` |

Two of these carry the argument.

**One Markdown file per Python file, and 131 docs-only commits against 73
touching `src/` this month.** For a single-developer desktop application that
ratio is upside down.

**116 of the 150 dated handoff notes have never been cited by any document.**
Measured by taking each note's basename and searching every tracked `*.md`
other than the note itself:

```
cited at least once: 34
never cited:         116
```

So 77% of the notes are write-only. The 34 that are cited are cited almost
entirely by the four living documents — `docs/DOCUMENTATION_INDEX.md` (15),
`BACKLOG.md` (14), `docs/spec_coverage.md` (12) and `NOTES.md` (7) — which is
the useful case: a living document pointing at the measurement that justifies
a claim.

## 2. What causes the volume

Not the guards. The guards add no documents; they read the ones that exist.
The cause is that `CLAUDE.md` and `AGENTS.md` require, for **every** batch:

1. an implementation plan — a new file,
2. a handoff note at `docs/unused-docs/changes/<yyyy-mm-dd>-<topic>.md` — a new file,
3. a `docs/spec_coverage.md` section,
4. a `NOTES.md` bullet,
5. `BACKLOG.md` entries for what was closed and filed,
6. a `docs/DOCUMENTATION_INDEX.md` entry.

Six writes, two of them permanent new files, per batch. 150 dated notes means
roughly 150 batches since 2026-02-23, the date of the earliest one.

The handoff note is not only a prose rule. `tools/agents/check_docs_sync.py`
returns `missing-handoff` unless a changed path starts with `docs/unused-docs/changes/`,
and `tests/test_docs_sync_rule.py` asserts that outcome. So a batch that
changes code **cannot** pass the suite without adding a note file. That is
why the count grows at exactly one per batch, with no judgement applied.

## 3. The second-order cost

Each document makes checkable claims — counts, paths, "this is built", branch
distances, "the workflow is three agents". Claims go stale silently, and a
stale document reads as current, which is worse than no document. The last
three batches were all of this kind, and none of them changed application
behaviour:

- **GSF** — a workflow that documents named as the enforcement mechanism had
  never run in this repo.
- **MAW** — the three-agent workflow was recorded as retired on 2026-11-08
  while its document, three role prompts and bootstrap script all still read
  as current.
- **LDS** — the guards were reading 17 of the 41 documents that make claims.

Each was a real defect. But the surface that produced them is the one this
proposal shrinks: fewer living documents means fewer claims to police.

## 4. The proposal

### 4.1 Keep, unchanged

`CLAUDE.md`, `AGENTS.md`, `BACKLOG.md`, `NOTES.md`, `docs/USER_GUIDE.md`,
`docs/spec_coverage.md`, `docs/DOCUMENTATION_INDEX.md`, and the master spec.
These are the living set: each one is read before work, not after it.

`docs/spec_coverage.md` stays mandatory. It is the only record that maps a
spec criterion to the test that verifies it, and the global spec-traceability
rule depends on it.

### 4.2 Make conditional: the handoff note

A batch writes a note only when it leaves something a future reader needs that
a commit message cannot hold:

- a **measurement** that justifies a decision (an approach dropped after being
  measured, a count that took work to establish),
- **follow-ups** that are not already filed in `BACKLOG.md`,
- a **verification status that is not simply green** — tests skipped, a path
  left untested, a manual check still owed,
- work that **spans more than one session**, where the next session needs the
  state.

Otherwise the commit message carries it. The commit message is already
required to be substantive here, it is versioned with the change it describes,
and `git log` cannot drift from it.

Measured against the 150 existing notes, the conditions above would have kept
roughly the 34 that are cited plus any carrying a non-green status; the write-only
remainder would not have been written.

### 4.3 Make conditional: the implementation plan file

Planning stays required — the global rule to plan before code and stop for
approval is unchanged. What changes is whether the plan becomes a **file**.
It does when:

- the batch has more than about five acceptance criteria, or
- it touches `src/` behaviour users see, or
- it will outlive one session.

A small, self-contained batch states its plan in the conversation and records
its criteria in `docs/spec_coverage.md`, which is where they are looked up
anyway.

### 4.4 Archive the closed half of `BACKLOG.md`

At 5,615 lines it is the largest living document and the one most exposed to
stale claims, because closed items keep their original wording. Proposal:
closed items older than 30 days move to `docs/backlog_archive_<yyyy-mm>.md`,
a dated name, which the LDS rule keeps outside the live scanned set. The
living `BACKLOG.md` then holds open items and recent closures only.

### 4.5 Not proposed: deleting what exists

No retroactive deletion of notes or plans. Three reasons:

1. 34 notes are cited by living documents, and the citation guards now check
   those pointers — deleting a note turns a living document red.
2. Dated records are already outside the guarded set, so they cost nothing in
   maintenance. They cost disk.
3. The history is the one thing in this set that cannot be regenerated.

## 5. The exact edits, if approved

### 5.1 `CLAUDE.md`, lines 98-101

Replace:

> **After every batch of work**, write a handoff note at
> `docs/unused-docs/changes/<yyyy-mm-dd>-<topic>.md` using template
> `.agents/templates/handoff-note.md`. Required fields: summary, files changed,
> test/verification status, follow-ups.

with:

> **A batch writes a handoff note when it leaves something a commit message
> cannot hold**: a measurement behind a decision, follow-ups not already in
> `BACKLOG.md`, a verification status that is not plainly green, or state the
> next session needs. Otherwise the commit message is the record. Where one is
> written: `docs/unused-docs/changes/<yyyy-mm-dd>-<topic>.md`, template
> `.agents/templates/handoff-note.md`, fields summary, files changed,
> test/verification status, follow-ups. Measured 2026-11-09: 116 of 150 notes
> had never been cited by any document, and the note was mandatory because
> `check_docs_sync.py` demanded one, not because a reader wanted one.

### 5.2 `AGENTS.md`, the *Required handoff artifact* section

Retitle to *Handoff notes* and carry the same conditional wording, pointing at
`CLAUDE.md` for the conditions rather than restating them — a third copy of a
rule is what the MAW batch deleted a document for.

### 5.3 `tools/agents/check_docs_sync.py`

`verdict` currently requires both a `docs/` change and a `docs/unused-docs/changes/` path.
Change: a code or dependency change requires a **documentation** change;
the handoff note is no longer part of the decision. `MISSING_HANDOFF` leaves
the outcome set, which `OUTCOMES` declares explicitly, so the declaration and
the tests move with it.

This is reason **(b)** for a test change under the repo's test rules — the
behaviour changed intentionally — and it must be stated in the commit.

### 5.4 Tests that move with it

| Test | What changes | Reason |
|---|---|---|
| `tests/test_docs_sync_rule.py` | the `missing-handoff` outcome and its fixtures; the suite asserts every outcome `verdict` can return, so the list shrinks with it | (b) |
| `tests/test_doc_status_claims.py` | one assertion requires the status walk to reach a `docs/unused-docs/changes/` path "because every batch adds a handoff note" — that premise is what this proposal removes | (b) |

Both are repo-assertion tests under the `meta` marker; neither touches
application behaviour.

## 6. Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| SDP-M1.1 | A code change with a documentation change and no handoff note is a PASS | `tests/test_docs_sync_rule.py`, a new fixture case |
| SDP-M1.2 | A code change with no documentation change is still a FAIL | existing fixture, unchanged |
| SDP-M1.3 | `missing-handoff` is gone from the declared outcome set and from `verdict` | the existing test asserting the outcome set is exhaustive |
| SDP-M2.1 | The status walk no longer requires a `docs/unused-docs/changes/` path, and still reaches every living document | `tests/test_doc_status_claims.py` |
| SDP-M3.1 | `CLAUDE.md` and `AGENTS.md` state one rule between them, not two copies | `tests/test_repo_hygiene.py`, the existing agreement guard |
| SDP-N1 | **Not code-testable:** whether §4.4's backlog archive is wanted at all, and at 30 days or another window | human |

## 7. What could go wrong

- **The commit message becomes the only record, and commit messages are not
  read.** Mitigation: the conditions in §4.2 are written so that anything a
  reader would come looking for still gets a note. The risk is real for the
  case nobody anticipated.
- **A batch that should have written a note does not.** The note is currently
  guaranteed by a test. After this change it is a judgement call, and
  judgement is what drifts. This is the strongest argument against the change.
- **`docs/spec_coverage.md` absorbs the load** and grows faster, since small
  batches now record criteria there instead of in a plan file. It is 1,858
  lines today.

## 8. What this does not change

The global rules are untouched: plan before code and stop for approval, never
fabricate, docs stay current with behaviour in the same change (rule 13),
spec traceability, the sweep budget, one batch at a time. This proposal is
narrowly about whether **per-batch records become files by default**.
