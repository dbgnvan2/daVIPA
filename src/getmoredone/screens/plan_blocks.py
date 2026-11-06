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

from typing import Optional

import customtkinter as ctk

from ..models import ActionItem, BlockType, TimeBlock
from ..theme import (
    block_type_colors,
    depth_bar_colors,
    priority_band_colors,
    semantic_colors,
)
from ..time_block_layout import MAX_DEPTH_BARS, block_height, depth_bars, priority_band

# The coloured edge that carries the priority band. Narrow on purpose: the
# project's theme rule allows a DB/semantic colour as a chip or stripe accent
# and not as a full-row fill, because a wall of saturated rows stops carrying
# information and starts fighting the text on top of it.
STRIPE_WIDTH_PX = 6


def accent_for_item(item: Optional[ActionItem]) -> str:
    """The band colour for the item behind a block, or the unscored grey."""
    bands = priority_band_colors()
    if item is None:
        return bands["unscored"]
    return bands[priority_band(getattr(item, "priority_score", 0))]


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
    palette = semantic_colors()
    frame = ctk.CTkFrame(parent, fg_color=palette["surface_subtle"], corner_radius=6)
    frame.grid(row=row, column=0, sticky="ew", pady=3, padx=2)
    frame.grid_columnconfigure(1, weight=1)

    stripe = ctk.CTkFrame(
        frame,
        width=STRIPE_WIDTH_PX,
        fg_color=accent_for_item(item),
        corner_radius=3,
    )
    stripe.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(4, 8), pady=4)
    stripe.grid_propagate(False)

    title = ctk.CTkLabel(frame, text=item.title, anchor="w", justify="left")
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
        text_color=palette["muted_text"],
        font=ctk.CTkFont(size=11),
    )
    subtitle.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(0, 5))

    bars = DepthBarStack(frame, item.depth)
    bars.grid(row=0, column=2, rowspan=2, padx=(4, 10), pady=6)

    return frame


def build_block_row(
    parent,
    block: TimeBlock,
    item: Optional[ActionItem],
    row: int,
    overflows_day_end: bool,
) -> ctk.CTkFrame:
    """One time block in the day column.

    The frame's height tracks ``planned_minutes``, so a 90 reads as three times
    a 30 without the user reading either number.
    """
    palette = semantic_colors()
    kind = BlockType.normalize(block.block_type)

    frame = ctk.CTkFrame(
        parent,
        fg_color=palette["surface_subtle"],
        corner_radius=6,
        height=block_height(block.planned_minutes),
        border_width=2 if overflows_day_end else 0,
        border_color=palette["warning"],
    )
    frame.grid(row=row, column=0, sticky="ew", pady=2, padx=2)
    frame.grid_columnconfigure(2, weight=1)
    # Without this the frame shrinks to fit its children and the height -- the
    # one thing carrying the block's length -- is thrown away.
    frame.grid_propagate(False)

    stripe = ctk.CTkFrame(
        frame,
        width=STRIPE_WIDTH_PX,
        fg_color=accent_for_block(block, item),
        corner_radius=3,
    )
    stripe.grid(row=0, column=0, sticky="ns", padx=(4, 8), pady=4)
    stripe.grid_propagate(False)

    ctk.CTkLabel(
        frame,
        text=f"{block.start_time}–{block.end_time}",
        width=100,
        anchor="w",
        text_color=palette["time_text"],
    ).grid(row=0, column=1, sticky="w", padx=(0, 6))

    ctk.CTkLabel(
        frame,
        text=_block_title(block, item),
        anchor="w",
        justify="left",
    ).grid(row=0, column=2, sticky="ew", padx=(0, 6))

    if kind == BlockType.ITEM:
        DepthBarStack(frame, item.depth if item else None).grid(
            row=0, column=3, padx=(4, 6)
        )

    ctk.CTkLabel(
        frame,
        text=f"{block.planned_minutes}m",
        width=48,
        anchor="e",
        text_color=palette["muted_text"],
    ).grid(row=0, column=4, padx=(0, 6))

    if overflows_day_end:
        # Shown, not refused: over-filling a day is the user's business, and
        # the planner's job is to say so rather than drop the block (P2).
        ctk.CTkLabel(
            frame,
            text="past day end",
            text_color=palette["warning"],
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=5, padx=(0, 10))

    return frame


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


def build_lunch_band(parent, row: int, start: str, end: str) -> ctk.CTkFrame:
    """The lunch gap, drawn where blocks were pushed past it.

    Not a block: it is not stored, cannot be dragged, resized or deleted, and
    exists only so the hour the day skips is visible rather than an unexplained
    jump in the times.
    """
    palette = semantic_colors()
    frame = ctk.CTkFrame(parent, fg_color="transparent", height=26)
    frame.grid(row=row, column=0, sticky="ew", pady=2, padx=2)
    frame.grid_columnconfigure(2, weight=1)
    frame.grid_propagate(False)

    stripe = ctk.CTkFrame(
        frame, width=STRIPE_WIDTH_PX, fg_color=block_type_colors()["lunch"], corner_radius=3
    )
    stripe.grid(row=0, column=0, sticky="ns", padx=(4, 8), pady=4)
    stripe.grid_propagate(False)

    ctk.CTkLabel(
        frame, text=f"{start}–{end}", width=100, anchor="w",
        text_color=palette["muted_text"],
    ).grid(row=0, column=1, sticky="w", padx=(0, 6))
    ctk.CTkLabel(
        frame, text="Lunch", anchor="w", text_color=palette["muted_text"],
    ).grid(row=0, column=2, sticky="ew")

    return frame
