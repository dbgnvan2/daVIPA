"""APE quarter assignment screen with two-panel APE workflow."""

from datetime import date, datetime
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from ..app_settings import AppSettings
from ..date_utils import current_quarter
from ..theme import button_style, semantic_colors, status_text_color
from ..weekly_tactic_logging import get_weekly_tactic_logger
from .chip_table import APE_LEFT_COLUMNS, APE_RIGHT_COLUMNS, ChipTable, panel_fitter
from .row_drag import RowDragSource
from .segment_color_utils import load_latest_lineage_color_maps, resolve_lineage_colors
from .split_panel import SPLITTER_WIDTH, SplitPanel

if TYPE_CHECKING:
    from ..app import GetMoreDoneApp
    from ..vps_manager import VPSManager


logger = get_weekly_tactic_logger()


class APEAssignmentScreen(ctk.CTkFrame):
    """Assign Annual Plan Elements to a selected quarter."""

    # UPD-D3/D4 — this screen's own corner of AppSettings. The divider's
    # ratio is stored under ``<SETTINGS_PREFIX>_split_ratio``.
    SETTINGS_PREFIX = "ape_quarter"

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
        # The app's own instance where there is one, so a saved divider does
        # not overwrite a setting changed elsewhere since this screen was
        # built; its own load when constructed without an app (tests).
        self.settings = getattr(app, "settings", None) or AppSettings.load()

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

        # UPD-F2 — the three filters sit on a row of their own, below the
        # row holding this tab's own controls, so every tab in the hub is the
        # same depth. They were on the controls row, which put eleven widgets
        # on one line and made the filters hard to find. A frame rather than
        # six more cells in the header's grid: the two rows then size their
        # columns independently, so a 160px combo does not stretch the column
        # the Year entry sits in.
        # Spec:  docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
        # Tests: tests/test_unified_panel_design.py::test_updf21_the_filters_are_on_their_own_row
        self.filter_row = ctk.CTkFrame(header, fg_color="transparent")
        self.filter_row.grid(row=2, column=0, columnspan=13, sticky="w",
                             padx=8, pady=(0, 8))

        ctk.CTkLabel(self.filter_row, text="Segment:").grid(row=0, column=0, padx=(0, 4), sticky="e")
        self.segment_filter_combo = ctk.CTkComboBox(
            self.filter_row, width=160, values=["All"], variable=self.segment_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.segment_filter_combo.grid(row=0, column=1, padx=4, sticky="w")

        ctk.CTkLabel(self.filter_row, text="SubSegment:").grid(row=0, column=2, padx=(10, 4), sticky="e")
        self.subsegment_filter_combo = ctk.CTkComboBox(
            self.filter_row, width=160, values=["All"], variable=self.subsegment_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.subsegment_filter_combo.grid(row=0, column=3, padx=4, sticky="w")

        ctk.CTkLabel(self.filter_row, text="Category:").grid(row=0, column=4, padx=(10, 4), sticky="e")
        self.category_filter_combo = ctk.CTkComboBox(
            self.filter_row, width=160, values=["All"], variable=self.category_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.category_filter_combo.grid(row=0, column=5, padx=4, sticky="w")

        # APC-M6.2 — somewhere for Save to say what it did, as APE Month has.
        # Before this the quarter screen reported neither a success nor a
        # refusal on either of its two write paths.
        self.status_label = ctk.CTkLabel(header, text="", text_color=status_text_color("muted"))
        self.status_label.grid(row=3, column=0, columnspan=13, sticky="w", padx=8, pady=(0, 8))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=0, minsize=520)
        body.grid_columnconfigure(1, weight=0, minsize=SPLITTER_WIDTH)
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
            width=SPLITTER_WIDTH,
            fg_color=semantic_colors()["border"],
            corner_radius=2,
            cursor="sb_h_double_arrow",
        )
        divider.grid(row=1, column=1, sticky="ns", padx=0, pady=(0, 8))
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

        # UPD-M4 — the header, the chips and the column widths come from
        # screens/chip_table.py, one table per panel. The prefixes are this
        # screen's corner of AppSettings; the two panels are different shapes
        # and must not share a width store (UPD-M3.6).
        self.left_table = ChipTable(
            self.left_list, self.settings,
            f"{self.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS,
        )
        self.right_table = ChipTable(
            self.right_list, self.settings,
            f"{self.SETTINGS_PREFIX}_right", APE_RIGHT_COLUMNS,
        )

        # UPD-M1 — the ratio, the clamp, the three divider handlers and the
        # body's resize handler all live in screens/split_panel.py.
        self.split = SplitPanel(
            body,
            left_frame,
            divider,
            settings=self.settings,
            prefix=self.SETTINGS_PREFIX,
            # UPD-F4 — the divider hands each panel's new width to that
            # panel's columns, so moving it widens or narrows the columns
            # instead of leaving empty space beside the last one.
            on_apply=panel_fitter(self.left_table, self.right_table),
        )

        # UPD-M2 — the row drag, the drop test and the descendant walk live in
        # screens/row_drag.py. What a dropped row means is this screen's, and
        # stays here as _assign_dragged_row.
        self.row_drag = RowDragSource(
            self, self.right_list, self._assign_dragged_row
        )

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
        self._render_rows(self.left_table, self._filtered_rows(self.left_items), selectable=True)
        self._render_rows(self.right_table, self._filtered_rows(self.right_items), selectable=False)

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
        self._render_rows(self.left_table, self._filtered_rows(self.left_items), selectable=True)
        self._render_rows(self.right_table, self._filtered_rows(self.right_items), selectable=False)

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

    def _render_rows(self, table: ChipTable, rows: list[dict], selectable: bool):
        """Render one panel into the shared chip table.

        Purpose: UPD-M4 — the header, the row frames, the chips and the column
                 widths come from screens/chip_table.py. The checkbox and the
                 Actions cell stay here, because what they do is this screen's.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m4
        Tests:   tests/test_unified_panel_design.py::test_updm41_ape_quarter_left_header_columns_are_unchanged
        """
        table.build_header()

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

            item, cells = table.add_row(
                {
                    "index": str(idx + 1),
                    "segment": segment_name,
                    "subsegment": subsegment_raw,
                    "category": category_raw,
                },
                {
                    "segment": segment_color,
                    "subsegment": subsegment_color,
                    "category": category_color,
                },
            )

            if selectable:
                item_id = row.get("id", f"row-{idx}")
                var = self.left_checks.get(item_id)
                if var is None:
                    var = ctk.BooleanVar(value=False)
                    self.left_checks[item_id] = var
                ctk.CTkCheckBox(item, text="", variable=var, width=20).grid(
                    row=0, column=table.grid_col("checkbox"), padx=2, pady=5, sticky="w"
                )
                self.row_drag.bind_row(
                    (item, cells["index"], cells["segment"],
                     cells["subsegment"], cells["category"]),
                    row,
                )
            else:
                ctk.CTkButton(
                    item,
                    text="Delete",
                    width=72,
                    command=lambda r=row: self.delete_quarter_item(r),
                    **button_style("danger"),
                ).grid(row=0, column=table.grid_col("actions"), padx=5, pady=5, sticky="e")

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

    def _assign_dragged_row(self, row: dict):
        """Assign one APE to the selected quarter, dropped rather than checked.

        Purpose: what a drop onto the right panel means on this screen.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m2--one-row-drag-not-four
        Tests:   tests/test_unified_panel_design.py::test_updm22_drop_inside_the_target_assigns_once

        APC-M6.2 — the drop reports through the same status line as the Save
        button, so a refused assignment says so however it was made. Called by
        screens/row_drag.py only on a release inside the drop target; the
        screen no longer decides that for itself.
        """
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

