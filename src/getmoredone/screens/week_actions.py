"""APE Week Actions — the Action Items hanging off a week's Weekly Tactics.

Purpose: the Weekly Tactics for a chosen week on the left; selecting one shows
         its Action Items on the right, in the same list the Today screen
         draws, with the same row behaviours.
Spec:    docs/spec_2026-11-07_ape_week_actions.md
Tests:   tests/test_ape_week_actions.py

The right panel is a ``TodayScreen`` subclass rather than a copy of it. Today's
``load_items`` and ``create_item_row`` are generic — they work on any list of
``ActionItem`` — and every row behaviour the tab needs (edit, complete, timer,
the three inline editors, push) is already there and already generic. AWA-M6
cut the three seams that were about *today* rather than about a list; this file
overrides those three and nothing else.
"""

from __future__ import annotations

from datetime import date
from tkinter import messagebox
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import customtkinter as ctk

from .. import week_options
from ..app_settings import AppSettings
from ..models import ActionItem
from ..theme import button_style, combo_box_style, semantic_colors, status_text_color
from .chip_table import (
    WEEK_ACTIONS_LEFT_COLUMNS,
    ChipTable,
    show_list_or_message,
)
from .lineage_filters import LineageFilters, weekly_tactic_parts
from .segment_color_utils import (
    load_category_color_map,
    load_latest_lineage_color_maps,
    resolve_chip_colors,
)
from .split_panel import MIN_PANEL_WIDTH, SPLITTER_WIDTH, SplitPanel
from .today import TodayScreen
from .week_collision_notice import notify_weekly_tactic_changes

if TYPE_CHECKING:
    from ..app import GetMoreDoneApp
    from ..vps_manager import VPSManager


