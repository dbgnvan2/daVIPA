"""Annual Plan Elements screen with drag/drop from Vision Elements."""

import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from ..app_settings import AppSettings
from ..theme import button_style, combo_box_style, semantic_colors, status_text_color
from ..vps_manager import ActionItemsAttachedError, ProjectBoardsAttachedError
from .chip_table import ANNUAL_RIGHT_COLUMNS, APE_LEFT_COLUMNS, ChipTable, panel_fitter
from .lineage_filters import FILTER_ROW_HEIGHT
from .row_drag import RowDragSource
from .segment_color_utils import load_latest_lineage_color_maps, resolve_lineage_colors
from .split_panel import SPLITTER_WIDTH, SplitPanel

if TYPE_CHECKING:
    from ..vps_manager import VPSManager
    from ..app import GetMoreDoneApp


class AnnualVisionSegmentsScreen(ctk.CTkFrame):
    """Drag vision elements into annual list to create annual plan records."""

    # UPD-D3/D4 — this screen's own corner of AppSettings. The divider's ratio
    # is stored under ``<SETTINGS_PREFIX>_split_ratio`` and each panel's column
    # widths under ``<SETTINGS_PREFIX>_<side>_col_widths``.
    SETTINGS_PREFIX = "annual_vision"

    def __init__(self, parent, vps_manager: "VPSManager", app: "GetMoreDoneApp"):
        super().__init__(parent)
        self.vps_manager = vps_manager
        self.app = app
        self.drag_index: Optional[int] = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.year_var = ctk.StringVar(value=str(datetime.now().year))
        self.left_items = []  # list of dict vision elements
        self.right_items = []
        self.segment_colors = {}
        self.subsegment_colors: dict[tuple[str, str], str] = {}
        self.category_colors: dict[tuple[str, str, str], str] = {}
        self.left_checks: dict[str, ctk.BooleanVar] = {}
        # The app's own instance where there is one, so a saved divider or
        # column width does not overwrite a setting changed elsewhere since
        # this screen was built; its own load when constructed without an app
        # (tests).
        self.settings = getattr(app, "settings", None) or AppSettings.load()

        self.create_ui()
        self.refresh_lists()

    def create_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(6, weight=1)

        # UPD-F2 — the title gets row 0 to itself and the controls drop to
        # row 1, which is where every other tab in the hub puts them. They
        # were on the title's row, so this tab was two lines shallower than
        # its neighbours and the body jumped when you moved between them.
        # Spec:  docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
        # Tests: tests/test_unified_panel_design.py::test_updf24_the_tab_with_no_filters_is_the_same_depth
        ctk.CTkLabel(header, text="Annual Plan Elements", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, columnspan=6, padx=8, pady=(8, 6), sticky="w"
        )
        ctk.CTkLabel(header, text="Year:").grid(row=1, column=0, padx=(8, 4), pady=(0, 8), sticky="e")
        self.year_entry = ctk.CTkEntry(header, width=90, textvariable=self.year_var)
        self.year_entry.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")
        ctk.CTkButton(header, text="Load Year", width=100, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=2, padx=6, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Save", width=100, command=self.add_selected, **button_style("primary")).grid(
            row=1, column=3, padx=6, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Refresh", width=90, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=4, padx=6, pady=(0, 8), sticky="w"
        )

        # This tab filters nothing -- there is no lineage above an annual plan
        # element to filter by -- so row 2 is an empty frame one combo deep.
        # The user asked for the blank line by name: without it the body of
        # this tab starts 36px above the body of the four that do filter.
        self.filter_row = ctk.CTkFrame(
            header, fg_color="transparent", height=FILTER_ROW_HEIGHT)
        self.filter_row.grid(row=2, column=0, columnspan=6, sticky="w",
                             padx=8, pady=(0, 8))
        self.filter_row.grid_propagate(False)

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=0, minsize=520)
        body.grid_columnconfigure(1, weight=0, minsize=SPLITTER_WIDTH)
        body.grid_columnconfigure(2, weight=0, minsize=520)
        body.grid_rowconfigure(1, weight=1)
        self.body = body

        self.left_title_label = ctk.CTkLabel(
            body,
            text="Vision Elements (check elements to add to the year and hit save)",
            font=ctk.CTkFont(weight="bold"),
        )
        self.left_title_label.grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.right_title_label = ctk.CTkLabel(
            body,
            text="Annual Plan Elements for the year 0",
            font=ctk.CTkFont(weight="bold"),
        )
        self.right_title_label.grid(
            row=0, column=2, sticky="w", padx=8, pady=(8, 4)
        )

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

        # UPD-M4 — one table per panel, from screens/chip_table.py. The right
        # panel's Actions column is 140px, not the APE tabs' 84: it holds Edit
        # as well as Delete.
        self.left_table = ChipTable(
            self.left_list, self.settings,
            f"{self.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS,
        )
        self.right_table = ChipTable(
            self.right_list, self.settings,
            f"{self.SETTINGS_PREFIX}_right", ANNUAL_RIGHT_COLUMNS,
        )

        # UPD-M1 — the ratio, the clamp and the four handlers live in
        # screens/split_panel.py, and the ratio now persists.
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

        # UPD-M2 — the row drag lives in screens/row_drag.py. This screen's
        # drop target is the right *frame*, not the list inside it, which is
        # one pixel-level difference from the APE tabs and is kept: a drop on
        # the frame's padding counts here and does not there.
        self.row_drag = RowDragSource(
            self, self.right_frame, self._create_from_row
        )

    def _parse_year(self) -> Optional[int]:
        try:
            return int(self.year_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Year", "Enter a valid year, e.g. 2026.")
            return None

    def refresh_lists(self):
        year = self._parse_year()
        if year is None:
            return

        self.segment_colors, self.subsegment_colors = load_latest_lineage_color_maps(self.vps_manager)
        self.category_colors = {
            (
                (r.get("segment_name", "") or "").strip().lower(),
                (r.get("subsegment_name", "") or "").strip().lower(),
                (r.get("name", "") or "").strip().lower(),
            ): (r.get("color_hex") or "")
            for r in self.vps_manager.get_vision_categories()
        }
        self.left_items = self.vps_manager.get_vision_elements()
        self.right_items = self.vps_manager.get_annual_vision_elements(year)
        self.left_title_label.configure(
            text="Vision Elements (check elements to add to the year and hit save)"
        )
        self.right_title_label.configure(
            text=f"Annual Plan Elements for the year {year}"
        )
        self._render_rows(self.left_table, self.left_items, selectable=True)
        self._render_rows(self.right_table, self.right_items, selectable=False)

    def _render_rows(self, table: ChipTable, rows: list[dict], selectable: bool):
        """Render one panel into the shared chip table.

        Purpose: UPD-M4 — the header, the row frames, the chips and the column
                 widths come from screens/chip_table.py. The checkbox and the
                 Actions cell stay here: this screen's Actions cell is a frame
                 holding Edit and Delete, which is why the table renders no
                 widget for a column the caller leaves out of `values`.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m4
        Tests:   tests/test_unified_panel_design.py::test_updm41_annual_right_row_keeps_edit_beside_delete
        """
        table.build_header()

        for idx, row in enumerate(rows):
            segment_name = row.get("segment_name", "")
            subsegment_raw = row.get("subsegment_name") or "-"
            segment_color, subsegment_color = resolve_lineage_colors(
                segment_name,
                subsegment_raw,
                self.vps_manager,
                self.segment_colors,
                self.subsegment_colors,
            )
            category_raw = row.get("category_name") or "-"
            category_color = row.get("category_color_hex") or self.category_colors.get(
                (
                    segment_name.strip().lower(),
                    subsegment_raw.strip().lower(),
                    category_raw.strip().lower(),
                ),
                "",
            )
            if not category_color:
                category_color = subsegment_color

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
                actions = ctk.CTkFrame(item, fg_color="transparent")
                actions.grid(row=0, column=table.grid_col("actions"),
                             padx=(4, 2), pady=5, sticky="w")
                ctk.CTkButton(
                    actions,
                    text="Edit",
                    width=64,
                    command=lambda r=row: self.edit_annual_item(r),
                    **button_style("secondary"),
                ).pack(side="left", padx=(0, 2))
                ctk.CTkButton(
                    actions,
                    text="Delete",
                    width=64,
                    command=lambda r=row: self.delete_annual_item(r),
                    **button_style("danger"),
                ).pack(side="left", padx=(2, 0))

    def _create_from_index(self, idx: int):
        year = self._parse_year()
        if year is None:
            return
        if idx < 0 or idx >= len(self.left_items):
            return
        item = self.left_items[idx]
        self._create_from_row(item)

    def _create_from_row(self, row: dict):
        year = self._parse_year()
        if year is None:
            return
        self.vps_manager.create_annual_records_from_vision_element(year, row["id"])
        self.refresh_lists()

    def add_selected(self):
        year = self._parse_year()
        if year is None:
            return
        selected_ids = [k for k, v in self.left_checks.items() if v.get()]
        if not selected_ids:
            return
        selected_set = set(selected_ids)
        for row in self.left_items:
            if row.get("id") in selected_set:
                self.vps_manager.create_annual_records_from_vision_element(year, row["id"])
        self.refresh_lists()


    def edit_annual_item(self, row: dict):
        """Edit a right-side annual item by updating its source Vision Element."""
        vision_element_id = row.get("vision_element_id")
        if not vision_element_id:
            messagebox.showerror("Missing Source", "This annual record is missing its source Vision Element.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Annual Plan Element")
        dialog.geometry("620x220")
        dialog.transient(self)
        dialog.grab_set()

        segment_var = ctk.StringVar(value=row.get("segment_name") or "")
        subsegment_var = ctk.StringVar(value=row.get("subsegment_name") or "")
        category_var = ctk.StringVar(value=row.get("category_name") or "")

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Segment:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        segment_combo = ctk.CTkComboBox(frame, variable=segment_var, values=[])
        segment_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(frame, text="SubSegment:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        subsegment_combo = ctk.CTkComboBox(frame, variable=subsegment_var, values=[], **combo_box_style())
        subsegment_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(frame, text="Category:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        category_combo = ctk.CTkComboBox(frame, variable=category_var, values=[], **combo_box_style())
        category_combo.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        status_label = ctk.CTkLabel(frame, text="", text_color=status_text_color("error"))
        status_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 6))

        def load_segments():
            values = [r["name"] for r in self.vps_manager.get_vision_segments()]
            segment_combo.configure(values=values or [""])

        def load_subsegments():
            seg = segment_var.get().strip() or None
            values = [r["name"] for r in self.vps_manager.get_vision_subsegments(segment_name=seg)]
            subsegment_combo.configure(values=values or [""])

        def load_categories():
            seg = segment_var.get().strip() or None
            sub = subsegment_var.get().strip() or None
            values = [r["name"] for r in self.vps_manager.get_vision_categories(segment_name=seg, subsegment_name=sub)]
            category_combo.configure(values=values or [""])

        segment_combo.configure(command=lambda _v: (load_subsegments(), load_categories()))
        subsegment_combo.configure(command=lambda _v: load_categories())

        load_segments()
        load_subsegments()
        load_categories()

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=4, column=0, columnspan=2, sticky="e", padx=8, pady=(8, 4))
        ctk.CTkButton(actions, text="Cancel", width=90, command=dialog.destroy, **button_style("secondary")).pack(
            side="right", padx=4
        )

        def on_save():
            seg = segment_var.get().strip()
            sub = subsegment_var.get().strip()
            cat = category_var.get().strip()
            if not seg or not sub or not cat:
                status_label.configure(text="Segment, SubSegment, and Category are required.")
                return
            try:
                self.vps_manager.update_vision_element(vision_element_id, seg, sub, cat)
            except Exception as exc:
                status_label.configure(text=f"Unable to save: {exc}")
                return
            dialog.destroy()
            self.refresh_lists()

        ctk.CTkButton(actions, text="Save", width=90, command=on_save, **button_style("primary")).pack(
            side="right", padx=4
        )

    def delete_annual_item(self, row: dict):
        year = self._parse_year()
        if year is None:
            return

        vision_element_id = row.get("vision_element_id")
        if not vision_element_id:
            messagebox.showerror("Missing Source", "This annual record is missing its source Vision Element.")
            return

        key = row.get("key_field") or "this annual record"
        if not messagebox.askyesno(
            "Delete Annual Vision Record",
            f"Delete {key} from {year}?",
            icon="warning",
        ):
            return

        try:
            deleted = self.vps_manager.delete_annual_records_for_vision_element(year, vision_element_id)
        except ProjectBoardsAttachedError as exc:
            project_list = "\n".join(f"  • {title}" for title in exc.board_titles)
            messagebox.showerror(
                "Projects Attached",
                "You must delete or reassign all Projects from an APE before you "
                f"can delete an APE.\n\n{len(exc.board_titles)} project(s) attached:\n"
                f"{project_list}",
            )
            return
        except ActionItemsAttachedError as exc:
            # An Annual Plan Element is deleted only when it has no child
            # records. This handler caught the *projects* refusal and not the
            # items one, so the new exception would have escaped a Tk callback
            # into a stderr a double-clicked app has nowhere to send (P5 — the
            # sibling exception was not handled).
            # Tests: tests/test_vps_ape_deletion_ui.py
            shown = "\n".join(f"  • {title}" for title in exc.titles[:10])
            if len(exc.titles) > 10:
                shown += f"\n  • ... and {len(exc.titles) - 10} more"
            messagebox.showerror(
                "Action Items Attached",
                "You must move or delete all Action Items on an APE before you "
                f"can delete it.\n\n{len(exc.titles)} action item(s) attached:\n"
                f"{shown}",
            )
            return

        if deleted:
            self.refresh_lists()
        else:
            messagebox.showerror("Delete Failed", "Annual record could not be deleted.")
