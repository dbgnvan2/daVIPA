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
import json

import pytest

from src.getmoredone.color_contrast import contrast_ratio
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


# ``MIN_NON_TEXT_CONTRAST``, ``MIN_TINT_CONTRAST`` and ``_luminance_of`` were
# here, with the 3:1 stripe bar and the 10:1 tint bar they measured. PBG-M5
# deleted the stripe table and the fill table, so the five tests that used them
# went too, and these are deleted rather than left: a constant naming a bar
# nothing enforces reads as a bar something enforces.


def test_pdm9_the_two_marks_are_legible_on_the_row_surface(restore_appearance):
    """PD-M9 — the green check and the red question mark are still glyphs.

    They sat on a priority fill until PBG-M3 and are measured against the
    theme's own row surface now, which is the only thing behind them. Held to
    the 4.5:1 text bar, not the 3:1 non-text one -- they are glyphs, and the
    whole of what each one says is which glyph it is.

    Against **every bundled theme's** surface, not just the one this process
    happens to have loaded. The pair this replaced measured against hard-coded
    priority fills and so was theme-independent for free; ``surface_subtle``
    is ``CTkFrame.top_fg_color``, which each theme file sets for itself --
    ``gray85``/``gray16`` in seven, and its own pair in ``apple_grey``,
    ``black_white`` and ``davipa`` (SEP-M1 gave the first two theirs; they
    repeated ``CTkFrame.fg_color`` before) -- so a single-theme measurement
    would let a theme ship a sub-4.5:1 glyph
    with the suite green. Read out of the JSON rather than by loading each
    theme, which would leave global CustomTkinter state behind it.
    """
    themes = sorted(Path("themes").glob("*.json"))
    assert len(themes) == 10, (
        f"{len(themes)} theme files found, not the 10 this app ships -- a "
        "floor here would hide a theme that stopped being measured"
    )

    failures = []
    for mode in THEMES:
        ctk.set_appearance_mode(mode)
        palette = semantic_colors()
        marks = {
            "scheduled": palette["scheduled_mark"],
            "unscheduled": palette["unscheduled_mark"],
        }
        assert marks["scheduled"] != marks["unscheduled"], (
            f"{mode}: the two marks are the same colour, so only the glyph "
            "tells them apart"
        )
        # A theme file's colour pair is [light, dark]; ``THEMES`` is the
        # appearance-mode name, so the half is picked by name and not by the
        # order this loop happens to run in.
        half = 0 if mode == "Light" else 1
        surfaces = {"the loaded theme": _as_hex(palette["surface_subtle"])}
        for path in themes:
            pair = json.loads(path.read_text())["CTkFrame"]["top_fg_color"]
            surfaces[path.name] = _as_hex(pair[half])

        for where, surface in surfaces.items():
            for role, mark in marks.items():
                ratio = contrast_ratio(_as_hex(mark), surface)
                if ratio < MIN_CONTRAST:
                    failures.append(
                        f"{mode}/{where}: {role} {mark} on {surface} is "
                        f"{ratio:.2f}"
                    )

    assert not failures, (
        f"marks closer than {MIN_CONTRAST}:1 to the surface behind them: "
        + "; ".join(failures)
    )


def test_sepm2_no_bundled_theme_has_one_surface_where_the_app_wants_two():
    """SEP-M2 — every bundled theme separates its two surface tokens.

    The app separates a row from its pane, and a Plan chip from its box, with
    one pair of tokens: ``surface`` is ``CTkFrame.fg_color`` and
    ``surface_subtle`` is ``CTkFrame.top_fg_color``. ``apple_grey`` and
    ``black_white`` gave them the same value in both modes -- ``#FFFFFF``
    /``#1D1D1F`` and ``#FFFFFF``/``#000000`` -- so on those two there was no
    edge to be had whichever token the code picked. That was app-wide and
    older than the Plan screen's badge: every list row in the app was the
    colour of its pane there. PBG-M3 only made the Plan screen join them, by
    taking away the priority tint that had been separating its rows.

    SEP-M1 gave each of those two a subtle surface off its own ramp, in
    ``tools/generate_ctk_themes.py`` where the themes are generated rather
    than in the JSON it writes. So this asserts the empty set instead of
    counting the known-flat two: there is no shipped-colour decision
    outstanding any more, and a theme that flattens from here is a
    regression whichever one it is.

    SEP-M7 -- three things an empty-set assertion has to do that counting the
    known-flat two did not. It must count the themes, because ``== set()`` over
    a glob also passes when the glob finds nothing. It must compare per mode,
    because a theme flat in one mode is flat where that user is. And it must
    resolve through ``_as_hex``, because eight of these themes name these
    colours ``grayNN``: ``gray100`` and ``#FFFFFF`` draw one pixel and compare
    unequal as strings.
    """
    themes = sorted(Path("themes").glob("*.json"))
    assert len(themes) == 10, (
        f"{len(themes)} theme files found, not the 10 this app ships -- an "
        "empty-set assertion over a glob passes when the glob finds nothing"
    )

    flat = set()
    for path in themes:
        frame = json.loads(path.read_text())["CTkFrame"]
        for mode, half in (("Light", 0), ("Dark", 1)):
            surface = _as_hex(frame["fg_color"][half])
            subtle = _as_hex(frame["top_fg_color"][half])
            if surface == subtle:
                flat.add(f"{path.stem}/{mode}")

    assert flat == set(), (
        "these themes give both surfaces one colour, so a row has no edge "
        f"against its pane on them: {sorted(flat)}"
    )


