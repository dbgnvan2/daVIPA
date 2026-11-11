"""SCV — one authority for a segment colour.

Spec: docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md

Two validators were hand-rolled out of ``startswith("#")``, ``len() == 7`` and
``int(text[1:], 16)``, which is the exact parse ``color_contrast``'s module
docstring forbids for this job: Python's ``int(x, 16)`` takes a leading sign, a
``0x`` prefix and PEP-515 underscores, so a value Tk raises on passes a check
written to mean "six hex digits". The four values in the table below are the
ones measured against the real staticmethods at ``6963d0a``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.getmoredone.color_contrast import normalize_hex_color
from src.getmoredone.vps_manager import VPSManager
from src.getmoredone.screens.vps_segment_editor import VPSSegmentEditorDialog


SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "getmoredone"

#: The fallback ``_derive_subsegment_color`` uses when it cannot read its base.
FALLBACK_BASE = "#64748B"

#: What ``int(…, 16)`` let through, and the one six-digit value in the same
#: family that must keep working. ``#0b1010`` is not a defect -- it is six hex
#: digits that merely *look* like a Python literal.
#:
#: The plan's §1 table measured the first three. The last two were measured
#: the same way after a cold pass pointed out that three values are examples
#: and the family is the thing: ``int()`` also strips surrounding whitespace
#: and takes a minus sign, so ``"# 12345"`` derived ``#0B368D`` and
#: ``"#-12345"`` derived ``#07368F``, both silently. One regex refuses all
#: five, so naming all five costs nothing and is what the fix actually claims.
INT_BASE_16_ACCEPTS = ("#0X1234", "#1_2345", "#+12345", "# 12345", "#-12345")

#: The three above that raised nothing and produced a colour from a misread
#: slice, with what they produced at ``6963d0a``. These are the adversarial
#: half: a crash is visible, and these were not.
SILENTLY_MISREAD = {"#+12345": "#0B368D", "# 12345": "#0B368D", "#-12345": "#07368F"}
STILL_VALID = "#0b1010"


def _derive(value):
    return VPSManager._derive_subsegment_color(value)


# ======================================================================
# SCV-M1 — one authority, both validators
# ======================================================================

def _slice_parse_sites(path: Path) -> int:
    """How many ``int(<something>[a:b], 16)`` calls one module contains.

    Parsed, not grepped: a regex over the source counts a call inside a
    docstring or a comment, and this module's own docstring quotes the
    pattern. ``ast`` sees only code.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "int"):
            continue
        if len(node.args) != 2:
            continue
        base = node.args[1]
        if not (isinstance(base, ast.Constant) and base.value == 16):
            continue
        target = node.args[0]
        if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Slice):
            count += 1
    return count


def test_scvm11_no_hand_rolled_hex_validator_survives():
    """SCV-M1.1 — a colour is sliced into ``int(…, 16)`` in three places only.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m1

    Exact counts per module, not a floor: a floor passes on a build where a
    fourth copy of the parse was added, which is the whole failure this
    batch closes. The three modules that keep one:

    * ``color_contrast.hex_to_rgb`` -- the authority. One function, reached by
      ``relative_luminance`` and by ``_derive_subsegment_color``, and it
      refuses anything ``_HEX_COLOR_RE`` does not match before it slices.
    * ``screens/drag_schedule_support.py`` -- ``interpolate_hex_color``
      (``SCV-A1``, filed not fixed: its only caller is the gradient in its own
      module, over theme colours, so it is not on the stored-colour path).
    * ``screens/item_editor_weekly_tactic_dialog.py`` --
      ``_text_color_for_background`` (``SCV-A3``: already wrapped in
      ``try/except ValueError`` with a fallback, so it is correct as it
      stands and is listed here so the next reader does not "fix" it).

    ``vps_manager.py``, ``vps_manager_taxonomy.py``,
    ``screens/vps_segment_editor.py`` and ``priority_levels.py`` are the four
    this batch owns, and every one of them must be at zero.
    """
    expected = {
        "color_contrast.py": 3,
        "screens/drag_schedule_support.py": 6,
        "screens/item_editor_weekly_tactic_dialog.py": 3,
    }
    found = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        count = _slice_parse_sites(path)
        if count:
            found[path.relative_to(SRC_ROOT).as_posix()] = count

    assert found == expected, (
        "a colour is sliced into int(..., 16) somewhere new, or the authority "
        f"moved: {found}"
    )

    for owned in (
        "vps_manager.py",
        "vps_manager_taxonomy.py",
        "screens/vps_segment_editor.py",
        "priority_levels.py",
    ):
        assert _slice_parse_sites(SRC_ROOT / owned) == 0, owned


