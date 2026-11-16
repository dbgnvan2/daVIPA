"""Render the Upcoming screen and report its Day/Date band's colours.

Purpose: DBC-M3 -- the only proof the setting reaches the band is the widget;
         a source-text assertion passes on a helper that is called and
         ignored.
Spec:    docs/unused-docs/implementation_plan_2026-11-15_date_band_colour.md#dbc-m3
Tests:   tests/test_date_band_colour.py::test_dbcm3_the_upcoming_band_is_drawn_from_the_helper

A **subprocess**, for the reason ``render_list_screen.py`` gives: several CTk
roots in one interpreter hang the run. The root is withdrawn and never mapped,
so it takes no focus and does not add to the ``mapped_windows`` count
``test_ci_contract.py`` holds. Not named ``test_*``: it is a helper.

Usage: python tests/render_date_band.py [<band colour>] [post-load]
Prints ``THEME``, then ``FILL``/``TEXT`` per band; exit 0 unless it fails.

``post-load`` hands the colour to the built screen instead of storing it in
``settings.json``. ``AppSettings.load`` normalizes an unusable stored value to
``""`` before any screen sees it, so a stored one cannot reach
``theme.date_band_colors`` at all -- and an assertion fed that way proves the
load healing, not the helper. This flag is how the helper's own fallback is
reached through a real screen build.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile
from datetime import date
from unittest.mock import MagicMock

if __name__ != "__main__":
    raise RuntimeError(
        f"{__file__} is a subprocess entry point, not a module: importing it "
        "sets GETMOREDONE_DATA_DIR for the whole process."
    )

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

WORKSPACE = pathlib.Path(tempfile.mkdtemp(prefix="render-date-band-"))
os.environ["GETMOREDONE_DATA_DIR"] = str(WORKSPACE)

RAW = sys.argv[1] if len(sys.argv) > 1 else ""
POST_LOAD = "post-load" in sys.argv[2:]

# Before the application is imported: the screen reads this in __init__.
(WORKSPACE / "settings.json").write_text(
    json.dumps({"list_date_band_color": "" if POST_LOAD else RAW})
)

import customtkinter as ctk

from src.getmoredone.models import ActionItem
from src.getmoredone.screens import upcoming as upcoming_module
from src.getmoredone.screens.upcoming import UpcomingScreen
from src.getmoredone.theme import semantic_colors
from src.getmoredone.vps_manager import VPSManager


def main() -> int:
    vps = VPSManager(str(WORKSPACE / "render.db"))
    manager = vps.db_manager
    today = date.today().isoformat()
    manager.create_action_item(
        ActionItem(who="Self", title="Call the plumber",
                   start_date=today, due_date=today,
                   importance=10, urgency=10, size=5, value=5),
        apply_defaults=False)

    window = ctk.CTk()
    window.withdraw()
    app = MagicMock()
    app.vps_manager = vps
    screen = UpcomingScreen(window, manager, app)
    screen.pack(fill="both", expand=True)
    window.update()

    if POST_LOAD:
        # ``refresh`` reloads settings, so the value has to come back from
        # ``load`` to survive the rebuild it does.
        injected = upcoming_module.AppSettings.load()
        injected.list_date_band_color = RAW
        upcoming_module.AppSettings.load = classmethod(lambda cls: injected)
        screen.refresh()
        window.update()

    print(f"THEME {semantic_colors()['surface_subtle']}")

    # A band holds a single label; an item row grids a dozen widgets.
    for node in screen.scroll_frame.winfo_children():
        children = node.winfo_children()
        if len(children) != 1 or not isinstance(children[0], ctk.CTkLabel):
            continue
        print(f"FILL {node.cget('fg_color')}")
        print(f"TEXT {children[0].cget('text_color')}")

    window.destroy()
    return 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    sys.exit(code)
