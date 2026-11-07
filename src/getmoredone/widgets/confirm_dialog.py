"""A yes/no question the app asks itself, rather than through the platform.

Purpose: PD-M12 -- ``tkinter.messagebox`` cannot be used from the Plan
         screen's drop path. On macOS, ``tk_messageBox`` raises
         ``_tkinter.TclError`` with no message when it is called from the idle
         callback that follows a drag release, and that exception killed both
         of the Plan screen's item-drop write paths before either wrote
         anything: a drop on a non-work day and a drop on either end of the
         day both begin with the question.
Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m12
Tests:   tests/test_plan_screen.py::test_pdm121_the_question_is_asked_by_the_app

This is an ordinary Tk toplevel with a grab and ``wait_window``, which is
Tcl's own modality and does not go near AppKit's. It is deliberately plain:
two buttons, Escape and the window's close button both answering no, and no
behaviour that a caller has to know about.

``ConfirmNotShown`` is the other half of the lesson. A question that cannot be
put on the screen must not leave the caller waiting for an answer that can
never come, so this raises rather than blocking, and the caller decides what
to do with a gesture it could not ask about.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk

from ..theme import button_style

# How long the dialog is given to become visible before it is taken as a
# question that cannot be asked. Generous: this is not a timeout on the user,
# who may leave the dialog open as long as they like -- it only runs while the
# window has not appeared at all.
CONFIRM_VISIBLE_TIMEOUT_MS = 4000


class ConfirmNotShown(RuntimeError):
    """The question could not be put on the screen, so it was not asked."""


def ask_yes_no(
    parent,
    title: str,
    message: str,
    *,
    yes_text: str = "Yes",
    no_text: str = "No",
) -> bool:
    """Ask ``message`` and return True for yes.

    Purpose: PD-M12 -- one question, asked without the platform's dialog.
    Spec:    docs/implementation_plan_2026-11-06_plan_day_controls.md#pd-m12
    Tests:   tests/test_plan_screen.py::test_pdm121_the_question_is_asked_by_the_app

    Raises ``ConfirmNotShown`` if the window never became visible. Closing the
    dialog, pressing Escape and answering ``no_text`` all return False: a
    question nobody answered is not a yes.
    """
    answer: dict = {"value": None}

    window = ctk.CTkToplevel(parent)
    window.title(title)
    window.resizable(False, False)

    def say(value: bool):
        answer["value"] = value
        window.destroy()

    body = ctk.CTkFrame(window, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=20, pady=16)

    ctk.CTkLabel(
        body,
        text=message,
        justify="left",
        anchor="w",
        wraplength=380,
    ).pack(fill="x", pady=(0, 14))

    buttons = ctk.CTkFrame(body, fg_color="transparent")
    buttons.pack(fill="x")

    # No first, yes last, so the safe answer is the one nearest the pointer's
    # usual path and the destructive-looking one is not where a stray Return
    # lands.
    ctk.CTkButton(
        buttons, text=no_text, command=lambda: say(False),
        **button_style("secondary"),
    ).pack(side="right", padx=(8, 0))
    ctk.CTkButton(
        buttons, text=yes_text, command=lambda: say(True),
        **button_style("primary"),
    ).pack(side="right")

    window.protocol("WM_DELETE_WINDOW", lambda: say(False))
    window.bind("<Escape>", lambda _event: say(False))

    try:
        window.transient(parent.winfo_toplevel())
    except tk.TclError:
        pass
    try:
        window.grab_set()
    except tk.TclError:
        # Another grab is up. The question is still asked, just not modally,
        # which is better than refusing to ask it.
        pass

    # A window that never appears would otherwise hold ``wait_window`` for the
    # life of the process -- the one outcome worse than the failure this
    # function exists to replace.
    def give_up_if_invisible():
        try:
            if not window.winfo_viewable():
                window.destroy()
        except tk.TclError:
            pass

    try:
        window.after(CONFIRM_VISIBLE_TIMEOUT_MS, give_up_if_invisible)
    except tk.TclError:
        pass

    try:
        parent.wait_window(window)
    except tk.TclError as problem:
        raise ConfirmNotShown(str(problem) or "the dialog could not be shown")

    value: Optional[bool] = answer["value"]
    if value is None:
        raise ConfirmNotShown("the dialog closed without being answered")
    return value
