## Where `main` stands (2026-11-08, end of day)

One batch at a time from here, per `CLAUDE.md`. What that leaves:

- **The nine open `SSC` filings are closed** (SST batch, 2026-11-08). Every
  status claim this repo made about itself that nothing checked: seventeen stale
  lines over built work, the WTP count (38/40/41 — it is 41), a coverage row
  naming a method that never existed, twelve line-number cites, and
  `PRI-A1`–`PRI-A4`, promised by two documents and filed in neither. Three
  guards now hold the class in `tests/test_doc_status_claims.py`. A cold pass
  on 2026-11-09 found eleven medium-or-higher defects in that work, all
  confirmed by re-measurement and all fixed: four of them were guards or
  figures in the batch's own tooling that could not fail on the thing they
  named, which is the batch's own subject. A second cold pass, in a different
  failure family, then found one high and five mediums — among them a criterion
  recorded `done` against the docs-sync gate, which runs only on
  `pull_request` and so has never run here (`SST-A8`). All six fixed.
  `SST-A1` to `SST-A8` are filed, not fixed. See
  `docs/changes/2026-11-08-status-claims.md`.

- **Both leftover branches are settled.**
  `refs/heads/claude/elegant-neumann-ab55c9` (UPD-F1) is **merged** at
  `2fac9b3`. `refs/heads/claude/plan-day-range-pdm13` is **superseded and
  stays unmerged** at `c8125af`: it holds the earlier design of the plan day,
  the one whose shared-setting write caused both reported faults. It must not
  be merged. Whether to delete it is undecided.
- **Eleven of the twenty red tests are closed.** Ten by the PDT batch — the
  nine plan-day failures and `test_every_referenced_test_name_exists` — which
  were stale test vehicles, not missing code: `outside` was implemented on
  `main` at both layers the whole time
  (`docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md`). The eleventh,
  `test_every_referenced_test_file_exists`, by the PRIT batch, which wrote the
  35 tests PRI-M1 and PRI-M2 had shipped without
  (`docs/changes/2026-11-08-pri-tests.md`). That also closes PDT-M4.2, the one
  criterion the PDT batch recorded `not done`. **Confirmed by CI run
  `42574256150` on `5eef83d`: 9 failed, 2635 passed, 2 skipped, the same on
  3.11, 3.12 and 3.13** — twenty down to nine, with no new failure. The
  measurement and the intermediate run are in `BACKLOG.md` item 1.
- **Nine failures are left, in two groups,** not three:
  - **Seven** always-on-top tests (`test_t51`, `test_t52`, `test_t56`,
    `test_t57`, `test_wt_m6b6`, `test_alpha_still_passes_through_the_attributes_wrapper`,
    `test_raw_tkinter_windows_are_hidden_and_registered_too`) pass locally and
    need one shared precondition — `BACKLOG.md` WTP-A11.
  - **Two that are not that family.** WTP-A11's own text excludes
    `test_pbm61`; the second exclusion is `BACKLOG.md` item 5's:
    `test_pbm61_a_tall_row_keeps_its_two_lines_together` is **skipped**
    locally, not passing, because `GETMOREDONE_NO_MAPPED_WINDOWS=1` skips it,
    so it cannot be reproduced on a working machine at all; and
    `test_updm14_zero_width_body_is_a_noop` builds no window and its cause is
    still unidentified.
- **The coverage gap is closed, and PRI-M3 is open in its place.** PRI-M1/M2
  had shipped with `models.py` naming two test files and three tests that had
  never existed, so the cap, the floor and the "(capped)" label were
  unverified. Both files now exist, 35 tests, mutation-proved, and the meta
  test is green — closed by writing the tests, not by editing the docstrings.
  `BACKLOG.md` item 2. What the same measurement turned up: **PRI-M3, the
  four-digit column, was never built at all**, so nothing yet proves `"P:9999"`
  fits the score column at the larger selectable row font sizes, and five list
  screens still carry their own width literals. Filed as `PRIT-N1`, medium, not
  built — it is a feature change against the aligned-column contract, not a
  test gap.

The claim that the plan-day branch "closes eight of the twenty red tests", and
the claim before it that nothing needed writing to close them, were both wrong
and are corrected in `BACKLOG.md` item 1 with the measurements.

## Recent Changes (2026-11-08)

### What the walk asked for - UPD-F1 to UPD-F4 all built and on `main`

The §11 walk happened. All four of its items are built and on `main`: the
three layout items here, and UPD-F1, the only defect among them, merged at
`2fac9b3`.

- ✅ **UPD-F2** - the three lineage filters moved off the controls row onto a
  row of their own on all five tabs, in a frame of their own at header row 2,
  with the status line below them at row 3. Annual Plan Elements has no
  filters at all, so its title now has row 0 to itself, its controls sit on
  row 1, and row 2 is an empty frame one combo high - the blank line asked
  for by name. 7 of 7 mutations red.
- ✅ **UPD-F3** - `APE_LEFT_COLUMNS`' checkbox column is headed "Pick" again,
  which reverses the text half of UPD-M5.5. The plan expected the 34px column
  to widen; measured in the bold header font, "Pick" is 28px, so nothing
  moved. Four panels share that column set, not the three the plan said. 6 of
  6 mutations red.
- ✅ **UPD-F4** - `ColumnResizer.fit_to_width` shares a panel across its
  resizable columns by weight, floor five characters (40px at `CHAR_PX = 8`),
  fixed columns reserved out, and returns the shortfall when a panel cannot
  seat the floors rather than clipping in silence. `SplitPanel.apply` gained
  an `on_apply` callback and the five screens pass `panel_fitter(...)`. Every
  resizable chip column's minimum dropped to the floor, from 60, 52 and 80.
  9 of 9 mutations red - one survived the first gate and the assertion was
  tightened to an exact panel fill.
