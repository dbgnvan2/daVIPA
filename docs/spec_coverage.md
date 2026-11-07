# Spec Coverage — Project Notes feature (2026-06-06)

Plan: [`docs/implementation_plan_2026-06-06_project_notes.md`](implementation_plan_2026-06-06_project_notes.md)

| Spec ID | Description | Implementation | Test | Status |
|---|---|---|---|---|
| M1.A.1 | `ProjectBoardLink.status: str = "open"` | `src/getmoredone/models.py` (class ProjectBoardLink) | `tests/test_project_notes.py::TestM1DataModel::test_project_board_link_has_status_field` | done |
| M1.A.2 | `project_board_links.status TEXT NOT NULL DEFAULT 'open'` on fresh DBs | `src/getmoredone/database.py` (initialize_schema, line ~285) | `tests/test_project_notes.py::TestM1DataModel::test_project_board_links_table_has_status_column` | done |
| M1.A.3 | Idempotent migration adds `status` to existing DBs | `src/getmoredone/database.py` (_run_migrations) | `tests/test_project_notes.py::TestM1DataModel::test_migration_adds_status_to_existing_db` | done |
| M1.A.4 | `add_project_board_link` / `get_project_board_links` round-trip status | `src/getmoredone/db_manager_project_boards.py::add_project_board_link`, `_row_to_project_board_link` AND `src/getmoredone/db_manager.py::_row_to_project_board_link` (kept in sync — see Adjacent Issues) | `tests/test_project_notes.py::TestM1DataModel::test_link_status_roundtrip` | done |
| M2.A.1 | `complete_project_note(link_id)` sets status='completed' | `src/getmoredone/db_manager_project_boards.py::complete_project_note` | `tests/test_project_notes.py::TestM2DBMethods::test_complete_project_note` | done |
| M2.A.2 | `reopen_project_note(link_id)` sets status='open' | `src/getmoredone/db_manager_project_boards.py::reopen_project_note` | `tests/test_project_notes.py::TestM2DBMethods::test_reopen_project_note` | done |
| M2.A.3 | `get_project_board_links(board_id, include_completed=True)` filters by status, orders newest-first | `src/getmoredone/db_manager_project_boards.py::get_project_board_links` | `tests/test_project_notes.py::TestM2DBMethods::test_get_links_filters_by_status`, `::test_get_links_ordered_newest_first` | done |
| M3.A.1 | "Project Notes" bold section header above Action Items | `src/getmoredone/screens/project_boards.py::load_notes` | `tests/test_project_notes.py::TestM3UI::test_project_notes_header_rendered` | done |
| M3.A.2 | Note row: label · status · Open · Complete/Reopen · Unlink (no checkbox, no priority, no dates) | `src/getmoredone/screens/project_boards.py::_render_project_note_row` | `tests/test_project_notes.py::TestM3UI::test_project_note_row_has_status_buttons_no_checkbox`, `::test_completed_note_shows_reopen_not_complete` | done |
| M3.A.3 | Complete/Reopen buttons update status; UI refreshes | `src/getmoredone/screens/project_boards.py::_on_complete_project_note`, `::_on_reopen_project_note` | `tests/test_project_notes.py::TestM3UI::test_complete_button_updates_status`, `::test_reopen_button_updates_status` | done |
| M3.A.4 | Count label: "N note(s) shown" or "N shown • M completed hidden" | `src/getmoredone/screens/project_boards.py::load_notes` (count block) | `tests/test_project_notes.py::TestM3UI::test_notes_count_label` | done |
| M4.A.1 | Shared "Show Completed" checkbox above both sections, default OFF | `src/getmoredone/screens/project_boards.py` (ProjectBoardsScreen.__init__ var; shared_filter frame in _render_detail) | `tests/test_project_notes.py::TestM4SharedShowCompleted::test_show_completed_default_off` | done |
| M4.A.2 | Toggle affects BOTH Notes and Action Items lists | `src/getmoredone/screens/project_boards.py::load_notes` (filter) and `_render_detail` (filter for action items) | `tests/test_project_notes.py::TestM4SharedShowCompleted::test_show_completed_filters_both_lists` | done |
| M4.A.3 | Select All only selects visible items when filter is on | (Pre-existing behavior preserved) `_on_check_all_changed` uses `item_checkbox_vars`, which only contains rendered rows | `tests/test_project_notes.py::TestM4SharedShowCompleted::test_select_all_still_respects_filter`, `tests/test_project_board_bulk_edit.py::TestShowCompletedToggle::test_select_all_respects_filter` | done |
| M5.A.1 | Old "N notes linked to this project." count-only label removed | Replaced by M3 section header in `load_notes` | `tests/test_project_notes.py::TestM5Cleanup::test_old_count_only_label_removed` | done |
| M5.A.2 | Create Note / Link Note / Open Notes toolbar buttons unchanged | No edits to `create_note`, `link_note`, `open_note_picker` | Visual check (also the prior `add_note_to_project` chooser delegates to these handlers, exercised by `tests/test_project_note_chooser.py::TestAddNoteToProjectHandler::*`) | done |
| M6.A.1 | Purpose/Spec/Tests docstrings on new methods | Docstrings present on: `ProjectBoardLink`, `add_project_board_link`, `get_project_board_links`, `complete_project_note`, `reopen_project_note`, `_row_to_project_board_link` (both copies), `load_notes`, `_render_project_note_row`, `_on_complete_project_note`, `_on_reopen_project_note`, `get_project_notes_folder`, `get_project_notes_subfolder_or_default`, `save_obsidian_settings` (updated) | Manual review (diff) | done |
| M6.A.2 | This file (`docs/spec_coverage.md`) exists and lists every spec ID | This file | `tests/test_project_notes.py::TestM6SpecCoverage::test_spec_coverage_doc_mentions_m1_through_m7` | done |
| M7.A.1 | `AppSettings.project_notes_subfolder = "GetMoreDone/Projects"` | `src/getmoredone/app_settings.py` (class AppSettings) | `tests/test_project_notes.py::TestM7Settings::test_settings_has_project_notes_subfolder` | done |
| M7.A.2 | `AppSettings.get_project_notes_folder()` | `src/getmoredone/app_settings.py::get_project_notes_folder` | `tests/test_project_notes.py::TestM7Settings::test_get_project_notes_folder_returns_path` | done |
| M7.A.3 | save/load round-trip the new field | `AppSettings.load` / `save` (auto via dataclass asdict/fields) | `tests/test_project_notes.py::TestM7Settings::test_settings_roundtrip_project_subfolder` | done |
| M7.A.4 | Settings screen "Project Notes Folder" entry, persisted by save_obsidian_settings | `src/getmoredone/screens/settings.py` (create_obsidian_section + save_obsidian_settings) | `tests/test_project_notes.py::TestM7SettingsScreenUI::test_settings_screen_has_project_notes_folder_field` | done |
| M7.A.5 | `CreateNoteDialog` routes `project_board` entity → project folder | `src/getmoredone/screens/item_editor_note_dialogs.py::create_note` (target_subfolder branch) | `tests/test_project_notes.py::TestM7Routing::test_create_note_for_project_writes_to_project_folder`, `::test_create_note_for_action_item_still_uses_generic_folder` | done |
| M7.A.6 | Blank project subfolder falls back to obsidian_notes_subfolder | `get_project_notes_subfolder_or_default` in `app_settings.py`; called from `create_note` | `tests/test_project_notes.py::TestM7Settings::test_blank_project_subfolder_falls_back`, `TestM7Routing::test_create_note_for_project_falls_back_when_blank` | done |
| M7.A.7 | Folder is created on first use | Already in `obsidian_utils.create_obsidian_note` (`notes_folder.mkdir(exist_ok=True)`) | `tests/test_project_notes.py::TestM7Settings::test_project_notes_folder_created_on_first_note` | done |

## Adjacent issues found, not fixed

Per CLAUDE.md §8 — flagged here for follow-up but **not** changed in this PR:

1. **Duplicate `_row_to_project_board_link`**. There are two copies (one on `DBManagerProjectBoardsMixin`, one on `DatabaseManager` at `db_manager.py:1491`) that hydrate the same row. The subclass version shadows the mixin via Python MRO — only updating the mixin would have silently returned `status='open'` for every link. Found while M1 tests failed unexpectedly. **Both copies are now kept in sync**, but the duplication is a latent footgun. Recommend a follow-up that removes the duplicate from `db_manager.py` and forces the mixin's version to win.
2. **Duplicate `_row_to_project_board`** — same pattern, same risk (status, completed_at). Not exercised in this change but the next person who touches `ProjectBoard` will hit it.
3. **`open_note_picker` and the new in-panel Notes list are functionally redundant.** The toolbar button still opens its own dialog listing the same notes that now appear in the panel as first-class rows. Worth simplifying later.
4. **`ProjectBoard.notes` field (freeform text)** is unrelated to Project Notes (Obsidian links). The naming overlap is long-term technical debt — possibly rename `ProjectBoard.notes` to `description` or `summary`.

## Final test counts

- This file's tests: 18 in `test_project_notes.py` (M1×4, M2×5, M3×7, M4×3, M5×1, M6×1, M7×9)

  Actually the M3 group includes 7 tests, M7 has 9, etc — see the file. Last run: all PASS.
- Full repo suite (last green run): **329 passed, 1 skipped** under `./venv/bin/python -m pytest`.

---

# Spec Coverage — Reward-Contingent Task Chunking (2026-08-24)

Spec: [`docs/spec_2026-08-23_dopamine_reward_protocol.md`](spec_2026-08-23_dopamine_reward_protocol.md)
Plan: [`docs/implementation_plan_2026-08-24_dopamine_reward_protocol.md`](implementation_plan_2026-08-24_dopamine_reward_protocol.md)

The spec numbers its sections but assigns no IDs, so these are the spec's own
section numbers prefixed `RP`: `RP-2.1` is spec §2.1.

