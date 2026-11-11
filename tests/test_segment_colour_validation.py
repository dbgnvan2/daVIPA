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

#: The §1 table: what ``int(…, 16)`` let through, and the one six-digit value
#: in the same family that must keep working. ``#0b1010`` is not a defect --
#: it is six hex digits that merely *look* like a Python literal.
INT_BASE_16_ACCEPTS = ("#0X1234", "#1_2345", "#+12345")
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


def test_scvm22_a_colour_that_parses_wrongly_is_not_derived_from():
    """SCV-M2.2 — ``#+12345`` must not derive ``#0B368D`` from a misread slice.

    Spec:  docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m2

    P7, the adversarial case, and the one that matters more than the two
    crashes above: this value raised nothing. ``int("+1", 16)`` is 1,
    ``int("23", 16)`` is 35, ``int("45", 16)`` is 69, so a colour was derived
    and drawn and nobody was told. A crash is visible; this is not.
    """
    assert _derive("#+12345") != "#0B368D", (
        "a colour is still being derived from a misread slice")
    assert _derive("#+12345") == _derive(FALLBACK_BASE)


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
