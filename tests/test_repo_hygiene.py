"""Repo hygiene tests.

Purpose: keep the repository root readable as a product, and stop a required
         resource being silently excluded from the distribution.
Spec:    docs/spec_2026-08-18_downloadable_release.md#r-m7
Tests:   this file

R-M7.B is the important one. `.gitignore` carries a blanket `*.json` rule with
a handful of `!` exceptions. That is the same shape as finding F1: a resource
the app loads at runtime can be excluded from the repo — and therefore from
every build — without anybody noticing, because the app keeps working on the
machine where the untracked file still exists locally.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

import pytest

# This whole file asserts on the REPOSITORY — workflows, packaging, licences,
# docs, traceability — not on application behaviour. Marked `meta` so
# `pytest -m "not meta"` gives a fast app-only run. The default `pytest` run
# still includes it: the marker is for speed, never for skipping.
pytestmark = pytest.mark.meta

REPO_ROOT = Path(__file__).resolve().parents[1]


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=str(REPO_ROOT),
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


def _tracked_root_files() -> list[str]:
    return [f for f in _tracked_files() if "/" not in f]


# --------------------------------------------------------------------------
# R-M7.A — no stray scripts at the repo root
# --------------------------------------------------------------------------

STRAY_PREFIXES = ("test_", "diagnose_", "fix_", "debug_", "verify_")


def test_rm7a_repo_root_has_no_stray_scripts():
    """Diagnostics live in tools/diagnostics/, tests live in tests/."""
    strays = sorted(
        f for f in _tracked_root_files()
        if f.lower().startswith(STRAY_PREFIXES)
    )
    assert not strays, (
        f"scripts at the repo root that belong in tools/diagnostics/ or tests/: "
        f"{strays}"
    )


def test_rm7a_diagnostics_folder_exists_and_is_populated():
    """Guard on the guard: the test above passes trivially if everything was
    deleted rather than relocated."""
    diagnostics = REPO_ROOT / "tools/diagnostics"
    assert diagnostics.is_dir(), "tools/diagnostics/ does not exist"
    contents = list(diagnostics.iterdir())
    assert len(contents) >= 5, f"tools/diagnostics/ looks empty: {contents}"


def test_rm7a_no_python_entry_points_lost_from_the_root():
    """run.py and conftest.py must stay where the tooling expects them."""
    for required in ("run.py", "conftest.py"):
        assert (REPO_ROOT / required).exists(), f"{required} is missing from the root"


# --------------------------------------------------------------------------
# R-M7.C — the root reads as a product, not as an agent workspace
# --------------------------------------------------------------------------

# Docs that belong at the root of any repository, plus the two agent-config
# files whose tooling reads them from the root and nowhere else.
ROOT_DOC_ALLOWLIST = {
    "README.md",
    "LICENSE",
    "INSTALL.md",
    "CHANGELOG.md",
    "THIRD_PARTY_NOTICES.md",
    "CLAUDE.md",       # Claude Code loads this from the repo root
    "AGENTS.md",       # multi-agent workflow contract
    "BACKLOG.md",
    "NOTES.md",
    "codex.md",
    "GetMoreDone_MasterSpec_SQLite_v1.md",
    "LEARNINGS.md",    # repo-specific failure-pattern playbook + fix log
}


def test_rm7c_repo_root_doc_allowlist():
    """Troubleshooting and agent-facing docs belong under docs/."""
    root_docs = {f for f in _tracked_root_files() if f.endswith(".md") or f == "LICENSE"}
    unexpected = sorted(root_docs - ROOT_DOC_ALLOWLIST)
    assert not unexpected, (
        f"root-level docs not on the allowlist: {unexpected}. Move them under "
        "docs/, or add them to ROOT_DOC_ALLOWLIST with a reason."
    )


def test_rm7c_allowlisted_root_docs_all_exist():
    """A stale allowlist entry hides a file that was deleted or moved."""
    missing = sorted(
        name for name in ROOT_DOC_ALLOWLIST if not (REPO_ROOT / name).exists()
    )
    assert not missing, f"ROOT_DOC_ALLOWLIST names files that do not exist: {missing}"


# --------------------------------------------------------------------------
# R-M7.B — the blanket *.json ignore cannot silently drop a shipped resource
# --------------------------------------------------------------------------

def test_rm7b_no_gitignore_copy_file():
    assert not (REPO_ROOT / ".gitignore copy").exists(), (
        "'.gitignore copy' is back; it was a duplicate of .gitignore"
    )


def test_rm7b_gitignore_still_has_the_blanket_json_rule_documented():
    """If the blanket rule is ever removed this test should be removed too —
    but while it exists, it must be visible rather than incidental."""
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.json" in text
    assert "!themes/*.json" in text, (
        "the themes exception is gone from .gitignore — every theme would be "
        "untracked and every build would lose them (finding F1)"
    )


def test_rm7b_required_json_resources_are_tracked():
    """Every JSON the app loads at runtime must be tracked by git.

    This is the F1 class. `*.json` is ignored wholesale, so a resource added
    later is untracked by default — it keeps working locally, where the file
    exists, and vanishes from every clone and every build.
    """
    tracked = set(_tracked_files())

    required: list[Path] = sorted((REPO_ROOT / "themes").glob("*.json"))
    assert required, "no theme JSON files found at all"
    required.append(REPO_ROOT / "src/getmoredone/email_cleaning_rules.json")

    untracked = [
        str(p.relative_to(REPO_ROOT))
        for p in required
        if p.exists() and str(p.relative_to(REPO_ROOT)) not in tracked
    ]
    assert not untracked, (
        f"JSON resources the app loads at runtime are NOT tracked by git: "
        f"{untracked}. The blanket *.json ignore swallowed them — add a "
        "'!' exception in .gitignore."
    )


def test_rm7b_tracked_json_resources_are_valid_json():
    """A tracked-but-corrupt resource fails at launch, not at commit time."""
    broken = []
    for rel in _tracked_files():
        if not rel.endswith(".json"):
            continue
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            broken.append(f"{rel}: {exc}")
    assert not broken, f"tracked JSON files that do not parse: {broken}"


def test_rm7b_ignore_rules_do_not_exclude_a_bundled_resource():
    """Ask git directly whether it would ignore each file the spec bundles.

    Checks behaviour rather than reading the rules, so a future rule change
    that shadows an exception is caught (P16: diagnose the running system).
    """
    from tests.test_packaging_resources import _analysis_datas

    from tools.packaging_filters import should_bundle

    candidates: list[Path] = []
    for src, dest in _analysis_datas():
        if src.is_dir():
            for p in src.rglob("*"):
                # Judge what actually ships: the packaging filter runs first,
                # so a file it drops cannot be missing from a build.
                if p.is_file() and should_bundle(f"{dest}/{p.relative_to(src).as_posix()}"):
                    candidates.append(p)
        elif src.is_file() and should_bundle(src.name):
            candidates.append(src)

    assert candidates, "the spec bundles nothing — the datas parse failed"

    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=str(REPO_ROOT),
        input="\n".join(str(p.relative_to(REPO_ROOT)) for p in candidates),
        capture_output=True, text=True, timeout=120,
    )
    # check-ignore exits 0 when it found ignored paths, 1 when it found none.
    ignored = [line for line in result.stdout.splitlines() if line.strip()]
    assert not ignored, (
        f"daVIPA.spec bundles files that .gitignore excludes, so they are "
        f"missing from every clone and every CI build: {ignored}"
    )


# --------------------------------------------------------------------------
# GSF-M2 — a document may not cite a root document that is not there
# --------------------------------------------------------------------------

# The live documents, as `tests/test_ci_contract.py::LIVE_DOCS` defines them,
# plus the dated records' own exclusion: those say what was true when they
# were written. Imported rather than retyped, so the two guards cannot drift
# into reading different halves of this repo.
# Two forms, both anchored so a path citation's trailing basename cannot be
# read as a root name: a fully backticked bare token, and a heading opening
# with one, which is how `docs/DOCUMENTATION_INDEX.md` names each document it
# lists. The token has no spaces and no `*`, so a shell command quoted in
# backticks (`grep -n "..." BACKLOG.md`) and a glob (`spec_*.md`) are out, and
# so is an unbackticked mention in running prose — "it does not delete the
# .md" is not a citation. What is left is exactly the form that goes stale
# unread: a document naming a file at the repo root.
_ROOT_DOC_CITATION = re.compile(r"`([\w.\-]+\.md)`")
_ROOT_DOC_HEADING = re.compile(r"^#{1,6} +([\w.\-]+\.md)\b", re.M)

# Names that look like a root document, are cited by a live document, and
# correctly do not exist here. One reason covers all four: they live in
# ``~/.claude/standards/``, outside any repo, and `CLAUDE.md`'s standards
# table is what cites them. Checked in both directions below — a name that
# starts resolving has to leave this list, or the list becomes the place a
# real defect hides.
ROOT_DOC_CITATION_EXEMPTIONS = {
    # The four under `~/.claude/standards/`, which are the author's machine
    # and deliberately not in this repo.
    "learnings.md",
    "file-maintainability.md",
    "ui-regression.md",
    "security.md",
    # A fixture filename, written by the guard tests themselves into a
    # `tmp_path` and named in `docs/spec_coverage.md` when a mutation is
    # recorded. It is not a pointer and will never be a tracked file; the
    # both-directions check below fails if it ever becomes one. Added by
    # LDS-M3.1, when deriving the scanned set brought `docs/spec_coverage.md`
    # into it.
    "PROBE.md",
}


def root_doc_citations(text: str) -> list[str]:
    """Bare root-level ``*.md`` names a document points a reader at.

    Only names with no directory part: a path is a different citation, read by
    `tests/test_traceability_refs.py` for tests and by
    `::test_sstm5_every_implementation_reference_resolves` for source. This
    arm is the one `SAG-A7` was an instance of — `CLAUDE.md`'s key-files table
    naming ``daVIPA_MasterSpec_SQLite_v1.md``, which has never existed.

    The directory part is excluded by the patterns alone: neither character
    class admits ``/``, and both anchor the token's left edge (a backtick, or
    the heading's space), so ``docs/USER_GUIDE.md`` cannot match either arm.
    An ``if "/" in name: continue`` guard stood here as well until a mutation
    round measured it: removing either exclusion on its own changed no outcome
    anywhere, and only removing both together turned the test red. Two
    mechanisms for one rule means neither is observably tested, so the
    redundant one is gone and the patterns are the mechanism.
    """
    out = []
    for pattern in (_ROOT_DOC_CITATION, _ROOT_DOC_HEADING):
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            if name.startswith("."):
                continue
            out.append(name)
    return out


def test_gsfm21_no_document_cites_a_root_doc_that_does_not_exist():
    """GSF-M2.1, GSF-M2.2 — the shape `SAG-A7` was.

    Purpose: the one pointer a reader is most likely to follow out of
             `CLAUDE.md` must name a file that is there.
    Spec:    docs/implementation_plan_2026-11-09_dead_gate_and_dead_spec_name.md#gsf-m21
    Tests:   this test

    Eleven live citations named ``daVIPA_MasterSpec_SQLite_v1.md``, including
    a `###` entry in `docs/DOCUMENTATION_INDEX.md`, so the index had an entry
    for a file this repo has never contained. The root file is
    ``GetMoreDone_MasterSpec_SQLite_v1.md``, which is the name
    `tools/agents/check_docs_sync.py` and `ROOT_DOC_ALLOWLIST` above both use
    — and `ROOT_DOC_ALLOWLIST` could not rot, because
    `::test_rm7c_allowlisted_root_docs_all_exist` reads it. Nothing read the
    prose.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_ci_contract import LIVE_DOCS, _live_documents

    assert LIVE_DOCS, "no live documents declared; the scan would be vacuous"
    tracked = {
        line
        for line in subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if line
    }
    root_names = {path for path in tracked if "/" not in path}

    dangling = []
    for doc in _live_documents():
        rel = doc.relative_to(REPO_ROOT)
        for name in root_doc_citations(doc.read_text(encoding="utf-8")):
            if name in root_names or name in ROOT_DOC_CITATION_EXEMPTIONS:
                continue
            if name in {path.rsplit("/", 1)[-1] for path in tracked}:
                continue          # cited bare but living under a directory
            dangling.append(f"{rel}: {name}")
    assert not dangling, (
        "these documents name a root-level document that does not exist:\n  "
        + "\n  ".join(sorted(dangling))
        + "\nName the file that is there, or add the name to "
        "ROOT_DOC_CITATION_EXEMPTIONS with the reason it is not in this repo. "
        "A name quoted as a defect rather than offered as a pointer — the way "
        "BACKLOG.md's closed SAG-A7 quotes the spec filename that never "
        "existed — is written WITHOUT backticks, which is the form this scan "
        "reads."
    )

    # The exemptions, both directions. A name that starts resolving has to
    # leave the list: a stale exemption is where the next instance of this
    # defect would sit unread.
    for name in sorted(ROOT_DOC_CITATION_EXEMPTIONS):
        assert name not in root_names, (
            f"{name} now exists in the repo root, so it is no longer exempt — "
            "drop it from ROOT_DOC_CITATION_EXEMPTIONS so its citations get "
            "checked"
        )

    # The scan itself, over text written here rather than over prose that
    # could stop using the form.
    assert root_doc_citations(
        "| `daVIPA_MasterSpec_SQLite_v1.md` | Complete technical spec |"
    ) == ["daVIPA_MasterSpec_SQLite_v1.md"], "the citation form is no longer matched"
    assert root_doc_citations("See `docs/USER_GUIDE.md` for the rest.") == [], (
        "a path citation is being read as a root name; that is a different "
        "guard's domain"
    )
    assert root_doc_citations("`GetMoreDone_MasterSpec_SQLite_v1.md` at the root") == [
        "GetMoreDone_MasterSpec_SQLite_v1.md"
    ]
    # The heading arm, which is how `docs/DOCUMENTATION_INDEX.md` listed an
    # entry for a file this repo has never contained. A mutation dropping this
    # arm left the test green once that entry was repaired, so it is asserted
    # here rather than against today's index.
    assert root_doc_citations(
        "### daVIPA_MasterSpec_SQLite_v1.md (19KB)\n\nThe spec.\n"
    ) == ["daVIPA_MasterSpec_SQLite_v1.md"], (
        "a document naming a root file in a heading is no longer read, so an "
        "index entry for a file that does not exist would pass"
    )
    assert root_doc_citations("## Where `main` stands") == []
    # And a quoted shell command is not a citation, which is what keeps
    # BACKLOG.md's `grep -n "..." BACKLOG.md` lines out of the domain.
    assert root_doc_citations('`grep -n "AWA-A1 -" BACKLOG.md`') == []
    # A dotfile name is dropped: a hidden file at the root is configuration
    # rather than a document a reader is being pointed at, and the allow-list
    # above is what covers those. Asserted here because no live document
    # writes the form, so a mutation removing the filter was green until this
    # line existed.
    assert root_doc_citations("see `.notes.md` for scratch") == []
    assert "GetMoreDone_MasterSpec_SQLite_v1.md" in root_names, (
        "the master spec is not at the repo root under that name, so the "
        "repair this guard protects has been undone"
    )

    # And it is reading the documents: the root docs they really do cite.
    cited = {
        name
        for doc in _live_documents()
        for name in root_doc_citations(doc.read_text(encoding="utf-8"))
    }
    assert "BACKLOG.md" in cited, (
        "no live document cites BACKLOG.md, so either the scan is reading "
        "nothing or the documents have stopped naming it"
    )