@pytest.mark.parametrize("value", INT_BASE_16_ACCEPTS)
def test_scvm12_the_validators_refuse_what_int_base_16_allows(value):
    """SCV-M1.2 — both validators refuse the three measured accepts.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m1

    Asserted against ``normalize_hex_color`` as well, so the three answers
    cannot drift apart: the point of SCV-M1 is that there is one authority,
    not three checks that happen to agree today.
    """
    assert normalize_hex_color(value) is None, value
    assert VPSManager._is_valid_hex_color(value) is False, value
    assert VPSSegmentEditorDialog.validate_color(None, value) is False, value


def test_scvm12_a_six_digit_colour_that_looks_like_a_literal_still_passes():
    """SCV-M1.2 — ``#0b1010`` is six hex digits, and must keep working.

    The adversarial half of the table in the other direction: a validator
    tightened by refusing anything with a ``b`` or an ``x`` in it would pass
    the test above and break a colour that was always legal.
    """
    assert normalize_hex_color(STILL_VALID) == "#0B1010"
    assert VPSManager._is_valid_hex_color(STILL_VALID) is True
    assert VPSSegmentEditorDialog.validate_color(None, STILL_VALID) is True


@pytest.mark.parametrize("typed,stored", [
    ("#abc", "#AABBCC"),
    ("#AbC123", "#ABC123"),
    ("  #abc123  ", "#ABC123"),
])
def test_scvm13_the_editor_stores_the_normalised_form(tmp_path, typed, stored):
    """SCV-M1.3 — what the editor writes is ``#RRGGBB``, not the typed text.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m1

    Delegating to ``normalize_hex_color`` widens the editor: ``#abc`` was
    refused by the ``len() == 7`` check and is accepted now. §4 of the plan
    takes that deliberately -- it is a form people type and every browser
    accepts -- **but only together with this**. Accepting the short form and
    storing it raw would put a value in the database that every reader has to
    expand again, which is how this class of defect started.

    Driven through the dialog's own ``save_segment``, not through
    ``update_segment``: P25 -- a guard that is not on the surface a person
    uses is worth nothing.
    """
    import customtkinter as ctk

    manager = VPSManager(str(tmp_path / "scv_editor.db"))
    try:
        segment_id = manager.create_segment("Scv Colour", "desc", "#123456", 91)
        segment = dict(manager.get_segment(segment_id))

        root = ctk.CTk()
        root.withdraw()
        try:
            dialog = VPSSegmentEditorDialog(root, manager, segment)
            dialog.color_entry.delete(0, "end")
            dialog.color_entry.insert(0, typed)
            dialog.save_segment()
        finally:
            root.destroy()

        assert manager.get_segment(segment_id)["color_hex"] == stored, (
            f"the editor stored the typed text rather than the normalised form"
        )
    finally:
        manager.close()


# ======================================================================
# SCV-M2 — deriving a colour cannot crash
# ======================================================================

@pytest.mark.parametrize("value", ["#0X1234", "#1_2345"])
def test_scvm21_deriving_from_a_malformed_colour_falls_back(value):
    """SCV-M2.1 — the measured crash: an uncaught ``ValueError`` in a VPS read.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m2

    ``_derive_subsegment_color`` asked its own gate whether the value was a
    colour, was told yes, and then sliced ``base[1:3]`` into ``int(…, 16)``.
    Both of these raised ``ValueError: invalid literal for int() with base 16``
    at ``6963d0a`` -- not a cosmetic fault but a hard crash inside
    ``get_vision_subsegments()``, independent of Tk.
    """
    assert _derive(value) == _derive(FALLBACK_BASE), value


@pytest.mark.parametrize("value,was", sorted(SILENTLY_MISREAD.items()))
def test_scvm22_a_colour_that_parses_wrongly_is_not_derived_from(value, was):
    """SCV-M2.2 — a misread slice must not become a colour.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m2

    P7, the adversarial case, and the one that matters more than the two
    crashes above: these three raised nothing. For ``#+12345``,
    ``int("+1", 16)`` is 1, ``int("23", 16)`` is 35 and ``int("45", 16)`` is
    69, so a colour was derived and drawn and nobody was told. A crash is
    visible; this is not.

    The old output is asserted by value, not just "not the fallback": a fix
    that happened to land on ``#0B368D`` by another route would pass a
    fallback-only check.
    """
    assert _derive(value) != was, (
        f"a colour is still being derived from a misread slice: {was}")
    assert _derive(value) == _derive(FALLBACK_BASE)


