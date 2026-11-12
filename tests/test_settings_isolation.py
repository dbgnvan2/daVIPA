"""The suite must not touch the user's real settings file or database.

Several tests call ``AppSettings.load()`` / ``.save()`` with no path, and
``DatabaseManager()`` with no path opens the real database and runs migrations
on it. Both are redirected by conftest.py.

The first version of this file checked only ``src.getmoredone.app_settings`` —
the same copy the fixture patched — and passed while the *other* module object
(`getmoredone.app_settings`, a different class) went on writing the real file.
So it asserts both class objects now, and it exercises the session hooks in a
nested pytest run rather than trusting that they work.

Spec: docs/unused-docs/implementation_plan_2026-08-19_backlog_clearance.md#batch-1
"""

import importlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from platformdirs import user_data_dir

from src.getmoredone.paths import APP_AUTHOR, APP_NAME

REAL_DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR)).expanduser().resolve()


@pytest.mark.parametrize("module_name", [
    "src.getmoredone.app_settings",
    "getmoredone.app_settings",
])
def test_every_copy_of_appsettings_is_redirected(module_name):
    """Both import spellings are different class objects. Patch both, check both."""
    settings_cls = importlib.import_module(module_name).AppSettings
    in_use = Path(settings_cls.get_settings_path())

    assert in_use != REAL_DATA_DIR / "settings.json", (
        f"{module_name} still points at the real settings file")
    assert REAL_DATA_DIR not in in_use.parents, (
        f"{module_name} redirects inside the real data directory: {in_use}")


def test_the_two_import_spellings_really_are_different_classes():
    """If this ever fails, the both-classes patch has become unnecessary."""
    a = importlib.import_module("src.getmoredone.app_settings").AppSettings
    b = importlib.import_module("getmoredone.app_settings").AppSettings

    assert a is not b, (
        "the two module objects have merged — simplify the conftest fixture")


def test_the_database_is_redirected_away_from_the_real_one():
    """DatabaseManager() with no path runs migrations on whatever it opens."""
    from src.getmoredone.paths import resolve_db_path

    assert os.environ.get("GETMOREDONE_DB"), (
        "GETMOREDONE_DB is unset, so a pathless DatabaseManager would open the "
        "user's real database and migrate it")
    assert Path(str(resolve_db_path(None))) != REAL_DATA_DIR / "getmoredone.db"


def test_saving_settings_does_not_write_the_real_file(tmp_path):
    from src.getmoredone.app_settings import AppSettings

    real = REAL_DATA_DIR / "settings.json"
    before = real.stat().st_mtime_ns if real.exists() else None

    AppSettings.load().save()

    assert Path(AppSettings.get_settings_path()).exists(), "the save went nowhere"
    if before is not None:
        assert real.stat().st_mtime_ns == before, "the real settings file was written"


def _run_nested_pytest(tmp_path, probe_body, env_extra=None, env_remove=()):
    """Run a throwaway pytest whose conftest carries our two session hooks."""
    repo_root = Path(__file__).resolve().parents[1]
    # Loaded by path under a distinct module name: a nested file called
    # conftest.py cannot `from conftest import ...` — it would import itself.
    (tmp_path / "conftest.py").write_text(textwrap.dedent(f"""
        import importlib.util
        import sys

        sys.path.insert(0, {str(repo_root)!r})
        _spec = importlib.util.spec_from_file_location(
            "gmd_root_conftest", {str(repo_root / "conftest.py")!r})
        _root = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_root)

        pytest_sessionstart = _root.pytest_sessionstart
        pytest_sessionfinish = _root.pytest_sessionfinish
    """))
    (tmp_path / "test_probe.py").write_text(textwrap.dedent(probe_body))
    # The nested run watches a fake data directory, so exercising the guard
    # never touches the real files — and never trips the parent run's own guard.
    fake_data_dir = tmp_path / "fake_app_data"
    fake_data_dir.mkdir()
    (fake_data_dir / "settings.json").write_text('{"stub": true}')

    # "absent" by default: the guard now treats a content change differently
    # when a packaged app process is running, and whether one is open on the
    # machine running these tests is not something a test may depend on.
    env = dict(os.environ, GETMOREDONE_TEST_GUARD_DIR=str(fake_data_dir),
               GETMOREDONE_TEST_GUARD_APP="absent")
    env.update(env_extra or {})
    for name in env_remove:
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", str(tmp_path)],
        capture_output=True, text=True, cwd=str(tmp_path), timeout=180, env=env,
    )
    result.fake_settings = fake_data_dir / "settings.json"
    return result


