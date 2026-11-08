# Spec + implementation plan — a Weekly Tactic acts as the parent of the Action Items linked to it

**Date:** 2026-11-08
**Area:** hierarchy readers (`db_manager`), Hierarchical screen, Item Editor,
VSP weekly tactic delete/complete paths
**Status:** awaiting approval. No implementation code written.
**Prefix for all IDs below:** `WTP`

---

## 0. What was asked

Verbatim, from the request:

> A weekly tactic item when linked to an Action Item becomes it's parent and
> should act like a parent record

Asked which of the app's existing "parent" behaviours that should cover, the
answer was **all four offered**:

1. Hierarchy views — the Hierarchical screen tree, and the Item Editor's
   Hierarchy dialog (`PARENT ITEM` / `CHILD ITEMS`).
2. The Item Editor's `Parent: <title>` label, with a View Parent button.
3. The delete guard, and the tactic delete cascade.
4. Completion rollup — flagged in the question as **not** current parent
   behaviour (a `parent_id` parent has no rollup today), so this one is new
   behaviour rather than parity, and was chosen anyway.

---

## 1. What is there now

### 1.1 A Weekly Tactic is already an Action Item

A Weekly Tactic is a row in `action_items` with `item_type = 'week'`
(`database.py:160`). It is created with `parent_id` **unset** — both creation
paths (`weekly_tactic.py:505`, `vps_manager.py:1032`) leave it NULL — and with
`annual_plan_element_id` required (`db_manager.py:1980`).

So a tactic is, today, a root item that happens to carry a date range.

### 1.2 The link from an Action Item to its tactic is not `parent_id`

The link lives in `action_items.weekly_tactic_id` (`models.py:45`). That is
deliberate, and defended in three places:

- `weekly_tactic.tactic_of` (line 133) reads `weekly_tactic_id` **alone**, and
  WT-M3.D.1 names it the single authority for "is this item week-filed",
  because WT-INV6 turns on it: an item with no Weekly Tactic is never modified
  by any re-filing rule.
- `weekly_tactic_migrations._move_week_links_off_parent_id` (line 132) rewrites
  every `parent_id` whose parent is a week row into `weekly_tactic_id` and
  **nulls `parent_id`**, on every launch.
- `weekly_tactic.LINK_PREDICATE_SQL` (line 193) is the one SQL home for "which
  tactic's panel lists this item". It reads both columns, preferring
  `weekly_tactic_id`, and AWA-M2.3's guard test asserts it is the only
  predicate-shaped string constant in `src/getmoredone`.

One button still writes `parent_id` instead — `weekly_items.py:560`, the APE
Week Assignment tab's *Add Action Item* — which is the open **AWA-A1**
(`BACKLOG.md:85`). This spec does **not** fix AWA-A1; see §7.

### 1.3 Every "parent" reader in the app reads `parent_id` only

| Reader | Where | What it does with `weekly_tactic_id` |
|---|---|---|
| `get_children(parent_id)` | `db_manager.py:816` | nothing — `WHERE parent_id = ?` |
| `get_subtree(item_id)` | `db_manager.py:834` | nothing — walks `get_children` |
| `get_root_items()` | `db_manager.py:855` | nothing — `WHERE parent_id IS NULL` |
| tree + `(N sub)` count | `hierarchical.py:155, 203, 322` | nothing |
| `PARENT ITEM` / `CHILD ITEMS` | `item_editor_dialogs.py:109, 140` | nothing |
| `Parent: <title>` label | `item_editor.py:305` | nothing |
| delete guard ("has N child items") | `item_editor.py:1499` | nothing |
| tactic delete cascade | `vps_manager.py:1267` | nothing — `DELETE … WHERE parent_id = ?` |
| completion | `db_manager.py:520` | re-files the item (WT-M5.A); no rollup |

The visible consequences today, for an item linked by `weekly_tactic_id`:

- It appears in the Hierarchical screen as a **root**, beside its own tactic,
  at the same indent level, unconnected to it.
- The tactic's row shows no `(N sub)` count.
- The Hierarchy dialog shows the item with no parent and the tactic with no
  children.
- The editor shows no `Parent:` line — the tactic appears only as the Organise
  tab's Weekly Tactic row (`item_editor.py:589`).
