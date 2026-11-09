# Spec Coverage — Plan day → Google Calendar export (2026-11-08)

Plan: [`docs/implementation_plan_2026-11-08_plan_calendar_export.md`](implementation_plan_2026-11-08_plan_calendar_export.md)

Suite: the files this change touches plus their neighbours —
`tests/test_calendar_export.py` (40), `tests/test_google_calendar_export_calls.py`
(18), `tests/test_plan_screen_calendar_export.py` (34),
`tests/test_time_block_crud.py` (+7), `tests/test_time_block_schema.py` (+4),
and the adjacent `tests/test_plan_screen.py`, `tests/test_plan_settings.py`,
`tests/test_time_block_layout.py`, `tests/test_time_block_colors.py`,
`tests/test_google_calendar_paths.py`, `tests/test_first_run.py`,
`tests/test_database.py`, `tests/test_ui_presence.py`. Run under
`GETMOREDONE_NO_MAPPED_WINDOWS=1`; see "Verification" below for the result.

The **full suite was not run locally** — the machine's own rule. No new test
takes the `mapped_windows` fixture, so the mapped-window count
`tests/test_ci_contract.py` asserts against `CLAUDE.md` and `conftest.py` does
not move.

No test in this batch reaches the network. Every exporter test passes a fake
client; every Google-layer test passes a fake `service`; every UI test replaces
`PlanScreen.calendar_client_factory`.

## Verification re-run, 2026-11-08 (after PD-M14 landed)

The whole set — the three CE files, the two time-block files,
`test_plan_screen.py`, `test_plan_settings.py`, `test_time_block_layout.py`,
`test_time_grid.py` — now that `screens/plan.py` imports again: **9 failed,
537 passed, 17 skipped.** This batch's own five files, run alone: **150
passed.** The nine failures are PD-M14's (the outside-group tests and
`test_pdm54_*`), in another session's in-progress area and in no file this
batch touches. Not fixed from here.

The fourth cold pass is still owed and has not run.

## Acceptance criteria