# --------------------------------------------------------------------------
# MAW-M1, MAW-M3 — the retired apparatus, and `docs/` paths that are not there
# --------------------------------------------------------------------------

# The root-doc arm above reads bare names only, by design: a path is a
# different citation. This reads the `docs/` paths, which is the form the
# retired three-agent workflow was cited by — `docs/MULTI_AGENT_WORKFLOW.md`,
# named by the documentation index, BACKLOG.md and the GSF guards' own scanned
# set. Deleting a document that four places point at is exactly the shape
# `SAG-A7` was, arriving from the other direction.
# Non-greedy on purpose. The character class has to admit a space, because
# `docs/daVIPA - Get Started.md` is a real tracked document; greedy, that
# space let one match span two paths, so a heading naming two documents
# ("### docs/a.md and docs/b.md") was read as the single path
# "docs/a.md and docs/b.md", which is tracked nowhere and would have failed
# the guard on correct prose. Non-greedy stops at the first `.md`, so such a
# line yields its first path only — a narrowing the unbounded arms accept in
# exchange for having no false positive.
_DOCS_PATH = r"docs/[\w./\- ]*?[\w\-]\.md"
# Five forms, because this repo writes all five and a guard that reads one is
# the shape it keeps getting bitten by. The heading arm is the one that
# matters most: the deleted document's entry in `docs/DOCUMENTATION_INDEX.md`
# was `### docs/MULTI_AGENT_WORKFLOW.md (NEW)`, which the backticked arm alone
# does not see — and that index names 26 documents that way. `GSF-M2.1` has
# the same arm one directory up, added for exactly the same reason, and a cold
# pass caught this guard shipping without it.
_DOCS_PATH_CITATIONS = (
    re.compile(rf"`({_DOCS_PATH})`"),                       # backticked
    re.compile(rf"`({_DOCS_PATH}):\d+`"),                   # with a line number
    re.compile(rf"^#{{1,6}} +({_DOCS_PATH})", re.M),        # a heading
    re.compile(rf"\]\(({_DOCS_PATH})\)"),                   # a markdown link
    re.compile(rf"^\s*(?:[-*]|\u2192) +({_DOCS_PATH})\b", re.M),  # a list item
)

