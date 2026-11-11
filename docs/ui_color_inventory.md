# UI Color Inventory

Generated via deterministic `rg` scans from repo root.

## Scan Commands
```bash
rg -n "fg_color=|hover_color=|text_color=|border_color=|button_color=|progress_color=|selected_color=|corner_radius=|highlight_color=" .
rg -n "#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b" .
rg -n -i "\"(darkgreen|green|red|orange|blue|teal|cyan|yellow|white|black|gray|grey)\"|\'(darkgreen|green|red|orange|blue|teal|cyan|yellow|white|black|gray|grey)\'" .
rg -n "set_default_color_theme\(|set_appearance_mode\(" .
```

## 1) Summary Counts By Type

- Hex colors (match count): **2282**
- Named colors (match count): **137**
- Tuple colors / appearance tuples (match count): **5**
- CustomTkinter theme API usage (`set_default_color_theme`/`set_appearance_mode`) line count: **25**
- Widget explicit overrides (line count): **569**

Widget override property breakdown:

| Property | Count |
|---|---:|
| `border_color` | 18 |
| `button_color` | 4 |
| `corner_radius` | 63 |
| `fg_color` | 271 |
| `highlight_color` | 2 |
| `hover_color` | 17 |
| `progress_color` | 2 |
| `selected_color` | 2 |
| `text_color` | 238 |

AppSettings persisted color/theme fields:

```text
126:    # Drag Schedule date box text color (hex)
127:    drag_schedule_date_text_color: str = "#FFFFFF"
310:                settings.appearance_mode = cls._normalize_appearance_mode(
311:                    settings.appearance_mode)
312:                settings.theme_name = cls._normalize_theme_name(
313:                    settings.theme_name)
445:        self.appearance_mode = self._normalize_appearance_mode(
446:            self.appearance_mode)
447:        self.theme_name = self._normalize_theme_name(self.theme_name)
55:    appearance_mode: str = "dark"  # system | dark | light
56:    theme_name: str = "apple_grey"
626:        _normalize_theme_name defers its import for the same reason.
696:    def _normalize_appearance_mode(value: Optional[str]) -> str:
69:    # tests/test_priority_level_colors.py::test_plcm21_every_level_has_a_settings_field
702:    def _normalize_theme_name(value: Optional[str]) -> str:
703:        """Coerce a persisted theme name, using theme.py's list and no other.
705:        This held a SECOND hardcoded copy of the theme names. Adding a theme to
708:        load, because the new name was not in the copy. Picking a new theme
711:        Imported inside the function: theme.py pulls in customtkinter, and
715:        from .theme import normalize_theme_name
717:        return normalize_theme_name(value)
73:    # "" means no fill — the row keeps the theme's own background, which is
78:    # The defaults are duplicated from theme.priority_level_fill_colors(),
82:    priority_level_color_any_critical: str = "#DCFCE7"
83:    priority_level_color_any_high: str = "#FEF3C7"
84:    priority_level_color_no_high_or_critical: str = ""
```

Hex top values:

| Color | Count |
|---|---:|
| `#dce4ee` | 122 |
| `#ffffff` | 111 |
| `#979da2` | 104 |
| `#000000` | 79 |
| `#565b5e` | 68 |
| `#3e454a` | 54 |
| `#4a4d50` | 54 |
| `#939ba2` | 54 |
| `#949a9f` | 54 |
| `#abc` | 45 |
| `#2e1c8f` | 40 |
| `#1d1d1f` | 35 |
| `#343638` | 32 |
| `#6e6e73` | 32 |
| `#aabbcc` | 32 |
| `#f9f9fa` | 32 |
| `#334155` | 30 |
| `#86868b` | 29 |
| `#111111` | 25 |
| `#dcfce7` | 25 |

Named top values:

| Color | Count |
|---|---:|
| `gray` | 54 |
| `white` | 24 |
| `green` | 18 |
| `red` | 15 |
| `blue` | 7 |
| `black` | 6 |
| `orange` | 6 |
| `grey` | 3 |
| `yellow` | 3 |
| `cyan` | 1 |

## 2) Complete Occurrence Table (Grouped by Color Value, then File)

Each row is from grep output and includes `file:line` and a short snippet.

### `#000`

| File:Line | Snippet |
|---|---|
| `tests/test_weekly_tactic_parent.py:738` | `palette={"primary": "#000", "on_primary": "#fff", "body_text": "#111"},` |

### `#000000`

| File:Line | Snippet |
|---|---|
| `docs/spec_2026-11-07_ape_week_actions.md:583` | `is not `"#000000"`, which could never fail because the theme value it compares` |
| `docs/unused-docs/backlog_archive_2026-11-09.md:1891` | `deleted line and a corrected fake: a `!= "#000000"` assertion that could never` |
| `docs/unused-docs/changes/2026-03-02-wcag-auto-text-contrast.md:12` | `- `pick_text_color(bg_hex, light="#FFFFFF", dark="#000000")`` |
| `docs/unused-docs/changes/2026-11-07-ape-week-actions.md:161` | `written the same round were corrected rather than filed (a `!= "#000000"`` |
| `src/getmoredone/color_contrast.py:161` | `dark: str = "#000000",` |
| `src/getmoredone/color_contrast.py:168` | `def pick_text_color(bg_hex: str, light: str = "#FFFFFF", dark: str = "#000000") -> str:` |
| `src/getmoredone/color_contrast.py:173` | `return "#000000"` |
| `tests/build_priority_colors_section.py:101` | `host.priority_level_color_vars[LEVEL_KEYS[0]].set("#000000")` |
| `tests/test_color_contrast.py:13` | `assert pick_text_color("#FFFF00") == "#000000"  # bright yellow -> black` |
| `tests/test_color_contrast.py:19` | `assert math.isclose(contrast_ratio("#000000", "#FFFFFF"), 21.0, rel_tol=0.0, abs_tol=0.01)` |
| `tests/test_color_contrast.py:44` | `assert math.isclose(relative_luminance("#000000"), 0.0, rel_tol=0.0, abs_tol=1e-9)` |
| `tests/test_drag_schedule_support.py:30` | `assert interpolate_hex_color("#000000", "#FFFFFF", 0.5) == "#808080"` |
| `tests/test_priority_level_colors.py:568` | `settings.priority_level_color_any_critical = "#000000"` |
| `tests/test_priority_level_colors.py:569` | `stub = _StubSettingsScreen(settings, {LEVEL_ANY_CRITICAL: "#000000"})` |
| `tests/test_priority_level_colors.py:581` | `assert settings.priority_level_color_any_critical == "#000000"` |
| `tests/test_priority_level_colors.py:696` | `for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1158` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#000000", "#FFFFFF"):` |
| `tests/test_priority_level_colors.py:1172` | ```return RowFill(segment_color, "#000000", ...)`` passes the pale half and` |
| `tests/test_priority_level_colors.py:1200` | ```pick_text_color`` answers ``#000000`` for anything it cannot parse, and` |
| `tests/test_unified_panel_design.py:901` | `theme's own value. A second line asserting the colour is not `"#000000"`` |
| `tests/test_vps_integration.py:1484` | `color_hex="#000000",` |
| `tests/test_vps_integration.py:1610` | `name="Third", description="", color_hex="#000000", order_index=3` |
| `tests/test_vps_integration.py:1613` | `name="First", description="", color_hex="#000000", order_index=1` |
| `tests/test_vps_integration.py:1616` | `name="Second", description="", color_hex="#000000", order_index=2` |
| `tests/test_vps_segments.py:173` | `@pytest.mark.parametrize("value", ["#000000", "#ffffff", "#AABBCC", "#1a2b3c"])` |
| `themes/apple_grey.json:5` | `"#000000"` |
| `themes/apple_grey.json:11` | `"#000000"` |
| `themes/apple_grey.json:38` | `"#000000",` |
| `themes/apple_grey.json:94` | `"#000000",` |
| `themes/apple_grey.json:152` | `"#000000",` |
| `themes/apple_grey.json:198` | `"#000000",` |
| `themes/apple_grey.json:209` | `"#000000",` |
| `themes/apple_grey.json:213` | `"#000000",` |
| `themes/apple_grey.json:278` | `"#000000",` |
| `themes/black_white.json:5` | `"#000000"` |
| `themes/black_white.json:11` | `"#000000"` |
| `themes/black_white.json:19` | `"#000000"` |
| `themes/black_white.json:23` | `"#000000"` |
| `themes/black_white.json:38` | `"#000000",` |
| `themes/black_white.json:58` | `"#000000",` |
| `themes/black_white.json:74` | `"#000000",` |
| `themes/black_white.json:94` | `"#000000",` |
| `themes/black_white.json:152` | `"#000000",` |
| `themes/black_white.json:198` | `"#000000",` |
| `themes/black_white.json:209` | `"#000000",` |
| `themes/black_white.json:213` | `"#000000",` |
| `themes/black_white.json:278` | `"#000000",` |
| `tools/generate_ctk_themes.py:53` | `APPLE_GREY_HOVER = ["#000000", "#F5F5F7"]` |
| `tools/generate_ctk_themes.py:57` | `BLACK_WHITE_HOVER = ["#000000", "#FFFFFF"]` |
| `tools/generate_ctk_themes.py:61` | `("CTk", "fg_color"): ["#F5F5F7", "#000000"],` |
| `tools/generate_ctk_themes.py:62` | `("CTkToplevel", "fg_color"): ["#F5F5F7", "#000000"],` |
| `tools/generate_ctk_themes.py:74` | `("CTk", "fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:75` | `("CTkToplevel", "fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:76` | `("CTkFrame", "fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:77` | `("CTkFrame", "top_fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:79` | `("CTkLabel", "text_color"): ["#000000", "#FFFFFF"],` |
| `tools/generate_ctk_themes.py:82` | `("CTkEntry", "text_color"): ["#000000", "#FFFFFF"],` |

### `#0000ff`

| File:Line | Snippet |
|---|---|
| `tests/test_color_contrast.py:22` | `assert math.isclose(contrast_ratio("#0000FF", "#FFFFFF"), 8.59, rel_tol=0.0, abs_tol=0.03)` |
| `tests/test_vps_data_integrity.py:250` | `color_hex="#0000FF",` |
| `tests/test_vps_integration.py:1507` | `color_hex="#0000FF",` |
| `tests/test_vps_integration.py:1634` | `valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#ABCDEF", "#123456"]` |

### `#000365`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:63` | `800: "#40299C", 900: "#2E1C8F", 950: "#000365",` |

### `#003366`

| File:Line | Snippet |
|---|---|
| `tests/test_color_contrast.py:14` | `assert pick_text_color("#003366") == "#FFFFFF"  # dark blue -> white` |

### `#00bcd4`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1164` | `('seg-6', 'Recreation', 'Hobbies and leisure activities', '#00BCD4', 6),` |

### `#00c800`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:98` | `- Command: `rg -n 'text_color="black"\|fg_color="white"\|dropdown_fg_color="white"\|button_hover_color="white"\|dropdown_text_color="black"\|button_color="white"\|text_color="#00C8` |
| `src/getmoredone/theme.py:465` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

### `#00ff00`

| File:Line | Snippet |
|---|---|
| `tests/test_vps_data_integrity.py:64` | `color_hex="#00FF00",` |
| `tests/test_vps_integration.py:1397` | `color_hex="#00FF00",` |
| `tests/test_vps_integration.py:1492` | `color_hex="#00FF00"` |
| `tests/test_vps_integration.py:1499` | `assert segment['color_hex'] == "#00FF00"` |
| `tests/test_vps_integration.py:1551` | `color_hex="#00FF00",` |
| `tests/test_vps_integration.py:1581` | `color_hex="#00FF00",` |
| `tests/test_vps_integration.py:1634` | `valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#ABCDEF", "#123456"]` |

### `#00ffaa`

| File:Line | Snippet |
|---|---|
| `tests/test_vision_planning_regressions.py:43` | `assert screen._get_date_text_color() == "#00FFAA"` |

### `#010203`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:636` | `settings.priority_level_color_any_critical = "#010203"` |
| `tests/test_priority_level_colors.py:639` | `).fill == "#010203"` |

### `#0284c7`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:459` | `"Week": "#0284C7",` |

### `#052e16`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:146` | `# deep -- the `low` fill is #052E16 -- and `success_strong`'s dark` |
| `src/getmoredone/theme.py:377` | `"low": "#052E16",` |

### `#059669`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:458` | `"Month": "#059669",` |

### `#07368f`

| File:Line | Snippet |
|---|---|
| `tests/test_segment_colour_validation.py:38` | `#: ``"#-12345"`` derived ``#07368F``, both silently. One regex refuses all` |
| `tests/test_segment_colour_validation.py:45` | `SILENTLY_MISREAD = {"#+12345": "#0B368D", "# 12345": "#0B368D", "#-12345": "#07368F"}` |

### `#0a0b0c`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:495` | `LEVEL_ANY_CRITICAL: "#0A0B0C",` |
| `tests/test_priority_level_colors.py:502` | `assert settings.priority_level_color_any_critical == "#0A0B0C"` |
| `tests/test_priority_level_colors.py:510` | `assert stub.priority_level_swatches[LEVEL_ANY_CRITICAL].fg_color == "#0A0B0C"` |
| `tests/test_priority_level_colors.py:523` | `AppSettings(), {LEVEL_ANY_CRITICAL: "#0A0B0C"}, write_succeeds=False` |
| `tests/test_priority_level_colors.py:1076` | `LEVEL_ANY_CRITICAL: "#0A0B0C",` |

### `#0a1b2c`

| File:Line | Snippet |
|---|---|
| `docs/spec_coverage.md:2011` | ``#0A1B2C` rather than the `#0a1b2c` it was created with (SCV-M5.1).` |
| `tests/test_vps_segments.py:97` | `segment_id = vps.create_segment("Coloured", "desc", "#0a1b2c", 94)` |
| `tests/test_vps_segments.py:105` | `# intentionally. This read `== "#0a1b2c"`, the literal handed to` |
| `tests/test_vps_segments.py:107` | `# `#0A1B2C`. The claim here is "seeded from the segment", so it is` |
| `tests/test_vps_segments.py:112` | `assert dialog.selected_color == "#0A1B2C"` |
| `tests/test_vps_segments.py:134` | `segment_id = vps.create_segment("Utterly Distinct", "d", "#0a1b2c", 95)` |

### `#0b1010`

| File:Line | Snippet |
|---|---|
| `docs/spec_coverage.md:1962` | `\| SCV-M1.2 \| `#0X1234`, `#1_2345` and `#+12345` are refused by both validators and by the authority; `#0b1010` still passes \| same \| `::test_scvm12_the_validators_refuse_what_i` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:30` | `\| `#0b1010` \| `True` \| `#0B1010` \| `#35474A` — correct; six hex digits, not a defect \|` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:58` | `\| SCV-M1.2 \| The three measured accepts are refused, and `#0b1010` still passes \| `::test_scvm12_the_validators_refuse_what_int_base_16_allows` — the §1 table as the fixture; co` |
| `tests/test_segment_colour_validation.py:31` | `#: family that must keep working. ``#0b1010`` is not a defect -- it is six hex` |
| `tests/test_segment_colour_validation.py:46` | `STILL_VALID = "#0b1010"` |
| `tests/test_segment_colour_validation.py:147` | `"""SCV-M1.2 — ``#0b1010`` is six hex digits, and must keep working.` |
| `tests/test_segment_colour_validation.py:153` | `assert normalize_hex_color(STILL_VALID) == "#0B1010"` |
| `tests/test_segment_colour_validation.py:272` | `app. ``#0b1010 -> #35474A`` (the plan's §1 table) and` |
| `tests/test_segment_colour_validation.py:276` | `assert _derive("#0b1010") == "#35474A"` |
| `tests/test_segment_colour_validation.py:279` | `assert _derive("  #0B1010 ") == "#35474A"` |

### `#0b368d`

| File:Line | Snippet |
|---|---|
| `BACKLOG.md:374` | `it as "correct already", which is wrong: it reads `#+12345` as `#0B368D` by the` |
| `docs/DOCUMENTATION_INDEX.md:432` | ``#0B368D` from a misread slice` |
| `docs/spec_coverage.md:1965` | `\| SCV-M2.2 \| `#+12345` falls back rather than deriving `#0B368D` from a misread slice \| same \| `::test_scvm22_a_colour_that_parses_wrongly_is_not_derived_from` \| done \|` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:29` | `\| `#+12345` \| `True` \| `None` \| `#0B368D` — no error, a colour derived from garbage \|` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:61` | `\| SCV-M2.2 \| `#+12345` falls back rather than deriving `#0B368D` from a misread slice \| `::test_scvm22_a_colour_that_parses_wrongly_is_not_derived_from` — adversarial (P7): look` |
| `src/getmoredone/vps_manager.py:220` | ```#+12345`` raised nothing and derived ``#0B368D`` from a` |
| `tests/test_segment_colour_validation.py:37` | `#: and takes a minus sign, so ``"# 12345"`` derived ``#0B368D`` and` |
| `tests/test_segment_colour_validation.py:45` | `SILENTLY_MISREAD = {"#+12345": "#0B368D", "# 12345": "#0B368D", "#-12345": "#07368F"}` |
| `tests/test_segment_colour_validation.py:235` | `that happened to land on ``#0B368D`` by another route would pass a` |

### `#0d0e0f`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:503` | `assert settings.priority_level_color_any_high == "#0D0E0F"` |
| `tests/test_priority_level_colors.py:509` | `assert stub.priority_level_color_vars[LEVEL_ANY_HIGH].get() == "#0D0E0F"` |
| `tests/test_priority_level_colors.py:1077` | `LEVEL_ANY_HIGH: "#0D0E0F",` |

### `#0d9488`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:455` | `"Annual Plan": "#0D9488",` |

### `#0ea5e9`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:49` | `\| `#0EA5E9` blue \| black \| 7.58 \| 2.16 \| 6.28 \|` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#0f172a`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:1186` | `dark = text_for("#0F172A")` |
| `tests/test_priority_level_colors.py:1189` | `assert contrast_ratio("#0F172A", dark) >= MIN_TEXT_CONTRAST` |
| `tests/test_priority_level_colors.py:1553` | `for colour in ("#DCFCE7", "#334155", "#F8FAFC", "#0F172A"):` |

### `#100f47`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:109` | `GROUND_GRADIENT = ("#100F47", "#291E68")` |

### `#101112`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:1078` | `LEVEL_NO_HIGH_OR_CRITICAL: "#101112",` |

### `#101342`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:45` | `DEEP_INK = "#101342"` |
| `src/getmoredone/brand.py:93` | `800: "#3F3A6B", 900: "#262454", 950: "#101342",` |
| `themes/davipa.json:5` | `"#101342"` |
| `themes/davipa.json:11` | `"#101342"` |

### `#10b981`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:50` | `\| `#10B981` green \| black \| 8.28 \| 1.98 \| 6.86 \|` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#111`

| File:Line | Snippet |
|---|---|
| `tests/test_weekly_tactic_parent.py:738` | `palette={"primary": "#000", "on_primary": "#fff", "body_text": "#111"},` |

### `#111111`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:491` | `settings.priority_level_color_any_critical = "#111111"` |
| `tests/test_rename_safe_links.py:2227` | `first = vps.create_segment("Santé", "d", "#111111", 90)` |
| `themes/black_white.json:34` | `"#111111",` |
| `themes/black_white.json:47` | `"#111111"` |
| `themes/black_white.json:67` | `"#111111"` |
| `themes/black_white.json:86` | `"#111111",` |
| `themes/black_white.json:119` | `"#111111",` |
| `themes/black_white.json:144` | `"#111111",` |
| `themes/black_white.json:172` | `"#111111",` |
| `themes/black_white.json:194` | `"#111111",` |
| `themes/black_white.json:205` | `"#111111",` |
| `themes/black_white.json:274` | `"#111111",` |
| `tools/generate_ctk_themes.py:56` | `BLACK_WHITE_ANCHOR = ["#111111", "#F3F4F6"]` |
| `tools/generate_ctk_themes.py:58` | `BLACK_WHITE_BUTTON_TEXT = ["#FFFFFF", "#111111"]` |
| `tools/generate_ctk_themes.py:80` | `("CTkEntry", "fg_color"): ["#FFFFFF", "#111111"],` |

