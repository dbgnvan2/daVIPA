"""WTP — a Weekly Tactic acts as the parent of the Action Items linked to it.

Purpose: hold the one definition of parenthood to one answer across the object
         reader (``weekly_tactic.parent_of``) and the SQL reader
         (``DatabaseManager.get_children``), and keep a week-filed item out of
         the tree's top level without hiding one whose tactic is gone.
Spec:    docs/spec_2026-11-08_weekly_tactic_as_parent.md
Tests:   this file

Every ``DatabaseManager`` here comes from ``make_vps(tmp_path)``, so no test
touches the user's real application database.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Self-contained path bootstrap, for the same reason test_ape_week_actions.py
# carries one: tests/test_ci_contract.py imports every test file with the repo
# root stripped from sys.path, and this file cannot rely on another having put
# it back.
_ROOT = Path(__file__).resolve().parents[1]
for _entry in (str(_ROOT), str(_ROOT / "src")):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest  # noqa: E402

import customtkinter as ctk  # noqa: E402

from src.getmoredone.models import ActionItem, Status  # noqa: E402
from src.getmoredone.screens.hierarchical import HierarchicalScreen  # noqa: E402
from src.getmoredone.weekly_tactic import parent_of, tactic_of  # noqa: E402
from tests.weekly_tactic_fixtures import (  # noqa: E402
    make_daily_item,
    make_vps,
    make_week_item,
    seed_ape,
)


# ---------------------------------------------------------------- WTP-M1 ----
# The object-level predicate. No database: it reads an ActionItem's columns.


def test_wtpm11_parent_id_alone():
    """WTP-M1.1 — a plain subtask's parent is its ``parent_id``."""
    item = ActionItem(who="Self", title="Subtask", parent_id="X")
    assert parent_of(item) == "X"


def test_wtpm12_tactic_alone():
    """WTP-M1.2 — a week-filed item's parent is its Weekly Tactic.

    This is the whole request: before WTP, this returned nothing because no
    reader looked at ``weekly_tactic_id``.
    """
    item = ActionItem(who="Self", title="Week-filed", weekly_tactic_id="T")
    assert parent_of(item) == "T"


def test_wtpm13_parent_id_wins_over_tactic():
    """WTP-M1.3 / WTP-D3 — both links set means one parent, the nearer one.

    An item that is a subtask of X *and* week-filed to T belongs under X. The
    alternative is the same work in two places in one tree, with ``(N sub)``
    counts that do not sum.
    """
    item = ActionItem(who="Self", title="Both", parent_id="X", weekly_tactic_id="T")
    assert parent_of(item) == "X"


def test_wtpm14_empty_string_is_no_parent():
    """WTP-M1.4 — a blank column is no link, not a link to ""."""
    assert parent_of(ActionItem(who="Self", title="Blank", parent_id="", weekly_tactic_id="")) is None
    # A blank parent_id must fall through to the tactic rather than win.
    assert parent_of(ActionItem(who="Self", title="Blank", parent_id="", weekly_tactic_id="T")) == "T"


def test_wtpm15_none_item():
    """WTP-M1.5 — None in, None out, as ``tactic_of`` already does."""
    assert parent_of(None) is None


def test_wtpm16_tactic_of_unchanged():
    """WTP-M1.6 / WTP-D5 — ``tactic_of`` still reads one column.

    WT-INV6 turns on it: an item with no Weekly Tactic is never modified by a
    re-filing rule. If ``parent_of``'s arrival had widened ``tactic_of``, every
    ``parent_id``-only child of a tactic would silently become week-filed and
    start cascading when its dates moved.
    """
    parent_id_only = ActionItem(who="Self", title="AWA-A1 shape", parent_id="T")
    assert tactic_of(parent_id_only) is None
    assert parent_of(parent_id_only) == "T"


def test_wtpm17_a_week_row_has_no_parent():
    """WTP-M1.7 — a Weekly Tactic is a root, whatever its columns hold.

    A tactic's lineage is its Annual Plan Element, which is not an Action Item.
    Were a week row a child here, it would still be excluded from
    ``get_children`` by ``LINK_PREDICATE_SQL``'s ``item_type != 'week'`` — the
    two definitions of "child" disagreeing, which is the failure AWA-A3
    recorded.
    """
    tactic = ActionItem(who="Self", title="Week", item_type="week", parent_id="X",
                        weekly_tactic_id="T")
    assert parent_of(tactic) is None


