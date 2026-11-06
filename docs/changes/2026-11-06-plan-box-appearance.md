# Handoff Note

- Date: 2026-11-06
- Agent: Code
- Topic: plan-box-appearance (PB-M1 to PB-M5)

## Summary

Five changes to how a task is drawn on the Plan screen, plus the defect that
made three of them look like missing features.

The defect: `ctk.CTkFrame` requests 200x200 when neither `width` nor `height`
is given. The priority stripe set only `width`, so its height request was a
constant nobody chose. In a Day Plan box the chip passed that request up and
the box clipped it to 34px, leaving the title laid out around y=100 — drawn,
below everything the box shows. On screen a planned half hour was a bare 6px
bar. The same missing `height=` made every Items-starting row ~200px tall.

- **PB-M1** — `priority_stripe_colors()`, a brighter table for the bar, held
  to the 3:1 WCAG non-text bar. `priority_band_colors()` is untouched and stays
  at 4.5:1, because PB-M4 puts a band colour behind text and that headroom is
  now load-bearing.
- **PB-M2** — the stripe asks for a height. Title, duration and bars appear.
- **PB-M3** — the three-bar depth stack, now visible, with its own test.
- **PB-M4** — `priority_fill_colors()`: a task is shaded by its band on both
  panes, title colour chosen for the shade. Padding and continuation chips are
  left unshaded.
- **PB-M5** — a task in a box is as tall as `drag_schedule_box_height_px` and
  its title column as wide as `drag_schedule_title_col_width`. Empty half hours
  keep `SLOT_MIN_HEIGHT_PX`. Unusable settings fall back.
- Also: the *no items start on this date* note was clipped at both ends
  (`CTkLabel` centres its text); it is anchored left and wraps to the column.

## Files changed

- `src/getmoredone/theme.py` — two new colour tables
- `src/getmoredone/screens/plan_blocks.py` — `STRIPE_MIN_HEIGHT_PX`,
  `SLOT_TITLE_WIDTH_PX`, `stripe_for_item`/`stripe_for_block`/`fill_for_item`,
  `slot_row_height(chips, chip_height)`, chip fill and sizing
- `src/getmoredone/screens/plan.py` — `box_height()`, `box_title_width()`,
  `_positive_setting()`, the wrapped empty-state note
- `tests/test_plan_screen.py`, `tests/test_time_block_colors.py`
- `docs/implementation_plan_2026-11-06_plan_box_appearance.md` (new),
  `docs/USER_GUIDE.md`, `docs/spec_coverage.md`, `CHANGELOG.md`,
  `docs/implementation_plan_2026-11-05_time_grid.md`

## Verification

- Command: the eight touched test files, run under the venv with mapped
  windows enabled (`GETMOREDONE_NO_MAPPED_WINDOWS` unset, so the geometry
  tests actually ran rather than skipping).
- Result: **PASS** — 280 passed.
- Command: the repo/infra assertions (`-m meta`).
- Result: **PASS** — 211 passed, 1 skipped. It caught one stale `Tests:`
  reference in `theme.py` naming a test that had been renamed.
- Mutation gate: 12 mutations, each the verbatim original reverted, each
  confirmed red, every file restored. Plus 2 more for the empty-note fix.
- On screen: `./start-demo.sh`, Plan, 2026-11-05 and 2026-11-06. All five
  asks confirmed visually. No errors in the launch log.

## Risks / Known gaps

- **Two mutations were green on the first pass, and both were defects in the
  tests, not the code.** (1) The chip had two independent guards — the
  stripe's `height=` and a `grid_propagate(False)` — so no test could fail on
  either alone. The redundant guard was removed rather than left unprovable.
  (2) `test_pbm41_fill_tints_carry_legible_text` was **vacuous**: with
  `pick_text_color` choosing black or white, at least one always clears 4.5:1
  at every luminance, so the assertion could not fail. It was replaced by a
  margin test and by a widget test on the rendered title colour.
- Two live `PlanScreen`s on one mapped root wedge Tk inside `root.update()`.
  Not a defect in the code under test, but it hangs a run; the two PB-M5
  wiring tests settle geometry with `update_idletasks()` instead.
- The demo's `drag_schedule_box_height_px` is 30, so the Plan boxes are
  compact there. The 86 default only applies to a fresh settings file.
