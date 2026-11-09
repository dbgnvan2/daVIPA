# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: weekly-tactic-as-parent (WTP-M1 – WTP-M6)

## Summary

A Weekly Tactic is now the parent of the Action Items linked to it, in every
reader of parenthood the app has. Spec and per-criterion status:
`docs/spec_2026-11-08_weekly_tactic_as_parent.md`. All 41 criteria are `done`,
with two human-review items outstanding under §6's "not code-testable"
heading. Corrected 2026-11-09 by the cold pass over the SST batch: this
sentence gave the count as 38 and said nothing about the two outstanding
items. The spec's §3 rows have never numbered fewer than 41; count them with
`grep -cE '^\| *\*{0,2}WTP-M[0-9.]+' docs/spec_2026-11-08_weekly_tactic_as_parent.md`.

Storage did not change. The link stays in `action_items.weekly_tactic_id`,
because `weekly_tactic_migrations._move_week_links_off_parent_id` nulls
`parent_id` for week parents on every launch — writing both columns would be
undone at the next start. The tactic is the parent because one new predicate
says so and every reader asks it:

- **WTP-M1** `weekly_tactic.parent_of` — `parent_id` when set, else the
  `weekly_tactic_id`, and `None` for a week row, which is a root. `tactic_of`
  is untouched, so WT-INV6 still turns on one column and the re-filing cascade
  touches no new rows.
- **WTP-M2** `get_children` answers for a tactic from `LINK_PREDICATE_SQL`,
  narrowed so an item that is both a subtask and week-filed appears once, under
  its subtask parent. `get_subtree` inherits it.
- **WTP-M3** `get_root_items` stops listing week-filed items. The Hierarchical
  screen needed no change: it reads both functions, so the tree nests and the
  `(N sub)` count fills in by itself.
- **WTP-M4** The Item Editor's `Parent:` line and the Hierarchy dialog's
  `PARENT ITEM` come from `parent_of`. `view_parent_item` — dead code since the
  hierarchy work — is bound to a new **View Parent** button, which the
  ordinary `parent_id` case gains too.
- **WTP-M5** The Item Editor's "has N child items" guard now fires for a
  tactic; `delete_weekly_action_item` deletes what `get_children` calls a
  child, down through a week-filed item's own subtasks; and the VSP screen's
  confirmation names the count, because that is the one click that destroys a
  week's work.
- **WTP-M6** Completing a tactic with open children asks first, naming the
  count, and does not cascade either way. Both tactic panels show `n/m` in a
  Done column, from `count_open_children_for_weekly_tactic` — one home for the
  number, so two panels cannot disagree about one week.

### Three faults found while implementing, all fixed here

1. `ShowRelatedDialog.refresh` held a **second** reader of parenthood: the
   "no related items" branch still asked about `current_item.parent_id`, so a
   week-filed item with no children of its own rendered "No related items
   found" directly beneath the `PARENT ITEM` section just drawn for it. Found
   by the WTP-M4.5 test.
2. `delete_weekly_action_item` ran its `parent_id` delete **before** testing
   `item_type`, so passing an ordinary item's id deleted that item's subtasks
   and then returned `False`, reporting that nothing had been deleted.
   Pre-existing and latent — `weekly_items.py` only ever passes a row from the
   weekly list — and guarded now that this delete is wider.
3. `test_wtpm32_dangling_link_stays_a_root` was **vacuous**, and the spec's
   justification for the guard it covers was **wrong**. See Risks below.

## Files changed

- `src/getmoredone/weekly_tactic.py` — `parent_of`
- `src/getmoredone/db_manager.py` — `get_children`, `get_root_items`
- `src/getmoredone/screens/item_editor.py` — parent line, View Parent binding,
  `_confirm_tactic_completion`
- `src/getmoredone/screens/item_editor_dialogs.py` — `ShowRelatedDialog.refresh`
- `src/getmoredone/vps_manager.py` — `delete_weekly_action_item`,
  `children_to_delete_with_weekly_tactic`,
  `count_open_children_for_weekly_tactic`
- `src/getmoredone/screens/weekly_items.py` — the delete confirmation, the Done
  column on the APE Week Assignment right panel
- `src/getmoredone/screens/week_actions.py` — the Done column on the tactic list
- `src/getmoredone/screens/chip_table.py` — `WEEK_ASSIGNMENT_RIGHT_COLUMNS`,
  and a `progress` column on `WEEK_ACTIONS_LEFT_COLUMNS`
