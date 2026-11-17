"""The Projects screen's right-hand panel after the LRP layout change.

Spec: docs/spec_2026-11-16_status_vocabulary.md

LRP-A1  the "Next Step:" line is gone from the detail header
LRP-A2  the item count sits on the "Action Items" line, left-justified
LRP-A3  Select All is the unlabelled box in the column header, column 0
LRP-A4  the Project Notes section starts collapsed
LRP-C1  three status checkboxes on the header line, Open ticked by default
"""

from types import SimpleNamespace

import pytest

from src.getmoredone.db_manager import DatabaseManager
from src.getmoredone.models import (
    ActionItem, ProjectBoard, ProjectBoardLink, ProjectBoardStatus, Status)
from src.getmoredone.theme import status_text_color

ctk = pytest.importorskip("customtkinter")

from src.getmoredone.screens.project_boards import (  # noqa: E402
    ProjectBoardEditorDialog, ProjectBoardsScreen)


# ------------------------------------------------------------------- fixtures

@pytest.fixture
def db_manager(tmp_path):
    manager = DatabaseManager(str(tmp_path / "status_filters.db"))
    yield manager
    manager.close()


@pytest.fixture
def screen(db_manager):
    """A screen on a board holding one item of each status."""
    try:
        root = ctk.CTk()
    except Exception as exc:  # pragma: no cover - headless CI guard
        pytest.skip(f"No GUI display available: {exc}")
    root.withdraw()

    board_id = db_manager.create_project_board(ProjectBoard(title="Mixed"))
    ids = {}
    for status in Status.ALL:
        item_id = db_manager.create_action_item(
            ActionItem(who="me", title=f"Item {status}", status=status))
        db_manager.link_action_item_to_project_board(board_id, item_id)
        ids[status] = item_id

    board = ProjectBoardsScreen(
        root, db_manager, SimpleNamespace(vps_manager=None))
    board.selected_board_id = board_id
    board.refresh()
    root.update_idletasks()
    yield board, board_id, ids, root
    root.destroy()


# -------------------------------------------------------------------- helpers

def _descendants(widget, kind):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, kind):
            found.append(child)
        found.extend(_descendants(child, kind))
    return found


def _at_grid_row(parent, row):
    """The direct children of ``parent`` gridded on ``row``."""
    return [child for child in parent.winfo_children()
            if child.grid_info() and int(child.grid_info()["row"]) == row]


def _items_header(screen_obj):
    """The frame holding "Action Items", the count and the status boxes."""
    for frame in _at_grid_row(screen_obj.items_frame, 3):
        texts = [w.cget("text") for w in _descendants(frame, ctk.CTkLabel)]
        if "Action Items" in texts:
            return frame
    raise AssertionError("no Action Items header frame on row 3")


def _column_header(screen_obj):
    """The column-heading strip, gridded on row 4 of the items frame."""
    rows = _at_grid_row(screen_obj.items_frame, 4)
    assert len(rows) == 1, rows
    return rows[0]


# --------------------------------------------------------------------- LRP-A1

def test_lrpa1_next_step_is_gone_from_the_detail_header(screen, db_manager):
    """The "Next Step:" meta line no longer appears, even when set."""
    board_obj, board_id, _ids, root = screen
    board = db_manager.get_project_board(board_id)
    board.next_step = "Call the supplier"
    db_manager.update_project_board(board)
    board_obj.refresh()
    root.update_idletasks()

    meta = board_obj.detail_meta.cget("text")
    assert "Next Step" not in meta, meta
    assert "Call the supplier" not in meta, meta


# --------------------------------------------------------------------- LRP-A2

def test_lrpa2_count_sits_on_the_action_items_line(screen):
    """The count is on the heading's own grid row, to its right, left-stuck."""
    board_obj, _board_id, _ids, _root = screen
    header = _items_header(board_obj)

    labels = {w.cget("text"): w for w in _descendants(header, ctk.CTkLabel)}
    title = labels["Action Items"]
    count = next(w for text, w in labels.items() if text.endswith("item")
                 or text.endswith("items") or " shown" in text)

    assert int(count.grid_info()["row"]) == int(title.grid_info()["row"])
    assert int(count.grid_info()["column"]) > int(title.grid_info()["column"])
    assert "w" in str(count.grid_info()["sticky"])
    assert "e" not in str(count.grid_info()["sticky"])


def test_lrpa2_count_names_the_number_of_visible_items(screen):
    """One item per status, Open alone ticked, so the count reads 1 of 3."""
    board_obj, _board_id, _ids, _root = screen
    header = _items_header(board_obj)
    texts = [w.cget("text") for w in _descendants(header, ctk.CTkLabel)]
    assert "1 shown • 2 hidden" in texts, texts


# --------------------------------------------------------------------- LRP-A3