- The tactic can be deleted with no "has N child items" guard, and
  `delete_weekly_action_item` then deletes only its `parent_id` children, so
  every `weekly_tactic_id` item **survives the delete as an unparented root
  item**, with no record of the week it had been filed under.

  **Corrected 2026-11-08, during implementation.** This bullet first claimed
  such an item survived "with a link to a row that is gone", 49 of them on the
  main database. That is wrong. `action_items.weekly_tactic_id` is
  `REFERENCES action_items(id) ON DELETE SET NULL` and `database.py:129` sets
  `PRAGMA foreign_keys = ON`, so deleting a tactic *nulls* the column. Counted
  read-only against the main database on 2026-11-08: 939 action items, 25 week
  rows, 49 linked by `weekly_tactic_id`, 0 linked by `parent_id` to a week row,
  and **no** link of either kind that fails to resolve. The item is left
  behind, but it is not left pointing at nothing. WTP-D6 and WTP-D7 are
  corrected below; the vacuous test this error produced is recorded in §6.

### 1.4 The one piece that already reads both columns

`vps_manager.get_action_items_for_weekly_tactic` (line 1110) is the panel
reader: given a tactic, it returns everything linked to it by either column,
via `LINK_PREDICATE_SQL`, and returns nothing for an id that is not a tactic.
This spec reuses that constant rather than writing the predicate a second time.

---

## 2. Decisions this spec makes

**WTP-D1 — storage does not change.** The link stays in `weekly_tactic_id`.
Writing `parent_id` as well would be undone on the next launch by
`_move_week_links_off_parent_id`, and would re-couple the two columns that
migration exists to keep apart. "Becomes its parent" is therefore implemented
in the *readers*: the tactic is the parent because every reader of parenthood
says so, not because a second column repeats the link.

**WTP-D2 — one object-level authority: `parent_of`.** A new predicate beside
`tactic_of`, in `weekly_tactic.py`:

```
parent_of(item) = item.parent_id  if set
                  else tactic_of(item)    # the weekly_tactic_id, if any
                  else None
```

`parent_id` wins when both are set. Every reader in §1.3 answers from this one
definition. This is the shape AWA-A3 asked for at the object level; the SQL
level already has `LINK_PREDICATE_SQL`.

**WTP-D3 — one item, one place in the tree.** A consequence of WTP-D2 and the
reason `parent_id` wins: an item that is both a subtask of item X and week-filed
to tactic T is shown under **X**, not under T, and not under both. Nesting it
under both would list the same work twice in one tree and make the `(N sub)`
counts not sum. Its editor `Parent:` line names X for the same reason.

**WTP-D4 — the panel reader stays wider than the tree reader, on purpose.**
`get_action_items_for_weekly_tactic` keeps answering "what work sits under this
week" and still lists the item from WTP-D3; `get_children` answers "what hangs
directly off this record". These are two different questions and the difference
is now stated in one place, at `LINK_PREDICATE_SQL`, instead of being
rediscovered. A test asserts they disagree **only** in that case (WTP-M2.4).

**WTP-D5 — `tactic_of` is not touched.** WT-INV6 depends on it reading one
column. `parent_of` is a new reader built on it, and adds no row to what the
re-filing cascade will modify. Nothing in this spec changes which items the
cascade touches.

**WTP-D6 — a dangling link must not hide an item.** `get_root_items` stops
listing week-filed items as roots, but only when their tactic **still exists**.
An item whose `weekly_tactic_id` names a row that is not there keeps appearing
as a root, so it stays reachable instead of vanishing from the only tree view
(P2 — surface, never silently drop).

**Corrected 2026-11-08:** this decision first called the guard load-bearing
because "the live databases already contain this state". They do not — the
column's `ON DELETE SET NULL` prevents it (§1.3). The guard is **defensive**:
the pragma is per connection, so an unresolvable value is reachable from a
client that does not set it, and the cost of keeping the guard is one
`NOT EXISTS` against the alternative of hiding a row. Kept on that basis.
WTP-M3.2 must therefore seed the state with the pragma off; with it on there is
nothing to test, and the first version of that test proved it by passing with
the guard removed (§6).

**WTP-D7 — the delete cascade is confirmed by count, not silently widened.**
`delete_weekly_action_item` starts deleting `weekly_tactic_id` children too.
That turns a delete that used to leave a week's items behind as unparented
roots into one that *destroys* them — 49 rows on the main database as counted
on 2026-11-08 — so the confirmation stops saying "and related action items" and
names the number (WTP-M5.2). The Item Editor's own guard (WTP-M5.1) refuses the delete
outright, as it already does for any parent with children — the two paths keep
their existing, different answers to "delete a parent", and this spec does not
reconcile them.

**WTP-D8 — rollup is a count and a confirmation, not a status rule.** A tactic
with open children can still be completed; it asks first. Completion does not
cascade to children, and a child completing does not complete the tactic.
Anything stronger would change what WT-M5.A means for a week's items, and was
not asked for.

---

## 3. Acceptance criteria → tests

