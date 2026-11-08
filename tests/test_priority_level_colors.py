"""PLC-M1 to PLC-M4 — the three priority levels, their colours, and the row tint.

Purpose: hold the level rule, the settings that colour it, the Settings tab
         that edits them, and the fill the five list screens draw.
Spec:    docs/implementation_plan_2026-11-08_priority_level_colours.md
Tests:   this file

Before this batch the rule ``item.importance == 20 or item.urgency == 20`` was
written out by hand in five screens, had no "high" tier, was not configurable,
and had no test of any kind. Everything here is therefore new coverage rather
than a restatement of what was already guarded.

No test in this file takes the ``mapped_windows`` fixture or builds a Tk root:
the level rule, the effective colour, the Settings tab's content and its save
path are all plain functions over plain objects, and the five screens are
checked structurally. ``test_ci_contract.py``'s mapped-window count is
therefore untouched.
"""

from __future__ import annotations

import ast
import inspect
import logging
import textwrap
from dataclasses import fields
from tkinter import colorchooser
from types import SimpleNamespace
from unittest import mock

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.color_contrast import (
    contrast_ratio,
    normalize_hex_color,
    pick_text_color,
)
from src.getmoredone.models import ActionItem, PriorityFactors, Status
from src.getmoredone.priority_levels import (
    LEVEL_ANY_CRITICAL,
    LEVEL_ANY_HIGH,
    LEVEL_KEYS,
    LEVEL_LABELS,
    LEVEL_NO_HIGH_OR_CRITICAL,
    NO_FILL,
    SETTINGS_FIELD_PREFIX,
    SOURCE_COMPLETED,
    SOURCE_LEVEL,
    SOURCE_NONE,
    SOURCE_SEGMENT,
    RowFill,
    level_color,
    priority_color_rows,
    priority_level,
    priority_level_for_item,
    row_control_kwargs,
    row_fill,
    settings_field_name,
)
from src.getmoredone.screens import (
    all_items,
    completed,
    hierarchical,
    today,
    upcoming,
    week_actions,
)
from src.getmoredone.screens.settings import SettingsScreen
from src.getmoredone.screens.settings_priority_colors import (
    SettingsPriorityColorsMixin,
)
from src.getmoredone.theme import priority_level_fill_colors
from tests.source_asserts import (
    assigns_attribute_of,
    assigns_self_attribute,
    call_string_args,
    calls_attribute,
    count_calls,
    local_assignments,
)

# WCAG AA for normal text. A level fill sits behind every label in the row, so
# it is held to the text bar and not the 3:1 non-text one.
MIN_TEXT_CONTRAST = 4.5

CRITICAL = PriorityFactors.IMPORTANCE["Critical"]
HIGH = PriorityFactors.IMPORTANCE["High"]
MEDIUM = PriorityFactors.IMPORTANCE["Medium"]
LOW = PriorityFactors.IMPORTANCE["Low"]

PALETTE = {"success_tint": "#E8F5EE", "row_text": "#DCE4EE"}

# The five row builders that decide a list row's fill. All_items and Completed
# build their rows inside ``refresh``; the other three have a method.
ROW_BUILDERS = (
    ("today.create_item_row", today.TodayScreen.create_item_row),
    ("upcoming.create_item_row", upcoming.UpcomingScreen.create_item_row),
    ("hierarchical.create_item_row", hierarchical.HierarchicalScreen.create_item_row),
    ("all_items.refresh", all_items.AllItemsScreen.refresh),
    ("completed.refresh", completed.CompletedScreen.refresh),
)


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    """A settings path inside tmp_path, restored by monkeypatch on exit.

    The default path is the user's real settings file, and ``save`` writes it.
    """
    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        AppSettings, "get_settings_path", classmethod(lambda cls: path)
    )
    return path


@pytest.fixture
def restore_appearance():
    """Put the appearance mode back, whatever the test did to it."""
    was_system = ctk.AppearanceModeTracker.appearance_mode_set_by == "system"
    original = ctk.get_appearance_mode()
    try:
        yield
    finally:
        ctk.set_appearance_mode("system" if was_system else original)


def _item(importance=None, urgency=None, **kwargs):
    return ActionItem(who="Self", title="x", importance=importance, urgency=urgency, **kwargs)


# =========================================================================
# PLC-M1 — the three levels
# =========================================================================

def test_plcm11_critical_in_either_factor_is_any_critical():
    """PLC-M1.1 — either factor, both, or one with the other missing."""
    assert priority_level(CRITICAL, LOW) == LEVEL_ANY_CRITICAL
    assert priority_level(LOW, CRITICAL) == LEVEL_ANY_CRITICAL
    assert priority_level(CRITICAL, CRITICAL) == LEVEL_ANY_CRITICAL
    # A missing factor is not an excuse: this is the ``or`` the five screens
    # have always used, and the opposite of ``priority_band``'s "unscored".
    assert priority_level(None, CRITICAL) == LEVEL_ANY_CRITICAL
    assert priority_level(CRITICAL, None) == LEVEL_ANY_CRITICAL


def test_plcm12_high_without_critical_is_any_high():
    """PLC-M1.2 — High in either factor, and no Critical anywhere."""
    assert priority_level(HIGH, LOW) == LEVEL_ANY_HIGH
    assert priority_level(LOW, HIGH) == LEVEL_ANY_HIGH
    assert priority_level(HIGH, HIGH) == LEVEL_ANY_HIGH
    assert priority_level(None, HIGH) == LEVEL_ANY_HIGH
    # One Critical anywhere outranks a High: this is the "but no Critical"
    # half of the level's name, and it is the whole difference between the
    # top two levels.
    assert priority_level(HIGH, CRITICAL) == LEVEL_ANY_CRITICAL


