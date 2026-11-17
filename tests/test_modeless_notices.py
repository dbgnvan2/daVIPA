"""MOD — a screen tells the user on its own notice line, not in an OS dialog.

Purpose: MOD-M1 to M4 — one notice contract, the 89 telling `messagebox`
         calls moved onto it, an error that persists, and a notice that
         survives the callback PD-M12 died in.
Spec:    docs/unused-docs/implementation_plan_2026-11-16_modeless_notices.md
Tests:   this file

Withdrawn windows throughout: a notice line is read with ``cget``, which needs
no map, so nothing here takes ``mapped_windows`` and the count asserted by
``test_ci_contract.py`` is unchanged.
"""

import ast
import pathlib
import time
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from src.getmoredone.app_settings import AppSettings
from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone import theme
from src.getmoredone.screens.status_notice import (
    TRANSIENT_KINDS,
    StatusNoticeMixin,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"

#: MOD-M2. The only two places left that may tell the user through the
#: platform, each because there is no screen to put a notice on: one is the
#: second instance refusing to start before any window exists, the other is
#: Settings having failed to build, so the screen that would carry the notice
#: is the one that did not appear.
PLATFORM_DIALOG_ALLOWLIST = {
    ("src/getmoredone/app.py", "main", "showwarning"),
    ("src/getmoredone/app.py", "show_settings", "showerror"),
}


def _telling_calls():
    """Every ``messagebox.show*`` call under ``src/``, by AST.

    (path, enclosing function, attribute) rather than a line number, so the
    allowlist does not rot the next time a file above one of them changes.
    """
    found = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(REPO_ROOT).as_posix()
        stack = []

        class Walk(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                stack.append(node.name)
                self.generic_visit(node)
                stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, node):
                func = node.func
                if (isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "messagebox"
                        and func.attr.startswith("show")):
                    found.add((rel, stack[-1] if stack else "<module>",
                               func.attr))
                self.generic_visit(node)

        Walk().visit(tree)
    return found


class _Screen(StatusNoticeMixin, ctk.CTkFrame):
    """The smallest thing that satisfies the contract, for the unit arms."""

    def __init__(self, master, settings=None):
        super().__init__(master)
        self.settings = settings if settings is not None else AppSettings()
        self.create_status_line(row=0, column=0, sticky="ew")


@pytest.fixture
def screen():
    built = []

    def _make(settings=None):
        root = ctk.CTk()
        root.withdraw()
        root.geometry("900x600")
        made = _Screen(root, settings)
        made.grid(row=0, column=0, sticky="nsew")
        built.append(root)
        return made

    yield _make
    for root in built:
        try:
            root.destroy()
        except Exception:
            pass


# ---------------------------------------------------------------- MOD-M1 ----


@pytest.mark.parametrize("kind", ["error", "warning", "info", "success", "muted"])
def test_modm1_every_reporting_screen_sets_text_and_semantic_colour(screen, kind):
    """The contract: the text lands, and the colour comes from the theme."""
    made = screen()
    made.set_status(f"the {kind} message", kind)
    assert made.status_label.cget("text") == f"the {kind} message"
    assert made.status_label.cget("text_color") == theme.status_text_color(kind)


def test_modm1_the_two_existing_screens_keep_their_signature(screen):
    """``set_status(text)`` and ``set_status(text, kind)``, positionally.

    The ~96 call sites already on `main` pass it both ways, so the adopted
    contract has to accept both or adoption is a rename.
    """
    made = screen()
    made.set_status("just the text")
    assert made.status_label.cget("text") == "just the text"
    assert made.status_label.cget("text_color") == theme.status_text_color("muted")
    made.set_status("text and kind", "error")
    assert made.status_label.cget("text_color") == theme.status_text_color("error")


def test_modm1_a_screen_with_no_notice_line_says_so(screen, caplog):
    """A notice before the line exists is logged, not swallowed (P2)."""
    made = screen()
    made.status_label = None
    with caplog.at_level("WARNING"):
        made.set_status("nowhere to put this", "error")
    assert "notice dropped" in caplog.text
    assert "nowhere to put this" in caplog.text


# ---------------------------------------------------------------- MOD-M2 ----


def test_modm2_no_screen_tells_the_user_through_the_platform():
    """Exactly the two allowed platform dialogs remain under ``src/``.

    An exact set, not a floor: a floor passes while a screen quietly goes
    back to a blocking dialog, which is the regression this guards.
    """
    assert _telling_calls() == PLATFORM_DIALOG_ALLOWLIST


def test_modm2_the_allowlist_describes_calls_that_exist():
    """Each allowlisted site is real, so the guard cannot pass on a typo.

    Without this, misspelling an entry would make the set comparison above
    fail open the moment the real call was also removed.
    """
    found = _telling_calls()
    for entry in PLATFORM_DIALOG_ALLOWLIST:
        assert entry in found, f"allowlisted site no longer exists: {entry}"


# ---------------------------------------------------------------- MOD-M3 ----


def test_modm3_an_error_survives_a_refresh(screen):
    """An error the user must act on is not timed out from under them."""
    made = screen()
    made.set_status("could not save the contact", "error")
    made.update()
    made.update_idletasks()
    assert made.status_label.cget("text") == "could not save the contact"
    assert getattr(made, "_status_dismiss_after", None) is None


@pytest.mark.parametrize("kind", sorted(TRANSIENT_KINDS))
def test_modm3_an_info_notice_clears_itself(screen, kind):
    """``info`` and ``success`` take themselves down."""
    settings = AppSettings()
    settings.notice_dismiss_ms = 1
    made = screen(settings)
    made.set_status("saved", kind)
    assert made.status_label.cget("text") == "saved"
    deadline = time.time() + 3
    while made.status_label.cget("text") and time.time() < deadline:
        made.update()
    assert made.status_label.cget("text") == "", (
        f"a {kind} notice stayed up past its delay")


def test_modm3_an_unknown_kind_persists(screen):
    """The safe direction: a kind nobody recognised stays visible."""
    settings = AppSettings()
    settings.notice_dismiss_ms = 1
    made = screen(settings)
    made.set_status("something happened", "chartreuse")
    for _ in range(5):
        made.update()
    assert made.status_label.cget("text") == "something happened"


def test_modm3_the_dismiss_delay_is_configurable(screen):
    """The delay is a setting, not a literal (P4).

    The shipped default is read from the class rather than restated, so
    changing it cannot leave this asserting a number the app does not have.
    """
    made = screen()
    assert made.dismiss_delay_ms() == AppSettings.notice_dismiss_ms
    settings = AppSettings()
    settings.notice_dismiss_ms = 250
    assert screen(settings).dismiss_delay_ms() == 250


@pytest.mark.parametrize("bad", [0, -1, "soon", None])
def test_modm3_an_unusable_delay_falls_back_to_the_default(screen, bad):
    """Zero would clear the notice in the frame it appeared in."""
    settings = AppSettings()
    settings.notice_dismiss_ms = bad
    assert screen(settings).dismiss_delay_ms() == AppSettings.notice_dismiss_ms


def test_modm3_a_later_notice_cancels_the_earlier_dismissal(screen):
    """A success followed by an error must not be cleared by the success.

    Without the cancel, the first notice's timer fires while the error is on
    screen and takes it down -- the one notice the user has to see.
    """
    settings = AppSettings()
    settings.notice_dismiss_ms = 1
    made = screen(settings)
    made.set_status("saved", "success")
    made.set_status("could not save", "error")
    deadline = time.time() + 1
    while time.time() < deadline:
        made.update()
    assert made.status_label.cget("text") == "could not save"


# ---------------------------------------------------------------- MOD-M4 ----


def test_modm4_a_notice_from_an_idle_callback_does_not_raise(screen):
    """The path PD-M12 died on: report from the callback a drop schedules.

    The platform dialog raised a bare ``TclError`` from here and took both
    write paths with it. A label already on screen cannot, and this is the
    test that would have caught it.
    """
    made = screen()
    raised = []
    made.winfo_toplevel().report_callback_exception = (
        lambda *exc: raised.append(exc))
    made.after_idle(lambda: made.set_status("dropped onto Saturday", "warning"))
    made.update()
    made.update_idletasks()
    assert not raised, f"a notice from an idle callback raised: {raised}"
    assert made.status_label.cget("text") == "dropped onto Saturday"


def test_modm4_a_notice_onto_a_destroyed_label_is_logged_not_raised(screen, caplog):
    """A screen torn down between the action and its report."""
    made = screen()
    made.status_label.destroy()
    with caplog.at_level("ERROR"):
        made.set_status("too late", "error")
    assert "notice could not be drawn" in caplog.text


# --------------------------------------------- the two screens that led ----


def test_modm1_the_scheduler_still_reports_on_its_own_line(tmp_path):
    """DragScheduleScreen's DRP-M3 behaviour is unchanged by adoption.

    It had this contract first; adopting the mixin must not move its line or
    change what a kind looks like.
    """
    from src.getmoredone.screens.drag_schedule import DragScheduleScreen

    root = ctk.CTk()
    root.withdraw()
    root.geometry("1400x800")
    db = DatabaseManager(str(tmp_path / "scheduler.db"))
    try:
        app = MagicMock()
        app.vps_manager.get_segment_colors_by_id.return_value = {}
        app.vps_manager.get_segment_color_map.return_value = {}
        made = DragScheduleScreen(root, db, app)
        made.pack(fill="both", expand=True)
        made.set_status("Saturday is outside your working week", "warning")
        assert made.status_label.cget("text") == (
            "Saturday is outside your working week")
        assert made.status_label.cget("text_color") == theme.status_text_color(
            "warning")
        assert isinstance(made, StatusNoticeMixin)
    finally:
        db.close()
        try:
            root.destroy()
        except Exception:
            pass


# ------------------------------------------- MOD-M2, the closing dialog ----


class _Dialog(StatusNoticeMixin, ctk.CTkToplevel):
    """A dialog that reports and then closes, like the 30 swept sites."""

    def __init__(self, master):
        super().__init__(master)
        self.withdraw()
        self.settings = AppSettings()
        self.create_status_line(row=0, column=0, sticky="ew")

    def save_and_close(self):
        self.notify_owner("Contact updated", "success")
        self.destroy()


def test_modm2_a_dialog_that_closes_reports_on_its_opener(screen):
    """The notice outlives the window that raised it.

    Written to the dialog's own label it would be destroyed in the frame it
    was drawn in, and the user would be told less than the modal told them.
    """
    owner = screen()
    dialog = _Dialog(owner)
    dialog.save_and_close()
    assert owner.status_label.cget("text") == "Contact updated"
    assert owner.status_label.cget("text_color") == theme.status_text_color(
        "success")


def test_modm2_the_walk_skips_an_ancestor_whose_line_has_gone(screen):
    """A torn-down line between the dialog and the screen is stepped over."""
    owner = screen()
    middle = _Dialog(owner)
    middle.status_label.destroy()
    leaf = _Dialog(middle)
    leaf.notify_owner("saved anyway", "success")
    assert owner.status_label.cget("text") == "saved anyway"


def test_modm2_an_orphan_notice_is_logged(caplog):
    """Nothing above to report on: logged with the message, never swallowed."""
    root = ctk.CTk()
    root.withdraw()
    try:
        orphan = _Dialog(root)
        with caplog.at_level("WARNING"):
            orphan.notify_owner("nobody will see this", "error")
        assert "notice dropped" in caplog.text
        assert "nobody will see this" in caplog.text
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_modm2_an_inline_list_is_capped():
    """A refusal that used a dialog body now fits a line.

    Tests:   src/getmoredone/screens/status_notice.py::inline_list
    """
    from src.getmoredone.screens.status_notice import INLINE_LIST_CAP, inline_list

    assert inline_list([]) == ""
    assert inline_list(["one"]) == "one"
    few = [f"n{i}" for i in range(INLINE_LIST_CAP)]
    assert inline_list(few) == ", ".join(few)
    assert "and 1 more" in inline_list(few + ["extra"])
    assert inline_list(few + ["extra"]).count(",") == INLINE_LIST_CAP - 1


def test_modm2_report_on_finds_the_nearest_line(screen):
    """``report_on`` serves callers that cannot carry the mixin at all."""
    from src.getmoredone.screens.status_notice import report_on

    owner = screen()
    assert report_on(owner, "from a module function", "warning") is True
    assert owner.status_label.cget("text") == "from a module function"


def test_modm2_report_on_says_when_nothing_took_it():
    """A plain widget with no line above it: the caller is told, not fooled."""
    from src.getmoredone.screens.status_notice import report_on

    root = ctk.CTk()
    root.withdraw()
    try:
        assert report_on(ctk.CTkFrame(root), "nowhere", "error") is False
    finally:
        try:
            root.destroy()
        except Exception:
            pass


# ------------------------------------------------ MOD-M1/M2 review round ----
#
# One guard per finding from the pre-push sweep (learning-qa and /code-review
# converged on four of them). Each names the src line it depends on, and each
# was mutation-checked: that line deleted or inverted, this test run, red
# confirmed, the file restored with the verbatim original.


def _notice_label_providers():
    """Class name -> True for every class under ``src/`` that builds a line.

    "Builds a line" is: calls ``create_status_line``, or assigns the attribute
    its ``NOTICE_LABEL_ATTR`` names. Resolved transitively through base-class
    *names*, which is enough here because no two screen classes share a name.

    A mixin gets its line from its *sibling* in the concrete class's MRO, not
    from its own bases, so one that builds no line itself counts as satisfied
    when every class that mixes it in has one. ``PlanWeekViewMixin`` and
    ``ItemEditorContactsMixin`` are that case; a mixin nobody mixes in is not.
    """
    classes = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            attr = "status_label"
            builds = False
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Assign)
                        and any(isinstance(t, ast.Name)
                                and t.id == "NOTICE_LABEL_ATTR"
                                for t in sub.targets)
                        and isinstance(sub.value, ast.Constant)):
                    attr = sub.value.value
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "create_status_line"):
                    builds = True
                if (isinstance(sub, ast.Attribute) and sub.attr == attr
                        and isinstance(sub.value, ast.Name)
                        and sub.value.id == "self"
                        and isinstance(sub.ctx, ast.Store)):
                    builds = True
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            classes[node.name] = (builds, bases)

    users = {}
    for name, (_builds, bases) in classes.items():
        for base in bases:
            users.setdefault(base, []).append(name)

    def has_line(name, seen=()):
        if name in seen or name not in classes:
            return False
        builds, bases = classes[name]
        if builds or any(has_line(b, seen + (name,)) for b in bases):
            return True
        mixed_into = users.get(name, [])
        return bool(mixed_into) and all(
            has_line(user, seen + (name,)) for user in mixed_into)

    return {name: has_line(name) for name in classes}


