# Implementation plan — Plan week view: resize, Category colours, drop (2026-11-14)

Status: **approved and built 2026-11-14.** Not walked on screen.
Spec: `docs/spec_2026-11-08_calendar_into_the_plan.md` §8 (CIP-M6) — this adds
CIP-M6.3, M6.4, M6.5 and answers §9 "Whether the week view is editable".
Builds on: `implementation_plan_2026-11-13_calendar_into_the_plan_week.md` (W1–W8).

The user's three requirements:

1. The week view resizes as the panel resizes.
2. Box colours are the action items' Category colours.
3. An Action Item can be dragged onto a box in the week view.

Requirement 3 reverses W4 ("the week is read-only") for one gesture only.

## What the code does today

- `screens/plan_week_view.py::_draw_week_grid` draws fixed boxes:
  `WEEK_COLUMN_WIDTH_PX = 64`, `WEEK_BOX_HEIGHT_PX = 12`, with column weight 0.
  A wide pane leaves empty space, and a narrow one clips the columns.
- `week_box_colors()` gives one token per kind: meeting, planned, free, unread.
  Every planned box is the padding grey, whatever item it holds.
- `load_week` empties `_slot_frames`, so a release over the week finds no box
  and says "The week is read-only — click a day to plan it".
- The day drop path (`on_drag_release` → `_drop_refusal` → `_allow_this_day` →
  `block_item`) reads `self.selected_date`, `self._grid` and `self._committed`
  throughout. In the week, those describe the last day drawn, not the box's date.
- `plan_week.read_week` already builds each date's grid with that date's own
  blocks and commitments (M6.2). The grid is counted into `DaySummary.boxes`
  and then discarded.

## Decisions (defaults proposed; each is your call)

**Resize**

- **R1 Width.** The seven day columns share the scroll frame's width equally
  (`weight=1`, one `uniform` group), and the boxes stretch across their column.
  Each column has a floor of 40 px. The test checks that the time labels, the
  two arrows and seven floors fit inside `day_width_floor()`, so the pane's
  existing floor never clips a column.