| Spec ID | Description | Implementation | Test | Status |
|---|---|---|---|---|
| RP-2.1 | `action_items.deliverable TEXT` on a fresh DB | `src/getmoredone/database.py::initialize_schema` | `tests/test_reward_protocol_schema.py::test_rp21_fresh_db_has_deliverable_column`, `::test_rp2_create_table_alone_declares_every_new_column` | done |
| RP-2.1a | Idempotent migration on an upgrading DB | `src/getmoredone/database.py::_run_migrations` | `tests/test_reward_protocol_schema.py::test_rp21a_migration_adds_deliverable_to_legacy_db_and_is_idempotent` | done |
| RP-2.2 | Five `work_logs` audit columns, spec types and defaults | `src/getmoredone/database.py::initialize_schema` | `tests/test_reward_protocol_schema.py::test_rp22_fresh_db_has_all_five_work_log_reward_columns` | done |
| RP-2.2a | Migration back-fills existing rows to `0`, per-column guards | `src/getmoredone/database.py::_run_migrations` | `tests/test_reward_protocol_schema.py::test_rp22a_migration_backfills_work_log_defaults_on_existing_rows`, `::test_rp22a_a_half_migrated_db_gets_the_rest_of_the_columns` | done |
| RP-2.3 | `project_boards.savor_count INTEGER NOT NULL DEFAULT 0` | `src/getmoredone/database.py` (both halves) | `tests/test_reward_protocol_schema.py::test_rp23_savor_count_column_and_migration` | done |
| RP-2.3a | Counter round-trips; increment is real | `src/getmoredone/db_manager_project_boards.py::increment_project_savor_count`, `db_manager.py::_row_to_project_board` | `tests/test_reward_protocol_schema.py::test_rp23a_savor_count_round_trips_through_get_project_board`, `::test_rp23a_increment_reports_an_unknown_board_instead_of_pretending` | done |
| RP-2.3b | `update_project_board` cannot roll the counter back (not in spec; added in plan §1) | `src/getmoredone/db_manager_project_boards.py::update_project_board` (column deliberately absent) | `tests/test_reward_protocol_schema.py::test_rp23b_update_project_board_cannot_clobber_savor_count` | done |
| RP-2.4 | `WorkLog` carries the five fields and round-trips | `src/getmoredone/models.py::WorkLog`, `db_manager.py::create_work_log`, `::_row_to_work_log` | `tests/test_reward_protocol_schema.py::test_rp24_work_log_reward_fields_round_trip`, `::test_rp24_a_plain_session_records_no_reward` | done |
| RP-2.5 | `ActionItem.deliverable` round-trips on create **and** update | `src/getmoredone/models.py::ActionItem`, `db_manager.py::_write_new_action_item`, `::_update_action_item` | `tests/test_reward_protocol_schema.py::test_rp25_deliverable_round_trips_on_create_and_update` | done |
| RP-3.1 | `phase_for`: `< 15 → wiring`, `>= 15 → maintaining` | `src/getmoredone/reward_protocol.py::phase_for` | `tests/test_reward_protocol.py::test_rp31_phase_for_boundary_is_exactly_fifteen` | done |
| RP-3.2 | Phase 1 always savors | `src/getmoredone/reward_protocol.py::decide_reward` | `tests/test_reward_protocol.py::test_rp32_phase_one_always_shows_savor` | done |
| RP-3.3 | Phase 2 savor rate ≈ 40% | `src/getmoredone/reward_protocol.py::decide_reward` | `tests/test_reward_protocol.py::test_rp33_phase_two_savor_rate_is_about_forty_percent` | done |
| RP-3.4 | Celebration ≈ 20% in both phases | `src/getmoredone/reward_protocol.py::decide_reward` | `tests/test_reward_protocol.py::test_rp34_celebration_rate_is_twenty_percent_in_both_phases` | done |
| RP-3.5 | Celebration independent of the savor decision | `src/getmoredone/reward_protocol.py::decide_reward` | `tests/test_reward_protocol.py::test_rp35_celebration_is_independent_of_savor` | done |
| RP-3.6 | Celebration values come from `CELEBRATION_TYPES`, all used | `src/getmoredone/reward_protocol.py::CELEBRATION_TYPES` | `tests/test_reward_protocol.py::test_rp36_celebration_values_come_from_the_declared_tuple` | done |
| RP-3.7 | Never guaranteed in either phase | `src/getmoredone/reward_protocol.py::decide_reward` | `tests/test_reward_protocol.py::test_rp37_celebration_is_never_guaranteed_in_either_phase` | done |
| RP-3.8 | Thresholds are named config, not literals in the logic | `src/getmoredone/reward_protocol.py` (module constants) | `tests/test_reward_protocol.py::test_rp38_decide_reward_body_has_no_magic_numbers` | done |
| RP-3.9 | Deterministic under a seed; the injected rng is the only variation | `src/getmoredone/reward_protocol.py::decide_reward` | `tests/test_reward_protocol.py::test_rp39_same_seed_gives_the_same_sequence` | done |
| RP-4.1 | Deliverable field on the item editor, value reaches the row | `src/getmoredone/screens/item_editor.py`, `item_editor_form.py::build_item_from_form` | `tests/test_ui_presence.py::test_item_editor_ui_elements_presence`, `tests/test_item_editor_new_item_builder.py::test_rp41_deliverable_from_form_reaches_the_saved_item`, `::test_rp41_a_blank_deliverable_is_stored_as_null_not_empty_string`, `tests/test_reward_protocol_timer.py::test_rp41_editor_picks_up_a_deliverable_written_by_the_timer` | done |
| RP-4.2 | Linked start captures deliverable, board and phase | `src/getmoredone/screens/timer_window_reward.py::prepare_reward_session` | `tests/test_reward_protocol_timer.py::test_rp42_linked_start_captures_the_session_deliverable`, `::test_rp42_the_edit_prompt_is_prefilled_and_carries_the_project_context` | done |
| RP-4.2a | Blank deliverable refused, hint verbatim | `src/getmoredone/screens/timer_window_dialogs.py::DeliverableDialog` | `tests/test_reward_celebration.py::test_rp42a_deliverable_dialog_refuses_blank_and_shows_the_hint`, `::test_rp42a_cancel_returns_no_deliverable` | done |
| RP-4.2b | Cancel aborts the start; nothing is written | `src/getmoredone/screens/timer_window.py::start_timer` | `tests/test_reward_protocol_timer.py::test_rp42b_cancelling_the_deliverable_dialog_does_not_start_the_timer`, `::test_rp42b_cancelling_does_not_save_an_edited_time_block` | done |
| RP-4.2c | Unlinked item runs the timer unchanged | `src/getmoredone/screens/timer_window_reward.py::resolve_reward_board` | `tests/test_reward_protocol_timer.py::test_rp42c_unlinked_item_starts_with_no_reward_protocol` | done |
| RP-4.3 | Break end no longer auto-stops | `src/getmoredone/screens/timer_window.py::tick`, `::enter_break_choice` | `tests/test_reward_protocol_timer.py::test_rp43_break_end_does_not_auto_stop` | done |
| RP-4.3a | "Continue focus" starts a fresh cycle | `src/getmoredone/screens/timer_window.py::begin_new_focus_cycle` | `tests/test_reward_protocol_timer.py::test_rp43a_continue_focus_starts_a_fresh_cycle` | done |
| RP-4.3b | Resume after rest does not re-enter a zero-second break | `src/getmoredone/screens/timer_window.py::pause_timer` | `tests/test_reward_protocol_timer.py::test_rp43b_resume_after_rest_does_not_re_enter_a_zero_second_break` | done |
| RP-4.3c | Stop and Finished/Continue preserved (UI-regression guardrail) | `src/getmoredone/screens/timer_window.py::stop_timer` (unchanged behaviour) | `tests/test_reward_protocol_timer.py::test_rp43c_stop_and_completion_frame_survive_the_break_change` | done |
| RP-4.4 | Done visible in every state except stopped | `src/getmoredone/screens/timer_window.py::_sync_done_button` | `tests/test_reward_protocol_timer.py::test_rp44_done_button_visibility_across_every_timer_state` | done |
| RP-4.4a | Done on an unlinked item skips the protocol | `src/getmoredone/screens/timer_window_reward.py::done_action` | `tests/test_reward_protocol_timer.py::test_rp44a_done_on_unlinked_item_skips_the_reward_protocol` | done |
| RP-4.5 | Savor before celebration | `src/getmoredone/screens/timer_window_reward.py::run_reward_sequence` | `tests/test_reward_protocol_timer.py::test_rp45_savor_precedes_celebration`, `::test_rp44_done_runs_the_reward_sequence_and_then_the_completion_flow` | done |
| RP-4.5a | Celebration never substitutes for savor | `src/getmoredone/screens/timer_window_reward.py::run_reward_sequence` | `tests/test_reward_protocol_timer.py::test_rp45a_celebration_never_substitutes_for_savor` | done |
| RP-4.5b | Every reward column written on Done | `src/getmoredone/screens/timer_window.py::save_work_log` | `tests/test_reward_protocol_timer.py::test_rp45b_done_writes_every_reward_column`, `::test_rp45_savor_delivered_records_the_dialog_not_the_decision` | done |
| RP-4.5c | Counter advances even when the savor is not shown | `src/getmoredone/screens/timer_window.py::save_work_log` | `tests/test_reward_protocol_timer.py::test_rp45c_counter_advances_even_when_savor_is_not_shown` | done |
| RP-4.5d | Counter and work log are written together or not at all | `src/getmoredone/screens/timer_window.py::save_work_log` | `tests/test_reward_protocol_timer.py::test_rp45d_counter_never_advances_without_a_work_log`, `::test_rp45d_a_second_save_does_not_count_the_same_completion_twice`, `::test_rp45_a_deleted_project_completes_without_the_protocol` | done |
| RP-4.5e | Savor copy verbatim, no verbal pat | `src/getmoredone/screens/timer_window_dialogs.py::SavorDialog` | `tests/test_reward_celebration.py::test_rp45e_savor_dialog_copy_is_verbatim`, `::test_rp45e_savor_copy_contains_no_verbal_pat`, `::test_rp45e_acknowledging_records_it_and_closing_does_not` | done |
| RP-4.5f | Celebration is non-blocking and self-cancelling | `src/getmoredone/screens/timer_window_celebration.py` | `tests/test_reward_celebration.py::test_rp45f_celebration_cleans_up_on_window_close`, `::test_rp45f_every_celebration_type_draws_and_schedules`, `::test_rp45f_a_second_celebration_does_not_stack_on_the_first`, `::test_rp45f_the_frame_step_stops_once_the_canvas_is_gone`, `::test_rp45f_an_unknown_type_leaves_nothing_running`, `tests/test_reward_protocol_timer.py::test_rp45f_the_timers_cleanup_cancels_a_running_celebration` | done |
| RP-4.5g | Snapshot frozen at session start | `src/getmoredone/screens/timer_window.py::save_work_log` | `tests/test_reward_protocol_timer.py::test_rp45g_snapshot_survives_a_later_edit_of_the_deliverable` | done |
| RP-6.1 | 15 completions all savor | — (integration) | `tests/test_reward_protocol_timer.py::test_rp61_fifteen_completions_all_savor` | done |
| RP-6.2 | Completion 16 is Phase 2, savor intermittent | — (integration) | `tests/test_reward_protocol_timer.py::test_rp62_sixteenth_completion_is_phase_two`, `::test_rp62_phase_two_savors_sometimes_and_not_always` | done |
| RP-6.3 | Multi-board item uses the oldest link (spec §7.1 MVP) | `src/getmoredone/db_manager_project_boards.py::get_project_boards_for_item` | `tests/test_reward_protocol_schema.py::test_rp63_first_linked_board_by_created_at_wins`, `::test_rp63_an_unlinked_item_has_no_boards` | done |
| RP-7 | Local celebration assets, no network | `tools/generate_tada_wav.py`, `assets/audio/tada.wav`, `screens/timer_window_celebration.py` (drawn confetti/balloons) | `tests/test_reward_celebration.py::test_rp7_committed_tada_wav_is_this_scripts_output`, `::test_rp7_the_chime_is_bundled_where_the_app_looks_for_it`, `::test_rp7_the_chime_is_short_small_and_playable` | done |

## Human review required (not code-testable)

| Item | Why it cannot be a test | What is tested instead |
|---|---|---|
| The savor step produces the intended felt sense | Subjective by definition | Copy asserted verbatim; ordering asserted; forbidden "good job" phrasings asserted absent |
| The confetti/balloon overlays look like a celebration | Visual quality | That each type draws items, schedules frames, is non-blocking and tears down cleanly |
| `assets/audio/tada.wav` sounds like "Ta-DA!" | Requires listening | Valid mono 16-bit WAV, 0.69s, 30 KB, non-silent, non-clipping, and byte-for-byte the generator's output |

# Spec Coverage — Time blocks, the Plan screen rebuild (2026-11-05)

Plan: [`docs/implementation_plan_2026-11-05_time_blocks.md`](implementation_plan_2026-11-05_time_blocks.md)

Every row's test was mutation-proved: the line it names deleted or inverted,
the test confirmed red, the verbatim original restored.

