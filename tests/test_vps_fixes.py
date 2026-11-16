"""VPS editor and planning screen — the structure two old bug fixes depend on.

BC3. Converted from a standalone script: every test returned a bool inside
``except Exception: return False``, so pytest ignored the verdict and an
exception read as a pass. None of these four were lying at the time of the
conversion — unlike ``test_vps_segments``, which was — but none of them could
have told us if they started.

The two fixes these guard:
  * the New Vision crash — `CTkMessageBox` replaced with tkinter's `messagebox`
  * segment selection on the planning screen — `selected_segments`

Spec: docs/unused-docs/implementation_plan_2026-08-19_backlog_clearance.md#batch-1
"""

import inspect  # noqa: F401  (kept: other tests in this file still use it)

import pytest

import ast
import pathlib

from tests.source_asserts import (
    assigns_self_attribute,
    calls_any_attribute,
    calls_attribute,
    references_name,
)

from src.getmoredone.screens import vps_editors
from src.getmoredone.screens.vps_editors import TLVisionEditorDialog
from src.getmoredone.screens.vps_planning import VPSPlanningScreen


def test_bc3_vps_editors_reaches_for_no_platform_dialog():
    """MOD-M2 -- the replacement for the missing-messagebox guard.

    The New Vision crash was a ``messagebox`` name that was not imported, and
    the guard was that the name exists. These editors no longer name it at
    all: every refusal goes on the dialog's own notice line, so the guard that
    matters now is the opposite one -- the module must not reach for the
    platform again, by import or by call (case b: the behaviour changed on
    purpose, and a guard for an import nothing uses guards nothing).
    """
    assert not hasattr(vps_editors, "messagebox"), (
        "vps_editors imports messagebox again; MOD-M2 reports on the notice "
        "line instead (StatusNoticeMixin.set_status)")
    source = pathlib.Path(vps_editors.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    reached = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr.startswith(("show", "ask"))
        and ast.unparse(node.func).startswith("messagebox.")
    ]
    assert reached == [], f"platform dialogs are back at lines {reached}"


def test_bc3_save_vision_does_not_use_ctkmessagebox():
    """`CTkMessageBox` does not exist in this CustomTkinter build — it crashed.

    Parsed, not greped. `"CTkMessageBox" not in source` is also satisfied by
    deleting the *comment* that explains why it must not come back, and is
    defeated by `getattr(ctk, "CTkMessage" + "Box")`. This matches a real
    identifier — bare or attribute — and nothing in a string or docstring.
    """
    assert not references_name(TLVisionEditorDialog.save_vision, "CTkMessageBox"), (
        "CTkMessageBox is back in save_vision — this is the New Vision crash")


def test_bc3_save_vision_still_reports_errors_to_the_user():
    """Removing the crash must not have removed the error message with it.

    The original check printed a warning and passed when no messagebox call was
    found, so a silent save_vision would have gone unnoticed. MOD-M2 moved the
    channel to the dialog's notice line, so the call asserted here moved with
    it (case b) -- the thing being guarded, that a failed save says something,
    is unchanged.
    """
    assert calls_attribute(
        TLVisionEditorDialog.save_vision, "self", "set_status"
    ), ("save_vision no longer tells the user anything when it fails")


@pytest.mark.parametrize("method", [
    "show_segment_filter_dialog",
    "update_segment_filter",
])
def test_bc3_planning_screen_exposes_segment_selection(method):
    assert callable(getattr(VPSPlanningScreen, method, None)), (
        f"VPSPlanningScreen.{method} is gone — segment filtering is unreachable")


def test_bc3_planning_screen_tracks_selected_segments():
    """The filter needs somewhere to write.

    `"selected_segments" in source` was satisfied by a comment, a docstring, or
    a line that only *read* the attribute — none of which is initialisation.
    This asserts an actual assignment to `self.selected_segments`.
    """
    assert assigns_self_attribute(VPSPlanningScreen.__init__, "selected_segments"), (
        "VPSPlanningScreen.__init__ no longer assigns self.selected_segments, "
        "so the segment filter has nothing to write to")
