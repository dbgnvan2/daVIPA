"""Which priority *level* an action item is in, and what colour that level draws.

Purpose: one place decides the three priority levels and the row tint each one
         takes, so the five list screens cannot drift apart and the user can
         recolour them from Settings.
Spec:    docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m1
Tests:   tests/test_priority_level_colors.py

A **level** is a rule on the two factors the user sets by hand, importance and
urgency. There are three, and they are the three the user named:

    Any Critical · Any High, but no Critical · No high or critical

A level is **not** a priority *band*. A band is a threshold on
``priority_score``, which is the *product* of all four factors
(``time_block_layout.PRIORITY_BANDS``); it has five names of its own and its own
colours in ``theme.py``. The band named "critical" and the level named "Any
Critical" are different questions about the same item, and the answers come
apart: a Medium / Medium / XL / XL item scores 400, which is the ``high`` band,
while having no high or critical factor at all. That is why this module carries
its own names rather than reusing the band ones, and why
``test_plcm14_a_big_score_is_not_a_critical_level`` exists.

Two deliberate choices in ``priority_level``:

* **Thresholds come from ``PriorityFactors``**, never from a literal 20 or 10,
  so renumbering the scale moves the levels with it. Each factor is compared
  against its own scale -- ``IMPORTANCE`` for importance, ``URGENCY`` for
  urgency -- because the two dicts holding identical values today is a fact
  about this build, not a rule.
* **A missing factor is not an excuse.** Importance ``None`` with urgency
  ``Critical`` is Any Critical. This preserves the ``or`` the five list screens
  have always used, and it is the opposite of ``priority_band``, where one
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

# Where a row's fill came from. The screens need this: only a level fill brings
# its own text colour with it (see ``RowFill.text_color``).
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


def level_colors(settings: Any) -> Dict[str, str]:
    """Every level's effective colour, keyed by level."""
    return {level: level_color(settings, level) for level in LEVEL_KEYS}


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

    ``text_color`` is ``None`` for every source except ``level``, and means
    "leave the screen's own ``row_text`` alone". Only a level fill carries a
    text colour, because only a level fill is a colour the user chose with no
    theme behind it: a pale green row in the dark theme needs dark text, and
    the theme's ``row_text`` there is near-white.

    Segment and completed fills keep exactly the text colour they have today.
    Their contrast is a real problem -- a pale segment colour in the dark theme
    also gets near-white text -- but it is a pre-existing one, logged in
    ``BACKLOG.md``, and fixing it here would be a silent sweep of behaviour
    nobody asked about.
    """

    fill: Optional[str]
    text_color: Optional[str]
    source: str


def row_fill(
    settings: Any,
    palette: Mapping[str, str],
    *,
    item: Any,
    use_completed_tint: bool,
    segment_color: Optional[str] = None,
) -> RowFill:
    """The fill for one list row.

    Purpose: PLC-M4 -- the one copy of a rule that was written out by hand in
             five screens, each with its own precedence chain around it.
    Spec:    docs/implementation_plan_2026-11-08_priority_level_colours.md#plc-m4
    Tests:   tests/test_priority_level_colors.py::test_plcm41_a_row_takes_its_level_colour

    Precedence is the one the screens already had, unchanged: a VSP segment
    colour wins, then completion, then the priority level, then nothing. The
    two flags are what each screen already decided for itself, and three of the
    five screens do not use every branch:

    * ``use_completed_tint`` is "should this row take the completed tint", not
      "is this item completed". The Completed screen passes ``False`` because
      every row there is completed and the tint would be the whole screen; it
      has never drawn one. Upcoming passes ``False`` because it has never had a
      completed branch at all.
    * ``segment_color`` is ``None`` from Hierarchical and Completed, which have
      always applied their segment colour as an accent only and never as a
      fill.

    Both differences are preserved here rather than quietly fixed; they are
    logged in ``BACKLOG.md`` instead.
    """
    if segment_color:
        return RowFill(segment_color, None, SOURCE_SEGMENT)
    if use_completed_tint:
        return RowFill(palette["success_tint"], None, SOURCE_COMPLETED)
    colour = level_color(settings, priority_level_for_item(item))
    if not colour:
        return RowFill(None, None, SOURCE_NONE)
    return RowFill(colour, pick_text_color(colour), SOURCE_LEVEL)
