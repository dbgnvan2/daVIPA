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
from ..models import ActionItem
from ..theme import button_style, combo_box_style, semantic_colors, status_text_color
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

    LEFT_PANE_MIN_WIDTH = 380

    def __init__(self, parent, vps_manager: "VPSManager", app: "GetMoreDoneApp"):
        super().__init__(parent)
        self.vps_manager = vps_manager
        self.app = app

        self.week_var = ctk.StringVar(value="")
        self.tactic_rows: List[Dict[str, Any]] = []
        self.tactic_buttons: Dict[str, ctk.CTkButton] = {}
        self.selected_tactic_id: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_ui()
        self.jump_to_current_week()

    # ----------------------------------------------------------------------- ui

    def create_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(5, weight=1)

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

        self.status_label = ctk.CTkLabel(
            header, text="", text_color=status_text_color("muted"))
        self.status_label.grid(row=1, column=4, sticky="w", padx=10,
                               pady=(0, 8))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=0, minsize=self.LEFT_PANE_MIN_WIDTH)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self.left_title_label = ctk.CTkLabel(
            body, text="Weekly Tactics", font=ctk.CTkFont(weight="bold"))
        self.left_title_label.grid(row=0, column=0, sticky="w", padx=8,
                                   pady=(8, 4))

        self.left_frame = ctk.CTkScrollableFrame(body, label_text="")
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.actions_panel = WeekTacticActionsPanel(
            body, self.app.db_manager, self.app)
        self.actions_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")

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
        # AWA-M4.5 — a tactic from the previous week must not stay on screen
        # beside a different week's list.
        self.select_tactic(None)
        if not week_start:
            self.tactic_rows = []
            self._render_tactics()
            self.status_label.configure(text="Choose a Week Start first.")
            return

        # ape_only=False (D4): a Weekly Tactic whose Annual Plan Element has
        # been detached still has Action Items under it, and hiding it would
        # make them unreachable from this tab with nothing on screen to say so
        # (P2). The count below says how many are listed.
        self.tactic_rows = self.vps_manager.get_weekly_action_items(
            week_start_date=week_start, ape_only=False)
        self._render_tactics()
        self.status_label.configure(
            text=f"{len(self.tactic_rows)} Weekly Tactic(s) for week of {week_start}."
        )

    # ------------------------------------------------------------------ tactics

    def _render_tactics(self):
        for child in self.left_frame.winfo_children():
            child.destroy()
        self.tactic_buttons = {}

        self.left_title_label.configure(
            text=f"Weekly Tactics ({len(self.tactic_rows)})")

        if not self.tactic_rows:
            ctk.CTkLabel(
                self.left_frame,
                text="No Weekly Tactics for this week.",
                text_color=semantic_colors()["muted_text"],
            ).grid(row=0, column=0, sticky="w", padx=8, pady=12)
            return

        for row_index, row in enumerate(self.tactic_rows):
            tactic_id = row["id"]
            label = (row.get("title") or "(untitled)").strip()
            ape = (row.get("ape_segment_name") or "").strip()
            button = ctk.CTkButton(
                self.left_frame,
                text=f"{label}\n{ape}" if ape else label,
                anchor="w",
                command=lambda rid=tactic_id: self.select_tactic(rid),
                **button_style("secondary"),
            )
            button.grid(row=row_index, column=0, sticky="ew", padx=4, pady=3)
            self.tactic_buttons[tactic_id] = button

    def select_tactic(self, tactic_id: Optional[str]):
        """AWA-M4.4 — set the selection and reload the right panel once."""
        self.selected_tactic_id = tactic_id
        row = next((r for r in self.tactic_rows if r["id"] == tactic_id), None)
        for rid, button in self.tactic_buttons.items():
            button.configure(
                **button_style("primary" if rid == tactic_id else "secondary"))
        self.actions_panel.set_tactic(row)

    def refresh(self):
        self.load_selected_week()
