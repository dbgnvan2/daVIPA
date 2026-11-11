"""Vision taxonomy and vision-element support for `VPSManager`."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from .color_contrast import normalize_hex_color
from .link_integrity import resolve_segment_id_exact


logger = logging.getLogger(__name__)


class VisionElementHasDependentsError(Exception):
    """Raised when a Vision Element cannot be deleted because child records
    (annual plan records, projects, or linked action items) still exist.

    Purpose: Force the user to delete or reassign child items before deleting a
             Vision Element, instead of cascading away annual records / failing
             with a raw RESTRICT foreign-key error on attached project boards.
    Spec:    docs/unused-docs/changes/2026-06-15-project-ape-linking.md
    Tests:   tests/test_vps_hub_crud.py::test_delete_vision_element_blocked_when_children_exist
    """

    def __init__(self, summary_lines: List[str]):
        self.summary_lines = summary_lines
        super().__init__("Cannot delete Vision Element: " + "; ".join(summary_lines))


class VPSTaxonomyMixin:
    @staticmethod
    def _report_colour_repair(table: str, read: int,
                              rewritten: "List[tuple]",
                              shown_only: "List[tuple]") -> None:
        """Say what a colour repair pass changed, and what it would not write.

        Purpose: SCV-M6.5 -- the pass overwrote a stored colour and said
                 nothing: no line, no count. ``row_fill`` warns when it
                 *refuses* a colour, so the only silent step was the one that
                 destroyed the value. Global rule 6 and P2: "N of M", and
                 name what was excluded.
        Spec:    docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md#scv-m3
        Tests:   tests/test_segment_colour_validation.py::test_scvm65_the_repair_pass_says_what_it_rewrote

        One line per pass rather than one per row: the first read after an
        upgrade canonicalises every row whose colour is not already upper-case
        ``#RRGGBB``, and a line each would be the whole log.
        """
        if rewritten:
            logger.warning(
                "%s colour repair: rewrote %d of %d row(s) read -- %s",
                table, len(rewritten), read,
                "; ".join(f"{row_id}: {stored!r} -> {new}"
                          for row_id, stored, new in rewritten),
            )
        if shown_only:
            logger.warning(
                "%s colour repair: %d of %d row(s) read were shown a fallback "
                "and left as stored, because their segment has no Settings "
                "entry to take a colour from -- %s",
                table, len(shown_only), read,
                "; ".join(f"{row_id}: {stored!r} shown as {new}"
                          for row_id, stored, new in shown_only),
            )

    def sync_vision_elements_with_taxonomy(self):
        """Ensure every Segment/SubSegment/Category row has a Vision Element key row."""
        rows = self.db.conn.execute(
            """
            SELECT
                s.id AS segment_id,
                s.name AS segment_name,
                ss.id AS subsegment_id,
                ss.name AS subsegment_name,
                c.id AS category_id,
                c.name AS category_name
            FROM vision_categories c
            JOIN vision_subsegments ss ON ss.id = c.subsegment_id
            JOIN vision_segments s ON s.id = ss.segment_id
            ORDER BY s.name COLLATE NOCASE ASC, ss.name COLLATE NOCASE ASC, c.name COLLATE NOCASE ASC
            """
        ).fetchall()

        now = datetime.now().isoformat()
        changed = False
        for row in rows:
            key_field = f"{row['segment_name']}|{row['subsegment_name']}|{row['category_name']}"
            existing = self.db.conn.execute(
                """
                SELECT id, key_field FROM vision_elements
                WHERE category_id = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (row["category_id"],),
            ).fetchone()
            if existing:
                if (existing["key_field"] or "") != key_field:
                    conflict = self.db.conn.execute(
                        "SELECT id FROM vision_elements WHERE key_field = ? AND id <> ?",
                        (key_field, existing["id"]),
                    ).fetchone()
                    if not conflict:
                        self.db.conn.execute(
                            """
                            UPDATE vision_elements
                            SET segment_id = ?, subsegment_id = ?, category_id = ?, key_field = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                row["segment_id"],
                                row["subsegment_id"],
                                row["category_id"],
                                key_field,
                                now,
                                existing["id"],
                            ),
                        )
                        self._sync_vision_element_derived_fields(existing["id"])
                        changed = True
                continue

            self.db.conn.execute(
                """
                INSERT INTO vision_elements
                (id, segment_id, subsegment_id, category_id, key_field, vision_text, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    f"ve-{uuid4().hex[:8]}",
                    row["segment_id"],
                    row["subsegment_id"],
                    row["category_id"],
                    key_field,
                    "",
                    now,
                    now,
                ),
            )
            changed = True

        if changed:
            self.db.conn.commit()

    def get_vision_segments(self) -> List[Dict[str, Any]]:
        self.sync_vision_segments_with_settings()
        cursor = self.db.conn.execute(
            "SELECT * FROM vision_segments ORDER BY name COLLATE NOCASE ASC"
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_vision_subsegments(self, segment_name: Optional[str] = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        query = """
            SELECT ss.*, s.name AS segment_name
            FROM vision_subsegments ss
            JOIN vision_segments s ON s.id = ss.segment_id
        """
        if segment_name:
            query += " WHERE LOWER(s.name) = LOWER(?)"
            params.append(segment_name.strip())
        query += " ORDER BY s.name COLLATE NOCASE ASC, ss.name COLLATE NOCASE ASC"
        cursor = self.db.conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        # SCV-M3.1: the gate was ``_is_valid_hex_color``, which called
        # ``#0X1234`` valid, so the pass that exists to replace a bad colour
        # skipped exactly the class of bad colour that then crashed the read.
        # It now asks ``normalize_hex_color``, and writes whenever the stored
        # text is not already the form it should be stored in.
        # Tests: tests/test_segment_colour_validation.py::test_scvm31_the_repair_pass_sees_a_malformed_stored_colour
        #
        # SCV-M6.6: the colour map is fetched at most once per call, not once
        # per row that needs a derived colour.
        # SCV-M6.7: a colour derived from a segment with no Settings entry is
        # shown and not stored -- see ``_report_colour_repair``.
        color_map: Optional[Dict[str, str]] = None
        rewritten: List[tuple] = []
        shown_only: List[tuple] = []
        for row in rows:
            stored = row.get("color_hex")
            color = normalize_hex_color(stored)
            guessed = False
            if color is None:
                if color_map is None:
                    color_map = self.get_segment_color_map()
                parent = self.match_segment_color(row.get("segment_name", ""), color_map)
                guessed = parent is None
                if parent is None:
                    parent = self.resolve_segment_color(row.get("segment_name", ""), color_map)
                color = self._derive_subsegment_color(parent)
            if color == stored:
                continue
            row["color_hex"] = color
            if guessed:
                shown_only.append((row["id"], stored, color))
                continue
            self.db.conn.execute(
                "UPDATE vision_subsegments SET color_hex = ?, updated_at = ? WHERE id = ?",
                (color, datetime.now().isoformat(), row["id"]),
            )
            rewritten.append((row["id"], stored, color))
        if rewritten:
            self.db.conn.commit()
        self._report_colour_repair("vision_subsegments", len(rows), rewritten, shown_only)
        return rows

    def get_vision_categories(self, segment_name: Optional[str] = None,
                              subsegment_name: Optional[str] = None) -> List[Dict[str, Any]]:
        params: List[Any] = []
        query = """
            SELECT c.*, ss.name AS subsegment_name, s.name AS segment_name
            FROM vision_categories c
            JOIN vision_subsegments ss ON ss.id = c.subsegment_id
            JOIN vision_segments s ON s.id = ss.segment_id
            WHERE 1=1
        """
        if segment_name:
            query += " AND LOWER(s.name) = LOWER(?)"
            params.append(segment_name.strip())
        if subsegment_name:
            query += " AND LOWER(ss.name) = LOWER(?)"
            params.append(subsegment_name.strip())
        query += " ORDER BY s.name COLLATE NOCASE ASC, ss.name COLLATE NOCASE ASC, c.name COLLATE NOCASE ASC"
        cursor = self.db.conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        # SCV-M3.1, as in ``get_vision_subsegments`` above. The inner
        # ``if not self._is_valid_hex_color(sub_color)`` that stood here was
        # dead: ``sub_color`` was this row's own colour, which the outer gate
        # had already declared invalid, so the condition was always true.
        #
        # SCV-M6.6: ``get_vision_subsegments`` and the colour map are fetched
        # at most once per call. They stood inside the loop, so three bad rows
        # meant three subsegment queries -- each one a repair pass of its own
        # ending in ``commit()``, which committed this loop's half-applied
        # UPDATEs as a side effect. SCV-M3.1 widened which rows take this
        # branch, so the nesting fires where it did not before.
        # SCV-M6.7: a colour derived from a segment with no Settings entry is
        # shown and not stored.
        subsegments: Optional[List[Dict[str, Any]]] = None
        color_map: Optional[Dict[str, str]] = None
        rewritten: List[tuple] = []
        shown_only: List[tuple] = []
        for row in rows:
            stored = row.get("color_hex")
            color = normalize_hex_color(stored)
            guessed = False
            if color is None:
                if subsegments is None:
                    # ``None``, not this row's segment: when the caller gave no
                    # segment the rows span several, and one unfiltered read is
                    # a superset of every per-row read it replaces.
                    subsegments = self.get_vision_subsegments(segment_name)
                sub = next(
                    (s for s in subsegments
                     if (s.get("name") or "").lower() == (row.get("subsegment_name") or "").lower()
                     and (s.get("segment_name") or "").lower() == (row.get("segment_name") or "").lower()),
                    None,
                )
                sub_color = normalize_hex_color((sub or {}).get("color_hex"))
                if sub_color is None:
                    if color_map is None:
                        color_map = self.get_segment_color_map()
                    seg = row.get("segment_name") or ""
                    parent = self.match_segment_color(seg, color_map)
                    guessed = parent is None
                    if parent is None:
                        parent = self.resolve_segment_color(seg, color_map)
                    sub_color = self._derive_subsegment_color(parent)
                color = self._derive_subsegment_color(sub_color)
            if color == stored:
                continue
            row["color_hex"] = color
            if guessed:
                shown_only.append((row["id"], stored, color))
                continue
            self.db.conn.execute(
                "UPDATE vision_categories SET color_hex = ?, updated_at = ? WHERE id = ?",
                (color, datetime.now().isoformat(), row["id"]),
            )
            rewritten.append((row["id"], stored, color))
        if rewritten:
            self.db.conn.commit()
        self._report_colour_repair("vision_categories", len(rows), rewritten, shown_only)
        return rows

    def _create_or_get_vision_segment(self, name: str) -> str:
        now = datetime.now().isoformat()
        norm = name.strip()
        settings_row = self.db.conn.execute(
            "SELECT name FROM segment_descriptions WHERE LOWER(name) = LOWER(?)",
            (norm,),
        ).fetchone()
        if not settings_row:
            raise ValueError(
                f"Segment '{norm}' does not exist in Vision Elements. Create it in VSP Plan -> Vision Elements first."
            )
        norm = settings_row["name"]
        row = self.db.conn.execute(
            "SELECT id FROM vision_segments WHERE LOWER(name) = LOWER(?)",
            (norm,)
        ).fetchone()
        if row:
            return row["id"]
        seg_id = f"vsg-{uuid4().hex[:8]}"
        # RN-M1.C: link to the segment description of the same name if there is
        # exactly one. None is correct when there is not — the row is reported
        # by the migration rather than guessed at (RN-INV5).
        description_id = resolve_segment_id_exact(self.db.conn, norm)
        self.db.conn.execute(
            "INSERT INTO vision_segments "
            "(id, name, vision_text, segment_description_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (seg_id, norm, "", description_id, now, now)
        )
        return seg_id

    def _create_or_get_vision_subsegment(
        self,
        segment_id: str,
        name: str,
        color_hex: Optional[str] = None,
        description: str = "",
        vision_text: str = "",
    ) -> str:
        now = datetime.now().isoformat()
        norm = name.strip()
        row = self.db.conn.execute(
            "SELECT id FROM vision_subsegments WHERE segment_id = ? AND LOWER(name) = LOWER(?)",
            (segment_id, norm)
        ).fetchone()
        if row:
            return row["id"]

        seg_row = self.db.conn.execute(
            "SELECT name FROM vision_segments WHERE id = ?",
            (segment_id,),
        ).fetchone()
        seg_name = (seg_row["name"] if seg_row else "").strip()
        base_color = self.resolve_segment_color(seg_name, self.get_segment_color_map())
        default_color = self._derive_subsegment_color(base_color)
        # SCV-M6.1: normalise, do not gate-then-store-raw. This read
        # ``if not self._is_valid_hex_color(chosen_color)`` over the text as
        # typed; once that gate reads ``#abc`` and ``abcdef``, both became
        # "valid" and were written verbatim to a column that
        # ``db_manager_project_boards`` selects directly, bypassing the repair
        # pass, on its way to ``fg_color``.
        chosen_color = normalize_hex_color(color_hex) or default_color

        sub_id = f"vss-{uuid4().hex[:8]}"
        self.db.conn.execute(
            "INSERT INTO vision_subsegments (id, segment_id, name, color_hex, description, vision_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sub_id, segment_id, norm, chosen_color, (description or "").strip(), (vision_text or "").strip(), now, now)
        )
        return sub_id

    def _resolve_vision_subsegment_id(self, segment_id: str, name: str) -> Optional[str]:
        row = self.db.conn.execute(
            "SELECT id FROM vision_subsegments WHERE segment_id = ? AND LOWER(name) = LOWER(?)",
            (segment_id, (name or "").strip()),
        ).fetchone()
        return row["id"] if row else None

    def _create_or_get_vision_category(
        self,
        subsegment_id: str,
        name: str,
        color_hex: Optional[str] = None,
        description: str = "",
        vision_text: str = "",
    ) -> str:
        now = datetime.now().isoformat()
        norm = name.strip()
        row = self.db.conn.execute(
            "SELECT id FROM vision_categories WHERE subsegment_id = ? AND LOWER(name) = LOWER(?)",
            (subsegment_id, norm)
        ).fetchone()
        if row:
            return row["id"]
        sub_row = self.db.conn.execute(
            "SELECT color_hex FROM vision_subsegments WHERE id = ?",
            (subsegment_id,),
        ).fetchone()
        sub_color = (sub_row["color_hex"] if sub_row else "") or "#64748B"
        default_color = self._derive_subsegment_color(sub_color)
        # SCV-M6.1, as in ``_create_or_get_vision_subsegment`` above. The
        # category path has no follow-up ``update_vision_category`` to
        # normalise after the fact, so this is the only gate it gets.
        chosen_color = normalize_hex_color(color_hex) or default_color
        cat_id = f"vct-{uuid4().hex[:8]}"
        self.db.conn.execute(
            "INSERT INTO vision_categories (id, subsegment_id, name, color_hex, description, vision_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cat_id, subsegment_id, norm, chosen_color, (description or "").strip(), (vision_text or "").strip(), now, now)
        )
        return cat_id

    def create_or_get_vision_element(self, segment_name: str, subsegment_name: str, category_name: str) -> str:
        """Create linked Segment/SubSegment/Category and the Vision Element key record."""
        segment_name = segment_name.strip()
        subsegment_name = subsegment_name.strip()
        category_name = category_name.strip()
        if not segment_name or not subsegment_name or not category_name:
            raise ValueError("Segment, SubSegment, and Category are required")

        seg_id = self._create_or_get_vision_segment(segment_name)
        sub_id = self._resolve_vision_subsegment_id(seg_id, subsegment_name)
        if not sub_id:
            raise ValueError(
                f"SubSegment '{subsegment_name}' does not exist under '{segment_name}'. "
                "Create it in VSP Plan -> Vision Elements first."
            )
        cat_id = self._create_or_get_vision_category(sub_id, category_name)

        key_field = f"{segment_name}|{subsegment_name}|{category_name}"
        now = datetime.now().isoformat()
        row = self.db.conn.execute(
            "SELECT id FROM vision_elements WHERE key_field = ?",
            (key_field,)
        ).fetchone()
        if row:
            self.db.conn.commit()
            return row["id"]

        ve_id = f"ve-{uuid4().hex[:8]}"
        self.db.conn.execute("""
            INSERT INTO vision_elements (id, segment_id, subsegment_id, category_id, key_field, vision_text, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (ve_id, seg_id, sub_id, cat_id, key_field, "", now, now))
        self.db.conn.commit()
        return ve_id

    def update_vision_subsegment_color(self, subsegment_id: str, color_hex: str) -> bool:
        """Update a subsegment color.

        SCV-M1.1/M3.1: the normalised form is what is stored. The gate used to
        be ``_is_valid_hex_color`` over ``.strip().upper()``, and now that the
        gate reads ``#abc``, storing the text as given would write a
        four-character colour to the table.
        """
        value = normalize_hex_color(color_hex)
        if value is None:
            raise ValueError("Invalid color. Use format #RRGGBB.")
        cur = self.db.conn.execute(
            "UPDATE vision_subsegments SET color_hex = ?, updated_at = ? WHERE id = ?",
            (value, datetime.now().isoformat(), subsegment_id),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

    def get_vision_elements(self) -> List[Dict[str, Any]]:
        self.sync_vision_elements_with_taxonomy()
        cursor = self.db.conn.execute("""
            SELECT
                ve.id,
                ve.key_field,
                ve.vision_text,
                s.id AS segment_id,
                s.name AS segment_name,
                s.vision_text AS segment_vision_text,
                ss.id AS subsegment_id,
                ss.name AS subsegment_name,
                ss.color_hex AS subsegment_color_hex,
                ss.vision_text AS subsegment_vision_text,
                c.id AS category_id,
                c.name AS category_name,
                c.vision_text AS category_vision_text
            FROM vision_elements ve
            JOIN vision_segments s ON s.id = ve.segment_id
            JOIN vision_subsegments ss ON ss.id = ve.subsegment_id
            JOIN vision_categories c ON c.id = ve.category_id
            WHERE ve.is_active = 1
            ORDER BY s.name COLLATE NOCASE ASC, ss.name COLLATE NOCASE ASC, c.name COLLATE NOCASE ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def update_vision_element(
        self,
        vision_element_id: str,
        segment_name: str,
        subsegment_name: str,
        category_name: str,
        vision_text: Optional[str] = None,
    ) -> bool:
        """Update a Vision Element and keep annual mirrors in sync."""
        segment_name = (segment_name or "").strip()
        subsegment_name = (subsegment_name or "").strip()
        category_name = (category_name or "").strip()
        if not segment_name or not subsegment_name or not category_name:
            raise ValueError("Segment, SubSegment, and Category are required")

        row = self.db.conn.execute(
            "SELECT id, key_field FROM vision_elements WHERE id = ?",
            (vision_element_id,),
        ).fetchone()
        if not row:
            return False
        # Captured before any write: the derived-title refresh needs it.
        previous_key_field = row["key_field"]

        seg_id = self._create_or_get_vision_segment(segment_name)
        sub_id = self._resolve_vision_subsegment_id(seg_id, subsegment_name)
        if not sub_id:
            raise ValueError(
                f"SubSegment '{subsegment_name}' does not exist under '{segment_name}'. "
                "Create it in VSP Plan -> Vision Elements first."
            )
        cat_id = self._create_or_get_vision_category(sub_id, category_name)
        key_field = f"{segment_name}|{subsegment_name}|{category_name}"
        now = datetime.now().isoformat()
        vision_value = (vision_text or "").strip() if vision_text is not None else None

        if vision_value is None:
            self.db.conn.execute(
                """
                UPDATE vision_elements
                SET segment_id = ?, subsegment_id = ?, category_id = ?, key_field = ?, updated_at = ?
                WHERE id = ?
                """,
                (seg_id, sub_id, cat_id, key_field, now, vision_element_id),
            )
        else:
            self.db.conn.execute(
                """
                UPDATE vision_elements
                SET segment_id = ?, subsegment_id = ?, category_id = ?, key_field = ?, vision_text = ?, updated_at = ?
                WHERE id = ?
                """,
                (seg_id, sub_id, cat_id, key_field, vision_value, now, vision_element_id),
            )

        # Keep derived annual records aligned.
        self.db.conn.execute(
            """
            UPDATE annual_vision_elements
            SET segment_name = ?, subsegment_name = ?, category_name = ?, key_field = ?,
                -- COALESCE: resolve_segment_id_exact returns None when the
                -- name is ambiguous, and overwriting a GOOD id with NULL
                -- because two descriptions differ only by case would be a
                -- worse bug than the one this column fixes.
                segment_description_id = COALESCE(?, segment_description_id),
                updated_at = ?
            WHERE vision_element_id = ?
            """,
            (segment_name, subsegment_name, category_name, key_field,
             resolve_segment_id_exact(self.db.conn, segment_name), now, vision_element_id),
        )
        self.db.conn.execute(
            """
            UPDATE annual_plan_elements
            SET segment_name = ?, subsegment_name = ?, category_name = ?, key_field = ?,
                -- COALESCE: resolve_segment_id_exact returns None when the
                -- name is ambiguous, and overwriting a GOOD id with NULL
                -- because two descriptions differ only by case would be a
                -- worse bug than the one this column fixes.
                segment_description_id = COALESCE(?, segment_description_id),
                updated_at = ?
            WHERE vision_element_id = ?
            """,
            (segment_name, subsegment_name, category_name, key_field,
             resolve_segment_id_exact(self.db.conn, segment_name), now, vision_element_id),
        )
        # RN-M3.A — refresh the derived Annual Initiative title here too.
        # The refresh was added to _sync_vision_element_derived_fields only,
        # and this is its near-identical sibling: renaming or re-pointing
        # through THIS path left the initiative showing the old composite.
        # Delegating rather than pasting a third copy — the duplication
        # between these two functions is what produced the gap.
        # RE-POINT: the stored segment id is stale by construction here, so
        # COALESCE's "keep what is there" is wrong on this path — it left the
        # plan element on the OLD segment when the new name was ambiguous.
        # Clearing it is correct: RN-M5 then names the row, and
        # _segment_id_for_ape still answers the cascade from the name.
        repointed = resolve_segment_id_exact(self.db.conn, segment_name)
        for table in ("annual_vision_elements", "annual_plan_elements"):
            self.db.conn.execute(
                f"UPDATE {table} SET segment_description_id = ? "
                "WHERE vision_element_id = ?",
                (repointed, vision_element_id),
            )

        self._sync_vision_element_derived_fields(
            vision_element_id, previous_key_field=previous_key_field
        )
        self.db.conn.commit()
        return True

    def _sync_vision_element_derived_fields(
        self, vision_element_id: str, previous_key_field: str = None
    ):
        """Recompute key_field and annual mirror names for one vision element."""
        row = self.db.conn.execute(
            """
            SELECT ve.id, s.name AS segment_name, ss.name AS subsegment_name, c.name AS category_name
            FROM vision_elements ve
            JOIN vision_segments s ON s.id = ve.segment_id
            JOIN vision_subsegments ss ON ss.id = ve.subsegment_id
            JOIN vision_categories c ON c.id = ve.category_id
            WHERE ve.id = ?
            """,
            (vision_element_id,),
        ).fetchone()
        if not row:
            return

        segment_name = row["segment_name"]
        subsegment_name = row["subsegment_name"]
        category_name = row["category_name"]
        key_field = f"{segment_name}|{subsegment_name}|{category_name}"
        now = datetime.now().isoformat()

        # What the composite WAS, so the refresh below can tell a derived title
        # from a hand-edited one. Callers that have ALREADY rewritten
        # vision_elements.key_field must pass it — update_vision_element does,
        # and without that this read returns the NEW value, previous == current,
        # and the refresh silently skips.
        if previous_key_field is None:
            previous = self.db.conn.execute(
                "SELECT key_field FROM vision_elements WHERE id = ?",
                (vision_element_id,),
            ).fetchone()
            previous_key_field = previous["key_field"] if previous else None

        self.db.conn.execute(
            "UPDATE vision_elements SET key_field = ?, updated_at = ? WHERE id = ?",
            (key_field, now, vision_element_id),
        )
        self.db.conn.execute(
            """
            UPDATE annual_vision_elements
            SET segment_name = ?, subsegment_name = ?, category_name = ?, key_field = ?,
                -- COALESCE: resolve_segment_id_exact returns None when the
                -- name is ambiguous, and overwriting a GOOD id with NULL
                -- because two descriptions differ only by case would be a
                -- worse bug than the one this column fixes.
                segment_description_id = COALESCE(?, segment_description_id),
                updated_at = ?
            WHERE vision_element_id = ?
            """,
            (segment_name, subsegment_name, category_name, key_field,
             resolve_segment_id_exact(self.db.conn, segment_name), now, vision_element_id),
        )
        self.db.conn.execute(
            """
            UPDATE annual_plan_elements
            SET segment_name = ?, subsegment_name = ?, category_name = ?, key_field = ?,
                -- COALESCE: resolve_segment_id_exact returns None when the
                -- name is ambiguous, and overwriting a GOOD id with NULL
                -- because two descriptions differ only by case would be a
                -- worse bug than the one this column fixes.
                segment_description_id = COALESCE(?, segment_description_id),
                updated_at = ?
            WHERE vision_element_id = ?
            """,
            (segment_name, subsegment_name, category_name, key_field,
             resolve_segment_id_exact(self.db.conn, segment_name), now, vision_element_id),
        )
        # RN-M3.A / RN-D7 — an Annual Initiative's title is DERIVED from the
        # APE's key field, the same way a Weekly Tactic's is derived from its
        # APE and week. Leaving it stale after a rename puts two different
        # names on one thing.
        #
        # Joined through annual_plan_element_id, which RN-M1.B added. Matching
        # on the OLD title here would be the very bug this change removes: the
        # rename has already moved the key field by the time this runs.
        # Only titles that are STILL the derived composite. A blanket update
        # here silently discarded a hand-edited title: the Annual Initiative
        # editor offers a Title field and update_annual_initiative persists it,
        # so RN-D7's "the title is derived" is true of how a title STARTS, not
        # of what the user may have made it.
        #
        # `previous_key_field` is what the composite was before this rename, so
        # a title equal to it is one nobody has touched. Anything else is the
        # user's and is left alone.
        if previous_key_field and previous_key_field != key_field:
            self.db.conn.execute(
                """
                UPDATE annual_initiatives
                SET title = ?, updated_at = ?
                WHERE annual_plan_element_id IN (
                    SELECT id FROM annual_plan_elements WHERE vision_element_id = ?
                )
                  AND LOWER(title) = LOWER(?)
                """,
                (key_field, now, vision_element_id, previous_key_field),
            )

    def rename_vision_segment(self, segment_id: str, new_name: str) -> bool:
        new_value = (new_name or "").strip()
        if not new_value:
            raise ValueError("Segment name is required.")

        current = self.db.conn.execute(
            "SELECT id, name FROM vision_segments WHERE id = ?",
            (segment_id,),
        ).fetchone()
        if not current:
            return False

        duplicate = self.db.conn.execute(
            "SELECT id FROM vision_segments WHERE LOWER(name) = LOWER(?) AND id <> ?",
            (new_value, segment_id),
        ).fetchone()
        if duplicate:
            raise ValueError(f"Segment '{new_value}' already exists.")

        try:
            self.db.conn.execute("BEGIN")
            now = datetime.now().isoformat()
            self.db.conn.execute(
                "UPDATE vision_segments SET name = ?, updated_at = ? WHERE id = ?",
                (new_value, now, segment_id),
            )
            # RN-M3.A / RN-INV4 — the linked segment description carries the
            # same name and is what Settings and every colour lookup read.
            # rename_vision_segment updated ONE of the two tables, which is the
            # whole of RN-F2: spec §2 shows vision_segments renamed and
            # segment_descriptions still holding the old value.
            #
            # By id, not by the old name: the id is what RN-M1.C added, and
            # matching on the old name is the pattern being removed.
            self.db.conn.execute(
                """
                UPDATE segment_descriptions
                SET name = ?, updated_at = ?
                WHERE id = (
                    SELECT segment_description_id FROM vision_segments WHERE id = ?
                )
                """,
                (new_value, now, segment_id),
            )
            ve_rows = self.db.conn.execute(
                "SELECT id FROM vision_elements WHERE segment_id = ?",
                (segment_id,),
            ).fetchall()
            for ve in ve_rows:
                self._sync_vision_element_derived_fields(ve["id"])
            self.db.conn.commit()
            return True
        except sqlite3.IntegrityError as exc:
            self.db.conn.rollback()
            raise ValueError(str(exc)) from exc
        except Exception:
            self.db.conn.rollback()
            raise

    def rename_vision_subsegment(self, subsegment_id: str, new_name: str) -> bool:
        new_value = (new_name or "").strip()
        if not new_value:
            raise ValueError("SubSegment name is required.")

        current = self.db.conn.execute(
            "SELECT id, segment_id, name FROM vision_subsegments WHERE id = ?",
            (subsegment_id,),
        ).fetchone()
        if not current:
            return False

        duplicate = self.db.conn.execute(
            """
            SELECT id FROM vision_subsegments
            WHERE segment_id = ? AND LOWER(name) = LOWER(?) AND id <> ?
            """,
            (current["segment_id"], new_value, subsegment_id),
        ).fetchone()
        if duplicate:
            raise ValueError(f"SubSegment '{new_value}' already exists in this Segment.")

        try:
            self.db.conn.execute("BEGIN")
            self.db.conn.execute(
                "UPDATE vision_subsegments SET name = ?, updated_at = ? WHERE id = ?",
                (new_value, datetime.now().isoformat(), subsegment_id),
            )
            ve_rows = self.db.conn.execute(
                "SELECT id FROM vision_elements WHERE subsegment_id = ?",
                (subsegment_id,),
            ).fetchall()
            for ve in ve_rows:
                self._sync_vision_element_derived_fields(ve["id"])
            self.db.conn.commit()
            return True
        except sqlite3.IntegrityError as exc:
            self.db.conn.rollback()
            raise ValueError(str(exc)) from exc
        except Exception:
            self.db.conn.rollback()
            raise

    def rename_vision_category(self, category_id: str, new_name: str) -> bool:
        new_value = (new_name or "").strip()
        if not new_value:
            raise ValueError("Category name is required.")

        current = self.db.conn.execute(
            "SELECT id, subsegment_id, name FROM vision_categories WHERE id = ?",
            (category_id,),
        ).fetchone()
        if not current:
            return False

        duplicate = self.db.conn.execute(
            """
            SELECT id FROM vision_categories
            WHERE subsegment_id = ? AND LOWER(name) = LOWER(?) AND id <> ?
            """,
            (current["subsegment_id"], new_value, category_id),
        ).fetchone()
        if duplicate:
            raise ValueError(f"Category '{new_value}' already exists in this SubSegment.")

        try:
            self.db.conn.execute("BEGIN")
            self.db.conn.execute(
                "UPDATE vision_categories SET name = ?, updated_at = ? WHERE id = ?",
                (new_value, datetime.now().isoformat(), category_id),
            )
            ve_rows = self.db.conn.execute(
                "SELECT id FROM vision_elements WHERE category_id = ?",
                (category_id,),
            ).fetchall()
            for ve in ve_rows:
                self._sync_vision_element_derived_fields(ve["id"])
            self.db.conn.commit()
            return True
        except sqlite3.IntegrityError as exc:
            self.db.conn.rollback()
            raise ValueError(str(exc)) from exc
        except Exception:
            self.db.conn.rollback()
            raise

    def get_vision_element_dependents(self, vision_element_id: str) -> Dict[str, Any]:
        """Summarize child records that block deleting a Vision Element.

        Purpose: List the annual records, projects, and linked action items that
                 must be removed/reassigned before a Vision Element can be deleted.
        Spec:    docs/unused-docs/changes/2026-06-15-project-ape-linking.md
        Tests:   tests/test_vps_hub_crud.py::test_delete_vision_element_blocked_when_children_exist
        """
        years = [
            row["year"]
            for row in self.db.conn.execute(
                "SELECT DISTINCT year FROM annual_plan_elements WHERE vision_element_id = ? ORDER BY year",
                (vision_element_id,),
            ).fetchall()
        ]
        project_titles = [
            row["title"]
            for row in self.db.conn.execute(
                """
                SELECT pb.title
                FROM project_boards pb
                JOIN annual_plan_elements ape ON ape.id = pb.annual_plan_element_id
                WHERE ape.vision_element_id = ?
                ORDER BY pb.title COLLATE NOCASE
                """,
                (vision_element_id,),
            ).fetchall()
        ]
        action_item_count = self.db.conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM action_items ai
            JOIN annual_plan_elements ape ON ape.id = ai.annual_plan_element_id
            WHERE ape.vision_element_id = ?
            """,
            (vision_element_id,),
        ).fetchone()["c"]
        return {
            "years": years,
            "project_titles": project_titles,
            "action_item_count": action_item_count,
        }

    def delete_vision_element(self, vision_element_id: str) -> bool:
        """Delete one Vision Element and derived annual rows via FK cascade.

        Refuses to delete (raising VisionElementHasDependentsError) when child
        records still exist — annual plan records, attached projects, or linked
        action items — so the user must delete or reassign them manually first.
        """
        deps = self.get_vision_element_dependents(vision_element_id)
        if deps["years"] or deps["project_titles"] or deps["action_item_count"]:
            summary_lines: List[str] = []
            if deps["years"]:
                summary_lines.append(
                    f"{len(deps['years'])} annual record(s): {', '.join(str(y) for y in deps['years'])}"
                )
            if deps["project_titles"]:
                summary_lines.append(
                    f"{len(deps['project_titles'])} project(s): {', '.join(deps['project_titles'])}"
                )
            if deps["action_item_count"]:
                summary_lines.append(f"{deps['action_item_count']} linked action item(s)")
            raise VisionElementHasDependentsError(summary_lines)

        cur = self.db.conn.execute(
            "DELETE FROM vision_elements WHERE id = ?",
            (vision_element_id,),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

    def update_segment_vision_text(self, segment_id: str, vision_text: str) -> bool:
        cur = self.db.conn.execute(
            "UPDATE vision_segments SET vision_text = ?, updated_at = ? WHERE id = ?",
            ((vision_text or "").strip(), datetime.now().isoformat(), segment_id),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

    def sync_vision_segments_with_settings(self):
        """Ensure every Settings life segment exists in vision_segments."""
        settings_rows = self.db.conn.execute(
            "SELECT id, name FROM segment_descriptions"
        ).fetchall()
        now = datetime.now().isoformat()
        for row in settings_rows:
            name = (row["name"] or "").strip()
            if not name:
                continue
            existing = self.db.conn.execute(
                "SELECT id, segment_description_id FROM vision_segments "
                "WHERE LOWER(name) = LOWER(?)",
                (name,),
            ).fetchone()
            if not existing:
                # RN-M1.C / RN-M2.C: stamp the id at create time. This runs at
                # every manager init, AFTER the migration, so a row created
                # here without its id would be unlinked until the next launch.
                self.db.conn.execute(
                    "INSERT INTO vision_segments "
                    "(id, name, vision_text, segment_description_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (f"vsg-{uuid4().hex[:8]}", name, "",
                     resolve_segment_id_exact(self.db.conn, name), now, now),
                )
            elif not existing["segment_description_id"]:
                # Heal a legacy row ONLY when the name resolves to exactly one
                # segment description.
                #
                # "we are here and certain" was wrong: this loop iterates
                # segment_descriptions, and two of them can differ only by case
                # ('Health' and 'health' are both legal — the UNIQUE index is
                # case-sensitive). Both iterations match the SAME vision_segments
                # row by LOWER(name), so the first one silently won. This runs at
                # every manager init, moments after the migration reported that
                # exact row as ambiguous and left it NULL — so the report was
                # false about the database it had just described.
                certain = resolve_segment_id_exact(self.db.conn, name)
                if certain is not None:
                    self.db.conn.execute(
                        "UPDATE vision_segments SET segment_description_id = ? "
                        "WHERE id = ?",
                        (certain, existing["id"]),
                    )
        self.db.conn.commit()

    def default_subsegment_color_for_segment(self, segment_name: str) -> str:
        segment_color = self.resolve_segment_color(segment_name, self.get_segment_color_map())
        return self._derive_subsegment_color(segment_color)

    def create_vision_subsegment(self, segment_name: str, subsegment_name: str, color_hex: Optional[str] = None) -> str:
        """Create a subsegment under an existing Settings segment."""
        seg_id = self._create_or_get_vision_segment(segment_name)
        return self._create_or_get_vision_subsegment(seg_id, subsegment_name, color_hex=color_hex)

    def create_vision_category(
        self,
        segment_name: str,
        subsegment_name: str,
        category_name: str,
        color_hex: Optional[str] = None,
        description: str = "",
        vision_text: str = "",
    ) -> str:
        seg_id = self._create_or_get_vision_segment(segment_name)
        sub_id = self._resolve_vision_subsegment_id(seg_id, subsegment_name)
        if not sub_id:
            raise ValueError(f"SubSegment '{subsegment_name}' does not exist under '{segment_name}'.")
        return self._create_or_get_vision_category(
            sub_id,
            category_name,
            color_hex=color_hex,
            description=description,
            vision_text=vision_text,
        )

    def get_vision_segments_admin(self) -> List[Dict[str, Any]]:
        self.sync_vision_segments_with_settings()
        cursor = self.db.conn.execute(
            """
            SELECT
                vs.id,
                vs.name,
                vs.vision_text,
                COALESCE(sd.description, '') AS description,
                COALESCE(sd.color_hex, '#334155') AS color_hex,
                COALESCE(sd.is_active, 1) AS is_active,
                sd.id AS settings_segment_id
            FROM vision_segments vs
            -- RN-M2.C: by id, not by name. rename_vision_segment updates
            -- vision_segments only, so a name join found nothing after a
            -- rename and the segment lost its colour and order.
            LEFT JOIN segment_descriptions sd ON sd.id = vs.segment_description_id
            ORDER BY vs.name COLLATE NOCASE ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]

    def create_vision_segment_admin(
        self,
        name: str,
        description: str,
        color_hex: str,
        vision_text: str,
        is_active: bool = True,
    ) -> str:
        segments = self.get_all_segments(active_only=False)
        next_order = (max((s.get("order_index") or 0 for s in segments), default=0) + 1)
        seg_settings_id = self.create_segment(
            name=name.strip(),
            description=(description or "").strip(),
            color_hex=color_hex.strip().upper(),
            order_index=next_order,
        )
        if not is_active:
            self.update_segment(seg_settings_id, is_active=False)
        vision_seg = self.db.conn.execute(
            "SELECT id FROM vision_segments WHERE LOWER(name) = LOWER(?)",
            (name.strip(),),
        ).fetchone()
        if vision_seg:
            self.update_segment_vision_text(vision_seg["id"], vision_text)
            return vision_seg["id"]
        raise ValueError("Failed to create vision segment.")

    def update_vision_segment_admin(
        self,
        segment_id: str,
        name: str,
        description: str,
        color_hex: str,
        vision_text: str,
        is_active: bool = True,
    ) -> bool:
        row = self.db.conn.execute(
            """
            SELECT sd.id AS settings_id
            FROM vision_segments vs
            -- RN-M2.C: by id, not by name. rename_vision_segment updates
            -- vision_segments only, so a name join found nothing after a
            -- rename and the segment lost its colour and order.
            LEFT JOIN segment_descriptions sd ON sd.id = vs.segment_description_id
            WHERE vs.id = ?
            """,
            (segment_id,),
        ).fetchone()
        if not row:
            return False
        settings_id = row["settings_id"]
        if settings_id:
            self.update_segment(
                settings_id,
                name=name.strip(),
                description=(description or "").strip(),
                color_hex=color_hex.strip().upper(),
                is_active=1 if is_active else 0,
            )
        else:
            self._create_or_get_vision_segment(name.strip())
        seg_row = self.db.conn.execute("SELECT id FROM vision_segments WHERE LOWER(name) = LOWER(?)", (name.strip(),)).fetchone()
        if not seg_row:
            return False
        self.update_segment_vision_text(seg_row["id"], vision_text)
        return True

    def delete_vision_segment_admin(self, segment_id: str) -> bool:
        row = self.db.conn.execute(
            """
            SELECT vs.id, vs.name, sd.id AS settings_id
            FROM vision_segments vs
            -- RN-M2.C: by id, not by name. rename_vision_segment updates
            -- vision_segments only, so a name join found nothing after a
            -- rename and the segment lost its colour and order.
            LEFT JOIN segment_descriptions sd ON sd.id = vs.segment_description_id
            WHERE vs.id = ?
            """,
            (segment_id,),
        ).fetchone()
        if not row:
            return False
        settings_id = row["settings_id"]
        if not settings_id:
            # RN-M2.C moved this join from a name match to the id, so a row
            # whose id is NULL — an unmatched or ambiguous row the migration
            # deliberately left that way — now falls through here. Before the
            # change the name join found the description and the protection
            # ran; after it, the raw DELETE below skipped delete_segment
            # entirely and raised FOREIGN KEY constraint failed.
            #
            # Fall back to the name so the protection still runs. Exact only:
            # guessing between two descriptions is what RN-INV5 forbids.
            settings_id = resolve_segment_id_exact(self.db.conn, row["name"])

        if settings_id:
            success, _counts = self.delete_segment(settings_id)
            return bool(success)

        # Ambiguous is NOT "genuinely unlinked". Falling through here raised an
        # uncaught FOREIGN KEY constraint failed with dependents present — and
        # had the FK not blocked it, vision_elements.segment_id is
        # ON DELETE CASCADE, so this line would have deleted the whole vision
        # element tree with none of delete_segment's protection.
        candidates = self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM segment_descriptions WHERE LOWER(name) = LOWER(?)",
            (row["name"],),
        ).fetchone()["n"]
        if candidates > 1:
            raise ValueError(
                f"'{row['name']}' matches {candidates} life segments, so which "
                "one this belongs to is ambiguous. Rename one of them first."
            )

        # Genuinely unlinked and unresolvable: the shadow row alone.
        cur = self.db.conn.execute("DELETE FROM vision_segments WHERE id = ?", (segment_id,))
        self.db.conn.commit()
        return cur.rowcount > 0

    def update_vision_subsegment(
        self,
        subsegment_id: str,
        name: str,
        color_hex: str,
        description: str,
        vision_text: str,
    ) -> bool:
        new_name = (name or "").strip()
        if not new_name:
            raise ValueError("SubSegment name is required.")
        # SCV-M1.1/M3.1: validate and normalise in one call, and store what it
        # returns rather than the text as typed.
        stored_color = normalize_hex_color(color_hex) if color_hex else None
        if color_hex and stored_color is None:
            raise ValueError("Invalid color. Use #RRGGBB.")

        row = self.db.conn.execute(
            "SELECT id, segment_id, name FROM vision_subsegments WHERE id = ?",
            (subsegment_id,),
        ).fetchone()
        if not row:
            return False
        if new_name.lower() != (row["name"] or "").strip().lower():
            self.rename_vision_subsegment(subsegment_id, new_name)
        cur = self.db.conn.execute(
            "UPDATE vision_subsegments SET color_hex = ?, description = ?, vision_text = ?, updated_at = ? WHERE id = ?",
            (stored_color, (description or "").strip(), (vision_text or "").strip(), datetime.now().isoformat(), subsegment_id),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

    def update_vision_category(
        self,
        category_id: str,
        name: str,
        color_hex: str,
        description: str,
        vision_text: str,
    ) -> bool:
        new_name = (name or "").strip()
        if not new_name:
            raise ValueError("Category name is required.")
        # SCV-M1.1/M3.1, as in ``update_vision_subsegment``.
        stored_color = normalize_hex_color(color_hex) if color_hex else None
        if color_hex and stored_color is None:
            raise ValueError("Invalid color. Use #RRGGBB.")
        row = self.db.conn.execute(
            "SELECT id, name FROM vision_categories WHERE id = ?",
            (category_id,),
        ).fetchone()
        if not row:
            return False
        if new_name.lower() != (row["name"] or "").strip().lower():
            self.rename_vision_category(category_id, new_name)
        cur = self.db.conn.execute(
            "UPDATE vision_categories SET color_hex = ?, description = ?, vision_text = ?, updated_at = ? WHERE id = ?",
            (stored_color, (description or "").strip(), (vision_text or "").strip(), datetime.now().isoformat(), category_id),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

    def delete_vision_subsegment(self, subsegment_id: str) -> bool:
        cur = self.db.conn.execute("DELETE FROM vision_subsegments WHERE id = ?", (subsegment_id,))
        self.db.conn.commit()
        return cur.rowcount > 0

    def delete_vision_category(self, category_id: str) -> bool:
        cur = self.db.conn.execute("DELETE FROM vision_categories WHERE id = ?", (category_id,))
        self.db.conn.commit()
        return cur.rowcount > 0

    def update_subsegment_vision_text(self, subsegment_id: str, vision_text: str) -> bool:
        cur = self.db.conn.execute(
            "UPDATE vision_subsegments SET vision_text = ?, updated_at = ? WHERE id = ?",
            ((vision_text or "").strip(), datetime.now().isoformat(), subsegment_id),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

    def update_category_vision_text(self, category_id: str, vision_text: str) -> bool:
        cur = self.db.conn.execute(
            "UPDATE vision_categories SET vision_text = ?, updated_at = ? WHERE id = ?",
            ((vision_text or "").strip(), datetime.now().isoformat(), category_id),
        )
        self.db.conn.commit()
        return cur.rowcount > 0

