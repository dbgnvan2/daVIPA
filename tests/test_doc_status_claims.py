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

There are thirteen guards here and three companions proving a guard can fire
(P24), because a document guard that silently matches nothing is
indistinguishable from a document that is correct. Ten of the thirteen have no
companion. Four of those — SST-M4, SST-M7, SST-M9 and the second half of
SST-M3 — each assert on a named anchor in a named file, so a guard that stopped
finding its subject
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
    names = {str(path.relative_to(REPO)) for path in documents}
    # Membership per family, not a total. This asserted `== 35` until the
    # fourth cold pass measured the total over the last 40 first-parent
    # commits and found three distinct values, moving twice inside two days:
    # the count rises with every plan document, and committing a plan is the
    # first step of every batch here. Its only failure mode was "someone
    # wrote a plan", which is the tax this repo's own CLAUDE.md note about
    # the meta test counts warns against ("one that did would go red on
    # every batch"). Narrowing the glob to one family, or dropping either
    # anchor document, still fails.
    for anchor in ("docs/implementation_plan_2026-11-08_status_claims.md",
                   "docs/spec_2026-11-08_weekly_tactic_as_parent.md"):
        assert anchor in names, (
            f"{anchor} is not in the scanned set, so the glob no longer "
            "reaches the document family it names")
    assert not [name for name in names if not name.endswith(".md")], (
        "a non-markdown path reached the scan")

    # The register's second direction reads the allow-list, not the deny-list.
    # It asked `_claims_not_built` until the third cold pass found the double
    # bind: a document headed "Status: Draft." classifies as `draft`, so
    # SAG-M1.3 requires it to be registered, and registering it made THIS
    # assertion red, because `_NOT_BUILT` does not accept "Draft." on its own.
    # Two vocabularies, no document stating either, and the plainest draft
    # status in the repo's own first step unable to satisfy both. Changed on
    # purpose (test rule (b)); `test_sagm13` holds the same pair of directions.
    for name in sorted(DRAFTS_NOT_BUILT):
        assert (REPO / name).exists(), f"registered document is gone: {name}"
        assert registered_claim_is_unbuilt(REPO / name), (
            f"{name} is registered but its status claim does not read as an "
            "unbuilt form, so the register's second direction is inert")

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


# ------------------------------------------------------------------- SAG-M1
#
# The inversion. `_NOT_BUILT` above is a deny-list: it can only reject a
# phrasing someone has already met. Three cold passes over the SST batch each
# found documents it could not see, and each was answered by lengthening it —
# the same patch three times, which is the measured record in `SST-A3`.
#
# This guard reads the other way round. A document's status claim must MATCH a
# recognised form, so silence, an approval state, or a new way of writing "not
# built" fails rather than passes. `SST-A3` put the cost at "a convention
# imposed on 35 existing documents"; measured, it was six, and §1.1 of the
# plan names them. (`_NOT_BUILT` holds twelve phrasings, not the ten the first
# records of this batch said: the last two were added by the SST batch's own
# third cold pass, which is the measured record the paragraph above is about.)
#
# What it still cannot do is judge whether a recognised claim is TRUE. SST-N1
# said that of the deny-list and it is just as true here (SAG-N1). What changes
# is the default.

#: The words this repo uses to say the work exists. One vocabulary, read by
#: `_BUILT_SHAPES` — the four shapes of the single form that claims the work
#: exists — so "Implementation is complete" and "built" are the same claim
#: rather than one recognised and one not. It was shared by three separate
#: forms until the third cold pass made them one.
#:
#: `live` was in this list until the cold pass, 2026-11-09, which pointed out
#: that "Live question, no answer yet" classifies as a built claim and that no
#: document here has ever used the word. A vocabulary word that only an unusual
#: sentence can reach is a hole, not a convenience.
_BUILT = r"(?:built|implemented|shipped|complete|completed|done)"

