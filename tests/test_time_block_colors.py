"""TB-M12.2/12.3 — the planner's colours are legible, and they live in one place.

Purpose: hold every band and block-type accent to a contrast minimum in both
         themes, and keep the Plan screen's modules free of inline hex.
Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m12
Tests:   this file

The theme rule this enforces is not a style preference: a colour written inline
in a screen is a second place it can be changed from, and the two then drift.
The check is run over the AST rather than by grep, because a grep for "#" finds
every comment in the file.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import customtkinter as ctk
import pytest

from src.getmoredone.color_contrast import contrast_ratio, relative_luminance
from src.getmoredone.theme import (
    block_type_colors,
    depth_bar_colors,
    semantic_colors,
)

# WCAG AA for normal text. These accents are stripes rather than text, where
# the standard asks only 3:1 -- held to the stricter bar anyway, so there is
# headroom if a band colour is ever put behind a label.
MIN_CONTRAST = 4.5

THEMES = ("Dark", "Light")

SCREEN_FILES = (
    Path("src/getmoredone/screens/plan.py"),
    Path("src/getmoredone/screens/plan_blocks.py"),
    Path("src/getmoredone/screens/plan_settings_dialog.py"),
)

HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

GRAY_NAME = re.compile(r"^gray(\d{1,3})$", re.IGNORECASE)


def _as_hex(color: str) -> str:
    """A theme colour as hex, resolving the ``grayNN`` names Tk understands.

    ``grayNN`` is NN percent of white, so gray20 is 0x33 -- checked against
    ``winfo_rgb`` for every value the themes actually use before this was
    written. Done arithmetically rather than through Tk so these tests need no
    display, the same reason the layout arithmetic lives outside the screen.
    """
    text = (color or "").strip()
    match = GRAY_NAME.match(text)
    if match:
        value = round(int(match.group(1)) * 255 / 100)
        return "#{0:02X}{0:02X}{0:02X}".format(value)
    return text


def _block_surface() -> str:
    """The frame colour a block's stripe is drawn on, in the current theme.

    ``surface_subtle`` and not ``surface``: the stripe sits on the block, and
    measuring against the lighter page background behind it reports a ratio no
    user ever sees. That distinction is what caught the light-theme critical
    red at 4.15.
    """
    return _as_hex(semantic_colors()["surface_subtle"])


@pytest.fixture
def restore_appearance():
    """Put the appearance mode back, whatever the test did to it.

    A module-level setting left switched leaks into every later test in the
    run, which is the class of failure the project's restore rule exists for.
    """
    was_system = ctk.AppearanceModeTracker.appearance_mode_set_by == "system"
    original = ctk.get_appearance_mode()
    try:
        yield
    finally:
        # "system" and not ``original``: ``get_appearance_mode`` returns the
        # resolved mode, so restoring that would turn "follow the OS" into a
        # fixed mode for every test collected after this file.
        ctk.set_appearance_mode("system" if was_system else original)




def test_block_type_colors_meet_contrast_in_both_themes(restore_appearance):
    """Buffer, break and lunch accents, held to the same bar as the bands."""
    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        surface = _block_surface()
        for kind, color in block_type_colors().items():
            ratio = contrast_ratio(surface, _as_hex(color))
            if ratio < MIN_CONTRAST:
                failures.append(f"{mode}/{kind}={color}: {ratio:.2f} on {surface}")

    assert not failures, "block types below the minimum: " + "; ".join(failures)


def test_pdm41_padding_and_lunch_share_one_colour(restore_appearance):
    """PD-M4.1 — break, buffer and lunch are one neutral, in both themes.

    Purpose: PD-M4 -- three kinds of time that are not work, told apart by
             their words rather than by three colours.
    Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m4

    Buffer and lunch already shared the neutral; a break was the theme's cyan,
    which read as a kind of work rather than a gap in it. An exact count of
    distinct values, not a floor: a floor of "at most three" is satisfied by
    the state this test exists to end.
    """
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        colors = block_type_colors()
        assert set(colors) == {"buffer", "break", "lunch"}, (
            f"{mode}: the padding table is {sorted(colors)}"
        )
        distinct = set(colors.values())
        assert len(distinct) == 1, (
            f"{mode}: three kinds of padding in {len(distinct)} colours: {colors}"
        )


def test_a_filled_depth_bar_is_distinguishable_from_an_empty_one(restore_appearance):
    """The three-bar stack carries information only if the two states differ.

    Measured against each other rather than against the surface: a filled bar
    that matched the empty one would render every depth as three identical
    lines, which is worse than showing no depth at all.
    """
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        colors = depth_bar_colors()
        ratio = contrast_ratio(_as_hex(colors["empty"]), _as_hex(colors["filled"]))
        assert ratio >= 3.0, (
            f"{mode}: a filled depth bar is {ratio:.2f} against an empty one"
        )




def test_tbm123_no_inline_hex_in_plan_screen():
    """TB-M12.3 — no hard-coded colour in the Plan screen's three modules.

    Asserted as an exact empty list, never a "fewer than N" floor: a floor
    hides the narrowing it was written to catch.
    """
    offenders = []
    for path in SCREEN_FILES:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if HEX_COLOR.match(node.value.strip()):
                    offenders.append(f"{path}:{node.lineno} {node.value!r}")

    assert offenders == [], (
        "colours belong in theme.py, not in a screen: " + "; ".join(offenders)
    )




# --- PB-M1 / PB-M4 : the stripe table and the fill table -------------------
#
# Two tables rather than one because they are held to different bars. A stripe
# is not text, so WCAG asks 3:1 of it; a band colour behind a label is text and
# asks 4.5:1. On a pale light-theme surface brighter means *less* contrast, so
# one value cannot be both the brightest bar and the safest label colour.

#: WCAG AA for a non-text graphical object. What a stripe actually has to meet.
MIN_NON_TEXT_CONTRAST = 3.0

#: What a fill tint has to clear against the text drawn on it. Well above the
#: 4.5 AA bar on purpose -- see ``test_pbm41_...`` for why 4.5 is unfailable
#: here. A tint is a pale or a deep background, not a mid grey, and 10:1 is
#: comfortably met by every value in the table while excluding the crossover
#: band where neither black nor white is a good answer.
MIN_TINT_CONTRAST = 10.0


def _luminance_of(color: str) -> float:
    """WCAG relative luminance, so "brighter" is a number and not a taste.

    Thin wrapper on ``color_contrast.relative_luminance`` -- the app's own
    function -- because the value arriving here may be a CustomTkinter
    (light, dark) tuple that has to be resolved first.

    This was a second copy of the formula, justified by a docstring saying
    ``color_contrast`` exposed only the ratio. It exposes
    ``relative_luminance`` publicly, and the copy had drifted already: it
    linearised at 0.03928 where the source uses the 0.04045 of the current
    WCAG text. Close enough never to change a verdict, which is what makes a
    duplicate formula worth deleting rather than correcting -- in the same
    file that asserts theme.py is the only module defining the band table.
    """
    return relative_luminance(_as_hex(color))












def test_pdm9_the_two_marks_are_legible_on_the_row_surface(restore_appearance):
    """PD-M9 — the green check and the red question mark are still glyphs.

    They sat on a priority fill until PBG-M3 and are measured against the
    theme's own row surface now, which is the only thing behind them. Held to
    the 4.5:1 text bar, not the 3:1 non-text one -- they are glyphs, and the
    whole of what each one says is which glyph it is.
    """
    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        palette = semantic_colors()
        surface = _as_hex(palette["surface_subtle"])
        marks = {
            "scheduled": palette["scheduled_mark"],
            "unscheduled": palette["unscheduled_mark"],
        }
        assert marks["scheduled"] != marks["unscheduled"], (
            f"{mode}: the two marks are the same colour, so only the glyph "
            "tells them apart"
        )
        for role, mark in marks.items():
            ratio = contrast_ratio(_as_hex(mark), surface)
            if ratio < MIN_CONTRAST:
                failures.append(
                    f"{mode}: {role} {mark} on {surface} is {ratio:.2f}"
                )

    assert not failures, (
        f"marks closer than {MIN_CONTRAST}:1 to the surface behind them: "
        + "; ".join(failures)
    )