New test file: `tests/test_weekly_tactic_parent.py`, unless named otherwise.
Every `DatabaseManager` in it takes an explicit `tmp_path` database.

### WTP-M1 — `parent_of`, the one object-level authority

| ID | Criterion | Test |
|---|---|---|
| WTP-M1.1 | `parent_of(item)` returns `parent_id` when it is set and `weekly_tactic_id` is not. | `test_wtpm11_parent_id_alone` |
| WTP-M1.2 | It returns the `weekly_tactic_id` when that is set and `parent_id` is not. | `test_wtpm12_tactic_alone` |
| WTP-M1.3 | With both set it returns `parent_id` (WTP-D3). | `test_wtpm13_parent_id_wins_over_tactic` |
| WTP-M1.4 | It returns None for both columns empty, and treats `''` as empty — the same test `tactic_of` applies. | `test_wtpm14_empty_string_is_no_parent` |
| WTP-M1.5 | It returns None for `item is None`, like `tactic_of`. | `test_wtpm15_none_item` |
| WTP-M1.6 | `tactic_of` still reads `weekly_tactic_id` alone (WTP-D5): an item with `parent_id` pointing at a week row and no `weekly_tactic_id` is still not week-filed. | `test_wtpm16_tactic_of_unchanged` |
| WTP-M1.7 | A week row has no parent: `parent_of` returns None for `item_type='week'`, whatever its columns hold. **Added 2026-11-08, during implementation** — not in the approved spec. Needed for WTP-M2.4 to be satisfiable: `LINK_PREDICATE_SQL` excludes week rows, so had `parent_of` called a week row a child, the object and SQL definitions would disagree, which is the AWA-A3 failure this spec exists to avoid. | `test_wtpm17_a_week_row_has_no_parent` |

### WTP-M2 — `get_children` and `get_subtree`

| ID | Criterion | Test |
|---|---|---|
| WTP-M2.1 | `get_children(<week row id>)` returns the items whose `weekly_tactic_id` names it. | `test_wtpm21_tactic_children_by_tactic_column` |
| WTP-M2.2 | It still returns a `parent_id`-only child of that tactic (the AWA-A1 shape), exactly once. | `test_wtpm22_parent_id_only_child_returned_once` |
| WTP-M2.3 | It does **not** return a week-filed item whose `parent_id` names another item (WTP-D3); that item is returned by `get_children(<that item>)` instead. | `test_wtpm23_subtask_stays_under_its_subtask_parent` |
| WTP-M2.4 | For every row in a fixture holding all four link shapes, `get_children` agrees with `parent_of` — the SQL and object readers return the same tree — and differs from `get_action_items_for_weekly_tactic` only on the WTP-D3 row. | `test_wtpm24_sql_and_object_readers_agree` |
| WTP-M2.5 | `get_children(<ordinary item>)` is unchanged: `parent_id` children only, and never a week row. | `test_wtpm25_ordinary_parent_unchanged` |
| WTP-M2.6 | `get_children` never returns an `item_type='week'` row, so a nested tactic is not a child. | `test_wtpm26_week_rows_are_never_children` |
| WTP-M2.7 | `get_subtree(<week row id>)` reaches a week-filed item's own `parent_id` subtasks, breadth-first. | `test_wtpm27_subtree_through_a_tactic` |
| WTP-M2.8 | The predicate SQL is still written exactly once in `src/getmoredone` — `LINK_PREDICATE_SQL` — after this change. | existing `tests/test_ape_week_actions.py::test_awam23_one_home_for_the_link_predicate` |

### WTP-M3 — roots, and the tree

| ID | Criterion | Test |
|---|---|---|
| WTP-M3.1 | `get_root_items()` does not return an item whose `weekly_tactic_id` names an existing week row. | `test_wtpm31_week_filed_items_are_not_roots` |
| WTP-M3.2 | It **does** return an item whose `weekly_tactic_id` names a row that no longer exists (WTP-D6). | `test_wtpm32_dangling_link_stays_a_root` |
| WTP-M3.3 | It still returns the week rows themselves, and ordinary parentless items. | `test_wtpm33_tactics_and_plain_items_are_still_roots` |
| WTP-M3.4 | `status_filter` still applies, and applies to the new exclusion too. | `test_wtpm34_status_filter_unchanged` |
| WTP-M3.5 | The Hierarchical screen renders a week-filed item at indent level 1 under its tactic, and once. | `test_wtpm35_tree_nests_week_filed_items` |
| WTP-M3.6 | The tactic's row shows `(N sub)` counting its week-filed children. | `test_wtpm36_tactic_row_shows_child_count` |

### WTP-M4 — the Item Editor's parent surfaces