def test_the_session_guard_fails_the_run_when_content_changes(tmp_path):
    """A test that rewrites the real settings file must turn the run red.

    Nothing exercised these hooks before; "it fires" had been checked by hand.
    The probe restores the file it edits, so this test is safe to run anywhere.

    Changed 2026-11-11 (intentional behaviour change, not a test bent to pass):
    the harness now forces the app state to "absent", because a content change
    with the packaged app running is that app saving, not an escape.
    """
    result = _run_nested_pytest(tmp_path, """
        import os
        from pathlib import Path

        def test_probe():
            watched = Path(os.environ["GETMOREDONE_TEST_GUARD_DIR"]) / "settings.json"
            watched.write_text('{"stub": true, "written_by_a_test": true}')
    """)

    assert "GUARD:" in result.stdout, (
        f"the guard did not report an escape:\n{result.stdout}\n{result.stderr}")
    assert "CONTENT changed" in result.stdout, result.stdout
    assert result.returncode != 0, "the guard did not fail the run"


def test_the_session_guard_leaves_a_clean_run_alone(tmp_path):
    result = _run_nested_pytest(tmp_path, """
        def test_probe():
            assert True
    """)

    assert result.returncode == 0, f"a clean run was failed:\n{result.stdout}"
    assert "GUARD:" not in result.stdout


def test_rlsm2_the_weekly_log_is_fingerprinted(tmp_path):
    """A test that writes the real weekly-tactic log must turn the run red.

    Purpose: RLS-M2 -- the fingerprint covered ``settings.json`` and
             ``getmoredone.db`` only, so the one file a render helper was found
             opening was the one file the guard could not see.
    Spec:    docs/unused-docs/implementation_plan_2026-11-12_test_harness_isolation.md#rls-m2

    Driven through the same nested run as the content-change guard above,
    pointed at a fake directory, so no real file is touched. The fake directory
    holds no log, so this is the "file appeared" route.
    """
    result = _run_nested_pytest(tmp_path, """
        import os
        from pathlib import Path

        def test_probe():
            watched = Path(os.environ["GETMOREDONE_TEST_GUARD_DIR"])
            (watched / "weekly_tactic_debug.log").write_text("written by a test\\n")
    """)

    assert "GUARD:" in result.stdout, (
        f"the guard did not notice the weekly log:\n{result.stdout}\n{result.stderr}")
    assert "weekly_log" in result.stdout, (
        f"the guard fired but did not name the weekly log:\n{result.stdout}")
    assert result.returncode != 0, "the guard did not fail the run"


# --- CIG-A4: the guard must name the right cause -----------------------------

_SETTINGS_BEFORE = (1_000_000_000, 40, "a" * 64, "/fake/settings.json")
_DB_BEFORE = (1_000_000_000, 3_000_000, "c" * 64, "/fake/getmoredone.db")


def _moved(before, *, size=None, digest=None):
    """``before`` with its mtime advanced, and optionally size or digest."""
    mtime, old_size, old_digest, path = before
    return (mtime + 10 ** 9,
            old_size if size is None else size,
            old_digest if digest is None else digest,
            path)


