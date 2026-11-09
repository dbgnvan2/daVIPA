# daVIPA Backlog

Last Updated: 2026-11-09 — trimmed back to what is active. 245 items became
76: the closed ones, the review-sweep residue ("below medium", "cold pass",
"deferred") and the items whose subject was deleted with the prose-reading
guards on 2026-11-09 are filed in
`docs/unused-docs/backlog_archive_2026-11-09.md`, with the reason on each.
The running "Last Updated" narrative that used to sit here — one paragraph
listing every batch of the preceding fortnight — went with them.

One batch at a time in this checkout (`CLAUDE.md`). What is here is open work:
adjacent issues from recent batches, screen reports, the carried-forward
features, and the long-standing bugs, requests and user stories at the end.

## `main` is green — what is left of the go-green list (2026-11-09)

Closed. CI run **42721197588** at `f01c23f` is green on Python 3.11, 3.12 and
3.13: `2660 passed, 10 skipped`. The twenty failures this section tracked from
run 42550648188 on `b6d6ddf` are all closed — eleven by the PDT and PRIT
batches on 2026-11-08, the remaining nine on 2026-11-09 by WTP-A11 (seven
tests that measured the CI display rather than the code) and by the two that
failed only in CI.

The one item below is what did not close with them. The section's history —
which batch closed which group, and the run that confirmed each — is filed in
`docs/unused-docs/backlog_archive_2026-11-09.md`.

Re-measure a failure list with:

```
gh run view <run-id> --log-failed | grep -oE "_{3,} test_[a-z0-9_]+ _{3,}" | sed -E 's/_+ (test_[a-z0-9_]+) _+/\1/' | sort -u
```

### The traceability pair — partly closed (low)

`::test_every_referenced_test_name_exists` is **green** (PDT-M4.1, `2cd83a3`).
References left behind by the PD-M14 rewrite were repointed at the tests that
now cover them, one at a time rather than matched approximately: **8 repointed
and 1 dropped across 3 rows of `docs/spec_coverage.md`, and 3 `Tests:` lines
across `src/getmoredone/screens/plan.py` and
`src/getmoredone/time_block_layout.py`**. (`2cd83a3`'s subject says "seven",
and the first two versions of this item said five and then seven; all three
counted names in a hand-written list, not edits in the diff.) One of them,
`edge_limit_time`, had no test under the name it claimed and none under any
other; it now points at
`tests/test_plan_screen.py::test_pdm146_both_ends_refuse_at_midnight_and_say_which`,
which is what asserts its limit reaches the message.

`::test_every_referenced_test_file_exists` was **still red** on the two
`models.py` references only, which was item 2. **Closed 2026-11-08 by the PRIT
batch** — the two files were written (`750afe6`), not the docstrings deleted,
which is what item 2 said the closure had to be. All three tests in
`tests/test_traceability_refs.py` are green.

## Adjacent issues — the status-claim batch (SST, 2026-11-08)

Found while measuring for the SST batch, outside its scope, not fixed.

### SST-A2 — fourteen test references are written in a form no guard reads (low)

`docs/spec_coverage*.md` carries 14 references of the form
`test_time_block_layout.py::test_name` — the basename without the `tests/`
prefix. `tests/test_traceability_refs.py`'s pattern requires `tests/`, so none
of the fourteen is checked, and `tests/test_doc_status_claims.py` leaves bare
`::test_…` names to that guard on purpose.

Resolved by hand: thirteen point at tests that exist. The fourteenth,
`test_time_block_layout.py::test_pdm58_the_day_cannot_cross_midnight`, does
not — and it is a deliberate quotation, inside
`docs/unused-docs/spec_coverage_2026-11-08_plan_calendar_export.md`'s record of which
references were failing at the time. So widening the existing pattern to accept
the bare form would turn a correct historical record red, which is why it was
not widened here.

The fix is the convention the `Tests:` guard already documents for retired
tests — a quoted reference drops the `::` form — applied to records that quote
a broken reference. Thirteen live references would then be checked, and the
fourteenth would stop looking like a live pointer.

**Priority:** Low
**Effort:** Low

### SST-A12 — `_defined_names()` cannot resolve an indented constant (low)

Its third pattern is `^(\w+)\s*[:=]`, column 0 only. Four of the current
implementation references resolve *only* through it — `CELEBRATION_TYPES`,
`LEVEL_KEYS`, `PRIORITY_BANDS`, `_HEX_COLOR_RE` — so naming a constant is an
established style here. A coverage row naming a class-level constant or a
`models.py` dataclass field, both indented, is correct and unresolvable, and
`test_sstm5_every_implementation_reference_resolves` fails on it. Walking the
AST for assignment targets at any depth is the fix.

Filed 2026-11-09 by the fourth cold pass over the SST batch.

**Priority:** Low
**Effort:** Low

### SST-A17 — the docs-gate command this batch documented assumes a built venv (low)

`CLAUDE.md` now says to run the docs-sync check by hand with the interpreter
inside `./venv/`, which exists only after `start.sh` has built it. On a fresh
clone on the other Mac the documented command fails with "no such file", though
`tools/agents/check_docs_sync.py` itself needs nothing from the venv. Naming
`python3` there, or saying the venv is a precondition, is the fix.

Filed 2026-11-09 by the fifth cold pass over the SST batch.

**Priority:** Low
**Effort:** Low

### SST-A18 — a test docstring still calls the docs-sync gate a merge gate (medium-low)

`tests/test_release_licensing.py::test_bi2_the_docs_sync_gate_knows_about_both_dependency_files`
opens by saying `CLAUDE.md` makes "dependencies changed -> docs updated" a merge
gate. `CLAUDE.md` now says the opposite, because this batch measured it: the
workflow triggers on `pull_request` only and this repo opens none, so the gate
has never run here. The test's assertions are fine; its stated reason is a claim
this repo makes about itself that is no longer true — this batch's own subject,
found in a file the batch did not open. Rewording it belongs with `SST-A8`,
which moves the check into the suite.

Filed 2026-11-09 by the fifth cold pass over the SST batch.

**Priority:** Medium-low
**Effort:** Low

## Adjacent issues — priority defaults and the cap (PRI, filed 2026-11-08)

