# Project status vocabulary, and the Projects right-hand panel

**Date:** 2026-11-16 **Status:** built
**Prefixes:** `SVU` (status vocabulary), `LRP` (layout, right panel)

## 1. Why

The project editor's Status dropdown offered `active`, `pending`,
`completed` — three words typed into the widget, with no `canceled`, while
`ProjectBoardStatus` and the table's `CHECK` constraint were a third and
fourth place the same list was written down. A project that is dropped had
nowhere to go.

The right-hand panel was rebuilt in the same batch because it is the same
screen, and because its status filter needed a definite list to offer.

**The decision this spec records is that the two vocabularies stay apart.** A
*project* can be parked, so it is `active`, `pending`, `canceled` or
`completed`. An *action item* cannot be parked — a task is either open, done,
or dropped — so it stays `open`, `completed`, `canceled`. Nothing about action
items changed here.

## 2. SVU — the project status vocabulary

**SVU-M1.** `ProjectBoardStatus` is `active`, `pending`, `canceled`,
`completed`, and `ProjectBoardStatus.ALL` is that list in that order. The
project editor's Status dropdown reads `ALL` rather than naming its values, so
the dropdown cannot fall behind the vocabulary again.

`Status` (action items) is untouched: `open`, `completed`, `canceled`, with
`Status.ALL` in that order and `Status.DEFAULT_VISIBLE = (open,)`. What it
gained is `ALL` and `DEFAULT_VISIBLE` as named constants, so the panel's
filters and `Validator.validate_action_item` both read the vocabulary instead
of repeating it (global rule 8).

Code: `models.py`, `validation.py`, `screens/project_boards.py`.

**SVU-M2.** `Database._widen_board_status_check` rebuilds `project_boards`
when its `CHECK` does not yet allow `'canceled'` — SQLite cannot alter a
`CHECK` in place.

Four decisions in that rebuild:

- It widens the table's **own** `CREATE TABLE` text from `sqlite_master` by
  regex, not a second hand-written schema — a database old enough to need this
  may carry columns a later migration added, which re-declaring would drop.
- It runs with `PRAGMA foreign_keys = OFF`, restored in a `finally`: the two
  child tables reference `project_boards` `ON DELETE CASCADE`, so dropping it
  with enforcement on would cascade them away.
- It is idempotent, and on a fresh database it does nothing —
  `_run_migrations` runs before the table is created, and its `CREATE TABLE`
  statement already carries the widened constraint.
- It is called from `_run_migrations`, which runs **before**
  `initialize_schema`'s `CREATE INDEX IF NOT EXISTS` statements. That ordering
  is what puts `idx_project_boards_status` and `idx_project_boards_ape` back
  after `DROP TABLE` takes them, so it has its own guard
  (`test_svum2_rebuild_leaves_the_board_indexes_in_place`).

No row's `status` value is rewritten, in any table.

Code: `database.py`.

## 3. LRP — the right-hand panel

- **LRP-A1** — the `Next Step:` meta line is dropped from the detail header.
  The field is untouched: still edited in the project editor, still on each
  tile.
- **LRP-A2** — `Action Items` and the count are one left-justified line:
  `N items`, or `N shown • M hidden` when the filters hold items back.
- **LRP-A3** — Select All loses its label and moves to column 0 of the column
  heading, directly above the row checkboxes. `build_header`'s empty heading
  label over that column is destroyed and replaced, not stacked on, so the two
  widgets cannot fight over the cell's width.
- **LRP-A4** — Project Notes starts collapsed, keeping its header line and
  count. The state lives on the screen, not in settings.
- **LRP-C1** — `Open`, `Completed`, `Canceled` on that same header line,
  left-justified, with `Open` ticked. These are the **action item** statuses:
  the four project words are not offered here, because these boxes filter the
  items on the board, not the board. A row shows when its own status is
  ticked, so unticking all three shows nothing; a status the boxes do not
  cover is shown rather than dropped (P2). The `Completed` box also governs
  the notes list, as the single shared `Show Completed` toggle it replaces
  did.

Code: `screens/project_boards.py`.