| Spec ID | Description | Implementation | Test | Status |
|---|---|---|---|---|
| CE-M1.1 | `time_blocks.calendar_event_id TEXT` **and `calendar_event_calendar_id TEXT`**, per-column guarded migration | `src/getmoredone/database.py` (`initialize_schema` CREATE TABLE, `_run_migrations` column tuple) | `tests/test_time_block_schema.py::test_cem11_migration_adds_calendar_event_id_idempotently`, `::test_cem11a_a_fresh_database_declares_calendar_event_id_on_its_own`, `::test_cem11b_migration_adds_the_event_calendar_idempotently`, `::test_cem11c_a_fresh_database_declares_the_event_calendar_on_its_own` | done |
| CE-M1.2 | `TimeBlock.calendar_event_id` and `.calendar_event_calendar_id`; defensive row read for both; `create_time_block` carries them | `src/getmoredone/models.py` (`TimeBlock`), `src/getmoredone/db_manager.py::_row_to_time_block`, `::create_time_block` | `tests/test_time_block_crud.py::test_cem12_calendar_event_id_round_trips`, `::test_cem12_a_row_without_the_column_still_reads`, `tests/test_time_block_crud.py::test_cem12b_the_event_calendar_round_trips`, `::test_cem12c_clearing_the_id_clears_the_calendar_with_it` | done, **narrowed** — see Deviations |
| CE-M1.3 | One narrow writer: `set_block_calendar_event_id` touches those two columns and `updated_at` only, and reports whether a row was written | `src/getmoredone/db_manager.py::set_block_calendar_event_id` | `tests/test_time_block_crud.py::test_cem13_recording_an_event_id_leaves_the_block_where_it_was`, `::test_cem13_recording_an_event_id_touches_one_block`, `::test_cem13_an_edit_does_not_erase_the_event_id`, `tests/test_calendar_export.py::test_cem13a_recording_an_id_for_a_block_that_is_gone_says_so` | done |
| CE-M2.1 | `build_export_plan` is pure; skips are counted and named | `src/getmoredone/calendar_exporter.py::build_export_plan` | `tests/test_calendar_export.py::test_cem211_an_unplaced_block_is_skipped_and_counted`, `::test_cem212_every_placed_block_gets_one_entry`, `::test_cem213_a_block_with_an_event_id_plans_an_update_not_a_create`, `::test_cem214_a_block_with_no_length_is_skipped_and_counted`, `::test_cem215a_a_day_that_cannot_be_parsed_counts_every_block`, `::test_cem216_a_block_the_day_draws_outside_the_grid_is_not_exported`, `::test_cem216a_a_block_under_the_lunch_hour_is_not_exported` | done, **extended** — see Deviations |
| CE-M2.2 | The event is called what the screen calls it; one owner for the rule | `src/getmoredone/time_block_layout.py::block_title`, `src/getmoredone/screens/plan_blocks.py::_block_title` (delegates) | `tests/test_calendar_export.py::test_cem221_every_branch_of_the_title_rule_names_a_block`, `tests/test_plan_screen_calendar_export.py::test_cem221a_an_event_is_titled_what_the_day_draws_on_the_block` | done |
| CE-M2.3 | Clock times in the user's timezone; `planned_minutes` is the duration | `src/getmoredone/calendar_exporter.py::build_export_plan`, `src/getmoredone/google_calendar.py::_get_local_timezone` | `tests/test_calendar_export.py::test_cem231_a_0930_block_exports_at_0930_local`, `::test_cem232_the_items_next_step_travels_with_the_event`, `tests/test_calendar_export.py::test_cem215_an_unreadable_stored_clock_time_no_longer_stops_a_block`, `tests/test_plan_screen_calendar_export.py::test_cem441c_the_exported_time_is_the_box_the_screen_draws` | done |
| CE-M2.4 | `export_day(...)` takes an injected client | `src/getmoredone/calendar_exporter.py::export_day` | `tests/test_calendar_export.py::test_cem241_export_day_uses_the_client_it_was_given`, `::test_cem242_the_calendar_id_is_passed_to_every_call` | done, **renamed test** — see Deviations |
| CE-M2.5 | Idempotent: a second export updates and creates nothing | `src/getmoredone/calendar_exporter.py::export_day`, `::_update` | `tests/test_calendar_export.py::test_cem251_a_second_export_updates_and_creates_nothing`, `::test_cem252_a_moved_block_updates_its_own_event`, `::test_cem253_an_event_deleted_in_google_is_made_again`, `tests/test_calendar_export.py::test_cem255_changing_the_export_calendar_moves_the_event`, `::test_cem255a_the_move_is_not_made_when_the_calendar_is_the_same`, `::test_cem255b_a_row_from_before_the_column_is_read_as_the_default`, `::test_cem255c_an_event_already_gone_from_the_old_calendar_still_moves`, `::test_cem255d_a_move_that_cannot_delete_keeps_the_old_id` | done |
| CE-M2.6 | Orphan sweep, and nothing else; an unmarked event is never deleted | `src/getmoredone/calendar_exporter.py::_sweep_orphans` | `tests/test_calendar_export.py::test_cem261_an_event_for_a_deleted_block_is_removed`, `::test_cem262_an_unmarked_event_is_never_deleted` (adversarial, P7), `::test_cem263_a_failed_block_keeps_its_event`, `::test_cem264_a_duplicate_event_for_a_live_block_is_removed`, `::test_cem265_a_sweep_that_cannot_list_is_reported_not_assumed_empty`, `::test_cem266_a_block_the_export_skipped_keeps_its_event`, `::test_cem283_a_cleared_day_still_removes_the_events_it_had`, `tests/test_plan_screen_calendar_export.py::test_cem433a_clearing_a_day_takes_its_events_off_the_calendar`, `tests/test_calendar_export.py::test_cem264_a_block_deleted_mid_export_takes_its_new_event_with_it`, `::test_cem264a_a_block_deleted_after_its_update_has_its_event_swept`, `::test_cem264b_a_failure_to_take_the_event_back_is_reported` | done |
| CE-M2.7 | One block's failure is one block's failure; an id only from the response | `src/getmoredone/calendar_exporter.py::export_day`, `::_create` | `tests/test_calendar_export.py::test_cem271_a_failed_block_does_not_stop_the_rest`, `::test_cem272_a_failed_create_leaves_the_block_unexported`, `::test_cem273_a_create_that_returns_no_id_is_a_failure` | done |
| CE-M2.8 | An empty day is not a success | `src/getmoredone/calendar_exporter.py::ExportOutcome.summary_line`, `::export_day` | `tests/test_calendar_export.py::test_cem281_an_empty_day_reports_nothing_to_export`, `::test_cem282_a_day_exports_only_its_own_blocks`, `::test_cem283_a_cleared_day_still_removes_the_events_it_had`, `::test_cem283a_a_day_with_nothing_at_either_end_says_nothing_to_export` | done |
| CE-M3.1 | `calendar_id` parameter, default `primary`, on every call | `src/getmoredone/google_calendar.py::create_event`, `::update_event`, `::delete_event`, `::list_day_events` | `tests/test_google_calendar_export_calls.py::test_cem311_the_calendar_id_reaches_every_call`, `::test_cem311a_the_default_calendar_is_still_primary` | done |
| CE-M3.2 | `list_day_events`, marker-filtered, `singleEvents=True`, paginated | `src/getmoredone/google_calendar.py::list_day_events` | `tests/test_google_calendar_export_calls.py::test_cem321_two_pages_are_both_returned`, `::test_cem322_only_our_own_marked_events_are_requested` | done |
| CE-M3.3 | The marker is written on create and preserved on update | `src/getmoredone/google_calendar.py::create_event`, `::update_event` | `tests/test_google_calendar_export_calls.py::test_cem331_create_writes_the_block_marker`, `::test_cem331a_an_event_with_no_marker_asked_for_carries_none`, `::test_cem332_update_preserves_the_marker` | done |
| CE-M3.4 | Retry 429/5xx with backoff, never 4xx; transport timeout | `src/getmoredone/google_calendar.py::_with_retry`, `::_status_of`, `::_build_service`, `::_transport_errors` | `tests/test_google_calendar_export_calls.py::test_cem341_a_503_is_retried_then_succeeds`, `::test_cem342_a_404_is_not_retried_and_says_the_event_is_gone`, `::test_cem342a_a_403_is_not_retried`, `::test_cem342b_a_retryable_status_that_runs_out_is_reported`, `::test_cem343_every_event_call_goes_through_the_retry_helper` (AST, exact count), `::test_cem344_the_transport_carries_a_timeout`, `::test_cem345_a_timeout_is_retried_then_succeeds`, `::test_cem345a_a_timeout_that_runs_out_of_attempts_is_reported`, `::test_cem345b_a_disk_error_is_not_mistaken_for_a_network_one` | done |
| CE-M2.6b | The sweep checks both halves of the marker: another day's event is never deleted, and an `extendedProperties` that is not the documented shape is read without raising | `src/getmoredone/calendar_exporter.py::_marker_date_of`, `::_private_properties`, `::_sweep_orphans` | `tests/test_calendar_export.py::test_cem266_an_event_marked_for_another_day_is_never_deleted`, `::test_cem266a_an_event_with_our_marker_and_no_date_is_still_swept`, `::test_cem266b_an_event_whose_properties_are_not_a_dict_is_ignored` | done — added after approval |
| CE-M3.4b | A retried `insert` cannot make a second event (own event id in the body, 409 reads it back); a 403 is retried only for a rate-limit reason; the payload's `dateTime`/`timeZone` strings are asserted | `src/getmoredone/google_calendar.py::_new_event_id`, `::_reasons_of`, `::_is_retryable`, `::create_event` | `tests/test_google_calendar_export_calls.py::test_cem347_the_insert_body_carries_the_wall_clock_times_and_a_real_zone`, `::test_cem347a_the_update_body_carries_them_too`, `::test_cem348_a_lost_insert_response_does_not_make_a_second_event`, `::test_cem348a_the_insert_carries_one_id_across_its_retries`, `::test_cem348b_two_creates_do_not_share_an_id`, `::test_cem349_a_403_rate_limit_is_retried_then_succeeds`, `::test_cem349a_a_403_that_is_a_real_refusal_is_not_retried`, `::test_cem349b_an_unreadable_error_body_leaves_the_status_to_decide` | done — added after approval |
| CE-M3.5 | `reminders` is the caller's choice: the meeting dialog keeps its popup, the Plan export inherits the user's own calendar setting | `src/getmoredone/google_calendar.py::create_event` (`DEFAULT_REMINDERS`, `INHERIT_REMINDERS`), `src/getmoredone/calendar_exporter.py::_create` | `tests/test_google_calendar_export_calls.py::test_cem35_the_caller_decides_the_reminders`, `tests/test_calendar_export.py::test_cem35_an_exported_block_inherits_the_user_s_own_reminders` | done — added after approval |
| CE-M4.1 | The button: header, secondary style, disabled immediately, re-enabled after | `src/getmoredone/screens/plan.py` (`btn_export_calendar`, `export_day_to_calendar`, `_report_export`) | `tests/test_plan_screen_calendar_export.py::test_cem411_the_button_disables_before_the_work_starts`, `::test_cem412_the_button_is_re_enabled_when_the_worker_finishes`, `::test_cem412a_a_second_click_while_running_does_nothing`, `::test_cem441a_the_export_button_is_not_a_second_primary` | done |
| CE-M4.2 | Background thread, honest status from the counts | `src/getmoredone/screens/plan.py::export_day_to_calendar`, `::_poll_export`, `::_report_export`, `::_still_on_screen`, `::destroy`; `calendar_exporter.ExportOutcome.summary_line` | `tests/test_plan_screen_calendar_export.py::test_cem421_the_status_line_reports_the_real_counts`, `::test_cem422_a_failing_export_sets_an_error_status`, `::test_cem422a_an_exception_from_the_client_is_reported_not_swallowed`, `::test_cem413_the_result_is_collected_by_a_callback_the_tk_thread_scheduled`, `::test_cem414_a_worker_that_vanishes_still_gives_the_button_back`, `::test_cem453_the_status_line_is_built_from_the_outcome_object`, `tests/test_calendar_export.py::test_cem422_the_summary_line_names_every_skip`, `::test_cem422a_a_failure_is_named_in_the_summary_line`, `tests/test_plan_screen_calendar_export.py::test_cem423_a_screen_that_is_gone_is_not_written_to`, `::test_cem424_destroying_the_screen_cancels_the_poll`, `::test_cem413a_pending_tk_finalizers_run_before_the_worker_starts`, `::test_cem425_a_result_that_lands_between_the_two_reads_is_not_called_a_failure` | done, **implemented as a poller** — see Deviations |
| CE-M4.3 | Prerequisites refused clearly, before any work | `src/getmoredone/screens/plan.py::export_day_to_calendar`, `::_finish_export_refusal` | `tests/test_plan_screen_calendar_export.py::test_cem431_missing_credentials_refuses_with_the_setup_message`, `::test_cem432_missing_libraries_refuses`, `::test_cem433_an_empty_day_runs_the_export_and_says_nothing_was_there`, `::test_cem433a_clearing_a_day_takes_its_events_off_the_calendar`, `::test_cem434_an_unconnected_account_refuses_rather_than_opening_a_browser`, `::test_cem435_a_worker_that_cannot_be_started_gives_the_button_back` | done, with **a third refusal the plan did not list** and **an empty day no longer among them** — see Deviations |
| CE-M4.4 | Reachable from the real screen; the selected date is what is exported | `src/getmoredone/screens/plan.py` (header pack, `export_day_to_calendar`) | `tests/test_plan_screen_calendar_export.py::test_cem441_the_header_holds_the_export_button_wired_to_the_export`, `::test_cem442_the_exported_date_is_the_selected_date`, `::test_cem452_an_item_block_exports_under_the_items_title`, `tests/test_plan_screen_calendar_export.py::test_cem444a_the_screens_own_client_is_built_non_interactively`, `::test_cem444b_a_client_that_needs_sign_in_reports_it_and_re_enables`, `::test_cem444c_a_second_screen_cannot_export_the_same_day`, `::test_cem444d_a_failed_export_gives_the_day_back` | done |
| CE-M4.5 | No UI test touches the network; the default is the real client | `src/getmoredone/screens/plan.py::calendar_client`; `src/getmoredone/app_settings.py` (`plan_export_calendar_id`) | `tests/test_plan_screen_calendar_export.py::test_cem451_the_screen_uses_its_injected_client_factory`, `::test_cem451a_without_a_factory_the_real_client_is_what_would_be_built`, `::test_cem443_the_configured_calendar_is_the_one_written_to`, `::test_cem443a_a_blank_calendar_setting_falls_back_to_primary` | done |

