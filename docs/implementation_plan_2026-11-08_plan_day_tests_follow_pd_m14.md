# Implementation plan — the plan-day tests follow PD-M14

**Date:** 2026-11-08
**Status:** approved 2026-11-08 and built the same day — see **Outcome** below
for the three places the build departed from this plan
**Prefix:** PDT (plan-day tests)
**Supersedes the merge of:** `refs/heads/claude/plan-day-range-pdm13` (preserved at `c8125af`)

---

## Outcome (written after the build, 2026-11-08)

Built. Per-criterion status is in `docs/spec_coverage.md`; the handoff note is
`docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md`. **The plan's criteria are left in place** rather than
rewritten to match what shipped, so that what was planned can be compared with
what
shipped. Three things below are now wrong, and are wrong here on purpose:

1. **PDT-M1's "primary vehicle" was not the one used.** This plan says every
   rewrite "gains a block at an index off the date". The shipped rewrites all
   use **lunch over the box** (`DayBounds(lunch_start=...)`) instead. The
   reason emerged while writing PDT-M1.1: `test_tgm31` asserts the
   `on_settings_saved` status line ("N blocks no longer fit the day"), which
   only a settings change produces. An off-the-date index would have forced
   that assertion to be dropped. Lunch keeps it, and is the realistic user
   path besides — `plan_settings_dialog.py` validates neither the lunch start
   against the day's hours nor the lunch length beyond a day.
2. **PDT-M4.2 says the two `models.py` file references are "two lines and it is
   what keeps this meta test red, so it is fixed here".** It was not fixed. The
   references name two test files and three tests for PRI-M1/M2 that have
   **never existed** in any branch, so there was nothing to repoint. Closing it
   means writing the three tests, which is the priority batch's work. Deleting
   the `Tests:` lines would have greened the meta test while hiding the gap.
   `spec_coverage.md` records PDT-M4.2 as `not done`, and it is now `BACKLOG.md`
   item 2.
3. **The "Done means" criterion is not met.** It asks for "CI on `main` down
   from 20 failures to the nine CI-environment ones — a number stated in the
   handoff note and checked against the run". No CI run covers this range yet,
   so the handoff note states local targeted runs only, and the count of what
   is left (**ten**, not nine: the nine plus
   `test_every_referenced_test_file_exists`) is derived from local runs and
   from reading the reference set, not from a CI run.

Two corrections to this plan's own measurements, found by the cold sweep:

- The table of public names lists `block_title` as `main`-only. That is
  **right** — `git grep "def block_title"` finds it nowhere on the branch — but
  it was challenged in review, so it is recorded as checked.
- PDT-M4.1 said "five names", then "seven". Both were wrong. Counted from the
  diff after the build: **8 references repointed and 1 dropped across 3 rows** of `docs/spec_coverage.md`, and **3 `Tests:` lines** across `src/getmoredone/screens/plan.py` and `src/getmoredone/time_block_layout.py`. The earlier numbers counted distinct
  names in a hand-written list rather than edits in the diff, and the list
  itself held six. `2cd83a3`'s subject still says "seven" and cannot be
  reworded now that it has a child commit; `BACKLOG.md` item 4 records the
  measured count and says so. Corrected in place.

---

## The finding that changes the brief

The brief was "port the branch's `outside` implementation onto `main`'s PD-M14
design". **There is nothing to port.** Measured on `main` at `4ca7116`:

- `tests/test_time_grid.py` — **58 passed**. The `outside` list is fully
  implemented and tested at the layout layer.
- `src/getmoredone/screens/plan.py` — `outside_frame`, `build_outside_group`,
  the `grid()`/`grid_remove()` pair, the P2 "N blocks no longer fit" status,
  and the scrollable holder at `OUTSIDE_GROUP_HEIGHT_PX` are all present
  (lines 607–613, 1050–1191, 935–947).
- `tests/test_plan_screen.py:2345` asserts
  `[b.label for b in screen._grid.outside] == ["never placed"]` and **passes**
  today, so the screen path from a block to the group on screen works.

The branch holds the earlier design, and `main` replaced it on purpose. The
public names each side has that the other does not:

