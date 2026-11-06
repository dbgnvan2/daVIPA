"""TB-M12.2/12.3 — the planner's colours are legible, and they live in one place.

Purpose: hold every band and block-type accent to a contrast minimum in both
         themes, and keep the Plan screen's modules free of inline hex.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m12
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

from src.getmoredone.color_contrast import (
    contrast_ratio,
    pick_text_color,
    relative_luminance,
)
from src.getmoredone.theme import (
    block_type_colors,
    depth_bar_colors,
    priority_band_colors,
    priority_fill_colors,
    priority_stripe_colors,
    semantic_colors,
)
from src.getmoredone.time_block_layout import PRIORITY_BANDS, UNSCORED_BAND

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


def test_tbm122_band_colors_meet_contrast_in_both_themes(restore_appearance):
    """TB-M12.2 — every priority band is legible against the block surface.

    Collected and reported together rather than asserted one at a time: a
    single failing band tells you the table needs work, and the whole list
    tells you how much.
    """
    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        surface = _block_surface()
        for band, color in priority_band_colors().items():
            ratio = contrast_ratio(surface, _as_hex(color))
            if ratio < MIN_CONTRAST:
                failures.append(f"{mode}/{band}={color}: {ratio:.2f} on {surface}")

    assert not failures, "bands below the contrast minimum: " + "; ".join(failures)


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
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m4

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


def test_every_band_name_has_exactly_one_colour(restore_appearance):
    """The band names and the colour table are kept in step, both themes.

    An exact set, not "every name has an entry": a colour for a band no score
    can reach is dead, and a band with no colour is a KeyError the first time
    a user scores an item into it.
    """
    expected = {name for _threshold, name in PRIORITY_BANDS} | {UNSCORED_BAND}

    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        assert set(priority_band_colors()) == expected


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


def test_theme_is_the_only_module_that_defines_the_band_table():
    """Nothing but theme.py may define ``priority_band_colors``.

    The companion to the test above: that one proves the screens hold no hex,
    this one proves no other module grew a second band table to hold it in.
    """
    offenders = [
        str(path)
        for path in Path("src/getmoredone").rglob("*.py")
        if path.name != "theme.py" and "def priority_band_colors" in path.read_text()
    ]

    assert offenders == [], f"a second band colour table exists in {offenders}"


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


def test_pbm11_stripe_colors_cover_every_band(restore_appearance):
    """PB-M1.1 — the stripe table answers for every band, in both themes.

    A band missing from this table is a KeyError the moment an item of that
    priority is drawn, which is every band's turn eventually.
    """
    expected = {name for _threshold, name in PRIORITY_BANDS} | {UNSCORED_BAND}
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        assert set(priority_stripe_colors()) == expected, (
            f"{mode}: stripe table is {sorted(priority_stripe_colors())}"
        )
        assert set(priority_fill_colors()) == expected, (
            f"{mode}: fill table is {sorted(priority_fill_colors())}"
        )


def test_pbm12_stripe_colors_meet_the_non_text_contrast_bar(restore_appearance):
    """PB-M1.2 — every stripe is visible against the surface it is drawn on.

    3:1 and not 4.5:1: a stripe carries no text, and holding it to the text bar
    is what forced the light-theme bands dark enough to be asked about.
    """
    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        surface = _block_surface()
        for band, color in priority_stripe_colors().items():
            ratio = contrast_ratio(surface, _as_hex(color))
            if ratio < MIN_NON_TEXT_CONTRAST:
                failures.append(f"{mode}/{band}={color}: {ratio:.2f} on {surface}")

    assert not failures, "stripes below the non-text minimum: " + "; ".join(failures)


def test_pbm13_stripe_colors_are_brighter_than_the_text_safe_set(restore_appearance):
    """PB-M1.3 — "brighter" as relative luminance, not as an opinion.

    Light theme only. The dark set is already near the top of each ramp with
    4.5:1 to spare, so there is nothing to trade there and the two tables are
    deliberately the same values -- asserting a strict increase in dark mode
    would be asserting a difference that should not exist.
    """
    ctk.set_appearance_mode("Light")
    safe = priority_band_colors()
    dimmer = [
        f"{band}: stripe {stripe} is not brighter than band {safe[band]}"
        for band, stripe in priority_stripe_colors().items()
        if _luminance_of(stripe) <= _luminance_of(safe[band])
    ]

    assert dimmer == [], "; ".join(dimmer)


def test_pbm13_the_dark_stripe_table_is_the_band_table(restore_appearance):
    """The other half of PB-M1.3, stated rather than left to be inferred.

    Without this, the two dark tables could drift apart and nothing would
    notice: no contrast test can tell a deliberate match from an accident.
    """
    ctk.set_appearance_mode("Dark")
    assert priority_stripe_colors() == priority_band_colors()


def test_pbm41_pick_text_color_is_not_what_makes_a_fill_legible(restore_appearance):
    """PB-M4.1 — the fill's own luminance, not the chooser's, carries the text.

    The obvious form of this criterion -- loop the fills, call
    ``pick_text_color``, assert 4.5:1 -- **cannot fail**. The chooser returns
    black or white, and for every luminance L at least one of the two clears
    4.5: black falls below it only when L < 0.175, where white is already
    above 4.67. It was written that way and passed against a mid grey planted
    to break it. What can fail is the fill being near that crossover at all,
    where the better of the two choices is only just legible and a theme tweak
    in either direction makes it worse. Each fill must clear the bar with the
    margin a tint should have.
    """
    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        for band, fill in priority_fill_colors().items():
            chosen = pick_text_color(_as_hex(fill))
            ratio = contrast_ratio(_as_hex(fill), chosen)
            if ratio < MIN_TINT_CONTRAST:
                failures.append(f"{mode}/{band}={fill} + {chosen}: {ratio:.2f}")

    assert not failures, (
        f"fills closer than {MIN_TINT_CONTRAST}:1 to their own text: "
        + "; ".join(failures)
    )


def test_pbm42_a_stripe_is_visible_on_its_own_fill(restore_appearance):
    """PB-M4.2 — the bar still reads once the task behind it is shaded.

    The stripe used to sit on ``surface_subtle``. It now sits on its own band's
    tint, which is a different and in the light theme a *lighter* background,
    so the ratio that was measured is not the ratio the user sees.
    """
    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        fills = priority_fill_colors()
        for band, stripe in priority_stripe_colors().items():
            ratio = contrast_ratio(_as_hex(fills[band]), _as_hex(stripe))
            if ratio < MIN_NON_TEXT_CONTRAST:
                failures.append(
                    f"{mode}/{band}: {stripe} on {fills[band]} is {ratio:.2f}"
                )

    assert not failures, "stripes lost against their own fill: " + "; ".join(failures)