## Deviations from the approved plan

Every one of these was a change the build forced, not a descope. The criteria
above are all met; these record where the shape differs from the plan's words.

1. **CE-M1.2 narrowed: `update_time_block` does *not* carry the column.** The
   plan said "`create_time_block` / `update_time_block` carry it". Mutation
   testing found the test that claimed to prove it could not fail — and
   following that up showed the behaviour was wrong, not just untested. A
   screen edit (drag, resize, relabel) passes a `TimeBlock` object the screen
   loaded *before* an export, whose `calendar_event_id` is `None`; carrying
   that `None` into the UPDATE would erase the id of a live event and orphan
   it on the calendar. `set_block_calendar_event_id` (CE-M1.3) is now the sole
   writer, and `tests/test_time_block_crud.py::test_cem13_an_edit_does_not_erase_the_event_id`
   asserts the new behaviour.
2. **CE-M2.1 extended: a third skip counter.** `skipped_bad_time`, for a block
   whose stored `start_time` cannot be parsed or whose date string cannot be
   read. The plan named two counters; a block in that state existed and was
   neither exportable nor accounted for, and silently dropping it is exactly
   what P2 forbids.
3. **`ExportOutcome` is a dataclass, not the dict the plan listed**, with
   `recreated`, `errors`, `as_dict()` and `summary_line()` added to the keys
   CE-M2.4 named. The screen reads the object; `as_dict()` keeps the
   plan's reporting shape available.
