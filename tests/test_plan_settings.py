"""TB-M4 — the day settings survive a corrupt file, and survive a round trip.

Purpose: prove the four day values and the seven weekday flags are coerced on
         load and on save, and that a hand-edited settings file cannot stop the
         app from starting.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
Tests:   this file

Every test here points ``get_settings_path`` at ``tmp_path``. The default
resolves to the user's real settings file, and a test that wrote there would
change the running app's configuration.
"""

from __future__ import annotations

import json

import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.time_block_layout import DEFAULT_DAY_END, DayBounds


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    """A settings path inside tmp_path, restored by monkeypatch on exit."""
    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        AppSettings, "get_settings_path", classmethod(lambda cls: path)
    )
    return path


def _write(settings_file, **values):
    settings_file.write_text(json.dumps(values))


def test_tbm41_bad_time_falls_back_to_default(settings_file):
    """TB-M4.1 — a garbage time loads as the default instead of raising.

    "9am" is the realistic corruption: it is what a person types when they
    hand-edit the file, and the packing arithmetic cannot read it. The app
    starting with 08:00 is recoverable; the app not starting is not.
    """
    _write(settings_file, plan_day_start="9am", plan_day_end="tea time")

    settings = AppSettings.load()

    assert settings.plan_day_start == "08:00"
    assert settings.plan_day_end == "17:00"


def test_a_readable_time_is_kept_and_not_defaulted(settings_file):
    """The companion to the fallback: a valid value must survive load.

    Without this, a normalizer that returned the default unconditionally would
    pass the test above and silently discard every setting the user made.
    """
    _write(settings_file, plan_day_start="06:30", plan_day_end="19:45")

    settings = AppSettings.load()

    assert settings.plan_day_start == "06:30"
    assert settings.plan_day_end == "19:45"


def test_a_time_is_normalized_to_hh_mm(settings_file):
    """``9:5`` is readable, so it is kept -- in the one written form."""
    _write(settings_file, plan_day_start="9:5")

    settings = AppSettings.load()

    assert settings.plan_day_start == "09:05"


@pytest.mark.parametrize(
    "stored, expected",
    [
        ([True, True], [True, True, False, False, False, False, False]),
        ([True] * 9, [True] * 7),
        ("nonsense", [True, True, True, True, True, False, False]),
        (42, [True, True, True, True, True, False, False]),
        (None, [True, True, True, True, True, False, False]),
        ([1, 0, "yes", "", None, 0, 1], [True, False, True, False, False, False, True]),
    ],
)
def test_tbm42_weekday_list_is_coerced_to_seven(settings_file, stored, expected):
    """TB-M4.2 — the weekday flags are always exactly seven booleans.

    The string case is the one that mattered: a str is iterable, so coercing
    it element-wise gave seven enabled days from the word "nonsense" -- a
    corrupt file that quietly turned on weekend blocking. A non-list falls back
    to the default rather than being taken apart.
    """
    _write(settings_file, plan_block_weekdays=stored)

    settings = AppSettings.load()

    assert settings.plan_block_weekdays == expected
    assert len(settings.plan_block_weekdays) == 7
    assert all(isinstance(flag, bool) for flag in settings.plan_block_weekdays)


@pytest.mark.parametrize(
    "stored, expected",
    [("60", 60), (-10, 0), (99999, 24 * 60), ("lunch", 60), (None, 60), (45.9, 45)],
)
def test_lunch_minutes_are_clamped_to_a_whole_day(settings_file, stored, expected):
    """A lunch longer than a day, or shorter than nothing, is not a day shape.

    Clamped rather than rejected: the number is still usable at the edge, and
    an unreadable one falls back to the 60 the default day uses.
    """
    _write(settings_file, plan_lunch_minutes=stored)

    settings = AppSettings.load()

    assert settings.plan_lunch_minutes == expected


