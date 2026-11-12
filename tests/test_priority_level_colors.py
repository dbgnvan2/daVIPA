"""PLC-M1 to PLC-M4 — the three priority levels, their colours, and the row tint.

Purpose: hold the level rule, the settings that colour it, the Settings tab
         that edits them, and the fill the five list screens draw.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md
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
from pathlib import Path
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
    fill_for_level,
    level_cell_fill,
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

_SRC = Path(__file__).resolve().parents[1] / "src" / "getmoredone"

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

# ``test_plcm41_a_row_takes_its_level_colour`` was here. **Retired on
# 2026-11-11 because the behaviour changed intentionally** (PCC-M1): it
# asserted the row tint the user asked to remove. Replaced by
# ``test_pccm1_a_level_no_longer_fills_a_row``, not rewritten in place, because
# a test whose name contradicts its body is worse than no test.


def test_plcm45_a_non_priority_fill_leaves_row_text_alone():
    """PLC-M4.5 — the completed tint and no fill keep the screen's own text.

    **Narrowed on 2026-11-10 (LRR-M2.1), because the behaviour changed on
    purpose.** This test used to include a segment fill, on the grounds that
    its contrast was a pre-existing problem filed in ``BACKLOG.md`` and that
    fixing it alongside PLC-M4 would have been a silent sweep. ``PLC-A1`` is
    that filing, and this batch closes it: a segment fill now derives its own
    text colour. The segment clause therefore moved to
    ``test_lrrm21_a_segment_fill_carries_its_own_text_colour``, which asserts
    the new behaviour, and ``test_lrrm23_the_completed_tint_keeps_the_themes_text_colour``
    holds the boundary between the two.

    What survives here is the rest of PLC-M4.5, unchanged and still true: a
    fill the *theme* chose keeps the text colour the theme designed for it.
    """
    for fill in (
        row_fill(PALETTE, use_completed_tint=True),
        row_fill(PALETTE, use_completed_tint=False),
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
            fill = fill_for_level(settings, level)
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

    Deliberately *not* a ban on comparing ``importance`` to a constant: this
    one is about where a row's *fill* comes from, and nothing more. When it was
    written the five screens did still compare to a literal, for the red ``P:``
    chip. They no longer do — ``PRI-A1`` closed on 2026-11-10 — and the ban
    that replaced it is
    ``test_lrrm11_no_screen_tests_importance_against_a_literal``, a separate
    check with a separate reason, so that neither claim can be satisfied by
    the other passing.
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
    fill = row_fill(PALETTE, use_completed_tint=item.status == Status.COMPLETED)
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


# ``test_plcm49_controls_follow_a_level_fill`` was here. **Retired on
# 2026-11-11 because the behaviour changed intentionally** (PCC-M1). It built
# its ``RowFill`` by hand, so it would have stayed green while guarding a state
# no row can reach. ``row_control_kwargs`` is unchanged and still covered for
# segment fills by ``test_lrr_cold_a_segment_fill_carries_its_controls_too``.


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


# =========================================================================
# LRR-M2 — a segment fill brings its own text colour (PLC-A1)
# =========================================================================

def test_lrrm21_a_segment_fill_carries_its_own_text_colour():
    """LRR-M2.1 — the segment fill is derived with ``pick_text_color`` too.

    This is the defect ``PLC-A1`` named: the five screens draw the row in a
    VSP segment colour read from ``segment_descriptions.color_hex`` and then
    leave the theme's ``row_text`` on it, which in the dark theme is near
    white. A pale segment colour is the common case, so the row that is
    hardest to read is the one the user coloured on purpose.

    Asserted against ``pick_text_color`` itself rather than a hard-coded pair,
    so the two cannot drift: the whole point is that this is the same
    derivation the level fill already uses (PLC-M4.4).
    """
    settings = AppSettings()
    item = _item(CRITICAL, CRITICAL)
    for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#000000", "#FFFFFF"):
        fill = row_fill(
            PALETTE, use_completed_tint=False, segment_color=colour,
        )
        assert fill.source == SOURCE_SEGMENT
        assert fill.fill == colour
        assert fill.text_color == pick_text_color(colour), colour


def test_lrrm22_the_segment_text_colour_follows_the_fill():
    """LRR-M2.2 — a pale fill gets dark text and a dark fill light text.

    Both directions, so the assertion cannot be satisfied by a constant: a
    ``return RowFill(segment_color, "#000000", ...)`` passes the pale half and
    fails here. Every colour is also held to the 4.5:1 text bar, which is what
    "legible" means for a label drawn on the row.
    """
    settings = AppSettings()
    item = _item(MEDIUM, MEDIUM)

    def text_for(colour):
        return row_fill(
            PALETTE, use_completed_tint=False, segment_color=colour,
        ).text_color

    pale = text_for("#F8FAFC")
    dark = text_for("#0F172A")
    assert pale != dark, f"pale and dark segments both got {pale}"
    assert contrast_ratio("#F8FAFC", pale) >= MIN_TEXT_CONTRAST
    assert contrast_ratio("#0F172A", dark) >= MIN_TEXT_CONTRAST

    # And across the range, not only at the two ends.
    for colour in ("#DCFCE7", "#FEF3C7", "#445566", "#7F7F7F", "#450A0A"):
        ratio = contrast_ratio(colour, text_for(colour))
        assert ratio >= MIN_TEXT_CONTRAST, f"{colour} -> {text_for(colour)} is {ratio:.2f}"


def test_lrrm21_an_unreadable_segment_colour_keeps_the_themes_text():
    """LRR-M2.1 — a segment colour Tk-but-not-hex falls back to ``None``.

    ``pick_text_color`` answers ``#000000`` for anything it cannot parse, and
    black on an unknown background can be worse than the theme's own
    ``row_text`` -- black on ``navy`` is about 1.3:1. So the derivation is
    attempted only on a value ``normalize_hex_color`` accepts, and anything
    else keeps exactly the behaviour it has today.

    **Changed 2026-11-11 (SCV-M4.1), reason (b) -- the behaviour changed
    intentionally.** This test also asserted ``fill.fill == colour``, because
    LRR-M2.1 deliberately passed the raw value through as the fill. SCV-M4.1
    ends that: the raw value is what reaches ``fg_color`` and raises there.
    The fill is now asserted by
    ``test_scvm41_a_malformed_segment_colour_does_not_become_a_fill``, and
    what is left here is M2.1's own claim, the text colour.
    """
    settings = AppSettings()
    item = _item(MEDIUM, MEDIUM)
    for colour in ("navy", "red", "not-a-colour", "#GGHHII"):
        fill = row_fill(
            PALETTE, use_completed_tint=False, segment_color=colour,
        )
        assert fill.source == SOURCE_SEGMENT
        assert fill.text_color is None, f"{colour} -> {fill.text_color}"

    # A three-digit hex is a form the normaliser accepts, so it is derived.
    short = row_fill(
        PALETTE, use_completed_tint=False, segment_color="#ABC",
    )
    assert short.text_color == pick_text_color("#AABBCC")


def test_lrrm23_the_completed_tint_keeps_the_themes_text_colour():
    """LRR-M2.3 — the tint is not widened along with the segment fill.

    ``PLC-A1`` names the segment fill, and only the segment fill. The completed
    tint is a theme token (``success_tint``), chosen in the theme against that
    same theme's ``row_text``; deriving a text colour for it would override a
    pairing that was designed rather than inherited.

    The two are asserted in one place on purpose. Taken apart, "the tint is
    ``None``" also passes on a build where M2.1 was never made and
    "the segment fill is derived" also passes on a build that widened the rule
    to every fill. Together they hold the line in both directions, which is
    what M2.3 is for. ``test_plcm45_a_non_priority_fill_leaves_row_text_alone``
    is the same claim for the tint on its own, kept as PLC-M4.5's own record.
    """
    settings = AppSettings()
    item = _item(CRITICAL, CRITICAL)

    done = row_fill(PALETTE, use_completed_tint=True)
    segment = row_fill(
        PALETTE, use_completed_tint=True, segment_color="#DCFCE7",
    )
    assert done.source == SOURCE_COMPLETED
    assert segment.source == SOURCE_SEGMENT
    assert done.text_color is None
    assert segment.text_color == pick_text_color("#DCFCE7")


# =========================================================================
# LRR-M1 — the `P:` chip asks the authority, not a literal 20 (PRI-A1)
# =========================================================================

_PRIORITY_FACTOR_ATTRS = ("importance", "urgency")


def _factor_literal_comparisons(path):
    """Every ``<...>.importance|urgency <op> <int literal>`` in one module.

    Returns ``(lineno, dump)`` per hit so a failure names the line rather than
    only a count. Parsed, not greped: the string ``"importance == 20"`` in a
    docstring, a ``BACKLOG.md`` quotation pasted into a comment, or a variable
    of that name contributes nothing, which is the whole reason
    ``tests/source_asserts.py`` exists.

    Any comparison operator counts, not only ``==``. A literal threshold on a
    priority factor is the P4 defect whichever way it is written, and nothing
    in ``screens/`` compares these two attributes to a literal legitimately --
    the scale lives in ``PriorityFactors``, so a real comparison names it and
    reaches the AST as a ``Name``, not a ``Constant``.
    """
    hits = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Compare):
            continue
        sides = [node.left, *node.comparators]
        names_a_factor = any(
            isinstance(side, ast.Attribute) and side.attr in _PRIORITY_FACTOR_ATTRS
            for side in sides
        )
        has_int_literal = any(
            isinstance(side, ast.Constant) and isinstance(side.value, int)
            and not isinstance(side.value, bool)
            for side in sides
        )
        if names_a_factor and has_int_literal:
            hits.append((node.lineno, ast.dump(node)))
    return hits


def test_lrrm11_no_screen_tests_importance_against_a_literal():
    """LRR-M1.1 — the literal 20 is gone from ``screens/``, and stays gone.

    ``PRI-A1``: ``item.importance == 20 or item.urgency == 20``, written out by
    hand in all five list screens for the red ``P:`` chip, while
    ``priority_levels.priority_level_for_item`` already answered exactly that
    question from ``PriorityFactors``. The literal is P4 -- renumbering the
    scale would have left five screens behind -- and the two rules had already
    come apart on real inputs (see ``test_lrrm12``).

    Scoped to the whole of ``screens/``, not to the five files that had the
    defect, so a sixth screen growing its own copy fails here. Asserted as an
    exact count of zero, never a floor: a floor is what hides the narrowing a
    guard was written to catch.
    """
    screens = sorted((_SRC / "screens").glob("*.py"))
    assert len(screens) > 40, f"only {len(screens)} screen modules found"

    hits = {
        path.name: found
        for path in screens
        if (found := _factor_literal_comparisons(path))
    }
    assert hits == {}, "a priority factor is compared to a literal in " + ", ".join(
        f"{name}:{lineno}" for name, found in hits.items() for lineno, _ in found
    )


def _cell_fill_expression(builder):
    """The row builder's own Priority-cell ``RowFill``, compiled.

    Returns a callable that evaluates the *real* expression from the screen's
    source against an item, in that screen module's own globals. So this is not
    a source-text assertion standing in for behaviour: the screen's own call is
    what runs, and it resolves the same names it will resolve at runtime.

    Needed because the expression is a local inside a several-hundred-line
    builder that cannot be called without a Tk root, a ``DatabaseManager``, a
    scroll frame and four lineage caches. Lifting the one expression out is a
    far smaller fiction than a stub of all of that.

    **Retargeted on 2026-11-11 (PCC-M3)** from the local
    ``is_priority_critical``, which the cell no longer keeps: it takes a colour
    rather than a flag, so the expression to evaluate is the ``level_cell_fill``
    call that replaced it. ``self`` is bound to a stand-in carrying only
    ``settings``, which is all the expression reads off it.
    """
    values = local_assignments(builder, "cell")
    assert len(values) == 1, f"`cell` assigned {len(values)} times"
    expression = ast.fix_missing_locations(ast.Expression(body=values[0]))
    code = compile(expression, "<cell-fill>", "eval")
    module_globals = vars(inspect.getmodule(builder))
    return lambda item, settings: eval(  # noqa: S307
        code,
        module_globals,
        {"item": item, "self": SimpleNamespace(settings=settings)},
    )


def test_lrrm12_an_off_scale_critical_is_still_critical():
    """LRR-M1.2 — the two inputs the literal got wrong (P7, adversarial).

    Both look right and are wrong under ``== 20``:

    * **importance 25** -- off the top of the scale, from a hand-edited
      database or a scale that gains a step. ``_at_least`` uses ``>=``, so the
      authority calls it critical; ``== 20`` calls it not critical, which is
      the dangerous direction to be wrong in. It under-reports the priority of
      the most urgent item the user has.
    * **the string ``"20"``** -- SQLite's column types are advisory, so a
      factor can come back as text. ``_at_least`` coerces with ``int()``;
      ``== 20`` is simply ``False`` against a string.

    An ordinary critical item and an ordinary medium one are asserted beside
    them, so the test cannot pass on a condition that is always true.
    """
    off_scale = _item(CRITICAL + 5, None)
    stringly = _item("20", None)
    ordinary = _item(CRITICAL, MEDIUM)
    not_critical = _item(MEDIUM, MEDIUM)

    # The authority's answers, which are what the screens must now give.
    assert priority_level_for_item(off_scale) == LEVEL_ANY_CRITICAL
    assert priority_level_for_item(stringly) == LEVEL_ANY_CRITICAL
    assert priority_level_for_item(ordinary) == LEVEL_ANY_CRITICAL
    assert priority_level_for_item(not_critical) != LEVEL_ANY_CRITICAL

    # Asked of the cell's colour since PCC-M3, not of a boolean: same
    # question, same four inputs.
    settings = AppSettings()
    critical_colour = settings.priority_level_color_any_critical
    assert critical_colour, "Any Critical ships with a colour; this test needs one"
    for name, builder in ROW_BUILDERS:
        cell_fill = _cell_fill_expression(builder)
        for item, label in (
            (off_scale, f"importance {CRITICAL + 5}"),
            (stringly, "importance '20'"),
            (ordinary, "an ordinary critical item"),
        ):
            assert cell_fill(item, settings).fill == critical_colour, (
                f"{name}: {label} does not colour the cell as critical"
            )
        # A medium item gets no cell colour at all, not merely a different one.
        assert cell_fill(not_critical, settings).fill is None, (
            f"{name}: a medium item colours the cell"
        )


# =========================================================================
# LRR cold pass — findings from the 2026-11-10 learning-qa review
# =========================================================================

def _literal_twenty_comparisons(path):
    """Every comparison against ``20`` or ``"20"`` in one module, by AST.

    The companion to ``_factor_literal_comparisons``, and the reason that one
    is not enough on its own. That walk requires an ``ast.Attribute`` named
    ``importance`` or ``urgency`` on one side, so it is blind to the form the
    factor chips use: the factor is bound into a tuple, read back as the local
    ``value``, and compared as ``str(value).strip() == "20"``. A ``Name`` on
    one side and a *string* literal on the other misses both of that walk's
    conditions, which is how four copies of the critical rule survived a guard
    named for banning them (found by a cold pass, 2026-11-10).

    So this one asks the blunter question -- is the number 20 compared against
    anything at all in this module -- which needs no guess about how the
    factor reached the comparison. It is only usable because the answer across
    all of ``screens/`` is zero: the scale lives in ``PriorityFactors``, and
    nothing in a screen has a legitimate reason to compare anything to 20.
    """
    hits = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Compare):
            continue
        for side in [node.left, *node.comparators]:
            elements = (
                side.elts if isinstance(side, (ast.Tuple, ast.List, ast.Set))
                else [side]
            )
            for element in elements:
                if (
                    isinstance(element, ast.Constant)
                    and not isinstance(element.value, bool)
                    and element.value in (20, "20")
                ):
                    hits.append((node.lineno, ast.unparse(node)))
    return hits


def test_lrr_cold_no_screen_compares_anything_to_twenty():
    """LRR-M1.1, second half — the literal 20 in any form, anywhere in screens/.

    ``test_lrrm11_no_screen_tests_importance_against_a_literal`` is named for
    a ban it could not enforce: it looks for ``item.importance == <int>``, and
    the four factor chips wrote ``str(value).strip() == "20"`` over a
    tuple-bound factor instead. Both halves of that shape are invisible to it.

    A guard narrower than its own name is the failure this repo has been
    bitten by most (``tests/source_asserts.py``'s own docstring opens on one),
    so the name is now backed by two checks that fail for different reasons.
    Exact count of zero over every module, never a floor.
    """
    screens = sorted((_SRC / "screens").glob("*.py"))
    assert len(screens) > 40, f"only {len(screens)} screen modules found"

    hits = {
        path.name: found
        for path in screens
        if (found := _literal_twenty_comparisons(path))
    }
    assert hits == {}, "20 is compared against a literal in " + ", ".join(
        f"{name}:{lineno} ({source})"
        for name, found in hits.items()
        for lineno, source in found
    )


def _factor_chip_condition(builder):
    """The row builder's own test for "paint this factor chip red", compiled.

    Found by its effect rather than by its text: the one ``if`` in the builder
    whose body writes ``label_kwargs["fg_color"]``. Returns a callable taking
    the loop's own two names, so the screen's real condition runs against
    adversarial factors -- the same approach as ``_cell_fill_expression``, and for
    the same reason: the condition sits inside a ``for`` over a list of
    four-tuples in a builder that cannot be called without a Tk root.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(builder)))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        # Only the branch that writes it *directly*. ``ast.walk`` descends, so
        # matching anywhere in the subtree also matched the enclosing
        # ``if self.columns_expanded:`` that draws the factor row at all.
        for statement in node.body:
            if (
                isinstance(statement, ast.Assign)
                and isinstance(target := statement.targets[0], ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "label_kwargs"
                and isinstance(target.slice, ast.Constant)
                and target.slice.value == "fg_color"
            ):
                found.append(node.test)
                break
    assert len(found) == 1, f"found {len(found)} fg_color branches, not 1"
    expression = ast.fix_missing_locations(ast.Expression(body=found[0]))
    code = compile(expression, "<factor-chip-condition>", "eval")
    module_globals = vars(inspect.getmodule(builder))
    return lambda label, value: eval(  # noqa: S307
        code, module_globals, {"label": label, "value": value}
    )


#: The four builders that draw the expandable I/U/E/V factor chips. Hierarchical
#: draws no factor row, which is why there are four and not five; the count is
#: asserted below so a fifth cannot be added without this list being revisited.
FACTOR_CHIP_BUILDERS = tuple(
    (name, builder) for name, builder in ROW_BUILDERS
    if name != "hierarchical.create_item_row"
)


def test_lrr_cold_the_factor_chips_ask_the_authority_too():
    """LRR-M1.2, second half — the I and U chips, which the first fix missed.

    ``str(value).strip() == "20"``, in ``today.py``, ``upcoming.py``,
    ``all_items.py`` and ``completed.py``: the same "is this factor critical"
    question the ``P:`` badge asks, two screenfuls below it, answered by a
    literal. It disagreed with the badge for exactly the inputs the badge was
    just taught to accept — an importance of 25 gave a red badge and a plain
    ``I:25`` chip on the same row — and it compared urgency against the
    importance threshold, which ``_at_least``'s docstring calls a fact about
    this build rather than a rule.

    ``E`` and ``V`` are asserted too: they are Size and Value, which are not
    factors a priority *level* is a rule on, so a critical-looking value there
    must not paint a chip. Without them this passes on a condition that
    ignores the label.
    """
    assert len(FACTOR_CHIP_BUILDERS) == 4, FACTOR_CHIP_BUILDERS

    for name, builder in FACTOR_CHIP_BUILDERS:
        paints_red = _factor_chip_condition(builder)
        for label in ("I", "U"):
            assert paints_red(label, CRITICAL), f"{name}: {label}:{CRITICAL}"
            assert paints_red(label, CRITICAL + 5), f"{name}: {label}:{CRITICAL + 5}"
            assert paints_red(label, "20"), f"{name}: {label} as the string '20'"
            assert not paints_red(label, HIGH), f"{name}: {label}:{HIGH} is not critical"
            assert not paints_red(label, None), f"{name}: {label} unset"
            assert not paints_red(label, ""), f"{name}: {label} blank"
        for label in ("E", "V"):
            assert not paints_red(label, CRITICAL), f"{name}: {label} is not a level factor"


def test_lrr_cold_a_segment_fill_carries_its_controls_too():
    """The checkbox and grip follow a segment fill, as they do a level fill.

    ``row_control_kwargs`` gated on ``source != SOURCE_LEVEL``, which was a
    proxy for "this fill brings a derived text colour" and correct only while
    the level fill was the one source that did. LRR-M2.1 made that false: on
    Today, Upcoming and All Items — the three screens that both fill a row
    from its segment and build row controls — the row text moved to the
    derived colour and the ``CTkCheckBox`` kept CustomTkinter's theme border,
    which is the light-on-light pairing PLC-M4.9 exists to prevent.

    Today's drag grip had already moved on its own, reading
    ``fill.text_color or palette["border"]`` directly, so the row was
    inconsistent with itself as well as with the theme.
    """
    settings = AppSettings()
    item = _item(MEDIUM, MEDIUM)
    for colour in ("#DCFCE7", "#334155", "#F8FAFC", "#0F172A"):
        fill = row_fill(
            PALETTE, use_completed_tint=False, segment_color=colour,
        )
        kwargs = row_control_kwargs(fill)
        assert set(kwargs) == {"border_color", "fg_color", "checkmark_color"}, colour
        assert kwargs["border_color"] == fill.text_color
        assert kwargs["checkmark_color"] == fill.fill
        assert contrast_ratio(kwargs["border_color"], colour) >= 3.0, colour


# =========================================================================
# SCV-M4 — a malformed segment colour never becomes a fill
# =========================================================================

def test_scvm41_a_malformed_segment_colour_does_not_become_a_fill():
    """SCV-M4.1 — the fill is a ``#RRGGBB`` value or none at all.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m4

    ``LRR-A1`` records that ``row_fill`` deliberately passed the raw stored
    value through as the fill while computing the normalised form for the text
    colour, on the grounds that what colour a row draws was not what
    ``PLC-A1`` named. That is what this closes: ``row_fill`` is the last gate
    before ``ctk.CTkFrame(fg_color=…)`` in five row builders, and a
    ``TclError`` raised there takes the whole list screen down part-way
    through a refresh -- which is the reason ``normalize_hex_color`` exists
    (PLC-M2.5).

    Both halves are asserted together, because either alone is satisfiable by
    the wrong build: "unreadable gives no fill" also passes where every
    segment fill was dropped, and "a readable colour still fills" also passes
    on today's pass-through.
    """
    settings = AppSettings()
    item = _item(MEDIUM, MEDIUM)

    def fill_for(colour):
        return row_fill(
            PALETTE, use_completed_tint=False, segment_color=colour,
        )

    for colour in ("navy", "red", "not-a-colour", "#GGHHII", "#0X1234",
                   "#1_2345", "#+12345", "#aabbccdd"):
        fill = fill_for(colour)
        assert fill.source == SOURCE_SEGMENT, colour
        assert fill.fill is None, f"{colour!r} reached a widget as {fill.fill!r}"
        assert fill.text_color is None, colour

    # A colour that can be read still fills the row, in the normalised form.
    for typed, normalised in (("#DCFCE7", "#DCFCE7"), ("#dcfce7", "#DCFCE7"),
                              ("#ABC", "#AABBCC"), ("#abc", "#AABBCC")):
        fill = fill_for(typed)
        assert fill.source == SOURCE_SEGMENT, typed
        assert fill.fill == normalised, typed
        assert fill.text_color == pick_text_color(normalised), typed


# =========================================================================
# PCC-M1 to PCC-M5 — the scheme moves from the row to the Priority cell
#
# Spec: docs/unused-docs/implementation_plan_2026-11-11_priority_cell_colour.md
#
# Before 2026-11-11 a level tinted the whole row and the Priority cell was
# ``palette["danger"]`` -- a hard red reachable from no setting. The two have
# swapped: the level colour is the cell's background, and a row with no segment
# colour and no completion keeps the theme's own background.
# =========================================================================

#: The Priority cell's expected ``ctk.CTkLabel`` colour options, as
#: ``ast.unparse`` renders them. Text and not a shape, so a swapped attribute
#: or a dropped fallback fails -- ``None`` is a colour Tk rejects.
EXPECTED_CELL_OPTIONS = {
    "fg_color": "cell.fill or 'transparent'",
    "text_color": "cell.text_color or row_text",
    "corner_radius": "6 if cell.fill else 0",
}

#: The same, for a critical I/U factor chip.
EXPECTED_CHIP_OPTIONS = {
    "fg_color": "critical_chip.fill or 'transparent'",
    "text_color": "critical_chip.text_color or row_text",
    "corner_radius": "6",
}


def _label_calls_using(builder, name):
    """Every ``ctk.CTkLabel`` call in ``builder`` that mentions ``name``.

    Each is returned as ``{keyword: source text}``. Found by effect rather than
    by position, for the reason ``_factor_chip_condition`` gives: these calls
    sit inside loops in builders that cannot run without a Tk root.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(builder)))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "CTkLabel"):
            continue
        if name not in {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}:
            continue
        found.append({kw.arg: ast.unparse(kw.value) for kw in node.keywords})
    return found


def _factor_chip_options(builder):
    """What the critical-chip branch writes into ``label_kwargs``.

    The same branch ``_factor_chip_condition`` finds, read for its assignments
    instead of its test.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(builder)))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        written = {}
        for statement in node.body:
            if (
                isinstance(statement, ast.Assign)
                and isinstance(target := statement.targets[0], ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id == "label_kwargs"
                and isinstance(target.slice, ast.Constant)
            ):
                written[target.slice.value] = ast.unparse(statement.value)
        if "fg_color" in written:
            found.append(written)
    assert len(found) == 1, f"found {len(found)} fg_color branches, not 1"
    return found[0]


def _danger_subscripts(builder):
    """Every ``…["danger"]`` read inside ``builder``, as source text."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(builder)))
    return [
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == "danger"
    ]


def test_pccm1_a_level_no_longer_fills_a_row():
    """PCC-M1 — a priority level is not one of ``row_fill``'s branches.

    Replaces ``test_plcm41_a_row_takes_its_level_colour``, whose claim this
    reverses. ``text_color`` is asserted as well as ``fill``: a row keeping a
    derived text colour without its fill draws black text on the theme's own
    background.
    """
    settings = AppSettings()
    for importance in (CRITICAL, HIGH):
        fill = row_fill(PALETTE, use_completed_tint=False)
        assert fill.fill is None, f"importance {importance} still fills the row"
        assert fill.text_color is None
        assert fill.source == SOURCE_NONE
        # And the level's colour is set, so this is not passing by accident.
        assert level_color(settings, priority_level(importance, LOW))


def test_pccm1_segment_and_completed_still_fill_a_row():
    """PCC-M1 — precedence is now segment, then completed, then nothing.

    Rewritten from ``test_plcm42_segment_and_completed_still_win`` by dropping
    its third, level clause; what it said about these two is unchanged.
    """
    segment = row_fill(PALETTE, use_completed_tint=False, segment_color="#445566")
    assert segment.fill == "#445566"
    assert segment.source == SOURCE_SEGMENT

    done = row_fill(PALETTE, use_completed_tint=True)
    assert done.fill == PALETTE["success_tint"]
    assert done.source == SOURCE_COMPLETED

    # A segment colour outranks the completed tint too, as it always has.
    both = row_fill(PALETTE, use_completed_tint=True, segment_color="#445566")
    assert both.source == SOURCE_SEGMENT

    plain = row_fill(PALETTE, use_completed_tint=False)
    assert plain.fill is None
    assert plain.source == SOURCE_NONE


def test_pccm1_row_fill_no_longer_takes_the_settings_or_the_item():
    """PCC-M1 — the two parameters it needed only to reach the level are gone.

    ``row_fill(self.settings, palette, item=item, …)`` read as though the row
    still depended on the item's priority. Asserted on the signature, so
    restoring either parameter fails here.
    """
    parameters = inspect.signature(row_fill).parameters
    assert list(parameters) == ["palette", "use_completed_tint", "segment_color"]
    assert "item" not in parameters
    assert "settings" not in parameters


def test_pccm2_the_priority_cell_takes_its_level_colour():
    """PCC-M2 — each level's cell colour comes from settings, not a constant."""
    settings = AppSettings()
    critical = level_cell_fill(settings, _item(CRITICAL, LOW))
    high = level_cell_fill(settings, _item(HIGH, LOW))
    assert critical.fill == settings.priority_level_color_any_critical
    assert critical.source == SOURCE_LEVEL
    assert high.fill == settings.priority_level_color_any_high
    assert high.source == SOURCE_LEVEL
    assert critical.fill != high.fill

    # And it follows the setting, not a constant.
    settings.priority_level_color_any_critical = "#010203"
    assert level_cell_fill(settings, _item(CRITICAL, LOW)).fill == "#010203"

    # ``fill_for_level`` is the same answer asked by level rather than by item.
    assert fill_for_level(settings, LEVEL_ANY_CRITICAL).fill == "#010203"
    assert fill_for_level(settings, LEVEL_ANY_HIGH) == high


def test_pccm2_an_unset_level_means_no_cell_fill():
    """PCC-M2 — no fill is ``None``, and it brings no text colour with it.

    Moved from ``test_plcm43_an_unset_level_means_no_fill``. Not ``""``: Tk
    rejects the empty string, turning "no fill" into a ``TclError`` mid-build.
    ``text_color is None`` is the clause the cell adds -- an uncoloured cell on
    a segment-filled row must keep the colour that row derived.
    """
    settings = AppSettings()
    plain = level_cell_fill(settings, _item(MEDIUM, MEDIUM))
    assert plain.fill is None
    assert plain.text_color is None
    assert plain.source == SOURCE_NONE

    settings.priority_level_color_any_critical = ""
    cleared = level_cell_fill(settings, _item(CRITICAL, LOW))
    assert cleared.fill is None
    assert cleared.text_color is None
    assert cleared.source == SOURCE_NONE


def test_pccm2_the_cell_text_clears_the_contrast_bar():
    """PCC-M2 — a cell fill brings its own, legible, text colour.

    Moved from ``test_plcm44_level_fill_text_clears_the_contrast_bar`` with the
    same six colours: what ``AGENTS.md`` requires of a data colour used as a
    fill. Across the range, not only the defaults, since the user picks it.
    """
    settings = AppSettings()
    for colour in ("#DCFCE7", "#FEF3C7", "#000000", "#FFFFFF", "#7F7F7F", "#450A0A"):
        settings.priority_level_color_any_critical = colour
        cell = level_cell_fill(settings, _item(CRITICAL, LOW))
        assert cell.text_color is not None
        ratio = contrast_ratio(cell.fill, cell.text_color)
        assert ratio >= MIN_TEXT_CONTRAST, f"{colour} -> {cell.text_color} is {ratio:.2f}"


def test_pccm3_every_priority_cell_calls_the_helper():
    """PCC-M3 — exactly one ``level_cell_fill`` call in each of the five.

    The total as well as the per-screen count, so dropping a screen from
    ``ROW_BUILDERS`` cannot leave this green -- as ``test_plcm48`` does.
    """
    counts = {
        name: count_calls(builder, "level_cell_fill") for name, builder in ROW_BUILDERS
    }
    assert counts == {name: 1 for name, _ in ROW_BUILDERS}
    assert sum(counts.values()) == 5
    assert len(ROW_BUILDERS) == 5


def test_pccm3_the_cell_options_come_from_the_helper():
    """PCC-M3 — the three colour options, by name, on all five screens.

    Exact text, not a shape: ``fg_color=cell.text_color`` is a shape-correct
    swap, and dropping a fallback yields ``None``, which Tk rejects mid-build.
    """
    for name, builder in ROW_BUILDERS:
        calls = _label_calls_using(builder, "cell")
        assert len(calls) == 1, f"{name}: {len(calls)} CTkLabel calls use `cell`"
        options = calls[0]
        for keyword, expected in EXPECTED_CELL_OPTIONS.items():
            assert options.get(keyword) == expected, f"{name}: {keyword}"


def test_pccm4_the_chip_options_come_from_the_level():
    """PCC-M4 — a critical I/U chip is painted from the Any Critical colour.

    Four screens; Hierarchical draws no factor row. The *condition* stays
    exactly ``is_critical_factor(label, value)`` because
    ``test_lrr_cold_the_factor_chips_ask_the_authority_too`` evals that
    expression with only ``label`` and ``value`` bound, so a local name added
    to it raises ``NameError`` there. Only the two colours changed.
    """
    assert len(FACTOR_CHIP_BUILDERS) == 4, FACTOR_CHIP_BUILDERS
    for name, builder in FACTOR_CHIP_BUILDERS:
        options = _factor_chip_options(builder)
        assert options == EXPECTED_CHIP_OPTIONS, f"{name}: {options}"
        assert count_calls(builder, "fill_for_level") == 1, name

    # Hierarchical has no chips, so it must not ask for the chip colour either.
    assert count_calls(hierarchical.HierarchicalScreen.create_item_row,
                       "fill_for_level") == 0


def test_pccm5_no_row_builder_reaches_for_the_danger_palette():
    """PCC-M5 — the hard red is gone from all five row builders.

    Count zero, scoped to the builder and not the file: ``button_style(
    "danger")`` elsewhere in these screens is a legitimate delete button.
    """
    for name, builder in ROW_BUILDERS:
        found = _danger_subscripts(builder)
        assert found == [], f"{name} still reads {found}"


#: The five screens and how to render one: module, class, and whether the items
#: must be completed first. Completed queries ``get_completed_items``, so an
#: open item is invisible to it and the render reports no rows at all.
RENDER_TARGETS = (
    ("today", "TodayScreen", False),
    ("upcoming", "UpcomingScreen", False),
    ("all_items", "AllItemsScreen", False),
    ("hierarchical", "HierarchicalScreen", False),
    ("completed", "CompletedScreen", True),
)


@pytest.fixture(scope="module")
def rendered_rows():
    """Every list screen's rows, as really built by CustomTkinter.

    One subprocess per screen, run once for the module: five renders at about
    two seconds each is worth paying once rather than per test. See
    ``tests/render_priority_cells.py`` for why it is a subprocess at all, and
    why no window is mapped.

    Returns ``{module: [(row_fill, [(text, fg_color, text_color), ...]), ...]}``.
    """
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    helper = root / "tests" / "render_priority_cells.py"
    rendered = {}
    for module, screen_class, needs_completing in RENDER_TARGETS:
        argv = [sys.executable, str(helper), module, screen_class]
        if needs_completing:
            argv.append("completed")
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=180, cwd=str(root)
        )
        # Only a *display* failure is a skip. A bare TclError is what a rejected
        # widget option raises, which is part of what this is for, so skipping
        # on it would hide the fault instead of reporting it -- the same
        # distinction test_plcm3_the_section_builds_on_real_widgets draws.
        if result.returncode != 0:
            lowered = result.stderr.lower()
            if "no display name" in lowered or "couldn't connect" in lowered:
                pytest.skip(f"no display for {module}: {result.stderr[-200:]}")
            pytest.fail(f"{module} failed to render:\n{result.stderr[-2000:]}")
        rows = []
        for line in result.stdout.splitlines():
            if line.startswith("ROW "):
                rows.append((line[4:], []))
            elif line.startswith("LBL "):
                text, fg_color, text_color = line[4:].split("|")
                rows[-1][1].append((text, fg_color, text_color))
        assert rows, f"{module} rendered no rows:\n{result.stdout}"
        rendered[module] = rows
    return rendered