def test_plcm13_medium_low_and_unset_are_no_high_or_critical():
    """PLC-M1.3 — everything below High, including nothing at all."""
    for importance, urgency in [
        (MEDIUM, MEDIUM),
        (MEDIUM, LOW),
        (LOW, LOW),
        (None, None),
        (0, 0),
        (None, MEDIUM),
    ]:
        assert priority_level(importance, urgency) == LEVEL_NO_HIGH_OR_CRITICAL, (
            importance,
            urgency,
        )


def test_plcm14_a_big_score_is_not_a_critical_level():
    """PLC-M1.4 (P7) — a large priority *score* is not a critical *level*.

    The adversarial case for this module: an item that looks urgent by every
    aggregate measure and is not, by the only measure a level uses. Medium
    importance and urgency with XL size and XL value scores
    5 x 5 x 16 x 16 = 6400, which ``priority_band`` calls ``critical`` — the
    top band, above its 2000 threshold. Its *level* is "no high or critical",
    because the user marked neither factor High.

    Conflating the two would paint this row as though the user had called it
    critical when they had not, which is the failure the two separate name
    sets exist to prevent.
    """
    from src.getmoredone.time_block_layout import priority_band

    item = _item(
        importance=MEDIUM,
        urgency=MEDIUM,
        size=PriorityFactors.SIZE["XL"],
        value=PriorityFactors.VALUE["XL"],
    )
    score = item.calculate_priority_score()
    assert score == 6400
    assert priority_band(score) == "critical"
    assert priority_level_for_item(item) == LEVEL_NO_HIGH_OR_CRITICAL


@pytest.mark.parametrize("name,number", sorted(PriorityFactors.IMPORTANCE.items()))
def test_plcm15_the_boundary_follows_priority_factors(name, number):
    """PLC-M1.5 — the levels are read off ``PriorityFactors``, not off 20 and 10.

    Parametrised over the real scale so that renumbering it moves the
    boundary with it instead of leaving a literal behind (rule 8).
    """
    expected = {
        "Critical": LEVEL_ANY_CRITICAL,
        "High": LEVEL_ANY_HIGH,
        "Medium": LEVEL_NO_HIGH_OR_CRITICAL,
        "Low": LEVEL_NO_HIGH_OR_CRITICAL,
    }[name]
    assert priority_level(number, None) == expected
    assert priority_level(None, number) == expected


def test_plcm15_a_value_off_the_scale_lands_in_the_nearest_level_down():
    """PLC-M1.5 — ``>=``, so a hand-edited database is not under-reported.

    A value between two steps, or above the top one, belongs to the level it
    has passed. ``==`` would drop both to "no high or critical", which is the
    opposite of what the number says.
    """
    assert priority_level(CRITICAL + 5, None) == LEVEL_ANY_CRITICAL
    assert priority_level(HIGH + 1, None) == LEVEL_ANY_HIGH
    assert priority_level(HIGH - 1, None) == LEVEL_NO_HIGH_OR_CRITICAL


def test_plcm16_the_three_levels_are_labelled_as_asked():
    """PLC-M1.6 — three levels, in the user's own words."""
    assert LEVEL_KEYS == (
        LEVEL_ANY_CRITICAL,
        LEVEL_ANY_HIGH,
        LEVEL_NO_HIGH_OR_CRITICAL,
    )
    assert [LEVEL_LABELS[level] for level in LEVEL_KEYS] == [
        "Any Critical",
        "Any High, but no Critical",
        "No high or critical",
    ]


def test_plcm16_a_non_numeric_factor_does_not_raise():
    """PLC-M1 — five screens render whatever the database holds."""
    assert priority_level("critical", None) == LEVEL_NO_HIGH_OR_CRITICAL
    assert priority_level(object(), None) == LEVEL_NO_HIGH_OR_CRITICAL


# =========================================================================
# PLC-M2 — the settings
# =========================================================================

def test_plcm21_every_level_has_a_settings_field():
    """PLC-M2.1 — the mapping holds in both directions, by exact set.

    An *undeclared* field is the failure this guards: ``save`` writes declared
    dataclass fields only, so a colour stored on an undeclared name is used
    for the session and gone at the next launch with nothing said.
    """
    declared = {
        f.name for f in fields(AppSettings) if f.name.startswith(SETTINGS_FIELD_PREFIX)
    }
    assert declared == {settings_field_name(level) for level in LEVEL_KEYS}


def test_plcm22_settings_defaults_match_the_theme_table():
    """PLC-M2.2 — the dataclass literals cannot drift from theme.py.

    A dataclass default has to be a literal, so it cannot read the theme
    table; this is what keeps the unavoidable copy honest.
    """
    defaults = AppSettings()
    assert priority_level_fill_colors() == {
        level: getattr(defaults, settings_field_name(level)) for level in LEVEL_KEYS
    }


def test_plcm23_critical_defaults_to_green():
    """PLC-M2.3 — the default the user asked for, by name and by value."""
    defaults = priority_level_fill_colors()
    assert defaults[LEVEL_ANY_CRITICAL] == "#DCFCE7"
    assert defaults[LEVEL_ANY_HIGH] == "#FEF3C7"
    assert defaults[LEVEL_NO_HIGH_OR_CRITICAL] == NO_FILL

    # Green, not the pale red these rows used to take. Asserted as a property
    # and not only as a hex, so a later edit to a different green still
    # passes and an edit back to a red does not.
    red, green, blue = (
        int(defaults[LEVEL_ANY_CRITICAL][i : i + 2], 16) for i in (1, 3, 5)
    )
    assert green > red and green > blue