@pytest.mark.parametrize("key,before,app_state,after,expected", [
    # Content moved, nothing else running: the escape the guard exists for.
    ("settings", _SETTINGS_BEFORE, False, _moved(_SETTINGS_BEFORE, size=41),
     "content_changed"),
    ("settings", _SETTINGS_BEFORE, False,
     _moved(_SETTINGS_BEFORE, digest="b" * 64), "content_changed"),
    # Same, with the app up: that app saving, reported but not an escape.
    ("settings", _SETTINGS_BEFORE, True,
     _moved(_SETTINGS_BEFORE, digest="b" * 64), "content_changed_app_running"),
    # Same, with no way to tell: unknown must not excuse it (P1).
    ("settings", _SETTINGS_BEFORE, None,
     _moved(_SETTINGS_BEFORE, digest="b" * 64), "content_changed_app_unknown"),
    # The database, same size, different bytes -- an in-place UPDATE of
    # existing rows. Compared by size alone until 2026-11-11, which read it as
    # "nothing was rewritten".
    ("database", _DB_BEFORE, False, _moved(_DB_BEFORE, digest="d" * 64),
     "content_changed"),
    # A file that appeared, and one that went: on a machine where the app has
    # never run, a test CREATING the real settings file is the escape, and it
    # is the one route with no digest or size to compare.
    ("settings", None, False, _SETTINGS_BEFORE, "content_changed"),
    ("settings", _SETTINGS_BEFORE, False, None, "content_changed"),
    # Only the timestamp moved: the bytes are equal, so nothing wrote.
    ("settings", _SETTINGS_BEFORE, True, _moved(_SETTINGS_BEFORE),
     "app_running"),
    ("settings", _SETTINGS_BEFORE, False, _moved(_SETTINGS_BEFORE),
     "timestamp_only"),
    ("settings", _SETTINGS_BEFORE, None, _moved(_SETTINGS_BEFORE),
     "app_unknown"),
    ("database", _DB_BEFORE, False, _moved(_DB_BEFORE), "timestamp_only"),
    # Nothing moved.
    ("settings", _SETTINGS_BEFORE, True, _SETTINGS_BEFORE, None),
])
def test_cghm11_the_guard_verdict_is_a_function_of_the_fingerprints(
        key, before, app_state, after, expected):
    """CGH-M1.1 — the decision, not the sentence.

    Purpose: until 2026-11-11 the branch was inline in the hook and only
             reachable by running a nested run, so the app-running case was
             never exercised (CIG-A4).
    """
    import conftest

    verdicts = conftest.guard_verdicts({key: before}, {key: after}, app_state)

    if expected is None:
        assert verdicts == [], f"an unchanged file produced {verdicts}"
        return
    assert [verdict for _, verdict, _ in verdicts] == [expected]
    assert verdicts[0][0] == key
    assert verdicts[0][2] == (after or before)[3]


def test_cghm12_a_verdict_blames_a_test_exactly_when_it_fails_the_run():
    """CGH-M1.2 — the accusation and the exit status cannot drift apart.

    The accusation used to be appended outside the if/else, so the branch
    written to say "harmless" ended by blaming a test anyway. The inverse is
    the same defect: a verdict that fails a run without saying why.
    """
    import conftest

    accusing = {
        verdict for verdict, text in conftest.GUARD_EXPLANATIONS.items()
        if conftest.GUARD_ACCUSATION in text
    }

    assert accusing == set(conftest.GUARD_FAILING_VERDICTS), (
        f"{sorted(accusing)} blame a test but "
        f"{sorted(conftest.GUARD_FAILING_VERDICTS)} fail the run")
    assert len(accusing) == 2, f"expected two accusing verdicts, got {accusing}"
    for verdict in conftest.GUARD_EXPLANATIONS:
        assert conftest.guard_should_fail(
            [("database", verdict, "/fake/db")]) is (verdict in accusing), (
            f"{verdict} fails the run and blames nobody, or the reverse")


def test_cghm12_a_timestamp_move_leaves_the_run_green(tmp_path):
    """CGH-M1.2, end to end: a touched mtime is reported and is not a failure."""
    result = _run_nested_pytest(tmp_path, """
        import os
        from pathlib import Path

        def test_probe():
            watched = Path(os.environ["GETMOREDONE_TEST_GUARD_DIR"]) / "settings.json"
            stat = watched.stat()
            os.utime(watched, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10 ** 9))
    """)

    import conftest

    assert "GUARD:" in result.stdout, (
        f"the timestamp move was not reported at all:\n{result.stdout}")
    assert conftest.GUARD_ACCUSATION not in result.stdout, (
        f"a timestamp move blamed a test:\n{result.stdout}")
    assert result.returncode == 0, (
        f"a timestamp move failed the run:\n{result.stdout}")