| Spec ID | Criterion | Implementation | Test | Status |
|---|---|---|---|---|
| TB-M1.1 | Migration adds `block_type`/`position` to a legacy `time_blocks` table and is idempotent on a second run | `src/getmoredone/database.py` (initialize_schema + _run_migrations), `src/getmoredone/models.py` (TimeBlock, BlockType) | `tests/test_time_block_schema.py::test_tbm11_migration_adds_columns_and_is_idempotent` | done |
| TB-M1.2 | A `TimeBlock` round-trips type and position through create → read | `src/getmoredone/database.py` (initialize_schema + _run_migrations), `src/getmoredone/models.py` (TimeBlock, BlockType) | `tests/test_time_block_schema.py::test_tbm12_block_type_and_position_round_trip` | done |
| TB-M1.3 | **Dirty state (P8)** — a row written before the migration reads back with `block_type='item'`, `position=0`, and does not raise | `src/getmoredone/database.py` (initialize_schema + _run_migrations), `src/getmoredone/models.py` (TimeBlock, BlockType) | `tests/test_time_block_schema.py::test_tbm13_pre_migration_row_reads_with_defaults` | done |
| TB-M2.1 | `update_time_block` persists a changed duration — the row, re-read, holds the new value | `src/getmoredone/db_manager.py` (update_time_block, get_items_for_start_date, get_blocked_item_ids; *`repack_day` and `reorder_time_blocks` were here and are gone*) | `tests/test_time_block_crud.py::test_tbm21_update_persists_duration` | done |
| TB-M2.2 | `reorder_time_blocks` leaves no two blocks on a day sharing a start time, and no gaps | `src/getmoredone/db_manager.py` (update_time_block, get_items_for_start_date, get_blocked_item_ids; *`repack_day` and `reorder_time_blocks` were here and are gone*) | *test removed with the criterion:* `test_tbm22_reorder_yields_unique_contiguous_times` | superseded by the grid — `reorder_time_blocks` is gone — a drag writes one row's box, so there is no day-wide re-timing to make unique. |
| TB-M2.3 | A reorder that fails partway writes **nothing** | `src/getmoredone/db_manager.py` (update_time_block, get_items_for_start_date, get_blocked_item_ids; *`repack_day` and `reorder_time_blocks` were here and are gone*) | *test removed with the criterion:* `test_tbm23_failed_reorder_is_atomic` | superseded by the grid — `reorder_time_blocks` is gone. Atomicity now belongs to `add_block_at`/`place_block_at`/`set_block_length`, each covered under TG-M6.2. |
| TB-M2.4 | `get_items_for_start_date` returns the item starting that day and **not** one starting the day before or after | `src/getmoredone/db_manager.py` (update_time_block, get_items_for_start_date, get_blocked_item_ids; *`repack_day` and `reorder_time_blocks` were here and are gone*) | `tests/test_time_block_crud.py::test_tbm24_start_date_filter_is_exact` | done |
| TB-M3.1 | `pack_day` packs from day start with no gaps | `src/getmoredone/time_block_layout.py` (*`pack_day` was here and is gone*) | *test removed with the criterion:* `test_tbm31_blocks_pack_from_day_start` | superseded by the grid — `pack_day` is gone. The grid derives every time from `slot_index`; see TG-M1.1. |
| TB-M3.2 | **Adversarial (P7)** — a block that fits *up to* lunch start but not through it is pushed whole to after lunch, not split and not overlapped onto lunch | `src/getmoredone/time_block_layout.py` | *test removed with the criterion:* `test_tbm32_block_straddling_lunch_moves_after_lunch` | superseded by the grid — a block is never pushed past lunch now. Lunch is a box that takes no tasks, and a drop that would run into it is refused and says so. See TG-M9.2. |
| TB-M3.3 | **Real scale (P9)** — a day of 14 × 60 min blocks: those past day end are returned and flagged, never dropped | `src/getmoredone/time_block_layout.py` | *test removed with the criterion:* `test_tbm33_overflow_blocks_are_flagged_not_dropped` | superseded by the grid — nothing can be placed past Day End, so there is no overflow to flag. Work the grid cannot hold is surfaced in the *Outside the day* group. See TG-M3.1. |
| TB-M3.4 | `duration_for_item` returns `work_block` when set, 30 when not | `src/getmoredone/time_block_layout.py` | `tests/test_time_block_layout.py::test_tbm34_work_block_wins_over_default` | done |
| TB-M3.5 | `depth_bars` → 3/2/1, and 1 for `None` and for an unrecognised string | `src/getmoredone/time_block_layout.py` | `tests/test_time_block_layout.py::test_tbm35_depth_bars_default_to_one` | done |
| TB-M3.6 | `is_block_day` is False for an unchecked weekday, True for a checked one | `src/getmoredone/time_block_layout.py` | `tests/test_time_block_layout.py::test_tbm36_unchecked_weekday_is_not_a_block_day` | done |
| TB-M4.1 | A settings file with a garbage `plan_day_start` loads with the default rather than raising | `src/getmoredone/app_settings.py` (_normalize_plan_day_settings) | `tests/test_plan_settings.py::test_tbm41_bad_time_falls_back_to_default` | done |
| TB-M4.2 | A `plan_block_weekdays` of the wrong length is coerced to seven booleans | `src/getmoredone/app_settings.py` (_normalize_plan_day_settings) | `tests/test_plan_settings.py::test_tbm42_weekday_list_is_coerced_to_seven` | done |
| TB-M4.3 | Saved day settings survive a save/load cycle | `src/getmoredone/app_settings.py` (_normalize_plan_day_settings) | `tests/test_plan_settings.py::test_tbm43_day_settings_round_trip` | done |
| TB-M5.1 | The modal exposes all four time fields and seven checkboxes, and Save writes them to `AppSettings` | `src/getmoredone/screens/plan_settings_dialog.py` | `tests/test_plan_screen.py::test_tbm51_settings_modal_writes_day_settings` | done |
| TB-M6.1 | Changing the date picker reloads the item list and the block list for the new date | `src/getmoredone/screens/plan.py` (create_header, on_date_changed) | `tests/test_plan_screen.py::test_tbm61_date_change_reloads_both_panes` | done |
| TB-M7.1 | The left pane shows exactly the items whose start date is the selected date | `src/getmoredone/screens/plan.py` (load_items), `screens/plan_blocks.py` (build_item_row) | `tests/test_plan_screen.py::test_tbm71_item_list_matches_selected_date` | done |
| TB-M8.1 | A drop on the day column creates one block in the database, with the item's work block as its length | `src/getmoredone/screens/plan.py` (bind_item_drag, on_drag_release, block_item, _require_block_day) | `tests/test_plan_screen.py::test_tbm81_drop_creates_block_using_work_block` | done |
| TB-M8.2 | A drop on an unchecked weekday creates **no** block and reports why | `src/getmoredone/screens/plan.py` (bind_item_drag, on_drag_release, block_item, _require_block_day) | `tests/test_plan_screen.py::test_tbm82_drop_on_non_block_day_is_refused` | done |
| TB-M9.1 | Both `<Button-3>` and `<Button-2>` are bound on a block widget | `src/getmoredone/screens/plan.py` (bind_block_handlers, open_block_menu, set_block_minutes) | `tests/test_plan_screen.py::test_tbm91_both_right_click_buttons_are_bound` | done |
| TB-M9.2 | Choosing 60 from the menu updates that block's row to 60 and re-times the blocks after it | `src/getmoredone/screens/plan.py` (bind_block_handlers, open_block_menu, set_block_minutes) | *test removed with the criterion:* `test_tbm92_duration_change_repacks_the_day` | superseded by the grid — The resize no longer re-times the rest of the day — nothing else moves. See TG-M11.2. |
| TB-M10.1 | Add Buffer and Add Break each create a typed block of the right length | `src/getmoredone/screens/plan.py` (add_padding_block), `models.py` (BlockType) | `tests/test_plan_screen.py::test_tbm101_buffer_and_break_blocks_are_typed` | done |
| TB-M11.1 | Dragging block 3 above block 1 leaves the database in that order, by position and by time | `src/getmoredone/screens/plan.py` (start_block_drag; *`drop_index_for_pointer` and `reorder_to` were here and are gone*) | *test removed with the criterion:* `test_tbm111_reorder_persists_new_order` | superseded by the grid — The reorder gesture is gone. A drag moves a block to the box it was dropped on; see TG-M11.1. |
| TB-M12.1 | Block height is proportional to minutes — a 90 is three times a 30 | `src/getmoredone/screens/plan_blocks.py`, `src/getmoredone/theme.py`, `time_block_layout.py` (*`block_height` was here and is gone*) | *test removed with the criterion:* `test_tbm121_block_height_tracks_minutes` | superseded by the grid — `block_height` is gone. A box is half an hour whatever is in it; its height is how many tasks share it. See TG-M10.1. |
| TB-M12.2 | Every band colour clears the contrast minimum against the block background in **both** light and dark themes (via the existing `color_contrast.py`) | `src/getmoredone/screens/plan_blocks.py`, `src/getmoredone/theme.py`, `time_block_layout.py` (*`block_height` was here and is gone*) | `tests/test_time_block_colors.py::test_tbm122_band_colors_meet_contrast_in_both_themes` | done |
| TB-M12.3 | No hard-coded hex outside the `theme.py` band table — parsed from the AST, asserted as an **exact count of zero** | `src/getmoredone/screens/plan_blocks.py`, `src/getmoredone/theme.py`, `time_block_layout.py` (*`block_height` was here and is gone*) | `tests/test_time_block_colors.py::test_tbm123_no_inline_hex_in_plan_screen` | done |

## Human review required (not code-testable)

| Item | Why it cannot be a test | What is tested instead |
|---|---|---|
| That the drag *feels* right — hit-test tolerance, hover feedback, whether a 45-pixel block is grabbable | Subjective, and a function of real pointer travel on a real display | Four event-level tests generate real `<ButtonPress-1>`/`<B1-Motion>`/`<ButtonRelease-1>` at the real row widgets and assert the database result: the item drop, the refused drop, the reorder, the right-click |
| That macOS delivers a right-click to one of the two bound buttons on this machine | The OS decides, not the app | Both `<Button-3>` and `<Button-2>` are asserted bound, from the screen's own `RIGHT_CLICK_SEQUENCES` constant, so adding a sequence without binding it fails |
| How the screen looks at full size | Visual quality | Block height proportionality in real geometry; band and block-type colours measured against the real block surface in both themes; an AST check that no screen module holds a hex colour |

Both human checks are outstanding: `/Applications/daVIPA.app` held the
single-instance lock for the whole batch, so a source launch would have exited
silently. Run `./start-demo.sh`, or quit the packaged app and `./start.sh`.

## Adjacent issues found, not fixed

- The drag hit-test was written out by hand four times in `drag_schedule.py`.
  Factored into one `widget_contains_pointer` in `drag_schedule_support.py`
  rather than adding a fifth and sixth copy; the 38 existing drag-schedule
  tests cover the change. The pre-push sweep then found that its `Tests:` line
  named a test that did not exist anywhere, so the function this batch
  extracted to be shared had no direct coverage at all. Twelve tests now cover
  it, including the named one.
- `delete_action_item` raises on an item that holds a block:
  `time_blocks.item_id` references `action_items(id)` with no `ON DELETE`
  clause and foreign keys are on. Pre-existing, but this batch makes creating a
  block a single drag, so a latent crash becomes reachable in ordinary use.
  Flagged, not fixed, per global rule 10 — the fix is a schema decision, not a
  line. In `BACKLOG.md`.
- Seventeen below-medium items are recorded in `BACKLOG.md` — four deferred
  during the build, eight from the pre-push review passes, four from the
  re-sweep of the fix commits, and one adjacent issue found while proving
  those fixes.

## Final test counts

Collected counts, measured with `--collect-only` rather than counted by hand,
so the parametrised cases are included.

| File | Tests | Needs a display |
|---|---|---|
| `tests/test_time_block_schema.py` | 6 | no |
| `tests/test_time_block_layout.py` | 115 | no |
| `tests/test_time_block_crud.py` | 30 | no |
| `tests/test_plan_settings.py` | 26 | no |
| `tests/test_time_block_colors.py` | 6 | sets the appearance mode; builds no widget |
| `tests/test_drag_schedule_support.py` | 18 (12 new) | one builds a withdrawn Tk root |
| `tests/test_plan_screen.py` | 62 | real Tk; 5 need `mapped_windows` |
| **Total in these files** | **263** | 200 build no Tk widget |

257 of those 263 are new in this batch; the other six predate it. The
*builds no Tk widget* count is 263 less the 62 in `test_plan_screen.py` and the
one withdrawn-root test — measured by which modules construct a widget, not
by which can run headless, since all of them can.

Whole suite after the batch: 1691 behaviour tests and 212 meta.

## Pre-push review passes

| Pass | Lens | Result |
|---|---|---|
| `/code-review` | correctness, reuse, simplification | 5 findings: 1 high, 2 medium, 2 low |
| `learning-qa` | the failure-pattern catalogue (P1–P39) | 12 findings: 2 high, 1 medium-high, 3 medium, 6 below |
| `/security-review` | injection, secrets, path traversal, deserialization | run because the diff adds SQL; no HIGH or MEDIUM findings |
| `learning-qa` over the fix commits | the same catalogue, re-run on the least-reviewed code in the change | 8 findings: 0 high, 4 medium, 4 low |

Everything at medium severity or above was fixed in the same session with a
test, each proved by mutation. Everything below medium is recorded in
`BACKLOG.md` with the pass that found it and the reason it was deferred, per
the review-sweep budget in `CLAUDE.md`: a below-medium fix is new unreviewed
surface that buys none of the safety it costs.

Two of the sweep's findings were about the tests themselves rather than the
code, and both were corrected as such: one expectation encoded the inverse of
the design (that `load_blocks` persists derived times), and one atomicity test
passed against a version with no transaction at all, because its fixture raised
before anything had been written.

The re-sweep of the fix commits found that the second of those corrections was
itself fragile: its replacement fixture raised on the second *read* of a bounds
property, which identifies the second day only while `pack_day` reads that
property exactly once per call. It does — probed rather than assumed — but the
test now counts the per-day repacks instead, and a second test asserts the
first day really is written before the failure, which is the thing that makes
the atomicity assertion mean anything. Because that pass produced no
high-severity finding, the budget in `CLAUDE.md` ends the sweep there.

# Spec Coverage — the Plan screen as a 30-minute grid (2026-11-05)

Plan: [`docs/implementation_plan_2026-11-05_time_grid.md`](implementation_plan_2026-11-05_time_grid.md)

This replaces the **order** model recorded in the section above, which never
shipped: a planned day was a list whose clock times were re-derived on every
edit. A day is now a fixed grid of half hours, and a block stores **which box**
it is in, relative to Day Start. The rows that section marks
*superseded by the grid* are the criteria that went with the old model.

Every row's test was mutation-proved: the line it names deleted or inverted,
the test confirmed red, the verbatim original restored. 27 mutations, 27 reds.

