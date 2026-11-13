# daVIPA Backlog

Last Updated: 2026-11-09 — trimmed back to what is active, in two passes.
245 items became 73: the closed ones, the review-sweep residue ("below
medium", "cold pass", "deferred") and the items whose subject was deleted with
the prose-reading guards are filed in
`docs/unused-docs/backlog_archive_2026-11-09.md`, with the reason on each. The
running "Last Updated" narrative that used to sit here went with them.

Then 73 became 49, under `standards/effort-budget.md` rule 3: a below-medium
finding about a test or a document is dropped, not filed. The 24 are named in the
commit that removed them, which is their whole record: 18 about tests, 5 about
documents, and one stale code item (a 2026-08-18 entry describing
`screens/reschedule_dialog.py` in the present tense; that file was deleted in
`a8b8d05` and the class it named is in no `src/` file). Then three of the Plan
screen's on-screen reports were confirmed gone on 2026-11-10 and left with that
confirmation, which is how the code items below number 31: 13 a user would see,
15 internal duplication or dead code, 3 in `tools/agents/check_docs_sync.py` —
plus 6 test items of medium severity, and the feature requests, user stories and
notes at the end.

One batch at a time in this checkout (`CLAUDE.md`). What is here is open work:
adjacent issues from recent batches, screen reports, the carried-forward
features, and the long-standing bugs, requests and user stories at the end.

## Adjacent issue — the band thresholds outlived the bands (PBG, filed 2026-11-12)

### PBG-A9 — the badge's pill is nearly the value of the row behind it (low)

In the light themes the shipped level fills (`#DCFCE7`, `#FEF3C7`) measure
about 1.3:1 against `surface_subtle`, so on screen the badge reads as a number
rather than as a coloured pill. The number itself is the signal and the badge's
*text* is derived for contrast by `level_cell_fill`, so nothing is illegible —
but the Plan screen traded a two-theme band table, whose values were held to
3:1 and 10:1 bars, for a scheme with no such bar, and that trade was not
measured when it was made.

Not fixed, because the fix is to darken the level defaults and those are the
colours the user set and the five list screens already draw. The same property
is true on all six screens; this is not a Plan-screen defect.

Fix when touched: decide whether the level fills want a minimum against the
row surface at all. If they do, the bar belongs in
`tests/test_priority_level_colors.py`, over all six screens at once, not here.

## Adjacent issues — the surface separation's neighbours (SEP, filed 2026-11-12)

Found during SEP, older than it, not fixed (rule 10).

### PBG-A12 — eight themes put muted label text at 2.5–3.0:1 in light mode (medium — a decision)

`base_dark_blue`, `blue`, `davipa`, `green`, `grey`, `orange`, `pink`,
`purple` ship CustomTkinter's `#858585` placeholder, which the app also uses as
a label colour: 2.50–3.09:1 on their light surfaces (bar 4.5). Dark mode
passes. Your call: darken it in eight themes, or split placeholder from label
colour. Unguarded.

### PBG-A11 — two bundled themes make one surface where the app wants two (medium — a decision, reopened)

`apple_grey` and `black_white` set `CTkFrame.top_fg_color` equal to
`fg_color`, so list rows and Plan chips have no edge on them. Pinned by
`test_pbga11_…`'s exact set. SEP changed the two themes and was backed out the
same day: an unnamed frame takes one token or the other by nesting depth, so the
change landed differently on every screen. SEP-A1 has to come first. Filed text:
`docs/unused-docs/changes/2026-11-12-pbg-a11-retired.md`.

### SEP-A1 — inherited surfaces that may collide like the Plan screen did (medium)

An unnamed `CTkFrame` surface flips with nesting depth. `today.py:210`'s pinned
header is measured flat on all ten themes; `project_boards.py` (4),
`item_editor_dialogs.py` (2) and `item_editor_project_dialog.py` (1) have the
same shape, unmeasured. Better fix than eight edits: a guard that measures a
rendered child against the widget behind it.

## Adjacent issue — child processes redirect the data directory by hand (CIG, filed 2026-11-12)

Found while fixing CIG-M1, the CI guard failure on `weekly_tactic_debug.log`,
and not fixed, under global rule 10.

### CIG-A1 — every test subprocess that imports the app must remember `GETMOREDONE_DATA_DIR` (low)

`conftest.py` isolates the weekly-tactic log in-process only
(`_preattach_weekly_tactic_log`). A child Python process gets no conftest, so
each call site sets the override itself: `test_first_run.py`,
`test_selftest_cli.py`, the two render helpers, and now `test_ci_contract.py`'s
import probe. The probe was the one that forgot, and it went unseen locally
because the real file already exists there. A session-wide child environment
would make this structural, but `pytest_sessionstart` deliberately unsets the
variable and `tests/test_demo_install.py::test_d1_the_suite_runs_with_no_data_dir_override`
pins that, so it is a design change, not a one-line fix.

## Open decision — what the colour inventory counts (CIV, filed 2026-11-11)

Both raised by the sweep over the gray-scale batch, and both about what the
document measures rather than defects, so neither was settled in the batch.

### CIV-A2 — prose about colours is counted as colour usage (medium — a decision)

CIV-A1 stopped the scan reading documents; the same effect survives inside
`src/`. Measured 2026-11-11: the `### ``#abc``` section's 6 rows are all
docstrings explaining that a three-digit hex gets expanded, and
`src/getmoredone/theme.py:16`'s `THEME_NAMES` contributes 4 named occurrences
that are theme identifiers, with 4 more from `generate_ctk_themes.py`.

A decision, not a defect: excluding comment lines would also drop comments
naming a real fill, such as the `# deep -- the ``low`` fill is #052E16` line
the report carries. The question is whether section 1 counts colours *used*
or colours *mentioned*. Implementable in `SCAN_COMMANDS` alone.

### CIV-A3 — `assets/icons/*.svg` is still uninventoried (low)

5 named-colour occurrences in shipped UI resources, named in the report's own
"Not covered" line since CIV-A1. One entry in `UI_CODE_PATHS` plus a `-g`;
the open question is whether an icon fill belongs in a report whose Hard Rule
is about widget colour.

## Adjacent issues — the unified panel walk's follow-ups (UPD-F, 2026-11-08)

Found while building UPD-F2, UPD-F3 and UPD-F4. Recorded rather than fixed,
per the standing rule that a feature change does not silently sweep adjacent
code. The plan's §8 holds the same list with its reasoning.

### 2026-11-08 - Type: Technical Debt

**Title:** UPD-A10 - a column at the five-character floor clips its own heading
**Description:** UPD-F4 dropped every resizable chip column's minimum to
`column_resize.min_column_width()`, five characters, 40px at `CHAR_PX = 8`,
because step 7 of the on-screen walk asked for "all columns to resize ... down
to 5 character widths". Three headings are longer than that floor: measured in
the bold header font inside pytest, "SubSegment" is **84px**, "Category" 60px
and "Segment" 58px, against a 40px minimum. A column dragged or fitted to the
floor therefore shows about five characters of a ten-character heading, and
`build_header` clips rather than wraps, so the heading reads "SubSe...".

This was already true at the old 60px minimum - "SubSegment" did not fit that
either - so UPD-F4 made an existing fault worse rather than introducing one.
The two honest fixes are both design decisions nobody has made: shorten the
headings ("Sub", "Cat", which is what `weekly_items.py`'s *filter* labels
already say - see UPD-A12), or give each column a floor measured from its own
heading, which would mean a `min_width` that is computed rather than declared
and would break the `min_width <= default_width` invariant
`::test_updm31_every_shipped_column_declares_a_width_it_can_have` pins.
**Priority:** Low
**Effort:** Low

### 2026-11-08 - Type: Technical Debt

**Title:** UPD-A11 - APE Week Actions' right panel does not rescale with the divider
**Description:** UPD-F4 wires `SplitPanel`'s new `on_apply` callback to
`chip_table.panel_fitter(...)` on all five two-panel tabs, but Week Actions
passes its **left** table only: its right panel is
`WeekTacticActionsPanel(TodayScreen)`, which has its own `ColumnResizer` under
the `week_actions` prefix and its own grid padding, and is not a `ChipTable`.
So on that one tab, dragging the divider rescales the left panel's columns and
leaves the right panel's where they were.

`panel_fitter`'s docstring says this, and
`::test_updf41_the_divider_is_wired_to_both_panels` asserts the one-table
wiring verbatim so it cannot become half-done by accident. Fixing it means
either `fit_to_width` called directly on `TodayScreen`'s resizer with that
screen's own padding accounted for - which is a second padding accounting to
keep in step with the first - or moving Today's columns onto `ChipTable`,
which is a batch of its own. The same question applies to the Today and
Scheduler screens, which use `ColumnResizer` without a `SplitPanel` at all.
**Priority:** Low
**Effort:** Medium

## Adjacent issues — Plan day calendar export (CE, 2026-11-08)

Found while building CE-M1 to CE-M5. Flagged, not fixed (global rule 10): each
is real, none is what was asked for, and each sits in code the export only
reads past.

### CE-A3 — `GoogleCalendarManager.__init__` authenticates (low)

Constructing the manager runs the OAuth flow or raises, so the class cannot be
built to ask it a cheap question. The export works around it with an injected
client factory on the screen (CE-M4.5) rather than reshaping the constructor,
because every existing caller depends on construction meaning "authenticated".

**Priority:** Low
**Effort:** Medium

### CE-A4 — the calendar dialog's create path is a second exporter (low)

`screens/calendar_dialog.py::create_event` writes an `ItemLink`, sets
`is_meeting` and opens a browser tab. The day export deliberately does none of
that, so there are now two ways an event reaches Google from this app with
different side effects. Not unified in this batch: the dialog's side effects
are what the Item Editor's flow is for, and dropping them would be a silent
change to it.

**Priority:** Low
**Effort:** Medium

## Outstanding — the calendar export's manual checklist (CE, 2026-11-08)

The six steps at the end of
[`docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md`](docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md)
are the part of CE-M1 - CE-M5 no test can cover: a real export, against a real
Google account, seen on the real calendar. The batch's status report does not
claim them as done and neither does this entry. They need the app driven by
hand, so they sit here until someone walks them.

**Priority:** Medium — the export is built, four cold passes deep and committed,
but nobody has yet watched it write a real event.
**Effort:** Low (one planned day, one account)

## Next feature — Google Calendar into the Plan (CIP, specced 2026-11-08)

Spec: [`docs/spec_2026-11-08_calendar_into_the_plan.md`](docs/spec_2026-11-08_calendar_into_the_plan.md).
**Batch 1, the read half, and batch 2, editing a meeting from the Plan
(CIP-M4), are built (2026-11-13).** Both owe an on-screen walk:
`docs/unused-docs/changes/2026-11-13-cip-read-half.md` and
`docs/unused-docs/changes/2026-11-13-cip-editing.md`. What is left is the week view (M6),
batch 3.

Read the connected calendars, show each day's commitments on the Plan grid so
the day is planned around the hours that are already gone, and let a commitment
the user owns be moved, resized, retitled or deleted from inside the day plan.
Phase 1 is the selected day; phase 2 is a seven-day planning view over the same
cache. `calendar_importer.py` stays: an action item is *what* has to be done, a
commitment is *when* something is already decided, and the work a meeting
causes usually needs a block before that meeting.

Two things the plan step has to settle, both recorded in the spec:

- **It wants to be two batches.** The read half (CIP-M1 to M3, M5) is
  self-contained and provable with a fake client. The editing half (CIP-M4)
  writes to other people's calendars and deletes events, so it should get its
  own review sweeps rather than riding along with the plumbing.
- ~~It cannot start while PD-M14 is in flight.~~ PD-M14 is done; batch 1
  extended `time_block_layout.py` after it.

**Priority:** Next feature
**Effort:** High (two batches)

## Adjacent issues — priority level colours (PLC, 2026-11-08)

Found while building PLC-M1 to PLC-M5. Flagged, not fixed (global rule 10):
each is real, none is what was asked for, and a fix for any of them would be a
silent sweep of behaviour nobody asked about. `SCV-A1`, `SCV-A2` and `SCV-A3` were
added 2026-11-11 on the same terms, by the batch that closed `LRR-A1`.

### PLC-A2 — Hierarchical and Completed ignore their own segment colour for the fill (low)

Both resolve `segment_color`, apply it as an accent, and then never consider it
for the row background, unlike Today, Upcoming and All Items
(`hierarchical.py:231-239`, `completed.py:204-212`). Either the accent-only
treatment is right and the other three are wrong, or the reverse; nothing
records which, and `row_fill` preserves the difference by having both pass
`segment_color=None`.

### PLC-A4 — `settings.py` is 1214 lines (low)

Well past the 700-line refactor mark in
`~/.claude/standards/file-maintainability.md`. This batch added nothing to it
but a mixin import and a tab, following `settings_integrations.py`, so the
direction is right; the six sections already in it remain.

## Adjacent issues — one panel design across the VSP tabs (UPD, 2026-11-07)

Found while building UPD-M1, recorded under the standing rule rather than
fixed in a sweeping diff.

### 2026-11-07 - Type: Technical Debt

**Title:** UPD-A5 - project_boards.py holds a fifth copy of the splitter, with a better clamp than the four
**Description:** `src/getmoredone/screens/project_boards.py:772-1126` has its
own splitter: `SPLITTER_WIDTH = 8`, `MIN_PANEL_WIDTH = 300`,
`_split_ratio = 0.6`, `_on_divider_press/_drag/_release`, and the apply inlined
into `_on_body_resize` rather than a separate `_apply_split_ratio`. The spec's
§1.1 said the splitter was written out four times; it is five, and the fifth
was found by the AST scan behind `test_updm15_no_screen_keeps_its_own_splitter`
rather than by reading. Two things follow. First, `split_panel.py` is not yet
the single owner it claims to be, and this screen is the one file that keeps
its own numbers for reasons of its own (a 300px minimum and a 0.6 default both
suit a board/detail layout, not two equal panels). Second, its clamp was
already **right** where the four were wrong: `right = max(MIN_PANEL_WIDTH,
total - left)` at `:1124`, which is the line UPD-M1.3 had to add to the shared
module. Not fixed because Project Boards is not a VSP tab and nothing in the
request named it, so adopting it here would be a change to an unrelated screen
on the back of this work. The scan asserts exactly what this file still
defines, so the day it is consolidated the test says so.
**Priority:** Low
**Effort:** Medium

### 2026-11-07 - Type: Technical Debt

**Title:** UPD-A6 - UPD-M1.5 cannot read 0 until UPD-M4, and the holdout list is a second place to keep in step
**Description:** `test_updm15_no_screen_keeps_its_own_splitter` asserts an
exact set, not a floor, so it is a real guard: it goes red if a seventh screen
grows its own splitter, and red again when `annual_vision_segments.py`,
`ape_period_view.py` or `weekly_items.py` adopts and is not struck off
`SPLITTER_HOLDOUTS`. That second failure is deliberate - an adoption that
leaves the list stale should not pass - but it does mean the list is a second
place that has to be kept in step with the code until UPD-M4 empties it. It is
recorded so that nobody reading the criterion as `done` is misled: the
criterion is `partial` in the spec's §10 and in `docs/spec_coverage.md`, and it
closes when the last holdout adopts. Not an action in itself.
**Update 2026-11-07, after UPD-M4:** the claim in this entry's title that
UPD-M4 empties the list was wrong, and so was the spec's §4 and both guard
docstrings. UPD-M4 covers the three APE/Annual tabs; the fourth copy of the
splitter and of the drag is in `weekly_items.py`, which UPD-M5 rewrites. Both
holdout sets are down to that one file, and both criteria close at UPD-M5.
**Resolved 2026-11-07 at UPD-M5.** `weekly_items.py` adopted, both holdout sets
are `set()`, and both guards now assert emptiness - so the second place to keep
in step is gone, and neither criterion is `partial` any more.
**Priority:** Low
**Effort:** Low

### 2026-11-08 - Type: Technical Debt

**Title:** UPD-A9 - the filter triple and the category chip colour are still written out five times each
**Description:** UPD-M6 needed both rules on APE Week Actions and moved them
into `screens/lineage_filters.py` (new) and
`segment_color_utils.load_category_color_map` / `resolve_chip_colors` rather
than writing a sixth copy, and moved `weekly_items.py` onto them in the same
change because that screen is the other one UPD-M5/UPD-M6 own. Five files
still hold their own copy of one or both:

- the three combos with the `All` sentinel and the match predicate -
  `ape_assignment.py:43`, `ape_period_view.py:43`,
  `drag_schedule.py` and `item_editor_weekly_tactic_dialog.py`, plus
  `weekly_items.py`'s combos themselves (its *predicate* and row readers are
  shared now, the widgets are not).
