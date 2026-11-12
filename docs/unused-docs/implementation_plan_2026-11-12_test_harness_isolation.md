# Implementation plan — test harness isolation (RLS)

- Date: 2026-11-12
- Spec prefix: **RLS** (verified unused in `BACKLOG.md` and `docs/spec_coverage.md`)
- Base: `ea91971`, which is `origin/main`; local and remote level, tree clean
- Status: **awaiting approval — no code written**

## 1. What this batch is

The six findings of the PCC cold pass of 2026-11-12, accepted and deferred by
the user so the PCC/LMM/PBG work could be pushed first. They are recorded in
full outside the repo at
`side-session-notes/local_3fff4d83…/2026-11-12-pcc-cold-pass-deferred-findings.md`.
All six were re-verified against `ea91971` before this plan was written, not
taken from the review report.

Nothing here changes application behaviour. Five of the six are in `tests/`,
one is in `conftest.py`.

## 2. Tier and budget, stated before the work

`effort-budget.md` §1: the changed paths are `tests/` and `conftest.py`, so
this is the **Light** tier — run the tests the change touches, read the diff
once, push. `CLAUDE.md`'s *Review sweeps* resolves the same way: "tests,
config or a document alone earns no sweep at all". So **no cold pass is
planned**, and `/csdp`'s second and third passes (`/code-review`,
`/security-review`) do not apply; its own guardrail says a test-only batch
gets the first alone. If the user wants a cold pass anyway it is cheap to add,
but by the standard it would be spending the full budget on test hygiene.

`effort-budget.md` §9: a batch that exists to fix reviewed findings is counted
by findings, not lines — **at most one guard per finding**, so six. This plan
adds **four** new guards and changes two existing tests, which is inside that.
The 2x line ceiling does not apply.

Prose ceiling (0.3x changed code) applies to the diff and will be measured in
the status report.

## 3. Acceptance criteria

| ID | Criterion | Where | Verified by |
|---|---|---|---|
| **RLS-M1** | `tests/render_list_screen.py` resolves no path in the user's real application-support directory, and removes the temp directory it makes | `tests/render_list_screen.py` | `tests/test_priority_level_colors.py::test_rlsm1_neither_render_helper_touches_the_real_data_dir` (parametrised over both helpers) |
| **RLS-M2** | `conftest.py`'s live-data fingerprint covers `weekly_tactic_debug.log`; `app.lock` is excluded with the reason stated in the docstring | `conftest.py::_user_data_fingerprint` | `tests/test_settings_isolation.py::test_rlsm2_the_weekly_log_is_fingerprinted` |
| **RLS-M3** | One `LBL` parser, used by both call sites, tolerant of a separator in the label text | `tests/test_priority_level_colors.py` | `tests/test_priority_level_colors.py::test_rlsm3_a_piped_title_parses_to_three_fields` |
| **RLS-M4** | The unconsumed `.frame_fill` channel is gone, and the fixture docstring describes only what the fixture provides | `tests/render_priority_cells.py`, `tests/test_priority_level_colors.py` | no new guard — see §5 |
| **RLS-M5** | The data-directory guard does not create the directory it guards, and asserts positively that the helper's workspace is under the temp root | `tests/test_priority_level_colors.py` | the strengthened assertion in `::test_pccm3_the_render_helper_stays_out_of_the_real_data_dir`, re-mutation-proved |
| **RLS-M6** | `tests/render_priority_cells.py` refuses to be imported, since import sets `GETMOREDONE_DATA_DIR` process-wide | `tests/render_priority_cells.py` | `tests/test_priority_level_colors.py::test_rlsm6_the_helper_refuses_to_be_imported` |
| **RLS-D1** | `docs/spec_coverage.md` carries a row per criterion above | `docs/spec_coverage.md` | none — no test reads prose (`effort-budget.md` §5) |

## 4. How each is built

**RLS-M1.** The fix is one environment variable, not two transplants. My relayed
description said to copy both `render_priority_cells.py:61-68` (the env) and
`:97-100` (the `AppSettings.get_settings_path` patch); re-reading showed the
patch is unnecessary here. `AppSettings.get_settings_path` →
`paths.default_settings_path` → `app_data_dir_path() / "settings.json"`, so
setting `GETMOREDONE_DATA_DIR` redirects the settings file, the weekly log,
`app.lock` and the database together. `render_priority_cells.py` needs the
classmethod patch only because it *writes* a chosen settings file.

So: a `mkdtemp` and `os.environ["GETMOREDONE_DATA_DIR"] = …` above the
`src.getmoredone` imports at `:32-33`; `:37`'s `VPSManager` path becomes
`WORKSPACE / "render.db"`; and `__main__` gains
`finally: shutil.rmtree(WORKSPACE, ignore_errors=True)`.

This does not conflict with the suite's policy of running with that variable
unset (`conftest.py:135-153`, guarded by
`test_demo_install.py::test_d1_the_suite_runs_with_no_data_dir_override`): that
policy is about the pytest process, and this is a child process setting its own.

The guard needs the helper to report where it landed, so `render_list_screen.py`
gains a `DATADIR {app_data_dir_path()}` line, as `render_priority_cells.py`
already prints. Its existing caller asserts on the *substrings* `GAP`, `DUP`
and `NOROWS` in stdout, so a new line must not contain them: `mkdtemp`
suffixes are lowercase and those words are uppercase, so it cannot.
`::test_rlsm1_…` then parametrises over both helpers, replacing the
single-helper guard.

