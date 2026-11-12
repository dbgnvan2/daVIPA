"""APE Week Assignment screen with month-to-week workflow."""

from __future__ import annotations

from datetime import date
from tkinter import messagebox
from typing import TYPE_CHECKING, Dict, List, Optional

import customtkinter as ctk
import tkinter as tk

from .. import week_options
from ..app_settings import AppSettings
from ..weekly_tactic_logging import get_weekly_tactic_logger
from ..theme import button_style, combo_box_style, semantic_colors, status_text_color
from .chip_table import (
    APE_LEFT_COLUMNS,
    WEEK_ASSIGNMENT_RIGHT_COLUMNS,
    ChipTable,
    panel_fitter,
    show_list_or_message,
)
from .lineage_filters import annual_plan_element_parts, weekly_tactic_parts
from .pick_record_dialog import describe_lineage, open_pick_record_dialog
from .row_drag import RowDragSource
from .segment_color_utils import (
    load_latest_lineage_color_maps,
    resolve_chip_colors,
)
from .split_panel import SPLITTER_WIDTH, SplitPanel
from .week_collision_notice import notify_weekly_tactic_changes

if TYPE_CHECKING:
    from ..app import GetMoreDoneApp
    from ..vps_manager import VPSManager

logger = get_weekly_tactic_logger()


