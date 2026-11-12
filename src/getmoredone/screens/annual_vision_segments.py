"""Annual Plan Elements screen with drag/drop from Vision Elements."""

import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from ..app_settings import AppSettings
from ..theme import button_style, combo_box_style, semantic_colors, status_text_color
from ..vps_manager import ActionItemsAttachedError, ProjectBoardsAttachedError
from ..weekly_tactic_logging import get_weekly_tactic_logger
from .chip_table import ANNUAL_RIGHT_COLUMNS, APE_LEFT_COLUMNS, ChipTable, panel_fitter
from .lineage_filters import FILTER_ROW_HEIGHT
from .pick_record_dialog import describe_lineage, open_pick_record_dialog
from .row_drag import RowDragSource
from .segment_color_utils import load_latest_lineage_color_maps, resolve_lineage_colors
from .split_panel import SPLITTER_WIDTH, SplitPanel

logger = get_weekly_tactic_logger()

if TYPE_CHECKING:
    from ..vps_manager import VPSManager
    from ..app import GetMoreDoneApp


# VTF-M1 — the left panel's ticks became a filter on the right panel, so the
# heading no longer tells the user to tick and press Save. There is no Save on
# this tab any more (VTF-M4); records are created from the button under the
# right panel (VTF-M3).
# The width the status line beside the Add New button wraps at. The button is
# 230px and the right half of the body is about 660px at the default ratio, so
# this is what is left for the sentence.
STATUS_WRAPLENGTH = 400