def _classes_calling(attr):
    """Every class under ``src/`` with a ``self.<attr>(...)`` call in it."""
    found = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == attr
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == "self"):
                    found.setdefault(node.name, f"{rel}:{sub.lineno}")
    return found


def test_modm1_every_class_that_reports_has_a_line_to_report_on():
    """The check the first 30 guards did not make, and the sweep needed.

    Both high findings were a class calling into the notice contract with
    nowhere for the notice to land, and the whole suite stayed green: the
    MOD-M2 exact-set guard cannot see it, because the dialog really is gone --
    the message just goes nowhere. ``WeekTacticActionsPanel`` reached for
    ``notify_owner`` when it had a line of its own and its owner had none, and
    ``ManageContactsScreen`` opened a reporting dialog with no line anywhere
    above it. This is statically decidable, so it is asserted rather than
    walked.
    """
    providers = _notice_label_providers()
    missing = {name: where
               for name, where in _classes_calling("set_status").items()
               if not providers.get(name, False)}
    assert missing == {}, (
        "these classes call self.set_status with no notice label to draw on; "
        "they need create_status_line, or the call belongs on another object: "
        f"{missing}"
    )


def test_modm1_every_opener_of_a_reporting_dialog_has_a_line():
    """``notify_owner`` walks up, so the *opener* is what must carry a line.

    ``EditContactDialog`` is opened from two places. One had a line and one
    did not, so Add / Update / Delete / Deactivate and "That contact no longer
    exists." were shown to nobody whenever contacts were managed from the
    Contacts tab -- the generic P5 shape, the dialog swept and one of its two
    openers left behind.
    """
    providers = _notice_label_providers()
    reporters = set(_classes_calling("notify_owner"))
    assert reporters, "nothing calls notify_owner; this guard stopped looking"

    bad = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Name)
                        and sub.func.id in reporters
                        and not providers.get(node.name, False)):
                    bad.setdefault(f"{node.name} -> {sub.func.id}",
                                   f"{rel}:{sub.lineno}")
    assert bad == {}, (
        "these classes open a dialog that reports through notify_owner but "
        f"have no notice line for it to walk up to: {bad}"
    )


