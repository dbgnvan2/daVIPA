"""The demo installation is isolated from the real one.

Purpose: prove that a second instance keeps its own database, settings, lock
         and logs, and that the real installation is never resolved or written.
Spec:    docs/spec_2026-11-05_demo_install.md
Tests:   this file

These exercise the real launchers and the real seeding script as subprocesses
rather than asserting on their text. `--print-env` exists on both scripts for
that reason: a grep would pass on a script whose resolution order was broken.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from platformdirs import user_data_dir

from src.getmoredone import paths
from src.getmoredone.paths import APP_AUTHOR, APP_NAME

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR_ENV = "GETMOREDONE_DATA_DIR"
DB_ENV = "GETMOREDONE_DB"


def _real_data_dir() -> Path:
    """The user's actual data directory, computed without app_data_dir_path().

    Same reasoning as conftest: going through the production resolver would
    make the guard agree with whatever the resolver currently believes, which
    is the thing under test.
    """
    return Path(user_data_dir(APP_NAME, APP_AUTHOR)).expanduser().resolve()


def _child_env(home: Path, **overrides: str | None) -> dict[str, str]:
    """A subprocess environment with both path variables under our control.

    The suite's own ``GETMOREDONE_DB`` (set in ``pytest_sessionstart``) would
    otherwise be inherited and outrank the data directory, so every test here
    would be measuring that variable instead of the one it names.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.pop(DB_ENV, None)
    env.pop(DATA_DIR_ENV, None)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def _print_env(script: str, home: Path, **overrides: str | None):
    """Run a launcher's ``--print-env`` and return the CompletedProcess."""
    return subprocess.run(
        ["bash", str(REPO_ROOT / script), "--print-env"],
        cwd=str(REPO_ROOT),
        env=_child_env(home, **overrides),
        capture_output=True,
        text=True,
        timeout=60,
    )


def _parsed(result) -> dict[str, str]:
    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            values[key] = value
    return values


def _row_count(db_path: Path) -> int:
    """action_items in a database, with the connection closed again.

    ``with sqlite3.connect(...)`` commits but does not close, and conftest
    fails a test that leaves a connection open.
    """
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("select count(*) from action_items").fetchone()[0]
    finally:
        conn.close()


def _fingerprint(path: Path) -> tuple:
    """(exists, size, sha256) — enough to catch any write to a real file."""
    if not path.exists():
        return (False, 0, "")
    data = path.read_bytes()
    return (True, len(data), hashlib.sha256(data).hexdigest())


# --------------------------------------------------------------------------
# D1 — the data directory override
# --------------------------------------------------------------------------

def test_d1_data_dir_override_redirects_db_and_settings(tmp_path, monkeypatch):
    """One override has to move the database AND the settings file.

    GETMOREDONE_DB moved only the first, which is what left a second instance
    sharing the real theme, Obsidian vault path and Gmail trigger label.
    """
    demo = tmp_path / "GetMoreDone-Demo"
    monkeypatch.setenv(DATA_DIR_ENV, str(demo))

    assert paths.app_data_dir_path() == demo.resolve()
    assert paths.default_db_path() == demo.resolve() / "getmoredone.db"
    assert paths.default_settings_path() == demo.resolve() / "settings.json"
    assert demo.is_dir(), "the override must create the directory, as the default does"


def test_d1_unset_override_falls_back_to_platformdirs(monkeypatch):
    """With the variable unset, every existing install must be unaffected."""
    monkeypatch.delenv(DATA_DIR_ENV, raising=False)

    assert paths.app_data_dir_path() == _real_data_dir()


def test_d1_blank_override_is_ignored(monkeypatch):
    """An exported-but-empty variable must not redirect the app.

    Same rule as GETMOREDONE_RESOURCE_ROOT. Without the strip, a blank value
    would resolve to the process's current directory — the repo, when launched
    from source — and the app would quietly write its data into the checkout.
    """
    monkeypatch.setenv(DATA_DIR_ENV, "   ")

    assert paths.app_data_dir_path() == _real_data_dir()


