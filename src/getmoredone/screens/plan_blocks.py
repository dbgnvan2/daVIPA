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
from ..models import ActionItem, BlockType, TimeBlock
from ..theme import (
    block_type_colors,
    depth_bar_colors,
    priority_band_colors,
    priority_fill_colors,
    priority_stripe_colors,
    semantic_colors,
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


def build_item_row(
    parent,
    item: ActionItem,
    row: int,
    already_blocked: bool,
    work_block_minutes: int,
) -> ctk.CTkFrame:
    """One action item in the left pane, ready to be dragged onto the day.

    Returns the frame, so the caller can bind the drag handlers to it and to
    its children -- a press that lands on a label must start the same drag as
    one that lands on the frame, or half the row is dead to the mouse.
    """
    fill = fill_for_item(item)
    on_fill = pick_text_color(fill)
    frame = ctk.CTkFrame(parent, fg_color=fill, corner_radius=6)
    frame.grid(row=row, column=0, sticky="ew", pady=3, padx=2)
    frame.grid_columnconfigure(1, weight=1)

    stripe = ctk.CTkFrame(
        frame,
        width=STRIPE_WIDTH_PX,
        height=STRIPE_MIN_HEIGHT_PX,
        fg_color=stripe_for_item(item),
        corner_radius=3,
    )
    stripe.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(4, 8), pady=4)
    stripe.grid_propagate(False)

    title = ctk.CTkLabel(
        frame, text=item.title, anchor="w", justify="left", text_color=on_fill
    )
    title.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(5, 0))

    # The scheduling facts, in the words the item editor uses for them.
    details = [f"P {item.priority_score}"]
    if item.work_block:
        details.append(f"Work Block {work_block_minutes}m")
    else:
        details.append(f"{work_block_minutes}m")
    if item.depth:
        details.append(item.depth)
    if already_blocked:
        # Marked, not hidden: an item can genuinely need two blocks in a day,
        # and removing it from the list would look like it had vanished.
        details.append("already blocked")

    subtitle = ctk.CTkLabel(
        frame,
        text="  ·  ".join(details),
        anchor="w",
        text_color=on_fill,
        font=ctk.CTkFont(size=11),
    )
    subtitle.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(0, 5))

    bars = DepthBarStack(frame, item.depth)
    bars.grid(row=0, column=2, rowspan=2, padx=(4, 10), pady=6)

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

#: Height of one task chip, and so what each task adds to a box's height.
#: The fallback only: PB-M5 takes the live value from
#: ``AppSettings.drag_schedule_box_height_px``, and this is what a missing or
#: unusable setting resolves to.
SLOT_CHIP_HEIGHT_PX = 30

#: What the chip's title column asks for. Fallback for
#: ``AppSettings.drag_schedule_title_col_width``, the same way.
SLOT_TITLE_WIDTH_PX = 80


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
    frame.grid_columnconfigure(0, minsize=SLOT_TIME_WIDTH_PX)
    frame.grid_columnconfigure(1, minsize=120, weight=1)
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

    if slot.is_lunch:
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

    ctk.CTkLabel(
        frame,
        text=slot.start_time,
        width=SLOT_TIME_WIDTH_PX,
        anchor="w",
        text_color=palette["time_text"],
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=0, sticky="nw", padx=(8, 4), pady=4)

    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=2)
    body.grid_columnconfigure(0, weight=1)

    rendered = SlotRow(frame=frame, slot_index=slot.index)

    if slot.is_lunch:
        ctk.CTkLabel(
            body,
            text="Lunch",
            anchor="w",
            text_color=palette["muted_text"],
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, sticky="w")
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
    # its edge. A continuation is left unfilled on purpose -- it is the same
    # task seen again, and shading it would read as a second task of equal
    # weight. Padding has no priority to shade with.
    if continued or kind in (BlockType.BUFFER, BlockType.BREAK):
        fill = "transparent"
        body_text = palette["muted_text"] if continued else palette["body_text"]
    else:
        fill = fill_for_item(item)
        body_text = pick_text_color(fill)

    chip = ctk.CTkFrame(
        parent, fg_color=fill, corner_radius=4, height=chip_height - 4
    )
    chip.grid(row=row, column=0, sticky="ew", pady=1)
    chip.grid_columnconfigure(0, minsize=STRIPE_WIDTH_PX + 8)
    chip.grid_columnconfigure(1, minsize=title_width, weight=1)
    chip.grid_columnconfigure(2, minsize=22)
    chip.grid_columnconfigure(3, minsize=48)
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
        fg_color=palette["border"] if continued else stripe_for_block(block, item),
        corner_radius=3,
    )
    stripe.grid(row=0, column=0, sticky="ns", padx=(0, 8), pady=2)
    stripe.grid_propagate(False)

    title = _block_title(block, item)
    ctk.CTkLabel(
        chip,
        text=f"↳ {title}" if continued else title,
        anchor="w",
        justify="left",
        text_color=body_text,
    ).grid(row=0, column=1, sticky="ew")

    if continued:
        # The minutes this box gives the task that the task does not use. 45 in
        # two boxes ends at 09:45 and leaves 15 of the second box spare, and
        # the whole 45-vs-60 question is why this is written on screen rather
        # than rounded away.
        spare = spare_minutes_in_last_slot(block) if last_box else 0
        ctk.CTkLabel(
            chip,
            text=f"{spare}m spare" if spare else "same task",
            width=48,
            anchor="e",
            text_color=palette["muted_text"],
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=3, sticky="e")
        return chip

    if kind == BlockType.ITEM:
        DepthBarStack(chip, item.depth if item else None).grid(
            row=0, column=2, padx=(4, 6)
        )

    ctk.CTkLabel(
        chip,
        text=f"{block.planned_minutes}m",
        width=48,
        anchor="e",
        text_color=body_text,
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=3, sticky="e")

    return chip


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
) -> List[Tuple[TimeBlock, ctk.CTkFrame]]:
    """Blocks no box can hold, drawn under the grid rather than dropped.

    Purpose: TG-M3 -- surface, never silently drop (P2).
    Spec:    docs/implementation_plan_2026-11-05_time_grid.md#tg-m3
    Tests:   tests/test_plan_screen.py::test_tgm31_an_outside_block_is_drawn

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
            height=SLOT_CHIP_HEIGHT_PX,
            border_width=1,
            border_color=palette["warning"],
        )
        holder.grid(row=row + offset, column=0, sticky="ew", pady=1, padx=2)
        holder.grid_columnconfigure(0, minsize=120, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_propagate(False)
        _build_block_chip(
            holder, block, items_by_id.get(block.item_id), 0, continued=False
        )
        widgets.append((block, holder))
    return widgets
