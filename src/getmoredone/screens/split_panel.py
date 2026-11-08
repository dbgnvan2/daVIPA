"""One owner for the vertical divider between a screen's two panels.

Purpose: hold the split ratio, its clamp, its persistence and the four divider
         event handlers, so a two-panel screen keeps none of them.
Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m1--one-splitter-not-four
Tests:   tests/test_unified_panel_design.py::test_updm11_split_panel_module_owns_the_divider

Before this module the same 30 lines were written out four times, byte for
byte, in ``annual_vision_segments.py``, ``ape_assignment.py``,
``ape_period_view.py`` and ``weekly_items.py``. ``project_boards.py`` holds a
fifth, older copy with a different minimum and a different clamp; it is not a
VSP tab and is out of this spec's scope, recorded as an adjacent issue.

Two deliberate differences from the four copies it replaces:

- the ratio is saved and restored (UPD-D4), where every tab used to open at
  0.5 however the divider had been left;
- the right panel is held at its minimum too (UPD-M1.3, "at any body width").
  The four copies clamped only the left and gave the right whatever was left,
  which on a body under ``2 * MIN_PANEL_WIDTH`` is a right panel below the
  minimum, and under ``MIN_PANEL_WIDTH`` a negative grid minsize. Tk accepts
  that silently -- measured -- so nothing failed, which is why it survived
  four copies. ``project_boards.py``'s copy already holds both sides.

A screen builds its own body grid, its own panels and its own divider widget --
this class owns nothing of the layout. It needs the left panel only to measure
the width a drag starts from, which is what the four copies did.
"""

import logging

logger = logging.getLogger(__name__)

# The divider's own width in pixels. The screen uses it for the widget and for
# the grid column the widget sits in; this module is the only place it is set.
SPLITTER_WIDTH = 8

# Neither panel is allowed below this, however the divider is dragged.
MIN_PANEL_WIDTH = 420

# Where a screen with nothing saved opens.
DEFAULT_SPLIT_RATIO = 0.5


class SplitPanel:
    """The divider between ``left_column`` and ``right_column`` of ``body``.

    settings/prefix are optional: with both, the ratio is read at construction
    and written back on every drag release, under ``<prefix>_split_ratio``.
    Without them the ratio lives for as long as the screen does.
    """

    def __init__(
        self,
        body,
        left_panel,
        divider,
        settings=None,
        prefix=None,
        left_column=0,
        right_column=2,
        splitter_width=SPLITTER_WIDTH,
        min_panel_width=MIN_PANEL_WIDTH,
        on_apply=None,
    ):
        self.body = body
        self.left_panel = left_panel
        self.divider = divider
        self.settings = settings
        self.prefix = prefix
        self.left_column = left_column
        self.right_column = right_column
        self.splitter_width = splitter_width
        self.min_panel_width = min_panel_width
        # UPD-F4 — called with (left_px, right_px) every time the panels are
        # re-sized, so a screen can re-share each panel's width across that
        # panel's columns. The divider is the only thing that changes a
        # panel's width, so this is the only place that knows the new one.
        self.on_apply = on_apply
        self.ratio = self._load_ratio()
        self._drag_start_x = None
        self._drag_start_left = None

        divider.bind("<ButtonPress-1>", self.on_press)
        divider.bind("<B1-Motion>", self.on_drag)
        divider.bind("<ButtonRelease-1>", self.on_release)
        body.bind("<Configure>", self.on_body_resize)

    # ----------------------------------------------------------- persistence
    def setting_attr(self) -> str:
        """The ``AppSettings`` field this screen's ratio is stored in."""
        return f"{self.prefix}_split_ratio"

    def _load_ratio(self) -> float:
        if self.settings is None or not self.prefix:
            return DEFAULT_SPLIT_RATIO
        attr = self.setting_attr()
        if not hasattr(self.settings, attr):
            # ``AppSettings.save`` writes declared dataclass fields only, so a
            # prefix with no field would persist nothing and say nothing. Say
            # it here rather than let a tab quietly stop remembering (P2).
            logger.warning(
                "[split_panel] %s has no AppSettings field, so this divider "
                "will not be remembered; declare it in app_settings.py",
                attr,
            )
            return DEFAULT_SPLIT_RATIO
        raw = getattr(self.settings, attr, None)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return DEFAULT_SPLIT_RATIO
        if value != value or value <= 0.0 or value >= 1.0:
            # NaN, or a ratio that puts a panel off the edge. The pixel clamp
            # below would survive it, but a stored value this far out is a file
            # someone edited, not a drag, and 0.5 is the honest answer to it.
            return DEFAULT_SPLIT_RATIO
        return value

    def _persist(self) -> None:
        if self.settings is None or not self.prefix:
            return
        attr = self.setting_attr()
        if not hasattr(self.settings, attr):
            return
        setattr(self.settings, attr, self.ratio)
        self.settings.save()

    # ------------------------------------------------------------- the clamp
    def _usable_width(self) -> int:
        """Pixels the two panels share, or 0 when the body has no layout yet."""
        total = self.body.winfo_width() - self.splitter_width
        return total if total > 0 else 0

    def clamp_left(self, left: int, total: int) -> int:
        """``left`` held inside both minimums, at any body width.

        When the body is too narrow to give both panels their minimum, the
        minimum wins over the ratio and the right panel is the one that gives:
        ``max_left`` can be below ``min_panel_width`` only if ``total`` is, and
        the outer ``max`` then pins the left panel to its minimum.
        """
        max_left = max(self.min_panel_width, total - self.min_panel_width)
        return max(self.min_panel_width, min(max_left, int(left)))

    # ----------------------------------------------------------- the handlers
    def apply(self) -> None:
        """Push the current ratio into the body's two panel columns.

        Both panels are held at or above the minimum. Where the body cannot
        seat two minimums it overflows instead: a minimum that gives way under
        pressure is not a minimum, and a column is better clipped than crushed
        to nothing. Above ``2 * min_panel_width`` the two always sum to
        ``total`` exactly, which is the only width a user will ever see.
        """
        total = self._usable_width()
        if not total:
            return
        left = self.clamp_left(int(total * self.ratio), total)
        right = max(self.min_panel_width, total - left)
        self.body.grid_columnconfigure(self.left_column, minsize=left)
        self.body.grid_columnconfigure(self.right_column, minsize=right)
        if self.on_apply is not None:
            self.on_apply(left, right)

    def on_body_resize(self, _event=None) -> None:
        """Re-apply on resize, but never while a drag is setting the ratio."""
        if self._drag_start_x is None:
            self.apply()

    def on_press(self, event) -> None:
        self._drag_start_x = event.x_root
        self._drag_start_left = self.left_panel.winfo_width()

    def on_drag(self, event) -> None:
        if self._drag_start_x is None or self._drag_start_left is None:
            return
        total = self._usable_width()
        if not total:
            return
        left = self.clamp_left(
            self._drag_start_left + (event.x_root - self._drag_start_x), total
        )
        self.ratio = left / total
        self.apply()

    def on_release(self, _event=None) -> None:
        was_dragging = self._drag_start_x is not None
        self._drag_start_x = None
        self._drag_start_left = None
        if was_dragging:
            self._persist()
