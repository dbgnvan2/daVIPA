# BACKLOG archive — 2026-11-12

Filed out of `BACKLOG.md` when the VSP-area items were worked. Each item
carries its closure under it. This is a filed record. No test reads it.

## Adjacent issues — the VSP tab filters and adds (VTF, filed 2026-11-11)

Found while building VTF-M1 - VTF-M7 and not fixed, under global rule 10.

### VTF-A1 — `screens/vision_planning.py` is an unreachable second annual panel (medium)

`show_vision_planning` has no caller: `grep -rn "show_vision_planning" src/`
finds the definition and nothing else. The module builds its own copy of the
Annual Plan Elements panel — the same two lists, the same ticks — so it did
**not** get the tick filter this batch added to
`screens/annual_vision_segments.py`, and nothing on screen reveals that,
because nothing on screen reaches it. Either delete it, or route the hub's tab
at it and delete the other one; two copies of one panel is how one of them
silently rots.

### VTF-A2 — two `weekly_items` methods are now unreachable from the UI (low)

`delete_selected_weekly_item` and `create_action_item_for_selected_weekly` were
the commands of the two bottom buttons VTF-M5 removed. Nothing calls them from
`src/` any more, but they are still exercised by tests in
`tests/test_unified_panel_design.py`, `tests/test_weekly_items_title.py` and
`tests/test_weekly_items_tactic_link.py`, so deleting the methods reddens three
files. They were left in place rather than deleted-with-their-tests inside a
batch whose subject was the buttons. Deleting them is a change of its own, and
the tests that cover the row's own Delete and APE Week Actions' Add must be
kept — only the selection-based ones go.

### VTF-A3 — four test files each carry their own withdrawn-root screen builder (low)

`tests/test_vsp_tab_filters.py`, `tests/test_vsp_tab_adds.py`,
`tests/test_vsp_tab_contracts.py` and `tests/test_unified_panel_design.py` each
define their own `_root()` / screen-construction helper, with the same
`ctk.CTk()` + `geometry("1400x900+0+0")` + `withdraw()` body. The withdrawal is
what keeps `tests/test_ci_contract.py`'s mapped-window count where it is (the
live number is in CLAUDE.md and conftest.py, and this entry said 23 after it
had moved), so the duplication is four places a future copy can forget it. A shared fixture in
`conftest.py` would make that impossible rather than merely conventional.

**Closed 2026-11-12.**

- VTF-A1 — deleted. `screens/vision_planning.py` and `app.show_vision_planning`
  were removed in `105900e`; the hub's tab is the one annual panel.
- VTF-A2 — deleted. Both methods went in `3ab1e45`. Their button tests went in
  `f4cb31d`; the BP6 lineage tests were kept and now build the item the way APE
  Week Actions' Add does (`tests/test_week_filed_item_lineage.py`), and
  `test_updm53` drives the row's Delete, the one caller left.
- VTF-A3 — one builder, `conftest.withdrawn_root(geometry=...)`, replaces the
  copies. There were eight, not four: `test_ape_week_actions.py` (1200x800),
  `test_weekly_tactic_parent.py`, `test_date_picker.py` and
  `test_inline_date_offsets.py` (no geometry) carried the same body. It is a
  function rather than a fixture because the screen builders in those files
  call it from inside helpers. The entry's premise was overstated:
  `_keep_tk_windows_off_screen` already withdraws every window at creation, so
  a copy that forgot `withdraw()` would not have put a window on screen. The
  guard is `tests/test_tk_offscreen.py::test_vtfa3_the_shared_root_takes_the_size_it_is_given`.

## Adjacent issue — the add button's panel on the other two VSP tabs (APB, filed 2026-11-12)

Raised by the cold sweep over the batch that moved APE Quarter Assignment's
and APE Month Assignment's add buttons under their left panels (`632cd7c`),
and not fixed, under global rule 10.

### APB-A1 — APE Week Assignment's add button is under the right panel against the same rule (medium)

The move was justified by "the control sits with the records it reads", and
that is equally true of `screens/weekly_items.py`: its `_add_options` builds
the dialog's options from `self.left_items` and `open_add_dialog` prompts
"Which Annual Plan Element is the tactic for ...?" off an `APE_LEFT_COLUMNS`
left panel, yet `Add Weekly Tactic` sits under the right one
(`weekly_items.py:229`). Nothing ties it there: that screen's `status_label`
is parented to the header (`weekly_items.py:161`), so moving the button moves
nothing else.

Annual Plan Elements is a different case and is **not** part of this item: its
`status_label` is parented to `right_actions`
(`annual_vision_segments.py:196`) and pinned there by
`tests/test_vsp_tab_contracts.py::test_vtfm71_annual_plan_elements_controls`,
so moving that button moves the status
line with it, or breaks the contract that says the outcome is reported beside
the button.

Not fixed because the request named the two APE assignment screens only, and
moving a third tab's control is a user-visible change on a screen nobody asked
about. Either move it for consistency, or record that APE Week Assignment adds
a right-panel record from the right panel on purpose.

**Closed 2026-11-12 as deliberate, by the user's decision.** `Add Weekly
Tactic` stays under the right panel of APE Week Assignment. It adds a record,
and the record it adds lands in the right panel, so the button sits with what
it creates. The Quarter and Month buttons moved left because they *assign* the
left record to the period on screen and create nothing; that reasoning does
not apply here.

### 2026-11-07 - Type: Cleanup

**Title:** AWA-A2 - a second "APE Weekly" label survives in dead code
**Description:** `screens/vision_planning.py:186` captions a placeholder tab
`"APE Weekly"`. `VisionPlanningScreen` is reachable only through
`app.show_vision_planning`, which no sidebar entry calls. Renaming the label is
harmless; leaving it means a grep for "APE Weekly" still hits. The real
question is whether `vision_planning.py` should exist at all — it is a whole
screen of placeholders behind an unreachable entry point. Decide that, rather
than renaming a label inside it.
**Priority:** Low
**Effort:** Small

**Moot 2026-11-12.** `screens/vision_planning.py` was deleted (VTF-A1,
`105900e`), so the label is gone with it.
`tests/test_ape_week_actions.py::test_awam13_no_ape_weekly_label_remains` now
walks all of `src/` (`020d13b`).
