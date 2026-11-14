"""
Hierarchical screen - shows items in parent-child tree view.
"""

import customtkinter as ctk
from typing import Optional, TYPE_CHECKING, List

from ..models import ActionItem, Status
from ..app_settings import AppSettings
from ..priority_levels import (
    level_cell_fill,
    row_fill,
)
from .item_lineage import lineage_for_item, LINEAGE_COL_CHARS
from .priority_cell import SCORE_CELL_WIDTH_PX, score_text
from .segment_color_utils import resolve_segment_color_for_item
from .week_collision_notice import (
    confirm_weekly_tactic_completion,
    notify_weekly_tactic_changes,
)
from ..theme import apply_segment_accent, semantic_colors, button_style, list_row_font
from .title_format import (
    split_action_item_title,
    format_column_text,
    CONTACT_COL_CHARS,
)
from .item_list_columns import ItemListLayout, TextColumn, ToolbarWrap

# Each tree level indents its title this far, inside the title column.
INDENT_PX = 30

if TYPE_CHECKING:
    from ..db_manager import DatabaseManager
    from ..app import GetMoreDoneApp


class HierarchicalScreen(ctk.CTkFrame):
    """Screen showing action items in hierarchical tree view."""

    COLUMN_PREFIX = "hierarchical"

    def __init__(self, parent, db_manager: 'DatabaseManager', app: 'GetMoreDoneApp'):
        super().__init__(parent)
        self.db_manager = db_manager
        self.app = app
        # Reloaded again at the top of refresh(); here so a row build that does
        # not come through refresh() still has settings to read.
        self.settings = AppSettings.load()
        self.search_query = ""  # Track search query
        self.segment_colors_by_id = {}
        self.segment_colors_by_name = {}
        self._parent_segment_cache = {}
        self._ape_segment_cache = {}
        self._ape_lineage_cache = {}
        self._week_action_segment_cache = {}
        self._item_lineage_cache = {}
        self.palette = semantic_colors()

        self.grid_columnconfigure(0, weight=1)
        # Row 0 = toolbar, row 1 = pinned column header, row 2 = the tree.
        self.grid_rowconfigure(2, weight=1)

        # Create header
        self.create_header()

        # LSR-M1/M2/M7: a pinned column header with dividers, and one
        # column layout for it and every row at every depth (LSR-M8).
        # LSR2: Pri, Due and Sub-items resize too; this list has no controls.
        self.layout = ItemListLayout(
            self, self.settings, self.COLUMN_PREFIX, first_col=0, title_default=320,
            columns=(TextColumn("pri", 4, "Pri", SCORE_CELL_WIDTH_PX),
                     TextColumn("due", 5, "Due", 110),
                     TextColumn("subitems", 6, "Sub-items", 70)))
        self.layout.set_columns([], [])
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
            text="Hierarchical View",
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

        # Status filter
        ctk.CTkLabel(header, text="Status:").grid(
            row=0, column=4, padx=(20, 5), pady=10)

        self.status_var = ctk.StringVar(value="open")
        self.status_combo = ctk.CTkComboBox(
            header,
            values=["open", "completed", "all"],
            variable=self.status_var,
            width=120,
            command=lambda _: self.refresh()
        )
        self.status_combo.grid(row=0, column=5, padx=5, pady=10)

        # New Item button
        btn_new = ctk.CTkButton(
            header,
            text="+ New Item",
            **button_style("primary"),
            command=self.create_new_item
        )
        btn_new.grid(row=0, column=6, padx=10, pady=10)
        self.toolbar_wrap = ToolbarWrap(header, self.search_entry, 1, 3)

    def perform_search(self):
        """Perform search and update the view."""
        self.search_query = self.search_entry.get().strip()
        self.refresh()

    def _build_column_header(self):
        """The pinned column headings, over the same columns as the rows (LSR-M7)."""
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
        """Refresh the hierarchical list."""
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

        # Get status filter
        status = self.status_var.get()
        status_filter = None if status == "all" else status

        # Get items (use search if query exists, otherwise get root items)
        if self.search_query:
            all_items = self.db_manager.search_items(self.search_query)
            # Apply status filter to search results
            if status_filter:
                all_items = [
                    item for item in all_items if item.status == status_filter]
            # For search results, show all matching items (not just roots)
            root_items = all_items
        else:
            # Get root items (items with no parent)
            root_items = self.db_manager.get_root_items(
                status_filter=status_filter)

        if not root_items:
            label = ctk.CTkLabel(
                self.scroll_frame,
                text="No root items found",
                font=ctk.CTkFont(size=14)
            )
            label.grid(row=0, column=0, pady=20)
            return

        # Display each item
        row = 0
        if self.search_query:
            # For search results, display items in a flat list
            for item in root_items:
                item_frame = self.create_item_row(item, 0)
                item_frame.grid(row=row, column=0,
                                sticky="ew", pady=2, padx=5)
                row += 1
        else:
            # Display root items and their children recursively
            for item in root_items:
                row = self.display_item_tree(item, row, 0)

    def display_item_tree(self, item: ActionItem, row: int, indent_level: int) -> int:
        """
        Display an item and its children recursively.

        Args:
            item: The item to display
            row: Current row number
            indent_level: Indentation level (0 for root, 1 for child, etc.)

        Returns:
            Next available row number
        """
        # Create item row
        item_frame = self.create_item_row(item, indent_level)
        # Every depth starts at the same x, so its columns line up with the
        # header's; the indent is inside the title cell (LSR-M8).
        item_frame.grid(row=row, column=0, sticky="ew", pady=2, padx=5)
        row += 1

        # Get and display children
        children = self.db_manager.get_children(item.id)
        for child in children:
            row = self.display_item_tree(child, row, indent_level + 1)

        return row

    def create_item_row(self, item: ActionItem, indent_level: int) -> ctk.CTkFrame:
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
        # segment_color=None: this screen applies its segment colour as an
        # accent only and has never used it as a row fill, unlike Today,
        # Upcoming and All Items (BACKLOG).
        fill = row_fill(
            palette,
            use_completed_tint=item.status == Status.COMPLETED,
            segment_color=None,
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

        # The indent comes out of the title's own width (LSR-M8).
        indent = indent_level * INDENT_PX

        # Title with indentation indicator for child rows.
        title_text = parsed.title
        if item.group:
            title_text += f" [{item.group}]"

        # Add indentation indicator for child items
        if indent_level > 0:
            indicator = "└─ "
            title_text = indicator + title_text

        # The row font, not a fixed size-14 Courier: the text budget is
        # counted at the row font's character width.
        title_label = ctk.CTkLabel(
            frame,
            text=self.layout.cell_text("title", title_text, indent),
            width=self.layout.cell_width("title", indent),
            font=list_row_font(),
            anchor="w",
            text_color=row_text,
        )
        title_label.grid(row=0, column=0, sticky="w",
                         padx=(5 + indent, 5), pady=5)
        title_label.bind("<Button-1>", lambda _event, item_id=item.id: self.edit_item(item_id))

        # Every stretching cell follows its column live (LSR-M4).
        self.layout.add_stretch_cells(
            frame, (title_label, title_text, indent),
            {"subsegment": subsegment_name or "-",
             "category": category_name or "-", "who": item.who},
            row_text, list_row_font())

        # Priority score
        # PCC-M3 -- the Priority cell's background is the priority colour
        # scheme, and the only place it is drawn. A cell with no colour of
        # its own keeps the row's text, which the row may have derived
        # from a segment fill.
        cell = level_cell_fill(self.settings, item)
        score_label_box, score_label = self.layout.add_level_cell(
            frame, "pri", cell, score_text(item.priority_score), row_text, list_row_font(),
        )

        # Due date, and the child count; an empty cell still holds its column.
        # No "Due: " prefix: the heading says Due, and at the 6-character
        # floor the prefix was all that showed (LSR2 sweep).
        due_text = item.due_date or ""
        self.layout.add_text_cell(frame, "due", due_text, row_text, list_row_font())
        children = self.db_manager.get_children(item.id)
        count_text = f"({len(children)} sub)" if children else ""
        self.layout.add_text_cell(frame, "subitems", count_text, row_text, list_row_font())

        return frame

    def complete_item(self, item_id: str):
        """Mark item as complete."""
        # WTP-M6.1 - the same question the editor asks. A declined
        # prompt completes nothing and says nothing.
        if not confirm_weekly_tactic_completion(self.db_manager, item_id, self):
            return
        self.db_manager.complete_action_item(item_id)
        notify_weekly_tactic_changes(self.db_manager, self)
        self.refresh()

    def edit_item(self, item_id: str):
        """Open item editor."""
        from .item_editor import ItemEditorDialog
        ItemEditorDialog(self, self.db_manager, item_id,
                         vps_manager=self.app.vps_manager, on_close_callback=self.refresh)

    def create_new_item(self):
        """Open item editor for new item."""
        from .item_editor import ItemEditorDialog
        ItemEditorDialog(self, self.db_manager,
                         vps_manager=self.app.vps_manager, on_close_callback=self.refresh)
