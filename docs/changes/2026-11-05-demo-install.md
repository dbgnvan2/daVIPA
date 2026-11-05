# Handoff Note

- Date: 2026-11-05
- Agent: Code
- Topic: demo-install

## Summary

A second, fully isolated "demo" instance of daVIPA can now run beside the real
one. `./start-demo.sh` gives it its own data directory — database,
`settings.json`, `app.lock` and `weekly_tactic_debug.log` — seeded with the six
sample items from `demo_data.py`, while `/Applications/daVIPA.app` keeps running
on the real data and is never written to.

The whole feature rests on one `src/` change: `paths.app_data_dir_path()` now
honours a `GETMOREDONE_DATA_DIR` override. `app.lock` is the row that decided
the shape of it — the app takes an exclusive `flock` on
`app_data_dir_path() / "app.lock"`, so a second instance sharing that directory
was refused at launch rather than merely sharing a theme. All four pieces of
writable state resolve through that one function, so one override isolates them
together.

Spec: `docs/spec_2026-11-05_demo_install.md` (IDs D1–D5).
Coverage: `docs/spec_coverage_2026-11-05_demo_install.md`.
User documentation: `docs/DEMO_INSTALL.md`.

Six commits, in four groups:

| Commits | What |
|---|---|
| `5508316` | the spec, before any code |
| `1a3e8c8`, `51b961a`, `df93846` | the implementation, its docs and its tests |
| `8cbdfaf`, `2873e3f` | fixes for three findings from the first review round |
| `246981f`, `d3f8ec0` | fixes for the findings from the second round |

## Files changed

- `src/getmoredone/paths.py` — the only `src/` change: the
  `GETMOREDONE_DATA_DIR` branch in `app_data_dir_path()`
- `start.sh` — no longer forces the production database over a data-dir-only
  override; `--print-env`; resolves a path the way `paths.py` does
- `start-demo.sh` — new
- `tools/create_demo_data.py` — put `tools/src` on `sys.path`, which does not
  exist, so the script `README.md` and `CLAUDE.md` both tell you to run could
  not import at all
- `conftest.py` — drops an ambient `GETMOREDONE_DATA_DIR` for the session
- `tests/test_demo_install.py` — new, 26 tests
- `tests/test_release_docs.py` — four tests for D5
- `docs/spec_2026-11-05_demo_install.md`, `docs/spec_coverage_2026-11-05_demo_install.md`,
  `docs/DEMO_INSTALL.md` — new
- `docs/DEV_PROD_WORKFLOW.md`, `docs/DOCUMENTATION_INDEX.md`, `README.md`,
  `CHANGELOG.md`, `BACKLOG.md`

Deliberately not touched, at the user's instruction: `INSTALL.md` (it carries
unrelated uncommitted edits, so D5.4 is recorded as **not done** for that file
alone) and the untracked files at the repository root.

## Verification

- Command: `GETMOREDONE_NO_MAPPED_WINDOWS=1 taskpolicy -b ./venv/bin/python -m
  pytest tests/test_demo_install.py tests/test_release_docs.py
  tests/test_settings_isolation.py tests/test_repo_hygiene.py -q`
- Result: **PASS** — 75 passed.

- Command: the full suite, locally
- Result: **NOT RUN.** Two attempts were stopped: the first because a second
  run had been pointed at the same log file, the second because a review
  subagent was running the whole suite without
  `GETMOREDONE_NO_MAPPED_WINDOWS=1`, so the three mapped-window tests were
  taking keyboard focus on a machine in use.

- Command: the full suite in CI, on `69f839b` (run 42088130403)
- Result: **7 failed, 1630 passed, 1 skipped**, identically on Python 3.11,
  3.12 and 3.13. All seven failures are pre-existing and unrelated to this
  batch: the same seven failed on the base commit `47ff250`, and on at least
  four commits before it, with **1600** passed. The pass count rose by exactly
  the 30 tests this batch adds and the failure set did not change, so this
  batch introduces no failure. The seven are all window-manager attribute
  assertions — `-topmost` and `-alpha` read back unchanged under the headless
  display, so `assert _topmost_now(...)` and
  `assert float(...attributes("-alpha")) == 0.0` fail:
  `test_t51_a_modal_drops_the_timers_always_on_top`,
  `test_t52_the_timer_is_topmost_again_afterwards`,
  `test_t56_a_second_modal_does_not_hand_the_flag_back_early`,
  `test_t57_an_unbalanced_resume_does_not_break_the_next_modal`,
  `test_alpha_still_passes_through_the_attributes_wrapper`,
  `test_raw_tkinter_windows_are_hidden_and_registered_too`,
  `test_wt_m6b6_a_notice_lowers_an_always_on_top_parent`.
  That is a standing red build, which the global rule says to fix or delete
  rather than keep as background noise. Out of scope here; recorded in
  `BACKLOG.md`.

- Command: `bash -n start.sh start-demo.sh`
- Result: **PASS** (also asserted by `test_d2_launchers_are_valid_bash`).

- Command: `sqlite3 "file:$HOME/Library/Application
  Support/GetMoreDone/getmoredone.db?mode=ro" 'select count(*) from
  action_items;'`, before and after the whole batch
