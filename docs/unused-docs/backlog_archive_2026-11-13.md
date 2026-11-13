# BACKLOG archive — 2026-11-13

Filed out of `BACKLOG.md` by the BSF batch, which worked the items whose entry
named the fix (`docs/unused-docs/implementation_plan_2026-11-13_backlog_small_fixes.md`).
Each item carries its closure under it. This is a filed record. No test reads it.

### ~~LMM-A1 — a block dragged onto an extended slot is refused (medium)~~ — fixed 2026-11-12

Fixed in the PBG sweep, together with a fifth call site the entry below had
claimed was fine. `move_block_to_slot` now passes `day_span=self._grid.span`
to `place_block_at`, and `set_block_length` takes a `day_span` of its own —
it had no such parameter at all, so a right-click resize of any block on a box
the drawn day added was refused `outside_grid` whatever length was asked for,
the one it already had included. Guards:
`tests/test_plan_screen.py::test_pbga8_an_ordinary_block_moves_onto_a_box_the_extended_day_drew`
and `tests/test_time_block_crud.py::test_pbga3_a_block_on_a_drawn_box_can_be_resized`.

**The completeness claim in the original entry was wrong**, and that is the
part worth keeping. It said the four other call sites got it right and "this
one is the omission". There were three more: `set_block_length` above,
`add_padding_block` (`plan.py:1316`) and AutoLoad (`plan.py:1946`). The last
two are deliberate — `template_span`'s docstring names the template as what
AutoLoad and the break button are allowed to fill — but the entry drew no line
between a deliberate omission and a defective one, which is what the next
reader would have acted on. The false docstring on
`_refuse_unless_it_fits` that made every omission look safe is corrected in
the same change.

**Closed:** Fixed 2026-11-12 (PBG sweep); the entry had been struck through and left in place.

### LMM-A2 — nothing refuses a second LUNCH block on one date (low)

`lunch_window` (`time_block_layout.py:572`) walks the date's blocks and
`return`s on the first `LUNCH` it finds. A second one is not an error, it is
simply unread: it keeps its slot, it draws, and it shades nothing. No write
path refuses it either, so a duplicate can only arrive from a bug elsewhere or
from a hand-edited database — which is why this is low rather than medium.

Fix when touched: either refuse the second write where lunch blocks are
created, or have `lunch_window` surface the duplicate rather than silently
taking the first (the "surface, never silently drop" rule, P2/P9). A silent
`return` on the first of several is the shape that hides the state.

**Closed:** Fixed 2026-11-13, BSF-M6: `add_block_at`, the only insert of a time block, refuses a second LUNCH block on a date (`SlotRefusal.LUNCH_EXISTS`).

### CGH-A1 — the `-topmost` silencer only inspects the first attribute (low)

`conftest.py`'s wrapper drops a `-topmost` write only when it is the FIRST
argument:

```python
if args and args[0] == "-topmost" and len(args) > 1:
    return None
```

`window.attributes("-alpha", 0.0, "-topmost", True)` is one call that sets
both, and it would go straight through to Tk — the hole the wrapper exists to
close, in the one shape it does not look at. An un-silenced `-topmost` during
a run forces window-server round-trips and has beachballed this machine.

Latent, not live: all six call sites under `src/` are single-attribute
(`grep -rn "attributes(" src/` → `"-topmost", True` or `'-topmost', True`),
so nothing produces the multi-attribute form today. `_RecordingTk` in
`tests/test_tk_offscreen.py` already recognises `-topmost` anywhere in the
call, so the test spy is stricter than the thing it tests.

Fix when touched: scan the argument pairs rather than `args[0]`, and drop the
`-topmost` pair while passing the rest through. Found by the third cold pass
of the CGH batch, which was reviewing the spy, not the wrapper.

**Closed:** Fixed 2026-11-13, BSF-M4: the silencer drops a `-topmost` pair anywhere in the call, and the Python 3.13 `topmost=` keyword.

### CE-A2 — `_say` prints to stdout from a GUI app (low)

`src/getmoredone/google_calendar.py::_say` writes status lines to stdout.
Same family as the fixed defect where a status `print` inside a credential
`try` discarded a valid token when the stdout write failed: a packaged app's
stdout is not guaranteed writable, and a print in a `try` makes the failure
look like the thing being tried. The export path calls it through the shared
helpers.

**Priority:** Low
**Effort:** Small

**Closed:** Closed 2026-11-13 without code: the console is the manual sign-in's interface (it ends in `input()`), and `_say` already cannot abort its caller.

