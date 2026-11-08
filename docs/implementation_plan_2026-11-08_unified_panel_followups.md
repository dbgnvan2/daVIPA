# Spec + implementation plan — what the on-screen check found

Status: **approved 2026-11-08. UPD-F1 built the same day (§2 carries its
per-criterion statuses); UPD-F2, UPD-F3 and UPD-F4 are built elsewhere.**
IDs: `UPD-F1` … `UPD-F4`. Use them verbatim in commits, docstrings and test
names. They continue `docs/spec_2026-11-07_unified_panel_design.md`, whose
UPD-M7.2 and UPD-M7.3 are the criteria this work closes.

---

## 1. Where this came from

The ten-step checklist in §11 of the unified panel spec was walked in the
running app on 2026-11-08. Verdicts, as reported:

| Step | Criterion | Verdict |
|---|---|---|
| 1 | six nav buttons | yes |
| 2 | the same header card, panels and divider on the five tabs | yes |
| 3 | row heights and chip style match | **mostly** — the filter area differs; see UPD-F2 |
| 4 | Week Assignment's Actions column and blank checkbox header | **change** — the header should read "Pick"; see UPD-F3 |
| 5 | Week Actions is a table, click anywhere selects | yes |
| 6 | the filters narrow, count and fall back | yes — and UPD-F2 makes them easier to find |
| 7 | the divider drags, neither panel is crushed | yes — and **columns should rescale with it**; see UPD-F4 |
| 8 | a column drag in the left panel moves only that column | yes |
| 9 | the same in the right panel, panels independent | yes |
| 10 | every width and divider position survives a relaunch | **no — nothing survives**; see UPD-F1 |

So **UPD-M7.2 is `partial`** (the design reads as one everywhere except the
filter area) and **UPD-M7.3 is `not done`** (steps 8 and 9 pass, step 10
fails). Both are recorded that way in the unified panel spec's §10.

---

## 2. UPD-F1 — a width or divider position does not survive a relaunch

### What is actually happening

Not a failure to write. The live settings file for the data directory in use
(`~/Library/Application Support/GetMoreDone-Demo/settings.json`, written
15:24 on 2026-11-08) holds dragged values:

```
ape_month_left_col_widths       = {checkbox:34, index:34, segment:60, subsegment:60, category:60}
week_assignment_left_col_widths = {checkbox:34, index:34, segment:135, subsegment:142, category:125}
ape_quarter_split_ratio         = 0.4430379746835443
```

and, in the same file, **empty dictionaries for three of the five tabs that
were dragged**:

```
ape_quarter_left_col_widths   = {}
annual_vision_left_col_widths = {}
annual_vision_right_col_widths= {}
week_actions_left_col_widths  = {}
today_col_widths              = {}
```

### The cause this plan will fix