### `#112233`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:317` | `settings.priority_level_color_any_critical = "#112233"` |
| `tests/test_priority_level_colors.py:323` | `assert reloaded.priority_level_color_any_critical == "#112233"` |
| `tests/test_priority_level_colors.py:326` | `assert level_color(reloaded, LEVEL_ANY_CRITICAL) == "#112233"` |
| `tests/test_unified_panel_design.py:2714` | `resolve_segment_color=lambda name, colors: "#112233",` |
| `tests/test_unified_panel_design.py:2723` | `assert (seg, sub, cat) == ("#112233", "#445566", "#445566")` |
| `tests/test_weekly_item_filters.py:26` | `(seg_id, "Creative", "Test Segment", "#112233", 1, 1, now, now),` |

### `#123456`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:546` | `LEVEL_ANY_CRITICAL: "#123456",` |
| `tests/test_rename_safe_links.py:1720` | `else original.upper(), "#123456", 99,` |
| `tests/test_rename_safe_links.py:2040` | `vps.create_segment(existing.upper(), "d", "#123456", 90)` |
| `tests/test_rename_safe_links.py:2042` | `vps.create_segment(existing.lower(), "d", "#123456", 91)` |
| `tests/test_rename_safe_links.py:2045` | `vps.create_segment(f"  {existing}  ", "d", "#123456", 92)` |
| `tests/test_rename_safe_links.py:2048` | `new_id = vps.create_segment("Utterly Distinct", "d", "#123456", 93)` |
| `tests/test_rename_safe_links.py:2080` | `other = vps.create_segment("Utterly Distinct", "d", "#123456", 93)` |
| `tests/test_rename_safe_links.py:2164` | `other = vps.create_segment("Quite Separate", "d", "#123456", 92)` |
| `tests/test_rename_safe_links.py:2187` | `seg = vps.create_segment("Before Padding", "d", "#123456", 94)` |
| `tests/test_rename_safe_links.py:2380` | `ids["C"] = vps.create_segment("Solo", "d", "#123456", 92)` |
| `tests/test_rename_safe_links.py:2381` | `ids["D"] = vps.create_segment("Other", "d", "#123456", 93)` |
| `tests/test_rename_safe_links.py:2476` | `seg = vps.create_segment("Before Failure", "d", "#123456", 96)` |
| `tests/test_segment_colour_validation.py:183` | `segment_id = manager.create_segment("Scv Colour", "desc", "#123456", 91)` |
| `tests/test_segment_colour_validation.py:261` | `for value in ("#abc", "\t#123456\n", "AABBCC"):` |
| `tests/test_segment_colour_validation.py:590` | `segment_id = manager.create_segment("Scv Load", "desc", "#123456", 96)` |
| `tests/test_vps_integration.py:1634` | `valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#ABCDEF", "#123456"]` |
| `tests/test_vps_segments.py:212` | `segment_id = vps.create_segment("Test Segment", "desc", "#123456", 99)` |
| `tests/test_vps_segments.py:217` | `assert stored["color_hex"] == "#123456"` |
| `tests/test_vps_segments.py:245` | `segment_id = vps.create_segment("Linked Segment", "desc", "#123456", 97)` |
| `tests/test_vps_segments.py:265` | `segment_id = vps.create_segment("Busy Segment", "desc", "#123456", 96)` |
| `tests/test_vps_segments.py:304` | `segment_id = vps.create_segment("Contract", "desc", "#123456", 95)` |
| `tests/test_vps_segments.py:373` | `segment_id = vps.create_segment("Full chain", "desc", "#123456", 90)` |

### `#14375e`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:92` | `primary_hover = _theme_value("CTkButton", "hover_color", "#14375e")` |
| `themes/base_dark_blue.json:19` | `"hover_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:42` | `"hover_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:64` | `"hover_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:83` | `"button_hover_color": ["#325882", "#14375e"]` |
| `themes/base_dark_blue.json:88` | `"button_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:115` | `"selected_hover_color": ["#325882", "#14375e"],` |

### `#14532d`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/backlog_archive_2026-11-09.md:1639` | `green such as `#14532D` for Any Critical gets about 1:1 and the tick vanishes.` |
| `src/getmoredone/theme.py:136` | `"success_strong": "#166534" if mode == "light" else "#14532D",` |

### `#14b8a6`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:54` | `\| `#14B8A6` teal \| black \| 8.44 \| 1.94 \| 6.99 \|` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#154b75`

| File:Line | Snippet |
|---|---|
| `themes/blue.json:39` | `"#154B75"` |
| `themes/blue.json:95` | `"#154B75"` |
| `themes/blue.json:153` | `"#154B75"` |
| `themes/blue.json:199` | `"#154B75"` |
| `themes/blue.json:210` | `"#154B75"` |
| `themes/blue.json:279` | `"#154B75"` |

### `#155e75`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md:184` | `(`#4B5563` light / `#9CA3AF` dark); only `break` differs (`#155E75` / `#22D3EE`).` |

### `#15803d`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:343` | `"low": "#15803D",` |

### `#166534`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-07-plan-clear-day-and-marks.md:43` | `fill: a mark nobody could see. The shipped pair is #166534/#4ADE80 (scheduled)` |
| `docs/unused-docs/implementation_plan_2026-11-06_plan_box_appearance.md:40` | ``#92400E`, `#166534`) so they clear **4.5:1** against `surface_subtle`. The` |
| `src/getmoredone/theme.py:136` | `"success_strong": "#166534" if mode == "light" else "#14532D",` |
| `src/getmoredone/theme.py:150` | `"scheduled_mark": "#166534" if mode == "light" else "#4ADE80",` |
| `src/getmoredone/theme.py:306` | `"low": "#166534",` |

### `#171447`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:43` | `MIDNIGHT = "#171447"` |
| `src/getmoredone/brand.py:88` | `800: "#42386D", 900: "#292256", 950: "#171447",` |
| `themes/davipa.json:19` | `"#171447"` |

### `#1a2b3c`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:94` | `canonical**, not only one that is unreadable: a row holding `#1a2b3c` is` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:95` | `rewritten to `#1A2B3C` on the first read after this change, and a row` |
| `tests/test_segment_colour_validation.py:692` | `row, var = VisionSegmentsScreen._color_input(None, root, "#1a2b3c")` |
| `tests/test_segment_colour_validation.py:693` | `assert row.winfo_children()[0].cget("fg_color") == "#1A2B3C"` |
| `tests/test_segment_colour_validation.py:694` | `assert var.get() == "#1a2b3c", "a readable colour was rewritten in the entry"` |
| `tests/test_segment_colour_validation.py:942` | `row, var = vs.VisionSegmentsScreen._color_input(None, root, "#1a2b3c")` |
| `tests/test_segment_colour_validation.py:944` | `assert captured["initialcolor"] == "#1A2B3C"` |
| `tests/test_vps_segments.py:173` | `@pytest.mark.parametrize("value", ["#000000", "#ffffff", "#AABBCC", "#1a2b3c"])` |

### `#1b6b49`

| File:Line | Snippet |
|---|---|
| `themes/green.json:213` | `"#1B6B49",` |

### `#1c2025`

| File:Line | Snippet |
|---|---|
| `themes/grey.json:213` | `"#1C2025",` |

### `#1d1d1d`

| File:Line | Snippet |
|---|---|
| `themes/grey.json:214` | `"#1D1D1D"` |

### `#1d1d1f`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:19` | `"#1D1D1F"` |
| `themes/apple_grey.json:23` | `"#1D1D1F"` |
| `themes/apple_grey.json:34` | `"#1D1D1F",` |
| `themes/apple_grey.json:47` | `"#1D1D1F"` |
| `themes/apple_grey.json:58` | `"#1D1D1F",` |
| `themes/apple_grey.json:67` | `"#1D1D1F"` |
| `themes/apple_grey.json:74` | `"#1D1D1F",` |
| `themes/apple_grey.json:86` | `"#1D1D1F",` |
| `themes/apple_grey.json:119` | `"#1D1D1F",` |
| `themes/apple_grey.json:144` | `"#1D1D1F",` |
| `themes/apple_grey.json:172` | `"#1D1D1F",` |
| `themes/apple_grey.json:194` | `"#1D1D1F",` |
| `themes/apple_grey.json:205` | `"#1D1D1F",` |
| `themes/apple_grey.json:274` | `"#1D1D1F",` |
| `tools/generate_ctk_themes.py:52` | `APPLE_GREY_ANCHOR = ["#1D1D1F", "#D2D2D7"]` |
| `tools/generate_ctk_themes.py:54` | `APPLE_GREY_BUTTON_TEXT = ["#FFFFFF", "#1D1D1F"]` |
| `tools/generate_ctk_themes.py:63` | `("CTkFrame", "fg_color"): ["#FFFFFF", "#1D1D1F"],` |
| `tools/generate_ctk_themes.py:64` | `("CTkFrame", "top_fg_color"): ["#FFFFFF", "#1D1D1F"],` |
| `tools/generate_ctk_themes.py:66` | `("CTkLabel", "text_color"): ["#1D1D1F", "#F5F5F7"],` |
| `tools/generate_ctk_themes.py:67` | `("CTkEntry", "fg_color"): ["#FFFFFF", "#1D1D1F"],` |
| `tools/generate_ctk_themes.py:69` | `("CTkEntry", "text_color"): ["#1D1D1F", "#F5F5F7"],` |

### `#1d2531`

| File:Line | Snippet |
|---|---|
| `themes/grey.json:39` | `"#1D2531"` |
| `themes/grey.json:95` | `"#1D2531"` |
| `themes/grey.json:153` | `"#1D2531"` |
| `themes/grey.json:199` | `"#1D2531"` |
| `themes/grey.json:210` | `"#1D2531"` |
| `themes/grey.json:279` | `"#1D2531"` |

### `#1e2c40`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:89` | `"button_hover_color": ["#234567", "#1e2c40"],` |

### `#1f2b24`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:129` | `"success_tint": "#E8F5EE" if mode == "light" else "#1F2B24",` |

### `#1f538d`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:91` | `primary = _theme_value("CTkButton", "fg_color", "#1f538d")` |
| `themes/base_dark_blue.json:18` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:40` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:52` | `"progress_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:62` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:72` | `"progress_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:82` | `"button_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:87` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:114` | `"selected_color": ["#3a7ebf", "#1f538d"],` |

### `#1f6aa5`

| File:Line | Snippet |
|---|---|
| `themes/blue.json:35` | `"#1F6AA5"` |
| `themes/blue.json:87` | `"#1F6AA5"` |
| `themes/blue.json:120` | `"#1F6AA5"` |
| `themes/blue.json:145` | `"#1F6AA5"` |
| `themes/blue.json:173` | `"#1F6AA5"` |
| `themes/blue.json:195` | `"#1F6AA5"` |
| `themes/blue.json:206` | `"#1F6AA5"` |
| `themes/blue.json:275` | `"#1F6AA5"` |
| `tools/generate_ctk_themes.py:48` | `"blue": ["#3B8ED0", "#1F6AA5"],` |

### `#21527b`

| File:Line | Snippet |
|---|---|
| `themes/blue.json:213` | `"#21527B",` |

### `#217953`

| File:Line | Snippet |
|---|---|
| `themes/green.json:39` | `"#217953"` |
| `themes/green.json:95` | `"#217953"` |
| `themes/green.json:153` | `"#217953"` |
| `themes/green.json:199` | `"#217953"` |
| `themes/green.json:210` | `"#217953"` |
| `themes/green.json:279` | `"#217953"` |

### `#2196f3`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1160` | `('seg-2', 'Purposeful Activity', 'Career, work, and meaningful projects', '#2196F3', 2),` |

### `#222222`

| File:Line | Snippet |
|---|---|
| `tests/test_rename_safe_links.py:2228` | `second = vps.create_segment("SANTÉ", "d", "#222222", 91)` |
| `tests/test_vps_segments.py:399` | `parents = vps.create_segment("Parents", "desc", "#222222", 89)` |

### `#223247`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:135` | `"selected_tint": "#E6EEF8" if mode == "light" else "#223247",` |

### `#22d3ee`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md:184` | `(`#4B5563` light / `#9CA3AF` dark); only `break` differs (`#155E75` / `#22D3EE`).` |

### `#233b53`

| File:Line | Snippet |
|---|---|
| `themes/blue.json:214` | `"#233B53"` |

### `#234567`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:89` | `"button_hover_color": ["#234567", "#1e2c40"],` |

### `#2563eb`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:454` | `"Annual Vision": "#2563EB",` |

### `#262454`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:93` | `800: "#3F3A6B", 900: "#262454", 950: "#101342",` |

### `#27272a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:378` | `"unscored": "#27272A",` |

### `#288862`

| File:Line | Snippet |
|---|---|
| `themes/green.json:38` | `"#288862",` |
| `themes/green.json:94` | `"#288862",` |
| `themes/green.json:152` | `"#288862",` |
| `themes/green.json:198` | `"#288862",` |
| `themes/green.json:209` | `"#288862",` |
| `themes/green.json:278` | `"#288862",` |

### `#291e68`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:109` | `GROUND_GRADIENT = ("#100F47", "#291E68")` |

### `#292256`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:88` | `800: "#42386D", 900: "#292256", 950: "#171447",` |
| `themes/davipa.json:23` | `"#292256"` |
| `themes/davipa.json:67` | `"#292256"` |
| `themes/davipa.json:271` | `"#292256"` |
| `themes/davipa.json:283` | `"#292256"` |
| `themes/davipa.json:303` | `"#292256"` |
| `themes/davipa.json:325` | `"#292256"` |
| `themes/davipa.json:331` | `"#292256"` |

### `#2a1400`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:83` | `800: "#6B2F00", 900: "#461F00", 950: "#2A1400",` |

### `#2cc985`

| File:Line | Snippet |
|---|---|
| `themes/green.json:34` | `"#2CC985",` |
| `themes/green.json:86` | `"#2CC985",` |
| `themes/green.json:119` | `"#2CC985",` |
| `themes/green.json:144` | `"#2CC985",` |
| `themes/green.json:172` | `"#2CC985",` |
| `themes/green.json:194` | `"#2CC985",` |
| `themes/green.json:205` | `"#2CC985",` |
| `themes/green.json:274` | `"#2CC985",` |
| `tools/generate_ctk_themes.py:44` | `"green": ["#2CC985", "#2FA572"],` |

### `#2e1c8f`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:33` | `INDIGO = "#2E1C8F"` |
| `src/getmoredone/brand.py:63` | `800: "#40299C", 900: "#2E1C8F", 950: "#000365",` |
| `themes/davipa.json:34` | `"#2E1C8F",` |
| `themes/davipa.json:35` | `"#2E1C8F"` |
| `themes/davipa.json:58` | `"#2E1C8F",` |
| `themes/davipa.json:74` | `"#2E1C8F",` |
| `themes/davipa.json:102` | `"#2E1C8F",` |
| `themes/davipa.json:131` | `"#2E1C8F",` |
| `themes/davipa.json:156` | `"#2E1C8F",` |
| `themes/davipa.json:172` | `"#2E1C8F",` |
| `themes/davipa.json:190` | `"#2E1C8F",` |
| `themes/davipa.json:205` | `"#2E1C8F",` |
| `themes/davipa.json:206` | `"#2E1C8F"` |
| `themes/davipa.json:229` | `"#2E1C8F",` |
| `themes/davipa.json:230` | `"#2E1C8F"` |
| `themes/davipa.json:233` | `"#2E1C8F",` |
| `themes/davipa.json:234` | `"#2E1C8F"` |
| `themes/davipa.json:274` | `"#2E1C8F",` |
| `themes/davipa.json:275` | `"#2E1C8F"` |
| `themes/davipa.json:310` | `"#2E1C8F",` |
| `themes/davipa.json:338` | `"#2E1C8F",` |

### `#2f6597`

| File:Line | Snippet |
|---|---|
| `themes/blue.json:38` | `"#2F6597",` |
| `themes/blue.json:94` | `"#2F6597",` |
| `themes/blue.json:152` | `"#2F6597",` |
| `themes/blue.json:198` | `"#2F6597",` |
| `themes/blue.json:209` | `"#2F6597",` |
| `themes/blue.json:278` | `"#2F6597",` |

### `#2fa572`

| File:Line | Snippet |
|---|---|
| `themes/green.json:35` | `"#2FA572"` |
| `themes/green.json:87` | `"#2FA572"` |
| `themes/green.json:120` | `"#2FA572"` |
| `themes/green.json:145` | `"#2FA572"` |
| `themes/green.json:173` | `"#2FA572"` |
| `themes/green.json:195` | `"#2FA572"` |
| `themes/green.json:206` | `"#2FA572"` |
| `themes/green.json:275` | `"#2FA572"` |
| `tools/generate_ctk_themes.py:44` | `"green": ["#2CC985", "#2FA572"],` |

### `#30343b`

| File:Line | Snippet |
|---|---|
| `themes/grey.json:38` | `"#30343B",` |
| `themes/grey.json:94` | `"#30343B",` |
| `themes/grey.json:152` | `"#30343B",` |
| `themes/grey.json:198` | `"#30343B",` |
| `themes/grey.json:209` | `"#30343B",` |
| `themes/grey.json:278` | `"#30343B",` |

### `#305648`

| File:Line | Snippet |
|---|---|
| `themes/green.json:214` | `"#305648"` |

### `#325882`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:19` | `"hover_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:42` | `"hover_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:64` | `"hover_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:83` | `"button_hover_color": ["#325882", "#14375e"]` |
| `themes/base_dark_blue.json:88` | `"button_color": ["#325882", "#14375e"],` |
| `themes/base_dark_blue.json:115` | `"selected_hover_color": ["#325882", "#14375e"],` |

### `#330039`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:68` | `800: "#691E71", 900: "#4E0157", 950: "#330039",` |

### `#333333`

| File:Line | Snippet |
|---|---|
| `tests/test_vps_segments.py:400` | `target = vps.create_segment("Target", "desc", "#333333", 88)` |

### `#334155`

| File:Line | Snippet |
|---|---|
| `BACKLOG.md:355` | `(`:1406`) both return `row["color_hex"] or "#334155"`, i.e. whatever the` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:110` | `slate `#334155` and the text is the stored value. Before 2026-11-11` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:145` | `stored colour is malformed, the swatch is slate `#334155` and the text is` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:103` | ``(row["color_hex"] or "").strip() or "#334155"`, i.e. the raw stored value.` |
| `src/getmoredone/screens/segment_color_utils.py:10` | `DEFAULT_SEGMENT_COLOR = "#334155"` |
| `src/getmoredone/screens/settings_vsp_segments.py:13` | `DEFAULT_INDICATOR_COLOR = "#334155"` |
| `src/getmoredone/screens/vision_segments.py:13` | `DEFAULT_SWATCH_COLOR = "#334155"` |
| `src/getmoredone/screens/vision_segments.py:379` | `color_row, color = self._color_input(f, (row or {}).get("color_hex", "#334155"))` |
| `src/getmoredone/vps_manager.py:1433` | `color_map[name] = row["color_hex"] or "#334155"` |
| `src/getmoredone/vps_manager.py:1443` | `color = (row["color_hex"] or "").strip() or "#334155"` |
| `src/getmoredone/vps_manager_taxonomy.py:1010` | `COALESCE(sd.color_hex, '#334155') AS color_hex,` |
| `tests/test_priority_level_colors.py:1553` | `for colour in ("#DCFCE7", "#334155", "#F8FAFC", "#0F172A"):` |
| `tests/test_segment_colour_validation.py:862` | ```fg_color=row.get("color_hex") or "#334155"`` straight from` |
| `themes/grey.json:35` | `"#334155"` |
| `themes/grey.json:87` | `"#334155"` |
| `themes/grey.json:120` | `"#334155"` |
| `themes/grey.json:145` | `"#334155"` |
| `themes/grey.json:173` | `"#334155"` |
| `themes/grey.json:195` | `"#334155"` |
| `themes/grey.json:206` | `"#334155"` |
| `themes/grey.json:275` | `"#334155"` |
| `tools/generate_ctk_themes.py:47` | `"grey": ["#475569", "#334155"],` |