- Item titles longer than the column are still clipped at the right edge.
  Anchored left, so the start is always readable; no ellipsis.

## Sweep (2026-11-06, after the first three commits)

Two passes over `99d438f...cfd6dc5`, both cold: a failure-pattern pass
(`learning-qa`) and a correctness pass (`/code-review`). Eight findings
between them, no high, three raised by both. `/security-review` was not run:
the range has no credential, auth, SQL, subprocess, HTTP or deserialisation
surface — the only grep hits were the word "request" in prose about
`CTkFrame` geometry.

Five mediums fixed with tests in `0d48c96` (src) and `cb8c476` (tests):

- The outside-the-day group's rows kept the 30/80 fallbacks while the day took
  the setting, in the column the group had just been moved into.
- That group also lost its scrollable container in the move, so a day with a
  dozen blocks outside it clipped the lower rows out of reach while the header
  counted them (P2). Scrollable at a fixed height, ungridded when empty.
- `_positive_setting` guaranteed "> 0", not usable: a box height of 14 made a
  two-task half hour the same height as a one-task one and clipped the second
  task. Floored at one line of text.
- The note's wraplength was unfloored and Tk reads `<= 0` as "do not wrap".
- Three docstrings and a settings comment named the wrong Settings section.

Plus three test-quality fixes: a colour test that passed only because this Mac
is in light mode, three tests holding `mapped_windows` without reading
geometry, and a duplicated WCAG luminance formula whose justification was
false. The documented mapped-window count (conftest: three, CLAUDE.md: ten;
actual: sixteen) is now asserted against the suite by AST.

Mutation gate on the fixes: 8 mutations, 8 red, every file restored. The
appearance pin was probed by forcing dark mode, where the test it protects
goes red as predicted.

Four below-medium findings went to `BACKLOG.md`, including two adjacent issues
flagged rather than fixed under rule 10.

## Adjacent issues found, not fixed

- `screens/drag_schedule.py:115` reads the same box-height setting with a bare
  `int(getattr(...))`, a different fallback (86) and a different floor (20).
  Hand-edit a `null` into settings.json and that screen does not open while
  the Plan screen falls back. One shared helper is the fix; widening this diff
  into another screen is not.
- The four Plan/Drag Schedule size controls render under "Date Increment
  Settings". The docs now say so; moving them needs approval.
- A press that lands exactly on a 14x3px depth bar does not start a drag
  (already in `BACKLOG.md`; still true, and the bars are now visible on the
  Day Plan too, so the target exists in one more place).
- `docs/spec_coverage.md`'s third human-review row ("does a drag feel right")
  is still outstanding and is now overtaken by PB-M5 — a chip is no longer
  30px by definition.

## Next agent actions

- Re-walk the drag feel on screen once a box height other than 30 is in use.

---

## PB-M6 / PB-M7 — a second round, after the first five were on screen

### Summary

Four more changes, asked for against the same demo once PB-M1 to PB-M5 were
visible.

- An item row in **Items starting** is now `slots_for_minutes(minutes)` boxes
  of `box_height()` tall — the same arithmetic and unit the day's grid uses, so
  a 90-minute item is three boxes and a 45-minute item is two. Held by
  `grid_propagate(False)`, which is what makes it the grid's height rather than
  its text's.
- The priority score came off the row. It was the third statement of one fact,
  after the fill and the stripe.
- The work-block length (`30m`) moved from the detail line to under the depth
  bars, which puts it where it already is on a task in a box.
- A continuation chip now carries the task's fill and stripe instead of being
  transparent, and keeps its `↳`. Transparent was the earlier decision, on the
  argument that shading a continuation would read as a second task; on screen a
  90-minute task read as one that stops after half an hour. Buffers and breaks
  stay transparent. The `same task` / `15m spare` line takes the text colour
  the new fill calls for.

### Files changed

- `src/getmoredone/screens/plan_blocks.py` — `build_item_row` height, span and
  detail line; the duration label; `_build_block_chip`'s merged fill branch and
  unconditional stripe; `SLOT_CHIP_HEIGHT_PX` moved above `build_item_row`
  because it is now a default argument and defaults bind at definition time.