Promised by `docs/unused-docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md`'s
"Adjacent issues found, not fixed", which ends "Each is filed in `BACKLOG.md`
as PRI-A1 … PRI-A4 when this plan is approved", and repeated in
`docs/DOCUMENTATION_INDEX.md`. The plan was approved and built; the four
filings were never made, so two documents asserted the existence of items that
were nowhere. Filed 2026-11-08 by the SST batch, which closed `SSC-1`'s second
clause, and held to by
`tests/test_doc_status_claims.py::test_sstm9_every_promised_pri_adjacent_item_is_filed`.

**Two of the plan's four descriptions were wrong, and are corrected here**
rather than copied. Measured at `79cd32d`.

### PRI-A1 — `item.importance == 20 or item.urgency == 20`, by hand in five screens (medium)

```
grep -rn "importance == 20" src/getmoredone/screens/
```

Five screens: `today.py`, `all_items.py`, `completed.py`, `hierarchical.py`,
`upcoming.py`. The literal `20` is P4, and
`priority_levels.priority_level_for_item` already answers exactly this
question. `PLC-A3` and `PLC-A6` are the same five copies reached from the
colour side — `PLC-A6` measures the two inputs they already disagree on (an
importance of `25`, and one stored as the string `"20"`). **One fix, filed
three times**; whoever takes it should close all three.

**Priority:** Medium
**Effort:** Low

### PRI-A2 — the score column's width is a magic number in five places (low)

```
grep -n "priority_score" src/getmoredone/screens/*.py
```

Five render sites, not the six the plan says: `width=60` in `today.py`,
`completed.py`, `hierarchical.py` and `upcoming.py`, and `width=80` in
`all_items.py`. The plan's sixth figure, `70`, is the Timer button in
`today.py`, not a score column — that is the plan's error, not a width that has
since moved.

**Priority:** Low
**Effort:** Low

### PRI-A3 — All Items shows the bare score, the other four show `P:n` (low)

`all_items.py` renders `str(item.priority_score)` in an 80px slot with a
`"Priority"` column header; the other four render `f"P:{item.priority_score}"`
in 60px with **no** header. The plan has this the wrong way round: it says
"only `today.py` has a header to match", and `grep -rn '"Priority"'
src/getmoredone/screens/` shows the header is `all_items.py`'s and nobody
else's. So the one screen whose column is labelled is also the one that drops
the `P:` prefix, which is the opposite of the reasoning the plan gives.

With a four-digit score now possible, the 60px slot is the one to measure
first: `PRI-M3` was specced for exactly this and is not built (`PRIT-N1`).

**Priority:** Low
**Effort:** Low

### PRI-A4 — demo data bypasses the defaults and the floor (low — a note, not a defect)

`src/getmoredone/demo_data.py` calls `create_action_item(..., apply_defaults=False)`
at both of its two call sites and hard-codes its factors, so a demo database
demonstrates neither Defaults nor the floor. Correct as designed; filed because
it is why `python tools/create_demo_data.py` will not show this feature, which
is worth knowing before anyone tests it that way.

**Priority:** Low
**Effort:** Low

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

### 2026-11-08 - Type: Technical Debt

**Title:** UPD-A12 - weekly_items.py abbreviates two filter labels the APE tabs write out
**Description:** `src/getmoredone/screens/weekly_items.py` labels its three
lineage filters "Segment:", **"Sub:"** and **"Cat:"**, where
`ape_assignment.py` and `ape_period_view.py` write "Segment:",
"SubSegment:" and "Category:". `screens/lineage_filters.build_combos`, which
APE Week Actions uses, also writes the short forms - so three tabs say "Sub"
and two say "SubSegment" for the same filter.

UPD-F2 moved all of those labels onto a new row without touching their text.
Which wording is right is a decision about the design, and the unification is
UPD-A9's work: that entry already owns the five remaining copies of the filter
triple, and the wording should be settled once, there, rather than twice.
**Priority:** Low
**Effort:** Low

### 2026-11-08 - Type: Technical Debt

**Title:** UPD-A13 - no test enforces docs/DOCUMENTATION_INDEX.md's completeness
**Description:** The global rule in `~/.claude/CLAUDE.md` is that where a repo
keeps a documentation index, every document is listed in it **and a test
enforces that**. No test checks the index for completeness. (This line used
to say `grep -rn DOCUMENTATION_INDEX tests/` returned nothing; the SST batch
falsified that on 2026-11-08 — the grep now returns the eight lines in
`tests/test_doc_status_claims.py`, none of which checks completeness. Corrected
2026-11-09 by the second cold pass; the conclusion stands, its evidence did
not.) **Measured 2026-11-09 by the third cold pass: 26 of the 42
`docs/unused-docs/implementation_plan_*.md`, `docs/spec_*.md` and `docs/unused-docs/spec_coverage_*.md`
documents are absent from the index.** Two of the 26 were the stale status
claims that pass found — a spec headed as a draft over a module that shipped in
August, and a plan whose `## Status` described three built phases in the future
tense. That is the mechanism: a document in no index is a document nobody
re-reads. The index is kept by hand - which is how it came to carry a
"Not approved" line for a plan that had been approved and built the same day,
found while writing this batch's entry.

The test is small: walk `docs/*.md` plus `docs/unused-docs/changes/*.md`, read the
`### <path>` headings out of the index, and assert the two sets match, with an
explicit allow-list for anything deliberately unlisted. It was not written
inside this batch because the batch's own entry is one of the things it would
police, and a check written by the change it is checking is the wrong order.
This is the same class as P25: a rule that holds on only one surface, and not
the one anyone uses.

**The same gap is filed again, at low, as `PLC-A5`**, whose own text is where
six other places route a reader for it. Whichever is taken, close both: the
test design is here, the routing is there, and `SSC-8` was the finding that
they had no pointer between them.
**Priority:** Medium
**Effort:** Low

## Adjacent issues — Plan day calendar export (CE, 2026-11-08)

Found while building CE-M1 to CE-M5. Flagged, not fixed (global rule 10): each
is real, none is what was asked for, and each sits in code the export only
reads past.

### CE-A1 — `update_event` silently drops `location` and `attendees` (medium)

`src/getmoredone/google_calendar.py::update_event` sends the body it fetched
with `summary`, `start`, `end` and `description` replaced. `location` and
`attendees` survive only because the fetched body carries them; nothing in the
signature lets a caller change them, and a caller that means to clear one has
no way to say so. The day export never sets either, so this batch cannot
trigger it — but the Item Editor's calendar dialog sets both on create, and
the first code that edits such an event through `update_event` will find it
can only ever preserve what is already there.

**Priority:** Medium
**Effort:** Small