**RLS-M2.** Add `("weekly_log", "weekly_tactic_debug.log")` to the tuple at
`conftest.py:77` and correct the docstring's "the real settings file and
database". `app.lock` stays out: the packaged app holds `flock` on it while
running, and the guard already carries an app-running probe because a running
app perturbs this directory — so the docstring states the exclusion and why.
The entries are hashed, not trusted by mtime, which the existing code already
does; `test_cghm12_a_timestamp_move_leaves_the_run_green` shows an mtime-only
mover already degrades to a report rather than a failure.

The new guard follows `test_the_session_guard_fails_the_run_when_content_changes`
(`tests/test_settings_isolation.py:119`), which drives a nested pytest run
pointed at a fake directory via `GETMOREDONE_TEST_GUARD_DIR` — so exercising
the guard touches no real file.

**RLS-M3.** Lift the parse to one module-level helper taking the `LBL ` line and
returning the triple, called from the fixture (`:1848`) and from
`::test_pccm3_a_saved_colour_reaches_the_real_widget` (`:2069`). The guard
feeds it a line built from `"PW|LS|Blog - W8 - write blog 3"` — the title
`render_list_screen.py:40` already uses — and asserts three fields with the
text intact.

**RLS-M4.** Delete the `THEME` print, the parse branch, `assert frame_fill`, the
`frame_fills` dict and the `SimpleNamespace` field; the fixture returns
`.rows` only. The docstring loses the clause claiming `.frame_fill` is "what an
untinted row must equal", which no test asserts and which
`::test_pccm1_a_rendered_row_has_no_priority_tint` contradicts in its own
docstring.

Deleting rather than finishing the assertion is deliberate. Equality against
the theme's frame fill is false on Upcoming, whose date-group header frame uses
`surface_subtle` (`upcoming.py:264`) and is reported as a row by the label
walk. The weakness the reviewer inferred from it — that a row tinted
`palette["danger"]` would pass the not-a-level-colour check — is already caught
by `::test_pccm5_no_row_builder_reaches_for_the_danger_palette`, an AST check
with an exact count of zero. So the channel buys nothing the suite lacks.

**RLS-M5.** Replace `real = app_data_dir_path()` with the computation
`conftest.py:73-75` uses and documents —
`Path(user_data_dir(APP_NAME, APP_AUTHOR)).expanduser().resolve()`, no
`mkdir` — and add a positive assertion that the reported directory is under
`tempfile.gettempdir()`, so a redirect that escaped into the cwd or `$HOME`
fails rather than passing a bare `!=`.

**RLS-M6.** Two lines at the top of `render_priority_cells.py`: raise
`RuntimeError` when `__name__ != "__main__"`, naming the reason. This keeps
the env-before-import ordering the file depends on, which a lazy-import
refactor would not. The guard asserts `importlib.import_module` raises.

## 5. Criteria not made code-testable, flagged

- **RLS-M4** gets no new guard. It is a deletion plus a docstring correction;
  `effort-budget.md` §5 forbids asserting on prose, and a test that a symbol is
  absent would be a guard against re-adding something nobody is adding. The
  proof is that the file no longer contains it and the suite stays green.
- **RLS-D1** likewise: no test reads `docs/spec_coverage.md`.
- Not in scope, and still unverified by anything: the CustomTkinter UI contract
  (`~/.claude/standards/ui-regression.md`) that PCC's subject matter sits in.
  The plan's §8 manual checklist in
  `implementation_plan_2026-11-11_priority_cell_colour.md` remains unwalked,
  and this batch does not touch it.

## 6. Order

1. RLS-M1 — the one with a user-facing consequence, and it is self-contained.
2. RLS-M6, then RLS-M5, then RLS-M3 — all in the two helper/test files M1
   already touches; M6 before M5 because M5's guard runs the helper.
3. RLS-M4 — last of the test work, because it removes plumbing the others read.
4. RLS-M2 — `conftest.py`, kept separate; it is the only file outside my own
   batch's paths.
5. RLS-D1 — `docs/spec_coverage.md`.

Commits: one for `tests/` + `conftest.py` work per the repo's rule that test
changes commit separately from `src/` (there is no `src/` change here, so this
is one test commit), then one for the document. Each new guard
mutation-proved against the verbatim original before its commit.

## 7. Verification

- `GETMOREDONE_NO_MAPPED_WINDOWS=1 nice -n 19 taskpolicy -b ./venv/bin/python -m pytest tests/test_priority_level_colors.py tests/test_settings_isolation.py tests/test_item_editor_no_context.py tests/test_demo_install.py -q`
  — the four files these changes touch or could break. No full suite locally.
- `./venv/bin/python tools/agents/check_docs_sync.py` — `tests/` is in
  `CODE_PREFIXES`, so this batch requires a change under `docs/` outside
  `docs/unused-docs/`; RLS-D1 satisfies it.
- Mutation proof per new guard, restoring from a byte-for-byte copy.
- `/csdp` to finish, at the Light tier stated in §2, then push `main` and
  **offer a merge — no PR**.

## 8. Risks

- `test_item_editor_no_context.py` currently renders with the developer's own
  settings. After RLS-M1 it renders with defaults, so its `GAP`/`DUP` column
  assertions change input. That is the point of the fix, but if that file has
  been passing *because* of a local `list_row_font_size`, it will fail here and
  that failure is a real finding about the file, not a regression to patch
  around. It is in the test list in §7 for that reason.
- `render_list_screen.py` is driven by one test file that no other batch is
  touching; `conftest.py` is shared with everything, which is why RLS-M2 is
  last and in its own hunk.
