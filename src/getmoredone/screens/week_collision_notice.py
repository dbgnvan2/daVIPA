"""The shared user-facing moments of a Weekly Tactic, on any screen.

Purpose: give the collision signal one wording and one place, so every surface
         that can move a week item reports it the same way; and the same for
         the question asked before completing a tactic that still has open
         children, which was written on one screen of seven.
Spec:    docs/spec_2026-08-18_weekly_tactic_scheduling.md#wt-m1c5
         docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m6
Tests:   tests/test_weekly_tactic_schema.py::test_wt_m1c5_collision_notice_reaches_the_user
         tests/test_weekly_tactic_completion_surfaces.py

``update_action_item`` and ``reschedule_item`` return False when a week item's
target week is already taken, and record the detail on
``db_manager.last_week_collision``. A return value nobody reads is the same
silence as no return value at all (P25) — so this is the reader.
"""

import logging
from contextlib import contextmanager
from tkinter import messagebox
from typing import Any, Optional

from ..models import Status
from .status_notice import report_on

logger = logging.getLogger(__name__)


@contextmanager
def _parent_not_on_top(parent: Any):
    """Lower an always-on-top parent for the life of the notice below it.

    Purpose: the question below still ends in ``messagebox``, and the parent
             is often the TimerWindow, which sets ``-topmost`` at construction
             and never drops it. A modal that opens *behind* its parent still
             holds ``grab_set()``, so it takes every click while showing
             nothing — the window underneath looks frozen. That is the bug the
             timer's own dialogs were fixed for; these call sites were left
             out (P5: the fix stopped at the file boundary).

             MOD-M2 left one caller: the two *telling* notices now go to the
             screen's own notice line, which is inside the window and cannot
             sit behind it. Only ``confirm_weekly_tactic_completion`` asks,
             and an asking site is still a modal (MOD-M5, phase 2).
    Tests:   tests/test_weekly_tactic_surfaces.py::test_wt_m6b6_a_notice_lowers_an_always_on_top_parent

    Imported inside the function on purpose: ``timer_window_dialogs`` imports
    this module, so a top-level import would be a cycle. The helper belongs in
    a neutral module and moving it is recorded in BACKLOG.md rather than done
    at the end of a batch.
    """
    if parent is None:
        yield
        return
    from .timer_window_dialogs import parent_topmost_suspended
    with parent_topmost_suspended(parent):
        yield


def describe_week_collision(collision: Optional[dict]) -> Optional[str]:
    """One sentence naming what did not move, or None if nothing collided."""
    if not collision:
        return None
    return (
        "That week already has a Weekly Tactic for this Annual Plan Element, "
        f"so the tactic stayed on {collision.get('kept_start')} instead of "
        f"moving to {collision.get('rejected_start')}. "
        "Only one Weekly Tactic can exist per plan element per week."
    )


def describe_cascade(report: Any) -> Optional[str]:
    """What a re-file created, phrased for a status line. None if nothing was.

    Spec:  docs/spec_2026-08-18_weekly_tactic_scheduling.md#wt-m6b5
    Tests: tests/test_weekly_tactic_surfaces.py::test_wt_m6b5_created_records_summarised_to_user
    """
    if report is None:
        return None
    status = getattr(report, "status", "refiled")
    if status == "tactic_missing":
        return (
            "This item's Weekly Tactic no longer exists, so the item was saved "
            "without being re-filed and may now sit outside its week."
        )
    if status == "ape_missing":
        return (
            "This item's Weekly Tactic has no Annual Plan Element, so the item "
            "was saved without being re-filed and may now sit outside its week."
        )
    text = report.describe() if hasattr(report, "describe") else ""
    return text or None


def cascade_needs_attention(report: Any) -> bool:
    """Does this report warrant interrupting the user?

    Creating a Weekly Tactic happens on most moves across a week boundary, so
    a modal for every one of those would be noise the user learns to dismiss.
    Two things genuinely need saying:

    * a **year rollover** created blank editorial rows that need the user's own
      words — nobody else can write them, and nothing else will ask;
    * the re-file **failed**, so the item is knowingly outside its week.

    Everything else is in the report and in ``weekly_tactic_debug.log``.
    """
    if report is None:
        return False
    return bool(getattr(report, "failed", False) or getattr(report, "stubs", None))