- ✅ **UPD-F1 is on `main`.** It was built, after this was written, on
  `refs/heads/claude/elegant-neumann-ab55c9` (`31816a0`, "save() writes what
  this object changed, not every field", plus its tests and note), and that
  branch is **merged**, at `2fac9b3`. `31816a0` is an ancestor of `main` and
  the `UPD-F1` docstrings are at `src/getmoredone/app_settings.py:237`, `:253`
  and `:417`, among six such references in that file. This bullet said the
  branch was unmerged and the defect still
  live; both were true when written and neither is now. The defect described
  below is **fixed**, not live.
  `AppSettings.save()` writes the whole object, so
  a screen holding an older snapshot reverts fields another object changed -
  which is why no width survived a relaunch. The fix changed
  `src/getmoredone/app_settings.py`; when this was written that file was held
  uncommitted by the calendar-export batch, so `CLAUDE.md`'s "One build batch
  at a time" ruled it out here and it was proposed as its own worktree
  session. That session ran, and its branch is merged. **Nothing to do.**
- ⚠️ **None of the three has been seen running.** UPD-F2.6, UPD-F3.5 and
  UPD-F4.7 are `not done` and are steps 11, 11 and 13 of the spec's §11
  (F2.6 and F3.5 share step 11; step 12 carries no UPD-F criterion).
  Steps 4 and 7 were rewritten, so those two are owed again as well: what was
  walked on 2026-11-08 is not what is there now.
- ⚠️ **A column at the five-character floor clips its own heading.**
  "SubSegment" measures 84px against a 40px minimum. True at the old 60px
  minimum too, and the narrower floor is what was asked for, so it is
  recorded as UPD-A10 rather than fixed.
- ⚠️ **APE Week Actions' right panel is not fitted** (UPD-A11). It is a
  `TodayScreen` subclass with its own column store, not a `ChipTable`, so its
  columns keep their pixel widths when the divider moves.

### The one panel design is built, and has not been looked at - UPD-M7

- ✅ **UPD-M7.1** - `tests/test_unified_panel_design.py` builds all five
  rewritten tabs and asserts no `Toplevel` is opened anywhere beneath the
  root, and reads its own syntax tree to assert that exactly zero of its 98
  tests take the `mapped_windows` fixture. The 22 mapped-window tests
  `CLAUDE.md` documents are the 22 that were there before this plan.
- ❌ **UPD-M7.2 and UPD-M7.3 are open and need you, not a test.** Whether the
  six tabs read as one design at a real window size with real data, and
  whether a dragged column width survives a relaunch, are the two things the
  tests cannot reach: every one of them builds its screen on a withdrawn root,
  which is what keeps a test run off the screen. The ten steps are §11 of
  `docs/spec_2026-11-07_unified_panel_design.md`.
- ⚠️ **Nothing in UPD-M1 through UPD-M6 has been seen running.** UPD-M4 changed
  the renderer, the splitter and the row drag of three tabs in one step.

### Plan day → Google Calendar export - CE-M1..M4

- ✅ **`src/getmoredone/calendar_exporter.py`** (new, GUI-free): decides what
  the day's blocks should become (`build_export_plan`, pure), then sends it
  (`export_day`). Opens its own `DatabaseManager` from a path, the way
  `calendar_importer` does, because it runs on a worker thread.
- ✅ **`time_blocks.calendar_event_id`** (TEXT) on fresh databases and by
  idempotent migration. `create_time_block` and the new
  `set_block_calendar_event_id` are the only writers; `update_time_block`
  deliberately does **not** carry the column, because a screen edit uses a
  block object loaded before the export and writing its `None` back would
  orphan a live event.
- ✅ **The orphan sweep is the only deleting code** and it keeps anything it
  cannot account for: events with no daVIPA marker, and events whose marker
  names a block this run did not confirm (failed or skipped). A failed
  `list_day_events` is counted as a failure, never read as "nothing to remove".
- ✅ **`google_calendar.py` hardened as a class (P5)**: `_with_retry` around
  all four event calls, 30s transport timeout, 429/5xx retried with backoff,
  404/410 raised as `CalendarEventMissing` so a hand-deleted event is
  re-created rather than reported as broken.
- ✅ **The button disables before anything fallible runs** and every refusal
  re-enables it. The worker touches no widget — Tk is not thread-safe and that
  includes `after()`; it leaves its result in an attribute and the Tk thread
  collects it (`_poll_export`, 100ms).
- ⚠️ **Mutation testing found two tests that could not fail** and both were
  real: `update_time_block` writing the column (removed, as above), and a
  `failed_block_ids` guard in the sweep that was dead code (removed).
- ⚠️ **A leaked monkeypatch of `GoogleCalendarManager.__new__`** in the new UI
  test broke four tests in other files: `monkeypatch` undoes a patch of an
  *inherited* dunder by writing `object.__new__` into the class dict, after
  which every real `GoogleCalendarManager(...)` raises `TypeError`. The test
  patches `__init__` only now and asserts the invariant where it broke it.

- ✅ **A cold review pass** (`learning-qa`, read-only) returned 11 findings:
  1 high, 3 medium, 7 low. The four at medium or above are fixed here — the
  empty-day refusal that made the orphan sweep unreachable, a `summary_line`
  that discarded a run's deletions and failures, a retry that saw `HttpError`
  only, and two Tk callbacks with no widget-liveness guard (P15). The seven low
  findings are CE-A5 to CE-A11 in `BACKLOG.md`.
- ✅ **A second cold pass**, in a different failure family (UI contract and
  test quality), returned 7: 1 high, 4 medium, 2 low. The high was that the
  Plan header asked for 1203px inside a 1200px window, so the status label —
  packed last, fixed widths everywhere else — got zero width and was never
  mapped: the export's only output channel, invisible at the default window
  size. The status line now has its own row and the button is 150px. The
  mediums were `has_credentials()` not meaning "connected" (the real client
  authenticates in `__init__`, on the worker thread, blocking on a browser),
  the thread start sitting outside the `try`, and two title tests that could
  not fail. CE-A12 to CE-A15 hold the rest.
- ✅ **A third cold pass**, in a third failure family (state, concurrency and
  document accuracy), returned 10 and found the batch's worst defect: the
  export read every block's time from its stored clock columns, which the
  screen's own docstring calls "a record, not the truth". A block's box is
  stored relative to Day Start, so moving Day Start re-times the day on screen
  and leaves those columns behind — a day drawn from 10:00 was going onto other
  people's calendars from 08:00. Times are now derived from the box with
  `times_for_slot`, and "on the grid" is `build_day_grid(...).outside`, so the
  blocks the day draws under *Outside the day* are the blocks the export skips.
  Four more at medium or above are fixed with it: a non-interactive client
  (below), one export per day keyed outside the screen instance, the calendar
  an event id belongs to recorded in its own column, and
  `set_block_calendar_event_id` reporting whether it wrote a row. CE-A16 holds
  the one minor finding.
- ✅ **A fourth cold pass**, on time correctness and the Google API contract,
  returned ten: four medium, six low, nothing high — so the budget is closed.
  The mediums: nothing asserted the `dateTime`/`timeZone` strings that actually
  leave the machine (dropping the zone or reading minutes as hours left the
  batch green); the retried `events().insert` could make a second event, which
  the export's sweep hid and the meeting dialog did not; a 403 carrying a
  rate-limit reason was reported as a hard failure for every block in a burst;
  every exported block carried the meeting dialog's ten-minute popup and
  overrode the user's own calendar setting; and the sweep deleted on the
  strength of Google's date filter without re-checking the marker's date.
  CE-A17 to CE-A21 hold the six lows, including the wall-clock/DST decision,
  written down rather than changed.
- ✅ **The set has been re-run** now that the other session's PD-M14 edit to
  `screens/plan.py` has landed: 9 failed, 537 passed, 17 skipped. All 150 of
  this batch's own tests pass. The nine red ones are PD-M14's — the
  outside-group tests in `test_plan_screen.py` and the two
  `test_pdm54_*` tests in `test_plan_settings.py` — in that session's
  in-progress area, in files this batch does not touch. Left to them.
- ⚠️ **The export's client cannot sign in.** `has_credentials()` and a token
  file *existing* are not the same as a token that works: revoked access, a
  changed password or a damaged pickle all reached `flow.run_local_server` and
  then `input()` — both waiting forever — on the worker thread, leaving the
  button disabled under "Exporting…" until the app was killed. Four documents
  said this could not happen. `GoogleCalendarManager(allow_interactive=False)`
  now raises `AuthenticationRequired` instead, and the worker reports it as
  "sign in again". The calendar dialog, which has a main thread and a console,
  still signs in normally.
- ⚠️ **Watch the Plan header's width.** It is now 8px inside the default
  window (1172 of 1180). `test_cem441b` fails if a widget is added or widened
  past that, which is the point: the last widget packed is the one that
  silently disappears.
- ⚠️ **Tk finalizers are not thread-safe either.** The export worker was
  intermittently wedging in `tkinter/font.py::__del__`: a garbage-collected Tk
  font object, collected on the worker thread, calling into Tcl from off the Tk
  thread, reached through `DatabaseManager.__init__`'s migrations. The screen
  now runs `gc.collect()` on the Tk thread before starting the worker.

### APE Week Actions joins the one panel design - UPD-M6

- ✅ **A draggable divider**, from `screens/split_panel.py`, where the body was
  a fixed 380px minimum on the left and `weight=1` on the right. The ratio
  lands in `AppSettings.week_actions_split_ratio` and is there on the next
  launch.
- ✅ **The tactic list is the shared chip table**: `#` / Weekly Tactic /
  Segment / SubSegment / Category at 34 / 220 / 135 / 155 / 125, every column
  draggable, under its own `week_actions_left` store. It was one `CTkButton`
  per tactic with the title and the segment name stacked inside it. Clicking
  any cell in a row still selects that tactic — every cell is bound, not just
  the row frame.
- ✅ **Segment / SubSegment / Category filters**, which this tab was the only
  one in the hub without. An empty result names the filter and says how many
  it hid, and an empty week says that instead (P2). A selection the new week
  cannot match falls back to All rather than leaving the panel empty for a
  reason nothing on screen gives.
- ✅ **The Actions panel on the right is untouched** and keeps the
  `week_actions` prefix, so widths a user has already set there are still read
  with the same keys (D3). There is no drop target and no drag source on this
  tab (D6) — asserted from the AST at exact count 0, with both pins written
  and run green *before* the rewrite.
- ✅ **Three rules now have one owner each** rather than a sixth copy:
  `screens/lineage_filters.py` (new) for the filter triple and the two lineage
  row readers, `segment_color_utils.load_category_color_map` /
  `resolve_chip_colors` for the category chip colour, and
  `chip_table.show_list_or_message` for the list-or-message rule. `weekly_items.py`
  moved onto all three in the same change. The five copies left under
  `screens/` are UPD-A9 in `BACKLOG.md`, not swept in here.
- ✅ **One defect in the shared table, fixed.** `add_row` clipped a chip to its
  column but gave a plain cell its raw text, so a Title column opened with one
  row pushing the others out of line and corrected itself the moment the
  handle was touched. A resizable plain column is clamped at the first render
  now; a fixed-width one keeps its raw text deliberately.
- ⚠️ **Not seen running.** Every test builds the screen on a withdrawn root.
  UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are still open.
- Gate: 20 mutations, each the verbatim original, each run alone, every file
  restored and sha256-compared — 20 red, no finding. 112 tests across
  `test_unified_panel_design.py` and `test_ape_week_actions.py`.

### Priority level colours are settable - PLC-M1 to PLC-M5

- ✅ **Three priority levels, named and decided in one place.** Any Critical;
  Any High, but no Critical; No high or critical. A level is a rule on an
  item's own Importance and Urgency, read off `PriorityFactors` rather than off
  a literal 20 or 10. New module `src/getmoredone/priority_levels.py`.
- ✅ **The "high" tier is new.** Before this, a High item looked exactly like a
  Low one: the five list screens only ever looked for Critical.
- ✅ **Any Critical defaults to green** (`#DCFCE7`), Any High to amber
  (`#FEF3C7`), the third level to no fill. Asked for directly, and confirmed
  before the plan was written. The pale red `critical_tint` is no longer used
  for a row fill.
- ✅ **Settings → Priority Colours**, a new tab: a `#RRGGBB` field, a Pick
  Colour button and a swatch per level, plus Apply / Save and Restore Defaults.
  A value that is not a colour is refused with the level's name and nothing is
  written — it is not silently rewritten to a default, the way
  `save_date_increment_settings` does. Clearing a field means no fill, and that
  survives a reload.
- ✅ **Five copies of the rule became one.** `importance == 20 or urgency == 20`
  was written out by hand in `today.py`, `upcoming.py`, `all_items.py`,
  `hierarchical.py` and `completed.py`, each with its own precedence chain;
  `priority_levels.row_fill` is now the single decision. Precedence is
  unchanged, including the branches three of those screens never used.
- ✅ **One colour per level, both modes, with the text colour derived.** A
  colour the user picks cannot have a light and a dark variant, so a level fill
  brings `pick_text_color` of itself instead of keeping the theme's `row_text`.
  Held to 4.5:1 across the range, not only at the two defaults.
- ✅ **A saved colour shows without a relaunch.** All five screens now reload
  `AppSettings` in `refresh()`; two of them had no `self.settings` at all.
- ✅ **New coverage, not a restatement.** The row tint had no test of any kind
  before this batch — `grep critical_tint tests/` returned nothing. 41 tests,
  none of them building a window; PLC-M4.1, M4.4 and M4.7 mutation-proved.
- ⚠️ **Not checked on screen.** Whether the green *reads* right is the one
  thing no test covers; the checklist is in
  `docs/changes/2026-11-08-priority-level-colours.md`.
- ⚠️ **The red `P:` chip is unchanged**, by the user's choice, so a green
  critical row sits beside a red chip. Logged as PLC-A3.

### Two cold review passes over PLC, and what they found

- ⚠️ **The validator written to keep a bad colour out of Tk admitted six
  shapes Tk rejects.** `normalize_hex_color` checked `len == 7` and
  `int(text[1:], 16)`, and Python's `int` takes a sign, a `0x` prefix,
  PEP-515 underscores, inner whitespace and non-ASCII digits: `0x1234` came
  back as `#0X1234`. Saved from the new field it reached `settings.json`, and
  from then on every row build in five screens *and* the Settings tab's own
  swatch raised `TclError` — so the tab the user would fix it from could not
  open. Now `#[0-9A-F]{6}`, in `_normalize_hex` too. **Five more of these
  validators remain** elsewhere in the app, one of them reachable to the same
  end through a VSP segment colour; they are PLC-A10, not fixed here.
  That Tk really does raise `TclError` on all six shapes is now asserted
  against a real Tk, in `tests/build_priority_colors_section.py`, rather than
  taken from its colour grammar.
- ⚠️ **The one test that built the section for real skipped on its own target
  class.** Any `TclError` became `pytest.skip`, and `TclError` is what a bad
  `grid` call or a colour Tk refuses raises. Four display-specific stderr
  fragments skip now; everything else fails.
- ✅ **Dark-mode row controls follow the fill.** The level table has no dark
  variant by design, so in dark mode a Critical row is light while the theme's
  checkbox border and drag grip stay light — about 2.6:1, under the 3:1
  non-text bar. `row_control_kwargs` gives the three screens that build row
  controls the fill's own text colour, and nothing at all for a segment,
  completed or unfilled row.
- ✅ **A refused write no longer leaves colours on the shared settings
  object**, where the next successful save from any other Settings section
  would have persisted what the user was told was not saved.
- ✅ **A sixth surface draws the fill, and the docs named five.** APE Week
  Assignment's Action Items panel is a `TodayScreen` subclass that overrides
  neither the row builder nor `refresh`, so it inherits the tint and the
  reload. The user guide and the in-app help now say so, and a test asserts the
  inheritance, since that is the only reason the panel is covered.
  (A first attempt at this put a reload into `WeekActionsScreen.refresh` — the
  *container*, which builds no rows of its own and already sets `self.settings`
  in `__init__`, so the line was redundant rather than useful — and a test that
  passed only because `WeekTacticActionsPanel.refresh` *is*
  `TodayScreen.refresh`. Both were reverted.)
- ✅ **The reload guard now asserts the result is assigned to
  `self.settings`** — both `today.py` and `upcoming.py` already load into a
  *local* elsewhere, which the old call-only check accepted — and that it
  happens in the first three statements of `refresh`.
- ⚠️ **A source guard was passing on a comment.** PLC-M3.6 ended in
  `"Priority Colours" in inspect.getsource(create_tabs)`, satisfied by the
  comment above the `add` call, while its own docstring claimed it was parsed
  rather than greped. It is now an AST check over the strings
  `self.tabview.add` is given, pinning all seven tabs in order.
- ⚠️ **One test could not fail:** `test_plcm32` asserted the cleared level
  equalled `""` against a fresh `AppSettings`, whose default for that field is
  already `""`. It now starts from a stored colour, so clearing is a real
  write.
- 📋 **Seven below-medium findings** went to `BACKLOG.md` as PLC-A6 to PLC-A12
  rather than being fixed in-loop.

## Recent Changes (2026-11-07)

### APE Week Assignment joins the one panel design - UPD-M5

- ✅ **The last two panels now draw with the shared chip table, splitter and row
  drag.** `weekly_items.py` lost nine splitter-and-drag methods, `_clear_scroll`
  and `_clip_label`, and gained the right panel's Actions column with a Delete
  on every row. Both panels' columns are draggable and persisted, and the
  divider is remembered, for the first time on this tab.
- ✅ **UPD-M1.5 and UPD-M2.5 are `done`.** Both holdout sets are empty, and the
  guards now assert emptiness rather than a shrinking list. `project_boards.py`
  still has a splitter and is named in `SPLITTER_OUT_OF_SCOPE` by UPD-A5; it
  never had a row drag, so the drag guard has no out-of-scope file at all.
- ⚠️ **A defect in the screen as it stood, found while writing M5.7's test.**
  `on_select_weekly_item` re-rendered the right panel without destroying what
  was there, so every selection click gridded a fresh header and a fresh set of
  rows into the same cells as the old ones - three clicks on a two-row week took
  the panel from 3 children to 12. Only `_render_lists` ever cleared. Adopting
  the shared table is the fix, because `build_header` clears its container. The
  test was proved red against the old screen first.
- ⚠️ **The spec contradicted itself about `Delete Weekly` and the contradiction
  is recorded, not quietly resolved.** §2's D5 lists only the two other buttons
  as staying; §5's risk list says `Delete Weekly` stays beside the row Deletes.
  Kept, because §5 is explicit where D5 is an implication and removing a working
  button is what a later step cannot undo. The row's Delete and the selection's
  Delete are one method with two callers, so the confirmation exists once.
- ⚠️ **The three name columns got narrower on this tab** - 180px each to
  135/155/125 - because that is what the other tabs use and §1.4 named the
  difference as a difference. Every column is draggable now, so a name that no
  longer fits can be widened; before, nothing could be.
- ⚠️ **Nothing in UPD-M1 to UPD-M5 has been seen running.** UPD-M7.2 and
  UPD-M7.3 are the on-screen criteria and are open.

### One panel design across the VSP tabs - UPD-M4, the three tabs adopt

- ✅ **APE Quarter Assignment, APE Month Assignment and Annual Vision Segments
  all draw their two panels with the shared chip table, the shared splitter and
  the shared row drag.** Six panels, one renderer. `annual_vision_segments.py`
  is 106 lines shorter, `ape_period_view.py` 82 and `ape_assignment.py` 51;
  nine splitter-and-drag methods and a private `_clip_label` went from each of
  the two screens that still had them.
- ✅ **Every column on all six panels can now be dragged wider or narrower, and
  each panel remembers its own widths.** None of the three tabs had resizable
  columns before. Eight new `AppSettings` fields hold them - six width maps and
  two divider ratios - because an undeclared field is dropped silently at the
  next launch, and `::test_updm44_every_panel_prefix_has_a_settings_field`
  holds that every panel a screen builds has one.
- ⚠️ **Two defects in the chip table's own config, both found by the first
  screen that adopted it.** `ChipColumn.min_width` defaulted to 40 while the
  checkbox and `#` columns declared 34, so both rendered at 40 and nothing said
  so; and the single `APE_COLUMNS` set held both a checkbox and an Actions
  column, which no panel does, putting every column of every panel one place to
  the right. The characterisation test written before the screen was touched
  caught the first on its first run - which is why that test was written first.
- ⚠️ **"Their existing test files pass unchanged" is false and recorded as
  such.** `test_apcm23_drag_path_reaches_the_same_reporting` drove a method the
  screen no longer has; it drives `_assign_dragged_row` now, the same change
  its APE Quarter sibling took at UPD-M2.
- ⚠️ **UPD-M1.5 and UPD-M2.5 are still `partial`.** Earlier notes said UPD-M4
  would close them. It does not: the fourth copy of the splitter and the drag
  is in `weekly_items.py`, which is rewritten at UPD-M5.
- ⚠️ **Not seen running.** Three tabs changed renderer, splitter and drag in
  one step and every test builds its screen on a withdrawn root.

### One panel design across the VSP tabs - UPD-M2, the row drag

- ✅ **Dragging a row from the left panel to the right has one owner:
  `src/getmoredone/screens/row_drag.py`.** `_bind_drag_widgets`,
  `_start_row_drag` and `_is_descendant` were byte-identical in the same four
  screens; `_finish_row_drag` differed only in the body of its final `if`,
  which is what a dropped row *means* and stays on the screen. APE Quarter
  Assignment has adopted it; two more adopted at UPD-M4 and
  `weekly_items.py` follows at UPD-M5.
- ⚠️ **The spec said the drag bound "press/motion/release on the row". It
  binds the press on the row and the release on the toplevel, and there is no
  motion handler anywhere** - nothing is drawn while a row is dragged, on any
  of the four. UPD-M2.1's wording inherited that and both are corrected.
- ✅ **A refused drop still redraws the list - now asserted.** The mutation
  gate found that removing `refresh_lists()` from the quarter screen's drop
  left every assertion green. The weekly screen's test says that behaviour out
  loud; its sibling here had nothing holding it (P5). The gap predates this
  step.
- ⚠️ **One docstring claim withdrawn.** A test said the drag lambda's `r=row`
  default argument guards against the late-binding trap. It does not - the
  loop is over the widgets and `row` is the call's own parameter - and
  removing the default left the test green. Said plainly in the test and in
  the module; the default is kept for intent, not effect.

### One panel design across the VSP tabs - UPD-M1, the splitter

- ✅ **The vertical divider has one owner:
  `src/getmoredone/screens/split_panel.py`.** The same 30 lines were written
  out in `annual_vision_segments.py`, `ape_assignment.py`,
  `ape_period_view.py` and `weekly_items.py` - `diff` of all four is
  byte-identical, measured before anything was removed. APE Quarter
  Assignment has adopted it; two more adopted at UPD-M4, `weekly_items.py`
  follows at UPD-M5, and
  `test_updm15_no_screen_keeps_its_own_splitter` names them so the list cannot
  go stale.
- ✅ **A divider stays where you left it.** It never did: every tab opened at
  the middle every launch, however the divider had been dragged. Stored per
  screen as `<prefix>_split_ratio`, the same way column widths are
  (`ape_quarter_split_ratio` is the first). `split_panel.py` logs a warning if
  a screen is given a prefix with no `AppSettings` field, because that would
  otherwise look like working drag and a forgetful relaunch.
- ⚠️ **The spec said the splitter was written out four times. It is five.**
  `project_boards.py` holds a fifth copy with its own minimum (300), its own
  default (0.6) and - as it turns out - a *better* clamp than the four: it
  holds both panels at the minimum where they held only the left. Project
  Boards is not a VSP tab, so it is recorded as UPD-A5 rather than swept into
  this change. The spec's §1.1 and its UPD-A2 are corrected where they stood.
- ✅ **The missing half of that clamp is fixed in the shared module.** On a
  body too narrow to seat two minimums the four copies gave the right panel
  whatever was left over, which below 420px is a negative grid minsize. Tk
  accepts that silently - measured - so nothing ever failed and it survived
  four copies. Both panels are held now, and the body overflows instead.
- ⚠️ **Not seen on screen.** Every test builds its screen on a withdrawn root.
  UPD-M7.2 and UPD-M7.3 are the on-screen criteria and are still open.

### APE Week Assignment, and the week's Action Items (AWA-M1 - AWA-M6)

- ✅ **"APE Weekly" is now "APE Week Assignment", and there is a sixth tab,
  "APE Week Actions".** Weekly Tactics for the selected week on the left; click
  one and its Action Items fill the right panel. Spec and per-criterion status:
  `docs/spec_2026-11-07_ape_week_actions.md` §6.
- ✅ **"Linked to the week tactic" meant two different columns in live data.**
  The re-filing cascade writes `weekly_tactic_id`; APE Week Assignment's own
  `Add Action Item` button writes `parent_id` and leaves the other NULL.
  Counted before writing anything: 49 / 0 in the main database, 0 / 1 in the
  demo one. A reader of one column is correct on this Mac and empty on the
  other. `weekly_tactic.LINK_PREDICATE_SQL` is the union, and
  `test_awam23_one_home_for_the_link_predicate` walks the AST over all of
  `src/getmoredone` to assert exactly one string constant expresses it.
  Corrected by the sweep: this entry claimed the scan already covered `src/`
  and it did not — it covered `screens/` and `vps_manager.py`, and a second,
  drifted copy sat in `weekly_tactic_maintenance._child_count`, outside both.
- ✅ **The right panel subclasses `TodayScreen` rather than copying it.**
  `load_items` and `create_item_row` were already generic; three things in that
  screen were about *today* and were written inline. They became
  `_build_toolbar(parent)`, `EMPTY_TEXT` and `COLUMN_PREFIX` — a pure move,
  checked against the five existing Today test files before anything depended
  on it (26 passed, 1 skipped). `WeekTacticActionsPanel` overrides those three
  plus `get_todays_items`, and nothing else, so edit, complete, timer, push and
  the three inline editors are the same code, not a second copy.
- ✅ **Week identity moved to `week_options.py`.** The three week helpers were
  private to `weekly_items.py` and now have a second caller. All three are pure
  — the clock and the settings object are passed in — so `date.today()` stays
  resolved in the screen and the existing week-options tests are untouched.
- ✅ **The pre-push sweep found one high and five mediums in this batch, all
  fixed with tests** (`8a324cb`, `ac22a78`). The high was the predicate above.
  The mediums: an item holding a different tactic in each link column was
  listed under both; `add_action_item` dropped the create's cascade report, so
  an item that could not be filed into the week looked exactly like one that
  was; and four tests held while the thing they name was broken, including an
  `assert "2" in ...` against a string that ends in a 2026 date and so always
  contained a "2". One medium was dismissed as a false positive — `conftest.py`
  has isolated `AppSettings` for the whole suite since long before this batch —
  with the reason written in `ac22a78`. Four below-medium went to `BACKLOG.md`
  as AWA-S1 to AWA-S4. The security pass found nothing.
- ✅ **A migration that runs on every launch replaced the tactic the user
  chose.** The re-sweep of those fix commits - a cold pass over the fixes
  themselves - found one high that none of the three earlier passes saw.
  `migrate_parent_links_to_weekly_tactic` runs from
  `Database.initialize_schema` on every `DatabaseManager` construction, and its
  UPDATE set `weekly_tactic_id` from `parent_id` for every row whose parent is
  a week item, including rows that already named a Weekly Tactic. So for the
  one item the correction above is about, the next launch replaced the user's
  last choice with the older link and the invariant repair then moved the
  item's dates. Reproduced on a throwaway database before the fix:
  `weekly_tactic_id` B became A, dates moved 2026-11-16 to 2026-11-09. What
  made it a high rather than an old defect is that the first fix round
  documented and tested the opposite rule, in a test that passes only because
  it never reopens the database - the dirty-state case (P8). Fixed in
  `a97b402`, with the reopen test in `e8b9eb7`. Three mediums with it: a create
  showed a "Week Already Taken" notice left over from an earlier clash in the
  session; the AWA-M2.3 guard claimed to catch copies its pattern could not
  see; and `chip_table`'s docstring described the five-renderer consolidation
  as done while nothing imports the module. One low was raised to medium and
  fixed - the fallback chip drew black text on a near-black pill in dark mode
  on 7 of the 10 themes - and one low was fixed in-loop against the sweep
  budget, recorded in `BACKLOG.md` with the reason. Four remain there as
  AWA-S5 to AWA-S8.
- ✅ **A third cold pass, on a different failure family, found no high.** Two
  mediums: the migration's new "kept the user's choice" count reached its
  return value and no log, so a launch that cleared a row's `parent_id` said
  nothing about it; and the `''` behaviour change above shipped with no test,
  in a predicate one of whose two consumers decides which duplicate tactic a
  dedupe deletes. One low was raised to medium - the AWA-M2.3 guard's
  "case-insensitive" claim was empty, because the membership test in front of
  the regex was still case-sensitive. Three lows are `AWA-S9` to `AWA-S11` in
  `BACKLOG.md`, one of them a pre-existing path where a week item nested under
  another week item could stop the app opening (reachability **not**
  established - that is the first step, not the fix).
- ⚠️ **One thing fixed last round was not a defect, and the mutation gate said
  so.** The outer parentheses added to `LINK_PREDICATE_SQL` change no result:
  `AND` binds tighter than `OR` in SQL and the predicate's trailing clause is
  an `AND`, so the grouping was already right. The mutation written for that
  claim came back green, and a direct check on an in-memory table returned
  identical rows either way. The parentheses are kept for readability, the test
  is gone as vacuous, and the claim is retracted in the spec's §6, in
  `BACKLOG.md` and in the predicate's own comment. Fixing something that was
  not broken is cheap here; believing it was is not.
- ⚠️ **The on-screen check has not been run.** Everything above is tests plus
  one refactor verified by an existing suite. The nine-step checklist at the
  end of that spec's §6 is what settles "works like the Today tab", and until
  it is walked that criterion is `not done`.
- ⚠️ **Known gap (AWA-A4):** the inherited drag grip writes `today_pin_rank`,
  the column Today orders by, so dragging a row to the top of the new panel
  also floats it to the top of Today. In `BACKLOG.md`; both fixes are
  behaviour changes beyond what the tab was asked to do.
- ⚠️ **AWA-A1 is open and is now user-visible:** APE Week Assignment's Add
  button still writes `parent_id` while the new tab's writes
  `weekly_tactic_id`. Both are read, so nothing is lost, but the two buttons
  disagree. One line plus a test; the spec recommends it; not in what was
  asked.

### APE quarter/month consistency (APC-M1 - APC-M6)

- ✅ **An APE could be filed under a quarter that does not contain its month.** The APE Month
  screen's Quarter picker opened on the literal `"1"` while its Month picker opened on today's
  month, so on 7 November it offered Q1 + M11 and `assign_ape_to_month` wrote it — the old
  check validated each argument's range and never their relationship. The Quarter picker now
  opens on the current calendar quarter, the Month picker offers only that quarter's three
  months, changing the quarter pulls the month into it, and the manager refuses a mismatched
  pair before writing anything. The APE Quarter screen had the identical hard-coded `"1"`;
  fixed in the same change.
- ✅ **Such a record was then invisible in APE Weekly.** The weekly screen derived the quarter
  from the selected week and asked for `q4 = 1 AND m11 = 1`. A row with `m11 = 1` and
  `q4 = 0` matched nothing, every November week, with nothing on screen to say why. The month
  flag *is* the month assignment, so `get_annual_plan_elements_for_month(year, month)`
  replaces `get_annual_plan_elements_for_period(year, quarter, month)` and both APE screens
  use it. The weekly screen's derived quarter had no other reader and is gone, not renamed.
- ✅ **The rule was written three times and owned nowhere** — a dict in `weekly_tactic`, a
  second dict inside `VPSManager._clear_quarter_month_flags`, and `((month - 1) // 3) + 1` in
  the weekly screen. `date_utils` now holds `QUARTER_OF_MONTH`, `MONTHS_OF_QUARTER`,
  `quarter_of_month()`, `months_of_quarter()` and `current_quarter()`; the three copies point
  at it, as does `first_of_next_quarter`, which had a fourth. Two AST tests keep a fifth from
  appearing.
- ✅ **Stored orphan flags are repaired on open.** `VPSSchema._repair_orphan_month_flags` sets
  the quarter flag every month flag implies. Additive only — a quarter flag with no month in
  it is a real state (assigned to the quarter, not yet to a month), so clearing anything there
  would destroy real assignments. Idempotent, with a dirty-state test (P8) that writes the row,
  closes the manager and reopens the file.
- ✅ **APE Month Save reports what it did.** The screen had no status surface, so a refused
  assignment looked exactly like a successful one. One wording, reached by both the Save button
  and the drop target (P5).
- ✅ **APE Quarter Save reports what it did too** (APC-M6.2, from the sweep). The month
  screen's docstring claimed the reporting class was covered because both of *its* paths
  reported through one wording. The class is four paths across two screens, and APE Quarter —
  edited in the same change for its quarter default — discarded `assign_ape_to_quarter`'s
  boolean on both of its paths and had no status surface at all, so a rejected APE simply did
  not appear in the right-hand panel: what a click on the wrong row looks like. It now has the
  same wording with Q for M, on Save and on drop, and says so when nothing is checked.
- ✅ **A raising assignment is counted, not allowed out of the loop** (APC-M2.4, from the
  sweep). `assign_ape_to_month` does not only return `False` — it raises when an APE's segment
  resolves to nothing. The raise left the earlier APEs written, skipped both the redraw and the
  status line, and left the previous press's "Assigned 3 APE(s)" on screen: a success message
  for a save that half happened, with the traceback going to a stderr a double-clicked app does
  not have.
- ✅ **The repair says which rows it changed** (APC-M5.4, from the sweep). It runs against the
  real database on every open and reported nothing — no count, no log line, no `updated_at` —
  so the only trace was the changed data: an APE in a quarter nobody remembers assigning (P2).
  It now returns the `(ape_id, quarter)` list, stamps `updated_at`, and logs the list when
  non-empty. That also makes its idempotence provable rather than inferred.
- ✅ **The month lookup refuses the junk a caller can reach it with** (APC-M4.4, from the
  sweep). `month < 1 or month > 12` raises `TypeError` on a string and *passes* a float, and
  the month is interpolated as a column name, so `11.0` reached SQLite as `m11.0` and raised
  from inside a Tk callback where nothing is on screen to show it. Not "type-safe", which is
  what this entry first said: an unhashable month still raises and `True` becomes `m1`. Both
  are unreachable from a caller and both are in `BACKLOG.md`.
- ✅ **The status line is read off the row, not off the return code** (APC-M2.5 / M6.3, from
  the re-sweep over the first round's own fixes). `assign_ape_to_month` writes before it can
  fail, so counting its booleans produced "Assigned 0 APE(s) to M11" beside a panel showing
  the row. Both screens now compute the sentence from the same unfiltered query the panel is
  drawn from, and name four states: assigned, partly assigned, could not be assigned, and
  reported assigned but not in the month.
- ✅ **Remove reports too, on both screens** (APC-M2.6 / M6.4). The first round hardened the
  two assign paths and left the two removes silent — the same P5 shape, one layer down. The
  cascade's own call site (`weekly_tactic.py:294`) is the seventh path in that class and is
  flagged in `BACKLOG.md`, not fixed: it has its own `CascadeReport` surface.
- ✅ **The repair's log line is tested** (APC-M5.5). Deleting it left every other APC test
  green, and the spec's reason for not testing it — that it goes to the user's log — was
  already disproved by `test_wt_m7a5_dedupe_log_reaches_a_handler` in this repo.
- Spec: `docs/spec_2026-11-07_ape_period_consistency.md`. Tests:
  `tests/test_ape_period_consistency.py` (53), twenty-five mutation proofs.
  Verified against copies of both real databases: the demo row is repaired and
  appears in APE Weekly; the installed app's 17 APE rows were already
  consistent and the migration changed none of them. Verified on screen against
  the **real** demo database on 2026-11-07 (spec §5.6), and the second round's
  status lines read on screen against a throwaway copy, with the migration and
  its log line observed in the running app (§5.13). Swept by `learning-qa`,
  `/code-review` and `/security-review` (§5.8) — four findings fixed here, one
  medium-high, two medium and one low-medium, with two lows and two adjacent
  issues in `BACKLOG.md` and no security finding — and then re-swept over the
  fix commits themselves (§5.11), which found four more including a defect in
  one of the fixes.

## Recent Changes (2026-08-24)

### Reward-contingent task chunking (the dopamine protocol)

- ✅ **The timer's reward now fires on a completed deliverable, not on the clock.** New
  one-line **Deliverable** field on an action item ("Draft section 2's opening paragraph",
  never "work on the report for 25 min"), a **Done — deliverable complete** button available
  for the whole session, and a **savor** step that names what you set out to do and asks you
  to look at it. Phase-gated: every completion below 15 on a Project, ~40% above it. A
  **celebration** (confetti / balloons / a chime) fires on ~20% at random in either phase,
  always after the savor and never instead of it. New pure `src/getmoredone/reward_protocol.py`
  makes the decision; `screens/timer_window_reward.py` runs it; `screens/timer_window_celebration.py`
  draws it. Spec: `docs/spec_2026-08-23_dopamine_reward_protocol.md`.
- ✅ **Break end is neutral.** `tick()` used to call `stop_timer()` when the break ran out,
  which showed Finished/Continue and so made the timer ringing the thing that ended the work —
  the exact coupling the feature exists to break. It now offers **Pause (rest)** / **Continue
  focus**. That needed a fifth state (`awaiting_choice`): at break end both countdowns are zero,
  and `pause_timer`'s resume rule reads exactly those two numbers, so "just pause instead of
  stop" makes Resume drop into a zero-second break that re-fires break-over every tick forever.
  Stop and Finished/Continue are untouched and pinned by `test_rp43c`.
- ✅ **Two deliberate departures from the spec.** The work log is written once (§4.5 step 4 saves
  one and step 5 defers to a flow that already saves one). The `savor_count` increment moved
  inside `save_work_log` — written as the spec lists it, a window closed between the two leaves
  a project claiming a completion nothing recorded.
- ✅ **`savor_delivered` records the dialog, not the decision.** Derived from `decision.show_savor`
  it is a restatement of the decision and cannot disagree with it, so it could never reveal a
  savor that was decided on and then not shown — which is the only thing the column is for.
  Found by mutation: suppressing the savor dialog entirely left the fifteen-completion test green.
- ✅ **Two dead row mappers deleted.** `DatabaseManager` shadows `_row_to_project_board` and
  `_row_to_project_board_link` on `DBManagerProjectBoardsMixin`; the mixin's copies had not run
  since the day they were duplicated, and had drifted — the dead one does not hydrate
  `start_date`/`end_date`, so the file named after project boards implied a project's dates are
  lost on load. They are not. `savor_count` went on the live copy at `db_manager.py:2048`.
- ⚠️ **A `.gitignore` bug that would have shipped a missing asset.** A bare `audio/` pattern
  matches a directory of that name at *any* depth, so `assets/audio/tada.wav` was excluded from
  git — present on this machine, absent from every clone and CI build. Caught by
  `test_repo_hygiene.py::test_rm7b_ignore_rules_do_not_exclude_a_bundled_resource`, not by me.
  Now anchored as `/audio/`.
- ✅ **Tests** — `test_reward_protocol.py` (11), `test_reward_protocol_schema.py` (15),
  `test_reward_protocol_timer.py` (26), `test_reward_celebration.py` (18). 19 mutations run
  against verbatim originals, all red. Full suite: **1438 passed, 7 skipped** (exit 0).
- ✅ **Four cold review passes, three rounds of fixes, and every round introduced a defect
  the next pass caught.** Highest-value catches: Done never stopped the clock (the break
  alarm fired over the savor prompt, and the test for it was hand-cancelling the tick on
  the line before, doing the fix's job); Start → Stop → Start put Done, Finished and
  Continue on screen together, two of which end the work with no reward protocol at all;
  and the reward sequence ran unguarded ahead of the only code that persists anything, so
  a TclError meant the user pressed Done, saw nothing, and lost the session. Then the
  fixes' own defects: `stop_timer` was too big a hammer and turned the window red and cut
  the music behind the savor prompt; the exhausted-cycle guard was copied from
  `pause_timer` and missed stop-during-break; and the status label claimed success on a
  completion that had failed. Stopped after pass four on the repo's own rule — the trend
  was high → high → medium → medium and unbounded re-sweeping does not converge.
- ⚠️ **A signed-off spec decision was amended.** `spec_2026-08-18_downloadable_release.md`
  D3 says "no audio ships" — users point Settings at their own music folder. The
  celebration needs a sound and the spec forbids fetching one, so `assets/audio/tada.wav`
  now ships. D3 is about not distributing somebody else's copyright; a 30 KB sound this
  repo generates from a committed script is not that. The guard was narrowed, not
  deleted: `GENERATED_AUDIO` names the exempt paths, each must name a generator that
  exists and is committed, and the bytes are proved to be its output. Any other tracked
  audio still fails. Revert is small if that call is wrong.
- ⚠️ **Not seen in the packaged app.** `/Applications/daVIPA.app` was running and holds the
  single-instance lock; it was not killed. The savor copy, the overlays and the chime still
  need a human to look at and listen to once.

---

## Recent Changes (2026-08-12)

### Today: drag-to-top pin + inline date "From today" offset ladder

- ✅ **Drag an Action Item to the top of Today to pin it above all others** — Each open Today row now has a drag handle (`⣿`) at its left edge; dragging it upward pins the item above every other row and keeps it there. Backed by a new nullable `action_items.today_pin_rank` column (schema + idempotent `ADD COLUMN` migration), kept **independent of the derived `priority_score`** (still `I×U×S×V`), so pinning never corrupts scores. `DatabaseManager.pin_item_to_today_top()` sets rank = `MAX(today_pin_rank over open items) + 1`; pin-aware sort keys float pinned rows first in normal, Top-3, and search modes. The pin survives editor saves, priority edits, and reschedules; `update_action_item` now inherits `today_pin_rank` from the DB so a stale full-object save can't wipe it (the column is owned solely by the targeted pin update). Scoped to the Today list only.
- ✅ **Drag mechanics** — The pin decision comes purely from the press→release `y_root` delta (`PIN_DRAG_THRESHOLD`); press and release are bound on the grip itself. The first cut gated on `<B1-Motion>` + a live-cursor drop-zone; `<B1-Motion>` does not fire reliably on a CTkLabel, so no gesture ever pinned. Diagnosed via real Tk `event_generate` on the grip (handler-level tests had passed while the live bindings were dead).
- ✅ **Inline date editor: "From today" offset ladder** — Clicking a row's Start/Due date opens the inline date dialog, which now shows `+1 +2 +3 +4 +5 +6 +7 +10 +14` buttons (below the date field) that set the date to today + N (weekend-aware). Replaces the single current-date `+1`. Offsets live in `TODAY_OFFSET_BUTTONS`. Dialog widened; buttons sized to fit.
- ✅ **Tests** — new `tests/test_today_pin.py` (migration, pin ordering, round-trip persistence, stale-save P22 guard, adversarial sort), `tests/test_today_pin_drag.py` (handler-level up/down/click + a real `event_generate` drag through the actual bindings), `tests/test_inline_date_offsets.py` (ladder presence + today+N). learning-qa pre-push sweep: clean (two low-severity findings fixed — the P22 stale-save and a dead `_first_open_row`). Full suite: **443 passed, 1 skipped**.

---

## Recent Changes (2026-08-06)

### App Dock icon (rocket → GMD check-mark) + Obsidian "Create Note" properties

- ✅ **Dock icon: default Python rocket → GetMoreDone check-mark** — Running the app (`python run.py` / `start.sh`) showed the Python launcher **rocket** in the macOS Dock because nothing set a runtime icon, and the packaged `.app` used `icon=None`. New `src/getmoredone/utils/app_icon.py::set_app_icon()` sets the window/taskbar icon via Tk `iconphoto` (Windows/Linux) **and** the macOS Dock icon via AppKit `setApplicationIconImage_` (pyobjc), called once from `GetMoreDoneApp.__init__` after the Tk root exists. Fully guarded — logs `[ICON] …` and can never block startup. `GetMoreDone.spec` BUNDLE `icon=` now points at the bundled `.icns`. Reuses the existing brand icon (blue rounded square + white check) as `assets/icons/app_icon.{png,icns}`. New macOS-only dependency `pyobjc-framework-Cocoa` (auto-installed via `requirements.txt`). Verified end-to-end: real `run.py` prints `[ICON] app icon set`; in-process `NSApp.applicationIconImage()` is valid 1024×1024.
- ✅ **Obsidian "Create Note" export writes only the 7 Notes-table properties** — The Notes-table export now produces frontmatter that is exactly `Prev, Next, tags, title, entity_id, created, Summary` (in that order). Removed `type` and the action-item extras (`who` / `due_date` / `priority_score`); renamed the old `PREV` / `NEXT` / `TAG` to `Prev` / `Next` / `tags` (lower/camel case). `Prev`/`Next`/`tags`/`Summary` are written empty; `title`/`entity_id`/`created` populated. `create_obsidian_note`'s signature was slimmed (removed the now-unused `entity_type`/`who`/`due_date`/`priority_score` params) and `CreateNoteDialog.create_note` no longer gathers that dead metadata. Side benefit: the in-app note-search `tag:` filter reads `tags:`, which the old `TAG:` writer never matched — producer and consumer are now aligned. Verified through the real `CreateNoteDialog.create_note()` end-to-end (writes the 7 properties in order, creates the `obsidian_note` DB link).
- ✅ **Sweep fixes (learning-qa, pre-push)** — (1) **P19/P3**: the note-search tag extractor grabbed *every* `- item` line in the frontmatter whenever `tags:` appeared, so the new list-typed `Prev`/`Next` would leak their link targets into `tag:` results once populated. Extracted a scoped, unit-tested `_extract_frontmatter_tags()` that reads only the `tags:` block. (2) **P14-adjacent**: `title: "{title}"` wasn't YAML-escaped — a title containing `"` or `\` broke the whole frontmatter; added `_yaml_dq()` and applied it. Both pre-existing/latent but made reachable/re-touched by this batch.
- ✅ **Tests** — new `tests/test_app_icon.py` (3: asset present, iconphoto set + reference retained, missing-asset safe); new Obsidian property-set guard (`test_create_note_has_only_the_export_properties` asserts all 7 present, all legacy keys absent, correct order) + quoted/backslash title round-trip; real `_extract_frontmatter_tags` cases (inline, block scoped past Prev/Next, absent). Full suite: **429 passed, 1 skipped**.
- ⚠️ **Known gap** — `Prev`/`Next`/`tags` are written empty (bare `key:`), matching how Obsidian serialises empty List/Tags properties. They render as List/Tags in a vault where those types are registered (as in the spec image); in a brand-new vault with no type registry an empty property defaults to Text until its type is set once. Emit `[]` instead if guaranteed List typing in fresh vaults is ever needed (logged to BACKLOG).

---

## Recent Changes (2026-07-26)

### Timer button in the editor + music finder fix + Obsidian note-open fix

- ✅ **⏱ Timer button on the Edit Action Item window** — The working-mode timer (countdown + break + background music + notes) was only reachable from Today/Upcoming/All Items. Added a full-width **⏱ Timer** button to the editor's action area, shown only for existing, non-completed items. It **saves pending edits first** (so the timer reflects the on-screen time block and notes), then opens the timer. On timer close it reloads notes/next-action **and planned-minutes** from the DB so a later Save in the editor can't clobber what the timer changed. `save_item()` now returns a success boolean.
- ✅ **Timer music: "can't find music" fixed** — Two causes. (1) With no music folder configured the finder bailed out; it now falls back to the app's bundled `audio/` folder so music works out of the box. (2) `.aif`/`.aiff` were excluded from the format allowlist, so a folder of playable AIFF tracks looked *empty* (only MP3s were seen) — AIFF is now a recognized/preferred format (pygame/SDL loads it). Failures were console-only; the timer window now shows the real reason inline ("No music folder set…", "No playable music in …", "♫ *track*", or a playback error). Format list + folder resolution centralized in new `src/getmoredone/utils/music_library.py` (was duplicated in 3 places); new `paths.bundled_audio_dir()`.
- ✅ **Obsidian "Open" note fix** — The Open button "blinked the screen but the note didn't open" for any note whose name contains spaces (every app-created note is `"{Title} - {date}.md"`). `open_in_obsidian()` built the `obsidian://` URI without percent-encoding (it only replaced backslashes, despite a comment claiming otherwise), so the raw space made the URI malformed. Now percent-encodes the vault name and file path (keeping `/`). Notes without spaces were unaffected, which had masked the bug.
- ✅ **Tests** — new `tests/test_music_library.py` (12: AIFF recognition, bundled-folder fallback, per-status messages), `tests/test_obsidian_integration.py::TestOpenInObsidianURI` (4: space/subfolder/no-space/outside-vault), and timer/editor tests in `tests/test_timer.py` + `tests/test_item_editor.py` (save-first gating, dirty-state planned-minutes reload, play-button state on music failure). Full suite: **410 passed, 1 skipped**. Real-widget smoke test confirmed the editor button visibility rules and the timer's music status line.
- ✅ **Editor save-success detection fixed** — `save_and_close`/`save_and_new`/`duplicate_item` previously inferred success from the error-label text (`save_and_new` didn't even check it), so they closed/reopened/duplicated even when validation failed. They now gate on the `save_item()` bool: a validation error keeps the dialog open with the message shown. Tests added for all three (failure vs success paths).
- ✅ **Editor ⏱ Timer button disables after completion** — if the timer completes the item (Finished/Continue), the editor's Timer button is now disabled on close so it can't re-open a timer on a done item (guard also added in `start_timer`).
- ✅ **Non-modal edit no longer clobbered** — the timer is a floating window, so you can edit the editor's Description/Next Action while it runs. `start_timer` now snapshots those fields; the on-close reload refreshes only the fields you left untouched (your in-flight edit wins), while untouched fields still pick up the timer's DB changes. Verified in a real-widget test (edited field preserved, untouched fields reloaded).
- ✅ **Second learning-qa sweep clean** — a retroactive sweep of the obsidian/save-gating/timer-hardening commits found no high-confidence issues. Applied one low-severity hardening: narrowed the editor's post-timer `except Exception` blocks to `(tk.TclError, AttributeError)` so a genuine logic error can't be silently swallowed (P2), matching the `timer_window.py` idiom. One informational property logged to BACKLOG (whitespace-only edits count as "untouched"). Full suite: **422 passed, 1 skipped**.

---

## Recent Changes (2026-07-17)

### Scheduler project attach + Item Editor UX + email-import cleaning

- ✅ **Scheduler: attach items to projects (bug fix + filter + select-all)** — The Projects tab was empty because `get_project_boards(show_pending=True)` built `statuses=[PENDING]`, *replacing* active instead of augmenting it, so with zero pending boards it returned nothing. Fixed so active is always shown and the flags add pending/completed. With the tab populated, the existing drag-to-attach / click-to-filter machinery works: drag 1–N (checked) items onto a project box to attach them (links stay **exclusive** — one project per item), click a project (or the new header **Project:** filter) to list only its items, then move them to a date from the Date Boxes/Calendar tab. Added a **Select-All** checkbox in the item-list header row (checks/unchecks every row, stays in sync with individual toggles). Stale-filter guard (P6): if the selected project leaves the list, the filter clears.
- ✅ **Item Editor: resizable window + draggable divider** — The editor is now resizable (`minsize` 700×500) with a draggable sash between the two columns; the right panel's right edge stays pinned to the window while dragging rebalances the split, and the right column's tab content fills the widened panel. Replaced broken reflow handlers that threw `AttributeError` on every resize.
- ✅ **Notes: seed from item + reachable Open** — Creating a note from an Action Item pre-fills the note body with the item's Description and Next Action (markdown sections). The note-row **Open** button (and delete) were being pushed off the narrow notes panel by long titles — buttons now pack first so they stay reachable, and double-clicking the title opens the note too. Same packing fix applied to the Link-note dialog.
- ✅ **Gmail import: strip footers + excess blank lines** — Imported email bodies are cleaned before landing in the description: blank-line runs collapse, decorative separator lines are removed, and trailing footer boilerplate (unsubscribe blocks, "you received this because…", copyright lines) is truncated. Editorial phrases live in `src/getmoredone/email_cleaning_rules.json` (config, not code); the importer logs how many lines were removed. Already-imported items are left unchanged.
- ✅ **Tests** — new `tests/test_item_editor_sash.py`, `tests/test_note_seed_content.py`, `tests/test_email_cleaning.py`, `tests/test_scheduler_project_attach.py`, plus a `get_project_boards` regression in `tests/test_database.py`. Full suite: **387 passed, 1 skipped**.
- ⚠️ **Known gaps** (from the learning-qa sweep): email footer detection is substring-based and aggressive by design for automated notifications — a *legitimate* mid-body mention of e.g. "unsubscribe" after the first content line would truncate what follows (mitigated: first-line phrase never cuts; drop count is logged). The Select-All per-checkbox loop keeps a broad `except` to tolerate a destroyed widget mid-refresh.

---

## Recent Changes (2026-07-08)

### Reusable column resizing + Scheduler all-columns resize / title-fill fix

- ✅ **New shared module `screens/column_resize.py`** — `ColumnResizer` + `ColumnSpec` + `chars_for_width`. One instance per screen owns column widths, persistence, the draggable divider handles, and live text re-clamping. Both the Today and Scheduler screens now use it (the two prior duplicate implementations were deleted).
- ✅ **Scheduler: all data columns resizable** — Title, Segment, SubSegment, Category, and Start Date each have a draggable divider ("end of column" line) at their right edge. Extra space goes to a trailing spacer column.
- ✅ **Scheduler: title fills the column (bug fix)** — Previously the title was clamped to a fixed 20 chars at render (`ITEM_TITLE_CHARS`) while only the drag path recomputed `width//8`, so a wide Title column still showed "BTA Video Posting…". Clamp now follows the actual column width everywhere (e.g. ~87 chars at 700px). Removed the dead per-screen constants.
- ✅ **Persistence** — widths stored in new `AppSettings.today_col_widths` / `drag_schedule_col_widths` dict fields (keyed by column id); legacy `*_title_col_width` scalars kept as fallback so existing Title widths survive.
- ✅ **Today** — migrated onto the shared resizer (Title-only resizable, behavior unchanged; `set_cell_width=False` because its title label sits inside a sub-frame).
- ✅ **Tests** — new `tests/test_column_resize.py` (chars-for-width, wide-title regression guard, legacy fallback, clamp bounds, dirty-state persistence); updated `tests/test_today_title_col_width.py` for the new dict field. Headless smoke test built both screens + simulated resizing all columns with 0 errors. Full suite: **365 passed, 1 skipped**.

---

## Recent Changes (2026-07-07)

### Today view: pinned column headers + resizable Title column

- ✅ **Pinned column-heading row** — The Today screen now has a fixed heading row (Title, SubSegment, Category, Context, Who, Start, Due, Pri, Time) that stays put above the list while rows scroll. Column widths mirror the data rows.
- ✅ **Resizable Title column** — The Title column (first text column) is now a fixed, draggable width. A 4px vertical divider at the right edge of the "Title" header doubles as the "end of column" line and the resize handle (`sb_h_double_arrow` cursor). Dragging live-resizes the column and re-clamps row titles with `…`; the width persists via the new `today_title_col_width` AppSettings field (default 260px, clamped 120–800). Mirrors the Scheduler pattern from `13cab10`.
- ✅ **Tests** — New `tests/test_today_title_col_width.py` (default value, save/load round-trip over dirty state, clamp bounds). Full suite: **357 passed, 1 skipped**.
- ⚠️ Pinned-header alignment uses a fixed `padx=25` inset to line up over the scrolled rows; verify visually and tune the inset if columns drift on your display.

---

## Recent Changes (2026-06-15)

### Scheduler group-drag, Project↔APE linking fixes, and delete guards

- ✅ **Scheduler checkbox group-drag** — Each item row on the Scheduler's left list now has a checkbox. Dragging a *checked* row moves every checked item together to the dropped date or project; dragging an *unchecked* row still moves just that one item (single-drag unchanged). The drag label shows the count when dragging a group.
- ✅ **Link Action Items dialog: filters + bulk link** — The project "Link Action Item" dialog gained `Completed` / `Not Completed` / `Linked` / `Not Linked` filter buttons (AND logic), per-row checkboxes, and a **Link Selected** button to attach a batch at once.
- ✅ **Projects require an APE** — The project editor now requires an Annual Plan Element and defaults new projects to `Contribution - Projects - Projects`. This was the real cause of "Save doesn't work / cards have no color": see next item.
- ✅ **Root-cause fix — dropped 1:1 APE↔project unique index** — A `UNIQUE INDEX idx_project_boards_unique_ape` enforced one project per APE. Editing a project to use an already-used APE threw `UNIQUE constraint failed` *after* the dialog closed, so the save silently failed and the APE stayed null → no card color. A migration drops the index (the regular `idx_project_boards_ape` lookup index is retained); multiple projects can now share one APE (e.g. the catch-all default). Runs automatically on next launch.
- ✅ **Delete guards (prevent silent cascade data loss)** — Deleting an **Annual Plan record (APE)** is blocked when projects are attached (more than the lone empty starter board, or any board with linked items). Deleting a **Vision Element** is blocked when child records exist (annual records, projects, or linked action items). Both show a dialog listing what is attached and require manual delete/reassign first.
- ✅ **Tests** — New: `tests/test_schedule_checkbox_drag.py`, `tests/test_link_action_items_dialog_filters.py`, `tests/test_project_shared_ape.py`, plus delete-guard cases in `tests/test_vps_hub_crud.py`. Full suite: **334 passed, 1 skipped**.
- ⚠️ Adjacent (not changed): `get_project_boards(show_pending=True)` returns only pending boards (active is added only when no status flag is passed) — pre-existing, unrelated to this work.

---

## Recent Changes (2026-06-06)

### Project Board: Bulk Edit + first-class Project Notes section

- ✅ **Bulk Edit on Action Items** — Checkbox-based multi-select with a "Select All" header on the project's Action Items list. The "Bulk Edit" button (enabled when ≥1 item is selected) opens a dialog to set Start Date and/or Priority on the selected items at once. Start Date validation: today or later only; Due Date auto-set to Start + 1 day; leaving a field blank or selecting "(Skip)" preserves existing values.
- ✅ **📄 chooser on project tile** — Clicking the paper icon now opens a small chooser asking "Create New Obsidian Note" or "Link Existing Obsidian Note" (the "Open Notes" toolbar button is unchanged for explicit "browse my linked notes").
- ✅ **Project Notes section** — The right panel of a selected project now lists each linked Obsidian note as a first-class row with its own Status, Open / Complete-or-Reopen / Unlink buttons. Sorted newest-linked first. The old "N notes linked to this project." one-liner is removed.
- ✅ **Per-link Status on `ProjectBoardLink`** — Project Notes have Open / Completed lifecycle (migration runs automatically; existing notes default to Open). Status is per-project, so the same Obsidian doc linked to two projects has independent statuses.
- ✅ **Shared "Show Completed" toggle, default OFF** — One checkbox above both sections filters BOTH the Project Notes list AND the Action Items list. Default off so the first view shows only open work (per user direction).
- ✅ **New setting: Project Notes Folder** — Settings → Obsidian Integration now has a "Project Notes Folder" entry (default `GetMoreDone/Projects`). New project notes land here instead of the generic Notes Subfolder. Blank value falls back to the generic Notes Subfolder so users who don't set it don't break.
- ✅ **30 new automated tests** in `tests/test_project_notes.py` plus updates to existing tests. Full suite: 328 passed, 1 skipped.
- 📄 Spec coverage table: [`docs/spec_coverage.md`](docs/spec_coverage.md).
- 📄 Plan: [`docs/implementation_plan_2026-06-06_project_notes.md`](docs/implementation_plan_2026-06-06_project_notes.md).
- ⚠️ Known follow-ups, not fixed in this change (documented in `docs/spec_coverage.md`):
  - Duplicate `_row_to_project_board_link` / `_row_to_project_board` methods in `db_manager.py` shadow the mixin's via Python MRO — both are now in sync but the duplication is a latent footgun.
  - `open_note_picker` (toolbar "Open Notes" dialog) is now functionally redundant with the in-panel list.
  - The freeform `ProjectBoard.notes` text field shares a name with the Obsidian Project Notes concept — long-term naming debt.

---

## Recent Changes (2026-01-24)

### VPS Segment Management in Settings (NEW)

- ✅ **New Settings Tab: VPS Life Segments** - Manage all life segments in one place
- ✅ **Create/Edit/Delete Segments** - Full CRUD operations for life segments
- ✅ **Color Picker** - Visual color picker with hex code input and preview
- ✅ **Segment Display** - Shows color preview, name, description, and active status
- ✅ **Order Management** - Set display order for segments
- ✅ **Active/Inactive Toggle** - Hide segments without deleting them
- ✅ **Smart Deletion Protection** - Cannot delete segments with linked records
  - Shows exact count of linked visions (e.g., "3 linked visions")
  - Provides step-by-step instructions to remove linked records first
  - Warns about cascade deletion of child records
- ✅ **9 Comprehensive Tests** - Full test coverage including multiple vision scenarios

### VPS (Visionary Planning System) Bug Fixes

- ✅ **Fixed New Vision button crash** - Replaced non-existent `CTkMessageBox` with standard `tkinter.messagebox`
- ✅ **Fixed empty year field validation** - Now provides sensible defaults (current year for start, +10 years for end)
- ✅ **Added segment multi-select** - New checkbox dialog to select/deselect multiple life segments for display
  - "Select Segments..." button shows selection dialog
  - Select All / Deselect All options
  - Button displays count (e.g., "3 of 5 Segments")

---

## Recent Changes (2026-01-23)

### Item Editor Improvements

- ✅ **Save button** - Now keeps window open after saving (shows "✓ Saved" confirmation)
- ✅ **Save & Close button** - New button that saves and closes window
- ✅ **Duplicate button** - Saves current changes first, then opens duplicate in NEW window (keeps original open)
- ✅ **Create Tasks button** - Renamed from "Create Sub-Item", now creates one child task per line in Next Action field

### Timer Window Improvements

- ✅ **Independent music controls** - Separate Play/Pause buttons for music (purple) independent from timer controls
- ✅ **Music continues when timer paused** - Timer pause doesn't affect music playback

---

## Known Issues

Bug - the Today listing should ONLY show items completed on Today. Not previous days.

---

## Feature Requests

FR - make the Edit Next Action screen float independent the main screen.