def test_modm3_a_notice_carrying_required_action_can_be_made_to_persist(screen):
    """``persist=True`` keeps a success notice up.

    MOD-M3's auto-clear was applied blanket to ``success``, which retrofitted
    a six-second lifetime onto notices that already existed on the Plan
    screens -- including "export that day again to remove it from Google
    Calendar", an instruction, and "removed 4 of 6 blocks", the partial
    outcome the house rules require to be surfaced. Green is the right colour
    for both; six seconds is not the right lifetime.
    """
    made = screen(AppSettings())
    made.settings.notice_dismiss_ms = 40

    made.set_status("Clear Day: removed 4 of 6 blocks", "success",
                    persist=True)
    for _ in range(30):
        made.update()
        time.sleep(0.005)
    assert "4 of 6" in made.notice_label().cget("text"), (
        "evidence that erases itself after six seconds is not surfaced"
    )

    made.set_status("Moved it", "success")
    for _ in range(30):
        made.update()
        time.sleep(0.005)
    assert made.notice_label().cget("text") == "", (
        "persist must not be the default; a bare confirmation still clears"
    )


def test_modm3_destroy_cancels_a_pending_dismissal(screen):
    """A dismissal must not outlive the widget it targets.

    ``utils/after_tracker.py`` exists for exactly this (P30), and
    ``TrackedAfterMixin`` does not cover it because it does not override
    ``after``. Left untracked, a success notice followed by a sidebar click
    within ``notice_dismiss_ms`` fired ``clear_status`` on a destroyed widget
    and wrote an ERROR-level traceback to ``app.log`` for ordinary navigation
    -- noise in the one file the MOD-M7 walk asks the user to read.
    """
    made = screen(AppSettings())
    made.settings.notice_dismiss_ms = 50
    made.set_status("Saved.", "success")
    assert made._status_dismiss_after, "nothing was scheduled to cancel"

    made.destroy()
    assert made._status_dismiss_after is None, (
        "the timer still points at a widget that has gone"
    )