# Cited `docs/` paths that correctly do not exist. One reason covers both:
# `BACKLOG.md` *proposes* writing them, in an item that is still open. Checked
# in both directions below — a name that starts resolving has to leave this
# list, or the list becomes the place a real defect hides.
DOCS_PATH_CITATION_EXEMPTIONS = {
    "docs/spec_glossary.md",
    "docs/spec_template.md",
}

# The apparatus of the retired three-agent workflow (MAW-M1.2). The bootstrap
# script created `codex/agent-code`, `codex/agent-docs` and
# `codex/agent-github` plus a worktree on each; two of those three branches
# were never created by anything else, and the third is 624 commits behind
# `main` and an ancestor of it. The role prompts told an agent to commit to
# them.
RETIRED_AGENT_APPARATUS = (
    "docs/MULTI_AGENT_WORKFLOW.md",
    "tools/agents/setup_worktrees.sh",
    ".agents/prompts/code-agent.md",
    ".agents/prompts/docs-agent.md",
    ".agents/prompts/github-agent.md",
    ".github/pull_request_template.md",
)


def docs_path_citations(text: str) -> list[str]:
    """The `docs/` paths a document points a reader at.

    The trailing character class forbids a path ending in a separator or a
    space, so a sentence naming the directory is not a citation. Each arm
    anchors the path's left edge — a backtick, a heading's space, a link's
    ``](``, a list marker — so an unbackticked mention in running prose is not
    a pointer, which is what lets a deleted document be named honestly in the
    past tense.
    """
    out = []
    for pattern in _DOCS_PATH_CITATIONS:
        out += [m.group(1) for m in pattern.finditer(text)]
    return out


