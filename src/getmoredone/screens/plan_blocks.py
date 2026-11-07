"""TB-M7/TB-M12 — the two row widgets the Plan screen is built from.

Purpose: render one draggable action item, and one time block, with the
         priority band as an accent, depth as a three-bar stack, and a height
         that tracks the block's length.
Spec:    docs/implementation_plan_2026-11-05_time_blocks.md#tb-m12
Tests:   tests/test_plan_screen.py

Every colour here comes from theme.py. The project rule is no hard-coded hex
in widgets, and a band colour written inline would be a second place it could
be changed from -- which is the condition the rule exists to prevent, not a
style preference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import customtkinter as ctk

from ..color_contrast import pick_text_color
from ..models import ActionItem, BlockType, Status, TimeBlock
from ..theme import (
    block_type_colors,
    depth_bar_colors,
    priority_band_colors,
    priority_fill_colors,
    priority_stripe_colors,
    semantic_colors,
    status_text_color,
)
from ..time_block_layout import (
    MAX_DEPTH_BARS,
    depth_bars,
    priority_band,
    slots_for_minutes,
    spare_minutes_in_last_slot,
)

# The coloured edge that carries the priority band. Narrow on purpose: the
# project's theme rule allows a DB/semantic colour as a chip or stripe accent
# and not as a full-row fill, because a wall of saturated rows stops carrying
# information and starts fighting the text on top of it.
STRIPE_WIDTH_PX = 6

#: What the stripe asks to be tall. It is gridded ``sticky="ns"`` and stretched
#: to its cell, so this number only has to be small -- but it has to be given.
#: ``ctk.CTkFrame`` requests 200x200 when neither dimension is set, and the
#: stripe set ``width`` alone, so its height request was a constant nobody
#: chose. Every container that let a child's request through grew to 200px:
#: an item row five times taller than its two lines of text, and a task chip
#: whose title was laid out at y=100 inside a box clipped to 34, which is why
#: a planned box showed nothing but the bar.
STRIPE_MIN_HEIGHT_PX = 12

#: Height of one task chip, and so what each task adds to a box's height, and
#: the half-hour unit an item row in the left pane is a multiple of. The
#: fallback only: PB-M5 takes the live value from
#: ``AppSettings.drag_schedule_box_height_px``, and this is what a missing or
#: unusable setting resolves to.
SLOT_CHIP_HEIGHT_PX = 30

#: What a task's title column asks for, in a box and in an item row alike: one
#: width across the two panes is what makes their columns line up. The fallback
#: only -- PB-M5 takes the live value from
#: ``AppSettings.drag_schedule_title_col_width``.
SLOT_TITLE_WIDTH_PX = 80

#: The gap between a task's stripe and its title, counted into the stripe's own
#: column so that column is the stripe plus its gap.
SLOT_STRIPE_GAP_PX = 8

#: What the depth bars' column and the length's column ask for. The bar stack
#: is 14px of bar in a 22px column; the length is a right-aligned label of its
#: own fixed width, so "30m" and "120m" end at the same pixel.
SLOT_BARS_WIDTH_PX = 22
SLOT_LENGTH_WIDTH_PX = 48

#: The column left of the depth bars. In the left pane it carries the marker
#: that says the day already holds a block for this item; in a day box it is
#: empty. It is a column in both so the two panes stay in step: a marker drawn
#: inside the title column would push the bars and the length of a blocked row
#: out of line with every other row and with the day beside it.
SLOT_MARKER_WIDTH_PX = 16

#: The gap between the end of a task's line and the right edge of the box or
#: row it is drawn in. Counted into the length's own column, so the panes'
#: widths and PD-M2's clamp both account for it.
CHIP_RIGHT_INSET_PX = 8

#: The marker itself. A chevron rather than the green check: the check already
#: means "this task is finished" on a day box (PD-M6), and one glyph cannot
#: carry both "done" and "has a block today" without saying the wrong one half
#: the time.
PD_BLOCKED_TEXT = ">"

#: The chip's columns by name, so a renderer and a test can refer to the same
#: index without counting.
CHIP_STRIPE_COLUMN = 0
CHIP_TITLE_COLUMN = 1
CHIP_MARKER_COLUMN = 2
CHIP_BARS_COLUMN = 3
CHIP_LENGTH_COLUMN = 4


def chip_column_minsizes(title_width: int = SLOT_TITLE_WIDTH_PX):
    """The column widths one task's line is laid out in, in order.

    Purpose: PD-M1.1 -- a day box and an item row are the same four columns,
             so there is one place that says what those columns are.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m1
    Tests:   tests/test_plan_screen.py::test_pdm11_the_item_row_uses_the_chips_column_order

    Both renderers configure their columns from here, and PD-M2's clamp adds
    them up to find the narrowest a pane can be dragged to and still draw a
    row. Written out twice they agreed by inspection, which is the kind of
    agreement that lasts until someone widens one of them.
    """
    return (
        STRIPE_WIDTH_PX + SLOT_STRIPE_GAP_PX,
        title_width,
        SLOT_MARKER_WIDTH_PX,
        SLOT_BARS_WIDTH_PX,
        SLOT_LENGTH_WIDTH_PX + CHIP_RIGHT_INSET_PX,
    )


def configure_chip_columns(widget, title_width: int = SLOT_TITLE_WIDTH_PX) -> None:
    """Lay a widget out in the chip's columns, whatever there are of them.

    Both renderers call this rather than configuring columns by index, so a
    column added to ``chip_column_minsizes`` reaches both panes or neither.
    The title takes the slack; every other column is the width it asks for.
    """
    for column, width in enumerate(chip_column_minsizes(title_width)):
        widget.grid_columnconfigure(
            column, minsize=width, weight=1 if column == CHIP_TITLE_COLUMN else 0
        )


#: The vertical gap between two consecutive boxes of the day: ``build_slot_row``
#: grids each box ``pady=1``, so one box's bottom edge and the next box's top
#: edge are 2px apart. An item row has to add it back, or an N-box row is 2(N-1)
#: pixels shorter than the N boxes it claims to be the size of.
SLOT_ROW_GAP_PX = 2

#: The least an item row may be drawn at, whatever the box height says: what
#: its own grid asks for. One line now -- the title's 5px top pad and its 28px
#: line -- because the ``already blocked`` words became a glyph on that same
#: line and took the second row away with them.
#:
#: It was 67 under PB-M6 and 66 under PD-M1, when the row had a second line for
#: the ``already blocked`` words. That floor was two boxes' worth of height at
#: any box height a user is likely to set, so a 30-minute row and a 60-minute
#: row were drawn within a few pixels of each other and the left pane stopped
#: showing how much of the day an item would take -- the one thing it is the
#: height it is in order to show. The words are a glyph on the title's line
#: now, and with them the second row and the floor they imposed.
#:
#: Measured, every time it has changed, by
#: ``test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for``, which reads the
#: requirement off the widgets the row builds. It is there because the number
#: was first written by hand as 66 when the arithmetic said 67, and the row
#: silently lost the last pixel of its bottom padding: nothing was unreadable
#: and no other assertion could see it, because the labels anchor to the top of
#: their cells. This is the one number here justified purely by arithmetic, so
#: the arithmetic is checked rather than restated.
#:
#: At one line the floor is below ``SLOT_MIN_HEIGHT_PX``, so the row and the
#: day now agree at every box height: a 90-minute item is three boxes tall
#: because the day will give it three boxes.
ITEM_ROW_MIN_HEIGHT_PX = 33


def stripe_for_item(item: Optional[ActionItem]) -> str:
    """PB-M1 — the brighter band colour, for the stripe on an item's row."""
    return priority_stripe_colors()[_band_of(item)]