### `#3366cc`

| File:Line | Snippet |
|---|---|
| `tests/test_unified_panel_design.py:575` | `{"segment": "#3366cc", "subsegment": "#44aa88", "category": "#cc7744"},` |
| `tests/test_unified_panel_design.py:692` | `{"segment": "#3366cc"},` |
| `tests/test_unified_panel_design.py:726` | `{"segment": "#3366cc"})` |
| `tests/test_unified_panel_design.py:751` | `{"segment": "#3366cc"})` |

### `#343638`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:230` | `"#343638"` |
| `themes/base_dark_blue.json:32` | `"fg_color": ["#F9F9FA", "#343638"],` |
| `themes/base_dark_blue.json:96` | `"fg_color": ["#F9F9FA", "#343638"],` |
| `themes/black_white.json:230` | `"#343638"` |
| `themes/blue.json:67` | `"#343638"` |
| `themes/blue.json:230` | `"#343638"` |
| `themes/green.json:67` | `"#343638"` |
| `themes/green.json:230` | `"#343638"` |
| `themes/grey.json:67` | `"#343638"` |
| `themes/grey.json:230` | `"#343638"` |
| `themes/orange.json:67` | `"#343638"` |
| `themes/orange.json:230` | `"#343638"` |
| `themes/pink.json:67` | `"#343638"` |
| `themes/pink.json:230` | `"#343638"` |
| `themes/purple.json:67` | `"#343638"` |
| `themes/purple.json:230` | `"#343638"` |

### `#350b00`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:58` | `800: "#86000E", 900: "#5D0000", 950: "#350B00",` |

### `#35474a`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:30` | `\| `#0b1010` \| `True` \| `#0B1010` \| `#35474A` — correct; six hex digits, not a defect \|` |
| `tests/test_segment_colour_validation.py:272` | `app. ``#0b1010 -> #35474A`` (the plan's §1 table) and` |
| `tests/test_segment_colour_validation.py:276` | `assert _derive("#0b1010") == "#35474A"` |
| `tests/test_segment_colour_validation.py:279` | `assert _derive("  #0B1010 ") == "#35474A"` |

### `#360031`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:73` | `800: "#78006E", 900: "#52004B", 950: "#360031",` |

### `#3a2328`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:45` | ``critical_tint` is `#FDECEC` light / `#3A2328` dark (`theme.py:129`).` |
| `src/getmoredone/theme.py:130` | `"critical_tint": "#FDECEC" if mode == "light" else "#3A2328",` |

### `#3a7ebf`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:18` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:40` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:52` | `"progress_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:62` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:72` | `"progress_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:82` | `"button_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:87` | `"fg_color": ["#3a7ebf", "#1f538d"],` |
| `themes/base_dark_blue.json:114` | `"selected_color": ["#3a7ebf", "#1f538d"],` |

### `#3b82f6`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:465` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

### `#3b8ed0`

| File:Line | Snippet |
|---|---|
| `themes/blue.json:34` | `"#3B8ED0",` |
| `themes/blue.json:86` | `"#3B8ED0",` |
| `themes/blue.json:119` | `"#3B8ED0",` |
| `themes/blue.json:144` | `"#3B8ED0",` |
| `themes/blue.json:172` | `"#3B8ED0",` |
| `themes/blue.json:194` | `"#3B8ED0",` |
| `themes/blue.json:205` | `"#3B8ED0",` |
| `themes/blue.json:274` | `"#3B8ED0",` |
| `tools/generate_ctk_themes.py:48` | `"blue": ["#3B8ED0", "#1F6AA5"],` |

### `#3d0005`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:78` | `800: "#850023", 900: "#5C0015", 950: "#3D0005",` |

### `#3e454a`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:42` | `"#3E454A",` |
| `themes/apple_grey.json:90` | `"#3E454A",` |
| `themes/apple_grey.json:148` | `"#3E454A",` |
| `themes/base_dark_blue.json:20` | `"border_color": ["#3E454A", "#949A9F"],` |
| `themes/base_dark_blue.json:41` | `"border_color": ["#3E454A", "#949A9F"],` |
| `themes/base_dark_blue.json:63` | `"border_color": ["#3E454A", "#949A9F"],` |
| `themes/black_white.json:42` | `"#3E454A",` |
| `themes/black_white.json:90` | `"#3E454A",` |
| `themes/black_white.json:148` | `"#3E454A",` |
| `themes/blue.json:42` | `"#3E454A",` |
| `themes/blue.json:90` | `"#3E454A",` |
| `themes/blue.json:148` | `"#3E454A",` |
| `themes/green.json:42` | `"#3E454A",` |
| `themes/green.json:90` | `"#3E454A",` |
| `themes/green.json:148` | `"#3E454A",` |
| `themes/grey.json:42` | `"#3E454A",` |
| `themes/grey.json:90` | `"#3E454A",` |
| `themes/grey.json:148` | `"#3E454A",` |
| `themes/orange.json:42` | `"#3E454A",` |
| `themes/orange.json:90` | `"#3E454A",` |
| `themes/orange.json:148` | `"#3E454A",` |
| `themes/pink.json:42` | `"#3E454A",` |
| `themes/pink.json:90` | `"#3E454A",` |
| `themes/pink.json:148` | `"#3E454A",` |
| `themes/purple.json:42` | `"#3E454A",` |
| `themes/purple.json:90` | `"#3E454A",` |
| `themes/purple.json:148` | `"#3E454A",` |

### `#3f3a6b`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:93` | `800: "#3F3A6B", 900: "#262454", 950: "#101342",` |

### `#40299c`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:63` | `800: "#40299C", 900: "#2E1C8F", 950: "#000365",` |

### `#42386d`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:88` | `800: "#42386D", 900: "#292256", 950: "#171447",` |
| `themes/davipa.json:27` | `"#42386D"` |
| `themes/davipa.json:43` | `"#42386D"` |
| `themes/davipa.json:71` | `"#42386D"` |
| `themes/davipa.json:91` | `"#42386D"` |
| `themes/davipa.json:116` | `"#42386D"` |
| `themes/davipa.json:149` | `"#42386D"` |
| `themes/davipa.json:169` | `"#42386D"` |
| `themes/davipa.json:187` | `"#42386D"` |
| `themes/davipa.json:287` | `"#42386D"` |
| `themes/davipa.json:307` | `"#42386D"` |

### `#424245`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:27` | `"#424245"` |
| `themes/apple_grey.json:71` | `"#424245"` |
| `tools/generate_ctk_themes.py:65` | `("CTkFrame", "border_color"): ["#D2D2D7", "#424245"],` |
| `tools/generate_ctk_themes.py:68` | `("CTkEntry", "border_color"): ["#D2D2D7", "#424245"],` |

### `#431407`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:375` | `"high": "#431407",` |

### `#445566`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:318` | `settings.priority_level_color_any_high = "#445566"` |
| `tests/test_priority_level_colors.py:324` | `assert reloaded.priority_level_color_any_high == "#445566"` |
| `tests/test_priority_level_colors.py:649` | `segment_color="#445566",` |
| `tests/test_priority_level_colors.py:651` | `assert segment.fill == "#445566"` |
| `tests/test_priority_level_colors.py:661` | `segment_color="#445566",` |
| `tests/test_priority_level_colors.py:1158` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#000000", "#FFFFFF"):` |
| `tests/test_priority_level_colors.py:1192` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#7F7F7F", "#450A0A"):` |
| `tests/test_unified_panel_design.py:2721` | `{}, {("purposeful work", "living systems"): "#445566"}, {},` |
| `tests/test_unified_panel_design.py:2723` | `assert (seg, sub, cat) == ("#112233", "#445566", "#445566")` |
| `tests/test_unified_panel_design.py:2727` | `{}, {("purposeful work", "living systems"): "#445566"},` |

### `#4477aa`

| File:Line | Snippet |
|---|---|
| `tests/test_unified_panel_design.py:2161` | `screen.subsegment_colors = {("purposeful work", "living systems"): "#4477aa"}` |
| `tests/test_unified_panel_design.py:2165` | `assert sub == "#4477AA"` |

### `#44aa66`

| File:Line | Snippet |
|---|---|
| `tests/test_weekly_item_filters.py:48` | `(vision_subsegment_id, vision_segment_id, "Books", "#44AA66", now, now),` |
| `tests/test_weekly_title_cleanup.py:31` | `(vision_subsegment_id, vision_segment_id, "Writing", "#44AA66", now, now),` |

### `#44aa88`

| File:Line | Snippet |
|---|---|
| `tests/test_unified_panel_design.py:575` | `{"segment": "#3366cc", "subsegment": "#44aa88", "category": "#cc7744"},` |

### `#450a0a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:374` | `"critical": "#450A0A",` |
| `tests/test_priority_level_colors.py:696` | `for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1192` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#7F7F7F", "#450A0A"):` |

### `#451a03`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:376` | `"medium": "#451A03",` |

### `#461f00`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:83` | `800: "#6B2F00", 900: "#461F00", 950: "#2A1400",` |

### `#472617`

| File:Line | Snippet |
|---|---|
| `themes/orange.json:214` | `"#472617"` |

### `#475569`

| File:Line | Snippet |
|---|---|
| `themes/grey.json:34` | `"#475569",` |
| `themes/grey.json:86` | `"#475569",` |
| `themes/grey.json:119` | `"#475569",` |
| `themes/grey.json:144` | `"#475569",` |
| `themes/grey.json:172` | `"#475569",` |
| `themes/grey.json:194` | `"#475569",` |
| `themes/grey.json:205` | `"#475569",` |
| `themes/grey.json:274` | `"#475569",` |
| `tools/generate_ctk_themes.py:47` | `"grey": ["#475569", "#334155"],` |

### `#4a4d50`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:116` | `"#4A4D50"` |
| `themes/apple_grey.json:169` | `"#4A4D50"` |
| `themes/apple_grey.json:187` | `"#4A4D50"` |
| `themes/base_dark_blue.json:51` | `"fg_color": ["#939BA2", "#4A4D50"],` |
| `themes/base_dark_blue.json:71` | `"fg_color": ["#939BA2", "#4A4D50"],` |
| `themes/base_dark_blue.json:80` | `"fg_color": ["#939BA2", "#4A4D50"],` |
| `themes/black_white.json:116` | `"#4A4D50"` |
| `themes/black_white.json:169` | `"#4A4D50"` |
| `themes/black_white.json:187` | `"#4A4D50"` |
| `themes/blue.json:116` | `"#4A4D50"` |
| `themes/blue.json:169` | `"#4A4D50"` |
| `themes/blue.json:187` | `"#4A4D50"` |
| `themes/green.json:116` | `"#4A4D50"` |
| `themes/green.json:169` | `"#4A4D50"` |
| `themes/green.json:187` | `"#4A4D50"` |
| `themes/grey.json:116` | `"#4A4D50"` |
| `themes/grey.json:169` | `"#4A4D50"` |
| `themes/grey.json:187` | `"#4A4D50"` |
| `themes/orange.json:116` | `"#4A4D50"` |
| `themes/orange.json:169` | `"#4A4D50"` |
| `themes/orange.json:187` | `"#4A4D50"` |
| `themes/pink.json:116` | `"#4A4D50"` |
| `themes/pink.json:169` | `"#4A4D50"` |
| `themes/pink.json:187` | `"#4A4D50"` |
| `themes/purple.json:116` | `"#4A4D50"` |
| `themes/purple.json:169` | `"#4A4D50"` |
| `themes/purple.json:187` | `"#4A4D50"` |

### `#4a90e2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/vps_segment_editor.py:16` | `DEFAULT_SEGMENT_COLOR = "#4A90E2"` |
| `tests/test_vision_planning_regressions.py:127` | `{"ai-1": "#4A90E2"},` |

### `#4ade80`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-07-plan-clear-day-and-marks.md:43` | `fill: a mark nobody could see. The shipped pair is #166534/#4ADE80 (scheduled)` |
| `src/getmoredone/theme.py:150` | `"scheduled_mark": "#166534" if mode == "light" else "#4ADE80",` |
| `src/getmoredone/theme.py:313` | `"low": "#4ADE80",` |

### `#4b1b2b`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:214` | `"#4B1B2B"` |

### `#4b5563`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md:184` | `(`#4B5563` light / `#9CA3AF` dark); only `break` differs (`#155E75` / `#22D3EE`).` |
| `src/getmoredone/theme.py:440` | `padding = "#4B5563" if mode == "light" else "#9CA3AF"` |
| `themes/black_white.json:27` | `"#4B5563"` |
| `tools/generate_ctk_themes.py:78` | `("CTkFrame", "border_color"): ["#D1D5DB", "#4B5563"],` |

### `#4caf50`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-08-20-rename-safe-links-acceptance.md:295` | `colour after: #4CAF50 (wanted #FF0000)` |
| `src/getmoredone/vps_schema.py:1159` | `('seg-1', 'Health', 'Physical and mental wellbeing', '#4CAF50', 1),` |
| `tests/test_rename_safe_links.py:2120` | `(seg_id, name, "", "#4CAF50", order, now, now),` |
| `tests/test_rename_safe_links.py:2377` | `(ids[key], name, "", "#4CAF50", order, now, now),` |
| `tests/test_vps_legacy_migration.py:32` | `("seg-health", "Health", "Legacy test segment", "#4CAF50", 1, now, now),` |
| `tests/test_vps_legacy_migration.py:162` | `(seg_id, name, "", "#4CAF50", order, now, now),` |

### `#4e0157`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:68` | `800: "#691E71", 900: "#4E0157", 950: "#330039",` |

### `#4e11d2`

| File:Line | Snippet |
|---|---|
| `themes/purple.json:213` | `"#4E11D2",` |

### `#52004b`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:73` | `800: "#78006E", 900: "#52004B", 950: "#360031",` |

### `#52525b`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:307` | `"unscored": "#52525B",` |

### `#565b5e`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:234` | `"#565B5E"` |
| `themes/apple_grey.json:238` | `"#565B5E"` |
| `themes/apple_grey.json:307` | `"#565B5E"` |
| `themes/base_dark_blue.json:33` | `"border_color": ["#979DA2", "#565B5E"],` |
| `themes/base_dark_blue.json:97` | `"border_color": ["#979DA2", "#565B5E"],` |
| `themes/base_dark_blue.json:98` | `"button_color": ["#979DA2", "#565B5E"],` |
| `themes/base_dark_blue.json:125` | `"border_color": ["#979DA2", "#565B5E"],` |
| `themes/black_white.json:234` | `"#565B5E"` |
| `themes/black_white.json:238` | `"#565B5E"` |
| `themes/black_white.json:307` | `"#565B5E"` |
| `themes/blue.json:71` | `"#565B5E"` |
| `themes/blue.json:234` | `"#565B5E"` |
| `themes/blue.json:238` | `"#565B5E"` |
| `themes/blue.json:307` | `"#565B5E"` |
| `themes/green.json:71` | `"#565B5E"` |
| `themes/green.json:234` | `"#565B5E"` |
| `themes/green.json:238` | `"#565B5E"` |
| `themes/green.json:307` | `"#565B5E"` |
| `themes/grey.json:71` | `"#565B5E"` |
| `themes/grey.json:234` | `"#565B5E"` |
| `themes/grey.json:238` | `"#565B5E"` |
| `themes/grey.json:307` | `"#565B5E"` |
| `themes/orange.json:71` | `"#565B5E"` |
| `themes/orange.json:234` | `"#565B5E"` |
| `themes/orange.json:238` | `"#565B5E"` |
| `themes/orange.json:307` | `"#565B5E"` |
| `themes/pink.json:71` | `"#565B5E"` |
| `themes/pink.json:234` | `"#565B5E"` |
| `themes/pink.json:238` | `"#565B5E"` |
| `themes/pink.json:307` | `"#565B5E"` |
| `themes/purple.json:71` | `"#565B5E"` |
| `themes/purple.json:234` | `"#565B5E"` |
| `themes/purple.json:238` | `"#565B5E"` |
| `themes/purple.json:307` | `"#565B5E"` |

### `#575183`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:92` | `400: "#A098C9", 500: "#867DAF", 600: "#6E6799", 700: "#575183",` |

### `#582007`

| File:Line | Snippet |
|---|---|
| `themes/orange.json:213` | `"#582007",` |

### `#590e2c`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:213` | `"#590E2C",` |

### `#5a4f85`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:87` | `400: "#A396CB", 500: "#897CB2", 600: "#71659B", 700: "#5A4F85",` |
| `themes/davipa.json:259` | `"#5A4F85"` |

### `#5c0015`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:78` | `800: "#850023", 900: "#5C0015", 950: "#3D0005",` |

### `#5c13da`

| File:Line | Snippet |
|---|---|
| `themes/purple.json:39` | `"#5C13DA"` |
| `themes/purple.json:95` | `"#5C13DA"` |
| `themes/purple.json:153` | `"#5C13DA"` |
| `themes/purple.json:199` | `"#5C13DA"` |
| `themes/purple.json:210` | `"#5C13DA"` |
| `themes/purple.json:279` | `"#5C13DA"` |

### `#5d0000`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:58` | `800: "#86000E", 900: "#5D0000", 950: "#350B00",` |

### `#5e42b4`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:62` | `400: "#AD8BF9", 500: "#9170E0", 600: "#7859CA", 700: "#5E42B4",` |

### `#6430a9`

| File:Line | Snippet |
|---|---|
| `themes/purple.json:214` | `"#6430A9"` |

### `#64748b`

| File:Line | Snippet |
|---|---|
| `docs/spec_coverage.md:1964` | `\| SCV-M2.1 \| `_derive_subsegment_color` raises for nothing a caller can hold, and falls back to `#64748B` where it cannot read a base \| `vps_manager.py::VPSManager._derive_subse` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:56` | `\| `#64748B` slate \| **white** \| 4.76 \| 3.71 \| 3.66 \|` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:81` | `### 3 · A slate `#64748B` row flips to white text in the light theme` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:59` | `3. **A slate `#64748B` row, light theme:** text flips to **white**. The` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:60` | `\| SCV-M2.1 \| `_derive_subsegment_color` raises nothing for any string, and falls back to `#64748B` where it cannot read one \| `::test_scvm21_deriving_from_a_malformed_colour_fal` |
| `src/getmoredone/screens/settings_vsp_segments.py:250` | `color_hex = subsegment.get("color_hex") or "#64748B"` |
| `src/getmoredone/screens/settings_vsp_segments.py:280` | `initial = subsegment.get("color_hex") or "#64748B"` |
| `src/getmoredone/vps_manager.py:160` | `DEFAULT_SUBSEGMENT_BASE = "#64748B"` |
| `src/getmoredone/vps_manager.py:1511` | `return "#64748B"` |
| `src/getmoredone/vps_manager_taxonomy.py:396` | `sub_color = (sub_row["color_hex"] if sub_row else "") or "#64748B"` |
| `tests/test_segment_colour_validation.py:28` | `FALLBACK_BASE = "#64748B"` |
| `tests/test_segment_colour_validation.py:273` | ```#64748B -> #9399AE`` are the values measured against the ``6963d0a``` |
| `tests/test_segment_colour_validation.py:802` | ```#64748B`` for a segment with no ``segment_descriptions`` row at all.` |
| `tests/test_segment_colour_validation.py:957` | ```False``, ``_derive_subsegment_color`` fell back to ``#64748B``, and that` |

