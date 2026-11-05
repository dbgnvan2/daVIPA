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

# Reused, not copied: this is the only machinery in the repo that loads the
# root conftest's session hooks into a throwaway pytest run, and a second copy
# would be a second thing to keep in step with those hooks.
from tests.test_settings_isolation import _run_nested_pytest

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


def _resolver_data_dir(monkeypatch, home: Path, value: str) -> Path:
    """What app_data_dir_path() itself returns for `value` under `home`.

    The real function, not a reimplementation of its rule: the whole point of
    the comparison is to catch the launchers' mirror of that rule drifting
    away from it, and a second copy here would drift in step. It does create
    the directory, because that is what app_data_dir_path() does — everything
    it creates is inside the calling test's tmp_path.
    """
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv(DATA_DIR_ENV, value)
    return paths.app_data_dir_path()


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


def test_d1_unset_override_falls_back_to_platformdirs(tmp_path, monkeypatch):
    """With the variable unset, every existing install must be unaffected.

    HOME is redirected because app_data_dir_path() ends in
    ``mkdir(parents=True, exist_ok=True)``. Checking the fallback against the
    user's real location would therefore CREATE that location on a machine
    where the app has never run — which is exactly what
    conftest._user_data_fingerprint's docstring refuses to do. Both sides of
    the comparison read the redirected HOME, so this still proves the
    platformdirs branch is the one taken.
    """
    monkeypatch.delenv(DATA_DIR_ENV, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    expected = Path(user_data_dir(APP_NAME, APP_AUTHOR)).expanduser().resolve()
    resolved = paths.app_data_dir_path()

    assert resolved == expected
    assert resolved.is_relative_to(tmp_path.resolve()), (
        "the fallback escaped the redirected HOME, so this test would create "
        "the user's real data directory"
    )


def test_d1_blank_override_is_ignored(tmp_path, monkeypatch):
    """An exported-but-empty variable must not redirect the app.

    Same rule as GETMOREDONE_RESOURCE_ROOT. Without the strip, a blank value
    would resolve to the process's current directory — the repo, when launched
    from source — and the app would quietly write its data into the checkout.
    """
    monkeypatch.setenv(DATA_DIR_ENV, "   ")
    monkeypatch.setenv("HOME", str(tmp_path))

    expected = Path(user_data_dir(APP_NAME, APP_AUTHOR)).expanduser().resolve()
    resolved = paths.app_data_dir_path()

    assert resolved == expected
    assert resolved.is_relative_to(tmp_path.resolve()), (
        "same reason as the unset case: this must not create the real directory"
    )


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


def test_d1_the_suite_runs_with_no_data_dir_override(tmp_path):
    """conftest drops an ambient override for the whole session.

    Both live-data guards compute the real directory from platformdirs, so an
    exported override would leave app_data_dir_path() pointing at the demo
    directory while the guards watched one nothing touched — isolation
    reported rather than enforced.

    This has to run the hooks under an override that is actually set. Asserting
    ``os.environ.get(DATA_DIR_ENV) is None`` in this process proved nothing:
    it is true in any shell that never exported the variable, and in CI, so it
    stayed green with the pop deleted. The nested-run helper is reused rather
    than copied so there is one implementation of "load the root conftest's
    session hooks into a throwaway run".
    """
    result = _run_nested_pytest(
        tmp_path,
        """
        import os

        def test_probe():
            assert os.environ.get("GETMOREDONE_DATA_DIR") is None, (
                "pytest_sessionstart did not drop the ambient override")
        """,
        env_extra={DATA_DIR_ENV: str(tmp_path / "ambient-demo")},
    )

    assert result.returncode == 0, (
        "the session hooks did not drop an exported GETMOREDONE_DATA_DIR:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_d1_the_session_restores_the_override_afterwards(tmp_path):
    """The pop is scoped to the session, not a permanent deletion.

    pytest_sessionfinish puts the value back, so an in-process caller that
    runs pytest.main() and then does other work still has its environment.
    """
    result = _run_nested_pytest(
        tmp_path,
        """
        def test_probe():
            assert True
        """,
        env_extra={DATA_DIR_ENV: str(tmp_path / "ambient-demo")},
    )

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


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


def test_d2_start_sh_treats_a_blank_data_dir_as_unset(tmp_path):
    """The shell and paths.py must agree on what "blank" means.

    They did not: the shell's -z is false for "   ", so start.sh skipped its
    production default, while paths.py strips the value and fell back to
    production anyway. The app opened the real database while the launcher
    printed an isolated path. Pairs with
    test_d1_blank_override_is_ignored, which fixes the Python half.
    """
    values = _parsed(_print_env("start.sh", tmp_path, GETMOREDONE_DATA_DIR="   "))

    expected = tmp_path / "Library/Application Support/GetMoreDone/getmoredone.db"
    assert values["data-dir"] == ""
    assert values["db-env"] == str(expected), (
        "start.sh skipped its production default for a blank data directory, "
        "which paths.py then resolved to production regardless"
    )
    assert values["db"] == str(expected)


def test_d2_demo_launcher_ignores_a_blank_data_dir(tmp_path):
    """A blank override falls back to the default, not to a directory of spaces.

    ``${VAR:-default}`` keeps "   ", and the launcher would then `mkdir -p` a
    whitespace-named directory in the repository.
    """
    values = _parsed(_print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR="  "))

    expected = tmp_path.resolve() / "Library/Application Support/GetMoreDone-Demo"
    assert Path(values["data-dir"]) == expected


def test_d2_demo_launcher_reports_one_canonical_directory(tmp_path):
    """Both variables must name the same spelling of the same directory.

    The data directory was exported raw while the database was derived from
    the canonicalised path, so --print-env could report two paths for one
    directory — and DEMO_INSTALL.md tells the reader to delete the one named
    first.
    """
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)

    values = _parsed(_print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(link)))

    assert Path(values["data-dir"]) == real.resolve()
    assert Path(values["db"]).parent == Path(values["data-dir"])


