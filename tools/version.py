#!/usr/bin/env python3
"""The one place an app version comes from: the CHANGELOG.

Purpose: three places used to claim a version and two of them were wrong.
         `getmoredone.__version__` sat at 0.3.1 for four releases and was read
         by nothing; daVIPA.spec passed no version at all, so every bundle's
         Info.plist reported CFBundleShortVersionString 0.0.0 and an installed
         app could not say which build it was.
Spec:    docs/spec_2026-08-18_downloadable_release.md#r-m4
Tests:   tests/test_version_source.py

CHANGELOG.md is the source because it is the file the release step already
edits, and `extract_release_notes.py` already treats it as authoritative for
the release body. Adding a second source of truth is what caused this.

This is a real module rather than a few lines inside daVIPA.spec for the reason
written at the top of that file: a spec file cannot be imported, so logic
living there cannot be tested. tools/packaging_filters.py exists for the same
reason.
"""

from __future__ import annotations

from pathlib import Path

from tools.extract_release_notes import VERSION_HEADING, normalise_version

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# The heading for work that has no version yet. Spelled in lower case because
# the comparison is case-folded: `## [unreleased]` is the same heading to a
# human, and labelling a bundle "unreleased" is the failure this skips.
UNRELEASED = "unreleased"


def latest_released_version(changelog: str) -> str:
    """Return the newest released version named in CHANGELOG.md text.

    `## [Unreleased]` is skipped. It is a heading, not a version, and a build
    labelled with it tells the user nothing.

    Raises:
        ValueError: the text names no released version. A default returned
            here would label a bundle with a version nobody chose, and would
            make "the changelog is empty", "the heading format changed" and a
            real read look identical (P19) -- the same silent producer/consumer
            drift extract_release_notes.py refuses.
    """
    for match in VERSION_HEADING.finditer(changelog):
        version = normalise_version(match.group("version"))
        if version.casefold() == UNRELEASED:
            continue
        if not version:
            continue
        return version
    raise ValueError("CHANGELOG.md names no released version heading")


def read_version(changelog_path: Path | None = None) -> str:
    """Read the newest released version straight from CHANGELOG.md.

    Raises:
        FileNotFoundError: no changelog to read. The caller is a build, and a
            build that cannot find the changelog must stop rather than invent
            a version.
        ValueError: see latest_released_version.
    """
    path = DEFAULT_CHANGELOG if changelog_path is None else changelog_path
    return latest_released_version(path.read_text(encoding="utf-8"))