def test_plcm23_the_default_is_not_the_old_critical_tint(restore_appearance):
    """PLC-M2.3 — the change actually changed something, in both modes."""
    from src.getmoredone.theme import semantic_colors

    for mode in ("Light", "Dark"):
        ctk.set_appearance_mode(mode)
        assert (
            priority_level_fill_colors()[LEVEL_ANY_CRITICAL]
            != semantic_colors()["critical_tint"]
        )


def test_plcm24_level_colours_round_trip(settings_file):
    """PLC-M2.4 — saved, reloaded, and still the user's three values."""
    settings = AppSettings()
    settings.priority_level_color_any_critical = "#112233"
    settings.priority_level_color_any_high = "#445566"
    settings.priority_level_color_no_high_or_critical = "#778899"
    assert settings.save()

    reloaded = AppSettings.load()
    assert reloaded.priority_level_color_any_critical == "#112233"
    assert reloaded.priority_level_color_any_high == "#445566"
    assert reloaded.priority_level_color_no_high_or_critical == "#778899"
    assert level_color(reloaded, LEVEL_ANY_CRITICAL) == "#112233"


@pytest.mark.parametrize(
    "stored",
    [
        "red",
        "#GGGGGG",
        "#12345",
        "rgb(1,2,3)",
        None,
        17,
        ["#FFFFFF"],
        # Shapes the first version of this guard admitted, because it validated
        # with ``int(text[1:], 16)``: Python accepts a 0x prefix, a sign,
        # PEP-515 underscores, inner whitespace and non-ASCII decimal digits,
        # and every one of these reached Tk as a seven-character "#......"
        # string that Tk then raised on, inside a row build.
        "0x1234",
        "#0X1234",
        "+12345",
        "#+12345",
        "# 12345",
        "#-12345",
        "#1_2345",
        "#\uff11\uff12\uff13\uff14\uff15\uff16",
    ],
)
def test_plcm25_a_malformed_stored_colour_falls_back_to_the_default(stored, caplog):
    """PLC-M2.5 (P8) — a settings file from an earlier run cannot crash a row.

    Tk raises on a colour it does not recognise, and the raise would happen
    inside a row build, taking the whole list screen down. The bad value is
    logged rather than swallowed, because silently showing the default is how
    a user loses a colour without being told (rule 6, surface never drop).
    """
    settings = SimpleNamespace(**{
        settings_field_name(LEVEL_ANY_CRITICAL): stored,
    })
    with caplog.at_level(logging.WARNING):
        assert level_color(settings, LEVEL_ANY_CRITICAL) == "#DCFCE7"
    assert "priority level" in caplog.text


def test_plcm26_no_fill_survives_a_reload(settings_file):
    """PLC-M2.6 — a level the user cleared stays cleared.

    Blank is a decision, not a missing value. Replacing it with the default
    would make a level impossible to turn off: clear it, reload, and the
    colour is back.
    """
    settings = AppSettings()
    settings.priority_level_color_any_critical = ""
    assert settings.save()

    reloaded = AppSettings.load()
    assert level_color(reloaded, LEVEL_ANY_CRITICAL) == NO_FILL
    # Whitespace is the same decision typed less carefully.
    assert level_color(
        SimpleNamespace(**{settings_field_name(LEVEL_ANY_HIGH): "   "}),
        LEVEL_ANY_HIGH,
    ) == NO_FILL


def test_plcm26_a_usable_value_is_normalised_on_the_way_out():
    """PLC-M2 — stored lowercase or bare hex still reaches Tk as #RRGGBB."""
    settings = SimpleNamespace(**{
        settings_field_name(LEVEL_ANY_CRITICAL): "dcfce7",
        settings_field_name(LEVEL_ANY_HIGH): "#abc",
    })
    assert level_color(settings, LEVEL_ANY_CRITICAL) == "#DCFCE7"
    assert level_color(settings, LEVEL_ANY_HIGH) == "#AABBCC"


# =========================================================================
# PLC-M3 — the Settings tab
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


class _StubSettingsScreen(SettingsPriorityColorsMixin):
    """Enough of ``SettingsScreen`` for the mixin's handlers, without widgets.

    The same shape ``test_settings_save_refusal.py`` uses: the real mixin
    methods run, against stand-ins for the Tk variables and the three
    ``SettingsScreen`` helpers they call, so the save path is tested without
    building a CustomTkinter screen. It inherits the mixin rather than
    reimplementing anything, so ``_refresh_priority_swatches`` under test is
    the real one.
    """

    def __init__(self, settings, values, write_succeeds=True):
        self.settings = settings
        self.priority_level_color_vars = {
            level: _Var(values.get(level, "")) for level in LEVEL_KEYS
        }
        self.priority_level_swatches = {level: _Swatch() for level in LEVEL_KEYS}
        self.priority_colors_status_label = SimpleNamespace(text="", level=None)
        self.app = SimpleNamespace(settings=None)
        self._write_succeeds = write_succeeds
        self.handed_to_app = 0

    # -- the bits of SettingsScreen the mixin leans on
    def _set_status(self, label, text, level="success"):
        label.text = text
        label.level = level

    def _write_settings(self, label):
        if self._write_succeeds:
            return True
        self._set_status(label, "Could not write the settings file", "error")
        return False

    def _hand_settings_to_app(self):
        self.handed_to_app += 1
        self.app.settings = self.settings

    @property
    def status(self):
        return (
            self.priority_colors_status_label.text,
            self.priority_colors_status_label.level,
        )


