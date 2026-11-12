"""Which priority *level* an action item is in, and what colour that level draws.

Purpose: one place decides the three priority levels and the colour each one
         draws, so the five list screens cannot drift apart and the user can
         recolour them from Settings. Since PCC-M1 (2026-11-11) that colour
         is the Priority cell's background, not a row tint.
Spec:    docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m1
Tests:   tests/test_priority_level_colors.py

A **level** is a rule on the two factors the user sets by hand, importance and
urgency. There are three, and they are the three the user named:

    Any Critical · Any High, but no Critical · No high or critical

A level is **not** a priority *band*. A band is a threshold on
``priority_score``, which is the *product* of all four factors
(``time_block_layout.PRIORITY_BANDS``); it has five names of its own and, until
PBG-M5 (2026-11-12), three colour tables in ``theme.py``. Since then the level
is the only priority anything is drawn in. The band named "critical" and the
level named "Any Critical" are different questions about the same item, and
the answers come apart: a Medium / Medium / XL / XL item scores 400, which is
the ``high`` band, while having no high or critical factor at all. That is why
this module carries its own names rather than reusing the band ones, and why
``test_plcm14_a_big_score_is_not_a_critical_level`` exists.

Two deliberate choices in ``priority_level``:

* **Thresholds come from ``PriorityFactors``**, never from a literal 20 or 10,
  so renumbering the scale moves the levels with it. Each factor is compared
  against its own scale -- ``IMPORTANCE`` for importance, ``URGENCY`` for
  urgency -- because the two dicts holding identical values today is a fact
  about this build, not a rule.
* **A missing factor is not an excuse.** Importance ``None`` with urgency
  ``Critical`` is Any Critical. This preserves the ``or`` the five list screens
  have always used, and it is the opposite of the band arithmetic, where one
  missing factor makes the whole item ``unscored``. The two are answering
  different questions: a band asks how big the score is, which a missing factor
  makes unanswerable, and a level asks whether the user marked either factor
  critical, which it does not.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .color_contrast import normalize_hex_color, pick_text_color
from .models import PriorityFactors

logger = logging.getLogger(__name__)


LEVEL_ANY_CRITICAL = "any_critical"
LEVEL_ANY_HIGH = "any_high"
LEVEL_NO_HIGH_OR_CRITICAL = "no_high_or_critical"

#: The three levels, most severe first. Everything that loops over the levels
#: loops over this, so a level cannot be left out of the Settings tab or the
#: defaults table without a test failing.
LEVEL_KEYS: Tuple[str, ...] = (
    LEVEL_ANY_CRITICAL,
    LEVEL_ANY_HIGH,
    LEVEL_NO_HIGH_OR_CRITICAL,
)

#: What the user sees. Their own words for the three levels, kept verbatim.
LEVEL_LABELS: Dict[str, str] = {
    LEVEL_ANY_CRITICAL: "Any Critical",
    LEVEL_ANY_HIGH: "Any High, but no Critical",
    LEVEL_NO_HIGH_OR_CRITICAL: "No high or critical",
}

#: ``AppSettings`` holds one colour field per level, named with this prefix.
SETTINGS_FIELD_PREFIX = "priority_level_color_"

# Where a fill came from. Kept for ``row_control_kwargs``, which asks whether a
# fill brought its own text colour; no screen reads it directly. Since PCC-M1 a
# *row* fill is never ``SOURCE_LEVEL`` -- only a Priority cell's is.
SOURCE_SEGMENT = "segment"
SOURCE_COMPLETED = "completed"
SOURCE_LEVEL = "level"
SOURCE_NONE = "none"

#: "No fill" -- the row keeps whatever background the theme gives it. Stored as
#: an empty string rather than ``None`` so that it survives a JSON round trip
#: as itself and not as a missing key (PLC-M2.6).
NO_FILL = ""


def settings_field_name(level: str) -> str:
    """The ``AppSettings`` field holding this level's colour."""
    return f"{SETTINGS_FIELD_PREFIX}{level}"


