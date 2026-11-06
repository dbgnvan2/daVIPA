"""TB-M5 — the Plan screen's day-settings modal.

Purpose: let the user set the shape of a time-blocking day -- when it starts,
         when lunch is and how long, when it ends, and which weekdays accept
         blocks at all.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m5
Tests:   tests/test_plan_screen.py::test_tbm51_settings_modal_writes_day_settings

A tabbed shell holding one Day tab, rather than a flat panel: these five
controls are the first of the planner's settings, not the last, and a second
tab should not require moving the first one's controls.
"""

from __future__ import annotations

import customtkinter as ctk

from ..app_settings import AppSettings
from ..theme import button_style, status_text_color
from ..time_block_layout import (
    MINUTES_PER_DAY,
    DayBounds,
    TimeFormatError,
    format_hhmm,
    normalize_block_weekdays,
    parse_clock_time,
    parse_hhmm,
    weekday_names,
)


class PlanSettingsDialog(ctk.CTkToplevel):
    """Modal for the four day times and the seven weekday flags.

    The dialog validates rather than normalises: a settings *file* that cannot
    be read falls back silently, because the alternative is an app that will
    not start -- but a user typing "9am" into Day Start is told, because
    silently substituting 08:00 under their hands is how a planner teaches
    someone to distrust it.
    """

    def __init__(self, parent, settings: AppSettings, on_saved=None):
        super().__init__(parent)
        self.settings = settings
        self.on_saved = on_saved

        self.title("Day Settings")
        self.geometry("460x440")

        self._build()

        self.transient(parent)
        self.grab_set()

    # -- construction --------------------------------------------------------

    def _build(self):
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        tabs = ctk.CTkTabview(container)
        tabs.pack(fill="both", expand=True)
        day_tab = tabs.add("Day")
        day_tab.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            day_tab,
            text="Blocks are packed from Day Start, in the order you arrange\n"
                 "them, skipping Lunch. Day End marks where a day is over-filled.",
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 12))

        self.day_start_entry = self._time_row(day_tab, 1, "Day Start:", self.settings.plan_day_start)
        self.lunch_start_entry = self._time_row(day_tab, 2, "Lunch Start:", self.settings.plan_lunch_start)

        ctk.CTkLabel(day_tab, text="Lunch (minutes):", anchor="w").grid(
            row=3, column=0, sticky="w", padx=8, pady=6
        )
        self.lunch_minutes_entry = ctk.CTkEntry(day_tab, width=120)
        self.lunch_minutes_entry.insert(0, str(self.settings.plan_lunch_minutes))
        self.lunch_minutes_entry.grid(row=3, column=1, sticky="w", padx=8, pady=6)

        self.day_end_entry = self._time_row(day_tab, 4, "Day End:", self.settings.plan_day_end)

        ctk.CTkLabel(day_tab, text="Days for Blocks:", anchor="w").grid(
            row=5, column=0, sticky="nw", padx=8, pady=(14, 6)
        )
        days_frame = ctk.CTkFrame(day_tab, fg_color="transparent")
        days_frame.grid(row=5, column=1, sticky="w", padx=8, pady=(14, 6))

        flags = normalize_block_weekdays(self.settings.plan_block_weekdays)
        self.weekday_vars = []
        for index, (name, enabled) in enumerate(zip(weekday_names(), flags)):
            var = ctk.BooleanVar(value=bool(enabled))
            self.weekday_vars.append(var)
            ctk.CTkCheckBox(
                days_frame,
                text=name,
                variable=var,
                width=70,
                checkbox_width=18,
                checkbox_height=18,
            ).grid(row=index // 4, column=index % 4, sticky="w", padx=4, pady=3)

        self.error_label = ctk.CTkLabel(
            container, text="", text_color=status_text_color("error"), anchor="w"
        )
        self.error_label.pack(fill="x", pady=(10, 0))

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(
            buttons, text="Save", width=100, command=self.save, **button_style("primary")
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            buttons, text="Cancel", width=100, command=self.destroy, **button_style("secondary")
        ).pack(side="right")

    def _time_row(self, parent, row: int, label: str, value: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, anchor="w").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        entry = ctk.CTkEntry(parent, width=120, placeholder_text="HH:MM")
        entry.insert(0, value or "")
        entry.grid(row=row, column=1, sticky="w", padx=8, pady=6)
        return entry

    # -- saving --------------------------------------------------------------

    def collect(self) -> dict:
        """The dialog's values, or raise ValueError naming the field at fault.

        Separated from ``save`` so the validation can be tested without driving
        a button, and so the error message is built in one place.
        """
        times = {}
        for field, entry, label in (
            ("plan_day_start", self.day_start_entry, "Day Start"),
            ("plan_lunch_start", self.lunch_start_entry, "Lunch Start"),
            ("plan_day_end", self.day_end_entry, "Day End"),
        ):
            raw = entry.get().strip()
            try:
                # parse_clock_time, not parse_hhmm: the lenient one accepts an
                # hour past 23 because an overrunning block's end_time needs
                # that, and format_hhmm would then clamp "170:0" to "99:59" --
                # storing a value the user never typed, which this dialog
                # exists to avoid.
                times[field] = format_hhmm(parse_clock_time(raw))
            except TimeFormatError:
                raise ValueError(f"{label} must be a time like 09:00") from None

        raw_minutes = self.lunch_minutes_entry.get().strip()
        try:
            lunch_minutes = int(raw_minutes)
        except ValueError:
            raise ValueError("Lunch must be a whole number of minutes") from None
        if lunch_minutes < 0:
            raise ValueError("Lunch cannot be a negative number of minutes")
        if lunch_minutes > MINUTES_PER_DAY:
            raise ValueError("Lunch cannot be longer than a day")

        if parse_hhmm(times["plan_day_end"]) <= parse_hhmm(times["plan_day_start"]):
            raise ValueError("Day End must be after Day Start")

        weekdays = [bool(var.get()) for var in self.weekday_vars]
        if not any(weekdays):
            # Not a cosmetic objection: with no block days every drop is
            # refused, and the planner would look broken rather than configured.
            raise ValueError("At least one day must accept blocks")

        return {**times, "plan_lunch_minutes": lunch_minutes, "plan_block_weekdays": weekdays}

    def save(self):
        """Validate, write to settings, and tell the caller to re-pack the day."""
        try:
            values = self.collect()
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return

        previous = {field: getattr(self.settings, field) for field in values}
        previous["plan_day_shape_unconfirmed"] = getattr(
            self.settings, "plan_day_shape_unconfirmed", False
        )
        for field, value in values.items():
            setattr(self.settings, field, value)
        # Set before the write, not after, because it has to go to disk with
        # the values it describes: this dialog is the one screen that shows the
        # user these four times and takes their confirmation of them, so this
        # is where a guessed day shape stops being a guess.
        self.settings.plan_day_shape_unconfirmed = False
        if not self.settings.save():
            # Said here rather than swallowed: ``on_saved`` reports "Day
            # settings saved" to the user, and the day it would then draw is
            # one that exists only in memory.
            #
            # And put back: this is the app-wide settings object, Cancel does
            # not restore it, and the Plan screen is rebuilt from it on every
            # navigation -- so leaving the new values on it would draw and time
            # the day against bounds that exist nowhere on disk. The
            # confirmation goes back with them: nothing was written, so nothing
            # was confirmed.
            for field, value in previous.items():
                setattr(self.settings, field, value)
            self.error_label.configure(
                text=getattr(self.settings, "last_save_error", None)
                or "Could not write the settings file — see the log"
            )
            return

        if self.on_saved:
            self.on_saved(DayBounds.from_settings(self.settings))

        self.destroy()