# ---------------------------------------------------------------- WTP-M2 ----


def test_wtpm21_tactic_children_by_tactic_column(tmp_path):
    """WTP-M2.1 — ``get_children`` of a tactic returns its week-filed items."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)

        children = vps.db_manager.get_children(tactic.id)

        assert [c.id for c in children] == [child.id]
    finally:
        vps.close()


def test_wtpm22_parent_id_only_child_returned_once(tmp_path):
    """WTP-M2.2 — the AWA-A1 shape is still a child, and counted once.

    ``weekly_items.py``'s Add Action Item writes ``parent_id`` and leaves
    ``weekly_tactic_id`` NULL. That button is unfixed (AWA-A1), so the reader
    has to cover both shapes — and must not return an item twice when a future
    fix sets both columns.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        legacy = make_daily_item(vps, title="Added from APE Week Assignment",
                                 parent_id=tactic.id)
        both = make_daily_item(vps, title="Both columns, same tactic",
                               parent_id=tactic.id,
                               weekly_tactic_id=tactic.id, refile=False)

        ids = [c.id for c in vps.db_manager.get_children(tactic.id)]

        assert sorted(ids) == sorted([legacy.id, both.id])
        assert len(ids) == len(set(ids))
    finally:
        vps.close()


def test_wtpm23_subtask_stays_under_its_subtask_parent(tmp_path):
    """WTP-M2.3 / WTP-D3 — week-filed *and* a subtask means one place.

    The tree reader puts it under its subtask parent. The panel reader still
    lists it under the week, because that answers a different question
    (WTP-D4) — asserted here so the difference is deliberate and visible.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        outer = make_daily_item(vps, title="Ship the series")
        nested = make_daily_item(vps, title="Draft part two",
                                 parent_id=outer.id,
                                 weekly_tactic_id=tactic.id, refile=False)

        assert [c.id for c in vps.db_manager.get_children(tactic.id)] == []
        assert [c.id for c in vps.db_manager.get_children(outer.id)] == [nested.id]

        panel = vps.get_action_items_for_weekly_tactic(tactic.id)
        assert nested.id in [p.id for p in panel]
    finally:
        vps.close()


def _all_link_shapes(vps):
    """One fixture holding every link shape, for the agreement test.

    Returns ``(ids_by_label, tactic_id, outer_id)``.
    """
    ape = seed_ape(vps)
    tactic = make_week_item(vps, ape, title="W1")
    second = make_week_item(vps, ape, start="2026-03-02", due="2026-03-08",
                            title="W2")
    outer = make_daily_item(vps, title="Ordinary parent")
    shapes = {
        "tactic_only": make_daily_item(
            vps, title="tactic only", weekly_tactic_id=tactic.id).id,
        "parent_id_only": make_daily_item(
            vps, title="parent_id only", parent_id=tactic.id).id,
        "both_same": make_daily_item(
            vps, title="both, same tactic", parent_id=tactic.id,
            weekly_tactic_id=tactic.id, refile=False).id,
        "both_split": make_daily_item(
            vps, title="subtask and week-filed", parent_id=outer.id,
            weekly_tactic_id=tactic.id, refile=False).id,
        "subtask": make_daily_item(
            vps, title="plain subtask", parent_id=outer.id).id,
        "unlinked": make_daily_item(vps, title="no links at all").id,
    }
    return shapes, tactic.id, second.id, outer.id


def test_wtpm24_sql_and_object_readers_agree(tmp_path):
    """WTP-M2.4 — ``get_children`` and ``parent_of`` return the same tree.

    The adversarial case (P7): all six link shapes in one database, including
    the two that "look right but are wrong" — both columns on the same tactic,
    and both columns split between a subtask parent and a tactic. AWA-A3
    recorded three readers disagreeing about what a child is; this is the test
    that keeps two of them from drifting apart again.
    """
    vps = make_vps(tmp_path)
    try:
        _all_link_shapes(vps)
        dbm = vps.db_manager

        rows = dbm.db.conn.execute("SELECT id FROM action_items").fetchall()
        every_id = [row["id"] for row in rows]

        expected = {}
        for item_id in every_id:
            item = dbm.get_action_item(item_id)
            parent = parent_of(item)
            if parent and dbm.get_action_item(parent) is not None:
                expected.setdefault(parent, set()).add(item_id)

        for item_id in every_id:
            actual = {c.id for c in dbm.get_children(item_id)}
            assert actual == expected.get(item_id, set()), item_id
    finally:
        vps.close()


def test_wtpm24_the_panel_reader_stays_wider(tmp_path):
    """WTP-M2.4 / WTP-D4 — the two readers differ on exactly one row.

    ``get_action_items_for_weekly_tactic`` answers "what work sits under this
    week" and keeps the WTP-D3 row; ``get_children`` answers "what hangs
    directly off this record" and drops it. The difference is one row, not a
    general divergence — which is what makes keeping both defensible.
    """
    vps = make_vps(tmp_path)
    try:
        shapes, tactic_id, _second, _outer = _all_link_shapes(vps)

        tree = {c.id for c in vps.db_manager.get_children(tactic_id)}
        panel = {p.id for p in vps.get_action_items_for_weekly_tactic(tactic_id)}

        assert panel - tree == {shapes["both_split"]}
        assert tree - panel == set()
    finally:
        vps.close()


def test_wtpm25_ordinary_parent_unchanged(tmp_path):
    """WTP-M2.5 — a non-tactic parent still gets its ``parent_id`` children."""
    vps = make_vps(tmp_path)
    try:
        seed_ape(vps)
        outer = make_daily_item(vps, title="Ordinary parent")
        inner = make_daily_item(vps, title="Ordinary child", parent_id=outer.id)
        make_daily_item(vps, title="Unrelated")

        assert [c.id for c in vps.db_manager.get_children(outer.id)] == [inner.id]
    finally:
        vps.close()


def test_wtpm26_week_rows_are_never_children(tmp_path):
    """WTP-M2.6 — a nested tactic is not a child, in either branch.

    The ``parent_id`` is written straight to the row: no supported path creates
    it, and ``_move_week_links_off_parent_id`` would clear it at the next
    launch. It is seeded because the reader must not depend on that migration
    having run — the dirty-state case (P8).
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        nested = make_week_item(vps, ape, start="2026-03-02", due="2026-03-08",
                                title="W2")
        outer = make_daily_item(vps, title="Ordinary parent")
        vps.db.conn.execute(
            "UPDATE action_items SET parent_id = ? WHERE id = ?",
            (tactic.id, nested.id),
        )
        vps.db.conn.execute(
            "UPDATE action_items SET parent_id = ? WHERE id = ?",
            (outer.id, tactic.id),
        )
        vps.db.conn.commit()

        assert [c.id for c in vps.db_manager.get_children(tactic.id)] == []
        assert [c.id for c in vps.db_manager.get_children(outer.id)] == []
    finally:
        vps.close()


