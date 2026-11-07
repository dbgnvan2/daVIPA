## Recent Changes (2026-11-07)

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
  other. `VPSManager.get_action_items_for_weekly_tactic` reads the union, and
  `test_awam23_one_home_for_the_link_predicate` walks the AST to assert it is
  the only function in `src/` naming both columns in one query string.
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
