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
from types import SimpleNamespace

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


def _real_data_dir_for(home: Path) -> Path:
    """platformdirs' answer for `home` — what the installed app would use.

    Both launchers transcribe this rule rather than importing platformdirs,
    which does not exist before the venv does. Comparing against the real
    function is what keeps the transcription honest: both scripts used to
    hardcode the macOS path, so on Linux they named a directory the app never
    opens — the demo guard protected nothing and start.sh exported a database
    `python run.py` would never have chosen.
    """
    saved = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        return Path(user_data_dir(APP_NAME, APP_AUTHOR)).expanduser().resolve()
    finally:
        if saved is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = saved


def _demo_data_dir_for(home: Path) -> Path:
    """Where ./start-demo.sh puts a demo when nothing is set."""
    real = _real_data_dir_for(home)
    return real.parent / f"{APP_NAME}-Demo"


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


def _resolver_db(monkeypatch, home: Path, value: str):
    """What env_db_path() itself returns for `value` under `home`.

    The real function, for the same reason _resolver_data_dir calls the real
    app_data_dir_path(): a second copy of the rule here would drift in step
    with the launcher's copy and prove nothing.
    """
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv(DB_ENV, value)
    return paths.env_db_path()


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


def test_d1_the_session_restores_the_override_afterwards(tmp_path, monkeypatch):
    """The pop is scoped to the session, not a permanent deletion.

    pytest_sessionfinish puts the value back, so an in-process caller that
    runs pytest.main() and then does other work still has its environment.

    This calls the two hooks directly, because the value has to be observed
    *after* the session that popped it has finished. The previous version ran
    a nested session whose body was ``assert True`` and whose only assertion
    was that it exited 0 — so deleting the restore left it green. It could not
    fail. Found by a cold review pass.
    """
    import conftest as root_conftest

    ambient = str(tmp_path / "ambient-demo")
    monkeypatch.setenv(DATA_DIR_ENV, ambient)
    session = SimpleNamespace(config=SimpleNamespace())

    root_conftest.pytest_sessionstart(session)
    assert DATA_DIR_ENV not in os.environ, (
        "pytest_sessionstart did not drop the ambient override")

    root_conftest.pytest_sessionfinish(session, 0)
    assert os.environ.get(DATA_DIR_ENV) == ambient, (
        "pytest_sessionfinish did not put the ambient override back: "
        f"{os.environ.get(DATA_DIR_ENV)!r}")


# --------------------------------------------------------------------------
# D2 — the launchers
# --------------------------------------------------------------------------

def test_d2_demo_launcher_resolves_the_demo_data_dir(tmp_path):
    """The demo defaults to GetMoreDone-Demo, never the real directory."""
    result = _print_env("start-demo.sh", tmp_path)

    assert result.returncode == 0, result.stderr
    values = _parsed(result)
    assert Path(values["data-dir"]) == _demo_data_dir_for(tmp_path)
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
    real = _real_data_dir_for(tmp_path)
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

    expected = _real_data_dir_for(tmp_path) / "getmoredone.db"
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

    expected = _real_data_dir_for(tmp_path) / "getmoredone.db"
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

    assert Path(values["data-dir"]) == _demo_data_dir_for(tmp_path)


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
# behavioural check is practical: anchored to whole lines, asserting exact
# counts and the branch each line falls in.
PIP_INSTALL_LINE = re.compile(
    r"^(?P<indent> *)\"\$VENV_PY\" -m pip install -q -r requirements\.txt \|\| exit 1$",
    re.MULTILINE,
)
SEED_LINE = re.compile(
    r"^(?P<indent> *)\"\$VENV_PY\" tools/create_demo_data\.py \|\| exit 1$",
    re.MULTILINE,
)


def _venv_branch_span(script: str) -> tuple[int, int]:
    """The character span of start-demo.sh's "create the venv" if-block.

    Nesting in bash is `if`/`fi`, not indentation. An earlier version of the
    guard below asked how many spaces the install line carried, which let the
    line be moved back inside this branch — the exact defect the guard exists
    for — as long as it kept four of them. Found by a cold review pass.
    """
    opener = 'if [ ! -x "$VENV_PY" ]; then'
    start = None
    depth = 0
    offset = 0
    for line in script.splitlines(keepends=True):
        stripped = line.strip()
        if start is None:
            if stripped == opener:
                start = offset
                depth = 1
        elif stripped.startswith("if "):
            depth += 1
        elif stripped == "fi":
            depth -= 1
            if depth == 0:
                return start, offset + len(line)
        offset += len(line)
    raise AssertionError(f"start-demo.sh has no unclosed `{opener}` branch")


