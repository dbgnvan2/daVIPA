# QA gate — WTP / PLC / UPD / PD (range 3f705b4..56c1dc0)

RANGE: 3f705b4..56c1dc0 (42 commits, 65 files, +12207/−1534)
COMMITS: e465f79 8c65080 869cbd6 43d8a43 a0fb2d3 91bfd8d ed17eaa 4390389 a0d7f7b (WTP);
         108e4e9 845c5fa eeb47cd 8aa02a6 3c59442 1a75086 ed61d9a 1ea8f24 ce2eb6a 3984e6f bbae5cb (PLC);
         4c4d1df 9339d4a 79a0003 504d9f6 1683c83 c2ea2ef 623cdef 4651f8b b61a4f8 2b8704d e436179 5294416 be19331 ee2f7c8 61d690d 5322bcf 9db67e4 (UPD/VSP);
         ed2e8be c7b9c75 8aa3a45 (PD)
APPLICABLE: P1–P42 (~/.claude/standards/learnings.md), repo CLAUDE.md, AGENTS.md, LEARNINGS.md
CHECKED: failure-pattern sweep + test-quality + theme rule, full committed range via `git diff 3f705b4..56c1dc0`
NOT COVERED: a run of the full suite (explicitly disallowed this session); the PD-M13.4 walk (no test can build a visible window — see below)
VERDICT: REJECTED

---

## Scope and method

This is a REVIEW ONLY. Nothing in the working tree was touched; the 24 tracked
files belonging to two concurrent sessions were left alone. Only the committed
range was read, materialized to /tmp/sweep.diff (15,844 lines) and inspected
commit-by-commit plus file-by-file at HEAD.

Weight went to the WTP batch, which had never had an independent pass. PLC, UPD
and PD each had at least one prior pass, so they were treated as a second pass
and read more lightly. No test file was executed (full suite disallowed; the
specific files for the one finding below would exercise Tk and were not run).

## The WTP batch (primary)

The core is sound. The one definition of parenthood is genuinely single-sourced:
`weekly_tactic.parent_of` (object reader) and `DatabaseManager.get_children`
(SQL reader) are held to the same answer by
`test_wtpm24_sql_and_object_readers_agree`, which walks *every* link shape in
one database — tactic-only, parent_id-only, both-same, both-split, plain
subtask, unlinked — including the two "looks right but is wrong" shapes (P7).

What was done right, and held:

- P6 (status without artifact): the delete confirmation reads
  `children_to_delete_with_weekly_tactic` — the *same* breadth-first walk the
  cascade deletes — rather than a second count, so the number shown cannot drift
  from what gets removed. The completion prompt reads `get_children` directly.
- P8 (dirty state): `test_wtpm32_dangling_link_stays_a_root` seeds a dangling
  `weekly_tactic_id` with `PRAGMA foreign_keys = OFF` because with it on the FK
  nulls the link and there is nothing to test — the mutation gate caught an
  earlier version that passed for the wrong reason. `test_wtpm26` seeds a nested
  tactic row the reader must not depend on a migration to have cleared.
- P2 (silent drop): `get_root_items`'s `NOT EXISTS` guard keeps a week-filed
  item whose tactic row is gone visible at the top level instead of dropping it
  from the only tree view. The docstring honestly records that the state is
  only reachable from a connection without the pragma, not from app deletes.
- P7 (gameable proxy): `priority_levels.priority_level` is the anti-gameable
  case done right — thresholds read from `PriorityFactors`, not literal 20/10,
  and `test_plcm14_a_big_score_is_not_a_critical_level` pins that a 400-scoring
  Medium/Medium item is *not* Any Critical.
- Test quality: no `> N` floors found anywhere in the new files; counts are
  exact (`== (1, 3)`, `== ["(2 sub)"]`, `== {one.id, two.id}`). Source checks
  go through `tests/source_asserts.py`, which walks the AST rather than matching
  substrings, and the helpers themselves are tested for the no-op directions
  (`tests/test_source_asserts.py`). No assert-free bodies, no `return` in tests.
- Theme rule: grep over the changed UI files for hard-coded hex/named colours
  found only the two centralized defaults `#DCFCE7`/`#FEF3C7` (app_settings
  dataclass + `theme.priority_level_fill_colors()`), held to each other by
  `test_plcm22_settings_defaults_match_the_theme_table`, plus `fg_color="transparent"`
  and theme-token reads (`palette["success_strong"]`, `semantic_colors()["muted_text"]`).
  No hard-coded widget colour was introduced.

