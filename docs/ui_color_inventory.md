# UI Color Inventory

Generated via deterministic `rg` scans of `src/`, `themes/` and `tools/generate_ctk_themes.py`: the UI code, the themes it loads, and the tool that writes them (CIV-A1, 2026-11-11).

Not covered: the tests, documents and plans that mention colours, and the named colours inside `assets/icons/*.svg`.

## Scan Commands

Rendered from `SCAN_COMMANDS` in `tools/color_audit.py`, so what is printed here is what produced this file. The four hand-written lines this replaced had drifted: they omitted three of the seven scans and every flag.

```bash
# widget
rg --sort path --no-config -n -H 'fg_color=|hover_color=|text_color=|border_color=|button_color=|progress_color=|selected_color=|corner_radius=|highlight_color=' src tools/generate_ctk_themes.py -g '*.py' -g '*.json'
# hex
rg --sort path --no-config -n -H '#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b' src tools/generate_ctk_themes.py -g '*.py' -g '*.json'
# named
rg --sort path --no-config -n -H -i '"(darkgreen|green|darkred|red|orange|blue|teal|cyan|yellow|white|black|gray[0-9]{0,3}|grey[0-9]{0,3})"|'"'"'(darkgreen|green|darkred|red|orange|blue|teal|cyan|yellow|white|black|gray[0-9]{0,3}|grey[0-9]{0,3})'"'"'' src tools/generate_ctk_themes.py -g '*.py' -g '*.json'
# theme_api
rg --sort path --no-config -n -H 'set_default_color_theme\(|set_appearance_mode\(' src tools/generate_ctk_themes.py -g '*.py' -g '*.json'
# tuples
rg --sort path --no-config -n -H '(fg_color|hover_color|text_color|border_color|button_color|progress_color|selected_color|highlight_color)\s*=\s*(\(|\[)' src tools/generate_ctk_themes.py -g '*.py' -g '*.json'
# app_settings
rg --sort path --no-config -n -H 'color|theme|appearance_mode|theme_name|drag_schedule_date_text_color|color_hex' src/getmoredone/app_settings.py
# theme_files
rg --sort path --no-config -n -H -i '#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|"(darkgreen|green|darkred|red|orange|blue|teal|cyan|yellow|white|black|gray[0-9]{0,3}|grey[0-9]{0,3})"|'"'"'(darkgreen|green|darkred|red|orange|blue|teal|cyan|yellow|white|black|gray[0-9]{0,3}|grey[0-9]{0,3})'"'"'' themes -g '*.json'
```

## 1) Summary Counts By Type

- Hex colors (match count): **1088**
- Named colors (match count): **649**
- Tuple colors / appearance tuples (match count): **2**
- CustomTkinter theme API usage (`set_default_color_theme`/`set_appearance_mode`) line count: **2**
- Widget explicit overrides (line count): **534**

Lines returned per scan. `scan_all` refuses an empty scan, so
this table is not the blindness check -- it is here to localise
a diff to one scan, and because section 1 omits the hex, named
and theme_files line counts.

| Scan | Lines |
|---|---:|
| `app_settings` | 25 |
| `hex` | 187 |
| `named` | 57 |
| `theme_api` | 2 |
| `theme_files` | 1292 |
| `tuples` | 2 |
| `widget` | 534 |

Widget override property breakdown:

| Property | Count |
|---|---:|
| `border_color` | 14 |
| `corner_radius` | 61 |
| `fg_color` | 249 |
| `hover_color` | 11 |
| `text_color` | 217 |

AppSettings persisted color/theme fields:

```text
src/getmoredone/app_settings.py:55:    appearance_mode: str = "dark"  # system | dark | light
src/getmoredone/app_settings.py:56:    theme_name: str = "apple_grey"
src/getmoredone/app_settings.py:69:    # tests/test_priority_level_colors.py::test_plcm21_every_level_has_a_settings_field
src/getmoredone/app_settings.py:78:    # The defaults are duplicated from theme.priority_level_fill_colors(),
src/getmoredone/app_settings.py:82:    priority_level_color_any_critical: str = "#DCFCE7"
src/getmoredone/app_settings.py:83:    priority_level_color_any_high: str = "#FEF3C7"
src/getmoredone/app_settings.py:84:    priority_level_color_no_high_or_critical: str = ""
src/getmoredone/app_settings.py:126:    # Drag Schedule date box text color (hex)
src/getmoredone/app_settings.py:127:    drag_schedule_date_text_color: str = "#FFFFFF"
src/getmoredone/app_settings.py:310:                settings.appearance_mode = cls._normalize_appearance_mode(
src/getmoredone/app_settings.py:311:                    settings.appearance_mode)
src/getmoredone/app_settings.py:312:                settings.theme_name = cls._normalize_theme_name(
src/getmoredone/app_settings.py:313:                    settings.theme_name)
src/getmoredone/app_settings.py:445:        self.appearance_mode = self._normalize_appearance_mode(
src/getmoredone/app_settings.py:446:            self.appearance_mode)
src/getmoredone/app_settings.py:447:        self.theme_name = self._normalize_theme_name(self.theme_name)
src/getmoredone/app_settings.py:626:        _normalize_theme_name defers its import for the same reason.
src/getmoredone/app_settings.py:696:    def _normalize_appearance_mode(value: Optional[str]) -> str:
src/getmoredone/app_settings.py:702:    def _normalize_theme_name(value: Optional[str]) -> str:
src/getmoredone/app_settings.py:703:        """Coerce a persisted theme name, using theme.py's list and no other.
src/getmoredone/app_settings.py:705:        This held a SECOND hardcoded copy of the theme names. Adding a theme to
src/getmoredone/app_settings.py:708:        load, because the new name was not in the copy. Picking a new theme
src/getmoredone/app_settings.py:711:        Imported inside the function: theme.py pulls in customtkinter, and
src/getmoredone/app_settings.py:715:        from .theme import normalize_theme_name
src/getmoredone/app_settings.py:717:        return normalize_theme_name(value)
```

Hex top values (20 of 244 distinct):

| Color | Count |
|---|---:|
| `#dce4ee` | 60 |
| `#ffffff` | 56 |
| `#979da2` | 52 |
| `#000000` | 35 |
| `#565b5e` | 34 |
| `#3e454a` | 27 |
| `#4a4d50` | 27 |
| `#939ba2` | 27 |
| `#949a9f` | 27 |
| `#1d1d1f` | 21 |
| `#2e1c8f` | 21 |
| `#6e6e73` | 17 |
| `#334155` | 16 |
| `#343638` | 16 |
| `#f9f9fa` | 16 |
| `#86868b` | 15 |
| `#111111` | 13 |
| `#d2d2d7` | 13 |
| `#f0e7ff` | 12 |
| `#42386d` | 11 |

Named top values (all 40 distinct):