| ID | Criterion | Test |
|---|---|---|
| WTP-M4.1 | Opening a week-filed item shows `Parent: <tactic title>`. | `test_wtpm41_editor_shows_tactic_as_parent` |
| WTP-M4.2 | An item with both links shows its `parent_id` parent, not the tactic (WTP-D3). | `test_wtpm42_editor_shows_nearer_parent` |
| WTP-M4.3 | The `Parent:` line carries a **View Parent** button that opens that parent in a second editor. `view_parent_item` (`item_editor.py:1652`) exists today and is bound to nothing — see §7. | `test_wtpm43_view_parent_button_opens_the_parent` |
| WTP-M4.4 | The Organise tab's Weekly Tactic row (WT-M6.A.2) is unchanged — the parent line is additional, not a replacement. | existing `tests/test_item_editor_weekly_tactic_ui.py::test_wt_m6a2_org_tab_shows_current_tactic_or_none` |
| WTP-M4.5 | The Hierarchy dialog shows the tactic under `PARENT ITEM` for a week-filed item. | `test_wtpm45_hierarchy_dialog_shows_the_tactic_as_parent` |
| WTP-M4.6 | It shows the week-filed items under `CHILD ITEMS` when opened on a tactic. | `test_wtpm46_hierarchy_dialog_lists_tactic_children` |

### WTP-M5 — delete

| ID | Criterion | Test |
|---|---|---|
| WTP-M5.1 | The Item Editor's delete of a tactic with week-filed items refuses, naming the count — the existing guard, now reached. | `test_wtpm51_editor_refuses_to_delete_a_tactic_with_children` |
| WTP-M5.2 | `delete_weekly_row`'s confirmation names how many Action Items will go with the tactic, and a refused confirmation deletes nothing. | `test_wtpm52_confirmation_names_the_child_count` |
| WTP-M5.3 | `delete_weekly_action_item` deletes `weekly_tactic_id` children as well as `parent_id` ones, leaving no row pointing at the deleted tactic. | `test_wtpm53_cascade_covers_both_link_columns` |
| WTP-M5.4 | It deletes the week-filed items' own `parent_id` subtasks too, so the cascade leaves no orphan one level down. | `test_wtpm54_cascade_reaches_grandchildren` |
| WTP-M5.5 | It still returns False, and deletes nothing, for an id that is not a week row. | existing `tests/test_vps_hub_crud.py` + `test_wtpm55_non_tactic_id_deletes_nothing` |
| WTP-M5.6 | `tests/test_vps_hub_crud.py::test_delete_weekly_action_item_removes_children` is extended, not rewritten, to cover both link shapes. Reason on the record: **the behaviour changed intentionally** (WTP-D7). | that test |

### WTP-M6 — completion rollup (new behaviour, not parity)

| ID | Criterion | Test |
|---|---|---|
| WTP-M6.1 | Completing a Weekly Tactic that has open children asks for confirmation naming the open count; declining completes nothing and says nothing. | `test_wtpm61_completing_a_tactic_with_open_children_asks` |
| WTP-M6.2 | Accepting completes the tactic only — no child's status changes. | `test_wtpm62_completion_does_not_cascade` |
| WTP-M6.3 | A tactic with no open children completes with no prompt. | `test_wtpm63_no_prompt_when_nothing_is_open` |
| WTP-M6.4 | The Weekly Tactic row in the APE Week Assignment right panel shows `n/m done` from its children. | `test_wtpm64_week_assignment_row_shows_progress`, plus `test_wtpm64_progress_counts_come_from_one_helper` for the helper and `test_wtpm64_a_tactic_with_nothing_under_it_shows_a_dash` for the empty case |
| WTP-M6.5 | The Week Actions tab's left tactic list shows the same count, from the same helper — one home, not two renderings. | `test_wtpm65_week_actions_list_shows_progress` |
| WTP-M6.6 | Completing a child changes that count, and `complete_action_item`'s WT-M5.A re-file still moves the item to the week it was completed in — so the count is read after the re-file, not before. | `test_wtpm66_count_follows_the_wt_m5a_refile` |

### Not code-testable

- **That the tree now reads as the user's plan.** The nesting, indent and
  count are asserted; whether a week's work is legible under its tactic is a
  look. **Human review proposal:** on the Hierarchical screen, with the main
  database, confirm each tactic shows its week's items nested beneath it and no
  item appears twice. Record it in the handoff note.
- **WTP-M5.2's wording.** The test asserts the count is in the string; that it
  reads as a warning rather than a statistic is a judgement.

---

## 4. Implementation order

