"""
Application settings management.
Stores user preferences like Obsidian vault path.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict, fields, field

from .paths import default_settings_path


@dataclass
class AppSettings:
    """Application settings."""

    # Not a dataclass field, deliberately: ``asdict`` must not write it to the
    # settings file and ``load`` must not read it back. It is the reason the
    # last ``save`` returned False, for a caller that reports to the user. The
    # two failures have different remedies and must not share one message.
    last_save_error = None

    # The four values the Plan grid derives every box from, and the only four
    # the Day Settings dialog takes a confirmation of. Not a dataclass field
    # for the same reason as above; a tuple so nothing can edit it in place.
    DAY_SHAPE_KEYS = (
        "plan_day_start",
        "plan_lunch_start",
        "plan_lunch_minutes",
        "plan_day_end",
    )

    # The fields ``save`` always writes from this object, never reads back from
    # the file. Everything else is merged (see ``_merge_over_file``), and this
    # one must not be: ``save`` makes the file parseable, which is the reason
    # this flag has to outlive the write, and only the Day Settings dialog
    # clears it. Merging it would mean a file still saying "unconfirmed" put
    # that back over the confirmation the dialog had just made. Not a dataclass
    # field, for the same reason as the two above.
    MERGE_EXEMPT_FIELDS = ("plan_day_shape_unconfirmed",)

    obsidian_vault_path: Optional[str] = None
    obsidian_notes_subfolder: str = "GetMoreDone"
    # M7.A.1 — Separate subfolder for Project Notes so they don't mingle with
    # action-item notes. Blank value falls back to obsidian_notes_subfolder.
    # Spec: docs/unused-docs/implementation_plan_2026-06-06_project_notes.md#M7.A.1
    project_notes_subfolder: str = "GetMoreDone/Projects"
    # Default green checkmark, can be customized to image path or emoji
    completion_icon: str = "✓"
    completion_badge_path: Optional[str] = None
    completion_confetti_threshold: int = 0
    appearance_mode: str = "dark"  # system | dark | light
    theme_name: str = "apple_grey"
    list_row_font_size: int = 14

    # PLC-M2 — the row tint for each of the three priority *levels*, which are
    # rules on importance and urgency: Any Critical, Any High but no Critical,
    # and neither. Not priority *bands* (thresholds on priority_score) — see
    # priority_levels.py for why the two are kept apart.
    #
    # Three declared fields and not one dict field, because the set of levels
    # is closed and named, and the UPD-M4 comment below records what an
    # *undeclared* key costs: it is set, used for the session, and silently
    # dropped at the next launch, because save() writes declared fields only.
    # Three names cannot do that, and
    # tests/test_priority_level_colors.py::test_plcm21_every_level_has_a_settings_field
    # holds the mapping from priority_levels.LEVEL_KEYS to these names in both
    # directions.
    #
    # "" means no fill — the row keeps the theme's own background, which is
    # what a row with no high or critical factor has always had. It is not a
    # stand-in for "unset": there is no such state, and the Restore Defaults
    # button is how a default comes back.
    #
    # The defaults are duplicated from theme.priority_level_fill_colors(),
    # which is where the project rule puts a colour. A dataclass default has to
    # be a literal, so it cannot read that table; test_plcm22 asserts the two
    # agree so the copy cannot drift.
    priority_level_color_any_critical: str = "#DCFCE7"
    priority_level_color_any_high: str = "#FEF3C7"
    priority_level_color_no_high_or_critical: str = ""

    # Timer settings
    default_time_block_minutes: int = 30
    default_break_minutes: int = 5
    timer_window_width: int = 450
    timer_window_height: int = 550
    timer_window_x: Optional[int] = None
    timer_window_y: Optional[int] = None
    timer_warning_minutes: int = 10  # When to show green warning

    # Next Action Window settings
    next_action_window_width: int = 500
    next_action_window_height: int = 400
    next_action_window_x: Optional[int] = None
    next_action_window_y: Optional[int] = None

    # Audio settings
    enable_break_sounds: bool = True
    break_start_sound: Optional[str] = None  # Path to WAV file for break start
    break_end_sound: Optional[str] = None    # Path to WAV file for break end
    # Path to folder containing music files for timer
    music_folder: Optional[str] = None
    music_volume: float = 0.7                # Music volume (0.0 to 1.0)

    # Date increment settings
    # Include Saturday in date calculations (push, +/-)
    include_saturday: bool = True
    # Include Sunday in date calculations (push, +/-)
    include_sunday: bool = True
    # First day of week for VSP week generation (0=Monday .. 6=Sunday)
    first_day_of_week: int = 0
    # WT-M2.A — which week counts as week 1 of a year: iso | jan1 | first_full.
    # Default 'iso' preserves the numbering every existing database was built
    # with. Spec: docs/spec_2026-08-18_weekly_tactic_scheduling.md#wt-m2a
    first_week_of_year_rule: str = "iso"

    # List view settings
    # Default state for list views (Today, Upcoming, All Items)
    default_columns_expanded: bool = False
    # First day of business year in MM-DD format
    business_year_start_mmdd: str = "01-01"
    # Drag Schedule date box text color (hex)
    drag_schedule_date_text_color: str = "#FFFFFF"
    # Drag Schedule date/future box height in pixels
    drag_schedule_box_height_px: int = 86
    drag_schedule_title_col_width: int = 220
    # Plan screen: width (px) of the items column. Fixed, not a share of
    # the window -- it holds titles, and the day beside it is what the
    # width is for. Editable in Settings > Date Increment Settings,
    # beside the two Drag Schedule sizes.
    plan_items_col_width: int = 260
    # Today view: width (px) of the resizable Title column
    today_title_col_width: int = 260
    # Per-column widths (px) for resizable list columns, keyed by column id.
    # Managed by screens/column_resize.py; the scalars above are legacy fallbacks.
    today_col_widths: dict = field(default_factory=dict)
    drag_schedule_col_widths: dict = field(default_factory=dict)
    # AWA-M5.5 — the APE Week Actions panel stores its Title width here, not
    # under ``today_col_widths``. It inherits the Today list, so without its
    # own key, resizing either panel would move the other.
    week_actions_col_widths: dict = field(default_factory=dict)

    # UPD-D4 — where a two-panel VSP tab's vertical divider was left. The same
    # class of state as a column width, and stored the same way: one field per
    # screen, named <screen prefix>_split_ratio. One per adopting screen, added
    # as each adopts; screens/split_panel.py logs a prefix with no field here.
    ape_quarter_split_ratio: float = 0.5
    ape_month_split_ratio: float = 0.5
    annual_vision_split_ratio: float = 0.5
    week_assignment_split_ratio: float = 0.5
    week_actions_split_ratio: float = 0.5

    # UPD-M4 — a two-panel VSP tab's column widths, one field per *panel*: the
    # two panels of one tab are different shapes, and one store for both would
    # make a drag in either move the other (UPD-M3.6). An undeclared field is
    # worse here than a missing ratio, because ColumnResizer._persist setattrs
    # it and calls save(), which writes declared dataclass fields only -- the
    # width is kept for the session and gone at the next launch, with nothing
    # said. Held by
    # tests/test_unified_panel_design.py::test_updm44_every_panel_prefix_has_a_settings_field.
    ape_quarter_left_col_widths: dict = field(default_factory=dict)
    ape_quarter_right_col_widths: dict = field(default_factory=dict)
    ape_month_left_col_widths: dict = field(default_factory=dict)
    ape_month_right_col_widths: dict = field(default_factory=dict)
    annual_vision_left_col_widths: dict = field(default_factory=dict)
    annual_vision_right_col_widths: dict = field(default_factory=dict)
    week_assignment_left_col_widths: dict = field(default_factory=dict)
    week_assignment_right_col_widths: dict = field(default_factory=dict)
    # UPD-M6 — the left panel of APE Week Actions only. Its right panel is a
    # TodayScreen subclass and keeps the week_actions_col_widths field above,
    # which already holds widths a user has set (UPD-D3).
    week_actions_left_col_widths: dict = field(default_factory=dict)

    # Future date options (Drag Schedule)
    mid_term_offset_days: int = 90
    long_term_offset_days: int = 180
    next_month_offset_days: int = 0
    next_quarter_offset_days: int = 0

    # Plan screen — the shape of a time-blocking day (TB-M4).
    # The planner derives every block's clock time from the day's order plus
    # these four values, so they are the day's definition, not decoration.
    # Spec:  docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
    # Tests: tests/test_plan_settings.py::test_tbm43_day_settings_round_trip
    plan_day_start: str = "08:00"
    plan_lunch_start: str = "12:00"
    # Lunch is a start plus a length rather than a start/end pair: a length is
    # what the packing arithmetic needs, and two times that could disagree with
    # each other is a state the user can get wrong.
    plan_lunch_minutes: int = 60
    plan_day_end: str = "17:00"
    # Which weekdays accept blocks, Monday first. A date whose weekday is False
    # is refused as a block day — the planner will not write work onto a day
    # the user has said they do not work.
    plan_block_weekdays: list = field(
        default_factory=lambda: [True, True, True, True, True, False, False]
    )
    # TG-M5 -- whether the four day values above are a stand-in nobody has
    # confirmed. Persisted on purpose, and this is the whole point of it: when
    # a settings file cannot be parsed, every value in this object is a
    # default, and the first save from *any* screen writes those defaults to
    # disk as ordinary-looking settings. Without a field that goes to disk
    # with them, the next launch reads a day start of 08:00 that nobody chose
    # and has no way to know it was a guess -- and the Plan screen's adoption,
    # which cannot be undone, would act on it. Cleared only by the Day
    # Settings dialog, which is the one screen that shows these four values and
    # takes the user's confirmation of them.
    #
    # The default is False and must stay False, so that constructing an
    # AppSettings in code is not a claim about a user. Deciding it from a file
    # is ``_day_shape_was_confirmed``, and absence there is never confirmation
    # -- read its docstring before changing either.
    plan_day_shape_unconfirmed: bool = False

    # CE-M3.1 / D3 — which Google Calendar the Plan screen's export writes to.
    # "primary" is the account's own calendar, which is what the three event
    # methods used to hard-code. A field rather than a constant so a user who
    # plans into a work calendar is not editing source to do it.
    # Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m31
    # Tests: tests/test_plan_screen_calendar_export.py::test_cem443_the_configured_calendar_is_the_one_written_to
    plan_export_calendar_id: str = "primary"

    # Email → Action Items (Gmail importer)
    gmail_import_enabled: bool = True
    gmail_import_trigger_label: str = "GMD"
    gmail_import_moved_label: str = "GMD/moved"
    gmail_import_interval_seconds: int = 300
    calendar_import_days_ahead: int = 14

    def __post_init__(self):
        """Start tracking assignments, with none recorded.

        Purpose: UPD-F1 -- ``save`` has to know which fields this object was
                 actually asked to change.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#2-upd-f1
        Tests:   tests/test_settings_merge_on_save.py::test_updf11_a_second_settings_object_does_not_revert_the_first

        The generated ``__init__`` has just assigned every field, and none of
        that is a choice anyone made -- so the set starts empty here rather
        than in ``__setattr__``, which runs during that ``__init__``.
        ``object.__setattr__`` because ``__setattr__`` below would otherwise
        record ``_assigned`` as an assignment of its own.
        """
        object.__setattr__(self, "_assigned", set())

    def __setattr__(self, name, value):
        """Record every attribute written on this object.

        Purpose: UPD-F1 -- the one thing that separates "set to this value" from
                 "never had an opinion", which comparing against the dataclass
                 default cannot do.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#2-upd-f1
        Tests:   tests/test_settings_merge_on_save.py::test_a_setting_turned_back_to_its_default_still_persists

        ``__dict__.get`` rather than ``self._assigned``: this runs for all 80-odd
        fields during ``__init__``, before ``__post_init__`` has made the set,
        and an attribute lookup that raises on every one of them would be the
        only exception this class throws in normal use.

        A dict field mutated **in place** is not seen here. Nothing in the app
        does that -- ``ColumnResizer._persist`` and ``SplitPanel._persist`` both
        build a new value and ``setattr`` it -- and a caller that did would be
        invisible to the merge, so it is stated rather than guarded.
        """
        assigned = self.__dict__.get("_assigned")
        if assigned is not None:
            assigned.add(name)
        object.__setattr__(self, name, value)

    def _assigned_names(self) -> set:
        """The fields written on this object since it was loaded.

        A set of its own for an object that somehow has none -- a copy, or an
        instance built around ``__init__`` -- for which the honest answer is
        "nothing is known to have changed", and the file wins.
        """
        return set(self.__dict__.get("_assigned") or ())

    def _forget_assignments(self) -> None:
        """Treat this object as freshly loaded: nothing changed yet.

        ``load`` normalizes six fields after construction, which is this build
        reading the file rather than a user choosing anything. Left recorded,
        every object would claim those six and a stale snapshot would go on
        reverting an appearance mode or a font size another screen had changed.
        """
        self.__dict__.get("_assigned", set()).clear()

    @classmethod
    def get_settings_path(cls) -> Path:
        """Get the path to the settings file (user-writable)."""
        return default_settings_path()

    @classmethod
    def load(cls) -> 'AppSettings':
        """Load settings from file."""
        settings_path = cls.get_settings_path()

        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                valid_keys = {f.name for f in fields(cls)}
                filtered = {k: v for k, v in data.items() if k in valid_keys}
                settings = cls(**filtered)
                settings.appearance_mode = cls._normalize_appearance_mode(
                    settings.appearance_mode)
                settings.theme_name = cls._normalize_theme_name(
                    settings.theme_name)
                settings.list_row_font_size = cls._normalize_list_row_font_size(
                    getattr(settings, "list_row_font_size", 14)
                )
                settings.completion_confetti_threshold = cls._normalize_completion_confetti_threshold(
                    getattr(settings, "completion_confetti_threshold", 0)
                )
                settings.business_year_start_mmdd = cls._normalize_business_year_start_mmdd(
                    getattr(settings, "business_year_start_mmdd", "01-01")
                )
                settings.first_week_of_year_rule = cls._normalize_first_week_of_year_rule(
                    getattr(settings, "first_week_of_year_rule", "iso")
                )
                substituted = settings._normalize_plan_day_settings()
                # Decided from the file, not from the fact that it parsed. A
                # file can parse perfectly and still have nothing to say about
                # the day's shape -- see ``_day_shape_was_confirmed``.
                settings.plan_day_shape_unconfirmed = (
                    not cls._day_shape_was_confirmed(data, substituted)
                )
                # Everything above is the file being read, not a choice. From
                # here on, an assignment is something a screen did.
                settings._forget_assignments()
                return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
                unreadable = cls()
                # Written to the file by the first save, so a relaunch still
                # knows these four day values were never chosen.
                unreadable.plan_day_shape_unconfirmed = True
                return unreadable

        # No file at all is no confirmation either: these four values are
        # defaults nobody has seen. Harmless on a fresh install, where there
        # are no blocks to adopt, and the honest answer in the case that is not
        # a fresh install -- a settings file deleted and a database kept.
        fresh = cls()
        fresh.plan_day_shape_unconfirmed = True
        return fresh

    @classmethod
    def _day_shape_was_confirmed(cls, data: dict, substituted: bool) -> bool:
        """Whether the four day values in a settings file are the user's.

        Purpose: TG-M5 -- the single question the irreversible grid adoption
                 is gated on.
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
        Tests:   tests/test_plan_settings.py::test_a_settings_file_from_before_day_settings_is_not_a_confirmed_day

        Confirmed means the file *says so*: ``plan_day_shape_unconfirmed``
        present and false, all four values present, and none of them
        substituted on the way in. Absence is not confirmation, and that is
        the whole of this method --

        * a file written before Day Settings existed holds none of the four
          keys, so all four values are this build's guess. ``load`` filters
          the parsed dict against the dataclass fields, which erases the
          difference between a default the user accepted and a default nobody
          has seen; checking for the key is the only way back to it.
        * a file written by a build that does not define this field has lost
          the key, because that build's ``save`` writes ``asdict`` of a class
          without it. A boolean whose absence meant "confirmed" could not
          survive one launch of an older packaged app.
        * a value the normalizer had to replace -- ``"25:00"``, a hand-edited
          ``"8am"`` -- is as much a guess as one that was never there.

        A wrong "unconfirmed" costs one visit to Day Settings. A wrong
        "confirmed" lets adoption rewrite stored clock times that nothing can
        recover, so the cheap mistake is the default.
        """
        if substituted:
            return False
        if data.get("plan_day_shape_unconfirmed") is not False:
            return False
        return all(key in data for key in cls.DAY_SHAPE_KEYS)

    def save(self) -> bool:
        """Write settings to file. Returns whether the write succeeded.

        Purpose: the one destructive step in this class, and the merge that
                 keeps it from being destructive about fields it was not asked
                 to change.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#2-upd-f1
        Tests:   tests/test_plan_settings.py::test_an_unreadable_settings_file_is_kept_before_it_is_overwritten
                 tests/test_settings_merge_on_save.py::test_updf11_a_second_settings_object_does_not_revert_the_first

        An unreadable file is **copied aside before it is overwritten.** When
        the file on disk exists but would not parse, every value in this object
        is a default standing in for one we could not read -- and this method
        writes all of them, not just the ones a dialog touched. Overwriting is
        how the user gets a working settings file back, but it would otherwise
        destroy the only copy of the one they had, including the fields no
        screen in the app can re-enter by hand.

        Whether to keep it is read **from the file, at save time**, and not
        from a flag set when this object was loaded. Over a dozen screens each
        call ``AppSettings.load()`` and hold their own object, while
        ``app.settings`` is loaded once at startup and lives for the session,
        so a flag captured at load describes a file another object may already
        have rewritten -- and the startup object would then archive a perfectly
        good file and say in the log that it could not be read. The file is the
        only thing that knows the answer. (P6: verify the artifact, do not
        trust a status field about it.)

        The same fact decides what gets written. UPD-F1: this used to dump
        ``asdict(self)`` -- every field -- so the last object to save put its
        own snapshot of every *other* field back, and a column width a VSP tab
        had stored minutes earlier was gone. APE Week Actions' right panel is a
        ``TodayScreen`` subclass and ``screens/today.py`` loads its own object
        unconditionally, so one column drag there reverted the widths five
        other tabs had saved in the same session. So the write is a
        read-modify-write: the file is re-read here and only the fields this
        object was actually asked to change are merged **over** it by
        ``_merge_over_file``, which repairs every screen holding its own
        snapshot rather than only that one (P5).

        This does **not** touch ``plan_day_shape_unconfirmed``: writing the
        file makes it parseable, it does not make these values the user's, and
        that one has to survive both this process and the next. Only the Day
        Settings dialog clears it, which is why it is in
        ``MERGE_EXEMPT_FIELDS`` and is written from this object every time.

        The return value is additive: callers that ignore it behave as before,
        and the ones that report success to the user should not.
        ``last_save_error`` carries which failure it was.
        """
        settings_path = self.get_settings_path()
        # Snapshotted before the normalizers below, which assign to this object
        # and would otherwise claim six fields on every save -- including on a
        # stale object that never touched them.
        assigned = self._assigned_names()
        self.last_save_error = None
        self.appearance_mode = self._normalize_appearance_mode(
            self.appearance_mode)
        self.theme_name = self._normalize_theme_name(self.theme_name)
        self.list_row_font_size = self._normalize_list_row_font_size(
            self.list_row_font_size
        )
        self.completion_confetti_threshold = self._normalize_completion_confetti_threshold(
            self.completion_confetti_threshold
        )
        self.business_year_start_mmdd = self._normalize_business_year_start_mmdd(
            self.business_year_start_mmdd
        )
        self.first_week_of_year_rule = self._normalize_first_week_of_year_rule(
            self.first_week_of_year_rule
        )
        self._normalize_plan_day_settings()

        # Ensure data directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        if self._will_not_parse(settings_path):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            kept = settings_path.with_name(f"{settings_path.name}.unreadable-{stamp}")
            try:
                shutil.copy2(settings_path, kept)
            except Exception as e:
                # Refusing to write is the lesser failure. This file is the only
                # copy of whatever could not be read out of it, and this method
                # replaces every value in it -- so overwriting after a failed
                # copy destroys the one thing the copy exists to keep, and the
                # caller would be told the settings were saved.
                print(f"Could not keep the unreadable settings file: {e}")
                self.last_save_error = (
                    "Could not set aside the settings file that would not"
                    " load, so nothing was changed — move or delete it and"
                    " try again"
                )
                return False
            try:
                # Outside the copy's ``try`` on purpose. A print that fails --
                # a packaged app with a closed stdout, a full disk -- must not
                # be read as a copy that failed, and must not escape a method
                # whose callers have no handler.
                print(f"Kept the unreadable settings file at {kept}")
            except Exception:
                pass

        # Read before the open, never inside it. ``open(path, 'w')``
        # truncates the moment it is evaluated, so reading in the ``json.dump``
        # call read an empty file and the merge had nothing to keep -- the
        # whole fix silently did nothing, and UPD-F1.1 still failed.
        payload = self._merge_over_file(self._on_disk(settings_path), assigned)

        try:
            with open(settings_path, 'w') as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            self.last_save_error = "Could not write the settings file — see the log"
            return False

        return True

    @staticmethod
    def _on_disk(settings_path: Path) -> dict:
        """What the settings file holds right now, or ``{}``.

        Purpose: UPD-F1 -- the "read" of ``save``'s read-modify-write.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#2-upd-f1
        Tests:   tests/test_settings_merge_on_save.py::test_updf16_a_file_with_foreign_widths_is_merged_not_replaced

        ``{}`` for a file that is missing, unreadable, or holds something that
        is not a JSON object. All three mean the same thing to the merge: there
        is nothing on disk to keep, so every value is written from this object
        -- which is exactly the recovery ``save`` already performs on an
        unreadable file after copying it aside.
        """
        try:
            with open(settings_path, 'r') as f:
                data = json.load(f)
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _merge_over_file(self, on_disk: dict, assigned: set) -> dict:
        """This object's changes over what the file already holds.

        Purpose: UPD-F1 -- a field this object was never asked to change keeps
                 the value the file has, so two screens holding their own
                 ``AppSettings`` no longer revert each other.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#2-upd-f1
        Tests:   tests/test_settings_merge_on_save.py::test_updf11_a_second_settings_object_does_not_revert_the_first
                 tests/test_settings_merge_on_save.py::test_updf16_a_file_with_foreign_widths_is_merged_not_replaced

        ``assigned`` is what ``__setattr__`` recorded, and a plain
        ``{**on_disk, **asdict(self)}`` is what this replaces: ``asdict``
        carries *every* field, so the file's value would lose every time, which
        is the bug.

        Comparing each value against its dataclass default instead was built
        first and withdrawn: "still at the default" reads a field a screen has
        deliberately set *to* its default as an untouched one, so turning any
        setting off could never be saved -- by one object alone, with no second
        object involved. ``tests/test_list_view_setting.py::test_default_setting``
        caught it. The plan named the dirty set as the fallback if the trade it
        described was not acceptable; the trade it described was not the one
        that comparison actually makes.

        A field is written when this object was asked to change it, when the
        field is exempt, or when the file has no value for it at all -- that
        last one so a merge never turns into a partial write and leaves the
        file no longer describing the settings it is the record of.

        Two consequences, both deliberate:

        * **A dict field is merged by key**, not replaced, so a key the file
          holds and this object's snapshot does not survives.
          ``ColumnResizer._persist`` merges over *its* snapshot of the field,
          and that snapshot is the thing that goes stale.
        * **A key the file holds and this class does not is kept.** ``load``
          filters unknown keys out, so a build without a field no longer
          deletes it from the file on the first save.
        """
        merged = dict(on_disk)
        for name, value in asdict(self).items():
            if not (name in self.MERGE_EXEMPT_FIELDS
                    or name in assigned
                    or name not in on_disk):
                continue
            stored = on_disk.get(name)
            if isinstance(value, dict) and isinstance(stored, dict):
                merged[name] = {**stored, **value}
            else:
                merged[name] = value
        return merged

    @staticmethod
    def _will_not_parse(settings_path: Path) -> bool:
        """Whether a settings file is there and cannot be read back.

        Purpose: the one question ``save`` has to ask before overwriting.
        Tests:   tests/test_plan_settings.py::test_a_second_object_does_not_archive_a_file_that_now_parses

        A file that cannot even be opened counts as one that will not parse:
        the answer feeds a decision about whether overwriting destroys
        something, and a file we cannot read is exactly the one we must not
        replace. Same breadth of catch as ``load``, deliberately -- the two
        must agree about what unreadable means.

        ``is_file``, not ``exists``: the copy exists to keep the *contents* of
        a file we could not parse, and a path that is a directory has none to
        lose. Caught by the two tests that make the settings path a directory
        to force a write failure -- with ``exists`` the copy was attempted,
        failed, and the user was told to move a file that was not there, about
        a failure that was really the write.
        """
        if not settings_path.is_file():
            return False
        try:
            with open(settings_path, 'r') as f:
                json.load(f)
        except Exception:
            return True
        return False

    def _normalize_plan_day_settings(self) -> bool:
        """TB-M4.1/4.2 — coerce the four day values and the seven weekday flags.

        Purpose: a hand-edited or corrupt settings file must not stop the app
                 from starting, and must not hand the packing arithmetic a time
                 it cannot read.
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md#tb-m4
        Tests:   tests/test_plan_settings.py::test_tbm41_bad_time_falls_back_to_default

        Applied on both load and save, like every other normalizer here: a
        value written by an older build, by hand, or by a future field the
        dialog does not yet guard arrives through load, and the dialog's own
        output goes out through save.

        The import is inside the function because time_block_layout imports
        models, and loading settings must not drag the data model in --
        _normalize_theme_name defers its import for the same reason.
        """
        from .time_block_layout import (
            DEFAULT_DAY_END,
            DEFAULT_DAY_START,
            DEFAULT_LUNCH_MINUTES,
            DEFAULT_LUNCH_START,
            MINUTES_PER_DAY,
            TimeFormatError,
            format_hhmm,
            normalize_block_weekdays,
            parse_clock_time,
        )

        # parse_clock_time, not parse_hhmm: a settings file written before that
        # check existed can hold "25:00", and a Day End past every block the
        # planner can make retires the overrun warning permanently. Falling
        # back rather than raising, because an unreadable settings file must
        # not stop the app from starting -- the dialog is where a person is
        # told, and it raises.
        # Returned rather than only applied: a substituted day value is a
        # guess of ours, and ``load`` has to mark the day's shape unconfirmed
        # when one was needed. The three clock values are parsed without a
        # default so the failure is visible here instead of being absorbed.
        substituted = False
        for name, fallback in (
            ("plan_day_start", DEFAULT_DAY_START),
            ("plan_lunch_start", DEFAULT_LUNCH_START),
            ("plan_day_end", DEFAULT_DAY_END),
        ):
            try:
                minutes = parse_clock_time(getattr(self, name))
            except TimeFormatError:
                minutes = parse_clock_time(fallback)
                substituted = True
            setattr(self, name, format_hhmm(minutes))

        try:
            lunch = int(self.plan_lunch_minutes)
        except (TypeError, ValueError):
            lunch = DEFAULT_LUNCH_MINUTES
            substituted = True
        # Capped at a day: a lunch longer than the day it sits in would push
        # every block past midnight, which looks like the planner losing them.
        clamped = max(0, min(lunch, MINUTES_PER_DAY))
        if clamped != lunch:
            substituted = True
        self.plan_lunch_minutes = clamped

        # Stored as a list, not a tuple: asdict() goes straight to JSON. Not
        # part of ``substituted``: the weekday flags are not one of the four
        # values adoption derives a box from, and a coerced flag cannot move
        # planned work to another hour.
        self.plan_block_weekdays = list(
            normalize_block_weekdays(self.plan_block_weekdays)
        )

        return substituted

    @staticmethod
    def _normalize_first_week_of_year_rule(value: Optional[str]) -> str:
        """WT-M2.A.2 — an unknown rule falls back to 'iso' without raising.

        Spec:  docs/spec_2026-08-18_weekly_tactic_scheduling.md#wt-m2a2
        Tests: tests/test_week_numbering.py::test_wt_m2a2_unknown_rule_falls_back_to_iso
        """
        from .week_calendar import normalize_rule
        return normalize_rule(value)

    @staticmethod
    def _normalize_appearance_mode(value: Optional[str]) -> str:
        allowed = {"system", "dark", "light"}
        mode = (value or "").strip().lower()
        return mode if mode in allowed else "dark"

    @staticmethod
    def _normalize_theme_name(value: Optional[str]) -> str:
        """Coerce a persisted theme name, using theme.py's list and no other.

        This held a SECOND hardcoded copy of the theme names. Adding a theme to
        THEME_NAMES made it appear in the Settings picker and be written to
        settings.json — and then this rewrote it to "apple_grey" on the next
        load, because the new name was not in the copy. Picking a new theme
        silently reverted to the default, with nothing logged.

        Imported inside the function: theme.py pulls in customtkinter, and
        loading settings must not require a GUI toolkit. selftest.py defers its
        imports the same way and for the same reason.
        """
        from .theme import normalize_theme_name

        return normalize_theme_name(value)

    @staticmethod
    def _normalize_list_row_font_size(value: Optional[int]) -> int:
        try:
            size = int(value)
        except (TypeError, ValueError):
            size = 14
        return max(10, min(24, size))

    @staticmethod
    def _normalize_business_year_start_mmdd(value: Optional[str]) -> str:
        text = (value or "").strip()
        if len(text) != 5 or text[2] != "-":
            return "01-01"
        month_text, day_text = text.split("-", 1)
        try:
            month = int(month_text)
            day = int(day_text)
        except ValueError:
            return "01-01"
        if month < 1 or month > 12:
            return "01-01"
        max_days = {
            1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
        }[month]
        if day < 1 or day > max_days:
            return "01-01"
        return f"{month:02d}-{day:02d}"

    @staticmethod
    def _normalize_completion_confetti_threshold(value: Optional[int]) -> int:
        try:
            threshold = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, threshold)

    def validate_vault_path(self) -> bool:
        """Check if vault path exists."""
        if not self.obsidian_vault_path:
            return False
        return Path(self.obsidian_vault_path).exists()

    def get_notes_folder(self) -> Optional[Path]:
        """Get the full path to the notes subfolder."""
        if not self.obsidian_vault_path:
            return None

        vault = Path(self.obsidian_vault_path)
        if not vault.exists():
            return None

        notes_folder = vault / self.obsidian_notes_subfolder
        return notes_folder

    def get_project_notes_folder(self) -> Optional[Path]:
        """Full path to the Project Notes subfolder, falling back when blank.

        Purpose: Resolve the Obsidian folder where Project Notes (.md) live.
                 If project_notes_subfolder is blank, falls back to the
                 generic obsidian_notes_subfolder so users who haven't
                 configured the new setting still get sane behavior.
        Spec:    docs/unused-docs/implementation_plan_2026-06-06_project_notes.md#M7.A.2
        Tests:   tests/test_project_notes.py::TestM7Settings::test_get_project_notes_folder_returns_path
                 tests/test_project_notes.py::TestM7Settings::test_blank_project_subfolder_falls_back
        """
        if not self.obsidian_vault_path:
            return None
        vault = Path(self.obsidian_vault_path)
        if not vault.exists():
            return None
        subfolder = (self.project_notes_subfolder or "").strip() or self.obsidian_notes_subfolder
        return vault / subfolder

    def get_project_notes_subfolder_or_default(self) -> str:
        """Return the subfolder string to pass to create_obsidian_note.

        Purpose: Resolves to the project subfolder, or to the generic
                 obsidian_notes_subfolder if the project setting is blank.
                 Separate from get_project_notes_folder() because
                 create_obsidian_note takes the subfolder *string*, not a Path.
        Spec:    docs/unused-docs/implementation_plan_2026-06-06_project_notes.md#M7.A.5
        Tests:   tests/test_project_notes.py::TestM7Settings::test_blank_project_subfolder_falls_back
        """
        return (self.project_notes_subfolder or "").strip() or self.obsidian_notes_subfolder
