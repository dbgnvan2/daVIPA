# PCC — the priority colour scheme moves from the row to the Priority cell

**Status:** awaiting approval. Written 2026-11-11, before any code.
**Base:** `main` at `1faf21a`, clean and in sync.
**Tier (`effort-budget.md` §1):** **Full** — `src/` and a user-visible contract.
Sweep budget applies: at most two warm passes, at least one cold pass.

---

## 1. What the user asked for

> "remove the priority color coding from the Next Actions and apply it ONLY to
> the Priority background color in the display. Currently it gets bright red -
> that's the item to change to the new color scheme."

Answered in conversation on 2026-11-11, before planning, because none of the
three was decidable from the code:

| Question | Answer |
|---|---|
| Which screen is "Next Actions"? There is no sidebar entry by that name. | **All five list screens** — Today, Upcoming, All Items, Hierarchical, Completed. |
| Which levels colour the cell? | **All three, per Settings** — Any Critical, Any High, and "no fill" for the third. |
| The I/U factor chips use the same bright red. Change them too? | **Yes, same scheme.** |

## 2. What the code does today, measured

Five screens render priority identically. The two colour decisions are
separate, and only the first is shared:

1. **The row fill.** `priority_levels.row_fill` (`src/getmoredone/priority_levels.py:298`)
   decides a row's background from, in order: VSP segment colour → completed
   tint → **priority level** → nothing. The level colours are
   `theme.priority_level_fill_colors` (`src/getmoredone/theme.py:380`): Any
   Critical `#DCFCE7`, Any High `#FEF3C7`, No high or critical `""` (no fill).
   `~/Library/Application Support/GetMoreDone/settings.json` holds no
   `priority_level_color_*` key, so the running app is on those defaults.
2. **The Priority cell.** Each screen draws its own, inline, with
   `palette["danger"]` — `#B91C1C` (`src/getmoredone/theme.py:131`) — as the
   background when the level is Any Critical:

   | Screen | Line | Text |
   |---|---|---|
   | `screens/today.py` | 667 | `P:{score}` |
   | `screens/upcoming.py` | 432 | `P:{score}` |
   | `screens/all_items.py` | 386 | `{score}`, under a `"Priority"` header |
   | `screens/hierarchical.py` | 321 | `P:{score}` |
   | `screens/completed.py` | 281 | `P:{score}` |

3. **The I/U factor chips** (the expandable column group, not the Priority
   cell) take the same `palette["danger"]` via `is_critical_factor`, in four
   screens — `today.py:709`, `upcoming.py:475`, `all_items.py:428`,
   `completed.py:312`. Hierarchical builds no chips.

So the bright red is #2, and "the new colour scheme" is #1's three level
colours — the scheme built on 2026-11-08 and settable in Settings → Priority
Colours. Nothing else was agreed anywhere: `BACKLOG.md`'s `PRI` section is
about the score column's width and the `P:` prefix, not colour.

A sixth surface inherits the change for free: the Action Items panel of APE
Week Assignment **is** a `TodayScreen` (`screens/chip_table.py:405`, guarded by
`test_plc_cold_the_week_panel_inherits_todays_rows_and_reload`).

## 3. The UI contract (`ui-regression.md` §2)

Nothing is removed, renamed, relocated or disabled. Every control in the five
rows keeps its place, its text, its width and its click binding — the Priority
cell keeps `width=60` (`width=80` in All Items), its `<Button-1>` binding to
`edit_priority_inline`, and its `corner_radius=6`-when-filled shape. What
changes is which colour two of them are drawn in. **One user-visible change to
call out:** rows that are green or amber today will be the theme's own
background, and the Priority cell will carry that green or amber instead.

## 4. Acceptance criteria

Each is a test. Spec IDs are used verbatim in test names and docstrings.

### Code

**PCC-M1 — a priority level no longer fills a row.**
Delete the level branch from `row_fill`. Precedence becomes segment →
completed → nothing. `SOURCE_LEVEL` stays in the module; §PCC-M2 uses it.

- `test_pccm1_a_level_no_longer_fills_a_row` — an Any Critical item and an Any
  High item, no segment and not completed, each yield `fill is None`,
  `text_color is None`, `source == SOURCE_NONE`.
