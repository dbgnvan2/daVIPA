# Handoff Note

- Date: 2026-11-09
- Agent: Code
- Topic: plan-day-tests-follow-pd-m14 (PDT)

## Summary

The brief was to port the `outside` implementation from
`refs/heads/claude/plan-day-range-pdm13` onto `main`'s PD-M14 design.
**There was nothing to port.** Measured on `main` at `4ca7116` before writing
anything: `outside` is implemented and green at the layout layer
(`tests/test_time_grid.py`, 58 passed), and the screen half — `outside_frame`,
`build_outside_group`, the `grid()`/`grid_remove()` pair, the P2 status, the
scrollable holder — was already there, with a screen test using the "never
placed" vehicle passing the whole time.

The nine red plan-day tests were **stale vehicles, not missing code**. Six
produced an outside block by saving a tighter Day End, which PD-M14.2 made
unable to orphan one: the drawn day is derived from the date's own blocks
(`span_for_blocks`), and `PlanScreen.refresh` calls `build_day_grid` with no
span, so the day always stretches to cover what the date holds. Three asserted
the Day Settings write PD-M14.1 withdrew.

Each test keeps every assertion it had. Only the setup changed. This is repo
test rule case **(b), the behaviour changed intentionally** — stated before any
test was edited.

### What replaced each vehicle

| tests | old vehicle | new vehicle | why this one |
|---|---|---|---|
| PDT-M1.1, M1.2, M1.3, M1.4, M1.6 | `on_settings_saved(DayBounds(day_end="12:00"))` | `on_settings_saved(DayBounds(lunch_start="16:00"))` | lunch over the block is the one settings change that still takes work off the grid, so `test_tgm31`'s status assertion survives intact |
| PDT-M1.5 | `day_end="10:00"`, 8 blocks | `lunch_start="13:00", lunch_minutes=240` | eight boxes of lunch is eight outside blocks, the number the fixed height is measured against |
| PDT-M2 | `bounds.day_start < started_at` | `slot_index == -1`, `start_time == "07:30"` | the capability the report asked for, against the mechanism that survived |
| PDT-M3 | `plan_day_start == "07:30"` precondition | the block was written; the settings file is unchanged byte for byte | a precondition that cannot be reached asserts nothing |

### Two findings worth keeping

- **`test_pdm131` and `test_pdm141` contradicted each other on `main`.** One
  asserted a drop moves `bounds.day_start`, the other that it does not, about
  the same call. PD-M13.1's own subject (the drop asks nothing, and it writes)
  is kept verbatim; the `day_start` half is gone, with a docstring line saying
  not to restore it.
- **`test_pbm55_the_settings_reach_the_outside_group_on_screen` had never run
  against the thing it names.** Since PD-M14 it had been reading its height off
  an *in-grid* block, because none was outside — which is why it reported 60px
  against an expected 64. Pointed at a real outside holder it passes:
  `build_outside_group` does honour `drag_schedule_box_height_px`. **No code
  fix was needed.** This was flagged in the plan as the one criterion that
  might need `src/` work; it did not.

## Files changed

- `tests/test_plan_screen.py` — PDT-M1.1–M1.6, PDT-M2 (`a19a38a`)
- `tests/test_plan_settings.py` — PDT-M3, both PD-M5.4 tests (`a19a38a`)
- `src/getmoredone/screens/plan.py` — `virtual_under_pointer`'s `Tests:` line (`2cd83a3`)
- `src/getmoredone/time_block_layout.py` — `edge_limit_time` and `build_day_grid` `Tests:` lines, one broken line break (`2cd83a3`)
- `src/getmoredone/screens/plan_blocks.py` — `build_outside_group`'s stale prose about Day End (`2cd83a3`)
- `docs/spec_coverage.md` — three dead references, plus the PDT rows
- `BACKLOG.md` — items 1, 2 and 4 rewritten
- `NOTES.md` — where `main` stands
- `docs/implementation_plan_2026-11-09_plan_day_tests_follow_pd_m14.md` — the plan (`11ec1dc`)
- `docs/DOCUMENTATION_INDEX.md` — this note and the plan

No `src/` behaviour changed in this batch. The three `src/` files hold
docstring text only.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_plan_screen.py tests/test_plan_settings.py tests/test_time_grid.py tests/test_time_block_layout.py -q`
- Result: **PASS** — 396 passed, 17 skipped
- Command: `… -m pytest tests/test_traceability_refs.py -q`
- Result: **FAIL, expected** — `test_every_referenced_test_name_exists` passes;
  `test_every_referenced_test_file_exists` still red on the two `models.py`
  references. See Risks.

Mutation-proved, each restored byte-identical and confirmed so with
`git diff --stat`:

| criterion | mutation | result |
|---|---|---|
| PDT-M1.1 | the lunch branch deleted from `build_day_grid` | red |
| PDT-M1.3 | the holder pinned to `SLOT_CHIP_HEIGHT_PX`, ignoring `chip_height` | red |
| PDT-M2 | `extended_span` makes no room before the first box | red |
| PDT-M3 | `extend_day_for` writes and saves the hours again | red, both tests |

The full suite was left to CI, per the repo's throttle rule.

## Risks / Known gaps

- **PRI-M1/M2 shipped without its tests.** `src/getmoredone/models.py` names
  `tests/test_priority_floor_and_cap.py` and `tests/test_priority_floor_form.py`
  and three tests inside them; none of the five has ever existed. So the
  priority cap, the floor and the "(capped)" label are unverified.
  `test_every_referenced_test_file_exists` stays red on exactly this.
  **Deliberately not closed:** deleting the `Tests:` lines would green the meta
  test while hiding the gap, which is the opposite of what it is for. Filed as
  `BACKLOG.md` item 2. Not this batch's work.
- **Nine CI-environment failures are untouched** and were never in scope:
  `test_t51`, `test_t52`, `test_t56`, `test_t57`, `test_wt_m6b6`,
  `test_alpha_still_passes_through_the_attributes_wrapper`,
  `test_raw_tkinter_windows_are_hidden_and_registered_too`,
  `test_pbm61_a_tall_row_keeps_its_two_lines_together`,
  `test_updm14_zero_width_body_is_a_noop`. All nine **pass locally** under
  `GETMOREDONE_NO_MAPPED_WINDOWS=1`; they need a window manager the CI runner
  does not have. `BACKLOG.md` items 3 and 5.
- **`refs/heads/claude/plan-day-range-pdm13` is superseded, not merged.** It
  stays at `c8125af`. Its design is what caused both reported faults, so it
  must not be merged; deleting it is a decision nobody has taken. No test can
  assert this (PDT-N1), so it lives here and in `BACKLOG.md`.
- **That the rewrites still assert the right things is a judgement**, not
  something mutation testing settles (PDT-N2). The table above is there so a
  reviewer can check each one against what it replaced.

## Next agent actions

- Write the three PRI tests, or decide the priority cap ships unverified and say
  so in `BACKLOG.md`. Until then `main`'s CI cannot go green.
- Design the one shared precondition for the nine CI-environment tests
  (WTP-A11). `23f0cc7` is the worked example for a single test; seven of them
  need one guard, not seven.
- Decide whether `refs/heads/claude/plan-day-range-pdm13` is deleted.