#: Each form is named, and the name appears in the failure message, so a
#: document that fails says which forms it was measured against rather than
#: printing one long alternation.
#:
#: **Order matters, and it is the unbuilt forms first.** `built` is the only
#: form that does not have to match at position 0, so when it was tried first
#: it shadowed the other three: "Draft — design complete, awaiting approval"
#: and "Awaiting approval; the spec is complete" both classified as `built`,
#: which is the opposite of what they say. Measured by the fourth cold pass,
#: 2026-11-09, over the third pass's own fix.
#:
#: There were five forms before the third cold pass — `built`,
#: `approved-and-built`, `partly-built` — one rule written three times, each
#: with a prefix enumerating the punctuation an ID list may contain. The
#: enumeration had been widened once and still rejected `&` and `:`, so it was
#: replaced with a built word anywhere in the first sentence. That was too
#: loose: the fourth pass measured "Spec complete, implementation not started."
#: and "Design done, no code yet." as `built`, where the deny-list this guard
#: replaces would have caught both. A guard that accepts a false claim in
#: silence is worse than one that rejects a true claim loudly, so the form is
#: anchored again — as a short list of *shapes*, each with a reason, rather
#: than as a class of permitted characters:
#:
#:   (a) the claim leads with the state — "built and on `main`"
#:   (b) only digits and punctuation come first — "2026-11-10 — built and on …"
#:   (c) the built word is a predicate — "M1, M2 and M3 are built."
#:   (d) an approval and a build in one sentence — "approved … and built."
#:
#: Nothing else is a built claim. "Spec complete, implementation not started."
#: matches none of the four, so the unbuilt forms get it; "All criteria done."
#: and "PD-M1 built, PD-M2 outstanding." match none either and fail loudly,
#: which is the right direction — "All criteria are done." is (c).
_BUILT_SHAPES = (
    rf"{_BUILT}\b",                                   # (a)
    rf"[^.!?a-zA-Z]*{_BUILT}\b",                       # (b)
    rf"[^.!?]*\b(?:is|are|was|were)\s+{_BUILT}\b",    # (c)
    rf"approved\b[^.!?]*\b{_BUILT}\b",               # (d)
)

_STATUS_FORMS = {
    "superseded": re.compile(r"^(superseded|withdrawn|abandoned)\b", re.I),
    # The two forms that do not claim the work exists. Both put a document in
    # DRAFTS_NOT_BUILT, and the negation check below does not apply to them:
    # "Not approved." is a negation by design, and the check is there to stop a
    # negation inverting a *built* claim. It made `not approved` an unreachable
    # alternative of this form until the third cold pass measured it.
    "draft": re.compile(r"^(draft|planned|proposed|not approved)\b", re.I),
    # The deny-list's own vocabulary, read the other way round: the twelve
    # phrasings `_NOT_BUILT` accepts as a registerable claim are a recognised
    # FORM, so the two guards cannot disagree about what an unbuilt status
    # looks like. Ten of the twelve were in that state — legitimate under
    # SST-M1 once registered, and red under SAG-M1.1 with no way to register
    # out. Measured by the third cold pass, 2026-11-09.
    #
    # It reads the whole first sentence, which is what catches "Spec complete,
    # implementation not started." now that it is tried before `built`.
    "not-built": re.compile(rf"^[^.!?]*(?:{_NOT_BUILT.pattern})", re.I),
    "built": re.compile("|".join(rf"^(?:{shape})" for shape in _BUILT_SHAPES),
                        re.I),
}

#: The forms that do not claim the work exists. A document whose claim matches
#: one of these belongs in `DRAFTS_NOT_BUILT`, and `SAG-M1.3` holds both
#: directions.
_UNBUILT_FORMS = ("draft", "not-built")

#: A built word reached only after a negation is not a built claim.
#: "Nothing is built yet" matches `partly-built` on its face, which would have
#: made the inversion weaker than the deny-list it replaces for exactly the
#: sentences SST-A3 is about.
#:
#: The negated words are enumerated rather than matched as a prefix. The first
#: version had `un\w+` in this alternation and so rejected "approved **under**
#: the standing instruction and built the same day" — two of this repo's own
#: plans — along with any status mentioning the *unified* panel or an
#: *unplanned* criterion. A pattern that broad fails on correct work, which is
#: the tax this file's other guards were rewritten to stop paying.
_NEGATION_WORDS = (r"not|no|nothing|none|never|without"
                   r"|unbuilt|unimplemented|unstarted|unfinished|undone")
_NEGATION = re.compile(rf"\b({_NEGATION_WORDS})\b", re.I)


def registered_claim_is_unbuilt(path):
    """Does this document's status claim read as work that is not written?

    The register's contract, as one function, because two guards ask it —
    `test_sstm2` and `SAG-M1.3` — and they asked it two different ways until
    the third cold pass, 2026-11-09. `test_sstm2` asked `_claims_not_built`,
    the deny-list; `SAG-M1.3` asked the allow-list. A document headed
    "Status: Draft." answers yes to the second and no to the first, so it had
    to be registered and could not be, and the repo's own first step is to
    commit a plan in exactly that state.
    """
    return classify_status_claim(_status_claim(path)) in _UNBUILT_FORMS