### SCV-A1 — `interpolate_hex_color` slices into `int(…, 16)` with no guard (low)

`screens/drag_schedule_support.py:109-110` reads both endpoints of its gradient
as `int(s[0:2], 16)` with nothing checking them first, which is the third copy
of the parse `SCV-M1` removed from the other two. Not on the stored-colour
path — its only caller is the gradient in its own module, over theme colours —
so it is not what `LRR-A1` named, and fixing it in the SCV batch would have
been a sweep of a module nobody asked about. It will behave exactly as
`_derive_subsegment_color` did the day something hands it a stored colour.
`tests/test_segment_colour_validation.py::test_scvm11_no_hand_rolled_hex_validator_survives`
counts it, so it cannot multiply unnoticed.

**Priority:** Low
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M5: `interpolate_hex_color` parses through `color_contrast`.

### SCV-A3 — `_text_color_for_background` misreads the `int(…, 16)` family (low)

`color_contrast.py`'s private `_text_color_for_background` slices and parses
its argument without going through `_HEX_COLOR_RE`, so it is the third member
of the family `SCV-M1` removed from the other two. The SCV plan's §5 recorded
it as "correct already", which is wrong: it reads `#+12345` as `#0B368D` by the
same misread slice `_derive_subsegment_color` did, and answers for the wrong
background.

Left as low because the consequence is cosmetic and bounded — one text colour
on one widget, no raise and no stored value — and because every caller now
reaches it through a normalised colour, so the misread needs a new caller to
become visible. Fixing it inside the SCV batch would have meant touching the
authority module's maths for a case no live path produces.

**Priority:** Low
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M5: the weekly tactic dialog's text colour parses through `color_contrast`.

### CI-A1 — the apt step has no retry, so a mirror outage is a red build (medium)

`.github/workflows/tests.yml:47-48` runs `sudo apt-get update` then
`sudo apt-get install -y xvfb python3-tk` with nothing around them. On
2026-11-11 all three matrix jobs (3.11, 3.12, 3.13) died there with
`Temporary failure resolving 'security.ubuntu.com'` and
`E: Failed to fetch .../python3-tk_3.14.3-0ubuntu2_amd64v3.deb`, exit code
100, before pytest ran at all. A re-run four minutes later failed identically.
Twelve minutes of red that said nothing about the commit.

This is P1 and global rule 5 in the workflow rather than in `src/`: a
retryable network failure given a terminal result, on an external call with no
timeout, retry or backoff. The fix is retry options on the apt call
(`-o Acquire::Retries=3`, or a retry action around the step), possibly with
the two packages cached.

Not done in the SCV batch that found it: it is a change to the CI contract,
which `tests/test_ci_contract.py` asserts on, and that wants a batch of its
own rather than a workflow edit tacked onto the end of one. Found by two
sessions independently on 2026-11-11.

**Priority:** Medium
**Effort:** Low

**Closed:** Fixed 2026-11-13, BSF-M7: the apt calls retry in a loop inside a 15-minute step limit.

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

**Closed:** Fixed 2026-11-13, BSF-M1: both deleted.

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

**Closed:** Fixed 2026-11-13, BSF-M2: the import deleted.

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

**Closed:** Fixed 2026-11-13, BSF-M3.

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

**Closed:** Moot 2026-11-13: the clause was already replaced by `FILED_PREFIX`, which excludes filed records.

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

**Closed:** Fixed 2026-11-13, BSF-M3: a 60-second timeout, reported as skipped. The only subprocess call in `tools/agents/`.

## Closed by the PRC batch (priority score cell, 2026-11-13)

### PBG-A1 — `PRIORITY_BANDS` has no reader in `src/` (low)

PBG-M5 deleted `priority_band` and the three colour tables it fed, because the
Plan screen was their only user and it draws the priority *level* badge now.
`PRIORITY_BANDS` (`time_block_layout.py:66`) survived: it is the arithmetic,
and `tests/test_priority_floor_and_cap.py:231` measures the score's cap against
the top threshold, as does
`test_priority_level_colors.py::test_plcm14_a_big_score_is_not_a_critical_level`.
`UNSCORED_BAND` did not — the PBG sweep deleted it, because `priority_band`
was its only reader and nothing was left to use the name.

So `PRIORITY_BANDS` is not dead, but its only readers are tests. Either is
defensible — it is a true statement about `priority_score` whether or not
anything colours it — and the decision is worth making deliberately rather
than by default.