### `#654321`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:490` | `settings.priority_level_color_no_high_or_critical = "#654321"` |
| `tests/test_vps_segments.py:220` | `segment_id, name="Renamed", color_hex="#654321", order_index=98) is True` |
| `tests/test_vps_segments.py:223` | `assert stored["color_hex"] == "#654321"` |

### `#67220b`

| File:Line | Snippet |
|---|---|
| `themes/orange.json:39` | `"#67220B"` |
| `themes/orange.json:95` | `"#67220B"` |
| `themes/orange.json:153` | `"#67220B"` |
| `themes/orange.json:199` | `"#67220B"` |
| `themes/orange.json:210` | `"#67220B"` |
| `themes/orange.json:279` | `"#67220B"` |

### `#673ab7`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1167` | `('seg-9', 'Personal Growth', 'Self-improvement and spirituality', '#673AB7', 9),` |

### `#6825e8`

| File:Line | Snippet |
|---|---|
| `themes/purple.json:38` | `"#6825E8",` |
| `themes/purple.json:94` | `"#6825E8",` |
| `themes/purple.json:152` | `"#6825E8",` |
| `themes/purple.json:198` | `"#6825E8",` |
| `themes/purple.json:209` | `"#6825E8",` |
| `themes/purple.json:278` | `"#6825E8",` |

### `#691e71`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:68` | `800: "#691E71", 900: "#4E0157", 950: "#330039",` |
| `themes/davipa.json:213` | `"#691E71",` |
| `themes/davipa.json:214` | `"#691E71"` |
| `themes/davipa.json:241` | `"#691E71",` |
| `themes/davipa.json:242` | `"#691E71"` |

### `#6b0f34`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:39` | `"#6B0F34"` |
| `themes/pink.json:95` | `"#6B0F34"` |
| `themes/pink.json:153` | `"#6B0F34"` |
| `themes/pink.json:199` | `"#6B0F34"` |
| `themes/pink.json:210` | `"#6B0F34"` |
| `themes/pink.json:279` | `"#6B0F34"` |

### `#6b2f00`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:83` | `800: "#6B2F00", 900: "#461F00", 950: "#2A1400",` |

### `#6b7280`

| File:Line | Snippet |
|---|---|
| `themes/black_white.json:71` | `"#6B7280"` |
| `themes/black_white.json:78` | `"#6B7280",` |
| `tools/generate_ctk_themes.py:81` | `("CTkEntry", "border_color"): ["#9CA3AF", "#6B7280"],` |
| `tools/generate_ctk_themes.py:83` | `("CTkEntry", "placeholder_text_color"): ["#6B7280", "#9CA3AF"],` |

### `#6bcb77`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:268` | `"low_load": "#6BCB77",` |

### `#6e6799`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:92` | `400: "#A098C9", 500: "#867DAF", 600: "#6E6799", 700: "#575183",` |

### `#6e6e73`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:51` | `"#6E6E73"` |
| `themes/apple_grey.json:78` | `"#6E6E73",` |
| `themes/apple_grey.json:107` | `"#6E6E73"` |
| `themes/apple_grey.json:136` | `"#6E6E73"` |
| `themes/apple_grey.json:161` | `"#6E6E73"` |
| `themes/apple_grey.json:222` | `"#6E6E73"` |
| `themes/apple_grey.json:250` | `"#6E6E73"` |
| `themes/apple_grey.json:295` | `"#6E6E73"` |
| `themes/black_white.json:51` | `"#6E6E73"` |
| `themes/black_white.json:107` | `"#6E6E73"` |
| `themes/black_white.json:136` | `"#6E6E73"` |
| `themes/black_white.json:161` | `"#6E6E73"` |
| `themes/black_white.json:222` | `"#6E6E73"` |
| `themes/black_white.json:250` | `"#6E6E73"` |
| `themes/black_white.json:295` | `"#6E6E73"` |
| `tools/generate_ctk_themes.py:70` | `("CTkEntry", "placeholder_text_color"): ["#6E6E73", "#A1A1A6"],` |
| `tools/generate_ctk_themes.py:176` | `widget_cfg["text_color_disabled"] = ["#86868B", "#6E6E73"]` |

### `#6e7174`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:241` | `"#6E7174",` |
| `themes/base_dark_blue.json:99` | `"button_hover_color": ["#6E7174", "#7A848D"],` |
| `themes/black_white.json:241` | `"#6E7174",` |
| `themes/blue.json:241` | `"#6E7174",` |
| `themes/green.json:241` | `"#6E7174",` |
| `themes/grey.json:241` | `"#6E7174",` |
| `themes/orange.json:241` | `"#6E7174",` |
| `themes/pink.json:241` | `"#6E7174",` |
| `themes/purple.json:241` | `"#6E7174",` |

### `#71659b`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:87` | `400: "#A396CB", 500: "#897CB2", 600: "#71659B", 700: "#5A4F85",` |
| `themes/davipa.json:263` | `"#71659B"` |

### `#71717a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:344` | `"unscored": "#71717A",` |

### `#767676`

| File:Line | Snippet |
|---|---|
| `tests/test_color_contrast.py:26` | `assert meets_wcag("#767676", "#FFFFFF", large_text=False)` |
| `tests/test_color_contrast.py:27` | `assert meets_wcag("#767676", "#FFFFFF", large_text=True)` |

### `#777777`

| File:Line | Snippet |
|---|---|
| `tests/test_color_contrast.py:21` | `assert math.isclose(contrast_ratio("#777777", "#FFFFFF"), 4.48, rel_tol=0.0, abs_tol=0.03)` |
| `tests/test_color_contrast.py:28` | `assert not meets_wcag("#777777", "#FFFFFF", large_text=False)` |
| `tests/test_color_contrast.py:34` | `first = pick_text_color_with_meta("#7A7A7A", light="#888888", dark="#777777")` |
| `tests/test_color_contrast.py:35` | `second = pick_text_color_with_meta("#7A7A7A", light="#888888", dark="#777777")` |
| `tests/test_color_contrast.py:38` | `assert first.text_color in {"#888888", "#777777"}` |

### `#778899`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:319` | `settings.priority_level_color_no_high_or_critical = "#778899"` |
| `tests/test_priority_level_colors.py:325` | `assert reloaded.priority_level_color_no_high_or_critical == "#778899"` |

### `#78006e`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:73` | `800: "#78006E", 900: "#52004B", 950: "#360031",` |

### `#7859ca`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:62` | `400: "#AD8BF9", 500: "#9170E0", 600: "#7859CA", 700: "#5E42B4",` |

### `#7a173d`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:38` | `"#7A173D",` |
| `themes/pink.json:94` | `"#7A173D",` |
| `themes/pink.json:152` | `"#7A173D",` |
| `themes/pink.json:198` | `"#7A173D",` |
| `themes/pink.json:209` | `"#7A173D",` |
| `themes/pink.json:278` | `"#7A173D",` |

### `#7a7a7a`

| File:Line | Snippet |
|---|---|
| `tests/test_color_contrast.py:34` | `first = pick_text_color_with_meta("#7A7A7A", light="#888888", dark="#777777")` |
| `tests/test_color_contrast.py:35` | `second = pick_text_color_with_meta("#7A7A7A", light="#888888", dark="#777777")` |

### `#7a848d`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:242` | `"#7A848D"` |
| `themes/base_dark_blue.json:99` | `"button_hover_color": ["#6E7174", "#7A848D"],` |
| `themes/black_white.json:242` | `"#7A848D"` |
| `themes/blue.json:242` | `"#7A848D"` |
| `themes/green.json:242` | `"#7A848D"` |
| `themes/grey.json:242` | `"#7A848D"` |
| `themes/orange.json:242` | `"#7A848D"` |
| `themes/pink.json:242` | `"#7A848D"` |
| `themes/purple.json:242` | `"#7A848D"` |

### `#7b320e`

| File:Line | Snippet |
|---|---|
| `themes/orange.json:38` | `"#7B320E",` |
| `themes/orange.json:94` | `"#7B320E",` |
| `themes/orange.json:152` | `"#7B320E",` |
| `themes/orange.json:198` | `"#7B320E",` |
| `themes/orange.json:209` | `"#7B320E",` |
| `themes/orange.json:278` | `"#7B320E",` |

### `#7c3aed`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:453` | `"TL Vision": "#7C3AED",` |
| `tests/test_vps_subsegment_colors.py:35` | `ok = manager.update_vision_subsegment_color(row["id"], "#7C3AED")` |
| `tests/test_vps_subsegment_colors.py:38` | `assert updated["color_hex"] == "#7C3AED"` |
| `themes/purple.json:35` | `"#7C3AED"` |
| `themes/purple.json:87` | `"#7C3AED"` |
| `themes/purple.json:120` | `"#7C3AED"` |
| `themes/purple.json:145` | `"#7C3AED"` |
| `themes/purple.json:173` | `"#7C3AED"` |
| `themes/purple.json:195` | `"#7C3AED"` |
| `themes/purple.json:206` | `"#7C3AED"` |
| `themes/purple.json:275` | `"#7C3AED"` |
| `tools/generate_ctk_themes.py:49` | `"purple": ["#8B5CF6", "#7C3AED"],` |

### `#7f7f7f`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:696` | `for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1192` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#7F7F7F", "#450A0A"):` |

### `#808080`

| File:Line | Snippet |
|---|---|
| `tests/test_drag_schedule_support.py:30` | `assert interpolate_hex_color("#000000", "#FFFFFF", 0.5) == "#808080"` |
| `tests/test_vps_integration.py:1589` | `color_hex="#808080",` |

### `#813389`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:35` | `VIOLET = "#813389"` |
| `src/getmoredone/brand.py:67` | `400: "#CE83D3", 500: "#B368B9", 600: "#9C4FA2", 700: "#813389",` |
| `themes/davipa.json:38` | `"#813389",` |
| `themes/davipa.json:39` | `"#813389"` |
| `themes/davipa.json:209` | `"#813389",` |
| `themes/davipa.json:210` | `"#813389"` |
| `themes/davipa.json:237` | `"#813389",` |
| `themes/davipa.json:238` | `"#813389"` |
| `themes/davipa.json:278` | `"#813389",` |
| `themes/davipa.json:279` | `"#813389"` |
| `themes/davipa.json:335` | `"#813389"` |

### `#813798`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:106` | `TILE_GRADIENT = (DEEP_INK, INDIGO, "#813798", "#FD915B")` |

### `#850023`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:78` | `800: "#850023", 900: "#5C0015", 950: "#3D0005",` |

### `#86000e`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:58` | `800: "#86000E", 900: "#5D0000", 950: "#350B00",` |

### `#867daf`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:92` | `400: "#A098C9", 500: "#867DAF", 600: "#6E6799", 700: "#575183",` |

### `#86868b`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:50` | `"#86868B",` |
| `themes/apple_grey.json:106` | `"#86868B",` |
| `themes/apple_grey.json:135` | `"#86868B",` |
| `themes/apple_grey.json:160` | `"#86868B",` |
| `themes/apple_grey.json:221` | `"#86868B",` |
| `themes/apple_grey.json:249` | `"#86868B",` |
| `themes/apple_grey.json:294` | `"#86868B",` |
| `themes/black_white.json:50` | `"#86868B",` |
| `themes/black_white.json:106` | `"#86868B",` |
| `themes/black_white.json:135` | `"#86868B",` |
| `themes/black_white.json:160` | `"#86868B",` |
| `themes/black_white.json:221` | `"#86868B",` |
| `themes/black_white.json:249` | `"#86868B",` |
| `themes/black_white.json:294` | `"#86868B",` |
| `tools/generate_ctk_themes.py:176` | `widget_cfg["text_color_disabled"] = ["#86868B", "#6E6E73"]` |

### `#86efac`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:262` | `"date_today": "#86EFAC",` |
| `tests/test_vision_planning_regressions.py:54` | `assert screen._date_background_for(today.strftime("%Y-%m-%d")) == "#86EFAC"` |

### `#888888`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/vision_planning.py:280` | `color = item.get('segment_color') or "#888888"` |
| `src/getmoredone/screens/vision_planning.py:542` | `color = item.get('segment_color') or "#888888"` |
| `src/getmoredone/screens/vision_planning.py:561` | `color = item.get('segment_color') or "#888888"` |
| `tests/test_color_contrast.py:34` | `first = pick_text_color_with_meta("#7A7A7A", light="#888888", dark="#777777")` |
| `tests/test_color_contrast.py:35` | `second = pick_text_color_with_meta("#7A7A7A", light="#888888", dark="#777777")` |
| `tests/test_color_contrast.py:38` | `assert first.text_color in {"#888888", "#777777"}` |

### `#897cb2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:87` | `400: "#A396CB", 500: "#897CB2", 600: "#71659B", 700: "#5A4F85",` |

### `#8b0000`

| File:Line | Snippet |
|---|---|
| `docs/VPS_DELETION_SAFETY.md:98` | `- Red warning box (color: `#8B0000`)` |

### `#8b5cf6`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:53` | `\| `#8B5CF6` violet \| black \| 4.96 \| 3.30 \| 4.11 \|` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |
| `themes/purple.json:34` | `"#8B5CF6",` |
| `themes/purple.json:86` | `"#8B5CF6",` |
| `themes/purple.json:119` | `"#8B5CF6",` |
| `themes/purple.json:144` | `"#8B5CF6",` |
| `themes/purple.json:172` | `"#8B5CF6",` |
| `themes/purple.json:194` | `"#8B5CF6",` |
| `themes/purple.json:205` | `"#8B5CF6",` |
| `themes/purple.json:274` | `"#8B5CF6",` |
| `tools/generate_ctk_themes.py:49` | `"purple": ["#8B5CF6", "#7C3AED"],` |

### `#8bc34a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1165` | `('seg-7', 'Contribution', 'Giving back and community involvement', '#8BC34A', 7),` |

### `#8f4000`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:82` | `400: "#EA833E", 500: "#C96A28", 600: "#AC5515", 700: "#8F4000",` |

### `#9170e0`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:62` | `400: "#AD8BF9", 500: "#9170E0", 600: "#7859CA", 700: "#5E42B4",` |

### `#92400e`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-06_plan_box_appearance.md:40` | ``#92400E`, `#166534`) so they clear **4.5:1** against `surface_subtle`. The` |
| `src/getmoredone/theme.py:305` | `"medium": "#92400E",` |

### `#9399ae`

| File:Line | Snippet |
|---|---|
| `tests/test_segment_colour_validation.py:273` | ```#64748B -> #9399AE`` are the values measured against the ``6963d0a``` |
| `tests/test_segment_colour_validation.py:277` | `assert _derive(FALLBACK_BASE) == "#9399AE"` |

### `#939ba2`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:115` | `"#939BA2",` |
| `themes/apple_grey.json:168` | `"#939BA2",` |
| `themes/apple_grey.json:186` | `"#939BA2",` |
| `themes/base_dark_blue.json:51` | `"fg_color": ["#939BA2", "#4A4D50"],` |
| `themes/base_dark_blue.json:71` | `"fg_color": ["#939BA2", "#4A4D50"],` |
| `themes/base_dark_blue.json:80` | `"fg_color": ["#939BA2", "#4A4D50"],` |
| `themes/black_white.json:115` | `"#939BA2",` |
| `themes/black_white.json:168` | `"#939BA2",` |
| `themes/black_white.json:186` | `"#939BA2",` |
| `themes/blue.json:115` | `"#939BA2",` |
| `themes/blue.json:168` | `"#939BA2",` |
| `themes/blue.json:186` | `"#939BA2",` |
| `themes/green.json:115` | `"#939BA2",` |
| `themes/green.json:168` | `"#939BA2",` |
| `themes/green.json:186` | `"#939BA2",` |
| `themes/grey.json:115` | `"#939BA2",` |
| `themes/grey.json:168` | `"#939BA2",` |
| `themes/grey.json:186` | `"#939BA2",` |
| `themes/orange.json:115` | `"#939BA2",` |
| `themes/orange.json:168` | `"#939BA2",` |
| `themes/orange.json:186` | `"#939BA2",` |
| `themes/pink.json:115` | `"#939BA2",` |
| `themes/pink.json:168` | `"#939BA2",` |
| `themes/pink.json:186` | `"#939BA2",` |
| `themes/purple.json:115` | `"#939BA2",` |
| `themes/purple.json:168` | `"#939BA2",` |
| `themes/purple.json:186` | `"#939BA2",` |

### `#949a9f`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:43` | `"#949A9F"` |
| `themes/apple_grey.json:91` | `"#949A9F"` |
| `themes/apple_grey.json:149` | `"#949A9F"` |
| `themes/base_dark_blue.json:20` | `"border_color": ["#3E454A", "#949A9F"],` |
| `themes/base_dark_blue.json:41` | `"border_color": ["#3E454A", "#949A9F"],` |
| `themes/base_dark_blue.json:63` | `"border_color": ["#3E454A", "#949A9F"],` |
| `themes/black_white.json:43` | `"#949A9F"` |
| `themes/black_white.json:91` | `"#949A9F"` |
| `themes/black_white.json:149` | `"#949A9F"` |
| `themes/blue.json:43` | `"#949A9F"` |
| `themes/blue.json:91` | `"#949A9F"` |
| `themes/blue.json:149` | `"#949A9F"` |
| `themes/green.json:43` | `"#949A9F"` |
| `themes/green.json:91` | `"#949A9F"` |
| `themes/green.json:149` | `"#949A9F"` |
| `themes/grey.json:43` | `"#949A9F"` |
| `themes/grey.json:91` | `"#949A9F"` |
| `themes/grey.json:149` | `"#949A9F"` |
| `themes/orange.json:43` | `"#949A9F"` |
| `themes/orange.json:91` | `"#949A9F"` |
| `themes/orange.json:149` | `"#949A9F"` |
| `themes/pink.json:43` | `"#949A9F"` |
| `themes/pink.json:91` | `"#949A9F"` |
| `themes/pink.json:149` | `"#949A9F"` |
| `themes/purple.json:43` | `"#949A9F"` |
| `themes/purple.json:91` | `"#949A9F"` |
| `themes/purple.json:149` | `"#949A9F"` |

### `#94a3b8`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/vision_segments.py:518` | `color_row, color = self._color_input(f, (row or {}).get("color_hex", "#94A3B8"))` |
| `src/getmoredone/theme.py:314` | `"unscored": "#94A3B8",` |

### `#97208c`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:72` | `400: "#EA6FDA", 500: "#D051C1", 600: "#B339A6", 700: "#97208C",` |

