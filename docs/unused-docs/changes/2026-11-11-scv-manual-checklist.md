# Handoff Note

- Date: 2026-11-11
- Topic: scv-segment-colour-validation

## Summary

SCV-M1 to SCV-M6, closing `BACKLOG.md`'s `LRR-A1`. Both hand-rolled hex
validators now answer from `color_contrast`; `color_contrast.hex_to_rgb` is the
one place in the segment-colour path that slices a colour string into
`int(..., 16)`.

SCV-M6 is the required cold `learning-qa` pass's own seven findings, two of
them high, fixed in this batch because `CLAUDE.md` fixes medium-or-higher in
the session that finds them. The high ones both say the same thing: the gate
was narrower than the claim made for it. `row_fill` said it was the last gate
before `ctk.CTkFrame(fg_color=…)`; four more sites took a stored colour there,
including `apply_segment_accent` on the next line of all five row builders.

SCV-M7 is a second cold pass, required because SCV-M6 produced highs, run on
test quality and the UI contract rather than the failure patterns. Its high
says the same thing a third time, and this one bites hardest: SCV-M6 made
every colour dialog openable and left both screens that *list* a segment
raising before the Edit button that opens them was created. The remediation
path this note describes did not work. Both are gated now, including
`settings_vsp_segments.py`, which is not in the SCV diff and is fixed anyway
because checklist items 1 and 2 below are performed on it.

This note exists for the on-screen checks no test covers, and for one claim
this batch set out not to re-measure and then measured by accident.

## Files changed

- `src/getmoredone/color_contrast.py` — new `hex_to_rgb`; `relative_luminance`
  now calls it
- `src/getmoredone/vps_manager.py` — `_is_valid_hex_color`,
  `_derive_subsegment_color`, `DEFAULT_SUBSEGMENT_BASE`,
  `_segment_color_to_store` and its two call sites `create_segment` /
  `update_segment` (SCV-M5.1, from the cold pass over the plan)
- `src/getmoredone/vps_manager_taxonomy.py` — the repair pass in
  `get_vision_subsegments` / `get_vision_categories`, and the three writers
  `update_vision_subsegment_color`, `update_vision_subsegment`,
  `update_vision_category`
- `src/getmoredone/screens/vps_segment_editor.py` — `validate_color`,
  `save_segment`, and `__init__` / `load_segment_data` (SCV-M6.2)
- `src/getmoredone/theme.py` — `apply_segment_accent` (SCV-M6.3)
- `src/getmoredone/screens/segment_color_utils.py` — `_normalize_color`,
  `resolve_chip_colors` (SCV-M6.3)
- `src/getmoredone/screens/vision_segments.py` — `_color_input` (SCV-M6.3),
  `_chip_color` and all three refresh methods (SCV-M7.1, SCV-M7.2)
- `src/getmoredone/screens/settings_vsp_segments.py` — `create_segment_row`
  (SCV-M7.4); not in the SCV diff, fixed because checklist items 1 and 2 run
  on that screen
- `src/getmoredone/priority_levels.py` — `row_fill`, `RowFill`'s docstring,
  `_warn_unreadable_segment_color`'s message
- `tests/test_segment_colour_validation.py` (new),
  `tests/test_priority_level_colors.py`, `tests/test_vps_segments.py`
- `BACKLOG.md`, `docs/USER_GUIDE.md`, `docs/spec_coverage.md`,
  `docs/DOCUMENTATION_INDEX.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_segment_colour_validation.py tests/test_priority_level_colors.py tests/test_vps_segments.py tests/test_vps_integration.py tests/test_vps_subsegment_colors.py tests/test_traceability_refs.py tests/test_repo_hygiene.py tests/test_docs_sync_rule.py tests/test_ci_contract.py -q`
- Result: PASS (272 passed, 1 skipped)
- Command: `./venv/bin/python tools/agents/check_docs_sync.py`
- Result: PASS (documentation changed with the code)
- The plan's §7 command is wrong and was not what was run:
  `tests/test_vps_integration.py` references nothing this batch touches. The
  command above is the real one — `test_vps_subsegment_colors.py` is the only
  file asserting what `_derive_subsegment_color` produces,
  `test_unified_panel_design.py` and `test_rename_safe_links.py` reach the
  repair pass. Found by a cold pass over the plan, 2026-11-11.
- Each of the seven criteria's tests was confirmed red against `6963d0a`
  before its fix. The three written or strengthened after the fix were
  mutation-proved instead: the verbatim `6963d0a` bodies of
  `_is_valid_hex_color` and `_derive_subsegment_color` restored (8 red), and
  `_HEX_COLOR_RE` narrowed to refuse a `B` digit (11 red).