def _at_least(value: Any, scale: Mapping[str, int], name: str) -> bool:
    """Is ``value`` at or above the ``name`` step of ``scale``?

    ``>=`` and not ``==`` so a value off the scale -- a hand-edited database,
    or a scale that gains a step -- lands in the nearest level down instead of
    falling through to "no high or critical", which would quietly under-report
    an item's priority. A missing or non-numeric factor is simply not at that
    step; it is never an error here, because five list screens render whatever
    the database holds.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False
    return number >= scale[name]


def priority_level(importance: Optional[int], urgency: Optional[int]) -> str:
    """Which of the three levels these two factors put an item in."""
    if (
        _at_least(importance, PriorityFactors.IMPORTANCE, "Critical")
        or _at_least(urgency, PriorityFactors.URGENCY, "Critical")
    ):
        return LEVEL_ANY_CRITICAL
    if (
        _at_least(importance, PriorityFactors.IMPORTANCE, "High")
        or _at_least(urgency, PriorityFactors.URGENCY, "High")
    ):
        return LEVEL_ANY_HIGH
    return LEVEL_NO_HIGH_OR_CRITICAL


def priority_level_for_item(item: Any) -> str:
    """``priority_level`` for an object with ``importance`` and ``urgency``."""
    return priority_level(
        getattr(item, "importance", None), getattr(item, "urgency", None)
    )


#: The two factors a priority *level* is a rule on, under the one-letter labels
#: the list screens draw them with in the expandable I/U/E/V factor row. ``E``
#: and ``V`` are Size and Value: they are in the priority *score*, and in no
#: level, so they are deliberately absent and a lookup for them misses.
#:
#: Each label maps to its own scale rather than to one shared dict, because the
#: two holding identical values today is a fact about this build and not a rule
#: -- the same reason ``priority_level`` compares each factor against its own.
LEVEL_FACTOR_SCALES: Dict[str, Mapping[str, int]] = {
    "I": PriorityFactors.IMPORTANCE,
    "U": PriorityFactors.URGENCY,
}


def is_critical_factor(label: str, value: Any) -> bool:
    """Is the single factor drawn under ``label`` at its own Critical step?

    Purpose: LRR-M1.2 -- the four list screens painted one factor chip red on
             ``label in ("I", "U") and str(value).strip() == "20"``, which is
             the question ``priority_level`` answers for the pair, asked badly
             for one. It read an importance of ``25`` as not critical while the
             row's own ``P:`` badge read it as critical, and it held urgency to
             importance's threshold.
    Tests:   tests/test_priority_level_colors.py::test_lrr_cold_the_factor_chips_ask_the_authority_too

    A label that is not a level factor is simply not critical, rather than an
    error: the screens loop over all four chips and ask about each.
    """
    scale = LEVEL_FACTOR_SCALES.get(label)
    return scale is not None and _at_least(value, scale, "Critical")


def level_color(settings: Any, level: str) -> str:
    """This level's colour: the user's if it is usable, else the theme default.

    Returns ``NO_FILL`` (an empty string) when the level is set to no fill.

    ``theme`` is imported inside the function on purpose. It pulls in
    customtkinter, and this module is reachable from ``AppSettings``-shaped code
    that must not require a GUI toolkit -- the same reason, and the same
    treatment, as ``AppSettings._normalize_theme_name``.
    """
    from .theme import priority_level_fill_colors

    default = priority_level_fill_colors().get(level, NO_FILL)
    raw = getattr(settings, settings_field_name(level), default)

    # Blank is a decision, not a missing value: the user cleared the field and
    # wants no fill. It must not be "helpfully" replaced with the default,
    # or a level could never be turned off (PLC-M2.6).
    if isinstance(raw, str) and not raw.strip():
        return NO_FILL

    normalized = normalize_hex_color(raw)
    if normalized is None:
        logger.warning(
            "Ignoring unusable colour %r for priority level %r; using %r. "
            "Set it again in Settings > Priority Colours.",
            raw,
            level,
            default or "no fill",
        )
        return default
    return normalized


#: Segment colours already warned about, so a list of 300 rows logs once per
#: bad value rather than 300 times. Unbounded in principle and bounded in
#: practice by the number of segments a user has; it holds the value, not the
#: row, so a redraw after the colour is corrected warns again if it is still
#: wrong.
_warned_segment_colors: set = set()


def _warn_unreadable_segment_color(value: Any) -> None:
    """Log a segment colour that cannot be drawn, once per value."""
    key = repr(value)
    if key in _warned_segment_colors:
        return
    _warned_segment_colors.add(key)
    logger.warning(
        "Segment colour %r is not a #RRGGBB value, so rows in that segment "
        "are drawn with no fill rather than risking a Tk error. Set it again "
        "in Vision Planning > Vision Elements.",
        value,
    )


def row_control_kwargs(fill: "RowFill") -> Dict[str, str]:
    """Widget options that keep a row's controls legible on its fill.

    Purpose: PLC-M4.9 -- a row fill with no light/dark branch is a *light*
             colour in dark mode, while a row's checkbox and drag grip take
             their colours from the theme: light-on-light, with the checkbox
             border at about 2.6:1, under the 3:1 bar for a non-text control.
             PLC-M4.4 fixed the row text and left the controls behind.
             The motivating case was a priority-level fill; since PCC-M1 the
             only row fill that derives a text colour is a VSP segment's, and
             that is the live case this serves.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m4
    Tests:   tests/test_priority_level_colors.py::test_lrr_cold_a_segment_fill_carries_its_controls_too,
             ::test_plc_cold_the_three_screens_with_row_controls_pass_the_kwargs

    The condition is "this fill brought a text colour with it", and nothing
    narrower. It used to also require ``source == SOURCE_LEVEL``, which was the
    same question while a level fill was the only source that derived one;
    LRR-M2.1 made a segment fill derive one too and left that test behind,
    so on the three screens that fill a row from its segment the row text moved
    and the checkbox did not (found by a cold pass, 2026-11-10).

    Empty for a fill with no text colour of its own -- the completed tint, no
    fill, and a segment colour too malformed to derive one from -- so those
    rows keep the theme's controls exactly as before. ``text_color`` already
    clears 4.5:1 against the fill (PLC-M4.4), so a control drawn in it clears
    the 3:1 non-text bar by construction, and a checkmark drawn in the fill
    itself sits inside a box of that same colour.
    """
    if not fill.text_color or not fill.fill:
        return {}
    return {
        "border_color": fill.text_color,
        "fg_color": fill.text_color,
        "checkmark_color": fill.fill,
    }


def priority_color_rows(settings: Any) -> List[Tuple[str, str, str]]:
    """``(level, label, colour)`` for the Settings tab, one per level, in order.

    Purpose: PLC-M3.1 -- the content of the Settings section, without a Tk root,
             so what the section shows can be tested without building it.
    Tests:   tests/test_priority_level_colors.py::test_plcm31_one_row_per_level_in_order
    """
    return [
        (level, LEVEL_LABELS[level], level_color(settings, level))
        for level in LEVEL_KEYS
    ]


@dataclass(frozen=True)
class RowFill:
    """What colour a list row is drawn in, and why.

    ``fill`` is ``None`` for no fill -- that is what CustomTkinter's
    ``fg_color`` wants for "inherit", and it is not the empty string, which Tk
    rejects.

    ``text_color`` is ``None`` for the ``completed`` and ``none`` sources, and
    means "leave the screen's own ``row_text`` alone". A ``level`` or
    ``segment`` fill carries one, because both are colours the user chose with
    no theme behind them: a pale green row in the dark theme needs dark text,
    and the theme's ``row_text`` there is near-white. A segment colour
    ``normalize_hex_color`` cannot read is the one exception: it yields no
    fill and no text colour at all, so the row draws exactly as it would with
    no segment colour set (LRR-M2.1, then SCV-M4.1 for the fill).

    The completed tint keeps the theme's text colour, and that is a decision
    rather than an omission: ``success_tint`` is a theme token, paired in the
    theme with the same theme's ``row_text``. Deriving a colour for it would
    override a pairing that was designed instead of inherited.
    """

    fill: Optional[str]
    text_color: Optional[str]
    source: str


def row_fill(
    palette: Mapping[str, str],
    *,
    use_completed_tint: bool,
    segment_color: Optional[str] = None,
) -> RowFill:
    """The fill for one list row.

    Purpose: PLC-M4 -- the one copy of a rule that was written out by hand in
             five screens, each with its own precedence chain around it.
    Spec:    docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m4
    Tests:   tests/test_priority_level_colors.py::test_pccm1_segment_and_completed_still_fill_a_row

    Precedence: a VSP segment colour wins, then completion, then nothing.

    **A priority level is no longer one of the branches (PCC-M1, 2026-11-11).**
    It was between PLC-M4 and then, which is why ``AGENTS.md`` names this the
    one permitted full-row data fill. The scheme now applies to the Priority
    cell alone (``level_cell_fill``), so a row with no segment colour and no
    completion keeps the theme's own background, as before 2026-11-08. That is
    also why ``settings`` and ``item`` are gone: both were here only to reach
    the level, and keeping them read as though the row still depended on the
    item's priority.

    The two flags are what each screen already decided for itself, and neither
    is used by all five:

    * ``use_completed_tint`` is "should this row take the completed tint", not
      "is this item completed". The Completed screen passes ``False`` because
      every row there is completed and the tint would be the whole screen; it
      has never drawn one. Upcoming passes ``False`` because it has never had a
      completed branch at all.
    * ``segment_color`` is ``None`` from Hierarchical and Completed, which have
      always applied their segment colour as an accent only and never as a
      fill.

    Both differences are preserved here rather than quietly fixed; they are
    logged in ``BACKLOG.md`` instead (``PLC-A2``).

    A segment fill derives its text colour the same way the level fill used to,
    so a pale VSP segment colour no longer draws the dark theme's near-white
    ``row_text`` on itself (LRR-M2.1, closing ``PLC-A1``).

    **The fill is the normalised value, or no fill at all (SCV-M4.1).** It
    used to be the raw stored value, passed through exactly as given --
    including a value ``normalize_hex_color`` rejects -- on the grounds that
    what colour a row draws was not what ``PLC-A1`` named. ``LRR-A1`` then
    filed the consequence: a value Tk cannot parse raises ``TclError``
    part-way through a refresh and takes the list screen down, measured as
    ``invalid color name "#0X1234"`` from ``ctk.CTkFrame(fg_color=…)``. A row
    with no fill is a row that looks like it did before the user set a colour;
    a raised ``TclError`` is a blank screen.

    This is **not** the last gate before ``ctk.CTkFrame(fg_color=…)``, and an
    earlier draft of this docstring said it was. Each of the five row builders
    calls ``theme.apply_segment_accent`` on the next line with the same raw
    value, and ``screens.segment_color_utils`` owns the value both of them are
    given. Those two gate it as well (SCV-M6.3); dropping the fill here would
    have bought nothing on its own.
    """
    if segment_color:
        # ``pick_text_color`` answers black for anything it cannot parse, and
        # black on an unknown background can be worse than the theme's own row
        # text -- black on ``navy`` is about 1.3:1 -- so an unreadable colour
        # gets no derived text colour either. The source stays ``segment``:
        # the precedence decision was made, and only the colour is missing.
        readable = normalize_hex_color(segment_color)
        if readable is None:
            # Said once per value, not once per row: five list screens call
            # this for every row they draw. ``level_color`` logs its own bad
            # values the same way, so "no colour given" stays distinguishable
            # from "a colour nobody could read" in app.log.
            _warn_unreadable_segment_color(segment_color)
        return RowFill(
            readable,
            pick_text_color(readable) if readable else None,
            SOURCE_SEGMENT,
        )
    if use_completed_tint:
        return RowFill(palette["success_tint"], None, SOURCE_COMPLETED)
    return RowFill(None, None, SOURCE_NONE)


def fill_for_level(settings: Any, level: str) -> RowFill:
    """The colour one priority *level* draws, and legible text for it.

    Purpose: PCC-M2 -- one authority for "what colour is this level", so the
             five Priority cells and four chip sites cannot drift apart the way
             the five row fills did before PLC-M4.
    Spec:    docs/unused-docs/implementation_plan_2026-11-11_priority_cell_colour.md#pcc-m2
    Tests:   tests/test_priority_level_colors.py::test_pccm2_the_priority_cell_takes_its_level_colour,
             ::test_pccm2_an_unset_level_means_no_cell_fill,
             ::test_pccm2_the_cell_text_clears_the_contrast_bar

    ``RowFill`` is reused rather than a second dataclass added: it is exactly
    ``(fill, text_color, source)`` and nothing in it is row-shaped.

    ``NO_FILL`` -- a cleared level, and the "No high or critical" default --
    yields no fill *and* no text colour, so an uncoloured cell keeps the text
    colour its row decided. An uncoloured cell can sit on a VSP segment fill,
    where discarding that row's derived colour would make the text illegible.

    ``level_color`` has already substituted the theme default for an unusable
    stored value and logged it, so there is nothing to validate here.
    """
    colour = level_color(settings, level)
    if not colour:
        return RowFill(None, None, SOURCE_NONE)
    return RowFill(colour, pick_text_color(colour), SOURCE_LEVEL)


def level_cell_fill(settings: Any, item: Any) -> RowFill:
    """The fill for one item's Priority cell.

    Purpose: PCC-M2 -- the priority colour scheme applies to this cell's
             background and nothing else. Before 2026-11-11 it tinted the whole
             row, and the cell was ``palette["danger"]``: a hard red unrelated
             to the scheme and unreachable from Settings.
    Spec:    docs/unused-docs/implementation_plan_2026-11-11_priority_cell_colour.md#pcc-m2
    Tests:   tests/test_priority_level_colors.py::test_pccm2_the_priority_cell_takes_its_level_colour,
             ::test_pccm3_a_rendered_priority_cell_carries_the_level_colour

    Asks ``priority_level_for_item`` and nothing else: it does not know whether
    its row has a segment fill, a completed tint or neither. The cell's colour
    is the item's priority; the row's is ``row_fill``'s separate decision.
    """
    return fill_for_level(settings, priority_level_for_item(item))