def test_tbm43_day_settings_round_trip(settings_file):
    """TB-M4.3 — what the dialog saves is what the next launch loads.

    Read back through ``load`` rather than off the object, because ``save``
    normalizes too: a value that round-tripped in memory but was mangled on
    the way to disk would still break the first pack after a restart.
    """
    settings = AppSettings()
    settings.plan_day_start = "07:15"
    settings.plan_lunch_start = "11:45"
    settings.plan_lunch_minutes = 30
    settings.plan_day_end = "18:30"
    settings.plan_block_weekdays = [False, True, True, True, True, True, False]
    settings.save()

    reloaded = AppSettings.load()

    assert reloaded.plan_day_start == "07:15"
    assert reloaded.plan_lunch_start == "11:45"
    assert reloaded.plan_lunch_minutes == 30
    assert reloaded.plan_day_end == "18:30"
    assert reloaded.plan_block_weekdays == [False, True, True, True, True, True, False]


def test_save_normalizes_before_writing(settings_file):
    """A bad value set on the object is cleaned on the way out, not stored.

    The dialog validates, but it is not the only writer: a future screen that
    sets a field directly must not be able to put an unreadable time on disk
    for the next launch to fall back from.
    """
    settings = AppSettings()
    settings.plan_day_start = "half seven"
    settings.plan_block_weekdays = [True]
    settings.save()

    written = json.loads(settings_file.read_text())

    assert written["plan_day_start"] == "08:00"
    assert written["plan_block_weekdays"] == [True] + [False] * 6


def test_an_unreadable_settings_file_does_not_stop_the_app(settings_file):
    """Truncated JSON loads as defaults -- P1: a bad file is not a dead app."""
    settings_file.write_text('{"plan_day_start": "07:0')

    settings = AppSettings.load()

    assert settings.plan_day_start == "08:00"
    assert settings.plan_block_weekdays == [True] * 5 + [False] * 2


def test_the_loaded_settings_build_usable_day_bounds(settings_file):
    """The point of all the coercion: ``DayBounds`` can read the result.

    Asserts the derived minutes, not the strings: this is the one path the
    packing arithmetic actually consumes, and a normalizer that produced
    plausible-looking text DayBounds still choked on would pass every test
    above.
    """
    _write(
        settings_file,
        plan_day_start="9am",
        plan_lunch_start="12:30",
        plan_lunch_minutes="45",
        plan_day_end="17:00",
        plan_block_weekdays="nonsense",
    )

    bounds = DayBounds.from_settings(AppSettings.load())

    assert bounds.day_start_minutes == 8 * 60
    assert bounds.lunch_start_minutes == 12 * 60 + 30
    assert bounds.lunch_end_minutes == 13 * 60 + 15
    assert bounds.day_end_minutes == 17 * 60


# --- found by the fix-range re-sweep ---------------------------------------


@pytest.mark.parametrize("stored", ["25:00", "24:00", "99:59", "170:0"])
def test_a_day_end_stored_past_midnight_is_brought_inside_the_day(
    settings_file, stored
):
    """A dirty-state test: the file can already hold what the dialog now refuses.

    The dialog validates new input, but it accepted and stored `25:00` before
    that check existed, so a file on disk can hold it today. Loaded unbounded,
    `day_end_minutes` is past every block the planner can make, and the "past
    day end" warning -- Day End's only job -- stays off permanently with
    nothing to say so. Guarding only the keyboard would heal new input and
    leave that file wrong forever.
    """
    settings_file.write_text(json.dumps({"plan_day_end": stored}))

    settings = AppSettings.load()

    assert settings.plan_day_end == DEFAULT_DAY_END
    assert DayBounds.from_settings(settings).day_end_minutes < 24 * 60


@pytest.mark.parametrize("field", ["plan_day_start", "plan_lunch_start"])
def test_the_other_day_bounds_are_bounded_too(settings_file, field):
    """The sibling fields, so the fix is not applied to one of three."""
    settings_file.write_text(json.dumps({field: "26:30"}))

    settings = AppSettings.load()

    assert getattr(settings, field) != "26:30"
    bounds = DayBounds.from_settings(settings)
    assert bounds.day_start_minutes < 24 * 60
    assert bounds.lunch_start_minutes < 24 * 60


def test_a_day_end_inside_the_day_still_survives_a_round_trip(settings_file):
    """Paired with the clamping tests so a normaliser that replaced every
    value would not pass for the right reason."""
    settings_file.write_text(json.dumps({"plan_day_end": "23:59"}))

    assert AppSettings.load().plan_day_end == "23:59"
