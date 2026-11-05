#!/bin/bash
# daVIPA demo launcher — a second, fully isolated instance.
#
# Spec: docs/spec_2026-11-05_demo_install.md#d2
# Docs: docs/DEMO_INSTALL.md
#
# Everything this instance writes — the database, settings.json, app.lock and
# weekly_tactic_debug.log — hangs off GETMOREDONE_DATA_DIR, because all four
# resolve through paths.app_data_dir_path(). app.lock is the reason the
# directory has to move rather than just the database: the installed app holds
# an exclusive flock on it, so an instance sharing that directory is refused at
# launch rather than merely sharing a theme.
#
# Both variables are set explicitly. GETMOREDONE_DB alone would leave the
# settings shared; GETMOREDONE_DATA_DIR alone used to be clobbered by start.sh's
# production default, which is now data-dir aware as well.

set -u

cd "$(dirname "$0")" || exit 1

DEFAULT_DEMO_DIR="${HOME}/Library/Application Support/GetMoreDone-Demo"
REAL_DATA_DIR="${HOME}/Library/Application Support/GetMoreDone"

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 is required (to check where the demo would write, and to"
    echo "   create the virtual environment). Install it and re-run."
    exit 1
fi

# Blank-after-trim falls back to the default, as paths.py's .strip() does.
# Without it, GETMOREDONE_DATA_DIR="   " would survive ${VAR:-default} and
# a directory named of spaces would be created in the repo.
gmd_trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

# Resolve a path exactly as paths.app_data_dir_path() does — expanduser(), then
# resolve() — and WITHOUT creating anything.
#
# The guard below has to run before any mkdir, so it cannot use
# `cd … && pwd -P`: that needs the directory to already exist, and creating a
# directory in order to find out whether it is allowed is precisely the defect
# this replaces. It also made the guard one-sided, because the real directory
# was canonicalised only `if [ -d ]`.
#
# Path.resolve() is non-strict: it resolves the symlinks it can and leaves the
# rest absolute, so both sides are comparable whether or not they exist. It is
# also what expands a "~" — the shell does not expand one inside a variable,
# so `mkdir -p "~/demo"` used to create a literal "~" directory in the repo
# while paths.py opened $HOME/demo. Same class as the blank-value rule above:
# the shell and paths.py have to agree on what a value means.
gmd_resolve() {
    python3 -I - "$1" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).expanduser().resolve())
PY
}

# How many action items the demo database holds: -1 if it cannot be read or
# has no such table, which is what an interrupted first seed leaves behind.
gmd_item_count() {
    python3 -I - "$1" <<'PY'
import sqlite3
import sys

try:
    con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
    try:
        print(con.execute("select count(*) from action_items").fetchone()[0])
    finally:
        con.close()
except Exception:
    print(-1)
PY
}

GMD_DEMO_DIR="$(gmd_trim "${GETMOREDONE_DATA_DIR:-}")"
if [ -z "$GMD_DEMO_DIR" ]; then
    GMD_DEMO_DIR="$DEFAULT_DEMO_DIR"
fi

DEMO_CANONICAL="$(gmd_resolve "$GMD_DEMO_DIR")" || exit 1
PROD_CANONICAL="$(gmd_resolve "$REAL_DATA_DIR")" || exit 1