### CE-A2 — `_say` prints to stdout from a GUI app (low)

`src/getmoredone/google_calendar.py::_say` writes status lines to stdout.
Same family as the fixed defect where a status `print` inside a credential
`try` discarded a valid token when the stdout write failed: a packaged app's
stdout is not guaranteed writable, and a print in a `try` makes the failure
look like the thing being tried. The export path calls it through the shared
helpers.

**Priority:** Low
**Effort:** Small

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
**Not started, and not to be started from the session that wrote the spec.**

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
- **It cannot start while PD-M14 is in flight.** CIP-M3.3 and CIP-M3.7 extend
  exactly the `time_block_layout.py` surface that batch is changing.

**Priority:** Next feature
**Effort:** High (two batches)

## Adjacent issue — weekly tactic as parent (WTP, 2026-11-08)

Found while building WTP-M6.4. Flagged, not fixed (global rule 10).

### WTP-A1 — the shipped-column width test names its sets by hand (low)

`tests/test_unified_panel_design.py::test_updm31_every_shipped_column_declares_a_width_it_can_have`
holds a literal dict of column sets, so a set added to `chip_table.py` is not
checked until somebody remembers to add it there too. That is what had
happened: `WEEK_ACTIONS_LEFT_COLUMNS` shipped in UPD-M6 and was never in the
dict, and the two sets this batch touched were added by hand for the same
reason. The guarantee the test is written to give — *every* shipped column
declares a width inside its own bounds — is not the guarantee it enforces.

The fix is to enumerate the module instead: every module-level
`Tuple[ChipColumn, ...]` in `chip_table.py`, found by name rather than listed.
Not fixed here because it is a change to a test's subject, which is the kind of
rewrite that wants its own pass rather than riding along with a feature.

**Priority:** Low
**Effort:** Small

## Adjacent issues — CI green (CIG, 2026-11-09)

Found while building `CIG-M1` to `CIG-M4`. Flagged per rule 10, not fixed: each
is real, none is what the batch was for, and every one of them is a second
design decision about tests this batch is already rewriting.

### CIG-A1 — the precondition registry cannot detect a new offender (medium)

`tests/test_display_capabilities.py::EXPECTED_CALLERS` holds the eight tests
that ask `require(...)`, and the guard asserts set equality both ways. That
catches a precondition **dropped** from one of the eight and a skip nobody
registered. It cannot catch what caused this batch: a *new* test that sets a
window attribute and reads it back without asking the precondition at all. Six
of the seven failures were written that way.

Nothing asserts the skip count either. After this batch CI reports 10 skips for
display reasons, and a count nobody checks is exactly how the test figures in
`CLAUDE.md` drifted by 741 and 13.

The right form is a test that finds the read-backs rather than listing their
callers — an AST walk for `wm attributes`-shaped reads whose enclosing function
does not call `require` — and that is a judgement about how much the suite
should know about its own environment, which is why it is filed.

**Priority:** Medium
**Effort:** Medium

### CIG-A2 — two `-alpha` tests skip where they could assert (medium)

`tests/test_tk_offscreen.py::test_alpha_still_passes_through_the_attributes_wrapper`
and `::test_raw_tkinter_windows_are_hidden_and_registered_too` now skip on CI.
They need not: the same file has two `-alpha` read-backs at
`test_a_remapped_window_is_made_transparent_again` and
`test_a_mapped_window_is_invisible_but_still_measurable` that **pass on CI**,
and what makes them different is that they take the `mapped_windows` fixture
and so map and settle their window first. `conftest.py` records that those two
were made green by CI measurement.

So the fix is to map these two as well, which keeps them asserting on CI
instead of skipping. Not done here because `mapped_windows` is the fixture the
local throttle skips, so the change cannot be verified on this machine at all —
it would be written blind and verified only by the next CI run.

**Priority:** Medium
**Effort:** Small

### CIG-A3 — T5.6 and T5.7 now have no CI coverage, and a spy is available (medium)

The plan rejected replacing the five always-on-top read-backs with a spy on
`wm attributes`, on the ground that
`tests/test_timer_session_endings.py` says the read-back is deliberately "past
the patch in both directions". That is a real reason for T5.1 and T5.2, which
are about the attribute reaching Tk. It is weaker for T5.6 and T5.7, which are
about a **depth counter**: `_suspend_topmost` / `_resume_topmost` nest, and the
bug they guard was an unbalanced resume handing the flag back early. A spy
measures that without a window manager, and
`tests/test_reward_protocol_timer.py` already spies on `wm attributes` with a
stub window, so the mechanism exists in this suite.

Filed rather than built because the plan stated a preference as a constraint
and the cold pass caught it; building the alternative in the same batch would
be the third design for these tests in one day.

**Priority:** Medium
**Effort:** Small

### CIG-A4 — `test_cigm14_the_private_copy_of_the_precondition_is_gone` asserts by grep (low)

Two unanchored substring checks over
`tests/test_weekly_tactic_completion_widgets.py`. The repo rule is to parse
rather than grep where a behavioural check is impractical, and
`tests/source_asserts.py` exists for exactly this. The substance — that the
private skip wording is gone and `_TOPMOST_ON` survives — is right; the form is
not.

**Priority:** Low
**Effort:** Small

### CIG-A5 — the `-alpha` probe is partly vacuous (low)

`_PROBES["-alpha"]` sets 0.0 and asserts 0.0 comes back. `conftest` already
sets alpha 0.0 on every test window at creation, so on a display where the
attribute is simply ignored and the read-back returns whatever was last stored,
the probe answers True without the display having honoured anything. A value
the wrapper does not already set — 0.5 — would distinguish the two.

Low rather than medium because the probe is measured against a second window by
`CIG-M1.1`, so a wrong answer is a red test rather than a silent skip; and
because the probe's window is built with raw `tk.Tk`, outside the wrapper.

**Priority:** Low
**Effort:** Small

### CIG-A6 — `_requirers()` matches only a bare `require(...)` (low)

The AST walk looks for `ast.Name` with `id == "require"`. A caller that writes
`caps.require("-topmost")` — which the module's own docstring style invites —
is an `ast.Attribute` and is invisible to it, so it would read as a missing
precondition. Harmless today, because all eight callers import the bare name;
it is the form that is wrong. Same family as `CIG-A1`.

**Priority:** Low
**Effort:** Small

### CIG-A7 — the new test file carries no marker, and three smaller things (low)