## 4. Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| SVU-M1 | The board vocabulary is the four words | `test_svum1_board_vocabulary_is_the_four_words` |
| SVU-M1 | The item vocabulary is unchanged, with no `pending`/`active` | `test_svum1_item_vocabulary_is_unchanged` |
| SVU-M1 | The two vocabularies are deliberately different | `test_svum1_the_two_vocabularies_are_not_the_same` |
| SVU-M1 | A new item is `open` | `test_svum1_a_new_item_is_open` |
| SVU-M1 | The default item filter is `open` alone | `test_svum1_the_default_filter_is_open_alone` |
| SVU-M1 | The validator takes every item status | `test_svum1_validator_accepts_every_item_status` |
| SVU-M1 | The validator rejects a board-only status on an item | `test_svum1_validator_rejects_a_board_only_status_on_an_item` |
| SVU-M1 | The project editor's Status dropdown offers all four | `test_svum1_project_editor_offers_all_four_statuses` |
| SVU-M2 | The board `CHECK` accepts `canceled` after the rebuild | `test_svum2_board_check_accepts_canceled` |
| SVU-M2 | The rebuild keeps every board row | `test_svum2_rebuild_keeps_existing_boards` |
| SVU-M2 | The rebuild leaves item/note status values alone | `test_svum2_rebuild_leaves_item_status_alone` |
| SVU-M2 | The rebuild does not cascade the notes away | `test_svum2_rebuild_keeps_the_notes_linked_to_a_board` |
| SVU-M2 | The rebuild leaves the board indexes in place | `test_svum2_rebuild_leaves_the_board_indexes_in_place` |
| SVU-M2 | Foreign keys are on again afterwards | `test_svum2_foreign_keys_are_on_again_after_the_rebuild` |
| SVU-M2 | A second open changes nothing | `test_svum2_migration_is_idempotent` |
| SVU-M2 | A fresh database needs no rebuild | `test_svum2_a_fresh_database_already_allows_canceled` |
| LRP-A1 | No `Next Step:` in the detail header | `test_lrpa1_next_step_is_gone_from_the_detail_header` |
| LRP-A2 | The count is on the heading's row, to its right, left-stuck | `test_lrpa2_count_sits_on_the_action_items_line` |
| LRP-A2 | The count names the number shown | `test_lrpa2_count_names_the_number_of_visible_items` |
| LRP-A3 | Select All is the unlabelled box in the column header | `test_lrpa3_select_all_is_the_unlabelled_box_in_the_column_header` |
| LRP-A3 | It is in the rows' checkbox column | `test_lrpa3_select_all_sits_in_the_rows_checkbox_column` |
| LRP-A3 | No labelled Select All remains | `test_lrpa3_no_labelled_select_all_remains` |
| LRP-A4 | Notes start collapsed | `test_lrpa4_notes_section_starts_collapsed` |
| LRP-A4 | The toggle opens and closes it | `test_lrpa4_toggle_opens_and_closes_the_notes_section` |
| LRP-A4 | The collapsed header still counts | `test_lrpa4_collapsed_header_still_counts_the_notes` |
| LRP-C1 | Three boxes on the header line, in order, left-justified | `test_lrpc1_three_boxes_on_the_header_line` |
| LRP-C1 | `Open` is the only default | `test_lrpc1_open_is_the_only_default` |
| LRP-C1 | Each box shows its own status | `test_lrpc1_ticking_a_box_shows_that_status` |
| LRP-C1 | Unticking everything shows nothing | `test_lrpc1_unticking_every_box_shows_nothing` |
| LRP-C1 | An unknown status is surfaced | `test_lrpc1_unknown_status_is_shown` |
| LRP-C1 | The Completed box also filters the notes | `test_lrpc1_completed_box_also_filters_the_notes` |

## 5. Known gaps

- **Nothing sets a project to `canceled` from the board list.** The editor's
  dropdown offers it and the `CHECK` accepts it, but the toolbar's one-click
  status buttons are still `Set Active` / `Set Pending` / `Complete`. Filed in
  `BACKLOG.md`.
- **The `Canceled` filter box has nothing to find on most boards** until an
  item is canceled somewhere. `complete_action_item` is the only writer of a
  terminal item status today; a "Cancel" action on an item is follow-up work,
  filed in `BACKLOG.md`.
- **The label reads `Canceled`, one `l`.** That is the stored value and the
  spelling used everywhere else in the code. The request said `Cancelled`.
