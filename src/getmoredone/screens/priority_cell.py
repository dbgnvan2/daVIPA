"""The Priority cell and critical factor chip, drawn with an edge.

Purpose: PCC-A3 -- a level colour is pale (Any Critical ``#DCFCE7``), and on a
         completed row's ``success_tint`` it measured 1.02:1: the cell drew and
         could not be seen. ``CTkLabel`` takes no border, so a filled cell is a
         bordered frame holding the label, inset 2px so the border is not drawn
         beneath it (the failure in PBG-A7). The border is the cell's own
         derived text colour, so the colours the user chose are unchanged.
Spec:    docs/unused-docs/changes/2026-11-12-pcc-a3-cell-edge.md
Tests:   tests/test_priority_level_colors.py::test_pcca3_a_filled_cell_has_an_edge_on_every_row_surface
"""
from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

import customtkinter as ctk

CELL_INSET_PX = 2
CELL_CORNER_RADIUS = 6
CELL_HEIGHT_PX = 28


def build_level_cell(
    master: Any,
    cell: Any,
    text: str,
    width: int,
    row_text: str,
    font: Any,
    on_click: Optional[Callable[[Any], None]] = None,
    **label_kwargs: Any,
) -> Tuple[Any, ctk.CTkLabel]:
    """Return ``(widget to grid, label)`` for one level-coloured cell.

    A cell with no fill is a bare label in the row's text colour, as before.
    A filled one is a frame of the same outer size. ``on_click`` is bound to
    both, so the whole cell stays clickable.
    """
    if not cell.fill:
        label = ctk.CTkLabel(
            master, text=text, width=width, fg_color="transparent",
            text_color=row_text, corner_radius=0, font=font, **label_kwargs,
        )
        widgets = (label,)
        outer = label
    else:
        outer = ctk.CTkFrame(
            master,
            width=width,
            height=CELL_HEIGHT_PX,
            fg_color=cell.fill,
            border_width=1,
            border_color=cell.text_color,
            corner_radius=CELL_CORNER_RADIUS,
        )
        label = ctk.CTkLabel(
            outer,
            text=text,
            width=width - 2 * CELL_INSET_PX,
            height=CELL_HEIGHT_PX - 2 * CELL_INSET_PX,
            fg_color=cell.fill,
            text_color=cell.text_color,
            corner_radius=0,
            font=font,
            **label_kwargs,
        )
        label.grid(row=0, column=0, padx=CELL_INSET_PX, pady=CELL_INSET_PX)
        widgets = (outer, label)
    if on_click is not None:
        for widget in widgets:
            widget.bind("<Button-1>", on_click)
    return outer, label