def test_wtpm27_subtree_through_a_tactic(tmp_path):
    """WTP-M2.7 — ``get_subtree`` reaches a week-filed item's own subtasks."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)
        grandchild = make_daily_item(vps, title="Find the quote",
                                     parent_id=child.id)

        ids = [i.id for i in vps.db_manager.get_subtree(tactic.id)]

        assert ids == [child.id, grandchild.id]
    finally:
        vps.close()


# ---------------------------------------------------------------- WTP-M3 ----


def test_wtpm31_week_filed_items_are_not_roots(tmp_path):
    """WTP-M3.1 — a week-filed item stops appearing at the tree's top level.

    It used to sit beside its own tactic, at the same indent, unconnected to
    it — the visible shape of the request.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)

        roots = [r.id for r in vps.db_manager.get_root_items()]

        assert child.id not in roots
        assert tactic.id in roots
    finally:
        vps.close()


def test_wtpm32_dangling_link_stays_a_root(tmp_path):
    """WTP-M3.2 / WTP-D6 — an item whose tactic link does not resolve stays visible.

    The dirty-state test (P8). Excluding every item with a non-empty
    ``weekly_tactic_id`` would drop such a row out of the only tree view in the
    app while leaving it in the table — P2: surface, never silently drop.

    **Seeded with foreign keys off, and that is the point.**
    ``weekly_tactic_id`` is ``REFERENCES action_items(id) ON DELETE SET NULL``
    and ``database.py:129`` sets ``PRAGMA foreign_keys = ON``, so deleting a
    tactic through the app *nulls* this column rather than leaving a value
    behind. The pragma is per connection, so the state is reachable from any
    client that does not set it. Counted on 2026-11-08, the main database holds
    49 items linked by ``weekly_tactic_id`` and **no** unresolvable link.

    An earlier version of this test deleted the tactic with the pragma on and
    asserted the same thing. It passed, and went on passing with the guard
    removed — the FK had nulled the link, so the row was a root for a reason
    the test was not about. The mutation gate is what found it.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Left behind by a delete",
                                weekly_tactic_id=tactic.id)
        vps.db.conn.execute("PRAGMA foreign_keys = OFF")
        vps.db.conn.execute("DELETE FROM action_items WHERE id = ?", (tactic.id,))
        vps.db.conn.commit()
        vps.db.conn.execute("PRAGMA foreign_keys = ON")

        stored = vps.db_manager.get_action_item(child.id)
        assert stored.weekly_tactic_id == tactic.id, "the seed must actually dangle"

        roots = [r.id for r in vps.db_manager.get_root_items()]

        assert child.id in roots
        # And it is not also a child of the id it still names.
        assert vps.db_manager.get_children(tactic.id) == []
    finally:
        vps.close()


def test_wtpm33_tactics_and_plain_items_are_still_roots(tmp_path):
    """WTP-M3.3 — the exclusion is narrow: tactics and unlinked items stay."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        plain = make_daily_item(vps, title="No links at all")
        outer = make_daily_item(vps, title="Ordinary parent")
        inner = make_daily_item(vps, title="Ordinary child", parent_id=outer.id)

        roots = [r.id for r in vps.db_manager.get_root_items()]

        assert tactic.id in roots
        assert plain.id in roots
        assert outer.id in roots
        assert inner.id not in roots
    finally:
        vps.close()


