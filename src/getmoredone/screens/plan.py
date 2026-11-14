"""Plan screen — time blocks and daily planning.

Purpose: pick a day, see the action items that start on it, drag them into a
         packed day of blocks, and rearrange, resize or pad that day.
Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_blocks.md
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
import gc
import threading
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
    can_place,
    default_minutes_for_block_type,
    duration_for_item,
    edge_limit_time,
    extended_span,
    is_block_day,
    slots_for_minutes,
    times_for_slot,
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
from .plan_commitment_edits import PlanCommitmentEditsMixin
from .plan_commitments import PlanCommitmentsMixin, commitments_by_slot
from .plan_settings_dialog import PlanSettingsDialog
from .plan_week_view import PlanWeekViewMixin
from .segment_color_utils import resolve_segment_color_for_item

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

#: How close (px) to the top or bottom edge of the day's scrolling viewport
#: the pointer has to come, during a drag, for the day to scroll itself
#: (PD-M11.5). Deep enough to reach with a dragged pointer, and shallow enough
#: that the top and bottom boxes of the view can still be dropped on.
PLAN_AUTOSCROLL_EDGE_PX = 32

#: How far (px) one autoscroll tick moves the day.
PLAN_AUTOSCROLL_STEP_PX = 24

#: Milliseconds between autoscroll ticks while the pointer is held in the edge
#: zone. A pointer held still delivers no motion events, so the scroll cannot
#: be driven by motion alone -- it has to be its own clock.
PLAN_AUTOSCROLL_MS = 60

#: Height (px) of the "Outside the day" group. Fixed and scrollable rather
#: than as tall as its contents: the group shares the items column with the
#: item list, and a dozen blocks growing it would push the list it sits under
#: off the bottom of the pane.
OUTSIDE_GROUP_HEIGHT_PX = 150

# ``NOTE_MIN_WRAP_PX = 120`` was here, a floor on the note's wraplength.
# Deleted (P27): PBG-M1's badge raised ``items_width_floor``, so the narrowest
# column leaves 169px and the floor could not fire. The column's own floor is
# what keeps the note wrapping.

#: Days with a calendar export in flight, keyed by (database path, day), and
#: the lock that guards the set.
#:
#: The marker cannot live on the screen instance. ``App.show_plan`` clears the
#: content frame and builds a **new** ``PlanScreen`` on every navigation, so
#: leaving the Plan screen and coming back gives a second screen whose
#: ``_export_running`` is False while the first screen's worker is still
#: exporting -- two exports of one day, racing over the same rows. The loser
#: writes an event id the winner has already replaced, so the work ends up on
#: no calendar, with no id in the database and two success lines on screen
#: (found by a cold review pass).
#:
#: Keyed by the database path as well as the day because a test fixture, or a
#: second window, may be on another database entirely, where the same date is
#: a different day's work.
_EXPORTS_IN_FLIGHT: set = set()
_EXPORTS_LOCK = threading.Lock()


def _claim_export(db_path, block_date) -> bool:
    """Take the one export slot for a day, or report that it is taken.

    Purpose: CE-M4.4 -- one export per day per database, across screens.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m44
    Tests:   tests/test_plan_screen_calendar_export.py::test_cem444c_a_second_screen_cannot_export_the_same_day

    Test-and-add under the lock, because the test and the add have to be one
    step: two threads that checked first and added afterwards would both see
    an empty set.
    """
    key = (str(db_path), str(block_date))
    with _EXPORTS_LOCK:
        if key in _EXPORTS_IN_FLIGHT:
            return False
        _EXPORTS_IN_FLIGHT.add(key)
        return True


def _release_export(db_path, block_date) -> None:
    """Give the slot back. Called from whichever thread finishes with it."""
    with _EXPORTS_LOCK:
        _EXPORTS_IN_FLIGHT.discard((str(db_path), str(block_date)))


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
    SlotRefusal.OUTSIDE_GRID: "That Time Block is outside the day — Day Settings sets its hours",
    SlotRefusal.CROSSES_LUNCH: "That Time Block runs into lunch — try a later one",
    SlotRefusal.SLOT_FULL: "That Time Block is full — try another one",
    SlotRefusal.LUNCH_EXISTS: "This day already has a lunch — drag that one to move it",
    # CIP-M3.3 -- a Google Calendar event holds the box.
    SlotRefusal.SLOT_COMMITTED: "A calendar event holds that Time Block — try another one",
}

#: LM3-M1 (LMM-A3) -- the lunch chip dropped on Earlier or Later.
LUNCH_EDGE_TEXT = "Lunch stays inside the day — drop it on a Time Block"

#: Said when a refusal arrives with a reason nothing here words. Better than
#: showing the user the reason's internal name, and loud enough to be noticed.
UNKNOWN_REFUSAL = "That Action Item cannot go there"


#: How often the Tk thread looks for the calendar export worker's result.
#: Short enough that the status line does not feel stuck, long enough that a
#: slow export is not a hundred idle callbacks a second.
#: Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
EXPORT_POLL_INTERVAL_MS = 100


def repair_status(repair):
    """PD-M14.7 -- the status line for a ``SlotRepair``, or ``None``.

    ``(text, kind)``. One wording for the load and for a settings save, which
    both run the repair and both have to say what it did.
    """
    if repair is None:
        return None
    if repair.refused:
        return (
            f"{repair.mismatched} block(s) here are not at the time they were"
            " planned at, and moving them back would not fit — drag them where"
            " you want them",
            "warning",
        )
    stuck = getattr(repair, "misaligned", 0)
    if stuck:
        put = f"put {len(repair.moved)} back; " if repair.moved else ""
        return (
            f"{put}{stuck} block(s) here were planned at a time no box starts at"
            " under this Day Start — drag them where you want them",
            "warning",
        )
    if repair.moved:
        count = len(repair.moved)
        noun = "block back on the time it was" if count == 1 else (
            "blocks back on the times they were"
        )
        return (f"Put {count} {noun} planned at", "muted")
    return None


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


class PlanScreen(PlanWeekViewMixin, PlanCommitmentEditsMixin, PlanCommitmentsMixin, ctk.CTkFrame):
    """Screen for planning time blocks."""

    def __init__(self, parent, db_manager: 'DatabaseManager', app: 'GetMoreDoneApp'):
        super().__init__(parent)
        self.db_manager = db_manager
        self.app = app

        self.settings = getattr(app, "settings", None)
        self.bounds = DayBounds.from_settings(self.settings) if self.settings else DayBounds()

        self.selected_date = date.today().strftime("%Y-%m-%d")

        # CIP-M3 -- this date's calendar commitments, read from the cache by
        # ``load_commitments`` on every redraw. Empty until then, so a gesture
        # before the first draw is checked against no meetings rather than
        # raising; the database writers read their own copy regardless (D2).
        self._commitments: list = []
        self._commitment_fetch = None
        self._committed: frozenset = frozenset()
        # Pending ``after`` ids for the read's poll, the automatic read and the
        # wait on another screen's read; ``destroy`` cancels whichever is set.
        self._refresh_poll_id = None
        self._auto_refresh_id = None
        self._claim_watch_id = None
        # CIP-M4 -- a meeting change in flight, and its poll.
        self._edit_poll_id = None
        self._edit_running = False
        self._edit_result = None
        self._drag_commitment = None
        # CIP-M6 -- the week view (plan_week_view.py), and each date's read
        # record while it is up, for the automatic read (W6).
        self._week_mode = False
        self._week_fetches: list = []
        self._week_summaries: list = []
        self._week_error: Optional[str] = None

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
        # PD-M13 -- set when this gesture went ahead on a day outside the
        # working week without asking, and read by the status line the
        # gesture writes, so the fact is not overwritten by its own success.
        self._non_work_day = False

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
        #: PF-M9 -- the outline's colour is restored too. Clearing only the
        #: width left the last-hovered Time Block tinted with the hover colour
        #: for the rest of the session: reported as "something outlines a Time
        #: Block and keeps it outlined as if the movement wasn't saved".
        self._drag_hover_colour = None
        self._block_menu: Optional[tk.Menu] = None
        #: The pending autoscroll tick (PD-M11.5), or ``None`` when the day is
        #: not scrolling itself. One at a time: the tick reschedules itself, so
        #: a second one would double the speed for the rest of the drag.
        self._autoscroll_job: Optional[str] = None

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
        self._last_repair = None
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
        # D10 -- a screen rebuilt while another one's calendar read is running
        # comes up with Refresh disabled, and re-enables when that read ends.
        self.sync_refresh_button()

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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m5
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m5
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
        """The screen's controls, in two rows.

        Purpose: PF-M4 -- the walk asked for the four buttons that add things
                 to the day on their own line, so the date and the two buttons
                 that act on the whole day are not crowded by them.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m4
        Tests:   tests/test_plan_screen_pf_header.py::test_pfm41_the_header_is_two_rows

        PF-M5 -- every button sits in a weighted, uniform column, so widening
        the window widens them equally instead of leaving 90px buttons beside
        panes that moved. The title and the date picker keep their own widths;
        what is left over is shared.
        """
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 0))
        header.grid_columnconfigure(0, weight=1)
        #: The header, named for the tests that measure it. ``btn_*.master`` is
        #: a row inside it now, and a test that measured that row would be
        #: measuring a quarter of what it means to measure.
        self.header = header

        # -- row 1: the date, Clear Day, AutoLoad --------------------------
        day_row = ctk.CTkFrame(header, fg_color="transparent")
        day_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        day_row.grid_columnconfigure(3, weight=1, uniform="day_row")
        day_row.grid_columnconfigure(4, weight=1, uniform="day_row")

        ctk.CTkLabel(
            day_row,
            text="Plan - Time Blocks",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 16), pady=4)

        ctk.CTkLabel(day_row, text="Date:").grid(
            row=0, column=1, sticky="w", padx=(0, 4)
        )
        self.date_picker = DatePickerButton(
            day_row,
            initial_date=self.selected_date,
            on_date_changed=self.on_date_changed,
            settings=self.settings,
            fg_color="transparent",
        )
        self.date_picker.grid(row=0, column=2, sticky="w", padx=(0, 12))

        # The reverse of the button beside it, styled as what it is. Danger
        # rather than primary: AutoLoad is this screen's one primary action,
        # and a destructive button that looks like the main one is a misclick
        # waiting to happen.
        self.btn_clear_day = ctk.CTkButton(
            day_row,
            text="Clear Day",
            width=100,
            command=self.clear_day,
            **button_style("danger"),
        )
        self.btn_clear_day.grid(row=0, column=3, sticky="ew", padx=(0, 8), pady=4)

        # The one button on this screen that acts on the whole day, so the one
        # that carries the primary colour. Nothing else here is primary, which
        # is the condition the theme rule puts on using it at all.
        self.btn_autoload = ctk.CTkButton(
            day_row,
            text="AutoLoad",
            width=100,
            command=self.autoload_day,
            **button_style("primary"),
        )
        self.btn_autoload.grid(row=0, column=4, sticky="ew", pady=4)

        # -- row 2: the five that add, read or open something --------------
        tools_row = ctk.CTkFrame(header, fg_color="transparent")
        tools_row.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 10))
        for column in range(5):
            tools_row.grid_columnconfigure(column, weight=1, uniform="tools_row")

        self.btn_add_buffer = ctk.CTkButton(
            tools_row,
            text="+ Buffer",
            width=90,
            command=lambda: self.add_padding_block(BlockType.BUFFER),
            **button_style("secondary"),
        )
        self.btn_add_buffer.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.btn_add_break = ctk.CTkButton(
            tools_row,
            text="+ Break",
            width=90,
            command=lambda: self.add_padding_block(BlockType.BREAK),
            **button_style("secondary"),
        )
        self.btn_add_break.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        # CE-M4.1 -- secondary, not primary: AutoLoad is this screen's one
        # primary action and the theme rule allows exactly one.
        # Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m41
        # Tests: tests/test_plan_screen_calendar_export.py::test_cem441_the_header_holds_the_export_button_wired_to_the_export
        self.btn_export_calendar = ctk.CTkButton(
            tools_row,
            text="⤴ Google Calendar",
            width=150,
            command=self.export_day_to_calendar,
            **button_style("secondary"),
        )
        self.btn_export_calendar.grid(row=0, column=2, sticky="ew", padx=(0, 8))

        # CIP-M5.2 -- reads this date's meetings from Google Calendar into the
        # cache the grid draws from. Secondary, beside the export it mirrors.
        # Spec:  docs/spec_2026-11-08_calendar_into_the_plan.md#8-m5--the-plan-screen-phase-1-m6--the-week-phase-2-m7--docs
        # Tests: tests/test_plan_screen_commitments.py::test_cipm52_refresh_disables_first
        self.btn_refresh_calendar = ctk.CTkButton(
            tools_row,
            text="↻ Calendar",
            width=100,
            command=self.refresh_calendar,
            **button_style("secondary"),
        )
        self.btn_refresh_calendar.grid(row=0, column=3, sticky="ew", padx=(0, 8))

        self.btn_settings = ctk.CTkButton(
            tools_row,
            text="⚙ Day Settings",
            width=130,
            command=self.open_settings,
            **button_style("secondary"),
        )
        self.btn_settings.grid(row=0, column=4, sticky="ew", padx=(0, 8))

        # CE-M4.1 -- the status line is NOT in the header.
        # Spec:  docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m41
        # Tests: tests/test_plan_screen_calendar_export.py::test_cem441b_the_header_fits_the_window_it_opens_in
        #
        # Every other widget in this header is packed with a fixed width, and
        # this label was packed last with no ``expand``, so Tk gave it
        # whatever the cavity had left -- which the export button's 168px took
        # to below zero: the header asked for 1203px inside a 1200px window
        # (1180 after the header's own padx), and a label squeezed to nothing
        # is never mapped. The one channel this screen reports anything
        # through would have gone silent on a default-sized window, for the
        # feature whose strings are the longest it produces. Its own row
        # cannot be squeezed by a seventh button.
        self.status_label = ctk.CTkLabel(self, text="", anchor="w")
        self.status_label.grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(2, 8)
        )

    def create_items_pane(self):
        # SEP-M5 -- named, not inherited: an unnamed CTkFrame's surface
        # alternates with nesting depth, and at app.py's depth this pane's
        # scroll frame came out the item row's own colour. Why:
        # docs/unused-docs/implementation_plan_2026-11-12_surface_separation.md
        # The theme's [light, dark] pair, not semantic_colors()'s resolved
        # string, so the pane repaints when the OS switches mode.
        palette = semantic_colors()
        pane_fill = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        frame = ctk.CTkFrame(self, fg_color=pane_fill)
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
            text_color=palette["muted_text"],
            font=ctk.CTkFont(size=11),
        )
        self.items_hint.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        self.items_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=pane_fill
        )
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m2
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m2
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m2
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
        # SEP-M5 -- named, not inherited; see ``create_items_pane``.
        palette = semantic_colors()
        pane_fill = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        frame = ctk.CTkFrame(self, fg_color=pane_fill)
        frame.grid(
            row=1, column=2, sticky="nsew",
            padx=(0, PLAN_PANE_EDGE_PAD_PX), pady=10,
        )
        frame.grid_columnconfigure(0, weight=1)
        # Row 4 is the scrolling grid. The two ends of the day (PD-M11.2) sit
        # in rows 3 and 5 and keep their own height, so the grid gets the rest.
        frame.grid_rowconfigure(4, weight=1)

        self.day_heading = ctk.CTkLabel(
            frame, text="Day Plan", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.day_heading.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        # CIP-M6 / W1 -- Day or Week, beside the heading it renames.
        self.create_view_toggle(frame)

        self.day_summary = ctk.CTkLabel(
            frame,
            text="",
            anchor="w",
            text_color=palette["muted_text"],
            font=ctk.CTkFont(size=11),
        )
        self.day_summary.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        # CIP-M5.4 / CIP-M3.8 -- how old the calendar's answer is, and the
        # meetings no box can show: all-day ones, and any part of a meeting
        # outside the boxes a date can have. Above the grid, never scrolled off.
        self.commitment_strip = ctk.CTkFrame(frame, fg_color="transparent")
        self.commitment_strip.grid(row=2, column=0, padx=10, pady=(0, 4), sticky="ew")
        self.commitment_strip.grid_columnconfigure(0, weight=1)

        # PD-M11.2 -- the two ends of the day are drawn outside the scrolling
        # grid, one above it and one below it, so neither can be scrolled off
        # the screen. Inside the grid they were part of its content: on a day
        # of eighteen boxes the Later box sat several hundred pixels below the
        # bottom of the pane, and with no way to scroll while dragging there
        # was no gesture that reached it at all.
        self.earlier_holder = ctk.CTkFrame(frame, fg_color="transparent")
        self.earlier_holder.grid(row=3, column=0, sticky="ew", padx=5)
        self.earlier_holder.grid_columnconfigure(0, weight=1)

        # The drop target for an item drag, and the container a block drag is
        # reordered within.
        self.blocks_scroll = ctk.CTkScrollableFrame(
            frame, fg_color=pane_fill
        )
        self.blocks_scroll.grid(row=4, column=0, sticky="nsew", padx=5, pady=4)
        self.blocks_scroll.grid_columnconfigure(0, weight=1)

        self.later_holder = ctk.CTkFrame(frame, fg_color="transparent")
        self.later_holder.grid(row=5, column=0, sticky="ew", padx=5, pady=(0, 5))
        self.later_holder.grid_columnconfigure(0, weight=1)

        self.day_drop_frame = frame

    # ================= loading ==============================================

    def refresh(self):
        self.load_items()
        self.load_blocks()

    def _flush_redraw(self):
        """Put a rebuilt pane on screen now, rather than at the next event.

        Purpose: PD-M10 -- a rebuilt pane stayed off the screen until the
                 pointer moved over the window. Moving a block, resizing one
                 or deleting one wrote the day correctly and looked like a
                 gesture that had done nothing.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m10
        Tests:   tests/test_plan_screen.py::test_pdm101_rebuilding_the_day_pane_flushes_the_redraw

        ``update_idletasks`` and not ``update``. Idle tasks are Tk's geometry
        and its own redisplay bookkeeping, which is all this can afford to
        ask for. ``update`` services the event queue and turns the platform's
        run loop, and that was measured here: with it in this path, six tests
        of this screen took four minutes and 120% of a CPU, because every
        pane rebuild pumped the whole loop. It is also the hang the
        ``after_idle`` in ``on_drag_release`` exists to avoid -- a queued
        click dispatched inside a rebuild lands in the widget the rebuild is
        destroying.

        What PD-M10 had wrong was not this call. It was the rebuild around it
        (PD-M11.1): the scroll frame left the grid for the duration, which
        unmapped the canvas the rows are drawn in, and the width and
        scrollregion it came back with are restored by ``<Configure>``
        handlers that an idle flush does not run. The pane was put back blank
        and filled itself in on the next event. Rebuilt in place there is
        nothing to restore.
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
        dialog = PlanSettingsDialog(
            self, self.settings, on_saved=self.on_settings_saved, db_manager=self.db_manager
        )
        dialog.wait_window()

    def on_settings_saved(self, bounds: DayBounds, renumbered: int = 0):
        """The day's shape changed; redraw it and say what that did.

        Purpose: TG-M6.4 as PD-M14.4 left it -- the dialog has already
                 renumbered every block so each keeps its clock time
                 (``DatabaseManager.shift_day_start``) and passes
                 ``renumbered``, the count. This callback writes nothing
                 itself; the redraw runs PD-M14.7's repair on the open date,
                 and what that did is said here, a refusal first.
        Spec:    docs/unused-docs/implementation_plan_2026-11-13_day_start_keeps_clock_times.md
        Tests:   tests/test_plan_screen.py::test_tgm64_the_settings_callback_writes_no_blocks
                 tests/test_plan_screen.py::test_pdm144_the_dialog_keeps_planned_work_on_its_clock

        The screen draws from the box. A block that no longer fits the new
        hours is surfaced as outside the day and counted here.
        """
        self.bounds = bounds
        self._last_repair = None
        self.refresh()

        if self._week_mode:
            # The week runs no repair and keeps no day grid; it counts what
            # it drew. Each date is repaired when it is opened as a day.
            if self._week_error:
                self.set_status(
                    f"Day settings saved — the week could not be read: {self._week_error}",
                    "error",
                )
                return
            outside = sum(summary.outside for summary in self._week_summaries)
            if outside:
                noun = "block" if outside == 1 else "blocks"
                self.set_status(
                    f"Day settings saved — {outside} {noun} this week no longer fit"
                    " the day; open the day to place them",
                    "warning",
                )
            else:
                said = ["Day settings saved"]
                if renumbered:
                    noun = "block kept its time" if renumbered == 1 else "blocks kept their times"
                    said.append(f"{renumbered} {noun}")
                self.set_status(" — ".join(said), "success")
            return

        # PD-M14.7 -- the redraw may have repaired the open date, or refused
        # to. Said here, or "saved" below would cover it.
        repair_said = repair_status(self._last_repair)
        if repair_said is not None and repair_said[1] == "warning":
            self.set_status(f"Day settings saved — {repair_said[0]}", "warning")
            return

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
        said = ["Day settings saved"]
        if renumbered:
            noun = "block kept its time" if renumbered == 1 else "blocks kept their times"
            said.append(f"{renumbered} {noun}")
        if repair_said is not None:
            said.append(repair_said[0])
        self.set_status(" — ".join(said), "success")

    def _segment_color_resolver(self):
        """A function giving each item its Vision Planning Category colour.

        The same lookup and caches the five list screens use, built fresh per
        refresh so a colour changed in Vision Planning shows on the next one.
        With no ``vps_manager`` (a test's stand-in app) every item gets none.
        """
        vps = getattr(self.app, "vps_manager", None)
        if vps is None:
            return lambda item: None
        by_id = vps.get_segment_colors_by_id()
        by_name = vps.get_segment_color_map()
        caches = ({}, {}, {})
        return lambda item: resolve_segment_color_for_item(
            item, by_id, by_name, self.db_manager, *caches
        )

    def load_items(self):
        """Draw the items that start on the selected date.

        Rebuilt in place (PD-M11.1): see ``load_blocks`` for why the scroll
        frame is no longer taken out of the grid first.
        """
        try:
            for widget in self.items_scroll.winfo_children():
                widget.destroy()

            self._items = self.db_manager.get_items_for_start_date(self.selected_date)
            blocked = self.db_manager.get_blocked_item_ids(self.selected_date)
            segment_color_for = self._segment_color_resolver()

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
                    wraplength=self.items_col_width() - ITEMS_TEXT_INSET_PX,
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
                        # PBG-M2 -- the badge's colour is the user's priority
                        # scheme, which lives here as it does on the five
                        # list screens. ``None`` resolves to the defaults.
                        settings=self.settings,
                        segment_color=segment_color_for(item),
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
            self._flush_redraw()

    def load_blocks(self):
        """Draw the day as its grid of half hours.

        Purpose: TG-M7 -- every box from Day Start to Day End, filled or not.
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m7
        Tests:   tests/test_plan_screen.py::test_tgm71_every_slot_is_drawn
                 tests/test_plan_screen.py::test_pdm111_a_rebuild_leaves_the_day_pane_in_the_grid

        PD-M11.1 -- rebuilt in place. This used to take the scroll frame out
        of the grid first and put it back in a ``finally``, to batch the
        redraw while the rows were destroyed and rebuilt. A
        ``CTkScrollableFrame`` is a frame inside a canvas inside a frame, and
        it is the outer frame that leaves the grid: the canvas is unmapped
        with it, and on the way back the width of the window the rows are
        drawn in, and the scrollregion, are both restored by ``<Configure>``
        handlers that only run when the event queue is next serviced. A flush
        of idle tasks does not service it, so the pane came back blank and
        filled in on the next mouse movement. Destroying and rebuilding the
        rows where they are costs one more layout pass and nothing else: Tk
        does its geometry at idle, so no intermediate state is drawn unless
        something asks for it in the middle, and nothing here does.
        """
        if self._week_mode:
            # CIP-M6 -- every redraw (a date change, a read, an edit) draws
            # whichever view is up.
            return self.load_week()
        try:
            for widget in self.blocks_scroll.winfo_children():
                widget.destroy()
            # Unconditional: emptied only inside the "there are blocks
            # outside the day" branch, the last group drawn would stay on
            # screen after the day that had one was left.
            for widget in self.outside_frame.winfo_children():
                widget.destroy()
            # PD-M11.2 -- the two ends of the day are not in the scroll frame
            # any more, so clearing its children does not clear them.
            for holder in (self.earlier_holder, self.later_holder):
                for widget in holder.winfo_children():
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
            repair = None
            if self._day_shape_is_the_users():
                # PD-M14.7 first, so adoption sees the boxes where the recorded
                # times put them. Same gate, for the same reason: against a
                # guessed Day Start the recorded time names the wrong box.
                repair = self.db_manager.repair_slots_from_times(
                    self.selected_date, self.bounds
                )
                adopted = self.db_manager.adopt_legacy_day(
                    self.selected_date, self.bounds
                )
                if repair.unreadable:
                    logger.warning(
                        "PD-M14.7: %d block(s) on %s have a box but no readable"
                        " start time; left where they are",
                        repair.unreadable,
                        self.selected_date,
                    )
            # Kept so on_settings_saved, which redraws through here, can say
            # what the repair did rather than cover it with "saved".
            self._last_repair = repair

            blocks = self.db_manager.get_time_blocks(self.selected_date)
            # CIP-M5.1 -- from the cache only; nothing here reaches Google.
            self.load_commitments()
            self._grid = build_day_grid(blocks, self.bounds, committed=self._committed)
            drawn_commitments = commitments_by_slot(self._commitments, self.bounds)
            self.draw_commitment_strip()
            items_by_id = self._items_by_id(blocks)
            segment_color_for = self._segment_color_resolver()

            self.update_day_summary(blocks)

            # Adoption is irreversible and was previously silent: the ids it
            # returns were thrown away. Named with the Day Start it used, so
            # the assumption it baked in is visible and checkable rather than
            # something to infer from blocks that moved.
            repair_said = repair_status(repair)
            warned = repair_said is not None and repair_said[1] == "warning"
            if adopted:
                # Adoption is said once and never again, so a repair warning
                # (which repeats on every load) is added to it, not put first.
                placed = (
                    f"Placed {len(adopted)} block(s) from an earlier version"
                    f" on the grid, using a day start of {self.bounds.day_start}"
                )
                if warned:
                    self.set_status(f"{placed} — {repair_said[0]}", "warning")
                else:
                    self.set_status(placed, "muted")
            elif repair_said is not None:
                self.set_status(*repair_said)
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
            #
            # PD-M11.2 — in its own holder outside the scrolling grid, which
            # is why it is row 0 of that holder rather than a row of the grid.
            self._virtual_frames.append((
                build_virtual_slot_row(
                    self.earlier_holder,
                    0,
                    label=PD_EARLIER_TEXT,
                    hint=PD_EARLIER_HINT,
                    chip_height=self.box_height(),
                ),
                DAY_EXTEND_EARLIER,
            ))

            for entry in self._grid.slots:
                rendered = build_slot_row(
                    self.blocks_scroll,
                    entry,
                    items_by_id,
                    row,
                    chip_height=self.box_height(),
                    title_width=self.box_title_width(),
                    segment_color_for=segment_color_for,
                    settings=self.settings,
                    commitments=drawn_commitments.get(entry.slot.index, ()),
                )
                self._slot_frames.append((rendered.frame, entry.slot.index))
                for commitment, widget in rendered.commitment_widgets:
                    self.bind_commitment_handlers(widget, commitment)
                for block, widget in rendered.block_widgets:
                    self.bind_block_handlers(widget, block)
                    self._block_widgets.append((widget, block.id))
                # PF-M8 -- the settings' lunch, before this date has one of its
                # own: draggable, so a day can be given its own lunch hour
                # without going to Day Settings and moving it on every date.
                if rendered.lunch_chip is not None:
                    self.bind_lunch_handlers(rendered.lunch_chip)
                row += 1

            self._virtual_frames.append((
                build_virtual_slot_row(
                    self.later_holder,
                    0,
                    label=PD_LATER_TEXT,
                    hint=PD_LATER_HINT,
                    chip_height=self.box_height(),
                ),
                DAY_EXTEND_LATER,
            ))

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
                    segment_color_for=segment_color_for,
                    settings=self.settings,
                ):
                    self.bind_block_handlers(widget, block)
                    self._block_widgets.append((widget, block.id))
            else:
                self.outside_frame.grid_remove()
        finally:
            self._flush_redraw()
        # CIP-M5.5 -- after the paint, never before it (M5.1).
        self.maybe_auto_refresh()

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
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m12
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
        # D12 -- planned work a meeting has since landed on. It stays where
        # it is; this is how the user hears about it on every redraw.
        overlapping = len(self._grid.overlapping)
        if overlapping:
            noun = "block overlaps" if overlapping == 1 else "blocks overlap"
            parts.append(f"{overlapping} {noun} a meeting")

        self.day_summary.configure(text="  ·  ".join(parts))

    def set_status(self, text: str, kind: str = "muted"):
        self.status_label.configure(text=text, text_color=status_text_color(kind))

    # ================= creating blocks ======================================

    def add_padding_block(self, block_type: str, slot_index: Optional[int] = None):
        """TB-M10/TG-M9 — put a buffer or a break on a box.

        With no ``slot_index`` it goes on the first empty box, or, when none
        is empty, the first box that will hold it (PBB-M1). That is what the
        toolbar buttons want: they are a click, not a drop, so there is no box
        under a pointer to read.
        """
        if self.refused_in_week():
            return None
        if not self._require_block_day():
            return

        minutes = default_minutes_for_block_type(block_type, self.settings)
        if slot_index is None:
            # PBB-M1: a click has no pointer to say "beside this task", so it
            # takes an empty half hour, as AutoLoad does; only a day with none
            # left falls back to the first box with room. A drag still puts
            # it exactly where it is dropped.
            slot_index = self.first_clear_slot(minutes)
            if slot_index is None:
                slot_index = self.first_free_slot(minutes)
            if slot_index is None:
                self.set_status(
                    f"No Time Block free for a {minutes}m {block_type}", "warning"
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
            f"Added a {minutes}m {block_type} at {block.start_time}"
            + self._take_non_work_note(),
            "success",
        )

    def block_item(
        self, item: ActionItem, slot_index: Optional[int] = None, day: Optional[str] = None
    ):
        """TG-M9 — make a block for this item on the box it was dropped on.

        Purpose: the half hour the user chose, not the end of the day.
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m9
        Tests:   tests/test_plan_screen.py::test_tgm91_a_drop_lands_on_the_slot_under_the_pointer

        With no ``slot_index`` it takes the first box that will hold it.
        No UI path passes that today -- every drop names the box under the
        pointer -- so it is the API's answer for a caller with no pointer to
        read, and the toolbar's ``add_padding_block`` is the one that needs it.
        An earlier version of this docstring claimed an item-row double-click
        used it; there has never been such a binding (`BACKLOG.md`).
        """
        # CIP-M6.5 -- a drop on the week names the box's date; every other
        # caller means the day on screen.
        day = day or self.selected_date
        # PD-M13 -- a drop never asks; see _require_block_day.
        if not self._require_block_day(ask=False, day=day):
            return

        # PF-M2 -- one block per item per day, said out loud. Nothing refused
        # a second block before this: ``add_block_at`` refuses a box with four
        # blocks in it, not an item that is already on the day, so dropping an
        # item that is already blocked wrote a second block on any free box
        # and was refused as a full box on its own.
        blocked = self._already_blocked_text(item, day)
        if blocked is not None:
            # The note is one-shot and belongs to a gesture that wrote
            # something; this gesture wrote nothing, so it is cleared rather
            # than left to surface on the next status line.
            self._non_work_day = False
            self.set_status(blocked, "warning")
            return

        minutes = duration_for_item(item, self.bounds.default_block_minutes)
        if slot_index is None:
            slot_index = self.first_free_slot(minutes)
            if slot_index is None:
                self.set_status(
                    f"No Time Block free for {minutes}m of {item.title}", "warning"
                )
                return

        # PF-M3 -- a follow-on task lands with the work it follows.
        after = self._linked_block_in_slot(item, slot_index, day)
        # ... and when its partner is in another box, a continuation goes to
        # the top of the one it was dropped on rather than under everything
        # already there.
        top = after is None and self._continues_a_block(item, day)

        block = TimeBlock(
            block_date=day,
            start_time="",
            end_time="",
            planned_minutes=minutes,
            item_id=item.id,
            label=item.title,
            block_type=BlockType.ITEM,
        )
        try:
            self.db_manager.add_block_at(
                block,
                slot_index,
                self.bounds,
                # PF-M6 -- the drawn day, not the template's hours. A box that
                # exists because the day was extended earlier or later is on
                # screen and accepts a drop; reading only the template refused
                # it as "outside the day" while the user was looking at it.
                day_span=self._placement_for(day)[0],
                after_block_id=after.id if after is not None else None,
                at_top=top,
            )
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        self.refresh()

        boxes = slots_for_minutes(minutes)
        spare = boxes * SLOT_MINUTES - minutes
        text = f"Blocked {minutes}m for {item.title}"
        if self._week_mode:
            text += f" on {date.fromisoformat(day).strftime('%a %d')}"
        text += f" at {block.start_time}"
        if self._week_mode and not self._week_day_read(day):
            text += " — calendar not read for that day"
        text += self._take_non_work_note(day)
        if spare:
            # Said out loud, because the box the task does not fill is still
            # spent: the next task starts at the following box, not at the
            # minute this one ends.
            text += f" — {boxes} boxes, {spare}m spare"
        self.set_status(text, "success")

    def _blocked_today(self, item_id: str, day: Optional[str] = None) -> Optional[TimeBlock]:
        """The block this item already has on the date on screen, if any.

        Purpose: PF-M2 -- one block per item per day, so a second drag says
                 where the work already is instead of writing beside it.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m2
        Tests:   tests/test_plan_screen.py::test_pfm21_a_second_drop_of_the_same_item_writes_nothing

        Item blocks only. A break or a buffer carries no ``item_id``, and the
        two of them repeating across a day is what they are for.
        """
        for block in self.db_manager.get_time_blocks(day or self.selected_date):
            if block.block_type != BlockType.ITEM:
                continue
            if block.item_id == item_id:
                return block
        return None

    def _already_blocked_text(self, item: ActionItem, day: Optional[str] = None) -> Optional[str]:
        """The sentence a drop of an item already on the day leaves, if it is.

        Purpose: PF-M2 -- one wording for three call sites, so the box drop,
                 the two ends of the day and the pre-check below cannot drift.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m2
        Tests:   tests/test_plan_screen.py::test_pfm22_the_refusal_says_where_the_block_is
        """
        sitting = self._blocked_today(item.id, day)
        if sitting is None:
            return None
        return (
            f"{item.title} is already in a Time Block at {sitting.start_time}"
            " — drag that Time Block to move it"
        )

    def _drop_refusal(
        self, item: ActionItem, slot_index: int, day: Optional[str] = None
    ) -> Optional[str]:
        """Why a drop on this box would write nothing, or ``None`` if it would.

        Purpose: PF-M1 -- the question is about a day, but it is asked about a
                 *gesture*, and a confirmation that leads straight to a refusal
                 spends the day's one answer on nothing: the yes is remembered
                 in ``_work_anyway`` whether or not the write happened. So the
                 two refusals the grid already knows about are read first.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m1
        Tests:   tests/test_plan_screen.py::test_pfm17_a_drop_that_cannot_write_asks_nothing

        Read, not enforced: ``block_item`` and ``extend_day_for`` make both
        checks again, because they are the write paths and a caller that is not
        this handler must get the same answers.
        """
        day = day or self.selected_date
        blocked = self._already_blocked_text(item, day)
        if blocked is not None:
            return blocked

        minutes = duration_for_item(item, self.bounds.default_block_minutes)
        span, committed = self._placement_for(day)
        reason = can_place(
            self.db_manager.get_time_blocks(day),
            self.bounds,
            slot_index,
            slots_for_minutes(minutes),
            day_span=span,
            committed=committed,
        )
        return refusal_text(reason) if reason else None

    def _allow_this_day(self, day: Optional[str] = None) -> bool:
        """Ask about a day outside the working week, and never lose the drop.

        Purpose: PF-M1 -- ``_require_block_day`` catches the ``TclError`` the
                 platform raises for a dialog it will not show. This catches
                 everything else, because the failure this path has already
                 produced twice is a gesture that wrote nothing and said
                 nothing: a question that raises is logged, the day is allowed,
                 and the status line names it.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m1
        Tests:   tests/test_plan_screen.py::test_pfm15_a_question_that_raises_still_schedules
        """
        try:
            return self._require_block_day(day=day)
        except Exception:  # noqa: BLE001 - a dialog may not eat the drop
            logger.exception("the non-work-day question raised on a drop")
            self._work_anyway.add(day or self.selected_date)
            self._non_work_day = True
            return True

    def _continues_a_block(self, item: ActionItem, day: Optional[str] = None) -> bool:
        """Is this item a continuation of work already blocked on this day?

        Purpose: PF-M3 -- "continuation from previous block" goes to the top of
                 the box it is dropped on, not under whatever is already there.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m3
        Tests:   tests/test_plan_screen.py::test_pfm35_a_continuation_lands_on_top

        A child item whose parent is on the day. Not a Weekly Tactic: a tactic
        is a container for unrelated work, and ordering its steps as a chain
        was the wrong reading of "linked" (2026-11-10).
        """
        parent = getattr(item, "parent_id", None)
        if not parent:
            return False
        for block in self.db_manager.get_time_blocks(day or self.selected_date):
            if block.block_type == BlockType.ITEM and block.item_id == parent:
                return True
        return False

    def _linked_block_in_slot(
        self, item: ActionItem, slot_index: int, day: Optional[str] = None
    ) -> Optional[TimeBlock]:
        """The block in this box that ``item`` should follow, if there is one.

        Purpose: PF-M3 -- a task dragged next to the work it belongs to takes
                 the place after it rather than the end of the box.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m3
        Tests:   tests/test_plan_screen.py::test_pfm31_a_child_lands_after_its_parent

        **Linked** is the parent/child pair: either item is the other's
        ``parent_id``. Nothing else is treated as a link — ``item_links``
        points at notes, files and URLs, and a shared ``weekly_tactic_id`` is a
        container for steps that need not follow one another (2026-11-10: the
        weekly tactic rule was removed for exactly that reason).

        The first match in draw order wins, which is what "the nearest" means
        here: the box is ordered by position and the walk follows it.
        """
        mine = {"parent": getattr(item, "parent_id", None)}
        for block in self.db_manager.get_time_blocks(day or self.selected_date):
            if block.slot_index != slot_index:
                continue
            if block.block_type != BlockType.ITEM or not block.item_id:
                continue
            if block.item_id == item.id:
                continue
            other = self.db_manager.get_action_item(block.item_id)
            if other is None:
                continue
            if mine["parent"] and getattr(other, "id", None) == mine["parent"]:
                return block
            if getattr(other, "parent_id", None) == item.id:
                return block
        return None

    # ================= exporting the day ====================================

    def calendar_client(self):
        """The Google Calendar client this screen exports with.

        Purpose: CE-M4.5 -- the seam that keeps every UI test off the network.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m45
        Tests:   tests/test_plan_screen_calendar_export.py::test_cem451_the_screen_uses_its_injected_client_factory

        A method rather than a client held on the screen: constructing
        ``GoogleCalendarManager`` authenticates, so one built at screen
        construction would run an OAuth flow for every user who never exports
        anything. Tests replace ``self.calendar_client_factory``.
        """
        factory = getattr(self, "calendar_client_factory", None)
        if factory is not None:
            return factory()

        from ..google_calendar import GoogleCalendarManager

        # ``allow_interactive=False``, because this client is built on the
        # export's worker thread. Signing in opens a browser, waits on a local
        # HTTP server with no timeout, and falls back to ``input()`` on a
        # console a double-clicked app does not have -- all three wait
        # forever. The screen's token check refuses when there is no token
        # file at all, but a token that is present and cannot be refreshed
        # (revoked access, a changed password, a corrupt pickle) gets past it,
        # and that is the case this flag covers: it raises
        # ``AuthenticationRequired``, which ``work()`` reports.
        return GoogleCalendarManager(allow_interactive=False)

    def export_day_to_calendar(self):
        """Push this day's blocks to Google Calendar, on a worker thread.

        Purpose: CE-M4.1/4.2/4.3 -- the button's whole behaviour.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m41
        Tests:   tests/test_plan_screen_calendar_export.py::test_cem411_the_button_disables_before_the_work_starts

        Order matters here. The button is disabled *before* anything slow or
        fallible runs, and every refusal below re-enables it on the way out --
        a disabled button and no explanation is the one outcome the user
        cannot do anything about.
        """
        if self.refused_in_week():
            return
        if getattr(self, "_export_running", False):
            return

        claimed = None
        self._export_running = True
        self._export_thread = None
        self._export_result = None
        self.btn_export_calendar.configure(state="disabled")

        try:
            from ..google_calendar import AuthenticationRequired, GoogleCalendarManager

            if not GoogleCalendarManager.is_available():
                self._finish_export_refusal(
                    "Google Calendar libraries are not installed — run: "
                    "pip install -r requirements.txt"
                )
                return

            if not GoogleCalendarManager.has_credentials():
                from .calendar_dialog import missing_credentials_message

                self._finish_export_refusal(missing_credentials_message())
                return

            # No "nothing to export" refusal here. A day whose blocks have
            # all been deleted is exactly the day whose events have to come
            # off the calendar, and the sweep inside the export is the only
            # code that removes them -- ``delete_event`` has no other caller.
            # Refusing before it ran left those events on the user's calendar
            # with no way to take them off, under a status line reading
            # "nothing to export" (P25, P2). The exporter reports an empty day
            # as such on its own, deletions included.

            # The third refusal, and the reason this one is not just
            # "credentials.json is there": ``has_credentials`` says nothing
            # about ``token.pickle``, and the real client's ``__init__``
            # authenticates -- ``flow.run_local_server`` with no timeout,
            # waiting on a browser consent, on the export's worker thread.
            # A user who has dropped credentials.json in place but never
            # connected, and then closes the consent tab, left this screen
            # disabled and reading "Exporting..." with no code path that
            # restores either (P1, P15). ``exists``, not ``valid``: an expired
            # token that can be refreshed reports ``valid`` False and needs no
            # browser, so refusing on it would refuse a working setup.
            if not GoogleCalendarManager.check_token_validity().get("exists"):
                from .calendar_dialog import not_connected_message

                self._finish_export_refusal(not_connected_message())
                return

            # Captured now, on the thread that owns them. The worker opens its own
            # database connection from the path, the way the calendar importer
            # does, because this screen's SQLite connection belongs to the main
            # thread.
            block_date = self.selected_date
            db_path = self.db_manager.db.db_path

            # The fourth refusal, and the only one that is not about this
            # screen: ``_export_running`` is per instance, and navigating away
            # from Plan and back builds a new one. Two screens exporting one
            # day race over the same rows.
            if not _claim_export(db_path, block_date):
                self._finish_export_refusal(
                    f"{block_date} is already being exported — "
                    "wait for that export to finish."
                )
                return
            claimed = (db_path, block_date)

            self.set_status(
                f"Exporting {self.selected_date} to Google Calendar…", "muted"
            )
            calendar_id = self._positive_calendar_id()
            # The day's shape goes with it. ``DayBounds`` is frozen, so the
            # worker cannot be handed a day that changes under it -- and
            # without it the export would time the day from the stored clock
            # columns, which record the bounds in force when each block was
            # placed, not the ones the screen is drawing now.
            bounds = self.bounds

            self._export_result = None

            def work():
                # Nothing in here touches a widget. Tk is not thread-safe, and
                # that includes ``after``: a worker that scheduled its own
                # callback would be calling into the Tcl interpreter from a
                # second thread, which wedges a process that has no mainloop
                # running and is undefined behaviour in one that has. The worker
                # leaves its result in an attribute and the Tk thread collects
                # it (``_poll_export``).
                try:
                    from ..calendar_exporter import export_day

                    outcome = export_day(
                        block_date,
                        client=self.calendar_client(),
                        db_path=db_path,
                        calendar_id=calendar_id,
                        bounds=bounds,
                    )
                    # Inside the try, so the slot is not given back until the
                    # result the poll reads has been recorded.
                    self._export_result = ("outcome", outcome)
                except AuthenticationRequired:
                    # Named before the catch-all, and reported as the refusal
                    # it is: "sign in again", not "export failed: Google
                    # Calendar needs you to sign in again...". The class is
                    # imported above, on the Tk thread, so a worker raising
                    # this cannot meet an unbound name while handling it.
                    from .calendar_dialog import not_connected_message

                    self._export_result = ("error", not_connected_message())
                    return
                except Exception as error:  # noqa: BLE001 - P15: the worker has a
                    # top-level guard, or a failure here is a silent no-op with a
                    # button that never comes back.
                    self._export_result = (
                        "error", f"Google Calendar export failed: {error}"
                    )
                    return
                finally:
                    # On this thread, because this thread is the one holding
                    # the slot: released whether the export succeeded, failed
                    # or raised something nobody expected. A slot leaked here
                    # refuses every later export of that day for the life of
                    # the process, with a message saying to wait for an export
                    # that has already finished (P1).
                    _release_export(db_path, block_date)

            # Drain pending finalizers on the thread that owns Tk, before the
            # worker exists. A tkinter font -- CustomTkinter makes one per widget,
            # and a destroyed screen's fonts become garbage -- calls into Tcl from
            # its ``__del__``, and the collection that runs it happens on whichever
            # thread next allocates. When that thread is the worker, the Tcl call
            # blocks, the export never reports, and the button never comes back.
            # A test run caught exactly that stack:
            #     tkinter/font.py __del__ <- DatabaseManager.__init__ <- work()
            # Collecting here runs those finalizers where they are safe to run.
            gc.collect()

            self._export_thread = threading.Thread(target=work, daemon=True)
            self._export_thread.start()
            self._schedule_export_poll()
        except Exception as error:  # noqa: BLE001 - a refusal, not a crash
            # The whole method, not just the prerequisite checks. Six
            # statements used to sit outside this guard with the button
            # already disabled and ``_export_running`` already True, so a
            # ``RuntimeError: can't start new thread`` -- or anything raised by
            # the attributes captured for the worker -- left the screen
            # disabled under "Exporting..." forever: nothing had scheduled the
            # poll, so nothing would ever re-enable it.
            if claimed is not None:
                # The claim is taken before the thread exists, so a failure
                # between the two -- ``RuntimeError: can't start new thread``,
                # most plausibly -- would leave the slot held by nothing.
                _release_export(*claimed)
            self._finish_export_refusal(f"Could not start the export: {error}")
            return


    def _positive_calendar_id(self) -> str:
        """The configured calendar, or ``primary`` when nothing says otherwise."""
        configured = getattr(self.settings, "plan_export_calendar_id", None)
        configured = (configured or "").strip() if isinstance(configured, str) else ""
        return configured or "primary"

    def _schedule_export_poll(self):
        """Ask the Tk thread to look for the worker's result shortly.

        Scheduled from the thread that owns the widgets, every time, which is
        the whole point: see the comment in ``work`` above.
        """
        try:
            self._export_poll_id = self.after(
                EXPORT_POLL_INTERVAL_MS, self._poll_export
            )
        except Exception:  # noqa: BLE001 - the widget is gone; nothing to tell
            self._export_poll_id = None

    def _poll_export(self):
        """Collect the worker's result, or come back later.

        Purpose: CE-M4.2 -- the hand-off from the worker to the status line.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
        Tests:   tests/test_plan_screen_calendar_export.py::test_cem421_the_status_line_reports_the_real_counts,
                 ::test_cem425_a_result_that_lands_between_the_two_reads_is_not_called_a_failure
        """
        result = self._export_result

        if result is None:
            thread = getattr(self, "_export_thread", None)
            if thread is not None and thread.is_alive():
                self._schedule_export_poll()
                return
            # Read again, and only then give up. The worker sets the result and
            # *then* exits, so a result that lands between the read above and
            # the liveness check above would otherwise be reported as "stopped
            # without reporting a result" over a run that had just succeeded --
            # two cold review passes flagged this ordering (P1: a transient
            # read as terminal).
            result = self._export_result
            if result is None:
                # The worker has a top-level guard, so this is close to
                # unreachable -- and if it is ever reached, a button that never
                # comes back is the worst possible way to find out.
                self._finish_export_refusal(
                    "The Google Calendar export stopped without reporting a result"
                )
                return

        self._export_result = None
        kind, payload = result
        if kind == "outcome":
            self._report_export(payload)
        else:
            self._finish_export_refusal(payload)

    def _report_export(self, outcome):
        """The status line, from the counts rather than from having finished.

        Purpose: CE-M4.2 -- a run that failed says so (P24).
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
        Tests:   tests/test_plan_screen_calendar_export.py::test_cem422_a_failing_export_sets_an_error_status
        """
        self._export_running = False
        if not self._still_on_screen():
            return
        # CIP-M6 -- the week keeps it disabled (plan_week_view._set_day_buttons).
        self.btn_export_calendar.configure(state="disabled" if self._week_mode else "normal")

        line = outcome.summary_line()
        if outcome.failed:
            detail = outcome.errors[0] if outcome.errors else ""
            self.set_status(f"{line}{(' — ' + detail) if detail else ''}", "error")
        elif outcome.exported or outcome.deleted_orphans:
            self.set_status(line, "success")
        else:
            self.set_status(line, "muted")

    def _finish_export_refusal(self, message: str, kind: str = "error"):
        """Give the button back, and say why nothing happened."""
        self._export_running = False
        if not self._still_on_screen():
            return
        # CIP-M6 -- the week keeps it disabled (plan_week_view._set_day_buttons).
        self.btn_export_calendar.configure(state="disabled" if self._week_mode else "normal")
        self.set_status(message, kind)

    def _still_on_screen(self) -> bool:
        """Whether this screen's widgets are still there to be written to.

        Purpose: CE-M4.2 / P15 -- the export reports from a Tk callback that
                 outlives the screen when the user navigates away mid-run.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
        Tests:   tests/test_plan_screen_calendar_export.py::test_cem423_a_screen_that_is_gone_is_not_written_to

        ``app.clear_content`` destroys the screen on every navigation, and Tk
        does not cancel a queued ``after`` when its widget dies. Without this
        the callback configures a dead button and raises inside the Tk
        callback, where nothing reports it. ``timer_window`` guards the same
        class of callback the same way.
        """
        try:
            return bool(self.winfo_exists())
        except Exception:  # noqa: BLE001 - the widget or interpreter is gone
            return False

    def destroy(self):
        """Cancel the pending export poll before the widgets go.

        Purpose: CE-M4.2 / P15 -- the queued callback must not outlive what it
                 writes to.
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md#ce-m42
        Tests:   tests/test_plan_screen_calendar_export.py::test_cem424_destroying_the_screen_cancels_the_poll

        The worker is a daemon thread and is left to finish: whatever it has
        already written to Google is already written, and the ids it records
        go to the database, not to this screen.
        """
        poll_id = getattr(self, "_export_poll_id", None)
        if poll_id is not None:
            try:
                self.after_cancel(poll_id)
            except Exception:  # noqa: BLE001 - already fired, or already gone
                pass
            self._export_poll_id = None
        self.cancel_commitment_callbacks()
        super().destroy()

    def autoload_day(self):
        """PD-M3 — block every item the day still has room for, in list order.

        Purpose: fill the day from the item list in one click, one item after
                 another, at the earliest box that holds each.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m3
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
        if self.refused_in_week():
            return None
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
        said += self._take_non_work_note()
        self.set_status(said, "success" if placed else "warning")

    def clear_day(self):
        """PD-M8 — take every scheduled item back off the day.

        Purpose: the reverse of AutoLoad. One click that empties the day of
                 tasks, so a plan can be thrown away and redone.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m8
        Tests:   tests/test_plan_screen.py::test_pdm8_clear_day_removes_every_item_block
                 tests/test_plan_screen.py::test_pdm8_clear_day_leaves_breaks_and_buffers
                 tests/test_plan_screen.py::test_pdm8_answering_no_removes_nothing
                 tests/test_plan_screen.py::test_pdm8_a_day_with_no_items_says_so_and_asks_nothing

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
        if self.refused_in_week():
            return None
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m3
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
        for entry in (
            self._grid.slots
            or build_day_grid(blocks, self.bounds, committed=self._committed).slots
        ):
            index = entry.slot.index
            if can_place(
                blocks, self.bounds, index, span, committed=self._committed
            ) is not None:
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
        for entry in (
            self._grid.slots
            or build_day_grid(blocks, self.bounds, committed=self._committed).slots
        ):
            if not can_place(
                blocks, self.bounds, entry.slot.index, span, committed=self._committed
            ):
                return entry.slot.index
        return None

    def _require_block_day(self, *, ask: bool = True, day: Optional[str] = None) -> bool:
        """Allow a write onto a day the user does not work, and say so.

        Purpose: PD-M7 -- a day outside the working week is a warning, not a
                 wall.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m7
        Tests:   tests/test_plan_screen.py::test_pdm131_a_drop_on_a_non_work_day_asks_nothing_and_writes
                 tests/test_plan_screen.py::test_pdm132_a_button_still_asks_on_a_non_work_day
                 tests/test_plan_screen.py::test_pdm7_a_work_day_says_nothing

        PD-M13: **a drop never asks.** No modal of any kind survives the
        moment a drag is released on macOS. The platform's own dialog raises
        ``_tkinter.TclError`` with no message from the idle callback
        ``on_drag_release`` schedules, which killed both write paths silently
        (PD-M12's traceback). An ordinary Tk toplevel with a grab and
        ``wait_window`` in its place hung the application outright: its window
        could not become visible from there, so the grab was up with nothing
        able to take it. Both were reported from the running screen on
        2026-11-07, three hours apart.

        So the drop paths pass ``ask=False`` and the question is gone from
        them. The day is not a wall -- the weekday list describes a normal
        week, and a Saturday someone has decided to work is not a mistake to
        be corrected -- so the block is written and the status line names the
        day and the week it is outside of. That is PD-M7's "a warning, not a
        wall" with the warning in the one place on this screen that cannot
        fail to appear.

        The two buttons keep the question (``ask=True``, the default): a modal
        raised from a button press is the ordinary case and the one the
        platform is content with, and AutoLoad fills a whole day, which is
        worth stopping for. Their question is wrapped all the same, because a
        dialog that raises must not take the gesture with it.

        Once per date, not once per drop, for the asking paths: the question
        is about the day, so five AutoLoads onto the same Saturday is one
        decision. The answer is held on the screen rather than written
        anywhere, so it lasts as long as the screen does and no longer -- it
        is permission for this sitting, not a change to the working week,
        which is what Day Settings is for.

        Declining leaves the same sentence the refusal used to, which is why
        the weekday list is in it: the answer to "why did nothing happen" is
        the days the week is set to.
        """
        day = day or self.selected_date
        if is_block_day(day, self.bounds):
            return True
        if day in self._work_anyway:
            return True

        allowed = [
            name for name, on in zip(weekday_names(), self.bounds.block_weekdays) if on
        ]
        week = ", ".join(allowed) if allowed else "no days"

        if not ask:
            self._non_work_day = True
            return True
        try:
            said_yes = messagebox.askyesno(
                "Not a work day",
                f"{day} is not a regular work day.\n\n"
                f"Day Settings allows {week}.\n\n"
                "Schedule anyway?",
                icon="warning",
                parent=self,
            )
        except tk.TclError as problem:
            # The failure PD-M12 was reported for, on the path that still
            # asks. A button is not the drop path and the platform has not
            # refused one, but a dialog that raises must not take the gesture
            # with it -- that is the whole of what went wrong before.
            logger.warning("the non-work-day question could not be asked: %s", problem)
            self._work_anyway.add(day)
            self._non_work_day = True
            return True

        if said_yes:
            self._work_anyway.add(day)
            return True

        self.set_status(
            f"{day} is not a block day (Day Settings allows "
            f"{week})",
            "warning",
        )
        return False

    def _take_non_work_note(self, day: Optional[str] = None) -> str:
        """What a status line owes when the gesture was on a non-work day.

        Purpose: PD-M13 -- a drop on a day outside the working week is not
                 asked about any more, so the status line it writes is the
                 only place the user learns which day they dropped on. Without
                 this the gesture's own success ("Blocked 30m for X at 09:00")
                 is written over the warning, and the warning is the half that
                 was not obvious. Surfaced, not dropped (P2).
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m13
        Tests:   tests/test_plan_screen.py::test_pdm131_a_drop_on_a_non_work_day_asks_nothing_and_writes
                 tests/test_plan_screen.py::test_pdm133_the_note_belongs_to_the_gesture

        One-shot: it belongs to the gesture it was raised for. The day itself
        is remembered in ``_work_anyway`` by the paths that ask, and nothing
        is remembered by the paths that do not -- so a second drop on the same
        Saturday is told the same thing, which is right, and a later gesture
        on a work day is not told anything, which is what the clearing is for.
        """
        if not self._non_work_day:
            return ""
        self._non_work_day = False
        allowed = [
            name for name, on in zip(weekday_names(), self.bounds.block_weekdays) if on
        ]
        week = ", ".join(allowed) if allowed else "no days"
        return (
            f" — {day or self.selected_date} is not a regular work day"
            f" (Day Settings allows {week})"
        )

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

    def bind_lunch_handlers(self, frame):
        """Make the settings' lunch chip draggable. PF-M8.

        Purpose: a day can be given its own lunch hour by dragging the one it
                 has, rather than by changing Day Settings, which moves lunch
                 on every date.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m8
        Tests:   tests/test_plan_screen.py::test_pfm84_dragging_the_lunch_chip_gives_this_date_a_lunch_block

        No right-click menu: there is no block to delete yet. Once the drag has
        created one, the chip is that block's and every block gesture applies --
        including Delete, which returns the date to the settings' lunch.
        """
        for widget in _subtree(frame):
            widget.bind("<ButtonPress-1>", self.start_lunch_drag)
            widget.bind("<B1-Motion>", self.on_drag_motion)
            widget.bind("<ButtonRelease-1>", self.on_drag_release)

    def start_lunch_drag(self, _event):
        """Begin dragging the settings' lunch, which has no block behind it."""
        self._drag_kind = "lunch"
        self._drag_block = None
        self._drag_item = None
        self._arm_drag_label("Lunch")

    def _lunch_block(self) -> Optional[TimeBlock]:
        """This date's own lunch block, if it has been moved once. PF-M8."""
        for block in self.db_manager.get_time_blocks(self.selected_date):
            if BlockType.normalize(block.block_type) == BlockType.LUNCH:
                return block
        return None

    def _outside_ids(self) -> set:
        """The ids in the "Outside the day" group, as the day is drawn now."""
        return {block.id for block in self._grid.outside}

    def _displaced_note(self, before: set) -> str:
        """What a gesture pushed out of its box, as a clause, or "" for none.

        Tests: tests/test_plan_screen.py::test_lmm3_a_lunch_move_says_how_many_blocks_it_displaced
               tests/test_plan_screen.py::test_lmm5_a_lunch_resize_says_how_many_it_displaced
        """
        displaced = len(self._outside_ids() - before)
        if not displaced:
            return ""
        plural = "" if displaced == 1 else "s"
        return f" — {displaced} Time Block{plural} moved to Outside the day"

    def place_lunch_at(self, slot_index: int):
        """PF-M8 — give this date a lunch block, or move the one it has.

        Purpose: the one gesture that makes a day's lunch its own. The first
                 drag writes the block the settings were standing in for; every
                 later one moves it, and deleting it hands the date back to Day
                 Settings.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m8
        Tests:   tests/test_plan_screen.py::test_pfm84_dragging_the_lunch_chip_gives_this_date_a_lunch_block
                 tests/test_plan_screen.py::test_pfm85_a_second_drag_moves_that_block

        The minutes come from Day Settings' lunch length: what is being moved is
        when lunch is, and its length is still a setting.
        """
        block = self._lunch_block()
        already_outside = self._outside_ids()
        try:
            if block is None:
                block = TimeBlock(
                    block_date=self.selected_date,
                    start_time="",
                    end_time="",
                    planned_minutes=self.bounds.lunch_length,
                    label="Lunch",
                    block_type=BlockType.LUNCH,
                )
                self.db_manager.add_block_at(
                    block, slot_index, self.bounds, day_span=self._grid.span
                )
            else:
                # The return value: the block read above holds the old time.
                # ``day_span`` as the add path passes it: without it the fit
                # is checked against Day Settings' hours, not the day drawn.
                block = self.db_manager.place_block_at(
                    block.id, slot_index, self.bounds, day_span=self._grid.span
                )
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except ValueError as error:
            self.set_status(str(error), "error")
            return

        self.refresh()
        self.set_status(
            f"Lunch moved to {block.start_time}"
            + self._displaced_note(already_outside),
            "success",
        )

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
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m11
        Tests:   tests/test_time_block_crud.py::test_tgm112_a_resize_that_does_not_fit_is_refused

        The in-memory ``block`` is deliberately not mutated before the write:
        it is the same object the row menu hands back on the next click, and a
        refused length left on it would show a size the database refused (P6).
        """
        already_outside = self._outside_ids()
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
            # PBG-A3 -- the drawn day, as the move paths pass it. Without it
            # a resize on a box the drawn day added was refused outright.
            resized = self.db_manager.set_block_length(
                block.id, minutes, self.bounds, day_span=self._grid.span
            )
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
        # PF-M8 -- as the move path, for the same reason.
        text += self._displaced_note(already_outside)
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m10
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

    def _day_canvas(self):
        """The canvas the day's grid scrolls inside, or ``None``.

        Purpose: PD-M11.5 -- autoscrolling the day means scrolling that canvas.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m11
        Tests:   tests/test_plan_screen.py::test_pdm115_the_day_canvas_is_the_scroll_frames_master

        A ``CTkScrollableFrame`` is the frame the rows are gridded into, and
        that frame is a child of the canvas that scrolls it. There is no
        accessor for the canvas, so this reads Tk's own ``master`` rather than
        CustomTkinter's private ``_parent_canvas``. Checked rather than
        assumed: if a later version of the library puts something else there,
        the day stops scrolling itself and nothing raises.
        """
        canvas = getattr(self.blocks_scroll, "master", None)
        return canvas if isinstance(canvas, tk.Canvas) else None

    def _autoscroll_direction(self) -> int:
        """-1 to scroll the day up, 1 down, 0 to leave it where it is.

        Purpose: PD-M11.5 -- "the Day Plan window should scroll as I drag an
                 item up or down to an area not shown".
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m11
        Tests:   tests/test_plan_screen.py::test_pdm115_the_pointer_at_the_bottom_edge_scrolls_down

        The viewport's own edges, not the pane's: the strip at each end of the
        day sits outside the canvas (PD-M11.2), and a pointer on one of those
        is choosing that end of the day rather than asking to scroll.
        """
        canvas = self._day_canvas()
        if canvas is None:
            return 0
        try:
            if not canvas.winfo_ismapped():
                return 0
            left = canvas.winfo_rootx()
            top = canvas.winfo_rooty()
            right = left + canvas.winfo_width()
            bottom = top + canvas.winfo_height()
        except tk.TclError:
            return 0

        x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
        if not left <= x_root <= right:
            return 0
        if top <= y_root <= top + PLAN_AUTOSCROLL_EDGE_PX:
            return -1
        if bottom - PLAN_AUTOSCROLL_EDGE_PX <= y_root <= bottom:
            return 1
        return 0

    def _autoscroll_steps(self, canvas) -> int:
        """How many scroll units make up one tick's worth of pixels.

        Purpose: PD-M11.5 -- a unit is whatever ``yscrollincrement`` says, and
                 CustomTkinter sets that per platform: 8px on macOS, 1px on
                 Windows. A fixed number of units would scroll a Windows day
                 eight times slower than a macOS one.
        Tests:   tests/test_plan_screen.py::test_pdm115_a_tick_is_the_same_distance_on_any_platform

        With no increment set, Tk reads a unit as a tenth of the view, so one
        is the only sane answer -- twenty-four of those would be two and a half
        screens per tick.
        """
        try:
            increment = int(canvas.cget("yscrollincrement"))
        except (tk.TclError, TypeError, ValueError):
            increment = 0
        if increment <= 0:
            return 1
        return max(1, round(PLAN_AUTOSCROLL_STEP_PX / increment))

    def _tick_autoscroll(self):
        """Scroll the day one step and come back, while the drag stays at the edge.

        Purpose: PD-M11.5 -- its own clock. A pointer held still at the bottom
                 of the pane delivers no motion events, so a scroll driven by
                 motion alone would stop exactly when it is wanted most.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m11
        Tests:   tests/test_plan_screen.py::test_pdm116_a_tick_outside_the_edge_zone_stops_the_scroll

        Rescheduling is the last thing it does, so the loop ends by not
        starting another tick -- there is no job left to cancel when the drag
        ends inside a tick.
        """
        self._autoscroll_job = None
        if not self._drag_kind:
            return
        direction = self._autoscroll_direction()
        if direction == 0:
            return
        canvas = self._day_canvas()
        if canvas is None:
            return
        try:
            canvas.yview_scroll(direction * self._autoscroll_steps(canvas), "units")
        except tk.TclError:
            return
        # The boxes moved under a pointer that did not: without this the
        # outline stays on the box that used to be there.
        self.update_hover_target()
        self._autoscroll_job = self.after(PLAN_AUTOSCROLL_MS, self._tick_autoscroll)

    def _pump_autoscroll(self):
        """Start the scroll if the pointer is at an edge and it is not running."""
        if self._autoscroll_job is not None:
            return
        if self._autoscroll_direction() != 0:
            self._tick_autoscroll()

    def _stop_autoscroll(self):
        """Cancel the pending tick, if there is one.

        Purpose: PD-M11.7 -- a tick that fires after the drag has ended would
                 scroll the day for a pointer that is not holding anything.
        Tests:   tests/test_plan_screen.py::test_pdm117_ending_a_drag_cancels_the_scroll
        """
        if self._autoscroll_job is not None:
            try:
                self.after_cancel(self._autoscroll_job)
            except (tk.TclError, ValueError):
                pass
            self._autoscroll_job = None

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
        self._pump_autoscroll()

    def on_drag_release(self, _event):
        kind, item, block = self._drag_kind, self._drag_item, self._drag_block
        commitment = getattr(self, "_drag_commitment", None)
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
        if kind == "item" and item is not None and self._week_mode:
            self.drop_on_week(item)
        elif kind == "item" and item is not None:
            # PF-M1 -- the question the buttons ask, asked here.
            #
            # PD-M13 took it off this path because a modal opened from the
            # idle callback below raised TclError on macOS, and an in-app
            # toplevel in its place hung the app. Both were reported from
            # the running screen. What cannot happen there is the modal *in
            # the idle callback*; this handler is the moment the gesture is
            # still synchronous, and it is the moment the Scheduler already
            # asks from. So the question is here, the write stays below, and
            # the ask is wrapped (`_allow_this_day`): a platform that refuses
            # the dialog writes the block and says which day it was on, which
            # is what happened before this module.
            #
            # Read first, refuse second, ask third, schedule fourth. The
            # pointer has to be read while it is still there; a drop that
            # cannot write is refused before the day's one answer is spent on
            # it, because the yes is remembered whether the write happens or
            # not; and a drop on the heading is not worth a question about
            # nothing.
            if target is not None:
                refusal = self._drop_refusal(item, target)
                if refusal is not None:
                    self.set_status(refusal, "warning")
                    return
                if not self._allow_this_day():
                    return
                self.after_idle(lambda: self.block_item(item, target))
            elif edge is not None:
                refusal = self._already_blocked_text(item)
                if refusal is not None:
                    self.set_status(refusal, "warning")
                    return
                if not self._allow_this_day():
                    return
                self.after_idle(lambda: self.extend_day_for(item, edge))
            elif self.pointer_over_day():
                # In the day column but not on a box -- the heading, the
                # summary, or the "outside the day" group below the grid.
                # Reported rather than guessed at: picking a box for them
                # would put the work somewhere they did not point.
                self.set_status("Drop an Action Item on a Time Block", "muted")
        elif kind == "block" and block is not None:
            if target is not None:
                self.after_idle(lambda: self.move_block_to_slot(block.id, target))
            elif edge is not None:
                # PF-M9 -- a scheduled Action Item can lengthen the day too.
                # It used to be refused on the argument that the day grows for
                # work that is not planned yet; reported from the running screen
                # on 2026-11-10 as "dragging an item to earlier than day start
                # doesn't work", which is what a refusal with no reason the user
                # can act on looks like.
                self.after_idle(lambda: self.move_block_to_edge(block.id, edge))
            elif self.pointer_over_day():
                # Same reason as the item branch above, and the same words'
                # worth of explanation: a move that does nothing and says
                # nothing is indistinguishable from a drag that missed.
                self.set_status("Drop that Action Item on a Time Block", "muted")
        elif kind == "commitment" and commitment is not None:
            # CIP-M4.2 / E3 -- asked and started here, while the gesture is
            # still synchronous (PD-M13: no modal from an idle callback).
            # Starting the worker destroys no widget, so this is safe inside
            # the handler; the redraw comes from the poll.
            if target is not None:
                self.drop_commitment(commitment, target)
            elif edge is not None or self.pointer_over_day():
                self.set_status("Drop a meeting on a Time Block to move it", "muted")
        elif kind == "lunch":
            # PF-M8 -- the settings' lunch, dragged. The first one writes the
            # block this date was standing in for; later ones move it.
            if target is not None:
                self.after_idle(lambda: self.place_lunch_at(target))
            elif edge is not None:
                # LM3-M1 (LMM-A3): an Action Item or a block dropped on
                # Earlier/Later lengthens the day. Lunch does not -- a lunch
                # outside the working day means nothing -- and this says so
                # rather than doing nothing.
                self.set_status(LUNCH_EDGE_TEXT, "warning")
            elif self.pointer_over_day():
                self.set_status("Drop lunch on a Time Block", "muted")

    def _end_drag(self):
        """Take the label off the screen and forget what was being dragged.

        Purpose: PD-M10.5 -- a release that lands on nothing writes nothing and
                 redraws nothing, so without the flush here the label stayed
                 visible until some later event repainted the screen.
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m10
        Tests:   tests/test_plan_screen.py::test_pdm105_ending_a_drag_hides_the_label_and_flushes

        Flushing from inside the ButtonRelease handler is safe here and only
        here: ``on_drag_release`` calls this before it schedules the drop's own
        ``after_idle``, so there is no queued rebuild for the flush to dispatch
        into the widget that is dispatching this event.
        """
        self._stop_autoscroll()
        self._drag_label_text = None
        if self._drag_label is not None:
            self._drag_label.place_forget()
            self._flush_redraw()
        self._drag_kind = None
        self._drag_item = None
        self._drag_block = None
        self._drag_commitment = None

    def _day_shape_is_the_users(self) -> bool:
        """Whether ``self.bounds`` came from settings we could actually read.

        Purpose: TG-M5 -- adoption is irreversible, so it must not run on a
                 guess. A settings file that exists but failed to parse yields
                 an all-defaults object, which is indistinguishable from a
                 real fresh install unless the loader says so -- and says so in
                 a field that goes to disk, since the first save from any
                 screen writes those defaults out as ordinary settings.
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m5
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m9
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
        Spec:    docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m5
        Tests:   tests/test_plan_screen.py::test_pdm114_a_drop_on_an_end_needs_no_pointer_in_the_scrolling_grid
                 tests/test_plan_screen.py::test_pdm5_a_drop_in_the_day_but_on_no_box_still_does_nothing

        Read the same way as ``slot_under_pointer`` and only after it has
        answered ``None``: a real box always wins.

        No ``blocks_scroll`` guard, unlike ``slot_under_pointer``. Since
        PD-M11.2 these two boxes are outside the scrolling grid -- that is the
        whole point of them being there -- so a pointer on one of them is not
        in the scroll frame at all, and the guard refused every drop on them.
        Nothing is lost by dropping it: the rectangles tested here are the two
        boxes themselves, not the pane they are in.
        """
        x_root, y_root = self.winfo_pointerx(), self.winfo_pointery()
        for frame, edge in self._virtual_frames:
            if widget_contains_pointer(frame, x_root, y_root):
                return edge
        return None

    def extend_day_for(self, item: ActionItem, edge: str):
        """PD-M14.1 — block the item past one end of the day, writing no settings.

        Purpose: "allow items to extend the day earlier or later when they are
                 dropped above the first block or below the last" (PD-M5),
                 rewritten to the instruction that the hours in Day Settings
                 "are solely for starting a blank plan for the day".
        Spec:    docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-1
        Tests:   tests/test_plan_screen.py::test_pdm141_a_drop_on_earlier_writes_no_settings

        One block, in one transaction, and nothing else. Not ``plan_day_start``,
        not ``plan_day_end``, not ``settings.save()``, and not
        ``shift_all_slots``.

        **What this replaces, and why it had to go.** The previous version moved
        the bound and renumbered every date's blocks to compensate. Both halves
        were forced by the same fact: ``slot_index`` counts boxes from Day
        Start, and Day Start is **one setting shared by every date**, so there
        was no way to lengthen one day without redefining all of them. Each
        drop on **Earlier** moved the setting back permanently -- nothing wrote
        it forward again, Clear Day included -- and the renumbering it needed
        touched every date in the file. Both reported faults were that one
        mechanism.

        Now the drawn day is derived from the date's own blocks
        (``DayGrid.span``, PD-M14.2) and a slot index is allowed to be
        negative, so the day grows at this date only, by writing the block that
        asked for it. Nothing is stored about the hours of a date, so nothing
        about them can go stale (P6) and nothing has to be put back: deleting
        the block is what un-stretches the day (PD-M14.3).

        No settings object is needed any more either, so a drop works on an
        instance whose settings file would not parse -- it used to refuse.

        The rollback arm went with the settings write. The only write left is
        the block, and ``add_block_at`` checks the fit before it writes
        anything, so a refusal leaves the day exactly as it was.
        """
        # PD-M13 -- a drop never asks; see _require_block_day.
        if not self._require_block_day(ask=False):
            return

        # PF-M2 -- the same one-block rule the box drop obeys. Without it the
        # invariant the refusal states was false on this path: an item already
        # at 09:00 could be dropped on Earlier and get a second block.
        blocked = self._already_blocked_text(item)
        if blocked is not None:
            self._non_work_day = False
            self.set_status(blocked, "warning")
            return

        minutes = duration_for_item(item, self.bounds.default_block_minutes)
        span = slots_for_minutes(minutes)
        # The day as it is drawn, which is the day the user dropped past. Not
        # the template's hours: with a block already outside them, "the box
        # above the first one" is above that block.
        grown = extended_span(self._grid.span, self.bounds, edge, span)
        if grown is None:
            # PD-M14.6 -- the two limits differ, so the message names the end
            # that was dropped on and the time it stops at, in one sentence
            # both ends share.
            name = PD_EARLIER_TEXT if edge == DAY_EXTEND_EARLIER else PD_LATER_TEXT
            self.set_status(
                f"{name} stops at {edge_limit_time(edge)}: "
                f"{minutes}m of {item.title} would put the block outside "
                f"{self.selected_date}",
                "warning",
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
            self.db_manager.add_block_at(
                block, grown.slot_index, self.bounds, day_span=grown.span
            )
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except Exception as problem:
            # Broad on purpose: a write that failed for any other reason is
            # still a drop that did not happen, and the screen has to say so
            # rather than leave the item looking placed. The class name when
            # the exception carries no message, which several built-ins do.
            self.refresh()
            self.set_status(
                f"The day was not extended — "
                f"{str(problem) or type(problem).__name__}",
                "error",
            )
            return

        self.refresh()
        self.set_status(
            f"The day now shows "
            f"{times_for_slot(grown.span.first, SLOT_MINUTES, self.bounds)[0]}–"
            f"{times_for_slot(grown.span.last, SLOT_MINUTES, self.bounds)[1]}; "
            f"blocked {minutes}m for {item.title} at {block.start_time}"
            + self._take_non_work_note(),
            "success",
        )

    def move_block_to_slot(self, block_id: str, slot_index: int):
        """TG-M11 — put a dragged block on the box it was dropped on.

        Spec:  docs/unused-docs/implementation_plan_2026-11-05_time_grid.md#tg-m11
        Tests: tests/test_plan_screen.py::test_tgm111_a_real_drag_moves_a_block_between_slots

        A refusal is reported and nothing is written. Moving the block to some
        other box that happens to fit would be the screen deciding where the
        user's work goes.
        """
        try:
            # LMM-A1 -- ``slot_index`` came off ``_slot_frames``, built over
            # the drawn span, so that is the day to check against.
            moved = self.db_manager.place_block_at(
                block_id, slot_index, self.bounds, day_span=self._grid.span
            )
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except ValueError as error:
            self.set_status(str(error), "error")
            return
        self.load_blocks()
        self.set_status(f"Moved to {moved.start_time}", "success")

    def move_block_to_edge(self, block_id: str, edge: str):
        """PF-M9 — put a scheduled Action Item past one end of the day.

        Purpose: the same gesture an Action Item from the list makes, for work
                 that is already in a Time Block. It used to be refused with a
                 sentence about "a block" making "a new half hour", which said
                 nothing a user could act on and used one word for two things.
        Spec:    docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md#pf-m9
        Tests:   tests/test_plan_screen.py::test_pfm91_a_scheduled_item_makes_the_day_earlier

        The day grows by the block's own length, as it does for an Action Item
        from the list, and the block lands in the new outer box.
        """
        block = self.db_manager.get_time_block(block_id)
        if block is None:
            self.set_status("That Action Item is no longer on the day", "error")
            return

        grown = extended_span(
            self._grid.span,
            self.bounds,
            edge,
            slots_for_minutes(block.planned_minutes),
        )
        if grown is None:
            self.set_status(
                f"{PD_EARLIER_TEXT if edge == DAY_EXTEND_EARLIER else PD_LATER_TEXT}"
                f" stops at {edge_limit_time(edge)} — the day cannot go "
                f"further that way",
                "warning",
            )
            return

        try:
            moved = self.db_manager.place_block_at(
                block.id, grown.slot_index, self.bounds, day_span=grown.span
            )
        except SlotRefusedError as refused:
            self.set_status(refusal_text(refused.reason), "error")
            return
        except ValueError as error:
            self.set_status(str(error), "error")
            return

        self.refresh()
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
        if self._week_mode:
            # CIP-M6.5 -- the week's box, by date and half hour.
            hovered = self.week_box_frame(self.week_box_under_pointer())
        elif target is not None:
            for frame, slot_index in self._slot_frames:
                if slot_index == target:
                    hovered = frame
                    break
        if hovered is self._drag_hover_frame:
            return
        self.clear_hover_target()
        if hovered is not None:
            self._drag_hover_border = hovered.cget("border_width")
            self._drag_hover_colour = hovered.cget("border_color")
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
                    border_width=self._drag_hover_border,
                    border_color=self._drag_hover_colour,
                )
            except tk.TclError:
                pass
            self._drag_hover_frame = None