| Color | Count |
|---|---:|
| `gray84` | 69 |
| `gray14` | 68 |
| `gray60` | 48 |
| `gray45` | 32 |
| `gray` | 31 |
| `gray20` | 29 |
| `gray40` | 28 |
| `gray41` | 28 |
| `gray90` | 25 |
| `gray74` | 24 |
| `gray53` | 19 |
| `gray55` | 19 |
| `gray100` | 18 |
| `gray28` | 18 |
| `gray29` | 18 |
| `gray10` | 14 |
| `gray95` | 14 |
| `gray70` | 11 |
| `gray21` | 10 |
| `gray36` | 9 |
| `gray62` | 9 |
| `gray75` | 9 |
| `gray80` | 9 |
| `green` | 9 |
| `white` | 9 |
| `gray16` | 8 |
| `gray50` | 8 |
| `gray52` | 8 |
| `gray13` | 7 |
| `gray65` | 7 |
| `gray85` | 7 |
| `red` | 7 |
| `orange` | 5 |
| `blue` | 4 |
| `gray30` | 3 |
| `darkred` | 2 |
| `grey` | 2 |
| `yellow` | 2 |
| `black` | 1 |
| `gray17` | 1 |

## 2) Complete Occurrence Table (Grouped by Color Value, then File)

Each row is from grep output and includes `file:line` and a short snippet.

### `#000000`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/color_contrast.py:161` | `dark: str = "#000000",` |
| `src/getmoredone/color_contrast.py:168` | `def pick_text_color(bg_hex: str, light: str = "#FFFFFF", dark: str = "#000000") -> str:` |
| `src/getmoredone/color_contrast.py:173` | `return "#000000"` |
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

### `#000365`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:63` | `800: "#40299C", 900: "#2E1C8F", 950: "#000365",` |

### `#00bcd4`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1164` | `('seg-6', 'Recreation', 'Hobbies and leisure activities', '#00BCD4', 6),` |

### `#00c800`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:467` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

### `#0284c7`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:461` | `"Week": "#0284C7",` |

### `#052e16`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:146` | ``# deep -- the `low` fill is #052E16 -- and `success_strong`'s dark`` |
| `src/getmoredone/theme.py:377` | `"low": "#052E16",` |

### `#059669`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:460` | `"Month": "#059669",` |

### `#0b368d`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_manager.py:220` | ``` ``#+12345`` raised nothing and derived ``#0B368D`` from a ``` |

### `#0d9488`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:457` | `"Annual Plan": "#0D9488",` |

### `#0ea5e9`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#100f47`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:109` | `GROUND_GRADIENT = ("#100F47", "#291E68")` |

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
| `src/getmoredone/vps_manager.py:1514` | `palette = ["#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#F97316"]` |

### `#111111`

| File:Line | Snippet |
|---|---|
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
| `src/getmoredone/theme.py:136` | `"success_strong": "#166534" if mode == "light" else "#14532D",` |

### `#14b8a6`

| File:Line | Snippet |
|---|---|
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

### `#15803d`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:343` | `"low": "#15803D",` |

### `#166534`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:136` | `"success_strong": "#166534" if mode == "light" else "#14532D",` |
| `src/getmoredone/theme.py:150` | `"scheduled_mark": "#166534" if mode == "light" else "#4ADE80",` |
| `src/getmoredone/theme.py:306` | `"low": "#166534",` |

### `#171447`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:43` | `MIDNIGHT = "#171447"` |
| `src/getmoredone/brand.py:88` | `800: "#42386D", 900: "#292256", 950: "#171447",` |
| `themes/davipa.json:19` | `"#171447"` |

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

### `#223247`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:135` | `"selected_tint": "#E6EEF8" if mode == "light" else "#223247",` |

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
| `src/getmoredone/theme.py:456` | `"Annual Vision": "#2563EB",` |

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

### `#334155`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/segment_color_utils.py:10` | `DEFAULT_SEGMENT_COLOR = "#334155"` |
| `src/getmoredone/screens/settings_vsp_segments.py:13` | `DEFAULT_INDICATOR_COLOR = "#334155"` |
| `src/getmoredone/screens/vision_segments.py:13` | `DEFAULT_SWATCH_COLOR = "#334155"` |
| `src/getmoredone/screens/vision_segments.py:399` | `color_row, color = self._color_input(f, (row or {}).get("color_hex", "#334155"))` |
| `src/getmoredone/vps_manager.py:1433` | `color_map[name] = row["color_hex"] or "#334155"` |
| `src/getmoredone/vps_manager.py:1443` | `color = (row["color_hex"] or "").strip() or "#334155"` |
| `src/getmoredone/vps_manager_taxonomy.py:1010` | `COALESCE(sd.color_hex, '#334155') AS color_hex,` |
| `themes/grey.json:35` | `"#334155"` |
| `themes/grey.json:87` | `"#334155"` |
| `themes/grey.json:120` | `"#334155"` |
| `themes/grey.json:145` | `"#334155"` |
| `themes/grey.json:173` | `"#334155"` |
| `themes/grey.json:195` | `"#334155"` |
| `themes/grey.json:206` | `"#334155"` |
| `themes/grey.json:275` | `"#334155"` |
| `tools/generate_ctk_themes.py:47` | `"grey": ["#475569", "#334155"],` |

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

### `#360031`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:73` | `800: "#78006E", 900: "#52004B", 950: "#360031",` |

### `#3a2328`

| File:Line | Snippet |
|---|---|
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
| `src/getmoredone/theme.py:467` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

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

### `#450a0a`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:374` | `"critical": "#450A0A",` |

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

### `#4ade80`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:150` | `"scheduled_mark": "#166534" if mode == "light" else "#4ADE80",` |
| `src/getmoredone/theme.py:313` | `"low": "#4ADE80",` |

### `#4b1b2b`

| File:Line | Snippet |
|---|---|
| `themes/pink.json:214` | `"#4B1B2B"` |

### `#4b5563`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:442` | `padding = "#4B5563" if mode == "light" else "#9CA3AF"` |
| `themes/black_white.json:27` | `"#4B5563"` |
| `tools/generate_ctk_themes.py:78` | `("CTkFrame", "border_color"): ["#D1D5DB", "#4B5563"],` |

### `#4caf50`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/vps_schema.py:1159` | `('seg-1', 'Health', 'Physical and mental wellbeing', '#4CAF50', 1),` |

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
| `src/getmoredone/screens/settings_vsp_segments.py:250` | `color_hex = subsegment.get("color_hex") or "#64748B"` |
| `src/getmoredone/screens/settings_vsp_segments.py:280` | `initial = subsegment.get("color_hex") or "#64748B"` |
| `src/getmoredone/vps_manager.py:160` | `DEFAULT_SUBSEGMENT_BASE = "#64748B"` |
| `src/getmoredone/vps_manager.py:1511` | `return "#64748B"` |
| `src/getmoredone/vps_manager_taxonomy.py:396` | `sub_color = (sub_row["color_hex"] if sub_row else "") or "#64748B"` |

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
| `src/getmoredone/theme.py:455` | `"TL Vision": "#7C3AED",` |
| `themes/purple.json:35` | `"#7C3AED"` |
| `themes/purple.json:87` | `"#7C3AED"` |
| `themes/purple.json:120` | `"#7C3AED"` |
| `themes/purple.json:145` | `"#7C3AED"` |
| `themes/purple.json:173` | `"#7C3AED"` |
| `themes/purple.json:195` | `"#7C3AED"` |
| `themes/purple.json:206` | `"#7C3AED"` |
| `themes/purple.json:275` | `"#7C3AED"` |
| `tools/generate_ctk_themes.py:49` | `"purple": ["#8B5CF6", "#7C3AED"],` |

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

