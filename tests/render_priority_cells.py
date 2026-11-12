"""Render one list screen and report every row label's text and colours.

Purpose: PCC-M3/PCC-M4 -- the AST checks say each screen *takes* its Priority
         cell colours from ``level_cell_fill``. This says what CustomTkinter
         actually holds on the widget afterwards, which is the colour the user
         sees. Nothing else in ``test_priority_level_colors.py`` builds a real
         row.
Spec:    docs/unused-docs/implementation_plan_2026-11-11_priority_cell_colour.md#pcc-m3

In a **subprocess**, for the reason ``tests/render_list_screen.py`` gives:
CustomTkinter does not tolerate several CTk roots in one interpreter, so a full
screen built after other tests have created and destroyed roots hangs the run.

Not named ``test_*`` on purpose: it is a helper, not a test.

The root is withdrawn, so no window is mapped and ``test_ci_contract.py``'s
mapped-window count is untouched.

``AppSettings.get_settings_path`` is redirected into the temporary directory
before the screen is built. Otherwise ``AppSettings.load()`` reads the user's
real settings file and the assertions would depend on whatever colours they
have saved -- and a later ``save`` would write to it.

Usage: python tests/render_priority_cells.py <module> <ScreenClass> [completed]
Prints a ``ROW <fg_color>`` line per rendered row -- the row frame's own fill,
which is what PCC-M1 changed -- followed by one
``LBL <text>|<fg_color>|<text_color>`` line per gridded label in it. Exit 0 unless it genuinely
fails to render.

``completed`` completes every item after creating it, which is the only way the
Completed screen has any rows at all: it queries ``get_completed_items``, so an
open item is invisible to it.
"""

import importlib
import pathlib
import sys
import tempfile
from datetime import date
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import customtkinter as ctk

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.models import ActionItem, PriorityFactors
from src.getmoredone.vps_manager import VPSManager

CRITICAL = PriorityFactors.IMPORTANCE["Critical"]
HIGH = PriorityFactors.IMPORTANCE["High"]
MEDIUM = PriorityFactors.IMPORTANCE["Medium"]

#: One item per priority level, titled with the level it is there to exercise.
#: Size and Value are Medium throughout so the *score* never reaches a band
#: that might be confused with the level (the distinction PLC-M1.4 guards).
ITEMS = (
    ("critical item", CRITICAL, MEDIUM),
    ("high item", HIGH, MEDIUM),
    ("plain item", MEDIUM, MEDIUM),
)


def main(module: str, attr: str, complete: bool = False) -> int:
    workspace = pathlib.Path(tempfile.mkdtemp())
    AppSettings.get_settings_path = classmethod(
        lambda cls, _path=workspace / "settings.json": _path
    )

    vps = VPSManager(str(workspace / "render.db"))
    manager = vps.db_manager
    today = date.today().isoformat()
    for title, importance, urgency in ITEMS:
        item_id = manager.create_action_item(
            ActionItem(
                who="Self",
                title=title,
                start_date=today,
                due_date=today,
                importance=importance,
                urgency=urgency,
                size=PriorityFactors.SIZE["M"],
                value=PriorityFactors.VALUE["M"],
            ),
            apply_defaults=False,
        )
        if complete:
            manager.complete_action_item(item_id)

    window = ctk.CTk()
    window.withdraw()
    app = MagicMock()
    app.vps_manager = vps
    screen_cls = getattr(
        importlib.import_module(f"src.getmoredone.screens.{module}"), attr
    )
    screen = screen_cls(window, manager, app)
    screen.pack(fill="both", expand=True)
    # Expanded, so the I/U/E/V factor chips are built as well as the cell.
    screen.columns_expanded = True
    screen.refresh()
    window.update()

    printed = 0
    for row in screen.scroll_frame.winfo_children():
        labels = _labels_in(row)
        if not labels:
            continue
        # The row frame's own fill: PCC-M1's visible claim is that a
        # priority level no longer sets it.
        print(f"ROW {row.cget('fg_color')}")
        for label in labels:
            print(
                f"LBL {label.cget('text')}"
                f"|{label.cget('fg_color')}"
                f"|{label.cget('text_color')}"
            )
        printed += 1

    if not printed:
        print("NOROWS")
    window.destroy()
    return 0


def _labels_in(widget):
    """Every gridded ``CTkLabel`` under ``widget``, at any depth.

    At any depth because the factor chips live in a nested ``factors_frame``,
    and the Priority cell does not. One walk finds both.
    """
    found = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel) and child.grid_info():
            found.append(child)
        found.extend(_labels_in(child))
    return found


if __name__ == "__main__":
    sys.exit(
        main(
            sys.argv[1],
            sys.argv[2],
            complete=len(sys.argv) > 3 and sys.argv[3] == "completed",
        )
    )