def test_wtpm34_status_filter_unchanged(tmp_path):
    """WTP-M3.4 — ``status_filter`` still applies, and applies with the exclusion."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        open_item = make_daily_item(vps, title="Still open")
        done_item = make_daily_item(vps, title="Finished")
        vps.db.conn.execute(
            "UPDATE action_items SET status = ? WHERE id = ?",
            (Status.COMPLETED, done_item.id),
        )
        vps.db.conn.commit()

        open_roots = [r.id for r in vps.db_manager.get_root_items(status_filter="open")]

        assert open_item.id in open_roots
        assert done_item.id not in open_roots
        assert tactic.id in open_roots
    finally:
        vps.close()


# ------------------------------------------------- WTP-M3.5 / WTP-M3.6 ----
# The Hierarchical screen. Built on a **withdrawn** root, so it adds nothing to
# the mapped window count tests/test_ci_contract.py pins at 22.


def _root():
    """A withdrawn Tk root, or a skip when there is no display."""
    try:
        root = ctk.CTk()
    except Exception as exc:  # Headless without a display.
        pytest.skip(f"Tk display unavailable: {exc}")
    root.geometry("1400x900+0+0")
    root.withdraw()
    return root


def _tree_rows(screen):
    """[(grid row, indent level)] for every rendered row, in grid order.

    The indent is read back out of the padding the screen gridded the frame
    with — ``padx=(indent_level * 30 + 5, 5)`` in ``display_item_tree`` — which
    is the only place the level survives into the widget tree.
    """
    frames = [c for c in screen.scroll_frame.winfo_children() if c.grid_info()]
    frames.sort(key=lambda c: int(c.grid_info()["row"]))
    out = []
    for frame in frames:
        left = frame.grid_info()["padx"]
        left = int(str(left).strip("() ").split(",")[0]) if not isinstance(left, int) else left
        out.append((frame, (left - 5) // 30))
    return out


def _row_text(frame):
    """Every label string inside one rendered row, flattened.

    ``CTkLabel`` only. A CustomTkinter label is a frame wrapping a ``tk.Label``
    and both answer ``cget("text")``, so a walk that took every widget
    returned each string twice — which made an assertion on the number of
    rendered count labels unable to distinguish one label from two.
    """
    texts = []
    stack = list(frame.winfo_children())
    while stack:
        widget = stack.pop()
        stack.extend(widget.winfo_children())
        if not isinstance(widget, ctk.CTkLabel):
            continue
        text = widget.cget("text")
        if isinstance(text, str) and text:
            texts.append(text)
    return texts


def test_wtpm35_tree_nests_week_filed_items(tmp_path):
    """WTP-M3.5 — the screen renders a week-filed item under its tactic, once.

    The screen itself is unchanged by this batch: it reads ``get_root_items``
    and ``get_children``, so this asserts the two readers compose into the tree
    the request asked for. Before WTP both rows came back as roots and rendered
    at indent 0, side by side.
    """
    vps = make_vps(tmp_path)
    root = None
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        make_daily_item(vps, title="Write the post", weekly_tactic_id=tactic.id)

        root = _root()
        screen = HierarchicalScreen(root, vps.db_manager,
                                    SimpleNamespace(vps_manager=vps))
        screen.update_idletasks()

        rendered = [(_row_text(frame), indent) for frame, indent in _tree_rows(screen)]
        levels = {}
        for texts, indent in rendered:
            for needle in ("W1 tactic", "Write the post"):
                if any(needle in t for t in texts):
                    levels.setdefault(needle, []).append(indent)

        assert levels["W1 tactic"] == [0]
        assert levels["Write the post"] == [1]
    finally:
        if root is not None:
            root.destroy()
        vps.close()


def test_wtpm36_tactic_row_shows_child_count(tmp_path):
    """WTP-M3.6 — the tactic's row carries the ``(N sub)`` count.

    Same mechanism as WTP-M3.5: ``create_item_row`` already renders the count
    from ``get_children``, which now answers for a tactic.
    """
    vps = make_vps(tmp_path)
    root = None
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        make_daily_item(vps, title="One", weekly_tactic_id=tactic.id)
        make_daily_item(vps, title="Two", weekly_tactic_id=tactic.id)

        root = _root()
        screen = HierarchicalScreen(root, vps.db_manager,
                                    SimpleNamespace(vps_manager=vps))
        screen.update_idletasks()

        counts = []
        for frame, _indent in _tree_rows(screen):
            texts = _row_text(frame)
            if any("W1 tactic" in t for t in texts):
                counts = [t for t in texts if t.endswith("sub)")]

        assert counts == ["(2 sub)"]
    finally:
        if root is not None:
            root.destroy()
        vps.close()


# ---------------------------------------------------------------- WTP-M4 ----
# The Item Editor's parent surfaces. Driven on stubs rather than real dialogs,
# the way tests/test_item_editor_weekly_tactic_ui.py drives the Org tab: the
# methods under test are called unbound, so no window is built and the mapped
# window count tests/test_ci_contract.py pins stays where it is.


class _FakeWidget:
    """A widget double that records what it was built with.

    Enough surface for the error dialog ``delete_item`` builds and the parent
    row ``create_form`` grids: both only construct, configure and pack.
    """

    made = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        _FakeWidget.made.append(kwargs)

    def title(self, *args):
        pass

    def geometry(self, *args):
        pass

    def transient(self, *args):
        pass

    def grab_set(self):
        pass

    def update_idletasks(self):
        pass

    def pack(self, *args, **kwargs):
        return self

    def grid(self, *args, **kwargs):
        return self

    def destroy(self):
        pass


def _fake_ctk():
    return SimpleNamespace(
        CTkToplevel=_FakeWidget,
        CTkLabel=_FakeWidget,
        CTkButton=_FakeWidget,
        CTkFrame=_FakeWidget,
        CTkFont=lambda **kwargs: None,
    )


def _editor_stub(manager, item, **extra):
    """Enough of ItemEditorDialog to drive one method without a display."""
    stub = SimpleNamespace(
        db_manager=manager,
        item=item,
        item_id=item.id if item else None,
        vps_manager=None,
        on_close_callback=None,
        winfo_rootx=lambda: 0,
        winfo_rooty=lambda: 0,
        winfo_width=lambda: 400,
        winfo_height=lambda: 150,
    )
    for key, value in extra.items():
        setattr(stub, key, value)
    return stub


def test_wtpm41_editor_shows_tactic_as_parent(tmp_path):
    """WTP-M4.1 — a week-filed item's parent line names its Weekly Tactic.

    Asserted through ``parent_of`` and the title the editor would read, not
    through a built widget: the editor resolves ``parent_of(self.item)`` and
    renders ``f"Parent: {parent_item.title}"``, and
    ``test_wtpm43_view_parent_button_opens_the_parent`` covers the binding.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)

        stored = vps.db_manager.get_action_item(child.id)
        parent_link = parent_of(stored)

        assert parent_link == tactic.id
        assert vps.db_manager.get_action_item(parent_link).title == "W1 tactic"
    finally:
        vps.close()