def test_plcm31_one_row_per_level_in_order():
    """PLC-M3.1 — the tab shows every level, in order, with its own colour."""
    rows = priority_color_rows(AppSettings())
    assert [level for level, _, _ in rows] == list(LEVEL_KEYS)
    assert [label for _, label, _ in rows] == [LEVEL_LABELS[k] for k in LEVEL_KEYS]
    assert [colour for _, _, colour in rows] == [
        priority_level_fill_colors()[k] for k in LEVEL_KEYS
    ]


def test_plcm32_saved_colours_reach_the_running_app():
    """PLC-M3.2 — the three fields are written and published to the app.

    The third level starts from a *non-empty* stored colour, so clearing it is
    a real write. Its dataclass default is already ``""``, so asserting
    ``== NO_FILL`` against a fresh ``AppSettings`` held whether or not the
    handler wrote anything, and the one action that removes a colour was
    unproven.
    """
    settings = AppSettings()
    settings.priority_level_color_no_high_or_critical = "#654321"
    settings.priority_level_color_any_critical = "#111111"
    stub = _StubSettingsScreen(
        settings,
        {
            LEVEL_ANY_CRITICAL: "#0A0B0C",
            LEVEL_ANY_HIGH: "0d0e0f",
            LEVEL_NO_HIGH_OR_CRITICAL: "",
        },
    )
    SettingsPriorityColorsMixin.save_priority_level_colors(stub)

    assert settings.priority_level_color_any_critical == "#0A0B0C"
    assert settings.priority_level_color_any_high == "#0D0E0F"
    assert settings.priority_level_color_no_high_or_critical == NO_FILL
    assert stub.handed_to_app == 1
    assert stub.status == ("✓ Saved priority level colours", "success")
    # The normalised value goes back into the field, so what is shown is what
    # was stored.
    assert stub.priority_level_color_vars[LEVEL_ANY_HIGH].get() == "#0D0E0F"
    assert stub.priority_level_swatches[LEVEL_ANY_CRITICAL].fg_color == "#0A0B0C"
    assert stub.priority_level_swatches[LEVEL_NO_HIGH_OR_CRITICAL].fg_color == (
        "transparent"
    )


def test_plcm33_a_refused_write_is_not_reported_as_saved():
    """PLC-M3.3 — a settings file that would not be written is not published.

    The ``_write_settings`` contract: ``AppSettings.save`` can decline, and a
    refused write must not reach ``app.settings`` or be reported as a save.
    """
    stub = _StubSettingsScreen(
        AppSettings(), {LEVEL_ANY_CRITICAL: "#0A0B0C"}, write_succeeds=False
    )
    SettingsPriorityColorsMixin.save_priority_level_colors(stub)

    assert stub.handed_to_app == 0
    assert stub.app.settings is None
    assert stub.status[1] == "error"
    assert "Saved" not in stub.status[0]


def test_plcm34_entry_values_are_normalised_and_bad_ones_refused():
    """PLC-M3.4 — a typo is refused by name, and nothing at all is written.

    Checked before anything is written, so a bad third field cannot leave the
    first two saved and the rest not. And refused rather than silently
    replaced: ``save_date_increment_settings`` rewrites a bad colour to
    ``#FFFFFF``, and a user who meant what they typed is never told.
    """
    settings = AppSettings()
    before = settings.priority_level_color_any_critical
    stub = _StubSettingsScreen(
        settings,
        {
            LEVEL_ANY_CRITICAL: "#123456",
            LEVEL_ANY_HIGH: "#FEF3C7",
            LEVEL_NO_HIGH_OR_CRITICAL: "chartreuse",
        },
    )
    SettingsPriorityColorsMixin.save_priority_level_colors(stub)

    assert stub.status[1] == "error"
    assert LEVEL_LABELS[LEVEL_NO_HIGH_OR_CRITICAL] in stub.status[0]
    assert "chartreuse" in stub.status[0]
    # Nothing written, not even the two good values before the bad one.
    assert settings.priority_level_color_any_critical == before
    assert stub.handed_to_app == 0


def test_plcm35_restore_defaults_writes_the_theme_table():
    """PLC-M3.5 — the defaults come back into the fields, and are not saved.

    Fields only: a button called "restore" that wrote three values to disk
    with no confirmation would be an undo nobody can undo.
    """
    settings = AppSettings()
    settings.priority_level_color_any_critical = "#000000"
    stub = _StubSettingsScreen(settings, {LEVEL_ANY_CRITICAL: "#000000"})

    SettingsPriorityColorsMixin.restore_priority_level_colors(stub)

    defaults = priority_level_fill_colors()
    assert {
        level: var.get() for level, var in stub.priority_level_color_vars.items()
    } == defaults
    assert stub.priority_level_swatches[LEVEL_ANY_CRITICAL].fg_color == (
        defaults[LEVEL_ANY_CRITICAL]
    )
    # Not written, and the status line says so.
    assert settings.priority_level_color_any_critical == "#000000"
    assert stub.handed_to_app == 0
    assert "Apply / Save" in stub.status[0]