- Result: **PASS** — 914 both times. The sha256 of the real `getmoredone.db`,
  `settings.json` and `app.lock` is unchanged across the batch
  (`a904c9bcb5fcd868`, `00ef729278877bfd`, `5efddaf385b9d42c`). The `app.lock`
  digest is the conclusive one: it proves the demo never opened the real
  directory, because opening it would have taken the lock.

- Command: `./start-demo.sh`, for real, with the packaged app running
- Result: **PASS** — both windows held open at once, the demo showing its six
  seeded items from its own database. This is spec §8, the criterion flagged as
  needing human review: two processes and two `flock` calls are not something
  the suite can assert. The demo instance was closed afterwards.

- Command: `./venv/bin/python tools/create_demo_data.py` under the demo
  environment
- Result: **PASS** — reports the database it seeds and the item count.

Every test added in this batch was proved able to fail by mutation: restoring
the defect verbatim, running the test, confirming red, restoring the original.
One of those mutations was itself wrong and is worth recording — the first
attempt at falsifying `test_d2_refusal_creates_nothing_under_the_real_path` put
the `mkdir` just above the `--print-env` block, which is still *below* the
guard, so the test passed and nothing was proved. Mutating with the original
defect — `mkdir` above the guard — fails it.

## Review passes

| Pass | Lens | Outcome |
|---|---|---|
| `learning-qa` | failures that hide (P1–P7 + repo checklist) | 11 findings: 2 high, 3 medium, 6 low |
| `/code-review` | correctness | 3 findings, all medium, all confirmed by hand |
| `/security-review` | security | no HIGH or MEDIUM at confidence ≥ 8; five candidates argued down in writing |
| cold test-quality pass | can each test fail | **not completed** — see Risks |

The two high-severity findings, both reproduced before being fixed:

1. The demo launcher's guard compared the two directories for **equality**, so
   a demo directory *inside* the real one was accepted — `GETMOREDONE_DATA_DIR`
   of `.../GetMoreDone/demo` exited 0, and a launch would have written the
   demo's database, settings and `app.lock` among 914 real action items. It now
   refuses any overlap in either direction; the reverse direction matters
   because `DEMO_INSTALL.md` documents an `rm -rf` reset of the demo directory.
2. `test_d1_the_suite_runs_with_no_data_dir_override` **could not fail**. It
   asserted `os.environ.get("GETMOREDONE_DATA_DIR") is None` in the running
   process, which is true in any shell that never exported the variable and in
   CI, so it stayed green with the `conftest` pop deleted. It now runs a nested
   pytest with the variable actually set.

Medium findings fixed: the `mkdir` ran before the guard (so a refused run
created the directory it refused, and `--print-env` had a filesystem side
effect); seeding keyed on the database *file* rather than its rows, so one
interrupted seed permanently disabled seeding and every later launch opened an
empty demo in silence; two tests called `app_data_dir_path()` with no override
and so created the user's real data directory on a blank machine; the
requirements install was asserted by indentation rather than by order; and the
`conftest` comment and spec D1.5 overstated what the override could reach.

## Risks / Known gaps

- **The full suite never ran on this machine.** It ran in CI instead, and the
  result is above: the 7 pre-existing window-attribute failures and nothing
  new. The four touched test files are green locally.
- **The owed cold pass did not finish.** The repo's own rule is that a pass
  producing a high-severity finding earns another, cold, in a different failure
  family. That pass was stopped partway. The two fix commits `246981f` and
  `d3f8ec0` are therefore the least-reviewed code in this batch — exactly the
  category the rule exists for. A cold pass over
  `df93846...d3f8ec0` is the first thing to do next.
- `INSTALL.md` has no demo-launcher line (D5.4, **not done**, deliberate).
- An ambient exported `GETMOREDONE_DB` is honoured by `pytest_sessionstart`
  rather than replaced, so a developer who exports it has the suite run
  migrations against that database. Pre-existing; this batch makes it easier to
  reach. Recorded in `BACKLOG.md`.
- `start.bat` keeps its own, different default (repo-local `data/`), and there
  is no `start-demo.bat`. An explicit non-goal.
- Two low findings recorded in `BACKLOG.md` rather than fixed in-loop: the new
  tests hash the whole production database twice per run, and
  `tests/test_audio.py:87` reads an unbound `settings` name.
- `tests/test_repo_hygiene.py:95` allowlists
  `GetMoreDone_MasterSpec_SQLite_v1.md` while `CLAUDE.md` names
  `daVIPA_MasterSpec_SQLite_v1.md`. One is stale. Adjacent, not fixed.

## Next agent actions

- Run a **cold** review pass over `df93846...d3f8ec0`, the two fix commits,
  with the test suite explicitly out of its scope. Give it a read-only lens: a
  subagent gets neither `GETMOREDONE_NO_MAPPED_WINDOWS=1` nor the
  `taskpolicy -b` hook, and one in this batch ran the whole suite twice despite
  being told not to, taking the user's keyboard focus.
- Decide what to do about the 7 standing CI failures. They are not this
  batch's, but they make CI unable to say "green" for anyone, which is the
  state the global rule tells us not to leave.
- Decide whether `docs/demo-install-prompt.md` (the kickoff prompt, currently
  untracked) belongs in `docs/changes/` beside the other `*-kickoff-prompt.md`
  files. Left untracked at the user's instruction.
