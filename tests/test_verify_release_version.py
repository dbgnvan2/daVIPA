"""Tests for the reconciliation between a release's version and its artifact.

Purpose: prove the check that reads the BUILT bundle can actually fail, in
         every shape the real defect took.
Spec:    docs/spec_2026-08-18_downloadable_release.md#r-m4e
Tests:   this file

Every other guard in this area reads an input file -- the changelog, the spec's
AST, a package constant. The bug they were written for (`0.0.0` in every
published release) was invisible to all of them, because none read what
PyInstaller wrote. So the case that matters most below is the one where the
plist has no CFBundleShortVersionString at all: that is exactly what
`BUNDLE(version=None)` produced, and it must fail rather than read as
"nothing to check" (P2, P6).
"""

from __future__ import annotations

import pathlib
import plistlib
import sys
from pathlib import Path

# Before any project import -- see the note in tests/test_version_source.py.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

from tools.verify_release_version import (  # noqa: E402
    SHORT_VERSION_KEY,
    main,
    package_version,
    plist_short_version,
)

CHANGELOG = (
    "# Changelog\n\n"
    "## [Unreleased]\n\n"
    "- pending\n\n"
    "## [1.4.0] - 2026-05-05\n\n"
    "- shipped\n\n"
    "## [1.3.0] - 2026-04-04\n\n"
    "- older\n"
)


@pytest.fixture
def changelog(tmp_path: Path) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG, encoding="utf-8")
    return path


@pytest.fixture
def package_init(tmp_path: Path) -> Path:
    """A package init agreeing with the fixture changelog's newest release."""
    path = tmp_path / "package_init.py"
    path.write_text('"""doc."""\n\n__version__ = "1.4.0"\n', encoding="utf-8")
    return path


@pytest.fixture
def run(changelog: Path, package_init: Path):
    """Invoke main() with both sources pointed at the fixtures.

    The __version__ reconciliation is unconditional, so every case has to say
    which package init it means -- otherwise these tests would be comparing the
    fixture changelog against the real repo's constant and failing for a reason
    that has nothing to do with what they assert.
    """
    def _run(*args: str) -> int:
        return main([*args, "--changelog", str(changelog),
                     "--package-init", str(package_init)])
    return _run


