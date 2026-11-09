# Implementation plan — the tests PRI-M1 and PRI-M2 shipped without (2026-11-08)

Status: **built and on `main`** — `tests/test_priority_floor_and_cap.py`
carries 15 tests including `test_prim11_…` and `test_prim12_…`. The build
status was added 2026-11-09 by the third cold pass over the SST batch; this
line recorded only how the plan was approved. Proceeding without a separate
approval round: the user's standing
instruction for this stretch was "proceed on your own recommendations as I'm
going to be away ... you can then start on open items", given after the PDT
batch's sweep. That is the authorization to pass the plan-approval gate the
global rules otherwise require, and it is recorded here rather than assumed.
Source: `BACKLOG.md` item 2 ("PRI-M1/M2 shipped without its tests", medium) and
`SSC-1` (high).

Spec: `docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md`. Its
acceptance criteria are used **verbatim** (PRI-M1.1 … PRI-M2.7); this file adds
no criteria of its own, because the work is writing the tests that spec already
names, not deciding new behaviour.

---

## What is actually there now — checked before planning, not assumed

Measured on `main` at `67612d5`.

| Piece | State today | Evidence |
|---|---|---|
| `PriorityFactors.MAX_SCORE` | `9999`, with the cap's cost stated in its comment | `models.py`, `grep -n "MAX_SCORE = " src/getmoredone/models.py` |
| `PriorityFactors.lowest` / `.floor()` | read `min(scale.values())`, not literals | same file |
| `priority_score_from_factors` | one scorer; `0` on any missing/zero factor, else `min(product, MAX_SCORE)` | same file |
| `priority_score_label` | `"n (i×u×s×v)"`, and `"n (capped — …)"` when the raw product exceeds the cap | same file |
| `apply_priority_floor` | fills each `None` factor from `floor()`; **one** call site | `grep -n apply_priority_floor src/getmoredone/db_manager.py` → create only |
| `create_action_item` | calls the floor on every create path, before `update_priority_score()` | `db_manager.py`, in the `PRI-M1` comment block |
| Item Editor live label | routes through `priority_score_label` | `screens/item_editor.py`, in `update_priority_display` |
| Row-click popup label | routes through the same function | `screens/inline_editors.py`, in `update_score` |
| New-item form floor | `apply_defaults_to_form` sets each empty combobox to its scale's lowest | `screens/item_editor.py`, in the `PRI-M1.7` comment block |
| **PRI-M3 (the four-digit column)** | **not built.** The `P:` labels are still literal `width=60` in five screens, with no shared width constant and no header-sharing | `grep -rn "SCORE_COLUMN\|score_column_width" src/` returns nothing |
| **Every test the spec names** | **none exists.** No `tests/test_priority_floor_and_cap.py`, no `tests/test_priority_floor_form.py`, no `tests/test_priority_column_width.py` | `ls tests/ \| grep -i priority` |

So PRI-M1 and PRI-M2 are implemented and unverified; PRI-M3 is neither.

## Scope — and what is deliberately left out

**In scope:** the fourteen tests for PRI-M1.1–M1.8 and PRI-M2.1–M2.6, in the
two files the spec names, plus PRI-M2.7's comment correction. That is exactly
`BACKLOG.md` item 2's subject.

**Out of scope, and not silently dropped:**

- **PRI-M3 is not built in this batch.** It is a feature change — a shared
  width constant threaded through five list screens and `today.py`'s header —
  against the repo's aligned-column contract, not a test gap. Writing its two
  tests against today's code would assert a design nobody has implemented.
  Filed below as `PRIT-N1` rather than built, because scaling this batch up to
  a five-screen UI change is the user's call, not mine. The cap it exists to
  serve is already in place, so nothing is broken by the delay: the column was
  already sized for four digits, and what PRI-M3.1 would add is the *proof*
  that `"P:9999"` fits at all eleven selectable row font sizes.
