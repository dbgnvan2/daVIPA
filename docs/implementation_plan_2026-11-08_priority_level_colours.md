# Priority level colours — PLC-M1 to PLC-M5

Status: **approved and implemented** (approved 2026-11-08, built the same day).
Per-criterion status in `docs/spec_coverage_2026-11-08_priority_level_colours.md`;
handoff note in `docs/changes/2026-11-08-priority-level-colours.md`. The five
adjacent issues below are filed as PLC-A1 to PLC-A5 in `BACKLOG.md`, and the
open question at the foot is still open.
Date: 2026-11-08
Supersedes nothing. Touches the row-fill rule introduced ad hoc across the five
list screens; does not touch `priority_band_colors` / `priority_stripe_colors` /
`priority_fill_colors`, which are a different thing (see "Two meanings of
priority" below).

Asked for: *"Put colour settings in Settings for Priority Levels. Change the
default to Green for the Critical levels. The Levels are Any Critical, Any High
but no Critical, no high or critical."*

Confirmed with the user before planning:

- Green default applies to **Any Critical only**. Any High gets amber; the
  third level gets no fill, as now.
- The colour paints the **row background tint only**. The red `P:` priority
  chip is deliberately left alone.

---

## What exists today

### Two meanings of "priority" in this codebase

Not to be conflated — the plan touches only the first.

1. **Priority *levels*** (this plan). A rule on the two *factors*:
   `item.importance == 20 or item.urgency == 20`. It decides a **row
   background tint**, and it is written out by hand in five screens:

   | Screen | Line | Fill when the rule holds |
   |---|---|---|
   | `screens/today.py` | 476, 483 | `palette["critical_tint"]` |
   | `screens/upcoming.py` | 286, 290 | `palette["critical_tint"]` |
   | `screens/all_items.py` | 241, 242 | `palette["critical_tint"]` |
   | `screens/hierarchical.py` | 224, 225 | `palette["critical_tint"]` |
   | `screens/completed.py` | 195, 197 | `palette["critical_tint"]` |

   `critical_tint` is `#FDECEC` light / `#3A2328` dark (`theme.py:129`).

2. **Priority *bands*** (not this plan). Thresholds on `priority_score`, the
   *product* of the four factors (`time_block_layout.PRIORITY_BANDS`), five
   names `critical/high/medium/low/unscored`, used by the Plan screen's stripes
   and chip fills. These stay exactly as they are. A band named "critical" is
   not the same thing as the level named "Any Critical", and the plan keeps the
   two sets of names and colours apart rather than merging them.

### The gaps

- **No "high" tier.** `PriorityFactors.IMPORTANCE` / `.URGENCY` are
  `Critical: 20, High: 10, Medium: 5, Low: 1` (`models.py:314-326`). The row
  rule only ever looks for 20, so "Any High, but no Critical" does not exist
  anywhere in the app.
- **Nothing is configurable.** There is no Settings control for any of it, and
  the three colours are not centralised — `critical_tint` is a theme palette
  entry used for this and nothing else.
- **The rule is duplicated five times.** Five copies of
  `importance == 20 or urgency == 20`, each with its own precedence chain
  around it. Adding a second tier by hand would make that ten.
- **Untested.** `grep critical_tint tests/` returns nothing. The row tint has
  no test at all today.

---

## PLC-M1 — the three levels, named and decided in one place

New module `src/getmoredone/priority_levels.py`. Classification only; no
colours, no widgets, no settings access.

```
LEVEL_ANY_CRITICAL      = "any_critical"              # "Any Critical"
LEVEL_ANY_HIGH          = "any_high"                  # "Any High, but no Critical"
LEVEL_NO_HIGH_OR_CRITICAL = "no_high_or_critical"     # "No high or critical"

LEVEL_KEYS   : tuple          # the three, highest first
LEVEL_LABELS : dict[str, str] # the user's three names, verbatim

def priority_level(importance: Optional[int], urgency: Optional[int]) -> str
```

Decided by `max(importance or 0, urgency or 0)` against thresholds read from
`PriorityFactors`, **not** from literal `20` / `10` — rule 8, and the
`PRIORITY_BANDS` comment in `time_block_layout.py` sets the precedent that the
arithmetic lives away from the colours so that a theme change cannot move an
item between levels. `>=` and not `==`, so a hand-edited database holding a
value off the scale lands in the nearest level down rather than falling through
to "no high or critical".

A missing factor is not an excuse: `importance=None, urgency=20` is
**Any Critical**. This mirrors the existing `or` and is the opposite of the
band rule, where a missing factor means `unscored` — the difference is
deliberate and documented in the module docstring, because the two are easy to
confuse.

**Acceptance**
- PLC-M1.1 Critical in either factor, or both, gives `any_critical`, including
  when the other factor is `None`.
  Test: `tests/test_priority_level_colors.py::test_plcm11_critical_in_either_factor_is_any_critical`
- PLC-M1.2 High in either factor with no Critical gives `any_high`.
  Test: `::test_plcm12_high_without_critical_is_any_high`
- PLC-M1.3 Medium, Low, `0` and `None` in both factors give
  `no_high_or_critical`.
  Test: `::test_plcm13_medium_low_and_unset_are_no_high_or_critical`
- PLC-M1.4 **(P7, adversarial)** An item that scores high on the *other* two
  factors — `size=XL, value=XL`, so `priority_score` is large and its *band* is
  `critical` — is still `no_high_or_critical` when importance and urgency are
  Medium. A big score must not be mistaken for a level.
  Test: `::test_plcm14_a_big_score_is_not_a_critical_level`
- PLC-M1.5 The boundary follows `PriorityFactors`: parametrised over
  `IMPORTANCE.items()`, each named value maps to the expected level, so
  renumbering the scale moves the boundary with it.
  Test: `::test_plcm15_the_boundary_follows_priority_factors`
- PLC-M1.6 The three labels are the user's three names verbatim, and
  `LEVEL_KEYS` holds exactly three keys.
  Test: `::test_plcm16_the_three_levels_are_labelled_as_asked`

## PLC-M2 — one colour per level, stored in settings

Three new `AppSettings` fields, one per level, named
`priority_level_color_<key>`:

```
priority_level_color_any_critical: str = "#DCFCE7"   # green
priority_level_color_any_high: str = "#FEF3C7"       # amber
priority_level_color_no_high_or_critical: str = ""   # no fill
```

Three declared scalar fields rather than one `dict` field, matching
`drag_schedule_date_text_color`: the set of levels is closed and named, and the
UPD-M4 comment in `app_settings.py` records what an *undeclared* key costs — it
is set, used for the session, and silently dropped at the next launch. Three
declared names cannot do that, and PLC-M2.1 holds the mapping.

`""` means **no fill** — the row keeps the theme's own background. It is not a
sentinel for "unset"; there is no such state, and "Restore defaults" (PLC-M3.4)
is how a user gets a default back.

**One hex per level, not one per theme.** `critical_tint` has separate light
and dark values; a user-chosen colour cannot. The consequence is accepted and
handled, not ignored: a pale green row in the dark theme needs dark text, so
PLC-M4.4 derives the row's text colour from the fill with `pick_text_color`
instead of leaving the theme's `row_text` on it.

The defaults themselves live in `theme.py` as
`priority_level_fill_colors() -> dict[str, str]`, which is where the project
rule puts a colour ("to add a semantic color, centralize it in `theme.py`").
The dataclass has to hold literals, so PLC-M2.2 asserts the two agree and the
duplicate cannot drift.

`priority_levels.level_color(settings, level) -> str` reads the field, validates
it, and falls back to the theme table.

**Acceptance**
- PLC-M2.1 Every key in `LEVEL_KEYS` has a declared `AppSettings` field named
  `priority_level_color_<key>`, and there are no `priority_level_color_*`
  fields without a level (exact count, both directions).
  Test: `::test_plcm21_every_level_has_a_settings_field`
- PLC-M2.2 The three dataclass defaults equal `theme.priority_level_fill_colors()`.
  Test: `::test_plcm22_settings_defaults_match_the_theme_table`
- PLC-M2.3 Any Critical defaults to `#DCFCE7`, Any High to `#FEF3C7`, the third
  level to `""`.
  Test: `::test_plcm23_critical_defaults_to_green`
- PLC-M2.4 The three round-trip through `save()` and `load()` against a
  `tmp_path` settings file.
  Test: `::test_plcm24_level_colours_round_trip`
- PLC-M2.5 **(P8, dirty state)** A settings file left by an earlier run holding
  `"red"`, `"#GGG"`, `"#12345"` or a non-string is ignored per-level, the theme
  default is used, and the bad value is logged — never handed to Tk, which
  raises on a bad colour and would take the whole list screen down.
  Test: `::test_plcm25_a_malformed_stored_colour_falls_back_to_the_default`
- PLC-M2.6 A level whose stored value is `""` yields `""` and is **not**
  replaced by the theme default — "no fill" survives a reload.
  Test: `::test_plcm26_no_fill_survives_a_reload`

## PLC-M3 — the Settings control

New mixin module `src/getmoredone/screens/settings_priority_colors.py`
(`SettingsPriorityColorsMixin`), following `settings_integrations.py`.
`settings.py` is already 1214 lines, past the maintainability standard's
700-line mark, so the section does not go in it.

A **new tab**, "Priority Colours", added by `create_tabs` between "Appearance"
and "Future Dates". Not a third section on the Appearance tab: that tab's frame
is a plain `CTkTabview` page, not scrollable, and its two existing sections
already run eight rows each — a third section would risk pushing itself off the
bottom on a short window, and I cannot confirm that without putting the app on
screen. A tab is visible at any window height and risks nothing in the two
sections already there. Say so if you would rather have it under Appearance.

One row per level, driven by `LEVEL_KEYS` so a level cannot be left out:

```
Any Critical                 [#DCFCE7] [Pick Colour] [swatch]
Any High, but no Critical    [#FEF3C7] [Pick Colour] [swatch]
No high or critical          [       ] [Pick Colour] [swatch]

[Apply / Save]  [Restore Defaults]        ✓ Saved / error
```

`colorchooser.askcolor`, the entry + "Pick Color" pattern already used by
`pick_drag_schedule_text_color`. The swatch is a small `CTkFrame` filled with
the current value — a chip, not a row fill, so it stays inside the theme rule.
Save goes through the existing `_write_settings` / `_hand_settings_to_app`
guards, and, as in `apply_theme_preferences`, publishes to the app only after
the write is known to have happened.

The row data comes from a pure helper so the content is testable without a Tk
root: `priority_color_rows(settings) -> list[(key, label, colour)]`.

**Acceptance**
- PLC-M3.1 `priority_color_rows` returns one row per level, in `LEVEL_KEYS`
  order, each carrying the user-facing label and the effective colour.
  Test: `::test_plcm31_one_row_per_level_in_order`
- PLC-M3.2 `save_priority_level_colors` writes all three entry values to
  settings and hands the saved object to the app.
  Test: `::test_plcm32_saved_colours_reach_the_running_app`
- PLC-M3.3 A refused write reports the error on the status label and does
  **not** publish to the app (the `_write_settings` contract).
  Test: `::test_plcm33_a_refused_write_is_not_reported_as_saved`
- PLC-M3.4 Normalisation: blank stores `""`; `DCFCE7` gains its `#`; a
  three-digit `#ABC` is expanded; a value that is still not `#RRGGBB` is
  **refused with a message naming the level**, and no value is written —
  the entry is not silently replaced behind the user's back.
  Test: `::test_plcm34_entry_values_are_normalised_and_bad_ones_refused`
- PLC-M3.5 "Restore Defaults" puts `theme.priority_level_fill_colors()` back
  into the three entry variables.
  Test: `::test_plcm35_restore_defaults_writes_the_theme_table`
- PLC-M3.6 The tab is reachable: `create_tabs` adds a tab and calls
  `create_priority_colors_section` (AST, via `tests/source_asserts.py`).
  Test: `::test_plcm36_create_tabs_adds_the_priority_colours_tab`

Tests call the mixin's methods unbound against a stub `self`, as
`tests/test_settings_save_refusal.py` already does — no Tk root, so the
`mapped_windows` count stays at 22 and `test_ci_contract.py` keeps passing.

## PLC-M4 — the five list screens draw it

One shared helper in `priority_levels.py`, replacing the five inline copies:

```
def row_fill(settings, palette, *, item, is_completed, segment_color) -> RowFill
#  -> RowFill(fill: Optional[str], text_color: Optional[str])
```

Precedence is the one the screens already have, unchanged: segment colour →
completed → priority level → no fill. `hierarchical.py` passes
`segment_color=None` because today it applies the segment colour as an accent
only and never as a fill; that difference is preserved here rather than fixed
(see "Adjacent issues").

`text_color` is `None` for every case except a priority-level fill, meaning
"leave the screen's `row_text` alone". Only the new case gets
`pick_text_color(fill)`. Segment and completed fills keep exactly the text
colour they have today — their contrast is a real problem, but it is a
pre-existing one and fixing it here would be a silent sweep.

**Acceptance**
- PLC-M4.1 A `Critical` item with no segment colour and not completed takes
  `priority_level_color_any_critical`; a `High` item takes the Any High colour.
  Test: `::test_plcm41_a_row_takes_its_level_colour`
- PLC-M4.2 A segment colour still wins over the level colour, and a completed
  row still takes `success_tint`.
  Test: `::test_plcm42_segment_and_completed_still_win`
- PLC-M4.3 A level colour of `""` gives `fill=None` — no fill — not the empty
  string, which Tk rejects.
  Test: `::test_plcm43_an_unset_level_means_no_fill`
- PLC-M4.4 A priority-level fill carries `pick_text_color` of itself, and that
  pair clears 4.5:1.
  Test: `::test_plcm44_level_fill_text_clears_the_contrast_bar`
- PLC-M4.5 A segment fill, a completed fill and no fill all carry
  `text_color=None`, so the screens' own `row_text` is untouched.
  Test: `::test_plcm45_a_non_priority_fill_leaves_row_text_alone`
- PLC-M4.6 Both default colours clear 4.5:1 against their picked text in the
  light **and** dark appearance modes.
  Test: `::test_plcm46_default_level_colours_are_legible_in_both_themes`
- PLC-M4.7 No row builder in the five screens still decides a fill from an
  inline importance/urgency comparison — AST over the five functions, asserted
  as **exactly 0**, not a floor.
  Test: `::test_plcm47_no_screen_still_inlines_the_critical_rule`
- PLC-M4.8 Each of the five row builders calls `row_fill` — AST, asserted as
  **exactly 5**, so a screen cannot be dropped from the set silently.
  Test: `::test_plcm48_every_list_screen_row_builder_calls_the_helper`

Mutation proof (repo test rule) will be run for PLC-M4.1, PLC-M4.4 and
PLC-M4.7, restoring the verbatim original each time.

### Not code-testable

That the green *reads* correctly on screen — against the dark theme, beside a
segment-coloured row, and with the still-red `P:` chip next to it — cannot be
asserted. **Proposed human review:** an on-screen checklist in the handoff note
(Today / Upcoming / All Items / Hierarchical / Completed × light and dark,
one critical row, one high row, one of neither, one segment-coloured), for you
to walk in the running app. No agent will put the app on screen.

## PLC-M5 — documents

- PLC-M5.1 `docs/USER_GUIDE.md` — the new tab, the three levels and what each
  one means, and that a blank value means no fill.
- PLC-M5.2 `docs/DOCUMENTATION_INDEX.md` — lists this plan and the handoff note.
- PLC-M5.3 `docs/changes/2026-11-08-priority-level-colours.md` — handoff note
  from `.agents/templates/handoff-note.md`, carrying the on-screen checklist.
- PLC-M5.4 `docs/spec_coverage.md` — the PLC criteria with their test names.
- PLC-M5.5 `NOTES.md` — the change; `BACKLOG.md` — the adjacent issues below.

No dependency change, so `requirements.txt` / `requirements-dev.txt` are
untouched; the docs gate treats both as dependency files and will not ask.

---

## Implementation order

1. **PLC-M1** `priority_levels.py` classification + its tests. No dependants
   yet, so it can be proven before anything consumes it.
2. **PLC-M2** `theme.priority_level_fill_colors()`, the three `AppSettings`
   fields, `level_color`, + tests. Depends on M1 for the keys.
3. **PLC-M4** `row_fill` + the five screen edits + tests. Depends on M1 and M2.
   Before M3 on purpose: the colours should be visible from the defaults before
   a control to change them exists, so the control is testable against
   something real.
4. **PLC-M3** the Settings mixin, the new tab, + tests. Depends on M2.
5. **PLC-M5** documents, and the status report.

Test commits separate from `src/` commits, per the repo rule.

---

## Adjacent issues found, not fixed

Per global rule 10 — flagged, not swept. To `BACKLOG.md` unless you say otherwise.

1. **Segment-coloured rows get theme text, not contrast-picked text.** All five
   screens set `row_text = palette["row_text"]` and then fill the row with a
   DB segment colour (`today.py:477-479`). A pale segment colour in the dark
   theme gets near-white text on it. Same defect class as PLC-M4.4, which fixes
   it only for the new priority fill.
2. **`hierarchical.py` ignores its own segment colour for the fill.** It
   resolves `segment_color`, applies it as an accent, and then — unlike the
   other four screens — never considers it for the row background
   (`hierarchical.py:215-227`). Either the accent-only treatment is right and
   the other four are wrong, or the reverse; nothing records which.
3. **The `P:` chip hard-codes `palette["danger"]` for critical in five
   screens.** Out of scope by your choice, but once Any Critical is green the
   row and its chip disagree. Worth a decision later.
4. **`settings.py` is 1214 lines**, well past the 700-line refactor mark. This
   change adds nothing to it beyond a mixin import and a tab, but the six
   existing sections remain.
5. **`docs/DOCUMENTATION_INDEX.md` is unenforced and stale** — it ends "All
   documentation up to date as of 2026-01-24" and no test checks that every
   document is listed, which global rule 13 asks for.

---

## Open question

The five screens in the table are the ones that tint a row by priority today.
**Weekly Items, Project Boards and the VSP panels do not**, and this plan does
not give them the fill. Say the word if the levels should reach those too; it is
a wider change (their row builders have their own precedence chains) and I did
not want to assume it.
