# Implementation plan — drag a Time Block between days in the week (2026-11-14)

Status: **approved and built 2026-11-14.** Not walked on screen.
Spec: `docs/spec_2026-11-08_calendar_into_the_plan.md` §8. This adds
CIP-M6.7 (drag a block in the week) and CIP-M6.8 (only the date opens a day).
It reverses M6.5's D7 ("block drags start from day chips, and the week does
not draw any").

The user's requirements:

1. A Time Block can be dragged from one day of the week to another.
2. Clicking a column's date heading opens that day in the Day view. A click
   anywhere else in the week leaves it in the week.
3. The Day / Week button does not change.

## What the code does today

- `_draw_week_grid` binds `_bind_open` (a click opens the day) on each
  column's heading, every box that is not empty, each box's title label, and
  each column's totals (`plan_week_view.py:351, 368, 378, 436`).
- An item drag in the week goes to `drop_on_week`. A block drag only starts
  from a day chip (`plan.py::bind_block_handlers`), so the week has none.
- `db_manager.place_block_at` moves a block to another box on **its own
  date** only: it checks and settles against `block.block_date`.
- An exported block keeps `calendar_event_id`. Its Google event carries a
  marker naming the block's date. An export of a day deletes marked events
  whose block is no longer on that day (`_sweep_orphans`). An update does
  not rewrite the marker.

## Decisions (defaults proposed; each is your call)

**Which block a press picks up**

- **B1** A press on a box picks up the box's earliest block, by the rule that
  colours the box: a block continued from above first, then grid order. A box
  holding more than one block gives up only that one. The others are moved in
  the day.
- **B2** Item, buffer and break blocks can be dragged. Lunch cannot. It is set
  per date from Day Settings, and moving it would leave one day with two
  lunches and the other with none. Pressing a lunch box does nothing.
- **B3** A press with no motion is not a drag (PD-M10.3, as the day does), so
  a plain click on a box does nothing.

**Where it lands**

- **B4** The block's start goes on the box it is dropped on, on that box's
  date, as in the day. A drop on the same date moves it within that day.
- **B5** The drop runs the same checks as an item drop in the week (M6.5),
  against the target date:
  - the date has blocks from an earlier version with no box: refused,
    "Open Fri 06 first";
  - a meeting, a full box, or a box outside the day (`can_place`, with that
    date's span and meetings);
  - the item already has a block on that date (PF-M2). Moving a block within
    its own date is not refused by its own presence;
  - a non-work date asks first, and the yes is remembered for that date (D5);
  - an unread calendar is allowed, and the status says so (D4).
- **B6** The write is one transaction in `db_manager`: a new
  `move_block_to_date(block_id, to_date, slot_index, bounds, day_span)`
  checks the fit on the target date, sets `block_date`, and settles the box,
  position and times. `place_block_at` stays as it is for the day.
- **B7** The screen stays in the week and redraws it. The status reads
  "Moved Report to Fri 20 at 10:00".

**Google Calendar**

- **B8** Moving an exported block to **another date** clears its
  `calendar_event_id`, through `set_block_calendar_event_id`, its only
  writer. The next export of the new date makes a fresh event with the right
  marker. The next export of the old date removes the old event as an orphan.
  If the id were kept, the event's marker would still name the old date, and
  a later delete of the block would leave that event in Google for good. The
  status adds "— export Thu 19 again to remove it from Google Calendar".
  A move within one date keeps the id, as today.

**Clicks**

- **B9** Only a column's date heading opens the day. Boxes, titles and
  totals no longer do. The heading keeps its hand cursor.
- **B10** The status line wording for a drop that misses a box changes from
  "click a day to open it" to "click a date to open it". So does the wording
  that refuses a meeting drag in the week.

**Unchanged:** the Day / Week button; item drops in the week (M6.5); every
day-view drag; the Clear day, Autoload, Buffer, Break and Export buttons,
which stay disabled in the week.

## Acceptance criteria → tests

Logic tests go in `tests/test_time_block_crud.py`, with no Tk. Screen tests
go in `tests/test_plan_screen_week.py`, on an unmapped screen. Each test is
mutation-checked against the verbatim line it names.

| ID | Criterion | Test |
|---|---|---|
| CIP-M6.7a | `move_block_to_date` writes the new date, box and times in one go | `test_cipm67_a_block_moves_to_another_date` |
| CIP-M6.7b | A move that does not fit on the target date writes nothing | `test_cipm67_a_move_that_does_not_fit_writes_nothing` |
| CIP-M6.7c | A move to another date clears the event id; one within a date keeps it | `test_cipm67_a_move_to_another_date_forgets_its_event` |
| CIP-M6.7d | A press on a box picks up its earliest block; lunch picks up nothing | `test_cipm67_a_press_picks_up_the_boxs_first_block` |
| CIP-M6.7e | A drop on another date's free box moves the block there; the week stays | `test_cipm67_a_drop_moves_the_block_to_that_date` |
| CIP-M6.7f | A meeting box, a full box, and an item already on that date refuse and write nothing | `test_cipm67_the_target_dates_rules_refuse` |
| CIP-M6.7g | A non-work date asks, and the answer is for that date | `test_cipm67_a_non_work_date_asks_first` |
| CIP-M6.7h | The status names the date, and the old date when an event was cleared | `test_cipm67_the_status_names_the_dates` |
| CIP-M6.8a | A click on a box, a title or a total stays in the week | `test_cipm68_a_click_off_the_date_stays_in_the_week` |
| CIP-M6.8b | A click on the date heading opens that day | `test_cipm68_the_date_heading_opens_the_day` |

Existing tests that change:

- The tests that a click on a box or a total opens the day change for reason
  (b): the behaviour changes on purpose.
- The tests that assert "click a day" wording change for the same reason.

## Build order

1. `db_manager.move_block_to_date`, tests first.
2. The week's block drag: press bindings on boxes and titles, the drop in
   `on_drag_release` for `kind == "block"` in week mode, the hover outline.
3. Clicks: `_bind_open` on headings only.
4. Docs:
   - spec §8 rows M6.7 and M6.8, with D7 marked as reversed;
   - `docs/USER_GUIDE.md` week section;
   - `CHANGELOG.md`, `docs/spec_coverage.md`;
   - walk checklist steps in `docs/unused-docs/changes/2026-11-14-plan-week-improvements.md`.
5. `/csdp`. A new write path in `db_manager`, so the full sweep applies:
   `learning-qa` plus a cold correctness pass.

Expected size: about 120 lines of `src/` and about 12 tests.

## Adjacent issues found, not fixed

- The export's update path never rewrites an event's date marker
  (`calendar_exporter._update`). No move changes a block's date today, so
  nothing reaches it. B8 avoids it rather than fixing it.
- A press on a box that holds two blocks can only pick up the first (B1). The
  day is the place to move the second.
