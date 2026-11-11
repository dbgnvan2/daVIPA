# daVIPA Documentation Index

## Overview

Complete index of all documentation files for the daVIPA task management application.

## Primary Documentation

### `codex.md`

Repository maintainability policy used during code review and refactoring:

- File responsibility and cohesion rules
- Refactor triggers and decision heuristics
- Testability and dependency-load guidance
- Default expectations for ongoing development work

### `docs/unused-docs/changes/`

Agent handoff notes and implementation summaries:

- One note per substantial agent change
- Verification commands and outcomes
- Risks / known gaps
- Follow-up guidance for subsequent agents

Notes are not listed here individually (PLC-A5 covers that gap), with two
exceptions worth finding without reading the directory:

- [`2026-11-08-one-batch-at-a-time.md`](changes/2026-11-08-one-batch-at-a-time.md)
  records the end of concurrent batches, the state `main` was left in, and the
  two unmerged branches.
- [`2026-11-11-manual-walk-four-batches.md`](changes/2026-11-11-manual-walk-four-batches.md)
  is one pass through the app covering what four batches left unverified on
  screen — LRR, SCV, CE/AWA and PF — in walk order rather than batch order. It
  is the only note that belongs to no single batch: sections A and B
  consolidate the two per-batch checklists, which stay the reference for a
  failure, and sections C, D and E are the two batches that had none.

### README.md (27KB)

Main project documentation including:

- Features overview
- Quick start guide
- Installation instructions
- Recent improvements (VPS, Timer, Contacts, etc.)
- **NEW: Testing section** with test commands and coverage

### docs/USER_GUIDE.md

Current end-user documentation including:

- Screen-by-screen walkthrough
- What/why for buttons and controls
- Item Editor, Timer, Calendar, and Settings details
- Scheduler usage, calendar tab, date filters, and future targets
- Project Board usage, note controls, and linked action-item workflow
- Vision Strategy Plan hub, Annual Plan Elements, and APE assignment flow
- List View terminology and current responsive-column behavior

### GetMoreDone_MasterSpec_SQLite_v1.md (19KB)

Complete specification including:

- System architecture
- Database schema
- Feature requirements
- Design decisions
- Business logic

### NOTES.md (2.3KB)

Recent changes log:

- VPS Segment Management (2026-01-24)
- VPS Bug Fixes (2026-01-24)
- Item Editor improvements (2026-01-23)
- Timer window improvements (2026-01-23)

### BACKLOG.md (4.1KB)

Feature backlog and task tracking:

- Completed features with dates
- Pending enhancements
- Known issues

### docs/ui_color_inventory.md (generated)

