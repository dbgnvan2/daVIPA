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
from pathlib import Path

import pytest

import getmoredone
from tools.version import DEFAULT_CHANGELOG, latest_released_version, read_version

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


def test_the_newest_released_heading_wins():
    changelog = (
        "## [2.0.0] - 2026-02-02\n\n- newer\n\n"
        "## [1.0.0] - 2026-01-01\n\n- older\n"
    )
    assert latest_released_version(changelog) == "2.0.0"


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