- the lower-cased three-part category colour key with its fall-back -
  `ape_assignment.py:406`, `ape_period_view.py:512`,
  `annual_vision_segments.py:214`, `drag_schedule.py:914`,
  `item_editor_weekly_tactic_dialog.py:274`.

Two of those five fall back differently: `annual_vision_segments` prefers the
row's own `category_color_hex` and then the segment's colour, and the tactic
dialog adds a `gray20` floor. That is why this is recorded rather than swept -
reconciling the fall-backs is a behaviour change on four screens, in a
different batch, with its own tests. This is the P5 shape: one rule, six
places, easy to get subtly wrong in one and not another.
**Priority:** Medium
**Effort:** Medium
**Also (2026-11-13, from the SCV-A2 survey):** the weekly tactic picker
(`item_editor_weekly_tactic_dialog.py`, about :274-284) passes
`vision_categories.color_hex` to `fg_color` only stripped. Unreachable today,
because `get_vision_categories()` repairs malformed rows first; moving the
dialog onto `resolve_chip_colors` closes it.

## Reported from the running screen — Plan / Day Plan (2026-11-07)

Four faults were reported after the PD-* batch shipped. Three were confirmed
gone on the running app on 2026-11-10 — the blank panel a moved block left
behind, the two ends of the day refusing a drop, and the missing drag-scroll —
and left this file with that confirmation. What remains is the fourth.

