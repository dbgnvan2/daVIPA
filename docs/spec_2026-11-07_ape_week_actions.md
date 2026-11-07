# Spec + implementation plan — APE Week Assignment rename, and a Week Actions tab

**Date:** 2026-11-07
**Area:** VSP Plan → Vision Planning hub
**Status:** built 2026-11-07. Approved as written, then implemented; §6 holds
the per-criterion status report and the mutation table.
**Prefix for all IDs below:** `AWA`

---

## 0. What was asked

Verbatim, from the request:

1. Change the tab name "APE Weekly" to "APE Week Assignment".
2. Add a new tab to show the Action Items linked to the week tactic.
3. Model it like the other panels: the Weekly Tactics for the selected week on
   the left; clicking one shows the Action Items linked to it.
4. On the right, "add Action Item".
5. Clicking an Action Item edits it.
6. "In fact the Action Items panel on the RIGHT should work like the 'Today'
   tab except it's filtered by the weekly tactic vs. today's date."

---

## 1. What is there now

### 1.1 The hub and its tabs

`src/getmoredone/screens/vision_planning_hub.py` is the live screen behind the
sidebar's **VSP Plan** button (`app.py:245` → `show_vision_planning_hub` →
`VisionPlanningHubScreen`). It is 104 lines and holds the whole tab contract in
two places that must stay in step:

```python
buttons = [                                     # line 53
    ("Vision Elements",         "vision_segments"),
    ("Annual Plan Elements",    "annual_vision_segments"),
    ("APE Quarter Assignment",  "ape_assignment"),
    ("APE Month Assignment",    "ape_period_view"),
    ("APE Weekly",              "ape_weekly"),
]

mapping = {                                     # line 88
    ...
    "ape_weekly": WeeklyItemsScreen,
}
```

`src/getmoredone/screens/vision_planning.py` also has a tab captioned
`"APE Weekly"` (line 186), but it builds a **placeholder** tab
(`_build_placeholder_tab`) and its screen class is reached only through
`app.show_vision_planning`, which no sidebar entry calls. It is not what the
user sees. See §7.

### 1.2 The screen behind the tab

`screens/weekly_items.py` (611 lines, `WeeklyItemsScreen`) is a two-pane
splitter: month-assigned APEs on the left, Weekly Tactics for the selected week
on the right, with `Edit Weekly Tactic` / `Delete Weekly` / `Add Action Item`
beneath the right pane. Its own header label reads **"APE Weekly Assignment"**
(line 74) — already a different string from the tab's "APE Weekly".

Reusable pieces already in it, which the new tab needs and must not copy:

| Helper | Line | What it does |
|---|---|---|
| `_first_day_of_week` | 243 | reads `AppSettings.first_day_of_week`, clamped to 0-6 |
| `_week_start_for` | 251 | `week_calendar.week_start(...)` — WT-M2.B, one home for week identity |
| `_build_selectable_week_options` | 255 | current week + next 3, then any existing week starts |

### 1.3 How an Action Item is linked to a Weekly Tactic — two ways, both live

A Weekly Tactic is itself a row in `action_items` with `item_type = 'week'`
(`weekly_tactic.py:463`). A child Action Item points at it through **one of two
columns**, and the codebase does not agree which:

| Column | Written by | Read by |
|---|---|---|
| `weekly_tactic_id` | `weekly_tactic.py:549` (the cascade, when an item is brought into a week) | `tactic_id_of` (`weekly_tactic.py:144`) — the single predicate WT-M3.D.1 says decides "has a Weekly Tactic"; `weekly_tactic_maintenance.py:593` |
| `parent_id` | `weekly_items.py:442` — the existing **Add Action Item** button, which sets `parent_id=weekly["id"]` and leaves `weekly_tactic_id` NULL | `weekly_tactic_maintenance.py:278` (`_child_count`), which reads `weekly_tactic_id = ? OR parent_id = ?` |

`weekly_tactic_migrations.py:135` is explicit that `weekly_tactic_id` is the
column that exists precisely so a tactic link is **not** confused with
"ordinary daily nesting", and its migration repoints children off `parent_id`
onto `weekly_tactic_id`, setting `parent_id = NULL`.

**This is not theoretical.** Counted on 2026-11-07 against both real databases:

| Database | `item_type='week'` rows | children via `weekly_tactic_id` | children via `parent_id` | both |
|---|---|---|---|---|
| `~/Library/Application Support/GetMoreDone/` | 25 | **49** | **0** | 0 |
| `~/Library/Application Support/GetMoreDone-Demo/` | 1 | **0** | **1** | 0 |

So a panel that reads only `weekly_tactic_id` shows nothing in the demo
database; one that reads only `parent_id` shows nothing in the main database.
Either choice looks correct on one machine and empty on the other. This is the
single highest-risk decision in the feature, and it is settled in AWA-M2.

### 1.4 The Today screen, and how much of it is reusable

`screens/today.py` is 886 lines. The structure is better than the size suggests:

- `load_items()` (line 240) is **generic**. It calls exactly two things that are
  Today-specific: `self.get_todays_items()` for the data, and the literal
  `"No items for today"` for the empty state. Everything else — the open /
  completed split, the section headers, the completed-time total, the ordering —
  works on any list of `ActionItem`.
- `create_item_row()` (line 438) is **generic**. It reads `self.scroll_frame`,
  `self.palette`, `self.resizer`, `self.db_manager` and the colour caches, and
  nothing that is about today's date.
- Every row behaviour the request asks for already exists and is generic:
  `edit_item` (778), `complete_item` (694), `start_timer` (765), the three
  inline editors (785, 802, 819), `push_item` (842).
- `get_todays_items()` (line 348) is the **only** date filter.

What is genuinely Today-only: the toolbar built inline in `__init__`
(lines 83-148: title, search, Expand/Collapse, Top 3, + New Item, Refresh), the
pin-drag and Top-3 sort keys, and the confetti. 21 lines reference
`today_pin_rank` / `show_top_3_only` / `_pin_drag`.

