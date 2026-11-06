"""The Settings screen's Save buttons must not report a write that refused.

``AppSettings.save`` returns False and writes nothing when a settings file is
there, will not parse, and cannot be copied aside -- refusing is the lesser
failure, because that file is the only copy of whatever could not be read out
of it. Every Save button on the Settings screen ignored that and printed
"✓ Saved" over it, and two of them did more than print: the appearance section
applied the theme app-wide, and the email section reloaded launchd from a file
that had not changed.

These drive the real methods against a stub of the widgets, which is the
pattern tests/test_settings_week_rule_ui.py established for this screen -- the
screen itself needs an app, a sidebar and a mapped window to build.
"""

import json
import shutil
from types import SimpleNamespace

import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.screens import settings_integrations
from src.getmoredone.screens.settings import SettingsScreen
from src.getmoredone.screens.settings_integrations import SettingsIntegrationsMixin


class _Label:
    """A status label that records what it was told, not how it looked."""

    def __init__(self):
        self.text = None
        self.level_color = None

    def configure(self, text=None, text_color=None):
        self.text = text
        self.level_color = text_color


@pytest.fixture
def settings_path(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        AppSettings, "get_settings_path", classmethod(lambda cls: path)
    )
    return path


def _refuse_the_write(monkeypatch, settings_path):
    """The one state in which ``save`` declines: unparseable, uncopyable."""
    original = '{ "obsidian_vault_path": "/Users/me/vault", not json'
    settings_path.write_text(original)
    monkeypatch.setattr(
        shutil, "copy2", lambda *a, **k: (_ for _ in ()).throw(OSError("full"))
    )
    return original


def _timer_audio_stub(settings, label):
    stub = SimpleNamespace(
        settings=settings,
        music_folder_var=SimpleNamespace(get=lambda: "/Users/me/music"),
        music_volume_var=SimpleNamespace(get=lambda: 0.5),
        timer_audio_status_label=label,
    )
    stub._set_status = lambda lbl, text, level="success": SettingsScreen._set_status(
        stub, lbl, text, level
    )
    stub._write_settings = lambda lbl: SettingsScreen._write_settings(stub, lbl)
    return stub


def test_a_refused_write_is_not_reported_as_saved(settings_path, monkeypatch):
    """The message has to be about what happened to the file."""
    original = _refuse_the_write(monkeypatch, settings_path)
    label = _Label()
    settings = AppSettings.load()

    SettingsScreen.save_timer_audio_settings(_timer_audio_stub(settings, label))

    assert settings_path.read_text() == original, "overwrote the unreadable file"
    assert "✓" not in (label.text or ""), (
        f"reported a save that did not happen: {label.text!r}"
    )
    assert label.text == settings.last_save_error, (
        f"did not report why the write was refused: {label.text!r}"
    )


def test_a_successful_write_is_still_reported_as_saved(settings_path):
    """The companion: a guard that always refuses would pass the test above."""
    settings_path.write_text(json.dumps({"music_volume": 0.1}))
    label = _Label()
    settings = AppSettings.load()

    SettingsScreen.save_timer_audio_settings(_timer_audio_stub(settings, label))

    assert json.loads(settings_path.read_text())["music_folder"] == "/Users/me/music"
    assert label.text.startswith("✓ Settings saved"), (
        f"a write that succeeded was not reported: {label.text!r}"
    )


def test_the_theme_is_not_applied_over_a_refused_write(settings_path, monkeypatch):
    """The appearance section does more than print, so it has more to skip.

    It hands its object to the app and applies the theme app-wide. Over a
    refused write that shows the user a theme the file does not hold, which is
    gone the next time the app starts -- the "✓ Saved" lie made visible.
    """
    _refuse_the_write(monkeypatch, settings_path)
    label = _Label()
    settings = AppSettings.load()
    app = SimpleNamespace(settings=object(), applied=[])
    app.apply_theme_preferences = lambda: app.applied.append(True)
    before = app.settings

    stub = SimpleNamespace(
        settings=settings,
        app=app,
        appearance_mode_var=SimpleNamespace(get=lambda: "Dark"),
        theme_name_var=SimpleNamespace(get=lambda: "dark-blue"),
        list_row_font_size_var=SimpleNamespace(get=lambda: "14"),
        completion_badge_path_var=SimpleNamespace(get=lambda: ""),
        completion_confetti_threshold_var=SimpleNamespace(get=lambda: "0"),
        _parse_positive_or_zero_int=lambda value, default=0: default,
        appearance_status_label=label,
    )
    stub._set_status = lambda lbl, text, level="success": SettingsScreen._set_status(
        stub, lbl, text, level
    )
    stub._write_settings = lambda lbl: SettingsScreen._write_settings(stub, lbl)

    SettingsScreen.apply_theme_preferences(stub)

    assert app.applied == [], "applied a theme the settings file does not hold"
    assert app.settings is before, "handed the app an object it cannot have written"
    assert "✓" not in (label.text or ""), f"reported a save: {label.text!r}"


def test_launchd_is_not_reloaded_over_a_refused_write(
    settings_path, monkeypatch
):
    """The updater re-reads the file, so a reload over a refusal is a lie twice.

    launchd would be reloaded against the interval already in the file while
    the user is told "Saved (launchd updated)." about the new one.
    """
    _refuse_the_write(monkeypatch, settings_path)
    ran = []
    monkeypatch.setattr(
        settings_integrations.subprocess, "run", lambda *a, **k: ran.append(a)
    )
    label = _Label()
    settings = AppSettings.load()

    stub = SimpleNamespace(
        settings=settings,
        gmail_enabled_var=SimpleNamespace(get=lambda: True),
        gmail_trigger_var=SimpleNamespace(get=lambda: "GMD"),
        gmail_moved_var=SimpleNamespace(get=lambda: "GMD/moved"),
        gmail_interval_var=SimpleNamespace(get=lambda: "120"),
        calendar_days_var=SimpleNamespace(get=lambda: "14"),
        gmail_status_label=label,
    )
    stub._set_status = lambda lbl, text, level="success": SettingsScreen._set_status(
        stub, lbl, text, level
    )
    stub._write_settings = lambda lbl: SettingsScreen._write_settings(stub, lbl)

    SettingsIntegrationsMixin.save_email_import_settings(stub)

    assert ran == [], "reloaded launchd from a settings file that was not written"
    assert "Saved" not in (label.text or ""), (
        f"reported a save that did not happen: {label.text!r}"
    )