def test_cghm13_a_content_change_with_the_app_up_is_reported_not_failed(tmp_path):
    """CGH-M1.3 — the app saving is not an escape, and says so.

    Measured 2026-11-09: the packaged app rewrites the user's database while it
    sits idle, so hashing the database (which this batch does, to close the
    same-size blind spot) would redden every local run with the app open.
    """
    result = _run_nested_pytest(tmp_path, """
        import os
        from pathlib import Path

        def test_probe():
            watched = Path(os.environ["GETMOREDONE_TEST_GUARD_DIR"]) / "settings.json"
            watched.write_text('{"stub": true, "saved_by_the_app": true}')
    """, env_extra={"GETMOREDONE_TEST_GUARD_APP": "running"})

    import conftest

    assert "GUARD:" in result.stdout, (
        f"the change was not reported at all:\n{result.stdout}")
    assert conftest.GUARD_ACCUSATION not in result.stdout, (
        f"the app saving was blamed on a test:\n{result.stdout}")
    assert result.returncode == 0, (
        f"the app saving failed the run:\n{result.stdout}")


def test_cghm13_the_database_is_hashed_not_just_sized(tmp_path, monkeypatch):
    """CGH-M1.3 — an in-place write of the same number of bytes is detected.

    Purpose: the fingerprint hashed ``settings`` only, so a test writing the
             real database in place was reported as "nothing was rewritten".
    """
    import conftest

    (tmp_path / "settings.json").write_text('{"stub": true}')
    db = tmp_path / "getmoredone.db"
    db.write_bytes(b"\x01" * 4096)
    monkeypatch.setenv("GETMOREDONE_TEST_GUARD_DIR", str(tmp_path))

    before = conftest._user_data_fingerprint()
    db.write_bytes(b"\x02" * 4096)
    after = conftest._user_data_fingerprint()

    assert before["database"][1] == after["database"][1], "the size moved"
    assert before["database"][2] is not None, "the database carries no digest"
    assert before["database"][2] != after["database"][2], "the digest is stale"
    assert [verdict for _, verdict, _ in
            conftest.guard_verdicts(before, after, False)] == ["content_changed"]


def test_cghm14_the_app_pattern_does_not_match_the_suites_own_launches():
    r"""CGH-M1.4 — the suite must not hand the guard an alibi for its own writes.

    Purpose: the pattern was ``daVIPA\.app/Contents/MacOS|run\.py`` and
             tests/test_first_run.py and tests/test_selftest_cli.py both spawn
             ``<repo>/run.py --selftest``, so a leaked subprocess would have
             read as "the app is running".
    """
    import re

    import conftest

    pattern = re.compile(conftest.APP_PROCESS_PATTERN)
    repo_root = Path(__file__).resolve().parents[1]

    assert not pattern.search(f"{sys.executable} {repo_root / 'run.py'} --selftest"), (
        "the suite's own selftest launch matches the app pattern")
    assert not pattern.search(f"{sys.executable} -m pytest tests"), (
        "a test run matches the app pattern")
    assert pattern.search(
        "/Applications/daVIPA.app/Contents/MacOS/daVIPA"), (
        "the packaged app does not match its own pattern")