def test_d2_demo_launcher_installs_requirements_before_seeding():
    """The install must not be nested inside the "create the venv" branch.

    It was, so a venv that existed but lacked a runtime dependency made the
    seed raise ModuleNotFoundError and took the launch down with it — where
    plain start.sh would have installed the dependency and started the app.
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

    branch_start, branch_end = _venv_branch_span(script)
    assert not branch_start <= installs[0].start() < branch_end, (
        'the requirements install sits inside the `if [ ! -x "$VENV_PY" ]` '
        "branch, so it runs only for a venv this script just created — a venv "
        "that exists but lacks a runtime dependency takes the seed, and the "
        "launch, down with it"
    )
    assert installs[0].start() < seeds[0].start(), (
        "the requirements install comes after the seeding call, so the seed "
        "runs before its dependencies are installed"
    )


def test_d2_launchers_are_valid_bash():
    """A launcher with a syntax error fails at the user, not in CI."""
    for script in ("start.sh", "start-demo.sh"):
        result = subprocess.run(
            ["bash", "-n", str(REPO_ROOT / script)],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, f"{script}: {result.stderr}"


def test_d2_the_launchers_agree_with_platformdirs(tmp_path):
    """Both scripts' idea of "the real installation" is platformdirs'.

    Neither can import platformdirs — on a first launch there is no venv —
    so both transcribe its rule, and both used to transcribe it as the macOS
    path unconditionally. On Linux that left the demo guard watching a
    directory the app never uses, so pointing the demo at the real
    ~/.local/share/GetMoreDone was accepted and would have seeded it.
    """
    real = _real_data_dir_for(tmp_path)

    refusal = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(real))
    assert refusal.returncode != 0, (
        f"start-demo.sh does not recognise {real} as the real installation:\n"
        f"{refusal.stdout}")

    default = _parsed(_print_env("start.sh", tmp_path))
    assert default["db-env"] == str(real / "getmoredone.db"), (
        "start.sh's production default is not the directory platformdirs "
        "names, so ./start.sh and `python run.py` would use two databases")


def test_d2_demo_launcher_refuses_a_case_variant_of_the_real_directory(tmp_path):
    """One name is not one directory on a case-insensitive volume.

    macOS volumes are case-insensitive by default and Path.resolve() folds no
    case, so ".../getmoredone" and ".../GetMoreDone" are two strings for one
    directory. The guard compared the strings, so the lowercase spelling was
    accepted and a launch would have written the demo's database, settings and
    app.lock in among the real items. Found by a cold review pass.
    """
    real = _real_data_dir_for(tmp_path)
    variant = real.parent / real.name.lower()

    result = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=str(variant))

    assert result.returncode != 0, (
        f"a case variant of the real directory was accepted:\n{result.stdout}")
    assert "is inside" in result.stdout


def test_d2_demo_launcher_refuses_the_filesystem_root(tmp_path):
    """"/" is the one directory that contains everything.

    The containment test built its pattern as "$DEMO"/*, which for "/" is the
    literal "//*" and matches nothing — so the root was accepted, exported as
    "//getmoredone.db", and DEMO_INSTALL.md's reset recipe then tells the
    reader to `rm -rf` what the launcher printed. Found by a cold review pass.
    """
    for spelling in ("/", "//", "/..", "/../.."):
        result = _print_env("start-demo.sh", tmp_path, GETMOREDONE_DATA_DIR=spelling)

        assert result.returncode != 0, (
            f"GETMOREDONE_DATA_DIR={spelling!r} was accepted:\n{result.stdout}")
        assert "root" in result.stdout


def test_d2_demo_launcher_refuses_a_database_symlinked_out_of_the_demo(tmp_path):
    """The guard canonicalises the directory; the app canonicalises the file.

    env_db_path() resolves the whole database path, following a final-component
    symlink, so a link at <demo>/getmoredone.db sent every write to its target
    while --print-env reported the demo path. The target can be the real
    database. Found by a cold review pass.
    """
    real = _real_data_dir_for(tmp_path)
    real.mkdir(parents=True)
    real_db = real / "getmoredone.db"
    real_db.write_bytes(b"")
    demo = _demo_data_dir_for(tmp_path)
    demo.mkdir(parents=True)
    (demo / "getmoredone.db").symlink_to(real_db)

    result = _print_env("start-demo.sh", tmp_path)

    assert result.returncode != 0, (
        f"a database symlinked out of the demo directory was accepted:\n"
        f"{result.stdout}")
    assert "outside" in result.stdout


def test_d2_start_sh_agrees_with_paths_on_a_non_breaking_space(tmp_path, monkeypatch):
    """The shell's whitespace class is not str.strip().

    bash's [[:space:]] does not match U+00A0 and Python's strip() does, so a
    value of one non-breaking space was non-empty to start.sh and empty to
    paths.py: the launcher printed a path inside the repository checkout while
    the app opened the real production database. Found by a cold review pass.
    """
    values = _parsed(_print_env("start.sh", tmp_path, GETMOREDONE_DATA_DIR="\u00a0"))

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv(DATA_DIR_ENV, "\u00a0")
    monkeypatch.delenv(DB_ENV, raising=False)

    assert values["data-dir"] == "", (
        "start.sh treated a non-breaking space as a data directory; paths.py "
        "strips it away and falls back to production")
    assert Path(values["db"]) == paths.resolve_db_path()


def test_d2_print_env_matches_the_db_resolver(tmp_path, monkeypatch):
    """start.sh mirrors env_db_path(), in-memory targets included.

    Nothing ran either launcher with GETMOREDONE_DB set, so the whole branch
    was untested: deleting it changed no test, and its unanchored substring
    test for "in-memory" reported "./dbs/mode=memory/x.db" unresolved while
    the app opened the resolved path. Found by a cold review pass.
    """
    spellings = [
        "~/explicit.db",
        str(tmp_path / "x" / ".." / "explicit.db"),
        ":memory:",
        "file::memory:?cache=shared",
        "file:/tmp/x.db?mode=memory",
        "./dbs/mode=memory/x.db",
    ]

    for spelling in spellings:
        values = _parsed(_print_env("start.sh", tmp_path, GETMOREDONE_DB=spelling))
        expected = _resolver_db(monkeypatch, tmp_path, spelling)

        assert values["db-env"] == spelling
        assert values["db"] == str(expected), (
            f"start.sh resolved GETMOREDONE_DB={spelling!r} to "
            f"{values['db']!r}, but env_db_path() returns {expected!r}"
        )


def test_d2_the_seed_decision_reads_an_awkward_path_and_creates_nothing(tmp_path):
    """The item count went through an f-string, not a URI.

    SQLite parses "file:<path>?<query>", so a "?" in the demo path truncated
    the filename and took `mode=ro` with it — the read created a file at the
    truncated path, during the one command documented to create nothing. A "%"
    made the path URI-decode to one that does not exist, so the count came
    back -1, seed stuck at yes, and load_demo_data() is additive: six more
    items on every launch. Found by a cold review pass.
    """
    parent = tmp_path / "awkward"
    for name in ("a?b", "pc%20x"):
        demo = parent / name
        demo.mkdir(parents=True)
        db = demo / "getmoredone.db"
        with sqlite3.connect(db) as con:
            con.execute("create table action_items (id integer primary key)")
            con.execute("insert into action_items values (1)")
        con.close()

        values = _parsed(_print_env("start-demo.sh", tmp_path,
                                    GETMOREDONE_DATA_DIR=str(demo)))

        assert values["seed"] == "no", (
            f"the launcher could not read the item count under {name!r}, so it "
            "would seed an already-seeded demo and double its items")

    assert sorted(child.name for child in parent.iterdir()) == ["a?b", "pc%20x"], (
        "reading the item count created something next to the demo directory")


def test_d2_demo_launcher_refuses_an_unknown_argument(tmp_path):
    """A mistyped flag used to perform a full launch.

    "--printenv" matched nothing, so the command documented to touch nothing
    fell through to the mkdir, the pip install and the seed. Found by a cold
    review pass.
    """
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "start-demo.sh"), "--printenv"],
        cwd=str(REPO_ROOT),
        env=_child_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 2, result.stdout
    assert "Unknown argument" in result.stdout
    assert not _demo_data_dir_for(tmp_path).exists(), (
        "the refused run created the demo data directory anyway")


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
    real = _real_data_dir_for(tmp_path)
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
    real = _real_data_dir_for(tmp_path)
    real.mkdir(parents=True)
    support = real.parent

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
    target = _real_data_dir_for(tmp_path)

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
    which cannot be imported before the venv exists. This pins both copies to
    app_data_dir_path() over the awkward spellings — a tilde, a trailing
    slash, a doubled slash, a "..", and a symlinked parent — so a change to
    the resolver that a mirror does not follow turns the suite red.

    It ran only start.sh until a cold review pass pointed out that the name
    and the paragraph above both claimed otherwise, leaving start-demo.sh's
    duplicate unpinned for every spelling but the tilde.
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

    for script in ("start.sh", "start-demo.sh"):
        for spelling in spellings:
            values = _parsed(
                _print_env(script, tmp_path, GETMOREDONE_DATA_DIR=spelling))
            expected = _resolver_data_dir(monkeypatch, tmp_path, spelling)
            assert Path(values["data-dir"]) == expected, (
                f"{script} resolved {spelling!r} to {values['data-dir']!r}, "
                f"but app_data_dir_path() resolves it to {expected}"
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