That one had two answers in it: the buttons asked before they wrote, and a drag
wrote without asking. The asymmetry was PD-M13's decision, taken because a
dialog could not be put on the screen at the moment a drag is released. On
2026-11-10 the question was asked for on the drop as well. It is built and
unverified on screen.

### 2026-11-10 - Type: Bug

**Title:** A single item dropped on a non-work day should ask, as AutoLoad does
**Description:** AutoLoad raises the confirmation on a day outside the working
week; dragging one item onto that day writes it and says so in the status line
only. Both should ask, and the drop is the one the walk found silent.
**Priority:** High
**Effort:** Built — waiting on walk step 4
**Notes:** PF-M1 asks in the release handler, after the pointer is read and
before the write is deferred to the idle callback the platform refused a dialog
in. It is the moment the Scheduler already asks from, and the ask is wrapped: a
platform that refuses it writes the block and names the day, which is the
behaviour it replaces. `docs/unused-docs/implementation_plan_2026-11-10_plan_walk_followups.md`
step 4 settles it.


## Adjacent issues from the plan day-controls batch (2026-11-06)

Found while building PD-M2 and PD-M3, not introduced by either, and not fixed
in the batch that found them — rule 10.

- **A Settings screen left open holds a stale copy of the settings.** The
  Settings screen builds its fields from its own `AppSettings.load()` at the
  time it is built. Dragging the Plan divider writes
  `plan_items_col_width`; if a Settings screen was already open, its Save
  writes the width it loaded back over the dragged one. This is every field on
  that handler, not just this one, and it predates the grip — the grip only
  made it reachable without typing. Low: the two screens are rarely open at
  once, and the fix is a reload on screen-show, which touches every field at
  once and so belongs in its own change.

