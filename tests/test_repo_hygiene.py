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
    "learnings.md",
    "file-maintainability.md",
    "ui-regression.md",
    "security.md",
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
