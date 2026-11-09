# Implementation plan — a new item starts at the lowest priority, and the score is capped at 9999 (2026-11-08)

Status: **PRI-M1 and PRI-M2 are built and on `main`; PRI-M3 is not.**
Corrected 2026-11-08: this line previously read "awaiting approval. No
implementation code written", which was false from the moment `9420927`
("feat(pri): priority defaults and the cap, as left on disk") landed. The
implementation docstrings are in `src/getmoredone/models.py`, `db_manager.py`,
`screens/item_editor.py` and `screens/inline_editors.py`; `grep -rn
"SCORE_COLUMN\|score_column_width" src/` returns nothing, which is PRI-M3. The
criteria below shipped without a single test; those are being written now
against this file, in `docs/implementation_plan_2026-11-08_pri_tests.md`. The
plan's body is left as it was written, because it is the record of what was
decided; only this status line is corrected. `PRI-A1`-`PRI-A4`, which §9 below
promises, are still filed nowhere - `SSC-1` in `BACKLOG.md` stays open for
that.
Source: user requirement, 2026-11-08 — "when creating a new action item the
priority setting are the lowest value for each item. Max the calculated value
at 9999 so the column width is 4 digits wide."

---

## What is actually there now — checked before planning

| Piece | State today |
|---|---|
| `models.py:82` `ActionItem.calculate_priority_score` | `importance × urgency × size × value`; returns **0** if any factor is `0` or `None`. No upper bound. |
| `models.PriorityFactors` | `IMPORTANCE`/`URGENCY` = Critical 20, High 10, Medium 5, **Low 1**; `SIZE`/`VALUE` = XL 16, L 8, M 4, **S 2**. So the product runs **4 … 102400**. |
| `db_manager.py:1154` `_apply_defaults` | Fills `importance`/`urgency`/`size`/`value` from the **who** default, else the **system** default. When neither names a factor it leaves it `None` — the item is stored unscored, `priority_score = 0`. |
| `db_manager.py:125` `create_action_item` | Calls `_apply_defaults` only when `apply_defaults=True`, then `item.update_priority_score()`. |
| `screens/item_editor.py:1220` `apply_defaults_to_form` | Same precedence for the *form*: with no default configured the four comboboxes are left **empty**, so a new item shows "Score: 0". |
| `screens/item_editor.py:1635` | A **second copy** of the product arithmetic, for the live "Score: n (i×u×s×v)" label. |
| `screens/inline_editors.py:202` | A **third copy**, for the row-click Priority Factors popup. |
| `time_block_layout.PRIORITY_BANDS` | Thresholds 2000 / 500 / 100 / 1 on the score, plus `unscored`. Comment states the range as "4 .. 102400". |
| Score column, five list screens | `today.py:657`, `upcoming.py:422`, `completed.py:275`, `hierarchical.py:313` draw `P:{score}` at **`width=60`**; `all_items.py:375` draws the bare number at **`width=80`**; `item_editor_dialogs.py:260,479` at **`width=70`**. `today.py:231` carries the matching header `("Pri", 60)`. |
| Row font | `theme.LIST_ROW_FONT_SIZE` defaults to 14 but is user-settable **10–24**, so the column's text width is not fixed. |

Two consequences of today's code that the request is about:

- **A new item is unscored, not lowest.** Unless Defaults are configured, a
  freshly created item sorts at the bottom of every `priority_score DESC` list
  *and* is drawn in the `unscored` grey rather than the `low` band.
- **The column can be overflowed by arithmetic.** `20 × 20 × 16 × 16` is
  `102400` — `P:102400`, eight characters, in a slot sized for four digits.

---

## Decisions proposed, not assumed silently — say if any is wrong

### D1. The cap is applied to the **stored** score, and it loses ordering at the top

"Max the calculated value at 9999" is implemented as
`min(product, 9999)` inside the one scoring function, so the capped number is
what is stored in `action_items.priority_score`, what sorts the lists, and what
is displayed.

The cost, counted rather than estimated: of the 256 factor combinations, **33
exceed 9999**, and they collapse onto **four** distinct scores —
`12800`, `25600`, `51200`, `102400` → all `9999`. The distinct-score count
drops from 27 to 24, and the highest-priority items — the ones at the top of
Today — stop being ordered against each other; they tie, and the queries fall
through to their secondary key (`created_at ASC`, or `title` in All Items). The
next value *below* the cap is `6400`, so everything from `12800` up is one flat
tier.

**Recommended anyway**, because it is what was asked for and because it keeps
one number everywhere: cap it once and no reader can disagree about it.

**The alternative, if the ordering matters more than the single number:** store
the true product and cap only the *display* (`min(score, 9999)`, drawn as
`9999+` when clamped). The column is still four digits plus a marker, and
sorting at the top keeps working. Say which you want — this is the one decision
in this batch that cannot be reversed by a later edit without rewriting stored
rows.

### D2. The floor is applied to every **create**, in one place

`create_action_item` gets the floor immediately before
`item.update_priority_score()`, so it runs on **every** create path, not only
the ones that pass `apply_defaults=True`. One rule, stated once: *no row this
app creates is unscored.*