def _status_claim(path):
    """The document's first status claim, or None.

    "First" is the scope, and it is a decision rather than an oversight: every
    stale claim the three cold passes found was in the document's leading
    `**Status:**` line or the first line of its `## Status` section — the one a
    reader reads for the current state. Later status lines keep `_NOT_BUILT` as
    a tripwire, and the residue is filed as `SAG-A1`.
    """
    in_section = False
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        # A fenced block is an example, not a claim. These documents quote
        # status conventions and the handoff-note template, whose own `Status`
        # field would otherwise be read as the document's claim — in either
        # direction: a quoted "built" line hid a real draft, and a quoted "not
        # built" line would demand that built work be registered. No real
        # document has one today; found by the fourth cold pass, 2026-11-09,
        # before one did.
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if _STATUS_HEADING.match(line):
            in_section = True
            continue
        if in_section and _ANY_HEADING.match(line):
            in_section = False
        if _STATUS_LINE.match(line):
            return _strip_status_label(line)
        if in_section and line.strip():
            # A markdown table row is not a one-line claim. A `## Status`
            # section that opens with a criterion/state table used to make the
            # header row the claim, which matched no form; now the sentence
            # below the table is found instead. A section that is *only* a
            # table still has no claim, and fails with the message below
            # saying so (fourth cold pass, 2026-11-09).
            if line.lstrip().startswith("|"):
                continue
            return _strip_status_label(line)
    return None


def _strip_status_label(line):
    """"**Status:** — _built and on `main`_." -> "built and on `main`.".

    The separator and the emphasis have to come off as well as the label,
    because every form is anchored at `^`. The first version removed `**` and
    the label only, so "**Status** — built and on `main`." — the dash before
    the state rather than after it, which is this repo's commonest status
    style — matched no form at all. It was green only because the six documents
    this batch edited happen to put the dash after the built word. Found cold,
    2026-11-09.
    """
    # A leading list marker comes off first, or the label is not at `^` and
    # nothing after this strips it: "- **Status:** Draft." kept its label and
    # so matched no anchored form, which landed only on draft and superseded
    # documents, because `built` had been left unanchored. Fourth cold pass.
    text = re.sub(r"^[-*+\u2022]\s+", "", line.strip())
    text = re.sub(r"^\*{0,2}status\*{0,2}\s*:?\s*", "", text, flags=re.I)
    text = text.replace("**", "").replace("*", "")
    return text.strip(" \t_:\u2013\u2014-").strip()


#: A built word that is a question, or that the next word negates, is not a
#: claim that the work exists: "Shipped? not yet." and "Done nothing yet."
#: both matched the forms above until the cold pass measured them, 2026-11-09.
_CANCELLED = re.compile(rf"^\s*(?:\?|\b(?:{_NEGATION_WORDS})\b)", re.I)


def classify_status_claim(text):
    """The form this claim matches, or None. Public so the tests can drive it.

    A form matches when its pattern matches and — for the forms that claim the
    work exists — nothing before the end of the match negates it and the match
    is not immediately cancelled by a question mark or a negation. The two
    unbuilt forms are exempt from both checks, because a negation is what they
    are made of.

    What this still cannot see is a built word used as an adjective —
    "Complete rewrite proposed." classifies as `built`. Filed as `SAG-A8`
    rather than guessed at: recognising that needs the word's part of speech,
    and a guard that tried would spend its failures on grammar.
    """
    if not text:
        return None
    for name, pattern in _STATUS_FORMS.items():
        match = pattern.match(text)
        if not match:
            continue
        if name not in _UNBUILT_FORMS:
            # A negation only matters where it can invert a claim that the
            # work exists. Applying it to `draft` and `not-built` discarded
            # the very words those forms are made of.
            if _NEGATION.search(text[:match.end()]):
                continue
            if _CANCELLED.match(text[match.end():]):
                continue
        return name
    return None