#: The three rendered items, by score. A score is the product of all four
#: factors and deliberately not the level -- 400 is the ``high`` band while
#: being "No high or critical" -- the distinction ``test_plcm14`` guards.
RENDERED_SCORES = {
    LEVEL_ANY_CRITICAL: 1600,
    LEVEL_ANY_HIGH: 800,
    LEVEL_NO_HIGH_OR_CRITICAL: 400,
}


def _cell_for(rows, score):
    """The ``(fg_color, text_color)`` of the Priority cell showing ``score``.

    All Items draws the bare number under a ``"Priority"`` header; the other
    four draw ``P:n`` with no header (``PRI-A3``). Both spellings are accepted,
    so one assertion covers all five screens.
    """
    for _row_fill, labels in rows:
        for text, fg_color, text_color in labels:
            if text in (f"P:{score}", str(score)):
                return fg_color, text_color
    raise AssertionError(f"no Priority cell for score {score}")


def test_pccm3_a_rendered_priority_cell_carries_the_level_colour(rendered_rows):
    """PCC-M3 — what CustomTkinter holds on the widget, on each of the five.

    The other five-screen checks here are structural. This one builds the row
    and reads the colour back, so it is the only one that catches a screen
    drawing something other than the answer it was given. The expected values
    are the shipped defaults: ``render_priority_cells`` points ``AppSettings``
    at its own temporary file, not at the developer's saved colours.
    """
    defaults = priority_level_fill_colors()
    for module, _screen_class, _needs_completing in RENDER_TARGETS:
        rows = rendered_rows[module]
        for level, score in RENDERED_SCORES.items():
            fg_color, text_color = _cell_for(rows, score)
            expected = defaults[level]
            if expected:
                assert fg_color == expected, f"{module} {level}: {fg_color}"
                assert text_color == pick_text_color(expected), f"{module} {level}"
            else:
                # "No high or critical" ships with no fill, so the cell is
                # transparent and keeps the row's own text colour.
                assert fg_color == "transparent", f"{module} {level}: {fg_color}"
                assert text_color != pick_text_color(defaults[LEVEL_ANY_CRITICAL])