| Spec ID | Criterion | Implementation | Test | Status |
|---|---|---|---|---|
| TG-M1.1 | `day_grid` yields one slot per half hour from Day Start to Day End inclusive of the last whole slot | `src/getmoredone/time_block_layout.py` (day_grid, Slot) | `tests/test_time_grid.py::test_tgm11_grid_covers_the_day_in_half_hours` | done |
| TG-M1.2 | Lunch slots are marked unavailable and are **not** omitted from the grid | `src/getmoredone/time_block_layout.py` (day_grid) | `tests/test_time_grid.py::test_tgm12_lunch_slots_are_marked_not_removed` | done |
| TG-M1.3 | A Day End that is not on a half hour yields no partial trailing slot | `src/getmoredone/time_block_layout.py` (day_grid) | `tests/test_time_grid.py::test_tgm13_a_ragged_day_end_yields_no_partial_slot` | done |
| TG-M2.1 | `slots_for_minutes` rounds up: 30→1, 45→2, 60→2, 1→1 | `src/getmoredone/time_block_layout.py` (slots_for_minutes, slot_span_of) | `tests/test_time_grid.py::test_tgm21_odd_lengths_round_up` | done |
| TG-M2.1a | The minutes a rounded-up block leaves spare in its last box are reported, not rounded away | `src/getmoredone/time_block_layout.py` (spare_minutes_in_last_slot), `screens/plan_blocks.py` (_build_block_chip) | `tests/test_time_grid.py::test_the_spare_minutes_of_the_last_box_are_what_the_task_leaves`, `::test_a_block_with_no_length_leaves_nothing_spare` | done |
| TG-M2.2 | **Adversarial (P7)** — a 2-slot block whose second slot is lunch is refused, not drawn across it | `src/getmoredone/time_block_layout.py` (can_place) | `tests/test_time_grid.py::test_tgm22_a_span_cannot_cross_lunch`, `::test_a_block_may_not_start_on_lunch_either` | done |
| TG-M2.3 | A refusal names its reason; every reason is a distinct named value | `src/getmoredone/time_block_layout.py` (SlotRefusal, SlotRefusedError, can_place) | `tests/test_time_grid.py::test_tgm23_each_refusal_has_its_own_reason` | done |
| TG-M2.4 | **Real scale (P9)** — a 9-hour day fully occupied: the next placement is refused, the placed ones are all returned | `src/getmoredone/time_block_layout.py` (can_place, slot_occupancy, MAX_BLOCKS_PER_SLOT) | `tests/test_time_grid.py::test_tgm24_a_full_day_refuses_the_next_one` | done |
| TG-M3.1 | **P2** — a block whose slot no longer exists is returned flagged, never dropped | `src/getmoredone/time_block_layout.py` (build_day_grid, DayGrid.outside) | `tests/test_time_grid.py::test_tgm31_blocks_outside_the_grid_are_surfaced`, `::test_a_block_whose_span_now_runs_past_the_day_is_surfaced_too`, `::test_a_never_placed_block_is_surfaced_rather_than_assumed_to_be_at_eight` | done |
| TG-M3.1a | A block sitting in a box lunch has since moved onto is surfaced too — a lunch box draws no tasks, so one left there would vanish | `src/getmoredone/time_block_layout.py` (build_day_grid) | `tests/test_time_grid.py::test_a_block_sitting_in_a_lunch_box_is_surfaced_not_hidden`, `::test_a_span_that_runs_through_lunch_is_surfaced_too` | done |
| TG-M3.1b | The "outside the day" group is **drawn**, and a settings change that creates one says so | `src/getmoredone/screens/plan_blocks.py` (build_outside_group), `screens/plan.py` (load_blocks, on_settings_saved) | `tests/test_plan_screen.py::test_tgm31_an_outside_block_is_drawn` | done |
| TG-M4.1 | Migration adds `slot_index`, is idempotent on a second run | `src/getmoredone/database.py` (initialize_schema + _run_migrations), `models.py` (TimeBlock.slot_index) | `tests/test_time_block_schema.py::test_tgm41_migration_adds_slot_index_idempotently` | done |
| TG-M4.1a | A fresh install gets the column from `CREATE TABLE` too, and it is nullable with no default so "never placed" stays representable | `src/getmoredone/database.py` (initialize_schema) | `tests/test_time_block_schema.py::test_a_fresh_database_has_slot_index_too`, `::test_slot_index_is_nullable_so_never_placed_is_representable` | done |
| TG-M4.2 | The day is indexed by `(block_date, slot_index, position)`, which is the order every read uses | `src/getmoredone/database.py` (_run_migrations, idx_blocks_date_slot) | `tests/test_time_block_schema.py::test_the_day_is_indexed_by_box` | done |
| TG-M5.1 | A row stored at `09:30` under an 08:00 Day Start adopts `slot_index` 3 | `src/getmoredone/db_manager.py` (adopt_legacy_day) | `tests/test_time_block_schema.py::test_tgm51_existing_times_map_to_slots` | done |
| TG-M5.2 | **Dirty state (P8)** — a row with an empty `start_time` adopts the first box that fits and does not raise; adopting twice changes nothing | `src/getmoredone/db_manager.py` (adopt_legacy_day) | `tests/test_time_block_schema.py::test_tgm52_a_timeless_row_migrates_by_position`, `::test_adopting_a_day_twice_changes_nothing_the_second_time` | done |
| TG-M5.3 | A readable start time goes on the box it names **or nowhere** — never slid to the nearest free box | `src/getmoredone/db_manager.py` (adopt_legacy_day) | `tests/test_time_block_schema.py::test_a_legacy_block_the_grid_cannot_hold_keeps_its_null`, `::test_a_legacy_block_before_day_start_keeps_its_null`, `::test_a_legacy_block_whose_own_box_is_full_keeps_its_null` | done |
| TG-M5.4 | The migration runs **only** against a day shape the settings file says was confirmed — not after an unreadable file, not on a file written before Day Settings existed, not on a value the app substituted, and not across a relaunch or a downgrade | `src/getmoredone/app_settings.py` (_day_shape_was_confirmed, load), `src/getmoredone/screens/plan.py` (_day_shape_is_the_users), `src/getmoredone/screens/plan_settings_dialog.py` (save) | `tests/test_plan_settings.py::test_a_settings_file_from_before_day_settings_is_not_a_confirmed_day`, `::test_a_build_that_dropped_the_field_is_not_confirmation`, `::test_a_confirmed_flag_without_the_values_it_describes_is_not_confirmation`, `::test_a_day_shape_the_user_confirmed_is_left_alone`, `::test_a_day_value_the_app_had_to_substitute_is_not_the_users`, `::test_a_lunch_the_app_had_to_clamp_is_not_the_users`, `::test_no_settings_file_is_not_a_confirmed_day`, `::test_a_guessed_day_shape_survives_a_relaunch`, `tests/test_plan_screen.py::test_adoption_does_not_run_on_a_file_from_before_day_settings`, `::test_adoption_does_not_run_on_a_guessed_day_start`, `::test_saving_day_settings_unblocks_adoption` | done |
| TG-M6.1 | Two blocks on one `slot_index` round-trip, ordered by `position` | `src/getmoredone/db_manager.py` (add_block_at, _settle_block_on_slot, get_time_blocks) | `tests/test_time_block_crud.py::test_tgm61_two_blocks_share_a_slot` | done |
| TG-M6.1a | `position` counts **within** a box, not across the day | `src/getmoredone/db_manager.py` (_next_position_in_slot) | `tests/test_time_block_crud.py::test_position_restarts_in_each_box` | done |
| TG-M6.2 | A write settles the box, the position and the derived times in one transaction; a refusal writes nothing | `src/getmoredone/db_manager.py` (add_block_at, place_block_at, set_block_length, _refuse_unless_it_fits) | `tests/test_time_block_crud.py::test_tgm62_a_failed_move_writes_nothing`, `::test_a_move_rewrites_the_times_with_the_slot`, `::test_a_block_can_be_nudged_inside_a_box_that_is_already_full` | done |
| TG-M6.3 | Every written row satisfies `end == start + planned_minutes` | `src/getmoredone/time_block_layout.py` (times_for_slot) | `tests/test_time_block_crud.py::test_tgm63_every_row_says_start_plus_duration`, `::test_a_resize_that_fits_rewrites_the_end_time` | done |
| TG-M6.4 | Day Start changing re-times every day with **no** write to `time_blocks` | `src/getmoredone/time_block_layout.py` (times_for_slot, day_grid) | `tests/test_time_block_crud.py::test_tgm64_a_day_start_change_writes_no_rows` | done |
| TG-M6.4a | The same through the screen: `on_settings_saved` writes nothing and the grid re-times | `src/getmoredone/screens/plan.py` (on_settings_saved) | `tests/test_plan_screen.py::test_tgm64_saving_settings_writes_no_blocks` | done |
| TG-M7.1 | Every slot in the grid is drawn, empty ones included | `src/getmoredone/screens/plan.py` (load_blocks), `screens/plan_blocks.py` (build_slot_row, build_empty_day_note) | `tests/test_plan_screen.py::test_tgm71_every_slot_is_drawn` | done |
| TG-M8.1 | A half-hour box is within 8px of its pane's width | `src/getmoredone/screens/plan_blocks.py` (build_slot_row, _configure_slot_columns) | `tests/test_plan_screen.py::test_tgm81_a_block_row_fills_its_pane` *(needs `mapped_windows`)* | done |
| TG-M8.2 | A box's title label is non-empty and mapped | `src/getmoredone/screens/plan_blocks.py` (_build_block_chip) | `tests/test_plan_screen.py::test_tgm82_a_block_row_shows_its_title` *(needs `mapped_windows`)* | done |
| ~~TG-M8.3~~ | **Dropped**, not implemented. The sliver bug it was written for does not reproduce, and `_aim_pointer_at`'s `max(1, …)` floor alters the aim only at widths 0 and 1 | — | — | not done — criterion withdrawn, with the measurement, in the plan's TG-M8 section |
| TG-M9.1 | Dropping an item on the 11:00 box creates a block at `slot_index` 6, not at the end of the day | `src/getmoredone/screens/plan.py` (slot_under_pointer, on_drag_release, block_item) | `tests/test_plan_screen.py::test_tgm91_a_drop_lands_on_the_slot_under_the_pointer` | done |
| TG-M9.2 | A drop on a lunch slot is refused, with the reason on the status line and nothing written | `src/getmoredone/screens/plan.py` (REFUSAL_TEXT, refusal_text, block_item) | `tests/test_plan_screen.py::test_tgm92_a_drop_on_lunch_is_refused_and_says_why` | done |
| TG-M9.3 | A release that lands on no box is a cancelled drag — never "the nearest box" | `src/getmoredone/screens/plan.py` (slot_under_pointer) | `tests/test_plan_screen.py::test_a_drop_that_lands_on_no_box_is_a_cancelled_drag` | done |
| TG-M10.1 | A second item dropped on a filled box joins it; both titles are drawn, and the box is drawn taller | `src/getmoredone/screens/plan_blocks.py` (build_slot_row, slot_row_height) | `tests/test_plan_screen.py::test_tgm101_two_tasks_share_a_box` | done |
| TG-M10.2 | The later boxes of a longer task are marked as continuations and say what they leave spare | `src/getmoredone/screens/plan_blocks.py` (_build_block_chip) | `tests/test_plan_screen.py::test_a_longer_task_marks_the_boxes_it_runs_through` | done |
| TG-M10.3 | A continuation chip carries no drag and no menu — the box a block starts in owns it | `src/getmoredone/screens/plan_blocks.py` (build_slot_row), `screens/plan.py` (load_blocks) | `tests/test_plan_screen.py::test_a_continuation_chip_carries_no_drag` | done |
| TG-M11.1 | A real press-and-release moves a block to the box it was dropped on | `src/getmoredone/screens/plan.py` (bind_block_handlers, on_drag_release, move_block_to_slot) | `tests/test_plan_screen.py::test_tgm111_a_real_drag_moves_a_block_between_slots` *(needs `mapped_windows`)* | done |
| TG-M11.2 | A resize that would not fit from where the block sits is refused and the block does not move | `src/getmoredone/db_manager.py` (set_block_length), `screens/plan.py` (set_block_minutes) | `tests/test_time_block_crud.py::test_tgm112_a_resize_that_does_not_fit_is_refused` | done |
| TG-M12.1 | A 45-minute item in a day reports 2 boxes, 1h 00m occupied, 45m planned — all three | `src/getmoredone/screens/plan.py` (update_day_summary, _clock) | `tests/test_plan_screen.py::test_tgm121_the_summary_separates_occupied_from_planned` | done |

## Human review required (not code-testable)

| Item | Why it cannot be a test | What is tested instead |
|---|---|---|
| Whether the grid *reads* as a day at full size — 18 boxes in the pane, the empty ones legible, the continuation chips distinguishable from the tasks that own them | Pixel judgement, not a predicate | TG-M8.1/8.2 in real geometry: a box fills its pane within 8px and its title label is mapped and wider than a pixel. TG-M10.1 asserts a shared box is drawn taller than a single one |
| Whether macOS delivers right-click as `<Button-3>` or `<Button-2>` on this machine | The OS decides, not the app | Both stay bound, asserted from the screen's own `RIGHT_CLICK_SEQUENCES`, and a real `<Button-3>` on a real chip is asserted to open a menu |
| Whether dragging a chip between boxes *feels* right — the hover outline, the grab target on a 30px chip | Subjective, and a function of real pointer travel | TG-M11.1 and the item-drop test generate real `<ButtonPress-1>`/`<B1-Motion>`/`<ButtonRelease-1>` at real widgets and assert the stored box |

### Walked on screen, 2026-11-06 (`./start-demo.sh`)

- **Right-click** — **done.** A real right-click on a placed chip opened the
  menu: 15 / 30 (default) / 45 / 60 / 90 minutes, Custom…, Delete block.
- **Does the grid read as a day** — **no, and the test that said it did was
  wrong.** At full size all 18 boxes fit one view with lunch shaded, but every
  placed task rendered as a bare 4px stripe: no title, no duration, no depth
  bars. TG-M8.1 and TG-M8.2 passed throughout, because a title laid out below
  the box it is clipped to is still full-width and still `winfo_ismapped()`.
  Cause and fix in
  `docs/implementation_plan_2026-11-06_plan_box_appearance.md` (PB-M2); the
  gap in the two tests is closed by PB-M2.1, which measures the title's
  position inside the box rather than its width.