def test_d1_override_is_expanded_and_resolved(tmp_path, monkeypatch):
    """A tilde and a '..' in the value must behave as the user means them."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(DATA_DIR_ENV, "~/demo")
    assert paths.app_data_dir_path() == (tmp_path / "demo").resolve()

    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path / "a" / ".." / "a" / "b"))
    assert paths.app_data_dir_path() == nested.resolve()


def test_d1_explicit_db_env_var_outranks_the_data_dir(tmp_path, monkeypatch):
    """GETMOREDONE_DB wins, and the data directory still sets the default.

    start-demo.sh sets both, and the Gmail importer's documented dev recipe
    sets only the first, so the order between them is load-bearing rather than
    academic.
    """
    demo = tmp_path / "demo"
    chosen = tmp_path / "explicit" / "chosen.db"
    chosen.parent.mkdir(parents=True)
    monkeypatch.setenv(DATA_DIR_ENV, str(demo))
    monkeypatch.setenv(DB_ENV, str(chosen))

    assert paths.resolve_db_path() == chosen.resolve()
    assert paths.default_db_path() == demo.resolve() / "getmoredone.db"


def test_d1_the_suite_runs_with_no_data_dir_override():
    """conftest drops an ambient override for the whole session.

    Both live-data guards compute the real directory from platformdirs, so an
    exported override would send the app into the demo directory while the
    guards watched one nothing touched — isolation reported, not enforced.
    """
    assert os.environ.get(DATA_DIR_ENV) is None, (
        "GETMOREDONE_DATA_DIR survived into the test session; the guards in "
        "conftest.py are no longer watching the directory the app resolves"
    )


# --------------------------------------------------------------------------
# D2 — the launchers
# --------------------------------------------------------------------------

def test_d2_demo_launcher_resolves_the_demo_data_dir(tmp_path):
    """The demo defaults to GetMoreDone-Demo, never the real directory."""
    result = _print_env("start-demo.sh", tmp_path)

    assert result.returncode == 0, result.stderr
    values = _parsed(result)
    expected = tmp_path.resolve() / "Library/Application Support/GetMoreDone-Demo"
    assert Path(values["data-dir"]) == expected
    assert not Path(values["db"]).is_relative_to(_real_data_dir())


def test_d2_demo_launcher_exports_an_explicit_db_path(tmp_path):
    """Both variables are set, so start.sh's default can never fire.

    A data-dir-only demo used to fall straight through start.sh's
    unconditional production default — the pitfall this deliverable exists to
    close.
    """
    values = _parsed(_print_env("start-demo.sh", tmp_path))

    assert values["db-env"], "the demo must export GETMOREDONE_DB explicitly"
    assert Path(values["db-env"]).parent == Path(values["data-dir"])
    assert values["db"] == values["db-env"]


def test_d2_demo_launcher_refuses_the_real_data_dir(tmp_path):
    """Hand-pointing the demo at the real installation must stop it.

    The trailing slash matters: the launcher canonicalises both sides, because
    a string comparison would pass a path that differs only in punctuation and
    the directory on the other side holds the user's real items.
    """
    real = tmp_path / "Library/Application Support/GetMoreDone"
    real.mkdir(parents=True)

    result = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=f"{real}/")

    assert result.returncode != 0, result.stdout
    assert str(real.resolve()) in result.stdout


def test_d2_start_sh_default_db_follows_the_data_dir_override(tmp_path):
    """start.sh must not force the production DB over a data-dir override."""
    demo = tmp_path / "Demo"
    values = _parsed(_print_env("start.sh", tmp_path, GETMOREDONE_DATA_DIR=str(demo)))

    assert values["db-env"] == "", (
        "start.sh exported GETMOREDONE_DB over a data-dir override, which "
        "sends the demo back to the production database"
    )
    assert Path(values["db"]) == demo / "getmoredone.db"


def test_d2_start_sh_default_db_is_unchanged_with_no_env(tmp_path):
    """With neither variable set, the exported path is what it has always been."""
    values = _parsed(_print_env("start.sh", tmp_path))

    expected = tmp_path / "Library/Application Support/GetMoreDone/getmoredone.db"
    assert values["db-env"] == str(expected)
    assert values["db"] == str(expected)
    assert values["data-dir"] == ""


def test_d2_launchers_are_valid_bash():
    """A launcher with a syntax error fails at the user, not in CI."""
    for script in ("start.sh", "start-demo.sh"):
        result = subprocess.run(
            ["bash", "-n", str(REPO_ROOT / script)],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"{script}: {result.stderr}"


# --------------------------------------------------------------------------
# D3 / D4 — the headless seed
# --------------------------------------------------------------------------

def _seed(demo_dir: Path):
    return subprocess.run(
        [sys.executable, "tools/create_demo_data.py"],
        cwd=str(REPO_ROOT),
        env=_child_env(demo_dir.parent, GETMOREDONE_DATA_DIR=str(demo_dir)),
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_d3_create_demo_data_runs_against_an_isolated_db(tmp_path):
    """The tool put tools/src on sys.path, so it could not import at all.

    README.md and CLAUDE.md both tell the reader to run it, and start-demo.sh
    now does too, so "it imports and seeds the database it names" is the whole
    of its contract.
    """
    demo = tmp_path / "demo"
    result = _seed(demo)

    assert result.returncode == 0, result.stderr
    assert str(demo.resolve() / "getmoredone.db") in result.stdout

    reported = re.search(r"\((\d+) items\)", result.stdout)
    assert reported, f"no item count reported: {result.stdout}"

    rows = _row_count(demo / "getmoredone.db")
    assert rows == int(reported.group(1))
    assert rows > 0


def test_d4_seed_writes_only_into_the_target_database(tmp_path):
    """Seeding a demo directory leaves the real files byte-identical.

    The session-wide fingerprint in conftest would catch this too, but after
    the run and naming a file rather than a test. This names the test.
    """
    real_dir = _real_data_dir()
    before = {
        name: _fingerprint(real_dir / name)
        for name in ("getmoredone.db", "settings.json")
    }

    demo = tmp_path / "demo"
    result = _seed(demo)
    assert result.returncode == 0, result.stderr

    after = {
        name: _fingerprint(real_dir / name)
        for name in ("getmoredone.db", "settings.json")
    }
    assert after == before, "seeding the demo changed a file in the real data directory"

    rows = _row_count(demo / "getmoredone.db")
    assert rows > 0, "nothing was seeded into the demo database"