Scope of that choice, so it is not a surprise: it also reaches the Weekly
Tactic container rows (`weekly_tactic.py:565`), the week-action items from the
Weekly Items and Week Actions screens (`weekly_items.py:583`,
`week_actions.py:186`), the VSP auto-created items (`vps_manager.py:1052`), and
`duplicate_action_item` / the derive-next-day path — which copy all four
factors from their original, so the floor only bites when **the original itself
was unscored**, and the copy then scores 4 while the original stays 0. Demo
data sets all four factors explicitly and is unaffected.

**The narrower alternative:** put the floor inside `_apply_defaults`, where
`apply_defaults=False` opts out. That leaves "Add Action Item" on the Weekly
Items screen creating unscored items while the same action in the Item Editor
creates a 4 — the inconsistency the single rule exists to avoid.

### D3. Existing rows are never back-filled

The floor is a **create**-time rule. `update_action_item` keeps `None` factors
as `None`, so an item that is unscored today stays unscored until someone edits
its factors. Back-filling on save would rewrite history on every unrelated edit
(P6 — a status that claims a value the user never set).

### D4. At the cap, the breakdown label says so

The editor's label is `"Score: 9999 (20×20×16×16)"` today — after the cap those
numbers multiply to 102400, so the label as it stands would be arithmetically
false. It becomes `"9999 (capped — 20×20×16×16)"`. Same change in the row-click
popup, which has its own copy of the label.

### D5. The three copies of the arithmetic become one function

The cap has to hold in all three places, and the current shape guarantees they
drift (P5: fix the whole class, not one call). `models.py` gains the single
`priority_score_from_factors(importance, urgency, size, value)`;
`ActionItem.calculate_priority_score`, the editor label and the popup label all
call it. A guard test asserts no module multiplies the four factors itself.

### D6. The floor and the cap are config, not literals

The floor is `min(scale.values())` on each factor's **own** scale, so
renumbering `PriorityFactors` moves the floor with it (the same reasoning
`priority_levels.py` already carries for the level thresholds). The cap is
`PriorityFactors.MAX_SCORE = 9999`, one constant, with the four-digit column as
its stated reason.

---

## M1 — Every new action item starts at the lowest value on each factor

New: `models.apply_priority_floor(item)`. Called from `create_action_item`.

| ID | Acceptance criterion | Verified by |
|---|---|---|
| PRI-M1.1 | The floor for a factor is the minimum of that factor's own scale, read from `PriorityFactors`, not a literal. Renumbering a scale moves the floor. | `tests/test_priority_floor_and_cap.py::test_prim11_the_floor_is_the_minimum_of_each_scale` (parametrized over the four scales; plus a monkeypatched scale whose minimum is not 1 or 2) |
| PRI-M1.2 | `create_action_item` on an item with no factors and **no** Defaults configured stores `importance=1, urgency=1, size=2, value=2` and `priority_score=4`. | `::test_prim12_a_new_item_is_never_unscored` |
| PRI-M1.3 | A who default and a system default both still outrank the floor; a who default of `importance=20` is not lowered. | `::test_prim13_defaults_outrank_the_floor` |
| PRI-M1.4 | A partially-configured default fills only what it names; the floor fills the rest (system default `importance=10` → `10, 1, 2, 2`, score 40). | `::test_prim14_the_floor_fills_only_what_is_missing` |
| PRI-M1.5 | A factor the caller set explicitly is never lowered, including on paths that pass `apply_defaults=False`. | `::test_prim15_an_explicit_factor_survives_the_floor` |
| PRI-M1.6 | `update_action_item` on a row whose factors are `None` leaves them `None` and the score 0 — D3. | `::test_prim16_editing_an_unscored_row_does_not_backfill` |
| PRI-M1.7 | The new-item editor **shows** the floor before the first save: with no Defaults configured, `apply_defaults_to_form` sets each combobox to its lowest label (`"Low (1)"`, `"S (2)"`) and the label reads `4`. | `tests/test_priority_floor_form.py::test_prim17_the_new_item_form_shows_the_lowest_factors` (unbound method over a fake dialog, the `SimpleNamespace` pattern already used in `tests/test_item_editor.py`) |
| PRI-M1.8 | Editing an **existing** item does not move its factors: `load_item_data` on a row with `importance=None` leaves that combobox empty rather than showing the floor. | `::test_prim18_an_existing_row_is_not_shown_a_floor_it_does_not_have` |

## M2 — The calculated score is capped at 9999