### `#888888`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/vision_planning.py:280` | `color = item.get('segment_color') or "#888888"` |
| `src/getmoredone/screens/vision_planning.py:542` | `color = item.get('segment_color') or "#888888"` |
| `src/getmoredone/screens/vision_planning.py:561` | `color = item.get('segment_color') or "#888888"` |

### `#897cb2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/brand.py:87` | `400: "#A396CB", 500: "#897CB2", 600: "#71659B", 700: "#5A4F85",` |

### `#8b5cf6`

| File:Line | Snippet |
|---|---|
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
| `src/getmoredone/theme.py:305` | `"medium": "#92400E",` |

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
| `src/getmoredone/screens/vision_segments.py:538` | `color_row, color = self._color_input(f, (row or {}).get("color_hex", "#94A3B8"))` |
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
| `src/getmoredone/theme.py:132` | `"danger_hover": "#991B1B",` |
| `src/getmoredone/theme.py:303` | `"critical": "#991B1B",` |

### `#9a3412`

| File:Line | Snippet |
|---|---|
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
| `src/getmoredone/theme.py:442` | `padding = "#4B5563" if mode == "light" else "#9CA3AF"` |
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
| `src/getmoredone/theme.py:467` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

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

### `#abc`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/color_contrast.py:50` | ```exception. A three-digit ``#ABC`` is expanded, because that is a form people``` |
| `src/getmoredone/screens/vps_segment_editor.py:216` | ```Accepts ``#abc`` and a missing ``#``, which the old check refused --``` |
| `src/getmoredone/screens/vps_segment_editor.py:242` | ```# text. ``validate_color`` accepts ``#abc`` and a missing ``#``, and``` |
| `src/getmoredone/vps_manager.py:206` | ``` ``normalize_hex_color`` expands ``#abc`` and supplies a missing ``#``. ``` |
| `src/getmoredone/vps_manager_taxonomy.py:356` | ```# typed; once that gate reads ``#abc`` and ``abcdef``, both became``` |
| `src/getmoredone/vps_manager_taxonomy.py:449` | ```gate reads ``#abc``, storing the text as given would write a``` |

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
| `src/getmoredone/theme.py:110` | `"on_primary": _theme_value("CTkButton", "text_color", "#DCE4EE"),` |
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
| `src/getmoredone/app_settings.py:82` | `priority_level_color_any_critical: str = "#DCFCE7"` |
| `src/getmoredone/theme.py:137` | `"on_strong": "#ECFDF5" if mode == "light" else "#DCFCE7",` |
| `src/getmoredone/theme.py:370` | `"low": "#DCFCE7",` |
| `src/getmoredone/theme.py:421` | `LEVEL_ANY_CRITICAL: "#DCFCE7",` |

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
| `src/getmoredone/theme.py:459` | `"Quarter": "#EA580C",` |

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
| `src/getmoredone/theme.py:467` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |
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
| `src/getmoredone/theme.py:458` | `"Annual Initiative": "#F59E0B",` |
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

### `#f97316`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:467` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |
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
| `src/getmoredone/theme.py:151` | `"unscheduled_mark": "#B91C1C" if mode == "light" else "#FCA5A5",` |
| `src/getmoredone/theme.py:261` | `"date_overdue": "#FCA5A5",` |

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

### `#fdecec`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:130` | `"critical_tint": "#FDECEC" if mode == "light" else "#3A2328",` |

### `#fee2e2`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:133` | `"on_danger": "#FEE2E2",` |
| `src/getmoredone/theme.py:367` | `"critical": "#FEE2E2",` |

### `#fef3c7`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/app_settings.py:83` | `priority_level_color_any_high: str = "#FEF3C7"` |
| `src/getmoredone/theme.py:369` | `"medium": "#FEF3C7",` |
| `src/getmoredone/theme.py:422` | `LEVEL_ANY_HIGH: "#FEF3C7",` |

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
| `src/getmoredone/theme.py:467` | `return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")` |

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

### `#ffffff`

| File:Line | Snippet |
|---|---|
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
| `src/getmoredone/screens/settings_priority_colors.py:199` | ``` ``#FFFFFF``, and a user who typed a colour they meant has no way to ``` |
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
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:393` | `return "black" if luminance > 160 else "white"` |

### `blue`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:892` | `status_color = "green" if self.timer_state == self.RUNNING else "blue"` |
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `src/getmoredone/theme.py:248` | `"blue": palette["primary"],` |
| `tools/generate_ctk_themes.py:48` | `"blue": ["#3B8ED0", "#1F6AA5"],` |

### `darkred`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/vision_planning.py:315` | `fg_color="darkred", hover_color="red",` |
| `src/getmoredone/screens/vision_planning.py:577` | `fg_color="darkred", hover_color="red",` |

### `gray`

| File:Line | Snippet |
|---|---|
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

### `gray10`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:3` | `"fg_color": ["gray95", "gray10"]` |
| `themes/base_dark_blue.json:6` | `"fg_color": ["gray95", "gray10"]` |
| `themes/blue.json:5` | `"gray10"` |
| `themes/blue.json:11` | `"gray10"` |
| `themes/green.json:5` | `"gray10"` |
| `themes/green.json:11` | `"gray10"` |
| `themes/grey.json:5` | `"gray10"` |
| `themes/grey.json:11` | `"gray10"` |
| `themes/orange.json:5` | `"gray10"` |
| `themes/orange.json:11` | `"gray10"` |
| `themes/pink.json:5` | `"gray10"` |
| `themes/pink.json:11` | `"gray10"` |
| `themes/purple.json:5` | `"gray10"` |
| `themes/purple.json:11` | `"gray10"` |

### `gray100`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:128` | `"gray100"` |
| `themes/apple_grey.json:302` | `"gray100",` |
| `themes/base_dark_blue.json:54` | `"button_hover_color": ["gray20", "gray100"],` |
| `themes/base_dark_blue.json:124` | `"fg_color": ["gray100", "gray20"],` |
| `themes/black_white.json:128` | `"gray100"` |
| `themes/black_white.json:302` | `"gray100",` |
| `themes/blue.json:128` | `"gray100"` |
| `themes/blue.json:302` | `"gray100",` |
| `themes/green.json:128` | `"gray100"` |
| `themes/green.json:302` | `"gray100",` |
| `themes/grey.json:128` | `"gray100"` |
| `themes/grey.json:302` | `"gray100",` |
| `themes/orange.json:128` | `"gray100"` |
| `themes/orange.json:302` | `"gray100",` |
| `themes/pink.json:128` | `"gray100"` |
| `themes/pink.json:302` | `"gray100",` |
| `themes/purple.json:128` | `"gray100"` |
| `themes/purple.json:302` | `"gray100",` |

### `gray13`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:11` | `"fg_color": ["gray90", "gray13"],` |
| `themes/blue.json:19` | `"gray13"` |
| `themes/green.json:19` | `"gray13"` |
| `themes/grey.json:19` | `"gray13"` |
| `themes/orange.json:19` | `"gray13"` |
| `themes/pink.json:19` | `"gray13"` |
| `themes/purple.json:19` | `"gray13"` |

