# Spec — a second, isolated demo installation

**Status:** Draft v1, awaiting approval
**Date:** 2026-11-05
**Spec ID root:** `D`
**Touches:** `src/getmoredone/paths.py`, `start.sh`, a new `start-demo.sh`,
`tools/create_demo_data.py`, `conftest.py`, and the dev/prod documentation.

---

## 1. Goal

Two daVIPA instances run side by side on one Mac, sharing nothing that matters:

1. **Real** — `/Applications/daVIPA.app`, writing
   `~/Library/Application Support/GetMoreDone/`. Unchanged, and never written
   to by any part of this work.
2. **Demo** — launched from the repo by `./start-demo.sh`, writing its own
   directory, seeded with the sample items from `demo_data.load_demo_data()`.

## 2. Why one env var is not enough

`GETMOREDONE_DB` already isolates the database. Nothing else in the app's
writable state goes through it:

| State | Resolver | Isolated by `GETMOREDONE_DB`? |
|---|---|---|
| Database | `paths.resolve_db_path` | yes |
| `settings.json` — theme, Obsidian vault path, Gmail trigger label | `app_settings.py:100` → `paths.default_settings_path` | **no** |
| `app.lock` — the single-instance lock | `app.py:490` → `paths.app_data_dir_path` | **no** |
| `weekly_tactic_debug.log` | `weekly_tactic_logging.py:39` | **no** |
| Google OAuth credentials | `paths.google_auth_dir` → `~/.getmoredone` | shared **by design** (see `google_auth_dir`'s docstring); out of scope |

`app.lock` is the row that decides the feature. `acquire_single_instance_lock`
takes an exclusive `flock` on `app_data_dir_path() / "app.lock"`, so a second
instance sharing that directory does not merely share a theme — it shows the
"GetMoreDone Already Running" dialog and exits.

Every entry above resolves through `app_data_dir_path()`. One override there
isolates all four at once, which is why this spec changes one function rather
than four call sites.

## 3. Invariants

- **I1.** With neither `GETMOREDONE_DB` nor `GETMOREDONE_DATA_DIR` set, every
  path the app resolves is byte-for-byte what it is today.
- **I2.** Nothing in this change writes to, deletes from, or migrates anything
  under `~/Library/Application Support/GetMoreDone/`. (`app_data_dir_path()`
  keeps its existing `mkdir(parents=True, exist_ok=True)` on a directory that
  already exists; no file inside it is opened for writing.)
- **I3.** Google credentials under `~/.getmoredone/` are not moved, copied or
  re-resolved. Both instances authenticate from the same place, as today.
- **I4.** The demo launcher cannot resolve to the real data directory, by
  fallback or by a stale environment.
- **I5.** The test suite runs with `GETMOREDONE_DATA_DIR` unset, whatever the
  developer's shell exports, so the existing live-data guards keep their
  meaning.

## 4. Non-goals

- A Windows `start-demo.bat`. `start.bat` keeps its own (different) default.
- Copying or anonymising real data into the demo. The demo is seeded from
  `demo_data.py` only.
- Any change to the Gmail importer's production behaviour or the launchd
  plists.
- Isolating Google credentials per instance.

## 5. Requirements

### D1 — Settings and data-dir isolation

The only `src/` change.

- **D1.1** `paths.app_data_dir_path()` honours `GETMOREDONE_DATA_DIR` when set
  to a non-blank value: `expanduser()`, `resolve()`, then the same
  `mkdir(parents=True, exist_ok=True)` it does today.
- **D1.2** Unset, or set to whitespace, falls back to
  `platformdirs.user_data_dir(APP_NAME, APP_AUTHOR)` — invariant I1. The blank
  handling matches the existing `resource_root()` override, so the two overrides
  in this module behave the same way.
- **D1.3** `default_db_path()` and `default_settings_path()` inherit the
  override with no change of their own.
- **D1.4** Precedence for the database is unchanged and explicit: an explicit
  argument, then `GETMOREDONE_DB`, then `GETMOREDONE_DATA_DIR`, then
  platformdirs. `GETMOREDONE_DB` outranks `GETMOREDONE_DATA_DIR` because
  `resolve_db_path` consults `env_db_path()` first.
- **D1.5** `conftest.py` removes `GETMOREDONE_DATA_DIR` from the environment for
  the duration of a test session and restores it afterwards — invariant I5.
  Without this, an exported override would send `resolve_db_path` to the demo
  directory, where `_forbid_resolving_the_real_database` would not fire, and a
  test run would migrate and write the demo database.

Acceptance — `tests/test_demo_install.py`:

| ID | Test |
|---|---|
| D1.1, D1.3 | `test_d1_data_dir_override_redirects_db_and_settings` |
| D1.2 | `test_d1_unset_override_falls_back_to_platformdirs` |
| D1.2 | `test_d1_blank_override_is_ignored` |
| D1.1 | `test_d1_override_is_expanded_and_resolved` |
| D1.4 | `test_d1_explicit_db_env_var_outranks_the_data_dir` |
| D1.5 | `test_d1_the_suite_runs_with_no_data_dir_override` |

### D2 — Demo launcher

- **D2.1** `./start-demo.sh` at the repo root exports
  `GETMOREDONE_DATA_DIR` (default `~/Library/Application Support/GetMoreDone-Demo`,
  overridable from the caller's environment) and an explicit
  `GETMOREDONE_DB` inside it, then delegates to `./start.sh` for the venv
  bootstrap and launch.
- **D2.2** The launcher refuses, with a non-zero exit, to run against the real
  data directory — invariant I4.
- **D2.3** `start.sh`'s default no longer clobbers a data-dir-only override:
  when `GETMOREDONE_DB` is unset and `GETMOREDONE_DATA_DIR` is set, it leaves
  `GETMOREDONE_DB` unset and lets `paths.py` derive the database from the data
  directory. With neither set, it exports exactly the path it exports today —
  invariant I1.
- **D2.4** Both scripts accept `--print-env`, which prints the resolved data
  directory and database and exits 0 before any venv, pip, cache-clearing or
  launch work. This exists so D2.1–D2.3 can be verified by running the scripts
  rather than by grepping their text.
- **D2.5** The demo seeds itself only when its database file does not yet
  exist. `load_demo_data()` is additive, so seeding on every launch would add
  another six items each time.

Acceptance — `tests/test_demo_install.py`:

| ID | Test |
|---|---|
| D2.1 | `test_d2_demo_launcher_resolves_the_demo_data_dir` |
| D2.1 | `test_d2_demo_launcher_exports_an_explicit_db_path` |
| D2.2 | `test_d2_demo_launcher_refuses_the_real_data_dir` |
| D2.3 | `test_d2_start_sh_default_db_follows_the_data_dir_override` |
| D2.3 | `test_d2_start_sh_default_db_is_unchanged_with_no_env` |
| D2.4 | `test_d2_launchers_are_valid_bash` |

### D3 — The demo-data tool actually runs

- **D3.1** `tools/create_demo_data.py:16` inserts
  `Path(__file__).parent / "src"` — that is `tools/src`, which does not exist.
  Run as a script, `sys.path[0]` is `tools/`, so the import of
  `getmoredone.demo_data` fails. It must insert the repo's `src/`.
- **D3.2** Its docstring names `GETMOREDONE_DATA_DIR` in the selection order it
  already documents.

`README.md` and `CLAUDE.md` both instruct the reader to run this script, so
D3.1 makes two existing documents true.

Acceptance: `test_d3_create_demo_data_runs_against_an_isolated_db`.

### D4 — Headless seed

- **D4.1** One command seeds a demo database with no GUI: the D3-fixed tool,
  run under the demo environment variables. No second seeder is introduced —
  the in-app Settings button, the tool and the launcher all reach
  `demo_data.load_demo_data()`.
- **D4.2** Seeding writes only into the target database.

Acceptance: `test_d4_seed_writes_only_into_the_target_database`.

### D5 — Documentation

- **D5.1** `docs/DEMO_INSTALL.md` covers the two-instance setup, both
  environment variables and their precedence, what stays shared, and how to
  reset the demo.
- **D5.2** `docs/DEV_PROD_WORKFLOW.md` lists `GETMOREDONE_DATA_DIR` in its DB
  selection order and links `DEMO_INSTALL.md`.
- **D5.3** `docs/DEV_PROD_WORKFLOW.md:22` currently claims `start.sh` defaults
  to the repo-local `data/getmoredone.db`. It does not — `start.sh:41` defaults
  to the production Application Support database, and only `start.bat:23` uses
  the repo-local path. Corrected here, because that sentence describes exactly
  the fallback D2.3 exists to defuse.
- **D5.4** `docs/DOCUMENTATION_INDEX.md`, `README.md` and `CHANGELOG.md`
  (under the existing `## [Unreleased]`) name the demo launcher.
  `INSTALL.md` is deliberately left alone: it carries unrelated uncommitted
  edits, and adding a line there would mean committing those too.

Acceptance: `test_d5_demo_doc_names_both_env_vars`,
`test_d5_demo_doc_links_resolve`.

## 6. Implementation order

1. This spec.
2. D1 `paths.py`, D2 `start.sh` + `start-demo.sh`, D3 `tools/create_demo_data.py`.
3. `tests/test_demo_install.py` and the D1.5 `conftest.py` change.
4. D5 documentation, spec coverage, handoff note.

## 7. Adjacent issues found, not fixed

- `start.sh` defaults the dev database to the production Application Support
  path while `start.bat:23` defaults to the repo-local `data/` path. Only the
  macOS script is made data-dir-aware here; the divergence stays.
- `tests/test_repo_hygiene.py:95` allowlists
  `GetMoreDone_MasterSpec_SQLite_v1.md` at the repo root, while `CLAUDE.md`
  names `daVIPA_MasterSpec_SQLite_v1.md`. One of the two is stale.

## 8. Criteria needing human review

- **Side-by-side launch.** That the installed app and the demo both hold a
  window open at once is a GUI fact about two processes and two `flock` calls.
  The automated tests cover the path split; the simultaneous launch is verified
  by hand and recorded in the handoff note.