def test_plcm36_create_tabs_adds_the_priority_colours_tab():
    """PLC-M3.6 — the section is reachable, and reachable by that name.

    A source check because proving it behaviourally needs a built
    CustomTkinter screen; parsed rather than greped, so a comment naming the
    method or the tab does not satisfy it. (It used to end in a bare
    ``"Priority Colours" in inspect.getsource(...)``, which the comment above
    the ``add`` call satisfied on its own -- exactly the shape
    ``source_asserts`` exists to replace.)
    """
    assert calls_attribute(SettingsScreen.create_tabs, "self",
                           "create_priority_colors_section")
    assert count_calls(SettingsScreen.create_priority_colors_section,
                       "priority_color_rows") == 1
    # The tab names as the tabview is actually given them. A substring check
    # over the source passed on the comment above the call ("# Tab 3: Priority
    # Colours..."), so renaming the tab -- or dropping the ``add`` entirely --
    # left it green. The whole set is asserted, in order, so this also pins
    # which tabs the Settings screen offers.
    assert call_string_args(SettingsScreen.create_tabs, "self.tabview", "add") == [
        "Database Management",
        "Appearance",
        "Priority Colours",
        "Future Dates",
        "Timer & Audio",
        "Organizational Factors",
        "Email Import",
    ]


# =========================================================================
# PLC-M4 — the fill the five screens draw
# =========================================================================

def test_plcm41_a_row_takes_its_level_colour():
    """PLC-M4.1 — each level draws its own colour, from settings."""
    settings = AppSettings()
    critical = row_fill(
        settings, PALETTE, item=_item(CRITICAL, LOW), use_completed_tint=False
    )
    high = row_fill(
        settings, PALETTE, item=_item(HIGH, LOW), use_completed_tint=False
    )
    assert critical.fill == settings.priority_level_color_any_critical
    assert critical.source == SOURCE_LEVEL
    assert high.fill == settings.priority_level_color_any_high
    assert high.source == SOURCE_LEVEL
    assert critical.fill != high.fill

    # And it follows the setting, not a constant.
    settings.priority_level_color_any_critical = "#010203"
    assert row_fill(
        settings, PALETTE, item=_item(CRITICAL, LOW), use_completed_tint=False
    ).fill == "#010203"


def test_plcm42_segment_and_completed_still_win():
    """PLC-M4.2 — precedence is unchanged: segment, then completed, then level."""
    settings = AppSettings()
    item = _item(CRITICAL, CRITICAL)

    segment = row_fill(
        settings, PALETTE, item=item, use_completed_tint=False,
        segment_color="#445566",
    )
    assert segment.fill == "#445566"
    assert segment.source == SOURCE_SEGMENT

    done = row_fill(settings, PALETTE, item=item, use_completed_tint=True)
    assert done.fill == PALETTE["success_tint"]
    assert done.source == SOURCE_COMPLETED

    # A segment colour outranks the completed tint too, as it always has.
    both = row_fill(
        settings, PALETTE, item=item, use_completed_tint=True,
        segment_color="#445566",
    )
    assert both.source == SOURCE_SEGMENT


def test_plcm43_an_unset_level_means_no_fill():
    """PLC-M4.3 — no fill is ``None``, which is what ``fg_color`` wants.

    Not ``""``: Tk rejects the empty string as a colour, so returning it would
    turn "no fill" into a raised ``TclError`` in the middle of a row build.
    """
    settings = AppSettings()
    plain = row_fill(
        settings, PALETTE, item=_item(MEDIUM, MEDIUM), use_completed_tint=False
    )
    assert plain.fill is None
    assert plain.source == SOURCE_NONE

    settings.priority_level_color_any_critical = ""
    cleared = row_fill(
        settings, PALETTE, item=_item(CRITICAL, LOW), use_completed_tint=False
    )
    assert cleared.fill is None
    assert cleared.source == SOURCE_NONE


def test_plcm44_level_fill_text_clears_the_contrast_bar():
    """PLC-M4.4 — a level fill brings its own, legible, text colour.

    This is what a single hex per level costs and how it is paid for: a pale
    green fill in the dark theme would otherwise keep the theme's near-white
    ``row_text``. Asserted over colours across the whole range, not only the
    two defaults, because the user can pick anything.
    """
    settings = AppSettings()
    for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):
        settings.priority_level_color_any_critical = colour
        fill = row_fill(
            settings, PALETTE, item=_item(CRITICAL, LOW), use_completed_tint=False
        )
        assert fill.text_color is not None
        ratio = contrast_ratio(fill.fill, fill.text_color)
        assert ratio >= MIN_TEXT_CONTRAST, f"{colour} -> {fill.text_color} is {ratio:.2f}"


def test_plcm45_a_non_priority_fill_leaves_row_text_alone():
    """PLC-M4.5 — segment, completed and no fill keep the screen's own text.

    Their contrast is a real problem and a pre-existing one (BACKLOG); fixing
    it here would be a silent sweep of behaviour nobody asked about.
    """
    settings = AppSettings()
    item = _item(CRITICAL, CRITICAL)
    for fill in (
        row_fill(settings, PALETTE, item=item, use_completed_tint=False,
                 segment_color="#445566"),
        row_fill(settings, PALETTE, item=item, use_completed_tint=True),
        row_fill(settings, PALETTE, item=_item(LOW, LOW), use_completed_tint=False),
    ):
        assert fill.text_color is None, fill