1. **WTP-M1** — `parent_of` in `weekly_tactic.py`, beside `tactic_of`. No
   caller yet. Tests first.
2. **WTP-M2** — `get_children` built from `LINK_PREDICATE_SQL` plus the
   WTP-D3 restriction; `get_subtree` inherits it. WTP-M2.4 is the criterion
   that keeps the SQL and object readers from drifting, and is written here.
3. **WTP-M3.1–M3.4** — `get_root_items`, with the WTP-D6 existence join.
4. **WTP-M3.5–M3.6** — the Hierarchical screen, which needs 2 and 3 and
   changes no code of its own if they are right. If it does need a change,
   that is a finding about 2 or 3.
5. **WTP-M4** — the editor label, the View Parent binding, the Hierarchy
   dialog. Needs 1.
6. **WTP-M5** — the cascade and both confirmations. Needs 1 and 2. Last of
   the parity work because it is the only destructive change.
7. **WTP-M6** — the rollup. Depends on 2 for the counts. Separable: it is the
   one item here that is new behaviour, and can be dropped without touching
   1–6.

Dependencies: 2 → 3 → 4; 1 → 5; 1 → 6; 2 → 7.

### Fix→test map (highest impact first)

| Change | Most likely to regress | Test written first |
|---|---|---|
| `get_root_items` exclusion | an item vanishing from the only tree view when its tactic is gone | `test_wtpm32_dangling_link_stays_a_root` — a dirty-state fixture (P8): a database that already holds the 49-item shape from §1.3 |
| cascade widened | destroying work a delete used to leave alone | `test_wtpm53_cascade_covers_both_link_columns`, then `test_wtpm52_confirmation_names_the_child_count` |
| `get_children` widened | the same item listed twice, or under two parents | `test_wtpm24_sql_and_object_readers_agree` — the adversarial case (P7): all four link shapes in one fixture |
| `parent_of` | quietly widening what the re-filing cascade touches | `test_wtpm16_tactic_of_unchanged` |

Mutation: for each test above, delete or invert the line it names, confirm red,
restore with the verbatim original.

---

## 5. Risks

- **The cascade is the only destructive change in this batch.** Before WTP-M5
  a tactic delete left its `weekly_tactic_id` items in place, with the link
  nulled by the column's `ON DELETE SET NULL`; after it, it deletes them. On
  the main database that is 49 rows that change from surviving to being
  deletable in one confirmed click. WTP-M5.1 means the Item Editor path
  refuses instead, so the destructive path is the VSP screen's, which is the
  one that already says "and related action items".
- **`get_root_items` has one caller** (`hierarchical.py:155`), so the
  exclusion is contained. If a later screen calls it expecting a flat list of
  parentless rows, it will get a narrower one.
- **WTP-M6 has no precedent to match.** No parent in this app rolls up today,
  so M6.4/M6.5 invent a surface. If the count reads as clutter on the tactic
  rows, dropping WTP-M6 leaves 1–6 intact.
- **AWA-A4 is adjacent to WTP-M6.5.** The Week Actions panel's rows carry
  Today's shared pin; adding a count to those rows touches the same renderer
  that bug lives in, without fixing it.

---

## 6. Status report

Recorded 2026-11-08, after implementation. Commits: `e465f79` (this spec),
`8c65080` and `43d8a43` (`src/`), `869cbd6`, `a0fb2d3` and `91bfd8d` (tests),
then the screen work and its tests. Nothing is pushed. Every test named below
is in `tests/test_weekly_tactic_parent.py` unless another file is given.

**Summary: all 38 criteria `done`** — the 35 in §3, plus WTP-M1.7 and the two
extra cases WTP-M5.2 needed. Nothing is `partial` and nothing is outstanding.

Three of them — WTP-M5.2, WTP-M6.4's rendering and WTP-M6.5 — were held back
mid-batch because `screens/weekly_items.py` and `screens/week_actions.py`
carried 327 uncommitted lines from a concurrent session. They were filed in
`BACKLOG.md` as WTP-A1 to WTP-A3, then built when that session committed and
both files came free; the backlog entries are withdrawn and the one entry under
WTP there now is an adjacent issue found while building WTP-M6.4.

### WTP-M1 — `parent_of`

| ID | Status | Proof |
|---|---|---|
| WTP-M1.1 | done | `src/getmoredone/weekly_tactic.py` `parent_of` · `test_wtpm11_parent_id_alone` |
| WTP-M1.2 | done | same · `test_wtpm12_tactic_alone` |
| WTP-M1.3 | done | same · `test_wtpm13_parent_id_wins_over_tactic` |
| WTP-M1.4 | done | same · `test_wtpm14_empty_string_is_no_parent` |
| WTP-M1.5 | done | same · `test_wtpm15_none_item` |
| WTP-M1.6 | done | `tactic_of` unchanged · `test_wtpm16_tactic_of_unchanged` (mutation-gated: making `tactic_of` read both columns turns it red) |
| WTP-M1.7 | done | `parent_of`'s week-row guard · `test_wtpm17_a_week_row_has_no_parent` |

