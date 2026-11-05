# Spec Coverage — a second, isolated demo installation (2026-11-05)

Spec: [`docs/spec_2026-11-05_demo_install.md`](spec_2026-11-05_demo_install.md)

Suite: the files this change touches — `tests/test_demo_install.py`,
`tests/test_release_docs.py`, `tests/test_settings_isolation.py`,
`tests/test_repo_hygiene.py` — **75 passed** under
`GETMOREDONE_NO_MAPPED_WINDOWS=1`.

The **full suite was not completed locally**. Two runs were started and both
were stopped: the first because a second run had been pointed at the same log
file, the second because a review subagent was running the whole suite *without*
`GETMOREDONE_NO_MAPPED_WINDOWS=1`, so the three mapped-window tests were
building real windows and taking keyboard focus on a machine in use. Treat the
75 above as what it is: the touched files, not the suite.

The whole suite ran in CI instead, on `69f839b`: **7 failed, 1630 passed, 1
skipped** on each of Python 3.11, 3.12 and 3.13. The same seven failed on the
base commit with 1600 passed, so the pass count rose by exactly the 30 tests
this batch adds and the failure set did not change. All seven are pre-existing
window-manager attribute assertions under the headless display, listed in the
handoff note and recorded in `BACKLOG.md`.

## D1 — Settings and data-dir isolation

| Spec ID | Criterion | Implementation | Test | Status |
|---|---|---|---|---|
| D1.1 | `GETMOREDONE_DATA_DIR` redirects the data directory, expanded, resolved and created | `paths.py::app_data_dir_path` | `tests/test_demo_install.py::test_d1_data_dir_override_redirects_db_and_settings` | done |
| D1.1 | A `~` and a `..` in the value behave as meant | same | `::test_d1_override_is_expanded_and_resolved` | done |
| D1.2 | Unset falls back to platformdirs, unchanged | same | `::test_d1_unset_override_falls_back_to_platformdirs` | done |
| D1.2 | Whitespace-only is treated as unset | same | `::test_d1_blank_override_is_ignored` | done |
| D1.3 | `default_db_path()` and `default_settings_path()` inherit it | `paths.py::default_db_path`, `::default_settings_path` | `::test_d1_data_dir_override_redirects_db_and_settings` | done |
| D1.4 | `GETMOREDONE_DB` outranks `GETMOREDONE_DATA_DIR` | `paths.py::resolve_db_path` | `::test_d1_explicit_db_env_var_outranks_the_data_dir` | done |
| D1.5 | The suite never inherits an exported override | `conftest.py::pytest_sessionstart`, `::pytest_sessionfinish` | `::test_d1_the_suite_runs_with_no_data_dir_override` (nested run, variable actually set) | done |
| D1.5 | The override is restored after the session | `conftest.py::pytest_sessionfinish` | `::test_d1_the_session_restores_the_override_afterwards` | done |
| D1.2 | The fallback tests do not create the real data directory | `tests/test_demo_install.py` (HOME redirected) | `::test_d1_unset_override_falls_back_to_platformdirs`, `::test_d1_blank_override_is_ignored` | done |

## D2 — Demo launcher

| Spec ID | Criterion | Implementation | Test | Status |
|---|---|---|---|---|
| D2.1 | The demo resolves to its own directory | `start-demo.sh` | `tests/test_demo_install.py::test_d2_demo_launcher_resolves_the_demo_data_dir` | done |
| D2.1 | Both variables set explicitly, so no fallback can fire | same | `::test_d2_demo_launcher_exports_an_explicit_db_path` | done |
| D2.1 | One canonical spelling in both variables | same | `::test_d2_demo_launcher_reports_one_canonical_directory` | done |
| D2.1 | A blank value falls back to the default | same | `::test_d2_demo_launcher_ignores_a_blank_data_dir` | done |
| D2.1 | A quoted `~` is expanded, not taken literally | same | `::test_d2_demo_launcher_expands_a_tilde` | done |
| D2.2 | The real directory itself is refused | `start-demo.sh` (overlap comparison) | `::test_d2_demo_launcher_refuses_the_real_data_dir` | done |
| D2.2 | A directory **inside** the real one is refused | same | `::test_d2_demo_launcher_refuses_a_directory_inside_the_real_one` | done |
| D2.2 | A directory **containing** the real one is refused | same | `::test_d2_demo_launcher_refuses_a_directory_containing_the_real_one` | done |
| D2.3 | `start.sh` no longer forces the production DB over a data-dir override | `start.sh` | `::test_d2_start_sh_default_db_follows_the_data_dir_override` | done |
| D2.3 | With neither variable set, `start.sh` exports what it always did | same | `::test_d2_start_sh_default_db_is_unchanged_with_no_env` | done |
| D2.3 | A blank data dir resolves to production in the shell too | same | `::test_d2_start_sh_treats_a_blank_data_dir_as_unset` | done |
| D2.4 | `--print-env` reports the resolution before doing any work | `start.sh`, `start-demo.sh` | every D2 test above runs through it | done |
| D2.4 | `--print-env` creates nothing | `start-demo.sh` (guard and exit precede the `mkdir`) | `::test_d2_print_env_creates_nothing` | done |
| D2.4 | A refused run creates nothing under the real path | same | `::test_d2_refusal_creates_nothing_under_the_real_path` | done |
| D2.4 | The launcher's resolver matches `app_data_dir_path()` | both scripts' `gmd_resolve` | `::test_d2_print_env_matches_the_resolver` (tilde, trailing slash, doubled slash, `..`, symlinked parent) | done |
| D2.4 | Both scripts parse | — | `::test_d2_launchers_are_valid_bash` | done |
| D2.5 | Seeds when the demo database holds no items | `start-demo.sh` (row count, not file existence) | `::test_d2_demo_launcher_reseeds_a_database_with_no_items` (absent, unreadable, populated, emptied) | done |
| D2.5 | Requirements are installed before the seed runs | same | `::test_d2_demo_launcher_installs_requirements_before_seeding` | done — source-text guard; see "Not covered" below |

