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

### `docs/changes/`

Agent handoff notes and implementation summaries:

- One note per substantial agent change
- Verification commands and outcomes
- Risks / known gaps
- Follow-up guidance for subsequent agents

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

### daVIPA_MasterSpec_SQLite_v1.md (19KB)

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

### docs/MULTI_AGENT_WORKFLOW.md (NEW)

Starter operational guide for multi-agent delivery:

- Role definitions (Code / Docs / GitHub agents)
- Worktree bootstrap command and branch model
- Required handoff note workflow
- PR template and CI docs-gate behavior

### `.github/pull_request_template.md`

Pull request template used for multi-agent delivery:

- Summary / validation sections
- Agent handoff reference
- Docs sync checklist
- Maintainability checklist aligned with `codex.md`

## VSP (Vision Strategy Plan) Documentation

### docs/VPS_UPDATES_2026-01-24.md (8.5KB) **NEW**

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
`UPD-F1` - `UPD-F4`, in the plan below; three are built and the §11 walk is
owed again, steps 4, 7 and the new 11 to 13 included (per-criterion status in
the spec's §10, and the batch's handoff note is
`docs/changes/2026-11-08-unified-panel-m7.md`):

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

### docs/implementation_plan_2026-11-08_unified_panel_followups.md

Spec and implementation plan for what the unified panel design's on-screen
check found (UPD-F1 - UPD-F4). **Approved 2026-11-08. UPD-F2, UPD-F3 and
UPD-F4 built the same day; UPD-F1 not built** -- it is the only defect of the
four and the only one that must change `src/getmoredone/app_settings.py`,
which the concurrent calendar-export batch holds uncommitted (per-criterion
status in `docs/spec_coverage.md`, and the batch's handoff note is
`docs/changes/2026-11-08-unified-panel-followups.md`):

- UPD-F1, the one defect: no column width or divider position survives a
  relaunch, because `AppSettings.save()` writes the whole object and a screen
  holding its own snapshot reverts what another screen wrote
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

### docs/implementation_plan_2026-11-08_priority_level_colours.md

Implementation plan for configurable priority level colours (PLC-M1 - PLC-M5).
**Approved 2026-11-08 and built the same day**; per-criterion status in
`docs/spec_coverage_2026-11-08_priority_level_colours.md`, and the batch's
handoff note is `docs/changes/2026-11-08-priority-level-colours.md`:

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

### docs/implementation_plan_2026-11-08_plan_calendar_export.md

Implementation plan for exporting a planned day to Google Calendar
(CE-M1 - CE-M5). **Approved 2026-11-08 and built the same day**;
per-criterion status, the verification runs and seven deviations from this
plan's wording are in
`docs/spec_coverage_2026-11-08_plan_calendar_export.md`, and the batch's
handoff note is `docs/changes/2026-11-08-plan-calendar-export.md`:

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
- Four adjacent issues found and not fixed
- The six-step manual checklist, which is the part no test can cover

### docs/spec_2026-11-08_weekly_tactic_as_parent.md

Spec and implementation plan for a Weekly Tactic acting as the parent of the
Action Items filed under it (WTP-M1 - WTP-M6). **Approved 2026-11-08 and built
the same day, then extended through WTP-M6.8: 40 of 40 criteria `done`** -
per-criterion status in the spec's §6. Three handoff notes:
`docs/changes/2026-11-08-weekly-tactic-as-parent.md` for the original batch,
`docs/changes/2026-11-08-weekly-tactic-completion-surfaces.md` for the
completion question on all seven surfaces (WTP-M6.7) and its widget tests
(WTP-M6.8), and the independent gate's reports in
`docs/cycles/2026-11-08_wtp-plc-upd-pd-qa-gate.md` and
`docs/cycles/2026-11-08_wtp-widget-tests-qa-gate.md`:

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

All requirements are now maintained in `daVIPA_MasterSpec_SQLite_v1.md`. The timer-specific requirements document is retained only for archival reference.

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
- daVIPA_MasterSpec_SQLite_v1.md

**VPS Documentation**

- docs/VPS_UPDATES_2026-01-24.md
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
- daVIPA_MasterSpec_SQLite_v1.md (19KB)
- docs/action-timer-requirements.md (19KB)
- docs/EMAIL-AUTH-TROUBLESHOOTING.md (11KB)

Medium (5-10KB):

- docs/google-calendar-setup.md (8.7KB)
- docs/VPS_UPDATES_2026-01-24.md (8.5KB)
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

1. docs/VPS_UPDATES_2026-01-24.md - Comprehensive VPS change log
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

**Understand VPS updates** → docs/VPS_UPDATES_2026-01-24.md

**Run tests** → docs/VPS_TESTING_SUMMARY.md or README.md (Testing section)

**Fix audio issues** → AUDIO_TROUBLESHOOTING.md

**Check feature backlog** → BACKLOG.md

**Understand the system** → daVIPA_MasterSpec_SQLite_v1.md

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

## Maintenance

Documentation is updated:

- After each feature implementation
- When bugs are fixed
- When tests are added
- When user issues are resolved
- During major releases

**Current Status**: ✅ All documentation up to date as of 2026-01-24