### WTP-M2 — `get_children` and `get_subtree`

| ID | Status | Proof |
|---|---|---|
| WTP-M2.1 | done | `src/getmoredone/db_manager.py` `get_children` · `test_wtpm21_tactic_children_by_tactic_column` |
| WTP-M2.2 | done | same · `test_wtpm22_parent_id_only_child_returned_once` |
| WTP-M2.3 | done | same, the `COALESCE(parent_id, '') = '' OR parent_id = ?` restriction · `test_wtpm23_subtask_stays_under_its_subtask_parent` |
| WTP-M2.4 | done | `test_wtpm24_sql_and_object_readers_agree` over all six link shapes, plus `test_wtpm24_the_panel_reader_stays_wider` for the WTP-D4 difference (asserted to be exactly one row). Mutation-gated: dropping the WTP-D3 restriction turns it red. |
| WTP-M2.5 | done | `get_children`'s else-branch · `test_wtpm25_ordinary_parent_unchanged` |
| WTP-M2.6 | done | same branch's `item_type != 'week'` test · `test_wtpm26_week_rows_are_never_children` |
| WTP-M2.7 | done | `get_subtree` unchanged, inherits the new answer · `test_wtpm27_subtree_through_a_tactic` |
| WTP-M2.8 | done | `get_children` imports `LINK_PREDICATE_SQL` rather than copying it · `tests/test_ape_week_actions.py::test_awam23_one_home_for_the_link_predicate`, which now also asserts `db_manager.LINK_PREDICATE_SQL is LINK_PREDICATE_SQL` — the fourth caller |

### WTP-M3 — roots, and the tree

