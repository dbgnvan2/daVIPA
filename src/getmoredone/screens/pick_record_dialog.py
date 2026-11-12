"""One dialog for the VSP tabs' Add New buttons.

Purpose: VTF-M3 — four tabs need the same thing. Pick one parent record from
         a list, write something, and say what happened on the tab's own
         status line. Four copies of a Toplevel with a combo box and two
         buttons is four places for the refusal path to be forgotten, which
         is what `_describe_quarter_assignment` and its siblings exist to
         stop happening to the Save buttons this replaces.
Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
Tests:   tests/test_vsp_tab_adds.py::test_vtfm37_add_new_reports_on_the_status_line

**The screens keep the decisions.** Each tab supplies its own options, its own
default and its own write, as three methods a test can call without a display:
what is here is the widget. The dialog is opened from a button `command`, the
same moment as the Edit and Delete confirmations these tabs already open, not
from a drag release or an idle callback (VTF-N2).
"""

import customtkinter as ctk

from ..theme import button_style, combo_box_style, status_text_color


def describe_lineage(row) -> str:
    """One VSP row as a line of text: Segment / SubSegment / Category.

    The label the dialog offers. Vision Elements and Annual Plan Elements
    both carry the triple under the same three `*_name` keys, so the four
    tabs read it the same way; a missing part shows as a dash rather than a
    gap, so two rows that differ only in their category still read apart.
    """
    parts = [
        (row.get("segment_name") or "").strip() or "-",
        (row.get("subsegment_name") or "").strip() or "-",
        (row.get("category_name") or "").strip() or "-",
    ]
    return " / ".join(parts)


def confirm_choice(label, keys_by_label, *, on_confirm, report, set_status,
                   close) -> bool:
    """One pick confirmed: the write, then the close, then the status line.

    Purpose: VTF-S7 — this is the hop that delivers every tab's add sentence,
             and it was inside a closure over a `CTkToplevel`, so no test
             could reach it. Both ends were asserted and the join was not:
             dropping `report` left a refused or half-written add silent on
             all four tabs with nothing red, which is the APC-M2.3 defect
             exactly. As a function it is drivable with four fakes.
    Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
    Tests:   tests/test_vsp_tab_adds.py::test_vtfs7_the_confirmed_pick_closes_then_reports
             tests/test_vsp_tab_adds.py::test_vtfs7_a_raising_write_keeps_the_dialog_open

    The order is the contract. `close` runs before `report` so the tab's
    status line is the last thing written and is not covered by a window that
    is still up; and a write that raises must leave the dialog open with the
    error on its own label, because the tab's line would be behind it.

    Returns True when the write went through and the dialog is gone.
    """
    key = keys_by_label.get((label or "").strip())
    if key is None:
        set_status("Choose one from the list first.")
        return False
    try:
        outcome = on_confirm(key)
    except Exception as exc:  # The write refused, or the row went stale.
        set_status(f"Could not add it: {exc}")
        return False
    close()
    report(outcome)
    return True


def open_pick_record_dialog(
    parent,
    *,
    title: str,
    prompt: str,
    options: list,
    report,
    on_confirm,
    initial=None,
    confirm_text: str = "Add",
    empty_message: str = "There is nothing left to add here.",
    geometry: str = "560x200",
):
    """Ask for one record from `options`, then call `on_confirm` with its key.

    `options` is a list of ``(key, label)``. `initial` is the key to open on,
    or None for no preselection. `on_confirm(key)` does the write and returns
    the sentence to report; raising from it leaves the dialog open with the
    error on its own status label, so a refusal is never silent.

    `report(text)` is the tab's status line. It is called for the outcome and
    for an empty option list -- the one case where no dialog opens at all, and
    the case a user meets by pressing Add New twice.

    Returns the dialog, so a caller (or a test) can drive it; None when there
    was nothing to ask about.
    """
    if not options:
        report(empty_message)
        return None

    labels = [label for _key, label in options]
    keys_by_label = {label: key for key, label in options}
    initial_label = next(
        (label for key, label in options if key == initial), "")

    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry(geometry)
    dialog.transient(parent)
    dialog.grab_set()

    frame = ctk.CTkFrame(dialog)
    frame.pack(fill="both", expand=True, padx=12, pady=12)
    frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(frame, text=prompt).grid(
        row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 6))

    choice_var = ctk.StringVar(value=initial_label)
    combo = ctk.CTkComboBox(
        frame, variable=choice_var, values=labels, **combo_box_style())
    combo.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=6)

    status_label = ctk.CTkLabel(
        frame, text="", text_color=status_text_color("error"), anchor="w",
        wraplength=480, justify="left")
    status_label.grid(row=2, column=0, columnspan=2, sticky="ew",
                      padx=8, pady=(2, 6))

    actions = ctk.CTkFrame(frame, fg_color="transparent")
    actions.grid(row=3, column=0, columnspan=2, sticky="e", padx=8, pady=(8, 4))

    def on_ok():
        confirm_choice(
            choice_var.get(), keys_by_label,
            on_confirm=on_confirm,
            report=report,
            set_status=lambda text: status_label.configure(text=text),
            close=dialog.destroy,
        )

    ctk.CTkButton(actions, text="Cancel", width=90, command=dialog.destroy,
                  **button_style("secondary")).pack(side="right", padx=4)
    ctk.CTkButton(actions, text=confirm_text, width=120, command=on_ok,
                  **button_style("primary")).pack(side="right", padx=4)

    # The widgets a caller drives without a pointer: the combo's variable, the
    # OK handler and the dialog's own status label.
    dialog.choice_var = choice_var
    dialog.confirm = on_ok
    dialog.status_label = status_label
    dialog.option_labels = labels
    return dialog
