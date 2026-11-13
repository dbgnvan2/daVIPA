"""Helpers for resolving item lineage labels for list-style views."""

from __future__ import annotations

from typing import Any

from ..models import ActionItem
from .title_format import split_action_item_title


LINEAGE_COL_CHARS = 15


def lineage_for_item(
    item: ActionItem,
    db_manager,
    item_cache: dict[str, tuple[str, str, str]],
    ape_cache: dict[str, tuple[str, str, str]],
    week_cache: dict[str, str],
    depth: int = 0,
) -> tuple[str, str, str]:
    item_id = getattr(item, "id", "") or ""
    if item_id and item_id in item_cache:
        cached = _normalize_lineage(item_cache[item_id])
        if any(cached):
            return cached

    lineage = _lineage_from_ape_id(getattr(item, "annual_plan_element_id", None), db_manager, ape_cache)
    if any(lineage):
        if item_id:
            item_cache[item_id] = lineage
        return lineage

    if depth < 2:
        # AWA-A1/AWA-A3 — `parent_of`, not `parent_id`: a week-filed item's
        # parent is its Weekly Tactic, named in `weekly_tactic_id`. Reading the
        # column directly meant an item with no Annual Plan Element of its own
        # — one attached to a tactic in the editor, or a legacy row the link
        # migration moved — showed no lineage chips at all, though its tactic
        # could answer for it. APE Week Actions' Add copies the tactic's APE
        # onto the item, so it is not that shape; the editor's attach is.
        # Imported here rather than at module scope: `weekly_tactic` opens a
        # log file in the real application-support directory at import time,
        # and this helper is a pure function that tools and tests import alone.
        # Tests: tests/test_week_filed_item_lineage.py::test_bp6_lineage_survives_even_with_the_annual_plan_element_missing
        from ..weekly_tactic import parent_of
        parent_id = parent_of(item)
        if parent_id:
            parent_item = db_manager.get_action_item(parent_id)
            if parent_item:
                parent_lineage = lineage_for_item(parent_item, db_manager, item_cache, ape_cache, week_cache, depth + 1)
                if any(parent_lineage):
                    if item_id:
                        item_cache[item_id] = parent_lineage
                    return parent_lineage

    structured = _lineage_from_structured_title(item)
    if any(structured):
        if item_id:
            item_cache[item_id] = structured
        return structured

    week_segment = _segment_from_week_action(getattr(item, "week_action_id", None), db_manager, week_cache)
    lineage = (week_segment, "", "")
    if item_id:
        item_cache[item_id] = lineage
    return lineage


def _lineage_from_structured_title(item: ActionItem) -> tuple[str, str, str]:
    parsed = split_action_item_title(item.title)
    context_parts = [part.strip() for part in parsed.context.split("|") if part.strip()]
    if len(context_parts) >= 3:
        category = context_parts[2].split(" - ", 1)[0].strip()
        return context_parts[0], context_parts[1], category
    return "", "", ""


def _lineage_from_ape_id(
    ape_id: str | None,
    db_manager,
    ape_cache: dict[str, tuple[str, str, str]],
) -> tuple[str, str, str]:
    if not ape_id:
        return "", "", ""
    if ape_id in ape_cache:
        cached = _normalize_lineage(ape_cache[ape_id])
        if any(cached):
            return cached

    lineage = ("", "", "")
    conn = getattr(getattr(db_manager, "db", None), "conn", None)
    if conn:
        row = conn.execute(
            """
            SELECT segment_name, subsegment_name, category_name
            FROM annual_plan_elements
            WHERE id = ?
            """,
            (ape_id,),
        ).fetchone()
        if row:
            lineage = (
                (row["segment_name"] or "").strip(),
                (row["subsegment_name"] or "").strip(),
                (row["category_name"] or "").strip(),
            )
    ape_cache[ape_id] = lineage
    return lineage


def _normalize_lineage(value: Any) -> tuple[str, str, str]:
    if isinstance(value, tuple):
        return (
            str(value[0] if len(value) > 0 else "") or "",
            str(value[1] if len(value) > 1 else "") or "",
            str(value[2] if len(value) > 2 else "") or "",
        )
    if isinstance(value, list):
        return (
            str(value[0] if len(value) > 0 else "") or "",
            str(value[1] if len(value) > 1 else "") or "",
            str(value[2] if len(value) > 2 else "") or "",
        )
    return "", "", ""


def _segment_from_week_action(week_action_id: str | None, db_manager, week_cache: dict[str, str]) -> str:
    if not week_action_id:
        return ""
    if week_action_id in week_cache:
        return week_cache[week_action_id]

    segment_name = ""
    conn = getattr(getattr(db_manager, "db", None), "conn", None)
    if conn:
        row = conn.execute(
            """
            SELECT sd.name AS segment_name
            FROM week_actions wa
            LEFT JOIN segment_descriptions sd ON sd.id = wa.segment_description_id
            WHERE wa.id = ?
            """,
            (week_action_id,),
        ).fetchone()
        if row:
            segment_name = (row["segment_name"] or "").strip()
    week_cache[week_action_id] = segment_name
    return segment_name