### `#979da2`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:233` | `"#979DA2",` |
| `themes/apple_grey.json:237` | `"#979DA2",` |
| `themes/apple_grey.json:270` | `"#979DA2",` |
| `themes/apple_grey.json:282` | `"#979DA2",` |
| `themes/apple_grey.json:306` | `"#979DA2",` |
| `themes/base_dark_blue.json:33` | `"border_color": ["#979DA2", "#565B5E"],` |
| `themes/base_dark_blue.json:97` | `"border_color": ["#979DA2", "#565B5E"],` |
| `themes/base_dark_blue.json:98` | `"button_color": ["#979DA2", "#565B5E"],` |
| `themes/base_dark_blue.json:113` | `"fg_color": ["#979DA2", "gray29"],` |
| `themes/base_dark_blue.json:116` | `"unselected_color": ["#979DA2", "gray29"],` |
| `themes/base_dark_blue.json:125` | `"border_color": ["#979DA2", "#565B5E"],` |
| `themes/black_white.json:233` | `"#979DA2",` |
| `themes/black_white.json:237` | `"#979DA2",` |
| `themes/black_white.json:270` | `"#979DA2",` |
| `themes/black_white.json:282` | `"#979DA2",` |
| `themes/black_white.json:306` | `"#979DA2",` |
| `themes/blue.json:70` | `"#979DA2",` |
| `themes/blue.json:233` | `"#979DA2",` |
| `themes/blue.json:237` | `"#979DA2",` |
| `themes/blue.json:270` | `"#979DA2",` |
| `themes/blue.json:282` | `"#979DA2",` |
| `themes/blue.json:306` | `"#979DA2",` |
| `themes/green.json:70` | `"#979DA2",` |
| `themes/green.json:233` | `"#979DA2",` |
| `themes/green.json:237` | `"#979DA2",` |
| `themes/green.json:270` | `"#979DA2",` |
| `themes/green.json:282` | `"#979DA2",` |
| `themes/green.json:306` | `"#979DA2",` |
| `themes/grey.json:70` | `"#979DA2",` |
| `themes/grey.json:233` | `"#979DA2",` |
| `themes/grey.json:237` | `"#979DA2",` |
| `themes/grey.json:270` | `"#979DA2",` |
| `themes/grey.json:282` | `"#979DA2",` |
| `themes/grey.json:306` | `"#979DA2",` |
| `themes/orange.json:70` | `"#979DA2",` |
| `themes/orange.json:233` | `"#979DA2",` |
| `themes/orange.json:237` | `"#979DA2",` |
| `themes/orange.json:270` | `"#979DA2",` |
| `themes/orange.json:282` | `"#979DA2",` |
| `themes/orange.json:306` | `"#979DA2",` |
| `themes/pink.json:70` | `"#979DA2",` |
| `themes/pink.json:233` | `"#979DA2",` |
| `themes/pink.json:237` | `"#979DA2",` |
| `themes/pink.json:270` | `"#979DA2",` |
| `themes/pink.json:282` | `"#979DA2",` |
| `themes/pink.json:306` | `"#979DA2",` |
| `themes/purple.json:70` | `"#979DA2",` |
| `themes/purple.json:233` | `"#979DA2",` |
| `themes/purple.json:237` | `"#979DA2",` |
| `themes/purple.json:270` | `"#979DA2",` |
| `themes/purple.json:282` | `"#979DA2",` |
| `themes/purple.json:306` | `"#979DA2",` |

### `#991b1b`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-05-time-blocks.md:112` | `changed to `#991B1B` (5.33). The earlier measurement had used the lighter` |
| `docs/unused-docs/implementation_plan_2026-11-06_plan_box_appearance.md:39` | `The light theme's band colours are deliberately dark (`#991B1B`, `#9A3412`,` |
| `src/getmoredone/theme.py:132` | `"danger_hover": "#991B1B",` |
| `src/getmoredone/theme.py:303` | `"critical": "#991B1B",` |

### `#9a3412`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-06_plan_box_appearance.md:39` | `The light theme's band colours are deliberately dark (`#991B1B`, `#9A3412`,` |
| `src/getmoredone/theme.py:304` | `"high": "#9A3412",` |
| `themes/orange.json:35` | `"#9A3412"` |
| `themes/orange.json:87` | `"#9A3412"` |
| `themes/orange.json:120` | `"#9A3412"` |
| `themes/orange.json:145` | `"#9A3412"` |
| `themes/orange.json:173` | `"#9A3412"` |
| `themes/orange.json:195` | `"#9A3412"` |
| `themes/orange.json:206` | `"#9A3412"` |
| `themes/orange.json:275` | `"#9A3412"` |
| `tools/generate_ctk_themes.py:45` | `"orange": ["#C2410C", "#9A3412"],` |

### `#9c27b0`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1161` | `('seg-3', 'Skills - Cognitive', 'Learning and intellectual development', '#9C27B0', 3),` |

### `#9c4fa2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:67` | `400: "#CE83D3", 500: "#B368B9", 600: "#9C4FA2", 700: "#813389",` |

### `#9ca3af`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md:184` | `(`#4B5563` light / `#9CA3AF` dark); only `break` differs (`#155E75` / `#22D3EE`).` |
| `src/getmoredone/theme.py:440` | `padding = "#4B5563" if mode == "light" else "#9CA3AF"` |
| `themes/black_white.json:70` | `"#9CA3AF",` |
| `themes/black_white.json:79` | `"#9CA3AF"` |
| `tools/generate_ctk_themes.py:81` | `("CTkEntry", "border_color"): ["#9CA3AF", "#6B7280"],` |
| `tools/generate_ctk_themes.py:83` | `("CTkEntry", "placeholder_text_color"): ["#6B7280", "#9CA3AF"],` |

### `#9d174d`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:35` | `"#9D174D"` |
| `themes/pink.json:87` | `"#9D174D"` |
| `themes/pink.json:120` | `"#9D174D"` |
| `themes/pink.json:145` | `"#9D174D"` |
| `themes/pink.json:173` | `"#9D174D"` |
| `themes/pink.json:195` | `"#9D174D"` |
| `themes/pink.json:206` | `"#9D174D"` |
| `themes/pink.json:275` | `"#9D174D"` |
| `tools/generate_ctk_themes.py:46` | `"pink": ["#BE185D", "#9D174D"],` |

### `#a098c9`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:92` | `400: "#A098C9", 500: "#867DAF", 600: "#6E6799", 700: "#575183",` |

### `#a0b0c0`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:195` | `(`#AABBCC`) while Tk draws the X11 one (`#A0B0C0`). Same black/white answer` |

### `#a1a1a6`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:79` | `"#A1A1A6"` |
| `tools/generate_ctk_themes.py:70` | `("CTkEntry", "placeholder_text_color"): ["#6E6E73", "#A1A1A6"],` |

### `#a396cb`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:87` | `400: "#A396CB", 500: "#897CB2", 600: "#71659B", 700: "#5A4F85",` |

### `#a855f7`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:465` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

### `#aab0b5`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:191` | `"#AAB0B5"` |
| `themes/base_dark_blue.json:81` | `"progress_color": ["gray40", "#AAB0B5"],` |
| `themes/black_white.json:191` | `"#AAB0B5"` |
| `themes/blue.json:191` | `"#AAB0B5"` |
| `themes/green.json:191` | `"#AAB0B5"` |
| `themes/grey.json:191` | `"#AAB0B5"` |
| `themes/orange.json:191` | `"#AAB0B5"` |
| `themes/pink.json:191` | `"#AAB0B5"` |
| `themes/purple.json:191` | `"#AAB0B5"` |

### `#aabbcc`

| File:Line | Snippet |
|---|---|
| `docs/DOCUMENTATION_INDEX.md:437` | `and only together with storing the normalised `#AABBCC`` |
| `docs/USER_GUIDE.md:929` | `and saved as `#AABBCC`, and the field refuses anything that is not six hex` |
| `docs/spec_coverage.md:1963` | `\| SCV-M1.3 \| The editor stores the normalised form, so `#abc` lands as `#AABBCC` \| `screens/vps_segment_editor.py::VPSSegmentEditorDialog.save_segment` \| `::test_scvm13_the_edi` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:195` | `(`#AABBCC`) while Tk draws the X11 one (`#A0B0C0`). Same black/white answer` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:199` | `now the normalised `#AABBCC`, so Tk draws what the text colour was derived` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:105` | `closes, and re-opening the editor on that segment shows `#AABBCC`.` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:96` | `holding `#abc` to `#AABBCC`. One write per such row, once; the condition is` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:131` | `closes, and re-opening the editor on that segment shows `#AABBCC` in the` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:91` | `decided it — but only together with storing the normalised `#AABBCC`. Accepting` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:115` | `2. Type `#abc` and save: accepted, and the stored value reads back `#AABBCC`.` |
| `tests/test_color_inventory_sync.py:38` | `#   * `#aabbcc` and `#ddeeff` tie at two hex occurrences each` |
| `tests/test_color_inventory_sync.py:45` | `"src/b.py:10:    fg_color=\"#aabbcc\"",` |
| `tests/test_color_inventory_sync.py:47` | `"src/c.py:5:     border_color=\"#aabbcc\"",` |
| `tests/test_color_inventory_sync.py:58` | `"src/b.py:10:    fg_color=\"#aabbcc\"",` |
| `tests/test_priority_level_colors.py:397` | `assert level_color(settings, LEVEL_ANY_HIGH) == "#AABBCC"` |
| `tests/test_priority_level_colors.py:1229` | `assert short.text_color == pick_text_color("#AABBCC")` |
| `tests/test_priority_level_colors.py:1606` | `("#ABC", "#AABBCC"), ("#abc", "#AABBCC")):` |
| `tests/test_segment_colour_validation.py:159` | `("#abc", "#AABBCC"),` |
| `tests/test_segment_colour_validation.py:367` | ```#AABBCC`` by the read that checked it. Corrected 2026-11-11 after a cold` |
| `tests/test_segment_colour_validation.py:385` | `assert stored("vision_subsegments", sub["id"]) == "#AABBCC"` |
| `tests/test_segment_colour_validation.py:393` | `assert stored("vision_categories", cat["id"]) == "#AABBCC"` |
| `tests/test_segment_colour_validation.py:431` | `assert manager.get_segment(created)["color_hex"] == "#AABBCC"` |
| `tests/test_segment_colour_validation.py:471` | `assert colours["scv admin"] == "#AABBCC"` |
| `tests/test_segment_colour_validation.py:476` | `assert manager.get_segment_color_map()["scv admin"] == "#AABBCC"` |
| `tests/test_segment_colour_validation.py:543` | `assert stored["Scv Short"] == "#AABBCC", stored` |
| `tests/test_segment_colour_validation.py:566` | `assert stored["Scv Short"] == "#AABBCC", stored` |
| `tests/test_segment_colour_validation.py:654` | `assert _normalize_color("#abc") == "#AABBCC"` |
| `tests/test_segment_colour_validation.py:655` | `assert _normalize_color("  #aabbcc  ") == "#AABBCC"` |
| `tests/test_vps_segments.py:173` | `@pytest.mark.parametrize("value", ["#000000", "#ffffff", "#AABBCC", "#1a2b3c"])` |
| `tests/test_vps_segments.py:192` | `stores the normalised ``#AABBCC``, asserted by` |

### `#abc`

| File:Line | Snippet |
|---|---|
| `docs/DOCUMENTATION_INDEX.md:436` | `- Delegating widens the segment editor to accept `#abc`, taken deliberately` |
| `docs/USER_GUIDE.md:928` | `Upcoming and All Items. Since 2026-11-11 the short form `#abc` is accepted` |
| `docs/spec_coverage.md:1963` | `\| SCV-M1.3 \| The editor stores the normalised form, so `#abc` lands as `#AABBCC` \| `screens/vps_segment_editor.py::VPSSegmentEditorDialog.save_segment` \| `::test_scvm13_the_edi` |
| `docs/spec_coverage.md:2009` | `no longer lists `#abc` and `aabbcc` as refusals (SCV-M1.3, plan §4), and` |
| `docs/spec_coverage.md:2050` | `was mutation-proved red at `#ABC`. `::test_scvm66_the_category_pass_does_not_requery_per_row`` |
| `docs/unused-docs/changes/2026-11-08-priority-level-colours.md:51` | `rather than raises and expands `#ABC`` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:194` | `- A 3-digit segment colour (`#ABC`) derives its text from the CSS expansion` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:104` | `11. **Same dialog, type `#abc` and Save.** Expect: accepted, the dialog` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:106` | `Before 2026-11-11 `#abc` was refused.` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:96` | `holding `#abc` to `#AABBCC`. One write per such row, once; the condition is` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:130` | `2. **Same dialog, type `#abc` and Save.** Expected: accepted, the dialog` |
| `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md:132` | `field. Before 2026-11-11 `#abc` was refused.` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:227` | `three-digit `#ABC` is expanded; a value that is still not `#RRGGBB` is` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:59` | `\| SCV-M1.3 \| What the editor **stores** is the normalised form, not the typed text, so `#abc` and `#AbC123` land as `#RRGGBB` \| `::test_scvm13_the_editor_stores_the_normalised_f` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:88` | ``len() == 7` today, so `#abc` is refused; `normalize_hex_color` expands the` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:89` | `three-digit form. Delegating therefore makes `#abc` valid. That is accepted` |
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:115` | `2. Type `#abc` and save: accepted, and the stored value reads back `#AABBCC`.` |
| `src/getmoredone/color_contrast.py:50` | `exception. A three-digit ``#ABC`` is expanded, because that is a form people` |
| `src/getmoredone/screens/vps_segment_editor.py:216` | `Accepts ``#abc`` and a missing ``#``, which the old check refused --` |
| `src/getmoredone/screens/vps_segment_editor.py:242` | `# text. ``validate_color`` accepts ``#abc`` and a missing ``#``, and` |
| `src/getmoredone/vps_manager.py:206` | ```normalize_hex_color`` expands ``#abc`` and supplies a missing ``#``.` |
| `src/getmoredone/vps_manager_taxonomy.py:356` | `# typed; once that gate reads ``#abc`` and ``abcdef``, both became` |
| `src/getmoredone/vps_manager_taxonomy.py:449` | `gate reads ``#abc``, storing the text as given would write a` |
| `tests/test_priority_level_colors.py:394` | `settings_field_name(LEVEL_ANY_HIGH): "#abc",` |
| `tests/test_priority_level_colors.py:1227` | `segment_color="#ABC",` |
| `tests/test_priority_level_colors.py:1606` | `("#ABC", "#AABBCC"), ("#abc", "#AABBCC")):` |
| `tests/test_segment_colour_validation.py:159` | `("#abc", "#AABBCC"),` |
| `tests/test_segment_colour_validation.py:168` | `Delegating to ``normalize_hex_color`` widens the editor: ``#abc`` was` |
| `tests/test_segment_colour_validation.py:261` | `for value in ("#abc", "\t#123456\n", "AABBCC"):` |
| `tests/test_segment_colour_validation.py:358` | ```(color_hex or "").strip().upper()``. Delegating the gate makes ``#abc``` |
| `tests/test_segment_colour_validation.py:359` | `pass it, so without this the three of them would write ``#ABC`` -- a` |
| `tests/test_segment_colour_validation.py:366` | ```.strip().upper()``, because the ``#ABC`` they stored was rewritten to` |
| `tests/test_segment_colour_validation.py:384` | `assert manager.update_vision_subsegment_color(sub["id"], "#abc") is True` |
| `tests/test_segment_colour_validation.py:392` | `cat["id"], "Scv Cat", "#abc", "", "") is True` |
| `tests/test_segment_colour_validation.py:430` | `created = manager.create_segment("Scv Store", "desc", "#abc", 97)` |
| `tests/test_segment_colour_validation.py:467` | `"Scv Admin", "desc", "#abc", "vision")` |
| `tests/test_segment_colour_validation.py:519` | `gate to ``normalize_hex_color`` turned them from "reject ``#abc``, use the` |
| `tests/test_segment_colour_validation.py:520` | `derived default" into "accept ``#abc``, write it verbatim" -- a regression` |
| `tests/test_segment_colour_validation.py:532` | `manager.create_vision_subsegment(seg_name, "Scv Short", color_hex="#abc")` |
| `tests/test_segment_colour_validation.py:561` | `manager.create_vision_category(seg_name, "Scv Sub", "Scv Short", color_hex="#abc")` |
| `tests/test_segment_colour_validation.py:634` | `apply_segment_accent(frame, "#abc")` |
| `tests/test_segment_colour_validation.py:654` | `assert _normalize_color("#abc") == "#AABBCC"` |
| `tests/test_vps_segments.py:189` | ```"#abc"``, the three-digit form the normaliser expands, and ``"aabbcc"``,` |
| `tests/test_vps_segments.py:198` | `@pytest.mark.parametrize("value", ["#abc", "aabbcc"])` |

### `#abc123`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md:59` | `\| SCV-M1.3 \| What the editor **stores** is the normalised form, not the typed text, so `#abc` and `#AbC123` land as `#RRGGBB` \| `::test_scvm13_the_editor_stores_the_normalised_f` |
| `tests/test_segment_colour_validation.py:160` | `("#AbC123", "#ABC123"),` |
| `tests/test_segment_colour_validation.py:161` | `("  #abc123  ", "#ABC123"),` |
| `tests/test_segment_colour_validation.py:433` | `assert manager.update_segment(created, color_hex="#AbC123") is True` |
| `tests/test_segment_colour_validation.py:434` | `assert manager.get_segment(created)["color_hex"] == "#ABC123"` |
| `tests/test_segment_colour_validation.py:442` | `assert manager.get_segment(created)["color_hex"] == "#ABC123"` |
| `tests/test_segment_colour_validation.py:446` | `assert manager.get_segment(created)["color_hex"] == "#ABC123"` |

### `#abcdef`

| File:Line | Snippet |
|---|---|
| `tests/test_drag_schedule_support.py:20` | `assert normalized_date_text_color("#ABCDEF") == "#ABCDEF"` |
| `tests/test_priority_level_colors.py:1111` | `stub.priority_level_color_vars[LEVEL_ANY_CRITICAL].set("#abcdef")` |
| `tests/test_priority_level_colors.py:1115` | `assert seen["color"] == "#ABCDEF"` |
| `tests/test_segment_colour_validation.py:544` | `assert stored["Scv Bare"] == "#ABCDEF", stored` |
| `tests/test_segment_colour_validation.py:567` | `assert stored["Scv Bare"] == "#ABCDEF", stored` |
| `tests/test_vps_integration.py:1634` | `valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#ABCDEF", "#123456"]` |

### `#ac5515`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:82` | `400: "#EA833E", 500: "#C96A28", 600: "#AC5515", 700: "#8F4000",` |

### `#ad1233`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:77` | `400: "#FF6F77", 500: "#F55161", 600: "#CB3046", 700: "#AD1233",` |

### `#ad8bf9`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:62` | `400: "#AD8BF9", 500: "#9170E0", 600: "#7859CA", 700: "#5E42B4",` |
| `themes/davipa.json:262` | `"#AD8BF9",` |

### `#adadad`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:214` | `"#ADADAD"` |

### `#b20016`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:57` | `400: "#FF7260", 500: "#F43E37", 600: "#DE1B24", 700: "#B20016",` |
| `themes/davipa.json:94` | `"#B20016",` |
| `themes/davipa.json:95` | `"#B20016"` |
| `themes/davipa.json:152` | `"#B20016",` |
| `themes/davipa.json:153` | `"#B20016"` |
| `themes/davipa.json:198` | `"#B20016",` |
| `themes/davipa.json:199` | `"#B20016"` |

### `#b339a6`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:72` | `400: "#EA6FDA", 500: "#D051C1", 600: "#B339A6", 700: "#97208C",` |

### `#b368b9`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:67` | `400: "#CE83D3", 500: "#B368B9", 600: "#9C4FA2", 700: "#813389",` |

### `#b3b3bc`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/backlog_archive_2026-11-09.md:1628` | `keeps `checkmark_color`, so apple_grey's dark hover `#B3B3BC` against a` |
| `themes/apple_grey.json:95` | `"#B3B3BC"` |
| `themes/apple_grey.json:153` | `"#B3B3BC"` |
| `themes/apple_grey.json:199` | `"#B3B3BC"` |
| `themes/apple_grey.json:210` | `"#B3B3BC"` |
| `themes/apple_grey.json:279` | `"#B3B3BC"` |

### `#b45309`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:134` | `"warning": "#B45309" if mode == "light" else "#FBBF24",` |
| `src/getmoredone/theme.py:342` | `"medium": "#B45309",` |

