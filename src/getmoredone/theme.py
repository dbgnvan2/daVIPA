"""Theme wiring and small semantic style helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import customtkinter as ctk

from .paths import resolve_theme_path

APPEARANCE_MODES = ("system", "dark", "light")
# "davipa" is the brand theme, built from brand.py and the colour system
# document. The rest predate it and are untouched.
THEME_NAMES = ("davipa", "green", "orange", "pink", "grey", "blue", "purple",
               "apple_grey", "black_white")
DEFAULT_THEME_NAME = "apple_grey"
LIST_ROW_FONT_SIZE = 14


def normalize_appearance_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in APPEARANCE_MODES else "dark"


def normalize_theme_name(value: str) -> str:
    """Coerce any persisted value to a known theme name.

    ``str()`` first: settings.json is user-writable, so the stored value may be a
    number, null, or anything else a hand-edit left behind.
    """
    name = str(value or "").strip().lower()
    return name if name in THEME_NAMES else DEFAULT_THEME_NAME


def theme_path_for(theme_name: str) -> Path:
    return resolve_theme_path(normalize_theme_name(theme_name))


def apply_theme_settings(settings) -> Tuple[str, str]:
    """Apply appearance mode + color theme from settings.

    Purpose: set the CustomTkinter theme at startup without ever raising.
    Spec:    docs/spec_2026-08-18_downloadable_release.md#r-m1a2
    Tests:   tests/test_packaging_resources.py::test_rm1a2_apply_theme_settings_never_raises_on_bad_name
    """
    global LIST_ROW_FONT_SIZE
    mode = normalize_appearance_mode(getattr(settings, "appearance_mode", "dark"))
    theme_name = normalize_theme_name(getattr(settings, "theme_name", "apple_grey"))
    font_size = getattr(settings, "list_row_font_size", LIST_ROW_FONT_SIZE)
    try:
        LIST_ROW_FONT_SIZE = max(10, min(24, int(font_size)))
    except (TypeError, ValueError):
        LIST_ROW_FONT_SIZE = 14

    ctk.set_appearance_mode(mode)

    # A missing or unreadable theme file must not stop the app from starting —
    # this runs before the first window exists, so an exception here is a launch
    # crash with no UI to report it. Degrade to CustomTkinter's built-in default.
    theme_path = theme_path_for(theme_name)
    if theme_path.exists():
        try:
            ctk.set_default_color_theme(str(theme_path))
        except (OSError, ValueError, KeyError) as exc:
            print(f"[WARN] Could not load theme {theme_path}: {exc}. Using the built-in default.")
    else:
        print(f"[WARN] Theme file not found: {theme_path}. Using the built-in default.")

    return mode, theme_name


def _mode_index() -> int:
    return 0 if (ctk.get_appearance_mode() or "Dark").lower() == "light" else 1


def _theme_value(widget: str, key: str, fallback: str) -> str:
    theme = getattr(ctk.ThemeManager, "theme", {}) or {}
    value = theme.get(widget, {}).get(key, fallback)
    if isinstance(value, (list, tuple)):
        idx = _mode_index()
        if len(value) > idx:
            return value[idx]
        return value[0] if value else fallback
    return value


def semantic_colors() -> Dict[str, str]:
    mode = (ctk.get_appearance_mode() or "Dark").lower()
    primary = _theme_value("CTkButton", "fg_color", "#1f538d")
    primary_hover = _theme_value("CTkButton", "hover_color", "#14375e")
    muted_text = _theme_value("CTkEntry", "placeholder_text_color", "gray62")
    label_text = _theme_value("CTkLabel", "text_color", "gray84")
    input_surface = _theme_value("CTkComboBox", "fg_color", _theme_value("CTkEntry", "fg_color", "gray20"))
    input_button = _theme_value("CTkComboBox", "button_color", primary)
    input_button_hover = _theme_value("CTkComboBox", "button_hover_color", primary_hover)
    input_text = _theme_value("CTkComboBox", "text_color", label_text)
    dropdown_surface = _theme_value("DropdownMenu", "fg_color", input_surface)
    dropdown_text = _theme_value("DropdownMenu", "text_color", label_text)
    return {
        "primary": primary,
        "primary_hover": primary_hover,
        "surface": _theme_value("CTkFrame", "fg_color", "gray17"),
        "ghost_hover": _theme_value("DropdownMenu", "hover_color", "gray28"),
        "border": _theme_value("CTkFrame", "border_color", "gray28"),
        "muted_text": muted_text,
        "body_text": label_text,
        "row_text": label_text,
        "on_primary": _theme_value("CTkButton", "text_color", "#DCE4EE"),
        "input_surface": input_surface,
        "input_button": input_button,
        "input_button_hover": input_button_hover,
        "input_text": input_text,
        "dropdown_surface": dropdown_surface,
        "dropdown_text": dropdown_text,
        "surface_subtle": _theme_value("CTkFrame", "top_fg_color", "gray21"),
        # Align list accents with Drag Schedule visual language.
        "chip_bg": "gray30",
        "chip_text": "white",
        "date_start_text": "#FFB347",
        "date_due_text": "#FF5A8A",
        # The clock label on a Plan box. It was a fixed peach, which is
        # the dark theme's colour in both themes: on the light one it is
        # pale text on a pale box and the hour is barely readable. The
        # label is the only thing that says which half hour a box is, so
        # it follows the body text and is legible in either mode.
        "time_text": label_text,
        "success_tint": "#E8F5EE" if mode == "light" else "#1F2B24",
        "critical_tint": "#FDECEC" if mode == "light" else "#3A2328",
        "danger": "#B91C1C",
        "danger_hover": "#991B1B",
        "on_danger": "#FEE2E2",
        "warning": "#B45309" if mode == "light" else "#FBBF24",
        "selected_tint": "#E6EEF8" if mode == "light" else "#223247",
        "success_strong": "#166534" if mode == "light" else "#14532D",
        "on_strong": "#ECFDF5" if mode == "light" else "#DCFCE7",
        # PD-M9 -- the two marks in the Plan items pane: a green check for an
        # item the day already holds a block for, a red question mark for one
        # it does not.
        #
        # Their own tokens rather than `success_strong`/`danger`, because they
        # are drawn on a priority *fill* and not on a surface. In the light
        # theme the fills are pale tints, so the marks are the same dark green
        # and red those two tokens carry there. In the dark theme the fills are
        # deep -- the `low` fill is #052E16 -- and `success_strong`'s dark
        # green measures 1.63:1 against it, a mark nobody can see, so the dark
        # theme takes the light pair instead. Measured by
        # ``tests/test_time_block_colors.py::test_pdm9_the_two_marks_are_legible_on_every_fill``.
        "scheduled_mark": "#166534" if mode == "light" else "#4ADE80",
        "unscheduled_mark": "#B91C1C" if mode == "light" else "#FCA5A5",
    }


def apply_segment_accent(frame: ctk.CTkFrame, segment_color: str | None):
    """Apply a narrow accent stripe; segment colors should not fill full rows."""
    if not segment_color:
        return
    accent = ctk.CTkFrame(frame, width=5, fg_color=segment_color, corner_radius=0)
    accent.place(x=0, y=0, relheight=1)


def button_style(kind: str = "primary") -> Dict[str, object]:
    """Shared semantic button styles used across screens."""
    palette = semantic_colors()
    if kind == "ghost":
        return {
            "fg_color": "transparent",
            "hover_color": palette["ghost_hover"],
            "border_width": 0,
            "text_color": palette["body_text"],
        }
    if kind == "secondary":
        return {
            "fg_color": "transparent",
            "hover_color": palette["ghost_hover"],
            "border_width": 1,
            "border_color": palette["border"],
            "text_color": palette["body_text"],
        }
    if kind == "danger":
        return {
            "fg_color": palette["danger"],
            "hover_color": palette["danger_hover"],
            "text_color": palette["on_danger"],
            "border_width": 0,
        }
    return {
        "fg_color": palette["primary"],
        "hover_color": palette["primary_hover"],
        "text_color": palette["on_primary"],
        "border_width": 0,
    }


def list_row_font() -> ctk.CTkFont:
    """Standard larger font for item-list rows."""
    return ctk.CTkFont(size=LIST_ROW_FONT_SIZE)


def combo_box_style() -> Dict[str, object]:
    """Theme-aware combobox styling for filters and settings controls."""
    palette = semantic_colors()
    return {
        "fg_color": palette["input_surface"],
        "text_color": palette["input_text"],
        "button_color": palette["input_button"],
        "button_hover_color": palette["input_button_hover"],
        "dropdown_fg_color": palette["dropdown_surface"],
        "dropdown_text_color": palette["dropdown_text"],
    }


def status_text_color(kind: str) -> str:
    """Return semantic text colors for status messages.

    Accepts semantic names and legacy color words to ease incremental cleanup.
    """
    palette = semantic_colors()
    normalized = (kind or "").strip().lower()
    mapping = {
        "success": palette["success_strong"],
        "green": palette["success_strong"],
        "error": palette["danger"],
        "danger": palette["danger"],
        "red": palette["danger"],
        "warning": palette["warning"],
        "orange": palette["warning"],
        "yellow": palette["warning"],
        "info": palette["primary"],
        "blue": palette["primary"],
        "muted": palette["muted_text"],
        "gray": palette["muted_text"],
        "body": palette["body_text"],
        "default": palette["body_text"],
        "white": palette["body_text"],
    }
    return mapping.get(normalized, kind or palette["body_text"])


def schedule_colors() -> Dict[str, object]:
    """Shared Drag Schedule palette values."""
    return {
        "date_overdue": "#FCA5A5",
        "date_today": "#86EFAC",
        "date_future": "#FDE68A",
        "future_near_term": "#F4D35E",
        "future_long_term": "#E9C6CF",
        "future_next_month": "#EFE6A7",
        "future_next_quarter": "#E9CAA0",
        "low_load": "#6BCB77",
        "load_gradient": ["#FFD8A8", "#FFB347", "#F5A6BE", "#EF7292", "#D94B66"],
        "load_fallback": "#DFF8D8",
    }


def priority_band_colors() -> Dict[str, str]:
    """TB-M12 — one accent colour per priority band, light and dark.

    Purpose: colour a block by the priority of the item behind it.
    Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m12
    Tests:   tests/test_time_block_colors.py::test_tbm122_band_colors_meet_contrast_in_both_themes

    The band a score falls in is decided by ``time_block_layout.priority_band``,
    not here: a theme change must not be able to move an item into a different
    band. This function only says what each band looks like.

    Centralised for the same reason the rest of this module is -- the project
    rule is no hard-coded colours in widgets, and a one-off hex in plan.py
    would be a second place a band's colour could be changed from.

    "unscored" is a deliberate fifth value, not a fallback: an item missing one
    of its four priority factors scores 0, and that is absence of information.
    Painting it the same grey-green as a genuinely low-priority item would show
    the user data they never entered.
    """
    mode = (ctk.get_appearance_mode() or "Dark").lower()
    if mode == "light":
        # Darker than the obvious 600-weight tints: those land at 4.2-4.3
        # against the light theme's block surface (CTkFrame top_fg_color,
        # gray81), which clears the 3:1 WCAG bar for a non-text accent but
        # leaves nothing spare if a band colour is ever put behind text. These
        # clear 4.5:1 -- measured against that surface, not the lighter page
        # background, because the stripe is drawn on the block.
        return {
            "critical": "#991B1B",
            "high": "#9A3412",
            "medium": "#92400E",
            "low": "#166534",
            "unscored": "#52525B",
        }
    return {
        "critical": "#F87171",
        "high": "#FB923C",
        "medium": "#FBBF24",
        "low": "#4ADE80",
        "unscored": "#94A3B8",
    }


def priority_stripe_colors() -> Dict[str, str]:
    """PB-M1 — the band accent as a stripe, brighter than the text-safe set.

    Purpose: a visible priority bar, without weakening the colours that have
             to sit behind a label.
    Spec:    docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m1
    Tests:   tests/test_time_block_colors.py::test_pbm12_stripe_colors_meet_the_non_text_contrast_bar

    A second table rather than an edit of ``priority_band_colors`` because the
    two are held to different bars and cannot both be satisfied by one value.
    A stripe is not text, so WCAG asks 3:1 of it; a band colour behind a label
    is text, and asks 4.5:1. On a pale light-theme surface, brighter means less
    contrast, so the light set below sits as high up each ramp as 3:1 allows
    and the text-safe set stays where 4.5:1 put it.

    The dark values are identical to ``priority_band_colors``: that set already
    clears 4.5:1 against the dark surface with room to spare, so there is
    nothing to trade and no second value worth inventing.
    """
    mode = (ctk.get_appearance_mode() or "Dark").lower()
    if mode == "light":
        return {
            "critical": "#DC2626",
            "high": "#C2410C",
            "medium": "#B45309",
            "low": "#15803D",
            "unscored": "#71717A",
        }
    return dict(priority_band_colors())


def priority_fill_colors() -> Dict[str, str]:
    """PB-M4 — the shade a task is drawn on, by the priority behind it.

    Purpose: carry priority as the shading of the task itself, not only as a
             6px bar at its edge.
    Spec:    docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m4
    Tests:   tests/test_plan_screen.py::test_pbm41_a_chips_title_is_coloured_for_the_shade_behind_it

    A tint and not the accent. The project rule allows a colour as a chip or
    stripe accent and not as a full-row fill, and the reason it gives -- a wall
    of saturated rows stops carrying information and fights the text on top of
    it -- applies whatever the colour's source. These are chosen so
    ``pick_text_color`` clears 4.5:1 on them and so the band's own stripe still
    clears 3:1 when drawn on them rather than on the bare surface.
    """
    mode = (ctk.get_appearance_mode() or "Dark").lower()
    if mode == "light":
        return {
            "critical": "#FEE2E2",
            "high": "#FFEDD5",
            "medium": "#FEF3C7",
            "low": "#DCFCE7",
            "unscored": "#F4F4F5",
        }
    return {
        "critical": "#450A0A",
        "high": "#431407",
        "medium": "#451A03",
        "low": "#052E16",
        "unscored": "#27272A",
    }


def priority_level_fill_colors() -> Dict[str, str]:
    """PLC-M2 — the default row tint for each of the three priority *levels*.

    Purpose: the one place the shipped level colours are written down.
    Spec:    docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m2
    Tests:   tests/test_priority_level_colors.py::test_plcm22_settings_defaults_match_the_theme_table

    A *level* is a rule on importance and urgency, not a band on
    ``priority_score`` — see ``priority_levels`` for why the two are kept
    apart. These are only the defaults: the user sets their own in
    Settings → Priority Colours, and ``priority_levels.level_color`` prefers
    theirs. The empty string is "no fill", which is what rows with no high or
    critical factor have always had.

    **One value per level, not one per theme**, unlike every other table in
    this module. A colour the user picks in a colour chooser cannot have a
    light and a dark variant, and a setting that silently did something
    different in the two appearance modes would be worse than one that does
    the same thing in both. The consequence — a pale fill needs dark text, in
    either mode — is handled where the fill is applied:
    ``priority_levels.row_fill`` derives the row's text colour from the fill
    with ``pick_text_color`` rather than leaving the theme's ``row_text`` on
    it. Both defaults below are held to 4.5:1 against that picked text in both
    modes by
    ``tests/test_priority_level_colors.py::test_plcm46_default_level_colours_are_legible_in_both_themes``.

    Green for Any Critical is the user's choice, asked for directly and
    confirmed before this was built. It is not the conventional red, and it is
    deliberately not ``critical_tint``, the pale red these rows used to take.
    """
    from .priority_levels import (
        LEVEL_ANY_CRITICAL,
        LEVEL_ANY_HIGH,
        LEVEL_NO_HIGH_OR_CRITICAL,
    )

    return {
        LEVEL_ANY_CRITICAL: "#DCFCE7",
        LEVEL_ANY_HIGH: "#FEF3C7",
        LEVEL_NO_HIGH_OR_CRITICAL: "",
    }


def block_type_colors() -> Dict[str, str]:
    """TB-M10/TB-M12 — the accent for a block that has no priority behind it.

    Buffer and break blocks carry no item, so they are not priority-coloured.
    A neutral accent says "this is padding" rather than implying an importance
    the block does not have.

    PD-M4: one neutral for all three. A break had the theme's cyan, which is
    the brightest thing on a planned day and read as a kind of work rather
    than a gap in it. The three are told apart by their words -- "Break",
    "Buffer", "Lunch" -- which is what they were already doing for buffer and
    lunch, who have shared this value from the start.
    Tests: tests/test_time_block_colors.py::test_pdm41_padding_and_lunch_share_one_colour
    """
    mode = (ctk.get_appearance_mode() or "Dark").lower()
    padding = "#4B5563" if mode == "light" else "#9CA3AF"
    return {"buffer": padding, "break": padding, "lunch": padding}


def depth_bar_colors() -> Dict[str, str]:
    """TB-M12 — the filled and empty states of the three-bar depth stack."""
    palette = semantic_colors()
    return {"filled": palette["body_text"], "empty": palette["border"]}


def vps_level_colors() -> Dict[str, str]:
    """Shared planning-hierarchy legend colors."""
    return {
        "TL Vision": "#7C3AED",
        "Annual Vision": "#2563EB",
        "Annual Plan": "#0D9488",
        "Annual Initiative": "#F59E0B",
        "Quarter": "#EA580C",
        "Month": "#059669",
        "Week": "#0284C7",
    }


def celebration_colors() -> Tuple[str, ...]:
    """Shared celebratory accent colors."""
    return ("#00C800", "#FFD54F", "#3B82F6", "#EF4444", "#A855F7", "#F97316")
