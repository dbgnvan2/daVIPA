"""The shared notice line: how a screen tells the user something.

Purpose: MOD-M1 -- one contract for reporting to the user, so no screen has to
         reach for a platform dialog to say "saved" or "that failed".
Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md#mod-m1
Tests:   tests/test_modeless_notices.py

This is not a new idea. ``PlanScreen`` and ``DragScheduleScreen`` have carried
``set_status(text, kind)`` since DRP-M3, and the reason is recorded at
``plan.py:2446``: on macOS the platform dialog raises a bare ``TclError`` from
the idle callback a drag release schedules, and a hand-rolled grabbed toplevel
in its place hung the application outright, because its window could not become
visible while its own grab was up. Both were reported from the running screen
on 2026-11-07, three hours apart. A label already on the screen cannot fail
either way, which is why it is the one place a notice is allowed to live.

What this module adds is that the other screens may have it too.
"""

import logging

import customtkinter as ctk

from ..theme import status_text_color

logger = logging.getLogger(__name__)


#: Kinds that clear themselves (MOD-M3). Everything else persists, so an
#: unknown kind stays on screen rather than vanishing: a notice nobody sees is
#: the failure this whole change exists to fix. ``status_text_color`` accepts
#: legacy colour words beside the semantic names, so both spellings are here.
TRANSIENT_KINDS = frozenset({"info", "blue", "success", "green"})


#: How many names an inline notice lists before it summarises the rest. A
#: status line has one line's room, where the dialog this replaced had a
#: scrollable body, so the cap is lower than the 10 that body used.
INLINE_LIST_CAP = 3


#: How many ancestors ``report_on`` walks before it gives up. A screen sits a
#: handful of frames below its toplevel, so this is slack, not a limit any
#: real widget reaches; it is here because ``master`` is whatever the widget
#: says it is and a cycle would spin for ever.
NOTICE_ANCESTRY_LIMIT = 20


def inline_list(names, cap: int = INLINE_LIST_CAP) -> str:
    """Join names for a one-line notice, summarising past ``cap``.

    Purpose: MOD-M2 -- the refusals that used to list their blockers down a
             dialog body have one line now, and a bulleted list with embedded
             newlines does not read on one.
    Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md#mod-m2
    Tests:   tests/test_modeless_notices.py::test_modm2_an_inline_list_is_capped

    Both APE deletion refusals compose one, so it lives here rather than in
    either of them (P5).
    """
    names = list(names)
    shown = ", ".join(str(n) for n in names[:cap])
    if len(names) > cap:
        shown += f" and {len(names) - cap} more"
    return shown


def report_on(widget, text: str, kind: str = "muted") -> bool:
    """Report on the first notice line at or above ``widget``.

    Purpose: MOD-M2 -- the week-collision notices are module functions given
             a ``parent`` widget, not screens, so they cannot carry the mixin.
    Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md#mod-m2
    Tests:   tests/test_modeless_notices.py::test_modm2_report_on_finds_the_nearest_line

    Returns whether a line took it, so a caller that must fall back can tell.
    That answer is ``set_status``'s own, not "a setter was called": a label
    that exists can still refuse the write while it is being torn down, and a
    caller told the user was informed when they were not is the silence this
    module exists to remove (P6 -- verify the claim against the artifact).
    """
    node = widget
    seen = 0
    while node is not None and seen < NOTICE_ANCESTRY_LIMIT:
        seen += 1
        getter = getattr(node, "notice_label", None)
        label = getter() if callable(getter) else getattr(node, "status_label",
                                                          None)
        setter = getattr(node, "set_status", None)
        if label is not None and callable(setter):
            try:
                if label.winfo_exists():
                    if setter(text, kind):
                        return True
            except Exception:
                # WARNING, not debug: this is one of the ways a notice goes
                # nowhere, and the quiet ones are the ones nobody finds (P2).
                logger.warning(
                    "a notice line on the way up was not usable: %r", text)
        node = getattr(node, "master", None)
    return False