def dangling_docs_path_citations(documents, tracked):
    """Cited `docs/` paths that are not tracked, as ``label: path``.

    ``documents`` is a sequence of ``(label, text)`` pairs. Extracted so the
    test can drive it over a fixture: a mutation that skipped this comparison
    entirely left the test green, because once every citation in the repo is
    repaired there is nothing left for the repo scan to find.
    """
    return [
        f"{label}: {cited}"
        for label, text in documents
        for cited in docs_path_citations(text)
        if cited not in tracked and cited not in DOCS_PATH_CITATION_EXEMPTIONS
    ]


def present_apparatus(tracked):
    """The retired apparatus paths present in ``tracked``, sorted.

    Extracted for the same reason: ``assert not present`` over the real repo
    cannot fail once the files are deleted, so the test drives this over a
    fixture listing that does contain one.
    """
    return sorted(path for path in RETIRED_AGENT_APPARATUS if path in tracked)


def test_mawm11_no_document_cites_a_docs_path_that_does_not_exist():
    """MAW-M1.1, MAW-M3.1 — the other direction of `SAG-A7`.

    Purpose: deleting a document must not leave the four places that point at
             it saying it is there.
    Spec:    docs/implementation_plan_2026-11-09_retired_agent_apparatus.md#maw-m31
    Tests:   this test

    `docs/MULTI_AGENT_WORKFLOW.md` was cited by `docs/DOCUMENTATION_INDEX.md`,
    `BACKLOG.md` and the GSF guards' own `DOCS_DIR_LIVE_DOCS`. `GSF-M2.1` reads
    bare root names and so would not have caught any of them.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_ci_contract import _live_documents

    tracked = {
        line
        for line in subprocess.run(
            ["git", "ls-files", "docs"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if line
    }
    assert tracked, "nothing tracked under docs/; the scan would be vacuous"

    dangling = dangling_docs_path_citations(
        [
            (doc.relative_to(REPO_ROOT).as_posix(), doc.read_text(encoding="utf-8"))
            for doc in _live_documents()
        ],
        tracked,
    )
    assert not dangling, (
        "these documents point a reader at a docs/ path that does not "
        "exist:\n  " + "\n  ".join(sorted(dangling))
        + "\nName the file that is there, or add the path to "
        "DOCS_PATH_CITATION_EXEMPTIONS with the reason it is not in this "
        "repo. A document that has been deleted is named without backticks, "
        "the way a dead root filename is — see CLAUDE.md, 'Naming a thing "
        "that no longer exists'."
    )

    # The exemptions, both directions.
    for path in sorted(DOCS_PATH_CITATION_EXEMPTIONS):
        assert path not in tracked, (
            f"{path} now exists, so it is no longer exempt — drop it from "
            "DOCS_PATH_CITATION_EXEMPTIONS so its citations get checked"
        )

    # The scan itself, over text written here rather than over prose that
    # could stop using the form.
    assert docs_path_citations(
        "4. Open/update PR per `docs/MULTI_AGENT_WORKFLOW.md`."
    ) == ["docs/MULTI_AGENT_WORKFLOW.md"], "the citation form is no longer matched"
    assert docs_path_citations("note: `docs/changes/2026-11-09-a-topic.md`") == [
        "docs/changes/2026-11-09-a-topic.md"
    ], "a path with a subdirectory is no longer matched"
    assert docs_path_citations("`docs/daVIPA - Get Started.md` has it") == [
        "docs/daVIPA - Get Started.md"
    ], "a path containing a space is no longer matched, and one is tracked"
    # Two paths on one unbounded line. The class has to admit a space for the
    # document above, and greedy that space let one match span both paths and
    # report "docs/USER_GUIDE.md and docs/ROADMAP.md", which is tracked
    # nowhere — the guard failing on correct prose. Non-greedy reads the first
    # path and stops. Found by a cold pass, latent rather than red, because no
    # line in the repo writes two paths this way yet.
    assert docs_path_citations("### docs/USER_GUIDE.md and docs/ROADMAP.md\n") == [
        "docs/USER_GUIDE.md"
    ], "a heading naming two documents is read as one path that does not exist"
    assert docs_path_citations("- docs/USER_GUIDE.md and docs/ROADMAP.md\n") == [
        "docs/USER_GUIDE.md"
    ], "a list item naming two documents is read as one path that does not exist"
    # The heading arm, which is how `docs/DOCUMENTATION_INDEX.md` names the 26
    # documents it lists — and the form the deleted document's own entry used,
    # so the backticked arm alone would not have caught it.
    assert docs_path_citations(
        "### docs/MULTI_AGENT_WORKFLOW.md (NEW)\n\nStarter guide.\n"
    ) == ["docs/MULTI_AGENT_WORKFLOW.md"], (
        "a document named in a heading is no longer read, so an index entry "
        "for a file that does not exist would pass"
    )
    # A markdown link, which is the most followable pointer this repo writes.
    assert docs_path_citations("see [the guide](docs/USER_GUIDE.md) first") == [
        "docs/USER_GUIDE.md"
    ], "a markdown-link citation is no longer read"
    # A list item, with either marker this repo uses.
    assert docs_path_citations("- docs/USER_GUIDE.md\n") == ["docs/USER_GUIDE.md"]
    assert docs_path_citations("  \u2192 docs/USER_GUIDE.md\n") == ["docs/USER_GUIDE.md"]
    # And a line-number suffix, which BACKLOG.md writes for non-chronic files.
    # The plain backticked arm wants a closing backtick straight after `.md`,
    # so this form is read by its own arm alone and reports the path once.
    assert docs_path_citations("`docs/USER_GUIDE.md:42` has it") == [
        "docs/USER_GUIDE.md"
    ], "a path with a line number is no longer read"

    # A directory, and an unbackticked mention, are not citations.
    assert docs_path_citations("the records under `docs/changes/`") == []
    assert docs_path_citations("see docs/USER_GUIDE.md for the rest") == []
    # A bare root name is the other guard's domain, not this one's.
    assert docs_path_citations("`CLAUDE.md` is the agreement") == []

    # The comparison, over a document written here. The repo check above
    # cannot fail once every citation is repaired, so a mutation that skipped
    # the comparison altogether left it green until these two lines existed.
    assert dangling_docs_path_citations(
        [("PROBE.md", "see `docs/MULTI_AGENT_WORKFLOW.md` for the roles")],
        tracked,
    ) == ["PROBE.md: docs/MULTI_AGENT_WORKFLOW.md"], (
        "a document citing a deleted docs/ path is not reported, so the scan "
        "is inert"
    )
    assert dangling_docs_path_citations(
        [("PROBE.md", "see `docs/USER_GUIDE.md` for the rest")], tracked
    ) == [], "a docs/ path that exists is reported as dangling"
    assert dangling_docs_path_citations(
        [("PROBE.md", "`docs/spec_glossary.md` is not written yet")], tracked
    ) == [], "an exempt path is reported as dangling"

    # And it is reading the documents: the docs/ paths they really do cite.
    cited = {
        path
        for doc in _live_documents()
        for path in docs_path_citations(doc.read_text(encoding="utf-8"))
    }
    assert "docs/spec_coverage.md" in cited, (
        "no live document cites docs/spec_coverage.md, so either the scan is "
        "reading nothing or the documents have stopped naming the file every "
        "batch records its criteria in"
    )


def test_mawm12_the_retired_agent_apparatus_is_absent():
    """MAW-M1.2 — the apparatus, not just the document that described it.

    Purpose: a retired workflow's runnable parts must not be left behind to
             read as current.
    Spec:    docs/implementation_plan_2026-11-09_retired_agent_apparatus.md#maw-m12
    Tests:   this test

    `tools/agents/setup_worktrees.sh` is the one that matters: it created two
    branches nothing else ever created, put a worktree on each, and printed
    "Open 3 agent sessions". `CLAUDE.md` and `AGENTS.md` had recorded the
    workflow as retired since 2026-11-08 while all of this stayed executable.
    """
    tracked = {
        line
        for line in subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if line
    }
    assert tracked, "git ls-files returned nothing; the check would be vacuous"
    assert "CLAUDE.md" in tracked, "the listing is not of this repo"

    # The tuple's own contents, so that dropping an entry is deliberate: a
    # mutation that removed the bootstrap script from it left this test green,
    # because a list of things that must be absent cannot fail by shrinking.
    assert set(RETIRED_AGENT_APPARATUS) == {
        "docs/MULTI_AGENT_WORKFLOW.md",
        "tools/agents/setup_worktrees.sh",
        ".agents/prompts/code-agent.md",
        ".agents/prompts/docs-agent.md",
        ".agents/prompts/github-agent.md",
        ".github/pull_request_template.md",
    }, (
        "RETIRED_AGENT_APPARATUS no longer names the six files the MAW batch "
        "deleted. If one is being revived, say so in CLAUDE.md and AGENTS.md "
        "first and change this assertion with it"
    )

    # The check itself, over a listing written here: over the real repo it
    # cannot fail once the files are gone.
    assert present_apparatus(
        {"CLAUDE.md", "tools/agents/setup_worktrees.sh"}
    ) == ["tools/agents/setup_worktrees.sh"], (
        "an apparatus file present in the listing is not reported, so the "
        "check is inert"
    )
    assert present_apparatus({"CLAUDE.md", ".agents/templates/handoff-note.md"}) == [], (
        "a file that is not part of the retired apparatus is reported"
    )

    present = present_apparatus(tracked)
    assert not present, (
        "the retired three-agent workflow's apparatus is back:\n  "
        + "\n  ".join(present)
        + "\nThe workflow is retired in CLAUDE.md and AGENTS.md: there are no "
        "per-role branches, and this repo opens no pull requests. If it is "
        "being revived, those two documents are what say so first."
    )
    # The handoff template is not part of it and must stay: every batch uses it.
    assert ".agents/templates/handoff-note.md" in tracked, (
        "the handoff-note template is gone, and CLAUDE.md requires a handoff "
        "note from every batch of work"
    )


CONVENTION_SECTION_HEADING = "### Naming a thing that no longer exists"

# Every guard that reads prose for a name that should not resolve. A guard
# that is not named in the section is a convention a future author can only
# learn by turning a test red, which is the thing the section exists to stop.
PROSE_CITATION_GUARD_IDS = ("GSF-M1.1", "GSF-M2.1", "MAW-M2.1", "MAW-M3.1")

_COUNT_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def convention_section(text: str) -> str:
    """The *Naming a thing that no longer exists* section of a document."""
    start = text.find(CONVENTION_SECTION_HEADING)
    if start < 0:
        return ""
    rest = text[start + len(CONVENTION_SECTION_HEADING):]
    end = rest.find("\n## ")
    nxt = rest.find("\n### ")
    if nxt >= 0 and (end < 0 or nxt < end):
        end = nxt
    return rest if end < 0 else rest[:end]


def convention_bullet_count(section: str) -> int:
    """How many conventions the section actually states, as bold bullets."""
    return len(re.findall(r"^- \*\*", section, re.M))


def stated_convention_count(section: str) -> int | None:
    """The count the section's own opening sentence claims, or None."""
    match = re.search(r"^(\w+) conventions\b", section.strip(), re.M)
    if not match:
        return None
    return _COUNT_WORDS.get(match.group(1).lower())