def test_lrpa3_select_all_is_the_unlabelled_box_in_the_column_header(screen):
    """It is in the heading strip, column 0, with no text of its own."""
    board_obj, _board_id, _ids, _root = screen
    header = _column_header(board_obj)

    boxes = _descendants(header, ctk.CTkCheckBox)
    assert len(boxes) == 1, [b.cget("text") for b in boxes]
    assert boxes[0].cget("text") == ""
    assert int(boxes[0].grid_info()["column"]) == 0

    # And it is still the control that drives the selection.
    board_obj.check_all_var.set(True)
    board_obj._on_check_all_changed()
    assert board_obj.selected_item_ids == set(board_obj.item_checkbox_vars)


def test_lrpa3_select_all_sits_in_the_rows_checkbox_column(screen):
    """Column 0 in the header is column 0 in every row -- they line up."""
    board_obj, _board_id, _ids, _root = screen
    header_box = _descendants(_column_header(board_obj), ctk.CTkCheckBox)[0]

    row_columns = set()
    for row in board_obj.items_frame.winfo_children():
        if not row.grid_info() or int(row.grid_info()["row"]) < 5:
            continue
        for box in _descendants(row, ctk.CTkCheckBox):
            row_columns.add(int(box.grid_info()["column"]))

    assert row_columns == {int(header_box.grid_info()["column"])}


def test_lrpa3_no_labelled_select_all_remains(screen):
    """The old labelled row is gone from the panel entirely."""
    board_obj, _board_id, _ids, _root = screen
    texts = [w.cget("text")
             for w in _descendants(board_obj.items_frame, ctk.CTkCheckBox)]
    assert "Select All" not in texts, texts


# --------------------------------------------------------------------- LRP-A4

def test_lrpa4_notes_section_starts_collapsed(screen, db_manager):
    """The header renders; the note rows do not."""
    board_obj, board_id, _ids, root = screen
    db_manager.add_project_board_link(
        ProjectBoardLink(project_board_id=board_id, url="x://", label="A note"))
    board_obj.load_notes()
    root.update_idletasks()

    assert board_obj.notes_expanded is False
    labels = [w.cget("text")
              for w in _descendants(board_obj.notes_links_frame, ctk.CTkLabel)]
    assert "Project Notes" in labels
    assert not any("A note" in text for text in labels), labels


def test_lrpa4_toggle_opens_and_closes_the_notes_section(screen, db_manager):
    """The disclosure button shows the rows, and hides them again."""
    board_obj, board_id, _ids, root = screen
    db_manager.add_project_board_link(
        ProjectBoardLink(project_board_id=board_id, url="x://", label="A note"))
    board_obj.load_notes()
    root.update_idletasks()

    board_obj._toggle_notes_section()
    root.update_idletasks()
    labels = [w.cget("text")
              for w in _descendants(board_obj.notes_links_frame, ctk.CTkLabel)]
    assert any("A note" in text for text in labels), labels

    board_obj._toggle_notes_section()
    root.update_idletasks()
    labels = [w.cget("text")
              for w in _descendants(board_obj.notes_links_frame, ctk.CTkLabel)]
    assert not any("A note" in text for text in labels), labels


def test_lrpa4_collapsed_header_still_counts_the_notes(screen, db_manager):
    """Collapsing hides the rows, not the fact that notes are filed."""
    board_obj, board_id, _ids, root = screen
    for n in range(2):
        db_manager.add_project_board_link(
            ProjectBoardLink(project_board_id=board_id, url=f"x://{n}",
                             label=f"Note {n}"))
    board_obj.load_notes()
    root.update_idletasks()

    assert board_obj.notes_expanded is False
    assert "2 notes shown" in board_obj.notes_count_label.cget("text")


# --------------------------------------------------------------------- LRP-C1

def test_lrpc1_three_boxes_on_the_header_line(screen):
    """Open, Completed, Canceled, in order, all left-justified.

    These are the action item statuses. The project's own four words
    (SVU-M1) are not offered here -- an item is never "pending".
    """
    board_obj, _board_id, _ids, _root = screen
    header = _items_header(board_obj)

    boxes = _descendants(header, ctk.CTkCheckBox)
    assert [b.cget("text") for b in boxes] == [
        "Open", "Completed", "Canceled"]

    title_row = int(next(w for w in _descendants(header, ctk.CTkLabel)
                         if w.cget("text") == "Action Items"
                         ).grid_info()["row"])
    for box in boxes:
        assert int(box.grid_info()["row"]) == title_row, box.cget("text")
        assert "w" in str(box.grid_info()["sticky"]), box.cget("text")
        assert "e" not in str(box.grid_info()["sticky"]), box.cget("text")


