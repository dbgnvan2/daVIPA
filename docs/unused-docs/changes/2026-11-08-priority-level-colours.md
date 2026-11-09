# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: priority-level-colours (PLC-M1 to PLC-M5)

## Summary

Three **priority levels** — Any Critical; Any High, but no Critical; No high or
critical — each with a row tint the user sets in Settings → **Priority
Colours**. Any Critical defaults to green `#DCFCE7`, Any High to amber
`#FEF3C7`, the third level to no fill.

What this replaced: the rule `item.importance == 20 or item.urgency == 20` was
written out by hand in five list screens, tinted the row pale red
(`critical_tint`), had no tier between Critical and nothing, was not
configurable, and had no test of any kind.

- `priority_levels.py` (new) decides the level and the fill. Thresholds come
  from `PriorityFactors`, never from a literal 20 or 10, and each factor is
  compared against its own scale.
- `theme.priority_level_fill_colors()` (new) is the one place the shipped
  colours are written down. One value per level, no light/dark branch — a
  colour the user picks cannot have two variants, so the row's *text* colour is
  derived from the fill with `pick_text_color` instead.
- `AppSettings` gained three declared fields, `priority_level_color_<level>`.
  `""` means no fill and survives a reload; a malformed stored value is logged
  and falls back to the theme default rather than reaching Tk, which raises on
  a colour it does not know.
- `priority_levels.row_fill` is now the single fill decision for all five
  screens. Precedence is unchanged (segment → completed → level → none), and
  the places where a screen never used a branch are preserved, not fixed.
- The five screens now reload `AppSettings` in `refresh()`, so a saved colour
  shows on the next visit instead of after a relaunch.

Scope confirmed with the user before building: green applies to **Any Critical
only**, and the colour paints the **row background tint only** — the red `P:`
chip is deliberately left alone.

## Files changed

New:
- `src/getmoredone/priority_levels.py`
- `src/getmoredone/screens/settings_priority_colors.py`
- `tests/test_priority_level_colors.py`
- `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md`
- `docs/unused-docs/changes/2026-11-08-priority-level-colours.md`

Changed:
- `src/getmoredone/color_contrast.py` — `normalize_hex_color`, which returns
  rather than raises and expands `#ABC`
- `src/getmoredone/theme.py` — `priority_level_fill_colors()`
- `src/getmoredone/app_settings.py` — three colour fields
- `src/getmoredone/screens/settings.py` — the Priority Colours tab and the mixin
- `src/getmoredone/screens/today.py`, `upcoming.py`, `all_items.py`,
  `hierarchical.py`, `completed.py` — `row_fill`, settings reload
- `tests/source_asserts.py` — `local_assignments`, `count_calls`,
  `assigns_attribute_of`
- `tests/test_source_asserts.py` — cover the three new helpers, both directions
- `docs/USER_GUIDE.md`, `docs/DOCUMENTATION_INDEX.md`, `docs/spec_coverage.md`,
  `NOTES.md`, `BACKLOG.md`

No dependency change, so `requirements.txt` and `requirements-dev.txt` are
untouched.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_priority_level_colors.py tests/test_source_asserts.py -q`
- Result: PASS — 58 passed
- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_ui_presence.py tests/test_settings_save_refusal.py tests/test_plan_settings.py tests/test_time_block_colors.py tests/test_color_contrast.py tests/test_list_view_setting.py tests/test_defaults_regression.py -q`
- Result: PASS — 78 passed
- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_ci_contract.py tests/test_no_vacuous_tests.py tests/test_item_editor_no_context.py tests/test_live_data_guard.py -q`
- Result: PASS — 113 passed, 1 skipped (the CI-only display test). This batch
  includes the subprocess renders of the real list screens.
- Full suite: NOT RUN locally by policy; CI runs it on push.

Mutation proof, each restored from a verbatim copy:

| Mutation | Test | Result |
|---|---|---|
| `row_fill` ignores the item's level and always reads Any High | `test_plcm41_a_row_takes_its_level_colour` | red |
| a level fill returns `text_color=None` | `test_plcm44...`, `test_plcm46...` | red |
| `today.py` decides its own `bg_color` again, as it used to | `test_plcm47_no_screen_still_inlines_the_critical_rule` | red |

## Risks / Known gaps

- **Not verified on screen.** No agent put the app up. The checklist below is
  the human-review half of PLC-M4, and it is the one thing no test covers:
  whether a green Any Critical *reads* right.
- The Settings section is a **new tab**, not a third section on Appearance.
  Appearance's page is not scrollable and its two sections already run eight
  rows each, so a third risked sitting below the bottom of a short window. Easy
  to move if the tab is unwanted.
- `test_plcm36` and `test_plcm47`/`M4.8` are **source-level** guards (parsed,
  not greped, with exact counts). Proving them behaviourally needs a built
  CustomTkinter screen.

### On-screen checklist (for Dave, in the running app)

Create four items: one with Importance Critical, one with Urgency Critical and
Importance unset, one with Importance High and Urgency Medium, one Medium/Low.
Give a fifth a VSP segment colour. Then, in light **and** dark mode:

1. Today — the two critical items are green, the high item is amber, the
   medium/low item has no fill, the segment item keeps its segment colour.
2. Upcoming, All Items, Hierarchical, Completed — same tints.
3. Row text is readable on the green and the amber in **both** modes.
4. Settings → Priority Colours — three rows, three swatches; Pick Colour opens
   the chooser; a junk value is refused by name; clearing a field gives no
   fill; Restore Defaults refills the fields and does not save until Apply.
5. Save a colour, go to Today, confirm it took effect with no relaunch.
6. The red `P:` chip still marks critical items, beside a green row.
7. **Dark mode, Today:** on a green or amber row, the complete checkbox and the
   drag grip are visible against the fill, not washed out. This is the one the
   second cold pass found by measurement (about 2.6:1 before the fix) and it is
   the change most worth a human eye.
8. **Type into a colour field.** The swatch should repaint as you type, and a
   half-typed `#12` should leave it blank rather than showing the old colour.
