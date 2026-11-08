"""WCAG-based color contrast helpers for foreground text selection."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
import logging
import re


logger = logging.getLogger(__name__)

#: The one hex shape this module stores and hands on, after upper-casing.
#:
#: Tk itself also parses ``#RGB``, ``#RRRGGGBBB`` and ``#RRRRGGGGBBBB``; those
#: are refused here rather than carried, and ``normalize_hex_color`` expands
#: the three-digit form before matching. What matters is the other direction:
#: ``int(text, 16)`` must not be used for this, because Python accepts a
#: leading sign, a ``0x`` prefix, PEP-515 underscores, surrounding whitespace
#: and non-ASCII decimal digits, so ``int("0X1234", 16)`` succeeds while Tk
#: raises on ``#0X1234``. A validator that exists to keep a bad colour away
#: from Tk has to be at least as strict as Tk, and this is stricter.
#: Checked against the real Tk by
#: ``tests/test_priority_level_colors.py::test_plcm3_the_section_builds_on_real_widgets``.
_HEX_COLOR_RE = re.compile(r"#[0-9A-F]{6}\Z")


def _normalize_hex(hex_color: str) -> str:
    text = (hex_color or "").strip().upper()
    if not text.startswith("#"):
        text = f"#{text}"
    if not _HEX_COLOR_RE.match(text):
        raise ValueError(f"Invalid hex color: {hex_color}")
    return text


def normalize_hex_color(value: object) -> "Optional[str]":
    """Coerce a stored or typed colour to ``#RRGGBB``, or ``None`` if it cannot be.

    Purpose: PLC-M2.5 -- a colour read back from settings.json, or typed into an
             entry, reaches Tk, and Tk raises on a value it does not recognise.
             A raised ``TclError`` inside a row build takes the whole list
             screen down, so a bad value has to be caught before it gets there.
    Spec:    docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m2
    Tests:   tests/test_priority_level_colors.py::test_plcm25_a_malformed_stored_colour_falls_back_to_the_default

    Returns rather than raises, unlike ``_normalize_hex``: every caller here has
    a default to fall back to and wants to log the bad value, not handle an
    exception. A three-digit ``#ABC`` is expanded, because that is a form people
    type and every browser accepts; a named colour such as ``"red"`` is not,
    because accepting some names and not others is worse than accepting none.
    """
    if not isinstance(value, str):
        return None
    text = value.strip().upper()
    if not text:
        return None
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) == 4:
        text = f"#{text[1] * 2}{text[2] * 2}{text[3] * 2}"
    if not _HEX_COLOR_RE.match(text):
        return None
    return text


def _srgb_channel_to_linear(channel: int) -> float:
    c_srgb = max(0.0, min(1.0, channel / 255.0))
    if c_srgb <= 0.04045:
        return c_srgb / 12.92
    return ((c_srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """Compute WCAG relative luminance for #RRGGBB."""
    color = _normalize_hex(hex_color)
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    r_lin = _srgb_channel_to_linear(r)
    g_lin = _srgb_channel_to_linear(g)
    b_lin = _srgb_channel_to_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(bg_hex: str, fg_hex: str) -> float:
    """Compute WCAG contrast ratio between two colors."""
    l_bg = relative_luminance(bg_hex)
    l_fg = relative_luminance(fg_hex)
    l1, l2 = (l_bg, l_fg) if l_bg >= l_fg else (l_fg, l_bg)
    return (l1 + 0.05) / (l2 + 0.05)


def meets_wcag(bg_hex: str, fg_hex: str, large_text: bool = False) -> bool:
    """Return True when contrast meets WCAG AA threshold."""
    threshold = 3.0 if large_text else 4.5
    return contrast_ratio(bg_hex, fg_hex) >= threshold


@dataclass(frozen=True)
class ContrastChoice:
    text_color: str
    contrast_ratio: float
    meets_threshold: bool


@lru_cache(maxsize=512)
def _pick_text_color_cached(bg_hex: str, light: str, dark: str, large_text: bool) -> ContrastChoice:
    bg = _normalize_hex(bg_hex)
    light_color = _normalize_hex(light)
    dark_color = _normalize_hex(dark)

    light_cr = contrast_ratio(bg, light_color)
    dark_cr = contrast_ratio(bg, dark_color)

    if dark_cr >= light_cr:
        chosen = dark_color
        chosen_cr = dark_cr
    else:
        chosen = light_color
        chosen_cr = light_cr

    threshold = 3.0 if large_text else 4.5
    meets = chosen_cr >= threshold
    if not meets:
        logger.warning(
            "WCAG AA contrast not met: bg=%s chosen=%s contrast=%.2f threshold=%.1f",
            bg,
            chosen,
            chosen_cr,
            threshold,
        )

    return ContrastChoice(text_color=chosen, contrast_ratio=chosen_cr, meets_threshold=meets)


def pick_text_color_with_meta(
    bg_hex: str,
    light: str = "#FFFFFF",
    dark: str = "#000000",
    large_text: bool = False,
) -> ContrastChoice:
    """Pick the best text color and include contrast metadata."""
    return _pick_text_color_cached(bg_hex, light, dark, large_text)


def pick_text_color(bg_hex: str, light: str = "#FFFFFF", dark: str = "#000000") -> str:
    """Pick the best-contrast text color against background."""
    try:
        return pick_text_color_with_meta(bg_hex, light=light, dark=dark, large_text=False).text_color
    except ValueError:
        return "#000000"