- **`PRI-A1`–`PRI-A4`**, which the PRI plan and `docs/DOCUMENTATION_INDEX.md`
  both promise, appear in no backlog. Noted in `SSC-1`; this batch does not
  invent them.

## Acceptance criteria → the test that verifies each

Every row is the spec's own criterion ID and the spec's own test name. A test
is `done` only when it has been mutation-proved: the line it names deleted or
inverted, the test run, confirmed red, and the **verbatim** original restored.

### `tests/test_priority_floor_and_cap.py`

| Spec ID | Test | Shape |
|---|---|---|
| PRI-M1.1 | `test_prim11_the_floor_is_the_minimum_of_each_scale` | Parametrized over the four scales; plus a monkeypatched scale whose minimum is neither 1 nor 2, so a literal `1`/`2` in the floor would fail. This is the test that makes PRI-M1.1 mean something. |
| PRI-M1.2 | `test_prim12_a_new_item_is_never_unscored` | `create_action_item` with no factors and no Defaults → stored row reads `1, 1, 2, 2` and `priority_score == 4`. Read back from the database, not from the in-memory object (P6). |
| PRI-M1.3 | `test_prim13_defaults_outrank_the_floor` | A who default of `importance=20` is not lowered; a system default likewise. |
| PRI-M1.4 | `test_prim14_the_floor_fills_only_what_is_missing` | System default `importance=10` → `10, 1, 2, 2`, score 40. |
| PRI-M1.5 | `test_prim15_an_explicit_factor_survives_the_floor` | Including the `apply_defaults=False` path, which is the one the floor was moved out of `_apply_defaults` to cover. |
| PRI-M1.6 | `test_prim16_editing_an_unscored_row_does_not_backfill` | D3: a row stored with `None` factors, updated, still reads `None` and score 0. This is a dirty-state test (P8): the row persists between the two calls. |
| PRI-M2.1 | `test_prim21_the_cap_is_four_digits_and_leaves_every_band_reachable` | `MAX_SCORE == 9999`, `len(str(MAX_SCORE)) == 4`, and `MAX_SCORE` above the top `PRIORITY_BANDS` threshold so `critical` is still reachable after the cap. |
| PRI-M2.2 | `test_prim22_every_factor_combination_is_capped` | All 256 combinations of the four scales. Asserts `min(product, MAX_SCORE)` for each, **and the exact counts** — 223 unchanged, 33 clamped — rather than a floor, so a narrowing is visible. Also asserts the four distinct capped raw products and that no raw product equals the cap, which is what makes "capped" detectable at all. |
| PRI-M2.3 | `test_prim23_a_missing_factor_is_still_unscored` | `None` and `0` in each of the four positions → `0`, not the cap and not the floor. |
| PRI-M2.4 | `test_prim24_the_stored_score_is_capped_on_create_and_on_update` | A 20/20/16/16 item reads back `9999` from the database after create **and** after update. |
| PRI-M2.5 | `test_prim25_only_one_function_multiplies_the_factors` | AST walk over `models.py`, `screens/item_editor.py`, `screens/inline_editors.py`; **exact count of 0** four-factor products outside `priority_score_from_factors`. Per the repo rule, this is parsed, not grepped, and counted exactly rather than floored. |
| PRI-M2.6 (model half) | `test_prim26_the_label_says_capped_only_above_the_cap` | `priority_score_label` at the boundary: the highest uncapped product (6400) gets no "capped", the lowest capped one (12800) does. The UI half is in the other file. |

### `tests/test_priority_floor_form.py`