## D3 / D4 — The headless seed

| Spec ID | Criterion | Implementation | Test | Status |
|---|---|---|---|---|
| D3.1 | The tool puts the repo's `src/` on `sys.path` and runs | `tools/create_demo_data.py` | `tests/test_demo_install.py::test_d3_create_demo_data_runs_against_an_isolated_db` | done |
| D3.2 | Its docstring names `GETMOREDONE_DATA_DIR` | same | — | done — prose, no test |
| D4.1 | One command seeds a demo database with no GUI | `tools/create_demo_data.py` under the demo environment | `::test_d3_create_demo_data_runs_against_an_isolated_db` | done |
| D4.2 | Seeding writes only into the target database | same | `::test_d4_seed_writes_only_into_the_target_database` | done |

## D5 — Documentation

| Spec ID | Criterion | Implementation | Test | Status |
|---|---|---|---|---|
| D5.1 | `docs/DEMO_INSTALL.md` exists and covers both variables | `docs/DEMO_INSTALL.md` | `tests/test_release_docs.py::test_d5_demo_doc_exists`, `::test_d5_demo_doc_names_the_variables_the_code_reads` | done |
| D5.1 | The directory it tells you to delete is the one the launcher uses | same | `::test_d5_demo_doc_names_the_launcher_default_directory` | done |
| D5.1 | Its links resolve | same | `::test_d5_demo_doc_links_resolve_to_real_files` | done |
| D5.2 | `DEV_PROD_WORKFLOW.md` lists the variable and links the doc | `docs/DEV_PROD_WORKFLOW.md` | — | done — prose, no test |
| D5.3 | The false claim about `start.sh`'s default is corrected | same | — | done — prose, no test |
| D5.4 | `DOCUMENTATION_INDEX.md`, `README.md`, `CHANGELOG.md` name the launcher | those files | `tests/test_release_docs.py::test_rm6b_readme_links_resolve_to_real_files` covers the README link | done |
| D5.4 | `INSTALL.md` | — | — | **not done** — deliberately skipped. The file carries unrelated uncommitted edits, so adding a line would have meant committing them. |

## Criteria needing human review

| Criterion | Status |
|---|---|
| Spec §8 — the demo and the installed app hold windows open at the same time | Verified by hand, recorded in the handoff note. Two processes and two `flock` calls are not something the suite can assert. |

## Not covered by the suite

- The three mapped-window tests are skipped locally under
  `GETMOREDONE_NO_MAPPED_WINDOWS=1`, which is what keeps a test run from
  taking the screen. CI runs them.
- `start-demo.sh`'s venv bootstrap and `exec ./start.sh` handoff run only on a
  real launch; `--print-env` exits before both, so no test reaches them. The
  ordering of the requirements install relative to the seed is therefore held
  by a source-text guard rather than by behaviour — anchored to whole lines,
  asserting exact counts and the relative position of the two lines, as the
  repo's rules require where no behavioural check is practical.
- An ambient exported `GETMOREDONE_DB` is honoured by `pytest_sessionstart`
  rather than replaced, so a developer who exports it has the suite run
  migrations against that database. Pre-existing; recorded in `BACKLOG.md`
  rather than fixed here.

## Review passes this batch went through

| Pass | Lens | Outcome |
|---|---|---|
| `learning-qa` | failures that hide (P1–P7 plus the repo checklist) | 11 findings: 2 high, 3 medium, 6 low |
| `/code-review` | correctness | 3 findings, all medium, all confirmed by hand |
| `/security-review` | security | no HIGH or MEDIUM at confidence ≥ 8; five candidates argued down in writing |
| cold test-quality pass | can each test fail; the scripts as programs | **not completed** — stopped partway because it was running the suite without the mapped-window guard. Owed, because the previous pass produced high-severity findings. |

Every high and medium finding was fixed with a test; every low was recorded in
`BACKLOG.md` with its severity and reason, not fixed in-loop.
