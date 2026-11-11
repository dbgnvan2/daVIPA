# Implementation plan — the five list screens' row rendering (LRR)

**Status:** approved 2026-11-10, build started in its own session; no
implementation code written at the time of this commit.
**Written:** 2026-11-10, measured at `0864390`.
**Closes:** `PRI-A1` (medium), `PLC-A1` (medium).
**Scope:** `src/getmoredone/priority_levels.py` and the five list screens.

## 1. Why these two together

Both are the same shape: a rule written out by hand in `today.py`,
`upcoming.py`, `all_items.py`, `hierarchical.py` and `completed.py`, where an
authority for it already exists and the five copies have drifted from it.

* `PRI-A1` — `item.importance == 20 or item.urgency == 20`, five times
  (`today.py:656`, `upcoming.py:421`, `all_items.py:375`,
  `hierarchical.py:312`, `completed.py:271`). `priority_levels.priority_level`
  answers exactly this, from `PriorityFactors`, so renumbering the scale moves
  the answer with it. The literal `20` is P4.
* `PLC-A1` — a row filled with a VSP segment colour keeps the screen's own
  `row_text`, so a pale segment colour in the dark theme draws near-white text
  on it. `row_fill` already returns a derived `text_color` for a priority-level
  fill and all five screens already honour it (`fill.text_color or
  palette["row_text"]`), so the fix is one `return` in one function.

All five screens already import from `..priority_levels`, so neither criterion
adds a dependency. Both are provable as function tests — no mapped window, so
the whole batch runs under the local throttle.

## 2. Acceptance criteria

| ID | Criterion | Test |
|---|---|---|
| LRR-M1.1 | The five screens ask `priority_level_for_item(item) == LEVEL_ANY_CRITICAL` for the `P:` chip; no `== 20` literal survives in `src/getmoredone/screens/` | `tests/test_priority_level_colors.py::test_lrrm11_no_screen_tests_importance_against_a_literal` — AST walk over the five modules, exact count `0`, per the repo's source-assert rule (parse it, assert counts, no `> N` floor) |
| LRR-M1.2 | An importance the old literal missed is critical: `25`, and the string `"20"` | `::test_lrrm12_an_off_scale_critical_is_still_critical` — adversarial (P7); confirm red on `== 20` before the fix |
| LRR-M2.1 | `row_fill` returns a `text_color` for a segment fill, derived from the fill with `pick_text_color` | `::test_lrrm21_a_segment_fill_carries_its_own_text_colour` |
| LRR-M2.2 | A pale segment colour gets dark text and a dark one light text — both directions, so the assertion cannot pass on a constant | `::test_lrrm22_the_segment_text_colour_follows_the_fill` |
| LRR-M2.3 | The completed tint still returns `None` — the theme's `row_text` is designed against it, and widening this to every fill is not what `PLC-A1` names | `::test_lrrm23_the_completed_tint_keeps_the_themes_text_colour` |

Not code-testable: how the change *looks* on the user's own segment colours.
That is `ui-regression.md` territory and goes to the manual checklist in §5.

## 3. Order

1. `LRR-M2` first — one function, one file, and the test for it is the cheapest
   to write. Highest-impact fix first, per the fix→test map rule.
2. `LRR-M1` second — five call sites, mechanical once M2 is green.
3. Documents, in the same change (global rule 13):
   * `RowFill`'s docstring says the segment fill "keeps exactly the text colour
     it has today" and points at `BACKLOG.md`. False after M2 — rewrite it.
   * `row_fill`'s docstring repeats the claim in its closing paragraph.
   * `BACKLOG.md`: delete the `PRI-A1` and `PLC-A1` entries.
   * `docs/USER_GUIDE.md`: check, do not assume. If no section describes row
     colour, say so in the status report rather than editing it.

## 4. Two things the next session will trip over

* **`PRI-A1`'s own text is stale.** It says "`PLC-A3` and `PLC-A6` are the same
  five copies … whoever takes it should close all three." `PLC-A6` was archived
  as residue on 2026-11-09 (`docs/unused-docs/backlog_archive_2026-11-09.md`),
  so only two are live. Close `PRI-A1`, and leave `PLC-A3` filed — see below.
* **`PRI-A1` also cites a guard that no longer exists**
  (`tests/test_doc_status_claims.py::test_sstm9_every_promised_pri_adjacent_item_is_filed`).
  That file was deleted with the prose-asserting guards. Deleting the entry
  therefore breaks nothing; do not go looking for the test to update.

## 5. Manual checklist (the part no test covers)

1. Today, Upcoming, All Items: a row with a pale segment colour reads legibly
   in the dark theme, and still does in the light one.
2. The same row's `P:` chip is unchanged for an ordinary critical item.
3. A row with importance Critical and urgency blank still shows the chip.

## 6. Adjacent issues found, not fixed (global rule 10)

Flagged here, left filed in `BACKLOG.md`:

* `PLC-A3` (low) — the `P:` chip hard-codes `palette["danger"]` for critical
  while the row tint is now user-chosen, so the two disagree by design. This
  batch replaces the chip's *condition*, not its colour: the colour is a
  product decision about what "critical" looks like, and making it here would
  be a silent sweep. One line in the commit message, nothing more.
* `PLC-A2` (low) — Hierarchical and Completed pass `segment_color=None` and
  apply their segment colour as an accent only, where the other three fill the
  row. Nothing records which is right. Untouched by M2, which changes only
  what a segment fill does once there is one.
* `PLC-A4` (low) — `settings.py` is 1214 lines. Not touched by this batch.

## 7. Verification

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest \
  tests/test_priority_level_colors.py tests/test_plan_screen.py -q
```

`tests/test_plan_screen.py` is in the run because it is the other reader of
`row_fill`. Commit tests and `src/` separately, by explicit path. One cold
`learning-qa` pass over the `src/` diff — this is a `src/` and UI change, so
the full sweep budget applies, not the docs-only exemption.
