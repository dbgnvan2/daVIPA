# Handoff Note

- Date: 2026-11-08
- Agent: Code
- Topic: unified-panel-f1 — a column width or divider position survives a relaunch

## Summary

UPD-F1 only, from §2 of
`docs/implementation_plan_2026-11-08_unified_panel_followups.md`. UPD-F2,
UPD-F3 and UPD-F4 are being built elsewhere and nothing here touches
`screens/chip_table.py`, `screens/column_resize.py` or the five VSP screen
modules.

**The fault, confirmed before it was fixed.** `AppSettings.save()` wrote
`json.dump(asdict(self), ...)` — every field. Over a dozen screens each call
`AppSettings.load()` and hold their own object, so whichever one saved last put
its own snapshot of every *other* field back. `screens/today.py` loads its own
object unconditionally and APE Week Actions' right panel is a `TodayScreen`
subclass, so one column drag there reverted the widths five VSP tabs had saved
earlier in the same session — which is why the §11 walk found three of the five
width fields empty and two populated.

UPD-F1.1's test was written first and watched fail against the unmodified
`save()` (P10). It failed on exactly the predicted assertion, so the hypothesis
held.

**The fix.** `save()` is now a read-modify-write: it re-reads the file and
merges this object's changes **over** what is on disk, so a field this object
was never asked to change keeps the file's value. One change at the `save()`
seam repairs every screen holding its own snapshot rather than only
`TodayScreen` (P5). No screen module is edited.

