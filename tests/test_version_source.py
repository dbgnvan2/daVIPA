"""Tests for the one place an app version comes from.

Purpose: prove a built bundle carries a real version, and that the two places
         naming one cannot drift apart again.
Spec:    docs/spec_2026-08-18_downloadable_release.md#r-m4
Tests:   this file

Three places used to claim a version and two were wrong: `__version__` sat at
0.3.1 for four releases and was read by nothing, and daVIPA.spec passed none at
all, so every bundle's Info.plist reported 0.0.0. The guard that matters most
here is the first one -- it goes red when a release bumps CHANGELOG.md and
forgets the package, which is exactly how the drift started (P6: a version is a
status claim, and a claim is checked against the thing it describes).

The negative cases matter as much as the happy path. A version resolver that
falls back to a default on an unreadable changelog hands a build a number
nobody chose, and makes "the format changed" look like a successful read (P19).
"""

from __future__ import annotations

import ast
import pathlib
import sys
from pathlib import Path

# Before any project import. tests/test_ci_contract.py imports every test file
# on its own with the repo root and src/ stripped from sys.path, so a file that
# leans on conftest.py for them fails that probe.
_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

import getmoredone  # noqa: E402
from tools.version import (  # noqa: E402
    DEFAULT_CHANGELOG,
    latest_released_version,
    read_version,
    released_versions,
    version_sort_key,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_FILE = REPO_ROOT / "daVIPA.spec"


def test_package_version_matches_the_changelog():
    """The release step cannot bump one and forget the other."""
    from_changelog = read_version()
    assert getmoredone.__version__ == from_changelog, (
        f"getmoredone.__version__ is {getmoredone.__version__!r} but "
        f"CHANGELOG.md's newest released heading is {from_changelog!r}. "
        "A release bumped one and not the other."
    )


def test_unreleased_is_not_a_version():
    changelog = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "- work that has not shipped\n\n"
        "## [0.9.1] - 2026-01-01\n\n"
        "- work that shipped\n"
    )
    assert latest_released_version(changelog) == "0.9.1"


def test_an_out_of_order_changelog_raises_rather_than_being_sorted():
    """Topmost AND highest, or an error.

    This test has been through both behaviours. It first asserted that 2.0.0
    above 1.0.0 returns 2.0.0 -- true under either rule, so it proved nothing.
    Rewritten, it asserted the topmost heading wins even when lower, which was
    the behaviour then. A review pointed out what that behaviour costs: the
    build takes the wrong version and the __version__ guard compares against
    that same wrong value, so it passes. Now it raises.

    Sorting silently would return the right number from a broken file and
    leave the file broken.
    """
    changelog = (
        "## [1.0.0] - 2026-01-01\n\n- listed first\n\n"
        "## [2.0.0] - 2026-02-02\n\n- listed second\n"
    )
    with pytest.raises(ValueError, match="2.0.0 is newer"):
        latest_released_version(changelog)


@pytest.mark.parametrize(
    "heading",
    [
        pytest.param("Yanked", id="a-word"),
        pytest.param("TBD", id="a-placeholder"),
        pytest.param("O.3.6", id="a-typod-leading-zero"),
        pytest.param("Version 0.3.6", id="a-prose-heading"),
        pytest.param("0.4.0-rc1", id="a-pre-release"),
        pytest.param("0", id="one-part"),
        pytest.param("1.2.3.4", id="four-parts"),
    ],
)
def test_a_heading_that_is_not_a_version_raises(heading):
    """Each of these used to pass straight through into the bundle's
    CFBundleShortVersionString, verbatim -- `Version 0.3.6` arriving as
    `ersion 0.3.6`, because normalise_version strips a leading V.

    The pre-release case raises on purpose rather than being accepted: what a
    bundle should report for `0.4.0-rc1` is a decision nobody has made, and
    guessing it here is how this file got into trouble.
    """
    changelog = f"## [{heading}] - 2026-01-01\n\n- content\n"
    with pytest.raises(ValueError, match="not x.y or x.y.z"):
        latest_released_version(changelog)


def test_the_repo_changelog_lists_releases_newest_first():
    """What makes "topmost" mean "newest" for this repo.

    latest_released_version does not compare versions, and nothing in the
    Keep a Changelog format stops a heading being inserted out of order. Out of
    order, a build is labelled with the wrong version and the __version__ drift
    guard compares against that same wrong value, so it passes. This is the
    check that cannot be satisfied by the mistake.
    """
    versions = released_versions(DEFAULT_CHANGELOG.read_text(encoding="utf-8"))
    assert versions, "CHANGELOG.md names no released version"

    keys = [version_sort_key(version) for version in versions]
    assert keys == sorted(keys, reverse=True), (
        f"CHANGELOG.md does not list releases newest-first: {versions}. "
        "latest_released_version takes the topmost heading, so an out-of-order "
        "heading labels the next build with the wrong version."
    )
    assert len(set(keys)) == len(keys), (
        f"CHANGELOG.md repeats a version heading: {versions}"
    )