The obstacle: `TodayScreen.__init__` (lines 45-164) builds the toolbar inline
and ends by calling `load_items()`. There is no `create_ui()` seam, so a
subclass cannot replace the toolbar without overriding the whole constructor.
AWA-M6 cuts exactly that seam and nothing else.

---

## 2. Decisions this spec makes

Each is a point where the request admits more than one reading. They are
decided here so implementation does not have to guess; each is cheap to reverse
before code is written.

**D1 — the tab is called "APE Week Assignment", and so is the screen header.**
The request names the tab. Leaving the in-screen header at "APE Weekly
Assignment" would put two different names on one screen, which is the same
class of drift the tab rename is fixing. Both change. (AWA-M1.1, AWA-M1.2.)

**D2 — the new tab is called "APE Week Actions".** It sits sixth, after "APE
Week Assignment". Reversible in one string.

**D3 — "linked to the week tactic" means `weekly_tactic_id` OR `parent_id`.**
Evidence in §1.3. Reading one column would show an empty panel on one of the
two live databases. The union is the only reading that is right on both.

**D4 — the left panel lists *all* Weekly Tactics for the week, not only
APE-linked ones.** `vps_manager.get_weekly_action_items` takes `ape_only`, and
the APE Week Assignment screen passes `True`. A tactic with no APE is still a
tactic with Action Items hanging off it, and hiding it would make its items
unreachable from this tab with nothing on screen to say so (P2). This tab
passes `ape_only=False` and shows the count. This is a deliberate divergence
from the sibling tab and is called out in the handoff note.

**D5 — "Add Action Item" prompts for a title, creates the linked row, then
opens the full editor on it.** `ItemEditorDialog.__init__` (line 70) has no
seed parameter for a tactic link, so a new unsaved item cannot be pre-linked
inside the editor. Creating first and editing second needs no change to the
editor. The alternative — adding a `weekly_tactic_id` seed parameter to
`ItemEditorDialog` — is cleaner but touches a dialog used by nine screens, and
is not worth that blast radius for this feature. An empty title cancels and
creates nothing.

**D6 — the right panel shows the tactic's children whatever their completion
date.** Today's completed section is "completed today". Filtered by tactic
rather than by date, that filter has no meaning; the panel shows open and
completed children of the tactic, and the completed section keeps its existing
time total.

---

## 3. Acceptance criteria → tests

Every criterion names the automated test that verifies it. New tests go in
`tests/test_ape_week_actions.py` unless stated otherwise.

### AWA-M1 — the tab is renamed

| ID | Criterion | Test |
|---|---|---|
| AWA-M1.1 | The hub's fifth nav button reads exactly `APE Week Assignment`. | `test_awam11_hub_nav_label_is_week_assignment` |
| AWA-M1.2 | `WeeklyItemsScreen`'s header label reads exactly `APE Week Assignment`. | `test_awam12_screen_header_matches_the_tab` |
| AWA-M1.3 | No user-visible string in `vision_planning_hub.py` or `weekly_items.py` contains `APE Weekly`. Parsed from the AST's string constants, asserted as an exact count of 0. | `test_awam13_no_ape_weekly_label_remains` |
| AWA-M1.4 | The nav key `ape_weekly` and the `mapping` entry still agree, whatever the label says — the rename does not break the route. | `test_awam14_every_nav_key_has_a_screen` |

### AWA-M2 — one predicate for "linked to this weekly tactic"

