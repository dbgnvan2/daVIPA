# PD-M14 — the day's hours are a template (IN PROGRESS, nothing committed)

Status at hand-off: **work in progress, uncommitted, test suite red.** Three of
the eight approved PD-M14 items are built; five are not started. Do not push.

Plan: `docs/implementation_plan_2026-11-08_day_hours_are_a_template.md`
(committed as `8aa3a45`). Read it rather than re-deriving the design.

## Built

- **PD-M14.2** — signed `slot_index` and the derived drawn day.
  `src/getmoredone/time_block_layout.py`: `DaySpan`, `template_span`,
  `span_for_blocks`, `_stays_inside_the_date`, `DayGrid.span`; `day_grid`,
  `can_place`, `slot_occupancy`, `build_day_grid` take an optional span;
  `times_for_slot` lost its `max(0, …)` clamp. Tests green:
  `tests/test_time_block_layout.py` (97), `tests/test_time_grid.py` (58).
- **PD-M14.1** — `extend_day_for` writes one block and nothing else. No
  `plan_day_start` / `plan_day_end` write, no `settings.save()`, no
  `shift_all_slots`, no rollback arm. `day_span` threaded through
  `db_manager.add_block_at` / `_refuse_unless_it_fits`. `extended_day_bound`
  and `_DayNotWritten` deleted; `extended_span` / `DayExtension` replace them.
- **PD-M14.6** — `edge_limit_time`, and one refusal sentence naming the end
  and its limit at both ends.

## Not started

PD-M14.3 (Clear Day), PD-M14.4 (`on_settings_saved` renumbers — reverses
TG-M6.4), PD-M14.5 (`first_free_slot` searches `template_span` only),
PD-M14.7 (the one-time `slot_index` repair), PD-M14.8 (the on-screen walk).

## Tests

- Green: `test_time_block_layout.py`, `test_time_grid.py`, and the 19
  `-k "pdm141 or pdm5 or pdm146"` tests in `test_plan_screen.py`.
- **Red: 7 tests** across `test_plan_screen.py`, `test_time_grid.py`,
  `test_time_block_crud.py` (282 passed, 7 failed, 17 skipped). One is
  identified: `test_plan_screen.py:3257` expects `outside_frame` to be gridded
  for a block past Day End — under PD-M14.2 that block is now *drawn* rather
  than surfaced, which is TG-M3.1's intended narrowing. The other six are
  unexamined. Get the list with:
  `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_plan_screen.py tests/test_time_grid.py tests/test_time_block_crud.py -q -p no:randomly --tb=line`
- No mutation gate has been run over any PD-M14 fix.

## Follow-ups

- Withdrawn criteria now include **PD-M5.6** (and its `_DayNotWritten`), on top
  of the PD-M5.2 / PD-M5.3 / PD-M5.5 / TG-M6.4 the plan lists. All of them, and
  **TG-M3.1-narrowed**, still need their `docs/spec_coverage.md` rows.
- Docs not yet touched: `spec_coverage.md`, the 11-05 and 11-06 plans,
  `USER_GUIDE.md`, `CHANGELOG.md`, `BACKLOG.md`.