def notify_cascade(db_manager: Any, parent: Any = None) -> bool:
    """Tell the user when the last save built something needing their attention.

    ``last_cascade_report`` had no reader anywhere in ``src/`` — a save that
    built eight planning rows, blank rollover stubs included, told the user
    nothing (P25).
    """
    report = getattr(db_manager, "last_cascade_report", None)
    if not cascade_needs_attention(report):
        return False
    message = describe_cascade(report)
    if not message:
        return False
    # MOD-M2: on the notice line of the screen that saved, not a dialog over
    # it. Always a ``warning``, never a self-clearing ``info``:
    # ``cascade_needs_attention`` admits exactly two things and both need the
    # user, so there is no transient case to have. The stubs one says "need
    # your words" and its own docstring says nothing else will ever ask, so a
    # six-second lifetime would be quieter than the modal this replaced --
    # the one way this change could make the app worse.
    shown = report_on(parent, message, "warning")
    if not shown:
        # Not silently dropped (P2). No notice line above this parent means a
        # screen the MOD-M1 sweep did not reach, and the message is the
        # evidence of which one.
        logger.warning("no notice line above %r; cascade notice dropped: %r",
                       parent, message)
    return shown


def notify_weekly_tactic_changes(db_manager: Any, parent: Any = None) -> bool:
    """Report a refused week *and* anything the cascade built. One call site."""
    collided = notify_week_collision(db_manager, parent)
    created = notify_cascade(db_manager, parent)
    return collided or created


def notify_week_collision(db_manager: Any, parent: Any = None) -> bool:
    """Show the collision notice if the last save hit one.

    Returns True when a notice was shown. Safe to call after every save: the
    flag is cleared at the start of each one, so a stale collision cannot be
    reported as this save's result.
    """
    message = describe_week_collision(getattr(db_manager, "last_week_collision", None))
    if not message:
        return False
    # MOD-M2: a refused week is something the user must act on, so it is a
    # ``warning`` and stays on the line until the screen replaces it.
    shown = report_on(parent, message, "warning")
    if not shown:
        logger.warning("no notice line above %r; collision notice dropped: %r",
                       parent, message)
    return shown


def confirm_weekly_tactic_completion(
    db_manager: Any, item_id: str, parent: Any = None
) -> bool:
    """WTP-M6.1 - ask before completing a Weekly Tactic with open children.

    Purpose: a tactic is the parent of the items filed under it, so completing
             one is a claim about a week's work. It asks rather than refuses,
             because a week does end with items still open and the user is the
             one who decides what that means. This lives here, not on a
             screen, because there are seven places that complete an item and
             a guard on one of them is the same as no guard (P25) - the Today
             checkbox and the Hierarchical tree are the surfaces people
             actually tick things off from.
    Spec:    docs/spec_2026-11-08_weekly_tactic_as_parent.md#wtp-m6
    Tests:   tests/test_weekly_tactic_completion_surfaces.py::test_wtpm67_every_completion_surface_asks_first
             tests/test_weekly_tactic_completion_surfaces.py::test_wtpm67_a_declined_prompt_completes_nothing_on_any_surface

    Returns True when there is nothing to ask about, so the ordinary path is
    unchanged for every item that is not a tactic and for a tactic whose
    children are all done. Completion does not cascade either way (WTP-D8):
    the question is about what the user is claiming, not about what the save
    will touch.

    The item type is read from the stored row rather than taken from the
    caller, because five of the seven call sites have only an ``item_id`` in
    hand and a caller that had to know would be a second reader of parenthood.
    """
    item = db_manager.get_action_item(item_id)
    if item is None or getattr(item, "item_type", None) != "week":
        return True
    open_children = [
        child
        for child in db_manager.get_children(item_id)
        if getattr(child, "status", None) != Status.COMPLETED
    ]
    if not open_children:
        return True
    count = len(open_children)
    noun = "Action Item" if count == 1 else "Action Items"
    with _parent_not_on_top(parent):
        return bool(
            messagebox.askyesno(
                "Complete Weekly Tactic",
                f"{count} {noun} under this Weekly Tactic "
                f"{'is' if count == 1 else 'are'} still open.\n\n"
                "Completing the tactic leaves them open. Complete it anyway?",
                parent=parent,
            )
        )
