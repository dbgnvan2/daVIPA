# Handoff Note

- Date: 2026-11-12
- Topic: priority-cell-colour (PCC-M1 - PCC-M5, PCC-D1 - PCC-D4)

## Summary

The priority colour scheme no longer tints a list row. The three priority
*levels* now colour the Priority cell's background on the five list screens
(Today, Upcoming, All Items, Hierarchical, Completed), and the bright red a
critical item used to take -- `palette["danger"]` applied to the whole row --
is gone. `priority_levels.fill_for_level` / `level_cell_fill` are the new
authorities; `row_fill`'s level branch was removed, leaving segment and
completed as the only row-fill sources.

Six commits: `1a7b047` (plan), `f1d1387` (src), `eb0c035` (tests), `6644d96`
(docs), then the sweep fixes `8234a40` (prose), `a28ce75` (tests), `f3453de`
(records).

## Files changed

- `src/getmoredone/priority_levels.py`, `theme.py`, `app_settings.py`
- `src/getmoredone/screens/{today,upcoming,all_items,hierarchical,completed}.py`
- `tests/test_priority_level_colors.py`, `tests/render_priority_cells.py` (new)
- `AGENTS.md`, `BACKLOG.md`, `docs/USER_GUIDE.md`, `docs/spec_coverage.md`,
  `docs/DOCUMENTATION_INDEX.md`, `docs/ui_color_inventory.md`

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_priority_level_colors.py tests/test_traceability_refs.py tests/test_color_inventory_sync.py -q`
- Result: PASS (77 in the colour file)
- Command: `./venv/bin/python tools/agents/check_docs_sync.py`
- Result: PASS
- Command: the full suite
- Result: NOT RUN -- local full runs are refused by standing instruction; CI runs it.
- Six mutation proofs taken against the verbatim original, one of which
  (`test_pccm3_the_render_helper_stays_out_of_the_real_data_dir`) had to be
  re-proved: its first version passed with the fix removed. An append-mode
  open that writes nothing leaves mtime unchanged, so watching the real data
  directory's mtimes proved nothing. It now asserts on the path the helper
  reports from `app_data_dir_path()`.
- Three cold passes (failure-pattern, correctness, security) over the original
  range, plus one cold pass over the fix commits. Two warm passes. No pass
  executed the application: a window on screen is refused by standing
  instruction, so the substitute is the manual checklist in the plan's
  section 8, which is **still outstanding** -- nobody has looked at the five
  screens in the running app.

## Risks / Known gaps

- **The effort budget was exceeded on tests and is reported, not hidden.**
  Measured over this batch with `tokenize` for comments and `ast` for
  docstring nodes, intersected with the added line numbers: test code 343
  lines against src code 46 lines = **7.46x**, where
  `~/.claude/standards/effort-budget.md` sets 2x. The cause is that the src
  change is tiny (one function split into two, five near-identical call sites)
  while the claim needing proof is "a colour reaches a real CustomTkinter
  widget on five screens", which needs a subprocess render harness. Prose came
  in under its ceiling at 0.57 for the test file and 0.41 for the helper,
  against the repo's own standing norms at HEAD (test files 0.43-0.65,
  `priority_levels.py` 1.43). The guards all work and all fail under mutation;
  they were reported rather than deleted.
- **PCC-A3, filed.** A completed row's Priority cell measures 1.02:1 against
  the row in light mode -- the indicator renders and cannot be seen. The user
  was shown the numbers and chose to ship the colours as approved. The trade
  is not one-way: in dark mode these colours beat the red they replaced,
  13.4:1 against 2.27:1, so the regression is light mode only. Cheapest fix
  when touched is `border_width=1, border_color=cell.text_color`, about 19:1
  with no colour change.
- **PCC-A1, filed.** The parent/child pickers
  (`screens/item_editor_dialogs.py:257`, `:476`) still draw an uncoloured
  score. Left alone deliberately -- the user named the list screens, and a
  dialog that was never coloured is not the red PCC replaced.
- The composition PCC-A3 describes has no assertion:
  `tests/render_priority_cells.py` renders open items for the three screens
  that tint completed rows, and `CompletedScreen` passes
  `use_completed_tint=False`, so no rendered row in the suite carries a fill
  under a cell.
- **Two user decisions this batch rests on**, recorded because neither is
  derivable from the code: green for Any Critical rather than the
  conventional red (asked for directly, confirmed before the build), and
  filing PCC-A3 rather than fixing it or altering the level colours.

## Next agent actions

- Walk the plan's section 8 checklist in the running app. Nothing in the
  suite covers a cell sitting on a filled row, and item 4 was added for it.
- `src/getmoredone/screens/plan.py` and `tests/test_plan_screen.py` were
  modified in this checkout by a concurrent session's lunch-move batch while
  this one ran. They were deliberately left unstaged and uncommitted here;
  `docs/USER_GUIDE.md` carries one of their hunks too. Do not assume the
  working tree is this batch's.