| ID | Acceptance criterion | Verified by |
|---|---|---|
| PRI-M2.1 | `PriorityFactors.MAX_SCORE == 9999`, is four digits wide, and is above the top `PRIORITY_BANDS` threshold so every band stays reachable. | `tests/test_priority_floor_and_cap.py::test_prim21_the_cap_is_four_digits_and_leaves_every_band_reachable` |
| PRI-M2.2 | For **all 256** factor combinations, the score is `min(product, MAX_SCORE)`: 223 unchanged, 33 clamped. | `::test_prim22_every_factor_combination_is_capped` (parametrized over the full product set) |
| PRI-M2.3 | A missing or zero factor is still `0`, not the cap and not the floor — `unscored` survives the change. | `::test_prim23_a_missing_factor_is_still_unscored` |
| PRI-M2.4 | The **stored** row is capped, on create and on update: a 20/20/16/16 item reads back `9999`. | `::test_prim24_the_stored_score_is_capped_on_create_and_on_update` |
| PRI-M2.5 | One function computes the score. No module multiplies the four factors itself — AST walk over `models.py`, `screens/item_editor.py`, `screens/inline_editors.py`, asserting an **exact count of 0** four-factor products outside `priority_score_from_factors`. | `::test_prim25_only_one_function_multiplies_the_factors` |
| PRI-M2.6 | Both score labels show the cap and say it is capped (D4): the editor's `update_priority_display` and the popup's `update_score` render `"9999 (capped — 20×20×16×16)"` for 20/20/16/16, and the uncapped form for 20/10/4/8. | `tests/test_priority_floor_form.py::test_prim26_a_capped_label_says_it_is_capped` |
| PRI-M2.7 | `priority_band` still classifies pre-cap rows already in the database (`102400` → `critical`), so the cap does not re-colour history. | existing `tests/test_time_block_layout.py` row, comment corrected from "the top of the scale" to "a legacy pre-cap score" |

## M3 — The column is four digits wide

| ID | Acceptance criterion | Verified by |
|---|---|---|
| PRI-M3.1 | The widest text the column can now hold — `"P:9999"`, and `"9999"` in All Items — fits the label's width at **every** selectable row font size (10–24), measured with the real font. | a new `test_priority_column_width.py` under `tests/`, `test_prim31_the_score_column_holds_four_digits_at_every_font_size` (planned; not written — `PRI-M3` is open) (`CTkFont.measure` on a withdrawn root — no mapped window, so the documented mapped-window count does not change) |
| PRI-M3.2 | The row label and `today.py`'s header read their width from **one** place, so the header cannot drift from the column it labels (the repo's aligned-column contract). | `test_prim32_the_header_and_the_row_use_one_width` (planned with it; not written) |

If PRI-M3.1 fails at the larger font sizes, the fix inside this batch is to
derive the constant from the font rather than raise a magic number, and
`today.py:231`'s `("Pri", 60)` moves with it. That is a measurement, not a
guess, which is why it is written as a test rather than as a number in this
plan.

---

## Implementation order

1. **M2 first, in `models.py`** — the shared `priority_score_from_factors`, the
   `MAX_SCORE` constant, `calculate_priority_score` delegating to it. Nothing
   else can be tested honestly until there is one scoring function.
2. **M1 in `models.py` + `db_manager.create_action_item`** — the floor, which
   needs the capped scorer already in place.
3. **M1.7 / M2.6 in the two UI modules** — the form defaults and the two
   labels, both now calling the shared function.
4. **M3** — the measurement, then whatever width it demands.
5. **Docs** — `docs/USER_GUIDE.md` §"Priority score" (the 4…9999 range, the
   floor on new items, the cap and what it costs at the top) and §"Defaults";
   `time_block_layout.py`'s range comment; `NOTES.md`; `CHANGELOG.md`;
   `docs/DOCUMENTATION_INDEX.md`; `docs/spec_coverage_2026-11-08_priority_defaults_and_cap.md`;
   handoff note `docs/changes/2026-11-08-priority-defaults-and-cap.md`.

Test commits stay separate from `src/` commits.

---

## Criteria that cannot be made code-testable

- **That the column looks right in the running app.** The measurement in
  PRI-M3.1 proves the string fits the slot; it does not prove the row still
  reads well at font 24, or that nothing else in the row reflowed. Manual
  checklist, in the handoff note: open Today, Upcoming, All Items, Completed
  and Hierarchy at font 14 and at font 24, with one 9999 item and one unscored
  item in view.
- **That 9999 is the right ceiling for you.** D1's cost is counted above but
  whether a flat top tier is acceptable is a judgement about how you use the
  list, not a property of the code.

---

## Adjacent issues found, not fixed

1. **`item.importance == 20 or item.urgency == 20`, written out by hand in five
   screens** — `today.py:653`, `all_items.py:372`, `completed.py:271`,
   `hierarchical.py:309`, `upcoming.py:418`. The literal `20` is P4, and
   `priority_levels.priority_level_for_item` already answers exactly this
   question. Not touched here: it is the same five-screen duplication the
   priority-level-colours batch filed, and folding it in would put a second
   unrelated rewrite in this diff.
2. **The score column's width is a magic number in six places** (60, 60, 60,
   60, 80, 70) and only `today.py` has a header to match. M3 touches the
   constant it must; unifying all six is a separate change.
3. **All Items shows the bare score, the other four show `P:n`** — a different
   column for the same number, in a 80px slot instead of 60px.
4. **`demo_data.py` creates with `apply_defaults=False` and hard-codes its
   factors**, so demo items are unaffected by both Defaults and the floor.
   Correct today; worth stating because it is why a demo database will not
   demonstrate this change.

Each is filed in `BACKLOG.md` as PRI-A1 … PRI-A4 when this plan is approved.