def test_modm2_report_on_does_not_claim_a_write_that_did_not_land(screen):
    """``report_on`` must answer with ``set_status``'s result, not its own.

    ``set_status`` swallows a failed ``label.configure`` on purpose (MOD-M4).
    Returning True regardless meant a half-torn-down ancestor took the notice
    as far as every caller could tell: ``notify_week_collision`` recorded
    ``shown = True``, skipped its warning, and told its caller a refused week
    had been reported (P6 -- a status field is worth nothing unchecked).
    """
    from src.getmoredone.screens.status_notice import report_on

    made = screen()

    class _Deaf:
        """A line that exists and refuses the write, as a dying screen does."""

        def __init__(self, label):
            self.status_label = label
            self.master = None

        def set_status(self, text, kind="muted"):
            return False

    deaf = _Deaf(made.notice_label())
    assert report_on(deaf, "a refused week", "warning") is False, (
        "a notice nobody drew must not be reported as delivered"
    )

    deaf.master = made
    assert report_on(deaf, "a refused week", "warning") is True
    assert "refused week" in made.notice_label().cget("text"), (
        "the walk must carry on past a line that refused it"
    )


SHARED_LABEL_SCREENS = [
    "weekly_items.py",
    "ape_assignment.py",
    "ape_period_view.py",
    "annual_vision_segments.py",
]


