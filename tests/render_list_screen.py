"""Render one list screen and report each row's grid columns.

Purpose: the column-contiguity check in test_item_editor_no_context.py runs
         this in a **subprocess**. CustomTkinter does not tolerate several CTk
         roots in one interpreter — building a full screen after other tests
         have already created and destroyed roots hangs the run — so the render
         gets its own process, and the test gets a hard timeout.

Not named ``test_*`` on purpose: it is a helper, not a test.

RLS-M1: ``GETMOREDONE_DATA_DIR`` is redirected before the application is
imported, or this process reads the user's real settings and opens their real
``weekly_tactic_debug.log``.

Usage: python tests/render_list_screen.py <module> <ScreenClass> [expanded]
Prints one ``DATADIR <path>`` line, then one "OK"/"GAP"/"DUP" line per rendered
row; exit 0 always unless it genuinely fails to render.

Columns are reported **without** deduplication on purpose. Deduping hides an
overlap — two widgets gridded into the same cell — and an overlap is precisely
what over-correcting a stale index produces, which is the direction every
constant in this area was just moved.
"""

import importlib
import os
import pathlib
import shutil
import sys
import tempfile
from datetime import date
from unittest.mock import MagicMock

if __name__ != "__main__":
    raise RuntimeError(
        f"{__file__} is a subprocess entry point, not a module. Importing it "
        "sets GETMOREDONE_DATA_DIR for the whole process and creates a "
        "temporary directory nothing will remove, because the redirect has to "
        "happen before the application is imported and so cannot be deferred "
        "to a function. Run it with subprocess.run([sys.executable, ...])."
    )

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

#: Before the application is imported: one variable covers the database, the
#: settings file, ``app.lock`` and ``weekly_tactic_debug.log``.
WORKSPACE = pathlib.Path(tempfile.mkdtemp(prefix="render-list-screen-"))
os.environ["GETMOREDONE_DATA_DIR"] = str(WORKSPACE)

import customtkinter as ctk

from src.getmoredone.models import ActionItem
from src.getmoredone.paths import app_data_dir_path
from src.getmoredone.vps_manager import VPSManager


def main(module: str, attr: str, expanded: bool = False) -> int:
    vps = VPSManager(str(WORKSPACE / "render.db"))
    manager = vps.db_manager
    today = date.today().isoformat()
    for title in ["PW|LS|Blog - W8 - write blog 3", "Call the plumber"]:
        manager.create_action_item(
            ActionItem(who="Self", title=title, start_date=today, due_date=today,
                       importance=10, urgency=10, size=5, value=5),
            apply_defaults=False)

    window = ctk.CTk()
    window.withdraw()
    app = MagicMock()
    app.vps_manager = vps
    screen_cls = getattr(
        importlib.import_module(f"src.getmoredone.screens.{module}"), attr)
    screen = screen_cls(window, manager, app)
    screen.pack(fill="both", expand=True)
    if expanded:
        # Both changed constants have an expanded arm that the default render
        # never reaches (btn_col_start = N if columns_expanded, col_offset = 1).
        screen.columns_expanded = True
        if hasattr(screen, "refresh"):
            screen.refresh()
    window.update()

    # The only externally observable proof the redirect took effect: resolving
    # the real directory leaves no trace a caller could measure.
    print(f"DATADIR {app_data_dir_path()}")

    printed = 0
    # Scoped to the list area: the toolbars above it grid controls with a
    # deliberate spacer gap, which is not what this checks.
    for node in screen.scroll_frame.winfo_children():
        gridded = [c for c in node.winfo_children() if c.grid_info()]
        if len(gridded) < 5 or not all(
                str(c.grid_info().get("row")) == "0" for c in gridded):
            continue
        columns = sorted(int(c.grid_info()["column"]) for c in gridded)
        if len(set(columns)) != len(columns):
            status = "DUP"          # two widgets stacked in one cell
        elif columns != list(range(len(columns))):
            status = "GAP"          # an index was skipped
        else:
            status = "OK"
        print(f"{status} {columns}")
        printed += 1

    if not printed:
        print("NOROWS")
    window.destroy()
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.argv[1], sys.argv[2],
                    expanded=len(sys.argv) > 3 and sys.argv[3] == "expanded")
    finally:
        # One render leaves a SQLite file behind, and the caller runs six.
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    sys.exit(code)