def test_sagm11_every_status_claim_matches_a_recognised_form():
    """SAG-M1.1 — an unrecognised status claim fails, including no claim."""
    unrecognised = {}
    for path in _status_documents():
        name = str(path.relative_to(REPO))
        claim = _status_claim(path)
        if classify_status_claim(claim) is None:
            unrecognised[name] = claim or "<no status claim at all>"

    assert not unrecognised, (
        "these documents' first status claim matches none of the recognised "
        f"forms {sorted(_STATUS_FORMS)}. A plan or spec has to say what state "
        "it is in, in a form a reader and this guard both recognise — lead "
        "with the state, not with the approval, and give a sentence rather "
        "than only a table:\n  "
        + "\n  ".join(f"{name} — {claim[:110]}"
                       for name, claim in sorted(unrecognised.items())))


def test_sagm12_an_unrecognised_status_claim_is_rejected():
    """SAG-M1.2 — the sentences a deny-list cannot reach.

    These are the shapes the third cold pass measured on real documents, where
    a deny-list of "not built" phrasings reaches none of them: a status that
    records only an approval, a question, or silence.

    The sentence SST-A3 was filed for — "Draft, implementation not scheduled.
    No code exists yet." — is **not** here, and that is the point rather than
    an omission: under the inversion it is recognised as a `draft` form, which
    SAG-M1.3 then requires to be in `DRAFTS_NOT_BUILT`. The deny-list let it
    pass with nothing recorded anywhere; the allow-list makes it a registration
    or a failure.
    """
    for claim in (
            "approved; in progress",
            "approved to proceed",
            "awaiting the user's decision",
            "under discussion",
            "Nothing is built yet.",
            # Found cold, 2026-11-09: a built word the next word negates, and
            # one that is a question. Both matched a form before the fix, and
            # neither contains a phrase `_NOT_BUILT` can see, so they passed
            # both guards — the exact class SAG-M1 exists to stop.
            "Done nothing yet.",
            "Shipped? not yet.",
            "Completed? No.",
            # "live" was in the vocabulary until the same pass.
            "Live question, no answer yet.",
            # Found by the fourth cold pass, 2026-11-09, as **false accepts**
            # of the third pass's own fix: a built word whose subject is the
            # spec, the design or the review, in a sentence that says the code
            # does not exist. The deny-list this guard replaces caught the
            # first of these; an unanchored built form did not, which made the
            # inversion weaker than the list on the sentences SST-A3 is about.
            "Design done, no code yet.",
            "Planning complete, nothing written yet.",
            "Review complete, implementation deferred.",
            "Research complete. Implementation to follow.",
            # These two were accepted by the third pass's form and are now
            # rejected on purpose: neither is one of the four built shapes, and
            # failing loudly is the right direction — "All criteria are done."
            # is shape (c) and passes.
            "All criteria done.",
            "PD-M1 built, PD-M2 outstanding.",
            "no code has been written for this",
            "unimplemented",
            "TBD",
            "",
    ):
        assert classify_status_claim(claim) is None, (
            f"{claim!r} was accepted as a recognised status form, so the "
            "allow-list is as permissive as the deny-list it replaces")

    for claim, expected in (
            ("built and on `main`. `conftest.py` carries it.", "built"),
            ("Built and on `main`.", "built"),
            ("implemented 2026-11-07. Section 5 records the departures.", "built"),
            # These were three separate forms — `built`, `approved-and-built`,
            # `partly-built` — until the third cold pass collapsed them into
            # one rule: a built word in the first sentence, un-negated. The
            # expected names change here because the forms changed on purpose
            # (test rule (b)), not because the test was made to pass.
            ("approved and implemented (PB-M1 to PB-M5 approved 2026-11-06)",
             "built"),
            ("approved 2026-11-08 and built. M1-M5 implemented.", "built"),
            ("PRI-M1 and PRI-M2 are built and on `main`; PRI-M3 is not.",
             "built"),
            ("superseded by PD-M13, which takes the modal off the drop path",
             "superseded"),
            ("draft, not approved, on the backlog.", "draft"),
            # SST-A3's own sentence, recognised rather than ignored.
            ("Draft, implementation not scheduled. No code exists yet.",
             "draft"),
            # An ID list is how this repo writes a partial state, and it
            # writes them with commas, slashes, brackets and three dashes.
            # Every one of these failed before the cold pass, which means the
            # next batch's own status line would have failed.
            ("M1, M2 and M3 are built.", "built"),
            ("SAG-M1/M2 are built.", "built"),
            ("PD-M1 \u2013 PD-M6 are shipped.", "built"),
            ("All of M1 (the hard part) are built.", "built"),
            # One vocabulary: these two were unrecognised while "built" was
            # recognised, when each form carried its own word list.
            ("Implementation is complete.", "built"),
            ("Everything is done.", "built"),
            # Measured by the third cold pass as claims the enumerated prefix
            # rejected on correct work. `[^.!?]*` is a sentence rather than a
            # list of punctuation, so these need no further patch.
            ("All criteria are done.", "built"),
            ("2026-11-10 \u2014 built and on `main`.", "built"),
            ("SAG-M1 & SAG-M2 are built.", "built"),
            ("`SAG-M1`: both halves are built.", "built"),
            # The unbuilt forms are tried first, so a claim that leads with
            # its state keeps it. All three of these classified as `built`
            # while `built` was tried first and unanchored — the opposite of
            # what they say (fourth cold pass).
            ("Spec complete, implementation not started.", "not-built"),
            ("Draft \u2014 design complete, awaiting approval", "draft"),
            ("Awaiting approval; the spec is complete", "not-built"),
            # `not approved` was an alternative of the `draft` form that the
            # negation check discarded, so it could never match: a document
            # headed "Status: Not approved." failed, and registering it did
            # not help because SAG-M1.1 scans every document.
            ("Not approved.", "draft"),
            ("Draft.", "draft"),
            # Every phrasing `_NOT_BUILT` accepts as a registerable claim is
            # now a recognised form. Ten of the twelve were legitimate under
            # SST-M1 and red under SAG-M1.1 with no way to register out.
            ("Not yet implemented.", "not-built"),
            ("No code written yet.", "not-built"),
            ("Not built.", "not-built"),
            ("Awaiting approval.", "not-built"),
            ("CIP-M1 to CIP-M42: no code exists.", "not-built"),
    ):
        assert classify_status_claim(claim) == expected, (
            f"{claim!r} was classified {classify_status_claim(claim)!r}, not "
            f"{expected!r} — a form this repo actually uses must stay "
            "recognised, or the guard's failures are about wording and not "
            "about status")


