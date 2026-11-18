#!/usr/bin/env python3
"""Reconcile a release's version against the things it produced.

Purpose: every other check in this area reads an INPUT file. The defect this
         closes -- `CFBundleShortVersionString 0.0.0` in every release ever
         published -- was invisible for exactly that reason: nothing read the
         bundle PyInstaller wrote. A flag that says "versioned" is checked
         against the artifact it describes, now (P6).
Spec:    docs/spec_2026-08-18_downloadable_release.md#r-m4e
Tests:   tests/test_verify_release_version.py

Usage:
    python tools/verify_release_version.py --tag v0.3.6
    python tools/verify_release_version.py --plist dist/daVIPA.app/Contents/Info.plist
    python tools/verify_release_version.py --tag "$GITHUB_REF_NAME" --plist <path>

Two reconciliations, each optional, both against CHANGELOG.md as the source:

  --tag    the tag being released must name the changelog's newest released
           version. The tag and the heading are two things a human sets
           separately. extract_release_notes.py already fails a tag with no
           matching section, but not a tag pointing at the wrong section -- so
           re-tagging an older version, or a `workflow_dispatch` whose
           release_tag input disagrees with the checked-out changelog, both
           publish assets whose version is not the one on the release.

  --plist  the built bundle's CFBundleShortVersionString must be that same
           version. This is the only check in the repo that reads what the
           build actually produced.

A script rather than inline workflow YAML for two reasons: a check that lives
only in a workflow cannot be run or tested before a push, and
tests/test_ci_contract.py bans `assert` and `python -c` inside run steps.

The `__version__`-against-changelog reconciliation is unconditional, so this is
never a no-op however it is called; a skipped tag or plist check says so on
stdout rather than passing quietly.

Exits 0 when every reconciliation agrees and 1 on any disagreement, including
a changelog, plist or package init it could not read.
"""

from __future__ import annotations

import argparse
import ast
import plistlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.extract_release_notes import normalise_version  # noqa: E402
from tools.version import DEFAULT_CHANGELOG, latest_released_version  # noqa: E402

SHORT_VERSION_KEY = "CFBundleShortVersionString"
PACKAGE_INIT = REPO_ROOT / "src" / "getmoredone" / "__init__.py"


def plist_short_version(plist_path: Path) -> str:
    """Return CFBundleShortVersionString from a built bundle's Info.plist.

    Raises:
        FileNotFoundError: no plist there. The caller has just built a bundle,
            so a missing plist means the build did not produce what it claims.
        KeyError: the key is absent. PyInstaller omits it entirely when
            BUNDLE() is given no version, which is the original defect -- it
            must not read as "matches" or as "nothing to check".
    """
    with plist_path.open("rb") as handle:
        plist = plistlib.load(handle)
    if SHORT_VERSION_KEY not in plist:
        raise KeyError(
            f"{plist_path} has no {SHORT_VERSION_KEY}. The bundle was built "
            f"without a version."
        )
    return str(plist[SHORT_VERSION_KEY])


def package_version(init_path: Path | None = None) -> str:
    """Return `__version__` from the package, by parsing rather than importing.

    Parsed because this runs inside a release build before the app's
    dependencies are necessarily importable, and because the value is wanted
    even when importing the package would fail for an unrelated reason.

    Raises:
        FileNotFoundError: no package init to read.
        ValueError: no single literal `__version__` assignment. Two of them, or
            a computed one, means this check no longer knows what it is
            comparing, and it must say so rather than pick one.
    """
    path = PACKAGE_INIT if init_path is None else init_path
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = [
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", "") == "__version__" for t in node.targets)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ]
    if len(found) != 1:
        raise ValueError(
            f"{path} has {len(found)} literal __version__ assignments, expected 1"
        )
    return found[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=None,
                        help="release tag or version, e.g. v0.3.6")
    parser.add_argument("--plist", type=Path, default=None,
                        help="path to a built bundle's Info.plist")
    parser.add_argument("--changelog", type=Path, default=DEFAULT_CHANGELOG)
    parser.add_argument("--package-init", type=Path, default=None,
                        help="package __init__.py holding __version__")
    args = parser.parse_args(argv)

    # An empty --tag is what an unset workflow input expands to, and it must not
    # count as a tag that was checked. It is not an error either: the
    # __version__ reconciliation below is unconditional, so there is always one
    # real check and this script is never a no-op. What it must not do is stay
    # quiet about the check it skipped.
    tag = (args.tag or "").strip()

    if not args.changelog.exists():
        print(f"error: no changelog at {args.changelog}", file=sys.stderr)
        return 1
    try:
        expected = latest_released_version(
            args.changelog.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []

    if not tag:
        print("note: no tag given -- tag/changelog agreement not checked")
    else:
        from_tag = normalise_version(tag)
        if from_tag != expected:
            failures.append(
                f"tag {tag!r} names version {from_tag!r} but "
                f"{args.changelog.name}'s newest released heading is "
                f"{expected!r}"
            )
        else:
            print(f"ok: tag {tag} matches the changelog ({expected})")

    if args.plist is not None:
        try:
            built = plist_short_version(args.plist)
        except (FileNotFoundError, KeyError, plistlib.InvalidFileException) as exc:
            failures.append(f"could not read a version from {args.plist}: {exc}")
        else:
            if built != expected:
                failures.append(
                    f"{args.plist} reports {SHORT_VERSION_KEY} {built!r} but "
                    f"the changelog's newest released heading is {expected!r}"
                )
            else:
                print(f"ok: built bundle reports {built}")

    # Not optional, and not gated on --tag/--plist. The pytest guard that holds
    # __version__ to the changelog does not run on a tag push: tests.yml
    # triggers on branches only. This is that same reconciliation, on the path
    # that actually builds a release.
    try:
        from_package = package_version(args.package_init)
    except (FileNotFoundError, SyntaxError, ValueError) as exc:
        failures.append(f"could not read __version__: {exc}")
    else:
        if from_package != expected:
            failures.append(
                f"__version__ is {from_package!r} but the changelog's newest "
                f"released heading is {expected!r}"
            )
        else:
            print(f"ok: __version__ matches the changelog ({expected})")

    for failure in failures:
        print(f"error: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
