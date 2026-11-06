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
import shutil

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


# --- found by the re-sweep of this batch's own fix commits -------------------


def test_an_unreadable_settings_file_is_kept_before_it_is_overwritten(settings_file):
    """The only copy of the user's settings must survive the recovery.

    ``load`` falls back to all-defaults when the file exists but will not
    parse, and ``save`` writes the whole object -- so the first save after a
    corrupt load replaces every value the user ever set, including the ones no
    screen in the app can re-enter by hand. Overwriting is how they get a
    working file back; destroying the original on the way is not part of that.
    """
    original = '{ "obsidian_vault_path": "/Users/me/vault", this is not json'
    settings_file.write_text(original)

    loaded = AppSettings.load()
    assert loaded.settings_unreadable is True

    assert loaded.save() is True

    kept = list(settings_file.parent.glob("settings.json.unreadable-*"))
    assert len(kept) == 1, f"the unreadable file was not kept aside: {kept}"
    assert kept[0].read_text() == original, "the kept copy is not what was there"
    assert json.loads(settings_file.read_text())["plan_day_start"] == "08:00"


def test_a_readable_file_is_not_copied_aside_on_every_save(settings_file):
    """The companion: a backup on every save would be a litter of files.

    Without this, keeping the unreadable file could be implemented as keeping
    every file, which passes the test above and leaves a new copy in the
    application data directory each time any settings screen is used.
    """
    _write(settings_file, plan_day_start="07:00")
    loaded = AppSettings.load()
    assert loaded.settings_unreadable is False

    loaded.save()

    assert list(settings_file.parent.glob("settings.json.unreadable-*")) == []


def test_a_guessed_day_shape_survives_the_save_that_hides_it(settings_file):
    """Writing the file makes it parseable; it does not make it theirs.

    Every settings screen loads its own object and saves the whole of it, so
    the first save from *anywhere* -- a theme, a column width, a timer window
    position -- writes a full set of defaults out as ordinary-looking
    settings. If the only record that the day's four times were a guess lived
    in memory, that save would erase it, and the Plan screen's irreversible
    adoption would act on a day start nobody chose.

    The parse flag is cleared by the write, because the file does now parse.
    The day's shape is a separate fact and goes to disk.
    """
    settings_file.write_text("{ not json")
    loaded = AppSettings.load()
    assert loaded.settings_unreadable is True
    assert loaded.plan_day_shape_unconfirmed is True

    assert loaded.save() is True

    assert loaded.settings_unreadable is False, (
        "the file parses now, and the parse flag still says it does not"
    )
    assert loaded.plan_day_shape_unconfirmed is True, (
        "a write from anywhere in the app turned a guessed day start into one"
        " adoption will act on"
    )


def test_a_guessed_day_shape_survives_a_relaunch(settings_file):
    """P8 -- the state that matters here is the state between runs.

    This is the whole reason the fact is a field. A corrupt file, any screen
    saving, then a restart: the file parses, so nothing on load says the day's
    four times were invented. The flag that lived only in memory was gone, and
    adoption ran against a guessed 08:00 on the next visit to the Plan screen.
    """
    settings_file.write_text("{ not json")
    AppSettings.load().save()

    relaunched = AppSettings.load()

    assert relaunched.settings_unreadable is False, "the file parses; this is a fresh load"
    assert relaunched.plan_day_shape_unconfirmed is True, (
        "one relaunch turned a guessed day shape into a confirmed one"
    )


def test_a_second_save_does_not_keep_a_readable_file_aside(settings_file):
    """One `.unreadable-` copy, of the file that was actually unreadable.

    The parse flag drives the copy-aside. Left set after a successful write, a
    second save in the same session copies a file that now parses perfectly to
    `settings.json.unreadable-<stamp>` and logs that it was unreadable.
    """
    settings_file.write_text("{ not json")
    loaded = AppSettings.load()

    loaded.save()
    loaded.plan_day_start = "07:00"
    loaded.save()

    kept = list(settings_file.parent.glob("settings.json.unreadable-*"))
    assert len(kept) == 1, f"kept a readable file aside as an unreadable one: {kept}"
    assert kept[0].read_text() == "{ not json"


def test_a_failed_write_is_reported(settings_file):
    """``save`` swallowed its own failure and the caller reported success.

    A readable file here, so the backup path is not involved: the settings
    path is a directory, and ``open(..., 'w')`` raises on it.
    """
    _write(settings_file, plan_day_start="07:00")
    loaded = AppSettings.load()
    assert loaded.settings_unreadable is False
    settings_file.unlink()
    settings_file.mkdir()

    assert loaded.save() is False, "a failed write reported success"


def test_a_failed_backup_refuses_to_overwrite_the_unreadable_file(
    settings_file, monkeypatch
):
    """The guard must not proceed past its own failure.

    Keeping the file aside and then overwriting it anyway when the copy failed
    is worse than not trying: the only copy of whatever could not be read out
    of it is gone, and the caller is told the settings were saved. Refusing is
    the lesser failure, and it is a failure the dialog shows.
    """
    original = '{ "obsidian_vault_path": "/Users/me/vault", not json'
    settings_file.write_text(original)
    loaded = AppSettings.load()

    def boom(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(shutil, "copy2", boom)

    assert loaded.save() is False, (
        "overwrote the file after failing to keep a copy of it, and said it saved"
    )
    assert settings_file.read_text() == original, "the only copy was destroyed"
    assert "set aside" in loaded.last_save_error, (
        f"blamed the write for a failure in the backup: {loaded.last_save_error!r}"
    )


def test_the_two_save_failures_do_not_share_one_message(settings_file, monkeypatch):
    """They have different causes and different remedies.

    One means the settings file could not be written -- check permissions, free
    space. The other means a file that would not load could not be set aside,
    nothing was touched, and the way out is to move or delete that file. A
    single message sends half the users to look at the wrong thing.
    """
    _write(settings_file, plan_day_start="07:00")
    readable = AppSettings.load()
    settings_file.unlink()
    settings_file.mkdir()
    assert readable.save() is False
    write_failure = readable.last_save_error

    settings_file.rmdir()
    settings_file.write_text("{ not json")
    unreadable = AppSettings.load()
    monkeypatch.setattr(shutil, "copy2", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))
    assert unreadable.save() is False
    backup_failure = unreadable.last_save_error

    assert write_failure != backup_failure, (
        f"both failures say {write_failure!r}"
    )
    assert "write" in write_failure
    assert "set aside" in backup_failure


def test_a_failing_status_print_does_not_fail_the_save(settings_file, monkeypatch):
    """A status message is not part of the operation it describes.

    The print naming where the unreadable file was kept sat inside the ``try``
    that guarded the copy, so a stdout write that failed -- a packaged app with
    a closed stdout, a full disk -- read as a copy that failed and refused the
    save, and the handler's own print then escaped a method whose callers have
    no handler. Exactly the shape of the credential-token failure in the
    project's own notes.
    """
    settings_file.write_text("{ not json")
    loaded = AppSettings.load()

    import builtins

    def no_stdout(*args, **kwargs):
        raise OSError("stdout is closed")

    monkeypatch.setattr(builtins, "print", no_stdout)

    assert loaded.save() is True, "a message that could not be printed failed the save"
    assert json.loads(settings_file.read_text())["plan_day_start"] == "08:00"
    assert len(list(settings_file.parent.glob("settings.json.unreadable-*"))) == 1