9. **Pick Colour with junk in the field.** Type `qqq`, then press Pick Colour:
   the chooser should open on the level's default. Before the fix the button
   did nothing at all and said nothing.
10. **APE Week Assignment → Action Items panel.** It is a `TodayScreen`
    subclass, so it takes the tints too. Save a colour and confirm it appears
    there without a relaunch.

## Review passes (2026-11-08)

Two **cold** passes over a diff built from this change's five commits only, so
neither saw the narrative of how the code was written. Severities were assigned
before any fix was written. Both passes independently found the same blocker.

**High, fixed:**

1. `color_contrast.normalize_hex_color` validated with `int(text[1:], 16)`,
   which Python accepts far more loosely than Tk: `0x1234` → `#0X1234`,
   `+12345`, `# 12345`, `#-12345`, `#1_2345` and full-width Unicode digits all
   passed as "valid" at seven characters. Saved from the new Settings field,
   such a value was written to `settings.json` and then raised `TclError` on
   every row build in five screens *and* on the Settings tab's own swatch — so
   the tab the user would fix it from could not open, and the only way back was
   hand-editing the file. Now a `#[0-9A-F]{6}` match, in both that function and
   the pre-existing `_normalize_hex` beside it.

   Not the whole class, and the first version of this note said it was. Five
   more `int(x, 16)` / `len != 7` colour validators remain, in
   `screens/vps_segment_editor.py`, `vps_manager.py`, `screens/settings.py`,
   `screens/drag_schedule_support.py` and
   `screens/item_editor_weekly_tactic_dialog.py`. One of them is reachable to
   the same end: a segment colour typed as `# 12345` passes
   `validate_color`, is written to `segment_descriptions.color_hex`, is read
   back by `segment_color_utils._normalize_color` (which validates nothing at
   all) and raises `TclError` in the row build of three list screens. Fixing
   them means changing a save gate and a read path in the VSP segment
   subsystem, with its own tests, which is not what this change is — so they
   are recorded in full as PLC-A10 under the standing rule rather than swept
   in here.
2. `test_plcm3_the_section_builds_on_real_widgets` turned any `TclError` into
   `pytest.skip` — and `TclError` is exactly what a bad `grid` call, a rejected
   option or a colour Tk refuses raise, which is the test's whole reason to
   exist. It skipped on its own target class. Now only four display-specific
   stderr fragments skip; everything else fails with the captured stderr.

**Medium, fixed:** the vacuous clear-a-field assertion in `test_plcm32` (the
third level's default is already `""`, so it held whether or not the handler
wrote anything); PLC-M3.6's unanchored `"Priority Colours" in
inspect.getsource(...)`, which the comment above the `add` call satisfied on its
own — now an AST check over the strings `self.tabview.add` is given, pinning the
whole seven-tab set in order; dark-mode row controls, which kept theme colours
on a light level fill; `self.settings` left mutated after a refused write, where
the next successful save from any other Settings section would have persisted
colours the user was told were not saved; Pick Colour raising on unparseable
entry text; the swatch not following the field although the user guide said it
did; and a sixth surface the docs did not mention — APE Week Assignment's
Action Items panel, a `TodayScreen` subclass that overrides neither the row
builder nor `refresh` and so inherits the tint.

One of those fixes was wrong and was reverted in the same session: the panel
was read as *overriding* `refresh` and therefore never reloading, on a grep
that found `def refresh` at line 553 of `week_actions.py` — which belongs to
`WeekActionsScreen`, the container, not to the panel. The panel inherits
`TodayScreen.refresh` and was never stale. The reload added to the container
(which builds no rows of its own, and already sets `self.settings` in
`__init__` at `week_actions.py:220`, so the line was redundant) is gone, and
the test that
"covered" it passed only because `WeekTacticActionsPanel.refresh` *is*
`TodayScreen.refresh`. What replaced it asserts the inheritance itself, which
is the real reason the panel is covered. Only the documentation half of that
finding was ever real.

The reload guard also became a real guard: it now asserts the reload is
assigned to `self.settings` (both `today.py` and `upcoming.py` already contain a
`settings = AppSettings.load()` into a *local* elsewhere, which the old
call-only check would have accepted) and that it sits in the first three
statements of `refresh`, across the five screens that define one.

**Below medium:** seven findings in `BACKLOG.md` as PLC-A6 to PLC-A12 — the chip
and the fill now disagreeing about "critical", the save stub publishing by the
opposite mechanism from the real helper, the per-row warning on a bad stored
colour, the six Save handlers that still have no rollback,
`segment_color_utils._normalize_color` doing no validation at all,
`local_assignments` returning `None` for a bare annotation, and the seven-tab
strip that cannot scroll.

A third pass is owed under the repo's sweep budget, since this round produced
high-severity findings: cold, and in a different failure family.

## Next agent actions

- Run the checklist above and report what looks wrong.
- Decide the four adjacent issues logged in `BACKLOG.md` under
  **PLC adjacent issues** — in particular whether the `P:` chip should follow
  the Any Critical colour now that it is green.
- Decide whether Weekly Items, Project Boards and the VSP panels should take
  the level fill too. They do not tint by priority at all today, and this batch
  deliberately did not give them the fill.