@pytest.mark.parametrize("name", SHARED_LABEL_SCREENS)
def test_modm1_a_shared_notice_line_has_exactly_one_writer(name):
    """No ``self.status_label.configure`` left on a screen that also reports.

    These four were given the mixin over a ``status_label`` that already
    carried their own standing content. ``set_status`` sets ``text_color`` and
    a raw ``configure(text=...)`` does not reset it, so a neutral count
    summary written after an error notice rendered in the error colour and
    stayed that way. Exact count, not a floor: a floor hides the narrowing it
    was written to catch.
    """
    path = SRC / "getmoredone" / "screens" / name
    tree = ast.parse(path.read_text(encoding="utf-8"))
    raw = [node.lineno for node in ast.walk(tree)
           if isinstance(node, ast.Call)
           and isinstance(node.func, ast.Attribute)
           and node.func.attr == "configure"
           and isinstance(node.func.value, ast.Attribute)
           and node.func.value.attr == "status_label"
           and isinstance(node.func.value.value, ast.Name)
           and node.func.value.value.id == "self"]
    assert len(raw) == 0, (
        f"{name} writes its own notice line directly at lines {raw}; route it "
        "through set_status so the colour and any pending dismissal are reset"
    )


def test_modm1_a_muted_write_takes_the_previous_colour_back_off(screen):
    """The behaviour the guard above protects, asserted once on the contract."""
    made = screen()
    made.set_status("Select a weekly tactic on the right first.", "warning")
    assert made.notice_label().cget("text_color") == theme.status_text_color(
        "warning")

    made.set_status("3 month item(s) on left, 2 weekly tactic(s) on right",
                    "muted")
    assert made.notice_label().cget("text_color") == theme.status_text_color(
        "muted"), "a neutral summary kept the last notice's colour"


