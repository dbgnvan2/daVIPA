"""Plan screen — time blocks and daily planning.

Purpose: pick a day, see the action items that start on it, drag them into a
         packed day of blocks, and rearrange, resize or pad that day.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md
Tests:   tests/test_plan_screen.py

The model, stated once because every method here assumes it: **a planned day
is a fixed grid of half hours.** Every half hour from Day Start to Day End is
a box, drawn whether anything is in it or not, and a block is placed on the
box the user drops it on. A block that is not a whole number of half hours
rounds up -- a 45 occupies two boxes, keeps its own 45, and leaves 15 of the
second box spare. More than one task may share a box, and a box costs 30
minutes however many tasks are in it.

Two consequences worth stating, because they are what the previous model got
wrong:

* **Gaps are legitimate.** An empty 09:00 between two filled boxes is a day
  the user planned that way, not a state to pack away.
* **``slot_index`` is relative to Day Start**, so moving Day Start re-times
  every day with no write to ``time_blocks`` at all. There is nothing to
  repack, which is why the packing machinery is gone.

The arithmetic lives in ``time_block_layout``, which has no Tk in it.
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
    SLOT_MINUTES,
    DayBounds,
    DayGrid,
    SlotRefusal,
    SlotRefusedError,
    build_day_grid,
    default_minutes_for_block_type,
    duration_for_item,
    is_block_day,
    slots_for_minutes,
    total_planned_minutes,
    weekday_names,
)
from ..widgets.date_picker import DatePickerButton
from .drag_schedule_support import widget_contains_pointer
from .plan_blocks import (
    build_empty_day_note,
    build_item_row,
    build_outside_group,
    build_slot_row,
)
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

# What each refusal reason is called on screen. Keyed by SlotRefusal, so a
# rule added to the grid arithmetic has exactly one place to be worded here,
# and a reason with no wording is caught by the test rather than shown to the
# user as a bare enum value.
#
# These replace DAY_TOO_FULL, which reported a ceiling the grid cannot reach:
# the last box ends at Day End, so no placement can run past what HH:MM can
# express.
REFUSAL_TEXT = {
    SlotRefusal.OUTSIDE_GRID: "That is outside the day — Day Settings sets its hours",
    SlotRefusal.CROSSES_LUNCH: "That would run into lunch — try a later box",
    SlotRefusal.SLOT_FULL: "That half hour is full — try another box",
}

#: Said when a refusal arrives with a reason nothing here words. Better than
#: showing the user the reason's internal name, and loud enough to be noticed.
UNKNOWN_REFUSAL = "That block cannot go there"


def refusal_text(reason: str) -> str:
    """The screen's wording for a grid refusal."""
    return REFUSAL_TEXT.get(reason, UNKNOWN_REFUSAL)