### `#b91c1c`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-05-time-blocks.md:110` | `- Reverting the light-theme `critical` band to `#B91C1C` turned the contrast` |
| `docs/unused-docs/changes/2026-11-07-plan-clear-day-and-marks.md:44` | `and #B91C1C/#FCA5A5 (unscheduled), and a test holds every combination of theme` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:111` | `red now, in the same red (`danger`, `#B91C1C`).` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:72` | ``#B91C1C`). The condition changed; for every value the UI can produce` |
| `src/getmoredone/screens/project_boards.py:1268` | `text_color="#B91C1C",` |
| `src/getmoredone/theme.py:131` | `"danger": "#B91C1C",` |
| `src/getmoredone/theme.py:151` | `"unscheduled_mark": "#B91C1C" if mode == "light" else "#FCA5A5",` |

### `#bcb3e3`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:91` | `50: "#F7F5FF", 100: "#EDE8FF", 200: "#D7CEFE", 300: "#BCB3E3",` |

### `#be185d`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:34` | `"#BE185D",` |
| `themes/pink.json:86` | `"#BE185D",` |
| `themes/pink.json:119` | `"#BE185D",` |
| `themes/pink.json:144` | `"#BE185D",` |
| `themes/pink.json:172` | `"#BE185D",` |
| `themes/pink.json:194` | `"#BE185D",` |
| `themes/pink.json:205` | `"#BE185D",` |
| `themes/pink.json:274` | `"#BE185D",` |
| `tools/generate_ctk_themes.py:46` | `"pink": ["#BE185D", "#9D174D"],` |

### `#beb1e5`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:86` | `50: "#F8F5FF", 100: "#EEE8FF", 200: "#DACDFF", 300: "#BEB1E5",` |

### `#c2410c`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:341` | `"high": "#C2410C",` |
| `themes/orange.json:34` | `"#C2410C",` |
| `themes/orange.json:86` | `"#C2410C",` |
| `themes/orange.json:119` | `"#C2410C",` |
| `themes/orange.json:144` | `"#C2410C",` |
| `themes/orange.json:172` | `"#C2410C",` |
| `themes/orange.json:194` | `"#C2410C",` |
| `themes/orange.json:205` | `"#C2410C",` |
| `themes/orange.json:274` | `"#C2410C",` |
| `tools/generate_ctk_themes.py:45` | `"orange": ["#C2410C", "#9A3412"],` |

### `#c7aaff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:61` | `50: "#F9F5FF", 100: "#F0E7FF", 200: "#DFCCFF", 300: "#C7AAFF",` |
| `themes/davipa.json:26` | `"#C7AAFF",` |
| `themes/davipa.json:42` | `"#C7AAFF",` |
| `themes/davipa.json:70` | `"#C7AAFF",` |
| `themes/davipa.json:90` | `"#C7AAFF",` |
| `themes/davipa.json:148` | `"#C7AAFF",` |
| `themes/davipa.json:258` | `"#C7AAFF",` |
| `themes/davipa.json:286` | `"#C7AAFF",` |
| `themes/davipa.json:306` | `"#C7AAFF",` |

### `#c96a28`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:82` | `400: "#EA833E", 500: "#C96A28", 600: "#AC5515", 700: "#8F4000",` |

### `#cb3046`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:77` | `400: "#FF6F77", 500: "#F55161", 600: "#CB3046", 700: "#AD1233",` |

### `#cc7744`

| File:Line | Snippet |
|---|---|
| `tests/test_unified_panel_design.py:575` | `{"segment": "#3366cc", "subsegment": "#44aa88", "category": "#cc7744"},` |
| `tests/test_unified_panel_design.py:877` | `{"segment": "", "subsegment": "", "category": "#cc7744"},` |
| `tests/test_unified_panel_design.py:881` | `assert cells["category"].cget("fg_color") == "#cc7744"` |
| `tests/test_unified_panel_design.py:914` | `{"segment": "", "category": "#cc7744"},` |
| `tests/test_unified_panel_design.py:919` | `assert cells["category"].cget("text_color") == pick_text_color("#cc7744")` |
| `tests/test_unified_panel_design.py:2169` | `("purposeful work", "living systems", "blog"): "#cc7744"}` |
| `tests/test_unified_panel_design.py:2172` | `assert cat == "#CC7744"` |
| `tests/test_unified_panel_design.py:2728` | `{("purposeful work", "living systems", "blog"): "#cc7744"},` |
| `tests/test_unified_panel_design.py:2730` | `assert cat == "#CC7744"` |

### `#cc8844`

| File:Line | Snippet |
|---|---|
| `tests/test_weekly_item_filters.py:55` | `(vision_category_id, vision_subsegment_id, "Learning", "#CC8844", now, now),` |
| `tests/test_weekly_item_filters.py:147` | `assert color == "#CC8844"` |
| `tests/test_weekly_title_cleanup.py:38` | `(vision_category_id, vision_subsegment_id, "APW Book", "#CC8844", now, now),` |

### `#cdcdcd`

| File:Line | Snippet |
|---|---|
| `themes/black_white.json:214` | `"#CDCDCD"` |

### `#ce83d3`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:67` | `400: "#CE83D3", 500: "#B368B9", 600: "#9C4FA2", 700: "#813389",` |

### `#d051c1`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:37` | `MAGENTA = "#D051C1"` |
| `src/getmoredone/brand.py:72` | `400: "#EA6FDA", 500: "#D051C1", 600: "#B339A6", 700: "#97208C",` |

### `#d1d5db`

| File:Line | Snippet |
|---|---|
| `themes/black_white.json:26` | `"#D1D5DB",` |
| `tools/generate_ctk_themes.py:78` | `("CTkFrame", "border_color"): ["#D1D5DB", "#4B5563"],` |

### `#d1d5de`

| File:Line | Snippet |
|---|---|
| `themes/black_white.json:95` | `"#D1D5DE"` |
| `themes/black_white.json:153` | `"#D1D5DE"` |
| `themes/black_white.json:199` | `"#D1D5DE"` |
| `themes/black_white.json:210` | `"#D1D5DE"` |
| `themes/black_white.json:279` | `"#D1D5DE"` |

### `#d2d2d7`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:26` | `"#D2D2D7",` |
| `themes/apple_grey.json:35` | `"#D2D2D7"` |
| `themes/apple_grey.json:70` | `"#D2D2D7",` |
| `themes/apple_grey.json:87` | `"#D2D2D7"` |
| `themes/apple_grey.json:120` | `"#D2D2D7"` |
| `themes/apple_grey.json:145` | `"#D2D2D7"` |
| `themes/apple_grey.json:173` | `"#D2D2D7"` |
| `themes/apple_grey.json:195` | `"#D2D2D7"` |
| `themes/apple_grey.json:206` | `"#D2D2D7"` |
| `themes/apple_grey.json:275` | `"#D2D2D7"` |
| `tools/generate_ctk_themes.py:52` | `APPLE_GREY_ANCHOR = ["#1D1D1F", "#D2D2D7"]` |
| `tools/generate_ctk_themes.py:65` | `("CTkFrame", "border_color"): ["#D2D2D7", "#424245"],` |
| `tools/generate_ctk_themes.py:68` | `("CTkEntry", "border_color"): ["#D2D2D7", "#424245"],` |

### `#d5d9de`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:124` | `"#D5D9DE"` |
| `themes/base_dark_blue.json:53` | `"button_color": ["gray36", "#D5D9DE"],` |
| `themes/black_white.json:124` | `"#D5D9DE"` |
| `themes/blue.json:124` | `"#D5D9DE"` |
| `themes/green.json:124` | `"#D5D9DE"` |
| `themes/grey.json:124` | `"#D5D9DE"` |
| `themes/orange.json:124` | `"#D5D9DE"` |
| `themes/pink.json:124` | `"#D5D9DE"` |
| `themes/purple.json:124` | `"#D5D9DE"` |

### `#d7cefe`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:91` | `50: "#F7F5FF", 100: "#EDE8FF", 200: "#D7CEFE", 300: "#BCB3E3",` |

### `#d94b66`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:269` | `"load_gradient": ["#FFD8A8", "#FFB347", "#F5A6BE", "#EF7292", "#D94B66"],` |

### `#dacdff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:86` | `50: "#F8F5FF", 100: "#EEE8FF", 200: "#DACDFF", 300: "#BEB1E5",` |

### `#dc2626`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:340` | `"critical": "#DC2626",` |

### `#dce4ee`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:47` | `\| Segment colour \| New text \| Ratio \| Was, dark (`#DCE4EE`) \| Was, light (`gray10`) \|` |
| `src/getmoredone/theme.py:110` | `"on_primary": _theme_value("CTkButton", "text_color", "#DCE4EE"),` |
| `tests/test_priority_level_colors.py:96` | `PALETTE = {"success_tint": "#E8F5EE", "row_text": "#DCE4EE"}` |
| `tests/test_unified_panel_design.py:903` | `light/dark list (`['gray10', '#DCE4EE']` on the active theme), so comparing` |
| `themes/apple_grey.json:98` | `"#DCE4EE",` |
| `themes/apple_grey.json:217` | `"#DCE4EE",` |
| `themes/apple_grey.json:218` | `"#DCE4EE"` |
| `themes/apple_grey.json:290` | `"#DCE4EE",` |
| `themes/apple_grey.json:291` | `"#DCE4EE"` |
| `themes/base_dark_blue.json:21` | `"text_color": ["#DCE4EE", "#DCE4EE"],` |
| `themes/base_dark_blue.json:43` | `"checkmark_color": ["#DCE4EE", "gray90"],` |
| `themes/base_dark_blue.json:90` | `"text_color": ["#DCE4EE", "#DCE4EE"],` |
| `themes/base_dark_blue.json:118` | `"text_color": ["#DCE4EE", "#DCE4EE"],` |
| `themes/black_white.json:98` | `"#DCE4EE",` |
| `themes/black_white.json:217` | `"#DCE4EE",` |
| `themes/black_white.json:218` | `"#DCE4EE"` |
| `themes/black_white.json:290` | `"#DCE4EE",` |
| `themes/black_white.json:291` | `"#DCE4EE"` |
| `themes/blue.json:46` | `"#DCE4EE",` |
| `themes/blue.json:47` | `"#DCE4EE"` |
| `themes/blue.json:98` | `"#DCE4EE",` |
| `themes/blue.json:217` | `"#DCE4EE",` |
| `themes/blue.json:218` | `"#DCE4EE"` |
| `themes/blue.json:290` | `"#DCE4EE",` |
| `themes/blue.json:291` | `"#DCE4EE"` |
| `themes/green.json:46` | `"#DCE4EE",` |
| `themes/green.json:47` | `"#DCE4EE"` |
| `themes/green.json:98` | `"#DCE4EE",` |
| `themes/green.json:217` | `"#DCE4EE",` |
| `themes/green.json:218` | `"#DCE4EE"` |
| `themes/green.json:290` | `"#DCE4EE",` |
| `themes/green.json:291` | `"#DCE4EE"` |
| `themes/grey.json:46` | `"#DCE4EE",` |
| `themes/grey.json:47` | `"#DCE4EE"` |
| `themes/grey.json:98` | `"#DCE4EE",` |
| `themes/grey.json:217` | `"#DCE4EE",` |
| `themes/grey.json:218` | `"#DCE4EE"` |
| `themes/grey.json:290` | `"#DCE4EE",` |
| `themes/grey.json:291` | `"#DCE4EE"` |
| `themes/orange.json:46` | `"#DCE4EE",` |
| `themes/orange.json:47` | `"#DCE4EE"` |
| `themes/orange.json:98` | `"#DCE4EE",` |
| `themes/orange.json:217` | `"#DCE4EE",` |
| `themes/orange.json:218` | `"#DCE4EE"` |
| `themes/orange.json:290` | `"#DCE4EE",` |
| `themes/orange.json:291` | `"#DCE4EE"` |
| `themes/pink.json:46` | `"#DCE4EE",` |
| `themes/pink.json:47` | `"#DCE4EE"` |
| `themes/pink.json:98` | `"#DCE4EE",` |
| `themes/pink.json:217` | `"#DCE4EE",` |
| `themes/pink.json:218` | `"#DCE4EE"` |
| `themes/pink.json:290` | `"#DCE4EE",` |
| `themes/pink.json:291` | `"#DCE4EE"` |
| `themes/purple.json:46` | `"#DCE4EE",` |
| `themes/purple.json:47` | `"#DCE4EE"` |
| `themes/purple.json:98` | `"#DCE4EE",` |
| `themes/purple.json:217` | `"#DCE4EE",` |
| `themes/purple.json:218` | `"#DCE4EE"` |
| `themes/purple.json:290` | `"#DCE4EE",` |
| `themes/purple.json:291` | `"#DCE4EE"` |

### `#dcfce7`