def test_sagm13_the_draft_register_holds_both_directions():
    """SAG-M1.3 — a draft claim must be registered, and the reverse.

    This is SST-M2's pair of directions, moved onto the allow-list: the "is it
    a draft" half no longer asks a deny-list of phrasings.
    """
    drafts = set()
    for path in _status_documents():
        if registered_claim_is_unbuilt(path):
            drafts.add(str(path.relative_to(REPO)))

    unregistered = sorted(drafts - DRAFTS_NOT_BUILT)
    assert not unregistered, (
        "these documents' status claim is an unbuilt form and they are not in "
        "DRAFTS_NOT_BUILT — either the work is built and the claim is stale, "
        f"or the document belongs in the register: {unregistered}")

    stale = sorted(DRAFTS_NOT_BUILT - drafts)
    assert not stale, (
        "these are registered as not built, and their status claim no longer "
        f"reads as an unbuilt form. If they were built, drop them: {stale}")


def test_sagm14_a_document_with_no_status_claim_fails(tmp_path):
    """SAG-M1.4 — silence is the failure mode a deny-list cannot have.

    `docs/implementation_plan_2026-06-22.md` carried no status line at all for
    five months, and no phrase list can see a sentence that was never written.
    """
    silent = tmp_path / "implementation_plan_2026-01-01_silent.md"
    silent.write_text(
        "# Implementation plan — something\n\nDate: 2026-01-01\n\n"
        "## Design\n\nIt does a thing.\n", encoding="utf-8")

    assert _status_claim(silent) is None
    assert classify_status_claim(_status_claim(silent)) is None

    # And a status section whose first line is prose is not a claim either.
    vague = tmp_path / "implementation_plan_2026-01-02_vague.md"
    vague.write_text(
        "# Implementation plan — something else\n\n## Status\n\n"
        "This section explains how the work was scoped.\n", encoding="utf-8")
    assert classify_status_claim(_status_claim(vague)) is None


