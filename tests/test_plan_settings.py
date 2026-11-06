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
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import ActionItem
from src.getmoredone.screens.plan import PlanScreen
from src.getmoredone.screens.settings import SettingsScreen
from src.getmoredone.time_block_layout import (
    DAY_EXTEND_EARLIER,
    DAY_EXTEND_LATER,
    DEFAULT_DAY_END,
    DayBounds,
)


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
    assert loaded.plan_day_shape_unconfirmed is True

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
    assert loaded.plan_day_start == "07:00", "precondition: the file was read"

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

    The write makes the file parse. It does not make the values anyone's, so
    the field goes to disk with them.
    """
    settings_file.write_text("{ not json")
    loaded = AppSettings.load()
    assert loaded.plan_day_shape_unconfirmed is True

    assert loaded.save() is True

    assert json.loads(settings_file.read_text())["plan_day_shape_unconfirmed"] is True, (
        "the fact that these four values were invented did not reach the file"
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

    assert relaunched.plan_day_shape_unconfirmed is True, (
        "one relaunch turned a guessed day shape into a confirmed one"
    )


def test_a_second_save_does_not_keep_a_readable_file_aside(settings_file):
    """One `.unreadable-` copy, of the file that was actually unreadable.

    ``save`` decides from the file, so the second save sees one that parses and
    leaves it alone. Implemented from a flag captured at load instead, this
    copies a perfectly good file to `settings.json.unreadable-<stamp>` and logs
    that it could not be read.
    """
    settings_file.write_text("{ not json")
    loaded = AppSettings.load()

    loaded.save()
    loaded.plan_day_start = "07:00"
    loaded.save()

    kept = list(settings_file.parent.glob("settings.json.unreadable-*"))
    assert len(kept) == 1, f"kept a readable file aside as an unreadable one: {kept}"
    assert kept[0].read_text() == "{ not json"


# --- found by the fifth pass, over the fourth round's fixes -----------------


def _write_confirmed(settings_file, **values):
    """A settings file whose day shape the user has confirmed.

    All four day values present and ``plan_day_shape_unconfirmed`` present and
    false -- which is what the Day Settings dialog writes, and the only thing
    ``load`` accepts as confirmation.
    """
    day = {
        "plan_day_start": "08:00",
        "plan_lunch_start": "12:00",
        "plan_lunch_minutes": 60,
        "plan_day_end": "17:00",
        "plan_day_shape_unconfirmed": False,
    }
    day.update(values)
    settings_file.write_text(json.dumps(day))


def test_a_settings_file_from_before_day_settings_is_not_a_confirmed_day(
    settings_file,
):
    """The upgrade path, which is the common one, not an edge case.

    Time blocks are as old as the application; the four day values are not.
    A settings file written before Day Settings existed parses perfectly and
    holds none of them, so ``load`` fills in 08:00 / 12:00 / 60 / 17:00 --
    every one of them this build's guess. Read as a confirmed day, the Plan
    screen's adoption then rewrites stored clock times against a day start
    nobody has ever seen, and that cannot be undone.

    ``load`` filters the parsed file against the dataclass fields, which erases
    the difference between a default the user accepted and a default nobody has
    seen. Only the presence of the key carries it.
    """
    _write(settings_file, obsidian_vault_path="/Users/me/vault")

    loaded = AppSettings.load()

    assert loaded.plan_day_start == "08:00", "precondition: the value is a default"
    assert loaded.plan_day_shape_unconfirmed is True, (
        "a file from before Day Settings existed was read as a confirmed day"
    )


def test_a_build_that_dropped_the_field_is_not_confirmation(settings_file):
    """A boolean whose absence means "confirmed" cannot survive a downgrade.

    ``save`` writes ``asdict`` of this dataclass, so a build that does not
    define the field writes a file without the key -- a packaged app one
    version behind, or any build of this batch before the field was added. If
    absence meant confirmation, one launch of that build would clear a guard
    that exists to stop an irreversible write.
    """
    _write_confirmed(settings_file)
    data = json.loads(settings_file.read_text())
    del data["plan_day_shape_unconfirmed"]
    settings_file.write_text(json.dumps(data))

    assert AppSettings.load().plan_day_shape_unconfirmed is True, (
        "a file that lost the key was read as a confirmed day"
    )


def test_a_confirmed_flag_without_the_values_it_describes_is_not_confirmation(
    settings_file,
):
    """The second of the two independent reasons a file is not confirmation.

    Written as one test because it is the only input that reaches the
    key-presence check on its own: a hand-edited file -- the case the whole
    normalizer exists for -- that says the day shape was confirmed while
    holding none of the four values that claim is about. Every file a build of
    this app writes carries both or neither, so for the realistic inputs the
    two checks cover each other, and neither can be removed on the evidence of
    the other's test.
    """
    _write(settings_file, plan_day_shape_unconfirmed=False, theme_name="dark-blue")

    assert AppSettings.load().plan_day_shape_unconfirmed is True, (
        "a flag was believed about four values that were not in the file"
    )


def test_a_day_shape_the_user_confirmed_is_left_alone(settings_file):
    """The companion, and the reason the rule above is a rule and not a floor.

    Refusing everything would gate adoption off permanently and leave every
    legacy block off the grid with no way back. What the dialog writes has to
    read back as confirmation.
    """
    _write_confirmed(settings_file, plan_day_start="07:30")

    loaded = AppSettings.load()

    assert loaded.plan_day_start == "07:30"
    assert loaded.plan_day_shape_unconfirmed is False, (
        "a day the user confirmed in the dialog did not read back as confirmed"
    )


def test_a_day_value_the_app_had_to_substitute_is_not_the_users(settings_file):
    """A value we replaced is a guess, whatever the file says about the rest.

    ``25:00`` is a Day End a build before the bound check could write, and
    ``_normalize_plan_day_settings`` silently replaces it with 17:00 so the app
    still starts. That substitute then fed adoption as though the user had
    chosen it.
    """
    _write_confirmed(settings_file, plan_day_end="25:00")

    loaded = AppSettings.load()

    assert loaded.plan_day_end == "17:00", "precondition: the value was substituted"
    assert loaded.plan_day_shape_unconfirmed is True, (
        "a day end the app substituted was treated as the user's"
    )


def test_a_lunch_the_app_had_to_clamp_is_not_the_users(settings_file):
    """The same, for the one of the four that is a number.

    A lunch of 3000 minutes is clamped to a day. The clamp keeps the packing
    arithmetic sane; it does not make 1440 a lunch anybody chose.
    """
    _write_confirmed(settings_file, plan_lunch_minutes=3000)

    loaded = AppSettings.load()

    assert loaded.plan_lunch_minutes == 24 * 60, "precondition: it was clamped"
    assert loaded.plan_day_shape_unconfirmed is True, (
        "a lunch length the app invented was treated as the user's"
    )


def test_no_settings_file_is_not_a_confirmed_day(settings_file):
    """No file is no confirmation. It is the same four guesses.

    Harmless on a fresh install, where there is nothing to adopt, and the
    honest answer in the case that is not a fresh install: a settings file
    deleted or moved aside with the database kept.
    """
    assert not settings_file.exists(), "precondition: no settings file"

    assert AppSettings.load().plan_day_shape_unconfirmed is True, (
        "a missing settings file was read as a confirmed day"
    )


def test_a_second_object_does_not_archive_a_file_that_now_parses(settings_file):
    """Over a dozen screens each hold their own ``AppSettings``.

    ``app.settings`` is loaded once at startup and lives for the session, and
    the Day Settings dialog saves that object. So: launch on a corrupt file,
    another screen saves and the file is kept aside and replaced, then the user
    opens Day Settings and saves. Decided from a flag captured at load, the
    startup object archives the good file a second time and logs that it could
    not be read; worse, if that copy fails the dialog refuses the write and
    tells the user to move a file that loads -- leaving the one screen that can
    confirm the day's shape unable to.
    """
    corrupt = "{ not json"
    settings_file.write_text(corrupt)
    startup = AppSettings.load()
    other_screen = AppSettings.load()

    assert other_screen.save() is True
    assert startup.save() is True, "refused a write against a file that parses"

    kept = list(settings_file.parent.glob("settings.json.unreadable-*"))
    assert len(kept) == 1, f"archived a file that parses: {[k.name for k in kept]}"
    assert kept[0].read_text() == corrupt
    assert json.loads(settings_file.read_text())["plan_day_shape_unconfirmed"] is True


def test_a_failed_write_is_reported(settings_file):
    """``save`` swallowed its own failure and the caller reported success.

    A readable file here, so the backup path is not involved: the settings
    path is a directory, and ``open(..., 'w')`` raises on it.
    """
    _write(settings_file, plan_day_start="07:00")
    loaded = AppSettings.load()
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


def _date_increment_stub(settings, app, label, box_height="86"):
    """The save method's widgets, stubbed around a real write and hand-over.

    The screen itself needs an app, a sidebar and a mapped window to build, so
    these drive the real method against a stub -- the pattern
    ``tests/test_settings_week_rule_ui.py`` established for this screen. Only
    the widgets are stubbed: ``_write_settings`` and ``_hand_settings_to_app``
    are the screen's own, so the write goes through ``AppSettings.save`` to the
    file the ``settings_file`` fixture points at. A refusal here is a refusal
    the file caused, not a stubbed return value.
    """
    from types import SimpleNamespace

    stub = SimpleNamespace(
        settings=settings,
        app=app,
        include_saturday_var=SimpleNamespace(get=lambda: True),
        include_sunday_var=SimpleNamespace(get=lambda: True),
        default_columns_expanded_var=SimpleNamespace(get=lambda: False),
        first_day_of_week_var=SimpleNamespace(get=lambda: "Monday"),
        week_rule_labels={},
        first_week_of_year_var=SimpleNamespace(get=lambda: "ISO 8601"),
        drag_schedule_text_color_var=SimpleNamespace(get=lambda: "#FFFFFF"),
        drag_schedule_box_height_var=SimpleNamespace(get=lambda: box_height),
        plan_items_col_width_var=SimpleNamespace(get=lambda: "260"),
        date_increment_status_label=label,
    )
    stub._parse_positive_int = lambda value, default: int(value)
    stub._set_status = lambda lbl, text, level="success": None
    stub._write_settings = lambda lbl: SettingsScreen._write_settings(stub, lbl)
    stub._hand_settings_to_app = lambda: SettingsScreen._hand_settings_to_app(stub)
    return stub


def _refuse_the_write(monkeypatch, settings_file):
    """The one state in which ``save`` declines: unparseable, uncopyable.

    The same mechanism ``tests/test_settings_save_refusal.py`` uses, and the
    only real one -- ``save`` refuses when the file on disk will not parse and
    cannot be set aside, because that file is the only copy of whatever could
    not be read out of it. Returns the text that must still be there after.
    """
    original = '{ "obsidian_vault_path": "/Users/me/vault", not json'
    settings_file.write_text(original)
    monkeypatch.setattr(
        shutil, "copy2", lambda *a, **k: (_ for _ in ()).throw(OSError("full"))
    )
    return original


def test_a_saved_box_height_reaches_the_running_app(settings_file):
    """PB-M5 -- the setting the Plan screen reads is the one Save just wrote.

    Found by running the app, after three review passes and a green suite: set
    the box height to 86, Save, walk to another screen and back, and the Day
    Plan is still drawn at 30. The Settings screen edits its own
    ``AppSettings.load()`` and the Plan screen reads ``app.settings`` when it
    is built, so a saved size did nothing until the next launch.

    What the app ends up holding is checked against the file, not against the
    screen's object: the two being the same object is what the previous fix
    did, and it is what the next test is about.
    """
    settings = AppSettings()
    app = type("_App", (), {})()
    at_launch = AppSettings()
    at_launch.drag_schedule_box_height_px = 30
    app.settings = at_launch

    stub = _date_increment_stub(settings, app, label=None, box_height="86")
    SettingsScreen.save_date_increment_settings(stub)

    assert json.loads(settings_file.read_text())["drag_schedule_box_height_px"] == 86
    assert app.settings is not at_launch, (
        "the app is still holding the object from launch, so the Plan screen "
        "reads the old sizes until the app is restarted"
    )
    assert app.settings.drag_schedule_box_height_px == 86, (
        "the saved box height did not reach the app's settings object"
    )


def test_a_refused_write_does_not_hand_the_app_the_unsaved_object(
    settings_file, monkeypatch
):
    """The ordering the appearance section uses, for the same reason.

    Handing the app an object that was not written would show sizes that are
    gone on the next launch.
    """
    original = _refuse_the_write(monkeypatch, settings_file)
    settings = AppSettings.load()
    app = type("_App", (), {})()
    at_launch = AppSettings()
    at_launch.drag_schedule_box_height_px = 30
    app.settings = at_launch

    stub = _date_increment_stub(settings, app, label=None, box_height="86")
    SettingsScreen.save_date_increment_settings(stub)

    assert settings_file.read_text() == original, "the refused write landed"
    assert app.settings is at_launch, (
        "a refused write handed the app an object the file does not hold"
    )
    assert app.settings.drag_schedule_box_height_px == 30


def test_a_refused_write_after_a_saved_one_does_not_reach_the_app(
    settings_file, monkeypatch
):
    """The leak the first fix for PB-M5.7 opened, found by a cold sweep.

    Handing ``self.settings`` over made the app's object this screen's object.
    From the next Save on, the guard that stops a refused write being reported
    as saved stopped nothing: the handler mutates ``self.settings`` before the
    guard and does not put it back, so the running app showed 200px boxes
    under a red "could not write the settings file".

    One ``settings`` object across both saves, as a real screen has -- it is
    loaded once in ``__init__`` and never reloaded.
    """
    settings = AppSettings()
    app = type("_App", (), {})()
    app.settings = AppSettings()

    SettingsScreen.save_date_increment_settings(
        _date_increment_stub(settings, app, label=None, box_height="86")
    )
    assert app.settings.drag_schedule_box_height_px == 86

    original = _refuse_the_write(monkeypatch, settings_file)
    SettingsScreen.save_date_increment_settings(
        _date_increment_stub(settings, app, label=None, box_height="200")
    )

    assert settings_file.read_text() == original, "the refused write landed"
    assert app.settings.drag_schedule_box_height_px == 86, (
        "a refused write reached the running app, because the app was holding "
        "the screen's own settings object"
    )


# ================= PD-M5.4 — extending a day is not confirming it =======


class _App:
    def __init__(self, settings):
        self.settings = settings


def test_pdm54_extending_the_day_is_not_confirming_it(settings_file, tmp_path):
    """PD-M5.4 — the flag that gates the irreversible adoption is left alone.

    ``plan_day_shape_unconfirmed`` says the four day times were invented rather
    than chosen, and it is what stops the Plan screen's one irreversible write
    running against a day nobody picked. Only the Day Settings dialog clears
    it. A drop that lengthens the day writes one of those four values -- which
    is exactly the shape of change that *looks* like confirmation and is not:
    the user said where one item goes, not that 08:00, 12:00, 60 and 17:00 are
    their day.
    """
    import customtkinter as ctk

    settings_file.write_text("{ not json")
    settings = AppSettings.load()
    assert settings.plan_day_shape_unconfirmed is True, (
        "precondition: an unreadable file means the day's shape is a guess"
    )

    manager = DatabaseManager(str(tmp_path / "plan.db"))
    root = ctk.CTk()
    try:
        panel = PlanScreen(root, manager, _App(settings))
        panel.selected_date = "2026-11-05"
        panel.refresh()
        item = ActionItem(who="me", title="Early start", start_date="2026-11-05")
        manager.create_action_item(item)

        panel.extend_day_for(item, DAY_EXTEND_EARLIER)

        assert settings.plan_day_start == "07:30", (
            "precondition for the real assertion: the extension has to have "
            f"happened, and the day start is {settings.plan_day_start}"
        )
        assert settings.plan_day_shape_unconfirmed is True, (
            "lengthening the day was taken as the user confirming its shape"
        )
        assert json.loads(settings_file.read_text())[
            "plan_day_shape_unconfirmed"
        ] is True, "the file now says a guessed day shape is the user's"
    finally:
        root.destroy()
        manager.close()


def test_pdm54_an_already_confirmed_day_stays_confirmed(settings_file, tmp_path):
    """The other direction: extending must not re-raise the flag either.

    Without this, the test above would pass for an implementation that wrote
    ``True`` unconditionally -- which would put every user who has opened Day
    Settings back behind the warning and stop their old blocks being placed.
    """
    import customtkinter as ctk

    _write(
        settings_file,
        plan_day_start="08:00",
        plan_lunch_start="12:00",
        plan_lunch_minutes=60,
        plan_day_end="17:00",
        plan_day_shape_unconfirmed=False,
    )
    settings = AppSettings.load()
    assert settings.plan_day_shape_unconfirmed is False, "precondition"

    manager = DatabaseManager(str(tmp_path / "plan.db"))
    root = ctk.CTk()
    try:
        panel = PlanScreen(root, manager, _App(settings))
        panel.selected_date = "2026-11-05"
        panel.refresh()
        item = ActionItem(who="me", title="Late finish", start_date="2026-11-05")
        manager.create_action_item(item)

        panel.extend_day_for(item, DAY_EXTEND_LATER)

        assert settings.plan_day_end == "17:30", settings.plan_day_end
        assert settings.plan_day_shape_unconfirmed is False, (
            "extending the day put a confirmed day back behind the warning"
        )
    finally:
        root.destroy()
        manager.close()
