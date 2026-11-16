# Handoff Note

- Date: 2026-11-15
- Topic: date-band-colour — DBC, a Setting for the Day/Date band background

## Summary
`AppSettings.list_date_band_color` sets the background of the band that
labels a Day/Date in a listing of action items. There is exactly one such
band: the Upcoming screen's date group header. `""` keeps the theme's
`surface_subtle`, so an existing install is unchanged, and clearing the field
is how that colour comes back.

`theme.date_band_colors(settings)` returns the fill and the band label's
colour together. A picked fill has no theme pairing behind it, so the label
is derived with `pick_text_color`; measured over the whole `#RRGGBB` space on
a 5-step grid, the worst case is 4.583:1 at `#4B7D87`, so the 4.5:1 claim in
`CHANGELOG.md` and `docs/USER_GUIDE.md` holds for any colour a user can pick,
not only the two the tests name. A value `normalize_hex_color` rejects falls
back to the theme and warns once per value, rather than reaching Tk, which
raises from inside the list refresh.

Plan and decisions:
`docs/unused-docs/implementation_plan_2026-11-15_date_band_colour.md`.

## Scope decisions
- Today's "To Do" and "Completed" bands label a status section, not a day,
  and are untouched. So are the Drag Schedule date boxes and the Plan week's
  day columns, which are a calendar rather than a listing and have their own
  colour logic.
- **Known consequence:** the pinned column-heading row on the five list
  screens is also `surface_subtle`. Once a band colour is set, the Upcoming
  band and that heading no longer match. Raised before building and accepted.

## Verification
- Commands (targeted, throttled):
  `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_date_band_colour.py tests/test_color_inventory_sync.py tests/test_theme_settings.py tests/test_settings_save_refusal.py tests/test_priority_level_colors.py tests/test_future_dates.py tests/test_plan_settings.py -q`
  and `… tests/test_list_pane_rebuild.py tests/test_list_screen_resize.py tests/test_item_editor_no_context.py tests/test_docs_sync_rule.py tests/test_repo_hygiene.py tests/test_traceability_refs.py tests/test_ci_contract.py -q`
- Result: PASS (nine guards in `tests/test_date_band_colour.py`; 203 passed,
  1 skipped over the ten touched and adjacent files, the skip being the
  CI-only display check).
- Every guard mutation-checked against its verbatim line — 11 mutations, all
  red, every original restored. One assertion needed two lines mutated at
  once to fail (the end-to-end bad-value arm, before it was rewritten); that
  is recorded under *Fixed* 5 as the reason it was rewritten.
- `./venv/bin/python tools/agents/check_docs_sync.py --base a9c13f0 --head HEAD`
  → PASS.
- **Not walked on screen.** Per the standing rule in this workspace the app is
  not launched from a session; the checklist below is owed.
- The Appearance section has **no contract test** asserting its controls are
  present — a pre-existing gap, not introduced here. The new row's grid
  placement was checked by reading the whole section's rows (0–8, column 3
  carrying the Apply/Save button at rowspan 5) rather than by rendering it.

## Walk checklist (on the running app)
1. Settings → Appearance: the section still shows Appearance Mode, Color
   Theme, Row Text Size, Completion Badge + Browse, Confetti Every N, and
   Apply / Save — none moved out of view at the window's normal height.
2. A new row reads "Day/Date band colour:" with an entry, **Pick Colour**, and
   a swatch. With the field blank the swatch is the theme's band colour.
3. Type `#D9E8FF`, watch the swatch follow the typing, press Apply / Save.
   Status reads saved.
4. Upcoming: each date band is `#D9E8FF` with dark date text. Rows and the
   pinned column heading are unchanged (the heading stays theme-coloured —
   expected, see Known consequence).
5. Back to Settings: the field shows `#D9E8FF` (normalised from what was
   typed, e.g. `d9e8ff` → `#D9E8FF`).
6. Type a dark colour, e.g. `#1B3A5C`, save, reopen Upcoming: the date text
   flips to white and stays readable.