def test_wtpm42_editor_shows_nearer_parent(tmp_path):
    """WTP-M4.2 / WTP-D3 — with both links, the parent line names the subtask parent."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        outer = make_daily_item(vps, title="Ship the series")
        nested = make_daily_item(vps, title="Draft part two",
                                 parent_id=outer.id,
                                 weekly_tactic_id=tactic.id, refile=False)

        stored = vps.db_manager.get_action_item(nested.id)

        assert parent_of(stored) == outer.id
    finally:
        vps.close()


def test_wtpm43_view_parent_button_opens_the_parent(tmp_path, monkeypatch):
    """WTP-M4.3 — View Parent opens the parent in a second editor.

    ``view_parent_item`` has existed since the hierarchy work and was bound to
    nothing; this drives the method the new button calls, with the dialog class
    replaced so no window is built. ``monkeypatch`` restores the module
    attribute afterwards.
    """
    from src.getmoredone.screens import item_editor as editor_module

    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)

        # The real class is captured *before* the double replaces the module
        # global, because ``view_parent_item`` resolves ``ItemEditorDialog``
        # at call time — taking the reference afterwards would call the double
        # and assert nothing.
        from src.getmoredone.screens.item_editor import ItemEditorDialog

        opened = []
        monkeypatch.setattr(
            editor_module, "ItemEditorDialog",
            lambda master, db, item_id, **kw: opened.append(item_id),
        )

        stub = _editor_stub(vps.db_manager,
                            vps.db_manager.get_action_item(child.id),
                            master=None, destroy=lambda: None)
        ItemEditorDialog.view_parent_item(stub, tactic.id)

        assert opened == [tactic.id]
    finally:
        vps.close()


def test_wtpm45_hierarchy_dialog_shows_the_tactic_as_parent(tmp_path, monkeypatch):
    """WTP-M4.5 — the Hierarchy dialog's PARENT ITEM is the Weekly Tactic.

    ``ShowRelatedDialog.refresh`` is driven on a stub with ``ctk`` replaced, so
    the rows it would render are recorded instead of drawn and no window is
    built. The first row it renders under PARENT ITEM is the assertion.

    This is also the test that found the dialog's *second* reader of
    parenthood: the "no related items" branch still asked about
    ``current_item.parent_id``, so a week-filed item with no children rendered
    "No related items found" directly beneath its own PARENT ITEM heading.
    """
    from src.getmoredone.screens import item_editor_dialogs as dialogs_module
    from src.getmoredone.screens.item_editor_dialogs import ShowRelatedDialog

    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)

        monkeypatch.setattr(dialogs_module, "ctk", _fake_ctk())
        _FakeWidget.made = []
        rendered = []
        stub = SimpleNamespace(
            db_manager=vps.db_manager,
            current_item_id=child.id,
            palette={"primary": "#000", "on_primary": "#fff", "body_text": "#111"},
            scroll_frame=SimpleNamespace(winfo_children=lambda: []),
            create_header_row=lambda row: None,
            create_item_row=lambda item, row: rendered.append(item.id),
        )

        ShowRelatedDialog.refresh(stub)

        headings = [kw.get("text", "") for kw in _FakeWidget.made]
        assert rendered == [tactic.id]
        assert "PARENT ITEM" in headings
        # The item has a parent and no children of its own, so the dialog must
        # not claim there is nothing related.
        assert "No related items found" not in headings
    finally:
        _FakeWidget.made = []
        vps.close()


def test_wtpm46_hierarchy_dialog_lists_tactic_children(tmp_path):
    """WTP-M4.6 — CHILD ITEMS lists the week-filed items, via get_children.

    The dialog reads ``get_children`` and needed no change, so this asserts the
    reader answers for the id the dialog passes it.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        one = make_daily_item(vps, title="One", weekly_tactic_id=tactic.id)
        two = make_daily_item(vps, title="Two", weekly_tactic_id=tactic.id)

        ids = {c.id for c in vps.db_manager.get_children(tactic.id)}

        assert ids == {one.id, two.id}
    finally:
        vps.close()