- **Does a drag feel right** — still outstanding, and now overtaken: PB-M5
  sizes a box from the Drag Schedule box-height setting, so what a 30px chip
  felt like is no longer the question. To be re-walked once PB-M5 is on screen.

### Walked on screen, 2026-11-06, after PB-M6 / PB-M7 (`./start-demo.sh`)

The demo relaunched on the committed code, `drag_schedule_box_height_px = 30`.

- **PB-M6.2, no priority value on a row** — **done.** No score on any of the
  five rows.
- **PB-M6.3, the work-block length under the depth bars** — **done, and since
  superseded by PD-M1.2.** `30m` / `60m` sat directly beneath the three-bar
  stack, right-aligned with it. What the walk did not ask was whether a day box
  puts it there, and it does not: it writes the length beside the bars at the
  right-hand end of the task's one line. The length moved there with PD-M1.
- **PB-M7, the continuation** — **done.** The 10:30 box of the 60-minute
  "Review project proposal" carries the same fill and the same stripe as its
  10:00 box, with the `↳` prefix and `same task` on the right.
- **PB-M6.1, a row the height of the space it takes** — **done, and only
  visible above the floor.** At a box height of 30 a one-box row is 67px and a
  two-box row 70, so the difference is 3px and the demo's own setting hides the
  thing the criterion is about. Set to 86 the left pane shows it plainly: the
  60-minute item is exactly twice the height of each 30-minute item, with its
  two lines of text at the top and the slack at the bottom.
- **A saved box height did nothing until the next launch** — **found here, and
  fixed.** This is what the walk was for: three review passes and a green suite
  had not touched it, because every test builds a screen from an object it was
  handed. See the Fixed entry in `CHANGELOG.md` and
  `tests/test_plan_settings.py::test_a_saved_box_height_reaches_the_running_app`.
- **Does a drag feel right** — still outstanding. PB-M5 and PB-M6 have changed
  what a chip and a row are, and no drag was performed in this walk.

A source launch exits silently with status 0 while `/Applications/daVIPA.app`
holds the single-instance lock, so use `./start-demo.sh`, or quit the packaged
app and `./start.sh`.

## Adjacent issues found, not fixed

- `PIXELS_PER_MINUTE` and `MIN_BLOCK_HEIGHT_PX` became unreachable with
  `block_height`. Deleted in this batch rather than flagged, since they are
  this change's own orphans and nothing outside `time_block_layout.py` read
  them.
- Three `Tests:` docstring lines named tests that no longer exist, found by
  `tests/test_traceability_refs.py` rather than by review. Repointed in this
  batch. The meta test is the only thing that catches this class, and it caught
  it on the full-suite run, not on the touched files.
- The four items deferred from the time-block rebuild in `BACKLOG.md` are
  unchanged by the grid, except that *"No way to move a block to another day"*
  is now the only way to re-plan work for tomorrow, since a drag within a day
  moves it between boxes.


---

# Spec Coverage — Plan box appearance (2026-11-06)

Plan: [`docs/implementation_plan_2026-11-06_plan_box_appearance.md`](implementation_plan_2026-11-06_plan_box_appearance.md)

Seven changes asked for against the running demo: five after the first
walkthrough, two more after those five were on screen. All tests are in
`tests/test_plan_screen.py` unless named otherwise.

