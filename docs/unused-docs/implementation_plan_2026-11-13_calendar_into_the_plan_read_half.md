# Implementation plan — Google Calendar into the Plan, read half (CIP batch 1)

Date: 2026-11-13. **Status: awaiting approval. No code written.**
Spec: [`docs/spec_2026-11-08_calendar_into_the_plan.md`](../spec_2026-11-08_calendar_into_the_plan.md)
(still marked draft; approving this plan approves the spec's §4–§6 and §8 M5 as
the scope below). Asked for by the user on 2026-11-13: "plan CIP read half".

## 1. Scope of this batch

**In:** M1 (store), M2 (read), M3 (grid), M5 (Plan screen), and the two M0
criteria that need no new gesture (M0.1, M0.3's first half).

**Out, to later batches:**
- **M4 (editing Google from the Plan)** is batch 2, per spec §10. It writes to
  other people's calendars and deletes events, so it gets its own reviews.
- **M0.2 (place prep work before the meeting)** is batch 3. It is a new
  placement gesture, and spec §11 says only a real week can judge it.
- **M0.3's second half** (deleting a commitment leaves its action item alone)
  needs M4's delete, so it moves to batch 2.
- **M6 (the week view)** is phase 2. This batch builds every function over a
  date range, so M6 is a UI addition.
- **M1.6 (`apply_commitment_edit`)** has no caller until M4 and goes to batch 2.
  Writing it now would be a writer with no caller.

## 2. Decisions this plan takes (each open to change at approval)

| # | Decision | Why |
|---|---|---|
| D1 | `can_place` gets a keyword `committed: frozenset[int]`, the set of held slot indices. A pure `committed_slots(commitments, bounds)` builds it. Default empty. | The lunch precedent (spec §3): one region-of-the-grid answer, computed once. A set of indices keeps `time_block_layout.py` free of the commitment model. |
| D2 | Every **db** write path loads the date's commitments itself (`DatabaseManager._committed_for(date, bounds)`), so no caller can forget them. The **screen** passes the set it loaded at refresh. | There are six `can_place` call sites: `db_manager.py` (`_refuse_unless_it_fits`, `repair_slots_from_times`, `adopt_legacy_day`) and `screens/plan.py` (`_drop_refusal`, `first_clear_slot`, `first_free_slot`). A rule a caller has to remember is what CIG-A1 records going wrong. |
| D3 | The new refusal is `SlotRefusal.SLOT_COMMITTED`. `can_place` then returns exactly **four** values (`LUNCH_EXISTS` is raised only by `add_block_at`, `db_manager.py:1693`), and `test_tgm23_each_refusal_has_its_own_reason` is rewritten to assert those four (today it asserts three). A new test asserts every `SlotRefusal` value has an entry in `REFUSAL_TEXT`, which nothing checks today. | Exact count, never a floor. "Mapped to a sentence" needs its own guard. |
| D4 | An event that crosses midnight becomes one commitment per date it touches, clipped to that date, and **only for dates inside the fetched range**. `events.list` also returns events that started before `timeMin`, and writing their earlier dates would break M1.4. A timed commitment, or the part of one, that the grid cannot draw (before 00:00 or past the last box, `LAST_DAY_END_MINUTES` = 23:30) is listed in the strip above the grid with its times, and holds the boxes the grid does have. | The spec is silent. One date, one grid (PD-M14.2), and nothing held is hidden (P2). |
| D5 | Local wall clock is the machine's zone: `tzlocal` when it imports (it is optional, `google_calendar.py:22`), otherwise `datetime.astimezone()` with no argument, which uses the OS zone. It is applied once, at parse time. This one decision also settles CE-A17 and CE-A21, and their backlog entries are updated to point here. | Spec §10: decide wall clock once for both directions. |
| D6 | A fetch is all-or-nothing for **transient** failures (network, 5xx, rate limit, lapsed sign-in): no date is replaced, and each date gets a failure record that keeps its last good `fetched_at`. A **permanent** failure on one calendar (404, or a 403 the client classifies as forbidden) does not block the others. That calendar is skipped, and every refresh names it on the status line until the setting is changed. | M2.7. One revoked shared calendar must not freeze the cache for good. |
| D7 | Two new `AppSettings` fields. `plan_commitment_calendar_ids` is a list defaulting to `["primary"]` through `field(default_factory=...)`, as at `app_settings.py:199`. `plan_commitment_stale_minutes` is an int defaulting to 15. On load, a non-list or empty list falls back to the default, and so does a non-positive number; each fallback is logged. | Config, not constants (global rule 8). A JSON string read as a list would be read one character at a time. |
| D8 | A commitment that pulls the drawn day outward (M3.7) widens `span_for_blocks` through a new `committed=` keyword. The screen's grid, `slot_occupancy`/`build_day_grid` at `plan.py:2252-2253`, the repair (PD-M14.7) and adoption all pass it. The exporter (`calendar_exporter.py:254`) deliberately does **not** (D12). | PD-M14.2: one derivation of the day's shape. |
| D9 | Dismissal (M3.4) ships in this batch for commitments with `can_edit = 0`. An editable one stays held until batch 2 lets the user move it from the Plan. Until then the user moves it in Google and presses Refresh. | Batch 1 must not leave someone else's meeting holding slots with no way out. The spec's rule for editable events is unchanged. |
| D10 | Refresh button: on the header's tools row, secondary style. It is disabled before the worker starts. A claim keyed by **database path alone** acts as the "server-side guard", so one calendar read runs per database, whatever its range (the export's `_EXPORTS_IN_FLIGHT` pattern). A rebuilt screen checks the claim at construction and comes up disabled while a read is in flight. The worker opens its own `DatabaseManager` on its thread, and the Tk thread polls for its result with `after()`, as the export does (`plan.py:1800-1857`). | Global rule on background-work buttons. Keying on the range let an auto-refresh and a manual one overlap, and the older one could finish last and overwrite the newer answer. |
| D12 | **A block already on a slot that a fetched commitment then takes stays where it is.** It is not moved to *Outside the day*. It is drawn with a conflict mark, and the status line counts it ("2 blocks overlap a meeting"). A gesture on that block does not count the committed slots the block already covers, so it can still be shortened, nudged or moved off. Only slots it would newly enter are refused. The exporter is unaffected and still exports it: it is still the user's plan. Commitments do not count toward the day summary's `slots_used` or `minutes_occupied`. | The normal case, missing from the spec: plan 10:00, a meeting is booked at 10:00, press Refresh. Sending the block to *Outside* would drop it from the export. Refusing every gesture would leave the user unable to move it out of the way. |
| D13 | Auto-refresh (M5.5) runs only when the libraries, `credentials.json` **and** a token file are all present. "Once" means once per date per process: a failed auto-refresh is not retried automatically, and the next try is the Refresh button. A date never read counts as stale under this gate. | M5.1 says the screen of a machine without Google is unchanged. Without the gate, every open would put a failure on it. |
| D11 | The fetch uses `list_events_between(time_min, time_max, calendar_id)` on `GoogleCalendarManager`: paginated, `singleEvents=True`, `orderBy=startTime`, through `_with_retry`. Scope `calendar` already covers reading. | M2.1, M2.2. The same client and retry path as the export. |