def test_scvm21_deriving_answers_for_anything_a_caller_can_hold():
    """SCV-M2.1 — nothing raises, and nothing is derived from a misread slice.

    The call sites hand it ``row.get("color_hex")`` and
    ``resolve_segment_color(...)``, i.e. whatever the database holds, which
    includes ``None`` and the empty string. Each input is held to the one
    right answer rather than only to "a colour came back": a build that still
    sliced the raw value would return a well-formed ``#RRGGBB`` for
    ``"#12345٠"`` -- ``٠`` is ARABIC-INDIC DIGIT ZERO, which
    ``int(…, 16)`` reads as 0 and Tk does not read at all.
    """
    unreadable = (None, "", "   ", "navy", "#GGHHII", "#aabbccdd", "0X1234",
                  "#12345٠", "rgb(1,2,3)", 0, 123456)
    for value in unreadable:
        assert normalize_hex_color(value) is None, value
        assert _derive(value) == _derive(FALLBACK_BASE), value

    # And a form the normaliser *does* read is derived from its expansion.
    for value in ("#abc", "\t#123456\n", "AABBCC"):
        readable = normalize_hex_color(value)
        assert readable is not None, value
        assert _derive(value) == _derive(readable), value


def test_scvm21_a_valid_colour_still_derives_what_it_always_did():
    """SCV-M2.1 — the fix changes nothing for a colour that was readable.

    The three §1 rows that crashed or misparsed are not the only inputs; a
    normalisation bug in the fix would move every subsegment colour in the
    app. ``#0b1010 -> #35474A`` (the plan's §1 table) and
    ``#64748B -> #9399AE`` are the values measured against the ``6963d0a``
    body of this function, not predicted from the new one.
    """
    assert _derive("#0b1010") == "#35474A"
    assert _derive(FALLBACK_BASE) == "#9399AE"
    # Case and surrounding whitespace were already tolerated.
    assert _derive("  #0B1010 ") == "#35474A"


# ======================================================================
# SCV-M3 — the repair pass can see the class it exists to repair
# ======================================================================

def _seed_malformed(manager: VPSManager, table: str, row_id: str, value: str) -> None:
    """Put a value in the database that no current code path would write.

    The only way to represent what an older build left behind: every writer
    now refuses this value, which is the point of SCV-M1. This is the dirty
    state P8 asks for, not a hand-edit standing in for a code path.
    """
    manager.db.conn.execute(
        f"UPDATE {table} SET color_hex = ? WHERE id = ?", (value, row_id)
    )
    manager.db.conn.commit()


def test_scvm31_the_repair_pass_sees_a_malformed_stored_colour(tmp_path):
    """SCV-M3.1 — a row holding ``#0X1234`` is repaired, not skipped.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m3

    ``_is_valid_hex_color`` is the gate on the colour-repair pass inside
    ``get_vision_subsegments`` and ``get_vision_categories``: a row it calls
    valid is ``continue``d past, untouched. So the pass that exists to replace
    a bad colour was blind to exactly this class of bad colour -- and at
    ``6963d0a`` the row did not merely survive, it crashed the read.

    P8, dirty state: the repair has to persist, so it is read back through a
    second ``VPSManager`` on the same file rather than from the dict the first
    one returned.
    """
    db_path = tmp_path / "scv_repair.db"
    manager = VPSManager(str(db_path))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]
        manager.create_vision_subsegment(seg_name, "Scv Sub")
        manager.create_or_get_vision_element(seg_name, "Scv Sub", "Scv Cat")

        sub = manager.get_vision_subsegments(seg_name)[0]
        cat = manager.get_vision_categories(seg_name, "Scv Sub")[0]
        _seed_malformed(manager, "vision_subsegments", sub["id"], "#0X1234")
        _seed_malformed(manager, "vision_categories", cat["id"], "#1_2345")

        repaired_sub = manager.get_vision_subsegments(seg_name)[0]
        repaired_cat = manager.get_vision_categories(seg_name, "Scv Sub")[0]
        for row in (repaired_sub, repaired_cat):
            colour = row["color_hex"]
            assert normalize_hex_color(colour) == colour, (
                f"the repair pass handed back {colour!r}")
    finally:
        manager.close()

    reopened = VPSManager(str(db_path))
    try:
        stored_sub = reopened.db.conn.execute(
            "SELECT color_hex FROM vision_subsegments WHERE id = ?", (sub["id"],)
        ).fetchone()["color_hex"]
        stored_cat = reopened.db.conn.execute(
            "SELECT color_hex FROM vision_categories WHERE id = ?", (cat["id"],)
        ).fetchone()["color_hex"]
        assert stored_sub == repaired_sub["color_hex"], (
            f"the subsegment repair did not persist: {stored_sub!r}")
        assert stored_cat == repaired_cat["color_hex"], (
            f"the category repair did not persist: {stored_cat!r}")
        assert normalize_hex_color(stored_sub) == stored_sub
        assert normalize_hex_color(stored_cat) == stored_cat
    finally:
        reopened.close()


