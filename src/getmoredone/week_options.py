"""Week identity and the week-picker's option list — one home, two callers.

Purpose: the APE Week Assignment screen and the APE Week Actions screen both
         need "which week is this date in" and "which weeks may be picked".
         A second copy of either is how the APE quarter/month defect started:
         two places owned the same rule, they disagreed, and the screen that
         derived its own answer showed nothing. The rule lives here and both
         screens call it.
Spec:    docs/spec_2026-11-07_ape_week_actions.md#4 (step 3)
Tests:   tests/test_ape_week_actions.py::test_awam41_week_defaults_to_current_week,
         tests/test_weekly_items_week_options.py

Every function here is pure: the clock and the settings object are passed in,
never read from a module global, so a caller's test needs no monkeypatching to
pin a week.
"""

from datetime import date, timedelta
from typing import Any, List, Optional

from . import week_calendar
from .app_settings import AppSettings

# How many weeks ahead of the current one the picker offers before it falls
# back to whatever week starts already exist in the database.
FUTURE_WEEKS_OFFERED = 3


def first_day_of_week(app: Any) -> int:
    """The user's first-day-of-week setting, clamped to 0-6 (0 = Monday).

    Falls back to loading the settings when the app has none on it, and to 0
    when the stored value is missing or not a number — a week picker is not
    worth raising over.
    """
    try:
        settings = getattr(app, "settings", None) or AppSettings.load()
        value = int(getattr(settings, "first_day_of_week", 0))
    except Exception:
        value = 0
    return value if 0 <= value <= 6 else 0


def week_start_for(target_date: date, first_day: int) -> date:
    """WT-M2.B — week identity comes from the one helper, not local arithmetic."""
    return week_calendar.week_start(target_date, first_day)


def selectable_week_options(
    today: date,
    existing_starts: Optional[List[str]],
    first_day: int,
) -> List[str]:
    """The week-start strings a picker offers, current week first.

    The current week and the next three, then any week start already in the
    data that is not already in the list — so a tactic filed against an older
    week stays reachable instead of dropping off the picker (P2).
    """
    current_start = week_start_for(today, first_day)
    options = [
        (current_start + timedelta(days=7 * index)).isoformat()
        for index in range(FUTURE_WEEKS_OFFERED + 1)
    ]
    for week_start in existing_starts or []:
        if week_start not in options:
            options.append(week_start)
    return options
