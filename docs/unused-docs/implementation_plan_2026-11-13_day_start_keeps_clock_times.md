# Implementation plan — Day Start keeps clock times (PD-M14.4, PD-M14.7)

Date: 2026-11-13. Approved by the user in chat ("Yes, build it") on the
SBN-A3 recommendation. Source criteria:
`implementation_plan_2026-11-08_day_hours_are_a_template.md#pd-m14-4` and `#pd-m14-7`.

## Design

**PD-M14.4.** Saving Day Settings with a new Day Start renumbers every slotted
block on every date by `(old − new) / 30` boxes, so each keeps its clock time.
`DatabaseManager.shift_day_start(old, new, write_settings)` runs
`shift_all_slots` and the settings write in one SQLite transaction: if the
settings write returns False or raises, the renumber rolls back. The dialog
gets the manager from `PlanScreen`. A Day Start move that is not a whole number
of boxes is refused while any block has a box, because no renumber keeps those
times. The status line says how many blocks kept their times.

This reverses TG-M6.4 / TG-M6.4a at the dialog: `on_settings_saved` still
writes nothing, but the dialog now does. Their tests stay (the layout and the
screen callback still behave as they say); the spec_coverage rows say which
layer each covers.

**PD-M14.7.** `DatabaseManager.repair_slots_from_times(date, bounds)` recomputes
each slotted block's box from its stored `start_time`
(`slot_index_for_time(..., allow_before=True)`). Unreadable times are skipped
and counted. If any moved block would not fit the repaired day (`can_place`:
outside the date, crossing lunch, full box) the date is left as it is and the
refusal is reported. Plan calls it on load, before adoption (so adoption sees the repaired
boxes), under the same `_day_shape_is_the_users()` gate. A refused repair
outranks every other load or save message on the status line. It writes nothing when slots and times agree,
so "once" is idempotence, not a stored flag.

## Criteria → tests

| ID | Criterion | Test |
|---|---|---|
| PD-M14.4a | 09:00→08:00 on three dates: every block's time unchanged, slot +2 | `tests/test_time_block_crud.py::test_pdm144_changing_the_hours_keeps_clock_times` |
| PD-M14.4b | Settings write fails → renumber rolled back, dialog says so | `::test_pdm144_a_renumber_that_fails_leaves_the_hours_alone` |
| PD-M14.4c | Non-30-minute move refused while blocks have boxes; allowed on an empty plan | `::test_pdm144_a_part_box_move_is_refused_while_blocks_are_planned` |
| PD-M14.4d | The dialog renumbers and the status line counts the blocks | `tests/test_plan_screen.py::test_pdm144_the_dialog_keeps_planned_work_on_its_clock` |
| PD-M14.7a | Slot 6 recorded 08:30, 09:00 day → slot −1, time unchanged | `tests/test_time_block_crud.py::test_pdm147_a_block_is_put_back_on_the_time_it_was_planned_at` |
| PD-M14.7b | A day that agrees: no write, twice | `::test_pdm147_a_day_that_agrees_is_not_touched` |
| PD-M14.7c | A repair that would collide writes nothing and says so | `::test_pdm147_a_repair_that_does_not_fit_writes_nothing` |
| PD-M14.7d | Unconfirmed day shape: Plan repairs nothing | `tests/test_plan_screen.py::test_pdm147_an_unconfirmed_day_shape_repairs_nothing` |
| PD-M14.7e | Plan load repairs and reports the count | `tests/test_plan_screen.py::test_pdm147_opening_a_day_puts_blocks_back_and_says_so` |
| walk | Change Day Start by an hour; planned items keep their times | handoff checklist |
