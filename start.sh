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

# Resolve a data-directory value exactly as paths.app_data_dir_path() does:
# strip() first, then expanduser(), then resolve(). Prints nothing for a blank
# value, which this script reads as unset.
#
# All three steps have to happen in Python, not in the shell. The strip is the
# one that was wrong: bash's [[:space:]] is not str.strip(), so a value of one
# non-breaking space was non-empty here and empty there — this script skipped
# its production default and printed a path inside the repository checkout,
# while app_data_dir_path() stripped the value away and opened the real
# production directory. The shell also does not expand a "~" inside a
# variable, and does not collapse "..", a doubled slash or a symlink.
#
# Pinned to the resolver by
# tests/test_demo_install.py::test_d2_print_env_matches_the_resolver.
gmd_resolve_dir() {
    python3 -I - "$1" <<'GMD_PY'
import sys
from pathlib import Path

value = sys.argv[1].strip()
print(Path(value).expanduser().resolve() if value else "")
GMD_PY
}

# Resolve a GETMOREDONE_DB value exactly as paths.env_db_path() does: an
# in-memory target passes through untouched, anything else is expanded and
# resolved. The in-memory test is anchored, as _is_memory_db_target's is — an
# unanchored substring test in the shell reported "./dbs/mode=memory/x.db"
# unresolved while the app opened the resolved path.
#
# Pinned to the resolver by
# tests/test_demo_install.py::test_d2_print_env_matches_the_db_resolver.
gmd_resolve_db() {
    python3 -I - "$1" <<'GMD_PY'
import sys
from pathlib import Path

value = sys.argv[1]
low = value.strip().lower()
if (
    low == ":memory:"
    or low.startswith("file::memory:")
    or (low.startswith("file:") and "mode=memory" in low)
):
    print(value)
else:
    print(Path(value).expanduser().resolve())
GMD_PY
}

# Where the installed app keeps its data, by platformdirs' rule for this app,
# transcribed because this runs before the venv exists. Hardcoding the macOS
# path made a Linux `./start.sh` export a database the app would never have
# chosen on its own, so a start.sh launch and a `python run.py` launch on one
# machine used two different databases without saying so. Pinned to
# platformdirs by
# tests/test_demo_install.py::test_d2_the_launchers_agree_with_platformdirs.
gmd_real_data_dir() {
    python3 -I - <<'GMD_PY'
import os
import sys
from pathlib import Path

APP_NAME = "GetMoreDone"
if sys.platform == "darwin":
    print(Path("~/Library/Application Support").expanduser() / APP_NAME)
else:
    base = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    print(Path(base).expanduser() / APP_NAME)
GMD_PY
}

GMD_DATA_DIR="$(gmd_resolve_dir "${GETMOREDONE_DATA_DIR:-}")" || exit 1

if [ -z "${GETMOREDONE_DB:-}" ] && [ -z "$GMD_DATA_DIR" ]; then
    export GETMOREDONE_DB="$(gmd_real_data_dir)/getmoredone.db"
fi

# The database that will actually be used, for display and for --print-env.
# Empty GETMOREDONE_DB means paths.py derives it from the data directory.
GMD_DB_RESOLVED="${GETMOREDONE_DB:-}"
if [ -z "$GMD_DB_RESOLVED" ]; then
    GMD_DB_RESOLVED="${GMD_DATA_DIR}/getmoredone.db"
else
    GMD_DB_RESOLVED="$(gmd_resolve_db "$GMD_DB_RESOLVED")" || exit 1
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
# Forwarded, and exec'd: run.py has its own flags — --selftest is the headless
# CI entry point — and dropping "$@" turned `./start.sh --selftest` into an
# ordinary GUI launch. exec leaves no parent shell alive for the session.
exec "$VENV_PY" run.py "$@"