4. **The orphan sweep keeps events for *skipped* blocks, not only failed
   ones.** The plan's sweep deleted "an event whose `gmd_block_id` no longer
   exists". That is still the rule, but "exists" is decided against the day's
   blocks: a block the export skipped (unplaced, no length, unreadable time)
   is still a block, so its event stays. Deleting it would be a run that did
   not confirm the day removing something on the strength of not knowing.
   `::test_cem266_a_block_the_export_skipped_keeps_its_event`.
5. **CE-M4.2's thread hands back by polling, not by `after()` from the
   worker.** The plan said "the `run_calendar_import_now` shape", which
   schedules `after(0, ...)` from the worker thread. That pattern wedged the
   test run: Tk is not thread-safe and `after` is not an exception, and a
   process with no `mainloop` running hangs on it. The worker now leaves its
   result in an attribute and the Tk thread collects it
   (`_poll_export`, `EXPORT_POLL_INTERVAL_MS = 100`).
   `::test_cem413_the_result_is_collected_by_a_callback_the_tk_thread_scheduled`
   asserts the hand-off direction.
6. **Two of the plan's test names changed.**
   `test_cem241_export_day_never_constructs_the_real_manager` →
   `test_cem241_export_day_uses_the_client_it_was_given`: the negative was not
   provable without patching the class, and the positive is what the seam is
   for. `test_cem322_only_our_marker_is_requested` →
   `::test_cem322_only_our_own_marked_events_are_requested`.
7. **A guard the plan implied was removed as dead code.** `_sweep_orphans`
   carried a `failed_block_ids` set; mutation testing showed deleting it
   changed no outcome, because the "this run confirmed nothing for this block"
   branch already covers failures. Kept-as-dead-code is worse than removed:
   it reads as a second rule that is not there.

8. **An empty day is not refused.** The plan grouped "no blocks planned"
   with the missing-credentials and missing-library refusals, under CE-M4.3,
   and it was built that way. A cold review pass found that this made CE-M2.6
   unreachable in the one case it exists for: the day whose blocks have all
   been deleted is the day whose events have to come off the calendar, and the
   sweep inside `export_day` is the only code that removes them. The export
   now always runs; the exporter reports an empty day itself, deletions
   included, and the status line a user reads for a genuinely empty day is
   unchanged.

9. **The status line left the header, and the button is 150px not 160px.**
   The plan put the button in the header beside the other day-wide actions,
   which it is. What the plan did not account for is that every widget in that
   header is packed with a fixed width and the status label was packed last
   with no `expand`: measured, the header asked for **1203px inside a 1200px
   window** (1180 after its own padx), so Tk gave the label nothing and a
   label squeezed to zero is never mapped. The one channel this screen reports
   anything through would have been invisible at the window's default size,
   for the feature whose strings are the longest it produces. The label now has
   its own grid row under the body, where no further button can squeeze it, and
   the button was trimmed to 150px so the header itself fits (1172 ≤ 1180).
   `app.py` gained `DEFAULT_GEOMETRY` / `DEFAULT_WINDOW_WIDTH_PX` so the test
   reads the window size rather than carrying a second copy of it (P4).

10. **A third prerequisite refusal, which the plan did not list.**
    `has_credentials()` only says `credentials.json` exists. The real client
    authenticates in `__init__` — `flow.run_local_server`, no timeout, waiting
    on a browser consent — and the export calls it **on the worker thread**. A
    user who had put `credentials.json` in place but never connected, and then
    closed the consent tab, was left with a disabled button and a status
    reading "Exporting…" that nothing would ever clear. The export now refuses
    on `check_token_validity()["exists"]` with
    `calendar_dialog.not_connected_message()`, which names the file it checked.
    `exists`, not `valid`: an expired token that can be refreshed reports
    `valid` False and needs no browser.

    **This was not enough, and the third cold pass found why.** A token that
    exists and cannot be *used* — revoked, corrupt, unrefreshable — passes this
    refusal and reaches exactly the wedge it was written to prevent. The client
    the export builds is now non-interactive (deviation 11), which closes the
    case rather than narrowing it.

11. **The export's client cannot sign in at all.** Not in the plan, which
    assumed the prerequisite checks were sufficient. `GoogleCalendarManager`
    takes `allow_interactive`, default `True` so the calendar dialog on the
    main thread is unaffected, and `PlanScreen.calendar_client` passes `False`:
    reaching the sign-in branch then raises `AuthenticationRequired`, which the
    worker reports as `not_connected_message()`. Nothing on a background thread
    can now open a browser or read from a console that a double-clicked app
    does not have.

12. **Every exported time is derived from the box, not read from the row.** The
    plan said "`start_time` → a timed event", which is what was built and was
    wrong: a block's box is stored relative to Day Start, so moving Day Start
    re-times the whole day on read and leaves `start_time` behind —
    `PlanScreen.on_settings_saved` calls those columns "a record, not the
    truth" and deliberately writes nothing. The export now computes each start
    with `times_for_slot` from the `DayBounds` the screen is drawing, and the
    screen hands those bounds to the worker. In the same change, "on the grid"
    became `build_day_grid(...).outside` rather than `slot_index is None`,
    because the grid is what decides: Day End moved past a block, or lunch
    moved over it, both put it under *Outside the day* on screen while the old
    check still exported it.

    One test changed with it, under rule (b) — the behaviour changed
    intentionally: `test_cem215` asserted that an unreadable stored clock time
    skipped the block and counted it. It no longer can, because the stored
    column is not read; the counter it named now guards an unparseable day
    string, which `test_cem215a` covers.

13. **A block's event id records the calendar it is on.** Also not in the plan.
    `plan_export_calendar_id` is a setting, and an event id means nothing
    except against the calendar it was created on, so the plan's single column
    was not enough to re-find an event after that setting changed.
    `calendar_event_calendar_id` is written only together with the id, read as
    `primary` when NULL (which is what rows from the first version of the
    export mean), and a mismatch makes the export move the event: delete on the
    old calendar, create on the configured one, counted as `moved`.

14. **Two counters the plan's status line did not have.** `vanished` for a
    block deleted while the export was in flight, and `moved` for deviation 13.
    Both are in `summary_line()`, because a count that is neither a success nor
    a failure still has to be said (P2).