Fix when touched: either delete it and rewrite those two tests against
`PriorityFactors.MAX_SCORE`, or keep it and say in the comment that it is a
scale with no renderer. The comment says the second today.

**Closed:** Closed 2026-11-13 as deliberate: the comment on `PRIORITY_BANDS` already says it is a scale with no renderer, which is the second option the entry offered.

### PBG-A10 — a pre-cap score is wider than the cell reserved for it (low)

`priority_score` is capped at `PriorityFactors.MAX_SCORE`, but rows written
before PRI-M2 still hold the raw product, up to 102400. `P:102400` is 59px of
text and 71px with the badge's corner-radius padding, against the 60px the
Plan row and the five list screens each reserve — so such a row overflows its
column and takes the width out of its neighbour. Pre-existing on the five list
screens; the Plan badge inherits it.

Fix when touched: either migrate the stored scores to the cap once, which is
the only way the displayed number stops disagreeing with what the app can
produce, or render `min(score, MAX_SCORE)` and say in the guide that it is
capped.

**Closed:** Fixed 2026-11-13, PRC-M1: a migration sets any stored score above `PriorityFactors.MAX_SCORE` to the cap, which is what recomputing it gives.

### PCC-A1 — the parent/child pickers draw an uncoloured priority score (low)

`screens/item_editor_dialogs.py:257` and `:476` draw a `P:{priority_score}`
label under a `"Priority"` header with no colour at all. They are the only
other place in the app where a priority score appears in a list, so after PCC
the same number is colour-coded on the five list screens and plain here.

Left alone deliberately: the user named the list screens, and a dialog that has
never been coloured is not the red PCC replaced. Whether a picker dialog should
carry the scheme at all is a design question, not a defect.

Fix when touched: call `priority_levels.level_cell_fill(settings, item)` and
pass `fill`/`text_color` to the label, as the five row builders now do. The
authority already derives legible text for any colour the user picks, so there
is nothing to work out — only the decision to do it.

The other finding, the score column's width (`width=60` in four screens,
`width=80` in All Items), is already open as `PRI-A2` and is not filed twice.

**Closed:** Fixed 2026-11-13, PRC-M3: both pickers draw the cell through `build_level_cell` with `level_cell_fill`.

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

**Closed:** Fixed 2026-11-13, PRC-M2: `SCORE_CELL_WIDTH_PX` and `ALL_ITEMS_SCORE_CELL_WIDTH_PX` in `screens/priority_cell.py`; the Plan badge uses the first.

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

**Closed:** Fixed 2026-11-13, PRC-M2: All Items writes `P:n` through `score_text`, as the other four do.

### PRI-A4 — demo data bypasses the defaults and the floor (low — a note, not a defect)

`src/getmoredone/demo_data.py` calls `create_action_item(..., apply_defaults=False)`
at both of its two call sites and hard-codes its factors, so a demo database
demonstrates neither Defaults nor the floor. Correct as designed; filed because
it is why `python tools/create_demo_data.py` will not show this feature, which
is worth knowing before anyone tests it that way.

**Priority:** Low
**Effort:** Low

**Closed:** Closed 2026-11-13 as a note: correct as designed, and the entry itself says so.

## Adjacent issues — the Day Plan's lunch and drag moves (LMM, filed 2026-11-12)

Found while building the lunch-block move fix (`3adfc91`) and not fixed, under
global rule 10. None of the three was reproduced on the running screen, and
they do not rest on the same evidence. LMM-A1's refusal was executed, not only
read: `can_place` called with `day_span` omitted and a slot outside the
template span returns `outside_grid`, so its mechanism is observed and only the
screen-level sequence -- extend the day, drag a block onto the new outer box --
was predicted. LMM-A1 and LMM-A2 are fixed and filed in
`docs/unused-docs/backlog_archive_2026-11-13.md`. LMM-A3 was located by
reading and not executed.

### LMM-A3 — the Day Settings lunch chip cannot be dropped on Earlier/Later (low)

The `kind == "lunch"` branch of `on_drag_release` (`screens/plan.py:2766`)
handles `target` and `pointer_over_day()` and has no `edge` case. The two
branches above it both do — `item` at `plan.py:2736` and `block` at `:2753` —
so dropping the lunch chip past either end of the day silently does nothing,
while the same gesture with an Action Item or a scheduled block extends the
day.

Whether lunch *should* be able to extend the day is a product question, not
only a defect: a lunch outside the drawn day is arguably meaningless. But the
present behaviour answers it by doing nothing at all and saying nothing, which
is the one answer a user cannot read.

