# Implementation plan — the Plan screen as a 30-minute grid

Status: **awaiting approval**. No implementation code is written until this is
approved (global planning rule: "Implement this" means "begin the planning
step").

Supersedes the day model in
`docs/implementation_plan_2026-11-05_time_blocks.md` (TB-M1…TB-M12). That plan
shipped and is on `main`; this one changes how a day is *shaped*, and says
below exactly which of its parts are retired and why.

---

## Why

Two things, from the screenshots of the running app on 2026-11-05.

1. **The Plan screen should read like the Schedule screen.** They do the same
   kind of work — action items on the left, somewhere to drop them on the
   right — and today they look nothing alike. Schedule drops an item onto a
   *named box* (a date). Plan should drop an item onto a *named box* too (a
   half hour).
2. **The Day Plan pane is visibly broken.** Ten blocks render as bare coloured
   slivers: no title, no time, no minutes. Diagnosed below; it is real, and no
   test in the suite can see it.

---

## What is actually there now — checked before planning

- `src/getmoredone/screens/plan.py` (~740 lines), `plan_blocks.py` (~270),
  `time_block_layout.py` (~600). The layout module imports no GUI toolkit and
  must not.
- A day is an **order**, not a set of times. `time_blocks.position` is stored
  and is the truth; `start_time` / `end_time` are derived by `pack_day` from
  (order + lengths + day bounds) and written back. Reorder, resize, delete and
  a settings change all reduce to one operation: repack the day.
- `time_blocks` columns: `id, item_id, block_date, start_time, end_time,
  planned_minutes, block_type, position`, with `idx_blocks_date_position` on
  `(block_date, position)`.
- **Nothing outside the Plan screen reads `time_blocks`.** Verified by grep:
  every other `start_time` hit in `src/` is `meeting_start_time` on
  `ActionItem`, which is unrelated. So the stored clock columns have exactly
  one consumer, and changing how they are derived breaks no other screen.

### The sliver bug, diagnosed

`build_block_row` (`plan_blocks.py:176`) calls `frame.grid_propagate(False)`
so the frame keeps the height that encodes the block's length. With
propagation off, a frame no longer takes its size from its children — it must
get a width from somewhere else, and nothing gives it one: the only column
configuration is `grid_columnconfigure(2, weight=1)`, which distributes *spare*
width and requests none.

The proof that this is the mechanism is in the same codebase. Schedule's date
boxes call `grid_propagate(False)` too (`drag_schedule.py:1034`) and render
correctly, because `_configure_date_box_columns` gives **every** column a
`minsize`. That is the missing half.

**No test can see it**, which is the more important half of the finding. The
geometry tests assert behaviour — a drag creates a block, a reorder changes the
order — and never that a row is as wide as its pane or that its labels are
visible. Worse, the helper they aim with reads:

```python
x = widget.winfo_rootx() + max(1, widget.winfo_width() // 2)
```

That `max(1, …)` is exactly what keeps a fully collapsed row clickable in the
test. A row 8px wide passes every one of them. This is P27 with a geometric
face: a guard that cannot fail, over a screen that is broken. TG-M3.2 below
fixes the gap, not just the row.

---

## Decisions taken (answered by the user, 2026-11-05)

1. **Fixed grid, drop on a slot.** Every half hour from Day Start to Day End is
   a box, drawn whether or not anything is in it. An item is dropped on the box
   you want it at. **Gaps are allowed** — an empty 09:00 between two filled
   boxes is a legitimate day, not a state to be packed away.
2. **Odd lengths round up.** A 45-minute item occupies two boxes. Its own
   number stays 45; the grid it occupies is 60. Both are shown, because they
   are different facts (see TG-M3.9).
3. **A box is worth 30 minutes however many tasks are in it.** Two tasks in the
   10:00 box means the day has spent 30 minutes there, not 60.

---

## The model

A block is `(slot_index, span)` on a grid, where:

- `slot_index` is the 0-based half hour from Day Start. **Relative to Day
  Start, not absolute**: when Day Start moves, every day re-times itself with
  no write at all. This is what retires `repack_all_days`.
- `span = ceil(planned_minutes / 30)`, minimum 1. **Derived, never stored** —
  two columns that can disagree about one fact is the bug class this project
  already catalogues (P6).
- `position` keeps its name and its index, but now orders blocks **within one
  slot**, which is what makes "more than one task in a box" representable.

`start_time` / `end_time` stay in the table and stay derived, now from
`slot_index` rather than from cumulative lengths. Keeping them written costs
one assignment, keeps the table readable in `sqlite3`, and keeps the
`end == start + duration` invariant and its tests meaningful.

---

## M1 — Grid arithmetic (pure functions, no display)

All of it in `time_block_layout.py`, all of it testable headless.

### TG-M1 — The grid itself
`day_grid(bounds) -> List[Slot]`, one `Slot` per half hour from Day Start to
Day End, each carrying its index, its start and end minutes, and whether it is
a lunch slot. Lunch is **slots marked unavailable**, not a band that pushes
things — in a fixed grid nothing needs pushing.

### TG-M2 — Placement
`slots_for_minutes(minutes)` rounds up, minimum 1.
`can_place(occupancy, slot_index, span)` answers whether a block fits: inside
the grid, not across a lunch slot, not past the last slot.
`place(…)` returns the new occupancy or a named refusal reason — a reason, not
a bool, because four call sites report it and a refusal worded four ways reads
as four different bugs (the lesson `DAY_TOO_FULL` already taught this batch).

### TG-M3 — Blocks the grid cannot hold
A day whose Day End moved earlier can hold blocks that no longer have a slot.
They are **returned and flagged, never dropped** (P2). The pane draws them in
an "outside the day" group under the grid with the reason.

---

## M2 — Schema and CRUD

### TG-M4 — `slot_index`
Guarded idempotent migration adding `slot_index INTEGER NOT NULL DEFAULT 0`,
per-column like the existing one, and an index on `(block_date, slot_index,
position)`.

### TG-M5 — Migrating the days already stored
Existing rows carry a real `start_time`. The migration maps each to the slot it
falls in, relative to that database's current Day Start. A row with an empty
`start_time` (written between a create and its repack) falls back to its
`position` order. Both paths get a dirty-state test (P8).

### TG-M6 — The writes
`place_block_at(block_id, slot_index)`, `add_block_at(…)`,
`set_block_span(…)`, each inside one transaction with the derived-time write,
as now. Two blocks sharing a `slot_index` is legal and ordered by `position`.

---

## M3 — The pane

### TG-M7 — The grid renders
Every slot from Day Start to Day End is drawn, empty ones included, each
labelled with its time, following `_configure_date_box_columns`' shape: every
column gets a `minsize` so the row has a width to request.

### TG-M8 — Row width is asserted, not assumed
The fix for the sliver bug, and the test that would have caught it: with a
mapped window, a block row's width is within a few pixels of the pane's, and
its title label is non-empty and `winfo_ismapped()`. Plus the removal of
`max(1, …)` from `_aim_pointer_at`, so a collapsed row makes the *drag* tests
fail too instead of being silently compensated for.

### TG-M9 — Drop an item on a slot
The drop target is the slot under the pointer, not the pane. A drop on an
occupied or unavailable slot is refused with its reason on the status line.

### TG-M10 — More than one task in a box
A second item dropped on a filled box joins it when the box has room by the
rules above; the box draws both titles.

### TG-M11 — Move, resize, delete
Dragging a block to another slot moves it there. Right-click sets its length,
which changes its span; a length that would not fit from where it sits is
refused with the reason rather than silently moving the block.

### TG-M12 — The day summary
Three numbers, because they are three different facts and collapsing them is
how the 45/60 question becomes a lie: **boxes used**, **time occupied** (boxes
× 30), **time planned** (the items' own minutes).

---

## What this retires, and why that is deliberate

| Retired | Reason |
|---|---|
| `pack_day`, `repack_day`, `repack_all_days` | A fixed grid derives times from `slot_index`; there is nothing to pack. |
| `DayTooFullError` and its four screen handlers | The grid is bounded by Day End, so a day cannot run past what `HH:MM` can express. The ceiling becomes unreachable. |
| The "past day end" overflow warning | Nothing can be placed past Day End, so the warning has no state to report. Replaced by TG-M3's "outside the day" group, which is the case that *can* still happen. |

These are removals of code that is correct and tested. They are listed so the
deletion is a decision on the record rather than something noticed in a diff —
**dead guards left in place are the thing this repo's own checklist (P27)
warns about**, so if the plan is approved they go, tests included.

A compaction action ("tidy the day", pulling blocks up into the earliest slots)
is the natural home for the packing arithmetic if it is wanted later. It is
**not** in this plan — gaps are legitimate per decision 1, so compaction is a
user choice, not a layout rule.

---

## Acceptance criteria → tests

| ID | Criterion | Test |
|---|---|---|
| TG-M1.1 | `day_grid` yields one slot per half hour from Day Start to Day End inclusive of the last whole slot | `tests/test_time_grid.py::test_tgm11_grid_covers_the_day_in_half_hours` |
| TG-M1.2 | Lunch slots are marked unavailable and are **not** omitted from the grid | `::test_tgm12_lunch_slots_are_marked_not_removed` |
| TG-M1.3 | A Day End that is not on a half hour yields no partial trailing slot | `::test_tgm13_a_ragged_day_end_yields_no_partial_slot` |
| TG-M2.1 | `slots_for_minutes` rounds up: 30→1, 45→2, 60→2, 1→1 | `::test_tgm21_odd_lengths_round_up` |
| TG-M2.2 | **Adversarial (P7)** — a 2-slot block whose second slot is lunch is refused, not drawn across it | `::test_tgm22_a_span_cannot_cross_lunch` |
| TG-M2.3 | A refusal names its reason; every reason is a distinct named value | `::test_tgm23_each_refusal_has_its_own_reason` |
| TG-M2.4 | **Real scale (P9)** — a 9-hour day fully occupied: the 19th placement is refused, the 18 placed are all returned | `::test_tgm24_a_full_day_refuses_the_next_one` |
| TG-M3.1 | A block whose slot no longer exists is returned flagged, never dropped | `::test_tgm31_blocks_outside_the_grid_are_surfaced` |
| TG-M4.1 | Migration adds `slot_index`, is idempotent on a second run | `tests/test_time_block_schema.py::test_tgm41_migration_adds_slot_index_idempotently` |
| TG-M5.1 | A row stored at `09:30` under an 08:00 Day Start migrates to `slot_index` 3 | `::test_tgm51_existing_times_map_to_slots` |
| TG-M5.2 | **Dirty state (P8)** — a row with an empty `start_time` migrates by `position` and does not raise | `::test_tgm52_a_timeless_row_migrates_by_position` |
| TG-M6.1 | Two blocks on one `slot_index` round-trip, ordered by `position` | `tests/test_time_block_crud.py::test_tgm61_two_blocks_share_a_slot` |
| TG-M6.2 | A move writes the slot **and** the derived times in one transaction; a failure writes neither | `::test_tgm62_a_failed_move_writes_nothing` |
| TG-M6.3 | Every written row satisfies `end == start + planned_minutes` | `::test_tgm63_every_row_says_start_plus_duration` |
| TG-M6.4 | Day Start changing re-times every day with **no** write to `time_blocks` | `::test_tgm64_a_day_start_change_writes_no_rows` |
| TG-M7.1 | Every slot in the grid is drawn, empty ones included | `tests/test_plan_screen.py::test_tgm71_every_slot_is_drawn` |
| **TG-M8.1** | **A block row is within 8px of its pane's width** (the sliver bug) | `::test_tgm81_a_block_row_fills_its_pane` *(needs `mapped_windows`)* |
| **TG-M8.2** | **A block row's title label is non-empty and mapped** | `::test_tgm82_a_block_row_shows_its_title` *(needs `mapped_windows`)* |
| TG-M8.3 | `_aim_pointer_at` no longer floors the width to 1 — a collapsed row fails the drag tests | `::test_tgm83_the_drag_helper_aims_at_a_real_width` |
| TG-M9.1 | Dropping an item on the 10:00 slot creates a block at `slot_index` 4, not at the end of the day | `::test_tgm91_a_drop_lands_on_the_slot_under_the_pointer` |
| TG-M9.2 | A drop on a lunch slot is refused, with the reason on the status line and nothing written | `::test_tgm92_a_drop_on_lunch_is_refused_and_says_why` |
| TG-M10.1 | A second item dropped on a filled box joins it; both titles are drawn | `::test_tgm101_two_tasks_share_a_box` |
| TG-M11.1 | A real press-and-release moves a block to the slot it was dropped on | `::test_tgm111_a_real_drag_moves_a_block_between_slots` *(needs `mapped_windows`)* |
| TG-M11.2 | A resize that would not fit from where the block sits is refused and the block does not move | `::test_tgm112_a_resize_that_does_not_fit_is_refused` |
| TG-M12.1 | A 45-minute item in a day reports 2 boxes, 60m occupied, 45m planned — all three | `::test_tgm121_the_summary_separates_occupied_from_planned` |

### Criteria that cannot be made code-testable

| What | Why | Proposed human review |
|---|---|---|
| Whether the grid *reads* as a day at full size | Pixel judgement, not a predicate | Dave runs `./start-demo.sh` and looks, once the grid renders |
| Whether macOS delivers right-click as `<Button-3>` or `<Button-2>` here | Platform behaviour this machine must answer | Both stay bound; Dave confirms the menu opens on his trackpad |

TG-M8.1 and TG-M8.2 are the two that convert "it looks broken" into a
predicate, which is why they are in the table rather than in this one.

---

## Implementation order and dependencies

1. **M1 (TG-M1…TG-M3)** — pure arithmetic, no dependencies, all headless.
   Nothing else can be built honestly before the grid rules exist.
2. **M2 (TG-M4…TG-M6)** — needs M1 for `slots_for_minutes` in the migration.
3. **TG-M8** — the sliver fix and its tests. **Deliberately before the rest of
   M3**: it is the one defect a user can see today, it is cheap, and every
   later pane test is written against a pane that is actually laid out.
4. **M3 (TG-M7, TG-M9…TG-M12)** — needs M2 for the writes.
5. **The retirements** — last, because they delete code the earlier steps may
   still be leaning on while in progress.
6. Docs: `docs/USER_GUIDE.md`, `CHANGELOG.md`, `docs/spec_coverage.md`, and a
   handoff note at `docs/changes/<date>-time-grid.md`.

Commits: `src/` and `tests/` separately throughout, per the repo's test rules.

---

## Adjacent issues found, not fixed

Per global rule 10 — flagged in the plan, not swept into the diff.

- **`max(1, widget.winfo_width() // 2)` in `_aim_pointer_at`.** The floor that
  hid the sliver bug. TG-M8.3 removes it, so this one *is* in scope — named
  here because it is a test-quality defect rather than a feature.
- **`build_item_row` has no width guard either.** It renders correctly today
  only because it does not call `grid_propagate(False)`. Nothing stops a future
  edit adding one, and no test would notice. TG-M8.1's assertion should cover
  the item pane too.
- **`add_padding_block`'s capped-default report is dead code**
  (`plan.py:445`, already in `BACKLOG.md` from the re-sweep). It will be
  touched by TG-M11; worth fixing while there rather than carrying it.
- **`AppSettings.load()`'s broad `except Exception`** (`BACKLOG.md`, P40). Not
  in scope, but TG-M6.4 depends on day-bound settings loading correctly, so if
  it misbehaves during this work that is the first place to look.

---

## What this plan does not cover

- Moving a block to another day (in `BACKLOG.md`, still open).
- The demo seed having no start dates, so the Plan item list is empty on a
  fresh demo (in `BACKLOG.md`). Worth doing *before* this is reviewed by hand,
  since the left pane is how the grid gets anything in it.
- The 7-day view. Decision 1 keeps Plan a single-day screen; the weekday
  checkboxes keep their current meaning (which days accept blocks at all).