def test_ldsm32_the_conventions_name_every_form_a_guard_reads():
    """LDS-M3.2 — the section's own count must match its bullets.

    Purpose: a convention a future author can only learn by turning a test
             red is a convention written in the wrong place, and a section
             that miscounts itself is the first sign it has stopped being
             maintained alongside the guards.
    Spec:    docs/implementation_plan_2026-11-09_derived_live_document_set.md#lds-m32
    Tests:   this test

    The MAW second cold pass found this section opening "Three conventions"
    over four bullets, with a closing sentence pointing at the wrong one. Both
    were found by reading, which is the part that does not scale.
    """
    # The helpers, over text written here: the repo check below cannot fail
    # once the section is correct.
    probe = (
        "## Working agreements\n\n"
        f"{CONVENTION_SECTION_HEADING}\n\n"
        "Two conventions, because.\n\n"
        "- **A thing** is named so. `GSF-M2.1` is the guard.\n"
        "- **Another thing** is named so. `MAW-M3.1` is the guard.\n\n"
        "### The next section\n\n"
        "- **Not a convention** at all.\n"
    )
    section = convention_section(probe)
    assert "Not a convention" not in section, (
        "the section reader runs past its own heading, so a bullet from the "
        "next section would be counted as a convention"
    )
    assert convention_bullet_count(section) == 2
    assert stated_convention_count(section) == 2
    assert stated_convention_count("no count here at all") is None
    assert convention_section("# A document with no such section") == ""

    # And over the agreement itself.
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    section = convention_section(claude)
    assert section, (
        f"CLAUDE.md has no '{CONVENTION_SECTION_HEADING}' section, so the "
        "citation conventions the guards enforce are written nowhere a "
        "future author will read them"
    )
    stated = stated_convention_count(section)
    actual = convention_bullet_count(section)
    assert stated == actual, (
        f"the section says there are {stated} conventions and states {actual}. "
        "A reader who counts is right and the sentence is wrong; a reader who "
        "trusts the sentence stops reading early."
    )
    for guard in PROSE_CITATION_GUARD_IDS:
        assert guard in section, (
            f"{guard} reads prose for a name that should not resolve, and the "
            "conventions section does not name it — so the only way to learn "
            "its rule is to write a sentence and watch it fail"
        )


