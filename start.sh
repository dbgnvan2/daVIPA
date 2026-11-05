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
if [ -z "${GETMOREDONE_DB:-}" ] && [ -z "${GETMOREDONE_DATA_DIR:-}" ]; then
    export GETMOREDONE_DB="${HOME}/Library/Application Support/GetMoreDone/getmoredone.db"
fi

# The database that will actually be used, for display and for --print-env.
# Empty GETMOREDONE_DB means paths.py derives it from the data directory.
GMD_DB_RESOLVED="${GETMOREDONE_DB:-}"
if [ -z "$GMD_DB_RESOLVED" ]; then
    GMD_DB_RESOLVED="${GETMOREDONE_DATA_DIR%/}/getmoredone.db"
fi

# Report the resolution and stop, before any venv, pip, cache-clearing or
# launch work. This is what makes the rule above testable by running the
# script rather than by reading it.
if [ "${1:-}" = "--print-env" ]; then
    echo "data-dir=${GETMOREDONE_DATA_DIR:-}"
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
if [ -n "${GETMOREDONE_DATA_DIR:-}" ]; then
    echo "   Data: ${GETMOREDONE_DATA_DIR}"
fi
echo "   DB: ${GMD_DB_RESOLVED}"
"$VENV_PY" run.py
