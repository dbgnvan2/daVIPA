# Handoff Note

- Date: 2026-10-02
- Agent: Code
- Topic: depth-work-block-fields

## Summary
Added two advisory scheduling fields to Action Item records: **Depth**
(Deep | Medium | Shallow) and **Work Block** (90 | 60 | 30 minutes). Both are
editable on the editor's **Priority** tab (below the priority factors), echoed
as read-only values in the **Action Plan** block (beside Project, Wk Tactic,
Orig. Week), and persisted as new `action_items` columns. Added a
**Schedule on Calendar** button to the Priority tab that reuses the existing
`create_calendar_event` action (the same one as the Dates tab's
"Manage Calendar Event" button), and pre-fills the event dialog's **Duration**
from the item's Work Block.

## Files changed
- `src/getmoredone/models.py` — `ActionItem.depth` / `.work_block` fields;
  `SchedulingOptions` constants + `parse_work_block` / `format_work_block`.
- `src/getmoredone/database.py` — `depth TEXT` / `work_block INTEGER` in the
  `action_items` CREATE TABLE, plus guarded `ALTER TABLE` migrations.
- `src/getmoredone/db_manager.py` — INSERT, UPDATE, and `_row_to_action_item`
  now carry both fields.
- `src/getmoredone/screens/item_editor.py` — Priority-tab controls (Depth combo,
  Work Block combo, Schedule on Calendar button), Action Plan echo labels, and
  `_refresh_scheduling_display`.
- `src/getmoredone/screens/item_editor_form.py` — shared builder reads both
  fields via `SchedulingOptions.parse_work_block`.
- `src/getmoredone/screens/calendar_dialog.py` — `CalendarEventDialog` accepts
  `default_duration_minutes` and pre-fills the event Duration with it.
- `docs/USER_GUIDE.md` — documented Depth/Work Block in Action Plan and
  Priority-tab sections.
- `tests/test_depth_work_block.py` — new: schema, migration, round-trip,
  form→DB, UI presence, and calendar duration pre-fill coverage.
- `tests/test_item_editor_missing_row.py`, `tests/test_item_editor_project_link.py`,
  `tests/test_item_editor_weekly_tactic_ui.py` — extended editor stubs with the
  two new form fields (behaviour changed intentionally; the builder reads them).

## Verification
- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 ./venv/bin/python -m pytest -m "not meta" -q`
- Result: PASS — 1394 passed, 6 skipped
- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 ./venv/bin/python -m pytest -m "meta" -q`
- Result: PASS — 207 passed, 1 skipped

## Risks / Known gaps
- No `defaults` table columns were added for Depth/Work Block; new items start
  with both blank (a deliberate non-goal of this change).

## Next agent actions
- Run the UI regression policy check (`docs/AGENT_UI_REGRESSION_POLICY.md`) if
  this is destined for a release PR.