def fill_for_item(item: Optional[ActionItem]) -> str:
    """PB-M4 — the shade a task is drawn on, by the priority behind it."""
    return priority_fill_colors()[_band_of(item)]


def _band_of(item: Optional[ActionItem]) -> str:
    """Which priority band an item falls in, or "unscored" when there is none."""
    if item is None:
        return "unscored"
    return priority_band(getattr(item, "priority_score", 0))


def accent_for_item(item: Optional[ActionItem]) -> str:
    """The band colour for the item behind a block, or the unscored grey."""
    return priority_band_colors()[_band_of(item)]


def accent_for_block(block: TimeBlock, item: Optional[ActionItem]) -> str:
    """The accent for a block: its priority band, or a neutral for padding.

    Buffer and break blocks carry no item, so they get a neutral. Colouring
    them by a priority they do not have would be information the eye reads and
    the data does not support.
    """
    kind = BlockType.normalize(block.block_type)
    if kind in (BlockType.BUFFER, BlockType.BREAK):
        return block_type_colors()[kind]
    return accent_for_item(item)


def stripe_for_block(block: TimeBlock, item: Optional[ActionItem]) -> str:
    """PB-M1 — ``accent_for_block`` in the brighter stripe table.

    Padding keeps its neutral: ``block_type_colors`` is already the dimmest
    thing on the row and brightening it would make a buffer compete with the
    task beside it for attention it has no claim to.
    """
    kind = BlockType.normalize(block.block_type)
    if kind in (BlockType.BUFFER, BlockType.BREAK):
        return block_type_colors()[kind]
    return stripe_for_item(item)


