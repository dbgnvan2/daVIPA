"""UPD-F1 — a column width or divider position survives a relaunch.

Purpose: prove ``AppSettings.save`` no longer reverts a field another object
         changed, so a width or split ratio written on one tab is still in the
         file after a different screen's object saves.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#2-upd-f1
Tests:   this file

Every test here points ``get_settings_path`` at ``tmp_path``. The default
resolves to the user's real settings file, and a test that wrote there would
change the running app's configuration.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.screens.annual_vision_segments import AnnualVisionSegmentsScreen
from src.getmoredone.screens.ape_assignment import APEAssignmentScreen
from src.getmoredone.screens.ape_period_view import APEPeriodViewScreen
from src.getmoredone.screens.chip_table import (
    ANNUAL_RIGHT_COLUMNS,
    APE_LEFT_COLUMNS,
    APE_RIGHT_COLUMNS,
    WEEK_ACTIONS_LEFT_COLUMNS,
    WEEK_ASSIGNMENT_RIGHT_COLUMNS,
    ChipTable,
)
from src.getmoredone.screens.column_resize import ColumnResizer, ColumnSpec
from src.getmoredone.screens.split_panel import SplitPanel
from src.getmoredone.screens.today import TodayScreen
from src.getmoredone.screens.week_actions import (
    WeekActionsScreen,
    WeekTacticActionsPanel,
)
from src.getmoredone.screens.weekly_items import WeeklyItemsScreen


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


def test_updf11_a_second_settings_object_does_not_revert_the_first(settings_file):
    """UPD-F1.1 — two objects, two fields, both survive the second save.

    Over a dozen screens each call ``AppSettings.load()`` and hold their own
    object. ``save`` wrote ``asdict(self)`` -- every field -- so whichever
    object saved last put its own snapshot of every *other* field back, and
    the width the first object had just stored was gone.
    """
    _write(settings_file, obsidian_vault_path="/Users/me/vault")
    first = AppSettings.load()
    second = AppSettings.load()

    first.today_col_widths = {"title": 410}
    assert first.save() is True

    second.list_row_font_size = 18
    assert second.save() is True

    on_disk = json.loads(settings_file.read_text())
    assert on_disk["list_row_font_size"] == 18, "the second object's own field was lost"
    assert on_disk["today_col_widths"] == {"title": 410}, (
        "the second save reverted a field the first object wrote"
    )


# --- the screens' own persistence paths ------------------------------------
#
# No Tk window is built here. `ChipTable` only stores its container, a
# `ColumnResizer` with no registered header or rows makes `_apply_live` a
# no-op, and `SplitPanel` only calls `bind` on the two widgets it is given --
# so the real drag-release path (`_on_start`/`_on_drag`/`_on_stop` ->
# `_persist` -> `AppSettings.save`) runs exactly as it does in the app.


class _Event:
    """The two attributes `ColumnResizer` reads off a drag event."""

    def __init__(self, x_root):
        self.x_root = x_root


class _Bindable:
    """A stand-in for the frames `SplitPanel` binds its handlers to."""

    def bind(self, *args, **kwargs):
        return None


def _drag(resizer, key, pixels):
    """Drag one column's divider by `pixels` and release it, as the app does."""
    resizer._on_start(_Event(x_root=400), key)
    resizer._on_drag(_Event(x_root=400 + pixels), key)
    resizer._on_stop(_Event(x_root=400 + pixels), key)


def _split(settings, prefix, ratio):
    """Set a divider position and release it, as `SplitPanel.on_release` does."""
    panel = SplitPanel(
        _Bindable(), _Bindable(), _Bindable(), settings=settings, prefix=prefix
    )
    panel.ratio = ratio
    panel._persist()
    return panel


