"""One owner for dragging a row from a screen's left panel to its right.

Purpose: bind a row's widgets as a drag source, test the drop on release, and
         hand the dropped row back to the screen.
Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m2--one-row-drag-not-four
Tests:   tests/test_unified_panel_design.py::test_updm21_every_widget_in_the_row_is_a_drag_handle

Before this module `_bind_drag_widgets`, `_start_row_drag`, `_finish_row_drag`
and `_is_descendant` appeared in `annual_vision_segments.py`,
`ape_assignment.py`, `ape_period_view.py` and `weekly_items.py`. The first two
and the last are byte-identical across all four, measured before anything was
removed; `_finish_row_drag` differs only in the body of its final `if`, which
is the screen's own assignment logic and stays in the screen as `on_drop`.

**The release is bound on the toplevel, not on the row.** A pointer that
leaves the row still has to be heard from, and the drop target is somewhere
else entirely. One consequence worth knowing: a plain `bind` replaces the
toplevel's handler for that sequence rather than adding to it, so there is one
drag slot per window. That is right for one mouse, and it is why
`finish` can `unbind` the sequence outright.

Nothing here draws the row being dragged. There is no ghost, no highlight and
no motion handler: press, then release over the target. That is what the four
copies did, and UPD-M2 is a consolidation, not a redesign.
"""


def is_descendant(widget, ancestor) -> bool:
    """True when `ancestor` is `widget` itself or any of its masters.

    Walks `.master` with `getattr`, so it is safe on the `None` that
    `winfo_containing` returns when the pointer is outside every widget.
    """
    current = widget
    while current is not None:
        if current == ancestor:
            return True
        current = getattr(current, "master", None)
    return False


class RowDragSource:
    """A left panel's rows, draggable onto one drop target.

    screen:      the widget the pointer and toplevel are read from.
    drop_target: the widget a release must land inside for the drop to count.
    on_drop:     called with the dragged row, once, only on a release inside
                 the target. Everything the screen does with that row -- the
                 assignment, the refresh, the status line -- belongs there.
    """

    def __init__(self, screen, drop_target, on_drop):
        self.screen = screen
        self.drop_target = drop_target
        self.on_drop = on_drop
        self.dragged_row = None

    def bind_row(self, widgets, row) -> None:
        """Make every widget in the row a handle for dragging that row.

        Every cell, not just the frame: a row whose only handle is the gap
        between its labels is a row that looks draggable and is not.
        """
        for widget in widgets:
            # `r=row` is carried over from the four copies and is not
            # load-bearing: the loop is over the widgets, and `row` is this
            # call's own parameter, so each call already closes over its own
            # row. Measured by mutation — removing the default leaves
            # test_updm21 green. Kept because it costs nothing and says the
            # intent out loud; no test asserts it, and none can.
            widget.bind("<ButtonPress-1>", lambda _event, r=row: self.start(r))

    def start(self, row) -> None:
        self.dragged_row = row
        self.screen.winfo_toplevel().bind("<ButtonRelease-1>", self.finish)

    def finish(self, _event=None) -> None:
        """Resolve a release: a drop inside the target, or nothing at all.

        A release with no drag in progress does nothing -- the input that
        looks like a drop and is not (P7). The binding is dropped first, so
        that holds however this was reached.
        """
        self.screen.winfo_toplevel().unbind("<ButtonRelease-1>")
        if not self.dragged_row:
            return
        pointer_x, pointer_y = self.screen.winfo_pointerxy()
        target = self.screen.winfo_containing(pointer_x, pointer_y)
        row = self.dragged_row
        self.dragged_row = None
        if is_descendant(target, self.drop_target):
            self.on_drop(row)