- `test_pccm1_segment_and_completed_still_fill_a_row` — **replaces**
  `test_plcm42_segment_and_completed_still_win`, whose claim ("precedence is
  segment, then completed, then level") is the behaviour being changed. A
  segment colour still outranks the completed tint.

**PCC-M2 — one authority says what colour a level draws, and derives its text.**
New in `priority_levels.py`, with the `Purpose:` / `Spec:` / `Tests:`
docstring the repo requires:

```
fill_for_level(settings, level) -> RowFill     # the colour and its derived text
level_cell_fill(settings, item) -> RowFill     # fill_for_level(settings, priority_level_for_item(item))
```

`RowFill` is reused rather than a second dataclass added: it is exactly
`(fill, text_color, source)` and nothing in it is row-shaped. `NO_FILL` and an
unusable stored value both yield `RowFill(None, None, SOURCE_NONE)`, so a cell
with no colour is a cell that looks as it did before anyone set one.

- `test_pccm2_the_priority_cell_takes_its_level_colour` — each level returns
  its settings colour, and follows a changed setting rather than a constant.
- `test_pccm2_an_unset_level_means_no_cell_fill` — "No high or critical", and
  a level cleared to `""`, give `fill is None` and `source == SOURCE_NONE`.
- `test_pccm2_the_cell_text_clears_the_contrast_bar` — over the same six
  colours `test_plcm44` used, `contrast_ratio(fill, text_color) >= 4.5`. This
  is `AGENTS.md`'s requirement for a data colour used as a fill, and it is
  what `src/getmoredone/color_contrast.py` is for.

**PCC-M3 — the five Priority cells are drawn from that authority, not from `danger`.**
Each cell takes `fg_color`, `text_color` and `corner_radius` from
`level_cell_fill`; with no fill it keeps the screen's own `row_text`, so it
stays legible on a segment or completed row. The local
`is_priority_critical` goes away — the cell no longer asks "is this critical",
it asks "what colour is my level".

- `test_pccm3_every_priority_cell_calls_the_helper` — AST over the five row
  builders: exactly one `level_cell_fill` call each, five in total, and
  `len(ROW_BUILDERS) == 5` so a screen cannot be dropped from the list and the
  test still pass. Exact counts, never a floor (`CLAUDE.md`, *Test rules*).
- `test_pccm3_a_critical_cell_is_drawn_in_the_level_colour` — real widgets, no
  AST: build one row per screen for an Any Critical item and read the score
  label's `cget("fg_color")` and `cget("text_color")`. Asserts the colour the
  user sees, not the shape of the source.
- `test_pccm3_an_uncoloured_cell_keeps_the_rows_text` — a "No high or critical"
  item on a segment-filled row: the cell is transparent and its text is the
  row's derived text, not `pick_text_color`'s answer for nothing.

**PCC-M4 — a critical I/U factor chip takes the Any Critical level colour.**
Four screens. `is_critical_factor` stays the authority for *whether* a chip is
critical (`LRR-M1.2`); only the colour moves, to
`fill_for_level(settings, LEVEL_ANY_CRITICAL)`.

- `test_pccm4_a_critical_chip_takes_the_level_colour` — the four screens, by
  widget: the chip's `fg_color` is the Any Critical colour and its text is
  derived from it.
- **Stated, not fixed:** if the user clears Any Critical to no fill, a critical
  chip gets no background and no longer stands out. That is the setting doing
  what it says, and `test_pccm2_an_unset_level_means_no_cell_fill` covers the
  mechanism. Recorded here so it is a decision and not a surprise.

**PCC-M5 — no hard red is left in the five row builders, and no new literal.**

- `test_pccm5_no_row_builder_uses_the_danger_palette` — AST scoped to the five
  row-builder functions, exact count zero for `palette["danger"]` and
  `self.palette["danger"]`. Scoped to the function, not the file, because
  `button_style("danger")` elsewhere in those screens is legitimate.
- No new colour literal is added anywhere: every colour comes from
  `theme.priority_level_fill_colors` or the user's setting.
  `./venv/bin/python tools/color_audit.py` is run regardless, and
  `docs/ui_color_inventory.md` is committed if it moves.

### Tests retired or rewritten, with the reason

`CLAUDE.md` forbids modifying a test to make it pass without first naming
which of (a) the code is wrong, (b) the behaviour changed intentionally,
(c) the test was over-specified. **All five below are (b).**

| Test | Disposition |
|---|---|
| `test_plcm41_a_row_takes_its_level_colour` | **Retired.** Its claim is the one being reversed. `test_pccm1_a_level_no_longer_fills_a_row` asserts the new behaviour. |
| `test_plcm42_segment_and_completed_still_win` | **Rewritten** as `test_pccm1_segment_and_completed_still_fill_a_row`; the level clause is gone. |
| `test_plcm43_an_unset_level_means_no_fill` | **Moved** to the cell: `test_pccm2_an_unset_level_means_no_cell_fill`. The `None`-not-`""` reason survives verbatim. |
| `test_plcm44_level_fill_text_clears_the_contrast_bar` | **Moved** to the cell: `test_pccm2_the_cell_text_clears_the_contrast_bar`, same six colours. |
| `test_plcm49_controls_follow_a_level_fill` | **Retired.** It builds a `RowFill` by hand, so it would keep passing — but no row takes a level fill any more, so it would guard a state the app cannot reach. `test_lrr_cold_a_segment_fill_carries_its_controls_too` covers the live case. |

`test_plcm45_a_non_priority_fill_leaves_row_text_alone` is **narrowed**: its
"no fill" clause now covers a critical item too, which is the same assertion
with a wider input. `test_plcm46`, `test_plcm47`, `test_plcm48`,
`test_plc_cold_the_three_screens_with_row_controls_pass_the_kwargs` and the
`LRR` and `SCV` tests are **unchanged and must stay green** — the level table
is still the scheme, `row_fill` is still called once per screen, and segment
fills still carry their controls.

Every new test is mutation-proved before the batch closes: delete or invert the
line it names, run it, confirm red, restore **the verbatim original**.

### Documentation (global rule 13; `tools/agents/check_docs_sync.py`)

**PCC-D1 — `AGENTS.md`, *Semantic color rules*.** The paragraph names
`priority_levels.row_fill` as the one path where a data colour may fill a row
with a derived foreground, and lists Today, Upcoming and All Items as taking
it. After this batch that path is segment-and-completed only, and the level
colour is a *cell* fill with its own derived foreground. The rule itself does
not change; what satisfies it does.

**PCC-D2 — `docs/USER_GUIDE.md`, *Priority Colours*** (lines 794–844). Six
sentences assert the old behaviour and are now wrong:
the "row tint … tints the whole row in Today, Upcoming, All Items,
Hierarchical and Completed" opener; "the row keeps the theme's own background"
for the third level; "The row's *text* colour is chosen automatically … and
the row's own controls … follow it"; "A **VSP segment colour outranks these
tints**"; and the closing "The red `P:` priority chip on a row is unchanged
and still marks a Critical item, so with a green Any Critical the row and its
chip differ by design" — which this batch exists to end.

**PCC-D3 — `docs/spec_coverage.md`** gains the PCC criteria, per
`spec-work.md`.

**PCC-D4 — `BACKLOG.md`** is touched only if a sweep finds something out of
scope. Nothing is known to file today. The three `PRI` items and the `CIV`
items are untouched.

## 5. Order of work

1. PCC-M2 — the authority, with its tests. No screen changes yet, so the
   suite stays green except for the five dispositions above.
2. PCC-M1 — delete the level branch; retire and rewrite those five tests.
3. PCC-M3 — the five Priority cells.
4. PCC-M4 — the four chip sites.
5. PCC-M5 — the guard, plus `tools/color_audit.py`.
6. PCC-D1…D4.
7. Sweep: one cold pass (`learning-qa` or a fresh subagent), below-medium
   findings dropped. A second pass only if the first finds a high.
8. `/csdp`. Push the branch; offer a merge. **No pull request.**

Commits: `src/` and `tests/` separate, so the ratio stays visible in
`git log --stat` (`CLAUDE.md`, *Test rules*).

Test runs, every time, never the full suite locally:

```
GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest \
  tests/test_priority_level_colors.py tests/test_color_inventory_sync.py -q
```

## 6. Adjacent issues found, not fixed (global rule 10)

Scanned `src/getmoredone/screens/` for the same pattern. Two findings, neither
in scope, and **neither is filed in `BACKLOG.md` until this plan is approved**
— the `PRI` section exists because a previous plan promised filings and never
made them.

- **PCC-A1 (low) — `screens/item_editor_dialogs.py:257` and `:476`** draw a
  `P:{priority_score}` label under a `"Priority"` header with **no colour at
  all**, in the parent/child picker dialogs. They are the only other place a
  priority score is shown in a list. Left alone: the user named the list
  screens, and a dialog that has never been coloured is not the red being
  replaced.
- **PCC-A2 (low) — the score column's width.** `width=60` in four screens and
  `width=80` in All Items, which is already `PRI-A2`, open. This batch touches
  those exact lines and deliberately does not change the widths, because a
  four-digit score in a 60px slot is a separate measurement (`PRI-M3`,
  specced and not built).

## 7. What this plan does not do

- It does not change the three level colours themselves, or the Settings tab.
  The green stays green; it moves.
- It does not touch the Plan screen's priority *bands*
  (`theme.priority_band_colors`, `theme.priority_fill_colors`). A band is a
  threshold on the score and a different question — `priority_levels`'
  module docstring explains why, and `test_plcm14` guards the distinction.
- It does not change `row_control_kwargs`. Its live caller is the segment
  fill, which still derives a text colour.