Every colour literal in `src/`, `themes/` and `tools/generate_ctk_themes.py`
-- the UI code, the themes it loads, and the tool that writes them -- with the
file and line of each occurrence and frequency tables for the hex and named
colours. Gray-scale literals (`gray95`) are included. It is an audit of UI code, not a repository-wide
census: that scope was decided as CIV-A1 on 2026-11-11 and is recorded in
`docs/unused-docs/changes/2026-11-11-colour-inventory-scope.md`. **Generated
-- never hand-edit it** (global rule 2: fix the code, don't fake the state).
Regenerate with:

```bash
./venv/bin/python tools/color_audit.py
```

`tests/test_color_inventory_sync.py` regenerates the report during the suite
and fails while the committed file differs from a fresh run, so any change
that adds or removes a colour literal needs the regenerated file committed
with it. That scan reads the **working tree, not `HEAD`**, so regenerate only
once the tree holds what you mean to commit. The generator shells out to
ripgrep, which `.github/workflows/tests.yml` installs for CI and which a
local run needs on `PATH`.

### The multi-agent workflow document and the PR template (deleted 2026-11-09)

Both had entries here. The workflow document described the three-agent branch
model — role definitions, a worktree bootstrap, a PR step — which `CLAUDE.md`
and `AGENTS.md` had recorded as retired since 2026-11-08; the template served
that PR step, and this repo opens no pull requests. Deleted by the MAW batch
along with the bootstrap script and the three role prompts (`GSF-A1`,
`GSF-A2`, and the 2026-08-20 filing that first named the surface). The two
rules worth keeping were already in `CLAUDE.md` and `AGENTS.md` in full:
**docs sync** (*Working agreements* / *Docs sync*) and the **required handoff
note** with its template at `.agents/templates/handoff-note.md`.

## VSP (Vision Strategy Plan) Documentation

### docs/unused-docs/VPS_UPDATES_2026-01-24.md (8.5KB) **NEW**

Comprehensive change log for January 24, 2026 updates:

- Critical bug fixes (CTkMessageBox, year validation, multi-select)
- New segment management features
- Enhanced deletion protection
- Complete testing breakdown
- Migration notes
- Verification checklist

### docs/VPS_TESTING_SUMMARY.md (5.1KB) **NEW**

Test documentation for VPS:

- 21 total tests (14 integration + 7 standalone)
- Test coverage breakdown
- Test results summary (100% pass rate)
- Commands to run tests
- Code coverage metrics
- Future testing considerations

### docs/DOCUMENTATION_UPDATE_SUMMARY.md (5.1KB) **NEW**

Summary of documentation and test updates:

- Documentation files updated
- Test updates and fixes
- Verification checklist
- Complete test results

### docs/spec_2026-11-07_ape_period_consistency.md

Spec and implementation plan for APE quarter/month consistency (APC-M1 - APC-M6):

- Why an APE filed under Q3 and M11 at once was invisible in APE Weekly
- One quarter<->month mapping in `date_utils`, replacing three copies
- The manager guard that refuses a pair which cannot both be true
- APE Month pickers that cannot produce such a pair
- The month-only lookup both APE screens now use
- The idempotent migration that repairs stored orphan month flags

### docs/spec_2026-11-07_ape_week_actions.md

Spec and implementation plan for the APE Week Assignment rename and a new
APE Week Actions tab (AWA-M1 - AWA-M6). Approved and built 2026-11-07; §6 is
the per-criterion status report, and the one criterion that needs a human at
the screen is still open there:

- Why "linked to the week tactic" means two different columns in live data
- The one predicate that reads both, and the counts behind that decision
- The seam cut into `today.py` so the right panel can subclass it
- The six decisions taken where the request admitted more than one reading
- Five adjacent issues found; one fixed because it blocked verification, four
  recorded in `BACKLOG.md`
- §6: the status table, the 28-mutation table, and the nine-step on-screen
  checklist that criterion is waiting on

### docs/spec_2026-11-07_unified_panel_design.md

Spec and implementation plan for one panel design across the VSP tabs
(UPD-M1 - UPD-M7). **Approved 2026-11-07. UPD-M3, UPD-M1, UPD-M2, UPD-M4,
UPD-M5 and UPD-M6 built; UPD-M7.1 done, UPD-M7.2 `partial` and UPD-M7.3 `not
done`.** §11 was walked on 2026-11-08 and produced four follow-ups,
`UPD-F1` - `UPD-F4`, in the plan below; all four are built and the §11 walk is
owed again, steps 4, 7 and the new 11 to 13 included (per-criterion status in
the spec's §10, and the batch's handoff note is
`docs/unused-docs/changes/2026-11-08-unified-panel-m7.md`):

- The feature matrix: which of the six tabs has panels, a divider, drag and
  resizable columns today, counted rather than assumed
- Why the splitter, the row drag and the chip table are each written out four
  or five times, and the three modules that replace them
- Why draggable column widths are the only genuinely new part of the request
- The two places "the same design" cannot be taken literally, and what is done
  instead
- How it sequences against the unpushed APE Week Actions batch
- §11: the on-screen checklist UPD-M7.2 and UPD-M7.3 are waiting on, written
  for the user to walk in the running app rather than for a test -- ten steps
  as walked on 2026-11-08, with steps 4 and 7 rewritten and steps 11 to 13
  added for what UPD-F2, UPD-F3 and UPD-F4 changed

### docs/unused-docs/implementation_plan_2026-11-08_unified_panel_followups.md

Spec and implementation plan for what the unified panel design's on-screen
check found (UPD-F1 - UPD-F4). **Approved 2026-11-08. UPD-F2, UPD-F3 and
UPD-F4 built the same day, and UPD-F1 built after them and merged at
`2fac9b3`** -- it was the only defect of the four and the only one that had to
change `src/getmoredone/app_settings.py`, which a concurrent batch held
uncommitted at the time, so it went to its own session (per-criterion
status in `docs/spec_coverage.md`, and the batch's handoff note is
`docs/unused-docs/changes/2026-11-08-unified-panel-followups.md`):

- UPD-F1, the one defect found at the walk: no column width or divider
  position survived a relaunch, because `AppSettings.save()` wrote the whole
  object and a screen holding its own snapshot reverted what another screen
  wrote. **Built afterwards in its own session (`31816a0`) and merged at
  `2fac9b3`**; the walk's step 10 is owed a re-walk, not a fix
- UPD-F2: the filter area is three lines deep on every tab -- the three combos
  on a row of their own, and a blank row of the same depth on the one tab that
  has no filters
- UPD-F3: Week Assignment's checkbox column is headed "Pick", which reverses
  the text half of UPD-M5.5
- UPD-F4: the columns rescale with the divider, down to five characters, with
  a stored width read as a weight rather than a pixel promise
- The four corrections made to the plan against the code after it was
  approved, each with its measurement
- §6: the three criteria that cannot be made code-testable, now §11 steps 11,
  12 and 13 of the unified panel spec

### docs/unused-docs/implementation_plan_2026-11-08_priority_level_colours.md

Implementation plan for configurable priority level colours (PLC-M1 - PLC-M5).
**Approved 2026-11-08 and built the same day**; per-criterion status in
`docs/unused-docs/spec_coverage_2026-11-08_priority_level_colours.md`, and the batch's
handoff note is `docs/unused-docs/changes/2026-11-08-priority-level-colours.md`:

- The three levels — Any Critical; Any High, but no Critical; No high or
  critical — and that a level is a rule on Importance and Urgency, not a
  threshold on the priority score
- Why priority *levels* and priority *bands* are kept as two name sets, and the
  case where the two answers come apart
- The five screens that each wrote the rule out by hand, with the line numbers
  they wrote it on
- Why one colour per level and not one per theme, and what that costs
- Why the control is a new tab rather than a third section on Appearance
- Five adjacent issues found and not fixed, filed in `BACKLOG.md`

### docs/spec_2026-11-08_calendar_into_the_plan.md

Spec for the other direction: reading the connected calendars, showing their
commitments on the Plan grid so a day is planned around what is already gone,
and editing those commitments in place (CIP-M0 - CIP-M7). **Draft, not
approved, no code written, on the backlog.** Phase 1 is the selected day;
phase 2 is a seven-day planning view over the same cache. Holds the decision
that a commitment is *not* a `time_blocks` row and the five reasons, the rule
that keeps the export's own events from returning as constraints on the blocks
that made them, why `calendar_importer.py` stays alongside it (an action item
is *what*, a commitment is *when*), and the four scope decisions taken
2026-11-08.

### docs/unused-docs/implementation_plan_2026-11-08_plan_calendar_export.md

Implementation plan for exporting a planned day to Google Calendar
(CE-M1 - CE-M5). **Approved 2026-11-08 and built the same day**;
per-criterion status, the verification runs, eighteen deviations from this
plan's wording and the four cold review passes' thirty-eight findings are in
`docs/unused-docs/spec_coverage_2026-11-08_plan_calendar_export.md`, and the batch's
handoff note is `docs/unused-docs/changes/2026-11-08-plan-calendar-export.md`:

- What the Plan screen's "⤴ Google Calendar" button exports, and the three
  named, counted reasons a block is skipped rather than guessed at
- The two halves of idempotency — an event id on the block and the block's id
  in the event's private properties — and why a tombstone table was not needed
- Why an event without daVIPA's marker is never updated or deleted, whatever
  its title or time
- Hardening the Google layer as a class: timeouts, retry on 429/5xx only, and
  404/410 as "the event is gone" rather than as a failure
- Why the worker thread hands its result back by polling instead of calling
  `after()` — Tk is not thread-safe and `after` is not an exception
- Why a day with no blocks left still runs the export: refusing first made the
  orphan sweep unreachable for the one day that needs it
- Why a background export cannot be allowed to sign in: the consent flow opens
  a browser and then waits on a console, so the client the worker builds raises
  `AuthenticationRequired` instead
- Why every exported time is derived from the block's box and not read from its
  stored clock columns, which are a record of bounds that may have moved
- Why a block's event id records the calendar it is on, and what changing the
  export calendar does to events already there
- Why one export per day is enforced outside the screen: navigating away and
  back builds a new one
- Four adjacent issues found while building, plus seventeen below-medium findings
  from the three cold review passes — none fixed in the batch, all filed in
  `BACKLOG.md` as CE-A1 to CE-A21
- The manual checklist, which is the part no test can cover

### docs/unused-docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md

Implementation plan for the lowest-value priority floor on new items and the
9999 cap on the calculated score (PRI-M1 - PRI-M3). **PRI-M1 and PRI-M2 are
built and on `main` (`9420927`); PRI-M3 is not built.** This entry said
"awaiting approval; no implementation code written" until 2026-11-08, which is
the other half of `SSC-1`. The criteria shipped with no tests at all; those are
being written against this plan in
`docs/unused-docs/implementation_plan_2026-11-08_pri_tests.md`:

- Why a new item is unscored today rather than lowest, and what that costs it
  in every `priority_score DESC` list
- The counted cost of capping the stored score: 33 of 256 factor combinations
  collapse onto one flat top tier, and the display-only alternative
- The three copies of the product arithmetic, and the one function that
  replaces them
- Why the floor is a create-time rule that never back-fills an existing row
- The column-width criterion written as a font measurement rather than as a
  number in prose
- Four adjacent issues found and not fixed. **Filed as PRI-A1 to PRI-A4 on
  2026-11-08** by the SST batch, which closed the rest of `SSC-1`; two of the
  four descriptions were wrong and are corrected in the filings rather than
  copied

### docs/unused-docs/implementation_plan_2026-11-08_pri_tests.md

Implementation plan for the tests PRI-M1 and PRI-M2 shipped without
(`BACKLOG.md` item 2, and the spec-status half of `SSC-1`). **Proceeding
without a separate approval round, on the user's standing instruction for this
stretch**, which the plan records rather than assumes:

- What is actually on `main`, measured before planning: PRI-M1 and PRI-M2
  built, PRI-M3 not built, and not one of the spec's named test files present
- Why PRI-M3 is filed rather than built here - a shared width constant threaded
  through five list screens is a feature change against the aligned-column
  contract, not a test gap
- The spec's own criterion IDs used verbatim, each against the spec's own test
  name, with the shape of each test and why that shape
- The two tests whose subject is source text rather than behaviour (PRI-M2.5's
  AST walk, PRI-M2.7's comment), and the exact-count rule they are written to
- Why the widget tests add no mapped window: `conftest.py` already silences
  `grab_set` and withdraws every window on creation

**Built 2026-11-08: all 15 criteria `done`** - 14 by test, PRI-M2.7 by an
existing test whose comment was corrected - per-criterion status in
`docs/spec_coverage.md`. 35 tests, mutation-proved against eight mutations.
Handoff note: `docs/unused-docs/changes/2026-11-08-pri-tests.md`, listed here only inside
this entry rather than as an entry of its own, as every handoff note is. The
plan says "fourteen tests"; 35 is the collected count, the parametrized rows
counted individually.

### docs/unused-docs/implementation_plan_2026-11-08_plan_day_tests_follow_pd_m14.md

Implementation plan for bringing nine stale plan-day tests up to the PD-M14
design (PDT-M1 - PDT-M5). **Approved 2026-11-08 and built the same day: 20 of
21 criteria `done` - 12 by test, 8 by review, PDT-M4.2 `not done` with its
reason. PDT-M4.2 was closed later the same day by the PRIT batch, which wrote
the two missing test files, so all 21 now read `done` - 13 by test, 8 by
review** - per-criterion status in `docs/spec_coverage.md`. Handoff note:
`docs/unused-docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md`, which is listed
here only inside this entry rather than as an entry of its own, as every
handoff note is:

- Why the brief it was written against - port `outside` from
  `refs/heads/claude/plan-day-range-pdm13` - had nothing to port: `outside` is
  implemented on `main` at both the layout layer and the screen, and a screen
  test using the "never placed" vehicle passed throughout
- The two public-name lists that show which side is the later design, and the
  shared-setting write on the branch that caused both reported faults
- The one cause behind six of the nine failures: PD-M14.2 derives the drawn day
  from the date's own blocks, so a tighter Day End can no longer orphan one
- The four routes to `outside` that still exist, each already green in
  `tests/test_time_grid.py`, and which one each rewrite uses
- `test_pdm131` and `test_pdm141` asserting opposite things about one call on
  one branch, and why `test_pdm131` is rewritten rather than deleted
- PDT-M1.3 flagged in advance as the one criterion that might need `src/` work,
  because it had never run against the holder it names; it did not
- Two criteria flagged by the plan as not code-testable (PDT-N1, PDT-N2); seven
of the 21 rows in `docs/spec_coverage.md` carry that marker, the other five
being the PDT-M5 document criteria with a
  human-review proposal for each
- Nine CI-environment failures listed as adjacent and not touched

### docs/unused-docs/implementation_plan_2026-11-10_list_row_rendering.md

Implementation plan for the five list screens' row rendering (LRR-M1 - LRR-M2),
closing `BACKLOG.md`'s `PRI-A1` and `PLC-A1`, both medium and both filed
2026-11-08. **Approved 2026-11-10 and built the same day: 5 of 5 criteria
`done`, one item not code-testable (how the change looks on the user's own
segment colours, reported as a manual checklist)** - per-criterion status in
`docs/spec_coverage.md`. Touches `src/getmoredone/priority_levels.py` and the
five screens. Handoff note:
`docs/unused-docs/changes/2026-11-11-lrr-manual-checklist.md`, which is listed
here only inside this entry rather than as an entry of its own, as every
handoff note is — it carries the ten-item on-screen checklist and the measured
contrast figures to check it against, this being a UI change no session can
verify:

- Both defects are one shape - a rule written out by hand in `today.py`,
  `upcoming.py`, `all_items.py`, `hierarchical.py` and `completed.py` where an
  authority for it already existed, and five copies that had drifted from it
- `priority_level_for_item` replaces `item.importance == 20 or item.urgency ==
  20` for the red `P:` chip. The authority compares against `PriorityFactors`
  with `>=` and an `int()` coercion, so it catches an importance of `25` and
  one stored as the string `"20"`, which the literal read as not critical -
  the dangerous direction to be wrong in
- The guard is an AST walk over all of `screens/`, not the five files that had
  the defect, at an exact count of zero. It found exactly the ten comparisons
  the plan named and nothing else in 58 modules
- `row_fill` now derives a segment fill's text colour with `pick_text_color`,
  so a pale VSP segment colour no longer draws the dark theme's near-white row
  text. The completed tint deliberately keeps the theme's, `success_tint`
  being a token paired in the theme with that same theme's `row_text`
- A segment colour Tk accepts but `normalize_hex_color` cannot read falls back
  to the theme's text rather than to `pick_text_color`'s black, which on an
  unknown background can be worse than what it replaced
- `PLC-A3` is left filed, its colour half still open: the chip's `danger` is a
  product decision about what critical looks like, not a copy to sweep
- One cold pass found three mediums, all fixed, and the first of them
  falsified the batch's own guard: the I and U **factor** chips asked
  `str(value).strip() == "20"` over a tuple-bound factor in four screens, a
  form the AST walk could not see while being named for banning it. The walk
  now has a second half that asks the blunter question. `row_control_kwargs`
  was gating on `source == SOURCE_LEVEL`, a proxy for "this fill brought a
  text colour" that LRR-M2.1 made false, so a segment row's text moved and
  its checkbox did not
- One medium was pre-existing and is filed as `LRR-A1` rather than swept:
  `vps_segment_editor.validate_color` accepts `#0X1234`, which reaches Tk and
  raises mid-refresh. Three below-medium findings were dropped per the sweep
  budget; one of them, a silent fallback, was taken because it shared an edit

### docs/unused-docs/implementation_plan_2026-11-11_segment_colour_validation.md

Implementation plan for one authority for a segment colour (SCV-M1 - SCV-M4),
closing `BACKLOG.md`'s `LRR-A1`, medium, filed 2026-11-10 by the LRR batch's
cold pass. **Approved 2026-11-11 and built the same day: 7 of 7 criteria
`done`, plus SCV-M5 from a cold pass over the plan and SCV-M6 from the cold
pass over the code, and SCV-M7 from a second cold pass on test quality and the
UI contract; one item not code-testable (what the editor and the VSP screens
do on screen, reported as a five-step manual checklist)** -
per-criterion status in `docs/spec_coverage.md`. Touches
`src/getmoredone/color_contrast.py`, `vps_manager.py`,
`vps_manager_taxonomy.py`, `priority_levels.py`, `theme.py` and
`screens/vps_segment_editor.py`, `screens/segment_color_utils.py`,
`screens/vision_segments.py`, `screens/settings_vsp_segments.py`:

- `LRR-A1` named one hand-rolled hex validator and there were two. The second,
  `VPSManager._is_valid_hex_color`, is the gate on the colour-repair pass
  inside `get_vision_subsegments` and `get_vision_categories`, so that pass
  skipped exactly the rows it exists to fix
- The consequence the filing did not name, measured at `6963d0a`:
  `_derive_subsegment_color('#0X1234')` raised an uncaught `ValueError` in a
  VPS read path, independent of Tk, and `'#+12345'` raised nothing and derived
  `#0B368D` from a misread slice
- `color_contrast.hex_to_rgb` is now the one place in the segment-colour path
  that slices a colour into `int(..., 16)`, counted by an AST walk with exact
  per-module counts
- Delegating widens the segment editor to accept `#abc`, taken deliberately
  and only together with storing the normalised `#AABBCC`
- Three adjacent issues stay filed rather than swept, as `SCV-A1`, `SCV-A2`
  and `SCV-A3`. The plan's §5 recorded the third as "correct already"; it is
  not, and the filing says so
- A cold pass over the plan by another session added `SCV-M5`, a medium: the
  segment table was gated only in the dialog, so the VSP segment admin screen
  could still store `#0X1234` into the one table `row_fill` draws from
- The required cold pass over the code added `SCV-M6`, seven findings with two
  highs. `row_fill` was not the last gate before `ctk.CTkFrame(fg_color=…)`,
  as its own docstring claimed: `theme.apply_segment_accent` is called on the
  next line of all five row builders with the same raw value, and three more
  sites took one too. The segment editor's raise was in `__init__`, not in the
  loader
- A second cold pass, on test quality and the UI contract, added `SCV-M7`:
  one high, three mediums, two lows, all fixed. SCV-M6 made every colour
  dialog openable and left both screens that *list* a segment raising before
  the Edit button that opens them was created, so the remediation path did not
  work. It also found two of this batch's own tests passing for the wrong
  reason, one of which passed with the code it tests reverted

Handoff note: `docs/unused-docs/changes/2026-11-11-scv-manual-checklist.md`,
which is listed here only inside this entry rather than as an entry of its own,
as every handoff note is — it carries the five-step on-screen checklist and the
measurement of the `TclError` claim this batch set out not to re-measure.

### docs/unused-docs/implementation_plan_2026-11-11_vsp_tab_filters.md

Implementation plan for the six VSP Planning tabs' left-to-right filter and the
bottom Add New (VTF-M1 - VTF-M7), from a user report of 2026-11-11. **Draft,
approved by nobody; no code written. The four design decisions are settled.** Touches the five dual-panel tab modules
and `vision_segments.py`:

- The report's first part is **not a regression**: in the whole history of the
  four assignment tabs `left_checks` is read only by `add_selected`, the Save
  button, and no checkbox in any version carried a `command=` or a
  `trace_add`. The tick has always been the assignment selector, so the
  filtering asked for was never built
- Left-to-right filtering works on APE Week Actions only, by row click
- `annual_vision_segments.py:81-84` says the Annual Plan Elements tab has no
  lineage to filter by. Every right-hand row carries `vision_element_id` and
  the three lineage names, so both the tick filter and the dropdowns the other
  tabs have are available from data already in hand
- The tick cannot be both filter and assignment selector; the user chose the
  tick as filter and a bottom Add New as the only way to add. VTF-M4 therefore
  removes four screens' Save buttons, which the plan records as an explicit
  UI-contract approval
- D2 settles which filter belongs to which panel, and reverses what this
  plan's first draft proposed: the Segment / SubSegment / Category dropdowns
  filter the **left** panel, and the **right** panel is filtered by what is
  ticked on the left. Today the dropdowns filter both, so VTF-M2 takes them off
  the right panel. APE Week Actions already obeys the rule
- D1 keeps the Vision Elements tab's structure and moves its three New buttons
  to the bottom; D3 keeps the tick filter on the Quarter and Month tabs, where
  both panels list the same record type; D4 keeps drag-and-drop

### docs/unused-docs/implementation_plan_2026-11-09_ci_green.md

Implementation plan for the nine tests CI has been red on since 2026-11-07
(CIG-M1 - CIG-M4). **Approved 2026-11-09 and built the same day: 10 of 10
criteria `done`, one item not code-testable (CIG-N1, that CI is green, closed
by a run id and nothing else)** - per-criterion status in
`docs/spec_coverage.md`. No file under `src/` is touched. Handoff note:
`docs/unused-docs/changes/2026-11-09-ci-green.md`, which is listed here only inside this
entry rather than as an entry of its own, as every handoff note is:

- Seven of the nine set a window attribute and read it back, which needs a
  window manager; CI runs under `xvfb-run -a`, which has none. One shared
  precondition, `tests/display_capabilities.py`, replaces six absent ones and
  one private copy - the private copy being why six stayed red after `23f0cc7`
  fixed the seventh
- One cold pass over the plan and the batch found six defects, two of which
  falsified the plan's own premise: Xvfb **does** report `-alpha` back for a
  window that has been mapped, which two sibling tests prove on CI, so the
  probe asks the narrower question about a *withdrawn* window; and skipping the
  two `-alpha` tests does cost coverage, because one of them is the only test
  that drives a raw `tk.Tk` through the window-hiding guard. Both corrections
  are in the plan with the measurement, not dropped
- `test_updm14_zero_width_body_is_a_noop`'s cause is still unknown and is filed
  as `CIG-A8`. Two comments asserting a cause were written and withdrawn after
  measurement; the test now forces the one number the code reads, which needs
  no diagnosis
- PB-M6.1's row test was asserting a floor that the broken layout satisfied -
  measured, not inferred - and was describing two lines of text that PD-M1 had
  already reduced to one. Rewritten and renamed, repo test rule (b) and (c)
- `WTP-A11`, `BACKLOG.md` item 3 and item 5 closed; `CIG-A1` - `CIG-A9` filed,
  not fixed. `CIG-A1` is the one that matters: the new guard is a registry of
  eight known callers, so it cannot detect a *new* test written the way these
  seven were

### docs/unused-docs/implementation_plan_2026-11-09_bare_name_citations.md

Implementation plan for bringing the bare `::name` citation form into the
traceability guard (SBN-M1 - SBN-M2), closing `BACKLOG.md`'s `SAG-A17`
(medium). **Approved under the standing instruction 2026-11-09 and built the
same day: 6 of 6 criteria `done`, one item not code-testable (SBN-N1, that a
resolving bare name is the right test for its row)** - per-criterion status in
`docs/spec_coverage.md`. No file under `src/` or `tools/` is touched. Handoff
note: `docs/unused-docs/changes/2026-11-09-bare-name-citations.md`, which is listed here
only inside this entry rather than as an entry of its own, as every handoff
note is:

- A citation written as a bare continuation was matched by nothing, so about a
  third of this repo's test citations were unchecked: 68 dead occurrences, 59
  distinct names, in 14 documents, 52 of them reading as live evidence. All 68
  are repaired - a renamed test re-cited by its real name, a retired one named
  with neither the path nor the `::`.
- `SAG-A17`'s own recommended fix was measured and **rejected**: anchoring a
  bare name to the nearest preceding path citation puts the anchor on the wrong
  file 356 times against 52 genuinely dead names.
- `_FULL`, a masking regex, was deleted after a mutation came back green proved
  it changed no outcome anywhere in the repo.
- Repairing the documents exposed ten criteria whose tests were never written,
  and PD-M14.4 and PD-M14.7 have no test under any name: `SBN-A3`.
- Nine mutations, two green and both recorded. One cold pass, in the family the
  plan named as its own risk - no high and eight mediums, all fixed, two of
  them in the guard's own prose. `SBN-A1` to `SBN-A7` filed, not fixed.

### docs/unused-docs/implementation_plan_2026-11-09_derived_live_document_set.md

Implementation plan for deriving the scanned document set and guarding the
vocabulary of retired concepts (LDS-M1, LDS-M3, LDS-M4), closing `BACKLOG.md`'s
`GSF-A3` (medium), `GSF-A4` (low) and `MAW-A3` (medium), and settling `GSF-N1`
as a writing convention rather than a rename. **Built 2026-11-09 under the
standing instruction: 8 of 8 criteria `done`, one item not code-testable
(LDS-N1, whether the prompt documents and dated records deserve a weaker
guard)** - per-criterion status in `docs/spec_coverage.md`. No file under
`src/` is touched. Handoff note:
`docs/unused-docs/changes/2026-11-09-derived-live-document-set.md`, listed here only inside
this entry rather than as an entry of its own, as every handoff note is:

- The `docs/` half of the scanned set was five names kept by hand. It is
  derived now, by one stated path rule - tracked, one level down, `*.md`, no
  ISO date in the name, no "prompt" in the name - which widens the scan from
  17 documents to 41 (the figure the MAW records give, which counts the
  handoff-note template `_live_documents` adds to the two listed halves).
- The dated records and the four prompt documents stay out, with the
  measurement for why: scanned as well, they report 13 unresolvable citations,
  11 of which were true when they were written. A guard that makes honest
  history unwritable is the defect, not the fix.
- Widening the scan found three repairs: a TOOL.md that has never been in this
  repo, cited from `docs/AGENT_UI_REGRESSION_POLICY.md` since before the
  rename (`GSF-A4`); a fixture filename quoted in `docs/spec_coverage.md`, now
  exempt with its reason; and a proposed-but-unmade rename written in
  backticks, which the conventions now cover as a named form.
- `tools/agents/retired_vocabulary.json` is new: the vocabulary of concepts
  this repo has retired, in config rather than in Python (global rule 9), with
  a date, a reason and a "write it instead" line per concept. A phrase is a
  finding only when the *sentence* holding it carries none of the retirement
  markers, so history stays writable - the mechanism `MAW-A3` asked for after
  `docs/GEMINI.md` described the three-agent split as current for two batches
  inside the scanned set.

### docs/unused-docs/implementation_plan_2026-11-09_retired_agent_apparatus.md

Implementation plan for deleting the retired three-agent workflow's apparatus
(MAW-M1 - MAW-M4), closing `BACKLOG.md`'s `GSF-A1` (medium), `GSF-A2` (low)
and the 2026-08-20 filing of the same surface. **Approved under the standing
instruction 2026-11-09 and built the same day: 5 of 5 criteria `done`, one item
not code-testable (MAW-N1, whether the remote `codex/agent-code` should be
deleted)** - per-criterion status in `docs/spec_coverage.md`. No file under
`src/` is touched. Handoff note:
`docs/unused-docs/changes/2026-11-09-retired-agent-apparatus.md`, which is listed here only
inside this entry rather than as an entry of its own, as every handoff note is:

- Six files deleted: the workflow document, the worktree bootstrap script that
  created `codex/agent-{code,docs,github}` plus a worktree on each, the three
  role prompts, and the pull request template. `CLAUDE.md` and `AGENTS.md` had
  recorded the workflow as retired since 2026-11-08 while all of it stayed
  executable.
- The document was deleted rather than rewritten: of its 70 lines, 35 described
  the retired workflow and 35 were a third copy of rules `CLAUDE.md` and
  `AGENTS.md` each carry in full. The one list only it held had drifted
  unnoticed until the GSF batch repaired it hours earlier.
- `AGENTS.md` still permitted two concurrent builds in two worktrees, which
  `CLAUDE.md` withdrew on 2026-11-08. Corrected, and MAW-M4.1 holds the
  agreement.
- Eleven mutations, five green in the first round and all eleven discriminating
  after the fixes they forced.
- One cold pass - three highs and three mediums, all fixed. The `docs/`-path
  guard had been written with the backticked form alone, so it would not have
  read this index's own `###` entries; the branch distance every document gave
  as "131 commits" measured 624 and an ancestor of `main`; and the handoff note
  claimed two records that did not yet exist.

### docs/unused-docs/implementation_plan_2026-11-09_dead_gate_and_dead_spec_name.md

Implementation plan for deleting the pull-request-only docs gate and repairing
the master-spec filename that does not exist (GSF-M1 - GSF-M2), closing
`BACKLOG.md`'s `SAG-A3` and `SAG-A7` (both low). **Approved under the standing
instruction 2026-11-09 and built the same day: 5 of 5 criteria `done`, one item
not code-testable (GSF-N1, whether the spec file should instead be renamed to
the app's name)** - per-criterion status in `docs/spec_coverage.md`. No file
under `src/` or `tools/` is touched. Handoff note:
`docs/unused-docs/changes/2026-11-09-dead-gate-and-dead-spec-name.md`, which is listed here
only inside this entry rather than as an entry of its own, as every handoff
note is:

- `agent-docs-gate.yml` triggered on `pull_request` only, which this repo never
  opens, so the gate had never run here. It is deleted; the rule it carried has
  been in the suite since `SAG-M2`. Four live documents described it as an
  enforcement a reader gets and are corrected.
- Eleven citations in seven documents named daVIPA_MasterSpec_SQLite_v1.md,
  written here without backticks because it has never existed - including the key-files table in `CLAUDE.md` and,
  in this index, a `###` entry heading, so the index had an entry for a file the
  repo has never contained. All eleven name the file that is there.
- Two guards hold the class now, each proved against a fixture the test writes
  rather than against today's prose, because a repo-state assertion cannot fail
  once the repo is clean.
- Nine mutations, three green and all three recorded; two of the three were one
  finding, a redundant path filter beside a path-blind regex where neither
  mechanism was observable alone, and the redundant one is deleted.
- One cold pass - no high, four mediums, all fixed. It measured seven of the
  ten documents in the originally hand-kept scanned set as deletable with both
  guards still green, and two documents this batch repaired as never in the set
  at all; the root half is derived from `git ls-files` now (GSF-M1.3). It also
  caught this batch citing a handoff note that did not yet exist.
- `GSF-A1` to `GSF-A5` filed, not fixed. `GSF-N1` needs the user.

### docs/unused-docs/implementation_plan_2026-11-09_status_allow_list.md

Implementation plan for inverting the status-claim guard into an allow-list and
putting the docs-sync rule in the test suite (SAG-M1 - SAG-M3), closing
`BACKLOG.md`'s `SST-A3` (high) and `SST-A8` (medium). **Approved under the
standing instruction 2026-11-09 and built the same day: 11 of 11 criteria
`done`, one item not code-testable (SAG-N1, that a recognised claim is true,
carried forward from SST-N1 unchanged)** - per-criterion status in
`docs/spec_coverage.md`. No file under `src/` is touched. Handoff note:
`docs/unused-docs/changes/2026-11-09-status-allow-list.md`, which is listed here only inside
this entry rather than as an entry of its own, as every handoff note is:

- A status claim must now **match** one of four recognised forms, so an
  approval state, a question, a new phrasing of "not built" and **silence** all
  fail by default. The cost `SST-A3` put at "35 existing documents" was measured
  at six, and the sixth - `docs/unused-docs/implementation_plan_2026-06-22.md`, with no
  status line for five months - was findable only under the inversion.
- The docs-sync decision is extracted into
  `tools/agents/check_docs_sync.py::verdict`, a pure function of changed paths,
  asserted over fixtures. It is not asserted over a git range on purpose:
  `tests.yml` checks out at depth 1 and has no `origin/main`, so a test that
  asked would skip on CI.
- Twenty-three mutations, seven for the criteria and sixteen for the cold
  passes' own fixes, plus one recorded as wrong. Four cold passes, each in a
  different family: two highs in this batch's own test code; one high and four
  mediums in the records rather than the code; four mediums where the guard
  would reject correct future work, and nothing that makes CI red; then two
  highs and three mediums in the third pass's own fix, where the guard had
  become weaker than the deny-list it replaces.
- `SAG-A1` to `SAG-A16` filed, not fixed; `SAG-A3` (deleting
  `agent-docs-gate.yml`) was left out deliberately.

### docs/unused-docs/implementation_plan_2026-11-08_status_claims.md

Implementation plan for the nine open `SSC` filings — status claims this repo
makes about itself that nothing checks (SST-M1 - SST-M10). **Approved
2026-11-08 and built the same day: 10 of 10 criteria `done`, one item flagged
not code-testable (SST-N1)** — per-criterion status in `docs/spec_coverage.md`.
No file under `src/` is touched. Handoff note:
`docs/unused-docs/changes/2026-11-08-status-claims.md`, which is listed here only inside
this entry rather than as an entry of its own, as every handoff note is:

- Four cold passes on 2026-11-09, in four failure families, found eleven,
  six, eight and eleven defects in this batch, all confirmed by re-measurement;
  every medium-or-higher one fixed. Twelve of the twenty-five mutations were
  green against the assertion as it then stood. The third pass audited the repo
  against the code and found no false correction, but two more stale status
  claims in wordings no guard reads. The fourth asked what the new guards
  reject rather than accept, and replaced two exact counts that would have gone
  red on correct work — a new plan document, or any new coverage row — with
  membership per source. A fifth pass, on whether the batch is green away from
  the machine that wrote it, found nothing at medium or higher and ended the
  sweep. `SST-A1` closed; `SST-A3` raised to high; `SST-A2`–`SST-A18` filed,
  not fixed, `SST-A8` being the docs-sync gate, which runs only on
  `pull_request` and so has never run here.
- Seventeen stale lines in sixteen documents saying no implementation code was
  written, over work that is built — the oldest wrong since August, and one of
  them about PD-M14, the surviving plan-day design. `SSC-4` called its four "a
  sample, not a list"; the other twelve were checked, and each correction names
  the coverage document or module that is its evidence
- The WTP criterion count measured from the spec's own rows: 41, against 38 in
  `BACKLOG.md` and 40 in the spec, whose arithmetic double-counted §3's
  amendments
- `RP-2.5` naming a `db_manager` method that has never existed, in a column no
  test read
- Twelve markdown line-number cites into the four documents every batch edits,
  three of them measurably dead, two of them in this batch's own plan
- `PRI-A1` to `PRI-A4` filed at last, with two of the four descriptions
  corrected against the code
- Three new guards, so the next one fails a test rather than waiting for a
  sweep: a register of documents allowed to claim unwritten code, a check that
  every `file::symbol` in an Implementation column resolves, and a check that
  the four chronic documents are not cited by line
- Two of those guards shipping unable to fail, both caught by the budget's rule
  that an in-loop fix is in scope for the next pass
- Two adjacent issues filed, not fixed: `SST-A1`, a reference guard whose floor
  is 18% of its domain, and `SST-A2`, fourteen test references written in a
  form no guard reads

### docs/spec_2026-11-08_weekly_tactic_as_parent.md

Spec and implementation plan for a Weekly Tactic acting as the parent of the
Action Items filed under it (WTP-M1 - WTP-M6). **Approved 2026-11-08 and built
the same day, then extended through WTP-M6.8: 41 of 41 criteria `done`, with
two human-review items outstanding** - per-criterion status in the spec's §6.
This entry and the spec both said 40 and `BACKLOG.md` said 38; the spec's own
criterion rows number 41, re-measured 2026-11-08 by the SST batch (`SSC-6`),
and the spec denied the two outstanding items in the same sentence (`SSC-9`). Three handoff notes:
`docs/unused-docs/changes/2026-11-08-weekly-tactic-as-parent.md` for the original batch,
`docs/unused-docs/changes/2026-11-08-weekly-tactic-completion-surfaces.md` for the
completion question on all seven surfaces (WTP-M6.7) and its widget tests
(WTP-M6.8), and the independent gate's reports in
`docs/unused-docs/cycles/2026-11-08_wtp-plc-upd-pd-qa-gate.md` and
`docs/unused-docs/cycles/2026-11-08_wtp-widget-tests-qa-gate.md`:

- Why the tactic is made a parent in the readers rather than in storage: the
  launch migration nulls `parent_id` for week parents, so writing it would be
  undone at the next start
- The nine readers of parenthood the app had, and what each did with
  `weekly_tactic_id` before this
- `parent_of` as the one object-level authority, `get_children` as its SQL
  form, and the test that holds the two to the same answer over every link
  shape
- Why `parent_id` wins when both columns are set, so one item has one place in
  the tree
- Three faults found while implementing: a second parenthood reader in the
  Hierarchy dialog, a delete that removed subtasks before deciding it should
  not have, and a vacuous test whose own justification in this spec was wrong
- The corrected account of what a tactic delete used to do, with the counts it
  was verified against
- The three criteria deferred on the day for a concurrent session's files,
  since built; the adjacent findings left unfixed are WTP-A1 to WTP-A8 in
  `BACKLOG.md`
- WTP-M6.7: the question was first built in `ItemEditorDialog` alone and
  reported done on that basis, while six other surfaces completed a tactic
  silently (P25). `confirm_weekly_tactic_completion` now holds it once
- WTP-M6.8: 21 real-widget tests that build each screen, find the control by
  reading the item id out of its own callback, and press it with the widget's
  own `toggle()`/`invoke()`

## Feature-Specific Documentation

### Requirements (Consolidated)

All requirements are now maintained in `GetMoreDone_MasterSpec_SQLite_v1.md`. The timer-specific requirements document is retained only for archival reference.

### docs/google-calendar-setup.md (13KB)

Google Calendar integration guide:

- OAuth 2.0 setup instructions
- credentials.json configuration
- Authorization flow
- **Exporting a planned day** from the Plan screen: what goes out, what is
  skipped and why, what a second export of the same day does, and which
  calendar is written to
- Troubleshooting common issues
- API quota information

### docs/DEMO_INSTALL.md

Running a demo instance beside the real installation:

- `GETMOREDONE_DATA_DIR` and `GETMOREDONE_DB`, and which outranks which
- Why the whole data directory moves, not just the database (`app.lock`)
- `./start-demo.sh`, its seed-when-empty rule and `--print-env`
- Why it refuses a directory overlapping the real installation, either way
- What stays shared (Google credentials)
- Resetting and reseeding the demo

### docs/DEV_PROD_WORKFLOW.md

Dev vs prod database selection, the two launchers' differing defaults, and the
Gmail importer's own rule.

## Troubleshooting Guides

### docs/EMAIL-AUTH-TROUBLESHOOTING.md (11KB)

Email authentication troubleshooting:

- Common OAuth errors
- Token refresh issues
- Client ID mismatches
- Step-by-step fixes

### docs/CLIENT_ID_MISMATCH_FIX.md (7.6KB)

Fixing client ID mismatch errors:

- Root cause analysis
- Token file cleanup
- Re-authorization steps
- Verification procedures

### AUDIO_TROUBLESHOOTING.md (2.0KB)

Audio playback issues:

- Missing pygame errors
- Audio file format issues
- Volume control problems
- Music folder configuration

### CLEAR_BROWSER_CACHE.md (5.7KB)

Browser cache clearing guide:

- Chrome instructions
- Firefox instructions
- Safari instructions
- Why clearing cache helps

### QUICK_FIX_ZOMBIE_TOKEN.md (2.0KB)

Quick fix for stuck tokens:

- Delete token.json
- Re-authorize
- Verify functionality

### fix_oauth_app_name.md (3.1KB)

OAuth application name configuration:

- Update Google Cloud Console
- Refresh credentials
- Test authorization

## Test Scripts

### test_vps_segments.py

Standalone test script for VPS segment management:

- 7 structure and functionality tests
- Import validation
- Method existence checks
- Enhanced deletion protection verification
- **Status**: ✅ All tests passing

### tests/test_vps_integration.py

Integration tests for VPS:

- 36 total tests across 6 test classes
- Bug fix tests (5 tests)
- Segment management tests (9 tests)
- Record creation/update/deletion tests
- **Status**: ✅ All tests passing (0.96s)

### Other Test Files

- `tests/test_database.py` - Database operations
- `tests/test_contact_integration.py` - Contact management
- `tests/test_date_adjustment.py` - Date validation
- `tests/test_item_editor.py` - Item editor functionality
- `tests/test_note_search.py` - Obsidian integration
- `tests/test_obsidian_integration.py` - Note linking
- `tests/test_timer.py` - Timer functionality
- `tests/test_today_screen.py` - Today screen
- `tests/test_upcoming_items.py` - Upcoming view
- `tests/test_validation.py` - Data validation

## Utility Scripts

### ../tools/convert_music_to_mp3.py

Convert audio files to MP3 format:

- Supports M4A, AAC, WAV, OGG
- Batch conversion
- Quality settings

### ../tools/create_demo_data.py

Create sample data for testing:

- Action items
- Contacts
- VPS records

### ../tools/diagnostics/diagnose_calendar.py

Diagnose Google Calendar issues

### ../tools/diagnostics/diagnose_client_id.py

Check OAuth client ID configuration

### ../tools/diagnostics/debug_auth_loading.py

Debug authentication loading issues

### test_audio.py

Test audio playback functionality

### tools/diagnose_google_auth.py

Test OAuth authentication

### test_obsidian_dialogs.py

Test Obsidian integration dialogs

### test_vps_init.py

Test VPS initialization

## Shell Scripts

### start.sh (Linux/Mac)

One-command startup script:

- Creates virtual environment
- Installs dependencies
- Launches application

### start.bat (Windows)

Windows startup script

### ../tools/diagnostics/fix_client_id_mismatch.sh

Automated client ID fix

### ../tools/diagnostics/fix_wrong_project.sh

Fix wrong Google Cloud project

### ../tools/diagnostics/fix_zombie_token.sh

Automated token cleanup

### ../tools/diagnostics/verify_auth.sh

Verify authentication setup

## Documentation Organization

### By Category

**Getting Started**

- README.md
- GetMoreDone_MasterSpec_SQLite_v1.md

**VPS Documentation**

- docs/unused-docs/VPS_UPDATES_2026-01-24.md
- docs/VPS_TESTING_SUMMARY.md
- docs/DOCUMENTATION_UPDATE_SUMMARY.md

**Feature Guides**

- docs/action-timer-requirements.md
- docs/google-calendar-setup.md

**Troubleshooting**

- docs/EMAIL-AUTH-TROUBLESHOOTING.md
- docs/CLIENT_ID_MISMATCH_FIX.md
- AUDIO_TROUBLESHOOTING.md
- CLEAR_BROWSER_CACHE.md
- QUICK_FIX_ZOMBIE_TOKEN.md
- fix_oauth_app_name.md

**Development**

- NOTES.md (recent changes)
- BACKLOG.md (task tracking)
- tests/\* (test files)

### By Size

Large (>10KB):

- README.md (27KB)
- GetMoreDone_MasterSpec_SQLite_v1.md (19KB)
- docs/action-timer-requirements.md (19KB)
- docs/EMAIL-AUTH-TROUBLESHOOTING.md (11KB)
- docs/google-calendar-setup.md (13KB)

Medium (5-10KB):
- docs/unused-docs/VPS_UPDATES_2026-01-24.md (8.5KB)
- docs/CLIENT_ID_MISMATCH_FIX.md (7.6KB)
- CLEAR_BROWSER_CACHE.md (5.7KB)

Small (<5KB):

- docs/VPS_TESTING_SUMMARY.md (5.1KB)
- docs/DOCUMENTATION_UPDATE_SUMMARY.md (5.1KB)
- BACKLOG.md (4.1KB)
- fix_oauth_app_name.md (3.1KB)
- NOTES.md (2.3KB)
- AUDIO_TROUBLESHOOTING.md (2.0KB)
- QUICK_FIX_ZOMBIE_TOKEN.md (2.0KB)

## Recent Updates (2026-01-24)

**NEW Documentation**

1. docs/unused-docs/VPS_UPDATES_2026-01-24.md - Comprehensive VPS change log
2. docs/VPS_TESTING_SUMMARY.md - Complete test documentation
3. docs/DOCUMENTATION_UPDATE_SUMMARY.md - Documentation update summary

**UPDATED Documentation**

1. README.md - Added Testing section
2. NOTES.md - Already included all recent changes
3. BACKLOG.md - Marked features complete

## Quick Access

### I need to...

**Learn about the project** → README.md

**See recent changes** → NOTES.md

**Fix authentication issues** → docs/EMAIL-AUTH-TROUBLESHOOTING.md

**Set up Google Calendar** → docs/google-calendar-setup.md

**Understand VPS updates** → docs/unused-docs/VPS_UPDATES_2026-01-24.md

**Run tests** → docs/VPS_TESTING_SUMMARY.md or README.md (Testing section)

**Fix audio issues** → AUDIO_TROUBLESHOOTING.md

**Check feature backlog** → BACKLOG.md

**Understand the system** → GetMoreDone_MasterSpec_SQLite_v1.md

**Clear browser cache** → CLEAR_BROWSER_CACHE.md

## Documentation Standards

All documentation follows these standards:

- Markdown format (.md)
- Clear section headings
- Code blocks with syntax highlighting
- Tables for structured data
- Emoji for visual clarity ✅ ⚠️ ❌
- Links to related documents
- Last updated dates

## Prompts and drafts (moved out of the repo root 2026-11-08)

These four sat untracked at the repo root until they were committed in
`2934e2d`, which turned `tests/test_repo_hygiene.py::test_rm7c_repo_root_doc_allowlist`
red: that test allows a fixed set of root documents and these were not on it.
They were moved here rather than added to the allowlist, whose entries are all
structural (README, a `CLAUDE.md` the tool loads from the root), which a draft
is not.

### `docs/daVIPA - Get Started.md`

The user-facing getting-started guide, 791 lines. Sits beside
`docs/USER_GUIDE.md`, which is the same genre and was already here.

### The four prompt briefs — filed 2026-11-09

`daVIPA_rebrand_prompt.md`, `demo-install-prompt.md`,
`prompt-test-suite-remediation.md` and `prompt-update-claude-md-and-learnings.md`
are task briefs for batches that are finished. They moved to
`docs/unused-docs/` on 2026-11-09, where they are kept for history and no test
reads them. The `Spec:` docstrings in `src/getmoredone/branding.py` and
`tests/test_branding.py` were repointed at the new path in the same change.

## Maintenance

Documentation is updated:

- After each feature implementation
- When bugs are fixed
- When tests are added
- When user issues are resolved
- During major releases

**Current Status**: on 2026-11-09 the per-batch records were filed under
`docs/unused-docs/` — 194 files: handoff notes, implementation plans,
coverage snapshots and dated status reports. No test reads them. This index
lists them still, because finding a record is what an index is for, but the
live reference set under `docs/` is now 43 Markdown files at depth 1 out of
237 files in `docs/` in all. The prose guards that used to check this
index's own citations are deleted; see `CLAUDE.md`, *Records are filed, not
tested*.

This footer used to read "All documentation up to date as of 2026-01-24";
nothing checks that claim - no test asserts every document is listed here, which
is PLC-A5 in `BACKLOG.md` - so it is stated as a date, not as a guarantee.