def test_lrpc1_open_is_the_only_default(screen):
    """Opening a project shows its open work and nothing else."""
    board_obj, _board_id, ids, _root = screen
    assert board_obj.item_status_filter_vars[Status.OPEN].get() is True
    for status in (Status.COMPLETED, Status.CANCELED):
        assert board_obj.item_status_filter_vars[status].get() is False, status

    assert set(board_obj.item_checkbox_vars) == {ids[Status.OPEN]}


@pytest.mark.parametrize("status", [Status.COMPLETED, Status.CANCELED])
def test_lrpc1_ticking_a_box_shows_that_status(screen, status):
    """Each box brings in its own status and no other."""
    board_obj, _board_id, ids, root = screen
    board_obj.item_status_filter_vars[status].set(True)
    board_obj._render_detail()
    root.update_idletasks()

    assert set(board_obj.item_checkbox_vars) == {ids[Status.OPEN],
                                                 ids[status]}


def test_lrpc1_unticking_every_box_shows_nothing(screen):
    """The controls are the whole filter: there is no hidden fallback."""
    board_obj, _board_id, _ids, root = screen
    board_obj.item_status_filter_vars[Status.OPEN].set(False)
    board_obj._render_detail()
    root.update_idletasks()

    assert board_obj.item_checkbox_vars == {}


def test_lrpc1_unknown_status_is_shown(screen, db_manager):
    """P2 -- a status the boxes do not cover is surfaced, not dropped."""
    board_obj, board_id, ids, root = screen
    item_id = db_manager.create_action_item(
        ActionItem(who="me", title="From an older build"))
    db_manager.link_action_item_to_project_board(board_id, item_id)
    db_manager.db.conn.execute(
        "UPDATE action_items SET status = 'deferred' WHERE id = ?", (item_id,))
    db_manager.db.conn.commit()

    board_obj._render_detail()
    root.update_idletasks()
    assert item_id in board_obj.item_checkbox_vars


def test_lrpc1_completed_box_also_filters_the_notes(screen, db_manager):
    """One pair of controls for both lists, as the shared toggle was."""
    board_obj, board_id, _ids, root = screen
    db_manager.add_project_board_link(
        ProjectBoardLink(project_board_id=board_id, url="c://",
                         label="Done note", status=Status.COMPLETED))
    board_obj.notes_expanded = True
    board_obj.load_notes()
    root.update_idletasks()
    labels = [w.cget("text")
              for w in _descendants(board_obj.notes_links_frame, ctk.CTkLabel)]
    assert not any("Done note" in text for text in labels), labels

    board_obj.item_status_filter_vars[Status.COMPLETED].set(True)
    board_obj.load_notes()
    root.update_idletasks()
    labels = [w.cget("text")
              for w in _descendants(board_obj.notes_links_frame, ctk.CTkLabel)]
    assert any("Done note" in text for text in labels), labels


# ---------------------------------------------------------- SVU-M1, the editor

def test_svum1_project_editor_offers_all_four_statuses(db_manager):
    """The project's Status dropdown was missing Canceled; now it is there."""
    from src.getmoredone.screens.project_boards import ProjectBoardEditorDialog

    try:
        root = ctk.CTk()
    except Exception as exc:  # pragma: no cover - headless CI guard
        pytest.skip(f"No GUI display available: {exc}")
    root.withdraw()
    dialog = ProjectBoardEditorDialog(root, db_manager)
    try:
        combos = _descendants(dialog, ctk.CTkComboBox)
        status_box = next(
            box for box in combos
            if str(box.cget("variable")) == str(dialog.status_var))
        assert list(status_box.cget("values")) == [
            "active", "pending", "canceled", "completed"]
    finally:
        dialog.destroy()
        root.destroy()


# --------------------------------------------------------------------- SVU-M3

def test_svum3_an_unknown_status_is_refused_without_a_redraw(
        screen, monkeypatch):
    """The two reasons a status change does not land need different answers.

    An unknown status changed nothing, so there is nothing to redraw. The
    notice names the vocabulary, as `validation.py`'s messages do -- a notice
    that only says the attempt failed leaves the user without the one fact
    that would let them fix it. Reported on this screen's own notice line:
    MOD-M2 leaves only two platform dialogs in the app, both for a failure
    with no screen to put a notice on, and this is not one.
    """
    screen_obj, board_id, _ids, _root = screen
    refreshed = []
    monkeypatch.setattr(screen_obj, "refresh", lambda: refreshed.append(1))

    screen_obj.set_board_status(board_id, "open")

    assert screen_obj.status_label.cget("text") == (
        "Status must be one of: active, pending, canceled, completed.")
    assert (screen_obj.status_label.cget("text_color")
            == status_text_color("error"))
    assert not refreshed, "nothing changed, so there is nothing to redraw"