# ---------------------------------------------------------------- WTP-M5 ----


def test_wtpm51_editor_refuses_to_delete_a_tactic_with_children(tmp_path, monkeypatch):
    """WTP-M5.1 — the existing guard now fires for a Weekly Tactic.

    The guard body is not new; what is new is ``get_children`` returning the
    week-filed items, so the branch is reached at all. ``ctk`` is replaced for
    the call so the error dialog is recorded instead of drawn, and restored by
    ``monkeypatch``.
    """
    from src.getmoredone.screens import item_editor as editor_module
    from src.getmoredone.screens.item_editor import ItemEditorDialog

    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1 tactic")
        make_daily_item(vps, title="Write the post", weekly_tactic_id=tactic.id)

        deleted = []
        manager = vps.db_manager
        monkeypatch.setattr(manager, "delete_action_item",
                            lambda item_id: deleted.append(item_id))
        monkeypatch.setattr(editor_module, "ctk", _fake_ctk())
        _FakeWidget.made = []

        ItemEditorDialog.delete_item(
            _editor_stub(manager, manager.get_action_item(tactic.id)))

        messages = [kw.get("text", "") for kw in _FakeWidget.made]
        assert deleted == []
        assert any("1 child item(s)" in text for text in messages), messages
    finally:
        _FakeWidget.made = []
        vps.close()


