"""PRI-M1.7, PRI-M1.8 and PRI-M2.6 — what the two priority editors show.

Spec: docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md
Plan: docs/implementation_plan_2026-11-08_pri_tests.md

The model-side tests live in ``tests/test_priority_floor_and_cap.py``. These
three are about the screen, because two of the criteria are only about the
screen:

* **PRI-M1.7 and PRI-M1.8 are a pair.** The floor is a create-time rule, so the
  new-item form must *show* it before the first save, and the editor opened on
  an existing unscored row must *not* -- showing it there would offer the user
  a value the row does not have and that nothing is going to write.
* **PRI-M2.6 is checked at both render sites.** PRI-M2's stated purpose was
  that three copies of the product arithmetic became one; a test that read only
  the Item Editor's label would not notice the row-click popup drifting back
  out of agreement with it.

No mapped window: ``conftest.py`` silences ``grab_set`` and withdraws every
window on creation, and ``ItemEditorDialog.__init__`` withdraws itself as well,
so the suite's documented mapped-window count is unchanged by this file.
"""

import customtkinter as ctk
import pytest

from src.getmoredone.models import ActionItem, Defaults, PriorityFactors
from src.getmoredone.screens.inline_editors import InlinePriorityDialog
from src.getmoredone.screens.item_editor import ItemEditorDialog
from src.getmoredone.vps_manager import VPSManager

CAPPED = (20, 20, 16, 16)      # 102400 raw -- the top of every scale
UNCAPPED = (20, 10, 4, 8)      # 6400 raw -- the highest product below the cap


@pytest.fixture
def vps(tmp_path):
    """A manager on a database of this test's own (the default path is real)."""
    manager = VPSManager(str(tmp_path / "priority_form.db"))
    try:
        yield manager
    finally:
        manager.close()


@pytest.fixture
def root():
    try:
        window = ctk.CTk()
    except Exception as exc:  # headless without a display
        pytest.skip(f"Tk display unavailable: {exc}")
    window.withdraw()
    try:
        yield window
    finally:
        window.destroy()


def _set_factors(dialog, factors):
    """Put the four factors into the dialog's comboboxes, by their labels."""
    importance, urgency, size, value = factors
    for var, scale, wanted in (
        (dialog.importance_var, PriorityFactors.IMPORTANCE, importance),
        (dialog.urgency_var, PriorityFactors.URGENCY, urgency),
        (dialog.size_var, PriorityFactors.SIZE, size),
        (dialog.value_var, PriorityFactors.VALUE, value),
    ):
        label = next(k for k, v in scale.items() if v == wanted)
        var.set(f"{label} ({wanted})")


def test_prim17_the_new_item_form_shows_the_lowest_factors(root, vps):
    """PRI-M1.7: with no Defaults configured, the form reads the floor, not 0.

    Before PRI-M1 this form left all four comboboxes empty and the label read
    "Score: 0" -- an unscored item the row was not going to be, since
    ``create_action_item`` floors it on save either way. The form and the row
    disagreeing about a brand-new item is the defect.
    """
    dialog = ItemEditorDialog(root, vps.db_manager, vps_manager=vps)

    shown = (
        dialog.importance_var.get(),
        dialog.urgency_var.get(),
        dialog.size_var.get(),
        dialog.value_var.get(),
    )
    assert shown == ("Low (1)", "Low (1)", "S (2)", "S (2)"), (
        f"the new-item form shows {shown}, not the lowest label on each scale"
    )
    assert dialog.priority_label.cget("text") == "4 (1×1×2×2)", (
        f"the score line reads {dialog.priority_label.cget('text')!r}; a new "
        "item is floored to 4 on save, so the form showing anything else "
        "disagrees with the row it is about to create"
    )


def test_prim17_a_default_still_shows_instead_of_the_floor(root, vps):
    """PRI-M1.7: and the floor fills only what the Defaults leave empty."""
    vps.db_manager.save_defaults(Defaults(scope_type="system", importance=20))

    dialog = ItemEditorDialog(root, vps.db_manager, vps_manager=vps)

    assert dialog.importance_var.get() == "Critical (20)", (
        f"the configured default was overwritten by the floor: "
        f"{dialog.importance_var.get()!r}"
    )
    assert dialog.urgency_var.get() == "Low (1)", dialog.urgency_var.get()
    assert dialog.priority_label.cget("text") == "80 (20×1×2×2)", (
        dialog.priority_label.cget("text")
    )


def test_prim18_an_existing_row_is_not_shown_a_floor_it_does_not_have(root, vps):
    """PRI-M1.8: the editor on an unscored row leaves its comboboxes empty.

    The pair to PRI-M1.7. ``apply_priority_floor`` has one call site, on
    create, so an existing row with ``None`` factors keeps them; the form must
    say so rather than displaying a floor no code is going to write (D3).
    """
    item = ActionItem(who="Self", title="an unscored row")
    item_id = vps.db_manager.create_action_item(item, apply_defaults=False)

    stored = vps.db_manager.get_action_item(item_id)
    stored.importance = stored.urgency = stored.size = stored.value = None
    vps.db_manager.update_action_item(stored)

    reread = vps.db_manager.get_action_item(item_id)
    assert reread.importance is None, (
        "the fixture failed to produce an unscored row, so this test would "
        f"pass for the wrong reason: importance is {reread.importance}"
    )

    dialog = ItemEditorDialog(root, vps.db_manager, item_id=item_id, vps_manager=vps)

    shown = (
        dialog.importance_var.get(),
        dialog.urgency_var.get(),
        dialog.size_var.get(),
        dialog.value_var.get(),
    )
    assert shown == ("", "", "", ""), (
        f"the editor shows {shown} for a row whose factors are all None, "
        "offering a floor the row does not have"
    )


def test_prim26_a_capped_label_says_it_is_capped(root, vps):
    """PRI-M2.6: both render sites, driven as behaviour.

    At the cap the breakdown no longer multiplies out to the number beside it
    -- "9999 (20x20x16x16)" reads as arithmetic that does not add up -- so the
    label has to say it was capped. Asserted at the Item Editor's
    ``update_priority_display`` and at the row-click popup's ``update_score``,
    because PRI-M2 exists to stop those two drifting apart.
    """
    item = ActionItem(who="Self", title="scored at the top",
                      importance=20, urgency=20, size=16, value=16)
    item_id = vps.db_manager.create_action_item(item)
    stored = vps.db_manager.get_action_item(item_id)

    editor = ItemEditorDialog(root, vps.db_manager, item_id=item_id, vps_manager=vps)
    popup = InlinePriorityDialog(root, stored)

    expected_capped = "9999 (capped — 20×20×16×16)"
    expected_uncapped = "6400 (20×10×4×8)"

    for name, dialog, read in (
        ("the Item Editor", editor,
         lambda: editor.priority_label.cget("text")),
        ("the row-click popup", popup,
         lambda: popup.score_label.cget("text")),
    ):
        _set_factors(dialog, CAPPED)
        if dialog is editor:
            editor.update_priority_display()
        else:
            popup.update_score()
        assert read() == expected_capped, (
            f"{name} shows {read()!r} for 20x20x16x16, which is 102400 raw -- "
            "the label must say it was capped or its breakdown reads as "
            "arithmetic that does not add up"
        )

        _set_factors(dialog, UNCAPPED)
        if dialog is editor:
            editor.update_priority_display()
        else:
            popup.update_score()
        assert read() == expected_uncapped, (
            f"{name} shows {read()!r} for 20x10x4x8, which is 6400 -- the "
            "highest product below the cap, so this label must not claim a cap"
        )
