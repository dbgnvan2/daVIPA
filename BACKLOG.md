# daVIPA Backlog

Last Updated: 2026-11-08 (WTP-M1 to WTP-M6 made a Weekly Tactic the parent of
the Action Items filed under it in every reader of parenthood, all 38 criteria
built, and added one adjacent issue as WTP-A1 - the shipped-column width test
that enumerates three of the five column sets by hand; UPD-M6 put APE Week
Actions on the shared divider
and chip table, gave it the three lineage filters it never had, and moved the
filter rule and the category chip colour into one owner each rather than a
sixth copy: one adjacent issue is filed as UPD-A9, the five copies left under
`screens/`; PLC-M1 to PLC-M5 made the three priority level colours settable and added five adjacent issues as PLC-A1 to PLC-A5 - the segment-fill text contrast the new priority fill fixes only for itself, two screens that ignore their own segment colour for the row fill, the `P:` chip's hard-coded red, `settings.py`'s length, and this index's own staleness; UPD-M5 moved APE Week Assignment's two panels onto
the shared chip table, splitter and row drag, the last screen in scope: UPD-A6
is resolved in place below, both holdout lists are empty and UPD-M1.5 and
UPD-M2.5 are `done`, and one adjacent issue is filed as UPD-A8, an unused
`import tkinter as tk` in `weekly_items.py`; UPD-M4 moved the three APE/Annual tabs onto the
shared chip table, splitter and row drag: AWA-S5 and AWA-S6 are resolved in
place below, UPD-A6's claim that UPD-M4 would empty the holdout lists is
corrected there - `weekly_items.py` is the last copy and UPD-M5 rewrites it -
and one adjacent issue is filed as UPD-A7, two dead index-based members in
`annual_vision_segments.py`; UPD-M1 added two adjacent issues as UPD-A5 and UPD-A6 - a fifth copy of the splitter in Project Boards, whose clamp was already right where the four consolidated copies were wrong, and the holdout list UPD-M1.5 needs until UPD-M4 empties it; a third cold pass over the AWA re-sweep's fixes added AWA-S9 to AWA-S11, found no high, and showed that half of one low fixed in the previous round was not a defect; the cold re-sweep of the AWA fix commits added its four remaining lows as AWA-S5 to AWA-S8, with its one high, three mediums and one raised low fixed in-loop and one low fixed against the budget with its reason stated there; the AWA sweep's four below-medium findings added as AWA-S1 to AWA-S4, with its one high and five mediums fixed in-loop and AWA-A3 mostly closed by that fix; four adjacent issues from the APE Week Assignment / APE Week Actions batch added, two medium and two low, with a fifth fixed in that batch because it blocked verification; the four Plan / Day Plan faults reported from the running screen are addressed by PD-M11, pending the on-screen check; one adjacent issue from that batch added - the same remove-and-rebuild pattern on six other screens; the APE period-consistency re-sweep's two lows and one adjacent issue added, on top of that sweep's own two lows and two adjacent issues; the third cold pass's three test-quality findings remain, all low; six findings from the plan day-controls cold sweep remain, one of them medium-high; one adjacent issue from the plan day-controls batch remains; the cold sweep of the fix commits' five remain, after the PB-M6/PB-M7 sweep's three and the plan-box-appearance sweep's four; the seventh pass's four remain, the sixth pass's raised save-reporting entry is mostly cleared, the five earlier sections from this batch remain, and older sections from 08-24 and earlier remain)

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

## Below-medium findings — WTP completion surfaces (2026-11-08)

From the Hermes `learning-qa-sweep` gate over `3f705b4..56c1dc0`
(`docs/cycles/2026-11-08_wtp-plc-upd-pd-qa-gate.md`) and from fixing its one
medium finding. The gate's F1 was fixed in-loop; everything here is below
medium, so it is filed rather than fixed.

### WTP-A2 — a `feat(wtp)` commit carries Calendar Export hunks (low)

The gate's F2. `8c65080` ("feat(wtp): a Weekly Tactic is the parent … M1–M3")
also contains unrelated CE work in `db_manager.py`: `calendar_event_id` added
to the time_blocks INSERT/UPDATE/read paths, and `set_block_calendar_event_id`.
Those hunks were read by the gate only as WTP commit content, never as CE work,
so the CE batch's own sweep should cover them. The read path falls back to
`None` on a missing column, so a pre-migration database does not crash. This is
the contamination class *One build batch at a time* in `CLAUDE.md` documents.

**Priority:** Low (process; no code defect found)
**Effort:** None — it is a note for the CE sweep, not a change

### WTP-A3 — `upcoming.py` reports a week collision twice (low)

