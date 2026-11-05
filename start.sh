#!/bin/bash
# daVIPA startup script
#
# Spec: docs/spec_2026-11-05_demo_install.md#d2

# Default to production DB path unless overridden.
#
# GETMOREDONE_DATA_DIR redirects the whole data directory — database, settings,
# app.lock, logs — and paths.py derives the database from it. Forcing the
# production database here would clobber a data-dir-only override, which is how
# a demo instance would end up writing the real data, so this default only
# applies when neither variable is set. With neither set it exports exactly
# what it always has.

# Blank-after-trim counts as unset, which is what paths.py's .strip() does.
# The shell's -z alone does not agree with it: "   " is non-empty here and
# empty there, so this script would skip the production default while
# app_data_dir_path() fell back to production anyway — the app writing the real
# database while this script printed an isolated path.
gmd_trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}

# Resolve a path the way paths.app_data_dir_path() does — expanduser(), then
# resolve() — so that what this script reports and what the app opens are the
# same path. The shell does not expand a "~" inside a variable, and it does not
# collapse "..", a double slash or a symlink; paths.py does all four. Pinned to
# the resolver by tests/test_demo_install.py::test_d2_print_env_matches_the_resolver.
gmd_resolve() {
    python3 -I - "$1" <<'GMD_PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).expanduser().resolve())
GMD_PY
}

GMD_DATA_DIR="$(gmd_trim "${GETMOREDONE_DATA_DIR:-}")"
if [ -n "$GMD_DATA_DIR" ]; then
    GMD_DATA_DIR="$(gmd_resolve "$GMD_DATA_DIR")" || exit 1
fi

if [ -z "${GETMOREDONE_DB:-}" ] && [ -z "$GMD_DATA_DIR" ]; then
    export GETMOREDONE_DB="${HOME}/Library/Application Support/GetMoreDone/getmoredone.db"
fi

# The database that will actually be used, for display and for --print-env.
# Empty GETMOREDONE_DB means paths.py derives it from the data directory.
GMD_DB_RESOLVED="${GETMOREDONE_DB:-}"
if [ -z "$GMD_DB_RESOLVED" ]; then
    GMD_DB_RESOLVED="${GMD_DATA_DIR}/getmoredone.db"
elif [ "${GMD_DB_RESOLVED#*:memory:}" = "$GMD_DB_RESOLVED" ] &&
     [ "${GMD_DB_RESOLVED#*mode=memory}" = "$GMD_DB_RESOLVED" ]; then
    # env_db_path() resolves a file path but passes an in-memory target
    # through untouched, so this mirrors both halves of that rule.
    GMD_DB_RESOLVED="$(gmd_resolve "$GMD_DB_RESOLVED")" || exit 1
fi

# Report the resolution and stop, before any venv, pip, cache-clearing or
# launch work. This is what makes the rule above testable by running the
# script rather than by reading it.
if [ "${1:-}" = "--print-env" ]; then
    echo "data-dir=${GMD_DATA_DIR}"
    echo "db-env=${GETMOREDONE_DB:-}"
    echo "db=${GMD_DB_RESOLVED}"
    exit 0
fi

echo "🚀 Starting daVIPA..."

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Use venv interpreter directly (avoids system Python/pip issues)
VENV_PY="$(pwd)/venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    echo "❌ Virtual environment Python not found at $VENV_PY"
    echo "   Delete ./venv and re-run ./start.sh"
    exit 1
fi
echo "🔧 Using virtual environment: $VENV_PY"

# Install/update requirements. requirements.txt is runtime-only since the
# requirements-dev.txt split, so this no longer greps the test packages out of
# it by name — a third test-only package used to slip straight through that.
echo "📥 Installing runtime requirements..."
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$(pwd)/.pip-cache}"
"$VENV_PY" -m pip install -q -r requirements.txt
PIP_STATUS=$?
if [ $PIP_STATUS -ne 0 ]; then
    echo "❌ Failed to install requirements. Check your network/DNS and try again."
    echo "   Tip: If you are offline, connect to the internet and re-run ./start.sh"
    exit $PIP_STATUS
fi

# Clear Python cache to avoid import issues
echo "🧹 Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "✅ Launching daVIPA..."
if [ -n "$GMD_DATA_DIR" ]; then
    echo "   Data: ${GMD_DATA_DIR}"
fi
echo "   DB: ${GMD_DB_RESOLVED}"
"$VENV_PY" run.py
