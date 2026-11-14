"""
Upcoming screen - shows items due in next N days.
"""

import customtkinter as ctk
from datetime import datetime, timedelta, date
from typing import Optional, TYPE_CHECKING

from ..models import ActionItem
from ..app_settings import AppSettings
from ..priority_levels import (
    LEVEL_ANY_CRITICAL,
    fill_for_level,
    is_critical_factor,
    level_cell_fill,
    row_control_kwargs,
    row_fill,
)
from ..date_utils import increment_date
from .priority_cell import SCORE_CELL_WIDTH_PX, build_level_cell, score_text
from .segment_color_utils import resolve_segment_color_for_item
from .week_collision_notice import (
    confirm_weekly_tactic_completion,
    notify_weekly_tactic_changes,
)
from ..theme import apply_segment_accent, semantic_colors, button_style, combo_box_style, list_row_font
from .inline_editors import InlineDateDialog, InlinePriorityDialog
from .item_lineage import lineage_for_item, LINEAGE_COL_CHARS
from .title_format import (
    split_action_item_title,
    format_column_text,
    CONTACT_COL_CHARS,
)
from .item_list_columns import (
    ToolbarWrap,
    FACTOR_CHIP_WIDTHS,
    FixedColumn,
    ItemListLayout,
    factors_column,
    timer_column,
)

if TYPE_CHECKING:
    from ..db_manager import DatabaseManager
    from ..app import GetMoreDoneApp