`tests/test_display_capabilities.py` AST-walks the test tree and reads source
text, which is what the `meta` marker is for, and it has none: it is counted as
app behaviour by `-m "not meta"`. Alongside it: `_independently()` in that file
has no `except` mirror of the probe's own, so a display that raises leaves the
comparison an error rather than a disagreement;
`test_pbm61_a_tall_row_keeps_its_slack_below_its_text`'s docstring cites
`plan_blocks.py` by line number, which `SST-M8` forbids for the chronic
documents and is the same defect class here; and the probe builds a second Tcl
interpreter, so it is the first `tk.Tk()` of a run and sets `_default_root`.

**Priority:** Low
**Effort:** Small

### CIG-A8 — why the body reports 1208px under X11 is unknown (low)

`test_updm14_zero_width_body_is_a_noop` failed on CI for months with
`assert 1208 <= 8`: `body.configure(width=8)` did not change
`body.winfo_width()` there, and does here. Two explanations were written into
the test as comments and both were withdrawn after measurement — the body
reports 1px whatever its holder does, and the root's geometry is not what the
body follows. The test no longer depends on the answer, so this is filed as the
open question it is rather than guessed at again.

**Priority:** Low
**Effort:** Medium (diagnosis, on a machine with the CI display)

### CIG-A9 — the traceability guard cannot see a bare `::name` (low)

`docs/spec_coverage.md` cited
`::test_pbm61_a_tall_row_keeps_its_two_lines_together` after this batch renamed
it, and `tests/test_traceability_refs.py` stayed green: its pattern is
`(tests/[\w/]+\.py)(?:::(\w+))?`, so a `::name` with no file before it is not
a reference it can check. The coverage file's Tests column is written that way
throughout — the file is named once in a section header and every row uses the
bare form — so the guard is blind to the majority of that column.

Found by reading, not by a test, which is the point of filing it.

**Priority:** Low
**Effort:** Medium

## Adjacent issues — priority level colours (PLC, 2026-11-08)

Found while building PLC-M1 to PLC-M5. Flagged, not fixed (global rule 10):
each is real, none is what was asked for, and a fix for any of them would be a
silent sweep of behaviour nobody asked about.

### PLC-A1 — a segment-coloured row keeps the theme's text colour (medium)

All five list screens set `row_text = palette["row_text"]` and then fill the
row with a VSP segment colour from the database, so a pale segment colour in
the dark theme gets near-white text on it. `today.py:487` is where the new fill pays for it; `upcoming.py`, `all_items.py`, `hierarchical.py` and `completed.py` have
the same shape.

Exactly the defect PLC-M4.4 fixes for the new priority fill, and fixed there in
the obvious way — derive the text colour from the fill with `pick_text_color`.
Not extended to segment fills in this batch, because that changes how every
segment-coloured row already on the user's screen looks.

### PLC-A2 — Hierarchical and Completed ignore their own segment colour for the fill (low)

Both resolve `segment_color`, apply it as an accent, and then never consider it
for the row background, unlike Today, Upcoming and All Items
(`hierarchical.py:231-239`, `completed.py:204-212`). Either the accent-only
treatment is right and the other three are wrong, or the reverse; nothing
records which, and `row_fill` preserves the difference by having both pass
`segment_color=None`.

### PLC-A3 — the `P:` chip hard-codes `danger` for critical, in five screens (low)

`fg_color=palette["danger"] if is_priority_critical else "transparent"`, with
its own inline `importance == 20 or urgency == 20` beside it
(`today.py:652`, `upcoming.py:417`, `all_items.py:371`, `hierarchical.py:309`,
`completed.py:271`). Out of scope by the user's explicit choice — the colour
setting paints the row tint only — but with Any Critical now green, the row and
its chip disagree by design. Worth a decision rather than leaving it implicit.

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

### 2026-11-07 - Type: Technical Debt

**Title:** UPD-A7 - two dead members in annual_vision_segments.py, by index, left by the drag that moved to rows
**Description:** `self.drag_index: Optional[int] = None`
(`src/getmoredone/screens/annual_vision_segments.py:33`) has no reader anywhere
in `src/` or `tests/` - grep returns the assignment and nothing else - and
`_create_from_index(idx)` (`:272`) has no caller: it looks the row up in
`self.left_items` by position and then calls `_create_from_row`, which is what
the drag and the button both use directly. Both are leftovers from an earlier
drag that carried a list index instead of the row. UPD-M4 did not remove them,
under the standing rule: a feature change does not silently sweep adjacent
code. They are harmless but they describe a drag the screen no longer has, and
an index-based lookup is the kind of thing a later edit reaches for. Removing
both is a two-line deletion with no test to change.
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Technical Debt

**Title:** UPD-A8 - weekly_items.py imports tkinter and never uses it
**Description:** `import tkinter as tk`
(`src/getmoredone/screens/weekly_items.py:10`) has no `tk.` reference left in
the file - grep returns the import and nothing else. It was already unused
before UPD-M5: the screen's own splitter and drag used `winfo_*` calls on
CustomTkinter widgets, not the `tkinter` namespace. UPD-M5 did not remove it,
under the standing rule that a feature change does not silently sweep adjacent
code. A one-line deletion with no test to change; the only reason to keep it is
that a later edit in this file may want it, which is not a reason.
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

## Adjacent issues — APE Week Assignment / APE Week Actions (AWA, 2026-11-07)

Found while reading the surrounding code for the AWA batch, recorded under the
standing rule rather than fixed in a sweeping diff. Full text, with the line
numbers and the reasoning, in `docs/spec_2026-11-07_ape_week_actions.md` §7.
One of the five, AWA-A5, was fixed in that batch instead of recorded, because
it made the meta test suite red and blocked verification.

### 2026-11-07 - Type: Bug

**Title:** AWA-A1 - APE Week Assignment's Add Action Item writes the wrong link column
**Description:** `screens/weekly_items.py:442` sets `parent_id` and leaves
`weekly_tactic_id` NULL, against `weekly_tactic_migrations.py:135`, which
exists to keep the two apart, and against `tactic_id_of`
(`weekly_tactic.py:144`), the predicate WT-M3.D.1 names as the single
authority. That one button is why the demo database's only tactic child is
linked by `parent_id`. The new APE Week Actions tab's own Add button writes
`weekly_tactic_id`, so the two buttons on two tabs now disagree in a way a user
can see. Nothing is lost today, because
`get_action_items_for_weekly_tactic` reads both columns. The spec recommends
setting both columns on create — one line plus a test. It was left out because
it is beyond what was asked and is the user's call.
**Priority:** Medium
**Effort:** Small

