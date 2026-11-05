# Dev vs Prod workflow (daVIPA)

Goal:
- Keep a **dev** instance you run from the repo and update freely
- Have a **prod** instance that behaves like a normal install (shareable app)

## DB selection

daVIPA chooses its SQLite database in this order:
1) Explicit db path passed by the caller (rare)
2) Environment variable: `GETMOREDONE_DB` — one specific database file
3) Environment variable: `GETMOREDONE_DATA_DIR` — the whole data directory;
   the database is `<data dir>/getmoredone.db`
4) Default (production):
   `~/Library/Application Support/GetMoreDone/getmoredone.db`

`GETMOREDONE_DATA_DIR` moves the settings file, `app.lock` and the
weekly-tactic log as well, which `GETMOREDONE_DB` does not. That is what a
second instance needs: see [DEMO_INSTALL.md](DEMO_INSTALL.md).

## Recommended setup

### Dev (repo)

Use the repo-local database:
- `/Users/davemini2/ProjectsLocal/daVIPA/data/getmoredone.db`

Set `GETMOREDONE_DB` to it. The two launchers do **not** agree on a default,
so do not rely on one:

- `start.bat` defaults to the repo-local `data\getmoredone.db`.
- `start.sh` defaults to the **production** Application Support database, and
  only when neither `GETMOREDONE_DB` nor `GETMOREDONE_DATA_DIR` is set.

(This section used to say both scripts defaulted to the repo-local database.
They never did.)

### Prod (installed)

Use the Application Support database:
- `~/Library/Application Support/GetMoreDone/getmoredone.db`

Do **not** set `GETMOREDONE_DB` for the prod app.

## Demo instance

A third arrangement: a demo install with throwaway data, running at the same
time as the real one. `./start-demo.sh`, documented in
[DEMO_INSTALL.md](DEMO_INSTALL.md).

## Gmail importer

The Gmail importer uses the same DB selection rule.

- Dev importer: set `GETMOREDONE_DB` to the repo-local DB (or pass `--db`)
- Prod importer: do not set `GETMOREDONE_DB` (it will write into Application Support)
