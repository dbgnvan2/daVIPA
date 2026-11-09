"""APE month assignment screen with two-panel APE workflow."""

from datetime import date
from tkinter import messagebox
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from ..app_settings import AppSettings
from ..date_utils import months_of_quarter, quarter_of_month
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


class APEPeriodViewScreen(ctk.CTkFrame):
    """Assign quarter-selected APEs to a selected month."""

    # UPD-D3/D4 — this screen's own corner of AppSettings. The divider's ratio
    # is stored under ``<SETTINGS_PREFIX>_split_ratio`` and each panel's column
    # widths under ``<SETTINGS_PREFIX>_<side>_col_widths``.
    SETTINGS_PREFIX = "ape_month"

    def __init__(self, parent, vps_manager: "VPSManager", app: "GetMoreDoneApp"):
        super().__init__(parent)
        self.vps_manager = vps_manager
        self.app = app

        year, quarter, month = self.default_period(date.today())
        self.year_var = ctk.StringVar(value=str(year))
        self.quarter_var = ctk.StringVar(value=str(quarter))
        self.month_var = ctk.StringVar(value=str(month))
        self.segment_filter_var = ctk.StringVar(value="All")
        self.subsegment_filter_var = ctk.StringVar(value="All")
        self.category_filter_var = ctk.StringVar(value="All")

        self.left_items: list[dict] = []
        self.right_items: list[dict] = []
        self.segment_colors = {}
        self.subsegment_colors = {}
        self.category_colors = {}
        self.left_checks: dict[str, ctk.BooleanVar] = {}
        # The app's own instance where there is one, so a saved divider or
        # column width does not overwrite a setting changed elsewhere since
        # this screen was built; its own load when constructed without an app
        # (tests).
        self.settings = getattr(app, "settings", None) or AppSettings.load()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_ui()
        self.refresh_lists()

    def create_ui(self):
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(14, weight=1)

        ctk.CTkLabel(
            header,
            text="APE Month Assignment",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=15, sticky="w", padx=8, pady=(8, 6))

        ctk.CTkLabel(header, text="Year:").grid(row=1, column=0, padx=(8, 4), pady=(0, 8), sticky="e")
        ctk.CTkEntry(header, width=86, textvariable=self.year_var).grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")
        ctk.CTkLabel(header, text="Quarter:").grid(row=1, column=2, padx=(8, 4), pady=(0, 8), sticky="e")
        self.quarter_combo = ctk.CTkComboBox(
            header,
            width=74,
            values=["1", "2", "3", "4"],
            variable=self.quarter_var,
            command=lambda _v: self.on_quarter_changed(),
        )
        self.quarter_combo.grid(row=1, column=3, padx=4, pady=(0, 8), sticky="w")
        ctk.CTkLabel(header, text="Month:").grid(row=1, column=4, padx=(8, 4), pady=(0, 8), sticky="e")
        self.month_combo = ctk.CTkComboBox(header, width=74, values=["1"], variable=self.month_var)
        self.month_combo.grid(row=1, column=5, padx=4, pady=(0, 8), sticky="w")
        self._sync_month_choices()
        ctk.CTkButton(header, text="Load", width=88, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=6, padx=(8, 4), pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Save", width=88, command=self.add_selected, **button_style("primary")).grid(
            row=1, column=7, padx=4, pady=(0, 8), sticky="w"
        )
        ctk.CTkButton(header, text="Refresh", width=88, command=self.refresh_lists, **button_style("secondary")).grid(
            row=1, column=8, padx=(4, 12), pady=(0, 8), sticky="w"
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
        self.filter_row.grid(row=2, column=0, columnspan=15, sticky="w",
                             padx=8, pady=(0, 8))

        ctk.CTkLabel(self.filter_row, text="Segment:").grid(row=0, column=0, padx=(0, 4), sticky="e")
        self.segment_filter_combo = ctk.CTkComboBox(
            self.filter_row, width=150, values=["All"], variable=self.segment_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.segment_filter_combo.grid(row=0, column=1, padx=4, sticky="w")

        ctk.CTkLabel(self.filter_row, text="SubSegment:").grid(row=0, column=2, padx=(10, 4), sticky="e")
        self.subsegment_filter_combo = ctk.CTkComboBox(
            self.filter_row, width=150, values=["All"], variable=self.subsegment_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.subsegment_filter_combo.grid(row=0, column=3, padx=4, sticky="w")

        ctk.CTkLabel(self.filter_row, text="Category:").grid(row=0, column=4, padx=(10, 4), sticky="e")
        self.category_filter_combo = ctk.CTkComboBox(
            self.filter_row, width=150, values=["All"], variable=self.category_filter_var, command=lambda _v: self.on_filters_changed()
        )
        self.category_filter_combo.grid(row=0, column=5, padx=4, sticky="w")

        # APC-M2.3 — somewhere for Save to say what it did. Both the button and
        # the drag write through here; before this the screen reported neither
        # a success nor a refusal.
        self.status_label = ctk.CTkLabel(header, text="", text_color=status_text_color("muted"))
        self.status_label.grid(row=3, column=0, columnspan=15, sticky="w", padx=8, pady=(0, 8))

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

        # UPD-M4 — one table per panel, from screens/chip_table.py.
        self.left_table = ChipTable(
            self.left_list, self.settings,
            f"{self.SETTINGS_PREFIX}_left", APE_LEFT_COLUMNS,
        )
        self.right_table = ChipTable(
            self.right_list, self.settings,
            f"{self.SETTINGS_PREFIX}_right", APE_RIGHT_COLUMNS,
        )

        # UPD-M1 — the ratio, the clamp and the four handlers live in
        # screens/split_panel.py. UPD-M4 is where this screen stopped keeping
        # its own copy of them, and gained the persistence it never had.
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
        # screens/row_drag.py. What a dropped row means is this screen's.
        self.row_drag = RowDragSource(
            self, self.right_list, self._assign_dragged_row
        )

    @staticmethod
    def default_period(today: date) -> tuple[int, int, int]:
        """The year, quarter and month the screen opens on.

        Purpose: open on a period that exists, with a quarter and a month that
                 agree.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m3
        Tests:   tests/test_ape_period_consistency.py::test_apcm31_quarter_defaults_to_current_quarter
                 tests/test_ape_period_consistency.py::test_apcm34_default_month_is_always_inside_the_default_quarter

        APC-M3.1 / APC-M3.4. The quarter used to be the literal ``"1"`` while
        the month was today's, so for eight months of the year the screen
        opened on a pair that cannot both be true — and on 7 November it
        offered Q1 + M11, which Save then wrote.

        Takes ``today`` rather than reading the clock so the pairing can be
        checked for every month of the year, not just the one the suite
        happens to run in.
        """
        return today.year, quarter_of_month(today.month), today.month

    def _sync_month_choices(self):
        """Offer only the months the selected quarter contains.

        Purpose: make an impossible quarter/month pair unpickable rather than
                 merely rejected after the fact.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m3
        Tests:   tests/test_ape_period_consistency.py::test_apcm32_month_combo_offers_only_that_quarters_months
                 tests/test_ape_period_consistency.py::test_apcm33_changing_quarter_moves_month_into_range

        APC-M3.2 / APC-M3.3. One code path builds the month list, at startup
        and on every quarter change, so the opening state cannot drift from the
        state a change produces. A month already inside the new quarter is
        kept; one outside it moves to that quarter's first month, because
        leaving it would recreate the pair this change exists to prevent.
        """
        try:
            quarter = int(self.quarter_var.get().strip())
            allowed = months_of_quarter(quarter)
        except (ValueError, TypeError):
            return
        self.month_combo.configure(values=[str(month) for month in allowed])
        try:
            current = int(self.month_var.get().strip())
        except (ValueError, TypeError):
            current = None
        if current not in allowed:
            self.month_var.set(str(allowed[0]))

    def on_quarter_changed(self):
        self._sync_month_choices()
        self.refresh_lists()

    def _parse_period(self) -> Optional[tuple[int, int, int]]:
        try:
            year = int(self.year_var.get().strip())
            quarter = int(self.quarter_var.get().strip())
            month = int(self.month_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Period", "Enter a valid year, quarter, and month.")
            return None
        if quarter not in (1, 2, 3, 4):
            messagebox.showerror("Invalid Quarter", "Quarter must be 1, 2, 3, or 4.")
            return None
        if month < 1 or month > 12:
            messagebox.showerror("Invalid Month", "Month must be between 1 and 12.")
            return None
        # APC-M3 — the pickers cannot produce this pair, but a stale variable
        # or a hand-typed year still reaches here, and the manager refuses the
        # write anyway (APC-M2.1). Saying so beats a Save that does nothing.
        if quarter_of_month(month) != quarter:
            messagebox.showerror(
                "Quarter and Month Disagree",
                f"Month M{month} is in Q{quarter_of_month(month)}, not Q{quarter}.",
            )
            return None
        return year, quarter, month

    def refresh_lists(self):
        parsed = self._parse_period()
        if not parsed:
            return
        year, quarter, month = parsed

        self.segment_colors, self.subsegment_colors = load_latest_lineage_color_maps(self.vps_manager)
        self.category_colors = {
            (
                (r.get("segment_name", "") or "").strip().lower(),
                (r.get("subsegment_name", "") or "").strip().lower(),
                (r.get("name", "") or "").strip().lower(),
            ): (r.get("color_hex") or "")
            for r in self.vps_manager.get_vision_categories()
        }
        self.left_items = self.vps_manager.get_annual_plan_elements_for_quarter(year, quarter)
        self.right_items = self.vps_manager.get_annual_plan_elements_for_month(year, month)
        self._refresh_filter_options()
        self.left_title_label.configure(text=f"APE For Quarter Q{quarter} (check APEs to add to Month M{month} and hit save)")
        self.right_title_label.configure(text=f"APE For Month M{month}")
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
        """Assign every checked APE to the selected month.

        Purpose: APC-M2.3 — Save says what it did, including what it failed to
                 do, for every APE in the press rather than for the press.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m2
        Tests:   tests/test_ape_period_consistency.py::test_apcm23_save_reports_refused_assignments
                 tests/test_ape_period_consistency.py::test_apcm24_a_raising_assignment_is_counted_not_escaped

        APC-M2.4 — each APE is assigned inside its own ``try``.
        ``assign_ape_to_month`` does not only return ``False``: it raises
        ``ValueError`` when an APE's ``segment_name`` resolves to no segment
        (``vps_manager`` — the renamed-segment hazard
        ``tests/test_rename_safe_links.py`` exists for). Without the ``try``
        the raise left the earlier APEs written, skipped both the redraw and
        the status line, and left the *previous* press's "Assigned 3 APE(s)"
        on screen — a success message for a save that half happened, with the
        traceback going to a stderr a double-clicked app does not have.

        Counted as refused rather than re-raised, and the exception goes to the
        log: the whole point of the status line is that a press reconciles
        with what reached the database, and a press that wrote two of three
        has to say two.
        """
        parsed = self._parse_period()
        if not parsed:
            return
        _year, quarter, month = parsed
        selected_ids = [row_id for row_id, var in self.left_checks.items() if var.get()]
        if not selected_ids:
            self.status_label.configure(text="Check one or more APEs on the left first.")
            return
        claimed = {
            ape_id for ape_id in selected_ids
            if self._assign_one(ape_id, quarter, month)
        }
        self.refresh_lists()
        self.status_label.configure(
            text=self._describe_month_assignment(
                selected_ids, claimed, self._ids_in_month(), month
            )
        )

    def _ids_in_month(self) -> set:
        """Which APEs the month really holds, as the right-hand panel has it.

        Purpose: APC-M2.5 — give the status line the artifact to reconcile
                 against, and make it the same read the panel is drawn from.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m2
        Tests:   tests/test_ape_period_consistency.py::test_apcm25_a_half_written_assignment_is_reported_as_partial

        ``refresh_lists`` has just set ``self.right_items`` from
        ``get_annual_plan_elements_for_month``, unfiltered. Reading it rather
        than asking again means the sentence and the panel cannot disagree:
        they are computed from one query.
        """
        return {row["id"] for row in getattr(self, "right_items", [])}

    def _assign_one(self, ape_id: str, quarter: int, month: int) -> bool:
        """One APE's month assignment: ``True`` only if the call said so.

        Not "only if the row was written" — that was this docstring's first
        claim and it is wrong in the direction that reaches the user. The
        manager writes before it can fail, so ``False`` here does **not** mean
        nothing was written. The caller reconciles against the row; this only
        reports what the call claimed.

        Purpose: APC-M2.4 — the one place a refusal and a raise are turned into
                 the same answer, so both callers on this screen count them the
                 same way.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m2
        Tests:   tests/test_ape_period_consistency.py::test_apcm24_a_raising_assignment_is_counted_not_escaped

        Both the Save button and the drop target go through here. Hardening one
        and leaving the other to raise is the sibling problem P5 describes, and
        it is the mistake the first version of this screen made.
        """
        try:
            if self.vps_manager.assign_ape_to_month(ape_id, quarter, month):
                return True
            logger.warning(
                "[ape_period_view] APE %s was not assigned to %d/%d.", ape_id, quarter, month
            )
        except Exception:
            logger.exception(
                "[ape_period_view] APE %s raised while being assigned to %d/%d.",
                ape_id, quarter, month,
            )
        return False

    @staticmethod
    def _describe_month_assignment(selected, claimed, in_month, month: int) -> str:
        """APC-M2.5 — the sentence is computed from the rows, not from a return code.

        Purpose: never let a refused assignment look like a successful one, and
                 never let a half-written one look like either.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m2
        Tests:   tests/test_ape_period_consistency.py::test_apcm23_save_reports_refused_assignments
                 tests/test_ape_period_consistency.py::test_apcm25_a_half_written_assignment_is_reported_as_partial

        ``assign_ape_to_month`` writes before it can fail.
        ``assign_ape_to_quarter`` commits the quarter flag and only then raises
        on a segment it cannot resolve, and ``assign_ape_to_month`` has two
        ``return False`` exits after both the quarter and the month flag are
        committed. So the first version of this — counting the booleans
        ``_assign_one`` handed back — said "Assigned 0 APE(s)" beside a panel
        that was showing the row. A status line about a write has to be read
        off the row after the call, which is P6, and reporting from a return
        code is P6 inverted.

        Four states, all named, because each is a different thing to do next
        (P2 — surface, never drop):

        - **assigned**: the call succeeded and the month holds it.
        - **partly assigned**: the call failed but the month holds it anyway —
          the flag is set with no month tactic behind it, and a retry raises
          again, so it needs the segment fixed rather than another press.
        - **could not be assigned**: the call failed and nothing was written.
        - **reported assigned but not in the month**: the call said yes and the
          row is not there. Nothing is known to produce this, which is exactly
          why it is reported rather than folded into one of the others.

        The class is four write paths across two screens. Both of this screen's
        report through here; APE Quarter has ``_describe_quarter_assignment``,
        the same wording with Q for M. The two *remove* paths are a fifth and
        sixth, and the cascade's own call site a seventh — see §5.11 of the
        spec for which were fixed and which were flagged.
        """
        assigned = [a for a in selected if a in claimed and a in in_month]
        partial = [a for a in selected if a not in claimed and a in in_month]
        refused = [a for a in selected if a not in claimed and a not in in_month]
        missing = [a for a in selected if a in claimed and a not in in_month]

        text = f"Assigned {len(assigned)} APE(s) to M{month}."
        if partial:
            text += (
                f" {len(partial)} partly assigned — in M{month} with no month "
                f"tactic behind it; see the log."
            )
        if refused:
            text += f" {len(refused)} could not be assigned — see the log."
        if missing:
            text += (
                f" {len(missing)} reported assigned but are not in M{month} — "
                f"see the log."
            )
        return text

    def _render_rows(self, table: ChipTable, rows: list[dict], selectable: bool):
        """Render one panel into the shared chip table.

        Purpose: UPD-M4 — the header, the row frames, the chips and the column
                 widths come from screens/chip_table.py. The checkbox and the
                 Actions cell stay here, because what they do is this screen's.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m4
        Tests:   tests/test_unified_panel_design.py::test_updm41_ape_month_headers_and_widths_are_unchanged
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
                    command=lambda r=row: self.delete_month_item(r),
                    **button_style("danger"),
                ).grid(row=0, column=table.grid_col("actions"), padx=5, pady=5, sticky="e")

    def delete_month_item(self, row: dict):
        parsed = self._parse_period()
        if not parsed:
            return
        _year, quarter, month = parsed
        label = row.get("key_field") or "this APE"
        if not messagebox.askyesno("Remove APE", f"Remove {label} from Month M{month}?", icon="warning"):
            return
        ok = self._remove_one(row["id"], quarter, month)
        self.refresh_lists()
        still_there = row["id"] in self._ids_in_month()
        if ok and not still_there:
            self.status_label.configure(text=f"Removed {label} from M{month}.")
        elif still_there:
            self.status_label.configure(
                text=f"{label} is still in M{month} — see the log."
            )
        else:
            self.status_label.configure(
                text=f"{label} is out of M{month}, but the remove reported a "
                     f"problem — see the log."
            )

    def _remove_one(self, ape_id: str, quarter: int, month: int) -> bool:
        """One APE's month removal: ``True`` only if the call reported success.

        Purpose: APC-M2.6 — the remove path reports too. It is the same class
                 as the two assign paths, on the same screen, and the first
                 version of this fix corrected only the assigns.
        Spec:    docs/spec_2026-11-07_ape_period_consistency.md#apc-m2
        Tests:   tests/test_ape_period_consistency.py::test_apcm26_a_failed_remove_is_reported

        Said against the row, as the assigns are: this returns what the call
        claimed, and the caller checks whether the APE actually left the month.
        A dialog that promised removal and a panel that still shows the row is
        the whole fault being fixed here, in its clearest form.
        """
        try:
            if self.vps_manager.unassign_ape_from_month(ape_id, quarter, month):
                return True
            logger.warning(
                "[ape_period_view] APE %s was not removed from %d/%d.",
                ape_id, quarter, month,
            )
        except Exception:
            logger.exception(
                "[ape_period_view] APE %s raised while being removed from %d/%d.",
                ape_id, quarter, month,
            )
        return False

    def _assign_dragged_row(self, row: dict):
        """Assign one dragged row to the selected month, and report it.

        Purpose: UPD-M2 — what a dropped row means on this screen. The drag,
                 the drop test and the descendant walk are in
                 screens/row_drag.py; this is the body of what was
                 _finish_row_drag's final `if`, moved as it was.
        Spec:    docs/spec_2026-11-07_unified_panel_design.md#upd-m2
        Tests:   tests/test_unified_panel_design.py::test_updm43_a_drop_assigns_on_each_tab
        """
        parsed = self._parse_period()
        if parsed:
            _year, quarter, month = parsed
            ok = self._assign_one(row["id"], quarter, month)
            self.refresh_lists()
            self.status_label.configure(
                text=self._describe_month_assignment(
                    [row["id"]],
                    {row["id"]} if ok else set(),
                    self._ids_in_month(),
                    month,
                )
            )

