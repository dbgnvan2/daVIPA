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

``GETMOREDONE_DATA_DIR`` is pointed at a temporary directory **before the
application is imported**, and ``AppSettings.get_settings_path`` with it.
Without the directory override this process resolves the user's real
``~/Library/Application Support/GetMoreDone/``: ``AppSettings.load()`` would
read whatever colours they have saved, and ``VPSManager.__init__`` would append
to the real ``weekly_tactic_debug.log``, which is the record a user reads to
audit what the weekly-tactic migration did to their own rows. ``conftest.py``'s
``_isolate_weekly_tactic_log`` cannot help: it swaps logging handlers
in-process, and that does not cross a process boundary.

Usage: python tests/render_priority_cells.py <module> <ScreenClass>
           [completed] [--critical=#RRGGBB]

``--critical`` writes that colour into the temporary ``settings.json`` as
``priority_level_color_any_critical`` before the screen is built. Without it
the file does not exist, ``AppSettings.load()`` returns the dataclass defaults,
and ``level_color`` falls back to the *same* theme default on an unreadable
value -- so a render of the defaults alone cannot tell a working settings read
from a broken one. Passing a colour no default uses makes the two
distinguishable.
Prints a ``ROW <fg_color>`` line per rendered row -- the row frame's own fill,
which is what PCC-M1 changed -- followed by one
``LBL <text>|<fg_color>|<text_color>`` line per gridded label in it. Exit 0 unless it genuinely
fails to render.

``completed`` completes every item after creating it, which is the only way the
Completed screen has any rows at all: it queries ``get_completed_items``, so an
open item is invisible to it.
"""

import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
from datetime import date
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

#: Set before the application is imported, so every path that hangs off
#: ``paths.app_data_dir_path`` -- the database, the settings file, ``app.lock``
#: and ``weekly_tactic_debug.log`` -- lands here and not in the user's real
#: application-support directory. ``paths`` reads the variable on each call and
#: caches nothing, but doing this after the import would still leave a window
#: for an import-time resolution to escape.
WORKSPACE = pathlib.Path(tempfile.mkdtemp(prefix="render-priority-cells-"))
os.environ["GETMOREDONE_DATA_DIR"] = str(WORKSPACE)

import customtkinter as ctk

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.models import ActionItem, PriorityFactors
from src.getmoredone.paths import app_data_dir_path
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


def main(
    module: str,
    attr: str,
    complete: bool = False,
    critical: str | None = None,
) -> int:
    settings_path = WORKSPACE / "settings.json"
    AppSettings.get_settings_path = classmethod(
        lambda cls, _path=settings_path: _path
    )
    if critical:
        settings_path.write_text(
            json.dumps({"priority_level_color_any_critical": critical})
        )

    vps = VPSManager(str(WORKSPACE / "render.db"))
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

    # What an untinted frame is *in this interpreter*. PCC-M1's rendered check
    # compares against this rather than assuming CustomTkinter's bundled
    # ['gray90', 'gray13']: the app's own default theme (apple_grey) has
    # ['#FFFFFF', '#1D1D1F'] here, so a test that asserted "no # in the value"
    # would fail the moment this helper applied the app's theme, while nothing
    # was tinted.
    print(f"THEME {ctk.ThemeManager.theme['CTkFrame']['fg_color']}")
    # Where the application resolved its data directory, read after it has
    # built everything. This is the only externally observable proof that
    # the redirect at the top of this file took effect: a subprocess that
    # resolved the real directory would merely *open* an existing log in
    # append mode, which leaves no trace a caller can measure.
    print(f"DATADIR {app_data_dir_path()}")

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
    try:
        flags = sys.argv[3:]
        chosen = next(
            (f.split("=", 1)[1] for f in flags if f.startswith("--critical=")),
            None,
        )
        code = main(
            sys.argv[1],
            sys.argv[2],
            complete="completed" in flags,
            critical=chosen,
        )
    finally:
        # One render leaves a SQLite file and a settings file behind, and the
        # fixture runs five. The suite proper reached 1449 stray directories
        # before conftest.py started cleaning up after itself.
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    sys.exit(code)