RETIRED_VOCABULARY_PATH = REPO_ROOT / "tools/agents/retired_vocabulary.json"


def load_retired_vocabulary(path: Path) -> dict:
    """The retired-vocabulary config, parsed."""
    return json.loads(path.read_text(encoding="utf-8"))


_BLOCK_START = re.compile(r"^\s*(?:[-*+>|]|#{1,6}\s|\d+[.)]\s)")
_SELF_CONTAINED_BLOCK = re.compile(r"^\s*(?:#{1,6}\s|\|)")


def prose_blocks(text: str) -> list[str]:
    """``text`` split where a markdown block starts, each block on one line.

    Purpose: a table row, a list item and a heading carry no terminal
             punctuation, so flattening a document and splitting on `.` makes
             a whole table into one sentence — and one `retired` in a far-off
             row then exempts every row in it.
    Spec:    docs/implementation_plan_2026-11-09_derived_live_document_set.md#lds-m41
    Tests:   tests/test_repo_hygiene.py::test_ldsm41_no_live_document_uses_retired_vocabulary

    A blank line, a bullet, a table row, a heading or a numbered item starts a
    new block; any other line continues the one before it, which is what keeps
    hard-wrapped prose readable as a single sentence. A heading and a table row
    also *end* at their own newline, because a hard-wrapped continuation of
    either is not a thing markdown has — without that, the line after a heading
    joined it and a heading naming the retirement exempted the paragraph
    beneath it.
    """
    blocks: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            blocks.append([])
        elif _BLOCK_START.match(line) or not blocks or not blocks[-1]:
            blocks.append([line])
            if _SELF_CONTAINED_BLOCK.match(line):
                # A heading and a table row end at their own newline. Without
                # this the line after a heading joined it, and a heading
                # saying "What was retired" exempted the paragraph beneath —
                # which is the MH defect in a third form.
                blocks.append([])
        else:
            blocks[-1].append(line)
    return [" ".join(block) for block in blocks if block]


def prose_sentences(text: str) -> list[str]:
    """``text`` as sentences, one markdown block at a time.

    Hard-wrapped prose inside a block is flattened, so a sentence that spans
    three lines is read whole; blocks are never joined to each other, which is
    what stops a marker in one table row exempting the rest of the table.
    Inline code spans go because a phrase quoted inside backticks is an
    artifact being named — a grep pattern, a filename, a quoted specimen — and
    not a description of how work is done.
    """
    out: list[str] = []
    for block in prose_blocks(text):
        flat = re.sub(r"`[^`]*`", " ", re.sub(r"\s+", " ", block))
        out.extend(re.split(r"(?<=[.;:!?])\s+", flat))
    return out


def sentence_is_history(
    sentence: str,
    markers: Iterable[str],
    reporting: Iterable[str] = (),
    blockers: Iterable[str] = (),
) -> bool:
    """Whether ``sentence`` reports a retired thing rather than describing one.

    Purpose: the exemption that keeps this guard from being a censor, split so
             that a past-tense account ("the document described the split") is
             history while a present-tense passive ("the Docs agent is
             described in AGENTS.md") is not.
    Spec:    docs/implementation_plan_2026-11-09_derived_live_document_set.md#lds-m41
    Tests:   tests/test_repo_hygiene.py::test_ldsm41_no_live_document_uses_retired_vocabulary

    ``markers`` are unconditional. A ``reporting`` verb counts only where it is
    not immediately preceded by one of ``blockers`` — a cold pass measured bare
    "described" exempting present-tense prose, and deleting it instead would
    have forced honest history to be rewritten.
    """
    lowered = sentence.lower()
    if any(marker.lower() in lowered for marker in markers):
        return True
    blockers = [blocker.lower() for blocker in blockers]
    for verb in reporting:
        verb = verb.lower()
        start = lowered.find(verb)
        while start != -1:
            before = lowered[:start]
            if not any(before.endswith(blocker) for blocker in blockers):
                return True
            start = lowered.find(verb, start + 1)
    return False


def retired_vocabulary_hits(
    concepts: Iterable[dict],
    documents: Iterable[tuple[str, str]],
    markers: Iterable[str] = (),
    reporting: Iterable[str] = (),
    blockers: Iterable[str] = (),
) -> list[str]:
    """``label: concept id: phrase`` for every retired phrase used as current.

    Purpose: a retired *concept* described as current is invisible to every
             citation guard, because a citation is a path and a description is
             prose.
    Spec:    docs/implementation_plan_2026-11-09_derived_live_document_set.md#lds-m41
    Tests:   tests/test_repo_hygiene.py::test_ldsm41_no_live_document_uses_retired_vocabulary

    Case-insensitive substring matching, because the phrase that found
    `docs/GEMINI.md` began a sentence and so began with a capital.

    A phrase is a finding only when the *sentence* holding it carries none of
    ``markers``. Without that window the guard failed on honest history —
    `AGENTS.md` naming the two branches that never existed, and
    `docs/GEMINI.md`'s own sentence saying the workflow was retired — which
    makes it a censor rather than a guard, and the citation conventions in
    `CLAUDE.md` exist precisely so that history stays writable.

    The window was the paragraph for one mutation round, and mutation MH
    measured what that cost: the exact sentence this guard exists for, put
    back into `docs/GEMINI.md`, did not fail it, because the bullet below it
    said "retired". A markdown paragraph of bullets is too coarse to carry
    the distinction between describing a thing and reporting that it is
    gone.

    Narrowing it to a sentence was not enough either, which a cold pass found
    after the mutation round: a table, a bullet list and a heading carry no
    terminal punctuation, so flattening a document made each of them one
    sentence and one `retired` anywhere in a table exempted every row of it.
    The window is one markdown block, then one sentence inside it — see
    `prose_blocks`.

    Takes every side as an argument so the scan can be driven over text
    written in a test: a comparison against the repository alone cannot fail
    once the repository is clean, which five mutations in the MAW batch
    established the hard way.
    """
    concepts = list(concepts)
    markers = list(markers)
    reporting = list(reporting)
    blockers = list(blockers)
    out = []
    for label, text in documents:
        for concept in concepts:
            if label in concept.get("allowed_in", ()):
                continue
            for phrase in concept["phrases"]:
                lowered_phrase = phrase.lower()
                for sentence in prose_sentences(text):
                    lowered = sentence.lower()
                    if lowered_phrase not in lowered:
                        continue
                    if sentence_is_history(sentence, markers, reporting, blockers):
                        continue
                    out.append(f"{label}: {concept['id']}: {phrase}")
                    break
    return out