def test_wtpm53_cascade_covers_both_link_columns(tmp_path):
    """WTP-M5.3 — deleting a tactic leaves no row pointing at it.

    Before this the cascade deleted only ``parent_id`` children, so every
    ``weekly_tactic_id`` item survived naming a row that was gone. That is the
    state WTP-D6 keeps visible; this is what stops producing it.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        by_tactic = make_daily_item(vps, title="Linked by the column",
                                    weekly_tactic_id=tactic.id)
        by_parent = make_daily_item(vps, title="Linked the AWA-A1 way",
                                    parent_id=tactic.id)
        untouched = make_daily_item(vps, title="Nothing to do with the week")

        assert vps.delete_weekly_action_item(tactic.id) is True

        rows = vps.db.conn.execute("SELECT id FROM action_items").fetchall()
        surviving = {row["id"] for row in rows}
        assert by_tactic.id not in surviving
        assert by_parent.id not in surviving
        assert tactic.id not in surviving
        assert untouched.id in surviving
    finally:
        vps.close()


def test_wtpm54_cascade_reaches_grandchildren(tmp_path):
    """WTP-M5.4 — a week-filed item's own subtasks go with it.

    The old cascade deleted one level by ``parent_id``, so a subtask of a
    week-filed item was left behind pointing at a deleted parent.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Write the post",
                                weekly_tactic_id=tactic.id)
        grandchild = make_daily_item(vps, title="Find the quote",
                                     parent_id=child.id)

        assert vps.delete_weekly_action_item(tactic.id) is True

        rows = vps.db.conn.execute("SELECT id FROM action_items").fetchall()
        surviving = {row["id"] for row in rows}
        assert grandchild.id not in surviving
    finally:
        vps.close()


def test_wtpm55_non_tactic_id_deletes_nothing(tmp_path):
    """WTP-M5.5 — an id that is not a week row deletes nothing, and returns False.

    The adversarial case (P7) for a widened delete: an ordinary parent id
    "looks right" to a cascade that walks children, and must not have its
    subtasks removed by the tactic delete path.
    """
    vps = make_vps(tmp_path)
    try:
        seed_ape(vps)
        outer = make_daily_item(vps, title="Ordinary parent")
        inner = make_daily_item(vps, title="Ordinary child", parent_id=outer.id)

        assert vps.delete_weekly_action_item(outer.id) is False

        rows = vps.db.conn.execute("SELECT id FROM action_items").fetchall()
        surviving = {row["id"] for row in rows}
        assert outer.id in surviving
        assert inner.id in surviving
    finally:
        vps.close()


# ---------------------------------------------------------------- WTP-M6 ----