def test_sagm15_the_forms_reject_a_built_word_after_a_negation(tmp_path):
    """SAG-M1.5 — the patterns, against text, in both directions.

    The negation check is what keeps the `built` form from accepting "Nothing
    is built yet", which would have made this guard weaker than the list it
    replaces on precisely the sentences SST-A3 is about.
    """
    assert _NEGATION.search("Nothing is ")
    assert _NEGATION.search("no code in ")
    assert _NEGATION.search("unimplemented")
    assert not _NEGATION.search("built and on ")
    assert not _NEGATION.search("PRI-M1 and PRI-M2 are ")

    # The cancellation check, which is the other half: a negation *after* the
    # match, and a question mark.
    assert _CANCELLED.match(" nothing yet")
    assert _CANCELLED.match("? not yet")
    assert not _CANCELLED.match(" and on `main`")
    assert not _CANCELLED.match(", except PD-M12")

    # The label stripper, which decides what the patterns see. The separator
    # and the emphasis come off with the label: four spellings of this repo's
    # own commonest status style failed before the cold pass measured them.
    assert _strip_status_label("**Status:** **Built and on `main`.**") == (
        "Built and on `main`.")
    assert _strip_status_label("Status: built") == "built"
    assert _strip_status_label("Status built 2026-11-09") == "built 2026-11-09"
    for spelling in ("**Status** \u2014 built and on `main`.",
                     "**Status:** \u2013 built and on `main`.",
                     "Status: - built and on `main`.",
                     "**Status:** _built and on `main`_."):
        assert classify_status_claim(_strip_status_label(spelling)) == "built", (
            f"{spelling!r} is a status claim this repo writes and it was not "
            "recognised; the forms are anchored at ^, so whatever the label "
            "leaves behind has to be stripped")

    # The register's contract, over a document written here rather than one
    # that happens to be registered: the plainest draft status this repo can
    # write has to be registerable. The one real registered document says
    # "draft, not approved, on the backlog. No code written yet.", which
    # satisfies the deny-list and the allow-list both, so it cannot show the
    # difference — and that is why the double bind survived three passes.
    plain = tmp_path / "implementation_plan_2026-01-02_plain_draft.md"
    plain.write_text("# Implementation plan — a thing\n\nStatus: Draft.\n",
                     encoding="utf-8")
    assert classify_status_claim(_status_claim(plain)) == "draft"
    assert registered_claim_is_unbuilt(plain), (
        "a document headed `Status: Draft.` has to be registerable: SAG-M1.3 "
        "requires an unbuilt claim to be in DRAFTS_NOT_BUILT, so a register "
        "that will not accept this one puts the author in a bind with no "
        "status line that satisfies both guards")
    assert not _claims_not_built(plain), (
        "if the deny-list now accepts `Draft.` on its own, the bind this "
        "assertion records is gone and the pair above can be simplified")

    # The four built shapes, each reached by a claim of its own. A shape
    # nobody can match is a dead branch, and the alternation is built from
    # `_BUILT_SHAPES`, so a shape added without a sample is a red test.
    for shape, sample in zip(_BUILT_SHAPES, (
            "built and on `main`.",
            "2026-11-10 \u2014 built and on `main`.",
            "M1, M2 and M3 are built.",
            "approved 2026-11-08 and built.")):
        assert classify_status_claim(sample) == "built", (
            f"no sample reaches the built shape {shape!r}")
    assert len(_BUILT_SHAPES) == 4, (
        "a built shape was added or removed; give it a sample in the loop "
        "above rather than widening the count")

    # The order of the forms, which is load-bearing: `built` is the only form
    # that need not match at position 0, so trying it first shadowed the other
    # three. These three sentences each lead with their state, and each
    # classified as `built` until the fourth cold pass, 2026-11-09.
    assert list(_STATUS_FORMS)[-1] == "built", (
        "the `built` form has to be tried last: it is the only one that can "
        "match away from position 0, so it shadows any form that follows it")
    assert classify_status_claim("Draft \u2014 design complete, awaiting "
                                 "approval") == "draft"
    assert classify_status_claim("Awaiting approval; the spec is "
                                 "complete") == "not-built"
    assert classify_status_claim("Spec complete, implementation not "
                                 "started.") == "not-built"

    # A status line inside a fenced block is an example, not a claim, in both
    # directions. These documents quote status conventions and the handoff-note
    # template, whose own `Status` field would otherwise be read as the
    # document's claim.
    # A criterion/state table in a `## Status` section is not the claim: its
    # header row was read as one and matched no form, so a document stating its
    # status as a table went red with nothing wrong with it. The sentence below
    # the table is found instead; a section that is only a table still has no
    # claim, and the failure message says to give a sentence.
    tabled = tmp_path / "implementation_plan_2026-01-06_tabled.md"
    tabled.write_text(
        "# Implementation plan \u2014 a thing\n\n## Status\n\n"
        "| Criterion | State |\n|---|---|\n| M1 | built |\n\n"
        "All criteria are built and on `main`.\n", encoding="utf-8")
    assert classify_status_claim(_status_claim(tabled)) == "built", (
        "a status section that opens with a table had its header row read as "
        "the claim, so a document stating its status as a table fails")
    only_table = tmp_path / "implementation_plan_2026-01-07_only_table.md"
    only_table.write_text(
        "# Implementation plan \u2014 a thing\n\n## Status\n\n"
        "| Criterion | State |\n|---|---|\n| M1 | built |\n", encoding="utf-8")
    assert _status_claim(only_table) is None, (
        "a status section with no sentence in it has no claim, and saying so "
        "is what makes the failure message's advice true")

    quoting = tmp_path / "implementation_plan_2026-01-03_quoting.md"
    quoting.write_text(
        "# Implementation plan \u2014 a thing\n\n"
        "The convention is:\n\n```markdown\n"
        "**Status:** built and on `main`.\n```\n\n"
        "**Status:** Draft, not approved.\n", encoding="utf-8")
    assert _status_claim(quoting) == "Draft, not approved.", (
        "a `Status` line inside a fenced example was read as the document's "
        "own claim, so a quoted convention decides whether a real draft is "
        "registered")
    assert registered_claim_is_unbuilt(quoting)

    # A list marker before the label. The label is stripped at `^`, so a
    # bullet left it in place and every anchored form then missed — which
    # landed only on draft and superseded documents, because `built` had been
    # left unanchored by the same pass.
    for bullet in ("- **Status:** Draft.", "* Status: superseded by PD-M13.",
                   "+ **Status:** built and on `main`."):
        assert classify_status_claim(_strip_status_label(bullet)) is not None, (
            f"{bullet!r} is a status line this repo could write and the label "
            "was not stripped, so no anchored form could match it")

    # The limitation, asserted rather than left to be rediscovered: a built
    # word used as an adjective still reads as a claim. `SAG-A8` is the filing;
    # this assertion is what will go red when someone closes it, which is the
    # only honest way to record a hole.
    assert classify_status_claim("Complete rewrite proposed. No code yet.") == (
        "built"), (
        "if this now classifies as None, SAG-A8 has been closed — delete this "
        "assertion and say so in the filing")

    # Every form is reachable: a pattern nobody can match is a dead branch, and
    # this asserts the dict's own keys rather than a count of them.
    reached = {classify_status_claim(claim) for claim in (
        "built and on `main`",
        "approved 2026-11-08 and built",
        "PRI-M1 is built",
        "superseded by PD-M13",
        "draft, not approved",
        "no code exists yet",
    )}
    assert reached == set(_STATUS_FORMS), (
        f"these forms were not reached by any sample: "
        f"{sorted(set(_STATUS_FORMS) - reached)}")

    # And every ALTERNATIVE inside the enumerated patterns is reachable, which
    # the check above cannot see: it proves the four form *names* can be
    # reached, and `not approved` was a dead alternative of `draft` for exactly
    # that reason — the negation check discarded the match before it was
    # returned. One word per alternative, taken from the patterns themselves,
    # so adding an alternative that cannot match is a red test rather than a
    # branch nobody notices (third cold pass, 2026-11-09).
    # The alternatives are read out of the patterns, not retyped: a loop over
    # a hardcoded list goes stale the moment a form gains an alternative, and
    # mutation AW2 proved it — adding a fifth draft spelling left this green.
    for name in ("superseded", "draft"):
        parsed = re.fullmatch(
            r"\^\((.+)\)\\b", _STATUS_FORMS[name].pattern)
        assert parsed, (
            f"the {name!r} form is no longer a bare alternation, so this loop "
            "is reading nothing — rewrite it against the new shape rather "
            "than deleting it")
        for word in parsed.group(1).split("|"):
            assert classify_status_claim(f"{word}.") == name, (
                f"{word!r} is an alternative of the {name!r} form that nothing "
                "can reach, so it is a dead branch")
    for phrase in _NOT_BUILT.pattern.split("|"):
        phrase = phrase.strip()
        assert classify_status_claim(f"{phrase}.") in _UNBUILT_FORMS, (
            f"{phrase!r} is a phrasing `_NOT_BUILT` accepts as a registerable "
            "claim, and the allow-list does not recognise it — so a document "
            "registered exactly as the register's own comment instructs would "
            "be red under SAG-M1.1 with no way to register out. Either unbuilt "
            "form satisfies the register: `not approved` is in both patterns "
            "and `draft` is matched first, which is harmless because "
            "SAG-M1.3 treats them alike")


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
    # Either phrasing: `all 41 criteria` while every row is done, or
    # `40 of 41 criteria` once a new row is added and not yet built. The
    # fourth cold pass found this accepted only the all-done form, so adding
    # a `WTP-M7` row made the *correct* summary fail.
    assert re.search(rf"(?:all|[0-9]+ of) {len(criteria)} criteria", summary), (
        f"§6's summary does not state the count the rows list "
        f"({len(criteria)}) — it said 40 while listing 41, and its arithmetic "
        "for 40 counted §3 as 35 after §3 had been amended")

    # `BACKLOG.md`'s header paragraph, anchored on its own sentence rather
    # than on the one historical wrong figure: the second cold pass set that
    # sentence to 40 and watched this guard pass, because the only assertion
    # here was that the string "all 38 criteria" was absent.
    # Anchored on the figure, not on the sentence around it. The seven-word
    # prose fragment that used to anchor this sat in BACKLOG.md's header
    # paragraph — one of the four chronic conflict surfaces this repo's
    # CLAUDE.md names *because* every batch rewrites that region — so any
    # rewording of it failed a test. No absence assertion goes with it: this
    # file's `SSC` filings quote the wrong claims they record verbatim, so
    # "all 40 criteria" is *correctly* present at the filing that recorded it,
    # and an absence check over the whole file is red on a true record — the
    # same trap that turned SST-M8 red twice in this batch. The positive check
    # alone closes the pass-2 hole, which existed because absence of
    # "all 38 criteria" was the only assertion here.
    backlog = (REPO / "BACKLOG.md").read_text(encoding="utf-8")
    assert re.search(rf"(?:all|[0-9]+ of) {len(criteria)} criteria", backlog), (
        "BACKLOG.md does not state the WTP count the spec lists "
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
    assert re.search(rf"(?:all|[0-9]+ of) {len(criteria)} criteria", entry), (
        "the index's WTP entry does not state the count the spec lists "
        f"({len(criteria)})")

    # The batch's own handoff note stated the count too, and kept 38 after
    # every other document had been corrected. It is deliberately *not*
    # asserted here: a dated handoff note records what was true on its date,
    # which is the same reason SST-M1 keeps `docs/changes/` out of the status
    # scan. Pinning a recounted figure into it would require editing a dated
    # record to state a figure that was not true on its date, every time a
    # criterion is added. The note was corrected to 41 in this batch
    # (`git log -p -- docs/changes/2026-11-08-weekly-tactic-as-parent.md`).


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
    # Membership per source, not a total. This asserted `== 186` until the
    # fourth cold pass recomputed the figure with this module's own parser at
    # each of the last 30 commits: 175, 184, 185, 186. Any batch that writes
    # one coverage row naming `file.py::symbol` moved it, and 66 commits
    # touched a `docs/spec_coverage*.md` in the last 30 days. Dropping a file
    # from the glob, or narrowing the row pattern, still fails here.
    contributing = {str(source) for source, _t, _s in found}
    for name in ("docs/spec_coverage.md",
                 "docs/spec_coverage_2026-08-19_item_editor_project_link.md",
                 "docs/spec_coverage_2026-11-05_demo_install.md",
                 "docs/spec_coverage_2026-11-08_plan_calendar_export.md",
                 "docs/spec_coverage_2026-11-08_priority_level_colours.md"):
        assert name in contributing, (
            f"{name} contributed no implementation reference — either it is "
            "outside the glob now, or its Implementation column has stopped "
            "naming symbols")
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
# `.github/workflows/agent-docs-gate.yml` ran on `pull_request` only, while
# this repo pushes to `main` and opens no pull requests. So the criterion's
# named evidence had never run. Found by the second cold pass, 2026-11-09;
# `SST-A8` filed the dead gate itself, and `SAG-A3` deleted it the same day.
# `NOTES.md` is deliberately absent: it opens with a dated "Where main
# stands" section that each batch rewrites with deletions (the PRIT batch's
# edit was +22/-13), so an `SST-…` id there is expected to age out, and a
# guard over it would fire with the wrong diagnosis. Found by the fourth cold
# pass, 2026-11-09.
SST_RECORDS = (
    "BACKLOG.md",
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