### `gray14`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:102` | `"gray14",` |
| `themes/apple_grey.json:131` | `"gray14",` |
| `themes/apple_grey.json:156` | `"gray14",` |
| `themes/apple_grey.json:245` | `"gray14",` |
| `themes/apple_grey.json:310` | `"gray14",` |
| `themes/apple_grey.json:338` | `"gray14",` |
| `themes/base_dark_blue.json:27` | `"text_color": ["gray14", "gray84"]` |
| `themes/base_dark_blue.json:34` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:44` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:55` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:65` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:100` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:126` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:136` | `"text_color": ["gray14", "gray84"]` |
| `themes/black_white.json:102` | `"gray14",` |
| `themes/black_white.json:131` | `"gray14",` |
| `themes/black_white.json:156` | `"gray14",` |
| `themes/black_white.json:245` | `"gray14",` |
| `themes/black_white.json:310` | `"gray14",` |
| `themes/black_white.json:338` | `"gray14",` |
| `themes/blue.json:58` | `"gray14",` |
| `themes/blue.json:74` | `"gray14",` |
| `themes/blue.json:102` | `"gray14",` |
| `themes/blue.json:131` | `"gray14",` |
| `themes/blue.json:156` | `"gray14",` |
| `themes/blue.json:245` | `"gray14",` |
| `themes/blue.json:310` | `"gray14",` |
| `themes/blue.json:338` | `"gray14",` |
| `themes/green.json:58` | `"gray14",` |
| `themes/green.json:74` | `"gray14",` |
| `themes/green.json:102` | `"gray14",` |
| `themes/green.json:131` | `"gray14",` |
| `themes/green.json:156` | `"gray14",` |
| `themes/green.json:245` | `"gray14",` |
| `themes/green.json:310` | `"gray14",` |
| `themes/green.json:338` | `"gray14",` |
| `themes/grey.json:58` | `"gray14",` |
| `themes/grey.json:74` | `"gray14",` |
| `themes/grey.json:102` | `"gray14",` |
| `themes/grey.json:131` | `"gray14",` |
| `themes/grey.json:156` | `"gray14",` |
| `themes/grey.json:245` | `"gray14",` |
| `themes/grey.json:310` | `"gray14",` |
| `themes/grey.json:338` | `"gray14",` |
| `themes/orange.json:58` | `"gray14",` |
| `themes/orange.json:74` | `"gray14",` |
| `themes/orange.json:102` | `"gray14",` |
| `themes/orange.json:131` | `"gray14",` |
| `themes/orange.json:156` | `"gray14",` |
| `themes/orange.json:245` | `"gray14",` |
| `themes/orange.json:310` | `"gray14",` |
| `themes/orange.json:338` | `"gray14",` |
| `themes/pink.json:58` | `"gray14",` |
| `themes/pink.json:74` | `"gray14",` |
| `themes/pink.json:102` | `"gray14",` |
| `themes/pink.json:131` | `"gray14",` |
| `themes/pink.json:156` | `"gray14",` |
| `themes/pink.json:245` | `"gray14",` |
| `themes/pink.json:310` | `"gray14",` |
| `themes/pink.json:338` | `"gray14",` |
| `themes/purple.json:58` | `"gray14",` |
| `themes/purple.json:74` | `"gray14",` |
| `themes/purple.json:102` | `"gray14",` |
| `themes/purple.json:131` | `"gray14",` |
| `themes/purple.json:156` | `"gray14",` |
| `themes/purple.json:245` | `"gray14",` |
| `themes/purple.json:310` | `"gray14",` |
| `themes/purple.json:338` | `"gray14",` |

### `gray16`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/chip_table.py:348` | `# themes ("gray16" in dark mode), which pick_text_color` |
| `themes/base_dark_blue.json:12` | `"top_fg_color": ["gray85", "gray16"],` |
| `themes/blue.json:23` | `"gray16"` |
| `themes/green.json:23` | `"gray16"` |
| `themes/grey.json:23` | `"gray16"` |
| `themes/orange.json:23` | `"gray16"` |
| `themes/pink.json:23` | `"gray16"` |
| `themes/purple.json:23` | `"gray16"` |

### `gray17`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:104` | `"surface": _theme_value("CTkFrame", "fg_color", "gray17"),` |

### `gray20`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:281` | `) or subsegment_color or self.segment_colors_by_id.get(segment_id, "gray20")` |
| `src/getmoredone/theme.py:95` | `input_surface = _theme_value("CTkComboBox", "fg_color", _theme_value("CTkEntry", "fg_color", "gray20"))` |
| `themes/apple_grey.json:127` | `"gray20",` |
| `themes/apple_grey.json:303` | `"gray20"` |
| `themes/apple_grey.json:331` | `"gray20"` |
| `themes/base_dark_blue.json:54` | `"button_hover_color": ["gray20", "gray100"],` |
| `themes/base_dark_blue.json:124` | `"fg_color": ["gray100", "gray20"],` |
| `themes/base_dark_blue.json:134` | `"fg_color": ["gray90", "gray20"],` |
| `themes/black_white.json:127` | `"gray20",` |
| `themes/black_white.json:303` | `"gray20"` |
| `themes/black_white.json:331` | `"gray20"` |
| `themes/blue.json:127` | `"gray20",` |
| `themes/blue.json:303` | `"gray20"` |
| `themes/blue.json:331` | `"gray20"` |
| `themes/green.json:127` | `"gray20",` |
| `themes/green.json:303` | `"gray20"` |
| `themes/green.json:331` | `"gray20"` |
| `themes/grey.json:127` | `"gray20",` |
| `themes/grey.json:303` | `"gray20"` |
| `themes/grey.json:331` | `"gray20"` |
| `themes/orange.json:127` | `"gray20",` |
| `themes/orange.json:303` | `"gray20"` |
| `themes/orange.json:331` | `"gray20"` |
| `themes/pink.json:127` | `"gray20",` |
| `themes/pink.json:303` | `"gray20"` |
| `themes/pink.json:331` | `"gray20"` |
| `themes/purple.json:127` | `"gray20",` |
| `themes/purple.json:303` | `"gray20"` |
| `themes/purple.json:331` | `"gray20"` |

### `gray21`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:117` | `"surface_subtle": _theme_value("CTkFrame", "top_fg_color", "gray21"),` |
| `themes/apple_grey.json:325` | `"gray21"` |
| `themes/base_dark_blue.json:131` | `"label_fg_color": ["gray80", "gray21"]` |
| `themes/black_white.json:325` | `"gray21"` |
| `themes/blue.json:325` | `"gray21"` |
| `themes/green.json:325` | `"gray21"` |
| `themes/grey.json:325` | `"gray21"` |
| `themes/orange.json:325` | `"gray21"` |
| `themes/pink.json:325` | `"gray21"` |
| `themes/purple.json:325` | `"gray21"` |

