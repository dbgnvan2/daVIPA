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

from src.getmoredone.color_contrast import contrast_ratio
from src.getmoredone.theme import (
    block_type_colors,
    depth_bar_colors,
    priority_band_colors,
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
    original = ctk.get_appearance_mode()
    yield
    ctk.set_appearance_mode(original)


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