## Risks / Known gaps

- **The `TclError` half of `LRR-A1` is now measured, and it holds.** Neither
  that filing nor the SCV plan measured it: `LRR-A1` asserted that a raw value
  reaching `ctk.CTkFrame(fg_color=…)` raises `TclError` part-way through a
  refresh and takes the list screen down, and no session had put a widget on
  screen to confirm it. Mutation-proving SCV-M6.3's dialog test did: with the
  verbatim pre-fix body of `vision_segments._color_input` restored,
  `ctk.CTkFrame(..., fg_color="#0X1234")` raised
  `_tkinter.TclError: invalid color name "#0X1234"` from `tkinter/__init__.py`
  at widget construction. What is still not measured is the *consequence* —
  that the raise blanks the screen rather than losing one row — because that
  depends on where the caller's own try/except sits, and none of the five row
  builders has one around the row loop.
- **The repair pass now rewrites a stored colour that is merely not
  canonical**, not only one that is unreadable: a row holding `#1a2b3c` is
  rewritten to `#1A2B3C` on the first read after this change, and a row
  holding `#abc` to `#AABBCC`. One write per such row, once; the condition is
  `color == stored`, so the second read writes nothing. It is the same
  invariant the writers now keep, applied to rows that predate them.
- **A segment's own stored colour is never repaired on read.** The repair pass
  covers `vision_subsegments` and `vision_categories` only; there is none for
  `segment_descriptions`, and none was added — the readers are safe
  (`row_fill` normalises or draws nothing, `_derive_subsegment_color` falls
  back) and `SCV-M5` means no code path can write a bad value any more, so a
  malformed one has to predate 2026-11-11. Correcting it means re-setting the
  colour in the editor. Checklist item 3 below says so.
- **Both segment colour maps still hand callers the raw stored value**
  (`BACKLOG.md`'s `SCV-A2`, which now names the pair). `row_fill`,
  `apply_segment_accent` and the screens' own `_normalize_color` are all
  gated, so the drawing path is covered; the maps' other readers were not
  surveyed.
- **A repair pass now writes a line to `app.log` saying what it rewrote.** The
  first read after this change canonicalises every subsegment and category row
  whose colour is not already upper-case `#RRGGBB`, so that line will name a
  lot of rows once, then nothing. It is a `WARNING` because overwriting a
  stored value the user set is worth seeing; if the one-time volume is a
  nuisance it should become `INFO` for the already-readable case and stay
  `WARNING` for the unreadable one, which is not done here.

## Next agent actions

The manual checklist. None of this can be asserted from a test — it is what
the app does on screen, and the first two items are the only check that
`save_segment`'s normalisation is wired to the entry the user actually types
in rather than to a value the test supplied.

1. **VSP → Settings → VSP Life Segments → Edit a segment.** Type `#0X1234`
   into the colour field and press Save. Expected: refused, with the error
   naming the `#RRGGBB` form, and the dialog stays open with the typing
   intact. Before 2026-11-11 this saved.
2. **Same dialog, type `#abc` and Save.** Expected: accepted, the dialog
   closes, and re-opening the editor on that segment shows `#AABBCC` in the
   field. Before 2026-11-11 `#abc` was refused.
3. **A segment whose colour is already malformed in the database.** If
   `app.log` carries `Segment colour ... is not a #RRGGBB value`, open Today,
   Upcoming or All Items: expected, the rows in that segment draw with no fill
   — the theme's own background, as they would with no segment colour set —
   and the screen does not blank. Then open VSP → Vision Elements for that
   segment: its subsegment and category lists open, and *their* colours are
   repaired on that read (check by reopening the screen; the colours stay the
   repaired ones). The **segment's own** colour is not repaired — it still
   reads back malformed in the editor, and `app.log` still names it on each
   fresh launch. Re-set it in the editor to clear it.
4. **VSP → Vision Elements → edit a subsegment, then a category.** Both
   dialogs open, each showing a swatch and the stored text. If either one's
   stored colour is malformed, the swatch is slate `#334155` and the text is
   the stored value; before 2026-11-11 the dialog raised on opening, which is
   SCV-M6.3's half of the same defect as item 1's.
5. **Open Today or All Items on a segment whose colour is malformed, and look
   at the left edge of its rows.** Expected: no accent stripe and no fill,
   and the screen renders. Before 2026-11-11 `row_fill` dropped the fill and
   `apply_segment_accent` raised on the next line with the same value, so
   dropping the fill bought nothing. This is the check that the two gates are
   both in place; it cannot be read off the tests, which drive the two
   functions separately.