def test_pccm1_a_rendered_row_has_no_priority_tint(rendered_rows):
    """PCC-M1 — the row frame itself, which is what the user asked about.

    A critical row's frame was ``#DCFCE7`` across its width; every row now
    keeps CustomTkinter's own frame colour, a light/dark pair and never a hex
    string. Every rendered row is checked, so a tint fails here whichever of
    the three levels kept it.
    """
    for module, _screen_class, _needs_completing in RENDER_TARGETS:
        for row_fill_value, labels in rendered_rows[module]:
            assert "#" not in row_fill_value, f"{module} row is tinted: {row_fill_value}"
            assert labels, f"{module} reported a row with no labels"


def test_pccm4_a_rendered_critical_chip_carries_the_level_colour(rendered_rows):
    """PCC-M4 — the I/U factor chips, rendered, on the four screens with them.

    ``I:20`` must carry the Any Critical colour. ``I:10`` is High, a level but
    not a *critical factor*, so it stays plain; ``E`` and ``V`` are Size and
    Value, in no level at all, and their clause is what stops this passing on
    a condition that ignores the label.
    """
    expected = priority_level_fill_colors()[LEVEL_ANY_CRITICAL]
    checked = 0
    for module, _screen_class, _needs_completing in RENDER_TARGETS:
        if module == "hierarchical":
            continue  # draws no factor row
        chips = {
            text: (fg_color, text_color)
            for _row_fill, labels in rendered_rows[module]
            for text, fg_color, text_color in labels
            if ":" in text and text.split(":")[0] in ("I", "U", "E", "V")
        }
        assert chips.get("I:20") == (expected, pick_text_color(expected)), (
            f"{module}: I:20 is {chips.get('I:20')}"
        )
        assert chips["I:10"][0] == "transparent", f"{module}: I:10 is painted"
        assert chips["E:4"][0] == "transparent", f"{module}: E:4 is painted"
        assert chips["V:4"][0] == "transparent", f"{module}: V:4 is painted"
        checked += 1
    assert checked == 4, checked