class UpcomingScreen(ctk.CTkFrame):
    """Screen showing upcoming items grouped by due date."""

    COLUMN_PREFIX = "upcoming"

    def __init__(self, parent, db_manager: 'DatabaseManager', app: 'GetMoreDoneApp'):
        super().__init__(parent)
        self.db_manager = db_manager
        self.app = app
        self.settings = AppSettings.load()
        self.segment_colors_by_id = {}
        self.segment_colors_by_name = {}
        self._parent_segment_cache = {}
        self._ape_segment_cache = {}
        self._ape_lineage_cache = {}
        self._week_action_segment_cache = {}
        self._item_lineage_cache = {}
        # Track column visibility state
        self.columns_expanded = self.settings.default_columns_expanded
        self.search_query = ""  # Track search query
        self.palette = semantic_colors()

        self.grid_columnconfigure(0, weight=1)
        # Row 0 = toolbar, row 1 = pinned column header, row 2 = the list.
        self.grid_rowconfigure(2, weight=1)

        # Create header
        self.create_header()

        # LSR-M1/M2/M7: a pinned column header with dividers, and one
        # column layout for it and the rows.
        self.layout = ItemListLayout(
            self, self.settings, self.COLUMN_PREFIX, first_col=1, title_default=260)
        self.column_header = None

        # Create scrollable frame for items
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="")
        self.scroll_frame.grid(
            row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.layout.bind(self.scroll_frame)

        # Load items
        self.refresh()

    def create_header(self):
        """Create header with controls."""
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        # Title
        title = ctk.CTkLabel(
            header,
            text="Upcoming Items",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, padx=10, pady=10)

        # Search entry
        self.search_entry = ctk.CTkEntry(
            header,
            placeholder_text="Search title, description, next action...",
            width=200
        )
        self.search_entry.grid(row=0, column=1, padx=5, pady=10)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())

        # Search button
        btn_search = ctk.CTkButton(
            header,
            text="Search",
            width=80,
            **button_style("secondary"),
            command=self.perform_search
        )
        btn_search.grid(row=0, column=2, padx=5, pady=10)

        # N-days selector
        ctk.CTkLabel(header, text="Next").grid(
            row=0, column=3, padx=(20, 5), pady=10)

        self.days_var = ctk.StringVar(value="7")
        self.days_combo = ctk.CTkComboBox(
            header,
            values=["1", "3", "7", "14", "30"],
            variable=self.days_var,
            width=80,
            command=lambda _: self.refresh()
        )
        self.days_combo.grid(row=0, column=4, padx=5, pady=10)

        ctk.CTkLabel(header, text="days").grid(
            row=0, column=5, sticky="w", padx=5, pady=10)

        # Who filter
        ctk.CTkLabel(header, text="Who:").grid(
            row=0, column=6, padx=(20, 5), pady=10)

        who_values = ["All"] + self.db_manager.get_distinct_who_values()
        self.who_var = ctk.StringVar(value="All")
        self.who_combo = ctk.CTkComboBox(
            header,
            values=who_values,
            variable=self.who_var,
            width=150,
            **combo_box_style(),
            command=lambda _: self.refresh()
        )
        self.who_combo.grid(row=0, column=7, padx=5, pady=10)

        # Expand/Collapse button
        self.expand_collapse_btn = ctk.CTkButton(
            header,
            text="Collapse" if self.columns_expanded else "Expand",
            width=100,
            **button_style("secondary"),
            command=self.toggle_columns
        )
        self.expand_collapse_btn.grid(row=0, column=8, padx=5, pady=10)

        # New Item button
        btn_new = ctk.CTkButton(
            header,
            text="+ New Item",
            **button_style("primary"),
            command=self.create_new_item
        )
        btn_new.grid(row=0, column=9, padx=10, pady=10)
        self.toolbar_wrap = ToolbarWrap(header, self.search_entry, 1, 5)

    def perform_search(self):
        """Perform search and update the view."""
        self.search_query = self.search_entry.get().strip()
        self.refresh()

    def toggle_columns(self):
        """Toggle between expanded and collapsed column view."""
        self.columns_expanded = not self.columns_expanded
        self.expand_collapse_btn.configure(
            text="Expand" if not self.columns_expanded else "Collapse")
        self.refresh()

    def _build_column_header(self):
        """The pinned column headings, over the same columns as the rows (LSR-M7)."""
        fixed = [
            FixedColumn(5, "Start", 60),
            FixedColumn(6, "Due", 60),
            FixedColumn(7, "Pri", SCORE_CELL_WIDTH_PX),
            FixedColumn(8, "Time", 50),
        ]
        if self.columns_expanded:
            fixed.append(factors_column(9))
        fixed.append(timer_column(10 if self.columns_expanded else 9))
        self.layout.set_columns([FixedColumn(0, "", 30)], fixed)
        if self.column_header is not None:
            self.column_header.destroy()
        hdr = self.layout.build_header(
            self,
            {"title": "Title", "subsegment": "SubSegment",
             "category": "Category", "who": "Who"},
            fg_color=self.palette["surface_subtle"],
            border_color=self.palette["border"],
        )
        # padx 15 = the list's outer padx (10) + each row's padx (5).
        hdr.grid(row=1, column=0, sticky="ew",
                 padx=self.layout.header_padx(self.scroll_frame, 10), pady=(10, 4))
        self.column_header = hdr

    def refresh(self):
        """Refresh the list of upcoming items."""
        self.palette = semantic_colors()
        # Reloaded here, not only in __init__, so a colour saved in
        # Settings > Priority Colours shows the next time this screen is
        # opened rather than only after a relaunch (PLC-M4).
        self.settings = AppSettings.load()
        # Clear current items
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.layout.clear_rows()
        self._build_column_header()

        # Refresh VSP segment color cache
        self.segment_colors_by_id = self.app.vps_manager.get_segment_colors_by_id()
        self.segment_colors_by_name = self.app.vps_manager.get_segment_color_map()
        self._parent_segment_cache = {}
        self._ape_segment_cache = {}
        self._ape_lineage_cache = {}
        self._week_action_segment_cache = {}
        self._item_lineage_cache = {}

        # Get filters
        n_days = int(self.days_var.get())
        who_filter = None if self.who_var.get() == "All" else self.who_var.get()
        who_filter_norm = who_filter.strip().lower() if who_filter else None

        # Keep Who dropdown up-to-date with newest values.
        current_who = self.who_var.get()
        who_values = ["All"] + self.db_manager.get_distinct_who_values()
        self.who_combo.configure(values=who_values)
        if current_who in who_values:
            self.who_var.set(current_who)
        else:
            self.who_var.set("All")
            who_filter = None
            who_filter_norm = None

        # Get items (use search if query exists, otherwise get upcoming)
        if self.search_query:
            items = self.db_manager.search_items(self.search_query)
            # Apply filters to search results
            today = datetime.now().date()
            end_date = today + timedelta(days=n_days)
            filtered_items = []
            for item in items:
                # Only include open items
                if item.status != "open":
                    continue
                # Check date range
                item_date = item.start_date or item.due_date
                if item_date and item_date <= end_date.isoformat():
                    # Apply who filter
                    item_who_norm = (item.who or "").strip().lower()
                    if who_filter_norm is None or item_who_norm == who_filter_norm:
                        filtered_items.append(item)
            items = filtered_items
        else:
            items = self.db_manager.get_upcoming_items(n_days, who_filter)

        if not items:
            label = ctk.CTkLabel(
                self.scroll_frame,
                text="No upcoming items",
                font=ctk.CTkFont(size=14)
            )
            label.grid(row=0, column=0, pady=20)
            return

        # Group by start date (or due date if no start date)
        grouped = {}
        for item in items:
            date_key = item.start_date or item.due_date or "No start date"
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(item)

        # Display grouped items
        row = 0
        for start_date in sorted(grouped.keys()):
            items_for_date = grouped[start_date]

            # Date header
            total_planned = sum(
                item.planned_minutes or 0 for item in items_for_date)
            date_label = self.format_date_header(
                start_date, len(items_for_date), total_planned)

            header_frame = ctk.CTkFrame(
                self.scroll_frame, fg_color=self.palette["surface_subtle"])
            header_frame.grid(row=row, column=0,
                              sticky="ew", pady=(10, 0), padx=5)
            header_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                header_frame,
                text=date_label,
                font=ctk.CTkFont(size=14, weight="bold")
            ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

            row += 1

            # Items for this date
            for item in items_for_date:
                item_frame = self.create_item_row(item)
                item_frame.grid(row=row, column=0,
                                sticky="ew", pady=2, padx=5)
                row += 1

    def create_item_row(self, item: ActionItem) -> ctk.CTkFrame:
        """Create a row for an action item."""
        palette = self.palette
        row_text = palette["row_text"]
        segment_color = resolve_segment_color_for_item(
            item,
            self.segment_colors_by_id,
            self.segment_colors_by_name,
            self.db_manager,
            self._parent_segment_cache,
            self._ape_segment_cache,
            self._week_action_segment_cache,
        )
        # use_completed_tint=False: this screen has never had a completed
        # branch, and giving it one here would be a behaviour change nobody
        # asked for (BACKLOG).
        fill = row_fill(
            palette,
            use_completed_tint=False,
            segment_color=segment_color,
        )
        bg_color = fill.fill
        row_text = fill.text_color or palette["row_text"]
        frame = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color)
        apply_segment_accent(frame, segment_color)
        self.layout.apply_grid(frame)
        parsed = split_action_item_title(item.title)
        _segment_name, subsegment_name, category_name = lineage_for_item(
            item,
            self.db_manager,
            self._item_lineage_cache,
            self._ape_lineage_cache,
            self._week_action_segment_cache,
        )

        # Complete checkbox
        var = ctk.BooleanVar(value=False)
        checkbox = ctk.CTkCheckBox(
            frame,
            text="",
            variable=var,
            width=30,
            command=lambda: self.complete_item(item.id),
            **row_control_kwargs(fill),
        )
        checkbox.grid(row=0, column=0, padx=5, pady=5)

        title_cell = ctk.CTkFrame(frame, fg_color="transparent")
        title_cell.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        title_cell.grid_columnconfigure(1, weight=1)
        has_badge = item.item_type == "week"
        if has_badge:
            ctk.CTkLabel(
                title_cell,
                text="WT",
                width=28,
                corner_radius=6,
                fg_color=palette["success_strong"],
                text_color=palette["on_strong"],
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=0, column=0, padx=(0, 6), sticky="w")
        # The badge (28) and its gap (6) come out of the title's width.
        title_delta = 34 if has_badge else 0
        title_label = ctk.CTkLabel(
            title_cell,
            text=self.layout.cell_text("title", parsed.title, title_delta),
            width=self.layout.cell_width("title", title_delta),
            font=list_row_font(),
            anchor="w",
            text_color=row_text
        )
        title_label.grid(row=0, column=1, sticky="ew")
        title_label.bind("<Button-1>", lambda _event, item_id=item.id: self.edit_item(item_id))

        # Every stretching cell follows its column live (LSR-M4).
        self.layout.add_stretch_cells(
            frame, (title_label, parsed.title, title_delta),
            {"subsegment": subsegment_name or "-",
             "category": category_name or "-", "who": item.who},
            row_text, list_row_font())

        # Start Date
        start_date_text = item.start_date if item.start_date else "-"
        if item.start_date:
            try:
                dt = datetime.fromisoformat(item.start_date)
                start_date_text = dt.strftime("%m/%d")
            except:
                pass
        start_label = ctk.CTkLabel(
            frame,
            text=f"S:{start_date_text}",
            width=60,
            anchor="w",
            text_color=row_text,
            font=list_row_font()
        )
        start_label.grid(row=0, column=5, padx=5, pady=5)
        start_label.bind("<Button-1>", lambda _event, item_id=item.id: self.edit_start_date_inline(item_id))

        # Due Date
        due_date_text = item.due_date if item.due_date else "-"
        if item.due_date:
            try:
                dt = datetime.fromisoformat(item.due_date)
                due_date_text = dt.strftime("%m/%d")
            except:
                pass
        due_label = ctk.CTkLabel(
            frame,
            text=f"D:{due_date_text}",
            width=60,
            anchor="w",
            text_color=row_text,
            font=list_row_font()
        )
        due_label.grid(row=0, column=6, padx=5, pady=5)
        due_label.bind("<Button-1>", lambda _event, item_id=item.id: self.edit_due_date_inline(item_id))

        # Priority score
        # PCC-M3 -- the Priority cell's background is the priority colour
        # scheme, and the only place it is drawn. A cell with no colour of
        # its own keeps the row's text, which the row may have derived
        # from a segment fill.
        cell = level_cell_fill(self.settings, item)
        score_label_box, score_label = build_level_cell(
            frame, cell, score_text(item.priority_score), SCORE_CELL_WIDTH_PX, row_text, list_row_font(),
            on_click=lambda _event, item_id=item.id: self.edit_priority_inline(item_id),
        )
        score_label_box.grid(row=0, column=7, padx=5, pady=5)

        # Estimated time (planned_minutes) - ALWAYS shown (not collapsed)
        time_text = f"{item.planned_minutes}m" if item.planned_minutes else "-"
        time_label = ctk.CTkLabel(
            frame,
            text=time_text,
            width=50,
            anchor="w",
            text_color=row_text,
            font=list_row_font()
        )
        time_label.grid(row=0, column=8, padx=5, pady=5)

        # Factor chips (I, U, E, V) - only shown when expanded
        col_offset = 0
        if self.columns_expanded:
            factors_frame = ctk.CTkFrame(frame, fg_color="transparent")
            factors_frame.grid(row=0, column=9, padx=5, pady=5)
            columns = list(zip(
                ("G", "C", "I", "U", "E", "V"),
                (item.group, item.category, item.importance, item.urgency,
                 item.size, item.value),
                FACTOR_CHIP_WIDTHS,
            ))
            # PCC-M4 -- a critical factor chip takes the Any Critical level
            # colour, the same scheme the Priority cell carries. Asked once
            # per row, not once per chip.
            critical_chip = fill_for_level(self.settings, LEVEL_ANY_CRITICAL)
            for col, (label, value, width) in enumerate(columns):
                text = f"{label}:{value}" if value not in (None, "") else ""
                label_kwargs = {
                    "text": text,
                    "width": width,
                    "anchor": "w",
                    "font": list_row_font(),
                    "text_color": row_text,
                }
                if is_critical_factor(label, value):
                    chip, _ = build_level_cell(
                        factors_frame, critical_chip, text, width, row_text,
                        list_row_font(), anchor="w",
                    )
                else:
                    chip = ctk.CTkLabel(factors_frame, **label_kwargs)
                chip.grid(
                    row=0, column=col, padx=2)
            col_offset = 1

        # Action buttons
        # Buttons shift by one when expanded factors are shown.
        btn_timer = ctk.CTkButton(
            frame,
            text="⏱ Timer",
            width=70,
            **button_style("secondary"),
            command=lambda: self.start_timer(item.id)
        )
        btn_timer.grid(row=0, column=9 + col_offset, padx=(0, 2), pady=5)

        return frame

    def format_date_header(self, start_date: str, count: int, total_minutes: int) -> str:
        """Format date header text."""
        if start_date == "No start date":
            return f"{start_date} ({count} items)"

        try:
            dt = datetime.fromisoformat(start_date)
            day_name = dt.strftime("%A, %B %d, %Y")

            # Check if today, tomorrow, etc.
            today = datetime.now().date()
            item_date = dt.date()
            days_diff = (item_date - today).days

            if days_diff == 0:
                day_name = f"Today - {day_name}"
            elif days_diff == 1:
                day_name = f"Tomorrow - {day_name}"
            elif days_diff < 7:
                day_name = f"This {dt.strftime('%A')} - {day_name}"

            header = f"{day_name} ({count} items"
            if total_minutes > 0:
                hours = total_minutes // 60
                mins = total_minutes % 60
                if hours > 0:
                    header += f", {hours}h {mins}m"
                else:
                    header += f", {mins}m"
            header += ")"

            return header
        except Exception:
            return f"{start_date} ({count} items)"

    def complete_item(self, item_id: str):
        """Mark item as complete."""
        # WTP-M6.1 - the same question the editor asks. A declined
        # prompt completes nothing and says nothing.
        if not confirm_weekly_tactic_completion(self.db_manager, item_id, self):
            return
        self.db_manager.complete_action_item(item_id)
        notify_weekly_tactic_changes(self.db_manager, self)
        notify_weekly_tactic_changes(self.db_manager, self)
        self.refresh()

    def start_timer(self, item_id: str):
        """Start timer for an action item."""
        # Get the action item
        item = self.db_manager.get_action_item(item_id)
        if not item:
            return

        # Open timer window
        from .timer_window import TimerWindow
        timer = TimerWindow.open_for(self, self.db_manager, item,
                                     on_close=self.refresh,
                                     vps_manager=self.app.vps_manager)

    def edit_item(self, item_id: str, focus_tab: str | None = None):
        """Open item editor."""
        from .item_editor import ItemEditorDialog
        ItemEditorDialog(self, self.db_manager, item_id,
                         vps_manager=self.app.vps_manager, on_close_callback=self.refresh,
                         focus_tab=focus_tab)

    def edit_start_date_inline(self, item_id: str):
        """Edit item start date in place."""
        item = self.db_manager.get_action_item(item_id)
        if not item:
            return
        dialog = InlineDateDialog(self, "Edit Start Date", item.start_date)
        self.wait_window(dialog)
        if dialog.result == "__cancel__":
            return
        new_start = dialog.result
        new_due = item.due_date
        if new_start and new_due and new_due < new_start:
            new_due = new_start
        self.db_manager.reschedule_item(item_id, new_start, new_due, reason="inline_start_edit")
        notify_weekly_tactic_changes(self.db_manager, self)
        self.refresh()

    def edit_priority_inline(self, item_id: str):
        """Edit item priority score in place."""
        item = self.db_manager.get_action_item(item_id)
        if not item:
            return
        dialog = InlinePriorityDialog(self, item)
        self.wait_window(dialog)
        if dialog.result == "__cancel__":
            return
        item.importance = dialog.result["importance"]
        item.urgency = dialog.result["urgency"]
        item.size = dialog.result["size"]
        item.value = dialog.result["value"]
        self.db_manager.update_action_item(item, normalize_week_dates=False)
        notify_weekly_tactic_changes(self.db_manager, self)
        self.refresh()

    def edit_due_date_inline(self, item_id: str):
        """Edit item due date in place."""
        item = self.db_manager.get_action_item(item_id)
        if not item:
            return
        dialog = InlineDateDialog(self, "Edit Due Date", item.due_date)
        self.wait_window(dialog)
        if dialog.result == "__cancel__":
            return
        new_due = dialog.result
        new_start = item.start_date
        if new_start and new_due and new_due < new_start:
            new_due = new_start
        self.db_manager.reschedule_item(item_id, new_start, new_due, reason="inline_due_edit")
        notify_weekly_tactic_changes(self.db_manager, self)
        self.refresh()

    def push_item(self, item_id: str):
        """Push item to next day without showing dialog, using weekend-aware logic."""
        # Get the item
        item = self.db_manager.get_action_item(item_id)
        if not item:
            return

        # Load settings for weekend handling
        settings = AppSettings.load()
        next_day = increment_date(
            date.today(), 1, settings.include_saturday, settings.include_sunday
        ).isoformat()

        # Calculate new dates (add 1 day using weekend-aware logic)
        new_start = item.start_date
        new_due = item.due_date

        if item.start_date:
            try:
                start_dt = date.fromisoformat(item.start_date)
                new_start_dt = increment_date(
                    start_dt, 1, settings.include_saturday, settings.include_sunday)
                new_start = new_start_dt.isoformat()
            except ValueError:
                new_start = item.start_date

        if item.due_date:
            try:
                due_dt = date.fromisoformat(item.due_date)
                new_due_dt = increment_date(
                    due_dt, 1, settings.include_saturday, settings.include_sunday)
                new_due = new_due_dt.isoformat()
            except ValueError:
                new_due = item.due_date

        # If item has no dates yet, assign next business day to both.
        if not item.start_date and not item.due_date:
            new_start = next_day
            new_due = next_day

        # Push to next day directly (no dialog, no reason)
        self.db_manager.reschedule_item(
            item_id, new_start, new_due, reason=None)
        notify_weekly_tactic_changes(self.db_manager, self)
        self.refresh()

    def create_new_item(self):
        """Open item editor for new item."""
        from .item_editor import ItemEditorDialog
        ItemEditorDialog(self, self.db_manager,
                         vps_manager=self.app.vps_manager, on_close_callback=self.refresh)