| Spec ID | Description | Implementation | Test | Status |
|---|---|---|---|---|
| PB-M1.1 | `priority_stripe_colors()` returns all five bands in both themes | `src/getmoredone/theme.py` (priority_stripe_colors) | `tests/test_time_block_colors.py::test_pbm11_stripe_colors_cover_every_band` | done |
| PB-M1.2 | Every stripe colour clears 3:1 on `surface_subtle`, both themes | `src/getmoredone/theme.py` (priority_stripe_colors) | `tests/test_time_block_colors.py::test_pbm12_stripe_colors_meet_the_non_text_contrast_bar` | done |
| PB-M1.2 | `priority_band_colors()` is unchanged and still clears 4.5:1 wherever a band sits behind text | `src/getmoredone/theme.py` (priority_band_colors) | `tests/test_time_block_colors.py::test_tbm122_band_colors_meet_contrast_in_both_themes` | done — pre-existing test, carried |
| PB-M1.3 | Every light-theme stripe colour is brighter than the text-safe band of the same name, by relative luminance rather than by eye | `src/getmoredone/theme.py` (priority_stripe_colors) | `tests/test_time_block_colors.py::test_pbm13_stripe_colors_are_brighter_than_the_text_safe_set`, `::test_pbm13_the_dark_stripe_table_is_the_band_table` | done |
| PB-M1.4 | An item row's stripe comes from the brighter table | `src/getmoredone/screens/plan_blocks.py` (stripe_for_item) | `::test_pbm1_an_item_rows_stripe_uses_the_brighter_table` *(pins the appearance mode)* | done — added in the sweep; the criterion was not in the plan |
| PB-M2.1 | A chip's title label lies wholly inside the box it is drawn in | `src/getmoredone/screens/plan_blocks.py` (STRIPE_MIN_HEIGHT_PX, _build_block_chip) | `::test_a_task_chips_title_is_inside_the_box_it_is_drawn_in` *(needs `mapped_windows`; labelled TG-M8.3 in its docstring, written before this plan)* | done |
| PB-M2.2 | An item row is no taller than its two lines of text | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `::test_an_item_row_lays_out_at_the_height_it_asks_for` | superseded by PB-M6.1 — a row is now a multiple of the box height on purpose. The test was rewritten to assert the row lays out at the height it *asks for* rather than at its text's height |
| PB-M3.1 | A chip for an item with depth renders three bars, all inside the box | `src/getmoredone/screens/plan_blocks.py` (_build_block_chip, DepthBarStack) | `::test_pbm31_the_depth_bars_are_inside_the_box` *(needs `mapped_windows`)* | done |
| PB-M4.1 | Every fill tint carries legible text under the colour `pick_text_color` picks for it, both themes | `src/getmoredone/theme.py` (priority_fill_colors, pick_text_color) | `tests/test_time_block_colors.py::test_pbm41_pick_text_color_is_not_what_makes_a_fill_legible`, `::test_pbm41_a_chips_title_is_coloured_for_the_shade_behind_it` | done |
| PB-M4.2 | Every stripe clears 3:1 against its own band's fill tint, both themes | `src/getmoredone/theme.py` (priority_stripe_colors, priority_fill_colors) | `tests/test_time_block_colors.py::test_pbm42_a_stripe_is_visible_on_its_own_fill` | done |
| PB-M4.3 | A chip for a critical item is filled with the critical tint and not `surface_subtle`; padding is left unshaded | `src/getmoredone/screens/plan_blocks.py` (fill_for_item, _build_block_chip) | `::test_pbm43_a_chip_is_filled_by_its_priority` *(pins the appearance mode)* | done |
| PB-M5.1 | `slot_row_height(1, chip_height=86)` is 90; the no-argument form is unchanged | `src/getmoredone/time_block_layout.py` (slot_row_height) | `::test_pbm51_box_height_follows_the_setting` | done |
| PB-M5.2 | A box built with `drag_schedule_box_height_px = 120` is taller than one at the default | `src/getmoredone/screens/plan.py` (box_height), `plan_blocks.py` (build_slot_row) | `::test_pbm52_the_setting_reaches_the_rendered_box` | done |
| PB-M5.3 | An unusable setting (0, negative, non-numeric) falls back to the constant | `src/getmoredone/screens/plan.py` (_positive_setting) | `::test_pbm53_an_unusable_box_height_falls_back` | done |
| PB-M5.4 | The chip's title column requests the Drag Schedule title width | `src/getmoredone/screens/plan.py` (box_title_width), `plan_blocks.py` (_build_block_chip) | `::test_pbm54_the_title_column_follows_the_drag_schedule_width` | done |
| PB-M5.5 | A block outside the day is sized by the same two settings as one in a box | `src/getmoredone/screens/plan_blocks.py` (build_outside_group), `plan.py` (load_blocks) | `::test_pbm55_an_outside_block_is_sized_like_one_in_a_box`, `::test_pbm55_the_settings_reach_the_outside_group_on_screen` | done |
| PB-M5.6 | A box height below one line of text is raised to the 30px floor; a usable value is not floored | `src/getmoredone/screens/plan.py` (_positive_setting, box_height) | `::test_pbm56_a_box_height_below_one_line_of_text_is_raised`, `::test_pbm56_a_usable_box_height_is_not_floored` | done |
| PB-M5.7 | A box height saved in Settings reaches the running app, without a relaunch; a refused write does not, including a refusal after a save that succeeded | `src/getmoredone/screens/settings.py` (`_hand_settings_to_app`, both callers) | `tests/test_plan_settings.py::test_a_saved_box_height_reaches_the_running_app`, `::test_a_refused_write_does_not_hand_the_app_the_unsaved_object`, `::test_a_refused_write_after_a_saved_one_does_not_reach_the_app` | done — found by the walk, the leak by the cold sweep |
| PB-M6.1 | An item row's requested height is the space the day gives those boxes — 30/45/60/90/120 minutes give 90/182/182/274/366px at a box height of 86, asserted as literals, not as an expression over the module's own constants | `src/getmoredone/screens/plan_blocks.py` (item_row_height, SLOT_ROW_GAP_PX) | `::test_pbm61_an_item_row_is_the_height_the_day_would_give_it` | done |
| PB-M6.1 | The row equals the span of the real boxes holding the task, measured from the first box's top edge to the last box's bottom edge on screen | `src/getmoredone/screens/plan_blocks.py` (item_row_height, slot_row_height) | `::test_pbm61_a_row_is_as_tall_as_the_boxes_beside_it` *(needs `mapped_windows`)* | done |
| PB-M6.1 | A row is never shorter than its own two lines of text, and from a box height of 62 up it is exactly the day's own height (63 until PD-M1.2 took a pixel off the floor) | `src/getmoredone/screens/plan_blocks.py` (ITEM_ROW_MIN_HEIGHT_PX) | `::test_pbm61_a_row_too_short_for_its_text_keeps_its_text` | done |
| PB-M6.1 | The floor is the height the row's own grid asks for, measured off the widgets rather than restated as a number | `src/getmoredone/screens/plan_blocks.py` (ITEM_ROW_MIN_HEIGHT_PX) | `::test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for` | done |
| PB-M6.1 | Every child of the row is drawn inside it and none is collapsed, at the floor and above it | `src/getmoredone/screens/plan_blocks.py` (build_item_row, grid_rowconfigure) | `::test_pbm61_every_line_of_a_row_is_drawn_inside_it` *(needs `mapped_windows`)* | done |
| PB-M6.1 | A tall row keeps its two lines together at the top instead of centring the title in the slack | `src/getmoredone/screens/plan_blocks.py` (build_item_row, grid_rowconfigure) | `::test_pbm61_a_tall_row_keeps_its_two_lines_together` *(needs `mapped_windows`)* | done |
| PB-M6.1 | The screen passes the setting it draws the day with, read off the rendered row | `src/getmoredone/screens/plan.py` (load_blocks → build_item_row) | `::test_pbm61_the_item_row_height_comes_from_the_setting` | done |
| PB-M6.1 | The row lays out at the height it asks for, against its own text | `src/getmoredone/screens/plan_blocks.py` (build_item_row, grid_propagate) | `::test_an_item_row_lays_out_at_the_height_it_asks_for` *(needs `mapped_windows`)* | done |
| PB-M6.2 | No label on an item row carries the priority score, in any form | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `::test_pbm62_an_item_row_does_not_print_its_priority_score` | done |
| PB-M6.3 | The work-block length sits in the depth bars' column and on a later grid row | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | *(test replaced by `::test_pdm12_the_length_sits_beside_the_depth_bars`)* | superseded by PD-M1.2 — a box writes the length beside the bars, not under them, so mirroring a box properly moved it |
| PB-M7.1 | A continuation chip's fill is the task's fill and its stripe is the task's stripe | `src/getmoredone/screens/plan_blocks.py` (_build_block_chip) | `::test_pbm71_a_continuation_box_is_the_colour_of_its_task` | done |
| PB-M7.2 | A continuation chip still carries the `↳` and names its task | `src/getmoredone/screens/plan_blocks.py` (_build_block_chip) | `::test_pbm71_a_continuation_box_keeps_its_arrow` | done |
| PD-M4.1 | Buffer, break and lunch resolve to one colour, in both appearance modes — asserted as an exact count of distinct values, not as two pairwise equalities | `src/getmoredone/theme.py` (block_type_colors) | `tests/test_time_block_colors.py::test_pdm41_padding_and_lunch_share_one_colour` | done |
| PD-M4.2 | A rendered break, buffer and lunch all draw their stripe in that one colour — lunch had no stripe at all before, so it had no colour to share | `src/getmoredone/screens/plan_blocks.py` (_build_lunch_chip, _build_block_chip) | `tests/test_plan_screen.py::test_pdm42_break_buffer_and_lunch_render_in_the_shared_colour` | done |
| PD-M4.3 | The shared colour meets contrast in both modes | `src/getmoredone/theme.py` (block_type_colors) | `tests/test_time_block_colors.py::test_block_type_colors_meet_contrast_in_both_themes` | done — no new test: that test already walks every key, so the shared value is covered by it |
| PD-M6.1 | A box whose task is completed draws a check, in a column of its own left of the time | `src/getmoredone/screens/plan_blocks.py` (build_slot_row, _configure_slot_columns, SLOT_CHECK_WIDTH_PX, item_is_complete, slot_is_complete) | `tests/test_plan_screen.py::test_pdm61_a_completed_task_shows_a_check_left_of_the_time` | done |
| PD-M6.2 | An open task draws no check | `src/getmoredone/screens/plan_blocks.py` (slot_is_complete) | `::test_pdm62_an_open_task_shows_no_check` | done |
| PD-M6.2 | A box holding one finished and one open task draws no check | `src/getmoredone/screens/plan_blocks.py` (slot_is_complete) | `::test_pdm63_a_box_with_one_task_still_open_shows_no_check` | done |
| PD-M6.3 | The check's colour is the theme's success token, not a literal | `src/getmoredone/screens/plan_blocks.py` (status_text_color) | `::test_pdm61_a_completed_task_shows_a_check_left_of_the_time` (second assertion) | done — the plan said `semantic_colors()["success"]`, which does not exist; `status_text_color("success")` is the token that does |
| PD-M6.4 | A continuation box of a completed task shows the check too — the box is spent either way | `src/getmoredone/screens/plan_blocks.py` (slot_is_complete, over `continued`) | `::test_pdm64_a_continuation_of_a_completed_task_shows_the_check` | done |
| PD-M6.5 | A block whose item has been deleted draws no check and does not raise | `src/getmoredone/screens/plan_blocks.py` (item_is_complete) | `::test_pdm65_a_block_whose_item_is_gone_draws_no_check` | done |
| PD-M6.5 | Padding in the box neither claims a check on its own nor withholds one from a finished task beside it | `src/getmoredone/screens/plan_blocks.py` (slot_is_complete, the `BlockType.ITEM` filter) | `::test_pdm66_a_break_in_the_box_does_not_hold_it_open` | done — added after the first version of this test put the break in a box alone, where a mutation removing the filter stayed green |
| PD-M1.1 | An item row's first line is the chip's four columns in the chip's order at the chip's widths — stripe, title, depth bars, length — read off a real chip rather than restated | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `::test_pdm11_the_item_row_uses_the_chips_column_order` | done |
| PD-M1.1 | The live Drag Schedule title width reaches the left pane, not only the day | `src/getmoredone/screens/plan.py` (load_blocks → build_item_row), `plan_blocks.py` (title_width) | `::test_pdm15_an_item_rows_title_column_follows_the_same_setting` | done |
| PD-M1.2 | The length is on the bars' own grid row, in the next column along | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `::test_pdm12_the_length_sits_beside_the_depth_bars` | done — replaces PB-M6.3 |
| PD-M1.3 | The row is still `item_row_height(span, box_height)` tall, and the floor is still what its own grid asks for (66px now, 67 before the length moved off the second line) | `src/getmoredone/screens/plan_blocks.py` (item_row_height, ITEM_ROW_MIN_HEIGHT_PX) | `::test_pbm61_an_item_row_is_the_height_the_day_would_give_it`, `::test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for` | done — the existing tests, unchanged in substance; the floor change showed up as a failing measurement |
| PD-M1.4 | Every part of the rebuilt row is drawn inside it horizontally, at the real items-column width — four columns on one line make width the risk the two-line row did not have | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it` *(needs `mapped_windows`)* | done |
| PD-M1.5 | The depth word is gone from the second line and `already blocked` is not; an item that is not blocked has no second line | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `::test_pdm14_the_second_line_is_the_blocked_marker_alone` | done |
| PD-M1.6 | The bar stack takes the title's own vertical justification -- no `n` or `s` in its sticky, and the bars fill the stack with no slack at either end | `src/getmoredone/screens/plan_blocks.py` (build_item_row, DepthBarStack) | `tests/test_plan_screen.py::test_pdm16_the_depth_bars_are_justified_like_the_text_on_the_line` | done — three versions, each reported from the screen: `n` floated the stack above the title, `s` sat it under the baseline, no sticky centres it as the label beside it is centred. Measured on the bars rather than on the frame around them, because a frame centres whatever is inside it and a frame-level assertion could not see the trailing gap -- the mutation gate caught that one green |
| PD-M2.1 | A drag of the grip moves the items column by the pointer's delta from the press, both directions | `src/getmoredone/screens/plan.py` (create_divider, on_divider_press/motion) | `::test_pdm21_dragging_the_grip_changes_the_items_column` | done |
| PD-M2.2 | Neither pane can be dragged shut: the items column stops at what one of its rows needs, the day at what one day row needs | `src/getmoredone/screens/plan.py` (items_width_floor, day_width_floor, _clamp_items_width) | `::test_pdm22_the_items_pane_cannot_be_dragged_shut`, `::test_pdm22_the_day_pane_cannot_be_dragged_shut` *(needs `mapped_windows`)* | done The cold sweep added `tests/test_plan_screen.py::test_pdm22_a_narrow_window_takes_the_width_from_the_items_pane`: the clamp ran only while the grip was held, so the window's own size could squeeze the day pane past its floor. |
| PD-M2.3 | Motion writes nothing; release writes once, counted, at the position it was released at; a motion or release that followed no press does nothing | `src/getmoredone/screens/plan.py` (on_divider_motion, on_divider_release) | `::test_pdm23_the_file_is_written_once_on_release_not_per_motion`, `::test_pdm23_a_motion_or_release_without_a_press_does_nothing` | done — the second test and the release-past-the-last-motion drag both came out of the mutation gate, which found the `_divider_from_x is None` guard and the release's own event unprovable as first written |
| PD-M2.4 | A refused write puts the width back on the app's own settings object and on the column, and says so on screen (P41) | `src/getmoredone/screens/plan.py` (on_divider_release) | `::test_pdm24_a_refused_write_leaves_the_old_width` | done |
| PD-M2.5 | The dragged width is on disk, read back with `AppSettings.load()` rather than off the object the drag mutated | `src/getmoredone/screens/plan.py` (on_divider_release) | `::test_pdm25_the_dragged_width_survives_a_rebuild` | done |
| PD-M2.6 | The grip writes the field the Settings entry is built from, so the two surfaces are one value | `src/getmoredone/screens/plan.py` (on_divider_release), `settings.py` (plan_items_col_width_var) | `::test_pdm26_the_grip_and_the_settings_field_are_one_value`, `::test_the_items_column_is_the_width_the_setting_asks_for` | done |
| PD-M2.7 | The items column is never narrower than one of its own rows, by setting, by fallback or by drag | `src/getmoredone/screens/plan.py` (items_col_width, _positive_setting) | `::test_an_unusable_items_column_width_falls_back_rather_than_collapsing`, `::test_pdm13_every_line_of_the_rebuilt_row_is_drawn_inside_it` | done — unplanned: a defect PD-M1 shipped, found while putting a number on the clamp. The 220px title-column default made a row 306px wide inside a 256px pane and the length label was laid out off the right edge, invisible, while `::test_pdm13` was green on the 80px *fallback* width it chose for itself |
| PD-M2.8 | The gap between the panes is 15px and all of it is grip | `src/getmoredone/screens/plan.py` (PLAN_DIVIDER_WIDTH_PX, PLAN_PANE_EDGE_PAD_PX, create_items_pane, create_day_pane) | `::test_pdm28_the_grip_is_the_whole_gap_between_the_panes` | done |
| PD-M2.9 | Both floors are measured against the window less `PLAN_PANE_CHROME_PX` — the grip and the two edge pads | `src/getmoredone/screens/plan.py` (_clamp_items_width) | `::test_pdm29_the_clamp_leaves_room_for_the_grip_and_the_edges` | done — four existing tests moved their patched window width up by the chrome: the behaviour changed intentionally, and a window of both floors plus 40 no longer holds 40px of slack |
| PD-M3.1 | Every item that fits is blocked, in list order, at the earliest box with nothing in it; a multi-box task takes its own boxes and the next item starts after them | `src/getmoredone/screens/plan.py` (autoload_day, first_clear_slot) | `::test_pdm31_autoload_fills_in_list_order`, `::test_pdm31_autoload_gives_a_long_task_its_own_boxes`, `::test_pdm31_a_long_task_does_not_land_on_a_later_occupied_box` | done — the plan said `first_free_slot`, the earliest box that is not *full*; a box holds four tasks, so that would have stacked four items at 08:00. Corrected to `first_clear_slot`, with the reason recorded in the plan |
| PD-M3.2 | An item already blocked today is skipped, not blocked twice | `src/getmoredone/screens/plan.py` (autoload_day) | `::test_pdm32_autoload_skips_an_item_already_blocked` | done |
| PD-M3.3 | Existing blocks are not moved, resized or deleted | `src/getmoredone/screens/plan.py` (autoload_day — `add_block_at` is the only write it makes) | `::test_pdm33_autoload_leaves_existing_blocks_untouched` | done |
| PD-M3.4 | Nothing is placed across lunch or past Day End | `src/getmoredone/screens/plan.py` (first_clear_slot, through `can_place`) | `::test_pdm34_autoload_does_not_straddle_lunch`, `::test_pdm34_autoload_does_not_run_past_the_day_end` | done |
| PD-M3.5 | The status line reports blocked / did not fit / already blocked, all three (P2) | `src/getmoredone/screens/plan.py` (autoload_day) | `::test_pdm35_autoload_reports_all_three_counts` | done The cold sweep added `tests/test_plan_screen.py::test_pdm35_the_counts_cover_the_whole_list_not_just_the_rows_shown` and `::test_pdm35_an_uncapped_run_does_not_mention_the_cap`: the counts were taken against the 60-row cap rather than the list, so items past it were in none of them. |
| PD-M3.6 | On a day with no room, nothing is written and the status says so, in the warning colour | `src/getmoredone/screens/plan.py` (autoload_day) | `::test_pdm36_a_full_day_writes_nothing` | done |
| PD-M3.7 | A refusal part-way rolls the whole run back, and the report says how far it got | `src/getmoredone/screens/plan.py` (autoload_day), `db_manager.transaction` | `::test_pdm37_autoload_is_one_transaction` | done — in `test_plan_screen.py` rather than `test_time_block_crud.py` as planned: `autoload_day` is a screen method and the rollback is only reachable through it |
| PD-M3.8 | Not offered on a non-working day — the `_require_block_day` refusal | `src/getmoredone/screens/plan.py` (autoload_day) | `::test_pdm38_autoload_refuses_a_non_working_day` | done |
| PD-M3.9 | A day with no items says so, not "no room" | `src/getmoredone/screens/plan.py` (autoload_day) | `::test_pdm3_autoload_on_an_empty_list_says_so` | done — unplanned: two different facts about the day, and one sentence for both would hide which one it is |
| PD-M5.1 | A virtual box is drawn above the first slot and below the last, every redraw, on an empty day too | `src/getmoredone/screens/plan_blocks.py` (build_virtual_slot_row), `plan.py` (load_blocks) | `::test_pdm51_a_virtual_box_sits_at_each_end`, `::test_pdm51_the_virtual_boxes_survive_a_redraw_with_blocks_on_the_day`, `::test_pdm51_a_virtual_box_says_which_end_it_is`, `::test_pdm51_a_virtual_box_is_not_a_slot` | done |
| PD-M5.2 | A drop on the top box moves Day Start back by the item's span and blocks it there | `src/getmoredone/screens/plan.py` (extend_day_for), `time_block_layout.py` (extended_day_bound) | `::test_pdm52_a_drop_above_moves_day_start_back`, `::test_pdm52_a_long_item_dropped_above_takes_the_day_back_far_enough` | done |
| PD-M5.3 | A drop on the bottom box moves Day End forward by the span and blocks it there | `src/getmoredone/screens/plan.py` (extend_day_for) | `::test_pdm53_a_drop_below_moves_day_end_forward`, `::test_pdm53_a_drop_below_does_not_renumber_the_day` | done |
| PD-M5.4 | Extending does **not** clear `plan_day_shape_unconfirmed`, and does not raise it either | `src/getmoredone/screens/plan.py` (extend_day_for — by not touching the flag; `AppSettings.save` does not write it) | `tests/test_plan_settings.py::test_pdm54_extending_the_day_is_not_confirming_it`, `::test_pdm54_an_already_confirmed_day_stays_confirmed` | done — the first version snapshotted the flag and restored it on the failure path; the mutation gate showed that line could never change anything, because no path here sets it, so it was removed rather than left as a line no test can fail on |
| PD-M5.5 | Every existing block keeps its clock time when either bound moves | `src/getmoredone/db_manager.py` (shift_all_slots), `screens/plan.py` (extend_day_for) | `tests/test_time_block_crud.py::test_pdm55_blocks_keep_their_times_when_the_day_grows`, `::test_pdm55_a_shift_of_zero_writes_nothing`, `::test_pdm55_a_block_outside_the_grid_is_not_given_a_box`, `::test_pdm55_every_date_is_renumbered_not_only_the_one_on_screen`, and `tests/test_plan_screen.py::test_pdm52_existing_blocks_keep_their_clock_times`, `::test_pdm55_a_block_on_another_date_keeps_its_clock_time` | done — in `test_time_block_crud.py` rather than `test_time_block_layout.py` as planned, because keeping the time turned out to need a *write*, not arithmetic: a block is stored by its box index, so moving Day Start back without renumbering slides the whole day earlier. The cold sweep then found that "every existing block" was being read as "every block on the date dropped on": Day Start is a single setting, so the renumber has to cover every date, and the test that asserted otherwise had pinned the defect |
| PD-M5.6 | A refused settings write leaves the day, the grid and the app as they were, and says so (P41) | `src/getmoredone/screens/plan.py` (extend_day_for, `_DayNotWritten`) | `::test_pdm56_a_refused_write_leaves_the_day_unchanged`, `::test_pdm56_a_refused_write_is_not_reported_as_a_longer_day` | done |
| PD-M5.7 | The virtual boxes are not droppable for a *block* drag — a block cannot invent a half hour | `src/getmoredone/screens/plan.py` (on_drag_release) | `::test_pdm57_a_block_drag_onto_a_virtual_box_is_refused` | done |
| PD-M5.8 | Midnight is the floor and the ceiling: the day cannot be extended past either | `src/getmoredone/time_block_layout.py` (extended_day_bound, LAST_DAY_END_MINUTES) | `tests/test_time_block_layout.py::test_pdm58_the_day_cannot_cross_midnight`, `::test_pdm58_the_ceiling_is_the_last_bound_that_yields_a_whole_box`, `::test_pdm5_the_bound_moves_by_the_whole_span`, `::test_pdm5_an_end_of_the_day_that_is_not_one_is_an_error`, and `tests/test_plan_screen.py::test_pdm5_an_item_that_would_cross_midnight_is_refused` | done — the ceiling is a Day End of **23:30**, not 24:00: a box running 23:30–24:00 would need a Day End that is not a time of day. Refused rather than clamped, because a clamped bound makes fewer boxes than the item needs |
| PD-M5.9 | A real box always wins over a virtual one, so a box flush against the Earlier box still gets its own drops | `src/getmoredone/screens/plan.py` (on_drag_release — the order of the branches) | `::test_pdm5_a_real_box_wins_over_a_virtual_one` | done — unplanned. The first version computed the edge only when no box had matched, which made the two guards mutually exclusive by construction: the precedence could not be got wrong, so this test could not fail. Both are now read and the branch order is the whole of the rule |
| PD-M5.10 | The drop gesture itself routes to the right end, not only the method | `src/getmoredone/screens/plan.py` (on_drag_release, virtual_under_pointer) | `::test_pdm5_an_item_drag_onto_a_virtual_box_extends_the_day`, `::test_pdm5_a_drop_in_the_day_but_on_no_box_still_does_nothing` | done — unplanned; without the first, the extension is only reachable by calling `extend_day_for`. The second came out of the mutation gate: a release that hit neither box returning an end of the day instead of `None` passed everything else, and would have lengthened the day for a drop on the heading |
| PD-M5.11 | Extending is refused on a non-working day, like every other write on this screen | `src/getmoredone/screens/plan.py` (extend_day_for — `_require_block_day`) | `::test_pdm5_the_day_cannot_be_extended_onto_a_non_block_day` | done — unplanned |
| PD-M7.1 | A write onto a day outside the weekday list asks first, naming the date and the days the week allows | `src/getmoredone/screens/plan.py` (_require_block_day) | `tests/test_plan_screen.py::test_pdm7_a_non_work_day_asks_before_scheduling` | done |
| PD-M7.2 | Yes writes the block | `src/getmoredone/screens/plan.py` (_require_block_day) | `::test_pdm7_a_non_work_day_asks_before_scheduling` (second half) | done |
| PD-M7.3 | No writes nothing and leaves the refusal's own sentence, weekday list included | `src/getmoredone/screens/plan.py` (_require_block_day) | `::test_pdm7_answering_no_writes_nothing` | done — no patching: conftest's recorder answers `askyesno` False already |
| PD-M7.4 | Asked once per date, not once per drop; the answer is held on the screen only | `src/getmoredone/screens/plan.py` (_work_anyway) | `::test_pdm7_the_question_is_asked_once_per_date` | done |
| PD-M7.5 | A day inside the weekday list asks nothing | `src/getmoredone/screens/plan.py` (_require_block_day) | `::test_pdm7_a_work_day_asks_nothing` | done — this is the test that found the `messageboxes` fixture leaking dialogs between tests |
| PD-M8.1 | A header button labelled Clear Day calls `clear_day`, and is not the primary colour AutoLoad uses | `src/getmoredone/screens/plan.py` (create_header) | `tests/test_plan_screen.py::test_pdm8_the_header_has_a_clear_day_button` | done — written after the method, which had no button at all: P25 |
| PD-M8.2 | Every item block on the date is removed, and the status says how many of how many | `src/getmoredone/screens/plan.py` (clear_day) | `::test_pdm8_clear_day_removes_every_item_block` | done |
| PD-M8.3 | Break and buffer blocks stay; the question and the status both account for them | `src/getmoredone/screens/plan.py` (clear_day) | `::test_pdm8_clear_day_leaves_breaks_and_buffers` | done |
| PD-M8.4 | It asks first, with the count and the date in the question; No removes nothing | `src/getmoredone/screens/plan.py` (clear_day) | `::test_pdm8_answering_no_removes_nothing` | done — no patching: conftest's recorder answers `askyesno` False already |
| PD-M8.5 | A day with no items scheduled says so and asks nothing | `src/getmoredone/screens/plan.py` (clear_day) | `::test_pdm8_a_day_with_no_items_says_so_and_asks_nothing` | done — asserted on a day that holds a break, so "nothing to remove" is about items and not about an empty day |
| PD-M8.6 | Clearing asks nothing about the weekday list | `src/getmoredone/screens/plan.py` (clear_day, no `_require_block_day`) | `::test_pdm8_clear_day_asks_nothing_about_the_weekday_list` | done |
| PD-M8.7 | One transaction, so a failure part-way leaves the day as it was | `src/getmoredone/screens/plan.py` (clear_day) | *(none)* | **not separately tested** — `delete_time_block` has no failure mode to inject without patching the connection; the transaction helper itself is covered by `tests/test_weekly_tactic_cascade.py::test_wt_m4d1_cascade_runs_in_one_transaction` |
| PD-M9.1 | A scheduled row draws the check in `scheduled_mark`, an unscheduled row the question mark in `unscheduled_mark`, both in the marker column | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | `tests/test_plan_screen.py::test_pdm9_a_scheduled_item_is_checked_and_an_unscheduled_one_questioned` | done |
| PD-M9.2 | Exactly one mark per row, either way | `src/getmoredone/screens/plan_blocks.py` (build_item_row) | same test | done — asserted as an exact count, so a row carrying both marks fails |
| PD-M9.3 | Both marks clear 4.5:1 against every priority fill in both themes | `src/getmoredone/theme.py` (scheduled_mark, unscheduled_mark) | `tests/test_time_block_colors.py::test_pdm9_the_two_marks_are_legible_on_every_fill` | done — the first pair was measured against `priority_band_colors`, which is not the table a row is filled from; against the real fills `success_strong` is 1.63:1 in the dark theme |
| PD-M9.4 | The colours are theme tokens, not literals in a screen file | `src/getmoredone/theme.py` | the screen reads them by name in `build_item_row` | done |
| PD-M10.1 | `load_blocks` flushes the redraw once after re-gridding the day pane, so a move, a resize or a padding block is on screen without waiting for an event | `src/getmoredone/screens/plan.py` (load_blocks, _flush_redraw) | `tests/test_plan_screen.py::test_pdm101_rebuilding_the_day_pane_flushes_the_redraw` | done |
| PD-M10.2 | `load_items` flushes the same way | `src/getmoredone/screens/plan.py` (load_items) | `::test_pdm102_rebuilding_the_items_pane_flushes_the_redraw` | done |
| PD-M10.3 | A press with no motion builds no drag label | `src/getmoredone/screens/plan.py` (_arm_drag_label) | `::test_pdm103_a_press_without_motion_shows_no_drag_label` | done |
| PD-M10.4 | The first motion shows the label with the dragged thing's name; a later motion moves that label rather than building another | `src/getmoredone/screens/plan.py` (on_drag_motion) | `::test_pdm104_the_first_motion_shows_the_label_and_the_second_moves_it` | done |
| PD-M10.5 | Ending a drag unplaces the label and flushes, so a release that lands on nothing still clears it | `src/getmoredone/screens/plan.py` (_end_drag) | `::test_pdm105_ending_a_drag_hides_the_label_and_flushes` | done |
| PD-M10.6 | A flush on a screen Tk has already torn down does not raise out of the `finally` it is called from | `src/getmoredone/screens/plan.py` (_flush_redraw) | `::test_pdm106_a_flush_on_a_screen_that_is_gone_does_not_raise` | done |
| PD-M10.7 | The panes repaint on the machine that reported it | — | *(not code-testable — superseded by PD-M11.8: the flush was not the cause, the rebuild around it was)* | superseded |
| PD-M11.1 | Both panes are rebuilt in place; neither leaves the grid to be rebuilt, which is what left the day pane blank until the next event | `src/getmoredone/screens/plan.py` (load_blocks, load_items) | `tests/test_plan_screen.py::test_pdm111_a_rebuild_leaves_the_day_pane_in_the_grid`, `::test_pdm111_a_rebuild_leaves_the_items_pane_in_the_grid` | done |
| PD-M11.2 | The two ends of the day are drawn outside the scrolling grid, in holders of their own, so neither can be scrolled off the screen | `src/getmoredone/screens/plan.py` (create_day_pane, load_blocks) | `::test_pdm112_the_two_ends_of_the_day_are_outside_the_scrolling_grid` | done |
| PD-M11.3 | A redraw refills those holders instead of stacking a second box in them | `src/getmoredone/screens/plan.py` (load_blocks) | `::test_pdm113_a_redraw_does_not_leave_a_second_box_at_either_end` | done |
| PD-M11.4 | A drop on an end is recognised with the pointer nowhere near the scrolling grid | `src/getmoredone/screens/plan.py` (virtual_under_pointer) | `::test_pdm114_a_drop_on_an_end_needs_no_pointer_in_the_scrolling_grid` | done |
| PD-M11.5 | A drag held at the top or bottom edge of the day's viewport scrolls the day, on its own clock, the same distance per tick on any platform | `src/getmoredone/screens/plan.py` (_day_canvas, _autoscroll_direction, _autoscroll_steps, _tick_autoscroll, _pump_autoscroll) | `::test_pdm115_the_day_canvas_is_the_scroll_frames_master`, `::test_pdm115_the_pointer_at_the_bottom_edge_scrolls_down`, `::test_pdm115_the_pointer_at_the_top_edge_scrolls_up`, `::test_pdm115_the_pointer_in_the_middle_scrolls_nothing`, `::test_pdm115_a_pointer_beside_the_day_scrolls_nothing`, `::test_pdm115_a_tick_is_the_same_distance_on_any_platform`, `::test_pdm115_a_drag_held_at_the_bottom_edge_scrolls_the_day` | done |
| PD-M11.6 | A tick with the pointer out of the edge zone, or with no drag in progress, scrolls nothing and schedules nothing | `src/getmoredone/screens/plan.py` (_tick_autoscroll) | `::test_pdm116_a_tick_outside_the_edge_zone_stops_the_scroll`, `::test_pdm116_a_tick_with_no_drag_scrolls_nothing` | done |
| PD-M11.7 | Ending a drag cancels the pending tick rather than forgetting it | `src/getmoredone/screens/plan.py` (_stop_autoscroll, _end_drag) | `::test_pdm117_ending_a_drag_cancels_the_scroll` | done |
| PD-M11.8 | On the running app: the day pane is on screen as soon as a block moves; an item dropped on Earlier and on Later lengthens the day; *Schedule anyway* shows the block it wrote | — | *(not code-testable — no test can see the screen; human review on the running app)* | partial — the repaint and the drag-edge scroll confirmed on the machine that reported them 2026-11-07; the two drops were still broken, for the reason PD-M12 gives, and are PD-M12.5 |
| PD-M12.1 | The non-work-day question is asked with the app's own dialog; `messagebox` is not on the drop path, where macOS raises `TclError` from it | `src/getmoredone/widgets/confirm_dialog.py`, `src/getmoredone/screens/plan.py` (_require_block_day) | `tests/test_plan_screen.py::test_pdm121_the_question_is_asked_by_the_app`, `::test_pdm121_the_question_names_the_answer_it_wants` | done |
| PD-M12.2 | A question that cannot be put on the screen schedules the work, logs why, and says so in the status line, once, for the gesture it happened to | `src/getmoredone/screens/plan.py` (_require_block_day, _take_unasked_note, block_item, extend_day_for) | `::test_pdm122_a_question_that_cannot_be_asked_still_schedules`, `::test_pdm122_the_note_belongs_to_the_gesture_not_to_the_day`, `::test_pdm122_the_end_of_the_day_says_it_too` | done |
| PD-M12.3 | A drop on either end of a non-work day lengthens the day and blocks the item | `src/getmoredone/screens/plan.py` (extend_day_for) | `::test_pdm123_a_drop_on_an_end_of_a_non_work_day_extends_the_day` | done |
| PD-M12.4 | No test can open a real confirm dialog; the suite records the question and answers no | `conftest.py` (_confirm_dialogs_never_block, confirms) | `::test_pdm124_a_test_cannot_open_a_real_dialog` | done |
| PD-M12.5 | On the running app: the dialog appears on a Saturday drop, *Schedule anyway* writes the block, and a drop on Earlier and on Later lengthens the day | — | *(not code-testable — nothing in this suite can build a visible window, which is how this fault reached the user)* | human review |

## PD-S — the six corrections from the built screen (2026-11-06)

Asked for against a screenshot of the finished batch, so each row is a defect
in what PD-M1 … PD-M6 shipped rather than a new feature.

| ID | Criterion | Where | Test | Status |
|---|---|---|---|---|
| PD-S1 | An item row is exactly the boxes the day will give it, at every box height the setting allows | `src/getmoredone/screens/plan_blocks.py` (ITEM_ROW_MIN_HEIGHT_PX, item_row_height) | `tests/test_plan_screen.py::test_pbm61_a_row_is_the_days_own_height_at_every_usable_box_height` | done — the 66px floor PD-M1 left was two boxes' worth at any realistic box height, so every row was drawn at it and PB-M6.1's purpose was defeated on screen while its tests stayed green: they asserted the floor, which was correct, and never that a 60-minute row is taller than a 30-minute one |
| PD-S2 | Every block ends `CHIP_RIGHT_INSET_PX` short of its right edge, in both panes, and the inset is counted into the pane's width floor | `src/getmoredone/screens/plan_blocks.py` (CHIP_RIGHT_INSET_PX, chip_column_minsizes) | `::test_pd2_every_block_ends_short_of_its_right_edge` | done |
| PD-S3 | The `NNm` length is the size of the title beside it, in both panes | `src/getmoredone/screens/plan_blocks.py` (build_item_row, _build_block_chip) | `::test_pd3_the_length_is_body_size_in_both_panes` | done — asserted against the title's own font, because the complaint is a relationship between two labels on one line, not a value |
| PD-S4 | The blocked marker is a glyph in its own column left of the depth bars, and the row is one line | `src/getmoredone/screens/plan_blocks.py` (PD_BLOCKED_TEXT, CHIP_MARKER_COLUMN, build_item_row) | `::test_pdm14_the_blocked_marker_is_a_glyph_left_of_the_depth_bars` | done — replaces `::test_pdm14_the_second_line_is_the_blocked_marker_alone`. The marker column is in `chip_column_minsizes`, so the day pane carries it too and a blocked row's bars and length stay in line with every other row |
| PD-S5 | A box holding only break or buffer is drawn on the same surface as a lunch box; an empty box is not | `src/getmoredone/screens/plan_blocks.py` (slot_is_padding, build_slot_row) | `::test_pdm42_a_padding_box_is_drawn_like_the_lunch_box` | done — PD-M4 matched the three stripes and left the box fills apart, which is the comparison a user makes. The empty-box assertion is there because without it the test passes for an implementation that fills every non-task box alike |
| PD-S6 | The word "Lunch" is the size and colour of a break's word | `src/getmoredone/screens/plan_blocks.py` (_build_lunch_chip) | `::test_pdm42_the_lunch_word_is_body_text_like_a_breaks` | done — it was 11pt muted text on the lunch surface, within a few values of its own background |

Fifteen mutations over these six, fourteen red on the first run. The fifteenth
found a dead line: with one text row and a floor equal to that row's height,
`grid_rowconfigure(1, weight=1)` could no longer change anything, because the
shortfall it was written for cannot occur. Removed rather than left as a line
no test can fail on.

## Human review required (not code-testable)

| Item | Why it cannot be a test | What is tested instead |
|---|---|---|
| Whether the brighter stripes read as brighter on this screen | A judgement about a display, not a predicate | PB-M1.3 asserts the stripe table's relative luminance exceeds the band table's, per band, in both themes |
| Whether a priority-shaded day reads as a column of priorities rather than as noise | Pixel judgement | PB-M4.1 asserts the fill is the band's and PB-M4.3 asserts every fill is readable under the text colour chosen for it |
| Whether a row that is three boxes tall reads as "this needs three boxes" rather than as an oversized row | Subjective | PB-M6.1 asserts the exact height in boxes, and that it lays out at that height on a real window |

### Walked on screen, 2026-11-06 (`./start-demo.sh`)

- **Does the grid read as a day** — **done, and the earlier answer is
  superseded.** PB-M2 was walked on screen: titles, durations and depth bars
  are drawn inside their boxes. The 2026-11-05 walkthrough row above
  ("no, and the test that said it did was wrong") describes the state before
  this batch.
- **Does a drag feel right** — **still outstanding.** PB-M5 makes a box as
  tall as the Drag Schedule box height, so the 30px grab target the question
  was about no longer exists at the default. To be re-walked; the question is
  now whether an 86px box is an easy target, not whether a 30px one is.
- **Do the item rows read at their new heights** — see the status report for
  this batch. The known consequence is stated in the plan under PB-M6: at a box
  height near the 30px floor a one-box row clips its second line.

## Pre-push review passes

Every row names the range it covered. The first version of this table did not,
and read as though the three passes over PB-M1 to PB-M5 had also covered PB-M6
and PB-M7 — which the handoff note, in the same commit, said plainly they had
not. That is the P6 failure the catalogue is about, in a document whose whole
job is to say what has been checked.

| Pass | Range | Lens | Result |
|---|---|---|---|
| `learning-qa` (cold) | `99d438f...2e4add9` | the failure-pattern catalogue (P1–P40) | 8 findings: 0 high, 3 medium, 5 below |
| `/code-review` (cold) | `99d438f...2e4add9` | correctness, reuse, simplification | 4 findings: 0 high, 2 medium, 2 below |
| `/security-review` | `99d438f...2e4add9` | injection, secrets, path traversal, deserialization | not applicable, established by grep of the added lines rather than by judgement: no SQL, no subprocess, no HTTP, no deserializer, no path handling |
| `learning-qa` (cold) | `2e4add9...HEAD` (PB-M6/PB-M7) | the same catalogue | 5 medium, 0 high, 4 below. Of the catalogue, 5 patterns genuinely applied; it said so rather than stretching the rest |
| `/code-review` (cold) | `2e4add9...HEAD` (PB-M6/PB-M7) | correctness, reuse, simplification | 5 findings: 0 high, 2 medium, 3 below |
| `/security-review` | `2e4add9...HEAD` | — | not applicable, by the same grep over this range's added lines |

Every pass was cold — given the range and the diff, not the session's
narrative. On the second range the two lenses converged on four of the same
findings, which is the evidence two lenses are for, and the useful ones came
from the two families the pattern catalogue only partly covers: test quality and
the UI-as-contract lens in `~/.claude/standards/ui-regression.md`.

Everything at medium or above was fixed with a test, each proved by mutation:
8/8 red for the PB-M1–M5 sweep fixes, 9/9 for PB-M6/PB-M7 as first written, 7/7
for the fixes to those. Everything below medium is in `BACKLOG.md` with the pass
that found it.

What the second sweep found is worth stating plainly, because three of the five
were in code and tests written in the same session that then reviewed them warm:

- The row height was 2px per box short of the day it claimed to match, and its
  acceptance test asserted the same formula the code used.
- The title collapsed to one pixel at the lowest box-height setting, and floated
  mid-row at the default on any multi-box row. Neither had a test, because every
  height assertion was `cget` and none measured a child.
- Four colour assertions and one score assertion compared the unscored tint
  with itself, because `_item(..., priority_score=N)` is recomputed to 0 by
  `create_action_item` and `_one_slot_pane` rendered with an empty
  `items_by_id`. The mutation gate came back 9/9 red over them and could not
  have caught it: mutating the lines the diff touched does not produce the
  mutant that fills every chip with the unscored tint. A green gate there was
  expected, not reassuring.
- Three of them were tests from the earlier batch — PB-M1.4's, PB-M4.1's and
  PB-M4.3's. Fixed rather than left, and said so here, because leaving them
  means this table claims those three criteria are verified when they were not.
  The fourth of that family, PB-M3.1's, passed no `items_by_id` at all, so its
  `depth` never reached the renderer.
- A further pass was not run: neither sweep produced a high-severity finding,
  which is the repo's condition for one. The re-sweep of the fix commits over
  `b6b1daa...HEAD` found no correctness defect in `src/`, one medium (the fourth
  assertion above) and five low.

The most useful finding was one neither pass reported as severe: a colour test
was passing only because this Mac is in light mode. Forced to dark it failed
against correct code, because the stripe and band tables are deliberately
identical there. On Mac Mini1, which runs dark, it would have gone red.

## Adjacent issues found, not fixed

- `src/getmoredone/screens/drag_schedule.py:115` reads the same two settings
  with its own inline fallbacks rather than through a shared helper. Flagged,
  not fixed: it is the sibling of the reader this batch added, and changing it
  is a second screen's worth of surface.
- The four size controls live under **Settings ▸ Date Increment Settings**,
  which is not where a user would look for them. Relocating a shipped control
  needs approval, so it is in `BACKLOG.md`.

---

## APC — APE quarter/month consistency (2026-11-07)

Spec and full per-criterion status report:
[`docs/spec_2026-11-07_ape_period_consistency.md`](spec_2026-11-07_ape_period_consistency.md)
§5.3. Kept there rather than inlined here because that batch (PD-*) was still
open in the tree when APC landed, and two batches editing one table is how a
status line ends up describing neither.

All of APC-M1 through APC-M6: **done**, 53 tests in
`tests/test_ape_period_consistency.py`, every behavioural claim proved by
mutation — twenty-five mutations in all, twelve for the original criteria
(§5.4 of that spec), eight for the pre-push sweep's four fixes (§5.9) and five
for the re-sweep of those fixes (§5.11). The criteria grew with the sweeps:
APC-M2.4, M4.4, M5.4 and M6.2 came from the sweep, and APC-M2.5, M2.6, M5.5,
M6.3 and M6.4 from the re-sweep over its own fix commits.

---

## AWA — APE Week Assignment, and the week's Action Items (2026-11-07)

Spec and full per-criterion status report:
[`docs/spec_2026-11-07_ape_week_actions.md`](spec_2026-11-07_ape_week_actions.md)
§6. Kept there for the same reason APC's is: the PD-* batch was again open in
this tree while AWA landed, and a status table that two batches both edit
describes neither of them.

AWA-M1 through AWA-M6: **done**, except the one criterion §3 flagged as not
code-testable — "works like the Today tab", on screen, which carries no ID
because it is a window rather than a function. That one is `not done` and stays
that way until the nine-step checklist at the end of that §6 has been walked at
the keyboard. 31 tests in
`tests/test_ape_week_actions.py`, plus one in
`tests/test_weekly_tactic_dedupe.py`, every behavioural claim proved by
mutation: 28 mutations for the batch and 10 for the sweep's fixes, each the
verbatim original line, each run alone, each file restored and
sha256-compared.

Three criteria were corrected after the pre-push sweep, and the corrections
are in §3 and §6 of the spec with their reasons:

- **AWA-M2.1** said the predicate was a plain `weekly_tactic_id = ? OR
  parent_id = ?`. An item can hold a different tactic in each column, and a
  plain `OR` listed that one item under both. `weekly_tactic_id` now wins when
  it is set.
- **AWA-M2.3** asserted the predicate had one home while it had two: the scan
  covered `screens/` and `vps_manager.py`, and the second copy was in
  `weekly_tactic_maintenance._child_count`, which feeds the dedupe that deletes
  a duplicate tactic — and had already drifted. The scan now covers all of
  `src/getmoredone`. This was the batch's one high finding and it was found by a
  cold pass, not by the context that wrote the test.
- **AWA-M5.4** did not require the create's cascade report to be reported.
  Thirteen other screens report it; this one dropped it, so an item saved
  un-re-filed looked identical to one that was filed.

**AWA-M4.1** gained two tests rather than a correction: nothing checked that
the screen reads the user's `first_day_of_week` at all, and nothing exercised
`_existing_week_starts`, whose P2 claim is that a tactic filed against an older
week stays reachable in the picker.

Two of those mutations did not come back red first time, and both are recorded
in §6's mutation table:

- `test_awam56` was a harness error on my side (the source holds real curly
  quotes, the mutation script held escapes) — the test was fine.
- `test_awam25` was genuinely vacuous. It deleted the tactic with an ordinary
  `DELETE`, but both link columns are `ON DELETE SET NULL` and the connection
  runs with `PRAGMA foreign_keys = ON`, so the delete cleared the link itself
  and the test asserted an outcome the schema already guaranteed. Reason given
  before rewriting: (c) the test was over-specified or vacuous. It now seeds
  the dangling link with foreign keys off and asserts the dirty state really is
  dirty before asserting the helper's answer.