def test_scvm31_the_taxonomy_writers_store_the_normalised_form(tmp_path):
    """SCV-M3.1 — widening the gate must not widen what reaches the table.

    ``update_vision_subsegment_color``, ``update_vision_subsegment`` and
    ``update_vision_category`` gate on ``_is_valid_hex_color`` and then store
    ``(color_hex or "").strip().upper()``. Delegating the gate makes ``#abc``
    pass it, so without this the three of them would write ``#ABC`` -- a
    four-character colour in the database, the very thing §4 of the plan
    accepts the short form only in order to avoid.
    """
    manager = VPSManager(str(tmp_path / "scv_writers.db"))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]
        manager.create_vision_subsegment(seg_name, "Scv Sub")
        manager.create_or_get_vision_element(seg_name, "Scv Sub", "Scv Cat")
        sub = manager.get_vision_subsegments(seg_name)[0]
        cat = manager.get_vision_categories(seg_name, "Scv Sub")[0]

        assert manager.update_vision_subsegment_color(sub["id"], "#abc") is True
        assert manager.get_vision_subsegments(seg_name)[0]["color_hex"] == "#AABBCC"

        assert manager.update_vision_subsegment(
            sub["id"], "Scv Sub", "#def", "", "") is True
        assert manager.get_vision_subsegments(seg_name)[0]["color_hex"] == "#DDEEFF"

        assert manager.update_vision_category(
            cat["id"], "Scv Cat", "#abc", "", "") is True
        assert manager.get_vision_categories(seg_name, "Scv Sub")[0]["color_hex"] == "#AABBCC"

        for value in INT_BASE_16_ACCEPTS:
            with pytest.raises(ValueError):
                manager.update_vision_subsegment_color(sub["id"], value)
            with pytest.raises(ValueError):
                manager.update_vision_subsegment(sub["id"], "Scv Sub", value, "", "")
            with pytest.raises(ValueError):
                manager.update_vision_category(cat["id"], "Scv Cat", value, "", "")
    finally:
        manager.close()


# ======================================================================
# SCV-M5 — the segment table is gated at the store, not only at the dialog
# ======================================================================

def test_scvm51_the_segment_writers_refuse_and_normalise_a_colour(tmp_path):
    """SCV-M5.1 — `create_segment` and `update_segment` gate the colour.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m1
    Found by a cold pass over the plan, 2026-11-11, medium.

    P25 — the guard has to be on the funnel, not on one surface. SCV-M1.3 put
    the normalisation in ``VPSSegmentEditorDialog.save_segment``, and these two
    methods wrote ``segment_descriptions.color_hex`` with no colour check of
    any kind. Two *other* user-facing writers go through them with nothing but
    ``.strip().upper()`` -- ``create_vision_segment_admin`` and
    ``update_vision_segment_admin`` -- so the VSP admin screen could still
    store ``#0X1234`` after SCV-M1.3, and ``segment_descriptions`` is the one
    table whose colour ``row_fill`` ever draws.

    Normalised, not merely refused: the short form has to expand here for the
    same reason it does in the dialog (plan §4).
    """
    manager = VPSManager(str(tmp_path / "scv_segment_writers.db"))
    try:
        created = manager.create_segment("Scv Store", "desc", "#abc", 97)
        assert manager.get_segment(created)["color_hex"] == "#AABBCC"

        assert manager.update_segment(created, color_hex="#AbC123") is True
        assert manager.get_segment(created)["color_hex"] == "#ABC123"

        for value in INT_BASE_16_ACCEPTS:
            with pytest.raises(ValueError):
                manager.create_segment(f"Scv Bad {value}", "", value, 98)
            with pytest.raises(ValueError):
                manager.update_segment(created, color_hex=value)
        # The refusal left the good value in place rather than half-writing.
        assert manager.get_segment(created)["color_hex"] == "#ABC123"

        # An update that names no colour is untouched by the gate.
        assert manager.update_segment(created, description="still fine") is True
        assert manager.get_segment(created)["color_hex"] == "#ABC123"
    finally:
        manager.close()