| Spec ID | Test | Shape |
|---|---|---|
| PRI-M1.7 | `test_prim17_the_new_item_form_shows_the_lowest_factors` | Real `ItemEditorDialog` against a withdrawn root — `tests/test_item_editor_no_context.py` is the working precedent, and `conftest.py` already silences `grab_set` and withdraws every window on creation, so this adds no mapped window and the documented mapped-window count does not change. With no Defaults configured, the four comboboxes read `"Low (1)"`, `"Low (1)"`, `"S (2)"`, `"S (2)"` and the label reads `4`. |
| PRI-M1.8 | `test_prim18_an_existing_row_is_not_shown_a_floor_it_does_not_have` | `load_item_data` on a row with `importance=None` leaves that combobox **empty**. The pair with M1.7: the floor is a create-time rule, so the editor must not display it on an existing row. |
| PRI-M2.6 (UI half) | `test_prim26_a_capped_label_says_it_is_capped` | Both render sites, driven as behaviour: set the four factors and call `update_priority_display` on a real `ItemEditorDialog`, and `update_score` on a real `InlinePriorityDialog`, then read the label text. Asserts `"9999 (capped — 20×20×16×16)"` for 20/20/16/16 and the uncapped form for 20/10/4/8, **at both sites**, since PRI-M2's stated purpose was that three copies of this arithmetic were collapsed into one. |

### PRI-M2.7 — the legacy comment

Not a new test. `tests/test_time_block_layout.py` has a row asserting
`102400 → critical`; its comment calls that "the top of the scale", which the
cap made false. Corrected to "a legacy pre-cap score", which is what it now is.
Rows written before the cap are still in the database and must not be
re-coloured, so the assertion itself is right and stays.

### SSC-1 — the plan's own status

`docs/implementation_plan_2026-11-08_priority_defaults_and_cap.md` heads itself
"awaiting approval. No implementation code written" over code that is on
`main`, and `docs/DOCUMENTATION_INDEX.md` repeats it. Corrected in this batch
because it is the spec this batch implements against, so leaving it would mean
writing tests for criteria the document says were never built. The correction
marks the status rather than rewriting the plan: M1 and M2 built, M3 not, tests
added here. `PRI-A1`–`PRI-A4` stay unfiled and `SSC-1` stays open for that part.

## Implementation order

1. `tests/test_priority_floor_and_cap.py` — the model-only tests first
   (PRI-M2.1, M2.2, M2.3, M2.6-model, M1.1), since they need no database and no
   widget, so a failure there is unambiguous.
2. The database tests in the same file (PRI-M1.2, M1.3, M1.4, M1.5, M1.6,
   M2.4). Every `DatabaseManager` takes an explicit `tmp_path` database.
3. PRI-M2.5's AST walk, last in that file: it is the one test whose subject is
   the source text, so it is written after the behavioural tests prove the
   behaviour it is guarding.
4. `tests/test_priority_floor_form.py` — the widget tests. (Planned as three;
   built as four, PRI-M1.7 taking two. The file's own table below lists both.)
5. PRI-M2.7's comment correction.
6. Mutation-prove each test, restoring the verbatim original.
7. SSC-1's status correction, and the documentation index entry for this plan.

Test changes commit separately from any `src/` change, per the repo rule. In
this batch the only non-test source edits are comment text, so the split is
test commits plus one documentation commit.

## Criteria that cannot be made code-testable

None in scope. PRI-M3.1's "fits at every selectable font size" is measurable
with `CTkFont.measure` on a withdrawn root, so it is testable — it is out of
scope because the code it would measure has not been written, not because it
resists a test.

## Risks

- **PRI-M2.5's AST walk may fail on first write** for a legitimate reason: a
  four-factor product elsewhere that is not a score. If so, the honest outcome
  is to narrow the walk to products of the four *factor variables*, stated in
  the test, rather than to raise the count above 0.
- **The widget tests may surface a real defect** in `apply_defaults_to_form` or
  in either label. That is the point of writing them, and the batch will report
  it as a finding rather than adjust the test to pass — repo rule case (a).

## Filed, not built

- `PRIT-N1` — PRI-M3, the four-digit column, with its two tests. The decision
  to widen five list screens' score column to one shared constant is the
  user's.
