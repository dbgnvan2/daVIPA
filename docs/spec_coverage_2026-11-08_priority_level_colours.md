# Spec Coverage — Priority level colours (2026-11-08)

Plan: [`docs/implementation_plan_2026-11-08_priority_level_colours.md`](implementation_plan_2026-11-08_priority_level_colours.md)

All tests below are in `tests/test_priority_level_colors.py` unless another file
is named. No test in that file takes the `mapped_windows` fixture, so the
mapped-window count held by `tests/test_ci_contract.py` is unchanged.

| Spec ID | Description | Implementation | Test | Status |
|---|---|---|---|---|
| PLC-M1.1 | Critical in either factor, or one with the other missing, is `any_critical` | `src/getmoredone/priority_levels.py::priority_level` | `::test_plcm11_critical_in_either_factor_is_any_critical` | done |
| PLC-M1.2 | High in either factor with no Critical is `any_high` | `src/getmoredone/priority_levels.py::priority_level` | `::test_plcm12_high_without_critical_is_any_high` | done |
| PLC-M1.3 | Medium, Low, `0` and `None` are `no_high_or_critical` | `src/getmoredone/priority_levels.py::priority_level` | `::test_plcm13_medium_low_and_unset_are_no_high_or_critical` | done |
| PLC-M1.4 | (P7) A large priority *score* is not a critical *level* | `src/getmoredone/priority_levels.py` (module docstring states the split) | `::test_plcm14_a_big_score_is_not_a_critical_level` | done |
| PLC-M1.5 | The boundary is read off `PriorityFactors`, and `>=` keeps an off-scale value in the nearest level down | `src/getmoredone/priority_levels.py::_at_least` | `::test_plcm15_the_boundary_follows_priority_factors` (parametrised over the real scale), `::test_plcm15_a_value_off_the_scale_lands_in_the_nearest_level_down` | done |
| PLC-M1.6 | Three levels, labelled in the user's words; a non-numeric factor does not raise | `src/getmoredone/priority_levels.py::LEVEL_KEYS`, `LEVEL_LABELS` | `::test_plcm16_the_three_levels_are_labelled_as_asked`, `::test_plcm16_a_non_numeric_factor_does_not_raise` | done |
| PLC-M2.1 | One declared `AppSettings` field per level, exact set both ways | `src/getmoredone/app_settings.py` (three `priority_level_color_*` fields) | `::test_plcm21_every_level_has_a_settings_field` | done |
| PLC-M2.2 | The dataclass defaults equal the theme table | `src/getmoredone/theme.py::priority_level_fill_colors` | `::test_plcm22_settings_defaults_match_the_theme_table` | done |
| PLC-M2.3 | Any Critical green, Any High amber, third level no fill — and not the old `critical_tint` | `src/getmoredone/theme.py::priority_level_fill_colors` | `::test_plcm23_critical_defaults_to_green`, `::test_plcm23_the_default_is_not_the_old_critical_tint` | done |
| PLC-M2.4 | The three round-trip through `save`/`load` | `src/getmoredone/app_settings.py` | `::test_plcm24_level_colours_round_trip` | done |
| PLC-M2.5 | (P8) A malformed stored value is logged and falls back, never reaching Tk | `src/getmoredone/priority_levels.py::level_color`, `src/getmoredone/color_contrast.py::normalize_hex_color` | `::test_plcm25_a_malformed_stored_colour_falls_back_to_the_default` (parametrised over 7 bad values) | done |
| PLC-M2.6 | A cleared level stays cleared across a reload; a usable value is normalised on the way out | `src/getmoredone/priority_levels.py::level_color` | `::test_plcm26_no_fill_survives_a_reload`, `::test_plcm26_a_usable_value_is_normalised_on_the_way_out` | done |
| PLC-M3.1 | One row per level, in order, with label and effective colour | `src/getmoredone/priority_levels.py::priority_color_rows` | `::test_plcm31_one_row_per_level_in_order` | done |
| PLC-M3.2 | Saved colours are written and published to the running app | `src/getmoredone/screens/settings_priority_colors.py::save_priority_level_colors` | `::test_plcm32_saved_colours_reach_the_running_app` | done |
| PLC-M3.3 | A refused write is not reported as saved and is not published | `src/getmoredone/screens/settings_priority_colors.py::save_priority_level_colors` | `::test_plcm33_a_refused_write_is_not_reported_as_saved` | done |
| PLC-M3.4 | Values normalised; a bad one refused by level name with nothing written | `src/getmoredone/screens/settings_priority_colors.py::save_priority_level_colors` | `::test_plcm34_entry_values_are_normalised_and_bad_ones_refused` | done |
| PLC-M3.5 | Restore Defaults refills the fields and does not save | `src/getmoredone/screens/settings_priority_colors.py::restore_priority_level_colors` | `::test_plcm35_restore_defaults_writes_the_theme_table` | done |
| PLC-M3.6 | The tab is reachable, by that name | `src/getmoredone/screens/settings.py::create_tabs` | `::test_plcm36_create_tabs_adds_the_priority_colours_tab` (AST) | done |
| PLC-M4.1 | A row takes its level's colour, from settings rather than a constant | `src/getmoredone/priority_levels.py::row_fill` | `::test_plcm41_a_row_takes_its_level_colour` — **mutation-proved** | done |
| PLC-M4.2 | Segment and completed still win, in that order | `src/getmoredone/priority_levels.py::row_fill` | `::test_plcm42_segment_and_completed_still_win`, `::test_plcm4_a_completed_row_in_all_items_still_uses_the_status_check` | done |
| PLC-M4.3 | No fill is `None`, not `""` | `src/getmoredone/priority_levels.py::row_fill` | `::test_plcm43_an_unset_level_means_no_fill` | done |
| PLC-M4.4 | A level fill carries `pick_text_color` of itself, clearing 4.5:1 | `src/getmoredone/priority_levels.py::row_fill` | `::test_plcm44_level_fill_text_clears_the_contrast_bar` — **mutation-proved** | done |
| PLC-M4.5 | Segment, completed and no fill leave the screen's `row_text` alone | `src/getmoredone/priority_levels.py::RowFill` | `::test_plcm45_a_non_priority_fill_leaves_row_text_alone` | done |
| PLC-M4.6 | The defaults are legible in both modes, and the table is identical across them | `src/getmoredone/theme.py::priority_level_fill_colors` | `::test_plcm46_default_level_colours_are_legible_in_both_themes` | done |
| PLC-M4.7 | No row builder inlines the fill rule: `bg_color` assigned exactly once, from `fill.fill`, in all five | the five screens' row builders | `::test_plcm47_no_screen_still_inlines_the_critical_rule` (AST, exact count) — **mutation-proved** | done |
| PLC-M4.8 | Exactly one `row_fill` call in each of the five, five in total; and all five reload settings in `refresh` | the five screens | `::test_plcm48_every_list_screen_row_builder_calls_the_helper`, `::test_plcm48_the_five_screens_reload_settings_before_building_rows` | done |
| PLC-M5.1 | USER_GUIDE documents the tab, the three levels and no-fill | `docs/USER_GUIDE.md` (Priority Colours) | — (documentation) | done |
| PLC-M5.2 | The plan is listed in the documentation index | `docs/DOCUMENTATION_INDEX.md` | — (documentation) | done |
| PLC-M5.3 | Handoff note written | `docs/changes/2026-11-08-priority-level-colours.md` | — (documentation) | done |
| PLC-M5.4 | Spec coverage generated | this file | — (documentation) | done |
| PLC-M5.5 | NOTES and BACKLOG updated | `NOTES.md`, `BACKLOG.md` | — (documentation) | done |

## Supporting coverage

The three new AST helpers PLC-M3.6/M4.7/M4.8 rely on are themselves tested in
both directions, so none of those guards can be a no-op:

| Helper | Test |
|---|---|
| `local_assignments` | `tests/test_source_asserts.py::test_local_assignments_counts_each_write_and_ignores_prose`, `::test_local_assignments_sees_every_branch`, `::test_local_assignments_says_no_to_a_name_never_assigned` |
| `count_calls` | `tests/test_source_asserts.py::test_count_calls_counts_calls_not_mentions` |
| `assigns_attribute_of` | `tests/test_source_asserts.py::test_assigns_attribute_of_rejects_a_different_owner_or_attribute` |

## Not code-testable

| Criterion | Why | Human review |
|---|---|---|
| The green *reads* correctly on screen — against the dark theme, beside a segment-coloured row, and next to the still-red `P:` chip | Appearance is not assertable; the contrast bar is held by PLC-M4.4/M4.6, but legible is not the same as right | The on-screen checklist in `docs/changes/2026-11-08-priority-level-colours.md`, six steps across the five screens in both modes |
| That the Priority Colours tab fits on a short window | Needs the app on a real display at a real size | Same checklist, step 4 |