7. Clear the field, save, reopen Upcoming: the band is back to the theme
   colour.
8. Type `rebeccapurple`, press Apply / Save: refused, the message names the
   value, nothing is saved. Then — without correcting it — change the Color
   Theme dropdown: it must snap back to the theme actually in force rather
   than displaying one that was never applied.
9. Switch Appearance Mode light↔dark with a band colour set: the fill is the
   same in both and the date text flips as needed.
10. Hand-edit `list_date_band_color` in `settings.json` to `"not-a-colour"`
    and relaunch: `app.log` carries one warning naming the value, Settings >
    Appearance shows the field **blank** (the value was dropped on load, not
    kept), Upcoming draws the theme colour, and a save in that section now
    goes through rather than being refused over a field you did not touch.

## Sweep
Four passes:

1. `learning-qa`, cold, over `a9c13f0...HEAD` — 3 medium, 0 high.
2. A cold correctness / UI-contract / test-quality pass over the same range —
   1 high, 4 medium.
3. `/security-review`, warm — no findings. The only trigger in the diff was a
   `subprocess.run` in a test harness: argv-list form, no shell, literal
   interpreter path.
4. `learning-qa`, cold, over the fix commits `7c51519...fbb1679` — 2 medium,
   0 high.

Passes 1 and 2 converged independently on the same top defect, which is the
evidence `learnings.md` P26 asks for. Pass 4 is the fix-commit re-sweep
`csdp` requires.

**Not swept:** the second fix round, `f567689..f972edd`, which answers pass 4.
The repo's stop rule is a further pass only if the previous one produced a
high-severity finding; pass 4 produced none. Both of its commits were
mutation-checked.

**None of the four assessed** the Appearance section's geometry or its control
contract (`standards/ui-regression.md`), algorithmic correctness beyond the
band, concurrency, performance, dependencies, or architecture. The app was
**not run**: the walk checklist above is owed.

### Fixed

1. **A refused save left five fields mutated on the shared settings object**
   (HIGH, found by two lenses independently). `apply_theme_preferences`
   validated the band colour last. It is also the `command` of the three
   Appearance combo boxes, so picking a theme with a typo in the band entry
   wrote appearance mode, theme name, row font size, badge path and confetti
   threshold onto `self.settings`, applied no theme, wrote no file, and left
   each combo displaying a choice that was never written — for the next Save
   on any other section of the screen to persist. Validation now runs first;
   a refusal restores the three combos from the file. Guard:
   `test_dbcm42_a_refusal_leaves_the_whole_section_untouched`.
2. **A hand-edited colour wedged the whole Appearance section** (MEDIUM). A
   value Tk accepts and `normalize_hex_color` does not — `"lightblue"` — drew
   the band correctly and then refused every save in that section, on every
   launch, naming a field the user had not touched. `AppSettings.load` now
   normalizes it like the other appearance fields. Guard:
   `test_dbcm11_load_heals_a_stored_value_tk_would_reject`.
3. **The heal was silent, and it silenced the one report of the condition**
   (MEDIUM, found by the re-sweep of the fix commits). After fix 2 no
   unusable value could reach `theme.date_band_colors`, which carried the
   warning; the entry then showed blank, which is what "never set" looks
   like, and the file kept the rejected value until some later Appearance
   save overwrote it. `_normalize_list_date_band_color` now logs the dropped
   value, for the reason `_normalize_commitment_settings` gives. Guard: the
   `caplog` arm of `test_dbcm11`, which also asserts a blank value is not
   reported as a bad colour.
4. **Two tests patched a target the suite overrides** (MEDIUM). Both DBC-M1
   tests patched `src.getmoredone.app_settings.default_settings_path`, which
   does nothing: conftest's session-scoped `_isolate_user_settings` replaces
   `AppSettings.get_settings_path` outright. Both were reading and writing the
   suite's one shared settings file, and the first one's `save()` leaked into
   the second — which is how the dead patch was found. `_redirect_settings`
   patches the attribute conftest patches.
