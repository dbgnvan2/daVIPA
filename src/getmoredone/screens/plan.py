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

import logging
import tkinter as tk
from tkinter import messagebox
from datetime import date
from typing import TYPE_CHECKING, Dict, List, Optional

import customtkinter as ctk

from ..models import ActionItem, BlockType, TimeBlock
from ..theme import button_style, semantic_colors, status_text_color
from ..time_block_layout import (
    DAY_EXTEND_EARLIER,
    DAY_EXTEND_LATER,
    DURATION_CHOICES,
    MAX_BLOCK_MINUTES,
    SLOT_MINUTES,
    DayBounds,
    DayGrid,
    SlotRefusal,
    SlotRefusedError,
    build_day_grid,
    day_grid,
    default_minutes_for_block_type,
    duration_for_item,
    extended_day_bound,
    is_block_day,
    slots_for_minutes,
    total_planned_minutes,
    weekday_names,
)
from ..widgets.date_picker import DatePickerButton
from .drag_schedule_support import widget_contains_pointer
from .plan_blocks import (
    PD_EARLIER_HINT,
    PD_EARLIER_TEXT,
    PD_LATER_HINT,
    PD_LATER_TEXT,
    SLOT_CHECK_WIDTH_PX,
    SLOT_CHIP_HEIGHT_PX,
    SLOT_TIME_WIDTH_PX,
    SLOT_TITLE_WIDTH_PX,
    build_empty_day_note,
    build_item_row,
    build_outside_group,
    build_slot_row,
    build_virtual_slot_row,
    chip_column_minsizes,
)
from .plan_settings_dialog import PlanSettingsDialog

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..db_manager import DatabaseManager
    from ..app import GetMoreDoneApp

# A right-click arrives as Button-3 on Linux and Windows. macOS delivers it as
# Button-2 under some input configurations, so both are bound; that the OS
# delivers one of them is a human check in the running app.
RIGHT_CLICK_SEQUENCES = ("<Button-3>", "<Button-2>")

#: Width (px) of the items column when the setting is missing or unusable.
PLAN_ITEMS_COL_WIDTH_PX = 260

#: How much of the items column is frame, padding and scrollbar rather than
#: text. Subtracted from the column width to get a wraplength that fits.
ITEMS_TEXT_INSET_PX = 56

#: Width (px) of the grip between the two panes. Narrow enough to read as a
#: divider and wide enough to press: it is the whole of column 1, so what is
#: here is what the pointer has to land on. The first version was 6px with a
#: 2px pad on each side, which drew a 10px gap of which only the middle 6
#: could be grabbed.
PLAN_DIVIDER_WIDTH_PX = 15

#: Padding (px) between a pane and the window's edge. The panes have none
#: between themselves and the grip, so the gap the user aims at is the grip.
PLAN_PANE_EDGE_PAD_PX = 10

#: Width (px) of the screen that is not either pane: the grip between them and
#: the padding at each outside edge. Subtracted before the two floors are
#: measured against the window, because a window is only as wide as the panes
#: plus this.
PLAN_PANE_CHROME_PX = PLAN_DIVIDER_WIDTH_PX + 2 * PLAN_PANE_EDGE_PAD_PX

#: Height (px) of the "Outside the day" group. Fixed and scrollable rather
#: than as tall as its contents: the group shares the items column with the
#: item list, and a dozen blocks growing it would push the list it sits under
#: off the bottom of the pane.
OUTSIDE_GROUP_HEIGHT_PX = 150

#: The narrowest the empty-items note will wrap to. Tk reads a wraplength of
#: zero or less as "do not wrap", so a column of 56px or under would have
#: turned the note back into the one long clipped line that the wrapping was
#: added to fix. Below this width the note is wider than its column and
#: clipped at the right edge, which is the readable end: it is anchored west,
#: so it still starts at the first word.
NOTE_MIN_WRAP_PX = 120

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


class _DayNotWritten(Exception):
    """PD-M5 — the settings file refused the day's new hours.

    Its own type so the one broad ``except`` in ``extend_day_for`` can tell a
    refused write from a refused placement when it chooses the words, while
    still rolling the database work back the same way for both.
    """


def refusal_text(reason: str) -> str:
    """The screen's wording for a grid refusal."""
    return REFUSAL_TEXT.get(reason, UNKNOWN_REFUSAL)