**A departure from the plan's stated mechanism, and why.** §2's approach says
to write `asdict(self)` merged over the file. Taken literally that is a no-op —
`asdict` carries every field, so the file's value loses every time. The only
reading that fixes anything is "a field still at its dataclass default takes
the file's value", and that is also the reading its stated trade-off describes.
It was built that way first, and it broke
`tests/test_list_view_setting.py::test_default_setting`: `default_columns_expanded`
defaults to `False`, so a screen setting it back to `False` read as *untouched*
and the `True` on disk was kept. **One object, no second screen, no stale
snapshot — a setting turned off could never be saved at all.** That is not the
trade §2 asked approval for ("a field a user clears in one screen can be
re-set by another screen's stale snapshot"); it is strictly worse, and it would
have shipped as "the toggle comes back on by itself".

So the merge is driven by a per-field record of what was actually assigned —
the fallback §2 itself names ("a per-field dirty set on `AppSettings`"). It is
a `__setattr__` and a `__post_init__`, about the same size as the comparison it
replaces, and correct in both directions: a field assigned to its own default
still wins, and a field never assigned never overwrites. The accepted trade is
smaller than the one described: a value a stale object *assigns* can still
revert a newer one, which is unchanged from before this fix.

`plan_day_shape_unconfirmed` is exempt (`MERGE_EXEMPT_FIELDS`) and still
written from this object every time. Merging it would mean a file saying
"unconfirmed" putting that back over the confirmation Day Settings had just
made — the one dialog that can clear it, unable to.

**UPD-F1.5 is not built.** Surfacing the clamp in `_load_widths` needs
`screens/column_resize.py`, which this task was told not to touch. See
"Risks / Known gaps".

## Files changed

- `src/getmoredone/app_settings.py` — `__post_init__`, `__setattr__`,
  `_assigned_names`, `_forget_assignments`, `_on_disk`, `_merge_over_file`,
  `MERGE_EXEMPT_FIELDS`; `save()` reads before it opens and writes the merge;
  `load()` forgets the normalizers' own assignments.
- `tests/test_settings_merge_on_save.py` — new, 8 tests.
- `docs/implementation_plan_2026-11-08_unified_panel_followups.md` — §2
  statuses, and the record of the withdrawn default-comparison merge.
- `docs/spec_coverage.md` — the UPD-F1 rows.
- `docs/changes/2026-11-08-unified-panel-f1.md` — this note.

No `src/getmoredone/screens/` file is touched. `column_resize.py`,
`split_panel.py` and `chip_table.py` were mutated during the mutation gate and
each restored byte-identical, sha256-compared.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_settings_merge_on_save.py -q`
- Result: PASS — 8 passed.

- Command: the same over `tests/test_plan_settings.py tests/test_list_view_setting.py tests/test_settings_isolation.py tests/test_settings_save_refusal.py tests/test_settings_week_rule_ui.py tests/test_theme_settings.py tests/test_column_resize.py tests/test_today_title_col_width.py tests/test_unified_panel_design.py tests/test_priority_level_colors.py tests/test_obsidian_dialogs.py tests/test_project_notes.py tests/test_today_screen.py tests/test_ape_week_actions.py tests/test_live_data_guard.py tests/test_week_numbering.py`
- Result: PASS except two pre-existing failures,
  `tests/test_plan_settings.py::test_pdm54_extending_the_day_is_not_confirming_it`
  and `::test_pdm54_an_already_confirmed_day_stays_confirmed`. Both fail
  identically with `src/getmoredone/app_settings.py` reverted to the branch
  tip, so neither is this change's.

- Command: the same over `tests/test_plan_screen.py tests/test_time_block_crud.py tests/test_drag_schedule_support.py tests/test_timer.py tests/test_date_picker.py tests/test_obsidian_integration.py`, run twice — once with this change and once with `app_settings.py` reverted — and the two `FAILED` lists diffed.
- Result: see "Risks / Known gaps". This set is heavily red on the branch tip
  already; the diff is what matters and it is recorded there.

- Mutation gate: 8 mutations, each the verbatim original line, one at a time,
  every file restored and sha256-compared. 8 red, no finding. Table in the
  status report.

- The app was **not** launched and no Tk window was put on screen.

## Risks / Known gaps

- **UPD-F1.5 is `not done`**, blocked by scope rather than by difficulty. The
  clamp it asks to surface is `ColumnResizer._load_widths`
  (`screens/column_resize.py`), which this task was told not to touch because
  UPD-F4 is being built in that file. The change is about ten additive lines:
  record `stored` against `clamped` per column in `_load_widths`, and log a
  warning naming the column, the stored width and the bound — the same shape as
  `SplitPanel._load_ratio`'s existing P2 warning, which is the local
  precedent. It needs to go in with UPD-F4 or in a batch of its own.
- **This branch is `claude/elegant-neumann-ab55c9`, in a worktree.** `main`
  does not have any of it. No pull request, by the repo's own rule.
- **`docs/spec_coverage.md` is a shared append surface.** UPD-F2, F3 and F4
  will append to the same end of the file; expect a conflict there and resolve
  it by keeping all four sections.
- **`BACKLOG.md`, `docs/USER_GUIDE.md` and `docs/DOCUMENTATION_INDEX.md` are
  deliberately untouched**, per `CLAUDE.md`'s instruction to leave the three
  chronic conflict documents until after the merge. UPD-F1 changes no UI text
  and no user-visible behaviour anyone has to be told about — a width now stays
  where it was put — so `docs/USER_GUIDE.md` has nothing to correct; the
  documentation index has no new document to list except this handoff note,
  which follows the dated-notes convention the index already covers.
- **Dict fields are merged by key, not replaced.** A key the file holds and
  this object's snapshot does not survives. The cost is that a width store
  cannot be emptied while another object holds entries for it; nothing in the
  app empties one.
- **A dict field mutated in place is invisible to the merge.** Nothing in the
  app does it (`ColumnResizer._persist` and `SplitPanel._persist` both build a
  new value and `setattr` it), and `__setattr__`'s docstring states it rather
  than guarding it.

## Next agent actions

- Decide UPD-F1.5: fold the clamp surfacing into the UPD-F4 batch, which is
  already in `screens/column_resize.py`, or give it its own batch.
- Merge `claude/elegant-neumann-ab55c9` into `main` when the other three
  items are in, resolving `docs/spec_coverage.md` by keeping every section.
- The two `test_pdm54_*` failures and whatever the `test_time_block_crud.py` /
  `test_plan_screen.py` reds turn out to be are pre-existing on `main` and
  belong to whoever owns the time-grid work, not to this batch.
