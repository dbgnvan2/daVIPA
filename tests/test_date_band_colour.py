"""DBC — the Day/Date band background colour setting.

Spec: docs/unused-docs/implementation_plan_2026-11-15_date_band_colour.md
"""

import logging
import pathlib
import subprocess
import sys

import pytest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.color_contrast import contrast_ratio
from src.getmoredone.screens.settings import SettingsScreen
from src.getmoredone.theme import (
    _warned_date_band_colors,
    date_band_colors,
    semantic_colors,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# =========================================================================
# DBC-M1 — the setting
# =========================================================================

def test_dbcm1_the_field_round_trips_and_defaults_to_the_theme(tmp_path, monkeypatch):
    """DBC-M1 — the field ships blank and survives a save/load."""
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(
        "src.getmoredone.app_settings.default_settings_path",
        lambda: settings_file,
    )

    assert AppSettings().list_date_band_color == ""

    settings = AppSettings.load()
    assert settings.list_date_band_color == ""

    settings.list_date_band_color = "#D9E8FF"
    assert settings.save()
    assert AppSettings.load().list_date_band_color == "#D9E8FF"


# =========================================================================
# DBC-M2 — the helper
# =========================================================================

def test_dbcm2_blank_is_the_theme_surface():
    """DBC-M2 — a cleared field means the theme's own band colour."""
    band = date_band_colors(SimpleNamespace(list_date_band_color=""))
    assert band.fill == semantic_colors()["surface_subtle"]
    # None means "use the theme's own pairing".
    assert band.text_color is None

    # Whitespace is cleared too, and a missing attribute is an older
    # settings.json with no such key.
    assert date_band_colors(SimpleNamespace(list_date_band_color="   ")).fill == band.fill
    assert date_band_colors(SimpleNamespace()).fill == band.fill


def test_dbcm21_a_colour_carries_a_derived_text_colour():
    """DBC-M2.1 — a picked fill brings a label colour legible on it."""
    band = date_band_colors(SimpleNamespace(list_date_band_color="#D9E8FF"))
    assert band.fill == "#D9E8FF"
    assert band.text_color == "#000000"
    assert contrast_ratio(band.fill, band.text_color) >= 4.5

    # A dark pick flips the label, which is the point of deriving it.
    dark = date_band_colors(SimpleNamespace(list_date_band_color="#1B3A5C"))
    assert dark.text_color == "#FFFFFF"
    assert contrast_ratio(dark.fill, dark.text_color) >= 4.5


def test_dbcm22_an_unusable_colour_falls_back_to_the_theme(caplog):
    """DBC-M2.2 — a value Tk would reject never reaches Tk, and warns once."""
    _warned_date_band_colors.clear()
    theme_fill = semantic_colors()["surface_subtle"]

    with caplog.at_level(logging.WARNING, logger="src.getmoredone.theme"):
        first = date_band_colors(SimpleNamespace(list_date_band_color="rebeccapurple"))
        second = date_band_colors(SimpleNamespace(list_date_band_color="rebeccapurple"))

    assert first == second
    assert first.fill == theme_fill
    assert first.text_color is None
    # Once per bad value, not once per date group in the list.
    assert sum("rebeccapurple" in r.getMessage() for r in caplog.records) == 1

    # Not a string at all: a hand-edited settings.json can hold anything.
    assert date_band_colors(SimpleNamespace(list_date_band_color=42)).fill == theme_fill
    _warned_date_band_colors.clear()


# =========================================================================
# DBC-M3 — the band itself
# =========================================================================

def _render_band(colour: str):
    """Build Upcoming in a subprocess and return its band's reported colours."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tests" / "render_date_band.py"), colour],
        capture_output=True, text=True, timeout=180, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    lines = dict(
        (line.split(" ", 1)[0], line.split(" ", 1)[1])
        for line in result.stdout.splitlines() if " " in line
    )
    assert "FILL" in lines, f"no band rendered: {result.stdout}"
    return lines


def test_dbcm3_the_upcoming_band_is_drawn_from_the_helper():
    """DBC-M3 — the setting reaches the widget, fill and label together."""
    themed = _render_band("")
    assert themed["FILL"] == themed["THEME"]

    picked = _render_band("#D9E8FF")
    assert picked["FILL"] == "#D9E8FF"
    assert picked["TEXT"] == "#000000"


# =========================================================================
# DBC-M4 — the Settings row
# =========================================================================

class _Var:
    """Stands in for a ``ctk.StringVar`` with no Tk root behind it."""

    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class _Swatch:
    def __init__(self):
        self.fg_color = None

    def configure(self, **kwargs):
        self.fg_color = kwargs.get("fg_color", self.fg_color)


class _StubAppearanceSection:
    """Enough of ``SettingsScreen`` to run its real Appearance save handler.

    The shape ``test_priority_level_colors.py`` uses: the real method, against
    stand-ins for the Tk variables and the helpers it calls.
    """

    apply_theme_preferences = SettingsScreen.apply_theme_preferences
    _parse_positive_or_zero_int = SettingsScreen._parse_positive_or_zero_int
    _date_band_swatch_color = SettingsScreen._date_band_swatch_color
    _refresh_date_band_swatch = SettingsScreen._refresh_date_band_swatch

    def __init__(self, band_value, write_succeeds=True):
        self.settings = AppSettings()
        self.appearance_mode_var = _Var("dark")
        self.theme_name_var = _Var("apple_grey")
        self.list_row_font_size_var = _Var("14")
        self.completion_badge_path_var = _Var("")
        self.completion_confetti_threshold_var = _Var("0")
        self.list_date_band_color_var = _Var(band_value)
        self.list_date_band_swatch = _Swatch()
        self.appearance_status_label = SimpleNamespace(text="", level=None)
        self.app = SimpleNamespace(apply_theme_preferences=self._noop)
        self._write_succeeds = write_succeeds
        self.writes = 0

    def _noop(self):
        pass

    def _set_status(self, label, text, level="success"):
        label.text = text
        label.level = level

    def _write_settings(self, label):
        if self._write_succeeds:
            self.writes += 1
            return True
        self._set_status(label, "Could not write the settings file", "error")
        return False

    def _hand_settings_to_app(self):
        pass

    @property
    def status(self):
        return self.appearance_status_label.text, self.appearance_status_label.level


def test_dbcm4_a_colour_is_saved():
    """DBC-M4 — Apply/Save stores the band colour, normalised."""
    screen = _StubAppearanceSection("d9e8ff")
    screen.apply_theme_preferences()

    assert screen.settings.list_date_band_color == "#D9E8FF"
    assert screen.writes == 1
    assert screen.status[1] == "success"
    # The field is shown what was stored, not what was typed.
    assert screen.list_date_band_color_var.get() == "#D9E8FF"
    assert screen.list_date_band_swatch.fg_color == "#D9E8FF"

    cleared = _StubAppearanceSection("")
    cleared.settings.list_date_band_color = "#D9E8FF"
    cleared.apply_theme_preferences()
    assert cleared.settings.list_date_band_color == ""
    assert cleared.list_date_band_swatch.fg_color == semantic_colors()["surface_subtle"]


def test_dbcm41_a_bad_colour_is_refused_and_not_written():
    """DBC-M4.1 — a typo is reported, not silently replaced by a default."""
    screen = _StubAppearanceSection("rebeccapurple")
    screen.settings.list_date_band_color = "#D9E8FF"
    screen.apply_theme_preferences()

    text, level = screen.status
    assert level == "error"
    assert "rebeccapurple" in text
    # Nothing in the section is written while the value is bad, and the colour
    # already stored is left alone.
    assert screen.writes == 0
    assert screen.settings.list_date_band_color == "#D9E8FF"