| ID | Criterion | Test |
|---|---|---|
| AWA-M2.1 | A single helper returns the Action Items linked to a tactic id, matching `weekly_tactic_id = ?` **OR** (`weekly_tactic_id IS NULL` **AND** `parent_id = ?`). Given a tactic with one child linked each way, it returns both. (Corrected after the sweep: the row said a plain `OR`. An item can hold a *different* tactic in each column — add from APE Week Assignment, then pick another tactic in the editor — and a plain `OR` listed that one item under **both** tactics. `weekly_tactic_id` wins when set; a `parent_id`-only child stays reachable, which is why the union exists. **Extended again after the re-sweep of this batch's fix commits:** the resolution must still hold after the app is restarted. `migrate_parent_links_to_weekly_tactic` runs from `Database.initialize_schema` on every `DatabaseManager` construction and overwrote an explicit `weekly_tactic_id` with the `parent_id` one, so the rule above was reversed at the next launch and the invariant repair then moved the item's dates. The criterion is therefore asserted across a real reopen, not only in-session — the dirty-state case (P8) the first round's test could not reach.) | `test_awam21_both_link_shapes_are_returned`, `test_awam23_an_item_is_listed_under_one_tactic_only`, `tests/test_weekly_tactic_link_migration.py::test_awam23_an_explicit_tactic_survives_a_reopen` |
| AWA-M2.2 | It never returns a row with `item_type = 'week'`: a tactic is not its own child, and two tactics in one week must not nest. | `test_awam22_week_rows_are_never_children` |
| AWA-M2.3 | It is the only place the linkage is expressed. AST walk over **all** of `src/getmoredone`: exactly **one** string constant, in `weekly_tactic.py`, is predicate-shaped — names `weekly_tactic_id` and reaches `parent_id = ?` from an `OR`. Exact count per file, not a floor. (Corrected twice. At implementation, the row said "screens/: exactly one", written before §4 settled the helper into `vps_manager`. After the sweep, because scanning only `screens/` and `vps_manager.py` is what let `weekly_tactic_maintenance._child_count` hold a second, drifted copy with nothing red — the high finding of this batch. Matched on shape rather than on the two names appearing together, because `db_manager`'s INSERT column list and UPDATE SET list both name both columns and neither expresses this predicate. **Narrowed in wording after the re-sweep:** the matcher was case-sensitive, required `parent_id` to be the second branch and matched only `= ?`, so the row's previous claim that *any* reintroduced copy fails the test was wrong. It is now case-insensitive, matches either branch order, and matches `= ?`, `= :name` and `IN (?)`. It still cannot see a copy split across two `ast.Constant` nodes, nor one expressed as a JOIN rather than an `OR` — of which `weekly_tactic_maintenance`'s invariant repair is one, with no `parent_id` arm at all. So the criterion is one home for *this SQL form*, not one definition of "child" everywhere; the latter is AWA-A1.) | `test_awam23_one_home_for_the_link_predicate` |
| AWA-M2.4 | A row linked by `parent_id` to a **non-week** parent (ordinary subtask nesting) is *not* returned for that parent's tactic. | `test_awam24_ordinary_subtasks_are_not_tactic_children` |
| AWA-M2.5 | Dirty-state (P8): a link that outlived the row it points at is not returned, and the call does not raise. (Corrected at implementation: an ordinary delete cannot produce that state — both link columns are `REFERENCES action_items(id) ON DELETE SET NULL` and the connection runs with `PRAGMA foreign_keys = ON`. The test seeds the link with foreign keys off, the way an older build or a restored backup leaves it.) | `test_awam25_orphaned_child_is_not_returned` |

### AWA-M3 — the new tab exists and is reachable

| ID | Criterion | Test |
|---|---|---|
| AWA-M3.1 | The hub has a sixth nav button reading exactly `APE Week Actions`, mapped to key `ape_week_actions`. | `test_awam31_hub_has_the_week_actions_tab` |
| AWA-M3.2 | `mapping["ape_week_actions"]` resolves to the new screen class. | `test_awam32_week_actions_key_resolves` |
| AWA-M3.3 | The new screen constructs on a withdrawn root against a `tmp_path` database and is destroyed cleanly — no mapped window, so `tests/test_ci_contract.py`'s mapped-window count is unchanged. | `test_awam33_screen_constructs_withdrawn` |

### AWA-M4 — left panel: Weekly Tactics for the selected week

| ID | Criterion | Test |
|---|---|---|
| AWA-M4.1 | The week picker defaults to the current week, computed by the shared helper, not by local arithmetic. | `test_awam41_week_defaults_to_current_week` |
| AWA-M4.2 | The left panel lists the Weekly Tactics whose `start_date` is the selected week. | `test_awam42_left_panel_lists_the_weeks_tactics` |
| AWA-M4.3 | It calls `get_weekly_action_items(..., ape_only=False)`, and the panel header states the count (D4, P2). | `test_awam43_no_tactic_is_silently_dropped` |
| AWA-M4.4 | Selecting a tactic sets the selection and reloads the right panel exactly once. | `test_awam44_selecting_a_tactic_reloads_the_right_panel` |
| AWA-M4.5 | Changing the week clears the selection, so the right panel cannot keep showing a tactic from another week. | `test_awam45_changing_week_clears_the_selection` |

### AWA-M5 — the right panel behaves like Today

| ID | Criterion | Test |
|---|---|---|
| AWA-M5.1 | The right panel class is a subclass of `TodayScreen`. | `test_awam51_right_panel_subclasses_today` |
| AWA-M5.2 | Its item query is the AWA-M2 helper, scoped to the selected tactic — it overrides `get_todays_items` and calls no date filter. | `test_awam52_right_panel_queries_by_tactic_not_date` |
| AWA-M5.3 | It inherits Today's row behaviours unchanged: `edit_item`, `complete_item`, `start_timer`, `push_item` and the three inline editors are not redefined on the subclass. | `test_awam53_row_behaviours_are_inherited_not_copied` |
| AWA-M5.4 | `Add Action Item` creates a row with `weekly_tactic_id` set to the selected tactic, `start_date`/`due_date` inside the week, reports what the create's re-file did, and then opens the editor on the new id. An empty title creates nothing. (Added after the sweep: the create re-files by default and records whether it refused a week or built cascade rows; thirteen other screens report that and this one dropped it. The notice has to precede `edit_item`, which opens a modal.) | `test_awam54_add_action_item_links_by_weekly_tactic_id`, `test_awam54b_empty_title_creates_nothing`, `test_awam54c_add_action_item_reports_what_the_refile_did` |
| AWA-M5.5 | Its `ColumnResizer` prefix is **not** `"today"`, so its Title-column width is stored separately and resizing one panel does not move the other. | `test_awam55_column_prefix_is_its_own` |
| AWA-M5.6 | With a tactic selected and no children, the empty state names the tactic rather than saying "No items for today". | `test_awam56_empty_state_names_the_tactic` |
| AWA-M5.7 | With no tactic selected, the panel shows a prompt and raises nothing. | `test_awam57_no_selection_is_not_an_error` |
| AWA-M5.8 | Completed children show regardless of completion date (D6). Adversarial (P7): a child completed 90 days ago still appears; a child of a *different* tactic completed today does not. | `test_awam58_completed_children_are_not_date_filtered` |

### AWA-M6 — the seam cut into Today, and nothing else

| ID | Criterion | Test |
|---|---|---|
| AWA-M6.1 | `TodayScreen` gains an overridable `_build_toolbar(parent)` holding today's search / Expand / Top 3 / + New Item / Refresh controls, and class attributes `EMPTY_TEXT` and `COLUMN_PREFIX`. | `test_awam61_today_exposes_the_seam` |
| AWA-M6.2 | `TodayScreen`'s own behaviour is unchanged: `COLUMN_PREFIX == "today"`, `EMPTY_TEXT == "No items for today"`, and the toolbar still builds the same six controls in the same order. | `test_awam62_today_toolbar_unchanged` |
| AWA-M6.3 | The existing Today suite passes untouched: `test_today_screen.py`, `test_today_pin.py`, `test_today_pin_drag.py`, `test_today_completed_filter.py`, `test_today_title_col_width.py`. | those five files, run as-is |

### Not code-testable

**One criterion cannot be made a test: "should work like the Today tab".** A
subclass that inherits the row builder is strong evidence, and AWA-M5.3 pins it
by asserting the methods are not redefined — but whether the panel *reads* like
Today on screen (row height, column alignment inside a half-width pane, the
toolbar not crowding) is a judgement.

**Human-review proposal:** after implementation, run the on-screen check the
way the APE period-consistency batch was verified on 2026-11-07 — launch the
app, open the tab, and record in the spec what the window showed, criterion by
criterion. Specifically: the right panel's columns at half width, the Title
column resizing independently of Today's, and a completed child rendering with
the same badge and tint as on Today. Explicitly **not** signed off by a test.

---

## 4. Implementation order

Each step is committable on its own and leaves the suite green.

1. **AWA-M6 — cut the seam in `today.py` first, alone.** Extract
   `_build_toolbar`, add `EMPTY_TEXT` and `COLUMN_PREFIX`, point `load_items`
   at `EMPTY_TEXT` and the resizer at `COLUMN_PREFIX`. Pure refactor, no
   behaviour change. Run the five Today test files before going further. This
   is first because everything downstream depends on it and because it is the
   only step that can break a screen the user uses every day.
2. **AWA-M2 — the link helper.** Add it to `vps_manager` beside
   `get_weekly_action_items`. No UI. Depends on nothing.
3. **Shared week helpers.** Lift `_first_day_of_week`, `_week_start_for` and
   `_build_selectable_week_options` out of `WeeklyItemsScreen` into a shared
   module and re-point the original at it — the same "one home for the rule"
   move the 2026-11-07 APC batch made for the quarter↔month mapping, and for
   the same reason: the new tab is the second caller, and a second copy is how
   the APC defect started. Depends on nothing; `tests/test_weekly_items_week_options.py`
   must stay green.
4. **AWA-M5 — the right panel.** Subclass `TodayScreen`, override
   `get_todays_items`, `EMPTY_TEXT`, `COLUMN_PREFIX` and `_build_toolbar`.
   Depends on 1 and 2.
5. **AWA-M4 — the left panel and the week picker.** Depends on 3 and 4.
6. **AWA-M3 — register the tab in the hub.** Depends on 4 and 5.
7. **AWA-M1 — the rename.** Last, deliberately: it is one string in each of two
   files and touches nothing else, so it cannot be blamed for a failure in
   steps 1-6.
8. **Docs.** Handoff note at `docs/changes/2026-11-07-ape-week-actions.md` from
   `.agents/templates/handoff-note.md`; this spec listed in
   `docs/DOCUMENTATION_INDEX.md`; `docs/USER_GUIDE.md` for the new tab and the
   renamed one; `NOTES.md`; `docs/spec_coverage.md`.

### Fix→test map (highest impact first)

| Change | Test written first | Why it ranks here |
|---|---|---|
| AWA-M2 link predicate | yes | The one decision that is silently wrong on one machine and right on the other. Nothing else on the tab matters if this is wrong. |
| AWA-M6 Today seam | yes | Touches the app's most-used screen. A regression here is felt immediately and by everything. |
| AWA-M5.4 Add Action Item | yes | Writes to the database, and writing the *wrong* link column is how §1.3's split started. |
| AWA-M5.8 completed filter | yes | A silent wrong-filter: the panel looks fine and just omits rows. |
| AWA-M4 left panel | after | Read-only; a wrong list is visible at once. |
| AWA-M1 rename | after | A label. Wrong is obvious. |

---

## 5. Risks

- **The Today seam is the real risk in this batch.** `today.py` is 886 lines
  with five test files and is the screen the user opens first every day. The
  mitigation is that step 1 changes no behaviour and is verified by the
  existing suite before any new code depends on it. If `_build_toolbar` cannot
  be extracted without moving behaviour, stop and report rather than widening
  the refactor.
- **`parent_id` is overloaded.** It means both "ordinary subtask" and "child of
  a week tactic", depending on which code wrote it. AWA-M2.4 pins the
  distinction, but any future change to `parent_id` semantics will touch this
  tab.
- **Two panels in one half-width pane.** The right panel inherits Today's
  column layout, which was laid out for a full-width screen. The columns may
  need `responsive_column_chars` to be given the pane's width rather than the
  window's. This is a layout question that only the on-screen check settles —
  flagged in §3, "Not code-testable".
- **`ItemEditorDialog` is used by nine screens.** D5 deliberately avoids
  changing it. If implementation finds it must change, that is a scope change:
  stop and report.

---

## 6. Status report

Implemented 2026-11-07. Every criterion is `done` except AWA-M6.3, which is
`done` by running the five files unchanged, and the one criterion §3 flagged as
not code-testable, which is `not done` and needs the user at a keyboard — the
checklist for it is at the end of this section.

| ID | Status | Proof |
|---|---|---|
| AWA-M1.1 | done | `screens/vision_planning_hub.py:58` — `test_awam11_and_m31_hub_nav_labels` asserts all six labels in order |
| AWA-M1.2 | done | `screens/weekly_items.py:72` — `test_awam12_screen_header_matches_the_tab` |
| AWA-M1.3 | done | `test_awam13_no_ape_weekly_label_remains` — zero `APE Weekly` string constants in either file, counted from the AST |
| AWA-M1.4 | done | `test_awam14_and_m32_every_nav_key_opens_its_own_screen` — every key opened, class named |
| AWA-M2.1 | done | `weekly_tactic.LINK_PREDICATE_SQL`, read by `vps_manager.get_action_items_for_weekly_tactic`, and `weekly_tactic_migrations.migrate_parent_links_to_weekly_tactic` keeping an explicit link — `test_awam21_both_link_shapes_are_returned`, `test_awam23_an_item_is_listed_under_one_tactic_only`, `tests/test_weekly_tactic_link_migration.py::test_awam23_an_explicit_tactic_survives_a_reopen` (as corrected in §3, twice) |
| AWA-M2.2 | done | `AND item_type != 'week'` — `test_awam22_week_rows_are_never_children` |
| AWA-M2.3 | done | `weekly_tactic.LINK_PREDICATE_SQL`, read by both SQL callers — `test_awam23_one_home_for_the_link_predicate` and `tests/test_weekly_tactic_dedupe.py::test_awam23_child_count_uses_the_shared_predicate` (as corrected three times in §3 - the scan's scope at implementation, again after the sweep, and the matcher's own reach after the re-sweep) |
| AWA-M2.4 | done | the `is_tactic` guard — `test_awam24_ordinary_subtasks_are_not_tactic_children` |
| AWA-M2.5 | done | `test_awam25_orphaned_child_is_not_returned`, as corrected in §3 |
| AWA-M3.1 | done | `screens/vision_planning_hub.py:59` — `test_awam11_and_m31_hub_nav_labels` |
| AWA-M3.2 | done | `screens/vision_planning_hub.py:96` — `test_awam14_and_m32_every_nav_key_opens_its_own_screen` |
| AWA-M3.3 | done | `test_awam33_screen_constructs_withdrawn`; `tests/test_ci_contract.py`'s mapped-window count is still 22 |
| AWA-M4.1 | done | `WeekActionsScreen.jump_to_current_week` — `test_awam41_week_defaults_to_current_week`, compared against `week_options`, not against arithmetic rewritten in the test | Extended after the sweep: `test_awam41c_week_start_follows_the_first_day_setting` checks the setting is read at all, against an oracle that does not call that helper (a Monday-start week begins on a Monday, a Sunday-start week on a Sunday), and `test_awam41d_an_older_week_stays_in_the_picker` exercises `_existing_week_starts`, whose P2 claim no test reached on this screen.
| AWA-M4.2 | done | `test_awam42_left_panel_lists_the_weeks_tactics` |
| AWA-M4.3 | done | `test_awam43_no_tactic_is_silently_dropped` records the `ape_only` argument the screen actually passed, and asserts the count in both the panel heading and the status line |
| AWA-M4.4 | done | `test_awam44_selecting_a_tactic_reloads_the_right_panel` — one call, recorded |
| AWA-M4.5 | done | `WeekActionsScreen.load_selected_week` — `test_awam45_changing_week_clears_the_selection` |
| AWA-M5.1 | done | `test_awam51_right_panel_subclasses_today` |
| AWA-M5.2 | done | `test_awam52_right_panel_queries_by_tactic_not_date` records the helper call and compares the panel's answer against it |
| AWA-M5.3 | done | `test_awam53_row_behaviours_are_inherited_not_copied` — nine behaviours, identity-compared against `TodayScreen`, exact list |
| AWA-M5.4 | done | `WeekTacticActionsPanel.add_action_item`, plus `db_manager.create_action_item` clearing `last_week_collision` so the notice reports this save — `test_awam54_add_action_item_links_by_weekly_tactic_id`, `test_awam54b_empty_title_creates_nothing`, `test_awam54c_add_action_item_reports_what_the_refile_did`, `test_awam54d_a_clean_create_does_not_report_an_old_collision` (as corrected in §3) |
| AWA-M5.5 | done | `COLUMN_PREFIX = "week_actions"` plus `AppSettings.week_actions_col_widths` — `test_awam55_column_prefix_is_its_own` |
| AWA-M5.6 | done | `set_tactic` — `test_awam56_empty_state_names_the_tactic` |
| AWA-M5.7 | done | `test_awam57_no_selection_is_not_an_error` |
| AWA-M5.8 | done | `test_awam58_completed_children_are_not_date_filtered` — the 90-day-old child shows, another tactic's child completed today does not |
| AWA-M6.1 | done | `screens/today.py:55-57` — `test_awam61_today_exposes_the_seam` |
| AWA-M6.2 | done | `test_awam62_today_column_prefix_and_empty_text_are_unchanged`, `test_awam62_today_toolbar_unchanged` — seven widgets, exact columns and order |
| AWA-M6.3 | done | the five Today files run unchanged: 26 passed, 1 skipped (the skip is the mapped-window geometry test, skipped by `GETMOREDONE_NO_MAPPED_WINDOWS`) |
| "works like the Today tab" on screen | **not done** | needs a human at the screen; checklist below |

### Mutation table

Every new test was mutated with the **verbatim** original line, run alone,
confirmed red, and the file restored and compared by sha256. 28 mutations, 28
red, 28 byte-identical restores. The two fix rounds add 10 and 7 more, all red,
all restores identical; both are accounted for in their own sections below.

Two mutations did not come back red on the first pass, and both were real:

1. `test_awam25_orphaned_child_is_not_returned` stayed **green** with the
   helper's guard removed. Both link columns carry `ON DELETE SET NULL` and
   the connection runs with foreign keys on, so the ordinary `DELETE` the test
   used cleared the link by itself: the test asserted an outcome the schema
   guaranteed and verified nothing about the helper. Rewritten to seed the
   dangling link with foreign keys off, and it now asserts the dirty state is
   dirty before asserting the helper's answer, so it cannot go vacuous again.
   Which of the three applied: **(c) the test was vacuous.**
2. `test_awam56_empty_state_names_the_tactic`'s mutation did not apply — the
   escaping in the mutation script, not the test. Re-run against the real
   characters, it is red.

### The sweep, and what it found in this batch

Three passes over the AWA range, per the project's sweep budget: `learning-qa`
(failure patterns), a cold correctness pass, and a cold test-quality +
security pass. One high and five medium were fixed in-loop with tests
(`8a324cb` for the code, `ac22a78` for the tests); one medium was dismissed as
a false positive; four below-medium went to `BACKLOG.md` as AWA-S1 to AWA-S4.
The security pass reported nothing — both new queries are parameterised and
the tab adds no subprocess, no deserialisation and no path from user text.

**High — the predicate had two homes, and the guard test could not see the
second.** AWA-M2.3 says the union predicate is written in exactly one place,
and `test_awam23_one_home_for_the_link_predicate` asserted it. The test
scanned `screens/` and `vps_manager.py`; the second copy was in
`weekly_tactic_maintenance._child_count`, outside both. The two had already
drifted — `_child_count` lacked the `item_type != 'week'` exclusion — and
`_child_count` feeds `_choose_survivor`, so a dedupe chose which duplicate
tactic to **delete** by counting a nested tactic as a child, a definition the
panel never uses. This is §7's AWA-A3, recorded in this batch as a Low
refactor; by the time the sweep reached it, it was deciding which rows a
delete kept. Both readers now share `weekly_tactic.LINK_PREDICATE_SQL`, and
the scan covers all of `src/getmoredone` with an exact count per file.

**Medium — an item with both link columns set was listed under two tactics.**
§1.3 records that both columns carry the link. It did not consider an item
holding a *different* tactic in each, which is reachable without leaving
supported UI: add from APE Week Assignment, whose button writes `parent_id`
(AWA-A1), then pick another Weekly Tactic in the editor, which sets
`weekly_tactic_id` and by design leaves `parent_id` alone. A plain `OR`
matched both, so two panels each claimed the row and the dedupe counted it
twice. `weekly_tactic_id` now wins when set — the tactic last chosen — and a
`parent_id`-only child stays reachable, which is why the union exists.

**Medium — AWA-M5.4 swallowed the create's cascade report.**
`create_action_item` re-files into the Weekly Tactic unless told not to, and
records on the manager whether it refused a week or built cascade rows.
Thirteen screen modules report that with `notify_weekly_tactic_changes`;
`week_actions.add_action_item` did not, so an item saved un-re-filed looked
identical to one that was filed. Reachable *because* of D4/AWA-M4.3, which
lists tactics whose Annual Plan Element has been detached — the re-file
refuses exactly those. The call goes before `edit_item`, which opens a modal;
a notice raised after it stacks behind the editor.

**Four medium test-quality findings, all tests that held while what they name
was broken.** `assert "2" in status_label.cget("text")` could not fail — the
text ends in an ISO date in 2026, so every value it can take contains a "2".
The AWA-M5.3 seam check used a set *intersection*, which proves four names are
present but cannot see a fifth override appear, which is the drift the
criterion is about; it is now a set difference by exact list. Two AWA-M4 paths
had no test at all: every week-screen test built it with `first_day=0` and the
oracle called the same production helper, so `_first_day_of_week` could have
ignored the user's setting entirely; and `_existing_week_starts`, whose P2
claim is that an older week stays reachable, was never exercised on this
screen because both tactics in `test_awam42` fall inside the four generated
weeks.

**One medium dismissed, with the reason.** The pass reported that ten tests
read the machine's own settings file through `AppSettings.load()` in
`TodayScreen.__init__`. They do not: `conftest.py:296` `_isolate_user_settings`
is a session-scoped autouse fixture that redirects `get_settings_path` to a
`tmp_path_factory` file for the whole run, in both import spellings of the
module, and restores it after; `tests/test_settings_isolation.py` covers it.
The second half is wrong too — the `ColumnResizer` is built with
`self.settings`, a real `AppSettings`, never with the app stub's `MagicMock`,
so no column width was being clamped. A redundant fixture and a test for it
were written before `conftest.py` was read, and both were reverted.

**Fix mutations:** 10, each the verbatim original, each run alone, every file
restored and sha256-compared. 10 red. Two of them are the AWA-M5.4 notice in
both directions — removed, and moved after `edit_item` — because the order is
half the fix.

### The re-sweep of this batch's own fix commits

Run because a fix commit is the least-reviewed code in any change — written
last, fastest, and in the most anchored state. Range `3d69956..HEAD` limited to
this batch's files; the Plan / Day Plan session's commits are interleaved and
out of scope. It found **one high that none of the three earlier passes saw**,
which is the whole argument for the pass.

**High — the contract AWA-M2.1 had just documented was reversed at the next
launch.** `migrate_parent_links_to_weekly_tactic` runs from
`Database.initialize_schema` on every `DatabaseManager` construction, and its
`UPDATE action_items SET weekly_tactic_id = ?, parent_id = NULL` fired for
every row whose parent is a week item — including rows that already named a
Weekly Tactic of their own. So for the exact item AWA-M2.1 is about, the next
launch replaced the user's last choice with the older link, nulled `parent_id`
so nothing recorded that it had happened, and let the invariant repair that
runs next in the same migration move the item's dates into the other tactic's
week. Reproduced on a throwaway database: `weekly_tactic_id` B became A and the
dates moved 2026-11-16 → 2026-11-09 with an `inv_repair` history row.

What makes it a high rather than a defect in old code is that the first fix
round *documented and tested* the opposite rule, in a test that passes only
because it never reopens the database. The fix keeps an explicit link, still
drops the stale `parent_id` so the migration stays idempotent, and reports the
two outcomes as two numbers (P2). The test reopens the file.

**Medium — a create reported a collision from earlier in the session.**
`last_week_collision` is cleared at the start of every *update* save, with a
comment saying why: the manager lives for the session, so a flag that is only
ever set reads as permanently true after the first clash. The create path only
ever set it, which was harmless until AWA-M5.4 added the first reader — and
that reader then showed "Week Already Taken" after every Add for the rest of
the session, for items that saved fine. `create_action_item` now clears it too.

**Medium — AWA-M2.3's guard claimed to catch copies it could not see.** Its
docstring said a reintroduced copy anywhere under `src/` fails the test. The
pattern was case-sensitive, required `parent_id` to be the second branch, and
matched only `= ?`. Widened, and the docstring now states its limits; §3 has
the detail. Two of the fix round's mutations plant a verbatim second copy —
once as it was written, once with the branches reversed and the keywords
lower-case — to prove the two forms the new pattern claims.

**Medium — `chip_table`'s docstring described the consolidation as done.**
Nothing imports the module: it is UPD-M3 of the unified-panel spec, and the
five renderers move onto it in UPD-M4 to UPD-M7. Rule 13 applies to a module
docstring as much as to a status line, so it now opens by saying nothing uses
it yet.

**One low raised to medium, and fixed.** The fallback chip measured a colour it
cannot parse: `semantic_colors()["surface_subtle"]` is a *named* Tk colour on 7
of the 10 themes (`gray16` in dark mode), `pick_text_color` cannot read it and
returned black, so a chip with no lineage colour drew black text on a
near-black pill. The reviewer rated it low. It is new code rendering unreadable
text on exactly the path the fallback exists for, so it was raised. The
fallback now leaves `text_color` unset and inherits the theme's own, which is
readable on the theme's own surface by construction.

**One low fixed in-loop against the budget, with the reason.**
`weekly_tactic_id IS NULL` was not the test `tactic_of` applies, so a row
holding `''` matched neither arm and vanished from the panel and from
`_child_count`. Fixed with `COALESCE`. The edit site is the same comment block
as the medium above it, and splitting them would have left a corrected comment
describing SQL that still had the old shape.

The same edit added outer parentheses to the constant, on the finding's claim
that a consumer writing `WHERE x OR {...}` would silently get the wrong rows
without them. **That half was not a defect**, and the third pass's mutation
gate is what established it: the test written for the claim stayed *green* when
the parentheses were removed. Checked directly afterwards on an in-memory
table — `WHERE x OR {p}`, `WHERE {p} OR x` and `WHERE x AND {p}` return
identical rows either way, because `AND` binds tighter than `OR` in SQL and the
predicate's trailing clause is an `AND`. The parentheses are kept, because
saying the grouping out loud beats relying on precedence, but no test asserts
them and nothing should claim they fixed anything. `a97b402`'s message
overstates them; the correction is here, in `BACKLOG.md` and in the
predicate's own comment, rather than quietly dropped.

The same pass corrected the predicate's own comment, which claimed to ask "the
same question as `tactic_of`". It does not, and should not: it is deliberately
wider, because a `parent_id`-only child must be listed somewhere rather than
stranded, while WT-INV6 turns on `tactic_of` and must not move an item that
never opted in. AWA-A1 is named there as the consequence.

**Four below-medium** are `AWA-S5` to `AWA-S8` in `BACKLOG.md`: the chip text
clamped to the column rather than to the pill, five unenforced `ChipTable`
lifecycle assumptions, `register_row` accepting bad and over-long tuples
silently, and the AWA-M5.3 override census not seeing a dunder override.

**Fix mutations:** 7, each the verbatim original, each run alone, every file
restored and sha256-compared. 7 red.

### The third cold pass over those fixes

Required by the budget, because the previous pass produced a high. Run on a
different failure family rather than correctness again: the changed migration's
data-path safety against every row shape a real database can hold, and test
quality. **No high.** Two mediums, one low raised to medium, three lows to
`BACKLOG.md` as AWA-S9 to AWA-S11, and one claim retracted.

**Medium — the new count reached the return dict and no log.** The module's own
docstring says nothing here is silent, and `_log_report` says it is the only
surface where the user can see what happened to their rows. It reads `moved`
and gates its line on `if moved:`. A row whose explicit tactic was kept still
had its `parent_id` cleared, and while the two outcomes were one number that
row was logged *because* it was miscounted — so counting it correctly without
logging it made the launch silent about a write to the user's data. That is a
net loss of coverage, which is what P2 is about. `kept_explicit_link` now has
its own line, with the item ids in it.

**Medium — the `''` change shipped untested.** A fix is not done without a
test, and one of this predicate's two consumers decides which duplicate tactic
a dedupe *deletes*. Now covered, and the test is honest about reachability:
with foreign keys on, writing `''` raises `IntegrityError: FOREIGN KEY
constraint failed`, because the column is `REFERENCES action_items(id)`. So it
is a dirty state (P8) seeded with foreign keys off, exactly as AWA-M2.5 is, not
a live write path.

**Low raised to medium — AWA-M2.3's "case-insensitive" claim was empty.** The
widened regex carries `re.IGNORECASE`, but the membership gate in front of it
(`"weekly_tactic_id" in sub.value`) did not, so the flag only widened the half
already pinned. Confirmed by running: a fully upper-case copy did not match.
Raised because a guard stating a guarantee it does not give is the same defect
this batch already rated medium one pass earlier. Both halves are lower-cased
now, and a mutation plants a shouted copy to prove it.

**One claim retracted.** The parenthesisation half of the previous round's
in-loop low was not a defect; the paragraph above has the measurement.

**Two lows corrected rather than filed**, because both were false claims in
docstrings written in the same round (rule 13) and the fixes are one deleted
line and one corrected fake: an assertion that the fallback chip's text colour
is not `"#000000"`, which could never fail because the theme value it compares
is a two-element light/dark list; and a seeded `last_week_collision` using
`attempted_start`, a key neither producer in `db_manager` writes nor
`describe_week_collision` reads. That test now asserts the dialog through
`conftest.py`'s `messageboxes` fixture, which is what its name claims.

**Three lows remain** as AWA-S9 to AWA-S11: the invariant repair's "child" is
wider than this predicate's and makes a week-under-week row able to stop the
app opening (pre-existing, and reachability **not** established); the P5 sibling
of the migration fix in `_repoint_children`, left because it is unreachable
within a single run; and the scan's docstring-only exclusion, which a prose
string under `src/` could turn red.

**Fix mutations:** 6, each the verbatim original, each run alone, every file
restored and sha256-compared. 6 red — after a seventh came back **green** and
was removed with its test, which is how the retraction above was found. That is
the gate doing the job it exists for.

**No fourth pass.** The budget takes a further pass only on a high-severity
finding, and this one produced none.

### The on-screen check — for the user, not for a test

§3 flagged one criterion as not code-testable: whether the panel *reads* like
Today inside a half-width pane. It needs the running app. In order:

1. **VSP Plan** in the sidebar. The nav row should show six buttons, the fifth
   reading **APE Week Assignment** and the sixth **APE Week Actions**.
2. Open **APE Week Assignment**. Its own header should read "APE Week
   Assignment" too — it used to read "APE Weekly Assignment" under a tab that
   read "APE Weekly".
3. Open **APE Week Actions**. The Week Start picker should already show this
   week. The left panel heading should read "Weekly Tactics (N)" with N
   matching the rows under it, and the status line should say the same count.
4. Click a tactic. The right panel should fill with its Action Items, with the
   same columns, row height, badges and tints as the Today screen. The heading
   above them should name the tactic.
5. Click a tactic with no items. The empty line should name that tactic, not
   say "No items for today".
6. Drag the right panel's **Title** column divider. Then open the Today screen
   and check its Title column has **not** moved. Come back and check this
   panel kept its own width.
7. **Add Action Item**, type a title, press OK. The editor should open on the
   new item. Close it; the item should be in the list.
8. Press **Add Action Item** again and cancel with an empty title. Nothing
   should be created.
9. Change the week in the picker. The right panel should go back to the
   "Select a Weekly Tactic" prompt rather than keeping the previous week's
   tactic on screen.

What to watch for, since these are the things no test here settles: columns
crowding or wrapping at half width, the toolbar overflowing the pane, and row
heights differing from Today's.

---

## 7. Adjacent issues found, not fixed

Per the standing rule, these were found while reading the surrounding code.
They are **not** fixed by this spec, and none is a prerequisite.

- **AWA-A1 — `weekly_items.py:442` writes the wrong link column.** The existing
  `Add Action Item` button sets `parent_id` and leaves `weekly_tactic_id` NULL,
  against `weekly_tactic_migrations.py:135`, which exists to keep the two
  apart, and against `tactic_id_of` (`weekly_tactic.py:144`), the predicate
  WT-M3.D.1 names as the single authority. That one button is the whole reason
  the demo database's only child is linked by `parent_id`. **Recommendation:**
  fix it in this batch — set both columns on create — because the new tab makes
  the inconsistency user-visible for the first time. It is listed here rather
  than folded into §3 because it is beyond what was asked, and it is the user's
  call. A one-line change plus a test.
- **AWA-A2 — a second "APE Weekly" label in dead code.**
  `screens/vision_planning.py:186` captions a placeholder tab `"APE Weekly"`.
  `VisionPlanningScreen` is reachable only through `app.show_vision_planning`,
  which no sidebar entry calls. Renaming it is harmless; leaving it means a
  grep for "APE Weekly" still hits. **Recommendation:** leave the label, and
  decide separately whether `vision_planning.py` should exist at all — it is a
  whole screen of placeholders behind an unreachable entry point.
- **AWA-A4 — the panel inherits Today's drag-to-top pin, and the pin is
  shared.** `create_item_row` binds the grip to `_start_pin_drag` /
  `_finish_pin_drag` (`today.py:541-542`), which write `action_items`.`today_pin_rank`
  — the same column the Today screen orders by. Inherited unchanged, as
  AWA-M5.3 requires, that means dragging a row to the top of the APE Week
  Actions panel also floats it to the top of Today. Found after
  implementation, by reading the inherited row builder rather than by a test.
  **Recommendation:** decide between suppressing the grip on this panel and
  giving it its own rank column; either is a behaviour change beyond what was
  asked, so neither was made here. Not a defect in anything this batch wrote.
- **AWA-A5 — `tests/test_ci_contract.py` counted session worktrees as
  uncollected test files.** Fixed in this batch rather than recorded, because
  it made the meta suite red and blocked verification: the desktop app's
  per-session worktrees live under `.claude/worktrees/<name>/`, each a full
  checkout with its own `tests/`, and the uncollected-files assertion globbed
  them. `.claude` is now excluded, with the exclusion predicate under test.
  Not caused by this feature; it fires for any worktree session.
- **AWA-A3 — `weekly_tactic_maintenance._child_count` already reads both
  columns** (line 278) while `tactic_of` reads one. The two disagree about
  what a child is. AWA-M2 adds a third reader that matches `_child_count`.
  Consolidating all three onto one helper is the right end state and is larger
  than this feature.

  **Mostly resolved in this batch's sweep** (`8a324cb`), which raised the same
  duplication as a high finding rather than a low refactor — and was right to:
  the two copies had already drifted, and `_child_count` feeds the dedupe that
  deletes a duplicate tactic. The two SQL readers now share
  `weekly_tactic.LINK_PREDICATE_SQL`. What is left is `tactic_of`, which answers
  the object-level question from `weekly_tactic_id` alone because WT-INV6 depends
  on it, and so still returns None for a `parent_id`-only child. That is AWA-A1's
  subject: closing this entry means fixing AWA-A1.

---

## 8. Files this will touch

| File | Change |
|---|---|
| `src/getmoredone/screens/today.py` | AWA-M6 seam only — `_build_toolbar`, `EMPTY_TEXT`, `COLUMN_PREFIX` |
| `src/getmoredone/screens/week_actions.py` | **new** — the tab: splitter, week picker, left tactic list, right panel |
| `src/getmoredone/screens/vision_planning_hub.py` | AWA-M1.1 label, AWA-M3.1 the sixth button and its mapping entry |
| `src/getmoredone/screens/weekly_items.py` | AWA-M1.2 header label; week helpers lifted out |
| `src/getmoredone/week_options.py` | **new** — the shared week helpers (step 3) |
| `src/getmoredone/vps_manager.py` | AWA-M2 the link helper |
| `tests/test_ape_week_actions.py` | **new** — AWA-M1 … AWA-M6 |
| `docs/` + `NOTES.md` | step 8 |

Expect the new screen around 300-380 lines. `codex.md`'s maintainability policy
is to be read before writing it; if it lands over the file-size threshold, the
splitter and the left list separate first.