## 3. Criteria → tests

New test files: `tests/test_calendar_commitments.py` (M1, M2, pure, fake
client), additions to `tests/test_time_grid.py` (M3 layout), and
`tests/test_plan_screen_commitments.py` (M3 drawing, M5). Every
`DatabaseManager` takes `tmp_path`. No test touches the network.

| ID | Criterion (short) | Test |
|---|---|---|
| M0.1 | One event gives both an action item (importer) and a commitment | `test_calendar_commitments.py::test_cipm01_one_event_is_both_an_item_and_a_commitment` |
| M0.3a | Deleting the action item leaves the commitment | `::test_cipm03_deleting_the_item_leaves_the_commitment` |
| M1.1 | Table on a fresh DB and by idempotent migration; columns as specified | `::test_cipm11_the_table_exists_fresh_and_migrated`, `::test_cipm11_the_migration_runs_twice_safely` |
| M1.2 | `CalendarCommitment` appended to `models.py`; existing positional construction unchanged | `::test_cipm12_existing_models_construct_positionally` |
| M1.3 | Never read ≠ read and empty ≠ read and failed | `::test_cipm13_three_states_of_a_date` |
| M1.4 | `replace_commitments_for_dates` replaces exactly the given dates, in one transaction | `::test_cipm14_only_the_fetched_dates_change`, `::test_cipm14_a_failure_part_way_writes_nothing` |
| M1.5 | `dismissed` survives a refetch (event_id + date) | `::test_cipm15_dismissal_survives_a_refetch` |
| M2.1 | One paginated list call per calendar for the whole range | `::test_cipm21_seven_days_is_one_call_per_calendar`, `::test_cipm21_every_page_is_read` |
| M2.2 | Non-interactive client; `AuthenticationRequired` is reported, not raised | `test_plan_screen_commitments.py::test_cipm22_a_lapsed_sign_in_is_reported` |
| M2.3 | Offset-aware times become local wall-clock minutes; D4 split at midnight | `test_calendar_commitments.py::test_cipm23_an_offset_time_is_stored_as_local_wall_clock`, `::test_cipm23_an_event_over_midnight_is_two_commitments` |
| M2.4 | All-day events: `is_all_day=1`, no slots | `::test_cipm24_an_all_day_event_holds_no_slot` |
| M2.5 | Cancelled, declined, transparent and `gmd_block_id` events are excluded, each counted | `::test_cipm25_each_exclusion_is_counted` (parametrised over the four) |
| M2.6 | An unparseable event is skipped and named | `::test_cipm26_an_unparseable_event_is_named_not_guessed` |
| M2.7 | A failed fetch keeps the old cache and records the failure (D6) | `::test_cipm27_a_failed_fetch_keeps_what_was_known` |
| M2.8 | The same event on two calendars is one commitment; `can_edit` is the most permissive | `::test_cipm28_one_event_on_two_calendars_is_one_commitment` |
| M3.1 | An exported day read back leaves the grid unchanged (P7, adversarial) | `::test_cipm31_an_exported_day_read_back_holds_no_slot`: runs the real `export_day` into a fake client that stores what it is sent, then fetches from the same fake. Events built with the marker set by hand would prove nothing. |
| M3.2 | Touched slots are held: 09:50–10:00 holds the 09:30 slot | `test_time_grid.py::test_cipm32_a_commitment_holds_every_slot_it_touches` |
| M3.3 | `SLOT_COMMITTED` refused by `can_place` and by every db writer; every refusal mapped to a sentence; `can_place` returns exactly four values | `test_time_grid.py::test_tgm23_each_refusal_has_its_own_reason` (rewritten, reason b), `test_plan_screen_commitments.py::test_cipm33_every_refusal_has_a_sentence`, `test_calendar_commitments.py::test_cipm33_every_write_path_refuses_a_committed_slot` (parametrised over add, move, resize, adopt, repair), `test_plan_screen_commitments.py::test_cipm33_the_free_slot_finders_skip_committed_slots` (`first_clear_slot`, `first_free_slot`, `_drop_refusal`) |
| D12 | A block under a new commitment stays, is marked, is counted, can be shortened or moved off, and is still exported | `test_calendar_commitments.py::test_cipd12_a_block_under_a_new_commitment_can_still_be_shortened`, `test_plan_screen_commitments.py::test_cipd12_an_overlapping_block_is_marked_and_counted`, `::test_cipd12_the_export_still_sends_it` |
| D4 | Range-edge and past-the-grid commitments | `test_calendar_commitments.py::test_cipd4_a_date_before_the_range_is_not_written`, `test_plan_screen_commitments.py::test_cipd4_a_commitment_past_the_last_box_is_listed_in_the_strip` |
| D6 | A permanent failure on one calendar does not block the others, and is named | `test_calendar_commitments.py::test_cipd6_a_forbidden_calendar_is_skipped_and_named` |
| D7 | A malformed calendar-id setting falls back to the default | `test_plan_settings.py::test_cipd7_a_string_calendar_list_falls_back` |
| M3.4 | A non-editable commitment can be dismissed for its date; the slots free up; it is drawn as ignored; nothing goes to Google. `can_edit` is derived from `organizer.self` or `guestsCanModify` | `::test_cipm34_dismissing_frees_the_slots_locally`, `::test_cipm34_can_edit_comes_from_the_event` (parametrised: organizer, guestsCanModify, neither), `test_plan_screen_commitments.py::test_cipm34_an_editable_commitment_offers_no_dismiss`, `::test_cipm34_a_dismissed_commitment_is_drawn_as_ignored` |
| M3.5 | Not counted in the day summary, and not one of the `MAX_BLOCKS_PER_SLOT` occupants | `test_plan_screen_commitments.py::test_cipm35_the_day_summary_does_not_count_a_commitment`, `test_time_grid.py::test_cipm35_slot_occupancy_does_not_count_a_commitment` |
| M3.6 | Drawn as its own region with its true times and title, coloured by a new theme token, not priority-coloured | `test_plan_screen_commitments.py::test_cipm36_a_commitment_is_drawn_with_its_times`, `::test_cipm36_its_colour_is_the_commitment_token_not_a_priority_fill` |
| M3.7 | A 07:00 commitment widens the drawn day (D8) | `test_time_grid.py::test_cipm37_an_early_commitment_widens_the_day` |
| M3.8 | All-day events drawn in a strip above the grid | `test_plan_screen_commitments.py::test_cipm38_all_day_events_are_in_the_strip` |
| M3.9 | Overlapping commitments: both shown, union held | `test_time_grid.py::test_cipm39_overlaps_hold_the_union`, `test_plan_screen_commitments.py::test_cipm39_both_overlapping_commitments_are_drawn` |
| M5.1 | The Plan screen paints with no network call | `test_plan_screen_commitments.py::test_cipm51_opening_plan_makes_no_call` (asserts the client factory was called **zero** times; a raising factory would be swallowed by the worker's catch-all at `plan.py:1829`) |
| M5.2 | Refresh is disabled before work starts and re-enabled on success and on each refusal; a rebuilt screen comes up disabled mid-fetch | `::test_cipm52_refresh_disables_first`, `::test_cipm52_a_rebuilt_screen_sees_the_fetch_in_flight` |
| M5.3 | The worker updates the screen on the Tk thread; one fetch per (db, range) | `::test_cipm53_a_second_fetch_of_the_same_range_is_refused` |
| M5.4 | The status says "Calendar as of HH:MM", "not read for this day", or the failure | `::test_cipm54_the_age_of_the_answer_is_shown` (parametrised over three states) |
| M5.5 | A stale date refreshes once on open, in the background, only behind the D13 gate | `::test_cipm55_a_stale_day_refreshes_once`, `::test_cipm55_no_credentials_means_no_auto_refresh`, `::test_cipm55_a_failed_auto_refresh_is_not_retried` |
| M7.1 | Docs: `USER_GUIDE.md`, `google-calendar-setup.md`, `CHANGELOG.md`, `NOTES.md`, `DOCUMENTATION_INDEX.md`, handoff note | no test (no guard reads prose); listed in the status report |

## 4. Build order

1. **Model, schema and store.** M1.1–M1.5, plus the two settings (D7).
2. **Parse and fetch.** Pure functions: M2.3–M2.6 and M2.8. Then
   `list_events_between` (D11) and `fetch_commitments` with D6 (M2.1, M2.2,
   M2.7, M3.1).
3. **Layout.** `committed_slots`, the `can_place` keyword, `SLOT_COMMITTED`,
   and the `span_for_blocks` and `build_day_grid` keywords (M3.2, M3.3, M3.5,
   M3.7, M3.9). Then `_committed_for` in every db writer (D2).
4. **Screen.** Drawing (M3.6, M3.8), dismissal (M3.4), the Refresh button and
   worker (M5.1–M5.5), and the theme token. Regenerate the colour inventory.
5. **Docs, reviews, push.**

Steps 1–3 run without a window. Step 4 is the UI-contract part and gets the
`ui-regression.md` treatment. `src/` and tests are committed separately.

## 5. Hazards

- **Header width.** `test_cem441b_the_header_fits_the_window_it_opens_in`
  already constrains the tools row. A fifth button may not fit. If it does
  not, the button goes on the day row with a status label, and the test still
  holds. Measured, not assumed.
- **Six `can_place` call sites.** If one misses `committed=`, the screen
  offers a box the db then refuses. `test_cipm33` covers the db side. For the
  screen side, `first_clear_slot` and `first_free_slot` get one test each in
  `test_plan_screen_commitments.py`, so the reviewer can check every site.
- **Repair (PD-M14.7) and commitments.** If putting a block back would land it
  on a committed slot, the repair refuses the date. That is the behaviour it
  already has for a full slot, and it is asserted inside `test_cipm33`.
- **Live Google is untested.** Real OAuth, pagination, rate limits and
  permissions are integration-only. The status report will say so rather than
  let a fake client imply it.

## 5a. Revised after a cold review (2026-11-13)

The first draft was missing D12 and D13. It also had D3 wrong (it claimed the
existing test asserts five values; it asserts three), and D4, D6, D7 and D10
were unsound as first written. Four tests could not fail as named:
`test_cipm35`, `test_cipm51`, `test_cipm31` and the untested `can_edit`
derivation. All of these are corrected above.

## 6. Not code-testable (walk after the batch)

1. A day with a meeting, a lunch, a buffer and an item, in both themes: the
   meeting does not read as a block.
2. Press Refresh with no network: the failure is shown, and the last-known
   commitments stay drawn with their age.
3. A real calendar with a declined meeting, a "free" event and an all-day
   event: none of the three holds a slot.
4. Export the day, then press Refresh: nothing changes on the grid (M3.1, live).

## 7. Size

About 35 criteria. Estimated 1,000–1,400 lines of `src/`, within the ≤2x test
budget. One build session. It needs at least one cold review and the
`/security-review` pass (an external read, and stored text from a third party).
