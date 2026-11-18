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

import re
from pathlib import Path

from tools.extract_release_notes import VERSION_HEADING, normalise_version

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"

# The heading for work that has no version yet. Spelled in lower case because
# the comparison is case-folded: `## [unreleased]` is the same heading to a
# human, and labelling a bundle "unreleased" is the failure this skips.
UNRELEASED = "unreleased"

# A released heading is `x.y` or `x.y.z` and nothing else. Deliberately
# strict: `## [Yanked]`, `## [TBD]` and a typo'd `## [O.3.6]` all used to
# sail through and become CFBundleShortVersionString verbatim. A pre-release
# heading such as `0.4.0-rc1` is rejected too -- not because it is wrong to
# want one, but because what a bundle should then report is a decision
# nobody has made, and guessing it here is how this file got into trouble.
VERSION_SHAPE = re.compile(r"^\d+(?:\.\d+){1,2}$")


def version_sort_key(version: str) -> tuple[int, ...]:
    """Parse `1.2.3` into `(1, 2, 3)` so two versions can be compared.

    Raises:
        ValueError: not a dotted run of integers. The caller is an ordering
            guard, and a version it cannot parse has to stop it rather than
            sort as equal and let the check pass over the thing it was written
            to catch.
    """
    # str.split always yields at least one element, so there is no empty-list
    # case to test for and none is checked for here.
    parts = version.split(".")
    if not all(part.isdigit() for part in parts):
        raise ValueError(f"not a dotted numeric version: {version!r}")
    return tuple(int(part) for part in parts)


def released_versions(changelog: str) -> list[str]:
    """Every released version heading, in the order the file lists them.

    `## [Unreleased]` is skipped. It is a heading, not a version, and a build
    labelled with it tells the user nothing. So is a heading that normalises to
    nothing -- `## [ ]` and `## [v]` both do.
    """
    found: list[str] = []
    for match in VERSION_HEADING.finditer(changelog):
        version = normalise_version(match.group("version"))
        if version.casefold() == UNRELEASED:
            continue
        if not version:
            continue
        found.append(version)
    return found


def latest_released_version(changelog: str) -> str:
    """Return the version in the TOPMOST released heading.

    Topmost, and checked to be the highest. Keep a Changelog puts the newest
    release first, so in a well-formed file the two are the same heading. This
    returns the topmost one and raises when it is not also the maximum, rather
    than silently sorting: a changelog in the wrong order is a thing to fix,
    and returning the right answer from a broken file hides it. Every heading
    is shape-checked first, because the comparison cannot mean anything over a
    value it could not parse.

    Raises:
        ValueError: the text names no released version. A default returned
            here would label a bundle with a version nobody chose, and would
            make "the changelog is empty", "the heading format changed" and a
            real read look identical (P19) -- the same silent producer/consumer
            drift extract_release_notes.py refuses.
    """
    versions = released_versions(changelog)
    if not versions:
        raise ValueError("CHANGELOG.md names no released version heading")

    malformed = [v for v in versions if not VERSION_SHAPE.fullmatch(v)]
    if malformed:
        raise ValueError(
            f"CHANGELOG.md has version headings that are not x.y or x.y.z: "
            f"{malformed}. Every one of them is a candidate for the version a "
            f"bundle reports, so none can be waved through."
        )

    newest = max(versions, key=version_sort_key)
    if versions[0] != newest:
        raise ValueError(
            f"CHANGELOG.md lists {versions[0]} first but {newest} is newer. "
            f"Releases are newest-first; out of order, a build takes the wrong "
            f"version and the __version__ guard compares against that same "
            f"wrong value and passes."
        )
    return versions[0]


def read_version(changelog_path: Path | None = None) -> str:
    """Read the topmost released version straight from CHANGELOG.md.

    Raises:
        FileNotFoundError: no changelog to read. The caller is a build, and a
            build that cannot find the changelog must stop rather than invent
            a version.
        ValueError: see latest_released_version.
    """
    path = DEFAULT_CHANGELOG if changelog_path is None else changelog_path
    return latest_released_version(path.read_text(encoding="utf-8"))
