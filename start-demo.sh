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

# A typo used to fall through to a full launch. "--printenv" matched nothing,
# so the one command documented to touch nothing did a mkdir, a pip install
# and a seed.
case "${1:-}" in
    ""|--print-env) ;;
    *)
        echo "❌ Unknown argument: $1"
        echo "   Usage: ./start-demo.sh [--print-env]"
        echo "   --print-env reports where the demo would write and exits"
        echo "   without creating anything."
        exit 2
        ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 is required (to check where the demo would write, and to"
    echo "   create the virtual environment). Install it and re-run."
    exit 1
fi

# The whole preflight in one Python program, because every rule it applies is
# paths.py's rule and the shell could not apply any of them the same way.
# Four separate defects came out of trying:
#
#   - `[[:space:]]` is not str.strip(). A value of one non-breaking space is
#     blank to Python and not to the shell, so start.sh printed a path in the
#     repository checkout while app_data_dir_path() stripped the value to
#     nothing and opened the real production directory.
#   - String comparison is not directory identity. macOS volumes are
#     case-insensitive by default, so ".../getmoredone" and ".../GetMoreDone"
#     are one directory and two strings; and resolve() collapses neither case
#     nor a firmlink prefix like /System/Volumes/Data. Both spellings walked
#     past a guard that compared the two canonical strings.
#   - "$DIR"/* is not containment when $DIR is "/". The pattern became "//*",
#     which matches nothing, so the one directory that contains everything was
#     the one directory the guard accepted — and DEMO_INSTALL.md then tells
#     the reader to `rm -rf` what it printed.
#   - An f-string is not a URI. A "?" in the demo path truncated the SQLite
#     URI and took `mode=ro` with it, so reading the item count created a file
#     during --print-env; a "%" made the path decode to one that does not
#     exist, so seed=yes stuck and every launch added six more items.
#
# It runs before any mkdir, so it cannot use `cd … && pwd -P`: that needs the
# directory to exist, and creating a directory to find out whether it is
# allowed is the defect this replaces. Path.resolve() is non-strict — it
# resolves what symlinks it can and leaves the rest absolute — so both sides
# are comparable whether or not they exist.
#
# Prints data-dir, db, seed and reason on success; prints the refusal and
# exits 1 otherwise.
gmd_preflight() {
    python3 -I - <<'GMD_PY'
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

APP_NAME = "GetMoreDone"


def real_data_dir():
    """Where the installed app keeps the user's data.

    platformdirs' rule for this app, transcribed rather than imported: on a
    first launch the venv does not exist yet, so neither platformdirs nor
    paths.py can be imported here. Hardcoding the macOS path instead meant
    that on Linux the guard below protected a directory the app never uses,
    leaving the real ~/.local/share/GetMoreDone open to being seeded. Pinned
    to platformdirs by
    tests/test_demo_install.py::test_d2_the_launchers_agree_with_platformdirs.
    """
    if sys.platform == "darwin":
        return Path("~/Library/Application Support") / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or "~/.local/share"
    return Path(base) / APP_NAME


def canonical(value):
    """expanduser() then resolve(), exactly as app_data_dir_path() does."""
    return Path(value).expanduser().resolve()


def identity(path):
    """(st_dev, st_ino), or None when the path does not exist."""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def within(inner, outer):
    """True when the string `inner` is `outer` or sits beneath it."""
    return inner == outer or inner.startswith(outer.rstrip("/") + "/")


def overlaps(inner, outer):
    """True when `inner` is `outer` or lies beneath it.

    Three tests, because one name is not one directory:

      - by name, which is the only test available for the components that do
        not exist yet;
      - by name case-folded, because macOS volumes are case-insensitive by
        default and resolve() case-folds nothing, so ".../getmoredone" and
        ".../GetMoreDone" are one directory and two strings. This may refuse
        a genuinely distinct directory on a case-sensitive volume, which
        costs the user a rename; the other direction costs them their data;
      - by identity, for a second name that survives resolve() — a firmlink
        prefix such as /System/Volumes/Data. This one can only speak for
        paths that exist.
    """
    inner_s, outer_s = str(inner), str(outer)
    if within(inner_s, outer_s) or within(inner_s.casefold(), outer_s.casefold()):
        return True
    outer_id = identity(outer)
    if outer_id is None:
        return False
    for candidate in (inner, *inner.parents):
        if identity(candidate) == outer_id:
            return True
    return False


def refuse(reason, demo, real, detail=None):
    print("❌ GETMOREDONE_DATA_DIR %s:" % reason)
    print("   demo: %s" % demo)
    print("   real: %s" % real)
    if detail:
        print("   %s" % detail)
    print("   The demo must never write there. Unset it to use the default,")
    print("   or name a directory outside the real one.")
    raise SystemExit(1)


def item_count(db):
    """action_items in the demo database: -1 when it cannot be read.

    -1 is what an interrupted first seed leaves behind — the file exists,
    created by DatabaseManager's migrations, with no such table yet.
    """
    uri = "file:" + urllib.request.pathname2url(str(db)) + "?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True)
        try:
            return con.execute("select count(*) from action_items").fetchone()[0]
        finally:
            con.close()
    except Exception:
        return -1


real = canonical(real_data_dir())
raw = (os.environ.get("GETMOREDONE_DATA_DIR") or "").strip()
demo = canonical(raw) if raw else real.parent / (APP_NAME + "-Demo")

if demo == Path(demo.anchor):
    refuse("names the filesystem root", demo, real)
if any(ch in str(demo) for ch in "\n\r"):
    refuse("contains a newline", demo, real,
           "No line of this report, and no test that parses it, could carry it.")
if overlaps(demo, real):
    refuse("is inside the real installation", demo, real)
if overlaps(real, demo):
    refuse("contains the real installation", demo, real)

db = canonical(demo / "getmoredone.db")
if not (db.parent == demo or demo in db.parents):
    refuse("has a database that resolves outside it", demo, real,
           "db: %s — a symlink there would send every write to its target."
           % db)

if not db.is_file():
    seed, reason = "yes", "no demo database yet"
else:
    items = item_count(db)
    if items <= 0:
        seed, reason = "yes", (
            "the demo database holds no items, so an earlier seed did not "
            "finish")
    else:
        seed, reason = "no", ""

print("data-dir=%s" % demo)
print("db=%s" % db)
print("seed=%s" % seed)
print("reason=%s" % reason)
GMD_PY
}

# Seed when there is nothing seeded — judged by the rows, not by the file.
# load_demo_data() opens a DatabaseManager, which creates the file and runs
# migrations before it inserts anything, so keying on the file alone meant one
# interrupted seed left every later launch opening an empty demo in silence.
# load_demo_data() is additive, which is why a demo that does hold items is
# left alone. Decided in the preflight, above --print-env, so the decision can
# be inspected without launching: it reads the database, and only the block
# further down writes.
if ! GMD_PLAN="$(gmd_preflight)"; then
    printf '%s\n' "$GMD_PLAN"
    exit 1
fi

{
    IFS= read -r GMD_LINE_DIR
    IFS= read -r GMD_LINE_DB
    IFS= read -r GMD_LINE_SEED
    IFS= read -r GMD_LINE_REASON
} <<GMD_PLAN_EOF
$GMD_PLAN
GMD_PLAN_EOF

export GETMOREDONE_DATA_DIR="${GMD_LINE_DIR#data-dir=}"
export GETMOREDONE_DB="${GMD_LINE_DB#db=}"
GMD_SEED="${GMD_LINE_SEED#seed=}"
GMD_SEED_REASON="${GMD_LINE_REASON#reason=}"

# Report the resolution and stop — before the mkdir, so that this really does
# show what would be used without touching the filesystem, as the docs say.
if [ "${1:-}" = "--print-env" ]; then
    echo "data-dir=${GETMOREDONE_DATA_DIR}"
    echo "db-env=${GETMOREDONE_DB}"
    echo "db=${GETMOREDONE_DB}"
    echo "seed=${GMD_SEED}"
    exit 0
fi

# mkdir's own stderr is left alone: "Not a directory" and "Permission denied"
# are the only things that tell these two cases apart, and the line below
# names neither.
if ! mkdir -p "$GETMOREDONE_DATA_DIR"; then
    echo "❌ Cannot create the demo data directory:"
    echo "   ${GETMOREDONE_DATA_DIR}"
    exit 1
fi

echo "🎭 Starting the daVIPA DEMO instance (your real data is untouched)"
echo "   Data: ${GETMOREDONE_DATA_DIR}"

if [ "$GMD_SEED" = "yes" ]; then
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