LEFT_TITLE = "Vision Elements (tick to filter the annual elements on the right)"


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
        # The year the panels currently show, which is not the year in the
        # entry box: the entry can be mid-edit, and the right panel's heading
        # must not re-parse it (a bad value pops an error dialog).
        self.shown_year = 0
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
        # Spec:  docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md#3-upd-f2
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
        ctk.CTkButton(header, text="Refresh", width=90, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=3, padx=6, pady=(0, 8), sticky="w"
        )

        # This tab carries no lineage *dropdowns* -- there is no lineage above
        # a vision element to narrow the left list by -- so row 2 is an empty
        # frame one combo deep. The user asked for the blank line by name:
        # without it the body of this tab starts 36px above the body of the
        # four that do filter. The left panel's ticks are this tab's filter
        # (VTF-M1) and sit on the rows, not here.
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
            text=LEFT_TITLE,
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

        # VTF-M3.1/M3.7 — the Add New that replaced the header Save, and
        # the status line it reports on. Under the right panel, because the
        # record it creates is a right-panel record.
        right_actions = ctk.CTkFrame(body, fg_color="transparent")
        right_actions.grid(row=2, column=2, sticky="ew", padx=(2, 8), pady=(0, 8))
        self.right_actions = right_actions
        ctk.CTkButton(
            right_actions,
            text="Add New Annual Plan Element",
            width=230,
            command=self.open_add_dialog,
            **button_style("primary"),
        ).pack(side="left", padx=(0, 8))
        # VTF-S8 — this is the one status line that sits in a panel column
        # rather than across the header, and `SplitPanel` sets that column's
        # width with `minsize`, which is a floor and not a ceiling. Without a
        # wrap the first long sentence -- the refusals below are over a
        # hundred characters -- makes the column request its own width and
        # pushes the panels off the body.
        self.status_label = ctk.CTkLabel(
            right_actions, text="", anchor="w",
            text_color=status_text_color("muted"),
            wraplength=STATUS_WRAPLENGTH, justify="left")
        self.status_label.pack(side="left", fill="x", expand=True)

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
        self.shown_year = year
        self.left_title_label.configure(text=LEFT_TITLE)
        self._render_rows(self.left_table, self.left_items, selectable=True)
        self.refresh_right_panel()

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
                ctk.CTkCheckBox(
                    item, text="", variable=var, width=20,
                    command=self.refresh_right_panel,
                ).grid(
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

    # ------------------------------------------------ the tick as a filter

    def _ticked_vision_element_ids(self) -> set:
        """The ids of the ticked rows the left panel is currently showing.

        Purpose: VTF-M1 — the tick is this tab's filter. A tick is only
                 honoured while its row is on screen (VTF-M1.9): a filter the
                 user cannot see is a filter they cannot undo. This tab shows
                 every vision element, so the restriction is a no-op here and
                 is written anyway, because `left_checks` outlives a Load Year
                 and would otherwise keep filtering by a row that has gone.
        Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
        Tests:   tests/test_vsp_tab_filters.py::test_vtfm19_a_hidden_tick_stops_filtering
        """
        visible = {
            row.get("id", f"row-{idx}")
            for idx, row in enumerate(self.left_items)
        }
        return {
            key for key, var in self.left_checks.items()
            if key in visible and var.get()
        }

    def _visible_right_items(self) -> list:
        """The right-hand rows the current ticks allow.

        No tick is no filter (VTF-M1.5), so an untouched screen shows the
        whole year exactly as it did before VTF-M1.
        """
        ticked = self._ticked_vision_element_ids()
        if not ticked:
            return list(self.right_items)
        return [
            row for row in self.right_items
            if row.get("vision_element_id") in ticked
        ]

    def refresh_right_panel(self):
        """Re-render the right panel alone, from the ticks.

        Purpose: VTF-M1.6 — the checkbox's own command, so a tick takes
                 effect without Load Year or Refresh. The left panel is not
                 re-rendered (VTF-M1.8): rebuilding it under the pointer would
                 destroy the checkbox that is mid-click, and a tick must never
                 be able to hide its own row.
        Tests:   tests/test_vsp_tab_filters.py::test_vtfm16_the_tick_refreshes_without_a_button
        """
        shown = self._visible_right_items()
        self.right_title_label.configure(text=self._right_title(shown))
        self._render_rows(self.right_table, shown, selectable=False)

    def _right_title(self, shown: list) -> str:
        """The right panel's heading, which says when a filter is narrowing it."""
        base = f"Annual Plan Elements for the year {self.shown_year}"
        if len(shown) == len(self.right_items):
            return base
        return f"{base} ({len(shown)} of {len(self.right_items)}, filtered by tick)"

    def _create_from_index(self, idx: int):
        year = self._parse_year()
        if year is None:
            return
        if idx < 0 or idx >= len(self.left_items):
            return
        item = self.left_items[idx]
        self._create_from_row(item)

    def _create_from_row(self, row: dict):
        """Create a dropped Vision Element's annual records, and say what happened.

        Purpose: the drop is a write, so it goes through the same write the
                 Add New dialog uses. It called the manager raw until
                 2026-11-11: `row_drag.finish` wraps `on_drop` in no `try`,
                 so a locked database or a stale row escaped into a Tk
                 callback -- a traceback on a stderr a packaged app has
                 nowhere to send, nothing on screen and no refresh -- and a
                 success said nothing either. The three sibling tabs all
                 guard and report on their drop (P1/P5).
        Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
        Tests:   tests/test_vsp_tab_adds.py::test_vtfs1_the_dropped_row_reports_what_it_wrote
                 tests/test_vsp_tab_adds.py::test_vtfs1_a_raising_drop_is_reported_not_escaped
        """
        key = row.get("id")
        if not key:
            self.status_label.configure(
                text="That row carries no Vision Element to add.")
            return
        self.status_label.configure(text=self._perform_add(key))

    # --------------------------------------------------- VTF-M3: Add New

    def _add_options(self) -> list:
        """The Vision Elements this year does not have an annual record for.

        Offering one that is already there would be an option that changes
        nothing: `create_annual_records_from_vision_element` is idempotent.
        """
        taken = {row.get("vision_element_id") for row in self.right_items}
        return [
            (row["id"], describe_lineage(row))
            for row in self.left_items
            if row.get("id") and row.get("id") not in taken
        ]

    def _empty_add_message(self, year: int) -> str:
        """Why the dialog has nothing to offer, in the words of the real reason.

        Purpose: VTF-S9 / P2/P9 — the quarter and month tabs' helper, for this
                 tab. One wording for two reasons told an empty database that
                 every Vision Element already had an annual record.
        Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
        Tests:   tests/test_vsp_tab_adds.py::test_vtfs9_every_tab_names_the_real_reason
        """
        if not self.left_items:
            return ("There are no Vision Elements yet -- add one on the "
                    "Vision Elements tab first.")
        return (f"Every Vision Element already has an annual record for "
                f"{year}.")

    def _add_default(self):
        """The ticked row to open the dialog on, when exactly one is ticked.

        VTF-M3.6 — one tick is an unambiguous intention; two are not, and
        guessing between them would create a record the user did not pick.
        """
        ticked = self._ticked_vision_element_ids()
        if len(ticked) != 1:
            return None
        only = next(iter(ticked))
        # The siblings' guard (P5): a key `_add_options` excluded is not an
        # option, so handing it over as `initial` opens the combo blank.
        taken = {row.get("vision_element_id") for row in self.right_items}
        return only if only not in taken else None

    def _perform_add(self, vision_element_id: str) -> str:
        """Create both annual records for one Vision Element, and say so.

        Purpose: VTF-M3.8 — the refresh is here, so the new row is in the
                 right panel before the sentence about it reaches the status
                 line. P6 — and the sentence is then read off that panel
                 rather than off the absence of an exception:
                 `create_annual_records_from_vision_element` logs a failed
                 project board as a warning and carries on, so "Added" was
                 claimed for a half-written record. P1 — a locked database is
                 reported, not raised into a Tk callback, because the drop
                 path shares this method and has no `try` above it.
        Spec:    docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md
        Tests:   tests/test_vsp_tab_adds.py::test_vtfs2_an_unwritten_add_is_not_reported_as_added
                 tests/test_vsp_tab_adds.py::test_vtfs1_a_raising_drop_is_reported_not_escaped
        """
        year = self._parse_year()
        if year is None:
            return "Enter a valid year first."
        row = next(
            (r for r in self.left_items if r.get("id") == vision_element_id),
            None)
        name = describe_lineage(row) if row else "the Vision Element"
        try:
            self.vps_manager.create_annual_records_from_vision_element(
                year, vision_element_id)
        except Exception as exc:
            logger.exception(
                "[annual_vision_segments] %s raised while being added to %s.",
                vision_element_id, year)
            self.refresh_lists()
            return f"Could not add {name} to {year}: {exc}"
        self.refresh_lists()
        if vision_element_id not in {
                r.get("vision_element_id") for r in self.right_items}:
            return (f"{name} is not in {year}'s Annual Plan Elements after "
                    f"the write -- see the log.")
        return f"Added {name} to {year}."

    def open_add_dialog(self):
        """VTF-M3.1 — pick a Vision Element and create its annual records."""
        year = self._parse_year()
        if year is None:
            return None
        return open_pick_record_dialog(
            self,
            title="Add New Annual Plan Element",
            prompt=f"Which Vision Element should {year} carry?",
            options=self._add_options(),
            initial=self._add_default(),
            confirm_text="Add",
            report=lambda text: self.status_label.configure(text=text),
            on_confirm=self._perform_add,
            empty_message=self._empty_add_message(year),
        )

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
