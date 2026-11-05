# A demo instance beside your real one

Two daVIPA instances, running at the same time, sharing nothing that matters:

| | Real | Demo |
|---|---|---|
| Launched by | `/Applications/daVIPA.app` | `./start-demo.sh` from the repo |
| Data directory | `~/Library/Application Support/GetMoreDone/` | `~/Library/Application Support/GetMoreDone-Demo/` |
| Contents | your actual work | six sample items from `demo_data.py` |

Spec: [spec_2026-11-05_demo_install.md](spec_2026-11-05_demo_install.md).

## Quick start

```bash
./start-demo.sh
```

On the first run it creates the demo directory, seeds the demo database and
launches. On later runs it just launches — the seed is additive, so re-running
it every time would pile up another set of sample items.

Seeding is decided by the rows, not by the file: a demo database that exists
but holds no action items gets seeded, because that is what an interrupted
first run leaves behind. A demo that holds items is never re-seeded.

To see what it will use without launching anything:

```bash
./start-demo.sh --print-env
```

It prints the data directory, the database, and whether this launch would seed
(`seed=yes` or `seed=no`), and it creates nothing — not even the demo
directory. The refusal below is checked before that point too, so asking the
question can never be what brings a directory into existence.

## The two environment variables

daVIPA resolves its database in this order:

1. An explicit path passed by the caller (rare).
2. `GETMOREDONE_DB` — one specific database file.
3. `GETMOREDONE_DATA_DIR` — the whole data directory; the database is
   `<data dir>/getmoredone.db`.
4. The default, `~/Library/Application Support/GetMoreDone/getmoredone.db`.

`GETMOREDONE_DB` therefore outranks `GETMOREDONE_DATA_DIR`. `start-demo.sh`
sets both, pointing both at the demo directory.

### Why the directory, not just the database

`GETMOREDONE_DB` isolates the database and nothing else. Four things live in
the data directory, and all four resolve through `paths.app_data_dir_path()`:

| File | What sharing it would do |
|---|---|
| `getmoredone.db` | the demo would show your real items |
| `settings.json` | the demo would share your theme, Obsidian vault path and Gmail trigger label — and writing a setting in one instance would change the other |
| `app.lock` | **the demo would not start at all.** The app takes an exclusive lock on this file, so the second instance shows "GetMoreDone Already Running" and exits |
| `weekly_tactic_debug.log` | demo migrations would be written into the log you read to audit changes to your real data |

`GETMOREDONE_DATA_DIR` moves all four at once.

## What stays shared

**Google credentials.** Both instances read `~/.getmoredone/credentials.json`
and the token beside it. That is deliberate — `gmail_importer`, the launchd
import job and six scripts under `tools/` all name that one directory, and
splitting it per instance would send you through OAuth again. See
`paths.google_auth_dir`.

The repo itself is shared too, of course: both the demo and a source launch run
the code in your working tree.

## Resetting the demo

Delete the demo directory and launch again. It will be recreated and reseeded.

```bash
rm -rf "$HOME/Library/Application Support/GetMoreDone-Demo"
./start-demo.sh
```

Never run that against `~/Library/Application Support/GetMoreDone` — that is
the real one.

`start-demo.sh` refuses to start if `GETMOREDONE_DATA_DIR` overlaps the real
installation **in either direction**: the real directory itself, anything
inside it, or any directory that contains it. Inside it would put the demo's
database, settings and lock file among your real data; containing it would make
the `rm -rf` above delete your real data. It compares the two as the filesystem
sees them — `expanduser()` then `resolve()`, the same rule the app applies — so
a `~`, a trailing slash, a doubled slash, a `..` or a symlinked parent will not
slip past, and the check runs before anything is created.


## What the launcher refuses

`./start-demo.sh` exits non-zero, before creating anything, when the demo
directory would overlap the real installation. It checks more than the two
names: a case variant of the real directory is the same directory on a stock
macOS volume, a firmlink path such as
`/System/Volumes/Data/Users/you/Library/...` is the same directory under a
different name, and `/` contains everything. It also refuses a
`getmoredone.db` inside the demo directory that is a symlink pointing out of
it, because the app resolves that link and would write to its target.

It accepts `--print-env`, or no argument at all, and exits 2 on anything else.
A mistyped `--printenv` used to fall through to a full launch.

## Seeding without the GUI

The launcher does this for you on a first run. To do it by hand — after a
reset, or to add another set of samples:

```bash
GETMOREDONE_DATA_DIR="$HOME/Library/Application Support/GetMoreDone-Demo" \
  ./venv/bin/python tools/create_demo_data.py
```

It prints the database it is seeding and the number of items it created. The
same loader sits behind **Settings → Load demo data**, which seeds whichever
database the running instance is using.

## Using another directory

Set `GETMOREDONE_DATA_DIR` yourself and `start-demo.sh` will honour it:

```bash
GETMOREDONE_DATA_DIR=~/demo-data ./start-demo.sh
```

This is also how to run a third instance — a scratch one for a screenshot, say
— without disturbing either of the other two.

## Related

- [DEV_PROD_WORKFLOW.md](DEV_PROD_WORKFLOW.md) — dev vs prod databases, and the
  Gmail importer's own selection rule.
- [spec_2026-11-05_demo_install.md](spec_2026-11-05_demo_install.md) — the
  requirements and their tests.