def _plist(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    with path.open("wb") as handle:
        plistlib.dump(payload, handle)
    return path


def test_with_no_tag_and_no_plist_it_still_reconciles_the_package(run, capsys):
    """Never a no-op: the __version__ check is unconditional."""
    assert run() == 0
    out = capsys.readouterr().out
    assert "__version__ matches the changelog" in out
    assert "no tag given" in out, (
        "a skipped tag check has to say so, or a release build that verified "
        "nothing about its tag looks identical to one that verified it"
    )
    assert "no plist given" in out, (
        "a skipped plist check has to say so too. Without the note the only "
        "difference between 'read the bundle and agreed' and 'never looked at "
        "a bundle' is the ABSENCE of a line, and nobody reads an absence -- "
        "which is the shape of the defect this script exists to close"
    )


def test_a_checked_plist_announces_itself_rather_than_only_the_failure(
        run, tmp_path, capsys):
    """The ok: line is what makes the note above meaningful."""
    plist = _plist(tmp_path, "Info.plist", {"CFBundleShortVersionString": "1.4.0"})
    assert run("--plist", str(plist)) == 0
    out = capsys.readouterr().out
    assert "built bundle reports 1.4.0" in out
    assert "no plist given" not in out


@pytest.mark.parametrize("tag", ["   ", " ", "\t", "\n"])
def test_a_whitespace_tag_is_an_error_not_a_skip(run, capsys, tag):
    """Behaviour changed deliberately: this used to be skipped like "".

    The two are not the same input. An unset workflow input expands to "",
    which is a check to skip. Whitespace is a release_tag somebody set wrong
    -- and the publish job gates on `inputs.release_tag != ''`, which is TRUE
    for " ", so skipping here would reconcile nothing and still create a
    public release under that tag. "Given nothing" and "given something
    unusable" must not take the same quiet path (P1).
    """
    assert run("--tag", tag) == 1
    captured = capsys.readouterr()
    assert "blank but not empty" in captured.err
    assert "no tag given" not in captured.out, (
        "it reported the tag as absent as well as rejecting it"
    )


def test_an_empty_tag_is_skipped_and_announced(run, capsys):
    """`--tag "$INPUT"` expands to an empty string when unset. That is not a
    tag to check, and not an error -- but it must not look like a pass."""
    assert run("--tag", "") == 0
    assert "no tag given" in capsys.readouterr().out


def test_a_checked_tag_is_announced(run, capsys):
    assert run("--tag", "v1.4.0") == 0
    out = capsys.readouterr().out
    assert "tag v1.4.0 matches the changelog" in out
    assert "no tag given" not in out


def test_a_matching_tag_passes(run):
    assert run("--tag", "v1.4.0") == 0


def test_a_bare_version_tag_passes(run):
    assert run("--tag", "1.4.0") == 0


@pytest.mark.parametrize(
    "tag",
    [
        pytest.param("v1.3.0", id="an-older-release-retagged"),
        pytest.param("v1.4.1", id="a-version-not-in-the-changelog"),
        pytest.param("v2.0.0", id="ahead-of-the-changelog"),
    ],
)
def test_a_tag_that_is_not_the_newest_heading_fails(run, tag):
    assert run("--tag", tag) == 1


def test_a_bundle_reporting_the_right_version_passes(run, tmp_path):
    plist = _plist(tmp_path, "good.plist", {SHORT_VERSION_KEY: "1.4.0"})
    assert run("--plist", str(plist)) == 0


def test_a_bundle_reporting_the_wrong_version_fails(run, tmp_path):
    plist = _plist(tmp_path, "wrong.plist", {SHORT_VERSION_KEY: "1.3.0"})
    assert run("--plist", str(plist)) == 1


def test_the_original_defect_fails_the_check(run, tmp_path):
    """PyInstaller given no version writes 0.0.0 -- every release up to v0.3.5."""
    plist = _plist(tmp_path, "zeroes.plist", {SHORT_VERSION_KEY: "0.0.0"})
    assert run("--plist", str(plist)) == 1


def test_a_plist_with_no_version_key_fails(run, tmp_path):
    """The absent-key shape must not read as "nothing to compare"."""
    plist = _plist(tmp_path, "keyless.plist", {"CFBundleName": "daVIPA"})
    assert run("--plist", str(plist)) == 1


def test_a_missing_plist_fails(run, tmp_path):
    assert run("--plist", str(tmp_path / "absent.plist")) == 1


def test_an_unparseable_plist_fails(run, tmp_path):
    path = tmp_path / "junk.plist"
    path.write_bytes(b"this is not a plist")
    assert run("--plist", str(path)) == 1


def test_a_missing_changelog_fails(tmp_path, package_init):
    assert main(["--tag", "v1.4.0", "--changelog", str(tmp_path / "none.md"),
                 "--package-init", str(package_init)]) == 1


def test_a_malformed_changelog_fails(tmp_path, package_init):
    """latest_released_version raises on `## [Yanked]`; that must surface as a
    non-zero exit, not a traceback escaping the script."""
    path = tmp_path / "CHANGELOG.md"
    path.write_text("## [Yanked]\n\n- nope\n", encoding="utf-8")
    assert main(["--tag", "v1.4.0", "--changelog", str(path),
                 "--package-init", str(package_init)]) == 1


def test_both_checks_must_pass_together(run, tmp_path):
    """A good tag does not excuse a bad bundle."""
    plist = _plist(tmp_path, "zeroes.plist", {SHORT_VERSION_KEY: "0.0.0"})
    assert run("--tag", "v1.4.0", "--plist", str(plist)) == 1


def test_plist_short_version_explains_a_missing_key(tmp_path):
    """Matched on the explanation, not the key name.

    `plist[SHORT_VERSION_KEY]` raises KeyError on its own, and that bare
    KeyError's message IS the key name -- so asserting on the key passes
    whether the explicit check exists or not. Proved by mutation: stubbing the
    check out left that weaker version of this test green. What the check adds
    is the sentence saying what a missing key means, which is the thing worth
    holding on to.
    """
    plist = _plist(tmp_path, "keyless.plist", {"CFBundleName": "daVIPA"})
    with pytest.raises(KeyError, match="built without a version"):
        plist_short_version(plist)


def test_plist_short_version_reads_a_real_value(tmp_path):
    plist = _plist(tmp_path, "good.plist", {SHORT_VERSION_KEY: "9.8.7"})
    assert plist_short_version(plist) == "9.8.7"


def test_a_stale_package_version_fails_even_with_a_good_tag(changelog, tmp_path):
    """The drift this whole batch exists for, on the path that builds a release.

    tests.yml does not run on a tag push, so the pytest guard holding
    __version__ to the changelog never fires for a release. This is that
    reconciliation where it does fire.
    """
    stale = tmp_path / "stale_init.py"
    stale.write_text('__version__ = "1.3.0"\n', encoding="utf-8")
    assert main(["--tag", "v1.4.0", "--changelog", str(changelog),
                 "--package-init", str(stale)]) == 1


def test_package_version_reads_a_literal(tmp_path):
    path = tmp_path / "init.py"
    path.write_text('__version__ = "2.5.1"\n', encoding="utf-8")
    assert package_version(path) == "2.5.1"


@pytest.mark.parametrize(
    "body",
    [
        pytest.param('"""no version here."""\n', id="absent"),
        pytest.param('__version__ = "1.0.0"\n__version__ = "2.0.0"\n', id="two-of-them"),
        pytest.param("__version__ = _compute()\n", id="computed"),
        pytest.param("__version__ = 3\n", id="not-a-string"),
    ],
)
def test_package_version_refuses_what_it_cannot_pin_down(tmp_path, body):
    """One literal or an error -- never a guess at which assignment counts."""
    path = tmp_path / "init.py"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match="literal __version__"):
        package_version(path)