### `gray28`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:105` | `"ghost_hover": _theme_value("DropdownMenu", "hover_color", "gray28"),` |
| `src/getmoredone/theme.py:106` | `"border": _theme_value("CTkFrame", "border_color", "gray28"),` |
| `themes/apple_grey.json:335` | `"gray28"` |
| `themes/base_dark_blue.json:13` | `"border_color": ["gray65", "gray28"]` |
| `themes/base_dark_blue.json:135` | `"hover_color": ["gray75", "gray28"],` |
| `themes/black_white.json:335` | `"gray28"` |
| `themes/blue.json:27` | `"gray28"` |
| `themes/blue.json:335` | `"gray28"` |
| `themes/green.json:27` | `"gray28"` |
| `themes/green.json:335` | `"gray28"` |
| `themes/grey.json:27` | `"gray28"` |
| `themes/grey.json:335` | `"gray28"` |
| `themes/orange.json:27` | `"gray28"` |
| `themes/orange.json:335` | `"gray28"` |
| `themes/pink.json:27` | `"gray28"` |
| `themes/pink.json:335` | `"gray28"` |
| `themes/purple.json:27` | `"gray28"` |
| `themes/purple.json:335` | `"gray28"` |

### `gray29`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:271` | `"gray29"` |
| `themes/apple_grey.json:283` | `"gray29"` |
| `themes/base_dark_blue.json:113` | `"fg_color": ["#979DA2", "gray29"],` |
| `themes/base_dark_blue.json:116` | `"unselected_color": ["#979DA2", "gray29"],` |
| `themes/black_white.json:271` | `"gray29"` |
| `themes/black_white.json:283` | `"gray29"` |
| `themes/blue.json:271` | `"gray29"` |
| `themes/blue.json:283` | `"gray29"` |
| `themes/green.json:271` | `"gray29"` |
| `themes/green.json:283` | `"gray29"` |
| `themes/grey.json:271` | `"gray29"` |
| `themes/grey.json:283` | `"gray29"` |
| `themes/orange.json:271` | `"gray29"` |
| `themes/orange.json:283` | `"gray29"` |
| `themes/pink.json:271` | `"gray29"` |
| `themes/pink.json:283` | `"gray29"` |
| `themes/purple.json:271` | `"gray29"` |
| `themes/purple.json:283` | `"gray29"` |

### `gray30`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/column_resize.py:280` | `fg_color=fg_color if fg_color is not None else ("gray70", "gray30"),` |
| `src/getmoredone/screens/item_editor.py:190` | `fg_color=("gray70", "gray30"))` |
| `src/getmoredone/theme.py:119` | `"chip_bg": "gray30",` |

### `gray36`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:123` | `"gray36",` |
| `themes/base_dark_blue.json:53` | `"button_color": ["gray36", "#D5D9DE"],` |
| `themes/black_white.json:123` | `"gray36",` |
| `themes/blue.json:123` | `"gray36",` |
| `themes/green.json:123` | `"gray36",` |
| `themes/grey.json:123` | `"gray36",` |
| `themes/orange.json:123` | `"gray36",` |
| `themes/pink.json:123` | `"gray36",` |
| `themes/purple.json:123` | `"gray36",` |

### `gray40`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:190` | `"gray40",` |
| `themes/apple_grey.json:262` | `"gray40",` |
| `themes/apple_grey.json:318` | `"gray40",` |
| `themes/base_dark_blue.json:81` | `"progress_color": ["gray40", "#AAB0B5"],` |
| `themes/base_dark_blue.json:108` | `"button_hover_color": ["gray40", "gray53"]` |
| `themes/base_dark_blue.json:128` | `"scrollbar_button_hover_color": ["gray40", "gray53"]` |
| `themes/black_white.json:190` | `"gray40",` |
| `themes/black_white.json:262` | `"gray40",` |
| `themes/black_white.json:318` | `"gray40",` |
| `themes/blue.json:190` | `"gray40",` |
| `themes/blue.json:262` | `"gray40",` |
| `themes/blue.json:318` | `"gray40",` |
| `themes/davipa.json:318` | `"gray40",` |
| `themes/green.json:190` | `"gray40",` |
| `themes/green.json:262` | `"gray40",` |
| `themes/green.json:318` | `"gray40",` |
| `themes/grey.json:190` | `"gray40",` |
| `themes/grey.json:262` | `"gray40",` |
| `themes/grey.json:318` | `"gray40",` |
| `themes/orange.json:190` | `"gray40",` |
| `themes/orange.json:262` | `"gray40",` |
| `themes/orange.json:318` | `"gray40",` |
| `themes/pink.json:190` | `"gray40",` |
| `themes/pink.json:262` | `"gray40",` |
| `themes/pink.json:318` | `"gray40",` |
| `themes/purple.json:190` | `"gray40",` |
| `themes/purple.json:262` | `"gray40",` |
| `themes/purple.json:318` | `"gray40",` |

### `gray41`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:259` | `"gray41"` |
| `themes/apple_grey.json:287` | `"gray41"` |
| `themes/apple_grey.json:315` | `"gray41"` |
| `themes/base_dark_blue.json:107` | `"button_color": ["gray55", "gray41"],` |
| `themes/base_dark_blue.json:117` | `"unselected_hover_color": ["gray70", "gray41"],` |
| `themes/base_dark_blue.json:127` | `"scrollbar_button_color": ["gray55", "gray41"],` |
| `themes/black_white.json:259` | `"gray41"` |
| `themes/black_white.json:287` | `"gray41"` |
| `themes/black_white.json:315` | `"gray41"` |
| `themes/blue.json:259` | `"gray41"` |
| `themes/blue.json:287` | `"gray41"` |
| `themes/blue.json:315` | `"gray41"` |
| `themes/davipa.json:315` | `"gray41"` |
| `themes/green.json:259` | `"gray41"` |
| `themes/green.json:287` | `"gray41"` |
| `themes/green.json:315` | `"gray41"` |
| `themes/grey.json:259` | `"gray41"` |
| `themes/grey.json:287` | `"gray41"` |
| `themes/grey.json:315` | `"gray41"` |
| `themes/orange.json:259` | `"gray41"` |
| `themes/orange.json:287` | `"gray41"` |
| `themes/orange.json:315` | `"gray41"` |
| `themes/pink.json:259` | `"gray41"` |
| `themes/pink.json:287` | `"gray41"` |
| `themes/pink.json:315` | `"gray41"` |
| `themes/purple.json:259` | `"gray41"` |
| `themes/purple.json:287` | `"gray41"` |
| `themes/purple.json:315` | `"gray41"` |

### `gray45`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:45` | `"text_color_disabled": ["gray60", "gray45"]` |
| `themes/base_dark_blue.json:56` | `"text_color_disabled": ["gray60", "gray45"]` |
| `themes/base_dark_blue.json:66` | `"text_color_disabled": ["gray60", "gray45"]` |
| `themes/base_dark_blue.json:101` | `"text_color_disabled": ["gray50", "gray45"]` |
| `themes/blue.json:107` | `"gray45"` |
| `themes/blue.json:136` | `"gray45"` |
| `themes/blue.json:161` | `"gray45"` |
| `themes/blue.json:250` | `"gray45"` |
| `themes/davipa.json:107` | `"gray45"` |
| `themes/davipa.json:136` | `"gray45"` |
| `themes/davipa.json:161` | `"gray45"` |
| `themes/davipa.json:250` | `"gray45"` |
| `themes/green.json:107` | `"gray45"` |
| `themes/green.json:136` | `"gray45"` |
| `themes/green.json:161` | `"gray45"` |
| `themes/green.json:250` | `"gray45"` |
| `themes/grey.json:107` | `"gray45"` |
| `themes/grey.json:136` | `"gray45"` |
| `themes/grey.json:161` | `"gray45"` |
| `themes/grey.json:250` | `"gray45"` |
| `themes/orange.json:107` | `"gray45"` |
| `themes/orange.json:136` | `"gray45"` |
| `themes/orange.json:161` | `"gray45"` |
| `themes/orange.json:250` | `"gray45"` |
| `themes/pink.json:107` | `"gray45"` |
| `themes/pink.json:136` | `"gray45"` |
| `themes/pink.json:161` | `"gray45"` |
| `themes/pink.json:250` | `"gray45"` |
| `themes/purple.json:107` | `"gray45"` |
| `themes/purple.json:136` | `"gray45"` |
| `themes/purple.json:161` | `"gray45"` |
| `themes/purple.json:250` | `"gray45"` |