- `tests/test_weekly_tactic_parent.py` — **new**, 41 tests
- `tests/test_unified_panel_design.py` — five column-set assertions updated for
  the new column, and the APE Week Assignment double given the two methods the
  screen now reads
- `tests/test_vps_hub_crud.py` — the delete test extended for both link shapes
- `tests/test_ape_week_actions.py` — `db_manager` added as the fourth caller of
  `LINK_PREDICATE_SQL`
- `docs/spec_2026-11-08_weekly_tactic_as_parent.md` — §6 status report, and
  three corrections
- `docs/USER_GUIDE.md`, `docs/DOCUMENTATION_INDEX.md`, `BACKLOG.md`

`src/` and `tests/` are in separate commits, so the ratio stays visible in
`git log --stat`.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_weekly_tactic_parent.py -q`
- Result: PASS — 41 tests

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_weekly_tactic_parent.py tests/test_unified_panel_design.py tests/test_ape_week_actions.py tests/test_vps_hub_crud.py tests/test_item_editor_weekly_tactic_ui.py tests/test_weekly_tactic_schema.py tests/test_ci_contract.py -q`
- Result: PASS — 273 passed, 1 skipped (the CI-only display test). The mapped
  window count is unchanged at 22: every new UI test uses a withdrawn root or
  drives the method on a stub.

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest tests/test_weekly_tactic_*.py tests/test_item_editor*.py tests/test_vps_hub_crud.py tests/test_ape_week_actions.py tests/test_database.py tests/test_ui_presence.py tests/test_unified_panel_design.py -q`
- Result: PASS — 362 tests. Run before the three screen criteria were built.

- Command: mutation gate, two passes, 15 mutations in all (scripts kept at
  `/private/tmp/claude-501/-Users-davemini2--claude-spares-spare-tq70jN/690a53f0-6f22-4cb9-b514-109978af76ed/scratchpad/mutate.py`
  and `.../scratchpad/mutate2.py`)
- Result: PASS — all 15 killed, every file restored byte for byte

| Mutation | Test | Verdict |
|---|---|---|
| drop `get_root_items`' `NOT EXISTS` existence guard | `test_wtpm32_dangling_link_stays_a_root` | red |
| drop `get_children`'s one-place-in-the-tree restriction | `test_wtpm24_sql_and_object_readers_agree` | red |
| drop `parent_of`'s week-row guard | `test_wtpm17_a_week_row_has_no_parent` | red |
| make `tactic_of` read both columns | `test_wtpm16_tactic_of_unchanged` | red |
| empty the cascade's delete list | `test_wtpm53_cascade_covers_both_link_columns` | red |
| drop the non-tactic guard on the cascade | `test_wtpm55_non_tactic_id_deletes_nothing` | red |
| make the Hierarchy dialog read `parent_id` | `test_wtpm45_hierarchy_dialog_shows_the_tactic_as_parent` | red |
| make `_confirm_tactic_completion` always allow | `test_wtpm61_completing_a_tactic_with_open_children_asks` | red |
| restore the old "and related action items" wording | `test_wtpm52_confirmation_names_the_child_count` | red |
| make the empty-week branch say "0 Action Items" | `test_wtpm52_confirmation_says_so_when_nothing_is_filed` | red |
| drop the singular | `test_wtpm52_one_item_is_singular` | red |
| blank the Done cell on the week assignment row | `test_wtpm64_week_assignment_row_shows_progress` | red |
| drop the dash for an empty week | `test_wtpm64_a_tactic_with_nothing_under_it_shows_a_dash` | red |
| blank the Done cell on the week actions list | `test_wtpm65_week_actions_list_shows_progress` | red |
| drop the `progress` column from the set | `test_updm51_right_panel_has_the_actions_column` | red |

**Not run:** the full suite. Other sessions were writing in this checkout for
most of the batch, so runs were kept to the files this change touches; CI runs
the whole thing on push.

**Not verified in the running app.** The nesting, the indent, the `(N sub)`
count, the parent line, the View Parent button, the two Done columns and the
delete confirmation are all asserted by tests, but nobody has looked at any of
it on screen with the real database. Checklist under "Next agent actions".

## Risks / Known gaps

### The spec's justification for WTP-D6 was wrong, and is corrected

The spec claimed a tactic delete left its week-filed items "with a link to a
row that is gone", 49 of them on the main database, and that `get_root_items`'
existence guard was load-bearing for that state. **It is not.**
`action_items.weekly_tactic_id` is `REFERENCES action_items(id) ON DELETE SET
NULL` and `database.py:129` sets `PRAGMA foreign_keys = ON`, so deleting a
tactic *nulls* the column. Counted on 2026-11-08 against the real database:
939 items, 25 week rows, 49 linked by `weekly_tactic_id`, 0 linked by
`parent_id` to a week row, and **no** link of either kind that fails to
resolve.

What the old behaviour actually did is still worth the fix: a week-filed item
survived the delete as an unparented root item, with no record of the week it
had been filed under.

The guard is kept — the pragma is per connection, so an unresolvable value is
reachable from a client that does not set it, and the cost is one `NOT EXISTS`
against hiding a row. Its test now seeds the state with the pragma off. The
earlier version deleted the tactic with foreign keys on and passed for a reason
it was not about; it stayed green with the guard removed. The mutation gate is
what found it.

### Three criteria were built late, after the files came free

`screens/weekly_items.py` and `screens/week_actions.py` carried 327
uncommitted lines from the **APE Weekly/Month record display issues** session
for most of the batch, so WTP-M5.2, WTP-M6.4's rendering and WTP-M6.5 were
filed in `BACKLOG.md` rather than built. That session then committed, both
files came free, and all three were built. The backlog entries are withdrawn.

Worth knowing for the review: those three are the **least-reviewed** code in
the change — written last, against files that had just moved under them.

### Two unplanned changes the criteria forced

- **A new column set.** WTP-M6.4 and M6.5 say the count is on the row, and both
  panels are chip tables, so the count is a column. `APE_RIGHT_COLUMNS` is
  shared by three right panels and only one of them lists Weekly Tactics, so
  the APE Week Assignment panel took `WEEK_ASSIGNMENT_RIGHT_COLUMNS` of its
  own rather than giving APE Quarter and APE Month a column that could only
  ever read `—`.
- **Five assertions in `tests/test_unified_panel_design.py`** pin those two
  column sets exactly — headings and pixel widths — and were updated. Reason on
  the record, per the test rule: **(b) the behaviour changed intentionally**.
  Each is still an exact pin, not a loosened one.

### Other

- **One criterion was added during implementation.** WTP-M1.7 — a week row has
  no parent — was not in the approved spec. It was needed for `parent_of` and
  `get_children` to agree: `LINK_PREDICATE_SQL` excludes week rows, so had
  `parent_of` called a week row a child the two definitions would have
  disagreed, which is the AWA-A3 failure. Recorded in §6 rather than folded in
  silently.
- **`get_root_items` has one caller** (`hierarchical.py:155`). A later screen
  calling it expecting every parentless row now gets a narrower list.
- **AWA-A1 is still open** and the batch tolerates it: WTP-M2.2 and WTP-M5.3
  both cover the `parent_id`-only shape.
- **AWA-A4 is in the renderer WTP-M6.5 touched.** The Week Actions rows carry
  Today's shared pin; this change added a cell to those rows and did not fix
  it.
- **One adjacent issue filed**, WTP-A1 in `BACKLOG.md`: the shipped-column
  width test enumerates its column sets by hand, so a new set is unchecked
  until someone remembers to add it. `WEEK_ACTIONS_LEFT_COLUMNS` had been
  missing from it since UPD-M6.
- **A cold review pass has not been run.** The project's sweep rules require at
  least one before this is pushed, and the three late criteria are the part
  that most needs it.

## Next agent actions

- Run the cold pass over the whole unpushed range — a different failure family
  from the implementation's own reading, and weighted toward the three screen
  criteria built last.
- On-screen checklist, for the user rather than a test:
  1. Hierarchical screen, status `all`: each Weekly Tactic shows its week's
     items nested one level beneath it, and no item appears twice.
  2. The tactic row shows `(N sub)` matching the number nested under it.
  3. Open a week-filed item: the `Parent:` line names its tactic, and **View
     Parent** opens the tactic's editor.
  4. **Show Related** on that item: `PARENT ITEM` is the tactic. On the tactic:
     `CHILD ITEMS` lists the week's items.
  5. APE Week Assignment, right panel: a Done column reading `n/m`, and `—` on
     a tactic with nothing filed under it. Same on the APE Week Actions tactic
     list, with the same numbers for the same week.
  6. Delete a tactic from the VSP weekly list: the confirmation names the
     count, and reads as a warning rather than a statistic. **No** deletes
     nothing.
  7. Delete the same tactic from its Item Editor: refused, naming the count.
  8. Complete a tactic with items still open: a prompt naming the open count;
     **No** completes nothing.
