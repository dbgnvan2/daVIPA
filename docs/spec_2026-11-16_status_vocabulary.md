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

Five decisions in that rebuild:

- It widens the table's **own** `CREATE TABLE` text from `sqlite_master` by
  regex, not a second hand-written schema — a database old enough to need this
  may carry columns a later migration added, which re-declaring would drop.
- It runs with `PRAGMA foreign_keys = OFF`, restored in a `finally`: the two
  child tables reference `project_boards` `ON DELETE CASCADE`, so dropping it
  with enforcement on would cascade them away.
- It is idempotent, and on a fresh database it does nothing —
  `_run_migrations` runs before the table is created, and its `CREATE TABLE`
  statement already carries the widened constraint.
- Its `finally` rolls back before restoring `PRAGMA foreign_keys = ON`.
  The `INSERT` opens a transaction, and the pragma is silently ignored while
  one is open, so without the rollback a rebuild that raised part-way would
  leave enforcement off for the life of the connection and the next board
  delete would orphan its items and notes instead of cascading them.
- A table whose `status` column was added by `ALTER TABLE ... ADD COLUMN`
  carries no `CHECK` at all. That is a normal state with nothing to widen, so
  it returns at debug level; the warning is kept for a `CHECK` that genuinely
  could not be parsed.
- It is called from `_run_migrations`, which runs **before**
  `initialize_schema`'s `CREATE INDEX IF NOT EXISTS` statements. That ordering
  is what puts `idx_project_boards_status` and `idx_project_boards_ape` back
  after `DROP TABLE` takes them, so it has its own guard
  (`test_svum2_rebuild_leaves_the_board_indexes_in_place`).

Two more came out of the sweep over this batch:

- **It is re-entrant.** `CREATE TABLE` is DDL in autocommit, durable the
  moment it runs, so the `finally`'s rollback cannot undo it. A rebuild that
  failed after it -- a write lock held by the packaged app on the `INSERT` --
  left `project_boards_svu` on disk, and `sqlite_master` stores a `CREATE`
  with `IF NOT EXISTS` stripped, so every later launch raised *table
  project_boards_svu already exists* out of `DatabaseManager.__init__` and
  that database could never be opened again. It now drops a leftover scratch
  table first. The early return on a missing `project_boards` is what makes
  that safe: a scratch table is only ever dropped on a launch where the real
  one is present, so it can never be the last copy of the data.
- **It refuses a connection whose commits are deferred.** `PRAGMA
  foreign_keys = OFF` is ignored while a transaction is open, so the rebuild
  depends on a commit it does not own -- and inside
  `DatabaseManager.transaction()` that commit is a no-op, which would leave
  enforcement ON and let `DROP TABLE project_boards` cascade every item and
  note away. No caller does that today (both `initialize_schema` callers run
  at construction); it refuses rather than rest on that holding, reads the
  pragma back before the destructive half, and uses `force_commit` for the two
  commits it owns.

The "already migrated?" question is answered from the matched `CHECK`, not the
whole schema text, so a comment that mentions `'canceled'` cannot make an
un-migrated database skip the rebuild. The pattern is case-insensitive and
tolerates a quoted column name.

No row's `status` value is rewritten, in any table.

Code: `database.py`.

**SVU-M3.** A project can be canceled *and found again*.

`set_project_board_status` gated on a hand-written set of three statuses, so it
silently refused `canceled` once the vocabulary had it, and
`get_project_boards` could only ever return active, pending and completed. The
editor could set the status, so a canceled project left the Projects screen and
nothing brought it back. The gate reads `ProjectBoardStatus.ALL`, the listing
takes `show_canceled`, the toolbar has a `Show Canceled` box beside the other
two, and the screen reports a refusal rather than refreshing over a discarded
`False`.

The three board filters sit **left** of the toolbar's spacer column. Right of
it the new box joins the size controls in the wrapped second row and pushes it
28px past the header's width at the default window (SPC-D10).

Code: `db_manager_project_boards.py`, `screens/project_boards.py`.

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
| SVU-M2 | A failed rebuild still leaves foreign keys on | `test_svum2_a_failed_rebuild_leaves_foreign_keys_on` |
| SVU-M2 | A CHECK-less table is left alone, and does not warn every launch | `test_svum2_a_check_less_table_is_left_alone_without_warning` |
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
| LRP-C1 | The empty-notes message names a control that exists | `test_lrpc1_the_empty_notes_message_names_a_control_that_exists` |
| SVU-M2 | A leftover scratch table does not block the next launch | `test_svum2_a_leftover_scratch_table_does_not_block_the_next_launch` |
| SVU-M2 | A deferred-commit connection is refused | `test_svum2_a_deferred_commit_connection_is_refused` |
| SVU-M2 | A comment mentioning `canceled` does not skip the rebuild | `test_svum2_a_comment_mentioning_canceled_does_not_skip_the_rebuild` |
| SVU-M2 | A lowercase `check(status in ...)` is widened too | `test_svum2_a_lowercase_check_is_widened_too` |
| SVU-M3 | Every status in the vocabulary can be set | `test_svum3_every_board_status_can_be_set` |
| SVU-M3 | An unknown board status is still refused | `test_svum3_an_unknown_board_status_is_refused` |
| SVU-M3 | A canceled board is out of the default list and reachable | `test_svum3_a_canceled_board_is_hidden_but_reachable` |
| SVU-M3 | A refused status change is reported, not redrawn | `test_svum3_a_refused_board_status_is_reported_not_swallowed` |
| SVU-M3 | The toolbar offers Show Canceled | `test_svum3_the_toolbar_offers_show_canceled` |

## 5. Known gaps

- **Nothing sets a project to `canceled` in one click.** The editor's
  dropdown offers it, the `CHECK` accepts it and `Show Canceled` finds it
  again, but the toolbar's one-click status buttons are still `Set Active` /
  `Set Pending` / `Complete`. Filed in `BACKLOG.md`.
- **A `status` CHECK this cannot parse is left in place with a log line.**
  That database then rejects `canceled`, and the failure surfaces later as an
  unhandled `IntegrityError` from the editor rather than at startup. Only a
  hand-edited database reaches it -- no such shape has ever shipped -- so it is
  filed as `SVU-A3` rather than fixed here.
- **The pragma read-back before the destructive half has no test**, by
  construction: its one reachable trigger is refused earlier, and any other
  connection would still roll back in the `finally`, so a guard could only ever
  pass. The reason is recorded at the branch.
- **The `Canceled` filter box has nothing to find on most boards** until an
  item is canceled somewhere. `complete_action_item` is the only writer of a
  terminal item status today; a "Cancel" action on an item is follow-up work,
  filed in `BACKLOG.md`.
- **The label reads `Canceled`, one `l`.** That is the stored value and the
  spelling used everywhere else in the code. The request said `Cancelled`.