## 🐛 Known Bugs

- [x] Today listing shows all completed items (should only show today's).
  **Not reproducible 2026-08-19 (BC1)** — already fixed in both the SQL and the
  Python search path, which restrict completed items to
  `DATE(completed_at) = today`. Verified against a real database, then pinned by
  `tests/test_today_completed_filter.py` so the entry cannot come back untested.
- [x] Item editor: `save_and_close` / `save_and_new` / `duplicate_item` inferred save success from the error-label text, so they closed/proceeded even on a validation error. Fixed 2026-07-26 — all three now gate on the `save_item()` bool, with tests.
- [x] Item editor: the ⏱ Timer button stayed enabled if the timer completed the item, allowing a re-open on a done item. Fixed 2026-07-26 — `_on_timer_closed` disables the button once the reloaded item is completed (guard also added in `start_timer`).
- [x] Item editor + timer non-modal reload could clobber edits: editing the editor's Description/Next Action *while* the timer is open was overwritten by the on-close reload. Fixed 2026-07-26 — `start_timer` snapshots the editable fields and the on-close reload only refreshes fields the user left untouched (their in-flight edit wins); untouched fields still pick up the timer's DB changes.

## 🎯 Feature Requests

### Obsidian Integration (In Progress)

- [x] Phase 1: Basic note linking (DONE)
- [x] Add notes section to Action Items (DONE)
- [x] Create note dialog (DONE)
- [x] Link existing note dialog (DONE)
- [ ] Phase 2: Add notes section to Contacts
- [ ] Phase 3: Bulk note operations
- [ ] Phase 4: Note templates

### Future Features

- [ ] Dark mode support
- [ ] Export tasks to CSV/Excel
- [ ] Recurring tasks
- [ ] Task dependencies
- [ ] Calendar view for time blocks
- [ ] Keyboard shortcuts (Ctrl+N for new task, etc.)
- [ ] Search across all notes
- [ ] Bulk operations (complete multiple tasks at once)
- [ ] Task templates
- [ ] Weekly/monthly reports

## ✨ Enhancements

- [ ] Add tooltips to all buttons
- [ ] Improve error messages (more user-friendly)
- [ ] Add confirmation dialogs for delete operations
- [ ] Better date picker widget
- [ ] Auto-save drafts when editing
- [ ] Undo/redo support
- [ ] Obsidian "Create Note" export writes `Prev`/`Next`/`tags` as empty (bare `key:`), which renders as List/Tags only in a vault where those property types are already registered. In a brand-new vault an empty property defaults to Text until its type is set once. If needed, emit `[]` to force List typing everywhere (trade-off: diverges from Obsidian's own empty-list serialization). Noted 2026-08-06.

## 🔧 Technical Debt

- [ ] Item editor timer merge: a whitespace-only edit to a notes field while the timer is open is treated as "untouched" (the merge compares stripped values) and gets reloaded from the DB. Cosmetic — `save_item` strips anyway, so no substantive data is lost. Known, deliberate property (2026-07-26 learning-qa sweep).
- [ ] Add GUI automation tests (PyAutoGUI)
- [ ] Refactor item_editor.py (currently 1800+ lines)
- [ ] Add type hints to all functions
- [ ] Add docstrings to all public methods
- [ ] Performance testing with 10,000+ tasks
- [ ] Database migration system
- [ ] Logging framework

## 📖 User Stories

### Epic: Advanced Planning

- [ ] US: As a user, I want to see weekly task overview in calendar view
- [ ] US: As a user, I want to track task dependencies (task A blocks task B)
- [ ] US: As a user, I want to see task timeline/Gantt chart
- [ ] US: As a user, I want to estimate vs actual time reports

### Epic: Collaboration

- [ ] US: As a user, I want to share tasks with team members
- [ ] US: As a user, I want to assign tasks to others
- [ ] US: As a user, I want to sync across devices

### Epic: Integrations

- [x] US: As a user, I want to link Obsidian notes to tasks (DONE)
- [ ] US: As a user, I want to import tasks from Todoist
- [ ] US: As a user, I want to sync with Google Calendar
- [ ] US: As a user, I want to create tasks from email

## 📝 Notes

### Testing Strategy

- Backend tests: pytest (21 tests passing)
- GUI tests: Manual + PyAutoGUI (to be added)
- User should test all GUI buttons after each change

### Virtual Environment Issue

- Need to activate venv each session: `source venv/bin/activate`
- Consider adding to shell startup or creating alias

### Obsidian Integration Status

- Phase 1 complete and tested
- All 21 integration tests passing
- User needs to manually verify GUI dialogs work correctly

---

## Quick Add Template

```markdown
### [Date] - [Type: Bug/Feature/Enhancement]

**Title:**
**Description:**
**Priority:** [Low/Medium/High/Critical]
**Effort:** [Small/Medium/Large]
**Notes:**
```