# SEP-M6 -- the (theme, mode) pairs whose ``muted_text`` sat under the 4.5:1
# text bar *before* SEP-M1 and still do, measured 2026-11-12. Eight themes
# carry CustomTkinter's bundled ``#858585`` placeholder, which is 2.498-2.957
# against their own light surfaces. SEP-M1 did not cause this and does not fix
# it; it is filed as PBG-A12. Named here rather than skipped, so the pairs
# outside it are held to the bar and no further theme can join the set
# unnoticed.
MUTED_TEXT_UNDER_BAR_BEFORE_SEP = {
    "base_dark_blue/Light",
    "blue/Light",
    "davipa/Light",
    "green/Light",
    "grey/Light",
    "orange/Light",
    "pink/Light",
    "purple/Light",
}


def test_sepm6_the_two_label_colours_are_legible_on_both_surfaces():
    """SEP-M6 — ``muted_text`` and ``body_text`` against both surface tokens.

    ``muted_text`` is ``CTkEntry.placeholder_text_color``, and the app uses it
    as a *label* colour as well as a placeholder -- the Plan panes' hints and
    summaries, the Plan chips' times, and twenty-odd labels on the project
    boards. So separating the surfaces moved the ground under it: giving
    ``black_white`` a ``#F3F4F6`` subtle surface took its light placeholder
    from 4.834 to 4.393 and under the bar, which is what SEP-M6 darkened
    ``#6B7280`` to ``#4B5563`` for.

    Measured against *both* tokens, because a label can sit on either -- the
    Plan summary is on the pane, the chip time on the chip -- and over all ten
    theme files rather than the one this process loaded, for the reason
    ``test_pdm9`` gives.

    What is deliberately *not* asserted: that every pair clears the bar. Eight
    themes ship CustomTkinter's ``#858585`` placeholder at 2.5-3.0:1 on their
    own light surfaces, which is older than this work and worse than what it
    fixed. Asserting the bar outright would redden the suite for a defect this
    batch did not cause; skipping those themes would let the two it touched
    regress silently. So the set of failures is asserted to be *exactly* the
    set that predates it.
    """
    themes = sorted(Path("themes").glob("*.json"))
    assert len(themes) == 10, (
        f"{len(themes)} theme files found, not the 10 this app ships -- a "
        "floor here would hide a theme that stopped being measured"
    )

    muted_under = set()
    body_failures = []
    for path in themes:
        theme = json.loads(path.read_text())
        for mode, half in (("Light", 0), ("Dark", 1)):
            surfaces = {
                "surface": _as_hex(theme["CTkFrame"]["fg_color"][half]),
                "surface_subtle": _as_hex(theme["CTkFrame"]["top_fg_color"][half]),
            }
            muted = _as_hex(theme["CTkEntry"]["placeholder_text_color"][half])
            body = _as_hex(theme["CTkLabel"]["text_color"][half])
            for token, surface in surfaces.items():
                if contrast_ratio(surface, muted) < MIN_CONTRAST:
                    muted_under.add(f"{path.stem}/{mode}")
                ratio = contrast_ratio(surface, body)
                if ratio < MIN_CONTRAST:
                    body_failures.append(
                        f"{path.stem}/{mode}: body {body} on {token} "
                        f"{surface} is {ratio:.2f}"
                    )

    assert not body_failures, (
        f"body text closer than {MIN_CONTRAST}:1 to a surface behind it: "
        + "; ".join(sorted(body_failures))
    )
    assert muted_under == MUTED_TEXT_UNDER_BAR_BEFORE_SEP, (
        "the themes whose muted label text is under "
        f"{MIN_CONTRAST}:1 changed.\n"
        f"  joined: {sorted(muted_under - MUTED_TEXT_UNDER_BAR_BEFORE_SEP)}\n"
        f"  left:   {sorted(MUTED_TEXT_UNDER_BAR_BEFORE_SEP - muted_under)}\n"
        "A theme that joined is a regression. A theme that left is PBG-A12 "
        "being fixed -- take it out of the set above with the fix."
    )
