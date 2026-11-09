"""The status claims in this repo's own documents, checked.

Nine `SSC` filings in `BACKLOG.md` were one defect wearing nine faces: a claim
that nothing checks. A plan headed itself "no implementation code written" over
code that shipped in August; a spec said "nothing is outstanding" eight lines
above two outstanding items; a coverage row named a method that does not exist;
one criterion count was given as 38, 40 and 41 in three documents. Every one of
them was found by a human reading, months late, because every automated check
in this repo reads ``Tests:`` references and nothing else.

These are the guards for the rest of that surface. They assert on the
REPOSITORY's documents, not on application behaviour, so they are marked
``meta`` like ``tests/test_traceability_refs.py`` — the marker is for the speed
of ``-m "not meta"``, never for skipping.

There are seven guards here and three companions proving a guard can fire
(P24), because a document guard that silently matches nothing is
indistinguishable from a document that is correct. The four without a
companion — SST-M4, SST-M7, SST-M9 and the second half of SST-M3 — each assert
on a named anchor in a named file, so a guard that stopped finding its subject
fails on the anchor rather than passing vacuously. That is weaker than a
companion and is filed as `SST-A4`.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta

REPO = Path(__file__).resolve().parents[1]

# ----------------------------------------------------------------- SST-M1/M2

# The documents whose status line may say the work is not built. Adding a plan
# here is a step in writing one; removing it is a step in finishing one. The
# guard checks BOTH directions, so a document that stays here after it is built
# fails as loudly as one that was never corrected.
#
# ``docs/changes/`` is outside this scan on purpose: a handoff note records what
# was true on its date and is not a status anybody reads for the current state.
# That exemption covers a claim that was true when written, not a figure that
# was never true — which is why SST-M3 does reach into the WTP handoff note for
# its criterion count. The second cold pass, 2026-11-09, read the two rules
# against each other and asked which was wrong; this is the line that was
# missing rather than a rule that was.
DRAFTS_NOT_BUILT = {
    # CIP — Google Calendar into the Plan. 42 `CIP-M…` criterion rows, no coverage
    # rows anywhere, no module under src/. The spec's own status line says the
    # user will start a session for it later.
    "docs/spec_2026-11-08_calendar_into_the_plan.md",
}

_STATUS_LINE = re.compile(r"^\*{0,2}status\b", re.I)

# A `## Status` heading with the claim on the line below it. The first version
# of this guard read only lines beginning with "Status" and so could not see
# `docs/implementation_plan_2026-06-06_project_notes.md`, whose `## Status`
# section said the plan awaited a sign-off over work that had shipped. Found by
# the cold pass over this batch, 2026-11-09.
_STATUS_HEADING = re.compile(r"^#+\s*\**status\b", re.I)

# A status section runs to the next heading of any level. It was a window of
# the first two non-blank lines until the second cold pass, 2026-11-09, which
# put a claim on the third line of a `## Status` section and watched the guard
# pass — and a status section longer than two lines is the normal shape here.
_ANY_HEADING = re.compile(r"^#{1,6} ")

# A phrase list, and therefore a tripwire rather than a proof: a new way of
# writing "not built" escapes it until it is added here. The phrases are the
# ones this repo has actually used, plus the nearest variants. A guard that
# tried to recognise the *meaning* would spend its failures on quotation, which
# is why corrections in this repo paraphrase the sentence they replace instead
# of quoting it.
#
# `SST-A3` files the structural fix, and the third cold pass raised it to high
# on evidence: the list missed two more documents whose work had shipped
# months earlier — a spec headed "Draft for implementation" and a plan whose
# `## Status` said it was ready for review. Both phrasings are below now,
# which is the same patch as last time. A deny-list of phrasings cannot be
# finished; the fix is to require a status line to *match* a recognised built /
# superseded / registered-draft form, so an unrecognised sentence fails. Three
# more documents recorded only an approval state ("approved; in progress") over
# built work, and no deny-list reaches those at all.
_NOT_BUILT = re.compile(
    r"awaiting approval"
    r"|not approved"
    r"|no implementation code"
    r"|no code written"
    r"|no code changed"
    r"|not built"
    r"|not started"
    r"|no code exists"
    r"|not yet implemented"
    r"|not yet built"
    r"|draft for implementation"
    r"|ready for review and approval",
    re.I,
)


def _status_documents():
    for pattern in ("docs/implementation_plan_*.md", "docs/spec_*.md"):
        for path in sorted(REPO.glob(pattern)):
            if path.name.startswith("spec_coverage"):
                continue
            yield path


def _claims_not_built(path):
    """The document's status lines that say the work is not written.

    A status line is one that begins with "Status", or any line in a section
    under a `## Status` heading, to the next heading. Prose elsewhere in a plan,
    narrating the state of the work at some past moment, is not a status claim:
    the one instance of it in this repo — the dopamine plan's §8 — is corrected
    in place rather than policed here, because a guard that read every sentence
    about implementation would spend its failures on quotation.
    """
    hits = []
    text = path.read_text(encoding="utf-8")
    in_status_section = False
    for number, line in enumerate(text.splitlines(), 1):
        if _STATUS_HEADING.match(line):
            in_status_section = True
            continue
        if in_status_section and _ANY_HEADING.match(line):
            in_status_section = False
        if (_STATUS_LINE.match(line) or in_status_section) and _NOT_BUILT.search(line):
            hits.append((number, line.strip()))
    return hits


def test_sstm1_no_document_claims_unwritten_code_outside_the_register():
    claiming = {}
    for path in _status_documents():
        hits = _claims_not_built(path)
        if hits:
            claiming[str(path.relative_to(REPO))] = hits

    unregistered = sorted(set(claiming) - DRAFTS_NOT_BUILT)
    assert not unregistered, (
        "these documents' status lines say the work is not written, and they "
        "are not in DRAFTS_NOT_BUILT. Either the work is built and the status "
        "line is stale, or the document belongs in the register:\n  "
        + "\n  ".join(
            f"{name}:{claiming[name][0][0]} — {claiming[name][0][1]}"
            for name in unregistered))

    stale = sorted(DRAFTS_NOT_BUILT - set(claiming))
    assert not stale, (
        "these documents are registered as not built but their status line no "
        "longer says so — if they were built, drop them from the register:\n  "
        + "\n  ".join(stale))


def test_sstm2_the_register_guard_can_fire():
    """Guards the guard: it has to read real documents and real status lines."""
    documents = list(_status_documents())
    # An exact count, not a floor: a floor is what let the reference guard in
    # tests/test_traceability_refs.py keep passing while its domain shrank.
    assert len(documents) == 35, (
        f"{len(documents)} plan/spec documents scanned, expected 35 — if one "
        "was added or removed, change this number deliberately")

    for name in sorted(DRAFTS_NOT_BUILT):
        assert (REPO / name).exists(), f"registered document is gone: {name}"
        assert _claims_not_built(REPO / name), (
            f"{name} is registered but its status line does not claim the work "
            "is unwritten, so the register's second direction is inert")

    # The patterns, against text rather than against the tree.
    assert _STATUS_HEADING.match("## Status")
    assert _STATUS_HEADING.match("### **Status**")
    assert not _STATUS_HEADING.match("Status is discussed in §6")
    # A `## Status report` heading is in the domain on purpose: it is a status
    # section, and a claim anywhere in it is a status claim.
    assert _STATUS_HEADING.match("## Status report")
    assert _ANY_HEADING.match("## Next steps") and not _ANY_HEADING.match("#not")
    assert _STATUS_LINE.match("**Status:** Draft, awaiting approval")
    assert _STATUS_LINE.match("Status: **awaiting approval**")
    assert not _STATUS_LINE.match("The status of this is awaiting approval")
    assert _NOT_BUILT.search("planned, not built — awaiting approval")
    assert _NOT_BUILT.search("Awaiting approval — no code changed yet.")
    assert not _NOT_BUILT.search("PRI-M1 and PRI-M2 are built and on `main`")


# ----------------------------------------------------------------- SST-M3/M4

WTP_SPEC = REPO / "docs/spec_2026-11-08_weekly_tactic_as_parent.md"
_WTP_ROW = re.compile(r"^\| *\*{0,2}(WTP-M[0-9.]+[a-z]?)\*{0,2}")


def _wtp_criteria():
    found = set()
    for line in WTP_SPEC.read_text(encoding="utf-8").splitlines():
        match = _WTP_ROW.match(line)
        if match:
            found.add(match.group(1))
    return found


def _wtp_status_report(spec):
    """§6's text alone, heading to next heading.

    The figure has to be checked where the spec *summarises* its own state, not
    anywhere in the file: the status line at the top states the count as well,
    which made a whole-file substring check unable to fail on §6 going stale.
    """
    heading = "## 6. Status report"
    assert heading in spec, (
        f"the WTP spec has no {heading!r} section — if §6 was renumbered or "
        "renamed, this guard needs the new anchor, not deleting")
    start = spec.index(heading)
    end = spec.find("\n## ", start)
    assert end != -1, "§6 is the last section; the slice would run to the end"
    return spec[start:end]


def test_sstm3_the_wtp_criterion_count_is_what_the_spec_lists():
    """38, 40 and 41 were all in the repo at once; the rows say which is right.

    The count is recounted here rather than pinned to a literal, so the figure
    in the prose is checked against the table it describes. `WTP-M1` to
    `WTP-M6` are section headings, not criteria — they never appear as a row's
    first cell, which is why this reads rows and not every mention.
    """
    criteria = _wtp_criteria()
    assert len(criteria) == 41, (
        f"the spec lists {len(criteria)} WTP criterion rows; every figure in "
        "prose that states the count has to be re-measured against it")

    spec = WTP_SPEC.read_text(encoding="utf-8")
    # Scoped to §6's summary. The first version asserted the figure against the
    # whole file, which the spec's own corrected status line also satisfies —
    # so §6 could go back to 40 and this guard would stay green. Found by the
    # cold pass over this batch, 2026-11-09.
    summary = _wtp_status_report(spec)
    assert f"all {len(criteria)} criteria" in summary, (
        f"§6's summary does not say 'all {len(criteria)} criteria' — it said "
        "40 while listing 41, and its arithmetic for 40 counted §3 as 35 after "
        "§3 had been amended to carry the additions")

    # `BACKLOG.md`'s header paragraph, anchored on its own sentence rather
    # than on the one historical wrong figure: the second cold pass set that
    # sentence to 40 and watched this guard pass, because the only assertion
    # here was that the string "all 38 criteria" was absent.
    backlog = (REPO / "BACKLOG.md").read_text(encoding="utf-8")
    assert f"in every reader of parenthood, all {len(criteria)} criteria" in backlog, (
        "BACKLOG.md's WTP sentence does not state the count the spec lists "
        f"({len(criteria)}); it has said 38 and 40 while the rows said "
        f"{len(criteria)}")

    # And `docs/DOCUMENTATION_INDEX.md`, the third document that disagreed in
    # the original defect and was in no guard's domain until now.
    index = (REPO / "docs/DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    entry_head = "### docs/spec_2026-11-08_weekly_tactic_as_parent.md"
    assert entry_head in index, "the WTP entry is gone from the index"
    start = index.index(entry_head)
    end = index.find("\n### ", start + len(entry_head))
    entry = index[start:end if end != -1 else len(index)]
    assert f"{len(criteria)} of {len(criteria)} criteria" in entry, (
        "the index's WTP entry does not state the count the spec lists "
        f"({len(criteria)} of {len(criteria)})")

    # The batch's own handoff note stated the count too, and kept 38 after
    # every other document had been corrected.
    note = (REPO / "docs/changes/2026-11-08-weekly-tactic-as-parent.md").read_text(
        encoding="utf-8")
    assert f"{len(criteria)} criteria" in note, (
        "the WTP handoff note does not state the criterion count the spec "
        f"lists ({len(criteria)})")
    assert "38 criteria" not in note, (
        "the WTP handoff note still states 38 criteria")


def test_sstm4_the_wtp_spec_does_not_deny_its_own_outstanding_items():
    spec = WTP_SPEC.read_text(encoding="utf-8")
    assert "nothing is outstanding" not in spec.lower(), (
        "the spec says nothing is outstanding; it then lists two "
        "'not code-testable' items, both `not done`")
    assert '### The two "not code-testable" items' in spec, (
        "the section holding the two outstanding items is gone — if they were "
        "closed, the summary and this guard both need rewriting, not deleting")


# ------------------------------------------------------------------- SST-M5

# A reference in an Implementation column: `file.py::symbol`, or a bare
# `::symbol` continuing the file named before it on the same line. A bare
# `::test_…` belongs to the Tests column, which tests/test_traceability_refs.py
# checks, so it is attributed to nothing here.
_SYMBOL_REF = re.compile(r"`(?:([\w/]+\.py))?::(\w+)`")


def _references_on(line):
    """(file, symbol) for every implementation reference on one line."""
    found = []
    carried = None
    for match in _SYMBOL_REF.finditer(line):
        filename, symbol = match.group(1), match.group(2)
        if filename:
            carried = filename
        if symbol.startswith("test_"):
            continue
        target = filename or carried
        if target is None:
            continue
        if target.rsplit("/", 1)[-1].startswith("test_"):
            continue
        found.append((target, symbol))
    return found


def _implementation_references():
    for path in sorted(REPO.glob("docs/spec_coverage*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            for target, symbol in _references_on(line):
                yield path.relative_to(REPO), target, symbol


def _defined_names():
    sources = [
        *sorted(REPO.glob("src/**/*.py")),
        *sorted(REPO.glob("tools/**/*.py")),
        REPO / "conftest.py",
    ]
    names = set()
    for path in sources:
        text = path.read_text(encoding="utf-8", errors="ignore")
        names |= set(re.findall(r"^\s*(?:async )?def (\w+)", text, re.M))
        names |= set(re.findall(r"^class (\w+)", text, re.M))
        names |= set(re.findall(r"^(\w+)\s*[:=]", text, re.M))
    return names


def test_sstm5_every_implementation_reference_resolves():
    """The Implementation column was unchecked, and had rotted.

    `RP-2.5` named `db_manager.py::_update_action_item`. The module has
    `_write_new_action_item` and `update_action_item`; nothing named
    `_update_action_item` has ever existed in `src/` or `tools/`. A plain
    ``grep -r _update_action_item src/`` prints two lines, both
    `bulk_update_action_items`, which carries the name as a substring — so the
    defect survived a grep as well as a reading.

    The symbol is resolved by name across `src/`, `tools/` and `conftest.py`
    rather than inside the file the row names. A row naming the wrong file but
    a real method is a lesser defect than one naming a method that does not
    exist, and chasing the former would fail this guard on the many rows that
    name a helper's home module rather than its caller.
    """
    names = _defined_names()
    unresolved = sorted({
        f"{source}: {target}::{symbol}"
        for source, target, symbol in _implementation_references()
        if symbol not in names
    })
    assert not unresolved, (
        "these coverage rows name an implementation symbol that is defined "
        "nowhere in src/, tools/ or conftest.py:\n  " + "\n  ".join(unresolved))


def test_sstm5_that_guard_can_fire():
    found = list(_implementation_references())
    # Exact, for the same reason as the document count above.
    assert len(found) == 186, (
        f"{len(found)} implementation references found, expected 186 — the "
        "pattern or the document set has changed; re-measure deliberately "
        "rather than lowering this")
    assert any(symbol.startswith("_") for _s, _t, symbol in found), (
        "no private symbol among the references, so the one defect this guard "
        "was written for would not have been in its domain")

    # The continuation form, which is how that defect was written.
    row = ("| RP-2.5 | x | `db_manager.py::_write_new_action_item`, "
           "`::_update_action_item` | `tests/t.py::test_rp25_x` | done |")
    assert _references_on(row) == [
        ("db_manager.py", "_write_new_action_item"),
        ("db_manager.py", "_update_action_item"),
    ], "the bare ::symbol continuation is not being attributed to its file"

    # And a Tests-column name must not be attributed to the file beside it.
    assert _references_on("| x | `screens/plan.py::build` | `::test_pdm1_x` |") == [
        ("screens/plan.py", "build"),
    ]


# ------------------------------------------------------------------- SST-M7

# Where each of the two filings declares itself. The two are written in two
# different formats — `### PLC-A5 — …`, and a dated
# `### 2026-11-08 - Type: Technical Debt` heading with `**Title:** UPD-A13 - …`
# under it — so each is found by its own declaration line, not by a heading
# built out of its name.
_FILING_ANCHORS = {
    "UPD-A13": re.compile(r"^\*\*Title:\*\* UPD-A13\b", re.M),
    "PLC-A5": re.compile(r"^### PLC-A5\b", re.M),
}


def _filing_body(backlog, name):
    """One filing's text, from the heading that owns it to the next heading.

    The first version of this took the body from the first *mention* of the
    name. Both names are mentioned in this file's opening summary, above any
    `###` heading, so the walk back found nothing, the slice started at byte 0,
    and the guard asserted that the whole file contains both names — which it
    does. It passed while neither filing mentioned the other. A guard that
    cannot locate what it reads is the defect this batch is about, written into
    the batch's own tooling.
    """
    anchor = _FILING_ANCHORS[name].search(backlog)
    assert anchor, f"the {name} filing's declaration line is gone"
    start = backlog.rfind("\n### ", 0, anchor.start())
    assert start != -1, f"the {name} filing sits under no heading"
    end = backlog.find("\n### ", anchor.end())
    return backlog[start:end if end != -1 else len(backlog)]


def test_sstm7_the_two_filings_of_the_index_gap_cross_reference():
    """One gap, filed twice at two severities, with no pointer between them.

    `UPD-A13` carries the designed fix at medium; `PLC-A5` files the same gap at
    low, and six places route the reader to `PLC-A5`. A reader following any of
    them landed on the low item and never reached the design.
    """
    backlog = (REPO / "BACKLOG.md").read_text(encoding="utf-8")
    assert "UPD-A13" in backlog and "PLC-A5" in backlog, (
        "one of the two filings of the documentation-index gap is gone")

    for name, other in (("UPD-A13", "PLC-A5"), ("PLC-A5", "UPD-A13")):
        body = _filing_body(backlog, name)
        assert other in body, (
            f"the {name} filing does not mention {other}, so a reader landing "
            "on it never learns the same gap is filed again elsewhere")


# ------------------------------------------------------------------- SST-M8

# The four documents every batch edits, so a line number in a cite into them is
# wrong within hours. The rule was adopted on 2026-11-08 after a commit whose
# own subject was "stop citing by line number" added a cite that its parent
# commit had already moved.
CHRONIC = ("BACKLOG.md", "docs/spec_coverage.md", "CLAUDE.md",
           "docs/DOCUMENTATION_INDEX.md")
# The basename, with any path prefix or none: this repo writes both
# `docs/spec_coverage.md:69` and the bare `spec_coverage.md:69`. The second
# cold pass wrote bare-basename cites into `NOTES.md` and watched the guard
# pass; no such cite existed in the repo, so the hole was latent.
_LINE_CITE = re.compile(
    r"(?:BACKLOG|spec_coverage|CLAUDE|DOCUMENTATION_INDEX)\.md:[0-9]")


def _markdown_files():
    for path in sorted(REPO.rglob("*.md")):
        parts = set(path.parts)
        if parts & {".git", "venv", "build", "dist", ".claude", "node_modules"}:
            continue
        yield path


def test_sstm8_the_chronic_documents_are_not_cited_by_line_number():
    offenders = []
    for path in _markdown_files():
        for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            if _LINE_CITE.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{number}")
    assert not offenders, (
        "these cite one of "
        + ", ".join(CHRONIC)
        + " by line number. Quote the text and give the grep that finds it; "
          "every batch edits these four, so the number is wrong within "
          "hours:\n  " + "\n  ".join(offenders))


def test_sstm8_that_guard_can_fire():
    scanned = {str(p.relative_to(REPO)) for p in _markdown_files()}
    # Membership, not a count. A floor of 140 is what let the reference guard in
    # tests/test_traceability_refs.py tolerate losing most of its domain
    # (`SST-A1`), and an exact count here would turn the suite red on every
    # batch, because every batch adds a handoff note. What the walk has to reach
    # is the four chronic documents it polices and at least one file from each
    # directory markdown lives in.
    for name in CHRONIC:
        assert name in scanned, f"the walk no longer reaches {name}"
    assert "NOTES.md" in scanned
    assert any(n.startswith("docs/changes/") for n in scanned), (
        "no handoff note in the walk — docs/changes/ has dropped out")
    assert any(n.startswith("docs/cycles/") for n in scanned), (
        "no gate record in the walk — docs/cycles/ has dropped out")
    assert any(
        n.startswith("docs/implementation_plan_") for n in scanned), (
        "no implementation plan in the walk")
    assert _LINE_CITE.search("see `BACKLOG.md:114` for the filing")
    assert _LINE_CITE.search("docs/spec_coverage.md:69 names it")
    assert _LINE_CITE.search("spec_coverage.md:69 names it")
    assert _LINE_CITE.search("see DOCUMENTATION_INDEX.md:402")
    assert not _LINE_CITE.search("see `BACKLOG.md` item 2")
    # A dated filename is not a line cite.
    assert not _LINE_CITE.search("docs/changes/2026-11-08-pri-tests.md")


# ------------------------------------------------------------------- SST-M9

PRI_PLAN = REPO / "docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md"

# ------------------------------------------------------------------ SST-M10

# The batch's records. SST-M10 was recorded `done` against "the docs-sync
# gate", which cannot produce that status: `tools/agents/check_docs_sync.py`
# only asserts that *some* path under `docs/` changed alongside code, and
# `.github/workflows/agent-docs-gate.yml` runs on `pull_request` only, while
# this repo pushes to `main` and opens no pull requests. So the criterion's
# named evidence had never run. Found by the second cold pass, 2026-11-09;
# `SST-A8` files the dead gate itself.
SST_RECORDS = (
    "BACKLOG.md",
    "NOTES.md",
    "docs/DOCUMENTATION_INDEX.md",
    "docs/spec_coverage.md",
    "docs/implementation_plan_2026-11-08_status_claims.md",
    "docs/changes/2026-11-08-status-claims.md",
)
_SST_ID = re.compile(r"\bSST-(?:M|A|N)[0-9]+\b")


def test_sstm10_every_record_of_this_batch_exists_and_names_it():
    """A weak guard, and weaker than the one it replaces claimed to be.

    It proves each record exists and refers to the batch by at least one of its
    own IDs. It cannot prove the record is accurate — `SST-N1` already says
    that about status lines generally, and the two cold passes over this batch
    found eleven and six defects in exactly that gap.
    """
    missing = [name for name in SST_RECORDS if not (REPO / name).exists()]
    assert not missing, "these records of the SST batch are gone: " + ", ".join(missing)

    silent = [
        name for name in SST_RECORDS
        if not _SST_ID.search((REPO / name).read_text(encoding="utf-8"))
    ]
    assert not silent, (
        "these records name no `SST-…` criterion or adjacent issue, so the "
        "batch is no longer traceable from them: " + ", ".join(silent))


def test_sstm9_every_promised_pri_adjacent_item_is_filed():
    """The plan's last section promises four filings; none of them existed.

    The promise is under "Adjacent issues found, not fixed" — the plan's
    sections are not numbered — and is repeated in
    `docs/DOCUMENTATION_INDEX.md`, so two documents asserted the existence of
    items that were nowhere.
    """
    plan = PRI_PLAN.read_text(encoding="utf-8")
    # The plan names the range by its endpoints — "`PRI-A1`-`PRI-A4`" and
    # "filed in `BACKLOG.md` as PRI-A1 … PRI-A4" — so the promise is read as a
    # range rather than as four literals, and the four numbered entries under
    # its "Adjacent issues found, not fixed" heading are counted to confirm
    # the range's size.
    section_head = "## Adjacent issues found, not fixed"
    assert section_head in plan, (
        f"the PRI plan has no {section_head!r} section, so the promise this "
        "guard reads is gone — rewrite it, do not delete it")
    section = plan[plan.index(section_head):]
    numbered = re.findall(r"^[0-9]+\. \*\*", section, re.M)
    assert len(numbered) == 4, (
        f"the plan lists {len(numbered)} adjacent issues under a promise to "
        "file four")
    promised = [f"PRI-A{n}" for n in range(1, len(numbered) + 1)]

    # Every name the plan mentions has to be inside the range it promised. The
    # previous form asserted that the set of names mentioned was exactly the
    # two endpoints, so naming all four in the plan — the natural edit now that
    # they are filed — turned this red with nothing wrong. Measured by the
    # second cold pass, 2026-11-09.
    mentioned = sorted(set(re.findall(r"PRI-A[0-9]+", plan)))
    outside = [name for name in mentioned if name not in promised]
    assert not outside, (
        f"the PRI plan names {outside}, outside the {len(numbered)} it promises "
        "to file under its adjacent-issues heading")

    backlog = (REPO / "BACKLOG.md").read_text(encoding="utf-8")
    # The name must end the token: `### PRI-A3` as a substring is also present
    # in `### PRI-A3x`, and a mutation that renamed the heading that way left
    # this guard green.
    unfiled = [
        name for name in promised
        if not re.search(rf"^### {name}\b", backlog, re.M)
    ]
    assert not unfiled, (
        "the PRI plan and docs/DOCUMENTATION_INDEX.md both say these are filed "
        "in BACKLOG.md; they are not: " + ", ".join(unfiled))