def test_scvm51_the_vsp_admin_writers_cannot_store_a_bad_colour(tmp_path):
    """SCV-M5.1 — the two admin writers inherit the gate.

    They are the surface a person uses (VSP > Vision Elements > segment
    admin), and they pass ``color_hex.strip().upper()`` straight into
    ``create_segment`` / ``update_segment``. Asserted here rather than left to
    the funnel's own test, because the funnel is only load-bearing if these
    actually route through it.
    """
    manager = VPSManager(str(tmp_path / "scv_admin_writers.db"))
    try:
        with pytest.raises(ValueError):
            manager.create_vision_segment_admin(
                "Scv Admin Bad", "desc", "#0X1234", "vision")

        segment_id = manager.create_vision_segment_admin(
            "Scv Admin", "desc", "#abc", "vision")
        assert segment_id

        colours = manager.get_segment_color_map()
        assert colours["scv admin"] == "#AABBCC"

        with pytest.raises(ValueError):
            manager.update_vision_segment_admin(
                segment_id, "Scv Admin", "desc", "#+12345", "vision")
        assert manager.get_segment_color_map()["scv admin"] == "#AABBCC"
    finally:
        manager.close()


def test_scvm51_the_seeded_segments_are_already_normalised(tmp_path):
    """SCV-M5.1 — the one writer that bypasses the funnel seeds good values.

    ``vps_schema.py`` inserts the nine shipped segments with literal colours
    straight into ``segment_descriptions``, so the funnel's gate never sees
    them. All nine are `#RRGGBB` today (measured, not assumed); asserted
    through a real database rather than by reading the source, so a seed
    changed anywhere in that path is caught.

    This is the last unguarded write to the one table whose colour
    ``row_fill`` draws.
    """
    manager = VPSManager(str(tmp_path / "scv_seeds.db"))
    try:
        segments = manager.get_all_segments(active_only=False)
        assert len(segments) == 9, [s["name"] for s in segments]
        for segment in segments:
            colour = segment["color_hex"]
            assert normalize_hex_color(colour) == colour, (
                f"{segment['name']} is seeded with {colour!r}")
    finally:
        manager.close()


# ======================================================================
# SCV-M6 — the cold pass over the src diff (2026-11-11)
# ======================================================================
#
# Seven findings, two high. These are the code half; SCV-M6.4 is a docstring
# claim and is held by test_scvm11 above plus the BACKLOG filing.


def test_scvm61_the_create_helpers_store_a_normalised_colour(tmp_path):
    """SCV-M6.1 (high) — the widened gate's two remaining callers.

    ``_create_or_get_vision_subsegment`` and ``_create_or_get_vision_category``
    read ``if not self._is_valid_hex_color(chosen_color): chosen_color =
    default_color`` and then store ``chosen_color`` as typed. Widening that
    gate to ``normalize_hex_color`` turned them from "reject ``#abc``, use the
    derived default" into "accept ``#abc``, write it verbatim" -- a regression
    this batch introduced, in the two writers whose rows
    ``db_manager_project_boards`` selects *directly*, bypassing the repair
    pass, before handing the value to ``ctk.CTkFrame(fg_color=…)``.

    Both forms are reachable from a user-typed entry
    (``settings_vsp_segments.py``, ``vision_segments.py``), so both are here.
    """
    manager = VPSManager(str(tmp_path / "scv_create_helpers.db"))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]

        manager.create_vision_subsegment(seg_name, "Scv Short", color_hex="#abc")
        manager.create_vision_subsegment(seg_name, "Scv Bare", color_hex="abcdef")
        manager.create_vision_subsegment(seg_name, "Scv Bad", color_hex="#0X1234")

        # Asserted against the TABLE, not against get_vision_subsegments:
        # SCV-M3.1's repair pass canonicalises on read, so reading the rows
        # back through it hides exactly the value this finding is about. The
        # consumers that matter here -- db_manager_project_boards' two
        # `vc.color_hex AS category_color_hex` selects -- do not go through it.
        stored = {r["name"]: r["color_hex"] for r in manager.db.conn.execute(
            "SELECT name, color_hex FROM vision_subsegments").fetchall()}
        assert stored["Scv Short"] == "#AABBCC", stored
        assert stored["Scv Bare"] == "#ABCDEF", stored
        assert normalize_hex_color(stored["Scv Bad"]) == stored["Scv Bad"], stored
    finally:
        manager.close()