# Refuse any overlap, in either direction, not just an exact match.
#
# Nested-inside was accepted until now: GETMOREDONE_DATA_DIR pointing at
# ".../GetMoreDone/demo" passed the equality test, and a launch then wrote the
# demo's database, settings, app.lock and log inside the real installation —
# the one thing this feature must never do.
#
# The reverse direction matters because of the reset recipe: DEMO_INSTALL.md
# tells the reader to `rm -rf` the demo directory, so a demo directory that
# contained the real one would turn that instruction into data loss.
#
# A trailing "/" on the left and "/*" on the right also makes this catch the
# exact match, so one test covers equality and containment together.
gmd_refuse() {
    echo "❌ GETMOREDONE_DATA_DIR $1 the real installation:"
    echo "   demo: ${DEMO_CANONICAL}"
    echo "   real: ${PROD_CANONICAL}"
    echo "   The demo must never write there. Unset it to use the default, or"
    echo "   name a directory outside the real one."
    exit 1
}
case "${DEMO_CANONICAL}/" in
    "${PROD_CANONICAL}"/*) gmd_refuse "is inside" ;;
esac
case "${PROD_CANONICAL}/" in
    "${DEMO_CANONICAL}"/*) gmd_refuse "contains" ;;
esac

export GETMOREDONE_DATA_DIR="$DEMO_CANONICAL"
export GETMOREDONE_DB="${DEMO_CANONICAL}/getmoredone.db"

# Seed when there is nothing seeded — judged by the rows, not by the file.
#
# load_demo_data() opens a DatabaseManager, which creates the file and runs
# migrations, before it inserts anything, and it has no except clause. So a
# seed interrupted part-way leaves the file present with no items; keying on
# the file alone meant run 1 failed loudly and every run after it launched an
# empty demo silently. load_demo_data() is additive, which is why a demo that
# does hold items is left alone.
#
# Decided here, above --print-env, so the decision can be inspected without
# launching. Deciding reads the database; only the block further down writes.
GMD_NEEDS_SEED=0
GMD_SEED_REASON=""
if [ ! -f "$GETMOREDONE_DB" ]; then
    GMD_NEEDS_SEED=1
    GMD_SEED_REASON="no demo database yet"
else
    GMD_ITEMS="$(gmd_item_count "$GETMOREDONE_DB")"
    if [ "${GMD_ITEMS:-0}" -le 0 ]; then
        GMD_NEEDS_SEED=1
        GMD_SEED_REASON="the demo database holds no items, so an earlier seed did not finish"
    fi
fi

# Report the resolution and stop — before the mkdir, so that this really does
# show what would be used without touching the filesystem, as the docs say.
if [ "${1:-}" = "--print-env" ]; then
    echo "data-dir=${GETMOREDONE_DATA_DIR}"
    echo "db-env=${GETMOREDONE_DB}"
    echo "db=${GETMOREDONE_DB}"
    if [ "$GMD_NEEDS_SEED" -eq 1 ]; then
        echo "seed=yes"
    else
        echo "seed=no"
    fi
    exit 0
fi

if ! mkdir -p "$GETMOREDONE_DATA_DIR" 2>/dev/null; then
    echo "❌ Cannot create the demo data directory:"
    echo "   ${GETMOREDONE_DATA_DIR}"
    exit 1
fi

echo "🎭 Starting the daVIPA DEMO instance (your real data is untouched)"
echo "   Data: ${GETMOREDONE_DATA_DIR}"

if [ "$GMD_NEEDS_SEED" -eq 1 ]; then
    echo "ℹ️  Seeding: ${GMD_SEED_REASON}."
    VENV_PY="$(pwd)/venv/bin/python"
    if [ ! -x "$VENV_PY" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv || exit 1
    fi
    # Unconditionally, not only for a venv this script just created. A venv
    # that exists but is missing a runtime dependency — an interrupted first
    # launch, or a package added to requirements.txt since — made the seed
    # below raise ModuleNotFoundError and took the whole launch down with it,
    # where plain start.sh would have installed the dependency and started.
    echo "📥 Installing runtime requirements..."
    export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$(pwd)/.pip-cache}"
    "$VENV_PY" -m pip install -q -r requirements.txt || exit 1
    echo "🌱 Seeding the demo database..."
    "$VENV_PY" tools/create_demo_data.py || exit 1
fi

# One launcher, one bootstrap: start.sh owns the venv, the requirements and the
# run. It will not touch GETMOREDONE_DB, which is already set.
exec ./start.sh