class WeekTacticActionsPanel(TodayScreen):
    """Today's list, filtered by Weekly Tactic instead of by today's date.

    Purpose: AWA-M5 — the Action Items panel the request asked to "work like
             the Today tab except it's filtered by the weekly tactic vs.
             today's date".
    Spec:    docs/spec_2026-11-07_ape_week_actions.md#awa-m5
    Tests:   tests/test_ape_week_actions.py::test_awam51_right_panel_subclasses_today
    """

    # AWA-M5.5 — its own width store, so dragging this panel's Title divider
    # does not move the Today screen's column, and vice versa.
    COLUMN_PREFIX = "week_actions"

    # AWA-M5.7 — what the list says before anything is selected. Replaced per
    # selection by ``set_tactic``, which names the tactic (AWA-M5.6).
    EMPTY_TEXT = "Select a Weekly Tactic on the left to see its Action Items."

    # Set before ``TodayScreen.__init__`` reaches ``load_items``, which calls
    # ``get_todays_items`` below while there is still no selection.
    selected_tactic: Optional[Dict[str, Any]] = None

    def get_todays_items(self) -> List[ActionItem]:
        """The selected tactic's Action Items — AWA-M5.2.

        Overrides Today's only date filter. This panel reads no clock at all:
        a completed child shows whatever day it was completed on (D6), because
        "completed today" has no meaning once the list is filtered by tactic.
        Spec:  docs/spec_2026-11-07_ape_week_actions.md#awa-m5
        Tests: tests/test_ape_week_actions.py::test_awam58_completed_children_are_not_date_filtered
        """
        if not self.selected_tactic:
            return []
        return self.app.vps_manager.get_action_items_for_weekly_tactic(
            self.selected_tactic["id"]
        )

    # ------------------------------------------------------------------ toolbar

    def _build_toolbar(self, parent):
        """Row 0: which tactic is showing, and Add Action Item.

        Replaces Today's search / Expand / Top 3 / + New Item / Refresh row.
        None of those five belongs above a list of one tactic's children.
        Spec:  docs/spec_2026-11-07_ape_week_actions.md#awa-m6
        Tests: tests/test_ape_week_actions.py::test_awam53_row_behaviours_are_inherited_not_copied
        """
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        bar.grid_columnconfigure(1, weight=1)
        self.toolbar_frame = bar

        self.heading_label = ctk.CTkLabel(
            bar,
            text="Action Items",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        self.heading_label.grid(row=0, column=0, sticky="w")

        self.add_button = ctk.CTkButton(
            bar,
            text="Add Action Item",
            width=140,
            command=self.add_action_item,
            **button_style("primary"),
        )
        self.add_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

    # ---------------------------------------------------------------- selection

    def set_tactic(self, tactic: Optional[Dict[str, Any]]):
        """Show one tactic's children, or the prompt when given nothing.

        AWA-M5.6 names the tactic in the empty state; AWA-M5.7 makes "nothing
        selected" a prompt rather than an error.
        Spec:  docs/spec_2026-11-07_ape_week_actions.md#awa-m5
        Tests: tests/test_ape_week_actions.py::test_awam56_empty_state_names_the_tactic
        """
        self.selected_tactic = dict(tactic) if tactic else None
        if self.selected_tactic:
            title = (self.selected_tactic.get("title") or "this tactic").strip()
            self.EMPTY_TEXT = f"No Action Items on “{title}” yet."
            self.heading_label.configure(text=f"Action Items — {title}")
        else:
            # Back to the class default, not a second copy of the wording.
            self.EMPTY_TEXT = type(self).EMPTY_TEXT
            self.heading_label.configure(text="Action Items")
        self.load_items()

    # ------------------------------------------------------------------- adding

    def _prompt_for_title(self) -> Optional[str]:
        """Ask for the new item's title. Overridden in tests."""
        dialog = ctk.CTkInputDialog(
            text="Action Item title:", title="New Action Item")
        return dialog.get_input()

    def add_action_item(self):
        """Create an Action Item on the selected tactic, then open the editor.

        D5 — ``ItemEditorDialog`` has no seed parameter for a tactic link, so a
        new unsaved item cannot be pre-linked inside it. The row is created
        with the link already on it and the editor opens on that row, which
        needs no change to a dialog nine screens use.

        AWA-M5.4 — the link is written as ``weekly_tactic_id``, the column
        ``weekly_tactic_migrations.py`` exists to keep apart from ordinary
        nesting. The sibling screen's button writes ``parent_id`` instead;
        that split is AWA-A1.
        Spec:  docs/spec_2026-11-07_ape_week_actions.md#awa-m5
        Tests: tests/test_ape_week_actions.py::test_awam54_add_action_item_links_by_weekly_tactic_id
        """
        if not self.selected_tactic:
            messagebox.showwarning(
                "No Weekly Tactic Selected",
                "Select a Weekly Tactic on the left first.",
            )
            return

        title = (self._prompt_for_title() or "").strip()
        if not title:
            return

        tactic = self.selected_tactic
        week_start = tactic.get("start_date")
        item = ActionItem(
            who=tactic.get("who") or "",
            title=title,
            description=f"Related to weekly tactic: {tactic.get('title') or ''}",
            weekly_tactic_id=tactic["id"],
            start_date=week_start,
            due_date=week_start,
            category=tactic.get("category"),
            annual_plan_element_id=tactic.get("annual_plan_element_id"),
            item_type="daily",
        )
        self.db_manager.create_action_item(item, apply_defaults=False)
        # The create re-files into the Weekly Tactic (`refile` defaults True),
        # which can refuse a week or build cascade rows, and records what it
        # did on the manager. Thirteen other screens report that; this one
        # swallowed it, so a tactic whose Annual Plan Element is detached —
        # which this tab lists on purpose, D4/AWA-M4.3 — saved the item
        # un-re-filed with nothing on screen to say so. Before `edit_item`:
        # that opens a modal, and a notice raised after it stacks behind the
        # editor where it cannot be read.
        notify_weekly_tactic_changes(self.db_manager, self)
        self.load_items()
        self.edit_item(item.id)


class WeekActionsScreen(ctk.CTkFrame):
    """The APE Week Actions tab: a week's tactics, and one tactic's items.

    Purpose: AWA-M3/M4 — pick a week, pick one of its Weekly Tactics, work on
             the Action Items underneath it.
    Spec:    docs/spec_2026-11-07_ape_week_actions.md#awa-m4
    Tests:   tests/test_ape_week_actions.py::test_awam42_left_panel_lists_the_weeks_tactics
    """

    # UPD-M6 — one prefix for this screen's own state. The left panel's column
    # widths are stored under `<prefix>_left_col_widths` and the divider under
    # `<prefix>_split_ratio`. The right panel is a `TodayScreen` subclass and
    # keeps the `week_actions_col_widths` field it already had (UPD-D3): a
    # rename would discard widths a user has set, saying nothing.
    SETTINGS_PREFIX = "week_actions"

    def __init__(self, parent, vps_manager: "VPSManager", app: "GetMoreDoneApp"):
        super().__init__(parent)
        self.vps_manager = vps_manager
        self.app = app
        self.settings = getattr(app, "settings", None) or AppSettings.load()

        self.week_var = ctk.StringVar(value="")
        # Every tactic in the chosen week, and the subset the filters leave.
        # Both are kept: the counts the screen reports are "shown of total",
        # and a count of what a filter hid cannot be recovered from the
        # filtered list alone (P2).
        self.tactic_rows: List[Dict[str, Any]] = []
        self.visible_rows: List[Dict[str, Any]] = []
        self.tactic_row_frames: Dict[str, ctk.CTkFrame] = {}
        self.selected_tactic_id: Optional[str] = None

        self.segment_colors: Dict[str, str] = {}
        self.subsegment_colors: Dict[Any, str] = {}
        self.category_colors: Dict[Any, str] = {}

        self.filters = LineageFilters(weekly_tactic_parts)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_ui()
        self._reload_color_maps()
        self.jump_to_current_week()

    # ----------------------------------------------------------------------- ui

    def create_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)

        ctk.CTkLabel(
            header,
            text="APE Week Actions",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=6, padx=(10, 20), pady=(8, 6),
               sticky="w")

        ctk.CTkLabel(header, text="Week Start:").grid(
            row=1, column=0, padx=(8, 5), pady=(0, 8), sticky="e")
        self.week_combo = ctk.CTkComboBox(
            header, width=136, values=[""], variable=self.week_var,
            command=lambda _value: self.load_selected_week(),
            **combo_box_style(),
        )
        self.week_combo.grid(row=1, column=1, padx=5, pady=(0, 8), sticky="w")

        ctk.CTkButton(
            header, text="Load", width=76, command=self.load_selected_week,
            **button_style("secondary"),
        ).grid(row=1, column=2, padx=5, pady=(0, 8), sticky="w")
        ctk.CTkButton(
            header, text="This Week", width=86,
            command=self.jump_to_current_week, **button_style("secondary"),
        ).grid(row=1, column=3, padx=5, pady=(0, 8), sticky="w")

        # UPD-M6.4 — the three filters the other five tabs all have, from
        # screens/lineage_filters.py. The module owns the "All" sentinel, the
        # option lists and the predicate; this screen owns where they sit and
        # what it says when they hide everything.
        next_column = self.filters.build_combos(
            header, start_column=4, on_change=self.on_filters_changed)

        self.status_label = ctk.CTkLabel(
            header, text="", text_color=status_text_color("muted"))
        self.status_label.grid(row=1, column=next_column, sticky="w", padx=10,
                               pady=(0, 8))
        header.grid_columnconfigure(next_column, weight=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        # The two panels open at the shared minimum and are re-sized by
        # SplitPanel on the body's first `<Configure>`. Without a minimum here
        # the first paint is two panels at their content width, which then
        # jump when the ratio is applied.
        body.grid_columnconfigure(0, weight=0, minsize=MIN_PANEL_WIDTH)
        body.grid_columnconfigure(1, weight=0, minsize=SPLITTER_WIDTH)
        body.grid_columnconfigure(2, weight=0, minsize=MIN_PANEL_WIDTH)
        body.grid_rowconfigure(1, weight=1)
        self.body = body

        self.left_title_label = ctk.CTkLabel(
            body, text="Weekly Tactics", font=ctk.CTkFont(weight="bold"))
        self.left_title_label.grid(row=0, column=0, sticky="w", padx=8,
                                   pady=(8, 4))

        # The shared table destroys every child of its container, so the
        # empty-state label lives in a sibling frame rather than inside the
        # scroll frame the table owns (chip_table's class docstring, AWA-S6 a).
        self.left_frame = ctk.CTkFrame(body)
        self.left_frame.grid(row=1, column=0, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(0, weight=1)

        self.left_list = ctk.CTkScrollableFrame(self.left_frame, label_text="")
        self.left_list.grid(row=0, column=0, sticky="nsew")
        self.left_list.grid_columnconfigure(0, weight=1)

        self.left_empty = ctk.CTkLabel(
            self.left_frame,
            text="No Weekly Tactics for this week.",
            text_color=semantic_colors()["muted_text"],
        )
        self.left_empty.grid(row=0, column=0, pady=12, padx=8, sticky="nw")

        divider = ctk.CTkFrame(
            body,
            width=SPLITTER_WIDTH,
            corner_radius=999,
            fg_color=semantic_colors()["border"],
            cursor="sb_h_double_arrow",
        )
        divider.grid(row=1, column=1, sticky="ns", padx=4, pady=4)
        self.divider = divider

        self.actions_panel = WeekTacticActionsPanel(
            body, self.app.db_manager, self.app)
        self.actions_panel.grid(row=0, column=2, rowspan=2, sticky="nsew")

        # UPD-M6.2 — the left list is the shared chip table, where it was one
        # CTkButton per tactic. Its own prefix, so a drag here never moves the
        # Actions panel's columns.
        self.left_table = ChipTable(
            self.left_list, self.settings,
            f"{self.SETTINGS_PREFIX}_left", WEEK_ACTIONS_LEFT_COLUMNS,
        )

        # UPD-M6.1 — the divider, from screens/split_panel.py. The body used
        # to be a fixed 380px minimum on the left and weight=1 on the right,
        # so the split was not the user's to set.
        self.split = SplitPanel(
            body,
            self.left_frame,
            divider,
            settings=self.settings,
            prefix=self.SETTINGS_PREFIX,
        )

    # -------------------------------------------------------------------- weeks

    def _first_day_of_week(self) -> int:
        return week_options.first_day_of_week(self.app)

    def _existing_week_starts(self) -> List[str]:
        rows = self.vps_manager.get_weekly_action_items(ape_only=False)
        return sorted({row["start_date"] for row in rows if row.get("start_date")},
                      reverse=True)

    def refresh_week_options(self):
        options = week_options.selectable_week_options(
            date.today(), self._existing_week_starts(), self._first_day_of_week()
        )
        self.week_combo.configure(values=options)
        if self.week_var.get() not in options:
            self.week_var.set(options[0])

    def jump_to_current_week(self):
        """AWA-M4.1 — the current week, from the shared helper."""
        current = week_options.week_start_for(
            date.today(), self._first_day_of_week()).isoformat()
        self.refresh_week_options()
        self.week_var.set(current)
        self.load_selected_week()

    def load_selected_week(self):
        """AWA-M4.2/M4.3/M4.5 — list the week's tactics, selection cleared."""
        week_start = (self.week_var.get() or "").strip()
        if not week_start:
            self.tactic_rows = []
            self.visible_rows = []
            # AWA-M4.5 — a tactic from the previous week must not stay on
            # screen beside a different week's list. This also renders.
            self.select_tactic(None)
            self.status_label.configure(text="Choose a Week Start first.")
            return

        # ape_only=False (D4): a Weekly Tactic whose Annual Plan Element has
        # been detached still has Action Items under it, and hiding it would
        # make them unreachable from this tab with nothing on screen to say so
        # (P2). The count below says how many are listed.
        self.tactic_rows = self.vps_manager.get_weekly_action_items(
            week_start_date=week_start, ape_only=False)
        self.filters.refresh_options(self.tactic_rows)
        self.visible_rows = self.filters.filtered(self.tactic_rows)
        self.select_tactic(None)
        self._report_counts()

    def on_filters_changed(self):
        """UPD-M6.4 — re-filter the list in place, keeping the selection.

        The week has not changed, so the selected tactic is still this week's
        and the right panel should keep it. It is cleared only when the filter
        has hidden the row it belongs to: leaving it would show one tactic's
        Action Items beside a list that does not contain it, which is the
        confusion AWA-M4.5 exists to prevent.
        Spec:  docs/spec_2026-11-07_unified_panel_design.md#upd-m6
        Tests: tests/test_unified_panel_design.py::test_updm64_a_filter_that_hides_the_selected_row_clears_the_panel
        """
        self.visible_rows = self.filters.filtered(self.tactic_rows)
        visible_ids = {row["id"] for row in self.visible_rows}
        if self.selected_tactic_id and self.selected_tactic_id not in visible_ids:
            self.select_tactic(None)
        else:
            self._render_tactics()
        self._report_counts()

    # ------------------------------------------------------------------ tactics

    def _reload_color_maps(self):
        """The three lineage colour maps, read fresh from the VSP tables."""
        self.segment_colors, self.subsegment_colors = (
            load_latest_lineage_color_maps(self.vps_manager))
        self.category_colors = load_category_color_map(self.vps_manager)

    def _render_tactics(self):
        """Render the week's tactics into the shared chip table.

        Purpose: UPD-M6.2 — the left panel was one `CTkButton` per tactic,
                 with the title and the segment name stacked on two lines and
                 no column a user could size. It is the same table the other
                 five panels draw now, with a Title column this tab needs
                 because its rows are picked by name.

                 WTP-M6.5 — each row also shows ``n/m`` in a Done column, so
                 the list says how much of the work under each tactic is
                 finished. It reads
                 ``vps_manager.count_open_children_for_weekly_tactic``, the
                 same helper the APE Week Assignment right panel reads
                 (WTP-M6.4), rather than counting here: two panels counting the
                 same week two ways is how they come to disagree.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m6
                 docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m6
        Tests:   tests/test_unified_panel_design.py::test_updm62_left_panel_is_the_shared_table
                 tests/test_weekly_tactic_parent.py::test_wtpm65_week_actions_list_shows_progress
        """
        self.tactic_row_frames = {}
        self.left_title_label.configure(text=self._left_title())
        self.left_empty.configure(text=self._empty_text())

        empty = not self.visible_rows
        show_list_or_message(self.left_list, self.left_empty, empty)
        if empty:
            self.left_table.clear()
            return

        palette = semantic_colors()
        self.left_table.build_header()
        for idx, row in enumerate(self.visible_rows, start=1):
            segment_name, subsegment_name, category_name = weekly_tactic_parts(row)
            segment_color, subsegment_color, category_color = resolve_chip_colors(
                segment_name, subsegment_name, category_name, self.vps_manager,
                self.segment_colors, self.subsegment_colors, self.category_colors,
            )
            tactic_id = row["id"]
            selected = tactic_id == self.selected_tactic_id

            done, total = self.vps_manager.count_open_children_for_weekly_tactic(
                tactic_id)
            frame, cells = self.left_table.add_row(
                {
                    "index": str(idx),
                    "title": (row.get("title") or "(untitled)").strip(),
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
                fg_color=palette["selected_tint"] if selected else None,
                border_width=2,
                border_color=segment_color,
            )
            self.tactic_row_frames[tactic_id] = frame

            # UPD-M6.3 — every cell is a click target, not just the frame: a
            # click lands on whichever widget is under the pointer, and a row
            # whose chips do not select is a row that only works at its edges.
            for widget in (frame, *cells.values()):
                widget.bind(
                    "<Button-1>",
                    lambda _event, rid=tactic_id: self.select_tactic(rid),
                )

    def _left_title(self) -> str:
        """The left panel's heading, which says what the filters left."""
        total = len(self.tactic_rows)
        shown = len(self.visible_rows)
        if shown == total:
            return f"Weekly Tactics ({total})"
        return f"Weekly Tactics ({shown} of {total})"

    def _empty_text(self) -> str:
        """What an empty left panel says, and why it is empty (UPD-M6.5, P2).

        A week with no tactics and a filter that hid every one of them are
        different facts, and the second one has to name the filter and the
        count: a panel that just says "none" after a filter is a panel that
        looks like an empty week.
        """
        hidden = len(self.tactic_rows) - len(self.visible_rows)
        if not self.tactic_rows:
            return "No Weekly Tactics for this week."
        return (
            f"No Weekly Tactics match the filter: {self.filters.describe()}. "
            f"{hidden} hidden."
        )

    def _report_counts(self):
        """The status line: how many are listed, and how many a filter hid."""
        week_start = (self.week_var.get() or "").strip()
        total = len(self.tactic_rows)
        shown = len(self.visible_rows)
        if shown == total:
            self.status_label.configure(
                text=f"{total} Weekly Tactic(s) for week of {week_start}.")
            return
        self.status_label.configure(
            text=(
                f"{shown} of {total} Weekly Tactic(s) for week of {week_start}. "
                f"{total - shown} hidden by {self.filters.describe()}."
            )
        )

    def select_tactic(self, tactic_id: Optional[str]):
        """AWA-M4.4 — set the selection and reload the right panel once."""
        self.selected_tactic_id = tactic_id
        row = next((r for r in self.tactic_rows if r["id"] == tactic_id), None)
        self._render_tactics()
        self.actions_panel.set_tactic(row)

    def refresh(self):
        self._reload_color_maps()
        self.load_selected_week()