def test_scvm61_the_category_helper_stores_a_normalised_colour(tmp_path):
    """SCV-M6.1 (high) — the category half, driven through its own helper.

    ``create_vision_category`` is the surface the Vision Elements dialog uses,
    and unlike the subsegment path it has no follow-up
    ``update_vision_category`` to normalise after the fact.
    """
    manager = VPSManager(str(tmp_path / "scv_create_category.db"))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]
        manager.create_vision_subsegment(seg_name, "Scv Sub")
        manager.create_vision_category(seg_name, "Scv Sub", "Scv Short", color_hex="#abc")
        manager.create_vision_category(seg_name, "Scv Sub", "Scv Bare", color_hex="abcdef")

        stored = {r["name"]: r["color_hex"] for r in manager.db.conn.execute(
            "SELECT name, color_hex FROM vision_categories").fetchall()}
        assert stored["Scv Short"] == "#AABBCC", stored
        assert stored["Scv Bare"] == "#ABCDEF", stored
    finally:
        manager.close()


def test_scvm62_the_segment_editor_opens_on_a_malformed_stored_colour(tmp_path):
    """SCV-M6.2 (high) — the one UI that can repair the value must open on it.

    ``load_segment_data`` did
    ``self.color_preview.configure(fg_color=self.segment['color_hex'])`` with
    the stored text. ``segment_descriptions`` has no repair pass -- only
    subsegments and categories do -- so a database written by the old
    validator still holds ``#0X1234``, and the dialog raised ``TclError``
    opening on it. P13: the guard went on save and not on load, in the file
    the batch was already editing.

    The entry still shows the stored text, because the user has to see what is
    there to correct it; only the swatch takes the fallback.
    """
    import customtkinter as ctk

    manager = VPSManager(str(tmp_path / "scv_editor_load.db"))
    try:
        segment_id = manager.create_segment("Scv Load", "desc", "#123456", 96)
        _seed_malformed(manager, "segment_descriptions", segment_id, "#0X1234")
        segment = dict(manager.get_segment(segment_id))
        assert segment["color_hex"] == "#0X1234"

        root = ctk.CTk()
        root.withdraw()
        try:
            dialog = VPSSegmentEditorDialog(root, manager, segment)
            assert dialog.color_entry.get() == "#0X1234", (
                "the user cannot see the value they have to correct")
            assert normalize_hex_color(dialog.selected_color) == dialog.selected_color, (
                f"the swatch colour is still unreadable: {dialog.selected_color!r}")
        finally:
            root.destroy()
    finally:
        manager.close()


def test_scvm63_the_accent_stripe_refuses_an_unreadable_colour():
    """SCV-M6.3 — ``row_fill`` is not the last gate before Tk.

    ``row_fill``'s docstring claimed it was, as the reason SCV-M4.1 could drop
    the fill. In all five row builders the next statement is
    ``apply_segment_accent(frame, segment_color)`` with the same raw value,
    and ``theme.py`` passes it to ``ctk.CTkFrame(fg_color=…)`` -- so a value
    Tk cannot parse raised two lines after the gate that was supposed to stop
    it, taking down the same refresh. P5: harden the class, not one member.

    Driven against real Tk, because the claim is about what Tk does.
    """
    import customtkinter as ctk
    from src.getmoredone.theme import apply_segment_accent

    root = ctk.CTk()
    root.withdraw()
    try:
        for colour in ("#0X1234", "#1_2345", "#+12345", "navy", "#GGHHII"):
            frame = ctk.CTkFrame(root)
            apply_segment_accent(frame, colour)
            assert not frame.winfo_children(), (
                f"{colour!r} was drawn as a stripe")

        frame = ctk.CTkFrame(root)
        apply_segment_accent(frame, "#abc")
        assert len(frame.winfo_children()) == 1, "a readable colour lost its stripe"
    finally:
        root.destroy()