15. **One export per day per database, not per screen.** The plan's re-entry
    guard was `self._export_running`. `App.show_plan` builds a new `PlanScreen`
    on every navigation, so that guard does not survive leaving the screen and
    coming back. The marker is now a module-level set keyed by
    `(database path, day)`, claimed under a lock before the worker starts and
    released in its `finally`.
16. **The insert carries an event id of our own.** The plan said nothing about
    idempotency, and `events().insert` is not idempotent — the retry the plan
    *did* ask for (CE-M3.4) is what made this reachable. Every
    `create_event` now sends a base32hex id built once per call, so a retry
    after a lost response is answered with a 409 and that event is read back
    rather than a second one being created. This changes the meeting dialog's
    behaviour too, which is the point: it had no sweep to clean up after
    itself.
17. **A 403 is not always a refusal.** The plan's retry rule was "429 and the
    5xx family". The Calendar API reports rate limits as a 403 with a reason
    in the body, so the reason is now read — defensively, because the body may
    be bytes, text, absent or not JSON — and four reasons are treated as
    retryable while every other 403 stays permanent.
18. **The reminders are the caller's to choose.** Not in the plan at all.
    `create_event` had hard-coded a ten-minute popup with `useDefault: False`
    for every caller, so an exported day of blocks would have overridden the
    user's own calendar reminder setting once per block. The dialog keeps the
    popup; the export asks for `{'useDefault': True}`.

## Cold review passes

Three cold passes, no implementation context any time, as `CLAUDE.md`
requires: the budget asks for one, and for a further one in a different
failure family when a pass produces a high-severity finding — which all three
of these did. A fourth is therefore owed and is **not** run (see
"Verification").

### Pass 1 — failure patterns (`learning-qa`)

Eleven findings: **1 high, 3 medium, 7 low**. The high and the three mediums
are fixed in this batch; the seven low findings are filed as CE-A5 to CE-A11
in `BACKLOG.md`, because the sweep budget does not fix below-medium findings
in-loop.

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | High | The empty-day pre-flight refusal made the orphan sweep unreachable: a cleared day's events could not be removed by any code path, under a status line saying there was nothing to export | Refusal removed (Deviation 8); `test_cem433a`, `test_cem283` |
| 2 | Medium | `ExportOutcome.summary_line` returned "Nothing to export" whenever `blocks_seen` was 0, discarding deletions *and failures* from the same run | Line now reports deletions and failures on a day with no blocks; `test_cem283`, `test_cem283a` |
| 3 | Medium | `_with_retry` caught `HttpError` only, so the transient class the new 30s timeout creates — timeouts, DNS, connection resets — reached the caller unretried (P1, P5) | `_transport_errors()` / `RETRYABLE_TRANSPORT_ERRORS`, named rather than `OSError` so a disk error is not retried as a network blip; `test_cem345`, `test_cem345a`, `test_cem345b` |
| 4 | Medium | Neither `_report_export` nor `_finish_export_refusal` checked that the screen still existed, and `destroy` did not cancel the queued poll — navigating away mid-export raised inside a Tk callback (P15) | `_still_on_screen()` on both reporters, `destroy()` override cancelling `_export_poll_id`; `test_cem423`, `test_cem424` |

Six further mutations prove the four fixes, bringing the batch to **48**: the
pre-flight refusal put back (red at `test_cem433a`), `summary_line` reading
`blocks_seen` alone (red at `test_cem283`), an empty retryable-transport tuple
(red at `test_cem345`), `[OSError]` in its place (red at `test_cem345b`),
`_still_on_screen` returning `True` (red at `test_cem423`), and `destroy`
reduced to `super().destroy()` (red at `test_cem424`).

The same pass noted, and this record keeps, two things that are not findings
against the code: `FakeCalendar.list_day_events` in the tests ignores the
marker-date filter it is given, so no test would catch that filter being
dropped (now CE-A13); and the `gmd_block_date` marker is written on create but
not on update, which becomes a live bug the day a block can be moved to
another day.

### Pass 2 — UI contract and test quality

Seven findings: **1 high, 4 medium, 2 low**. The high and all four mediums are
fixed, and so is CE-A5, which this pass re-rated: filed as low after pass 1 on
the reading that the window costs one wasted poll, it in fact reports a
successful export as a worker that vanished. The two low findings are CE-A12
and CE-A15 in `BACKLOG.md`, with the pass's test-hygiene notes as CE-A14.

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | High | The header asked for 1203px inside a 1200px window, so the status label — packed last, fixed widths everywhere else — got zero width and was never mapped. The export's only output channel, invisible at the default size | Status label moved to its own grid row, button trimmed to 150px (Deviation 9); `test_cem441b` |
| 2 | Medium | `has_credentials()` says nothing about `token.pickle`, and the real client authenticates in `__init__`: a never-connected user who closed the browser consent was left disabled under "Exporting…" forever | Third refusal on `check_token_validity()` (Deviation 10); `test_cem434` |
| 3 | Medium | Six statements including `Thread(...).start()` ran outside the `try`, with the button already disabled and nothing scheduled to re-enable it | The guard now covers the whole method; `test_cem435` |
| 4 | Medium | `test_cem221`'s headline assertion compared `block_title()`'s output to `block_title()`'s output through a one-line delegation — true for any implementation, broken ones included | Tautology removed, literals kept, and the real producer/consumer contract asserted against the text Tk draws; `test_cem221a` |
| 5 | Medium | The `(item no longer exists)` branch was claimed covered and was not: the case that claimed it had a label, so it returned through `block.label` | Fifth case, the branch asserted; `test_cem221` |
| 6 | Low | `test_cem423`'s only assertion (`_export_running is False`) is set *before* the liveness guard, so it passed with the guard deleted | Recorders on `set_status` and `configure`, asserted empty |
| 7 | Low | The `⤴` glyph has no font fallback guarantee on Windows | Filed as CE-A12 |

