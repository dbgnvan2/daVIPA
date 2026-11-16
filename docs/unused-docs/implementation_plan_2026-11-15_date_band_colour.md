# Implementation plan — Day/Date band background colour (DBC, 2026-11-15)

## What and why

The bands that label a Day/Date in a listing of action items take the theme's
`surface_subtle` and cannot be changed. There is exactly one such band:
`UpcomingScreen.load_items`'s date group header. Today's "To Do" and
"Completed" bands label a *status section*, not a day, and are out of scope;
the Drag Schedule date boxes and the Plan week grid are a calendar, not a
listing, and already have their own colour logic.

Give the user one setting for that band's background.

## Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| DBC-M1 | `AppSettings.list_date_band_color: str = ""`, round-tripped by save/load. `""` means the theme's own `surface_subtle`, so an existing install looks unchanged. | `tests/test_date_band_colour.py::test_dbcm1_the_field_round_trips_and_defaults_to_the_theme` |
| DBC-M2 | `theme.date_band_colors(settings)` returns `(surface_subtle, None)` for `""` and for a value `normalize_hex_color` rejects, and `(colour, pick_text_color(colour))` otherwise. A rejected value warns once per value. | `::test_dbcm2_blank_is_the_theme_surface`, `::test_dbcm21_a_colour_carries_a_derived_text_colour`, `::test_dbcm22_an_unusable_colour_falls_back_to_the_theme` |
| DBC-M3 | The Upcoming date band is drawn from that helper, fill and label text colour together. | `::test_dbcm3_the_upcoming_band_is_drawn_from_the_helper` |
| DBC-M4 | Settings → Appearance has a `Day/Date band colour:` entry, a Pick Colour button and a live swatch; Apply/Save persists it, and a value that is not a colour is refused with a message rather than rewritten to a default. | `::test_dbcm4_a_colour_is_saved`, `::test_dbcm41_a_bad_colour_is_refused_and_not_written` |

## Decisions

- **One value, not one per appearance mode.** Same reason as
  `priority_level_fill_colors`: a colour chooser cannot return a light and a
  dark variant, and the contrast consequence is handled by deriving the label
  colour from the fill.
- **The label colour is derived** (`pick_text_color`, 4.5:1), which is what
  `AGENTS.md`'s *Semantic color rules* require of any band that takes a colour
  the theme did not pair text with.
- **Clearing the field restores the theme colour.** No separate "unset" state —
  the same semantics as `priority_level_color_*`.
- **A bad value is refused in the UI, not silently replaced**, following
  `save_priority_level_colors` rather than `save_date_increment_settings`.

## Known consequence

The pinned column-heading rows on the five list screens are also
`surface_subtle`. Once a band colour is set, the Upcoming band and those
headings no longer match. Accepted when this was approved.