def test_ldsm41_no_live_document_uses_retired_vocabulary():
    """LDS-M4.1, LDS-M4.2, LDS-M4.3 — `MAW-A3` closed.

    Purpose: retiring a concept must take its vocabulary out of the live
             documents, not only its pointers.
    Spec:    docs/implementation_plan_2026-11-09_derived_live_document_set.md#lds-m41
    Tests:   this test

    `docs/GEMINI.md` described the work as split between three named agents
    for two batches after the workflow was retired, inside the scanned set the
    whole time. Both guards that read that document resolve paths, and that
    sentence contains none.
    """
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_ci_contract import _live_documents

    # The config: shape first, because a guard reading a malformed concept
    # silently reads no phrases.
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "tools/agents/retired_vocabulary.json"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert tracked.returncode == 0, (
        "tools/agents/retired_vocabulary.json is not tracked, so it is absent "
        "on CI and this guard raises there instead of reading the documents. "
        "The repo ignores *.json; an editorial config needs an explicit "
        "negation in .gitignore, as email_cleaning_rules.json has."
    )
    config = load_retired_vocabulary(RETIRED_VOCABULARY_PATH)
    assert config.get("_comment"), (
        "the config has no _comment, so the next reader has no statement of "
        "what it is for or how a phrase is matched (global rule 9)"
    )
    concepts = config["concepts"]
    markers = config["retirement_markers"]
    reporting = config["reporting_markers"]
    blockers = config["reporting_marker_blockers"]
    assert markers, (
        "no retirement markers, so every mention of a retired concept is a "
        "finding — including the sentences that say it was retired, which is "
        "a censor and not a guard"
    )
    assert config.get("_retirement_markers_comment"), (
        "the markers have no comment, so the next reader cannot tell what "
        "window they are read over, or that it is one markdown block"
    )
    # The markers are the guard's entire exemption surface, and until a cold
    # pass measured it nothing bounded them: adding `"the "` kept every
    # fixture below green while exempting essentially every sentence in the
    # repo. A marker must not occur in ordinary current-tense prose.
    neutral_prose = (
        "Work happens on main, or on a feature branch merged into it.",
        "The sidebar drives navigation between 13 screens.",
        "Every DatabaseManager in a test takes an explicit tmp_path database.",
        "One batch builds in this checkout at a time, and the index is shared.",
        "A cold pass gets the diff and the range and none of the narrative.",
    )
    for marker in markers:
        assert len(marker) >= 5, (
            f"retirement marker {marker!r} is short enough to appear inside "
            "an unrelated word, and it exempts every sentence it lands in"
        )
        for ordinary in neutral_prose:
            assert marker.lower() not in ordinary.lower(), (
                f"retirement marker {marker!r} occurs in ordinary "
                f"current-tense prose ({ordinary!r}), so it exempts "
                "sentences that are describing present practice"
            )
    for marker in markers:
        others = [other for other in markers if other != marker]
        assert not any(other in marker for other in others), (
            f"retirement marker {marker!r} contains another marker, so it is "
            "dead config: the shorter one already matches everywhere it does"
        )
    assert concepts, "no retired concepts declared; the scan would be vacuous"
    seen = set()
    for concept in concepts:
        for field in ("id", "retired", "reason", "write_instead", "phrases"):
            assert concept.get(field), (
                f"concept {concept.get('id', '?')!r} is missing {field!r}; a "
                "prohibition without a date and a reason is archaeology a "
                "future reader cannot date or argue with"
            )
        assert concept["id"] not in seen, f"duplicate concept id {concept['id']!r}"
        seen.add(concept["id"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", concept["retired"]), (
            f"concept {concept['id']!r} has retired={concept['retired']!r}, "
            "which is not an ISO date"
        )
        assert all(len(phrase) >= 8 for phrase in concept["phrases"]), (
            f"concept {concept['id']!r} has a phrase short enough to appear "
            "in an ordinary sentence; a substring scan on it would fail on "
            "prose that has nothing to do with the retired concept"
        )
        if concept.get("allowed_in"):
            assert concept.get("allowed_because"), (
                f"concept {concept['id']!r} exempts documents without saying "
                "why, so the exemption cannot be reviewed"
            )

    # The scan, over text written here, in both directions and both cases.
    sentence = "Work is typically split between Code, Docs, and GitHub agents."
    history = (
        "There are no per-role branches; the three-agent workflow this "
        "section used to describe was retired on 2026-11-09."
    )
    # Two phrases of the one concept match it, which is deliberate: the long
    # form is the sentence this repo actually wrote, the short one catches a
    # paraphrase. Every hit is reported, so the failure message names the
    # phrase to rewrite rather than the first phrase that happened to match.
    assert retired_vocabulary_hits(concepts, [("PROBE.md", sentence)], markers, reporting, blockers) == [
        "PROBE.md: three-agent-workflow: code, docs, and github agents",
        "PROBE.md: three-agent-workflow: github agent",
    ], "the sentence that two batches missed is no longer matched"
    # The other direction, which is the whole design: the same vocabulary,
    # named as history, is not a finding. Without this the guard rejected
    # AGENTS.md, docs/GEMINI.md and docs/spec_coverage.md on their own
    # accounts of the retirement.
    assert retired_vocabulary_hits(concepts, [("PROBE.md", history)], markers, reporting, blockers) == [], (
        "prose that says the concept was retired is reported as though it "
        "described the concept as current, so the guard is a censor"
    )
    assert retired_vocabulary_hits(concepts, [("PROBE.md", history)]) != [], (
        "the markers are not the mechanism — the history prose passes with "
        "no markers given, so something else is exempting it"
    )
    # The window is the sentence, and the sentence alone. This is the
    # assertion mutation MH was missing: with a paragraph window, the bad
    # sentence sat beside a bullet saying "retired" and the guard stayed
    # green on the one defect it was written for.
    # And the window is one markdown *block*, not the flattened document.
    # A table row, a bullet and a heading end without punctuation, so a
    # sentence window over flattened text made each table one sentence. A
    # cold pass measured all three forms of the MH defect passing.
    # The fixtures end without punctuation on purpose. With a full stop the
    # sentence split separates them by itself and the block boundary is never
    # exercised — mutation MP measured exactly that, and came back green.
    marked = "the three-agent workflow was retired on 2026-11-09"
    unpunctuated = sentence.rstrip(".")
    for shape, text in (
        ("a bullet list", f"- {marked}\n- {unpunctuated}\n"),
        ("a table", f"| x | {marked} |\n| y | {unpunctuated} |\n"),
        ("a heading", f"### What was retired\n{unpunctuated}\n"),
        ("a numbered list", f"1. {marked}\n2. {unpunctuated}\n"),
    ):
        assert retired_vocabulary_hits(concepts, [("PROBE.md", text)], markers, reporting, blockers), (
            f"the defect sentence in {shape} is exempted by a marker "
            "elsewhere in the same block, which is mutation MH again in the "
            "form a cold pass found: a marker in one table row must not "
            "exempt another row"
        )
        assert retired_vocabulary_hits(concepts, [("PROBE.md", text.replace(unpunctuated, marked))], markers, reporting, blockers) == [], (
            f"{shape} holding only marked history is a finding, so the "
            "block split has made the guard a censor instead"
        )

    assert retired_vocabulary_hits(
        concepts, [("PROBE.md", f"{history}\n{sentence}")], markers
    ) == [
        "PROBE.md: three-agent-workflow: code, docs, and github agents",
        "PROBE.md: three-agent-workflow: github agent",
    ], (
        "a retirement marker in a neighbouring sentence exempts this one, so "
        "a description of current practice passes whenever it is written next "
        "to an account of the retirement — which is where it would be written"
    )
    # Hard-wrapped prose is one sentence, not three lines.
    wrapped = "The branches\ncodex/agent-docs and codex/agent-github never\nexisted here."
    assert retired_vocabulary_hits(concepts, [("PROBE.md", wrapped)], markers, reporting, blockers) == [], (
        "a sentence wrapped across lines is no longer read whole, so honest "
        "history fails whenever its marker lands on another line"
    )
    # A phrase quoted inside backticks is an artifact named, not a
    # description: `git grep -i \"docs agent\"` is a command.
    assert retired_vocabulary_hits(
        concepts, [("PROBE.md", 'Found by `git grep -i "docs agent"` over the tree.')], markers
    ) == [], "an inline code span is read as prose, so quoting a command fails the guard"
    assert prose_sentences("a `b c` d. e") == ["a   d.", "e"], (
        "prose_sentences no longer strips inline code or splits on sentence "
        "ends, so the window the markers are read over has changed"
    )
    assert retired_vocabulary_hits(concepts, [("PROBE.md", sentence.upper())], markers, reporting, blockers), (
        "the scan is case-sensitive, so a phrase that opens a sentence "
        "evades it — the exact way the MAW agreement scan first failed"
    )
    # A past-tense account is history; the present-tense passive of the same
    # verb is not. A cold pass measured bare "described" exempting both.
    assert retired_vocabulary_hits(
        concepts,
        [("PROBE.md", "docs/GEMINI.md described the split between Code, Docs and GitHub agents.")],
        markers,
        reporting,
        blockers,
    ) == [], "a past-tense account of what a document said is not history"
    for passive in (
        "The Docs agent is described in AGENTS.md and owns every document.",
        "Each role is still described as owning a per-role branch.",
    ):
        assert retired_vocabulary_hits(
            concepts, [("PROBE.md", passive)], markers, reporting, blockers
        ), (
            "a present-tense passive of a reporting verb exempts the "
            f"sentence ({passive!r}), which is how bare 'described' let "
            "current-tense prose through"
        )

    assert retired_vocabulary_hits(concepts, [("PROBE.md", "work happens on main")], markers, reporting, blockers) == [], (
        "prose that names no retired concept is reported, so the guard "
        "would fail on honest documents"
    )
    # A whole-document exemption is still honoured when a concept carries
    # one, though no concept does: the markers do that work, and exempting
    # docs/GEMINI.md as a document would have hidden the one sentence this
    # guard was written for.
    # The fixture phrase deliberately contains no retirement marker — an
    # earlier draft used "a retired phrase", which the markers exempt, so the
    # assertion passed for the wrong reason.
    assert retired_vocabulary_hits(
        [{"id": "x", "phrases": ["the bongo protocol"], "allowed_in": ["PROBE.md"]}],
        [("PROBE.md", "here is the bongo protocol")],
        markers,
        reporting,
        blockers,
    ) == [], "a concept's allowed_in list is no longer honoured"
    assert not any(c.get("allowed_in") for c in concepts), (
        "a concept has taken a whole-document exemption; the per-sentence "
        "markers are the mechanism, and a document-wide pass is how the "
        "sentence in docs/GEMINI.md survived two batches"
    )
    assert retired_vocabulary_hits(
        [{"id": "x", "phrases": ["the bongo protocol"]}],
        [("PROBE.md", "here is The Bongo Protocol in prose")],
        markers,
        reporting,
        blockers,
    ) == ["PROBE.md: x: the bongo protocol"], (
        "the scan reads the concepts it is given, not a list of its own"
    )

    # And over the live documents.
    hits = retired_vocabulary_hits(
        concepts,
        [
            (doc.relative_to(REPO_ROOT).as_posix(), doc.read_text(encoding="utf-8"))
            for doc in _live_documents()
        ],
        markers,
        reporting,
        blockers,
    )
    if hits:
        reasons = {
            concept["id"]: f"{concept['reason']} Write it instead: {concept['write_instead']}"
            for concept in concepts
        }
        detail = "\n  ".join(sorted(hits))
        advice = "\n  ".join(f"{cid}: {why}" for cid, why in sorted(reasons.items()))
        raise AssertionError(
            "these live documents use the vocabulary of a retired "
            f"concept:\n  {detail}\n\n  {advice}"
        )