**Closed:** LM3-M1 (2026-11-13): the lunch chip dropped on an edge now says why nothing happened; lunch still does not extend the day.

## Adjacent issues — APE Week Assignment / APE Week Actions (AWA, 2026-11-07)

Found while reading the surrounding code for the AWA batch, recorded under the
standing rule rather than fixed in a sweeping diff. Full text, with the line
numbers and the reasoning, in `docs/spec_2026-11-07_ape_week_actions.md` §7.
One of the five, AWA-A5, was fixed in that batch instead of recorded, because
it made the meta test suite red and blocked verification.

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

**Closed:** AWA2-M1 (2026-11-13): the grip is suppressed on APE Week Actions; no second rank column was added.

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

**Closed:** DRP-M1..M3 (2026-11-13): every dialog on the release path is wrapped in try/except TclError, logs, and writes to a new Scheduler status line; the drag ends in a finally. The relink question stays modal; a refused question writes nothing. Not walked on screen.

## Adjacent issues from the PD-M12 batch (2026-11-07)

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

**Closed:** 2026-11-13. Option (b) in the form the item asked for, per path: every write path that asks from a drag release has a test that makes its dialog raise -- `tests/test_plan_screen.py::test_pdm132_a_question_that_raises_does_not_take_the_gesture`, `::test_pfm15_a_question_that_raises_still_schedules`, `tests/test_project_multi_link.py::test_drpm2_a_refused_dialog_on_a_project_drop_writes_nothing_and_ends_the_drag`, `tests/test_weekly_tactic_surfaces.py::test_drpm3_a_refused_notice_on_a_date_drop_still_refreshes_and_says_so`. Dialogs reached from a button or menu are not in the failure class. The general lesson is `~/.claude/standards/learnings.md` P45.

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

**Closed:** 2026-11-13, accepted as the weaker check it is. The per-document convention would touch 34 documents to tighten a guard over citations, and the anchoring rule was measured and rejected (SAG-A17). The path arm remains the strong form; a writer who wants the check cites with a path.

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

**Closed:** LPR-M1 (2026-11-13): the pair is removed on all six; `git diff -w` is the pair and nothing else. Not walked on screen.

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

**Closed:** 2026-11-13 -- already done (BC2, 2026-08-19); BACKLOG.md holds open work only.

- **`+ Break` and `+ Buffer` place at the first box that is not full.** Both
  toolbar buttons use `first_free_slot`, so a 30m break lands in the earliest
  box with fewer than four tasks in it — on a planned day that is on top of
  work, not in an empty half hour. PD-M3's AutoLoad uses `first_clear_slot`
  instead. Low, and a decision rather than a defect: a break deliberately
  dropped beside a task is a thing people do, and it is not obvious the button
  should refuse to do what a drag can. Worth settling before the two paths
  drift further apart.

**Closed:** PBB-M1 (2026-11-13): settled for an empty half hour first, falling back to room beside work; a drag still places where dropped.

### SCV-A2 — the two segment colour maps hand callers the raw stored value (medium)

`get_segment_color_map` (`vps_manager.py:1394`) and `get_segment_colors_by_id`
(`:1406`) both return `row["color_hex"] or "#334155"`, i.e. whatever the
database holds. The by-name one is the load-bearing half — it feeds
`resolve_segment_color`, and so `_derive_subsegment_color` and `row_fill`.

`SCV-M4` closed the row-fill reader, `SCV-M6.3` closed the accent stripe and
the screens' own `segment_color_utils._normalize_color`, and `SCV-M5` gated
every writer of `segment_descriptions.color_hex`, so a malformed value has to
predate 2026-11-11 to be in there at all and no code path can add one. What is
left is a survey of the maps' *other* readers, which is the work here — not a
normalising wrapper on the maps, which would hide which readers needed one.

**Priority:** Medium
**Effort:** Low

**Closed:** 2026-11-13, surveyed. All 15 reader sites normalise the value (normalize_hex_color directly, or via _chip_color, segment_color_utils._normalize_color or _derive_subsegment_color) before any Tk call or hex_to_rgb; no fix needed. Adjacent, not fixed: item_editor_weekly_tactic_dialog.py passes vision_categories.color_hex to fg_color only stripped (about :274-284). Unreachable while get_vision_categories() rewrites malformed rows before returning them; the one-line guard is _normalize_color, as resolve_chip_colors does. Belongs with UPD-A9.
