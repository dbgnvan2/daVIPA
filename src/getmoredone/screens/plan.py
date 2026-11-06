"""Plan screen — time blocks and daily planning.

Purpose: pick a day, see the action items that start on it, drag them into a
         packed day of blocks, and rearrange, resize or pad that day.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md
Tests:   tests/test_plan_screen.py

The model, stated once because every method here assumes it: **a planned day
is an order, not a set of appointments.** Nothing on this screen lets a block
be dropped at 10:17. The user arranges blocks in the sequence they intend to
work them, and the clock times are derived from that order, the block lengths
and the day's bounds (``time_block_layout.pack_day``). That is why a reorder
re-times the whole day, and why the arithmetic lives in a module with no Tk in
it rather than in here.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import TYPE_CHECKING, Dict, List, Optional

import customtkinter as ctk

from ..models import ActionItem, BlockType, TimeBlock
from ..theme import button_style, semantic_colors, status_text_color
from ..time_block_layout import (
    DURATION_CHOICES,
    MAX_BLOCK_MINUTES,
    DayBounds,
    PackedBlock,
    default_minutes_for_block_type,
    duration_for_item,
    is_block_day,
    lunch_window,
    move_block_to_gap,
    pack_day,
    sort_blocks,
    total_planned_minutes,
    weekday_names,
)
from ..widgets.date_picker import DatePickerButton
from .drag_schedule_support import widget_contains_pointer
from .plan_blocks import build_block_row, build_item_row, build_lunch_band
from .plan_settings_dialog import PlanSettingsDialog

if TYPE_CHECKING:
    from ..db_manager import DatabaseManager
    from ..app import GetMoreDoneApp

# A right-click arrives as Button-3 on Linux and Windows. macOS delivers it as
# Button-2 under some input configurations, so both are bound; that the OS
# delivers one of them is a human check in the running app.
RIGHT_CLICK_SEQUENCES = ("<Button-3>", "<Button-2>")

# How many items the left pane will draw. Announced when it bites, never
# silently applied (P2): a planner that quietly stopped listing an item would
# be hiding the work it exists to surface.
MAX_ITEM_ROWS = 60


class PlanScreen(ctk.CTkFrame):
    """Screen for planning time blocks."""

    def __init__(self, parent, db_manager: 'DatabaseManager', app: 'GetMoreDoneApp'):
        super().__init__(parent)
        self.db_manager = db_manager
        self.app = app

        self.settings = getattr(app, "settings", None)
        self.bounds = DayBounds.from_settings(self.settings) if self.settings else DayBounds()

        self.selected_date = date.today().strftime("%Y-%m-%d")

        # DatePickerButton calls its on_date_changed from its own __init__,
        # which lands here before the panes it would reload exist. The flag is
        # the guard: the date is still recorded, but nothing is drawn until
        # construction has finished and refresh() runs for the first time.
        self._ready = False

        # Drag state. One drag at a time, and its kind decides what a release
        # means: an item drop creates a block, a block drop reorders the day.
        self._drag_kind: Optional[str] = None
        self._drag_item: Optional[ActionItem] = None
        self._drag_block: Optional[TimeBlock] = None
        self._drag_label: Optional[ctk.CTkLabel] = None
        self._drag_hover_frame = None
        self._block_menu: Optional[tk.Menu] = None

        #: Rendered block frames in day order, so a drop can be turned into an
        #: insertion index without asking Tk which widget is under the mouse.
        self._block_frames: List[tuple] = []
        self._packed: List[PackedBlock] = []
        self._items: List[ActionItem] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.create_items_pane()
        self.create_day_pane()

        self._ready = True
        self.refresh()

    # ================= construction =========================================

    def create_header(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            header,
            text="Plan - Time Blocks",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(header, text="Date:").pack(side="left", padx=(16, 4))
        self.date_picker = DatePickerButton(
            header,
            initial_date=self.selected_date,
            on_date_changed=self.on_date_changed,
            settings=self.settings,
            fg_color="transparent",
        )
        self.date_picker.pack(side="left", padx=(0, 10))

        self.btn_settings = ctk.CTkButton(
            header,
            text="⚙ Day Settings",
            width=130,
            command=self.open_settings,
            **button_style("secondary"),
        )
        self.btn_settings.pack(side="right", padx=10)

        self.btn_add_break = ctk.CTkButton(
            header,
            text="+ Break",
            width=90,
            command=lambda: self.add_padding_block(BlockType.BREAK),
            **button_style("secondary"),
        )
        self.btn_add_break.pack(side="right", padx=4)

        self.btn_add_buffer = ctk.CTkButton(
            header,
            text="+ Buffer",
            width=90,
            command=lambda: self.add_padding_block(BlockType.BUFFER),
            **button_style("secondary"),
        )
        self.btn_add_buffer.pack(side="right", padx=4)

        self.status_label = ctk.CTkLabel(header, text="", anchor="e")
        self.status_label.pack(side="right", padx=10)

    def create_items_pane(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self.items_heading = ctk.CTkLabel(
            frame, text="Items", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.items_heading.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        self.items_hint = ctk.CTkLabel(
            frame,
            text="Drag an item onto the day to block it.",
            anchor="w",
            text_color=semantic_colors()["muted_text"],
            font=ctk.CTkFont(size=11),
        )
        self.items_hint.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        self.items_scroll = ctk.CTkScrollableFrame(frame)
        self.items_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.items_scroll.grid_columnconfigure(0, weight=1)

    def create_day_pane(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        self.day_heading = ctk.CTkLabel(
            frame, text="Day Plan", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.day_heading.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        self.day_summary = ctk.CTkLabel(
            frame,
            text="",
            anchor="w",
            text_color=semantic_colors()["muted_text"],
            font=ctk.CTkFont(size=11),
        )
        self.day_summary.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        # The drop target for an item drag, and the container a block drag is
        # reordered within.
        self.blocks_scroll = ctk.CTkScrollableFrame(frame)
        self.blocks_scroll.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.blocks_scroll.grid_columnconfigure(0, weight=1)
        self.day_drop_frame = frame

    # ================= loading ==============================================

    def refresh(self):
        self.load_items()
        self.load_blocks()

    def on_date_changed(self, new_date: str):
        self.selected_date = new_date
        if self._ready:
            self.refresh()

    def open_settings(self):
        if self.settings is None:
            self.set_status("Settings are unavailable", "error")
            return
        dialog = PlanSettingsDialog(self, self.settings, on_saved=self.on_settings_saved)
        dialog.wait_window()

    def on_settings_saved(self, bounds: DayBounds):
        """The day's shape changed, so every stored time on *every* day is stale.

        Not just the date on screen. Day Start, lunch and Day End are settings,
        so they shape every planned day; a day left holding times derived from
        bounds that no longer exist stores values that do not follow from their
        inputs, and the first reader to trust the stored string rather than
        re-deriving it gets the old shape of the day.
        """
        self.bounds = bounds
        repacked = self.db_manager.repack_all_days(self.bounds)
        self.refresh()
        if len(repacked) > 1:
            self.set_status(f"Day settings saved; re-timed {len(repacked)} days", "success")

    def load_items(self):
        grid_info = self.items_scroll.grid_info()
        self.items_scroll.grid_remove()
        try:
            for widget in self.items_scroll.winfo_children():
                widget.destroy()

            self._items = self.db_manager.get_items_for_start_date(self.selected_date)
            blocked = self.db_manager.get_blocked_item_ids(self.selected_date)

            self.items_heading.configure(
                text=f"Items starting {self.selected_date}"
            )

            shown = self._items[:MAX_ITEM_ROWS]
            if not shown:
                ctk.CTkLabel(
                    self.items_scroll,
                    text=(
                        "No open items start on this date.\n\n"
                        "This list is filtered on each item's Start Date, so an item\n"
                        "with the wrong start date will not appear here."
                    ),
                    justify="left",
                ).grid(row=0, column=0, padx=10, pady=20, sticky="w")
            else:
                for row, item in enumerate(shown):
                    frame = build_item_row(
                        self.items_scroll,
                        item,
                        row,
                        already_blocked=item.id in blocked,
                        work_block_minutes=duration_for_item(
                            item, self.bounds.default_block_minutes
                        ),
                    )
                    self.bind_item_drag(frame, item)

            # Announce the cap rather than applying it silently (P2).
            if len(self._items) > len(shown):
                self.items_hint.configure(
                    text=(
                        f"Showing {len(shown)} of {len(self._items)} items. "
                        "Drag an item onto the day to block it."
                    )
                )
            else:
                self.items_hint.configure(
                    text="Drag an item onto the day to block it."
                )
        finally:
            self.items_scroll.grid(**grid_info)

    def load_blocks(self):
        grid_info = self.blocks_scroll.grid_info()
        self.blocks_scroll.grid_remove()
        try:
            for widget in self.blocks_scroll.winfo_children():
                widget.destroy()
            self._block_frames = []

            blocks = sort_blocks(self.db_manager.get_time_blocks(self.selected_date))
            self._packed = pack_day(blocks, self.bounds)
            items_by_id = self._items_by_id(blocks)

            self.update_day_summary(blocks)

            if not self._packed:
                ctk.CTkLabel(
                    self.blocks_scroll,
                    text=(
                        "No blocks on this day yet.\n\n"
                        "Drag an item across from the left, or add a Buffer or Break."
                    ),
                    justify="left",
                ).grid(row=0, column=0, padx=10, pady=20, sticky="w")
                return

            lunch = lunch_window(self.bounds)
            row = 0
            for entry in self._packed:
                if entry.pushed_after_lunch and lunch:
                    build_lunch_band(self.blocks_scroll, row, lunch[0], lunch[1])
                    row += 1

                block = entry.block
                # The packed times, not the stored ones: a settings change
                # re-shapes the day on screen in the same pass that writes it,
                # and showing the old times until the next reload would be a
                # status that disagrees with the data (P6).
                block.start_time = entry.start_time
                block.end_time = entry.end_time

                frame = build_block_row(
                    self.blocks_scroll,
                    block,
                    items_by_id.get(block.item_id),
                    row,
                    overflows_day_end=entry.overflows_day_end,
                )
                self.bind_block_handlers(frame, block)
                self._block_frames.append((frame, block.id))
                row += 1
        finally:
            self.blocks_scroll.grid(**grid_info)

    def _items_by_id(self, blocks) -> Dict[str, ActionItem]:
        """The items behind these blocks, including ones not in the left pane.

        A block's item may start on another date, or be completed since -- it
        is still the item that block is for, and the block has to be able to
        say so. Looked up individually rather than by reusing the date-filtered
        list, which is the bug that would make every older block read
        "(item no longer exists)".
        """
        found = {item.id: item for item in self._items}
        for block in blocks:
            if block.item_id and block.item_id not in found:
                item = self.db_manager.get_action_item(block.item_id)
                if item:
                    found[item.id] = item
        return found

    def update_day_summary(self, blocks):
        planned = total_planned_minutes(blocks)
        hours, minutes = divmod(planned, 60)
        planned_text = f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"

        parts = [f"{len(blocks)} blocks", f"{planned_text} planned"]
        if not is_block_day(self.selected_date, self.bounds):
            allowed = [
                name for name, on in zip(weekday_names(), self.bounds.block_weekdays) if on
            ]
            parts.append(
                "not a block day — Day Settings allows "
                + (", ".join(allowed) if allowed else "no days")
            )
        overflowing = sum(1 for entry in self._packed if entry.overflows_day_end)
        if overflowing:
            parts.append(f"{overflowing} past {self.bounds.day_end}")

        self.day_summary.configure(text="  ·  ".join(parts))

    def set_status(self, text: str, kind: str = "muted"):
        self.status_label.configure(text=text, text_color=status_text_color(kind))

    # ================= creating blocks ======================================

    def add_padding_block(self, block_type: str):
        """TB-M10 — append a buffer or a break to the day."""
        if not self._require_block_day():
            return

        minutes = default_minutes_for_block_type(block_type, self.settings)
        # One transaction, as everywhere a write is followed by its repack: in
        # between, the new row holds no times at all, and a repack that failed
        # there would leave it that way with nothing in the day to show it.
        with self.db_manager.transaction():
            self.db_manager.create_time_block(
                TimeBlock(
                    block_date=self.selected_date,
                    start_time="",
                    end_time="",
                    planned_minutes=minutes,
                    block_type=block_type,
                )
            )
            self.db_manager.repack_day(self.selected_date, self.bounds)
        self.load_blocks()
        self.set_status(f"Added a {minutes}m {block_type}", "success")

    def block_item(self, item: ActionItem):
        """TB-M8 — make a block for this item at the end of the day."""
        if not self._require_block_day():
            return

        minutes = duration_for_item(item, self.bounds.default_block_minutes)
        with self.db_manager.transaction():
            self.db_manager.create_time_block(
                TimeBlock(
                    block_date=self.selected_date,
                    start_time="",
                    end_time="",
                    planned_minutes=minutes,
                    item_id=item.id,
                    label=item.title,
                    block_type=BlockType.ITEM,
                )
            )
            self.db_manager.repack_day(self.selected_date, self.bounds)
        self.refresh()
        try:
            requested = int(getattr(item, "work_block", None))
        except (TypeError, ValueError):
            requested = 0
        if requested > minutes:
            # Said, not swallowed: the item asked for a length the planner
            # cannot store, and the block it got is not the one it asked for.
            self.set_status(
                f"Blocked {minutes}m for {item.title}"
                f" (Work Block of {requested}m is longer than a day)",
                "warning",
            )
        else:
            self.set_status(f"Blocked {minutes}m for {item.title}", "success")

    def _require_block_day(self) -> bool:
        """Refuse to write a block onto a day the user does not work.

        Refused with the reason, not silently: a drop that does nothing and
        says nothing is indistinguishable from a drag that missed.
        """
        if is_block_day(self.selected_date, self.bounds):
            return True
        allowed = [
            name for name, on in zip(weekday_names(), self.bounds.block_weekdays) if on
        ]
        self.set_status(
            f"{self.selected_date} is not a block day (Day Settings allows "
            + (", ".join(allowed) if allowed else "no days")
            + ")",
            "warning",
        )
        return False

    # ================= the block context menu ===============================

    def bind_block_handlers(self, frame, block: TimeBlock):
        for widget in [frame] + list(frame.winfo_children()):
            for sequence in RIGHT_CLICK_SEQUENCES:
                widget.bind(
                    sequence, lambda event, b=block: self.open_block_menu(event, b)
                )
            widget.bind("<ButtonPress-1>", lambda event, b=block: self.start_block_drag(event, b))
            widget.bind("<B1-Motion>", self.on_drag_motion)
            widget.bind("<ButtonRelease-1>", self.on_drag_release)

    def open_block_menu(self, event, block: TimeBlock):
        """TB-M9 — durations, a custom length, and delete.

        A tkinter.Menu rather than a CTk widget: CustomTkinter has no context
        menu, and this is the first right-click surface in the app.
        """
        menu = tk.Menu(self, tearoff=0)
        # Held on the screen: tkinter does not keep a reference to a posted
        # menu, and one collected while still on screen takes its commands
        # with it, so the first click after a garbage collection does nothing.
        self._block_menu = menu
        for minutes in DURATION_CHOICES:
            menu.add_command(
                label=f"{minutes} minutes" + ("  (default)" if minutes == 30 else ""),
                command=lambda m=minutes, b=block: self.set_block_minutes(b, m),
            )
        menu.add_separator()
        menu.add_command(
            label="Custom…", command=lambda b=block: self.ask_custom_minutes(b)
        )
        menu.add_separator()
        menu.add_command(label="Delete block", command=lambda b=block: self.delete_block(b.id))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Without this the menu keeps the pointer grab on X11 and the next
            # click goes nowhere.
            menu.grab_release()

    def set_block_minutes(self, block: TimeBlock, minutes: int):
        """Resize one block, then re-time everything after it."""
        block.planned_minutes = minutes
        # One transaction. ``block`` still carries the end_time the last repack
        # gave it, so between these two writes the row reads as a 30-minute
        # block that claims 90 minutes, and the block after it still owns the
        # minutes this one has just taken.
        with self.db_manager.transaction():
            self.db_manager.update_time_block(block)
            self.db_manager.repack_day(self.selected_date, self.bounds)
        self.load_blocks()
        self.set_status(f"Set block to {minutes}m", "success")

    def ask_custom_minutes(self, block: TimeBlock):
        dialog = ctk.CTkInputDialog(
            text="Block length in minutes:", title="Block Length"
        )
        raw = dialog.get_input()
        if raw is None:
            return
        try:
            minutes = int(raw.strip())
        except (AttributeError, ValueError):
            self.set_status("Block length must be a whole number of minutes", "error")
            return
        if minutes <= 0:
            self.set_status("Block length must be more than zero minutes", "error")
            return
        if minutes > MAX_BLOCK_MINUTES:
            # Refused rather than clamped: a block longer than a day would be
            # stored with an end_time that format_hhmm had clamped, so the row
            # would no longer say start + duration, and it would be drawn tall
            # enough to put every block after it out of reach.
            self.set_status(
                f"Block length must be {MAX_BLOCK_MINUTES} minutes or less", "error"
            )
            return
        self.set_block_minutes(block, minutes)

    def delete_block(self, block_id: str):
        with self.db_manager.transaction():
            self.db_manager.delete_time_block(block_id)
            self.db_manager.repack_day(self.selected_date, self.bounds)
        self.refresh()
        self.set_status("Block deleted", "muted")

    # ================= dragging =============================================

    def bind_item_drag(self, frame, item: ActionItem):
        for widget in [frame] + list(frame.winfo_children()):
            widget.bind("<ButtonPress-1>", lambda event, i=item: self.start_item_drag(event, i))
            widget.bind("<B1-Motion>", self.on_drag_motion)
            widget.bind("<ButtonRelease-1>", self.on_drag_release)

    def start_item_drag(self, _event, item: ActionItem):
        self._drag_kind = "item"
        self._drag_item = item
        self._drag_block = None
        self._show_drag_label(item.title)

    def start_block_drag(self, _event, block: TimeBlock):
        self._drag_kind = "block"
        self._drag_block = block
        self._drag_item = None
        self._show_drag_label(block.label or block.block_type.title())

    def _show_drag_label(self, text: str):
        palette = semantic_colors()
        if self._drag_label is None:
            self._drag_label = ctk.CTkLabel(
                self,
                text=text,
                fg_color=palette["chip_bg"],
                text_color=palette["chip_text"],
                corner_radius=6,
                padx=8,
                pady=4,
            )
        else:
            self._drag_label.configure(text=text)
        self._drag_label.lift()
        self._position_drag_label()

    def _position_drag_label(self):
        if self._drag_label is None:
            return
        x = self.winfo_pointerx() - self.winfo_rootx() + 12
        y = self.winfo_pointery() - self.winfo_rooty() + 12
        self._drag_label.place(x=x, y=y)

    def on_drag_motion(self, _event):
        if not self._drag_kind:
            return
        self._position_drag_label()
        self.update_hover_target()

    def on_drag_release(self, _event):
        kind, item, block = self._drag_kind, self._drag_item, self._drag_block
        self.clear_hover_target()
        self._end_drag()

        if not kind:
            return

        # Where the drop landed must be read now, while the pointer is still
        # there. The write and the redraw must NOT happen now: both end in
        # refresh(), which destroys the very row whose ButtonRelease handler is
        # running, and tearing down the widget that is dispatching the event
        # hangs Tk. after_idle lets this handler return first.
        if kind == "item" and item is not None:
            if self.pointer_over_day():
                self.after_idle(lambda: self.block_item(item))
        elif kind == "block" and block is not None:
            target = self.drop_index_for_pointer()
            if target is not None:
                self.after_idle(lambda: self.reorder_to(block.id, target))

    def _end_drag(self):
        if self._drag_label is not None:
            self._drag_label.place_forget()
        self._drag_kind = None
        self._drag_item = None
        self._drag_block = None

    def pointer_over_day(self) -> bool:
        return widget_contains_pointer(
            self.day_drop_frame, self.winfo_pointerx(), self.winfo_pointery()
        )

    def drop_index_for_pointer(self) -> Optional[int]:
        """Where in the day order a block dropped here belongs.

        The index is decided by which half of which rendered block the pointer
        is in, so dropping on the top half of block 3 puts the dragged block
        before it and the bottom half puts it after. Pointer-y against frame
        midpoints rather than asking Tk what widget is underneath: during a
        drag the pointer is over the floating drag label, not the row.

        None means the drop was outside the day column, which is a cancelled
        drag rather than a move to the end -- a release over the sidebar should
        not quietly re-order the day.
        """
        if not widget_contains_pointer(
            self.blocks_scroll, self.winfo_pointerx(), self.winfo_pointery()
        ):
            return None

        y_root = self.winfo_pointery()
        index = len(self._block_frames)
        for position, (frame, _block_id) in enumerate(self._block_frames):
            try:
                top = frame.winfo_rooty()
                middle = top + frame.winfo_height() / 2
            except tk.TclError:
                continue
            if y_root < middle:
                index = position
                break
        return index

    def reorder_to(self, block_id: str, gap_index: int):
        """Move one block into the gap the pointer was released in.

        ``gap_index`` is counted against the rendered rows, dragged block
        included, which is the only thing the screen can measure. The
        conversion to a list position lives in time_block_layout, because
        getting it wrong here is invisible: it reorders *something*, just not
        where the user let go.
        """
        order = [bid for _frame, bid in self._block_frames]
        new_order = move_block_to_gap(order, block_id, gap_index)
        if new_order == order:
            return
        self.db_manager.reorder_time_blocks(self.selected_date, new_order, self.bounds)
        self.load_blocks()
        self.set_status("Day rearranged", "success")

    def update_hover_target(self):
        """Outline the day column while an item is being dragged onto it."""
        if self._drag_kind != "item":
            return
        hovered = self.day_drop_frame if self.pointer_over_day() else None
        if hovered is self._drag_hover_frame:
            return
        self.clear_hover_target()
        if hovered is not None:
            hovered.configure(border_width=2, border_color=semantic_colors()["primary_hover"])
            self._drag_hover_frame = hovered

    def clear_hover_target(self):
        if self._drag_hover_frame is not None:
            try:
                self._drag_hover_frame.configure(border_width=0)
            except tk.TclError:
                pass
            self._drag_hover_frame = None