class DepthBarStack(ctk.CTkFrame):
    """Depth drawn as three stacked bars, the filled count showing how deep.

    Deep fills three, Medium two, Shallow one, and an item with no depth set
    fills one -- requirement 8's "Default depth to 1".
    """

    BAR_WIDTH_PX = 14
    BAR_HEIGHT_PX = 3
    BAR_GAP_PX = 2

    def __init__(self, parent, depth: Optional[str], **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.filled = depth_bars(depth)
        colors = depth_bar_colors()

        # Drawn top-heavy: the deepest bar sits at the top of the stack, so a
        # column of blocks reads as a bar chart down the day.
        for index in range(MAX_DEPTH_BARS):
            is_filled = index >= (MAX_DEPTH_BARS - self.filled)
            bar = ctk.CTkFrame(
                self,
                width=self.BAR_WIDTH_PX,
                height=self.BAR_HEIGHT_PX,
                corner_radius=1,
                fg_color=colors["filled"] if is_filled else colors["empty"],
            )
            bar.grid(row=index, column=0, pady=(0, self.BAR_GAP_PX))
            bar.grid_propagate(False)


def item_row_height(span: int, box_height: int = SLOT_CHIP_HEIGHT_PX) -> int:
    """How tall an item row is drawn: the space the day gives it, exactly.

    Purpose: PB-M6.1 -- an item row is the size of the space it will take, so
             the day's room for it is visible before the drag.
    Spec:    docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m6
    Tests:   tests/test_plan_screen.py::test_pbm61_an_item_row_is_the_height_the_day_would_give_it

    ``span`` boxes of ``slot_row_height(1, box_height)``, plus the
    ``SLOT_ROW_GAP_PX`` between each pair -- the measurement a user would take
    from the top edge of the first box to the bottom edge of the last, in a day
    whose boxes hold this task and nothing else -- and never less than
    ``ITEM_ROW_MIN_HEIGHT_PX``, so a row that cannot match the day and stay
    readable stays readable.

    A box already holding another task is taller still (``slot_row_height``
    counts chips), so the equality is with the empty day the item would be
    dropped into, not with every day.

    Named rather than inlined for the reason ``slot_row_height`` is: the first
    version multiplied ``box_height`` by the span, which is 2px per box short
    of the day and 4px short of one box, and its test asserted that same
    product. The claim and the check agreed with each other and not with the
    screen. Both now go through here, and the box height comes from
    ``slot_row_height``, so the two panes cannot drift apart without this
    function changing.
    """
    as_the_day_draws_it = (
        span * slot_row_height(1, box_height) + SLOT_ROW_GAP_PX * (span - 1)
    )
    return max(ITEM_ROW_MIN_HEIGHT_PX, as_the_day_draws_it)


def build_item_row(
    parent,
    item: ActionItem,
    row: int,
    already_blocked: bool,
    work_block_minutes: int,
    *,
    box_height: int = SLOT_CHIP_HEIGHT_PX,
    title_width: int = SLOT_TITLE_WIDTH_PX,
) -> ctk.CTkFrame:
    """One action item in the left pane, ready to be dragged onto the day.

    Purpose: PD-M1 -- an item is drawn as the thing it is about to become: a
             task in a box, at the size of the space it will take.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m1
    Tests:   tests/test_plan_screen.py::test_pdm11_the_item_row_uses_the_chips_column_order
             tests/test_plan_screen.py::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it
             tests/test_plan_screen.py::test_pbm61_every_line_of_a_row_is_drawn_inside_it

    Returns the frame, so the caller can bind the drag handlers to it and to
    its children -- a press that lands on a label must start the same drag as
    one that lands on the frame, or half the row is dead to the mouse.

    The first line is ``_build_block_chip``'s line: the same four columns in
    the same order at the same widths -- stripe, title, depth bars, length --
    so the two panes read as one list of tasks either side of a divider. PB-M6
    built it as two stacked lines with the length under the bars, which
    mirrored a box's facts without mirroring its layout, and on screen the
    left pane still looked like a different kind of thing from the right.

    ``title_width`` is passed through from the same Drag Schedule setting the
    boxes use for it. Taken from a constant here instead, the two panes would
    line up at the default and nowhere else.

    ``PD_BLOCKED_TEXT`` sits in its own column left of the depth bars, and only
    when the day already holds a block for this item: the one scheduling fact a
    box does not already show. It was two words on a second line until the row
    had to be the height of the space it will take, which a second line made
    impossible -- the floor that line imposed was two boxes tall, so every row
    shorter than that was drawn at the floor and a 30-minute item looked the
    size of an hour. The depth word went at PD-M1.5, a fourth way of saying
    what the row's shade, its stripe and its bar stack all say.

    The height is the space the day will give those half hours, asked of
    ``slot_row_height`` rather than recomputed: one box plus the 2px gap to the
    next, ``slots_for_minutes`` times over. A 90-minute item is three boxes tall
    on the left because it will be three boxes tall on the right.
    ``grid_propagate(False)`` is what holds it there; a row that grew to its own
    text would be telling the user a length it does not have.

    Multiplying ``box_height`` directly was 2px per box short of the day, and
    the test asserted the same formula the code used, so the one relationship
    this function exists for was the one thing unchecked.

    No row carries weight any more. A second row did, which kept the two lines
    at the top of a tall row and made a row too short for both lose the empty
    space rather than the text: with the weight on row 0, Tk took the whole
    shortfall out of it and collapsed the title to a single pixel. With one
    line and a floor that is that line's own height the shortfall cannot
    happen, Tk leaves the slack unallocated at the bottom, and the text sits at
    the top either way -- so the line was kept until the mutation gate showed
    that moving the weight changed nothing it could see.
    """
    fill = fill_for_item(item)
    on_fill = pick_text_color(fill)
    span = slots_for_minutes(work_block_minutes)
    frame = ctk.CTkFrame(
        parent,
        fg_color=fill,
        corner_radius=6,
        height=item_row_height(span, box_height),
    )
    frame.grid(row=row, column=0, sticky="ew", pady=3, padx=2)
    # The chip's columns, kept in the same order and at the same widths by
    # ``test_pdm11_the_item_row_uses_the_chips_column_order``, which reads them
    # off a real chip rather than restating them.
    configure_chip_columns(frame, title_width)
    frame.grid_propagate(False)

    stripe = ctk.CTkFrame(
        frame,
        width=STRIPE_WIDTH_PX,
        height=STRIPE_MIN_HEIGHT_PX,
        fg_color=stripe_for_item(item),
        corner_radius=3,
    )
    stripe.grid(
        row=0, column=CHIP_STRIPE_COLUMN, rowspan=2, sticky="ns",
        padx=(0, 8), pady=4,
    )
    stripe.grid_propagate(False)

    title = ctk.CTkLabel(
        frame, text=item.title, anchor="w", justify="left", text_color=on_fill
    )
    title.grid(row=0, column=CHIP_TITLE_COLUMN, sticky="ew", pady=(5, 0))

    if already_blocked:
        # Marked, not hidden: an item can genuinely need two blocks in a day,
        # and removing it from the list would look like it had vanished. A
        # glyph rather than the words it replaced, which cost the row a second
        # line and so cost every row in the pane the height that made it the
        # size of the space it will take.
        ctk.CTkLabel(
            frame,
            text=PD_BLOCKED_TEXT,
            width=SLOT_MARKER_WIDTH_PX,
            anchor="w",
            text_color=on_fill,
        ).grid(row=0, column=CHIP_MARKER_COLUMN, sticky="nw", pady=(5, 0))

    bars = DepthBarStack(frame, item.depth)
    bars.grid(
        row=0, column=CHIP_BARS_COLUMN, padx=(4, 6), pady=(5, 0), sticky="n"
    )

    # The length, where a box writes it: the right-hand end of the task's own
    # line. This is the same task before it has been dragged there.
    ctk.CTkLabel(
        frame,
        text=f"{work_block_minutes}m",
        width=SLOT_LENGTH_WIDTH_PX,
        anchor="e",
        text_color=on_fill,
    ).grid(
        row=0, column=CHIP_LENGTH_COLUMN, sticky="ne",
        padx=(0, CHIP_RIGHT_INSET_PX), pady=(5, 0),
    )

    return frame


# ``build_block_row`` was here: one row per block, as tall as the block was
# long. ``build_slot_row`` below draws one row per half hour instead, which is
# what lets a box hold two tasks and an empty box be drawn at all.


def _block_title(block: TimeBlock, item: Optional[ActionItem]) -> str:
    """What to call a block: its item's title, its label, or its kind."""
    kind = BlockType.normalize(block.block_type)
    if kind == BlockType.BUFFER:
        return block.label or "Buffer"
    if kind == BlockType.BREAK:
        return block.label or "Break"
    if item is not None:
        return item.title
    # An item block whose item is gone. Named rather than blank: a block with
    # no text looks like a rendering fault, and the label is the last record of
    # what it was for.
    return block.label or "(item no longer exists)"


# ``build_lunch_band`` was here. The grid marks lunch slots rather than
# removing them, so lunch is a box like any other and needs no separate band.


# =====================================================================
# TG-M7 -- the 30-minute grid
#
# One row per half hour from Day Start to Day End, drawn whether anything is
# in it or not. An empty 09:00 between two filled boxes is a legitimate day,
# not a state to pack away, so the empty boxes are the point rather than
# something to hide.
# Spec: docs/implementation_plan_2026-11-05_time_grid.md#tg-m7
# =====================================================================

#: The time column's width. Fixed, so every row's titles start at the same x
#: -- aligned columns are a design goal in this repo's tabular UIs, and a time
#: column sized to its own text is the first thing that breaks it.
SLOT_TIME_WIDTH_PX = 58

#: What an empty box is tall enough to be a drop target for. A box the pointer
#: struggles to land on is a box the user cannot plan into.
SLOT_MIN_HEIGHT_PX = 32

#: Defined with the stripe constants above, not here with the rest of the box
#: sizes, because ``build_item_row`` takes it as a default argument and a
#: default is evaluated where the function is defined.
#: (``SLOT_CHIP_HEIGHT_PX``)

#: Defined with the stripe constants above for the reason
#: ``SLOT_CHIP_HEIGHT_PX`` is: PD-M1 made it a default argument of
#: ``build_item_row``, so it has to exist by the time that function is defined.
#: (``SLOT_TITLE_WIDTH_PX``)

#: PD-M6 -- the completion mark, and the column it sits in to the left of the
#: time. A column of its own rather than a prefix on the time label: the mark
#: is green and the time is not, and one label cannot be two colours.
PD_CHECK_TEXT = "\u2713"
SLOT_CHECK_WIDTH_PX = 16


@dataclass
class SlotRow:
    """A rendered box, and the per-block widgets a caller must bind to.

    The widgets are handed back rather than bound here so this module stays
    free of the screen's drag and menu state: it draws, and ``plan.py`` decides
    what a press on one of these means.
    """

    frame: ctk.CTkFrame
    slot_index: int
    block_widgets: List[Tuple[TimeBlock, ctk.CTkFrame]] = field(default_factory=list)


def _configure_slot_columns(frame: ctk.CTkFrame) -> None:
    """Every column gets a width to request, following the Schedule panel.

    ``_configure_date_box_columns`` in drag_schedule.py is the working sibling:
    its date boxes also switch off grid propagation and render correctly
    because no column is left to be sized by whatever happens to be in it.
    """
    frame.grid_columnconfigure(0, minsize=SLOT_CHECK_WIDTH_PX)
    frame.grid_columnconfigure(1, minsize=SLOT_TIME_WIDTH_PX)
    frame.grid_columnconfigure(2, minsize=120, weight=1)
    frame.grid_rowconfigure(0, weight=1)


def slot_row_height(chips: int, chip_height: int = SLOT_CHIP_HEIGHT_PX) -> int:
    """How tall a box holding this many task chips is drawn.

    Purpose: PB-M5 -- box height follows the Drag Schedule box-height setting.
    Spec:    docs/implementation_plan_2026-11-06_plan_box_appearance.md#pb-m5
    Tests:   tests/test_plan_screen.py::test_pbm51_box_height_follows_the_setting

    Named rather than inlined because two tests and the renderer all need the
    same answer, and a second copy of the arithmetic is how a layout assertion
    starts agreeing with itself instead of with the screen.

    An empty box keeps ``SLOT_MIN_HEIGHT_PX`` whatever the setting says: it
    holds no text, and its height only has to be enough to drop onto.
    """
    return max(SLOT_MIN_HEIGHT_PX, chips * chip_height + 4)


def build_slot_row(
    parent,
    grid_slot,
    items_by_id: Dict[str, ActionItem],
    row: int,
    *,
    chip_height: int = SLOT_CHIP_HEIGHT_PX,
    title_width: int = SLOT_TITLE_WIDTH_PX,
) -> SlotRow:
    """One half-hour box of the day.

    Purpose: TG-M7/TG-M10 -- the fixed grid, including the boxes holding more
             than one task.
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m7
    Tests:   tests/test_plan_screen.py::test_tgm71_every_slot_is_drawn

    A box drawn for a lunch half hour says so and takes no tasks. A box that a
    longer task runs through shows that task greyed and marked, so the user can
    see what the box is spent on without it looking like a second copy of the
    task.
    """
    palette = semantic_colors()
    slot = grid_slot.slot
    chips = len(grid_slot.starting) + len(grid_slot.continued)

    if slot.is_lunch or slot_is_padding(grid_slot):
        fill = palette["surface"]
    elif grid_slot.is_empty:
        fill = "transparent"
    else:
        fill = palette["surface_subtle"]

    frame = ctk.CTkFrame(
        parent,
        fg_color=fill,
        corner_radius=6,
        height=slot_row_height(chips, chip_height),
        border_width=1,
        border_color=palette["border"],
    )
    frame.grid(row=row, column=0, sticky="ew", pady=1, padx=2)
    _configure_slot_columns(frame)
    # The height is what tells the user a box holds two tasks rather than one,
    # so it must survive its children.
    frame.grid_propagate(False)

    if slot_is_complete(grid_slot, items_by_id):
        ctk.CTkLabel(
            frame,
            text=PD_CHECK_TEXT,
            width=SLOT_CHECK_WIDTH_PX,
            anchor="w",
            text_color=status_text_color("success"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="nw", padx=(6, 0), pady=4)

    ctk.CTkLabel(
        frame,
        text=slot.start_time,
        width=SLOT_TIME_WIDTH_PX,
        anchor="w",
        text_color=palette["time_text"],
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=1, sticky="nw", padx=(8, 4), pady=4)

    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.grid(row=0, column=2, sticky="nsew", padx=(0, 6), pady=2)
    body.grid_columnconfigure(0, weight=1)

    rendered = SlotRow(frame=frame, slot_index=slot.index)

    if slot.is_lunch:
        _build_lunch_chip(body, row=0)
        return rendered

    inner = 0
    for block in grid_slot.starting:
        chip = _build_block_chip(
            body,
            block,
            items_by_id.get(block.item_id),
            inner,
            continued=False,
            chip_height=chip_height,
            title_width=title_width,
        )
        rendered.block_widgets.append((block, chip))
        inner += 1
    for block in grid_slot.continued:
        # Which continuation this is, so only the final box can claim the
        # spare minutes: they are a property of the last box, and a middle box
        # the task consumes whole has none.
        offset = grid_slot.slot.index - (block.slot_index or 0)
        last_box = offset >= slots_for_minutes(block.planned_minutes) - 1
        # Deliberately not added to block_widgets: a press here would start a
        # drag of a block whose home is another box, and a right-click would
        # offer to resize it from a box it does not start in. The box a block
        # starts in is the one that owns it.
        _build_block_chip(
            body,
            block,
            items_by_id.get(block.item_id),
            inner,
            continued=True,
            last_box=last_box,
            chip_height=chip_height,
            title_width=title_width,
        )
        inner += 1

    return rendered


def item_is_complete(item: Optional[ActionItem]) -> bool:
    """Whether this item has been marked completed.

    Purpose: PD-M6 -- one answer for the mark, rather than a status string
             compared four ways.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m6
    Tests:   tests/test_plan_screen.py::test_pdm61_a_completed_task_shows_a_check_left_of_the_time

    Case-folded and stripped: the column is user-editable through the item
    editor's own history and through older rows, and a mark that depends on
    the exact casing of a word is a mark that is silently wrong.
    """
    if item is None:
        return False
    return str(getattr(item, "status", "") or "").strip().lower() == Status.COMPLETED


def slot_is_complete(grid_slot, items_by_id: Dict[str, ActionItem]) -> bool:
    """Whether every task in this box is finished, and there is one.

    Purpose: PD-M6 -- the check sits beside the box's time, so it is the
             box's claim about itself.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m6
    Tests:   tests/test_plan_screen.py::test_pdm63_a_box_with_one_task_still_open_shows_no_check

    **All**, not any. A box holding a finished task beside an unfinished one
    reads as finished from the time column, which is the one place a reader
    is counting on the mark to be exact -- and a half hour with work left in
    it is not a half hour that is done.

    Padding is not work, so a break or a buffer can never carry the mark, and
    a box of nothing but padding is not a finished box. A block whose item has
    been deleted is unknown, not finished.
    """
    tasks = [
        block
        for block in list(grid_slot.starting) + list(grid_slot.continued)
        if BlockType.normalize(block.block_type) == BlockType.ITEM
    ]
    if not tasks:
        return False
    return all(item_is_complete(items_by_id.get(block.item_id)) for block in tasks)


def slot_is_padding(grid_slot) -> bool:
    """True when this box holds padding and nothing else.

    Purpose: PD-M4 -- break, buffer and lunch are one kind of thing, so they
             are drawn as one kind of thing.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m4
    Tests:   tests/test_plan_screen.py::test_pdm42_a_padding_box_is_drawn_like_the_lunch_box

    PD-M4 gave the three one stripe colour and stopped there, which left the
    row behind a break or a buffer drawn on the surface every task box uses
    while lunch had its own lighter one. On screen the stripes matched and the
    boxes did not, which is the comparison a user actually makes.

    An empty box is not padding: it is room, and it is drawn as room.
    """
    chips = list(grid_slot.starting) + list(grid_slot.continued)
    if not chips:
        return False
    return all(
        BlockType.normalize(block.block_type)
        in (BlockType.BUFFER, BlockType.BREAK)
        for block in chips
    )


def _build_lunch_chip(parent, row: int) -> ctk.CTkFrame:
    """The lunch box's own row: the padding stripe, and the word.

    Purpose: PD-M4 -- break, buffer and lunch are one colour.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m4
    Tests:   tests/test_plan_screen.py::test_pdm42_break_buffer_and_lunch_render_in_the_shared_colour

    A lunch half hour is a property of the day rather than a block, so it had
    no chip and therefore nowhere to carry a colour: the only thing it shaded
    was its own row fill, which is the surface every other box is drawn on.
    The stripe is the same width, the same corner radius and the same place as
    a break's and a buffer's, because the point of the shared colour is that
    the three read as one kind of thing.
    """
    chip = ctk.CTkFrame(parent, fg_color="transparent")
    chip.grid(row=row, column=0, sticky="ew", pady=1)
    chip.grid_columnconfigure(0, minsize=STRIPE_WIDTH_PX + 8)
    chip.grid_columnconfigure(1, weight=1)

    stripe = ctk.CTkFrame(
        chip,
        width=STRIPE_WIDTH_PX,
        height=STRIPE_MIN_HEIGHT_PX,
        fg_color=block_type_colors()["lunch"],
        corner_radius=3,
    )
    stripe.grid(row=0, column=0, sticky="ns", padx=(0, 8), pady=2)
    stripe.grid_propagate(False)

    # Body size and body colour, like a break's word and a buffer's. At the
    # theme's muted text on the surface a lunch box is drawn on, the word was
    # within a few values of its own background.
    ctk.CTkLabel(
        chip,
        text="Lunch",
        anchor="w",
        text_color=semantic_colors()["body_text"],
    ).grid(row=0, column=1, sticky="w", padx=(0, CHIP_RIGHT_INSET_PX))
    return chip


def _build_block_chip(
    parent,
    block: TimeBlock,
    item: Optional[ActionItem],
    row: int,
    *,
    continued: bool,
    last_box: bool = True,
    chip_height: int = SLOT_CHIP_HEIGHT_PX,
    title_width: int = SLOT_TITLE_WIDTH_PX,
) -> ctk.CTkFrame:
    """One task inside a box.

    ``continued`` marks the second and later boxes of a longer task: shown so
    the time is accounted for, greyed and without its controls so it is not
    mistaken for another task.
    """
    palette = semantic_colors()
    kind = BlockType.normalize(block.block_type)

    # PB-M4: the task carries its priority as shading, not only as the bar at
    # its edge. Padding has no priority to shade with, so it keeps the bare
    # surface and the theme's own text.
    #
    # PB-M7: a continuation is shaded too. It was left unfilled on the
    # argument that shading it would read as a second task of equal weight;
    # on screen the opposite happened -- a 90-minute task was one coloured box
    # followed by two empty ones, which reads as a task that stops. The arrow
    # is what says "the same task, continued", and it is enough to say it.
    if kind in (BlockType.BUFFER, BlockType.BREAK):
        fill = "transparent"
        body_text = palette["body_text"]
    else:
        fill = fill_for_item(item)
        body_text = pick_text_color(fill)

    chip = ctk.CTkFrame(
        parent, fg_color=fill, corner_radius=4, height=chip_height - 4
    )
    chip.grid(row=row, column=0, sticky="ew", pady=1)
    configure_chip_columns(chip, title_width)
    chip.grid_rowconfigure(0, weight=1)
    # No grid_propagate(False) here, deliberately. It would also hold the chip
    # to its height, but then neither it nor the stripe's height= could be
    # shown to matter: each alone keeps the title inside the box, so a test
    # can only fail when both are reverted, and a line no test can fail on is
    # a line nobody can safely change. The stripe's own height is the root
    # cause and is where the fix stays.

    stripe = ctk.CTkFrame(
        chip,
        width=STRIPE_WIDTH_PX,
        height=STRIPE_MIN_HEIGHT_PX,
        # PB-M7: the continuation's bar is the task's bar. A border-grey one
        # made the later half hours of a long task look like padding.
        fg_color=stripe_for_block(block, item),
        corner_radius=3,
    )
    stripe.grid(
        row=0, column=CHIP_STRIPE_COLUMN, sticky="ns", padx=(0, 8), pady=2
    )
    stripe.grid_propagate(False)

    title = _block_title(block, item)
    ctk.CTkLabel(
        chip,
        text=f"↳ {title}" if continued else title,
        anchor="w",
        justify="left",
        text_color=body_text,
    ).grid(row=0, column=CHIP_TITLE_COLUMN, sticky="ew")

    if continued:
        # The minutes this box gives the task that the task does not use. 45 in
        # two boxes ends at 09:45 and leaves 15 of the second box spare, and
        # the whole 45-vs-60 question is why this is written on screen rather
        # than rounded away.
        spare = spare_minutes_in_last_slot(block) if last_box else 0
        ctk.CTkLabel(
            chip,
            text=f"{spare}m spare" if spare else "same task",
            width=SLOT_LENGTH_WIDTH_PX,
            anchor="e",
            # PB-M7: chosen for the shade now behind it, like the title. The
            # theme's muted text is the right colour for the theme's surface
            # and the wrong one for a band tint.
            text_color=body_text,
        ).grid(
            row=0, column=CHIP_LENGTH_COLUMN, sticky="e",
            padx=(0, CHIP_RIGHT_INSET_PX),
        )
        return chip

    if kind == BlockType.ITEM:
        DepthBarStack(chip, item.depth if item else None).grid(
            row=0, column=CHIP_BARS_COLUMN, padx=(4, 6)
        )

    ctk.CTkLabel(
        chip,
        text=f"{block.planned_minutes}m",
        width=SLOT_LENGTH_WIDTH_PX,
        anchor="e",
        text_color=body_text,
    ).grid(
        row=0, column=CHIP_LENGTH_COLUMN, sticky="e",
        padx=(0, CHIP_RIGHT_INSET_PX),
    )

    return chip


#: PD-M5 — what the two always-drawn boxes at the ends of the day say.
PD_EARLIER_TEXT = "Earlier"
PD_LATER_TEXT = "Later"
PD_EARLIER_HINT = "drop an item here to start the day earlier"
PD_LATER_HINT = "drop an item here to end the day later"


def build_virtual_slot_row(
    parent,
    row: int,
    *,
    label: str,
    hint: str,
    chip_height: int = SLOT_CHIP_HEIGHT_PX,
) -> ctk.CTkFrame:
    """PD-M5 — the box above the day and the box below it.

    Purpose: "leave a virtual block for these two areas so there is something
             to drop into". A drop needs a rectangle; without one the gesture
             is aiming at the gap between the grid and the pane's edge.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m5
    Tests:   tests/test_plan_screen.py::test_pdm51_a_virtual_box_sits_at_each_end

    Drawn like a half hour and dimmed, in the same columns, so it reads as part
    of the day without claiming to be a half hour that exists: it carries a
    word where a box carries its clock time, because it has no clock time until
    the drop decides one. Transparent and 1px-bordered like an empty box, which
    is what it is a proposal for.
    """
    palette = semantic_colors()
    frame = ctk.CTkFrame(
        parent,
        fg_color="transparent",
        corner_radius=6,
        height=slot_row_height(1, chip_height),
        border_width=1,
        border_color=palette["border"],
    )
    frame.grid(row=row, column=0, sticky="ew", pady=1, padx=2)
    _configure_slot_columns(frame)
    frame.grid_propagate(False)

    ctk.CTkLabel(
        frame,
        text=label,
        width=SLOT_TIME_WIDTH_PX,
        anchor="w",
        text_color=palette["muted_text"],
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=1, sticky="nw", padx=(8, 4), pady=4)

    ctk.CTkLabel(
        frame,
        text=hint,
        anchor="w",
        justify="left",
        text_color=palette["muted_text"],
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=2, sticky="nw", padx=(0, 6), pady=4)

    return frame


def build_empty_day_note(parent, row: int) -> ctk.CTkLabel:
    """What the grid says when every box is empty.

    Its own function so the drop instructions live in one place, and so the
    note can be found by a test without matching on prose.
    """
    label = ctk.CTkLabel(
        parent,
        text=(
            "Nothing planned yet. Drag an item from the left onto the half "
            "hour you mean to work it."
        ),
        anchor="w",
        justify="left",
        text_color=semantic_colors()["muted_text"],
        font=ctk.CTkFont(size=11),
    )
    label.grid(row=row, column=0, sticky="ew", padx=10, pady=(2, 8))
    return label


def build_outside_group(
    parent,
    blocks: List[TimeBlock],
    items_by_id: Dict[str, ActionItem],
    row: int,
    *,
    chip_height: int = SLOT_CHIP_HEIGHT_PX,
    title_width: int = SLOT_TITLE_WIDTH_PX,
) -> List[Tuple[TimeBlock, ctk.CTkFrame]]:
    """Blocks no box can hold, drawn beneath the item list rather than dropped.

    Purpose: TG-M3 -- surface, never silently drop (P2).
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m3
    Tests:   tests/test_plan_screen.py::test_tgm31_an_outside_block_is_drawn
             tests/test_plan_screen.py::test_pbm55_an_outside_block_is_sized_like_one_in_a_box

    The two size settings are passed through for the same reason they reach a
    box: a row here sits directly beneath the item rows and across from the
    boxes, and a task that changes size depending on which of the three it is
    in reads as three different kinds of thing.

    A block gets here when Day End moved earlier than its box, when its length
    now runs past the last box, or when it has never been placed at all. The
    day it stops being drawn is the day the user loses planned work with
    nothing on screen to say so.
    """
    palette = semantic_colors()
    ctk.CTkLabel(
        parent,
        text=f"Outside the day ({len(blocks)}) — drag onto a box to place",
        anchor="w",
        text_color=palette["warning"],
        font=ctk.CTkFont(size=11, weight="bold"),
    ).grid(row=row, column=0, sticky="ew", padx=10, pady=(12, 2))

    widgets: List[Tuple[TimeBlock, ctk.CTkFrame]] = []
    for offset, block in enumerate(blocks, start=1):
        holder = ctk.CTkFrame(
            parent,
            fg_color=palette["surface_subtle"],
            corner_radius=6,
            height=chip_height,
            border_width=1,
            border_color=palette["warning"],
        )
        holder.grid(row=row + offset, column=0, sticky="ew", pady=1, padx=2)
        holder.grid_columnconfigure(0, minsize=120, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_propagate(False)
        _build_block_chip(
            holder,
            block,
            items_by_id.get(block.item_id),
            0,
            continued=False,
            chip_height=chip_height,
            title_width=title_width,
        )
        widgets.append((block, holder))
    return widgets
