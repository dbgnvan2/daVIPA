# Colour inventory scope: CIV-A1 decided

**Date:** 2026-11-11
**Decision:** narrow the colour scan to `src/` and `themes/`.
**Decided by:** the repo owner, answering the question two cold passes raised.

This is the record of a `BACKLOG.md` item that left because it was settled.
Filed here, not kept open there, because `BACKLOG.md` holds open work only.

## What changed

`tools/color_audit.py`'s five recursive scans searched `.` and carried three
exclusion globs. They now search `UI_CODE_ROOT = "src"`, and `theme_files`
still searches `themes`. All three globs are gone: with `src` and `themes` as
the only search paths, the report itself, the theme files' double count and
the staleness gate's own fixtures are unreachable rather than excluded.

## Why

The repo-root scan counted every document, spec, plan, archive and test
fixture that mentioned a colour as the app's colour usage. Measured
2026-11-11:

- A docs-only edit made the committed report stale, because the occurrence
  rows cite the matched line by number. It happened twice inside the batch,
  against this repo's own rule that a document alone earns no sweep.
- 3 of the 5 lines the `tuples` scan returned came from the gate's own
  fixture file, so `scan_all`'s refusal of an empty scan -- the only guard
  against a scan going blind -- could be satisfied by test data.
- Section 1's "Hard Rule" is about hard-coded colours in UI code, which is
  not what a repository-wide census measures.

## What it cost

437 of 1953 occurrences, 22%. Measured before the change by top-level
directory, and reconciled against the regenerated report afterwards: the
seven scans now return 1516 lines, which is exactly the figure measured as
kept. By directory, dropped: `tests/` 284, `docs/` 101, `tools/` 39,
`assets/` 5, and 8 across `BACKLOG.md`, `AGENTS.md` and `NOTES.md`.

Per-scan, before -> after: `hex` 511 -> 154, `named` 71 -> 41, `widget`
555 -> 526, `theme_api` 25 -> 2, `app_settings` 26 -> 26, `theme_files`
765 -> 765, `tuples` 2 -> 2.

## Two blind spots this leaves

Both hold real UI colour and are no longer inventoried. Widening to either is
a one-line change in `SCAN_COMMANDS`.

- `tools/generate_ctk_themes.py` -- 37 colour occurrences on 2026-11-11. It
  *writes* the files in `themes/`, so the inventory now covers its output
  while missing where those colours are authored.
- `assets/icons/*.svg` -- 5 named-colour occurrences. Shipped UI resources.

## What stops it drifting back

- `test_civm14_every_scan_stays_inside_src_and_themes` asserts, behaviourally
  across all seven scans, that no returned line lies outside those two trees.
  Mutation-proved: widening `UI_CODE_ROOT` to `"."` turns it red.
- `test_civm5_the_scans_feeding_one_count_do_not_overlap` still guards the
  double count the `!themes/**` glob used to prevent. Mutation-proved:
  pointing `theme_files` at the repo root turns it red.

The scope is now one named constant, so a future widening is a deliberate
edit that fails a test rather than a silent change in what the document
means.