Eight further mutations prove these fixes, bringing the batch to **56**: the
status label put back in the header and the button put back to 160px (both red
at `test_cem441b`), the token check deleted (red at `test_cem434`), the thread
start moved back outside the guard (red at `test_cem435`), the orphaned-item
title returning blank (red at `test_cem221`), the day pane no longer calling
the shared title rule (red at `test_cem221a`), `_still_on_screen` returning
`True` (red at `test_cem423`, which it was not before), and the poller giving
up on its first read of `None` (red at `test_cem425`).

**One claim in that pass is wrong, recorded so it is not repeated:** it reads
`delete_action_item` as leaving an item's time blocks behind, which would make
`(item no longer exists)` reachable by deleting a blocked item. It is not —
`time_blocks.item_id` is `REFERENCES action_items(id)` with no `ON DELETE`
clause and the connection runs `PRAGMA foreign_keys = ON`, so that delete
raises instead. The branch is for a row orphaned some other way, which is why
the new case hands the state straight to the pure function rather than faking
it into SQLite.

### Pass 3 — state, concurrency and document accuracy

Ten findings: **1 blocker, 2 medium, 1 minor, 4 documentation, 2 recorded
without a severity of their own**. The blocker and both mediums are fixed, as
is the fourth finding (`cestate-04`), which this record rates medium on the
same reading the pass gave it: the events it loses are unreachable by any later
run. The minor one is filed as CE-A16; the documentation findings are corrected
in this document, `BACKLOG.md`, `CHANGELOG.md`, `docs/USER_GUIDE.md`,
`docs/google-calendar-setup.md`, `docs/DOCUMENTATION_INDEX.md` and the handoff
note.

| # | Severity | Finding | Fix |
|---|---|---|---|
| cestate-01 | **Blocker** | The screen's token refusal only covers a *missing* token file. A token that exists and cannot be loaded or refreshed — revoked access, a changed password, a corrupt pickle — falls through to `flow.run_local_server` and then to `input()`, both on the export's worker thread, both waiting forever: the button stays disabled under "Exporting…" until the app is killed. Four documents asserted this could not happen | `GoogleCalendarManager(allow_interactive=False)` raises the new `AuthenticationRequired` instead of starting the consent flow; `PlanScreen.calendar_client` builds its client that way, and `work()` reports `not_connected_message()`. `test_cem346`, `::_346a`, `test_cem444a`, `::_444b` |
| cestate-02 | Medium | The export timed every block from `block.start_time`, which the screen's own docstring calls "a record, not the truth" — a block's box is stored relative to Day Start, so moving Day Start re-timed the day on screen and left the stored columns behind. A day drawn from 10:00 went onto other people's calendars from 08:00. Worse, "on the grid" was `slot_index is not None`, while the screen decides it with `build_day_grid`: blocks the day draws under *Outside the day* — Day End moved past them, or lunch moved over them — were exported at those stale times, which the user guide promises are skipped | Every start time is now derived with `times_for_slot` from the `DayBounds` the screen is drawing, and `off_grid` comes from `build_day_grid(...).outside`. The screen captures `self.bounds` and hands it to the worker (frozen, so it cannot change underneath). `test_cem215`, `::_215a`, `::_216`, `::_216a`, `test_cem441c` |
| cestate-03 | Medium | `_export_running` is an attribute of one `PlanScreen`, and `App.show_plan` builds a new screen on every navigation: leaving Plan and coming back during an export gave a screen that would start a second export of the same day. The two race over the same rows — the loser writes an id the winner has already replaced, so the block points at a deleted event, and the user is told twice that it worked | A module-level `_EXPORTS_IN_FLIGHT` set keyed by `(database path, day)`, claimed under a lock before the thread starts and released in the worker's `finally`. `test_cem444c`, `::_444d` |
| cestate-04 | Medium | `calendar_event_id` recorded no calendar, and the target calendar is a setting the user can change. After a change the export asked the *new* calendar to update an id that had never existed there, and the old event was unreachable for good — the sweep lists only the configured calendar | New `time_blocks.calendar_event_calendar_id` column (idempotent migration + CREATE TABLE), `TimeBlock.calendar_event_calendar_id`, written only with the id. On a mismatch the export deletes the old event from the *old* calendar and creates on the configured one, counted as `moved`. `test_cem11b`, `::_11c`, `test_cem12b`, `::_12c`, `test_cem255`, `::_255a`, `::_255b`, `::_255c`, `::_255d` |
| cestate-05 | Medium | `set_block_calendar_event_id` ignored `rowcount`, and the sweep used block ids read before the first API call. A block deleted while the export was talking to Google was counted as created, its new event left on the calendar with nothing naming it; and on the update path its event was *protected* by the stale snapshot | The setter returns whether a row was written; the export counts a `vanished` block instead of a success and leaves the event out of `live_event_ids`, so the one deleting code path removes it. The sweep re-reads the day's block ids immediately before it runs. `test_cem13a`, `test_cem264`, `::_264a`, `::_264b` |
| cestate-06 | Minor | Every export opens a second `DatabaseManager`, re-running every migration and repair on the worker thread with the report discarded | Filed as CE-A16 |
| cedoc-07 | Doc | The CE-M2.2 coverage row named a test that no longer exists under that name | Corrected in this document |
| cedoc-08 | Doc | Four stale counts: this document's per-file test counts, the exporter's line count, and `DOCUMENTATION_INDEX.md` still saying eight deviations / eleven findings / CE-A1–A11 | Corrected in both documents |
| cedoc-09 | Doc | "Transient Google errors … are already retried three times" in `docs/google-calendar-setup.md` and `CHANGELOG.md`. `RETRY_ATTEMPTS = 3` is three *attempts* — two retries | Corrected in both |
| cedoc-10 | Doc | CE-A9 in `BACKLOG.md` states its docstring/property disagreement backwards, and CE-A11 calls `primary` the "only reachable value" when `AppSettings.load` reads a hand-edited file | Corrected in `BACKLOG.md` |

Thirty-two further mutations prove these fixes, bringing the batch to **88**:
seven for `cestate-02` (the stored column read back, the day-parse counter
zeroed, `slot_index`-based off-grid twice, the bounds argument dropped on the
way in and on the way through, and the screen capturing a default day), five
for `cestate-01` (the guard removed, the guard made unconditional, the flag
ignored, the screen's client built interactively, the worker's named refusal
replaced), four for `cestate-03` (the claim removed, the claim made per
screen, the slot never released, the slot released too early), five for
`cestate-05` (the `rowcount` check in the setter and in the exporter, the
pre-flight snapshot restored, a failed take-back uncounted, the counter
dropped from the status line) and eleven for `cestate-04`.

