"""The Priority Colours tab of the Settings screen.

Purpose: PLC-M3 — let the user set the row tint for each of the three priority
         levels (Any Critical; Any High, but no Critical; No high or critical).
Spec:    docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m3
Tests:   tests/test_priority_level_colors.py

Its own module, following ``settings_integrations.py``: ``settings.py`` is
already past the 700-line mark in the file-maintainability standard, and this
section has no reason to be in it.

The rows are driven by ``priority_levels.LEVEL_KEYS`` rather than written out
one by one, so a level cannot be left out of this tab without
``test_plcm31_one_row_per_level_in_order`` noticing. What each row *says* comes
from ``priority_color_rows``, a plain function over settings, so the content is
testable without a Tk root.
"""

from __future__ import annotations

import customtkinter as ctk
from tkinter import colorchooser

from ..color_contrast import normalize_hex_color
from ..priority_levels import (
    LEVEL_KEYS,
    LEVEL_LABELS,
    NO_FILL,
    priority_color_rows,
    settings_field_name,
)
from ..theme import button_style, priority_level_fill_colors

#: What the swatch shows for a level set to no fill. ``""`` is not a colour Tk
#: accepts, and ``None`` is not accepted by ``configure`` either.
_NO_FILL_SWATCH = "transparent"


class SettingsPriorityColorsMixin:
    def create_priority_colors_section(self, parent=None):
        """Build the Priority Colours section: one row per priority level."""
        if parent is None:
            parent = self
        section = ctk.CTkFrame(parent)
        section.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        section.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            section,
            text="Priority Level Colours",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 15))

        self.priority_level_color_vars = {}
        self.priority_level_swatches = {}

        for offset, (level, label, colour) in enumerate(
            priority_color_rows(self.settings)
        ):
            row = offset + 1
            ctk.CTkLabel(section, text=f"{label}:").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )

            variable = ctk.StringVar(value=colour)
            self.priority_level_color_vars[level] = variable
            entry = ctk.CTkEntry(section, textvariable=variable, width=140)
            entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)

            ctk.CTkButton(
                section,
                text="Pick Colour",
                width=110,
                command=lambda level=level: self.pick_priority_level_color(level),
                **button_style("secondary"),
            ).grid(row=row, column=2, sticky="w", padx=6, pady=5)

            # A chip, not a row fill: the theme rule allows a colour as a small
            # accent, and the user needs to see the colour they typed without
            # leaving the screen.
            swatch = ctk.CTkFrame(
                section,
                width=48,
                height=22,
                corner_radius=6,
                fg_color=colour or _NO_FILL_SWATCH,
            )
            swatch.grid(row=row, column=3, sticky="w", padx=10, pady=5)
            swatch.grid_propagate(False)
            self.priority_level_swatches[level] = swatch

            # Follow the field as it is typed in, not only on Pick Colour /
            # Restore / Save. Without this the swatch shows the previous colour
            # while the user reads it as confirmation of what they just typed,
            # and the user guide's "a swatch showing what is in the field"
            # would not be true. Registered after the swatch exists, since the
            # callback repaints it.
            variable.trace_add(
                "write", lambda *_: self._refresh_priority_swatches()
            )

        buttons_row = len(LEVEL_KEYS) + 1
        self.priority_colors_save_btn = ctk.CTkButton(
            section,
            text="Apply / Save",
            width=120,
            command=self.save_priority_level_colors,
        )
        self.priority_colors_save_btn.grid(
            row=buttons_row, column=0, sticky="w", padx=10, pady=(12, 5)
        )
        self.priority_colors_restore_btn = ctk.CTkButton(
            section,
            text="Restore Defaults",
            width=140,
            command=self.restore_priority_level_colors,
            **button_style("secondary"),
        )
        self.priority_colors_restore_btn.grid(
            row=buttons_row, column=1, sticky="w", padx=10, pady=(12, 5)
        )

        self.priority_colors_status_label = self._status_label(
            section, text="", level="success"
        )
        self.priority_colors_status_label.grid(
            row=buttons_row + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 4)
        )

        info_text = (
            "A priority level is a rule on an item's Importance and Urgency, and "
            "it tints the whole row in Today, Upcoming, All Items, Hierarchical "
            "and Completed, and in the Action Items panel of APE Week "
            "Assignment, which draws Today's rows.\n"
            "  • Any Critical — Importance or Urgency is Critical.\n"
            "  • Any High, but no Critical — either is High, and neither is Critical.\n"
            "  • No high or critical — neither is High or Critical.\n"
            "Colours are #RRGGBB and apply in both light and dark mode; the row's "
            "text colour is chosen for contrast against whatever you pick.\n"
            "Clear a field to give that level no fill, so the row keeps the theme's "
            "own background.\n"
            "These are not the Plan screen's priority bands, which come from the "
            "priority score."
        )
        self._info_label(section, text=info_text, justify="left", wraplength=600).grid(
            row=buttons_row + 2, column=0, columnspan=4, sticky="w", padx=10, pady=5
        )

    def pick_priority_level_color(self, level: str):
        """Choose one level's colour with the system colour chooser."""
        # Normalised, not raw: Tk raises on a colour it cannot parse, and the
        # exception would escape the button command, leaving a dead button and
        # no message. A half-typed "#12" opens on the level's default instead.
        current = normalize_hex_color(
            self.priority_level_color_vars[level].get()
        ) or priority_level_fill_colors().get(level) or None
        picked = colorchooser.askcolor(
            color=current,
            title=f"Pick the colour for {LEVEL_LABELS[level]}",
        )
        if picked and picked[1]:
            self.priority_level_color_vars[level].set(picked[1].upper())
            self._refresh_priority_swatches()

    def restore_priority_level_colors(self):
        """Put the shipped defaults back into the three fields.

        Fills the fields only; the user still presses Apply / Save, which is
        said on the status line. Writing straight to disk from a button labelled
        "restore" would discard three values with no confirmation and no undo.
        """
        defaults = priority_level_fill_colors()
        for level in LEVEL_KEYS:
            self.priority_level_color_vars[level].set(defaults.get(level, NO_FILL))
        self._refresh_priority_swatches()
        self._set_status(
            self.priority_colors_status_label,
            "Defaults restored — press Apply / Save to keep them",
            "muted",
        )

    def _refresh_priority_swatches(self):
        """Repaint each swatch from its field."""
        for level, swatch in getattr(self, "priority_level_swatches", {}).items():
            colour = normalize_hex_color(self.priority_level_color_vars[level].get())
            swatch.configure(fg_color=colour or _NO_FILL_SWATCH)

    def save_priority_level_colors(self):
        """Validate all three fields, then write them.

        Every field is checked **before** any is written. Writing as it goes
        would leave the first levels saved and the rest not when the third
        field is a typo, which is a state the user did not ask for and cannot
        see.

        A value that is not a colour is refused with the level's own name in
        the message, rather than being silently replaced by a default —
        ``save_date_increment_settings`` quietly rewrites a bad colour to
        ``#FFFFFF``, and a user who typed a colour they meant has no way to
        know it was discarded.
        """
        normalized = {}
        for level in LEVEL_KEYS:
            raw = self.priority_level_color_vars[level].get().strip()
            if not raw:
                normalized[level] = NO_FILL
                continue
            value = normalize_hex_color(raw)
            if value is None:
                self._set_status(
                    self.priority_colors_status_label,
                    f"{LEVEL_LABELS[level]}: “{raw}” is not a colour. "
                    f"Use #RRGGBB, or clear the field for no fill.",
                    "error",
                )
                return
            normalized[level] = value

        previous = {
            level: getattr(self.settings, settings_field_name(level), None)
            for level in LEVEL_KEYS
        }
        for level, value in normalized.items():
            setattr(self.settings, settings_field_name(level), value)

        if not self._write_settings(self.priority_colors_status_label):
            # Put it back. ``self.settings`` is shared by every Save handler on
            # this screen, so colours the user was just told were NOT saved
            # would otherwise be written to disk by the next successful save
            # from any other section. See the note in
            # ``SettingsScreen._hand_settings_to_app``: the aliasing half of
            # this is handled there, the rollback half is per handler.
            for level, value in previous.items():
                setattr(self.settings, settings_field_name(level), value)
            return

        self._hand_settings_to_app()
        for level, value in normalized.items():
            self.priority_level_color_vars[level].set(value)
        self._refresh_priority_swatches()
        self._set_status(
            self.priority_colors_status_label,
            "✓ Saved priority level colours",
            "success",
        )