def test_cghm14_app_detection_cannot_hang_or_raise(monkeypatch):
    """CGH-M1.4 — unknown is not an escape (P1), and the call has a timeout (P5)."""
    import shutil

    import conftest

    # Every assertion below is about the pgrep path, which the forcing seam
    # short-circuits. Exported in the shell -- the obvious thing to do while
    # debugging the guard -- it inverted this test and the stated cause with it.
    monkeypatch.delenv(conftest.TEST_GUARD_APP_ENV, raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert conftest.app_is_running() is None, "no pgrep must read as unknown"

    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/pgrep")

    class _Found:
        def __init__(self, returncode, stdout=""):
            self.returncode = returncode
            self.stdout = stdout

    seen = {}

    def _answer(returncode, stdout=""):
        def run(cmd, **kwargs):
            seen.update(kwargs)
            return _Found(returncode, stdout)
        return run

    for returncode, stdout, expected in [
        (0, "44389\n", True),
        (0, "", False),
        (1, "", False),
        (2, "", None),
    ]:
        monkeypatch.setattr(subprocess, "run", _answer(returncode, stdout))
        assert conftest.app_is_running() is expected, (
            f"pgrep exit {returncode} with {stdout!r} read as the wrong state")

    assert seen.get("timeout"), "the lookup has no timeout"

    def _raise(exc):
        def run(cmd, **kwargs):
            raise exc
        return run

    for exc in (OSError("no such binary"),
                subprocess.TimeoutExpired(cmd="pgrep", timeout=2.0)):
        monkeypatch.setattr(subprocess, "run", _raise(exc))
        assert conftest.app_is_running() is None, (
            f"{type(exc).__name__} did not read as unknown")


def test_remove_test_db_dir_refuses_a_directory_it_did_not_make(tmp_path):
    """The helper runs at the end of every local run; a wrong path is final.

    conftest.remove_test_db_dir is handed an attribute off session.config. If
    that ever points somewhere real, rmtree takes it with no way back — so the
    name is checked, not trusted.
    """
    import conftest

    precious = tmp_path / "not-ours"
    precious.mkdir()
    (precious / "important.txt").write_text("keep me")

    assert conftest.remove_test_db_dir(precious) is False
    assert (precious / "important.txt").read_text() == "keep me", (
        "the helper deleted a directory that was not one of its own"
    )


def test_remove_test_db_dir_removes_one_it_did_make(tmp_path):
    """And it does actually delete the real thing, not merely decline."""
    import conftest

    ours = tmp_path / "gmd-test-db-abc123"
    ours.mkdir()
    (ours / "test.db").write_text("x")

    assert conftest.remove_test_db_dir(ours) is True
    assert not ours.exists()


def test_the_temp_database_directory_is_removed_at_the_end_of_a_run(tmp_path):
    """The two hooks together, in a nested run.

    tempfile.mkdtemp does not clean up after itself and nothing here did
    either, so every run left one behind: 1449 had accumulated since
    2026-08-19, one per run.

    The first version of this test pointed a nested pytest at a directory
    outside the repo, so the root conftest was never collected, no temp
    directory was ever made, and "none left behind" passed whether the cleanup
    ran or not. It went green with the cleanup call deleted. Hence the first
    assertion: prove the run really made one in the place being watched before
    concluding anything from its absence.
    """
    temp_root = tmp_path / "temp_root"
    temp_root.mkdir()
    receipt = tmp_path / "db_path.txt"

    result = _run_nested_pytest(
        tmp_path,
        f"""
        import os
        from pathlib import Path

        def test_probe():
            Path({str(receipt)!r}).write_text(os.environ["GETMOREDONE_DB"])
        """,
        env_extra={"TMPDIR": str(temp_root), "GETMOREDONE_NO_MAPPED_WINDOWS": "1"},
        env_remove=("GETMOREDONE_DB",),
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # The instrument moves: sessionstart made a directory, and made it here.
    assert receipt.exists(), "the probe never ran"
    db_path = Path(receipt.read_text())
    assert temp_root in db_path.parents, (
        f"the nested run put its database at {db_path}, not under the temp root "
        f"this test watches — the absence of leftovers there proves nothing"
    )
    assert db_path.parent.name.startswith("gmd-test-db-"), db_path

    leftovers = list(temp_root.glob("gmd-test-db-*"))
    assert leftovers == [], (
        f"the run left {len(leftovers)} temp database director(ies) behind: "
        f"{[q.name for q in leftovers]}"
    )