def test_released_versions_keeps_file_order_and_drops_non_versions():
    changelog = (
        "## [Unreleased]\n\n- pending\n\n"
        "## [9.9.9] - 2026-03-03\n\n- newest\n\n"
        "## [ ] - 2026-02-02\n\n- blank\n\n"
        "## [0.1.0] - 2026-01-01\n\n- oldest\n"
    )
    assert released_versions(changelog) == ["9.9.9", "0.1.0"]


def test_version_sort_key_compares_numerically_not_as_text():
    """0.3.10 is newer than 0.3.5, which string ordering gets backwards."""
    assert version_sort_key("0.3.10") > version_sort_key("0.3.5")
    assert "0.3.10" < "0.3.5", "if this fails the test above has stopped proving anything"


@pytest.mark.parametrize(
    "version",
    [
        pytest.param("", id="empty"),
        pytest.param("1.2.3a", id="suffix"),
        pytest.param("1.2.x", id="placeholder"),
        pytest.param("1..2", id="empty-part"),
        pytest.param("one.two", id="words"),
    ],
)
def test_version_sort_key_refuses_what_it_cannot_parse(version):
    """Sorting an unparseable version as equal would pass the ordering guard
    over exactly the heading it should have caught.

    Matched on the message, not just the type. `int("3a")` raises ValueError on
    its own, so a bare `pytest.raises(ValueError)` passes whether the explicit
    check is there or not -- proved by mutation: relaxing `all` to `any` left
    that weaker version of this test green.
    """
    with pytest.raises(ValueError, match="not a dotted numeric version"):
        version_sort_key(version)


def test_a_v_prefixed_heading_is_normalised():
    assert latest_released_version("## [v1.2.3] - 2026-01-01\n") == "1.2.3"


@pytest.mark.parametrize(
    "changelog",
    [
        pytest.param("", id="empty-file"),
        pytest.param("# Changelog\n\nProse and no headings.\n", id="no-headings"),
        pytest.param("## [Unreleased]\n\n- only unshipped work\n", id="only-unreleased"),
        pytest.param("## [unreleased]\n\n- lower case\n", id="only-unreleased-lowercase"),
        pytest.param("## [UNRELEASED]\n\n- upper case\n", id="only-unreleased-uppercase"),
        pytest.param("## [ ] - 2026-01-01\n\n- blank heading\n", id="blank-version"),
        pytest.param("## [v] - 2026-01-01\n\n- prefix only\n", id="prefix-only"),
    ],
)
def test_no_released_version_raises(changelog):
    """Never a default: a build stops rather than invent a version."""
    with pytest.raises(ValueError):
        latest_released_version(changelog)


def test_read_version_raises_when_the_changelog_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_version(tmp_path / "there-is-no-changelog.md")


def test_read_version_defaults_to_the_repo_changelog():
    assert read_version() == latest_released_version(
        DEFAULT_CHANGELOG.read_text(encoding="utf-8")
    )


def _bundle_keywords() -> dict[str, ast.expr]:
    """Return the BUNDLE(...) keywords from daVIPA.spec, by name.

    A spec file cannot be imported, so this parses rather than greps -- the
    repo's rule for a source-text guard that cannot be avoided. Same approach
    as tests/test_packaging_resources.py.
    """
    tree = ast.parse(SPEC_FILE.read_text(encoding="utf-8"), filename=str(SPEC_FILE))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "BUNDLE"
    ]
    assert len(calls) == 1, (
        f"daVIPA.spec has {len(calls)} BUNDLE calls, expected exactly 1"
    )
    return {kw.arg: kw.value for kw in calls[0].keywords if kw.arg is not None}


def test_the_bundle_is_given_a_version():
    keywords = _bundle_keywords()
    assert "version" in keywords, (
        "daVIPA.spec BUNDLE() has no version=, so CFBundleShortVersionString "
        "falls back to 0.0.0 and an installed app cannot say which build it is."
    )
    value = keywords["version"]
    assert isinstance(value, ast.Name) and value.id == "APP_VERSION", (
        "BUNDLE(version=...) must be APP_VERSION, resolved from the changelog. "
        f"It is {ast.unparse(value)!r}, and a literal there is a third place "
        "to forget."
    )


def test_the_spec_resolves_the_version_rather_than_hard_coding_it():
    tree = ast.parse(SPEC_FILE.read_text(encoding="utf-8"), filename=str(SPEC_FILE))
    assigned = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", "") == "APP_VERSION" for target in node.targets)
    ]
    assert len(assigned) == 1, (
        f"daVIPA.spec has {len(assigned)} APP_VERSION assignments, expected 1"
    )
    call = assigned[0]
    assert isinstance(call, ast.Call) and getattr(call.func, "id", "") == "read_version", (
        f"APP_VERSION must come from read_version(), not {ast.unparse(call)!r}"
    )
