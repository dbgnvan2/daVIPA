import tkinter as tk
from datetime import date, timedelta

import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.screens.drag_schedule_support import (
    color_for_day_stats,
    date_background_for,
    format_day_stats_text,
    future_options_for,
    interpolate_hex_color,
    normalized_date_text_color,
    widget_contains_pointer,
)


def test_normalized_date_text_color_normalizes_hash_and_fallback():
    assert normalized_date_text_color("ffffff") == "#ffffff"
    assert normalized_date_text_color("#ABCDEF") == "#ABCDEF"
    assert normalized_date_text_color("bad") == "#FFFFFF"


def test_format_day_stats_text_formats_hours_and_pluralization():
    assert format_day_stats_text(1, 75) == "1 item - 1h 15m"
    assert format_day_stats_text(3, 30) == "3 items - 0h 30m"


def test_interpolate_hex_color_midpoint():
    assert interpolate_hex_color("#000000", "#FFFFFF", 0.5) == "#808080"


def test_color_for_day_stats_progresses_beyond_green():
    low = color_for_day_stats(1, 30)
    high = color_for_day_stats(12, 360)

    assert low.startswith("#")
    assert high.startswith("#")
    assert low != high


def test_future_options_for_returns_sorted_dates():
    settings = AppSettings(
        mid_term_offset_days=30,
        long_term_offset_days=90,
        next_month_offset_days=0,
        next_quarter_offset_days=0,
    )
    options = future_options_for(date(2026, 3, 19), settings)

    assert len(options) == 4
    assert [label for label, *_rest in options] == [label for label, *_rest in sorted(options, key=lambda item: item[1])]


def test_date_background_for_tracks_past_present_future():
    today = date.today()
    assert date_background_for((today - timedelta(days=1)).isoformat()).startswith("#")
    assert date_background_for(today.isoformat()).startswith("#")
    assert date_background_for((today + timedelta(days=1)).isoformat()).startswith("#")


# --- widget_contains_pointer ------------------------------------------------
#
# The drop-target hit test, extracted so the Plan screen's two drag surfaces
# and drag_schedule.py's four call sites share one copy. Its docstring named
# the first of these tests before the test existed; the pre-push sweep caught
# the claim, and these are the tests it was claiming.


class _FakeWidget:
    """The four geometry calls widget_contains_pointer makes, and nothing else.

    A fake rather than a real widget because the arithmetic needs no display,
    and because a *destroyed* widget cannot be built on purpose -- it can only
    be built by raising what Tk raises.
    """

    def __init__(self, *, rootx, rooty, width, height, mapped=True, raises=None):
        self._rootx = rootx
        self._rooty = rooty
        self._width = width
        self._height = height
        self._mapped = mapped
        self._raises = raises

    def winfo_ismapped(self):
        if self._raises == "ismapped":
            raise tk.TclError("bad window path name")
        return self._mapped

    def winfo_rootx(self):
        if self._raises == "geometry":
            raise tk.TclError("bad window path name")
        return self._rootx

    def winfo_rooty(self):
        return self._rooty

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height


def test_widget_contains_pointer_uses_root_coordinates():
    """The point is in screen coordinates, not the widget's own.

    This is the distinction the function exists to get right, and the one the
    four hand-written copies it replaced were most at risk of getting wrong: a
    widget 500px from the left edge of the screen does not contain the point
    x=10 just because it is 600px wide.
    """
    widget = _FakeWidget(rootx=500, rooty=300, width=600, height=200)

    assert widget_contains_pointer(widget, 510, 310) is True
    assert widget_contains_pointer(widget, 10, 310) is False
    assert widget_contains_pointer(widget, 510, 10) is False


@pytest.mark.parametrize(
    "x_root,y_root,expected",
    [
        (100, 100, True),   # top-left corner, inclusive
        (300, 250, True),   # bottom-right corner, inclusive
        (200, 175, True),   # the middle
        (99, 175, False),   # one pixel left
        (301, 175, False),  # one pixel right
        (200, 99, False),   # one pixel above
        (200, 251, False),  # one pixel below
    ],
)
def test_widget_contains_pointer_edges(x_root, y_root, expected):
    """The rectangle is closed on all four sides.

    Stated as a test because a drop released exactly on a border has to land
    somewhere, and "somewhere" has to be the same side every time.
    """
    widget = _FakeWidget(rootx=100, rooty=100, width=200, height=150)

    assert widget_contains_pointer(widget, x_root, y_root) is expected


def test_an_unmapped_widget_is_never_a_drop_target():
    """A widget that is not on screen cannot be dropped on.

    Without this an unmapped frame still reports a rectangle -- often 1x1 at
    the top-left -- so a drop near the corner of the screen would land on a
    target the user cannot see.
    """
    widget = _FakeWidget(rootx=100, rooty=100, width=200, height=150, mapped=False)

    assert widget_contains_pointer(widget, 150, 150) is False


@pytest.mark.parametrize("raises", ["ismapped", "geometry"])
def test_a_destroyed_widget_is_not_a_drop_target(raises):
    """A drag that outlives a refresh holds references Tk has thrown away.

    Both calls are inside the try for a reason: whichever one the destroyed
    widget is asked first is the one that raises.
    """
    widget = _FakeWidget(
        rootx=100, rooty=100, width=200, height=150, raises=raises
    )

    assert widget_contains_pointer(widget, 150, 150) is False


def test_a_widget_in_a_withdrawn_window_is_not_a_drop_target():
    """The same claim as the fake, made against real Tk.

    The fake asserts what the function does with a False from
    ``winfo_ismapped``; this asserts that real Tk says False for a child of a
    window that is not on screen, which is the fact the fake is standing in
    for. Needs a Tk root but not a mapped one, so it does not ask for the
    ``mapped_windows`` fixture.
    """
    root = tk.Tk()
    root.withdraw()
    try:
        frame = tk.Frame(root, width=200, height=150)
        frame.place(x=0, y=0)
        root.update_idletasks()

        assert frame.winfo_ismapped() == 0, "a withdrawn window's children are unmapped"
        assert widget_contains_pointer(frame, frame.winfo_rootx() + 5,
                                      frame.winfo_rooty() + 5) is False
    finally:
        root.destroy()