def test_scvm63_the_colour_maps_normalise_what_they_hand_out():
    """SCV-M6.3 — ``segment_color_utils._normalize_color`` validated nothing.

    It is the owner of the colours the five list screens and Vision Elements
    draw with -- both the fill and the accent -- and it only stripped
    whitespace. One gate here covers every consumer downstream of it.
    """
    from src.getmoredone.screens.segment_color_utils import (
        DEFAULT_SEGMENT_COLOR, _normalize_color,
    )

    assert normalize_hex_color(DEFAULT_SEGMENT_COLOR) == DEFAULT_SEGMENT_COLOR
    for colour in ("#0X1234", "#1_2345", "#+12345", "navy", "#GGHHII"):
        assert _normalize_color(colour) is None, colour
    assert _normalize_color("#abc") == "#AABBCC"
    assert _normalize_color("  #aabbcc  ") == "#AABBCC"
    assert _normalize_color(None) is None
    assert _normalize_color("") is None


def test_scvm63_the_colour_dialogs_open_on_a_malformed_stored_colour():
    """SCV-M6.3 — the same raise as SCV-M6.2, in the other colour editor.

    ``vision_segments._color_input`` built its swatch with
    ``fg_color=initial`` straight from ``row["color_hex"]``, and all three
    dialogs that edit a colour here -- segment, subsegment, category -- go
    through it. So the screen the user is sent to in order to repair a value
    raised on opening. Same family as ``vps_segment_editor``: P5, both
    members or neither.

    Called unbound: the helper reads no attribute of the screen, and
    constructing the screen needs a database and a parent app.
    """
    import customtkinter as ctk
    from src.getmoredone.screens.vision_segments import (
        DEFAULT_SWATCH_COLOR, VisionSegmentsScreen,
    )

    assert normalize_hex_color(DEFAULT_SWATCH_COLOR) == DEFAULT_SWATCH_COLOR

    root = ctk.CTk()
    root.withdraw()
    try:
        for colour in ("#0X1234", "#1_2345", "#+12345", "#GGHHII"):
            row, var = VisionSegmentsScreen._color_input(None, root, colour)
            assert var.get() == colour, (
                f"the entry no longer shows the stored {colour!r} to correct")
            swatch = row.winfo_children()[0]
            drawn = swatch.cget("fg_color")
            assert drawn == DEFAULT_SWATCH_COLOR, (
                f"the swatch for {colour!r} was drawn as {drawn!r}")

        row, var = VisionSegmentsScreen._color_input(None, root, "#1a2b3c")
        assert row.winfo_children()[0].cget("fg_color") == "#1A2B3C"
        assert var.get() == "#1a2b3c", "a readable colour was rewritten in the entry"
    finally:
        root.destroy()


def test_scvm65_the_repair_pass_says_what_it_rewrote(tmp_path, caplog):
    """SCV-M6.5 — the pass that destroys a stored value must say so.

    ``row_fill`` warns once per unreadable colour, and the pass that actually
    overwrites the row wrote silently: no line, no count. Global rule 6 and
    P2 -- surface what was changed, "N of M". Without it the only report of a
    colour changing by itself is the user's, with nothing in ``app.log`` to
    confirm or deny it.
    """
    import logging

    manager = VPSManager(str(tmp_path / "scv_repair_log.db"))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]
        manager.create_vision_subsegment(seg_name, "Scv Sub")
        manager.create_or_get_vision_element(seg_name, "Scv Sub", "Scv Cat")
        sub = manager.get_vision_subsegments(seg_name)[0]
        _seed_malformed(manager, "vision_subsegments", sub["id"], "#0X1234")

        with caplog.at_level(logging.WARNING,
                             logger="src.getmoredone.vps_manager_taxonomy"):
            manager.get_vision_subsegments(seg_name)

        messages = [r.getMessage() for r in caplog.records]
        assert messages, "the repair pass rewrote a row and said nothing"
        joined = " ".join(messages)
        assert "#0X1234" in joined, (
            f"the log does not name the value that was replaced: {messages}")
        assert "1 of 1" in joined, (
            f"the log does not say how many of how many: {messages}")
    finally:
        manager.close()


