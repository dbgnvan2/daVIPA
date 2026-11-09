You are working in the daVIPA (GetMoreDone) repo at ~/ProjectsLocal/daVIPA —
a Python/CustomTkinter desktop task manager with a SQLite backend.

## Goal
Set up a second, fully isolated "demo" installation on this Mac so two
independent instances run side by side:
1. Real data (unchanged) — /Applications/daVIPA.app →
   ~/Library/Application Support/GetMoreDone/
2. Demo data — a fresh DB seeded with sample items, launched from the repo.

## What already exists (do NOT rebuild these)
- DB selection order (src/getmoredone/paths.py `resolve_db_path`):
  explicit arg → `GETMOREDONE_DB` env var → default
  `~/Library/Application Support/GetMoreDone/getmoredone.db`.
- Demo loader: src/getmoredone/demo_data.py → `load_demo_data()` (6 sample
  ActionItems + system/who defaults; additive only, never deletes).
- In-app "Load demo data" button: src/getmoredone/screens/settings.py
  (~line 137 wiring, ~line 1115 handler).
- start.sh bootstraps the venv and runs run.py; it hardcodes the prod DB
  path as a default ONLY when `GETMOREDONE_DB` is unset.

## The gap you must close
`GETMOREDONE_DB` isolates the database, but NOT settings:
`AppSettings.get_settings_path()` → `paths.default_settings_path()` →
`app_data_dir_path()/"settings.json"`, and `app_data_dir_path()` has no env
override. So a second instance currently shares the real settings.json
(Obsidian vault path, theme, Gmail trigger label) and ~/.getmoredone/ Google
creds. Close that so the demo is fully independent.

## Deliverables (each with acceptance criteria)

### D1 — Settings/data-dir isolation (the only source change)
- Add an env override to `paths.py` `app_data_dir_path()`: honor
  `GETMOREDONE_DATA_DIR` (a directory path, expanduser+resolve, mkdir as the
  current code does) when set; unset → exact current behavior via
  `platformdirs.user_data_dir("GetMoreDone","GetMoreDone")`. Make
  `default_db_path()` and `default_settings_path()` inherit it automatically.
- Acceptance: `GETMOREDONE_DATA_DIR=/tmp/x` yields
  `default_db_path() == /tmp/x/getmoredone.db` and
  `default_settings_path() == /tmp/x/settings.json`. Default (unset) behavior
  is byte-for-byte unchanged.

### D2 — Demo launcher
- A script (e.g. `start-demo.sh` at repo root) that points the demo instance
  at a demo dir — recommend `~/Library/Application Support/GetMoreDone-Demo/`
  — then delegates to the same venv bootstrap/run as start.sh.
- PITFALL: start.sh hardcodes the prod DB default when `GETMOREDONE_DB` is
  unset, which would clobber a `GETMOREDONE_DATA_DIR`-only override. Ensure
  the demo can never fall through to the prod DB (set both vars explicitly,
  or patch start.sh so its default respects `GETMOREDONE_DATA_DIR`).
- Acceptance: launching the demo with prod untouched writes ONLY into the
  demo dir — no new rows in the prod DB, no write to prod settings.json.

### D3 — Fix the broken tool script
- tools/create_demo_data.py has `sys.path.insert(0, str(Path(__file__).parent
  / "src"))` → resolves to tools/src (wrong). Fix to the repo src/ dir. Verify
  it runs clean and reports the item count.

### D4 — Headless seed (nice-to-have)
- One command that creates + seeds the demo DB without the GUI, using
  `demo_data.load_demo_data()` against the demo path, so the demo's first
  launch isn't empty.

### D5 — Docs
- A short `docs/DEMO_INSTALL.md` (or a section in
  docs/DEV_PROD_WORKFLOW.md) covering the two-instance setup, the two env
  vars, and how to reset the demo.

## Hard constraints (do NOT violate)
- NEVER write to or delete anything under
  ~/Library/Application Support/GetMoreDone/ (prod). Its getmoredone.db holds
  914 action items. Reading it is fine; writing it is not.
- Do not touch Google credentials (~/.getmoredone/) or change how prod
  resolves auth.
- Do not modify the Gmail importer's prod behavior or the launchd plists.
- Default (no-env-var) behavior must stay identical for prod users.

## Repo conventions
- Spec first: add a concise spec under docs/ for D1 before/with the code.
- Tests live in tests/. Run: `GETMOREDONE_NO_MAPPED_WINDOWS=1
  ./venv/bin/python -m pytest -m "not meta" -q`.
- conftest.py sets `GETMOREDONE_DB` to a temp file for tests. Several tests
  (test_settings_isolation.py, test_live_data_guard.py, test_audio.py) compute
  the REAL data dir directly via `platformdirs.user_data_dir` — verify they
  still hold with no env set, and add coverage for the new override.
- Commit src / docs / tests as separate commits (repo convention); csdp-style:
  commit → sweep → fix → document → push.

## Verification (report back with evidence)
1. Fresh demo dir seeds N items (state N) via the headless path; a sqlite3
   query confirms the rows exist ONLY in the demo DB.
2. Launcher starts under demo env; prod DB row count is unchanged before vs
   after (914 action_items).
3. Full suite green under `GETMOREDONE_NO_MAPPED_WINDOWS=1`.
4. tools/create_demo_data.py runs clean.
