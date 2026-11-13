"""LPR-M1 — the six list screens rebuild their rows where the pane is.

Spec: docs/spec_coverage.md#list-pane-rebuild-lpr-2026-11-13

Each screen used to take its ``CTkScrollableFrame`` out of the grid, rebuild
the rows, and put it back in a ``finally``. Leaving the grid unmaps the canvas
the rows are drawn in, and the canvas window's width and the scrollregion are
put back by ``<Configure>`` handlers that run only when the event queue is next
serviced -- the blank-pane defect PD-M11.1 fixed on the Plan screen.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import customtkinter as ctk  # noqa: E402
import pytest  # noqa: E402

from tests.weekly_tactic_fixtures import make_vps  # noqa: E402


@pytest.fixture
def root():
    win = ctk.CTk()
    win.withdraw()
    win.geometry("1400x900+0+0")
    yield win
    win.destroy()


@pytest.fixture
def vps(tmp_path):
    manager = make_vps(tmp_path)
    yield manager
    manager.close()


def _app(vps):
    app = MagicMock()
    app.vps_manager = vps
    return app


def _build(name, root, vps):
    from src.getmoredone.screens.all_items import AllItemsScreen
    from src.getmoredone.screens.completed import CompletedScreen
    from src.getmoredone.screens.hierarchical import HierarchicalScreen
    from src.getmoredone.screens.today import TodayScreen
    from src.getmoredone.screens.upcoming import UpcomingScreen
    from src.getmoredone.screens.vps_planning import VPSPlanningScreen

    if name == "vps_planning":
        return VPSPlanningScreen(root, vps, _app(vps))
    cls = {
        "today": TodayScreen,
        "upcoming": UpcomingScreen,
        "all_items": AllItemsScreen,
        "completed": CompletedScreen,
        "hierarchical": HierarchicalScreen,
    }[name]
    return cls(root, vps.db_manager, _app(vps))


@pytest.mark.parametrize(
    "name",
    ["today", "upcoming", "all_items", "completed", "hierarchical", "vps_planning"],
)
def test_lprm1_a_refresh_leaves_the_list_pane_in_the_grid(name, root, vps, monkeypatch):
    screen = _build(name, root, vps)
    screen.pack(fill="both", expand=True)
    screen.update_idletasks()
    removed = []
    monkeypatch.setattr(
        screen.scroll_frame, "grid_remove", lambda *a, **k: removed.append(1)
    )
    row = screen.scroll_frame.grid_info()["row"]

    screen.refresh()

    assert removed == [], f"{name}: the list pane was taken out of the grid to be rebuilt"
    assert screen.scroll_frame.grid_info()["row"] == row, screen.scroll_frame.grid_info()