- **R2 Height.** Box height = (visible scroll height − heading row − totals
  rows) ÷ number of rows, with a floor of 12 px (today's size) and no cap.
  Below the floor, the grid scrolls as it does now.
- **R3 When.** On `<Configure>` of the scroll frame, the existing boxes are
  reconfigured. Nothing is re-read or redrawn. The size is set only when it
  changes, the same guard as `apply_items_width`, so the resize cannot loop.
- **R4** Leaving the week puts columns 1–8 back to how the day draws them.

**Colours**

- **C1** A box holding an item's Time Block is filled with that item's
  Category colour. The lookup is the one the day chips use
  (`_segment_color_resolver`). If a box holds more than one block, the
  earliest-starting one sets the colour: a continued block before a starting
  one, then grid order.
- **C2** An item with no Category colour, and buffer, break and lunch blocks
  (including the lunch slot), keep today's padding colour.
- **C3** Meeting, free and unread boxes do not change. A meeting still wins
  a box (`box_kind`).
- **C4** The boxes carry no text, so there is no foreground to derive
  contrast for. This is how the box meets the AGENTS.md data-colour rule. No
  new colour literal is added.

**Drop**

- **D1 Which day.** The block goes on the box's own date. The screen stays in
  the week and redraws it. The status names the date: "Blocked 30m for X on
  Thu 19 at 10:00".
- **D2 Which checks.** The day's own refusals run against that date's own
  blocks, grid span and commitments:
  - already blocked that day (PF-M2);
  - a box held by a meeting, a full box, or a box outside the day (`can_place`);
  - the write-side check in `db_manager.add_block_at`.

  To make this work, `_blocked_today`, `_already_blocked_text`,
  `_drop_refusal`, `_require_block_day`, `_allow_this_day` and `block_item`
  take a `day` (and its grid). It defaults to the selected day, so the day
  view's calls do not change. `read_week` keeps each date's grid on its
  summary so the drop does not rebuild it.
- **D3 Targets.** Free and planned boxes accept a drop, and a planned box takes
  up to four blocks, the same as the day. A meeting box is refused with the
  day's wording. A drop on a heading, a total or a gap does nothing and keeps
  today's sentence, re-worded to "Drop on a box to plan it — click a day to
  open it".
- **D4 Unread calendar.** Allowed, the same as the day. The day lets you drop
  onto a date whose calendar was never read. The status adds "— calendar not
  read for that day".
- **D5 Non-work day.** The question names the box's date. The yes is
  remembered for that date (`_work_anyway`), the same as the day.
- **D6** During the drag, the box under the pointer gets the day's hover
  outline.
- **D7 What stays locked.** Clear day, Autoload, Buffer, Break and Export stay
  disabled in the week. Clicking a column still opens that day. Only item drags
  exist here: block and meeting drags start from day chips, and the week does
  not draw any.

## Acceptance criteria → tests

New tests go in `tests/test_plan_screen_week.py` (on an unmapped screen) and
`tests/test_plan_week.py` (logic only, no Tk). Each test is mutation-checked
against the verbatim line it names.

| ID | Criterion | Test |
|---|---|---|
| CIP-M6.3a | Columns share the width: a wider scroll frame gives wider boxes, equal across the seven | `test_cipm63_columns_follow_the_pane_width` |
| CIP-M6.3b | Box height follows the visible height, never below 12 px | `test_cipm63_boxes_follow_the_pane_height_to_a_floor` |
| CIP-M6.3c | A `<Configure>` with an unchanged size reconfigures nothing | `test_cipm63_an_unchanged_size_sets_nothing` |
| CIP-M6.3d | Seven floors plus labels and arrows fit in `day_width_floor()` | `test_cipm63_the_week_fits_the_day_pane_floor` |
| CIP-M6.3e | Leaving the week restores the day's column setup | `test_cipm63_leaving_the_week_restores_the_columns` |
| CIP-M6.4a | A box's item comes from its grid slot, earliest block first | `test_cipm64_a_box_names_its_earliest_item` (logic) |
| CIP-M6.4b | An item box is filled with its Category colour | `test_cipm64_an_item_box_has_its_category_colour` |
| CIP-M6.4c | No Category colour, padding, or lunch keeps the planned token; a meeting keeps its own | `test_cipm64_uncoloured_and_padding_keep_the_planned_token` |
| CIP-M6.5a | A drop on a free box of another date writes the block on that date and slot | `test_cipm65_a_drop_writes_on_the_boxs_date` |
| CIP-M6.5b | The refusal reads that date's blocks, not the selected day's (already blocked, full) | `test_cipm65_the_refusal_reads_the_boxs_date` |
| CIP-M6.5c | A meeting box on that date refuses and writes nothing | `test_cipm65_a_meeting_box_refuses` |
| CIP-M6.5d | The week stays up and redraws; the status names the date | `test_cipm65_the_week_stays_and_names_the_date` |
| CIP-M6.5e | A drop on no box writes nothing and says so | `test_cipm65_a_drop_on_no_box_writes_nothing` |
| CIP-M6.5f | The non-work-day question and its remembered yes are for the box's date | `test_cipm65_the_question_is_about_the_boxs_date` |
| CIP-M6.5g | The day view's drop is unchanged | existing `tests/test_plan_screen.py` TG-M9 / PF-M1 / PF-M2 tests, run as they are |
| CIP-M6.4 | Padding first in a box colours nothing | `test_cipm64_padding_first_colours_nothing` (logic) |

No existing test asserted a week drop is refused, so no test changed. Two
tests were added during the build: `test_cipm65_an_unread_date_is_said` (D4)
and `test_cipm65_the_box_under_the_pointer_is_outlined` (D6).

## Build order

1. Logic: `plan_week` keeps the grid, and adds an earliest-item-per-box
   helper. Tests first.
2. Drop: give the six day methods a `day` parameter, then add the week's drop
   targets and hover. Tests first.
3. Colours, then resize, in `plan_week_view.py`.
4. Docs:
   - spec §8 rows M6.3–M6.5 and §9 answered;
   - `docs/USER_GUIDE.md` week section;
   - `CHANGELOG.md`, `NOTES.md`, `docs/spec_coverage.md`;
   - a walk checklist in `docs/unused-docs/changes/`.
5. `/csdp`. This touches `src/` and the drop, a write path, so it gets the
   full sweep: `learning-qa` plus a cold correctness pass.

Expected size: about 150–200 lines of `src/`, mostly the `day` parameter
threaded through the six methods. About 15 tests.

## Adjacent issues found, not fixed

- A closed (non-work) day's boxes are shaded free in the week (batch-3 low,
  already recorded). The drop makes it more visible, because a drop there asks
  the non-work-day question.
- The header names only one flagged day (batch-3 low, already recorded).
- `_drop_refusal` and `block_item` each read `get_time_blocks` for the same
  date in one gesture. This is harmless, and it is left alone because
  `block_item` must re-check as the write path.