### `gray50`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:101` | `"text_color_disabled": ["gray50", "gray45"]` |
| `themes/blue.json:249` | `"gray50",` |
| `themes/davipa.json:249` | `"gray50",` |
| `themes/green.json:249` | `"gray50",` |
| `themes/grey.json:249` | `"gray50",` |
| `themes/orange.json:249` | `"gray50",` |
| `themes/pink.json:249` | `"gray50",` |
| `themes/purple.json:249` | `"gray50",` |

### `gray52`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:35` | `"placeholder_text_color": ["gray52", "gray62"]` |
| `themes/blue.json:78` | `"gray52",` |
| `themes/davipa.json:78` | `"gray52",` |
| `themes/green.json:78` | `"gray52",` |
| `themes/grey.json:78` | `"gray52",` |
| `themes/orange.json:78` | `"gray52",` |
| `themes/pink.json:78` | `"gray52",` |
| `themes/purple.json:78` | `"gray52",` |

### `gray53`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:263` | `"gray53"` |
| `themes/apple_grey.json:319` | `"gray53"` |
| `themes/base_dark_blue.json:108` | `"button_hover_color": ["gray40", "gray53"]` |
| `themes/base_dark_blue.json:128` | `"scrollbar_button_hover_color": ["gray40", "gray53"]` |
| `themes/black_white.json:263` | `"gray53"` |
| `themes/black_white.json:319` | `"gray53"` |
| `themes/blue.json:263` | `"gray53"` |
| `themes/blue.json:319` | `"gray53"` |
| `themes/davipa.json:319` | `"gray53"` |
| `themes/green.json:263` | `"gray53"` |
| `themes/green.json:319` | `"gray53"` |
| `themes/grey.json:263` | `"gray53"` |
| `themes/grey.json:319` | `"gray53"` |
| `themes/orange.json:263` | `"gray53"` |
| `themes/orange.json:319` | `"gray53"` |
| `themes/pink.json:263` | `"gray53"` |
| `themes/pink.json:319` | `"gray53"` |
| `themes/purple.json:263` | `"gray53"` |
| `themes/purple.json:319` | `"gray53"` |

### `gray55`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:258` | `"gray55",` |
| `themes/apple_grey.json:314` | `"gray55",` |
| `themes/base_dark_blue.json:107` | `"button_color": ["gray55", "gray41"],` |
| `themes/base_dark_blue.json:127` | `"scrollbar_button_color": ["gray55", "gray41"],` |
| `themes/black_white.json:258` | `"gray55",` |
| `themes/black_white.json:314` | `"gray55",` |
| `themes/blue.json:258` | `"gray55",` |
| `themes/blue.json:314` | `"gray55",` |
| `themes/davipa.json:314` | `"gray55",` |
| `themes/green.json:258` | `"gray55",` |
| `themes/green.json:314` | `"gray55",` |
| `themes/grey.json:258` | `"gray55",` |
| `themes/grey.json:314` | `"gray55",` |
| `themes/orange.json:258` | `"gray55",` |
| `themes/orange.json:314` | `"gray55",` |
| `themes/pink.json:258` | `"gray55",` |
| `themes/pink.json:314` | `"gray55",` |
| `themes/purple.json:258` | `"gray55",` |
| `themes/purple.json:314` | `"gray55",` |

### `gray60`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:22` | `"text_color_disabled": ["gray74", "gray60"]` |
| `themes/base_dark_blue.json:45` | `"text_color_disabled": ["gray60", "gray45"]` |
| `themes/base_dark_blue.json:56` | `"text_color_disabled": ["gray60", "gray45"]` |
| `themes/base_dark_blue.json:66` | `"text_color_disabled": ["gray60", "gray45"]` |
| `themes/base_dark_blue.json:91` | `"text_color_disabled": ["gray74", "gray60"]` |
| `themes/base_dark_blue.json:119` | `"text_color_disabled": ["gray74", "gray60"]` |
| `themes/blue.json:51` | `"gray60"` |
| `themes/blue.json:106` | `"gray60",` |
| `themes/blue.json:135` | `"gray60",` |
| `themes/blue.json:160` | `"gray60",` |
| `themes/blue.json:222` | `"gray60"` |
| `themes/blue.json:295` | `"gray60"` |
| `themes/davipa.json:51` | `"gray60"` |
| `themes/davipa.json:106` | `"gray60",` |
| `themes/davipa.json:135` | `"gray60",` |
| `themes/davipa.json:160` | `"gray60",` |
| `themes/davipa.json:222` | `"gray60"` |
| `themes/davipa.json:295` | `"gray60"` |
| `themes/green.json:51` | `"gray60"` |
| `themes/green.json:106` | `"gray60",` |
| `themes/green.json:135` | `"gray60",` |
| `themes/green.json:160` | `"gray60",` |
| `themes/green.json:222` | `"gray60"` |
| `themes/green.json:295` | `"gray60"` |
| `themes/grey.json:51` | `"gray60"` |
| `themes/grey.json:106` | `"gray60",` |
| `themes/grey.json:135` | `"gray60",` |
| `themes/grey.json:160` | `"gray60",` |
| `themes/grey.json:222` | `"gray60"` |
| `themes/grey.json:295` | `"gray60"` |
| `themes/orange.json:51` | `"gray60"` |
| `themes/orange.json:106` | `"gray60",` |
| `themes/orange.json:135` | `"gray60",` |
| `themes/orange.json:160` | `"gray60",` |
| `themes/orange.json:222` | `"gray60"` |
| `themes/orange.json:295` | `"gray60"` |
| `themes/pink.json:51` | `"gray60"` |
| `themes/pink.json:106` | `"gray60",` |
| `themes/pink.json:135` | `"gray60",` |
| `themes/pink.json:160` | `"gray60",` |
| `themes/pink.json:222` | `"gray60"` |
| `themes/pink.json:295` | `"gray60"` |
| `themes/purple.json:51` | `"gray60"` |
| `themes/purple.json:106` | `"gray60",` |
| `themes/purple.json:135` | `"gray60",` |
| `themes/purple.json:160` | `"gray60",` |
| `themes/purple.json:222` | `"gray60"` |
| `themes/purple.json:295` | `"gray60"` |