def test_wtpm61_completing_a_tactic_with_open_children_asks(tmp_path, monkeypatch):
    """WTP-M6.1 — the prompt names the open count, and No completes nothing."""
    import tkinter.messagebox as messagebox

    from src.getmoredone.screens.item_editor import ItemEditorDialog

    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        make_daily_item(vps, title="One", weekly_tactic_id=tactic.id)
        make_daily_item(vps, title="Two", weekly_tactic_id=tactic.id)

        asked = []
        monkeypatch.setattr(
            messagebox, "askyesno",
            lambda title, message, **kw: asked.append(message) or False)

        manager = vps.db_manager
        stub = _editor_stub(manager, manager.get_action_item(tactic.id))
        stub._is_weekly_tactic_record = (
            lambda: ItemEditorDialog._is_weekly_tactic_record(stub))

        allowed = ItemEditorDialog._confirm_tactic_completion(stub)

        assert allowed is False
        assert len(asked) == 1
        assert "2 Action Items" in asked[0]
    finally:
        vps.close()


def test_wtpm62_completion_does_not_cascade(tmp_path):
    """WTP-M6.2 / WTP-D8 — completing a tactic leaves its children alone."""
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Still mine to do",
                                weekly_tactic_id=tactic.id)

        vps.db_manager.complete_action_item(tactic.id)

        assert vps.db_manager.get_action_item(child.id).status != Status.COMPLETED
    finally:
        vps.close()


def test_wtpm63_no_prompt_when_nothing_is_open(tmp_path, monkeypatch):
    """WTP-M6.3 — no children open, no question; and never for a plain item."""
    import tkinter.messagebox as messagebox

    from src.getmoredone.screens.item_editor import ItemEditorDialog

    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        child = make_daily_item(vps, title="Done already",
                                weekly_tactic_id=tactic.id)
        plain = make_daily_item(vps, title="An ordinary item")
        vps.db.conn.execute(
            "UPDATE action_items SET status = ? WHERE id = ?",
            (Status.COMPLETED, child.id))
        vps.db.conn.commit()

        asked = []
        monkeypatch.setattr(
            messagebox, "askyesno",
            lambda title, message, **kw: asked.append(message) or False)

        manager = vps.db_manager
        for item_id in (tactic.id, plain.id):
            stub = _editor_stub(manager, manager.get_action_item(item_id))
            stub._is_weekly_tactic_record = (
                lambda s=stub: ItemEditorDialog._is_weekly_tactic_record(s))
            assert ItemEditorDialog._confirm_tactic_completion(stub) is True

        assert asked == []
    finally:
        vps.close()


def test_wtpm64_progress_counts_come_from_one_helper(tmp_path):
    """WTP-M6.4 — ``(done, total)`` for a tactic, from the tree reader.

    One home for the number, so two panels cannot show two different counts
    for the same week. The renderings that call it are not in this batch; see
    the handoff note.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, title="W1")
        done = make_daily_item(vps, title="Finished", weekly_tactic_id=tactic.id)
        make_daily_item(vps, title="Open one", weekly_tactic_id=tactic.id)
        make_daily_item(vps, title="Open two", weekly_tactic_id=tactic.id)
        vps.db.conn.execute(
            "UPDATE action_items SET status = ? WHERE id = ?",
            (Status.COMPLETED, done.id))
        vps.db.conn.commit()

        assert vps.count_open_children_for_weekly_tactic(tactic.id) == (1, 3)
        # And it agrees with the (N sub) count the tree renders.
        assert len(vps.db_manager.get_children(tactic.id)) == 3
    finally:
        vps.close()


def test_wtpm66_count_follows_the_wt_m5a_refile(tmp_path):
    """WTP-M6.6 — the count is read after WT-M5.A moves a completed item.

    Completing an item re-files it into the week it was *completed* in, not the
    week it was planned for. So a count read from a stale in-memory list would
    disagree with the one the tactic's own panel shows. Reading through
    ``get_children`` each time is what makes the two agree.
    """
    vps = make_vps(tmp_path)
    try:
        ape = seed_ape(vps)
        tactic = make_week_item(vps, ape, start="2026-02-23", due="2026-03-01",
                                title="W1")
        item = make_daily_item(vps, title="Write the post", start="2026-02-25",
                               due="2026-02-25", weekly_tactic_id=tactic.id)

        assert vps.count_open_children_for_weekly_tactic(tactic.id) == (0, 1)

        vps.db_manager.complete_action_item(item.id)

        stored = vps.db_manager.get_action_item(item.id)
        done, total = vps.count_open_children_for_weekly_tactic(stored.weekly_tactic_id)
        assert (done, total) == (1, 1)
    finally:
        vps.close()


if __name__ == "__main__":  # pragma: no cover - parity with the other suites
    pytest.main([__file__])
