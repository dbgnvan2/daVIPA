"""APE quarter assignment screen with two-panel APE workflow."""

from datetime import date, datetime
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from ..color_contrast import pick_text_color
from ..date_utils import current_quarter
from ..theme import button_style, semantic_colors, status_text_color
from ..weekly_tactic_logging import get_weekly_tactic_logger
from .segment_color_utils import load_latest_lineage_color_maps, resolve_lineage_colors

if TYPE_CHECKING:
    from ..app import GetMoreDoneApp
    from ..vps_manager import VPSManager


logger = get_weekly_tactic_logger()


class APEAssignmentScreen(ctk.CTkFrame):
    """Assign Annual Plan Elements to a selected quarter."""
    SPLITTER_WIDTH = 8
    MIN_PANEL_WIDTH = 420

    def __init__(self, parent, vps_manager: "VPSManager", app: "GetMoreDoneApp"):
        super().__init__(parent)
        self.vps_manager = vps_manager
        self.app = app

        # APC-M6 — the same hard-coded Q1 the Month screen had. Two APE
        # screens that disagree about which quarter you are in is how an APE
        # ends up filed in one quarter and worked in another.
        self.year_var = ctk.StringVar(value=str(datetime.now().year))
        self.quarter_var = ctk.StringVar(value=str(current_quarter(date.today())))
        self.segment_filter_var = ctk.StringVar(value="All")
        self.subsegment_filter_var = ctk.StringVar(value="All")
        self.category_filter_var = ctk.StringVar(value="All")

        self.left_items: list[dict] = []
        self.right_items: list[dict] = []
        self.segment_colors = {}
        self.subsegment_colors = {}
        self.category_colors = {}
        self.left_checks: dict[str, ctk.BooleanVar] = {}
        self._split_ratio = 0.5
        self._drag_start_x: Optional[int] = None
        self._drag_start_left: Optional[int] = None
        self.dragged_row: Optional[dict] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_ui()
        self.refresh_lists()

    def create_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(12, weight=1)

        ctk.CTkLabel(
            header,
            text="APE Quarter Assignment",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=13, sticky="w", padx=8, pady=(8, 6))

        ctk.CTkLabel(header, text="Year:").grid(row=1, column=0, padx=(8, 4), pady=(0, 8), sticky="e")
        ctk.CTkEntry(header, width=86, textvariable=self.year_var).grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")
        ctk.CTkLabel(header, text="Quarter:").grid(row=1, column=2, padx=(8, 4), pady=(0, 8), sticky="e")
        ctk.CTkComboBox(header, width=74, values=["1", "2", "3", "4"], variable=self.quarter_var).grid(
            row=1, column=3, padx=4, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Load", width=88, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=4, padx=(8, 4), pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Save", width=88, command=self.add_selected, **button_style("primary")).grid(
            row=1, column=5, padx=4, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Refresh", width=88, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=6, padx=(4, 12), pady=(0, 8), sticky="w"
        )

        ctk.CTkLabel(header, text="Segment:").grid(row=1, column=7, padx=(0, 4), pady=(0, 8), sticky="e")
        self.segment_filter_combo = ctk.CTkComboBox(
            header, width=160, values=["All"], variable=self.segment_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.segment_filter_combo.grid(row=1, column=8, padx=4, pady=(0, 8), sticky="w")

        ctk.CTkLabel(header, text="SubSegment:").grid(row=1, column=9, padx=(10, 4), pady=(0, 8), sticky="e")
        self.subsegment_filter_combo = ctk.CTkComboBox(
            header, width=160, values=["All"], variable=self.subsegment_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.subsegment_filter_combo.grid(row=1, column=10, padx=4, pady=(0, 8), sticky="w")

        ctk.CTkLabel(header, text="Category:").grid(row=1, column=11, padx=(10, 4), pady=(0, 8), sticky="e")
        self.category_filter_combo = ctk.CTkComboBox(
            header, width=160, values=["All"], variable=self.category_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.category_filter_combo.grid(row=1, column=12, padx=4, pady=(0, 8), sticky="w")

        # APC-M6.2 — somewhere for Save to say what it did, as APE Month has.
        # Before this the quarter screen reported neither a success nor a
        # refusal on either of its two write paths.
        self.status_label = ctk.CTkLabel(header, text="", text_color=status_text_color("muted"))
        self.status_label.grid(row=2, column=0, columnspan=13, sticky="w", padx=8, pady=(0, 8))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=0, minsize=520)
        body.grid_columnconfigure(1, weight=0, minsize=self.SPLITTER_WIDTH)
        body.grid_columnconfigure(2, weight=0, minsize=520)
        body.grid_rowconfigure(1, weight=1)
        self.body = body

        self.left_title_label = ctk.CTkLabel(body, text="", font=ctk.CTkFont(weight="bold"))
        self.left_title_label.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        self.right_title_label = ctk.CTkLabel(body, text="", font=ctk.CTkFont(weight="bold"))
        self.right_title_label.grid(row=0, column=2, sticky="w", padx=8, pady=(8, 4))

        left_frame = ctk.CTkFrame(body)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 2), pady=(0, 8))
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame = left_frame

        divider = ctk.CTkFrame(
            body,
            width=self.SPLITTER_WIDTH,
            fg_color=semantic_colors()["border"],
            corner_radius=2,
            cursor="sb_h_double_arrow",
        )
        divider.grid(row=1, column=1, sticky="ns", padx=0, pady=(0, 8))
        divider.bind("<ButtonPress-1>", self._on_divider_press)
        divider.bind("<B1-Motion>", self._on_divider_drag)
        divider.bind("<ButtonRelease-1>", self._on_divider_release)
        self.divider = divider

        right_frame = ctk.CTkFrame(body)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(2, 8), pady=(0, 8))
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame = right_frame

        self.left_list = ctk.CTkScrollableFrame(left_frame)
        self.left_list.grid(row=0, column=0, sticky="nsew")
        self.left_list.grid_columnconfigure(0, weight=1)

        self.right_list = ctk.CTkScrollableFrame(right_frame)
        self.right_list.grid(row=0, column=0, sticky="nsew")
        self.right_list.grid_columnconfigure(0, weight=1)
        body.bind("<Configure>", self._on_body_resize)

    def _parse_period(self) -> Optional[tuple[int, int]]:
        try:
            year = int(self.year_var.get().strip())
            quarter = int(self.quarter_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Period", "Enter a valid year and quarter.")
            return None
        if quarter not in (1, 2, 3, 4):
            messagebox.showerror("Invalid Quarter", "Quarter must be 1, 2, 3, or 4.")
            return None
        return year, quarter

    def refresh_lists(self):
        parsed = self._parse_period()
        if not parsed:
            return
        year, quarter = parsed

        self.segment_colors, self.subsegment_colors = load_latest_lineage_color_maps(self.vps_manager)
        self.category_colors = {
            (
                (r.get("segment_name", "") or "").strip().lower(),
                (r.get("subsegment_name", "") or "").strip().lower(),
                (r.get("name", "") or "").strip().lower(),
            ): (r.get("color_hex") or "")
            for r in self.vps_manager.get_vision_categories()
        }
        self.left_items = self.vps_manager.get_annual_plan_elements(year)
        self.right_items = self.vps_manager.get_annual_plan_elements_for_quarter(year, quarter)
        self._refresh_filter_options()
        self.left_title_label.configure(text=f"Annual Plan Elements (check APEs to add to Quarter Q{quarter} and hit save)")
        self.right_title_label.configure(text=f"APE For Quarter Q{quarter}")
        self._render_rows(self.left_list, self._filtered_rows(self.left_items), selectable=True)
        self._render_rows(self.right_list, self._filtered_rows(self.right_items), selectable=False)

    def _filtered_rows(self, rows: list[dict]) -> list[dict]:
        seg = self.segment_filter_var.get().strip()
        sub = self.subsegment_filter_var.get().strip()
        cat = self.category_filter_var.get().strip()
        filtered = rows
        if seg and seg != "All":
            filtered = [r for r in filtered if (r.get("segment_name") or "").strip() == seg]
        if sub and sub != "All":
            filtered = [r for r in filtered if (r.get("subsegment_name") or "").strip() == sub]
        if cat and cat != "All":
            filtered = [r for r in filtered if (r.get("category_name") or "").strip() == cat]
        return filtered

    def _refresh_filter_options(self):
        rows = self.left_items
        seg_values = sorted({(r.get("segment_name") or "").strip() for r in rows if (r.get("segment_name") or "").strip()}, key=str.lower)
        seg_combo_values = ["All"] + seg_values
        current_seg = self.segment_filter_var.get().strip() or "All"
        if current_seg not in seg_combo_values:
            current_seg = "All"
            self.segment_filter_var.set(current_seg)
        self.segment_filter_combo.configure(values=seg_combo_values)

        sub_rows = rows if current_seg == "All" else [r for r in rows if (r.get("segment_name") or "").strip() == current_seg]
        sub_values = sorted({(r.get("subsegment_name") or "").strip() for r in sub_rows if (r.get("subsegment_name") or "").strip()}, key=str.lower)
        sub_combo_values = ["All"] + sub_values
        current_sub = self.subsegment_filter_var.get().strip() or "All"
        if current_sub not in sub_combo_values:
            current_sub = "All"
            self.subsegment_filter_var.set(current_sub)
        self.subsegment_filter_combo.configure(values=sub_combo_values)

        cat_rows = sub_rows if current_sub == "All" else [r for r in sub_rows if (r.get("subsegment_name") or "").strip() == current_sub]
        cat_values = sorted({(r.get("category_name") or "").strip() for r in cat_rows if (r.get("category_name") or "").strip()}, key=str.lower)
        cat_combo_values = ["All"] + cat_values
        current_cat = self.category_filter_var.get().strip() or "All"
        if current_cat not in cat_combo_values:
            current_cat = "All"
            self.category_filter_var.set(current_cat)
        self.category_filter_combo.configure(values=cat_combo_values)

    def on_filters_changed(self):
        self._refresh_filter_options()
        self._render_rows(self.left_list, self._filtered_rows(self.left_items), selectable=True)
        self._render_rows(self.right_list, self._filtered_rows(self.right_items), selectable=False)

    def add_selected(self):
        """Assign every checked APE to the selected quarter.

        Purpose: APC-M6.2 — the quarter screen says what Save did, as the month
                 screen does, on both of its write paths.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m6
        Tests:   tests/test_ape_period_consistency.py::test_apcm62_quarter_save_reports_refused_assignments
                 tests/test_ape_period_consistency.py::test_apcm62_quarter_save_with_nothing_checked_says_so

        APC-M6.2. ``assign_ape_to_quarter`` returns a bare boolean and can
        raise ``ValueError`` when an APE's segment resolves to nothing, and
        this screen discarded both: a rejected APE simply did not appear in the
        right-hand panel, which is what a click on the wrong row looks like.
        The month screen was hardened on exactly this axis in the same change
        and this one was left silent — the "fixed as a class" shape P5
        describes, where the denominator was two paths on one screen and is
        really four across two.
        """
        parsed = self._parse_period()
        if not parsed:
            return
        _year, quarter = parsed
        selected_ids = [row_id for row_id, var in self.left_checks.items() if var.get()]
        if not selected_ids:
            self.status_label.configure(text="Check one or more APEs on the left first.")
            return
        claimed = {
            ape_id for ape_id in selected_ids if self._assign_one(ape_id, quarter)
        }
        self.refresh_lists()
        self.status_label.configure(
            text=self._describe_quarter_assignment(
                selected_ids, claimed, self._ids_in_quarter(), quarter
            )
        )

    def _ids_in_quarter(self) -> set:
        """Which APEs the quarter really holds, as the right-hand panel has it.

        Purpose: APC-M6.3 — give the status line the artifact to reconcile
                 against, and make it the same read the panel is drawn from.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m6
        Tests:   tests/test_ape_period_consistency.py::test_apcm63_a_half_written_quarter_assignment_is_reported_as_partial

        ``refresh_lists`` has just set ``self.right_items`` from
        ``get_annual_plan_elements_for_quarter``, unfiltered.
        """
        return {row["id"] for row in getattr(self, "right_items", [])}

    def _assign_one(self, ape_id: str, quarter: int) -> bool:
        """One APE's quarter assignment: ``True`` only if the call said so.

        Not "only if the row was written" — that was this docstring's first
        claim and it is wrong in the direction that reaches the user. The
        manager writes before it can fail, so ``False`` here does **not** mean
        nothing was written. The caller reconciles against the row; this only
        reports what the call claimed.

        Purpose: APC-M6.2 — turn a refusal and a raise into the same answer, so
                 both write paths on this screen count them the same way.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m6
        Tests:   tests/test_ape_period_consistency.py::test_apcm62_a_raising_quarter_assignment_is_counted_not_escaped
        """
        try:
            if self.vps_manager.assign_ape_to_quarter(ape_id, quarter):
                return True
            logger.warning(
                "[ape_assignment] APE %s was not assigned to Q%d.", ape_id, quarter
            )
        except Exception:
            logger.exception(
                "[ape_assignment] APE %s raised while being assigned to Q%d.",
                ape_id, quarter,
            )
        return False

    @staticmethod
    def _describe_quarter_assignment(selected, claimed, in_quarter, quarter: int) -> str:
        """APC-M6.3 — the sentence is computed from the rows, not from a return code.

        Purpose: never let a refused assignment look like a successful one, and
                 never let a half-written one look like either.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m6
        Tests:   tests/test_ape_period_consistency.py::test_apcm62_quarter_save_reports_refused_assignments
                 tests/test_ape_period_consistency.py::test_apcm63_a_half_written_quarter_assignment_is_reported_as_partial

        ``assign_ape_to_quarter`` commits the quarter flag through
        ``set_annual_plan_element_quarter`` and only then raises on a segment
        it cannot resolve, so a ``False`` from it does not mean nothing was
        written. Counting the booleans put "Assigned 0 APE(s) to Q4." beside a
        panel that was showing the row.

        The month screen's ``_describe_month_assignment`` with Q for M, and the
        same four states, for the same reason — see its docstring.
        """
        assigned = [a for a in selected if a in claimed and a in in_quarter]
        partial = [a for a in selected if a not in claimed and a in in_quarter]
        refused = [a for a in selected if a not in claimed and a not in in_quarter]
        missing = [a for a in selected if a in claimed and a not in in_quarter]

        text = f"Assigned {len(assigned)} APE(s) to Q{quarter}."
        if partial:
            text += (
                f" {len(partial)} partly assigned — in Q{quarter} with no "
                f"quarter initiative behind it; see the log."
            )
        if refused:
            text += f" {len(refused)} could not be assigned — see the log."
        if missing:
            text += (
                f" {len(missing)} reported assigned but are not in Q{quarter} — "
                f"see the log."
            )
        return text

    def _render_rows(self, container: ctk.CTkScrollableFrame, rows: list[dict], selectable: bool):
        for w in container.winfo_children():
            w.destroy()

        col_widths = {
            "index": 34,
            "segment": 135,
            "subsegment": 155,
            "category": 125,
            "actions": 84,
            "checkbox": 34,
        }

        header = ctk.CTkFrame(container, fg_color=semantic_colors()["surface_subtle"])
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 4))
        if selectable:
            header.grid_columnconfigure(0, minsize=col_widths["checkbox"])
            offset = 1
            ctk.CTkLabel(header, text="", width=col_widths["checkbox"]).grid(row=0, column=0, padx=2, pady=5, sticky="w")
        else:
            offset = 0
        header.grid_columnconfigure(offset + 0, minsize=col_widths["index"])
        header.grid_columnconfigure(offset + 1, minsize=col_widths["segment"])
        header.grid_columnconfigure(offset + 2, minsize=col_widths["subsegment"])
        header.grid_columnconfigure(offset + 3, minsize=col_widths["category"])
        header.grid_columnconfigure(offset + 4, weight=1 if selectable else 0, minsize=0 if selectable else col_widths["actions"])

        for idx, label in enumerate(("#", "Segment", "SubSegment", "Category")):
            width = col_widths[("index", "segment", "subsegment", "category")[idx]]
            ctk.CTkLabel(header, text=label, width=width, font=ctk.CTkFont(weight="bold"), anchor="w").grid(
                row=0, column=offset + idx, padx=5, pady=5, sticky="w"
            )
        if not selectable:
            ctk.CTkLabel(header, text="Actions", width=col_widths["actions"], font=ctk.CTkFont(weight="bold"), anchor="e").grid(
                row=0, column=offset + 4, padx=5, pady=5, sticky="e"
            )

        for idx, row in enumerate(rows):
            segment_name = row.get("segment_name") or ""
            subsegment_raw = row.get("subsegment_name") or "-"
            category_raw = row.get("category_name") or "-"
            segment_color, subsegment_color = resolve_lineage_colors(
                segment_name,
                subsegment_raw,
                self.vps_manager,
                self.segment_colors,
                self.subsegment_colors,
            )
            category_color = self.category_colors.get(
                (segment_name.strip().lower(), subsegment_raw.strip().lower(), category_raw.strip().lower()),
                "",
            ) or subsegment_color

            item = ctk.CTkFrame(container)
            item.grid(row=idx + 1, column=0, sticky="ew", padx=4, pady=2)
            if selectable:
                item.grid_columnconfigure(0, minsize=col_widths["checkbox"])
                offset = 1
            else:
                offset = 0
            item.grid_columnconfigure(offset + 0, minsize=col_widths["index"])
            item.grid_columnconfigure(offset + 1, minsize=col_widths["segment"])
            item.grid_columnconfigure(offset + 2, minsize=col_widths["subsegment"])
            item.grid_columnconfigure(offset + 3, minsize=col_widths["category"])
            item.grid_columnconfigure(offset + 4, weight=1 if selectable else 0, minsize=0 if selectable else col_widths["actions"])

            if selectable:
                item_id = row.get("id", f"row-{idx}")
                var = self.left_checks.get(item_id)
                if var is None:
                    var = ctk.BooleanVar(value=False)
                    self.left_checks[item_id] = var
                ctk.CTkCheckBox(item, text="", variable=var, width=20).grid(row=0, column=0, padx=2, pady=5, sticky="w")

            index_label = ctk.CTkLabel(item, text=str(idx + 1), width=col_widths["index"], anchor="w")
            index_label.grid(
                row=0, column=offset + 0, padx=5, pady=5, sticky="w"
            )
            seg_chip = ctk.CTkLabel(
                item,
                text=f" {self._clip_label(segment_name, 15)} ",
                fg_color=segment_color,
                text_color=pick_text_color(segment_color),
                corner_radius=6,
                width=col_widths["segment"] - 12,
                anchor="w",
            )
            seg_chip.grid(row=0, column=offset + 1, padx=5, pady=5, sticky="w")
            sub_chip = ctk.CTkLabel(
                item,
                text=f" {self._clip_label(subsegment_raw, 15)} ",
                fg_color=subsegment_color,
                text_color=pick_text_color(subsegment_color),
                corner_radius=6,
                width=col_widths["subsegment"] - 12,
                anchor="w",
            )
            sub_chip.grid(row=0, column=offset + 2, padx=5, pady=5, sticky="w")
            cat_chip = ctk.CTkLabel(
                item,
                text=f" {self._clip_label(category_raw, 15)} ",
                fg_color=category_color,
                text_color=pick_text_color(category_color),
                corner_radius=6,
                width=col_widths["category"] - 12,
                anchor="w",
            )
            cat_chip.grid(row=0, column=offset + 3, padx=5, pady=5, sticky="w")

            if not selectable:
                ctk.CTkButton(
                    item,
                    text="Delete",
                    width=72,
                    command=lambda r=row: self.delete_quarter_item(r),
                    **button_style("danger"),
                ).grid(row=0, column=offset + 4, padx=5, pady=5, sticky="e")
            else:
                self._bind_drag_widgets((item, index_label, seg_chip, sub_chip, cat_chip), row)

    def delete_quarter_item(self, row: dict):
        parsed = self._parse_period()
        if not parsed:
            return
        _year, quarter = parsed
        label = row.get("key_field") or "this APE"
        if not messagebox.askyesno("Remove APE", f"Remove {label} from Quarter Q{quarter}?", icon="warning"):
            return
        ok = self._remove_one(row["id"], quarter)
        self.refresh_lists()
        still_there = row["id"] in self._ids_in_quarter()
        if ok and not still_there:
            self.status_label.configure(text=f"Removed {label} from Q{quarter}.")
        elif still_there:
            self.status_label.configure(
                text=f"{label} is still in Q{quarter} — see the log."
            )
        else:
            self.status_label.configure(
                text=f"{label} is out of Q{quarter}, but the remove reported a "
                     f"problem — see the log."
            )

    def _remove_one(self, ape_id: str, quarter: int) -> bool:
        """One APE's quarter removal: ``True`` only if the call reported success.

        Purpose: APC-M6.4 — the remove path reports too. It is the same class as
                 the two assign paths, on the same screen.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m6
        Tests:   tests/test_ape_period_consistency.py::test_apcm64_a_failed_quarter_remove_is_reported

        ``unassign_ape_from_quarter`` returns ``False`` for an APE row that no
        longer exists, and this ran straight after a ``messagebox.askyesno``
        that promised removal: a dialog that said it would remove the row, and
        a panel that still shows it, with nothing in between.
        """
        try:
            if self.vps_manager.unassign_ape_from_quarter(ape_id, quarter):
                return True
            logger.warning(
                "[ape_assignment] APE %s was not removed from Q%d.", ape_id, quarter
            )
        except Exception:
            logger.exception(
                "[ape_assignment] APE %s raised while being removed from Q%d.",
                ape_id, quarter,
            )
        return False

    def _bind_drag_widgets(self, widgets: tuple, row: dict):
        for widget in widgets:
            widget.bind("<ButtonPress-1>", lambda _event, r=row: self._start_row_drag(r))

    def _start_row_drag(self, row: dict):
        self.dragged_row = row
        self.winfo_toplevel().bind("<ButtonRelease-1>", self._finish_row_drag)

    def _finish_row_drag(self, _event):
        self.winfo_toplevel().unbind("<ButtonRelease-1>")
        if not self.dragged_row:
            return
        pointer_x, pointer_y = self.winfo_pointerxy()
        target = self.winfo_containing(pointer_x, pointer_y)
        row = self.dragged_row
        self.dragged_row = None
        if self._is_descendant(target, self.right_list):
            parsed = self._parse_period()
            if parsed:
                _year, quarter = parsed
                ok = self._assign_one(row["id"], quarter)
                self.refresh_lists()
                self.status_label.configure(
                    text=self._describe_quarter_assignment(
                        [row["id"]],
                        {row["id"]} if ok else set(),
                        self._ids_in_quarter(),
                        quarter,
                    )
                )

    def _on_body_resize(self, _event):
        if self._drag_start_x is None:
            self._apply_split_ratio()

    def _on_divider_press(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_left = self.left_frame.winfo_width()

    def _on_divider_drag(self, event):
        if self._drag_start_x is None or self._drag_start_left is None:
            return
        total = self.body.winfo_width() - self.SPLITTER_WIDTH
        if total <= 0:
            return
        left = self._drag_start_left + (event.x_root - self._drag_start_x)
        max_left = max(self.MIN_PANEL_WIDTH, total - self.MIN_PANEL_WIDTH)
        left = max(self.MIN_PANEL_WIDTH, min(max_left, left))
        self._split_ratio = left / total
        self._apply_split_ratio()

    def _on_divider_release(self, _event):
        self._drag_start_x = None
        self._drag_start_left = None

    def _apply_split_ratio(self):
        total = self.body.winfo_width() - self.SPLITTER_WIDTH
        if total <= 0:
            return
        max_left = max(self.MIN_PANEL_WIDTH, total - self.MIN_PANEL_WIDTH)
        left = int(total * self._split_ratio)
        left = max(self.MIN_PANEL_WIDTH, min(max_left, left))
        right = total - left
        self.body.grid_columnconfigure(0, minsize=left)
        self.body.grid_columnconfigure(2, minsize=right)

    def _is_descendant(self, widget, ancestor) -> bool:
        current = widget
        while current is not None:
            if current == ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    @staticmethod
    def _clip_label(value: str, limit: int) -> str:
        text = (value or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit - 1].rstrip() + "…"