### `gray62`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:93` | `muted_text = _theme_value("CTkEntry", "placeholder_text_color", "gray62")` |
| `themes/base_dark_blue.json:35` | `"placeholder_text_color": ["gray52", "gray62"]` |
| `themes/blue.json:79` | `"gray62"` |
| `themes/davipa.json:79` | `"gray62"` |
| `themes/green.json:79` | `"gray62"` |
| `themes/grey.json:79` | `"gray62"` |
| `themes/orange.json:79` | `"gray62"` |
| `themes/pink.json:79` | `"gray62"` |
| `themes/purple.json:79` | `"gray62"` |

### `gray65`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:13` | `"border_color": ["gray65", "gray28"]` |
| `themes/blue.json:26` | `"gray65",` |
| `themes/green.json:26` | `"gray65",` |
| `themes/grey.json:26` | `"gray65",` |
| `themes/orange.json:26` | `"gray65",` |
| `themes/pink.json:26` | `"gray65",` |
| `themes/purple.json:26` | `"gray65",` |

### `gray70`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/column_resize.py:280` | `fg_color=fg_color if fg_color is not None else ("gray70", "gray30"),` |
| `src/getmoredone/screens/item_editor.py:190` | `fg_color=("gray70", "gray30"))` |
| `themes/apple_grey.json:286` | `"gray70",` |
| `themes/base_dark_blue.json:117` | `"unselected_hover_color": ["gray70", "gray41"],` |
| `themes/black_white.json:286` | `"gray70",` |
| `themes/blue.json:286` | `"gray70",` |
| `themes/green.json:286` | `"gray70",` |
| `themes/grey.json:286` | `"gray70",` |
| `themes/orange.json:286` | `"gray70",` |
| `themes/pink.json:286` | `"gray70",` |
| `themes/purple.json:286` | `"gray70",` |

### `gray74`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:22` | `"text_color_disabled": ["gray74", "gray60"]` |
| `themes/base_dark_blue.json:91` | `"text_color_disabled": ["gray74", "gray60"]` |
| `themes/base_dark_blue.json:119` | `"text_color_disabled": ["gray74", "gray60"]` |
| `themes/blue.json:50` | `"gray74",` |
| `themes/blue.json:221` | `"gray74",` |
| `themes/blue.json:294` | `"gray74",` |
| `themes/davipa.json:50` | `"gray74",` |
| `themes/davipa.json:221` | `"gray74",` |
| `themes/davipa.json:294` | `"gray74",` |
| `themes/green.json:50` | `"gray74",` |
| `themes/green.json:221` | `"gray74",` |
| `themes/green.json:294` | `"gray74",` |
| `themes/grey.json:50` | `"gray74",` |
| `themes/grey.json:221` | `"gray74",` |
| `themes/grey.json:294` | `"gray74",` |
| `themes/orange.json:50` | `"gray74",` |
| `themes/orange.json:221` | `"gray74",` |
| `themes/orange.json:294` | `"gray74",` |
| `themes/pink.json:50` | `"gray74",` |
| `themes/pink.json:221` | `"gray74",` |
| `themes/pink.json:294` | `"gray74",` |
| `themes/purple.json:50` | `"gray74",` |
| `themes/purple.json:221` | `"gray74",` |
| `themes/purple.json:294` | `"gray74",` |

### `gray75`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:334` | `"gray75",` |
| `themes/base_dark_blue.json:135` | `"hover_color": ["gray75", "gray28"],` |
| `themes/black_white.json:334` | `"gray75",` |
| `themes/blue.json:334` | `"gray75",` |
| `themes/green.json:334` | `"gray75",` |
| `themes/grey.json:334` | `"gray75",` |
| `themes/orange.json:334` | `"gray75",` |
| `themes/pink.json:334` | `"gray75",` |
| `themes/purple.json:334` | `"gray75",` |

### `gray80`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:324` | `"gray80",` |
| `themes/base_dark_blue.json:131` | `"label_fg_color": ["gray80", "gray21"]` |
| `themes/black_white.json:324` | `"gray80",` |
| `themes/blue.json:324` | `"gray80",` |
| `themes/green.json:324` | `"gray80",` |
| `themes/grey.json:324` | `"gray80",` |
| `themes/orange.json:324` | `"gray80",` |
| `themes/pink.json:324` | `"gray80",` |
| `themes/purple.json:324` | `"gray80",` |

### `gray84`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:94` | `label_text = _theme_value("CTkLabel", "text_color", "gray84")` |
| `themes/apple_grey.json:103` | `"gray84"` |
| `themes/apple_grey.json:132` | `"gray84"` |
| `themes/apple_grey.json:157` | `"gray84"` |
| `themes/apple_grey.json:246` | `"gray84"` |
| `themes/apple_grey.json:311` | `"gray84"` |
| `themes/apple_grey.json:339` | `"gray84"` |
| `themes/base_dark_blue.json:27` | `"text_color": ["gray14", "gray84"]` |
| `themes/base_dark_blue.json:34` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:44` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:55` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:65` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:100` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:126` | `"text_color": ["gray14", "gray84"],` |
| `themes/base_dark_blue.json:136` | `"text_color": ["gray14", "gray84"]` |
| `themes/black_white.json:103` | `"gray84"` |
| `themes/black_white.json:132` | `"gray84"` |
| `themes/black_white.json:157` | `"gray84"` |
| `themes/black_white.json:246` | `"gray84"` |
| `themes/black_white.json:311` | `"gray84"` |
| `themes/black_white.json:339` | `"gray84"` |
| `themes/blue.json:59` | `"gray84"` |
| `themes/blue.json:75` | `"gray84"` |
| `themes/blue.json:103` | `"gray84"` |
| `themes/blue.json:132` | `"gray84"` |
| `themes/blue.json:157` | `"gray84"` |
| `themes/blue.json:246` | `"gray84"` |
| `themes/blue.json:311` | `"gray84"` |
| `themes/blue.json:339` | `"gray84"` |
| `themes/green.json:59` | `"gray84"` |
| `themes/green.json:75` | `"gray84"` |
| `themes/green.json:103` | `"gray84"` |
| `themes/green.json:132` | `"gray84"` |
| `themes/green.json:157` | `"gray84"` |
| `themes/green.json:246` | `"gray84"` |
| `themes/green.json:311` | `"gray84"` |
| `themes/green.json:339` | `"gray84"` |
| `themes/grey.json:59` | `"gray84"` |
| `themes/grey.json:75` | `"gray84"` |
| `themes/grey.json:103` | `"gray84"` |
| `themes/grey.json:132` | `"gray84"` |
| `themes/grey.json:157` | `"gray84"` |
| `themes/grey.json:246` | `"gray84"` |
| `themes/grey.json:311` | `"gray84"` |
| `themes/grey.json:339` | `"gray84"` |
| `themes/orange.json:59` | `"gray84"` |
| `themes/orange.json:75` | `"gray84"` |
| `themes/orange.json:103` | `"gray84"` |
| `themes/orange.json:132` | `"gray84"` |
| `themes/orange.json:157` | `"gray84"` |
| `themes/orange.json:246` | `"gray84"` |
| `themes/orange.json:311` | `"gray84"` |
| `themes/orange.json:339` | `"gray84"` |
| `themes/pink.json:59` | `"gray84"` |
| `themes/pink.json:75` | `"gray84"` |
| `themes/pink.json:103` | `"gray84"` |
| `themes/pink.json:132` | `"gray84"` |
| `themes/pink.json:157` | `"gray84"` |
| `themes/pink.json:246` | `"gray84"` |
| `themes/pink.json:311` | `"gray84"` |
| `themes/pink.json:339` | `"gray84"` |
| `themes/purple.json:59` | `"gray84"` |
| `themes/purple.json:75` | `"gray84"` |
| `themes/purple.json:103` | `"gray84"` |
| `themes/purple.json:132` | `"gray84"` |
| `themes/purple.json:157` | `"gray84"` |
| `themes/purple.json:246` | `"gray84"` |
| `themes/purple.json:311` | `"gray84"` |
| `themes/purple.json:339` | `"gray84"` |

### `gray85`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:12` | `"top_fg_color": ["gray85", "gray16"],` |
| `themes/blue.json:22` | `"gray85",` |
| `themes/green.json:22` | `"gray85",` |
| `themes/grey.json:22` | `"gray85",` |
| `themes/orange.json:22` | `"gray85",` |
| `themes/pink.json:22` | `"gray85",` |
| `themes/purple.json:22` | `"gray85",` |