# The seeding step runs only on a first launch, against the repository's own
# venv, so no test can reach it without building a venv or writing to this
# checkout's. This is the source-text guard the repo's rules allow where no
# behavioural check is practical: anchored to whole lines, asserting an exact
# count and an exact indentation.
PIP_INSTALL_LINE = re.compile(
    r"^(?P<indent> *)\"\$VENV_PY\" -m pip install -q -r requirements\.txt \|\| exit 1$",
    re.MULTILINE,
)
SEED_LINE = re.compile(
    r"^(?P<indent> *)\"\$VENV_PY\" tools/create_demo_data\.py \|\| exit 1$",
    re.MULTILINE,
)


def test_d2_demo_launcher_installs_requirements_before_seeding():
    """The install must not be nested inside the "create the venv" branch.

    It was, so a venv that existed but lacked a runtime dependency made the
    seed raise ModuleNotFoundError and took the launch down with it — where
    plain start.sh would have installed the dependency and started the app.
    Indentation is the structure here: 4 spaces is the seeding block, 8 would
    be back inside the venv-creation branch.
    """
    script = (REPO_ROOT / "start-demo.sh").read_text(encoding="utf-8")
    installs = list(PIP_INSTALL_LINE.finditer(script))
    seeds = list(SEED_LINE.finditer(script))

    assert len(installs) == 1, (
        f"expected exactly one requirements install in start-demo.sh, found "
        f"{len(installs)}"
    )
    assert len(seeds) == 1, (
        f"expected exactly one seeding call in start-demo.sh, found {len(seeds)}"
    )
    assert len(installs[0].group("indent")) == 4, (
        f"the requirements install is indented "
        f"{len(installs[0].group('indent'))} spaces, so it is nested inside "
        "the venv-creation branch and will not run for a venv that already "
        "exists"
    )
    assert installs[0].start() < seeds[0].start(), (
        "the requirements install comes after the seeding call, so the seed "
        "runs before its dependencies are installed — which is the failure "
        "this guard exists to catch, and indentation alone does not catch it"
    )


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


def test_d2_demo_launcher_refuses_a_directory_inside_the_real_one(tmp_path):
    """Containment, not just equality.

    ".../GetMoreDone/demo" passed the old equality test, and a launch then put
    the demo's database, settings, app.lock and log INSIDE the real
    installation — the one thing this feature must never do.
    """
    real = tmp_path / "Library/Application Support/GetMoreDone"
    real.mkdir(parents=True)

    result = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(real / "demo"))

    assert result.returncode != 0, (
        f"a demo directory inside the real one was accepted:\n{result.stdout}")
    assert "is inside" in result.stdout
    assert list(real.iterdir()) == [], (
        "the refused run still created something inside the real directory")