| ID | Status | Proof |
|---|---|---|
| WTP-M3.1 | done | `db_manager.py` `get_root_items` · `test_wtpm31_week_filed_items_are_not_roots` |
| WTP-M3.2 | done | the `NOT EXISTS` guard · `test_wtpm32_dangling_link_stays_a_root`. **This test was vacuous when first written** and is the reason §1.3/WTP-D6/WTP-D7 are corrected above: it deleted the tactic with foreign keys on, the column's `ON DELETE SET NULL` nulled the link, and the row was a root for a reason the test was not about — it stayed green with the guard removed. It now seeds with `PRAGMA foreign_keys = OFF` and asserts the seed actually dangles before reading roots. Found by the mutation gate, not by review. |
| WTP-M3.3 | done | `get_root_items` · `test_wtpm33_tactics_and_plain_items_are_still_roots` |
| WTP-M3.4 | done | same · `test_wtpm34_status_filter_unchanged` |
| WTP-M3.5 | done | `screens/hierarchical.py` **unchanged**, as §8 expected · `test_wtpm35_tree_nests_week_filed_items` (indent read back from the row's `padx`) |
| WTP-M3.6 | done | also unchanged · `test_wtpm36_tactic_row_shows_child_count` |

### WTP-M4 — the Item Editor's parent surfaces

| ID | Status | Proof |
|---|---|---|
| WTP-M4.1 | done | `screens/item_editor.py`, the `parent_of`-driven parent frame · `test_wtpm41_editor_shows_tactic_as_parent` |
| WTP-M4.2 | done | same · `test_wtpm42_editor_shows_nearer_parent` |
| WTP-M4.3 | done | `self.view_parent_button` bound to `view_parent_item` · `test_wtpm43_view_parent_button_opens_the_parent` |
| WTP-M4.4 | done | the Organise tab untouched · existing `tests/test_item_editor_weekly_tactic_ui.py::test_wt_m6a2_org_tab_shows_current_tactic_or_none` |
| WTP-M4.5 | done | `screens/item_editor_dialogs.py` `ShowRelatedDialog.refresh` · `test_wtpm45_hierarchy_dialog_shows_the_tactic_as_parent`. This test found a **second reader of parenthood** in the same method: the "no related items" branch still asked about `current_item.parent_id`, so a week-filed item with no children of its own rendered "No related items found" directly beneath the `PARENT ITEM` section just drawn for it. Both readers now go through `parent_of`. |
| WTP-M4.6 | done | same method · `test_wtpm46_hierarchy_dialog_lists_tactic_children` |

### WTP-M5 — delete

| ID | Status | Proof |
|---|---|---|
| WTP-M5.1 | done | `item_editor.py`'s existing guard, now reached via `get_children` · `test_wtpm51_editor_refuses_to_delete_a_tactic_with_children` |
| WTP-M5.2 | done | `screens/weekly_items.py` `delete_weekly_row`, reading `children_to_delete_with_weekly_tactic` — the same list the cascade deletes, so the number shown is read off the work that will be done (P6) · `test_wtpm52_confirmation_names_the_child_count`, and the refused confirmation is asserted against the database rather than a call log. Two cases beyond the criterion, both mutation-gated: `test_wtpm52_confirmation_says_so_when_nothing_is_filed` (P7 — a message that always names a number would warn about "0 Action Items" for a tactic with nothing under it) and `test_wtpm52_one_item_is_singular`. |
| WTP-M5.3 | done | `vps_manager.py` `delete_weekly_action_item` + `children_to_delete_with_weekly_tactic` · `test_wtpm53_cascade_covers_both_link_columns` (mutation-gated) |
| WTP-M5.4 | done | the same subtree walk · `test_wtpm54_cascade_reaches_grandchildren` |
| WTP-M5.5 | done | the new `if not self.db_manager.is_weekly_tactic(...): return False` guard · `test_wtpm55_non_tactic_id_deletes_nothing` (mutation-gated). This test found a **pre-existing latent fault**: the `DELETE … WHERE parent_id = ?` ran before the `item_type` test, so passing an ordinary item's id deleted that item's subtasks and then returned False, reporting that nothing had been deleted. Latent because `weekly_items.py:598` only ever passes a week row. |
| WTP-M5.6 | done | `tests/test_vps_hub_crud.py::test_delete_weekly_action_item_removes_children`, extended (commit `91bfd8d`), with the reason on the record in the commit message: (b) the behaviour changed intentionally |

### WTP-M6 — completion rollup

| ID | Status | Proof |
|---|---|---|
| WTP-M6.1 | done | `item_editor.py` `_confirm_tactic_completion`, called from `complete_item` · `test_wtpm61_completing_a_tactic_with_open_children_asks` (mutation-gated) |
| WTP-M6.2 | done | the prompt returns a bool and nothing else changes status · `test_wtpm62_completion_does_not_cascade` |
| WTP-M6.3 | done | the same method's early return · `test_wtpm63_no_prompt_when_nothing_is_open` |
| WTP-M6.4 | done | `vps_manager.count_open_children_for_weekly_tactic` · `test_wtpm64_progress_counts_come_from_one_helper` asserts its `(done, total)` and that the number agrees with the `(N sub)` count the tree renders. The rendering is a Done column on the row · `test_wtpm64_week_assignment_row_shows_progress` (reads `1/3` off the cell) and `test_wtpm64_a_tactic_with_nothing_under_it_shows_a_dash` (`—`, not `0/0`, which reads as a count that failed). Both mutation-gated. The panel took a column set of its own, `WEEK_ASSIGNMENT_RIGHT_COLUMNS`, rather than a column added to `APE_RIGHT_COLUMNS`: the other two APE right panels list Annual Plan Elements, which have no children, so a Done column there could only ever read `—`. |
| WTP-M6.5 | done | `screens/week_actions.py` `_render_tactics`, reading the same helper · `test_wtpm65_week_actions_list_shows_progress`, which asserts the rendered cell **and** the helper's own answer — a rendering that hard-coded the string fails the first, a helper that drifted fails the second. Mutation-gated. |
| WTP-M6.6 | done | `count_open_children_for_weekly_tactic` reads through `get_children`, so it is read after the re-file · `test_wtpm66_count_follows_the_wt_m5a_refile` |

### The two "not code-testable" items

- **That the tree reads as the user's plan** — **not done**, as foreseen. The
  human review proposal stands: it is the checklist in
  `docs/changes/2026-11-08-weekly-tactic-as-parent.md`. Nobody has opened the
  Hierarchical screen against the main database.
- **WTP-M5.2's wording** — **not done**, as foreseen. The test asserts the
  count, the plural and "cannot be undone" are in the string. Whether
  *"This will also delete 3 Action Items filed under it. This cannot be
  undone."* reads as a warning rather than a statistic is a judgement, and it
  is step 6 of the same checklist.

### Verification

| Run | Result |
|---|---|
| `pytest tests/test_weekly_tactic_parent.py -q` | 41 passed |
| `pytest tests/test_unified_panel_design.py tests/test_ape_week_actions.py -q` | 112 passed |
| the 14 touched-area files, before the screen work | 362 passed |
| `pytest tests/test_ci_contract.py -q` | 82 passed, 1 skipped — the mapped-window count is still 22 |
| `pytest tests/test_vps_hub_crud.py -q` | 11 passed |
| mutation gate, 8 mutations (M1-M6 readers) | all 8 killed; every file restored byte for byte |
| mutation gate, 7 mutations (the three screen criteria) | all 7 killed; every file restored byte for byte |

All runs used `GETMOREDONE_NO_MAPPED_WINDOWS=1`. The full suite was **not** run
locally — four sessions were writing in this checkout — and CI runs it on push.
A cold review pass has **not** been run; the project's sweep budget requires at
least one before this is pushed.

---

## 7. Adjacent issues found, not fixed

Per the standing rule, these were found while reading the surrounding code.
None is a prerequisite.

- **AWA-A1 is still open, and this spec is built to tolerate it.**
  `weekly_items.py:560` still writes `parent_id` for the APE Week Assignment
  tab's *Add Action Item*. WTP-M2.2 and WTP-M5.3 both cover that shape, so the
  parity work is correct with or without the fix. **Recommendation:** fix it
  separately, as `BACKLOG.md:85` already proposes; folding it in here would mix
  a storage fix into a reader change and make WTP-M2.2's test unable to fail.
- **`view_parent_item` (`item_editor.py:1652`) is dead code.** It builds a
  second `ItemEditorDialog` on a parent id and no widget calls it. WTP-M4.3
  binds it rather than writing a new handler — so the dead code becomes live
  code, which is a behaviour change to the existing `parent_id` case as well:
  a subtask's editor gains a button it has never had. Called out because that
  is beyond "a weekly tactic acts like a parent", and is the user's call.
  **Recommendation:** keep it in scope; the alternative is a tactic parent line
  with a button and a subtask parent line without one.
- **No test enforces `docs/DOCUMENTATION_INDEX.md`.** The repo keeps the index
  and the global standard asks for a test that every document is listed in it.
  Nothing asserts it; `grep -rn DOCUMENTATION_INDEX tests/` is empty, and the
  index's own footer still reads "up to date as of 2026-01-24". This spec adds
  its entries by hand. **Recommendation:** a separate meta test, not this batch.
- **The two delete paths disagree about deleting a parent.** The Item Editor
  refuses (`item_editor.py:1499`); the VSP screen cascades
  (`vps_manager.py:1267`). WTP-M5 makes both tactic-aware and leaves them
  disagreeing, because reconciling them changes ordinary subtask deletion too.

---

## 8. Files this will touch

| File | Change |
|---|---|
| `src/getmoredone/weekly_tactic.py` | **WTP-M1** — `parent_of`, beside `tactic_of` |
| `src/getmoredone/db_manager.py` | **WTP-M2, M3** — `get_children`, `get_root_items` |
| `src/getmoredone/screens/hierarchical.py` | **WTP-M3.5/M3.6** — expected: no change |
| `src/getmoredone/screens/item_editor.py` | **WTP-M4.1–M4.3** — parent line + View Parent; **WTP-M6.1–M6.3** — the complete prompt |
| `src/getmoredone/screens/item_editor_dialogs.py` | **WTP-M4.5/M4.6** — `PARENT ITEM` / `CHILD ITEMS` |
| `src/getmoredone/vps_manager.py` | **WTP-M5.3/M5.4** — the cascade; **WTP-M6.4/M6.5** — one progress helper |
| `src/getmoredone/screens/weekly_items.py` | **WTP-M5.2** — the confirmation; **WTP-M6.4** — the count on the row |
| `src/getmoredone/screens/week_actions.py` | **WTP-M6.5** — the count on the tactic list |
| `src/getmoredone/screens/chip_table.py` | **not foreseen** — `WEEK_ASSIGNMENT_RIGHT_COLUMNS`, and a Done column on `WEEK_ACTIONS_LEFT_COLUMNS`. WTP-M6.4/M6.5 say "shows `n/m done`" and both panels are chip tables, so the count has to be a column; the column sets live here |
| `tests/test_unified_panel_design.py` | **not foreseen** — five tests pin those two sets exactly, and one more drives the APE Week Assignment panel through a double that now needs two more methods. Reason on the record: (b) the behaviour changed intentionally |
| `tests/test_weekly_tactic_parent.py` | **new** — WTP-M1 … WTP-M6 |
| `tests/test_vps_hub_crud.py` | **WTP-M5.6** — extended for both link shapes |
| `docs/DOCUMENTATION_INDEX.md` | this spec, and the handoff note |
| `docs/changes/2026-11-08-weekly-tactic-as-parent.md` | **new** — handoff note |

Test changes are committed separately from `src/` changes.
