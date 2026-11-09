# Implementation plan — the bare `::name` citation form brought into the traceability guard (SBN)

**Date:** 2026-11-09
**Status: approved under the standing instruction and being built the same day.**
The user's instruction for this session was "proceed on your own recommendations
as I'm going to be away … you can then start on open items", and when the SAG
batch closed they chose this item by name ("SAG-A17 next"). Recorded here
rather than assumed, because the global rule is to stop after the plan.

**Closes:** `BACKLOG.md`'s `SAG-A17` (medium), and with it the scope note on
`PDT-A1`.

## 0. What this is

`tests/test_traceability_refs.py` checks a citation written as a path —
`tests/<file>.py::test_y`. A citation written as a bare continuation — a leading
`::` and a name, with no path — is matched by nothing, so it is never checked. `PDT-A1`
filed that against `docs/spec_coverage.md`; `SAG-M4` widened the guard's scan
to the plan, spec and handoff-note families and left the blind spot in place,
so the batch that repaired every dead path in those families tripled the
domain of the gap beside it. Two instances sat on the rows directly above one
`SAG-M4.3` repaired.

## 1. What was measured first

### 1.1 The domain

Over the four scanned families, with full citations masked out so only orphan
`::name` tokens remain, and counting only names that look like a test
(`test_*` or `Test*`):

| | count |
|---|---|
| bare `::test_*` citations | 1097, in 34 documents |
| of those, **resolving against nothing defined under `tests/`** | **68** occurrences, 59 distinct names, in 14 documents |
| of those 68, on a line that carries a retirement or "planned" marker | 16 |
| **dead and reading as live evidence** | **52** |

Of the 68, **38** have a candidate successor — a test sharing the spec-ID
prefix, or a near-match by name — and 30 have none. Every one needs a
judgement, which is why `SBN-M2` is a criterion and not a cleanup.

Re-measured over `HEAD` with the resolver as shipped, because the first count
of the marked subset was taken with a different keyword list: 68 occurrences,
16 of them on a line matching
`deleted|withdrawn|replaced|planned|not written|~~|retired|struck`, so 52 read
as live evidence. `BACKLOG.md`'s `SAG-A17` records 69 and 52 from the sixth
cold pass of the SAG batch, taken before this arm's resolver existed; the
figures here supersede it and its entry says so.

Measured with a scratch script, not committed, so §1.2's table in particular
cannot be reproduced from the repo — `SBN-A6`. What the repo does hold is the
rule itself, asserted over fixtures and over the real documents by `SBN-M1`'s
tests, and the dead count, which any checkout can re-derive by running
`tests/test_traceability_refs.py::test_sbnm21_every_bare_name_citation_resolves`
against an older commit's documents.

### 1.2 The resolution rule, and why `SAG-A17`'s own recommendation is rejected

`SAG-A17` says the right fix is to read the file from the nearest preceding
path-form citation in the same document — "what a human reader does" — and
calls the alternative, searching every file under `tests/`, "a weaker check".
Measured, that recommendation is wrong for this repo's prose:

| anchoring rule | bare citations that resolve | mismatch against the anchor | no anchor at all |
|---|---|---|---|
| a path on the same line | 206 | 257 | 390 |
| carried across lines, reset at headings | 754 | 356 | 283 |
| carried through the whole document | 814 | 556 | 23 |

A mismatch is not a dead test. These documents cite a second file in the same
table row, and a `## Status` section's prose cites a test in a different file
from the row above it, so the anchor is the wrong file far more often than the
name is dead. Enforcing it would demand rewriting **hundreds** of honest
citations, and the 51 that matter would arrive inside that noise.

So the rule is: **a bare `::test_*` citation must name something defined
somewhere under `tests/`.** It is weaker than the path form — it does not
prove the name is in the file the reader would open next — and it is the whole
of what can be checked without inventing a convention these documents do not
follow. The gap that remains is `SBN-A1`, stated rather than implied.

### 1.3 What stays out of the domain