class StatusNoticeMixin:
    """Give a screen the notice line, and the ``set_status`` contract.

    Purpose: MOD-M1 -- the contract ``PlanScreen`` and ``DragScheduleScreen``
             already satisfy, in one place so 23 other screens can satisfy it
             without each inventing it.
    Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md#mod-m1
    Tests:   tests/test_modeless_notices.py::test_modm1_every_reporting_screen_sets_text_and_semantic_colour

    Mixed in ahead of ``ctk.CTkFrame``. A screen that already builds its own
    ``status_label`` keeps it; one that does not calls
    :meth:`create_status_line`.
    """

    #: Which attribute holds the notice label. Overridden where a screen
    #: already uses ``status_label`` for something else -- ``TimerWindow``
    #: shows the timer's own state there ("Ready to start"), and a notice
    #: written over it would erase what the window is for.
    NOTICE_LABEL_ATTR = "status_label"

    #: Set by :meth:`create_status_line`, or by the screen itself.
    status_label = None

    def notice_label(self):
        """The label notices are drawn on, or None before it is built."""
        return getattr(self, self.NOTICE_LABEL_ATTR, None)

    def create_status_line(self, parent=None, **grid_kwargs):
        """Build the notice label and return it.

        ``grid_kwargs`` goes straight to ``grid``, so the caller places it;
        a screen knows where its own bottom row is and this does not.
        """
        label = ctk.CTkLabel(parent if parent is not None else self,
                             text="", anchor="w")
        setattr(self, self.NOTICE_LABEL_ATTR, label)
        if grid_kwargs:
            label.grid(**grid_kwargs)
        return label

    def set_status(self, text: str, kind: str = "muted",
                   persist: bool = False) -> bool:
        """Show ``text`` on the notice line, coloured for ``kind``.

        Purpose: MOD-M1/M3/M4 -- report to the user without a platform dialog,
                 persist anything they must act on, and never raise from the
                 callback the notice was written in.
        Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md#mod-m1
        Tests:   tests/test_modeless_notices.py::test_modm1_every_reporting_screen_sets_text_and_semantic_colour
                 tests/test_modeless_notices.py::test_modm3_an_error_survives_a_refresh
                 tests/test_modeless_notices.py::test_modm4_a_notice_from_an_idle_callback_does_not_raise

        An ``info`` or ``success`` notice clears itself after
        ``AppSettings.notice_dismiss_ms``; an ``error``, ``warning`` or
        ``muted`` one stays until the screen says otherwise (MOD-M3).

        ``persist=True`` keeps a transient kind up anyway, for the notices
        whose text carries something the user still has to do or account for:
        "export that day again to remove it from Google Calendar" is an
        instruction, and "removed 4 of 6 blocks" is the partial-outcome
        evidence the house rules require to be surfaced. A green confirmation
        is the right colour for both; six seconds is not the right lifetime.

        Returns whether the notice was drawn, so ``report_on`` can keep
        walking rather than report a write that did not land (P6).
        """
        label = self.notice_label()
        if label is None:
            # Not silently dropped (P2): a screen reporting before it has a
            # notice line is a wiring mistake, and the message is the evidence.
            logger.warning("%s has no status line yet; notice dropped: %r",
                           type(self).__name__, text)
            return False

        self._cancel_pending_dismiss()
        try:
            label.configure(text=text, text_color=status_text_color(kind))
        except Exception:
            # MOD-M4: the caller may be an idle callback from a drag release,
            # and a notice that raises there takes the gesture with it --
            # which is PD-M12's traceback. Report and carry on.
            logger.exception("notice could not be drawn: %r", text)
            return False

        if text and not persist and kind in TRANSIENT_KINDS:
            self._schedule_dismiss()
        return True

    def notify_owner(self, text: str, kind: str = "muted") -> bool:
        """Report on the nearest ancestor's notice line instead of this one.

        Purpose: MOD-M2 -- a dialog that reports and then closes cannot report
                 on itself; its line goes with it.
        Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md#mod-m2
        Tests:   tests/test_modeless_notices.py::test_modm2_a_dialog_that_closes_reports_on_its_opener
                 tests/test_modeless_notices.py::test_modm2_an_orphan_notice_is_logged

        ~30 of the swept call sites are `showinfo("Success", ...)` followed by
        ``self.destroy()``. Written to this object's own label the message
        would be destroyed in the same frame it was drawn, so the user would
        be told nothing at all -- quieter than the dialog it replaced, and
        the one way this change could make the app worse.

        Walks ``master`` rather than taking the opener as an argument: a
        dialog is constructed with its parent as ``master`` already, so there
        is no new wiring for 19 dialog classes to get wrong.
        """
        if report_on(getattr(self, "master", None), text, kind):
            return True
        # Not silently dropped (P2). Falling back to this object's own line is
        # wrong here -- the caller is about to destroy it -- so say so, with
        # the message, and let the walk checklist find the screen that needs
        # a notice line of its own.
        logger.warning("no notice line above %s; %s notice dropped: %r",
                       type(self).__name__, kind, text)
        return False

    def clear_status(self):
        """Take the notice down now."""
        self._cancel_pending_dismiss()
        label = self.notice_label()
        if label is None:
            return
        try:
            if not label.winfo_exists():
                # The screen went away before the dismissal fired. Nothing is
                # wrong and nothing is lost, so this is not an ERROR: app.log
                # is what the walk checklist reads for real dropped notices.
                logger.debug("the notice line is gone; nothing to clear")
                return
            label.configure(text="")
        except Exception:
            logger.exception("notice could not be cleared")

    def dismiss_delay_ms(self) -> int:
        """How long a transient notice stays, from settings (P4)."""
        from ..app_settings import AppSettings

        settings = getattr(self, "settings", None)
        default = AppSettings.notice_dismiss_ms
        value = getattr(settings, "notice_dismiss_ms", default)
        try:
            value = int(value)
        except (TypeError, ValueError):
            logger.warning("notice_dismiss_ms is not a number: %r; using %d",
                           value, default)
            return default
        # A zero or negative delay would take the notice down in the same
        # frame it went up, which reads as the notice never having appeared.
        return value if value > 0 else default

    def destroy(self):
        """Cancel a pending dismissal before its target goes away.

        Purpose: MOD-M3 -- ``utils/after_tracker.py`` was written for exactly
                 this: a timer against a widget the user can close in the
                 meantime fires into Tk as "invalid command name", or here
                 lands in ``clear_status`` and writes an ERROR traceback to
                 ``app.log`` for an ordinary sidebar click (P30).
        Tests:   tests/test_modeless_notices.py::test_modm3_destroy_cancels_a_pending_dismissal

        ``TrackedAfterMixin`` does not override ``after``, so mixing it in
        does not cover this; the mixin sits ahead of it in every MRO, so
        ``super().destroy()`` still reaches its cancellation and the widget's.
        """
        self._cancel_pending_dismiss()
        super().destroy()

    def _schedule_dismiss(self):
        try:
            self._status_dismiss_after = self.after(self.dismiss_delay_ms(),
                                                    self.clear_status)
        except Exception:
            # No event loop to schedule on. The notice stays up, which is the
            # safe direction: visible too long beats never seen.
            logger.debug("no loop to schedule the notice dismissal on")
            self._status_dismiss_after = None

    def _cancel_pending_dismiss(self):
        pending = getattr(self, "_status_dismiss_after", None)
        if not pending:
            return
        self._status_dismiss_after = None
        try:
            self.after_cancel(pending)
        except Exception:
            # Already fired or the widget is going away; nothing to cancel.
            logger.debug("nothing to cancel for the notice dismissal")
