"""Build the Priority Colours section for real and report what it produced.

Purpose: PLC-M3 -- every other test of this section calls the mixin's handlers
         against stand-ins, so none of them would catch a bad ``grid`` call, a
         widget option CustomTkinter rejects, or a ``fg_color`` Tk will not
         take. Those only show when the user opens Settings.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m3
Tests:   tests/test_priority_level_colors.py::test_plcm3_the_section_builds_on_real_widgets

Run in a **subprocess** by that test, for the reason
``tests/render_list_screen.py`` gives: CustomTkinter does not tolerate several
CTk roots in one interpreter, and building a screen after other tests have
created and destroyed roots hangs the run.

The root is **withdrawn** and never mapped, so this takes no keyboard focus and
puts no window on screen, and it does not add to the ``mapped_windows`` count
that ``test_ci_contract.py`` holds.

Not named ``test_*`` on purpose: it is a helper, not a test.

Prints one ``KEY=value`` line per fact and exits 0; the test does the asserting.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import customtkinter as ctk

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.priority_levels import LEVEL_KEYS, LEVEL_LABELS
from src.getmoredone.screens.settings_priority_colors import (
    SettingsPriorityColorsMixin,
)
from src.getmoredone.theme import status_text_color


class _Host(SettingsPriorityColorsMixin, ctk.CTkFrame):
    """The mixin plus the three ``SettingsScreen`` helpers it leans on."""

    def __init__(self, parent):
        super().__init__(parent)
        self.settings = AppSettings()

    def _status_label(self, parent, text="", level="success", **kwargs):
        return ctk.CTkLabel(
            parent, text=text, text_color=status_text_color(level), **kwargs
        )

    def _info_label(self, parent, text, **kwargs):
        return ctk.CTkLabel(
            parent, text=text, text_color=status_text_color("muted"), **kwargs
        )

    def _set_status(self, label, text, level="success"):
        label.configure(text=text, text_color=status_text_color(level))

    def _write_settings(self, label):  # never reached: no save is attempted
        raise AssertionError("the helper must not write the real settings file")

    def _hand_settings_to_app(self):
        raise AssertionError("the helper must not publish to a running app")


#: Shapes ``int(text[1:], 16)`` called valid and Tk does not. Kept here, next
#: to the only Tk root in the suite, so the claim can be checked rather than
#: believed.
TK_MUST_REJECT = (
    "#0X1234",
    "#+12345",
    "# 12345",
    "#-12345",
    "#1_2345",
    "#\uff11\uff12\uff13\uff14\uff15\uff16",
)


def main() -> int:
    root = ctk.CTk()
    root.withdraw()
    host = _Host(root)
    host.create_priority_colors_section(host)
    root.update_idletasks()

    section = host.winfo_children()[0]
    labels = [
        widget.cget("text")
        for widget in section.winfo_children()
        if isinstance(widget, ctk.CTkLabel)
    ]

    print(f"ENTRIES={len(host.priority_level_color_vars)}")
    print(f"SWATCHES={len(host.priority_level_swatches)}")
    for level in LEVEL_KEYS:
        print(f"VALUE:{level}={host.priority_level_color_vars[level].get()}")
        print(f"SWATCH:{level}={host.priority_level_swatches[level].cget('fg_color')}")
        print(f"LABELLED:{level}={f'{LEVEL_LABELS[level]}:' in labels}")

    # Restore Defaults, through the real variables and the real swatches.
    host.priority_level_color_vars[LEVEL_KEYS[0]].set("#000000")
    host.restore_priority_level_colors()
    root.update_idletasks()
    print(f"RESTORED={host.priority_level_color_vars[LEVEL_KEYS[0]].get()}")

    # A refusal, which must come back before anything is written -- the two
    # guards above raise if the save path gets past validation.
    host.priority_level_color_vars[LEVEL_KEYS[0]].set("chartreuse")
    host.save_priority_level_colors()
    root.update_idletasks()
    print(f"REFUSAL={host.priority_colors_status_label.cget('text')}")

    # The premise of the whole validator, asked of Tk itself rather than
    # assumed from its colour grammar: these are the shapes the first version
    # of normalize_hex_color admitted, and the reason it had to stop is that
    # Tk raises on them. Nothing else in the suite puts one in front of Tk.
    for raw in TK_MUST_REJECT:
        try:
            ctk.CTkFrame(root, fg_color=raw).grid()
            root.update_idletasks()
            verdict = "accepted"
        except Exception as exc:                      # TclError, or whatever Tk raises
            verdict = type(exc).__name__
        print(f"TKREJECTS:{raw}={verdict}")

    root.destroy()
    print("BUILT=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