def test_plcm46_default_level_colours_are_legible_in_both_themes(restore_appearance):
    """PLC-M4.6 — the shipped colours work in light and dark, being one table.

    The claim being guarded is the design choice in
    ``priority_level_fill_colors``: one value per level, no mode branch. A
    mode branch added later would make a saved setting mean two different
    things, so the table is asserted *identical* across modes as well as
    legible in each.
    """
    seen = []
    for mode in ("Light", "Dark"):
        ctk.set_appearance_mode(mode)
        table = priority_level_fill_colors()
        seen.append(table)
        for level, colour in table.items():
            if colour == NO_FILL:
                continue
            text = normalize_hex_color(colour)
            assert text is not None, (level, colour)
            settings = AppSettings()
            setattr(settings, settings_field_name(level), colour)
            fill = row_fill(
                settings,
                PALETTE,
                item=_item(CRITICAL if level == LEVEL_ANY_CRITICAL else HIGH, LOW),
                use_completed_tint=False,
            )
            ratio = contrast_ratio(fill.fill, fill.text_color)
            assert ratio >= MIN_TEXT_CONTRAST, f"{mode} {level}: {ratio:.2f}"
    assert seen[0] == seen[1]


def test_plcm47_no_screen_still_inlines_the_critical_rule():
    """PLC-M4.7 — each row builder assigns ``bg_color`` once, from ``fill.fill``.

    The shape is the contract. Before this batch each of the five decided a
    fill for itself with its own ``if/elif`` chain on ``importance == 20``;
    adding a second tier by hand would have made ten copies. Asserted as an
    exact count of one, never a floor: a floor would pass on a screen that had
    grown its branches back.

    Deliberately *not* a ban on comparing ``importance`` to a constant —
    ``today.py`` and the other four still do that for the red ``P:`` chip,
    which the user asked to leave alone.
    """
    for name, builder in ROW_BUILDERS:
        values = local_assignments(builder, "bg_color")
        assert len(values) == 1, f"{name} assigns bg_color {len(values)} times"
        assert assigns_attribute_of(values[0], "fill", "fill"), (
            f"{name} does not take its fill from row_fill's result"
        )


def test_plcm48_every_list_screen_row_builder_calls_the_helper():
    """PLC-M4.8 — exactly one ``row_fill`` call in each of the five, and five total.

    The total is asserted as well as the per-screen count, so a screen cannot
    be dropped from ``ROW_BUILDERS`` and the test still pass.
    """
    counts = {name: count_calls(builder, "row_fill") for name, builder in ROW_BUILDERS}
    assert counts == {name: 1 for name, _ in ROW_BUILDERS}
    assert sum(counts.values()) == 5
    assert len(ROW_BUILDERS) == 5


