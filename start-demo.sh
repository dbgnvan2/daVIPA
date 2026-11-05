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
export GETMOREDONE_DATA_DIR="${GETMOREDONE_DATA_DIR:-$DEFAULT_DEMO_DIR}"

REAL_DATA_DIR="${HOME}/Library/Application Support/GetMoreDone"

if ! mkdir -p "$GETMOREDONE_DATA_DIR" 2>/dev/null; then
    echo "❌ Cannot create the demo data directory:"
    echo "   ${GETMOREDONE_DATA_DIR}"
    exit 1
fi

# Compare the directories as the filesystem sees them, not as they were typed:
# a trailing slash, a "..", a "~" or a symlinked parent would all defeat a
# string comparison, and the thing on the other side of it is 914 real action
# items.
DEMO_CANONICAL="$(cd "$GETMOREDONE_DATA_DIR" && pwd -P)" || exit 1
PROD_CANONICAL="$REAL_DATA_DIR"
if [ -d "$REAL_DATA_DIR" ]; then
    PROD_CANONICAL="$(cd "$REAL_DATA_DIR" && pwd -P)" || exit 1
fi

if [ "$DEMO_CANONICAL" = "$PROD_CANONICAL" ]; then
    echo "❌ GETMOREDONE_DATA_DIR points at the real installation:"
    echo "   ${DEMO_CANONICAL}"
    echo "   The demo must never write there. Unset it to use the default, or"
    echo "   name a different directory."
    exit 1
fi

export GETMOREDONE_DB="${DEMO_CANONICAL}/getmoredone.db"

if [ "${1:-}" = "--print-env" ]; then
    echo "data-dir=${GETMOREDONE_DATA_DIR}"
    echo "db-env=${GETMOREDONE_DB}"
    echo "db=${GETMOREDONE_DB}"
    exit 0
fi

echo "🎭 Starting the daVIPA DEMO instance (your real data is untouched)"
echo "   Data: ${GETMOREDONE_DATA_DIR}"

# Seed only when the demo database does not exist yet. load_demo_data() is
# additive by design, so seeding on every launch would add another set of
# sample items each time.
if [ ! -f "$GETMOREDONE_DB" ]; then
    VENV_PY="$(pwd)/venv/bin/python"
    if [ ! -x "$VENV_PY" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv venv || exit 1
        echo "📥 Installing runtime requirements..."
        export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$(pwd)/.pip-cache}"
        "$VENV_PY" -m pip install -q -r requirements.txt || exit 1
    fi
    echo "🌱 Seeding the demo database..."
    "$VENV_PY" tools/create_demo_data.py || exit 1
fi

# One launcher, one bootstrap: start.sh owns the venv, the requirements and the
# run. It will not touch GETMOREDONE_DB, which is already set.
exec ./start.sh
