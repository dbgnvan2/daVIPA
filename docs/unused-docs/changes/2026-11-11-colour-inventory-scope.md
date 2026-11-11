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
555 -> 526, `theme_api` 23 -> 2, `app_settings` 26 -> 26, `theme_files`
765 -> 765, `tuples` 2 -> 2. `theme_api`'s 23 is the count with the three
globs in place; 25 is the count without the gate-fixture glob, and quoting it
here left the table summing to 1955 against a stated 1953.

## Revised the same day: the generator is in, and the grays are visible

Two changes the repo owner asked for after this was filed.

**`tools/generate_ctk_themes.py` is now scanned** -- it writes the files in
`themes/`, so the inventory covered its output while missing where those
colours are authored. It put 37 lines back (33 `hex`, 4 `named`). Declared as
a *file*, not as the `tools` directory: `tools/color_audit.py` beside it
matches `HEX_PATTERN` with its own regex literals, so a directory path would
report the scanner's source as the app's colour usage.

**`NAMED_PATTERN` now matches the gray-scale suffix.** It took bare colour
words only, so CustomTkinter's `"gray95"`/`"gray17"` were invisible to every
scan: 539 of the 544 lines holding one, 527 of them theme lines carrying no
other colour and so appearing nowhere in the report at all. Found by the cold
pass over this narrowing.

A measured gotcha that came out of it: `.gitignore` has `*.json` whitelisted
back by `!themes/*.json`, and rg 14.1.1 honours that whitelist only when
`themes` is the sole search path -- `rg P themes` returns 532 lines, `rg P src
themes` returns 1. Any scan over `themes` therefore keeps its own invocation.

## The one blind spot this leaves

`assets/icons/*.svg` -- 5 named-colour occurrences, shipped UI resources, not
inventoried.

## What stops it drifting back

- `test_civm14_every_scan_stays_inside_the_declared_paths` asserts,
  behaviourally across all seven scans, that no returned line lies outside
  `src/`, `themes/` or the named generator file. Mutation-proved: widening the
  scan paths to `"."` turns it red.
- `test_civm15_gray_scale_literals_reach_the_named_tables` asserts that every
  line holding a `gray95`-style literal is returned by `named` or
  `theme_files`. It was written first and failed at 539 of 544.
- `test_civm5_the_scans_feeding_one_count_do_not_overlap` still guards the
  double count the `!themes/**` glob used to prevent. Mutation-proved:
  pointing `theme_files` at the repo root turns it red.

Scope lives in `UI_CODE_PATHS`, with `"themes"` and the `app_settings` path
still literals in `SCAN_COMMANDS`, so it is not quite one constant. A widening
is still a deliberate edit that fails a test rather than a silent change in
what the document means.