def _settings_reload_statement_index(func) -> int:
    """Which top-level statement of ``func`` is ``self.settings = AppSettings.load(...)``.

    Both halves, in one statement: ``assigns_self_attribute`` looks only at
    assignment *targets* and ``calls_attribute`` only at calls, so asserting
    them separately accepted a ``refresh`` that wrote ``self.settings`` from a
    cache at the top and called ``AppSettings.load()`` into a local further
    down — the very hole the pair was meant to close.

    Raises if there is no such statement, so it cannot quietly report a
    passing position for a function that never reloads.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(func))).body[0]
    for index, statement in enumerate(tree.body):
        if not isinstance(statement, ast.Assign):
            continue
        targets_self_settings = any(
            isinstance(target, ast.Attribute)
            and target.attr == "settings"
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            for target in statement.targets
        )
        value = statement.value
        loads_settings = (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "load"
            and isinstance(value.func.value, ast.Name)
            and value.func.value.id == "AppSettings"
        )
        if targets_self_settings and loads_settings:
            return index
    raise AssertionError(
        f"{func.__qualname__} has no self.settings = AppSettings.load() statement"
    )


def test_plcm48_the_five_screens_reload_settings_before_building_rows():
    """PLC-M4 — a colour saved in Settings shows without a relaunch.

    Each list screen holds its own ``AppSettings``; without a reload in
    ``refresh`` a saved colour would not appear until the app was restarted,
    which would read as the setting not working.
    """
    refreshers = (
        today.TodayScreen.refresh,
        upcoming.UpcomingScreen.refresh,
        all_items.AllItemsScreen.refresh,
        hierarchical.HierarchicalScreen.refresh,
        completed.CompletedScreen.refresh,
        # WeekTacticActionsPanel is deliberately NOT here: it inherits
        # TodayScreen.refresh rather than defining one, so this entry would be
        # the same function object as Today's and would read as a sixth check
        # while testing Today twice. Its inheritance is asserted instead, in
        # test_plc_cold_the_week_panel_inherits_todays_rows_and_reload.
    )
    for refresher in refreshers:
        name = refresher.__qualname__
        # One statement that both writes ``self.settings`` AND reads it from
        # ``AppSettings.load``, near the top, before the rows are built.
        # ``today.py`` and ``upcoming.py`` both already contain a
        # ``settings = AppSettings.load()`` into a *local* elsewhere, and
        # asserting the call and the assignment separately would accept a
        # screen that did the two in different statements — green here, while
        # the saved colour stayed invisible until relaunch. Three because a
        # screen may clear its frame or take a guard first; all five sit at
        # index 1 or 2 today.
        assert _settings_reload_statement_index(refresher) <= 2, name


def test_plcm4_a_completed_row_in_all_items_still_uses_the_status_check():
    """PLC-M4.2 — All Items decides "completed" from the status, as before."""
    settings = AppSettings()
    item = _item(CRITICAL, LOW, status=Status.COMPLETED)
    fill = row_fill(
        settings,
        PALETTE,
        item=item,
        use_completed_tint=item.status == Status.COMPLETED,
    )
    assert fill.source == SOURCE_COMPLETED
    assert fill.fill == PALETTE["success_tint"]


#: Stderr fragments that mean "there is no display here", as opposed to "the
#: section is broken". Deliberately narrow: the reason is in the comment inside
#: ``test_plcm3_the_section_builds_on_real_widgets``. Compared lower-cased,
#: because Tcl capitalises its own two ("Can't find a usable init.tcl") and a
#: marker that can never match is a marker that is not there.
_NO_DISPLAY_MARKERS = (
    "no display name and no $display",
    "couldn't connect to display",
    "can't find a usable init.tcl",
    "can't find a usable tk.tcl",
)


def test_plcm3_the_section_builds_on_real_widgets():
    """PLC-M3 — the section constructs, and its handlers run on real widgets.

    Every other test of this section calls the mixin against stand-ins, so none
    of them would catch a bad ``grid`` call, an option CustomTkinter rejects, or
    a ``fg_color`` Tk will not take — faults that only appear when the user
    opens Settings. This builds it for real.

    In a subprocess with a hard timeout, for the reason
    ``tests/render_list_screen.py`` gives: CustomTkinter does not tolerate
    several CTk roots in one interpreter, and a hanging test is worse than no
    test. The helper withdraws its root, so no window is mapped and the
    ``mapped_windows`` count is untouched.
    """
    import pathlib
    import subprocess
    import sys

    from tests import build_priority_colors_section

    root = pathlib.Path(__file__).resolve().parents[1]
    helper = root / "tests" / "build_priority_colors_section.py"
    result = subprocess.run(
        [sys.executable, str(helper)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(root),
    )
    # Only a *display* failure is a skip. A bare ``TclError`` is what a bad
    # grid call, a rejected widget option, or an fg_color Tk will not take all
    # raise -- which is this test's whole target class, so skipping on it would
    # leave the test unable to fail for the thing it exists to catch.
    if result.returncode != 0 and any(
        marker in result.stderr.lower() for marker in _NO_DISPLAY_MARKERS
    ):
        pytest.skip(f"Tk display unavailable: {result.stderr.strip()[-200:]}")
    assert result.returncode == 0, (
        f"the section failed to build:\n{result.stdout}\n{result.stderr}"
    )

    printed = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    assert printed.get("BUILT") == "ok", result.stdout
    assert printed.get("ENTRIES") == str(len(LEVEL_KEYS)), result.stdout
    assert printed.get("SWATCHES") == str(len(LEVEL_KEYS)), result.stdout

    # The premise of PLC-M2.5, confirmed against the real Tk rather than read
    # off its colour grammar: every shape the old validator admitted is one Tk
    # refuses. If Tk ever accepted one, the guard could be loosened for it --
    # and if this ever fails the other way, the guard is load-bearing for a
    # reason the comments no longer state correctly.
    for raw in build_priority_colors_section.TK_MUST_REJECT:
        verdict = printed.get(f"TKREJECTS:{raw}")
        assert verdict is not None, result.stdout
        # TclError specifically, not merely "something went wrong": that is
        # the exception a row build would have raised, and naming it here is
        # what makes color_contrast.py's comment a checked statement.
        assert verdict == "TclError", (
            f"Tk gave {verdict} for {raw!r}, not TclError, so the comment in "
            f"color_contrast.py explaining why int(x, 16) is too lax "
            f"describes the wrong failure for this value"
        )
        assert normalize_hex_color(raw) is None, raw

    defaults = priority_level_fill_colors()
    for level in LEVEL_KEYS:
        assert printed[f"LABELLED:{level}"] == "True", (
            f"{LEVEL_LABELS[level]} has no label in the built section"
        )
        assert printed[f"VALUE:{level}"] == defaults[level], result.stdout
        # A level set to no fill cannot paint its swatch "" — Tk rejects it.
        expected = defaults[level] or "transparent"
        assert printed[f"SWATCH:{level}"] == expected, result.stdout

    assert printed["RESTORED"] == defaults[LEVEL_KEYS[0]]
    assert "chartreuse" in printed["REFUSAL"]
    assert LEVEL_LABELS[LEVEL_KEYS[0]] in printed["REFUSAL"]


# =========================================================================
# Fixes for the findings of the two cold review passes (2026-11-08)
# =========================================================================

def test_plc_cold_a_bad_colour_cannot_be_saved_from_the_entry():
    """H1 — the shapes the validator used to admit are refused at the entry.

    The save path, not just ``level_color``: these reached ``settings.json``,
    and from then on every row build in five screens and the Settings tab's own
    swatch raised ``TclError``, so the tab the user would fix it from could not
    open. The only way back was hand-editing the file.
    """
    for raw in ("0x1234", "+12345", "# 12345", "#1_2345", "#-12345"):
        settings = AppSettings()
        before = settings.priority_level_color_any_critical
        stub = _StubSettingsScreen(settings, {LEVEL_ANY_CRITICAL: raw})
        SettingsPriorityColorsMixin.save_priority_level_colors(stub)

        assert stub.status[1] == "error", raw
        assert raw in stub.status[0], raw
        assert settings.priority_level_color_any_critical == before, raw
        assert stub.handed_to_app == 0, raw


def test_plcm49_controls_follow_a_level_fill():
    """PLC-M4.9 — a row's controls stay legible on a level fill.

    ``priority_level_fill_colors`` has no dark variant, by design: a colour the
    user picked cannot have one. So in dark mode a Critical row is light while
    the theme's checkbox and grip colours are light too — the checkbox border
    measures about 2.6:1 against the shipped green, under the 3:1 bar for a
    non-text control. PLC-M4.4 fixed the row text and left these behind.
    """
    settings = AppSettings()
    for level in (LEVEL_ANY_CRITICAL, LEVEL_ANY_HIGH):
        colour = priority_level_fill_colors()[level]
        fill = RowFill(colour, pick_text_color(colour), SOURCE_LEVEL)
        kwargs = row_control_kwargs(fill)
        assert set(kwargs) == {"border_color", "fg_color", "checkmark_color"}
        assert kwargs["border_color"] == fill.text_color
        assert kwargs["checkmark_color"] == colour
        # 3:1 is the WCAG bar for a non-text control; this clears it because
        # text_color already clears 4.5:1 against the same fill.
        assert contrast_ratio(kwargs["border_color"], colour) >= 3.0

    # Every other kind of fill leaves the theme's controls alone, so a
    # segment-coloured or completed row looks exactly as it did before.
    assert row_control_kwargs(RowFill("#123456", None, SOURCE_SEGMENT)) == {}
    assert row_control_kwargs(RowFill(PALETTE["success_tint"], None,
                                      SOURCE_COMPLETED)) == {}
    assert row_control_kwargs(RowFill(None, None, SOURCE_NONE)) == {}


def test_plc_cold_the_three_screens_with_row_controls_pass_the_kwargs():
    """PLC-M4.9 — the three row builders that build controls use the helper.

    Today has a grip and a checkbox; Upcoming and All Items have a checkbox.
    Hierarchical and Completed build neither in their row, so they are not in
    this list and the count below says so.
    """
    with_controls = (
        ("today", today.TodayScreen.create_item_row),
        ("upcoming", upcoming.UpcomingScreen.create_item_row),
        ("all_items", all_items.AllItemsScreen.refresh),
    )
    for name, builder in with_controls:
        assert count_calls(builder, "row_control_kwargs") == 1, name
    assert sum(
        count_calls(b, "row_control_kwargs")
        for _, b in with_controls
    ) == 3
    for name, builder in (
        ("hierarchical", hierarchical.HierarchicalScreen.create_item_row),
        ("completed", completed.CompletedScreen.refresh),
    ):
        assert count_calls(builder, "row_control_kwargs") == 0, name


def test_plc_cold_a_refused_write_puts_the_settings_object_back():
    """M4 — a refused save leaves no colour behind on the shared object.

    ``self.settings`` is shared by every Save handler on the Settings screen.
    Mutating it before the ``_write_settings`` guard and not restoring it meant
    the colours the user was told were *not* saved would be written to disk by
    the next successful save from any other section — Appearance, Timer,
    Future Dates.
    """
    settings = AppSettings()
    before = {
        level: getattr(settings, settings_field_name(level))
        for level in LEVEL_KEYS
    }
    stub = _StubSettingsScreen(
        settings,
        {
            LEVEL_ANY_CRITICAL: "#0A0B0C",
            LEVEL_ANY_HIGH: "#0D0E0F",
            LEVEL_NO_HIGH_OR_CRITICAL: "#101112",
        },
        write_succeeds=False,
    )
    SettingsPriorityColorsMixin.save_priority_level_colors(stub)

    assert stub.status[1] == "error"
    for level, value in before.items():
        assert getattr(settings, settings_field_name(level)) == value, level


def test_plc_cold_the_colour_chooser_is_given_a_colour_tk_can_parse():
    """M5 — Pick Colour opens on a usable colour, not on raw entry text.

    ``colorchooser.askcolor(color=...)`` hands its argument to Tk, which raises
    on anything it cannot parse. The exception escaped the button command, so
    a user who typo'd and then reached for the picker got a dead button and no
    message at all.
    """
    seen = {}

    def fake_askcolor(color=None, title=None):
        seen["color"] = color
        return (None, None)

    stub = _StubSettingsScreen(AppSettings(), {LEVEL_ANY_CRITICAL: "qqq"})
    with mock.patch.object(colorchooser, "askcolor", fake_askcolor):
        SettingsPriorityColorsMixin.pick_priority_level_color(
            stub, LEVEL_ANY_CRITICAL
        )
        # Unparseable text falls back to the level's own default.
        assert seen["color"] == priority_level_fill_colors()[LEVEL_ANY_CRITICAL]

        stub.priority_level_color_vars[LEVEL_ANY_CRITICAL].set("#abcdef")
        SettingsPriorityColorsMixin.pick_priority_level_color(
            stub, LEVEL_ANY_CRITICAL
        )
        assert seen["color"] == "#ABCDEF"


def test_plc_cold_the_week_panel_inherits_todays_rows_and_reload():
    """PLC-M4.10 — the sixth surface that draws the fill, and why it is covered.

    ``WeekTacticActionsPanel`` subclasses ``TodayScreen`` and overrides neither
    ``create_item_row`` nor ``refresh``, so it inherits the level fill *and*
    Today's settings reload — which is why it is not in the ``refreshers``
    tuple above: its ``refresh`` is the same function object, and listing it
    would have looked like a sixth check while testing Today twice.

    Asserted rather than assumed, because the inheritance is the only reason
    the panel is covered at all. If it ever defines its own ``refresh``, this
    fails and PLC-M4.10 has to be given a real check.
    """
    panel = week_actions.WeekTacticActionsPanel
    assert issubclass(panel, today.TodayScreen)
    assert "refresh" not in panel.__dict__
    assert "create_item_row" not in panel.__dict__
    assert panel.refresh is today.TodayScreen.refresh
    assert panel.create_item_row is today.TodayScreen.create_item_row
