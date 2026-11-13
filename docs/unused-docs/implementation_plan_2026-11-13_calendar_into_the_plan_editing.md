# Implementation plan — Google Calendar into the Plan, editing (CIP batch 2)

Date: 2026-11-13. **Status: awaiting approval. No code written.**
Spec: [`docs/spec_2026-11-08_calendar_into_the_plan.md`](../spec_2026-11-08_calendar_into_the_plan.md)
§7 (M4). Batch 1 (the read half) is pushed at `3af9d33`, CI green.

## 1. Scope

**In:** CIP-M4.1 to M4.8, M1.6 (`apply_commitment_edit`, deferred from batch 1)
and M0.3b (deleting a commitment leaves its action item alone).

**Out:** M6 (the week view) is batch 3, by the user's choice on 2026-11-13.
M0.2 (prep before a meeting) stays later.

## 2. Decisions (each open to change at approval)

| # | Decision | Why |
|---|---|---|
| E1 | **Guest email: ask each time.** When the meeting has other guests (attendees other than self and other than resources), the confirm step asks "Email the N other guests about this change?" — Yes / No / Cancel. No guests, no question. `update_event` and `delete_event` gain a keyword `send_updates`, default `"none"`, so the export is unchanged. | The user's choice, 2026-11-13. The current code hard-wires `sendUpdates='none'`. |
| E2 | **Only a timed meeting wholly on the drawn date, with `can_edit`, can be moved or resized.** All-day meetings, and the parts of a meeting split across midnight (D4), can be retitled or deleted but not moved. The chip says why on right-click. | A part of a split meeting has no real start or end on this date to move. Moving across days is the week view's question (spec §9, still open). |
| E3 | **Move = drag the chip in the box where the meeting starts to another box.** The new start is that box's start; the real length is kept (a 45-minute meeting stays 45 minutes). | The grid works in 30-minute boxes. A drop has no finer position. |
| E4 | **Resize = right-click → length**, the same choices and *Custom…* the block menu offers (TB-M9). No edge-drag. | Blocks have no edge-drag either; one gesture for both. |
| E5 | **A move or resize may land only on boxes that are free apart from the meeting itself**: not a block, not lunch, not another held meeting. Refused with the reason, before any network call. | The point of moving a meeting is to make room. Landing it on a block makes the D12 overlap the user then has to clear. |
| E6 | **Stale-write check.** Before writing, the event is read (as `update_event` already does) and its start, end and summary compared with the cached commitment. If Google's copy differs, nothing is written: "This meeting changed in Google Calendar since HH:MM. Refresh, then try again." | M4.5: the cache must never be ahead of Google, and a write must not overwrite a change it never saw. |
| E7 | **Confirm before:** every delete (names the event, says it is removed from the calendar, and for a recurring occurrence says "this occurrence only"); any edit of a recurring occurrence; any edit with guests (E1). A plain move of a guestless, non-recurring meeting is not confirmed: it is undone by moving it back. | M4.4, M4.6, and the global rule on irreversible outward actions. |
| E8 | **One calendar-traffic claim per database.** A write claims the same key as Refresh (`_REFRESHES_IN_FLIGHT`, renamed `_CALENDAR_TRAFFIC`). While either runs, Refresh and every edit gesture are disabled, and a gesture made anyway is refused with a status line. | M4.7: never concurrent with a fetch. One key is simpler than two that must check each other. |
| E9 | **After Google confirms, the cache is updated from Google's reply**, parsed by the batch-1 `parse_event`, through `apply_commitment_edit`. A delete removes the date's rows for that `event_id`. A 404/410 on delete counts as done (the end state asked for); on update it is refused with "Refresh". | M1.6 and P6: the stored state comes from what Google returned, not from what was asked. |
| E10 | **New code goes in a new mixin, `screens/plan_commitment_edits.py`**, and pure logic in `calendar_commitments.py`. `plan.py` (3,320 lines) gets only the drag-kind branch. | `file-maintainability.md`. |

## 3. Criteria → tests

New files: `tests/test_calendar_commitment_edits.py` (logic, fake client, no
window) and `tests/test_plan_screen_commitment_edits.py` (screen, unmapped).