- `src/getmoredone/screens/plan.py` — `build_item_row` called with
  `box_height=self.box_height()`.
- `tests/test_plan_screen.py` — six new tests, one rewritten.
- `docs/implementation_plan_2026-11-06_plan_box_appearance.md`,
  `docs/spec_coverage.md`, `docs/USER_GUIDE.md`, `CHANGELOG.md`.

### Verification

- Command: `pytest tests/test_plan_screen.py tests/test_time_block_colors.py tests/test_plan_settings.py -q`
- Result: PASS — 160 passed, mapped windows enabled.
- Mutation gate: 9 mutations over the four changes, 9 red, every file restored
  from a verbatim copy. The first run skipped one because
  `    frame.grid_propagate(False)` matches twice in the module; anchored to its
  preceding line and re-run.

### Risks / Known gaps

- One rewritten test, under test rule (b): the behaviour changed intentionally.
  `test_an_item_row_is_as_tall_as_its_text_not_the_stripe_default` asserted the
  opposite of PB-M6.1 and is now
  `test_an_item_row_lays_out_at_the_height_it_asks_for`. PB-M2.2 is marked
  superseded in both the plan and `docs/spec_coverage.md` rather than left
  claiming a property this change removes.
- Two test names the plan doc had named were wrong (`PB-M4.1`'s, and PB-M2.2's
  after the rewrite). Found by checking every `::test_` reference in both docs
  against the suite, not by review. Both corrected.
- **Not yet seen on screen.** Every height and colour claim here is measured —
  by `cget`, by `winfo_y`/`winfo_height` on a mapped window, and in one case
  against the rendered day itself — but nobody has looked at the Plan screen
  since these changes. The demo was running the pre-change code throughout; it
  needs restarting.

### Sweep over this range — `2e4add9...HEAD`

Both cold passes run and their findings fixed. `learning-qa`: 5 medium, 0 high,
4 below. `/code-review`: 2 medium, 3 below. Four findings converged. Five
patterns of the catalogue genuinely applied to a pure-UI diff and it said so
rather than stretching the rest. `/security-review` not applicable, by grep of
this range's added lines.

What they found, all three of the mediums in code written and reviewed warm in
the same session:

1. **The height was 2px per box short of the day it claimed to match.** A day
   box is `box_height + 4` and consecutive boxes are 2px apart, so a 3-box row
   was 258px of row for 274px of day. The acceptance test asserted the same
   product the code computed. Fixed by `item_row_height`, built on
   `slot_row_height`; the test now asserts literals, and a second test measures
   the rendered day the item itself produces.
2. **The title collapsed to one pixel at a box height of 30, and floated
   mid-row at the default.** `grid_rowconfigure(0, weight=1)` put the whole
   shortfall on the title's row, so a one-box row showed its depth and its
   length and not which item it was; a 3-box row centred the title 100px from
   its own detail line. The weight is on an empty row 2 now, and
   `ITEM_ROW_MIN_HEIGHT_PX = 66` keeps the row above its own two lines. Two new
   geometry tests measure every child against the frame.
3. **Four colour assertions and one score assertion compared the unscored
   tint with itself** — three found by the first two passes, a fourth by the
   re-sweep of the fixes, and `test_pbm62`'s dead `"51200" in text` alongside
   them.** `_item(..., priority_score=51200)` does not make a scored item —
   `create_action_item` recomputes from four `None` factors and gets 0 — and
   `_one_slot_pane` rendered with an empty `items_by_id`, so the chip's item was
   `None`. Fixed with `_scored_item`, which asserts its own band, and
   `items_by_id` threaded through the helper. Three of them were tests from the
   earlier batch — PB-M1.4's, PB-M4.1's and PB-M4.3's: adjacent, fixed rather
   than left, and said so in `docs/spec_coverage.md`, because leaving them means
   that document claims those three criteria are verified when they were not.
   One more call site of the same family, `test_pbm31`'s, passed no
   `items_by_id` at all, so its `depth="Deep"` reached nothing.

The mutation gate on PB-M6/PB-M7 came back 9/9 red and could not have caught
finding 3 — mutating the lines the diff touched does not produce the mutant that
fills every chip with the unscored tint. A green gate there was expected, not
reassuring. The gate on these fixes is 7/7 red, after two green mutants sent two
of the new tests back: one built its expected height from the same constants the
code reads (the same self-agreement, in the test written to fix it), and one
pinned a `sticky` change that turned out to change nothing, which was reverted
rather than kept with a false justification.