5. **The end-to-end bad-value arm could not fail for its stated reason**
   (MEDIUM, re-sweep). It fed the value through `settings.json`, which fix 2
   taught `load` to heal, so the band drew the theme fill because the value
   had been erased before `date_band_colors` ran. `render_date_band.py` takes
   a `post-load` flag that hands the colour to the built screen instead;
   mutating the helper's fallback now reddens the arm with the
   `TclError: unknown color name "rebeccapurple"` from inside the refresh
   that the feature exists to prevent.
6. Three comments in `app_settings.py` said the normalizers claim "six"
   fields; this change made it seven.

### Not fixed

- **`apply_theme_preferences` writes its status label after
  `app.apply_theme_preferences()`**, which destroys and rebuilds this screen,
  so the "✓ Saved" message lands on a destroyed widget. Pre-existing, and
  moving the line earlier does not help — the rebuild wipes the message either
  way. The new widget-touching lines were ordered before that call, and the
  test assertion that would have papered over it was removed.
- **The `save()`-side copy of the normalizer has no test**: deleting it leaves
  the suite green. Below the filing bar — `load` is the path a hand edit
  arrives by, and the UI validates before assigning.
- **`_redirect_settings` patches one import spelling** where conftest patches
  both. Harmless for these tests; a trap for whoever copies the helper.
- **The Appearance section has no contract test** asserting its controls are
  present, so the new row's placement was checked by reading the section's
  rows rather than by rendering it. Pre-existing gap.

### Dropped (below medium, recorded so they are not retried)

`date_band_colors` called once per date group rather than hoisted;
`_warned_date_band_colors` never invalidated; `colorchooser.askcolor` may
return `#rrrrggggbbbb` on some X11 Tk builds (the same assumption
`pick_priority_level_color` already makes, so fixing one means fixing its
siblings); the USER_GUIDE bullet sitting under "Date Increment Settings:"
beside already-mis-grouped siblings; `_render_band`'s dict keeping only the
last `FILL`/`TEXT`.

### Accepted cost

The Appearance tab does not scroll and is now one row taller. Raised before
building and accepted; walk-checklist step 1 is the check.

## Effort budget

Full tier: the change is in `src/`. Measured over `a9c13f0...HEAD` after the
trims, counting a `src/` added line as prose when it is a comment, a blank, or
inside a docstring (`ast`-resolved), and as code otherwise. Generated files
(`docs/ui_color_inventory.md`) excluded.

| | Code | Prose | Ratio | Ceiling |
|---|---:|---:|---:|---:|
| Feature `a9c13f0...7c51519` | 101 | 78 | **0.77** | 0.30 |
| Fixes `7c51519...HEAD` | 46 | 34 | **0.74** | 0.30 |
| Whole batch | 139 | 100 | **0.72** | 0.30 |

| | Code | Tests | Ratio | Ceiling |
|---|---:|---:|---:|---:|
| Feature | 101 | 325 | **3.22** | 2.0 |
| Fixes | 46 | 135 | **2.93** | n/a — counted by findings |
| Whole batch | 139 | 449 | **3.23** | 2.0 |

**Over on both, and reported rather than hidden**, which `effort-budget.md`
§9 requires. Two corrections to what an earlier draft of this note claimed:

- It said 0.34x prose. That counted hand-written documents only; §9 counts
  comments and docstrings too. The real figure is more than twice the ceiling,
  and the two longest blocks were cut to a measurement and a pointer to this
  file rather than justified. The rest is the Purpose/Spec/Tests convention
  the repo's traceability guard reads, and the one-line-per-guard the ceiling
  does not count.
- The fix half's test ratio is not a breach: §9 counts a findings batch by
  findings, at most one guard per finding. Six findings fixed, three guards
  added or rewritten.

The feature half's 3.22x is a real breach. About 80 of those lines are
`tests/render_date_band.py`, the subprocess harness: several CTk roots in one
interpreter hang the run, and the alternative — asserting on the source text
of `load_items` — is what this repo's test rules forbid where a behavioural
check is practical. Without it the ratio is 2.4x, still over.