def test_scvm66_the_category_pass_does_not_requery_per_row(tmp_path):
    """SCV-M6.6 — the nested call is hoisted out of the loop.

    ``get_vision_categories`` called ``self.get_vision_subsegments(...)``
    inside its row loop. That call ends in ``commit()``, which committed the
    category UPDATEs already applied earlier in the same loop — so the outer
    pass had no atomicity of its own — and it is an N+1: a full subsegment
    query *and* repair pass per bad category row, each of which runs
    ``get_segment_color_map`` again. SCV-M3.1 widened which rows enter that
    branch, so the nesting now fires where it did not before.

    Counted, not reasoned: three bad rows, and the inner call must happen at
    most once.
    """
    db_path = tmp_path / "scv_nested.db"
    manager = VPSManager(str(db_path))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]
        manager.create_vision_subsegment(seg_name, "Scv Sub")
        for name in ("Cat A", "Cat B", "Cat C"):
            manager.create_or_get_vision_element(seg_name, "Scv Sub", name)
        cats = manager.get_vision_categories(seg_name, "Scv Sub")
        assert len(cats) == 3
        for cat in cats:
            _seed_malformed(manager, "vision_categories", cat["id"], "#0X1234")

        calls = {"subsegments": 0, "colour_map": 0}
        real_subsegments = type(manager).get_vision_subsegments
        real_map = type(manager).get_segment_color_map

        def counting_subsegments(self, *args, **kwargs):
            calls["subsegments"] += 1
            return real_subsegments(self, *args, **kwargs)

        def counting_map(self, *args, **kwargs):
            calls["colour_map"] += 1
            return real_map(self, *args, **kwargs)

        type(manager).get_vision_subsegments = counting_subsegments
        type(manager).get_segment_color_map = counting_map
        try:
            repaired = manager.get_vision_categories(seg_name, "Scv Sub")
        finally:
            type(manager).get_vision_subsegments = real_subsegments
            type(manager).get_segment_color_map = real_map

        assert len(repaired) == 3
        for row in repaired:
            assert normalize_hex_color(row["color_hex"]) == row["color_hex"], row
        assert calls["subsegments"] <= 1, (
            f"three bad rows made {calls['subsegments']} subsegment queries")
        assert calls["colour_map"] <= 1, (
            f"three bad rows made {calls['colour_map']} colour-map queries")
    finally:
        manager.close()


def test_scvm67_an_unloaded_segment_colour_is_not_persisted(tmp_path):
    """SCV-M6.7 — a fallback is not a decision (P1).

    When the stored colour is unreadable the pass derives one from
    ``resolve_segment_color(segment_name, color_map)``, which answers
    ``#64748B`` for a segment with no ``segment_descriptions`` row at all.
    ``get_vision_subsegments`` does not sync the two tables first, so that
    state is reachable — and the grey derived from it used to be *written*,
    where it became a valid value the pass would never revisit. A transient
    "the segment colour is not there" turned terminal.

    The row still shows a colour, so nothing on screen changes; it is only
    not written.
    """
    db_path = tmp_path / "scv_unloaded.db"
    manager = VPSManager(str(db_path))
    try:
        seg_name = manager.get_all_segments(active_only=False)[0]["name"]
        manager.create_vision_subsegment(seg_name, "Scv Sub")
        manager.create_or_get_vision_element(seg_name, "Scv Sub", "Scv Cat")
        sub = manager.get_vision_subsegments(seg_name)[0]
        _seed_malformed(manager, "vision_subsegments", sub["id"], "#0X1234")

        # The segment leaves Settings but its vision_segments row survives,
        # which is the state resolve_segment_color falls back for.
        manager.db.conn.execute(
            "DELETE FROM segment_descriptions WHERE LOWER(name) = LOWER(?)",
            (seg_name,),
        )
        manager.db.conn.commit()
        assert seg_name.strip().lower() not in manager.get_segment_color_map()

        shown = manager.get_vision_subsegments(seg_name)[0]["color_hex"]
        assert normalize_hex_color(shown) == shown, shown
    finally:
        manager.close()

    reopened = VPSManager(str(db_path))
    try:
        stored = reopened.db.conn.execute(
            "SELECT color_hex FROM vision_subsegments WHERE id = ?", (sub["id"],)
        ).fetchone()["color_hex"]
        assert stored == "#0X1234", (
            f"a colour guessed from a missing segment was persisted as {stored!r}")
    finally:
        reopened.close()