### 2026-11-07 - Type: Bug

**Title:** AWA-A4 - the APE Week Actions panel inherits Today's pin, and the pin is shared
**Description:** `create_item_row` binds the drag grip to `_start_pin_drag` /
`_finish_pin_drag` (`today.py:541-542`), which write
`action_items.today_pin_rank` — the column the Today screen orders by.
Inherited unchanged, as AWA-M5.3 requires, dragging a row to the top of the new
panel also floats it to the top of Today. Found after implementation, by
reading the inherited row builder, not by a test. Either fix — suppressing the
grip on this panel, or giving the panel its own rank column — is a behaviour
change beyond what the tab was asked to do, so neither was made.
**Priority:** Medium
**Effort:** Small

### 2026-11-07 - Type: Refactor

**Title:** AWA-A3 - three readers disagree about what a Weekly Tactic's child is
**Description:** `weekly_tactic_maintenance._child_count` (line 278) already
reads both link columns while `tactic_of` reads one. AWA-M2 adds a third
reader, matching `_child_count`. Consolidating all three onto one helper is the
right end state and is larger than the AWA feature was.

**Mostly resolved 2026-11-07** (`8a324cb`), after the AWA sweep raised the same
duplication as a high finding: the two *SQL* readers now share
`weekly_tactic.LINK_PREDICATE_SQL`, and they had already drifted - `_child_count`
lacked the `item_type != 'week'` exclusion, so the dedupe chose which duplicate
tactic survived by counting a nested tactic as a child. What this entry recorded
as a Low refactor was, by then, deciding which rows a delete kept. The guard test
could not see it: it scanned `screens/` and `vps_manager.py` only.

What remains is the object-level reader: `tactic_of` answers "is this item
week-filed" from `weekly_tactic_id` alone, which WT-INV6 depends on, and so still
returns None for a `parent_id`-only child. That is AWA-A1's subject, not this
one. Closing this entry means fixing AWA-A1.
**Priority:** Low
**Effort:** Low (what is left)

### 2026-11-07 - Type: Cleanup

**Title:** AWA-A2 - a second "APE Weekly" label survives in dead code
**Description:** `screens/vision_planning.py:186` captions a placeholder tab
`"APE Weekly"`. `VisionPlanningScreen` is reachable only through
`app.show_vision_planning`, which no sidebar entry calls. Renaming the label is
harmless; leaving it means a grep for "APE Weekly" still hits. The real
question is whether `vision_planning.py` should exist at all — it is a whole
screen of placeholders behind an unreachable entry point. Decide that, rather
than renaming a label inside it.
**Priority:** Low
**Effort:** Small

## Reported from the running screen — Plan / Day Plan (2026-11-07)

Four faults reported by the user after the PD-* batch shipped. **Recorded, not
investigated**: the descriptions below are the report, not a diagnosis. Nothing
here has been reproduced, read in the code, or confirmed against a running app
by this session.

**All four are addressed by PD-M11** (`docs/unused-docs/implementation_plan_2026-11-06_plan_day_controls.md`),
on 2026-11-07, pending the on-screen check that is PD-M11.8. The first three
turned out to be one cause and not the one PD-M10 treated: the panes were
rebuilt by lifting the scroll frame out of the grid, which unmaps the canvas
the rows are drawn in and leaves its window width and scrollregion to
`<Configure>` handlers that an idle flush does not run. They are rebuilt in
place now. The second report had a cause of its own as well - the two ends of
the day were rows of the scrolling grid, so **Later** sat below the bottom of
a pane too short for eighteen half hours - and the fourth is built as the
autoscroll (PD-M11.5). Leave these entries here until the running app says
they are gone.

### 2026-11-07 - Type: Bug

**Title:** Moving a Day Block leaves a blank panel until the mouse leaves it
**Description:** Moving a block on the Day Plan produces a blank panel. It
fills in as soon as the mouse moves outside the panel area.
**Priority:** High
**Effort:** Unknown
**Notes:** Reads like the repaint class the PD-* batch set out to fix — a pane
re-gridded inside an event callback that Tk does not draw until the next
mouse motion over the window. That batch added `_flush_redraw` for exactly
that shape, so either a path was missed or the fix does not cover the move
path. First thing to check: whether the move path calls the flush at all.

### 2026-11-07 - Type: Bug

**Title:** An item cannot be moved into the early or late extended sections
**Description:** Dragging an item into the early or late extended section of
the day does not drop it there.
**Priority:** High
**Effort:** Unknown

### 2026-11-07 - Type: Bug

