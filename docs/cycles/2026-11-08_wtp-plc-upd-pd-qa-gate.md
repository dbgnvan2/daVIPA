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

---

## Re-gate — range 56c1dc0..HEAD (F1 fix)

RANGE: 56c1dc0..HEAD (3 commits: 4b2ac93 fix, 3ee86c7 test, 1c7584d docs)
APPLICABLE: P5, P19, P25, P26, P28, P29, P31, P32 (per ~/.claude/standards/learnings.md and repo LEARNINGS.md)
CHECKED: the committed diff via `git diff 56c1dc0..HEAD` (not the working tree), the seven changed screens at HEAD, the shared guard, `complete_action_item`/`get_children`/`get_action_item` in db_manager.py, `count_open_children_for_weekly_tactic`, `Status`, the AST guard tests, and `tests/test_weekly_tactic_completion_surfaces.py` + `tests/test_weekly_tactic_parent.py` (run: 72 passed).
NOT COVERED: any window-on-screen walk (no test builds a visible window; the timer's accepting path and the full teardown remain unit-uncovered, as the handoff note honestly records).

VERDICT: APPROVED

### Is F1 actually fixed — yes

`grep complete_action_item` over all of `src/` returns exactly the seven
surfaces, and every one is guarded:

- today.py:732, all_items.py:458, upcoming.py:530, hierarchical.py:363,
  project_boards.py:1687, item_editor.py:1569 — each `complete_item` now opens
  with `if not confirm_weekly_tactic_completion(...): return`.
- timer_window.py:1176 and :1195 — both inside `finished_action`, both
  downstream of the single guard at :1147.

The only other matches are `db_manager.py:527` (the definition) and
`db_manager.py:589`/`completed.py:335` (`uncomplete_action_item`, a reopen
path — not a completion, so correctly unguarded). `weekly_items.py` and
`week_actions.py` have no completion action; the checkbox in weekly_items'
left panel is a row-selection BooleanVar, not a "mark done" control. No
bulk-complete or direct `status = COMPLETED` write exists in any screen. Seven
is the real denominator, and all seven ask.

`ItemEditorDialog._confirm_tactic_completion` is a genuine one-line delegation
(item_editor.py:1557-1560), and `test_wtpm67`'s `_drive_editor` binds the stub
to the *real* `ItemEditorDialog._confirm_tactic_completion`, so the delegation
itself is under test, not a stand-in.

### Timer placement — correct

The guard sits at timer_window.py:1147, after the `winfo_exists()` early return
and before the Next Action close, `_save_notes_to_item`, the note dialog, and
both completions. Declining returns at :1150 before any of those, so neither a
typed note nor a window is lost. The "window was closed while dialog was open"
branch (:1169-1183) is now only reachable *after* the guard returned True, so
it still completes correctly; a decline never reaches the dialog, so the branch
cannot fire after a refusal. For a non-tactic item, or a tactic with no open
children, the guard returns True immediately — the ordinary path is untouched.

### The two AST tests — exact set, and a real but mitigated weakness

`test_wtpm67_the_set_of_completion_call_sites_is_pinned` asserts
`_completion_call_sites() == EXPECTED_CALL_SITES` — an exact dict, not a floor.
It fails on an added site (the one-of-seven direction), a removed or renamed
site, or a changed per-function count. Verified the expected dict matches the
actual call sites line-for-line. It would fail when it should.

`test_wtpm67_every_completion_call_site_is_guarded` is name-presence, not
gating: it checks the function body *mentions*
`confirm_weekly_tactic_completion` or `_confirm_tactic_completion`, so it would
NOT red on "guard moved after the completion" or "result ignored". That is the
fragile class LEARNINGS warns about, but it is backstopped by
`test_wtpm67_a_declined_prompt_completes_nothing_on_any_surface`, which drives
each real screen method against a real DatabaseManager, intercepts `askyesno`
to return False, and asserts the row is still not completed — that test catches
both reordering and ignored-result. The AST pair is a second net, not the net.

### "Open children" semantics — correct, and consistent

The guard counts `get_children(item_id)` with `status != COMPLETED`. Against
WTP-M6.6: a child completed in a *different* week was already re-filed off this
tactic, so `get_children` no longer returns it (correctly not counted); a child
completed in the *same* week is still linked but filtered out; a still-open
child is counted and — because completion does not cascade (WTP-D8) — is
exactly what `complete_action_item` will leave open. The count names what the
save leaves open, which is what the question claims.

It also agrees with `count_open_children_for_weekly_tactic` (the Done column's
`(done, total)`, same `get_children` reader, same "only COMPLETED is done"
definition), so the prompt's count cannot disagree with the `n/m` beside the
tactic. Two things worth noting, both pre-existing and inherited verbatim from
the editor's original guard: `CANCELED` children count as "open" (status !=
COMPLETED) — consistent with the Done column, which also treats them as
not-done; and `get_children` is the narrower tree reader (WTP-D4), so a child
that is both a subtask and week-filed is excluded from the prompt — again the
same reader the Done column and `(N sub)` count use. Neither is a drift or a
regression.

### Findings (none medium or higher)

- LOW · test-quality · P19-corollary · `test_wtpm67_every_completion_call_site_is_guarded`
  asserts name presence, not that the guard's return gates the completion.
  Mitigated by the parametrized decline test (which asserts the real row stays
  open). A future edit that keeps the name but ignores the result would still
  be caught, just not by this test.
- LOW · test-quality · P31 · the call-site pin walks only
  `src/getmoredone/screens/*.py`, so a completion path added outside `screens/`
  (a CLI, a script) would escape both AST guards. No such path exists today
  (verified by grep over all of `src/`); the test's docstring states its scope
  honestly.
- LOW · style · item_editor.py:1557 keeps a function-local import of the guard
  to avoid touching another session's uncommitted hunk. Documented in the
  handoff note as a deliberate, temporary seam. Not a defect.

Re-reviewed the three filed lows and do not promote them: WTP-A2 (CE hunks in
a feat(wtp) commit) is process note only; WTP-A3 (upcoming.py's double
`notify_weekly_tactic_changes`) is a duplicate dialog with no data effect and
predates this range (the two lines are context, not additions, in this diff);
WTP-A4 is documentation.

### Verdict

APPROVED. F1 is fixed on all seven surfaces through one implementation, the
timer placement is correct (including the window-closed-during-dialog branch),
the call-site set is asserted exactly rather than as a floor, and the guard's
definition of "open children" is consistent with WTP-M6.6 and with the Done
column. The fix introduces no medium-or-higher finding. Three low test-quality
observations remain, all backstopped by behavioural tests or honest scope
statements, and none is a reason to hold the range.