One of those eleven came back **green — the test could not fail**:
`test_cem12c` cleared the event id with the calendar argument defaulted, so
`calendar_id if event_id else None` could be reduced to `calendar_id` and
nothing noticed. The test now passes a calendar alongside the `None` id, which
is the only way that guard can be exercised.

### Pass 4 — time correctness and the Google API contract

Ten findings: **4 medium, 6 low**. Nothing of high severity, which is where
`CLAUDE.md` says to stop — the fourth pass closes the budget. The four mediums
are fixed here; the six lows are filed as CE-A17 to CE-A21 (two of the ten are
the same wall-clock decision, filed together as CE-A17 and CE-A21).

Two of the pass's own severities are re-rated in this record, and the reasoning
is given rather than the number changed quietly:

* The **DST** finding came back medium. It is filed as low (CE-A17). The grid
  is wall-clock, so sending wall-clock is what makes the calendar agree with
  the screen: a block drawn 00:30-02:30 should read 00:30-02:30 on the
  calendar, whatever the elapsed hours. Changing it to elapsed-duration would
  make the calendar disagree with the screen, which is the defect the third
  pass was fixing. The genuinely wrong case — a start inside a skipped hour —
  is a question about what the Plan screen should draw, not about the export.
* The **marker-date** finding came back low. It is treated as medium and fixed,
  because the consequence is an irreversible deletion of calendar data the app
  did not create, and the fix is three lines in the one function that deletes.

| # | Severity | Finding | Fix |
|---|---|---|---|
| cetime-01 | Medium | Nothing asserted the payload that actually reaches Google. Every time test asserted `ExportEntry.start` — a datetime the app computed and the app read back — while `start['dateTime']`, `end['dateTime']` and `timeZone` were asserted by no test in the repo (`grep -rn timeZone tests/` returned nothing). Dropping the zone, sending `date` instead of `dateTime`, or reading minutes as hours all left the whole batch green | `test_cem347_the_insert_body_carries_the_wall_clock_times_and_a_real_zone` and `::_347a` assert the three strings that leave the machine. The zone is checked by handing it to `ZoneInfo`, not by comparing it with what the manager returns: asking the production helper for the expected value would pass just as well if the field were dropped |
| cetime-02 | Medium | `events().insert` is not idempotent and is retried on 429, the 5xx family and every transport error, so a request that lands and whose response is lost makes a second event. The export's sweep happens to remove the loser; `screens/calendar_dialog.py` has no sweep, so the meeting dialog made two identical events — with attendees — and recorded one | The insert body carries an event id of our own (`_new_event_id`, base32hex, built once per `create_event` call so every attempt sends the same one). A 409 is now told apart from every other refusal as `CalendarEventExists`, and that event is read back instead of a second one being created. `test_cem348`, `::_348a`, `::_348b` |
| cetime-03 | Medium | Retryability was decided on the status alone, but the Calendar API reports per-user and per-project rate limits as a **403** with a reason, not only as a 429. A day of twenty blocks plus the sweep's list is a burst of twenty-odd calls, so a throttled export was the failure a day-sized export met first — and every block in the burst was reported to the user as a hard "FAILED" by the very layer built to absorb it | `_reasons_of` reads the reason out of the error body defensively (bytes, text, absent, or not JSON at all), and `_is_retryable` treats a 403 as retryable only for `rateLimitExceeded`, `userRateLimitExceeded`, `quotaExceeded` and `backendError`. A 403 that is a real refusal, and a 403 whose body cannot be read, both stay permanent. `test_cem349`, `::_349a`, `::_349b` |
| cetime-04 | Medium | `create_event` hard-coded `reminders: useDefault False` with a ten-minute popup for every caller, so a sixteen-block day became sixteen popups the user never asked for — and because `useDefault` is False it overrode whatever the user had set on the calendar itself. Not re-sent on update either, so a first export and a re-export of the same block behaved differently | `reminders` is a parameter (P4). The meeting dialog keeps the popup by default; the Plan export passes `INHERIT_REMINDERS` — `{'useDefault': True}` — so the user's own calendar setting decides. `test_cem35` in both files, asserting the literal rather than the constant |
| cetime-05 | Medium (re-rated from low) | The sweep re-checked the block id locally — "a filter passed to an API is an argument, not a guarantee" — but never the marker's **date**, and the list call carries no `timeMin`/`timeMax`. Any event the query returned whose block id was not on the exported day was deleted. Google copies private properties onto a duplicated event, and with `singleEvents=True` every instance of a recurring one inherits them | `_marker_date_of` is checked beside `_marker_of`: an event whose marker names another day is skipped. `_private_properties` also reads the structure defensively, so an `extendedProperties` that is not the documented shape no longer raises out of the sweep. `test_cem266`, `::_266a`, `::_266b` |
| cetime-06 | Low | Wall-clock arithmetic across a DST transition sends a duration the day never planned | Filed as CE-A17, with the wall-clock decision written down |
| cetime-07 | Low | `list_day_events` pagination has no page ceiling, so a repeated `nextPageToken` hangs the export thread | Filed as CE-A18 |
| cetime-08 | Low | The sweep's per-event loop has no per-event guard, so one bad row loses the whole `ExportOutcome` | Malformed-response half fixed with cetime-05; the general per-event `try` filed as CE-A19 |
| cetime-09 | Low | `ssl.SSLCertVerificationError` is a subclass of `ssl.SSLError` and so is retried as though it were transient | Filed as CE-A20 |
| cetime-10 | Low | Re-exporting an unchanged day from another timezone silently moves every event | Filed as CE-A21 |