**Title:** "Schedule anyway" on a non-work day does nothing
**Description:** Scheduling on a non-work day raises the confirmation message,
but answering "schedule anyway" does not schedule the item — or the item does
not appear afterwards. Which of those two it is has not been established.
**Priority:** High
**Effort:** Unknown
**Notes:** Possibly the same thing as the sweep's PLAUSIBLE low finding
recorded below ("`plan._require_block_day` opens a modal from inside a drop's
`after_idle`"): the permission is recorded against one read of
`self.selected_date` and the caller reads it again after the modal returns.
That finding was left unfixed because neither review pass could drive a date
change through Tk's modal grab and there was no demonstrated misbehaviour to
test against. **This report may be that demonstration.** Unverified — do not
treat the two as the same bug until one reproduction shows it.

### 2026-11-07 - Type: Enhancement

**Title:** The Day Plan does not scroll while dragging an item past its edge
**Description:** Dragging an item up or down towards an area that is off
screen should scroll the Day Plan window to follow it. It does not, so an
item cannot be dragged to a time that is not already visible.
**Priority:** Medium
**Effort:** Unknown


## Adjacent issues from the PD-M12 batch (2026-11-07)

### 2026-11-07 - Type: Bug

**Title:** The Scheduler asks through the platform's dialog inside a drag release
**Description:** `drag_schedule.py::on_drag_release` calls `_drop_onto_project`
directly, which calls `messagebox.showinfo` for a dragged Weekly Tactic and
`confirm_exclusive_relink` (→ `messagebox.askyesno` in
`project_link_notice.py`) before filing items under a project. That is the same
call from the same kind of place as the fault PD-M12 fixed on the Plan screen:
on macOS `tk_messageBox` raised `_tkinter.TclError` with no message when it was
opened from the idle callback following a drag release, and here it is opened
from inside the release handler itself. If it fails the same way, the
exception leaves the Tk callback and the drop files nothing and says nothing.
**Priority:** High if it reproduces - a silent no-op on a write gesture
**Effort:** Small - take the modal off that release path the way PD-M13 did:
file the link, say what happened where the screen already reports, and wrap any
question that remains in `try/except tk.TclError` so a dialog that fails cannot
take the gesture with it. **Not** by swapping in an in-app toplevel: PD-M12 tried
that on the Plan screen and it hung the application, and `confirm_dialog.py` is
deleted.
**Notes:** Not fixed with PD-M12 or PD-M13. It has not been reported and it is a
second screen's confirmation UI; fixing it there before anyone has walked the
Plan screen's own remedy is how one unverified fix becomes two - and the first
two remedies here were both wrong on screen. **Worth a walk before anything
else:** drag an item onto a project on the Scheduler screen and see whether it
files. The other
twenty `messagebox` call sites in the app, Clear Day on the Plan screen
included, are reached from a button or a menu and are not in this class.

### 2026-11-07 - Type: Test quality

**Title:** The messagebox stub cannot fail, so no test can see a dialog that does
**Description:** `conftest.py::_messageboxes_never_block` replaces every
function in `tkinter.messagebox`, session-wide, with a recorder that returns a
canned answer and cannot raise. It exists for a good reason - a real modal
blocks a test run until someone clicks it - but it means the only call that
fails in the running app is a call no test makes. PD-M12 is what that costs: a
`TclError` out of `askyesno` killed two write paths on every weekend day, while
the PD-M7 test (then named `test_pdm7_a_non_work_day_asks_before_scheduling`,
now `::test_pdm132_a_button_still_asks_on_a_non_work_day`) passed throughout,
asserting the block was written by code that could not ask the question at all.
PD-M13 is what the second half costs: nothing in the suite could show that an
in-app toplevel never returns from that callback either, because conftest
withdraws every window, so the second remedy shipped as unseen as the first.
**Priority:** Medium
**Effort:** Medium - a decision, then a sweep
**Notes:** Two ways out, and they are not exclusive. (a) Where a dialog gates a
write, call it through an app-owned seam like `widgets/confirm_dialog`, which a
test can make raise - PD-M12 does this for one guard. (b) Give the recorder a
way to be told to raise, and use it in at least one test per gated write path,
so the failure mode is exercised somewhere. The general lesson belongs in
`~/.claude/standards/learnings.md`: a stub installed for safety that cannot
reproduce the failure it stands in for turns the untested path into an
*invisible* one, which is P25 one layer down.

## Adjacent issue from the PD-M11 batch (2026-11-07)

### 2026-11-07 - Type: Bug

**Title:** Six other screens rebuild a scrolling pane by taking it out of the grid
**Description:** `today.py`, `upcoming.py`, `all_items.py`, `completed.py`,
`hierarchical.py` and `vps_planning.py` all call `grid_remove()` on a
`CTkScrollableFrame`, destroy and rebuild its rows, and put it back in a
`finally`. All six come from `9525d94` ("Fix GUI flickering by preventing
intermediate renders during screen refresh"), which is where the Plan screen
got the pattern too. Taking that frame out of the grid unmaps the canvas its
rows are drawn in, and the width of the canvas window and the scrollregion are
both restored by `<Configure>` handlers that run only when the event queue is
next serviced - which is the blank-pane defect PD-M11.1 fixed on the Plan
screen.
**Priority:** Medium
**Effort:** Medium - six screens, each with its own on-screen contract
**Notes:** Not fixed with PD-M11. None of the six was reported, and six
screens' worth of UI regression is not a change to make alongside a fix to a
seventh. The fix is mechanical and identical in each: delete the
`grid_info()`/`grid_remove()` pair and the `grid(**grid_info)` in the
`finally`, keep the destroy-and-rebuild. What it needs is a walk of each
screen afterwards, which is the actual cost.

### 2026-11-07 - Type: Documentation

**Title:** The documentation index lists two spec docs and none of the plans
**Description:** `docs/DOCUMENTATION_INDEX.md` names
`docs/spec_2026-11-07_ape_period_consistency.md` and
`docs/spec_2026-11-07_ape_week_actions.md` individually, and covers handoff
notes with one generic `docs/unused-docs/changes/` entry. The seventeen
`implementation_plan_*.md` files, the other seven `spec_*.md` files and the five
`spec_coverage*.md` files are not listed anywhere in it, including
`implementation_plan_2026-11-06_plan_day_controls.md`, which is the plan of
record for PD-M1 - PD-M11.
**Priority:** Low
**Effort:** Small - one pass over `ls docs/`, plus the meta test
**Notes:** Found while updating docs for PD-M11; the gap predates that batch and
no test enforces the index, so nothing failed. The global rule is that where a
repo keeps a documentation index every document is listed in it and a test
enforces that - this repo has the index and not the test. Worth doing as one
docs pass with a meta test that compares `docs/*.md` against the index, rather
than one entry at a time.

## Adjacent issues from the plan day-controls batch (2026-11-06)

Found while building PD-M2 and PD-M3, not introduced by either, and not fixed
in the batch that found them — rule 10.

- **`+ Break` and `+ Buffer` place at the first box that is not full.** Both
  toolbar buttons use `first_free_slot`, so a 30m break lands in the earliest
  box with fewer than four tasks in it — on a planned day that is on top of
  work, not in an empty half hour. PD-M3's AutoLoad uses `first_clear_slot`
  instead. Low, and a decision rather than a defect: a break deliberately
  dropped beside a task is a thing people do, and it is not obvious the button
  should refuse to do what a drag can. Worth settling before the two paths
  drift further apart.
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

## Weekly Tactic scheduling — carried forward

### 2026-08-18 - Type: Bug

**Title:** A week item that cannot snap to its week start is never repaired
**Description:** `normalize_week_item_starts` (`weekly_tactic_maintenance.py`) snaps
every week item onto its week boundary at start-up. On the very first run the
WT-INV5 unique index does not exist yet, so a collision simply happens and the
dedupe merges the pair. On every run afterwards the index does exist, the UPDATE
raises, the row is left mid-week, and it is counted in the returned `collisions`
list. `dedupe_weekly_tactics` will never see it, because it groups by the raw
`start_date` the row still holds — so the WT-INV5 violation is permanent and its
only trace is a warning in `weekly_tactic_debug.log`.
**Priority:** Medium
**Effort:** Small
**Status:** [x] **Done 2026-08-19 (BC2).** The stated cause had moved on: the
repair *does* consume `week_start_normalization["collisions"]`, but only to mark
that tactic's children unrepairable. The real gap was that
`find_duplicate_weekly_tactics` grouped by the raw `start_date`, so a tactic left
mid-week formed a group of one and was never merged. It now groups by the *week*
each row belongs to, and the survivor is snapped onto its week start once the
duplicate holding that date is gone. Tests:
`tests/test_weekly_tactic_dedupe.py::test_bc2_*` (three, including a dirty-state
and an idempotency case).
**Notes:** Found by the learning-qa sweep of commit 55f1b36 (finding 8, P1/P3 — a
repairable condition recorded as a terminal one).

### 2026-08-18 - Type: Enhancement

**Title:** `RescheduleDialog` has no caller in `src/`
**Description:** `src/getmoredone/screens/reschedule_dialog.py` defines
`RescheduleDialog`, but nothing in `src/` constructs it — the only references are
the class statement itself and two tests. The live "push to next day" path
(`today.py`, `upcoming.py`) calls `reschedule_item` directly instead. So a
dialog that offers a reason field and a date picker is unreachable from the app.
**Priority:** Low
**Effort:** Small
**Notes:** Found by the learning-qa sweep of ca802ff (finding 6, P21 —
built-but-not-wired). Either wire it to a Reschedule action or delete it; a
surface reachable only from a test inflates the WT-M6 coverage claim. Left alone
in this change because it is out of scope for the weekly-tactic spec, and it was
already like this before.

### SAG-A4 — one assertion couples an exit code to an outcome-name spelling (low)

`tests/test_docs_sync_rule.py` decides which side of `gate.PASSING` an outcome
should fall on by testing `expected.startswith(("pass", "no-"))` — that is, by
the spelling of the fixture's own outcome name. Renaming an outcome's *value*
silently changes which branch the assertion exercises rather than failing. A
per-fixture expectation would be independent of the spelling.

The gap is also wider than the title: **no test asserts `main`'s exit code at
all.** `return 0 if code in PASSING else 1` is the line a CI step would act on,
and only `verdict`'s outcome name is asserted.

Filed 2026-11-09 by the first cold pass over the SAG batch, which described this
as an assertion on `main`'s exit code; the second pass measured that there is no
such assertion.

**Priority:** Low
**Effort:** Small

### SAG-A5 — `run()` puts a literal backslash-n in its error message (low)

`tools/agents/check_docs_sync.py::run` raises
`RuntimeError(f"Command failed: {' '.join(cmd)}\\n{result.stderr}")` — an
escaped backslash in a plain (non-raw) string, so the message carries the two
characters `\n` instead of a newline and the git error runs on from the command
line. It is the class `CLAUDE.md`'s "backslash sequences in embedded code
strings" rule covers, arriving the other way round. The message is now read by
`SAG-M2.3`'s skip line, so it is user-facing.

**Priority:** Low
**Effort:** Small

### SAG-A6 — a dead `docs/unused-docs/changes/` clause in the docs check (low)

`verdict` computes `docs_changed` as `path.startswith(DOC_PREFIXES) or path in
DOC_FILES or path.startswith("docs/unused-docs/changes/")`. `DOC_PREFIXES` is `("docs/",)`,
so the third clause can never be the one that matters: every
`docs/unused-docs/changes/…` path already satisfies the first. A handoff note alone
**does** satisfy the docs requirement, and `tests/test_docs_sync_rule.py`'s
fixture `(("src/getmoredone/db_manager.py", "docs/unused-docs/changes/…md"), "pass")`
asserts exactly that — so the clause is dead, and the behaviour it looks like it
adds is the behaviour the rule already has. Whether that is the right rule is a
separate question from whether the clause is reachable; this item is only about
the clause.

Filed 2026-11-09 by the first cold pass over the SAG batch, which said the
fixtures prove a note alone does *not* satisfy the requirement; they prove the
opposite, corrected by the second pass. Deleting the clause is a
behaviour-preserving edit; it is filed rather than done because the batch's rule
is that below-medium findings are not fixed in-loop.

**Priority:** Low
**Effort:** Small

### SAG-A10 — `test_sagm23` cannot tell an unreadable range from a missing git (low)

`tests/test_docs_sync_rule.py` asserts that the tool's output contains
"skipped" when the range cannot be read. It would also pass if git were absent
or the working directory were not a repository, so the test does not establish
that the *range* is what failed. Asserting on the message's command text as
well would separate the two.

Filed 2026-11-09 by the third cold pass over the SAG batch.

**Priority:** Low
**Effort:** Small

### SAG-A11 — `run()` has no timeout on its subprocess (low, P5)

`tools/agents/check_docs_sync.py::run` calls `subprocess.run` with no
`timeout`, so a hung `git diff` hangs the check. `~/.claude/standards/learnings.md`
P5 is the rule — timeout, retry, backoff on every external call — and the
global rules say to fix a class rather than an instance, so the sibling calls in
`tools/agents/` should be done in the same change.

Adjacent, found 2026-11-09 by the third cold pass over the SAG batch and not
changed by it (global rule 10). `SAG-A5` is the other defect in the same
function.

**Priority:** Low
**Effort:** Small

## Quick Add Template

```markdown
### [Date] - [Type: Bug/Feature/Enhancement]

**Title:**
**Description:**
**Priority:** [Low/Medium/High/Critical]
**Effort:** [Small/Medium/Large]
**Notes:**
```

### SAG-A18 — `tests/` itself is outside the traceability scan, undocumented (low)

`SCANNED` covers `src`, `tools`, `conftest.py` and four document globs, but not
`tests/*.py`, which holds 118 path-form references of its own. The exclusion is
load-bearing and deliberate — ten of those references are fictional fixtures
(`tests/test_a.py`, `tests/test_thing.py`, and this guard's own comment citing
`tests/test_column_resize.py::test_updf13_` as the example of a dead citation),
so adding the arm would go red on the guard's own prose. Unlike
`COVERAGE_WITHOUT_PATHS`, nothing says so: a reader sees four document families
scanned and a test suite that is not. Either document the exclusion where
`SCANNED` is defined, or add the arm with a named exemption for the fixtures.
Measured by the sixth cold pass, which also confirmed all 118 resolve today
except the deliberate fixtures.

### SBN-A1 — a bare `::name` citation resolves against the whole suite, not against its own file (medium)

`tests/test_traceability_refs.py`'s bare arm (`SBN-M1`) accepts a name defined
anywhere under `tests/`. The path arm resolves inside the file the citation
names, which is the stronger check. So a row citing `` `::test_x` `` under a
table that named `tests/test_a.py` passes even when `test_x` lives in
`tests/test_z.py` and has nothing to do with the criterion — and the batch's
own plan demonstrated it: `SBN-M2.1` cited the path arm's test while meaning
the bare arm's, and the guard was green on it.

Not fixed because the anchoring rule was measured and rejected: see the closed
`SAG-A17` above and §1.2 of
`docs/unused-docs/implementation_plan_2026-11-09_bare_name_citations.md`. The honest
options are a per-document convention (declare the file a table's bare names
belong to, in the document) or leaving it as the weaker check it is. The first
is a documentation change across 34 documents, not a guard change.

### SBN-A2 — bare `::name` citations that name a `src/` symbol are read by nothing (low)

68 bare names in the scanned families are not test names — `::update_action_item`,
`::export_day`, `::_build_service` — almost all of them continuing a
`src/…py::func` citation in a neighbouring table cell, and 51 of them resolve
against nothing under `tests/`, which is why they are excluded by `_TESTISH`
rather than merely unresolved. Checking them means resolving against `src/`,
which `tests/test_doc_status_claims.py::test_sstm5_every_implementation_reference_resolves`
already does for the Implementation column of the coverage family only. The arm
to add is that resolver over the bare form, in all four families.

### SBN-A3 — PD-M14.4 and PD-M14.7 have no automated test, under any name (medium)

Found by repairing `docs/unused-docs/implementation_plan_2026-11-08_day_hours_are_a_template.md`:
ten of its criteria name tests that were never written. Measured per criterion
after the cold pass corrected an over-broad first claim:

- **PD-M14.5's first bullet** and **PD-M14.3's break/buffer clause** *are*
  covered, by `tests/test_plan_screen.py::test_pdm34_autoload_does_not_run_past_the_day_end`,
  `::test_pdm36_a_full_day_writes_nothing` and
  `::test_pdm8_clear_day_leaves_breaks_and_buffers`.
- **PD-M14.3's span clause** (the day still starts at −1) is not.
- **PD-M14.4** and **PD-M14.7** are not covered at all. There is no production
  caller of `shift_all_slots`, and no repair pass exists in `src/`: `grep -rn
  "def .*repair" src/` finds only VPS and weekly-tactic ones. So the question
  is not only "write the test" but whether the criteria describe code that was
  ever built.

A product judgement, which is why it is filed rather than answered.

### SBN-A4 — the guard asserts that bare citations keep existing, so improving a family turns it red (low)

`::test_this_guard_can_actually_fire` asserts membership per family: at least
one bare `::name` citation must be found in the coverage family, the plans, the
dated specs and the handoff notes. That is deliberate — an exact count goes red
on every batch and a floor is forbidden here — but it means a future batch that
converts one family's bare citations to the path form, which is the stronger
form, fails the guard for having improved the documents. The fix is to assert
the arm's *mechanism* against a fixture (a document the test writes) rather
than against the repo's current prose, the same move the sixth SAG cold pass
made for the resolver probe.

### SBN-A5 — T5.3's raising-handler case is not covered (low)

`docs/unused-docs/implementation_plan_2026-08-25_timer_session_endings.md`'s T5.3 is
"topmost restored even when the modal's handler **raises**". The test that
carries `T5.3` asserts the other half (a parent that was not topmost is left
alone), and no test in `tests/test_timer_session_endings.py` raises inside a
modal's handler and then checks the restore — `grep -n raise` over that file
finds none. The plan said `::test_t57_an_unbalanced_resume_does_not_break_the_next_modal`
covered it; that test drives a stray resume, which is the depth counter. The
document now says the case is uncovered. The test is a few lines of work: open
a modal whose handler raises, assert topmost comes back and the depth returns
to zero.

### SBN-A7 — two alternatives in `_BARE`'s lookbehind are unexercised (low)

`_BARE = re.compile(r"(?<![\w.)])::(\w+)")`. Measured over the scanned
documents: of 1930 `::name` tokens, the character before is a backtick (1098),
the `y` of `.py` or another name character (794), an ellipsis (37) or a line
start — `)` never occurs and the one `.` case is excluded by `_TESTISH` anyway.
The `_FULL` mask was deleted in the same batch on exactly this ground, that it
changed no outcome; these two alternatives were kept. Either drop them or add
the fixture that exercises them.

### GSF-A5 — `BACKLOG.md` says a file under `src/getmoredone/screens/` defines a function, and no such file is tracked (medium)

`grep -n 'reschedule_dialog.py' BACKLOG.md` finds two entries, one of which
says in the present tense that `src/getmoredone/screens/reschedule_dialog.py`
*defines* a function. `git ls-files` finds no file of that name anywhere, and
none named `confirm_dialog.py` either, which a third entry also names. Found by
the GSF class measurement, which counted 55 unresolvable path citations in the
live documents and found this to be the one genuine defect among the 25
distinct names. Either the file was renamed and these entries were not, or the
entries describe work that was never built; the fix needs those items read
rather than their citations rewritten, which is why it is filed and not
repaired here.

### MAW-A1 — `.agents/` now holds only a template (low)

The three role prompts are deleted, so `.agents/prompts/` is gone and
`.agents/` holds nothing but `templates/handoff-note.md`, which
`tests/test_repo_hygiene.py::test_mawm12_the_retired_agent_apparatus_is_absent`
positively requires to stay. Whether a one-file `.agents/` tree is worth
keeping, or the template belongs under `docs/` or `.github/`, is a tidying
question with a guard to update either way. Found while measuring the deletion
set.

### MAW-N1 — `origin/codex/agent-code` still exists on the remote (needs a decision)

The last of the three role branches. Measured 2026-11-09:
`git rev-list --left-right --count main...origin/codex/agent-code` gives
**624 0** and `git merge-base --is-ancestor origin/codex/agent-code main`
succeeds, so it is 624 commits behind `main`, nothing ahead, and every commit
on it is already here. Deleting the ref would lose nothing. Last commit
2026-04-03. Deleting a remote branch is the user's call, not mine, which is why
this is filed as a decision rather than done.