| | names |
|---|---|
| branch only | `drawn_day_slots`, `slot_is_on_the_date`, `_overlaps_lunch` |
| `main` only | `DaySpan`, `DayExtension`, `span_for_blocks`, `template_span`, `extended_span`, `edge_limit_time`, `_stays_inside_the_date`, `block_title` |

`extend_day_for`'s own docstring on `main` records what the branch's mechanism
cost: `slot_index` counts boxes from Day Start, Day Start is one setting shared
by every date, so each drop on **Earlier** moved that setting back permanently
and renumbered every date's blocks to compensate. Both reported faults — the
day start ratcheting to 05:30, and blocks moving on other dates — were that one
mechanism. Porting it back would reintroduce them.

**So the work is not a port. It is bringing nine stale tests and the stale
docstring references up to the design that survived** — repo test rule case
(b), the behaviour changed intentionally. It is the same route in substance
(keep `main`'s design, make the tests fit), with no code to carry over.

## Why the nine fail: one cause, not nine

`main` draws the day from the date's own blocks (`span_for_blocks`, PD-M14.2),
and `PlanScreen.refresh` calls `build_day_grid(blocks, self.bounds)` with **no
span** (`plan.py:1085`), so the drawn day always stretches to cover what the
date holds. **Tightening Day Settings can therefore no longer orphan a block.**
That is PD-M14's point: the hours are "solely for starting a blank plan for the
day".

Six of the nine reach `outside` by exactly that withdrawn route —
`panel.on_settings_saved(DayBounds(day_end="10:00"))` — and now get
`outside=[]`, `span=DaySpan(first=0, last=17)`. The vehicle is stale; the
behaviour each one asserts is still live.

A block still reaches `outside` on `main` by four routes, each already covered
by a passing test in `tests/test_time_grid.py`:

| route | vehicle | passing test today |
|---|---|---|
| index off the date | `slot_index=400` or `-20` | `test_pdm142_a_block_whose_index_leaves_the_date_is_still_surfaced` |
| length past midnight | `120m at slot_index=31` | `test_pdm142_a_block_whose_span_runs_past_midnight_is_surfaced` |
| never placed | `slot_index=None` | `test_a_never_placed_block_is_surfaced_rather_than_assumed_to_be_at_eight` |
| lunch moved over work | lunch box over a placed block | `test_a_block_sitting_in_a_lunch_box_is_surfaced_not_hidden` |

The rewrites use **"index off the date"** as the primary vehicle, because it is
the case `_stays_inside_the_date` exists for and it needs no settings change to
set up.

## Acceptance criteria

Every criterion is an existing test, rewritten. No test is deleted, and no
assertion is weakened: the subject of each assertion stays, only the vehicle
that produces an outside block changes.

### PDT-M1 — the six outside-group tests reach `outside` by a live route

All in `tests/test_plan_screen.py`. Each loses the
`on_settings_saved(DayBounds(day_end=…))` setup and gains a block at an index
off the date.

| ID | test | what it must still assert |
|---|---|---|
| PDT-M1.1 | `test_tgm31_an_outside_block_is_drawn` (1437) | `_grid.outside` is empty before, holds the block after, and the label is drawn in `outside_frame` |
| PDT-M1.2 | `test_every_part_of_an_outside_row_starts_a_drag` (2299) | every descendant of an outside row, not only the row, begins a drag |
| PDT-M1.3 | `test_pbm55_the_settings_reach_the_outside_group_on_screen` (3139) | the holder's height is the configured `drag_schedule_box_height_px` (64), not the default |
| PDT-M1.4 | `test_the_outside_group_does_not_outlive_the_day_that_had_one` (2633) | changing to a day with no outside block empties the group |
| PDT-M1.5 | `test_the_outside_group_scrolls_instead_of_growing_past_the_pane` (3202) | 8 outside blocks, `CTkScrollableFrame`, height `OUTSIDE_GROUP_HEIGHT_PX` |
| PDT-M1.6 | `test_the_outside_group_takes_no_room_on_a_day_without_one` (3233) | `grid_info() == {}` with none, `!= {}` with one, `== {}` again after |

**PDT-M1.3 carries a risk worth naming.** It fails today at
`holder.cget("height") == 64` with 60, having found an **in-grid** block
because none was outside. 60 is what the in-grid path draws. Whether the
outside path honours the setting is therefore **not yet established** — this
test has never once run against a real outside holder. If it still reads 60
after the rewrite, that is a genuine PB-M5.5 defect in `build_outside_group`,
not a stale test, and it gets a code fix. **This is the one criterion that may
turn out to need `src/` work.** It will be reported either way.

### PDT-M2 — `test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day`

`tests/test_plan_screen.py:587`. It asserts `panel.bounds.day_start < started_at`
and `"The day now runs" in status`. PD-M14.1 withdrew the first (the hours are
not written) and reworded the second to "The day now shows".

It also directly contradicts `test_pdm141_a_drop_on_earlier_writes_no_settings`
(5301), which asserts `screen.bounds.day_start == "08:00"` with the message
"the screen took a new day", and whose docstring says it *replaces*
`test_pdm52_a_drop_above_moves_day_start_back`. Two tests on `main` assert
opposite things about the same call.

- **PDT-M2.1** — PD-M13.1's own subject is kept and is what the test is about:
  the drop on a non-work day **asks nothing** (`messageboxes == []`) and
  **writes the block** (`len(manager.get_time_blocks(SATURDAY)) == 1`). Both
  assertions stay verbatim.
- **PDT-M2.2** — the capability the report asked for ("I can't move an item
  into the early or late extended sections") is asserted against the surviving
  mechanism: the block lands at a **negative slot index**, earlier than the
  day start, as `test_pdm141_a_drop_on_earlier_writes_no_settings` already
  shows at `("Early start", -1, "07:30")`. This replaces
  `panel.bounds.day_start < started_at`.
- **PDT-M2.3** — the status text assertion follows the implementation: "The day
  now shows", and `"not a regular work day"` is kept.
- **PDT-M2.4** — the docstring records that the Day Settings half was withdrawn
  by PD-M14.1 and names it, so the next reader does not restore it.

### PDT-M3 — the two PD-M5.4 tests

`tests/test_plan_settings.py:784` and `:829`. Both fail on their **preconditions**
(`plan_day_start == "07:30"`, `plan_day_end == "17:30"`) — the write PD-M14.1
removed. Their subject, that `plan_day_shape_unconfirmed` is left alone, is now
guaranteed structurally: `extend_day_for` writes no settings at all.

- **PDT-M3.1** — both tests keep the flag assertions and drop the withdrawn
  preconditions, replacing them with a precondition that *can* fail: the block
  was written (`get_time_blocks` holds it). A test whose premise cannot be
  reached asserts nothing.
- **PDT-M3.2** — each docstring records that the stronger guarantee is
  `test_pdm141_a_drop_on_earlier_never_calls_save` (5323), and links to it, so
  the pair is not read as the only thing standing between the user and the
  flag.

### PDT-M4 — the stale docstring references

Both meta tests are red on references the PD-M14 rewrite left behind.

- **PDT-M4.1** — `test_every_referenced_test_name_exists` passes. The six names to settle: `test_pdm52_a_drop_above_moves_day_start_back`
  (`plan.py`, withdrawn — point it at its replacement),
  `test_pdm146_each_end_names_the_time_it_stops_at` and
  `test_tgm31_blocks_outside_the_grid_are_surfaced` (`time_block_layout.py`),
  and three in `docs/spec_coverage.md`
  (`test_pdm52_existing_blocks_keep_their_clock_times`,
  `test_pdm5_an_item_that_would_cross_midnight_is_refused`,
  `test_pdm58_the_day_cannot_cross_midnight`).
  Each is repointed at the test that now covers it, or the claim is dropped if
  nothing does — **not** repointed at an approximate match.
- **PDT-M4.2** — `test_every_referenced_test_file_exists` passes:
  `src/getmoredone/models.py` names `tests/test_priority_floor_and_cap.py` and
  `tests/test_priority_floor_form.py`, neither of which exists.
  **Out of the plan-day family** — it belongs to the Priority Levels work. It
  is two lines and it is what keeps this meta test red, so it is fixed here and
  called out as adjacent rather than left to keep the suite red.

### PDT-M5 — the documents

- **PDT-M5.1** — `BACKLOG.md`'s "What `main` needs" section is rewritten: the
  three routes are resolved, "port" is recorded as "nothing to port", and the
  branch's disposition is stated.
- **PDT-M5.2** — `docs/spec_coverage.md` gains the PDT rows and loses the three
  dead references from PDT-M4.1.
- **PDT-M5.3** — `docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md`, from
  `.agents/templates/handoff-note.md`.
- **PDT-M5.4** — `docs/DOCUMENTATION_INDEX.md` lists this plan and the handoff
  note. Added **last**, after the rest, per the conflict-surface rule.
- **PDT-M5.5** — `NOTES.md`'s "Where `main` stands" is updated to the real red
  count and its two families.

## Not code-testable

- **PDT-N1 — the branch's disposition.** That `refs/heads/claude/plan-day-range-pdm13`
  is superseded rather than lost is a fact about a git ref, not about this
  working tree. No test can assert it. **Human review proposal:** the branch
  stays unmerged at `c8125af`, recorded in `BACKLOG.md` and in the handoff
  note; deleting it is a separate decision I will not take. It **is** pushed —
  `refs/remotes/origin/claude/plan-day-range-pdm13` is at the same commit — so
  nothing on it depends on this checkout surviving.
- **PDT-N2 — that the rewritten tests still protect the original behaviour.**
  Each rewrite keeps its assertions and changes only its setup, which mutation
  testing proves can still fail, but "this is still the right thing to assert"
  is a judgement. **Human review proposal:** the cold sweep reads each rewrite
  against the test it replaces, and the handoff note tabulates old vehicle →
  new vehicle → assertions kept.

## Out of scope — adjacent issues found, not fixed

`main` is red on **20** tests, not 9. Of the other nine, **eight pass locally
and fail only in CI**; the ninth is skipped locally, as the paragraph after the
list sets out:

`test_t51_a_modal_drops_the_timers_always_on_top`,
`test_t52_the_timer_is_topmost_again_afterwards`,
`test_t56_a_second_modal_does_not_hand_the_flag_back_early`,
`test_t57_an_unbalanced_resume_does_not_break_the_next_modal`,
`test_wt_m6b6_a_notice_lowers_an_always_on_top_parent`,
`test_alpha_still_passes_through_the_attributes_wrapper`,
`test_raw_tkinter_windows_are_hidden_and_registered_too`,
`test_pbm61_a_tall_row_keeps_its_two_lines_together`,
`test_updm14_zero_width_body_is_a_noop`.

Verified: **eight of the nine pass** under
`GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest` locally; the ninth,
`test_pbm61_a_tall_row_keeps_its_two_lines_together`, takes the
`mapped_windows` fixture, which is exactly what that variable skips, so it is
skipped rather than passing. Seven of them are the
always-on-top / window-geometry family, failing on a CI runner with no window
manager — the same class as the `-topmost` skip added yesterday, which fixed
one of its members. **A different batch, a different fix, and not touched
here.** Filed in `BACKLOG.md` by PDT-M5.1.

## Implementation order

Tests before docs, and `src/` only if PDT-M1.3 forces it. Test changes commit
separately from any `src/` change.

1. **PDT-M1.1** first — the smallest rewrite, and it establishes the new
   vehicle the other five reuse. Mutation-tested before the rest are written.
2. **PDT-M1.2, M1.4, M1.5, M1.6** — the same vehicle, four files' worth of
   setup. No dependencies among them.
3. **PDT-M1.3** — last of the six, because it is the one that may expose a
   defect. If it does: stop, report it, fix `build_outside_group`, commit the
   `src/` change on its own.
4. **PDT-M2** — independent of PDT-M1.
5. **PDT-M3** — depends on nothing; different file.
6. **PDT-M4** — after M1–M3, because those rewrites may themselves change which
   test names the docstrings should point at.
7. **PDT-M5** — docs, after the code is settled. M5.4 last of all.
8. **Sweep** — 1 warm pass, then 1 cold pass minimum, per the repo's sweep
   budget. The cold pass gets the diff and the range and none of this plan.

## Verification

Targeted runs only, per the repo rule:

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest \
  tests/test_plan_screen.py tests/test_plan_settings.py tests/test_time_grid.py \
  tests/test_time_block_layout.py -q
```

plus the two meta tests by name. The full suite is left to CI.

**Done means:** those four files and the two meta tests green locally, and CI
on `main` down from 20 failures to the nine CI-environment ones — a number
stated in the handoff note and checked against the run, not assumed.