## Findings

### F1 — MEDIUM — P25 — the completion confirmation is wired on one surface of seven

`_confirm_tactic_completion` (the WTP-M6 "completing a tactic with open children
asks first" guard) exists only in `ItemEditorDialog.complete_item`
(`src/getmoredone/screens/item_editor.py:1580`). `DatabaseManager.complete_action_item`
is called directly, with no confirmation, from:

- `screens/today.py:725` — the checkbox on each row (`today.py:552`), and a
  Weekly Tactic row *does* render there (`today.py:557`, the "WT" badge)
- `screens/all_items.py:451`
- `screens/upcoming.py:523`
- `screens/hierarchical.py:356`
- `screens/project_boards.py:1680`
- `screens/timer_window.py:1163` and `:1182`

All of those surfaces list week rows (all_items/upcoming/completed/today all
draw the "WT" badge), so completing a Weekly Tactic from the Today checkbox, the
Hierarchical tree, or the timer marks it done and leaves its open children open
*without the warning the spec requires*. WTP-M6 says "completing a Weekly Tactic
with open children asks first, naming the count, and completes nothing if
declined" — that is met only from the editor.

The harm is a missing warning, not lost work: completion deliberately does not
cascade (WTP-D8), so the data is the same either way. That keeps this at medium
rather than high, but it is exactly the P25 shape this repo's LEARNINGS.md calls
out as live, and it is a spec criterion only partially met on the screens a user
actually checks items off from.

Suggested fix direction (for the next build batch, not this review): move the
guard to the shared completion path or call it from each surface that can hold a
week row, and add one test per surface that intercepts the boundary and asserts
the prompt fires for a tactic-with-open-children (the editor test
`test_wtpm61` already proves the pattern for one surface).

### F2 — LOW — process — cross-batch contamination in a "feat(wtp)" commit

`8c65080` ("feat(wtp): a Weekly Tactic is the parent … M1–M3") carries the WTP
hunks *and* unrelated Calendar Export changes to `db_manager.py` —
`calendar_event_id` added to the time_blocks INSERT/UPDATE/read paths and the
new `set_block_calendar_event_id`. The CE work is not one of the four batches in
this range, so those hunks were reviewed here only as WTP commit content, never
as CE work. The read path is defensively written (falls back to `None` on a
missing column), so no crash on a pre-migration DB, but the commit label
understates its contents and the CE hunks have no review of their own yet.

This is the contamination class CLAUDE.md already documents (four concurrent
batches sharing db_manager.py and the three doc files), so it is a process
observation, not a new code defect. Flag it for the CE batch's own sweep.

## Second-pass notes (PLC / UPD / PD)

No new medium-or-higher findings on the second pass.

- PLC: `priority_levels.py` is a clean single-source for level/tint logic;
  `color_contrast.normalize_hex_color` is stricter than Tk and the claim is
  checked against real Tk by `build_priority_colors_section.py` (subprocess,
  withdrawn root, and it raises if the save path reaches the real settings file
  or a running app — P28/P34 guarded). The two-homes colour default is held by
  `test_plcm22`.
- PD: `ed2e8be` (no modal on the drop path) is a careful fix — drop paths stop
  asking (`ask=False`) rather than hang, button paths keep the question wrapped
  in `try/except tk.TclError`, and the non-work-day note is one-shot and
  appended to all four status lines that can follow a non-work-day write. The
  deleted `widgets/confirm_dialog.py` was the thing that hung the app.
- PD-M13.4 (a walk over the running screen) is honestly recorded as NOT COVERED:
  no test in this suite can build a visible window, which is how both earlier
  remedies reached the user. This remains a genuine verification gap and belongs
  in the handoff note, not as a finding to fix in-loop.

## Verdict

REJECTED.

One medium finding (F1) — a spec criterion (WTP-M6) met on only one of the
completion surfaces, reachable from the Today checkbox and the Hierarchical
tree. Per the sweep budget in CLAUDE.md, a medium buys a fix, not another pass;
it must be addressed before this range is pushed. No high-severity findings.
The WTP core (parent_of / get_children / get_root_items / delete cascade /
progress counts) is otherwise clean, and the WTP test suite is the strongest
part of the change — exact counts, adversarial link-shape fixtures, and dirty
-state seeding where it matters.