| ID | Test |
|---|---|
| M4.1 | `test_cipm41_an_uneditable_chip_has_no_drag_binding`; `test_cipm41_the_menu_of_an_uneditable_meeting_offers_no_edit`; `test_cipm41_a_drop_of_an_uneditable_meeting_makes_no_call` |
| M4.2 | `test_cipm42_a_move_writes_the_new_start_and_the_same_length`; `test_cipm42_a_resize_writes_the_new_end`; `test_cipm42_a_move_onto_a_block_is_refused_before_any_call` (E5); `test_cipm42_a_split_or_all_day_meeting_cannot_be_moved` (E2) |
| M4.3 | `test_cipm43_retitle_changes_the_summary_only`; `test_cipm43_an_empty_title_is_refused` |
| M4.4 | `test_cipm44_delete_asks_first_and_names_the_event`; `test_cipm44_cancel_makes_no_call`; `test_cipm44_a_gone_event_counts_as_deleted` |
| M4.5 | `test_cipm45_a_failed_write_leaves_the_cache_and_grid_as_they_were`; `test_cipm45_a_changed_event_is_not_overwritten` (E6); `test_cipm45_the_cache_takes_googles_reply_not_the_request` (E9) |
| M4.6 | `test_cipm46_a_recurring_occurrence_is_confirmed_as_this_one_only`; `test_cipm46_attendees_conference_reminders_recurrence_description_survive` |
| M4.7 | `test_cipm47_a_write_is_refused_while_a_refresh_runs`; `test_cipm47_refresh_is_refused_while_a_write_runs`; `test_cipm47_the_claim_outlives_the_screen` |
| M4.8 | `test_cipm48_each_missing_prerequisite_refuses_and_reenables` (parametrised over no libraries, no credentials, no token, lapsed sign-in) |
| E1 | `test_cipe1_guests_are_asked_and_the_answer_reaches_send_updates`; `test_cipe1_no_guests_no_question`; `test_cipe1_the_export_still_sends_none` |
| M1.6 | `test_cipm16_apply_commitment_edit_replaces_only_that_event_on_that_date` |
| M0.3b | `test_cipm03b_deleting_a_commitment_leaves_its_action_item` |

Each test is mutation-checked against the verbatim line it names.

## 4. Build order

1. **Client:** `send_updates` keyword on `update_event` and `delete_event`
   (E1). Export call unchanged.
2. **Logic** in `calendar_commitments.py`: `edit_commitment(client, commitment,
   *, start_minutes=None, minutes=None, title=None, send_updates)` and
   `delete_commitment(...)` — the E6 check, the write, the parse of the reply.
   `guest_count(event)`, `movable(commitment)` (E2), and the E5 target check.
3. **Store:** `apply_commitment_edit` (M1.6).
4. **Screen:** the mixin — drag kind, length menu, *Rename…*, *Delete from
   Google Calendar…*, the confirm dialog (E1, E7), worker and poll on the
   shared claim (E8). Uneditable chips get no drag binding.
5. **Docs:** user guide (moving a meeting, guest emails), setup page, spec
   status and M4 notes, `spec_coverage.md`, CHANGELOG, NOTES, BACKLOG,
   handoff note with a walk checklist.
6. **Reviews, push** via /csdp: cold `learning-qa`, cold correctness pass,
   `/security-review` (outward writes and deletes).

## 5. Hazards

- **Writes to other people's calendars, and one irreversible action.** No
  test reaches live Google. The report will say so. The first real move and
  delete are walk items, on a test meeting.
- **`guestsCanModify`.** A guest who may modify changes the meeting for
  everyone. Google allows it; the confirm step (E1) names the guests so the
  user sees who is affected.
- **Time zone.** `update_event` writes the wall-clock start with the OS zone,
  as the export does (D5 left `local_zone()` uncalled). A meeting created in
  another zone is moved in this one's wall clock, which is what the grid shows.

## 6. Not code-testable (walk after the batch)

1. Drag your own test meeting to another box; open Google Calendar and check
   the time, the guests, the video link and the description.
2. Move a meeting with one guest and answer *No* to the email question; check
   the guest received nothing. Repeat with *Yes*.
3. Move one occurrence of a weekly meeting; check the other weeks are unchanged.
4. Try to drag a meeting someone else organises: nothing moves.
5. Delete a test meeting from the Plan; check it is gone from Google.

## 7. Size

About 25 criteria. Estimated 500–750 lines of `src/`, tests within ≤2x.
One build session.