def test_svum3_a_board_deleted_elsewhere_is_refreshed_away(
        screen, monkeypatch):
    """The other reason: a real status, and no row to apply it to.

    The card belongs to a board another screen deleted. Leaving it on the
    board means every further click on it fails identically, with a notice
    that describes a project the user can still see.
    """
    screen_obj, _board_id, _ids, _root = screen
    refreshed = []
    monkeypatch.setattr(screen_obj, "refresh", lambda: refreshed.append(1))

    screen_obj.set_board_status("no-such-board", ProjectBoardStatus.COMPLETED)

    assert screen_obj.status_label.cget("text") == (
        "That project no longer exists. Board refreshed.")
    assert (screen_obj.status_label.cget("text_color")
            == status_text_color("error"))
    assert refreshed, "the ghost card has to go, or the next click repeats this"


def _editor_stub(db_manager, board, typed):
    """The editor's save path with everything but Status held constant."""
    return SimpleNamespace(
        board=board,
        title_var=SimpleNamespace(get=lambda: "Typed"),
        ape_var=SimpleNamespace(get=lambda: "label"),
        ape_label_to_id={"label": "ape-1"},
        notices=[],
        priority_var=SimpleNamespace(get=lambda: ""),
        status_var=SimpleNamespace(get=lambda: typed),
        next_step_var=SimpleNamespace(get=lambda: ""),
        notes_box=SimpleNamespace(get=lambda *a: ""),
        start_date_var=SimpleNamespace(get=lambda: ""),
        end_date_var=SimpleNamespace(get=lambda: ""),
        _extract_factor_value=lambda _v: None,
        result=None,
        destroy=lambda: None,
    )


def test_svum3_a_typed_status_is_refused_not_corrected(db_manager):
    """The editor's Status combobox is free-text and the writers are ungated.

    An unknown value either raises IntegrityError into Tk's callback handler
    or, on a database the migration leaves CHECK-less, stores and drops the
    board out of every status filter -- SVU-M3's own failure by another door.

    It is refused, the way the invalid Annual Plan Element three lines above
    it is. A silent fallback to `active` was worse than either: it moved the
    project into the active group and discarded `completed_at` below, and said
    nothing.
    """
    board = ProjectBoard(title="Typed", status=ProjectBoardStatus.COMPLETED)
    board.completed_at = "2026-11-17T09:00:00"
    db_manager.create_project_board(board)
    stub = _editor_stub(db_manager, db_manager.get_project_board(board.id),
                        "actve")
    stub.set_status = lambda text, kind=None: stub.notices.append((text, kind))

    ProjectBoardEditorDialog.save(stub)

    assert stub.result is None, "a refused save must not produce a board"
    assert stub.notices == [
        ("Status must be one of: active, pending, canceled, completed.",
         "error")]
    stored = db_manager.get_project_board(board.id)
    assert stored.status == ProjectBoardStatus.COMPLETED
    assert stored.completed_at == "2026-11-17T09:00:00", (
        "the clamp used to fall through to active and wipe this")


def test_svum3_a_capitalised_status_is_accepted(db_manager):
    """`Completed` is the capitalisation the board's buttons and the guide use.

    The dropdown's own values are lowercase, so the two spellings meet in this
    box. Folding case accepts it rather than refusing a user who typed what
    the rest of the UI shows them.
    """
    board = ProjectBoard(title="Typed")
    db_manager.create_project_board(board)
    stub = _editor_stub(db_manager, db_manager.get_project_board(board.id),
                        " Completed ")
    stub.set_status = lambda text, kind=None: stub.notices.append((text, kind))

    ProjectBoardEditorDialog.save(stub)

    assert stub.notices == [], stub.notices
    assert stub.result is not None, "the dialog produced no board"
    assert stub.result.status == ProjectBoardStatus.COMPLETED
    assert stub.result.completed_at, "a completed project is stamped"


def test_svum3_the_toolbar_offers_show_canceled(screen):
    """The way back for a canceled project."""
    screen_obj, _board_id, _ids, _root = screen
    labels = {box.cget("text")
              for box in _descendants(screen_obj, ctk.CTkCheckBox)}
    assert "Show Canceled" in labels, sorted(labels)
    assert screen_obj.show_canceled_var.get() is False


def test_lrpc1_the_empty_notes_message_names_a_control_that_exists(
        screen, db_manager):
    """LRP-C1 replaced the `Show Completed` box the old message named."""
    screen_obj, board_id, _ids, root = screen
    db_manager.add_project_board_link(ProjectBoardLink(
        project_board_id=board_id, url="note://done", label="Done",
        link_type="note", status=Status.COMPLETED))
    screen_obj.notes_expanded = True
    screen_obj.refresh()
    root.update_idletasks()

    texts = [label.cget("text")
             for label in _descendants(screen_obj, ctk.CTkLabel)]
    empty = [text for text in texts if "note(s) completed" in text]
    assert empty, texts
    assert "Show Completed" not in empty[0]
    assert "'Completed' on the Action Items line" in empty[0]