**Bare names that are not tests.** 68 of them, 51 resolving against nothing
under `tests/` — and almost all name a *source* function
(`::update_action_item`, `::export_day`, `::_build_service`): a continuation of
a `src/…py` citation in a neighbouring cell, not a test reference at all. The
rest are abbreviation fragments of a test-ID list (`::_346a`, `::_255b`).
Including them would mean resolving against `src/` too, which is a different
guard. Filed as `SBN-A2`.

**A third citation form, the basename without the path.** `test_x.py::name`
is excluded by `_BARE`'s lookbehind and is read by neither arm: 54 of them in
the scanned families, 31 unresolvable, of which three cite a test. `SST-A2`
already carries it and stays open. Named here because this section is what a
reader consults to see how much of the gap `SBN-M1` closes, and it closes two
forms of three — found by the cold pass, which also measured that one of those
three names a test this batch retired elsewhere.

## 2. Acceptance criteria → tests

Spec IDs are this plan's own, `SBN-M*`. Tests live in
`tests/test_traceability_refs.py`.

| ID | criterion | test |
|---|---|---|
| SBN-M1.1 | A bare `::name` citation whose name looks like a test is in the guard's domain, and fails when the name is defined nowhere under `tests/` | `::test_sbnm11_a_bare_name_citation_is_checked` |
| SBN-M1.2 | A `::name` that belongs to a full citation is **not** read as bare — neither the trailing name of a `tests/<file>.py::name` citation, nor the second element of a `path::Class::method` chain, nor the continuation of a `src/…py::func` citation | `::test_sbnm12_a_name_in_a_full_citation_is_not_bare` |
| SBN-M1.3 | A bare name that is not a test name is out of the domain, and says so by construction rather than by omission | `::test_sbnm13_a_bare_non_test_name_is_out_of_the_domain` |
| SBN-M1.4 | The bare-name arm cannot go inert: the guard asserts that bare citations are being found and resolved in real documents, and that an invented name fails | `::test_this_guard_can_actually_fire` |
| SBN-M2.1 | Every one of the 68 dead bare citations is repaired: a renamed test re-cited by its real name, a retired one named **without** the `::` so it is history rather than a pointer | `::test_sbnm21_every_bare_name_citation_resolves`, over the real documents (the path arm's `::test_every_referenced_test_name_exists` was named here first and is **not** extended — the bare arm is a test of its own) |
| SBN-M2.2 | A repair that re-cites a different test is true — the named test asserts the criterion in that row | review, per row, recorded in the handoff note |
| SBN-N1 | **Not code-testable:** that a resolving bare name is the *right* test for its row, or even in the file the reader would open. §1.2 is the measurement that says why no rule available here can check it | human-verified for the rows this batch touches |

## 3. Implementation order

1. The guard's tokeniser and the bare-name arm, with `SBN-M1`'s four tests —
   red against the 68 before any document is touched, which is the proof the
   arm works.
2. The 68 repairs, document by document, in the order §1.1's table reports
   them.
3. Mutations, then one cold pass, then the records.

## 4. Risks, and what this does not close

- **`SBN-A1`: a bare name that resolves may still be the wrong test.** §1.2.
- **The repairs are the risk, not the guard.** 30 of the 68 have no candidate
  successor, so the honest repair is to name them without `::` and say what
  happened — which makes a criterion's evidence read as absent. That is the
  truth being recorded, and `docs/spec_coverage.md` rows that lose their only
  evidence are the ones to check hardest.
- **One citation is a form, not a reference.**
  `docs/unused-docs/changes/2026-11-09-ci-green.md` writes a bare `::` and a name while describing
  the citation convention itself. It is prose about the form and is rewritten,
  not resolved — a guard exemption for the literal name would be a hole.

## 5. Adjacent issues found, not fixed

Flagged per rule 10:

1. **`SBN-A2`** — the non-test bare names of §1.3 (51 dead of 68), which are
   `src/` citations and need a `src/`-resolving guard.
2. **`SAG-A18`** — `tests/` itself is outside the scan, undocumented. Found by
   the sixth cold pass of the SAG batch and still open.