def test_d2_demo_launcher_refuses_a_directory_containing_the_real_one(tmp_path):
    """The other direction matters because of the documented reset.

    DEMO_INSTALL.md tells the reader to delete the demo directory, so a demo
    directory that contained the real one would turn that instruction into
    data loss.
    """
    support = tmp_path / "Library/Application Support"
    (support / "GetMoreDone").mkdir(parents=True)

    result = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(support))

    assert result.returncode != 0, (
        f"a demo directory containing the real one was accepted:\n{result.stdout}")
    assert "contains" in result.stdout


def test_d2_print_env_creates_nothing(tmp_path):
    """DEMO_INSTALL.md calls --print-env a way to look without launching.

    The mkdir used to run before the guard, so merely asking what would be
    used created directories — including under the protected path when the
    answer was going to be a refusal.
    """
    result = _print_env("start-demo.sh", tmp_path)

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "Library").exists(), (
        "--print-env created the data directory it only promised to describe")


def test_d2_refusal_creates_nothing_under_the_real_path(tmp_path):
    """A refused run must not be the thing that brings the real path into being.

    With the mkdir first, pointing the demo at a not-yet-existing real
    directory created that directory and *then* refused.
    """
    target = tmp_path / "Library/Application Support/GetMoreDone"

    result = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=f"{target}/")

    assert result.returncode != 0, result.stdout
    assert not target.exists(), (
        "the refused run created the real data directory before refusing it")


def test_d2_demo_launcher_expands_a_tilde(tmp_path):
    """The shell does not expand a "~" inside a variable; paths.py does.

    `GETMOREDONE_DATA_DIR='~/demo'` (quoted, or read from a plist) made the
    launcher create a literal "~" directory in the repository checkout while
    the app opened $HOME/demo.
    """
    values = _parsed(_print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR="~/demo-tilde"))

    assert Path(values["data-dir"]) == (tmp_path / "demo-tilde").resolve()
    assert not (REPO_ROOT / "~").exists(), (
        "a literal '~' directory was created in the repository")


def test_d2_print_env_matches_the_resolver(tmp_path, monkeypatch):
    """--print-env is the oracle every D2 test uses, so it must not drift.

    Both launchers resolve a path themselves rather than importing paths.py,
    which cannot be imported before the venv exists. This pins the two
    implementations together over the awkward spellings — a tilde, a trailing
    slash, a doubled slash, a "..", and a symlinked parent — so a change to
    app_data_dir_path() that this mirror does not follow turns the suite red.
    """
    link_target = tmp_path / "actual"
    link_target.mkdir()
    (tmp_path / "linked").symlink_to(link_target)

    spellings = [
        "~/demo",
        str(tmp_path / "demo") + "/",
        str(tmp_path) + "//demo",
        str(tmp_path / "a" / ".." / "demo"),
        str(tmp_path / "linked" / "demo"),
    ]

    for spelling in spellings:
        values = _parsed(_print_env("start.sh", tmp_path, GETMOREDONE_DATA_DIR=spelling))
        expected = _resolver_data_dir(monkeypatch, tmp_path, spelling)
        assert Path(values["data-dir"]) == expected, (
            f"start.sh resolved {spelling!r} to {values['data-dir']!r}, but "
            f"app_data_dir_path() resolves it to {expected}"
        )
        assert Path(values["db"]) == expected / "getmoredone.db"


def test_d2_demo_launcher_reseeds_a_database_with_no_items(tmp_path):
    """An interrupted first seed must not permanently disable seeding.

    load_demo_data() creates the file and runs migrations before inserting
    anything, and has no except clause, so an interruption leaves the file
    present with no items. Keying on the file alone meant run 1 failed loudly
    and every run after it launched an empty demo in silence.
    """
    demo = tmp_path / "demo"
    demo.mkdir()
    db = demo / "getmoredone.db"

    absent = _parsed(_print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(demo)))
    assert absent["seed"] == "yes", "a missing database must be seeded"

    # A file that exists but carries no schema at all: the earliest point an
    # interruption can leave it.
    db.write_bytes(b"")
    assert _parsed(
        _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(demo))
    )["seed"] == "yes", "an unreadable database must be re-seeded, not skipped"

    # Migrated but empty: the interruption landed after DatabaseManager ran
    # and before the first insert.
    _seed(demo)
    seeded = _row_count(db)
    assert seeded > 0, "the seeding helper did not insert anything"
    assert _parsed(
        _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(demo))
    )["seed"] == "no", "a demo that already holds items must not be re-seeded"

    conn = sqlite3.connect(db)
    try:
        conn.execute("delete from action_items")
        conn.commit()
    finally:
        conn.close()
    assert _parsed(
        _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(demo))
    )["seed"] == "yes", "a migrated but empty database must be seeded"