| File:Line | Snippet |
|---|---|
| `NOTES.md:516` | `- ✅ **Any Critical defaults to green** (`#DCFCE7`), Any High to amber` |
| `docs/USER_GUIDE.md:801` | `- **Any Critical** — Importance *or* Urgency is Critical. Default `#DCFCE7`,` |
| `docs/unused-docs/backlog_archive_2026-11-09.md:1629` | ``#DCFCE7` checkmark is about 1.3:1 — the tick disappears while the pointer is` |
| `docs/unused-docs/changes/2026-11-08-priority-level-colours.md:11` | `Colours**. Any Critical defaults to green `#DCFCE7`, Any High to amber` |
| `docs/unused-docs/cycles/2026-11-08_wtp-plc-upd-pd-qa-gate.md:61` | `found only the two centralized defaults `#DCFCE7`/`#FEF3C7` (app_settings` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:129` | `priority_level_color_any_critical: str = "#DCFCE7"   # green` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:166` | `- PLC-M2.3 Any Critical defaults to `#DCFCE7`, Any High to `#FEF3C7`, the third` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:199` | `Any Critical                 [#DCFCE7] [Pick Colour] [swatch]` |
| `src/getmoredone/app_settings.py:82` | `priority_level_color_any_critical: str = "#DCFCE7"` |
| `src/getmoredone/theme.py:137` | `"on_strong": "#ECFDF5" if mode == "light" else "#DCFCE7",` |
| `src/getmoredone/theme.py:370` | `"low": "#DCFCE7",` |
| `src/getmoredone/theme.py:419` | `LEVEL_ANY_CRITICAL: "#DCFCE7",` |
| `tests/test_priority_level_colors.py:289` | `assert defaults[LEVEL_ANY_CRITICAL] == "#DCFCE7"` |
| `tests/test_priority_level_colors.py:366` | `assert level_color(settings, LEVEL_ANY_CRITICAL) == "#DCFCE7"` |
| `tests/test_priority_level_colors.py:396` | `assert level_color(settings, LEVEL_ANY_CRITICAL) == "#DCFCE7"` |
| `tests/test_priority_level_colors.py:696` | `for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1158` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#000000", "#FFFFFF"):` |
| `tests/test_priority_level_colors.py:1192` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1253` | `segment_color="#DCFCE7",` |
| `tests/test_priority_level_colors.py:1258` | `assert segment.text_color == pick_text_color("#DCFCE7")` |
| `tests/test_priority_level_colors.py:1553` | `for colour in ("#DCFCE7", "#334155", "#F8FAFC", "#0F172A"):` |
| `tests/test_priority_level_colors.py:1605` | `for typed, normalised in (("#DCFCE7", "#DCFCE7"), ("#dcfce7", "#DCFCE7"),` |

### `#ddeeff`

| File:Line | Snippet |
|---|---|
| `tests/test_color_inventory_sync.py:38` | `#   * `#aabbcc` and `#ddeeff` tie at two hex occurrences each` |
| `tests/test_color_inventory_sync.py:46` | `"src/a.py:20:    fg_color=\"#ddeeff\"",` |
| `tests/test_color_inventory_sync.py:48` | `"src/a.py:3:     text_color=\"#ddeeff\"",` |
| `tests/test_color_inventory_sync.py:59` | `"src/a.py:20:    hover_color=\"#ddeeff\"",` |
| `tests/test_segment_colour_validation.py:389` | `assert stored("vision_subsegments", sub["id"]) == "#DDEEFF"` |

### `#de1b24`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:31` | `CRIMSON = "#DE1B24"` |
| `src/getmoredone/brand.py:57` | `400: "#FF7260", 500: "#F43E37", 600: "#DE1B24", 700: "#B20016",` |
| `themes/davipa.json:86` | `"#DE1B24",` |
| `themes/davipa.json:87` | `"#DE1B24"` |
| `themes/davipa.json:119` | `"#DE1B24",` |
| `themes/davipa.json:120` | `"#DE1B24"` |
| `themes/davipa.json:144` | `"#DE1B24",` |
| `themes/davipa.json:145` | `"#DE1B24"` |
| `themes/davipa.json:194` | `"#DE1B24",` |
| `themes/davipa.json:195` | `"#DE1B24"` |

### `#def`

| File:Line | Snippet |
|---|---|
| `tests/test_segment_colour_validation.py:388` | `sub["id"], "Scv Sub", "#def", "", "") is True` |

### `#dfccff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:61` | `50: "#F9F5FF", 100: "#F0E7FF", 200: "#DFCCFF", 300: "#C7AAFF",` |
| `themes/davipa.json:22` | `"#DFCCFF",` |
| `themes/davipa.json:115` | `"#DFCCFF",` |
| `themes/davipa.json:168` | `"#DFCCFF",` |
| `themes/davipa.json:186` | `"#DFCCFF",` |
| `themes/davipa.json:270` | `"#DFCCFF",` |
| `themes/davipa.json:282` | `"#DFCCFF",` |
| `themes/davipa.json:324` | `"#DFCCFF",` |
| `themes/davipa.json:334` | `"#DFCCFF",` |

### `#dff8d8`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:270` | `"load_fallback": "#DFF8D8",` |

### `#e6eef8`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:135` | `"selected_tint": "#E6EEF8" if mode == "light" else "#223247",` |

### `#e8f5ee`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:129` | `"success_tint": "#E8F5EE" if mode == "light" else "#1F2B24",` |
| `tests/test_priority_level_colors.py:96` | `PALETTE = {"success_tint": "#E8F5EE", "row_text": "#DCE4EE"}` |

### `#e91e63`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1163` | `('seg-5', 'Relationships', 'Personal and professional connections', '#E91E63', 5),` |

### `#e99fed`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:66` | `50: "#FFF3FF", 100: "#FFE2FF", 200: "#FCC1FF", 300: "#E99FED",` |

### `#e9c6cf`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:265` | `"future_long_term": "#E9C6CF",` |

### `#e9caa0`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:267` | `"future_next_quarter": "#E9CAA0",` |

### `#ea580c`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:457` | `"Quarter": "#EA580C",` |

### `#ea6fda`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:72` | `400: "#EA6FDA", 500: "#D051C1", 600: "#B339A6", 700: "#97208C",` |

### `#ea833e`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:82` | `400: "#EA833E", 500: "#C96A28", 600: "#AC5515", 700: "#8F4000",` |

### `#eab308`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/project_boards.py:1267` | `hover_color="#EAB308",` |

### `#ecfdf5`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:137` | `"on_strong": "#ECFDF5" if mode == "light" else "#DCFCE7",` |

### `#ede8ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:91` | `50: "#F7F5FF", 100: "#EDE8FF", 200: "#D7CEFE", 300: "#BCB3E3",` |

### `#eee8ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:86` | `50: "#F8F5FF", 100: "#EEE8FF", 200: "#DACDFF", 300: "#BEB1E5",` |

### `#ef4444`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:52` | `\| `#EF4444` red \| black \| 5.58 \| 2.93 \| 4.62 \|` |
| `src/getmoredone/theme.py:465` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#ef7292`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:269` | `"load_gradient": ["#FFD8A8", "#FFB347", "#F5A6BE", "#EF7292", "#D94B66"],` |

### `#efe6a7`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:266` | `"future_next_month": "#EFE6A7",` |

### `#f0e7ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:61` | `50: "#F9F5FF", 100: "#F0E7FF", 200: "#DFCCFF", 300: "#C7AAFF",` |
| `themes/davipa.json:18` | `"#F0E7FF",` |
| `themes/davipa.json:59` | `"#F0E7FF"` |
| `themes/davipa.json:75` | `"#F0E7FF"` |
| `themes/davipa.json:103` | `"#F0E7FF"` |
| `themes/davipa.json:127` | `"#F0E7FF",` |
| `themes/davipa.json:128` | `"#F0E7FF"` |
| `themes/davipa.json:132` | `"#F0E7FF"` |
| `themes/davipa.json:157` | `"#F0E7FF"` |
| `themes/davipa.json:311` | `"#F0E7FF"` |
| `themes/davipa.json:330` | `"#F0E7FF",` |
| `themes/davipa.json:339` | `"#F0E7FF"` |

### `#f3f4f6`

| File:Line | Snippet |
|---|---|
| `themes/black_white.json:35` | `"#F3F4F6"` |
| `themes/black_white.json:87` | `"#F3F4F6"` |
| `themes/black_white.json:120` | `"#F3F4F6"` |
| `themes/black_white.json:145` | `"#F3F4F6"` |
| `themes/black_white.json:173` | `"#F3F4F6"` |
| `themes/black_white.json:195` | `"#F3F4F6"` |
| `themes/black_white.json:206` | `"#F3F4F6"` |
| `themes/black_white.json:275` | `"#F3F4F6"` |
| `tools/generate_ctk_themes.py:56` | `BLACK_WHITE_ANCHOR = ["#111111", "#F3F4F6"]` |

### `#f43e37`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:57` | `400: "#FF7260", 500: "#F43E37", 600: "#DE1B24", 700: "#B20016",` |

### `#f4d35e`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:264` | `"future_near_term": "#F4D35E",` |

### `#f4f4f5`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:371` | `"unscored": "#F4F4F5",` |

### `#f55161`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:39` | `CORAL = "#F55161"` |
| `src/getmoredone/brand.py:77` | `400: "#FF6F77", 500: "#F55161", 600: "#CB3046", 700: "#AD1233",` |

### `#f59e0b`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:51` | `\| `#F59E0B` amber \| black \| 9.78 \| **1.67** \| 8.10 \|` |
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:70` | ``#F59E0B` was 1.67:1, which is near-invisible. If the row text still looks` |
| `docs/unused-docs/changes/2026-11-11-manual-walk-four-batches.md:56` | `amber `#F59E0B` measured 1.67:1 before, which is near-invisible.` |
| `src/getmoredone/theme.py:456` | `"Annual Initiative": "#F59E0B",` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#f5a6be`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:269` | `"load_gradient": ["#FFD8A8", "#FFB347", "#F5A6BE", "#EF7292", "#D94B66"],` |

### `#f5f5f7`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:4` | `"#F5F5F7",` |
| `themes/apple_grey.json:10` | `"#F5F5F7",` |
| `themes/apple_grey.json:39` | `"#F5F5F7"` |
| `themes/apple_grey.json:59` | `"#F5F5F7"` |
| `themes/apple_grey.json:75` | `"#F5F5F7"` |
| `tools/generate_ctk_themes.py:53` | `APPLE_GREY_HOVER = ["#000000", "#F5F5F7"]` |
| `tools/generate_ctk_themes.py:61` | `("CTk", "fg_color"): ["#F5F5F7", "#000000"],` |
| `tools/generate_ctk_themes.py:62` | `("CTkToplevel", "fg_color"): ["#F5F5F7", "#000000"],` |
| `tools/generate_ctk_themes.py:66` | `("CTkLabel", "text_color"): ["#1D1D1F", "#F5F5F7"],` |
| `tools/generate_ctk_themes.py:69` | `("CTkEntry", "text_color"): ["#1D1D1F", "#F5F5F7"],` |

### `#f7f5ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:91` | `50: "#F7F5FF", 100: "#EDE8FF", 200: "#D7CEFE", 300: "#BCB3E3",` |

### `#f87171`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:310` | `"critical": "#F87171",` |

### `#f8f5ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:86` | `50: "#F8F5FF", 100: "#EEE8FF", 200: "#DACDFF", 300: "#BEB1E5",` |

### `#f8fafc`

| File:Line | Snippet |
|---|---|
| `tests/test_priority_level_colors.py:1185` | `pale = text_for("#F8FAFC")` |
| `tests/test_priority_level_colors.py:1188` | `assert contrast_ratio("#F8FAFC", pale) >= MIN_TEXT_CONTRAST` |
| `tests/test_priority_level_colors.py:1553` | `for colour in ("#DCFCE7", "#334155", "#F8FAFC", "#0F172A"):` |

### `#f97316`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md:55` | `\| `#F97316` orange \| black \| 7.49 \| 2.19 \| 6.21 \|` |
| `src/getmoredone/theme.py:465` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#f9f5ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:61` | `50: "#F9F5FF", 100: "#F0E7FF", 200: "#DFCCFF", 300: "#C7AAFF",` |
| `themes/davipa.json:4` | `"#F9F5FF",` |
| `themes/davipa.json:10` | `"#F9F5FF",` |

### `#f9f9fa`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:229` | `"#F9F9FA",` |
| `themes/base_dark_blue.json:32` | `"fg_color": ["#F9F9FA", "#343638"],` |
| `themes/base_dark_blue.json:96` | `"fg_color": ["#F9F9FA", "#343638"],` |
| `themes/black_white.json:229` | `"#F9F9FA",` |
| `themes/blue.json:66` | `"#F9F9FA",` |
| `themes/blue.json:229` | `"#F9F9FA",` |
| `themes/green.json:66` | `"#F9F9FA",` |
| `themes/green.json:229` | `"#F9F9FA",` |
| `themes/grey.json:66` | `"#F9F9FA",` |
| `themes/grey.json:229` | `"#F9F9FA",` |
| `themes/orange.json:66` | `"#F9F9FA",` |
| `themes/orange.json:229` | `"#F9F9FA",` |
| `themes/pink.json:66` | `"#F9F9FA",` |
| `themes/pink.json:229` | `"#F9F9FA",` |
| `themes/purple.json:66` | `"#F9F9FA",` |
| `themes/purple.json:229` | `"#F9F9FA",` |

### `#facc15`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/project_boards.py:1266` | `fg_color="#FACC15",` |

### `#fb923c`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:311` | `"high": "#FB923C",` |

### `#fbbf24`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:134` | `"warning": "#B45309" if mode == "light" else "#FBBF24",` |
| `src/getmoredone/theme.py:312` | `"medium": "#FBBF24",` |

### `#fca5a5`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-11-07-plan-clear-day-and-marks.md:44` | `and #B91C1C/#FCA5A5 (unscheduled), and a test holds every combination of theme` |
| `src/getmoredone/theme.py:151` | `"unscheduled_mark": "#B91C1C" if mode == "light" else "#FCA5A5",` |
| `src/getmoredone/theme.py:261` | `"date_overdue": "#FCA5A5",` |
| `tests/test_vision_planning_regressions.py:53` | `assert screen._date_background_for((today - timedelta(days=1)).strftime("%Y-%m-%d")) == "#FCA5A5"` |

### `#fcc1ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:66` | `50: "#FFF3FF", 100: "#FFE2FF", 200: "#FCC1FF", 300: "#E99FED",` |

### `#fd915b`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:106` | `TILE_GRADIENT = (DEEP_INK, INDIGO, "#813798", "#FD915B")` |

### `#fd924a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:41` | `AMBER = "#FD924A"` |
| `src/getmoredone/brand.py:81` | `50: "#FFF4EF", 100: "#FFE6D8", 200: "#FFC9A9", 300: "#FD924A",` |
| `themes/davipa.json:173` | `"#FD924A"` |
| `themes/davipa.json:191` | `"#FD924A"` |

### `#fde68a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:263` | `"date_future": "#FDE68A",` |
| `tests/test_vision_planning_regressions.py:55` | `assert screen._date_background_for((today + timedelta(days=1)).strftime("%Y-%m-%d")) == "#FDE68A"` |

### `#fdecec`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:45` | ``critical_tint` is `#FDECEC` light / `#3A2328` dark (`theme.py:129`).` |
| `src/getmoredone/theme.py:130` | `"critical_tint": "#FDECEC" if mode == "light" else "#3A2328",` |

### `#fee2e2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:133` | `"on_danger": "#FEE2E2",` |
| `src/getmoredone/theme.py:367` | `"critical": "#FEE2E2",` |

### `#fef3c7`

| File:Line | Snippet |
|---|---|
| `NOTES.md:517` | `(`#FEF3C7`), the third level to no fill. Asked for directly, and confirmed` |
| `docs/USER_GUIDE.md:804` | `Critical. Default `#FEF3C7`, an amber. This tier is new; before` |
| `docs/unused-docs/changes/2026-11-08-priority-level-colours.md:12` | ``#FEF3C7`, the third level to no fill.` |
| `docs/unused-docs/cycles/2026-11-08_wtp-plc-upd-pd-qa-gate.md:61` | `found only the two centralized defaults `#DCFCE7`/`#FEF3C7` (app_settings` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:130` | `priority_level_color_any_high: str = "#FEF3C7"       # amber` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:166` | `- PLC-M2.3 Any Critical defaults to `#DCFCE7`, Any High to `#FEF3C7`, the third` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:200` | `Any High, but no Critical    [#FEF3C7] [Pick Colour] [swatch]` |
| `src/getmoredone/app_settings.py:83` | `priority_level_color_any_high: str = "#FEF3C7"` |
| `src/getmoredone/theme.py:369` | `"medium": "#FEF3C7",` |
| `src/getmoredone/theme.py:420` | `LEVEL_ANY_HIGH: "#FEF3C7",` |
| `tests/test_priority_level_colors.py:290` | `assert defaults[LEVEL_ANY_HIGH] == "#FEF3C7"` |
| `tests/test_priority_level_colors.py:547` | `LEVEL_ANY_HIGH: "#FEF3C7",` |
| `tests/test_priority_level_colors.py:696` | `for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1158` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#000000", "#FFFFFF"):` |
| `tests/test_priority_level_colors.py:1192` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#7F7F7F", "#450A0A"):` |

### `#ff0000`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-08-20-rename-safe-links-acceptance.md:295` | `colour after: #4CAF50 (wanted #FF0000)` |
| `tests/test_color_contrast.py:29` | `assert not meets_wcag("#FF0000", "#FFFFFF", large_text=False)` |
| `tests/test_color_contrast.py:30` | `assert meets_wcag("#FF0000", "#FFFFFF", large_text=True)` |
| `tests/test_rename_safe_links.py:2146` | `assert vps.update_segment(first, name="Kappa", color_hex="#FF0000") is True, (` |
| `tests/test_rename_safe_links.py:2160` | `assert stored["color_hex"] == "#FF0000", "the colour never reached the row"` |
| `tests/test_rename_safe_links.py:2452` | `vps.update_segment(second, color_hex="#FF0000")` |
| `tests/test_rename_safe_links.py:2499` | `vps.update_segment(seg, color_hex="#FF0000")` |
| `tests/test_vps_data_integrity.py:35` | `color_hex="#FF0000",` |
| `tests/test_vps_integration.py:1530` | `color_hex="#FF0000",` |
| `tests/test_vps_integration.py:1634` | `valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#ABCDEF", "#123456"]` |

### `#ff00ff`

| File:Line | Snippet |
|---|---|
| `tests/test_vps_data_integrity.py:385` | `color_hex="#FF00FF",` |
| `tests/test_vps_integration.py:1653` | `color_hex="#FF00FF",` |

### `#ff5733`

| File:Line | Snippet |
|---|---|
| `tests/test_vps_integration.py:1462` | `color_hex="#FF5733",` |
| `tests/test_vps_integration.py:1474` | `assert segment['color_hex'] == "#FF5733"` |

### `#ff5a8a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:122` | `"date_due_text": "#FF5A8A",` |

### `#ff6f77`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:77` | `400: "#FF6F77", 500: "#F55161", 600: "#CB3046", 700: "#AD1233",` |

### `#ff7260`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:57` | `400: "#FF7260", 500: "#F43E37", 600: "#DE1B24", 700: "#B20016",` |

### `#ff93ef`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:71` | `50: "#FFF3FC", 100: "#FFE3F9", 200: "#FFC1F4", 300: "#FF93EF",` |

### `#ff9800`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1162` | `('seg-4', 'Wealth Creation', 'Financial growth and management', '#FF9800', 4),` |

### `#ff9e9e`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:76` | `50: "#FFF4F4", 100: "#FFE5E4", 200: "#FFC7C5", 300: "#FF9E9E",` |

### `#ffa090`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:56` | `50: "#FFF4F2", 100: "#FFE5E1", 200: "#FFC7BD", 300: "#FFA090",` |

### `#ffb347`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:121` | `"date_start_text": "#FFB347",` |
| `src/getmoredone/theme.py:269` | `"load_gradient": ["#FFD8A8", "#FFB347", "#F5A6BE", "#EF7292", "#D94B66"],` |

### `#ffc107`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1166` | `('seg-8', 'Travel', 'Exploration and adventure', '#FFC107', 8),` |

### `#ffc1f4`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:71` | `50: "#FFF3FC", 100: "#FFE3F9", 200: "#FFC1F4", 300: "#FF93EF",` |

### `#ffc7bd`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:56` | `50: "#FFF4F2", 100: "#FFE5E1", 200: "#FFC7BD", 300: "#FFA090",` |

### `#ffc7c5`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:76` | `50: "#FFF4F4", 100: "#FFE5E4", 200: "#FFC7C5", 300: "#FF9E9E",` |

### `#ffc9a9`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:81` | `50: "#FFF4EF", 100: "#FFE6D8", 200: "#FFC9A9", 300: "#FD924A",` |

### `#ffd54f`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:465` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

### `#ffd8a8`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:269` | `"load_gradient": ["#FFD8A8", "#FFB347", "#F5A6BE", "#EF7292", "#D94B66"],` |

### `#ffe2ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:66` | `50: "#FFF3FF", 100: "#FFE2FF", 200: "#FCC1FF", 300: "#E99FED",` |

### `#ffe3f9`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:71` | `50: "#FFF3FC", 100: "#FFE3F9", 200: "#FFC1F4", 300: "#FF93EF",` |

### `#ffe5e1`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:56` | `50: "#FFF4F2", 100: "#FFE5E1", 200: "#FFC7BD", 300: "#FFA090",` |

### `#ffe5e4`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:76` | `50: "#FFF4F4", 100: "#FFE5E4", 200: "#FFC7C5", 300: "#FF9E9E",` |

### `#ffe6d8`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:81` | `50: "#FFF4EF", 100: "#FFE6D8", 200: "#FFC9A9", 300: "#FD924A",` |

### `#ffedd5`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:368` | `"high": "#FFEDD5",` |

### `#fff`

| File:Line | Snippet |
|---|---|
| `tests/test_weekly_tactic_parent.py:738` | `palette={"primary": "#000", "on_primary": "#fff", "body_text": "#111"},` |

### `#fff3fc`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:71` | `50: "#FFF3FC", 100: "#FFE3F9", 200: "#FFC1F4", 300: "#FF93EF",` |

### `#fff3ff`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:66` | `50: "#FFF3FF", 100: "#FFE2FF", 200: "#FCC1FF", 300: "#E99FED",` |

### `#fff4ef`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:81` | `50: "#FFF4EF", 100: "#FFE6D8", 200: "#FFC9A9", 300: "#FD924A",` |

### `#fff4f2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:56` | `50: "#FFF4F2", 100: "#FFE5E1", 200: "#FFC7BD", 300: "#FFA090",` |

### `#fff4f4`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:76` | `50: "#FFF4F4", 100: "#FFE5E4", 200: "#FFC7C5", 300: "#FF9E9E",` |

### `#ffff00`

| File:Line | Snippet |
|---|---|
| `tests/test_color_contrast.py:13` | `assert pick_text_color("#FFFF00") == "#000000"  # bright yellow -> black` |

### `#ffffff`

| File:Line | Snippet |
|---|---|
| `docs/USER_GUIDE.md:786` | `- **Drag Schedule date text color** — What: Hex color for date-box text (default `#FFFFFF`). Why: Improve readability across box colors.` |
| `docs/unused-docs/changes/2026-03-02-wcag-auto-text-contrast.md:12` | `- `pick_text_color(bg_hex, light="#FFFFFF", dark="#000000")`` |
| `src/getmoredone/app_settings.py:127` | `drag_schedule_date_text_color: str = "#FFFFFF"` |
| `src/getmoredone/brand.py:48` | `ON_DARK = "#FFFFFF"` |
| `src/getmoredone/color_contrast.py:160` | `light: str = "#FFFFFF",` |
| `src/getmoredone/color_contrast.py:168` | `def pick_text_color(bg_hex: str, light: str = "#FFFFFF", dark: str = "#000000") -> str:` |
| `src/getmoredone/screens/drag_schedule.py:1050` | `date_text_color_for(color, getattr(self.settings, "drag_schedule_date_text_color", "#FFFFFF")),` |
| `src/getmoredone/screens/drag_schedule.py:1070` | `date_text_color_for(color, getattr(self.settings, "drag_schedule_date_text_color", "#FFFFFF")),` |
| `src/getmoredone/screens/drag_schedule.py:1200` | `text_color=date_text_color_for(color, getattr(self.settings, "drag_schedule_date_text_color", "#FFFFFF")),` |
| `src/getmoredone/screens/drag_schedule.py:1302` | `return normalized_date_text_color(getattr(self.settings, "drag_schedule_date_text_color", "#FFFFFF"))` |
| `src/getmoredone/screens/drag_schedule.py:1305` | `return date_text_color_for(bg_color, getattr(self.settings, "drag_schedule_date_text_color", "#FFFFFF"))` |
| `src/getmoredone/screens/drag_schedule_support.py:58` | `color = str(configured_value or "#FFFFFF").strip()` |
| `src/getmoredone/screens/drag_schedule_support.py:62` | `return "#FFFFFF"` |
| `src/getmoredone/screens/settings.py:625` | `value=getattr(self.settings, "drag_schedule_date_text_color", "#FFFFFF")` |
| `src/getmoredone/screens/settings.py:713` | `color_value = self.drag_schedule_text_color_var.get().strip() or "#FFFFFF"` |
| `src/getmoredone/screens/settings.py:717` | `color_value = "#FFFFFF"` |
| `src/getmoredone/screens/settings.py:741` | `initial = self.drag_schedule_text_color_var.get().strip() or "#FFFFFF"` |
| `src/getmoredone/screens/settings_priority_colors.py:199` | ```#FFFFFF``, and a user who typed a colour they meant has no way to` |
| `tests/test_color_contrast.py:14` | `assert pick_text_color("#003366") == "#FFFFFF"  # dark blue -> white` |
| `tests/test_color_contrast.py:19` | `assert math.isclose(contrast_ratio("#000000", "#FFFFFF"), 21.0, rel_tol=0.0, abs_tol=0.01)` |
| `tests/test_color_contrast.py:21` | `assert math.isclose(contrast_ratio("#777777", "#FFFFFF"), 4.48, rel_tol=0.0, abs_tol=0.03)` |
| `tests/test_color_contrast.py:22` | `assert math.isclose(contrast_ratio("#0000FF", "#FFFFFF"), 8.59, rel_tol=0.0, abs_tol=0.03)` |
| `tests/test_color_contrast.py:26` | `assert meets_wcag("#767676", "#FFFFFF", large_text=False)` |
| `tests/test_color_contrast.py:27` | `assert meets_wcag("#767676", "#FFFFFF", large_text=True)` |
| `tests/test_color_contrast.py:28` | `assert not meets_wcag("#777777", "#FFFFFF", large_text=False)` |
| `tests/test_color_contrast.py:29` | `assert not meets_wcag("#FF0000", "#FFFFFF", large_text=False)` |
| `tests/test_color_contrast.py:30` | `assert meets_wcag("#FF0000", "#FFFFFF", large_text=True)` |
| `tests/test_color_contrast.py:45` | `assert math.isclose(relative_luminance("#FFFFFF"), 1.0, rel_tol=0.0, abs_tol=1e-9)` |
| `tests/test_drag_schedule_support.py:19` | `assert normalized_date_text_color("ffffff") == "#ffffff"` |
| `tests/test_drag_schedule_support.py:21` | `assert normalized_date_text_color("bad") == "#FFFFFF"` |
| `tests/test_drag_schedule_support.py:30` | `assert interpolate_hex_color("#000000", "#FFFFFF", 0.5) == "#808080"` |
| `tests/test_future_dates.py:82` | `original_color = getattr(settings, "drag_schedule_date_text_color", "#FFFFFF")` |
| `tests/test_future_dates.py:85` | `settings.drag_schedule_date_text_color = "#FFFFFF"` |
| `tests/test_future_dates.py:89` | `assert reloaded.drag_schedule_date_text_color == "#FFFFFF"` |
| `tests/test_plan_settings.py:656` | `drag_schedule_text_color_var=SimpleNamespace(get=lambda: "#FFFFFF"),` |
| `tests/test_priority_level_colors.py:338` | `["#FFFFFF"],` |
| `tests/test_priority_level_colors.py:539` | ```#FFFFFF``, and a user who meant what they typed is never told.` |
| `tests/test_priority_level_colors.py:696` | `for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):` |
| `tests/test_priority_level_colors.py:1158` | `for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#000000", "#FFFFFF"):` |
| `tests/test_settings_week_rule_ui.py:29` | `drag_schedule_text_color_var=SimpleNamespace(get=lambda: "#FFFFFF"),` |
| `tests/test_vision_planning_regressions.py:39` | `screen.settings = SimpleNamespace(drag_schedule_date_text_color="#FFFFFF")` |
| `tests/test_vision_planning_regressions.py:40` | `assert screen._get_date_text_color() == "#FFFFFF"` |
| `tests/test_vision_planning_regressions.py:46` | `assert screen._get_date_text_color() == "#FFFFFF"` |
| `tests/test_vps_segments.py:173` | `@pytest.mark.parametrize("value", ["#000000", "#ffffff", "#AABBCC", "#1a2b3c"])` |
| `themes/apple_grey.json:18` | `"#FFFFFF",` |
| `themes/apple_grey.json:22` | `"#FFFFFF",` |
| `themes/apple_grey.json:46` | `"#FFFFFF",` |
| `themes/apple_grey.json:66` | `"#FFFFFF",` |
| `themes/black_white.json:4` | `"#FFFFFF",` |
| `themes/black_white.json:10` | `"#FFFFFF",` |
| `themes/black_white.json:18` | `"#FFFFFF",` |
| `themes/black_white.json:22` | `"#FFFFFF",` |
| `themes/black_white.json:39` | `"#FFFFFF"` |
| `themes/black_white.json:46` | `"#FFFFFF",` |
| `themes/black_white.json:59` | `"#FFFFFF"` |
| `themes/black_white.json:66` | `"#FFFFFF",` |
| `themes/black_white.json:75` | `"#FFFFFF"` |
| `themes/davipa.json:46` | `"#FFFFFF",` |
| `themes/davipa.json:47` | `"#FFFFFF"` |
| `themes/davipa.json:66` | `"#FFFFFF",` |
| `themes/davipa.json:98` | `"#FFFFFF",` |
| `themes/davipa.json:99` | `"#FFFFFF"` |
| `themes/davipa.json:123` | `"#FFFFFF",` |
| `themes/davipa.json:124` | `"#FFFFFF"` |
| `themes/davipa.json:217` | `"#FFFFFF",` |
| `themes/davipa.json:218` | `"#FFFFFF"` |
| `themes/davipa.json:245` | `"#FFFFFF",` |
| `themes/davipa.json:246` | `"#FFFFFF"` |
| `themes/davipa.json:290` | `"#FFFFFF",` |
| `themes/davipa.json:291` | `"#FFFFFF"` |
| `themes/davipa.json:302` | `"#FFFFFF",` |
| `tools/generate_ctk_themes.py:54` | `APPLE_GREY_BUTTON_TEXT = ["#FFFFFF", "#1D1D1F"]` |
| `tools/generate_ctk_themes.py:57` | `BLACK_WHITE_HOVER = ["#000000", "#FFFFFF"]` |
| `tools/generate_ctk_themes.py:58` | `BLACK_WHITE_BUTTON_TEXT = ["#FFFFFF", "#111111"]` |
| `tools/generate_ctk_themes.py:63` | `("CTkFrame", "fg_color"): ["#FFFFFF", "#1D1D1F"],` |
| `tools/generate_ctk_themes.py:64` | `("CTkFrame", "top_fg_color"): ["#FFFFFF", "#1D1D1F"],` |
| `tools/generate_ctk_themes.py:67` | `("CTkEntry", "fg_color"): ["#FFFFFF", "#1D1D1F"],` |
| `tools/generate_ctk_themes.py:74` | `("CTk", "fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:75` | `("CTkToplevel", "fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:76` | `("CTkFrame", "fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:77` | `("CTkFrame", "top_fg_color"): ["#FFFFFF", "#000000"],` |
| `tools/generate_ctk_themes.py:79` | `("CTkLabel", "text_color"): ["#000000", "#FFFFFF"],` |
| `tools/generate_ctk_themes.py:80` | `("CTkEntry", "fg_color"): ["#FFFFFF", "#111111"],` |
| `tools/generate_ctk_themes.py:82` | `("CTkEntry", "text_color"): ["#000000", "#FFFFFF"],` |

### `black`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:98` | `- Command: `rg -n 'text_color="black"\|fg_color="white"\|dropdown_fg_color="white"\|button_hover_color="white"\|dropdown_text_color="black"\|button_color="white"\|text_color="#00C8` |
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:100` | `- Command: `rg -n 'text_color="(green\|red\|gray\|white\|black)"\|fg_color="(white\|black\|gray[0-9]+)"\|button_hover_color="white"\|dropdown_fg_color="white"\|dropdown_text_color=` |
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:393` | `return "black" if luminance > 160 else "white"` |
| `tests/test_date_picker.py:331` | `"white", "black", "darkblue", "lightblue", "lightgray", "lightgrey",` |
| `tests/test_release_licensing.py:70` | `"flake8", "pylint", "ruff", "mypy", "black", "isort", "bandit",` |

### `blue`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:892` | `status_color = "green" if self.timer_state == self.RUNNING else "blue"` |
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `src/getmoredone/theme.py:248` | `"blue": palette["primary"],` |
| `tests/test_color_inventory_sync.py:39` | `#   * "red" and "blue" tie at two named occurrences each` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |
| `tests/test_theme_settings.py:72` | `assert status_text_color("blue")` |
| `tools/generate_ctk_themes.py:48` | `"blue": ["#3B8ED0", "#1F6AA5"],` |

### `cyan`

| File:Line | Snippet |
|---|---|
| `tests/test_date_picker.py:333` | `"purple", "cyan", "magenta",` |

### `gray`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:98` | `- Command: `rg -n 'text_color="black"\|fg_color="white"\|dropdown_fg_color="white"\|button_hover_color="white"\|dropdown_text_color="black"\|button_color="white"\|text_color="#00C8` |
| `src/getmoredone/screens/vision_planning.py:83` | `fg_color="gray", width=120).pack(side="left", padx=5)` |
| `src/getmoredone/screens/vision_planning.py:171` | `text_color="gray"` |
| `src/getmoredone/screens/vision_planning.py:227` | `toolbar, text="Refresh", width=80, fg_color="gray",` |
| `src/getmoredone/screens/vision_planning.py:249` | `text_color="gray"` |
| `src/getmoredone/screens/vision_planning.py:381` | `ctrl, text="Refresh", width=80, fg_color="gray",` |
| `src/getmoredone/screens/vision_planning.py:409` | `sep = ctk.CTkFrame(body, width=2, fg_color="gray")` |
| `src/getmoredone/screens/vision_planning.py:463` | `text_color="gray"` |
| `src/getmoredone/screens/vision_planning.py:500` | `text_color="gray"` |
| `src/getmoredone/screens/vision_planning.py:629` | `text_color="gray"` |
| `src/getmoredone/screens/vps_editors.py:1289` | `separator = ctk.CTkFrame(main_frame, height=2, fg_color="gray")` |
| `src/getmoredone/theme.py:250` | `"gray": palette["muted_text"],` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |
| `tests/test_theme_settings.py:71` | `assert status_text_color("gray")` |
| `themes/apple_grey.json:176` | `"gray",` |
| `themes/apple_grey.json:177` | `"gray"` |
| `themes/base_dark_blue.json:73` | `"border_color": ["gray", "gray"]` |
| `themes/black_white.json:176` | `"gray",` |
| `themes/black_white.json:177` | `"gray"` |
| `themes/blue.json:176` | `"gray",` |
| `themes/blue.json:177` | `"gray"` |
| `themes/davipa.json:176` | `"gray",` |
| `themes/davipa.json:177` | `"gray"` |
| `themes/green.json:176` | `"gray",` |
| `themes/green.json:177` | `"gray"` |
| `themes/grey.json:176` | `"gray",` |
| `themes/grey.json:177` | `"gray"` |
| `themes/orange.json:176` | `"gray",` |
| `themes/orange.json:177` | `"gray"` |
| `themes/pink.json:176` | `"gray",` |
| `themes/pink.json:177` | `"gray"` |
| `themes/purple.json:176` | `"gray",` |
| `themes/purple.json:177` | `"gray"` |

### `green`

| File:Line | Snippet |
|---|---|
| `docs/action-timer-requirements.md:587` | `color = "green"  # Warning color` |
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:98` | `- Command: `rg -n 'text_color="black"\|fg_color="white"\|dropdown_fg_color="white"\|button_hover_color="white"\|dropdown_text_color="black"\|button_color="white"\|text_color="#00C8` |
| `docs/unused-docs/changes/2026-11-05-demo-install.md:282` | `batch's, but they make CI unable to say "green" for anyone, which is the` |
| `src/getmoredone/screens/timer_window.py:847` | `self._update_status_label("Working...", "green")` |
| `src/getmoredone/screens/timer_window.py:892` | `status_color = "green" if self.timer_state == self.RUNNING else "blue"` |
| `src/getmoredone/screens/timer_window.py:1059` | `self._update_status_label("Recording...", "green")` |
| `src/getmoredone/screens/timer_window.py:1097` | `self._update_status_label("Working...", "green")` |
| `src/getmoredone/screens/vision_planning.py:81` | `fg_color="green", width=120).pack(side="left", padx=5)` |
| `src/getmoredone/screens/vision_planning.py:376` | `ctrl, text="Save", width=70, fg_color="green",` |
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `src/getmoredone/theme.py:240` | `"green": palette["success_strong"],` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |
| `tests/test_reward_protocol_timer.py:1572` | `timer._update_status_label("Working...", "green")` |
| `tests/test_theme_settings.py:26` | `assert normalize_theme_name("GREEN") == "green"` |
| `tests/test_theme_settings.py:32` | `assert theme_path_for("green").name == "green.json"` |
| `tests/test_theme_settings.py:69` | `assert status_text_color("green")` |
| `tools/generate_ctk_themes.py:44` | `"green": ["#2CC985", "#2FA572"],` |

### `grey`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |
| `tools/generate_ctk_themes.py:47` | `"grey": ["#475569", "#334155"],` |

### `orange`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:862` | `self._update_status_label("Paused", "orange")` |
| `src/getmoredone/screens/timer_window.py:1025` | `self._update_status_label("Resting — Resume starts another block", "orange")` |
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `src/getmoredone/theme.py:245` | `"orange": palette["warning"],` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |
| `tools/generate_ctk_themes.py:45` | `"orange": ["#C2410C", "#9A3412"],` |

### `red`

| File:Line | Snippet |
|---|---|
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:98` | `- Command: `rg -n 'text_color="black"\|fg_color="white"\|dropdown_fg_color="white"\|button_hover_color="white"\|dropdown_text_color="black"\|button_color="white"\|text_color="#00C8` |
| `docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md:173` | ``"red"`, `"#GGG"`, `"#12345"` or a non-string is ignored per-level, the theme` |
| `src/getmoredone/color_contrast.py:51` | `type and every browser accepts; a named colour such as ``"red"`` is not,` |
| `src/getmoredone/screens/timer_window.py:919` | `self._update_status_label("Stopped", "red")` |
| `src/getmoredone/screens/timer_window.py:971` | `self._update_status_label("⏰ BREAK OVER! ⏰", "red")` |
| `src/getmoredone/screens/timer_window.py:1074` | `self._update_status_label("Not saved — try Done again", "red")` |
| `src/getmoredone/screens/vision_planning.py:315` | `fg_color="darkred", hover_color="red",` |
| `src/getmoredone/screens/vision_planning.py:577` | `fg_color="darkred", hover_color="red",` |
| `src/getmoredone/theme.py:243` | `"red": palette["danger"],` |
| `tests/test_color_inventory_sync.py:39` | `#   * "red" and "blue" tie at two named occurrences each` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |
| `tests/test_priority_level_colors.py:332` | `"red",` |
| `tests/test_priority_level_colors.py:1216` | `for colour in ("navy", "red", "not-a-colour", "#GGHHII"):` |
| `tests/test_priority_level_colors.py:1597` | `for colour in ("navy", "red", "not-a-colour", "#GGHHII", "#0X1234",` |
| `tests/test_theme_settings.py:70` | `assert status_text_color("red")` |

### `white`

| File:Line | Snippet |
|---|---|
| `assets/icons/music_note.svg:1` | `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">` |
| `assets/icons/pause.svg:1` | `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">` |
| `assets/icons/play.svg:1` | `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">` |
| `assets/icons/stop.svg:1` | `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">` |
| `assets/icons/volume.svg:1` | `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">` |
| `docs/action-timer-requirements.md:589` | `color = "white"  # Normal color` |
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:98` | `- Command: `rg -n 'text_color="black"\|fg_color="white"\|dropdown_fg_color="white"\|button_hover_color="white"\|dropdown_text_color="black"\|button_color="white"\|text_color="#00C8` |
| `docs/unused-docs/changes/2026-03-19-theme-token-cleanup.md:100` | `- Command: `rg -n 'text_color="(green\|red\|gray\|white\|black)"\|fg_color="(white\|black\|gray[0-9]+)"\|button_hover_color="white"\|dropdown_fg_color="white"\|dropdown_text_color=` |
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:393` | `return "black" if luminance > 160 else "white"` |
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:396` | `return "white"` |
| `src/getmoredone/screens/vision_planning.py:285` | `text_color="white", width=130, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:294` | `text_color="white", width=130, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:303` | `text_color="white", width=130, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:547` | `text_color="white", width=120, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:566` | `text_color="white", width=120, height=28, corner_radius=6,` |
| `src/getmoredone/theme.py:120` | `"chip_text": "white",` |
| `src/getmoredone/theme.py:253` | `"white": palette["body_text"],` |
| `tests/test_date_picker.py:329` | `# 'white' and 'lightgray', which a hex-only check would wave straight through.` |
| `tests/test_date_picker.py:331` | `"white", "black", "darkblue", "lightblue", "lightgray", "lightgrey",` |

### `yellow`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:954` | `self._update_status_label("⏰ BREAK TIME! ⏰", "yellow")` |
| `src/getmoredone/theme.py:246` | `"yellow": palette["warning"],` |
| `tests/test_date_picker.py:332` | `"gray", "grey", "red", "green", "blue", "yellow", "orange", "pink",` |

### Theme API Occurrences

| File:Line | Snippet |
|---|---|
| `AGENTS.md:84` | `customtkinter.set_default_color_theme("path/to/theme.json")` |
| `AGENTS.md:94` | `- call set_appearance_mode(settings.appearance_mode)` |
| `AGENTS.md:95` | `- call set_default_color_theme(path_for_theme_name)` |
| `src/getmoredone/theme.py:57` | `ctk.set_appearance_mode(mode)` |
| `src/getmoredone/theme.py:65` | `ctk.set_default_color_theme(str(theme_path))` |
| `tests/test_color_inventory_sync.py:62` | `"src/z.py:9:     set_appearance_mode(\"dark\")",` |
| `tests/test_color_inventory_sync.py:63` | `"src/a.py:1:     set_default_color_theme(\"blue\")",` |
| `tests/test_plan_screen.py:160` | `ctk.set_appearance_mode("light")` |
| `tests/test_plan_screen.py:164` | `ctk.set_appearance_mode("system" if was_system else previous)` |
| `tests/test_priority_level_colors.py:130` | `ctk.set_appearance_mode("system" if was_system else original)` |
| `tests/test_priority_level_colors.py:307` | `ctk.set_appearance_mode(mode)` |
| `tests/test_priority_level_colors.py:742` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:98` | `ctk.set_appearance_mode("system" if was_system else original)` |
| `tests/test_time_block_colors.py:110` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:124` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:147` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:166` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:184` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:266` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:283` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:301` | `ctk.set_appearance_mode("Light")` |
| `tests/test_time_block_colors.py:318` | `ctk.set_appearance_mode("Dark")` |
| `tests/test_time_block_colors.py:337` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:362` | `ctk.set_appearance_mode(mode)` |
| `tests/test_time_block_colors.py:395` | `ctk.set_appearance_mode(mode)` |

### Tuple / Appearance Tuple Occurrences

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/item_editor.py:190` | `fg_color=("gray70", "gray30"))` |
| `src/getmoredone/screens/vps_segment_editor.py:35` | `self.selected_color = (` |
| `tests/test_color_inventory_sync.py:66` | `"src/z.py:40:    fg_color=(\"white\", \"black\")",` |
| `tests/test_color_inventory_sync.py:67` | `"src/a.py:2:     text_color=(\"black\", \"white\")",` |
| `tests/test_color_inventory_sync.py:68` | `"src/m.py:7:     border_color=(\"gray\", \"grey\")",` |

## 3) Replace Plan

Recommended migration targets:

- **Theme defaults (JSON-driven):**
- Base CTk widget palette defaults (`CTkButton`, `CTkFrame`, `CTkEntry`, `CTkCheckBox`, `CTkSwitch`, etc.) should stay in `/themes/*.json`.
- Remove one-off color literals that duplicate core palette choices.
- **Semantic tokens (code-level):**
- Route UI state colors through semantic names in `src/getmoredone/theme.py` (e.g., `primary`, `primary_hover`, `ghost_hover`, `selected_tint`, `critical_tint`, `success_tint`, `muted_text`, `border`).
- Convert direct `fg_color`/`hover_color`/`text_color` literals in screens to semantic token lookups.
- **Allowed data-driven colors:**
- Keep `segment_descriptions.color_hex` as the only domain data-driven color source.
- A segment color may fill a row only where that row's foreground is derived from it for contrast (`priority_levels.row_fill`); everywhere else keep it to accent/chip/stripe/icon usage.
- **Persisted settings:**
- Keep only settings-level color fields that are user-configurable and intentional (`drag_schedule_date_text_color`) plus theme selectors (`appearance_mode`, `theme_name`).

## 4) Hard Rule

**No new hard-coded colors except data-driven segment colors (`segment_descriptions.color_hex`).**

Enforcement recommendation: run the same `rg` commands in CI and diff this inventory after refactors.