`UpcomingScreen.complete_item` calls `notify_weekly_tactic_changes` on two
consecutive lines, so a completion that hits a week collision shows the same
warning dialog twice. Introduced by `a1468c8` ("fix(weekly-tactic): resolve the
nine third-sweep findings"), which is already pushed and outside the swept
range — a fix pass adding the line a previous fix pass had already added (P26).
Deleting one line is the whole fix.

**Priority:** Low (duplicate dialog; no data effect)
**Effort:** Small

### WTP-A4 — the rollover's effect on the Done column is not in the guide (low)

`complete_action_item` re-files a completed item onto the Weekly Tactic for the
week it was *finished* in, not the week it was planned for. This is specified —
WTP-M6.6, tested by `test_wtpm66_count_follows_the_wt_m5a_refile` — and it is
the year-rollover behaviour working as intended ("finishing in January
something planned for last December"). It is not a defect.

What is missing is the user-facing half. Measured 2026-11-08: completing items
inside their own week reads `0/3 → 1/3 → 2/3 → 3/3`, as expected; completing a
February item in November moves it off the February tactic, so that tactic's
Done column goes `0/3 → 0/2 → 0/1` — the denominator shrinks instead of the
numerator growing. `docs/USER_GUIDE.md` does not say a tactic's Done count can
fall when its work is finished late, and the column is surprising to read
without it.

**Priority:** Low (documentation)
**Effort:** Small

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

### PLC-A5 — `docs/DOCUMENTATION_INDEX.md` is stale and unenforced (low)

It ends "**Current Status**: ✅ All documentation up to date as of 2026-01-24",
which has not been true for months, and no test checks that every document is
listed in it — which global rule 13 asks for. The index also mixes per-document
sections with category descriptions, so "every document is listed" is not
currently a well-defined property of it.

## Below-medium findings from the PLC cold review passes (2026-11-08)

Two cold passes ran over the PLC diff. Their high and medium findings were
fixed in that batch; these are the below-medium ones, held here rather than
fixed in-loop because a cosmetic fix buys none of the safety it costs.

### PLC-A6 — the `P:` chip and the row fill now disagree about "critical" (low)

Extends PLC-A3. `row_fill` derives the level from `priority_levels._at_least`,
which reads `PriorityFactors` and compares with `>=` after `int()` coercion;
five lines below it in the same five row builders, the chip still uses the
literal `item.importance == 20 or item.urgency == 20`. They disagree for an
importance of `25` (the fill appears, the chip does not) and for one stored as
the string `"20"` (likewise — and `completed.py:306` compares
`str(value).strip() == "20"`, so string-typed factors do occur). Fixing PLC-A3
should replace the literal with a call to the module, not just recolour the
chip.

### PLC-A7 — the save test's stub publishes by the opposite mechanism (low)

`_StubSettingsScreen._hand_settings_to_app` assigns `self.settings` to
`self.app.settings`; the real `SettingsScreen._hand_settings_to_app` re-reads
the file with `AppSettings.load()`, precisely so a refused write cannot leak.
So PLC-M3.2's "reaches the running app" is proven against a stub that models
the opposite of the real guard. The disk round trip is covered separately by
`test_plcm24`, so nothing is unguarded; one test through the real helper with
the `settings_file` fixture would close the gap.

### PLC-A8 — an unusable stored colour is logged once per row, per refresh (low)

`priority_levels.level_color` warns every time it falls back, and it is called
once per row in five screens, so one bad field writes thousands of identical
lines into `app.log` on each refresh. The Settings entry also shows the
*effective* colour rather than the stored one, so the tab displays a value the
file does not contain with no indication the stored one was rejected. A
once-per-value log plus a status line on the tab would surface the drop where
it can be fixed.

### PLC-A9 — the other six Save handlers still have no rollback (low)

`settings_priority_colors.save_priority_level_colors` now restores
`self.settings` when `_write_settings` declines. The other six handlers on the
Settings screen do not, and `SettingsScreen._hand_settings_to_app`'s docstring
already documents the class. One shared helper that snapshots the fields a
handler is about to write and restores them on refusal would retire it; doing
it per handler in a sweeping diff would not.

### PLC-A10 — five more colour validators use `int(x, 16)`, and one is reachable (medium)

The whole of the H1 class, which the PLC batch closed for *settings* colours
only. `int(x, 16)` accepts a leading sign, a `0x` prefix, PEP-515 underscores,
surrounding whitespace and non-ASCII decimal digits, so a seven-character
`#......` string that Tk raises on passes every one of these:

| Where | Function |
|---|---|
| `screens/vps_segment_editor.py:177` | `validate_color`, which gates `save_segment` |
| `vps_manager.py:158` | `_is_valid_hex_color` |
| `screens/settings.py:716` | the `drag_schedule_date_text_color` check (`len != 7` only) |
| `screens/drag_schedule_support.py:61` | same `len != 7` |
| `screens/item_editor_weekly_tactic_dialog.py:387` | same pattern |

And the read path has no check at all: `screens/segment_color_utils.py:164`
`_normalize_color` passes its result straight to `fg_color` as a row fill in
Today, Upcoming and All Items, from `segment_descriptions.color_hex`.

Reachable end to end, the same shape as the bug the batch fixed: VSP → segment
editor → type `# 12345` → `validate_color` returns True → written to
`segment_descriptions.color_hex` → read back unvalidated → `TclError` inside
the row build of three list screens.

Not fixed in the PLC batch because closing it properly means changing a save
gate *and* a read path in the VSP segment subsystem, with its own tests and its
own already-stored data — a change of its own, not a line in a colour batch
(standing rule 10). `color_contrast.normalize_hex_color` is the validator to
route all six call sites through; it returns `None` rather than raising, which
is what a save gate and a row build both want.

### PLC-A13 — `hover_color` was not taken with the other three checkbox colours (low)

`priority_levels.row_control_kwargs` sets `border_color`, `fg_color` and
`checkmark_color` from the fill but leaves `hover_color` at the theme's.
CustomTkinter repaints both the inner square and the border in `hover_color` on
pointer-enter for a checked box (`ctk_checkbox.py:371-379`) while the checkmark
keeps `checkmark_color`, so apple_grey's dark hover `#B3B3BC` against a
`#DCFCE7` checkmark is about 1.3:1 — the tick disappears while the pointer is
on it. The theme's own pairing was no better before the fill existed, so this
is not a new class; it is the moment the four stopped being chosen together.

### PLC-A14 — the completion ✓ is drawn in `success_strong`, whatever the fill (low)

`screens/completed.py:223` and `screens/today.py:522` draw the tick in
`palette["success_strong"]` rather than from the row fill. Completed passes
`use_completed_tint=False`, so its rows do take a level fill. On the two
shipped defaults this measures 6.4-8.3:1 and is fine; a user who picks a dark
green such as `#14532D` for Any Critical gets about 1:1 and the tick vanishes.
`row_control_kwargs` covers the checkbox and the grip, not this glyph, and
PLC-M4.4 covers labels, not it either.

### PLC-A11 — `source_asserts.local_assignments` can return `None` (low)

For an `ast.AnnAssign` with no value, `node.value` is `None` and is appended to
the result list; a caller then passes `None` to `assigns_attribute_of`, which
returns `False`. Harmless today because no row builder annotates `bg_color`
without assigning it, misleading the first time one does.

### PLC-A12 — the Settings tab strip has seven tabs and does not scroll (low)

`CTkTabview`'s segmented button neither wraps nor scrolls, and the seven labels
now run to about 110 characters. The window opens at 1200x700 with no
`minsize`, so a narrow window or a small display can clip "Email Import" with
no way to reach it. The tab *set* is now pinned in order by
`test_plcm36_create_tabs_adds_the_priority_colours_tab`, so a fix can shorten
labels without silently dropping a tab. The missing `minsize` is the older half
of this and is not specific to the new tab.

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

## Sweep findings — APE Week Actions (AWA, 2026-11-07)

Three passes over the AWA range: `learning-qa` (failure patterns), a cold
correctness pass, and a cold test-quality + security pass. One high and five
medium were fixed in-loop with tests (`8a324cb`, `ac22a78`); one medium was
dismissed as a false positive with its reason in that commit's message; the
below-medium ones are here, per the project's sweep budget. The security pass
reported nothing.

### 2026-11-07 - Type: Bug

**Title:** AWA-S1 - a third status renders the right panel completely blank
**Description:** `vps_manager.get_action_items_for_weekly_tactic` has no status
predicate, while `TodayScreen.load_items` renders only `open` and `completed`
items. An item in any other status is fetched and rendered nowhere. If *every*
child of a tactic is in that state the panel draws nothing at all - not even the
empty-state message, because the branch at `today.py:291` is skipped while
`items` is non-empty. Nothing writes a third status today, which is why this is
low; the Today screen's own query restricts status in SQL, so matching it is
also the consistent fix. Found by two of the three passes independently (P2).
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Bug

**Title:** AWA-S2 - the Add button acts on a snapshot and does not check the result
**Description:** `week_actions.set_tactic` stores the tactic as a dict;
`add_action_item` writes from that snapshot without re-reading the row, discards
`create_action_item`'s return value, and calls `edit_item` unconditionally. A
tactic deleted in another tab mid-session makes the INSERT raise on the foreign
key and the button look dead - no row, no message (P6/P42).
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Bug

**Title:** AWA-S3 - only Jump to current week rebuilds the week picker
**Description:** `WeekActionsScreen.refresh_week_options` has exactly one
caller, `jump_to_current_week()`. Neither **Load** nor `refresh()` rebuilds the
combo, so a Weekly Tactic created in a week outside the four generated ones does
not appear in the picker until the user happens to jump to the current week.
`_existing_week_starts` is now covered at construction
(`test_awam41d_an_older_week_stays_in_the_picker`); the missing *re*-build is
not.
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Test

**Title:** AWA-S4 - six coverage gaps in tests/test_ape_week_actions.py
**Description:** All low, from the cold test-quality pass; the high and the four
mediums it found are fixed in `ac22a78`. (a) `test_awam33`'s two assertions are
near-vacuous - `isinstance` is guaranteed by the helper that built the object and
`winfo_viewable() == 0` by `_root()` withdrawing the root; only its teardown half
is real. (b) `test_awam54` selects `parent_id` and never asserts it, though which
of the two columns the button writes is the whole point of AWA-M5.4 - one
`assert row["parent_id"] is None` closes it. (c) The helper's `ORDER BY status,
COALESCE(start_date, due_date), priority_score DESC` is unverified: every test
compares sets or single-element lists, while the rendered order is user-visible.
(d) `add_action_item`'s no-selection warning branch is untested; removing it turns
a real click into a `TypeError`. (e) `test_awam21` asserts only the returned id
set, so if `create_action_item` ever repointed `parent_id` onto
`weekly_tactic_id` at create time the `parent_id` half would stop being exercised
silently. (f) Minor: `_panel` and `test_awam51` take `tmp_path` and never use it;
`test_awam55` restates `_setting_attr` twice; no test checks that a drag on one
panel leaves another panel's stored width alone, which is the AWA-M5.5 claim.
**Priority:** Low
**Effort:** Medium

## Re-sweep findings — APE Week Actions fix commits (AWA, 2026-11-07)

A cold pass over this batch's own fix commits (`8a324cb`, `ac22a78`, `6a112c3`,
`5fb6af2`), run because a fix commit is the least-reviewed code in any change.
It found **one high** that none of the three earlier passes saw: the migration
that runs on every `DatabaseManager` construction overwrote an explicit
`weekly_tactic_id` with the `parent_id` tactic, so the contract the previous fix
round had just documented and tested was reversed at the next launch, and the
invariant repair then moved the item's dates. Reproduced on a throwaway
database, fixed, and covered by a dirty-state test across a real reopen.

Three mediums fixed with it: the collision flag the create path only ever set,
the AST guard that claimed to catch copies it could not see, and the
`chip_table` docstring that described the consolidation as done when nothing
imports the module. One finding rated low by the reviewer was **raised to
medium** and fixed — the fallback chip rendered black text on a near-black pill
in dark mode on 7 of the 10 themes, which is new code producing unreadable text
on exactly the path the fallback exists for.

**One low was fixed in-loop, against the budget**: `LINK_PREDICATE_SQL`
treated `''` differently from `tactic_of`, and was not fully parenthesised. It
is recorded here rather than silently: the edit site was the same comment block
as the medium above it, and splitting it would have left the corrected comment
describing SQL that still had the old shape.

**Half of that low was not a defect, and the mutation gate is what said so.**
The finding claimed a consumer writing `WHERE x OR {...}` would silently get
the wrong rows without outer parentheses. It would not: AND binds tighter than
OR in SQL and the predicate's trailing clause is an AND, so the grouping was
already right. The test written for the claim stayed **green** when the
parentheses were removed, and a direct check on an in-memory table returned
identical rows for `WHERE x OR {p}`, `WHERE {p} OR x` and `WHERE x AND {p}`
either way. The parentheses are kept, because saying the grouping out loud
beats relying on precedence, but they carry no test and the commit message of
`a97b402` overstates them - corrected here, in the spec's §6 and in the
predicate's own comment, rather than left standing. The `''` half is a real
behaviour change and has a test.

The four below-medium findings that remain, of which AWA-S5 and AWA-S6 were
resolved at UPD-M4 (recorded in place, below, rather than deleted):

### 2026-11-07 - Type: Technical Debt

**Title:** AWA-S5 - a chip's text is clamped to the column width, not to the pill
**Description:** `ChipTable._chip_width` makes the pill `CHIP_INSET` (12px)
narrower than its column, but `add_row` calls
`resizer.cell_text(column.key, full_text)` with the default `reserve=0`, so the
character budget is computed from the full column width. For the 135px Segment
column that is 16 characters in a ~123px pill, and the last character is
clipped. `ColumnResizer.cell_text` already takes `reserve` for exactly this, and
the cell is registered with `reserve=0` alongside `width_delta=CHIP_INSET`;
`_apply_live` reproduces the same mismatch on every drag. Cosmetic, and in new
code nothing imports yet, so it is low - but it should be settled before
UPD-M4 moves the first screen onto the table, because every adopting screen
inherits it.
**Resolved 2026-11-07 at UPD-M4**, in `column_resize.py` rather than around it:
`ColumnResizer.chars` and `.cell_text` take the same `width_delta` that
`register_row` already took, and `_apply_live` passes it, so the first render
and the live re-clamp agree. `reserve` was the wrong lever - the difference
between the column budget and the pill budget is 1 or 2 characters depending on
the column width, so a fixed `reserve=1` would be wrong at half the widths;
`::test_updm35_chip_text_fits_the_pill_not_the_column` asserts at 135, 136 and
160px for that reason. `drag_schedule.py` and `today.py` pass 0 and are
unaffected: their pills fill their columns, so there was no sibling to fix (P5
checked, not assumed).
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Technical Debt

**Title:** AWA-S6 - ChipTable's lifecycle assumptions are not enforced by its API
**Description:** Five unenforced assumptions in
`src/getmoredone/screens/chip_table.py`: (a) `clear()` destroys *every* child of
`self.container`, not only the widgets the table created, so a screen that puts
an empty-state label or a second table in the same frame loses it; (b) `clear()`
calls `resizer.clear_rows()` but leaves `resizer._header` pointing at the
destroyed header frame and there is no `clear_header()` - harmless in the
documented order and `_apply_live` is `winfo_exists()`-guarded, but it
contradicts the comment that explains why rows are cleared; (c) the container's
column 0 never gets `grid_columnconfigure(0, weight=1)`, so the `sticky="ew"` on
the header and every row frame does nothing unless the screen sets it, while the
module docstring says the table owns those frames; (d) `add_row` without a prior
`build_header()` grids the first row at row 1 and leaves row 0 empty, and calling
`build_header()` after `add_row` silently destroys the rows; (e) `values={}`
appends a zero-cell, zero-height row with no error and no signal. None is
reachable from the documented call order, which is why this is low.
**Resolved 2026-11-07 at UPD-M4** - four enforced, one settled by stating it.
(b) `ColumnResizer.clear_header()` exists and `ChipTable.clear()` calls it; (c)
`build_header()` weights the container's column 0; (d) `add_row` before
`build_header` raises `ValueError`; (e) `values` naming no column of the table
raises `ValueError`. (a) is deliberately **not changed**: `clear()` destroying
every child of its container is what all six adopting panels need, and
destroying only the table's own widgets would leave a stale label behind for a
screen that added one, which is the worse failure. The constraint - the table
owns its container outright, nothing else may be gridded into it - is stated in
the class docstring instead, with the four tests that hold the other four named
there.
**Priority:** Low
**Effort:** Medium

### 2026-11-07 - Type: Technical Debt

**Title:** AWA-S7 - register_row normalisation accepts bad and over-long tuples silently
**Description:** `ColumnResizer.register_row`
(`src/getmoredone/screens/column_resize.py:152-157`) reads
`width_delta = cell[4] if len(cell) > 4 else 0` and ignores elements 5 and beyond
without complaint, so a mis-ordered tuple normalises cleanly. A non-numeric
`width_delta` also passes normalisation and fails later inside a drag handler
(`label.configure(width=max(1, width - width_delta))` raises `TypeError` inside a
Tk event callback, where it prints to stderr rather than reaching the caller).
No validation and no test for either. `width_delta` was added in this batch, so
this is new surface, but both callers in `src/` pass 3- or 4-tuples.
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Technical Debt

**Title:** AWA-S8 - the AWA-M5.3 override census cannot see a dunder override
**Description:** `test_awam53` in `tests/test_ape_week_actions.py` asserts the
exact set of `WeekTacticActionsPanel` attributes that override `TodayScreen`,
which is a real improvement on the set-intersection it replaced. But the census
filters `not name.startswith("__")`, so an added `__init__` or `__getattr__`
override - the most likely way the Today seam actually gets broken - would not
appear in `overridden` and the exact-list assertion would stay green.
**Priority:** Low
**Effort:** Low

## Third cold pass — APE Week Actions re-sweep fixes (AWA, 2026-11-07)

A third cold pass over the re-sweep's own fix commits (`a97b402`, `e8b9eb7`),
run on a different failure family: the changed migration's data-path safety
against every real row shape, and test quality. **No high.** Two mediums and
one low raised to medium were fixed with tests; three lows are below, and one
"low" turned out not to be a defect at all.

- **The kept count reached the return dict and no log.** `_log_report` reads
  only `moved` and gates the line on `if moved:`. A row whose explicit tactic
  was kept still had its `parent_id` cleared - a write to the user's data - and
  while the two outcomes were one number that row was logged *because* it was
  miscounted. Counting it correctly without logging it made the launch silent
  about it, which is a net loss of coverage (P2). Fixed; `kept_explicit_link`
  now has its own line with the item ids.
- **The `''` behaviour change shipped untested.** `COALESCE(weekly_tactic_id,
  '') = ''` makes the SQL agree with `tactic_of`, and one of the predicate's
  two consumers decides which duplicate tactic a dedupe *deletes*. Now covered,
  seeded with foreign keys off the way AWA-M2.5 is - measured: with foreign
  keys on, writing `''` raises `IntegrityError`, so the state is a dirty one
  (P8), not a live write path.
- **The AWA-M2.3 guard's "case-insensitive" claim was empty.** The regex
  carried `re.IGNORECASE` but the membership gate in front of it did not, so
  the flag only widened the half already pinned. Confirmed by running:
  `"WEEKLY_TACTIC_ID = ? OR PARENT_ID = ?"` did not match. Raised from low,
  because a guard that states a guarantee it does not give is the same defect
  this batch already rated medium once. Fixed, with a mutation planting a
  shouted copy.
- **Half of a low fixed last round was not a defect.** See the note in the
  re-sweep section above: the outer parentheses on `LINK_PREDICATE_SQL` change
  no result, the test written for the claim stayed green under mutation, and
  the claim is corrected in three places rather than left standing.

Two lows in new tests were corrected rather than filed, because both were false
claims in docstrings written in the same round (rule 13) and the fixes are a
deleted line and a corrected fake: a `!= "#000000"` assertion that could never
fail, since the theme value it compares is a two-element list; and a seeded
`last_week_collision` using a key (`attempted_start`) that neither producer in
`db_manager` writes nor `describe_week_collision` reads. That test now asserts
the dialog through the `messageboxes` fixture, which is what its name claims.

The three that remain:

### 2026-11-07 - Type: Bug

**Title:** AWA-S9 - the invariant repair's "child" is wider than the predicate's, and a week-under-week row can stop the app opening
**Description:** `LINK_PREDICATE_SQL` excludes `child.item_type != 'week'`;
the invariant repair's query
(`src/getmoredone/weekly_tactic_maintenance.py:591-603`) constrains only the
parent side (`WHERE week.item_type = 'week'`). So the repair acts on week rows
AWA-M2.2 deliberately keeps out, which is more than the disagreement AWA-A1
describes. It has teeth: for `W1` and `W2` both week items of one APE with
`W2.parent_id = W1`, the link migration's else-branch sets
`W2.weekly_tactic_id = W1`, and the repair then rewrites `W2.start_date` to
W1's week start (`:686-689`, an unguarded `UPDATE`), which violates the WT-INV5
unique index on `(annual_plan_element_id, start_date) WHERE item_type='week'`.
`repair_weekly_tactic_invariants` is called with no `try/except`
(`weekly_tactic_migrations.py:296-298`), so the `IntegrityError` would
propagate out of `Database.initialize_schema` and the app would not open. Low
because whether the UI can set a week item's `parent_id` to another week item
was **not established** - the parent picker's row filter was not traced - so
reachability is unknown rather than shown. Pre-existing; not introduced by the
AWA batch. Establishing reachability is the first step, not the fix.
**Priority:** Low
**Effort:** Medium

### 2026-11-07 - Type: Technical Debt

**Title:** AWA-S10 - the P5 sibling of the migration fix was not fixed with it
**Description:** `_repoint_children`
(`src/getmoredone/weekly_tactic_maintenance.py:322-326`) still runs
`UPDATE action_items SET weekly_tactic_id = ?, parent_id = NULL WHERE
parent_id = ?` with no branch on an existing explicit link - exactly the shape
`migrate_parent_links_to_weekly_tactic` was changed away from in `a97b402`. P5
says fix a class, not an instance. It was left because it is unreachable within
a single run: the link migration (step 2) clears every `parent_id` whose parent
is a week item before the dedupe (step 3) runs, and its own comment says it
exists for "stragglers written by an older build between migration and
dedupe". Recorded rather than fixed silently (rule 10), and rather than swept
in on a low severity.
**Priority:** Low
**Effort:** Low

### 2026-11-07 - Type: Technical Debt

**Title:** AWA-S11 - the AWA-M2.3 scan can be turned red by a prose string
**Description:** `test_awam23_one_home_for_the_link_predicate` excludes strings
by value-equality against module, function and class docstrings only. A
non-docstring prose string under `src/getmoredone` that names
`weekly_tactic_id`, then "or", then `parent_id = ?` would match the shape and
fail the exact-count assertion. Confirmed by running: `"either
weekly_tactic_id is set, or the legacy shape where parent_id = ? was used"`
matches. None exists today. Low, and deliberately so: the cost is a one-line
edit to this test, and the cost of a looser gate is the high finding the test
was written for. The docstring states it.
**Priority:** Low
**Effort:** Low

## Reported from the running screen — Plan / Day Plan (2026-11-07)

Four faults reported by the user after the PD-* batch shipped. **Recorded, not
investigated**: the descriptions below are the report, not a diagnosis. Nothing
here has been reproduced, read in the code, or confirmed against a running app
by this session.

**All four are addressed by PD-M11** (`docs/implementation_plan_2026-11-06_plan_day_controls.md`),
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
notes with one generic `docs/changes/` entry. The seventeen
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

## Deferred from the APE period-consistency sweep (2026-11-07)

Found by the three passes over `7aa601d...HEAD` — learning-qa, a correctness
pass over the source diff, and a security pass (which found nothing). Four
findings were fixed in the batch with tests: one medium-high, two medium and
one low-medium. These are what was recorded instead, each with the reason,
because the repo's budget stops in-loop fixes below medium.

- **`date_utils.quarter_of_month` silently truncates a float and accepts a
  bool.** Low. `int(month)` runs inside the `try`, so `quarter_of_month(11.7)`
  returns 4 and `quarter_of_month(True)` returns 1 — measured, not inferred.
  The docstring's stated reason for raising at all is that "a caller holding
  month 0 or 13 has a bug, and a silent answer is what let the bad pair reach
  the database"; a caller holding 11.7 has the same bug and gets the silent
  answer. **Not fixed here** because no production caller can reach it with a
  non-integer: every one goes through `int()` or `date.month`. The fix is a
  type check before the coercion, and it wants its own small change rather than
  a fix-pass edit to the one function this batch made four callers share.
- **`plan._require_block_day` opens a modal from inside a drop's
  `after_idle`.** Low, and PLAUSIBLE rather than confirmed. `messagebox.askyesno`
  pumps the Tk event queue, which is exactly what `_flush_redraw` picks
  `update_idletasks` over `update` to avoid; the permission is recorded against
  `self.selected_date` and the caller reads `self.selected_date` again after
  the modal returns (`plan.py:1169`) to decide where the block goes. **Not
  fixed here** because neither pass could drive a date change through Tk's
  modal grab, so there is no demonstrated misbehaviour to write a test against
  — only a latent coupling between a permission keyed on one read of the date
  and a write that takes another.

### Adjacent issues found, not fixed

- **The Plan screen's failure arm is on 3 of its 8 write paths.** Pre-existing,
  raised because `clear_day`'s new docstring says it adopts "the same arm
  AutoLoad has", which reads as a class that is 3/8. `autoload_day`,
  `extend_day_for` and `clear_day` have it. `add_padding_block`, `block_item`
  (whose `try` catches only `SlotRefusedError`, deliberately), `delete_block`,
  `set_block_minutes` and `move_block_to_slot` do not — a failed
  `create_time_block`/`delete_time_block` in any of them raises inside a Tk
  callback and presents as a gesture that did nothing.
- **`weekly_items` files a week under the calendar month of its start date.**
  Pre-existing and unchanged by this batch, which only removed the derived
  quarter beside it. A week starting Mon 2026-11-30 runs into December and its
  APEs are looked up for November only. Whether that is the intended reading of
  a straddling week is a product question, not a defect to patch blind.

## Deferred from the APE re-sweep of that batch's own fix commits (2026-11-07)

The fix commits from the sweep above went back through learning-qa as
`c31fce7...HEAD` — the budget's rule that every in-loop fix is itself in scope
for the next pass. It returned four findings: three were fixed with tests
(APC-M2.5/M2.6, APC-M5.5, APC-M6.3/M6.4, plus the drag tests' assertions), and
these are what was recorded instead. Full account in spec §5.11 and §5.12.

- **`get_annual_plan_elements_for_month`'s guard raises on an unhashable month
  and accepts `True`.** Low. `month not in QUARTER_OF_MONTH` raises
  `TypeError` for `[]`, `{}` or `set()`, and `True` passes the membership test
  (because `True == 1`) and becomes column `m1`. **Not fixed here** for the
  same reason as `quarter_of_month` above: both screens parse the month with
  `int()`, so no caller can reach it. What was fixed is the claim — the test
  was named `..._is_type_safe` and `NOTES.md` said "type-safe"; both now say
  what the guard actually does. The fix is an `isinstance` check that excludes
  `bool`, and it belongs with the `quarter_of_month` entry above as one small
  change to the two guards.
- **A transient database error reads as a permanent refusal.** Low, P1 nuance.
  Both screens' `_assign_one` and `_remove_one` catch `Exception`, so a
  `sqlite3.OperationalError` ("database is locked") produces the same sentence
  as an APE whose segment cannot be resolved — "could not be assigned", which
  invites a retry for one and not the other. The log line carries the
  exception, so the information exists; the status line does not use it.
  **Not fixed here** because telling retryable from terminal means classifying
  the exception, and the honest version of that is a shared helper for every
  screen that writes, not two more `except` clauses on these two.

### Adjacent issues found, not fixed

- **`weekly_tactic.py:294` calls `assign_ape_to_month` with no `try` and
  discards the return.** It is the seventh member of the class the two screens'
  six write paths belong to, and it was the one the first fix round's "four
  paths across two screens" claim missed. **Not fixed here** because it sits in
  the re-filing cascade, which already has its own `CascadeReport` surface for
  telling the user what a cascade did: hardening it means reporting through
  that, not bolting a status label onto a different subsystem. It should be
  done with the next cascade change.

## Deferred from the plan day-controls cold sweep (2026-11-06)

Found by the three sweep passes over `6976b49...HEAD` — learning-qa, a cold
correctness pass and a security pass. The high-severity finding and the three
mediums were fixed in the batch (`aead482`). These are what was recorded
instead of fixed, each with the reason, because a fix pass is new unreviewed
surface and the repo's budget stops in-loop fixes below medium.

- **The app holds two live `AppSettings` objects, and either one's save reverts
  the other's fields.** Medium-high, and the only finding above low that was
  not fixed. `AppSettings.save` writes `asdict(self)` — every field — and
  `screens/settings.py:34` loads a settings object of its own. So: launch,
  change the theme in Settings and save (the file is updated, `app.settings` is
  stale), then drag the Plan divider or drop an item on *Earlier*. The Plan
  screen writes `asdict(app.settings)` over the file and the theme change is
  gone, with nothing said. The write itself is not new — `plan_settings_dialog`
  has done it since TG-M6 — but PD-M2 and PD-M5 added two triggers that fire on
  a casual drag rather than on an explicit Save, which is what makes it likely
  to be hit. **Not fixed here because the defect is the two objects, not the
  two new call sites**: the fix is one owner for the settings file (either the
  Settings screen writes through `app.settings`, or `save` merges what it did
  not load), and that is an app-wide change to the semantics of every save in
  the app. It is not a thing to do in a fix pass at the end of a batch, and
  patching only the two new triggers would leave the same defect behind three
  older ones.
- **The *Earlier* and *Later* boxes get no hover outline.** Low.
  `update_hover_target` reads `self._slot_frames`, which holds the real
  half-hour boxes only, so dragging over the two virtual boxes outlines
  nothing — while every real box does. The one target on the screen that has to
  announce itself is the only one that does not.
- **Extending the day earlier into lunch is refused with a message about the
  wrong thing.** Low. With Day Start at 13:00 and lunch at 12:00, a drop on
  *Earlier* makes box 0 a lunch box, `can_place` returns `CROSSES_LUNCH`, and
  the user is told "That block cannot go there" — a sentence about a box, when
  the fact is that the day cannot start inside lunch. The rollback is correct;
  only the wording is wrong.
- **`extend_day_for` catches `Exception` where its transaction rolls back on
  `BaseException`.** Low. A `KeyboardInterrupt` inside the block takes the
  database back and leaves `self.settings.plan_day_start` on the new, unsaved
  value for the life of the process — the P41 case the method's own docstring
  is about. Unreachable in the packaged app, which is why it is low.
- **The empty-day note wraps to the setting, not to the column.** Low, and
  wider than it first looked. The note's `wraplength` is computed from
  `items_col_width()` when the note is built, so after a drag that widens the
  pane it keeps the old wrap until the next refresh — and, since the resize
  clamp made a drawn width narrower than the setting an ordinary state, it also
  wraps to a width the column does not have whenever the window is too narrow,
  clipping the note with no gesture from the user at all. One line: read
  `_items_width`, which is the width drawn. Left out of the fix round because
  the note is one sentence on an empty day and the round had already produced a
  high-severity finding of its own.
- **The depth-bars column is 2px narrower than what is gridded into it, and a
  padding chip's length sits 2px left of a task's.** Low.
  `SLOT_BARS_WIDTH_PX` is 22, but `DepthBarStack` is gridded with
  `padx=(4, 6)` around a 14px stack in both renderers, so the column needs 24
  and both width floors are 2px short. Separately, `_build_block_chip` grids
  the bars only for `BlockType.ITEM`, so a buffer or break chip's length label
  lands 2px left of a task's in the same pane. The two *panes* stay in step
  with each other; rows within one pane do not. Fixing it means changing the
  chip column contract and the tests that assert it, for 2px.
- **`shift_all_slots` accepts a negative `by`.** Low, and listed for the record
  rather than as a defect: nothing calls it with one, Day Start only ever moves
  back on this path, and a negative shift would be the correct write if a
  shortening path is ever added.

## Deferred from the third cold pass — test quality (2026-11-07)

A cold pass over `14d9199...HEAD` with a test-quality lens: eight mutations of
`plan.py`, seven red on the test that names the line. No finding of medium or
higher, so by the review budget none was fixed in the loop. Two of its lows
were factual errors in prose written in the same batch and were corrected
there; these three are the rest.

- **`caplog.at_level` names a logger the code never touches.** Low.
  `tests/test_plan_screen.py::test_pdm37_a_failure_that_is_not_a_refusal_is_still_reported`
  passes `logger="getmoredone.screens.plan"`, but the test file imports the
  module as `src.getmoredone.screens.plan`, so that is the logger's real name.
  The two `caplog` assertions still pass for the right reason today — and go
  red when the `logger.exception` call is deleted or demoted — but only because
  ERROR clears the root logger's default level. Demote that log line to WARNING
  or INFO later and they fail against correct code, with a misdirected
  `at_level` as the cause. One word: `logger=plan.__name__`, or drop the
  argument.
- **Two drag tests measure from the setting, not from the drawn width.** Low.
  `test_pdm21_dragging_the_grip_changes_the_items_column` and
  `test_pdm26_the_grip_and_the_settings_field_are_one_value` take their
  reference from `items_col_width()`, while `on_divider_press` now snapshots
  `_items_width`. The two agree only because the screen is unmapped, where
  `winfo_width()` is 1 and the clamp applies no right-hand bound — which is the
  distinction both docstrings were rewritten to explain. If either test ever
  takes `mapped_windows`, its expectation comes from the side the fix removed.
  Read `panel._items_width`.
- **The `sizer` screen is an expensive way to read a floor.** Low. Both tests
  above build a whole second `PlanScreen` — 50-odd widgets and a full
  `refresh()` against the database — to obtain `items_width_floor()`, which
  reads `drag_schedule_title_col_width` and never `plan_items_col_width`. The
  sequencing is right (the setting must be in place before the screen is
  built); the second screen is not needed to get there, in a file whose runtime
  is already throttled.
- **`apply_items_width`'s "only on a change" guard is pinned by nothing.** Low.
  Its docstring says a grid change from inside `<Configure>` "would not
  settle". Removing the `if held != self._items_width:` guard and running
  `test_pdm22_a_resize_alone_rebalances_the_panes` against a real mapped window
  with two `root.update()` calls stayed green in 2.9s: Tk emits no
  `<Configure>` for a `minsize` set to the value it already holds, so the
  stated hazard is not reachable by this route and the justification is
  unverified either way. Low because no regression is observable — but a future
  change that reconfigures with a *different* value from inside that handler
  would reintroduce the loop with nothing to catch it.

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

## Below medium, from the cold sweep of the fix commits (2026-11-06)

Found by the cold `learning-qa` pass over `8138181...HEAD` — the six fix
commits no other pass had seen. Its one medium finding (a refused write
reaching the running app, once the app held the Settings screen's own object)
was fixed in-loop with three tests; these five were not, for the usual reason:
a below-medium fix is new unreviewed surface that buys none of the safety it
costs.

- **The floor test's equality holds only at widget scaling 1.0.**
  `tests/test_plan_screen.py::test_pbm61_the_floor_is_what_the_rows_own_grid_asks_for`
  sums `winfo_reqheight()` plus `grid_info()["pady"]`, both of which
  CustomTkinter scales, against the raw `ITEM_ROW_MIN_HEIGHT_PX`.
  `ScalingTracker.get_window_dpi_scaling` returns 1 on darwin and on Linux, so
  both Macs and the ubuntu CI matrix are unaffected; on a Windows HiDPI display
  at 150% the sum is about 101 against a floor of 67 and the test is a false
  red, with nothing actually clipped. The repo ships `start.bat` and a
  `build-windows` job and has no Windows test job, so it would first surface on
  a contributor's machine. Fix: compare against
  `row._apply_widget_scaling(ITEM_ROW_MIN_HEIGHT_PX)`, or skip unless scaling
  is 1.
- **That same test's `pady` parsing misreads three forms it never sees.**
  `re.findall(r"\d+", str(pady))` recovers `5` and `(6, 2)`, which is
  everything `build_item_row` writes. It would misread a Tk screen distance
  (`"2m"` as 2 rather than about 7.6px, `"0.5c"` as 5) and a float
  (`(5.5, 0)` as 10) — silently, so the guard would demand the wrong floor
  rather than fail. Fix: split the tokens and assert each converts and that
  there are one or two of them.
- **Nothing holds the hand-over as a class.** `app.settings` is read by the
  Plan screen and the Weekly Items screen; the Settings-screen sections that
  write a field either of them reads are the appearance section and the
  date-increment section, and both now hand over. The class is complete today
  and no test says so, so the next section that writes a field the Plan screen
  reads reintroduces the original bug. A meta test over the `save_*` handlers
  in `settings.py` would hold it.
- **Two divergent stubs of the same Save handler, one of them blind.**
  `tests/test_settings_week_rule_ui.py::_save_stub` and
  `tests/test_plan_settings.py::_date_increment_stub` both stand in for
  `save_date_increment_settings`'s widgets, and the first carries neither
  `app` nor `plan_items_col_width_var`, so it raises part-way through and the
  two tests using it wrap the call in `except AttributeError: pass`. The
  assertions they make are still live — the rule reaches the settings object
  before the raise — but nothing after that line can be seen from them, which
  is part of why the suite could not see the missing hand-over. Low: the
  stubs' own assertions hold. Fix: one shared stub carrying every widget the
  handler touches, and no swallowed `AttributeError`.
- **A concurrent writer still loses its write to disk.** `_write_settings`
  writes the whole snapshot the Settings screen loaded at construction, so an
  open Timer window calling `save_window_settings`
  (`src/getmoredone/screens/timer_window.py:1769`) has its write overwritten by
  the next Save on the Settings screen. Pre-existing, and not widened by the
  hand-over fix — memory now matches disk either way. Low: the lost fields are
  window geometry.

## Below medium, from the PB-M6/PB-M7 sweep (2026-11-06)

Found by the cold `learning-qa` and `/code-review` passes over
`2e4add9...HEAD`. Recorded rather than fixed: none is above low severity, and a
below-medium fix is new unreviewed surface that buys none of the safety it
costs.

- **The row no longer says whether the length is the item's own.** The detail
  line used to read `Work Block 30m` when the item carried its own
  `work_block` and `30m` when the length came from the settings default. The
  label under the depth bars is always `{minutes}m`, so the distinction is
  gone. Neither form is pinned by a test. `plan_blocks.py` `build_item_row`.
- **Nothing bounds an item row's span.** `slots_for_minutes` is capped only at
  `MINUTES_PER_DAY`, so an item with a long work block — or a user whose
  `default_time_block_minutes` is 240 — produces a row of 8 to 48 boxes that
  pushes the rest of the list out of sight with no hint it is there. A cap, or
  a "needs N boxes" line instead of N boxes of height, is the fix.
- **`drag_schedule.py:113-116` now disagrees about what one box is.** It reads
  the same box-height setting with its own fallback (86) and floor (20), and
  applies no `slots_for_minutes` scaling to its own item rows. Already listed
  under the earlier sweep's entry for the same file; the two screens have now
  drifted further apart. One shared helper is the fix.
- **`docs/` points at test names that no longer exist, and nothing checks it.**
  Adjacent, found while verifying this batch's own references: a script that
  pulls every `test_*` token out of `docs/**/*.md` and `CHANGELOG.md` and
  matches it against `^\s*def test_` across `tests/` finds stale names in
  `docs/VPS_DATA_INTEGRITY_AUDIT.md` and nine older handoff notes. Two in
  `docs/spec_coverage.md` were repointed with this batch because that file is
  the coverage claim itself — `test_spec_coverage_doc_mentions_m1_through_m5`
  (renamed to `_m7`) and RP-4.2's second test. The rest are left: each needs
  the real test located or the row marked `partial`, which is its own batch.
  The fix that stops it recurring is a meta test asserting every
  `::test_` reference in the documentation index resolves, with the deliberate
  exceptions (`*test removed with the criterion*`, `*as planned*`) named
  explicitly rather than skipped by pattern.

## Below medium, from the plan-box-appearance sweep (2026-11-06)

Two review passes over the batch that shaded a task by its priority and sized
it from the Drag Schedule settings: a failure-pattern pass and a correctness
pass. Eight findings between them, no high. The five medium ones were fixed
with tests in the same session; these are the rest, plus two adjacent issues
flagged rather than fixed (global rule 10).

- **Adjacent: `drag_schedule.py` reads the shared box-height setting without
  the guard written for the Plan screen.** `screens/drag_schedule.py:115` is
  `max(20, int(getattr(self.settings, "drag_schedule_box_height_px", 86)))`.
  A hand-edited `null` or `"86px"` in settings.json raises there and the
  screen does not open, while the Plan screen falls back to 30. The two
  readers also disagree on the fallback (86 vs 30) and the floor (20 vs 30),
  so the user guide's claim that a task is the same size on both screens holds
  only on the happy path. One `_positive_setting`-style helper shared by both
  is the fix. Not fixed here: it is outside the batch, and silently widening
  the diff into another screen is the sweeping-diff half of rule 10.
- **Adjacent: the four Plan and Drag Schedule size controls sit under
  "Date Increment Settings".** `create_date_increment_section` renders the two
  Drag Schedule sizes, the Plan items column width and the date-increment
  rules together, under a heading and an info paragraph that describe only
  date incrementing. The docs now say where the controls actually are, which
  is the honest half; moving them to Appearance is a relocation of existing
  controls and needs approval under the UI regression standard, so it is
  recorded rather than done.
- **A shaded item row has no title/detail hierarchy.** `build_item_row` sets
  the title and the detail line to the same `pick_text_color(fill)`, because
  that function has no muted variant. Contrast is fine on both; the title no
  longer reads as the louder of the two. Wants a `pick_muted_text_color`, or a
  fixed alpha blend toward the fill.
- **`docs/USER_GUIDE.md` has two "Date Increment Settings:" headings** in the
  settings reference, listing different controls under the same name. Older
  than this batch; found while correcting the section a control lives in.

## Below medium, from the seventh pass of the grid rebuild (2026-11-06)

Cold pass over the sixth round's own fix — seven production call sites across
two screens, the widest fix in the batch. Two mediums, both in the batch's own
new tests, fixed there. Four lows, here.

- **"Run Import Now" erases the refusal it just caused.**
  `run_email_import_now` (`settings_integrations.py:226`) calls
  `save_email_import_settings`, which now reports a refused write on
  `gmail_status_label` — and then line 259 sets that same label to
  "Running import…" and starts the thread, so the import runs against values
  that were never written and the user is told nothing. Not a regression: the
  old code wrote a false "Saved (launchd updated)." into the same label and
  erased that instead. The fix is for `save_email_import_settings` to return
  the bool and for this caller to stop on False. `run_calendar_import_now`
  reports on a different label and is unaffected.
- **A refused database save leaves the entry showing the raw text.**
  `save_database_settings` skips
  `self.business_year_start_var.set(...)` on the early return, and
  `AppSettings.save` normalises that field before it decides whether to write —
  so the widget shows what was typed while `self.settings` holds the normalised
  value. Cosmetic: the error is displayed, and the next Save re-reads the entry.
- **Every section writes its widget values into `self.settings` before the
  save.** After one successful Appearance save, `self.app.settings` is that same
  object, so a later refused save in any section leaves the running app holding
  values the file does not have until relaunch. The ordering is older than this
  batch and unchanged by it; the new guard makes it visible rather than silent,
  which is why it is low. The fix is to stage the widget values and commit them
  on a successful write only.
- **Nothing pins the mixin's dependency on `_write_settings`.**
  `SettingsIntegrationsMixin` calls a method defined on `SettingsScreen`, which
  resolves because `SettingsScreen` is the only class that mixes it in — but the
  new tests supply `_write_settings` on a `SimpleNamespace` stub, so no test
  walks that MRO hop. Renaming or moving `_write_settings` would leave the suite
  green and raise `AttributeError` on the Email Import Save button.

## Below medium, from the sixth pass of the grid rebuild (2026-11-06)

Cold pass, lens: the blast radius of the changed `AppSettings` contract across
the twenty-odd screens that load and save their own settings object. Two
mediums, fixed in the batch; the rest are here.

- **On a full disk the refusal names a remedy that cannot work.** A write that
  fails part-way through `json.dump` leaves invalid JSON behind; the next save
  then finds a file that will not parse, fails to copy it aside for want of the
  same space, and tells the user to move or delete it and try again. Moving the
  settings file does not free the disk. Low: the state is recoverable and the
  message is at least about the right file, but it points at the wrong remedy.
- **Adjacent issue found, not fixed: tests pinned to the calendar.**
  `test_the_date_is_a_picker_not_a_free_text_entry` compared the date picker,
  which is built from `date.today()`, against a date the fixture had assigned
  behind it — so it passed only on the day it was written and went red at the
  first midnight. Fixed here, because it was red. There are 24 other uses of
  `date.today()` across `tests/`, unaudited; some are legitimate relative-date
  arithmetic and some may be the same defect waiting for a particular weekday.
  Worth one pass with a frozen clock rather than finding them one midnight at a
  time.
- **`TimerWindow` and `NextActionWindow` hold a long-lived `AppSettings` and
  save the whole of it.** They are Tk children of the screen that opened them,
  so `app.clear_content()` destroys them before the user can reach the Plan
  screen, and nothing stale can be written today. If either is ever reparented
  to the app root, it becomes a path that writes a stale
  `plan_day_shape_unconfirmed` over a confirmation and the user's four day
  times. Low because it is not reachable now; recorded because the thing that
  makes it unreachable is a parent argument nobody would think to preserve.

## Below medium, from the fifth pass of the grid rebuild (2026-11-05)

Cold pass, lens: the settings-file format and the state around the new
persisted field. One finding below medium.

- **The confirmation gate covers the migration, not the planning done on an
  unconfirmed day.** `load_blocks` gates `adopt_legacy_day` on the day's shape
  being the user's, but `move_block_to_slot` and `add_block_at` are ungated,
  and `_settle_block_on_slot` derives and stores clock times from the same
  `day_start`. Low, and arguably correct: the user is dragging onto a grid they
  can see, and the times follow the boxes they chose. But the settings file can
  then hold stored times derived from a day shape it also records as
  unconfirmed. Worth deciding deliberately rather than by omission.

## Deferred from the time-block rebuild (2026-11-05)

Recorded rather than fixed in the batch that found them, because a fix pass is
new unreviewed surface and none of these is above low severity.

- **Deleting a block asks nothing.** `Delete block` on the right-click menu
  removes it immediately. Every other destructive action in the app confirms
  first. Low: a block holds no content of its own, and dragging the item back
  rebuilds it — but it is inconsistent with the rest of the app.
- **A depth bar is not draggable.** The three-bar stack is a grandchild of the
  task chip, and the drag handlers are bound to the chip and its direct
  children only, so a press that lands exactly on a 14×3px bar does not start a
  drag. Low: the target is tiny and the rest of the chip works. *(Still true
  under the grid; the widget it hangs off is now the chip, not the row.)*
- **The demo instance cannot exercise the Plan screen as seeded.** All six
  sample items in `demo_data.py` have an empty start date, and the Plan item
  list filters on start date exactly, so the left pane is empty on a fresh demo
  until a start date is set by hand. Worth giving the sample items dates
  relative to first launch.
- **No way to move a block to another day.** Blocks are created on, and belong
  to, the selected date. Re-planning an item for tomorrow means deleting the
  block and dragging the item again on that day. *Raised by the grid from low to
  worth doing:* a drag within a day now moves a block between boxes, so this is
  the only gesture a user would reasonably expect and not find.

## Below medium, from the third pass of the grid rebuild (2026-11-05)

A cold correctness and test-quality pass over the second round's fix commits.
It produced one high and four medium findings, all fixed with tests and
mutation-proved, and these two.

- **The kept-aside settings file is named to the second.** A save that fails
  after a successful copy leaves the flag set, so an immediate retry inside the
  same second writes `settings.json.unreadable-<same stamp>` and replaces the
  first copy. Harmless as it stands -- the original is unchanged by a failed
  write, so the second copy has identical content -- but the name is one
  collision away from mattering. Low: add a counter, or use a finer stamp.
- **Each settings screen loads its own `AppSettings` and saves the whole
  object.** So the last screen to save silently reverts every field another
  screen changed, including the day settings the Plan dialog just wrote, and
  `screens/settings.py` additionally replaces `app.settings` with its own copy.
  Pre-existing and wider than this batch: it is the root of both the "reports
  success on a failed write" entry below and the reason the unreadable flag is
  cleared by the Day Settings dialog rather than by `save`. Worth one diff of
  its own that gives the app a single settings object.

## Below medium, from the re-sweep of the grid rebuild's fix commits (2026-11-05)

The second sweep round: a cold `learning-qa` pass over the three fix commits
alone, which is the least-reviewed code in the change. It produced one high and
four medium findings, all fixed with tests and mutation-proved, and these five.
Severity rated before any fix was written, as above.

- **The spare-minutes label re-derives a span the layout module already
  computes.** `plan_blocks.build_slot_row` calls
  `slots_for_minutes(block.planned_minutes)` where `build_day_grid` uses
  `slot_span_of(block)` for the same fact. They agree — `slot_span_of` is a
  one-line wrapper — and `slots_for_minutes` takes `Optional[int]`, so there is
  no crash path. Low, and P19: two expressions of one fact in a module whose
  own docstring says span is computed in one place for exactly this reason. If
  they ever diverge, no box satisfies the last-box test and the label silently
  disappears. One call swap.
- **`AppSettings.load`'s `except Exception` spans the six normalizers as well
  as the parse.** A bug in `_normalize_plan_day_settings` is therefore reported
  to the user as "Day Settings could not be read" and blocks adoption for the
  session — a code defect presented as a file problem (P40). Low: the fallback
  is still safe and the print names the real exception. Narrow the `try` to
  `json.load` plus the constructor, or separate `JSONDecodeError`/`OSError`
  from the rest.
- **`_subtree` overwrites `<Button-1>` on every descendant of a block chip.**
  Nothing in a chip is interactive today, so nothing is broken — but the first
  `CTkButton` or `CTkCheckBox` put inside one will stop responding with no
  error. Low, and now documented in the helper's own docstring along with why
  its pre-order traversal is load-bearing. The fix is an `isinstance` skip for
  widgets that handle their own clicks.
- **`add_block_at` now depends on its caller not pre-setting `slot_index`.**
  With the `keep_position` default off this is only reachable by a caller that
  builds a block whose `slot_index` already equals the target box, which then
  keeps `position = 0` and collides with whatever is in that box. Both
  production callers build a fresh block with `slot_index=None`, so it is
  latent. Low: a contract change in a public-ish method with no guard and no
  test.
- **✅ Mostly cleared 2026-11-06 — a settings save that could not happen was
  reported as done.** Raised to medium by the sixth pass of the grid rebuild
  and fixed there: the seven call sites that reported success
  (`screens/settings.py` ×6, `settings_integrations.py`) now go through
  `SettingsScreen._write_settings`, which reports the refusal on that section's
  own status label, and the two that did more than report — Appearance applying
  the theme app-wide, Email Import reloading launchd — skip that too.
  `tests/test_settings_save_refusal.py` covers all four behaviours.
  **What remains, at low:** three call sites still ignore the return value and
  fail silently rather than wrongly — `column_resize.py:104`,
  `timer_window.py:1778` and `timer_window_dialogs.py:452` (window positions
  saved on close). That is three call sites but **four surfaces**:
  `ColumnResizer` is built twice, by `today.py:70` with `prefix="today"` and by
  `drag_schedule.py:92` with `prefix="drag_schedule"`, so a column drag on
  either screen saves silently. None of them tells the user anything either way,
  so none can lie; the setting is simply lost until the settings file is
  dealt with. The user-facing notice that an unreadable file was kept aside is
  still only in the log, and still belongs with whatever fixes these three.
- **The traceability guard checks test pointers in `docs/spec_coverage.md` but
  not source ones.** Extending the guard to that document found eight rows
  naming deleted tests. Its *Implementation* column has the same class of
  defect — the re-sweep found seven deleted functions named there, four of them
  on rows still marked `done` — and the guard cannot see any of it. Those rows
  are corrected, but nothing stops the next one. Low-to-medium: parse the
  parenthesised symbol lists and assert each name still exists in the file the
  row points at.

## Below medium, from the grid rebuild's pre-push sweep (2026-11-05)

Severity-rated before any fix was written. The sweep ran `learning-qa`, a cold
`/code-review` and a cold `/security-review`; everything medium and above was
fixed in the same session with a test, each proved by mutation. These are the
rest, left alone deliberately: a fix commit is the least-reviewed code in a
change, and a cosmetic fix buys none of the safety it costs.

- **The day summary's box denominator counts lunch** (`plan.py:458`,
  `learning-qa`, low). `f"{slots_used} of {len(slots)} boxes"` uses the whole
  grid, but lunch boxes take no tasks, so a completely full default day reads
  *16 of 18 boxes* and can never reach 18. It is a capacity claim that
  overstates capacity by the lunch length. Fix: divide by the placeable boxes,
  or say "16 of 16 workable boxes (2 lunch)".
- **`clear_hover_target` restores the border width but not its colour**
  (`plan.py:881`, `/code-review`, low). `update_hover_target` sets
  `border_width` and `border_color`; the clear path puts only the width back.
  Release a drag over the sidebar or the items pane and no redraw follows, so
  the last-hovered box keeps the hover colour at 1px for the rest of the
  session — the "subtly different from its neighbours" outcome the docstring
  says the method exists to prevent. Low: a successful drop hides it, because
  `load_blocks` rebuilds the frames.
- **`block_item`'s no-box branch has no UI caller** (`plan.py:518`,
  `/code-review`, low). Every drop names the box under the pointer, so
  `slot_index=None` is reached only by tests and by the API shape it shares
  with `add_padding_block`. The docstring claiming an item-row double-click
  used it was wrong and is now corrected — there has never been such a
  binding. Decide one way or the other: add the double-click (a plain click on
  an item row currently does nothing and says nothing) or delete the branch.
- **`_next_block_position` and `_next_position_in_slot` do not say which is
  which** (`db_manager.py:1321` and `:1397`, `learning-qa`, low). One counts
  day-wide, the other per-box, for a single column that now means both things
  depending on whether `slot_index` is NULL. Traced and coherent — the
  day-wide counter only ever applies to blocks with no box, where a per-box
  counter has no meaning, and `test_a_new_block_with_no_box_is_ordered_but_not_placed`
  pins it — so this is a naming hazard for the next reader, not a defect.
- **`sort_blocks_by_slot` uses a bare `10**6` sentinel for "unplaced"**
  (`time_block_layout.py:708`, `learning-qa`, low). A named constant would say
  what it is (P4).
- **`test_bad_lunch_length_falls_back_or_clamps` asserts only `>= 0`**
  (`tests/test_time_block_layout.py:322`, `learning-qa`, low). For three
  different bad inputs it cannot distinguish the fallback-to-60 case from the
  clamp-to-0 case its own name offers as the alternative. It is still
  mutation-killable — removing `max(0, ...)` turns `-10` red — so it is not a
  dead guard, just a loose one (P29 family). **Pre-existing, not introduced by
  this batch.**

## Deferred from the grid rebuild (2026-11-05)

- **Four tasks to a box is a constant nobody is told about.**
  `MAX_BLOCKS_PER_SLOT = 4` in `time_block_layout.py`. A fifth drop on a box is
  refused with *That half hour is full — try another box*, which does not name
  the number, and nothing in the UI or Day Settings does either. Low: the
  refusal is clear about what happened, just not about the limit. Either say
  the number in the message or make it a day setting.
- **No way to tidy a day.** Gaps are legitimate by design (decision 1), so
  nothing packs them away — which means there is also no single action for "pull
  everything up", and a day re-planned around a cancelled task has to be dragged
  box by box. Low, and deliberately out of the approved plan: compaction is a
  user choice, not a layout rule. The arithmetic for it is in the git history of
  `pack_day` if it is wanted.
- **A block adopted from the old model can sit outside the day with no obvious
  next step.** `adopt_legacy_day` leaves a block's box `NULL` when the time it
  names will not hold it, so it lands in the *Outside the day* group with
  *drag onto a box to place*. Correct, and it is the surfacing P2 asks for — but
  the user has to work out for themselves that shortening it may be what is
  needed. Low: a one-line hint naming the reason per block would close it.
- **A clamped Work Block is no longer reported.** `block_item` used to say
  *Blocked 1440m for X (Work Block of 5000m is longer than a day)*. The grid
  rewrite dropped that branch **and** its test
  (`test_a_capped_work_block_is_reported_not_quietly_applied`), and the
  retirement table lists neither — found by this batch's own pre-push sweep,
  not foreseen in the plan. Low rather than medium because the case is now
  nearly unreachable: 1440 minutes needs 48 boxes, so in any day shorter than
  a full 24 hours the drop is refused for not fitting and the user is told
  that. It survives only in a 00:00–24:00 day, where the block is placed at
  1440 with nothing said about the 5000 that was asked for.

### From the pre-push review sweeps on this batch

Severity-rated before any fix was written. Everything medium and above was
fixed in the same session with a test; these are the rest. Each names the pass
that found it — `/code-review` for correctness, `learning-qa` for the
failure-pattern catalogue.

- **`total_planned_minutes` and the grid disagree about an unusable length**
  (`src/getmoredone/time_block_layout.py`, `/code-review`, low). *Rewritten
  2026-11-05: the second party was `pack_day`, which the grid deleted.* The
  summary arithmetic falls back to **0** for a block whose `planned_minutes` is
  zero or unparseable, while `slots_for_minutes` falls back to
  `FALLBACK_BLOCK_MINUTES` and gives it a box. The day summary now prints both
  numbers side by side, so such a block is counted in *occupied* and missing
  from *planned* — the disagreement is on screen rather than inferred. Low:
  nothing in the app can create one, it takes a hand-edited row. Note the old
  mitigation ("the next repack corrects the drawing") is gone with the packer —
  nothing repacks. Worth making the fallback one function both call.
- **`db_manager` commits unconditionally in places** (`/code-review`, low).
  Some writers call `commit()` rather than taking `commit=False` and deferring
  to `transaction()`. Pre-existing and untouched by this batch; the four screen
  writes this batch added are now inside transactions. Low until a caller needs
  one of those writers to be part of a larger unit.
- **Deleting an action item that holds a time block raises** (`database.py`,
  `learning-qa`, low-medium). `time_blocks.item_id` references
  `action_items(id)` with no `ON DELETE` clause and foreign keys are on, so
  `delete_action_item` raises `IntegrityError` for an item with a block. The
  item editor calls it bare inside a Tk command, so the traceback goes to
  stderr, the dialog never closes its own way, and the user sees a confirmation
  that did nothing and said nothing. Pre-existing — `87ae093`'s Plan screen
  also created blocks — but this batch makes creating one a single drag, so a
  latent crash becomes reachable in ordinary use. Flagged, not fixed, per
  global rule 10: the fix is a schema decision (cascade, set null, or refuse
  with a message), not a line.
- **A failed settings write is reported as success** (`app_settings.py`,
  `learning-qa`, low-medium). `save()` swallows a write error with a `print`
  and returns `None`, so on a read-only or full disk the Day Settings dialog
  closes, the day re-times itself, and the preference is gone at next launch.
  Wants `save()` to return a bool or raise, and the dialog to stay open with
  the message in its error label.
- **The migration guard's stated reason has no test** (`database.py`,
  `learning-qa`, low-medium). The per-column guard exists because an
  interrupted earlier run can leave a database with `block_type` and not
  `position`. The six schema tests cover fresh, fully-legacy, idempotent and
  CREATE-TABLE-alone, but never that half-migrated state — so collapsing the
  loop into a single `if 'block_type' not in columns:` would keep every test
  green while leaving such a database permanently without `position`, which by
  that test file's own words "would not fail loudly — it would make every
  reorder a no-op". Wants a fixture that ALTERs only `block_type` on before
  `initialize_schema`.
- **The 60-item cap drops the unscored items first** (`db_manager.py`,
  `learning-qa`, low). `get_items_for_start_date` orders by `priority_score
  DESC`, and an item missing any one of its four factors scores 0 — absence of
  information, not low priority. So an unscored item on a day with more than 60
  items cannot be dragged at all. The cap announces what it dropped and that is
  tested; what it has no stated justification for is the number, and the item
  pane is already scrollable, so the cap may not need to exist.
- **A source guard matches an unanchored substring**
  (`tests/test_time_block_colors.py`, `learning-qa`, low). One assertion tests
  `"def priority_band_colors" in path.read_text()`. The count is exact rather
  than a floor, which is the part that matters, but the project rule asks for
  an AST walk or a whole-line anchor; line 160 of the same file already parses
  with `ast`.
- **`Status.OPEN` exists and the query uses the literal `"open"`**
  (`db_manager.py`, `learning-qa`, low). Correct against `models.py` today, but
  a renamed status would silently empty the Plan screen's left pane rather than
  fail.

### From the re-sweep of this batch's own fix commits

A fix commit is the least-reviewed code in a change — written last, in the
most anchored state — so the fixes above were themselves swept. That pass
returned no high-severity finding, three mediums (all fixed with tests), and
these four. Each was severity-rated before any fix was written.

- **A rolled-back write says nothing unless it was a slot refusal**
  (`src/getmoredone/screens/plan.py`, low). *Rewritten 2026-11-05:
  `DayTooFullError` is gone; the four write paths now catch `SlotRefusedError`,
  two of them `ValueError` as well.* Any other exception inside those
  transactions rolls the write back and propagates into Tk's callback
  machinery. Nothing in the app installs `report_callback_exception`
  (re-verified 2026-11-05: still no occurrence anywhere in `src/`), so the
  traceback goes to stderr and the user sees a click that did nothing and said
  nothing. Low because no other exception class is reachable through those
  paths today; the fix is one default handler for the whole app, not more
  `except` clauses, which is why it is not a line.
- ~~**The settings file is written before the days are re-timed**~~
  **Resolved by the grid rebuild (2026-11-05).** `save()` still writes the file
  before `on_saved` runs, but `on_settings_saved` now writes nothing: a block's
  box is stored relative to Day Start, so there is no re-timing left to refuse
  and no stored day that can disagree with the file.
- ~~**`set_block_minutes` has no ceiling of its own**~~ **Resolved by the grid
  rebuild (2026-11-05).** The ceiling no longer depends on the caller:
  `db_manager.set_block_length` calls `clamp_block_minutes` itself before it
  writes, so a third caller passing an unbounded number is clamped at the
  write. (The day-level guard this entry credited is gone — the grid is bounded
  by Day End, so a day that cannot be written is unreachable.)
- ~~**`add_padding_block`'s capped-default report cannot fire**~~ **Resolved
  by the grid rebuild (2026-11-05), by deletion.** The dead
  `requested > minutes` branch is gone from `add_padding_block`. Its
  `block_item` sibling's report — the one that did fire — went with it, which
  is the new entry under the grid rebuild's deferrals above.

### Adjacent, found while proving the fixes above (2026-11-05)

- **`AppSettings.load()` swallows programming errors and resets every
  setting** (`app_settings.py:151`). The whole load, normalisers included, is
  wrapped in `except Exception as e: print(...)` and falls through to a
  defaults object. So a `NameError` or `AttributeError` in any normaliser does
  not surface as a crash — it silently discards the user's entire settings
  file for that launch, with one line on stderr. Found because a mutation test
  of the day-bounds normaliser came back **green**: the mutant was invalid code
  that raised `NameError`, the broad `except` ate it, the defaults satisfied
  the assertion, and the test passed for the wrong reason. Pre-existing and
  outside this batch's scope, so flagged rather than fixed per global rule 10.
  Wants the corrupt-file cases (`JSONDecodeError`, `OSError`) caught narrowly
  and everything else allowed to raise. Note that any test asserting a
  fallback-to-default behaviour through `load()` is weakened by this until it
  is fixed.

## ✅ Cleared 2026-08-25 — the five deferred from the timer-endings batch

All five fixed and pushed the same day they were recorded. Kept as a list
rather than deleted, so the entries below can be read as a record of what was
deferred and for how long, not only of what is outstanding.

- **A test failing on a timer ending path hung the run.** conftest silenced
  `grab_set`/`lift`/`focus_force`/`-topmost` and left `tkinter.messagebox`,
  which is the same class. Neutralised for the run; the fifteen tests that
  patch it themselves still win.
- **The complete-and-create follow-up landed unfiled from its project.** The two
  copy paths disagreed about what "made from an item" means; they share
  `inherit_derived_item_context` now.
- **`_cleanup_and_destroy` detected a surviving window and told nobody.** It
  returns the answer, and the ending lowers a stuck timer before raising the
  follow-up's editor over it.
- **Nothing guarded a second timer window on one item.** `TimerWindow.open_for`
  plus a weak registry, wired through all four openers.
- **`NextStepsDialog` was dead code.** Deleted.

## Deferred — found by review, deliberately not fixed

### Found during the demo-install launch check (2026-11-05)

- **The window title reports how the app was built, not which data it
  opened.** `src/getmoredone/app.py:43` sets
  `"[PROD]" if getattr(sys, "frozen", False) else "[DEV]"`, so a plain
  `./start.sh` on the real database and `./start-demo.sh` on the demo both
  show `daVIPA [DEV]`. Observed with both instances running side by side. For
  a feature whose point is telling two instances apart, the most visible
  signal is the one that does not. Low: the launcher's guard is what prevents
  the dangerous case, and this only makes two safe states look alike. A fix
  would derive the tag from `app_data_dir_path()` rather than `sys.frozen`,
  and would need a test that a demo-directory launch and a production launch
  produce different titles.

### Deferred from the demo-install cold review pass (2026-11-05)

Two cold read-only passes over the four fix commits `df93846..d3f8ec0` — one
on test quality, one on the two launchers read as programs — produced 21
findings. Every high and medium one was fixed with a test except the two
recorded here; the lows follow.

**An interrupted seed that got as far as its first insert is never retried
(medium).** `start-demo.sh` seeds when the demo database holds no action
items. `load_demo_data()` calls `create_action_item()` per item with no
surrounding transaction, so a Ctrl-C part-way commits what it had written: the
count is then positive, the launcher reports `seed=no`, and the demo stays
permanently short of its six items with no signal to the user beyond the
documented `rm -rf` reset.

Deferred rather than fixed, with the reason stated at the time: both remedies
reach past this feature. A completion marker makes "has items but no marker"
ambiguous for every demo seeded before the marker existed, and reseeding those
would double their items; wrapping the insert loop in one transaction changes
`demo_data.load_demo_data()`, which the in-app Settings button shares. The
residual failure loses no real data, is visible (a short demo), and is
recoverable by the documented reset. Fix it by making the seed atomic in
`demo_data.py`, with the Settings button in scope, not by patching the
launcher.

**`start.sh` does not `cd` to its own directory (medium, pre-existing).** Every
path in it is relative to `$PWD`, so `bash ~/ProjectsLocal/daVIPA/start.sh`
from elsewhere creates a `venv/` in the caller's directory, then reports a
missing `requirements.txt` as a network problem — and `find . -type d -name
"__pycache__" -exec rm -rf {} +` would run against that directory. One line
fixes it (`cd "$(dirname "$0")" || exit 1`, which `start-demo.sh` already
has). Adjacent, not swept into this batch: it predates the demo work and
`exec ./start.sh` is unaffected, because the demo launcher cds first.

**Lows, recorded not fixed**, per the rule that a cosmetic fix buys none of
the safety it costs:

- `start.sh --print-env` reports `data-dir=` empty when neither variable is
  set, rather than the production directory the launch will use. The flag
  answers "where would this go" only for `db=`.
  `test_d2_start_sh_default_db_is_unchanged_with_no_env` asserts the empty
  string, so it changes in the same commit.
- `test_d2_demo_launcher_expands_a_tilde`'s second assertion,
  `not (REPO_ROOT / "~").exists()`, cannot fail for the defect it names (the
  `mkdir` now runs after the `--print-env` exit) and asserts on shared
  checkout state, so an unrelated stray `~` directory fails it.
- `start-demo.sh`'s `command -v python3` preflight is untested; its whole
  value is its message, and without it the user gets a silent exit 1.
  `_print_env(..., PATH="/nonexistent")` would reach it.
- `test_d2_demo_launcher_reseeds_a_database_with_no_items` discards `_seed()`'s
  exit code, so a broken seeder surfaces as `sqlite3.OperationalError: no such
  table` from the next line rather than as the subprocess failure it is.
- `test_d1_blank_override_is_ignored` writes outside its `tmp_path` *when it
  fails*: without `.strip()` the resolver mkdirs a whitespace-named directory
  in the checkout. `monkeypatch.chdir(tmp_path)` contains it.
- `test_d1_the_suite_runs_with_no_data_dir_override` proves a nested run, not
  "the suite", and is coupled to the two hook names `_run_nested_pytest`
  re-exports, so moving the pop into `pytest_configure` would turn it red
  while isolation still held.

### CI has been red for longer than anyone noticed (2026-11-05)

The `Tests` workflow fails **7 of 1630** on every Python version, and has done
since before this batch — the same seven failed on `47ff250` and on at least
four commits before it. All seven assert a window-manager attribute that the
headless CI display never honours: `-topmost` reads back false where the test
set it true, and `-alpha` reads back `1.0` where the test set `0.0`.

- `test_t51_a_modal_drops_the_timers_always_on_top`
- `test_t52_the_timer_is_topmost_again_afterwards`
- `test_t56_a_second_modal_does_not_hand_the_flag_back_early`
- `test_t57_an_unbalanced_resume_does_not_break_the_next_modal`
- `test_alpha_still_passes_through_the_attributes_wrapper`
- `test_raw_tkinter_windows_are_hidden_and_registered_too`
- `test_wt_m6b6_a_notice_lowers_an_always_on_top_parent`

Rated medium, and deliberately not fixed in this batch, which changed none of
that code. It matters because a red build nobody can distinguish from a real
failure is the state the global rule names as worse than no CI: this batch's
own run could only be read as clean by counting the failures and comparing
them to the base. Either have these seven skip where the window manager does
not honour the attribute — the repo already has
`GETMOREDONE_NO_MAPPED_WINDOWS` for exactly this class — or assert the
wrapper's recorded intent rather than the attribute read back.

### The demo tests hash the whole production database (2026-11-05)

`tests/test_demo_install.py::_fingerprint` does `read_bytes()` + sha256 on the
real `getmoredone.db` before and after the seeding tests. Reading production is
allowed and the assertion is the right one, but `conftest._user_data_fingerprint`
deliberately digests only `settings.json` and documents why the guard has to
stay cheap — so this is two full reads and hashes of a 914-item database per
run for information that `(exists, size, mtime_ns)` already carries.

Rated low: correct, just wasteful. Match conftest's split — size and mtime for
the database, a digest for settings. Found by the failure-pattern sweep over
the data-directory override.

### An ambient `GETMOREDONE_DB` is honoured by the test session (2026-11-05)

`conftest.pytest_sessionstart` points `GETMOREDONE_DB` at a temp database only
`if not os.environ.get("GETMOREDONE_DB")`. A developer who has exported that
variable — which `docs/DEV_PROD_WORKFLOW.md` tells them to do for the dev
database, and which `start-demo.sh` now exports for the demo — has the suite
run migrations, a row-deleting dedupe and a date-moving repair against that
database. The live-data guards do not fire, because the named database is not
the production one.

Pre-existing, not introduced here, but this batch makes it easier to reach by
adding a second populated database and a launcher that exports the variable.
Rated medium-low and deferred rather than fixed in-loop: the fix is a policy
decision (refuse, warn, or override) that belongs with whoever owns the dev
workflow, not a correction to this change. Found by the failure-pattern sweep
over the data-directory override.

### `test_audio.py` references an undefined name (2026-11-05)

`tests/test_audio.py:87` reads `getattr(settings, "music_volume", 1.0)`, and
nothing in that test binds `settings` — it would raise `NameError`, not fail an
assertion. It has never fired because the line is reached only when the real
settings file names a music folder that holds a playable track, and the earlier
skip paths catch every other case, including on CI. So a developer who
configures a music folder is the one who meets it. Either load the settings the
test already resolves the path from, or drop to a literal volume. Found while
mapping the data-directory override (low); outside that change, not fixed
in-loop.

### `project_time_line`'s guard tests presence, not value (2026-08-25)

It checks `"session_count" not in row` and then reads `row.get(...) or 0`, so a
row where the key is *present but None* renders the exact `Time: 0 sessions | 0m`
the guard was added to remove. Unreachable today — both producers use `COUNT(*)`
(never NULL) and `COALESCE(SUM(...), 0)`. Separately, `sqlite3.Row` has no
key-based `__contains__`: `"session_count" in row` iterates its *values*, so a Row
returns None even when the columns are there. Both call sites pass a `dict` and
the type hint says `dict`, so this is latent. One line closes the first half:
`if row.get("session_count") is None or row.get("total_minutes") is None`. Found
by the csdp re-sweep (low). Not fixed in-loop, per the below-medium rule.


### An item on two projects gives its full time to both (2026-08-25)

`project_board_items` is many-to-many, so the Time line on each board counts the
whole of a shared item's sessions. Project totals therefore do not sum to a
person's real time. Defensible — each project genuinely absorbed that work — and
it matches the user-guide wording, but the semantics are pinned nowhere, and this
same screen's `_refresh_multi_link_notice` treats multi-board items as an anomaly
to be re-filed. One test asserting the chosen behaviour would stop a later change
flipping it silently. Found by the csdp sweep (low 3).

### A session under a minute counts as zero time (2026-08-25)

`save_work_log` stores `work_seconds_elapsed // 60`, so two 40-second sessions
render "2 sessions | 0m". Pre-existing, but the Time line is the first surface to
present the sum as "total time" and the user guide does not mention it. Either
store seconds or say so in the guide. Found by the csdp sweep (low 5).

### `format_minutes` clamps a negative total to "0m" (2026-08-25)

Only reachable by direct SQL or an import — the one writer cannot produce a
negative — but a negative row would silently offset positive sessions in the same
project before the clamp ever applies. Recorded so it is not mistaken for a live
defect later, and so the clamp is not read as validation. Found by the csdp sweep
(low 4).


### The topmost-suspension helper lives in the wrong module (2026-08-25)

`week_collision_notice` now lowers an always-on-top parent before showing a
notice, but it has to import `parent_topmost_suspended` from
`timer_window_dialogs` *inside the function* — a top-level import would be a
cycle, since `timer_window_dialogs` imports the notice module. The helper is
generic and belongs in `utils/`, with `timer_window_dialogs` re-exporting it for
the AST guards that scan that file by name (`test_t54`, `test_t55`). Deferred
because moving it at the end of a batch risks those guards for no behavioural
gain. Found by the csdp re-sweep (M1).

### `test_n26`'s strftime count gives wrong advice when it fires (2026-08-25)

It asserts exactly one `.strftime` call in `timer_window.py`. Correct today and
mutation-proved, but any future *legitimate* `strftime` in that module goes red
with "the date format is written in N places; it belongs in day_stamp alone",
which would be misleading. It is also blind to a duplicate written as an f-string
format spec (`f"{d:%m-%d}"`). Anchoring on the literal `"%m-%d"` as an AST
`Constant` would be both stricter and better-worded. Found by the csdp re-sweep
(L4).


### `_append_session_note`'s empty-string guard is unreachable (2026-08-25)

It reads `if not note or not note.strip(): return`, but `CompletionNoteDialog.save`
already normalises an empty box to `None`, so `dialog.result` is never `""`.
Mutation-proved during the csdp sweep: weakening the guard to `if note is None`
leaves every test green, and `test_n23` covers only the Skip → `None` path. Its
docstring claims more than it shows. Either drop the unreachable half or add a
direct call with `"   "` and pin it. Found by the csdp sweep (F9).


### `adopt_opener` is unguarded directly above the guard that explains why (2026-08-25)

`open_for` wraps its `deiconify`/`lift`/`focus_force` in a try, with a comment
saying an escape from there reaches a screen that has no handler. One line
above it, `live.adopt_opener(...)` is unguarded, and it calls
`db_manager.get_action_item`, which can raise on a DB error — the same P5 shape
on the adjacent line. Likelihood is low (both openers fetched the item
successfully moments earlier) and the consequence is a traceback plus an
unraised timer, not data loss. It cannot leave a half-updated item: the
`setattr` loop over `dataclasses.fields` has nothing in it that can throw.
Found by the csdp fourth pass.


### The callback dedupe only catches the immediately-previous opener (2026-08-25)

`adopt_opener` compares `on_close == self.on_close_callback`, which stops one
screen chaining itself repeatedly. Once a *second* opener chains,
`self.on_close_callback` is the `both` closure and the first opener's bound
method no longer compares equal to it — so alternating openers grow the chain
again. Measured: two screens alternating over five presses ran
`['A','B','A','B','A']` for one close. Duplicated refreshes, no data loss, so
below medium. Fix shape: keep an ordered list of adopted callbacks and test
membership with `in`, instead of nesting closures. Found by the csdp third pass.

### The pop-out notes window is not refreshed by a timer reuse (2026-08-25)

`adopt_opener` refreshes the timer's own notes box but not
`NextActionWindow.notes_text`, which is filled once at construction. With the
pop-out open across a reuse it shows the pre-edit description, and pressing
Save there writes that stale text over the editor's save. Narrower than the bug
it neighbours — the user has to press Save on visibly stale text, and closing
the pop-out does not auto-save. `refresh_notes()` already exists; calling it
under the same untouched rule closes it. Found by the csdp third pass.

### `_save_notes_to_item` strips one side of its comparison (2026-08-25)

`notes` is stripped and `self.item.description` is not, so a stored value with
surrounding whitespace never compares equal and every ending fires a redundant
`update_action_item` plus `notify_weekly_tactic_changes`. Content-preserving.
One-line fix: `if notes != (self.item.description or "").strip():`. Pre-existing,
but the reuse path now re-seeds the box from an unstripped DB value, so it is
reachable where it was not before. Found by the csdp third pass.


### Reusing a timer does not update its clock (2026-08-25)

`adopt_opener` re-reads the item, but `time_block_minutes`,
`work_seconds_remaining` and the time-block entry are set in `__init__` and are
not touched on a reuse. So editing planned minutes from 30 to 90 and pressing
Timer again gives a window whose data says 90 and whose clock still counts 30.
Measured during the csdp re-sweep (finding 8). Not fixed in that batch because
changing the clock underneath a session that may already be running is a
behavioural decision, not a repair: a reuse mid-session should probably leave
the clock alone and only adopt the new duration when the timer is stopped.


### Legacy `" - Followup"` titles stack once under the new stamp (2026-08-25)

Rows already in the user's database carry the old undated `" - Followup"`
suffix, which `FOLLOW_UP_SUFFIX_RE` does not match. A follow-up of one of those
becomes `"X - Followup - Follow up 08-25"`. It stacks exactly once and then
stabilises, because the second stamp *is* matched next time. Cosmetic and
bounded, but it is the stacking the once-only rule existed to prevent. Fix is
either a second alternation in the regex or a one-off title migration. Found by
the csdp sweep of the backlog-clearance batch.

### Three hand-kept lists of messagebox names must agree, and do not (2026-08-25)

`conftest._MESSAGEBOX_DEFAULTS` neutralises 8 functions;
`test_tk_offscreen.ALLOWED_NEUTRALISED_DIALOGS` names 4; the `window_makers`
seed set in the same file names 7, omitting `askyesnocancel` which conftest does
patch. A future test calling `messagebox.showinfo` — patched, recorded, entirely
safe — turns `test_no_helper_builds_a_window_the_suite_cannot_reach` red with a
false alarm, on a guard people are meant to trust. It is the "two lists that
drift" defect B1 was written to remove, reintroduced one file over in the same
batch (P5). Fix: derive both sets from `_MESSAGEBOX_DEFAULTS`. Found by the csdp
sweep (F7).

### The `messageboxes` fixture yields the whole session's history (2026-08-25)

`yield _MESSAGEBOXES` hands over every record since session start, and only
tests that *request* the fixture truncate; `test_b51b` does not, and leaks three
records that survive to session end. So `any(f == "showerror" ...)` searches
everything every earlier test recorded. Latent rather than live today — measured
`showerror=0` at the moment `test_b52` runs, and its mutation still goes red —
but the first test that records a `showerror` without requesting the fixture
makes `test_b52` permanently unfalsifiable. Fix: yield a per-test slice. Found by
the csdp sweep (F8).

### `test_b25`'s docstring claims more than it checks (2026-08-25)

It says "a fifth opener added without going through `open_for` fails here". It
parses four hardcoded modules, so a fifth screen constructing `TimerWindow(...)`
is invisible to it. The claim is true by accident today — only those four files
reference `TimerWindow` in `src/` — which is exactly the condition under which it
goes stale unnoticed. Fix: glob `src/getmoredone/screens/*.py`, keep the
exact-set assertion. Found by the csdp sweep (F9).


### test_rm3d's importability probe is order-dependent (2026-08-24)

`test_rm3d_every_test_file_is_importable_on_its_own` strips the repo root from
`sys.path` before importing each test file, then walks them alphabetically. A
file that imports `conftest` to re-establish the path only passes if an earlier
file already put the root back — so the guarantee holds for most files by
ordering luck rather than by each file being self-contained. Found by adding
`tests/test_after_tracker.py`, which sorts first and therefore failed where
`tests/test_connection_leak.py`, doing exactly the same thing, passed. The
probe should re-insert nothing and every file should bootstrap its own path, or
the probe should reset `sys.path` to a known state between files.

### Below-medium from the window-leak sweep (2026-08-24)

- **`_init` runs twice for every CTk/CTkToplevel.** `CTk.__init__` calls
  `tkinter.Tk.__init__` before setting `_window_exists`, and `CTk.withdraw`
  reads it — so the first withdraw raises `AttributeError` into the swallow.
  Harmless (the outer one succeeds) and completely invisible.
- **conftest's restore path does not actually un-patch.** `cls.attributes`
  resolves to the inherited `Wm.wm_attributes`, so `setattr` on teardown leaves
  an own attribute on each class. Semantically identical; pre-existing shape,
  shared by `lift`/`focus_force`/`grab_set`/`deiconify`/`update`.
- **The sweeper discards its count.** A single long test can still hold many
  windows at once with no signal (P2).
- `timer_window.py` still prints `[ERROR] Save & Close failed` after the rename.
- `test_clearing_the_notes_box_clears_it_on_every_ending` covers 2 endings of 5
  while its name and docstring say every/four.
- `test_the_sweeper_survives_a_root_destroyed_with_its_children` relies on
  `WeakSet` iteration order to reach the exception path.
- `test_deiconify_puts_the_window_back_out_of_sight` is parametrized over the
  ctk pair only, not the newly patched `tk.Tk`/`tk.Toplevel`.
- The `_WINDOWS_MAY_BE_MAPPED` escape in `_deiconify` is only covered by the
  three `mapped_windows` tests — the ones developers are told to skip locally,
  so that guard exists only in CI.
- **Cancel Timer discards typed notes with no in-app signal.** The behaviour is
  as specified ("Cancel means nothing happened") and the user guide says so
  explicitly, but the other three endings persist them, and the label names the
  timer rather than the notes. A dirty-check confirmation would close it.

### ~~What else may be leaking~~ — FIXED 2026-08-24

All four are closed. Kept rather than deleted, because the reasoning is the
useful part: the window leak was a resource hidden rather than released (P30),
and these are the same question asked of every other finite resource.

- ~~**`pygame.mixer.init()` is never matched by `mixer.quit()`.**~~ Fixed:
  `utils/audio_playback.release_audio_device()`, called from
  `daVIPAApp.on_closing`. At app shutdown rather than when a timer window
  closes — the mixer is process-global, so a per-window release would cut the
  music of any other timer still open. Unloads before quitting; `quit()` alone
  leaves the loaded track's file handle held.
- ~~**24 uncancelled `after(...)` callbacks.**~~ Fixed: `utils/after_tracker.
  TrackedAfterMixin` gives a window `tracked_after`, and its `destroy()`
  cancels whatever is still pending. Applied to the four sites that schedule
  seconds into the future on a window the user can close first — the timer's
  flash chain and save-notes reset, `NextActionWindow`'s reset, and the item
  editor's error-label reset. A test parses for any *discarded* `self.after`
  handle of a second or more, which is the real signal; the timer tick keeps
  its handle in `update_timer_id` and is cancelled by a different mechanism.
- ~~**11 test sites holding an open SQLite connection.**~~ Fixed by a net
  rather than 11 edits, for the same reason as the window sweeper: it covers
  the helpers, the failure paths, and the twelfth. conftest registers every
  `DatabaseManager` and `VPSManager` at construction and closes any left open
  at the end of the test, with a session-scoped assertion that none outlives
  the run.
- ~~**`VPSManager` teardown unaudited.**~~ Covered by the same net; five
  functions built one without closing it.

Original text follows for the reasoning:

- **`pygame.mixer.init()` is never matched by `mixer.quit()`.** One call, in
  `screens/timer_window.py:1490`; `quit` appears nowhere in `src/`. The audio
  device is opened for the life of the process. Strongest sibling of the window
  bug: a finite OS resource acquired and never returned, invisible because
  nothing about it is on screen.
- **24 uncancelled `self.after(...)` callbacks across the screens.**
  `_flash_window` schedules four out to +1300 ms, `save_notes` a +2000 ms button
  reset in both the timer and the pop-out notes window. Only the celebration set
  and `update_timer_id` are tracked and cancelled. A window destroyed inside one
  of those intervals leaves the callback firing at a dead widget — the "invalid
  command name" the celebration module's docstring exists to avoid, at every
  site that was not hardened.
- **11 test sites build a `DatabaseManager` and never `close()` it**, holding an
  open SQLite connection and its file handle: `test_defaults_regression`,
  `test_scheduler_project_attach::_build_screen`, `test_settings_isolation`,
  `test_today_pin_drag::_make_screen`, `test_today_screen` (×2) and the
  `test_live_data_guard` self-checks. Harmless at this scale — a few dozen fds —
  but it is the same shape and would bite on a suite ten times the size.
- **`VPSManager` is constructed 28 times in tests** and its teardown was not
  audited. Worth the same check.


### reward protocol: below-medium findings and deferred scope (2026-08-24)

Graded below medium and kept out of the change, per the review-sweep rules — a
cosmetic fix is new unreviewed surface and buys none of the safety it costs.

- ~~`continue_action` builds its own `WorkLog` inline~~ — **fixed, and this entry
  was wrong.** It said the inline row "correctly carries no reward columns".
  That is true of `deliverable_completed`, `savor_delivered` and `phase`, but
  `deliverable_snapshot` is not reward-fired: the sibling Stop → Finished path
  writes it with `deliverable_completed=0`, so the identical session ended the
  other way recorded nothing about what it was for. The duplicate item it
  creates was also missing `deliverable` entirely. Both fixed in `9f7b5f3`;
  `continue_action` now routes through `save_work_log`. Kept here rather than
  deleted, because a backlog entry that mischaracterises a gap is worse than no
  entry — it reads as a decision already taken.
- **`tests/test_timer.py`'s `db_manager` fixture uses `tempfile`, not `tmp_path`.**
  Explicit, so it does not reach the user's real database, but it leaks the file
  if a test raises between `yield` and `unlink`.
- **Two dead `.gitignore` lines**, `./audio/` and `./venv/`. A pattern containing
  a slash is anchored to the file's own directory, so both look for a directory
  literally named `.` and neither has ever matched anything. Left alone while
  fixing the `audio/` rule beside them, rather than widening that diff.
- **Spec §7.2 — phase generalisation.** A new project in a familiar category
  ideally starts part-way into Phase 1 (partial transfer). Out of scope for v1;
  would be a manual `phase_override` or a `savor_count` seed.
- **Spec §7.1 — multi-board savor counting.** An item filed under several boards
  counts towards the oldest link only. In practice filing is exclusive on every
  surface, so this affects rows created before that.
- **The Deliverable field is not on `screens/inline_editors.py`.** A recorded
  decision, not an oversight — the timer captures one at start where it matters.

### reward protocol: low findings from the two cold review passes (2026-08-24)

Graded low and deferred. Everything medium or above from those passes was fixed
in `9f7b5f3`.

- **A project deleted mid-session writes a row indistinguishable from an
  unlinked one** (`timer_window_reward.py`). Both produce `phase=NULL`,
  `savor_delivered=0`, `celebration_type=NULL`. Only a log line — gone on the
  next launch — separates "the protocol could not run" from "there was no
  protocol". A distinguishable `phase` value would make the audit trail able to
  answer the question it exists for.
- **`finished_action`'s window-already-destroyed branch returns without
  `_cleanup_and_destroy`**, so `cancel_celebration()` is skipped. Latent, not
  live: the only route into that branch comes through `on_window_close`, which
  has already cancelled.
- **The sibling `after` chains are still untracked** — `_flash_window` schedules
  four callbacks out to +1300 ms, and `save_notes` (in both the timer and the
  pop-out notes window) schedules a +2000 ms button reset. None is registered
  and none is cancelled on destroy. Pre-existing, but P5-shaped: the celebration
  hardened one member of the class and left the siblings.
- **The celebration is largely occluded.** `CompletionNoteDialog` opens
  milliseconds later, topmost and centred on the same window, so ~1.5 s of
  confetti animates behind it. Fixing it means either delaying the dialog or
  drawing the celebration somewhere else — both bigger than the finding.
- **`test_rp45f_celebration_length_is_short` takes `host` and `monkeypatch` and
  uses neither**, building a real Toplevel for a constant comparison.
- **The Deliverable placeholder is 60 characters** in a single-line entry in the
  narrow left column of the item editor. May clip; not verified either way,
  since it needs a real window manager.
- **`save_work_log`'s early return leaves the flags set.** Every other exit
  clears them. Not reachable today — Done is hidden when the timer is stopped,
  and Start clears them anyway — but the asymmetry is what turns into a bug when
  a new caller appears.
- **A transient database error at Start silently downgrades a tracked session.**
  `prepare_reward_session` catches, logs, and returns True with
  `session_board_id` still None, so the whole session runs with no deliverable
  dialog, no snapshot and no counter. Deliberate — the alternative is a Start
  button that does nothing — but it is the transient-becomes-terminal shape
  (P1), and only a log line records it.
- **Four of the newer timer tests have no `try/finally: timer.destroy()`**,
  unlike the rest of the file; they lean on the `root` fixture to clean up. One
  also restores a patched method on a plain line rather than in a `finally`, and
  names the good method `broken`.
- **`self.item` is never reloaded while the timer is open.** If another screen
  edits the description and the user then changes the timer's notes box, the
  timer's stale in-memory copy overwrites the external edit on save. Pre-existing
  for any differing edit; clearing the box is one more trigger now that a
  deletion is persisted like any other change.
- **The savor copy lives in Python source** (`timer_window_dialogs.py`), with
  tests pinning the literals. Global rule 9 says content requiring editorial
  judgement belongs in a config file. The same applies to `WIRING_THRESHOLD` and
  the two probabilities — defensible as constants today, but they are the knobs
  a user will eventually want.


### rename-safe links: low-severity findings (2026-08-20)

From the third review round, not fixed in-loop:

- **`update_segment`'s `vision_segments` lookup is invisible to the RN-M4
  scan.** The insert half of this is done — all four `INSERT INTO
  vision_segments` sites now stamp `segment_description_id` (`vps_manager.py`
  in the third round, `vps_schema.py` in `af9a88e`). What remains is that the
  RN-M4 guard cannot see this lookup at all, so a regression here would not
  be caught by the scan that exists to catch it.
- **`_commit_heal` is safe only inside `DatabaseManager.transaction()`.** Four
  raw `conn.execute("BEGIN")` blocks exist (the three renames and
  `delete_entity_cascade`). No healer is reachable from them today — the code
  now returns early rather than committing when a transaction was already
  open — but the interaction is worth removing rather than guarding.
- **The four `COALESCE` clauses are two redundant copies.** `update_vision_element`
  delegates to its sibling now, so its own mirror `UPDATE`s are dead work.
- **`test_rn_deleting_a_segment_with_plan_elements_is_refused`'s
  `assert ok is False` is weak on its fixture** — the delete already refuses via
  four other tables. Only the `"Annual Plan Elements" in counts` assertion has
  teeth.
- **`backfill_segment_ids` runs its candidate query twice per NULL row** —
  the pre-existing `matches` query was left beside `resolve_segment_id_exact`.
- **`create_segment` allows two life segments whose names differ only by case.**
  That is the root cause of every ambiguity this batch had to handle; a
  case-insensitive guard there would remove the class.


Graded below medium by the two reviews of Batch 4 and deliberately not fixed
in-loop, per the sweep rules — each fix is new unreviewed surface.

- **`link_integrity.add_segment_description_id_columns` returns `False` for
  both "column already there" and "table absent",** so the report cannot tell
  a no-op from a missing table. `test_rn_m1d` is satisfied by either.
- **`counts["duplicate_initiatives"]` counts GROUPS, not rows,** and
  `_log_report` then says "%d duplicate_initiatives need a human" using it.
- **`test_vps_data_integrity.py::test_comprehensive_count` asserts
  `len(tables) >= 6`** — a P29 floor over an enumerable set. This change added
  two qualifying tables and the floor absorbed it silently.
- **`_collected_files`'s `lru_cache` returns a mutable `set`.** No caller
  mutates it today; `frozenset` would keep it that way.
- **`rename_vision_segment` writes `segment_descriptions.name` (UNIQUE) but
  checks for duplicates only against `vision_segments`.** Confirmed again by
  the pre-push re-sweep, which also could not produce a collision through it:
  `sync_vision_segments_with_settings` mirrors every description into
  `vision_segments` at manager init, so the `vision_segments` check covers
  `segment_descriptions` by proxy. It is the **third** writer of that column;
  the other two now share `_refuse_case_collision`. Not guarded here because
  the guard would be unfalsifiable on a synced database, and this batch has
  shown what an untestable guard costs. What makes it worth revisiting is the
  proxy's own weak point: the `UPDATE segment_descriptions … WHERE id =
  (SELECT segment_description_id FROM vision_segments WHERE id = ?)` matches
  nothing when that id is NULL — the state the migration deliberately leaves
  for an ambiguous row — so the two tables diverge silently rather than
  erroring. That silent no-op is the falsifiable part, and the better fix.
- **Whether an Annual Plan Element should block a segment delete** is now
  answered yes (it does), but `annual_vision_elements` blocking too may be
  stricter than intended. Worth a look the first time it refuses.


### Found while closing the rename-safe-links acceptance items (2026-08-20)

Graded below medium and deliberately not fixed in-loop.

- **Segment names longer than 15 characters are clipped with an ellipsis in
  every VSP chip.** `_clip_label(name, 15)` — "Health and Fitness" renders as
  "Health and Fit…". Pre-existing display behaviour, not a rename regression,
  but a user who renames a segment to something descriptive cannot read it
  back. The same static method is copy-pasted into six screen modules
  (`vision_segments`, `vision_elements`, `annual_vision_segments`,
  `ape_assignment`, `ape_period_view`, `weekly_items`) with three different
  limits (15, 18, 20), so widening it is six edits.
- **`screens/vps_planning.py` (51 KB, `VPSPlanningScreen`) has no caller on
  the run path.** `app.show_vps_planning` is a compatibility shim that
  redirects to `show_vision_planning_hub`; the only import is in
  `tests/test_vps_fixes.py`. P21: a component kept alive by its own test.
- **`VPSSchema.initialize_vps_schema` runs twice per launch.** `DatabaseManager`
  and `VPSManager` share one `Database` and both call `initialize_schema`. The
  weekly-tactic and link-integrity migrations are behind a once-per-`Database`
  guard for exactly this; the VSP schema is not. Idempotent today — the second
  legacy pass returns early because `vision_segments_legacy` is gone — so this
  is wasted work rather than a defect. Observed directly by tracing the call.
- **`segment_descriptions.name` permits an empty or whitespace-only name.**
  `NOT NULL` does not exclude `''`. Nothing produces one today, and the branch
  that would have defended against it in the legacy migration was removed
  rather than left untestable (see `a79aeca`). A validation guard in
  `create_segment`/`update_segment` would close it at the source.


### Found by the second cold pass (2026-08-20)

Below medium, or bigger than this batch. Not fixed in-loop.

- **The legacy migration still collapses two case-colliding segments into one
  `vision_segments` row.** Withholding the id stamp stops the row *asserting* a
  life segment it is only half entitled to, and the ambiguity now reaches the
  report — but both sub-segments still hang off the one row, and the second
  one's `vision_elements.key_field` still spells the segment the other way, so
  the tree and the key field disagree. Fixing it means keying `segment_cache`
  by description id rather than lowered name, which changes the shape of
  migrated data. No test covers the residual mis-filing.
- **`backfill_initiative_ape_links` does not guard `_table_exists` for
  `annual_plans`**, which its candidate query joins. Unreachable today —
  `VPSSchema.initialize_vps_schema` runs before it — but a direct call on a
  partial database raises `no such table` inside `initialize_schema`.
- **An initiative whose `annual_plan_id` names no surviving plan is invisible
  to the title match**, because the candidate query inner-joins `annual_plans`.
  It needs a database corrupted by another build: the FK is `NOT NULL
  REFERENCES annual_plans(id) ON DELETE CASCADE` and `PRAGMA foreign_keys` is
  ON at the one connection site.
- **The plan-year tie-break can prefer the wrong initiative.** When two
  initiatives match one plan element by title, the one whose annual plan agrees
  about the year is preferred — a heuristic, not evidence. If the plan element's
  *own* initiative is the drifted one, the tie-break takes the stale twin. The
  batch's base commit did the same; what changed is that the demoted candidate
  is now named in the report instead of being dropped silently
  (`test_rn_m1b1_backfill_surfaces_the_candidate_the_tie_break_demoted`). The
  runtime heal has no report channel, so there it is still silent. Telling the
  two apart needs something the data does not currently hold.


### Found by the pre-push failure-pattern sweep (2026-08-20)

The one medium finding — `update_segment` having no case-collision guard — was
fixed (`2d97da3`). These four were graded below medium and recorded.

- **`NAME_LOOKUP_ALLOWLIST`'s keys are unchecked editorial data.**
  `test_rn_m4a_no_link_resolves_through_a_name` pins `PERMITTED_NAME_LOOKUPS` to
  an exact count, but the allowlist beside it is only checked with
  `len(reason) > 40`. Nothing verifies a key's `file.py::symbol` still exists,
  so renaming or deleting the function rots the entry green — the same failure
  the exact-count comment was written to avoid. Fix by parsing each key's file
  with `ast` and asserting the named function is defined there.
- **`_find_annual_initiative_for_ape` returns two different row shapes.** The
  id path returns `SELECT ai.*`; the heal path returns a row from
  `find_initiative_candidates_by_title`, whose `SELECT ai.*, ap.year AS
  annual_plan_year` carries an extra key that is not a column of the table. All
  four consumers read only `["id"]`, so there is no live defect — but it is an
  implicit contract difference between two branches of one function.
- **A whitespace-only difference in a stored segment name defeats the abstain
  logic.** `_agreed_description_id` strips its bucket key; `resolve_segment_id_exact`
  strips only the needle, not the stored side. So `'Health'` and `'Health '`
  disagree in the bucket — stamp correctly withheld — and then resolve to
  exactly one match in the backfill, which links silently, producing no
  `ambiguous` entry. Needs a legacy database holding an untrimmed name; no
  current app path writes one, and `update_segment` now strips before writing.
- **An initiative whose `annual_plan_id` names no surviving plan is invisible
  to the title match**, and `backfill_initiative_ape_links` does not
  `_table_exists`-guard `annual_plans`, which its candidate query joins. Both
  need a database another build corrupted; the FK is `NOT NULL … ON DELETE
  CASCADE` with `PRAGMA foreign_keys` ON.


### Found by the pre-push re-sweep of the fix commits (2026-08-20)

Its high finding — `update_segment`'s guard freezing a pre-existing collided
pair — was fixed (`897a16c`). Its medium on the untested strip was fixed
(`b5276dc`). These are the rest.

- **`update_vision_segment_admin` is annotated `-> bool` but can now raise.**
  `update_segment` raises a `ValueError` on a colliding rename and on a blank
  name; this caller does not catch, so the exception propagates through a
  `bool` signature to `screens/vision_segments.py::save`, which does catch it
  and shows an inline message. The behaviour is right and the annotation
  under-describes it. Nothing tests that propagation.
- **The blank-name raise is an untested contract change.** `update_segment`
  previously wrote a blank name into `segment_descriptions` and the
  vision-rename branch silently skipped. Raising is better; no test says so.
- **The widget test drives `save_segment()` directly**, so it does not assert
  the Save button is wired to it — only a `callable(getattr(...))` existence
  check covers that seam. One seam short of a full front-end assertion.
- **`_refuse_case_collision`'s message can name a segment the user cannot
  see**: the collision query does not filter `is_active`, so a retired segment
  can be quoted back as the blocker. Pre-existing in `create_segment` and
  inherited by `update_segment`.
- **`exclude_id: str = None` should be `Optional[str]`.**


### Found by the final reviews of the collision guard (2026-08-20)

Its four highs and its medium were fixed. These were graded low and recorded.

- **`update_segment`'s `rollback()` is not gated on an outer transaction.**
  `_DeferredCommitConnection` gates `commit()` but lets `rollback()` through
  to the raw connection, so if a caller ever wrapped `update_segment` in
  `DatabaseManager.transaction()`, the rollback would discard that caller's
  work. Checked: all three call sites (`vps_manager_taxonomy.py:913`, `:948`,
  `screens/vps_segment_editor.py:221`) are outside any `transaction()` block
  and outside the four raw `BEGIN` sites, so this is latent. Same status the
  repo already records for `_commit_heal`, and the same fix would serve both.
- **Renaming a broken row into a *different* existing pair is refused**, even
  though it strictly reduces the number of unresolvable names. That is what
  the stated rule mandates and permitting it would be worse policy, but it is
  the one place the guard is stricter than the harm it prevents.
- **`RENAME_VERDICTS` names its temp database with `abs(hash(...))`**, which is
  not stable across runs. Harmless only because pytest already numbers `tmp_path`
  per test; a stable key would be better.
- **A SQL query split across adjacent string literals is invisible to RN-M4's
  scan**, which regexes the source while Python concatenates at compile time.
  An AST walk over `src/` found exactly one real occurrence hidden this way and
  it was fixed by writing the query as one literal — but nothing stops the next
  one. The scan should parse string constants rather than raw text. Note the
  mirror lookup in `update_segment` is still two literals; no current pattern
  matches it in either spelling, so nothing is hidden today.


### Test-suite remediation leftovers (2026-08-20)

- **Random-order testing is untested.** `pytest-randomly` is not a dev
  dependency and one was not added for this batch. The suite was run with every
  file in reverse order (identical result, no order-dependence), which catches
  gross ordering problems but not seed-sensitive interactions.
- **Two fixtures are named `test_*`** — `test_item` and `test_contact` in
  `tests/test_obsidian_integration.py`. Legal, but a trap: every scanner for
  vacuous tests has to special-case them, and a reader sees a test that returns
  a value. Rename to `sample_*`.
- **Ten tests recorded above from Batch 3 remain unable to fail.** The vacuous
  scan does not catch them — they assert *something*, just not the thing their
  name claims. They need individual attention rather than a scan.


### The retired multi-agent workflow is still described in four places (2026-08-20)

`CLAUDE.md` and `AGENTS.md` were corrected. These still describe branches that
do not exist, and were left alone because rewriting them was out of scope:

- `docs/MULTI_AGENT_WORKFLOW.md`
- `.agents/prompts/code-agent.md`, `docs-agent.md`, `github-agent.md`
- `tools/agents/setup_worktrees.sh` — creates `codex/agent-{code,docs,github}`

`tools/agents/check_docs_sync.py` is live and correct; it is not part of this.


### Batch 3 final gate: test-quality findings (2026-08-20)

The fifth review round found **no defect reaching a user** — control flow was
proven unchanged across all seven `_authenticate` paths and every release guard
was mutation-proved still firing. These are the test-quality findings from the
same pass, recorded rather than fixed in-loop. They are squarely in scope for
the test-suite remediation batch (`prompt-test-suite-remediation.md`, task 4).

Each was demonstrated by a mutation, not argued for:

- **`test_bi3_a_failed_status_print_does_not_discard_a_valid_token` passes with
  its own defect reintroduced.** Move the status line back inside the `try`
  *and* drop `OSError` from `_say`, and it still passes: the except-handler's
  own `_say` raises the fixture's `OSError` first, so the run never reaches
  `FileNotFoundError`. It asserts two negatives and never asserts the token
  survived. **The tenth test in this batch that could not fail.**
- **`_say`'s `OSError` arm is untested** — the arm the helper exists for
  (closed pipe, `--noconsole`). Removing it passes 19/19.
- **Adding `-e`/`--editable` to `PIP_OPTIONS_TAKING_A_VALUE` opened a hole**:
  `pip install -e requests` is now invisible to the "every dependency comes
  from a requirements file" guard. Pip-semantically correct, but a widening of
  the guard.
- **Three improvements are unlocked**: the `- run: <cmd>` branch in
  `_run_step_lines`, the pip global-options regex, and `_code_only()` on the
  `-r requirements` findall each work but have no test, so reverting any of
  them stays green.
- **`test_the_opt_out_values_are_not_duplicated_across_modules` scans only its
  own file**, despite the name. A duplicate in another test module is not
  caught.
- **Two `.gmd-optout-probe` changes contradict each other**: the `finally`
  block's comment justifies loud cleanup because a leftover breaks
  `test_rm3d_all_test_files_are_collected`, but the same commit excluded the
  directory from that test. The premise is now false and the exclusion is inert.
- **The `else:` relocations in `_authenticate` are untested** — moving the
  status prints back inside the `try` passes, because the load-bearing fix is
  `_say` swallowing. Correct defence-in-depth, unlocked.

### Pre-existing, found by the same pass

- **`_authenticate()` accepts an expired token with no refresh_token.**
  `if not creds:` is false for a truthy `Credentials` object, so re-auth is
  skipped, `_save_token` re-saves the dead token, and the user is told
  "Google Calendar service initialized successfully" before every API call
  fails. Verified identical before and after this batch — not a regression, but
  a real defect.


### Google auth: adjacent items from the Batch 3 reviews (2026-08-20)

Found by the three reviews of Batch 3, recorded rather than fixed because each
is outside BI3 and none is a regression from it.

- **`gmail_importer._load_creds` creates `~/.getmoredone` unconditionally**
  (`src/getmoredone/gmail_importer.py:81`) before it checks anything, and
  hardcodes `legacy_dot_dir()` rather than sharing `paths.google_auth_dir()`.
  Harmless now that the auth directory is one fixed location, but it is the
  side effect that made the removed fallback dangerous. Route it through the
  resolver when that file is next touched.
- **Five diagnostic scripts still hardcode `~/.getmoredone`**:
  `tools/diagnostics/verify_auth.sh:69`, `fix_client_id_mismatch.sh:23`,
  `fix_zombie_token.sh:16`, `debug_auth_loading.py:29`,
  `diagnose_client_id.py:135,157`. Correct today; they would all be wrong
  together if the location ever moves. `tools/diagnose_google_auth.py` — the one
  README and INSTALL point users at — was fixed.
- **`gmail_importer` writes `gmail_token.json` with no `chmod 600`**
  (`:99`), next to a `token.pickle` that is `0600`. Verified world-readable on
  this machine. Pre-existing, and a real credential-exposure item.
- **`test_bi3_saving_a_token_sets_owner_only_permissions` is skipped on
  Windows.** `os.chmod` there only toggles the read-only bit, so the token this
  repo's Windows binary writes has no equivalent protection and nothing checks
  it.
- **`python-dotenv` is declared in `requirements.txt` and imported nowhere** in
  `src/`. Either a real unused dependency or an undeclared runtime need.
- **The docs-sync gate's `CODE_PREFIXES` is still incomplete.**
  `tools/agents/check_docs_sync.py:12` covers `src/`, `tools/`, `tests/` plus
  the two dependency files. A PR touching only `conftest.py`, `pytest.ini`,
  `.github/` or `start.sh` reports "no code/dependency changes detected" — the
  same P3 shape as the `requirements-dev.txt` miss that was just fixed. Not
  changed here because widening a merge gate is a process decision, not a
  defect fix: adding `.github/` would make every workflow tweak require a docs
  update.
- **`test_bi2_no_test_tooling_is_declared_as_a_runtime_dependency` is a prefix
  list, so it is not exhaustive.** `freezegun`, `responses` or `factory-boy` in
  `requirements.txt` would still reach the notices check rather than failing
  there. It narrows the hole rather than closing it.
- **A failed token save is only a `print()`.** In a double-clicked GUI build
  stdout goes nowhere, so "signed in but the token was not saved" is invisible
  and the user simply gets asked to sign in again every launch. Surfacing it in
  the calendar dialog needs a UI decision.


### Release workflow: concurrent release creation — FIXED 2026-08-20 (BI1)

`build-windows` and `build-macos` both called `softprops/action-gh-release` with
the same `tag_name`, so a tagged run was a check-then-create race between two
jobs, and a red job does not un-publish a Release: if one job won the create and
the other errored, the result was a public, permanent Release carrying one
platform's assets only — the same outcome `fail_on_unmatched_files` was added to
prevent.

Fixed as the entry proposed: a single `publish` job with
`needs: [build-windows, build-macos]` downloads both artifacts and makes one
release call, so a half-succeeded run publishes nothing at all. The release notes
are generated once instead of once per platform.

**Still untested against a real tagged run.** CI is the one thing that cannot be
verified by running it here; the guarantee rests on
`tests/test_ci_contract.py::test_bi1_*` reading the YAML. The first `v*` tag after
this change is the real test — watch it, and if the `publish` job fails, no
Release is created, which is the intended behaviour rather than a regression.

### Item editor Project link: deferred decisions — all resolved in Batch 2 (2026-08-19)

Surfaced while adding "Set Project" to the item editor, deferred as decisions
rather than oversights. Batch 2 of
[`docs/implementation_plan_2026-08-19_backlog_clearance.md`](docs/implementation_plan_2026-08-19_backlog_clearance.md)
took each decision and closed it. Kept here as the record of what was decided.

- ~~**Two surfaces disagree about how many projects an item may have.**~~
  **Decided: an Action Item belongs to exactly one Project (BP1).** The
  Projects screen's "link existing items" dialog is exclusive too now. Because
  that dialog can therefore delete links, all three surfaces — the editor, the
  Scheduler's drag-drop and this dialog — ask the same question through
  `screens/project_link_notice.confirm_exclusive_relink` before anything is
  unfiled, and the same question covers the Annual Plan Element that clearing
  a project also destroys.
- ~~**`weekly_items.py` still composes prefixed titles.**~~ **Stopped (BP6).**
  A related Action Item is titled what the user typed. Confirmed first that
  `lineage_for_item` resolves an item's lineage from its Annual Plan Element
  and then its parent, and that these rows carry both, so the title prefix was
  a third choice that was never reached.
- ~~**`get_unlinked_action_items` has no `LIMIT`.**~~ **Capped at 500 (BP5),**
  with `count_unlinked_action_items` for the callers that wanted a number, and
  the Scheduler saying "showing N of M" when the cap bites. A lineage-filtered
  view fetches up to `UNLINKED_FILTERED_LIMIT` (5000) instead, because those
  filters cannot go into SQL and truncating before them would drop rows the
  filter would have kept.
- ~~**`complete_and_create` has no caller in `src/`.**~~ **Retired (BP4),**
  along with `RescheduleDialog` and `screens/reschedule_dialog.py`.
- ~~**`save_item` and `save_item_if_needed` assemble a new item's fields
  twice.**~~ **Factored into `screens/item_editor_form.py` (BP3).** Both paths
  share one field assembly, one validation and one insert sequence, and a test
  compares the rows they produce field by field.

### Open — found while clearing Batch 2 (2026-08-19)

- **`duplicate_action_item` has no caller in `src/`.** BP4 deleted
  `complete_and_create`, which was its only one; `create_followup_item` builds
  its copy independently. It is a public DB API with three tests of its own, so
  removing it was outside the decision taken. Either wire it or retire it, the
  same call BP4 made.
- ~~**`ProjectBoardsScreen.create_action_item_from_board` still uses the
  additive `link_action_item_to_project_board`.**~~ **Fixed** — it is exclusive
  now. Verified the switch is a genuine no-op there: `_apply_defaults` never
  touches `annual_plan_element_id`, so the item's plan element is the board's
  either way.
- ~~**Deleting an Annual Plan Element leaves any Weekly Tactic on it
  unsaveable.**~~ **Decided and fixed (2026-08-19):** an Annual Plan Element is
  deleted only when it has no child records. `delete_annual_records_for_vision_element`
  raises `ActionItemsAttachedError` naming the items, and destroys nothing on
  the way to the refusal.
- **A project's Annual Plan Element is synced onto its items only at link
  time.** `update_project_board` changes a board's plan element and touches
  none of its items; `delete_project_board` removes the board and leaves every
  ex-member carrying the dead board's. So editing a project's plan element
  reproduces exactly the stale state that filing was fixed to prevent. Not
  fixed here — it is a resync question about a different writer, with its own
  blast radius.
- **The raw APE `UPDATE` in `link_item_to_project_exclusive` bypasses
  `_stamp_segment_from_relationships`**, so `segment_description_id` stays
  derived from the previous plan element until the next `update_action_item`.
  Reasoned from the code, not reproduced.
- **`ProjectBoardsAttachedError`'s message lists every attached board with no
  cap**, while its sibling `ActionItemsAttachedError` caps at ten. Bounded in
  practice by boards-per-APE, so left alone — noted because the cap was added
  to one of two sibling handlers.
- **`test_app_icon._tk_available` leaks a Tk root** if `Tk()` succeeds but
  `withdraw()` raises. Not reachable in practice.
- **`LinkProjectActionItemsDialog` renders up to 200 rows eagerly** on open,
  each with four widgets, and does it again on every keystroke in Search. On a
  real database this takes long enough to notice.
- ~~**The Projects screen's "Unlink" button and every other unfiling path
  disagree.**~~ **Decided and fixed (2026-08-19):** removing an item from a
  project removes only the link; its Annual Plan Element stays, because the
  user may be on the way to a different project. Unlink was right all along —
  `clear_item_project_links` was the one overreaching.
- **`build_item_from_form` canonicalises a Weekly Tactic title from the item's
  *stored* start date**, before the form's start date is written onto it. That
  is the order `save_item` used before BP3 and was preserved deliberately; it
  looks wrong and should be checked against what WT-M6 intends.
- **Four Who-filter predicates on one screen, two of them different.** The
  Scheduler's project and unlinked branches now share one rule
  (`DragScheduleScreen._matches_who` / `_who_values_matching`): a blank filter
  matches nothing. Its date-filter and default branches go through
  `get_all_items` / `get_upcoming_items`, whose
  gate on `if who_filter:`, so the two blank forms behave differently *there*
  as well. Measured, because a first draft of this entry got it wrong:

  | filter | project / unlinked branches | `get_all_items` / `get_upcoming_items` |
  |---|---|---|
  | `"   "` | matches nothing | matches owner-*less* rows |
  | `""` | matches nothing | filter dropped — returns **everything** |

  So one blank selection produces three different answers on one screen. Not
  fixed here because those two methods are shared with other screens; changing
  them is its own change with its own blast radius. Reachable because
  `get_distinct_who_values` returns blank owners verbatim into the dropdown.
- **`get_distinct_who_values` has no `WHERE who IS NOT NULL`**, unlike its
  `group` and `category` siblings, and `who` is nullable — so a `None` can
  reach `CTkComboBox(values=...)`. Pre-existing; same family as the entry
  above.

### delete_segment coverage — resolved, and the entry was wrong (2026-08-19)

This was recorded as "cannot be exercised: every VSP table has a NOT NULL
foreign key to its parent, so an orphan cannot be inserted". That reasoning
confused *orphan* with *linked*. `delete_segment` counts
`WHERE segment_description_id = ?`, and an ordinary chain built through the
manager's own API sets that column on all seven tables — no orphan required.

Now covered by `tests/test_vps_segments.py::test_bc3_delete_segment_counts_every_vsp_table`
(all seven at once) and a parametrised companion that hangs the parents off a
second segment so each non-vision table blocks deletion on its own. Kept here as
a record of the wrong call, not as outstanding work.

### An unreadable week start disables WT-INV5 database-wide, with only a log line (2026-08-19)

If two week items on one Annual Plan Element share a `start_date` that is not a
date, they are duplicates as far as the unique index is concerned but belong to
no week. The dedupe reports them under `unmergeable` and deliberately does not
merge them — merging would be irreversible and `''` means "no start date", not
"the same week". The consequence is that `create_weekly_tactic_unique_index`
raises, is caught, and the index is **never created**, so WT-INV5 is unenforced
for *every* APE and week in the database from then on, not just for the bad rows.

`unique_index_enforced` has no consumer outside the migration and its tests, and
`unmergeable_groups` reaches only `weekly_tactic_debug.log`. There is no in-app
way to find the offending ids or clear the state.

Mitigating: `normalize_week_item_starts` falls back to `due_date`, so the
empty-start case is rescued whenever the due date parses; the genuinely stuck
case is a non-empty unparseable string. Not reachable on the live database today
(25 week rows, all Monday-aligned).

Wanted: a startup banner or a Settings diagnostic naming the rows, rather than a
log line nobody reads. Needs a UI decision, which is why it is here.

### Other known items

- [x] **Done 2026-08-19 (BC3).** It was 16 tests across four files, not two, and
  one of them (`test_enhanced_deletion_protection`) was *returning False* — a
  failing test reporting green since `delete_segment`'s return shape changed.
  Another opened the user's real database. All four files now assert;
  `PytestReturnNotNoneWarning` count is 0. See `LEARNINGS.md`.
- [x] **Done 2026-08-20 (BI2).** `requirements-dev.txt` split out; `TEST_ONLY_PACKAGES`
  deleted and `start.sh`'s `grep -v '^pytest'` with it — there were **two** hardcoded
  copies of the answer, not one. The split is asserted as set disjointness rather than
  by naming pytest, so a third test-only package cannot land in the wrong file.
- [x] **Done 2026-08-20 (BI3).** `GoogleCalendarManager.__init__` reads its arguments
  first and creates nothing. The default location moved into
  `paths.google_auth_dir()`, shared by the constructor and the two static checks that
  each hardcoded it — fixing only the constructor would have left `has_credentials()`
  looking in a different directory. `~/.getmoredone` still wins when it exists.
- The `LICENSE` is an unreviewed draft. It carries a warning header protected by
  `test_rm2a_license_carries_the_unreviewed_draft_warning`; have a lawyer review it
  before the first paid sale, then delete the header and that test together.


## ✅ Recently Completed (2026-01-24)

### VPS Segment Management

- [x] Added VPS Life Segments tab to Settings
- [x] Create new segments with color picker
- [x] Edit existing segments (name, description, color, order, active status)
- [x] Delete segments with enhanced protection:
  - Reports exact count of linked visions
  - Shows detailed error message with removal instructions
  - Prevents accidental deletion of segments with data
- [x] Visual color preview in segment list
- [x] Active/Inactive status toggle
- [x] Comprehensive test coverage (9 new tests)

### VPS Bug Fixes

- [x] Fixed New Vision button crash (CTkMessageBox error)
- [x] Fixed empty year field validation with sensible defaults
- [x] Added multi-select checkbox dialog for life segments
- [x] Segment filter now shows count of selected segments

## ✅ Recently Completed (2026-01-23)

### Item Editor Enhancements

- [x] Save button keeps window open after saving
- [x] New "Save & Close" button added
- [x] Duplicate button saves changes before duplicating and opens in new window
- [x] "Create Tasks" feature - creates child items from Next Action field (one per line)

### Timer Improvements

- [x] Independent music controls (separate Play/Pause buttons)
- [x] Music continues when timer is paused
- [x] Visual distinction with purple buttons for music controls

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