# Every two-panel tab, as the five screen classes declare themselves: the
# prefix each one passes to `ChipTable` and the column set it passes with it.
# Taken from the screen modules rather than retyped, so a renamed prefix or a
# re-pointed column set fails here instead of quietly persisting nowhere.
TABS = (
    (f"{APEAssignmentScreen.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS),
    (f"{APEAssignmentScreen.SETTINGS_PREFIX}_right", APE_RIGHT_COLUMNS),
    (f"{APEPeriodViewScreen.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS),
    (f"{APEPeriodViewScreen.SETTINGS_PREFIX}_right", APE_RIGHT_COLUMNS),
    (f"{AnnualVisionSegmentsScreen.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS),
    (f"{AnnualVisionSegmentsScreen.SETTINGS_PREFIX}_right", ANNUAL_RIGHT_COLUMNS),
    (f"{WeeklyItemsScreen.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS),
    (f"{WeeklyItemsScreen.SETTINGS_PREFIX}_right", WEEK_ASSIGNMENT_RIGHT_COLUMNS),
    (f"{WeekActionsScreen.SETTINGS_PREFIX}_left", WEEK_ACTIONS_LEFT_COLUMNS),
)

SPLIT_PREFIXES = (
    APEAssignmentScreen.SETTINGS_PREFIX,
    APEPeriodViewScreen.SETTINGS_PREFIX,
    AnnualVisionSegmentsScreen.SETTINGS_PREFIX,
    WeeklyItemsScreen.SETTINGS_PREFIX,
    WeekActionsScreen.SETTINGS_PREFIX,
)


def _today_resizer(settings, prefix=TodayScreen.COLUMN_PREFIX):
    """The resizer `TodayScreen.__init__` builds, with its own spec.

    `prefix` is the subclass's, when the panel under test is one: APE Week
    Actions' right panel is a `TodayScreen` subclass with its own
    `COLUMN_PREFIX`, so it stores its Title width in a field of its own and
    reverts everything else from the object `TodayScreen.__init__` loaded.
    """
    return ColumnResizer(
        owner=None,
        settings=settings,
        prefix=prefix,
        set_cell_width=False,
        specs=[ColumnSpec("title", grid_col=1, default_width=260, min_width=120)],
    )


def test_updf12_a_today_save_does_not_wipe_a_vsp_width(settings_file):
    """UPD-F1.2 — the drag that was reverting five tabs' columns.

    `TodayScreen` loads its own `AppSettings` unconditionally
    (`screens/today.py`), and APE Week Actions' right panel is a `TodayScreen`
    subclass -- so a column drag in that panel saved Today's snapshot, taken
    before the VSP tabs had stored anything, over everything they had written
    in the same session. The object here is loaded *first*, which is what made
    it stale.
    """
    _write(settings_file, obsidian_vault_path="/Users/me/vault")
    todays = AppSettings.load()

    vsp = AppSettings.load()
    table = ChipTable(None, vsp, "ape_quarter_left", APE_LEFT_COLUMNS)
    _drag(table.resizer, "segment", 40)
    assert json.loads(settings_file.read_text())["ape_quarter_left_col_widths"][
        "segment"
    ] == 175, "precondition: the VSP drag has to have reached the file"

    _drag(
        _today_resizer(todays, WeekTacticActionsPanel.COLUMN_PREFIX), "title", 40
    )

    on_disk = json.loads(settings_file.read_text())
    assert on_disk["week_actions_col_widths"]["title"] == 300, (
        "the panel's own width was lost"
    )
    assert on_disk["ape_quarter_left_col_widths"]["segment"] == 175, (
        "a column drag on APE Week Actions' Today-derived panel reverted the "
        "width a VSP tab had saved earlier in the session"
    )


def test_updf13_all_five_tabs_persist_their_own_widths(settings_file):
    """UPD-F1.3 — every panel and every divider on all five tabs survives.

    One `AppSettings` object per panel, each loaded before any of them saves,
    which is what the app does: a screen takes its object when it is first
    opened and keeps it. The checklist's step 10 walked all five tabs in one
    session and found three of them empty afterwards.
    """
    _write(settings_file, obsidian_vault_path="/Users/me/vault")

    holders = {prefix: AppSettings.load() for prefix, _columns in TABS}
    split_holders = {prefix: AppSettings.load() for prefix in SPLIT_PREFIXES}

    for prefix, columns in TABS:
        table = ChipTable(None, holders[prefix], prefix, columns)
        _drag(table.resizer, "segment", 40)
    for index, prefix in enumerate(SPLIT_PREFIXES):
        _split(split_holders[prefix], prefix, 0.30 + index * 0.05)

    on_disk = json.loads(settings_file.read_text())
    for prefix, _columns in TABS:
        stored = on_disk[f"{prefix}_col_widths"]
        assert stored.get("segment") == 175, (
            f"{prefix} did not keep its own column width: {stored}"
        )
    for index, prefix in enumerate(SPLIT_PREFIXES):
        assert on_disk[f"{prefix}_split_ratio"] == pytest.approx(
            0.30 + index * 0.05
        ), f"{prefix} did not keep its divider position"


def test_updf14_stored_widths_are_what_the_resizer_reports(settings_file):
    """UPD-F1.4 — a stored width is read back, not replaced by the default.

    The companion to the three tests above: they prove the file keeps the
    number, this proves the next launch uses it. Without it the merge could
    write widths nothing ever reads and every criterion above would still pass.
    """
    _write(
        settings_file,
        ape_quarter_left_col_widths={"segment": 175, "subsegment": 210},
    )
    table = ChipTable(None, AppSettings.load(), "ape_quarter_left", APE_LEFT_COLUMNS)

    assert table.width("segment") == 175
    assert table.width("subsegment") == 210
    defaults = {column.key: column.default_width for column in APE_LEFT_COLUMNS}
    assert defaults["segment"] != 175 and defaults["subsegment"] != 210, (
        "the stored widths match the defaults, so this test proves nothing"
    )
    assert table.width("category") == defaults["category"], (
        "a column with nothing stored must still open at its default"
    )


def test_updf16_a_file_with_foreign_widths_is_merged_not_replaced(settings_file):
    """UPD-F1.6 — P8, dirty state: the file already holds another session's work.

    Two things this object cannot know about, both of which it used to
    destroy: a whole field it has never touched, and a key inside a field it
    has. `ColumnResizer._persist` merges over *its* snapshot of the field, and
    that snapshot is exactly what goes stale, so the field-level merge is not
    enough on its own.
    """
    _write(settings_file, obsidian_vault_path="/Users/me/vault")
    mine = AppSettings.load()

    foreign = AppSettings.load()
    foreign.annual_vision_right_col_widths = {"segment": 190}
    foreign.today_col_widths = {"who": 90}
    foreign.week_actions_split_ratio = 0.37
    assert foreign.save() is True

    _drag(_today_resizer(mine), "title", 40)

    on_disk = json.loads(settings_file.read_text())
    assert on_disk["annual_vision_right_col_widths"] == {"segment": 190}, (
        "a field this object never touched was reset to its default"
    )
    assert on_disk["week_actions_split_ratio"] == pytest.approx(0.37), (
        "a divider position this object never touched was reset to its default"
    )
    assert on_disk["today_col_widths"] == {"who": 90, "title": 300}, (
        "a key inside a field this object did touch was dropped: the resizer "
        "only knows about its own columns"
    )


# --- the merge's own moving parts ------------------------------------------
#
# Three guards that are not acceptance criteria but are the lines the criteria
# above lean on. The first is the regression that sent this fix back to the
# drawing board; the other two were added because the mutation that breaks
# them left every test above green.


def test_a_setting_turned_back_to_its_default_still_persists(settings_file):
    """Why the merge is driven by assignments and not by the defaults.

    Comparing each value against its dataclass default was the first build of
    this merge, and it made turning any setting *off* impossible to save:
    `default_columns_expanded` is `False` by default, so a screen setting it
    back to `False` read as "untouched" and the `True` on disk was kept. One
    object, no stale snapshot, no second screen -- plainly a bug rather than
    the trade the plan described.
    `tests/test_list_view_setting.py::test_default_setting` is the test that
    caught it; this one states the rule.
    """
    _write(settings_file, default_columns_expanded=True, list_row_font_size=18)
    settings = AppSettings.load()
    assert settings.default_columns_expanded is True, "precondition"

    settings.default_columns_expanded = False
    settings.list_row_font_size = 14
    assert settings.save() is True

    on_disk = json.loads(settings_file.read_text())
    assert on_disk["default_columns_expanded"] is False, (
        "a setting turned off came back on"
    )
    assert on_disk["list_row_font_size"] == 14, (
        "a value set back to the default was reverted to the file's"
    )


def test_the_merge_does_not_put_an_unconfirmed_day_shape_back(settings_file):
    """The direction the Day Settings dialog needs: its clear has to stick.

    Held by the assignment record rather than by `MERGE_EXEMPT_FIELDS` -- the
    dialog assigns the flag, so it wins either way. Stated anyway because it
    is what the dialog depends on, and because the first build of this merge
    (default comparison) broke exactly this: `False` is the default, so
    clearing read as "no opinion" and the `True` on disk was kept, leaving the
    one dialog that can confirm the day's shape unable to.
    The test below is the one that pins the exemption.
    """
    _write(settings_file, plan_day_shape_unconfirmed=True, plan_day_start="07:30")
    dialog_object = AppSettings.load()
    assert dialog_object.plan_day_shape_unconfirmed is True, "precondition"

    dialog_object.plan_day_shape_unconfirmed = False
    assert dialog_object.save() is True

    assert json.loads(settings_file.read_text())[
        "plan_day_shape_unconfirmed"
    ] is False, "the file put the guessed day shape back over the confirmation"


def test_every_field_is_written_even_when_the_file_has_never_held_it(settings_file):
    """A merge must not turn into a partial write.

    Taking the file's value for an untouched field is right only while the
    file *has* one: a field absent from disk and still at its default has to
    be written, or the file stops describing the settings it is the record of
    and a renamed or restored field reads back as missing rather than default.
    """
    _write(settings_file, plan_day_start="07:30")

    assert AppSettings.load().save() is True

    on_disk = json.loads(settings_file.read_text())
    missing = sorted(
        spec.name for spec in dataclasses.fields(AppSettings)
        if spec.name not in on_disk
    )
    assert missing == [], f"these fields were left out of the file: {missing}"


def test_a_stale_object_does_not_revert_a_field_the_normalizers_touch(settings_file):
    """`load` and `save` both assign to six fields of their own accord.

    `AppSettings.load` coerces the appearance mode, theme, font size, confetti
    threshold, business year start and week rule after construction, and
    `save` does the same again before it writes. Those are this build reading
    the file, not anyone choosing anything -- so `load` forgets them and
    `save` snapshots the record before its own run. Left recorded, every
    object in the app would claim all six and a stale snapshot would go on
    reverting a theme another screen had just changed.
    """
    _write(settings_file, theme_name="apple_grey")
    stale = AppSettings.load()

    switcher = AppSettings.load()
    # A real theme: `_normalize_theme_name` rewrites an unknown one back to
    # `apple_grey`, which would make this test pass for the wrong reason.
    switcher.theme_name = "purple"
    assert switcher.save() is True
    assert json.loads(settings_file.read_text())["theme_name"] == "purple", (
        "precondition: the theme change has to have reached the file"
    )

    _drag(_today_resizer(stale), "title", 40)

    on_disk = json.loads(settings_file.read_text())
    assert on_disk["theme_name"] == "purple", (
        "a column drag reverted the theme, because loading the settings "
        "counted as choosing them"
    )
    assert on_disk["today_col_widths"]["title"] == 300, (
        "precondition: the drag has to have reached the file"
    )


def test_a_guess_the_file_calls_confirmed_is_written_back_as_a_guess(settings_file):
    """`MERGE_EXEMPT_FIELDS` — the field the file must never win.

    A file can say `plan_day_shape_unconfirmed: false` and hold none of the
    four day values it is a claim about: a build before Day Settings existed
    wrote no such key, and `load` filters unknown keys out, so absence is read
    as "never chosen" and the flag comes back `True`. That correction has to
    reach the file, or the next launch reads `false` again and the Plan
    screen's one irreversible write runs against a day nobody picked.

    Nothing else makes this field exempt: `load` forgets its own assignment of
    it, so without the exemption the merge keeps the file's `false` -- the
    cheap mistake traded for the one that cannot be recovered.
    """
    _write(settings_file, plan_day_shape_unconfirmed=False, theme_name="purple")
    settings = AppSettings.load()
    assert settings.plan_day_shape_unconfirmed is True, (
        "precondition: a flag with none of the four values is not confirmation"
    )

    assert settings.save() is True

    assert json.loads(settings_file.read_text())[
        "plan_day_shape_unconfirmed"
    ] is True, "the file went on claiming a guessed day shape was the user's"