class WeeklyItemsScreen(ctk.CTkFrame):
    """Assign month-selected Annual Plan Elements into weekly tactics."""

    # UPD-M5 — the divider position and each panel's column widths are this
    # screen's own: ``week_assignment_split_ratio``,
    # ``week_assignment_left_col_widths`` and ``..._right_col_widths``. The
    # column widths used to be the four class constants that stood here, which
    # is why the two panels could not be sized separately and why the numbers
    # drifted from the other tabs' (spec section 1.4).
    SETTINGS_PREFIX = "week_assignment"

    def __init__(self, parent, vps_manager: "VPSManager", app: "GetMoreDoneApp"):
        super().__init__(parent)
        self.vps_manager = vps_manager
        self.app = app
        self.settings = getattr(app, "settings", None) or AppSettings.load()

        self.week_options: List[str] = []
        self.week_var = ctk.StringVar(value="")
        self.segment_filter_var = ctk.StringVar(value="All")
        self.subsegment_filter_var = ctk.StringVar(value="All")
        self.category_filter_var = ctk.StringVar(value="All")

        self.left_items: List[Dict[str, object]] = []
        # What the right panel is showing. Three paths index it by row
        # position -- selection, double-click-to-open, the selected tint --
        # so it must stay in step with what is rendered, not with the week.
        self.right_items: List[Dict[str, object]] = []
        # The week's tactics before the tick filter: the "of M" in the
        # heading, and what the filter is applied to.
        self.all_right_items: List[Dict[str, object]] = []
        # The week the right panel is showing, so its heading does not have to
        # re-read a selector that can be mid-edit.
        self.shown_week_start = ""
        self.left_checks: dict[str, ctk.BooleanVar] = {}
        self.segment_colors = {}
        self.subsegment_colors = {}
        self.category_colors = {}

        self.selected_weekly_idx: Optional[int] = None
        self.selected_weekly_item: Optional[Dict[str, object]] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_ui()
        self.refresh()

    def create_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(12, weight=1)

        ctk.CTkLabel(
            header,
            text="APE Week Assignment",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=13, padx=(10, 20), pady=(8, 6), sticky="w")

        ctk.CTkLabel(header, text="Week Start:").grid(row=1, column=0, padx=(8, 5), pady=(0, 8), sticky="e")
        self.week_combo = ctk.CTkComboBox(header, width=136, values=[""], variable=self.week_var, **combo_box_style())
        self.week_combo.grid(row=1, column=1, padx=5, pady=(0, 8), sticky="w")

        ctk.CTkButton(header, text="Load", width=76, command=self.load_selected_week, **button_style("secondary")).grid(
            row=1, column=2, padx=5, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="This Week", width=86, command=self.jump_to_current_week, **button_style("secondary")).grid(
            row=1, column=3, padx=5, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Refresh", width=86, command=self.refresh, **button_style("secondary")).grid(
            row=1, column=5, padx=5, pady=(0, 8), sticky="w"
        )

        # UPD-F2 — the three filters sit on a row of their own, below the
        # row holding this tab's own controls, so every tab in the hub is the
        # same depth. They were on the controls row, which put eleven widgets
        # on one line and made the filters hard to find. A frame rather than
        # six more cells in the header's grid: the two rows then size their
        # columns independently, so a 160px combo does not stretch the column
        # the Week Start combo sits in.
        # Spec:  docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
        # Tests: tests/test_unified_panel_design.py::test_updf21_the_filters_are_on_their_own_row
        self.filter_row = ctk.CTkFrame(header, fg_color="transparent")
        self.filter_row.grid(row=2, column=0, columnspan=13, sticky="w",
                             padx=8, pady=(0, 8))

        ctk.CTkLabel(self.filter_row, text="Segment:").grid(row=0, column=0, padx=(0, 4), sticky="e")
        self.segment_filter_combo = ctk.CTkComboBox(
            self.filter_row,
            width=150,
            values=["All"],
            variable=self.segment_filter_var,
            command=lambda _v: self.on_filters_changed(),
            **combo_box_style(),
        )
        self.segment_filter_combo.grid(row=0, column=1, padx=4, sticky="w")

        ctk.CTkLabel(self.filter_row, text="Sub:").grid(row=0, column=2, padx=(8, 4), sticky="e")
        self.subsegment_filter_combo = ctk.CTkComboBox(
            self.filter_row,
            width=150,
            values=["All"],
            variable=self.subsegment_filter_var,
            command=lambda _v: self.on_filters_changed(),
            **combo_box_style(),
        )
        self.subsegment_filter_combo.grid(row=0, column=3, padx=4, sticky="w")

        ctk.CTkLabel(self.filter_row, text="Cat:").grid(row=0, column=4, padx=(8, 4), sticky="e")
        self.category_filter_combo = ctk.CTkComboBox(
            self.filter_row,
            width=150,
            values=["All"],
            variable=self.category_filter_var,
            command=lambda _v: self.on_filters_changed(),
            **combo_box_style(),
        )
        self.category_filter_combo.grid(row=0, column=5, padx=4, sticky="w")

        # Row 3, not the controls row: every other tab in the hub puts its
        # status line under the filters, and this one had it beside them.
        self.status_label = ctk.CTkLabel(header, text="", text_color=status_text_color("muted"))
        self.status_label.grid(row=3, column=0, columnspan=13, sticky="w", padx=10, pady=(0, 8))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=0, minsize=520)
        body.grid_columnconfigure(1, weight=0, minsize=SPLITTER_WIDTH)
        body.grid_columnconfigure(2, weight=0, minsize=520)
        body.grid_rowconfigure(1, weight=1)
        self.body = body

        self.left_title_label = ctk.CTkLabel(body, text="Month-assigned Annual Plan Elements", font=ctk.CTkFont(weight="bold"))
        self.left_title_label.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        self.right_title_label = ctk.CTkLabel(body, text="Weekly Tactics", font=ctk.CTkFont(weight="bold"))
        self.right_title_label.grid(row=0, column=2, sticky="w", padx=8, pady=(8, 4))

        # UPD-M5 — each panel is a plain frame holding the scroll frame the
        # shared table owns and, in the same cell, the empty-state label. The
        # table destroys every child of its container (chip_table's class
        # docstring says so), so the label cannot live inside it.
        self.left_frame = ctk.CTkFrame(body)
        self.left_frame.grid(row=1, column=0, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=1)

        self.left_list = ctk.CTkScrollableFrame(self.left_frame, label_text="")
        self.left_list.grid(row=0, column=0, sticky="nsew")
        self.left_list.grid_columnconfigure(0, weight=1)

        self.left_empty = ctk.CTkLabel(
            self.left_frame,
            text="No month-assigned Annual Plan Elements match the current week/filter.",
            text_color=status_text_color("muted"),
        )
        self.left_empty.grid(row=0, column=0, pady=20, padx=10, sticky="nw")

        divider = ctk.CTkFrame(
            body,
            width=SPLITTER_WIDTH,
            corner_radius=999,
            fg_color=semantic_colors()["border"],
            cursor="sb_h_double_arrow",
        )
        divider.grid(row=1, column=1, sticky="ns", padx=4, pady=4)
        self.divider = divider

        self.right_frame = ctk.CTkFrame(body)
        self.right_frame.grid(row=1, column=2, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

        self.right_list = ctk.CTkScrollableFrame(self.right_frame, label_text="")
        self.right_list.grid(row=0, column=0, sticky="nsew")
        self.right_list.grid_columnconfigure(0, weight=1)

        self.right_empty = ctk.CTkLabel(
            self.right_frame,
            text="No weekly tactics exist for the selected week yet.",
            text_color=status_text_color("muted"),
        )
        self.right_empty.grid(row=0, column=0, pady=20, padx=10, sticky="nw")

        # VTF-M5.4 — one button under the right panel. The two it replaced
        # were second routes to the row's own controls: Delete Weekly called
        # the same `delete_weekly_row` as the row's Delete, and Edit Weekly
        # Tactic opened the same editor as a double-click. Add Action Item
        # created an Action Item this panel cannot display; that button
        # belongs to the Week Actions tab, which has it.
        right_actions = ctk.CTkFrame(self.right_frame)
        right_actions.grid(row=1, column=0, sticky="w", padx=4, pady=(6, 4))
        self.right_actions = right_actions
        ctk.CTkButton(
            right_actions,
            text="Add Weekly Tactic",
            command=self.open_add_dialog,
            width=170,
            **button_style("primary"),
        ).pack(side="left", padx=6, pady=6)

        # UPD-M5 — one table per panel, from screens/chip_table.py. The two
        # panels take the same column sets as the other APE tabs, so the three
        # tabs now show the same widths and all of them are draggable.
        self.left_table = ChipTable(
            self.left_list, self.settings,
            f"{self.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS,
        )
        self.right_table = ChipTable(
            self.right_list, self.settings,
            f"{self.SETTINGS_PREFIX}_right", WEEK_ASSIGNMENT_RIGHT_COLUMNS,
        )

        # UPD-M1 — the ratio, the clamp and the four handlers live in
        # screens/split_panel.py, which also persists the position this screen
        # used to forget on every rebuild.
        self.split = SplitPanel(
            body,
            self.left_frame,
            divider,
            settings=self.settings,
            prefix=self.SETTINGS_PREFIX,
            # UPD-F4 — the divider hands each panel's new width to that
            # panel's columns, so moving it widens or narrows the columns
            # instead of leaving empty space beside the last one.
            on_apply=panel_fitter(self.left_table, self.right_table),
        )

        # UPD-M2 — the press, the release and the descendant walk live in
        # screens/row_drag.py. What a dropped row means is this screen's.
        self.row_drag = RowDragSource(
            self, self.right_list, self._assign_dragged_row
        )

    def refresh(self):
        self.segment_colors, self.subsegment_colors = load_latest_lineage_color_maps(self.vps_manager)
        self.category_colors = {
            ((r.get("segment_name", "") or "").strip().lower(), (r.get("subsegment_name", "") or "").strip().lower(), (r.get("name", "") or "").strip().lower()): (r.get("color_hex") or "")
            for r in self.vps_manager.get_vision_categories()
        }
        weekly_items = self.vps_manager.get_weekly_action_items(ape_only=True)
        existing_starts = sorted({wi["start_date"] for wi in weekly_items if wi.get("start_date")}, reverse=True)
        self.week_options = self._build_selectable_week_options(existing_starts)
        self.week_combo.configure(values=self.week_options or [""])
        if self.week_var.get() not in self.week_options:
            self.week_var.set(self.week_options[0] if self.week_options else "")
        self.load_selected_week()

    def load_selected_week(self):
        parsed = self._selected_week_context()
        if not parsed:
            self.left_items = []
            self.right_items = []
            self.all_right_items = []
            self.shown_week_start = ""
            self._render_lists()
            self.status_label.configure(text="Choose a Week Start.")
            return

        week_start, year, month = parsed
        self.left_items = self.vps_manager.get_annual_plan_elements_for_month(year, month)
        all_weekly_items = self.vps_manager.get_weekly_action_items(week_start_date=week_start, ape_only=True)

        self._refresh_filter_options(self.left_items, all_weekly_items)
        self.left_items = [row for row in self.left_items if self._ape_matches_filters(row)]
        # VTF-M2.1 — the three dropdowns are the left panel's filter only.
        # The right panel is filtered by the ticks (VTF-M1.4), applied in
        # `_render_lists` after the checkboxes have been rebuilt.
        self.all_right_items = list(all_weekly_items)
        # Loading a week rebuilds every checkbox, so no tick survives it and
        # the panel shows the whole week. Set here as well as in
        # `_render_lists` so the status line below never reads the previous
        # week's list.
        self.right_items = list(all_weekly_items)
        self.shown_week_start = week_start

        self.selected_weekly_idx = None
        self.selected_weekly_item = None
        self._render_lists()
        self.left_title_label.configure(
            text=f"Month-assigned APEs for {year}-{month:02d} "
                 "(tick to filter the tactics on the right)")
        self.right_title_label.configure(text=self._right_title())
        self.status_label.configure(text=f"{len(self.left_items)} month item(s) on left, {len(self.right_items)} weekly tactic(s) on right")

    def jump_to_current_week(self):
        current_week_start = self._week_start_for(date.today()).isoformat()
        if current_week_start in self.week_options:
            self.week_var.set(current_week_start)
            self.load_selected_week()

    def _selected_week_context(self) -> Optional[tuple[str, int, int]]:
        """The week start and the year and month it falls in.

        Purpose: give every caller on this screen one reading of the selected
                 week.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m1
        Tests:   tests/test_ape_period_consistency.py::test_apcm14_week_context_carries_no_derived_quarter

        APC-M1.4 — no quarter. This used to derive one with
        ``((month - 1) // 3) + 1`` so the left-panel lookup could demand the
        matching quarter flag as well as the month flag. The lookup matches on
        the month alone now (APC-M4.1), and no other caller here ever read the
        quarter, so the derivation is gone rather than re-pointed at the shared
        mapping.
        """
        week_start = self.week_var.get().strip()
        if not week_start:
            return None
        week_date = date.fromisoformat(week_start)
        return week_start, week_date.year, week_date.month

    def _first_day_of_week(self) -> int:
        return week_options.first_day_of_week(self.app)

    def _week_start_for(self, target_date: date) -> date:
        """WT-M2.B — week identity comes from the one helper, not local arithmetic."""
        return week_options.week_start_for(target_date, self._first_day_of_week())

    def _build_selectable_week_options(self, existing_starts: List[str]) -> List[str]:
        """The picker's week starts, from the shared helper.

        ``date.today()`` is resolved here rather than inside the helper, which
        keeps the helper pure and keeps this module the one place a test has
        to pin the clock.
        Spec:  docs/spec_2026-11-07_ape_week_actions.md#4
        Tests: tests/test_weekly_items_week_options.py
        """
        return week_options.selectable_week_options(
            date.today(), existing_starts, self._first_day_of_week()
        )

    def _refresh_filter_options(self, left_rows: List[Dict[str, object]], right_rows: List[Dict[str, object]]):
        combined_parts = [self._ape_parts(row) for row in left_rows] + [self._weekly_parts(row) for row in right_rows]
        seg_values = sorted({part[0] for part in combined_parts if part[0] and part[0] != "-"}, key=str.lower)
        sub_values = sorted({part[1] for part in combined_parts if part[1] and part[1] != "-"}, key=str.lower)
        cat_values = sorted({part[2] for part in combined_parts if part[2] and part[2] != "-"}, key=str.lower)
        self._configure_filter_combo(self.segment_filter_combo, self.segment_filter_var, ["All"] + seg_values)
        self._configure_filter_combo(self.subsegment_filter_combo, self.subsegment_filter_var, ["All"] + sub_values)
        self._configure_filter_combo(self.category_filter_combo, self.category_filter_var, ["All"] + cat_values)

    @staticmethod
    def _configure_filter_combo(combo: ctk.CTkComboBox, variable: ctk.StringVar, values: List[str]):
        current = variable.get().strip() or "All"
        if current not in values:
            current = "All"
            variable.set(current)
        combo.configure(values=values)

    def on_filters_changed(self):
        self.load_selected_week()

    # --------------------------------------------------- VTF-M3: Add New

    def _add_options(self) -> list:
        """The month's APEs on the left, as the dialog's options (VTF-M3.4).

        `left_items` is the list the dropdowns have already narrowed, so the
        dialog offers what the left panel is showing. None is excluded: one
        APE can carry a tactic in several weeks, and
        `create_week_action_items_for_ape` reports a collision itself.
        """
        return [
            (row["id"], describe_lineage(row))
            for row in self.left_items if row.get("id")
        ]

    def _add_default(self):
        """The ticked row to open the dialog on, when exactly one is ticked.

        VTF-M3.6 — one tick is an unambiguous intention; two are not.
        """
        ticked = self._ticked_ape_ids()
        return next(iter(ticked)) if len(ticked) == 1 else None

    def _create_tactic_for(self, ape_id) -> str:
        """Create one weekly tactic for the selected week, and say what happened.

        Purpose: VTF-M3.4 — the one write both remaining paths share. The
                 drag path and the Add New dialog had the same four lines,
                 including the `ValueError` that is a stale APE or a bad
                 month; two copies is where one of them stops reporting
                 collisions (P5).
        Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
        Tests:   tests/test_vsp_tab_adds.py::test_vtfm34_the_week_tab_adds_a_weekly_tactic
                 tests/test_weekly_tactic_schema.py::test_wt_m1c3_both_creation_paths_report_collisions
        """
        parsed = self._selected_week_context()
        if not parsed:
            return "Choose a Week Start first."
        week_start, year, month = parsed
        try:
            result = self.vps_manager.create_week_action_items_for_ape(
                ape_id, year, month, [week_start])
        except Exception as exc:
            # A stale APE or a bad month raises ValueError; a locked database
            # raises sqlite3.OperationalError. Only ValueError was caught
            # until 2026-11-11, and the drag path has no `try` above this one
            # (`row_drag.finish` calls `on_drop` raw), so anything else was a
            # traceback on stderr and nothing on screen (P1/P5).
            logger.exception("[weekly_items] create failed: %s", exc)
            return f"Could not create the weekly tactic: {exc}"
        # Always refresh and always say what happened: a create that collided
        # used to produce no refresh, no status and no sign of rejection.
        self.refresh()
        return self._describe_week_creation(
            int(result.get("created_count", 0)),
            int(result.get("skipped_count", 0)),
            int(result.get("collided_count", 0)),
        )

    def open_add_dialog(self):
        """VTF-M3.4/M5.4 — pick a parent APE and add a tactic for the week."""
        parsed = self._selected_week_context()
        if not parsed:
            self.status_label.configure(text="Choose a Week Start first.")
            return None
        week_start, _year, _month = parsed
        return open_pick_record_dialog(
            self,
            title="Add Weekly Tactic",
            prompt=f"Which Annual Plan Element is the tactic for {week_start}?",
            options=self._add_options(),
            initial=self._add_default(),
            confirm_text="Add Tactic",
            report=lambda text: self.status_label.configure(text=text),
            on_confirm=self._create_tactic_for,
            empty_message=(
                "No month-assigned APEs are listed on the left. Assign one to "
                "this month on the APE Month Assignment tab first."),
        )

    @staticmethod
    def _describe_week_creation(created: int, skipped: int, collided: int) -> str:
        """WT-M1.C.3 — one wording for every path that creates weekly tactics.

        Spec:  docs/spec_2026-08-18_weekly_tactic_scheduling.md#wt-m1c3
        Tests: tests/test_weekly_tactic_schema.py::test_wt_m1c3_both_creation_paths_report_collisions

        Both callers of ``create_week_action_items_for_ape`` report through here.
        Hardening only the button and leaving the drag silent is the sibling
        problem P5 describes — and the drag was the one that showed nothing at
        all when a week was refused.
        """
        status = f"Created {created} weekly tactic(s); skipped {skipped} existing item(s)."
        if collided:
            status += f" {collided} already existed for that week and were not duplicated."
        return status

    def _render_lists(self):
        """Render both panels, left first.

        `_render_left_rows` rebuilds `left_checks` from scratch, so the right
        panel's tick filter is applied after it: computing it first would
        filter by the checkboxes of the render before this one.
        """
        self.left_checks = {}
        self._render_left_rows()
        self.right_items = self._visible_right_items()
        self._render_right_rows()

    # ------------------------------------------------ the tick as a filter

    def _ticked_ape_ids(self) -> set:
        """The ids of the ticked rows the left panel is currently showing.

        `left_items` is already narrowed by the dropdowns by the time it is
        rendered, and `_render_lists` rebuilds every checkbox, so a dropdown
        change clears the ticks with the rows: there is no tick here that the
        user cannot see (VTF-M1.9).
        """
        visible = {row.get("id") for row in self.left_items}
        return {
            key for key, var in self.left_checks.items()
            if key in visible and var.get()
        }

    def _visible_right_items(self) -> List[Dict[str, object]]:
        """The week's tactics the current ticks allow.

        A weekly tactic names its parent APE in `annual_plan_element_id`, so
        ticking APEs on the left shows their tactics for the week (VTF-M1.4).
        No tick is no filter (VTF-M1.5).
        """
        ticked = self._ticked_ape_ids()
        if not ticked:
            return list(self.all_right_items)
        return [
            row for row in self.all_right_items
            if row.get("annual_plan_element_id") in ticked
        ]

    def refresh_right_panel(self):
        """Re-render the right panel alone, from the ticks.

        Purpose: VTF-M1.6 — the checkbox's own command, so a tick takes
                 effect without Load Week or Refresh. The left panel is not
                 re-rendered (VTF-M1.8); rebuilding it would destroy the
                 checkbox that is mid-click and clear every tick.
        Tests:   tests/test_vsp_tab_filters.py::test_vtfm14_the_week_tab_right_panel_follows_the_ticks

        The selection is dropped: it is held as a row *index* into
        `right_items`, so a filter that changes which rows are listed would
        leave it pointing at a different tactic. APE Week Actions already
        clears its right panel when a filter hides the selected tactic.
        """
        self.selected_weekly_idx = None
        self.selected_weekly_item = None
        self.right_items = self._visible_right_items()
        self.right_title_label.configure(text=self._right_title())
        self._render_right_rows()

    def _right_title(self) -> str:
        """The right panel's heading, which says when a filter is narrowing it."""
        base = f"Weekly Tactics for {self.shown_week_start}"
        if len(self.right_items) == len(self.all_right_items):
            return base
        return (f"{base} ({len(self.right_items)} of "
                f"{len(self.all_right_items)}, filtered by tick)")

    @staticmethod
    def _show_list_or_message(list_frame, message, empty: bool) -> None:
        """Show the panel's list or its empty-state label, never both.

        Purpose: UPD-M5.6 — the shared table owns its scroll frame outright,
                 so the "nothing here" label sits in the same grid cell beside
                 it rather than inside it, and exactly one of the two is
                 gridded at a time.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m5
        Tests:   tests/test_unified_panel_design.py::test_updm56_both_panels_still_say_when_they_are_empty

        UPD-M6 moved the body into `chip_table.show_list_or_message`, where
        APE Week Actions' left panel needs the same swap. This stays as the
        seam the two render methods and their tests call.
        """
        show_list_or_message(list_frame, message, empty)

    def _render_left_rows(self):
        """Render the month-assigned APEs into the shared chip table.

        Purpose: UPD-M5.6 — the header, the row frames, the chips and the
                 column widths come from screens/chip_table.py. The checkbox
                 cell and the drag binding stay here, because what they do is
                 this screen's.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m5
        Tests:   tests/test_unified_panel_design.py::test_updm55_left_header_matches_the_other_tabs
        """
        empty = not self.left_items
        self._show_list_or_message(self.left_list, self.left_empty, empty)
        if empty:
            self.left_table.clear()
            return

        self.left_table.build_header()
        for idx, row in enumerate(self.left_items, start=1):
            segment_name, subsegment_name, category_name = self._ape_parts(row)
            segment_color, subsegment_color, category_color = self._row_colors(
                segment_name, subsegment_name, category_name)

            item, cells = self.left_table.add_row(
                {
                    "index": str(idx),
                    "segment": segment_name,
                    "subsegment": subsegment_name,
                    "category": category_name,
                },
                {
                    "segment": segment_color,
                    "subsegment": subsegment_color,
                    "category": category_color,
                },
            )

            checked = ctk.BooleanVar(value=False)
            self.left_checks[row["id"]] = checked
            ctk.CTkCheckBox(
                item, text="", variable=checked, width=20,
                command=self.refresh_right_panel,
            ).grid(
                row=0, column=self.left_table.grid_col("checkbox"),
                padx=2, pady=5, sticky="w",
            )
            self.row_drag.bind_row(
                (item, cells["index"], cells["segment"],
                 cells["subsegment"], cells["category"]),
                row,
            )

    def _render_right_rows(self):
        """Render the week's tactics, each with its own Delete.

        Purpose: UPD-M5.1, UPD-M5.2 — the right panel is a table in the same
                 shape as the other tabs' and each row carries the Delete the
                 image has in an Actions column. Selection and
                 double-click-to-open are re-bound here; the table knows
                 nothing about either.

                 WTP-M6.4 — each row also shows ``n/m`` in a Done column, from
                 ``count_open_children_for_weekly_tactic``: a tactic is a
                 parent now, so its row says how much of the week under it is
                 finished. The number comes from the helper, not from a count
                 taken here, so this panel and the Week Actions tactic list
                 cannot disagree about one week (WTP-M6.5 reads the same one).
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m5
                 docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m6
        Tests:   tests/test_unified_panel_design.py::test_updm51_right_panel_has_the_actions_column
                 tests/test_weekly_tactic_parent.py::test_wtpm64_week_assignment_row_shows_progress
        """
        empty = not self.right_items
        self._show_list_or_message(self.right_list, self.right_empty, empty)
        if empty:
            self.right_table.clear()
            return

        palette = semantic_colors()
        self.right_table.build_header()
        for idx, row in enumerate(self.right_items, start=1):
            segment_name, subsegment_name, category_name = self._weekly_parts(row)
            segment_color, subsegment_color, category_color = self._row_colors(
                segment_name, subsegment_name, category_name)
            bg = palette["selected_tint"] if idx - 1 == self.selected_weekly_idx else None

            done, total = self.vps_manager.count_open_children_for_weekly_tactic(
                row["id"])
            item, cells = self.right_table.add_row(
                {
                    "index": str(idx),
                    "segment": segment_name,
                    "subsegment": subsegment_name,
                    "category": category_name,
                    "progress": f"{done}/{total}" if total else "—",
                },
                {
                    "segment": segment_color,
                    "subsegment": subsegment_color,
                    "category": category_color,
                },
                fg_color=bg,
                border_width=2,
                border_color=segment_color,
            )

            ctk.CTkButton(
                item,
                text="Delete",
                width=72,
                command=lambda r=row: self.delete_weekly_row(r),
                **button_style("danger"),
            ).grid(row=0, column=self.right_table.grid_col("actions"),
                   padx=5, pady=5, sticky="e")

            for widget in (item, cells["index"], cells["segment"],
                           cells["subsegment"], cells["category"],
                           cells["progress"]):
                widget.bind("<Button-1>", lambda _e, i=idx - 1: self.on_select_weekly_item(i))
                widget.bind("<Double-Button-1>", lambda _e, i=idx - 1: self._open_weekly_from_index(i))

    def _row_colors(self, segment_name: str, subsegment_name: str,
                    category_name: str) -> tuple[str, str, str]:
        """The three chip colours for one row.

        The same four lines were written out in both render methods; the
        category lookup in particular is a three-part lower-cased key that is
        easy to get subtly wrong in one copy and not the other (P5). UPD-M6
        moved the body into `segment_color_utils.resolve_chip_colors`, which
        APE Week Actions' rows need too; this stays as this screen's seam.
        """
        return resolve_chip_colors(
            segment_name, subsegment_name, category_name, self.vps_manager,
            self.segment_colors, self.subsegment_colors, self.category_colors,
        )

    def on_select_weekly_item(self, idx: int):
        if idx < 0 or idx >= len(self.right_items):
            return
        self.selected_weekly_idx = idx
        self.selected_weekly_item = self.right_items[idx]
        self._render_right_rows()

    def _open_weekly_from_index(self, idx: int):
        self.on_select_weekly_item(idx)
        self.open_selected_weekly_item()

    def create_action_item_for_selected_weekly(self):
        if not self.selected_weekly_item:
            messagebox.showwarning("No Weekly Item Selected", "Select a weekly tactic on the right first.")
            return

        from ..models import ActionItem

        dialog = ctk.CTkInputDialog(text="Immediate Step:", title="New Related Action")
        title = (dialog.get_input() or "").strip()
        if not title:
            return

        # BP6 — the title is what the user typed, not "<tactic context> - <it>".
        # No screen has offered a Context field since PL-era; the prefix was a
        # third-choice lineage fallback that ``lineage_for_item`` never reaches
        # for these rows, because they carry both an Annual Plan Element and a
        # parent. It only ever fired for a legacy-shaped tactic title.
        # Spec:  docs/unused-docs/implementation_plan_2026-08-19_backlog_clearance.md#bp6
        # Tests: tests/test_weekly_items_title.py
        weekly = self.selected_weekly_item
        item = ActionItem(
            who=weekly.get("who") or "",
            title=title,
            description=f"Related to weekly item: {weekly.get('title') or ''}",
            # AWA-A1 — the link is `weekly_tactic_id`, as the APE Week Actions
            # tab's own Add writes it. `parent_id` alone left
            # `weekly_tactic.tactic_of` — the one predicate WT-M3.D.1 names as
            # the authority on "is this item week-filed" — answering no for
            # every row this button made, so two buttons on two tabs produced
            # two row shapes for one relationship. `parent_of` still answers
            # the tactic, because it falls back to `tactic_of`, so the tree is
            # unchanged. Closes AWA-A3's remainder.
            #
            # Not *both* columns, which is what the spec's recommendation and
            # the backlog entry proposed: `migrate_parent_links_to_weekly_tactic`
            # runs from `Database.initialize_schema` on every launch and clears
            # `parent_id` on a row that already names a tactic explicitly
            # (`kept_explicit_link`), so a row written with both is rewritten
            # at the next launch and logs a write to the user's data for every
            # item this button ever made. One column is the shape the app keeps.
            # Spec:  docs/spec_2026-11-07_ape_week_actions.md#awa-m5
            # Tests: tests/test_weekly_items_tactic_link.py::test_awaa1_the_add_button_links_by_weekly_tactic_id
            weekly_tactic_id=weekly["id"],
            start_date=weekly.get("start_date"),
            due_date=weekly.get("start_date"),
            category=weekly.get("category"),
            annual_plan_element_id=weekly.get("annual_plan_element_id"),
            item_type="daily",
        )
        self.app.db_manager.create_action_item(item, apply_defaults=False)
        # Writing the tactic link puts this create on the re-file cascade
        # (`create_action_item`'s `refile` defaults True, and it acts when
        # `tactic_of` answers), which can refuse a week or build plan records
        # and records what it did on the manager. Fourteen other screens
        # report that; this one had nothing to report because it never
        # re-filed, and reporting success over a swept-away report is the
        # defect its sibling in `week_actions.py` already fixed (P5, P2).
        notify_weekly_tactic_changes(self.app.db_manager, self)
        self.status_label.configure(text="Added a related Action Item for the selected weekly tactic.")

    def open_selected_weekly_item(self):
        if not self.selected_weekly_item:
            messagebox.showwarning("No Weekly Item Selected", "Select a weekly tactic on the right first.")
            return
        from .item_editor import ItemEditorDialog
        ItemEditorDialog(self, self.app.db_manager, item_id=self.selected_weekly_item["id"], vps_manager=self.vps_manager, on_close_callback=self.on_weekly_editor_closed)

    def delete_selected_weekly_item(self):
        """The Delete Weekly button: delete whatever is selected."""
        if not self.selected_weekly_item:
            messagebox.showwarning("No Weekly Item Selected", "Select a weekly tactic on the right first.")
            return
        self.delete_weekly_row(self.selected_weekly_item)

    def delete_weekly_row(self, row: Dict[str, object]):
        """Delete one weekly tactic, after asking — naming what will go with it.

        Purpose: UPD-M5.2, UPD-M5.3 — the row's own Delete button and the
                 Delete Weekly button below the list are two ways to delete
                 the same thing, so they are one method with two callers
                 rather than two copies of the confirmation (P5). A refused
                 confirmation deletes nothing and says nothing.

                 WTP-M5.2 — the confirmation names the count. WTP-M5.3 widened
                 what this delete destroys: a tactic is a parent now, so the
                 cascade takes the items linked by ``weekly_tactic_id`` as well
                 as the ``parent_id`` children, and their own subtasks. "and
                 related action items" was already vague; against the wider
                 delete it understates it. The number comes from
                 ``children_to_delete_with_weekly_tactic``, which returns the
                 ids the cascade will actually delete — the same list, not a
                 second count of the same thing (P6: the figure shown is read
                 off the work that will be done).
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m5
                 docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m5
        Tests:   tests/test_unified_panel_design.py::test_updm53_delete_is_confirmed_before_it_happens
                 tests/test_weekly_tactic_parent.py::test_wtpm52_confirmation_names_the_child_count
        """
        title = (row.get("title") or "this weekly tactic").strip()
        doomed = self.vps_manager.children_to_delete_with_weekly_tactic(row["id"])
        if doomed:
            count = len(doomed)
            noun = "Action Item" if count == 1 else "Action Items"
            prompt = (
                f"Delete {title}?\n\n"
                f"This will also delete {count} {noun} filed under it. "
                f"This cannot be undone."
            )
        else:
            prompt = f"Delete {title}?\n\nNo Action Items are filed under it."
        if not messagebox.askyesno("Delete Weekly Tactic", prompt, icon="warning"):
            return
        if self.vps_manager.delete_weekly_action_item(row["id"]):
            self.refresh()
        else:
            messagebox.showerror("Delete Failed", "Weekly tactic could not be deleted.")

    def on_weekly_editor_closed(self):
        self.refresh()

    def _assign_dragged_row(self, row: Dict[str, object]):
        """Create a weekly tactic from an APE dropped on the right panel.

        Purpose: UPD-M2.2 — the press, the release and the drop test live in
                 screens/row_drag.py; this is the body of what was
                 _finish_row_drag's final `if`, moved as it was.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m5
        Tests:   tests/test_weekly_tactic_schema.py::test_wt_m1c3_both_creation_paths_report_collisions
        """
        if not self._selected_week_context():
            # The dialog says the same thing on the same input; the drag path
            # used to do nothing at all for it.
            self.status_label.configure(
                text="Select a Week Start before dragging an Annual Plan Element."
            )
            return
        self.status_label.configure(text=self._create_tactic_for(row["id"]))

    def _ape_matches_filters(self, row: Dict[str, object]) -> bool:
        seg, sub, cat = self._ape_parts(row)
        return self._parts_match_filters(seg, sub, cat)

    def _parts_match_filters(self, seg_name: str, sub_name: str, cat_name: str) -> bool:
        seg = self.segment_filter_var.get().strip()
        sub = self.subsegment_filter_var.get().strip()
        cat = self.category_filter_var.get().strip()
        if seg and seg != "All" and seg_name != seg:
            return False
        if sub and sub != "All" and sub_name != sub:
            return False
        if cat and cat != "All" and cat_name != cat:
            return False
        return True

    # Both readers moved into screens/lineage_filters.py at UPD-M6, where APE
    # Week Actions reads the same Weekly Tactic rows. The `ape_*` keys and the
    # `who` fall-back are one rule and now have one owner; these stay as the
    # seams this screen's render and filter paths call.

    @staticmethod
    def _ape_parts(row: Dict[str, object]) -> tuple[str, str, str]:
        return annual_plan_element_parts(row)

    def _weekly_parts(self, row: Dict[str, object]) -> tuple[str, str, str]:
        return weekly_tactic_parts(row)