def _clock(minutes: int) -> str:
    """A duration as the summary says it: ``45m``, or ``2h 30m``.

    One function, because the summary prints three durations side by side and
    three formattings of the same quantity would read as three different units.
    """
    hours, remainder = divmod(max(0, int(minutes)), 60)
    return f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"


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
        #: The hovered box's own border width, so clearing the hover puts it
        #: back instead of flattening it to 0.
        self._drag_hover_border: int = 1
        self._block_menu: Optional[tk.Menu] = None

        #: Rendered boxes, as (frame, slot_index), in day order. A drop is
        #: turned into a slot by pointer-y against these frames rather than by
        #: asking Tk what is under the mouse: during a drag the pointer is over
        #: the floating drag label, not the box.
        self._slot_frames: List[tuple] = []
        #: The task chips this screen bound handlers to, as
        #: (widget, block_id). Only blocks that *start* in a box are in here:
        #: a continuation chip is drawn but owns nothing, so it carries no
        #: drag and no menu.
        self._block_widgets: List[tuple] = []
        #: The grid last drawn, so the summary and the drop rules read the
        #: same object the user is looking at.
        self._grid: DayGrid = DayGrid()
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
        """The day's shape changed. Nothing is written, and that is the point.

        Purpose: TG-M6.4 -- a block's box is stored relative to Day Start, so
                 moving Day Start re-times every day on read. There is no
                 stored clock time to go stale, nothing to re-pack, and no
                 transaction that can leave one day's times derived from one
                 set of bounds and another's from a different set.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m6
        Tests:   tests/test_plan_screen.py::test_tgm64_saving_settings_writes_no_blocks

        The stored ``start_time``/``end_time`` columns are still written when a
        block is placed or resized, and they are still the block's own times --
        but they are a record, not the truth, and the screen draws from the
        grid. A day whose boxes no longer exist under the new bounds is
        surfaced as outside the day rather than re-timed into one that does.
        """
        self.bounds = bounds
        self.refresh()

        outside = len(self._grid.outside)
        if outside:
            # Said, because this is the one way a settings change can take
            # work off the grid, and a block silently absent is the failure
            # the "outside the day" group exists to prevent (P2).
            noun = "block" if outside == 1 else "blocks"
            self.set_status(
                f"Day settings saved — {outside} {noun} no longer fit the day;"
                " drag them onto a box",
                "warning",
            )
            return
        self.set_status("Day settings saved", "success")

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
        """Draw the day as its grid of half hours.

        Purpose: TG-M7 -- every box from Day Start to Day End, filled or not.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m7
        Tests:   tests/test_plan_screen.py::test_tgm71_every_slot_is_drawn
        """
        grid_info = self.blocks_scroll.grid_info()
        self.blocks_scroll.grid_remove()
        try:
            for widget in self.blocks_scroll.winfo_children():
                widget.destroy()
            self._slot_frames = []
            self._block_widgets = []

            # Place anything that has never been on the grid before drawing,
            # so a day stored by the old model reads as a day rather than as a
            # list of blocks outside it. Idempotent, so this is a no-op on
            # every load after the first.
            self.db_manager.adopt_legacy_day(self.selected_date, self.bounds)

            blocks = self.db_manager.get_time_blocks(self.selected_date)
            self._grid = build_day_grid(blocks, self.bounds)
            items_by_id = self._items_by_id(blocks)

            self.update_day_summary(blocks)

            row = 0
            for entry in self._grid.slots:
                rendered = build_slot_row(
                    self.blocks_scroll, entry, items_by_id, row
                )
                self._slot_frames.append((rendered.frame, entry.slot.index))
                for block, widget in rendered.block_widgets:
                    self.bind_block_handlers(widget, block)
                    self._block_widgets.append((widget, block.id))
                row += 1

            if not blocks:
                build_empty_day_note(self.blocks_scroll, row)
                row += 1

            # Surfaced under the grid, never dropped (P2).
            if self._grid.outside:
                for block, widget in build_outside_group(
                    self.blocks_scroll, self._grid.outside, items_by_id, row
                ):
                    self.bind_block_handlers(widget, block)
                    self._block_widgets.append((widget, block.id))
                row += 1 + len(self._grid.outside)
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
        """Boxes used, time occupied, time planned -- all three, separately.

        Purpose: TG-M12 -- collapsing these is how the 45-in-two-boxes case
                 becomes a lie. A 45-minute task occupies 60 minutes of the
                 day and plans 45 of them; a summary reporting one number
                 would have to pick which of those to be wrong about.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m12
        Tests:   tests/test_plan_screen.py::test_tgm121_the_summary_separates_occupied_from_planned
        """
        parts = [
            f"{self._grid.slots_used} of {len(self._grid.slots)} boxes",
            f"{_clock(self._grid.minutes_occupied)} occupied",
            f"{_clock(total_planned_minutes(blocks))} planned",
        ]
        if not is_block_day(self.selected_date, self.bounds):
            allowed = [
                name for name, on in zip(weekday_names(), self.bounds.block_weekdays) if on
            ]
            parts.append(
                "not a block day — Day Settings allows "
                + (", ".join(allowed) if allowed else "no days")
            )
        if self._grid.outside:
            parts.append(f"{len(self._grid.outside)} outside the day")

        self.day_summary.configure(text="  ·  ".join(parts))

    def set_status(self, text: str, kind: str = "muted"):
        self.status_label.configure(text=text, text_color=status_text_color(kind))

    # ================= creating blocks ======================================

    def add_padding_block(self, block_type: str, slot_index: Optional[int] = None):
        """TB-M10/TG-M9 — put a buffer or a break on a box.

        With no ``slot_index`` it goes on the first box that will hold it,
        which is what the toolbar buttons want: they are a click, not a drop,
        so there is no box under a pointer to read.
        """
        if not self._require_block_day():
            return

        minutes = default_minutes_for_block_type(block_type, self.settings)
        if slot_index is None:
            slot_index = self.first_free_slot(minutes)
            if slot_index is None:
                self.set_status(
                    f"No free half hour left for a {minutes}m {block_type}", "warning"
                )
                return

        block = TimeBlock(
            block_date=self.selected_date,
            start_time="",
            end_time="",
            planned_minutes=minutes,
            block_type=block_type,
        )
        try:
            self.db_manager.add_block_at(block, slot_index, self.bounds)
        except SlotRefusedError as refused:
            # Said, not left as a click that did nothing: a refused action and
            # a broken one look identical from the outside.
            self.set_status(refusal_text(refused.reason), "error")
            return
        self.load_blocks()
        self.set_status(
            f"Added a {minutes}m {block_type} at {block.start_time}", "success"
        )

    def block_item(self, item: ActionItem, slot_index: Optional[int] = None):
        """TG-M9 — make a block for this item on the box it was dropped on.

        Purpose: the half hour the user chose, not the end of the day.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m9
        Tests:   tests/test_plan_screen.py::test_tgm91_a_drop_lands_on_the_slot_under_the_pointer

        With no ``slot_index`` — the item row's own double-click path, where
        there is no pointer over a box to read — it takes the first box that
        will hold it.
        """
        if not self._require_block_day():
            return

        minutes = duration_for_item(item, self.bounds.default_block_minutes)
        if slot_index is None:
            slot_index = self.first_free_slot(minutes)
            if slot_index is None:
                self.set_status(
                    f"No free half hour left for {minutes}m of {item.title}", "warning"
                )
                return

        block = TimeBlock(
            block_date=self.selected_date,
            start_time="",
            end_time="",
            planned_minutes=minutes,
            item_id=item.id,
            label=item.title,
            block_type=BlockType.ITEM,
        )
        try:
            self.db_manager.add_block_at(block, slot_index, self.bounds)
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        self.refresh()

        boxes = slots_for_minutes(minutes)
        spare = boxes * SLOT_MINUTES - minutes
        text = f"Blocked {minutes}m for {item.title} at {block.start_time}"
        if spare:
            # Said out loud, because the box the task does not fill is still
            # spent: the next task starts at the following box, not at the
            # minute this one ends.
            text += f" — {boxes} boxes, {spare}m spare"
        self.set_status(text, "success")

    def first_free_slot(self, minutes: int) -> Optional[int]:
        """The earliest box in today's grid that will hold this length.

        For the paths with no pointer to read. ``None`` when the day has no
        room, which the caller reports rather than writing anyway: a day with
        nowhere left is a fact about the day, not a failure.
        """
        from ..time_block_layout import can_place

        blocks = self.db_manager.get_time_blocks(self.selected_date)
        span = slots_for_minutes(minutes)
        for entry in self._grid.slots or build_day_grid(blocks, self.bounds).slots:
            if not can_place(blocks, self.bounds, entry.slot.index, span):
                return entry.slot.index
        return None

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
        """TG-M11 — change a block's length, keeping it where it is.

        Purpose: a length that will not fit from where the block sits is
                 refused. The block is not slid to a box where it would fit:
                 that answers a question the user did not ask.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m11
        Tests:   tests/test_time_block_crud.py::test_tgm112_a_resize_that_does_not_fit_is_refused

        The in-memory ``block`` is deliberately not mutated before the write:
        it is the same object the row menu hands back on the next click, and a
        refused length left on it would show a size the database refused (P6).
        """
        try:
            resized = self.db_manager.set_block_length(block.id, minutes, self.bounds)
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self.load_blocks()

        boxes = slots_for_minutes(resized.planned_minutes)
        spare = boxes * SLOT_MINUTES - resized.planned_minutes
        text = f"Set block to {resized.planned_minutes}m"
        if spare:
            text += f" — {boxes} boxes, {spare}m spare"
        self.set_status(text, "success")

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
        """Remove a block. Its box goes back to being empty, and stays there.

        No repack: an empty box between two filled ones is a legitimate day,
        so nothing moves up to fill the hole the delete leaves.
        """
        self.db_manager.delete_time_block(block_id)
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
        target = self.slot_under_pointer()
        if kind == "item" and item is not None:
            if target is not None:
                self.after_idle(lambda: self.block_item(item, target))
            elif self.pointer_over_day():
                # In the day column but not on a box -- the heading, the
                # summary, or the "outside the day" group below the grid.
                # Reported rather than guessed at: picking a box for them
                # would put the work somewhere they did not point.
                self.set_status("Drop an item on a half-hour box", "muted")
        elif kind == "block" and block is not None:
            if target is not None:
                self.after_idle(lambda: self.move_block_to_slot(block.id, target))

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

    def slot_under_pointer(self) -> Optional[int]:
        """The box the pointer is inside, or ``None``.

        Purpose: TG-M9 -- the drop target is a half hour, not the pane.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m9
        Tests:   tests/test_plan_screen.py::test_tgm91_a_drop_lands_on_the_slot_under_the_pointer

        Each box's own rectangle, not a midpoint rule: a box is a place, so a
        release either lands in one or does not. ``None`` is a cancelled drag
        and never "the nearest box" -- a release over the sidebar must not
        quietly move the day's work.

        Read from the frames' root coordinates rather than by asking Tk what is
        under the mouse, because during a drag the pointer is over the floating
        drag label.
        """
        x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
        if not widget_contains_pointer(self.blocks_scroll, x_root, y_root):
            return None

        for frame, slot_index in self._slot_frames:
            if widget_contains_pointer(frame, x_root, y_root):
                return slot_index
        return None

    def move_block_to_slot(self, block_id: str, slot_index: int):
        """TG-M11 — put a dragged block on the box it was dropped on.

        Spec:  docs/implementation_plan_2026-11-05_time_grid.md#tg-m11
        Tests: tests/test_plan_screen.py::test_tgm111_a_real_drag_moves_a_block_between_slots

        A refusal is reported and nothing is written. Moving the block to some
        other box that happens to fit would be the screen deciding where the
        user's work goes.
        """
        try:
            moved = self.db_manager.place_block_at(block_id, slot_index, self.bounds)
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self.load_blocks()
        self.set_status(f"Moved to {moved.start_time}", "success")

    def update_hover_target(self):
        """Outline the box under the pointer during a drag.

        The box, not the column: with a fixed grid the user is choosing a half
        hour, and an outline around the whole pane would not tell them which
        one they are about to get. Both kinds of drag get it, because a block
        being moved lands on a box exactly as an item does.
        """
        if not self._drag_kind:
            return
        target = self.slot_under_pointer()
        hovered = None
        if target is not None:
            for frame, slot_index in self._slot_frames:
                if slot_index == target:
                    hovered = frame
                    break
        if hovered is self._drag_hover_frame:
            return
        self.clear_hover_target()
        if hovered is not None:
            self._drag_hover_border = hovered.cget("border_width")
            hovered.configure(
                border_width=2, border_color=semantic_colors()["primary_hover"]
            )
            self._drag_hover_frame = hovered

    def clear_hover_target(self):
        """Put the outlined box's own border back.

        Restored to what it was rather than to 0: every box is drawn with a
        1px border, so clearing to 0 would leave the last-hovered box subtly
        different from its neighbours for the rest of the session.
        """
        if self._drag_hover_frame is not None:
            try:
                self._drag_hover_frame.configure(
                    border_width=self._drag_hover_border
                )
            except tk.TclError:
                pass
            self._drag_hover_frame = None