DESTROY_AND_REPORT_FILES = [
    "vps_editors.py",
    "vps_segment_editor.py",
    "edit_contact.py",
]


@pytest.mark.parametrize("name", DESTROY_AND_REPORT_FILES)
def test_modm2_a_dialog_does_not_close_inside_the_try_that_reports_for_it(name):
    """``self.destroy()`` must not sit in a ``try`` whose handler reports here.

    ``messagebox.showerror`` did not need the dialog to still exist; a label on
    the dialog does. With ``destroy()`` inside the ``try``, a TclError out of
    teardown after a save had already succeeded reported "Could not save ..."
    onto a widget on its way out: a false failure, and an invisible one.
    """
    path = SRC / "getmoredone" / "screens" / name
    tree = ast.parse(path.read_text(encoding="utf-8"))

    def calls(nodes, attr):
        return any(isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Attribute)
                   and n.func.attr == attr
                   and isinstance(n.func.value, ast.Name)
                   and n.func.value.id == "self"
                   for body in nodes for n in ast.walk(body))

    offenders = [node.lineno for node in ast.walk(tree)
                 if isinstance(node, ast.Try)
                 and calls(node.body, "destroy")
                 and any(calls(h.body, "set_status") for h in node.handlers)]
    assert offenders == [], (
        f"{name} closes the dialog inside a try whose except reports on it, "
        f"at lines {offenders}; move destroy() after the except"
    )