Sixteen further mutations prove these fixes, bringing the batch to **104**: six
for `cetime-02` and `cetime-03` together (the 403 branch removed, the reasons
parse neutered, a real refusal made retryable, an unreadable body made
retryable, the 409 no longer told apart, the insert's own id removed), two more
for the id itself (made a constant, and rebuilt per attempt so each retry
carries a fresh one), two for `cetime-04` (the caller's reminders ignored, and
the export's argument dropped), three for the payload (the zone dropped from an
insert, minutes read as hours, and an update sending `date` for `dateTime`) and
three for `cetime-05` (the date check removed, the date check made to demand a
date rather than tolerate none, and the properties read without checking their
shape). All sixteen red.

One test double had to change with the behaviour, under rule (b) — the
behaviour changed intentionally: `FakeClient.create_event` in
`tests/test_plan_screen_calendar_export.py` and `FakeCalendar.create_event` in
`tests/test_calendar_export.py` now accept the `reminders` keyword the exporter
sends. Ten screen tests went red on the kwarg before they did, which is the
double doing its job.

## Verification

Commands run, under `GETMOREDONE_NO_MAPPED_WINDOWS=1` and `nice -n 19`:

```
# before the third cold pass's fixes
pytest tests/test_calendar_export.py tests/test_google_calendar_export_calls.py \
       tests/test_plan_screen_calendar_export.py tests/test_first_run.py \
       tests/test_google_calendar_paths.py            → 93 passed
pytest tests/test_time_block_crud.py tests/test_time_block_schema.py \
       tests/test_time_block_layout.py tests/test_time_block_colors.py \
       tests/test_database.py                          → 182 passed
pytest tests/test_ui_presence.py tests/test_plan_settings.py              → 52 passed
pytest tests/test_plan_screen.py                       → 192 passed, 17 skipped
pytest <the 21 touched files and neighbours>            → 650 passed, 18 skipped

# after them (third cold pass)
{R} tests/test_calendar_export.py                    → 40 passed
{R} tests/test_google_calendar_export_calls.py       → 18 passed
{R} tests/test_plan_screen_calendar_export.py        → 34 passed
{R} tests/test_time_block_schema.py tests/test_time_block_crud.py  → 58 passed

# the whole set, once the other session's PD-M14 edit landed
{R} <the same set>                     → 9 failed, 537 passed, 17 skipped
{R} <this batch's five files alone>    → 150 passed

# after the fourth cold pass
{R} tests/test_calendar_export.py                    → 44 passed
{R} tests/test_google_calendar_export_calls.py       → 27 passed
{R} tests/test_plan_screen_calendar_export.py        → 34 passed
{R} <this batch's five files + test_google_calendar_paths.py> → 182 passed
{R} -m meta                            → 2 failed, 211 passed, 1 skipped
```

**The nine red tests in the whole-set run are not this batch's.** They are
PD-M14's, in the other session's in-progress area and in files this change does
not touch: the seven outside-group tests in `tests/test_plan_screen.py`
(`test_pdm131_*`, `test_tgm31_an_outside_block_is_drawn`,
`test_every_part_of_an_outside_row_starts_a_drag`,
`test_the_outside_group_does_not_outlive_the_day_that_had_one`,
`test_pbm55_the_settings_reach_the_outside_group_on_screen`,
`test_the_outside_group_scrolls_instead_of_growing_past_the_pane`,
`test_the_outside_group_takes_no_room_on_a_day_without_one`) and the two
`test_pdm54_*` tests in `tests/test_plan_settings.py`.

**The two red meta tests are not this batch's either.**
`test_traceability_refs.py::test_every_referenced_test_file_exists` and
`::test_every_referenced_test_name_exists` fail on four references, none of them
from a file this change touches: `docs/spec_coverage.md` →
`test_time_block_layout.py::test_pdm58_the_day_cannot_cross_midnight` and
`screens/plan.py` → `test_plan_screen.py::test_pdm52_a_drop_above_moves_day_start_back`
(both PD-M14's), and `models.py` → `tests/test_priority_floor_and_cap.py` and
`tests/test_priority_floor_form.py` (the uncommitted priority-defaults work).
Every `Tests:` reference this batch wrote resolves.

**The review budget is closed.** Four cold passes have run, each in a
different failure family: failure patterns, UI contract and test quality, state
and concurrency and document accuracy, and time correctness and the API
contract. The fourth produced nothing of high severity, which is the stopping
condition in `CLAUDE.md`. Every fix from the third pass was in scope for the
fourth, and the fourth's own five fixes are the least-reviewed code in the
change — which is what CE-A17 to CE-A21 and the manual checklist are for.

Mutation proof: 88 mutations — 6 for M1, 13 for M2, 9 for M3, 12 for M4, 2
for the cross-file defect below, 6 for the first cold pass's fixes, 8 for the
second's and 32 for the third's — each the verbatim original line removed or
inverted, one named test run against it, then restored in a `finally`. All red
after the two findings below were fixed. The harness is
`scratchpad/patches/mutate.py` (session scratchpad, not in the repo).

Three mutations came back **green — the test could not fail**. Two were real
defects, not test gaps; the third was a vacuous test:

- `update_time_block` writing `calendar_event_id` (Deviation 1).
- the `failed_block_ids` guard in `_sweep_orphans` (Deviation 7).
- `test_cem12c` clearing an event id with the calendar argument defaulted
  (third cold pass, above).

One defect was found only by running the touched files **together with their
neighbours**, which is why that run is part of this record: the new UI test
patched `GoogleCalendarManager.__new__` with `monkeypatch`, and because
`__new__` is *inherited* rather than owned, the undo wrote `object.__new__`
into the class dict. Every later `GoogleCalendarManager(credentials_file=...)`
in the same process then raised
`TypeError: object.__new__() takes exactly one argument`, failing four tests in
`tests/test_first_run.py` and `tests/test_google_calendar_paths.py` that pass
on their own. The test patches `__init__` only now and asserts
`"__new__" not in GoogleCalendarManager.__dict__` at the point where it broke
it, so a re-introduction fails there rather than three hundred tests later.

## Not code-testable

From the plan, unchanged: an OAuth consent flow, what a real Google Calendar
shows, and the behaviour of the real API's rate limiter. The manual checklist
is in the plan document (§"Criteria that cannot be made code-testable") and the
handoff note at `docs/changes/2026-11-08-plan-calendar-export.md` repeats it.