### `gray90`

| File:Line | Snippet |
|---|---|
| `themes/apple_grey.json:99` | `"gray90"` |
| `themes/apple_grey.json:330` | `"gray90",` |
| `themes/base_dark_blue.json:11` | `"fg_color": ["gray90", "gray13"],` |
| `themes/base_dark_blue.json:43` | `"checkmark_color": ["#DCE4EE", "gray90"],` |
| `themes/base_dark_blue.json:134` | `"fg_color": ["gray90", "gray20"],` |
| `themes/black_white.json:99` | `"gray90"` |
| `themes/black_white.json:330` | `"gray90",` |
| `themes/blue.json:18` | `"gray90",` |
| `themes/blue.json:99` | `"gray90"` |
| `themes/blue.json:330` | `"gray90",` |
| `themes/green.json:18` | `"gray90",` |
| `themes/green.json:99` | `"gray90"` |
| `themes/green.json:330` | `"gray90",` |
| `themes/grey.json:18` | `"gray90",` |
| `themes/grey.json:99` | `"gray90"` |
| `themes/grey.json:330` | `"gray90",` |
| `themes/orange.json:18` | `"gray90",` |
| `themes/orange.json:99` | `"gray90"` |
| `themes/orange.json:330` | `"gray90",` |
| `themes/pink.json:18` | `"gray90",` |
| `themes/pink.json:99` | `"gray90"` |
| `themes/pink.json:330` | `"gray90",` |
| `themes/purple.json:18` | `"gray90",` |
| `themes/purple.json:99` | `"gray90"` |
| `themes/purple.json:330` | `"gray90",` |

### `gray95`

| File:Line | Snippet |
|---|---|
| `themes/base_dark_blue.json:3` | `"fg_color": ["gray95", "gray10"]` |
| `themes/base_dark_blue.json:6` | `"fg_color": ["gray95", "gray10"]` |
| `themes/blue.json:4` | `"gray95",` |
| `themes/blue.json:10` | `"gray95",` |
| `themes/green.json:4` | `"gray95",` |
| `themes/green.json:10` | `"gray95",` |
| `themes/grey.json:4` | `"gray95",` |
| `themes/grey.json:10` | `"gray95",` |
| `themes/orange.json:4` | `"gray95",` |
| `themes/orange.json:10` | `"gray95",` |
| `themes/pink.json:4` | `"gray95",` |
| `themes/pink.json:10` | `"gray95",` |
| `themes/purple.json:4` | `"gray95",` |
| `themes/purple.json:10` | `"gray95",` |

### `green`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:847` | `self._update_status_label("Working...", "green")` |
| `src/getmoredone/screens/timer_window.py:892` | `status_color = "green" if self.timer_state == self.RUNNING else "blue"` |
| `src/getmoredone/screens/timer_window.py:1059` | `self._update_status_label("Recording...", "green")` |
| `src/getmoredone/screens/timer_window.py:1097` | `self._update_status_label("Working...", "green")` |
| `src/getmoredone/screens/vision_planning.py:81` | `fg_color="green", width=120).pack(side="left", padx=5)` |
| `src/getmoredone/screens/vision_planning.py:376` | `ctrl, text="Save", width=70, fg_color="green",` |
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `src/getmoredone/theme.py:240` | `"green": palette["success_strong"],` |
| `tools/generate_ctk_themes.py:44` | `"green": ["#2CC985", "#2FA572"],` |

### `grey`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `tools/generate_ctk_themes.py:47` | `"grey": ["#475569", "#334155"],` |

### `orange`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:862` | `self._update_status_label("Paused", "orange")` |
| `src/getmoredone/screens/timer_window.py:1025` | `self._update_status_label("Resting — Resume starts another block", "orange")` |
| `src/getmoredone/theme.py:16` | `THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",` |
| `src/getmoredone/theme.py:245` | `"orange": palette["warning"],` |
| `tools/generate_ctk_themes.py:45` | `"orange": ["#C2410C", "#9A3412"],` |

### `red`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/color_contrast.py:51` | ```type and every browser accepts; a named colour such as ``"red"`` is not,``` |
| `src/getmoredone/screens/timer_window.py:919` | `self._update_status_label("Stopped", "red")` |
| `src/getmoredone/screens/timer_window.py:971` | `self._update_status_label("⏰ BREAK OVER! ⏰", "red")` |
| `src/getmoredone/screens/timer_window.py:1074` | `self._update_status_label("Not saved — try Done again", "red")` |
| `src/getmoredone/screens/vision_planning.py:315` | `fg_color="darkred", hover_color="red",` |
| `src/getmoredone/screens/vision_planning.py:577` | `fg_color="darkred", hover_color="red",` |
| `src/getmoredone/theme.py:243` | `"red": palette["danger"],` |

### `white`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:393` | `return "black" if luminance > 160 else "white"` |
| `src/getmoredone/screens/item_editor_weekly_tactic_dialog.py:396` | `return "white"` |
| `src/getmoredone/screens/vision_planning.py:285` | `text_color="white", width=130, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:294` | `text_color="white", width=130, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:303` | `text_color="white", width=130, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:547` | `text_color="white", width=120, height=28, corner_radius=6,` |
| `src/getmoredone/screens/vision_planning.py:566` | `text_color="white", width=120, height=28, corner_radius=6,` |
| `src/getmoredone/theme.py:120` | `"chip_text": "white",` |
| `src/getmoredone/theme.py:253` | `"white": palette["body_text"],` |

### `yellow`

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/timer_window.py:954` | `self._update_status_label("⏰ BREAK TIME! ⏰", "yellow")` |
| `src/getmoredone/theme.py:246` | `"yellow": palette["warning"],` |

### Theme API Occurrences

| File:Line | Snippet |
|---|---|
| `src/getmoredone/theme.py:57` | `ctk.set_appearance_mode(mode)` |
| `src/getmoredone/theme.py:65` | `ctk.set_default_color_theme(str(theme_path))` |

### Tuple / Appearance Tuple Occurrences

| File:Line | Snippet |
|---|---|
| `src/getmoredone/screens/item_editor.py:190` | `fg_color=("gray70", "gray30"))` |
| `src/getmoredone/screens/vps_segment_editor.py:35` | `self.selected_color = (` |

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