`AppSettings.save()` writes `asdict(self)` — **the whole object, every
field.** Any screen holding its own snapshot therefore reverts every field
another object has changed since that snapshot was loaded. `save`'s own
docstring states the premise ("Over a dozen screens each call
`AppSettings.load()` and hold their own object") without drawing the
consequence for a field two screens can both write.

The five VSP tabs share `app.settings`
(`screens/ape_assignment.py:56` and its four siblings:
`getattr(app, "settings", None) or AppSettings.load()`). **`TodayScreen` does
not** — `screens/today.py:67` is an unconditional `AppSettings.load()`, and
`:266` reloads it again mid-session. APE Week Actions' right panel *is* a
`TodayScreen` subclass (`WeekTacticActionsPanel`, `screens/week_actions.py:49`,
decision D3), so dragging a column in that panel saves Today's stale snapshot
over everything the VSP tabs had written in the same session.

This is a hypothesis with strong evidence, not a confirmed fault: the test
named in UPD-F1.1 is what confirms it, and it is written **first** and watched
fail before any fix (P10).

### Acceptance criteria

| ID | Criterion | Test | Status |
|---|---|---|---|
| UPD-F1.1 | Two `AppSettings` objects loaded from one file, each writing a *different* field, both survive: the second `save()` does not revert the first's field | `tests/test_settings_merge_on_save.py::test_updf11_a_second_settings_object_does_not_revert_the_first` | `done` |
| UPD-F1.2 | A width written by a VSP tab's resizer survives a `TodayScreen`-held object's `save()` in the same session | `tests/test_settings_merge_on_save.py::test_updf12_a_today_save_does_not_wipe_a_vsp_width` | `done` |
| UPD-F1.3 | Every column width and split ratio written on all five tabs is readable from the file afterwards — all five prefixes populated, none empty | `tests/test_settings_merge_on_save.py::test_updf13_all_five_tabs_persist_their_own_widths` | `done` |
| UPD-F1.4 | A resizer built from a settings object that holds stored widths reports those widths, not the spec defaults | `tests/test_settings_merge_on_save.py::test_updf14_stored_widths_are_what_the_resizer_reports` | `done` |
| UPD-F1.5 | **P2** — a stored width outside its column's bounds is clamped *and* the clamp is surfaced, not silently swallowed | `test_updf15_a_stored_width_outside_its_bounds_is_surfaced` | **`not done`** — blocked, see below |
| UPD-F1.6 | **P8, dirty state** — a settings file containing another session's widths is merged with, not overwritten by, this object's defaults | `tests/test_settings_merge_on_save.py::test_updf16_a_file_with_foreign_widths_is_merged_not_replaced` | `done` |

**Built 2026-11-08** on `claude/elegant-neumann-ab55c9`, in a worktree of its
own (§9's risk, taken as written). The hypothesis above was confirmed, not
assumed: UPD-F1.1's test was written first and watched fail against the
unmodified `save()`, on exactly the predicted assertion.

**UPD-F1.5 is `not done`, and the reason is scope, not difficulty.** The clamp
it asks to surface is in `ColumnResizer._load_widths`
(`screens/column_resize.py`), which UPD-F4 is being built in and which the
UPD-F1 batch was told not to touch. The change is about ten additive lines —
record `stored` against `clamped` per column and log a warning naming the
column, the stored width and the bound, the same shape as
`SplitPanel._load_ratio`'s existing P2 warning. It belongs in the UPD-F4 batch
or in one of its own. Nothing was half-built and no test pretends to cover it.

### Approach

Make `save()` a read-modify-write against the file rather than a blind dump:
re-read the file at save time (`save` already reads it, for
`_will_not_parse`), and write `asdict(self)` merged over what is on disk, so a
field this object never touched keeps the value the file has. This is the
narrow fix and it repairs **every** screen holding its own snapshot at once
rather than only `TodayScreen` (P5 — fix the siblings in the same change).

The alternative — give `TodayScreen` the app's object — fixes one screen and
leaves a dozen. It is recorded here as rejected, not overlooked.

Open question for approval: a merge means a field a user *clears* in one
screen can be re-set by another screen's stale snapshot. Fields written by
exactly one screen are unaffected. If that trade is not acceptable, the
fallback is a per-field dirty set on `AppSettings`, which is a larger change.

### What was actually built, and why it is the fallback

The approach above was built as written, measured, and withdrawn. Recorded
here rather than quietly changed.

`asdict(self)` merged over the file is a **no-op**: `asdict` carries every
field, so `{**on_disk, **asdict(self)}` is `asdict(self)`, and the file's value
loses every time. The only reading of "a field this object never touched" that
is available without tracking assignments is "a field still at its dataclass
default" — and that is also the reading the trade-off above describes, since
"clears" means "sets back to the default".

Built that way, it broke
`tests/test_list_view_setting.py::test_default_setting`.
`default_columns_expanded` defaults to `False`, so a screen setting it back to
`False` read as *untouched* and the `True` already on disk was kept. **One
object, one save, no second screen and no stale snapshot: a setting turned off
could not be saved at all.** That is not the trade this section asked approval
for — it is strictly worse, and it would have shipped as "the toggle comes back
on by itself".

So the fallback this section names was built instead: a per-field record of
what was assigned, via `__post_init__` and `__setattr__` on `AppSettings`.
`load` forgets its own normalizers' assignments, and `save` snapshots the
record before its own normalizers run, so a stale object claims nothing it was
not asked to change. It is about the same size as the comparison it replaces,
and correct in both directions — a field assigned to its own default still
wins, a field never assigned never overwrites.

The trade that remains is smaller than the one described: a value a stale
object *assigns* can still revert a newer one. That is unchanged from before
this fix, so nothing regressed.

`plan_day_shape_unconfirmed` is exempt (`AppSettings.MERGE_EXEMPT_FIELDS`) and
written from this object every time. Merging it would mean a file still saying
"unconfirmed" putting that back over the confirmation Day Settings had just
made, leaving the one dialog that can clear it unable to.

---

## 3. UPD-F2 — the filter area is three lines deep on every tab that has one

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| UPD-F2.1 | On every tab with the three filters, the Segment / SubSegment / Category combos sit on their own grid row, below the row holding that tab's other controls | `test_updf21_the_filters_are_on_their_own_row` |
| UPD-F2.2 | A blank spacer row sits between them, so the header card is three rows deep | `test_updf22_a_spacer_row_sits_above_the_filters` |
| UPD-F2.3 | The depth is the same on all of them — one assertion over the set of tabs, not one per tab | `test_updf23_every_filtered_tab_is_three_rows_deep` |
| UPD-F2.4 | Annual Plan Elements, which had its filters inline, is one of them | `test_updf24_annual_plan_elements_is_three_rows_deep_too` |
| UPD-F2.5 | Nothing else in the header card moved — the existing control set and its order are unchanged | `test_updf25_the_header_controls_are_the_same_set_in_the_same_order` |

"Three lines deep" is asserted as the filter widgets' grid row index and the
presence of a spacer row of a fixed height, which a withdrawn root can read.
Whether it *looks* three lines deep is UPD-F2.6 below.

---

## 4. UPD-F3 — the checkbox column on Week Assignment's left panel says "Pick"

Confirmed as APE Week Assignment's **left** panel (Month-assigned Annual Plan
Elements), which already has the checkbox. APE Week Actions' Weekly Tactics
table is **not** in scope and gains no checkbox.

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| UPD-F3.1 | `APE_LEFT_COLUMNS`' checkbox column has the heading `"Pick"` | `test_updf31_the_checkbox_column_is_headed_pick` |
| UPD-F3.2 | The column is wide enough for the word without clipping it, and is still fixed-width with no drag handle | `test_updf32_the_pick_column_fits_its_heading_and_has_no_handle` |
| UPD-F3.3 | The checkbox itself is unchanged — same cell, same column index, same toggle behaviour | `test_updf33_the_checkbox_still_toggles_in_the_same_column` |
| UPD-F3.4 | APE Quarter and APE Month share `APE_LEFT_COLUMNS`, so they get the same heading; asserted rather than assumed | `test_updf34_all_three_ape_left_panels_say_pick` |

`ChipColumn("checkbox", "", 34, …)` is 34px; "Pick" at `CHAR_PX = 8` needs
about 40 plus padding, so UPD-F3.2 will move the width. That is a visible
change on three tabs and is listed as a deviation, not slipped in.

---

## 5. UPD-F4 — the columns rescale with the divider, down to five characters

### Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| UPD-F4.1 | Moving the divider rescales **every resizable column** in the panel that grew or shrank, in proportion to its stored width | `test_updf41_a_divider_move_rescales_every_resizable_column` |
| UPD-F4.2 | Fixed-width columns (checkbox, `#`, Actions) do not rescale | `test_updf42_a_fixed_column_keeps_its_width_when_the_panel_moves` |
| UPD-F4.3 | No column goes below **five characters' width** (40px at `CHAR_PX = 8`); at the floor the remaining columns absorb the rest | `test_updf43_no_column_goes_below_five_characters` |
| UPD-F4.4 | **P7, adversarial** — a panel narrow enough that five characters each does not fit returns the floor for every column and surfaces the overflow rather than returning a negative or zero width | `test_updf44_a_panel_too_narrow_for_the_floor_surfaces_it` |
| UPD-F4.5 | A column drag still changes only that column at the current panel width, and is what gets stored | `test_updf45_a_drag_still_moves_only_its_own_column` |
| UPD-F4.6 | The stored widths are read back as proportions of the panel, so a relaunch at a different window size keeps the *shape* the user set | `test_updf46_stored_widths_survive_a_different_window_size` |

### Approach

Treat each resizable column's stored width as a **weight**, not a pixel
promise: on a panel `<Configure>`, reserve the fixed columns, then distribute
what is left across the resizable ones in proportion to their stored widths,
with a 40px floor. A drag writes that column's new pixel width, which becomes
its new weight. This is why UPD-F4.6 exists: the behaviour the user asked for
in step 7 and the behaviour they asked for in step 10 are only compatible if
the stored number is a weight.

The chip columns' `min_width` is 60 today (`screens/chip_table.py:99-101`);
the floor moves to 40. That is a deliberate behaviour change on five tabs.

---

## 6. What cannot be made code-testable

| ID | Criterion | Why | Proposal |
|---|---|---|---|
| UPD-F2.6 | The filter area *looks* three lines deep and the card does not overflow at a real window size | a withdrawn root has no real geometry, and row indices are not appearance | human review: one step added to §11 |
| UPD-F4.7 | Dragging the divider *feels* like the columns move with it, with no flicker or lag | subjective, and frame timing is not observable off-screen | human review: one step added to §11 |
| UPD-F3.5 | "Pick" reads as a column heading rather than as a button | subjective | human review, folded into the step above |

These three get a **new §11 step each** in the unified panel spec, walked the
same way, and are recorded `not done` until walked. They are not asserted by a
test and no test will claim them.

---

## 7. Order and dependencies

1. **UPD-F1** first, and alone. It is the only defect; the other three are
   requests. Its test is written and watched fail before the fix (P10).
2. **UPD-F3** second — the smallest change, and it touches a constant the
   other two will be reading.
3. **UPD-F2** third. Independent of F1 and F3.
4. **UPD-F4** last. It depends on UPD-F1 being fixed, because its own
   acceptance criterion UPD-F4.6 is about what survives a relaunch, and that
   cannot be verified while nothing survives one.

Each lands as its own commit pair (src, then tests), and the batch ends with
`/csdp` — which is already owed over 42 unpushed commits before any of this.

---

## 8. Adjacent issues found, not fixed

Per the global rule on surrounding code:

- **`screens/today.py:266` reloads `AppSettings` mid-session**
  ("Reload settings for icon changes"), which is a second, independent way for
  a stale snapshot to appear. UPD-F1's merge makes it harmless; the reload
  itself is left alone.
- **Over a dozen screens hold their own `AppSettings.load()`.** UPD-F1 fixes
  the consequence for all of them at the `save()` seam rather than editing
  each. No screen is changed, so none is left inconsistent.
- **`CLAUDE.md:53` names the entry point `getmoredone.app.daVIPAApp`**; the
  class is `GetMoreDoneApp` (`src/getmoredone/app.py:22`). Not this plan's
  file. Already flagged in UPD-M6's and UPD-M7's handoff notes.
- **UPD-A9** (five remaining copies of the filter triple and the category
  colour key) is still open in `BACKLOG.md` and is not swept here. UPD-F2
  touches the filter *layout* on those same five files, which makes UPD-A9
  cheaper to do first — recorded, not decided.

- **No test enforces `docs/DOCUMENTATION_INDEX.md`'s completeness.** The global
  rule is that where a repo keeps a documentation index, a test asserts every
  document is in it; `grep -rn DOCUMENTATION_INDEX tests/` returns nothing, so
  this repo's index is kept by hand. Not fixed here — it is a meta test of its
  own, and writing it inside a batch whose own entry it would police is the
  wrong order. Filed for `BACKLOG.md` when this plan is approved.

## 9. Risk

**This checkout has another batch building in it.** The calendar-export batch
holds uncommitted hunks in `src/getmoredone/app_settings.py`, which UPD-F1
must change. Per `CLAUDE.md`'s "One build batch at a time", UPD-F1 should not
start until that batch is committed, or it needs its own worktree. The other
three items touch `screens/chip_table.py`, `screens/column_resize.py` and the
five VSP screens, none of which that batch holds.
