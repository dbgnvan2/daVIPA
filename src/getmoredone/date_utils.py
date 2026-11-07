"""
Date utility functions for weekend-aware date calculations.
"""

from datetime import date, timedelta
from typing import Optional, Tuple


def increment_date(start_date: date, days: int, include_saturday: bool = True, include_sunday: bool = True) -> date:
    """
    Increment a date by the specified number of days, skipping weekends if configured.

    Args:
        start_date: The starting date
        days: Number of days to increment (can be negative for decrement)
        include_saturday: Whether Saturday is included in date calculations
        include_sunday: Whether Sunday is included in date calculations

    Returns:
        The new date, potentially adjusted to skip excluded weekend days

    Note:
        - If both Saturday and Sunday are included, this behaves like normal date arithmetic
        - If one or both weekend days are excluded, the function will skip over them
        - This only applies to automated calculations; manual date entry is unrestricted
    """
    # If both weekend days are included, just do normal date arithmetic
    if include_saturday and include_sunday:
        return start_date + timedelta(days=days)

    # Calculate the direction of movement
    direction = 1 if days > 0 else -1
    remaining_days = abs(days)
    current_date = start_date

    # Move day by day, skipping excluded weekend days
    while remaining_days > 0:
        current_date += timedelta(days=direction)

        # Check if current date is an excluded weekend day
        weekday = current_date.weekday()  # 0=Monday, 5=Saturday, 6=Sunday
        is_excluded_saturday = weekday == 5 and not include_saturday
        is_excluded_sunday = weekday == 6 and not include_sunday

        # Only count this day if it's not an excluded weekend day
        if not (is_excluded_saturday or is_excluded_sunday):
            remaining_days -= 1

    return current_date


def adjust_to_business_day(target_date: date, include_saturday: bool = True, include_sunday: bool = True) -> date:
    """
    Adjust a date forward to the next business day if it falls on an excluded weekend day.

    Args:
        target_date: The date to potentially adjust
        include_saturday: Whether Saturday is included as a business day
        include_sunday: Whether Sunday is included as a business day

    Returns:
        The adjusted date (same as input if already a business day)
    """
    # If both weekend days are included, no adjustment needed
    if include_saturday and include_sunday:
        return target_date

    current_date = target_date

    # Keep moving forward until we find a non-excluded day
    while True:
        weekday = current_date.weekday()  # 0=Monday, 5=Saturday, 6=Sunday

        is_excluded_saturday = weekday == 5 and not include_saturday
        is_excluded_sunday = weekday == 6 and not include_sunday

        # If this day is acceptable, return it
        if not (is_excluded_saturday or is_excluded_sunday):
            return current_date

        # Move to next day
        current_date += timedelta(days=1)


def get_next_business_day(from_date: date, include_saturday: bool = True, include_sunday: bool = True) -> date:
    """
    Get the next business day after the given date.

    This is a convenience function that increments by 1 day and adjusts to business day.

    Args:
        from_date: The starting date
        include_saturday: Whether Saturday is included as a business day
        include_sunday: Whether Sunday is included as a business day

    Returns:
        The next business day
    """
    return increment_date(from_date, 1, include_saturday, include_sunday)


def first_of_next_month(today_date: date) -> date:
    year = today_date.year + (1 if today_date.month == 12 else 0)
    month = 1 if today_date.month == 12 else today_date.month + 1
    return date(year, month, 1)


def first_of_next_quarter(today_date: date) -> date:
    next_quarter = QUARTER_OF_MONTH[today_date.month] + 1
    year = today_date.year
    if next_quarter == 5:
        next_quarter = 1
        year += 1
    return date(year, MONTHS_OF_QUARTER[next_quarter][0], 1)


def future_date_targets(
    today_date: date,
    near_term_days: int,
    long_term_days: int,
    next_month_offset_days: int,
    next_quarter_offset_days: int,
) -> Tuple[date, date, date, date]:
    near_term_days = max(1, int(near_term_days))
    long_term_days = max(1, int(long_term_days))
    near_date = today_date + timedelta(days=near_term_days)
    long_date = today_date + timedelta(days=long_term_days)
    month_date = first_of_next_month(today_date) + timedelta(days=int(next_month_offset_days))
    quarter_date = first_of_next_quarter(today_date) + timedelta(days=int(next_quarter_offset_days))
    return near_date, long_date, month_date, quarter_date


# ---------------------------------------------------------------------------
# APC-M1 — the one quarter <-> month mapping
# ---------------------------------------------------------------------------
#
# Calendar quarters. Before this lived here it was written three times: a dict
# in ``weekly_tactic``, a second dict inside
# ``VPSManager._clear_quarter_month_flags``, and ``((month - 1) // 3) + 1`` in
# the APE Weekly screen. Three copies that happened to agree, and nothing that
# owned the rule — which is how an APE came to be filed under Q3 and M11 at
# once, invisible to APE Weekly ever after.

QUARTER_OF_MONTH: dict[int, int] = {month: ((month - 1) // 3) + 1 for month in range(1, 13)}

MONTHS_OF_QUARTER: dict[int, tuple[int, int, int]] = {
    quarter: tuple(month for month in range(1, 13) if QUARTER_OF_MONTH[month] == quarter)
    for quarter in (1, 2, 3, 4)
}


def quarter_of_month(month: int) -> int:
    """The calendar quarter a month belongs to.

    Purpose: one answer to "which quarter is month 11 in", for every caller.
    Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m1
    Tests:   tests/test_ape_period_consistency.py::test_apcm11_quarter_of_month_covers_every_month

    Raises ``ValueError`` on a month outside 1-12 rather than returning a
    plausible-looking quarter: a caller holding month 0 or 13 has a bug, and a
    silent answer is what let the bad pair reach the database.
    """
    try:
        return QUARTER_OF_MONTH[int(month)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"month must be 1-12, got {month!r}")


def months_of_quarter(quarter: int) -> tuple[int, int, int]:
    """The three months a calendar quarter contains.

    Purpose: one answer to "which months may be picked for Q4".
    Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m1
    Tests:   tests/test_ape_period_consistency.py::test_apcm11_months_of_quarter_covers_every_quarter
    """
    try:
        return MONTHS_OF_QUARTER[int(quarter)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"quarter must be 1-4, got {quarter!r}")


def current_quarter(today_date: date) -> int:
    """The quarter a date falls in — what a quarter picker should open on.

    Purpose: give the APE screens a default that cannot disagree with the
             month picker beside it.
    Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m3
    Tests:   tests/test_ape_period_consistency.py::test_apcm31_quarter_defaults_to_current_quarter
    """
    return quarter_of_month(today_date.month)