def _subtree(widget):
    """``widget`` and every descendant, depth first.

    A chip nests its labels inside a body frame, so "the row's children" is
    not the same set as "the row's widgets", and a binding loop over the
    former leaves most of the row inert.

    **Depth first, parent before child, and that order matters.** A
    CustomTkinter widget's own ``bind`` forwards the handler to the internal
    widgets it is made of, with ``add=True``. Binding the parent first and the
    internals after means the plain ``tkinter`` bind on each internal replaces
    the forwarded copy, so a press fires once. Reverse this traversal and both
    survive, every drag starts twice, and nothing says so.

    It also means a loop over this list overwrites ``<Button-1>`` on every
    descendant, so an interactive widget inside a chip -- a button, a checkbox
    -- would stop responding. Nothing in a chip is interactive today; the
    backlog carries the ``isinstance`` skip for when one is.
    """
    found = [widget]
    for child in widget.winfo_children():
        found.extend(_subtree(child))
    return found


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

        #: Dates the user has said to schedule on anyway, though the
        #: weekday list calls them non-working. The question is about the day,
        #: so it is asked once per date rather than once per drop -- five
        #: items onto a Saturday is one decision, not five.
        self._work_anyway: set = set()

        # Drag state. One drag at a time, and its kind decides what a release
        # means: an item drop creates a block, a block drop reorders the day.
        self._drag_kind: Optional[str] = None
        self._drag_item: Optional[ActionItem] = None
        self._drag_block: Optional[TimeBlock] = None
        self._drag_label: Optional[ctk.CTkLabel] = None
        # What the label will say once the pointer actually moves (PD-M10.3).
        self._drag_label_text: Optional[str] = None
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
        #: PD-M5 — the two always-drawn boxes at the ends of the day, each
        #: paired with which end it is. Kept apart from ``_slot_frames``
        #: because they are not slots: nothing may be placed in them, and a
        #: drop on one lengthens the day before anything is placed at all.
        self._virtual_frames: List[tuple] = []
        #: The task chips this screen bound handlers to, as
        #: (widget, block_id). Only blocks that *start* in a box are in here:
        #: a continuation chip is drawn but owns nothing, so it carries no
        #: drag and no menu.
        self._block_widgets: List[tuple] = []
        #: The grid last drawn, so the summary and the drop rules read the
        #: same object the user is looking at.
        self._grid: DayGrid = DayGrid()
        self._items: List[ActionItem] = []

        #: PD-M2 drag state: where the grip was pressed, the width it was
        #: pressed at, and the width the motion has taken it to. ``None`` for
        #: the press means no drag is in progress, so a stray motion or
        #: release -- Tk delivers both to a widget that was never pressed when
        #: a drag starts elsewhere and ends over it -- does nothing.
        self._divider_from_x: Optional[int] = None
        self._divider_from_width: int = 0
        self._divider_width: int = 0

        # The items column is a fixed width and the day takes the rest.
        # It was a third of the window on a weight of its own, which gave
        # a list of titles as much room as the thing the titles are
        # dragged onto. The width is a setting so it can be sized to the
        # titles the user actually has -- by typing it into Settings, or
        # since PD-M2 by dragging the grip in column 1.
        #: The width the items column is actually drawn at, which is the
        #: setting held inside what both panes need -- not the setting itself.
        self._items_width: int = self.items_col_width()
        self.grid_columnconfigure(0, weight=0, minsize=self._items_width)
        self.grid_columnconfigure(1, weight=0, minsize=PLAN_DIVIDER_WIDTH_PX)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.create_items_pane()
        self.create_divider()
        self.create_day_pane()

        # PD-M2.2 at the other end: the window's own size is as able to squeeze
        # a pane shut as the grip is.
        self.bind("<Configure>", self.on_resize)

        self._ready = True
        self.refresh()

    def items_col_width(self) -> int:
        """Width (px) of the items column, from Settings.

        Purpose: the column is sized by a setting, not by a share of the
                 window.
        Tests:   tests/test_plan_screen.py::test_the_items_column_is_the_width_the_setting_asks_for

        A missing, unparseable or non-positive value falls back rather
        than collapsing the column: a settings file is user-editable, and
        a zero there would hide the list with no way back to it from the
        screen it hid.

        Floored at ``items_width_floor()`` since PD-M1 made a row the day
        chip's four columns, one of which is the 220px Drag Schedule title
        width. At the shipped 260 the row asked for 306px inside a 256px pane
        and the ``30m`` label was laid out past the right edge: measured, not
        inferred -- it was invisible in the app while the first version of
        ``::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it``
        stayed green, because that test built its row at the 80px *fallback*
        title width rather than at the setting's real default. The floor is the
        same one PD-M2's grip clamps to, so the pane the user can drag and the
        pane the screen opens at cannot disagree about what a row needs.
        """
        return self._positive_setting(
            "plan_items_col_width",
            PLAN_ITEMS_COL_WIDTH_PX,
            minimum=self.items_width_floor(),
        )

    def box_height(self) -> int:
        """Height (px) of one task in a day box, from the Drag Schedule setting.

        Purpose: PB-M5 -- the Day Plan boxes are sized by the Drag Schedule
                 box-height setting rather than by a constant.
        Spec:    docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m5
        Tests:   tests/test_plan_screen.py::test_pbm52_the_setting_reaches_the_rendered_box
                 tests/test_plan_screen.py::test_pbm56_a_box_height_below_one_line_of_text_is_raised

        Floored, not merely positive. A box is pinned to
        ``chips * chip_height + 4`` and does not let its contents push it
        taller, while a chip grows to its own text; below one line of text per
        chip the second task in a half hour is laid out past the box's clip
        edge, which is the PB-M2 defect reached through a setting instead of a
        missing ``height=``. ``SLOT_CHIP_HEIGHT_PX`` is that line of text,
        which is also why it is the fallback.
        """
        return self._positive_setting(
            "drag_schedule_box_height_px",
            SLOT_CHIP_HEIGHT_PX,
            minimum=SLOT_CHIP_HEIGHT_PX,
        )

    def box_title_width(self) -> int:
        """Width (px) of a day box's title column, from the Drag Schedule setting.

        Purpose: PB-M5 -- one title width across the two screens that show a
                 task as a row, so the columns line up between them.
        Spec:    docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m5
        Tests:   tests/test_plan_screen.py::test_pbm54_the_title_column_follows_the_drag_schedule_width
        """
        return self._positive_setting(
            "drag_schedule_title_col_width", SLOT_TITLE_WIDTH_PX
        )

    def _positive_setting(
        self, name: str, fallback: int, minimum: Optional[int] = None
    ) -> int:
        """A settings integer, or ``fallback`` when it is missing or unusable.

        A settings file is user-editable, so every size read from one has to
        survive a zero, a negative and a typo. Collapsing a column or a box to
        nothing hides the control the user would need to put it back.

        ``minimum`` raises a value that parses but is too small to draw what
        the dimension has to hold. Positive is not the same bar as usable, and
        a caller that needs the stronger one says so rather than discovering
        it as a clipped widget. The raise is documented in the user guide
        beside the fallback, which is the only surface a hand-edited settings
        file has.

        The fallback is raised too. It did not used to be, and for the box
        height that could not show: there the fallback and the minimum are the
        same constant. For the items column they are not -- the floor is
        derived from the title-column setting -- so a zero in the file took the
        unfloored fallback and clipped the row, which is the defect the
        minimum exists to prevent, reached by the one path that skipped it.
        """
        try:
            value = int(getattr(self.settings, name, None))
        except (TypeError, ValueError):
            value = 0
        if value <= 0:
            value = fallback
        if minimum is not None:
            return max(minimum, value)
        return value

    # ================= construction =========================================

    def create_header(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))

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

        # The one button on this screen that acts on the whole day, so the one
        # that carries the primary colour. Nothing else here is primary, which
        # is the condition the theme rule puts on using it at all.
        self.btn_autoload = ctk.CTkButton(
            header,
            text="AutoLoad",
            width=100,
            command=self.autoload_day,
            **button_style("primary"),
        )
        self.btn_autoload.pack(side="right", padx=4)

        # The reverse of the button beside it, styled as what it is. Danger
        # rather than primary: AutoLoad is this screen's one primary action,
        # and a destructive button that looks like the main one is a misclick
        # waiting to happen.
        self.btn_clear_day = ctk.CTkButton(
            header,
            text="Clear Day",
            width=100,
            command=self.clear_day,
            **button_style("danger"),
        )
        self.btn_clear_day.pack(side="right", padx=4)

        self.status_label = ctk.CTkLabel(header, text="", anchor="e")
        self.status_label.pack(side="right", padx=10)

    def create_items_pane(self):
        frame = ctk.CTkFrame(self)
        frame.grid(
            row=1, column=0, sticky="nsew",
            padx=(PLAN_PANE_EDGE_PAD_PX, 0), pady=10,
        )
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

        # Blocks no box can hold sit under the item list, in the column
        # they have to be dragged from. Its own container rather than a
        # tail of ``items_scroll``: that one is emptied by ``load_items``
        # and this is filled by ``load_blocks``, so sharing it would make
        # the group survive or vanish depending on which ran last.
        #
        # Scrollable, and that is the whole point of the container. The group
        # has no cap -- shortening Day End can put a dozen blocks here at
        # once -- and in a plain frame every row past the bottom of the pane
        # was clipped with no way to reach it. The header counts them, so the
        # screen would have been telling the user that work it had made
        # undraggable was still there (P2).
        self.outside_frame = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", height=OUTSIDE_GROUP_HEIGHT_PX
        )
        self.outside_frame.grid(
            row=3, column=0, sticky="ew", padx=5, pady=(0, 5)
        )
        self.outside_frame.grid_columnconfigure(0, weight=1)
        # Not held back here as well. ``load_blocks`` runs from ``refresh`` in
        # __init__ and grids or ungrids the group on every redraw, so a second
        # grid_remove on this path would be a line no test could fail on --
        # the same reason the chip in a box carries no grid_propagate.

    def items_width_floor(self) -> int:
        """The narrowest the items column may be dragged to, in pixels.

        Purpose: PD-M2.2 -- neither pane can be dragged shut.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m2
        Tests:   tests/test_plan_screen.py::test_pdm22_the_items_pane_cannot_be_dragged_shut

        What one item row asks for, plus the frame, padding and scrollbar
        around it. Derived rather than chosen: the row's columns are the day
        chip's columns and one of them is a user setting, so a round number
        here would be wrong the first time someone widened the title column.
        """
        return sum(chip_column_minsizes(self.box_title_width())) + (
            ITEMS_TEXT_INSET_PX
        )

    def day_width_floor(self) -> int:
        """The narrowest the day pane may be left, in pixels.

        Purpose: PD-M2.2 -- the other end of the same clamp.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m2
        Tests:   tests/test_plan_screen.py::test_pdm22_the_day_pane_cannot_be_dragged_shut

        One day row: the completion check, the time, and the same four columns
        the item row has, plus the pane's own chrome. The chrome is the items
        pane's number because the two panes are the same frame around the same
        scrollable frame, so what is not text is the same on both sides.
        """
        return (
            SLOT_CHECK_WIDTH_PX
            + SLOT_TIME_WIDTH_PX
            + sum(chip_column_minsizes(self.box_title_width()))
            + ITEMS_TEXT_INSET_PX
        )

    def _clamp_items_width(self, width: int) -> int:
        """``width`` held inside what the two panes each need.

        The right-hand end is measured against the real window, which is the
        only place the day's share is known. On a screen that has not been laid
        out ``winfo_width`` is 1, and clamping to that would pin the column to
        its floor for a drag that has not happened yet -- so with no width to
        measure there is no right-hand end, only the floor.

        ``PLAN_PANE_CHROME_PX`` comes off the window first. The window holds
        the two panes, the grip between them and the padding at each edge, and
        the first version compared the floors against the whole of it -- so the
        day pane could be left 26px under its own floor, which is the clipping
        the floors exist to prevent, and widening the grip to 15px would have
        made it 35.

        Tests:   tests/test_plan_screen.py::test_pdm29_the_clamp_leaves_room_for_the_grip_and_the_edges
        """
        floor = self.items_width_floor()
        width = max(floor, int(width))
        room = self.winfo_width()
        if room > 1:
            for_panes = room - PLAN_PANE_CHROME_PX
            width = min(width, max(floor, for_panes - self.day_width_floor()))
        return width

    def apply_items_width(self, width: int) -> int:
        """Draw the items column at ``width``, held inside what both panes need.

        Purpose: PD-M2.2 -- one place that puts a width on the column, so the
                 clamp cannot be bypassed by a caller that sets the minsize
                 itself.
        Tests:   tests/test_plan_screen.py::test_pdm22_a_narrow_window_takes_the_width_from_the_items_pane

        Reconfigures only on a change, because this runs from ``<Configure>``
        and a grid change that fires another ``<Configure>`` would not settle.
        """
        held = self._clamp_items_width(width)
        if held != self._items_width:
            self._items_width = held
            self.grid_columnconfigure(0, minsize=held)
        return held

    def on_resize(self, event=None):
        """Re-divide the two panes when the window's size changes.

        Purpose: PD-M2.2 -- neither pane can be squeezed shut.
        Tests:   tests/test_plan_screen.py::test_pdm22_a_narrow_window_takes_the_width_from_the_items_pane

        The clamp used to run only while the grip was held. Column 0 has a
        minsize and column 2 has a weight, so in a window too narrow for both
        floors the whole shortfall came out of the day pane -- the side with
        nothing holding it open -- and the block length clipped off the right
        edge, which is the defect the floors were added to prevent. A resize
        divides the room by the same rule a drag does: the items column gives
        up width down to its own floor so the day keeps its floor.

        The width asked for is the setting every time, not the width currently
        drawn, so widening the window gives the items pane back what a narrower
        one took off it.
        """
        if not self._ready or self._divider_from_x is not None:
            return
        self.apply_items_width(self.items_col_width())

    def create_divider(self):
        """The grip between the two panes, which drags them wider and narrower.

        Purpose: PD-M2 -- "the dividing line vertical between the two areas
                 should slide right and left to resize the two areas."
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m2
        Tests:   tests/test_plan_screen.py::test_pdm21_dragging_the_grip_changes_the_items_column
                 tests/test_plan_screen.py::test_pdm28_the_grip_is_the_whole_gap_between_the_panes

        Its own ``PLAN_DIVIDER_WIDTH_PX`` column rather than a border on
        either pane: a border
        belongs to the frame that draws it and cannot be pressed without
        pressing the pane, and a pane here is a drag surface already.

        Not ``ColumnResizer``. That widget resizes columns inside a table row
        and persists to ``<prefix>_col_widths``; this is a splitter between two
        top-level grid columns writing one integer setting, and the two have
        nothing but the gesture in common.
        """
        self.divider = ctk.CTkFrame(
            self,
            width=PLAN_DIVIDER_WIDTH_PX,
            fg_color=semantic_colors()["border"],
            corner_radius=0,
        )
        self.divider.grid(row=1, column=1, sticky="ns", pady=10)
        self.divider.grid_propagate(False)
        # The cursor is the only thing on screen that says this is draggable,
        # so it is set here rather than left to the theme.
        try:
            self.divider.configure(cursor="sb_h_double_arrow")
        except tk.TclError:
            # A cursor name X11 or the platform does not know is not a reason
            # to lose the divider.
            pass
        self.divider.bind("<Button-1>", self.on_divider_press)
        self.divider.bind("<B1-Motion>", self.on_divider_motion)
        self.divider.bind("<ButtonRelease-1>", self.on_divider_release)

    def on_divider_press(self, event):
        """Remember where the grip was pressed, and at what width.

        The width drawn, not the width in the settings file. They differ
        whenever the window is too narrow for the setting -- which the resize
        clamp made an ordinary state rather than an edge case -- and taking the
        setting here meant a bare click on the grip saved the clamped width
        over it. A 600px setting in a 900px pane became 442px on a click that
        moved nothing, so widening the window afterwards no longer gave the
        600 back, and the first 158px of a leftward drag did nothing.
        """
        self._divider_from_x = event.x_root
        self._divider_from_width = self._items_width
        self._divider_width = self._divider_from_width

    def on_divider_motion(self, event):
        """Resize the columns to follow the pointer. Nothing is written here.

        Measured from the press, not from the last motion: applying each
        motion's own delta to the current width doubles every drag after the
        first, and the clamp would make the error silent at the ends.
        """
        if self._divider_from_x is None:
            return
        moved = event.x_root - self._divider_from_x
        self._divider_width = self.apply_items_width(
            self._divider_from_width + moved
        )

    def on_divider_release(self, event):
        """Take the final position and write it, once.

        P41: ``self.settings`` is the app's own settings object, not a copy of
        it. So a refused write cannot be left as it is -- every screen built
        from that object afterwards would draw a width no file holds, and the
        next launch would undo it with nothing having said so. The previous
        value goes back on the object and on the column, and the refusal is
        reported where the pane the user just dragged can show it.
        """
        if self._divider_from_x is None:
            return
        self.on_divider_motion(event)
        self._divider_from_x = None

        width = self._divider_width
        if self.settings is None or width == self._divider_from_width:
            return

        previous = getattr(self.settings, "plan_items_col_width", None)
        self.settings.plan_items_col_width = width
        if not self.settings.save():
            self.settings.plan_items_col_width = previous
            self.apply_items_width(self.items_col_width())
            self.items_hint.configure(
                text=(
                    getattr(self.settings, "last_save_error", None)
                    or "Could not write the settings file — see the log"
                )
            )

    def create_day_pane(self):
        frame = ctk.CTkFrame(self)
        frame.grid(
            row=1, column=2, sticky="nsew",
            padx=(0, PLAN_PANE_EDGE_PAD_PX), pady=10,
        )
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

    def _flush_redraw(self):
        """Put a rebuilt pane on screen now, rather than at the next event.

        Purpose: PD-M10 -- both panes are rebuilt by taking the scroll frame
                 out of the grid, destroying its children and putting it back.
                 Tk draws from an idle handler, and every one of these rebuilds
                 runs inside an event callback or an ``after_idle`` of one, so
                 the re-gridded frame could stay undrawn until some later event
                 arrived. In the app that event was the next mouse movement
                 over the window: moving a block, resizing one or deleting one
                 wrote the day correctly and looked like a gesture that had
                 done nothing.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m10
        Tests:   tests/test_plan_screen.py::test_pdm101_rebuilding_the_day_pane_flushes_the_redraw

        ``update_idletasks`` and not ``update``: idle tasks are geometry and
        redisplay, which is all that is owed here. ``update`` also services the
        event queue, and these rebuilds run from drag handlers -- dispatching a
        queued click in the middle of one would re-enter a rebuild that is
        destroying the widget the click is for, which is the hang the
        ``after_idle`` in ``on_drag_release`` exists to avoid.
        """
        try:
            self.update_idletasks()
        except tk.TclError:
            # The screen went away while a rebuild was in flight: a window
            # closing, or a date change whose redraw outlived the screen.
            # There is nothing left to draw, and raising here would turn a
            # closed window into an error on the way out.
            pass

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
                # anchor and wraplength both matter here. CTkLabel centres its
                # text by default, so a label wider than its cell overflows on
                # both sides and Tk clips both -- which read as a sentence
                # missing its first word. The hard line breaks this text used
                # to carry were sized for a column that was a third of the
                # window; the column is now a setting, so the text wraps to it.
                ctk.CTkLabel(
                    self.items_scroll,
                    text=(
                        "No open items start on this date.\n\n"
                        "This list is filtered on each item's Start Date, so "
                        "an item with the wrong start date will not appear "
                        "here."
                    ),
                    anchor="w",
                    justify="left",
                    wraplength=max(
                        NOTE_MIN_WRAP_PX,
                        self.items_col_width() - ITEMS_TEXT_INSET_PX,
                    ),
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
                        box_height=self.box_height(),
                        title_width=self.box_title_width(),
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
            self._flush_redraw()

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
            # Unconditional: emptied only inside the "there are blocks
            # outside the day" branch, the last group drawn would stay on
            # screen after the day that had one was left.
            for widget in self.outside_frame.winfo_children():
                widget.destroy()
            self._slot_frames = []
            self._virtual_frames = []
            self._block_widgets = []

            # Place anything that has never been on the grid before drawing,
            # so a day stored by the old model reads as a day rather than as a
            # list of blocks outside it. Idempotent, so this is a no-op on
            # every load after the first.
            #
            # Guarded because this is the one irreversible write on this
            # screen: it turns a stored clock time into a box, the box is
            # relative to Day Start, and ``_settle_block_on_slot`` overwrites
            # the stored time that said otherwise. Run against a Day Start we
            # are only guessing at, it moves planned work to an hour nobody
            # picked and destroys the record of what was picked. A settings
            # file that exists and cannot be read is exactly that guess, so
            # the blocks keep their NULL -- which ``build_day_grid`` surfaces
            # as outside the day -- until the day's shape is known (P1: a
            # transient read failure must not be written down as a fact).
            adopted = []
            if self._day_shape_is_the_users():
                adopted = self.db_manager.adopt_legacy_day(
                    self.selected_date, self.bounds
                )

            blocks = self.db_manager.get_time_blocks(self.selected_date)
            self._grid = build_day_grid(blocks, self.bounds)
            items_by_id = self._items_by_id(blocks)

            self.update_day_summary(blocks)

            # Adoption is irreversible and was previously silent: the ids it
            # returns were thrown away. Named with the Day Start it used, so
            # the assumption it baked in is visible and checkable rather than
            # something to infer from blocks that moved.
            if adopted:
                self.set_status(
                    f"Placed {len(adopted)} block(s) from an earlier version"
                    f" on the grid, using a day start of {self.bounds.day_start}",
                    "muted",
                )
            elif self._day_shape_is_unconfirmed() and any(
                block.slot_index is None for block in blocks
            ):
                # Both halves are load-bearing. Without the first this also
                # fires when no settings object was supplied at all, which is a
                # wiring mistake and nothing the user can act on. Without the
                # second it fires on every date change of an ordinary day,
                # naming blocks from an earlier version that do not exist.
                #
                # No cause named, deliberately. There are three, and the
                # message cannot tell which: a settings file that would not
                # parse, a file from a version that had no Day Settings --
                # which is every version before this one, so it is the common
                # one -- and a day time the app had to substitute. An earlier
                # wording blamed the file for all three and was false for the
                # one that happens most. What is true in every state it can
                # appear in is the state itself, and the remedy, which is one
                # screen.
                self.set_status(
                    "Your day's shape has not been confirmed, so blocks from an"
                    " earlier version are left off the grid — open ⚙ Day"
                    " Settings and save to place them",
                    "warning",
                )

            row = 0
            # PD-M5 — above the first box and below the last, every redraw,
            # whether or not the day has anything in it. A drop target that
            # appears only once there is something to drop past would not be
            # there for the first item of the day.
            self._virtual_frames.append((
                build_virtual_slot_row(
                    self.blocks_scroll,
                    row,
                    label=PD_EARLIER_TEXT,
                    hint=PD_EARLIER_HINT,
                    chip_height=self.box_height(),
                ),
                DAY_EXTEND_EARLIER,
            ))
            row += 1

            for entry in self._grid.slots:
                rendered = build_slot_row(
                    self.blocks_scroll,
                    entry,
                    items_by_id,
                    row,
                    chip_height=self.box_height(),
                    title_width=self.box_title_width(),
                )
                self._slot_frames.append((rendered.frame, entry.slot.index))
                for block, widget in rendered.block_widgets:
                    self.bind_block_handlers(widget, block)
                    self._block_widgets.append((widget, block.id))
                row += 1

            self._virtual_frames.append((
                build_virtual_slot_row(
                    self.blocks_scroll,
                    row,
                    label=PD_LATER_TEXT,
                    hint=PD_LATER_HINT,
                    chip_height=self.box_height(),
                ),
                DAY_EXTEND_LATER,
            ))
            row += 1

            if not blocks:
                build_empty_day_note(self.blocks_scroll, row)
                row += 1

            # Surfaced beneath the item list, never dropped (P2). Under
            # the items rather than under the grid: a block here is one
            # the user has to drag onto a box, which is the same move as
            # an item above it, from the same column.
            if self._grid.outside:
                self.outside_frame.grid()
                for block, widget in build_outside_group(
                    self.outside_frame,
                    self._grid.outside,
                    items_by_id,
                    0,
                    chip_height=self.box_height(),
                    title_width=self.box_title_width(),
                ):
                    self.bind_block_handlers(widget, block)
                    self._block_widgets.append((widget, block.id))
            else:
                self.outside_frame.grid_remove()
        finally:
            self.blocks_scroll.grid(**grid_info)
            self._flush_redraw()

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

        With no ``slot_index`` it takes the first box that will hold it.
        No UI path passes that today -- every drop names the box under the
        pointer -- so it is the API's answer for a caller with no pointer to
        read, and the toolbar's ``add_padding_block`` is the one that needs it.
        An earlier version of this docstring claimed an item-row double-click
        used it; there has never been such a binding (`BACKLOG.md`).
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

    def autoload_day(self):
        """PD-M3 — block every item the day still has room for, in list order.

        Purpose: fill the day from the item list in one click, one item after
                 another, at the earliest box that holds each.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m3
        Tests:   tests/test_plan_screen.py::test_pdm31_autoload_fills_in_list_order

        Purely additive. It never moves, resizes or deletes a block that is
        already there, which is what makes it undoable by hand in an app with
        no undo, and it does not extend the day: lengthening the working day is
        PD-M5's deliberate gesture, not something a button does quietly.

        One transaction, so a refusal part-way leaves none of it rather than
        half a planned day. ``first_free_slot`` re-reads the day inside that
        transaction, on the same connection, so each item is placed after the
        one before it rather than all of them into the same box.

        The item list is re-read rather than taken from ``self._items``. It is
        the same query and the same cap the pane draws, so in the ordinary case
        it is the list on screen; where the two differ the list on screen is
        the stale one, and blocking an item that has since been completed
        elsewhere is not what the click asked for.

        It places through ``first_clear_slot``, not ``first_free_slot``, which
        is a correction to the approved plan rather than what it said. See that
        method for why.
        """
        if not self._require_block_day():
            return

        items = self.db_manager.get_items_for_start_date(self.selected_date)
        shown = items[:MAX_ITEM_ROWS]
        # What the row cap takes off the end, counted so the report can say it
        # (P2/P9). The pane announces its own cap; a button that silently
        # planned 60 of 73 items and reported "blocked 12 of 60" would not.
        unseen = len(items) - len(shown)
        if not shown:
            self.set_status(
                "AutoLoad: nothing to block — no open items start on "
                f"{self.selected_date}",
                "warning",
            )
            return

        blocked_ids = self.db_manager.get_blocked_item_ids(self.selected_date)
        placed = 0
        no_room = 0
        already = 0
        try:
            with self.db_manager.transaction():
                for item in shown:
                    if item.id in blocked_ids:
                        already += 1
                        continue
                    minutes = duration_for_item(
                        item, self.bounds.default_block_minutes
                    )
                    slot_index = self.first_clear_slot(minutes)
                    if slot_index is None:
                        no_room += 1
                        continue
                    self.db_manager.add_block_at(
                        TimeBlock(
                            block_date=self.selected_date,
                            start_time="",
                            end_time="",
                            planned_minutes=minutes,
                            item_id=item.id,
                            label=item.title,
                            block_type=BlockType.ITEM,
                        ),
                        slot_index,
                        self.bounds,
                    )
                    placed += 1
        except SlotRefusedError as refused:
            # Counted and said, never swallowed. A refusal here is the day
            # disagreeing with the box first_clear_slot just offered, which is
            # a bug rather than a full day -- and the transaction has already
            # taken the earlier items back out, so the number that would have
            # been written is part of the report.
            self.refresh()
            # ``len(shown)`` here, not ``len(items)``: this is how far the run
            # got through what it was going to try, and the items past the cap
            # were never going to be tried at all. They are still named, so the
            # sentence accounts for the whole list either way.
            tried = f"{placed} of {len(shown)} tried"
            if unseen:
                tried += f", {unseen} past the {MAX_ITEM_ROWS}-row list"
            self.set_status(
                f"AutoLoad wrote nothing — {refusal_text(refused.reason)} "
                f"(refused after {tried})",
                "error",
            )
            return
        except Exception as problem:
            # Anything else. The transaction has rolled back, so the day on
            # screen is the day in the database -- but without this arm the
            # exception leaves a Tk callback with nothing redrawn and nothing
            # said, and a press that failed looks exactly like a press that
            # found nothing to do.
            # Logged as well as said. The status line is transient -- the next
            # set_status overwrites it -- and this arm turns what would have
            # been a traceback into one sentence, so without the log an
            # AttributeError in here leaves nothing behind to diagnose it by.
            logger.exception("AutoLoad failed")
            self.refresh()
            self.set_status(
                # ``str(problem)``, not ``problem``: an exception instance is
                # always truthy, so ``problem or ...`` can never take its
                # second branch, and a message-less built-in such as
                # ``KeyError()`` ended the sentence at the dash.
                f"AutoLoad wrote nothing — "
                f"{str(problem) or type(problem).__name__}",
                "error",
            )
            return

        self.refresh()
        # Every count, every time (P2): "blocked 4" alone cannot be told apart
        # from "blocked 4 and quietly dropped 7", and the four numbers add up
        # to the whole list rather than to the part of it that was tried.
        said = (
            f"AutoLoad: blocked {placed} of {len(items)} — "
            f"{no_room} did not fit, {already} already blocked"
        )
        if unseen:
            said += f", {unseen} past the {MAX_ITEM_ROWS}-row list"
        self.set_status(said, "success" if placed else "warning")

    def clear_day(self):
        """PD-M8 — take every scheduled item back off the day.

        Purpose: the reverse of AutoLoad. One click that empties the day of
                 tasks, so a plan can be thrown away and redone.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m8
        Tests:   tests/test_plan_screen.py::test_pdm8_clear_day_removes_every_item_block
                 tests/test_plan_screen.py::test_pdm8_clear_day_leaves_breaks_and_buffers
                 tests/test_plan_screen.py::test_pdm8_answering_no_removes_nothing
                 tests/test_plan_screen.py::test_pdm8_a_day_with_no_items_says_so

        Item blocks only, because that is what AutoLoad writes. A break or a
        buffer was put there by hand, one gesture each, and taking them out
        would be a deletion nobody asked for -- so the question says how many
        are staying, since a button called Clear Day that leaves two blocks
        behind has to account for them where the user is looking.

        Asked first. This is the only button on the screen that destroys work,
        the app has no undo, and the count is in the question so the answer is
        given against the real day rather than against the word "all".

        No ``_require_block_day``: the weekday list is about planning work
        onto a day, and taking work off one is not planning. A Saturday that
        was filled -- by a Yes to PD-M7, or before the week was narrowed --
        has to be clearable without being asked about the week again.

        One transaction, so a failure part-way leaves the day as it was rather
        than half-cleared. ``delete_time_block`` commits on its own, which the
        transaction's commit gate suppresses -- that gate is what makes the
        rollback real here.
        """
        blocks = self.db_manager.get_time_blocks(self.selected_date)
        mine = [
            block for block in blocks
            if BlockType.normalize(block.block_type) == BlockType.ITEM
        ]
        kept = len(blocks) - len(mine)
        if not mine:
            self.set_status(
                f"Clear Day: nothing to remove — no items are scheduled on "
                f"{self.selected_date}",
                "warning",
            )
            return

        question = (
            f"Remove {len(mine)} scheduled "
            f"{'item' if len(mine) == 1 else 'items'} from "
            f"{self.selected_date}?"
        )
        if kept == 1:
            question += "\n\nThe one break or buffer block stays where it is."
        elif kept:
            question += (
                f"\n\nThe {kept} break and buffer blocks stay where they are."
            )
        question += "\n\nThis cannot be undone."
        if not messagebox.askyesno(
            "Clear Day", question, icon="warning", parent=self
        ):
            self.set_status("Clear Day: nothing removed", "muted")
            return

        try:
            with self.db_manager.transaction():
                for block in mine:
                    self.db_manager.delete_time_block(block.id)
        except Exception as problem:
            # The same arm AutoLoad has, for the same reason: without it a
            # failure leaves a Tk callback with nothing redrawn and nothing
            # said, and a press that failed looks like a press that found
            # nothing to do. Logged as well as said, because the status line
            # is overwritten by the next one.
            logger.exception("Clear Day failed")
            self.refresh()
            self.set_status(
                f"Clear Day removed nothing — "
                f"{str(problem) or type(problem).__name__}",
                "error",
            )
            return

        self.refresh()
        # Both numbers, every time (P2): "removed 4" cannot be told apart
        # from "removed 4 and quietly left 2 it should have taken", and the
        # blocks left behind are the ones the question promised to keep.
        said = f"Clear Day: removed {len(mine)} of {len(blocks)} blocks"
        if kept == 1:
            said += " — 1 break or buffer left in place"
        elif kept:
            said += f" — {kept} break and buffer blocks left in place"
        self.set_status(said, "success")

    def first_clear_slot(self, minutes: int) -> Optional[int]:
        """The earliest box in today's grid with nothing in it at all.

        Purpose: PD-M3 -- "one after another", for AutoLoad.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m3
        Tests:   tests/test_plan_screen.py::test_pdm31_autoload_fills_in_list_order

        Not ``first_free_slot``, which is the earliest box that is not *full*.
        A box holds four tasks, so on an empty default day first_free_slot
        answers 08:00 four times running: AutoLoad would have stacked the first
        four items four deep at 08:00, the next four at 08:30, and called it a
        planned day. The approved plan named first_free_slot and said that was
        what "one after another" meant on a grid with work already in it. It is
        not -- the depth is there for a second task a person deliberately puts
        beside a first, and a button that fills it is not planning a day.

        Every box of a multi-box task has to be clear, not only the first: a
        90m task at 08:00 covers 08:00, 08:30 and 09:00, and dropping it on top
        of something already sitting at 09:00 is the same defect one box along.
        """
        from ..time_block_layout import can_place, slot_occupancy

        blocks = self.db_manager.get_time_blocks(self.selected_date)
        span = slots_for_minutes(minutes)
        occupancy = slot_occupancy(blocks, self.bounds)
        for entry in self._grid.slots or build_day_grid(blocks, self.bounds).slots:
            index = entry.slot.index
            if can_place(blocks, self.bounds, index, span) is not None:
                continue
            if any(occupancy.get(index + step) for step in range(span)):
                continue
            return index
        return None

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
        """Ask before writing a block onto a day the user does not work.

        Purpose: PD-M7 -- a day outside the working week is a warning, not a
                 wall.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m7
        Tests:   tests/test_plan_screen.py::test_pdm7_a_non_work_day_asks_before_scheduling
                 tests/test_plan_screen.py::test_pdm7_answering_no_writes_nothing
                 tests/test_plan_screen.py::test_pdm7_a_work_day_asks_nothing

        Asked rather than refused. The weekday list describes a normal week;
        it is not a lock on the calendar, and a Saturday someone has decided
        to work is not a mistake to be corrected. The screen opens on today,
        so on a weekend every write path returned before doing anything --
        AutoLoad before it read a single item, a dropped item before it wrote
        one -- and four separate gestures doing nothing read as the screen
        being broken rather than as the day being closed.

        Once per date, not once per drop: the question is about the day, so
        five items onto the same Saturday is one decision. The answer is held
        on the screen rather than written anywhere, so it lasts as long as the
        screen does and no longer -- it is permission for this sitting, not a
        change to the working week, which is what Day Settings is for.

        Declining leaves the same sentence the refusal used to, which is why
        the weekday list is in it: the answer to "why did nothing happen" is
        the days the week is set to.
        """
        if is_block_day(self.selected_date, self.bounds):
            return True
        if self.selected_date in self._work_anyway:
            return True

        allowed = [
            name for name, on in zip(weekday_names(), self.bounds.block_weekdays) if on
        ]
        week = ", ".join(allowed) if allowed else "no days"
        if messagebox.askyesno(
            "Not a work day",
            f"{self.selected_date} is not a regular work day.\n\n"
            f"Day Settings allows {week}.\n\n"
            "Schedule anyway?",
            icon="warning",
            parent=self,
        ):
            self._work_anyway.add(self.selected_date)
            return True

        self.set_status(
            f"{self.selected_date} is not a block day (Day Settings allows "
            f"{week})",
            "warning",
        )
        return False

    # ================= the block context menu ===============================

    def bind_block_handlers(self, frame, block: TimeBlock):
        """Bind drag and menu to every widget in a block's subtree.

        Every descendant, not only the direct children: an outside-day row
        wraps its chip in a holder, so the title and minutes labels sit two
        levels down and a press on the text -- most of the row -- reached
        nothing at all.

        Tests: tests/test_plan_screen.py::test_every_part_of_an_outside_row_starts_a_drag
        """
        for widget in _subtree(frame):
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
        if block.slot_index is None:
            # Reachable by an ordinary gesture: the outside-day group binds
            # this same menu. Said in the screen's words -- the database's
            # message is for a programmer and carries the row id.
            self.set_status(
                "That block is not on a box yet — drag it onto a half hour first",
                "error",
            )
            return

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
        self._arm_drag_label(item.title)

    def start_block_drag(self, _event, block: TimeBlock):
        self._drag_kind = "block"
        self._drag_block = block
        self._drag_item = None
        self._arm_drag_label(block.label or block.block_type.title())

    def _arm_drag_label(self, text: str):
        """Hold the label's text until the pointer moves.

        Purpose: PD-M10.3 -- every press on a row is the start of a drag as far
                 as these handlers know, so showing the label here put one
                 under the pointer on an ordinary click as well. The click's
                 release hid it again, but on a platform that draws at idle the
                 hiding was not on screen either, and the name of whatever was
                 clicked sat beside the pointer until something else repainted
                 the screen.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m10
        Tests:   tests/test_plan_screen.py::test_pdm103_a_press_without_motion_shows_no_drag_label

        A press with no motion is not a drag, so it gets no label at all. The
        first motion is what makes it one.
        """
        self._drag_label_text = text

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
        armed = self._drag_label_text
        if armed is not None:
            # PD-M10.4 -- the pointer has moved, so this is a drag. Cleared
            # first: _show_drag_label is what puts it on screen, and a second
            # motion must reposition the label rather than build it again.
            self._drag_label_text = None
            self._show_drag_label(armed)
        else:
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
        # Both read, and the order of the branches below is what decides
        # between them: a half hour that exists always wins. Computing the
        # edge only when no box matched would make the two guards mutually
        # exclusive by construction, and a precedence nothing can get wrong is
        # also a precedence no test can check.
        edge = self.virtual_under_pointer()
        if kind == "item" and item is not None:
            if target is not None:
                self.after_idle(lambda: self.block_item(item, target))
            elif edge is not None:
                self.after_idle(lambda: self.extend_day_for(item, edge))
            elif self.pointer_over_day():
                # In the day column but not on a box -- the heading, the
                # summary, or the "outside the day" group below the grid.
                # Reported rather than guessed at: picking a box for them
                # would put the work somewhere they did not point.
                self.set_status("Drop an item on a half-hour box", "muted")
        elif kind == "block" and block is not None:
            if target is not None:
                self.after_idle(lambda: self.move_block_to_slot(block.id, target))
            elif edge is not None:
                # PD-M5.7 — the day grows to make room for work that is not
                # planned yet, not to rehouse work that already has a box. A
                # block dropped here would be asking the day to lengthen for
                # something it is already long enough to hold.
                self.set_status(
                    "A block cannot make a new half hour — move it onto a box, "
                    "or drag an item here to lengthen the day",
                    "warning",
                )
            elif self.pointer_over_day():
                # Same reason as the item branch above, and the same words'
                # worth of explanation: a move that does nothing and says
                # nothing is indistinguishable from a drag that missed.
                self.set_status("Drop a block on a half-hour box", "muted")

    def _end_drag(self):
        """Take the label off the screen and forget what was being dragged.

        Purpose: PD-M10.5 -- a release that lands on nothing writes nothing and
                 redraws nothing, so without the flush here the label stayed
                 visible until some later event repainted the screen.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m10
        Tests:   tests/test_plan_screen.py::test_pdm105_ending_a_drag_hides_the_label_and_flushes

        Flushing from inside the ButtonRelease handler is safe here and only
        here: ``on_drag_release`` calls this before it schedules the drop's own
        ``after_idle``, so there is no queued rebuild for the flush to dispatch
        into the widget that is dispatching this event.
        """
        self._drag_label_text = None
        if self._drag_label is not None:
            self._drag_label.place_forget()
            self._flush_redraw()
        self._drag_kind = None
        self._drag_item = None
        self._drag_block = None

    def _day_shape_is_the_users(self) -> bool:
        """Whether ``self.bounds`` came from settings we could actually read.

        Purpose: TG-M5 -- adoption is irreversible, so it must not run on a
                 guess. A settings file that exists but failed to parse yields
                 an all-defaults object, which is indistinguishable from a
                 real fresh install unless the loader says so -- and says so in
                 a field that goes to disk, since the first save from any
                 screen writes those defaults out as ordinary settings.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
        Tests:   tests/test_plan_screen.py::test_adoption_does_not_run_on_a_guessed_day_start
        """
        if self.settings is None:
            return False
        return not self._day_shape_is_unconfirmed()

    def _day_shape_is_unconfirmed(self) -> bool:
        """Whether these four day values are a stand-in nobody has confirmed.

        Purpose: TG-M5 -- the narrower of the two questions, and the one with a
                 remedy. "Not the user's" covers a missing settings object too,
                 which is a wiring mistake and nothing the user can act on;
                 this one is a day shape they can confirm in a dialog, so this
                 is the one worth telling them about.
        Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
        Tests:   tests/test_plan_screen.py::test_no_settings_object_is_not_reported_as_an_unconfirmed_day
        """
        if self.settings is None:
            return False
        return bool(getattr(self.settings, "plan_day_shape_unconfirmed", False))

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

    def virtual_under_pointer(self) -> Optional[str]:
        """Which end of the day the pointer is over, or ``None``.

        Purpose: PD-M5 -- the two boxes that are not slots.
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m5
        Tests:   tests/test_plan_screen.py::test_pdm52_a_drop_above_moves_day_start_back

        Read the same way as ``slot_under_pointer`` and only after it has
        answered ``None``: a real box always wins, so the two boxes can sit
        flush against the grid without stealing a drop meant for 08:00.
        """
        x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
        if not widget_contains_pointer(self.blocks_scroll, x_root, y_root):
            return None

        for frame, edge in self._virtual_frames:
            if widget_contains_pointer(frame, x_root, y_root):
                return edge
        return None

    def extend_day_for(self, item: ActionItem, edge: str):
        """PD-M5 — lengthen the day at one end and block the item in the room it made.

        Purpose: "allow items to extend the day earlier or later when they are
                 dropped above the first block or below the last".
        Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m5
        Tests:   tests/test_plan_screen.py::test_pdm52_a_drop_above_moves_day_start_back

        ``plan_day_shape_unconfirmed`` is left exactly as it was found
        (PD-M5.4), by not being touched at all. ``AppSettings.save`` does write
        the field -- it writes every field -- but it never changes its value,
        and ``_day_shape_was_confirmed`` only reads a literal ``False``, so a
        save here cannot confirm a day shape. Lengthening a day is not the user
        confirming the four
        values the flag gates, and that flag is what stops the irreversible
        grid adoption running against a day shape nobody chose. An earlier
        version of this method snapshotted it and put it back on the failure
        path; the mutation gate showed that line could never change anything,
        because nothing on any path here sets it.

        One unit of work. The settings write is the last thing inside the
        database transaction, so a refused write takes the renumbering and the
        new block back out with it rather than leaving the file and the day
        disagreeing about where the day starts (P41: ``self.settings`` is the
        app's own object, so the attribute has to go back too).

        This renumbers and ``on_settings_saved`` (TG-M6.4) does not, and the
        difference is the gesture rather than an inconsistency. Typing a new
        Day Start into Settings is a decision about what the day is, and
        re-timing the work inside it is what that decision means. Dropping one
        item above the first box is a decision about that item: the bound moves
        as a side effect, so everything already planned -- on this date and
        every other -- has to stay where the person put it.
        """
        if not self._require_block_day():
            return
        if self.settings is None:
            self.set_status(
                "The day's hours cannot be changed without a settings file",
                "error",
            )
            return

        minutes = duration_for_item(item, self.bounds.default_block_minutes)
        span = slots_for_minutes(minutes)
        new_bound = extended_day_bound(self.bounds, edge, span)
        if new_bound is None:
            where = "before midnight" if edge == DAY_EXTEND_EARLIER else "past midnight"
            self.set_status(
                f"{minutes}m of {item.title} would put the day {where}; "
                "a day is one date",
                "warning",
            )
            return

        key = (
            "plan_day_start" if edge == DAY_EXTEND_EARLIER else "plan_day_end"
        )
        previous = getattr(self.settings, key)
        # Where the item lands. Earlier: box 0 of the day that is about to
        # exist, the others having been renumbered past it. Later: the first
        # box the old day did not have, which is the old box count.
        slot_index = 0 if edge == DAY_EXTEND_EARLIER else len(day_grid(self.bounds))

        setattr(self.settings, key, new_bound)
        new_bounds = DayBounds.from_settings(self.settings)
        block = TimeBlock(
            block_date=self.selected_date,
            start_time="",
            end_time="",
            planned_minutes=minutes,
            item_id=item.id,
            label=item.title,
            block_type=BlockType.ITEM,
        )
        wrote_the_file = False
        try:
            with self.db_manager.transaction():
                if edge == DAY_EXTEND_EARLIER:
                    # Before the new block, and before anything reads the day:
                    # a slot index counts boxes from Day Start, so moving Day
                    # Start without renumbering slides every planned task
                    # earlier on the clock (PD-M5.5). Every date, because
                    # Day Start is one setting for all of them.
                    self.db_manager.shift_all_slots(span)
                self.db_manager.add_block_at(block, slot_index, new_bounds)
                if not self.settings.save():
                    raise _DayNotWritten(
                        self.settings.last_save_error
                        or "the day's new hours could not be saved"
                    )
                wrote_the_file = True
        except Exception as problem:
            # Broad on purpose. Whatever failed, the file and the database have
            # to agree about where the day starts, and the only way to promise
            # that is to put the day back on every path out of here. The
            # settings write is last inside the transaction, so in every
            # failure but a commit that itself fails the file was never
            # touched and the attribute is the whole of it.
            setattr(self.settings, key, previous)
            restored = True
            if wrote_the_file:
                restored = bool(self.settings.save())
            self.refresh()
            if isinstance(problem, SlotRefusedError):
                said = refusal_text(problem.reason)
            else:
                # The class name when the exception carries no message, which
                # several built-ins do: "The day was not extended — " with
                # nothing after the dash is a sentence that says less than the
                # failure it is reporting.
                said = str(problem) or type(problem).__name__
            if not restored:
                said += (
                    " — and the day's hours could not be put back; "
                    "check ⚙ Day Settings"
                )
            self.set_status(f"The day was not extended — {said}", "error")
            return

        self.bounds = new_bounds
        self.refresh()
        self.set_status(
            f"The day now runs {new_bounds.day_start}–{new_bounds.day_end}; "
            f"blocked {minutes}m for {item.title} at {block.start_time}",
            "success",
        )

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