Three below-medium findings are in `BACKLOG.md`.

### Re-sweep of the fix commits — `b6b1daa...HEAD`

Cold, one lens (correctness and test quality, where the first two passes' useful
findings came from). **No correctness defect in `src/`**: `item_row_height`
matches what the day draws, `SLOT_ROW_GAP_PX` is the real gap, the empty
weighted row 2 adds no dead zone to the drag binding, and the on-screen
comparison test was checked to compare like with like.

One medium — the fourth unscored-item assertion above, left standing by the
commit that removed the other three — and five low, of which four are fixed here
because each is one line or a sentence and leaving them means a document or a
docstring states something false:

- The floor was 66 and the row's own grid requests 67: row 1's larger bottom pad
  is the `{minutes}m` label's 6px, not the subtitle's 5. The row lost the last
  pixel of its bottom padding, which no assertion could see because both labels
  anchor to the top of their cell. It was the one number in this change
  justified purely by arithmetic, so it now has a test that measures it:
  `test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for` sums what each of
  the row's text rows requests off the real widgets and compares that with the
  constant. Red at 66.
- "exact at every box height the day itself can show a line of text at" was
  false for box heights 31–62, a reachable range: a 44px box renders a 28px
  label perfectly well and the row is still 67. The claim is now "from 63 up",
  which is what the code does. The user guide was the one document that had it
  right.
- "Exactly the space the item's work block will take in the day" holds only for
  an empty day — a half hour already holding a task is taller than one box. Said
  so in all three documents.
- `test_pbm61_every_line_of_a_row_is_drawn_inside_it`'s docstring implied it
  guards the row-2 weight on its own. It fails on the combination; with the
  floor in place the weight alone keeps it green. The docstring now points at
  the test that does pin the weight.

The sixth, `_scored_item`'s unused `"medium"` factor row, is deleted rather than
left as a branch no caller reaches.

### Walked on screen — one medium, which is what the walk is for

The demo was relaunched on the committed code and the Plan screen looked at.
PB-M6.2, PB-M6.3 and PB-M7 are right on screen; PB-M6.1 is right but invisible
at the demo's own box height of 30, where a one-box row is 67px and a two-box
row 70. At 86 the 60-minute item is exactly twice the height of each 30-minute
one, with its text at the top and the slack at the bottom.

Setting it to 86 is how the medium turned up: **the saved value did nothing
until the next launch.** `SettingsScreen.__init__` does its own
`AppSettings.load()`, so the object it edits is not the one the app holds, and
the Plan screen reads `app.settings` when it is built. The appearance section
hands its object over after a successful write; `save_date_increment_settings`
— which carries both settings PB-M5 wired to the Plan screen — never did.
Before PB-M5 the Plan screen used a constant, so this is new surface from this
batch, not something it inherited.

Fixed after the write and not before, the same ordering and the same reason as
the appearance section: a refused save leaves the file saying something else.
Two tests, both red under mutation, and the round trip walked in the demo:
30 → 86, Save, Settings → Plan, the boxes and the rows change with no restart.

No review pass could have found it. Every test in the suite builds a screen
from a settings object it was handed, which is precisely the step the Save
button was missing — the P25 shape again: a path reachable from only one
surface, and not the one anyone uses.

**Adjacent issues found, not fixed.** Verifying this batch's own `::test_`
references against `tests/` turned up stale names across the older
documentation — `docs/VPS_DATA_INTEGRITY_AUDIT.md` and nine earlier handoff
notes. Two inside `docs/spec_coverage.md` were repointed here, because that file
is the coverage claim itself and a row naming a test that does not exist is a
claim that cannot be checked: `test_spec_coverage_doc_mentions_m1_through_m5`
(renamed to `_m7` in `cf4189d`) and RP-4.2's second test. The rest are in
`BACKLOG.md` with the meta test that would stop it recurring.

### Next agent actions

- Restart the demo and look at the Plan screen: the item-row heights beside the
  day, the continuation colours, and a row at box height 30 against one at 86.
- Re-walk the drag feel, still outstanding from PB-M5.
